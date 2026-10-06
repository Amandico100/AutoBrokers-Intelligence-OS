# -*- coding: utf-8 -*-
"""SPEC-130-A F3 · U6 — A MENSAGEM do WhatsApp (G6 · D-MC-74 · D-MC-71 · D-MC-55).

    2 balões · ≤ 700 caracteres · ≤ 2 emojis · no máximo 2 opções (a recomendada e a mais em conta) · "das N que
    cotei" · juros COM NOME · link + validade + 1 linha verdadeira da anfitriã · nenhuma frase proibida · nenhuma
    comissão · nenhum nome da perdedora. Sobre o CONTRATO (`fixtures/proposta/modelo_contrato.json`) e sobre o
    modelo REAL que a proposta monta do canário (o motor, não um atalho — CLAUDE.md §9.4).

Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec130a_a_mensagem.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import copy
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.services.multicalculo import mensagem as MSG  # noqa: E402
from app.services.multicalculo.proposta import montar_proposta  # noqa: E402
from dubles import mundo_da_proposta as M  # noqa: E402

CONTRATO = BACKEND / "tests" / "fixtures" / "proposta" / "modelo_contrato.json"
LINK = "https://app.exemplo.test/r/tOkEn_ficticio_0123456789abcdefghijklmnopq"


@pytest.fixture
def contrato():
    return json.loads(CONTRATO.read_text(encoding="utf-8"))


def _opcoes_citadas(balao: str):
    return re.findall(r"^\*([^*]+):\*", balao, re.M)


def test_os_dois_baloes_do_contrato(contrato):
    b1, b2 = MSG.mensagem_whatsapp(contrato, LINK)
    medida = MSG.conferir([b1, b2])
    assert medida["caracteres"] <= MSG.TETO_DE_CARACTERES and 1 <= medida["emojis"] <= 2 and medida["proibidas"] == []
    assert b1.startswith("Pronto, Mariana! Das 12 seguradoras que cotei para o seu Compass, 11 deram preço")
    assert _opcoes_citadas(b1) == ["Recomendada", "Mais em conta"]            # D-MC-74: no máximo 2, estas duas
    assert "*R$ 4.784,27 por ano* ou 10x de R$ 555,83 com juros, total R$ 5.558" in b1      # juros com NOME
    assert "Menor franquia" not in b1 and "Tokio" not in b1
    assert b2.splitlines() == [LINK, "Os preços valem até 13/10/2026.",
                               "Resulta Seguros, nota 5,0 no Google (14 avaliações)."]


def test_sem_juros_so_quando_o_parcelamento_bate(contrato):
    contrato["opcoes"][0]["parcelas_sem_juros"] = {"vezes": 5, "valor": 956.85}
    b1 = MSG.mensagem_whatsapp(contrato, LINK)[0]
    assert "ou 5x de R$ 956,85 sem juros" in b1 and "10x" not in b1.split("*Mais em conta:*")[0]


def test_a_comissao_e_a_perdedora_nao_entram_mesmo_se_o_modelo_vier_sujo(contrato):
    sujo = copy.deepcopy(contrato)
    sujo["opcoes"][0]["comissao_percentual"] = 17.37
    sujo["entre_corretoras"] = [{"corretora": "Resulta Seguros", "melhor_completa": 4784.27, "vencedora": True},
                                {"corretora": None, "melhor_completa": 5100.0, "vencedora": False}]
    texto = "\n".join(MSG.mensagem_whatsapp(sujo, LINK))
    assert "17,37" not in texto and "17.37" not in texto and "None" not in texto and "5.100" not in texto
    assert "Quem atende é a Resulta Seguros, que teve o menor preço entre as 2 corretoras comparadas." in texto


def test_o_teto_encolhe_a_mensagem_em_vez_de_estourar(contrato):
    longo = copy.deepcopy(contrato)
    for o in longo["opcoes"]:
        o["motivos"] = ["Um motivo bem comprido que ocupa espaço na mensagem para forçar o encolhimento " * 2]
    baloes = MSG.mensagem_whatsapp(longo, LINK)
    assert MSG.conferir(baloes)["caracteres"] <= MSG.TETO_DE_CARACTERES
    assert "*R$ 4.784,27 por ano*" in baloes[0] and LINK in baloes[1]


def test_o_guarda_das_frases_proibidas_acha_quando_ela_esta_la():
    """🔴 GUARDA com controle: o medidor acha a frase, conta os emojis e mede o tamanho (senão ele não guarda nada)."""
    m = MSG.conferir(["É o mais barato do mercado, corra! ✅✅✅", "x" * 700])
    assert m["proibidas"] == ["mais barato do mercado", "corra"] and m["emojis"] == 3 and m["caracteres"] > 700


def test_a_mensagem_do_modelo_real_do_canario(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    modelo = asyncio.run(montar_proposta(m.dono, m.pedido_id, "novo_sem_apolice", primeiro_nome="Mariana", db=m.db,
                                         agora=datetime(2026, 10, 6, 11, 0, tzinfo=timezone.utc)))
    baloes = MSG.mensagem_whatsapp(modelo, LINK)
    medida = MSG.conferir(baloes)
    assert medida["caracteres"] <= MSG.TETO_DE_CARACTERES and medida["emojis"] <= 2 and medida["proibidas"] == []
    r = modelo["resumo"]
    assert f"Das {r['seguradoras_cotadas']} seguradoras que cotei" in baloes[0]
    assert _opcoes_citadas(baloes[0]) == ["Recomendada", "Mais em conta"]
    rec = modelo["opcoes"][0]
    assert f"{rec['premio_anual']:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".") in baloes[0]
    texto = "\n".join(baloes)
    for proibido in (M.NOME_BETA, M.MARCA_BETA, "Vega", "17,37"):
        assert proibido not in texto
    assert M.MARCA_ALFA in baloes[1] and "Os preços valem até 11/10/2026." in baloes[1]
