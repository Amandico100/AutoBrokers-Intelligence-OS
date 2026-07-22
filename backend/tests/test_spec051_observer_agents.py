"""SPEC-051 — Observador mudo, isolamento, mídia e agentes."""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT.parent


def _load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_observer_has_no_outbound_dependency():
    for relative in (
        "app/services/atlas/observer_intake.py",
        "app/services/atlas/attendance_capture.py",
        "app/services/atlas/observer_media.py",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        assert not any("providers" in name or "whatsapp_service" in name or "dispatch" in name for name in imported)
        assert not any(isinstance(node, ast.Attribute) and node.attr.startswith("send_") for node in ast.walk(tree))


def test_direct_chat_exclusions_are_tenant_scoped():
    mod = _load("spec051_attendance_capture", "app/services/atlas/attendance_capture.py")
    integration = {
        "company_id": "resulta",
        "alert_target": {
            "observer_scope": "insurers_and_clients",
            "observer_exclusions": ["5511999990000"],
            "internal_numbers": ["5511888880000"],
        },
    }
    assert mod.client_chat_allowed(integration, "5547999991111", "5511777770000@s.whatsapp.net", "5511777770000")
    assert not mod.client_chat_allowed(integration, "5547999991111", "grupo@g.us", "")
    assert not mod.client_chat_allowed(integration, "5547999991111", "status@broadcast", "")
    assert not mod.client_chat_allowed(integration, "5547999991111", "5511999990000@s.whatsapp.net", "5511999990000")
    assert not mod.client_chat_allowed(integration, "5547999991111", "5511888880000@s.whatsapp.net", "5511888880000")
    assert not mod.client_chat_allowed(integration, "5547999991111", "5547999991111@s.whatsapp.net", "5547999991111")
    assert not mod.client_chat_allowed(integration, "5547999991111", "221800818593797@lid", "221800818593797")
    assert mod.client_chat_allowed(
        integration,
        "5547999991111",
        "221800818593797@lid",
        "5511777770000",
        alternate_jid="5511777770000@s.whatsapp.net",
    )
    assert not mod.client_chat_allowed(
        integration,
        "5547999991111",
        "221800818593797@lid",
        "5511888880000",
        alternate_jid="5511888880000@s.whatsapp.net",
    )


def test_media_enrichment_and_agent_orchestration_contracts():
    observer = (ROOT / "app/services/atlas/observer_intake.py").read_text(encoding="utf-8")
    media = (ROOT / "app/services/atlas/observer_media.py").read_text(encoding="utf-8")
    scheduler = (ROOT / "app/tasks/buffer_processor.py").read_text(encoding="utf-8")
    sentinel = (ROOT / "app/services/atlas/route_sentinel.py").read_text(encoding="utf-8")
    distiller = (ROOT / "app/services/attendance_distiller.py").read_text(encoding="utf-8")
    memory = (ROOT / "app/services/agent_memory.py").read_text(encoding="utf-8")
    admin = (ROOT / "app/api/admin_atlas.py").read_text(encoding="utf-8")

    for field in ("mimetype", "filename", "caption", "message_id", "wa_timestamp", "company_id"):
        assert field in observer + media
    assert "/message/downloadmedia" in media
    assert "OBSERVER_MEDIA_MAX_MB" in media
    assert "enrichment_status" in media and "derived_text" in media
    assert "finally" in media and "unlink" in media
    assert "private_object" in media and "get_public_url" not in media
    assert "observer_media_check" in scheduler

    assert "ATLAS_INCREMENTAL_INTERVAL_MINUTES" in scheduler
    assert "AGENT_MEMORY_INTERVAL_HOURS" in scheduler
    assert "if passed is True" in sentinel
    assert "incremental=True" in sentinel and "atlas:sentinela:watermark:" in sentinel
    assert 'detail.get("signature") == signature' in sentinel
    assert '"status": "draft"' in distiller
    assert '"status": "pending_review"' in distiller
    assert "rebuild_agent_memories" in memory
    assert "/espelho/run" in admin
    assert "processa somente dados novos" in admin.lower()

    sentinel_mod = _load("spec051_route_sentinel", "app/services/atlas/route_sentinel.py")
    watermarks = sentinel_mod._session_watermarks([
        {"insurer_key": "hdi", "ramo": "auto", "last_event_at": "2026-07-22T10:00:00Z"},
        {"insurer_key": "hdi", "ramo": "auto", "last_event_at": "2026-07-22T11:00:00Z"},
        {"insurer_key": "porto", "ramo": None, "last_event_at": "2026-07-22T09:00:00Z"},
    ])
    assert watermarks == [
        ("hdi", "auto", "2026-07-22T11:00:00Z"),
        ("porto", "auto", "2026-07-22T09:00:00Z"),
    ]


def test_multitenant_pairing_keys_and_browser_secret_boundary():
    orchestrator = (ROOT / "app/services/whatsapp/pairing_orchestrator.py").read_text(encoding="utf-8")
    proxy = (WEB / "app/api/dashboard/whatsapp-channel/route.ts").read_text(encoding="utf-8")
    assert "whatsapp:pairing:{company_id}:{purpose}" in orchestrator
    assert "company_id" in orchestrator and "purpose" in orchestrator
    assert "attempt_id" in orchestrator and "correlation_id" in orchestrator
    assert "EVOLUTION_GO_GLOBAL_KEY" not in proxy
    assert "instance_token" not in proxy and "webhook_token" not in proxy
    assert "company_id: ctx.companyId" in proxy
    assert "company_id: body" not in proxy and "company_id: payload" not in proxy


def test_media_worker_success_and_failure_are_isolated():
    media = _load("spec051_observer_media_behavior", "app/services/atlas/observer_media.py")

    class Redis:
        def __init__(self, payload):
            self.queue = [payload]
            self.values = {}

        async def lpop(self, _key):
            return self.queue.pop(0) if self.queue else None

        async def set(self, key, value, ex=None, nx=False):
            if nx and key in self.values:
                return False
            self.values[key] = value
            return True

        async def delete(self, key):
            self.values.pop(key, None)

    payload = '{"company_id":"resulta","message_id":"M1","table":"observed_events"}'
    redis = Redis(payload)
    redis_module = types.ModuleType("app.core.redis")

    async def get_redis():
        return redis

    redis_module.get_async_redis_client = get_redis
    previous_redis_module = sys.modules.get("app.core.redis")
    sys.modules["app.core.redis"] = redis_module
    updates = []
    original_process = media._process_payload
    original_update = media._update_record_sync
    try:
        async def success(_payload):
            return None

        media._process_payload = success
        assert asyncio.run(media.check_observer_media(batch_size=1)) == 1

        redis.queue.append(payload)

        async def failure(_payload):
            raise RuntimeError("download_failed")

        media._process_payload = failure
        media._update_record_sync = lambda item, changes: updates.append((item, changes))
        assert asyncio.run(media.check_observer_media(batch_size=1)) == 0
        assert updates and updates[-1][1]["enrichment_status"] == "failed"
    finally:
        media._process_payload = original_process
        media._update_record_sync = original_update
        if previous_redis_module is None:
            sys.modules.pop("app.core.redis", None)
        else:
            sys.modules["app.core.redis"] = previous_redis_module


def test_atlas_concurrent_claim_is_single_winner():
    sentinel = _load("spec051_route_sentinel_claim", "app/services/atlas/route_sentinel.py")

    class Redis:
        def __init__(self):
            self.values = {}

        async def set(self, key, value, nx=False, ex=None):
            if nx and key in self.values:
                return False
            self.values[key] = value
            return True

    async def run():
        redis = Redis()
        results = await asyncio.gather(
            sentinel._claim_with_redis(redis, "atlas:test", ttl_seconds=60),
            sentinel._claim_with_redis(redis, "atlas:test", ttl_seconds=60),
        )
        assert sum(bool(token) for token in results) == 1

    asyncio.run(run())


def test_six_multitenant_cases():
    mod = _load("spec051_pairing_tenant", "app/services/whatsapp/pairing_orchestrator.py")
    orchestrator = (ROOT / "app/services/whatsapp/pairing_orchestrator.py").read_text(encoding="utf-8")
    proxy = (WEB / "app/api/dashboard/whatsapp-channel/route.ts").read_text(encoding="utf-8")
    webhook = (ROOT / "app/api/webhook.py").read_text(encoding="utf-8")
    sample = mod.public_pairing_state({
        "attempt_id": "a", "state": "qr_ready", "qr_base64": "resulta-qr",
        "company_id": "resulta", "token": "secret", "global_key": "secret",
    })
    checks = {
        "resulta_not_autofleet": mod.PairingOrchestrator._key("resulta", "observer") != mod.PairingOrchestrator._key("autofleet", "observer"),
        "autofleet_not_resulta": 'state.get("company_id") != company_id' in orchestrator,
        "qr_isolated": sample.get("qr_base64") == "resulta-qr" and "company_id" not in sample,
        "webhook_tenant": "get_integration_by_webhook_token" in webhook and "webhook_token_matches" in webhook,
        "tenant_records": '"company_id": company_id' in orchestrator and '.eq("company_id", company_id)' in orchestrator,
        "no_browser_credentials": "token" not in sample and "global_key" not in sample and "ctx.companyId" in proxy,
    }
    assert len(checks) == 6 and all(checks.values()), [name for name, ok in checks.items() if not ok]


if __name__ == "__main__":
    test_observer_has_no_outbound_dependency()
    test_direct_chat_exclusions_are_tenant_scoped()
    test_media_enrichment_and_agent_orchestration_contracts()
    test_multitenant_pairing_keys_and_browser_secret_boundary()
    test_media_worker_success_and_failure_are_isolated()
    test_atlas_concurrent_claim_is_single_winner()
    test_six_multitenant_cases()
    print("PASS: SPEC-051 observer/agent contracts (6 tenant cases)")
