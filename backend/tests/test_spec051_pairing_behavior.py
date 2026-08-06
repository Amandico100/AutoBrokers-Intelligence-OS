"""SPEC-051 — behavioral tests for pairing serialization and expiry.

Standalone by design: no live Redis, Supabase, or Evolution Go is required.
"""

from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
import sys
from datetime import timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_orchestrator():
    # `channel_identity` é carregado DE VERDADE, não dublado: ele decide o nome
    # da instância, e o nome é a chave de deduplicação do acervo. Um dublê aqui
    # deixaria o teste verde enquanto o nome real mudasse — que é exatamente o
    # tipo de verde que não protege ninguém. O módulo é puro (sem I/O, sem
    # dependência de `app.*`), então carregá-lo não traz o `openai` do pacote.
    if "app.services.whatsapp.channel_identity" not in sys.modules:
        ident_path = ROOT / "app/services/whatsapp/channel_identity.py"
        ident_spec = importlib.util.spec_from_file_location(
            "app.services.whatsapp.channel_identity", ident_path)
        ident = importlib.util.module_from_spec(ident_spec)
        sys.modules[ident_spec.name] = ident
        ident_spec.loader.exec_module(ident)

    path = ROOT / "app/services/whatsapp/pairing_orchestrator.py"
    spec = importlib.util.spec_from_file_location("spec051_pairing_behavior_mod", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeRedis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, nx=False, ex=None):
        assert ex is None or isinstance(ex, (int, timedelta)), (
            "redis-py only accepts int or timedelta for ex"
        )
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    async def delete(self, key):
        return 1 if self.values.pop(key, None) is not None else 0

    async def eval(self, _script, keys_count, *args):
        if keys_count == 1:
            key, expected = args
            if self.values.get(key) == expected:
                return await self.delete(key)
            return 0
        attempt_key, scope_key, raw, _ttl, expected, attempt_id, replace_scope = args
        current_raw = self.values.get(attempt_key)
        if current_raw:
            current = json.loads(current_raw)
            if int(current.get("_revision") or 0) != int(expected):
                return current_raw
        elif int(expected) != 0:
            return ""
        self.values[attempt_key] = raw
        scoped_raw = self.values.get(scope_key)
        can_replace = replace_scope == "1"
        if scoped_raw and not can_replace:
            can_replace = json.loads(scoped_raw).get("attempt_id") == attempt_id
        if not scoped_raw or can_replace:
            self.values[scope_key] = raw
        return raw


def _test_orchestrator(mod, *, slow_refresh=False):
    redis = FakeRedis()

    class TestOrchestrator(mod.PairingOrchestrator):
        def __init__(self):
            super().__init__()
            self.base_url = "https://provider.invalid"
            self.global_key = "global"
            self.public_backend_url = "https://api.invalid"
            self.connect_calls = 0
            self.invalidations = 0
            self.refresh_started = asyncio.Event()
            self.release_refresh = asyncio.Event()

        async def _redis(self):
            return redis

        async def _prepare_and_connect(self, state, *, method, phone_number):
            self.connect_calls += 1
            state.update(mod.build_pairing_state(
                "qr_ready",
                attempt_id=state["attempt_id"],
                correlation_id=state["correlation_id"],
                expires_at=state["expires_at"],
                support_ref=state["support_ref"],
                qr_base64="qr",
                instance="tenant-instance",
                created_at=state["created_at"],
            ))
            return await self._save(state)

        async def _refresh(self, state):
            if slow_refresh:
                self.refresh_started.set()
                await self.release_refresh.wait()
            state.update(mod.build_pairing_state(
                "qr_ready",
                attempt_id=state["attempt_id"],
                correlation_id=state["correlation_id"],
                expires_at=state["expires_at"],
                support_ref=state["support_ref"],
                qr_base64="fresh-qr",
                instance=state.get("instance"),
                created_at=state.get("created_at"),
            ))
            return await self._save(state)

        async def _integration(self, company_id, purpose):
            return {"company_id": company_id, "purpose": purpose, "token": "encrypted-at-rest"}

        async def _invalidate_incomplete(self, integration):
            self.invalidations += 1

    return TestOrchestrator(), redis


async def _one_connect_and_tenant_isolation():
    mod = _load_orchestrator()
    orchestrator, _redis = _test_orchestrator(mod)

    first = await orchestrator.start("resulta", "observer")
    second = await orchestrator.start("resulta", "observer")
    assert first["attempt_id"] == second["attempt_id"]
    assert orchestrator.connect_calls == 1

    try:
        await orchestrator.get("autofleet", "observer", first["attempt_id"])
    except mod.PairingNotFoundError:
        pass
    else:
        raise AssertionError("another tenant read Resulta's attempt")

    assert "company_id" not in first and "token" not in json.dumps(first)


