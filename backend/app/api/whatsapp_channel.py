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


def _instance_name(company_id: str, purpose: str = "attendance") -> str:
    """S17-12 multi-número: uma instância Evolution POR PROPÓSITO por corretora.
    'attendance' mantém o nome curto (compat); demais ganham sufixo."""
    base = f"ab-{str(company_id).replace('-', '')[:12]}"
    p = str(purpose or "attendance").strip().lower()
    if p in ("", "attendance"):
        return base
    suffix = "".join(ch for ch in p if ch.isalnum())[:10] or "aux"
    return f"{base}-{suffix}"


def _public_backend_url() -> str:
    return (os.getenv("PUBLIC_BACKEND_URL") or os.getenv("BACKEND_PUBLIC_URL") or "").rstrip("/")


class ChannelSetupPayload(BaseModel):
    company_id: str
    agent_id: Optional[str] = None
    alert_number: Optional[str] = None  # S17-3: destino do alerta de desconexão
    purpose: str = "attendance"  # S17-12: multi-número por corretora (attendance | auxiliary:<slug> | dispatch)


@router.get("/api/whatsapp-channel/diagnostics")
async def whatsapp_channel_diagnostics(
    company_id: str,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    """Diagnóstico transparente do canal (SPEC-017): mostra EXATAMENTE o que
    falta/quebrou, sem expor segredos. Usado pelo card do dashboard em erro."""
    _require_internal_key(x_autobrokers_internal_key)
    base_url = (os.getenv("EVOLUTION_BASE_URL") or "").rstrip("/")
    api_key = os.getenv("EVOLUTION_API_KEY") or ""
    public_url = _public_backend_url()
    out: Dict[str, Any] = {
        "evolution_base_url_set": bool(base_url),
        "evolution_api_key_set": bool(api_key),
        "public_backend_url_set": bool(public_url),
        "evolution_reachable": False,
        "evolution_http_status": None,
        "instance": _instance_name(company_id),
        "instance_state": None,
        "error": None,
    }
    if not base_url or not api_key:
        out["error"] = "envs_ausentes"
        return out
    headers = {"apikey": api_key}
    try:
        async with httpx.AsyncClient(timeout=10.0, base_url=base_url) as client:
            root = await client.get("/", headers=headers)
            out["evolution_http_status"] = root.status_code
            out["evolution_reachable"] = root.status_code < 500
            try:
                info = root.json() if root.content else {}
                out["evolution_version"] = str(info.get("version") or "")[:20]
            except Exception:  # noqa: BLE001
                pass
            state_res = await client.get(f"/instance/connectionState/{out['instance']}", headers=headers)
            if state_res.status_code < 400 and state_res.content:
                data = state_res.json()
                inner = data.get("instance") if isinstance(data.get("instance"), dict) else data
                out["instance_state"] = str(inner.get("state") or inner.get("connectionStatus") or "")[:30]
            else:
                out["instance_state"] = f"http_{state_res.status_code}"
    except httpx.HTTPError as e:
        out["error"] = f"evolution_unreachable:{type(e).__name__}"

    # Sem linha em integrations o webhook NÃO roteia — o diagnóstico tem que
    # gritar isso (foi o que escondeu o canal mudo por 2 dias).
    try:
        from app.core.database import get_supabase_client

        supabase = get_supabase_client()

        def _row():
            return (
                supabase.client.table("integrations")
                .select("id, agent_id, is_active, webhook_token_prefix")
                .eq("company_id", company_id)
                .eq("provider", "evolution")
                .eq("instance_id", out["instance"])
                .limit(1)
                .execute()
            )

        res = await asyncio.to_thread(_row)
        row = res.data[0] if res.data else None
        out["integration_row"] = bool(row)
        out["integration_agent_bound"] = bool(row and row.get("agent_id"))
        if not row:
            out["error"] = out["error"] or "integracao_ausente_no_banco"
    except Exception as e:  # noqa: BLE001
        out["integration_row"] = None
        logger.warning(f"[WA CHANNEL] diagnostics row check failed: {type(e).__name__}")
    return out


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

    instance = _instance_name(company_id, payload.purpose)
    token, token_hash, token_prefix = new_webhook_credentials()
    webhook_url = build_webhook_url(public_url, "evolution", token)

    def _safe_snippet(res: httpx.Response) -> str:
        try:
            return (res.text or "")[:120].replace("\n", " ")
        except Exception:  # noqa: BLE001
            return ""

    headers = {"apikey": platform["api_key"], "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, base_url=platform["base_url"]) as client:
            # 1) Garante a instância (idempotente: 403/409 = já existe).
            create = await client.post(
                "/instance/create",
                headers=headers,
                json={
                    "instanceName": instance,
                    "qrcode": True,
                    "integration": "WHATSAPP-BAILEYS",
                    # Cinto e suspensório (v2.3.x): webhook já na criação.
                    "webhook": {
                        "url": webhook_url,
                        "byEvents": False,
                        "base64": True,  # F1: midia decodificada no proprio webhook
                        "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"],
                    },
                },
            )
            if create.status_code >= 400 and create.status_code not in (403, 409):
                logger.error(f"[WA CHANNEL] instance create failed http={create.status_code} body={_safe_snippet(create)}")
                raise HTTPException(
                    status_code=502,
                    detail=f"evolution_instance_create_failed:http_{create.status_code}:{_safe_snippet(create)}",
                )

            # 2) Configura o webhook da instância para a NOSSA rota com token.
            webhook_body = {
                "webhook": {
                    "enabled": True,
                    "url": webhook_url,
                    "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"],
                    "byEvents": False,
                    "base64": True,  # F1: midia decodificada no proprio webhook
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
                    logger.error(f"[WA CHANNEL] webhook set failed http={wh.status_code}/{wh2.status_code} body={_safe_snippet(wh2)}")
                    raise HTTPException(
                        status_code=502,
                        detail=f"evolution_webhook_set_failed:http_{wh.status_code}/{wh2.status_code}:{_safe_snippet(wh2)}",
                    )
    except httpx.HTTPError as e:
        logger.error(f"[WA CHANNEL] evolution unreachable: {type(e).__name__}")
        raise HTTPException(status_code=502, detail=f"evolution_unreachable:{type(e).__name__}") from e

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
            # NOT NULL no schema; telefone real só existe após parear — a
            # instância identifica o canal até lá.
            "identifier": instance,
            "purpose": str(payload.purpose or "attendance").strip().lower(),
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

    # FAIL-LOUD: sem a linha em integrations o webhook não roteia NADA — se o
    # banco recusar (coluna/constraint), o setup TEM que falhar visível, nunca
    # deixar a instância de pé sem rota (bug que escondeu o canal por 2 dias).
    try:
        await asyncio.to_thread(_upsert)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WA CHANNEL] integração NÃO gravada: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Instância criada, mas a integração não foi gravada no banco ({type(e).__name__}). O canal NÃO vai responder até corrigir.",
        )
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
    qr = data.get("base64") or (data.get("qrcode") or {}).get("base64")
    qr_text = data.get("code") or (data.get("qrcode") or {}).get("code")
    # v2.3.x: base64 é a imagem; 'code' é o TEXTO do QR (não renderizável como img).
    return {
        "ok": bool(qr or qr_text),
        "instance": instance,
        "qr_base64": qr,
        "qr_text": qr_text if not qr else None,
        "raw_state": data.get("state"),
    }


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
