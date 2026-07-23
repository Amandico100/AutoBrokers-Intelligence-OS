"""SPEC-051 — contrato do pareamento QR/passkey e superfícies de produto."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT.parent


def _load_orchestrator():
    path = ROOT / "app/services/whatsapp/pairing_orchestrator.py"
    spec = importlib.util.spec_from_file_location("spec051_pairing_orchestrator", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_pairing_state_contract_and_provider_normalization():
    mod = _load_orchestrator()
    assert len(mod.PAIRING_STATES) == 25
    assert {
        "qr_ready", "passkey_challenge", "passkey_awaiting_confirmation",
        "passkey_code_available", "qr_expired", "passkey_expired",
        "passkey_socket_restarted", "re_pair_required", "db_pool_exhausted",
        "provider_unavailable", "timed_out", "cancelled",
    }.issubset(mod.PAIRING_STATES)

    qr = mod.normalize_provider_state(
        {"data": {"QRCode": "abc", "state": "qr_ready", "expiresAt": "2030-01-01T00:00:00Z"}},
        {"data": {"LoggedIn": False, "Connected": True}},
    )
    assert qr["state"] == "qr_ready"
    assert qr["qr_base64"] == "abc"

    passkey = mod.normalize_provider_state(
        {"data": {
            "passkeyStage": "awaiting_confirmation",
            "passkeyOpenUrl": "https://web.whatsapp.com/#wapk=opaque",
            "passkeyCode": "123-456",
            "expiresAt": "2030-01-01T00:00:00Z",
        }},
        {"data": {}},
    )
    assert passkey["state"] == "passkey_awaiting_confirmation"
    assert passkey["passkey_stage"] == "awaiting_confirmation"
    assert passkey["passkey_open_url"].startswith("https://web.whatsapp.com/")

    connected = mod.normalize_provider_state({}, {"data": {"LoggedIn": True}})
    assert connected["state"] == "connected"
    terminal = mod.normalize_provider_state(
        {"data": {"state": "qr_expired", "errorCode": "qr_expired"}}, {"data": {}}
    )
    assert terminal["state"] == "qr_expired"

    state = mod.build_pairing_state("recoverable_error", error_code="provider_http_502")
    for key in ("state", "next_action", "expires_at", "poll_after_ms", "support_ref", "error"):
        assert key in state
    assert "token" not in state and "global_key" not in state and "connection_string" not in state


def test_api_proxy_and_modal_contracts():
    api = (ROOT / "app/api/whatsapp_channel.py").read_text(encoding="utf-8")
    proxy = (WEB / "app/api/dashboard/whatsapp-channel/route.ts").read_text(encoding="utf-8")
    flow = (WEB / "components/vault/WhatsAppPairingFlow.tsx").read_text(encoding="utf-8")
    view = (WEB / "components/vault/PairingStateView.tsx").read_text(encoding="utf-8")

    for route in (
        '/api/whatsapp-channel/pairing"',
        '/api/whatsapp-channel/pairing/{attempt_id}"',
        '/api/whatsapp-channel/pairing/{attempt_id}/retry"',
        '/api/whatsapp-channel/pairing/{attempt_id}/cancel"',
        '/api/admin/whatsapp-channel/diagnostics"',
    ):
        assert route in api

    assert "AbortController" in proxy and "20_000" in proxy
    assert "X-Correlation-ID" in proxy and "res.status" in proxy
    assert "setInterval" not in flow
    assert "setTimeout" in flow and "poll_after_ms" in flow
    assert "inFlightRef" in flow and "attempt_id" in flow
    assert "TERMINAL.has(pairing.state) ? 'pairing'" in flow
    assert "if (!response.ok)" in flow and "pairing_state_busy" in flow
    assert "pairing_code" in view and "Código de pareamento" in view

    expected_text = (
        "Gerar QR code",
        "Gerar novo QR",
        "O WhatsApp pediu uma confirmação de segurança",
        "Abrir WhatsApp Web",
        "Instalar assistente de pareamento",
        "Já instalei — continuar",
        "Cancelar tentativa",
        "Conectar usando número",
        "não evita a confirmação por chave de acesso",
    )
    for text in expected_text:
        assert text in flow + view

    assert "Preparando..." not in flow + view
    assert "passkey_awaiting_confirmation" in view
    assert "A conta não confirmou a chave de acesso" in view
    orchestrator = (ROOT / "app/services/whatsapp/pairing_orchestrator.py").read_text(encoding="utf-8")
    assert "status_response.status_code in (401, 404)" in orchestrator
    assert "current.get(\"state\") not in TERMINAL_STATES" in orchestrator

    assert 'detail="observer_channel_not_paired"' in api
    assert '"unpaired": True' in api


def test_expired_or_missing_attempt_returns_to_clean_start():
    flow = (WEB / "components/vault/WhatsAppPairingFlow.tsx").read_text(encoding="utf-8")

    assert "if (TERMINAL.has(next.state))" in flow
    assert "sessionStorage.removeItem(STORAGE_KEY)" in flow
    assert "response.status === 404 || detail === 'pairing_not_found'" in flow
    assert "resetToStart();" in flow
    assert "setPairing(null)" in flow
    assert "TERMINAL.has(pairing.state) ? 'pairing'" in flow


def test_helper_is_versioned_and_origin_restricted():
    helper = WEB / "public/tools/passkey-helper-autobrokers-0.7.2-ab1.zip"
    checksum = WEB / "public/tools/passkey-helper-autobrokers-0.7.2-ab1.zip.sha256"
    runbook = WEB / "docs/canon/runbooks/RUNBOOK-PASSKEY-WHATSAPP.md"
    assert helper.exists() and helper.stat().st_size > 500
    assert checksum.exists() and len(checksum.read_text(encoding="utf-8").split()[0]) == 64
    text = runbook.read_text(encoding="utf-8")
    assert "https://web.whatsapp.com" in text
    assert "chrome://extensions" in text and "edge://extensions" in text
    assert "não solicita" in text.lower()


def test_twelve_modal_cases():
    mod = _load_orchestrator()
    flow = (WEB / "components/vault/WhatsAppPairingFlow.tsx").read_text(encoding="utf-8")
    view = (WEB / "components/vault/PairingStateView.tsx").read_text(encoding="utf-8")
    orchestrator = (ROOT / "app/services/whatsapp/pairing_orchestrator.py").read_text(encoding="utf-8")
    checks = {
        "timeout": mod.build_pairing_state("timed_out")["state"] == "timed_out",
        "provider_400": mod.PairingOrchestrator._error_state("provider_http_400") == "configuration_error",
        "backend_502": mod.PairingOrchestrator._error_state("provider_http_502") == "provider_unavailable",
        "qr": mod.normalize_provider_state({"QRCode": "x"}, {})["state"] == "qr_ready",
        "qr_expired": mod.normalize_provider_state({"errorCode": "qr_expired"}, {})["state"] == "qr_expired",
        "retry": 'method="qr"' in orchestrator and "Gerar novo QR" in view,
        "passkey": mod.normalize_provider_state({"passkeyStage": "challenge"}, {})["state"] == "passkey_challenge",
        "passkey_expired": mod.normalize_provider_state({"passkeyStage": "expired"}, {})["state"] == "passkey_expired",
        "awaiting_confirmation": mod.normalize_provider_state({"passkeyStage": "awaiting_confirmation"}, {})["state"] == "passkey_awaiting_confirmation",
        "technical_error": mod.build_pairing_state("technical_error")["state"] == "technical_error",
        "refresh": "sessionStorage" in flow and "attempt_id" in flow,
        "double_click": "inFlightRef.current" in flow,
    }
    assert len(checks) == 12 and all(checks.values()), [name for name, ok in checks.items() if not ok]


if __name__ == "__main__":
    test_pairing_state_contract_and_provider_normalization()
    test_api_proxy_and_modal_contracts()
    test_expired_or_missing_attempt_returns_to_clean_start()
    test_helper_is_versioned_and_origin_restricted()
    test_twelve_modal_cases()
    print("PASS: SPEC-051 pairing/passkey contracts (12 modal cases + stale-attempt recovery)")
