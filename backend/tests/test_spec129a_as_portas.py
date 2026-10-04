# -*- coding: utf-8 -*-
"""SPEC-129-A F3 — AS PORTAS: Reprocessar, cancelar e decidir chegam ao motor, e só ao run DA FILA.

🔴 CLAUDE.md §9.4: as ROTAS REAIS (`app.api.work_runs.router`, por HTTP, `TestClient`) e o motor
real (`WorkRunService`, `WorkApprovalService`, `SmithWorker`). Dublê SÓ na borda: o banco
(`dubles_do_work_os.BancoEmMemoria` — filtros do PostgREST, UPDATE que devolve só o que casou, os
CHECKs da `_02`), o Redis e o relógio.

  G5  Reprocessar grava a outbox e o run RODA (o worker real o conclui) · `retry_scheduled` é
      antecipado · `efeito_incerto` → 409 (e de novo 409: nunca vira laço) · "sem fila" → 409
      intocado · cancelar dormindo → `cancelled` na hora, e o despertador não o reabre ·
      cancelar não toca o acionamento
  G9  `company_id` trocado → 404, nada escrito
  §0.8 `decidir` só aceita `pending` (uma recusa não vira aprovação) e ACORDA o run · a aprovação
      vencida vence o run · "sem fila" nunca tem o status tocado

Cada guarda novo tem a sua LINHA DE CONTROLE (§9.3): o mesmo caminho, com o fator que o guarda
decide, dando o resultado oposto.

Dois `company_id` sintéticos (uuid), nenhum nome de corretora (CLAUDE.md §13.9). As duas
corretoras REAIS ficam no teste do fio (`test_spec129a_o_fio_da_espera.py`, C6).

    cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec129a_as_portas.py -q
"""
from __future__ import annotations

