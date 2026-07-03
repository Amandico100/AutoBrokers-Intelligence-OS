"""Canal WhatsApp da corretora — setup Evolution + QR + status (SPEC-017 P1.2).

Endpoints internos (chave interna Next↔Backend, mesmo padrão do InfoCap):
  POST /api/whatsapp-channel/setup   — garante instância Evolution da corretora,
                                       gera token de webhook e configura o webhook.
  GET  /api/whatsapp-channel/qr      — QR code (base64) para conectar no dashboard.
  GET  /api/whatsapp-channel/status  — estado da conexão (instância + integração).

Plataforma Evolution (global, EasyPanel): EVOLUTION_BASE_URL + EVOLUTION_API_KEY.
Instância por corretora: `ab-<8 primeiros do company_id>`. O token plaintext do
webhook aparece UMA vez (na URL configurada na instância); no banco só o hash.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.database import get_supabase_client
from app.services.whatsapp.channel_security import (
    build_webhook_url,
    new_webhook_credentials,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_TIMEOUT = 20.0


def _require_internal_key(provided: Optional[str]) -> None:
    expected = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    if not expected or not provided or provided != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


def _evolution_platform() -> Dict[str, str]:
    base_url = (os.getenv("EVOLUTION_BASE_URL") or "").rstrip("/")
    api_key = os.getenv("EVOLUTION_API_KEY") or ""
    if not base_url or not api_key:
        raise HTTPException(status_code=503, detail="evolution_not_configured")
    return {"base_url": base_url, "api_key": api_key}


def _instance_name(company_id: str) -> str:
    return f"ab-{str(company_id).replace('-', '')[:12]}"


def _public_backend_url() -> str:
    return (os.getenv("PUBLIC_BACKEND_URL") or os.getenv("BACKEND_PUBLIC_URL") or "").rstrip("/")


class ChannelSetupPayload(BaseModel):
    company_id: str
    agent_id: Optional[str] = None
    alert_number: Optional[str] = None  # S17-3: destino do alerta de desconexão


@router.post("/api/whatsapp-channel/setup")
async def whatsapp_channel_setup(
    payload: ChannelSetupPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    company_id = (payload.company_id or "").strip()
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id required")
    platform = _evolution_platform()
    public_url = _public_backend_url()
    if not public_url:
        raise HTTPException(status_code=503, detail="public_backend_url_not_configured")

    instance = _instance_name(company_id)
    token, token_hash, token_prefix = new_webhook_credentials()
    webhook_url = build_webhook_url(public_url, "evolution", token)

    headers = {"apikey": platform["api_key"], "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=_TIMEOUT, base_url=platform["base_url"]) as client:
        # 1) Garante a instância (idempotente: 403/409 = já existe).
        create = await client.post(
            "/instance/create",
            headers=headers,
            json={"instanceName": instance, "qrcode": True, "integration": "WHATSAPP-BAILEYS"},
        )
        if create.status_code >= 400 and create.status_code not in (403, 409):
            logger.error(f"[WA CHANNEL] instance create failed http={create.status_code}")
            raise HTTPException(status_code=502, detail="evolution_instance_create_failed")

        # 2) Configura o webhook da instância para a NOSSA rota com token.
        webhook_body = {
            "webhook": {
                "enabled": True,
                "url": webhook_url,
                "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"],
                "byEvents": False,
                "base64": False,
            }
        }
        wh = await client.post(f"/webhook/set/{instance}", headers=headers, json=webhook_body)
        if wh.status_code >= 400:
            # fallback formato flat (versões antigas do Evolution)
            wh2 = await client.post(
                f"/webhook/set/{instance}",
                headers=headers,
                json={"enabled": True, "url": webhook_url, "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]},
            )
            if wh2.status_code >= 400:
                logger.error(f"[WA CHANNEL] webhook set failed http={wh.status_code}/{wh2.status_code}")
                raise HTTPException(status_code=502, detail="evolution_webhook_set_failed")

    # 3) Upsert da integração (hash do token; plaintext NUNCA persiste).
    supabase = get_supabase_client()

    def _resolve_attendant_agent_id() -> Optional[str]:
        """SPEC-017 P2: sem agent_id explícito, vincula o ATENDENTE da corretora
        (role attendance) — nunca o Core — para o canal do segurado."""
        if payload.agent_id:
            return payload.agent_id
        try:
            res = (
                supabase.client.table("agents")
                .select("id, is_active")
                .eq("company_id", company_id)
                .eq("agent_role", "attendance")
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            if res.data:
                return str(res.data[0]["id"])
            # fallback: atendente existe mas está inativo — ainda assim é o correto
            res2 = (
                supabase.client.table("agents")
                .select("id")
                .eq("company_id", company_id)
                .eq("agent_role", "attendance")
                .limit(1)
                .execute()
            )
            return str(res2.data[0]["id"]) if res2.data else None
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[WA CHANNEL] attendant agent lookup failed: {type(e).__name__}")
            return None

    attendant_agent_id = _resolve_attendant_agent_id()

    def _upsert() -> None:
        record = {
            "company_id": company_id,
            "type": "whatsapp",
            "provider": "evolution",
            "base_url": platform["base_url"],
            "instance_id": instance,
            "token": platform["api_key"],
            "webhook_token_hash": token_hash,
            "webhook_token_prefix": token_prefix,
            "alert_target": {"number": payload.alert_number} if payload.alert_number else None,
            "channel_status": "connecting",
            "is_active": True,
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
        }
        if attendant_agent_id:
            record["agent_id"] = attendant_agent_id
        existing = (
            supabase.client.table("integrations")
            .select("id")
            .eq("company_id", company_id)
            .eq("provider", "evolution")
            .eq("instance_id", instance)
            .limit(1)
            .execute()
        )
        if existing.data:
            supabase.client.table("integrations").update(record).eq("id", existing.data[0]["id"]).execute()
        else:
            supabase.client.table("integrations").insert(record).execute()

    await asyncio.to_thread(_upsert)
    logger.info(f"[WA CHANNEL] setup ok instance={instance} token_prefix={token_prefix}")
    return {"ok": True, "instance": instance, "webhook_token_prefix": token_prefix, "status": "connecting"}


@router.get("/api/whatsapp-channel/qr")
async def whatsapp_channel_qr(
    company_id: str,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    platform = _evolution_platform()
    instance = _instance_name(company_id)
    headers = {"apikey": platform["api_key"]}
    async with httpx.AsyncClient(timeout=_TIMEOUT, base_url=platform["base_url"]) as client:
        res = await client.get(f"/instance/connect/{instance}", headers=headers)
        if res.status_code >= 400:
            raise HTTPException(status_code=502, detail="evolution_qr_failed")
        data = res.json() if res.content else {}
    qr = data.get("base64") or (data.get("qrcode") or {}).get("base64") or data.get("code")
    return {"ok": bool(qr), "instance": instance, "qr_base64": qr, "raw_state": data.get("state")}


@router.get("/api/whatsapp-channel/status")
async def whatsapp_channel_status(
    company_id: str,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    platform = _evolution_platform()
    instance = _instance_name(company_id)
    headers = {"apikey": platform["api_key"]}
    state = "unknown"
    async with httpx.AsyncClient(timeout=_TIMEOUT, base_url=platform["base_url"]) as client:
        res = await client.get(f"/instance/connectionState/{instance}", headers=headers)
        if res.status_code < 400 and res.content:
            data = res.json()
            inner = data.get("instance") if isinstance(data.get("instance"), dict) else data
            state = str(inner.get("state") or inner.get("connectionStatus") or "unknown").lower()
    return {"ok": True, "instance": instance, "state": state, "connected": state in ("open", "connected")}
