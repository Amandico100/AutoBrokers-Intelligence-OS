"""
FastAPI Main Application
"""

import os

import sentry_sdk
from dotenv import load_dotenv

load_dotenv()

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    send_default_pii=False,  # Never send personal data (LGPD/GDPR compliance)
    traces_sample_rate=0.1
    if os.getenv("ENV") == "production"
    else 1.0,  # 10% in prod, 100% in dev
    environment=os.getenv("ENV", "development"),
)

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.agents.graph import close_async_postgres_pool
from app.api import chat_router
from app.api.agent_config import router as agent_config_router
from app.api.artifacts import router as artifacts_router
from app.api.brand import router as brand_router
from app.api.corpus import router as corpus_router
from app.api.factory import router as factory_router
from app.api.documents import router as documents_router
from app.api.webhook import router as webhook_router
from app.core import settings
from app.core.database import create_async_supabase_client
from app.core.redis import close_async_redis_client
from app.tasks.buffer_processor import shutdown_buffer_scheduler, start_buffer_scheduler

# Configurar logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# Lifespan manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifespan: startup and shutdown"""

    # === STARTUP ===

    # 0. LangSmith Observability (if configured)
    from app.core.langsmith_setup import configure_langsmith
    langsmith_enabled = configure_langsmith()
    if langsmith_enabled:
        logger.info("[STARTUP] ✅ LangSmith tracing enabled")

    # 1. Inicializar cliente Supabase Async (non-blocking)
    logger.info("[STARTUP] Initializing Async Supabase Client...")
    app.state.supabase_async = await create_async_supabase_client()
    logger.info("[STARTUP] ✅ Async Supabase Client ready")

    # 2. Preload pricing cache (evita cold start no primeiro request)
    logger.info("[STARTUP] Preloading LLM pricing cache...")
    try:
        from app.services.usage_service import preload_pricing_cache
        count = preload_pricing_cache()
        logger.info(f"[STARTUP] ✅ Pricing cache loaded: {count} models")
    except Exception as e:
        logger.warning(f"[STARTUP] ⚠️ Pricing cache preload failed (will use fallback): {e}")

    # 3. Iniciar scheduler do WhatsApp Buffer
    logger.info("[STARTUP] Starting WhatsApp Buffer Scheduler...")
    start_buffer_scheduler()

    # 4. F2 — Motor de Rotinas (Claude-Rotinas): agendador em background.
    import asyncio as _asyncio

    from app.services.routine_engine import routine_scheduler_loop

    app.state.routine_scheduler = _asyncio.create_task(routine_scheduler_loop())
    logger.info("[STARTUP] ✅ Routine engine scheduler started")

    # 5. SPEC-055 — Smith Worker.
    #
    # O alvo arquitetural é um SERVIÇO SEPARADO (`python -m app.workers.smith_worker`),
    # e é assim que deve ficar em produção: tarefa longa não disputa event loop
    # com requisição web, e um deploy da API não derruba trabalho em curso.
    #
    # Enquanto esse serviço não existe no EasyPanel, esta flag permite rodar o
    # worker dentro da API. Não é o estado final — mas já é melhor do que o
    # scheduler in-process anterior, porque agora existe lease: se este processo
    # morrer no meio, o run é recuperado em vez de ficar preso para sempre.
    #
    # Default DESLIGADO. Ligar apenas de forma consciente.
    app.state.smith_worker = None
    if str(os.getenv("WORK_WORKER_IN_PROCESS", "")).strip().lower() in ("1", "true", "yes", "on"):
        try:
            from app.workers.smith_worker import SmithWorker

            _worker = SmithWorker()
            app.state.smith_worker = _worker
            app.state.smith_worker_task = _asyncio.create_task(_worker.executar())
            logger.warning(
                "[STARTUP] ⚠️ Smith Worker rodando DENTRO da API (ponte). "
                "O alvo é um serviço dedicado — ver SPEC-055 §11.1."
            )
        except Exception as _e:  # noqa: BLE001
            logger.error("[STARTUP] Smith Worker não iniciou: %s", type(_e).__name__)

    yield

    # SPEC-055 — encerrar o worker antes do resto, para liberar leases
    _worker = getattr(app.state, "smith_worker", None)
    if _worker:
        try:
            _worker.parar.set()
            _t = getattr(app.state, "smith_worker_task", None)
            if _t:
                await _asyncio.wait_for(_t, timeout=20)
        except Exception:  # noqa: BLE001
            logger.warning("[SHUTDOWN] Smith Worker encerrado sem confirmação")

    # F2 — parar o agendador de rotinas
    task = getattr(app.state, "routine_scheduler", None)
    if task:
        task.cancel()

    # === SHUTDOWN ===
    logger.info("[SHUTDOWN] Stopping WhatsApp Buffer Scheduler...")
    shutdown_buffer_scheduler()

    logger.info("[SHUTDOWN] Closing async Redis client...")
    await close_async_redis_client()

    logger.info("[SHUTDOWN] Closing PostgreSQL Connection Pool...")
    await close_async_postgres_pool()


