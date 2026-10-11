# -*- coding: utf-8 -*-
"""SPEC-131-0 parte A — conserto da confirmação: a RETOMADA de um cálculo no Agger de uma PESSOA nunca fica presa.

O defeito (📊 reprodução do laudo, 8 voltas do motor real: `('calculando', 2, 'pausado', '')` em todas): o login no Agger
de uma pessoa sem desfecho PAUSA a conta, mas só encerrava cálculos que não estavam `calculando`. Na retomada TODOS estão
`calculando` → nenhum encerrado; a retomada exige a conta da pessoa (pausada) → `_escolher` devolve None → o grupo é
pulado antes de `tentativas` subir → o cálculo fica `calculando` para sempre, sem erro, e o pedido nunca fecha.

O que cada teste guarda (o MOTOR real, `uma_volta`, sobre o dublê de borda do `test_spec129b_o_motor`):
    (1) login sem desfecho na retomada → `falhou` com MOTIVO_PESSOA_SEM_RESPOSTA, o pedido fecha, nunca a conta global
    (2) senha recusada na retomada (caso irmão pré-existente) → `falhou` com MOTIVO_SENHA_DA_PESSOA, pedido fecha
    (3) defesa: a conta exigida já está pausada/bloqueada quando a retomada chega → `falhou` com motivo, nunca pulado
    controle: a conta exigida só está ocupada por outro motor (lease viva) → o cálculo ESPERA (não falha à toa)
Nenhum nome de corretora nem de pessoa (CLAUDE.md §13.9). Nenhuma senha real.
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

_TESTS = Path(__file__).resolve().parent
if str(_TESTS) not in sys.path:
    sys.path.insert(0, str(_TESTS))

import test_spec129b_o_motor as TM  # noqa: E402
from test_spec129b_o_motor import ambiente  # noqa: E402,F401  (fixture)
import test_spec1310_f3_contas as F3  # noqa: E402
from portal_worker.multicalculo import motor as MOT  # noqa: E402


class _SessaoIndefinida(Exception):
    pass


def _mod():
    return SimpleNamespace(SessaoOcupada=TM.SessaoOcupada, CredencialRecusada=TM.CredencialRecusada,
                           SessaoIndefinida=_SessaoIndefinida)


def _calc(amb, cid):
    return next(x for x in amb.banco.linhas("multicalculo_calculos") if x["id"] == cid)


def _pedido_do(amb, cid):
    pid = _calc(amb, cid)["pedido_id"]
    return next(p for p in amb.banco.linhas("multicalculo_pedidos") if p["id"] == pid)


def _voltas(amb, n=4):
    hist = []
    for vez in range(n):
        m = TM.motor(amb, f"m{vez}")
        m._sessao_mod = _mod()
        TM.rodar(m.uma_volta())
        TM.rodar(m.desligar())
        amb.relogio.avancar(16 * 60)
        hist.append(vez)
    return hist


def _cenario(amb, *, estado="ativo"):
    a = TM.empresa(amb)
    g = F3.conta_global(amb, a)
    ma = F3.membro(amb, a)
    pa = F3.conta_da_pessoa(amb, a, ma, estado=estado, batida_antiga=False)
    cid = F3._calculando_no(amb, a, pa, exigida=True)
    return a, g, pa, cid


def test_1_retomada_com_login_sem_desfecho_no_agger_da_pessoa_falha_com_o_motivo(ambiente):
    amb = ambiente
    _a, g, pa, cid = _cenario(amb)
    amb.mundo.login[pa] = _SessaoIndefinida

    _voltas(amb)
    c = _calc(amb, cid)
    assert c["status"] == "falhou", ("o cálculo ficou preso na retomada", c["status"], c.get("tentativas"))
    assert (c.get("erro") or "").startswith("agger_da_pessoa_sem_resposta"), c.get("erro")
    assert TM.conta(amb, pa)["robo_estado"] == "pausado"
    assert g not in F3.obtidas(amb), "a retomada caiu no Agger da corretora"
    assert len([x for x in amb.mundo.obter if x[1] == pa]) == 1, "insistiu no login da pessoa"
    assert _pedido_do(amb, cid)["status"] not in ("na_fila", "calculando"), "o pedido nunca fechou"


def test_2_retomada_com_senha_recusada_no_agger_da_pessoa_falha_com_o_motivo(ambiente):
    amb = ambiente
    _a, g, pa, cid = _cenario(amb)
    amb.mundo.login[pa] = TM.CredencialRecusada

    _voltas(amb)
    c = _calc(amb, cid)
    assert c["status"] == "falhou", ("o cálculo ficou preso na retomada", c["status"], c.get("tentativas"))
    assert c.get("erro") == MOT.erro_curto(MOT.MOTIVO_SENHA_DA_PESSOA), c.get("erro")
    assert TM.conta(amb, pa)["robo_estado"] == "bloqueado"
    assert g not in F3.obtidas(amb), "a retomada caiu no Agger da corretora"
    assert _pedido_do(amb, cid)["status"] not in ("na_fila", "calculando"), "o pedido nunca fechou"


@pytest.mark.parametrize("estado", ["pausado", "bloqueado"])
def test_3_defesa_a_conta_exigida_ja_inelegivel_o_calculo_falha_em_vez_de_esperar_para_sempre(ambiente, estado):
    amb = ambiente
    _a, g, pa, cid = _cenario(amb, estado=estado)

    _voltas(amb)
    c = _calc(amb, cid)
    assert c["status"] == "falhou", ("o cálculo ficou preso na retomada", c["status"], c.get("tentativas"))
    assert (c.get("erro") or "").startswith("agger_da_pessoa_indisponivel"), c.get("erro")
    assert F3.obtidas(amb) == set(), "abriu sessão numa conta pausada/bloqueada ou na da corretora"
    assert _pedido_do(amb, cid)["status"] not in ("na_fila", "calculando"), "o pedido nunca fechou"


def test_3_controle_conta_exigida_so_ocupada_por_outro_motor_o_calculo_espera(ambiente):
    """Linha de CONTROLE da defesa: a conta está ATIVA e a lease é de outro motor vivo — esperar é o certo."""
    amb = ambiente
    _a, _g, pa, cid = _cenario(amb)
    TM.conta(amb, pa).update(robo_dono="outro-motor-vivo", robo_batida_em=TM.T0.isoformat())

    m = TM.motor(amb, "m0")
    m._sessao_mod = _mod()
    TM.rodar(m.uma_volta())
    TM.rodar(m.desligar())
    c = _calc(amb, cid)
    assert c["status"] == "calculando" and not c.get("erro"), (c["status"], c.get("erro"))
    assert F3.obtidas(amb) == set()
