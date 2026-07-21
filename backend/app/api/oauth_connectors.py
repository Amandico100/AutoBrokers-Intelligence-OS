"""
OAuth Connectors store (C2-P2 frente 2) — grava tokens OAuth (Google Drive, Notion) na
conexão da CORRETORA (tenant_connections + Vault/Fernet). Modelo tenant-scoped (mesmo dos
conectores), NÃO o agent-scoped antigo. O fluxo OAuth (authorize/callback) roda no Next (web);
aqui só cifra o token e marca a conexão como connected. Segredo NUNCA volta/loga.
"""
import hmac
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.database import AsyncSupabaseClient, get_async_db
from app.services.encryption_service import get_encryption_service

logger = logging.getLogger(__name__)
router = APIRouter()

# slugs OAuth suportados nesta frente
OAUTH_SLUGS = {"google_drive", "notion", "google_calendar", "slack"}


def _require_internal_key(provided: Optional[str]) -> None:
    expected = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    if not expected:
        raise HTTPException(status_code=500, detail="Internal API key not configured")
    if not provided or not hmac.compare_digest(str(provided), str(expected)):
        raise HTTPException(status_code=401, detail="Unauthorized internal request")


class OAuthStorePayload(BaseModel):
    company_id: str
    slug: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    scope: Optional[str] = None
    account_label: Optional[str] = None
    name: Optional[str] = None
    # SPEC-044: conexão PESSOAL (padrão ChatGPT Enterprise) — NULL = da corretora.
    owner_user_id: Optional[str] = None


@router.post("/connectors/oauth/store")
async def store_oauth_token(
    payload: OAuthStorePayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    db: AsyncSupabaseClient = Depends(get_async_db),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    company_id = (payload.company_id or "").strip()
    slug = (payload.slug or "").strip()
    if not company_id or slug not in OAUTH_SLUGS:
        raise HTTPException(status_code=400, detail="company_id and a valid slug are required")
    if not payload.access_token:
        raise HTTPException(status_code=400, detail="access_token required")

    # template
    tpl_res = await db.client.table("connector_templates").select("id").eq("slug", slug).limit(1).execute()
    tpl = tpl_res.data[0] if tpl_res and tpl_res.data else None
    if not tpl:
        raise HTTPException(status_code=404, detail="connector_template not found")
    template_id = tpl["id"]

    # cifrar tokens (NUNCA texto puro / nunca logar)
    try:
        ciphertext = get_encryption_service().encrypt(json.dumps({
            "access_token": payload.access_token,
            "refresh_token": payload.refresh_token,
        }))
    except Exception as e:  # noqa: BLE001
        logger.error(f"[OAUTH STORE] encryption error: {e}")
        raise HTTPException(status_code=500, detail="encryption_failed") from e

    expires_at = None
    if payload.expires_in:
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(payload.expires_in))).isoformat()

    conn_config = {"scope": payload.scope, "account_label": payload.account_label, "expires_at": expires_at}
    now_iso = datetime.now(timezone.utc).isoformat()

    # SPEC-044 upsert por DONO: 1 conexão da CORRETORA (owner NULL) + 1 PESSOAL
    # por usuário para o mesmo template (índices parciais garantem no banco).
    owner = (payload.owner_user_id or "").strip() or None
    q = (
        db.client.table("tenant_connections")
        .select("id")
        .eq("company_id", company_id).eq("connector_template_id", template_id).neq("status", "archived")
    )
    q = q.eq("owner_user_id", owner) if owner else q.is_("owner_user_id", "null")
    existing_res = await q.order("created_at", desc=False).limit(1).execute()
    existing = existing_res.data[0] if existing_res and existing_res.data else None

    fields = {
        "encrypted_secret_ref": ciphertext,
        "connection_config": conn_config,
        "status": "connected",
        "health_status": "healthy",
        "last_checked_at": now_iso,
        "metadata": {"configured_via": "oauth", "provider": slug,
                     "ownership": "personal" if owner else "company"},
        "updated_at": now_iso,
    }
    if existing:
        conn_id = existing["id"]
        await db.client.table("tenant_connections").update(fields).eq("id", conn_id).eq("company_id", company_id).execute()
    else:
        ins = {**fields, "company_id": company_id, "connector_template_id": template_id,
               "owner_user_id": owner,
               "name": payload.name or (f"{slug} — pessoal" if owner else f"{slug} — corretora")}
        ins_res = await db.client.table("tenant_connections").insert(ins).execute()
        conn_id = ins_res.data[0]["id"] if ins_res and ins_res.data else None

    logger.info(f"[OAUTH STORE] company={company_id} slug={slug} connection={conn_id} "
                f"owner={'personal' if owner else 'company'} status=connected")
    return {"ok": True, "connection_id": conn_id, "status": "connected", "slug": slug,
            "ownership": "personal" if owner else "company"}
