# -*- coding: utf-8 -*-
"""SPEC-129-A F0 — O TESTE DO FIO da espera durável (nasce VERMELHO; fica VERDE com F1+F2).

O fio (SPEC §2), elo a elo, com o MOTOR REAL em cada elo — dublê só na borda (CLAUDE.md §9.4):

  criar     WorkRunService.criar → RPC work_run_create → work_runs(queued) + outbox(pending)
  fila      _laco_dispatcher → OutboxDispatcher.despachar_lote → XADD → _laco_consumo → _agendar
  lease     _executar_run → runs.adquirir_lease (CAS, só smith)
  rodar     _processar → portal_operation → executar_passo("portal:<op>:criar", efeito="idempotente",
            guardar=("portal_job_id",)) → PortalExecutionGateway (modo `on`, ENFILEIRAR) → portal_jobs
            → executar_passo("portal:<op>:aguardar") → job não terminou → runs.dormir → ESPERANDO
  acordar   _laco_orfaos → runs.despertar_vencidos → CAS → queued + outbox `run.woken` (e o re-despacho)
  retomar   :criar `succeeded` devolve o job guardado (fn NÃO roda) → :aguardar lê `done` → concluir

  Motor real: SmithWorker (o `iniciar()` real, os laços reais), OutboxDispatcher, WorkQueue,
  WorkRunService, WorkApprovalService, WorkEffectService, portal_operation + executar_passo,
  PortalExecutionGateway + resolver + journeys. Borda (`dubles_do_work_os.py`): banco (PostgREST com as
  travas do banco real e da `_02`), Redis Streams, portal-worker, relógio.

  C1 dorme e acorda      job → waiting_input → relógio +10 min em passos de 60 s → `done` no 3º despertar
                         → completed · run.succeeded ×1 · portal_jobs ×1 · :criar 1 tentativa · acordou = 3
  C2 reinício dormindo   A morre em waiting_input → B (instância nova) acorda e conclui · contagens de C1
  C3 reinício no meio    A morre DEPOIS do insert do job e ANTES do :criar `succeeded` → B retoma → MESMO
                         job, SEM espera bloqueante (o ramo "já existe" respeita enqueue)
  C4 cancelar dormindo   → cancelled na hora; o despertar seguinte não o reabre
  C5 mensagem perdida    o Redis descarta o `run.woken` → re-despacho > 10 min → conclui
  C6 duas corretoras     A dormindo, B acordando → nenhuma escrita cruza company_id · uma sombra
                         `running` sem lease → intocada
  C7 controle            C1 com o código de 04/10 (git `5ab37e7`) → falha pelo motivo esperado (§9.3):
                         o worker CONCLUI POR CIMA DA ESPERA (problema 2 da SPEC §0)

🔴 Dois `company_id` REAIS, por SELECT só leitura (CLAUDE.md §13.9 — nenhum nome de corretora aqui).
🔴 SEM BANCO O TESTE FALHA, com a causa. Pular não conta como verde (SPEC-129-A §7.1, G1).

    cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec129a_o_fio_da_espera.py -q
"""
from __future__ import annotations

