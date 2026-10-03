# -*- coding: utf-8 -*-
r"""SPEC-126 · CONSERTO 2 · pendências 1–5 do laudo de confirmação — cada uma pelo MOTOR que decide.

📊 Sondas do juiz (02/10, `scratchpad/confirm126/test_conf126_sondas.py`, saída `sondas_out.txt`):
  pend. 1  a REDE recusava a descrição do problema: "pode mandar, eu esqueci a chave dentro", "sim, já
           tentei de tudo e nada resolveu", "pode mandar, tô aqui faz 2 horas", "pode mandar, o pneu furou
           e não tenho estepe" (+ "sim, ela já ligou pra vocês antes", "sim, não sei o que houve")
  pend. 2  a REDE aceitava "pode mandar, ah não esquece" e "pode mandar... deixa"
  pend. 3  o FISCAL desmentia fato do sistema: "O agendamento da vistoria foi cancelado pela seguradora",
           "O sinistro foi cancelado pela seguradora em 10/09", "O prestador anterior foi dispensado…"
  pend. 4  K3 (cancelamento → pessoa) para "esquece a placa que mandei, o guincho é pro outro carro" e
           "deixa pra lá, cadê o guincho?"
  pend. 5  `N` para "esquece, achei a chave" (o chaveiro já na rua)

Motores: `confirmacao_comprovada` (a rede do portão) e, de ponta a ponta, `nodes.tool_node` →
`InsurerDispatchTool._arun`; `guardar_a_verdade_do_handoff` (o fiscal); `classificar_turno` (a cascata).

Rodar (de backend/):
    PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec126_conserto2_rede_fiscal_k3.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from langchain_core.messages import AIMessage, HumanMessage

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

import app.agents.tools.insurer_dispatch_tool as IT  # noqa: E402
from app.agents import honestidade_do_handoff as H  # noqa: E402
from app.agents import nodes as N  # noqa: E402
from app.atendimento.pos_acionamento import classificar_turno  # noqa: E402
from test_spec125_conserto_y import CASO_AUTO, PERGUNTA, ao_vivo  # noqa: E402,F401
from test_spec126_u3_d1_parente_aciona import EMPRESA_A, SESSAO_A, borda, estado  # noqa: E402,F401


def _rede(resposta) -> bool:
    falas = [("agente", PERGUNTA)] + [("segurado", r) for r in (resposta if isinstance(resposta, list)
                                                               else [resposta])]
    return IT.confirmacao_comprovada(falas, CASO_AUTO)["comprovada"]


# ─── pend. 1: a descrição do problema é o sim, não a retirada ─────────────────────────────────
DESCRICAO_NAO_RETIRA = [
    "pode mandar, eu esqueci a chave dentro",
    "sim, já tentei de tudo e nada resolveu",
    "pode mandar, tô aqui faz 2 horas",
    "pode mandar, o pneu furou e não tenho estepe",
    "sim, ela já ligou pra vocês antes",
    "sim, não sei o que houve",
    # controles do mesmo desenho
    "sim, estou parado há 3 horas", "pode mandar, esperando desde as 18h",
    "pode mandar, não esquece de levar o macaco", "sim, o pneu estourou e o estepe tá furado",
    "sim, ninguém conseguiu resolver aqui",
]


@pytest.mark.parametrize("resposta", DESCRICAO_NAO_RETIRA)
def test_pend1_a_descricao_do_problema_e_o_sim(resposta):
    assert _rede(resposta), resposta


# ─── pend. 2 + os controles: a retirada e o adiamento continuam NÃO ───────────────────────────
CONTINUAM_NAO = [
    "pode mandar, ah não esquece", "pode mandar... deixa", "pode mandar… esquece", ["pode mandar", "esquece"],
    ["pode mandar", "ah não esquece"], "pode mandar, ah, deixa", "pode mandar. deixa",
    # "esqueci" ≠ "esquece"; "faz 2 horas" ≠ "daqui 2 horas" — os controles do outro lado
    "pode mandar, esquece", "pode esquecer", "pode mandar daqui 2 horas", "pode mandar em 2 horas",
    "pode acionar às 18h", "pode mandar 2 horas", "sim, já resolvi", "sim, o carro ligou",
    "sim, nada, já resolveu", "sim, não sei", "não sei, pode", "sim, ele ligou aqui",
    "pode mandar o borracheiro",   # serviço NOMEADO diferente do resumo de guincho
]


@pytest.mark.parametrize("resposta", CONTINUAM_NAO)
def test_pend2_e_controles_retirada_adiamento_e_troca_continuam_nao(resposta):
    assert not _rede(resposta), resposta


def test_pend1_o_servico_nomeado_continua_trocando_o_pedido():
    """Só o SINTOMA da peça sai: "troca o pneu" nomeia o serviço de pneu e continua sendo troca."""
    assert IT.servico_trocado(["pode mandar, troca o pneu"], CASO_AUTO)
    assert not IT.servico_trocado(["pode mandar, o pneu furou e não tenho estepe"], CASO_AUTO)


# ─── pend. 1 de ponta a ponta: o chaveiro com "eu esqueci a chave dentro" SAI ─────────────────
PERGUNTA_CHAVEIRO = "Chaveiro para o carro de placa AAA0A91, na Rua Um, 100. Posso acionar?"
CASO_CHAVEIRO = {**CASO_AUTO, "subservice": "chaveiro", "problema_descricao": "a chave ficou trancada dentro"}


@pytest.mark.parametrize("ok, sai", [("pode mandar, eu esqueci a chave dentro", True),
                                     ("pode mandar, ah não esquece", False)])   # a linha de controle
def test_pend1_pelo_motor_o_chaveiro_sai_com_a_descricao(borda, ao_vivo, ok, sai):
    from app.services.evals import bancada_confirmacao as BC

    banco, _prov = borda
    rot = sys.modules["app.services.dispatch_router"]
    efeitos: list = []

    async def _start(**kw):
        efeitos.append(("START", kw.get("subservice")))
        return {"ok": True, "session": {"client_phone": kw.get("client_phone"), "subservice": kw.get("subservice")}}

    rot.start_live_dispatch = _start
    banco.tabelas.setdefault("conversations", []).append(
        {"id": "conv-y", "company_id": EMPRESA_A, "session_id": SESSAO_A, "channel": "whatsapp",
         "ficha_atendimento": None})
    agora = datetime.now(timezone.utc)
    for k, (quem, texto) in enumerate([("segurado", "tranquei a chave no carro"), ("agente", PERGUNTA_CHAVEIRO),
                                       ("segurado", ok)]):
        banco.tabelas.setdefault("messages", []).append({
            "id": "m-%s" % uuid.uuid4().hex[:8], "conversation_id": "conv-y",
            "role": "user" if quem == "segurado" else "assistant", "content": texto, "payload": {},
            "created_at": (agora - timedelta(minutes=5 - k)).isoformat()})
    tool = IT.InsurerDispatchTool(company_id=EMPRESA_A, supabase_client=banco)
    st = estado([HumanMessage(content=ok), AIMessage(content="", tool_calls=[{
        "name": "insurer_dispatch", "id": "c1", "args": {**CASO_CHAVEIRO, "dados_confirmados": True}}])])
    with BC.classificador_duble_na_borda():           # diz OK: quem decide é a rede
        asyncio.run(N.tool_node(st, tools=[tool]))
    assert (efeitos == [("START", "chaveiro")]) is sai, efeitos


# ─── pend. 3: o fiscal não desmente o fato de terceiro ────────────────────────────────────────
FATO_DE_TERCEIRO = [
    "O agendamento da vistoria foi cancelado pela seguradora.",
    "O sinistro foi cancelado pela seguradora em 10/09.",
    "O prestador anterior foi dispensado e um novo está a caminho.",
    "Sua vistoria foi desmarcada pela seguradora, quer remarcar?",
    "O pedido consta como cancelado no sistema da seguradora.",
    "Esse protocolo foi cancelado pelo sistema, vou abrir outro com você.",
    "Sua apólice consta como cancelada.", "A parcela 3 está cancelada.",
]


@pytest.mark.parametrize("texto", FATO_DE_TERCEIRO)
def test_pend3_o_fiscal_nao_reescreve_o_fato_de_terceiro(texto):
    assert H.guardar_a_verdade_do_handoff(texto, []) == texto


#: os controles: o FEITO do agente continua reescrito — inclusive com o agente de fora como álibi
FEITO_DO_AGENTE = [
    "Pronto, cancelado!", "Cancelado ✅", "Cancelei o guincho.", "O guincho foi cancelado.",
    "O guincho foi dispensado.", "Pronto, o guincho foi cancelado pela seguradora.",
    "O guincho foi cancelado pela corretora.", "Prontinho, o pedido foi cancelado pelo sistema.",
]


@pytest.mark.parametrize("texto", FEITO_DO_AGENTE)
def test_pend3_controle_o_feito_do_agente_continua_reescrito(texto):
    saida = H.guardar_a_verdade_do_handoff(texto, [])
    assert saida != texto and H.NOTA_DO_CANCELAMENTO_SEM_FERRAMENTA in saida, saida


# ─── pend. 4/5: K3 é cancelar o serviço — o objeto decide ─────────────────────────────────────
@pytest.mark.parametrize("fala", [
    "esquece a placa que mandei, o guincho é pro outro carro",     # pend. 4 — correção de dado
    "deixa pra lá, cadê o guincho?",                                # pend. 4 — impaciência
    "esquece o endereço que te passei, o guincho tem que ir na Rua Dois",
    "esquece aquilo, manda o guincho", "deixa pra lá, já entendi", "esquece, quanto tempo falta?",
    "esqueci a chave dentro do carro, o chaveiro ja vem?",
])
def test_pend4_o_esquece_de_outra_coisa_nao_e_cancelar(fala):
    assert classificar_turno([fala]) != "K3", fala


@pytest.mark.parametrize("fala", [
    "esquece, achei a chave",                                       # pend. 5
    "deixa pra lá, encontrei a chave", "esquece, abri o carro",
    # controles: o cancelamento de sempre continua K3
    "esquece o guincho", "deixa pra lá", "dispensa o reboque, vou levar empurrando", "desmarca o técnico",
    "esquece o chaveiro, já abri a porta", "o guincho pode ir embora", "esquece, o carro pegou",
    "não manda mais ninguém", "deixa pra lá o guincho",
])
def test_pend5_e_controles_cancelar_continua_k3(fala):
    assert classificar_turno([fala]) == "K3", fala
