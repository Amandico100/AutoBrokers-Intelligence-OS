"""
Grafo do Agente LangGraph.
Monta o StateGraph com os nós e arestas.
"""

import asyncio
import json
import logging
from datetime import datetime
from functools import partial
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.core.prompts import (
    build_composite_prompt,
    expand_http_tool_variables,
    expand_mcp_tool_variables,
    expand_subagent_variables,
)
from app.core.utils import get_api_key_for_provider
from app.factories.llm_factory import LLMFactory
from app.services.agent_service import AgentService
from app.services.memory_service import MemoryService

from .capability_resolver import active_keys, resolve_active_capabilities
from .nodes import agent_node, log_node, should_continue, should_continue_after_tools, tool_node
from .state import AgentState
from .tools import HumanHandoffTool, KnowledgeBaseTool, MCPToolFactory, WebSearchTool

logger = logging.getLogger(__name__)

# === ASYNC POOL SINGLETON ===
# Pool is created once and reused. Checkpointer instances are lightweight.
_async_postgres_pool = None
_checkpointer_init_attempted = False


async def get_async_postgres_checkpointer():
    """
    Returns an AsyncPostgresSaver using a global AsyncConnectionPool.

    CRITICAL: Uses prepare_threshold=None for Supabase PgBouncer compatibility.
    The pool is opened lazily on first use.
    """
    global _async_postgres_pool, _checkpointer_init_attempted

    from langgraph.checkpoint.memory import MemorySaver

    from app.core import settings

    db_url = settings.SUPABASE_DB_URL

    if not db_url:
        logger.warning("[Checkpoint] DB_URL ausente, usando MemorySaver")
        return MemorySaver()

    # Check pool health
    if _async_postgres_pool is not None:
        try:
            if hasattr(_async_postgres_pool, "closed") and _async_postgres_pool.closed:
                logger.warning("[Checkpoint] Async pool encontrado FECHADO. Descartando...")
                _async_postgres_pool = None
                _checkpointer_init_attempted = False
        except Exception:
            logger.warning("[Checkpoint] Async pool em estado inconsistente. Descartando...")
            _async_postgres_pool = None
            _checkpointer_init_attempted = False

    # Create pool if needed
    if _async_postgres_pool is None:
        if _checkpointer_init_attempted:
            logger.debug("[Checkpoint] Init já tentado anteriormente, retornando MemorySaver")
            return MemorySaver()

        _checkpointer_init_attempted = True

        try:
            from psycopg.rows import dict_row
            from psycopg_pool import AsyncConnectionPool

            # CRÍTICO: prepare_threshold=None para Supabase Transaction Mode (PgBouncer)
            connection_kwargs = {
                "autocommit": True,
                "prepare_threshold": None,  # OBRIGATÓRIO para PgBouncer
                "row_factory": dict_row,
            }

            logger.info("[Checkpoint] 🔌 Criando novo AsyncConnectionPool...")
            _async_postgres_pool = AsyncConnectionPool(
                conninfo=db_url,
                min_size=5,
                max_size=20,
                max_lifetime=300,  # Recicla conexões após 5 min para evitar SSL EOF do servidor
                max_idle=60,       # Fecha conexões ociosas após 1 min
                open=False,  # Abrimos explicitamente abaixo
                kwargs=connection_kwargs,
                check=AsyncConnectionPool.check_connection,  # 🔒 Testa conexões antes de entregar
            )

            # Open the pool
            await _async_postgres_pool.open()
            logger.info("[Checkpoint] ✅ AsyncConnectionPool aberto (min=5, max=20)")

        except Exception as e:
            # Log seguro: Mostra o tipo do erro mas esconde os detalhes que podem ter a senha
            logger.error(f"[Checkpoint] ❌ Erro fatal ao criar AsyncPool: {type(e).__name__}")
            _async_postgres_pool = None
            return MemorySaver()

    # Create and setup the async saver
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        checkpointer = AsyncPostgresSaver(_async_postgres_pool)

        # Setup tables (idempotent - IF NOT EXISTS)
        await checkpointer.setup()

        return checkpointer

    except Exception as e:
        logger.error(f"[Checkpoint] Erro ao instanciar AsyncPostgresSaver: {e}")
        return MemorySaver()


async def close_async_postgres_pool():
    """
    Fecha o pool de conexões async e limpa referências globais.
    """
    global _async_postgres_pool, _checkpointer_init_attempted

    if _async_postgres_pool:
        try:
            await _async_postgres_pool.close()
            logger.info("[Checkpoint] AsyncConnectionPool fechado com sucesso")
        except Exception as e:
            logger.error(f"[Checkpoint] Erro ao fechar async pool: {e}")
        finally:
            _async_postgres_pool = None
            _checkpointer_init_attempted = False
  # Permite recriação imediata





# Removed in favor of LLMFactory


