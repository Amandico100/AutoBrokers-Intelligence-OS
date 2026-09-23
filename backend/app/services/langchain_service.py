"""
Serviço LangChain - Chat com IA com Multi-Tenancy e RAG + LangGraph
ADAPTADO PARA MULTI-AGENTES (Versão Final Estável)
"""

import asyncio
import logging
import time
from datetime import datetime
from collections.abc import Mapping
from typing import Any, Dict, Iterator, List, Optional, Tuple

from cachetools import LRUCache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Pool error handling for hot-reload recovery
try:
    from psycopg_pool import PoolClosed
except ImportError:
    PoolClosed = Exception  # Fallback if psycopg_pool not installed

try:
    from psycopg import OperationalError
except ImportError:
    OperationalError = Exception  # Fallback

# Services
from app.agents.guardrails import SmithGuardrail  # [NEW] Guardrails Import

# Models
from app.models.conversation_log import ConversationMetrics, RAGChunk

from .document_service import get_document_service
from .encryption_service import get_encryption_service
from .qdrant_service import get_qdrant_service

# Pool reset for hot-reload recovery (async version)
# Note: close_async_postgres_pool is imported locally in recovery code

logger = logging.getLogger(__name__)

# ===== GRAPH CACHE - LRU Cache com limite para evitar OOM =====
_graphs_cache: LRUCache = LRUCache(maxsize=500)


async def get_or_create_graph(
    company_id: str,
    agent_id: str,
    agent_config: dict,
    api_key: str,
    qdrant_service,
    supabase_client,
    enable_logging: bool = True,
):
    """
    Retorna o grafo cacheado ou cria um novo se não existir (ASYNC).
    A chave inclui updated_at para invalidação automática quando a config muda.
    """
    global _graphs_cache

    # PEGAR O UPDATED_AT PARA INVALIDAÇÃO AUTOMÁTICA
    updated_at = agent_config.get("updated_at", "")
    if hasattr(updated_at, "isoformat"):
        updated_at = updated_at.isoformat()

    # 🔥 A chave agora inclui a data de atualização
    # 🔴 SPEC-116: e a ROTA do papel. Trocar a rota no banco tem de mudar o
    # modelo SEM deploy — com o grafo cacheado só por `updated_at` do agente, o
    # modelo velho seguiria respondendo até o processo reiniciar. O resolvedor
    # tem cache de 60 s: a troca vale em até 1 minuto.
    try:
        from app.factories.llm_factory import LLMFactory

        _r = LLMFactory.resolver_para(agent_config, agent_config)
        rota = f"{_r.provider}/{_r.model}/{_r.effort}/v{_r.versao_da_rota}"
    except Exception as exc:  # noqa: BLE001 — quem constrói o grafo levanta o erro de verdade
        rota = f"sem-rota:{type(exc).__name__}"
    cache_key = f"{company_id}:{agent_id}:{updated_at}:{rota}"

    # LRUCache gerencia automaticamente a evição; invalidação centralizada cuida de versões antigas
    if cache_key in _graphs_cache:
        logger.debug(f"[GRAPH CACHE] Reusing cached graph for key {cache_key}")
        return _graphs_cache[cache_key]

    logger.info(
        f"[GRAPH CACHE] Creating new graph for key {cache_key} (Model: {agent_config.get('llm_model')})"
    )

    # Criar novo grafo passando as configs do AGENTE (ASYNC)
    from app.agents import create_agent_graph

    graph = await create_agent_graph(
        company_config=agent_config,
        agent_data=agent_config,
        api_key=api_key,
        qdrant_service=qdrant_service,
        supabase_client=supabase_client,
        company_id=company_id,
        enable_logging=enable_logging,
    )

    _graphs_cache[cache_key] = graph
    logger.info(f"[GRAPH CACHE] Graph cached. Total cached: {len(_graphs_cache)}")

    return graph


