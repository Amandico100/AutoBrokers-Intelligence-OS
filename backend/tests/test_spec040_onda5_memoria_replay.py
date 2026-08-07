# -*- coding: utf-8 -*-
"""SPEC-040 Onda 5 - Memoria por agente + replay + contribuicao.

Cobre: reescrita deterministica dos blocos de memoria (zero LLM) a partir dos
dados reais, upsert idempotente por (agent_task, block_key), marcador diario,
bloco do conselho vindo do Redis, leitura agrupada, endpoints de replay com
transcript MASCARADO e contribuicao por corretora (fiacao), scheduler.
Standalone (stubs, sem pytest).
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
        self._on_conflict = None
        self._eq = []
        self._gte = []
        self._in = []
        self._order = None
        self._desc = True
        self._limit = None
        self._faixa = None

    def select(self, *_a, **_k): self._mode = "select"; return self
    def insert(self, payload): self._mode = "insert"; self._payload = payload; return self

    def upsert(self, payload, on_conflict=None, **_k):
        self._mode = "upsert"
        self._payload = payload
        self._on_conflict = on_conflict
        return self

    def eq(self, col, val): self._eq.append((col, val)); return self
    def gte(self, col, val): self._gte.append((col, val)); return self
    def in_(self, col, vals): self._in.append((col, list(vals))); return self
    def like(self, col, pat): return self

    def order(self, col, desc=True):
        self._order, self._desc = col, desc
        return self

    def limit(self, n): self._limit = n; return self

    # Paginacao — a memoria dos agentes le o acervo inteiro por paginas desde
    # 06/08/2026. 📊 O motivo: o PostgREST corta em 1.000 linhas e ignora o
    # `.limit()` pedido acima disso; o bloco "espelho de atendimento" dizia
    # "1.000 sessoes" quando eram 1.577, e a memoria do agente e a base do que
    # ele responde. `.range(a, b)` e INCLUSIVO nas duas pontas.
    def range(self, inicio, fim):
        self._faixa = (int(inicio), int(fim))
        return self

    def _rows(self):
        rows = list(self.store.get(self.name, []))
        for col, val in self._eq:
            rows = [r for r in rows if str(r.get(col)) == str(val)]
        for col, val in self._gte:
            rows = [r for r in rows if str(r.get(col) or "") >= str(val)]
        for col, vals in self._in:
            rows = [r for r in rows if r.get(col) in vals]
        if self._order:
            rows.sort(key=lambda r: str(r.get(self._order) or ""), reverse=self._desc)
        if self._faixa:
            inicio, fim = self._faixa
            rows = rows[inicio:fim + 1]
        if self._limit:
            rows = rows[: self._limit]
        return rows

    def execute(self):
        self.store.setdefault(self.name, [])
        if self._mode == "upsert" and self._on_conflict:
            keys = [k.strip() for k in self._on_conflict.split(",")]
            for r in self.store[self.name]:
                if all(r.get(k) == self._payload.get(k) for k in keys):
                    r.update(self._payload)  # upsert real: atualiza
                    return _Result([r])
        if self._mode in ("insert", "upsert"):
            row = dict(self._payload)
            row.setdefault("id", f"{self.name}-{len(self.store[self.name]) + 1}")
            self.store[self.name].append(row)
            return _Result([row])
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
    for name in ("app", "app.core", "app.services", "app.services.atlas"):
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
    _load("app.core.heartbeat", "app/core/heartbeat.py")
    # Carregado DE VERDADE, nao dublado: e o laco de paginacao que a memoria usa
    # para ler o acervo inteiro. 📊 06/08/2026 um duble com a forma que EU
    # imaginei escondeu um ImportError por 2.255 tentativas — um duble valida a
    # suposicao de quem o escreve, nao a realidade. O modulo e puro, entao
    # carregar o de verdade custa nada e prova alguma coisa.
    _load("app.leitura_completa", "app/leitura_completa.py")
    mem = _load("app.services.agent_memory", "app/services/agent_memory.py")
    return mem, store, redis


def _seed(store):
    now = datetime.now(timezone.utc)
    iso = lambda **kw: (now - timedelta(**kw)).isoformat()  # noqa: E731
    store["observed_sessions"] = [
        {"company_id": "c1", "insurer_key": "hdi", "started_at": iso(days=2), "created_at": iso(days=2)},
        {"company_id": "c1", "insurer_key": "porto", "started_at": iso(days=3), "created_at": iso(days=3)},
        {"company_id": "c2", "insurer_key": "hdi", "started_at": iso(days=1), "created_at": iso(days=1)},
    ]
    store["ura_maps"] = [
        {"insurer_key": "hdi", "ramo": "auto", "status": "observed",
         "map": {"coverage": {"nodes": 33, "pct": 40}}},
    ]
    store["route_drift"] = [
        {"insurer_key": "porto", "severity": "cosmetico", "created_at": iso(days=4)},
    ]
    store["attendance_sessions"] = [
        {"company_id": "c1", "created_at": iso(days=1),
         "summary": {"distilled": {"servico": "guincho", "score": 82}}},
        {"company_id": "c1", "created_at": iso(days=2), "summary": {}},
    ]
    store["conversation_scorecards"] = [
        {"company_id": "c1", "score": 85, "created_at": iso(days=1)},
        {"company_id": "c1", "score": 75, "created_at": iso(days=2)},
    ]
    store["broker_insights"] = [
        {"kind": "desejo", "created_at": iso(days=5)},
        {"kind": "dor", "created_at": iso(days=6)},
    ]
    store["conduct_playbooks"] = [
        {"ramo": "auto", "servico": "guincho", "status": "active", "version": 2},
        {"ramo": "auto", "servico": "guincho", "status": "retired", "version": 1},
        {"ramo": "auto", "servico": "bateria", "status": "draft", "version": 1},
    ]


def run():
    print("== SPEC-040 Onda 5 - Memoria por agente + replay ==\n")
    mem, store, redis, = _bootstrap()
    _seed(store)
    redis.kv["council:last_convening"] = json.dumps(
        {"question": "Ativar playbook?", "verdict": "aprovar", "members_ok": 2,
         "at": "2026-07-19T18:00:00+00:00"})

    n = asyncio.run(mem.rebuild_agent_memories())
    blocks = store.get("agent_memories", [])
    tasks = {b["agent_task"] for b in blocks}
    check("blocos reescritos p/ os agentes principais", n >= 8
          and {"observador", "tecelao", "sentinela_rotas", "espelho_atendimento",
               "auditor", "garimpo", "alfaiate", "conselho"} <= tasks, (n, sorted(tasks)))

    obs = next(b for b in blocks if b["agent_task"] == "observador")
    check("observador: contagens reais por seguradora",
          "3 sessões" in obs["content"] and "hdi (2)" in obs["content"], obs["content"])
    esp = next(b for b in blocks if b["agent_task"] == "espelho_atendimento")
    check("espelho: destiladas + baseline interno",
          "1 destiladas" in esp["content"] and "82" in esp["content"], esp["content"])
    alf = next(b for b in blocks if b["agent_task"] == "alfaiate")
    check("alfaiate: playbooks por status com rollback",
          "1 ativos" in alf["content"] and "rollback" in alf["content"], alf["content"])
    cons = next(b for b in blocks if b["agent_task"] == "conselho")
    check("conselho: ultima convocacao do Redis", "aprovar" in cons["content"], cons["content"])

    # idempotencia: reescrever nao duplica blocos (upsert por task+key)
    before = len(store["agent_memories"])
    asyncio.run(mem.rebuild_agent_memories())
    check("reescrita nao duplica blocos (upsert)", len(store["agent_memories"]) == before,
          (before, len(store["agent_memories"])))

    # marcador diario
    n1 = asyncio.run(mem.check_agent_memories())
    n2 = asyncio.run(mem.check_agent_memories())
    check("marcador diario: 2a rodada pula", n1 > 0 and n2 == 0, (n1, n2))

    # leitura p/ a Central
    rows = mem.load_all_memories_sync()
    check("leitura agrupavel p/ a Central", len(rows) == before and
          all(r.get("content") for r in rows))

    # fiacao: endpoints + scheduler
    admin_src = (ROOT / "app/api/admin_atlas.py").read_text(encoding="utf-8")
    check("admin: memorias da Central expostas",
          "/central/memorias" in admin_src and "memorias/rebuild" in admin_src)
    check("admin: replay de acionamento e atendimento",
          "/replay/acionamento" in admin_src and "/replay/atendimento" in admin_src)
    check("admin: replay do atendimento MASCARA o transcript",
          "templatize(str(e.get(" in admin_src.replace('"', "'"))
    check("admin: contribuicao por corretora",
          "/onboarding/contribuicao" in admin_src and "efeito rede" in admin_src)
    sched_src = (ROOT / "app/tasks/buffer_processor.py").read_text(encoding="utf-8")
    check("scheduler: memoria dos agentes agendada", "agent_memory_check" in sched_src)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n_, d in FAILURES:
            print(f"  - {n_}: {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
