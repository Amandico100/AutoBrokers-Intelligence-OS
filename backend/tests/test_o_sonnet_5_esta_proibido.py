# -*- coding: utf-8 -*-
"""SPEC-121 F7 — o Sonnet 5 está PROIBIDO; o Sonnet 5.5 entra no lugar dele.

Ordem do Founder (29/09/2026, literal): "Instale o Sonnet 5.5 no lugar do Sonnet 5,
e o Sonnet 5 deve ser substituído. Não deve mais estar no AutoBrokers. Precisa ser
o Sonnet 5.5 ou senão o Opus 5.5. Sonnet 5 está PROIBIDO de ser usado no sistema."

🔴 CHAMA O MOTOR (CLAUDE.md §9.4): `model_policy.resolver` e `LLMFactory` reais →
adaptador `ChatAnthropicGovernado` → `_get_request_payload` (o que SAIRIA ao
provedor). Borda dublada: o BANCO (o snapshot versionado, SEM promover legado) e
a REDE (nenhuma chamada sai; chave literal falsa).

  (i)   pedir `claude-sonnet-5` por QUALQUER porta (rota, agente, corretora,
        bancada, botão "testar conexão") é RECUSADO — nunca chega ao provedor;
  (ii)  o pedido montado para `claude-sonnet-5-5` não leva tool_choice any/tool,
        nem temperature/top_p/top_k, nem thinking disabled (vira between_tools
        quando o esforço cabe, senão sai);
  (iii) nenhum literal `claude-sonnet-5` (exato) no código de produto;
  (iv)  o snapshot e a migration 20260929_01 (o texto que o Postgres aplicou)
        concordam sobre os dois modelos.

Rodar (de backend/):  .venv/Scripts/python -m pytest -q tests/test_o_sonnet_5_esta_proibido.py
"""
from __future__ import annotations

import copy
import json
import os
import re
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
RAIZ_REPO = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.environ["SEM_REDE"] = "1"

CHAVE_FALSA = "sk-ant-teste-chave-falsa-nao-existe"
PROIBIDO = "claude-sonnet-5"
NOVO = "claude-sonnet-5-5"
MIGRATION = BACKEND / "supabase" / "migrations" / "20260929_01_spec121_sonnet_5_5.sql"


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

from app.factories import model_policy as MP  # noqa: E402
from app.factories.llm_factory import ChatAnthropicGovernado, LLMFactory  # noqa: E402
from app.factories.model_policy import ModeloNaoResolvido  # noqa: E402

SNAP = json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def banco():
    """O snapshot COMO ESTÁ — ⛔ sem promover legado a APPROVED (é o que se prova)."""
    cat = copy.deepcopy(SNAP["catalogo"])
    pap = copy.deepcopy(SNAP["papeis"])
    original = MP.leitor_do_banco
    MP.leitor_do_banco = lambda: (cat, pap)
    MP.limpar_cache()
    yield cat, pap
    MP.leitor_do_banco = original
    MP.limpar_cache()


@pytest.fixture
def rede_espiada(monkeypatch):
    """Se algum modelo Anthropic chegasse a gerar, a chamada passaria por aqui."""
    chamadas: list = []

    def _gerar(self, messages, stop=None, run_manager=None, **kw):  # noqa: ANN001
        chamadas.append(self._get_request_payload(messages, stop=stop, **kw)["model"])
        raise RuntimeError("rede dublada: nada sai")

    def _fluir(self, messages, stop=None, run_manager=None, **kw):  # noqa: ANN001
        _gerar(self, messages, stop=stop, **kw)
        yield  # pragma: no cover — nunca chega aqui

    # `streaming=True` (a fábrica liga) faz o `invoke` ir por `_stream`: as duas portas.
    monkeypatch.setattr(ChatAnthropicGovernado, "_generate", _gerar)
    monkeypatch.setattr(ChatAnthropicGovernado, "_stream", _fluir)
    return chamadas


@tool
def consultar_apolice(numero: str) -> str:
    """Consulta uma apólice pelo número."""
    return "ok"


def _rota(pap, papel, modelo, esforco):
    pap[papel].update(provider="anthropic", modelo_primario=modelo, esforco=esforco,
                      modelo_reserva=None, provider_reserva=None, esforco_reserva=None)
    MP.limpar_cache()


