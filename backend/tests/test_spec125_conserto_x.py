# -*- coding: utf-8 -*-
"""SPEC-125 · CONSERTO ÚNICO · parte X — a segurança do dado.

Os laudos do juiz (B2/B3/B4) e do red team (B1/B2, P2, P6) reproduziram, no motor
real, cinco caminhos por onde o dado escapava ou o titular era barrado. Cada um tem
aqui o MOTOR de produção (§9.4), uma LINHA DE CONTROLE (§9.2) e um guarda que fica
VERMELHO quando o conserto é desfeito (§9.3/§9.5). Sem rede, sem banco, sem LLM.
Dados 100 % fictícios (CPF com dígito verificador válido; nenhuma corretora real).

  X1  dado de terceiro pela exceção "autorizado" — cobertura nunca é serviço; nada da
      apólice chega ao modelo, com a POLICY_INTELLIGENCE_V2 LIGADA ou DESLIGADA
  X2  "o que já sabemos" só oferece o CPF que ele disse como SEU; o de assunto anterior
      vai mascarado até ele confirmar; o fiscal não empurra CPF de terceiro; T19 na SAÍDA
  X3  o critério do nome não barra o titular ("aqui é o seguinte", apelido, nome do meio)
  X4  o prompt (e o CPF do bloco) fora do checkpoint
  X5  o v2 devolveu "ou não há saída" e a escalada quando a ferramenta falha
  X6  a frase contraditória do prompt do BANCO sai na montagem do v2; o v1 fica byte a byte
  C8/C11 (rodada DEPOIS) irritação sozinha não chama pessoa; o nome do telefone chega à fala
"""
from __future__ import annotations

import asyncio
import json
import pickle

import pytest

from app.agents import nodes as N
from app.agents import quem_e_o_segurado as Q
from app.agents.tools import infocap_tool as T
from app.core import prompts as P

from tests.test_spec125_s8a_apolice_de_terceiro import (  # noqa: F401 — a borda é fixture
    APOLICE, CPF_DA_MAE, CPF_DO_FILHO, DADOS_DA_APOLICE, _consultar, borda)

CPF = CPF_DA_MAE                     # "52998224725" — fictício, DV válido
CPF_FMT = "529.982.247-25"


def _o_que_o_modelo_le(r: dict) -> str:
    """O texto que o `tool_node` entrega ao MODELO (a função de produção)."""
    return N._conteudo_da_consulta_para_o_modelo(r).lower()


def _dados_no(texto: str) -> list:
    return [d for d in DADOS_DA_APOLICE if d.lower() in texto.lower()]


# =========================================================================== #
# X1 — a exceção "autorizado" não abre a apólice de outra pessoa (RT B1)
# =========================================================================== #
COBERTURA_DA_MAE = [f"minha mãe pediu pra eu ver se o seguro dela cobre vidro, o cpf dela é {CPF}"]


@pytest.mark.parametrize("flag", ["true", "false"])
def test_x1_cobertura_da_mae_e_corte_total_com_a_flag_ligada_e_desligada(borda, monkeypatch, flag):
    monkeypatch.setenv("POLICY_INTELLIGENCE_V2", flag)
    r = _consultar(CPF, COBERTURA_DA_MAE)
    le = _o_que_o_modelo_le(r)
    assert r.get("titular_e_outra_pessoa") is True
    assert _dados_no(le) == [] and _dados_no(json.dumps(r, default=str)) == []
    # nem o resumo "apólice localizada (ramo auto), valendo hoje"
    for palavra in ("localizada", "valendo", "ramo auto", "vigente"):
        assert palavra not in le, palavra


@pytest.mark.parametrize("flag", ["true", "false"])
def test_x1_CONTROLE_o_titular_le_os_dados_dele(borda, monkeypatch, flag):
    """§9.3: o MESMO caminho CONSEGUE entregar os dados — o corte não é cegueira."""
    monkeypatch.setenv("POLICY_INTELLIGENCE_V2", flag)
    r = _consultar(CPF, ["meu carro quebrou, o meu seguro cobre vidro?", f"meu cpf é {CPF}"])
    assert not r.get("titular_e_outra_pessoa")
    assert _dados_no(_o_que_o_modelo_le(r)), "o controle tem de mostrar os dados ao titular"


