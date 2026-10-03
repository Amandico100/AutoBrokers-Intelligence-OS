# -*- coding: utf-8 -*-
"""SPEC-124 — o CONSERTO ÚNICO (juiz B1/P3 · red team B1/P1/P8). Puro: nenhum banco, nenhum modelo.

🔴 A VERDADE QUE ESTE ARQUIVO GUARDA: com o DEDUZIR desligado (sem calibração), o destravador do
portal NÃO DEDUZ NADA. (§9.3, SPEC-127 P4: até o P4 era "não responde NENHUMA parada"; agora o CÓDIGO
conduz o tipo de telefone e responde a peça que `especificos` desambigua — só o que ele PROVA.) Toda outra
parada volta ao caminho de hoje (o agente pergunta ao segurado, ou a equipe nas paradas NUNCA), com a linha
do diário dizendo o que aconteceu de fato.

C1  `uf_desconhecida` é do SEGURADO: a UF que ele escreveu não está na lista do portal; qualquer UF da
    lista seria OUTRA (a cidade homônima). E a UF só vai ao portal como SIGLA que está na LISTA.
C2  "dado do caso" no portal = o valor do CAMPO que a parada espera — nunca qualquer folha dos params.
C3  o questionário: o worker etiqueta o slot (`pergunta_<codigo>`); a resposta tem formato para ele, e o
    `pergunta` genérico (sem código, sem pergunta pendente) não tem.
C4  a linha do diário de PESSOA numa parada que o segurado responde diz que o agente PERGUNTA a ele.

💭 Todos os dados abaixo são fictícios.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents.tools import portal_params as PP  # noqa: E402
from app.services import destravador as DT  # noqa: E402

UFS = sorted(PP._UFS)
CASO = {"insurer_name": "LIBERTY SEGUROS S/A", "cpf_cnpj": "00000000000", "placa": "AAA0A00",
        "segurado": {"nome": "Fulano Ficticio"},
        "dano": {"peca": "para-brisa", "como": "pedra", "onde": "urbano"},
        "local": {"estado": "SC", "cidade": "Florianopolis",
                  "cidade_servico": {"uf": "RS", "cidade": "BOM JESUS"}, "cidade_servico_uf_de": "segurado"},
        "especificos": {"peca": "para-brisa"}}
#: a parada que o produto produz: o segurado escreveu "Bom Jesus/RS" e o portal não lista RS
PARADA_UF = {"stage": "uf_desconhecida", "operacao": "responder", "slot": "cidade_servico",
             "opcoes": [u for u in UFS if u != "RS"], "pergunta": "", "mensagem": ""}
OUTRA = {"provedor": "anthropic", "acao": "RESPONDER"}


def P(valor, classe="responder_com_dado", nota=100, acao="RESPONDER"):
    return DT.Proposta(classe=classe, acao=acao, valor=valor, nota=nota, motivo="m")


def _segunda(valor):
    return {**OUTRA, "valor": valor}


# ═════════════════════════════════════════════════════════════════════════════
# C1 — a UF é do segurado
# ═════════════════════════════════════════════════════════════════════════════
def test_C1_a_entrada_e_do_produto_a_uf_vem_escrita_e_valida():
    assert PP.cidade_do_servico_valida("Bom Jesus/RS") == ("BOM JESUS", "RS", "")
    assert PP.cidade_do_servico_valida("Bom Jesus")[2] == "uf_ausente"      # sem UF o pedido nem nasce


def test_C1_uf_desconhecida_e_perguntar_ao_segurado_na_tabela():
    assert DT.CLASSE_DA_PARADA_DO_PORTAL["uf_desconhecida"] == "perguntar_ao_segurado"


@pytest.mark.parametrize("valor", ["SC", "sc", "PR", "RS", "Santa Catarina", "FLORIANOPOLIS", "Fulano Ficticio"])
def test_C1_nenhuma_uf_vai_ao_portal_nem_a_do_cadastro_nem_com_nota_100(valor):
    d = DT.decidir_parada_do_portal(P(valor), PARADA_UF, CASO, provedor="openai", segunda_opiniao=_segunda(valor))
    assert (d.acao, d.classe, d.proibicao) == ("PERGUNTAR_AO_SEGURADO", "perguntar_ao_segurado",
                                               "so_o_segurado_sabe")
    # e o código decide SEM o modelo (a tool nem o chama)
    assert DT.decidir_parada_do_portal(None, PARADA_UF, CASO).acao == "PERGUNTAR_AO_SEGURADO"


def test_C1_reproducao_do_red_team_rt_uf_e_rt_uf2():
    """`rt_uf.py` (lista sem RS, modelo diz SC nota 5) e `rt_uf2.py` (o `GET /ufs` mudou de formato →
    lista vazia → "PEDRA", o nome do segurado…): antes RESPONDER, agora pergunta."""
    for opcoes in ([u for u in UFS if u != "RS"], [""]):
        ev = {"stage": "uf_desconhecida", "opcoes": opcoes,
              "continuacao": {"possivel": True, "acao_esperada": "responder:cidade_servico", "etapa": "cidade"}}
        parada = DT.parada_do_portal(ev)
        for valor, nota in (("SC", 5), ("Florianopolis", 1), ("PEDRA", 1), ("Fulano Ficticio", 1)):
            prop = DT.ler_destravamento(json.dumps({"classe": "responder_com_dado", "acao": "RESPONDER",
                                                    "valor": valor, "nota": nota}))
            d = DT.decidir_parada_do_portal(prop, parada, CASO, limiar=70, modo="on", provedor="openai",
                                            pedir_segunda=True)
            assert d.acao == "PERGUNTAR_AO_SEGURADO", (opcoes[:1], valor)


def test_C1_a_uf_so_sai_como_SIGLA_que_esta_na_LISTA_da_parada():
    lista = PARADA_UF["opcoes"]
    ok = {"cidade_servico": {"uf": "SC", "cidade": "BOM JESUS"}}
    assert DT.resposta_do_portal("uf_desconhecida", "cidade_servico", "sc", CASO, opcoes=lista) == ok
    # CONTROLE acima: a mesma função CONSEGUE responder; abaixo, cada recusa é pela regra certa
    assert DT.resposta_do_portal("uf_desconhecida", "cidade_servico", "SC", CASO) == {}          # sem lista
    assert DT.resposta_do_portal("uf_desconhecida", "cidade_servico", "SC", CASO, opcoes=[]) == {}
    assert DT.resposta_do_portal("uf_desconhecida", "cidade_servico", "RS", CASO, opcoes=lista) == {}  # fora
    for livre in ("FLORIANOPOLIS", "PEDRA", "Fulano Ficticio", "S C", "SCX"):
        assert DT.resposta_do_portal("uf_desconhecida", "cidade_servico", livre, CASO,
                                     opcoes=lista + [livre]) == {}, livre                    # não é sigla


#: 🔴 §9.3 — A LIÇÃO MIGROU (SPEC-127 P4). Esta guarda afirmava "o destravador do portal não responde
#: NENHUMA parada sozinho". Era verdade até o P4: agora o CÓDIGO conduz o tipo de telefone (a opção do
#: CONTRATO) e responde a peça que `especificos` desambigua — dado PROVADO, nunca deduzido. O que ela
#: protegia continua testado, mais forte: SEM CALIBRAÇÃO NADA É DEDUZIDO, e o que responde é EXATAMENTE o
#: que o código prova (nunca o valor do modelo, nunca classe `deduzir`). E a linha de CONTROLE prova que a
#: guarda consegue ver diferença: nas opções de sempre (sem prova do código), NADA responde — a de antes.
#: 💭 Caso fictício; as opções são as REAIS do portal (`tests/fixtures/vidros/`).
CASO_P4 = {**CASO, "dano": {**CASO["dano"], "peca": "lanterna"}, "contato": {"tipo_telefone": "segurado"},
           "especificos": {"peca": "lanterna", "lanterna_posicao": "da frente"}}
OPCOES_SEM_PROVA = ["SC", "Pedra", "tentar o reparo", "Sim"]
OPCOES_COM_PROVA = ["COMERCIAL", "CELULAR DO SEGURADO", "CELULAR CORRETOR", "LANTERNA DIANTEIRA CONVENCIONAL",
                    "LANTERNA TRASEIRA NEBLINA", "LANTERNA TRASEIRA BI-PARTIDA MALA LED", "Não Sabe"]
SLOTS = ("cidade_servico", "como", "peca", "pergunta_140", "aceita_reparo", "tipo_telefone")


def _decisoes(stage, opcoes, caso):
    for slot in SLOTS:
        parada = {"stage": stage, "operacao": "responder", "slot": slot, "opcoes": opcoes}
        prova = DT.dado_do_caso_no_portal(parada, caso)
        for valor in opcoes + ["aceito a franquia de R$ 300", "cancelar pedido", "123456789"]:
            for classe in ("responder_com_dado", "conduzir", "deduzir"):
                d = DT.decidir_parada_do_portal(P(valor, classe=classe), parada, caso, provedor="openai",
                                                segunda_opiniao=_segunda(valor))
                yield slot, valor, classe, prova, d


@pytest.mark.parametrize("stage", sorted(DT.CLASSE_DA_PARADA_DO_PORTAL) + ["parada_inventada"])
def test_C1_HOJE_sem_calibracao_NADA_e_deduzido_no_portal_so_responde_o_que_o_CODIGO_prova(stage):
    """DEDUZIR desligado: toda parada × a saída mais agressiva do modelo (nota 100, 2ª opinião de outro
    provedor concordando, cada classe) → o que vai ao portal é SÓ o que o código prova (P4)."""
    assert DT.DEDUZIR_AUTONOMO_CALIBRADO is False
    for slot, valor, classe, prova, d in _decisoes(stage, OPCOES_COM_PROVA, CASO_P4):
        if d.acao == "RESPONDER":
            assert d.classe in ("conduzir", "responder_com_dado") and d.classe != "deduzir", (stage, slot, d)
            assert prova and d.valor == prova and d.acao_do_modelo == "", (stage, slot, valor, classe, d.valor)
            assert d.porta_do_deduzir is False
    # CONTROLE (a guarda de antes, intacta): sem prova do código, NENHUMA parada responde
    for slot, valor, classe, _prova, d in _decisoes(stage, OPCOES_SEM_PROVA, CASO):
        assert d.acao != "RESPONDER", (stage, slot, valor, classe)


def test_C1_HOJE_CONTROLE_a_guarda_consegue_ver_diferenca():
    """§9.3 corolário: a guarda acima só guarda se o código DE FATO responde em algum lugar — o tipo de
    telefone (o contrato) e a peça (o que `especificos` desambigua). Sem isto ela seria um carimbo."""
    respondeu = {(st, d.valor) for st in ("tipo_de_telefone_desconhecido", "peca_ambigua")
                 for _s, _v, _c, _p, d in _decisoes(st, OPCOES_COM_PROVA, CASO_P4) if d.acao == "RESPONDER"}
    assert respondeu == {("tipo_de_telefone_desconhecido", "CELULAR DO SEGURADO"),
                         ("peca_ambigua", "LANTERNA DIANTEIRA CONVENCIONAL")}


# ═════════════════════════════════════════════════════════════════════════════
# C2 — o dado do caso é o do CAMPO da parada
# ═════════════════════════════════════════════════════════════════════════════
def test_C2_o_dado_do_caso_e_o_do_campo_que_a_parada_espera():
    assert DT.valores_do_slot_no_portal("uf_desconhecida", "cidade_servico", CASO) == {"rs"}   # a ESCRITA
    assert DT.valores_do_slot_no_portal("motivo_ambiguo", "como", CASO) == {"pedra"}
    assert DT.valores_do_slot_no_portal("peca_ambigua", "peca", CASO) == {DT._n("para-brisa")}
    # nem o estado do cadastro, nem o nome, nem a cidade do cadastro, nem outro campo
    tudo = set().union(*(DT.valores_do_slot_no_portal(st, sl, CASO) for st, sl in (
        ("uf_desconhecida", "cidade_servico"), ("motivo_ambiguo", "como"), ("peca_ambigua", "peca"))))
    assert not ({"sc", "fulano ficticio", "florianopolis", "urbano"} & tudo)
    # o slot que não é o da parada não lê nada
    assert DT.valores_do_slot_no_portal("motivo_ambiguo", "peca", CASO) == set()


def test_C2_qualquer_folha_dos_params_NAO_e_dado_do_caso(monkeypatch):
    """A régua do `responder_com_dado` (a tabela trocada AQUI só para exercitá-la): uma opção que é outra
    folha do caso (o `onde`) não responde; o valor do CAMPO (o `como`) responde — a linha de CONTROLE."""
    monkeypatch.setitem(DT.CLASSE_DA_PARADA_DO_PORTAL, "motivo_ambiguo", "responder_com_dado")
    parada = {"stage": "motivo_ambiguo", "operacao": "responder", "slot": "como",
              "opcoes": ["Pedra", "Urbano", "Vandalismo"]}
    folha = DT.decidir_parada_do_portal(P("Urbano"), parada, CASO, provedor="openai")
    assert folha.acao != "RESPONDER"
    controle = DT.decidir_parada_do_portal(P("Pedra"), parada, CASO, provedor="openai")
    assert (controle.acao, controle.valor) == ("RESPONDER", "Pedra")


# ═════════════════════════════════════════════════════════════════════════════
# C3 — o questionário: o slot ETIQUETADO do worker
# ═════════════════════════════════════════════════════════════════════════════
def test_C3_o_slot_do_questionario_e_o_etiquetado_e_o_generico_nao_tem_formato():
    from portal_worker.journeys import vidros_estado as ST

    assert ST.etapa_da_parada("questionario_incompleto")[1] == "responder:pergunta"   # o mapa genérico…
    assert DT.slot_da_parada_confere("questionario_incompleto", "pergunta_140")       # …que o worker etiqueta
    assert not DT.slot_da_parada_confere("questionario_incompleto", "pergunta")
    assert DT.resposta_do_portal("questionario_incompleto", "pergunta_140", "Sim", CASO) == {"pergunta_140": "Sim"}
    assert DT.resposta_do_portal("questionario_incompleto", "pergunta", "Sim", CASO) == {}
    assert DT.resposta_do_portal("motivo_ambiguo", "peca", "Pedra", CASO) == {}          # slot de outra parada


def test_C3_quando_a_calibracao_religar_o_questionario_tem_formato(monkeypatch):
    monkeypatch.setattr(DT, "DEDUZIR_AUTONOMO_CALIBRADO", True)
    base = {"stage": "questionario_incompleto", "operacao": "responder", "opcoes": ["Sim", "Não"]}
    d = DT.decidir_parada_do_portal(P("Sim", classe="deduzir", nota=95), {**base, "slot": "pergunta_140"}, CASO,
                                    provedor="openai", segunda_opiniao=_segunda("Sim"))
    assert (d.acao, d.valor) == ("RESPONDER", "Sim")
    g = DT.decidir_parada_do_portal(P("Sim", classe="deduzir", nota=95), {**base, "slot": "pergunta"}, CASO,
                                    provedor="openai", segunda_opiniao=_segunda("Sim"))
    assert g.acao == "PERGUNTAR_AO_SEGURADO" and g.proibicao == "resposta_sem_formato_ou_repetida"


# ═════════════════════════════════════════════════════════════════════════════
# C4 — o diário diz o que acontece de fato
# ═════════════════════════════════════════════════════════════════════════════
def _d(acao, modo="on", proibicao="o_modelo_chamou_uma_pessoa"):
    return DT.Destravamento(classe="deduzir", acao=acao, proibicao=proibicao, limiar=70, modo=modo,
                            gatilho="portal:x")


@pytest.mark.parametrize("stage", ["uf_desconhecida", "motivo_ambiguo", "questionario_incompleto"])
def test_C4_pessoa_numa_parada_do_segurado_e_PERGUNTA_no_diario(stage):
    parada = {"stage": stage}
    assert DT.acao_do_portal_no_diario(_d("PESSOA"), parada) == "perguntou_segurado"
    frase = DT._frase_do_portal("yelum", parada, _d("PESSOA"))
    assert "pergunta ao segurado pelo caminho de hoje" in frase and "pessoa da corretora" not in frase


def test_C4_CONTROLE_as_outras_acoes_nao_mudam():
    assert DT.acao_do_portal_no_diario(_d("PESSOA"), {"stage": "coverage_absent"}) == "chamou_pessoa"
    assert "pessoa da corretora" in DT._frase_do_portal("yelum", {"stage": "coverage_absent"}, _d("PESSOA"))
    assert DT.acao_do_portal_no_diario(_d("PESSOA", modo="sombra"), {"stage": "motivo_ambiguo"}) == "nao_agiu"
    assert DT.acao_do_portal_no_diario(_d("RESPONDER"), {"stage": "motivo_ambiguo"}) == "respondeu_portal"
    assert DT.acao_do_portal_no_diario(_d("PERGUNTAR_AO_SEGURADO"), {"stage": "x"}) == "perguntou_segurado"


def test_C4_pelo_destravador_a_saida_invalida_vira_pergunta_no_diario(monkeypatch):
    """O caminho inteiro de `destravar_parada_do_portal` (DEDUZIR ligado só aqui, para o modelo ser chamado):
    o modelo devolve lixo → PESSOA → a tool segue o caminho de hoje (pergunta) → o diário diz isso."""
    from app.services import diario_de_decisoes as DD

    monkeypatch.setattr(DT, "DEDUZIR_AUTONOMO_CALIBRADO", True)
    linhas = []

    async def _registrar(**k):
        linhas.append(k)
        return "diario-1"

    async def _vazio(*_a, **_k):
        return []

    class _Lixo:
        async def ainvoke(self, _m):
            from langchain_core.messages import AIMessage

            return AIMessage(content="isto não é json")

    monkeypatch.setattr(DD, "registrar_decisao", _registrar)
    monkeypatch.setattr(DT, "_conversa_do_segurado", _vazio)
    monkeypatch.setattr(DT, "_memoria_da_corretora", _vazio)
    ev = {"stage": "motivo_ambiguo", "opcoes": ["Pedra", "Vandalismo"],
          "continuacao": {"possivel": True, "acao_esperada": "responder:como", "etapa": "causa"}}
    d = asyncio.run(DT.destravar_parada_do_portal(
        "aaaaaaaa-0000-4000-8000-0000000124a1", ev, CASO, modo="on", job_id="job-1",
        llm=DT.ModeloInjetado(llm=_Lixo(), provedor="openai", modelo="dublê")))
    assert d.acao == "PESSOA" and d.proibicao.startswith("saida_invalida")
    assert [k["acao"] for k in linhas] == ["perguntou_segurado"]
    assert "pergunta ao segurado pelo caminho de hoje" in linhas[0]["explicacao_para_gente"]