# ---------------------------------------------------------------------------
# (i) o Sonnet 5 é recusado por TODA porta — e nada chega ao provedor
# ---------------------------------------------------------------------------
PORTAS = {
    "rota do papel": lambda pap: (_rota(pap, "atendimento", PROIBIDO, "high"),
                                  LLMFactory.create_llm({}, {}, api_key=CHAVE_FALSA,
                                                        papel="atendimento").invoke("oi")),
    "agente sem papel": lambda pap: LLMFactory.create_llm(
        {}, {"llm_provider": "anthropic", "llm_model": PROIBIDO}, api_key=CHAVE_FALSA).invoke("oi"),
    "corretora sem papel": lambda pap: LLMFactory.create_llm(
        {"llm_provider": "anthropic", "llm_model": PROIBIDO}, None, api_key=CHAVE_FALSA).invoke("oi"),
    "bancada (override)": lambda pap: LLMFactory.criar_de_resolvido(
        MP.resolver("juiz_eval", override={"provider": "anthropic", "model": PROIBIDO}),
        api_key=CHAVE_FALSA).invoke("oi"),
    "testar conexão": lambda pap: LLMFactory.para_teste_de_conexao(
        "anthropic", PROIBIDO, api_key=CHAVE_FALSA).invoke("oi"),
}


@pytest.mark.parametrize("porta", sorted(PORTAS))
def test_o_sonnet_5_e_recusado_e_nunca_chega_ao_provedor(banco, rede_espiada, porta):
    _, pap = banco
    with pytest.raises(ModeloNaoResolvido, match="claude-sonnet-5'.*BLOCKED"):
        PORTAS[porta](pap)
    assert PROIBIDO not in rede_espiada, rede_espiada
    assert rede_espiada == [], "nenhuma chamada pode ter saído"


def test_controle_o_sonnet_5_5_passa_pelas_mesmas_portas(banco, rede_espiada):
    """LINHA DE CONTROLE: a MESMA porta, com o 5.5, chega à borda (e a borda dublada
    é que para). O guarda sabe diferenciar — não recusa todo Claude."""
    _, pap = banco
    _rota(pap, "atendimento", NOVO, "high")
    with pytest.raises(RuntimeError, match="rede dublada"):
        LLMFactory.create_llm({}, {}, api_key=CHAVE_FALSA, papel="atendimento").invoke("oi")
    with pytest.raises(RuntimeError, match="rede dublada"):
        LLMFactory.create_llm({}, {"llm_provider": "anthropic", "llm_model": NOVO},
                              api_key=CHAVE_FALSA).invoke("oi")
    assert rede_espiada == [NOVO, NOVO]


# ---------------------------------------------------------------------------
# (ii) o pedido do Sonnet 5.5 não leva o que dá 400
# ---------------------------------------------------------------------------
def _llm_55(pap, esforco):
    _rota(pap, "atendimento", NOVO, esforco)
    return LLMFactory.create_llm({}, {"llm_temperature": 0.4}, api_key=CHAVE_FALSA,
                                 papel="atendimento")


@pytest.mark.parametrize("escolha", ["any", "consultar_apolice"])
def test_sonnet_55_nunca_recebe_tool_choice_forcado_nem_sampling(banco, escolha):
    _, pap = banco
    llm = _llm_55(pap, "low")
    assert isinstance(llm, ChatAnthropicGovernado)
    ligado = llm.bind_tools([consultar_apolice], tool_choice=escolha)
    p = llm._get_request_payload([("human", "oi")], **ligado.kwargs)
    assert p["model"] == NOVO
    assert (p.get("tool_choice") or {}).get("type") == "auto", p.get("tool_choice")
    assert p["tools"][0]["name"] == "consultar_apolice"
    assert not {"temperature", "top_p", "top_k"} & (set(p) | set(p.get("extra_body") or {})), p
    assert (p.get("output_config") or {}).get("effort") == "low"
    assert (p.get("thinking") or {}).get("type") != "disabled", p.get("thinking")


def test_sonnet_55_sem_raciocinio_vira_between_tools_quando_o_esforco_cabe(banco):
    _, pap = banco
    llm = _llm_55(pap, "low")
    p = llm._get_request_payload([("human", "oi")], thinking={"type": "disabled"})
    assert p.get("thinking") == {"type": "between_tools"}, p.get("thinking")


def test_sonnet_55_sem_raciocinio_acima_do_teto_sai_do_payload(banco):
    """`between_tools` só vale com effort ≤ high: em xhigh o thinking sai (adaptive)."""
    _, pap = banco
    llm = _llm_55(pap, "xhigh")
    p = llm._get_request_payload([("human", "oi")], thinking={"type": "disabled"})
    assert "thinking" not in p or p["thinking"].get("type") not in ("disabled", "between_tools"), p


