# -*- coding: utf-8 -*-
"""SPEC-126 U3-B · D1 — o parente aciona e NUNCA vê dado da apólice no turno SEGUINTE.

📊 Probe da U3 (motor real, conversa semeada, 02/10/2026): depois do turno do filho,
`attendance_ficha.bloco_para_o_prompt(ficha)` mostrava "<APOLICE> · auto · Seguradora ·
vigente até 01/03/2027". O `ToolMessage` estava cortado (U3); a ficha DURÁVEL não.

🔴 O TESTE DO FIO (1ª entrega da U3-B, nasceu VERMELHO): `nodes.tool_node` REAL →
`InfocapPolicyLookupTool._arun` REAL → `policy_context` REAL → a ficha gravada no banco (de
mentira, mas que filtra) → `attendance_ficha.carregar` + `bloco_para_o_prompt` REAIS (o que
`graph.py:1763-1783` injeta no prompt do turno seguinte) e `quem_e_o_segurado.montar` +
`bloco_para_o_prompt` REAIS (`graph.py:1808`). Dublês só na borda (provedor, banco).
Controle: o TITULAR falando → o bloco continua com a apólice (o guarda consegue ficar vermelho).
Dados 100 % fictícios; nenhuma corretora real (CLAUDE.md §13.9).
"""
from __future__ import annotations

import asyncio
import copy
import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents import nodes as N
from app.agents import quem_e_o_segurado as Q
from app.services import attendance_ficha as F
from tests.test_spec126_u3_d1_parente_aciona import (  # noqa: F401 — a borda é fixture
    APOLICE, CPF_DO_PAI, EMPRESA_A, FILHO_PEDE_GUINCHO, SESSAO_A, VIGENCIA_FIM, _com_conversa,
    borda, consultar_pelo_motor, estado, o_que_o_modelo_le)

#: o que é DADO da apólice no bloco do prompt (a seguradora fictícia vira `.title()` no bloco)
DADOS_NO_PROMPT = (APOLICE, VIGENCIA_FIM, "Seguradoraficticia", "SEGURADORAFICTICIA", "ZZZ9Z99")


def _ficha(banco) -> dict:
    return asyncio.run(F.carregar(banco, EMPRESA_A, SESSAO_A))


def _prompt_do_turno_seguinte(banco, falas) -> str:
    """O que `graph.py` monta no turno seguinte: o bloco da FICHA + o bloco de QUEM É."""
    ficha = _ficha(banco)
    historico = [{"role": "user", "content": f, "created_at": "2026-10-02T12:00:%02d+00:00" % i}
                 for i, f in enumerate(falas)]
    quem = Q.montar(historico=historico, ficha=ficha)
    return F.bloco_para_o_prompt(ficha, []) + "\n" + Q.bloco_para_o_prompt(quem)


def _dados(texto: str) -> list:
    return [d for d in DADOS_NO_PROMPT if d.lower() in texto.lower()]


# =========================================================================== #
# 🔴 O FIO
# =========================================================================== #
def test_fio_o_turno_seguinte_do_parente_nao_mostra_a_apolice(borda):
    banco, _ = borda
    _com_conversa(banco)
    saida = consultar_pelo_motor(FILHO_PEDE_GUINCHO, CPF_DO_PAI)
    assert "pode acionar" in o_que_o_modelo_le(saida).lower(), "o parente tem de ser AUTORIZADO"

    prompt = _prompt_do_turno_seguinte(banco, FILHO_PEDE_GUINCHO)
    assert _dados(prompt) == [], "dado da apólice do TITULAR no prompt do parente: %s" % _dados(prompt)
    assert "é do TITULAR, que NÃO é quem fala" in prompt, prompt
    assert "NÃO diga" in prompt and "placa" in prompt

    # ⛔ e o ACIONAMENTO continua com a apólice INTEIRA (a marca só cala o prompt)
    ficha = _ficha(banco)
    ap = F.apolice_do_caso(ficha=ficha) or {}
    assert ap.get("numapo") == APOLICE and ap.get("seguradora"), ficha
    assert (ficha.get("apolice_do_caso") or {}).get("de_outra_pessoa") is True


def test_controle_o_titular_falando_continua_vendo_a_apolice(borda):
    """§9.2/§9.3 — o MESMO caminho com o titular: o bloco CONSEGUE mostrar a apólice."""
    banco, _ = borda
    _com_conversa(banco)
    falas = ["meu carro quebrou, preciso de guincho", f"meu cpf é {CPF_DO_PAI}"]
    consultar_pelo_motor(falas, CPF_DO_PAI)
    prompt = _prompt_do_turno_seguinte(banco, falas)
    assert APOLICE in prompt and VIGENCIA_FIM in prompt, prompt
    assert "é do TITULAR" not in prompt
    assert (_ficha(banco).get("apolice_do_caso") or {}).get("de_outra_pessoa") is None


