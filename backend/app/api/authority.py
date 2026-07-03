"""Autoridade & Prompt Efetivo (Onda 3 / SPEC-018) — endpoints READ-ONLY.

GET /api/authority/prompt-effective?company_id&agent_id — o que o runtime
REALMENTE monta para o agente (camadas, tools, capabilities, divergências).
Chave interna Next↔Backend; nenhum segredo/prompt cru exposto (redigido).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException

from app.core.database import get_supabase_client
from app.services.prompt_effective_service import build_prompt_effective

logger = logging.getLogger(__name__)
router = APIRouter()


def _require_internal_key(provided: Optional[str]) -> None:
    expected = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    if not expected or not provided or provided != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


@router.get("/api/authority/prompt-effective")
async def prompt_effective(
    company_id: str,
    agent_id: str,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    supabase = get_supabase_client()
    client = getattr(supabase, "client", supabase)

    def _load() -> Dict[str, Any]:
        agent_res = client.table("agents").select("*").eq("id", agent_id).eq("company_id", company_id).limit(1).execute()
        if not agent_res.data:
            raise HTTPException(status_code=404, detail="agent_not_found")
        agent = agent_res.data[0]
        company_res = client.table("companies").select("agent_instructions, llm_provider, llm_model").eq("id", company_id).limit(1).execute()
        company_config = company_res.data[0] if company_res.data else {}
        http_res = client.table("agent_http_tools").select("name, is_active").eq("agent_id", agent_id).execute()
        deleg_res = client.table("agent_delegations").select("id").eq("orchestrator_id", agent_id).eq("is_active", True).execute()
        return {
            "agent": agent,
            "company_config": company_config,
            "http_tools": http_res.data or [],
            "delegations_count": len(deleg_res.data or []),
        }

    data = await asyncio.to_thread(_load)

    from app.agents.capability_resolver import resolve_active_capabilities

    resolved = await asyncio.to_thread(
        resolve_active_capabilities, supabase, str(company_id), data["agent"].get("agent_role")
    )

    mcp_tools = []
    try:
        from app.services.mcp_gateway_service import get_mcp_gateway

        mcp_tools = await get_mcp_gateway().get_agent_mcp_tools(str(agent_id)) or []
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[AUTHORITY] mcp lookup skipped: {type(e).__name__}")

    return build_prompt_effective(
        agent=data["agent"],
        company_config=data["company_config"],
        resolved_capabilities=resolved or {},
        http_tools=data["http_tools"],
        mcp_tools=mcp_tools,
        delegations_count=data["delegations_count"],
    )
