# -*- coding: utf-8 -*-
"""SPEC-129-A F2 · G2 — A COBRANÇA NÃO REPETE (a ponte das rotinas, que ENVIA, ligada em produção).

O motor real: `SmithWorker` (laços reais), `WorkRunService`, `bridge.routine.execute` + `executar_passo`.
Dublê só na BORDA: o banco, o Redis, o relógio (`dubles_do_work_os`) e o MOTOR DE ROTINAS que envia
(`routine_engine._execute_routine` — é ele que fala com o segurado; aqui ele CONTA e pode MATAR o processo).

  G2.1 morto DEPOIS do passo `executar_rotina` e antes do `concluir` → `_execute_routine` ×1 (não repete)
  G2.2 morto NO MEIO do passo (os TRÊS ramos: motor, `config.workflow`, monitor) → +0 e `efeito_incerto`;
       o aviso legível e o `routine_runs` delegado fechado como `error`; o Reprocessar recusa (409)
  G2.3 `retry_scheduled` de 3 h (re-enfileirado pelo despertador) → `expired`, +0, aviso, `routine_runs` fechado
  G2.4 mensagem velha (> 2 h) que chega DIRETO ao handler → `expired` sem rodar, +0, aviso, `routine_runs` fechado
  G2.5 CONTROLE: o caminho feliz roda UMA vez, conclui e carimba o `routine_runs` como `ok`

🔴 Duas corretoras REAIS (SELECT só leitura) — a fixture `corretoras` do teste do fio. Sem banco: FALHA.

    cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/test_spec129a_a_cobranca_nao_repete.py -q
"""
from __future__ import annotations

