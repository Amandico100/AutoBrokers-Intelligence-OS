# -*- coding: utf-8 -*-
"""SPEC-116 U3 — o SHIM da fábrica de hoje (`resolve_chat_model`) e o papel do agente.

🔴 VERDADE VENCIDA SUBSTITUÍDA (CLAUDE.md §9.3). Este arquivo afirmava, desde a
SPEC-013 FB-1: "core + gpt-4o-mini → promovido a gpt-4o (CORE_CHAT_MODEL)" e
"attendance + mini MANTÉM o mini". As duas frases eram a política: um modelo
velho escondido decidindo o chat do corretor, e o atendente do segurado preso no
mini (EVIDENCIAS/01 F1/F13). A lição migra, não morre:
  · o shim NÃO promove mais para gpt-4o, nem com CORE_CHAT_MODEL no ambiente;
  · papel com ROTA → o modelo da rota (atendimento incluso), mesmo provedor;
  · rota de outro provedor que o do agente → mantém o do agente (a fábrica de
    hoje escolhe o cliente pelo provedor do agente; até a F2, trocar quebraria);
  · rota inválida (lifecycle proibido) → mantém o do agente e registra ERRO.

Dublê SÓ do banco (`model_policy.leitor_do_banco` = snapshot copiado).
Rodar (de backend/):  python -m pytest -q tests/test_model_policy.py
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

from app.factories import model_policy as MP  # noqa: E402

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


def test_papel_do_agente():
    assert MP.papel_do_agente("core") == MP.papel_do_agente("") == MP.papel_do_agente(None) == "chat_principal"
    assert MP.papel_do_agente("attendance") == MP.papel_do_agente("insured_external") == "atendimento"
    assert MP.papel_do_agente("subagent") == MP.papel_do_agente("auxiliary") == "subagente"
    assert MP.is_core_chat_role("core") and MP.is_core_chat_role(None)
    assert not MP.is_core_chat_role("attendance")


def _outro_provedor(prov):
    """Um modelo legado (dublê APPROVED) de provedor DIFERENTE do da rota."""
    return "claude-sonnet-5" if prov == "openai" else "gpt-4o-mini"


def _mesmo_provedor(prov):
    return "gpt-4o-mini" if prov == "openai" else "claude-sonnet-5"


def test_shim_nao_promove_mais_para_gpt_4o(banco, monkeypatch):
    # (24/09/2026) o esperado vem da ROTA — antes afirmava "rota anthropic".
    _, pap = banco
    monkeypatch.setenv("CORE_CHAT_MODEL", "gpt-4o")
    prov = pap["chat_principal"]["provider"]
    outro = _outro_provedor(prov)
    # agente de outro provedor: mantém o do agente — nada de gpt-4o
    assert MP.resolve_chat_model("core", outro) == outro
    assert MP.resolve_chat_model(None, outro) == outro
    # mesmo provedor: a ROTA — e nunca o gpt-4o do env
    assert MP.resolve_chat_model("core", _mesmo_provedor(prov)) == pap["chat_principal"]["modelo_primario"] != "gpt-4o"


def test_shim_devolve_a_rota_quando_o_provedor_bate(banco):
    _, pap = banco
    prov = pap["atendimento"]["provider"]
    assert MP.resolve_chat_model("attendance", _mesmo_provedor(prov)) == pap["atendimento"]["modelo_primario"]
    pap["atendimento"].update(provider="anthropic", modelo_primario="claude-opus-5-5", esforco=None)
    MP.limpar_cache()
    assert MP.resolve_chat_model("attendance", "claude-sonnet-5") == "claude-opus-5-5"
    prov_core = pap["chat_principal"]["provider"]
    assert MP.resolve_chat_model("core", _mesmo_provedor(prov_core)) == pap["chat_principal"]["modelo_primario"]


def test_shim_mantem_o_do_agente_quando_a_rota_e_de_outro_provedor(banco):
    # 📊 toda corretora nova nascia openai/gpt-4o-mini (EVIDENCIAS/01 §c) — a fábrica
    # de hoje não pode receber um modelo de OUTRO provedor pelo shim.
    _, pap = banco
    outro = _outro_provedor(pap["atendimento"]["provider"])
    assert MP.resolve_chat_model("attendance", outro) == outro


def test_shim_mantem_o_do_agente_quando_a_rota_e_invalida(banco):
    _, pap = banco
    pap["atendimento"]["modelo_primario"] = "claude-3-5-sonnet-20241022"  # BLOCKED
    MP.limpar_cache()
    assert MP.resolve_chat_model("attendance", "claude-sonnet-5") == "claude-sonnet-5"


def test_resolver_papel_sem_rota_usa_o_agente_governado(banco):
    r = MP.resolver("agente_custom", agente={"llm_provider": "anthropic", "llm_model": "claude-opus-5-5",
                                              "reasoning_effort": "medium"})
    assert (r.model, r.origem, r.effort, r.classe_de_dado) == ("claude-opus-5-5", "agente", "medium", "pii")
    # esforço gravado que o modelo não aceita (Haiku não tem effort) → default do provedor
    r = MP.resolver("agente_custom", agente={"llm_provider": "anthropic",
                                              "llm_model": "claude-haiku-4-5-20251001",
                                              "reasoning_effort": "medium"})
    assert r.effort is None
    with pytest.raises(MP.ModeloNaoResolvido):   # modelo legado do agente não passa
        MP.resolver("agente_custom", agente={"llm_provider": "openai", "llm_model": "gpt-3.5-turbo"})


def test_resolver_classe_efetiva_e_a_mais_sensivel(banco):
    # extrator_planos é publico; se o chamador declara pii, Fable (sem pii) é recusado
    r = MP.resolver("extrator_planos", override={"provider": "anthropic", "model": "claude-fable-5-1"})
    assert r.classe_de_dado == "publico"
    with pytest.raises(MP.ModeloNaoResolvido, match="pii"):
        MP.resolver("extrator_planos", classe_de_dado="pii",
                    override={"provider": "anthropic", "model": "claude-fable-5-1"})


def test_resolver_esforco_fora_dos_niveis_e_erro(banco):
    with pytest.raises(MP.ModeloNaoResolvido):
        MP.resolver("atendimento", override={"provider": "anthropic", "model": "claude-sonnet-5",
                                             "effort": "turbo"})
    with pytest.raises(MP.ModeloNaoResolvido):   # gpt-6-astra não tem 'none'
        MP.resolver("atendimento", override={"provider": "openai", "model": "gpt-6-astra",
                                             "effort": "none"})


def test_sem_banco_o_resolvedor_cai_no_snapshot():
    original = MP.leitor_do_banco

    def _caido():
        raise ConnectionError("banco fora")

    MP.leitor_do_banco = _caido
    MP.limpar_cache()
    try:
        r = MP.resolver("atendimento")
        assert (r.model, r.origem) == (SNAP["papeis"]["atendimento"]["modelo_primario"], "snapshot")
    finally:
        MP.leitor_do_banco = original
        MP.limpar_cache()
