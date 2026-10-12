"""SPEC-130-B · os dois achados da CONFIRMAÇÃO (12/10/2026), com o motor real (`_linhas_do_modelo`).

1. A regra do rótulo embrulhado em duas linhas (D-130B-13) deixava o rótulo de OUTRA linha ficar com o
   prêmio e o limite da linha de baixo ("Vendaval Não contratada" + "Danos Elétricos 600.000,00 15.103,93").
2. O limite lido de IMAGEM (visão) não tem trecho para conferir e venceria o do cadastro em `reconciliar`.

Linha de controle: o rótulo LEGITIMAMENTE quebrado em duas linhas continua entrando — prova que o guarda
novo consegue distinguir os dois casos (CLAUDE.md §9.3).
"""
from decimal import Decimal

from app.services import policy_document_evidence_service as S


def _ler(texto, linhas, *, literal=True):
    dados = {"linhas": linhas}
    saida, _descartadas, _motivos = S._linhas_do_modelo(
        dados, {1: texto}, base={"document_id": "d"}, exigir_trecho_literal=literal,
        metodo="modelo" if literal else "visao")
    return saida


def _rotulos(saida):
    return [(i["structured"]["label"], i["structured"]["lmi"], i["structured"]["premium"]) for i in saida]


def test_o_rotulo_de_outra_linha_nao_fica_com_o_premio_da_de_baixo():
    texto = "Vendaval Nao contratada\nDanos Eletricos 600.000,00 15.103,93"
    saida = _ler(texto, [{"pagina": 1, "rotulo": "Vendaval", "limite": "600.000,00", "premio": "15.103,93",
                          "trecho": "Vendaval Nao contratada Danos Eletricos 600.000,00 15.103,93"}])
    assert saida == [], _rotulos(saida)


def test_titulo_de_secao_em_cima_nao_vira_cobertura():
    texto = "COBERTURAS ADICIONAIS\nDanos Eletricos 600.000,00 15.103,93"
    saida = _ler(texto, [{"pagina": 1, "rotulo": "Coberturas Adicionais", "limite": "600.000,00",
                          "premio": "15.103,93",
                          "trecho": "COBERTURAS ADICIONAIS Danos Eletricos 600.000,00 15.103,93"}])
    assert saida == [], _rotulos(saida)


def test_controle_o_rotulo_legitimamente_quebrado_continua_entrando():
    texto = "Responsabilidade Civil Guarda de\nVeiculos de Terceiros 100.000,00 512,40"
    saida = _ler(texto, [{"pagina": 1, "rotulo": "Responsabilidade Civil Guarda de Veiculos de Terceiros",
                          "limite": "100.000,00", "premio": "512,40",
                          "trecho": "Responsabilidade Civil Guarda de Veiculos de Terceiros 100.000,00 512,40"}])
    assert len(saida) == 1, saida
    assert saida[0]["structured"]["premium"] == "R$ 512,40"


def test_controle_linha_de_baixo_so_com_valores_nao_e_barrada_pelo_guarda_novo():
    assert S._rotulo_de_baixo_no_do_modelo("600.000,00 15.103,93", "Danos Eletricos") is True
    assert S._rotulo_de_baixo_no_do_modelo("Danos Eletricos 600.000,00 15.103,93", "Vendaval") is False
    assert S._rotulo_de_baixo_no_do_modelo("Danos Eletricos 600.000,00 15.103,93", "Danos Eletricos") is True


def test_a_visao_nunca_traz_limite():
    saida = _ler("", [{"pagina": 1, "rotulo": "Incendio", "limite": "9.999.999,00", "premio": "1.000,00",
                       "trecho": ""}], literal=False)
    assert len(saida) == 1
    assert saida[0]["structured"]["lmi"] is None
    assert saida[0]["structured"]["premium"] == "R$ 1.000,00"
    assert Decimal("1000.00") > 0  # a linha fica: só o limite cai