@pytest.mark.parametrize("flag", ["true", "false"])
def test_x1_a_excecao_legitima_nunca_serializa_a_apolice_ao_modelo(borda, monkeypatch, flag):
    """Titular junto pedindo SERVIÇO: o `data` fica (o acionamento acha a apólice), mas o
    modelo lê só o texto — com a flag DESLIGADA o `json.dumps` do `data` ia inteiro."""
    monkeypatch.setenv("POLICY_INTELLIGENCE_V2", flag)
    r = _consultar(CPF, ["meu carro quebrou na estrada, preciso de guincho",
                         f"o carro é da minha mae, cpf dela {CPF}",
                         "ela esta aqui comigo e pediu pra eu chamar"])
    assert r.get(T.MARCA_DO_TITULAR_AUTORIZADO) is True
    assert r["data"]["selected"]["policy_number"] == APOLICE
    le = _o_que_o_modelo_le(r)
    assert "pode acionar" in le and _dados_no(le) == []


def test_x1_MUTACAO_sem_a_regra_da_pergunta_de_dado_a_mae_vaza(borda, monkeypatch):
    """Desfazer X1 (a pergunta de cobertura volta a valer como serviço) → VERMELHO."""
    import re

    monkeypatch.setenv("POLICY_INTELLIGENCE_V2", "false")
    monkeypatch.setattr(T, "_RX_PERGUNTA_DE_DADO", re.compile(r"(?!x)x"))
    monkeypatch.setattr(T, "MARCAS_DE_APOLICE_DE_OUTRA_PESSOA", ("titular_e_outra_pessoa",))
    r = _consultar(CPF, COBERTURA_DA_MAE)
    assert _dados_no(_o_que_o_modelo_le(r)), "sem o conserto, os dados da mãe chegam ao modelo"


_MAE_JUNTO = [f"o carro é da minha mae, cpf dela {CPF}", "ela esta aqui comigo e pediu pra eu chamar"]


@pytest.mark.parametrize("fala,autorizado", [
    ("preciso de guincho, quanto tempo demora?", True),         # pergunta do SERVIÇO
    ("o carro parou a 5 km daqui, manda o guincho", True),
    ("manda o guincho, ela quer saber se cobre 200 km", False),  # pergunta de COBERTURA
    ("guincho: vê se a franquia é alta", False),
])
def test_x1_a_regra_pura_da_excecao_servico_versus_dado(fala, autorizado):
    r = T.de_quem_e_a_apolice(CPF, _MAE_JUNTO + [fala])
    assert r["terceiro"] is True and r["autorizado"] is autorizado, r


@pytest.mark.parametrize("fala", [
    f"o cpf da mãe é {CPF}",                                 # sem possessivo
    f"o seguro da mamãe, cpf {CPF}",                         # carinhoso
    f"quero saber a apólice do joão, cpf {CPF}",             # sem parentesco
    f"o cpf do meu sócio é {CPF}",
])
def test_x1_terceiro_sem_possessivo_ou_sem_parentesco(fala):
    assert T.de_quem_e_a_apolice(CPF, [fala])["terceiro"] is True


@pytest.mark.parametrize("fala", [
    f"o seguro do gol venceu? cpf {CPF}",                    # o carro, não gente
    f"a apólice do carro tá valendo? cpf {CPF}",
    f"a apolice da porto cobre guincho? cpf {CPF}",
    f"o meu cpf é {CPF}, a apólice do joão eu vejo depois",  # "meu cpf" na mensagem do documento
])
def test_x1_CONTROLE_coisa_nao_e_gente_e_meu_cpf_vence(fala):
    assert T.de_quem_e_a_apolice(CPF, [fala])["terceiro"] is False


# =========================================================================== #
# X2 — "o que já sabemos" só o CPF DELE; anterior mascarado; o fiscal; T19 na saída
# =========================================================================== #
ANTES = "2026-07-01T10:00:00+00:00"
DEPOIS = "2026-10-02T10:00:00+00:00"


def _h(*linhas):
    return [{"role": r, "content": c, "created_at": q} for r, c, q in linhas]


