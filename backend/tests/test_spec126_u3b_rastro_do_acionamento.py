# -*- coding: utf-8 -*-
"""SPEC-126 U3-B · D2 — o ACIONAMENTO também conta para "o mesmo celular, muitas apólices".

A U3 deixou o rastro só na CONSULTA (`infocap_tool._rastrear_a_consulta`). Sem o do
acionamento, quem acionasse três apólices sem consultar passava pela D2. Pelo MOTOR:
`nodes.tool_node` REAL → `_rastro_do_acionamento` → `consultas_por_telefone` REAL →
`invocation_recorder` REAL grava `tool_invocations` → a porta única do grupo REAL. Dublês
só na BORDA: a ferramenta de acionamento (o canal com a seguradora), provedor, banco,
Redis, destino e canal do grupo. 🔴 Dois tenants REAIS com o mesmo telefone.
"""
from __future__ import annotations

import asyncio
import json

from langchain_core.messages import AIMessage, HumanMessage

from app.agents import nodes as N
from app.atendimento import consultas_por_telefone as CT
from app.services.policy_context import construir_policy_context
from tests.test_spec126_u3_d1_parente_aciona import (  # noqa: F401 — a borda é fixture
    EMPRESA_A, EMPRESA_B, SESSAO_A, SESSAO_B, borda, consultar_pelo_motor, estado, resultado_found)
from tests.test_spec126_u3_d2_consultas_por_telefone import APOLICES, CPFS, grupo  # noqa: F401


class _Dispatch:
    """A BORDA do acionamento: o canal com a seguradora. Devolve o que a ferramenta real
    devolve quando o acionamento sai (`insurer_dispatch_tool._arun`, status `dispatched`)."""

    name, exige_async = "insurer_dispatch", True

    def __init__(self, status="dispatched"):
        self.status = status

    async def _arun(self, **_kw):
        return {"status": self.status, "content": "[ACIONAMENTO REAL INICIADO]\nSERVIÇO ACIONADO: guincho"}


def acionar(i: int, *, empresa=EMPRESA_A, sessao=SESSAO_A, contexto=None, status="dispatched") -> dict:
    """UM turno de acionamento da i-ésima apólice, com o contexto da apólice no estado."""
    ctx = contexto or construir_policy_context(resultado_found(APOLICES[i]), company_id=empresa)
    st = estado([HumanMessage(content="pode mandar"), AIMessage(content="", tool_calls=[{
        "name": "insurer_dispatch", "id": "call-a%d" % i,
        "args": {"subservice": "guincho", "titular_cpf": CPFS[i], "dados_confirmados": True}}])],
        empresa=empresa, sessao=sessao)
    st["infocap_policy_context"] = ctx
    return asyncio.run(N.tool_node(st, tools=[_Dispatch(status)]))


def _rastros(banco, empresa):
    return [(l.get("output_summary") or {}).get(CT.CHAVE_DO_RASTRO)
            for l in banco.tabelas.get("tool_invocations", []) if l.get("company_id") == empresa]


def test_o_acionamento_grava_o_rastro_e_o_modelo_nao_o_le(borda, grupo):
    banco, _ = borda
    saida = acionar(0)
    rastros = [r for r in _rastros(banco, EMPRESA_A) if r]
    assert len(rastros) == 1 and rastros[0]["apolice_final"] == APOLICES[0][-4:], rastros
    bruto = json.dumps(banco.tabelas.get("tool_invocations"), default=str)
    assert CPFS[0] not in bruto and APOLICES[0] not in bruto, "documento CRU em tool_invocations"
    # ⛔ o rastro é do RECORDER: o final da apólice não volta ao modelo pelo ToolMessage
    lido = "\n".join(str(m.content) for m in saida["messages"])
    assert CT.CHAVE_DO_RASTRO not in lido and APOLICES[0][-4:] not in lido, lido


def test_controle_acionamento_que_nao_saiu_nao_deixa_rastro(borda, grupo):
    banco, _ = borda
    acionar(0, status="missing_data")
    assert [r for r in _rastros(banco, EMPRESA_A) if r] == []


def test_consulta_minha_mais_acionamento_da_mesma_apolice_conta_uma(borda, grupo):
    """D-126-C: "meu cpf é…" + o acionamento da MESMA apólice = UMA unidade."""
    _, prov = borda
    prov.sequencia.append(resultado_found(APOLICES[0]))
    ctx = consultar_pelo_motor(["preciso de guincho", f"meu cpf é {CPFS[0]}"], CPFS[0]).get(
        "infocap_policy_context")
    acionar(0, contexto=ctx)
    linhas = asyncio.run(CT.consultas_recentes(borda[0], company_id=EMPRESA_A, telefone="5500000001260"))
    assert len(linhas) == 2, "consulta e acionamento têm de deixar rastro"
    assert CT.decidir(linhas[1:], linhas[0]["rastro"])["distintas"] == 1


def test_g4_tres_apolices_acionadas_avisam_uma_vez_o_grupo_da_dona(borda, grupo):
    acionar(0)
    acionar(1)
    assert grupo == [], "2 apólices distintas NÃO avisam (D2: mais de 2)"
    saida = acionar(2)
    assert len(grupo) == 1 and grupo[0][0] == "grupo-da-%s" % EMPRESA_A, grupo
    texto = grupo[0][1]
    assert all("final %s" % a[-4:] in texto for a in APOLICES[:3]), texto
    assert not any(c in texto for c in CPFS) and not any(a in texto for a in APOLICES)
    # ⛔ o acionamento NÃO foi bloqueado
    assert "[ACIONAMENTO REAL INICIADO]" in "\n".join(str(m.content) for m in saida["messages"])


def test_g4_consulta_e_acionamento_de_apolices_distintas_se_somam(borda, grupo):
    _, prov = borda
    for i in (0, 1):
        prov.sequencia.append(resultado_found(APOLICES[i]))
        consultar_pelo_motor(["bom dia, preciso de um guincho", CPFS[i]], CPFS[i])
    assert grupo == []
    acionar(2)
    assert len(grupo) == 1, "a 3ª apólice veio pelo ACIONAMENTO e não foi contada"


def test_g4_dois_tenants_nao_se_somam(borda, grupo):
    banco, _ = borda
    acionar(0)
    acionar(1)
    acionar(2, empresa=EMPRESA_B, sessao=SESSAO_B)
    assert grupo == [], "B somou os acionamentos de A"
    assert len([r for r in _rastros(banco, EMPRESA_B) if r]) == 1
    acionar(3)
    assert [d for d, _t in grupo] == ["grupo-da-%s" % EMPRESA_A]


def test_o_aviso_que_explode_nao_derruba_o_acionamento(borda, grupo, monkeypatch):
    async def _explode(*_a, **_k):
        raise RuntimeError("banco fora do ar")

    monkeypatch.setattr(CT, "conferir_e_avisar", _explode)
    saida = acionar(0)
    assert "[ACIONAMENTO REAL INICIADO]" in "\n".join(str(m.content) for m in saida["messages"])