# Criar app FastAPI com lifespan
# Docs desabilitados em produção (DEBUG=false)
debug_mode = os.getenv("DEBUG", "false").lower() == "true"

app = FastAPI(
    title="AutoBrokers Intelligence OS API",
    description="Backend FastAPI do AutoBrokers Intelligence OS",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs" if debug_mode else None,
    redoc_url="/redoc" if debug_mode else None,
    openapi_url="/openapi.json" if debug_mode else None,
)

# Rate Limiting
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.rate_limit import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Trust proxy headers (Railway) - necessary for HTTPS redirects
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rotas
app.include_router(chat_router, tags=["Chat"])
app.include_router(documents_router, tags=["Documents"])
# SPEC-057 — identidade da corretora. Egresso e derivacao de paleta ficam
# no backend, onde vive o egress_guard.
app.include_router(brand_router, tags=["Brand Identity"])
# SPEC-057 — Artifact Hub. /shared/{token} e a unica rota cujo resultado
# vai para alguem sem sessao; ela devolve o mesmo vazio para todo motivo
# de recusa, para nao confirmar existencia de token.
app.include_router(artifacts_router, tags=["Artifact Hub"])
# SPEC-057 H — corpus normativo. Rotas de PLATAFORMA: o corpus e o mesmo
# para todas as corretoras, entao nenhuma delas recebe company_id.
app.include_router(corpus_router, tags=["Corpus Normativo"])
# SPEC-058 — Auxiliary Factory. /oportunidades e a rota que transforma
# pedido de corretora em roadmap com evidencia, em vez de opiniao.
app.include_router(factory_router, tags=["Auxiliary Factory"])
# SPEC-059 — Intelligence Fabric. Duas superficies: a da corretora
# (briefing, prioridades, recomendacoes) e a da plataforma (sinais, regras,
# demanda agregada e anonima).
try:
    from app.api.intelligence import admin as intelligence_admin_router
    from app.api.intelligence import router as intelligence_router

    app.include_router(intelligence_router, tags=["Intelligence"])
    app.include_router(intelligence_admin_router, tags=["Admin Intelligence"])
    logger.info("[STARTUP] Intelligence Fabric API registrada")
except Exception as _e:  # noqa: BLE001
    logger.error("[STARTUP] Intelligence API indisponivel: %s", type(_e).__name__)

# SPEC-060 — Research Intelligence. Pesquisa com fonte, claim e citacao;
# monitores que so avisam quando muda algo relevante.
try:
    from app.api.research import admin as research_admin_router
    from app.api.research import router as research_router

    app.include_router(research_router, tags=["Research"])
    app.include_router(research_admin_router, tags=["Admin Research"])
    logger.info("[STARTUP] Research Intelligence API registrada")
except Exception as _e:  # noqa: BLE001
    logger.error("[STARTUP] Research API indisponivel: %s", type(_e).__name__)

# SPEC-061 — Control Plane. A autoridade administrativa mora aqui, em UM lugar:
# o BFF do Next pergunta, nao decide. Duas copias da matriz de papeis
# divergiriam na primeira permission nova.
try:
    from app.api.control_plane import router as control_plane_router

    app.include_router(control_plane_router, tags=["Control Plane"])
    logger.info("[STARTUP] Control Plane API registrada")
except Exception as _e:  # noqa: BLE001
    logger.error("[STARTUP] Control Plane API indisponivel: %s", type(_e).__name__)
app.include_router(agent_config_router, prefix="/api/agent", tags=["Agent Config"])
from app.api.agents import router as agents_router
from app.api.billing import router as billing_router
from app.api.billing_admin import router as billing_admin_router
from app.api.mcp import router as mcp_router
from app.api.plans import router as plans_router
from app.api.pricing import router as pricing_router
from app.api.stripe_checkout import router as stripe_checkout_router
from app.api.stripe_webhooks import router as stripe_webhooks_router

