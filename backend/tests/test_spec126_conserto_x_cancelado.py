# -*- coding: utf-8 -*-
r"""SPEC-126 · CONSERTO X · RT-B1 — "cancelado" dito pelo MODELO, sem ferramenta, em qualquer forma.

📊 Sonda do red team (`rt126_probe1.py` §3, HEAD f44526c, 02/10/2026): `guardar_a_verdade_do_handoff(r, [])`
deixava INTACTAS "Pronto, cancelado!", "Cancelado ✅", "Feito, guincho cancelado.", "Pedido cancelado com
sucesso.", "Consegui cancelar o guincho.", "Desmarquei o guincho.", "O cancelamento já foi solicitado à
seguradora." — o fiscal só via `cancelei`, `está/foi cancelado` e `cancelamento feito`. O segurado lia
"Pronto, cancelado!" e o prestador seguia a caminho (D4/T5: nenhuma ferramenta cancela).

O conserto lê a FORMA, não uma lista: o particípio (`cancelado/desmarcado/dispensado`) afirmado — fora de
negação, de pergunta, de modal ("vai ser", "para ficar") e de intenção ("você quer") —, o feito em 1ª pessoa
(`consegui cancelar`, `desmarquei`, `dispensei`) e o cancelamento PEDIDO à seguradora.

Pelo MOTOR: `guardar_a_verdade_do_handoff` é a função que `nodes.py` aplica a toda resposta final.
🔴 Mutação (rodada uma vez, por cópia): voltar `afirma_cancelamento` à regex da U4 → os casos do RT vermelhos.
"""
from __future__ import annotations

import pytest
from langchain_core.messages import ToolMessage

from app.agents import honestidade_do_handoff as H


@pytest.mark.parametrize("frase", [
    "Pronto, cancelado!",
    "Cancelado ✅",
    "Feito, guincho cancelado.",
    "Pedido cancelado com sucesso.",
    "Prontinho! Guincho CANCELADO.",
    "Consegui cancelar o guincho.",
    "Desmarquei o guincho.",
    "O cancelamento já foi solicitado à seguradora.",
    "Já pedi pra seguradora cancelar.",
    "Tudo certo, o guincho foi dispensado.",
    "Cancelado o pedido, fica tranquilo.",
    "Solicitei o cancelamento do guincho.",
    "Não se preocupe, está cancelado.",
    "Dispensei o reboque, tudo certo.",
])
def test_rt_b1_o_fiscal_reescreve_o_cancelado_em_toda_forma(frase):
    saida = H.guardar_a_verdade_do_handoff(frase, [])
    assert saida != frase, "VAZOU ao segurado: %r" % frase
    assert H.afirma_cancelamento(saida) is False, saida          # a nota não se auto-reescreve
    assert "não está cancelado" in saida.lower()


@pytest.mark.parametrize("frase", [
    "Não está cancelado ainda.",
    "O guincho ainda não foi cancelado.",
    "Para cancelar, vou chamar a pessoa da corretora.",
    "Você quer cancelar?",
    "O cancelamento é feito pela corretora.",
    "O guincho está cancelado?",
    "Você quer o guincho cancelado?",
    "Entendi, você quer o guincho cancelado.",
    "Para ficar cancelado, a pessoa da corretora precisa confirmar com a seguradora.",
    "O pedido só vai ser cancelado quando a equipe confirmar.",
    "Sua apólice consta como cancelada desde março.",       # status do sistema, não ação do agente
    "Quer que eu peça o cancelamento à equipe?",
    H.NOTA_DO_CANCELAMENTO_SEM_FERRAMENTA,
])
def test_rt_b1_controle_o_fiscal_nao_toca_negacao_pergunta_intencao_ou_regra(frase):
    assert H.guardar_a_verdade_do_handoff(frase, []) == frase


def test_rt_b1_a_passagem_confirmada_fica_e_so_o_cancelado_sai():
    ok = ToolMessage(content=H.SUCESSO_DO_HANDOFF, tool_call_id="c1", name="request_human_agent")
    frase = "Já passei seu caso para a equipe. Pronto, cancelado!"
    saida = H.guardar_a_verdade_do_handoff(frase, [ok])
    assert saida.startswith("Já passei seu caso para a equipe.")
    assert "Pronto, cancelado" not in saida and "não está cancelado" in saida.lower()
