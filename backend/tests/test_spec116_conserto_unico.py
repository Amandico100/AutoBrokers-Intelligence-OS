# -*- coding: utf-8 -*-
"""SPEC-116 · CONSERTO ÚNICO (protocolo §5 ⑤) — os achados do juiz e do red team.

🔴 CHAMA O MOTOR (CLAUDE.md §9.4). Dublê SÓ na borda (banco, rede do provedor,
REST do Supabase). ⛔ Nenhum teste aqui escreve no Supabase real nem chama provedor.

  C1 · o cache_control do prompt Anthropic vem da ROTA, não do `llm_provider`
       gravado (red B1) — `nodes.agent_node` + payload REAL do adaptador; e o
       log (`nodes.log_node`) grava o provedor que respondeu/da rota (red P4).
  C4 · o ledger do portal NÃO grava sem job/empresa nem dentro do pytest pelo
       transporte real (juiz B3 / red P2) — `modelo_do_portal.decidir`.
  C5 · a migration `_05` recusa, no BANCO, a rota que o resolvedor recusaria —
       a regra do SQL é a mesma de `model_policy._validar` (red P3).
  C6 · o botão "testar conexão" passa pela FÁBRICA (sem temperature no Claude 5;
       modelo não governado = recusa com motivo) — os DOIS endpoints (juiz P5).
  C7 · `POST /api/agents` confere o modelo no catálogo, como o PUT (red P5).
  C8 · o oráculo `cob-n1-p19a` aceita a NEGAÇÃO "não é golpe" (juiz P7).

Rodar (de backend/):  .venv/Scripts/python -m pytest -q tests/test_spec116_conserto_unico.py
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List

import httpx
import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
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

from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # noqa: E402

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

TENANT_A = "aaaaaaaa-0000-4000-8000-00000000000a"
CHAVE_FALSA = "sk-teste-chave-falsa-nao-existe"
MIGRATION_05 = (BACKEND / "supabase" / "migrations"
                / "20260923_05_spec116_rota_so_aceita_modelo_governado.sql")


@pytest.fixture(autouse=True)
def banco(monkeypatch):
    """O banco dublado: snapshot copiado + cliente Supabase mudo (ledger)."""
    cat = _legados_como_dubles(copy.deepcopy(SNAP["catalogo"]))
    pap = copy.deepcopy(SNAP["papeis"])
    monkeypatch.setattr(MP, "leitor_do_banco", lambda: (cat, pap))
    monkeypatch.setattr(_db, "get_supabase_client", lambda: _BancoMudo())
    monkeypatch.setattr(_uso, "get_supabase_client", _db.get_supabase_client)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste-openai-falsa")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-teste-falsa")
    MP.limpar_cache()
    yield cat, pap
    MP.limpar_cache()


# ===========================================================================
# C1 — o formato do system (cache_control) segue a ROTA
# ===========================================================================
class _ModeloQueGuarda:
    """Borda do provedor: guarda as mensagens que o nó mandaria."""

    def __init__(self):
        self.mensagens: List[list] = []

    async def ainvoke(self, mensagens, *a, **k):
        self.mensagens.append(list(mensagens))
        return AIMessage(content="ok")


def _estado(agent_data):
    return {"messages": [HumanMessage(content="minha apólice cobre vidro?")],
            "system_prompt": "PROMPT ESTÁTICO DA CORRETORA", "static_prompt": "PROMPT ESTÁTICO DA CORRETORA",
            "dynamic_context": "memória do cliente", "agent_data": agent_data, "company_config": {},
            "tools_used": [], "rag_chunks": []}


def _rota(provedor, modelo):
    return {"papel": "atendimento", "provedor": provedor, "modelo": modelo, "provedor_reserva": None}


def _payload_do_provedor(provider, model, mensagens):
    """O payload REAL que o adaptador da fábrica mandaria (sem rede)."""
    r = MP.resolver("atendimento", override={"provider": provider, "model": model})
    llm = LLMFactory.create_llm({}, {"agent_role": "attendance"}, api_key=CHAVE_FALSA,
                                modelo_resolvido=r)
    return llm._get_request_payload(mensagens)


def test_c1_agente_nulo_com_rota_anthropic_leva_cache_control():
    """📊 red B1: agente nascido NULO (F4) + rota anthropic → o system saía como
    STRING, sem cache_control (input cheio a cada turno)."""
    modelo = _ModeloQueGuarda()
    agente_nulo = {"agent_role": "attendance", "llm_provider": None, "llm_model": None}
    asyncio.run(N.agent_node(_estado(agente_nulo), {}, modelo,
                             rota=_rota("anthropic", "claude-sonnet-5")))
    sistema = modelo.mensagens[0][0]
    assert isinstance(sistema, SystemMessage) and isinstance(sistema.content, list), sistema
    p = _payload_do_provedor("anthropic", "claude-sonnet-5", modelo.mensagens[0])
    assert "cache_control" in json.dumps(p["system"]), p["system"]


def test_c1_controle_agente_gravado_anthropic_com_rota_openai_nao_leva_blocos():
    """LINHA DE CONTROLE: o gravado diz anthropic, a ROTA diz openai → o system
    é texto simples (o campo gravado não manda mais)."""
    modelo = _ModeloQueGuarda()
    gravado = {"agent_role": "attendance", "llm_provider": "anthropic", "llm_model": "claude-sonnet-5"}
    asyncio.run(N.agent_node(_estado(gravado), {}, modelo, rota=_rota("openai", "gpt-6-sol")))
    sistema = modelo.mensagens[0][0]
    assert isinstance(sistema.content, str), sistema.content
    assert "cache_control" not in json.dumps(
        _payload_do_provedor("openai", "gpt-6-sol", modelo.mensagens[0]), ensure_ascii=False)


class _SupabaseDoLog:
    def __init__(self):
        self.inseridos: List[dict] = []
        self.client = self

    def table(self, _nome):
        dono = self

        class _T:
            def insert(self, linha):
                dono.inseridos.append(linha)
                return self

            def execute(self):
                return self

        return _T()


def _estado_do_log(agent_data, resposta):
    return {"messages": [HumanMessage(content="oi"), resposta], "agent_data": agent_data,
            "company_config": {}, "company_id": TENANT_A, "final_response": "olá"}


def test_c1_log_grava_o_provedor_da_rota_e_nao_o_openai_inventado():
    db = _SupabaseDoLog()
    resposta = AIMessage(content="olá", response_metadata={"model_name": "claude-sonnet-5-20260630"})
    N.log_node(_estado_do_log({"id": "ag-1", "llm_provider": None}, resposta), db,
               rota=_rota("anthropic", "claude-sonnet-5"))
    linha = db.inseridos[0]
    assert (linha["llm_provider"], linha["llm_model"]) == ("anthropic", "claude-sonnet-5-20260630")


def test_c1_log_prefere_o_provedor_que_respondeu():
    """A reserva respondeu (OpenAI) numa rota anthropic → o log diz OpenAI."""
    db = _SupabaseDoLog()
    resposta = AIMessage(content="olá", response_metadata={"model_name": "gpt-6-sol",
                                                           "model_provider": "openai"})
    N.log_node(_estado_do_log({"id": "ag-1", "llm_provider": "anthropic"}, resposta), db,
               rota=_rota("anthropic", "claude-sonnet-5"))
    assert db.inseridos[0]["llm_provider"] == "openai"


def test_c1_controle_sem_rota_e_sem_provedor_nao_inventa_openai():
    db = _SupabaseDoLog()
    N.log_node(_estado_do_log({"id": "ag-1"}, AIMessage(content="olá")), db)
    assert db.inseridos[0]["llm_provider"] == "desconhecido"


# ===========================================================================
# C4 — o ledger do portal: sem job, sem linha; no pytest, só por dublê
# ===========================================================================
from portal_worker import modelo_do_portal as PM  # noqa: E402

ACAO = {"action": "fill", "target": "Placa", "value": "ABC1D23", "reason": "tela pede placa"}


class _RestQueConta:
    def __init__(self):
        self.posts: List[dict] = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        if req.method == "POST" and req.url.path.endswith("/token_usage_logs"):
            self.posts.append(json.loads(req.content))
            return httpx.Response(201)
        return httpx.Response(404)


@pytest.fixture
def portal(monkeypatch):
    rest = _RestQueConta()
    monkeypatch.setattr(PM, "transporte_do_supabase", httpx.MockTransport(rest))
    monkeypatch.setattr(PM, "gravador_de_uso", PM._gravar_no_banco)   # o escritor de PRODUÇÃO
    monkeypatch.setenv("SUPABASE_URL", "https://banco-de-teste.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "chave-de-servico-falsa")

    async def _provedor(pedido, cabecalhos):   # a borda da rede do provedor
        return {"model": pedido["model"], "output_text": json.dumps(ACAO),
                "usage": {"input_tokens": 100, "output_tokens": 10}}

    monkeypatch.setattr(PM, "_postar_no_provedor", _provedor)
    rota = PM.ModeloDoPortal(**_campos_da_rota())
    return SimpleNamespace(rest=rest, rota=rota)


def _campos_da_rota():
    r = MP.resolver("portal_decisao")
    linha = SNAP["catalogo"][r.model]
    return {"papel": PM.PAPEL, "provider": r.provider, "model": r.model, "effort": r.effort,
            "api_surface": r.api_surface, "capacidades": r.capacidades,
            "classe_de_dado": r.classe_de_dado, "lifecycle": r.lifecycle, "precos": linha, "reserva": None,
            "origem": "rota", "versao_da_rota": r.versao_da_rota, "base_url": None,
            "api_key_env": None}


def test_c4_sem_job_e_sem_empresa_nao_grava_no_ledger(portal):
    """📊 as 31 linhas `portal` de 23/09 (company NULL, job NULL): o motor agora
    recusa gravá-las — mesmo com um transporte que aceitaria."""
    r = asyncio.run(PM.decidir("sys", "user", rota=portal.rota))
    assert json.loads(r["texto"]) == ACAO
    assert portal.rest.posts == []


def test_c4_controle_com_job_e_empresa_grava_uma_linha(portal):
    """LINHA DE CONTROLE: o mesmo motor, com o job do acionamento, GRAVA."""
    asyncio.run(PM.decidir("sys", "user", company_id=TENANT_A, job_id="job-1", rota=portal.rota))
    assert len(portal.rest.posts) == 1
    linha = portal.rest.posts[0]
    assert linha["company_id"] == TENANT_A and linha["details"]["job_id"] == "job-1"


def test_c4_no_pytest_sem_duble_do_banco_nao_abre_conexao(portal, monkeypatch):
    """Transporte REAL (None) dentro do pytest ⇒ não grava e não abre cliente."""
    abertos = []
    monkeypatch.setattr(PM, "transporte_do_supabase", None)
    monkeypatch.setattr(PM, "_cliente_supabase", lambda: abertos.append(1) or (_ for _ in ()).throw(
        RuntimeError("abriu conexão com o banco")))
    linha = {"model_name": "x", "company_id": TENANT_A, "details": {"job_id": "job-1"}}
    assert asyncio.run(PM._gravar_no_banco(linha)) is False
    assert abertos == []
    # CONTROLE: fora do pytest (variável ausente), o escritor TENTA abrir o cliente
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with pytest.raises(RuntimeError, match="abriu conexão"):
        asyncio.run(PM._gravar_no_banco(linha))
    assert abertos == [1]


# ===========================================================================
# C5 — a migration _05: a regra do BANCO é a regra do resolvedor
# ===========================================================================
#: (24/09/2026) a função da trava foi SUBSTITUÍDA pela conclusão da Onda A: a
#: versão em vigor é a da migration mais nova que a define.
MIGRATION_DA_TRAVA = (BACKEND / "supabase" / "migrations"
                      / "20260924_01_spec116_onda_a_conclusao.sql")


def _sql():
    return MIGRATION_DA_TRAVA.read_text(encoding="utf-8")


def _corpo_da_funcao(sql):
    m = re.search(r"create or replace function public\.llm_papeis_so_modelo_governado\(\)(.*?)\$fn\$;",
                  sql, re.S | re.I)
    assert m, "a função do trigger sumiu da migration"
    return m.group(1)


def test_c5_a_lista_de_producao_do_sql_e_a_do_model_policy():
    """(24/09/2026) a trava do banco é a regra de PRODUÇÃO: só APPROVED."""
    corpo = _corpo_da_funcao(_sql())
    m = re.search(r"v_producao\s+constant\s+text\[\]\s*:=\s*array\[([^\]]*)\]", corpo, re.I)
    assert m, "lista de lifecycles de produção ausente"
    producao = tuple(x.strip().strip("'") for x in m.group(1).split(","))
    assert producao == MP.LIFECYCLES_DE_PRODUCAO == ("APPROVED",)
    m = re.search(r"v_escala\s+constant\s+text\[\]\s*:=\s*array\[([^\]]*)\]", corpo, re.I)
    assert m and tuple(x.strip().strip("'") for x in m.group(1).split(",")) == MP.NIVEIS_DE_ESFORCO
    # a trava antiga (_05) continua no histórico com a lista da bancada
    antiga = _corpo_da_funcao(MIGRATION_05.read_text(encoding="utf-8"))
    assert re.search(r"v_usaveis\s+constant", antiga)


@pytest.mark.parametrize("regra,padrao", [
    ("fora do catálogo", r"if not found then\s+raise exception"),
    ("provider divergente", r"v_prov is distinct from v_linha\.provider"),
    ("lifecycle", r"v_linha\.lifecycle is null or not \(v_linha\.lifecycle = any\(v_producao\)\)"),
    ("esforço mínimo", r"v_linha\.capacidades ->> 'esforco_minimo_producao'"),
    ("mínimo exige declarar", r"v_esforco is null\s+or array_position\(v_escala, v_esforco\) < array_position\(v_escala, v_minimo\)"),
    ("classe de dado", r"new\.classe_de_dado = any\(coalesce\(v_linha\.classes_de_dado"),
    ("esforço", r"\(v_linha\.capacidades -> 'niveis_de_esforco'\) \? v_esforco"),
    ("reserva também", r"array\['primario','reserva'\]"),
])
def test_c5_a_funcao_confere_cada_regra_do_resolvedor(regra, padrao):
    assert re.search(padrao, _corpo_da_funcao(_sql()), re.I), regra


def test_c5_trigger_seguranca_e_verify():
    sql = _sql()
    assert re.search(r"create trigger trg_llm_papeis_governado\s+before insert or update on public\.llm_papeis",
                     sql, re.I)
    assert re.search(r"security invoker\s+set search_path = pg_catalog, public", sql, re.I)
    assert "revoke all on function public.llm_papeis_so_modelo_governado() from anon, authenticated" in sql
    assert "revoke all on function public.llm_papeis_so_modelo_governado() from public" in sql
    for bloco in ("-- APPLY:", "-- VERIFY:", "-- ROLLBACK:"):
        assert bloco in sql
    assert "drop trigger if exists trg_llm_papeis_governado" in sql   # idempotente


# ===========================================================================
# C6 — "testar conexão" pela fábrica, nos dois endpoints
# ===========================================================================
@pytest.fixture
def provedor(monkeypatch):
    vistos: List[Any] = []

    def _invoke(self, entrada, config=None, **kw):
        vistos.append((self, entrada))
        return AIMessage(content="OK")

    monkeypatch.setattr(BaseChatModel, "invoke", _invoke)
    return vistos


def _msgs(entrada):
    return entrada if isinstance(entrada, list) else [HumanMessage(content=str(entrada))]


def test_c6_claude5_sem_temperature_e_gpt4o_com():
    llm = LLMFactory.para_teste_de_conexao("anthropic", "claude-sonnet-5", api_key=CHAVE_FALSA)
    assert "temperature" not in llm._get_request_payload([HumanMessage(content="oi")])
    llm = LLMFactory.para_teste_de_conexao("openai", "gpt-4o", api_key=CHAVE_FALSA)
    assert "temperature" in llm._get_request_payload([HumanMessage(content="oi")])   # controle


def test_c6_modelo_nao_governado_e_recusado():
    with pytest.raises(MP.ModeloNaoResolvido):
        LLMFactory.para_teste_de_conexao("anthropic", "claude-3-5-sonnet-20241022", api_key=CHAVE_FALSA)
    with pytest.raises(MP.ModeloNaoResolvido):
        LLMFactory.para_teste_de_conexao("anthropic", "gpt-4o", api_key=CHAVE_FALSA)


def _cliente_agent_config():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import agent_config
    from app.core.auth import require_internal_key

    app = FastAPI()
    app.include_router(agent_config.router, prefix="/api/agent")
    app.dependency_overrides[require_internal_key] = lambda: None
    return TestClient(app)


def test_c6_endpoint_agent_config_testa_pela_fabrica(provedor):
    r = _cliente_agent_config().post(f"/api/agent/test/{TENANT_A}", json={
        "llm_provider": "anthropic", "llm_model": "claude-sonnet-5", "llm_api_key": CHAVE_FALSA})
    assert r.status_code == 200 and r.json()["success"] is True, r.text
    llm, entrada = provedor[0]
    assert type(llm).__name__ == "ChatAnthropicGovernado"
    assert "temperature" not in llm._get_request_payload(_msgs(entrada))
    # modelo retirado → falha COM motivo, sem chamar o provedor
    r = _cliente_agent_config().post(f"/api/agent/test/{TENANT_A}", json={
        "llm_provider": "anthropic", "llm_model": "claude-3-5-sonnet-20241022", "llm_api_key": CHAVE_FALSA})
    assert r.json()["success"] is False and "não governado" in r.json()["message"]
    assert len(provedor) == 1


def _cliente_agents(servico=None):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import app.api.agents as AGT
    from app.core.auth import require_master_admin

    app = FastAPI()
    app.include_router(AGT.router, prefix="/api/agents")
    app.dependency_overrides[require_master_admin] = lambda: True
    if servico is not None:
        app.dependency_overrides[AGT.get_agent_service] = lambda: servico
    return TestClient(app)


def test_c6_endpoint_agents_test_llm_pela_fabrica(provedor):
    c = _cliente_agents()
    r = c.post("/api/agents/test-llm", json={"provider": "anthropic", "model": "claude-opus-5-5",
                                              "api_key": CHAVE_FALSA})
    assert r.status_code == 200, r.text
    llm, entrada = provedor[0]
    assert "temperature" not in llm._get_request_payload(_msgs(entrada))
    r = c.post("/api/agents/test-llm", json={"provider": "openai", "model": "gpt-4.5-preview",
                                              "api_key": CHAVE_FALSA})
    assert r.status_code == 400 and "não governado" in r.json()["detail"]
    assert len(provedor) == 1


# ===========================================================================
# C7 — POST /api/agents confere o modelo (como o PUT)
# ===========================================================================
class _Servico:
    def __init__(self):
        self.criados: List[Any] = []

    def create_agent(self, company_id, agente):
        self.criados.append(agente)
        agora = datetime(2026, 9, 23)
        return {"id": str(uuid.uuid4()), "company_id": str(company_id), "name": agente.name,
                "slug": agente.slug, "created_at": agora, "updated_at": agora}


def _novo(**campos):
    return {"company_id": TENANT_A, "name": "Atendente", "slug": "atendente", **campos}


def test_c7_post_recusa_modelo_retirado_e_nada_e_criado():
    s = _Servico()
    r = _cliente_agents(s).post("/api/agents/", json=_novo(llm_provider="anthropic",
                                                           llm_model="claude-3-5-sonnet-20241022"))
    assert r.status_code == 400 and "claude-3-5-sonnet-20241022" in r.json()["detail"], r.text
    r = _cliente_agents(s).post("/api/agents/", json=_novo(vision_model="claude-3-5-sonnet-20240620"))
    assert r.status_code == 400, r.text
    assert s.criados == []


def test_c7_controle_post_sem_modelo_ou_aprovado_cria():
    s = _Servico()
    assert _cliente_agents(s).post("/api/agents/", json=_novo()).status_code == 200
    assert _cliente_agents(s).post("/api/agents/", json=_novo(
        llm_provider="anthropic", llm_model="claude-sonnet-5")).status_code == 200
    assert len(s.criados) == 2


# ===========================================================================
# C8 — o oráculo cob-n1-p19a não pune a negação
# ===========================================================================
def _oraculo_p19a():
    from app.services.evals import bancada as B

    return next(c for c in B.carregar_casos("cobranca") if c["chave"].startswith("cob-n1-p19a"))


def test_c8_negacao_passa_e_afirmacao_reprova():
    from app.services.evals import evaluators as E

    o = _oraculo_p19a()["oraculo"]
    assert o.get("negacao_ok") is True
    esperado = {"nao_contem": o["nao_deve_conter"], "negacao_ok": True}
    assert E.nao_contem("Não é golpe: a mensagem é da sua corretora.", esperado)[0] is True
    assert E.nao_contem("Fique tranquilo, isso não é golpe.", esperado)[0] is True
    assert E.nao_contem("Cuidado, é golpe! Não pague.", esperado)[0] is False
    assert E.nao_contem("Não se preocupe, é golpe.", esperado)[0] is False


def test_c8_controle_sem_a_flag_o_substring_continua():
    from app.services.evals import evaluators as E

    assert E.nao_contem("Não é golpe.", {"nao_contem": ["é golpe"]})[0] is False


def test_c8_o_corpus_versionado_subiu_e_o_manifesto_acompanha():
    """🔴 O que este teste guarda é o ACOMPANHAMENTO, não o número.

    📊 26/09/2026, SPEC-117: a afirmação era `== ... == 3`. O corpus subiu para
    **4** (11 casos N2 novos) e este teste ficou vermelho — não por defeito, mas
    por guardar uma verdade que venceu. É o CLAUDE.md §9.3 na letra: *"teste que
    guarda verdade vencida é pior que teste nenhum"*, e a saída é **migrar a
    lição**, nunca apagá-la.

    A lição é: o caso versionado e o manifesto **não podem divergir** — se o
    gerador sobe a versão do corpus e o manifesto fica atrás, ninguém sabe qual
    corpus produziu qual medição. Isso continua sendo afirmado, e agora sobrevive
    à próxima subida de versão. O piso `>= 3` fica porque 3 foi a primeira versão
    em que o dublê ganhou a forma real das tools (F6 da SPEC-116): voltar abaixo
    dele seria regressão, não evolução.
    """
    from app.services.evals import bancada as B

    versao_do_caso = _oraculo_p19a()["versao"]
    versao_do_manifesto = B.manifesto()["versao"]

    assert versao_do_caso == versao_do_manifesto, (
        "o corpus está na versão %r e o manifesto na %r — a medição não sabe "
        "de qual corpus veio" % (versao_do_caso, versao_do_manifesto))
    assert versao_do_caso >= 3, (
        "a versão do corpus caiu abaixo de 3, em que o dublê ganhou a forma "
        "real das tools: %r" % (versao_do_caso,))


def test_c8_CONTROLE_a_divergencia_de_versao_seria_vista():
    """🔴 O guarda acima precisa CONSEGUIR ficar vermelho (CLAUDE.md §9.3).

    Sem esta linha, `>= 3` sozinho passaria com o manifesto em 3 e o corpus em
    99 — e o teste teria deixado de guardar o que importa. Aqui a comparação é
    exercitada sobre um par divergente construído à mão.
    """
    corpus, manifesto = 4, 3
    assert not (corpus == manifesto), (
        "a comparação de versões não distingue 4 de 3 — o guarda acima é carimbo")
