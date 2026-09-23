# -*- coding: utf-8 -*-
"""SPEC-116 F2 · G6 + G7 — um turno com ferramenta NUNCA é refeito; a reserva
só entra ANTES da 1ª ferramenta.

G6 (EVIDENCIAS/03 F4): `langchain_service.process_message` refazia o turno
inteiro quando o erro continha "connection" — e o erro de rede do SDK do modelo
é literalmente "Connection error.". Aqui o turno roda o `tool_node` REAL com uma
ferramenta-dublê que CONTA o efeito e depois cai: o efeito tem de contar 1.
LINHA DE CONTROLE: erro de pool SEM ferramenta no turno → o retry antigo ainda
acontece (o conserto do pool continua servindo).

G7 (D-116-07): `nodes.agent_node` com a RESERVA declarada:
  · 429 antes da 1ª ferramenta → a reserva responde; o ledger (o
    `CostCallbackHandler` real) grava `reserva_usada` + `motivo_reserva`;
  · breaker do primário ABERTO → a reserva, sem tocar no primário;
  · 429 DEPOIS da ferramenta → o erro sobe, a reserva é chamada 0 vezes;
  · CONTROLE: sem reserva na rota → o 429 sobe como sempre subiu.

Rodar (de backend/):  .venv/Scripts/python -m pytest -q tests/test_spec116_f2_turno_e_reserva.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, List, Optional

import httpx
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

import openai  # noqa: E402
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage  # noqa: E402
from langchain_core.tools import BaseTool  # noqa: E402

import app.agents as AG  # noqa: E402
import app.agents.graph as G  # noqa: E402
import app.core.relogio_do_modelo as R  # noqa: E402
import app.services.langchain_service as LS  # noqa: E402
from app.agents import nodes as N  # noqa: E402
from app.core.callbacks.cost_callback import CostCallbackHandler  # noqa: E402
from app.factories import model_policy as MP  # noqa: E402
from app.factories.llm_factory import LLMFactory  # noqa: E402

CID = "11111111-1111-1111-1111-111111111111"
EFEITO = {"acionamentos": 0}


class _Acionar(BaseTool):
    """Ferramenta-dublê COM EFEITO: conta cada execução (o "acionamento")."""

    name: str = "acionar"
    description: str = "Aciona a assistência (dublê)."

    def _run(self, pedido: str) -> str:
        EFEITO["acionamentos"] += 1
        return "ACIONADO"


acionar = _Acionar()


def _req():
    return httpx.Request("POST", "https://api.provedor.invalid/v1/x")


def _erro_429():
    return openai.RateLimitError("rate limited", response=httpx.Response(429, request=_req()),
                                 body=None)


def _erro_de_rede_do_modelo():
    return openai.APIConnectionError(request=_req())  # mensagem: "Connection error."


# ===========================================================================
# G6 — process_message não refaz turno que já executou ferramenta
# ===========================================================================
class _Supabase:
    client = _BancoMudo()

    def get_company(self, cid):
        return {"id": cid}

    def get_conversation_history(self, **_k):
        return []


class _GuardaQuePassa:
    fail_close = True

    def __init__(self, *a, **k):
        pass

    async def validate_input(self, texto):
        return False, None, texto


AGENTE = {"id": "ag-1", "company_id": CID, "agent_role": "attendance", "llm_provider": "anthropic",
          "llm_model": "claude-sonnet-5", "security_settings": {}}


@pytest.fixture
def servico(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-teste-anthropic-falsa")
    svc = object.__new__(LS.LangChainService)
    svc.supabase = _Supabase()
    svc.qdrant = None

    async def _agente(*_a, **_k):
        return dict(AGENTE)

    async def _grafo(**_k):
        return object()

    async def _pool():
        return None

    svc._get_raw_agent = _agente
    monkeypatch.setattr(LS, "SmithGuardrail", _GuardaQuePassa)
    monkeypatch.setattr(LS, "get_or_create_graph", _grafo)
    monkeypatch.setattr(G, "close_async_postgres_pool", _pool)
    return svc


def _turno_que_cai(erro, *, com_ferramenta: bool, chamadas: dict):
    async def invoke_agent(**_k):
        chamadas["invoke"] += 1
        if chamadas["invoke"] > 1 and chamadas.get("segunda_responde"):
            return {"response": "ok de novo", "tools_used": []}
        if com_ferramenta:
            estado = {"messages": [HumanMessage(content="aciona"), AIMessage(content="", tool_calls=[
                {"name": "acionar", "args": {"pedido": "1"}, "id": "t1"}])],
                "agent_data": {"agent_role": "attendance"}, "tools_used": []}
            await N.tool_node(estado, tools=[acionar])  # o nó REAL, com o marcador do turno
        raise erro()
    return invoke_agent


def _processar(svc):
    return asyncio.run(svc.process_message("aciona", CID, "u-1", "s-1", collect_metrics=False,
                                           required_role="attendance"))


def test_g6_erro_de_rede_do_modelo_depois_da_ferramenta_nao_refaz(servico, monkeypatch):
    EFEITO["acionamentos"] = 0
    chamadas = {"invoke": 0}
    monkeypatch.setattr(AG, "invoke_agent", _turno_que_cai(_erro_de_rede_do_modelo,
                                                           com_ferramenta=True, chamadas=chamadas))
    with pytest.raises(openai.APIConnectionError):
        _processar(servico)
    assert "connection" in str(_erro_de_rede_do_modelo()).lower(), "o erro real diz 'connection'"
    assert EFEITO["acionamentos"] == 1, EFEITO
    assert chamadas["invoke"] == 1, chamadas


def test_g6_erro_de_conexao_do_banco_depois_da_ferramenta_nao_refaz(servico, monkeypatch):
    """Mesmo um erro que NÃO é do SDK do modelo (mensagem de conexão do banco)
    não refaz um turno que já passou pela ferramenta — o marcador do turno barra."""
    EFEITO["acionamentos"] = 0
    chamadas = {"invoke": 0}
    monkeypatch.setattr(AG, "invoke_agent", _turno_que_cai(
        lambda: RuntimeError("server closed the connection unexpectedly"),
        com_ferramenta=True, chamadas=chamadas))
    with pytest.raises(RuntimeError):
        _processar(servico)
    assert EFEITO["acionamentos"] == 1, EFEITO
    assert chamadas["invoke"] == 1, chamadas


def test_g6_erro_de_rede_do_modelo_sem_ferramenta_nao_refaz_o_turno(servico, monkeypatch):
    """Erro do SDK do MODELO nunca é "pool": o SDK já repetiu a chamada e a
    reserva da rota já foi tentada no nó. Refazer o grafo inteiro (com cache de
    grafos zerado e pool do Postgres fechado) só atrasaria o erro."""
    chamadas = {"invoke": 0, "segunda_responde": True}
    monkeypatch.setattr(AG, "invoke_agent", _turno_que_cai(_erro_de_rede_do_modelo,
                                                           com_ferramenta=False, chamadas=chamadas))
    with pytest.raises(openai.APIConnectionError):
        _processar(servico)
    assert chamadas["invoke"] == 1, chamadas


def test_g6_controle_erro_de_pool_sem_ferramenta_ainda_refaz(servico, monkeypatch):
    chamadas = {"invoke": 0, "segunda_responde": True}
    monkeypatch.setattr(AG, "invoke_agent", _turno_que_cai(
        lambda: RuntimeError("the connection pool is closed"), com_ferramenta=False,
        chamadas=chamadas))
    resposta, _ = _processar(servico)
    assert resposta == "ok de novo" and chamadas["invoke"] == 2, chamadas


# ===========================================================================
# G7 — a reserva da rota, só antes da 1ª ferramenta
# ===========================================================================
class _UsoCapturado:
    def __init__(self):
        self.linhas: List[dict] = []
        self.supabase = None

    def track_cost_sync(self, **kw):
        self.linhas.append(kw)

    def calculate_cost(self, *a, **k):
        return 0.0


class _Reserva(GenericFakeChatModel):
    chamadas: int = 0

    def bind_tools(self, tools: Any, **kw: Any):
        return self

    async def ainvoke(self, *a, **k):
        type(self).chamadas += 1
        return await super().ainvoke(*a, **k)


class _Primario:
    def __init__(self, erro=None):
        self.erro, self.chamadas = erro, 0

    async def ainvoke(self, *_a, **_k):
        self.chamadas += 1
        if self.erro:
            raise self.erro()
        return AIMessage(content="primário respondeu")


ROTA = {"papel": "atendimento", "provedor": "anthropic", "modelo": "claude-sonnet-5",
        "provedor_reserva": "openai"}


def _reserva_com_ledger():
    r = MP.resolver("brand_capture", override={"provider": "openai", "model": "gpt-6-sol"})
    uso = _UsoCapturado()
    h = CostCallbackHandler(service_type="chat", company_id=None,
                            details=LLMFactory.detalhes_do_ledger(r, modelo_pedido=None,
                                                                  reserva_usada=True),
                            model_name="gpt-6-sol", provider="openai")
    h.usage_service = uso
    _Reserva.chamadas = 0
    resp = AIMessage(content="A reserva respondeu.", response_metadata={"model_name": "gpt-6-sol"},
                     usage_metadata={"input_tokens": 30, "output_tokens": 10, "total_tokens": 40})
    return _Reserva(messages=iter([resp]), callbacks=[h]), uso


def _estado(mensagens):
    return {"messages": mensagens, "system_prompt": "teste", "static_prompt": "teste",
            "dynamic_context": "", "agent_data": {"agent_role": "attendance"}, "company_config": {},
            "tools_used": [], "rag_chunks": []}


@pytest.fixture(autouse=True)
def breaker_em_memoria(monkeypatch):
    memoria = R._RedisDeMemoria({})

    async def _cli():
        return memoria

    monkeypatch.setattr(R, "_cliente", _cli)
    return memoria


def test_g7_429_antes_da_ferramenta_usa_a_reserva_e_o_ledger_grava_o_motivo():
    reserva, uso = _reserva_com_ledger()
    primario = _Primario(_erro_429)
    saida = asyncio.run(N.agent_node(_estado([HumanMessage(content="oi")]), {}, primario,
                                     llm_reserva=reserva, rota=ROTA))
    assert primario.chamadas == 1 and _Reserva.chamadas == 1
    assert "reserva respondeu" in N.extract_text_from_content(saida["messages"][-1].content)
    assert len(uso.linhas) == 1, uso.linhas
    d = uso.linhas[0]["details"]
    assert (d["reserva_usada"], d["motivo_reserva"]) == (True, "429"), d
    assert (d["modelo_resolvido"], d["modelo_real"]) == ("gpt-6-sol", "gpt-6-sol"), d


def test_g7_breaker_aberto_vai_direto_para_a_reserva(breaker_em_memoria):
    asyncio.run(R._abrir(breaker_em_memoria, *R._chaves("anthropic")))
    reserva, uso = _reserva_com_ledger()
    primario = _Primario()
    asyncio.run(N.agent_node(_estado([HumanMessage(content="oi")]), {}, primario,
                             llm_reserva=reserva, rota=ROTA))
    assert primario.chamadas == 0 and _Reserva.chamadas == 1
    assert uso.linhas[0]["details"]["motivo_reserva"] == "breaker_aberto"


def test_g7_429_depois_da_ferramenta_retem_e_nao_refaz():
    reserva, uso = _reserva_com_ledger()
    primario = _Primario(_erro_429)
    msgs = [HumanMessage(content="aciona"),
            AIMessage(content="", tool_calls=[{"name": "acionar", "args": {"pedido": "1"}, "id": "t1"}]),
            ToolMessage(content="ACIONADO", tool_call_id="t1", name="acionar")]
    with pytest.raises(openai.RateLimitError):
        asyncio.run(N.agent_node(_estado(msgs), {}, primario, llm_reserva=reserva, rota=ROTA))
    assert _Reserva.chamadas == 0 and uso.linhas == []


def test_g7_erro_definitivo_nao_aciona_a_reserva():
    """400 é defeito nosso (ou da chave): mandar a outro provedor esconderia."""
    reserva, _ = _reserva_com_ledger()

    def _400():
        return openai.BadRequestError("bad", response=httpx.Response(400, request=_req()), body=None)

    with pytest.raises(openai.BadRequestError):
        asyncio.run(N.agent_node(_estado([HumanMessage(content="oi")]), {}, _Primario(_400),
                                 llm_reserva=reserva, rota=ROTA))
    assert _Reserva.chamadas == 0


def test_g7_controle_sem_reserva_o_429_sobe_como_antes():
    with pytest.raises(openai.RateLimitError):
        asyncio.run(N.agent_node(_estado([HumanMessage(content="oi")]), {}, _Primario(_erro_429),
                                 rota=ROTA))
