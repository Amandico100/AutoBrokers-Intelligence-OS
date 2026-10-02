# -*- coding: utf-8 -*-
"""SPEC-126 U3-B — duas falas erradas ao segurado, pelo MOTOR.

1. 📊 U1 C11: à pergunta "falo com o titular do CPF final 4725?", "Sou eu sim" NÃO liberava
   o CPF que já estava na conversa (`quem_e_o_segurado._confirmou_agora` só lia "sim" no
   começo da fala) — e o agente pedia o CPF de novo. Motor: `quem_e_o_segurado.montar`.
2. 📊 T6 (bancada U1, Luna, 02/10/2026): num CHAVEIRO de carro o agente disse "o prestador
   pode pedir uma senha de acesso, que são os 4 últimos números do telefone informado" — a
   instrução da assistência RESIDENCIAL de uma seguradora, que o bloco do prompt juntava às
   de todos os corredores. Motor: `corridor_playbooks.conhecimento_de_assistencia`, chamado
   EXATAMENTE como `graph.py` o chama, e `insurer_dispatch_service.client_summary_from_capture`
   (a mensagem que sai ao segurado com o protocolo).
"""
from __future__ import annotations

import os

import pytest

from app.agents import quem_e_o_segurado as Q
from app.services import corridor_playbooks as CP

CPF = "52998224725"            # fictício, DV válido
SENHA = "4 últimos"            # o trecho das DUAS instruções de senha residencial


# =========================================================================== #
# 1 · "Sou eu sim" libera o CPF que já está na conversa
# =========================================================================== #
def _historico(resposta: str) -> list:
    """Assunto anterior (há 10 dias) com o CPF dito como dele; assunto atual com a pergunta
    do agente pelo FINAL e a resposta do segurado."""
    return [
        {"role": "user", "content": f"meu cpf é {CPF}", "created_at": "2026-09-20T10:00:00+00:00"},
        {"role": "assistant", "content": "Anotado.", "created_at": "2026-09-20T10:00:10+00:00"},
        {"role": "user", "content": "oi, preciso de um guincho", "created_at": "2026-10-02T10:00:00+00:00"},
        {"role": "assistant", "content": f"Falo com o titular do CPF final {CPF[-4:]}?",
         "created_at": "2026-10-02T10:00:05+00:00"},
        {"role": "user", "content": resposta, "created_at": "2026-10-02T10:00:20+00:00"},
    ]


@pytest.mark.parametrize("resposta", ["Sou eu sim", "sou eu", "Isso, sou eu", "eu mesmo",
                                      "Sim, sou eu!", "sou eu mesma", "sim"])
def test_a_confirmacao_libera_o_cpf_inteiro(resposta):
    quem = Q.montar(historico=_historico(resposta), n_dias=7)
    assert quem["cpf"] == CPF, (resposta, quem)
    assert CPF in Q.bloco_para_o_prompt(quem)


@pytest.mark.parametrize("resposta", ["não sou eu", "nao, sou a esposa dele",
                                      "sou eu que tô com o carro do meu pai",
                                      "sim, sou eu que tô com o carro do meu pai",
                                      "sou eu quem vai receber o guincho do meu pai"])
def test_o_que_nao_confirma_nao_libera(resposta):
    quem = Q.montar(historico=_historico(resposta), n_dias=7)
    assert quem["cpf"] == "", (resposta, quem)
    assert CPF not in Q.bloco_para_o_prompt(quem) and quem["cpf_final"] == CPF[-4:]


# =========================================================================== #
# 2 · A senha da assistência residencial não chega a quem pediu guincho
# =========================================================================== #
def _bloco_do_prompt(**escopo) -> str:
    """A chamada de `graph.py` (todos os corredores) — com ou sem o escopo do acionamento."""
    return CP.conhecimento_de_assistencia(sorted(CP._PLAYBOOKS), **escopo)


def _avise(bloco: str) -> str:
    i = bloco.find("AVISE TAMBÉM")
    return bloco[i:bloco.find("COMO TERMINA")] if i >= 0 else ""


def test_o_grafo_chama_o_gerador_sem_escopo():
    """A âncora do motor: o teste chama o gerador como o grafo chama (§9.4)."""
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fonte = open(os.path.join(raiz, "app", "agents", "graph.py"), encoding="utf-8").read()
    assert "conhecimento_de_assistencia(sorted(_PLAYBOOKS))" in fonte


def test_o_prompt_de_abertura_nao_ensina_a_senha_de_uma_seguradora_a_todas():
    avise = _avise(_bloco_do_prompt())
    assert avise, "CONTROLE: o bloco ainda tem o AVISE TAMBÉM (com o que vale para todos)"
    assert SENHA not in avise and "senha" not in avise.lower(), avise
    assert "18 anos" in avise, "a instrução que vale para TODO corredor continua"


@pytest.mark.parametrize("seguradora,servico", [("zurich", "guincho"), ("allianz", "chaveiro"),
                                                ("porto", "guincho"), ("yelum", "pneu")])
def test_guincho_auto_de_qualquer_seguradora_nao_ouve_a_senha(seguradora, servico):
    avise = _avise(_bloco_do_prompt(seguradora=seguradora, ramo="auto", servico=servico))
    assert avise and SENHA not in avise and "senha" not in avise.lower(), avise


@pytest.mark.parametrize("seguradora", ["allianz", "yelum"])
def test_controle_residencial_da_seguradora_dona_ouve_a_senha(seguradora):
    """§9.2 — a linha de CONTROLE: o MESMO gerador CONSEGUE entregar a senha."""
    avise = _avise(_bloco_do_prompt(seguradora=seguradora, ramo="residencial", servico="encanador"))
    assert SENHA in avise, avise
    assert "documento do veículo" not in avise, "a instrução do CARRO na casa"


def test_a_mensagem_do_protocolo_leva_a_senha_so_ao_corredor_dono():
    from app.services.insurer_dispatch_service import client_summary_from_capture

    def _msg(ref, sub):
        return client_summary_from_capture({"playbook_ref": ref, "subservice": sub,
                                            "captured": {"protocol": "PR-1"}}) or ""

    assert SENHA in _msg(CP.resolve_playbook_ref("allianz", "residencial"), "encanador")
    for seguradora in ("allianz", "zurich", "porto"):
        assert SENHA not in _msg(CP.resolve_playbook_ref(seguradora, "auto"), "guincho"), seguradora


def test_corredor_sem_instrucao_continua_calado_e_o_bloco_cabe():
    """`[]` é decisão (calar) — e o teto do bloco (`test_a_atendente_sabe_conduzir…`) segue."""
    assert _avise(_bloco_do_prompt(seguradora="hdi", ramo="residencial", servico="encanador")) == ""
    assert len(_bloco_do_prompt()) < 8000
