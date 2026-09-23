# -*- coding: utf-8 -*-
"""SPEC-116 F2 · G4 — a fábrica constrói CADA modelo do jeito que o provedor exige.

Chama o MOTOR (CLAUDE.md §9.4): `LLMFactory` real → adaptador → objeto do
LangChain → `_get_request_payload` (o que SAIRIA ao provedor). Borda dublada:
o BANCO (snapshot versionado como dublê de `llm_papeis`/`llm_pricing`) e a REDE
(nenhuma chamada sai; chaves literais falsas).

  · Sonnet 5 / Opus 5.5 → `output_config.effort` da rota; sem sampling
  · Opus 5.5 → NUNCA `tool_choice` any/tool nem `thinking` disabled (400)
  · Opus 4.8 → sem temperature, decidido pelo CATÁLOGO (não por prefixo)
  · GPT-6 Sol → Responses API, `reasoning.effort`, `store=False`, sem
    temperature e sem `stream_options`; gpt-4o continua em chat_completions
  · Gemini 3.8 → `thinking_level`
  · OpenAI-compatível (DeepSeek) → UMA linha do catálogo: base_url + chave do
    `api_key_env`, esforço no `reasoning_effort`
  · chave: provedor desconhecido é ERRO (antes: a chave da OpenAI)

Rodar (de backend/):  .venv/Scripts/python -m pytest -q tests/test_spec116_f2_adaptadores.py
"""
from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.environ["SEM_REDE"] = "1"

CHAVE_FALSA = "sk-teste-chave-falsa-nao-existe"


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

from langchain_core.tools import tool  # noqa: E402

from app.core import utils as U  # noqa: E402
from app.factories import model_policy as MP  # noqa: E402
from app.factories.llm_factory import LLMFactory  # noqa: E402

SNAP = json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def banco():
    cat = copy.deepcopy(SNAP["catalogo"])
    pap = copy.deepcopy(SNAP["papeis"])
    original = MP.leitor_do_banco
    MP.leitor_do_banco = lambda: (cat, pap)
    MP.limpar_cache()
    yield cat, pap
    MP.leitor_do_banco = original
    MP.limpar_cache()


def _rota(pap, papel, **campos):
    pap[papel].update(campos)
    pap[papel]["versao"] = int(pap[papel].get("versao") or 1) + 1
    MP.limpar_cache()


@tool
def consultar_apolice(numero: str) -> str:
    """Consulta uma apólice pelo número."""
    return "ok"


def _llm(papel, **kw):
    return LLMFactory.create_llm({}, {"llm_temperature": 0.4}, api_key=CHAVE_FALSA, papel=papel, **kw)


def _payload(llm, **kw):
    return llm._get_request_payload([("human", "oi")], **kw)


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("modelo,esforco", [("claude-sonnet-5", "low"), ("claude-opus-5-5", "medium")])
def test_claude_recebe_o_esforco_da_rota_e_nenhum_sampling(banco, modelo, esforco):
    _, pap = banco
    _rota(pap, "atendimento", modelo_primario=modelo, esforco=esforco)
    p = _payload(_llm("atendimento"))
    assert p["model"] == modelo
    assert (p.get("output_config") or {}).get("effort") == esforco, p.get("output_config")
    assert not {"temperature", "top_p", "top_k"} & set(p), p.keys()
    assert "anthropic-beta" not in json.dumps(p.get("extra_headers") or {}), "header beta obsoleto"


def test_opus_55_nunca_recebe_tool_choice_forcado(banco):
    """Opus 5.5 → 400 com tool_choice any/tool. `bind_tools(tool_choice='any')`
    é o que o LangChain faz em `with_structured_output` — a fábrica rebaixa para auto."""
    _, pap = banco
    _rota(pap, "atendimento", modelo_primario="claude-opus-5-5", esforco="medium")
    llm = _llm("atendimento")
    for escolha in ("any", "consultar_apolice"):
        ligado = llm.bind_tools([consultar_apolice], tool_choice=escolha)
        p = llm._get_request_payload([("human", "oi")], **ligado.kwargs)
        assert (p.get("tool_choice") or {}).get("type") == "auto", (escolha, p.get("tool_choice"))
        assert (p.get("thinking") or {}).get("type") not in ("disabled", "enabled"), p.get("thinking")
        assert p["tools"][0]["name"] == "consultar_apolice"


def test_controle_sonnet_5_aceita_tool_choice_forcado(banco):
    """LINHA DE CONTROLE: quem aceita (Sonnet 5, tool_choice_forcado_ok=true)
    recebe o forçado — o guarda sabe diferenciar, não rebaixa todo mundo."""
    _, pap = banco
    _rota(pap, "atendimento", modelo_primario="claude-sonnet-5")
    llm = _llm("atendimento")
    ligado = llm.bind_tools([consultar_apolice], tool_choice="any")
    p = llm._get_request_payload([("human", "oi")], **ligado.kwargs)
    assert (p.get("tool_choice") or {}).get("type") == "any", p.get("tool_choice")


