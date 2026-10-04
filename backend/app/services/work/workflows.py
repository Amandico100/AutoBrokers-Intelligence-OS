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

import asyncio
import logging
import re
import time
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

WorkflowHandler = Callable[[dict], Awaitable[str]]

_REGISTRO: dict[str, WorkflowHandler] = {}


def registrar_workflow(chave: str, *, idade_maxima_s: Optional[int] = None,
                       ao_desistir: Optional[Callable[[Any, dict, str], None]] = None,
                       ) -> Callable[[WorkflowHandler], WorkflowHandler]:
    """Registra um workflow. SPEC-129-A: o registro também diz como o Work OS DESISTE dele.

    · `idade_maxima_s` (D-129A-5) — quanto tempo, desde o `requested_at`, o trabalho ainda
      vale a pena. Passou disso sem rodar → `expired` (o despertador e o re-despacho de
      `runs.py` leem `handler.idade_maxima_s`). Sem declarar: o padrão do Work OS (2 h).
    · `ao_desistir(db, run, motivo)` — o que o workflow faz quando o Work OS desiste dele
      (expirou sem rodar, ou um efeito externo ficou incerto). A ponte da cobrança grava o
      aviso legível e fecha o `routine_runs` delegado.
    """
    def decorador(fn: WorkflowHandler) -> WorkflowHandler:
        if idade_maxima_s is not None:
            fn.idade_maxima_s = int(idade_maxima_s)  # type: ignore[attr-defined]
        if ao_desistir is not None:
            fn.ao_desistir = ao_desistir  # type: ignore[attr-defined]
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


#: SPEC-129-A §6 — o que uma etapa faz FORA do banco do Work OS (D-129A-4):
#:   nenhum      só lê/calcula. Interrompida → nova tentativa. Concluída SEM `guardar`
#:               → roda de novo na retomada (o comportamento de antes — ver `executar_passo`)
#:   idempotente repetir não duplica (o portal_job tem chave). Interrompida → nova tentativa
#:   externo     fala com o mundo (mensagem, cobrança, pedido). Interrompida → `EfeitoIncerto`
EFEITOS = ("nenhum", "idempotente", "externo")

#: `guardar` aceita só isto: ids e estados. Nunca texto livre, nunca objeto aninhado, nunca PII.
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_FICHA = re.compile(r"^[A-Za-z0-9_.:\-]{1,120}$")
#: 8+ dígitos seguidos (com a pontuação de CPF, CNPJ, telefone ou cartão no meio) = PII provável
_DIGITOS_DE_PESSOA = re.compile(r"\d(?:[\s.\-/()]*\d){7,}")
_INT_MAXIMO_GUARDAVEL = 10 ** 7   # um CPF sem pontuação é um int de 11 dígitos


def _guardavel(valor: Any) -> bool:
    """O valor pode ir para `work_steps.output_summary`? (SPEC-129-A §6: "nunca PII")."""
    if valor is None or isinstance(valor, bool):
        return True
    if isinstance(valor, int):
        return abs(valor) < _INT_MAXIMO_GUARDAVEL
    if isinstance(valor, str):
        if _UUID.match(valor):
            return True
        return bool(_FICHA.match(valor)) and not _DIGITOS_DE_PESSOA.search(valor)
    return False


def _o_que_guardar(resultado: Any, guardar: tuple, step_key: str) -> dict:
    """Só as chaves DECLARADAS, só valores guardáveis. O resto não chega ao banco."""
    if not guardar or not isinstance(resultado, dict):
        return {}
    saida: dict = {}
    for chave in guardar:
        if chave not in resultado:
            continue
        valor = resultado[chave]
        if _guardavel(valor):
            saida[chave] = valor
        else:
            # o NOME da chave pode ir ao log; o valor, nunca
            logger.warning("[Workflows] etapa %s: `%s` não é guardável (texto livre, objeto ou PII) — "
                           "não foi para o banco", step_key, chave)
    return saida


