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
    "Ola {nome_segurado},\n"
    "Aqui e a {nome_atendente}, da {nome_corretora}, tudo bem?\n\n"
    "A Seguradora {nome_seguradora} informou que a parcela *{numero_parcela}* "
    "do seguro do *{item_segurado}* ainda esta pendente.\n"
    "Desta forma, a seguradora gerou um novo boleto para pagamento pra voce "
    "nao ficar sem cobertura, ok!?\n\n"
    "Qualquer duvida estou a disposicao.\n\n"
    "Segue o boleto abaixo.\n"
    "Apolice: *{numero_apolice}*"
)
TERMINAL_JOB_STATUSES = {"done", "needs_human", "failed"}
TEST_LINK_TTL_SECONDS = 7 * 24 * 60 * 60


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


def _first_text(*values: Any, default: str = "") -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return default


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
        "attendant_name": _first_text(raw.get("attendant_name"), raw.get("nome_atendente"), default="Even"),
        "brokerage_name": _first_text(raw.get("brokerage_name"), raw.get("nome_corretora"), default="sua corretora"),
        "insurer_name": _first_text(raw.get("insurer_name"), raw.get("nome_seguradora"), default="ALLIANZ"),
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


def test_send_number(config: Dict[str, Any], delivery: Optional[Dict[str, Any]] = None) -> str:
    cfg = normalize_billing_config(config, delivery)
    number = str(cfg.get("test_number") or "")
    if cfg.get("send_mode") != "test":
        return ""
    return number if len(number) >= 10 else ""


