# -*- coding: utf-8 -*-
"""SPEC-129-A F2 · G6 — O LOOP NÃO TRAVA: a espera do portal não segura o processo.

📊 Antes (SPEC-129-A §0, problema 4): `gateway.py` fazia `time.sleep` de até 150 s DENTRO do
`async def` do workflow — o event loop parava, o heartbeat parava, a lease de 120 s vencia.

O motor real: `SmithWorker`, `portal_operation` + `executar_passo`, `PortalExecutionGateway` (modo
`on`). Borda: banco, Redis, portal-worker, relógio (`dubles_do_work_os`). O teto da espera
BLOQUEANTE fica em 3 s (`PORTAL_GATEWAY_WAIT_S=3`): se algum caminho ainda bloquear, o teste MEDE.

  G6.1 ticker de 100 ms com atraso < 1 s durante `portal.operation` inteira (cria, dorme, acorda, conclui)
  G6.2 a retomada que REENCONTRA o job (o C3): atraso < 1 s e nenhum ciclo ≥ 1 s
  G6.3 o gateway: "já existe" + ENFILEIRAR devolve o handle SEM esperar (controle: AGUARDAR espera)
  G6.4 o gateway honra a chave do chamador também em LEITURA (controle: sem chave, leitura = sem chave)
  G6.5 `portal.operation` SEMPRE enfileira, e chama o gateway FORA do event loop (`to_thread`)
  G6.6 nenhum `time.sleep` alcançável dos workflows registrados

    cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/test_spec129a_o_loop_nao_trava.py -q
"""
from __future__ import annotations

