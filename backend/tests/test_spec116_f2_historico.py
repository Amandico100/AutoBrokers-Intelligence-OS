# -*- coding: utf-8 -*-
"""SPEC-116 F2 · G5 — o histórico DEVOLVE o raciocínio ao modelo que o produziu.

O motor real (CLAUDE.md §9.4): `LLMFactory` → cliente do LangChain em STREAMING
(como em produção) → `nodes.agent_node` monta o histórico → `nodes.tool_node`
executa a ferramenta → volta ao `agent_node`. Dublê SÓ na borda: um servidor
HTTP local que fala o protocolo do provedor e que, como a API de verdade faz
com Opus 5.5 / DeepSeek, devolve **400** se o bloco de raciocínio da rodada
anterior não voltar no pedido seguinte.

  · Anthropic (Opus 5.5): bloco `thinking` com assinatura, SSE de /v1/messages
  · OpenAI-compatível (DeepSeek): `reasoning_content`, SSE de /chat/completions

Cada um: 3 rodadas de ferramenta + a resposta final passam. LINHAS DE CONTROLE:
(a) a rota com OUTRO modelo no mesmo provedor → o bloco NÃO volta e o dublê dá
400 (o sanitize ainda existe, e só para troca de modelo); (b) a mutação
"restaurar o sanitize incondicional" deixa o teste vermelho (relatório da F2).

Rodar (de backend/):  .venv/Scripts/python -m pytest -q tests/test_spec116_f2_historico.py
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.environ["SEM_REDE"] = "1"

CHAVE_FALSA = "sk-teste-chave-falsa-nao-existe"
RODADAS_DE_TOOL = 3


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

from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402
from langchain_core.tools import BaseTool  # noqa: E402

from app.agents import nodes as N  # noqa: E402
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

#: CANDIDATE usados só pela MECÂNICA do adaptador compatível (a bancada os roda via
#: override); no dublê viram APPROVED para a rota de teste montar.
_legados_original = _legados_como_dubles


def _legados_como_dubles(cat):  # noqa: F811
    _legados_original(cat)
    for m in ("gemini-3.8-flash", "deepseek-flash"):
        if m in cat:
            cat[m]["lifecycle"] = "APPROVED"
    return cat

EFEITOS = {"consultas": 0}


class _Consultar(BaseTool):
    """Dublê de ferramenta no formato das do produto (`BaseTool` com `_run`)."""

    name: str = "consultar"
    description: str = "Consulta um cadastro pelo número (dublê sem PII)."

    def _run(self, numero: str) -> str:
        EFEITOS["consultas"] += 1
        return f"cadastro {numero}: ativo"


consultar = _Consultar()


# ===========================================================================
# O dublê do PROVEDOR — a única borda
# ===========================================================================
def _sse(eventos):
    return "".join(f"event: {e.get('type')}\ndata: {json.dumps(e)}\n\n" for e in eventos).encode()


def _anthropic_mensagem(n, modelo, final):
    ev = [{"type": "message_start", "message": {
        "id": f"msg_{n}", "type": "message", "role": "assistant", "model": modelo, "content": [],
        "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 12, "output_tokens": 1}}},
        {"type": "content_block_start", "index": 0,
         "content_block": {"type": "thinking", "thinking": "", "signature": ""}},
        {"type": "content_block_delta", "index": 0,
         "delta": {"type": "thinking_delta", "thinking": f"raciocinio da rodada {n}"}},
        {"type": "content_block_delta", "index": 0,
         "delta": {"type": "signature_delta", "signature": f"sig-{n}"}},
        {"type": "content_block_stop", "index": 0}]
    if final:
        ev += [{"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}},
               {"type": "content_block_delta", "index": 1,
                "delta": {"type": "text_delta", "text": "Tudo conferido."}},
               {"type": "content_block_stop", "index": 1}]
        motivo = "end_turn"
    else:
        ev += [{"type": "content_block_start", "index": 1, "content_block": {
                "type": "tool_use", "id": f"toolu_{n}", "name": "consultar", "input": {}}},
               {"type": "content_block_delta", "index": 1,
                "delta": {"type": "input_json_delta", "partial_json": json.dumps({"numero": str(n)})}},
               {"type": "content_block_stop", "index": 1}]
        motivo = "tool_use"
    ev += [{"type": "message_delta", "delta": {"stop_reason": motivo, "stop_sequence": None},
            "usage": {"output_tokens": 20}},
           {"type": "message_stop"}]
    return _sse(ev)


def _anthropic_falta_raciocinio(corpo):
    """Cada assistente com tool_use tem de trazer o `thinking` ASSINADO de volta."""
    for m in corpo.get("messages") or []:
        if m.get("role") != "assistant" or not isinstance(m.get("content"), list):
            continue
        tipos = [b.get("type") for b in m["content"]]
        if "tool_use" in tipos:
            blocos = [b for b in m["content"] if b.get("type") == "thinking"]
            if not blocos or not str(blocos[0].get("signature") or "").startswith("sig-"):
                return "thinking block with signature must be passed back unchanged"
    return None


def _compat_mensagem(n, modelo, final):
    base = {"id": f"c{n}", "object": "chat.completion.chunk", "created": 0, "model": modelo}
    ch = [dict(base, choices=[{"index": 0, "delta": {"role": "assistant", "content": "",
                                                     "reasoning_content": f"pensei-{n}"},
                               "finish_reason": None}])]
    if final:
        ch.append(dict(base, choices=[{"index": 0, "delta": {"content": "Tudo conferido."},
                                       "finish_reason": None}]))
        motivo = "stop"
    else:
        ch.append(dict(base, choices=[{"index": 0, "delta": {"tool_calls": [{
            "index": 0, "id": f"call_{n}", "type": "function",
            "function": {"name": "consultar", "arguments": json.dumps({"numero": str(n)})}}]},
            "finish_reason": None}]))
        motivo = "tool_calls"
    ch.append(dict(base, choices=[{"index": 0, "delta": {}, "finish_reason": motivo}]))
    ch.append(dict(base, choices=[], usage={"prompt_tokens": 9, "completion_tokens": 7,
                                            "total_tokens": 16}))
    return ("".join(f"data: {json.dumps(c)}\n\n" for c in ch) + "data: [DONE]\n\n").encode()


def _compat_falta_raciocinio(corpo):
    for m in corpo.get("messages") or []:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            if not str(m.get("reasoning_content") or "").startswith("pensei-"):
                return "reasoning_content must be passed back to the API"
    return None


class Provedor:
    """Servidor local com o comportamento de 400 da API real."""

    def __init__(self, tipo, modelo):
        self.tipo, self.modelo, self.pedidos, self.recusas = tipo, modelo, [], []
        dono = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silêncio
                pass

            def do_POST(self):  # noqa: N802
                corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
                dono.pedidos.append(corpo)
                n = len(dono.pedidos)
                falta = (_anthropic_falta_raciocinio if dono.tipo == "anthropic"
                         else _compat_falta_raciocinio)(corpo)
                if falta:
                    dono.recusas.append(falta)
                    erro = json.dumps({"type": "error", "error": {
                        "type": "invalid_request_error", "message": falta}}).encode()
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(erro)))
                    self.end_headers()
                    self.wfile.write(erro)
                    return
                final = n > RODADAS_DE_TOOL
                corpo_sse = (_anthropic_mensagem if dono.tipo == "anthropic"
                             else _compat_mensagem)(n, dono.modelo, final)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(corpo_sse)))
                self.end_headers()
                self.wfile.write(corpo_sse)

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def fechar(self):
        self.srv.shutdown()


# ===========================================================================
# O banco das rotas (dublê) e o laço agente ⇄ ferramenta com os nós REAIS
# ===========================================================================
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


def _estado(mensagens):
    return {"messages": mensagens, "system_prompt": "Você é um assistente de teste.",
            "static_prompt": "Você é um assistente de teste.", "dynamic_context": "",
            "agent_data": {"agent_role": "core"}, "company_config": {}, "tools_used": [],
            "rag_chunks": []}


async def _conversa(llm, rota_do_turno):
    ligado = llm.bind_tools([consultar])
    msgs = [HumanMessage(content="confira o cadastro três vezes")]
    tools_used = []
    for _ in range(RODADAS_DE_TOOL + 1):
        est = _estado(list(msgs))
        est["tools_used"] = list(tools_used)
        saida = await N.agent_node(est, {}, ligado, llm_base=llm, tools_base=[consultar],
                                   rota=rota_do_turno)
        resposta = saida["messages"][-1]
        msgs.append(resposta)
        if not getattr(resposta, "tool_calls", None):
            return msgs
        est = _estado(list(msgs))
        est["tools_used"] = list(tools_used)
        feito = await N.tool_node(est, tools=[consultar])
        msgs.extend(feito["messages"])
        tools_used = list(feito.get("tools_used") or [])
    return msgs


def _rodar(coro):
    return asyncio.run(coro)


# ===========================================================================
# Anthropic — Opus 5.5
# ===========================================================================
def test_opus_55_tres_rodadas_com_o_thinking_de_volta(banco, monkeypatch):
    _, pap = banco
    prov = Provedor("anthropic", "claude-opus-5-5")
    try:
        monkeypatch.setenv("ANTHROPIC_API_URL", prov.url)
        pap["chat_principal"].update(provider="anthropic", modelo_primario="claude-opus-5-5", esforco="medium")
        MP.limpar_cache()
        r = MP.resolver("chat_principal")
        llm = LLMFactory.create_llm({}, {"agent_role": "core"}, api_key=CHAVE_FALSA, modelo_resolvido=r)
        assert llm.streaming is True, "o teste roda o caminho de produção (streaming)"
        EFEITOS["consultas"] = 0
        msgs = _rodar(_conversa(llm, {"provedor": r.provider, "modelo": r.model}))
        assert prov.recusas == [], prov.recusas
        assert len(prov.pedidos) == RODADAS_DE_TOOL + 1
        assert EFEITOS["consultas"] == RODADAS_DE_TOOL
        assert isinstance(msgs[-1], AIMessage) and "conferido" in N.extract_text_from_content(msgs[-1].content)
        # o que VOLTOU no último pedido: os 3 blocos assinados, na ordem
        assinaturas = [b.get("signature") for m in prov.pedidos[-1]["messages"]
                       if m["role"] == "assistant" for b in m["content"] if b.get("type") == "thinking"]
        assert assinaturas == ["sig-1", "sig-2", "sig-3"], assinaturas
        assert (prov.pedidos[0].get("output_config") or {}).get("effort") == "medium"
    finally:
        prov.fechar()


def test_controle_modelo_trocado_nao_devolve_o_thinking(banco, monkeypatch):
    """LINHA DE CONTROLE: a rota diz OUTRO modelo (a reserva, ou a troca de rota
    no meio da conversa) → o raciocínio NÃO volta (ele é preso ao modelo que o
    gerou) → o dublê recusa como a API recusaria. Prova que o guarda enxerga a
    diferença entre preservar e sanitizar."""
    _, pap = banco
    prov = Provedor("anthropic", "claude-opus-5-5")
    try:
        monkeypatch.setenv("ANTHROPIC_API_URL", prov.url)
        pap["chat_principal"].update(provider="anthropic", modelo_primario="claude-opus-5-5", esforco="medium")
        MP.limpar_cache()
        r = MP.resolver("chat_principal")
        llm = LLMFactory.create_llm({}, {"agent_role": "core"}, api_key=CHAVE_FALSA, modelo_resolvido=r)
        with pytest.raises(Exception) as info:
            _rodar(_conversa(llm, {"provedor": "anthropic", "modelo": "claude-sonnet-5"}))
        assert "400" in str(info.value) or type(info.value).__name__ == "BadRequestError", info.value
        assert prov.recusas, "o dublê precisava ter recusado"
    finally:
        prov.fechar()


# ===========================================================================
# OpenAI-compatível — DeepSeek (reasoning_content)
# ===========================================================================
def test_compativel_tres_rodadas_com_reasoning_content_de_volta(banco, monkeypatch):
    cat, pap = banco
    prov = Provedor("compat", "deepseek-flash")
    try:
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-teste-deepseek-falsa")
        cat["deepseek-flash"]["base_url"] = prov.url
        pap["brand_capture"].update(provider="deepseek", modelo_primario="deepseek-flash", esforco="high")
        MP.limpar_cache()
        r = MP.resolver("brand_capture")
        llm = LLMFactory.create_llm({}, {}, modelo_resolvido=r)
        EFEITOS["consultas"] = 0
        msgs = _rodar(_conversa(llm, {"provedor": r.provider, "modelo": r.model}))
        assert prov.recusas == [], prov.recusas
        assert len(prov.pedidos) == RODADAS_DE_TOOL + 1
        assert EFEITOS["consultas"] == RODADAS_DE_TOOL
        voltaram = [m.get("reasoning_content") for m in prov.pedidos[-1]["messages"]
                    if m.get("role") == "assistant"]
        assert voltaram == ["pensei-1", "pensei-2", "pensei-3"], voltaram
        assert prov.pedidos[0].get("reasoning_effort") == "high"
        assert "conferido" in N.extract_text_from_content(msgs[-1].content)
    finally:
        prov.fechar()