import asyncio
import sys
import types
import uuid
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
for _p in (str(RAIZ), str(RAIZ / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from test_spec129a_o_fio_da_espera import corretoras, mundo  # noqa: E402,F401  (fixtures reais)

import dubles_do_work_os as D  # noqa: E402
from app.services.work import runs as R  # noqa: E402
from app.services.work import workflows as W  # noqa: E402
from app.workers import smith_worker as SW  # noqa: E402

WORKFLOW = "bridge.routine.execute"
DECLARADO = "teste129a.rotina_declarada"


# ═════════════════════════════════════════════════════════════════════════════
# A borda: o motor de rotinas (que ENVIA), o monitor de pesquisa e o workflow declarado
# ═════════════════════════════════════════════════════════════════════════════
class Envios:
    """Conta quantas vezes o trabalho QUE FALA COM O MUNDO rodou, por ramo."""

    def __init__(self):
        self.vezes = {"motor": 0, "declarado": 0, "monitor": 0}
        self.matar_no_meio: dict = {}       # ramo -> processo a matar DENTRO do envio

    def _talvez_morrer(self, ramo: str) -> None:
        proc = self.matar_no_meio.pop(ramo, None)
        if proc is not None:
            proc.morrer()
            raise D.MorteDoProcesso(f"{proc.nome} morreu NO MEIO do envio ({ramo})")

    async def execute_routine(self, _db, rotina, *, work_run_id=None):
        self.vezes["motor"] += 1
        self._talvez_morrer("motor")

    async def declarado(self, ctx):
        self.vezes["declarado"] += 1
        self._talvez_morrer("declarado")
        return "rotina declarada executada"

    async def verificar_monitor(self, ctx):
        self.vezes["monitor"] += 1
        self._talvez_morrer("monitor")
        return "monitor verificado"


@pytest.fixture
def envios(monkeypatch):
    e = Envios()
    motor = types.ModuleType("app.services.routine_engine")
    motor._execute_routine = e.execute_routine
    monkeypatch.setitem(sys.modules, "app.services.routine_engine", motor)
    pacote = sys.modules.get("app.services")
    if pacote is not None:
        monkeypatch.setattr(pacote, "routine_engine", motor, raising=False)

    pesquisa = types.ModuleType("app.services.research")
    pesquisa.__path__ = []
    monitor_mod = types.ModuleType("app.services.research.monitor_service")
    fluxos_mod = types.ModuleType("app.services.research.workflows")
    e.monitores: dict = {}

    class MonitorService:
        def __init__(self, _db):
            pass

        def por_rotina(self, routine_id):
            return e.monitores.get(routine_id)

    monitor_mod.MonitorService = MonitorService
    fluxos_mod.verificar_monitor = e.verificar_monitor
    pesquisa.monitor_service, pesquisa.workflows = monitor_mod, fluxos_mod
    for nome, mod in (("app.services.research", pesquisa),
                      ("app.services.research.monitor_service", monitor_mod),
                      ("app.services.research.workflows", fluxos_mod)):
        monkeypatch.setitem(sys.modules, nome, mod)

    cobranca = types.ModuleType("app.services.billing_collection")
    cobranca.is_billing_routine = lambda rotina: bool((rotina.get("config") or {}).get("cobranca"))
    monkeypatch.setitem(sys.modules, "app.services.billing_collection", cobranca)

    monkeypatch.setitem(W._REGISTRO, DECLARADO, e.declarado)
    return e


# ═════════════════════════════════════════════════════════════════════════════
# O mundo da cobrança
# ═════════════════════════════════════════════════════════════════════════════
def _rotina(mundo, cid: str, *, ramo: str = "motor", envios: Envios | None = None) -> str:
    rid = str(uuid.uuid4())
    config = {"cobranca": True}
    if ramo == "declarado":
        config["workflow"] = DECLARADO
    mundo.banco.semear("routines", {"id": rid, "company_id": cid, "name": "Cobrança de outubro",
                                    "config": config, "is_active": True})
    if ramo == "monitor" and envios is not None:
        envios.monitores[rid] = {"id": str(uuid.uuid4()), "is_active": True}
    return rid


def _criar_run(mundo, cid: str, rid: str) -> str:
    api = R.WorkRunService(mundo.processo("api").db)
    linha = api.criar(company_id=cid, source_type="routine", source_id=rid,
                      outcome_type="routine.execution", outcome_title="Cobrança de outubro",
                      workflow_key=WORKFLOW, idempotency_key=f"routine:{rid}:{uuid.uuid4().hex[:8]}",
                      input_payload={"routine_id": rid}, priority=40)
    run_id = str(linha["run_id"])
    # o bilhete que `routine_engine._criar_work_run_para_rotina` abre ao delegar
    mundo.banco.semear("routine_runs", {"routine_id": rid, "company_id": cid, "status": "delegated",
                                        "work_run_id": run_id, "output_preview": "executando como Work Run"})
    return run_id


def _eventos(mundo, run_id, tipo):
    return [e for e in mundo.banco.linhas("work_events")
            if e.get("work_run_id") == run_id and e.get("event_type") == tipo]


def _bilhete(mundo, run_id) -> dict:
    return next(r for r in mundo.banco.linhas("routine_runs") if r.get("work_run_id") == run_id)


def _passo(mundo, run_id, chave="executar_rotina"):
    return next((s for s in mundo.banco.linhas("work_steps")
                 if s.get("work_run_id") == run_id and s.get("step_key") == chave), None)


async def _ate_terminar(mundo, worker, proc, run_id, *, passos=12, passo_s=60) -> list:
    mortes = []
    for _ in range(passos):
        if mundo.banco.run(run_id).get("status") in D.ESTADOS_TERMINAIS_DO_RUN:
            break
        mundo.relogio.avancar(passo_s)
        mortes += await D.ciclo(worker, proc)
    return mortes


# ═════════════════════════════════════════════════════════════════════════════
# G2.5 — CONTROLE: o caminho feliz
# ═════════════════════════════════════════════════════════════════════════════
def test_g2_5_controle_o_caminho_feliz_roda_uma_vez_e_carimba(mundo, corretoras, envios):
    X, _Y = corretoras
    rid = _rotina(mundo, X)
    run_id = _criar_run(mundo, X, rid)

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)
        return await D.ciclo(wa, a)

    mortes = asyncio.run(cenario())
    assert not mortes
    run = mundo.banco.run(run_id)
    assert run["status"] == "completed", run
    assert envios.vezes["motor"] == 1
    assert len(_eventos(mundo, run_id, "run.succeeded")) == 1
    assert _bilhete(mundo, run_id)["status"] == "ok", "o bilhete delegado não foi carimbado na chegada"
    assert (_passo(mundo, run_id) or {}).get("status") == "succeeded"


# ═════════════════════════════════════════════════════════════════════════════
# G2.1 — morto DEPOIS do passo e antes do `concluir`
# ═════════════════════════════════════════════════════════════════════════════
def test_g2_1_morto_depois_do_passo_nao_repete_a_cobranca(mundo, corretoras, envios):
    X, _Y = corretoras
    rid = _rotina(mundo, X)
    run_id = _criar_run(mundo, X, rid)

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)

        def morre_quando_o_passo_conclui(escrita):
            linha = (escrita.depois or [{}])[0]
            if (escrita.dono == a.nome and not a.morto and linha.get("step_key") == "executar_rotina"
                    and (escrita.payload or {}).get("status") == "succeeded"):
                a.morrer()
                raise D.MorteDoProcesso("worker-A morreu depois do passo, antes do concluir")

        mundo.banco.ao_gravar("work_steps", "update", morre_quando_o_passo_conclui)
        mortes = await D.ciclo(wa, a)
        assert a.morto and mundo.banco.run(run_id)["status"] == "running", "A devia morrer com o run no ar"
        assert (_passo(mundo, run_id) or {}).get("status") == "succeeded"
        b = mundo.processo("worker-B")
        wb = await D.ligar_worker(b, SW)
        mortes += await _ate_terminar(mundo, wb, b, run_id)
        return mortes

    asyncio.run(cenario())
    run = mundo.banco.run(run_id)
    assert run["status"] == "completed", f"B devia retomar e concluir: {run['status']}"
    assert envios.vezes["motor"] == 1, (f"🔴 a cobrança rodou {envios.vezes['motor']}× — a retomada repetiu "
                                        "um passo que já tinha terminado")
    assert len(_eventos(mundo, run_id, "run.succeeded")) == 1
    assert _eventos(mundo, run_id, "step.reused"), "a retomada devia registrar que NÃO repetiu"
    assert _bilhete(mundo, run_id)["status"] == "ok"


