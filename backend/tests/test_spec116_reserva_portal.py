# -*- coding: utf-8 -*-
"""SPEC-116-RESERVA — o cérebro do PORTAL: Sol falha → Opus 5.5 decide.

🔴 CHAMA O MOTOR (CLAUDE.md §9.4): `adaptive.decide_next_action` com o
`modelo_do_portal` real, pelas bordas de `test_spec116_f3b_portal.py` (REST do
Supabase + a rede do provedor). A rota `portal_decisao` recebe o MAPA do Founder
(reserva anthropic/claude-opus-5-5, esforço padrão).

  · 429 / 500 / 503 / timeout / conexão do Sol → UMA chamada ao Opus 5.5, UMA
    ação devolvida ao laço, UMA linha no ledger com o motivo (sem efeito repetido:
    a decisão é pura — quem age é o laço, uma vez, com a ação que voltou);
  · 400 / 404 → NÃO troca (defeito nosso); o laço recebe `ask_human`.

Rodar (de backend/):  .venv/Scripts/python -m pytest -q tests/test_spec116_reserva_portal.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from test_spec116_f3b_portal import ACAO_OK, MODELO_HOJE, _decidir, borda  # noqa: E402,F401


@pytest.fixture
def com_reserva(borda):
    borda.rest.pap["portal_decisao"].update(provider_reserva="anthropic",
                                            modelo_reserva="claude-opus-5-5",
                                            esforco_reserva=None)
    return borda


def _por_fora(borda, exc):
    """A rede do Sol cai com `exc` ANTES de responder; o Opus responde."""
    cliente = borda.prov.cliente()

    class _Cliente(cliente):
        async def post(self, url, headers=None, json=None, **k):  # noqa: A002
            if json and json.get("model") == MODELO_HOJE:
                borda.prov.pedidos.append({"url": str(url), "corpo": json, "headers": {}})
                raise exc
            return await super().post(url, headers=headers, json=json, **k)

    sys.modules["httpx"].AsyncClient = _Cliente


@pytest.mark.parametrize("status", [429, 500, 503])
def test_sol_falha_transitoria_o_opus_decide_uma_vez(com_reserva, status):
    # SPEC-122 (30/09/2026): o Sol da rota é o gpt-6.1-sol (antes o Sol 6, hoje DEPRECATED)
    assert MODELO_HOJE == "gpt-6.1-sol"
    com_reserva.prov.status = [status, 200]
    assert _decidir() == ACAO_OK
    assert com_reserva.prov.modelos == [MODELO_HOJE, "claude-opus-5-5"], "UMA reserva, sem repetir"
    assert com_reserva.prov.pedidos[1]["url"].endswith("/v1/messages")
    assert len(com_reserva.rest.ledger) == 1
    linha = com_reserva.rest.ledger[0]
    d = linha["details"]
    assert d["reserva_usada"] is True and f"HTTP {status}" in d["motivo_reserva"]
    assert linha["model_name"] == "claude-opus-5-5"


@pytest.mark.parametrize("exc", [httpx.ReadTimeout("lento"), httpx.ConnectError("caiu")],
                         ids=["timeout", "conexao"])
def test_sol_timeout_ou_conexao_o_opus_decide(com_reserva, exc):
    _por_fora(com_reserva, exc)
    assert _decidir() == ACAO_OK
    assert com_reserva.prov.modelos == [MODELO_HOJE, "claude-opus-5-5"]
    assert com_reserva.rest.ledger[0]["details"]["reserva_usada"] is True


@pytest.mark.parametrize("status", [400, 404])
def test_sol_falha_nao_transitoria_nao_troca(com_reserva, status):
    com_reserva.prov.status = [status, 200]
    acao = _decidir()
    assert com_reserva.prov.modelos == [MODELO_HOJE], f"{status} virou chamada ao Opus"
    assert acao["action"] == "ask_human" and f"HTTP {status}" in acao["value"]
    assert com_reserva.rest.ledger == []
