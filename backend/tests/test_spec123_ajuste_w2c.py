# -*- coding: utf-8 -*-
"""SPEC-123 · ajuste W2c (gerente) — a tela que vai ao DESTRAVADOR no PONTO A guarda a quebra de linha.

📊 O builder do W2b mediu: `_tela_do_turno` achata cada mensagem num texto só, e aí `opcoes_numeradas`
não acha opção nenhuma → a pergunta ao segurado saía sem as opções e a resposta dele não virava tecla.
O cérebro de HOJE continua com a forma achatada (controle byte a byte).
"""
from app.services import dispatch_router as R
from app.services import insurer_dispatch_service as IDS

_MENU = ("Agora, preciso que selecione abaixo a opção que corresponde com o seu problema:\n"
         "1 - Falta de energia\n2 - Problema elétrico\n3 - Outro")


def _sessao():
    return {"pending_insurer_messages": ["Olá!  Tudo   bem?", _MENU]}


def test_o_destravador_recebe_a_tela_com_as_linhas_e_ve_as_opcoes():
    tela = R._tela_do_turno(_sessao(), "", preservar_linhas=True)
    assert "\n1 - Falta de energia\n" in tela
    assert [l for _, l in IDS.opcoes_numeradas(tela)][:3] == ["Falta de energia", "Problema elétrico", "Outro"]


def test_controle_o_cerebro_de_hoje_continua_com_a_tela_achatada_byte_a_byte():
    hoje = R._tela_do_turno(_sessao(), "")
    assert hoje == "Olá! Tudo bem?\n" + " ".join(_MENU.split())
    # a linha de controle consegue ser diferente (§9.3): achatada, o parser não acha as três opções
    assert len(IDS.opcoes_numeradas(hoje)) < 3 or hoje != R._tela_do_turno(_sessao(), "", preservar_linhas=True)