# ═════════════════════════════════════════════════════════════════════════════
# G2.2 — morto NO MEIO do passo, nos TRÊS ramos da ponte
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("ramo", ["motor", "declarado", "monitor"])
def test_g2_2_morto_no_meio_vira_efeito_incerto_nos_tres_ramos(mundo, corretoras, envios, ramo):
    X, _Y = corretoras
    rid = _rotina(mundo, X, ramo=ramo, envios=envios)
    run_id = _criar_run(mundo, X, rid)

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)
        envios.matar_no_meio[ramo] = a
        await D.ciclo(wa, a)
        assert a.morto, "o envio devia ter matado A no meio"
        b = mundo.processo("worker-B")
        wb = await D.ligar_worker(b, SW)
        await _ate_terminar(mundo, wb, b, run_id)

    asyncio.run(cenario())
    run = mundo.banco.run(run_id)
    assert sum(envios.vezes.values()) == 1 and envios.vezes[ramo] == 1, (
        f"🔴 o ramo `{ramo}` rodou de novo depois de morrer no meio: {envios.vezes}")
    assert run["status"] == "failed" and run.get("error_code") == R.CODIGO_EFEITO_INCERTO, \
        f"esperado failed/efeito_incerto, veio {run['status']}/{run.get('error_code')}"
    assert not _eventos(mundo, run_id, "run.succeeded")
    aviso = _eventos(mundo, run_id, "routine.nao_concluida")
    assert len(aviso) == 1 and aviso[0]["severity"] == "warning", aviso
    assert "Cobrança de outubro" in aviso[0]["message_human"] and "cobrança" in aviso[0]["message_human"].lower()
    bilhete = _bilhete(mundo, run_id)
    assert bilhete["status"] == "error" and bilhete.get("finished_at"), bilhete
    passo = _passo(mundo, run_id) or {}
    assert passo.get("status") == "failed" and (passo.get("output_summary") or {}).get("efeito_incerto")

    api = R.WorkRunService(mundo.processo("api").db)
    r = api.reprocessar(run_id, X, workflows={WORKFLOW: W.resolver_workflow(WORKFLOW)})
    assert r.get("http") == 409 and r.get("codigo") == R.CODIGO_EFEITO_INCERTO, r


