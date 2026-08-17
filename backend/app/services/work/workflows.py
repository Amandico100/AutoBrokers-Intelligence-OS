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
import re
import time
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
    step_id: Optional[str] = None
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
        # Etapa já existe: retomada de um run que morreu no meio. O `idem`
        # é único por (empresa, run, etapa), então o insert bate na constraint
        # e a etapa antiga é reencontrada — é assim que a retomada não duplica.
        logger.info("[Workflows] etapa %s já registrada (retomada): %s", step_key, type(exc).__name__)
        step_id = _localizar_step(db, run_id, company_id, step_key)

    # A TENTATIVA, que faltava. Sem ela, uma etapa que só passou na quarta vez
    # é indistinguível de uma que passou de primeira: `work_steps` guarda o
    # ESTADO FINAL, não a história. Quem perde com isso é quem precisa
    # diagnosticar — o Admin da SPEC-061 e o Founder olhando um trabalho lento.
    attempt_id, numero = _abrir_tentativa(db, company_id, run_id, step_id)

    runs.evento(company_id, run_id, "step.started",
                nome if numero <= 1 else f"{nome} (tentativa {numero})",
                step_id=step_id)
    runs.marcar_progresso(run_id, company_id, step_key, min(95, ordinal * 20))

    inicio = time.monotonic()
    try:
        resultado = await fn()
    except Exception as exc:  # noqa: BLE001
        if step_id:
            _atualizar_step(db, step_id, {"status": "failed", "finished_at": _agora_iso()})
        _fechar_tentativa(db, attempt_id, status="failed", inicio=inicio, erro=exc)
        runs.evento(company_id, run_id, "step.failed", f"{nome}: não foi possível concluir",
                    step_id=step_id, severity="error")
        raise

    if step_id:
        _atualizar_step(db, step_id, {"status": "succeeded", "finished_at": _agora_iso()})
    _fechar_tentativa(db, attempt_id, status="succeeded", inicio=inicio)
    runs.evento(company_id, run_id, "step.completed", f"{nome}: concluído", step_id=step_id)
    return resultado


def _localizar_step(db: Any, run_id: str, company_id: str,
                    step_key: str) -> Optional[str]:
    """Reencontra a etapa de uma retomada. Sem isto, a segunda tentativa
    ficaria órfã — e a retomada é exatamente quando a tentativa importa."""
    try:
        r = (db.table("work_steps").select("id")
             .eq("work_run_id", run_id).eq("company_id", company_id)
             .eq("step_key", step_key).limit(1).execute())
        return (r.data or [{}])[0].get("id")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Workflows] etapa não localizada: %s", type(exc).__name__)
        return None


def _abrir_tentativa(db: Any, company_id: str, run_id: str,
                     step_id: Optional[str]) -> tuple[Optional[str], int]:
    """Abre a tentativa da etapa. Devolve `(id, numero)`.

    `work_attempts` é UNIQUE em `(work_step_id, attempt_number)`: o número vem
    de quantas já existem, e não de um contador em memória — o worker pode
    morrer e outro assumir, e o número precisa continuar certo mesmo assim.

    Falhar aqui **não** derruba o trabalho: contabilidade quebrada é ruim,
    trabalho do corretor perdido é pior.
    """
    if not step_id:
        return None, 1
    numero = 1
    try:
        anteriores = (db.table("work_attempts").select("attempt_number")
                      .eq("work_step_id", step_id)
                      .order("attempt_number", desc=True).limit(1).execute())
        if anteriores.data:
            numero = int(anteriores.data[0].get("attempt_number") or 0) + 1
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Workflows] tentativas anteriores: %s", type(exc).__name__)

    try:
        r = db.table("work_attempts").insert({
            "company_id": company_id, "work_run_id": run_id,
            "work_step_id": step_id, "attempt_number": numero,
            "worker_id": _worker_id(), "status": "running",
            "started_at": _agora_iso(),
        }).execute()
        return (r.data or [{}])[0].get("id"), numero
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Workflows] tentativa não aberta: %s", type(exc).__name__)
        return None, numero