async def _cancel_wins_over_inflight_poll_and_retry_is_fresh():
    mod = _load_orchestrator()
    orchestrator, _redis = _test_orchestrator(mod, slow_refresh=True)
    first = await orchestrator.start("resulta", "observer")

    poll_task = asyncio.create_task(
        orchestrator.get("resulta", "observer", first["attempt_id"])
    )
    await orchestrator.refresh_started.wait()
    cancel_task = asyncio.create_task(
        orchestrator.cancel("resulta", "observer", first["attempt_id"])
    )
    await asyncio.sleep(0)
    orchestrator.release_refresh.set()
    await poll_task
    cancelled = await cancel_task
    final = await orchestrator.get("resulta", "observer", first["attempt_id"])
    assert cancelled["state"] == "cancelled"
    assert final["state"] == "cancelled"
    assert orchestrator.invalidations == 1

    retried = await orchestrator.retry(
        "resulta", "observer", first["attempt_id"], "retry-correlation"
    )
    assert retried["attempt_id"] != first["attempt_id"]
    assert orchestrator.connect_calls == 2


async def _passkey_confirmation_expires_and_invalidates():
    mod = _load_orchestrator()
    redis = FakeRedis()

    class Response:
        def __init__(self, payload):
            self.status_code = 200
            self.content = b"json"
            self._payload = payload

        def json(self):
            return self._payload

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, path, headers=None):
            if path == "/instance/status":
                return Response({"data": {"LoggedIn": False, "Connected": True}})
            return Response({"data": {
                "passkeyStage": "awaiting_confirmation",
                "passkeyOpenUrl": "https://web.whatsapp.com/#wapk=opaque",
            }})

    class PasskeyOrchestrator(mod.PairingOrchestrator):
        def __init__(self):
            super().__init__()
            self.base_url = "https://provider.invalid"
            self.global_key = "global"
            self.public_backend_url = "https://api.invalid"
            self.invalidations = 0

        async def _redis(self):
            return redis

        async def _integration(self, company_id, purpose):
            return {"company_id": company_id, "purpose": purpose, "token": "runtime-token"}

        async def _invalidate_incomplete(self, integration):
            self.invalidations += 1

    original_client = mod.httpx.AsyncClient
    mod.httpx.AsyncClient = Client
    try:
        orchestrator = PasskeyOrchestrator()
        now = mod._utcnow()
        state = mod.build_pairing_state(
            "passkey_awaiting_confirmation",
            attempt_id="passkey-attempt",
            correlation_id="passkey-correlation",
            created_at=mod._iso(now - timedelta(seconds=100)),
            expires_at=mod._iso(now + timedelta(minutes=5)),
            instance="tenant-instance",
        )
        state.update({
            "company_id": "resulta",
            "purpose": "observer",
            "_passkey_wait_started_at": mod._iso(now - timedelta(seconds=91)),
        })
        await orchestrator._save(state)
        result = await orchestrator.get("resulta", "observer", "passkey-attempt")
        assert result["state"] == "passkey_failed"
        assert orchestrator.invalidations == 1
    finally:
        mod.httpx.AsyncClient = original_client


async def _stale_write_cannot_resurrect_terminal_state():
    mod = _load_orchestrator()
    orchestrator, _redis = _test_orchestrator(mod)
    first = await orchestrator.start("resulta", "observer")
    current = await orchestrator._load_attempt(first["attempt_id"])
    stale_refresh = copy.deepcopy(current)
    cancelled = copy.deepcopy(current)
    cancelled.update(mod.build_pairing_state(
        "cancelled",
        attempt_id=current["attempt_id"],
        correlation_id=current["correlation_id"],
        expires_at=current["expires_at"],
        support_ref=current["support_ref"],
        instance=current.get("instance"),
        created_at=current.get("created_at"),
    ))
    await orchestrator._save(cancelled)
    stale_refresh.update(mod.build_pairing_state(
        "qr_ready",
        attempt_id=current["attempt_id"],
        correlation_id=current["correlation_id"],
        expires_at=current["expires_at"],
        support_ref=current["support_ref"],
        qr_base64="stale",
        instance=current.get("instance"),
        created_at=current.get("created_at"),
    ))
    persisted = await orchestrator._save(stale_refresh)
    assert persisted["state"] == "cancelled"
    final = await orchestrator._load_attempt(first["attempt_id"])
    assert final["state"] == "cancelled"


def test_pairing_behavior():
    asyncio.run(_one_connect_and_tenant_isolation())
    asyncio.run(_cancel_wins_over_inflight_poll_and_retry_is_fresh())
    asyncio.run(_passkey_confirmation_expires_and_invalidates())
    asyncio.run(_stale_write_cannot_resurrect_terminal_state())


def test_passkey_url_rejects_credentials_and_non_default_port():
    mod = _load_orchestrator()
    assert mod._safe_passkey_url("https://web.whatsapp.com/#wapk=opaque")
    assert mod._safe_passkey_url("https://user@web.whatsapp.com/#wapk=opaque") is None
    assert mod._safe_passkey_url("https://web.whatsapp.com:444/#wapk=opaque") is None


if __name__ == "__main__":
    test_pairing_behavior()
    test_passkey_url_rejects_credentials_and_non_default_port()
    print("PASS: SPEC-051 pairing behavioral tests")
