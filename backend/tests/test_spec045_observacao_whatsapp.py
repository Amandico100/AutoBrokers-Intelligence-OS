# -*- coding: utf-8 -*-
"""SPEC-045 - Modo observacao, fila de cortesia e organizacao por funcao.

Cobre: attendance_observation_mode (cache + query), capture_channel_message,
client_busy/fila de cortesia/nota de contexto (platform_outbound), gate no
webhook + captura fromMe (source-check), toggle attendance-only (source-check
da store Next), blueprint v2 sem pronome/genero com abertura em variaveis e
render aninhado. Standalone (stubs, sem pytest).
"""

import asyncio
import importlib.util
import json
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT.parent
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
        self._neq = []
        self._gte = []
        self._on_conflict = None

    def select(self, *_a, **_k): self._mode = "select"; return self
    def insert(self, payload): self._mode = "insert"; self._payload = payload; return self

    def upsert(self, payload, on_conflict=None, **_k):
        self._mode = "upsert"; self._payload = payload; self._on_conflict = on_conflict
        return self

    def update(self, payload): self._mode = "update"; self._payload = payload; return self
    def eq(self, col, val): self._eq.append((col, val)); return self
    def neq(self, col, val): self._neq.append((col, val)); return self
    def gte(self, col, val): self._gte.append((col, val)); return self
    def order(self, *_a, **_k): return self
    def limit(self, *_a): return self

    def _rows(self):
        rows = list(self.store.get(self.name, []))
        for col, val in self._eq:
            rows = [r for r in rows if str(r.get(col)) == str(val)]
        for col, val in self._neq:
            rows = [r for r in rows if str(r.get(col)) != str(val)]
        for col, val in self._gte:
            rows = [r for r in rows if str(r.get(col) or "") >= str(val)]
        return rows

    def execute(self):
        self.store.setdefault(self.name, [])
        if self._mode in ("insert", "upsert"):
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
        self.lists = {}
        self.hashes = {}

    async def get(self, key): return self.kv.get(key)
    async def set(self, key, val, ex=None): self.kv[key] = val

    async def hincrby(self, key, field, n):
        self.hashes.setdefault(key, {})
        self.hashes[key][field] = self.hashes[key].get(field, 0) + n

    async def rpush(self, key, val): self.lists.setdefault(key, []).append(val)
    async def lpop(self, key):
        lst = self.lists.get(key) or []
        return lst.pop(0) if lst else None
    async def llen(self, key): return len(self.lists.get(key) or [])


def _bootstrap():
    store, redis = {}, _Redis()
    for name in ("app", "app.core", "app.services", "app.services.atlas",
                 "app.services.whatsapp", "app.services.whatsapp.providers"):
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
    _load("app.services.insurer_registry", "app/services/insurer_registry.py")
    # observer_intake real (o capture reusa o storage parametrizado dele)
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
    _load("app.services.whatsapp.evolution_inbound", "app/services/whatsapp/evolution_inbound.py")
    _load("app.services.whatsapp.providers.evolution_go", "app/services/whatsapp/providers/evolution_go.py")
    _load("app.services.atlas.observer_intake", "app/services/atlas/observer_intake.py")
    cap = _load("app.services.atlas.attendance_capture", "app/services/atlas/attendance_capture.py")

    # dispatch_router stub p/ client_busy
    dr = types.ModuleType("app.services.dispatch_router")
    dr._active = []

    async def _list(company_id):
        return dr._active

    dr.list_active_dispatches = _list
    sys.modules["app.services.dispatch_router"] = dr

    act = types.ModuleType("app.services.activity_log")
    act.logged = []

    async def _log(company_id, category, title, detail=""):
        act.logged.append({"company_id": company_id, "title": title})

    act.log_activity = _log
    sys.modules["app.services.activity_log"] = act

    integ = types.ModuleType("app.services.integration_service")

    class _IS:
        def get_platform_whatsapp_integration(self, company_id):
            return {"id": "i1"}

    integ.get_integration_service = lambda: _IS()
    sys.modules["app.services.integration_service"] = integ
    was = types.ModuleType("app.services.whatsapp_service")
    was.sent = []

    class _WA:
        def send_message(self, number, text, integration):
            was.sent.append({"to": number, "text": text})
            return True

    was.get_whatsapp_service = lambda: _WA()
    sys.modules["app.services.whatsapp_service"] = was

    po = _load("app.services.platform_outbound", "app/services/platform_outbound.py")
    return cap, po, store, redis, dr, was, act