async def create_agent_graph(
    company_config: Dict[str, Any],
    api_key: str,
    qdrant_service,
    supabase_client,
    company_id: str,
    agent_data: Optional[Dict[str, Any]] = None,
    enable_logging: bool = True,
):
    """
    Cria o grafo do agente com as tools configuradas (ASYNC).

    Args:
        company_config: Configuração da empresa (provider, model, etc)
        api_key: API key descriptografada do LLM
        qdrant_service: Instância do QdrantService para RAG
        supabase_client: Cliente Supabase para logging
        company_id: ID da empresa (para RAG)
        enable_logging: Se deve salvar logs no final

    Returns:
        Grafo compilado pronto para .ainvoke() ou .astream_events()
    """
    logger.info(f"[Graph] Criando grafo async para company {company_id}")

    # Get agent_id early for cost tracking
    agent_id = agent_data.get("id") if agent_data else None

    # === 1. Identificar Provider e Key (Correção 401 Anthropic) ===
    # 1. Identificar qual provedor o Agente está configurado para usar
    # (Default para openai se não definido)
    provider = "openai"
    if agent_data and agent_data.get("llm_provider"):
        provider = agent_data.get("llm_provider")
    elif company_config.get("llm_provider"):
        provider = company_config.get("llm_provider")

    # === SELEÇÃO DE CHAVE: FORÇAR USO DE VARIÁVEL DE AMBIENTE ===
    selected_api_key = get_api_key_for_provider(provider)

    # 3. Criar o LLM do Agente com a chave correta
    llm = LLMFactory.create_llm(
        company_config=company_config,
        agent_data=agent_data,
        api_key=selected_api_key, # <--- Usando a chave selecionada
        company_id=company_id,
        agent_id=agent_id
    )

    # === 2. Cria as Tools ===
    # agent_id já foi definido acima
    collection_name = agent_data.get("collection_name") if agent_data else None

    kb_tool = KnowledgeBaseTool(
        company_id=company_id, agent_id=agent_id, collection_name=collection_name
    )

    # === SPEC-014 C-FIX-1: capabilities resolvidas pelo Registry (fonte ÚNICA de verdade) ===
    # Lê capabilities/bindings/entitlements + conexão + saúde do provider. Papel vazio NÃO recebe nada.
    _agent_role = (agent_data or {}).get("agent_role")
    active_caps = resolve_active_capabilities(supabase_client, str(company_id), _agent_role) if company_id else {}
    _active = active_keys(active_caps)
    logger.info(f"[Graph] 🧭 Capabilities ativas (role={_agent_role}): {sorted(_active)}")

    # Web Search (Tavily) — só quando a capability platform.web.search está ATIVA
    # (binding do papel + entitlement não desligado + TAVILY_API_KEY presente no backend).
    # SPEC-060 §35.6 — depois do cutover o Core NÃO recebe mais a tool antiga.
    # Ela continua existindo e funcionando; o que muda é que nenhuma resposta
    # passa a se apoiar numa string de busca sem fonte classificada. Quem
    # pesquisa é `pesquisar_na_web`, pelo Research Orchestrator.
    try:
        from ..services.research.legacy_adapter import (
            capacidades_ativas as _expandir_caps,
            web_search_ainda_e_autoridade as _web_legado)

        _active = _expandir_caps(_active)
        _legado_permitido = _web_legado()
    except Exception:  # noqa: BLE001
        _legado_permitido = True

    web_search_tool = (WebSearchTool()
                       if (_legado_permitido and "platform.web.search" in _active)
                       else None)

    # Onda 3 / SPEC-018 S2/S5: modo ESTRITO de autoridade (default OFF = comportamento
    # atual). Ligado, a autoridade real é a capability do Registry; tools_config vira
    # toggle visual por agente (human_handoff/csv_analytics).
    import os as _os
    from ..services.tool_authority import LEGACY_TOOL_CAPABILITIES, legacy_tool_allowed
    _strict_authority = str(_os.getenv("AUTHORITY_STRICT_MODE", "")).strip().lower() in ("1", "true", "yes", "on")

    # Human Handoff Tool - toggle no tools_config; capability manda em modo estrito (S5)
    tools_config = agent_data.get("tools_config", {}) if agent_data else {}
    allow_human_handoff = legacy_tool_allowed(
        "human_handoff", tools_config, _active,
        strict=_strict_authority, capability_key=LEGACY_TOOL_CAPABILITIES["human_handoff"],
    )

    # SPEC-063 Bloco B — para quem FALA COM O SEGURADO, devolver para humano não
    # é um extra que se liga numa tela: é o único caminho legítimo em SINISTRO,
    # em risco grave e quando não existe corredor para aquela seguradora.
    #
    # 📊 Em 02/08/2026 os agentes de atendimento tinham `tools_config = {}` — e
    # `ATTENDANCE_BASE_PROMPT` MANDA chamar humano nesses casos. O prompt
    # prometia o que a ferramenta não tinha como cumprir: o modelo dizia "vou
    # chamar um atendente" e não havia ferramenta para chamar.
    #
    # Prompt que promete e ferramenta que não existe é pior que nenhum dos dois.
    if not allow_human_handoff and str(_agent_role or "").lower() in ("attendance", "insured_external"):
        allow_human_handoff = True
        logger.info("[Graph] 🔔 HumanHandoffTool ligada por PAPEL (%s): o prompt "
                    "promete humano em sinistro e risco grave", _agent_role)

    # Unwrap para pegar o client real (tools usam .table() diretamente)
    real_supabase_client = getattr(supabase_client, 'client', supabase_client) if supabase_client else None

    human_handoff_tool = (
        HumanHandoffTool(supabase_client=real_supabase_client)
        if allow_human_handoff and real_supabase_client
        else None
    )

    if allow_human_handoff:
        logger.info(f"[Graph] 🔔 HumanHandoffTool habilitada para agente {agent_id}")

    # CSV Analytics Tool - toggle no tools_config; capability manda em modo estrito (S5)
    from .tools.csv_analytics_tool import CSVAnalyticsTool

    csv_analytics_enabled = legacy_tool_allowed(
        "csv_analytics", tools_config, _active,
        strict=_strict_authority, capability_key=LEGACY_TOOL_CAPABILITIES["csv_analytics"],
    )
    csv_analytics_tool = CSVAnalyticsTool(company_id=company_id, agent_id=agent_id) if csv_analytics_enabled else None

    if csv_analytics_enabled:
        logger.info(f"[Graph] 📊 CSVAnalyticsTool habilitada para agente {agent_id}")

    # Lista de tools disponíveis
    tools = [kb_tool]
    if web_search_tool:
        tools.append(web_search_tool)
    if human_handoff_tool:
        tools.append(human_handoff_tool)
    if csv_analytics_tool:
        tools.append(csv_analytics_tool)

    # === HTTP TOOL ROUTER ===
    from .tools.http_request import HttpToolRouter

    # SPEC-018 S2: em modo estrito, HTTP tools só entram com capability funcional
    # ativa no Registry — fim da autorização por tabela/menção de prompt.
    _http_allowed = (not _strict_authority) or ("tenant.http_tools.execute" in _active)

    raw_id = agent_data.get("id") if agent_data else None
    dynamic_agent_id = str(raw_id) if raw_id else None

    if not _http_allowed:
        logger.info("[Graph] 🔒 AUTHORITY_STRICT_MODE: HTTP tools bloqueadas (sem capability tenant.http_tools.execute)")
    if dynamic_agent_id and supabase_client and _http_allowed:
        # Unwrap para pegar o client real (HttpToolRouter usa .table() diretamente)
        real_client = getattr(supabase_client, 'client', supabase_client)
        http_router = HttpToolRouter(
            agent_id=dynamic_agent_id, supabase_client=real_client
        )
        tools.append(http_router)
        logger.info(
            f"[Graph] ✅ HttpToolRouter adicionado para agente {dynamic_agent_id}"
        )

    # === MCP TOOLS (Dinâmicas) ===
    if agent_id and supabase_client:
        # SPEC-018 S3: em modo estrito, cada servidor MCP exige a capability
        # tenant.mcp.<server> ativa no Registry; flag OFF = comportamento legado.
        try:
            from ..services.mcp_gateway_service import get_mcp_gateway
            from ..services.tool_authority import filter_mcp_tools_by_capability

            gateway = get_mcp_gateway()
            mcp_tools_config = await gateway.get_agent_mcp_tools(str(agent_id))
            _n_before = len(mcp_tools_config or [])
            mcp_tools_config = filter_mcp_tools_by_capability(
                mcp_tools_config, _active, strict=_strict_authority
            )
            if _strict_authority and _n_before and len(mcp_tools_config) < _n_before:
                logger.info(
                    f"[Graph] 🔒 AUTHORITY_STRICT_MODE: {_n_before - len(mcp_tools_config)} MCP tools "
                    "bloqueadas (sem capability tenant.mcp.<server>)"
                )

            if mcp_tools_config:
                mcp_tools = MCPToolFactory.create_tools_for_agent(
                    agent_id=str(agent_id),
                    mcp_tools_config=mcp_tools_config
                )

                if mcp_tools:
                    tools.extend(mcp_tools)
                    logger.info(
                        f"[Graph] ✅ {len(mcp_tools)} MCP tools criadas: "
                        f"{[t.name for t in mcp_tools]}"
                    )
        except Exception as e:
            logger.error(f"[Graph] Erro ao criar MCP tools: {e}")

    # === SUBAGENT DELEGATION TOOLS ===
    if agent_id and supabase_client:
        logger.info(f"[Graph] 🔍 Buscando delegações para orchestrator {agent_id}...")
        try:
            from .tools.subagent_tool import SubAgentTool

            real_client = getattr(supabase_client, 'client', supabase_client)
            delegations_response = (
                real_client.table("agent_delegations")
                .select("subagent_id, task_description, max_context_chars, timeout_seconds, max_iterations")
                .eq("orchestrator_id", str(agent_id))
                .eq("is_active", True)
                .execute()
            )

            if delegations_response.data:
                # ✅ FIX N+1: Buscar TODOS os subagentes em uma única query
                sub_ids = [d["subagent_id"] for d in delegations_response.data]
                sub_agents_response = (
                    real_client.table("agents")
                    .select("*")
                    .in_("id", sub_ids)
                    .execute()
                )
                sub_agents_map = {
                    str(s["id"]): s for s in (sub_agents_response.data or [])
                }

                # Montar dicionário com dados completos
                available_subagents = {}
                for delegation in delegations_response.data:
                    sub_id = delegation["subagent_id"]
                    sub_data = sub_agents_map.get(sub_id)
                    if sub_data:
                        available_subagents[sub_id] = {
                            "subagent_data": sub_data,
                            "task_description": delegation["task_description"],
                            "max_context_chars": delegation.get("max_context_chars", 2000),
                            "timeout_seconds": delegation.get("timeout_seconds", 30),
                            "max_iterations": delegation.get("max_iterations", 5),
                        }

                if available_subagents:
                    subagent_tool = SubAgentTool(
                        available_subagents=available_subagents,
                        company_id=str(company_id),
                        company_config=company_config,
                        supabase_client=supabase_client,
                    )
                    tools.append(subagent_tool)
                    logger.info(
                        f"[Graph] 🤖 SubAgentTool criada com {len(available_subagents)} especialistas: "
                        f"{list(available_subagents.keys())}"
                    )
        except Exception as e:
            # Tabela pode não existir ainda (pré-migration)
            logger.warning(f"[Graph] ⚠️ SubAgent delegation ERRO: {e}")

    # === CAPABILITY-GOVERNED TOOLS (SPEC-014 C-FIX-1) — anexa SÓ o que está ATIVO no Registry ===
    # Governado pelo resolver (papel + entitlement + conexão). Papel vazio não recebe nada.
    try:
        if company_id and _active:
            # SPEC-057 — leitura profunda (Firecrawl). Só entra com a capability
            # ativa E a chave configurada: tool que sempre responde "não
            # configurado" gasta token em toda invocação e ensina o modelo a
            # tentar de novo. Sem chave, a lista volta vazia e nada é anexado.
            if "platform.web.scrape" in _active:
                from .tools.deep_web import ferramentas_de_leitura_profunda
                tools.extend(ferramentas_de_leitura_profunda(
                    company_id=str(company_id), supabase=supabase_client))
            if "control_plane.read" in _active:
                from .tools.control_plane_tool import ControlPlaneReadTool
                tools.append(ControlPlaneReadTool(company_id=str(company_id), supabase_client=supabase_client))
            if "operational.infocap.policy_lookup.read" in _active:
                from .tools.infocap_tool import InfocapPolicyLookupTool
                tools.append(InfocapPolicyLookupTool(company_id=str(company_id), agent_role=str(_agent_role or "core")))
                # Ferramenta DEDICADA de placa/veículo (fix 15/07): caminho
                # explícito CPF→/itens quando o corretor pede a placa direto.
                from .tools.vehicle_tool import VehicleLookupTool
                tools.append(VehicleLookupTool(company_id=str(company_id)))
            # SPEC-017 P5: acionamento de seguradora — SÓ o atendente externo.
            # Dry-run enquanto INSURER_DISPATCH_LIVE estiver fechado (S17-6).
            # Capability formal (operational.insurer.dispatch) entra na Onda 3.
            if str(_agent_role or "").strip().lower() == "attendance":
                from .tools.insurer_dispatch_tool import InsurerDispatchTool
                tools.append(InsurerDispatchTool(company_id=str(company_id), supabase_client=supabase_client))
            # F2: Chat Principal cria/gerencia ROTINAS por conversa (Claude-Rotinas).
            if str(_agent_role or "core").strip().lower() in ("core", "", "core(legado)"):
                from .tools.routine_tools import CreateRoutineTool, ListRoutinesTool, ManageRoutineTool
                tools.append(CreateRoutineTool(company_id=str(company_id), supabase_client=supabase_client))
                tools.append(ListRoutinesTool(company_id=str(company_id), supabase_client=supabase_client))
                tools.append(ManageRoutineTool(company_id=str(company_id), supabase_client=supabase_client))
                # SPEC-040 Onda 2 (Missão B): visão operacional do Core — leitura
                # determinística de acionamentos (escopo da corretora) e dos mapas
                # do Atlas (estrutura global, sem dado de cliente).
                from .tools.operations_tools import AtlasRoutesTool, OperationsSummaryTool
                tools.append(OperationsSummaryTool(company_id=str(company_id)))
                tools.append(AtlasRoutesTool())
            # SPEC-020 P3 / SPEC-065 — portal_action: abrir atendimento de vidros.
            #
            # DUAS chaves soltam esta ferramenta, e a diferenca entre elas e o que
            # separava o Atendente do portal ha quatro semanas:
            #
            #   tenant.portal.execute                    -> generica. core, auxiliary.
            #   operational.portal.assistance.prepare    -> o corredor. attendance.
            #
            # 📊 Medido em 04/08/2026: `tenant.portal.execute` esta desligada para
            # `attendance` desde a SPEC-054 Bloco C, com o motivo na propria linha:
            # "SPEC-053 5.2 - Atendimento externo nao recebe ferramenta generica".
            #
            # E esta CERTO. `portal.execute` — entre em qualquer portal e faca
            # qualquer coisa — e a ferramenta generica que a 053 proibe a quem
            # conversa com desconhecidos no WhatsApp. Afrouxar aquilo seria dar a um
            # agente exposto a texto de estranho a chave de todos os portais.
            #
            # Mas `portal_action` NAO e generica: jornada fixa (`vidros_lanternas` /
            # `abrir_atendimento`), parametros montados no servidor a partir da
            # InfoCap, `confirm=False` cravado. E um CORREDOR DEFINIDO — que e o que
            # a 053 5.2 manda usar ("corredores definidos; menor privilegio").
            #
            # E o corredor ja tinha chave, ja ligada para o Atendente desde sempre:
            # `assistance.prepare` (preparar, com requires_approval_before_submit) e
            # `assistance.request` (enviar, com requires_approval). O portao e que
            # nunca aprendeu a conferi-la — exigia a chave generica para soltar uma
            # ferramenta especifica.
            #
            # Nao era conflito entre SPEC-053 e SPEC-020. Era o portao lendo a chave
            # errada, e a discussao canonica inteira nasceu desse engano.
            #
            # 🔴 P-90, 04/08/2026 — AS DUAS CHAVES NÃO SÃO DO MESMO PAPEL, E ISSO
            # IMPORTA MAIS DO QUE PARECIA.
            #
            # 📊 Medido no Supabase dcajcvlzcjbmyapmklil em 04/08/2026:
            #
            #     SELECT agent_role, capability_key, enabled FROM capability_bindings
            #      WHERE capability_key LIKE '%portal%';
            #
            #   · `operational.portal.assistance.prepare` → SÓ `attendance`.
            #   · `tenant.portal.execute`                 → `core` e `auxiliary`
            #                                               (desligada para attendance).
            #
            # Ou seja: o CHAT INTERNO da corretora (papel `core`) também recebe
            # `portal_action`. Ele não passa pelo portão `attendance_agent_active`
            # do webhook — ele responde ao corretor, não ao segurado.
            #
            # 📊 Hoje isso alcança UMA corretora: `tenant.portal.execute` exige
            # conexão (`requires_connection=true`, provider `portal_worker`), e só
            # a Resulta (04b5cdbc…) tem linha em `portal_accounts`. O core dela
            # está ativo. Logo, o chat interno da Resulta consegue enfileirar um
            # `portal_jobs` de `abrir_atendimento` HOJE.
            #
            # Por que isso NÃO foi fechado aqui, e sim subordinado:
            # `portal_tool._arun` pergunta `attendance_agent_active` ANTES de montar
            # os params, e é essa resposta que vira `confirm`. Com o agente de
            # atendimento desligado, o job do chat interno nasce `confirm=False` e
            # para no 80% — exatamente o que ele já fazia. Nada foi aberto por este
            # caminho, e nada passa a ser. Quando o Founder ligar o agente, este
            # caminho passa a poder abrir pedido de verdade também, e isso está
            # escrito no relatório em vez de escondido numa capability.
            #
            # Fechar a chave do `core` é uma decisão de produto (o corretor pode
            # abrir um chamado de vidro pelo chat?), não de execução — e mudá-la
            # exige escrever no banco. Fica registrado, não decidido sozinho.
            if _active & {"operational.portal.assistance.prepare", "tenant.portal.execute"}:
                from .tools.portal_tool import PortalActionTool
                tools.append(PortalActionTool(company_id=str(company_id), supabase_client=supabase_client))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[Graph] ⚠️ Capability tools (SPEC-014) não anexadas: {e}")

    # === SPEC-057 — o corretor pede o relatório por conversa ===
    # É aqui que a fundação das 054–057 vira algo que ele vê: "me faz o
    # panorama do mês" devolve uma peça com a marca da corretora dele.
    if company_id and supabase_client and str(_agent_role or "core").strip().lower() in ("core", "", "core(legado)"):
        try:
            from .tools.report_tool import ferramenta_de_relatorio
            tools.extend(ferramenta_de_relatorio(
                company_id=str(company_id), supabase=supabase_client))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[Graph] ⚠️ ferramenta de relatório não anexada: {e}")

        # SPEC-058 — a Factory pelo chat. "Queria que alguém acompanhasse os
        # boletos" devolve uma PROPOSTA do formato certo, nunca uma criação:
        # Auxiliar criado no meio de uma conversa vira coisa que ninguém pediu
        # e ninguém sabe desligar.
        try:
            from .tools.factory_tool import ferramenta_de_automacao
            tools.extend(ferramenta_de_automacao(
                company_id=str(company_id), supabase=supabase_client))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[Graph] ⚠️ ferramenta da Factory não anexada: {e}")

        # SPEC-064 Bloco G — o chat manda o Auxiliar trabalhar AGORA.
        #
        # Era a decisão D9 do plano de execução — "o corretor pede no chat e
        # recebe ali mesmo, em vez de esperar a rotina" — e nenhuma SPEC a
        # implementou: a 064 cobria criar e editar, e executar caiu entre elas.
        #
        # Não é executor novo: enfileira `bridge.auxiliary.execute`, o MESMO
        # workflow da Rotina. Muda só `source_type='chat'`, para o histórico
        # distinguir "rodou porque eu pedi" de "rodou sozinho".
        # Sem `user_id` aqui, pelo mesmo motivo das ferramentas de inteligência
        # logo abaixo: **o grafo é cacheado por (empresa, agente)** e reusado em
        # muitas conversas. Amarrar um usuário na montagem faria o trabalho de
        # uma pessoa nascer no nome de outra. Quem pediu é resolvido no turno.
        try:
            from .tools.auxiliary_run_tool import AuxiliaryRunTool
            tools.append(AuxiliaryRunTool(
                supabase_client=supabase_client,
                company_id=str(company_id)))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[Graph] ⚠️ ferramenta de executar Auxiliar não anexada: {e}")

        # SPEC-059 — "o que precisa da minha atenção hoje?" deixa de ser uma
        # pergunta que o modelo responde por conta própria. As quatro
        # ferramentas devolvem o que está gravado, com evidência, e a capability
        # `tenant.intelligence.read` continua sendo a autoridade: sem ela ativa
        # no Registry, nada é anexado.
        # SPEC-060 — pesquisa com fonte. A capability é a autoridade: sem
        # `platform.research.search` ativa no Registry, nada é anexado. O
        # alias de `platform.web.search` já foi expandido acima, então quem
        # tinha busca continua tendo.
        try:
            if "platform.research.search" in _active:
                from .tools.research_tool import ferramentas_de_pesquisa
                tools.extend(ferramentas_de_pesquisa(
                    company_id=str(company_id), supabase=supabase_client))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[Graph] ⚠️ ferramentas de pesquisa não anexadas: {e}")

        try:
            if "tenant.intelligence.read" in _active:
                from .tools.intelligence_tool import ferramentas_de_inteligencia
                # Sem `user_id`: o grafo é cacheado por (empresa, agente) e
                # reusado em muitas conversas — amarrar um usuário aqui faria
                # o briefing de uma pessoa vazar para a sessão de outra. O
                # escopo pessoal é aplicado nas APIs, onde há sessão.
                tools.extend(ferramentas_de_inteligencia(
                    company_id=str(company_id), supabase=supabase_client))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[Graph] ⚠️ ferramentas de inteligência não anexadas: {e}")

    # Bind final (Standard + Dinâmicas)
    llm_with_tools = llm.bind_tools(tools)

    # === 3. Define os Nós ===
    # SPEC-057 §I — o cutover para o Tool Gateway acontece POR TURNO, dentro do
    # nó do agente, e não aqui. O grafo é cacheado por (empresa, agente) e
    # reusado em muitas conversas: escolher ferramenta na montagem fixaria a
    # mesma lista para todo mundo, que é exatamente o que o progressive
    # disclosure da SPEC-056 existe para desfazer. Além disso, aqui não há
    # mensagem do usuário — e sem ela não há Skill a resolver.
    agent_fn = partial(
        agent_node,
        llm_with_tools=llm_with_tools,
        llm_base=llm,
        tools_base=tools,
        cutover_ctx={
            "supabase_client": supabase_client,
            "company_id": str(company_id) if company_id else None,
            "agent_role": str(_agent_role or "core"),
            "active_capabilities": active_caps,
        },
    )
    tool_fn = partial(tool_node, tools=tools)
    log_fn = partial(log_node, supabase_client=supabase_client)

    # === 4. Monta o Grafo ===
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", agent_fn)
    workflow.add_node("tools", tool_fn)

    if enable_logging:
        workflow.add_node("log", log_fn)

    # === 5. Define as Arestas ===
    workflow.add_edge(START, "agent")

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": "log" if enable_logging else END},
    )

    workflow.add_conditional_edges(
        "tools",
        should_continue_after_tools,
        {"agent": "agent", "end": "log" if enable_logging else END},
    )

    if enable_logging:
        workflow.add_edge("log", END)

    # === 6. Compila com ASYNC Checkpointer ===
    checkpointer = await get_async_postgres_checkpointer()
    graph = workflow.compile(checkpointer=checkpointer)

    logger.info("[Graph] Grafo criado com sucesso (AsyncPostgresSaver ativo)")

    return graph


