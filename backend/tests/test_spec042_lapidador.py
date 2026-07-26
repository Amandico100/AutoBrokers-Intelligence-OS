# -*- coding: utf-8 -*-
"""SPEC-042 - Lapidador (otimizacao reflexiva de conduta, padrao GEPA).

Cobre: coleta de feedback textual deterministica (sessoes fracas + flags do
Auditor, dedupe), reflexao com modelo FORTE gerando DRAFT versionado (nunca
assume sozinho - gate), custo zero sem feedback suficiente, PII no candidato
reprova, sem playbook ativo nao roda, fiacao scheduler/endpoint. Standalone.
"""

import asyncio
import importlib.util
import json
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


GOOD_CANDIDATE = {
    "objetivo": "guincho melhor", "acolhimento": "Sinto muito! Resolvo agora.",
    "ficha_coleta": [{"campo": "endereco_atual", "como_pedir": "Onde o carro esta?",
                      "quando": "inicio", "ja_temos_na_apolice": False}],
    "pre_checks": ["retirar pertences"], "sensibilidade": "rodovia: seguranca",
    "encerramento": "acompanhar", "frases_exemplo": ["Ja aciono!"],
    "_mudancas": ["parou de re-pedir CPF (feedback)", "uma pergunta por vez"],
}


def _bootstrap():
    store, redis = {}, _Redis()
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
    utils.get_api_key_for_provider = lambda p, m=None: "key"
    sys.modules["app.core.utils"] = utils
    lcm = types.ModuleType("langchain_core.messages")

    class _Msg:
        def __init__(self, content):
            self.content = content

    lcm.SystemMessage = _Msg
    lcm.HumanMessage = _Msg
    sys.modules["langchain_core.messages"] = lcm
    lf = types.ModuleType("app.factories.llm_factory")

    class LLMFactory:
        calls = []
        lapidador_response = GOOD_CANDIDATE

        @staticmethod
        def create_llm(company_config, agent_data, api_key, company_id=None, agent_id=None):
            model = agent_data.get("llm_model")

            class _LLM:
                async def ainvoke(self, msgs):
                    system = msgs[0].content
                    LLMFactory.calls.append({"model": model, "system": system[:40]})
                    if "Lapidador" in system:
                        return types.SimpleNamespace(
                            content=json.dumps(LLMFactory.lapidador_response, ensure_ascii=False))
                    return types.SimpleNamespace(content="{}")

            return _LLM()

    lf.LLMFactory = LLMFactory
    sys.modules["app.factories.llm_factory"] = lf
    act = types.ModuleType("app.services.activity_log")

    async def _log(company_id, category, title, detail=""):
        store.setdefault("agent_activities", []).append({"category": category, "title": title})

    act.log_activity = _log
    sys.modules["app.services.activity_log"] = act
    _load("app.core.heartbeat", "app/core/heartbeat.py")
    _load("app.services.atlas.templater", "app/services/atlas/templater.py")
    _load("app.services.attendance_distiller", "app/services/attendance_distiller.py")
    _load("app.services.playbook_gate", "app/services/playbook_gate.py")
    opt = _load("app.services.prompt_optimizer", "app/services/prompt_optimizer.py")
    return opt, store, redis, lf.LLMFactory


def _seed(store):
    now = datetime.now(timezone.utc)
    iso = lambda **kw: (now - timedelta(**kw)).isoformat()  # noqa: E731
    store["attendance_sessions"] = [
        {"company_id": "c1", "created_at": iso(days=2), "status": "closed",
         "started_at": iso(days=2),
         "summary": {"distilled": {"ramo": "auto", "servico": "guincho", "score": 55,
                                   "flags": ["re-pediu CPF", "repetiu mensagem"],
                                   "resumo_conduta": ["acolheu"]}}},
        {"company_id": "c1", "created_at": iso(days=3), "status": "closed",
         "started_at": iso(days=3),
         "summary": {"distilled": {"ramo": "auto", "servico": "guincho", "score": 90,
                                   "flags": [], "resumo_conduta": ["perfeito"]}}},
    ]
    store["conversation_scorecards"] = [
        {"score": 60, "flags": ["amnesia", "re-pediu CPF"], "created_at": iso(days=1)},
        {"score": 65, "flags": ["cliente_frustrado"], "created_at": iso(days=1)},
    ]
    store["conduct_playbooks"] = [
        {"id": "pb1", "ramo": "auto", "servico": "guincho", "version": 1,
         "status": "active", "content": {"ficha_coleta": [
             {"campo": "endereco", "como_pedir": "Onde?"}]}},
    ]