def _runs_mod():
    """`runs.py` — o dono de `Esperando`, `ESPERANDO` e `EfeitoIncerto` (SPEC-129-A §6).

    Import tardio, e sem passar por `app/services/__init__.py` quando dá: este módulo é
    carregado por caminho em testes que não têm (nem precisam de) o pacote inteiro.
    `runs.py` é stdlib pura, então carregá-lo pelo arquivo é seguro.
    """
    import sys

    mod = sys.modules.get("app.services.work.runs")
    if mod is not None and hasattr(mod, "Esperando"):
        return mod
    try:
        from app.services.work import runs as _R

        return _R
    except Exception:  # noqa: BLE001
        import importlib.util
        import os

        caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs.py")
        spec = importlib.util.spec_from_file_location("app.services.work.runs", caminho)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["app.services.work.runs"] = mod
        spec.loader.exec_module(mod)
        return mod


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
    efeito: str = "nenhum",
    guardar: tuple = (),
) -> Any:
    """Roda uma etapa registrando início, fim, tentativa e progresso.

    Sem isto, cada workflow inventaria seu próprio jeito de reportar — e a
    tela de Trabalhos mostraria coisas diferentes para cada tipo de trabalho.

    🔴 SPEC-129-A §6 — a RETOMADA (o run morreu, foi recuperado ou acordou):

        etapa `succeeded`  → devolve `output_summary[guardar]` SEM chamar `fn` e sem abrir
                             tentativa (D-129A-4: o que terminou não repete). ⚠️ Vale quando a
                             etapa declarou `guardar` ou um `efeito` ≠ "nenhum". Uma etapa
                             "nenhum" sem `guardar` (só leitura/cálculo, e cujo VALOR o chamador
                             consome) roda de novo, como antes: devolver `None` ali quebraria
                             a retomada dos workflows que usam o resultado, e repeti-la não tem
                             efeito fora do banco.
        etapa `running`    → foi interrompida no meio. `nenhum`/`idempotente`: nova tentativa.
                             `externo`: levanta `EfeitoIncerto` — pode ter acontecido; não repete.
        etapa `waiting_input` → a etapa DORMIU (devolveu `runs.ESPERANDO`): roda de novo, é a
                             conferência seguinte.

    `fn` que devolve `runs.ESPERANDO` (ela chamou `runs.dormir`): a etapa fica `waiting_input`
    — NUNCA `succeeded`, senão o próximo despertar pegaria um resultado guardado e não
    conferiria nada.

    `guardar` (ids e estados curtos — ver `_guardavel`) é o que vai para `output_summary` e o
    que a retomada devolve. Na primeira passagem, quem chama recebe o resultado inteiro de `fn`.
    """
    if efeito not in EFEITOS:
        raise ValueError(f"efeito inválido: {efeito!r} (use {EFEITOS})")
    guardar = tuple(guardar or ())
    _R = _runs_mod()

    db = getattr(ctx["db"], "client", ctx["db"])
    runs = ctx["runs"]
    company_id, run_id = ctx["company_id"], ctx["run_id"]

    if ctx["cancelado"]():
        raise asyncio_cancelado()

    idem = f"{company_id}:{run_id}:{step_key}"
    step_id: Optional[str] = None
    anterior: Optional[dict] = None
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
        anterior = _localizar_step(db, run_id, company_id, step_key)
        step_id = (anterior or {}).get("id")

    status_anterior = str((anterior or {}).get("status") or "")
    saida_anterior = (anterior or {}).get("output_summary")
    saida_anterior = saida_anterior if isinstance(saida_anterior, dict) else {}

    # 🔴 O que TERMINOU não repete (achado 7 da SPEC-129-A: o insert batia na trava, a etapa
    # era reencontrada e `fn()` rodava de novo — a cobrança, o pedido no portal, tudo).
    if status_anterior == "succeeded" and (guardar or efeito != "nenhum"):
        runs.evento(company_id, run_id, "step.reused",
                    f"{nome}: já concluída antes — não foi repetida", step_id=step_id,
                    severity="debug")
        return {k: saida_anterior[k] for k in guardar if k in saida_anterior} if guardar else None

    # 🔴 Efeito EXTERNO interrompido no meio: pode ter acontecido (D-129A-4). Não repete — nem
    # agora, nem numa volta futura (a marca fica na etapa).
    incerta = status_anterior == "running" or (
        status_anterior == "failed" and bool(saida_anterior.get("efeito_incerto")))
    if efeito == "externo" and incerta:
        if step_id:
            _atualizar_step(db, step_id, {"status": "failed", "finished_at": _agora_iso(),
                                          "output_summary": {"efeito_incerto": True}},
                            company_id=company_id)
            _fechar_tentativas_abertas(db, company_id, step_id)
        runs.evento(company_id, run_id, "step.failed",
                    f"{nome}: foi interrompida no meio e pode ter acontecido — não será repetida",
                    step_id=step_id, severity="warning")
        raise _R.EfeitoIncerto(f"etapa '{step_key}' interrompida no meio")

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
            _atualizar_step(db, step_id, {"status": "failed", "finished_at": _agora_iso()},
                            company_id=company_id)
        _fechar_tentativa(db, attempt_id, status="failed", inicio=inicio, erro=exc)
        runs.evento(company_id, run_id, "step.failed", f"{nome}: não foi possível concluir",
                    step_id=step_id, severity="error")
        raise

    if isinstance(resultado, _R.Esperando):
        # 🔴 DORMIU: a etapa NÃO termina `succeeded` (o próximo despertar confere de novo).
        if step_id:
            _atualizar_step(db, step_id, {"status": "waiting_input"}, company_id=company_id)
        _fechar_tentativa(db, attempt_id, status="waiting", inicio=inicio)
        return resultado

    campos: dict = {"status": "succeeded", "finished_at": _agora_iso()}
    if guardar:
        campos["output_summary"] = _o_que_guardar(resultado, guardar, step_key)
    if step_id:
        _atualizar_step(db, step_id, campos, company_id=company_id)
    _fechar_tentativa(db, attempt_id, status="succeeded", inicio=inicio)
    runs.evento(company_id, run_id, "step.completed", f"{nome}: concluído", step_id=step_id)
    return resultado


