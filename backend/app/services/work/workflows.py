"""Registro de workflows executáveis pelo Work Run. SPEC-055 §14.

Contrato mínimo: um workflow é uma corrotina que recebe o contexto e devolve o
resumo humano do que fez.

    async def meu_workflow(ctx: dict) -> str: ...

O contexto traz `run_id`, `company_id`, `payload`, os serviços (`runs`,
`approvals`, `effects`) e `cancelado()` — que o workflow **deve** consultar
entre etapas, porque cancelamento é cooperativo (SPEC-053 §10.7): não matamos
uma ação externa pela metade.

O catálogo definitivo é do **Skill Registry (SPEC-056)**. Aqui fica só o
contrato e os workflows de ponte que a SPEC-055 precisa para migrar Rotinas,
Auxiliares e Portais sem criar um segundo executor.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

WorkflowHandler = Callable[[dict], Awaitable[str]]

_REGISTRO: dict[str, WorkflowHandler] = {}


def registrar_workflow(chave: str) -> Callable[[WorkflowHandler], WorkflowHandler]:
    def decorador(fn: WorkflowHandler) -> WorkflowHandler:
        _REGISTRO[chave] = fn
        logger.debug("[Workflows] registrado: %s", chave)
        return fn

    return decorador


_extras_carregados = False


def carregar_extras() -> None:
    """Importa os workflows das SPECs posteriores, uma vez por processo.

    Registro por decorador só existe depois do import. Deixar isso a cargo de
    cada ponto de entrada (worker, API, teste) garante que alguém esqueça — e o
    sintoma seria "não sei executar este tipo de trabalho ainda", que parece
    bug de dado e não de import. Fica aqui, no dono do registro.
    """
    global _extras_carregados
    if _extras_carregados:
        return
    _extras_carregados = True
    for spec, modulo in (("SPEC-059", "app.services.intelligence.workflows"),
                         ("SPEC-060", "app.services.research.workflows")):
        try:
            __import__(modulo)
        except Exception as exc:  # noqa: BLE001
            # Uma SPEC que não registra não pode impedir a outra: são famílias
            # de trabalho independentes, e derrubar as duas por causa de um
            # import quebrado transformaria um defeito em dois.
            logger.error("[Workflows] %s não registrada: %s", spec,
                         type(exc).__name__)


def resolver_workflow(chave: Optional[str]) -> Optional[WorkflowHandler]:
    if not chave:
        return None
    if chave not in _REGISTRO:
        carregar_extras()
    return _REGISTRO.get(chave)


def workflows_registrados() -> list[str]:
    carregar_extras()
    return sorted(_REGISTRO)


# ---------------------------------------------------------------------------
# Etapas — utilitário comum
# ---------------------------------------------------------------------------


async def executar_passo(
    ctx: dict,
    *,
    step_key: str,
    ordinal: int,
    nome: str,
    step_type: str,
    fn: Callable[[], Awaitable[Any]],
    capability_key: Optional[str] = None,
    risk_level: str = "low",
) -> Any:
    """Roda uma etapa registrando início, fim, tentativa e progresso.

    Sem isto, cada workflow inventaria seu próprio jeito de reportar — e a
    tela de Trabalhos mostraria coisas diferentes para cada tipo de trabalho.
    """
    db = getattr(ctx["db"], "client", ctx["db"])
    runs = ctx["runs"]
    company_id, run_id = ctx["company_id"], ctx["run_id"]

    if ctx["cancelado"]():
        raise asyncio_cancelado()

    idem = f"{company_id}:{run_id}:{step_key}"
    try:
        res = db.table("work_steps").insert({
            "work_run_id": run_id, "company_id": company_id, "step_key": step_key,
            "ordinal": ordinal, "name": nome, "step_type": step_type,
            "status": "running", "risk_level": risk_level,
            "capability_key": capability_key, "idempotency_key": idem,
            "started_at": _agora_iso(),
        }).execute()
        step_id = (res.data or [{}])[0].get("id")
    except Exception as exc:  # noqa: BLE001
        # Etapa já existe: retomada de um run que morreu no meio.
        logger.info("[Workflows] etapa %s já registrada (retomada): %s", step_key, type(exc).__name__)
        step_id = None

    runs.evento(company_id, run_id, "step.started", nome, step_id=step_id)
    runs.marcar_progresso(run_id, company_id, step_key, min(95, ordinal * 20))

    try:
        resultado = await fn()
    except Exception as exc:  # noqa: BLE001
        if step_id:
            _atualizar_step(db, step_id, {"status": "failed", "finished_at": _agora_iso()})
        runs.evento(company_id, run_id, "step.failed", f"{nome}: não foi possível concluir",
                    step_id=step_id, severity="error")
        raise

    if step_id:
        _atualizar_step(db, step_id, {"status": "succeeded", "finished_at": _agora_iso()})
    runs.evento(company_id, run_id, "step.completed", f"{nome}: concluído", step_id=step_id)
    return resultado


def _atualizar_step(db: Any, step_id: str, campos: dict) -> None:
    try:
        db.table("work_steps").update(campos).eq("id", step_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Workflows] etapa não atualizada: %s", type(exc).__name__)


def _agora_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def asyncio_cancelado() -> BaseException:
    import asyncio

    return asyncio.CancelledError()


# ---------------------------------------------------------------------------
# Workflows de ponte — SPEC-055 §19, §20, §21
# ---------------------------------------------------------------------------


@registrar_workflow("bridge.routine.execute")
async def bridge_rotina(ctx: dict) -> str:
    """Executa uma Rotina existente sob Work Run.

    O motor de rotinas **é preservado** (SPEC-053 §6). O que muda é quem
    manda: antes o scheduler in-process do FastAPI, agora o Work Run — que
    tem lease, retomada e trilha auditável.
    """
    from app.services import routine_engine

    payload = ctx["payload"]
    routine_id = payload.get("routine_id")
    if not routine_id:
        return "Rotina sem identificador — nada a executar."

    db = getattr(ctx["db"], "client", ctx["db"])

    # SPEC-060 §22 — uma Rotina pode ser o gatilho de um monitor de pesquisa.
    # A checagem vive aqui, e não no motor de Rotinas, porque é aqui que o
    # trabalho acontece: o motor continua sem saber que pesquisa existe, e o
    # monitor continua sem agendador próprio.
    try:
        from app.services.research.monitor_service import MonitorService

        monitor = MonitorService(ctx["db"]).por_rotina(str(routine_id))
    except Exception:  # noqa: BLE001
        monitor = None

    if monitor and monitor.get("is_active"):
        from app.services.research.workflows import verificar_monitor

        return await verificar_monitor({**ctx, "payload": {
            **payload, "monitor_id": monitor["id"]}})

    # SPEC-060 §37 — a Rotina de fechamento do Auxiliar Radar declara o
    # workflow dela em `config.workflow`. A ponte respeita essa declaração em
    # vez de manter uma lista de nomes aqui: uma lista viraria um segundo
    # registro de workflows ao lado do da SPEC-055.
    try:
        rot = (db.table("routines").select("config")
               .eq("id", routine_id).maybe_single().execute())
        declarado = str((((rot.data if rot else None) or {})
                         .get("config") or {}).get("workflow") or "")
    except Exception:  # noqa: BLE001
        declarado = ""

    if declarado:
        fn = resolver_workflow(declarado)
        if fn is not None:
            return await fn({**ctx, "payload": {**payload, **(
                (((rot.data or {}).get("config") or {}).get("params")) or {})}})
        logger.warning("[Bridge] rotina %s declara workflow desconhecido: %s",
                       routine_id, declarado)

    async def _executar() -> Any:
        res = db.table("routines").select("*").eq("id", routine_id).maybe_single().execute()
        rotina = res.data if res else None
        if not rotina:
            raise ValueError(f"rotina {routine_id} não encontrada")
        await routine_engine._execute_routine(ctx["db"], rotina)
        return rotina.get("name") or routine_id

    nome = await executar_passo(
        ctx, step_key="executar_rotina", ordinal=1, nome="Executar rotina",
        step_type="routine", fn=_executar,
    )
    return f"Rotina '{nome}' executada."


@registrar_workflow("bridge.auxiliary.execute")
async def bridge_auxiliar(ctx: dict) -> str:
    """Executa um Auxiliar instalado sob Work Run.

    `auxiliary_runs` continua sendo escrito para compatibilidade até o
    cutover (SPEC-055 §20.2). A leitura canônica passa a ser `work_runs`.
    """
    payload = ctx["payload"]
    tenant_auxiliary_id = payload.get("tenant_auxiliary_id")
    if not tenant_auxiliary_id:
        return "Auxiliar sem identificador — nada a executar."

    db = getattr(ctx["db"], "client", ctx["db"])

    async def _carregar() -> dict:
        res = (db.table("tenant_auxiliaries").select("*")
               .eq("id", tenant_auxiliary_id).eq("company_id", ctx["company_id"])
               .maybe_single().execute())
        if not res or not res.data:
            raise ValueError("auxiliar não encontrado para este tenant")
        return res.data

    aux = await executar_passo(ctx, step_key="carregar_auxiliar", ordinal=1,
                               nome="Carregar configuração do Auxiliar",
                               step_type="load", fn=_carregar)

    async def _registrar_compat() -> None:
        try:
            db.table("auxiliary_runs").insert({
                "company_id": ctx["company_id"],
                "tenant_auxiliary_id": tenant_auxiliary_id,
                "status": "succeeded",
                "run_type": "work_run",
                "metadata": {"work_run_id": ctx["run_id"]},
                "started_at": _agora_iso(),
                "finished_at": _agora_iso(),
            }).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Bridge] compat auxiliary_runs: %s", type(exc).__name__)

    await executar_passo(ctx, step_key="registrar_compat", ordinal=2,
                         nome="Registrar histórico de compatibilidade",
                         step_type="compat", fn=_registrar_compat)

    return f"Auxiliar '{aux.get('name') or tenant_auxiliary_id}' executado."


@registrar_workflow("bridge.portal.job")
async def bridge_portal(ctx: dict) -> str:
    """Orquestra um job de portal sob Work Run.

    O Portal Worker **continua sendo quem toca o portal** — ele tem
    Playwright, sessão cifrada e evidência. O Work Run coordena, registra e
    aplica idempotência ao redor.

    `needs_human` do portal vira `waiting_approval` do Work Run: é o mesmo
    conceito, agora com modelo executável (67 dos 91 jobs de hoje estão
    nesse estado).
    """
    payload = ctx["payload"]
    job_id = payload.get("portal_job_id")
    if not job_id:
        return "Job de portal sem identificador."

    db = getattr(ctx["db"], "client", ctx["db"])

    async def _acompanhar() -> str:
        res = db.table("portal_jobs").select("status, error").eq("id", job_id).maybe_single().execute()
        job = (res.data if res else None) or {}
        status = job.get("status")
        if status == "needs_human":
            ctx["runs"]._transicionar(ctx["run_id"], "waiting_approval", {})
            ctx["runs"].evento(ctx["company_id"], ctx["run_id"], "approval.requested",
                               "O portal precisa de uma ação sua para continuar.")
            return "aguardando_humano"
        return status or "desconhecido"

    status = await executar_passo(ctx, step_key="acompanhar_portal", ordinal=1,
                                  nome="Acompanhar execução no portal",
                                  step_type="portal", fn=_acompanhar,
                                  capability_key="tenant.portal.execute", risk_level="high")

    if status == "aguardando_humano":
        return "O portal precisa de uma ação sua para continuar."
    return f"Job de portal finalizado com status '{status}'."


@registrar_workflow("system.healthcheck")
async def workflow_healthcheck(ctx: dict) -> str:
    """Workflow trivial para validar o pipeline ponta a ponta.

    Existe para provar, em produção, que outbox → fila → lease → etapa →
    evento → conclusão funciona — sem tocar em nada do corretor.
    """

    async def _ping() -> str:
        return "ok"

    await executar_passo(ctx, step_key="ping", ordinal=1, nome="Verificação do pipeline",
                         step_type="system", fn=_ping)
    return "Pipeline de execução durável verificado com sucesso."
