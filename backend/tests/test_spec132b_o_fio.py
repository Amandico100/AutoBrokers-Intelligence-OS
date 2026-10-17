# -*- coding: utf-8 -*-
"""SPEC-132-B · B4 — O TESTE DO FIO da Cotação Rápida (a costura: a saída REAL de uma fatia é a entrada da outra).

    a capability da migration 20261014_04 (o binding do papel core, o scope)
      → `create_agent_graph` REAL anexa as 3 ferramentas (e só ao papel core, e só com a capability ativa)
    → o LLM DUBLÊ "lê" a frase do corretor e chama `cotacao_preparar` (com um `user_id`/`session_id` FALSOS nos
      argumentos — o `tool_node` REAL tem de sobrescrevê-los com os do ESTADO do turno)
    → o resumo + o `confirmacao_id` → o "sim" → `cotacao_disparar` pelo MESMO `tool_node`
    → a porta REAL → `qual_agger` (a conta DA PESSOA) → a fila → o MOTOR real com o robô do Agger DUBLÊ
    → o Work Run `cotacao.chat` pelo `SmithWorker._processar` REAL → `publicar_cotacao` REAL (B2)
    → o HTML que `abrir_compartilhado` SERVE é a página de VENDA (a marca da corretora fictícia, sem o canal)
    → a mensagem do assistente gravada UMA vez na MESMA conversa, com a tabela preenchida pelo `resumo` REAL da B2
    → o `result_payload` do run (link, token, mensagem, resumo) → `GET /api/cotacoes` REAL (B3) lista o item com o
      link, e o "Ver apresentação" devolve o MESMO link sem republicar
    Duas corretoras: nada atravessa (ferramenta, conversa, lista, detalhe).

Dublê SÓ na borda (CLAUDE.md §9.4): o banco (`BancoU1`, o PostgREST em memória com as travas do U1), o Agger (o
`RoboDuble` do motor, rodadas reais da fixture), o Redis (em memória), o MODELO (o LLM que escolhe a ferramenta) e o
`get_supabase_client` (⛔ nunca o banco real: o registro de invocação cai no nulo).
⛔ Dados FICTÍCIOS (§13.9). Rodar: cd backend && python -m pytest tests/test_spec132b_o_fio.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import functools
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec129b_o_motor as TM  # noqa: E402
import test_spec1310_f3_contas as F3  # noqa: E402
import test_spec132b_a_conversa as CONV  # noqa: E402
from test_spec129b_o_motor import ambiente  # noqa: E402,F401  (fixture)

from app.agents.tools import cotacao_tool as T  # noqa: E402
from app.services.cotacao import confirmacao as CONF  # noqa: E402
from app.services.cotacao import resposta as RESP  # noqa: E402
from app.services.cotacao import workflow as WF  # noqa: E402
from app.services.multicalculo import config as CFG  # noqa: E402
from app.services.multicalculo.porta import MulticalculoProvider  # noqa: E402
from app.services.multicalculo.repositorio import RepositorioMulticalculo  # noqa: E402

BASE = "https://app.exemplo.test"
CHAVE_INTERNA = "chave-interna-do-fio-132b"
MIGRATION = BACKEND / "supabase" / "migrations" / "20261014_04_spec132b_capability_cotacao.sql"
CAPABILITY = "tenant.multicalculo.cotacao"
FERRAMENTAS = ("cotacao_preparar", "cotacao_disparar", "cotacao_ajustar")
CPF, CPF_PONTUADO, NOME = CONV.CPF, CONV.CPF_PONTUADO, CONV.NOME
FRASE = (f"cota o Onix 2022 placa ABC1D23 da Fulana, CPF {CPF_PONTUADO}, nasc 01/02/1980, CEP 01001-000, "
         "20 anos de carteira")
MARCA_A = "Lumen Seguros Ficticia"
MARCA_B = "Boreal Seguros Ficticia"


# =====================================================================================================================
# a capability — o que a migration grava, lido do PRÓPRIO arquivo (se ela perder o scope, o grafo nega: vermelho)
# =====================================================================================================================
def linhas_da_migration() -> dict:
    sql = MIGRATION.read_text(encoding="utf-8")
    corpo = "\n".join(l for l in sql.splitlines() if not l.lstrip().startswith("--"))
    cap = re.search(r"insert into public\.capabilities.*?values\s*\((.*?)\)\s*on conflict", corpo, re.S | re.I)
    assert cap, "a migration não insere a capability"
    valores = [v.strip().strip("'") for v in re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", cap.group(1))]
    chaves = ("capability_key", "name", "category", "owner", "risk", "requires_connection", "requires_approval",
              "provider", "is_active")
    capability = dict(zip(chaves, valores))
    for k in ("requires_connection", "requires_approval", "is_active"):
        capability[k] = capability[k].lower() == "true"
    capability["provider"] = None if capability["provider"].lower() == "null" else capability["provider"]
    b = re.search(r"insert into public\.capability_bindings.*?select\s+'(\w+)',\s*'([\w.]+)',\s*(true|false),\s*"
                  r"'(\{.*?\})'::jsonb", corpo, re.S | re.I)
    assert b, "a migration não insere o binding"
    binding = {"agent_role": b.group(1), "capability_key": b.group(2), "enabled": b.group(3) == "true",
               "scope": json.loads(b.group(4))}
    return {"capability": capability, "binding": binding}


def semear_capability(banco, *, com_binding: bool = True) -> None:
    linhas = linhas_da_migration()
    banco.semear("capabilities", dict(linhas["capability"]))
    if com_binding:
        banco.semear("capability_bindings", dict(linhas["binding"]))


# =====================================================================================================================
# o grafo REAL (create_agent_graph) — o modelo e o checkpointer são a borda
# =====================================================================================================================
class _ModeloDuble:
    def bind_tools(self, tools):
        return self


def ferramentas_do_grafo(monkeypatch, db, company_id: str, *, papel: str = "core") -> list:
    """As ferramentas que o `create_agent_graph` REAL entrega ao `tool_node` desta corretora (capturadas no `partial`
    do nó, sem tocar em nada do grafo)."""
    from app.agents import graph as G

    capturado = {}
    parcial = functools.partial

    def _partial(f, *a, **kw):
        if f is G.tool_node:
            capturado["tools"] = list(kw["tools"])
        return parcial(f, *a, **kw)

    async def _sem_checkpointer():
        return None

    resolvido = SimpleNamespace(provider="dublê", model="dublê", reserva=None, papel="core", effort=None)
    monkeypatch.setattr(G, "partial", _partial)
    monkeypatch.setattr(G, "get_async_postgres_checkpointer", _sem_checkpointer)
    monkeypatch.setattr(G, "get_api_key_for_provider", lambda *a, **k: "chave-dublê")
    monkeypatch.setattr(G.LLMFactory, "resolver_para", staticmethod(lambda *a, **k: resolvido))
    monkeypatch.setattr(G.LLMFactory, "create_llm", staticmethod(lambda *a, **k: _ModeloDuble()))
    asyncio.run(G.create_agent_graph(company_config={}, api_key="x", qdrant_service=None, supabase_client=db,
                                     company_id=company_id, agent_data={"agent_role": papel},
                                     enable_logging=False))
    return capturado["tools"]


# =====================================================================================================================
# o turno: o LLM dublê escolhe a ferramenta; o tool_node REAL executa
# =====================================================================================================================
def turno(tools, *, company_id: str, user_id: str, session_id: str, nome: str, args: dict) -> str:
    """UMA chamada de ferramenta pelo `tool_node` REAL, com o ESTADO do turno (quem pediu, a conversa). O LLM dublê
    põe nos argumentos um `user_id`/`session_id` FALSOS: só o estado pode valer."""
    from langchain_core.messages import AIMessage, HumanMessage

    from app.agents.nodes import tool_node

    estado = {"messages": [HumanMessage(content=FRASE),
                           AIMessage(content="", tool_calls=[{"name": nome, "args": dict(args),
                                                              "id": f"call-{uuid4().hex[:8]}"}])],
              "company_id": company_id, "user_id": user_id, "session_id": session_id,
              "agent_data": {"agent_role": "core", "company_id": company_id}, "tools_used": [], "rag_chunks": []}
    saida = asyncio.run(tool_node(estado, tools))
    [msg] = [m for m in saida["messages"] if getattr(m, "type", "") == "tool"]
    return str(msg.content)


# =====================================================================================================================
# o mundo
# =====================================================================================================================
class Fio(CONV.Mundo):
    def corretora_com_marca(self, marca: str, cor: str) -> str:
        from dubles.mundo_da_proposta import _paleta

        a = self.corretora()
        for e in self.banco.linhas("companies"):
            if e["id"] == a:
                e["company_name"] = marca.replace("Seguros", "Corretora")
        self.banco.semear("brand_profiles", {
            "company_id": a, "display_name": marca, "is_published": True, "palette": _paleta(cor, "#EE7501"),
            "susep_code": "SUSEP 10.2030405", "contact": {"whatsapp": "5548999990132"},
            "about_md": "Corretora de bairro, atendimento com calma.", "insurers": ["Porto", "Allianz", "Tokio"]})
        return a

    def runs(self, corretora):
        return [r for r in self.banco.linhas("work_runs")
                if r["workflow_key"] == "cotacao.chat" and r["company_id"] == corretora]

    def api(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.api import cotacoes as API

        self.mp.setattr(API, "_db", lambda: self.db)
        app = FastAPI()
        app.include_router(API.router)
        c = TestClient(app)
        c.cab = {"X-AutoBrokers-Internal-Key": CHAVE_INTERNA}
        return c


@pytest.fixture
def fio(ambiente, monkeypatch):
    amb = ambiente
    monkeypatch.setenv("MULTICALCULO_HMAC_KEY", F3.CHAVE_HMAC)
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", CHAVE_INTERNA)
    monkeypatch.delenv("TOOL_GATEWAY_MODE", raising=False)
    m = Fio(amb, monkeypatch)

    async def _redis():
        return m.redis

    def _sem_banco_real(*a, **k):
        raise RuntimeError("o teste do fio nunca abre o banco real")

    import app.core.database as DB

    monkeypatch.setattr(DB, "get_supabase_client", _sem_banco_real)
    monkeypatch.setattr(CONF, "obter_redis", _redis)
    # a borda do Agger: a porta REAL com o relógio do banco dublê e a marca `preset` que o robô dublê lê (como na B1)
    monkeypatch.setattr(T, "_porta", lambda db: MulticalculoProvider(RepositorioMulticalculo(db),
                                                                      agora=amb.relogio.agora,
                                                                      presets=lambda o: {"preset": o}))
    monkeypatch.setattr(WF, "_dormir", lambda s: asyncio.sleep(0))
    semear_capability(m.banco)
    return m


def _id_da_confirmacao(saida: str) -> str:
    return CONV._id_da_confirmacao(saida)


# =====================================================================================================================
# o GUARDA do fio (as mutações no fim do arquivo o deixam VERMELHO)
# =====================================================================================================================
def guarda_o_fio(m: Fio) -> dict:
    a = m.corretora_com_marca(MARCA_A, "#1D5579")
    b = m.corretora_com_marca(MARCA_B, "#2E7D32")
    uid, conta = m.pessoa(a, com_agger=True)
    intruso, _conta_do_intruso = m.pessoa(a, com_agger=True)     # outra pessoa da MESMA corretora, com Agger próprio
    conversa, sess = m.conversa(a, uid)
    _conversa_do_intruso, sess_do_intruso = m.conversa(a, intruso)
    ub, _ = m.pessoa(b, com_agger=True)
    conversa_b, sess_b = m.conversa(b, ub)
    m.falou(conversa, FRASE)

    # ① o grafo REAL anexa as 3 ferramentas à corretora (o binding é por papel: vale para A e para B)
    tools_a = ferramentas_do_grafo(m.mp, m.db, a)
    assert set(FERRAMENTAS) <= {t.name for t in tools_a}, "o grafo não anexou a Cotação Rápida"
    assert {t.company_id for t in tools_a if t.name in FERRAMENTAS} == {a}
    tools_b = ferramentas_do_grafo(m.mp, m.db, b)
    assert {t.company_id for t in tools_b if t.name in FERRAMENTAS} == {b}

    # ② preparar — o modelo escreve um user_id/session_id FALSOS; o estado do turno vence
    falsos = {"user_id": intruso, "session_id": sess_do_intruso}
    r1 = turno(tools_a, company_id=a, user_id=uid, session_id=sess, nome="cotacao_preparar",
               args={**CONV.COMPLETOS, **falsos})
    assert "Confira antes de eu calcular" in r1 and "no seu Agger" in r1, r1
    assert not m.pedidos(), "preparar NÃO calcula (D-132B-03)"

    # ③ o "sim" do CORRETOR (uma fala NOVA na conversa, depois do resumo — conserto juiz B4) → disparar pelo MESMO
    #    tool_node. ⚠️ §9.3: antes este guarda encadeava preparar → disparar sem fala nenhuma no meio (era verdade
    #    vencida: o código não distinguia; agora recusa — `test_b4_preparar_e_disparar_no_mesmo_turno_nao_calcula`)
    m.falou(conversa, "sim, pode calcular")
    r2 = turno(tools_a, company_id=a, user_id=uid, session_id=sess, nome="cotacao_disparar",
               args={"confirmacao_id": _id_da_confirmacao(r1), **falsos})
    assert "Calculando nas seguradoras no seu Agger" in r2, r2
    [ped] = m.pedidos(a)
    assert (ped["servico"], ped["solicitante_user_id"]) == ("cotacao", uid), "a cotação não é de quem pediu"
    assert {(c["conta_exigida_id"], c["conta_regra"]) for c in m.calculos(ped["id"])} == {(conta, "cotacao_da_pessoa")}
    [run] = m.runs(a)
    assert (run["conversation_id"], run["requester_user_id"]) == (conversa, uid)
    ent = run["input_payload"]
    assert (ent.get("cliente_nome_curto"), ent.get("documento_mascarado"), ent.get("placa")) == \
        ("Fulana", "***.***.***-25", "ABC1D23"), ent
    assert CPF not in json.dumps(ent) and NOME not in json.dumps(ent), "PII em claro no run"

    # ④ o motor real (o robô do Agger dublê) e o Work Run pelo worker real
    m.motor()
    assert {(c["status"], c["account_id"]) for c in m.calculos(ped["id"])} == {("fechado", conta)}
    m.rodar_runs(a)
    run = m.banco.run(run["id"])
    assert run["status"] == "completed", run["status"]

    # ⑤ a mensagem do assistente: UMA, na MESMA conversa, com o link e a tabela do `resumo` REAL da B2
    msgs = m.mensagens_do_assistente(conversa)
    assert len(msgs) == 1, [x["content"][:60] for x in msgs]
    texto, cot = msgs[0]["content"], msgs[0]["payload"]["cotacao"]
    url = cot["url"]
    assert url and url.startswith(f"{BASE}/r/"), cot
    assert f"Apresentação para o cliente: {url}" in texto and "**Mensagem para o cliente**" in texto, texto
    resumo = (run.get("result_payload") or {}).get("resumo") or {}
    assert resumo.get("opcoes"), f"o run não guardou o resumo da B2: {run.get('result_payload')}"
    linhas = [l for l in texto.splitlines() if l.startswith("| ") and not l.startswith("| |")]
    assert linhas and len(linhas) == min(3, len(resumo["opcoes"])), texto
    for linha, op in zip(linhas, resumo["opcoes"]):
        assert linha.startswith(f"| {op['papel']} | {op['seguradora']} | {op['parcela']['vezes']}x "), (linha, op)
        assert "| — | — |" not in linha, f"a tabela saiu vazia do resumo real: {linha}"
    assert CPF not in texto and CPF_PONTUADO not in texto
    assert not m.mensagens_do_assistente(conversa_b), "a resposta de A caiu na conversa de B"

    # ⑥ o HTML SERVIDO pelo link é a página de VENDA da corretora A
    from app.services.artifacts.service import ArtifactService

    token = url.rsplit("/r/", 1)[1]
    servido = ArtifactService(m.banco.visao("rota-publica")).abrir_compartilhado(token, user_agent="Mozilla/5.0")
    assert servido and servido.get("html"), "o link não abriu"
    html = servido["html"]
    canal = CFG.PADRAO_DO_PRODUTO["canal"]
    # SPEC-130-C (D-130C-05, §9.3): o selo Nível 5 passou a ser da CORRETORA nas três páginas; o NOME do canal continua fora
    for proibido in (canal["nome"],):
        assert proibido.lower() not in html.lower(), f"a página da corretora fala do canal: {proibido}"
    # a lição migra (§9.3): o selo do programa agora TEM de estar na página da corretora (config padrão: ligado)
    assert canal["selo"]["nome"] in html, "o selo Nível 5 da corretora não chegou à página de venda (D-130C-05)"
    assert MARCA_A in html and MARCA_B not in html, "a página não tem a marca de quem cotou"
    assert "Fulana" in html and CPF not in html and CPF_PONTUADO not in html

    # ⑦ o result_payload do run (o que a B3 lê) e a lista REAL da API
    res = run["result_payload"]
    assert (res.get("url"), res.get("token")) == (url, token), res
    assert res.get("mensagem") and url in res["mensagem"]["texto"], res.get("mensagem")
    api = m.api()
    lista = api.get("/api/cotacoes", params={"company_id": a, "user_id": uid, "escopo": "minhas"}, headers=api.cab)
    assert lista.status_code == 200, lista.text
    [item] = lista.json()["itens"]
    assert (item["id"], item["estado"], item["tem_apresentacao"], item["da_conversa"]) == \
        (ped["id"], "pronta", True, True), item
    assert (item["cliente"], item["documento"], item["placa"]) == ("Fulana", "***.***.***-25", "ABC1D23"), item
    versoes_antes = len(m.banco.linhas("artifact_versions"))
    ap = api.post(f"/api/cotacoes/{ped['id']}/apresentacao", json={"company_id": a, "user_id": uid}, headers=api.cab)
    assert ap.status_code == 200 and ap.json()["url"] == url, ap.text
    envio = api.post(f"/api/cotacoes/{ped['id']}/envio", json={"company_id": a, "user_id": uid, "via": "copiar"},
                     headers=api.cab)
    assert envio.status_code == 200 and url in envio.json()["texto"], envio.text
    assert len(m.banco.linhas("artifact_versions")) == versoes_antes, "o 'Ver apresentação' republicou"
    # e a B2 chamada de novo (o "Ver apresentação" de uma cotação sem link no run) devolve o MESMO link
    from app.services.multicalculo import proposta as P

    de_novo = asyncio.run(P.publicar_cotacao(a, ped["id"], pessoa_user_id=uid, primeiro_nome="Fulana", db=m.db))
    assert (de_novo["url"], de_novo["token"]) == (url, token), "publicar de novo a MESMA página criou outro link"
    assert len(m.banco.linhas("artifact_versions")) == versoes_antes, "publicar de novo a MESMA página versionou"
    assert de_novo["resumo"] == resumo, "o resumo devolvido no reaproveitamento não é o da página"

    # ⑧ duas corretoras: nada atravessa
    lista_b = api.get("/api/cotacoes", params={"company_id": b, "user_id": ub, "escopo": "todas"}, headers=api.cab)
    assert lista_b.status_code == 200 and lista_b.json()["itens"] == [], lista_b.text
    det_b = api.get(f"/api/cotacoes/{ped['id']}", params={"company_id": b, "user_id": ub}, headers=api.cab)
    assert det_b.status_code == 404, det_b.text
    r_b = turno(tools_b, company_id=b, user_id=ub, session_id=sess, nome="cotacao_ajustar",
                args={"pedido_id": ped["id"], "tipo": "franquia", "valor": "reduzida"})
    assert "Não achei esta conversa na sua corretora" in r_b, r_b
    r_b2 = turno(tools_b, company_id=b, user_id=ub, session_id=sess_b, nome="cotacao_ajustar",
                 args={"pedido_id": ped["id"], "tipo": "franquia", "valor": "reduzida"})
    assert "Não achei essa cotação na sua corretora" in r_b2, r_b2
    assert len(m.pedidos()) == 1 and not m.runs(b)
    return {"a": a, "uid": uid, "pedido": ped, "url": url, "run": run}


# =====================================================================================================================
# os testes
# =====================================================================================================================
def test_o_fio_da_frase_do_corretor_a_aba_cotacoes(fio):
    guarda_o_fio(fio)


def test_a_capability_da_migration_e_o_que_o_resolver_aceita(fio):
    """A migration tem o que o resolver exige de uma capability HIGH (scope não vazio) e o binding é do papel core —
    e SEM o binding o grafo não anexa nada (a linha de controle: o guarda consegue diferir)."""
    from app.agents.capability_resolver import active_keys, resolve_active_capabilities

    linhas = linhas_da_migration()
    assert linhas["capability"]["risk"] == "high" and linhas["capability"]["requires_connection"] is False
    assert linhas["binding"]["agent_role"] == "core" and set(linhas["binding"]["scope"]["ferramentas"]) == \
        set(FERRAMENTAS)
    m = fio
    a = m.corretora()
    assert CAPABILITY in active_keys(resolve_active_capabilities(m.db, a, "core"))
    assert CAPABILITY not in active_keys(resolve_active_capabilities(m.db, a, "attendance"))
    # o atendente do segurado nunca recebe a ferramenta
    assert not set(FERRAMENTAS) & {t.name for t in ferramentas_do_grafo(m.mp, m.db, a, papel="attendance")}
    # a corretora que desligou pelo entitlement não recebe
    m.banco.semear("tenant_capability_entitlements", {"company_id": a, "capability_key": CAPABILITY,
                                                      "enabled": False})
    assert not set(FERRAMENTAS) & {t.name for t in ferramentas_do_grafo(m.mp, m.db, a)}
    # CONTROLE: outra corretora (sem entitlement) recebe — o binding é por papel, vale para QUALQUER corretora
    outra = m.corretora()
    assert set(FERRAMENTAS) <= {t.name for t in ferramentas_do_grafo(m.mp, m.db, outra)}


def test_sem_o_binding_o_grafo_nao_anexa(ambiente, monkeypatch):
    m = Fio(ambiente, monkeypatch)
    import app.core.database as DB

    monkeypatch.setattr(DB, "get_supabase_client", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sem banco")))
    semear_capability(m.banco, com_binding=False)
    a = m.corretora()
    assert not set(FERRAMENTAS) & {t.name for t in ferramentas_do_grafo(monkeypatch, m.db, a)}


def test_a_tabela_do_chat_sai_do_resumo_da_b2_na_ordem_da_pagina():
    """O contrato B2 → B1 (`proposta.resumo_da_cotacao` → `resposta.tabela`), sem o banco: o `papel` da página vence
    o rótulo, a parcela é a ÚNICA da página e "Igual à sua atual" não some quando é a 1ª."""
    resumo = {"opcoes": [
        {"id": "igual_a_atual", "papel": "Igual à sua atual", "seguradora": "Seguradora Um",
         "parcela": {"vezes": 10, "valor": 312.5, "sem_juros": True}, "a_vista": 3125.0, "franquia": 2900.0},
        {"id": "mais_em_conta", "papel": "Mais em conta", "seguradora": "Seguradora Dois",
         "parcela": {"vezes": 6, "valor": 450.0, "sem_juros": False, "total": 2700.0}, "a_vista": 2600.0,
         "franquia": 4100.0},
        {"id": "mais_completa", "papel": "Mais completa", "seguradora": "Seguradora Tres", "parcela": None,
         "a_vista": 3900.0, "franquia": None}]}
    linhas = RESP.tabela(resumo["opcoes"]).splitlines()[2:]
    assert linhas[0].startswith("| Igual à sua atual | Seguradora Um | 10x R$") and "sem juros" in linhas[0]
    assert linhas[1].startswith("| Mais em conta | Seguradora Dois | 6x R$") and "sem juros" not in linhas[1]
    assert linhas[2].startswith("| Mais completa | Seguradora Tres | — |")
    # CONTROLE: o formato antigo (o que a B1 lia antes da costura) NÃO preenche a parcela — os dois formatos diferem
    antigo = [{"id": "recomendada", "seguradora": "X", "premio_anual": 1.0, "parcelas": {"vezes": 10, "valor": 1.0}}]
    assert "| Recomendada | X | — |" in RESP.tabela(antigo)


# =====================================================================================================================
# as MUTAÇÕES — o defeito de costura reintroduzido, o guarda fica VERMELHO
# =====================================================================================================================
def test_mutacao_o_workflow_nao_grava_o_link_no_result_o_fio_fica_vermelho(fio, monkeypatch):
    """O defeito que a costura achou: o worker concluía todo run com `result_payload = {}` — a aba Cotações não tinha o
    link. Com o `Concluido` virando texto puro, o guarda tem de cair."""
    from app.services.work import runs as R

    monkeypatch.setattr(R, "Concluido", lambda resumo, resultado=None: resumo)
    with pytest.raises(AssertionError):
        guarda_o_fio(fio)


def test_mutacao_a_mensagem_le_o_resumo_e_nao_o_modelo_o_fio_fica_vermelho(fio, monkeypatch):
    """O outro defeito de costura: a B1 montava a mensagem para o cliente com o `resumo` (que não tem o que ela lê) —
    a função recusava e o corretor ficava SEM a mensagem. Reintroduzido, o guarda cai."""
    from app.services.multicalculo import mensagem as MSG

    real = MSG.mensagem_de_cotacao

    def com_o_resumo(modelo, link):
        return real({"opcoes": [{"id": o.get("id"), "seguradora": o.get("seguradora")}
                                for o in (modelo.get("opcoes") or [])]}, link)

    monkeypatch.setattr(MSG, "mensagem_de_cotacao", com_o_resumo)
    with pytest.raises(AssertionError):
        guarda_o_fio(fio)


def test_mutacao_o_link_nao_e_reaproveitado_o_fio_fica_vermelho(fio, monkeypatch):
    """O "Ver apresentação" republicava a cada clique (versão e link novos). Sem o reaproveitamento, o guarda cai."""
    from app.services.multicalculo import proposta as P

    monkeypatch.setattr(P, "link_que_ainda_vale", lambda *a, **k: None)
    with pytest.raises(AssertionError):
        guarda_o_fio(fio)


# =====================================================================================================================
# CONSERTO ÚNICO (juiz 132-B B1/B2/B4 + red team B-1/B-2/B-3) — pelo FIO REAL: tool_node, porta, motor, worker, B2
# publicando de verdade e o HTML que o `/r/` SERVE. Cada guarda tem a mutação logo abaixo (fica VERMELHO com ela).
# =====================================================================================================================
def _servido(m, url: str) -> str:
    from app.services.artifacts.service import ArtifactService

    r = ArtifactService(m.banco.visao("rota-publica")).abrir_compartilhado(url.rsplit("/r/", 1)[1],
                                                                          user_agent="Mozilla/5.0")
    return (r or {}).get("html") or ""


def _tabela(texto: str) -> list:
    return [l for l in texto.splitlines() if l.startswith("| ") and not l.startswith("| |") and "---" not in l]


def _cotacao_pronta(m, *, extra=None, whatsapp=None):
    """Uma cotação inteira pelo fio: a frase, o resumo, o SIM do corretor, o disparo, o motor e o run."""
    a = m.corretora_com_marca(MARCA_A, "#1D5579")
    uid, _ = m.pessoa(a, com_agger=True)
    if whatsapp:
        for v in m.banco.linhas("company_members"):
            if v.get("user_id") == uid and v.get("company_id") == a:
                v.update({"whatsapp_trabalho_e164": whatsapp,
                          "whatsapp_trabalho_confirmado_em": "2026-10-01T00:00:00+00:00"})
    conversa, sess = m.conversa(a, uid)
    m.falou(conversa, FRASE)
    tools = ferramentas_do_grafo(m.mp, m.db, a)
    r1 = turno(tools, company_id=a, user_id=uid, session_id=sess, nome="cotacao_preparar",
               args={**CONV.COMPLETOS, **(extra or {})})
    m.falou(conversa, "sim, pode calcular")
    r2 = turno(tools, company_id=a, user_id=uid, session_id=sess, nome="cotacao_disparar",
               args={"confirmacao_id": _id_da_confirmacao(r1)})
    [ped] = m.pedidos(a)
    m.motor()
    m.rodar_runs(a)
    [msg] = m.mensagens_do_assistente(conversa)
    return {"a": a, "uid": uid, "conversa": conversa, "sess": sess, "tools": tools, "pedido": ped, "r1": r1,
            "r2": r2, "msg": msg, "url": msg["payload"]["cotacao"]["url"]}


# -- B1 · o RECÁLCULO responde com a tabela e o link DO AJUSTE ------------------------------------------------------
def guarda_o_recalculo(m: Fio) -> None:
    c = _cotacao_pronta(m)
    a, pid = c["a"], c["pedido"]["id"]
    r = turno(c["tools"], company_id=a, user_id=c["uid"], session_id=c["sess"], nome="cotacao_ajustar",
              args={"pedido_id": pid, "tipo": "franquia", "valor": "reduzida"})
    assert r.startswith("Recalculando com a franquia reduzida"), r
    m.motor()
    m.rodar_runs(a)
    [aj] = [x for x in m.calculos(pid) if x["opcao"] == "ajuste"]
    assert aj["status"] == "fechado"
    [run_aj] = [x for x in m.runs(a) if (x.get("input_payload") or {}).get("ajuste_calculo_id") == aj["id"]]
    assert m.banco.run(run_aj["id"])["status"] == "completed"
    msgs = m.mensagens_do_assistente(c["conversa"])
    assert len(msgs) == 2, [x["content"][:60] for x in msgs]
    [depois] = [x for x in msgs if x["payload"]["cotacao"]["work_run_id"] == run_aj["id"]]
    assert "(Recalculado com a franquia reduzida.)" in depois["content"]
    assert _tabela(depois["content"]) != _tabela(c["msg"]["content"]), "o recálculo mostrou a tabela de ANTES"
    url = depois["payload"]["cotacao"]["url"]
    assert url and url != c["url"], "o recálculo devolveu o link de ANTES"
    # os preços da Recomendada são os do AJUSTE, no banco (nunca os de antes)
    resumo = m.banco.run(run_aj["id"])["result_payload"]["resumo"]
    rec = next(o for o in resumo["opcoes"] if o["id"] == "recomendada")
    do_ajuste = {round(float(o["premio_total"]), 2) for o in m.banco.linhas("multicalculo_ofertas")
                 if o["calculo_id"] == aj["id"]}
    assert round(float(rec["a_vista"]), 2) in do_ajuste, (rec, sorted(do_ajuste)[:5])
    # e a página que o novo link SERVE é a do recálculo; a de antes continua abrindo com os preços de antes
    assert _servido(m, url) and _servido(m, c["url"])


def test_b1_o_recalculo_responde_com_a_tabela_e_o_link_do_ajuste(fio):
    guarda_o_recalculo(fio)


def test_mutacao_b1_a_comparacao_ignora_o_ajuste_o_guarda_fica_vermelho(fio, monkeypatch):
    from app.services.multicalculo import comparacao as CMP

    monkeypatch.setattr(CMP, "estados_do_recalculo", lambda estados, _id: [dict(e) for e in estados])
    with pytest.raises(AssertionError):
        guarda_o_recalculo(fio)


# -- B4 · preparar e disparar no MESMO turno (o modelo encadeia) não calcula ------------------------------------------
def guarda_o_mesmo_turno(m: Fio) -> None:
    a = m.corretora_com_marca(MARCA_A, "#1D5579")
    uid, _ = m.pessoa(a, com_agger=True)
    conversa, sess = m.conversa(a, uid)
    m.falou(conversa, FRASE)                          # a ÚNICA fala do corretor: o pedido
    tools = ferramentas_do_grafo(m.mp, m.db, a)
    cid = _id_da_confirmacao(turno(tools, company_id=a, user_id=uid, session_id=sess, nome="cotacao_preparar",
                                   args=dict(CONV.COMPLETOS)))
    r = turno(tools, company_id=a, user_id=uid, session_id=sess, nome="cotacao_disparar", args={"confirmacao_id": cid})
    assert "ainda NÃO calculei" in r and not m.pedidos(a), "disparou sem o 'sim' do corretor"
    # CONTROLE: o corretor responde "sim" → o MESMO id dispara (a recusa não o consumiu)
    m.falou(conversa, "sim")
    r = turno(tools, company_id=a, user_id=uid, session_id=sess, nome="cotacao_disparar", args={"confirmacao_id": cid})
    assert "Calculando nas seguradoras" in r and len(m.pedidos(a)) == 1, r


def test_b4_preparar_e_disparar_no_mesmo_turno_nao_calcula(fio):
    guarda_o_mesmo_turno(fio)


def test_mutacao_b4_o_sim_nao_e_conferido_o_guarda_fica_vermelho(fio, monkeypatch):
    monkeypatch.setattr(CONF, "confirmou_depois", lambda *a, **k: True)
    with pytest.raises(AssertionError):
        guarda_o_mesmo_turno(fio)


# -- B2 · sem apólice anexada, a página SERVIDA não tem "economia" (mutação 5 da SPEC) -------------------------------
def guarda_economia_sem_prova(m: Fio) -> None:
    c = _cotacao_pronta(m, extra={"seguradora_atual": "Seguradora X", "premio_atual_anual": "4200.00"})
    html = _servido(m, c["url"])
    assert html and 'id="h-eco"' not in html and "a menos por ano</h2>" not in html, "economia sem apólice"
    [run] = m.runs(c["a"])
    assert run["input_payload"]["situacao"] == "novo_sem_apolice" and "apolice_atual" not in run["input_payload"]
    # o que o corretor disse fica no resumo DELE (com o valor lido certo: "4200.00" é R$ 4.200,00, não 420 mil)
    assert "O cliente disse que paga hoje: Seguradora X" in c["r1"] and "4.200,00 por ano" in c["r1"], c["r1"]


def test_b2_sem_a_apolice_anexada_a_pagina_nao_tem_economia(fio):
    guarda_economia_sem_prova(fio)


def test_mutacao_5_economia_sem_prova_o_guarda_fica_vermelho(fio, monkeypatch):
    from app.services.cotacao import pedido_da_conversa as PC
    from app.services.multicalculo import proposta as P

    def antigo(d, ficha):                             # o defeito: o que o modelo escreveu vira a apólice "lida"
        return ("novo_com_apolice", {"seguradora": d["seguradora_atual"], "premio_anual": 420000.0,
                                     "origem": "documento"}, None)

    monkeypatch.setattr(PC, "seguro_atual", antigo)
    monkeypatch.setattr(P, "apolice_com_prova", lambda ap: dict(ap) if ap else None)
    with pytest.raises(AssertionError):
        guarda_economia_sem_prova(fio)


# -- RT B-3 · a aba Cotações confere o link: quem saiu da corretora · link vencido -----------------------------------
NUMERO_DO_CORRETOR = "+5511977776666"


def guarda_a_aba_confere_o_link(m: Fio) -> None:
    c = _cotacao_pronta(m, extra={"telefone": "(11) 98888-7777"}, whatsapp=NUMERO_DO_CORRETOR)
    a, pid, url = c["a"], c["pedido"]["id"], c["url"]
    assert NUMERO_DO_CORRETOR[1:] in _servido(m, url), "a página não aponta para quem cotou (o controle)"
    api = m.api()
    # CONTROLE: nada mudou → o MESMO link
    r = api.post(f"/api/cotacoes/{pid}/apresentacao", json={"company_id": a, "user_id": c["uid"]}, headers=api.cab)
    assert r.status_code == 200 and r.json()["url"] == url, r.text
    # ① quem cotou SAIU da corretora: o gestor clica "Enviar" → link NOVO, que não aponta para o número dele
    for v in m.banco.linhas("company_members"):
        if v.get("user_id") == c["uid"] and v.get("company_id") == a:
            v["status"] = "inactive"
    chefe, _ = m.pessoa(a)
    r = api.post(f"/api/cotacoes/{pid}/envio", json={"company_id": a, "user_id": chefe}, headers=api.cab)
    assert r.status_code == 200, r.text
    novo = r.json()["link"]
    assert novo != url and NUMERO_DO_CORRETOR[1:] not in _servido(m, novo), "o link ainda manda a quem saiu"
    assert novo in r.json()["texto"] and novo.rsplit("/r/", 1)[1] in (r.json().get("wa_me_url") or "")
    # ② o link VENCEU: o "Ver apresentação" devolve um link que ABRE
    from datetime import datetime, timedelta, timezone

    for sh in m.banco.linhas("artifact_shares"):
        if novo.endswith(sh.get("token") or "#"):
            sh["expires_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    r = api.post(f"/api/cotacoes/{pid}/apresentacao", json={"company_id": a, "user_id": chefe}, headers=api.cab)
    assert r.status_code == 200 and r.json()["url"] != novo and _servido(m, r.json()["url"]), r.text


def test_rt_b3_a_aba_nunca_entrega_o_link_de_quem_saiu_nem_o_vencido(fio):
    guarda_a_aba_confere_o_link(fio)


def test_mutacao_rt_b3_a_aba_devolve_o_link_do_run_o_guarda_fica_vermelho(fio, monkeypatch):
    from app.api import cotacoes as API

    async def antiga(db, cid, pid, pedido):           # o defeito: o link guardado no run, para sempre
        run = API.runs_por_pedido(db, cid, pedido_id=pid).get(pid)
        info = API.do_run(run)
        return {"url": info["url"], "token": info.get("token"), "modelo": info.get("modelo"),
                "mensagem": info.get("mensagem")}

    monkeypatch.setattr(API, "apresentacao", antiga)
    with pytest.raises(AssertionError):
        guarda_a_aba_confere_o_link(fio)
