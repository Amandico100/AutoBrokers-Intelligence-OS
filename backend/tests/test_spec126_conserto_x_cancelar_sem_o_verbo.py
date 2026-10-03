# -*- coding: utf-8 -*-
r"""SPEC-126 · CONSERTO X · RT-B2 — cancelar SEM o verbo "cancelar" num caso JÁ ACIONADO → pessoa na hora.

📊 Sonda do red team (HEAD f44526c, 02/10/2026): `classificar_turno` dava `N` para "esquece o guincho",
"deixa pra lá", "dispensa/desmarca/suspende o guincho", "manda voltar o guincho", "não precisa mandar mais
ninguém", "o guincho pode ir embora", "pode liberar o de vocês", "cancelaaaa", "aborta" (`rt126_probe1.py`
§2); e `por_que_vai_direto_a_pessoa` dava a SEGUNDA CHANCE a esses casos quando o modelo escrevia o motivo em
prosa ("cliente quer cancelar o guincho") — `rt126_probe2.py`.

A decisão vem das FALAS (R9 = `K3`) e do ESTADO (`_e_pos_acionamento`), nunca do código no motivo.

A ESCOLHA DOCUMENTADA (o objeto decide):
  · verbo de dispensar + SERVIÇO ("esquece o guincho", "desmarca o técnico")        → K3
  · "esquece" / "deixa pra lá" / "aborta" como a ÚLTIMA coisa do turno               → K3 (inequívoco no
    pós-acionamento: a última palavra dele sobre o serviço que está na rua é "deixa")
  · "esquece" / "deixa pra lá" + sinal de que se resolveu ("já resolvi", "o carro pegou") → K3
  · "deixa pra lá, já entendi" (o objeto é a EXPLICAÇÃO) → NÃO é K3
  · "esquece aquilo, manda o guincho" (o objeto é OUTRA coisa e ele PEDE o serviço) → NÃO é K3
🔴 Mutação (uma vez, por cópia): tirar as regras novas da cascata → os casos do RT vermelhos.
"""
from __future__ import annotations

import os
import sys

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

# ⚠️ os pacotes REAIS antes do módulo da SPEC-123: ele instala pacotes-casca em `sys.modules` quando
#    `app` ainda não foi importado, e a casca quebrava o arquivo de teste seguinte na mesma rodada
#    (`ImportError: IntegrationService … (unknown location)`) — a mesma ordem de `test_spec126_u5_diario`.
from app.agents import nodes as _N  # noqa: E402,F401
from app.atendimento.pos_acionamento import classificar_turno  # noqa: E402

from test_spec123_atendimento_segunda_chance import (  # noqa: E402,F401
    ENVIOS, _banco, _conversa, _diario, _linha, _pedir, borda)


def _ficha_do_produto():
    """A ficha como o PRODUTO a grava depois de um acionamento — pelo escritor real (`fundir`)."""
    from app.services.attendance_ficha import ficha_vazia, fundir

    f = fundir(ficha_vazia(), {"servico": "guincho", "seguradora": "seguradora exemplo",
                               "confirmados": {"local_atual": "Rua Teste 10"}})
    return fundir(f, {"acionamento": {"protocolo": "PR20261002"}})


def _caso_acionado(cid, fala, ficha=None):
    # (cópia do helper da U4: importar aquele módulo de teste duplica as fixtures dele na coleta)
    b = _banco(_conversa(cid, preview=fala, ficha=ficha or _ficha_do_produto()))
    b.tabelas["messages"].append({"conversation_id": cid, "role": "user", "content": fala,
                                  "created_at": "2026-10-02T10:00:00+00:00"})
    return b


@pytest.mark.parametrize("fala", [
    "esquece o guincho", "deixa pra lá o guincho", "dispensa o guincho", "desmarca o guincho",
    "suspende o guincho", "manda voltar o guincho", "o carro pegou, pode dispensar o guincho",
    "pode desmarcar o técnico", "esquece o chaveiro, já abri a porta",
    "deixa pra lá", "Deixa pra lá então", "esquece", "esquece isso", "aborta",
    "esquece, já resolvi", "deixa pra lá, o carro pegou", "deixa quieto, consegui sozinho",
    "não manda mais", "não precisa mandar mais ninguém", "não precisa mandar ninguém mais",
    "o guincho pode ir embora", "já chegou um guincho particular, pode liberar o de vocês",
    "cancelaaaa", "não vem mais não",
])
def test_rt_b2_k3_reconhece_cancelar_sem_o_verbo(fala):
    assert classificar_turno([fala]) == "K3", fala