# === RAG PREFETCH (41C.1.2) ===
# Mensagens triviais (saudações/curtas) não justificam consultar a base.
_RAG_TRIVIAL_MESSAGES = {
    "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite",
    "ok", "okay", "obrigado", "obrigada", "valeu", "tchau",
    "blz", "beleza", "e aí", "e ai",
}

# Sinais de intenção de conhecimento (pergunta sobre base/documento/seguro).
_RAG_INTENT_KEYWORDS = (
    "qual", "como", "onde", "quando", "documento", "base", "rag",
    "palavra-chave", "palavra chave", "política", "politica",
    "procedimento", "seguradora", "apólice", "apolice", "cobertura",
    "sinistro", "assistência", "assistencia", "cotação", "cotacao",
)


def should_prefetch_rag(user_message: str) -> bool:
    """
    Decide deterministicamente se vale a pena pré-buscar a base de conhecimento
    antes do LLM (recall safety — o LLM pode não emitir o tool_call sozinho).
    Pura, sem I/O. Não loga conteúdo.
    """
    msg = (user_message or "").strip().lower()
    if not msg:
        return False
    if msg in _RAG_TRIVIAL_MESSAGES:
        return False
    if any(kw in msg for kw in _RAG_INTENT_KEYWORDS):
        return True
    # Perguntas mais longas tendem a precisar de contexto recuperado.
    return len(msg) > 25



