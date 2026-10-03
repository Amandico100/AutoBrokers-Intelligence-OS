# -*- coding: utf-8 -*-
r"""SPEC-126 · CONSERTO X · Juiz-B2 + RT-B4 — o parente/motorista que NÃO diz "dele/dela" é terceiro (D1).

📊 Sondas (HEAD f44526c, 02/10/2026): `de_quem_e_a_apolice(cpf, falas)` → `terceiro=False` (= titular, a
apólice INTEIRA ao modelo) para "o carro do meu pai quebrou" + CPF solto (`juiz126/j_d1.py`), "sou o
motorista", "sou o genro, … pro carro do meu sogro", "sou a nora", "sou o caseiro", "sou a diarista", e
"na verdade o carro é do meu sogro" dito DEPOIS do CPF (`rt126_probe1.py` §4).

A REGRA: terceiro detectado → o CPF que ELE mandou é o do TITULAR. Pedido de SERVIÇO → autorizado a acionar,
sem dado; pedido de DADO (prêmio, vigência, apólice) → negado.
Controles: "meu filho vai acompanhar" (o titular falando), "o carro é meu, minha esposa usa", "sou eu, o dono",
"sou motorista de aplicativo" (profissão do próprio titular), "o carro do meu pai, mas o seguro é meu",
"o carro do vizinho bateu no meu" (colisão, não posse).

Pelo MOTOR (CLAUDE.md §9.4): `nodes.tool_node` REAL → `InfocapPolicyLookupTool._arun` → o que o MODELO lê.
🔴 Mutação (uma vez, por cópia): voltar os sinais novos → os casos do juiz/RT vermelhos.
"""
from __future__ import annotations

import os
import sys

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

from test_spec126_u3_d1_parente_aciona import (  # noqa: E402,F401
    CPF_DO_PAI, _com_conversa, borda, consultar_pelo_motor, dados_no, o_que_o_modelo_le)

from app.agents.tools import infocap_tool as T  # noqa: E402

DOC = CPF_DO_PAI


# =========================================================================== #
# PELO MOTOR — o que o modelo lê
# =========================================================================== #
def test_fio_o_carro_do_meu_pai_quebrou_cpf_solto_e_pergunta_o_premio_e_negado(borda):
    saida = consultar_pelo_motor(["o carro do meu pai quebrou", DOC, "qual o prêmio?"], DOC)
    le = o_que_o_modelo_le(saida)
    assert le == T.TEXTO_DA_APOLICE_DE_TERCEIRO, le
    assert dados_no(le) == [] and not saida.get("infocap_policy_context")


def test_fio_o_carro_do_meu_pai_quebrou_cpf_solto_e_pede_guincho_aciona_sem_dado(borda):
    banco, prov = borda
    _com_conversa(banco)
    saida = consultar_pelo_motor(["o carro do meu pai quebrou", DOC, "preciso de guincho"], DOC)
    le = o_que_o_modelo_le(saida)
    assert prov.consultas
    assert le != T.TEXTO_DA_APOLICE_DE_TERCEIRO, le
    assert "pode acionar" in le.lower(), le
    assert dados_no(le) == [], dados_no(le)


def test_fio_controle_o_titular_com_cpf_solto_continua_recebendo_os_dados(borda):
    """§9.3: o mesmo caminho CONSEGUE entregar dado — o conserto não cegou o titular."""
    le = o_que_o_modelo_le(consultar_pelo_motor(["meu carro quebrou", DOC, "preciso de guincho"], DOC))
    assert dados_no(le), le


# =========================================================================== #
# A régua pura — terceiro / autorizado
# =========================================================================== #
@pytest.mark.parametrize("falas,autorizado", [
    (["o carro do meu pai quebrou, preciso de guincho", DOC], True),
    (["o carro do meu pai quebrou, preciso de guincho", DOC, "e qual a vigencia da apolice dele?"], False),
    (["preciso de guincho pro carro da minha esposa", DOC, "qual o premio do seguro dela?"], False),
    (["sou o motorista dele, o carro quebrou na estrada, preciso de guincho", DOC], True),
    (["sou o motorista, o carro quebrou, preciso de guincho", DOC], True),
    (["sou o motorista da empresa, o carro quebrou, preciso de guincho", DOC], True),
    (["sou o genro, preciso de guincho pro carro do meu sogro", DOC], True),
    (["sou a nora, o carro quebrou aqui, manda um guincho", DOC], True),
    (["sou genro do seu Jorge, ele ta no hospital, preciso de guincho", DOC], True),
    (["sou o sogro, preciso de um guincho", DOC], True),
    (["sou a cunhada, o carro nao liga, preciso de guincho", DOC], True),
    (["sou o caseiro, a casa do patrao ta sem luz, preciso de eletricista", DOC], True),
    (["sou a diarista, o cano estourou aqui na casa, preciso de encanador", DOC], True),
    (["sou o funcionario, o carro quebrou, preciso de guincho", DOC], True),
    (["o carro da minha esposa quebrou", DOC, "manda um guincho"], True),
    (["o carro do meu sogro quebrou na estrada", DOC], False),            # sem pedido de serviço ainda
    (["oi, preciso de guincho", DOC, "na verdade o carro e do meu sogro"], True),
    (["preciso de guincho, cpf " + DOC, "ah e o seguro e do meu pai, mas ele ta aqui"], True),
])
def test_o_terceiro_sem_dele_e_reconhecido(falas, autorizado):
    r = T.de_quem_e_a_apolice(DOC, falas)
    assert r["terceiro"] is True, (falas, r)
    assert r["autorizado"] is autorizado, (falas, r)
    assert r["proprio"] is False


@pytest.mark.parametrize("falas", [
    ["meu filho vai acompanhar o guincho, preciso de guincho", DOC],
    ["preciso de guincho", DOC, "meu filho vai acompanhar, o nome dele e Pedro"],
    ["o carro é meu, minha esposa usa, preciso de guincho", DOC],
    ["sou eu, o dono, preciso de guincho", DOC],
    ["sou motorista de aplicativo, meu carro quebrou, preciso de guincho", DOC],
    ["sou motorista, meu carro quebrou", DOC],
    ["o carro do meu pai quebrou, mas o seguro é meu, preciso de guincho", DOC],
    ["o carro do meu vizinho bateu no meu, preciso de guincho", DOC],
    ["estou na casa da minha mãe, meu carro quebrou, preciso de guincho", DOC],   # lugar, não posse
    # 📊 acervo (02/10, lente das regras novas em 15.773 falas): colisão contada pelo titular, lugar, URA
    ["ao dar re, nao vi o carro do meu colega estacionado do lado, preciso abrir sinistro", DOC],
    ["meu carro estava estacionado em frente a casa do meu irmao e bateram nele", DOC],
    ["ola! sou a assistente virtual da seguradora", DOC],
    ["preciso de guincho", DOC],
    ["meu cpf é " + DOC, "na verdade o carro e do meu sogro"],              # "meu cpf" vence
])
def test_controle_o_titular_nao_vira_terceiro(falas):
    assert T.de_quem_e_a_apolice(DOC, falas)["terceiro"] is False, falas
