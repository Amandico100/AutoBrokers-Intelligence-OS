# -*- coding: utf-8 -*-
"""SPEC-116 · O TESTE DO FIO — a ROTA do papel chega ao payload que sai ao provedor.

O fio (SPEC-116 §4), atravessado com o MOTOR real e dublê SÓ na borda:

    agente do banco (agent_role='attendance', anthropic/claude-sonnet-5)
      → app/factories/llm_factory.py:LLMFactory.create_llm
      → app/factories/model_policy.py:resolve_chat_model   (shim de hoje)
      → model_policy.resolver('atendimento')  ← lê llm_papeis + llm_pricing
      → ChatAnthropic(...)  → _get_request_payload(...)  ← o que SAIRIA ao provedor

Bordas dubladas: o BANCO (`model_policy.leitor_do_banco` devolve o snapshot, e o
cliente Supabase do ledger é um banco mudo) e a REDE (nenhuma chamada sai: só se
monta o payload; chave literal falsa).

O que prova (G1 da SPEC-116 §9):
  · o payload leva o model da ROTA e nenhum `temperature` (Claude 5 dá 400);
  · trocar a ROTA no banco muda o payload SEM mudar uma vírgula do agente —
    e voltar a rota volta o payload (linha de controle);
  · a rota VENCE o `llm_model` gravado no agente, para papel com rota.

⚠️ O que é da F2 (exceção declarada, `xfail(strict=True)`): o ESFORÇO da rota
chegar ao payload e o provedor desconhecido virar ERRO na fábrica. Hoje a
fábrica ignora o effort para Claude e cai no gpt-4o-mini com provedor
desconhecido; a F2 liga a fábrica ao resolvedor e APAGA os dois xfail — com
`strict=True`, se passarem antes disso o teste fica vermelho e avisa.

Rodar (de backend/):  python -m pytest -q tests/test_o_fio_do_modelo.py
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

#: ⛔ 100% FALSA — não existe em provedor nenhum e não vem do ambiente.
CHAVE_FALSA = "sk-teste-chave-falsa-nao-existe"


class _BancoMudo:
    """Banco do LEDGER que responde vazio a tudo (zero rede). Mesmo dublê de
    `test_o_modelo_tem_relogio.py`: a fábrica monta o CostCallbackHandler, que
    constrói o UsageService, que abre o cliente Supabase."""

    class _Consulta:
        data: list = []

        def __getattr__(self, _nome):
            return lambda *a, **k: self

        def execute(self):
            return self

    client = None

    def table(self, _nome):
        return self._Consulta()


def _dublar_o_banco_do_ledger():
    import app.core.database as _db
    import app.services.usage_service as _uso

    _db.get_supabase_client = lambda: _BancoMudo()
    _uso.get_supabase_client = _db.get_supabase_client


_dublar_o_banco_do_ledger()

from app.factories import model_policy as MP  # noqa: E402
from app.factories.llm_factory import LLMFactory  # noqa: E402

SNAP = json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))

#: O agente como o banco o guarda hoje (📊 EVIDENCIAS/02: 8/8 anthropic/claude-sonnet-5).
AGENTE = {
    "agent_role": "attendance",
    "llm_provider": "anthropic",
    "llm_model": "claude-sonnet-5",
    "llm_temperature": 0.7,
    "llm_max_tokens": 1200,
    "reasoning_effort": "medium",
}


@pytest.fixture
def banco():
    """Dublê do BANCO das rotas: o snapshot, copiado — o teste pode trocar a rota."""
    cat = copy.deepcopy(SNAP["catalogo"])
    pap = copy.deepcopy(SNAP["papeis"])
    original = MP.leitor_do_banco
    MP.leitor_do_banco = lambda: (cat, pap)
    MP.limpar_cache()
    yield cat, pap
    MP.leitor_do_banco = original
    MP.limpar_cache()


def _trocar_rota(pap, papel, **campos):
    pap[papel].update(campos)
    pap[papel]["versao"] = int(pap[papel].get("versao") or 1) + 1
    MP.limpar_cache()


def _payload(agente):
    llm = LLMFactory.create_llm({}, agente, api_key=CHAVE_FALSA)
    return llm, llm._get_request_payload([("human", "oi")])


def test_fio_a_rota_semente_chega_ao_payload(banco):
    agente = dict(AGENTE)
    llm, p = _payload(agente)
    r = MP.resolver("atendimento")
    assert type(llm).__name__ == "ChatAnthropic"
    assert (r.model, r.origem, r.versao_da_rota) == ("claude-sonnet-5", "rota", 1)
    assert p["model"] == r.model
    assert "temperature" not in p, "Claude 5 rejeita temperature (400)"


def test_fio_trocar_a_rota_muda_o_payload_sem_mudar_o_agente(banco):
    _, pap = banco
    agente = dict(AGENTE)
    antes = dict(agente)

    _trocar_rota(pap, "atendimento", modelo_primario="claude-opus-5-5")
    _, p = _payload(agente)
    assert p["model"] == "claude-opus-5-5"
    assert MP.resolver("atendimento").versao_da_rota == 2
    assert agente == antes, "o agente não foi tocado"

    # LINHA DE CONTROLE: a rota de volta devolve o payload de antes
    _trocar_rota(pap, "atendimento", modelo_primario="claude-sonnet-5")
    _, p = _payload(dict(AGENTE))
    assert p["model"] == "claude-sonnet-5"


def test_fio_a_rota_vence_o_modelo_gravado_no_agente(banco):
    agente = dict(AGENTE, llm_model="claude-opus-5")
    _, p = _payload(agente)
    assert p["model"] == MP.resolver("atendimento").model == "claude-sonnet-5"


def test_fio_chat_principal_segue_a_sua_rota_e_nao_a_do_atendimento(banco):
    _, pap = banco
    _trocar_rota(pap, "chat_principal", modelo_primario="claude-opus-5")
    _, p_core = _payload(dict(AGENTE, agent_role="core"))
    _, p_atend = _payload(dict(AGENTE))
    assert (p_core["model"], p_atend["model"]) == ("claude-opus-5", "claude-sonnet-5")


@pytest.mark.xfail(strict=True, reason="F2 liga a fábrica ao resolvedor: effort da rota no payload")
def test_fio_o_esforco_da_rota_chega_ao_payload(banco):
    _, pap = banco
    _trocar_rota(pap, "atendimento", esforco="low")
    _, p = _payload(dict(AGENTE))
    assert (p.get("output_config") or {}).get("effort") == "low", p.keys()


@pytest.mark.xfail(strict=True, reason="F2: provedor desconhecido na fábrica vira ERRO (hoje cai no gpt-4o-mini)")
def test_fio_provedor_desconhecido_na_fabrica_e_erro(banco):
    with pytest.raises(MP.ModeloNaoResolvido):
        LLMFactory.create_llm(
            {}, dict(AGENTE, agent_role="subagent", llm_provider="moonshot", llm_model="kimi-k3"),
            api_key=CHAVE_FALSA)
