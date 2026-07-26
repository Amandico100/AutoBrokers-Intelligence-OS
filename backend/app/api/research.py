"""API do Research Intelligence. SPEC-060 §32.

Duas superfícies:

* **tenant** — a corretora vê as próprias pesquisas e monitores.
* **plataforma** — o Admin vê providers, fontes, custos, qualidade e ruído.

§32.4: `company_id` nunca vem do cliente sem passar pelo BFF autenticado;
nenhuma query livre; URL de fetch nunca vem direta do cliente sem validação
(quem valida é o Egress Guard, dentro do provider).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/research", tags=["Research"])
admin = APIRouter(prefix="/api/admin/research", tags=["Admin Research"])

TETO = 100


def _autorizar(chave: Optional[str]) -> None:
    esperada = (os.getenv("BACKEND_INTERNAL_API_KEY")
                or os.getenv("ADMIN_API_KEY") or "").strip()
    if not esperada:
        raise HTTPException(503, "chave interna nao configurada")
    if (chave or "").strip() != esperada:
        raise HTTPException(401, "nao autorizado")


def _db():
    return get_supabase_client()


# ==========================================================================
# Tenant — §32.1
# ==========================================================================


class PesquisaIn(BaseModel):
    company_id: str
    pergunta: str
    modo: Optional[str] = None
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    origem: str = "user"


@router.post("")
async def iniciar(payload: PesquisaIn,
                  x_internal_key: Optional[str] = Header(None)):
    """Inicia a pesquisa. Modo pesado vira Work Run; rápido responde na hora.

    A divisão é de §25.1 e existe para não fazer o corretor esperar dois
    minutos por uma pergunta simples — nem perder uma pesquisa profunda porque
    a conexão dele caiu.
    """
    _autorizar(x_internal_key)
    from app.services.research.planner import resolver_modo
    from app.services.research.schemas import MODOS_COM_WORK_RUN

    modo = payload.modo or resolver_modo(payload.pergunta)
    if modo not in MODOS_COM_WORK_RUN:
        from app.services.research.orchestrator import pesquisar

        r = await pesquisar(_db(), company_id=payload.company_id,
                            pergunta=payload.pergunta, modo=modo,
                            user_id=payload.user_id,
                            conversation_id=payload.conversation_id,
                            origem=payload.origem)
        return {"ok": r.ok, "sincrono": True, **r.como_dict()}

    from app.services.work.runs import WorkRunService

    try:
        run = WorkRunService(_db()).criar(
            company_id=payload.company_id, source_type="research",
            source_id=None, outcome_type="research.request",
            outcome_title=payload.pergunta[:180],
            workflow_key="research.execute",
            idempotency_key=f"research:{payload.company_id}:{abs(hash(payload.pergunta.lower().strip()))}",
            input_payload={"pergunta": payload.pergunta, "modo": modo,
                           "user_id": payload.user_id,
                           "conversation_id": payload.conversation_id,
                           "origem": payload.origem},
            requester_user_id=payload.user_id, priority=45, risk_level="low")
    except Exception as exc:  # noqa: BLE001
        logger.exception("[Research] work run nao criado")
        raise HTTPException(500, f"falha ao iniciar: {type(exc).__name__}") from exc

    return {"ok": True, "sincrono": False, "modo": modo,
            "work_run_id": run.get("run_id"), "reaproveitado": run.get("reused"),
            "mensagem": ("Comecei a pesquisa. Ela roda em segundo plano e o "
                         "resultado aparece aqui quando ficar pronto.")}


@router.get("")
async def listar(company_id: str, limite: int = Query(30, le=TETO),
                 x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    try:
        r = (_db().client.table("research_requests")
             .select("id, mode, question, status, result_summary, limitations, "
                     "created_at, work_run_id")
             .eq("company_id", company_id)
             .order("created_at", desc=True).limit(limite).execute())
        return {"ok": True, "pesquisas": r.data or []}
    except Exception:  # noqa: BLE001
        return {"ok": True, "pesquisas": []}


@router.get("/{research_id}")
async def detalhe(research_id: str, company_id: str,
                  x_internal_key: Optional[str] = Header(None)):
    """Pesquisa com claims, citações e fontes — tudo no nível da afirmação."""
    _autorizar(x_internal_key)
    from app.services.research.claim_service import ClaimService

    db = _db()
    try:
        pedido = (db.client.table("research_requests").select("*")
                  .eq("id", research_id).eq("company_id", company_id)
                  .maybe_single().execute()).data
    except Exception:  # noqa: BLE001
        pedido = None
    if not pedido:
        raise HTTPException(404, "pesquisa nao encontrada")

    servico = ClaimService(db)
    claims = servico.do_pedido(company_id, research_id)
    citacoes = servico.citacoes(company_id,
                                [str(c["id"]) for c in claims if c.get("id")])
    for c in claims:
        c["citacoes"] = citacoes.get(str(c.get("id")), [])

    return {"ok": True, "pesquisa": pedido, "claims": claims,
            "cobertura_de_citacao": servico.cobertura_de_citacao(claims)}


@router.get("/{research_id}/sources")
async def fontes(research_id: str, company_id: str,
                 x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    try:
        r = (_db().client.table("research_source_snapshots")
             .select("id, provider_key, retrieved_at, published_at, "
                     "excerpt_redacted, prompt_injection_status, "
                     "research_source_id, word_count")
             .eq("research_request_id", research_id).limit(60).execute())
        return {"ok": True, "fontes": r.data or []}
    except Exception:  # noqa: BLE001
        return {"ok": True, "fontes": []}


class MonitorIn(BaseModel):
    company_id: str
    nome: str
    urls: list[str] = Field(default_factory=list)
    tipo: str = "url"
    topico: Optional[str] = None
    cadencia: str = "daily"
    termos: list[str] = Field(default_factory=list)
    user_id: Optional[str] = None
    canais: list[str] = Field(default_factory=lambda: ["dashboard"])


@router.post("/monitors")
async def criar_monitor(payload: MonitorIn,
                        x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.research.monitor_service import MonitorService

    r = MonitorService(_db()).criar(
        company_id=payload.company_id, nome=payload.nome, urls=payload.urls,
        tipo=payload.tipo, topico=payload.topico, cadencia=payload.cadencia,
        user_id=payload.user_id, canais=payload.canais, termos=payload.termos)
    if not r.get("ok"):
        raise HTTPException(400, str(r.get("erro") or "nao foi possivel criar"))
    return r


@router.get("/monitors")
async def listar_monitores(company_id: str, limite: int = Query(50, le=TETO),
                           x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.research.monitor_service import MonitorService

    return {"ok": True,
            "monitores": MonitorService(_db()).listar(company_id, limite=limite)}


@router.get("/monitors/{monitor_id}/observations")
async def observacoes(monitor_id: str, company_id: str,
                      x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.research.monitor_service import MonitorService

    return {"ok": True,
            "observacoes": MonitorService(_db()).observacoes(
                company_id, monitor_id)}


class AlterarMonitorIn(BaseModel):
    company_id: str
    ativo: Optional[bool] = None
    cadencia: Optional[str] = None
    canais: Optional[list[str]] = None


@router.patch("/monitors/{monitor_id}")
async def alterar_monitor(monitor_id: str, payload: AlterarMonitorIn,
                          x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.research.monitor_service import MonitorService

    ok = MonitorService(_db()).alterar(
        payload.company_id, monitor_id, ativo=payload.ativo,
        cadencia=payload.cadencia, canais=payload.canais)
    if not ok:
        raise HTTPException(400, "nada a alterar")
    return {"ok": True}


@router.post("/monitors/{monitor_id}/run")
async def rodar_monitor(monitor_id: str, company_id: str,
                        x_internal_key: Optional[str] = Header(None)):
    """Executa agora, sem esperar a agenda. Útil logo após criar."""
    _autorizar(x_internal_key)
    from app.services.research.monitor_service import MonitorService

    r = await MonitorService(_db()).executar(monitor_id)
    return {"ok": bool(r.get("ok")), **r}


# --------------------------------------------------------------------------
# Auxiliar "Radar de Mercado e Regulação" — §37
# --------------------------------------------------------------------------
#
# A instalação do Auxiliar precisa de um efeito real: sem isto, a corretora
# instala o Radar, vê o card "ativo" e nunca recebe aviso nenhum — a pior
# forma de falhar, porque parece que está funcionando.


class RadarIn(BaseModel):
    company_id: str
    user_id: Optional[str] = None


@router.post("/radar/install")
async def instalar_radar(payload: RadarIn,
                         x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.research.radar import RadarDeMercado

    r = RadarDeMercado(_db()).instalar(company_id=payload.company_id,
                                       user_id=payload.user_id)
    if not r.get("ok"):
        raise HTTPException(400, str(r.get("erro") or "nao foi possivel instalar"))
    return r


@router.post("/radar/uninstall")
async def desinstalar_radar(payload: RadarIn,
                            x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.research.radar import RadarDeMercado

    return RadarDeMercado(_db()).desinstalar(company_id=payload.company_id)


@router.get("/radar")
async def status_radar(company_id: str,
                       x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.research.radar import RadarDeMercado

    servico = RadarDeMercado(_db())
    return {"ok": True,
            **servico.status(company_id=company_id),
            "mudancas_na_semana": len(
                servico.mudancas_do_periodo(company_id=company_id, dias=7))}


# ==========================================================================
# Plataforma — §32.2
# ==========================================================================


@admin.get("/overview")
async def visao_geral(dias: int = Query(30, le=180),
                      x_internal_key: Optional[str] = Header(None)):
    """§31.3 e §31.5 — o que foi pesquisado e com que qualidade."""
    _autorizar(x_internal_key)
    from datetime import datetime, timedelta, timezone

    from app.services.research.providers import saude

    db = _db().client
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()

    def _contar(tabela: str, filtros: Optional[dict] = None,
                campo: str = "created_at") -> int:
        try:
            q = db.table(tabela).select("id", count="exact").gte(campo, desde)
            for k, v in (filtros or {}).items():
                q = q.eq(k, v)
            r = q.execute()
            return int(getattr(r, "count", None) or len(r.data or []))
        except Exception:  # noqa: BLE001
            return -1

    try:
        claims = (db.table("research_claims")
                  .select("status, risk_level, citation_count, "
                          "official_citation_count")
                  .gte("created_at", desde).limit(4000).execute()).data or []
    except Exception:  # noqa: BLE001
        claims = []

    total = len(claims)
    com_citacao = sum(1 for c in claims if int(c.get("citation_count") or 0) > 0)
    criticos = [c for c in claims if c.get("risk_level") in ("high", "critical")]
    criticos_sem_oficial = sum(
        1 for c in criticos if int(c.get("official_citation_count") or 0) == 0)

    return {
        "ok": True, "periodo_dias": dias,
        "pesquisas": _contar("research_requests"),
        "bloqueadas": _contar("research_requests", {"status": "blocked"}),
        "monitores": _contar("research_monitors"),
        "observacoes": _contar("research_observations", campo="observed_at"),
        "fontes": _contar("research_sources", campo="first_seen_at"),
        "claims": total,
        "qualidade": {
            "cobertura_de_citacao": (round(100.0 * com_citacao / total, 1)
                                     if total else None),
            "claims_criticos": len(criticos),
            "criticos_sem_fonte_oficial": criticos_sem_oficial,
            "observacao": (None if total else
                           "ainda não há claims suficientes para calcular qualidade"),
        },
        "providers": [{"provider": s.provider_key, "disponivel": s.disponivel,
                       "motivo": s.motivo, "operacoes": list(s.operacoes)}
                      for s in saude(_db())],
    }


@admin.get("/providers")
async def providers(x_internal_key: Optional[str] = Header(None)):
    """§31.1 — estado, custo e última chamada. Nunca a chave."""
    _autorizar(x_internal_key)
    from datetime import datetime, timedelta, timezone

    from app.services.research.providers import saude

    db = _db().client
    desde = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    try:
        uso = (db.table("research_provider_usage")
               .select("provider_key, operation, status, units, latency_ms, "
                       "cache_hit, created_at")
               .gte("created_at", desde).limit(4000).execute()).data or []
    except Exception:  # noqa: BLE001
        uso = []

    por_provider: dict[str, dict] = {}
    for u in uso:
        k = str(u.get("provider_key"))
        g = por_provider.setdefault(k, {
            "provider": k, "chamadas": 0, "erros": 0, "sem_credito": 0,
            "unidades": 0.0, "latencia_total": 0, "cache_hits": 0,
            "ultima_chamada": None})
        g["chamadas"] += 1
        if u.get("status") == "error":
            g["erros"] += 1
        if u.get("status") == "no_credit":
            g["sem_credito"] += 1
        g["unidades"] += float(u.get("units") or 0)
        g["latencia_total"] += int(u.get("latency_ms") or 0)
        if u.get("cache_hit"):
            g["cache_hits"] += 1
        if not g["ultima_chamada"] or str(u.get("created_at")) > g["ultima_chamada"]:
            g["ultima_chamada"] = u.get("created_at")

    for g in por_provider.values():
        g["latencia_media_ms"] = (round(g["latencia_total"] / g["chamadas"])
                                  if g["chamadas"] else None)
        g.pop("latencia_total", None)

    estado = {s.provider_key: s for s in saude(_db())}
    linhas = []
    for chave, s in estado.items():
        linhas.append({**por_provider.get(chave, {"provider": chave, "chamadas": 0}),
                       "disponivel": s.disponivel, "motivo": s.motivo,
                       "operacoes": list(s.operacoes)})
    return {"ok": True, "providers": linhas}


@admin.get("/sources")
async def fontes_admin(limite: int = Query(100, le=300),
                       x_internal_key: Optional[str] = Header(None)):
    """§31.2 — Source Registry com tier e política."""
    _autorizar(x_internal_key)
    from app.services.research.source_registry import SourceRegistry

    registry = SourceRegistry(_db())
    return {"ok": True,
            "politicas": registry.listar_politicas(),
            "fontes": registry.fontes_recentes(limite=limite)}


@admin.post("/sources/seed")
async def semear_fontes(x_internal_key: Optional[str] = Header(None)):
    """Publica o catálogo inicial de §18.1. Idempotente."""
    _autorizar(x_internal_key)
    from app.services.research.source_registry import SourceRegistry

    return {"ok": True, "inseridas": SourceRegistry(_db()).semear_politicas()}


@admin.get("/monitors")
async def monitores_admin(limite: int = Query(100, le=300),
                          x_internal_key: Optional[str] = Header(None)):
    """§31.4 — monitores com saúde e RUÍDO. O ruído é o número que importa."""
    _autorizar(x_internal_key)
    from app.services.research.monitor_service import MonitorService

    db = _db()
    servico = MonitorService(db)
    try:
        linhas = (db.client.table("research_monitors")
                  .select("id, company_id, name, monitor_type, cadence, "
                          "is_active, health, health_reason, last_run_at, "
                          "last_change_at, consecutive_failures")
                  .order("last_run_at", desc=True).limit(limite).execute()).data or []
    except Exception:  # noqa: BLE001
        linhas = []

    ruido = {r["monitor_id"]: r for r in servico.ruido_por_monitor()}
    for m in linhas:
        m["ruido"] = ruido.get(str(m.get("id")))
    return {"ok": True, "monitores": linhas}


@admin.get("/costs")
async def custos(dias: int = Query(30, le=180),
                 x_internal_key: Optional[str] = Header(None)):
    """§31.6 e §33.2 — custo por provider e por corretora, medido."""
    _autorizar(x_internal_key)
    from datetime import datetime, timedelta, timezone

    db = _db().client
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    try:
        uso = (db.table("research_provider_usage")
               .select("company_id, provider_key, units, cost_brl, "
                       "cost_is_estimated, cache_hit, status")
               .gte("created_at", desde).limit(5000).execute()).data or []
    except Exception:  # noqa: BLE001
        uso = []

    por_tenant: dict[str, dict] = {}
    for u in uso:
        k = str(u.get("company_id") or "plataforma")
        g = por_tenant.setdefault(k, {"company_id": k, "chamadas": 0,
                                      "unidades": 0.0, "cache_hits": 0,
                                      "tudo_estimado": True})
        g["chamadas"] += 1
        g["unidades"] += float(u.get("units") or 0)
        if u.get("cache_hit"):
            g["cache_hits"] += 1
        if not u.get("cost_is_estimated"):
            g["tudo_estimado"] = False

    return {"ok": True, "periodo_dias": dias,
            "por_corretora": sorted(por_tenant.values(),
                                    key=lambda x: -x["unidades"]),
            "observacao": ("Unidades são chamadas e créditos de provider, "
                           "medidos. Preço ao cliente é da SPEC-062 e não "
                           "aparece aqui.")}


@admin.get("/security")
async def seguranca(dias: int = Query(30, le=180),
                    x_internal_key: Optional[str] = Header(None)):
    """§31.7 — o que a defesa de conteúdo web barrou."""
    _autorizar(x_internal_key)
    from datetime import datetime, timedelta, timezone

    db = _db().client
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    try:
        snaps = (db.table("research_source_snapshots")
                 .select("prompt_injection_status, injection_score, metadata")
                 .gte("retrieved_at", desde).limit(4000).execute()).data or []
    except Exception:  # noqa: BLE001
        snaps = []

    padroes: dict[str, int] = {}
    for s in snaps:
        for p in ((s.get("metadata") or {}).get("padroes") or []):
            padroes[p] = padroes.get(p, 0) + 1

    return {
        "ok": True, "periodo_dias": dias,
        "paginas_lidas": len(snaps),
        "suspeitas": sum(1 for s in snaps
                         if s.get("prompt_injection_status") == "suspeito"),
        "quarentenadas": sum(1 for s in snaps
                             if s.get("prompt_injection_status") == "quarentena"),
        "padroes_detectados": padroes,
        "observacao": ("Conteúdo em quarentena não é enviado ao modelo. "
                       "Página que fala sobre o assunto também casa com os "
                       "padrões — por isso quarentena não é acusação."),
    }
