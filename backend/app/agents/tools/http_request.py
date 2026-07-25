"""
Ferramenta de Requisição HTTP Dinâmica — Executa chamadas HTTP configuradas no banco de dados.

Isso permite que os agentes chamem APIs externas sem exigir novo código Python.
As ferramentas são configuradas na tabela agent_http_tools.
"""

import json
import logging
import re
from typing import Any, Dict, Optional, Type

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)


class HttpRequestTool(BaseTool):
    """
    Tool genérica que executa requisições HTTP configuradas dinamicamente.
    Suporta execução Síncrona e Assíncrona.
    """

    name: str
    description: str
    args_schema: Type[BaseModel]
    target_url: str
    method: str
    headers: Dict[str, str]
    body_template: Optional[str] = None  # Template JSON com placeholders {{param}}

    def _prepare_request(self, kwargs):
        """Helper para preparar URL, Params e Body (com suporte a templates)"""
        logger.info(
            f"[HttpTool] 🚀 {self.name} ({self.method} {self.target_url}) | Params: {kwargs}"
        )

        # 1. Substituir variáveis de Path na URL (formato {param})
        final_url = self.target_url
        path_params = {}
        for key, value in kwargs.items():
            if f"{{{key}}}" in final_url:
                final_url = final_url.replace(f"{{{key}}}", str(value))
                path_params[key] = value

        # 2. Parâmetros restantes (não usados na URL)
        remaining = {k: v for k, v in kwargs.items() if k not in path_params}

        # 3. Para GET, usar query params
        if self.method == "GET":
            return final_url, remaining, None

        # 4. Para POST/PUT/PATCH, verificar body_template
        json_body = None

        if self.body_template:
            # Processar o template substituindo {{param}} pelos valores
            try:
                body_str = self.body_template

                # Substituir placeholders {{param}} pelos valores
                def replace_placeholder(match):
                    param_name = match.group(1)
                    value = remaining.get(param_name, "")
                    # Se o valor é string, manter como está para deixar o JSON válido
                    # Se é número ou boolean, converter
                    if isinstance(value, (int, float, bool)):
                        return (
                            str(value).lower()
                            if isinstance(value, bool)
                            else str(value)
                        )
                    # Para strings, precisamos retornar com aspas para JSON válido
                    return str(value)

                # Padrão para encontrar {{parametro}}
                body_str = re.sub(r"\{\{(\w+)\}\}", replace_placeholder, body_str)

                # Parse do JSON resultante
                json_body = json.loads(body_str)
                logger.info(f"[HttpTool] 📋 Body template processado: {json_body}")

            except json.JSONDecodeError as e:
                logger.warning(
                    f"[HttpTool] ⚠️ Erro ao processar body_template: {e}. Usando parâmetros diretamente."
                )
                json_body = remaining
        else:
            # Sem template, usar parâmetros diretamente como body JSON
            json_body = remaining if remaining else None

        return final_url, {}, json_body

    # ------------------------------------------------------------------
    # SPEC-054 Bloco C — HTTP Egress Guard
    # ------------------------------------------------------------------
    def _egress_policy(self):
        """Política de saída desta tool.

        `allowed_hosts` vem do cadastro. Vazio = DENY ALL: a ausência de
        allowlist NÃO libera a internet. Sem isso, uma tool cadastrada com
        URL controlável levaria a SSRF (metadata da cloud, rede interna).
        """
        from app.core.egress_guard import EgressPolicy

        raw = getattr(self, "allowed_hosts", None)
        if not raw:
            # Fallback seguro: só o host da própria URL configurada.
            from urllib.parse import urlparse

            host = (urlparse(self.url).hostname or "").lower()
            raw = [host] if host else []

        return EgressPolicy.from_iterable(
            raw,
            allow_plaintext_http=bool(getattr(self, "allow_plaintext_http", False)),
        )

    def _guard(self, url: str):
        from app.core.egress_guard import EgressBlocked, check_url, safe_log_url

        try:
            return check_url(url, self._egress_policy())
        except EgressBlocked as blocked:
            logger.warning(
                "[HttpTool][EGRESS_BLOCKED] motivo=%s detalhe=%s url=%s",
                blocked.reason, blocked.detail, safe_log_url(url),
            )
            raise

    @staticmethod
    def _validate_response(response) -> Optional[str]:
        """Content-type e tamanho. Retorna mensagem de erro ou None."""
        from app.core.egress_guard import MAX_RESPONSE_BYTES, content_type_allowed

        ctype = response.headers.get("content-type")
        if not content_type_allowed(ctype):
            return f"Resposta recusada: content-type não permitido ({(ctype or 'ausente')[:60]})."

        declared = response.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > MAX_RESPONSE_BYTES:
            return "Resposta recusada: excede o tamanho máximo permitido."

        if len(response.content) > MAX_RESPONSE_BYTES:
            return "Resposta recusada: excede o tamanho máximo permitido."

        return None

    def _run(self, **kwargs) -> Any:
        """Execução Síncrona (usada pelo LangGraph atual)"""
        from app.core.egress_guard import (
            CONNECT_TIMEOUT_S, EgressBlocked, READ_TIMEOUT_S, TOTAL_TIMEOUT_S, safe_log_url,
        )

        try:
            url, params, json_body = self._prepare_request(kwargs)
            self._guard(url)

            timeout = httpx.Timeout(TOTAL_TIMEOUT_S, connect=CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S)
            # follow_redirects=False: cada redirect é revalidado explicitamente.
            with httpx.Client(timeout=timeout, follow_redirects=False) as client:
                response = client.request(
                    method=self.method, url=url, headers=self.headers,
                    params=params, json=json_body,
                )
                response = self._follow_redirects_sync(client, response)

                if response.status_code >= 400:
                    return f"Erro API ({response.status_code}): {response.text[:500]}"

                invalid = self._validate_response(response)
                if invalid:
                    logger.warning("[HttpTool] %s url=%s", invalid, safe_log_url(url))
                    return invalid

                return response.text[:5000]

        except EgressBlocked as blocked:
            return f"Chamada bloqueada pela política de segurança de saída ({blocked.reason})."
        except Exception as e:
            logger.error(f"[HttpTool] Erro Sync: {type(e).__name__}")
            return "Erro técnico interno na execução da ferramenta."

    def _follow_redirects_sync(self, client, response):
        from app.core.egress_guard import MAX_REDIRECTS, check_url

        hops = 0
        while response.is_redirect and hops < MAX_REDIRECTS:
            location = response.headers.get("location", "")
            if not location:
                break
            if location.startswith("/"):
                from urllib.parse import urljoin

                location = urljoin(str(response.url), location)
            check_url(location, self._egress_policy())  # revalida DO ZERO
            response = client.request(method=self.method, url=location, headers=self.headers)
            hops += 1
        return response

    async def _arun(self, **kwargs) -> Any:
        """Execução Assíncrona"""
        from app.core.egress_guard import (
            CONNECT_TIMEOUT_S, EgressBlocked, MAX_REDIRECTS, READ_TIMEOUT_S,
            TOTAL_TIMEOUT_S, check_url, safe_log_url,
        )

        try:
            url, params, json_body = self._prepare_request(kwargs)
            self._guard(url)

            timeout = httpx.Timeout(TOTAL_TIMEOUT_S, connect=CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                response = await client.request(
                    method=self.method, url=url, headers=self.headers,
                    params=params, json=json_body,
                )

                hops = 0
                while response.is_redirect and hops < MAX_REDIRECTS:
                    location = response.headers.get("location", "")
                    if not location:
                        break
                    if location.startswith("/"):
                        from urllib.parse import urljoin

                        location = urljoin(str(response.url), location)
                    check_url(location, self._egress_policy())  # revalida DO ZERO
                    response = await client.request(method=self.method, url=location, headers=self.headers)
                    hops += 1

                if response.status_code >= 400:
                    return f"Erro API ({response.status_code}): {response.text[:500]}"

                invalid = self._validate_response(response)
                if invalid:
                    logger.warning("[HttpTool] %s url=%s", invalid, safe_log_url(url))
                    return invalid

                return response.text[:5000]

        except EgressBlocked as blocked:
            return f"Chamada bloqueada pela política de segurança de saída ({blocked.reason})."
        except Exception as e:
            logger.error(f"[HttpTool] Erro Async: {type(e).__name__}")
            return "Erro técnico interno na execução da ferramenta."


def create_dynamic_tool(tool_config: Dict) -> HttpRequestTool:
    """Factory que cria a Tool a partir do JSON do banco."""
    fields = {}
    for param in tool_config.get("parameters", []):
        param_type = int if param.get("type") == "integer" else str
        fields[param["name"]] = (
            param_type,
            Field(description=param.get("description", "")),
        )

    # Nome da classe do Schema precisa ser único para evitar conflitos no LangChain
    schema_name = f"{tool_config['name']}_Input"
    InputModel = create_model(schema_name, **fields)

    return HttpRequestTool(
        name=tool_config["name"],
        description=tool_config["description"],
        args_schema=InputModel,
        target_url=tool_config["url"],
        method=tool_config.get("method", "GET"),
        headers=tool_config.get("headers") or {},
        body_template=tool_config.get(
            "body_template"
        ),  # Template JSON com placeholders {{param}}
    )


# === ROUTER TOOL: Carrega tools do banco a cada execução ===


class HttpToolRouterInput(BaseModel):
    """Input para o HttpToolRouter - apenas o nome da tool e parâmetros em JSON."""

    tool_name: str = Field(description="Nome da ferramenta HTTP a executar")
    params: str = Field(default="{}", description="Parâmetros em formato JSON")


class HttpToolRouter(BaseTool):
    """
    Tool Router que carrega dinamicamente as HTTP tools do banco de dados.
    Garante que cada agente só acesse suas próprias tools, mesmo com cache de grafo.

    IMPORTANTE: Só executa tools que foram MENCIONADAS no prompt do agente.
    A IA chama esta tool passando o nome da ferramenta desejada + parâmetros.
    A tool busca a config do banco e executa (se autorizada).
    """

    name: str = "http_api"
    description: str = "Executa chamadas HTTP para APIs externas. Use APENAS as ferramentas que foram descritas no prompt do sistema. Passe tool_name com o nome da ferramenta e params com os parâmetros em JSON."
    args_schema: Type[BaseModel] = HttpToolRouterInput

    agent_id: str
    supabase_client: Any  # Supabase client instance

    def _get_available_tools_description(self) -> str:
        """Retorna descrição das tools disponíveis para este agente."""
        try:
            response = (
                self.supabase_client.table("agent_http_tools")
                .select("name, description, method")
                .eq("agent_id", self.agent_id)
                .eq("is_active", True)
                .execute()
            )

            if response.data:
                tools_desc = []
                for t in response.data:
                    tools_desc.append(
                        f"- {t['name']}: {t['description']} ({t['method']})"
                    )
                return "\n".join(tools_desc)
        except Exception as e:
            logger.error(f"[HttpToolRouter] Error fetching tools: {e}")

        return "Nenhuma ferramenta HTTP configurada."

    def _run(
        self, tool_name: str, params: str = "{}", allowed_tools: list = None
    ) -> Any:
        """
        Executa a tool HTTP especificada.

        Args:
            tool_name: Nome da ferramenta a executar
            params: Parâmetros em formato JSON
            allowed_tools: Lista de nomes de tools autorizadas (mencionadas no prompt)
        """
        logger.info(
            f"[HttpToolRouter] 🔍 Agent {self.agent_id} requesting tool: {tool_name}"
        )

        # === VERIFICAÇÃO DE AUTORIZAÇÃO ===
        # Se allowed_tools foi passado, verificar se a tool está na lista
        if allowed_tools is not None:
            if not allowed_tools:
                # Lista vazia = nenhuma HTTP tool foi mencionada no prompt
                return (
                    f"❌ Ferramenta '{tool_name}' não autorizada.\n\n"
                    f"Nenhuma ferramenta HTTP foi configurada no prompt deste agente.\n"
                    f"Para usar ferramentas HTTP, o administrador deve incluir {{nome_da_ferramenta}} no prompt do agente."
                )

            if tool_name not in allowed_tools:
                return (
                    f"❌ Ferramenta '{tool_name}' não autorizada.\n\n"
                    f"Esta ferramenta não foi mencionada no prompt do agente.\n"
                    f"Ferramentas disponíveis neste contexto: {', '.join(allowed_tools)}"
                )

            logger.info(
                f"[HttpToolRouter] ✅ Tool '{tool_name}' autorizada (mencionada no prompt)"
            )

        try:
            # 1. Buscar config da tool específica do banco
            response = (
                self.supabase_client.table("agent_http_tools")
                .select("*")
                .eq("agent_id", self.agent_id)
                .eq("name", tool_name)
                .eq("is_active", True)
                .execute()
            )

            if not response.data:
                available = self._get_available_tools_description()
                return f"Ferramenta '{tool_name}' não encontrada para este agente.\n\nFerramentas disponíveis:\n{available}"

            tool_config = response.data[0]
            logger.info(f"[HttpToolRouter] ✅ Found tool config: {tool_config['name']}")

            # 2. Parse dos parâmetros
            try:
                kwargs = json.loads(params) if params else {}
            except json.JSONDecodeError:
                kwargs = {}

            # 3. Criar e executar a tool
            tool = create_dynamic_tool(tool_config)
            return tool._run(**kwargs)

        except Exception as e:
            logger.error(f"[HttpToolRouter] Error: {e}", exc_info=True)
            return "Erro interno ao executar ferramenta."

    async def _arun(
        self, tool_name: str, params: str = "{}", allowed_tools: list = None
    ) -> Any:
        """Versão assíncrona."""
        # === VERIFICAÇÃO DE AUTORIZAÇÃO ===
        if allowed_tools is not None:
            if not allowed_tools or tool_name not in allowed_tools:
                return f"❌ Ferramenta '{tool_name}' não autorizada para este agente."

        try:
            response = (
                self.supabase_client.table("agent_http_tools")
                .select("*")
                .eq("agent_id", self.agent_id)
                .eq("name", tool_name)
                .eq("is_active", True)
                .execute()
            )

            if not response.data:
                return f"Ferramenta '{tool_name}' não encontrada."

            tool_config = response.data[0]
            kwargs = json.loads(params) if params else {}

            tool = create_dynamic_tool(tool_config)
            return await tool._arun(**kwargs)

        except Exception as e:
            logger.error(f"[HttpToolRouter] Async Error: {e}", exc_info=True)
            return "Erro interno ao executar ferramenta."