# Função para invalidar cache de um agente específico (chamar quando tools mudam)
def invalidate_agent_graph_cache(company_id: str, agent_id: str):
    """
    Invalida o cache do grafo de um agente específico (todas as versões).
    Usa list() para evitar RuntimeError: dictionary changed size during iteration.
    """
    global _graphs_cache
    prefix = f"{company_id}:{agent_id}:"
    keys_to_remove = [k for k in list(_graphs_cache.keys()) if k.startswith(prefix)]
    for key in keys_to_remove:
        try:
            del _graphs_cache[key]
            logger.info(f"[GRAPH CACHE] Invalidated cache for {key}")
        except KeyError:
            pass  # Já foi removido por outra thread ou LRU eviction


class _ProvedoresDoCatalogo(Mapping):
    """`provedor → [modelos]` DERIVADO do catálogo (SPEC-116 U5).

    Era uma lista escrita à mão — o 7º catálogo do repo (EVIDENCIAS/03 §3.0),
    que recusava `claude-sonnet-5` na UI enquanto a produção rodava nele. Agora
    é LEITURA de `llm_pricing` (cache de 60 s do Model Router): modelo de
    CONVERSA com lifecycle usável (APPROVED · CANDIDATE · DEPRECATED).
    BLOCKED/HISTORICAL somem daqui sozinhos. `openrouter` existe sempre (a
    lista dele é sincronizada do próprio OpenRouter).

    ⚠️ É um `Mapping` e não um `dict` congelado de propósito: `agent_config.py`
    importa o objeto uma vez e pergunta `in`/`.get`/`.keys()` a cada pedido.
    """

    def _agora(self) -> Dict[str, List[str]]:
        from app.factories.model_policy import LIFECYCLES_USAVEIS, catalogo

        saida: Dict[str, List[str]] = {"openrouter": []}
        for nome, linha in sorted(catalogo().items()):
            if linha.get("tipo") != "chat" or linha.get("lifecycle") not in LIFECYCLES_USAVEIS:
                continue
            saida.setdefault(str(linha.get("provider") or ""), []).append(nome)
        saida.pop("", None)
        return saida

    def __getitem__(self, chave: str) -> List[str]:
        return self._agora()[chave]

    def __iter__(self) -> Iterator[str]:
        return iter(self._agora())

    def __len__(self) -> int:
        return len(self._agora())


SUPPORTED_PROVIDERS = _ProvedoresDoCatalogo()

#: Os pacotes de SDK de MODELO. Um erro que nasce num deles é do provedor do
#: modelo, nunca do pool do Postgres — por mais que a mensagem diga "connection".
_PACOTES_DE_PROVEDOR_DE_MODELO = ("openai", "anthropic", "google", "groq", "httpx", "httpcore",
                                  "langchain_openai", "langchain_anthropic",
                                  "langchain_google_genai")


def _erro_do_provedor_de_modelo(exc: BaseException) -> bool:
    vistos: set = set()
    atual: Optional[BaseException] = exc
    while atual is not None and id(atual) not in vistos:
        vistos.add(id(atual))
        raiz = (type(atual).__module__ or "").split(".")[0]
        if raiz in _PACOTES_DE_PROVEDOR_DE_MODELO:
            return True
        atual = atual.__cause__ or atual.__context__
    return False


DEFAULT_SYSTEM_PROMPT = """Você é o AutoBrokers, copiloto operacional inteligente da corretora.
Seja profissional, claro e objetivo nas suas respostas.
Se não souber a resposta, diga que não sabe."""


