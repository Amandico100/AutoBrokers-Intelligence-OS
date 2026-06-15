"""
InfoCap Connector — Secret Storage (42I2.0C).

Secret Flow seguro (mesmo padrão do WhatsApp 39A4.2): recebe credenciais InfoCap
APENAS server-side (chave interna Next↔Backend), cifra com EncryptionService
(Fernet) e grava o ciphertext em public.tenant_connections.encrypted_secret_ref.
NUNCA retorna/loga login/senha/ciphertext. NÃO faz chamada real ao InfoCap.
"""
import hmac
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.database import AsyncSupabaseClient, get_async_db
from app.services.encryption_service import get_encryption_service

logger = logging.getLogger(__name__)
router = APIRouter()

INFOCAP_SLUG = "infocap"


def _require_internal_key(provided: Optional[str]) -> None:
    """Exige a chave interna Next↔Backend (mesmo padrão do WhatsApp/Auxiliares)."""
    expected = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    if not expected:
        logger.error("[INFOCAP SECRET] Internal API key not configured")
        raise HTTPException(status_code=500, detail="Internal API key not configured")
    if not provided or not hmac.compare_digest(str(provided), str(expected)):
        raise HTTPException(status_code=401, detail="Unauthorized internal request")


class InfocapSecretPayload(BaseModel):
    company_id: str
    tenant_connection_id: str
    base_url: Optional[str] = None
    username: str
    password: str


@router.post("/attendance/connectors/infocap/secret")
async def store_infocap_secret(
    payload: InfocapSecretPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    db: AsyncSupabaseClient = Depends(get_async_db),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)

    company_id = (payload.company_id or "").strip()
    connection_id = (payload.tenant_connection_id or "").strip()
    username = (payload.username or "").strip()
    password = payload.password or ""
    base_url = (payload.base_url or "").strip()

    if not company_id or not connection_id:
        raise HTTPException(status_code=400, detail="company_id and tenant_connection_id are required")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password are required")
    if base_url and not re.match(r"^https?://", base_url, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="invalid base_url")

    # 1. Conexão pertence à empresa?
    conn_res = (
        await db.client.table("tenant_connections")
        .select("id, company_id, connector_template_id, connection_config")
        .eq("id", connection_id)
        .eq("company_id", company_id)
        .limit(1)
        .execute()
    )
    conn = conn_res.data[0] if conn_res and conn_res.data else None
    if not conn:
        raise HTTPException(status_code=404, detail="tenant_connection not found")

    # 2. É template InfoCap?
    tpl_res = (
        await db.client.table("connector_templates")
        .select("slug")
        .eq("id", conn.get("connector_template_id"))
        .limit(1)
        .execute()
    )
    tpl = tpl_res.data[0] if tpl_res and tpl_res.data else None
    if not tpl or tpl.get("slug") != INFOCAP_SLUG:
        raise HTTPException(status_code=400, detail="connection is not an InfoCap connector")

    # 3. Cifrar credenciais (NUNCA em texto puro; nunca logar)
    try:
        ciphertext = get_encryption_service().encrypt(
            json.dumps({"username": username, "password": password})
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"[INFOCAP SECRET] encryption error: {e}")
        raise HTTPException(status_code=500, detail="encryption_failed") from e

    # 4. Atualizar conexão: ref cifrada + base_url (não-secreto) + status connected
    prev_config = conn.get("connection_config") if isinstance(conn.get("connection_config"), dict) else {}
    new_config = dict(prev_config)
    if base_url:
        new_config["base_url"] = base_url
    base_url_ok = isinstance(new_config.get("base_url"), str) and len(new_config.get("base_url")) > 0

    update_fields: Dict[str, Any] = {
        "encrypted_secret_ref": ciphertext,
        "connection_config": new_config,
        "status": "connected" if base_url_ok else "configuring",
        "health_status": "unknown",
        "metadata": {"configured_via": "infocap_secret_flow", "safe_secret_flow": True},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.client.table("tenant_connections").update(update_fields).eq("id", connection_id).eq(
        "company_id", company_id
    ).execute()

    # Log sanitizado: só ids/flags, NUNCA login/senha/ciphertext
    logger.info(
        f"[INFOCAP SECRET] stored company={company_id} connection={connection_id} "
        f"base_url_set={base_url_ok} status={update_fields['status']}"
    )

    return {
        "ok": True,
        "provider": "infocap",
        "status": update_fields["status"],
        "base_url_configured": base_url_ok,
        "secret_ref_present": True,
        "ready_for_real_lookup": bool(base_url_ok),
    }


# ---------------------------------------------------------------------------
# Read-only Real Call (42I2.1) — CorpAPI (api.corpnuvem.com)
# Doc: login(email/senha/aplicacao) -> token; GET /lista_clientes?texto=...
# ---------------------------------------------------------------------------

LOOKUP_TIMEOUT_S = 12.0
TOKEN_FIELDS = ["token", "access_token", "jwt", "auth_token", "Authorization", "token_auth"]
ARRAY_KEYS = ["data", "clientes", "result", "results", "items", "registros", "rows", "lista"]


class InfocapLookupPayload(BaseModel):
    company_id: str
    tenant_connection_id: str
    document: Optional[str] = None
    name: Optional[str] = None


def _digits(s: Optional[str]) -> str:
    return re.sub(r"\D", "", s or "")


def _mask_tail(value: Optional[str], keep: int = 2) -> Optional[str]:
    d = _digits(value)
    if len(d) < keep:
        return None
    return f"****{d[-keep:]}"


def _mask_name(name: Optional[str]) -> Optional[str]:
    if not name or not isinstance(name, str):
        return None
    parts = [p for p in name.strip().split() if p]
    return " ".join(f"{p[0].upper()}***" for p in parts) or None


def _first_str(record: Dict[str, Any], keys: List[str]) -> Optional[str]:
    for k in keys:
        v = record.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, (int, float)):
            return str(v)
    return None


