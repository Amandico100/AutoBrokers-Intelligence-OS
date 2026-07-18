"""SPEC-038 ATLAS — endpoints admin do Observador (Bloco A).

Todos exigem master admin (X-Admin-API-Key) — inteligência 100% AutoBrokers,
corretoras JAMAIS acessam (política do conhecimento global).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends

from app.core.auth import require_master_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/atlas", tags=["Admin ATLAS (SPEC-038)"])


@router.get("/observer/report")
async def observer_report(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Relatório vivo do spike/captura: últimos eventos observados (sem PII de
    não-seguradora por construção), sessões, contadores de descarte e a
    estrutura do último HISTORY_SYNC."""
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()

    def _query() -> Dict[str, Any]:
        events = (supabase.client.table("observed_events")
                  .select("insurer_key, direction, msg_type, text, media_meta, wa_timestamp, created_at, session_id")
                  .order("created_at", desc=True).limit(25).execute())
        sessions = (supabase.client.table("observed_sessions")
                    .select("insurer_key, counterparty, status, started_at, last_event_at")
                    .order("last_event_at", desc=True).limit(10).execute())
        rows = []
        for e in (events.data or []):
            rows.append({**e, "text": (str(e.get("text") or "")[:120] or None)})
        return {"events": rows, "sessions": sessions.data or []}

    out = await asyncio.to_thread(_query)

    drops: Dict[str, Any] = {}
    history: Dict[str, Any] = {}
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        keys = [k async for k in r.scan_iter(match="atlas:drops:*")]
        for k in keys[:10]:
            name = k.decode() if isinstance(k, bytes) else str(k)
            h = await r.hgetall(name)
            drops[name.rsplit(":", 1)[-1]] = {
                (kk.decode() if isinstance(kk, bytes) else kk): (vv.decode() if isinstance(vv, bytes) else vv)
                for kk, vv in (h or {}).items()}
        hs = await r.get("atlas:history_sync:last_structure")
        hc = await r.hgetall("atlas:history_sync:count")
        history = {
            "last_structure": (hs.decode() if isinstance(hs, bytes) else hs),
            "count": {(kk.decode() if isinstance(kk, bytes) else kk): (vv.decode() if isinstance(vv, bytes) else vv)
                      for kk, vv in (hc or {}).items()},
        }
    except Exception as e:  # noqa: BLE001
        drops = {"error": type(e).__name__}

    return {"ok": True, **out, "drops": drops, "history_sync": history}


@router.post("/observer/history-sync")
async def trigger_history_sync(
    body: Optional[Dict[str, Any]] = None, _: Any = Depends(require_master_admin)
) -> Dict[str, Any]:
    """Dispara o pedido de history sync no GO (POST /chat/history-sync) para a
    instância configurada nos envs — parte da verificação D2 do spike."""
    base = (os.getenv("EVOLUTION_GO_BASE_URL") or "").rstrip("/")
    token = os.getenv("EVOLUTION_GO_INSTANCE_TOKEN") or ""
    if not base or not token:
        return {"ok": False, "error": "evolution_go_not_configured"}
    count = int((body or {}).get("count") or 50)
    try:
        async with httpx.AsyncClient(timeout=30.0, base_url=base) as client:
            res = await client.post("/chat/history-sync",
                                    headers={"apikey": token, "Content-Type": "application/json"},
                                    json={"count": count})
            return {"ok": res.status_code < 400, "status": res.status_code, "body": (res.text or "")[:300]}
    except httpx.HTTPError as e:
        return {"ok": False, "error": f"go_unreachable:{type(e).__name__}"}
