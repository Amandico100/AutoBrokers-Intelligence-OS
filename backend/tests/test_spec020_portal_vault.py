"""SPEC-020 - Cofre de portal do smith-api (portal_vault): mascara + round-trip.

Rodar: python backend/tests/test_spec020_portal_vault.py
"""

import importlib.util
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS = 0
FAIL = 0
FAILURES = []


def check(name, cond, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


for name in ("app", "app.services"):
    m = sys.modules.setdefault(name, types.ModuleType(name))
    m.__path__ = []

spec = importlib.util.spec_from_file_location("app.services.portal_vault", ROOT / "app/services/portal_vault.py")
pv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pv)


def run():
    print("== SPEC-020 - portal_vault ==\n")

    m = pv.mask("corretor123")
    check("mask mantem inicio/fim", m.startswith("co") and m.endswith("23"))
    check("mask esconde o meio", "•" in m and "rretor1" not in m)
    check("mask curto", pv.mask("ab") == "a••")
    check("mask vazio", pv.mask("") == "")

    try:
        from cryptography.fernet import Fernet

        os.environ["PORTAL_VAULT_KEY"] = Fernet.generate_key().decode()
        tok = pv.encrypt("senha-portal-123")
        check("encrypt != claro", tok != "senha-portal-123")
        check("round-trip", pv.decrypt(tok) == "senha-portal-123")
    except ImportError:
        print("  [skip] cryptography ausente localmente")

    print(f"\n== {PASS} ok / {FAIL} fail ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} ({d})")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
