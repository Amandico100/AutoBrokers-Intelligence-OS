"""Poll loop do portal-worker (SPEC-020 P1): pega portal_jobs 'queued', roda a
journey Playwright determinística e grava status/evidência. Sem Redis novo (poll
na tabela, mesmo padrão do routine_scheduler_loop). Gate PORTAL_REAL_ENABLED off:
em standby o worker sobe e responde /health mas NÃO executa job nenhum."""
from __future__ import annotations

import asyncio
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
    if account_id:
        acc = supa.table("portal_accounts").select("username, secret_encrypted").eq("id", account_id).limit(1).execute()
        if acc.data:
            from portal_worker import vault

            params.setdefault("username", acc.data[0].get("username") or "")
            enc = acc.data[0].get("secret_encrypted")
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
            context = await browser.new_context()
            page = await context.new_page()
            result = await journey_fn(page, params, evidence)
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