def _portal_insurer_name(item: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    explicit = _first_text(item.get("nome_seguradora"), item.get("seguradora"), item.get("insurer_name"))
    if explicit:
        return explicit
    if str(item.get("portal") or "").strip().lower() == "allianz_corretor":
        return "ALLIANZ"
    return _first_text(cfg.get("insurer_name"), default="seguradora")


def _insured_item_name(item: Dict[str, Any]) -> str:
    vehicle = item.get("vehicle") if isinstance(item.get("vehicle"), dict) else {}
    policy = item.get("policy") if isinstance(item.get("policy"), dict) else {}
    return _first_text(
        item.get("item_segurado"),
        item.get("veiculo"),
        vehicle.get("veiculo") if vehicle else "",
        item.get("bem"),
        item.get("risco"),
        item.get("ramo"),
        policy.get("ramo") if policy else "",
        item.get("modalidade"),
        default="seguro",
    )


class _MessageData(dict):
    def __missing__(self, key: str) -> str:
        return ""


def build_customer_message(item: Dict[str, Any], template: str, config: Optional[Dict[str, Any]] = None) -> str:
    cfg = normalize_billing_config(config or {})
    valor = item.get("valor")
    valor_txt = f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if isinstance(valor, (int, float)) else str(valor or "")
    segurado = _first_text(item.get("nome_segurado"), item.get("cliente_nome"), item.get("client_name"), default="cliente")
    apolice = _first_text(item.get("numero_apolice"), item.get("apolice_susep"), item.get("apolice"))
    parcela = _first_text(item.get("numero_parcela"), item.get("parcela"))
    data = {
        "cliente_nome": segurado,
        "nome_segurado": segurado,
        "nome_atendente": _first_text(cfg.get("attendant_name"), default="Even"),
        "nome_corretora": _first_text(cfg.get("brokerage_name"), default="sua corretora"),
        "nome_seguradora": _portal_insurer_name(item, cfg),
        "numero_parcela": parcela,
        "item_segurado": _insured_item_name(item),
        "numero_apolice": apolice,
        "vencimento": item.get("vencimento") or "",
        "valor": valor_txt,
        "apolice": apolice,
        "recibo": item.get("recibo") or "",
        "portal": item.get("portal") or "",
    }
    try:
        return template.format_map(_MessageData(data))
    except Exception:  # noqa: BLE001
        return DEFAULT_MESSAGE_TEMPLATE.format_map(_MessageData(data))


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


def _company_name(client, company_id: str) -> str:
    try:
        res = client.table("companies").select("company_name").eq("id", company_id).limit(1).execute()
        rows = res.data or []
        return str((rows[0] or {}).get("company_name") or "").strip() if rows else ""
    except Exception:  # noqa: BLE001
        return ""


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


async def _resolve_customer_phone(
    company_id: str,
    cpf_cnpj: str,
    provider_key: str,
    item: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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
        out = {"phone": _digits((result or {}).get("client_phone")), "status": (result or {}).get("status") or "unknown", "source": provider_key}
        vehicle_lookup = getattr(provider, "vehicle", None)
        policy_number = str((item or {}).get("apolice_susep") or (item or {}).get("apolice") or "").strip()
        if callable(vehicle_lookup):
            try:
                vehicle_result = await vehicle_lookup(
                    company_id=company_id,
                    document=doc,
                    policy_number=policy_number or None,
                    db=db,
                    internal_key=internal_key,
                )
                if isinstance(vehicle_result, dict) and vehicle_result.get("ok"):
                    vehicle = vehicle_result.get("vehicle") if isinstance(vehicle_result.get("vehicle"), dict) else {}
                    policy = vehicle_result.get("policy") if isinstance(vehicle_result.get("policy"), dict) else {}
                    client = vehicle_result.get("client") if isinstance(vehicle_result.get("client"), dict) else {}
                    if vehicle.get("veiculo"):
                        out["item_segurado"] = str(vehicle.get("veiculo") or "").strip()
                        out["vehicle"] = vehicle
                    insurer = policy.get("seguradora_abrev") or policy.get("seguradora")
                    if insurer:
                        out["seguradora"] = str(insurer).strip()
                    if client.get("telefone") and not out["phone"]:
                        out["phone"] = _digits(client.get("telefone"))
                    if client.get("nome"):
                        out["cliente_nome"] = str(client.get("nome") or "").strip()
            except Exception:  # noqa: BLE001
                pass
        return out
    except Exception as e:  # noqa: BLE001
        return {"phone": "", "status": f"provider_error:{type(e).__name__}"}


async def _attach_contacts(company_id: str, items: List[Dict[str, Any]], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for item in items:
        contact = await _resolve_customer_phone(company_id, str(item.get("cpf_cnpj") or ""), cfg["management_provider"], item)
        merged = {**item, "whatsapp": contact.get("phone") or "", "contact_status": contact.get("status")}
        for field in ("item_segurado", "vehicle", "seguradora", "cliente_nome"):
            if contact.get(field) and not merged.get(field):
                merged[field] = contact.get(field)
        enriched.append(merged)
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
            "parcela": item.get("parcela"),
            "item_segurado": _insured_item_name(item),
            "message": build_customer_message(item, cfg["message_template"], cfg),
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


def _find_whatsapp_integration(client, company_id: str) -> Optional[Dict[str, Any]]:
    res = (
        client.table("integrations")
        .select("*")
        .eq("company_id", company_id)
        .eq("is_active", True)
        .execute()
    )
    rows = [dict(r) for r in (res.data or [])]
    rank = {"auxiliary": 0, "attendance": 1}
    rows.sort(key=lambda r: rank.get(str(r.get("purpose") or ""), 2))
    return rows[0] if rows else None


def _signed_boleto_url(client, storage_path: Any) -> str:
    path = str(storage_path or "").strip().lstrip("/")
    if not path:
        return ""
    try:
        res = client.storage.from_("portal-evidence").create_signed_url(path, TEST_LINK_TTL_SECONDS)
        if isinstance(res, dict):
            return str(res.get("signedURL") or res.get("signedUrl") or res.get("signed_url") or "")
        data = getattr(res, "data", None)
        if isinstance(data, dict):
            return str(data.get("signedURL") or data.get("signedUrl") or data.get("signed_url") or "")
    except Exception:  # noqa: BLE001
        return ""
    return ""


def _boletos_by_recibo(boletos: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for boleto in boletos:
        recibo = str(boleto.get("recibo") or "").strip()
        if recibo and recibo not in out:
            out[recibo] = boleto
    return out


def _format_test_message(item: Dict[str, Any], cfg: Dict[str, Any], boleto: Optional[Dict[str, Any]], boleto_url: str) -> str:
    lines = [
        "[TESTE AutoBrokers - Auxiliar de Cobranca]",
        build_customer_message(item, cfg["message_template"], cfg),
    ]
    if boleto_url:
        lines.append(f"Boleto (link temporario): {boleto_url}")
    elif boleto:
        lines.append(f"Boleto: nao anexado nesta simulacao ({boleto.get('reason') or 'sem link disponivel'}).")
    else:
        lines.append("Boleto: nao baixado nesta execucao de teste.")
    lines.append("Esta mensagem foi enviada somente para o numero de teste configurado, nao para o cliente real.")
    return "\n\n".join(lines)


async def _send_test_messages(
    client,
    routine: Dict[str, Any],
    items: List[Dict[str, Any]],
    boletos: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    blockers: List[str],
) -> List[Dict[str, Any]]:
    number = test_send_number(cfg, routine.get("delivery"))
    if not number or not items:
        return []
    integration = await asyncio.to_thread(_find_whatsapp_integration, client, str(routine["company_id"]))
    if not integration:
        blockers.append("modo teste: corretora sem canal WhatsApp ativo para enviar a simulacao")
        return []

    from app.services.whatsapp_service import get_whatsapp_service

    by_recibo = _boletos_by_recibo(boletos)
    sent: List[Dict[str, Any]] = []
    for item in items[: int(cfg["max_boletos_por_execucao"])]:
        boleto = by_recibo.get(str(item.get("recibo") or "").strip())
        boleto_url = await asyncio.to_thread(_signed_boleto_url, client, boleto.get("storage_path") if boleto else "")
        text = _format_test_message(item, cfg, boleto, boleto_url)
        entry = {
            "cliente_nome": item.get("cliente_nome"),
            "recibo": item.get("recibo"),
            "to_last4": number[-4:],
            "boleto_link": bool(boleto_url),
            "ok": False,
        }
        try:
            ok = await asyncio.to_thread(get_whatsapp_service().send_message, number, text, integration)
            entry["ok"] = bool(ok)
        except Exception as e:  # noqa: BLE001
            entry["error"] = type(e).__name__
            blockers.append(f"modo teste: falha ao enviar simulacao para ...{number[-4:]} ({type(e).__name__})")
        sent.append(entry)
    return sent


def _format_report(
    *,
    routine: Dict[str, Any],
    cfg: Dict[str, Any],
    jobs: List[Dict[str, Any]],
    items: List[Dict[str, Any]],
    boletos: List[Dict[str, Any]],
    blockers: List[str],
    approval_id: Optional[str],
    test_sends: List[Dict[str, Any]],
) -> str:
    ok_boletos = [b for b in boletos if b.get("ok")]
    ok_test_sends = [s for s in test_sends if s.get("ok")]
    lines = [
        f"Auxiliar de Cobranca - {routine.get('name') or 'Cobranca de boletos'}",
        f"Portais varridos: {', '.join(cfg.get('portal_keys') or [])}",
        f"Jobs: {len(jobs)} | inadimplentes: {len(items)} | boletos baixados: {len(ok_boletos)}",
    ]
    if approval_id:
        lines.append(f"Aprovacao pendente criada: {approval_id}")
    if cfg.get("send_mode") == "test":
        if ok_test_sends:
            last4 = str(ok_test_sends[0].get("to_last4") or "????")
            lines.append(f"Modo teste ativo: {len(ok_test_sends)} simulacao(oes) enviada(s) para ...{last4}. Nenhum cliente real recebeu mensagem.")
        else:
            lines.append("Modo teste ativo: nenhum cliente real recebeu mensagem.")
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
    if cfg.get("brokerage_name") == "sua corretora" and company_id:
        name = await asyncio.to_thread(_company_name, client, company_id)
        if name:
            cfg["brokerage_name"] = name
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
    wants_approval = cfg.get("send_mode") == "approval" or (cfg.get("send_mode") == "live" and cfg.get("approval_required"))
    if items and wants_approval:
        approval_id = await asyncio.to_thread(_create_approval_request, client, routine, items, boletos, cfg)
        if not approval_id:
            blockers.append("nao consegui criar pedido de aprovacao")
    test_sends = await _send_test_messages(client, routine, items, boletos, cfg, blockers) if items else []
    if items and cfg.get("send_mode") == "approval":
        blockers.append("modo aprovacao: mensagens aguardam aprovacao antes de qualquer envio ao cliente")
    elif items and cfg.get("send_mode") == "none":
        blockers.append("modo somente relatorio: nenhuma mensagem sera enviada ao cliente")
    elif items and cfg.get("send_mode") == "live" and not customer_send_allowed(cfg):
        blockers.append("envio ao cliente bloqueado por configuracao/gate de seguranca")
    elif items and cfg.get("send_mode") == "live":
        blockers.append("envio direto ao cliente permanece desativado nesta fase de homologacao")

    return _format_report(
        routine=routine,
        cfg=cfg,
        jobs=jobs,
        items=items,
        boletos=boletos,
        blockers=blockers,
        approval_id=approval_id,
        test_sends=test_sends,
    )