def _localizar_step(db: Any, run_id: str, company_id: str,
                    step_key: str) -> Optional[dict]:
    """Reencontra a etapa de uma retomada — com o STATUS e o que ela guardou.

    Sem isto, a segunda tentativa ficaria órfã — e a retomada é exatamente
    quando a tentativa importa. E sem o status, uma etapa concluída rodaria de
    novo (SPEC-129-A, achado 7)."""
    try:
        r = (db.table("work_steps").select("id, status, output_summary")
             .eq("work_run_id", run_id).eq("company_id", company_id)
             .eq("step_key", step_key).limit(1).execute())
        linha = (r.data or [{}])[0]
        return dict(linha) if linha and linha.get("id") else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Workflows] etapa não localizada: %s", type(exc).__name__)
        return None


def _fechar_tentativas_abertas(db: Any, company_id: str, step_id: str) -> None:
    """A tentativa que o processo morto deixou `running` fecha como interrompida."""
    try:
        (db.table("work_attempts").update({
            "status": "failed", "finished_at": _agora_iso(), "error_class": "EfeitoIncerto",
            "error_message_redacted": "interrompida no meio: o processo parou", "retryable": False,
        }).eq("work_step_id", step_id).eq("company_id", company_id).eq("status", "running").execute())
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Workflows] tentativas abertas não fechadas: %s", type(exc).__name__)


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
        # `waiting` (a etapa dormiu — SPEC-129-A) não é falha: é uma conferência que achou
        # o portal ainda trabalhando.
        if status not in ("succeeded", "waiting"):
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


def _atualizar_step(db: Any, step_id: str, campos: dict,
                    company_id: Optional[str] = None) -> None:
    try:
        q = db.table("work_steps").update(campos).eq("id", step_id)
        if company_id:
            q = q.eq("company_id", str(company_id))   # CLAUDE.md §7: o filtro no código
        q.execute()
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


#: D-129A-5 — a cobrança atrasada 2 h já saiu da janela útil; a rotina volta na próxima ocorrência
IDADE_MAXIMA_DA_ROTINA_S = 2 * 3600


def _ler_ts(valor: Any):
    """`timestamptz` do PostgREST → `datetime` com fuso (ou `None`)."""
    from datetime import datetime, timezone

    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(str(valor).strip().replace("Z", "+00:00").replace(" ", "T", 1))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _agora():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def _linha_do_run(db: Any, run_id: str, company_id: str, colunas: str) -> dict:
    try:
        r = (db.table("work_runs").select(colunas)
             .eq("id", run_id).eq("company_id", str(company_id)).limit(1).execute())
        return dict((r.data or [{}])[0] or {})
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Workflows] run %s ilegível: %s", run_id, type(exc).__name__)
        return {}


