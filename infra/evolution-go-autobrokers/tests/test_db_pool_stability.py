#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
whatsmeow = (root / "pkg/whatsmeow/service/whatsmeow.go").read_text(encoding="utf-8")
config = (root / "pkg/config/config.go").read_text(encoding="utf-8")
env = (root / "pkg/config/env/env.go").read_text(encoding="utf-8")

start = whatsmeow.index("func (w whatsmeowService) StartClient")
end = whatsmeow.index("func schedulePresenceUpdates", start)
start_client = whatsmeow[start:end]

checks = {
    "shared sqlstore container is retained by the service": "authContainer" in whatsmeow,
    "shared sql.DB is wrapped with NewWithDB": "sqlstore.NewWithDB" in whatsmeow,
    "StartClient does not allocate a sqlstore pool": "sqlstore.New(" not in start_client,
    "pool max-open env is declared": "POSTGRES_MAX_OPEN_CONNS" in env,
    "pool max-idle env is declared": "POSTGRES_MAX_IDLE_CONNS" in env,
    "pool max-lifetime env is declared": "POSTGRES_CONN_MAX_LIFETIME_MINUTES" in env,
    "pool max-idle-time env is declared": "POSTGRES_CONN_MAX_IDLE_TIME_MINUTES" in env,
    "max-open default is 20": bool(re.search(r"PostgresMaxOpenConns:\s+20", config)),
    "max-idle default is 5": bool(re.search(r"PostgresMaxIdleConns:\s+5", config)),
    "lifetime default is 30 minutes": bool(re.search(r"PostgresConnMaxLifetimeMinutes:\s+30", config)),
    "idle-time default is 5 minutes": bool(re.search(r"PostgresConnMaxIdleTimeMinutes:\s+5", config)),
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    for name in failed:
        print(f"FAIL: {name}", file=sys.stderr)
    raise SystemExit(1)

print(f"PASS: {len(checks)} bounded-pool lifecycle checks")
