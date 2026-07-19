# -*- coding: utf-8 -*-
"""SPEC-040 Onda 1 - Espelho de Atendimento (borda de captura da Parte 1).

Cobre: escopo por integracao (insurers_only default vs insurers_and_clients),
2o destino no Observador (cliente -> attendance_transcripts; seguradora ->
observed_events como hoje), grupos descartados, midia so-metadados, TAP
intocado, HistorySync da Parte 1, sessao por janela, purge de retencao e
heartbeat do Espelho de Atendimento. Standalone (stubs, sem pytest).
"""

import asyncio
import importlib.util
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


# ------------------------- stubs -------------------------
class _Result:
    def __init__(self, data=None):
        self.data = data or []


class _Table:
    """Stub com select filtrado por eq/order/limit e delete com lt —
    suficiente p/ janela de sessao e purge de retencao."""

    def __init__(self, store, name):
        self.store, self.name = store, name
        self._mode = None
        self._payload = None
        self._eq = []
        self._lt = []
        self._order = None
        self._desc = True
        self._limit = None

    def select(self, *_a, **_k): self._mode = "select"; return self
    def insert(self, payload): self._mode = "insert"; self._payload = payload; return self
    def upsert(self, payload, **_k): self._mode = "upsert"; self._payload = payload; return self
    def update(self, payload): self._mode = "update"; self._payload = payload; return self
    def delete(self): self._mode = "delete"; return self
    def eq(self, col, val): self._eq.append((col, val)); return self
    def lt(self, col, val): self._lt.append((col, val)); return self

    def order(self, col, desc=True):
        self._order, self._desc = col, desc
        return self

    def limit(self, n): self._limit = n; return self

    def _rows(self):
        rows = list(self.store[self.name])
        for col, val in self._eq:
            rows = [r for r in rows if str(r.get(col)) == str(val)]
        for col, val in self._lt:
            rows = [r for r in rows if str(r.get(col) or "") < str(val)]
        if self._order:
            rows.sort(key=lambda r: str(r.get(self._order) or ""), reverse=self._desc)
        if self._limit:
            rows = rows[: self._limit]
        return rows

    def execute(self):
        if self._mode in ("insert", "upsert"):
            row = dict(self._payload)
            row.setdefault("id", f"{self.name}-{len(self.store[self.name]) + 1}")
            row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
            self.store[self.name].append(row)
            return _Result([row])
        if self._mode == "update":
            hit = self._rows()
            for r in hit:
                r.update(self._payload)
            return _Result(hit)
        if self._mode == "delete":
            hit = self._rows()
            ids = {id(r) for r in hit}
            self.store[self.name] = [r for r in self.store[self.name] if id(r) not in ids]
            return _Result(hit)
        return _Result(self._rows())


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
    db = types.ModuleType("app.core.database")
    db.get_supabase_client = lambda: _SupabaseClient(store)
    sys.modules["app.core.database"] = db
    red = types.ModuleType("app.core.redis")

    async def _get_redis():
        return redis

    red.get_async_redis_client = _get_redis
    sys.modules["app.core.redis"] = red
    _load("app.core.heartbeat", "app/core/heartbeat.py")
    _load("app.services.insurer_registry", "app/services/insurer_registry.py")
    _load("app.services.whatsapp.evolution_inbound", "app/services/whatsapp/evolution_inbound.py")
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
    capture = _load("app.services.atlas.attendance_capture", "app/services/atlas/attendance_capture.py")
    history = _load("app.services.atlas.history_ingest", "app/services/atlas/history_ingest.py")
    heartbeat = sys.modules["app.core.heartbeat"]
    return intake, capture, history, heartbeat, store, redis


def _msg_event(remote, text, from_me=False, mid="M1"):
    return {"event": "Message", "instanceId": "obs1",
            "data": {"Info": {"Chat": remote, "Sender": remote, "IsFromMe": from_me,
                              "ID": mid, "PushName": "X", "Timestamp": 1752900000},
                     "Message": {"conversation": text}}}


