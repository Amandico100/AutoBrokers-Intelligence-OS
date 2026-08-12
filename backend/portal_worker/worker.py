"""Poll loop do portal-worker (SPEC-020 P1): pega portal_jobs 'queued', roda a
journey Playwright determinística e grava status/evidência. Sem Redis novo (poll
na tabela, mesmo padrão do routine_scheduler_loop). Gate PORTAL_REAL_ENABLED off:
em standby o worker sobe e responde /health mas NÃO executa job nenhum."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger("portal_worker")

POLL_SECONDS = int(os.getenv("PORTAL_POLL_SECONDS", "30"))
# Teto duro por journey: nenhum job pode segurar o worker além disso.
JOB_TIMEOUT_SECONDS = int(os.getenv("PORTAL_JOB_TIMEOUT_SECONDS", "1200"))
# Job 'running' mais velho que timeout+margem = órfão (worker morreu/reiniciou).
STALE_MARGIN_SECONDS = 600


def portal_real_enabled() -> bool:
    return str(os.getenv("PORTAL_REAL_ENABLED", "false")).strip().lower() in ("1", "true", "yes", "on")


# Chromium: headless MODERNO, não o clássico.
#
# 📊 Medido em 10/08/2026 contra o portal da HDI, um fator por vez, com linha
# de CONTROLE repetida no início e no fim da bateria::
#
#     headless clássico  ...................  BLOQUEADO  "Access Denied" (Akamai)
#     + args anti-automação ................  BLOQUEADO
#     + script de stealth ..................  BLOQUEADO
#     + args E stealth .....................  BLOQUEADO
#     navegador COM janela .................  PASSOU
#     --headless=new .......................  PASSOU     ← e roda sem tela
#
# Cinco variações deram o mesmo bloqueio, então nenhuma delas era a causa: o
# fator é o MODO headless. O clássico é um binário separado, com fingerprint
# próprio, e o Akamai o reconhece. O `--headless=new` é o mesmo Chrome de
# janela rodando sem desenhar — passa, e não precisa de Xvfb no contêiner.
#
# `headless=False` + `--headless=new` é como se pede o modo novo no Playwright:
# o parâmetro precisa ficar falso para a lib não injetar o `--headless` antigo.
#
# A Allianz continua no mesmo navegador — e é ela a linha de controle desta
# mudança: se ela seguir baixando os 4 boletos, o modo novo não regrediu nada.
def _launch_kwargs() -> Dict[str, Any]:
    modo = str(os.getenv("PORTAL_HEADLESS_MODE", "new")).strip().lower()
    if modo == "classic":
        return {"headless": True}
    if modo == "headed":  # só com tela/Xvfb — último recurso
        return {"headless": False, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    return {
        "headless": False,
        "args": [
            "--headless=new",
            "--no-sandbox",            # contêiner sem privilégio
            "--disable-dev-shm-usage",  # /dev/shm pequeno derruba aba em Docker
            "--disable-blink-features=AutomationControlled",
        ],
    }


def _parse_ts(value: Any) -> datetime | None:
    """ISO tolerante (Supabase devolve '2026-07-10 04:01:46.5+00')."""
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    if text.endswith("+00"):
        text = text + ":00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def stale_running_patch(job: Dict[str, Any], now: datetime | None = None) -> Dict[str, Any] | None:
    """Patch de recuperação p/ job 'running' órfão; None = deixar em paz.
    1ª ocorrência → volta pra fila (nova tentativa); reincidente → failed.
    (Um job vidros ficou 3 dias preso em running após restart do worker.)"""
    started = _parse_ts(job.get("started_at")) or _parse_ts(job.get("created_at"))
    if started is None:
        return None
    now = now or datetime.now(timezone.utc)
    age = (now - started).total_seconds()
    if age < JOB_TIMEOUT_SECONDS + STALE_MARGIN_SECONDS:
        return None
    attempts = int(job.get("attempts") or 0)
    if attempts < 2:
        return {"status": "queued", "error": "requeue: worker reiniciou durante a execucao anterior"}
    return {
        "status": "failed",
        "error": f"job orfao apos {attempts} tentativa(s): worker interrompido durante a execucao",
        "finished_at": _now(),
    }


async def recover_stale_jobs(supa) -> int:
    """Roda a cada tick: destrava jobs órfãos sem intervenção humana."""
    try:
        res = supa.table("portal_jobs").select("id, started_at, created_at, attempts").eq("status", "running").execute()
    except Exception as e:  # noqa: BLE001
        logger.warning("[PORTAL] recover_stale_jobs indisponivel: %s", type(e).__name__)
        return 0
    recovered = 0
    for job in res.data or []:
        patch = stale_running_patch(job)
        if not patch:
            continue
        try:
            supa.table("portal_jobs").update(patch).eq("id", job["id"]).eq("status", "running").execute()
            recovered += 1
            logger.warning("[PORTAL] job orfao %s -> %s", job.get("id"), patch.get("status"))
        except Exception as e:  # noqa: BLE001
            logger.warning("[PORTAL] falha ao recuperar job orfao: %s", type(e).__name__)
    return recovered


def _supabase():
    from supabase import create_client

    url = os.getenv("SUPABASE_URL") or ""
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    return create_client(url, key)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _upload_portal_blob(supa, path: str, blob: bytes, content_type: str = "application/pdf") -> str | None:
    """Upload privado de evidencias/boletos do portal. Retorna storage path."""
    clean_path = str(path or "").strip().lstrip("/")
    if not clean_path or not blob:
        return None
    try:
        await asyncio.to_thread(
            lambda: supa.storage.from_("portal-evidence").upload(
                clean_path,
                blob,
                {"content-type": content_type or "application/octet-stream", "cache-control": "3600", "upsert": "true"},
            )
        )
        return clean_path
    except Exception as e:  # noqa: BLE001
        logger.warning("[PORTAL] upload portal-evidence falhou: %s", type(e).__name__)
        return None


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


def _hitl_kind(result, evidence: Dict[str, Any]) -> str:
    text = " ".join([
        str(getattr(result, "message", "") or ""),
        json.dumps(getattr(result, "captured", {}) or {}, ensure_ascii=True),
        json.dumps(evidence or {}, ensure_ascii=True),
    ]).lower()
    if any(token in text for token in ("captcha", "2fa", "mfa", "otp", "codigo de verificacao", "duas etapas")):
        return "captcha_2fa"
    return "review"


def _augment_hitl_evidence(result, evidence: Dict[str, Any]) -> Dict[str, Any]:
    message = str(getattr(result, "message", "") or "").strip()
    captured = getattr(result, "captured", {}) or {}
    kind = _hitl_kind(result, evidence)
    return {
        **(evidence or {}),
        **captured,
        "message": message,
        "hitl": {
            "required": True,
            "kind": kind,
            "resume_mode": "requeue_after_human",
            "reason": message or "portal pediu revisao humana",
        },
    }


async def _capture_hitl_screenshot(page) -> str | None:
    try:
        raw = await page.screenshot(type="jpeg", quality=60, full_page=False)
        if not raw:
            return None
        return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
    except Exception as e:  # noqa: BLE001
        logger.warning("[PORTAL] falha ao capturar screenshot HITL: %s", type(e).__name__)
        return None


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
            browser = await p.chromium.launch(**_launch_kwargs())
            # Locale/fuso do corretor real: apps legados Allianz derivam nomes
            # de atributos de strings localizadas e QUEBRAM no boot com en-US
            # (InvalidCharacterError em setAttribute — job c17fc7db).
            context_kwargs: Dict[str, Any] = {
                "accept_downloads": True,
                "locale": "pt-BR",
                "timezone_id": "America/Sao_Paulo",
            }
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
            # A Ficha de Gestão (ngx-file-management) morre no boot com
            # InvalidCharacterError ao chamar setAttribute('-') — fatal no
            # Chromium headless, inofensivo no Chrome do corretor. O shim
            # engole SÓ o atributo inválido; o app continua montando.
            await context.add_init_script(
                """(() => {
                  const orig = Element.prototype.setAttribute;
                  Element.prototype.setAttribute = function (name, value) {
                    try { return orig.call(this, name, value); }
                    catch (e) { /* atributo inválido de app legado — ignora */ }
                  };
                })();"""
            )
            if session_storage:
                evidence["session_storage_restored"] = await _restore_session_storage(context, session_storage)
            page = await context.new_page()
            # Que navegador subiu, de fato. Sem isto, um portal que recusa o
            # acesso deixa duas explicações igualmente plausíveis — "o modo
            # errado" e "o IP do servidor" — e nenhuma forma de separá-las
            # sem outro deploy. A evidência tem de trazer o que foi usado.
            params["_launch_mode"] = _launch_kwargs()
            evidence["launch_mode"] = params["_launch_mode"]
            params["_job_id"] = str(job_id)
            params["_company_id"] = str(job.get("company_id") or "")
            params["_portal_key"] = str(job.get("portal_key") or "")
            params["_upload_blob"] = lambda path, blob, content_type="application/pdf": _upload_portal_blob(
                supa, path, blob, content_type
            )
            try:
                result = await asyncio.wait_for(journey_fn(page, params, evidence), timeout=JOB_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"journey excedeu o teto de {JOB_TIMEOUT_SECONDS}s (PORTAL_JOB_TIMEOUT_SECONDS)"
                ) from None
            if account_row and result.status == "done" and (result.captured or {}).get("logged_in"):
                state = await context.storage_state()
                session_storage = await _capture_session_storage(page)
                evidence["session_storage_captured"] = bool(session_storage)
                evidence["session_saved"] = _save_session_state(
                    supa, job, account_row, state, session_storage=session_storage
                )
            screenshots = list(result.screenshots or [])
            if result.status == "needs_human":
                hitl_shot = await _capture_hitl_screenshot(page)
                if hitl_shot:
                    screenshots.insert(0, hitl_shot)
                evidence = _augment_hitl_evidence(result, evidence)
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
        "evidence": evidence if result.status == "needs_human" else {**evidence, **(result.captured or {}), "message": result.message},
        "screenshots": screenshots,
        "error": None,  # limpa nota de requeue de tentativa anterior
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
            await recover_stale_jobs(supa)
            n = await run_once(supa)
            if n:
                logger.info(f"[PORTAL] processou {n} job(s)")
        except Exception as e:  # noqa: BLE001
            logger.error(f"[PORTAL] loop falhou: {type(e).__name__}: {str(e)[:200]}")
        await asyncio.sleep(POLL_SECONDS)
