# -*- coding: utf-8 -*-
"""SPEC-038 Bloco A — Observador: filtro de borda, captura dos DOIS lados,
modos observer/tap, history sync estrutura-somente. Standalone (stubs)."""

import asyncio
import importlib.util
import json
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
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(dotted, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


# ------------------------- stubs -------------------------
class _Result:
    def __init__(self, data=None):
        self.data = data or []


class _Table:
    def __init__(self, store, name):
        self.store, self.name = store, name
        self._mode = None
        self._payload = None

    def select(self, *_a, **_k): self._mode = "select"; return self
    def insert(self, payload): self._mode = "insert"; self._payload = payload; return self
    def upsert(self, payload, **_k): self._mode = "upsert"; self._payload = payload; return self
    def update(self, payload): self._mode = "update"; self._payload = payload; return self
    def eq(self, *_a): return self
    def order(self, *_a, **_k): return self
    def limit(self, *_a): return self

    def execute(self):
        if self._mode in ("insert", "upsert"):
            row = dict(self._payload)
            row.setdefault("id", f"{self.name}-{len(self.store[self.name]) + 1}")
            self.store[self.name].append(row)
            return _Result([row])
        return _Result([])  # select: sem sessão aberta


class _SupabaseClient:
    def __init__(self, store):
        self.client = self
        self._store = store

    def table(self, name):
        self._store.setdefault(name, [])
        return _Table(self._store, name)


class _Redis:
    def __init__(self):
        self.hashes = {}
        self.kv = {}

    async def hincrby(self, key, field, n):
        self.hashes.setdefault(key, {})
        self.hashes[key][field] = self.hashes[key].get(field, 0) + n

    async def set(self, key, val, ex=None): self.kv[key] = val
    async def get(self, key): return self.kv.get(key)
    async def hgetall(self, key): return self.hashes.get(key, {})


def _bootstrap():
    store, redis = {}, _Redis()
    for name in ("app", "app.core", "app.services", "app.services.whatsapp",
                 "app.services.whatsapp.providers", "app.services.atlas"):
        m = sys.modules.setdefault(name, types.ModuleType(name))
        m.__path__ = []
    # database + redis stubs
    db = types.ModuleType("app.core.database")
    db.get_supabase_client = lambda: _SupabaseClient(store)
    sys.modules["app.core.database"] = db
    red = types.ModuleType("app.core.redis")

    async def _get_redis():
        return redis

    red.get_async_redis_client = _get_redis
    sys.modules["app.core.redis"] = red
    # registry real + inbound real + conversor real (código de produção)
    _load("app.services.insurer_registry", "app/services/insurer_registry.py")
    _load("app.services.whatsapp.evolution_inbound", "app/services/whatsapp/evolution_inbound.py")
    # evolution_go depende de requests/models/exceptions — stubs mínimos
    sys.modules.setdefault("requests", types.SimpleNamespace(post=lambda *a, **k: None))
    exc = types.ModuleType("app.services.whatsapp.exceptions")
    for k in ("ProviderConfigError", "ProviderNotSupportedError", "WhatsappRetryableError"):
        setattr(exc, k, type(k, (Exception,), {}))
    sys.modules["app.services.whatsapp.exceptions"] = exc
    mdl = types.ModuleType("app.services.whatsapp.models")

    class _D:  # noqa: N801
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    for k in ("CanonicalMessage", "InboundBatch", "MediaRef", "OutboundMedia", "SendResult", "TemplateRef"):
        setattr(mdl, k, type(k, (_D,), {}))
    sys.modules["app.services.whatsapp.models"] = mdl
    base = types.ModuleType("app.services.whatsapp.providers.base")
    base.ProviderCapabilities = type("PC", (), {"__init__": lambda s, **k: None})
    sys.modules["app.services.whatsapp.providers.base"] = base
    _load("app.services.whatsapp.providers.evolution_go", "app/services/whatsapp/providers/evolution_go.py")
    intake = _load("app.services.atlas.observer_intake", "app/services/atlas/observer_intake.py")
    return intake, store, redis


def _msg_event(remote, text, from_me=False, mid="M1"):
    return {"event": "Message", "instanceId": "obs1",
            "data": {"Info": {"Chat": remote, "Sender": remote, "IsFromMe": from_me,
                              "ID": mid, "PushName": "X", "Timestamp": 1752900000},
                     "Message": {"conversation": text}}}


def run():
    print("== SPEC-038 Bloco A — Observador ==\n")
    intake, store, redis = _bootstrap()
    integ_obs = {"purpose": "observer", "company_id": "c1", "identifier": "554796274743"}
    integ_att = {"purpose": "attendance", "company_id": "c1", "identifier": "554796274743"}
    hdi = "551155020700@s.whatsapp.net"      # registry HDI
    amigo = "5547999112233@s.whatsapp.net"   # NÃO-seguradora

    # 1) inbound de seguradora (observer) → capturado + consumido
    r1 = asyncio.run(intake.observer_tap(integ_obs, _msg_event(hdi, "Menu: Guincho / Bateria", mid="A1")))
    ev = store.get("observed_events", [])
    check("observer consome (dict)", isinstance(r1, dict))
    check("evento de seguradora capturado", len(ev) == 1 and ev[0]["insurer_key"] == "hdi", ev)
    check("direction=in", ev[0]["direction"] == "in")

    # 2) fromMe (a atendente digitando) → direction=out + raw_out
    asyncio.run(intake.observer_tap(integ_obs, _msg_event(hdi, "2", from_me=True, mid="A2")))
    ev = store["observed_events"]
    check("fromMe capturado direction=out", len(ev) == 2 and ev[1]["direction"] == "out", [e.get("direction") for e in ev])
    check("raw_out preservado no fromMe", isinstance((ev[1].get("interactive") or {}).get("raw_out"), dict))

    # 3) FILTRO DE BORDA: amigo → NADA armazenado + contador
    r3 = asyncio.run(intake.observer_tap(integ_obs, _msg_event(amigo, "oi mano", mid="A3")))
    check("amigo descartado (nada armazenado)", len(store["observed_events"]) == 2)
    drops = redis.hashes.get("atlas:drops:554796274743", {})
    check("contador de descarte non_insurer", drops.get("non_insurer", 0) >= 1, drops)
    check("observer ainda consome no descarte", isinstance(r3, dict))

    # 4) grupo → descartado
    asyncio.run(intake.observer_tap(integ_obs, _msg_event("12036@g.us", "grupo", mid="A4")))
    check("grupo descartado", len(store["observed_events"]) == 2)

    # 5) modo TAP (attendance): captura seguradora e devolve None (pipeline segue)
    r5 = asyncio.run(intake.observer_tap(integ_att, _msg_event(hdi, "Digite o CPF", mid="A5")))
    check("tap captura e devolve None", r5 is None and len(store["observed_events"]) == 3)

    # 6) tap de NÃO-seguradora → None e nada armazenado (Even segue normal)
    r6 = asyncio.run(intake.observer_tap(integ_att, _msg_event(amigo, "cliente real", mid="A6")))
    check("tap não-seguradora: None + não armazena", r6 is None and len(store["observed_events"]) == 3)

    # 7) HISTORY_SYNC: estrutura-somente + consome sempre
    hs = {"event": "HistorySync", "data": {"Conversations": [1, 2, 3], "Progress": 40}}
    r7 = asyncio.run(intake.observer_tap(integ_att, hs))
    check("history sync consumido mesmo no tap", isinstance(r7, dict))
    struct = redis.kv.get("atlas:history_sync:last_structure")
    check("history sync: só estrutura gravada", struct and "Conversations" in struct and "3" in struct, struct)
    check("history sync: conteúdo NÃO armazenado", len(store["observed_events"]) == 3)

    # 8) dedupe: mesmo message_id não duplica (upsert em memória: aceita, mas
    #    o índice único do banco protege — aqui validamos que message_id vai no registro)
    check("message_id presente p/ dedupe", store["observed_events"][0].get("message_id") == "A1")

    # 9) allowlist inclui variantes com/sem 9 e envs INSURER_CONTACT_*
    import os
    os.environ["INSURER_CONTACT_TESTE_ASSISTENCIA"] = "5511911112222"
    allow = intake.insurer_allowlist()
    check("env INSURER_CONTACT_* entra na allowlist", "5511911112222" in allow and "551111112222" in allow)
    check("registry HDI na allowlist", "551155020700" in allow and allow["551155020700"] == "hdi")

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  - {n}: {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
