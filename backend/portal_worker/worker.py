"""Poll loop do portal-worker (SPEC-020 P1): pega portal_jobs 'queued', roda a
journey Playwright determinística e grava status/evidência. Sem Redis novo (poll
na tabela, mesmo padrão do routine_scheduler_loop). Gate PORTAL_REAL_ENABLED off:
em standby o worker sobe e responde /health mas NÃO executa job nenhum."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger("portal_worker")

POLL_SECONDS = int(os.getenv("PORTAL_POLL_SECONDS", "30"))


def portal_real_enabled() -> bool:
    return str(os.getenv("PORTAL_REAL_ENABLED", "false")).strip().lower() in ("1", "true", "yes", "on")


def _supabase():
    from supabase import create_client

    url = os.getenv("SUPABASE_URL") or ""
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    return create_client(url, key)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_identity(job: Dict[str, Any], account: Dict[str, Any]) -> Dict[str, str] | None:
    company_id = str(job.get("company_id") or account.get("company_id") or "").strip()
    portal_key = str(job.get("portal_key") or account.get("portal_key") or "").strip()
    account_label = str(account.get("account_label") or "default").strip() or "default"
    if not company_id or not portal_key:
        return None
    return {"company_id": company_id, "portal_key": portal_key, "account_label": account_label}


def _decode_session_blob(raw: str) -> Dict[str, Any]:
    data = json.loads(raw)
    if isinstance(data, dict) and isinstance(data.get("storage_state"), dict):
        session_storage = data.get("session_storage")
        return {
            "storage_state": data["storage_state"],
            "session_storage": session_storage if isinstance(session_storage, list) else [],
        }
    return {"storage_state": data if isinstance(data, dict) else None, "session_storage": []}


def _load_session_bundle(supa, job: Dict[str, Any], account: Dict[str, Any]) -> Dict[str, Any]:
    ident = _session_identity(job, account)
    if not ident:
        return {"storage_state": None, "session_storage": []}
    try:
        res = (
            supa.table("portal_sessions")
            .select("storage_state_encrypted, health")
            .eq("company_id", ident["company_id"])
            .eq("portal_key", ident["portal_key"])
            .eq("account_label", ident["account_label"])
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows or not rows[0].get("storage_state_encrypted"):
            return {"storage_state": None, "session_storage": []}
        from portal_worker import vault

        raw = vault.decrypt(rows[0]["storage_state_encrypted"])
        return _decode_session_blob(raw)
    except Exception as e:  # noqa: BLE001
        logger.warning("[PORTAL] falha ao carregar sessao persistida: %s", type(e).__name__)
        return {"storage_state": None, "session_storage": []}


def _load_session_state(supa, job: Dict[str, Any], account: Dict[str, Any]) -> Dict[str, Any] | None:
    state = _load_session_bundle(supa, job, account).get("storage_state")
    return state if isinstance(state, dict) else None


def _save_session_state(
    supa,
    job: Dict[str, Any],
    account: Dict[str, Any],
    storage_state: Dict[str, Any],
    session_storage: list | None = None,
) -> bool:
    ident = _session_identity(job, account)
    if not ident or not isinstance(storage_state, dict):
        return False
    try:
        from portal_worker import vault

        payload = {
            "version": 1,
            "storage_state": storage_state,
            "session_storage": session_storage if isinstance(session_storage, list) else [],
        }
        encrypted = vault.encrypt(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
        row = {
            **ident,
            "storage_state_encrypted": encrypted,
            "verified_at": _now(),
            "health": "ok",
        }
        (
            supa.table("portal_sessions")
            .upsert(row, on_conflict="company_id,portal_key,account_label")
            .execute()
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("[PORTAL] falha ao salvar sessao persistida: %s", type(e).__name__)
        return False


async def _capture_session_storage(page) -> list:
    try:
        data = await page.evaluate(
            """() => ({
              origin: window.location.origin,
              entries: Object.fromEntries(Object.entries(window.sessionStorage || {}))
            })"""
        )
        if not isinstance(data, dict):
            return []
        entries = data.get("entries")
        origin = str(data.get("origin") or "").strip()
        if not origin or not isinstance(entries, dict) or not entries:
            return []
        return [{"origin": origin, "entries": entries}]
    except Exception as e:  # noqa: BLE001
        logger.warning("[PORTAL] falha ao capturar sessionStorage: %s", type(e).__name__)
        return []


async def _restore_session_storage(context, session_storage: list) -> bool:
    restored = False
    for item in session_storage or []:
        if not isinstance(item, dict):
            continue
        origin = str(item.get("origin") or "").strip()
        entries = item.get("entries")
        if not origin or not isinstance(entries, dict):
            continue
        payload = json.dumps({"origin": origin, "entries": entries}, ensure_ascii=True)
        await context.add_init_script(
            """(() => {
              const payload = %s;
              if (window.location.origin !== payload.origin) return;
              for (const [key, value] of Object.entries(payload.entries || {})) {
                window.sessionStorage.setItem(key, String(value));
              }
            })();""" % payload
        )
        restored = True
    return restored


async def _run_job(supa, job: Dict[str, Any]) -> None:
    from portal_worker.journeys import get_journey

    job_id = job["id"]
    journey_fn = get_journey(str(job.get("portal_key")), str(job.get("journey")))
    if journey_fn is None:
        supa.table("portal_jobs").update({
            "status": "failed",
            "error": f"journey desconhecida: {job.get('portal_key')}.{job.get('journey')}",
            "finished_at": _now(),
        }).eq("id", job_id).execute()
        return

    params = dict(job.get("params") or {})
    # Credencial: se há account_id, decifra a senha do cofre (NUNCA em log/LLM).
    account_id = job.get("account_id")
    account_row: Dict[str, Any] | None = None
    if account_id:
        acc = (
            supa.table("portal_accounts")
            .select("username, secret_encrypted, account_label, portal_key, company_id")
            .eq("id", account_id)
            .limit(1)
            .execute()
        )
        if acc.data:
            account_row = dict(acc.data[0] or {})
            from portal_worker import vault

            params.setdefault("username", account_row.get("username") or "")
            enc = account_row.get("secret_encrypted")
            if enc:
                try:
                    params["password"] = vault.decrypt(enc)
                except Exception:  # noqa: BLE001
                    logger.error("[PORTAL] falha ao decifrar credencial da conta")

    evidence: Dict[str, Any] = {}
    from playwright.async_api import async_playwright

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context_kwargs: Dict[str, Any] = {"accept_downloads": True}
            session_storage: list = []
            if account_row:
                session_bundle = _load_session_bundle(supa, job, account_row)
                storage_state = session_bundle.get("storage_state")
                session_storage = session_bundle.get("session_storage") or []
                if storage_state:
                    context_kwargs["storage_state"] = storage_state
                    params["session_loaded"] = True
                    evidence["session_reused"] = True
            context = await browser.new_context(**context_kwargs)
            if session_storage:
                evidence["session_storage_restored"] = await _restore_session_storage(context, session_storage)
            page = await context.new_page()
            result = await journey_fn(page, params, evidence)
            if account_row and result.status == "done" and (result.captured or {}).get("logged_in"):
                state = await context.storage_state()
                session_storage = await _capture_session_storage(page)
                evidence["session_storage_captured"] = bool(session_storage)
                evidence["session_saved"] = _save_session_state(
                    supa, job, account_row, state, session_storage=session_storage
                )
            await browser.close()
    except Exception as e:  # noqa: BLE001
        supa.table("portal_jobs").update({
            "status": "failed",
            "error": f"{type(e).__name__}: {str(e)[:300]}",
            "evidence": evidence,
            "finished_at": _now(),
        }).eq("id", job_id).execute()
        return

    supa.table("portal_jobs").update({
        "status": result.status,
        "evidence": {**evidence, **(result.captured or {}), "message": result.message},
        "screenshots": result.screenshots or [],
        "finished_at": _now(),
    }).eq("id", job_id).execute()
    logger.info(f"[PORTAL] job {job_id} -> {result.status}")


async def run_once(supa) -> int:
    """Pega 1 job queued (claim atômico queued->running) e roda. Retorna 0 ou 1."""
    res = supa.table("portal_jobs").select("*").eq("status", "queued").order("created_at").limit(1).execute()
    jobs = res.data or []
    if not jobs:
        return 0
    job = jobs[0]
    claim = supa.table("portal_jobs").update({
        "status": "running", "started_at": _now(), "attempts": int(job.get("attempts") or 0) + 1,
    }).eq("id", job["id"]).eq("status", "queued").execute()
    if not claim.data:
        return 0  # outro worker levou
    await _run_job(supa, job)
    return 1


async def poll_loop() -> None:
    """Loop principal. Nunca derruba o processo. Standby se o gate estiver off."""
    if not portal_real_enabled():
        logger.info("[PORTAL] standby (PORTAL_REAL_ENABLED=false) — não executa jobs")
        return
    logger.info("[PORTAL] worker iniciado (poll %ss)", POLL_SECONDS)
    while True:
        try:
            supa = _supabase()
            n = await run_once(supa)
            if n:
                logger.info(f"[PORTAL] processou {n} job(s)")
        except Exception as e:  # noqa: BLE001
            logger.error(f"[PORTAL] loop falhou: {type(e).__name__}: {str(e)[:200]}")
        await asyncio.sleep(POLL_SECONDS)
