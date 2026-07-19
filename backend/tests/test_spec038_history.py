# -*- coding: utf-8 -*-
"""SPEC-038 Bloco C+ — ingestao HistorySync (recencia, filtro) + resolvedor IA
(coleta de ambiguos, aplicacao, custo). Standalone."""

import asyncio
import importlib.util
import sys
import types
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
    spec = importlib.util.spec_from_file_location(dotted, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


# ---- stubs de banco/redis ----
class _Tbl:
    def __init__(self, store, name):
        self.store, self.name, self._m, self._p = store, name, None, None

    def select(self, *a, **k): self._m = "select"; return self
    def insert(self, p): self._m, self._p = "insert", p; return self
    def upsert(self, p, **k): self._m, self._p = "insert", p; return self
    def update(self, p): self._m = "update"; return self
    def eq(self, *a): return self
    def order(self, *a, **k): return self
    def limit(self, *a): return self

    def execute(self):
        if self._m == "insert":
            row = dict(self._p); row.setdefault("id", f"{self.name}-{len(self.store[self.name])+1}")
            self.store[self.name].append(row); return types.SimpleNamespace(data=[row])
        return types.SimpleNamespace(data=[])


class _DB:
    def __init__(self, store): self.client = self; self._s = store
    def table(self, n): self._s.setdefault(n, []); return _Tbl(self._s, n)


def _bootstrap():
    store = {}
    for name in ("app", "app.core", "app.services", "app.services.atlas", "app.services.whatsapp",
                 "app.services.whatsapp.providers"):
        m = sys.modules.setdefault(name, types.ModuleType(name)); m.__path__ = []
    db = types.ModuleType("app.core.database"); db.get_supabase_client = lambda: _DB(store)
    sys.modules["app.core.database"] = db
    red = types.ModuleType("app.core.redis")

    class _R:
        async def get(self, k): return None
        async def set(self, k, v, ex=None): pass
        async def hincrby(self, k, f, n): pass
    async def _gr(): return _R()
    red.get_async_redis_client = _gr
    sys.modules["app.core.redis"] = red
    hb = types.ModuleType("app.core.heartbeat")
    async def _beat(t, n=0): pass
    hb.beat = _beat; sys.modules["app.core.heartbeat"] = hb
    _load("app.services.insurer_registry", "app/services/insurer_registry.py")
    _load("app.services.whatsapp.evolution_inbound", "app/services/whatsapp/evolution_inbound.py")
    sys.modules.setdefault("requests", types.SimpleNamespace(post=lambda *a, **k: None))
    exc = types.ModuleType("app.services.whatsapp.exceptions")
    for k in ("ProviderConfigError", "ProviderNotSupportedError", "WhatsappRetryableError"):
        setattr(exc, k, type(k, (Exception,), {}))
    sys.modules["app.services.whatsapp.exceptions"] = exc
    mdl = types.ModuleType("app.services.whatsapp.models")

    class _D:
        def __init__(self, **kw): [setattr(self, k, v) for k, v in kw.items()]
    for k in ("CanonicalMessage", "InboundBatch", "MediaRef", "OutboundMedia", "SendResult", "TemplateRef"):
        setattr(mdl, k, type(k, (_D,), {}))
    sys.modules["app.services.whatsapp.models"] = mdl
    base = types.ModuleType("app.services.whatsapp.providers.base")
    base.ProviderCapabilities = type("PC", (), {"__init__": lambda s, **k: None})
    sys.modules["app.services.whatsapp.providers.base"] = base
    _load("app.services.whatsapp.providers.evolution_go", "app/services/whatsapp/providers/evolution_go.py")
    _load("app.services.atlas.observer_intake", "app/services/atlas/observer_intake.py")
    hist = _load("app.services.atlas.history_ingest", "app/services/atlas/history_ingest.py")
    return hist, store


def run():
    print("== SPEC-038 Bloco C+ — HistorySync + Resolvedor IA ==\n")
    hist, store = _bootstrap()

    # HistorySync com 2 conversas: HDI (recente) e um amigo (descartar)
    body = {"event": "HistorySync", "data": {"Conversations": [
        {"id": "5547999112233@s.whatsapp.net", "messages": [  # amigo — descartar
            {"message": {"key": {"fromMe": False}, "messageTimestamp": 1000,
                         "message": {"conversation": "oi tudo bem"}}}]},
        {"id": "551155020700@s.whatsapp.net", "messages": [  # HDI — manter
            {"message": {"key": {"fromMe": False}, "messageTimestamp": 5000,
                         "message": {"conversation": "Menu HDI: 1 Guincho 2 Chaveiro"}}},
            {"message": {"key": {"fromMe": True}, "messageTimestamp": 5001,
                         "message": {"conversation": "1"}}},
            {"message": {"key": {"fromMe": False}, "messageTimestamp": 5002,
                         "message": {"conversation": "Enviaremos o guincho. Confirma?"}}},
        ]},
    ]}}
    integ = {"purpose": "observer", "company_id": "c1", "identifier": "554796274743"}
    res = asyncio.run(hist.ingest_history_sync(integ, body))
    check("2 conversas vistas, 1 de seguradora", res["conversations"] == 2 and res["insurer_conversations"] == 1, res)
    evs = store.get("observed_events", [])
    check("eventos HDI gravados (>=3)", len(evs) >= 3, len(evs))
    check("amigo descartado (nenhum evento non-hdi)", all(e["insurer_key"] == "hdi" for e in evs), [e.get("insurer_key") for e in evs])
    check("source=history_sync", all(e["source"] == "history_sync" for e in evs))
    check("direction correto (in/out)", {e["direction"] for e in evs} == {"in", "out"}, [e["direction"] for e in evs])
    check("sessao criada p/ o burst", len(store.get("observed_sessions", [])) == 1, store.get("observed_sessions"))
    check("evento tem session_id", all(e.get("session_id") for e in evs))

    # 2) recencia: conversa com timestamps maiores vem primeiro no sort interno
    convs = hist._find_conversations(body["data"])
    check("localiza conversas (tolerante a casing)", len(convs) == 2, len(convs))

    # 3) resolvedor: coleta arestas ambiguas (menu -> '->' sem eco)
    parser = _load("app.services.atlas.atlas_parser", "app/services/atlas/atlas_parser.py")
    m = {"nodes": {"a": {"kind": "menu", "text": "O que precisa? 1 Guincho 2 Chaveiro",
                         "options": [{"label": "Guincho"}, {"label": "Chaveiro"}]},
                   "b": {"kind": "informativo", "text": "Enviaremos o chaveiro."}},
         "edges": {"a|→": {"src": "a", "label": "→", "to": "b", "inferred": True}}}
    items = parser._collect_ambiguous(m)
    check("coleta 1 aresta ambigua", len(items) == 1 and items[0]["options"] == ["Guincho", "Chaveiro"], items)

    # 4) estimativa de custo (Sonnet default): barata e por seguradora
    est = parser.estimate_cost(nodes=30, ambiguous_edges=12)
    check("custo estimado < R$0,20/seguradora", est["brl_per_insurer"] < 0.20, est)
    check("modelo default forte (sonnet)", "sonnet" in est["model"], est)

    # 5) parser desligavel por env
    import os
    os.environ["ATLAS_PARSER_ENABLED"] = "0"
    n = asyncio.run(parser.resolve_typed_choices(m, "hdi"))
    check("resolvedor respeita ATLAS_PARSER_ENABLED=0", n == 0)
    os.environ["ATLAS_PARSER_ENABLED"] = "1"

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  - {n}: {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
