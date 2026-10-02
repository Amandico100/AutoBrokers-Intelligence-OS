# -*- coding: utf-8 -*-
"""SPEC-125 · juiz final — os dois BLOCKERs do laudo, pelo motor, com controles.

B1 · o "pode" depois de negação/dúvida/pergunta virava o SIM do acionamento (T8).
B2 · a fala dita junto de uma ferramenta que NÃO fez (segunda chance do handoff,
     `confirm_first`) ia ao segurado prometendo o que não houve.
"""
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agents.honestidade_do_handoff import guardar_a_verdade_do_handoff
from app.agents.nodes import com_o_que_foi_dito_antes_da_ferramenta
from app.agents.tools.human_handoff import SEGUNDA_CHANCE_DO_HANDOFF
from app.agents.tools.insurer_dispatch_tool import (confirmacao_comprovada,
                                                     pedido_de_confirmacao)

P = "Confirma: guincho da Rua Sete 100 para a Oficina do Zé? Posso acionar?"
PEDIDO = {"local_atual": "Rua Sete 100", "local_destino": "Oficina do Ze",
          "veiculo_placa": "ABC1D23"}


def _ok(resposta):
    return confirmacao_comprovada([("agente", P), ("segurado", resposta)], PEDIDO)["comprovada"]


def test_b1_pode_negado_ou_perguntado_nao_aciona():
    for fala in ("a seguradora disse que não pode acionar", "não sei se pode acionar",
                 "não sei quem pode acionar", "você não pode acionar", "ninguém pode acionar",
                 "quem pode acionar?", "pergunta pro meu marido se pode acionar",
                 "só meu marido pode acionar", "será que pode acionar?"):
        assert _ok(fala) is False, fala


def test_b1_controle_o_ok_legitimo_continua_valendo():
    for fala in ("sou eu que tô com o carro pode acionar", "pode mandar", "pode acionar",
                 "Ninguém se machucou, pode acionar", "Não, ninguém se machucou. Pode mandar",
                 "ok pode seguir", "sim", "Já disse que pode"):
        assert _ok(fala) is True, fala


def _turno(pre, nome, resultado, final):
    msgs = [HumanMessage(content="cadê o guincho??"),
            AIMessage(content=pre, tool_calls=[{"id": "c1", "name": nome, "args": {}}]),
            ToolMessage(content=resultado, tool_call_id="c1", name=nome)]
    junto = com_o_que_foi_dito_antes_da_ferramenta(final, msgs)
    return guardar_a_verdade_do_handoff(junto, msgs)


def test_b2_promessa_dita_junto_da_segunda_chance_nao_sai():
    saida = _turno("Vou pedir para a nossa equipe seguir daqui e te retornar.",
                   "request_human_agent", SEGUNDA_CHANCE_DO_HANDOFF,
                   "O guincho foi acionado às 14h. Quer que eu cobre a seguradora?")
    assert saida == "O guincho foi acionado às 14h. Quer que eu cobre a seguradora?"


def test_b2_ja_acionei_junto_do_confirm_first_nao_apaga_a_pergunta():
    final = "Antes de acionar, me confirma: guincho da Rua Sete 100 para a Oficina do Zé?"
    saida = _turno("Pronto, já acionei o guincho ✅", "insurer_dispatch",
                   str(pedido_de_confirmacao("sem sim")), final)
    assert saida == final


def test_b2_controle_a_orientacao_com_handoff_feito_continua_saindo():
    saida = _turno("Saia de casa agora e ligue 193.", "request_human_agent",
                   "HANDOFF_OK · a equipe FOI avisada e recebeu o resumo do caso.",
                   "Nossa equipe já está com o seu caso.")
    assert saida.startswith("Saia de casa agora e ligue 193.")
