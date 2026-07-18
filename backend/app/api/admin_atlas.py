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


@router.post("/weave")
async def weave(body: Optional[Dict[str, Any]] = None, _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Tece o mapa observado. Sem insurer_key: tece TODAS as seguradoras com
    sessões observadas. Idempotente (reprocessa o histórico)."""
    from app.services.atlas.weaver import weave_insurer

    payload = body or {}
    insurer = str(payload.get("insurer_key") or "").strip().lower()
    ramo = str(payload.get("ramo") or "").strip().lower() or "auto"
    if insurer:
        return await weave_insurer(insurer, ramo)

    from app.core.database import get_supabase_client

    supabase = get_supabase_client()

    def _distinct() -> list:
        rows = (supabase.client.table("observed_sessions")
                .select("insurer_key").not_.is_("insurer_key", "null").execute().data or [])
        return sorted({r["insurer_key"] for r in rows if r.get("insurer_key")})

    keys = await asyncio.to_thread(_distinct)
    results = [await weave_insurer(k, ramo) for k in keys]
    return {"ok": True, "woven": results}


@router.get("/maps")
async def atlas_maps(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Todos os mapas observados (resumo p/ a grade da página Atlas)."""
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()

    def _q() -> list:
        return (supabase.client.table("ura_maps")
                .select("id, insurer_key, ramo, status, source, diff_summary, map, created_at")
                .in_("status", ["observed", "proposed", "active"])
                .order("created_at", desc=True).execute().data or [])

    rows = await asyncio.to_thread(_q)
    # dedupe por (insurer, ramo) mantendo o mais recente; resumo só (sem o mapa inteiro)
    seen = set()
    cards = []
    for r in rows:
        k = (r["insurer_key"], r["ramo"])
        if k in seen:
            continue
        seen.add(k)
        cov = ((r.get("map") or {}).get("coverage") or {})
        cards.append({
            "id": r["id"], "insurer_key": r["insurer_key"], "ramo": r["ramo"],
            "status": r["status"], "source": r["source"],
            "nodes": cov.get("nodes", 0), "coverage_pct": cov.get("pct", 0),
            "sessions": ((r.get("map") or {}).get("meta") or {}).get("sessions", 0),
            "updated_at": r["created_at"],
        })
    return {"ok": True, "cards": cards}


@router.get("/map/{insurer_key}/{ramo}")
async def atlas_map_detail(insurer_key: str, ramo: str, _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Mapa completo (árvore) de uma seguradora×ramo para a visualização."""
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()

    def _q() -> Optional[dict]:
        rows = (supabase.client.table("ura_maps").select("id, map, status, source, created_at")
                .eq("insurer_key", insurer_key.lower()).eq("ramo", ramo.lower())
                .in_("status", ["observed", "proposed", "active"])
                .order("created_at", desc=True).limit(1).execute().data or [])
        return rows[0] if rows else None

    row = await asyncio.to_thread(_q)
    if not row:
        return {"ok": False, "error": "mapa não encontrado"}
    return {"ok": True, "insurer_key": insurer_key, "ramo": ramo,
            "status": row["status"], "map": row.get("map") or {}}


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
