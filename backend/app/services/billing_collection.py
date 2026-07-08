"""SPEC-023 P4 - rotina global de cobranca de boletos.

Este modulo NAO e um worker novo. Ele e uma especializacao do motor existente de
rotinas: enfileira portal_jobs, consolida evidencias e devolve o relatorio para
o routine_engine entregar pelo canal da rotina.
"""
from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

BILLING_KIND = "billing_collection"
DEFAULT_PORTAL_KEYS = ["allianz_corretor"]
DEFAULT_MESSAGE_TEMPLATE = (
    "Ola, {cliente_nome}. Identificamos uma parcela pendente do seu seguro "
    "com vencimento em {vencimento}, no valor de R$ {valor}. Segue o boleto para regularizacao."
)
TERMINAL_JOB_STATUSES = {"done", "needs_human", "failed"}


def _digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "sim"}


def _int_clamped(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _as_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def normalize_billing_config(config: Optional[Dict[str, Any]], delivery: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    raw = config if isinstance(config, dict) else {}
    delivery = delivery if isinstance(delivery, dict) else {}
    portals = _as_list(raw.get("portal_keys") or raw.get("selected_portals")) or DEFAULT_PORTAL_KEYS[:]
    send_mode = str(raw.get("send_mode") or "test").strip().lower()
    if send_mode not in {"test", "approval", "live", "none"}:
        send_mode = "test"
    test_number = _digits(raw.get("test_number") or delivery.get("number") or "")
    return {
        **raw,
        "kind": BILLING_KIND,
        "portal_keys": portals,
        "approval_required": bool(raw.get("approval_required", True)),
        "send_mode": send_mode,
        "test_number": test_number,
        "message_template": str(raw.get("message_template") or DEFAULT_MESSAGE_TEMPLATE).strip() or DEFAULT_MESSAGE_TEMPLATE,
        "max_boletos_por_execucao": _int_clamped(raw.get("max_boletos_por_execucao") or raw.get("max_boletos"), 10, 1, 50),
        "poll_timeout_seconds": _int_clamped(raw.get("poll_timeout_seconds"), 360, 30, 1800),
        "management_provider": str(raw.get("management_provider") or "infocap").strip().lower() or "infocap",
    }


def selected_portal_keys(config: Optional[Dict[str, Any]]) -> List[str]:
    return _as_list((config or {}).get("portal_keys")) or DEFAULT_PORTAL_KEYS[:]


def is_billing_routine(routine: Dict[str, Any]) -> bool:
    config = routine.get("config") if isinstance(routine, dict) else {}
    return isinstance(config, dict) and str(config.get("kind") or "").strip().lower() == BILLING_KIND


def customer_send_allowed(config: Dict[str, Any], env: Optional[Dict[str, str]] = None) -> bool:
    env = env if env is not None else os.environ
    cfg = normalize_billing_config(config)
    if cfg.get("send_mode") != "live":
        return False
    if cfg.get("approval_required"):
        return False
    return _truthy(env.get("BILLING_CUSTOMER_SEND_ENABLED"))


def build_customer_message(item: Dict[str, Any], template: str) -> str:
    valor = item.get("valor")
    valor_txt = f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if isinstance(valor, (int, float)) else str(valor or "")
    data = {
        "cliente_nome": item.get("cliente_nome") or "cliente",
        "vencimento": item.get("vencimento") or "",
        "valor": valor_txt,
        "apolice": item.get("apolice_susep") or item.get("apolice") or "",
        "recibo": item.get("recibo") or "",
        "portal": item.get("portal") or "",
    }
    try:
        return template.format(**data)
    except Exception:  # noqa: BLE001
        return DEFAULT_MESSAGE_TEMPLATE.format(**data)


def _client(supabase):
    return getattr(supabase, "client", supabase)


def _portal_account(client, company_id: str, portal_key: str) -> Optional[Dict[str, Any]]:
    res = (
        client.table("portal_accounts")
        .select("id, portal_key, account_label, username, health")
        .eq("company_id", company_id)
        .eq("portal_key", portal_key)
        .order("created_at", desc=False)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return dict(rows[0]) if rows else None


def _enqueue_job(client, routine: Dict[str, Any], portal_key: str, account: Dict[str, Any], cfg: Dict[str, Any]) -> Optional[str]:
    ins = client.table("portal_jobs").insert({
        "company_id": str(routine["company_id"]),
        "portal_key": portal_key,
        "journey": "cobranca_sweep",
        "account_id": account.get("id"),
        "params": {
            "max_boletos": cfg["max_boletos_por_execucao"],
            "download_boletos": True,
            "require_downloads": True,
            "source": "routine_engine",
            "routine_id": str(routine.get("id") or ""),
        },
        "status": "queued",
    }).execute()
    return str(ins.data[0]["id"]) if ins.data else None


async def _poll_job(client, job_id: str, timeout_seconds: int) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last: Dict[str, Any] = {"id": job_id, "status": "queued"}
    while time.monotonic() < deadline:
        res = (
            client.table("portal_jobs")
            .select("id, portal_key, journey, status, evidence, error, screenshots, finished_at")
            .eq("id", job_id)
            .limit(1)
            .execute()
        )
        if res.data:
            last = dict(res.data[0])
            if str(last.get("status")) in TERMINAL_JOB_STATUSES:
                return last
        await asyncio.sleep(5)
    return {**last, "status": "timeout", "error": "portal_job nao terminou dentro do tempo limite"}


def _extract_items(job: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence = job.get("evidence") if isinstance(job, dict) else {}
    if not isinstance(evidence, dict):
        return []
    items = evidence.get("inadimplentes")
    if not isinstance(items, list):
        captured = evidence.get("captured") if isinstance(evidence.get("captured"), dict) else {}
        items = captured.get("inadimplentes") if isinstance(captured, dict) else []
    out = []
    for item in items or []:
        if isinstance(item, dict):
            out.append({**item, "portal_job_id": job.get("id"), "portal": item.get("portal") or job.get("portal_key")})
    return out


def _extract_boletos(job: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence = job.get("evidence") if isinstance(job, dict) else {}
    if not isinstance(evidence, dict):
        return []
    boletos = evidence.get("boletos")
    if not isinstance(boletos, list):
        return []
    return [b for b in boletos if isinstance(b, dict)]


async def _resolve_customer_phone(company_id: str, cpf_cnpj: str, provider_key: str) -> Dict[str, Any]:
    doc = _digits(cpf_cnpj)
    if len(doc) not in (11, 14):
        return {"phone": "", "status": "missing_document"}
    try:
        from app.core.database import create_async_supabase_client
        from app.providers.policy_data_provider import get_policy_data_provider

        internal_key = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
        provider = get_policy_data_provider(provider_key)
        if provider is None or not internal_key:
            return {"phone": "", "status": "provider_unavailable"}
        db = await create_async_supabase_client()
        result = await provider.lookup(
            company_id=company_id,
            document=doc,
            db=db,
            internal_key=internal_key,
            unmasked=True,
        )
        phone = _digits((result or {}).get("client_phone"))
        return {"phone": phone, "status": (result or {}).get("status") or "unknown", "source": provider_key}
    except Exception as e:  # noqa: BLE001
        return {"phone": "", "status": f"provider_error:{type(e).__name__}"}


async def _attach_contacts(company_id: str, items: List[Dict[str, Any]], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for item in items:
        contact = await _resolve_customer_phone(company_id, str(item.get("cpf_cnpj") or ""), cfg["management_provider"])
        enriched.append({**item, "whatsapp": contact.get("phone") or "", "contact_status": contact.get("status")})
    return enriched


def _safe_items_for_payload(items: List[Dict[str, Any]], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    safe = []
    for item in items:
        safe.append({
            "portal": item.get("portal"),
            "portal_job_id": item.get("portal_job_id"),
            "cliente_nome": item.get("cliente_nome"),
            "cpf_cnpj": item.get("cpf_cnpj"),
            "whatsapp": item.get("whatsapp"),
            "contact_status": item.get("contact_status"),
            "apolice_susep": item.get("apolice_susep"),
            "recibo": item.get("recibo"),
            "vencimento": item.get("vencimento"),
            "valor": item.get("valor"),
            "message": build_customer_message(item, cfg["message_template"]),
        })
    return safe


def _create_approval_request(client, routine: Dict[str, Any], items: List[Dict[str, Any]], boletos: List[Dict[str, Any]], cfg: Dict[str, Any]) -> Optional[str]:
    if not items:
        return None
    try:
        ins = client.table("approval_requests").insert({
            "company_id": str(routine["company_id"]),
            "subject_type": "billing_collection",
            "subject_id": str(routine.get("id") or ""),
            "action_type": "send_billing_whatsapp",
            "status": "pending",
            "risk_level": "high",
            "preview": {
                "routine_name": routine.get("name"),
                "items_count": len(items),
                "boletos_count": len([b for b in boletos if b.get("ok")]),
                "send_mode": cfg.get("send_mode"),
                "approval_required": cfg.get("approval_required"),
            },
            "request_payload": {
                "routine_id": str(routine.get("id") or ""),
                "portal_keys": cfg.get("portal_keys"),
                "items": _safe_items_for_payload(items, cfg),
                "boletos": boletos,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            "requested_by_user_id": routine.get("created_by"),
        }).execute()
        return str(ins.data[0]["id"]) if ins.data else None
    except Exception:  # noqa: BLE001
        return None


def _format_report(
    *,
    routine: Dict[str, Any],
    cfg: Dict[str, Any],
    jobs: List[Dict[str, Any]],
    items: List[Dict[str, Any]],
    boletos: List[Dict[str, Any]],
    blockers: List[str],
    approval_id: Optional[str],
) -> str:
    ok_boletos = [b for b in boletos if b.get("ok")]
    lines = [
        f"Auxiliar de Cobranca - {routine.get('name') or 'Cobranca de boletos'}",
        f"Portais varridos: {', '.join(cfg.get('portal_keys') or [])}",
        f"Jobs: {len(jobs)} | inadimplentes: {len(items)} | boletos baixados: {len(ok_boletos)}",
    ]
    if approval_id:
        lines.append(f"Aprovacao pendente criada: {approval_id}")
    if cfg.get("send_mode") == "test":
        lines.append("Modo teste ativo: nenhuma mensagem foi enviada para cliente.")
    if blockers:
        lines.append("Bloqueios/avisos:")
        lines.extend([f"- {b}" for b in blockers[:10]])
    if items:
        lines.append("Clientes encontrados:")
        for item in items[:20]:
            valor = item.get("valor")
            valor_txt = f"R$ {valor:.2f}" if isinstance(valor, (int, float)) else str(valor or "valor nao informado")
            phone = item.get("whatsapp") or f"sem telefone ({item.get('contact_status') or 'n/a'})"
            lines.append(
                f"- {item.get('cliente_nome') or 'Cliente'} | CPF/CNPJ {item.get('cpf_cnpj') or '?'} | "
                f"vcto {item.get('vencimento') or '?'} | {valor_txt} | WhatsApp: {phone}"
            )
    else:
        lines.append("Nenhum inadimplente consolidado nesta execucao.")
    return "\n".join(lines)[:4000]


async def execute_billing_collection_routine(supabase, routine: Dict[str, Any]) -> str:
    client = _client(supabase)
    company_id = str(routine.get("company_id") or "")
    cfg = normalize_billing_config(routine.get("config"), routine.get("delivery"))
    blockers: List[str] = []
    job_ids: List[str] = []

    for portal_key in selected_portal_keys(cfg):
        try:
            account = await asyncio.to_thread(_portal_account, client, company_id, portal_key)
            if not account:
                blockers.append(f"portal {portal_key}: sem credencial conectada")
                continue
            job_id = await asyncio.to_thread(_enqueue_job, client, routine, portal_key, account, cfg)
            if job_id:
                job_ids.append(job_id)
            else:
                blockers.append(f"portal {portal_key}: falha ao enfileirar job")
        except Exception as e:  # noqa: BLE001
            blockers.append(f"portal {portal_key}: {type(e).__name__}")

    jobs: List[Dict[str, Any]] = []
    for job_id in job_ids:
        jobs.append(await _poll_job(client, job_id, int(cfg["poll_timeout_seconds"])))

    for job in jobs:
        status = str(job.get("status") or "")
        if status == "needs_human":
            blockers.append(f"portal {job.get('portal_key')}: precisa de humano ({(job.get('evidence') or {}).get('message') or 'revisao'})")
        if status in {"failed", "timeout"}:
            blockers.append(f"portal {job.get('portal_key')}: {status} {job.get('error') or ''}".strip())

    items: List[Dict[str, Any]] = []
    boletos: List[Dict[str, Any]] = []
    for job in jobs:
        items.extend(_extract_items(job))
        boletos.extend(_extract_boletos(job))

    items = await _attach_contacts(company_id, items, cfg) if items else []
    approval_id = None
    if items and cfg.get("approval_required"):
        approval_id = await asyncio.to_thread(_create_approval_request, client, routine, items, boletos, cfg)
        if not approval_id:
            blockers.append("nao consegui criar pedido de aprovacao")
    if items and not customer_send_allowed(cfg):
        blockers.append("envio ao cliente bloqueado por configuracao/gate de seguranca")

    return _format_report(
        routine=routine,
        cfg=cfg,
        jobs=jobs,
        items=items,
        boletos=boletos,
        blockers=blockers,
        approval_id=approval_id,
    )