def test_a_marca_sobrevive_ao_acionamento_e_o_acionamento_recebe_a_apolice_inteira(borda):
    """O turno do ACIONAMENTO relê o contexto (estado → ficha), escolhe a apólice e sobrescreve
    seguradora/ramo com os do SISTEMA — e regrava a ficha SEM perder a marca."""
    banco, _ = borda
    _com_conversa(banco)
    ctx = consultar_pelo_motor(FILHO_PEDE_GUINCHO, CPF_DO_PAI).get("infocap_policy_context")

    recebido: dict = {}

    class _Dispatch:
        name, exige_async = "insurer_dispatch", True

        async def _arun(self, **kw):
            recebido.update(kw)
            return {"status": "dispatched", "content": "[ACIONAMENTO REAL INICIADO]\nSERVIÇO ACIONADO: guincho"}

    st = estado([HumanMessage(content=f) for f in FILHO_PEDE_GUINCHO] + [AIMessage(content="", tool_calls=[{
        "name": "insurer_dispatch", "id": "call-d1",
        "args": {"subservice": "guincho", "titular_cpf": CPF_DO_PAI, "insurer_key": "outra",
                 "ramo_da_apolice": "residencial", "dados_confirmados": True}}])])
    st["infocap_policy_context"] = copy.deepcopy(ctx)
    saida = asyncio.run(N.tool_node(st, tools=[_Dispatch()]))

    assert recebido.get("titular_cpf") == CPF_DO_PAI, "o CPF vai INTEIRO ao acionamento (D3)"
    assert recebido.get("insurer_key") == F.chave_da_seguradora("SEGURADORAFICTICIA"), recebido
    assert recebido.get("ramo_da_apolice") == "auto", recebido
    assert (_ficha(banco).get("apolice_do_caso") or {}).get("de_outra_pessoa") is True
    assert _dados(o_que_o_modelo_le(saida)) == []


def test_o_resultado_antigo_da_consulta_no_historico_ja_e_o_texto_cortado(borda):
    """O OUTRO caminho medido: o `ToolMessage` da consulta FICA no histórico do checkpoint e
    volta ao modelo no turno seguinte. Ele é o texto do titular autorizado — sem dado."""
    banco, _ = borda
    _com_conversa(banco)
    saida = consultar_pelo_motor(FILHO_PEDE_GUINCHO, CPF_DO_PAI)
    tool_msgs = [m for m in saida["messages"] if getattr(m, "type", "") == "tool"]
    assert tool_msgs and all(_dados(str(m.content)) == [] for m in tool_msgs)
    assert "rastro_da_consulta" not in json.dumps([str(m.content) for m in tool_msgs])


# =========================================================================== #
# O DOSSIÊ AO GRUPO (trecho D)
# =========================================================================== #
def _conversa_com_a_ficha(banco, **extra) -> dict:
    ficha = copy.deepcopy(_ficha(banco))
    ficha.setdefault("confirmados", {})["titular_nome"] = {"valor": "Joao Carlos", "origem": "cliente"}
    ficha.update(extra)
    return {"id": "conv-x", "company_id": EMPRESA_A, "session_id": SESSAO_A, "user_name": "Filho",
            "user_phone": "5500000001260", "ficha_atendimento": ficha}


@pytest.mark.parametrize("pos_acionamento", [False, True])
def test_o_dossie_diz_que_o_pedido_foi_de_terceiro_so_com_as_iniciais(borda, pos_acionamento):
    from app.agents.tools.human_handoff import HumanHandoffTool

    banco, _ = borda
    _com_conversa(banco)
    consultar_pelo_motor(FILHO_PEDE_GUINCHO, CPF_DO_PAI)
    extra = {"acionamento": {"protocolo": "PR-0001"}} if pos_acionamento else {}
    dossie = HumanHandoffTool(supabase_client=banco)._montar_dossie(
        _conversa_com_a_ficha(banco, **extra), "segurado pediu uma pessoa")
    assert "👪 Pedido feito por terceiro (parente/motorista) — titular: J. C." in dossie, dossie
    assert "Joao Carlos" not in dossie, "o nome inteiro do titular no histórico do grupo"


def test_controle_o_dossie_do_titular_nao_tem_a_linha(borda):
    from app.agents.tools.human_handoff import HumanHandoffTool

    banco, _ = borda
    _com_conversa(banco)
    consultar_pelo_motor(["meu carro quebrou, preciso de guincho", f"meu cpf é {CPF_DO_PAI}"], CPF_DO_PAI)
    dossie = HumanHandoffTool(supabase_client=banco)._montar_dossie(
        _conversa_com_a_ficha(banco), "segurado pediu uma pessoa")
    assert "Pedido feito por terceiro" not in dossie
    assert APOLICE in dossie, "CONTROLE: a corretora continua vendo a apólice no dossiê"


# =========================================================================== #
# A BANCADA não corta o parente que o produto deixa acionar (trecho E)
# =========================================================================== #
def test_a_bancada_responde_ao_parente_o_que_o_produto_responde():
    from app.agents.tools import infocap_tool as T
    from app.services.evals import bancada as B

    base = {"resposta": {"content": "Apolice 123 vigente", "data": {"ok": True, "status": "found"},
                         "policy_response_contract": {"x": 1}}}
    cen = {"roteiro": {"falas_fixas": [["sou o filho dele, o carro quebrou, preciso de guincho",
                                         f"o cpf dele é {CPF_DO_PAI}"]]}}
    r = B._corte_de_terceiro(cen, copy.deepcopy(base), {"documento": CPF_DO_PAI})["resposta"]
    assert r.get(T.MARCA_DO_TITULAR_AUTORIZADO) is True and r["content"] == T.texto_do_titular_autorizado({})
    assert r["data"] == base["resposta"]["data"] and r["policy_response_contract"] is None
    # CONTROLE: pedir DADO continua cortado
    cen_dado = {"roteiro": {"falas_fixas": [[f"me passa a apolice do meu pai, o cpf dele é {CPF_DO_PAI}"]]}}
    r2 = B._corte_de_terceiro(cen_dado, copy.deepcopy(base), {"documento": CPF_DO_PAI})["resposta"]
    assert r2["content"] == T.TEXTO_DA_APOLICE_DE_TERCEIRO
