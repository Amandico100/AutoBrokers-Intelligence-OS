# -*- coding: utf-8 -*-
"""SPEC-125 · rodada pós-conserto Z (📊 C3 t2): a autorização no FIM da oração, sem vírgula, é sim."""
from app.agents.tools.insurer_dispatch_tool import _resposta_do_segurado as r

P = "Vou acionar o guincho para a placa ABC1D23 na Rua Sete, 100. Posso acionar?"


def test_autorizacao_no_fim_sem_virgula_e_sim():
    assert r("sou eu que tô com o carro pode acionar", P) == "sim"
    assert r("tô aqui no local pode mandar", P) == "sim"


def test_controle_objecao_e_adiamento_continuam_vencendo():
    assert r("ta bom, depois eu peço", P) == "nao"
    assert r("nao pode acionar", P) == "nao"
    assert r("sou eu que tô com o carro", P) == "outro"
