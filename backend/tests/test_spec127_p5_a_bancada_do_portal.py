# -*- coding: utf-8 -*-
"""SPEC-127 P5 — a BANCADA do DEDUZIR do portal: o corpus (gabarito da atendente, escrito ANTES) e a régua.

Grátis: dublês na borda do modelo; o motor é o do produto (`destravador.destravar_parada_do_portal`, §9.4).

P5-a  o corpus: sem PII nas falas; a resposta do gabarito é UMA opção da lista; a contagem declarada é a do
      arquivo; e cada parada NASCE pelo motor de hoje (o worker não a resolve — senão não seria parada).
P5-b  o motor da bancada É o do produto, e as bordas trocadas voltam ao fim (nenhum banco tocado).
P5-c  a régua (a MESMA da SPEC-126 U6): o CONTROLE ("a 1ª opção") não religa; o dublê perfeito religa só onde
      n ≥ 10 (Yelum) e não onde n < 10 (Porto) — sem a prova, a autonomia do portal continua 0.
G6    "Curitibanos" nunca por "Curitiba" (e as outras armadilhas de lugar) — nem calibrado, nem com as DUAS
      opiniões concordando; "Não sabe" nunca sai do destravador.
P5-d  o SQL de religar é da linha `vidros` (nunca liga a URA pela calibração do portal).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import destravador as DT  # noqa: E402
from app.services import diario_de_decisoes as DD  # noqa: E402
from app.services.evals import bancada_portal as BP  # noqa: E402
from portal_worker.journeys import vidros_apifirst as AF  # noqa: E402
from portal_worker.journeys import vidros_questionario as QZ  # noqa: E402

CASOS = BP.carregar_casos()
#: 📊 a contagem DECLARADA no relatório da SPEC-127 (o corpus de 03/10, `p5_corpus.py`)
CONTAGEM = {"yelum": {"peca": 7, "causa": 11, "questionario": 7, "cidade": 6, "lataria": 2, "responder": 26},
            "porto": {"peca": 2, "causa": 3, "cidade": 6, "responder": 5}}
CALIBRAVEIS = [c for c in CASOS if c["tipo"] != "cidade"]


# ═════════════════════════════════════════════════════════════════════════════
# P5-a — o corpus
# ═════════════════════════════════════════════════════════════════════════════
def test_a_contagem_declarada_e_a_do_arquivo():
    assert BP.contagem(CASOS) == CONTAGEM


def test_o_corpus_nao_tem_PII_e_o_gabarito_e_uma_opcao_da_lista():
    assert {c["id"]: BP.pii_do_caso(c) for c in CASOS if BP.pii_do_caso(c)} == {}
    for c in CASOS:
        g = c["gabarito"]
        assert g["acao"] in ("RESPONDER", "PERGUNTAR")
        if g["acao"] == "RESPONDER":
            assert g["resposta"] in c["parada"]["opcoes"], c["id"]
            assert "HAR" in c["fonte"]                            # a escolha da ATENDENTE, não a nossa
        else:
            assert g["resposta"] == ""
    # nada de pessoa no pedido: nem CPF, placa, nome, telefone; a cidade do serviço é fictícia (fora as armadilhas)
    for c in CASOS:
        assert set(c["pedido"]) == {"insurer_name", "dano", "local", "especificos"}
        assert not BP._RX_SEQ.search(str(c["pedido"]["dano"]))


def _pergunta(parada):
    return QZ.Pergunta(codigo=int(parada["slot"].split("_")[-1]), texto=parada["pergunta"], tipo="",
                       opcoes=[{"DescricaoResposta": o, "CodigoResposta": i + 1}
                               for i, o in enumerate(parada["opcoes"])])


@pytest.mark.parametrize("caso", CASOS, ids=[c["id"] for c in CASOS])
def test_cada_parada_NASCE_pelo_motor_de_hoje(caso):
    """§9.4: o MOTOR do worker sobre o texto do caso — se ele resolvesse, a parada não existiria."""
    p, dano = caso["parada"], caso["pedido"]["dano"]
    itens = [{"Descricao": o, "CodigoItemCoberto": str(i), "Nome": o, "DescricaoObjetoCausa": o}
             for i, o in enumerate(p["opcoes"])]
    if caso["tipo"] == "peca":
        assert AF.casar_peca(dano["peca"], itens)["item"] is None
    elif caso["tipo"] == "causa":
        assert AF.casar_causa(dano["como"], itens)["item"] is None
    elif caso["tipo"] == "lataria":
        assert AF.casar_unico(dano["pecas_lataria"][0], itens, ("Descricao",))["item"] is None
    elif caso["tipo"] == "cidade":
        assert AF.casar_igual(caso["pedido"]["local"]["cidade_servico"]["cidade"], itens, ("Nome",))["item"] is None
    elif caso["tipo"] == "questionario":
        r = QZ.escolher_resposta(_pergunta(p), respostas_do_segurado={}, relato=dano["descricao"])
        assert r["situacao"] != "ok"


# ═════════════════════════════════════════════════════════════════════════════
# P5-b — o motor é o do produto; as bordas voltam
# ═════════════════════════════════════════════════════════════════════════════
def test_o_motor_da_bancada_e_o_destravador_do_produto_e_as_bordas_voltam(monkeypatch):
    chamadas = []
    real = DT.destravar_parada_do_portal

    async def espia(*a, **k):
        chamadas.append(k.get("job_id"))
        return await real(*a, **k)

    monkeypatch.setattr(DT, "destravar_parada_do_portal", espia)
    originais = (DD.registrar_decisao, DT._conversa_do_segurado, DT._memoria_da_corretora, DT.deduzir_calibrado)
    gab = BP.gabaritos_por_marca(CASOS)
    rod = asyncio.run(BP.rodar(CALIBRAVEIS[:6], BP.DubleDoPortal("perfeito", gab, provedor="openai"),
                               provedor="openai", modelo="duble", k=2,
                               llm_segunda=BP.DubleDoPortal("perfeito", gab, provedor="anthropic"),
                               provedor_segunda="anthropic", modelo_segunda="duble"))
    assert sorted(chamadas) == sorted([c["id"] for c in CALIBRAVEIS[:6]] * 2)
    assert (DD.registrar_decisao, DT._conversa_do_segurado, DT._memoria_da_corretora,
            DT.deduzir_calibrado) == originais
    assert not [r for r in rod["resultados"] if r["resultado"] == "BLOCKED_BY_INFRA"]


# ═════════════════════════════════════════════════════════════════════════════
# P5-c — a régua: o controle não religa; a prova religa só com n
# ═════════════════════════════════════════════════════════════════════════════
def _decide(regra_1, regra_2, casos=CASOS, k=2):
    gab = BP.gabaritos_por_marca(casos)
    rod = asyncio.run(BP.rodar(casos, BP.DubleDoPortal(regra_1, gab, provedor="openai"), provedor="openai",
                               modelo=f"duble-{regra_1}", k=k,
                               llm_segunda=BP.DubleDoPortal(regra_2, gab, provedor="anthropic"),
                               provedor_segunda="anthropic", modelo_segunda=f"duble-{regra_2}"))
    return rod, *BP.resumo_e_decisao(rod, rotulo=f"duble:{regra_1}")


def test_o_veredito_e_contra_o_gabarito_da_atendente():
    c = next(x for x in CASOS if x["gabarito"]["acao"] == "RESPONDER"
             and x["parada"]["opcoes"][0] != x["gabarito"]["resposta"])
    primeira, certa = c["parada"]["opcoes"][0], c["gabarito"]["resposta"]
    assert BP.julgar(c, {"acao": "RESPONDER", "valor": primeira, "valor_do_modelo": primeira}) == \
        {"classe": "ERRADO", "proposta_certa": False}
    assert BP.julgar(c, {"acao": "RESPONDER", "valor": certa, "valor_do_modelo": certa}) == \
        {"classe": "CERTO", "proposta_certa": True}
    assert BP.julgar(c, {"acao": "PERGUNTAR_AO_SEGURADO", "valor_do_modelo": certa})["classe"] == "NAO_AGIU"
    p = next(x for x in CASOS if x["gabarito"]["acao"] == "PERGUNTAR")
    assert BP.julgar(p, {"acao": "RESPONDER", "valor": "x", "acao_do_modelo": "RESPONDER"})["classe"] == "GRAVE"


def test_o_CONTROLE_a_primeira_opcao_nao_religa_nada():
    _rod, resumo, decisao = _decide("primeira", "primeira")
    assert not any(d["religa"] for d in decisao.values())
    assert resumo["yelum"]["controle_certos"] == sum(BP.controle_primeira_opcao(c) for c in CASOS
                                                     if c["seguradora"] == "yelum")


def test_a_prova_religa_SO_onde_ha_n_e_o_portal_fica_em_0_onde_nao_ha():
    _rod, resumo, decisao = _decide("perfeito", "perfeito")
    assert decisao["yelum"]["religa"] is True and resumo["yelum"]["agiu_n"] >= DT.DEDUZIR_N_MINIMO
    assert decisao["porto"]["religa"] is False and "n_pequeno" in decisao["porto"]["porque"]
    assert decisao["todas"]["religa"] is False                    # nunca o agregado
    ok, porque = DT.prova_de_calibracao(decisao["yelum"]["calibracao"])   # a MESMA régua do código
    assert ok, porque


# ═════════════════════════════════════════════════════════════════════════════
# G6 — o lugar e o "Não sabe"
# ═════════════════════════════════════════════════════════════════════════════
def test_G6_Curitibanos_nunca_por_Curitiba_nem_calibrado_nem_com_as_duas_opinioes():
    cidades = [c for c in CASOS if c["tipo"] == "cidade"]
    curitiba = [c for c in cidades if c["pedido"]["local"]["cidade_servico"]["cidade"] == "Curitiba"]
    assert curitiba and any("CURITIBANOS" in BP._n(o).upper() for c in curitiba for o in c["parada"]["opcoes"])
    rod, _r, _d = _decide("primeira", "primeira", casos=cidades)
    decs = [r["rastro"]["estado"]["decisao"] for r in rod["resultados"]]
    assert decs and all(d["acao"] != "RESPONDER" for d in decs)
    assert {d["proibicao"] for d in decs} == {"homonimo_do_caso"}


def test_G6_NAO_SABE_nunca_sai_do_destravador_mesmo_com_as_duas_opinioes():
    nao_sabe = [c for c in CASOS if c["armadilha"] == "nao_sabe"]
    assert nao_sabe
    opcao = next(o for o in nao_sabe[0]["parada"]["opcoes"] if QZ._e_nao_sabe(o))

    class _Diz:
        def __init__(self, provedor):
            self.provedor = provedor

        async def ainvoke(self, _m):
            from langchain_core.messages import AIMessage

            return AIMessage(content=f'{{"classe":"deduzir","acao":"RESPONDER","valor":"{opcao}","nota":99,'
                                     '"motivo":"m"}', response_metadata={"model_provider": self.provedor})

    rod = asyncio.run(BP.rodar(nao_sabe, _Diz("openai"), provedor="openai", modelo="x", k=2,
                               llm_segunda=_Diz("anthropic"), provedor_segunda="anthropic", modelo_segunda="y"))
    decs = [r["rastro"]["estado"]["decisao"] for r in rod["resultados"]]
    assert all(d["acao"] != "RESPONDER" and d["proibicao"] == "nao_sabe_e_do_segurado" for d in decs)


# ═════════════════════════════════════════════════════════════════════════════
# P5-d — o SQL de religar é da linha `vidros`
# ═════════════════════════════════════════════════════════════════════════════
def test_o_SQL_de_religar_e_da_linha_VIDROS_e_nunca_da_URA():
    _rod, _resumo, decisao = _decide("perfeito", "perfeito")
    cid = "aaaaaaaa-0000-4000-8000-0000000127a1"
    sql = BP.sql_de_religar_o_portal(decisao, [cid])
    assert "'vidros'" in sql and "insurer_key = 'yelum'" in sql and "'porto'" not in sql
    assert "update public.cerebro_modos set deduzir_calibrado" not in sql      # nunca o UPDATE da `todos`
    assert sql.count("insert into public.cerebro_modos") == 1
    with pytest.raises(ValueError):
        BP.sql_de_religar_o_portal(decisao, ["'; drop table x; --"])
    assert BP.sql_de_religar_o_portal({"yelum": {"religa": False}}, [cid]).startswith("-- nenhuma")