def _rotina_desistiu(db: Any, run: dict, motivo: str) -> None:
    """`ao_desistir` da ponte de rotinas (SPEC-129-A §6, "A COBRANÇA").

    O Work OS desistiu do run (expirou sem rodar, ou a etapa externa ficou incerta). A
    corretora PRECISA ver isso — uma cobrança que some em silêncio é pior que uma que falha:
      · evento `warning` legível na linha do tempo do trabalho
      · o `routine_runs` `delegated` fecha como `error` (antes só o sucesso o fechava, e a
        tela mostrava "executando como Work Run" para sempre)
    Nunca levanta: quem chama é o laço do Work OS.
    """
    run_id, company_id = str(run.get("id") or ""), str(run.get("company_id") or "")
    if not run_id or not company_id:
        return
    db = getattr(db, "client", db)
    nome, cobranca = "", False
    try:
        entrada = (_linha_do_run(db, run_id, company_id, "input_payload").get("input_payload") or {})
        routine_id = entrada.get("routine_id") if isinstance(entrada, dict) else None
        if routine_id:
            r = (db.table("routines").select("*").eq("id", routine_id)
                 .eq("company_id", company_id).limit(1).execute())
            rotina = (r.data or [None])[0] or {}
            nome = str(rotina.get("name") or "")
            try:
                from app.services.billing_collection import is_billing_routine

                cobranca = bool(rotina) and bool(is_billing_routine(rotina))
            except Exception:  # noqa: BLE001
                cobranca = False
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Bridge] rotina do run %s ilegível: %s", run_id, type(exc).__name__)

    oque = "A cobrança" if cobranca else "A rotina"
    rotulo = f"{oque} “{nome}”" if nome else oque
    # Quem chama: o worker no `EfeitoIncerto` (passa `status='failed'`) ou o despertador /
    # re-despacho ao expirar (passa a linha como estava ANTES: queued, retry_scheduled…).
    incerta = str(run.get("status") or "") == "failed"
    expirou = not incerta
    texto = (f"{rotulo} foi interrompida no meio e não será repetida sozinha: {motivo}" if incerta
             else f"{rotulo} não rodou: {motivo}")
    try:
        _runs_mod().WorkRunService(db).evento(
            company_id, run_id, "routine.nao_concluida", texto[:900], severity="warning",
            payload={"status": "expired" if expirou else "failed"})
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Bridge] aviso da rotina não registrado: %s", type(exc).__name__)
    try:
        db.table("routine_runs").update({
            "finished_at": _agora_iso(),
            "status": "error",
            "error": texto[:900],
            "output_preview": "o motor de trabalhos desistiu desta execução",
        }).eq("work_run_id", run_id).eq("status", "delegated").execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Bridge] routine_run delegado não fechado: %s", type(exc).__name__)


def _expirar_no_handler(ctx: dict, motivo: str) -> Any:
    """O run chegou ao handler já velho demais (mensagem atrasada no Redis): `expired`, não roda.

    O despertador e o re-despacho expiram o que está na FILA; uma mensagem que sobreviveu na
    fila do Redis além do limite chega direto aqui. CAS `running`(meu token) → `expired`.
    Devolve `ESPERANDO`: o run já está fechado, e o worker não escreve por cima.
    """
    _R = _runs_mod()
    runs, run_id, company_id = ctx["runs"], ctx["run_id"], ctx["company_id"]
    if runs._transicionar(run_id, "expired", {
        "finished_at": _agora_iso(), "error_code": _R.CODIGO_EXPIRADO_PELA_IDADE,
        "error_message": motivo, "wake_at": None,
        "lease_owner": None, "lease_token": None, "lease_expires_at": None,
    }, de="running", lease_token=ctx.get("lease_token"), company_id=company_id):
        runs.evento(company_id, run_id, "run.expired", motivo, severity="warning",
                    payload={"motivo": _R.CODIGO_EXPIRADO_PELA_IDADE})
        _rotina_desistiu(ctx["db"], {"id": run_id, "company_id": company_id,
                                     "status": "expired"}, motivo)
    return _R.ESPERANDO


@registrar_workflow("bridge.routine.execute", idade_maxima_s=IDADE_MAXIMA_DA_ROTINA_S,
                    ao_desistir=_rotina_desistiu)