import asyncio
import re
import sys
import threading
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
for _p in (str(RAIZ), str(RAIZ / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from test_spec129a_o_fio_da_espera import (  # noqa: E402,F401  (fixtures e leituras do fio)
    OP, PASSO_CRIAR, SEGURADORA, _criar, _jobs, _passo, corretoras, mundo,
)

import dubles_do_work_os as D  # noqa: E402
from app.services.portals import contracts as C  # noqa: E402
from app.services.portals import gateway as G  # noqa: E402
from app.workers import smith_worker as SW  # noqa: E402

LIMITE_S = 1.0


async def _girar_medindo(mundo, worker, proc, run_id, *, passos=15, passo_s=60, terminar=True):
    """Anda o relógio; o portal termina o job quando o run DORME. Devolve (maior ciclo, mortes)."""
    duracoes, mortes = [], []
    for _ in range(passos):
        if mundo.banco.run(run_id).get("status") in D.ESTADOS_TERMINAIS_DO_RUN:
            break
        mundo.relogio.avancar(passo_s)
        mundo.portal.pegar()
        if terminar and mundo.banco.run(run_id).get("status") == "waiting_input":
            for j in _jobs(mundo, run_id):
                if j.get("status") != "done":
                    mundo.portal.terminar(j["id"])
        t0 = time.monotonic()
        mortes += await D.ciclo(worker, proc)
        duracoes.append(time.monotonic() - t0)
    return max(duracoes or [0.0]), mortes


# ═════════════════════════════════════════════════════════════════════════════
# G6.1 — o loop fica livre durante a operação inteira
# ═════════════════════════════════════════════════════════════════════════════
def test_g6_1_o_loop_fica_livre_durante_portal_operation(mundo, corretoras):
    X, _Y = corretoras

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)
        rid = _criar(mundo, X, rotulo="g6-1")
        async with D.MedidorDoLaco() as medidor:
            t0 = time.monotonic()
            mortes = await D.ciclo(wa, a)
            primeiro = time.monotonic() - t0
            maior, mais = await _girar_medindo(mundo, wa, a, rid)
        return rid, medidor.maior_atraso_s, max(primeiro, maior), mortes + mais

    rid, atraso, maior_ciclo, mortes = asyncio.run(cenario())
    assert not mortes
    assert mundo.banco.run(rid)["status"] == "completed"
    assert atraso < LIMITE_S, f"o event loop ficou PRESO {atraso:.2f}s durante portal.operation"
    assert maior_ciclo < LIMITE_S, f"um ciclo levou {maior_ciclo:.2f}s: alguma etapa ESPEROU o portal"


# ═════════════════════════════════════════════════════════════════════════════
# G6.2 — a retomada que reencontra o job (o C3)
# ═════════════════════════════════════════════════════════════════════════════
def test_g6_2_retomada_no_ja_existe_nao_espera(mundo, corretoras):
    X, _Y = corretoras

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)

        def morre_depois_do_insert(escrita):
            if escrita.dono == a.nome and not a.morto:
                a.morrer()
                raise D.MorteDoProcesso("worker-A morreu logo depois de criar o portal_job")

        mundo.banco.ao_gravar("portal_jobs", "insert", morre_depois_do_insert)
        rid = _criar(mundo, X, rotulo="g6-2")
        await D.ciclo(wa, a)
        assert a.morto
        job_de_a = [j["id"] for j in _jobs(mundo, rid)]
        b = mundo.processo("worker-B")
        wb = await D.ligar_worker(b, SW)
        async with D.MedidorDoLaco() as medidor:
            # o portal NÃO termina: a retomada de B tem de DORMIR, não esperar o job
            maior, _m = await _girar_medindo(mundo, wb, b, rid, passos=4, terminar=False)
        return rid, job_de_a, medidor.maior_atraso_s, maior

    rid, job_de_a, atraso, maior_ciclo = asyncio.run(cenario())
    assert [j["id"] for j in _jobs(mundo, rid)] == job_de_a, "a retomada criou OUTRO job"
    assert ((_passo(mundo, rid, PASSO_CRIAR) or {}).get("output_summary") or {}).get("portal_job_id") \
        == job_de_a[0]
    assert mundo.banco.run(rid)["status"] == "waiting_input", "B devia ter dormido sobre o job de A"
    assert atraso < LIMITE_S, f"o event loop ficou PRESO {atraso:.2f}s na retomada"
    assert maior_ciclo < LIMITE_S, (f"um ciclo de B levou {maior_ciclo:.2f}s: o ramo 'já existe' "
                                    "esperou o portal em vez de devolver o handle")


# ═════════════════════════════════════════════════════════════════════════════
# G6.3 / G6.4 — o gateway, direto
# ═════════════════════════════════════════════════════════════════════════════
def _req(cid, *, chave="wr:run-g6:op", modo=C.ESPERA_ENFILEIRAR, run="run-g6"):
    return C.PortalExecutionRequest(company_id=cid, operation_key=OP, insurer_key=SEGURADORA,
                                    business_input={"competencia": "2026-10"}, work_run_id=run,
                                    origem_confiavel=True, idempotency_key=chave, wait_mode=modo)


@pytest.mark.parametrize("modo,deve_esperar", [(C.ESPERA_ENFILEIRAR, False), (C.ESPERA_AGUARDAR, True)])
def test_g6_3_ja_existe_com_enfileirar_devolve_o_handle_sem_esperar(mundo, corretoras, modo, deve_esperar):
    """O par é o CONTROLE: a mesma chamada em AGUARDAR espera — prova que o contador consegue subir."""
    X, _Y = corretoras
    db = mundo.processo("api").db
    esperas: list = []
    t = {"s": 0.0}

    def dormir(s):
        esperas.append(s)
        t["s"] += s

    primeiro = G.PortalExecutionGateway(db).executar(_req(X))
    assert primeiro.portal_job_id, primeiro
    gw = G.PortalExecutionGateway(db, agora=lambda: t["s"], dormir=dormir)
    de_novo = gw.executar(_req(X, modo=modo))
    assert de_novo.portal_job_id == primeiro.portal_job_id, "a mesma chave tem de reencontrar o MESMO job"
    assert len([j for j in mundo.banco.linhas("portal_jobs") if j["company_id"] == X]) == 1
    if deve_esperar:
        assert esperas, "CONTROLE: em AGUARDAR o ramo 'já existe' espera — senão o guarda não guarda nada"
    else:
        assert not esperas, f"🔴 o ramo 'já existe' ESPEROU {sum(esperas):g}s com wait_mode=ENFILEIRAR"
        assert not de_novo.pode_repetir and "ja existia" in de_novo.motivo


