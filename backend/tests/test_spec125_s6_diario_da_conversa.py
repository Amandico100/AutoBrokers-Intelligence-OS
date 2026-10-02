# -*- coding: utf-8 -*-
"""SPEC-125 S6 — o diário da CONVERSA (só os momentos de julgamento, D7) e o texto completo.

O MOTOR real (`diario_de_decisoes.registrar_julgamento_da_conversa` / `fechar_como_erro_leve`)
sobre o banco em memória da SPEC-123 (`test_spec123_diario_fio.Mundo`: COLUNAS do banco real +
as travas da migration), com DUAS corretoras reais (ids por SELECT read-only, sem nome).
As listas do serviço são conferidas contra os CHECKs VIVOS do banco (não duas verdades).

    cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec125_s6_diario_da_conversa.py -q
"""
from __future__ import annotations

import asyncio
import re
import sys
import uuid
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tests"))

from app.services import diario_de_decisoes as D  # noqa: E402
from test_spec123_diario_fio import Banco, Mundo, banco  # noqa: E402,F401  (o fixture `banco` é reusado)

JARGAO = re.compile(r"\w+_\w+|\{[A-Z]")


def test_as_listas_novas_batem_com_o_banco(banco):
    defs = banco["checks"]
    assert set(re.findall(r"'(\w+)'::text", defs["ck_diario_acao"])) == set(D.ACOES)
    assert set(re.findall(r"'(\w+)'::text", defs["ck_diario_resultado"])) == {
        "pendente", *D.RESULTADOS_FINAIS, *D.SINAIS_DE_ERRO_LEVE}
    assert set(re.findall(r"'(\w+)'::text", defs["ck_diario_momento"])) == set(D.MOMENTOS)
    for classe, acao in D.MOMENTOS.values():
        assert classe in D.CLASSES and acao in D.ACOES
    assert {"momento", "tela_completa", "valor_completo"} <= banco["colunas"]["diario_de_decisoes"]


def test_a_frase_da_conversa_e_de_gente():
    casos = {
        "deduziu": ("derrapei na chuva na BR-101 e bati no barranco", "o local foi uma rodovia",
                    "ele disse BR-101", "O agente entendeu que o local foi uma rodovia, sem perguntar de novo"),
        "respondeu_regra": ("o guincho vai até onde?", "até 200 km do local", "", "respondeu sozinho"),
        "nao_chamou_pessoa": ("que demora, vocês são lentos", "Já estou acionando, um minuto", "", "continuou o atendimento sozinho"),
        "chamou_pessoa": ("tem um ferido aqui", "", "há risco à vida", "chamou uma pessoa da corretora"),
    }
    for momento, (fala, valor, motivo, trecho) in casos.items():
        f = D.frase_da_conversa(momento=momento, fala=fala, valor=valor, motivo=motivo, fonte="a apólice", nota=85)
        assert f.startswith('O segurado escreveu "') and trecho in f, (momento, f)
        assert not JARGAO.search(f), (momento, f)          # D7: sem nome de variável nem marca de máscara
    assert "certeza 85%" in f