async def bridge_rotina(ctx: dict) -> str:
    """Executa uma Rotina existente sob Work Run.

    O motor de rotinas **é preservado** (SPEC-053 §6). O que muda é quem
    manda: antes o scheduler in-process do FastAPI, agora o Work Run — que
    tem lease, retomada e trilha auditável.

    🔴 SPEC-129-A (a cobrança ENVIA): os TRÊS ramos — monitor de pesquisa, `config.workflow`
    e o motor de rotinas — passam por UM `executar_passo("executar_rotina", efeito="externo")`:
      · morto DEPOIS do passo e antes do `concluir` → a retomada não roda a rotina de novo
      · morto NO MEIO do passo → `EfeitoIncerto` (`failed efeito_incerto`), nunca repete
      · velho demais (> 2 h do pedido) → `expired`, sem rodar, com aviso legível
    O `billing_sent_log` continua sendo a segunda linha de defesa.
    """
    from app.services import routine_engine

    payload = ctx["payload"]
    routine_id = payload.get("routine_id")
    if not routine_id:
        return "Rotina sem identificador — nada a executar."

    db = getattr(ctx["db"], "client", ctx["db"])
    company_id = str(ctx["company_id"])
    _R = _runs_mod()

    # D-129A-5 — a IDADE, por `requested_at`. Só antes de a etapa existir: depois dela, quem
    # decide é a etapa (concluída → não repete; interrompida → efeito incerto).
    if _localizar_step(db, ctx["run_id"], company_id, "executar_rotina") is None:
        pedido = _ler_ts(_linha_do_run(db, ctx["run_id"], company_id,
                                       "requested_at").get("requested_at"))
        if pedido is not None and (_agora() - pedido).total_seconds() > IDADE_MAXIMA_DA_ROTINA_S:
            return _expirar_no_handler(
                ctx, f"Expirou sem rodar: passou de {IDADE_MAXIMA_DA_ROTINA_S / 3600:g} h desde o "
                     "pedido. A próxima ocorrência da rotina faz o trabalho; nada foi enviado.")

    async def _executar() -> Any:
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

        res = (db.table("routines").select("*").eq("id", routine_id)
               .eq("company_id", company_id).maybe_single().execute())
        rotina = res.data if res else None
        if not rotina:
            raise ValueError(f"rotina {routine_id} não encontrada")

        # SPEC-060 §37 — a Rotina de fechamento do Auxiliar Radar declara o
        # workflow dela em `config.workflow`. A ponte respeita essa declaração em
        # vez de manter uma lista de nomes aqui: uma lista viraria um segundo
        # registro de workflows ao lado do da SPEC-055.
        config = rotina.get("config") or {}
        declarado = str((config if isinstance(config, dict) else {}).get("workflow") or "")
        if declarado:
            fn = resolver_workflow(declarado)
            if fn is not None:
                return await fn({**ctx, "payload": {**payload, **(
                    (config.get("params") if isinstance(config, dict) else None) or {})}})
            logger.warning("[Bridge] rotina %s declara workflow desconhecido: %s",
                           routine_id, declarado)

        # ⚠️ SPEC-EXTRA-001 — o run VIAJA. Sem esta linha a cobrança executada
        #    pela ponte grava um ledger sem dizer qual trabalho a produziu, e
        #    a recusa da porta não tem Work Event onde cair (P-098-RUN-NOS-JOBS).
        await routine_engine._execute_routine(
            ctx["db"], rotina, work_run_id=str(ctx.get("run_id") or "") or None)
        return f"Rotina '{rotina.get('name') or routine_id}' executada."

    try:
        resumo = await executar_passo(
            ctx, step_key="executar_rotina", ordinal=1, nome="Executar rotina",
            step_type="routine", fn=_executar, efeito="externo",
        )
    except _R.EfeitoIncerto:
        raise   # o worker grava `failed efeito_incerto` e chama `_rotina_desistiu`
    except Exception as exc:  # noqa: BLE001
        # A rotina FALHOU (e disse que falhou): o bilhete de entrega também é carimbado.
        try:
            db.table("routine_runs").update({
                "finished_at": _agora_iso(), "status": "error",
                "error": f"o trabalho falhou: {type(exc).__name__}",
            }).eq("work_run_id", ctx["run_id"]).eq("status", "delegated").execute()
        except Exception as exc_r:  # noqa: BLE001
            logger.warning("[Bridge] routine_run delegado não fechado: %s", type(exc_r).__name__)
        raise
    if isinstance(resumo, _R.Esperando):
        return resumo   # um workflow declarado dormiu: o bilhete fecha quando ele terminar

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

    if resumo is None:
        # Retomada: a etapa já tinha terminado antes do reinício — não rodou de novo.
        return f"Rotina '{routine_id}' já executada antes do reinício — não foi repetida."
    return str(resumo)


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


# ---------------------------------------------------------------------------
# A espera do portal — SPEC-129-A §6 (sem `time.sleep`, sem segurar processo)
# ---------------------------------------------------------------------------

#: prazo da espera enquanto o portal-worker TRABALHA (job `queued`/`running`). O cálculo
#: mais longo medido é 📊 413–420 s (ficha §1.3); 2 h cobre fila cheia sem esperar para sempre.
PRAZO_DO_PORTAL_S = 2 * 3600
#: D-129A-7 — `needs_human`: a espera é por GENTE. Relógio em backoff e prazo de 24 h.
PRAZO_DO_HUMANO_S = 24 * 3600
BACKOFF_DO_HUMANO_S = (300, 600, 1200, 2400, 3600)   # 5 → 10 → 20 → 40 → 60 min (teto 60)
ESPERA_PORTAL = "portal"
ESPERA_HUMANO = "portal_humano"


class _EsperaVencida(Exception):
    """O prazo da espera passou. O handler falha o run com a frase humana (não repete nada)."""


