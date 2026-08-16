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


@router.get("/cobranca-capabilities")
async def cobranca_capabilities(
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    """Quais portais a Cobrança SABE varrer — derivado, nunca decorado.

    🔴 O defeito que isto corrige, medido em 16/08/2026:

        registry (`portais_com_cobranca()`) ...... 6 portais
        tela (`page.tsx:62` PORTAIS_COM_COBRANCA)  2 portais

    Tokio, Yelum, MAPFRE e Zurich tinham journey completa e testada, e apareciam
    como "não automatizado" para a corretora. Capacidade construída, paga e
    invisível — e nenhum teste guardava a sincronia, porque a tela era um array
    literal em TypeScript que ninguém comparava com o Python.

    A correção não é atualizar o array. É **apagar o array** e derivar.

    Duas verdades diferentes, e a distinção importa
    ===============================================
        `registry`  o que o CÓDIGO sabe fazer
        `deployed`  o que a IMAGEM NO AR sabe fazer

    Elas divergem de verdade: 📊 a P-149 registra a journey da MAPFRE existindo
    no repositório e **não** na imagem implantada — um job dela terminava em
    "journey desconhecida" com todos os testes verdes. Marcar a MAPFRE como
    pronta por causa do registry seria repetir a mentira em outro lugar.

    Por isso `operacional` é a INTERSEÇÃO, e é ela que a tela usa.

    Sem conseguir falar com o portal-worker, devolve `degraded` e **nenhum**
    portal como operacional. Preferir o silêncio ao otimismo: dizer "não
    consegui confirmar" custa uma tentativa; dizer "está pronto" sem estar custa
    um job que morre em produção.
    """
    _require_internal_key(x_key)

    registry: list[str] = []
    try:
        from portal_worker.journeys import portais_com_cobranca

        registry = list(portais_com_cobranca())
    except Exception as e:  # noqa: BLE001
        logger.warning("[PORTAL] registry indisponivel nesta imagem: %s", type(e).__name__)

    deployed: Optional[list[str]] = None
    degraded_reason = ""
    base = (os.getenv("PORTAL_WORKER_URL") or "").strip().rstrip("/")
    if base:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=4.0) as cli:
                r = await cli.get(f"{base}/health")
            if r.status_code == 200:
                corpo = r.json() if r.content else {}
                bruto = corpo.get("portais_com_cobranca")
                if isinstance(bruto, list):
                    deployed = [str(x) for x in bruto]
                else:
                    degraded_reason = "portal-worker antigo: /health sem portais_com_cobranca"
            else:
                degraded_reason = f"portal-worker respondeu {r.status_code}"
        except Exception as e:  # noqa: BLE001
            degraded_reason = f"portal-worker inacessivel ({type(e).__name__})"
    else:
        degraded_reason = "PORTAL_WORKER_URL nao configurada"

    if deployed is None:
        operacional: list[str] = []
    else:
        operacional = sorted(set(registry) & set(deployed))

    return {
        "registry": sorted(registry),
        "deployed": sorted(deployed) if deployed is not None else None,
        "operacional": operacional,
        "degraded": deployed is None,
        "degraded_reason": degraded_reason,
    }


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
