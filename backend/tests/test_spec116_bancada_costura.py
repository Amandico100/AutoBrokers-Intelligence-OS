# -*- coding: utf-8 -*-
"""SPEC-116 F5b — a COSTURA da bancada: resolvedor + fábrica REAIS, isolados do produto.

O braço real sai de `LLMFactory.criar_de_resolvido` (o MESMO adaptador por
provedor do produto). Três coisas têm de valer, e cada uma tem a sua LINHA DE
CONTROLE (CLAUDE.md §9.2/§9.3 — guarda que não consegue ficar vermelho é carimbo):

  1. o DISJUNTOR de produção não escuta a bancada: 5 × 429 do braço não abrem o
     breaker; um sucesso do braço não FECHA um breaker aberto.
     CONTROLE: o mesmo braço SEM o isolamento abre o breaker.
  2. o LEDGER de produção recebe cada chamada como service_type='bancada',
     company_id NULO (visível, nunca faturado).
  3. o custo de cada caso = usage_metadata × preço do catálogo, pela MESMA conta
     do ledger (`usage_service.calculate_cost`) — nunca inventado.

Borda: a rede do provedor (o `_agenerate` do cliente real é trocado), o Redis
(o degrau de memória do próprio relógio) e o escritor do ledger
(`UsageService.track_cost_sync`). O motor — grafo, nó, fábrica, callbacks — é o real.
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from langchain_core.messages import AIMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402

from app.core import relogio_do_modelo as R  # noqa: E402
from app.factories import llm_factory as LF  # noqa: E402
from app.factories import model_policy as MP  # noqa: E402
from app.services import usage_service as US  # noqa: E402
from app.services.evals import bancada as B  # noqa: E402

BRACO = "anthropic:claude-sonnet-5:low"
CHAVE_FALSA = "chave-de-teste-sem-rede"


def _caso(chave: str) -> dict:
    for c in B.carregar_casos("atendimento"):
        if c["chave"] == chave:
            return c
    raise AssertionError(chave)


class Erro429(Exception):
    """O que um SDK levanta num 429 (o relógio lê `status_code`)."""
    status_code = 429


class _LedgerCapturado(US.UsageService):
    """O `UsageService` REAL (preço e conta de custo do catálogo), sem banco:
    o que ele gravaria em `token_usage_logs` fica numa lista."""

    def __init__(self):  # noqa: D107 — sem cliente de banco
        self.supabase = None
        self.linhas = []

    def _ensure_cache_loaded(self):
        return None

    def track_cost_sync(self, **kw):
        kw["total_cost_usd"] = self.calculate_cost(
            kw["model"], kw["input_tokens"], kw.get("output_tokens", 0),
            kw.get("cache_creation_tokens", 0), kw.get("cache_read_tokens", 0),
            kw.get("cached_tokens", 0))
        self.linhas.append(kw)
        return True


@pytest.fixture
def borda(monkeypatch):
    """Snapshot do catálogo no lugar do banco, Redis de memória, ledger capturado."""
    monkeypatch.setattr(MP, "_ler_banco", lambda: (_ for _ in ()).throw(RuntimeError("sem banco no teste")))
    monkeypatch.setitem(MP._cache, "dados", None)
    monkeypatch.setattr(US, "_pricing_cache", US._precos_do_snapshot())
    monkeypatch.setattr(US, "_cache_loaded_at", 10 ** 12)
    ledger = _LedgerCapturado()
    monkeypatch.setattr(US, "_usage_service", ledger)
    redis = R._RedisDeMemoria({})

    async def _cliente():
        return redis

    monkeypatch.setattr(R, "_cliente", _cliente)
    monkeypatch.setattr(LF.ChatAnthropicGovernado, "_should_stream", lambda self, **k: False)
    return {"ledger": ledger, "redis": redis}


def _provedor_que_falha(monkeypatch):
    async def _falha(self, messages, stop=None, run_manager=None, **kw):
        raise Erro429("rate limit (injetado na borda do provedor)")

    monkeypatch.setattr(LF.ChatAnthropicGovernado, "_agenerate", _falha)


def _provedor_que_responde(monkeypatch, uso=(1200, 80)):
    async def _ok(self, messages, stop=None, run_manager=None, **kw):
        msg = AIMessage(content="Certo, vou verificar a sua apólice.",
                        usage_metadata={"input_tokens": uso[0], "output_tokens": uso[1],
                                        "total_tokens": uso[0] + uso[1]},
                        response_metadata={"model_name": "claude-sonnet-5"})
        return ChatResult(generations=[ChatGeneration(message=msg)],
                          llm_output={"model_name": "claude-sonnet-5"})

    monkeypatch.setattr(LF.ChatAnthropicGovernado, "_agenerate", _ok)


def _construir_isolado(resolvido, callbacks):
    return B.construir_llm_padrao(resolvido, callbacks, api_key=CHAVE_FALSA)


def _construir_sem_isolamento(resolvido, callbacks):
    """CONTROLE: a fábrica crua, com o relógio de produção pendurado."""
    return LF.LLMFactory.criar_de_resolvido(resolvido, api_key=CHAVE_FALSA,
                                            service_type=B.SERVICE_TYPE_DA_BANCADA)


def _estado():
    return asyncio.run(R.estado_do_breaker("anthropic"))["estado"]


def _rodar(construir, k=1):
    return B.rodar_bancada("atendimento", [BRACO], [_caso("atd-n1-cpf-guincho")], k=k, nivel="N1",
                           construir_llm=construir, teto_usd=5,
                           precos=lambda b: B.preco_do_catalogo(b))


# ---------------------------------------------------------------------------
# 1 · o disjuntor de produção não escuta a bancada
# ---------------------------------------------------------------------------
def test_429_da_bancada_nao_abre_o_breaker_do_produto(borda, monkeypatch):
    _provedor_que_falha(monkeypatch)
    assert R.BREAKER_FALHAS >= 1
    rel = _rodar(_construir_isolado, k=R.BREAKER_FALHAS)
    assert len(rel.resultados) == R.BREAKER_FALHAS
    assert all(r.resultado == "BLOCKED_BY_INFRA" and "Erro429" in (r.erro or "") for r in rel.resultados), \
        [(r.resultado, r.erro) for r in rel.resultados]
    assert _estado() == "fechado"
    assert not [k for k in borda["redis"].dados if k.startswith("llm_breaker")], borda["redis"].dados


def test_controle_sem_isolamento_o_mesmo_429_abre_o_breaker(borda, monkeypatch):
    """Prova de que o guarda de cima CONSEGUE ficar vermelho."""
    _provedor_que_falha(monkeypatch)
    _rodar(_construir_sem_isolamento, k=R.BREAKER_FALHAS)
    assert _estado() == "aberto"


def test_sucesso_da_bancada_nao_fecha_um_breaker_aberto(borda, monkeypatch):
    asyncio.run(R._abrir(borda["redis"], *R._chaves("anthropic")))
    assert _estado() == "aberto"
    _provedor_que_responde(monkeypatch)
    rel = _rodar(_construir_isolado)
    assert rel.resultados[0].rastro["chamadas_ao_modelo"] >= 1
    assert _estado() == "aberto", "a bancada fechou o breaker do produto (registrar_sucesso)"


def test_controle_sem_isolamento_o_sucesso_fecha_o_breaker(borda, monkeypatch):
    asyncio.run(R._abrir(borda["redis"], *R._chaves("anthropic")))
    _provedor_que_responde(monkeypatch)
    _rodar(_construir_sem_isolamento)
    assert _estado() == "fechado"


# ---------------------------------------------------------------------------
# 2 · o ledger: service_type='bancada', company_id NULO — e 3 · o custo é o do catálogo
# ---------------------------------------------------------------------------
def test_ledger_grava_como_bancada_sem_corretora_e_o_custo_bate(borda, monkeypatch):
    _provedor_que_responde(monkeypatch, uso=(1200, 80))
    rel = _rodar(_construir_isolado)
    r = rel.resultados[0]
    linhas = borda["ledger"].linhas
    assert linhas, "nenhuma chamada chegou ao ledger — o custo real ficaria invisível"
    assert len(linhas) == r.rastro["chamadas_ao_modelo"]
    for l in linhas:
        assert l["service_type"] == "bancada", l["service_type"]
        assert l["company_id"] is None and l["agent_id"] is None
        assert l["details"]["papel"] == "atendimento" and l["details"]["origem_da_rota"] == "bancada"
        assert l["model"] == "claude-sonnet-5"
    # o custo do caso = soma do que o ledger gravou, pela MESMA conta, com preço do catálogo
    assert r.custo_usd > 0
    assert r.custo_usd == pytest.approx(sum(l["total_cost_usd"] for l in linhas), rel=1e-9)
    esperado = US.UsageService.calculate_cost(borda["ledger"], "claude-sonnet-5", 1200, 80) * len(linhas)
    assert r.custo_usd == pytest.approx(esperado, rel=1e-9)
    assert r.tokens["in"] == 1200 * len(linhas) and r.tokens["out"] == 80 * len(linhas)


def test_braco_que_escreveria_como_produto_nao_roda(borda, monkeypatch):
    """Se a fábrica devolvesse o custo como 'plataforma' (ou com corretora), a
    bancada RECUSA construir o braço — não mede às custas do faturamento."""
    _provedor_que_responde(monkeypatch)
    resolvido = MP.resolver("atendimento", override={"provider": "anthropic", "model": "claude-sonnet-5",
                                                     "effort": "low"})
    cru = LF.LLMFactory.criar_de_resolvido(resolvido, api_key=CHAVE_FALSA, service_type="plataforma")
    with pytest.raises(B.BancadaSemIsolamento):
        B.isolar_do_produto(cru)
    cru = LF.LLMFactory.criar_de_resolvido(resolvido, api_key=CHAVE_FALSA, service_type="bancada",
                                           company_id="00000000-0000-4000-8000-0000000000a1")
    with pytest.raises(B.BancadaSemIsolamento):
        B.isolar_do_produto(cru)


def test_preco_desconhecido_recusa_o_braco(borda):
    assert B.preco_do_catalogo(B.Braco.de("openai:modelo-que-nao-existe")) is None
    p = B.preco_do_catalogo(B.Braco.de(BRACO))
    assert p["entrada"] == US._pricing_cache["claude-sonnet-5"]["input"]
    assert p["saida"] == US._pricing_cache["claude-sonnet-5"]["output"]


def test_reserva_do_teto_usa_o_max_tokens_do_braco_e_nao_o_do_catalogo(borda):
    """128 mil tokens de saída do catálogo fariam a reserva de UMA chamada de
    Sonnet custar US$ 1,28 — e um teto de US$ 0,50 nunca deixaria rodar."""
    resolvido = MP.resolver("atendimento", override={"provider": "anthropic", "model": "claude-sonnet-5"})
    assert int(resolvido.capacidades["max_output"]) > B.MAX_TOKENS_DA_BANCADA
    llm = _construir_isolado(resolvido, [])
    assert llm.max_tokens == B.MAX_TOKENS_DA_BANCADA
