# -*- coding: utf-8 -*-
"""SPEC-126 · CONSERTO 5 — os dois blockers do juiz de escalação (BE-1, BE-2), como guardas.

As sondas do juiz (`escal126/compara.py`, `escal126/test_escal126_d4.py`, fora da árvore) entram aqui
como guardas determinísticos. Nenhuma frase é real; nenhum dado de pessoa.

BE-1 · `pos_acionamento._CANCELAR_SEM_O_VERBO` — a pontuação colada ao verbo ("esquece... o guincho",
       "dispensa! o guincho") tirava o cancelamento do K3 → a segunda chance, prestador na rua (D4).
       Pelo MOTOR do handoff (caso acionado, escritor real da ficha): PESSOA e UM aviso ao grupo.
BE-2 · `honestidade_do_handoff._participio_afirmado` — o fato de terceiro olhava QUEM cancelou, não O
       QUÊ: "O guincho foi cancelado pela seguradora" passava intacta sem ferramenta nenhuma.

🔴 Mutação (rodada uma vez, por CÓPIA, e restaurada por cópia):
   M1 tirar o ramo `_PONTUACAO_E_O_SERVICO` de `_CANCELAR_SEM_O_VERBO` → BE-1 (K3 e motor) vermelhos.
   M2 `_sujeito_e_o_servico` devolve sempre False → BE-2 (o serviço sem ferramenta) vermelhos.
   M3 `_resposta_abre_anunciando` devolve sempre False → o "Feito!/Tudo bem." da resposta vermelhos.
   M4 `_status_de_cancelado_na_tool` devolve sempre False → "com o status da ferramenta" vermelhos.
   M5 a frase que é só o anúncio ("Feito!") não sai → "o anúncio sai com a afirmação" vermelho.
   📊 03/10 (`scratchpad/conserto5/c5_mutacao.py`): HEAD 14eb941 43 falhas · M1 17 · M2 19 · M3 2 ·
   M4 10 · M5 1; restaurado por cópia com o hash igual.
"""
import os
import sys

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

from app.agents import honestidade_do_handoff as H  # noqa: E402
from app.atendimento.pos_acionamento import classificar_turno  # noqa: E402
from test_spec123_atendimento_segunda_chance import ENVIOS, _pedir, borda  # noqa: E402,F401
from test_spec126_u4_cancelamento import _caso_acionado  # noqa: E402

NOTA = H.NOTA_DO_CANCELAMENTO_SEM_FERRAMENTA


# ===========================================================================
# BE-1 · a pontuação colada ao verbo não muda o objeto
# ===========================================================================
#: 📊 `escal126/compara.py` (03/10): K3 em 44e0f1a, `N` em 14eb941.
CANCELA_COM_PONTUACAO = [
    "esquece... o guincho", "esquece. o guincho", "esquece, o guincho", "esquece: o guincho",
    "deixa pra lá... o guincho já pode ir", "dispensa! o guincho", "esquece… o guincho",
    "esquece!! seu guincho",
]
#: os controles de que o conserto 2 não volta atrás (pend. 4) e de que o "manda" desfaz.
NAO_E_CANCELAR = [
    "esquece a placa que mandei, o guincho é pro outro carro",
    "esquece a placa…, o guincho é pro outro carro",
    "deixa pra lá, cadê o guincho?",
    "esquece, manda o guincho",
    "nao se esqueça, o guincho chega 18h",
    "não precisa, o guincho",
]
#: a linha de CONTROLE: o que já era K3 continua (prova que o guarda distingue).
JA_ERA_K3 = ["esquece o guincho", "esquece - o guincho", "esquece, achei a chave"]


@pytest.mark.parametrize("fala", CANCELA_COM_PONTUACAO)
def test_be1_pontuacao_colada_ao_verbo_continua_k3(fala):
    assert classificar_turno([fala]) == "K3", fala


@pytest.mark.parametrize("fala", NAO_E_CANCELAR)
def test_be1_controle_a_oracao_seguinte_nao_e_o_objeto(fala):
    assert classificar_turno([fala]) != "K3", fala


@pytest.mark.parametrize("fala", JA_ERA_K3)
def test_be1_controle_o_que_ja_era_k3(fala):
    assert classificar_turno([fala]) == "K3", fala


#: o MOTOR (§9.4): `HumanHandoffTool._arun` real, caso acionado, com o motivo em prosa que um modelo
#: escreve. 📊 sonda do juiz: as 5 com pontuação davam SEGUNDA_CHANCE, aviso_ao_grupo=0 (10 de 10).
FALAS_DO_MOTOR = ["esquece o guincho", "esquece... o guincho", "esquece: o guincho",
                  "deixa pra lá... o guincho já pode ir", "dispensa! o guincho", "esquece, o guincho"]
MOTIVOS = ["o segurado pediu para cancelar o guincho", "segurado não quer mais o serviço"]


@pytest.mark.parametrize("motivo", MOTIVOS)
@pytest.mark.parametrize("fala", FALAS_DO_MOTOR)
def test_be1_pelo_motor_vai_a_pessoa_com_um_aviso(borda, fala, motivo):
    import app.agents.tools.human_handoff as HH

    cid = "c-c5-%d-%d" % (FALAS_DO_MOTOR.index(fala), MOTIVOS.index(motivo))
    b = _caso_acionado(cid, fala)
    antes = len(ENVIOS)
    r = _pedir(HH, b, cid, motivo)
    assert not HH.foi_segunda_chance(r), (fala, r)          # D4: NUNCA a segunda chance
    assert r == H.SUCESSO_DO_HANDOFF, (fala, r)
    assert len(ENVIOS) - antes == 1, (fala, len(ENVIOS) - antes)


