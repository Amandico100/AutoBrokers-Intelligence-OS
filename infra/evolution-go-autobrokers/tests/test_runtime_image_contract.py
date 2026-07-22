#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")

checks = {
    "runtime keeps the provider non-root": "USER evolution" in dockerfile,
    "runtime pre-creates the provider log directory": "mkdir -p /app/logs" in dockerfile,
    "runtime grants the log directory to the provider user": (
        "chown evolution:evolution /app/logs" in dockerfile
        or "chown -R evolution:evolution /app" in dockerfile
    ),
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    for name in failed:
        print(f"FAIL: {name}", file=sys.stderr)
    raise SystemExit(1)

print(f"PASS: {len(checks)} runtime image checks")