def test_controle_opus_55_sem_raciocinio_nao_ganha_between_tools(banco):
    """LINHA DE CONTROLE: o Opus 5.5 NÃO declara `raciocinio_desligado` → o thinking
    disabled só sai (como antes da SPEC-121). O between_tools vem do CATÁLOGO."""
    _, pap = banco
    _rota(pap, "atendimento", "claude-opus-5-5", "low")
    llm = LLMFactory.create_llm({}, {}, api_key=CHAVE_FALSA, papel="atendimento")
    p = llm._get_request_payload([("human", "oi")], thinking={"type": "disabled"})
    assert "thinking" not in p, p.get("thinking")


# ---------------------------------------------------------------------------
# (iii) nenhum literal do Sonnet 5 no código de produto
# ---------------------------------------------------------------------------
#: o id EXATO — `claude-sonnet-5-5`, `claude-sonnet-5-20260630` etc. não contam.
_LITERAL_PROIBIDO = re.compile(r"claude-sonnet-5(?![-.\w])")
PASTAS = ("backend/app", "backend/portal_worker", "backend/scripts", "lib", "app", "components",
          "docling-service/app")
EXTENSOES = {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".json"}
IGNORAR = ("__pycache__", "node_modules", "/tests/", ".test.", ".spec.")
#: listas de BLOQUEIO/histórico que PODEM citar o id (arquivo → motivo). O snapshot
#: cita o Sonnet 5 para dizer que ele é BLOCKED — é o próprio registro da proibição.
PERMITIDOS = {
    "backend/app/factories/modelos_snapshot.json": "o registro BLOCKED + substituido_por",
}


def ocorrencias(texto: str) -> int:
    return len(_LITERAL_PROIBIDO.findall(texto))


def varrer(raiz: Path = RAIZ_REPO) -> dict:
    achados: dict = {}
    for pasta in PASTAS:
        base = raiz / pasta
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix not in EXTENSOES:
                continue
            rel = p.relative_to(raiz).as_posix()
            if any(x in "/" + rel for x in IGNORAR) or rel in PERMITIDOS:
                continue
            n = ocorrencias(p.read_text(encoding="utf-8", errors="replace"))
            if n:
                achados[rel] = n
    return achados


def test_nenhum_literal_do_sonnet_5_no_codigo_de_produto():
    achados = varrer()
    assert not achados, f"o Sonnet 5 está PROIBIDO (SPEC-121) — literal em: {achados}"


def test_controle_o_varredor_ve_o_id_exato_e_so_ele():
    assert ocorrencias('DISTILLER_LLM_MODEL = os.getenv("X", "claude-sonnet-5")') == 1
    assert ocorrencias("# default `claude-sonnet-5` / anthropic") == 1
    assert ocorrencias('"claude-sonnet-5-5" "claude-sonnet-5-20260630" claude-sonnet-5.5') == 0


# ---------------------------------------------------------------------------
# (iv) o snapshot e a migration concordam
# ---------------------------------------------------------------------------
def _capacidades_da_migration() -> dict:
    sql = MIGRATION.read_text(encoding="utf-8")
    bloco = sql.split("insert into public.llm_pricing", 1)[1]
    m = re.search(r"'(\{.*?\})'::jsonb", bloco, re.S)
    return json.loads(m.group(1))


def test_o_snapshot_e_a_migration_concordam():
    cat = SNAP["catalogo"]
    velho, novo = cat[PROIBIDO], cat[NOVO]
    assert (velho["lifecycle"], velho["substituido_por"]) == ("BLOCKED", NOVO), velho
    assert velho["lifecycle"] in MP.LIFECYCLES_PROIBIDOS
    assert (novo["lifecycle"], novo["provider"], novo["api_surface"], novo["tipo"]) == (
        "APPROVED", "anthropic", "messages", "chat")
    assert (novo["input_price_per_million"], novo["output_price_per_million"],
            novo["cache_read_multiplier"], novo["cache_write_multiplier"]) == (2, 10, 0.1, 1.25)
    assert novo["preco_verificado_em"] == "2026-09-29"
    assert novo["capacidades"] == _capacidades_da_migration(), "snapshot ≠ migration"
    caps = novo["capacidades"]
    assert caps["tool_choice_forcado_ok"] is False and caps["sampling_ok"] is False
    assert caps["raciocinio_desligado"] == "between_tools"
    assert sorted(novo["classes_de_dado"]) == ["interno", "pii", "publico"]
    # ninguém aponta mais para o proibido; nenhuma rota o usa
    assert [m for m, l in cat.items() if l.get("substituido_por") == PROIBIDO] == []
    assert [p for p, r in SNAP["papeis"].items()
            if PROIBIDO in (r.get("modelo_primario"), r.get("modelo_reserva"))] == []
