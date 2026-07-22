#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
whatsmeow = (root / "pkg/whatsmeow/service/whatsmeow.go").read_text(encoding="utf-8")
instance = (root / "pkg/instance/service/instance_service.go").read_text(encoding="utf-8")
store = (root / "pkg/passkey/ceremony/store.go").read_text(encoding="utf-8")
handler = (root / "pkg/passkey/handler/passkey_handler.go").read_text(encoding="utf-8")
server = (root / "pkg/server/handler/server_handler.go").read_text(encoding="utf-8")

checks = {
    "passkey webhook events share the QR bucket": (
        'case "QRCode", "QRTimeout", "QRSuccess", "PasskeyRequest", "PasskeyConfirmation", "PasskeyError":'
        in whatsmeow
    ),
    "socket replacement invalidates ceremony": "passkey_socket_restarted" in whatsmeow,
    "ceremony token is not logged": "ceremony token=%s" not in whatsmeow,
    "passkey QR contract exposes errors": 'PasskeyError' in instance and 'json:"passkeyError,omitempty"' in instance,
    "passkey QR contract exposes expiry": 'ExpiresAt' in instance and 'json:"expiresAt,omitempty"' in instance,
    "ceremony state tracks expiry": 'ExpiresAt' in store and 'json:"expiresAt"' in store,
    "ceremony API returns expiry": 'resp["expiresAt"]' in handler,
    "passkey CORS is restricted to WhatsApp Web": "https://web.whatsapp.com" in handler,
    "passkey CORS removes inherited wildcard": 'Header().Del("Access-Control-Allow-Origin")' in handler,
    "health diagnostics expose provider version": '"version"' in server and "version string" in server,
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    for name in failed:
        print(f"FAIL: {name}", file=sys.stderr)
    raise SystemExit(1)

print(f"PASS: {len(checks)} passkey contract checks")
