"""SPEC-023 P2 - HITL CAPTCHA/2FA evidence for portal jobs.

Rodar: python backend/tests/test_spec023_hitl.py
House-style: importlib/stubs/check, sem pytest.
"""

import asyncio
import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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


class _Page:
    url = "https://portal.example/challenge"

    def __init__(self):
        self.calls = []

    async def screenshot(self, **kwargs):
        self.calls.append(kwargs)
        return b"jpeg-bytes"


def run():
    print("== SPEC-023 P2 - Portal HITL evidence ==\n")

    from portal_worker.journeys import JourneyResult
    from portal_worker.worker import _augment_hitl_evidence, _capture_hitl_screenshot, _hitl_kind

    cap = JourneyResult(status="needs_human", message="portal pediu CAPTCHA/2FA")
    check("captcha/2FA classifica kind", _hitl_kind(cap, {}) == "captcha_2fa")

    unk = JourneyResult(status="needs_human", message="tela pos-login nao reconhecida")
    check("tela desconhecida classifica review", _hitl_kind(unk, {}) == "review")

    evidence = {"url": "https://portal.example/challenge", "login_fields_found": {"username": True, "password": True}}
    enriched = _augment_hitl_evidence(cap, evidence)
    check("hitl evidence preserva mensagem", enriched.get("message") == "portal pediu CAPTCHA/2FA", enriched)
    check("hitl evidence inclui contrato", enriched.get("hitl", {}).get("required") is True, enriched)
    check("hitl evidence inclui kind", enriched.get("hitl", {}).get("kind") == "captcha_2fa", enriched)
    check("hitl evidence indica requeue", enriched.get("hitl", {}).get("resume_mode") == "requeue_after_human", enriched)

    page = _Page()
    shot = asyncio.run(_capture_hitl_screenshot(page))
    expected = "data:image/jpeg;base64," + base64.b64encode(b"jpeg-bytes").decode("ascii")
    check("screenshot vira data URL", shot == expected, shot)
    check("screenshot usa jpeg viewport", page.calls and page.calls[0].get("type") == "jpeg" and page.calls[0].get("full_page") is False, page.calls)

    print(f"\n== {PASS} ok / {FAIL} fail ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} ({d})")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