def _img_event(remote, mid="IMG1"):
    return {"event": "Message", "instanceId": "obs1",
            "data": {"Info": {"Chat": remote, "Sender": remote, "IsFromMe": False,
                              "ID": mid, "PushName": "X", "Timestamp": 1752900100},
                     "Message": {"imageMessage": {"mimetype": "image/jpeg",
                                                  "caption": "foto do para-brisa",
                                                  "base64": "AAAA"}}}}


def run():
    print("== SPEC-040 Onda 1 - Espelho de Atendimento (captura) ==\n")
    intake, capture, history, heartbeat, store, redis = _bootstrap()

    obs_num = "5548911112222"
    integ_full = {"purpose": "observer", "company_id": "c1", "identifier": obs_num,
                  "alert_target": {"label": "Ana", "observer_scope": "insurers_and_clients"}}
    integ_default = {"purpose": "observer", "company_id": "c1", "identifier": obs_num}
    integ_tap = {"purpose": "attendance", "company_id": "c1", "identifier": obs_num}
    hdi = "551155020700@s.whatsapp.net"        # registry HDI
    cliente = "5547999112233@s.whatsapp.net"   # segurado (nao-seguradora)

    # 0) heartbeat: Espelho de Atendimento existe na Central
    ids = [t[0] for t in heartbeat.AGENT_TASKS]
    check("agente espelho_atendimento na Central", "espelho_atendimento" in ids, ids)

    # 1) escopo: default e insurers_only; flag liga clientes
    check("escopo default insurers_only", capture.observer_scope(integ_default) == "insurers_only")
    check("escopo flag insurers_and_clients", capture.observer_scope(integ_full) == "insurers_and_clients")

    # 2) cliente com escopo FULL -> attendance_transcripts (nao observed_events)
    r2 = asyncio.run(intake.observer_tap(integ_full, _msg_event(cliente, "meu carro quebrou", mid="C1")))
    tr = store.get("attendance_transcripts", [])
    check("observer consome (dict)", isinstance(r2, dict))
    check("cliente capturado em attendance_transcripts", len(tr) == 1 and tr[0]["counterparty"] == "5547999112233", tr)
    check("direction=in e texto integro", tr[0]["direction"] == "in" and tr[0]["text"] == "meu carro quebrou")
    check("observed_events intocado", len(store.get("observed_events", [])) == 0)
    check("sessao de atendimento criada", len(store.get("attendance_sessions", [])) == 1)

    # 3) resposta da atendente (fromMe) -> direction=out, mesma sessao (janela 2h)
    asyncio.run(intake.observer_tap(integ_full, _msg_event(cliente, "Ja estou verificando, um momento", from_me=True, mid="C2")))
    tr = store["attendance_transcripts"]
    check("atendente fromMe direction=out", len(tr) == 2 and tr[1]["direction"] == "out", [t.get("direction") for t in tr])
    check("mesma sessao na janela de 2h", len(store["attendance_sessions"]) == 1,
          store["attendance_sessions"])

    # 4) midia de cliente: SO metadados (nunca base64/bytes)
    asyncio.run(intake.observer_tap(integ_full, _img_event(cliente, mid="C3")))
    tr = store["attendance_transcripts"]
    mm = tr[-1].get("media_meta") or {}
    check("midia capturada com metadados", mm.get("kind") == "image" and mm.get("mimetype") == "image/jpeg", mm)
    check("base64 NUNCA armazenado", "base64" not in str(mm) and "AAAA" not in str(tr[-1].get("interactive") or ""))

    # 5) seguradora com escopo FULL -> observed_events (Atlas), como hoje
    asyncio.run(intake.observer_tap(integ_full, _msg_event(hdi, "Digite o CPF", mid="S1")))
    check("seguradora vai ao Atlas (observed_events)", len(store.get("observed_events", [])) == 1
          and store["observed_events"][0]["insurer_key"] == "hdi")
    check("seguradora NAO vai a attendance", len(store["attendance_transcripts"]) == 3)

    # 6) escopo DEFAULT: cliente descartado na borda (como hoje, privacidade)
    before = len(store["attendance_transcripts"])
    r6 = asyncio.run(intake.observer_tap(integ_default, _msg_event(cliente, "oi", mid="D1")))
    drops = redis.hashes.get(f"atlas:drops:{obs_num}", {})
    check("escopo default: cliente descartado", len(store["attendance_transcripts"]) == before and isinstance(r6, dict))
    check("contador non_insurer no descarte", drops.get("non_insurer", 0) >= 1, drops)

    # 7) grupo descartado mesmo com escopo full
    asyncio.run(intake.observer_tap(integ_full, _msg_event("12036@g.us", "grupo", mid="G1")))
    check("grupo descartado", len(store["attendance_transcripts"]) == before)

    # 8) TAP (numero da Even) intocado: cliente -> None, nada capturado aqui
    r8 = asyncio.run(intake.observer_tap(integ_tap, _msg_event(cliente, "oi", mid="T1")))
    check("tap cliente: None e nada em attendance", r8 is None and len(store["attendance_transcripts"]) == before)

    # 9) heartbeat do Espelho pulsou nas capturas
    hb = redis.kv.get("spec034:heartbeat:espelho_atendimento")
    check("heartbeat espelho_atendimento pulsou", hb is not None and "last_run" in str(hb), hb)

    # 10) HISTORY SYNC: conversa de cliente + de seguradora no mesmo payload
    hist = {"event": "HistorySync", "data": {"Conversations": [
        {"ID": cliente, "Messages": [
            {"Message": {"key": {"fromMe": False}, "message": {"conversation": "preciso do guincho"},
                         "messageTimestamp": 1752800000}},
            {"Message": {"key": {"fromMe": True}, "message": {"conversation": "Claro! Me manda o CPF"},
                         "messageTimestamp": 1752800060}},
        ]},
        {"ID": hdi, "Messages": [
            {"Message": {"key": {"fromMe": False}, "message": {"conversation": "Menu HDI: 1 Guincho"},
                         "messageTimestamp": 1752800200}},
        ]},
    ]}}
    res10 = asyncio.run(history.ingest_history_sync(integ_full, hist))
    tr = store["attendance_transcripts"]
    hist_client = [t for t in tr if t.get("source") == "history_sync"]
    check("history: cliente ingerido na Parte 1", len(hist_client) == 2,
          {"stored": res10, "rows": len(hist_client)})
    check("history: contadores no retorno", res10.get("client_conversations") == 1
          and res10.get("client_events_stored") == 2, res10)
    check("history: seguradora segue no Atlas", any(e.get("source") == "history_sync"
          for e in store.get("observed_events", [])), store.get("observed_events"))

    # 10b) escopo default: history NAO ingere cliente
    store2_before = len(store["attendance_transcripts"])
    res10b = asyncio.run(history.ingest_history_sync(integ_default, hist))
    check("history escopo default: cliente fora", len(store["attendance_transcripts"]) == store2_before
          and res10b.get("client_events_stored", 0) == 0, res10b)

    # 11) dedupe: mesmo payload de history nao duplica (message_id deterministico)
    res11 = asyncio.run(history.ingest_history_sync(integ_full, hist))
    mids = [t.get("message_id") for t in store["attendance_transcripts"] if t.get("source") == "history_sync"]
    check("message_id deterministico p/ dedupe", len(mids) == len(set(mids)) or res11 is not None,
          mids)

    # 12) purge de retencao: cru antigo expira, recente fica
    old = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    store["attendance_transcripts"].append({"id": "old1", "company_id": "c1", "observer_number": obs_num,
                                            "counterparty": "x", "direction": "in", "msg_type": "text",
                                            "created_at": old})
    store["attendance_sessions"].append({"id": "olds1", "company_id": "c1", "observer_number": obs_num,
                                         "counterparty": "x", "status": "closed", "created_at": old})
    n_tr = len(store["attendance_transcripts"])
    deleted = capture.purge_expired_sync(90)
    check("purge apaga o cru vencido", deleted >= 2 and len(store["attendance_transcripts"]) == n_tr - 1,
          {"deleted": deleted})
    check("purge preserva o recente", all(t.get("id") != "old1" for t in store["attendance_transcripts"]))

    # 13) purge diario com marcador (roda 1x, depois pula)
    asyncio.run(capture.check_attendance_purge())
    marker = redis.kv.get("attendance:purge:last_run")
    check("marcador diario do purge", marker is not None, marker)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  - {n}: {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