app.include_router(agents_router, prefix="/api/agents", tags=["Agents (Multi-Agent)"])
app.include_router(webhook_router, tags=["Webhook"])
app.include_router(pricing_router, tags=["Admin Pricing"])
app.include_router(plans_router, tags=["Admin Plans"])
app.include_router(billing_router, tags=["Billing (Owner)"])
app.include_router(billing_admin_router, tags=["Admin Billing"])

# SPEC-034/036: superficies do portal admin (Central de Agentes, Acionamentos,
# Insights, Registro, Mapas/Alfaiate)
from app.api.admin_spec034 import router as admin_spec034_router

app.include_router(admin_spec034_router, tags=["Admin SPEC-034"])

# SPEC-038: ATLAS — Observador (relatório do spike + history sync)
from app.api.admin_atlas import router as admin_atlas_router

app.include_router(admin_atlas_router, tags=["Admin ATLAS (SPEC-038)"])
app.include_router(stripe_webhooks_router, prefix="/api/webhooks", tags=["Stripe Webhooks"])
app.include_router(stripe_checkout_router, prefix="/api/billing", tags=["Stripe Checkout"])
app.include_router(mcp_router, prefix="/api/mcp", tags=["MCP Integrations"])

# === Sanitization (Document Sanitizer) ===
from app.api.sanitization import router as sanitization_router

app.include_router(sanitization_router, prefix="/api/sanitization", tags=["Sanitization"])

# === Auxiliares (Product layer over Smith runtime) ===
from app.api.auxiliaries import router as auxiliaries_router

app.include_router(auxiliaries_router, prefix="/api/auxiliaries", tags=["Auxiliaries"])

# === WhatsApp Integrations (Vault secret flow) ===
from app.api.whatsapp_integrations import router as whatsapp_integrations_router

app.include_router(
    whatsapp_integrations_router, prefix="/api/whatsapp-integrations", tags=["WhatsApp Integrations"]
)

# (SPEC-046) attendance_agent_reply removido — era o fallback LLM do runtime
# TS legado (42B5L-BE); único chamador (lib/attendance/runtime-llm-fallback.ts)
# saiu junto com o bridge. O atendente roda direto no Smith.

# === InfoCap Connector Secret Storage (secret flow — 42I2.0C) ===
from app.api.infocap_connector import router as infocap_connector_router
from app.api.oauth_connectors import router as oauth_connectors_router

app.include_router(infocap_connector_router, tags=["InfoCap Connector"])
app.include_router(oauth_connectors_router, tags=["OAuth Connectors"])

# === SPEC-017 P1.2 — Canal WhatsApp da corretora (Evolution setup/QR/status) ===
from app.api.whatsapp_channel import router as whatsapp_channel_router

app.include_router(whatsapp_channel_router, tags=["WhatsApp Channel"])

# === Onda 3 / SPEC-018 — Autoridade & Prompt Efetivo (read-only) ===
from app.api.authority import router as authority_router

app.include_router(authority_router, tags=["Authority"])

# === SPEC-017 — Espelho de acionamentos ativos (Conversas do dashboard) ===
from app.api.dispatch_monitor import router as dispatch_monitor_router

app.include_router(dispatch_monitor_router, tags=["Dispatch"])

# === SPEC-063 — Catálogo de corredores para a tela (a lista vem do CÓDIGO) ===
# A página de Corredores lia `corridor_templates` (2 linhas) enquanto o motor
# executava 13 corredores de `corridor_playbooks.py`. Sem esta rota, a tela não
# tem como enxergar quem executa.
from app.api.corridors import router as corridors_router

app.include_router(corridors_router, tags=["Corridors"])

# === Attendance Media (audio transcription — 42M0) ===
from app.api.attendance_media import router as attendance_media_router

app.include_router(attendance_media_router, tags=["Attendance Media"])

# === Portais (SPEC-020): registro global + credenciais por corretora (cifradas) ===
from app.api.portal import router as portal_router

app.include_router(portal_router, tags=["Portal"])