def test_g6_4_a_chave_do_chamador_vale_em_leitura(mundo, corretoras):
    from portal_worker.journeys import journey_para_operacao

    X, _Y = corretoras
    gw = G.PortalExecutionGateway(mundo.processo("api").db)
    leitura = journey_para_operacao("hdi_corretor", OP)
    assert not C.precisa_de_idempotencia(leitura.effect_class), "a operação do teste devia ser LEITURA"
    assert gw.chave_de_idempotencia(_req(X, chave="wr:abc:op"), leitura) == "wr:abc:op"
    assert gw.chave_de_idempotencia(_req(X, chave=None), leitura) is None, \
        "CONTROLE: leitura SEM chave do chamador continua sem chave (não se deriva)"


# ═════════════════════════════════════════════════════════════════════════════
# G6.5 — `portal.operation` sempre enfileira, fora do event loop
# ═════════════════════════════════════════════════════════════════════════════
def test_g6_5_portal_operation_sempre_enfileira_e_fora_do_loop(mundo, corretoras, monkeypatch):
    X, _Y = corretoras
    chamadas: list = []
    original = G.PortalExecutionGateway.executar

    def espiao(self, req):
        chamadas.append((req.wait_mode, req.idempotency_key, threading.current_thread() is threading.main_thread()))
        return original(self, req)

    monkeypatch.setattr(G.PortalExecutionGateway, "executar", espiao)

    async def cenario():
        a = mundo.processo("worker-A")
        wa = await D.ligar_worker(a, SW)
        rid = _criar(mundo, X, rotulo="g6-5")
        run = mundo.banco.run(rid)
        run["input_payload"] = {**run["input_payload"], "wait_mode": C.ESPERA_AGUARDAR}  # a tentação
        await D.ciclo(wa, a)
        return rid

    rid = asyncio.run(cenario())
    assert len(chamadas) == 1, chamadas
    modo, chave, na_thread_principal = chamadas[0]
    assert modo == C.ESPERA_ENFILEIRAR, f"o payload pediu `await` e o workflow obedeceu: {modo}"
    assert chave == f"wr:{rid}:{OP}", chave
    assert not na_thread_principal, "o gateway rodou NA thread do event loop (sem `asyncio.to_thread`)"
    assert mundo.banco.run(rid)["status"] == "waiting_input"


# ═════════════════════════════════════════════════════════════════════════════
# G6.6 — nenhum `time.sleep` alcançável
# ═════════════════════════════════════════════════════════════════════════════
def test_g6_6_nenhum_time_sleep_alcancavel_dos_workflows():
    trabalho = RAIZ / "app" / "services" / "work"
    achados = [f"{p.name}:{i}" for p in trabalho.glob("*.py")
               for i, linha in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
               if re.search(r"\btime\.sleep\b", linha) and not linha.lstrip().startswith("#")]
    assert not achados, f"`time.sleep` no Work OS: {achados}"
    fonte = (RAIZ / "app" / "services" / "portals" / "gateway.py").read_text(encoding="utf-8")
    usos = [linha.strip() for linha in fonte.splitlines()
            if re.search(r"\btime\.sleep\b", linha) and not linha.lstrip().startswith("#")]
    assert usos == ["self._dormir = dormir or time.sleep"], (
        f"o gateway ganhou outro `time.sleep` além do padrão do modo `await`: {usos}")