def test_opus_48_sem_temperature_pelo_catalogo(banco):
    """Opus 4.8 dá 400 com sampling; a regra velha (prefixo da família 5) deixava passar."""
    r = MP.resolver("brand_capture", override={"provider": "anthropic", "model": "claude-opus-4-8"})
    p = _payload(LLMFactory.create_llm({}, {"llm_temperature": 0.4}, api_key=CHAVE_FALSA,
                                       modelo_resolvido=r))
    assert "temperature" not in p and "temperature" not in (p.get("extra_body") or {}), p


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------
def test_gpt6_sol_pela_responses_com_esforco_e_store_false(banco):
    _, pap = banco
    _rota(pap, "atendimento", provider="openai", modelo_primario="gpt-6-sol", esforco="low")
    llm = _llm("atendimento")
    ligado = llm.bind_tools([consultar_apolice])
    p = llm._get_request_payload([("human", "oi")], **ligado.kwargs)
    assert p["model"] == "gpt-6-sol"
    assert "input" in p and "messages" not in p, "Responses API"
    assert p["reasoning"]["effort"] == "low"
    assert p["store"] is False
    assert "reasoning.encrypted_content" in (p.get("include") or [])
    assert "temperature" not in p and "stream_options" not in p, p.keys()
    assert p["tools"][0]["name"] == "consultar_apolice"


def test_gpt4o_continua_em_chat_completions_com_temperature(banco):
    # 🔴 (conserto único — §9.3): a afirmação é sobre o ADAPTADOR do gpt-4o, e
    # dependia de `portal_decisao` ainda estar no seed (gpt-4o). A `_04` trocou a
    # rota; o teste passa a DECLARAR a rota que prova — a lição migra, o
    # comportamento guardado (chat completions + temperature) é o mesmo.
    _, pap = banco
    _rota(pap, "portal_decisao", provider="openai", modelo_primario="gpt-4o", esforco=None)
    p = _payload(_llm("portal_decisao"))
    assert p["model"] == "gpt-4o"
    assert "messages" in p and "input" not in p
    assert p["temperature"] == 0.4
    assert p["stream_options"] == {"include_usage": True}


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------
def test_gemini_38_recebe_thinking_level(banco, monkeypatch):
    _, pap = banco
    _rota(pap, "brand_capture", provider="google", modelo_primario="gemini-3.8-flash", esforco="low")
    llm = _llm("brand_capture")
    assert type(llm).__name__ == "ChatGoogleGenerativeAI"
    assert llm.thinking_level == "low"


# ---------------------------------------------------------------------------
# OpenAI-compatível genérico: UMA linha do catálogo
# ---------------------------------------------------------------------------
def test_provedor_compativel_entra_por_uma_linha_do_catalogo(banco, monkeypatch):
    _, pap = banco
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-teste-deepseek-falsa")
    _rota(pap, "brand_capture", provider="deepseek", modelo_primario="deepseek-flash", esforco="high")
    llm = LLMFactory.create_llm({}, {}, papel="brand_capture")
    assert type(llm).__name__ == "ChatOpenAICompativel"
    assert str(llm.openai_api_base).rstrip("/") == "https://api.deepseek.com"
    assert llm.openai_api_key.get_secret_value() == "sk-teste-deepseek-falsa"
    p = _payload(llm)
    assert p["model"] == "deepseek-flash" and p.get("reasoning_effort") == "high", p


def test_linha_compativel_sem_base_url_e_erro(banco, monkeypatch):
    cat, pap = banco
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-teste-deepseek-falsa")
    cat["deepseek-flash"]["base_url"] = None
    _rota(pap, "brand_capture", provider="deepseek", modelo_primario="deepseek-flash")
    with pytest.raises(MP.ModeloNaoResolvido):
        LLMFactory.create_llm({}, {}, papel="brand_capture")


# ---------------------------------------------------------------------------
# Chamador de plataforma sem papel: o modelo DELE, se governado — não a rota do chat
# ---------------------------------------------------------------------------
def test_chamador_de_plataforma_sem_agent_role_nao_herda_a_rota_do_chat(banco):
    """📊 o despacho de produção roda claude-opus-5; `papel_do_agente(None)` é
    chat_principal (Sonnet 5). Sem `agent_role` no dicionário = `sem_papel`."""
    llm = LLMFactory.create_llm({}, {"llm_provider": "anthropic", "llm_model": "claude-opus-5"},
                                api_key=CHAVE_FALSA)
    assert _payload(llm)["model"] == "claude-opus-5"
    with pytest.raises(MP.ModeloNaoResolvido):  # e o que não é governado é ERRO
        LLMFactory.create_llm({}, {"llm_provider": "anthropic",
                                   "llm_model": "claude-3-5-sonnet-20241022"},
                              api_key=CHAVE_FALSA)


# ---------------------------------------------------------------------------
# A chave
# ---------------------------------------------------------------------------
def test_chave_de_provedor_desconhecido_e_erro_e_nunca_a_da_openai(banco, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste-openai-falsa")
    with pytest.raises(U.ChaveNaoResolvida) as info:
        U.get_api_key_for_provider("moonshot", "kimi-k3")
    assert isinstance(info.value, ValueError) and isinstance(info.value, MP.ModeloNaoResolvido)


def test_chave_vem_do_api_key_env_do_catalogo(banco, monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "sk-teste-xai-falsa")
    assert U.get_api_key_for_provider("xai") == "sk-teste-xai-falsa"
    assert U.get_api_key_for_provider(None, "grok-4.7") == "sk-teste-xai-falsa"
    monkeypatch.delenv("XAI_API_KEY")
    with pytest.raises(ValueError):
        U.get_api_key_for_provider("xai")


def test_suportados_derivam_do_catalogo(banco):
    from app.services.langchain_service import SUPPORTED_PROVIDERS

    assert "claude-sonnet-5" in SUPPORTED_PROVIDERS["anthropic"]
    assert "gpt-6-sol" in SUPPORTED_PROVIDERS["openai"]
    assert "claude-3-5-sonnet-20241022" not in SUPPORTED_PROVIDERS["anthropic"]  # BLOCKED
    assert "openrouter" in SUPPORTED_PROVIDERS
    assert "text-embedding-3-small" not in SUPPORTED_PROVIDERS.get("openai", [])  # não é conversa