# ===================================================================== #
# SPEC-063 Blocos S e G — o que o atendente já sabe, e como se conduz
# ===================================================================== #

# Teto do bloco de conduta, em caracteres.
#
# Os playbooks têm de 6 a 10 KB cada. Colar um inteiro empurraria o RAG e o
# histórico para fora do contexto — o agente ganharia conduta e perderia o
# conhecimento com que responde. A SPEC-063 G exige teto explícito, e é este.
_TETO_DA_CONDUTA = 2600


def _slots_obrigatorios_do_caso(ficha: dict) -> list:
    """Os dados que ESTE caso exige, segundo o corredor que o executa.

    A lista não é inventada aqui: vem de `corridor_playbooks`, que é a
    autoridade sobre o que a URA daquela seguradora vai pedir. Se não der para
    resolver o corredor, devolve lista vazia — e a ficha simplesmente não
    mostra "o que falta". Vazio é honesto; lista chutada faria o agente cobrar
    do cliente um dado que ninguém vai usar.
    """
    try:
        from app.services.corridor_playbooks import (
            missing_slots_for_subservice,
            resolve_playbook_ref,
        )
    except Exception:  # noqa: BLE001
        return []

    ramo = str(ficha.get("ramo") or "").strip().lower()
    servico = str(ficha.get("servico") or "").strip().lower()
    seguradora = str(ficha.get("seguradora") or "").strip().lower()
    if not (ramo and servico and seguradora):
        return []
    try:
        ref = resolve_playbook_ref(seguradora, ramo, "whatsapp")
        if not ref:
            return []
        # `missing_slots_for_subservice` devolve o que falta dado o que já há;
        # com dicionário vazio, ele devolve a lista COMPLETA de obrigatórios.
        return list(missing_slots_for_subservice(ref, servico, {}) or [])
    except Exception as exc:  # noqa: BLE001
        logger.debug("[FICHA] slots do caso indisponíveis (%s)", type(exc).__name__)
        return []


async def _conduta_do_caso(supabase_client, mensagem: str) -> str:
    """A conduta destilada de atendimentos humanos reais, para ESTE tipo de caso.

    📊 16 playbooks (12 ativos), gerados por claude-opus-5 a partir de 297
    atendimentos humanos, com objetivo, verificações prévias, ficha de coleta,
    acolhimento e sensibilidade. Todos órfãos: lidos apenas pelo juiz que os
    aprova e pela tela do admin que os conta.

    O ramo e o serviço são inferidos pelo classificador que o Atlas já usa
    (`infer_ramo_servico`) — determinístico, sem chamada de modelo. Um
    classificador novo aqui seria um segundo jeito de responder a mesma
    pergunta, e os dois divergiriam com o tempo.
    """
    import asyncio

    texto = str(mensagem or "").strip()
    if len(texto) < 8:
        return ""
    try:
        from app.services.atlas.templater import infer_ramo_servico

        ramo, servico = infer_ramo_servico([], texto)
    except Exception:  # noqa: BLE001
        return ""
    if not (ramo and servico):
        return ""

    cli = supabase_client.client if hasattr(supabase_client, "client") else supabase_client
    if cli is None:
        return ""

    def _q(r: str):
        return (cli.table("conduct_playbooks")
                .select("content, ramo, servico, version")
                .eq("ramo", r).eq("servico", servico).eq("status", "active")
                .order("version", desc=True).limit(1).execute())

    try:
        res = await asyncio.to_thread(_q, ramo)
        # O RAMO `outro` É O GENÉRICO DO SERVIÇO — 07/08/2026.
        #
        # 📊 `outro/sinistro` foi destilado de 629 atendimentos (nota 74,5) e
        # `outro/consulta` de 254. Ambos ATIVOS, e nenhum dos dois era lido:
        # esta função infere o ramo por palavra no texto e nunca devolve
        # "outro" — não existe frase que diga "meu seguro é do ramo outro".
        #
        # Eles não são lixo nem erro de rotulagem: são a conduta daquele
        # serviço quando o ramo não muda o que se faz. Como segunda tentativa
        # eles são exatamente isso — o que vale quando não há conduta do ramo
        # específico. Nunca ANTES: `auto/sinistro` continua ganhando de
        # `outro/sinistro` quando a conversa é de carro.
        if not res.data and ramo != "outro":
            res = await asyncio.to_thread(_q, "outro")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CONDUTA] leitura falhou (%s)", type(exc).__name__)
        return ""
    if not res.data:
        return ""

    c = res.data[0].get("content") or {}
    if not isinstance(c, dict):
        return ""

    # O cabeçalho anuncia o playbook QUE VEIO, não o que foi procurado: com o
    # fallback acima os dois podem diferir, e dizer "(AUTO)" sobre uma conduta
    # gravada como genérica seria dar ao modelo uma precisão que ela não tem.
    ramo_lido = str(res.data[0].get("ramo") or ramo)
    rotulo = "GERAL" if ramo_lido == "outro" else ramo_lido.upper()
    linhas = [f"=== 🎧 COMO SE CONDUZ UM ATENDIMENTO DE {servico.upper()} "
              f"({rotulo}) ===",
              "Destilado de atendimentos humanos reais desta corretora. "
              "Não é script: é o jeito que funciona."]

    if c.get("objetivo"):
        linhas.append(f"Objetivo: {str(c['objetivo']).strip()}")

    def _item(it: object) -> str:
        """Um item da conduta, no menor texto que o modelo precisa ler.

        🔴 ISTO ERA `str(it)` — E COMIA UM TERÇO DO ORÇAMENTO DE CONTEXTO.
        =================================================================
        Um item de `ficha_coleta` é um dicionário. `str()` num dicionário
        devolve a sintaxe do Python inteira:

            {'campo': 'Placa do veiculo', 'quando': 'na abertura', 'como_pedir':
             'Confirma pra mim...', 'ja_temos_na_apolice': True}

        📊 Medido em 07/08/2026: **163 caracteres, dos quais 67 (41%) são
        aspas, chaves e nomes de chave** que o modelo não precisa ler. Em 12
        itens são **804 caracteres desperdiçados** — quase um terço do
        `_TETO_DA_CONDUTA` de 2.600.

        E o que ficava de fora não era detalhe: 📊 nos SEIS playbooks em
        rascunho, o bloco renderizado passava de 4.600 chars e a truncagem caía
        **dentro da ficha** — `acolhimento`, `sensibilidade` e `encerramento`
        **nunca chegavam ao prompt em nenhum deles**. Toda regra escrita só em
        `sensibilidade` — inclusive "nunca prometa valor" — era decorativa.

        `ja_temos_na_apolice` não vai no texto de propósito: ele governa COMO a
        frase foi escrita (confirmação em vez de pergunta), e essa decisão já
        está dentro do `como_pedir`. Repetir a flag gastaria contexto para
        dizer ao modelo algo que a própria frase já diz.
        """
        if isinstance(it, dict):
            campo = str(it.get("campo") or "").strip()
            quando = str(it.get("quando") or "").strip()
            frase = str(it.get("como_pedir") or "").strip()
            partes = campo or "item"
            if quando:
                partes += f" — {quando}"
            return f"{partes}: \"{frase}\"" if frase else partes
        return str(it).strip()

    def _lista(chave: str, titulo: str, teto: int) -> None:
        itens = c.get(chave)
        if isinstance(itens, list) and itens:
            linhas.append(titulo)
            for it in itens[:teto]:
                linhas.append(f"  · {_item(it)}")
        elif isinstance(itens, str) and itens.strip():
            linhas.append(f"{titulo} {itens.strip()}")

    _lista("pre_checks", "Confira ANTES de prometer qualquer coisa:", 5)
    # 🔴 A ORDEM É POR CRITICIDADE, e não por ordem de leitura humana.
    #
    # O bloco é cortado em `_TETO_DA_CONDUTA` quando estoura, e o corte cai
    # sempre no FIM. Então o fim tem de ser o que menos machuca perder.
    #
    # 📊 Antes, a ordem era ficha → acolhimento → sensibilidade → encerramento,
    # e a ficha sozinha estourava o teto nos seis playbooks medidos: as
    # proibições de `sensibilidade` — inclusive "nunca prometa valor" — nunca
    # chegavam ao modelo. A regra mais importante do playbook era a primeira a
    # ser cortada.
    #
    # Agora: o que CONFERIR e o que NÃO FAZER vêm antes das perguntas. Perder o
    # fim da ficha custa uma pergunta que o modelo improvisa; perder a
    # sensibilidade custa uma promessa que a corretora não pode cumprir.
    _lista("sensibilidade", "Cuidado humano (vale mais que qualquer pergunta):", 3)
    _lista("acolhimento", "Como abrir:", 2)
    _lista("ficha_coleta", "Colete de uma vez só (não peça em conta-gotas):", 12)
    _lista("encerramento", "Como fechar:", 2)

    bloco = chr(10).join(linhas)
    if len(bloco) > _TETO_DA_CONDUTA:
        # Cortar no fim de uma linha, não no meio de uma frase: conduta cortada
        # na metade de uma orientação é pior que conduta ausente.
        bloco = bloco[:_TETO_DA_CONDUTA].rsplit(chr(10), 1)[0]
        bloco += chr(10) + "  (...conduta resumida para nao empurrar o conhecimento para fora)"
    logger.info("[CONDUTA] injetada | %s/%s | %d chars", ramo, servico, len(bloco))
    return bloco