def test_x2_o_cpf_que_ele_disse_ser_da_mae_nunca_volta_como_dele():
    """RT B2: 01/07 "o cpf dela é X" (da mãe) → 02/10 "preciso de guincho"."""
    quem = Q.montar(historico=_h(("user", f"o carro da minha mãe quebrou, o cpf dela é {CPF}", ANTES),
                                 ("user", "oi, preciso de guincho", DEPOIS)), n_dias=7)
    bloco = Q.bloco_para_o_prompt(quem)
    assert quem["cpf"] == "" and quem["cpf_final"] == "" and quem["perguntar_cpf"] is True
    assert CPF not in bloco and "4725" not in bloco


def test_x2_nem_no_mesmo_assunto_nem_com_outro_dele_junto():
    hist = _h(("user", f"meu cpf é {CPF_DO_FILHO}", DEPOIS),
              ("user", f"ah, o titular é meu pai, CPF {CPF}", DEPOIS))
    quem = Q.montar(historico=hist, n_dias=7)
    assert quem["cpf"] == CPF_DO_FILHO and quem["cpfs_distintos"] == 1
    assert CPF not in Q.bloco_para_o_prompt(quem)


def test_x2_o_dele_de_assunto_anterior_vai_so_com_o_final_e_manda_confirmar():
    quem = Q.montar(historico=_h(("user", f"meu cpf é {CPF}", ANTES),
                                 ("user", "oi, preciso de guincho", DEPOIS)), n_dias=7)
    bloco = Q.bloco_para_o_prompt(quem)
    assert quem["cpf"] == "" and quem["cpf_final"] == "4725" and quem["perguntar_cpf"] is False
    assert CPF not in bloco and "final 4725" in bloco and "confirme" in bloco


def test_x2_depois_do_sim_no_assunto_atual_o_numero_entra_inteiro():
    hist = _h(("user", f"meu cpf é {CPF}", ANTES), ("user", "oi, preciso de guincho", DEPOIS),
              ("assistant", "Claro! É o CPF final 4725?", DEPOIS), ("user", "sim, é esse", DEPOIS))
    quem = Q.montar(historico=hist, n_dias=7)
    assert quem["cpf"] == CPF and CPF in Q.bloco_para_o_prompt(quem)


@pytest.mark.parametrize("resposta", ["não, esse era da minha esposa", "outro"])
def test_x2_CONTROLE_sem_o_sim_continua_mascarado(resposta):
    hist = _h(("user", f"meu cpf é {CPF}", ANTES), ("user", "oi, preciso de guincho", DEPOIS),
              ("assistant", "É o CPF final 4725?", DEPOIS), ("user", resposta, DEPOIS))
    assert CPF not in Q.bloco_para_o_prompt(Q.montar(historico=hist, n_dias=7))


def test_x2_CONTROLE_o_cpf_dito_neste_assunto_vai_inteiro_para_as_ferramentas():
    quem = Q.montar(historico=_h(("user", f"preciso de guincho, cpf {CPF_FMT}", DEPOIS)), n_dias=7)
    bloco = Q.bloco_para_o_prompt(quem)
    assert quem["cpf"] == CPF and CPF in bloco and 'a ele, só "final 4725"' in bloco


def test_x2_o_fiscal_nao_conta_o_cpf_da_mae_como_ja_dito():
    from langchain_core.messages import HumanMessage

    mae = {"messages": [HumanMessage(content=f"o cpf da minha mãe é {CPF}, ela precisa de guincho")],
           "dynamic_context": ""}
    dele = {"messages": [HumanMessage(content=f"meu cpf é {CPF}")], "dynamic_context": ""}
    assert N._documentos_ja_ditos(mae) == []
    assert N._documentos_ja_ditos(dele) == [CPF]                    # CONTROLE


def test_x2_o_fiscal_nao_empurra_o_cpf_da_mae_no_turno(monkeypatch):
    """Motor real (`agent_node` + modelo dublê): "o SEU cpf?" depois do CPF da mãe NÃO é
    pergunta repetida — sem regeneração (antes: regenerava mandando usar o número dela)."""
    from langchain_core.messages import HumanMessage

    from tests.test_spec125_s4_prompt_v2 import CONFIRMA, REPERGUNTA, _turno

    conversa = [HumanMessage(content=f"o cpf da minha mãe é {CPF}"),
                HumanMessage(content="o carro dela quebrou")]
    modelo, texto, *_ = _turno(conversa, [REPERGUNTA, CONFIRMA], monkeypatch=monkeypatch)
    assert len(modelo.chamadas) == 1 and texto == REPERGUNTA