class LangChainService:
    """Serviço ÚNICO para processar mensagens com LangChain (Multi-Agent + RAG)"""

    def __init__(self, openai_api_key: str, supabase_client):
        self.default_openai_key = openai_api_key
        self.supabase = supabase_client
        self.encryption_service = get_encryption_service()

        # SPEC-116 U8: o id do embedding vem da ROTA do papel `embedding`
        # (D-116-12: text-embedding-3-small KEEP — trocar exige reindexar).
        from app.factories.model_policy import resolver as _resolver_do_papel

        self.embeddings = OpenAIEmbeddings(
            model=_resolver_do_papel("embedding").model, openai_api_key=openai_api_key
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, length_function=len
        )

        self.qdrant = get_qdrant_service()
        self.document_service = get_document_service()

        logger.info("LangChain service initialized with Multi-Agent support")

    async def _get_raw_agent(
        self, company_id: str, agent_id: Optional[str] = None,
        required_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Busca o agente "cru" direto do banco para ter acesso às chaves criptografadas.
        NÃO usa AgentService para evitar que as chaves sejam mascaradas.

        Usa asyncio.to_thread() para não bloquear o event loop do FastAPI
        enquanto a query HTTP ao Supabase executa (~5-50ms).

        SPEC-063 Bloco A — `required_role` existe porque esta função escolhia
        **o agente ativo mais antigo da corretora**, sem olhar o papel. Quando o
        pareamento do WhatsApp gravava `agent_id` nulo (o ternário morto de
        `pairing_orchestrator`), quem respondia o SEGURADO era o primeiro por
        `created_at` — nas três corretoras de produção, o **core**, cujo prompt
        instrui a entregar CPF sem mascarar.

        A regra agora é: **papel pedido é papel entregue.** Se o papel certo não
        existe ou está desligado, devolve `None` — e quem chamou tem de calar.
        Devolver o agente errado é pior que não responder: o segurado recebe uma
        resposta de um agente que não foi feito para falar com ele.
        """
        try:
            papel = str(required_role or "").strip().lower() or None

            def _fetch():
                query = (
                    self.supabase.client.table("agents")
                    .select("*")
                    .eq("company_id", company_id)
                    .eq("is_active", True)
                )

                if agent_id:
                    query = query.eq("id", agent_id)
                elif papel:
                    query = query.eq("agent_role", papel)

                return query.order("created_at").limit(1).execute()

            result = await asyncio.to_thread(_fetch)

            if not (result.data and len(result.data) > 0):
                return None

            agente = result.data[0]

            # A trava final: mesmo com `agent_id` explícito, o papel tem de bater.
            # Um id apontando para o agente errado (dado velho, pareamento antigo)
            # não pode virar permissão para falar com o segurado.
            if papel:
                papel_do_agente = str(agente.get("agent_role") or "").strip().lower()
                if papel_do_agente != papel:
                    logger.error(
                        "[AGENTE] papel exigido=%s mas o agente %s da empresa %s tem papel=%s "
                        "— recusando. Ninguém responde com o papel errado.",
                        papel, agente.get("id"), company_id, papel_do_agente or "(vazio)",
                    )
                    return None

            return agente
        except Exception as e:
            logger.error(f"Error fetching raw agent: {e}")
            return None

    async def _analyze_image(
        self,
        image_url: str,
        *,
        company_id: str = None,
        agent_id: str = None,
        agent_data: Optional[Dict[str, Any]] = None,
        llm=None,
    ) -> Optional[str]:
        """A visão do `process_message` — o MESMO motor do webhook e do chat.

        🔴 SPEC-116 U8 (F3a): era um segundo cliente, por fora da fábrica, com
        default literal e `temperature=0.3` (Claude 5 → 400); em erro devolvia a
        frase "[Erro na análise de imagem]", que ia ao PROMPT como se fosse a
        descrição. Agora delega a `vision_service.describe_image` (papel
        `visao`, ledger incluso) e devolve None na falha. `llm=` é o ponto de
        injeção da bancada.
        """
        from app.services.vision_service import describe_image

        return await describe_image(
            image_url,
            company_id=company_id,
            agent_id=agent_id,
            agent_data=agent_data,
            purpose_hint="Agente de Suporte",
            llm=llm,
        )

    async def process_message(
        self,
        user_message: str,
        company_id: str,
        user_id: str,
        session_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        rag_context: Optional[str] = None,
        collect_metrics: bool = True,
        options: Optional[Dict[str, bool]] = None,
        image_url: Optional[str] = None,
        channel: str = "web",
        agent_id: Optional[str] = None,
        async_supabase_client=None,  # NEW: For async memory operations
        required_role: Optional[str] = None,
    ) -> Tuple[str, Optional[ConversationMetrics]]:
        metrics = (
            ConversationMetrics(start_time=time.time()) if collect_metrics else None
        )

        # SPEC-044: identidade do usuário POR REQUISIÇÃO (ContextVar) — o grafo
        # é cacheado/compartilhado; o CostCallbackHandler lê daqui na hora de
        # atribuir o custo. Nunca no construtor do grafo/LLM.
        try:
            from app.core.request_context import set_current_user_id

            set_current_user_id(user_id)
        except Exception:  # noqa: BLE001
            pass

        try:
            if not company_id:
                raise ValueError("company_id is required")

            # 1. Validar empresa
            company = self.supabase.get_company(company_id)
            if not company:
                raise ValueError(f"Company {company_id} not found")

            # 2. BUSCAR AGENTE (RAW)
            # SPEC-063 Bloco A — `required_role` viaja do chamador. O caminho do
            # WhatsApp exige "attendance"; sem esse papel ninguém responde ao
            # segurado, nem por omissão nem por fallback.
            agent = await self._get_raw_agent(company_id, agent_id, required_role=required_role)

            if not agent:
                if required_role:
                    logger.error(
                        "[CONFIG] empresa %s nao tem agente ATIVO com papel '%s' — "
                        "recusando responder (SPEC-063 A)", company_id, required_role,
                    )
                    raise ValueError(
                        f"AGENTE_DE_PAPEL_AUSENTE: nenhum agente ativo com papel '{required_role}'."
                    )
                logger.error(f"[CONFIG] No active agents found for company {company_id}")
                raise ValueError("CONFIG_REQUIRED: Nenhum Agente de IA encontrado.")

            # 3. Obter API Key do provedor que VAI responder
            # 🔴 SPEC-116: é o provedor da ROTA do papel (o Model Router), não o
            # gravado no agente — a rota pode ter trocado. Papel/provedor
            # desconhecido levanta aqui, antes de qualquer chamada.
            from app.core.utils import get_api_key_for_provider
            from app.factories.llm_factory import LLMFactory

            try:
                _resolvido = LLMFactory.resolver_para(agent, agent)
                api_key = get_api_key_for_provider(_resolvido.provider, _resolvido.model)
            except ValueError as e:
                logger.error(f"[CONFIG] {e}")
                raise

            # 3.5. GUARDRAILS CHECK
            # Verifica segurança antes de invocar qualquer LLM ou Tool
            security_settings = agent.get("security_settings", {})
            logger.info(f"[SECURITY] 🔍 Security enabled={security_settings.get('enabled', False)}")

            # Inicializa com o texto original
            final_message = user_message
            guardrail = None

            try:
                guardrail = SmithGuardrail(agent_config=agent, company_id=company_id)
                is_blocked, block_reason, sanitized_text = await guardrail.validate_input(user_message)

                if is_blocked:
                    logger.warning(f"[SECURITY] 🛡️ Message BLOCKED: {block_reason}")
                    if metrics:
                        metrics.end_time = time.time()
                    return block_reason, metrics

                # 🔥 CORREÇÃO: Usa texto sanitizado (pode ter PII mascarado)
                final_message = sanitized_text
                logger.debug("[SECURITY] ✅ Message passed guardrail")

            except Exception as gr_error:
                logger.error(f"[SECURITY] ⚠️ Guardrail exception: {gr_error}", exc_info=True)

                # 🔥 CORREÇÃO: Fail-close se configurado (default: True)
                fail_close = getattr(guardrail, 'fail_close', True) if guardrail else True
                if fail_close:
                    if metrics:
                        metrics.end_time = time.time()
                    return "Erro temporário de segurança. Por favor, tente novamente.", metrics
                # Se fail_close=False, continua com texto original

            # 4. Histórico — janela de 20 msgs fazia o ATENDENTE "esquecer" a
            # conversa de 1h atrás (incidente 2026-07-12: re-pediu CPF/nome do
            # mesmo cliente). 60 cobre horas de atendimento; env ajusta.
            if not conversation_history:
                try:
                    import os as _os

                    _hist_limit = int(_os.getenv("CHAT_HISTORY_WINDOW", "60") or 60)
                    conversation_history = self.supabase.get_conversation_history(
                        session_id=session_id, company_id=company_id, limit=_hist_limit
                    )
                except Exception as e:
                    logger.error(f"[CHAT] Failed to fetch conversation history: {e}")
                    conversation_history = []  # Fallback para lista vazia

            # Garante que não é None (alguns erros retornam None ao invés de levantar exceção)
            if conversation_history is None:
                conversation_history = []

            # 5. Obter Grafo (Configurado com o Agente) - ASYNC
            graph = await get_or_create_graph(
                company_id=company_id,
                agent_id=agent.get("id"),
                agent_config=agent,
                api_key=api_key,
                qdrant_service=self.qdrant,
                supabase_client=self.supabase.client,
                enable_logging=True,
            )

            # 6. Vision - Usa final_message (já sanitizado)
            enriched_message = final_message
            if image_url:
                from app.services.vision_service import imagem_ja_descrita

                # 🔴 UMA chamada de visão por foto (SPEC-116 U8). 📊 23/09/2026:
                # o webhook descrevia a foto do segurado (e gravava a marca no
                # texto) e ESTE ramo a descrevia de novo — 2 chamadas por foto e
                # o contexto visual duplicado no prompt. A marca no texto é a
                # prova de que a descrição já está aqui: reaproveita.
                if imagem_ja_descrita(final_message):
                    logger.info("[VISION] imagem já descrita neste turno — reaproveitada")
                else:
                    desc = await self._analyze_image(
                        image_url,
                        company_id=company_id,
                        agent_id=agent.get("id"),
                        agent_data=agent,
                    )
                    if desc:
                        enriched_message = (
                            f"{final_message}\n\n[CONTEXTO VISUAL]:\n{desc}"
                        )
                        logger.info("[VISION] ✅ Imagem analisada (papel visao)")
                    else:
                        logger.warning("[VISION] ⚠️ imagem sem descrição — segue só com o texto")

            # 7. Invocar Agente (LangGraph) - COM RETRY PARA POOL FECHADO
            from app.agents import invoke_agent
            from app.agents.nodes import abrir_marcador_do_turno, fechar_marcador_do_turno

            # 🔴 SPEC-116 U6b — o MARCADOR DO TURNO. O `tool_node` anota nele cada
            # ferramenta ANTES de executá-la. Se o turno cair depois disso, ele
            # NÃO é refeito: a ferramenta pode ter produzido efeito (mensagem,
            # acionamento, portal) e refazer o turno a faria de novo.
            marcador, _ficha_do_marcador = abrir_marcador_do_turno()
            try:
                result = await invoke_agent(
                    graph=graph,
                    user_message=enriched_message,
                    company_id=company_id,
                    user_id=user_id,
                    session_id=session_id,
                    company_config=agent,
                    options=options,
                    channel=channel,
                    supabase_client=self.supabase.client,
                    agent_id=agent.get("id"),
                    async_supabase_client=async_supabase_client,
                )
            except (PoolClosed, OperationalError, Exception) as e:
                # Detectar erro de pool fechado ou conexão perdida (SSL EOF)
                error_msg = str(e).lower()
                is_pool_error = (
                    isinstance(e, PoolClosed)
                    or isinstance(e, OperationalError)
                    or "pool" in error_msg
                    or "connection" in error_msg
                    or "ssl" in error_msg
                    or "eof" in error_msg
                )
                # 🔴 SPEC-116 U6b (EVIDENCIAS/03 F4): o erro de rede do SDK do
                # MODELO diz literalmente "Connection error." — e o turno inteiro
                # era refeito, ferramentas inclusive. Erro de provedor de modelo
                # não é pool: o SDK já repetiu a CHAMADA (max_retries) e a reserva
                # da rota já foi tentada no nó. E nenhum turno que já executou
                # ferramenta é refeito, por motivo nenhum.
                if is_pool_error and _erro_do_provedor_de_modelo(e):
                    logger.warning("[LANGCHAIN] erro do provedor do modelo (%s) — o turno NÃO "
                                   "é refeito (o SDK já repetiu a chamada)", type(e).__name__)
                    is_pool_error = False
                if is_pool_error and marcador.tools_iniciadas:
                    logger.error(
                        "[LANGCHAIN] ⛔ %s depois de %d ferramenta(s) no turno — NÃO refaço o "
                        "turno (efeito em dobro). Erro sobe.", type(e).__name__,
                        marcador.tools_iniciadas)
                    is_pool_error = False

                if is_pool_error:
                    logger.warning(
                        f"[LANGCHAIN] ♻️ Connection Pool closed. Resetting connection and retrying... Error: {e}"
                    )

                    # 1. Limpar cache global de grafos
                    global _graphs_cache
                    _graphs_cache.clear()
                    logger.info("[LANGCHAIN] 🗑️ Graph cache cleared")

                    # 2. 🔥 FORÇAR RESET DO POOL NO GRAPH.PY (Correção Crítica)
                    # Isso garante que o get_or_create_graph crie uma conexão nova
                    try:
                        from app.agents.graph import close_async_postgres_pool
                        await close_async_postgres_pool()
                        logger.info("[LANGCHAIN] 🔌 Async postgres pool reset")
                    except Exception as pool_err:
                        logger.warning(f"[LANGCHAIN] Error resetting pool: {pool_err}")

                    # 3. Recriar grafo (agora com pool novo) - ASYNC
                    graph = await get_or_create_graph(
                        company_id=company_id,
                        agent_id=agent.get("id"),
                        agent_config=agent,
                        api_key=api_key,
                        qdrant_service=self.qdrant,
                        supabase_client=self.supabase.client,
                        enable_logging=True,
                    )

                    # 4. Tentar novamente com novo grafo
                    result = await invoke_agent(
                        graph=graph,
                        user_message=enriched_message,
                        company_id=company_id,
                        user_id=user_id,
                        session_id=session_id,
                        company_config=agent,
                        options=options,
                        channel=channel,
                        supabase_client=self.supabase.client,
                        agent_id=agent.get("id"),
                        async_supabase_client=async_supabase_client,
                    )
                    logger.info("[LANGCHAIN] ✅ Retry successful after pool recovery")
                else:
                    raise e  # Outro erro, deixa subir
            finally:
                fechar_marcador_do_turno(_ficha_do_marcador)

            response_text = result["response"]

            # 🔥 SAFETY: Garantir que response sempre seja string
            # Modelos de raciocínio (o1, o3, GPT-5) podem retornar lista de blocos
            if isinstance(response_text, list):
                text_parts = []
                for block in response_text:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                response_text = "".join(text_parts)
            elif not isinstance(response_text, str):
                response_text = str(response_text) if response_text else ""

            if metrics:
                metrics.end_time = time.time()
                metrics.tokens_total = result.get("tokens_total", 0)

            return response_text, metrics

        except Exception as e:
            logger.error(f"[LANGCHAIN] Error: {str(e)}", exc_info=True)
            raise

    # ===== RAG METHODS (Mantidos para compatibilidade) =====

    def get_rag_context(
        self,
        query: str,
        company_id: str,
        top_k: int = 3,
        metrics: Optional[ConversationMetrics] = None,
        agent_id: Optional[str] = None,
        include_tenant_wide: bool = True,
        include_global: bool = False,
    ):
        try:
            results = self.search_documents(
                query,
                company_id,
                top_k,
                agent_id=agent_id,
                include_tenant_wide=include_tenant_wide,
                include_global=include_global,
            )
            if not results:
                return None, []

            context = "\n\n".join([f"[Trecho]\n{r.get('content')}" for r in results])
            rag_chunks = [
                RAGChunk(
                    content=r.get("content"),
                    document_id=r.get("document_id"),
                    score=r.get("score"),
                )
                for r in results
            ]
            return context, rag_chunks
        except Exception:
            return None, []

    def search_documents(
        self,
        query: str,
        company_id: str,
        top_k: int = 3,
        score_threshold: float = 0.4,
        agent_id: Optional[str] = None,
        include_tenant_wide: bool = True,
        include_global: bool = False,
    ) -> List[Dict[str, Any]]:
        try:
            query_embedding = self.embeddings.embed_query(query)
            results = self.qdrant.search_similar(
                company_id=company_id,
                query_embedding=query_embedding,
                top_k=top_k,
                agent_id=agent_id,
                include_tenant_wide=include_tenant_wide,
                exclude_metadata_document_types=["official_policy_document"],
                score_threshold=score_threshold,
            )
            if include_global:
                from .knowledge_scope import (
                    ORCAMENTO_GLOBAL,
                    build_global_search_kwargs,
                    merge_rag_results,
                    seguradora_da_pergunta,
                )

                # Mesma regra do `search_service`, e pelo mesmo motivo:
                # pergunta que nomeia UMA companhia nao pode ser respondida
                # pela regra de outra — e trecho de contrato nao disputa vaga
                # com carta destilada (SPEC-067 §6). Uma busca por faixa, com o
                # MESMO embedding ja gerado acima.
                #
                # Consertar so um dos dois caminhos globais seria deixar a
                # metade que ninguem esta olhando com o defeito antigo.
                carrier = seguradora_da_pergunta(query)
                # 🔴 `faceta` e `temas` NAO entram aqui como `must` — 15/08/2026.
                # SPEC-070 §5.1:304: "null passa em todo filtro, NUNCA ELIMINA.
                # Rotulo da COTA E PRIORIDADE". O leitor existe e esta testado;
                # o que falta e a forma certa de usa-lo — uma terceira linha de
                # ORCAMENTO_GLOBAL, que ACRESCENTA sem REMOVER. O motivo longo
                # esta em `search_service.py`, no mesmo ponto. Paridade mantida:
                # os dois caminhos globais estao desligados igualmente.
                for _rotulo, faixa, _cota in ORCAMENTO_GLOBAL:
                    global_results = self.qdrant.search_similar(
                        company_id=company_id,
                        query_embedding=query_embedding,
                        top_k=top_k,
                        score_threshold=score_threshold,
                        **build_global_search_kwargs(
                            carrier_slug=carrier, namespace=faixa),
                    )
                    results = merge_rag_results(results, global_results)

                # A COTA DA FACETA — uma busca A MAIS, nunca um corte. Espelho
                # exato de `search_service`: consertar so um dos dois caminhos
                # globais deixa a metade que ninguem olha com o defeito antigo.
                # O porque de ser cota e nao `must` esta em
                # `knowledge_scope.COTA_DE_FACETA`.
                from .knowledge_scope import (COTA_DE_FACETA, FAIXAS_DA_FACETA,
                                              faceta_da_pergunta)

                faceta_pedida = faceta_da_pergunta(query)
                if faceta_pedida:
                    extra = self.qdrant.search_similar(
                        company_id=company_id,
                        query_embedding=query_embedding,
                        top_k=COTA_DE_FACETA,
                        score_threshold=score_threshold,
                        **build_global_search_kwargs(
                            carrier_slug=carrier, namespace=FAIXAS_DA_FACETA,
                            faceta=faceta_pedida),
                    )
                    results = merge_rag_results(results, extra)
            return results
        except Exception as e:
            logger.error(f"[RAG] Error: {e}")
            return []

    def process_document(self, document_id: str, company_id: str, text: str) -> bool:
        try:
            self.document_service.update_document_status(document_id, "processing")
            chunks = self.text_splitter.split_text(text)
            if not chunks:
                raise ValueError("No chunks")

            embeddings = self.embeddings.embed_documents(chunks)

            self.qdrant.insert_embeddings(
                company_id=company_id,
                document_id=document_id,
                embeddings=embeddings,
                chunks=chunks,
                metadata={"processed_at": datetime.now().isoformat()},
            )

            self.document_service.update_document_status(
                document_id, "completed", chunks_count=len(chunks)
            )
            return True
        except Exception as e:
            logger.error(f"Doc process error: {e}")
            self.document_service.update_document_status(
                document_id, "failed", error_message=str(e)
            )
            return False


# ===== MÉTODOS AUXILIARES PARA API =====


def get_supported_providers() -> Dict[str, List[str]]:
    """Retorna providers e modelos suportados"""
    return SUPPORTED_PROVIDERS


def get_models_for_provider(provider: str) -> List[str]:
    """Retorna modelos disponíveis para um provider"""
    return SUPPORTED_PROVIDERS.get(provider, [])