async def _build_initial_state(
    user_message: str,
    company_id: str,
    user_id: str,
    session_id: str,
    company_config: Dict[str, Any],
    options: Dict[str, Any] = None,
    supabase_client=None,
    agent_id: str = None,
) -> tuple:
    """
    Constrói o estado inicial.
    AUTH SIMPLIFICADA: Usa chaves globais do ambiente (.env).
    """
    # === 1. RECUPERAR DADOS DO AGENTE ===
    real_agent_data = None
    system_prompt_source = None

    if agent_id:
        try:
            agent_service = AgentService()
            # AgentService agora retorna objeto simples (sem chaves)
            agent_response = agent_service.get_agent_by_id(agent_id)

            if agent_response:
                real_agent_data = agent_response.model_dump()
                logger.info(f"[Graph] Agente carregado: {real_agent_data.get('name')}")

                system_prompt_source = real_agent_data.get("agent_system_prompt")
                pass  # llm_provider is used later by create_agent_graph, not here
        except Exception as e:
            logger.error(f"[Graph] Erro ao carregar agente: {e}")

    # NOTE: LLM creation removed - it was dead code.
    # The graph already creates its own LLM in create_agent_graph() with proper callbacks.
    # This function only builds the initial STATE, not the LLM.

    # === SPEC-052 Lote 3 — plano de contexto ===
    # Decide ANTES de recuperar. Contexto irrelevante nao e neutro: ele compete
    # com o relevante pela atencao do modelo, e custa token em toda mensagem.
    try:
        from .context_assembly import CONTEXT_ASSEMBLY_ATIVO, planejar_para

        from .context_assembly import modo as _ca_modo

        _plano_ctx = planejar_para(user_message)
        _ca_ativo = CONTEXT_ASSEMBLY_ATIVO()
        logger.info("[Context] modo=%s | %s | fontes=%s | esforco=%s",
                    _ca_modo(), _plano_ctx.motivo,
                    _plano_ctx.fontes or "nenhuma", _plano_ctx.esforco)
    except Exception as exc:  # noqa: BLE001
        # Falha no planejador nunca pode impedir o atendimento: sem plano, o
        # comportamento antigo continua valendo.
        logger.warning("[Context] planejador indisponivel (%s)", type(exc).__name__)
        _plano_ctx, _ca_ativo = None, False

    # === MEMORY SYSTEM V2 (ASYNC) ===
    memory_context = ""
    _quer_memoria = (not _ca_ativo) or (_plano_ctx is None) or any(
        f.startswith("memoria") for f in _plano_ctx.fontes)
    if not _quer_memoria:
        logger.info("[Memory] pulada pelo plano de contexto (%s)", _plano_ctx.intencao.tipo)
    if supabase_client and _quer_memoria:
        try:
            real_client = supabase_client.client if hasattr(supabase_client, "client") else supabase_client
            memory_service = MemoryService(real_client)
            memory_context = await memory_service.build_memory_context_async(
                user_id=user_id,
                company_id=company_id,
                current_query=user_message,
                max_facts=10,
                max_summaries=3,
                agent_id=agent_id,
            )
            if memory_context:
                logger.info(f"[Memory] 🧠 Contexto carregado: {len(memory_context)} chars.")
        except Exception as e:
            logger.error(f"[Memory] ❌ Erro ao carregar contexto: {e}")

    # === PROMPT CONSTRUCTION ===
    base_instructions = (
        system_prompt_source
        or company_config.get("agent_instructions")
        or "Seja um assistente útil."
    )

    # === CONTEXT PACKAGE (42A6) ===
    # Bloco declarativo de papel (role/audience/policies), antes das instruções base.
    # Complementa — não substitui — o agent_system_prompt. Se o agente não tiver
    # campos declarativos, nada muda (backward-compatible). Entra no static_prompt
    # (cacheável) por ser estável por agente.
    try:
        from .context_package import (
            get_agent_field,
            render_context_package_block,
            should_render_context_package,
        )

        if real_agent_data and should_render_context_package(real_agent_data):
            cp_block = render_context_package_block(real_agent_data)
            if cp_block:
                base_instructions = f"{cp_block}\n\n{base_instructions}"
                logger.info(
                    "[ContextPackage] present=true "
                    f"role={get_agent_field(real_agent_data, 'agent_role')} "
                    f"audience={get_agent_field(real_agent_data, 'agent_audience')} "
                    f"blueprint_version={get_agent_field(real_agent_data, 'blueprint_version')}"
                )
            else:
                logger.info("[ContextPackage] present=false")
        else:
            logger.info("[ContextPackage] present=false")
    except Exception as e:  # noqa: BLE001 — nunca pode quebrar o chat
        logger.warning(f"[ContextPackage] erro ignorado: {type(e).__name__}")

    # === HTTP TOOLS ===
    allowed_http_tools = []
    if agent_id and supabase_client:
        try:
            real_client = supabase_client.client if hasattr(supabase_client, "client") else supabase_client
            response = (
                real_client.table("agent_http_tools")
                .select("name, description, method, parameters")
                .eq("agent_id", str(agent_id))
                .eq("is_active", True)
                .execute()
            )
            http_tools = response.data or []
            if http_tools:
                base_instructions, allowed_http_tools = expand_http_tool_variables(
                    base_instructions, http_tools
                )
        except Exception:
            pass

    # === MCP TOOLS ===
    allowed_mcp_tools = []
    if agent_id and supabase_client:
        try:
            from ..services.mcp_gateway_service import get_mcp_gateway
            gateway = get_mcp_gateway()
            mcp_tools = await gateway.get_agent_mcp_tools(str(agent_id))

            if mcp_tools:
                base_instructions, allowed_mcp_tools = expand_mcp_tool_variables(
                    base_instructions, mcp_tools
                )
                logger.info(f"[Graph] MCP tools mencionadas no prompt: {allowed_mcp_tools}")
        except Exception as e:
            logger.error(f"[Graph] Erro ao carregar MCP tools: {e}")

    # === SUBAGENT DELEGATION PROMPT EXPANSION ===
    # Otimizado: usa IN query para buscar todos os subagents de uma vez
    if agent_id and supabase_client:
        try:
            real_client = supabase_client.client if hasattr(supabase_client, "client") else supabase_client
            delegations_response = (
                real_client.table("agent_delegations")
                .select("subagent_id, task_description")
                .eq("orchestrator_id", str(agent_id))
                .eq("is_active", True)
                .execute()
            )
            if delegations_response.data:
                # Buscar TODOS os subagentes em uma única query (em vez de N queries individuais)
                sub_ids = [d["subagent_id"] for d in delegations_response.data]
                sub_agents_response = (
                    real_client.table("agents")
                    .select("id, name")
                    .in_("id", sub_ids)
                    .execute()
                )
                sub_agents_map = {
                    str(s["id"]): s for s in (sub_agents_response.data or [])
                }

                delegations_with_data = []
                for d in delegations_response.data:
                    sub_data = sub_agents_map.get(d["subagent_id"])
                    if sub_data:
                        delegations_with_data.append({
                            "subagent_data": sub_data,
                            "subagent_id": d["subagent_id"],
                            "task_description": d["task_description"],
                        })

                if delegations_with_data:
                    subagent_prompt = expand_subagent_variables(delegations_with_data)
                    base_instructions += subagent_prompt
                    logger.info(
                        f"[Graph] 🤖 Prompt expandido com {len(delegations_with_data)} especialistas"
                    )
        except Exception as e:
            logger.warning(f"[Graph] ⚠️ SubAgent prompt expansion ERRO: {e}")

    # Prompt ESTÁTICO (instruções + tools) - será cacheado.
    # SPEC-013 P0: base por PAPEL — Core = copiloto inteligente; attendance = evidence-first.
    _agent_role_for_prompt = (real_agent_data or {}).get("agent_role") if real_agent_data else None
    # SPEC-017 identidade: nome configurado pela corretora (config.display_name
    # tem prioridade sobre agents.name). Sem hard-code de plataforma.
    _agent_cfg = (real_agent_data or {}).get("config") or {}
    _agent_display_name = str(
        (_agent_cfg.get("display_name") if isinstance(_agent_cfg, dict) else None)
        or (real_agent_data or {}).get("name")
        or ""
    )
    # Identidade multi-tenant: o atendente se apresenta como "<nome>, da
    # <CORRETORA>" (feedback founder 12/07) — nome da empresa vem do cadastro.
    _company_display_name = ""
    try:
        if company_id and supabase_client is not None:
            _c = supabase_client.table("companies").select("company_name, legal_name").eq(
                "id", str(company_id)).limit(1).execute()
            if _c.data:
                _company_display_name = str(_c.data[0].get("company_name") or _c.data[0].get("legal_name") or "")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[Graph] company name lookup falhou: {type(e).__name__}")
    static_prompt = build_composite_prompt(
        base_instructions,
        agent_role=_agent_role_for_prompt,
        agent_display_name=_agent_display_name,
        company_display_name=_company_display_name,
    )

    # Prompt DINÂMICO (memória) - NÃO será cacheado
    #
    # 🔴 A HORA MORA AQUI, e não no `static_prompt`. Ela ficava no bloco
    # cacheado e o destruía a cada 60 segundos — o cache casa por prefixo
    # exato e o TTL é de 5 minutos. 📊 07/08/2026: só 2,3% de 4.509 chamadas
    # aproveitaram cache; pagava-se a escrita (~1,25×) e não se colhia a
    # leitura (~0,1×). A DATA continua no bloco estável (muda uma vez por dia).
    from app.core.prompts import data_e_hora_agora

    dynamic_context = f"\n\n{data_e_hora_agora()}"
    if memory_context:
        dynamic_context += f"\n\n=== 🧠 MEMÓRIA ===\n{memory_context}\n=== FIM DA MEMÓRIA ==="

    options = options or {}
    allow_web = False
    if real_agent_data:
        allow_web = real_agent_data.get("allow_web_search", False)
    else:
        allow_web = company_config.get("allow_web_search", False)

    if options.get("web_search") and not allow_web:
        options["web_search"] = False
    elif options.get("web_search"):
        dynamic_context += "\n\n🌐 MODO WEB ATIVO: Use a tool 'web_search'."

    # === RAG PREFETCH DETERMINÍSTICO (41C.1.2) ===
    # Recall safety: a base é apenas uma tool e o LLM pode responder sem chamá-la.
    # Aqui pré-buscamos o conhecimento do agente e injetamos no contexto dinâmico.
    # Não substitui a tool 'knowledge_base_search' (que segue ativa) — é aditivo.
    rag_prefetch_content = ""
    rag_prefetch_chunks = []
    rag_prefetch_time_ms = 0
    rag_prefetch_strategy = None
    rag_prefetch_score = None
    try:
        _quer_rag = (
            any(f.startswith("rag") or f == "normativo" for f in _plano_ctx.fontes)
            if (_ca_ativo and _plano_ctx is not None)
            else should_prefetch_rag(user_message)
        )
        if not _quer_rag and _ca_ativo:
            logger.info("[RAG Prefetch] pulado pelo plano (%s)", _plano_ctx.intencao.tipo)
        if _quer_rag:
            is_hyde = True
            if real_agent_data is not None:
                is_hyde = bool(real_agent_data.get("is_hyde_enabled", True))
            logger.info(
                f"[RAG Prefetch] searching company={company_id} agent={agent_id}"
            )
            from ..services.search_service import get_search_service

            _search_service = get_search_service()
            # SPEC-013 P0 + SPEC-017 S17-7: Core E o atendente externo usam o
            # conhecimento global curado além do privado da corretora (Founder:
            # atendente nunca "burro"). Auxiliar segue só com o privado (Onda 4).
            _role_for_rag = (real_agent_data or {}).get("agent_role") if real_agent_data else None
            _rag_include_global = str(_role_for_rag or "").strip().lower() in ("", "core", "attendance")
            rag_result = await asyncio.to_thread(
                _search_service.smart_search,
                company_id,
                user_message,
                str(agent_id) if agent_id else None,
                is_hyde,
                # SPEC-064 Bloco J — o comentario aqui dizia "OFF p/ attendance"
                # e a linha logo acima INCLUI 'attendance' na lista. O codigo
                # esta certo: o atendente PRECISA do conhecimento global — sao
                # as 8.916 cartas destiladas de atendimento real. Era o
                # comentario que estava velho, e comentario que contradiz o
                # codigo ao lado e pior que comentario nenhum: ele faz a
                # proxima pessoa "consertar" o que funciona.
                _rag_include_global,  # ON para core E attendance; OFF para auxiliar
            )
            if rag_result and rag_result.get("found") and rag_result.get("content"):
                rag_prefetch_content = rag_result.get("content") or ""
                rag_prefetch_chunks = rag_result.get("chunks") or []
                rag_prefetch_time_ms = int(rag_result.get("search_time_ms") or 0)
                rag_prefetch_strategy = rag_result.get("strategy")
                rag_prefetch_score = rag_result.get("max_score")
                logger.info(
                    "[RAG Prefetch] found=true "
                    f"chunks={len(rag_prefetch_chunks)} "
                    f"score={rag_prefetch_score} strategy={rag_prefetch_strategy}"
                )
            else:
                logger.info("[RAG Prefetch] no result")
        else:
            logger.info("[RAG Prefetch] skipped: greeting/short")
    except Exception as e:  # noqa: BLE001 — prefetch nunca pode quebrar o chat
        logger.warning(f"[RAG Prefetch] erro ignorado: {type(e).__name__}")

    if rag_prefetch_content:
        dynamic_context += (
            "\n\n=== 📚 CONTEXTO RECUPERADO DA BASE DE CONHECIMENTO ===\n"
            f"{rag_prefetch_content}\n"
            "=== FIM DO CONTEXTO RECUPERADO ===\n\n"
            "INSTRUÇÕES SOBRE O CONTEXTO RECUPERADO:\n"
            "- Se a resposta estiver no contexto recuperado, responda com base nele.\n"
            "- Não diga que não encontrou se o contexto recuperado contém a resposta.\n"
            "- Use a informação recuperada com precisão.\n"
            "- Não invente informações fora do contexto quando a pergunta for sobre "
            "base/documento/procedimento interno."
        )

    # === AUXILIARY AWARENESS (42A7) ===
    # Só para o Core e quando a mensagem indica intenção sobre auxiliares/automação.
    # Bloco compacto e seguro (sem config/segredo) — entra no dynamic_context.
    try:
        from .auxiliary_context import (
            load_tenant_auxiliaries_for_context,
            render_auxiliary_context_block,
            should_load_auxiliary_context,
        )

        if supabase_client and should_load_auxiliary_context(real_agent_data, user_message):
            aux_client = supabase_client.client if hasattr(supabase_client, "client") else supabase_client
            aux_rows = load_tenant_auxiliaries_for_context(aux_client, company_id)
            if aux_rows:
                aux_block = render_auxiliary_context_block(aux_rows)
                if aux_block:
                    dynamic_context += f"\n\n{aux_block}"
                    logger.info(f"[AuxContext] loaded count={len(aux_rows)} company={company_id}")
                else:
                    logger.info("[AuxContext] skipped reason=empty_block")
            else:
                logger.info("[AuxContext] skipped reason=no_active_auxiliaries")
        else:
            logger.info("[AuxContext] skipped reason=not_core_or_no_trigger")
    except Exception as e:  # noqa: BLE001 — awareness nunca pode quebrar o chat
        logger.warning(f"[AuxContext] error ignored type={type(e).__name__}")

    # ------------------------------------------------------------------ #
    # SPEC-063 Blocos S e G — a ficha do atendimento e a conduta destilada.
    #
    # (helpers logo abaixo, em _slots_obrigatorios_do_caso e _conduta_do_caso)
    #
    # Só para quem fala com o SEGURADO. O copiloto interno do corretor não tem
    # ficha de atendimento nem conduta de assistência: são outra conversa.
    # ------------------------------------------------------------------ #
    # `_agent_role_for_prompt`, e não `_agent_role`.
    #
    # 🔴 03/08/2026: esta linha nasceu com `_agent_role`, que é local de
    # `create_agent_graph` — **outra função**. Aqui virava `LOAD_GLOBAL` sem
    # global correspondente: `NameError` em TODA chamada de
    # `_build_initial_state`, para TODO papel. O chat inteiro caía, e não só a
    # ficha e a conduta que esta linha guarda.
    #
    # E o teste passava porque afirmava a linha **como string**, não executando
    # a função. É o §9.1 do CLAUDE.md uma camada acima: build verde não prova
    # que a aplicação sobe — **teste verde não prova que o prompt monta**.
    if str(_agent_role_for_prompt or "").lower() in ("attendance", "insured_external"):
        # --- S · O QUE JÁ SE SABE ---------------------------------------
        # A memória do que já foi perguntado era a janela de 60 mensagens.
        # Passou disso, o CPF que o cliente deu no começo sumia — e o código
        # registra que isso JÁ aconteceu em produção. Num sinistro real, isso é
        # pedir o CPF de novo a quem acabou de bater o carro.
        try:
            from app.services.attendance_ficha import bloco_para_o_prompt, carregar

            _cli = supabase_client.client if hasattr(supabase_client, "client") else supabase_client
            _ficha = await carregar(_cli, str(company_id), str(session_id or ""))
            _obrig = _slots_obrigatorios_do_caso(_ficha)
            _bloco_ficha = bloco_para_o_prompt(_ficha, _obrig)
            if _bloco_ficha:
                dynamic_context += f"\n\n{_bloco_ficha}"
                logger.info("[FICHA] injetada | fase=%s | confirmados=%d",
                            _ficha.get("fase"), len(_ficha.get("confirmados") or {}))
        except Exception as e:  # noqa: BLE001 — a ficha nunca derruba o turno
            logger.warning("[FICHA] não injetada (%s)", type(e).__name__)

        # --- G · COMO SE CONDUZ ESTE TIPO DE ATENDIMENTO ------------------
        # 📊 16 playbooks de conduta, 12 ativos, destilados por claude-opus-5 de
        # 297 atendimentos HUMANOS reais, com ficha de coleta de até 19 campos.
        # Eram lidos por exatamente duas coisas: o juiz que os aprova e a tela
        # do admin que os conta. Nenhuma palavra chegava ao turno.
        #
        # As "fases" que o agente seguia eram seis parágrafos escritos à mão.
        try:
            _bloco_conduta = await _conduta_do_caso(supabase_client, user_message)
            if _bloco_conduta:
                dynamic_context += f"\n\n{_bloco_conduta}"
        except Exception as e:  # noqa: BLE001
            logger.warning("[CONDUTA] não injetada (%s)", type(e).__name__)

    # Prompt completo para uso geral
    composite_prompt = static_prompt + dynamic_context

    messages = [SystemMessage(content=composite_prompt), HumanMessage(content=user_message)]

    initial_state = {
        "messages": messages,
        "company_id": company_id,
        "user_id": user_id,
        "session_id": session_id,
        "company_config": company_config,
        "agent_data": real_agent_data,
        "system_prompt": composite_prompt,
        "static_prompt": static_prompt,      # 🔥 NEW: Parte cacheável
        "dynamic_context": dynamic_context,  # 🔥 NEW: Parte dinâmica
        "rag_context": rag_prefetch_content,
        "rag_chunks": rag_prefetch_chunks,
        "rag_search_time_ms": rag_prefetch_time_ms,
        "search_strategy": rag_prefetch_strategy,
        "retrieval_score": rag_prefetch_score,
        "tools_used": [],
        "policy_response_contract": None,
        "llm_response_time_ms": 0,
        "tokens_input": 0,
        "tokens_output": 0,
        "tokens_total": 0,
        "final_response": None,
        "allowed_http_tools": allowed_http_tools,
        "internal_steps": [],  # SubAgent delegation logs
    }

    config = {"configurable": {"thread_id": f"{company_id}:{session_id}"}}

    return initial_state, config, real_agent_data