def _extract_token(data: Any) -> Optional[str]:
    if isinstance(data, str) and data.strip():
        return data.strip()
    if isinstance(data, dict):
        for k in TOKEN_FIELDS:
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        # token aninhado em data/result
        for k in ["data", "result"]:
            nested = data.get(k)
            if isinstance(nested, dict):
                t = _extract_token(nested)
                if t:
                    return t
    return None


def _extract_array(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        for k in ARRAY_KEYS:
            v = data.get(k)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
        # registro único
        if any(isinstance(val, (str, int, float)) for val in data.values()):
            return [data]
    return []


def _sanitize_match(record: Dict[str, Any]) -> Dict[str, Any]:
    cancelado = record.get("cancelado")
    status = _first_str(record, ["sit_acompanhamento_txt", "status", "situacao", "renovacao_situacao"])
    if not status and cancelado is not None:
        status = "cancelado" if cancelado in (True, 1, "1", "S", "s") else "ativo"
    return {
        "policy_ref": _first_str(record, ["codcli", "codigo", "id", "nosnum"]) or "infocap-match",
        "insurer_key": _first_str(record, ["seguradora_abrev", "cia", "codcia", "seguradora"]),
        "product": _first_str(record, ["ramo_abrev", "ramo", "codram", "produto", "descricao"]),
        "line_kind": None,
        "policy_status": status,
        "masked_policy_number": _mask_tail(
            _first_str(record, ["numapo", "apolice", "nosnum", "numero", "num_apolice"])
        ),
        "holder_name_masked": _mask_name(_first_str(record, ["cliente", "nome", "name", "razao_social"])),
    }


@router.post("/attendance/connectors/infocap/lookup")
async def infocap_lookup(
    payload: InfocapLookupPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    db: AsyncSupabaseClient = Depends(get_async_db),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    started = time.monotonic()

    company_id = (payload.company_id or "").strip()
    connection_id = (payload.tenant_connection_id or "").strip()
    if not company_id or not connection_id:
        raise HTTPException(status_code=400, detail="company_id and tenant_connection_id are required")

    # Conexão + template
    conn_res = (
        await db.client.table("tenant_connections")
        .select("id, company_id, connector_template_id, connection_config, encrypted_secret_ref, status")
        .eq("id", connection_id)
        .eq("company_id", company_id)
        .limit(1)
        .execute()
    )
    conn = conn_res.data[0] if conn_res and conn_res.data else None
    if not conn:
        return {"ok": False, "status": "blocked_not_configured", "source": "infocap", "blockers": ["connection_not_found"]}

    tpl_res = (
        await db.client.table("connector_templates").select("slug").eq("id", conn.get("connector_template_id")).limit(1).execute()
    )
    tpl = tpl_res.data[0] if tpl_res and tpl_res.data else None
    if not tpl or tpl.get("slug") != INFOCAP_SLUG:
        return {"ok": False, "status": "blocked_not_configured", "source": "infocap", "blockers": ["not_infocap_connector"]}

    config = conn.get("connection_config") if isinstance(conn.get("connection_config"), dict) else {}
    base_url = (config.get("base_url") or "").rstrip("/")
    cipher = conn.get("encrypted_secret_ref")
    if not base_url:
        return {"ok": False, "status": "blocked_not_configured", "source": "infocap", "blockers": ["missing_base_url"]}
    if not cipher:
        return {"ok": False, "status": "blocked_missing_credentials", "source": "infocap", "blockers": ["missing_credentials"]}

    # Decifrar credenciais (NUNCA logar)
    try:
        creds = json.loads(get_encryption_service().decrypt(cipher))
        email = creds.get("username") or creds.get("email")
        senha = creds.get("password") or creds.get("senha")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[INFOCAP LOOKUP] decrypt error: {e}")
        return {"ok": False, "status": "provider_error", "source": "infocap", "blockers": ["decrypt_error"]}
    if not email or not senha:
        return {"ok": False, "status": "blocked_missing_credentials", "source": "infocap", "blockers": ["incomplete_credentials"]}

    auth_path = config.get("infocap_auth_path") or "/login"
    # CorpAPI: busca por CPF/CNPJ é endpoint próprio (/busca_cpf?cpf_cnpj=); por nome é /lista_clientes?texto=
    cpf_search_path = config.get("infocap_cpf_search_path") or "/busca_cpf"
    cpf_search_param = config.get("infocap_cpf_search_param") or "cpf_cnpj"
    name_search_path = config.get("infocap_search_path") or "/lista_clientes"
    name_search_param = config.get("infocap_search_param") or "texto"
    extra_params_raw = config.get("infocap_search_extra_params")
    extra_params = extra_params_raw if isinstance(extra_params_raw, dict) else {}

    doc_digits = _digits(payload.document)
    name = (payload.name or "").strip()
    if doc_digits:
        query_strategy = "document_cpf"
        search_path = cpf_search_path
        search_param = cpf_search_param
        search_value: str = doc_digits
    elif name:
        query_strategy = "customer_name"
        search_path = name_search_path
        search_param = name_search_param
        search_value = name
    else:
        return {
            "ok": False, "status": "not_found", "source": "infocap", "provider": "infocap",
            "query_strategy": "fallback", "blockers": ["no_search_term"], "verification_status": "unverified",
        }

    diag = {
        "provider": "infocap",
        "query_strategy": query_strategy,
        "search_path": search_path,
        "search_param": search_param,
    }

    def _done(result: Dict[str, Any]) -> Dict[str, Any]:
        merged = {**diag, **result}
        dur = int((time.monotonic() - started) * 1000)
        logger.info(
            f"[INFOCAP LOOKUP] company={company_id} connection={connection_id} provider=infocap "
            f"status={merged.get('status')} strategy={query_strategy} search_path={search_path} "
            f"result_count={merged.get('result_count')} duration_ms={dur}"
        )
        return merged

    try:
        async with httpx.AsyncClient(timeout=LOOKUP_TIMEOUT_S, base_url=base_url) as client:
            # 1. Auth
            auth_res = await client.post(auth_path, json={"email": email, "senha": senha, "aplicacao": 0})
            if auth_res.status_code in (401, 403):
                return _done({"ok": False, "status": "auth_error", "verification_status": "unverified", "http_status": auth_res.status_code, "blockers": ["auth_rejected"]})
            if auth_res.status_code >= 400:
                return _done({"ok": False, "status": "provider_error", "verification_status": "unverified", "http_status": auth_res.status_code, "blockers": ["auth_http_error"]})
            token = None
            try:
                token = _extract_token(auth_res.json())
            except Exception:  # noqa: BLE001
                token = (auth_res.text or "").strip() or None
            if not token:
                return _done({"ok": False, "status": "auth_error", "verification_status": "unverified", "blockers": ["no_token_in_login_response"]})

            # 2. Search (read-only)
            headers = {"Authorization": token, "Content-Type": "application/json"}
            params = {search_param: search_value, **extra_params}
            search_res = await client.get(search_path, params=params, headers=headers)
            http_status = search_res.status_code
            if http_status == 404:
                return _done({"ok": False, "status": "not_found", "verification_status": "unverified", "http_status": 404, "result_count": 0, "blockers": []})
            if http_status in (401, 403):
                return _done({"ok": False, "status": "auth_error", "verification_status": "unverified", "http_status": http_status, "blockers": ["search_unauthorized"]})
            if http_status >= 400:
                return _done({"ok": False, "status": "provider_error", "verification_status": "unverified", "http_status": http_status, "blockers": ["search_http_error"]})

            try:
                arr = _extract_array(search_res.json())
            except Exception:  # noqa: BLE001
                arr = []
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        logger.error(f"[INFOCAP LOOKUP] http error: {type(e).__name__}")
        return _done({"ok": False, "status": "provider_error", "verification_status": "unverified", "blockers": ["network_error"]})

    if len(arr) == 0:
        return _done({"ok": False, "status": "not_found", "verification_status": "unverified", "http_status": http_status, "result_count": 0, "blockers": [], "notes": ["Nenhum resultado para o termo de busca."]})
    if len(arr) > 1:
        return _done({
            "ok": False,
            "status": "multiple_matches",
            "verification_status": "unverified",
            "http_status": http_status,
            "result_count": len(arr),
            "matches": [_sanitize_match(r) for r in arr[:5]],
            "requires_human": True,
            "blockers": ["multiple_matches"],
        })

    selected = _sanitize_match(arr[0])
    now = datetime.now(timezone.utc).isoformat()
    source_ref = f"infocap:{search_path.lstrip('/')}"
    return _done({
        "ok": True,
        "status": "found",
        "source_ref": source_ref,
        "http_status": http_status,
        "result_count": 1,
        "selected": selected,
        "matches": [selected],
        "verification_status": "verified_by_connector",
        "coverage_evidence": {
            "source": "infocap",
            "source_ref": source_ref,
            "verified_at": now,
            "verified_by": "connector",
            "confidence": "medium",
            "coverage_summary": "Segurado/apólice localizado(a) na InfoCap (consulta read-only).",
            "limitations": [
                "Confirmação read-only via conector; cobertura específica do serviço requer leitura detalhada da apólice.",
            ],
            "human_required": False,
        },
        "requires_human": False,
        "notes": ["Resultado real read-only via InfoCap (CorpAPI)."],
    })