# ═════════════════════════════════════════════════════════════════════════════
# G2.3 — `retry_scheduled` de 3 h, re-enfileirado pelo despertador → expired
# ═════════════════════════════════════════════════════════════════════════════
def test_g2_3_retry_de_tres_horas_expira_sem_cobrar(mundo, corretoras, envios):
    X, _Y = corretoras
    rid = _rotina(mundo, X)
    run_id = _criar_run(mundo, X, rid)
    tres_horas = (mundo.relogio.agora() - D.timedelta(hours=3)).isoformat()
    # o estado que `falhar(retryable=True)` deixa: retry_scheduled + wake_at vencido, sem lease
    for o in mundo.banco.linhas("work_queue_outbox"):
        if o.get("work_run_id") == run_id:
            o["status"] = "published"
    run = mundo.banco.run(run_id)
    run.update({"status": "retry_scheduled", "requested_at": tres_horas, "queued_at": tres_horas,
                "wake_at": (mundo.relogio.agora() - D.timedelta(minutes=1)).isoformat(),
                "error_code": "provider_indisponivel"})

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)
        await D.ciclo(wa, a)

    asyncio.run(cenario())
    run = mundo.banco.run(run_id)
    assert run["status"] == "expired" and run.get("error_code") == R.CODIGO_EXPIRADO_PELA_IDADE, run
    assert envios.vezes["motor"] == 0, "🔴 a cobrança de 3 h atrás RODOU"
    aviso = _eventos(mundo, run_id, "routine.nao_concluida")
    assert len(aviso) == 1 and aviso[0]["severity"] == "warning" and "não rodou" in aviso[0]["message_human"]
    assert _bilhete(mundo, run_id)["status"] == "error", "a expirada sumiu em silêncio: bilhete aberto"


# ═════════════════════════════════════════════════════════════════════════════
# G2.4 — a mensagem velha que chega DIRETO ao handler
# ═════════════════════════════════════════════════════════════════════════════
def test_g2_4_mensagem_velha_no_handler_expira_sem_cobrar(mundo, corretoras, envios):
    X, _Y = corretoras
    rid = _rotina(mundo, X)
    run_id = _criar_run(mundo, X, rid)
    # pedido de 3 h atrás, mas recém-enfileirado (o re-despacho e o despertador não o veem)
    mundo.banco.run(run_id)["requested_at"] = (mundo.relogio.agora() - D.timedelta(hours=3)).isoformat()

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)
        return await D.ciclo(wa, a)

    assert not asyncio.run(cenario())
    run = mundo.banco.run(run_id)
    assert run["status"] == "expired" and run.get("error_code") == R.CODIGO_EXPIRADO_PELA_IDADE, run
    assert envios.vezes["motor"] == 0, "🔴 a cobrança velha RODOU ao chegar no handler"
    assert not _eventos(mundo, run_id, "run.succeeded"), "o worker concluiu por cima da expiração"
    assert _eventos(mundo, run_id, "routine.nao_concluida")
    assert _bilhete(mundo, run_id)["status"] == "error"
    assert _passo(mundo, run_id) is None, "nenhuma etapa devia ter começado"


# ═════════════════════════════════════════════════════════════════════════════
# O registro diz como desistir (D-129A-5): o despertador lê isto
# ═════════════════════════════════════════════════════════════════════════════
def test_a_ponte_declara_idade_e_desistencia_no_registro():
    h = W.resolver_workflow(WORKFLOW)
    assert getattr(h, "idade_maxima_s", None) == 2 * 3600
    assert callable(getattr(h, "ao_desistir", None))
    assert W.resolver_workflow("system.espera_de_teste") is not None, "o canário do G11 não está registrado"