# SPEC-055 - Work OS: execucao duravel
try:
    from app.api.work_runs import router as work_runs_router
    app.include_router(work_runs_router, tags=["Work Runs"])
    logger.info("[STARTUP] Work Runs API registrada")

    # Painel de subsistemas no startup. Sem isto, a unica forma de saber o que
    # esta ligado e adivinhar pelo comportamento — e um log que nao responde
    # "o que esta no ar?" obriga a diagnosticar por tentativa.
    try:
        import os as _os

        from app.agents.context_assembly import modo as _ctx_modo
        from app.agents.gateway_cutover import modo_atual as _gw_modo
        from app.services.research.firecrawl import configurado as _fc_ok

        logger.info(
            "[STARTUP] SUBSISTEMAS SPEC-054..057 | marca=%s artefatos=%s corpus=%s | "
            "tool_gateway=%s context_assembly=%s authority_strict=%s | "
            "firecrawl=%s ponte_rotinas=%s worker_na_api=%s",
            "on" if brand_router else "off",
            "on" if artifacts_router else "off",
            "on" if corpus_router else "off",
            _gw_modo(), _ctx_modo(),
            "on" if str(_os.getenv("AUTHORITY_STRICT_MODE", "")).strip().lower()
            in ("1", "true", "yes", "on") else "off",
            "configurado" if _fc_ok() else "SEM CHAVE",
            "on" if str(_os.getenv("WORK_RUNS_ROUTINE_BRIDGE", "")).strip() in ("1", "true", "on") else "off",
            "on" if str(_os.getenv("WORK_WORKER_IN_PROCESS", "")).strip() in ("1", "true", "on") else "off",
        )
    except Exception as _e:  # noqa: BLE001
        logger.warning("[STARTUP] painel de subsistemas indisponivel: %s", type(_e).__name__)
except Exception as _e:
    logger.error(f"[STARTUP] Work Runs API indisponivel: {type(_e).__name__}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "AutoBrokers Intelligence OS API",
        "version": "1.0.0",
    }


@app.get("/robots.txt")
async def robots_txt():
    """Block search engine crawlers from indexing the API"""
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse("User-agent: *\nDisallow: /\n")


def _checar_storage() -> dict:
    """MinIO: o bucket responde?

    Devolve o ENDEREÇO junto — sem ele, "não conectou" não diz se o problema é
    o nome do host, a credencial ou o serviço fora do ar. O endereço não é
    segredo; a senha nunca aparece.
    """
    from app.core.config import settings

    alvo = str(getattr(settings, "MINIO_ENDPOINT", "") or "(não configurado)")
    balde = str(getattr(settings, "MINIO_BUCKET", "") or "documents")
    try:
        from app.services.minio_service import MinioService

        existe = MinioService().client.bucket_exists(balde)
        return {"conectado": True, "endereco": alvo, "bucket": balde,
                "bucket_existe": bool(existe)}
    except Exception as exc:  # noqa: BLE001
        return {"conectado": False, "endereco": alvo, "bucket": balde,
                "erro": type(exc).__name__,
                "detalhe": str(exc)[:200],
                "dica": _dica_do_storage(alvo, str(exc))}


def _dica_do_storage(endereco: str, erro: str) -> str:
    """Traduz a falha do MinIO em uma instrução.

    Existe porque "S3Error: InvalidRequest" não diz a ninguém o que fazer — e a
    causa mais provável neste ambiente é contraintuitiva.
    """
    baixo = erro.lower()

    # O caso que custou dois deploys: o MinIO valida o cabeçalho `Host` pela
    # regra de DNS (RFC 1123), onde **underscore é inválido**. O nome interno
    # do EasyPanel usa underscore no nome do projeto, então o endereço RESOLVE
    # (a requisição chega) e o MinIO recusa. Redis e Qdrant funcionam com o
    # mesmo padrão porque não validam o host.
    if "invalid hostname" in baixo or "invalidrequest" in baixo:
        if "_" in endereco:
            return ("o endereço tem underscore, e o MinIO recusa isso no "
                    "cabeçalho Host (regra de DNS). O endereço RESOLVE — a "
                    "requisição chegou e foi recusada. Use um nome só com "
                    "hífen: o nome curto do serviço "
                    "(`autobrokers-smith-minio:9000`) ou o endereço público "
                    "com MINIO_SECURE=true.")
        return ("o MinIO recusou o cabeçalho Host. Confira se o endereço tem "
                "apenas letras, números, hífen e ponto.")

    if "403" in baixo or "accessdenied" in baixo or "signature" in baixo:
        return ("o endereço está certo e a CREDENCIAL não. O backend lê "
                "MINIO_ROOT_USER e MINIO_ROOT_PASSWORD; o Docling lê "
                "MINIO_ACCESS_KEY e MINIO_SECRET_KEY.")

    if ("resolve" in baixo or "getaddrinfo" in baixo or "nodename" in baixo
            or "name or service not known" in baixo):
        return ("o endereço NÃO resolve — a requisição não chegou. O nome do "
                "serviço está errado ou ele não está no ar.")

    if "timed out" in baixo or "timeout" in baixo:
        return ("o endereço resolve e ninguém responde na porta. Confira a "
                "porta e se o serviço está rodando.")

    return ("sem causa reconhecida. O `detalhe` acima é a mensagem do "
            "servidor.")