async def invoke_agent(
    graph,
    user_message: str,
    company_id: str,
    user_id: str,
    session_id: str,
    company_config: Dict[str, Any],
    options: Dict[str, Any] = None,
    channel: str = "web",
    supabase_client=None,
    agent_id: str = None,
    async_supabase_client=None,  # NEW: AsyncClient for non-blocking memory operations
) -> Dict[str, Any]:
    """
    Execute the agent graph asynchronously.

    Uses _build_initial_state helper for state initialization,
    then runs graph.ainvoke() for async execution.
    """
    # Build state (now async)
    initial_state, config, real_agent_data = await _build_initial_state(
        user_message,
        company_id,
        user_id,
        session_id,
        company_config,
        options,
        supabase_client,
        agent_id,
    )

    # === LANGSMITH TRACING (Multi-Tenant) ===
    # Injeta metadados para isolamento por company/agent no dashboard
    from app.core.langsmith_setup import get_langsmith_config, is_langsmith_enabled

    if is_langsmith_enabled():
        ls_config = get_langsmith_config(
            company_id=company_id,
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            channel=channel,
        )
        config["metadata"] = ls_config["metadata"]
        config["tags"] = ls_config["tags"]
        config["run_name"] = ls_config["run_name"]
        logger.debug(f"[LangSmith] Trace configurado: {ls_config['run_name']}")

    logger.info(
        f"[Agent] Invoking graph async for thread {config['configurable']['thread_id']} with agent {agent_id or 'DEFAULT'}"
    )

    # Execute graph asynchronously (now using AsyncPostgresSaver)
    result = await graph.ainvoke(initial_state, config)

    # Extrai resposta final
    final_response = result.get("final_response", "")
    logger.info(
        f"[Agent] final_response no state: {final_response[:100] if final_response else 'VAZIO'}"
    )

    # Se não veio no state, busca na última mensagem
    if not final_response:
        from langchain_core.messages import AIMessage

        for msg in reversed(result.get("messages", [])):
            logger.debug(
                f"[Agent] Checando mensagem: type={type(msg).__name__}, hasContent={hasattr(msg, 'content')}"
            )
            if isinstance(msg, AIMessage):
                content = getattr(msg, "content", None)
                if content:
                    # 🔥 FIX: Tratamento para conteúdo em lista (Reasoning Models)
                    # Modelos como o1, o3 e GPT-5 com reasoning retornam lista de blocos
                    if isinstance(content, list):
                        text_parts = []
                        for block in content:
                            # Pega apenas blocos de texto, ignora 'reasoning'
                            if isinstance(block, dict) and block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                            elif isinstance(block, str):
                                text_parts.append(block)
                        final_response = "".join(text_parts)
                    else:
                        # Conteúdo normal (string)
                        final_response = str(content)

                    if final_response.strip():
                        logger.info(
                            f"[Agent] Encontrada resposta final: {final_response[:100]}..."
                        )
                        break

    # Garante que seja string para evitar erro no Pydantic
    if not isinstance(final_response, str):
        final_response = str(final_response) if final_response else ""

    logger.info(
        f"[Agent] Resposta final extraída: {final_response[:100] if final_response else 'VAZIO!!!'}"
    )

    # === MEMORY SYSTEM V2 - SUMMARIZATION TRIGGER (REFATORADO ASYNC) ===
    # Verifica se deve agendar sumarização (totalmente ASYNC/NON-BLOCKING)
    if supabase_client or async_supabase_client:
        try:
            # Prioriza o cliente async se existir, senão usa o sync
            client_to_use = async_supabase_client if async_supabase_client else supabase_client
            memory_service = MemoryService(client_to_use)

            # ✅ CORREÇÃO: Usar get_memory_settings_async com agent_id
            # Isso garante que não bloqueamos o loop, independente do cliente
            settings = await memory_service.get_memory_settings_async(agent_id)

            # Conta APENAS mensagens do usuário (HumanMessage), não AI/System
            all_messages = result.get("messages", [])
            human_messages_count = sum(
                1 for m in all_messages if isinstance(m, HumanMessage)
            )

            logger.info(
                f"[Memory] Trigger check: mode={settings.get('web_summarization_mode')}, "
                f"threshold={settings.get('web_message_threshold')}, "
                f"human_messages={human_messages_count}, channel={channel}"
            )

            # SPEC-059 / SPEC-052 Lote 4 — LEIA ANTES DE MEXER.
            #
            # `last_message_at=datetime.now()` faz a inatividade ser SEMPRE
            # zero neste ponto: estamos no meio do turno. Isso não é descuido —
            # é a consequência de o gatilho viver aqui. Nenhum modo baseado em
            # TEMPO (`session_end`, `inactivity`) pode disparar durante a
            # conversa, porque ninguém sabe, no meio dela, que ela acabou.
            #
            # Este caminho cobre apenas os modos por CONTAGEM. O fechamento por
            # inatividade é do varredor `memory_fabric.fechar_sessoes_inativas`,
            # no laço de manutenção do Smith Worker — lá existe relógio e lá a
            # sessão pode ser declarada encerrada de verdade.
            #
            # Não "conserte" isto passando outro timestamp: o resumo sairia no
            # meio da conversa, com metade do contexto. Ver CA-011.
            should_trigger = memory_service.should_summarize(
                settings=settings,
                channel=channel,
                messages_count=human_messages_count,
                last_message_at=datetime.now(),
                session_ended=False,
            )

            logger.info(f"[Memory] Should summarize: {should_trigger}")

            if should_trigger:
                # ✅ CORREÇÃO: Sempre usar schedule_summarization_async
                # O MemoryService agora sabe lidar com clients sync/async internamente
                await memory_service.schedule_summarization_async(
                    session_id=session_id,
                    user_id=user_id,
                    company_id=company_id,
                    messages=result.get("messages", []),
                    channel=channel,
                    settings=settings,
                    agent_id=agent_id,
                )
                logger.info(
                    f"[Memory] Summarization scheduled async for session {session_id}"
                )

        except Exception as e:
            logger.error(f"[Memory] Error scheduling summarization: {e}", exc_info=True)

    return {
        "response": final_response,
        "tools_used": result.get("tools_used", []),
        "rag_chunks": result.get("rag_chunks", []),
        "tokens_total": result.get("tokens_total", 0),
        "response_time_ms": result.get("llm_response_time_ms", 0),
    }