# ═════════════════════════════════════════════════════════════════════════════
# G7 (a parte da F2) — o que uma etapa GUARDA: só ids e estados, nunca PII
# ═════════════════════════════════════════════════════════════════════════════
def test_guardar_com_cpf_nao_chega_ao_banco(mundo, corretoras):
    """O motor real (`executar_passo`) sobre o banco-dublê com as travas: só o declarado e guardável."""
    X, _Y = corretoras
    rid = _rotina(mundo, X)
    run_id = _criar_run(mundo, X, rid)
    job = str(uuid.uuid4())
    db = mundo.processo("worker-A").db
    ctx = {"db": db, "runs": R.WorkRunService(db), "company_id": X, "run_id": run_id,
           "cancelado": lambda: False}

    async def fn():
        return {"portal_job_id": job, "business_state": "needs_human", "cpf": "123.456.789-09",
                "cpf_cru": "12345678909", "cpf_int": 12345678909, "telefone": "(47) 99999-1234",
                "texto": "o segurado Fulano pediu", "aninhado": {"portal_job_id": job},
                "nao_declarada": "ok"}

    devolvido = asyncio.run(W.executar_passo(
        ctx, step_key="guardar", ordinal=1, nome="Guardar", step_type="system", fn=fn,
        efeito="idempotente",
        guardar=("portal_job_id", "business_state", "cpf", "cpf_cru", "cpf_int", "telefone",
                 "texto", "aninhado")))
    assert devolvido["cpf"] == "123.456.789-09", "quem chama recebe o resultado inteiro na 1ª passagem"
    salvo = (_passo(mundo, run_id, "guardar") or {}).get("output_summary")
    assert salvo == {"portal_job_id": job, "business_state": "needs_human"}, (
        f"🔴 a etapa guardou o que não devia (PII, texto livre ou objeto): {salvo}")
    assert not any(c.isdigit() for c in str({k: v for k, v in salvo.items() if k != "portal_job_id"}))

    # e a RETOMADA devolve exatamente o guardado, sem chamar `fn` de novo
    chamadas = []

    async def fn_de_novo():
        chamadas.append(1)
        return {}

    retomado = asyncio.run(W.executar_passo(
        ctx, step_key="guardar", ordinal=1, nome="Guardar", step_type="system", fn=fn_de_novo,
        efeito="idempotente", guardar=("portal_job_id", "business_state", "cpf")))
    assert retomado == {"portal_job_id": job, "business_state": "needs_human"} and not chamadas


# ═════════════════════════════════════════════════════════════════════════════
# CONSERTO ÚNICO (juiz B1 ‖ red team Q1/Q2) — a etapa EXTERNA é fail-CLOSED
# ═════════════════════════════════════════════════════════════════════════════
class _FalhaTransitoria(Exception):
    """O que o httpx/PostgREST levanta num soluço de rede — NÃO é 23505."""


def _falhar_proximas(proc, tabela: str, op: str, quantas: int = 1) -> dict:
    """Na visão do banco DESTE processo, as próximas `quantas` `op` em `tabela` levantam ANTES do banco."""
    original = proc.db.table
    estado = {"n": quantas}

    def table(nome):
        c = original(nome)
        if nome != tabela:
            return c
        exe = c.execute

        def execute():
            if c.op == op and estado["n"] > 0:
                estado["n"] -= 1
                raise _FalhaTransitoria(f"soluço de rede em {op} {tabela}")
            return exe()
        c.execute = execute
        return c
    proc.db.table = table
    return estado