def test_x2_o_fiscal_com_o_cpf_anterior_manda_confirmar_o_final(monkeypatch):
    from langchain_core.messages import HumanMessage

    from tests.test_spec125_s4_prompt_v2 import CONFIRMA, REPERGUNTA, _turno

    bloco = Q.bloco_para_o_prompt({"cpf": "", "cpf_final": "4725", "cpfs_distintos": 1,
                                   "cpf_de_assunto_anterior": True})
    modelo, texto, *_ = _turno([HumanMessage(content="oi, preciso de chaveiro")], [REPERGUNTA, CONFIRMA],
                               dynamic="\n\n" + bloco, monkeypatch=monkeypatch)
    aviso = str(modelo.chamadas[1][-1].content)
    assert texto == CONFIRMA and "final 4725" in aviso and "confirme" in aviso and CPF not in aviso


@pytest.mark.parametrize("entrada,esperado", [
    (f"Confirmei o CPF {CPF_FMT} aqui.", "Confirmei o CPF final 4725 aqui."),
    (f"cpf {CPF} ok", "cpf final 4725 ok"),
    ("seu cnpj 11.222.333/0001-81", "seu cnpj final 0181"),
    (f"{CPF_FMT} e 111.444.777-35", "final 4725 e final 7735"),
])
def test_x2_t19_a_saida_mascara_todo_documento_valido(entrada, esperado):
    assert Q.mascarar_documentos_na_saida(entrada) == esperado


@pytest.mark.parametrize("texto", [
    "ligue no telefone (11) 98765-4321",
    f"seu protocolo é {CPF}",                        # rotulado: protocolo sai EXATO (T6)
    "o técnico liga do 11987654321",
    "número 12345678901 não fecha o dígito",
    "a placa ABC1D23 e o renavam 12345678900",
])
def test_x2_t19_CONTROLE_telefone_protocolo_e_numero_qualquer_saem_exatos(texto):
    assert Q.mascarar_documentos_na_saida(texto) == texto


def test_x2_t19_o_agent_node_mascara_a_resposta_ao_segurado(monkeypatch):
    from langchain_core.messages import HumanMessage

    from tests.test_spec125_s4_prompt_v2 import _turno

    _m, texto, *_ = _turno([HumanMessage(content="oi")], [f"Prontinho! Confirmei o CPF {CPF_FMT}."],
                           monkeypatch=monkeypatch)
    assert CPF_FMT not in texto and "final 4725" in texto


def test_x2_t19_CONTROLE_o_corretor_no_chat_principal_ve_o_numero(monkeypatch):
    estado = {"agent_data": {"agent_role": "core"}}
    assert N._sem_documento_inteiro(f"CPF {CPF_FMT}", estado) == f"CPF {CPF_FMT}"
    assert N._sem_documento_inteiro(f"CPF {CPF_FMT}", {"agent_data": {"agent_role": "attendance"}}) \
        == "CPF final 4725"


def test_x2_t19_MUTACAO_sem_o_filtro_de_saida_o_cpf_sai_inteiro(monkeypatch):
    from langchain_core.messages import HumanMessage

    from tests.test_spec125_s4_prompt_v2 import _turno

    monkeypatch.setattr(N, "_sem_documento_inteiro", lambda texto, state: texto)
    _m, texto, *_ = _turno([HumanMessage(content="oi")], [f"Confirmei o CPF {CPF_FMT}."],
                           monkeypatch=monkeypatch)
    assert CPF_FMT in texto, "sem o filtro, o guarda de cima ficaria vermelho"