def _checar_redis() -> dict:
    import os

    url = str(os.getenv("REDIS_URL") or "")
    # A URL carrega a senha. Só o host aparece.
    host = url.split("@")[-1] if "@" in url else "(não configurado)"
    try:
        import redis  # type: ignore

        redis.Redis.from_url(url, socket_connect_timeout=3).ping()
        return {"conectado": True, "host": host}
    except Exception as exc:  # noqa: BLE001
        return {"conectado": False, "host": host,
                "erro": type(exc).__name__, "detalhe": str(exc)[:200]}


def _checar_qdrant() -> dict:
    import os

    host = str(os.getenv("QDRANT_HOST") or "(não configurado)")
    porta = str(os.getenv("QDRANT_PORT") or "6333")
    try:
        import httpx

        r = httpx.get(f"http://{host}:{porta}/readyz", timeout=3.0)
        return {"conectado": r.status_code < 400, "host": f"{host}:{porta}",
                "http": r.status_code}
    except Exception as exc:  # noqa: BLE001
        return {"conectado": False, "host": f"{host}:{porta}",
                "erro": type(exc).__name__, "detalhe": str(exc)[:200]}


def _sinais_do_codigo() -> dict:
    """O que este processo sabe fazer. Serve para responder "o deploy entrou?"
    sem gastar um centavo e sem depender de o build injetar variável nenhuma.

    Cada chave é uma peça que nasceu num commit datado. Se a peça existe, o
    commit está no ar. Peça nova = uma linha nova aqui.
    """
    import os as _os

    sinais: dict = {"git_commit": _os.getenv("GIT_COMMIT") or "nao-injetado"}
    try:
        from app.services import attendance_distiller as _d

        sinais["teto_de_gasto"] = hasattr(_d, "_teto_de_gasto")
        sinais["fecha_sessao_vencida"] = hasattr(_d, "_fechar_sessoes_vencidas_sync")
        sinais["le_resposta_com_pensamento"] = hasattr(_d, "_texto_da_resposta")
        sinais["teto_atual"] = _d._teto_de_gasto() if hasattr(_d, "_teto_de_gasto") else None
    except Exception:  # noqa: BLE001
        sinais["destilador"] = "indisponivel"
    try:
        from app.services.atlas.templater import templatize

        # Cada frase abaixo só passa/mascara com o conserto de PII do dia.
        sinais["pii_cartao"] = templatize("4111 1111 1111 1111") != "4111 1111 1111 1111"
        sinais["pii_nao_come_a_frase"] = templatize(
            "Boleto de seguro nao pago leva ao cancelamento") == \
            "Boleto de seguro nao pago leva ao cancelamento"
        sinais["pii_rotulo_com_barra"] = templatize(
            "Cidade/CEP onde o reparo sera feito") == "Cidade/CEP onde o reparo sera feito"
        sinais["pii_email"] = templatize("a@b.com.br") != "a@b.com.br"
        sinais["pii_numero_longo"] = templatize("protocolo: 999999999") != "protocolo: 999999999"
        sinais["pii_senha_com_hifen"] = templatize("senha - Abc2026") != "senha - Abc2026"
        # A inversa, e ela vale tanto quanto: o conhecimento tem de sobreviver.
        # Se esta virar False, o mascarador ficou guloso e esta apagando carta.
        sinais["conhecimento_sobrevive"] = (
            templatize("A senha do atendimento sao os quatro ultimos digitos do telefone")
            == "A senha do atendimento sao os quatro ultimos digitos do telefone"
            and templatize("A assistencia cobre ate 200 km da residencia")
            == "A assistencia cobre ate 200 km da residencia")
    except Exception:  # noqa: BLE001
        sinais["templater"] = "indisponivel"
    try:
        from app.services.corridor_playbooks import normalize_insurer_key

        sinais["seguradora_normalizada"] = normalize_insurer_key("tokio_marine") == "tokio"
    except Exception:  # noqa: BLE001
        pass

    # O SINAL QUE DECIDE SE DÁ PARA RECONECTAR O WHATSAPP.
    #
    # 3.653 áudios foram capturados sem as coordenadas de download e estão
    # perdidos. A correção grava `mediaKey`/`directPath`; sem ela no ar, a
    # reconexão re-entrega o histórico e perde os áudios de novo, do mesmo jeito
    # silencioso. Não dá para "achar que subiu" — tem de dar para conferir.
    #
    # Confere as duas metades, porque uma sem a outra é defeito: gravar sem
    # esconder publicaria a chave de descriptografia numa resposta de API.
    try:
        from app.services.atlas.observer_intake import (
            COORDENADAS_DE_MIDIA, sem_coordenadas)

        amostra = {"kind": "audio", "segundos": 44, "mediaKey": "x", "directPath": "/y"}
        limpo = sem_coordenadas(amostra)
        sinais["midia_recuperavel"] = ("mediaKey" in COORDENADAS_DE_MIDIA
                                       and "directPath" in COORDENADAS_DE_MIDIA)
        sinais["midia_chave_escondida"] = ("mediaKey" not in limpo
                                           and limpo.get("download") == "recuperavel")
    except Exception:  # noqa: BLE001
        sinais["midia_recuperavel"] = False
        sinais["midia_chave_escondida"] = False

    # O template do briefing existe no catálogo? Sem ele, o artefato morre em
    # chave estrangeira e o briefing fica em `pending` sem ninguém saber.
    try:
        from app.services.artifacts.templates import POR_CHAVE

        sinais["templates_do_briefing"] = all(
            k in POR_CHAVE for k in ("briefing.daily_operational",
                                     "briefing.weekly_executive"))
    except Exception:  # noqa: BLE001
        sinais["templates_do_briefing"] = False
    return sinais