# ===========================================================================
# BE-2 · o fato de terceiro não vale para o serviço DESTE acionamento sem ferramenta
# ===========================================================================
#: 📊 `escal126/compara.py` (03/10): REESCRITAS em 44e0f1a, INTACTAS em 14eb941 (9 de 9) + 3 formas
#: vizinhas (a vírgula que corta a oração, o "pedido" sozinho, o "Feito!" com a agenda).
SERVICO_SEM_FERRAMENTA = [
    "O guincho foi cancelado pela seguradora.",
    "Entrei em contato e o guincho foi cancelado pela seguradora.",
    "Seu pedido de guincho foi cancelado pela central, conforme você pediu.",
    "Feito! O guincho foi cancelado pela seguradora.",
    "Tudo bem. O guincho foi cancelado pela seguradora.",
    "Seu guincho foi cancelado pelo sistema.",
    "Seu guincho consta como cancelado.",
    "O guincho anterior foi cancelado.",
    "Seu chaveiro foi dispensado pela assistência.",
    "O guincho, infelizmente, foi cancelado pela seguradora.",
    "Seu pedido foi cancelado pela seguradora.",
    "Feito! O agendamento da vistoria foi cancelado pela seguradora.",
]
#: os controles que ficam INTACTOS (o objetivo do conserto 2 não volta atrás).
FATO_DE_TERCEIRO = [
    "O sinistro foi cancelado pela seguradora.",
    "O agendamento da vistoria foi cancelado pela seguradora.",
    "O prestador anterior foi dispensado.",
    "O prestador anterior foi dispensado e um novo está a caminho.",
    "Sua apólice consta como cancelada.",
    "Para cancelar, chamo a pessoa da corretora.",
    "Certo, vou verificar. O sinistro foi cancelado pela seguradora.",
    "O sinistro foi cancelado pela seguradora, e o guincho segue a caminho.",
]


class _ToolMsg:
    def __init__(self, name, content):
        self.name, self.content = name, content


#: 📊 `portal_params.py:1720` — o status que uma ferramenta de verdade devolve.
STATUS_DA_TOOL = [_ToolMsg("portal", "A seguradora mostra este atendimento como cancelado, então eu não "
                                     "consigo seguir por aqui.")]
#: o aviso do MODO TESTE do acionamento ("será cancelado") é futuro, não status.
AVISO_DO_MODO_TESTE = [_ToolMsg("insurer_dispatch", "este acionamento é um teste e será cancelado no final.")]


@pytest.mark.parametrize("texto", SERVICO_SEM_FERRAMENTA)
def test_be2_o_servico_cancelado_sem_ferramenta_e_reescrito(texto):
    saida = H.guardar_a_verdade_do_handoff(texto, [])
    assert saida != texto
    assert NOTA in saida
    assert H.afirma_cancelamento(saida) is False, saida       # a nota não se auto-reescreve


@pytest.mark.parametrize("texto", SERVICO_SEM_FERRAMENTA)
def test_be2_o_aviso_do_modo_teste_nao_e_status(texto):
    assert H.guardar_a_verdade_do_handoff(texto, AVISO_DO_MODO_TESTE) != texto


@pytest.mark.parametrize("texto", [t for t in SERVICO_SEM_FERRAMENTA
                                   if not t.startswith(("Feito!", "Tudo bem."))])
def test_be2_com_o_status_da_ferramenta_do_turno_fica_intacto(texto):
    assert H.guardar_a_verdade_do_handoff(texto, STATUS_DA_TOOL) == texto


@pytest.mark.parametrize("texto", FATO_DE_TERCEIRO)
def test_be2_controle_o_fato_de_terceiro_fica_intacto(texto):
    assert H.guardar_a_verdade_do_handoff(texto, []) == texto


def test_be2_controle_o_feito_do_agente_continua_reescrito():
    assert H.guardar_a_verdade_do_handoff("Pronto, cancelado!", []) == NOTA


def test_be2_o_anuncio_sai_com_a_afirmacao_que_ele_anunciava():
    """"Feito! Ainda não está cancelado…" se contradiz: o "Feito!" sai junto."""
    assert H.guardar_a_verdade_do_handoff("Feito! O guincho foi cancelado pela seguradora.", []) == NOTA
    saida = H.guardar_a_verdade_do_handoff("Tudo bem. O guincho foi cancelado pela seguradora. "
                                           "Qualquer coisa me chama.", [])
    assert saida == "Qualquer coisa me chama. " + NOTA, saida


def test_be2_o_pedido_que_consta_como_cancelado_so_com_a_ferramenta():
    """§9.3 — a lição do conserto 2 MIGRA: "O pedido consta como cancelado no sistema da seguradora"
    é fato de terceiro QUANDO uma ferramenta do turno o trouxe; sem ela, não há como saber, e o
    lado seguro é reescrever (o "pedido" é o deste acionamento)."""
    texto = "O pedido consta como cancelado no sistema da seguradora."
    assert H.guardar_a_verdade_do_handoff(texto, STATUS_DA_TOOL) == texto
    assert H.guardar_a_verdade_do_handoff(texto, []) != texto