# =========================================================================== #
# X3 — o nome não barra o titular (juiz B3)
# =========================================================================== #
@pytest.mark.parametrize("falas,titular", [
    (["aqui é o seguinte, meu carro não liga", f"meu cpf é {CPF}"], "J*** B***"),
    (["aqui é a minha mãe falando, ela quer guincho", f"cpf {CPF}"], "J*** B***"),
    (["aqui é a portaria do prédio", f"cpf {CPF}"], "J*** B***"),
    (["oi, me chamo Zé", f"cpf {CPF}"], "J*** B***"),
    (["oi, me chamo José, mas todo mundo me chama de Zé", f"cpf {CPF}"], "J*** B***"),
    (["oi, me chamo Chico", f"cpf {CPF}"], "F*** B***"),
    (["meu nome é Carlos", f"cpf {CPF}"], "J*** C*** B***"),       # o nome do meio é dele
    ([f"o carro é da minha esposa mas o seguro é meu, cpf {CPF}"], "J*** B***"),
    (["meu nome é Pedro e sou o titular", f"cpf {CPF}"], "M*** E***"),
])
def test_x3_o_titular_nao_vira_terceiro(falas, titular):
    r = T.de_quem_e_a_apolice(CPF, falas, inicial_do_titular=titular)
    assert r["terceiro"] is False, r


@pytest.mark.parametrize("falas,titular", [
    (["oi, meu nome é Pedro", CPF], "M*** E***"),                  # o nome dito, de outra inicial
    (["o carro esta no nome da minha esposa", CPF], ""),           # o bem é dela, sem "o seguro é meu"
    ([f"nao sou o titular, o cpf é {CPF}"], ""),
])
def test_x3_CONTROLE_os_sinais_de_verdade_continuam_valendo(falas, titular):
    assert T.de_quem_e_a_apolice(CPF, falas, inicial_do_titular=titular)["terceiro"] is True


@pytest.mark.parametrize("texto", ["aqui é o seguinte, meu carro quebrou", "aqui e o problema: nao liga",
                                   "aqui é a minha mãe falando", "aqui é o carro da minha esposa",
                                   "aqui é a portaria"])
def test_x3_nao_nomes_nao_viram_nome(texto):
    assert Q.nome_dito(texto) == "" and Q.nome_dito_como_nome(texto) == ""


def test_x3_CONTROLE_nomes_de_verdade_continuam(monkeypatch):
    assert Q.nome_dito("me chamo joão") == "João"
    assert Q.nome_dito("Sou o João, o carro quebrou") == "João"         # RT P12: S maiúsculo
    assert Q.nome_dito_como_nome("Sou o João") == ""                    # forma fraca não decide


def test_x3_MUTACAO_a_regua_antiga_do_nome_barra_o_titular(monkeypatch):
    """Desfazer X3 (qualquer "aqui é o X" vira nome, e a inicial só da 1ª palavra) → VERMELHO."""
    import app.agents.quem_e_o_segurado as QQ

    monkeypatch.setattr(QQ, "nome_dito_como_nome", lambda t: "Seguinte" if "seguinte" in str(t) else "")
    r = T.de_quem_e_a_apolice(CPF, ["aqui é o seguinte, meu carro não liga", f"cpf {CPF}"],
                              inicial_do_titular="J*** P***")
    assert r["terceiro"] is True


# =========================================================================== #
# X4 — o prompt (e o CPF) fora do checkpoint (juiz B4 · D1)
# =========================================================================== #
SEGREDO = f"PROMPT-DO-TURNO com o bloco · CPF {CPF} · fim"


def _grafo_real_com_checkpoint(monkeypatch):
    """`agent_node` REAL num StateGraph(AgentState) com checkpointer em memória."""
    from functools import partial

    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.graph import END, START, StateGraph

    import app.services.activity_log as AL
    from app.agents.state import AgentState
    from tests.test_spec125_s4_prompt_v2 import _Modelo

    async def _log(*_a, **_k):
        return None

    monkeypatch.setattr(AL, "log_activity", _log)
    monkeypatch.setattr(N, "_registrar_julgamento_no_diario", lambda *a, **k: None)
    monkeypatch.setattr(N, "_marcar_erro_leve_no_diario", lambda *a, **k: None)
    modelo = _Modelo(["Certo, já vou ver."])
    wf = StateGraph(AgentState)
    wf.add_node("agent", partial(N.agent_node, llm_with_tools=modelo))
    wf.add_edge(START, "agent")
    wf.add_edge("agent", END)
    saver = InMemorySaver()
    return wf.compile(checkpointer=saver), saver, modelo


