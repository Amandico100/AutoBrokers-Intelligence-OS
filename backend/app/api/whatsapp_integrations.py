"""
WhatsApp Integrations API — Secret Flow seguro (39A4.2).

Recebe credenciais Z-API APENAS server-side (via chave interna Next↔Backend),
cifra token/client_token (EncryptionService) e grava em public.integrations.
NUNCA retorna/loga segredo. NÃO envia mensagem (test é validação local).
"""
import hmac
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.database import AsyncSupabaseClient, get_async_db
from app.services.whatsapp.integration_secrets import (
    prepare_integration_for_runtime,
    prepare_integration_for_storage,
)

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_PROVIDERS = {"z-api"}
DEFAULT_BASE_URL = "https://api.z-api.io/instances"


def _require_internal_key(provided: Optional[str]) -> None:
    """Exige a chave interna Next↔Backend (mesmo padrão de Auxiliares)."""
    expected = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    if not expected:
        logger.error("[WA INTEGRATIONS] Internal API key not configured")
        raise HTTPException(status_code=500, detail="Internal API key not configured")
    if not provided or not hmac.compare_digest(str(provided), str(expected)):
        raise HTTPException(status_code=401, detail="Unauthorized internal request")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mask(value: Optional[str]) -> Optional[str]:
    return f"...{str(value)[-4:]}" if value else None


def _sanitize(row: Dict[str, Any]) -> Dict[str, Any]:
    """Projeção SEM segredos para devolver ao Next/UI."""
    return {
        "id": row.get("id"),
        "company_id": row.get("company_id"),
        "agent_id": row.get("agent_id"),
        "provider": row.get("provider"),
        "identifier_masked": _mask(row.get("identifier")),
        "has_instance_id": bool(row.get("instance_id")),
        "has_client_token": bool(row.get("client_token")),
        "base_url": row.get("base_url"),
        "is_active": row.get("is_active"),
    }


class ConfigurePayload(BaseModel):
    company_id: str
    agent_id: str
    provider: str = "z-api"
    identifier: str
    instance_id: str
    token: str
    client_token: Optional[str] = None
    base_url: Optional[str] = None
    buffer_enabled: Optional[bool] = True
    buffer_debounce_seconds: Optional[int] = 3
    buffer_max_wait_seconds: Optional[int] = 10


class TestPayload(BaseModel):
    company_id: str
    integration_id: Optional[str] = None
    agent_id: Optional[str] = None


@router.post("/configure")
async def configure(
    payload: ConfigurePayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    db: AsyncSupabaseClient = Depends(get_async_db),
):
    _require_internal_key(x_autobrokers_internal_key)

    company_id = (payload.company_id or "").strip()
    agent_id = (payload.agent_id or "").strip()
    provider = (payload.provider or "z-api").lower().strip()
    identifier = (payload.identifier or "").strip()
    instance_id = (payload.instance_id or "").strip()
    token = (payload.token or "").strip()
    client_token = (payload.client_token or "").strip() or None
    base_url = (payload.base_url or DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL

    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(status_code=400, detail="provider not allowed")
    if not company_id or not agent_id:
        raise HTTPException(status_code=400, detail="company_id and agent_id are required")
    if not identifier or not instance_id or not token:
        raise HTTPException(status_code=400, detail="identifier, instance_id and token are required")

    # Valida que o agente pertence à empresa (anti-IDOR), sem maybe_single (evita 406).
    try:
        ag = (
            await db.client.table("agents")
            .select("id, company_id")
            .eq("id", agent_id)
            .eq("company_id", company_id)
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WA INTEGRATIONS] agent lookup failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Failed to validate agent")
    if not ag.data:
        raise HTTPException(status_code=404, detail="agent not found for this company")

    # Cifra token/client_token (39A4.1) ANTES de gravar.
    to_store = prepare_integration_for_storage(
        {
            "company_id": company_id,
            "agent_id": agent_id,
            "provider": provider,
            "identifier": identifier,
            "instance_id": instance_id,
            "token": token,
            "client_token": client_token,
            "base_url": base_url,
            "is_active": True,
            "buffer_enabled": bool(payload.buffer_enabled) if payload.buffer_enabled is not None else True,
            "buffer_debounce_seconds": payload.buffer_debounce_seconds or 3,
            "buffer_max_wait_seconds": payload.buffer_max_wait_seconds or 10,
            "updated_at": _now(),
        }
    )

    try:
        resp = (
            await db.client.table("integrations")
            .upsert(to_store, on_conflict="provider,identifier")
            .execute()
        )
        row = resp.data[0] if resp.data else None
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WA INTEGRATIONS] upsert failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Failed to store integration")

    if not row:
        raise HTTPException(status_code=500, detail="Integration not stored")

    logger.info(
        f"[WA INTEGRATIONS] ✅ stored integration for company {company_id} | agent {agent_id} | provider {provider}"
    )
    return {"success": True, "integration": _sanitize(row)}


@router.post("/test")
async def test_configuration(
    payload: TestPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    db: AsyncSupabaseClient = Depends(get_async_db),
):
    """Valida a configuração localmente (descriptografa em memória). NÃO envia mensagem."""
    _require_internal_key(x_autobrokers_internal_key)

    company_id = (payload.company_id or "").strip()
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")

    try:
        query = (
            db.client.table("integrations")
            .select("*")
            .eq("company_id", company_id)
            .eq("is_active", True)
        )
        if payload.integration_id:
            query = query.eq("id", payload.integration_id)
        elif payload.agent_id:
            query = query.eq("agent_id", payload.agent_id)
        resp = await query.limit(1).execute()
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WA INTEGRATIONS] test lookup failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Failed to load integration")

    if not resp.data:
        raise HTTPException(status_code=404, detail="integration not found")

    runtime = prepare_integration_for_runtime(resp.data[0]) or {}
    ok = bool(runtime.get("instance_id") and runtime.get("token") and runtime.get("identifier"))

    # NUNCA chama a Z-API. NUNCA retorna token.
    return {
        "success": ok,
        "dry_run": True,
        "message": (
            "Configuração local válida. Nenhuma mensagem foi enviada."
            if ok
            else "Configuração incompleta. Revise os campos."
        ),
    }