def _ler_job_da_corretora(db: Any, job_id: str, company_id: str) -> Optional[dict]:
    """O `portal_job` DESTA corretora (CLAUDE.md §7: o filtro no código, sempre)."""
    try:
        r = (db.table("portal_jobs").select("id, status, evidence, error, params")
             .eq("id", job_id).eq("company_id", str(company_id)).limit(1).execute())
        dados = r.data or []
        return dict(dados[0]) if dados else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Workflows] portal_job %s ilegível: %s", job_id, type(exc).__name__)
        return None


async def _conferir_o_portal(ctx: dict, job_id: str, *, passo: str,
                             prazo_s: int = PRAZO_DO_PORTAL_S) -> Any:
    """UMA conferência do job: terminou → `{"business_state", "status"}`; senão DORME.

    Dormir = `runs.dormir` (CAS `running`(meu token) → `waiting_input` + `wake_at` +
    `wait_for`): o run fica sem dono, nenhum processo segura a espera, e o despertador o
    devolve à fila. Quem chama é a etapa `:aguardar` — e ela NÃO termina `succeeded`
    dormindo (`executar_passo` a deixa `waiting_input`).

      job `queued`/`running`   → dorme o intervalo normal (`runs.ESPERA_PADRAO_S`)
      job `needs_human`        → D-129A-7: dorme em backoff 5→10→20→40→60 min, prazo 24 h,
                                 e avisa UMA vez (na entrada nessa espera)
      prazo da espera vencido  → `_EsperaVencida`; o `portal_job` fica intocado
    """
    from app.services.portals import contracts as _C
    from app.services.portals.gateway import STATUS_EM_CURSO, traduzir_estado

    db = getattr(ctx["db"], "client", ctx["db"])
    runs, run_id, company_id = ctx["runs"], ctx["run_id"], str(ctx["company_id"])
    job = await asyncio.to_thread(_ler_job_da_corretora, db, job_id, company_id)
    status = str((job or {}).get("status") or "")

    tipo = ESPERA_PORTAL
    if job and status not in STATUS_EM_CURSO:
        estado = traduzir_estado(job)
        if estado != _C.NEGOCIO_PRECISA_HUMANO:
            return {"business_state": estado, "status": status}
        tipo = ESPERA_HUMANO

    espera = ctx.get("espera") if isinstance(ctx.get("espera"), dict) else {}
    mesma = espera.get("ref") == job_id and espera.get("tipo") == tipo
    prazo = _ler_ts(espera.get("prazo")) if mesma else None
    if prazo is not None and _agora() >= prazo:
        raise _EsperaVencida(tipo)

    if tipo == ESPERA_HUMANO:
        if not mesma:
            runs.evento(company_id, run_id, "portal.needs_human",
                        "O portal precisa de uma ação de alguém da equipe para continuar. "
                        "Confiro de novo em 5 min, e depois com intervalos maiores, por até 24 h.",
                        severity="warning", payload={"portal_job_id": job_id})
        vezes = int(espera.get("acordou") or 0) if mesma else 0
        intervalo: Optional[int] = BACKOFF_DO_HUMANO_S[min(vezes, len(BACKOFF_DO_HUMANO_S) - 1)]
        prazo_da_espera = PRAZO_DO_HUMANO_S
    else:
        intervalo = None   # `runs.ESPERA_PADRAO_S`
        prazo_da_espera = int(prazo_s)

    return runs.dormir(run_id, lease_token=ctx.get("lease_token"), acordar_em_s=intervalo,
                       wait_for={"tipo": tipo, "ref": job_id, "prazo_s": prazo_da_espera,
                                 "passo": passo},
                       company_id=company_id)


def _falhar_pela_espera(ctx: dict, tipo: str, operacao: str) -> Any:
    """Prazo vencido: o run FALHA com a frase humana, pelo CAS do próprio token.

    Devolve `ESPERANDO` — o run já está fechado, e o worker não pode escrever `completed`
    por cima. O `portal_job` NÃO é tocado: tempo esgotado não é prova de que nada aconteceu
    (`gateway.py`, o mesmo princípio do "tempo esgotado NÃO é falha" do modo `await`).
    """
    _R = _runs_mod()
    horas = (PRAZO_DO_HUMANO_S if tipo == ESPERA_HUMANO else PRAZO_DO_PORTAL_S) / 3600
    if tipo == ESPERA_HUMANO:
        mensagem = (f"Ninguém resolveu a pendência do portal em {horas:g} h ({operacao}). "
                    "O trabalho foi encerrado sem repetir nada; o pedido no portal ficou como está.")
    else:
        mensagem = (f"O portal não respondeu em {horas:g} h ({operacao}). O trabalho foi "
                    "encerrado sem repetir nada; o pedido no portal ficou como está — confira lá "
                    "antes de pedir de novo.")
    ctx["runs"].falhar(ctx["run_id"], str(ctx["company_id"]), _R.CODIGO_ESPERA_VENCIDA, mensagem,
                       retryable=False, lease_token=ctx.get("lease_token"))
    return _R.ESPERANDO