@pytest.mark.parametrize("fala", [
    "deixa pra lá, já entendi",                 # o objeto é a explicação
    "esquece aquilo, manda o guincho",          # pede o serviço
    "esquece o que eu falei, pode mandar o guincho",
    "não esquece de mandar o guincho",          # negação
    "o guincho não vem mais?",                  # pergunta, não pedido (fica fora de K3)
    "não precisa mandar mensagem mais não",
    "deixa pra lá a vistoria, manda o guincho",
    "pode liberar o carro?",
    # 📊 acervo (02/10, controle da cascata em 15.773 falas): conselho, não ordem — casavam na 1ª versão
    "pode seguir viagem, mas nao se esqueca de buscar uma assistencia especializada",
    "anota o numero caso tu esqueca",
])
def test_rt_b2_controle_o_que_nao_e_cancelar_o_servico(fala):
    assert classificar_turno([fala]) != "K3", fala


@pytest.mark.parametrize("fala,motivo", [
    ("esquece o guincho", "cliente quer cancelar o guincho"),
    ("deixa pra la, o carro pegou", "o segurado desistiu do guincho"),
    ("dispensa o guincho", "cancelar acionamento"),
    ("manda voltar o guincho", "cliente pediu para esquecer o guincho"),
    ("desmarca o guincho", "o segurado tem uma dúvida"),            # motivo que nem fala em cancelar
])
def test_rt_b2_o_fio_caso_acionado_vai_a_pessoa_com_o_dossie_mesmo_com_motivo_em_prosa(
        borda, monkeypatch, fala, motivo):
    import app.agents.tools.human_handoff as HH
    import app.services.o_grupo_so_o_que_importa as G
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF

    # a carga que vai ao feed/medição do grupo — observada, não dublada (o real roda)
    cargas, real = [], G._carga

    def _espiao(*a, **k):
        c = real(*a, **k)
        cargas.append(c)
        return c
    monkeypatch.setattr(G, "_carga", _espiao)

    cid = "c-x-b2-fio"
    b = _caso_acionado(cid, fala)
    r = _pedir(HH, b, cid, motivo)
    assert r == SUCESSO_DO_HANDOFF, (fala, motivo, r)                # NUNCA a segunda chance
    assert _linha(b, cid)["status"] == "HUMAN_REQUESTED"
    assert len(ENVIOS) == 1, ENVIOS
    dossie = ENVIOS[0][1]
    assert "CANCELAR" in dossie and "NÃO cancelou" in dossie
    assert fala in dossie                                            # a frase dele
    assert [l["acao"] for l in _diario(b, cid)] == ["chamou_pessoa"]
    # o motivo que o grupo/medição lê é o CÓDIGO do D4, mesmo com o motivo do modelo em prosa
    assert cargas and all(c.get("motivo") == "cancelamento_pos_acionamento"
                          and c.get("motivo_classe") == "regra" for c in cargas), cargas


def test_rt_b2_controle_deixa_pra_la_ja_entendi_num_caso_acionado_nao_e_cancelamento(borda):
    import app.agents.tools.human_handoff as HH

    cid = "c-x-b2-ctl1"
    b = _caso_acionado(cid, "deixa pra lá, já entendi")
    r = _pedir(HH, b, cid, "cliente quer cancelar o guincho")
    assert HH.foi_segunda_chance(r), r
    assert ENVIOS == []


def test_rt_b2_controle_antes_de_acionar_esquece_o_guincho_ganha_a_segunda_chance(borda):
    """Sem acionamento não há o que cancelar na seguradora: o ESTADO decide, não a frase."""
    import app.agents.tools.human_handoff as HH

    cid = "c-x-b2-ctl2"
    b = _caso_acionado(cid, "esquece o guincho", ficha={"fase": "coleta", "servico": "guincho"})
    assert _pedir(HH, b, cid, "cliente quer cancelar o guincho") == HH.SEGUNDA_CHANCE_DO_HANDOFF
    assert ENVIOS == []
