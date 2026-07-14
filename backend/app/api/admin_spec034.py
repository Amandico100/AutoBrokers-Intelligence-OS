"""Endpoints admin das superfícies SPEC-034/036 (Etapa 1).

Alimentam as páginas novas do portal admin (design Claude Design 14/07):
Central de Agentes, Acionamentos ao vivo, Insights·Garimpo — e as ações do
Alfaiate (aprovar mapa) e do Registro de Seguradoras.

Todos exigem master admin (X-Admin-API-Key), mesmo padrão do billing_admin.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.core.auth import require_master_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/spec034", tags=["Admin SPEC-034"])


@router.get("/agents-status")
async def agents_status(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    from app.core.heartbeat import read_all

    return {"agents": await read_all()}


@router.get("/sessions")
async def active_sessions(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Sessões de acionamento ativas (Redis) com transcript para a timeline."""
    sessions: List[Dict[str, Any]] = []
    try:
        from app.core.redis import get_async_redis_client
        from app.services.dispatch_mirror import insurer_label_from_ref

        redis = await get_async_redis_client()
        async for key in redis.scan_iter(match="dispatch:active:*"):
            k = key.decode() if isinstance(key, (bytes, bytearray)) else str(key)
            raw = await redis.get(k)
            if not raw:
                continue
            try:
                s = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
            except Exception:  # noqa: BLE001
                continue
            parts = k.split(":")
            transcript = (s.get("transcript") or [])[-40:]
            sessions.append({
                "company_id": parts[2] if len(parts) >= 4 else "",
                "insurer_phone": parts[3] if len(parts) >= 4 else "",
                "insurer_label": insurer_label_from_ref(s.get("playbook_ref")),
                "case_id": s.get("case_id"), "state": s.get("state"),
                "subservice": s.get("subservice"), "created_at": s.get("created_at"),
                "sentinela_attempts": s.get("sentinela_attempts") or 0,
                "reason": s.get("reason"),
                "timeline": [
                    {"at": t.get("at"), "direction": t.get("direction"),
                     "via": t.get("via") or ("seguradora" if t.get("direction") == "in" else "even"),
                     "text": str(t.get("text") or "")[:300]}
                    for t in transcript
                ],
            })
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ADMIN34] sessions falhou: {type(e).__name__}")
    sessions.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return {"sessions": sessions}


@router.get("/insights")
async def insights(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Ranking do Garimpo + histórico da IA de Sugestões (30 dias)."""
    out: Dict[str, Any] = {"ranking": [], "sugestoes": [], "companies": {}}
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        rows = await asyncio.to_thread(
            lambda: db.client.table("broker_insights")
            .select("company_id, kind, summary, source, status, created_at")
            .order("created_at", desc=True).limit(1000).execute()
        )
        garimpo = [r for r in rows.data or [] if r.get("source") == "garimpo"]
        counts = Counter((r["kind"], r["summary"][:80]) for r in garimpo)
        out["ranking"] = [
            {"kind": k, "summary": s, "count": c}
            for (k, s), c in counts.most_common(20)
        ]
        out["sugestoes"] = [
            {"company_id": r.get("company_id"), "summary": r.get("summary"),
             "status": r.get("status"), "created_at": r.get("created_at")}
            for r in (rows.data or []) if r.get("source") == "sugestoes_ia"
        ][:20]
        comp = await asyncio.to_thread(
            lambda: db.client.table("companies").select("id, company_name").execute()
        )
        out["companies"] = {c["id"]: c["company_name"] for c in comp.data or []}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ADMIN34] insights falhou: {type(e).__name__}")
    return out


@router.get("/scorecards")
async def scorecards(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    out: Dict[str, Any] = {"summary": [], "recent": []}
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        rows = await asyncio.to_thread(
            lambda: db.client.table("conversation_scorecards")
            .select("company_id, conversation_id, score, flags, created_at")
            .order("created_at", desc=True).limit(500).execute()
        )
        by_company: Dict[str, List[int]] = {}
        flag_counter: Counter = Counter()
        for r in rows.data or []:
            by_company.setdefault(str(r.get("company_id")), []).append(int(r.get("score") or 0))
            for f in r.get("flags") or []:
                flag_counter[f] += 1
        out["summary"] = [
            {"company_id": cid, "avg_score": round(sum(v) / len(v), 1), "audited": len(v)}
            for cid, v in by_company.items()
        ]
        out["top_flags"] = flag_counter.most_common(8)
        out["recent"] = (rows.data or [])[:30]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ADMIN34] scorecards falhou: {type(e).__name__}")
    return out


@router.get("/registry")
async def registry(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    from app.services.insurer_registry import INSURER_REGISTRY

    return {"registry": INSURER_REGISTRY}


@router.get("/maps")
async def list_maps(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    out: Dict[str, Any] = {"maps": [], "overlays": []}
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        maps = await asyncio.to_thread(
            lambda: db.client.table("ura_maps")
            .select("id, insurer_key, ramo, version, status, diff_summary, created_at")
            .order("created_at", desc=True).limit(100).execute()
        )
        overlays = await asyncio.to_thread(
            lambda: db.client.table("playbook_overlays")
            .select("id, playbook_ref, kind, note, status, created_at")
            .order("created_at", desc=True).limit(100).execute()
        )
        out["maps"] = maps.data or []
        out["overlays"] = overlays.data or []
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ADMIN34] maps falhou: {type(e).__name__}")
    return out


@router.post("/maps/{map_id}/activate")
async def activate_map_endpoint(map_id: str, _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Aprovação 1-clique do founder: promove um mapa proposto a ativo."""
    from app.services.ura_map_service import activate_map

    ok = await activate_map(map_id)
    return {"ok": ok}