def _fechar_tentativa(db: Any, attempt_id: Optional[str], *, status: str,
                      inicio: float, erro: Optional[BaseException] = None) -> None:
    """Fecha a tentativa com duração e, quando houve, a classe do erro.

    A mensagem do erro é **redigida**: exceção de provider carrega URL com
    query string, e query string carrega chave. `error_message_redacted` existe
    com esse nome porque o schema já sabia disso.
    """
    if not attempt_id:
        return
    campos: dict[str, Any] = {
        "status": status, "finished_at": _agora_iso(),
        "metrics": {"duracao_ms": int((time.monotonic() - inicio) * 1000)},
    }
    if erro is not None:
        campos["error_class"] = type(erro).__name__
        campos["error_message_redacted"] = _redigir(str(erro))
        # Erro de programação não é retentável: repetir um `TypeError` produz
        # o mesmo `TypeError` e queima a fila.
        campos["retryable"] = type(erro).__name__ not in (
            "TypeError", "ValueError", "KeyError", "AttributeError",
            "NotImplementedError", "AssertionError")
    try:
        db.table("work_attempts").update(campos).eq("id", attempt_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Workflows] tentativa não fechada: %s", type(exc).__name__)

    # SPEC-062 §18.2 — duração e falha de Work Run viram SLI aqui, no ponto em
    # que a tentativa fecha. Medir só o caminho feliz produziria um p95 lindo e
    # mentiroso: a lentidão mora justamente onde as coisas dão errado, e a
    # tentativa que falhou é a que interessa.
    try:
        from ..observability import sli as _sli

        _sli.registrar(_sli.WORK_RUN_DURACAO,
                       campos["metrics"]["duracao_ms"],
                       contexto={"status": status,
                                 "erro_classe": campos.get("error_class")})
        if status != "succeeded":
            _sli.registrar(_sli.WORK_RUN_FALHA, 1, unidade="evento",
                           contexto={"erro_classe": campos.get("error_class"),
                                     "retryable": campos.get("retryable")})
    except Exception:  # noqa: BLE001
        pass  # métrica nunca atrapalha o trabalho


_SEGREDO = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|authorization|bearer|"
    r"key)\b\s*[=:]\s*\S+|tvly-\S+|AIza\S+|fc-\S+|sk-\S+")


def _redigir(mensagem: str) -> str:
    """Nunca deixa segredo chegar ao banco por dentro de uma exceção."""
    return _SEGREDO.sub("[redigido]", (mensagem or ""))[:1000]


def _worker_id() -> str:
    try:
        from .runs import worker_id

        return worker_id()
    except Exception:  # noqa: BLE001
        return "desconhecido"


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

    # 🔴 FECHA a linha `delegated` que o motor abriu ao delegar.
    #
    # 📊 Medido em 17/08/2026: `routine_engine._criar_work_run_para_rotina`
    # insere um `routine_runs` com `status='delegated'` e
    # `output_preview='executando como Work Run'` — e NINGUÉM a fechava. A tela
    # do Auxiliar mostrava "executando como Work Run" para sempre, mesmo com o
    # Work Run já `completed`. O Founder ficou 15 minutos olhando uma execução
    # que tinha terminado.
    #
    # A execução de verdade grava a PRÓPRIA linha (dentro de
    # `_execute_routine`), com o relatório. Esta aqui é só o bilhete de
    # entrega, e bilhete de entrega precisa ser carimbado na chegada.
    try:
        db.table("routine_runs").update({
            "finished_at": _agora_iso(),
            "status": "ok",
            "output_preview": "entregue ao motor de trabalhos e concluído",
        }).eq("work_run_id", ctx["run_id"]).eq("status", "delegated").execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Bridge] nao consegui fechar o routine_run delegado: %s",
                       type(exc).__name__)

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


