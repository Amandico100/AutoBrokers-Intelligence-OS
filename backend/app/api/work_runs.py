"""API de Work Runs — SPEC-055 §24.

Superfície mínima para o corretor acompanhar e decidir. Toda rota deriva o
tenant do contexto autenticado; `company_id` **nunca** vem do cliente — foi
esse seam que a SPEC-048 identificou como origem de vazamento entre corretoras.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/work", tags=["Work Runs"])


def _db() -> Any:
    return get_supabase_client().client


def _exigir_chave_interna(chave: Optional[str]) -> None:
    """Rotas internas exigem a chave de serviço."""
    import os

    esperada = (os.getenv("ADMIN_API_KEY") or "").strip()
    if not esperada or (chave or "").strip() != esperada:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="não autorizado")


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------


@router.get("/runs")
async def listar_runs(
    company_id: str = Query(..., description="tenant derivado da sessão pelo BFF"),
    status_filtro: Optional[str] = Query(None, alias="status"),
    limite: int = Query(50, le=200),
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
):
    _exigir_chave_interna(x_internal_key)
    try:
        q = (_db().table("work_runs")
             .select("id, outcome_title, outcome_type, status, progress_percent, "
                     "current_step_key, risk_level, source_type, requested_at, "
                     "started_at, finished_at, error_message, result_summary")
             .eq("company_id", company_id)
             .order("requested_at", desc=True)
             .limit(limite))
        if status_filtro:
            q = q.eq("status", status_filtro)
        return {"runs": (q.execute().data or [])}
    except Exception as exc:  # noqa: BLE001
        logger.error("[WorkAPI] falha ao listar: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="não foi possível listar os trabalhos")


@router.get("/runs/{run_id}")
async def detalhe_run(
    run_id: str,
    company_id: str = Query(...),
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
):
    _exigir_chave_interna(x_internal_key)
    db = _db()
    try:
        # eq(company_id) é a defesa contra IDOR — sem isso qualquer run seria
        # legível por qualquer tenant que soubesse o id.
        run = (db.table("work_runs").select("*")
               .eq("id", run_id).eq("company_id", company_id).maybe_single().execute())
        if not run or not run.data:
            raise HTTPException(status_code=404, detail="trabalho não encontrado")

        steps = (db.table("work_steps")
                 .select("step_key, ordinal, name, status, started_at, finished_at")
                 .eq("work_run_id", run_id).eq("company_id", company_id)
                 .order("ordinal").execute()).data or []

        eventos = (db.table("work_events")
                   .select("event_type, severity, message_human, created_at")
                   .eq("work_run_id", run_id).eq("company_id", company_id)
                   .order("created_at", desc=True).limit(100).execute()).data or []

        return {"run": run.data, "steps": steps, "timeline": eventos}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("[WorkAPI] falha no detalhe: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="não foi possível abrir o trabalho")


# ---------------------------------------------------------------------------
# Criação e controle
# ---------------------------------------------------------------------------


class CriarRunBody(BaseModel):
    company_id: str
    outcome_type: str
    outcome_title: str
    workflow_key: str
    idempotency_key: str
    source_type: str = "api"
    source_id: Optional[str] = None
    input_payload: dict = Field(default_factory=dict)
    requester_user_id: Optional[str] = None
    priority: int = 50
    risk_level: str = "low"
    cost_budget_brl: Optional[float] = None


@router.post("/runs", status_code=201)
async def criar_run(
    body: CriarRunBody,
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
):
    _exigir_chave_interna(x_internal_key)
    from app.services.work.runs import WorkRunService

    try:
        resultado = WorkRunService(get_supabase_client()).criar(
            company_id=body.company_id,
            source_type=body.source_type,
            source_id=body.source_id,
            outcome_type=body.outcome_type,
            outcome_title=body.outcome_title,
            workflow_key=body.workflow_key,
            idempotency_key=body.idempotency_key,
            input_payload=body.input_payload,
            requester_user_id=body.requester_user_id,
            priority=body.priority,
            risk_level=body.risk_level,
            cost_budget_brl=body.cost_budget_brl,
        )
        return resultado
    except Exception as exc:  # noqa: BLE001
        logger.error("[WorkAPI] falha ao criar run: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="não foi possível criar o trabalho")


@router.post("/runs/{run_id}/cancel")
async def cancelar_run(
    run_id: str,
    company_id: str = Query(...),
    usuario_id: Optional[str] = Query(None),
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
):
    _exigir_chave_interna(x_internal_key)
    from app.services.work.runs import WorkRunService

    db = _db()
    existe = (db.table("work_runs").select("id, status")
              .eq("id", run_id).eq("company_id", company_id).maybe_single().execute())
    if not existe or not existe.data:
        raise HTTPException(status_code=404, detail="trabalho não encontrado")

    WorkRunService(get_supabase_client()).solicitar_cancelamento(run_id, company_id, usuario_id)
    return {
        "ok": True,
        "mensagem": "Cancelamento solicitado. Etapas já concluídas são preservadas.",
    }


# ---------------------------------------------------------------------------
# Aprovações
# ---------------------------------------------------------------------------


@router.get("/approvals")
async def listar_aprovacoes(
    company_id: str = Query(...),
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
):
    _exigir_chave_interna(x_internal_key)
    from app.services.work.approvals import WorkApprovalService

    return {"approvals": WorkApprovalService(get_supabase_client()).pendentes(company_id)}


class DecidirBody(BaseModel):
    company_id: str
    usuario_id: str
    decisao: str  # approved | rejected | approved_with_edit
    payload_editado: Optional[dict] = None
    motivo: Optional[str] = None


@router.post("/approvals/{approval_id}/decide")
async def decidir_aprovacao(
    approval_id: str,
    body: DecidirBody,
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
):
    _exigir_chave_interna(x_internal_key)
    from app.services.work.approvals import ApprovalNotGranted, WorkApprovalService

    try:
        linha = WorkApprovalService(get_supabase_client()).decidir(
            company_id=body.company_id,
            approval_id=approval_id,
            decisao=body.decisao,
            usuario_id=body.usuario_id,
            payload_editado=body.payload_editado,
            motivo=body.motivo,
        )
        return {"ok": True, "approval": linha}
    except ApprovalNotGranted as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.error("[WorkAPI] falha ao decidir: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="não foi possível registrar a decisão")


# ---------------------------------------------------------------------------
# Observabilidade
# ---------------------------------------------------------------------------


@router.get("/health")
async def saude_work_os(
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
):
    """Saúde do Work OS. Números honestos, sem inferência."""
    _exigir_chave_interna(x_internal_key)
    db = _db()
    saida: dict = {}

    def _contar(tabela: str, **filtros) -> int:
        try:
            q = db.table(tabela).select("id", count="exact")
            for k, v in filtros.items():
                q = q.eq(k, v)
            return q.execute().count or 0
        except Exception:  # noqa: BLE001
            return -1

    saida["runs_na_fila"] = _contar("work_runs", status="queued")
    saida["runs_executando"] = _contar("work_runs", status="running")
    saida["runs_aguardando_aprovacao"] = _contar("work_runs", status="waiting_approval")
    saida["outbox_pendente"] = _contar("work_queue_outbox", status="pending")
    saida["outbox_abandonado"] = _contar("work_queue_outbox", status="abandoned")
    saida["efeitos_desconhecidos"] = _contar("work_effects", status="unknown")

    try:
        from app.core.redis import get_async_redis_client
        from app.services.work.queue import WorkQueue

        saida["fila"] = await WorkQueue(await get_async_redis_client()).profundidade()
    except Exception as exc:  # noqa: BLE001
        saida["fila"] = {"erro": type(exc).__name__}

    return saida


@router.get("/cutover")
async def cutover_progresso():
    """Progresso do cutover do grafo para o Tool Gateway. SPEC-057 §Bloco I.

    Responde a única pergunta que importa antes de virar a chave: **em quantas
    conversas a decisão nova bateu com a antiga?** Sem este número, "está
    rodando em shadow" é uma afirmação sem prova.
    """
    import os

    from app.agents.gateway_cutover import modo_atual, progresso

    p = progresso(get_supabase_client())
    p["modo"] = modo_atual()
    p["authority_strict"] = str(
        os.getenv("AUTHORITY_STRICT_MODE", "")).strip().lower() in ("1", "true", "yes", "on")
    return p
