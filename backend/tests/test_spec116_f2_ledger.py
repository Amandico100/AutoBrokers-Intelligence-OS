# -*- coding: utf-8 -*-
"""SPEC-116 F2 · G8 — o ledger diz QUEM pediu o quê e o que RESPONDEU.

O callback é o REAL, e é o que a FÁBRICA anexou (`llm.callbacks[0]`, o mesmo
objeto que roda em produção). Borda dublada: o `usage_service` (captura o que
seria gravado em `token_usage_logs`) e o banco das rotas (snapshot).

`details` ganha: papel · modelo_pedido · modelo_resolvido · modelo_real ·
esforco · origem_da_rota · versao_da_rota · reserva_usada · motivo_reserva ·
tokens de raciocínio e de cache (leitura/escrita).

Rodar (de backend/):  .venv/Scripts/python -m pytest -q tests/test_spec116_f2_ledger.py
"""
from __future__ import annotations

import copy
import json
import os
import sys
import uuid
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.environ["SEM_REDE"] = "1"


class _BancoMudo:
    class _Consulta:
        data: list = []

        def __getattr__(self, _nome):
            return lambda *a, **k: self

        def execute(self):
            return self

    client = None

    def table(self, _nome):
        return self._Consulta()


import app.core.database as _db  # noqa: E402
import app.services.usage_service as _uso  # noqa: E402

_db.get_supabase_client = lambda: _BancoMudo()
_uso.get_supabase_client = _db.get_supabase_client

from langchain_core.messages import AIMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, LLMResult  # noqa: E402

from app.factories import model_policy as MP  # noqa: E402
from app.factories.llm_factory import LLMFactory  # noqa: E402

SNAP = json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))

#: 🔴 (24/09/2026 — conclusão da Onda A) PRODUÇÃO só aceita APPROVED. Estes testes
#: provam a MECÂNICA de trocar a rota (provedor, adaptador, temperatura, ledger)
#: usando modelos LEGADOS como dublês de "outro modelo" — no dublê eles são
#: promovidos a APPROVED. A regra de lifecycle (e o mínimo de esforço) é provada
#: em `test_nenhum_modelo_fora_do_catalogo.py` (§9.3: a lição migra, não morre).
MODELOS_LEGADOS_DUBLES = ("claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5",
                          "claude-haiku-4-5-20251001", "gpt-4o", "gpt-4o-mini",
                          "gpt-4o-mini-2024-07-18", "whisper-1")


def _legados_como_dubles(cat):
    for m in MODELOS_LEGADOS_DUBLES:
        if m in cat:
            cat[m]["lifecycle"] = "APPROVED"
    return cat

CHAVE_FALSA = "sk-teste-chave-falsa-nao-existe"
AGENTE = {"agent_role": "attendance", "llm_provider": "anthropic", "llm_model": "claude-sonnet-5",
          "reasoning_effort": "medium"}


class _UsoCapturado:
    def __init__(self):
        self.linhas = []
        self.supabase = None

    def track_cost_sync(self, **kw):
        self.linhas.append(kw)

    def calculate_cost(self, *a, **k):
        return 0.0


@pytest.fixture
def banco():
    cat = _legados_como_dubles(copy.deepcopy(SNAP["catalogo"]))
    pap = copy.deepcopy(SNAP["papeis"])
    original = MP.leitor_do_banco
    MP.leitor_do_banco = lambda: (cat, pap)
    MP.limpar_cache()
    yield cat, pap
    MP.leitor_do_banco = original
    MP.limpar_cache()


def _chamada(handler, *, modelo_real, metadados=None, cache_read=40, cache_creation=10):
    uso = _UsoCapturado()
    handler.usage_service = uso
    rid = uuid.uuid4()
    handler.on_chat_model_start({}, [[]], run_id=rid, metadata=metadados or {})
    msg = AIMessage(content="ok", response_metadata={"model_name": modelo_real},
                    usage_metadata={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150,
                                    "input_token_details": {"cache_read": cache_read,
                                                            "cache_creation": cache_creation},
                                    "output_token_details": {"reasoning": 30}})
    handler.on_llm_end(LLMResult(generations=[[ChatGeneration(message=msg)]]), run_id=rid)
    assert len(uso.linhas) == 1, uso.linhas
    return uso.linhas[0]


