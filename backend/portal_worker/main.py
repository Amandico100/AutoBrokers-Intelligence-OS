"""portal-worker (SPEC-020 P1): FastAPI fino (health) + poll loop no startup.
Serviço próprio no EasyPanel (mesmo repo; Dockerfile em backend/portal_worker/).
Gate PORTAL_REAL_ENABLED off por padrão: sobe, responde /health, não age."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI

from portal_worker.worker import poll_loop, portal_real_enabled

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="AutoBrokers Portal Worker")


def build_info() -> dict:
    """SHA/hora gravados no build (Dockerfile stage gitinfo) — prova qual versão
    está no ar. Sem os arquivos (ex.: dev local) devolve 'unknown', nunca quebra."""
    info = {}
    here = Path(__file__).resolve().parent
    for key, fname in (("build_sha", "build_sha.txt"), ("build_time", "build_time.txt")):
        try:
            info[key] = (here / fname).read_text(encoding="ascii").strip() or "unknown"
        except Exception:  # noqa: BLE001
            info[key] = "unknown"
    return info


@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(poll_loop())


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "portal_real_enabled": portal_real_enabled(), **build_info()}
