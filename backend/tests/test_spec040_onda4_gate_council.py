# -*- coding: utf-8 -*-
"""SPEC-040 Onda 4 - Gate nunca-regredir + Conselho de Agentes + Regressao.

Cobre: checks deterministicos do gate (PII reprova sempre), juiz que so aprova
candidato >= atual, flip versionado ativo->retired, rollback de 1 chamada,
Conselho DESLIGADO por default (zero custo) e ligado com membros sem chave
pulados + sintese do lider, sentinela de regressao (drop dispara alerta,
estavel nao), fiacao no scheduler/heartbeat/admin. Standalone (stubs).
"""

import asyncio
import importlib.util
import json
import os
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS = FAIL = 0
FAILURES = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


def _load(dotted, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(dotted, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


class _Result:
    def __init__(self, data=None):
        self.data = data or []


class _Table:
    def __init__(self, store, name):
        self.store, self.name = store, name
        self._mode = None
        self._payload = None
        self._eq = []
        self._gte = []
        self._order = None
        self._desc = True
        self._limit = None

    def select(self, *_a, **_k): self._mode = "select"; return self
    def insert(self, payload): self._mode = "insert"; self._payload = payload; return self
    def update(self, payload): self._mode = "update"; self._payload = payload; return self
    def eq(self, col, val): self._eq.append((col, val)); return self
    def gte(self, col, val): self._gte.append((col, val)); return self

    def order(self, col, desc=True):
        self._order, self._desc = col, desc
        return self

    def limit(self, n): self._limit = n; return self

    def _rows(self):
        rows = list(self.store.get(self.name, []))
        for col, val in self._eq:
            rows = [r for r in rows if str(r.get(col)) == str(val)]
        for col, val in self._gte:
            rows = [r for r in rows if str(r.get(col) or "") >= str(val)]
        if self._order:
            rows.sort(key=lambda r: str(r.get(self._order) or ""), reverse=self._desc)
        if self._limit:
            rows = rows[: self._limit]
        return rows

    def execute(self):
        self.store.setdefault(self.name, [])
        if self._mode == "insert":
            row = dict(self._payload)
            row.setdefault("id", f"{self.name}-{len(self.store[self.name]) + 1}")
            self.store[self.name].append(row)
            return _Result([row])
        if self._mode == "update":
            hit = self._rows()
            for r in hit:
                r.update(self._payload)
            return _Result(hit)
        return _Result(self._rows())


class _Supabase:
    def __init__(self, store):
        self.client = self
        self._store = store

    def table(self, name):
        return _Table(self._store, name)


class _Redis:
    def __init__(self):
        self.kv = {}

    async def set(self, key, val, ex=None): self.kv[key] = val
    async def get(self, key): return self.kv.get(key)


def _bootstrap():
    store, redis = {}, _Redis()
    sent_alerts = []
    for name in ("app", "app.core", "app.services", "app.services.atlas",
                 "app.factories", "langchain_core"):
        m = sys.modules.setdefault(name, types.ModuleType(name))
        m.__path__ = []

    db = types.ModuleType("app.core.database")
    db.get_supabase_client = lambda: _Supabase(store)
    sys.modules["app.core.database"] = db

    red = types.ModuleType("app.core.redis")

    async def _get_redis():
        return redis

    red.get_async_redis_client = _get_redis
    sys.modules["app.core.redis"] = red

    utils = types.ModuleType("app.core.utils")

    def _key_for(provider, model=None):
        if provider in ("openai", "anthropic"):
            return "key"
        return None  # kimi/grok sem chave: membro pulado

    utils.get_api_key_for_provider = _key_for
    sys.modules["app.core.utils"] = utils

    lcm = types.ModuleType("langchain_core.messages")

    class _Msg:
        def __init__(self, content):
            self.content = content

    lcm.SystemMessage = _Msg
    lcm.HumanMessage = _Msg
    sys.modules["langchain_core.messages"] = lcm

    lf = types.ModuleType("app.factories.llm_factory")

    # ⚠️ ATUALIZADO EM 23/09/2026 — SPEC-116 F3b (CLAUDE.md §9.3). O conselho e o
    # juiz passaram a pedir PAPEL à fábrica (`resolver_para` + `create_llm(papel=…,
    # modelo_resolvido=…)`). O dublê fala o contrato NOVO e resolve pelo CATÁLOGO
    # REAL (o snapshot): membro fora do catálogo é PULADO — a lição "membro sem
    # chave/provedor não quebra o conselho" migra para "membro não governado é
    # pulado, nunca vira outro modelo".
    _snap = json.loads((ROOT / "app" / "factories" / "modelos_snapshot.json")
                       .read_text(encoding="utf-8"))

    class LLMFactory:
        calls = []
        judge_response = {"nota_candidato": 88, "nota_atual": 75, "veredito": "aprovar",
                          "riscos": [], "melhorias": []}

        @staticmethod
        def resolver_para(company_config, agent_data, *, papel=None, classe_de_dado=None):
            rota = _snap["papeis"].get(papel or "")
            if rota:
                return types.SimpleNamespace(provider=rota["provider"],
                                             model=rota["modelo_primario"], papel=papel)
            prov, modelo = (agent_data or {}).get("llm_provider"), (agent_data or {}).get("llm_model")
            linha = _snap["catalogo"].get(modelo or "")
            if not linha or linha.get("provider") != prov or linha.get("lifecycle") not in (
                    "APPROVED", "CANDIDATE", "DEPRECATED"):
                raise ValueError(f"fora do catalogo: {prov}:{modelo}")
            return types.SimpleNamespace(provider=prov, model=modelo, papel=papel)

        @staticmethod
        def create_llm(company_config, agent_data, api_key=None, company_id=None, agent_id=None,
                       service_type=None, *, papel=None, modelo_resolvido=None, **_kw):
            r = modelo_resolvido or LLMFactory.resolver_para(company_config, agent_data, papel=papel)
            model = r.model

            class _LLM:
                async def ainvoke(self, msgs):
                    system, user = msgs[0].content, msgs[1].content
                    LLMFactory.calls.append({"model": model, "system": system[:60]})
                    if "juiz de playbooks" in system:
                        return types.SimpleNamespace(
                            content=json.dumps(LLMFactory.judge_response))
                    if "membro do conselho" in system:
                        return types.SimpleNamespace(
                            content="VEREDITO: aprovar\nRISCOS: nenhum\nSUGESTAO: seguir")
                    if "lider do conselho" in system or "líder do conselho" in system:
                        return types.SimpleNamespace(content=json.dumps(
                            {"veredito": "aprovar", "consenso": True,
                             "justificativa": "pareceres alinhados", "ajustes_sugeridos": []}))
                    return types.SimpleNamespace(content="{}")

            return _LLM()

    lf.LLMFactory = LLMFactory
    sys.modules["app.factories.llm_factory"] = lf

    # alerta (regressao) — stubs do canal do Vigia
    dr = types.ModuleType("app.services.dispatch_router")

    async def _support_contact(company_id):
        return "120363@g.us"

    dr._support_contact = _support_contact

    # 🔴 SPEC-EXTRA-001.3: a porta única resolve o destino pelo resolvedor
    # CANÔNICO (o mesmo que recusa destino compartilhado entre corretoras), e
    # não mais por `_support_contact` direto. O dublê devolve o mesmo contato.
    async def _resolver_destino_de_suporte(company_id):
        return {"destino": await _support_contact(company_id), "fonte": "duble",
                "recusa": None}

    dr.resolver_destino_de_suporte = _resolver_destino_de_suporte
    sys.modules["app.services.dispatch_router"] = dr

    # E a contagem em `platform_sends` — o alerta ao grupo passou a ser contado.
    po = types.ModuleType("app.services.platform_outbound")

    async def _record_platform_send(company_id, phone, kind, summary):
        store.setdefault("platform_sends", []).append(
            {"company_id": company_id, "kind": kind})

    po.record_platform_send = _record_platform_send
    sys.modules["app.services.platform_outbound"] = po

    integ = types.ModuleType("app.services.integration_service")

    class _IS:
        def get_platform_whatsapp_integration(self, company_id):
            return {"id": "i1"}

    integ.get_integration_service = lambda: _IS()
    sys.modules["app.services.integration_service"] = integ

    was = types.ModuleType("app.services.whatsapp_service")

    class _WA:
        # ⚠️ `bloco_unico` ACRESCENTADO EM 16/09/2026 — SPEC-EXTRA-001.3. O alerta
        # de qualidade passou a sair pela PORTA ÚNICA do grupo, que manda
        # `bloco_unico=True` (o que vai ao grupo é DOCUMENTO, não conversa). Um
        # dublê que trave na assinatura transforma evolução de contrato em falso
        # vermelho — e a afirmação deste guarda ("o alerta CHEGA ao canal de
        # suporte") continua exatamente a mesma.
        def send_message(self, contact, text, integration, *, bloco_unico=False):
            sent_alerts.append({"contact": contact, "text": text,
                                "bloco_unico": bloco_unico})

    was.get_whatsapp_service = lambda: _WA()
    sys.modules["app.services.whatsapp_service"] = was

    act = types.ModuleType("app.services.activity_log")

    async def _log(company_id, category, title, detail=""):
        store.setdefault("agent_activities", []).append(
            {"company_id": company_id, "category": category, "title": title})

    act.log_activity = _log
    sys.modules["app.services.activity_log"] = act

    _load("app.core.heartbeat", "app/core/heartbeat.py")
    _load("app.services.atlas.templater", "app/services/atlas/templater.py")
    dist_stub = types.ModuleType("app.services.attendance_distiller")
    dist_stub._provider_model = lambda strong=False: ("anthropic", "claude-opus-4-8" if strong else "claude-sonnet-5")
    dist_stub._load_group_summaries_sync = lambda ramo, servico, limit=30: [
        {"resumo_conduta": ["acolheu", "coletou"], "score": 85}]
    sys.modules["app.services.attendance_distiller"] = dist_stub

    # 🔴 SPEC-EXTRA-001.3: o alerta de qualidade sai pela PORTA ÚNICA do grupo.
    # Ela é carregada de verdade (não dublada) porque é ELA que este guarda
    # precisa exercitar: sem isto o `import` falha e o `except` do sentinela
    # transforma "a porta não existe" em "o alerta falhou" — que é o mesmo
    # silêncio que a SPEC-040 existe para impedir.
    _load("app.services.o_fim_do_atendimento", "app/services/o_fim_do_atendimento.py")
    _load("app.services.o_grupo_so_o_que_importa",
          "app/services/o_grupo_so_o_que_importa.py")

    council = _load("app.services.agent_council", "app/services/agent_council.py")
    gate = _load("app.services.playbook_gate", "app/services/playbook_gate.py")
    regr = _load("app.services.regression_sentinel", "app/services/regression_sentinel.py")
    return council, gate, regr, store, redis, lf.LLMFactory, sent_alerts


def run():
    print("== SPEC-040 Onda 4 - Gate + Conselho + Regressao ==\n")
    council, gate, regr, store, redis, factory, sent_alerts = _bootstrap()
    heartbeat = sys.modules["app.core.heartbeat"]

    # ---------- Conselho ----------
    os.environ.pop("COUNCIL_ENABLED", None)
    r0 = asyncio.run(council.convene_council("teste?", "ctx"))
    check("conselho DESLIGADO por default (zero custo)",
          r0.get("enabled") is False and len(factory.calls) == 0, r0)
    check("agente conselho na Central", "conselho" in [t[0] for t in heartbeat.AGENT_TASKS])

    os.environ["COUNCIL_ENABLED"] = "1"
    r1 = asyncio.run(council.convene_council("Ativar playbook guincho?", "contexto"))
    ok_members = [o for o in r1.get("opinions", []) if o.get("ok")]
    skipped = [o for o in r1.get("opinions", []) if not o.get("ok")]
    check("conselho ligado: membros GOVERNADOS pelo catalogo opinam",
          [o.get("member") for o in ok_members] == ["anthropic:claude-opus-5"],
          [o.get("member") for o in ok_members])
    check("membros fora do catalogo (gpt-5.5/kimi/grok) pulados sem quebrar",
          sorted(o.get("member") for o in skipped)
          == ["moonshot:kimi-k3", "openai:gpt-5.5", "xai:grok-4.5"],
          [o.get("member") for o in skipped])
    check("nenhum membro virou o mini (SPEC-116)",
          "gpt-4o-mini" not in [c["model"] for c in factory.calls], factory.calls)
    check("lider consolida em JSON", (r1.get("synthesis") or {}).get("veredito") == "aprovar", r1.get("synthesis"))
    os.environ.pop("COUNCIL_ENABLED", None)

    # ---------- Gate: checks deterministicos ----------
    bad_pii = {"ficha_coleta": [{"campo": "x", "como_pedir": "y"}],
               "frases_exemplo": ["Confirma o CPF 123.456.789-00?"]}
    probs = gate.deterministic_checks(bad_pii)
    check("gate: PII reprova sempre", "pii_detectada" in probs, probs)
    check("gate: ficha vazia reprova", "ficha_coleta_vazia" in gate.deterministic_checks({"a": 1}))

    # ---------- Gate: ativacao com juiz ----------
    good = {"objetivo": "guincho", "acolhimento": "Sinto muito!",
            "ficha_coleta": [{"campo": "endereco", "como_pedir": "Onde o carro esta?",
                              "ja_temos_na_apolice": False}],
            "frases_exemplo": ["Ja aciono para voce!"]}
    store["conduct_playbooks"] = [
        {"id": "pb1", "ramo": "auto", "servico": "guincho", "version": 1,
         "status": "active", "content": good},
        {"id": "pb2", "ramo": "auto", "servico": "guincho", "version": 2,
         "status": "draft", "content": good},
    ]
    res = asyncio.run(gate.activate_playbook("pb2"))
    pb1 = next(p for p in store["conduct_playbooks"] if p["id"] == "pb1")
    pb2 = next(p for p in store["conduct_playbooks"] if p["id"] == "pb2")
    check("gate aprova candidato melhor (88 vs 75)", res.get("ok") is True, res)
    check("flip versionado: atual vira retired, draft vira active",
          pb1["status"] == "retired" and pb2["status"] == "active",
          [(p["id"], p["status"]) for p in store["conduct_playbooks"]])

    # ---------- Gate: NUNCA regredir ----------
    store["conduct_playbooks"].append(
        {"id": "pb3", "ramo": "auto", "servico": "guincho", "version": 3,
         "status": "draft", "content": good})
    factory.judge_response = {"nota_candidato": 60, "nota_atual": 88, "veredito": "aprovar",
                              "riscos": ["cobre menos casos"], "melhorias": []}
    res3 = asyncio.run(gate.activate_playbook("pb3"))
    pb3 = next(p for p in store["conduct_playbooks"] if p["id"] == "pb3")
    check("gate BLOQUEIA candidato pior (60 < 88) mesmo com veredito aprovar",
          res3.get("ok") is False and pb3["status"] == "draft", res3)

    # ---------- Rollback ----------
    rb = asyncio.run(gate.rollback_playbook("auto", "guincho"))
    pb1 = next(p for p in store["conduct_playbooks"] if p["id"] == "pb1")
    pb2 = next(p for p in store["conduct_playbooks"] if p["id"] == "pb2")
    check("rollback reativa a versao anterior",
          rb.get("ok") is True and pb1["status"] == "active" and pb2["status"] == "retired", rb)

    # ---------- Sentinela de Regressao ----------
    now = datetime.now(timezone.utc)
    rows = []
    for i in range(6):  # baseline forte (dias anteriores)
        rows.append({"company_id": "c1", "score": 90, "flags": [],
                     "created_at": (now - timedelta(days=3, hours=i)).isoformat()})
    for i in range(6):  # ultimas 24h em queda
        rows.append({"company_id": "c1", "score": 60, "flags": ["repetiu_mensagem"],
                     "created_at": (now - timedelta(hours=i + 1)).isoformat()})
    findings = regr.analyze_regressions(rows, now, min_samples=5, drop_points=10)
    check("regressao detectada (90 -> 60)", len(findings) == 1
          and findings[0]["drop"] >= 29, findings)
    check("flags dominantes no achado", findings[0]["top_flags"] == ["repetiu_mensagem"])

    stable = [dict(r, score=88) for r in rows]
    check("estavel: sem alarme falso",
          regr.analyze_regressions(stable, now, 5, 10) == [])

    store["conversation_scorecards"] = rows
    n = asyncio.run(regr.check_regression())
    check("check dispara alerta no canal de suporte", n == 1 and len(sent_alerts) == 1
          and "QUALIDADE" in sent_alerts[0]["text"], sent_alerts)
    n2 = asyncio.run(regr.check_regression())
    check("marcador diario: 2a rodada nao repete", n2 == 0)

    # ---------- fiacao ----------
    sched_src = (ROOT / "app/tasks/buffer_processor.py").read_text(encoding="utf-8")
    check("scheduler: sentinela de regressao agendada", "regression_sentinel_check" in sched_src)
    admin_src = (ROOT / "app/api/admin_atlas.py").read_text(encoding="utf-8")
    check("admin: activate/rollback/conselho expostos",
          "/activate" in admin_src and "playbooks/rollback" in admin_src
          and "/conselho/convene" in admin_src and "/conselho/status" in admin_src)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n_, d in FAILURES:
            print(f"  - {n_}: {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