import asyncio
import copy
import inspect
import os
import subprocess
import sys
import time
import types
import uuid
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
REPO = RAIZ.parent
for _p in (str(RAIZ), str(RAIZ / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# `app/services/__init__.py` arrasta langchain (minutos de import). O motor do Work OS não precisa
# dele: os pacotes-pai entram como namespace SÓ se ainda não foram importados (mesmo padrão dos
# testes da 073/074/075). Os MÓDULOS do motor são os reais, do disco.
for _n in ("app", "app.services"):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [str(RAIZ / _n.replace(".", "/"))]
        sys.modules[_n] = _m

import dubles_do_work_os as D  # noqa: E402
from app.services.observability import sli as SLI  # noqa: E402
from app.services.portals import contracts as C  # noqa: E402
from app.services.portals import gateway as G  # noqa: E402
from app.services.work import approvals as AP  # noqa: E402,F401
from app.services.work import effects as EF  # noqa: E402,F401
from app.services.work import queue as Q  # noqa: E402,F401
from app.services.work import runs as R  # noqa: E402
from app.services.work import workflows as W  # noqa: E402
from app.workers import smith_worker as SW  # noqa: E402

#: o código de 04/10 — a base da SPEC-129-A (o controle C7 roda o C1 contra ELE)
BASE_DE_04_10 = "5ab37e7"
OP = "billing.overdue.list"          # journey de LEITURA (hdi_corretor.cobranca_sweep): exige conta
SEGURADORA = "hdi"
PORTAL = "hdi_corretor"
PASSO_CRIAR = f"portal:{OP}:criar"
PASSO_AGUARDAR = f"portal:{OP}:aguardar"


# ═════════════════════════════════════════════════════════════════════════════
# O banco REAL — só leitura: duas corretoras e o retrato das colunas
# ═════════════════════════════════════════════════════════════════════════════
def _dsn() -> str | None:
    dsn = os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        try:
            from dotenv import load_dotenv

            load_dotenv(RAIZ / ".env")
        except Exception:  # noqa: BLE001
            pass
        dsn = os.environ.get("SUPABASE_DB_URL")
    return dsn


@pytest.fixture(scope="module")
def corretoras() -> tuple[str, str]:
    """Dois `company_id` reais + a conferência de que o retrato do dublê não envelheceu.

    🔴 Sem banco: FALHA (não pula). O fio sem duas corretoras reais não prova o isolamento (G1, G9)."""
    dsn = _dsn()
    if not dsn:
        pytest.fail("SEM BANCO: SUPABASE_DB_URL ausente. O fio da SPEC-129-A precisa de duas corretoras "
                    "REAIS (SELECT só leitura). Pular não conta como verde (SPEC §7.1, G1).")
    try:
        import psycopg
    except ImportError:
        pytest.fail("SEM BANCO: psycopg (v3) não instalado — o fio não pode ler as duas corretoras reais.")
    try:
        with psycopg.connect(dsn, prepare_threshold=None, connect_timeout=20) as c, c.cursor() as cur:
            cur.execute("begin; set transaction read only")   # 🔴 nunca SET de sessão pelo pooler
            cur.execute("select id from companies order by id limit 2")
            empresas = [str(r[0]) for r in cur.fetchall()]
            cur.execute("select table_name, column_name from information_schema.columns "
                        "where table_schema='public' and table_name = any(%s)",
                        (sorted(t for t in D.ESQUEMA if t != "companies"),))
            vivas: dict[str, set] = {}
            for t, col in cur.fetchall():
                vivas.setdefault(t, set()).add(col)
            cur.execute("rollback")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"SEM BANCO: não consegui ler o banco real ({type(exc).__name__}). "
                    "Pular não conta como verde (SPEC §7.1, G1).")
    assert len(empresas) == 2 and empresas[0] != empresas[1], \
        f"o fio precisa de DUAS corretoras reais (achei {len(empresas)})"
    envelheceu = {}
    for t, cols in vivas.items():
        retrato = set(D.ESQUEMA[t]) - D.COLUNAS_DA_02.get(t, set())
        diferenca = (cols - D.COLUNAS_DA_02.get(t, set())) ^ retrato
        if diferenca:
            envelheceu[t] = sorted(diferenca)
    assert not envelheceu, (f"o retrato do banco no dublê ENVELHECEU (dubles_do_work_os.ESQUEMA): "
                            f"{envelheceu} — atualize o retrato antes de confiar no fio")
    return empresas[0], empresas[1]


# ═════════════════════════════════════════════════════════════════════════════
# O contrato fixo da SPEC-129-A §6 (F1 entrega em runs.py; F2 em workflows.py)
# ═════════════════════════════════════════════════════════════════════════════
def _faltas_do_contrato() -> list[str]:
    faltas = []
    for nome in ("Esperando", "ESPERANDO", "EfeitoIncerto"):
        if not hasattr(R, nome):
            faltas.append(f"runs.{nome} (F1)")
    if hasattr(R, "Esperando") and hasattr(R, "ESPERANDO") and not isinstance(R.ESPERANDO, R.Esperando):
        faltas.append("runs.ESPERANDO não é instância de runs.Esperando (F1)")
    if hasattr(R, "EfeitoIncerto") and not (isinstance(R.EfeitoIncerto, type)
                                           and issubclass(R.EfeitoIncerto, Exception)):
        faltas.append("runs.EfeitoIncerto não é Exception (F1)")
    for metodo in ("dormir", "despertar_vencidos", "redespachar_parados", "reprocessar",
                   "despertar_por_aprovacao"):
        if not callable(getattr(R.WorkRunService, metodo, None)):
            faltas.append(f"WorkRunService.{metodo} (F1)")
    if callable(getattr(R.WorkRunService, "dormir", None)):
        params = inspect.signature(R.WorkRunService.dormir).parameters
        for p in ("lease_token", "acordar_em_s", "wait_for"):
            if p not in params:
                faltas.append(f"WorkRunService.dormir(…, {p}=…) (F1)")
    params = inspect.signature(W.executar_passo).parameters
    for p in ("efeito", "guardar"):
        if p not in params:
            faltas.append(f"workflows.executar_passo(…, {p}=…) (F2)")
    return faltas


def _exigir_contrato() -> None:
    """Dentro do TESTE (não numa fixture): sem o contrato, o cenário FALHA — não vira erro de setup."""
    faltas = _faltas_do_contrato()
    if faltas:
        pytest.fail("CONTRATO AUSENTE (SPEC-129-A §6) — o fio não tem por onde passar: " + " · ".join(faltas))


# ═════════════════════════════════════════════════════════════════════════════
# O mundo de cada cenário
# ═════════════════════════════════════════════════════════════════════════════
@pytest.fixture
def mundo(corretoras, monkeypatch):
    X, Y = corretoras
    m = D.Mundo(empresas=(X, Y))
    for cid in (X, Y):   # a conexão da corretora no portal (um por corretora — §14.4 da SPEC-075)
        m.banco.semear("portal_accounts", {"company_id": cid, "portal_key": PORTAL,
                                           "account_label": "principal", "health": "ok"})
    monkeypatch.setenv("PORTAL_EXECUTION_GATEWAY_MODE", C.MODO_ON)
    # 🔴 o teto de uma espera BLOQUEANTE fica em 3 s: se algum caminho ainda bloquear, o teste mede
    #    (G6) em vez de pendurar 150 s
    monkeypatch.setenv("PORTAL_GATEWAY_WAIT_S", "3")
    monkeypatch.setattr(G, "ESPERA_MAXIMA_S", 3)
    monkeypatch.setattr(SLI, "_cliente", lambda: None)   # a métrica é borda: nunca o banco real
    m.relogio.instalar()
    try:
        yield m
    finally:
        m.relogio.desinstalar()


def _criar(mundo: D.Mundo, company_id: str, *, rotulo: str = "fio") -> str:
    """Pelo caminho do produto: `WorkRunService.criar` → RPC `work_run_create`."""
    api = R.WorkRunService(mundo.processo("api").db)
    linha = api.criar(
        company_id=company_id, source_type="system", outcome_type="portal.operation",
        outcome_title=f"Teste do fio da espera ({rotulo})", workflow_key="portal.operation",
        idempotency_key=f"spec129a:{rotulo}:{uuid.uuid4().hex[:10]}",
        input_payload={"operation_key": OP, "insurer_key": SEGURADORA,
                       "business_input": {"competencia": "2026-10"}})
    return str(linha["run_id"])


# -- leituras do TESTE sobre o banco (o que se afirma é o estado, não o código) ---------------------
def _eventos(mundo, run_id, tipo):
    return [e for e in mundo.banco.linhas("work_events")
            if e.get("work_run_id") == run_id and e.get("event_type") == tipo]


def _outbox(mundo, run_id, tipo=None):
    return [o for o in mundo.banco.linhas("work_queue_outbox")
            if o.get("work_run_id") == run_id and (tipo is None or o.get("event_kind") == tipo)]


def _jobs(mundo, run_id):
    run = mundo.banco.run(run_id)
    saida = []
    for j in mundo.banco.linhas("portal_jobs"):
        linhagem = (((j.get("evidence") or {}).get("gateway") or {}).get("linhagem") or {})
        if j.get("company_id") == run.get("company_id") and run_id in (j.get("work_run_id"),
                                                                        linhagem.get("work_run_id")):
            saida.append(j)
    return saida


def _passo(mundo, run_id, chave):
    return next((s for s in mundo.banco.linhas("work_steps")
                 if s.get("work_run_id") == run_id and s.get("step_key") == chave), None)


def _tentativas(mundo, run_id, chave):
    passo = _passo(mundo, run_id, chave)
    if not passo:
        return 0
    return len([a for a in mundo.banco.linhas("work_attempts") if a.get("work_step_id") == passo["id"]])


class Observacao:
    """A linha do tempo de um run, tirada do banco depois de cada ciclo."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.estados: list[tuple[float, str]] = []
        self.concluiu_com_job_vivo = False
        self.concluiu_em: float | None = None
        self.mortes: list = []

    def anotar(self, mundo: D.Mundo) -> None:
        run = mundo.banco.run(self.run_id)
        st = run.get("status")
        if not self.estados or self.estados[-1][1] != st:
            self.estados.append((mundo.relogio.segundos(), st))
        if st == "completed" and self.concluiu_em is None:
            self.concluiu_em = mundo.relogio.segundos()
            if any(j.get("status") != "done" for j in _jobs(mundo, self.run_id)):
                self.concluiu_com_job_vivo = True

    def passou_por(self, status: str) -> bool:
        return any(s == status for _t, s in self.estados)


def _terminal(mundo, run_id) -> bool:
    return mundo.banco.run(run_id).get("status") in D.ESTADOS_TERMINAIS_DO_RUN


async def _girar(mundo, worker, processo, obs: list[Observacao], *, passos: int, passo_s: float,
                 politica=None, ao_fim_do_ciclo=None) -> None:
    """Anda o relógio em `passo_s`, o portal-worker trabalha, o worker roda UM ciclo real."""
    for _ in range(passos):
        if all(_terminal(mundo, o.run_id) for o in obs):
            return
        mundo.relogio.avancar(passo_s)
        mundo.portal.pegar()
        if politica:
            politica()
        mortes = await D.ciclo(worker, processo)
        for o in obs:
            o.mortes += mortes
            o.anotar(mundo)
        if ao_fim_do_ciclo:
            ao_fim_do_ciclo()


def _terminar_quando(mundo, run_id, *, despertares: int):
    """O portal termina o job quando o run já acordou `despertares` vezes e voltou a dormir."""
    def politica():
        run = mundo.banco.run(run_id)
        if run.get("status") == "waiting_input" and len(_outbox(mundo, run_id, "run.woken")) >= despertares:
            for j in _jobs(mundo, run_id):
                if j.get("status") != "done":
                    mundo.portal.terminar(j["id"])
    return politica


def _conferir_c1(mundo, obs: Observacao) -> dict[str, str]:
    """As afirmações do C1. Devolve {MOTIVO: detalhe} — vazio é verde."""
    rid = obs.run_id
    run = mundo.banco.run(rid)
    falhas: dict[str, str] = {}
    if obs.concluiu_com_job_vivo:
        falhas["CONCLUIU_POR_CIMA_DA_ESPERA"] = (
            f"o run virou `completed` com o portal_job ainda {[j.get('status') for j in _jobs(mundo, rid)]} "
            f"(linha do tempo {obs.estados})")
    if run.get("status") != "completed":
        falhas["NAO_CONCLUIU"] = f"status final {run.get('status')!r} (linha do tempo {obs.estados})"
    if not obs.passou_por("waiting_input"):
        falhas["NUNCA_DORMIU"] = f"o run nunca esteve em `waiting_input` (linha do tempo {obs.estados})"
    n = len(_eventos(mundo, rid, "run.succeeded"))
    if n != 1:
        falhas["SUCESSO_NAO_E_UM"] = f"run.succeeded ×{n} (esperado ×1)"
    n = len(_jobs(mundo, rid))
    if n != 1:
        falhas["JOBS_NAO_E_UM"] = f"portal_jobs ×{n} (esperado ×1)"
    n = _tentativas(mundo, rid, PASSO_CRIAR)
    if n != 1:
        falhas["CRIAR_NAO_E_UMA_TENTATIVA"] = f"`{PASSO_CRIAR}` com {n} tentativa(s) (esperado 1)"
    acordou = (run.get("wait_for") or {}).get("acordou") if isinstance(run.get("wait_for"), dict) else None
    if acordou != 3:
        falhas["ACORDOU_NAO_E_3"] = f"wait_for.acordou = {acordou!r} (esperado 3)"
    n = len(_outbox(mundo, rid, "run.woken"))
    if n != 3:
        falhas["DESPERTARES_NAO_SAO_3"] = f"outbox `run.woken` ×{n} (esperado ×3)"
    criar = _passo(mundo, rid, PASSO_CRIAR) or {}
    jobs = _jobs(mundo, rid)
    if jobs and (criar.get("output_summary") or {}).get("portal_job_id") != jobs[0]["id"]:
        falhas["CRIAR_NAO_GUARDOU_O_JOB"] = (f"`{PASSO_CRIAR}`.output_summary.portal_job_id = "
                                             f"{(criar.get('output_summary') or {}).get('portal_job_id')!r}")
    return falhas


async def _o_c1(mundo, X, *, modulo_do_worker=SW) -> Observacao:
    """O cenário do C1 — só ESTADO observável, para valer também contra o código de 04/10 (C7)."""
    proc = mundo.processo("worker-A")
    worker = await D.ligar_worker(proc, modulo_do_worker)
    rid = _criar(mundo, X, rotulo="c1")
    obs = Observacao(rid)
    obs.mortes += await D.ciclo(worker, proc)
    obs.anotar(mundo)
    await _girar(mundo, worker, proc, [obs], passos=10, passo_s=60,
                 politica=_terminar_quando(mundo, rid, despertares=2))
    return obs


# ═════════════════════════════════════════════════════════════════════════════
# C1 — dorme e acorda
# ═════════════════════════════════════════════════════════════════════════════
def test_c1_dorme_e_acorda(mundo, corretoras):
    _exigir_contrato()
    X, _Y = corretoras
    obs = asyncio.run(_o_c1(mundo, X))
    assert not obs.mortes, f"o processo não devia morrer no C1: {obs.mortes}"
    falhas = _conferir_c1(mundo, obs)
    assert not falhas, "C1: " + " · ".join(f"{k}: {v}" for k, v in falhas.items())
    # o :criar guarda SÓ o que declarou (ids/estados curtos): nunca o texto do portal
    saida = (_passo(mundo, obs.run_id, PASSO_CRIAR) or {}).get("output_summary") or {}
    assert set(saida) <= {"portal_job_id"}, \
        f"`{PASSO_CRIAR}` guardou chaves não declaradas em `guardar=`: {sorted(saida)}"


# ═════════════════════════════════════════════════════════════════════════════
# C2 — reinício dormindo
# ═════════════════════════════════════════════════════════════════════════════
def test_c2_reinicio_dormindo(mundo, corretoras):
    _exigir_contrato()
    X, _Y = corretoras

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)
        rid = _criar(mundo, X, rotulo="c2")
        obs = Observacao(rid)
        obs.mortes += await D.ciclo(wa, a)
        obs.anotar(mundo)
        assert mundo.banco.run(rid).get("status") == "waiting_input", \
            f"A devia deixar o run dormindo antes de morrer: {obs.estados}"
        a.morrer()                                     # kill -9 no contêiner A
        marca = len(mundo.banco.escritas)
        b = mundo.processo("worker-B")                 # o contêiner novo
        wb = await D.ligar_worker(b, SW)
        assert wb.worker_id != wa.worker_id
        await _girar(mundo, wb, b, [obs], passos=10, passo_s=60,
                     politica=_terminar_quando(mundo, rid, despertares=2))
        return obs, marca

    obs, marca = asyncio.run(cenario())
    falhas = _conferir_c1(mundo, obs)
    assert not falhas, "C2: " + " · ".join(f"{k}: {v}" for k, v in falhas.items())
    assert not [e for e in mundo.banco.escritas[marca:] if e.dono == "worker-A"], \
        "o processo morto escreveu depois de morrer (o dublê não cortou o kill -9)"
    assert [e for e in mundo.banco.escritas[marca:] if e.dono == "worker-B"], "quem concluiu foi B"


# ═════════════════════════════════════════════════════════════════════════════
# C3 — reinício no meio do :criar
# ═════════════════════════════════════════════════════════════════════════════
def test_c3_reinicio_no_meio_do_criar(mundo, corretoras):
    _exigir_contrato()
    X, _Y = corretoras

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)

        def morre_depois_do_insert(escrita):
            # o job ENTROU no banco; o :criar ainda não virou `succeeded` → kill -9 agora
            if escrita.dono == a.nome and not a.morto:
                a.morrer()
                raise D.MorteDoProcesso("worker-A morreu logo depois de criar o portal_job")

        mundo.banco.ao_gravar("portal_jobs", "insert", morre_depois_do_insert)
        rid = _criar(mundo, X, rotulo="c3")
        obs = Observacao(rid)
        obs.mortes += await D.ciclo(wa, a)
        obs.anotar(mundo)
        assert a.morto, "o gancho devia ter matado A no insert do portal_job"
        jobs_de_a = [j["id"] for j in _jobs(mundo, rid)]
        assert len(jobs_de_a) == 1, f"A devia ter deixado exatamente 1 job no banco: {jobs_de_a}"
        criar_de_a = _passo(mundo, rid, PASSO_CRIAR) or {}
        assert criar_de_a.get("status") != "succeeded", "A morreu ANTES do :criar `succeeded`"

        b = mundo.processo("worker-B")
        wb = await D.ligar_worker(b, SW)
        duracoes: list[float] = []

        def terminar_se_b_ja_dormiu():
            if mundo.banco.run(rid).get("status") == "waiting_input":
                for j in _jobs(mundo, rid):
                    if j.get("status") != "done":
                        mundo.portal.terminar(j["id"])

        async with D.MedidorDoLaco() as medidor:
            for _ in range(15):
                if _terminal(mundo, rid):
                    break
                mundo.relogio.avancar(60)
                mundo.portal.pegar()
                terminar_se_b_ja_dormiu()
                t0 = time.monotonic()
                obs.mortes += await D.ciclo(wb, b)
                duracoes.append(time.monotonic() - t0)
                obs.anotar(mundo)
        return obs, jobs_de_a, medidor.maior_atraso_s, max(duracoes or [0.0])

    obs, jobs_de_a, atraso, maior_ciclo = asyncio.run(cenario())
    rid = obs.run_id
    run = mundo.banco.run(rid)
    assert run.get("status") == "completed", f"B devia retomar e concluir: {obs.estados}"
    jobs = _jobs(mundo, rid)
    assert [j["id"] for j in jobs] == jobs_de_a, f"B criou OUTRO job: A={jobs_de_a} agora={[j['id'] for j in jobs]}"
    assert ((_passo(mundo, rid, PASSO_CRIAR) or {}).get("output_summary") or {}).get("portal_job_id") \
        == jobs_de_a[0], "o :criar de B tem de guardar o MESMO job que A criou"
    assert len(_eventos(mundo, rid, "run.succeeded")) == 1
    assert not obs.concluiu_com_job_vivo, f"concluiu com o job vivo: {obs.estados}"
    assert atraso < 1.0, f"o event loop ficou PRESO {atraso:.2f}s na retomada (espera bloqueante)"
    assert maior_ciclo < 1.0, (f"um ciclo de B levou {maior_ciclo:.2f}s: o ramo 'já existe' esperou o "
                               "portal em vez de devolver o handle (enqueue)")


# ═════════════════════════════════════════════════════════════════════════════
# C4 — cancelar dormindo
# ═════════════════════════════════════════════════════════════════════════════
def test_c4_cancelar_dormindo(mundo, corretoras):
    _exigir_contrato()
    X, _Y = corretoras

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)
        rid = _criar(mundo, X, rotulo="c4")
        obs = Observacao(rid)
        obs.mortes += await D.ciclo(wa, a)
        obs.anotar(mundo)
        assert mundo.banco.run(rid).get("status") == "waiting_input", obs.estados
        api = R.WorkRunService(mundo.processo("api").db)
        api.solicitar_cancelamento(rid, X, ator=None)
        logo_depois = mundo.banco.run(rid).get("status")
        tentativas_aguardar = _tentativas(mundo, rid, PASSO_AGUARDAR)
        outbox_antes = len(_outbox(mundo, rid))
        for j in _jobs(mundo, rid):            # a tentação: o portal termina logo depois
            mundo.portal.terminar(j["id"])
        await _girar(mundo, wa, a, [obs], passos=12, passo_s=60)
        return obs, logo_depois, tentativas_aguardar, outbox_antes

    obs, logo_depois, tentativas_aguardar, outbox_antes = asyncio.run(cenario())
    rid = obs.run_id
    assert logo_depois == "cancelled", f"cancelar um run DORMINDO é na hora (sem dono): {logo_depois!r}"
    assert mundo.banco.run(rid).get("status") == "cancelled", f"o despertar reabriu: {obs.estados}"
    assert not _outbox(mundo, rid, "run.woken"), "o despertador acordou um run cancelado"
    assert len(_outbox(mundo, rid)) == outbox_antes, "nada mais vai para a fila de um run cancelado"
    assert _tentativas(mundo, rid, PASSO_AGUARDAR) == tentativas_aguardar, ":aguardar rodou depois de cancelado"
    assert not _eventos(mundo, rid, "run.succeeded")
    assert [s for _t, s in obs.estados if s == "completed"] == []


# ═════════════════════════════════════════════════════════════════════════════
# C5 — a mensagem perdida
# ═════════════════════════════════════════════════════════════════════════════
def test_c5_mensagem_perdida(mundo, corretoras):
    _exigir_contrato()
    X, _Y = corretoras

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)
        rid = _criar(mundo, X, rotulo="c5")
        obs = Observacao(rid)
        obs.mortes += await D.ciclo(wa, a)
        obs.anotar(mundo)
        assert mundo.banco.run(rid).get("status") == "waiting_input", obs.estados
        mundo.redis.perder_proxima(lambda p: p.get("work_run_id") == rid
                                   and p.get("event_kind") == "run.woken")
        perdida_em: dict = {}

        def anotar_a_perda():
            if mundo.redis.perdidas and "t" not in perdida_em:
                perdida_em["t"] = mundo.relogio.segundos()

        await _girar(mundo, wa, a, [obs], passos=30, passo_s=60,
                     politica=_terminar_quando(mundo, rid, despertares=1),
                     ao_fim_do_ciclo=anotar_a_perda)
        return obs, perdida_em.get("t")

    obs, perdida_em = asyncio.run(cenario())
    rid = obs.run_id
    assert len(mundo.redis.perdidas) == 1, f"o cenário devia perder 1 mensagem: {mundo.redis.perdidas}"
    assert mundo.banco.run(rid).get("status") == "completed", f"a mensagem perdida prendeu o run: {obs.estados}"
    assert _outbox(mundo, rid, "run.redriven"), "quem salvou não foi o re-despacho do Postgres"
    assert obs.concluiu_em is not None and perdida_em is not None
    assert obs.concluiu_em - perdida_em > 600, (f"concluiu {obs.concluiu_em - perdida_em:.0f}s depois da "
                                                "perda: o re-despacho é para PARADO > 10 min")
    assert len(_eventos(mundo, rid, "run.succeeded")) == 1
    assert len(_jobs(mundo, rid)) == 1


# ═════════════════════════════════════════════════════════════════════════════
# C6 — duas corretoras
# ═════════════════════════════════════════════════════════════════════════════
def test_c6_duas_corretoras(mundo, corretoras):
    _exigir_contrato()
    X, Y = corretoras
    tres_horas = mundo.relogio.agora() - D.timedelta(hours=3)
    sombra = mundo.banco.semear("work_runs", {
        "id": (sid := str(uuid.uuid4())), "company_id": X, "source_type": "system",
        "outcome_type": "claims.shadow", "outcome_title": "observação de sinistro",
        "status": "running", "runtime_kind": "sombra", "workflow_key": "claims.shadow",
        "thread_id": f"work:{X}:{sid}", "input_fingerprint": "x", "idempotency_key": f"sombra:{sid}",
        "requested_at": tres_horas.isoformat(), "queued_at": tres_horas.isoformat(),
        "started_at": tres_horas.isoformat(), "heartbeat_at": tres_horas.isoformat()})
    retrato_da_sombra = copy.deepcopy(sombra)

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)
        ry = _criar(mundo, Y, rotulo="c6-y")
        oy = Observacao(ry)
        oy.mortes += await D.ciclo(wa, a)
        oy.anotar(mundo)
        mundo.relogio.avancar(30)
        rx = _criar(mundo, X, rotulo="c6-x")
        ox = Observacao(rx)
        ox.mortes += await D.ciclo(wa, a)
        ox.anotar(mundo)
        intercalou = {"sim": False}
        antes = {"x": 0, "y": 0}

        def politica():
            for rid in (rx, ry):
                _terminar_quando(mundo, rid, despertares=1)()

        def ao_fim():
            agora = {"x": len(_outbox(mundo, rx, "run.woken")), "y": len(_outbox(mundo, ry, "run.woken"))}
            if (agora["x"] > antes["x"]) != (agora["y"] > antes["y"]):
                intercalou["sim"] = True          # uma acordou enquanto a outra dormia
            antes.update(agora)

        await _girar(mundo, wa, a, [ox, oy], passos=60, passo_s=20, politica=politica, ao_fim_do_ciclo=ao_fim)
        return ox, oy, intercalou["sim"]

    ox, oy, intercalou = asyncio.run(cenario())
    for o, cid in ((ox, X), (oy, Y)):
        run = mundo.banco.run(o.run_id)
        assert run.get("status") == "completed", f"{cid[:8]}: {o.estados}"
        assert o.passou_por("waiting_input") and not o.concluiu_com_job_vivo, \
            f"{cid[:8]}: concluiu sem dormir, ou por cima da espera: {o.estados}"
        assert len(_eventos(mundo, o.run_id, "run.succeeded")) == 1
        jobs = _jobs(mundo, o.run_id)
        assert len(jobs) == 1 and jobs[0]["company_id"] == cid
        contas = {c["id"] for c in mundo.banco.linhas("portal_accounts") if c["company_id"] == cid}
        assert jobs[0].get("account_id") in contas, "o job entrou com a conta de OUTRA corretora"
    assert intercalou, "o cenário não exercitou 'A dormindo, B acordando' (as duas acordaram juntas)"

    motor = [e for e in mundo.banco.escritas if e.dono not in ("semeadura", "portal-worker")]
    for e in motor:
        if e.op in ("update", "delete") and e.antes:
            empresas = {r.get("company_id") for r in e.antes}
            assert len(empresas) == 1, (f"uma escrita CRUZOU corretoras: {e.op} {e.tabela} "
                                        f"filtros={e.filtros} empresas={sorted(empresas)}")
        if e.tabela == "work_runs" and e.op == "update" and e.antes and "status" in (e.payload or {}):
            eq = e.filtros_eq()
            linha = e.antes[0]
            assert str(eq.get("company_id")) == linha["company_id"], \
                (f"transição para {e.payload['status']!r} sem `.eq('company_id')` da linha "
                 f"(SPEC §6: TODA escrita de status é CAS com company_id): filtros={e.filtros}")
            assert eq.get("runtime_kind") == "smith", \
                (f"transição para {e.payload['status']!r} sem `.eq('runtime_kind','smith')` "
                 f"(SPEC §6): filtros={e.filtros}")
    assert mundo.banco.run(sid) == retrato_da_sombra, "a sombra `running` sem lease foi TOCADA"
    assert not [e for e in motor if any(r.get("id") == sid for r in e.antes)], "uma escrita casou a sombra"
    assert not _outbox(mundo, sid) and not [ev for ev in mundo.banco.linhas("work_events")
                                            if ev.get("work_run_id") == sid], "a sombra ganhou fila ou evento"


# ═════════════════════════════════════════════════════════════════════════════
# C7 — o CONTROLE: o C1 contra o código de 04/10 falha pelo motivo esperado (CLAUDE.md §9.3)
# ═════════════════════════════════════════════════════════════════════════════
def _codigo_de_04_10(monkeypatch, mundo) -> types.ModuleType:
    """Carrega do git (`5ab37e7`) o motor de 04/10 e o põe no lugar do atual SÓ neste teste."""
    modulos = (("app.services.work.runs", "backend/app/services/work/runs.py"),
               ("app.services.portals.gateway", "backend/app/services/portals/gateway.py"),
               ("app.services.work.workflows", "backend/app/services/work/workflows.py"),
               ("app.workers.smith_worker", "backend/app/workers/smith_worker.py"))
    carregados = {}
    for nome, rel in modulos:
        r = subprocess.run(["git", "-C", str(REPO), "show", f"{BASE_DE_04_10}:{rel}"],
                           capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, f"não consegui ler {rel} em {BASE_DE_04_10}: {r.stderr.strip()[:200]}"
        mod = types.ModuleType(nome)
        mod.__file__ = f"<git {BASE_DE_04_10}:{rel}>"
        mod.__package__ = nome.rpartition(".")[0]
        monkeypatch.setitem(sys.modules, nome, mod)
        exec(compile(r.stdout, mod.__file__, "exec"), mod.__dict__)  # noqa: S102
        carregados[nome] = mod
    gw = carregados["app.services.portals.gateway"]
    gw.ESPERA_MAXIMA_S, gw.ESPERA_ENTRE_LEITURAS_S = 0.3, 0.05   # a espera de 150 s, encurtada
    mundo.relogio.cobrir(*carregados.values())
    return carregados["app.workers.smith_worker"]


def test_c7_controle_o_codigo_de_04_10_falha_pelo_motivo_esperado(mundo, corretoras, monkeypatch):
    X, _Y = corretoras
    worker_antigo = _codigo_de_04_10(monkeypatch, mundo)
    obs = asyncio.run(_o_c1(mundo, X, modulo_do_worker=worker_antigo))
    falhas = _conferir_c1(mundo, obs)
    assert falhas, "🔴 o C1 PASSOU com o código de 04/10: o guarda não tem como falhar (CLAUDE.md §9.3)"
    assert "CONCLUIU_POR_CIMA_DA_ESPERA" in falhas, (
        f"o código de 04/10 falhou o C1 por OUTRO motivo — o controle não prova o que devia: {falhas}")
    assert "NUNCA_DORMIU" in falhas, f"o código de 04/10 não sabe dormir, e o C1 devia ver isso: {falhas}"
