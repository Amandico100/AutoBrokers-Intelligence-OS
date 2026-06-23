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

from app.core.config import settings
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

LOOKUP_TIMEOUT_S = 8.0
TOKEN_FIELDS = ["token", "access_token", "jwt", "auth_token", "Authorization", "token_auth"]
ARRAY_KEYS = ["cliente", "clientes", "data", "result", "results", "items", "registros", "rows", "lista", "documentos"]
POLICY_NUMBER_KEYS = ["numapo", "nosnum", "apolice", "num_apolice", "numero_apolice"]
CLIENT_REF_KEYS = ["codfil", "codigo", "codcli"]


class InfocapLookupPayload(BaseModel):
    company_id: str
    tenant_connection_id: str
    document: Optional[str] = None
    name: Optional[str] = None
    prefer_insurer: Optional[str] = None
    prefer_product: Optional[str] = None


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
        # qualquer valor que seja lista de objetos (shape desconhecido)
        for v in data.values():
            if isinstance(v, list) and any(isinstance(r, dict) for r in v):
                return [r for r in v if isinstance(r, dict)]
        # registro único
        if any(isinstance(val, (str, int, float)) for val in data.values()):
            return [data]
    return []


def _format_doc(digits: str) -> Optional[str]:
    """CPF ddd.ddd.ddd-dd / CNPJ dd.ddd.ddd/dddd-dd, ou None."""
    if len(digits) == 11:
        return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"
    if len(digits) == 14:
        return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
    return None


def _shape(data: Any) -> Dict[str, Any]:
    """Diagnóstico de SHAPE (apenas NOMES de chaves/contagem; NUNCA valores)."""
    if isinstance(data, list):
        first = next((r for r in data if isinstance(r, dict)), None)
        return {
            "raw_type": "array",
            "result_count": len(data),
            "top_level_keys": [],
            "array_key_detected": None,
            "sample_keys": list(first.keys())[:30] if first else [],
        }
    if isinstance(data, dict):
        top_keys = list(data.keys())[:30]
        # procurar a chave cujo valor é lista de objetos
        array_key = None
        arr: List[Dict[str, Any]] = []
        for k in ARRAY_KEYS:
            v = data.get(k)
            if isinstance(v, list):
                array_key, arr = k, [r for r in v if isinstance(r, dict)]
                break
        if array_key is None:
            for k, v in data.items():
                if isinstance(v, list) and any(isinstance(r, dict) for r in v):
                    array_key, arr = k, [r for r in v if isinstance(r, dict)]
                    break
        if array_key is not None:
            first = arr[0] if arr else None
            return {
                "raw_type": "object",
                "result_count": len(arr),
                "top_level_keys": top_keys,
                "array_key_detected": array_key,
                "sample_keys": list(first.keys())[:30] if first else [],
            }
        # registro único
        scalar = any(isinstance(v, (str, int, float, bool)) for v in data.values())
        return {
            "raw_type": "object",
            "result_count": 1 if scalar else 0,
            "top_level_keys": top_keys,
            "array_key_detected": None,
            "sample_keys": top_keys if scalar else [],
        }
    if isinstance(data, str):
        return {"raw_type": "string", "result_count": 0, "top_level_keys": [], "array_key_detected": None, "sample_keys": []}
    return {"raw_type": "empty", "result_count": 0, "top_level_keys": [], "array_key_detected": None, "sample_keys": []}


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


def _extract_documents(data: Any) -> List[Dict[str, Any]]:
    """Extrai a lista de documentos/apólices (shape /cliente_ligacoes e /documento[s])."""
    if isinstance(data, dict):
        d = data.get("documentos")
        if isinstance(d, list):
            return [r for r in d if isinstance(r, dict)]
        if isinstance(d, dict):
            for k in ("documentos", "documento", "data", "lista", "rows"):
                v = d.get(k)
                if isinstance(v, list):
                    return [r for r in v if isinstance(r, dict)]
        dd = data.get("documento")
        if isinstance(dd, list):
            return [r for r in dd if isinstance(r, dict)]
        if isinstance(dd, dict):
            return [dd]
    return _extract_array(data)