def test_ledger_do_atendimento_grava_pedido_resolvido_e_real(banco):
    _, pap = banco
    # dublê: a rota Anthropic de 23/09 (o balde de cache da Anthropic é o sujeito aqui)
    pap["atendimento"].update(provider="anthropic", modelo_primario="claude-sonnet-5", esforco="low", versao=7)
    MP.limpar_cache()
    llm = LLMFactory.create_llm({}, dict(AGENTE, llm_model="claude-opus-5"), api_key=CHAVE_FALSA,
                                company_id="11111111-1111-1111-1111-111111111111")
    linha = _chamada(llm.callbacks[0], modelo_real="claude-sonnet-5-20260630")
    d = linha["details"]
    assert d["papel"] == "atendimento"
    assert d["modelo_pedido"] == "claude-opus-5", "o que o AGENTE tinha gravado"
    assert d["modelo_resolvido"] == "claude-sonnet-5", "o que a ROTA mandou"
    assert d["modelo_real"] == "claude-sonnet-5-20260630", "o que o PROVEDOR disse que respondeu"
    assert (d["esforco"], d["origem_da_rota"], d["versao_da_rota"]) == ("low", "rota", 7), d
    assert d["reserva_usada"] is False and d.get("motivo_reserva") is None
    assert d["reasoning_tokens"] == 30, "a chave do LangChain é `reasoning`"
    assert (d["tokens_cache_leitura"], d["tokens_cache_escrita"]) == (40, 10)
    # Anthropic: o cache fica no balde da Anthropic
    assert (linha["cache_read_tokens"], linha["cached_tokens"]) == (40, 0)
    assert linha["model"] == "claude-sonnet-5-20260630"


def test_ledger_openai_poe_o_cache_no_balde_da_openai(banco, monkeypatch):
    """📊 F12: langchain-openai põe o cache da OpenAI em `cache_read` (balde da
    Anthropic). O provedor decide o balde."""
    _, pap = banco
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste-openai-falsa")
    pap["atendimento"].update(provider="openai", modelo_primario="gpt-6-sol", esforco="medium")
    MP.limpar_cache()
    llm = LLMFactory.create_llm({}, dict(AGENTE), company_id="11111111-1111-1111-1111-111111111111")
    linha = _chamada(llm.callbacks[0], modelo_real="gpt-6-sol-2026-09-22", cache_creation=0)
    assert (linha["cached_tokens"], linha["cache_read_tokens"]) == (40, 0), linha
    assert linha["details"]["modelo_resolvido"] == "gpt-6-sol"


def test_ledger_da_reserva_grava_o_motivo(banco):
    r = MP.resolver("brand_capture", override={"provider": "anthropic", "model": "claude-haiku-4-5"})
    llm = LLMFactory.create_llm({}, {}, api_key=CHAVE_FALSA, modelo_resolvido=r, reserva_usada=True)
    d = _chamada(llm.callbacks[0], modelo_real="claude-haiku-4-5",
                 metadados={"motivo_reserva": "5xx"})["details"]
    assert (d["reserva_usada"], d["motivo_reserva"]) == (True, "5xx"), d


def test_o_provedor_do_ledger_vem_da_fabrica_e_nao_de_prefixo(banco, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-teste-deepseek-falsa")
    r = MP.resolver("brand_capture", override={"provider": "deepseek", "model": "deepseek-flash"})
    llm = LLMFactory.create_llm({}, {}, modelo_resolvido=r)
    h = llm.callbacks[0]
    assert h._provedor_do_modelo("deepseek-flash") == "deepseek"
    from app.core.callbacks.cost_callback import provedor_pelo_catalogo

    assert provedor_pelo_catalogo("gpt-4o-mini-2024-07-18") == "openai"
    assert provedor_pelo_catalogo("modelo-que-ninguem-conhece") is None
