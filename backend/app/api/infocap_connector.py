"""
InfoCap Connector — Secret Storage (42I2.0C).

Secret Flow seguro (mesmo padrão do WhatsApp 39A4.2): recebe credenciais InfoCap
APENAS server-side (chave interna Next↔Backend), cifra com EncryptionService
(Fernet) e grava o ciphertext em public.tenant_connections.encrypted_secret_ref.
NUNCA retorna/loga login/senha/ciphertext. NÃO faz chamada real ao InfoCap.
"""
import hmac
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

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

    # 4. Atualizar conexão: ref cifrada + base_url (com fallback GLOBAL) + TESTE de auth real.
    prev_config = conn.get("connection_config") if isinstance(conn.get("connection_config"), dict) else {}
    new_config = dict(prev_config)
    effective_base = base_url or new_config.get("base_url") or settings.INFOCAP_BASE_URL or ""
    if effective_base:
        new_config["base_url"] = effective_base
    base_url_ok = bool(effective_base)

    # Teste de autenticação REAL (sem afirmar "conectado" sem prova).
    status, health = "configuring", "unknown"
    if base_url_ok:
        status, health, _ = await _infocap_auth_test(effective_base.rstrip("/"), username, password)

    update_fields: Dict[str, Any] = {
        "encrypted_secret_ref": ciphertext,
        "connection_config": new_config,
        "status": status,
        "health_status": health,
        "last_checked_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {"configured_via": "infocap_secret_flow", "safe_secret_flow": True},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.client.table("tenant_connections").update(update_fields).eq("id", connection_id).eq(
        "company_id", company_id
    ).execute()

    logger.info(
        f"[INFOCAP SECRET] stored company={company_id} connection={connection_id} "
        f"base_url_set={base_url_ok} status={status} health={health}"
    )

    return {
        "ok": True,
        "provider": "infocap",
        "status": status,
        "health_status": health,
        "base_url_configured": base_url_ok,
        "secret_ref_present": True,
        "connected": status == "connected",
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
    unmasked: bool = False  # Core/corretor interno: dados completos (CPF/nome/nº)


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


# Campos crus de documento/CPF e nome (usados no modo interno/desmascarado do Core).
_DOC_KEYS = ["cpf_cnpj", "cpf", "cnpj", "documento", "doc", "cpfcnpj", "cgccpf", "ni"]
_NAME_KEYS = ["cliente", "nome", "name", "razao_social", "segurado", "nome_cliente"]
_POLNUM_KEYS = ["numapo", "apolice", "nosnum", "numero", "num_apolice"]


def _sanitize_match(record: Dict[str, Any], unmasked: bool = False) -> Dict[str, Any]:
    cancelado = record.get("cancelado")
    status = _first_str(record, ["sit_acompanhamento_txt", "status", "situacao", "renovacao_situacao"])
    if not status and cancelado is not None:
        status = "cancelado" if cancelado in (True, 1, "1", "S", "s") else "ativo"
    policy_number = _first_str(record, _POLNUM_KEYS)
    name = _first_str(record, _NAME_KEYS)
    out = {
        "policy_ref": _first_str(record, ["codcli", "codigo", "id", "nosnum"]) or "infocap-match",
        "insurer_key": _first_str(record, ["seguradora_abrev", "cia", "codcia", "seguradora"]),
        "product": _first_str(record, ["ramo_abrev", "ramo", "codram", "produto", "descricao"]),
        "line_kind": None,
        "policy_status": status,
        "masked_policy_number": _mask_tail(policy_number),
        "holder_name_masked": _mask_name(name),
    }
    if unmasked:  # Core/corretor interno: dados completos (dono da informação)
        out["policy_number"] = policy_number
        out["holder_name"] = name
        out["document"] = _first_str(record, _DOC_KEYS)
    return out


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


def _sanitize_policy(doc: Dict[str, Any], unmasked: bool = False) -> Dict[str, Any]:
    """Normaliza uma apólice/documento. unmasked=True (Core/corretor) → dados completos."""
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
    policy_number = _first_str(doc, _POLNUM_KEYS)
    name = _first_str(doc, _NAME_KEYS)
    out = {
        "policy_ref": _first_str(doc, ["nosnum", "codigo", "codcli"]) or "infocap-doc",
        "insurer_key": _first_str(doc, ["seguradora_abrev", "seguradora", "cia", "codcia"]),
        "product": _first_str(doc, ["ramo_abrev", "ramo", "codram", "produto", "descricao"]),
        "line_kind": None,
        "policy_status": status,
        "masked_policy_number": _mask_tail(policy_number),
        "holder_name_masked": _mask_name(name),
        "valid_from": valid_from,
        "valid_to": valid_to,
        "active_now": ae["active_now"],
        "expired": ae["expired"],
        "coverages_count": len(coverages),
        "cancelled": is_cancel,
    }
    if unmasked:
        out["policy_number"] = policy_number
        out["holder_name"] = name
        out["document"] = _first_str(doc, _DOC_KEYS)
    return out


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
    unmasked = bool(getattr(payload, "unmasked", False))
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
                return _done({"ok": False, "status": "multiple_matches", "verification_status": "unverified", "http_status": http_status, "result_count": len(arr), "matches": [_sanitize_match(r, unmasked) for r in arr[:5]], "requires_human": True, "blockers": ["multiple_client_matches"]})

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
            policies = [_sanitize_policy(p, unmasked) for p in source_docs]
            documents_count = len(policies)
            now = datetime.now(timezone.utc).isoformat()
            # Flags de cliente reutilizadas em todos os desfechos (42I3A).
            client_flags = {
                "infocap_client_found": True,
                "client_ref_available": bool(client_ref),
                "client_ref_fields": [k for k in CLIENT_REF_KEYS if k in client_ref],
                "client_ref": client_ref,
            }
            if unmasked:  # Core/corretor: nome e CPF/CNPJ completos do cliente
                client_flags["client_name"] = _first_str(record, _NAME_KEYS)
                client_flags["client_document"] = _first_str(record, _DOC_KEYS)

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
    mode: Optional[str] = None
    policy_ref: Optional[str] = None


CONTRACT_STATUSES = {
    "found",
    "ambiguous_customer",
    "ambiguous_policy",
    "source_limited",
    "provider_auth_error",
    "provider_timeout",
    "unknown_shape",
    "document_evidence_required",
    "conflict_requires_human",
}

_CONTRACT_FORBIDDEN_KEYS = {
    "cpf_cnpj", "cpf", "cnpj", "documento", "doc", "cpfcnpj", "cgccpf", "ni",
    "cliente", "nome", "name", "razao_social", "segurado", "nome_cliente",
    "email", "emails", "telefone", "telefones", "celular", "endereco", "endereço",
    "logradouro", "bairro", "cep", "numapo", "apolice", "numero_apolice",
    "num_apolice", "nosnum", "codigo", "codcli", "codfil", "valor", "premio",
    "premio_liquido", "is", "lmi", "importancia_segurada", "limite",
    "token", "access_token", "auth_token", "authorization", "senha", "password",
    "secret", "payload", "raw", "raw_payload",
}

_ITEM_KEYS = {"itens", "items", "item", "bens"}
_COVERAGE_KEYS = {"coberturas", "coverages", "garantias", "verbas", "capitais"}
_PREMIUM_KEYS = {"premio", "premios", "premio_liquido", "premio_total"}
_DEDUCTIBLE_KEYS = {"franquia", "franquias", "deductibles", "dedutivel"}
_CLAUSE_KEYS = {"clausula", "clausulas", "condicoes", "condições", "conditions"}
_INSTALLMENT_KEYS = {"parcelas", "prestacoes", "prestações", "installments"}
_HISTORY_KEYS = {"historico", "histórico", "acompanhamento", "andamentos"}
_ASSISTANCE_KEYS = {"assistencia", "assistências", "assistencias", "assistance", "assistances"}


def _keynorm(key: Any) -> str:
    return str(key or "").strip().lower()


def _type_name(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return type(value).__name__


def _first_dict(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return next((item for item in value if isinstance(item, dict)), None)
    return None


def _safe_contract_shape(data: Any, *, max_depth: int = 3) -> Dict[str, Any]:
    """Retorna somente metadados estruturais do payload, nunca valores."""
    top_level_keys = list(data.keys())[:50] if isinstance(data, dict) else []
    nested_key_paths: set[str] = set()
    types_by_key: Dict[str, str] = {}
    list_keys: set[str] = set()
    counts: Dict[str, int] = {}
    sample_keys: Dict[str, List[str]] = {}
    all_keys: set[str] = set()
    array_key_detected: Optional[str] = None

    def visit(value: Any, path: str, depth: int) -> None:
        nonlocal array_key_detected
        if depth > max_depth:
            return
        if isinstance(value, dict):
            if path:
                nested_key_paths.add(path)
                types_by_key[path] = "object"
            for key, child in value.items():
                key_s = str(key)
                all_keys.add(key_s)
                child_path = f"{path}.{key_s}" if path else key_s
                nested_key_paths.add(child_path)
                types_by_key[child_path] = _type_name(child)
                visit(child, child_path, depth + 1)
            return
        if isinstance(value, list):
            if path:
                list_keys.add(path)
                counts[path] = len(value)
                types_by_key[path] = "array"
                if array_key_detected is None and any(isinstance(item, dict) for item in value):
                    array_key_detected = path
                first = _first_dict(value)
                if first:
                    sample_keys[path] = list(first.keys())[:50]
                    all_keys.update(str(k) for k in first.keys())
            if depth < max_depth:
                first = _first_dict(value)
                if first is not None:
                    visit(first, f"{path}[]" if path else "[]", depth + 1)

    visit(data, "", 0)
    structural = {
        "raw_type": "array" if isinstance(data, list) else "object" if isinstance(data, dict) else _type_name(data),
        "top_level_keys": sorted(top_level_keys),
        "nested_key_paths": sorted(nested_key_paths),
        "types_by_key": dict(sorted(types_by_key.items())),
        "list_keys": sorted(list_keys),
        "counts": dict(sorted(counts.items())),
        "sample_keys": {k: sorted(v) for k, v in sorted(sample_keys.items())},
        "array_key_detected": array_key_detected,
    }
    keyset = {_keynorm(k) for k in all_keys}
    list_keyset = {_keynorm(k.split(".")[-1].replace("[]", "")) for k in list_keys}
    detected = {
        "codigo_present": "codigo" in keyset,
        "codfil_present": "codfil" in keyset,
        "cpf_cnpj_present": "cpf_cnpj" in keyset,
        "nosnum_present": "nosnum" in keyset,
        "numapo_present": "numapo" in keyset,
        "items_present": bool(keyset & _ITEM_KEYS or list_keyset & _ITEM_KEYS),
        "coverages_present": bool(keyset & _COVERAGE_KEYS or list_keyset & _COVERAGE_KEYS),
        "premiums_present": bool(keyset & _PREMIUM_KEYS or list_keyset & _PREMIUM_KEYS),
        "deductibles_present": bool(keyset & _DEDUCTIBLE_KEYS or list_keyset & _DEDUCTIBLE_KEYS),
        "clauses_present": bool(keyset & _CLAUSE_KEYS or list_keyset & _CLAUSE_KEYS),
        "installments_present": bool(keyset & _INSTALLMENT_KEYS or list_keyset & _INSTALLMENT_KEYS),
        "history_present": bool(keyset & _HISTORY_KEYS or list_keyset & _HISTORY_KEYS),
        "assistance_present": bool(keyset & _ASSISTANCE_KEYS or list_keyset & _ASSISTANCE_KEYS),
    }
    hash_src = json.dumps(structural, sort_keys=True, ensure_ascii=True)
    return {
        **structural,
        "result_count": len(data) if isinstance(data, list) else len(_extract_array(data)),
        "detected_policy_fields": detected,
        "shape_hash": hashlib.sha256(hash_src.encode("utf-8")).hexdigest()[:16],
        "parse_status": "ok" if isinstance(data, (dict, list)) else "unknown_shape",
    }


def _select_unique_contract_candidate(candidates: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], str]:
    if len(candidates) == 1:
        candidate = candidates[0]
        if _first_str(candidate, ["codigo", "codcli"]):
            return candidate, "found"
        return None, "source_limited"
    if len(candidates) > 1:
        return None, "ambiguous_customer"
    return None, "source_limited"


def _select_policy_locator(
    docs: List[Dict[str, Any]],
    *,
    codfil: Any,
    requested_policy_ref: Optional[str] = None,
) -> Tuple[Optional[Dict[str, str]], str]:
    requested = str(requested_policy_ref or "").strip()
    docs_with_nosnum = [doc for doc in docs if _first_str(doc, ["nosnum"])]
    if requested:
        matches = [doc for doc in docs_with_nosnum if _first_str(doc, ["nosnum"]) == requested]
        if len(matches) != 1:
            return None, "source_limited" if not matches else "ambiguous_policy"
        selected = matches[0]
    else:
        if len(docs_with_nosnum) == 0:
            return None, "source_limited"
        if len(docs_with_nosnum) > 1:
            return None, "ambiguous_policy"
        selected = docs_with_nosnum[0]
    nosnum = _first_str(selected, ["nosnum"])
    if not nosnum:
        return None, "source_limited"
    codfil_val = _first_str(selected, ["codfil"]) or str(codfil or "")
    return {"provider": "infocap", "codfil": str(codfil_val), "nosnum": str(nosnum)}, "found"


_CONTRACT_STRUCTURAL_KEYS = {
    "top_level_keys",
    "nested_key_paths",
    "types_by_key",
    "list_keys",
    "counts",
    "sample_keys",
    "detected_policy_fields",
}


def _sanitize_contract_output(value: Any, *, structural_context: bool = False) -> Any:
    """Defesa final: remove valores sensiveis de qualquer saida do contract probe."""
    if isinstance(value, list):
        return [_sanitize_contract_output(item, structural_context=structural_context) for item in value]
    if isinstance(value, dict):
        if isinstance(value.get("policy_locator"), dict):
            value = dict(value)
            value["policy_locator"] = {"provider": value["policy_locator"].get("provider", "infocap")}
        out: Dict[str, Any] = {}
        for key, child in value.items():
            key_norm = _keynorm(key)
            child_structural = structural_context or key_norm in _CONTRACT_STRUCTURAL_KEYS
            if not child_structural and key_norm in _CONTRACT_FORBIDDEN_KEYS:
                continue
            if key_norm == "policy_locator" and isinstance(child, dict):
                out[key] = {"provider": child.get("provider", "infocap")}
                continue
            out[key] = _sanitize_contract_output(child, structural_context=child_structural)
        return out
    return value


def _shape_probe_endpoint(
    logical_endpoint: str,
    http_status: Optional[int],
    data: Any = None,
    *,
    error_hint: Optional[str] = None,
) -> Dict[str, Any]:
    shape = _safe_contract_shape(data) if data is not None else _safe_contract_shape(None)
    return {
        "logical_endpoint": logical_endpoint,
        "method": "GET",
        "http_status": http_status,
        "ok": bool(http_status and http_status < 400 and not error_hint),
        "error_hint": error_hint,
        **shape,
    }


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


async def _contract_get(
    client: httpx.AsyncClient,
    path: str,
    params: Dict[str, Any],
    headers: Dict[str, str],
    logical_endpoint: str,
) -> Tuple[Dict[str, Any], Optional[Any], str]:
    try:
        res = await client.get(path, params=params, headers=headers)
    except httpx.TimeoutException:
        return _shape_probe_endpoint(logical_endpoint, None, None, error_hint="provider_timeout"), None, "provider_timeout"
    except httpx.HTTPError:
        return _shape_probe_endpoint(logical_endpoint, None, None, error_hint="network_error"), None, "provider_timeout"

    if res.status_code in (401, 403):
        return _shape_probe_endpoint(logical_endpoint, res.status_code, None, error_hint="auth_error"), None, "provider_auth_error"
    if res.status_code >= 400:
        return _shape_probe_endpoint(logical_endpoint, res.status_code, None, error_hint="provider_http_error"), None, "source_limited"

    try:
        data = res.json()
    except Exception:  # noqa: BLE001
        return _shape_probe_endpoint(logical_endpoint, res.status_code, None, error_hint="non_json_response"), None, "unknown_shape"
    return _shape_probe_endpoint(logical_endpoint, res.status_code, data), data, "found"


def _merge_detected_policy_fields(endpoints: List[Dict[str, Any]]) -> Dict[str, bool]:
    merged = {
        "codigo_present": False,
        "codfil_present": False,
        "cpf_cnpj_present": False,
        "nosnum_present": False,
        "numapo_present": False,
        "items_present": False,
        "coverages_present": False,
        "premiums_present": False,
        "deductibles_present": False,
        "clauses_present": False,
        "installments_present": False,
        "history_present": False,
        "assistance_present": False,
    }
    for endpoint in endpoints:
        fields = endpoint.get("detected_policy_fields")
        if not isinstance(fields, dict):
            continue
        for key in merged:
            merged[key] = merged[key] or fields.get(key) is True
    return merged


def _short_hash(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:12]


async def _run_policy_chain_contract_probe(
    *,
    client: httpx.AsyncClient,
    headers: Dict[str, str],
    config: Dict[str, Any],
    company_id: str,
    qtype: str,
    raw_query: str,
    digits: str,
    codfil: Any,
    requested_policy_ref: Optional[str],
    auth_status: Optional[int],
) -> Dict[str, Any]:
    cpf_search_path = config.get("infocap_cpf_search_path") or "/cliente_cpf"
    name_search_path = config.get("infocap_search_path") or "/lista_clientes"
    cliente_path = config.get("infocap_cliente_path") or "/cliente"
    ligacoes_path = config.get("infocap_ligacoes_path") or "/cliente_ligacoes"
    documento_path = config.get("infocap_documento_path") or "/documento"
    endpoints: List[Dict[str, Any]] = []
    candidate_count = 0
    document_count = 0
    policy_locator: Optional[Dict[str, str]] = None

    if qtype == "cpf":
        search_params = {"codfil": codfil, "cpf_cnpj": digits}
        search_endpoint = "initial_search.cliente_cpf"
        search_path = cpf_search_path
    else:
        search_params = {"texto": raw_query}
        search_endpoint = "initial_search.lista_clientes"
        search_path = name_search_path

    search_shape, search_data, status = await _contract_get(
        client, search_path, search_params, headers, search_endpoint
    )
    endpoints.append(search_shape)
    if status != "found":
        return _sanitize_contract_output({
            "ok": False,
            "provider": "infocap",
            "mode": "policy_chain_contract",
            "status": status,
            "auth_http_status": auth_status,
            "candidate_count": 0,
            "document_count": 0,
            "detected_policy_fields": _merge_detected_policy_fields(endpoints),
            "endpoints": endpoints,
        })

    candidates = _extract_array(search_data)
    candidate_count = len(candidates)
    candidate, status = _select_unique_contract_candidate(candidates)
    if status != "found" or not candidate:
        return _sanitize_contract_output({
            "ok": False,
            "provider": "infocap",
            "mode": "policy_chain_contract",
            "status": status,
            "auth_http_status": auth_status,
            "candidate_count": candidate_count,
            "document_count": 0,
            "detected_policy_fields": _merge_detected_policy_fields(endpoints),
            "endpoints": endpoints,
        })

    codigo_val = _first_str(candidate, ["codigo", "codcli"])
    codfil_val = _first_str(candidate, ["codfil"]) or str(codfil or "1")
    if not codigo_val:
        status = "source_limited"
        return _sanitize_contract_output({
            "ok": False,
            "provider": "infocap",
            "mode": "policy_chain_contract",
            "status": status,
            "auth_http_status": auth_status,
            "candidate_count": candidate_count,
            "document_count": 0,
            "detected_policy_fields": _merge_detected_policy_fields(endpoints),
            "endpoints": endpoints,
        })

    cliente_shape, _, status = await _contract_get(
        client,
        cliente_path,
        {"codfil": codfil_val, "codigo": codigo_val},
        headers,
        "customer_detail.cliente",
    )
    endpoints.append(cliente_shape)
    if status != "found":
        return _sanitize_contract_output({
            "ok": False,
            "provider": "infocap",
            "mode": "policy_chain_contract",
            "status": status,
            "auth_http_status": auth_status,
            "candidate_count": candidate_count,
            "document_count": 0,
            "detected_policy_fields": _merge_detected_policy_fields(endpoints),
            "endpoints": endpoints,
        })

    catalog_shape, catalog_data, status = await _contract_get(
        client,
        ligacoes_path,
        {"codigo": codigo_val},
        headers,
        "policy_catalog.cliente_ligacoes",
    )
    endpoints.append(catalog_shape)
    if status != "found":
        return _sanitize_contract_output({
            "ok": False,
            "provider": "infocap",
            "mode": "policy_chain_contract",
            "status": status,
            "auth_http_status": auth_status,
            "candidate_count": candidate_count,
            "document_count": 0,
            "detected_policy_fields": _merge_detected_policy_fields(endpoints),
            "endpoints": endpoints,
        })

    docs = _extract_documents(catalog_data)
    document_count = len(docs)
    policy_locator, status = _select_policy_locator(
        docs,
        codfil=codfil_val,
        requested_policy_ref=requested_policy_ref,
    )
    if status != "found" or not policy_locator:
        return _sanitize_contract_output({
            "ok": False,
            "provider": "infocap",
            "mode": "policy_chain_contract",
            "status": status,
            "auth_http_status": auth_status,
            "candidate_count": candidate_count,
            "document_count": document_count,
            "detected_policy_fields": _merge_detected_policy_fields(endpoints),
            "policy_locator": policy_locator,
            "endpoints": endpoints,
        })

    detail_shape, _, detail_status = await _contract_get(
        client,
        documento_path,
        {"codfil": policy_locator["codfil"], "nosnum": policy_locator["nosnum"]},
        headers,
        "policy_detail.documento",
    )
    endpoints.append(detail_shape)
    status = detail_status
    logger.info(
        f"[INFOCAP CONTRACT PROBE] company_hash={_short_hash(company_id)} "
        f"status={status} endpoints={len(endpoints)} candidates={candidate_count} docs={document_count}"
    )
    return _sanitize_contract_output({
        "ok": status == "found",
        "provider": "infocap",
        "mode": "policy_chain_contract",
        "status": status,
        "auth_http_status": auth_status,
        "candidate_count": candidate_count,
        "document_count": document_count,
        "detected_policy_fields": _merge_detected_policy_fields(endpoints),
        "policy_locator": policy_locator,
        "endpoints": endpoints,
    })


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
    mode = (payload.mode or "").strip().lower()
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

            if mode == "policy_chain_contract":
                if qtype == "cpf" and not digits:
                    raise HTTPException(status_code=400, detail="cpf query requires digits")
                if qtype != "cpf" and not raw_query:
                    raise HTTPException(status_code=400, detail="name query is required")
                return await _run_policy_chain_contract_probe(
                    client=client,
                    headers=headers,
                    config=config,
                    company_id=company_id,
                    qtype="cpf" if qtype == "cpf" else "name",
                    raw_query=raw_query,
                    digits=digits,
                    codfil=codfil,
                    requested_policy_ref=payload.policy_ref,
                    auth_status=auth_status,
                )

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
    unmasked: bool = False  # Core/corretor interno: dados completos


# Chaves candidatas de listas de cobertura/itens e de rótulos/valores (amplas — InfoCap varia o shape).
_COVERAGE_LIST_KEYS = (
    "itens", "coberturas", "garantias", "verbas", "capitais", "importancias", "bens",
    "ramos", "detalhes", "objetos", "clausulas", "componentes", "produtos_itens",
)
_COVERAGE_LABEL_KEYS = ("descricao", "cobertura", "garantia", "nome", "item", "ramo", "tipo", "bem", "clausula", "objeto", "titulo")
_COVERAGE_AMOUNT_KEYS = ("valor", "is", "importancia_segurada", "importancia", "limite", "limite_maximo_indenizacao", "lmi", "capital", "valor_is", "valor_segurado", "premio", "premio_liquido")


def _coverage_item_lists(doc: Dict[str, Any]) -> List[List[Dict[str, Any]]]:
    """Coleta listas de itens/coberturas: chaves conhecidas + qualquer lista de dicts com rótulo."""
    lists: List[List[Dict[str, Any]]] = []
    seen = set()
    for k in _COVERAGE_LIST_KEYS:
        v = doc.get(k)
        if isinstance(v, list) and any(isinstance(x, dict) for x in v):
            lists.append([x for x in v if isinstance(x, dict)]); seen.add(k)
    # fallback: qualquer lista de dicts (no topo) que tenha um campo de rótulo plausível
    for k, v in doc.items():
        if k in seen or not isinstance(v, list):
            continue
        dicts = [x for x in v if isinstance(x, dict)]
        if dicts and any(_first_str(d, list(_COVERAGE_LABEL_KEYS)) for d in dicts[:5]):
            lists.append(dicts)
    return lists


def _coverage_texts(doc: Dict[str, Any]) -> List[str]:
    """Coleta textos de descrição de ramo/itens/coberturas (sem PII)."""
    parts: List[str] = []
    for key in ("ramo", "ramo_abrev", "produto", "descricao", "tipo_seguro"):
        v = doc.get(key)
        if isinstance(v, str):
            parts.append(v)
    for items in _coverage_item_lists(doc):
        for it in items[:60]:
            for dk in _COVERAGE_LABEL_KEYS:
                dv = it.get(dk)
                if isinstance(dv, str):
                    parts.append(dv)
    return [p for p in parts if p]


def _coverage_sections(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Seções de cobertura (descrição + valor). Amplo: varre todas as listas de itens plausíveis."""
    out: List[Dict[str, Any]] = []
    for items in _coverage_item_lists(doc):
        for it in items[:60]:
            label = _first_str(it, list(_COVERAGE_LABEL_KEYS))
            amount = _first_str(it, list(_COVERAGE_AMOUNT_KEYS))
            if label:
                out.append({"label": label, "amount": amount})
    return out[:60]


def _signal(texts_joined: str, has_any_text: bool, pattern: "re.Pattern[str]") -> Optional[bool]:
    """True se houver match; False se há texto mas sem match; None se não há texto algum."""
    if not has_any_text:
        return None
    return bool(pattern.search(texts_joined))


def _build_evidence_pack(
    doc: Dict[str, Any], prefer_insurer: Optional[str], prefer_product: Optional[str], unmasked: bool = False
) -> Dict[str, Any]:
    """Monta o policy_evidence_pack a partir de um documento de detalhe. unmasked=True → dados completos (Core)."""
    base = _sanitize_policy(doc, unmasked)
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
        **({
            "policy_number": base.get("policy_number"),
            "holder_name": base.get("holder_name"),
            "document": base.get("document"),
        } if unmasked else {}),
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
    unmasked = bool(getattr(payload, "unmasked", False))
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
            pack = _build_evidence_pack(doc, prefer_insurer, prefer_product, unmasked)
            _log("found", extra=f" confidence={pack.get('confidence')}")
            return {
                "ok": True,
                "status": "found",
                "source": "infocap",
                "source_ref": "infocap:documento",
                "http_status": det.status_code,
                "policy": _sanitize_policy(doc, unmasked),
                "policy_evidence_pack": pack,
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        logger.error(f"[INFOCAP DETAIL] http error: {type(e).__name__}")
        _log("provider_error")
        return {"ok": False, "status": "provider_error", "source": "infocap", "blockers": ["network_error"]}


# ---------------------------------------------------------------------------
# Providers health (SPEC-014 C-FIX-1 G) — master/internal. Sem segredo: só presença
# de configuração para o Cockpit refletir a VERDADE (ex.: busca web operacional?).
# ---------------------------------------------------------------------------
@router.get("/health/providers")
async def providers_health(
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    return {
        "ok": True,
        "tavily_configured": bool(getattr(settings, "TAVILY_API_KEY", None)),
        "docling_configured": bool(getattr(settings, "DOCLING_SERVICE_URL", None)),
        "infocap_base_url_set": bool(getattr(settings, "INFOCAP_BASE_URL", None)),
    }


# ---------------------------------------------------------------------------
# Auth test real (C-FIX-2) — prova de conexão sem afirmar "connected" sem teste.
# Retorna (status, health, http_status). status ∈ connected|error|configuring.
# ---------------------------------------------------------------------------
AUTH_TEST_TIMEOUT_S = 8.0


async def _infocap_auth_test(base_url: str, email: str, senha: str, auth_path: str = "/login"):
    if not base_url or not email or not senha:
        return "configuring", "incomplete", None
    try:
        async with httpx.AsyncClient(timeout=AUTH_TEST_TIMEOUT_S, base_url=base_url) as client:
            res = await client.post(auth_path, json={"email": email, "senha": senha, "aplicacao": 0})
            if res.status_code in (401, 403):
                return "error", "invalid_credentials", res.status_code
            if res.status_code >= 400:
                return "configuring", "unavailable", res.status_code
            token = None
            try:
                token = _extract_token(res.json())
            except Exception:  # noqa: BLE001
                token = (res.text or "").strip() or None
            if not token:
                return "error", "invalid_credentials", res.status_code
            return "connected", "healthy", res.status_code
    except (httpx.TimeoutException, httpx.HTTPError):
        return "configuring", "unavailable", None


class InfocapTestPayload(BaseModel):
    company_id: str
    tenant_connection_id: str


@router.post("/attendance/connectors/infocap/test")
async def infocap_test(
    payload: InfocapTestPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    db: AsyncSupabaseClient = Depends(get_async_db),
) -> Dict[str, Any]:
    """Testa a conexão InfoCap usando o segredo JÁ salvo (não re-digita login/senha)."""
    _require_internal_key(x_autobrokers_internal_key)
    company_id = (payload.company_id or "").strip()
    connection_id = (payload.tenant_connection_id or "").strip()
    if not company_id or not connection_id:
        raise HTTPException(status_code=400, detail="company_id and tenant_connection_id are required")

    conn_res = (
        await db.client.table("tenant_connections")
        .select("id, company_id, connection_config, encrypted_secret_ref")
        .eq("id", connection_id).eq("company_id", company_id).limit(1).execute()
    )
    conn = conn_res.data[0] if conn_res and conn_res.data else None
    if not conn:
        return {"ok": False, "status": "error", "health": "not_found"}
    config = conn.get("connection_config") if isinstance(conn.get("connection_config"), dict) else {}
    base_url = (config.get("base_url") or settings.INFOCAP_BASE_URL or "").rstrip("/")
    cipher = conn.get("encrypted_secret_ref")
    if not cipher:
        await db.client.table("tenant_connections").update(
            {"status": "configuring", "health_status": "missing_credentials", "last_checked_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", connection_id).eq("company_id", company_id).execute()
        return {"ok": False, "status": "configuring", "health": "missing_credentials"}
    try:
        creds = json.loads(get_encryption_service().decrypt(cipher))
        email = creds.get("username") or creds.get("email")
        senha = creds.get("password") or creds.get("senha")
    except Exception:  # noqa: BLE001
        return {"ok": False, "status": "error", "health": "decrypt_error"}

    status, health, http_status = await _infocap_auth_test(base_url, email, senha)
    await db.client.table("tenant_connections").update(
        {"status": status, "health_status": health, "last_checked_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", connection_id).eq("company_id", company_id).execute()
    logger.info(f"[INFOCAP TEST] company={company_id} connection={connection_id} status={status} health={health}")
    return {"ok": status == "connected", "status": status, "health": health, "http_status": http_status}