def _estado_inicial():
    from langchain_core.messages import HumanMessage

    return {"messages": [HumanMessage(content="oi")], "company_id": "c", "user_id": "u",
            "session_id": "s", "company_config": {}, "agent_data": {"agent_role": "attendance"},
            "system_prompt": SEGREDO, "static_prompt": SEGREDO, "dynamic_context": SEGREDO,
            "tools_used": [], "rag_chunks": []}


def _gravado(saver) -> bytes:
    return pickle.dumps((dict(saver.storage), dict(saver.writes), dict(saver.blobs)))


def test_x4_o_checkpoint_nao_guarda_o_prompt_nem_o_cpf_e_o_modelo_le_o_prompt(monkeypatch):
    from app.agents import graph as G

    app, saver, modelo = _grafo_real_com_checkpoint(monkeypatch)
    entrada, cfg = G.entrada_sem_o_prompt(_estado_inicial(), {"configurable": {"thread_id": "c:s"}})
    asyncio.run(app.ainvoke(entrada, cfg))
    # o modelo LEU o prompt do turno (o system da chamada)
    assert SEGREDO in str(modelo.chamadas[0][0].content)
    # e nada dele ficou gravado: nem o texto, nem o CPF
    gravado = _gravado(saver)
    assert SEGREDO.encode() not in gravado and CPF.encode() not in gravado
    # o `repr` do portador não mostra o prompt (log/trace)
    assert SEGREDO not in repr(cfg["configurable"][N.CHAVE_DO_PROMPT_DO_TURNO])


def test_x4_CONTROLE_com_o_prompt_na_entrada_ele_vai_ao_checkpoint(monkeypatch):
    """§9.3: o guarda acima CONSEGUE falhar — é o que o produto fazia em f28c4a5."""
    app, saver, _m = _grafo_real_com_checkpoint(monkeypatch)
    asyncio.run(app.ainvoke(_estado_inicial(), {"configurable": {"thread_id": "c:s"}}))
    assert SEGREDO.encode() in _gravado(saver)


def test_x4_um_checkpoint_antigo_com_prompt_e_sobrescrito_por_nada(monkeypatch):
    from app.agents import graph as G

    app, saver, _m = _grafo_real_com_checkpoint(monkeypatch)
    cfg0 = {"configurable": {"thread_id": "c:s"}}
    asyncio.run(app.ainvoke(_estado_inicial(), cfg0))                   # o turno de ANTES do conserto
    entrada, cfg = G.entrada_sem_o_prompt(_estado_inicial(), cfg0)
    asyncio.run(app.ainvoke(entrada, cfg))
    valores = asyncio.run(app.aget_state(cfg0)).values
    assert all(valores.get(k) is None for k in N.CAMPOS_DO_PROMPT_DO_TURNO)


def test_x4_o_produto_invoca_o_grafo_pela_entrada_sem_o_prompt():
    """As duas portas de produção (`invoke_agent` e o stream) passam por `entrada_sem_o_prompt`."""
    import inspect

    from app.agents import graph as G

    fonte = inspect.getsource(G)
    assert "graph.ainvoke(initial_state" not in fonte
    assert "_entrada, config = entrada_sem_o_prompt(initial_state, config)" in fonte
    assert "estado_da_volta, config = entrada_sem_o_prompt(initial_state, config)" in fonte


def test_x4_sem_o_portador_o_estado_vale_como_veio():
    """A bancada e os testes que montam o estado na mão continuam funcionando."""
    estado = {"system_prompt": "x"}
    assert N.com_o_prompt_do_turno(estado, None) is estado
    assert N.com_o_prompt_do_turno(estado, {"configurable": {}}) is estado


# =========================================================================== #
# X5 + C8 — a escalada que o v2 tinha cortado; irritação sozinha não é motivo
# =========================================================================== #
def test_x5_o_v2_devolveu_o_nao_ha_saida_e_a_escalada_da_falha():
    v2 = P.ATTENDANCE_BASE_PROMPT_V2
    for ancora in ("ou não há saída (a ferramenta falhou de novo)",
                   "corrija o dado ou chame a equipe",
                   "a equipe com o dossiê",
                   "Irritação sozinha NÃO é motivo"):
        assert ancora in v2, ancora
    assert "irritado E pedindo saída" in v2                            # o afrouxamento autorizado (D6)


