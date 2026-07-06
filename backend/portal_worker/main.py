"""portal-worker (SPEC-020 P1): FastAPI fino (health) + poll loop no startup.
Serviço próprio no EasyPanel (mesmo repo; Dockerfile em backend/portal_worker/).
Gate PORTAL_REAL_ENABLED off por padrão: sobe, responde /health, não age."""
from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI

from portal_worker.worker import poll_loop, portal_real_enabled

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="AutoBrokers Portal Worker")


@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(poll_loop())


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "portal_real_enabled": portal_real_enabled()}
