"""SPEC-020 — Portais: registro GLOBAL (URLs iguais p/ todas) + credenciais POR
CORRETORA (login/senha cifrados em portal_accounts). Multi-tenant: o company_id
vem da SESSÃO no proxy Next (nunca do cliente); cada corretora só vê/edita as
suas. Endpoints internos (chave Next<->backend X-AutoBrokers-Internal-Key)."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

from app.core.database import get_supabase_client
from app.services import portal_vault

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/portal", tags=["Portal"])


def _require_internal_key(provided: Optional[str]) -> None:
    expected = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    if not expected or provided != expected:
        raise HTTPException(status_code=401, detail="chave interna invalida")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/portals")
async def list_portals(x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    supa = get_supabase_client()
    res = supa.client.table("portals").select("*").eq("is_active", True).order("sort_order").execute()
    return {"portals": res.data or []}


@router.get("/credentials")
async def list_credentials(
    company_id: str,
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    _require_internal_key(x_key)
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id obrigatorio")
    supa = get_supabase_client()
    res = (
        supa.client.table("portal_accounts")
        .select("id, portal_key, account_label, username, health, updated_at, secret_encrypted")
        .eq("company_id", company_id)
        .execute()
    )
    out = []
    for r in res.data or []:
        # NUNCA devolve a senha — só se está configurada.
        out.append({
            "id": r["id"], "portal_key": r["portal_key"], "account_label": r.get("account_label"),
            "username": r.get("username"), "health": r.get("health"),
            "has_password": bool(r.get("secret_encrypted")), "updated_at": r.get("updated_at"),
        })
    return {"credentials": out}


@router.post("/credentials")
async def save_credential(
    request: Request,
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    _require_internal_key(x_key)
    body = await request.json()
    company_id = str(body.get("company_id") or "")
    portal_key = str(body.get("portal_key") or "")
    username = str(body.get("username") or "").strip()
    password = str(body.get("password") or "")
    label = str(body.get("account_label") or "principal")
    if not company_id or not portal_key or not username:
        raise HTTPException(status_code=400, detail="company_id, portal_key e username sao obrigatorios")

    supa = get_supabase_client()
    row = {
        "company_id": company_id, "portal_key": portal_key, "account_label": label,
        "username": username, "health": "unknown", "updated_at": _now(),
    }
    # Senha só é regravada se veio nova (edição de username não apaga a senha).
    if password:
        try:
            row["secret_encrypted"] = portal_vault.encrypt(password)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[PORTAL] cofre indisponivel: {type(e).__name__}")
            raise HTTPException(status_code=500, detail="cofre indisponivel — PORTAL_VAULT_KEY configurada no smith-api?")

    existing = (
        supa.client.table("portal_accounts").select("id")
        .eq("company_id", company_id).eq("portal_key", portal_key).eq("account_label", label)
        .limit(1).execute()
    )
    if existing.data:
        supa.client.table("portal_accounts").update(row).eq("id", existing.data[0]["id"]).execute()
    else:
        supa.client.table("portal_accounts").insert(row).execute()
    return {"ok": True}


@router.delete("/credentials")
async def delete_credential(
    company_id: str,
    portal_key: str,
    account_label: str = "principal",
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    _require_internal_key(x_key)
    supa = get_supabase_client()
    (
        supa.client.table("portal_accounts").delete()
        .eq("company_id", company_id).eq("portal_key", portal_key).eq("account_label", account_label)
        .execute()
    )
    return {"ok": True}
