"""SPEC-020 hardening - recuperacao de jobs orfaos + timeout + build info.

Rodar: python backend/tests/test_spec020_worker_hardening.py
Logica pura (sem Playwright/Supabase): stale_running_patch, _parse_ts, build_info.
Motivacao: job vidros 1b60d8c8 ficou 3 dias preso em 'running' apos restart do
worker (2026-07-07 -> 2026-07-10) e ninguem percebeu.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
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


from portal_worker.worker import (  # noqa: E402
    JOB_TIMEOUT_SECONDS,
    STALE_MARGIN_SECONDS,
    _parse_ts,
    stale_running_patch,
)


def run():
    print("== SPEC-020 hardening - worker ==\n")

    now = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)
    old = (now - timedelta(seconds=JOB_TIMEOUT_SECONDS + STALE_MARGIN_SECONDS + 60)).isoformat()
    fresh = (now - timedelta(seconds=60)).isoformat()

    # _parse_ts tolerante aos formatos do Supabase
    check("parse ISO com espaco e +00", _parse_ts("2026-07-10 04:01:46.577587+00") is not None)
    check("parse ISO com T e Z", _parse_ts("2026-07-10T04:01:46Z") is not None)
    check("parse vazio -> None", _parse_ts("") is None)
    check("parse lixo -> None", _parse_ts("ontem") is None)
    naive = _parse_ts("2026-07-10 04:01:46")
    check("parse sem tz assume UTC", naive is not None and naive.tzinfo is not None)

    # stale_running_patch: fresco fica em paz
    check("job running fresco nao e tocado", stale_running_patch({"started_at": fresh, "attempts": 1}, now) is None)

    # orfao na 1a tentativa -> volta pra fila
    p1 = stale_running_patch({"started_at": old, "attempts": 1}, now)
    check("orfao 1a tentativa -> requeue", p1 is not None and p1.get("status") == "queued", p1)
    check("requeue registra motivo", p1 is not None and "worker" in str(p1.get("error") or ""), p1)

    # orfao reincidente -> failed com finished_at
    p2 = stale_running_patch({"started_at": old, "attempts": 2}, now)
    check("orfao reincidente -> failed", p2 is not None and p2.get("status") == "failed", p2)
    check("failed carrega finished_at", p2 is not None and bool(p2.get("finished_at")), p2)

    # sem started_at usa created_at; sem nenhum -> None (nunca chuta)
    p3 = stale_running_patch({"created_at": old, "attempts": 0}, now)
    check("fallback por created_at funciona", p3 is not None and p3.get("status") == "queued", p3)
    check("sem timestamps -> nao toca", stale_running_patch({"attempts": 0}, now) is None)

    # build_info nunca quebra sem os arquivos (dev local)
    import types

    fastapi_stub = types.ModuleType("fastapi")

    class _App:
        def __init__(self, **_):
            pass

        def on_event(self, *_a, **_k):
            return lambda fn: fn

        def get(self, *_a, **_k):
            return lambda fn: fn

    fastapi_stub.FastAPI = _App
    sys.modules.setdefault("fastapi", fastapi_stub)
    from portal_worker.main import build_info

    info = build_info()
    check("build_info tem build_sha", "build_sha" in info, info)
    check("build_info tem build_time", "build_time" in info, info)
    check("build_info sem arquivo -> unknown (nao quebra)", all(bool(v) for v in info.values()), info)

    print(f"\nPASS={PASS} FAIL={FAIL}")
    if FAILURES:
        for name, detail in FAILURES:
            print(f"  FALHOU: {name} -> {detail}")
        sys.exit(1)


if __name__ == "__main__":
    run()
