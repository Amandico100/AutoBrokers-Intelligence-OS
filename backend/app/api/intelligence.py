"""API do Intelligence Fabric. SPEC-059 §27.

Duas superfícies, e a fronteira entre elas é a coisa mais importante do
arquivo:

* **tenant** — o corretor vê o que é da corretora dele. `company_id` chega
  pelo BFF autenticado, nunca de um parâmetro que o browser escolhe.
* **plataforma** — o Admin vê agregado e redigido. Evidência de tenant
  sensível exige justificativa e fica no audit log (§26.7).

Nenhuma rota daqui recebe query livre do cliente (§27.4). Filtro fechado,
`limit` com teto, e `company_id` sempre aplicado no repositório — RLS sem
policy protege contra acesso direto, não contra um filtro esquecido no código
que usa service role (CLAUDE.md §7).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/intelligence", tags=["Intelligence"])
admin = APIRouter(prefix="/api/admin/intelligence", tags=["Admin Intelligence"])

TETO_LISTA = 100


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
# Tenant — §27.1
# ==========================================================================


@router.get("/briefing/current")
async def briefing_atual(company_id: str, tipo: str = "daily_operational",
                         user_id: Optional[str] = None,
                         x_internal_key: Optional[str] = Header(None)):
    """O briefing publicado do período. Não gera — só entrega o que existe."""
    _autorizar(x_internal_key)
    from app.services.intelligence.briefing_service import BriefingService

    pub = BriefingService(_db()).atual(company_id, briefing_type=tipo,
                                       user_id=user_id)
    if not pub:
        # 200 com `briefing: null` de propósito: "ainda não há briefing hoje"
        # é uma resposta legítima, não um erro. 404 faria a tela mostrar falha
        # onde só há ausência.
        return {"ok": True, "briefing": None,
                "mensagem": "Ainda não há briefing publicado para este período."}
    return {"ok": True, "briefing": pub}


@router.post("/briefings/generate")
async def gerar_briefing(company_id: str, tipo: str = "daily_operational",
                         user_id: Optional[str] = None,
                         x_internal_key: Optional[str] = Header(None)):
    """Briefing sob demanda — §16.4. Idempotente por período."""
    _autorizar(x_internal_key)
    from app.services.intelligence.briefing_service import BriefingService

    try:
        r = BriefingService(_db()).gerar(company_id, briefing_type=tipo,
                                         user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[Intelligence] geração de briefing falhou")
        raise HTTPException(500, f"falha ao gerar: {type(exc).__name__}") from exc
    return {"ok": bool(r.get("ok")), **r}


@router.get("/briefings")
async def historico(company_id: str, limite: int = Query(30, le=TETO_LISTA),
                    x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.intelligence.briefing_service import BriefingService

    return {"ok": True,
            "briefings": BriefingService(_db()).historico(company_id, limite=limite)}


@router.get("/findings")
async def findings(company_id: str, user_id: Optional[str] = None,
                   limite: int = Query(50, le=TETO_LISTA),
                   x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.intelligence.finding_engine import FindingEngine

    return {"ok": True,
            "findings": FindingEngine(_db()).ativos(company_id, user_id=user_id,
                                                    limite=limite)}


class RespostaFindingIn(BaseModel):
    company_id: str
    acao: str = Field(description="acknowledge | snooze | dismiss | resolve")
    user_id: Optional[str] = None
    dias: int = 1


@router.post("/findings/{finding_id}/respond")
async def responder_finding(finding_id: str, payload: RespostaFindingIn,
                            x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.intelligence.finding_engine import FindingEngine

    ok = FindingEngine(_db()).responder(
        payload.company_id, finding_id, payload.acao,
        user_id=payload.user_id, dias_adiar=payload.dias)
    if not ok:
        raise HTTPException(400, "ação desconhecida ou finding inexistente")
    return {"ok": True}


@router.get("/recommendations")
async def recomendacoes(company_id: str, user_id: Optional[str] = None,
                        limite: int = Query(30, le=TETO_LISTA),
                        x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.intelligence.recommendation_service import RecommendationService

    return {"ok": True,
            "recomendacoes": RecommendationService(_db()).elegiveis(
                company_id, user_id=user_id, limite=limite)}


class RespostaRecomendacaoIn(BaseModel):
    company_id: str
    acao: str
    user_id: Optional[str] = None
    motivo: Optional[str] = None
    comentario: Optional[str] = None
    action_key: Optional[str] = None
    dias: int = 1


@router.post("/recommendations/{rec_id}/respond")
async def responder_recomendacao(rec_id: str, payload: RespostaRecomendacaoIn,
                                 x_internal_key: Optional[str] = Header(None)):
    """Registra a decisão. Quando aceita, abre o caminho canônico."""
    _autorizar(x_internal_key)
    from app.services.intelligence.execution import executar_recomendacao
    from app.services.intelligence.feedback_service import FeedbackService

    r = FeedbackService(_db()).registrar(
        company_id=payload.company_id, recommendation_id=rec_id,
        acao=payload.acao, user_id=payload.user_id, motivo=payload.motivo,
        comentario=payload.comentario, dias_adiar=payload.dias,
        action_key=payload.action_key)
    if not r.get("ok"):
        raise HTTPException(400, str(r.get("erro") or "não foi possível registrar"))

    if not r.get("executar"):
        return {"ok": True, "status": r.get("status"), "mensagem": r.get("mensagem")}

    saida = executar_recomendacao(
        _db(), company_id=payload.company_id, recommendation_id=rec_id,
        user_id=payload.user_id, action_key=payload.action_key or r.get("action_key"))
    return {"ok": True, "status": r.get("status"),
            "mensagem": saida.get("mensagem") or r.get("mensagem"),
            "execucao": saida}


@router.get("/preferences")
async def preferencias(company_id: str, cadencia: str = "daily",
                       user_id: Optional[str] = None,
                       x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.intelligence.briefing_service import BriefingService

    return {"ok": True,
            "perfil": BriefingService(_db()).perfil(company_id, cadencia=cadencia,
                                                    user_id=user_id)}


class PreferenciasIn(BaseModel):
    company_id: str
    cadencia: str = "daily"
    user_id: Optional[str] = None
    campos: dict = Field(default_factory=dict)


@router.put("/preferences")
async def salvar_preferencias(payload: PreferenciasIn,
                              x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.intelligence.briefing_service import BriefingService

    r = BriefingService(_db()).atualizar_preferencias(
        payload.company_id, cadencia=payload.cadencia,
        user_id=payload.user_id, campos=payload.campos)
    if not r:
        raise HTTPException(400, "nenhum campo válido para salvar")
    return {"ok": True, "perfil": r}


@router.get("/outcomes")
async def outcomes(company_id: str, dias: int = Query(30, le=180),
                   x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.intelligence.outcome_service import OutcomeService

    return {"ok": True,
            "outcomes": OutcomeService(_db()).do_periodo(company_id, dias=dias)}


@router.get("/memory")
async def memoria(company_id: str, x_internal_key: Optional[str] = Header(None)):
    """O que o AutoBrokers aprendeu sobre a corretora — SPEC-052 Lote 4."""
    _autorizar(x_internal_key)
    from app.services.memory_fabric import MemoryFabric

    fabric = MemoryFabric(_db())
    return {"ok": True, "fatos": fabric.fatos_da_corretora(company_id),
            "diagnostico": fabric.diagnostico(company_id=company_id)}


# ==========================================================================
# Plataforma — §27.2
# ==========================================================================


@admin.get("/overview")
async def visao_geral(dias: int = Query(7, le=90),
                      x_internal_key: Optional[str] = Header(None)):
    """Central de Inteligência — §26.1. Números medidos, sem estimativa."""
    _autorizar(x_internal_key)
    from datetime import datetime, timedelta, timezone

    from app.services.intelligence.feedback_service import FeedbackService

    db = _db().client
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()

    def _contar(tabela: str, filtros: Optional[dict] = None,
                campo_data: str = "created_at") -> int:
        try:
            q = db.table(tabela).select("id", count="exact").gte(campo_data, desde)
            for k, v in (filtros or {}).items():
                q = q.eq(k, v)
            r = q.execute()
            return int(getattr(r, "count", None) or len(r.data or []))
        except Exception:  # noqa: BLE001
            return -1

    qualidade = FeedbackService(_db()).qualidade(dias=dias)
    try:
        fontes = (db.table("intelligence_rules")
                  .select("rule_key, name, status, last_run_at, last_run_signals")
                  .order("last_run_at", desc=True).limit(40).execute()).data or []
    except Exception:  # noqa: BLE001
        fontes = []

    return {
        "ok": True, "periodo_dias": dias,
        "sinais": _contar("intelligence_signals"),
        "sinais_suprimidos": _contar("intelligence_signals", {"status": "suppressed"}),
        "findings_ativos": _contar("intelligence_findings", {"status": "active"}),
        "recomendacoes": _contar("recommendations"),
        "briefings": _contar("briefing_publications", {"status": "published"}),
        "candidatos_conhecimento": _contar("knowledge_candidates"),
        "qualidade": qualidade,
        "regras": fontes,
    }


@admin.get("/signals")
async def sinais(company_id: Optional[str] = None, tipo: Optional[str] = None,
                 severidade: Optional[str] = None, status: Optional[str] = None,
                 limite: int = Query(100, le=300),
                 x_internal_key: Optional[str] = Header(None)):
    """Sinais com filtro fechado — §26.2. Resumo já redigido na origem."""
    _autorizar(x_internal_key)
    db = _db().client
    try:
        q = (db.table("intelligence_signals")
             .select("id, company_id, signal_type, domain, severity, confidence, "
                     "trust_tier, status, summary_redacted, rule_key, rule_version, "
                     "priority_score, occurrence_count, created_at, valid_until"))
        for campo, valor in (("company_id", company_id), ("signal_type", tipo),
                             ("severity", severidade), ("status", status)):
            if valor:
                q = q.eq(campo, valor)
        linhas = (q.order("created_at", desc=True).limit(limite).execute()).data or []
    except Exception as exc:  # noqa: BLE001
        logger.error("[Admin] sinais: %s", type(exc).__name__)
        linhas = []
    return {"ok": True, "sinais": linhas}


@admin.get("/findings")
async def findings_admin(company_id: Optional[str] = None,
                         status: Optional[str] = None,
                         limite: int = Query(100, le=300),
                         x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    db = _db().client
    try:
        q = (db.table("intelligence_findings")
             .select("id, company_id, finding_type, title, summary, severity, "
                     "status, priority_score, confidence, delivery_count, "
                     "created_at, resolved_at, dismissed_at"))
        if company_id:
            q = q.eq("company_id", company_id)
        if status:
            q = q.eq("status", status)
        linhas = (q.order("priority_score", desc=True).limit(limite).execute()).data or []
    except Exception:  # noqa: BLE001
        linhas = []
    return {"ok": True, "findings": linhas}


@admin.get("/briefings")
async def briefings_admin(company_id: Optional[str] = None,
                          limite: int = Query(60, le=200),
                          x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    db = _db().client
    try:
        q = (db.table("briefing_publications")
             .select("id, company_id, briefing_type, period_start, period_end, "
                     "headline, item_count, critical_count, recommendation_count, "
                     "delivery_status, published_at, artifact_id"))
        if company_id:
            q = q.eq("company_id", company_id)
        linhas = (q.order("published_at", desc=True).limit(limite).execute()).data or []
    except Exception:  # noqa: BLE001
        linhas = []
    return {"ok": True, "briefings": linhas}


@admin.get("/demand-clusters")
async def clusters(status: Optional[str] = None,
                   limite: int = Query(60, le=200),
                   x_internal_key: Optional[str] = Header(None)):
    """Radar de Demanda — §26.5. Agregado e anônimo por construção."""
    _autorizar(x_internal_key)
    from app.services.intelligence.demand_cluster_service import DemandClusterService

    return {"ok": True,
            "clusters": DemandClusterService(_db()).listar(status=status, limite=limite)}


class ClusterIn(BaseModel):
    status: Optional[str] = None
    nota: Optional[str] = None
    outcome: Optional[str] = None
    candidato_auxiliar: Optional[str] = None
    candidato_skill: Optional[str] = None
    ator: Optional[str] = None


@admin.patch("/demand-clusters/{cluster_id}")
async def alterar_cluster(cluster_id: str, payload: ClusterIn,
                          x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.intelligence.demand_cluster_service import DemandClusterService

    ok = DemandClusterService(_db()).alterar(
        cluster_id, status=payload.status, nota=payload.nota,
        outcome=payload.outcome, candidato_auxiliar=payload.candidato_auxiliar,
        candidato_skill=payload.candidato_skill, ator=payload.ator)
    if not ok:
        raise HTTPException(400, "nada a alterar ou status inválido")
    return {"ok": True}


class FusaoIn(BaseModel):
    origem_id: str
    destino_id: str
    ator: Optional[str] = None


@admin.post("/demand-clusters/merge")
async def fundir_clusters(payload: FusaoIn,
                          x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.intelligence.demand_cluster_service import DemandClusterService

    ok = DemandClusterService(_db()).fundir(
        origem_id=payload.origem_id, destino_id=payload.destino_id,
        ator=payload.ator)
    if not ok:
        raise HTTPException(400, "não foi possível fundir")
    return {"ok": True}


@admin.get("/rules")
async def regras(x_internal_key: Optional[str] = Header(None)):
    """Regras com a qualidade observada de cada uma — §26.6."""
    _autorizar(x_internal_key)
    from app.services.intelligence.rule_engine import RuleEngine

    db = _db()
    motor = RuleEngine(db)
    try:
        linhas = (db.client.table("intelligence_rules").select("*")
                  .order("rule_key").limit(100).execute()).data or []
    except Exception:  # noqa: BLE001
        linhas = []
    qualidade = {q["rule_key"]: q for q in motor.qualidade_por_regra()}
    for r in linhas:
        r["qualidade"] = qualidade.get(r.get("rule_key"))
    return {"ok": True, "regras": linhas,
            "detectores_registrados": _detectores()}


def _detectores() -> list[str]:
    try:
        from app.services.intelligence.detectors import registrados

        return registrados()
    except Exception:  # noqa: BLE001
        return []


class RegraIn(BaseModel):
    status: Optional[str] = None
    configuracao: Optional[dict] = None
    ator: Optional[str] = None


@admin.patch("/rules/{rule_key}")
async def alterar_regra(rule_key: str, payload: RegraIn,
                        x_internal_key: Optional[str] = Header(None)):
    """Pausar, reativar ou recalibrar — sem deploy, com versão nova."""
    _autorizar(x_internal_key)
    from app.services.intelligence.rule_engine import RuleEngine

    motor = RuleEngine(_db())
    feito = False
    if payload.status:
        feito = motor.alterar_status(rule_key, payload.status, ator=payload.ator) or feito
    if payload.configuracao is not None:
        feito = motor.alterar_configuracao(rule_key, payload.configuracao,
                                           ator=payload.ator) or feito
    if not feito:
        raise HTTPException(400, "nada a alterar")
    return {"ok": True}


class ReplayIn(BaseModel):
    company_id: str
    rule_keys: Optional[list[str]] = None


@admin.post("/replay")
async def replay(payload: ReplayIn, x_internal_key: Optional[str] = Header(None)):
    """Roda os detectores agora, ignorando o intervalo — §26.6.

    Quem pede replay quer o resultado agora. O dedupe continua valendo: replay
    não duplica sinal, ele reavalia o estado.
    """
    _autorizar(x_internal_key)
    from app.services.intelligence.rule_engine import RuleEngine

    r = RuleEngine(_db()).varrer_empresa(payload.company_id,
                                         apenas=payload.rule_keys)
    return {"ok": True, "resumo": r.resumo(),
            "regras": [{"rule_key": x.rule_key, "executou": x.executou,
                        "sinais": x.sinais_criados, "motivo": x.motivo,
                        "erro": x.erro} for x in r.regras]}


@admin.get("/quality")
async def qualidade(dias: int = Query(30, le=180),
                    company_id: Optional[str] = None,
                    x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.intelligence.feedback_service import FeedbackService
    from app.services.intelligence.rule_engine import RuleEngine

    return {"ok": True,
            "geral": FeedbackService(_db()).qualidade(company_id=company_id, dias=dias),
            "por_regra": RuleEngine(_db()).qualidade_por_regra(dias=dias)}


@admin.get("/knowledge-candidates")
async def candidatos(escopo: Optional[str] = None,
                     limite: int = Query(50, le=200),
                     x_internal_key: Optional[str] = Header(None)):
    """Fila de curadoria — SPEC-052. Nada aqui está publicado."""
    _autorizar(x_internal_key)
    from app.services.intelligence.knowledge_candidate_adapter import \
        KnowledgeCandidateAdapter

    return {"ok": True,
            "candidatos": KnowledgeCandidateAdapter(_db()).fila(escopo=escopo,
                                                                limite=limite)}


class DecisaoCandidatoIn(BaseModel):
    aprovar: bool
    user_id: str
    nota: Optional[str] = None


@admin.post("/knowledge-candidates/{candidate_id}/decide")
async def decidir_candidato(candidate_id: str, payload: DecisaoCandidatoIn,
                            x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.intelligence.knowledge_candidate_adapter import \
        KnowledgeCandidateAdapter

    ok = KnowledgeCandidateAdapter(_db()).decidir(
        candidate_id, aprovar=payload.aprovar, user_id=payload.user_id,
        nota=payload.nota)
    if not ok:
        raise HTTPException(400, "não foi possível registrar a decisão")
    return {"ok": True}


@admin.get("/memory-health")
async def saude_da_memoria(x_internal_key: Optional[str] = Header(None)):
    """Diagnóstico da memória — SPEC-052 Lote 4.

    Existe porque a memória ficou zerada por dois meses sem ninguém notar:
    nenhuma tela mostrava a contagem. Agora ela é consultável.
    """
    _autorizar(x_internal_key)
    from app.services.memory_fabric import MemoryFabric

    return {"ok": True, "diagnostico": MemoryFabric(_db()).diagnostico()}