import asyncio
import sys
import types
import uuid
from datetime import timedelta
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
for _p in (str(RAIZ), str(RAIZ / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
# o mesmo padrão do teste do fio: pacotes-pai como namespace (sem arrastar langchain nem o
# `app/api/__init__.py`, que importa TODAS as rotas). Os MÓDULOS são os reais, do disco.
for _n in ("app", "app.services", "app.api"):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [str(RAIZ / _n.replace(".", "/"))]
        sys.modules[_n] = _m

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import dubles_do_work_os as D  # noqa: E402
from app.api import work_runs as API  # noqa: E402
from app.services.observability import sli as SLI  # noqa: E402
from app.services.work import approvals as AP  # noqa: E402
from app.services.work import runs as R  # noqa: E402
from app.workers import smith_worker as SW  # noqa: E402

X = str(uuid.UUID(int=0x129F31))
Y = str(uuid.UUID(int=0x129F32))
WF = "system.healthcheck"          # registrado de verdade em workflows.py (o Reprocessar o resolve)
CHAVE = "chave-interna-do-teste-129a"
H = {"X-Internal-Key": CHAVE}


@pytest.fixture
def mundo(monkeypatch):
    m = D.Mundo(empresas=(X, Y))
    api = m.processo("api")
    monkeypatch.setenv("ADMIN_API_KEY", CHAVE)
    monkeypatch.setattr(API, "get_supabase_client", lambda: api.db)
    monkeypatch.setattr(SLI, "_cliente", lambda: None)   # a métrica é borda: nunca o banco real
    m.relogio.instalar()
    try:
        yield m
    finally:
        m.relogio.desinstalar()


@pytest.fixture
def http(mundo):
    app = FastAPI()
    app.include_router(API.router)
    with TestClient(app) as c:
        yield c


# ─────────────────────────────────────────────────────────────────────────────
def _semear(mundo, cid=X, *, status="failed", runtime_kind="smith", workflow_key=WF, **extra) -> str:
    rid = str(uuid.uuid4())
    quando = mundo.relogio.iso()
    mundo.banco.semear("work_runs", {
        "id": rid, "company_id": cid, "source_type": "system", "outcome_type": workflow_key,
        "outcome_title": "teste das portas", "status": status, "runtime_kind": runtime_kind,
        "workflow_key": workflow_key, "thread_id": f"work:{cid}:{rid}", "input_fingerprint": "x",
        "idempotency_key": f"portas:{rid}", "requested_at": quando, "queued_at": quando, **extra})
    return rid


def _aprovacao(mundo, rid, cid=X, *, status="pending", vence_em_s: float = 3600) -> str:
    aid = str(uuid.uuid4())
    mundo.banco.semear("approval_requests", {
        "id": aid, "company_id": cid, "work_run_id": rid, "status": status,
        "action_type": "teste", "expires_at": (mundo.relogio.agora() + timedelta(seconds=vence_em_s)).isoformat(),
        "action_fingerprint": "fp"})
    return aid


def _run(mundo, rid):
    return dict(mundo.banco.run(rid))


def _aprov(mundo, aid):
    return dict(next(a for a in mundo.banco.linhas("approval_requests") if a["id"] == aid))


def _outbox(mundo, rid, tipo=None):
    return [o for o in mundo.banco.linhas("work_queue_outbox")
            if o["work_run_id"] == rid and (tipo is None or o["event_kind"] == tipo)]


def _eventos(mundo, rid, tipo=None):
    return [e for e in mundo.banco.linhas("work_events")
            if e.get("work_run_id") == rid and (tipo is None or e["event_type"] == tipo)]


def _escritas_no_run(mundo, rid):
    return [e for e in mundo.banco.escritas
            if e.tabela == "work_runs" and e.op == "update" and any(a["id"] == rid for a in e.antes)]


def _retry(http, rid, cid=X):
    return http.post(f"/api/work/runs/{rid}/retry", params={"company_id": cid, "usuario_id": "u1"}, headers=H)


def _cancel(http, rid, cid=X):
    return http.post(f"/api/work/runs/{rid}/cancel", params={"company_id": cid, "usuario_id": "u1"}, headers=H)


def _decide(http, aid, decisao, cid=X):
    return http.post(f"/api/work/approvals/{aid}/decide", headers=H,
                     json={"company_id": cid, "usuario_id": "u1", "decisao": decisao})


def _rodar_o_worker(mundo) -> list:
    """O worker REAL (`iniciar()` real): órfãos/despertador → dispatcher → consumo."""
    proc = mundo.processo("worker-A")

    async def _ir():
        w = await D.ligar_worker(proc, SW)
        return await D.ciclo(w, proc)
    return asyncio.run(_ir())


def _auditar(mundo) -> None:
    """§7: toda transição de status de um run leva o `company_id` DA LINHA; a de um `smith`, o runtime."""
    for e in mundo.banco.escritas:
        if e.tabela != "work_runs" or e.op != "update" or "status" not in (e.payload or {}):
            continue
        if not e.antes or e.dono == "semeadura":
            continue
        eq = e.filtros_eq()
        for linha in e.antes:
            assert str(eq.get("company_id")) == linha["company_id"], f"sem company_id DA LINHA: {e.filtros}"
            if linha["runtime_kind"] == "smith":
                assert eq.get("runtime_kind") == "smith", f"sem runtime_kind='smith': {e.filtros}"


# ═════════════════════════════════════════════════════════════════════════════
# G5 — Reprocessar: a outbox, e o run RODA
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("status,extra", [
    ("retry_scheduled", {"wake_at": "+3600"}),       # antecipa a nova tentativa (antes: 409)
    ("failed", {"error_code": "x", "error_message": "caiu"}),
    ("cancelled", {}),
])
def test_reprocessar_volta_a_fila_com_outbox_e_o_run_RODA(mundo, http, status, extra):
    if extra.get("wake_at") == "+3600":
        extra = {**extra, "wake_at": (mundo.relogio.agora() + timedelta(hours=1)).isoformat()}
    rid = _semear(mundo, status=status, **extra)

    r = _retry(http, rid)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] and r.json()["status"] == "queued"
    run = _run(mundo, rid)
    assert run["status"] == "queued" and run["wake_at"] is None and run["error_code"] is None
    assert len(_outbox(mundo, rid, "run.retried")) == 1, "Reprocessar sem outbox = preso na fila para sempre"
    assert len(_eventos(mundo, rid, "run.retried")) == 1

    mortes = _rodar_o_worker(mundo)
    assert not mortes, mortes
    run = _run(mundo, rid)
    assert run["status"] == "completed", f"o run reprocessado NÃO rodou: {run['status']}"
    assert len(_eventos(mundo, rid, "run.succeeded")) == 1
    _auditar(mundo)


def test_CONTROLE_queued_sem_outbox_nao_roda(mundo, http):
    """§9.3: o que a rota de 04/10 deixava — `queued` sem outbox — NÃO roda no mesmo ciclo.
    Sem esta linha, o teste acima passaria com um worker que roda tudo o que está `queued`."""
    preso = _semear(mundo, status="queued")
    assert not _outbox(mundo, preso)
    assert not _rodar_o_worker(mundo)
    assert _run(mundo, preso)["status"] == "queued", "o controle rodou sem outbox: o guarda não discrimina"


def test_reprocessar_efeito_incerto_e_409_e_nunca_vira_laco(mundo, http):
    rid = _semear(mundo, status="failed", error_code=R.CODIGO_EFEITO_INCERTO,
                  error_message="interrompido no meio")
    antes = _run(mundo, rid)
    for _ in range(3):
        r = _retry(http, rid)
        assert r.status_code == 409, r.text
        assert "reconcilie" in r.json()["detail"].lower()
    assert _run(mundo, rid) == antes and not _outbox(mundo, rid), "a recusa escreveu no run"
    assert not _escritas_no_run(mundo, rid)


@pytest.mark.parametrize("runtime_kind,workflow_key,status", [
    ("acionamento", "acionamento.seguradora", "failed"),
    ("sombra", "claims.shadow", "failed"),
    ("proposta", "metric.proposal", "cancelled"),
])
def test_reprocessar_e_cancelar_sem_fila_sao_409_e_intocados(mundo, http, runtime_kind, workflow_key, status):
    rid = _semear(mundo, status=status, runtime_kind=runtime_kind, workflow_key=workflow_key)
    vivo = _semear(mundo, status="running", runtime_kind=runtime_kind, workflow_key=workflow_key)
    antes, antes_vivo = _run(mundo, rid), _run(mundo, vivo)

    r = _retry(http, rid)
    assert r.status_code == 409 and "fila" in r.json()["detail"], r.text
    c = _cancel(http, vivo)
    assert c.status_code == 409 and "fila" in c.json()["detail"], c.text

    assert _run(mundo, rid) == antes and _run(mundo, vivo) == antes_vivo, "um \"sem fila\" foi tocado"
    assert not _escritas_no_run(mundo, rid) and not _escritas_no_run(mundo, vivo)
    assert not _outbox(mundo, rid) and not _eventos(mundo, vivo)


def test_CONTROLE_cancelar_o_mesmo_run_DA_FILA_funciona(mundo, http):
    """§9.3: o MESMO pedido, mudando só o `runtime_kind` para `smith`, cancela — então o 409 acima
    é do guarda do runtime, e não de um cancelar que nunca funciona."""
    vivo = _semear(mundo, status="running")
    c = _cancel(http, vivo)
    assert c.status_code == 200 and c.json()["status"] == "cancelling", c.text


def test_reprocessar_estado_e_sem_executor_sao_409(mundo, http):
    rodando = _semear(mundo, status="running")
    sem_exec = _semear(mundo, status="failed", workflow_key="nao.registrado.129a")
    assert _retry(http, rodando).status_code == 409
    assert _retry(http, sem_exec).status_code == 409
    assert not _outbox(mundo, rodando) and not _outbox(mundo, sem_exec)


# ═════════════════════════════════════════════════════════════════════════════
# G9 — a outra corretora
# ═════════════════════════════════════════════════════════════════════════════
def test_outra_corretora_e_404_em_todas_as_portas(mundo, http):
    falhou = _semear(mundo, status="failed")
    dormindo = _semear(mundo, status="waiting_input", wake_at=mundo.relogio.iso())
    esperando = _semear(mundo, status="waiting_approval")
    aid = _aprovacao(mundo, esperando)
    fotos = {r: _run(mundo, r) for r in (falhou, dormindo, esperando)}
    foto_ap = _aprov(mundo, aid)

    assert _retry(http, falhou, Y).status_code == 404
    assert _cancel(http, dormindo, Y).status_code == 404
    assert _decide(http, aid, "approved", Y).status_code == 404

    assert {r: _run(mundo, r) for r in fotos} == fotos, "a porta escreveu num run de OUTRA corretora"
    assert _aprov(mundo, aid) == foto_ap
    assert not any(_outbox(mundo, r) for r in fotos)

    # controle: a MESMA chamada com a corretora certa age
    assert _retry(http, falhou, X).status_code == 200
    _auditar(mundo)


# ═════════════════════════════════════════════════════════════════════════════
# Cancelar
# ═════════════════════════════════════════════════════════════════════════════
def test_cancelar_dormindo_e_cancelled_na_hora_e_o_despertador_nao_reabre(mundo, http):
    dormindo = _semear(mundo, status="waiting_input", wake_at=mundo.relogio.iso(),
                       wait_for={"tipo": "portal_job", "ref": "j1"})
    agendado = _semear(mundo, status="retry_scheduled", wake_at=mundo.relogio.iso())
    for rid in (dormindo, agendado):
        c = _cancel(http, rid)
        assert c.status_code == 200 and c.json()["status"] == "cancelled", c.text
        assert _run(mundo, rid)["status"] == "cancelled" and _run(mundo, rid)["wake_at"] is None

    mundo.relogio.avancar(300)
    assert not _rodar_o_worker(mundo)
    for rid in (dormindo, agendado):
        assert _run(mundo, rid)["status"] == "cancelled", "o despertador reabriu um cancelado"
        assert not _outbox(mundo, rid)
    _auditar(mundo)


def test_cancelar_o_que_ja_terminou_e_409(mundo, http):
    feito = _semear(mundo, status="completed")
    antes = _run(mundo, feito)
    c = _cancel(http, feito)
    assert c.status_code == 409, c.text
    assert _run(mundo, feito) == antes


# ═════════════════════════════════════════════════════════════════════════════
# decidir — só `pending`, e a decisão ACORDA o run
# ═════════════════════════════════════════════════════════════════════════════
def test_aprovacao_acorda_o_run_e_ele_RODA(mundo, http):
    rid = _semear(mundo, status="waiting_approval")
    aid = _aprovacao(mundo, rid)
    r = _decide(http, aid, "approved")
    assert r.status_code == 200, r.text
    assert r.json()["approval"]["run_despertado"] is True
    assert _aprov(mundo, aid)["status"] == "approved"
    assert _run(mundo, rid)["status"] == "queued" and len(_outbox(mundo, rid, "run.woken")) == 1

    assert not _rodar_o_worker(mundo)
    assert _run(mundo, rid)["status"] == "completed", "a aprovação não levou o run até o fim"
    _auditar(mundo)


def test_rejeitada_depois_aprovada_a_segunda_e_recusada(mundo, http):
    rid = _semear(mundo, status="waiting_approval")
    aid = _aprovacao(mundo, rid)
    r1 = _decide(http, aid, "rejected")
    assert r1.status_code == 200, r1.text
    assert _run(mundo, rid)["status"] == "cancelled", "a recusa não encerrou o run"
    assert not _outbox(mundo, rid)

    r2 = _decide(http, aid, "approved")
    assert r2.status_code == 409, f"uma RECUSA virou APROVAÇÃO depois: {r2.text}"
    assert "recusada" in r2.json()["detail"], r2.text
    assert _aprov(mundo, aid)["status"] == "rejected" and _aprov(mundo, aid)["decision"] == "rejected"
    assert _run(mundo, rid)["status"] == "cancelled" and not _outbox(mundo, rid)
    _auditar(mundo)


def test_o_CAS_da_decisao_vence_a_leitura_velha(mundo, http, monkeypatch):
    """Duas pessoas decidem ao mesmo tempo: as duas LERAM `pending`. O UPDATE com
    `.eq("status","pending")` deixa UMA ganhar; a outra recebe nada → 409, nada sobrescrito."""
    rid = _semear(mundo, status="waiting_approval")
    aid = _aprovacao(mundo, rid)
    leitura_velha = {"id": aid, "company_id": X, "status": "pending",
                     "expires_at": _aprov(mundo, aid)["expires_at"], "work_run_id": rid}
    assert _decide(http, aid, "rejected").status_code == 200
    monkeypatch.setattr(AP.WorkApprovalService, "_ler_aprovacao", lambda self, c, a: dict(leitura_velha))
    r = _decide(http, aid, "approved")
    assert r.status_code == 409, f"a segunda decisão sobrescreveu a primeira: {r.text}"
    assert _aprov(mundo, aid)["status"] == "rejected"
    assert _run(mundo, rid)["status"] == "cancelled"


def test_aprovacao_vencida_pelo_relogio_e_409_e_nao_acorda(mundo, http):
    rid = _semear(mundo, status="waiting_approval")
    aid = _aprovacao(mundo, rid, vence_em_s=60)
    mundo.relogio.avancar(120)
    r = _decide(http, aid, "approved")
    assert r.status_code == 409 and "venceu" in r.json()["detail"], r.text
    assert _run(mundo, rid)["status"] == "waiting_approval" and not _outbox(mundo, rid)
    # controle: a MESMA aprovação, decidida antes de vencer, acorda
    rid2 = _semear(mundo, status="waiting_approval")
    aid2 = _aprovacao(mundo, rid2, vence_em_s=60)
    assert _decide(http, aid2, "approved").status_code == 200
    assert _run(mundo, rid2)["status"] == "queued"


def test_decidir_sobre_sem_fila_registra_mas_nao_toca_o_status(mundo, http):
    """A proposta de métrica (runtime `proposta`) lê `approval_requests` por conta própria: a
    decisão é registrada; o STATUS do run nunca é tocado, nem com um evento de CAS perdido."""
    for decisao in ("approved", "rejected"):
        rid = _semear(mundo, status="waiting_approval", runtime_kind="proposta",
                      workflow_key="metric.proposal")
        aid = _aprovacao(mundo, rid)
        antes = _run(mundo, rid)
        r = _decide(http, aid, decisao)
        assert r.status_code == 200, r.text
        assert r.json()["approval"]["run_despertado"] is False
        assert _run(mundo, rid) == antes and not _escritas_no_run(mundo, rid), "o \"sem fila\" foi tocado"
        assert not _eventos(mundo, rid, "run.cas_perdido"), "a porta tentou transicionar um \"sem fila\""


def test_expirar_vencidas_vence_o_run_smith_e_poupa_o_sem_fila(mundo):
    smith = _semear(mundo, status="waiting_approval")
    proposta = _semear(mundo, status="waiting_approval", runtime_kind="proposta",
                       workflow_key="metric.proposal")
    outra = _semear(mundo, Y, status="waiting_approval")
    viva = _semear(mundo, status="waiting_approval")
    a1, a2, a3 = (_aprovacao(mundo, smith, vence_em_s=60), _aprovacao(mundo, proposta, vence_em_s=60),
                  _aprovacao(mundo, outra, Y, vence_em_s=60))
    a4 = _aprovacao(mundo, viva, vence_em_s=7200)   # controle: não venceu
    antes_proposta = _run(mundo, proposta)
    mundo.relogio.avancar(120)

    n = AP.WorkApprovalService(mundo.processo("worker-A").db).expirar_vencidas()
    assert n == 3
    assert all(_aprov(mundo, a)["status"] == "expired" for a in (a1, a2, a3))
    assert _run(mundo, smith)["status"] == "expired", "a aprovação venceu e o run ficou esperando para sempre"
    assert _run(mundo, outra)["status"] == "expired"
    assert _run(mundo, proposta) == antes_proposta and not _escritas_no_run(mundo, proposta)
    assert _aprov(mundo, a4)["status"] == "pending" and _run(mundo, viva)["status"] == "waiting_approval"
    _auditar(mundo)


# ═════════════════════════════════════════════════════════════════════════════
# /health conta as esperas
# ═════════════════════════════════════════════════════════════════════════════
def test_health_conta_as_esperas(mundo, http):
    agora = mundo.relogio.agora()
    _semear(mundo, status="waiting_input", wake_at=(agora + timedelta(minutes=5)).isoformat())
    _semear(mundo, status="waiting_input", wake_at=(agora - timedelta(minutes=30)).isoformat())
    _semear(mundo, status="retry_scheduled", wake_at=(agora + timedelta(minutes=1)).isoformat())
    _semear(mundo, status="waiting_input", runtime_kind="acionamento",
            workflow_key="acionamento.seguradora")   # sem fila: não conta como espera da fila
    r = http.get("/api/work/health", headers=H)
    assert r.status_code == 200, r.text
    s = r.json()
    assert (s["runs_dormindo"], s["runs_nova_tentativa_agendada"], s["runs_despertar_atrasado"]) == (2, 1, 1), s


def test_sem_chave_e_401(mundo, http):
    rid = _semear(mundo, status="failed")
    r = http.post(f"/api/work/runs/{rid}/retry", params={"company_id": X})
    assert r.status_code == 401 and _run(mundo, rid)["status"] == "failed"
