# -*- coding: utf-8 -*-
"""SPEC-130-A · F1 · U1 — A COMPARAÇÃO sobre as 104 ofertas REAIS do canário de 05/10 (G2, G3, D-130A-03/04/09).

O motor real (`comparacao.comparar`/`opcoes`) roda sobre a fixture SANEADA (`fixtures/proposta/
ofertas_canario_saneadas.json`: corretora_a/corretora_b, uuids fictícios, nenhum nome de corretora — §13.9).

📊 O que os dados reais dizem (contados aqui, no próprio teste, por caminho independente do motor):
   104 ofertas · 38 padrão · 44 econômica · 22 ajuste · 81 "Compreensiva" · casco 100 em 88 ·
   a "Azul Assinatura" tem prêmio de ASSINATURA (o `premio_mensal` é premio_total/12, derivado) ·
   a melhor completa da corretora_a: 3.730,56 (padrão) e 2.975,96 (econômica) · da corretora_b: 4.784,27 (padrão).
⚠️ Os EVENTOS da fixture são 💭 sintéticos com as FAMÍLIAS medidas; o 6º (Hdi CREDENCIAL na corretora_b, que
   ofertou R$ 7.956,37 na mesma opção) reproduz o caso 📊 real que o gerente achou.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.services.multicalculo import comparacao as C
from app.services.multicalculo.config import PADRAO_DO_PRODUTO, mesclar

BACKEND = Path(__file__).resolve().parents[1]
FIXTURE = BACKEND / "tests" / "fixtures" / "proposta" / "ofertas_canario_saneadas.json"


@pytest.fixture(scope="module")
def dados():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def quadro(dados):
    return C.comparar(dados["ofertas"], dados["eventos"], estados=dados["estados"])


def _opcao_de(dados):
    return {e["calculo_id"]: e["opcao"] for e in dados["estados"]}


def _sem_chave(obj, proibida="comissao"):
    """Procura recursivamente qualquer chave que contenha `proibida`."""
    if isinstance(obj, dict):
        return all(proibida not in str(k) and _sem_chave(v, proibida) for k, v in obj.items())
    if isinstance(obj, (list, tuple)):
        return all(_sem_chave(v, proibida) for v in obj)
    return True


# =====================================================================================================================
# os FATOS medidos (contados por fora do motor) e a classe que o motor dá
# =====================================================================================================================
def test_os_fatos_medidos_do_pedido_real(dados):
    of = dados["ofertas"]
    op = _opcao_de(dados)
    assert len(of) == 104
    assert sorted(op[o["calculo_id"]] for o in of).count("padrao") == 38
    assert sorted(op[o["calculo_id"]] for o in of).count("economica") == 44
    assert sorted(op[o["calculo_id"]] for o in of).count("ajuste") == 22
    assert sum(1 for o in of if o["coberturas"].get("tipoPadronizado") == "Compreensiva") == 81
    assert sum(1 for o in of if o["coberturas"].get("casco") == 100) == 88
    # o premio_mensal é DERIVADO (premio_total/12) em todas — inútil para achar assinatura
    assert all(abs(o["premio_mensal"] - o["premio_total"] / 12) < 0.02 for o in of)
    # saneada (§13.9): as corretoras só por letra e uuid fictício; nenhuma oferta carrega nome de corretora
    assert set(dados["corretoras"]) == {"corretora_a", "corretora_b"}
    assert all("corretora" not in o for o in of)
    assert {o["corretora_company_id"] for o in of} == set(dados["corretoras"].values())


def test_classificar_completa_e_os_motivos_humanos(dados):
    classes = [C.classificar(o) for o in dados["ofertas"]]
    completas = [o for o, c in zip(dados["ofertas"], classes) if c.comparavel]
    # completa = compreensiva + casco 100 + não assinatura (contado por fora)
    esperado = [o for o in dados["ofertas"] if o["coberturas"].get("tipoPadronizado") == "Compreensiva"
                and o["coberturas"].get("casco") == 100 and "assinatura" not in o["seguradora"].lower()]
    assert len(completas) == len(esperado) and {o["id"] for o in completas} == {o["id"] for o in esperado}
    motivos = {c.motivo for c in classes if not c.comparavel}
    assert {"não cobre batida no seu carro", "só cobre danos a terceiros", "paga só 80 % da tabela FIPE",
            "só cobre batida com perda total", "preço de assinatura, não é um prêmio anual"} <= motivos
    # a Azul por Assinatura: DIFERENTE, preço nunca exibido — e o "proteção para terceiros" é RCF pela régua do auto
    assin = [o for o in dados["ofertas"] if o["seguradora"] == "Azul Assinatura"]
    assert len(assin) == 4
    for o in assin:
        c = C.classificar(o)
        assert not c.comparavel and c.chave == "assinatura" and c.exibe_preco is False
    terceiros = next(o for o in assin if "terceiros" in o["pacote"])
    assert C.REGRAS_POR_RAMO[31](terceiros, None).chave == "so_terceiros"


def test_assinatura_vem_da_config_e_a_config_pode_trocar(dados):
    azul = next(o for o in dados["ofertas"] if o["seguradora"] == "Azul Assinatura" and "completo" in o["pacote"])
    assert C.classificar(azul).chave == "assinatura"
    sem_regra = mesclar({"produtos_de_assinatura": []})
    # sem a regra da config, a mesma oferta cai na régua do auto (casco 90 → parcial), nunca vira COMPLETA
    assert C.classificar(azul, config=sem_regra).chave == "casco_parcial"


# =====================================================================================================================
# G2 · o ranking: só completas, POR OPÇÃO, a vencedora certa
# =====================================================================================================================
def test_g2_ranking_so_tem_completas_e_a_vencedora_e_a_menor(dados, quadro):
    ids_completos = {o["id"] for o in dados["ofertas"] if C.classificar(o).comparavel}
    for opcao, linhas in quadro.por_opcao.items():
        assert linhas, opcao
        assert all(l["oferta_id"] in ids_completos for l in linhas)
        assert [l["premio_anual"] for l in linhas] == sorted(l["premio_anual"] for l in linhas)
    assert all("Assinatura" not in l["seguradora"] for l in quadro.ranking())
    a, b = dados["corretoras"]["corretora_a"], dados["corretoras"]["corretora_b"]
    entre = {e["corretora_company_id"]: e for e in quadro.entre_corretoras}
    assert entre[a]["melhor_completa"] == 3730.56 and entre[a]["seguradora"] == "Youse" and entre[a]["vencedora"]
    assert entre[b]["melhor_completa"] == 4784.27 and entre[b]["seguradora"] == "Bradesco" and not entre[b]["vencedora"]
    assert quadro.vencedora == a
    assert quadro.ranking("economica", a)[0]["premio_anual"] == 2975.96
    assert quadro.ranking("economica", b)[0]["premio_anual"] == 4168.45
    assert quadro.sem_opcao == 0


def test_guarda_a_economica_e_o_ajuste_nunca_entram_no_ranking_da_padrao(dados, quadro):
    """🔴 GUARDA (mutação registrada na entrega): a econômica TAMBÉM é compreensiva casco 100 — se o comparador
    ignorar a opção, a Youse da econômica (R$ 2.975,96) vira a "recomendada" da padrão."""
    op = _opcao_de(dados)
    ranking_padrao = quadro.ranking("padrao")
    assert ranking_padrao and all(op[l["calculo_id"]] == "padrao" for l in ranking_padrao)
    assert all(l["opcao"] == "padrao" for l in ranking_padrao)
    precos = {l["premio_anual"] for l in ranking_padrao}
    assert 2975.96 not in precos                      # a Youse da ECONÔMICA
    assert 4211.32 not in precos                      # o Bradesco do AJUSTE
    # CONTROLE: os dois preços existem no quadro, nas opções deles (o guarda consegue ficar vermelho)
    assert 2975.96 in {l["premio_anual"] for l in quadro.ranking("economica")}
    assert 4211.32 in {l["premio_anual"] for l in quadro.ranking("ajuste")}


def test_oferta_sem_estado_nao_entra_em_ranking_nenhum(dados):
    estados = [e for e in dados["estados"] if e["opcao"] != "economica"]
    q = C.comparar(dados["ofertas"], dados["eventos"], estados=estados)
    assert q.sem_opcao == 44 and "economica" not in q.por_opcao


def test_diferentes_agrupados_sem_duplicata_e_assinatura_sem_preco(quadro):
    difs = quadro.diferentes
    chaves = [(d["seguradora"], d["produto"], d["chave_motivo"]) for d in difs]
    assert len(chaves) == len(set(chaves))
    assin = [d for d in difs if d["chave_motivo"] == "assinatura"]
    assert assin and all(d["premio_anual"] is None for d in assin)
    assert all(d["motivo"] for d in difs)


# =====================================================================================================================
# quem não respondeu: frase humana, nunca o texto cru, e quem OFERTOU na opção não entra
# =====================================================================================================================
def test_nao_responderam_frase_humana_e_quem_ofertou_fica_fora(dados, quadro):
    nomes = {r["seguradora"]: r for r in quadro.nao_responderam}
    assert set(nomes) == {"Sura", "Suhai", "Sompo", "Alfa"}
    assert nomes["Sura"]["motivo"] == "não aceitou este perfil"
    assert nomes["Suhai"]["motivo"] == "sistema da seguradora indisponível"
    assert nomes["Sompo"]["motivo"] == "não foi possível consultar"
    # 📊 caso REAL: a HDI da corretora_b ofertou R$ 7.956,37 na padrão e tem um seguradora_recusou|CREDENCIAL
    b = dados["corretoras"]["corretora_b"]
    assert 7956.37 in {l["premio_anual"] for l in quadro.ranking("padrao", b) if l["seguradora"] == "HDI"}
    assert "HDI" not in nomes and "Youse" not in nomes
    # CONTROLE: sem a oferta da HDI, a mesma recusa APARECE (a regra é a oferta, não a família)
    sem_hdi = [o for o in dados["ofertas"] if o["seguradora"] != "Hdi"]
    q2 = C.comparar(sem_hdi, dados["eventos"], estados=dados["estados"])
    assert "HDI" in {r["seguradora"] for r in q2.nao_responderam}


def test_o_texto_cru_da_seguradora_nunca_sai(dados):
    eventos = copy.deepcopy(dados["eventos"])
    for e in eventos:
        e["mensagem"] = "ERRO ORA-01017 senha invalida https://portal.exemplo/x?token=abc"
        e["mensagens"] = ["Usuário bloqueado CPF 529.982.247-25"]
    q = C.comparar(dados["ofertas"], eventos, estados=dados["estados"])
    texto = json.dumps([q.nao_responderam_por_opcao, q.resumo], ensure_ascii=False)
    assert "ORA-" not in texto and "http" not in texto and "529.982" not in texto and "bloqueado" not in texto


# =====================================================================================================================
# as OPÇÕES (D-130A-09) · nota · motivos verdadeiros · G3 sem comissão
# =====================================================================================================================
def test_opcoes_sem_apolice_recomendada_mais_em_conta_e_a_terceira(dados, quadro):
    ops = C.opcoes(quadro, situacao="novo_sem_apolice")
    a = dados["corretoras"]["corretora_a"]
    assert [o["id"] for o in ops] == ["recomendada", "mais_em_conta", "menor_franquia"]
    rec, conta, terceira = ops
    assert (rec["seguradora"], rec["premio_anual"]) == ("Youse", 3730.56)
    assert (conta["seguradora"], conta["premio_anual"]) == ("Youse", 2975.96)
    n = len(quadro.ranking("padrao", a))
    assert n == 13 and rec["motivos"][0] == f"Menor preço entre as {n} seguradoras com cobertura completa"
    # a menor franquia da padrão da corretora_a é de OUTRA seguradora (contado por fora)
    padrao_a = quadro.ranking("padrao", a)
    menor = min((l for l in padrao_a if l["franquia"]["valor"] is not None), key=lambda l: l["franquia"]["valor"])
    assert terceira["seguradora"] == menor["seguradora"] != "Youse"
    assert f"A menor franquia do quadro: {C.reais(menor['franquia']['valor'])}" in terceira["motivos"]
    assert "R$ 754,60 a menos por ano que a opção \"Recomendada\"" in conta["o_que_muda"]
    assert rec["o_que_muda"] == []
    for o in ops:
        assert 0 <= o["nota"] <= 100 and 2 <= len(o["motivos"]) <= C.MAX_MOTIVOS
        assert o["ref"]["corretora_company_id"] == a
    assert ops[0]["nota"] == C.opcoes(quadro, situacao="novo_sem_apolice")[0]["nota"]     # determinística


def test_opcoes_com_apolice_e_renovacao(quadro):
    """🔴 RT-B1 (red team, 06/10): a 1ª opção é SEMPRE a menor completa; a seguradora da apólice entra como "igual" na
    posição VERDADEIRA dela (antes ela ia para o topo e a página a chamava de "a melhor das N")."""
    apolice = {"seguradora": "Bradesco", "premio_anual": 4500}
    ops = C.opcoes(quadro, situacao="novo_com_apolice", apolice_atual=apolice)
    assert [o["rotulo"] for o in ops] == ["Recomendada", "Igual à sua atual", "Mais em conta"]
    assert (ops[0]["seguradora"], ops[0]["premio_anual"]) == ("Youse", 3730.56)
    assert ops[1]["seguradora"] == "Bradesco" and ops[1]["premio_anual"] == 4458.32
    assert any("que a sua apólice atual" in m for m in ops[1]["motivos"])
    assert any(m.endswith("menor preço entre as 13 seguradoras com cobertura completa") and not m.startswith("Menor")
               for m in ops[1]["motivos"])                                   # a posição dela, não "a menor"
    ren = C.opcoes(quadro, situacao="renovacao", apolice_atual=apolice)
    assert [o["id"] for o in ren][:2] == ["recomendada", "sua_renovacao"] and ren[1]["rotulo"] == "Sua renovação"
    with pytest.raises(ValueError):
        C.opcoes(quadro, situacao="qualquer")


def test_RT_B1_a_seguradora_da_apolice_que_ja_e_a_menor_vem_primeiro_como_igual(quadro):
    ops = C.opcoes(quadro, situacao="novo_com_apolice", apolice_atual={"seguradora": "Youse", "premio_anual": 3900})
    assert [o["id"] for o in ops][0] == "igual_a_atual" and ops[0]["premio_anual"] == 3730.56
    assert ops[0]["motivos"][0] == "Menor preço entre as 13 seguradoras com cobertura completa"
    assert "recomendada" not in [o["id"] for o in ops]                    # a mesma oferta não aparece duas vezes


@pytest.mark.parametrize("situacao", ["novo_com_apolice", "renovacao"])
def test_J_B2_sem_a_apolice_recusa_e_seguradora_fora_do_quadro_nao_vira_igual(quadro, situacao):
    """🔴 J-B2 (juiz, 06/10): sem a apólice, recusa (nunca um "Igual à sua atual" inventado); com uma seguradora que
    não deu preço completo, NÃO existe opção "igual" — antes era a menor completa, de outra seguradora, com o rótulo."""
    for vazia in (None, {}, {"seguradora": "  "}, {"premio_anual": 5000}):
        with pytest.raises(ValueError, match="apólice atual"):
            C.opcoes(quadro, situacao=situacao, apolice_atual=vazia)
    ops = C.opcoes(quadro, situacao=situacao, apolice_atual={"seguradora": "Seguradora Que Nao Cotou", "premio_anual": 5000})
    ids = [o["id"] for o in ops]
    assert "igual_a_atual" not in ids and "sua_renovacao" not in ids and ids[0] == "recomendada"
    assert any("que a sua apólice atual" in m for m in ops[0]["motivos"])  # a comparação com a apólice continua


def test_completa_mais_vira_a_terceira_quando_houver_calculo(dados):
    a = dados["corretoras"]["corretora_a"]
    estados = copy.deepcopy(dados["estados"])
    estados.append({"calculo_id": "c0ffee00-0000-4000-8000-0000000000cm", "corretora_company_id": a,
                    "opcao": "completa_mais", "status": "fechado"})
    youse = next(o for o in dados["ofertas"] if o["seguradora"] == "Youse" and o["premio_total"] == 3730.56)
    mais = dict(copy.deepcopy(youse), id="c0ffee00-0000-4000-8000-0000000000of",
                calculo_id="c0ffee00-0000-4000-8000-0000000000cm", premio_total=4100.0)
    # a completa+ como o robô a grava: a padrão + pequenos reparos (`reparoRapido`, presets._COMPLETA_MAIS). Sem a
    # diferença de cobertura ela seria a MESMA oferta com outro rótulo (J-P4 — o teste abaixo)
    mais["coberturas"] = dict(mais["coberturas"], reparoRapido=True)
    q = C.comparar(dados["ofertas"] + [mais], dados["eventos"], estados=estados)
    ops = C.opcoes(q, situacao="novo_sem_apolice")
    assert [o["id"] for o in ops] == ["recomendada", "mais_em_conta", "mais_completa"]
    assert ops[2]["premio_anual"] == 4100.0
    com = C.opcoes(q, situacao="novo_com_apolice", apolice_atual={"seguradora": "Bradesco"})
    assert [o["id"] for o in com] == ["recomendada", "igual_a_atual", "mais_em_conta"]       # RT-B1: a menor no topo
    com_youse = C.opcoes(q, situacao="novo_com_apolice", apolice_atual={"seguradora": "Youse"})
    assert [o["id"] for o in com_youse] == ["igual_a_atual", "mais_em_conta", "mais_completa"]


def test_J_P4_a_completa_mais_igual_a_recomendada_nao_vira_terceira_opcao(dados):
    """🔴 J-P4 (juiz, 06/10): a "Mais completa" que é a MESMA seguradora com o mesmo prêmio (ou as mesmas coberturas)
    da recomendada não é opção — cai para a "Menor franquia"/"Outra completa". Controle: com outra cobertura, entra."""
    a = dados["corretoras"]["corretora_a"]
    estados = copy.deepcopy(dados["estados"]) + [{"calculo_id": "c0ffee00-0000-4000-8000-0000000000cm",
                                                  "corretora_company_id": a, "opcao": "completa_mais"}]
    youse = next(o for o in dados["ofertas"] if o["seguradora"] == "Youse" and o["premio_total"] == 3730.56)
    base = dict(copy.deepcopy(youse), id="c0ffee00-0000-4000-8000-0000000000of",
                calculo_id="c0ffee00-0000-4000-8000-0000000000cm")
    mesmo_preco = dict(copy.deepcopy(base), premio_total=3730.90)
    mesmas_coberturas = dict(copy.deepcopy(base), premio_total=4100.0)
    for repetida in (mesmo_preco, mesmas_coberturas):
        q = C.comparar(dados["ofertas"] + [repetida], dados["eventos"], estados=estados)
        assert "mais_completa" not in [o["id"] for o in C.opcoes(q, situacao="novo_sem_apolice")]
    controle = copy.deepcopy(mesmas_coberturas)
    controle["coberturas"]["reparoRapido"] = True                           # acrescenta pequenos reparos
    q = C.comparar(dados["ofertas"] + [controle], dados["eventos"], estados=estados)
    assert [o["id"] for o in C.opcoes(q, situacao="novo_sem_apolice")][2] == "mais_completa"


def test_g3_nenhuma_comissao_sai_da_comparacao_nem_das_opcoes(dados):
    ofertas = copy.deepcopy(dados["ofertas"])
    for o in ofertas:
        o["comissao_percentual"] = 15.0                # a corretora DONA lê a comissão — a comparação não a passa
    q = C.comparar(ofertas, dados["eventos"], estados=dados["estados"])
    saidas = [q.por_opcao, q.diferentes_por_opcao, q.nao_responderam_por_opcao, q.entre_corretoras, q.resumo]
    for sit, ap in (("novo_sem_apolice", None), ("novo_com_apolice", {"seguradora": "Bradesco"}),
                    ("renovacao", {"seguradora": "Tokio"})):
        saidas.append(C.opcoes(q, situacao=sit, apolice_atual=ap))
    assert _sem_chave(saidas)
    # CONTROLE: a varredura acha a chave quando ela está lá
    assert not _sem_chave([{"x": {"comissao_percentual": 1}}])


def test_empate_entre_corretoras_pela_regra_da_config(dados):
    a, b = dados["corretoras"]["corretora_a"], dados["corretoras"]["corretora_b"]
    base = next(o for o in dados["ofertas"] if o["seguradora"] == "Youse" and o["premio_total"] == 3730.56)
    estados = [{"calculo_id": "ca", "corretora_company_id": a, "opcao": "padrao"},
               {"calculo_id": "cb", "corretora_company_id": b, "opcao": "padrao"}]
    ofertas = [dict(base, id="oa", calculo_id="ca", corretora_company_id=a),
               dict(base, id="ob", calculo_id="cb", corretora_company_id=b)]
    q = C.comparar(ofertas, [], estados=estados, corretoras_info={a: {"nota_google": 4.1}, b: {"nota_google": 4.9}})
    assert q.vencedora == b
    q2 = C.comparar(ofertas, [], estados=estados, corretoras_info={a: {"ordem_de_adesao": 1}, b: {"ordem_de_adesao": 2}})
    assert q2.vencedora == a
    q3 = C.comparar(ofertas, [], estados=estados, ordem_corretoras=[b, a])
    assert q3.vencedora == b


# =====================================================================================================================
# QUALQUER ramo (≠ 31): passa sem quebrar
# =====================================================================================================================
def test_um_ramo_que_nao_e_auto_passa_pela_comparacao_e_pelas_opcoes():
    a = "a0000000-0000-4000-8000-000000000002"
    estados = [{"calculo_id": "r-p", "corretora_company_id": a, "opcao": "padrao"},
               {"calculo_id": "r-e", "corretora_company_id": a, "opcao": "economica"}]
    pedido = {"tipo": "Residencial", "incendio": 500000, "danos_eletricos": 20000}

    def of(i, seg, cod, premio, calc, cob=None):
        return {"id": f"r{i}", "calculo_id": calc, "corretora_company_id": a, "seguradora": seg,
                "seguradora_codigo": cod, "pacote": "Residencial", "premio_total": premio, "franquia_valor": None,
                "coberturas": dict(cob or pedido), "parcelamentos": [{"parcelas": 4, "demais_parcelas": premio / 4}]}

    ofertas = [of(1, "Seg A", 1, 900.0, "r-p"), of(2, "Seg B", 2, 850.0, "r-p"), of(3, "Seg C", 3, 700.0, "r-p"),
               of(4, "Seg B", 2, 640.0, "r-e")]
    ofertas[2]["coberturas"] = {"tipo": "Residencial", "incendio": 300000}      # configuração DIFERENTE do pedido
    q = C.comparar(ofertas, [], estados=estados, ramo=2)
    assert [l["seguradora"] for l in q.ranking()] == ["Seg B", "Seg A"]
    assert [d["motivo"] for d in q.diferentes] == ["cobre um conjunto diferente do pedido"]
    ops = C.opcoes(q, situacao="novo_sem_apolice")
    assert [o["id"] for o in ops][:2] == ["recomendada", "mais_em_conta"]
    assert all(len(o["motivos"]) >= 2 and 0 <= o["nota"] <= 100 for o in ops)
    assert all(c["chave"] != "casco" for c in ops[0]["coberturas"])


def test_reais_no_formato_do_brasil():
    assert C.reais(3730.56) == "R$ 3.730,56"
    assert C.reais(5009.0) == "R$ 5.009"
    assert C.reais(754.6) == "R$ 754,60"
    assert PADRAO_DO_PRODUTO["opcoes"]["na_pagina"] >= 2