@app.get("/health")
async def health_check(request: Request):
    """Health check detalhado - verifica conexão real com ambos os clientes"""
    from datetime import datetime

    from fastapi.responses import JSONResponse

    from app.core.database import get_supabase_client

    health_status = {
        "status": "healthy",
        "database_sync": "unknown",
        "database_async": "unknown",
        "langchain": "initialized",
        "timestamp": datetime.utcnow().isoformat(),
        # QUAL CÓDIGO ESTÁ NO AR.
        #
        # Em 29 e 30/07/2026 a pergunta "o deploy entrou?" apareceu seis vezes,
        # e não havia como responder: nada aqui dizia qual versão respondia.
        # A dúvida custava um clique em botão que gasta crédito só para
        # descobrir, pela mensagem que voltava, se o código era o novo.
        #
        # `GIT_COMMIT` depende do build injetar a variável, e o EasyPanel pode
        # não injetar. Então além dela vão os SINAIS: presença das travas que
        # nasceram em cada commit. Eles não dependem de build nenhum — são o
        # próprio código respondendo se existe. Uma peça nova acrescenta uma
        # linha aqui e a pergunta some.
        "codigo": _sinais_do_codigo(),
    }

    # 1. Verificar cliente async (primary - non-blocking)
    try:
        db = request.app.state.supabase_async
        await db.client.table("companies").select("id").limit(1).execute()
        health_status["database_async"] = "connected"
    except Exception as e:
        health_status["database_async"] = f"error: {str(e)}"
        logger.error(f"[HEALTH] Async database check failed: {e}")

    # 2. Verificar cliente sync (backward compat)
    try:
        supabase = get_supabase_client()
        supabase.client.table("companies").select("id").limit(1).execute()
        health_status["database_sync"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database_sync"] = "disconnected"
        health_status["error"] = str(e)
        logger.error(f"[HEALTH] Sync database check failed: {e}")

    # 3. Infraestrutura de apoio — SPEC-061.
    #
    # Sem isto, "o MinIO está acessível?" era uma pergunta sem resposta: não
    # havia como saber sem entrar no servidor. E o sintoma de MinIO
    # inacessível é uma peça que não é gerada — ausência, não erro.
    #
    # Estes três NÃO derrubam o health para 503: o Work OS e a conversa
    # funcionam sem eles. Marcar como doente o que ainda atende faria o
    # balanceador tirar do ar um serviço que estava trabalhando.
    health_status["storage"] = _checar_storage()
    health_status["redis"] = _checar_redis()
    health_status["qdrant"] = _checar_qdrant()

    # Retornar 503 se unhealthy (load balancers dependem disso)
    if health_status["status"] == "unhealthy":
        return JSONResponse(status_code=503, content=health_status)

    return health_status


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