def test_conserto_q1_insert_da_etapa_falha_a_cobranca_nao_roda_sem_registro(mundo, corretoras, envios):
    """📊 red team A1: o INSERT de `work_steps` falhava (não-23505), `fn` rodava com `step_id=None`,
    A morria ao carimbar o bilhete e B rodava DE NOVO → 2 envios. Agora: não roda sem a etapa;
    volta pelo despertador (`etapa_nao_verificada`) e roda UMA vez."""
    X, _Y = corretoras
    rid = _rotina(mundo, X)
    run_id = _criar_run(mundo, X, rid)

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)
        _falhar_proximas(a, "work_steps", "insert")

        def morre_ao_carimbar(escrita):   # A morre DEPOIS do envio, antes do concluir
            if escrita.dono == a.nome and not a.morto:
                a.morrer()
                raise D.MorteDoProcesso("A morreu depois do envio")
        mundo.banco.ao_gravar("routine_runs", "update", morre_ao_carimbar)
        await D.ciclo(wa, a)
        assert envios.vezes["motor"] == 0, "🔴 a cobrança rodou SEM a etapa registrada"
        run = mundo.banco.run(run_id)
        assert (run["status"], run.get("error_code")) == ("retry_scheduled", R.CODIGO_ETAPA_NAO_VERIFICADA), run
        assert run.get("wake_at"), "a nova tentativa precisa do despertador (wake_at)"
        assert _bilhete(mundo, run_id)["status"] == "delegated", "o bilhete não pode virar `error`: nada rodou"
        await _ate_terminar(mundo, wa, a, run_id)
        if a.morto:
            b = mundo.processo("worker-B")
            wb = await D.ligar_worker(b, SW)
            await _ate_terminar(mundo, wb, b, run_id)

    asyncio.run(cenario())
    run = mundo.banco.run(run_id)
    assert envios.vezes["motor"] == 1, f"🔴 a cobrança saiu {envios.vezes['motor']}×"
    assert run["status"] == "completed", run


def test_conserto_q2_leitura_da_etapa_falha_na_retomada_nao_repete(mundo, corretoras, envios):
    """📊 juiz B1(a) / red team A2: a etapa JÁ tinha terminado, a releitura falhava e `fn` rodava de
    novo. CONTROLE: o G2.1 (mesmo cenário sem o soluço) — 1 envio."""
    X, _Y = corretoras
    rid = _rotina(mundo, X)
    run_id = _criar_run(mundo, X, rid)

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)

        def morre_quando_o_passo_conclui(escrita):
            linha = (escrita.depois or [{}])[0]
            if (escrita.dono == a.nome and not a.morto and linha.get("step_key") == "executar_rotina"
                    and (escrita.payload or {}).get("status") == "succeeded"):
                a.morrer()
                raise D.MorteDoProcesso("A morreu depois do passo, antes do concluir")
        mundo.banco.ao_gravar("work_steps", "update", morre_quando_o_passo_conclui)
        await D.ciclo(wa, a)
        assert (_passo(mundo, run_id) or {}).get("status") == "succeeded"
        b = mundo.processo("worker-B")
        wb = await D.ligar_worker(b, SW)
        # 1ª leitura: a da idade, no handler (falhar ali é inofensivo); 2ª: a releitura da etapa
        _falhar_proximas(b, "work_steps", "select", quantas=2)
        await _ate_terminar(mundo, wb, b, run_id)

    asyncio.run(cenario())
    run = mundo.banco.run(run_id)
    assert envios.vezes["motor"] == 1, f"🔴 a cobrança saiu {envios.vezes['motor']}× (releitura falhou)"
    assert run["status"] == "completed", run
    assert _eventos(mundo, run_id, "step.reused"), "a volta devia REUSAR a etapa concluída"


def test_conserto_a3_resposta_do_insert_perdida_roda_uma_vez_sem_incerto_falso(mundo, corretoras, envios):
    """📊 red team A3 (P1): o INSERT GRAVOU e só a resposta se perdeu → a releitura acha a etapa
    `running` com a assinatura DESTA tentativa → é a nossa: roda UMA vez (antes: `efeito_incerto`
    falso, 0 envios e o corretor lendo "reconcilie")."""
    X, _Y = corretoras
    rid = _rotina(mundo, X)
    run_id = _criar_run(mundo, X, rid)

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)
        feito = {"n": 0}

        def resposta_perdida(escrita):
            if escrita.dono == a.nome and feito["n"] == 0 and \
                    (escrita.depois or [{}])[0].get("step_key") == "executar_rotina":
                feito["n"] = 1
                raise _FalhaTransitoria("timeout lendo a resposta do INSERT (a linha GRAVOU)")
        mundo.banco.ao_gravar("work_steps", "insert", resposta_perdida)
        await _ate_terminar(mundo, wa, a, run_id)

    asyncio.run(cenario())
    run = mundo.banco.run(run_id)
    assert envios.vezes["motor"] == 1 and run["status"] == "completed", (envios.vezes, run["status"],
                                                                          run.get("error_code"))


