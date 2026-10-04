# -*- coding: utf-8 -*-
"""SPEC-129-A F1 — O CAS do Work OS: toda escrita de status é "a linha ou nada".

O que este guarda prova, com o MOTOR real (`WorkRunService`, `SmithWorker._processar`) sobre o
dublê de BORDA do banco (`dubles_do_work_os.BancoEmMemoria`: filtros com a semântica do PostgREST,
UPDATE que devolve SÓ as linhas que casaram, e os CHECKs da `_02`):

  G3  duas leases → UMA ganha · `concluir` sobre `waiting_approval` → recusado · `cancelling` e
      `waiting_*` nunca viram `running` · token alheio não escreve
  G4  despertador e re-despacho só `smith`, só workflow registrado; idade por `requested_at`;
      espera com `wait_for` nunca expira pela idade; a sombra `running` sem lease fica INTOCADA
  G1  o worker NÃO conclui sobre `ESPERANDO` (espião em `concluir`, com linha de controle)
  D-129A-4  `EfeitoIncerto` → `failed efeito_incerto`, e o Reprocessar recusa (409)
  §7  toda transição de status de um run `smith` leva `.eq("company_id")` DA LINHA e
      `.eq("runtime_kind","smith")` (auditoria sobre o registro de escritas do dublê)

Dois `company_id` sintéticos (uuid), nenhum nome de corretora (CLAUDE.md §13.9). As duas corretoras
REAIS ficam no teste do fio (`test_spec129a_o_fio_da_espera.py`, C6).

    cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec129a_o_cas.py -q
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
for _n in ("app", "app.services"):   # o mesmo padrão do teste do fio: sem arrastar langchain
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [str(RAIZ / _n.replace(".", "/"))]
        sys.modules[_n] = _m

import dubles_do_work_os as D  # noqa: E402
from app.services.work import runs as R  # noqa: E402
from app.services.work import workflows as W  # noqa: E402
from app.workers import smith_worker as SW  # noqa: E402

X = str(uuid.UUID(int=0x1290A1))
Y = str(uuid.UUID(int=0x1290A2))
WF = "system.healthcheck"
REGISTRO = {WF: None, "bridge.routine.execute": None}


@pytest.fixture
def mundo():
    m = D.Mundo(empresas=(X, Y))
    m.relogio.instalar()
    try:
        yield m
    finally:
        m.relogio.desinstalar()


def _svc(mundo, nome="worker-A") -> R.WorkRunService:
    return R.WorkRunService(mundo.processo(nome).db)


def _semear(mundo, cid=X, *, status="queued", runtime_kind="smith", workflow_key=WF,
            idade_s: float = 0, **extra) -> str:
    rid = str(uuid.uuid4())
    quando = (mundo.relogio.agora() - timedelta(seconds=idade_s)).isoformat()
    mundo.banco.semear("work_runs", {
        "id": rid, "company_id": cid, "source_type": "system", "outcome_type": workflow_key,
        "outcome_title": "teste do CAS", "status": status, "runtime_kind": runtime_kind,
        "workflow_key": workflow_key, "thread_id": f"work:{cid}:{rid}", "input_fingerprint": "x",
        "idempotency_key": f"cas:{rid}", "requested_at": quando, "queued_at": quando, **extra})
    return rid


def _run(mundo, rid):
    return mundo.banco.run(rid)


def _outbox(mundo, rid, tipo=None):
    return [o for o in mundo.banco.linhas("work_queue_outbox")
            if o["work_run_id"] == rid and (tipo is None or o["event_kind"] == tipo)]


def _eventos(mundo, rid, tipo=None):
    return [e for e in mundo.banco.linhas("work_events")
            if e.get("work_run_id") == rid and (tipo is None or e["event_type"] == tipo)]


def _auditar(mundo) -> None:
    """§6/§7: toda transição de status de um run `smith` é CAS com company_id DA LINHA e runtime_kind."""
    for e in mundo.banco.escritas:
        if e.tabela != "work_runs" or e.op != "update" or "status" not in (e.payload or {}):
            continue
        if not e.antes or e.dono == "semeadura":
            continue
        eq = e.filtros_eq()
        for linha in e.antes:
            assert str(eq.get("company_id")) == linha["company_id"], \
                f"transição para {e.payload['status']!r} sem company_id DA LINHA: {e.filtros}"
            if linha["runtime_kind"] == "smith":
                assert eq.get("runtime_kind") == "smith", \
                    f"transição para {e.payload['status']!r} sem runtime_kind='smith': {e.filtros}"


# ═════════════════════════════════════════════════════════════════════════════
# G3 — a lease
# ═════════════════════════════════════════════════════════════════════════════
def test_duas_leases_uma_ganha(mundo):
    rid = _semear(mundo)
    a = _svc(mundo, "worker-A").adquirir_lease(rid, "A", company_id=X)
    b = _svc(mundo, "worker-B").adquirir_lease(rid, "B", company_id=X)
    assert (a is None) != (b is None), f"as duas leases ganharam (ou nenhuma): A={a} B={b}"
    assert _run(mundo, rid)["lease_owner"] == "A" and _run(mundo, rid)["status"] == "running"
    _auditar(mundo)


def test_lease_vencida_se_retoma_e_a_viva_nao(mundo):
    rid = _semear(mundo)
    assert _svc(mundo).adquirir_lease(rid, "A", company_id=X)
    assert _svc(mundo, "worker-B").adquirir_lease(rid, "B", company_id=X) is None
    mundo.relogio.avancar(R.LEASE_DURACAO_SEGUNDOS + 1)
    b = _svc(mundo, "worker-B").adquirir_lease(rid, "B", company_id=X)
    assert b and _run(mundo, rid)["lease_owner"] == "B"


@pytest.mark.parametrize("status", ["cancelling", "waiting_input", "waiting_approval",
                                    "retry_scheduled", "completed", "cancelled"])
def test_espera_cancelamento_e_terminal_nunca_viram_running(mundo, status):
    extra = {"wake_at": mundo.relogio.iso()} if status in R.ESTADOS_DE_ESPERA else {}
    rid = _semear(mundo, status=status, **extra)
    assert _svc(mundo).adquirir_lease(rid, "A", company_id=X) is None
    assert _run(mundo, rid)["status"] == status


def test_lease_so_da_fila_e_so_da_corretora(mundo):
    sombra = _semear(mundo, status="running", runtime_kind="sombra", workflow_key="claims.shadow",
                     idade_s=3 * 3600)
    retrato = dict(_run(mundo, sombra))
    assert _svc(mundo).adquirir_lease(sombra, "A", company_id=X) is None
    assert _run(mundo, sombra) == retrato, "a lease tocou um run SEM FILA"
    rid = _semear(mundo, X)
    assert _svc(mundo).adquirir_lease(rid, "A", company_id=Y) is None, \
        "a mensagem trazia OUTRA corretora e a lease foi tomada"
    assert _run(mundo, rid)["status"] == "queued"


# ═════════════════════════════════════════════════════════════════════════════
# G3 — o fechamento é do dono, e só de quem está rodando
# ═════════════════════════════════════════════════════════════════════════════
def test_concluir_sobre_waiting_approval_e_recusado(mundo):
    rid = _semear(mundo)
    svc = _svc(mundo)
    lease = svc.adquirir_lease(rid, "A", company_id=X)
    assert svc._transicionar(rid, "waiting_approval", {"lease_owner": None, "lease_token": None,
                                                       "lease_expires_at": None},
                             de="running", lease_token=lease["lease_token"], company_id=X)
    assert svc.concluir(rid, X, "feito", lease_token=lease["lease_token"]) is False
    assert _run(mundo, rid)["status"] == "waiting_approval"
    assert not _eventos(mundo, rid, "run.succeeded"), "run.succeeded saiu sem a transição"
    assert _eventos(mundo, rid, "run.cas_perdido")
    _auditar(mundo)


def test_token_alheio_nao_conclui_nem_dorme_e_o_dono_conclui_sem_apagar_a_espera(mundo):
    rid = _semear(mundo)
    svc = _svc(mundo)
    lease = svc.adquirir_lease(rid, "A", company_id=X)
    alheio = str(uuid.uuid4())
    assert svc.concluir(rid, X, "x", lease_token=alheio) is False
    assert svc.dormir(rid, lease_token=alheio, acordar_em_s=60, wait_for={"tipo": "t"},
                      company_id=X) is R.ESPERANDO
    assert _run(mundo, rid)["status"] == "running", "um token alheio fez o run dormir"
    svc.dormir(rid, lease_token=lease["lease_token"], acordar_em_s=60,
               wait_for={"tipo": "portal_job", "ref": "j1"}, company_id=X)
    mundo.relogio.avancar(61)
    svc.despertar_vencidos(REGISTRO)
    l2 = svc.adquirir_lease(rid, "A", company_id=X)
    assert svc.concluir(rid, X, "feito", lease_token=l2["lease_token"]) is True
    run = _run(mundo, rid)
    assert run["status"] == "completed" and run["wait_for"]["acordou"] == 1, \
        f"concluir apagou a história da espera: {run.get('wait_for')}"
    assert len(_eventos(mundo, rid, "run.succeeded")) == 1
    _auditar(mundo)


# ═════════════════════════════════════════════════════════════════════════════
# dormir e despertar
# ═════════════════════════════════════════════════════════════════════════════
def test_dorme_acorda_e_preserva_prazo_e_contagem(mundo):
    rid = _semear(mundo)
    svc = _svc(mundo)
    lease = svc.adquirir_lease(rid, "A", company_id=X)
    svc.dormir(rid, lease_token=lease["lease_token"], acordar_em_s=120,
               wait_for={"tipo": "portal_job", "ref": "J", "prazo_s": 3600, "texto": "x" * 500,
                         "aninhado": {"cpf": "123"}}, company_id=X)
    run = _run(mundo, rid)
    assert run["status"] == "waiting_input" and run["lease_token"] is None and run["wake_at"]
    prazo = run["wait_for"]["prazo"]
    assert "texto" not in run["wait_for"] and "aninhado" not in run["wait_for"], \
        "wait_for guardou texto livre / objeto aninhado"
    mundo.relogio.avancar(60)
    assert svc.despertar_vencidos(REGISTRO) == [] and _run(mundo, rid)["status"] == "waiting_input"
    mundo.relogio.avancar(61)
    assert len(svc.despertar_vencidos(REGISTRO)) == 1
    run = _run(mundo, rid)
    assert run["status"] == "queued" and run["wait_for"]["acordou"] == 1 and run["wake_at"] is None
    assert len(_outbox(mundo, rid, "run.woken")) == 1
    lease = svc.adquirir_lease(rid, "A", company_id=X)
    mundo.relogio.avancar(30)
    svc.dormir(rid, lease_token=lease["lease_token"], acordar_em_s=120,
               wait_for={"tipo": "portal_job", "ref": "J", "prazo_s": 3600}, company_id=X)
    run = _run(mundo, rid)
    assert run["wait_for"]["prazo"] == prazo, "o 2º dormir regravou o prazo (ele é absoluto)"
    assert run["wait_for"]["acordou"] == 1
    _auditar(mundo)


def test_dois_despertadores_um_envia(mundo):
    rid = _semear(mundo, status="waiting_input", wake_at=mundo.relogio.iso(),
                  wait_for={"tipo": "t", "ref": "r", "acordou": 0})
    a, b = _svc(mundo, "worker-A"), _svc(mundo, "worker-B")
    ok_a = a._transicionar(rid, "queued", {}, de="waiting_input", company_id=X)
    ok_b = b._transicionar(rid, "queued", {}, de="waiting_input", company_id=X)
    assert (ok_a, ok_b) == (True, False), "o segundo CAS também ganhou"


def test_despertador_so_smith_so_registrado(mundo):
    agora = mundo.relogio.iso()
    estranho = _semear(mundo, status="waiting_input", workflow_key="nao.registrado", wake_at=agora)
    sem_fila = _semear(mundo, status="waiting_input", runtime_kind="acionamento",
                       workflow_key="acionamento.seguradora")
    retratos = {r: dict(_run(mundo, r)) for r in (estranho, sem_fila)}
    mundo.relogio.avancar(60)
    _svc(mundo).despertar_vencidos(REGISTRO)
    _svc(mundo).redespachar_parados(REGISTRO)
    # e o "sem fila" continua intocado MESMO com a chave dele no registro (só o runtime_kind o protege)
    _svc(mundo).despertar_vencidos({**REGISTRO, "acionamento.seguradora": None})
    for r, retrato in retratos.items():
        assert _run(mundo, r) == retrato, f"o despertador tocou {retrato['workflow_key']}"
        assert not _outbox(mundo, r) and not _eventos(mundo, r)


def test_idade_e_prazo(mundo):
    desistiu: list = []

    class Handler:
        idade_maxima_s = 2 * 3600

        @staticmethod
        def ao_desistir(db, run, motivo):
            desistiu.append((run["id"], motivo))

    registro = {WF: Handler}
    agora = mundo.relogio.iso()
    velho_sem_espera = _semear(mundo, status="retry_scheduled", idade_s=3 * 3600, wake_at=agora)
    velho_com_espera = _semear(mundo, status="waiting_input", idade_s=3 * 3600, wake_at=agora,
                               wait_for={"tipo": "t", "ref": "r", "acordou": 2,
                                         "prazo": (mundo.relogio.agora() + timedelta(hours=20)).isoformat()})
    prazo_vencido = _semear(mundo, status="waiting_input", wake_at=agora,
                            wait_for={"tipo": "t", "ref": "r",
                                      "prazo": (mundo.relogio.agora() - timedelta(hours=2)).isoformat()})
    _svc(mundo).despertar_vencidos(registro)

    r = _run(mundo, velho_sem_espera)
    assert (r["status"], r["error_code"]) == ("expired", R.CODIGO_EXPIRADO_PELA_IDADE)
    assert not _outbox(mundo, velho_sem_espera), "o expirado foi para a fila"
    assert [e["severity"] for e in _eventos(mundo, velho_sem_espera, "run.expired")] == ["warning"]
    assert _run(mundo, velho_com_espera)["status"] == "queued", \
        "uma espera com wait_for expirou pela IDADE"
    r = _run(mundo, prazo_vencido)
    assert (r["status"], r["error_code"]) == ("expired", R.CODIGO_ESPERA_VENCIDA)
    assert sorted(d[0] for d in desistiu) == sorted([velho_sem_espera, prazo_vencido]), \
        "o workflow não soube que o Work OS desistiu (a cobrança sumiria em silêncio)"
    _auditar(mundo)


# ═════════════════════════════════════════════════════════════════════════════
# G4 — o re-despacho e a sombra
# ═════════════════════════════════════════════════════════════════════════════
def test_redespacho_cura_o_parado_e_nao_toca_a_sombra(mundo):
    parado = _semear(mundo, idade_s=11 * 60)
    recente = _semear(mundo, idade_s=5 * 60)
    velho = _semear(mundo, idade_s=3 * 3600)
    hb = (mundo.relogio.agora() - timedelta(minutes=11)).isoformat()
    rodando_sem_dono = _semear(mundo, status="running", idade_s=20 * 60, heartbeat_at=hb, started_at=hb)
    sombra = _semear(mundo, status="running", runtime_kind="sombra", workflow_key="claims.shadow",
                     idade_s=3 * 3600, heartbeat_at=hb, started_at=hb)
    retrato_sombra = dict(_run(mundo, sombra))

    # 🔴 A chave da sombra entra no REGISTRO de propósito: hoje nenhum "sem fila" usa chave
    #    registrada, e o registro esconderia a falta do filtro `runtime_kind`. Aqui ele fica SOZINHO.
    registro = {**REGISTRO, "claims.shadow": None}
    a, b = _svc(mundo, "worker-A"), _svc(mundo, "worker-B")
    a.redespachar_parados(registro)
    b.redespachar_parados(registro)   # o 2º varredor não reenvia: o CAS regravou o relógio

    assert len(_outbox(mundo, parado, "run.redriven")) == 1
    assert not _outbox(mundo, recente)
    assert (_run(mundo, velho)["status"], _run(mundo, velho)["error_code"]) == \
        ("expired", R.CODIGO_EXPIRADO_PELA_IDADE)
    assert _run(mundo, rodando_sem_dono)["status"] == "queued"
    assert len(_outbox(mundo, rodando_sem_dono, "run.redriven")) == 1
    assert _run(mundo, sombra) == retrato_sombra, "o re-despacho TOCOU a sombra `running` sem lease"
    assert not _outbox(mundo, sombra) and not _eventos(mundo, sombra), "a sombra ganhou fila ou evento"
    _auditar(mundo)


def test_orfaos_voltam_e_cancelamento_orfao_vence(mundo):
    vencida = (mundo.relogio.agora() - timedelta(seconds=5)).isoformat()
    lease = {"lease_owner": "morto", "lease_token": str(uuid.uuid4()), "lease_expires_at": vencida}
    orfao = _semear(mundo, status="running", **lease)
    cancelando = _semear(mundo, status="cancelling", **{**lease, "lease_token": str(uuid.uuid4())})
    _svc(mundo).recuperar_orfaos()
    assert _run(mundo, orfao)["status"] == "queued" and _outbox(mundo, orfao, "run.recovered")
    assert _run(mundo, cancelando)["status"] == "cancelled", "um cancelamento pedido voltou para a fila"
    assert not _outbox(mundo, cancelando)
    _auditar(mundo)


# ═════════════════════════════════════════════════════════════════════════════
# As portas: cancelar, Reprocessar, aprovação
# ═════════════════════════════════════════════════════════════════════════════
def test_cancelar_dormindo_e_na_hora_e_o_despertar_nao_reabre(mundo):
    dormindo = _semear(mundo, status="waiting_input", wake_at=mundo.relogio.iso())
    assert _svc(mundo, "api").solicitar_cancelamento(dormindo, X) == "cancelled"
    mundo.relogio.avancar(120)
    _svc(mundo).despertar_vencidos(REGISTRO)
    assert _run(mundo, dormindo)["status"] == "cancelled" and not _outbox(mundo, dormindo)

    rodando = _semear(mundo)
    _svc(mundo).adquirir_lease(rodando, "A", company_id=X)
    assert _svc(mundo, "api").solicitar_cancelamento(rodando, X) == "cancelling"

    sem_fila = _semear(mundo, status="running", runtime_kind="acionamento",
                       workflow_key="acionamento.seguradora")
    assert _svc(mundo, "api").solicitar_cancelamento(sem_fila, X) == "cancelling", \
        "o \"sem fila\" mudou de comportamento"
    assert _svc(mundo, "api").solicitar_cancelamento(dormindo, Y) is None, "cancelou o run de OUTRA corretora"
    _auditar(mundo)


def test_reprocessar(mundo):
    api = _svc(mundo, "api")
    falhou = _semear(mundo, status="failed", error_code="x")
    r = api.reprocessar(falhou, X, "u1", workflows=REGISTRO)
    assert r["ok"] and _run(mundo, falhou)["status"] == "queued"
    assert len(_outbox(mundo, falhou, "run.retried")) == 1, "Reprocessar sem outbox = preso para sempre"

    agendado = _semear(mundo, status="retry_scheduled", wake_at=mundo.relogio.iso())
    assert api.reprocessar(agendado, X, workflows=REGISTRO)["ok"], "não antecipou o retry_scheduled"

    casos = {
        "efeito_incerto": (_semear(mundo, status="failed", error_code=R.CODIGO_EFEITO_INCERTO), X, 409),
        "sem_fila": (_semear(mundo, status="failed", runtime_kind="acionamento",
                             workflow_key="acionamento.seguradora"), X, 409),
        "nao_encontrado": (falhou, Y, 404),
        "estado": (_semear(mundo, status="completed"), X, 409),
        "sem_executor": (_semear(mundo, status="failed", workflow_key="nao.registrado"), X, 409),
    }
    for codigo, (rid, cid, http) in casos.items():
        antes = dict(_run(mundo, rid))
        r = api.reprocessar(rid, cid, workflows=REGISTRO)
        assert (r["ok"], r["http"], r["codigo"]) == (False, http, codigo), f"{codigo}: {r}"
        assert _run(mundo, rid) == antes, f"{codigo}: a recusa escreveu no run"
    _auditar(mundo)


def test_despertar_por_aprovacao(mundo):
    aprovado = _semear(mundo, status="waiting_approval")
    recusado = _semear(mundo, status="waiting_approval")
    svc = _svc(mundo, "api")
    assert svc.despertar_por_aprovacao(aprovado, Y, "approved") is False, "acordou o run de OUTRA corretora"
    assert svc.despertar_por_aprovacao(aprovado, X, "approved") is True
    assert _run(mundo, aprovado)["status"] == "queued" and len(_outbox(mundo, aprovado, "run.woken")) == 1
    assert svc.despertar_por_aprovacao(aprovado, X, "approved") is False, "decisão repetida acordou de novo"
    assert svc.despertar_por_aprovacao(recusado, X, "rejected") is True
    assert _run(mundo, recusado)["status"] == "cancelled" and not _outbox(mundo, recusado)
    _auditar(mundo)


# ═════════════════════════════════════════════════════════════════════════════
# G1 — o worker não conclui sobre ESPERANDO · D-129A-4 — EfeitoIncerto
# ═════════════════════════════════════════════════════════════════════════════
class _Espiao(R.WorkRunService):
    def __init__(self, db):
        super().__init__(db)
        self.concluir_chamado = 0

    def concluir(self, *a, **k):
        self.concluir_chamado += 1
        return super().concluir(*a, **k)


def _worker(mundo) -> tuple:
    proc = mundo.processo("worker-A")
    w = SW.SmithWorker()
    w.db, w.worker_id = proc.db, "worker-A"
    w.runs = _Espiao(proc.db)
    return w, proc


def _processar(mundo, workflow_key, handler):
    w, _proc = _worker(mundo)
    rid = _semear(mundo, workflow_key=workflow_key)
    lease = w.runs.adquirir_lease(rid, w.worker_id, company_id=X)
    W._REGISTRO[workflow_key] = handler
    try:
        asyncio.run(w._processar(rid, X, {"workflow_key": workflow_key},
                                 lease_token=lease["lease_token"]))
    finally:
        W._REGISTRO.pop(workflow_key, None)
    return w, rid


def test_o_worker_nao_conclui_sobre_ESPERANDO(mundo):
    async def dorme(ctx):
        return ctx["runs"].dormir(ctx["run_id"], lease_token=ctx["lease_token"], acordar_em_s=120,
                                  wait_for={"tipo": "teste", "ref": "1"}, company_id=ctx["company_id"])

    w, rid = _processar(mundo, "teste.129a.dorme", dorme)
    assert w.runs.concluir_chamado == 0, "o worker chamou concluir() sobre um handler que DORMIU"
    assert _run(mundo, rid)["status"] == "waiting_input"
    assert not _eventos(mundo, rid, "run.succeeded")
    _auditar(mundo)


def test_CONTROLE_o_worker_conclui_quem_terminou(mundo):
    """Sem esta linha, o guarda acima passaria com um worker que nunca conclui nada (§9.3)."""
    async def termina(ctx):
        return "feito"

    w, rid = _processar(mundo, "teste.129a.termina", termina)
    assert w.runs.concluir_chamado == 1 and _run(mundo, rid)["status"] == "completed"
    assert len(_eventos(mundo, rid, "run.succeeded")) == 1


def test_efeito_incerto_vira_failed_e_o_reprocessar_recusa(mundo):
    async def interrompido(ctx):
        raise R.EfeitoIncerto("executar_rotina estava `running`")

    _w, rid = _processar(mundo, "teste.129a.incerto", interrompido)
    run = _run(mundo, rid)
    assert (run["status"], run["error_code"]) == ("failed", R.CODIGO_EFEITO_INCERTO)
    assert _eventos(mundo, rid, "effect.uncertain")
    r = _svc(mundo, "api").reprocessar(rid, X, workflows={"teste.129a.incerto": None})
    assert (r["ok"], r["http"], r["codigo"]) == (False, 409, R.CODIGO_EFEITO_INCERTO)
    _auditar(mundo)


def test_o_caminho_sem_fila_continua_fechando_o_proprio_run(mundo):
    """O portal da SPEC-EXTRA-001.10 fecha o PRÓPRIO run sem lease (`fechar_work_run`)."""
    rid = _semear(mundo, status="running", runtime_kind="portal", workflow_key="portal.vidros")
    svc = _svc(mundo, "portal-tool")
    assert svc.concluir(rid, X, "Atendimento aberto", {"numero_do_atendimento": "1"})
    assert _run(mundo, rid)["status"] == "completed"
    outro = _semear(mundo, status="running", runtime_kind="portal", workflow_key="portal.vidros")
    svc.concluir(outro, Y, "x")
    assert _run(mundo, outro)["status"] == "running", "fechou o run de OUTRA corretora"
