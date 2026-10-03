# -*- coding: utf-8 -*-
r"""SPEC-126 · CONSERTO Y · item 1 — a REDE (regex) do portão não diz SIM ao que não é ok.

📊 juiz B1 + red team P1 (02/10, HEAD f44526c): "manda não", "pode mandar daqui 1 hora", "pode mandar,
já resolvi", ["pode","deixar"], ["pode mandar","esquece"], ["sim","o carro pegou"], "sim?", "sim,
quanto custa?", "não sei, pode", "👌" — a regex dizia SIM (21 dos 24 não-oks novos da bancada,
`scratchpad/y_regex_head_vs_novo.py`). Nesses textos o portão era CAMADA ÚNICA: só o classificador.

O que se afirma é o MOTOR (CLAUDE.md §9.4): `confirmacao_comprovada` — a mesma função que o portão, a
ferramenta e a bancada usam — e o FIO pela ferramenta real (`_arun`, caminho LIVE, bordas dubladas),
com o classificador na BORDA dizendo OK PARA TUDO (o classificador que alucina): quem segura é a rede.
Os CONTROLES (§9.2): o ok claro continua ok (D5), e a palavra-armadilha negada/fora de contexto não
derruba ("o carro NÃO pegou", "tô a 2 km daqui", "quando chegar me avisa").

Rodar (de backend/):
    PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec126_conserto_y_rede.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

import app.agents.tools.insurer_dispatch_tool as IT  # noqa: E402
from test_spec125_conserto_y import CASO_AUTO, EMPRESA, PERGUNTA, SESSAO, _banco, ao_vivo  # noqa: E402,F401

PED = dict(CASO_AUTO)

NAO_OK = [
    ["manda não"], ["pode mandar não"], ["aciona não"], ["pode mandar não, viu"],     # negação posposta
    ["pode mandar daqui 1 hora"], ["pode mandar quando eu chegar lá"], ["manda mais tarde"],
    ["pode acionar depois das 18h"], ["Pode acionar em meia hora"], ["pode acionar às 18h"],  # adiamento
    ["pode mandar, já resolvi"], ["pode mandar… esquece"], ["ok", "já resolveu aqui, obrigado"],  # retirada
    ["pode", "deixar"], ["Pode. Deixa"], ["pode... deixar"],                           # rajada / pontuação
    ["pode mandar", "esquece"], ["sim", "o carro pegou"], ["pode mandar", "o carro pegou aqui, valeu"],
    ["isso", "deixa quieto"], ["sim. ah não, era pro carro da minha esposa"],
    ["sim?"], ["sim, quanto custa?"], ["sim vai ter custo?"], ["sim", "vai ter custo?"],  # pergunta
    ["não sei, pode"],                                                                  # dúvida
    ["👌"], ["🙏"],                                                                      # emoji ambíguo
]
OK = [
    ["pode mandar"], ["manda"], ["fechou"], ["vai lá"], ["bora"], ["👍"], ["👍🏻"], ["sim, pode acionar"],
    ["isso, manda agora"], ["✅ Pode acionar"], ["Não, ninguém se machucou. Pode mandar"],
    ["sim, o carro não pegou mesmo"], ["pode mandar, não consegui resolver sozinho"],
    ["pode mandar, tô a uns 2 km daqui"], ["Sim. Quando chegar me avisa"],
    ["Oficina Dois", "pode mandar"], ["pode mandar", "valeu"], ["sim, o carro pegou fogo, manda rápido"],
]


def _rede(falas):
    return IT.confirmacao_comprovada([("agente", PERGUNTA)] + [("segurado", f) for f in falas], PED)


@pytest.mark.parametrize("falas", NAO_OK, ids=lambda f: " | ".join(f)[:40])
def test_a_rede_recusa_o_que_nao_e_ok(falas):
    r = _rede(falas)
    assert not r["comprovada"], (falas, r)


@pytest.mark.parametrize("falas", OK, ids=lambda f: " | ".join(f)[:40])
def test_controle_o_ok_claro_continua_ok(falas):
    r = _rede(falas)
    assert r["comprovada"], (falas, r)


def test_a_ultima_palavra_vale_o_nao_antes_do_sim_e_de_outra_pergunta():
    """N1 continua: o "não" ANTES do sim é resposta a outra pergunta; DEPOIS, é retirada."""
    assert _rede(["não. pode mandar"])["comprovada"]
    assert not _rede(["pode mandar. não"])["comprovada"]
    assert not _rede(["sim", "não"])["comprovada"]


def test_a_rede_le_as_falas_juntas_a_rajada_que_retira_derruba_o_sim_de_antes():
    """Fala a fala, ["pode mandar", "esquece"] tinha um SIM e nenhum NÃO "forte" de antes — e passava."""
    assert IT._resposta_do_segurado("pode mandar", PERGUNTA) == "sim"
    assert IT._resposta_do_segurado("pode mandar\nesquece", PERGUNTA) == "nao"
    assert IT._resposta_do_segurado("sim\nvai ter custo?", PERGUNTA) == "outro"


# ─── o FIO: a ferramenta real, o classificador na borda dizendo OK PARA TUDO ───────────────────
@pytest.fixture
def classificador_que_alucina():
    from app.services.evals import bancada_confirmacao as BC

    with BC.classificador_duble_na_borda(lambda _p, _f: "ok") as chamadas:
        yield chamadas


def _acionar(falas_do_segurado):
    banco = _banco([("segurado", "meu carro morreu na estrada, preciso de guincho"), ("agente", PERGUNTA)]
                   + [("segurado", f) for f in falas_do_segurado])
    tool = IT.InsurerDispatchTool(company_id=EMPRESA, supabase_client=banco)
    return asyncio.run(tool._arun(**{**CASO_AUTO, "session_id": SESSAO, "dados_confirmados": True}))


@pytest.mark.parametrize("falas", [["manda não"], ["pode mandar daqui 1 hora"], ["pode mandar", "esquece"],
                                   ["pode", "deixar"], ["sim", "o carro pegou"], ["sim, quanto custa?"]],
                         ids=lambda f: " | ".join(f))
def test_fio_o_classificador_diz_ok_e_a_rede_segura(ao_vivo, classificador_que_alucina, falas):
    r = _acionar(falas)
    assert r["status"] == "confirm_first", r
    assert not [c for c in ao_vivo if c[0] == "start_live_dispatch"], "a rede deixou passar: %s" % falas
    assert classificador_que_alucina == [], "a rede tinha de parar ANTES do classificador"


def test_fio_controle_o_ok_aciona(ao_vivo, classificador_que_alucina):
    r = _acionar(["pode mandar"])
    assert r["status"] == "dispatched", r
    assert len([c for c in ao_vivo if c[0] == "start_live_dispatch"]) == 1
    assert len(classificador_que_alucina) == 1
