# -*- coding: utf-8 -*-
"""SPEC-124 F2 · D3 · G4 — a bancada da visão com GABARITO POR CAMPO.

🔴 Chama o MOTOR (CLAUDE.md §9.4): `bancada.rodar_bancada("visao_campos", …)` → `motor_visao_campos` →
o braço (dublê na borda: o modelo) → `veredito_dos_campos` sobre o corpus REAL (`visao_campos/casos.jsonl`
materializado). Nenhum helper reimplementa o juiz.

Linha de controle (§9.2/§9.3): o dublê `perfeito` (devolve o gabarito) tem de dar 100 %; o `burro`, 0 %
nos campos com valor; e um braço que erra UM dígito do CPF tem de perder EXATAMENTE o campo cpf.

Rodar (de backend/):  python -m pytest -q tests/test_spec124_visao_bancada_por_campo.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.evals import bancada as B  # noqa: E402
from app.services.evals import dubles as D  # noqa: E402

CORPUS = BACKEND / "tests" / "corpus" / "bancada" / "visao_campos"


def _casos():
    return B.carregar_casos("visao_campos")


# ---------------------------------------------------------------------------
# O corpus: 10 documentos, gabarito completo, valores sintéticos VÁLIDOS em forma
# ---------------------------------------------------------------------------
def _cpf_valido(cpf: str) -> bool:
    d = [int(c) for c in re.sub(r"\D", "", cpf)]
    if len(d) != 11:
        return False
    for n in (9, 10):
        s = sum(a * b for a, b in zip(d[:n], range(n + 1, 1, -1))) % 11
        if d[n] != (0 if s < 2 else 11 - s):
            return False
    return True


def test_corpus_tem_os_dez_documentos_com_gabarito_completo_e_valores_validos():
    casos = _casos()
    assert len(casos) == 10
    tipos = {c["entrada"]["tipo"] for c in casos}
    assert tipos == {"apolice_auto", "apolice_residencial", "cnh", "crlv", "orcamento", "boleto", "foto_dano"}
    for caso in casos:
        m = D.materializar(caso)
        gab = m["oraculo"]["campos"]
        assert tuple(gab) == B.CAMPOS_DA_VISAO, caso["chave"]
        assert m["oraculo"]["resposta_modelo_ouro"] == gab
        assert (CORPUS.parent / caso["entrada"]["imagem"]).exists()
        assert "SINTÉTICO" in caso["origem"]
        if gab["cpf"]:
            assert _cpf_valido(gab["cpf"]), caso["chave"]
        if gab["placa"]:
            assert re.fullmatch(r"[A-Z]{3}\d[A-Z]\d{2}", gab["placa"]), caso["chave"]
        if gab["vigencia_inicio"]:
            assert gab["vigencia_inicio"] < gab["vigencia_fim"]
    # o degradado e a CNH fotografada existem (o acerto em documento ruim é o que separa os braços)
    assert {"vcampos-apolice-auto-degradada", "vcampos-cnh-fotografada"} <= {c["chave"] for c in casos}


# ---------------------------------------------------------------------------
# O JUIZ por campo — normaliza, mas não perdoa
# ---------------------------------------------------------------------------
def test_juiz_normaliza_forma_e_reprova_conteudo():
    C = B.comparar_campo
    assert C("cpf", "123.456.789-09", "12345678909") == "acerto"
    assert C("cpf", "123.456.789-09", "123.456.789-08") == "errado"          # UM dígito
    assert C("placa", "ABC1D23", "abc-1d23") == "acerto"
    assert C("placa", "ABC1D23", "ABC1023") == "errado"                      # D lido como 0
    assert C("vigencia_inicio", "2026-08-15", "15/08/2026") == "acerto"
    assert C("vigencia_inicio", "2026-08-15", "2026-08-16") == "errado"
    assert C("valor_total", 3487.62, "R$ 3.487,62") == "acerto"
    assert C("valor_total", 3487.62, 3487.6) == "errado"
    assert C("valor_total", 2920.0, "2.920") == "acerto"
    assert C("nome", "Joana Ficticia Antunes", "JOANA FICTÍCIA ANTUNES") == "acerto"
    assert C("nome", "Joana Ficticia Antunes", "JOANA ANTUNES") == "errado"
    assert C("numero_apolice", "912345678901234", "9123456789O1234") == "errado"
    assert C("cpf", None, None) == "acerto"
    assert C("cpf", None, "123.456.789-09") == "inventou"
    assert C("cpf", "123.456.789-09", None) == "faltou"


def test_juiz_de_coberturas_exige_cada_lmi_e_nenhuma_a_mais():
    gab = [{"nome": "Casco (Colisão, Incêndio e Roubo)", "valor": 92350.0},
           {"nome": "Danos Materiais a Terceiros", "valor": 150000.0}]
    C = B.comparar_campo
    assert C("coberturas", gab, [{"nome": "Danos materiais a terceiros", "valor": "150.000,00"},
                                 {"nome": "Casco", "valor": 92350}]) == "acerto"      # ordem e forma livres
    assert C("coberturas", gab, [{"nome": "Casco", "valor": 92350},
                                 {"nome": "Danos Materiais a Terceiros", "valor": 512.40}]) == "errado"  # prêmio ≠ LMI
    assert C("coberturas", gab, [{"nome": "Casco", "valor": 92350}]) == "errado"          # faltou uma
    assert C("coberturas", gab, gab + [{"nome": "Vidros", "valor": 450}]) == "errado"     # uma a mais
    # o item OPCIONAL do gabarito (linha sem LMI no quadro): pode vir sem valor, ou não vir; com valor, erro
    opc = gab + [{"nome": "Assistência 24h", "valor": None, "opcional": True}]
    assert C("coberturas", opc, gab) == "acerto"
    assert C("coberturas", opc, gab + [{"nome": "Assistência 24h: Plano Completo (guincho 400 km)",
                                        "valor": None}]) == "acerto"
    assert C("coberturas", opc, gab + [{"nome": "Assistência 24h", "valor": 400}]) == "errado"
    assert C("coberturas", opc, gab + [{"nome": "Vidros", "valor": None}]) == "errado"    # sem valor, mas não é o opcional


def test_json_da_resposta_tolera_cerca_e_texto_em_volta():
    assert B.json_da_resposta('```json\n{"cpf": null}\n```') == {"cpf": None}
    assert B.json_da_resposta('Segue: {"placa": "ABC1D23"} ok') == {"placa": "ABC1D23"}
    assert B.json_da_resposta("não consegui ler") is None


# ---------------------------------------------------------------------------
# O FIO da bancada: corpus → motor → braço → juiz, com a LINHA DE CONTROLE
# ---------------------------------------------------------------------------
def test_linha_de_controle_perfeito_100_burro_0_nos_campos_com_valor(tmp_path):
    rel = B.rodar_bancada("visao_campos", ["duble:perfeito", "duble:burro"], k=1, teto_usd=10)
    arq = rel.salvar(str(tmp_path / "controle.json"))
    r = B.resumo_da_visao([arq])
    assert r["duble:perfeito"]["documentos"] == 10 and r["duble:perfeito"]["nota_d3"] == 1.0
    assert r["duble:perfeito"]["documentos_perfeitos"] == 10
    assert r["duble:burro"]["acerto_presentes"] == 0.0 and r["duble:burro"]["nota_d3"] == 0.0
    assert r["duble:burro"]["formato_invalido"] == 10
    # o acerto "geral" do burro NÃO é zero (null certo conta) — por isso a decisão usa a nota D3
    assert r["duble:burro"]["acerto_geral"] > 0.3


class _LLMQueErraUmDigito:
    """Borda dublada: um modelo que lê tudo certo MENOS um dígito do CPF — e registra o pedido."""

    def __init__(self):
        self.pedidos = []

    async def ainvoke(self, mensagens, config=None, **kw):
        from langchain_core.messages import AIMessage

        self.pedidos.append(mensagens)
        caso = D.CASO_ATUAL.get()
        gab = dict(caso["oraculo"]["campos"])
        if gab.get("cpf"):
            ult = gab["cpf"][-1]
            gab["cpf"] = gab["cpf"][:-1] + ("0" if ult != "0" else "1")
        return AIMessage(content=json.dumps(gab, ensure_ascii=False),
                         usage_metadata={"input_tokens": 1000, "output_tokens": 200, "total_tokens": 1200},
                         response_metadata={"model_name": "duble:perfeito"})

    def invoke(self, *a, **k):  # pragma: no cover
        raise AssertionError("o motor é assíncrono")


def test_motor_perde_exatamente_o_campo_cpf_e_manda_a_imagem_como_o_produto(tmp_path):
    llm = _LLMQueErraUmDigito()
    rel = B.rodar_bancada("visao_campos", ["duble:perfeito"], k=1, teto_usd=10,
                          construir_llm=lambda resolvido, cbs: llm)
    com_cpf = {c["chave"] for c in _casos() if c["oraculo"]["campos"].get("cpf")}
    for r in rel.resultados:
        v = r.rastro["estado"]["veredito_campos"]
        errados = sorted(c for c, x in v["campos"].items() if x != "acerto")
        assert errados == (["cpf"] if r.chave in com_cpf else []), (r.chave, errados)
        assert r.resultado == ("FAIL" if r.chave in com_cpf else "PASS")
    # o pedido: a instrução FIXA no system + a imagem em data-URI no formato de describe_image
    sistema, humano = llm.pedidos[0]
    assert sistema.content == B.INSTRUCAO_DE_CAMPOS
    blocos = humano.content
    assert blocos[1]["type"] == "image_url" and blocos[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert all(p[0].content == B.INSTRUCAO_DE_CAMPOS for p in llm.pedidos), "o prompt mudou entre documentos"


def test_o_papel_grava_no_ledger_como_visao_e_o_teto_le_so_o_papel():
    defn = B.definicao_do_papel("visao_campos")
    assert defn["rota"] == "visao" and defn["papel_no_ledger"] == "visao"

    class _Q:
        def __init__(self, dono, tabela):
            self.dono, self.tabela, self.filtros = dono, tabela, []

        def select(self, *_a):
            return self

        def eq(self, k, v):
            self.filtros.append(("eq", k, v))
            return self

        def gte(self, k, v):
            self.filtros.append(("gte", k, v))
            return self

        def in_(self, k, v):
            self.filtros.append(("in", k, tuple(v)))
            return self

        def range(self, *_a):
            return self

        def execute(self):
            self.dono.consultas.append((self.tabela, self.filtros))
            if self.tabela == "llm_pricing":
                return type("R", (), {"data": [{"model_name": "gpt-6-luna"}]})()
            return type("R", (), {"data": [{"total_cost_usd": 0.01}, {"total_cost_usd": 0.02}]})()

    class _DB:
        def __init__(self):
            self.consultas = []

        def table(self, t):
            return _Q(self, t)

    db = _DB()
    assert B.gasto_do_ledger_do_papel("openai", "2026-10-01T00:00:00+00:00", "visao", cliente=db) == 0.03
    filtros = dict((k, v) for _op, k, v in db.consultas[-1][1])
    assert filtros["details->>papel"] == "visao" and filtros["service_type"] == "bancada"