async def stream_agent(
    graph,
    user_message: str,
    company_id: str,
    user_id: str,
    session_id: str,
    company_config: Dict[str, Any],
    options: Dict[str, Any] = None,
    supabase_client=None,
    agent_id: str = None,
    async_supabase_client=None,  # <--- ADICIONADO: Suporte Async
):
    """
    Stream agent responses token-by-token using SSE.
    Includes robust fallback and ASYNC MEMORY SUMMARIZATION.
    """
    # Build initial state directly (now async)
    initial_state, config, real_agent_data = await _build_initial_state(
        user_message,
        company_id,
        user_id,
        session_id,
        company_config,
        options,
        supabase_client,
        agent_id,
    )

    # Contexto para canal (usado na memória e LangSmith)
    channel = "web"

    # === LANGSMITH TRACING (Multi-Tenant) ===
    # Injeta metadados para isolamento por company/agent no dashboard
    from app.core.langsmith_setup import get_langsmith_config, is_langsmith_enabled

    if is_langsmith_enabled():
        ls_config = get_langsmith_config(
            company_id=company_id,
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            channel=channel,
        )
        config["metadata"] = ls_config["metadata"]
        config["tags"] = ls_config["tags"]
        config["run_name"] = ls_config["run_name"]
        logger.debug(f"[LangSmith] Stream trace configurado: {ls_config['run_name']}")

    logger.info(f"[Stream] Iniciando astream_events para thread {company_id}:{session_id}")

    has_streamed = False

    try:
        # === RETRY LOOP PARA RESILIÊNCIA DE CONEXÃO ===
        # Supabase/PgBouncer pode fechar conexões inativas. Tentamos até 3x.
        from psycopg import OperationalError as PsycopgOperationalError

        max_retries = 3

        for attempt in range(max_retries):
            try:
                # Loop de Eventos
                async for event in graph.astream_events(initial_state, config, version="v1"):
                    kind = event["event"]
                    name = event.get("name", "")
                    data = event.get("data", {})

                    # --- Streaming Token por Token ---
                    # Filtra por langgraph_node: só streama tokens do nó "agent" (orquestrador).
                    # Tokens do SubAgent (que rodam no nó "tools") são ignorados.
                    if kind == "on_chat_model_stream":
                        event_node = event.get("metadata", {}).get("langgraph_node")
                        if event_node != "agent":
                            continue
                        chunk = data.get("chunk")
                        content = None

                        if hasattr(chunk, "content"):
                            content = chunk.content
                        elif isinstance(chunk, dict):
                            content = chunk.get("content")
                        elif isinstance(chunk, str):
                            content = chunk

                        if content:
                            text_to_yield = ""
                            if isinstance(content, list):
                                for block in content:
                                    if isinstance(block, dict) and block.get("type") == "text":
                                        text_to_yield += block.get("text", "")
                                    elif isinstance(block, str):
                                        text_to_yield += block
                            elif isinstance(content, str):
                                text_to_yield = content

                            if text_to_yield:
                                yield text_to_yield
                                has_streamed = True

                    # --- Fallback no Fim do Agente ---
                    elif kind == "on_chain_end" and name == "agent" and not has_streamed:
                        output = data.get("output")
                        final_text = ""
                        if isinstance(output, dict) and "messages" in output:
                            msgs = output["messages"]
                            if isinstance(msgs, list) and len(msgs) > 0:
                                last_msg = msgs[-1]
                                final_text = getattr(last_msg, "content", str(last_msg))
                            elif hasattr(msgs, "content"):
                                final_text = msgs.content
                        elif hasattr(output, "content"):
                            final_text = output.content

                        if final_text:
                            if isinstance(final_text, list):
                                text_parts = []
                                for block in final_text:
                                    if isinstance(block, dict) and block.get("type") == "text":
                                        text_parts.append(block.get("text", ""))
                                    elif isinstance(block, str):
                                        text_parts.append(block)
                                final_text = "".join(text_parts)

                            if final_text:
                                logger.info(f"[Stream] ⚠️ Fallback Node 'agent': Enviando {len(final_text)} chars.")
                                yield final_text
                                has_streamed = True

                # Stream completado com sucesso
                if not has_streamed:
                    try:
                        final_state = await graph.aget_state(config)
                        final_text = final_state.values.get("final_response", "")
                        if final_text:
                            yield str(final_text)
                            has_streamed = True
                    except Exception as final_error:  # noqa: BLE001
                        logger.warning(f"[Stream] final_response fallback indisponivel: {type(final_error).__name__}")
                break

            except (PsycopgOperationalError, Exception) as retry_error:
                error_str = str(retry_error).lower()
                is_connection_error = any(kw in error_str for kw in ["closed", "connection", "consuming input failed", "server closed"])

                if is_connection_error and attempt < max_retries - 1:
                    logger.warning(f"[Stream] ⚠️ Conexão DB perdida (tentativa {attempt + 1}/{max_retries}): {type(retry_error).__name__}")
                    await asyncio.sleep(1)  # Backoff antes de retry
                    continue
                else:
                    # Erro não recuperável ou tentativas esgotadas
                    logger.error(f"[Stream] ❌ Erro após {attempt + 1} tentativas: {retry_error}")
                    raise  # Re-raise para o except externo

        # === 🚀 MEMORY SYSTEM V2 - SUMMARIZATION TRIGGER (ADICIONADO) ===
        # Executado APÓS o fim do stream, não bloqueia a resposta visual
        if supabase_client or async_supabase_client:
            try:
                # 1. Recuperar estado atualizado do grafo para contar mensagens
                final_state = await graph.aget_state(config)
                all_messages = final_state.values.get("messages", [])

                # 2. Configurar Memory Service
                client_to_use = async_supabase_client if async_supabase_client else supabase_client
                memory_service = MemoryService(client_to_use)

                # 3. Ler settings Async por agent_id
                settings = await memory_service.get_memory_settings_async(agent_id)

                # 4. Contar mensagens Humanas
                human_messages_count = sum(
                    1 for m in all_messages if isinstance(m, HumanMessage)
                )

                logger.info(
                    f"[Stream Memory] Trigger check: msgs={human_messages_count}, threshold={settings.get('web_message_threshold', 20)}"
                )

                should_trigger = memory_service.should_summarize(
                    settings=settings,
                    channel=channel,
                    messages_count=human_messages_count,
                    last_message_at=datetime.now(),
                    session_ended=False,
                )

                if should_trigger:
                    await memory_service.schedule_summarization_async(
                        session_id=session_id,
                        user_id=user_id,
                        company_id=company_id,
                        messages=all_messages,
                        channel=channel,
                        settings=settings,
                        agent_id=agent_id,
                    )
                    logger.info(
                        f"[Stream Memory] ✅ Summarization scheduled async for session {session_id}"
                    )

            except Exception as e:
                logger.error(f"[Stream Memory] Error in background trigger: {e}")

    except Exception as e:
        logger.error(f"[Stream] Error during streaming: {e}", exc_info=True)
        yield "\n\n[Erro interno no servidor durante a geração da resposta.]"