# =========================================================================== #
# X6 — a frase contraditória do BANCO sai no v2; o v1 fica byte a byte
# =========================================================================== #
DO_BANCO = "Atenda com calma; colete uma informacao por vez; seja cordial."


def test_x6_no_v2_a_frase_do_banco_vira_a_regra_unica():
    v2 = P.build_composite_prompt(DO_BANCO, agent_role="attendance", prompt_versao="v2")
    assert "uma informacao por vez" not in v2
    assert P.FRASE_NOVA_DO_MOLDE in v2 and "Atenda com calma;" in v2 and "seja cordial." in v2


def test_x6_CONTROLE_no_v1_e_no_core_nada_muda():
    v1 = P.build_composite_prompt(DO_BANCO, agent_role="attendance", prompt_versao="v1")
    assert "colete uma informacao por vez" in v1 and P.FRASE_NOVA_DO_MOLDE not in v1
    core = P.build_composite_prompt(DO_BANCO, agent_role="core", prompt_versao="v2")
    assert "colete uma informacao por vez" in core


def test_x6_no_v1_a_montagem_com_a_frase_e_a_do_commit_base():
    from tests.test_spec125_s4_prompt_v2 import _prompts_do_commit_base

    base = _prompts_do_commit_base()
    if base is None:
        pytest.skip("git indisponível")
    assert P.build_composite_prompt(DO_BANCO, agent_role="attendance", prompt_versao="v1") \
        == base.build_composite_prompt(DO_BANCO, agent_role="attendance")


def test_x6_a_parte_b_da_migration_esta_descartada_e_nao_executa():
    import os
    import re

    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "supabase", "migrations", "20261001_07_spec125_prompt_v2.sql")
    with open(caminho, encoding="utf-8") as fh:
        sql = fh.read()
    assert "DESCARTADA" in sql
    vivo = "\n".join(l for l in sql.split("\n") if not l.strip().startswith("--"))
    assert not re.search(r"set\s+agent_system_prompt", vivo, re.I), "nenhum UPDATE do prompt executa"


# =========================================================================== #
# C11 — o nome do telefone chega à linha de TRATAMENTO, para confirmar
# =========================================================================== #
_BLOCO_SEM_NOME = ("=== 🪪 QUEM FALA NESTE TURNO ===\nAPRESENTAÇÃO: x\n"
                   "TRATAMENTO: ⛔ você NÃO sabe o nome de quem está falando neste atendimento. "
                   "Não use nenhum nome que apareça na memória — pergunte, ou fale sem nome.\n"
                   "QUEM VAI ATENDER: y")


def test_c11_o_nome_do_telefone_vira_nome_provavel_a_confirmar():
    from app.agents import graph as G

    novo = G.tratamento_com_o_nome_provavel(_BLOCO_SEM_NOME, {"nome": "Ana", "nome_origem": "contato do WhatsApp"})
    linha = next(l for l in novo.split("\n") if l.startswith("TRATAMENTO"))
    assert "**Ana**" in linha and "Falo com Ana?" in linha and "NÃO sabe" not in linha
    assert novo.split("\n")[1] == "APRESENTAÇÃO: x" and novo.endswith("QUEM VAI ATENDER: y")


def test_c11_CONTROLE_sem_nome_ou_com_a_ficha_sabendo_nada_muda():
    from app.agents import graph as G

    assert G.tratamento_com_o_nome_provavel(_BLOCO_SEM_NOME, {}) == _BLOCO_SEM_NOME
    da_ficha = _BLOCO_SEM_NOME.replace(
        _BLOCO_SEM_NOME.split("\n")[2], "TRATAMENTO: chame o segurado de **Bruno** — é o nome DESTE atendimento.")
    assert G.tratamento_com_o_nome_provavel(da_ficha, {"nome": "Ana"}) == da_ficha


def test_c11_o_graph_passa_o_nome_do_telefone_para_a_linha():
    import inspect

    from app.agents import graph as G

    assert "_bloco_quem_fala = tratamento_com_o_nome_provavel(_bloco_quem_fala, _quem)" in inspect.getsource(G)
