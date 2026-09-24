# -*- coding: utf-8 -*-
"""SPEC-116-RESERVA — a reserva cross-provider nos caminhos P0 (dispatch + chat/atendimento).

🔴 CHAMA O MOTOR (CLAUDE.md §9.4): o cérebro do acionamento pela função de
produção (`dispatch_watchdog._adaptive_reply`, `dispatch_router.o_cerebro_ja_sabe`)
→ `llm_factory.invocar_com_reserva` → fábrica real → Model Router real → callback
de custo real. Dublês SÓ na borda (os de `test_spec116_f3b_plataforma.py`): o banco
das rotas (com o MAPA do Founder aplicado), o banco do ledger e a rede do provedor
(`_agenerate` dos clientes governados). NENHUMA chamada real (BLOCKED_BY_CREDIT).

O turno de conversa (`nodes.agent_node`) é provado com os dublês da F2
(`test_spec116_f2_turno_e_reserva.py`), aqui só o que a F2 não cobria:
timeout / 5xx / conexão, o breaker do provedor OpenAI e o histórico sanitizado.

Rodar (de backend/):  .venv/Scripts/python -m pytest -q tests/test_spec116_reserva_p0.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import anthropic
import httpx
import openai
import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage  # noqa: E402

import app.core.relogio_do_modelo as R  # noqa: E402
from app.agents import nodes as N  # noqa: E402
from app.factories import model_policy as MP  # noqa: E402
from test_spec116_f2_turno_e_reserva import _reserva_com_ledger, _Reserva, _estado  # noqa: E402
from test_spec116_f3b_plataforma import EMPRESA_A, EMPRESA_B, borda  # noqa: E402,F401

#: O MAPA do Founder (24/09/2026) — o mesmo da migration 20260924_02.
MAPA = {
    "atendimento": ("anthropic", "claude-opus-5-5", None),
    "chat_principal": ("anthropic", "claude-opus-5-5", None),
    "portal_decisao": ("anthropic", "claude-opus-5-5", None),
    "dispatch": ("openai", "gpt-6-sol", "high"),
}


def _req():
    return httpx.Request("POST", "https://api.invalid/v1")


def _falhas_anthropic():
    return {
        "429": anthropic.RateLimitError("rate", response=httpx.Response(429, request=_req()),
                                        body=None),
        "5xx": anthropic.InternalServerError("boom", response=httpx.Response(500, request=_req()),
                                             body=None),
        "timeout": anthropic.APITimeoutError(request=_req()),
        "conexao": anthropic.APIConnectionError(request=_req()),
    }


@pytest.fixture(autouse=True)
def breaker_em_memoria(monkeypatch):
    memoria = R._RedisDeMemoria({})

    async def _cli():
        return memoria

    monkeypatch.setattr(R, "_cliente", _cli)
    return memoria


@pytest.fixture
def com_mapa(borda):
    """A borda da F3b com o MAPA aplicado nas rotas (o que a migration grava)."""
    for papel, (prov, modelo, esforco) in MAPA.items():
        borda.pap[papel].update(provider_reserva=prov, modelo_reserva=modelo,
                                esforco_reserva=esforco)
    MP.limpar_cache()
    return borda


def _falhar_so(borda, modelo, exc):
    """A rede cai SÓ para `modelo`; o outro provedor responde."""
    original = borda.prov._agenerate

    async def _agen(llm, messages, stop=None, run_manager=None, **kw):
        payload = llm._get_request_payload(messages, stop=stop, **kw)
        if payload.get("model") == modelo:
            borda.prov.payloads.append(payload)
            raise exc
        return await original(llm, messages, stop=stop, run_manager=run_manager, **kw)

    borda.prov._agenerate = _agen


def _sentinela():
    from app.tasks import dispatch_watchdog as W

    sessao = {"playbook_ref": "", "company_id": EMPRESA_A, "slots": {}, "history": []}
    return asyncio.run(W._adaptive_reply(EMPRESA_A, sessao, "Digite 1 para guincho, 2 para chaveiro"))


# ---------------------------------------------------------------------------
# A ROTA: o resolver devolve a reserva do mapa — banco e snapshot
# ---------------------------------------------------------------------------
def test_o_resolver_devolve_a_reserva_do_mapa(com_mapa):
    for papel, (prov, modelo, esforco) in MAPA.items():
        r = MP.resolver(papel)
        assert r.reserva is not None, papel
        assert (r.reserva.provider, r.reserva.model, r.reserva.effort) == (prov, modelo, esforco)
        assert r.reserva.provider != r.provider, f"{papel}: reserva tem de ser OUTRO provedor"
    sem = [p for p in com_mapa.pap if p not in MAPA and MP.resolver(p).reserva is not None]
    assert sem == [], f"papel fora do mapa ganhou reserva: {sem}"


def test_banco_fora_o_snapshot_ainda_traz_a_reserva(monkeypatch):
    """⚠️ Depende do snapshot REGENERADO depois de aplicar 20260924_02."""
    def _fora():
        raise ConnectionError("banco fora")

    monkeypatch.setattr(MP, "leitor_do_banco", _fora)
    MP.limpar_cache()
    try:
        for papel, (prov, modelo, esforco) in MAPA.items():
            r = MP.resolver(papel)
            assert r.origem == "snapshot"
            assert r.reserva is not None and (r.reserva.provider, r.reserva.model,
                                              r.reserva.effort) == (prov, modelo, esforco), papel
    finally:
        MP.limpar_cache()


# ---------------------------------------------------------------------------
# DISPATCH — o cérebro do acionamento pelo helper canônico
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("motivo", ["429", "5xx", "timeout", "conexao"])
def test_dispatch_falha_transitoria_do_opus_a_reserva_sol_responde(com_mapa, motivo):
    _falhar_so(com_mapa, "claude-opus-5-5", _falhas_anthropic()[motivo])
    com_mapa.prov.resposta = "2"
    assert _sentinela() == "2"
    assert com_mapa.prov.modelos == ["claude-opus-5-5", "gpt-6-sol"], "UMA reserva, sem repetir"
    corpo_reserva = com_mapa.prov.payloads[1]
    assert json.dumps(corpo_reserva.get("reasoning")) == json.dumps({"effort": "high"}), corpo_reserva
    linhas = com_mapa.banco.linhas()
    assert len(linhas) == 1, "só quem respondeu grava tokens"
    d = linhas[0]["details"]
    assert (d["reserva_usada"], d["motivo_reserva"]) == (True, motivo), d
    assert (d["papel"], d["modelo_resolvido"]) == ("dispatch", "gpt-6-sol")
    assert linhas[0]["company_id"] == EMPRESA_A


def test_dispatch_400_nao_troca_de_modelo(com_mapa):
    erro = anthropic.BadRequestError("bad", response=httpx.Response(400, request=_req()), body=None)
    _falhar_so(com_mapa, "claude-opus-5-5", erro)
    assert _sentinela() is None, "o except do chamador devolve None (corredor segue sem cérebro)"
    assert com_mapa.prov.modelos == ["claude-opus-5-5"], "400 é defeito nosso: a reserva NÃO entra"
    assert com_mapa.banco.linhas() == []


def test_dispatch_breaker_aberto_vai_direto_para_a_reserva(com_mapa):
    # o breaker que o helper vai consultar (a borda da F3b isola um por teste)
    asyncio.run(R._abrir(asyncio.run(R._cliente()), *R._chaves("anthropic")))
    com_mapa.prov.resposta = "1"
    assert _sentinela() == "1"
    assert com_mapa.prov.modelos == ["gpt-6-sol"], "o primário NÃO é chamado com o breaker aberto"
    assert com_mapa.banco.linhas()[0]["details"]["motivo_reserva"] == "breaker_aberto"


def test_dispatch_controle_sem_reserva_o_429_sobe(borda):
    """CONTROLE: a rota de hoje (sem reserva) — o 429 sobe e nada mais é chamado."""
    borda.pap["dispatch"].update(provider_reserva=None, modelo_reserva=None, esforco_reserva=None)
    MP.limpar_cache()
    _falhar_so(borda, "claude-opus-5-5", _falhas_anthropic()["429"])
    assert _sentinela() is None
    assert borda.prov.modelos == ["claude-opus-5-5"]


def test_dispatch_cerebro_antes_do_segurado_usa_a_reserva(com_mapa, monkeypatch):
    from app.services import dispatch_router as DR

    monkeypatch.setenv("CEREBRO_ANTES_DO_SEGURADO", "1")

    async def _fontes(company_id, session):
        return [("ficha", "ponto de referencia: em frente a padaria azul")]

    monkeypatch.setattr(DR, "fontes_do_que_ja_existe", _fontes)
    _falhar_so(com_mapa, "claude-opus-5-5", _falhas_anthropic()["5xx"])
    com_mapa.prov.resposta = "em frente a padaria azul"
    valor, origem = asyncio.run(DR.o_cerebro_ja_sabe(
        EMPRESA_B, {"company_id": EMPRESA_B}, slot="ponto", rotulo="ponto de referencia",
        tela="Informe o ponto"))
    assert (valor, origem) == ("em frente a padaria azul", "ficha")
    assert com_mapa.prov.modelos == ["claude-opus-5-5", "gpt-6-sol"]
    assert com_mapa.banco.linhas()[0]["details"]["motivo_reserva"] == "5xx"


def test_os_tres_callsites_do_dispatch_passam_pelo_helper():
    """Forma: nenhum `create_llm(papel="dispatch")` → `ainvoke` direto sobrou."""
    raiz = BACKEND / "app"
    diretos = [str(p) for p in raiz.rglob("*.py")
               if 'papel="dispatch"' in p.read_text(encoding="utf-8")]
    assert diretos == [], diretos
    usam = sorted(p.name for p in raiz.rglob("*.py")
                  if 'invocar_com_reserva("dispatch"' in p.read_text(encoding="utf-8")
                  or ('invocar_com_reserva(\n' in p.read_text(encoding="utf-8")
                      and '"dispatch"' in p.read_text(encoding="utf-8")))
    assert usam == ["dispatch_router.py", "dispatch_watchdog.py", "webhook.py"], usam


# ---------------------------------------------------------------------------
# CHAT / ATENDIMENTO — o nó do turno (o que a F2 não cobria)
# ---------------------------------------------------------------------------
ROTA_SOL = {"papel": "atendimento", "provedor": "openai", "modelo": "gpt-6-sol",
            "provedor_reserva": "anthropic"}


class _PrimarioSol:
    def __init__(self, erro=None):
        self.erro, self.chamadas = erro, 0

    async def ainvoke(self, *_a, **_k):
        self.chamadas += 1
        raise self.erro


def _falhas_openai():
    return {
        "5xx": openai.InternalServerError("boom", response=httpx.Response(503, request=_req()),
                                          body=None),
        "timeout": openai.APITimeoutError(request=_req()),
        "conexao": openai.APIConnectionError(request=_req()),
    }


@pytest.mark.parametrize("motivo", ["5xx", "timeout", "conexao"])
def test_chat_falha_transitoria_antes_da_ferramenta_a_reserva_responde(motivo):
    reserva, uso = _reserva_com_ledger()
    primario = _PrimarioSol(_falhas_openai()[motivo])
    saida = asyncio.run(N.agent_node(_estado([HumanMessage(content="oi")]), {}, primario,
                                     llm_reserva=reserva, rota=ROTA_SOL))
    assert primario.chamadas == 1 and _Reserva.chamadas == 1
    assert "reserva respondeu" in N.extract_text_from_content(saida["messages"][-1].content)
    d = uso.linhas[0]["details"]
    assert (d["reserva_usada"], d["motivo_reserva"]) == (True, motivo), d


@pytest.mark.parametrize("motivo", ["5xx", "timeout", "conexao"])
def test_chat_falha_transitoria_depois_da_ferramenta_nao_troca_nem_refaz(motivo):
    reserva, uso = _reserva_com_ledger()
    msgs = [HumanMessage(content="aciona"),
            AIMessage(content="", tool_calls=[{"name": "acionar", "args": {}, "id": "t1"}]),
            ToolMessage(content="ACIONADO", tool_call_id="t1", name="acionar")]
    with pytest.raises(type(_falhas_openai()[motivo])):
        asyncio.run(N.agent_node(_estado(msgs), {}, _PrimarioSol(_falhas_openai()[motivo]),
                                 llm_reserva=reserva, rota=ROTA_SOL))
    assert _Reserva.chamadas == 0 and uso.linhas == []


def test_chat_breaker_da_openai_aberto_vai_direto_para_o_opus(breaker_em_memoria):
    asyncio.run(R._abrir(breaker_em_memoria, *R._chaves("openai")))
    reserva, uso = _reserva_com_ledger()
    primario = _PrimarioSol(RuntimeError("não devia ser chamado"))
    asyncio.run(N.agent_node(_estado([HumanMessage(content="oi")]), {}, primario,
                             llm_reserva=reserva, rota=ROTA_SOL))
    assert primario.chamadas == 0 and _Reserva.chamadas == 1
    assert uso.linhas[0]["details"]["motivo_reserva"] == "breaker_aberto"


class _ReservaQueOlha(GenericFakeChatModel):
    vistas: list = []

    def bind_tools(self, tools, **kw):
        return self

    async def ainvoke(self, entrada, *a, **k):
        type(self).vistas = list(entrada)
        return await super().ainvoke(entrada, *a, **k)


def test_chat_historico_sanitizado_ao_cruzar_de_provedor():
    """O raciocínio do Sol (itens `reasoning`) não vai ao Opus — ele o recusaria."""
    anterior = AIMessage(
        content=[{"type": "reasoning", "id": "rs_1", "summary": [],
                  "encrypted_content": "SEGREDO-DO-SOL"},
                 {"type": "text", "text": "Olá, em que posso ajudar?"}],
        response_metadata={"model_provider": "openai", "model_name": "gpt-6-sol"},
        additional_kwargs={"reasoning": {"id": "rs_1", "encrypted_content": "SEGREDO-DO-SOL"}})
    msgs = [HumanMessage(content="oi"), anterior, HumanMessage(content="e a apólice?")]
    reserva = _ReservaQueOlha(messages=iter([AIMessage(content="Aqui está.")]))
    asyncio.run(N.agent_node(_estado(msgs), {}, _PrimarioSol(_falhas_openai()["5xx"]),
                             llm_reserva=reserva, rota=ROTA_SOL))
    vistas = _ReservaQueOlha.vistas
    assert vistas, "a reserva não foi chamada"
    assert "SEGREDO-DO-SOL" not in repr(vistas), "raciocínio do outro provedor vazou para a reserva"
    assert any("em que posso ajudar" in repr(m.content) for m in vistas if isinstance(m, AIMessage))