def test_o_julgamento_da_conversa_por_corretora(banco, monkeypatch):
    A, B = banco["A"], banco["B"]
    mundo = Mundo(banco["colunas"])
    conv_a, conv_b = str(uuid.uuid4()), str(uuid.uuid4())
    banco_async = Banco(mundo, assincrono=True)

    async def _cliente():
        return banco_async

    monkeypatch.setattr(D, "_cliente", _cliente)
    sessao = {"slots": {"segurado_nome": "Marcelino Tavares", "placa": "XYZ1A23"}}
    fala = "Sou o Marcelino Tavares, placa XYZ1A23, derrapei na chuva na BR-101"

    def reg(cid, conv, momento="deduziu", **k):
        return asyncio.run(D.registrar_julgamento_da_conversa(
            company_id=cid, conversation_id=conv, momento=momento, fala_do_segurado=fala,
            valor="o local foi uma rodovia", motivo="ele disse BR-101", nota=85, seguradora="porto",
            ramo="auto", servico="guincho", modelo="gpt-6.1-sol", sessao=sessao, **k))

    id_a = reg(A, conv_a)
    id_b = reg(B, conv_b)
    assert id_a and id_b and id_a != id_b
    assert reg(A, conv_a) == id_a, "idempotente: o mesmo julgamento não vira duas linhas"
    assert reg(A, conv_a, momento="chutou") is None, "momento fora da lista não grava"
    linhas = {l["id"]: l for l in mundo.rows("diario_de_decisoes")}
    assert len(linhas) == 2
    la = linhas[id_a]
    assert (la["origem"], la["momento"], la["classe"], la["acao"]) == ("atendimento", "deduziu", "deduzir",
                                                                         "respondeu_segurado")
    # 🔴 a COMPLETA guarda o texto inteiro; a MASCARADA e a frase não têm nome nem placa
    assert la["tela_completa"] == fala and "XYZ1A23" in la["tela_completa"]
    for col in ("tela_mascarada", "explicacao_para_gente", "valor_mascarado", "motivo"):
        assert "XYZ1A23" not in la[col] and "Tavares" not in la[col], (col, la[col])
    assert not JARGAO.search(la["explicacao_para_gente"]), la["explicacao_para_gente"]
    assert mundo.rows("work_events") == [], "conversa sem acionamento: nenhum evento de work_run"

    # chamou pessoa → ação `chamou_pessoa`
    id_p = reg(A, conv_a, momento="chamou_pessoa", chave_idempotencia="conversa:chamou:pessoa:1")
    assert linhas.get(id_p) is None and next(
        l for l in mundo.rows("diario_de_decisoes") if l["id"] == id_p)["acao"] == "chamou_pessoa"

    # ② o erro leve fecha SÓ a última pendente daquela conversa daquela corretora
    assert asyncio.run(D.fechar_como_erro_leve(company_id=B, conversation_id=conv_a, sinal="segurado_corrigiu")) == 0
    assert asyncio.run(D.fechar_como_erro_leve(company_id=A, conversation_id=conv_a, sinal="sumiu")) == 0
    assert asyncio.run(D.fechar_como_erro_leve(company_id=A, conversation_id=conv_a, sinal="segurado_corrigiu")) == 1
    fechadas = [l for l in mundo.rows("diario_de_decisoes") if l["resultado"] == "segurado_corrigiu"]
    assert len(fechadas) == 1 and fechadas[0]["company_id"] == A and fechadas[0]["resultado_em"]
    assert next(l for l in mundo.rows("diario_de_decisoes") if l["id"] == id_b)["resultado"] == "pendente"
    for q in mundo.registro:
        if q.nome == "diario_de_decisoes" and q.op in ("select", "update"):
            assert any(p[0] == "eq" and p[1] == "company_id" for p in q.pred), \
                f"🔴 consulta ao diário SEM filtro de corretora: {q.op} {q.pred}"


def test_o_acionamento_tambem_guarda_o_completo(banco, monkeypatch):
    """A linha da URA (SPEC-123) ganha `tela_completa` — e continua SEM `momento`."""
    mundo = Mundo(banco["colunas"])
    banco_async = Banco(mundo, assincrono=True)

    async def _cliente():
        return banco_async

    monkeypatch.setattr(D, "_cliente", _cliente)
    tela = "Confirme a placa XYZ1A23?\n1 - Sim\n2 - Não"
    i = asyncio.run(D.registrar_decisao(
        company_id=banco["A"], origem="acionamento", work_run_id=None, conversation_id=None,
        seguradora="porto", ramo="auto", rota="r", servico="s", tela=tela, classe="responder_com_dado",
        acao="respondeu_ura", valor="1", nota=90, limiar=70, motivo="", explicacao_para_gente="",
        modelo="m", segunda_opiniao=None, modo="on", gatilho="g", chave_idempotencia="acion:completo:1"))
    l = next(x for x in mundo.rows("diario_de_decisoes") if x["id"] == i)
    assert l["tela_completa"] == tela and "XYZ1A23" not in l["tela_mascarada"] and "momento" not in l