_CANCEL_TRUTHY = {True, 1, "1", "t", "T", "true", "True", "s", "S", "sim", "Sim", "SIM"}


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    """Parse flexível de data (dd/mm/yyyy, yyyy-mm-dd, dd-mm-yyyy). None se falhar."""
    if not value or not isinstance(value, str):
        return None
    raw = value.strip()[:10]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _active_expired(
    valid_from: Optional[str], valid_to: Optional[str], cancelled: bool
) -> Dict[str, Optional[bool]]:
    """active_now / expired (True/False/None=unknown). Cancelado => não ativo."""
    now = datetime.now(timezone.utc)
    dt_from = _parse_date(valid_from)
    dt_to = _parse_date(valid_to)
    expired: Optional[bool] = None
    if dt_to is not None:
        expired = now.date() > dt_to.date()
    active: Optional[bool] = None
    if cancelled:
        active = False
    elif dt_to is not None:
        started = dt_from is None or now.date() >= dt_from.date()
        active = started and now.date() <= dt_to.date()
    return {"active_now": active, "expired": expired}


def _sanitize_policy(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza uma apólice/documento (sanitizado; sem PII crua, número mascarado)."""
    is_cancel = doc.get("cancelado") in _CANCEL_TRUTHY
    status = "cancelado" if is_cancel else (
        _first_str(doc, ["sit_acompanhamento_txt", "sit_renovacao_txt", "tipdoc_txt", "situacao", "status"]) or "ativo"
    )
    coverages = doc.get("itens") if isinstance(doc.get("itens"), list) else (
        doc.get("coberturas") if isinstance(doc.get("coberturas"), list) else []
    )
    valid_from = _first_str(doc, ["inivig", "datini", "inicio_vigencia"])
    valid_to = _first_str(doc, ["fimvig", "datfim", "fim_vigencia"])
    ae = _active_expired(valid_from, valid_to, is_cancel)
    return {
        "policy_ref": _first_str(doc, ["nosnum", "codigo", "codcli"]) or "infocap-doc",
        "insurer_key": _first_str(doc, ["seguradora_abrev", "seguradora", "cia", "codcia"]),
        "product": _first_str(doc, ["ramo_abrev", "ramo", "codram", "produto", "descricao"]),
        "line_kind": None,
        "policy_status": status,
        "masked_policy_number": _mask_tail(_first_str(doc, ["numapo", "apolice", "nosnum", "numero", "num_apolice"])),
        "holder_name_masked": _mask_name(_first_str(doc, ["cliente", "nome", "name", "razao_social"])),
        "valid_from": valid_from,
        "valid_to": valid_to,
        "active_now": ae["active_now"],
        "expired": ae["expired"],
        "coverages_count": len(coverages),
        "cancelled": is_cancel,
    }


def _policy_sort_key(policy: Dict[str, Any], prefer_insurer: Optional[str], prefer_product: Optional[str]):
    """Ordena: ativas/vigentes > não canceladas > fim mais futuro > match seguradora/produto."""
    active = policy.get("active_now")
    not_cancelled = not policy.get("cancelled")
    dt_to = _parse_date(policy.get("valid_to"))
    end_ord = dt_to.timestamp() if dt_to else 0.0
    insurer = (policy.get("insurer_key") or "").lower()
    product = (policy.get("product") or "").lower()
    insurer_match = bool(prefer_insurer and prefer_insurer.lower() in insurer)
    product_match = bool(prefer_product and prefer_product.lower() in product)
    # Maior tupla = melhor (reverse=True na ordenação).
    return (
        1 if active is True else 0,
        1 if not_cancelled else 0,
        end_ord,
        1 if insurer_match else 0,
        1 if product_match else 0,
    )


_COVERAGE_KEYWORDS = re.compile(r"assist|residencial|eletric|el[eé]tric", re.IGNORECASE)


def _coverage_keyword_hit(doc: Dict[str, Any]) -> bool:
    """Scan leve apenas em descrições de cobertura/ramo (sem PII)."""
    parts: List[str] = []
    for key in ("ramo", "ramo_abrev", "produto", "descricao"):
        v = doc.get(key)
        if isinstance(v, str):
            parts.append(v)
    for listkey in ("itens", "coberturas"):
        items = doc.get(listkey)
        if isinstance(items, list):
            for it in items[:20]:
                if isinstance(it, dict):
                    for dk in ("descricao", "cobertura", "nome", "item"):
                        dv = it.get(dk)
                        if isinstance(dv, str):
                            parts.append(dv)
    return bool(_COVERAGE_KEYWORDS.search(" ".join(parts)))


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
    base_url = (config.get("base_url") or settings.INFOCAP_BASE_URL or "").rstrip("/")
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
    # CorpAPI (42I2.1C): CPF/CNPJ via /cliente_cpf?codfil=1&cpf_cnpj=<digits> (array_key "cliente");
    # nome via /lista_clientes?texto= (array_key "clientes").
    cpf_search_path = config.get("infocap_cpf_search_path") or "/cliente_cpf"
    cpf_search_param = config.get("infocap_cpf_search_param") or "cpf_cnpj"
    name_search_path = config.get("infocap_search_path") or "/lista_clientes"
    name_search_param = config.get("infocap_search_param") or "texto"
    extra_params_raw = config.get("infocap_search_extra_params")
    codfil_default = config.get("infocap_codfil", 1)
    ligacoes_path = config.get("infocap_ligacoes_path") or "/cliente_ligacoes"
    documentos_path = config.get("infocap_documentos_path") or "/documentos"
    documento_path = config.get("infocap_documento_path") or "/documento"

    doc_digits = _digits(payload.document)
    name = (payload.name or "").strip()
    if doc_digits:
        query_strategy = "document_cpf"
        search_path = cpf_search_path
        search_param = cpf_search_param
        search_value: str = doc_digits
        extra_params = extra_params_raw if isinstance(extra_params_raw, dict) else {"codfil": codfil_default}
    elif name:
        query_strategy = "customer_name"
        search_path = name_search_path
        search_param = name_search_param
        search_value = name
        extra_params = extra_params_raw if isinstance(extra_params_raw, dict) else {}
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

            # 2. Search (read-only) — localizar CLIENTE
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

            if len(arr) == 0:
                return _done({"ok": False, "status": "not_found", "verification_status": "unverified", "http_status": http_status, "result_count": 0, "blockers": [], "notes": ["Nenhum resultado para o termo de busca."]})
            # Busca por NOME com vários clientes → desambiguação humana (nível cliente)
            if query_strategy == "customer_name" and len(arr) > 1:
                return _done({"ok": False, "status": "multiple_matches", "verification_status": "unverified", "http_status": http_status, "result_count": len(arr), "matches": [_sanitize_match(r) for r in arr[:5]], "requires_human": True, "blockers": ["multiple_client_matches"]})

            record = arr[0]
            codfil_val = record.get("codfil") or codfil_default
            codigo_val = _first_str(record, ["codigo", "codcli"])
            matched_by = "cpf" if query_strategy == "document_cpf" else "name"

            client_ref: Dict[str, Any] = {}
            for k in CLIENT_REF_KEYS:
                v = record.get(k)
                if isinstance(v, (str, int)) and str(v).strip():
                    client_ref[k] = v
            for k in ("ativo", "vigente"):
                if record.get(k) is not None:
                    rv = record.get(k)
                    client_ref[k] = bool(rv) if isinstance(rv, (bool, int)) else rv
            for k in ("cidade", "estado"):
                v = _first_str(record, [k])
                if v:
                    client_ref[k] = v

            # 3. Discovery read-only de apólices/documentos do cliente
            documents: List[Dict[str, Any]] = []
            if codigo_val:
                try:
                    lig = await client.get(ligacoes_path, params={"codigo": codigo_val}, headers=headers)
                    if lig.status_code < 400:
                        documents = _extract_documents(lig.json())
                except (httpx.TimeoutException, httpx.HTTPError):
                    pass
            if not documents and name:
                try:
                    ds = await client.get(documentos_path, params={"codfil": codfil_val, "texto": name}, headers=headers)
                    if ds.status_code < 400:
                        documents = _extract_documents(ds.json())
                except (httpx.TimeoutException, httpx.HTTPError):
                    pass

            # 4. Detalhe de até 3 documentos com nosnum (falhas parciais toleradas)
            detailed: List[Dict[str, Any]] = []
            for d in documents[:3]:
                nosnum = _first_str(d, ["nosnum"])
                if not nosnum:
                    detailed.append(d)
                    continue
                try:
                    det = await client.get(documento_path, params={"codfil": codfil_val, "nosnum": nosnum}, headers=headers)
                    if det.status_code < 400:
                        darr = _extract_documents(det.json())
                        detailed.append(darr[0] if darr else d)
                    else:
                        detailed.append(d)
                except (httpx.TimeoutException, httpx.HTTPError):
                    detailed.append(d)

            source_docs = detailed or documents
            policies = [_sanitize_policy(p) for p in source_docs]
            documents_count = len(policies)
            now = datetime.now(timezone.utc).isoformat()
            # Flags de cliente reutilizadas em todos os desfechos (42I3A).
            client_flags = {
                "infocap_client_found": True,
                "client_ref_available": bool(client_ref),
                "client_ref_fields": [k for k in CLIENT_REF_KEYS if k in client_ref],
                "client_ref": client_ref,
            }

            # Cliente sem documentos → client_found
            if documents_count == 0:
                return _done({
                    "ok": False,
                    "status": "client_found",
                    "verification_status": "unverified",
                    "http_status": http_status,
                    "result_count": 1,
                    **client_flags,
                    "documents_count": 0,
                    "matched_by": matched_by,
                    "next_possible_endpoints": ["/cliente_ligacoes", "/documentos", "/documento"],
                    "requires_human": False,
                    "blockers": [],
                    "notes": ["Cliente localizado na InfoCap, mas nenhum documento/apólice vinculado foi retornado."],
                })

            prefer_insurer = (payload.prefer_insurer or "").strip() or None
            prefer_product = (payload.prefer_product or "").strip() or None
            paired = list(zip(policies, source_docs))
            # Ordena por relevância (ativas/vigentes > não canceladas > fim futuro > preferência).
            paired.sort(key=lambda pr: _policy_sort_key(pr[0], prefer_insurer, prefer_product), reverse=True)
            active = [(p, raw) for p, raw in paired if not p.get("cancelled")]
            candidates = active if active else paired

            # Não auto-selecionar quando houver mais de uma apólice ATIVA.
            if len(candidates) > 1:
                return _done({
                    "ok": False,
                    "status": "multiple_matches",
                    "verification_status": "unverified",
                    "http_status": http_status,
                    "result_count": documents_count,
                    "documents_count": documents_count,
                    "matched_by": matched_by,
                    **client_flags,
                    "matches": [p for p, _ in paired[:5]],
                    "requires_human": True,
                    "blockers": ["multiple_policies"],
                    "notes": ["Cliente possui múltiplas apólices; selecionar manualmente."],
                })

            selected_policy, selected_raw = candidates[0]
            confidence = "high" if _coverage_keyword_hit(selected_raw) else "medium"
            return _done({
                "ok": True,
                "status": "found",
                "source_ref": "infocap:documento",
                "http_status": http_status,
                "result_count": 1,
                "documents_count": documents_count,
                "matched_by": matched_by,
                **client_flags,
                "selected": selected_policy,
                "matches": [selected_policy],
                "verification_status": "verified_by_connector",
                "coverage_evidence": {
                    "source": "infocap",
                    "source_ref": "infocap:documento",
                    "verified_at": now,
                    "verified_by": "connector",
                    "confidence": confidence,
                    "coverage_summary": "Apólice localizada na InfoCap; cobertura específica ainda depende da leitura dos detalhes/itens.",
                    "limitations": [
                        "Leitura read-only de metadados da apólice; coberturas/itens detalhados podem exigir leitura do documento (PDF).",
                    ],
                    "human_required": False,
                },
                "requires_human": False,
                "notes": ["Apólice localizada via InfoCap (cliente -> documentos -> detalhe)."],
            })
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        logger.error(f"[INFOCAP LOOKUP] http error: {type(e).__name__}")
        return _done({"ok": False, "status": "provider_error", "verification_status": "unverified", "blockers": ["network_error"]})


# ---------------------------------------------------------------------------
# Probe read-only (42I2.1B) — descobre endpoint/param/shape reais sem expor
# valores. Apenas diagnostico (nomes de chaves/contagens/status), nunca valores.
# ---------------------------------------------------------------------------

PROBE_TIMEOUT_S = 10.0


class InfocapProbePayload(BaseModel):
    company_id: str
    tenant_connection_id: str
    query_type: str = "cpf"  # cpf|name
    query: str
    codfil: Optional[int] = 1


def _status_hint(http_status: int) -> str:
    if http_status in (401, 403):
        return "auth_error"
    if http_status == 404:
        return "not_found"
    if http_status >= 400:
        return "provider_error"
    return "ok"


async def _probe_one(
    client: httpx.AsyncClient,
    path: str,
    params: Dict[str, Any],
    headers: Dict[str, str],
    masked_label: str,
) -> Dict[str, Any]:
    """Executa 1 GET read-only e devolve so diagnostico de shape (sem valores)."""
    try:
        res = await client.get(path, params=params, headers=headers)
    except (httpx.TimeoutException, httpx.HTTPError) as e:  # noqa: BLE001
        return {
            "endpoint": masked_label, "method": "GET", "http_status": None, "ok": False,
            "result_count": 0, "raw_type": "empty", "top_level_keys": [], "array_key_detected": None,
            "sample_keys": [], "status_hint": "provider_error", "error_hint": type(e).__name__,
        }
    hint = _status_hint(res.status_code)
    if res.status_code >= 400:
        return {
            "endpoint": masked_label, "method": "GET", "http_status": res.status_code, "ok": False,
            "result_count": 0, "raw_type": "empty", "top_level_keys": [], "array_key_detected": None,
            "sample_keys": [], "status_hint": hint, "error_hint": None,
        }
    try:
        shape = _shape(res.json())
    except Exception:  # noqa: BLE001
        return {
            "endpoint": masked_label, "method": "GET", "http_status": res.status_code, "ok": True,
            "result_count": 0, "raw_type": "string", "top_level_keys": [], "array_key_detected": None,
            "sample_keys": [], "status_hint": hint, "error_hint": "non_json_response",
        }
    return {
        "endpoint": masked_label, "method": "GET", "http_status": res.status_code, "ok": True,
        "status_hint": hint, "error_hint": None, **shape,
    }


@router.post("/attendance/connectors/infocap/probe")
async def infocap_probe(
    payload: InfocapProbePayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    db: AsyncSupabaseClient = Depends(get_async_db),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    started = time.monotonic()
    company_id = (payload.company_id or "").strip()
    connection_id = (payload.tenant_connection_id or "").strip()
    if not company_id or not connection_id:
        raise HTTPException(status_code=400, detail="company_id and tenant_connection_id are required")

    conn_res = (
        await db.client.table("tenant_connections")
        .select("id, company_id, connector_template_id, connection_config, encrypted_secret_ref")
        .eq("id", connection_id).eq("company_id", company_id).limit(1).execute()
    )
    conn = conn_res.data[0] if conn_res and conn_res.data else None
    if not conn:
        return {"ok": False, "status": "blocked_not_configured", "blockers": ["connection_not_found"], "probes": []}
    tpl_res = (
        await db.client.table("connector_templates").select("slug").eq("id", conn.get("connector_template_id")).limit(1).execute()
    )
    tpl = tpl_res.data[0] if tpl_res and tpl_res.data else None
    if not tpl or tpl.get("slug") != INFOCAP_SLUG:
        return {"ok": False, "status": "blocked_not_configured", "blockers": ["not_infocap_connector"], "probes": []}

    config = conn.get("connection_config") if isinstance(conn.get("connection_config"), dict) else {}
    base_url = (config.get("base_url") or settings.INFOCAP_BASE_URL or "").rstrip("/")
    cipher = conn.get("encrypted_secret_ref")
    if not base_url:
        return {"ok": False, "status": "blocked_not_configured", "blockers": ["missing_base_url"], "probes": []}
    if not cipher:
        return {"ok": False, "status": "blocked_missing_credentials", "blockers": ["missing_credentials"], "probes": []}
    try:
        creds = json.loads(get_encryption_service().decrypt(cipher))
        email = creds.get("username") or creds.get("email")
        senha = creds.get("password") or creds.get("senha")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[INFOCAP PROBE] decrypt error: {e}")
        return {"ok": False, "status": "provider_error", "blockers": ["decrypt_error"], "probes": []}

    auth_path = config.get("infocap_auth_path") or "/login"
    codfil = payload.codfil if payload.codfil is not None else 1
    qtype = (payload.query_type or "cpf").lower()
    raw_query = (payload.query or "").strip()
    digits = _digits(raw_query)
    formatted = _format_doc(digits) if digits else None

    probes: List[Dict[str, Any]] = []
    auth_status: Optional[int] = None
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_S, base_url=base_url) as client:
            auth_res = await client.post(auth_path, json={"email": email, "senha": senha, "aplicacao": 0})
            auth_status = auth_res.status_code
            if auth_res.status_code >= 400:
                return {
                    "ok": False,
                    "status": "auth_error" if auth_res.status_code in (401, 403) else "provider_error",
                    "auth_http_status": auth_res.status_code, "probes": [],
                }
            try:
                token = _extract_token(auth_res.json())
            except Exception:  # noqa: BLE001
                token = (auth_res.text or "").strip() or None
            if not token:
                return {
                    "ok": False, "status": "auth_error", "auth_http_status": auth_res.status_code,
                    "blockers": ["no_token_in_login_response"], "probes": [],
                }
            headers = {"Authorization": token, "Content-Type": "application/json"}

            targets: List[Dict[str, Any]] = []
            if qtype == "cpf" and digits:
                targets += [
                    {"path": "/busca_cpf", "params": {"cpf_cnpj": digits}, "label": "/busca_cpf?cpf_cnpj=***"},
                    {"path": "/cliente_cpf", "params": {"codfil": codfil, "cpf_cnpj": digits}, "label": "/cliente_cpf?codfil=N&cpf_cnpj=***"},
                    {"path": "/producao", "params": {"texto": digits}, "label": "/producao?texto=***(cpf)"},
                ]
                if formatted:
                    targets += [
                        {"path": "/busca_cpf", "params": {"cpf_cnpj": formatted}, "label": "/busca_cpf?cpf_cnpj=***(fmt)"},
                        {"path": "/cliente_cpf", "params": {"codfil": codfil, "cpf_cnpj": formatted}, "label": "/cliente_cpf?codfil=N&cpf_cnpj=***(fmt)"},
                    ]
            else:
                name = raw_query
                targets += [
                    {"path": "/lista_clientes", "params": {"texto": name}, "label": "/lista_clientes?texto=***(nome)"},
                    {"path": "/producao", "params": {"texto": name}, "label": "/producao?texto=***(nome)"},
                ]

            for t in targets:
                probes.append(await _probe_one(client, t["path"], t["params"], headers, t["label"]))
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        logger.error(f"[INFOCAP PROBE] http error: {type(e).__name__}")
        return {"ok": False, "status": "provider_error", "blockers": ["network_error"], "probes": probes}

    winner = next((p for p in probes if p.get("ok") and (p.get("result_count") or 0) > 0), None)
    dur = int((time.monotonic() - started) * 1000)
    for p in probes:
        logger.info(
            f"[INFOCAP PROBE] company={company_id} connection={connection_id} endpoint={p.get('endpoint')} "
            f"http={p.get('http_status')} count={p.get('result_count')}"
        )
    logger.info(f"[INFOCAP PROBE] company={company_id} auth_http={auth_status} winner={bool(winner)} duration_ms={dur}")

    return {
        "ok": True,
        "provider": "infocap",
        "auth_http_status": auth_status,
        "query_type": qtype,
        "winner_endpoint": winner.get("endpoint") if winner else None,
        "winner_array_key": winner.get("array_key_detected") if winner else None,
        "winner_sample_keys": winner.get("sample_keys") if winner else [],
        "probes": probes,
    }


# ---------------------------------------------------------------------------
# Policy Detail + Evidence Pack (42I3A) — carrega 1 apólice por nosnum e monta
# um pacote de evidência estruturado e sanitizado. NUNCA afirma cobertura sem
# itens/coberturas no documento. Sem PII crua; nome/numero mascarados.
# ---------------------------------------------------------------------------

_SIG_RESIDENTIAL = re.compile(r"residenc|resid[êe]ncia|im[oó]vel|casa|home|habita", re.IGNORECASE)
_SIG_ELECTRICIAN = re.compile(r"eletric|el[eé]tric|electr|eletricista", re.IGNORECASE)
_SIG_EMERGENCY = re.compile(r"assist|emerg[êe]nc|24h|24\s*horas|socorro|chaveiro|encanador", re.IGNORECASE)


class InfocapPolicyDetailPayload(BaseModel):
    company_id: str
    tenant_connection_id: str
    codfil: Optional[int] = None
    policy_ref: str


def _coverage_texts(doc: Dict[str, Any]) -> List[str]:
    """Coleta textos de descrição de ramo/itens/coberturas (sem PII)."""
    parts: List[str] = []
    for key in ("ramo", "ramo_abrev", "produto", "descricao", "tipo_seguro"):
        v = doc.get(key)
        if isinstance(v, str):
            parts.append(v)
    for listkey in ("itens", "coberturas"):
        items = doc.get(listkey)
        if isinstance(items, list):
            for it in items[:40]:
                if isinstance(it, dict):
                    for dk in ("descricao", "cobertura", "nome", "item", "ramo", "tipo"):
                        dv = it.get(dk)
                        if isinstance(dv, str):
                            parts.append(dv)
    return [p for p in parts if p]


def _coverage_sections(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Seções de cobertura sanitizadas (descrição + valor de cobertura, sem PII)."""
    out: List[Dict[str, Any]] = []
    for listkey in ("itens", "coberturas"):
        items = doc.get(listkey)
        if isinstance(items, list):
            for it in items[:40]:
                if not isinstance(it, dict):
                    continue
                label = _first_str(it, ["descricao", "cobertura", "nome", "item", "ramo", "tipo"])
                amount = _first_str(it, ["valor", "is", "importancia_segurada", "limite", "capital"])
                if label:
                    out.append({"label": label, "amount": amount})
    return out[:40]


def _signal(texts_joined: str, has_any_text: bool, pattern: "re.Pattern[str]") -> Optional[bool]:
    """True se houver match; False se há texto mas sem match; None se não há texto algum."""
    if not has_any_text:
        return None
    return bool(pattern.search(texts_joined))


def _build_evidence_pack(
    doc: Dict[str, Any], prefer_insurer: Optional[str], prefer_product: Optional[str]
) -> Dict[str, Any]:
    """Monta o policy_evidence_pack sanitizado a partir de um documento de detalhe."""
    base = _sanitize_policy(doc)
    texts = _coverage_texts(doc)
    joined = " ".join(texts)
    has_text = bool(texts)
    sections = _coverage_sections(doc)

    signals = {
        "residential": _signal(joined, has_text, _SIG_RESIDENTIAL),
        "electrician": _signal(joined, has_text, _SIG_ELECTRICIAN),
        "emergency_assistance": _signal(joined, has_text, _SIG_EMERGENCY),
    }
    any_signal = any(v is True for v in signals.values())
    cancelled = bool(base.get("cancelled"))

    # Confiança: high só com sinais positivos + apólice não cancelada + vigente.
    if cancelled or base.get("active_now") is False:
        confidence = "low"
    elif any_signal and (sections or base.get("coverages_count")):
        confidence = "high"
    elif sections or base.get("coverages_count"):
        confidence = "medium"
    else:
        confidence = "low"

    limitations: List[str] = []
    if not sections and not base.get("coverages_count"):
        limitations.append(
            "Documento não trouxe itens/coberturas detalhados; existência da apólice confirmada, cobertura específica não."
        )
    if cancelled:
        limitations.append("Apólice consta como cancelada.")
    if base.get("active_now") is False and not cancelled:
        limitations.append("Apólice fora do período de vigência atual.")
    human_required = cancelled or confidence == "low"

    return {
        "source": "infocap",
        "verified_by": "connector",
        "policy_found": True,
        "policy_selected": True,
        "policy_ref": base.get("policy_ref"),
        "masked_policy_number": base.get("masked_policy_number"),
        "insurer_detected": base.get("insurer_key"),
        "product_detected": base.get("product"),
        "line_kind_detected": base.get("line_kind"),
        "policy_status": base.get("policy_status"),
        "active_now": base.get("active_now"),
        "expired": base.get("expired"),
        "valid_from": base.get("valid_from"),
        "valid_to": base.get("valid_to"),
        "holder_name_masked": base.get("holder_name_masked"),
        "risk_address_summary_masked": _first_str(doc, ["cidade", "municipio", "estado", "uf"]),
        "object_summary": _first_str(doc, ["objeto", "bem", "descricao_objeto", "local_risco"]),
        "coverage_sections": sections,
        "coverages_count": base.get("coverages_count"),
        "cancelled": cancelled,
        "assistance_signals": signals,
        "confidence": confidence,
        "human_required": human_required,
        "limitations": limitations,
    }


@router.post("/attendance/connectors/infocap/policy-detail")
async def infocap_policy_detail(
    payload: InfocapPolicyDetailPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    db: AsyncSupabaseClient = Depends(get_async_db),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    started = time.monotonic()
    company_id = (payload.company_id or "").strip()
    connection_id = (payload.tenant_connection_id or "").strip()
    policy_ref = (payload.policy_ref or "").strip()
    if not company_id or not connection_id or not policy_ref:
        raise HTTPException(status_code=400, detail="company_id, tenant_connection_id and policy_ref are required")

    conn_res = (
        await db.client.table("tenant_connections")
        .select("id, company_id, connector_template_id, connection_config, encrypted_secret_ref")
        .eq("id", connection_id).eq("company_id", company_id).limit(1).execute()
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
    base_url = (config.get("base_url") or settings.INFOCAP_BASE_URL or "").rstrip("/")
    cipher = conn.get("encrypted_secret_ref")
    if not base_url:
        return {"ok": False, "status": "blocked_not_configured", "source": "infocap", "blockers": ["missing_base_url"]}
    if not cipher:
        return {"ok": False, "status": "blocked_missing_credentials", "source": "infocap", "blockers": ["missing_credentials"]}
    try:
        creds = json.loads(get_encryption_service().decrypt(cipher))
        email = creds.get("username") or creds.get("email")
        senha = creds.get("password") or creds.get("senha")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[INFOCAP DETAIL] decrypt error: {e}")
        return {"ok": False, "status": "provider_error", "source": "infocap", "blockers": ["decrypt_error"]}
    if not email or not senha:
        return {"ok": False, "status": "blocked_missing_credentials", "source": "infocap", "blockers": ["incomplete_credentials"]}

    auth_path = config.get("infocap_auth_path") or "/login"
    documento_path = config.get("infocap_documento_path") or "/documento"
    codfil = payload.codfil if payload.codfil is not None else config.get("infocap_codfil", 1)
    prefer_insurer = (config.get("infocap_prefer_insurer") or "").strip() or None
    prefer_product = (config.get("infocap_prefer_product") or "").strip() or None

    def _log(status: str, extra: str = "") -> None:
        dur = int((time.monotonic() - started) * 1000)
        logger.info(
            f"[INFOCAP DETAIL] company={company_id} connection={connection_id} endpoint={documento_path} "
            f"status={status} selected_policy_ref={policy_ref} duration_ms={dur}{extra}"
        )

    try:
        async with httpx.AsyncClient(timeout=LOOKUP_TIMEOUT_S, base_url=base_url) as client:
            auth_res = await client.post(auth_path, json={"email": email, "senha": senha, "aplicacao": 0})
            if auth_res.status_code in (401, 403):
                _log("auth_error")
                return {"ok": False, "status": "auth_error", "source": "infocap", "http_status": auth_res.status_code, "blockers": ["auth_rejected"]}
            if auth_res.status_code >= 400:
                _log("provider_error")
                return {"ok": False, "status": "provider_error", "source": "infocap", "http_status": auth_res.status_code, "blockers": ["auth_http_error"]}
            try:
                token = _extract_token(auth_res.json())
            except Exception:  # noqa: BLE001
                token = (auth_res.text or "").strip() or None
            if not token:
                _log("auth_error")
                return {"ok": False, "status": "auth_error", "source": "infocap", "blockers": ["no_token_in_login_response"]}

            headers = {"Authorization": token, "Content-Type": "application/json"}
            det = await client.get(documento_path, params={"codfil": codfil, "nosnum": policy_ref}, headers=headers)
            if det.status_code == 404:
                _log("not_found")
                return {"ok": False, "status": "not_found", "source": "infocap", "http_status": 404, "blockers": ["policy_not_found"]}
            if det.status_code in (401, 403):
                _log("auth_error")
                return {"ok": False, "status": "auth_error", "source": "infocap", "http_status": det.status_code, "blockers": ["detail_unauthorized"]}
            if det.status_code >= 400:
                _log("provider_error")
                return {"ok": False, "status": "provider_error", "source": "infocap", "http_status": det.status_code, "blockers": ["detail_http_error"]}
            try:
                docs = _extract_documents(det.json())
            except Exception:  # noqa: BLE001
                docs = []
            if not docs:
                _log("not_found")
                return {"ok": False, "status": "not_found", "source": "infocap", "http_status": det.status_code, "blockers": ["empty_detail"]}

            doc = docs[0]
            pack = _build_evidence_pack(doc, prefer_insurer, prefer_product)
            _log("found", extra=f" confidence={pack.get('confidence')}")
            return {
                "ok": True,
                "status": "found",
                "source": "infocap",
                "source_ref": "infocap:documento",
                "http_status": det.status_code,
                "policy": _sanitize_policy(doc),
                "policy_evidence_pack": pack,
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        logger.error(f"[INFOCAP DETAIL] http error: {type(e).__name__}")
        _log("provider_error")
        return {"ok": False, "status": "provider_error", "source": "infocap", "blockers": ["network_error"]}