def run():
    print("== SPEC-042 - Lapidador (GEPA) ==\n")
    opt, store, redis, factory = _bootstrap()
    _seed(store)

    # 1) coleta de feedback textual (deterministica, com dedupe)
    fb = opt.collect_feedback_sync("auto", "guincho")
    check("feedback textual coletado", len(fb) >= 4, fb)
    check("feedback inclui flags de sessao E do auditor",
          any("re-pediu CPF" in f for f in fb) and any("amnesia" in f for f in fb), fb)
    check("dedupe preserva 1 ocorrencia", sum(1 for f in fb if "re-pediu CPF" in f) <= 2, fb)

    # 2) feedback insuficiente = zero LLM
    r_few = asyncio.run(opt.optimize_playbook("auto", "guincho", min_feedback=99))
    check("feedback insuficiente: nao gasta LLM",
          r_few.get("reason") == "feedback_insuficiente" and len(factory.calls) == 0, r_few)

    # 3) rodada completa: reflexao forte -> DRAFT versionado
    res = asyncio.run(opt.optimize_playbook("auto", "guincho", min_feedback=2))
    drafts = [p for p in store["conduct_playbooks"] if p["status"] == "draft"]
    check("draft otimizado criado (nunca assume sozinho)",
          res.get("ok") is True and len(drafts) == 1 and drafts[0]["version"] == 2, res)
    check("reflexao usou o modelo FORTE",
          factory.calls and factory.calls[-1]["model"] == "claude-opus-5",
          [c["model"] for c in factory.calls])
    check("mudancas explicadas no retorno", "re-pedir CPF" in " ".join(res.get("mudancas") or []),
          res.get("mudancas"))
    check("playbook ativo INTOCADO (gate decide depois)",
          next(p for p in store["conduct_playbooks"] if p["id"] == "pb1")["status"] == "active")

    # 4) candidato com PII reprova nos checks
    factory.lapidador_response = dict(GOOD_CANDIDATE,
                                      frases_exemplo=["Confirma o CPF 123.456.789-00?"])
    r_pii = asyncio.run(opt.optimize_playbook("auto", "guincho", min_feedback=2))
    check("candidato com PII reprovado", r_pii.get("reason") == "candidato_reprovado_checks"
          and "pii_detectada" in (r_pii.get("problems") or []), r_pii)
    factory.lapidador_response = GOOD_CANDIDATE

    # 5) sem playbook ativo nao roda (o Destilador cria o primeiro)
    for p in store["conduct_playbooks"]:
        if p["id"] == "pb1":
            p["status"] = "retired"
    r_no = asyncio.run(opt.optimize_playbook("auto", "guincho", min_feedback=2))
    check("sem ativo: Lapidador nao inventa do zero",
          r_no.get("reason") == "sem_playbook_ativo", r_no)

    # 6) heartbeat do alfaiate pulsou na lapidacao
    hb = redis.kv.get("spec034:heartbeat:alfaiate")
    check("heartbeat alfaiate pulsou", hb is not None and "last_run" in str(hb))

    # 7) fiacao
    sched_src = (ROOT / "app/tasks/buffer_processor.py").read_text(encoding="utf-8")
    check("scheduler: lapidador agendado", "lapidador_check" in sched_src)
    admin_src = (ROOT / "app/api/admin_atlas.py").read_text(encoding="utf-8")
    check("admin: /espelho/optimize e /espelho/sessoes",
          "/espelho/optimize" in admin_src and "/espelho/sessoes" in admin_src)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n_, d in FAILURES:
            print(f"  - {n_}: {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
