# -*- coding: utf-8 -*-
"""SPEC-116 F3a (U8) — quem ESCREVE para o segurado e quem decide se ele é atendido.

🔴 CHAMA O MOTOR (CLAUDE.md §9.4):
  G-AUX    `auxiliaries._summarize` / `_draft_followup` saem no PROVEDOR DA ROTA
           `auxiliar` (quebrados desde 07/08: Claude dentro de `ChatOpenAI`)
  G-PUT    `PUT /api/agents/{id}` (a rota REAL do FastAPI) recusa modelo
           retirado/fora do catálogo com 400 humano; legado gravado fica; sem
           modelo passa (mutação: tirar a conferência ⇒ VERMELHO)
  G-REGEN  `nodes.agent_node` REAL, fiscal da pergunta repetida: a regeneração
           monta um payload VÁLIDO no adaptador Anthropic REAL (sem rede)
           (mutação: SystemMessage de volta no fim ⇒ VERMELHO)
  G-BUF    `processar_buffers_prontos` REAL: primário com disjuntor aberto +
           reserva de pé ⇒ ATENDE; os dois abertos ⇒ RETÉM
  G-SUB    `SubAgentTool._run_react_loop`: papel `subagente`, raciocínio
           preservado entre rodadas, log com o modelo REAL

⛔ Sem rede, sem banco, sem modelo real, sem envio, sem PII.
Rodar (de backend/):  .venv/Scripts/python -m pytest -q tests/test_spec116_f3a_quem_escreve_pede_papel.py
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List

import pytest

BACKEND = Path(__file__).resolve().parent.parent
for _c in (str(BACKEND), str(BACKEND / "tests")):
    if _c not in sys.path:
        sys.path.insert(0, _c)
os.environ["SEM_REDE"] = "1"


class _Q:
    data: list = []

    def __getattr__(self, _n):
        return lambda *a, **k: self

    def execute(self):
        return self


class _BancoMudo:
    client = None

    def table(self, _n):
        return _Q()


_BancoMudo.client = _BancoMudo()

import app.core.database as _db  # noqa: E402
import app.services.usage_service as _uso  # noqa: E402

_db.get_supabase_client = lambda: _BancoMudo()
_uso.get_supabase_client = _db.get_supabase_client

from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.messages import (  # noqa: E402
    AIMessage, HumanMessage, SystemMessage, ToolMessage,
)

from app.factories import model_policy as MP  # noqa: E402
from app.factories.llm_factory import (  # noqa: E402
    ChatAnthropicGovernado, ChatOpenAIGovernado, LLMFactory,
)

SNAP = json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))
TENANT_A = "aaaaaaaa-0000-4000-8000-00000000000a"
CHAVE_ANTHROPIC = "sk-ant-teste-falsa"
CHAVE_OPENAI = "sk-teste-openai-falsa"


@pytest.fixture
def banco(monkeypatch):
    cat = copy.deepcopy(SNAP["catalogo"])
    pap = copy.deepcopy(SNAP["papeis"])
    original = MP.leitor_do_banco
    MP.leitor_do_banco = lambda: (cat, pap)
    MP.limpar_cache()
    monkeypatch.setenv("OPENAI_API_KEY", CHAVE_OPENAI)
    monkeypatch.setenv("ANTHROPIC_API_KEY", CHAVE_ANTHROPIC)
    yield cat, pap
    MP.leitor_do_banco = original
    MP.limpar_cache()


def _trocar_rota(pap, papel, provider, modelo):
    pap[papel].update(provider=provider, modelo_primario=modelo)
    MP.limpar_cache()


@pytest.fixture
def provedor(monkeypatch):
    """A BORDA: o `ainvoke` da classe-base de todo modelo de chat."""
    chamadas: List[dict] = []
    resposta = {"texto": '```json\n{"summary": "Segurado pediu guincho.", "topics": ["guincho"], '
                         '"confidence": "high"}\n```'}

    async def _ainvoke(self, entrada, config=None, **kw):
        chamadas.append({"classe": type(self).__name__, "llm": self, "mensagens": entrada,
                         "model": getattr(self, "model_name", None) or getattr(self, "model", None)})
        return AIMessage(content=resposta["texto"],
                         usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})

    monkeypatch.setattr(BaseChatModel, "ainvoke", _ainvoke)
    return SimpleNamespace(chamadas=chamadas, resposta=resposta)


# ===========================================================================
# G-AUX — os auxiliares saem no provedor da ROTA, com a chave dele
# ===========================================================================
def test_auxiliar_resumo_sai_no_provedor_da_rota(banco, provedor):
    import app.api.auxiliaries as AUX

    _, pap = banco
    assert pap["auxiliar"]["provider"] == "anthropic", "a rota de hoje é Claude (o seed)"
    saida, uso, modelo = asyncio.run(AUX._summarize(
        [{"role": "user", "content": "meu carro quebrou"}], company_id=TENANT_A,
        detalhes={"auxiliary": AUX.RESUMO_SLUG, "run_id": "run-1"}))
    ch = provedor.chamadas[0]
    # 🔴 o defeito de 07/08: um Claude dentro de `ChatOpenAI`, com a chave da OpenAI
    assert ch["classe"] == "ChatAnthropicGovernado" and ch["model"] == pap["auxiliar"]["modelo_primario"]
    assert ch["llm"].anthropic_api_key.get_secret_value() == CHAVE_ANTHROPIC
    assert ch["llm"].max_tokens == 1200, "o piso da CONVERSA não vale para o auxiliar"
    assert modelo == pap["auxiliar"]["modelo_primario"]
    assert saida["summary"] == "Segurado pediu guincho.", "JSON cercado por ``` é lido"
    assert uso == {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}
    custo = ch["llm"].callbacks[0]
    assert (custo.service_type, custo.company_id) == ("auxiliary_run", TENANT_A)
    assert custo.details["papel"] == "auxiliar" and custo.details["auxiliary"] == AUX.RESUMO_SLUG


def test_auxiliar_followup_troca_de_provedor_com_a_rota(banco, provedor):
    """A rota muda para a OpenAI → o cliente e a chave mudam juntos (sem deploy)."""
    import app.api.auxiliaries as AUX

    _, pap = banco
    _trocar_rota(pap, "auxiliar", "openai", "gpt-4o-mini")
    provedor.resposta["texto"] = "Oi! Seguimos acompanhando o seu caso."
    msg, _uso2, modelo = asyncio.run(AUX._draft_followup(
        [{"role": "user", "content": "e aí?"}], "retomar", company_id=TENANT_A))
    ch = provedor.chamadas[0]
    assert (ch["classe"], ch["model"], modelo) == ("ChatOpenAIGovernado", "gpt-4o-mini", "gpt-4o-mini")
    assert ch["llm"].openai_api_key.get_secret_value() == CHAVE_OPENAI
    assert msg == "Oi! Seguimos acompanhando o seu caso."
    # CONTROLE: de volta ao Claude, o MESMO motor monta o cliente da Anthropic
    _trocar_rota(pap, "auxiliar", "anthropic", "claude-sonnet-5")
    asyncio.run(AUX._draft_followup([], "retomar", company_id=TENANT_A))
    ch = provedor.chamadas[-1]
    assert ch["classe"] == "ChatAnthropicGovernado"
    assert "temperature" not in ch["llm"]._get_request_payload(ch["mensagens"])


# ===========================================================================
# G-PUT — o PUT do agente confere o modelo no catálogo (rota REAL do FastAPI)
# ===========================================================================
class _ServicoDeAgentes:
    def __init__(self, gravado: dict):
        self.gravado = gravado
        self.atualizados: List[Any] = []

    def get_agent_by_id(self, agent_id):
        return SimpleNamespace(**self.gravado)

    def update_agent(self, agent_id, dados, company_id=None):
        self.atualizados.append(dados)
        agora = datetime(2026, 9, 23)
        return {"id": str(agent_id), "company_id": self.gravado["company_id"], "name": "Atendente",
                "slug": "atendente", "created_at": agora, "updated_at": agora}


def _put(servico, corpo):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import app.api.agents as AGT
    from app.core.auth import require_master_admin

    app = FastAPI()
    app.include_router(AGT.router, prefix="/api/agents")
    app.dependency_overrides[AGT.get_agent_service] = lambda: servico
    app.dependency_overrides[require_master_admin] = lambda: True
    return TestClient(app).put(f"/api/agents/{uuid.uuid4()}", json=corpo)


def test_put_do_agente_recusa_modelo_retirado_e_aceita_o_resto(banco):
    servico = _ServicoDeAgentes({"company_id": TENANT_A, "llm_provider": "openai",
                                 "llm_model": "gpt-4o-mini", "vision_model": None})
    # retirado (BLOCKED) → 400 com frase para gente, e NADA é gravado
    r = _put(servico, {"llm_provider": "anthropic", "llm_model": "claude-3-5-sonnet-20241022"})
    assert r.status_code == 400, r.text
    assert "claude-3-5-sonnet-20241022" in r.json()["detail"] and "não pode ser usado" in r.json()["detail"]
    # fora do catálogo → 400
    r = _put(servico, {"llm_model": "gpt-4.5-preview"})
    assert r.status_code == 400 and "catálogo" in r.json()["detail"], r.text
    # visão retirada → 400
    r = _put(servico, {"vision_model": "claude-3-5-sonnet-20240620"})
    assert r.status_code == 400, r.text
    assert servico.atualizados == [], "nenhuma escrita com modelo recusado"
    # CONTROLE — o legado que JÁ está gravado fica (a tela manda o formulário inteiro)
    r = _put(servico, {"llm_provider": "openai", "llm_model": "gpt-4o-mini", "name": "Atendente"})
    assert r.status_code == 200, r.text
    # CONTROLE — sem modelo é permitido (a ROTA decide) · e um aprovado passa
    assert _put(servico, {"name": "Atendente"}).status_code == 200
    assert _put(servico, {"llm_provider": "anthropic", "llm_model": "claude-sonnet-5"}).status_code == 200
    assert len(servico.atualizados) == 3
    # e o legado NÃO pode ser escolhido de novo por quem não o tinha
    outro = _ServicoDeAgentes({"company_id": TENANT_A, "llm_provider": "anthropic",
                               "llm_model": "claude-sonnet-5", "vision_model": None})
    r = _put(outro, {"llm_provider": "openai", "llm_model": "gpt-4o-mini"})
    assert r.status_code == 400 and "legado" in r.json()["detail"], r.text


# ===========================================================================
# G-REGEN — a regeneração dos fiscais é um payload VÁLIDO para o Claude
# ===========================================================================
class _ModeloQueValidaNoAnthropic:
    """Dublê do modelo do turno: cada chamada é MONTADA pelo adaptador Anthropic
    REAL da fábrica (sem rede). Payload inválido fica anotado como erro."""

    def __init__(self, adaptador, textos):
        self.adaptador, self.textos = adaptador, list(textos)
        self.chamadas: List[list] = []
        self.erros: List[str] = []

    async def ainvoke(self, mensagens, config=None):
        self.chamadas.append(list(mensagens))
        try:
            self.adaptador._get_request_payload(list(mensagens))
        except Exception as e:  # noqa: BLE001
            self.erros.append(f"{type(e).__name__}: {e}")
            raise
        i = min(len(self.chamadas) - 1, len(self.textos) - 1)
        return AIMessage(content=self.textos[i])


def test_regeneracao_do_fiscal_monta_payload_valido_no_claude(banco):
    import app.services.activity_log as AL
    import test_slot_confirmado_nao_se_pergunta as S
    from app.agents import nodes as N

    adaptador = LLMFactory.create_llm({}, {"agent_role": "attendance"}, papel="atendimento")
    assert isinstance(adaptador, ChatAnthropicGovernado)
    repetida = "Só para eu confirmar: a água ainda está escorrendo?"
    boa = "Perfeito, com o registro fechado já estou acionando a assistência."
    modelo = _ModeloQueValidaNoAnthropic(adaptador, [repetida, boa])
    estado = {
        "messages": [HumanMessage(content="e ai, vem hoje?")],
        "company_id": S.EMPRESA, "session_id": S.SESSAO, "user_id": "u",
        "company_config": {}, "agent_data": {"agent_role": "attendance", "llm_provider": "anthropic"},
        "system_prompt": "prompt sintetico", "static_prompt": "prompt sintetico",
        "dynamic_context": "contexto dinamico", "ficha_atendimento": S._ficha_do_encanador(),
    }

    async def _log(*a, **k):
        return None

    original = AL.log_activity
    AL.log_activity = _log
    try:
        saida = asyncio.run(N.agent_node(estado, None, modelo))
    finally:
        AL.log_activity = original
    assert len(modelo.chamadas) == 2, "o fiscal não regenerou"
    assert modelo.erros == [], modelo.erros
    assert saida["messages"][-1].content == boa, "a regeneração RODOU e a resposta boa saiu"
    ultima = modelo.chamadas[-1][-1]
    assert isinstance(ultima, HumanMessage) and N.ROTULO_DA_CORRECAO_INTERNA in ultima.content
    assert "escorrendo" in ultima.content.lower()
    assert sum(isinstance(m, SystemMessage) for m in modelo.chamadas[-1]) == 1


def test_controle_system_no_fim_e_recusado_pelo_adaptador_anthropic(banco):
    """LINHA DE CONTROLE: o defeito medido pela F2 — o adaptador REAL recusa um
    SystemMessage no fim; o helper monta o mesmo pedido como válido, também
    depois de um `tool_result` (a Anthropic funde os turnos do usuário)."""
    from app.agents.nodes import mensagens_com_correcao

    adaptador = LLMFactory.create_llm({}, {"agent_role": "attendance"}, papel="atendimento")
    base = [SystemMessage(content=[{"type": "text", "text": "estatico", "cache_control": {"type": "ephemeral"}},
                                   {"type": "text", "text": "dinamico"}]),
            HumanMessage(content="oi"),
            AIMessage(content="", tool_calls=[{"name": "consultar", "args": {}, "id": "t1"}]),
            ToolMessage(content="ok", tool_call_id="t1")]
    with pytest.raises(ValueError, match="non-consecutive system"):
        adaptador._get_request_payload(base + [SystemMessage(content="reescreva")])
    payload = adaptador._get_request_payload(mensagens_com_correcao(base, "reescreva"))
    assert payload["messages"][-1]["role"] == "user"
    blocos = payload["messages"][-1]["content"]
    assert blocos[0]["type"] == "tool_result" and "reescreva" in json.dumps(blocos, ensure_ascii=False)
    assert payload["system"][0].get("cache_control") == {"type": "ephemeral"}, "o cache fica"


# ===========================================================================
# G-BUF — o disjuntor do primário aberto NÃO retém quando a reserva está de pé
# ===========================================================================
def test_buffer_segue_pela_reserva_e_retem_sem_ela():
    import test_a_costura_do_isolamento as C

    V = C.V

    async def _cenario(abertos, resolvedor):
        duble, RM, servico, bp = C._preparar()
        await V._semear(servico, V.ESCOPO_A, 3, inicio=0)
        V._andar(30)
        for p in abertos:
            await C._abrir_o_disjuntor(RM, p)
        borda = C.Borda()
        resumo = await C._varrer(bp, servico, duble, borda,
                                 barrados=bp["provedores_barrados"],
                                 provedor_de=C._resolvedor(resolvedor))
        return resumo, borda

    # primário (anthropic) aberto + reserva (openai) fechada ⇒ ATENDE as 3
    resumo, borda = asyncio.run(_cenario([C.PROVEDOR_A], {V.ESCOPO_A: (C.PROVEDOR_A, C.PROVEDOR_B)}))
    assert borda.atendidas.count(V.ESCOPO_A) == 3 and resumo["adiadas"]["breaker"] == 0, resumo
    # os DOIS abertos ⇒ RETÉM as 3 (nada chega ao segurado)
    resumo, borda = asyncio.run(_cenario([C.PROVEDOR_A, C.PROVEDOR_B],
                                         {V.ESCOPO_A: (C.PROVEDOR_A, C.PROVEDOR_B)}))
    assert V.ESCOPO_A not in borda.atendidas and resumo["adiadas"]["breaker"] == 3, resumo
    # CONTROLE: sem reserva declarada ⇒ retém como sempre (a regra antiga vale)
    resumo, borda = asyncio.run(_cenario([C.PROVEDOR_A], {V.ESCOPO_A: (C.PROVEDOR_A, None)}))
    assert resumo["adiadas"]["breaker"] == 3, resumo
    # e o resolvedor antigo (só o provedor, str) continua valendo
    resumo, borda = asyncio.run(_cenario([C.PROVEDOR_A], {V.ESCOPO_A: C.PROVEDOR_A}))
    assert resumo["adiadas"]["breaker"] == 3, resumo


def test_o_escopo_devolve_a_reserva_da_rota(banco, monkeypatch):
    """O elo: `provedor_do_escopo` (REAL) devolve (primário, reserva) da ROTA."""
    import app.services.integration_service as IS
    import app.tasks.buffer_processor as BP

    _, pap = banco
    pap["atendimento"].update(provider_reserva="openai", modelo_reserva="gpt-4o")
    MP.limpar_cache()

    class _Integracoes:
        def get_integration_by_id(self, escopo):
            return {"company_id": TENANT_A, "agent_id": "ag-a"}

    class _Servico:
        async def _get_raw_agent(self, cid, agent_id, required_role=None):
            return {"id": agent_id, "company_id": cid, "agent_role": "attendance",
                    "llm_provider": "anthropic", "llm_model": "claude-sonnet-5"}

    monkeypatch.setattr(IS, "get_integration_service", lambda _c: _Integracoes())
    guardado = BP._LANGCHAIN_PARA_RESOLVER[0]
    BP._LANGCHAIN_PARA_RESOLVER[0] = _Servico()
    try:
        assert asyncio.run(BP.provedor_do_escopo("int-1")) == ("anthropic", "openai")
        # CONTROLE: sem reserva na rota ⇒ (primário, None)
        pap["atendimento"].update(provider_reserva=None, modelo_reserva=None)
        MP.limpar_cache()
        assert asyncio.run(BP.provedor_do_escopo("int-1")) == ("anthropic", None)
    finally:
        BP._LANGCHAIN_PARA_RESOLVER[0] = guardado


# ===========================================================================
# G-SUB — o subagente pede o papel, preserva o raciocínio e loga o modelo real
# ===========================================================================
def test_subagente_papel_raciocinio_e_rotulo_real(banco, monkeypatch):
    from langchain_core.tools import BaseTool

    from app.agents.tools import subagent_tool as ST

    class _Consulta(BaseTool):
        name: str = "consultar"
        description: str = "dublê"

        def _run(self, **_k):
            return "resultado"

    pensado = AIMessage(
        content=[{"type": "thinking", "thinking": "vou consultar", "signature": "sig-1"},
                 {"type": "tool_use", "id": "t1", "name": "consultar", "input": {}}],
        tool_calls=[{"name": "consultar", "args": {}, "id": "t1"}],
        response_metadata={"model_name": "claude-sonnet-5", "model_provider": "anthropic"})
    final = AIMessage(content="pronto", response_metadata={"model_name": "claude-sonnet-5"})
    vistos: List[list] = []
    criados: List[Any] = []

    class _Modelo:
        def bind_tools(self, _t):
            return self

        async def ainvoke(self, mensagens):
            vistos.append(list(mensagens))
            return pensado if len(vistos) == 1 else final

    def _criar(*a, **k):
        criados.append(k.get("modelo_resolvido"))
        return _Modelo()

    logs: List[dict] = []

    class _Sb:
        def table(self, _n):
            return self

        def insert(self, linha):
            logs.append(linha)
            return self

        def execute(self):
            return self

    monkeypatch.setattr(LLMFactory, "create_llm", staticmethod(_criar))
    monkeypatch.setattr(ST.SubAgentTool, "_build_subagent_tools", lambda self, d, i: [_Consulta()])
    tool = ST.SubAgentTool(available_subagents={}, company_id=TENANT_A, company_config={},
                           supabase_client=_Sb())
    saida = json.loads(asyncio.run(tool._run_react_loop(
        "tarefa", "sub-1", "", {"subagent_data": {"agent_name": "Especialista",
                                                  "llm_provider": "openai", "llm_model": "gpt-4o"}})))
    assert saida["response"] == "pronto"
    assert criados[0].papel == "subagente" and criados[0].model == "claude-sonnet-5", "a ROTA decide"
    # o raciocínio VOLTOU intacto na 2ª rodada (mesmo provedor e modelo)
    devolvido = [m for m in vistos[1] if isinstance(m, AIMessage)][0]
    assert devolvido.content[0] == {"type": "thinking", "thinking": "vou consultar", "signature": "sig-1"}
    # o log grava o modelo REAL, nunca um rótulo inventado
    assert logs and logs[0]["llm_model"] == "claude-sonnet-5" and logs[0]["llm_provider"] == "anthropic"
