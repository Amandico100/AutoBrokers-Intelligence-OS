# -*- coding: utf-8 -*-
"""SPEC-133-A.1 F2 — o sexo pelo PRIMEIRO nome (D-133A1-02, o pedido do Founder de 10/10).

"Perguntar para Mariana, claramente uma mulher, se ela é homem ou mulher é chato." A regra: o primeiro nome do "nome
completo" → a proporção de cada sexo na tabela do IBGE (Censo 2010, `app/data/nomes_por_sexo_ibge.json`); ≥ o limiar
(`canal.sexo_pelo_nome_min_pct`) de um lado → grava o sexo, marca `inferido_pelo_nome` e PULA a pergunta, sem anunciar;
entre os dois limiares ou fora da tabela → pergunta como antes. O nome nunca vai ao modelo.

📊 Os nomes ambíguos foram MEDIDOS na tabela (10/10/2026, IBGE): Juraci 45,4 % homens · Eli 59,1 % · Darci 66,9 % ·
Valdeci 74,9 %. Os claros: Mariana 0,4 % · Renata 0,5 % · Joana 0,4 % · Sílvia 0,3 % · José 99,6 % · Carlos 99,6 % ·
Pedro 99,5 %.

O FIO: "nome completo" → conversa._no_roteiro → sexo_pelo_nome (tabela) → respostas.sexo + inferido_pelo_nome →
montar_perfil (condutor.sexo assumido) → cotacao.disparar → MulticalculoProvider.calcular REAL (o pedido com o sexo).

⛔ Dados fictícios (CPF sintético com DV válido, placa e nomes inventados) — CLAUDE.md §13.9.
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec133a1_sexo_pelo_nome.py -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# os dublês e o mundo do fio da 133-A (as fixtures entram por import — pytest as acha pelo nome no módulo)
from test_spec133a_a_conversa import (  # noqa: E402,F401
    CPF_FICTICIO, M, ModeloProibido, TEL, canal, falar, motor_grava_o_quadro, mundo, rodar, rodar_o_run)

CID = "c1300000-0000-4000-8000-00000000ca1a"
PERGUNTA_DO_SEXO = "homem ou mulher"
PERGUNTA_DA_CARTEIRA = "carteira de motorista"
ATE_O_NOME = ["oi", "sim", "ABC1D23", "01001-000", "não", "uns 800 km", "não", CPF_FICTICIO]

#: (primeiro nome como a pessoa escreve, o que a regra deve devolver com o limiar padrão 70)
CASOS = [
    ("Mariana", "F"), ("Renata", "F"), ("Joana", "F"), ("Sílvia", "F"),
    ("José", "M"), ("Carlos", "M"), ("Pedro", "M"),
    ("JOSÉ", "M"), ("  mariana  ", "F"), ("SÍLVIA", "F"), ("João-Pedro", "M"), ("joão", "M"),
    ("Juraci", None),          # 📊 45,4 % homens — o ambíguo de verdade
    ("Eli", None),             # 📊 59,1 %
    ("Darci", None),           # 📊 66,9 % — perto do limiar, ainda pergunta
    ("Xandrolina", None),      # fora da tabela (inventado)
    ("Pessoa", None),          # o nome dos testes da 133-A: fora da tabela → a pergunta continua no fio antigo
    ("", None),
]


def defeitos(sexo_fn, *, min_pct=70.0):
    """A régua: cada caso que a função responde diferente do esperado é um DEFEITO. A real exige []."""
    saida = []
    for nome, esperado in CASOS:
        obtido = sexo_fn(f"{nome} Sintetica Teste" if nome.strip() else nome, min_pct=min_pct)
        if obtido != esperado:
            saida.append(f"{nome.strip() or '<vazio>'}: esperado {esperado}, veio {obtido}")
    return saida


@pytest.fixture
def conversa():
    from app.services.canal import conversa as C

    C.nomes_por_sexo.cache_clear()
    yield C
    C.nomes_por_sexo.cache_clear()


# =====================================================================================================================
# a TABELA (o dado do IBGE, versionado)
# =====================================================================================================================
def test_a_tabela_do_ibge_tem_fonte_data_comando_e_nomes_normalizados(conversa):
    bruto = json.loads(conversa.TABELA_DE_NOMES.read_text(encoding="utf-8"))
    assert "IBGE" in bruto["fonte"] and "2010" in bruto["fonte"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", bruto["coletado_em"])
    assert "gerar_nomes_por_sexo.py" in bruto["comando"]
    tabela = conversa.nomes_por_sexo()
    assert len(tabela) >= 600                                     # 📊 630 em 10/10/2026
    assert all(re.fullmatch(r"[a-z]+", n) for n in tabela), "nome com acento, maiúscula ou espaço na tabela"
    assert all(h >= 0 and m >= 0 and h + m > 0 for h, m in tabela.values())
    # a tabela CONSEGUE dizer os dois lados (§9.3): há nome claro de cada sexo e há ambíguo
    assert tabela["mariana"][1] > 100 * tabela["mariana"][0] and tabela["jose"][0] > 100 * tabela["jose"][1]
    h, m = tabela["juraci"]
    assert 30 < 100 * h / (h + m) < 70


# =====================================================================================================================
# a REGRA
# =====================================================================================================================
def test_a_regra_decide_os_claros_e_deixa_os_ambiguos_e_os_raros_para_a_pergunta(conversa):
    assert defeitos(conversa.sexo_pelo_nome) == []


def test_o_limiar_decide_perto_da_fronteira(conversa):
    s = conversa.sexo_pelo_nome
    assert s("Valdeci Sintetica", min_pct=70) == "M" and s("Valdeci Sintetica", min_pct=80) is None   # 📊 74,9 %
    assert s("Darci Sintetica", min_pct=65) == "M" and s("Darci Sintetica", min_pct=70) is None       # 📊 66,9 %


def test_mutacao_limiar_ignorado_fica_vermelho(conversa):
    """Mutação: decidir pela MAIORIA (o limiar ignorado) → Juraci, Eli e Darci deixam de ser perguntados → VERMELHO."""
    def maioria(nome, *, min_pct):
        return conversa.sexo_pelo_nome(nome, min_pct=50.0001)

    achados = defeitos(maioria)
    assert len(achados) == 3 and all(a.split(":")[0] in ("Juraci", "Eli", "Darci") for a in achados), achados


def test_mutacao_tabela_vazia_pergunta_sempre(conversa, monkeypatch):
    """Tabela ausente ou ilegível → {} → a regra nunca conclui (pergunta sempre). A régua vê a diferença: os sete claros
    (e as variações de grafia) viram defeito — a tabela é o que faz a regra funcionar."""
    monkeypatch.setattr(conversa, "TABELA_DE_NOMES", BACKEND / "app" / "data" / "nao_existe_133a1.json")
    conversa.nomes_por_sexo.cache_clear()
    assert conversa.nomes_por_sexo() == {}
    assert all(conversa.sexo_pelo_nome(n, min_pct=70) is None for n, _ in CASOS)
    assert len(defeitos(conversa.sexo_pelo_nome)) == sum(1 for _, e in CASOS if e)


@pytest.mark.parametrize("config, esperado", [
    (None, 70.0), ({}, 70.0), ({"canal": {"sexo_pelo_nome_min_pct": 80}}, 80.0),
    ({"canal": {"sexo_pelo_nome_min_pct": 100}}, 100.0),
    ({"canal": {"sexo_pelo_nome_min_pct": 50}}, 70.0), ({"canal": {"sexo_pelo_nome_min_pct": 30}}, 70.0),
    ({"canal": {"sexo_pelo_nome_min_pct": 101}}, 70.0), ({"canal": {"sexo_pelo_nome_min_pct": True}}, 70.0),
    ({"canal": {"sexo_pelo_nome_min_pct": "80"}}, 70.0),
])
def test_o_limiar_vem_da_config_do_canal(conversa, config, esperado):
    from app.services.multicalculo.config import PADRAO_DO_PRODUTO

    assert PADRAO_DO_PRODUTO["canal"]["sexo_pelo_nome_min_pct"] == 70
    assert conversa.limiar_do_sexo_pelo_nome(config) == esperado


# =====================================================================================================================
# a CONVERSA
# =====================================================================================================================
def _ate_o_nascimento(c, nome, *, config=None):
    estado = None
    r = None
    for fala in ATE_O_NOME + [nome, "01/02/1980"]:
        estado = c.repo.carregar_estado(object(), CID, TEL) if estado is None else r.estado
        r = rodar(c.conversa.responder(object(), CID, TEL, fala, None, estado, config=config, llm=ModeloProibido()))
        c.repo.salvar_estado(object(), CID, TEL, r.estado)
    return r


@pytest.mark.parametrize("nome, sexo", [("Mariana Sintetica Teste", "F"), ("Renata Sintetica", "F"),
                                        ("joana sintetica", "F"), ("José Sintetico", "M"),
                                        ("CARLOS SINTETICO", "M"), ("Pedro Sintetico Teste", "M")])
def test_nome_claro_pula_a_pergunta_sem_anunciar(canal, nome, sexo):
    canal.conversa.nomes_por_sexo.cache_clear()
    r = _ate_o_nascimento(canal, nome)
    texto = "\n".join(r.baloes).lower()
    assert r.estado["etapa"] == "habilitacao" and PERGUNTA_DA_CARTEIRA in texto
    assert PERGUNTA_DO_SEXO not in texto
    assert not re.search(r"\b(mulher|homem|feminino|masculino|senhora|senhor)\b", texto), "anunciou o palpite"
    assert r.estado["respostas"]["sexo"] == sexo and r.estado["inferido_pelo_nome"] == ["sexo"]


@pytest.mark.parametrize("nome", ["Juraci Sintetica Teste", "Xandrolina Sintetica", "Eli Sintetico"])
def test_nome_ambiguo_ou_raro_pergunta_como_antes(canal, nome):
    canal.conversa.nomes_por_sexo.cache_clear()
    r = _ate_o_nascimento(canal, nome)
    assert r.estado["etapa"] == "sexo" and PERGUNTA_DO_SEXO in "\n".join(r.baloes).lower()
    assert "sexo" not in r.estado["respostas"] and "inferido_pelo_nome" not in r.estado
    r2 = rodar(canal.conversa.responder(object(), CID, TEL, "mulher", None, r.estado, llm=ModeloProibido()))
    assert r2.estado["respostas"]["sexo"] == "F" and r2.estado["etapa"] == "habilitacao"
    assert "inferido_pelo_nome" not in r2.estado


def test_o_limiar_da_config_chega_a_conversa(canal):
    """📊 Valdeci 74,9 % homens: padrão 70 → pula; a corretora com 80 → pergunta. Darci 66,9 %: 65 → pula."""
    canal.conversa.nomes_por_sexo.cache_clear()
    assert _ate_o_nascimento(canal, "Valdeci Sintetico").estado["etapa"] == "habilitacao"
    canal.repo.estados.clear()
    r = _ate_o_nascimento(canal, "Valdeci Sintetico", config={"canal": {"sexo_pelo_nome_min_pct": 80}})
    assert r.estado["etapa"] == "sexo"
    canal.repo.estados.clear()
    r = _ate_o_nascimento(canal, "Darci Sintetico", config={"canal": {"sexo_pelo_nome_min_pct": 65}})
    assert r.estado["etapa"] == "habilitacao" and r.estado["respostas"]["sexo"] == "M"


def test_tabela_vazia_a_conversa_pergunta_para_mariana(canal, monkeypatch):
    monkeypatch.setattr(canal.conversa, "nomes_por_sexo", lambda: {})
    r = _ate_o_nascimento(canal, "Mariana Sintetica Teste")
    assert r.estado["etapa"] == "sexo" and PERGUNTA_DO_SEXO in "\n".join(r.baloes).lower()


def test_recomecar_apaga_a_marca_do_inferido(canal):
    canal.conversa.nomes_por_sexo.cache_clear()
    r = _ate_o_nascimento(canal, "Mariana Sintetica Teste")
    assert r.estado["inferido_pelo_nome"] == ["sexo"]
    r2 = rodar(canal.conversa.responder(object(), CID, TEL, "começar de novo", None, r.estado, llm=ModeloProibido()))
    assert r2.estado["etapa"] == "placa" and "inferido_pelo_nome" not in r2.estado


# =====================================================================================================================
# 🔴 O FIO — "Mariana" do "oi" até a PORTA REAL, sem a pergunta, com o sexo declarado assumido no pedido
# =====================================================================================================================
def test_o_fio_mariana_sem_a_pergunta_ate_a_porta(mundo, canal, monkeypatch):
    m, c = mundo, canal
    c.conversa.nomes_por_sexo.cache_clear()
    from app.services.multicalculo import porta as P

    chamadas = []
    original = P.MulticalculoProvider.calcular

    async def espiao(self, **kw):
        chamadas.append(dict(kw))
        return await original(self, **kw)

    monkeypatch.setattr(P.MulticalculoProvider, "calcular", espiao)
    proibido = ModeloProibido()
    falas = ["oi", "sim", "ABC1D23", "01001-000", "não", "uns 800 km", "não", CPF_FICTICIO,
             "Mariana Sintetica Teste", "01/02/1980", "20", "3.500"]               # sem "homem"/"mulher"
    r = falar(c, m.db, m.canal, falas, llm=proibido)
    assert proibido.chamadas == 0, "o nome (ou outra resposta de regra) foi ao modelo"
    assert r.disparar and r.estado["etapa"] == "calculando", r.estado.get("etapa")
    enviados = "\n".join("\n".join(b) for (_c, t, b) in c.envio.enviados if t == TEL).lower()
    assert PERGUNTA_DA_CARTEIRA in enviados and PERGUNTA_DO_SEXO not in enviados
    assert "condutor.sexo" in r.disparar["assumidos"] and "segurado.sexo" in r.disparar["assumidos"]

    run_id = rodar(c.cotacao.disparar(m.db, m.canal, TEL, r.disparar, r.estado))
    assert run_id and len(chamadas) == 1
    pedido = chamadas[0]["pedido"]
    assert pedido.valor("segurado", "sexo") == "F" and pedido.valor("condutor", "sexo") == "F"
    assert "condutor.sexo" in pedido.assumidos
    bruto = json.dumps(m.banco.run(run_id)["input_payload"], ensure_ascii=False)
    assert "Mariana" not in bruto and "Sintetica" not in bruto
    # o resto do fio segue igual: o motor grava, o run entrega
    pedidos = [p for p in m.banco.linhas("multicalculo_pedidos") if p["origem"] == "canal"]
    assert motor_grava_o_quadro(m.banco, pedido_id=pedidos[0]["id"], dados=m.dados) > 0
    antes = len(c.envio.enviados)
    rodar(rodar_o_run(m.db, run_id, m.canal))
    novos = ["\n".join(b) for (_c, t, b) in c.envio.enviados[antes:] if t == TEL]
    assert len(novos) == 1 and "Prontinho" in novos[0]