def _semear_etapa(mundo, cid, run_id, status, **extra):
    mundo.banco.semear("work_steps", {
        "id": str(uuid.uuid4()), "work_run_id": run_id, "company_id": cid, "step_key": "externa",
        "ordinal": 1, "name": "Externa", "step_type": "routine", "status": status,
        "risk_level": "low", "idempotency_key": f"{cid}:{run_id}:externa", "output_summary": {},
        **extra})


def _ctx(mundo, cid, run_id):
    db = mundo.processo("worker-A").db
    return {"db": db, "runs": R.WorkRunService(db), "company_id": cid, "run_id": run_id,
            "cancelado": lambda: False}


@pytest.mark.parametrize("status_lido", ["waiting_input", "failed"])
def test_conserto_b1b_etapa_reencontrada_volta_a_running_antes_de_rodar(mundo, corretoras, status_lido):
    """📊 juiz B1(b) casos D/E: uma etapa EXTERNA reencontrada `waiting_input` ou `failed` SEM a marca
    (Reprocessar) rodava `fn` sem regravar `running`; morrer no meio deixava o status velho e a
    retomada seguinte rodava DE NOVO. Agora: morrer no meio → a retomada levanta `EfeitoIncerto`."""
    X, _Y = corretoras
    rid = _rotina(mundo, X)
    run_id = _criar_run(mundo, X, rid)
    _semear_etapa(mundo, X, run_id, status_lido)
    ctx = _ctx(mundo, X, run_id)
    chamadas = {"n": 0}
    visto = []

    async def envia_e_morre():
        chamadas["n"] += 1
        visto.append((_passo(mundo, run_id, "externa") or {}).get("status"))
        raise D.MorteDoProcesso("morreu no meio do envio")

    with pytest.raises(D.MorteDoProcesso):
        asyncio.run(W.executar_passo(ctx, step_key="externa", ordinal=1, nome="Externa",
                                     step_type="routine", fn=envia_e_morre, efeito="externo"))
    assert visto == ["running"], f"🔴 a etapa externa rodou marcada {visto}, não `running`"
    # a retomada é DEPOIS (o relógio do dublê é congelado; a assinatura da tentativa é o instante)
    mundo.relogio.avancar(30)
    with pytest.raises(R.EfeitoIncerto):
        asyncio.run(W.executar_passo(ctx, step_key="externa", ordinal=1, nome="Externa",
                                     step_type="routine", fn=envia_e_morre, efeito="externo"))
    assert chamadas["n"] == 1, f"🔴 o efeito externo rodou {chamadas['n']}×"
    passo = _passo(mundo, run_id, "externa") or {}
    assert passo.get("status") == "failed" and (passo.get("output_summary") or {}).get("efeito_incerto")


def test_conserto_b1b_CONTROLE_etapa_running_vira_incerto_sem_rodar(mundo, corretoras):
    """O controle C do juiz: `running` de um processo morto → `EfeitoIncerto`, 0 chamadas
    (a assinatura não é a desta tentativa)."""
    X, _Y = corretoras
    rid = _rotina(mundo, X)
    run_id = _criar_run(mundo, X, rid)
    _semear_etapa(mundo, X, run_id, "running", started_at="2026-01-01T00:00:00+00:00")
    chamadas = []

    async def fn():
        chamadas.append(1)
        return "x"

    with pytest.raises(R.EfeitoIncerto):
        asyncio.run(W.executar_passo(_ctx(mundo, X, run_id), step_key="externa", ordinal=1,
                                     nome="Externa", step_type="routine", fn=fn, efeito="externo"))
    assert not chamadas