def run():
    print("== SPEC-045 - Observacao + fila de cortesia + funcao ==\n")
    cap, po, store, redis, dr, was, act = _bootstrap()

    # ---------- 1) modo observacao ----------
    store["agents"] = [{"id": "a1", "company_id": "c1", "agent_role": "attendance", "is_active": False}]
    obs = asyncio.run(cap.attendance_observation_mode("c1"))
    check("agente OFF = modo observacao", obs is True)
    check("resultado cacheado no Redis", redis.kv.get("attendance:obsmode:c1") == "1")
    store["agents"][0]["is_active"] = True
    still = asyncio.run(cap.attendance_observation_mode("c1"))
    check("cache 60s segura o valor (hot path barato)", still is True)
    redis.kv.pop("attendance:obsmode:c1", None)
    now_on = asyncio.run(cap.attendance_observation_mode("c1"))
    check("agente ON = responde (sem observacao)", now_on is False)

    # ---------- 2) captura de canal (observacao) ----------
    ok_in = asyncio.run(cap.capture_channel_message("c1", "554796274743", "5547999112233",
                                                    "meu carro quebrou", "in", "M1"))
    ok_out = asyncio.run(cap.capture_channel_message("c1", "554796274743", "5547999112233",
                                                     "Ja estou vendo, um minuto", "out", "M2"))
    tr = store.get("attendance_transcripts", [])
    check("cliente e atendente humana capturados no cofre", ok_in and ok_out and len(tr) == 2
          and tr[0]["direction"] == "in" and tr[1]["direction"] == "out", tr)
    check("mesma sessao de atendimento", len(store.get("attendance_sessions", [])) == 1)

    # ---------- 3) fila de cortesia ----------
    now = datetime.now(timezone.utc)
    store["conversations"] = [{"id": "cv1", "company_id": "c1", "channel": "whatsapp",
                               "user_phone": "5547999112233", "status": "active",
                               "last_message_at": now.isoformat()}]
    busy = asyncio.run(po.client_busy("c1", "5547999112233"))
    check("cliente em conversa recente = ocupado", busy == "conversa", busy)
    res = asyncio.run(po.send_to_client_guarded("c1", "5547999112233", "Sua parcela vence amanha",
                                                "billing", "cobranca da parcela 3"))
    check("envio ADIADO (fila de cortesia), nada enviado", res.get("queued") is True and not was.sent, res)
    check("adiamento registrado em Atividades", any("adiado" in a["title"] for a in act.logged))

    store["conversations"] = []  # atendimento terminou
    dr._active = []
    res2 = asyncio.run(po.send_to_client_guarded("c1", "5547988887777", "Boleto disponivel",
                                                 "billing", "cobranca da parcela 1"))
    check("cliente livre = envia e registra", res2.get("ok") and not res2.get("queued")
          and len(was.sent) == 1 and len(store.get("platform_sends", [])) == 1, res2)

    # fila drena quando desocupa
    drained = asyncio.run(po.check_platform_queue())
    check("fila existe para drenar depois", isinstance(drained, int))

    # ---------- 4) nota de contexto ----------
    note = asyncio.run(po.context_note_for("c1", "5547988887777"))
    check("nota de contexto p/ o atendente", note is not None and "cobranca da parcela 1" in note, note)
    none_note = asyncio.run(po.context_note_for("c1", "5599000000000"))
    check("sem envio recente = sem ruido (None)", none_note is None)

    # ---------- 5) fiacao no webhook (source-check) ----------
    wh = (ROOT / "app/api/webhook.py").read_text(encoding="utf-8")
    check("gate de observacao ANTES da IA", "attendance_observation_mode" in wh
          and "Modo observação" in wh)
    check("fromMe da atendente capturado em observacao", "observation fromMe capture" in wh
          or "capture_channel_message" in wh.split("skip_reason")[1][:2000])
    check("nota de contexto injetada SO no texto da IA", "message_for_ai" in wh
          and "context_note_for" in wh)

    # ---------- 6) toggle e blueprint (source-check) ----------
    st_src = (WEB / "lib/admin/tenant-agent-store.ts").read_text(encoding="utf-8")
    check("toggle so para attendance (Core sempre ativo)",
          "setTenantAgentActive" in st_src and "toggle_only_attendance" in st_src)
    bp_src = (WEB / "lib/admin/agent-blueprints-canonical.ts").read_text(encoding="utf-8")
    check("pronome e genero REMOVIDOS do blueprint",
          "attendant_pronoun" not in bp_src.split("VAR_MAX_LENGTH")[0]
          and "attendant_gender" not in bp_src.split("VAR_MAX_LENGTH")[0])
    check("abertura padrao com variaveis + render aninhado",
          "Sou {{attendant_name}}, da {{company_name}}" in bp_src
          and "render aninhado" in bp_src)
    check("blueprint versionado (v2)", "blueprint_version: 'v2'" in bp_src)
    ui_src = (WEB / "app/dashboard/personalizacao/agentes/AgentConfigClient.tsx").read_text(encoding="utf-8")
    check("UI: botao ligar/desligar com estados claros",
          "Observando em silêncio" in ui_src and "Ligar agente" in ui_src)
    hub_src = (WEB / "app/dashboard/personalizacao/corretora/whatsapp/WhatsAppHubClient.tsx").read_text(encoding="utf-8")
    check("hub WhatsApp por funcao com fila de cortesia explicada",
          "Atendimento & Acionamentos" in hub_src and "fila de cortesia" in hub_src)
    sched_src = (ROOT / "app/tasks/buffer_processor.py").read_text(encoding="utf-8")
    check("scheduler: fila de cortesia agendada", "platform_queue_check" in sched_src)
    mig = ROOT / "supabase/migrations/20260720_02_spec045_platform_sends.sql"
    check("migracao platform_sends registrada", mig.exists())

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  - {n}: {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