@registrar_workflow("portal.operation")
async def portal_operation(ctx: dict) -> str:
    """Executa uma OPERAÇÃO DE NEGÓCIO num portal, sob Work Run — SPEC-075 §13.

    A diferença para `bridge.portal.job` é onde o job nasce.

    📊 `bridge.portal.job` só ACOMPANHA um `portal_job_id` que o chamador já
    tem. Censo de 16/08/2026: nenhum código do repositório preenche
    `payload["portal_job_id"]`, e `grep -rn "bridge.portal.job"` só encontra a
    própria definição. A ponte foi construída e nunca foi ligada, porque
    faltava quem criasse o job com linhagem — e criar job com linhagem era
    justamente o que não existia.

    Este workflow fecha o circuito: recebe `operation_key` + `business_input`,
    e o `PortalExecutionGateway` resolve portal, conta e journey, cria o
    `portal_job` **já apontando para este Work Run**, e devolve o resultado
    canônico.

    🔴 O que este workflow NÃO faz: escolher journey, escolher conta, ler
    credencial. Ele passa o pedido de negócio adiante. Quem decide é o
    registro e o resolver — nunca o payload, que pode ter vindo de conversa.

    Por que a linhagem importa mais do que parece
    ---------------------------------------------
    Sem ela, um acionamento que deu errado não tem história: não dá para
    perguntar de que conversa veio, que rotina disparou, nem qual tool
    autorizou. Com ela, o `work_run_id` no `portal_job` responde as três — e é
    o mesmo id que a timeline do Work Run mostra ao corretor.
    """
    from app.services.portals import contracts as _C
    from app.services.portals.gateway import PortalExecutionGateway

    payload = ctx["payload"] or {}
    operation_key = str(payload.get("operation_key") or "").strip()
    if not operation_key:
        return "Pedido de portal sem operação de negócio."

    db = getattr(ctx["db"], "client", ctx["db"])

    async def _executar() -> str:
        req = _C.PortalExecutionRequest(
            company_id=str(ctx["company_id"]),
            operation_key=operation_key,
            business_input=dict(payload.get("business_input") or {}),
            # A linhagem vem do RUNTIME, não do payload. Se viesse do payload,
            # um chamador poderia atribuir o próprio trabalho a outro Work Run.
            work_run_id=str(ctx.get("run_id") or "") or None,
            skill_release_id=payload.get("skill_release_id"),
            tool_release_id=payload.get("tool_release_id"),
            agent_id=payload.get("agent_id"),
            user_id=payload.get("user_id"),
            session_id=payload.get("session_id"),
            insurer_key=payload.get("insurer_key"),
            portal_key_hint=payload.get("portal_key_hint"),
            account_id_hint=payload.get("account_id_hint"),
            # 🔴 `True` porque este workflow só é alcançável pelo SmithWorker,
            # que roda server-side. O payload de um Work Run é montado por
            # código, não digitado por modelo. Se um dia uma rota expuser
            # criação de Work Run com payload livre, esta linha vira o buraco —
            # e o teste de contrato existe para acender nesse dia.
            origem_confiavel=True,
            idempotency_key=payload.get("idempotency_key"),
            effect_class_autorizada=payload.get("effect_class_autorizada"),
            wait_mode=str(payload.get("wait_mode") or _C.ESPERA_AGUARDAR),
        )

        gw = PortalExecutionGateway(db)
        resultado = gw.executar(req)

        # Guarda o resultado canônico no contexto, para o passo seguinte e para
        # quem ler a timeline depois.
        ctx.setdefault("resultados", {})["portal"] = resultado.para_dict()

        if resultado.business_state == _C.NEGOCIO_PRECISA_HUMANO:
            ctx["runs"]._transicionar(ctx["run_id"], "waiting_approval", {})
            ctx["runs"].evento(ctx["company_id"], ctx["run_id"],
                               "approval.requested",
                               resultado.message or
                               "O portal precisa de uma ação sua para continuar.")
        elif resultado.business_state == _C.NEGOCIO_TALVEZ_COMMITADO:
            # 🔴 Nunca vira retry. O Work Run precisa PARAR aqui e chamar gente:
            # pode existir um pedido pago no nome do segurado, e a única coisa
            # pior que não terminar é terminar duas vezes.
            ctx["runs"].evento(ctx["company_id"], ctx["run_id"],
                               "effect.uncertain",
                               "A operação pode ter acontecido no portal. "
                               "Reconcilie antes de qualquer nova tentativa.")

        return resultado.business_state

    estado = await executar_passo(
        ctx, step_key=f"portal:{operation_key}", ordinal=1,
        nome=f"Executar `{operation_key}` no portal",
        step_type="portal", fn=_executar,
        capability_key="tenant.portal.execute", risk_level="high")

    return f"Operação `{operation_key}` no portal terminou como `{estado}`."


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
