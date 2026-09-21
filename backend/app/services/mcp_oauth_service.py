"""
MCP OAuth Service - Credenciais da PLATAFORMA.

As credenciais OAuth (Client ID + Secret) são da plataforma AutoBrokers.
Cada agente só armazena os TOKENS de acesso após autorização.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx

from app.core.relogio_do_modelo import timeout_http

logger = logging.getLogger(__name__)

#: Quanto tempo um convite de OAuth (`state` assinado) continua valendo.
#:
#: 🔴 SPEC-EXTRA-001.8 · FATIA 3. 📊 Medido por leitura em 21/09/2026: o `state`
#: era assinado (HMAC-SHA256) mas **não tinha instante nenhum dentro** — um
#: convite gerado hoje continuava aceito daqui a um ano. Quinze minutos é mais
#: que o dobro do que um OAuth humano leva (escolher a conta e clicar "permitir")
#: e fecha a janela em que um link vazado ainda escreve no banco.
STATE_VALIDADE_SEGUNDOS = 15 * 60


class ConexaoNaoEncontrada(Exception):
    """O agente ou a conexão pedida **não é desta corretora** — ou não existe.

    🔴 UMA exceção para os dois casos, de propósito (CLAUDE.md §7). Quem chama
    não consegue distinguir "é de outra corretora" de "nunca existiu", e por isso
    não consegue usar a resposta para descobrir que ids existem lá fora.
    """



class MCPOAuthService:
    """
    Serviço de OAuth para MCP - Credenciais da PLATAFORMA.

    Client ID/Secret: Variáveis de ambiente (uma única credencial)
    Access Tokens: Salvos por agente (cada cliente que autoriza)
    """

    def __init__(self):
        self._encryption_service = None
        self._supabase = None

        # Credenciais da PLATAFORMA (variáveis de ambiente)
        self.platform_credentials = {
            "google": {
                "client_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
            },
            "github": {
                "client_id": os.getenv("GITHUB_OAUTH_CLIENT_ID"),
                "client_secret": os.getenv("GITHUB_OAUTH_CLIENT_SECRET"),
            },
            "slack": {
                "client_id": os.getenv("SLACK_OAUTH_CLIENT_ID"),
                "client_secret": os.getenv("SLACK_OAUTH_CLIENT_SECRET"),
            },
        }

        # URLs de OAuth por provider
        self.provider_config = {
            "google": {
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": [
                    # Calendar
                    "https://www.googleapis.com/auth/calendar.readonly",
                    "https://www.googleapis.com/auth/calendar.events",
                    # Drive
                    "https://www.googleapis.com/auth/drive.readonly",
                    "https://www.googleapis.com/auth/drive.file",
                ],
            },
            "github": {
                "auth_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "scopes": ["repo", "read:user"],
            },
            "slack": {
                "auth_url": "https://slack.com/oauth/v2/authorize",
                "token_url": "https://slack.com/api/oauth.v2.access",
                "scopes": ["channels:read", "chat:write", "users:read"],
            },
        }

        self.redirect_base = os.getenv(
            "MCP_OAUTH_REDIRECT_BASE",
            "https://smithv2-production.up.railway.app"
        )

    @property
    def encryption(self):
        if self._encryption_service is None:
            from .encryption_service import get_encryption_service
            self._encryption_service = get_encryption_service()
        return self._encryption_service

    @property
    def supabase(self):
        if self._supabase is None:
            from ..core.database import get_supabase_client
            self._supabase = get_supabase_client().client
        return self._supabase

    # =========================================================================
    # CREDENCIAIS DA PLATAFORMA
    # =========================================================================

    def get_platform_credentials(self, provider: str) -> Optional[Dict[str, str]]:
        """
        Retorna credenciais OAuth da PLATAFORMA (variáveis de ambiente).
        """
        creds = self.platform_credentials.get(provider)

        if not creds or not creds.get("client_id") or not creds.get("client_secret"):
            logger.warning(f"[MCP OAuth] Credenciais não configuradas para {provider}")
            return None

        return creds

    def is_provider_configured(self, provider: str) -> bool:
        """Verifica se um provider está configurado na plataforma."""
        return self.get_platform_credentials(provider) is not None

    # =========================================================================
    # 🔴 A CERCA DE CORRETORA — COLADA NA AÇÃO (SPEC-EXTRA-001.8 · FATIA 3)
    # =========================================================================
    #
    # 📊 Medido por leitura em 21/09/2026, neste arquivo, antes destes métodos:
    #
    #     delete_connection    `.delete().eq("id", connection_id)`      id PURO
    #     disconnect_agent     `.update(...).eq("agent_id", agent_id)`  id PURO
    #     get_agent_connections `.select(...).eq("agent_id", agent_id)` id PURO
    #
    # A única proteção era um pré-check NA ROTA (`app/api/mcp.py:45,62`), feito
    # em dois saltos e **antes** da ação. Isso é checa-e-depois-age: entre a
    # pergunta e o `DELETE` existe uma janela (TOCTOU), e — o que importa mais —
    # qualquer chamador NOVO do serviço herdava zero proteção, porque a cerca
    # não morava aqui.
    #
    # ⛔ `agent_mcp_connections` NÃO tem coluna `company_id`. 📊 Medido em
    # `backend/supabase/migrations/schema_completo.sql:407-419` — 11 colunas:
    # id · agent_id · mcp_server_id · access_token · refresh_token ·
    # token_expires_at · scopes_granted · is_active · connected_at · created_at ·
    # updated_at. Quem sabe de quem é a conexão é o AGENTE dela. Por isso a posse
    # é confirmada em DOIS SALTOS e a ação seguinte carrega o agente CONFIRMADO
    # no filtro — nunca o que veio de fora.

    def _agente_da_corretora(self, agent_id: str, company_id: str) -> Optional[str]:
        """O `agents.id` confirmado **desta** corretora, ou `None`.

        ⛔ Erro de banco → `None`. Não conseguir provar a posse não é prová-la
        (a mesma regra de `_validate_connection_belongs_to_company`).
        """
        if not agent_id or not company_id:
            return None
        try:
            resultado = self.supabase.table("agents") \
                .select("id") \
                .eq("id", str(agent_id)) \
                .eq("company_id", str(company_id)) \
                .limit(1) \
                .execute()
            linhas = resultado.data or []
            return str(linhas[0]["id"]) if linhas else None
        except Exception as e:
            logger.error(f"[MCP OAuth] posse do agente não conferida: {e}")
            return None

    def _agente_dono_da_conexao(self, connection_id: str, company_id: str) -> Optional[str]:
        """O agente CONFIRMADO desta corretora que é dono da conexão, ou `None`."""
        if not connection_id or not company_id:
            return None
        try:
            resultado = self.supabase.table("agent_mcp_connections") \
                .select("agent_id") \
                .eq("id", str(connection_id)) \
                .limit(1) \
                .execute()
            linhas = resultado.data or []
        except Exception as e:
            logger.error(f"[MCP OAuth] dono da conexão não conferido: {e}")
            return None
        if not linhas:
            return None
        return self._agente_da_corretora(str(linhas[0].get("agent_id") or ""), company_id)

    # =========================================================================
    # CONEXÕES DO AGENTE (apenas tokens)
    # =========================================================================

    async def get_agent_connections(self, agent_id: str, company_id: str) -> list:
        """Lista conexões OAuth de um agente (tokens salvos).

        🔴 `company_id` é OBRIGATÓRIO: agente de outra corretora levanta
        `ConexaoNaoEncontrada`, a mesma resposta de agente que não existe.
        """
        agente = self._agente_da_corretora(agent_id, company_id)
        if not agente:
            raise ConexaoNaoEncontrada("agente não encontrado")
        try:
            result = self.supabase.table("agent_mcp_connections") \
                .select("id, mcp_server_id, access_token, is_active, connected_at, mcp_servers(name, display_name, oauth_provider)") \
                .eq("agent_id", agente) \
                .execute()

            connections = []
            for conn in (result.data or []):
                provider = conn.get("mcp_servers", {}).get("oauth_provider")
                connections.append({
                    "id": conn["id"],
                    "mcp_server_id": conn["mcp_server_id"],
                    "is_connected": bool(conn.get("access_token")),
                    "is_active": conn.get("is_active", False),
                    "connected_at": conn.get("connected_at"),
                    "mcp_server": conn.get("mcp_servers"),
                    "provider_configured": self.is_provider_configured(provider) if provider else False,
                })

            return connections
        except Exception as e:
            logger.error(f"[MCP OAuth] Error: {e}")
            return []

    # =========================================================================
    # URL GENERATION
    # =========================================================================

    async def get_authorization_url(
        self,
        provider: str,
        agent_id: str,
        mcp_server_id: str,
        company_id: str,
    ) -> Dict[str, Any]:
        """
        Gera URL de autorização OAuth usando credenciais da PLATAFORMA.

        🔴 SPEC-EXTRA-001.8 · FATIA 3: a corretora entra **dentro do `state`
        assinado**. O callback é a única rota deste módulo sem chave interna
        (o navegador do corretor chega nela vindo do Google/GitHub/Slack), então
        a corretora precisa viajar por um caminho que ninguém de fora consegue
        escrever — e a assinatura HMAC é esse caminho.
        """
        if provider not in self.provider_config:
            return {"error": f"Provider '{provider}' não suportado"}

        if not company_id:
            return {"error": "Corretora não informada"}

        # 🔴 A posse é confirmada AQUI também, não só na rota: quem gera o
        #    convite é quem assina, e assinar o agente alheio é o ataque.
        agente = self._agente_da_corretora(agent_id, company_id)
        if not agente:
            raise ConexaoNaoEncontrada("agente não encontrado")

        # Buscar credenciais da PLATAFORMA
        creds = self.get_platform_credentials(provider)
        if not creds:
            return {"error": f"Provider '{provider}' não configurado. Entre em contato com o suporte."}

        config = self.provider_config[provider]

        # State para CSRF protection + dados
        state_data = {
            "agent_id": agente,
            "company_id": str(company_id),
            "mcp_server_id": mcp_server_id,
            "provider": provider,
            "nonce": secrets.token_urlsafe(16),
        }
        state = self._encode_state(state_data)

        # Build URL
        redirect_uri = f"{self.redirect_base}/api/mcp/oauth/callback/{provider}"

        params = {
            "client_id": creds["client_id"],
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
        }

        # Provider-specific params
        if provider == "google":
            params["scope"] = " ".join(config["scopes"])
            params["access_type"] = "offline"
            params["prompt"] = "consent"
        elif provider == "github":
            params["scope"] = " ".join(config["scopes"])
        elif provider == "slack":
            params["scope"] = ",".join(config["scopes"])

        auth_url = f"{config['auth_url']}?{urlencode(params)}"

        logger.info(f"[MCP OAuth] URL gerada para {provider}, agent={agent_id}")
        return {"url": auth_url, "state": state}

    # =========================================================================
    # TOKEN EXCHANGE
    # =========================================================================

    async def exchange_code_for_tokens(
        self,
        provider: str,
        code: str,
        state: str,
    ) -> Dict[str, Any]:
        """
        Troca authorization code por tokens usando credenciais da PLATAFORMA.
        """
        if provider not in self.provider_config:
            return {"success": False, "error": f"Provider '{provider}' não suportado"}

        # Decode state
        state_data = self._decode_state(state)
        if not state_data:
            return {"success": False, "error": "State inválido"}

        agent_id = state_data.get("agent_id")
        mcp_server_id = state_data.get("mcp_server_id")
        company_id = state_data.get("company_id")

        if not agent_id or not mcp_server_id or not company_id:
            return {"success": False, "error": "State incompleto"}

        # 🔴 O PROVIDER DO CAMINHO TEM DE SER O DO CONVITE — 21/09/2026.
        #
        # 📊 Medido por leitura: `provider` já ia dentro do state e **nunca era
        # comparado** com o da URL. Um state legítimo de `google` reapresentado
        # em `/oauth/callback/github` gravava um token de GitHub na linha do
        # servidor do Google, com credenciais do GitHub — o dono acaba com uma
        # conexão que diz uma coisa e guarda outra.
        if str(state_data.get("provider") or "") != provider:
            logger.warning("[MCP OAuth] provider do state não é o do callback")
            return {"success": False, "error": "State inválido"}

        # 🔴 E A CORRETORA AINDA TEM DE SER DONA DO AGENTE NA HORA DA ESCRITA.
        #    O convite pode ter sido assinado minutos atrás; o que vale é agora.
        #    ⛔ Erro de banco → recusa (não conseguir provar não é provar).
        if not self._agente_da_corretora(str(agent_id), str(company_id)):
            logger.warning("[MCP OAuth] agente do state não é mais desta corretora")
            return {"success": False, "error": "State inválido"}

        # Buscar credenciais da PLATAFORMA
        creds = self.get_platform_credentials(provider)
        if not creds:
            return {"success": False, "error": "Credenciais da plataforma não configuradas"}

        config = self.provider_config[provider]
        redirect_uri = f"{self.redirect_base}/api/mcp/oauth/callback/{provider}"

        # Exchange code for tokens
        token_data = {
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "code": code,
            "redirect_uri": redirect_uri,
        }

        if provider == "google":
            token_data["grant_type"] = "authorization_code"

        try:
            # 🔴 Teto explícito (SPEC-EXTRA-001.8 §7.5): troca de code por token.
            async with httpx.AsyncClient(timeout=timeout_http()) as client:
                headers = {"Accept": "application/json"}
                response = await client.post(
                    config["token_url"],
                    data=token_data,
                    headers=headers,
                    timeout=30.0,
                )

                if response.status_code != 200:
                    logger.error(f"[MCP OAuth] Token error: {response.text}")
                    return {"success": False, "error": "Falha ao obter tokens"}

                tokens = response.json()

            # Parse tokens
            if provider == "slack":
                if not tokens.get("ok"):
                    return {"success": False, "error": tokens.get("error", "Slack error")}
                access_token = tokens.get("access_token")
                refresh_token = None
            else:
                access_token = tokens.get("access_token")
                refresh_token = tokens.get("refresh_token")

            if not access_token:
                return {"success": False, "error": "Access token não retornado"}

            # Calculate expiration
            expires_in = tokens.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            # Upsert connection with tokens
            connection_data = {
                "agent_id": agent_id,
                "mcp_server_id": mcp_server_id,
                "access_token": self.encryption.encrypt(access_token),
                "refresh_token": self.encryption.encrypt(refresh_token) if refresh_token else None,
                "token_expires_at": expires_at.isoformat(),
                "is_active": True,
                "connected_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            self.supabase.table("agent_mcp_connections").upsert(
                connection_data,
                on_conflict="agent_id,mcp_server_id"
            ).execute()

            logger.info(f"[MCP OAuth] ✅ Tokens salvos: {provider} para agent {agent_id}")
            return {
                "success": True,
                "provider": provider,
                "agent_id": agent_id,
            }

        except Exception as e:
            logger.error(f"[MCP OAuth] Exception: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # =========================================================================
    # TOKEN ACCESS (for MCP Gateway)
    # =========================================================================

    async def get_agent_oauth_tokens(
        self,
        agent_id: str,
        mcp_server_id: str,
    ) -> Optional[Dict[str, str]]:
        """Busca tokens OAuth de um agente (para uso pelo MCP Gateway)."""
        try:
            result = self.supabase.table("agent_mcp_connections") \
                .select("access_token, refresh_token, token_expires_at, mcp_servers(oauth_provider)") \
                .eq("agent_id", agent_id) \
                .eq("mcp_server_id", mcp_server_id) \
                .eq("is_active", True) \
                .single() \
                .execute()

            if not result.data or not result.data.get("access_token"):
                return None

            data = result.data
            access_token = self.encryption.decrypt(data["access_token"])
            refresh_token = self.encryption.decrypt(data["refresh_token"]) if data.get("refresh_token") else None
            expires_at = data.get("token_expires_at")
            provider = data.get("mcp_servers", {}).get("oauth_provider")

            # Verificar se token expirou ou vai expirar em 5 minutos
            if expires_at and refresh_token and provider:
                from datetime import datetime, timedelta
                try:
                    # Parse ISO datetime
                    exp_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    now = datetime.now(exp_time.tzinfo) if exp_time.tzinfo else datetime.utcnow()

                    if now >= exp_time - timedelta(minutes=5):
                        logger.info(f"[MCP OAuth] Token expirado/expirando, fazendo refresh para {provider}")
                        new_tokens = await self._refresh_access_token(
                            provider, refresh_token, agent_id, mcp_server_id
                        )
                        if new_tokens:
                            access_token = new_tokens["access_token"]
                            refresh_token = new_tokens.get("refresh_token", refresh_token)
                except Exception as e:
                    logger.error(f"[MCP OAuth] Erro ao verificar expiração: {e}")

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
            }
        except Exception as e:
            logger.error(f"[MCP OAuth] Error getting tokens: {e}")
            return None

    async def _refresh_access_token(
        self,
        provider: str,
        refresh_token: str,
        agent_id: str,
        mcp_server_id: str
    ) -> Optional[Dict[str, str]]:
        """Faz refresh do access token expirado."""
        try:
            creds = self.get_platform_credentials(provider)
            if not creds:
                return None

            config = self.provider_config.get(provider)
            if not config:
                return None

            # 🔴 Teto explícito (SPEC-EXTRA-001.8 §7.5): renovação do token.
            async with httpx.AsyncClient(timeout=timeout_http()) as client:
                if provider == "google":
                    response = await client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "client_id": creds["client_id"],
                            "client_secret": creds["client_secret"],
                            "refresh_token": refresh_token,
                            "grant_type": "refresh_token"
                        },
                        timeout=30.0
                    )
                else:
                    # Outros providers (implementar conforme necessário)
                    logger.warning(f"[MCP OAuth] Refresh não implementado para {provider}")
                    return None

                if response.status_code != 200:
                    logger.error(f"[MCP OAuth] Refresh failed: {response.text}")
                    return None

                tokens = response.json()
                new_access_token = tokens.get("access_token")
                new_refresh_token = tokens.get("refresh_token", refresh_token)  # Google pode retornar novo refresh
                expires_in = tokens.get("expires_in", 3600)

                if not new_access_token:
                    return None

                # Atualizar no banco
                from datetime import datetime, timedelta
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                self.supabase.table("agent_mcp_connections").update({
                    "access_token": self.encryption.encrypt(new_access_token),
                    "refresh_token": self.encryption.encrypt(new_refresh_token) if new_refresh_token else None,
                    "token_expires_at": expires_at.isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }).eq("agent_id", agent_id).eq("mcp_server_id", mcp_server_id).execute()

                logger.info(f"[MCP OAuth] ✅ Token refreshed para {provider}")
                return {
                    "access_token": new_access_token,
                    "refresh_token": new_refresh_token,
                }

        except Exception as e:
            logger.error(f"[MCP OAuth] Refresh error: {e}", exc_info=True)
            return None

    async def disconnect_agent(self, agent_id: str, mcp_server_id: str,
                               company_id: str) -> bool:
        """Remove tokens de um agente (desconecta).

        🔴 `company_id` é OBRIGATÓRIO, e o filtro leva o agente CONFIRMADO.
        """
        agente = self._agente_da_corretora(agent_id, company_id)
        if not agente:
            raise ConexaoNaoEncontrada("agente não encontrado")
        try:
            self.supabase.table("agent_mcp_connections") \
                .update({
                    "access_token": None,
                    "refresh_token": None,
                    "token_expires_at": None,
                    "is_active": False,
                    "updated_at": datetime.utcnow().isoformat(),
                }) \
                .eq("agent_id", agente) \
                .eq("mcp_server_id", mcp_server_id) \
                .execute()
            return True
        except Exception as e:
            logger.error(f"[MCP OAuth] Disconnect error: {e}")
            return False

    async def delete_connection(self, connection_id: str, company_id: str) -> bool:
        """Remove uma conexão completamente.

        🔴 Escrita DESTRUTIVA: o `id` sozinho nunca basta. A posse é confirmada
        aqui (dois saltos) e o `DELETE` sai com **os dois** filtros —
        `id` E `agent_id` confirmado. Assim, mesmo que a conexão troque de dono
        entre a pergunta e a ação (TOCTOU), o `DELETE` não pega nada.
        """
        agente = self._agente_dono_da_conexao(connection_id, company_id)
        if not agente:
            raise ConexaoNaoEncontrada("conexão não encontrada")
        try:
            self.supabase.table("agent_mcp_connections") \
                .delete() \
                .eq("id", connection_id) \
                .eq("agent_id", agente) \
                .execute()
            return True
        except Exception as e:
            logger.error(f"[MCP OAuth] Delete error: {e}")
            return False

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _encode_state(self, data: dict) -> str:
        """
        Codifica e assina o state OAuth usando HMAC-SHA256.
        Formato: base64(json_data).signature

        SECURITY: Requer APP_SECRET ou SECRET_KEY configurado.
        """
        secret = os.getenv("APP_SECRET") or os.getenv("SECRET_KEY")

        if not secret:
            logger.error("[MCP OAuth] CRITICAL: APP_SECRET or SECRET_KEY not configured")
            raise ValueError(
                "OAuth security requires APP_SECRET or SECRET_KEY environment variable. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )

        # 🔴 O RELÓGIO DENTRO DA ASSINATURA (SPEC-EXTRA-001.8 · FATIA 3).
        #    `iat` entra AQUI, e não em quem chama, para que nenhum state novo
        #    consiga nascer sem instante. Ele vai dentro do que é assinado —
        #    mexer nele invalida a assinatura.
        assinado = dict(data)
        assinado.setdefault("iat", int(time.time()))

        json_data = json.dumps(assinado, sort_keys=True)
        encoded_data = base64.urlsafe_b64encode(json_data.encode()).decode()

        # Criar assinatura HMAC-SHA256
        signature = hmac.new(
            secret.encode(),
            encoded_data.encode(),
            hashlib.sha256
        ).hexdigest()

        # Retornar dados + assinatura
        return f"{encoded_data}.{signature}"

    def _decode_state(self, state: str) -> Optional[dict]:
        """
        Decodifica e verifica assinatura do state OAuth.
        Retorna None se a assinatura for inválida.
        """
        try:
            # Separar dados da assinatura
            if "." not in state:
                logger.warning("[MCP OAuth] State sem assinatura (formato antigo ou inválido)")
                return None

            encoded_data, provided_signature = state.rsplit(".", 1)

            # Verificar assinatura
            secret = os.getenv("APP_SECRET") or os.getenv("SECRET_KEY")

            if not secret:
                logger.error("[MCP OAuth] CRITICAL: APP_SECRET or SECRET_KEY not configured")
                return None

            expected_signature = hmac.new(
                secret.encode(),
                encoded_data.encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(provided_signature, expected_signature):
                logger.warning("[MCP OAuth] Assinatura do state inválida - possível tentativa de manipulação")
                return None

            # Decodificar dados
            json_data = base64.urlsafe_b64decode(encoded_data.encode()).decode()
            dados = json.loads(json_data)
            if not isinstance(dados, dict):
                return None

            # 🔴 O CONVITE VENCE (SPEC-EXTRA-001.8 · FATIA 3).
            #
            # ⛔ State SEM `iat` é recusado, nunca "aceito por compatibilidade":
            # um state antigo é exatamente o que este relógio existe para barrar.
            # O preço é uma janela de poucos minutos, no deploy, em que um OAuth
            # já começado precisa ser reiniciado — ruidoso e de um clique.
            nascido = dados.get("iat")
            if not isinstance(nascido, int):
                logger.warning("[MCP OAuth] state sem instante de emissão — recusado")
                return None
            idade = int(time.time()) - nascido
            if idade < -60 or idade > STATE_VALIDADE_SEGUNDOS:
                logger.warning("[MCP OAuth] state fora da validade (%ss) — recusado", idade)
                return None

            return dados
        except Exception as e:
            logger.error(f"[MCP OAuth] Erro ao decodificar state: {e}")
            return None


# Singleton
_oauth_service: Optional[MCPOAuthService] = None


def get_mcp_oauth_service() -> MCPOAuthService:
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = MCPOAuthService()
    return _oauth_service
