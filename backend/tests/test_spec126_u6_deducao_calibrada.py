# -*- coding: utf-8 -*-
"""SPEC-126 U6 — A DEDUÇÃO calibrada do destravador.

🔴 O TESTE DO FIO (a 1ª entrega): uma trava DEDUZIR da Yelum pelo MOTOR (`destravador.destravar` real; dublê
SÓ no cliente do provedor e no banco — a borda de `test_spec122_sombra_e_sem_chute.amb`):

    tela REAL (yelum-residencial) → `handle_insurer_message` → `needs_human`
    → `destravar(modo="on")` → o modelo propõe DEDUZIR "Encanador" (nota 88)
    → `decidir_destravamento` → a régua chega à PORTA do DEDUZIR
    → `deduzir_calibrado(empresa, "yelum", ramo)` → `acao_do_cerebro.calibracao_da_chave` → `cerebro_modos`
         · sem a linha calibrada (o de HOJE)        → NÃO deduz (pergunta ao segurado), a 2ª opinião nem é paga
         · com a linha calibrada DESTA seguradora   → a 2ª opinião (outro provedor) concorda → RESPONDE
         · a linha de OUTRA corretora / seguradora  → NÃO deduz (dois tenants)
    → "Curitibanos" para um caso em "Curitiba": NUNCA, mesmo ligada (P-124-14)

Nasceu VERMELHO: antes da U6 a chave era a constante global (`DEDUZIR_AUTONOMO_CALIBRADO`) e
`destravador.deduzir_calibrado` não existia.

⚠️ Este arquivo NÃO importa a fixture `_deduzir_calibrado` dos arquivos da 123 (que liga a constante global
para provar a MECÂNICA): aqui a constante fica False, como no produto.

MUTAÇÃO (uma vez, em worktree próprio, restaurando por CÓPIA — saída no relatório da U6):
  M1 `DEDUZIR_N_MINIMO = 0` e `DEDUZIR_WILSON_MINIMO = 0` (o "limiar 0") → a seguradora sem prova religa →
     `test_G7_seguradora_sem_n_nao_religa` e `test_O_FIO_prova_ruim_no_banco_nao_liga` VERMELHOS.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from tests.test_spec122_sombra_e_sem_chute import (  # noqa: F401 — fixtures
    AC, CLIENTE, D, EMPRESA_A, EMPRESA_B, R, _fio_fixo, amb, sessao, tela_real,
)
from tests.test_spec123_destravador_fio import (  # noqa: F401 — fixtures (SEM `_deduzir_calibrado`)
    REF_YELUM_RES, RELATO, TELA_SERVICOS, destravar, dt, js, sessao_travada,
)
from app.services import destravador as DT
from app.services.evals import bancada as B

#: 💭 a prova que VALE (sintética): 10 casos que agiram, 10 certos nas k; no conjunto da porta (12) o modelo
#: propôs certo 11 e a tecla 1 acertaria 6 — o controle foi batido.
PROVA_BOA = {"n": 10, "certos": 10, "controle_n": 12, "controle_certos": 6, "modelo_proposta_certos": 11,
             "rodada": "teste-u6"}


def _chave(amb_, company, seguradora="yelum", *, calibrado=False, prova=None, ramo="todos", modo="on"):
    linha = {"company_id": company, "insurer_key": seguradora, "ramo": ramo, "modo": modo, "limiar": 70,
             "deduzir_calibrado": calibrado}
    if prova is not None:
        linha["calibracao"] = prova
    amb_.chaves.append(linha)
    AC._CACHE_DA_CHAVE.clear()


def _respostas_encanador(dt_):
    dt_.respostas = {
        ("destravador", "openai"): js(classe="deduzir", acao="RESPONDER", valor="Encanador", nota=88,
                                      motivo="vazamento no sifão é encanador"),
        ("destravador_segunda", "anthropic"): js(classe="deduzir", acao="RESPONDER", valor="Encanador",
                                                 nota=91, motivo="vazamento = encanador"),
    }


def _papeis(dt_):
    return [c["papel"] for c in dt_.chamadas_ao_modelo]


# =============================================================================
# 🔴 O TESTE DO FIO
# =============================================================================
def test_O_FIO_chave_desligada_nao_deduz_e_a_segunda_opiniao_nem_e_paga(dt):
    """HOJE: a Yelum da corretora A está `on`, mas SEM a dedução calibrada → pergunta ao segurado."""
    assert DT.DEDUZIR_AUTONOMO_CALIBRADO is False
    _chave(dt, EMPRESA_A, "yelum")
    s = sessao_travada()
    _respostas_encanador(dt)
    d = destravar(EMPRESA_A, s, TELA_SERVICOS)
    assert d.acao != "RESPONDER" and d.proibicao == "deduzir_sem_calibracao", d
    assert (d.porta_do_deduzir, d.deduzir_calibrado) == (True, False)
    assert _papeis(dt) == ["destravador"], "a 2ª opinião foi paga com a dedução desligada"


def test_O_FIO_a_linha_calibrada_DESTA_seguradora_deduz(dt):
    _chave(dt, EMPRESA_A, "yelum", calibrado=True, prova=dict(PROVA_BOA))
    s = sessao_travada()
    _respostas_encanador(dt)
    d = destravar(EMPRESA_A, s, TELA_SERVICOS)
    assert (d.acao, d.valor, d.classe, d.proibicao) == ("RESPONDER", "Encanador", "deduzir", ""), d
    assert (d.porta_do_deduzir, d.deduzir_calibrado) == (True, True)
    assert d.segunda_opiniao["provedor"] == "anthropic" and d.segunda_opiniao["concordou"] is True
    assert _papeis(dt) == ["destravador", "destravador_segunda"]


def test_O_FIO_dois_tenants_a_chave_de_A_nao_liga_nada_em_B(dt):
    """🔴 CLAUDE.md §7: a linha calibrada é da corretora A. A MESMA tela na corretora B não deduz."""
    _chave(dt, EMPRESA_A, "yelum", calibrado=True, prova=dict(PROVA_BOA))
    _chave(dt, EMPRESA_B, "yelum")                       # B está `on`, sem a dedução
    s = sessao_travada(company=EMPRESA_B, run="run-126-b")
    _respostas_encanador(dt)
    d = destravar(EMPRESA_B, s, TELA_SERVICOS)
    assert d.acao != "RESPONDER" and d.proibicao == "deduzir_sem_calibracao", d
    # o banco que VAZA a linha de A para B: o cinto do leitor recusa (a linha não é desta corretora)
    dt.banco_vaza = True
    AC._CACHE_DA_CHAVE.clear()
    assert asyncio.run(DT.deduzir_calibrado(EMPRESA_B, "yelum", "residencial")) is False
    # CONTROLE: a própria A continua calibrada
    AC._CACHE_DA_CHAVE.clear()
    dt.banco_vaza = False
    assert asyncio.run(DT.deduzir_calibrado(EMPRESA_A, "yelum", "residencial")) is True


def test_O_FIO_a_chave_de_OUTRA_seguradora_nao_liga_esta(dt):
    _chave(dt, EMPRESA_A, "porto", calibrado=True, prova=dict(PROVA_BOA))
    _chave(dt, EMPRESA_A, "yelum")
    s = sessao_travada()
    _respostas_encanador(dt)
    d = destravar(EMPRESA_A, s, TELA_SERVICOS)
    assert d.acao != "RESPONDER" and d.proibicao == "deduzir_sem_calibracao", d


def test_O_FIO_prova_ruim_no_banco_nao_liga(dt):
    """O código não confia no banco: `deduzir_calibrado = true` com n = 9 (o CHECK recusaria; aqui a
    linha chegou mesmo assim) → desligado."""
    _chave(dt, EMPRESA_A, "yelum", calibrado=True, prova={**PROVA_BOA, "n": 9, "certos": 9})
    s = sessao_travada()
    _respostas_encanador(dt)
    d = destravar(EMPRESA_A, s, TELA_SERVICOS)
    assert d.acao != "RESPONDER" and d.proibicao == "deduzir_sem_calibracao", d


def test_O_FIO_producao_nao_liga_a_deducao_por_parametro(dt):
    """`destravar(deduzir_calibrado=True)` sem braço injetado é IGNORADO: só a linha do banco liga."""
    _chave(dt, EMPRESA_A, "yelum")
    s = sessao_travada()
    _respostas_encanador(dt)
    d = destravar(EMPRESA_A, s, TELA_SERVICOS, deduzir_calibrado=True)
    assert d.acao != "RESPONDER" and d.proibicao == "deduzir_sem_calibracao", d


#: 💭 SINTÉTICA de propósito (o acervo não tem tela de cidade homônima; P-124-14 nasceu de um ataque da
#: confirmação da 124): o menu de cidades no corredor da Yelum residencial.
TELA_CIDADES = "Em qual cidade é o atendimento?\n1 - Curitibanos\n2 - Curitiba\n3 - Voltar"


def _deduz(valor, nota=95):
    return js(classe="deduzir", acao="RESPONDER", valor=valor, nota=nota, motivo="a cidade do caso")


def test_O_FIO_Curitibanos_para_Curitiba_nunca_mesmo_LIGADA(dt):
    _chave(dt, EMPRESA_A, "yelum", calibrado=True, prova=dict(PROVA_BOA))
    s = sessao_travada(slots={"problema_descricao": RELATO, "local_cidade": "Curitiba"})
    # o modelo E a 2ª opinião erram JUNTOS (o erro correlacionado do porto-092): só a regra pega
    dt.respostas = {("destravador", "openai"): _deduz("Curitibanos"),
                    ("destravador_segunda", "anthropic"): _deduz("Curitibanos")}
    d = destravar(EMPRESA_A, s, TELA_CIDADES, gatilho="cerebro")
    assert d.acao != "RESPONDER" and d.proibicao == "homonimo_do_caso", d
    assert "Curitibanos" not in str(d.valor if d.acao == "RESPONDER" else "")


def test_O_FIO_CONTROLE_Curitiba_para_Curitiba_age_quando_ligada(dt):
    """A linha de controle: a MESMA tela, a cidade CERTA, a chave ligada → responde (o guarda consegue
    deixar passar; não é um "não" a tudo)."""
    _chave(dt, EMPRESA_A, "yelum", calibrado=True, prova=dict(PROVA_BOA))
    s = sessao_travada(slots={"problema_descricao": RELATO, "local_cidade": "Curitiba"})
    dt.respostas = {("destravador", "openai"): _deduz("Curitiba"),
                    ("destravador_segunda", "anthropic"): _deduz("Curitiba")}
    d = destravar(EMPRESA_A, s, TELA_CIDADES, gatilho="cerebro")
    assert (d.acao, d.valor, d.proibicao) == ("RESPONDER", "Curitiba", ""), d


def test_a_segunda_opiniao_em_Curitibanos_nao_concorda_com_Curitiba(dt):
    """`_mesma_resposta` do produto casa por prefixo e daria "concordou"; a do destravador, por igualdade."""
    assert DT._mesma_escolha(TELA_CIDADES, "Curitiba", "Curitibanos") is False
    assert DT._mesma_escolha(TELA_CIDADES, "Curitiba", "2") is True          # CONTROLE: tecla = rótulo
    assert DT._rotulo_escolhido(TELA_CIDADES, "Curitiba") == "curitiba"


# =============================================================================
# P-124-14 — o homônimo e o prefixo, em código
# =============================================================================
@pytest.mark.parametrize("escolha, caso, homonimo", [
    ("Curitibanos", ["Curitiba"], True),
    ("Curitiba", ["Curitibanos"], True),
    ("São José dos Campos", ["São José"], True),
    ("Bom Jesus - SC", ["Bom Jesus - RS"], True),
    ("CURITIBA", ["Curitiba"], False),                   # CONTROLE: o próprio, só a caixa muda
    ("Curitiba - PR", ["Curitiba"], False),              # CONTROLE: a UF de um lado só
    ("Pinhais", ["Curitiba"], False),                    # outro lugar não é HOMÔNIMO (a porta decide)
    ("Curitibanos", [], False),
])
def test_homonimo_do_caso(escolha, caso, homonimo):
    assert DT.homonimo_do_caso(escolha, caso) is homonimo


def test_a_uf_irma_entra_no_lugar_do_caso():
    s = {"slots": {"local_cidade": "Bom Jesus", "local_uf": "RS", "local_rua": "Rua A"}}
    assert DT.localidades_do_caso(s) == ["Bom Jesus - rs"]
    assert DT.homonimo_do_caso("Bom Jesus - SC", DT.localidades_do_caso(s)) is True


PARADA_CIDADE = {"stage": "cidade_ambigua", "operacao": "responder", "slot": "cidade_servico",
                 "opcoes": ["CURITIBANOS", "CURITIBA"], "pergunta": "Qual a cidade?", "mensagem": ""}
#: 💭 caso fictício
CASO_PORTAL = {"insurer_name": "LIBERTY SEGUROS S/A", "cpf_cnpj": "00000000000",
               "local": {"estado": "PR", "cidade_servico": {"uf": "PR", "cidade": "Curitiba"}},
               "dano": {"peca": "para-brisa", "como": "pedra"}, "especificos": {}}


def _portal(valor):
    seg = {"provedor": "anthropic", "acao": "RESPONDER", "valor": valor}
    return DT.decidir_parada_do_portal(
        DT.Proposta(classe="deduzir", acao="RESPONDER", valor=valor, nota=97, motivo="m"),
        PARADA_CIDADE, CASO_PORTAL, provedor="openai", segunda_opiniao=seg, deduzir_calibrado=True)


def test_portal_cidade_ambigua_Curitibanos_nunca_mesmo_ligada():
    d = _portal("CURITIBANOS")
    assert d.acao != "RESPONDER" and d.proibicao == "homonimo_do_caso", d
    d2 = _portal("PINHAIS")                               # qualquer cidade que não é a do pedido
    assert d2.acao != "RESPONDER", d2
    ok = _portal("CURITIBA")                              # CONTROLE
    assert (ok.acao, ok.valor) == ("RESPONDER", "CURITIBA"), ok


def test_portal_chave_desligada_nao_deduz_a_cidade_certa():
    seg = {"provedor": "anthropic", "acao": "RESPONDER", "valor": "CURITIBA"}
    d = DT.decidir_parada_do_portal(
        DT.Proposta(classe="deduzir", acao="RESPONDER", valor="CURITIBA", nota=97, motivo="m"),
        PARADA_CIDADE, CASO_PORTAL, provedor="openai", segunda_opiniao=seg)
    assert d.acao != "RESPONDER" and d.proibicao == "deduzir_sem_calibracao", d


# =============================================================================
# (c) escolha restrita: dois menus colados (📊 des-D-ramo_indeterminado-allianz-004)
# =============================================================================
def _caso_do_corpus(trecho):
    [c] = [x for x in B.carregar_casos_do_destravador(trecho)]
    return c


def test_a_tecla_que_vale_em_dois_menus_colados_e_ambigua():
    c = _caso_do_corpus("ramo_indeterminado-allianz-004")
    tela = c["entrada"]["tela"]
    assert DT._escolha_ambigua(tela, "1") is True
    assert DT._escolha_ambigua(tela, "Residencial") is False            # CONTROLE: o rótulo é um só
    s = c["entrada"]["sessao"]
    seg = {"provedor": "anthropic", "acao": "RESPONDER", "valor": "1"}
    d = DT.decidir_destravamento(DT.ler_destravamento(_deduz("1", 97)), s, tela, gatilho="cerebro",
                                 provedor="openai", segunda_opiniao=seg, deduzir_calibrado=True)
    assert d.acao != "RESPONDER" and d.proibicao == "escolha_ambigua", d


# =============================================================================
# (e1) a placa da apólice: "confirme o veículo" sem modelo
# =============================================================================
def test_e1_o_veiculo_da_placa_do_caso_e_dado_do_caso_nao_deducao():
    c = B.ficha_realista(_caso_do_corpus("des-D-cerebro-alfa-037"))
    s, tela = B.sessao_do_caso(c), c["entrada"]["tela"]
    g = c["oraculo"]["destravador"]["gatilho"]
    assert s["slots"]["veiculo_placa"] == "BRA2E19" and "BR#-###9" in tela
    d = DT.decidir_destravamento(DT.ler_destravamento(_deduz("1", 97)), s, tela, gatilho=g)
    assert (d.acao, d.valor, d.classe, d.porta_do_deduzir) == ("RESPONDER", "1", "responder_com_dado", False), d
    # CONTROLE 1: sem a placa no caso → é dedução (porta) e, desligada, não age
    s2 = {**s, "slots": {k: v for k, v in s["slots"].items() if k != "veiculo_placa"}}
    d2 = DT.decidir_destravamento(DT.ler_destravamento(_deduz("1", 97)), s2, tela, gatilho=g)
    assert d2.acao != "RESPONDER" and d2.porta_do_deduzir and d2.proibicao == "deduzir_sem_calibracao", d2
    # CONTROLE 2: placa de OUTRO veículo → nada casa → dedução
    s3 = {**s, "slots": {**s["slots"], "veiculo_placa": "XYZ9Z99"}}
    d3 = DT.decidir_destravamento(DT.ler_destravamento(_deduz("1", 97)), s3, tela, gatilho=g)
    assert d3.acao != "RESPONDER" and d3.porta_do_deduzir, d3


# =============================================================================
# A PROVA (G7) — o critério de religar, em código
# =============================================================================
def test_wilson_bate_com_os_numeros_do_relatorio():
    assert [round(x, 3) for x in DT.wilson(10, 10)] == [0.722, 1.0]
    assert round(DT.wilson(9, 10)[0], 3) == 0.596
    assert round(DT.wilson(8, 8)[0], 3) == 0.676


@pytest.mark.parametrize("prova, ok, porque", [
    (PROVA_BOA, True, "calibrado"),
    ({**PROVA_BOA, "n": 9, "certos": 9}, False, "n_pequeno:9<10"),
    ({**PROVA_BOA, "certos": 9}, False, "wilson_abaixo:0.596"),
    ({**PROVA_BOA, "n": 20, "certos": 17}, False, "acerto_abaixo:17/20"),
    ({**PROVA_BOA, "modelo_proposta_certos": 6}, False, "nao_bateu_o_controle:6<=6/12"),
    ({**PROVA_BOA, "rodada": ""}, False, "prova_sem_rodada"),
    ({**PROVA_BOA, "n": True}, False, "sem_prova"),
    ({k: v for k, v in PROVA_BOA.items() if k != "controle_n"}, False, "sem_controle"),
    (None, False, "sem_prova"),
])
def test_prova_de_calibracao(prova, ok, porque):
    assert DT.prova_de_calibracao(prova) == (ok, porque)


def _rodada(casos):
    """Uma rodada `--calibracao` GRAVADA (sintética): [(chave, seguradora, controle, [(acao, certo, proposta,
    valor_do_modelo), …k])]."""
    res = []
    for chave, seg, ctl, ts in casos:
        for i, (acao, certo, prop, vm) in enumerate(ts, 1):
            res.append({"chave": chave, "braco": "openai:gpt-6.1-sol:high", "tentativa": i, "resultado": "PASS",
                        "rastro": {"estado": {
                            "calibracao": {"seguradora": seg, "controle_tecla_1": ctl},
                            "decisao": {"acao": acao, "valor": vm, "valor_do_modelo": vm, "porta_do_deduzir": True,
                                        "nota": 95, "segunda_opiniao": {"nota": 80, "concordou": acao == "RESPONDER"}},
                            "veredito_destravador": {"classe": "CERTO" if certo else "ERRO",
                                                     "proposta_certa": prop}}}})
    return {"resultados": res}


def _casos(seg, n, *, controle_certos, k=2):
    return [(f"{seg}-{i}", seg, i < controle_certos, [("RESPONDER", True, True, "2")] * k) for i in range(n)]


def test_G7_seguradora_com_prova_religa_e_a_sem_n_nao_religa():
    rodada = _rodada(_casos("yelum", 10, controle_certos=5) + _casos("porto", 5, controle_certos=2))
    resumo = B.resumo_da_calibracao([rodada])
    dec = B.decidir_religar(resumo, rodada="teste")
    assert dec["yelum"]["religa"] is True and dec["yelum"]["calibracao"]["n"] == 10
    assert DT.prova_de_calibracao(dec["yelum"]["calibracao"]) == (True, "calibrado")
    assert dec["todas"]["religa"] is False                 # o agregado nunca religa


def test_G7_seguradora_sem_n_nao_religa():
    """🔴 A MUTAÇÃO M1 (limiar 0) deixa ESTE vermelho: 5/5 numa seguradora religaria."""
    dec = B.decidir_religar(B.resumo_da_calibracao([_rodada(_casos("porto", 5, controle_certos=2))]),
                            rodada="teste")
    assert dec["porto"]["religa"] is False and dec["porto"]["porque"].startswith("n_pequeno"), dec["porto"]


def test_G7_k1_nao_conta_e_o_controle_tem_de_ser_batido():
    # k = 1: sem autoconsistência medida → nenhum caso conta como certo
    dec = B.decidir_religar(B.resumo_da_calibracao([_rodada(_casos("hdi", 12, controle_certos=2, k=1))]),
                            rodada="t")
    assert dec["hdi"]["religa"] is False and dec["hdi"]["calibracao"]["certos"] == 0
    # 12/12 agindo certo, mas a tecla 1 acertaria TODOS: o modelo não bateu o controle
    dec2 = B.decidir_religar(B.resumo_da_calibracao([_rodada(_casos("hdi", 12, controle_certos=12))]),
                             rodada="t")
    assert dec2["hdi"]["religa"] is False and dec2["hdi"]["porque"].startswith("nao_bateu_o_controle")
    # as k discordam → o caso não é "certo"
    disc = [("hdi-x", "hdi", False, [("RESPONDER", True, True, "1"), ("RESPONDER", True, True, "Residencial")])]
    r = B.resumo_da_calibracao([_rodada(disc)])
    assert (r["hdi"]["agiu_n"], r["hdi"]["agiu_certos"], r["hdi"]["k_concordantes"]) == (1, 0, 0)


def test_sql_de_religar_so_onde_religa_e_so_para_as_corretoras_pedidas():
    rodada = _rodada(_casos("yelum", 10, controle_certos=5) + _casos("porto", 5, controle_certos=2))
    dec = B.decidir_religar(B.resumo_da_calibracao([rodada]), rodada="teste")
    sql = B.sql_de_religar(dec, [EMPRESA_A])
    assert sql.count("update public.cerebro_modos") == 1
    assert f"company_id = '{EMPRESA_A}'" in sql and "insurer_key = 'yelum'" in sql and "'porto'" not in sql
    assert EMPRESA_B not in sql
    with pytest.raises(ValueError):
        B.sql_de_religar(dec, ["'; drop table x; --"])


# =============================================================================
# (g1)(g2) a bancada: só a PORTA, ficha REALISTA, o controle "tecla 1"
# =============================================================================
def test_g2_ficha_realista_sem_mascara_de_dado_e_a_placa_mascarada_na_tela():
    c = B.ficha_realista(_caso_do_corpus("des-D-cerebro-alfa-067"))
    slots = c["entrada"]["ficha"]["slots"]
    assert slots["local_numero"] == "120" and slots["titular_cpf"] == "12345678909", slots
    assert not [v for v in slots.values() if isinstance(v, str) and v.startswith("{")], slots
    assert c["entrada"]["sessao"]["client_phone"] == B.TELEFONE_DA_BANCADA       # nunca vai ao banco
    assert "{PLACA}" not in c["entrada"]["tela"] and "BRA2E19" not in c["entrada"]["tela"]
    assert "BR#-###9" in json.dumps(c["oraculo"]["destravador"]["aceitas"], ensure_ascii=False)
    # o original não mudou (cópia)
    assert "{PLACA}" in _caso_do_corpus("des-D-cerebro-alfa-067")["entrada"]["tela"]


def test_g1_os_casos_da_calibracao_sao_so_os_da_porta():
    casos = B.carregar_casos_da_calibracao()
    chaves = {c["chave"] for c in casos}
    # 📊 02/10: 39 DEDUZIR com prova → 32 na porta (4 resolvidos pela placa — e1 —, 3 de custo)
    assert len(casos) >= 30, len(casos)
    assert not chaves & {"des-D-cerebro-alfa-037", "des-D-cerebro-alfa-057", "des-D-cerebro-alfa-067",
                         "des-D-cerebro-allianz-048"}, "o veículo da placa não é calibração (e1)"
    assert all(c["calibrando"] and c["entrada"]["calibracao"]["porta_esperada"]["porta"] for c in casos)
    # a linha de controle existe nos dois sentidos (a tecla 1 acerta uns e erra outros)
    ctl = [c["entrada"]["calibracao"]["controle_tecla_1"] for c in casos]
    assert any(ctl) and not all(ctl)
    # nenhuma máscara de dado sobrou na ficha que vai ao modelo
    for c in casos:
        for v in (c["entrada"]["sessao"].get("slots") or {}).values():
            assert not (isinstance(v, str) and v in B.VALORES_REALISTAS), (c["chave"], v)


def test_o_leitor_unico_devolve_a_calibracao_da_mesma_linha_do_modo(amb):
    _chave(amb, EMPRESA_A, "yelum", calibrado=True, prova=dict(PROVA_BOA), ramo="residencial")
    _chave(amb, EMPRESA_A, "yelum", ramo="todos")
    assert asyncio.run(AC.calibracao_da_chave(EMPRESA_A, "yelum", "residencial")) == (True, PROVA_BOA)
    assert asyncio.run(AC.calibracao_da_chave(EMPRESA_A, "yelum", "auto")) == (False, {})   # cai no 'todos'
    assert asyncio.run(AC.calibracao_da_chave(EMPRESA_B, "yelum", "residencial")) == (False, {})
    assert asyncio.run(AC.modo_e_limiar(EMPRESA_A, "yelum", "residencial")) == ("on", 70)    # o modo não mudou


def test_a_constante_global_continua_desligada_no_codigo():
    fonte = Path(DT.__file__).read_text(encoding="utf-8")
    assert "\nDEDUZIR_AUTONOMO_CALIBRADO = False\n" in fonte
    assert DT.DEDUZIR_N_MINIMO >= 10 and DT.DEDUZIR_WILSON_MINIMO >= 0.70 and DT.DEDUZIR_ACERTO_MINIMO >= 0.90


def test_a_migration_tem_apply_verify_rollback_e_nao_liga_nada():
    m = (Path(__file__).resolve().parents[1] / "supabase" / "migrations"
         / "20261002_10_spec126_u6_deduzir_calibrado.sql").read_text(encoding="utf-8")
    for x in ("-- APPLY:", "-- VERIFY", "-- ROLLBACK:", "EXPAND-FIRST: sim", "DESTRUTIVA:   não",
              "default false", "ck_cerebro_modos_deduzir_so_com_prova", "add column if not exists"):
        assert x in m, x
    corpo = "\n".join(l for l in m.splitlines() if not l.lstrip().startswith("--"))
    assert "update public.cerebro_modos" not in corpo.lower(), "a migration não liga nada"