@registrar_workflow("bridge.portal.job")
async def bridge_portal(ctx: dict) -> str:
    """Orquestra um job de portal sob Work Run.

    O Portal Worker **continua sendo quem toca o portal** — ele tem
    Playwright, sessão cifrada e evidência. O Work Run coordena, registra e
    aplica idempotência ao redor.

    🔴 SPEC-129-A (D-129A-7): `needs_human` do portal vira `waiting_input` com relógio em
    backoff (5→10→20→40→60 min) e prazo de 24 h. 📊 Antes gravava `waiting_approval` SEM
    `approval_request` — uma espera que ninguém acorda — e o worker concluía por cima.
    """
    payload = ctx["payload"]
    job_id = payload.get("portal_job_id")
    if not job_id:
        return "Job de portal sem identificador."
    _R = _runs_mod()
    job_id = str(job_id)

    async def _acompanhar() -> Any:
        return await _conferir_o_portal(ctx, job_id, passo="acompanhar_portal")

    try:
        r = await executar_passo(ctx, step_key="acompanhar_portal", ordinal=1,
                                 nome="Acompanhar execução no portal",
                                 step_type="portal", fn=_acompanhar,
                                 capability_key="tenant.portal.execute", risk_level="high",
                                 efeito="idempotente", guardar=("business_state", "status"))
    except _EsperaVencida as exc:
        return _falhar_pela_espera(ctx, str(exc), "acompanhamento do job")
    if isinstance(r, _R.Esperando):
        return r
    status = (r or {}).get("status") or "desconhecido"
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

    🔴 SPEC-129-A — a espera é DURÁVEL, partida em duas etapas:
      `portal:<op>:criar`    efeito idempotente, guarda só o `portal_job_id`. O gateway roda
                             em `asyncio.to_thread`, SEMPRE em modo ENFILEIRAR, com a chave
                             `wr:<run>:<op>`: a retomada no meio reencontra o MESMO job.
                             Resultado COM `portal_job_id` = sucesso (mesmo vindo como
                             `needs_human` "enfileirado"); sem ele = recusa do gateway.
      `portal:<op>:aguardar` lê o job: não terminou → `runs.dormir` → `ESPERANDO`, e o
                             worker NÃO conclui. Terminou → traduz o estado e conclui.
    📊 Antes: um `sleep` bloqueante de até 150 s dentro do event loop — o heartbeat parava e a lease
    de 120 s vencia no meio da espera (SPEC-129-A §0, problema 4).
    """
    from app.services.portals import contracts as _C
    from app.services.portals.gateway import PortalExecutionGateway

    payload = ctx["payload"] or {}
    operation_key = str(payload.get("operation_key") or "").strip()
    if not operation_key:
        return "Pedido de portal sem operação de negócio."

    db = getattr(ctx["db"], "client", ctx["db"])
    _R = _runs_mod()
    run_id = str(ctx.get("run_id") or "") or None

    async def _criar() -> dict:
        req = _C.PortalExecutionRequest(
            company_id=str(ctx["company_id"]),
            operation_key=operation_key,
            business_input=dict(payload.get("business_input") or {}),
            # A linhagem vem do RUNTIME, não do payload. Se viesse do payload,
            # um chamador poderia atribuir o próprio trabalho a outro Work Run.
            work_run_id=run_id,
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
            # 🔴 SPEC-129-A: a chave de NEGÓCIO do chamador vence; sem ela, uma por run e
            # operação — é ela que faz a retomada reencontrar o job em vez de criar outro.
            idempotency_key=payload.get("idempotency_key") or f"wr:{run_id}:{operation_key}",
            effect_class_autorizada=payload.get("effect_class_autorizada"),
            # 🔴 SEMPRE enfileirar: quem espera é o Work Run (dormindo), nunca um processo.
            wait_mode=_C.ESPERA_ENFILEIRAR,
        )
        resultado = await asyncio.to_thread(PortalExecutionGateway(db).executar, req)
        ctx.setdefault("resultados", {})["portal"] = resultado.para_dict()
        if resultado.portal_job_id:
            return {"portal_job_id": str(resultado.portal_job_id)}
        # Sem job: o gateway RECUSOU (sem conexão, não suportado, não autorizado…).
        return {"business_state": resultado.business_state,
                "mensagem": resultado.message or resultado.motivo}

    criado = await executar_passo(
        ctx, step_key=f"portal:{operation_key}:criar", ordinal=1,
        nome=f"Pedir `{operation_key}` ao portal",
        step_type="portal", fn=_criar,
        capability_key="tenant.portal.execute", risk_level="high",
        efeito="idempotente", guardar=("portal_job_id", "business_state"))
    criado = criado if isinstance(criado, dict) else {}
    job_id = criado.get("portal_job_id")
    if not job_id:
        estado = criado.get("business_state") or _C.NEGOCIO_FALHOU
        return f"Operação `{operation_key}` no portal terminou como `{estado}`."

    async def _aguardar() -> Any:
        return await _conferir_o_portal(ctx, str(job_id),
                                        passo=f"portal:{operation_key}:aguardar")

    try:
        r = await executar_passo(
            ctx, step_key=f"portal:{operation_key}:aguardar", ordinal=2,
            nome=f"Aguardar o portal (`{operation_key}`)",
            step_type="portal", fn=_aguardar,
            capability_key="tenant.portal.execute", risk_level="high",
            efeito="idempotente", guardar=("business_state", "status"))
    except _EsperaVencida as exc:
        return _falhar_pela_espera(ctx, str(exc), f"`{operation_key}`")
    if isinstance(r, _R.Esperando):
        return r   # dormiu: o worker NÃO conclui; o despertador traz o run de volta

    estado = (r or {}).get("business_state")
    if not estado:
        # Não é para acontecer: `:aguardar` só termina com o estado em mãos. Concluir aqui
        # seria declarar pronto um pedido que ninguém conferiu.
        raise RuntimeError("a conferência do portal terminou sem estado de negócio")
    if estado == _C.NEGOCIO_TALVEZ_COMMITADO:
        # 🔴 Nunca vira retry. O Work Run precisa PARAR aqui e chamar gente:
        # pode existir um pedido pago no nome do segurado, e a única coisa
        # pior que não terminar é terminar duas vezes.
        ctx["runs"].evento(ctx["company_id"], ctx["run_id"],
                           "effect.uncertain",
                           "A operação pode ter acontecido no portal. "
                           "Reconcilie antes de qualquer nova tentativa.")
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


@registrar_workflow("system.espera_de_teste")
async def workflow_espera_de_teste(ctx: dict) -> str:
    """O canário da espera durável (SPEC-129-A G11) — prova, em PRODUÇÃO, que o Work OS dorme.

    `ping` (1 tentativa) → dorme `minutos` (padrão 10, de 1 a 60) → acorda sozinho → conclui.
    Reiniciar o `smith-worker` no meio NÃO pode duplicar nada: o run dormindo não tem dono,
    e o `ping` concluído não roda de novo. Não toca em nada do corretor.
    """
    payload = ctx.get("payload") or {}
    try:
        minutos = int(payload.get("minutos") or 10)
    except (TypeError, ValueError):
        minutos = 10
    minutos = max(1, min(60, minutos))
    _R = _runs_mod()
    referencia = "espera_de_teste"

    async def _ping() -> dict:
        return {"ok": True}

    await executar_passo(ctx, step_key="ping", ordinal=1, nome="Verificação do pipeline",
                         step_type="system", fn=_ping, efeito="idempotente", guardar=("ok",))

    async def _esperar() -> Any:
        espera = ctx.get("espera") if isinstance(ctx.get("espera"), dict) else {}
        if espera.get("tipo") == "relogio" and espera.get("ref") == referencia:
            prazo = _ler_ts(espera.get("prazo"))
            if prazo is not None and _agora() >= prazo:
                return {"acordou": int(espera.get("acordou") or 0)}
        return ctx["runs"].dormir(
            ctx["run_id"], lease_token=ctx.get("lease_token"), acordar_em_s=None,
            wait_for={"tipo": "relogio", "ref": referencia, "prazo_s": minutos * 60,
                      "passo": "esperar"},
            company_id=str(ctx["company_id"]))

    r = await executar_passo(ctx, step_key="esperar", ordinal=2, nome=f"Dormir {minutos} min",
                             step_type="system", fn=_esperar, efeito="idempotente",
                             guardar=("acordou",))
    if isinstance(r, _R.Esperando):
        return r
    return (f"Espera durável verificada: dormiu {minutos} min sem segurar processo e acordou "
            f"sozinho ({(r or {}).get('acordou')} conferência(s)).")
