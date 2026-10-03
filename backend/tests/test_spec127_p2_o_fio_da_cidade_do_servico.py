# -*- coding: utf-8 -*-
"""SPEC-127 P2 — O TESTE DO FIO: a cidade é a do SERVIÇO, no DOM inteiro.

📊 O defeito (laudo INV-PORTAL, BLOCO 0 item 1): `adaptive.fatos_da_tela` lia
`collected["local"]` — estado, cidade e CEP do CADASTRO (InfoCap) — e escrevia
na tela "Selecione o estado ONDE DESEJA SER ATENDIDO". Quem mora em Palhoça e
quer o vidro em Joinville tinha o pedido aberto em Palhoça, sem parada nenhuma.

O fio, com o MOTOR real e o dublê só no navegador (`_pagina_falsa_do_dom`, sobre
as árvores derivadas do HTML real do intake):

    vidros_lanternas.abrir_atendimento (a entrada do worker)
      → passo 1 (guard da fronteira A) → "Iniciar atendimento" → "Confirmar"
      → run_adaptive(conter=True): 20% contato → 50% peça/causa → 50% cidade/CEP
      → a tela do protocolo

🔴 Nasceu VERMELHO no HEAD `44e0f1a` (o DOM escrevia "Palhoca") e o par sem
cidade do serviço abria o pedido mesmo assim.
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from portal_worker import adaptive as AD  # noqa: E402
from portal_worker.journeys import vidros_lanternas as VL  # noqa: E402
from tests._pagina_falsa_do_dom import PaginaFalsa, RuntimeFalso  # noqa: E402

# 💭 caso SINTÉTICO: mora em Palhoça (cadastro), quer o serviço em Joinville.
CADASTRO = {"estado": "SC", "cidade": "Palhoca", "cep": "88130000"}
FLUXO = {
    ("yelum_passo1", "Confirmar"): "yelum_contato_20",
    ("yelum_contato_20", "Avançar"): "yelum_parabrisa_50_peca_causa",
    ("yelum_parabrisa_50_peca_causa", "Avançar"): "yelum_lataria_50_cidade_cep",
    ("yelum_lataria_50_cidade_cep", "Avançar"): "protocolo",
}
SUGESTOES = {"fl-input-171": ["SC"], "fl-input-172": ["JOINVILLE"]}


def _params(local, *, confirm=True):
    return {
        "insurer_name": "Yelum", "cpf_cnpj": "00000000191", "placa": "QAB1A91",
        "data_dano": "14/08/2026", "confirm": confirm,
        "solicitante": {"relacao": "Corretor", "nome": "CORRETORA DE TESTE",
                        "email": "corretora@example.invalid", "telefone": "4700000000",
                        "cpf_cnpj": "00000000000191"},
        "segurado": {"nome": "SEGURADO DE TESTE", "cep": "88130000"},
        "dano": {"peca": "para-brisa", "como": "COLISÃO ACIDENTAL", "onde": "urbano",
                 "descricao": "BATI O CARRO E O PARA-BRISA TRINCOU INTEIRO NA ESTRADA"},
        "local": local,
        "especificos": {},
    }


def _abre_o_passo1_e_o_modal(p, texto):
    # O modal "Dados da apólice" nasce do "Iniciar atendimento" (📊 HAR: GET /apolices).
    if texto == "Iniciar atendimento" and p.atual == "yelum_passo1":
        p.tela["buttons"].append({"text": "Confirmar", "disabled": False})


def _rodar(local, *, confirm=True, sugestoes=None, monkeypatch=None):
    pagina = PaginaFalsa("yelum_passo1", FLUXO, sugestoes or SUGESTOES, ao_clicar=_abre_o_passo1_e_o_modal)
    rt = RuntimeFalso(pagina, liberado=confirm)
    params = _params(local, confirm=confirm)
    params["_runtime"] = rt
    vistos = []

    async def _cerebro(state, goal, collected, history, force=False, **_k):
        # O modelo só NAVEGA: na falsa, ele sempre pede "Avançar".
        vistos.append({"tela": state, "dados": collected})
        return {"action": "click", "target": "Avançar", "value": "", "reason": "teste"}

    async def _navegou(page, insurer):
        return True

    monkeypatch.setattr(AD, "decide_next_action", _cerebro)
    monkeypatch.setattr(VL, "_select_insurer_start", _navegou)
    evidence: dict = {}
    r = asyncio.run(VL.abrir_atendimento(pagina, params, evidence))
    return r, pagina, evidence, vistos, rt


def _escritos(pagina):
    return [x for x in pagina.log if x[0] in ("fill", "autocomplete", "select")]


def test_o_dom_preenche_a_cidade_do_SERVICO_e_nunca_a_do_cadastro(monkeypatch):
    local = {**CADASTRO, "cidade_servico": {"uf": "SC", "cidade": "Joinville"}}
    r, pagina, ev, _vistos, _rt = _rodar(local, monkeypatch=monkeypatch)
    cidade = {c["id"]: c["value"] for c in pagina.telas["yelum_lataria_50_cidade_cep"]["inputs"]}
    assert cidade["fl-input-172"] == "JOINVILLE", f"cidade escrita: {cidade}"
    assert cidade["fl-input-171"] == "SC"
    assert not any("palhoca" in AD._norm(str(x)) for x in _escritos(pagina)), _escritos(pagina)
    # O CEP do cadastro é de Palhoça: numa busca em Joinville ele acharia a loja errada.
    assert cidade["cep"] == "", f"CEP do cadastro foi para a cidade do servico: {cidade['cep']!r}"
    assert r.status == "done" and (r.captured or {}).get("protocolo") == "40000001", (r.status, r.message)


def test_CONTROLE_mesma_cidade_o_CEP_do_cadastro_vai(monkeypatch):
    """O par que prova que o CEP vazio acima vem da REGRA, não de cegueira."""
    local = {**CADASTRO, "cidade_servico": {"uf": "SC", "cidade": "Palhoça"}}
    r, pagina, _ev, _v, _rt = _rodar(local, sugestoes={"fl-input-171": ["SC"], "fl-input-172": ["PALHOÇA"]},
                                     monkeypatch=monkeypatch)
    cidade = {c["id"]: c["value"] for c in pagina.telas["yelum_lataria_50_cidade_cep"]["inputs"]}
    assert cidade["fl-input-172"] == "PALHOÇA" and cidade["cep"] == "88130000", cidade
    assert r.status == "done"


def test_sem_a_cidade_do_servico_o_dom_PARA_antes_de_escrever(monkeypatch):
    r, pagina, ev, vistos, rt = _rodar(dict(CADASTRO), monkeypatch=monkeypatch)
    assert r.status == "needs_human"
    assert (r.captured or {}).get("acao_esperada") == "responder:cidade_servico", r.captured
    assert (r.captured or {}).get("stage") == "falta_cidade_servico"
    # nada escrito no portal: nenhum clique, nenhum efeito armado, nenhum modelo
    assert pagina.cliques == [] and rt.gravacoes == [] and vistos == []
    assert "Iniciar atendimento" not in pagina.cliques


def test_a_cidade_HOMONIMA_nunca_e_escolhida(monkeypatch):
    """P-124-14 no DOM: "Curitiba" × CURITIBANOS. 📊 O `_pick_autocomplete`
    clicava "começa com → contém → a PRIMEIRA sugestão"."""
    local = {**CADASTRO, "cidade_servico": {"uf": "SC", "cidade": "Curitiba"}}
    r, pagina, ev, _v, _rt = _rodar(local, sugestoes={"fl-input-171": ["SC"], "fl-input-172": ["CURITIBANOS"]},
                                    monkeypatch=monkeypatch)
    cidade = {c["id"]: c["value"] for c in pagina.telas["yelum_lataria_50_cidade_cep"]["inputs"]}
    assert cidade["fl-input-172"] == "", f"o autocomplete ficou com {cidade['fl-input-172']!r}"
    assert r.status == "needs_human"
    assert (r.captured or {}).get("stage") == "cidade_ambigua"
    assert (r.captured or {}).get("acao_esperada") == "responder:cidade_servico"
    assert (r.captured or {}).get("opcoes") == ["CURITIBANOS"], r.captured
    assert "Avançar" not in pagina.cliques[pagina.cliques.index("Confirmar") + 3:], pagina.cliques


def test_CONTROLE_a_cidade_igual_entre_parecidas_e_escolhida(monkeypatch):
    local = {**CADASTRO, "cidade_servico": {"uf": "SC", "cidade": "Curitiba"}}
    r, pagina, _ev, _v, _rt = _rodar(local, sugestoes={"fl-input-171": ["SC"],
                                                       "fl-input-172": ["CURITIBANOS", "CURITIBA"]},
                                     monkeypatch=monkeypatch)
    cidade = {c["id"]: c["value"] for c in pagina.telas["yelum_lataria_50_cidade_cep"]["inputs"]}
    assert cidade["fl-input-172"] == "CURITIBA" and r.status == "done", (cidade, r.message)


@pytest.mark.parametrize("valor,sugestoes,esperado", [
    ("Curitiba", ["CURITIBANOS"], None),
    ("Palmas", ["PALMA SOLA"], None),
    ("Santo Amaro", ["SANTO AMARO DA IMPERATRIZ"], None),
    ("São José", ["SÃO JOSÉ DO CEDRO", "SAO JOSE"], 1),
    ("Joinville", ["JOINVILLE", "JOINVILLE"], None),   # duas iguais = nenhuma
    ("", ["SC"], None),
])
def test_sugestao_igual_e_igualdade_e_so(valor, sugestoes, esperado):
    assert AD.sugestao_igual(valor, sugestoes) == esperado
