"""F2 — Motor de Rotinas (Claude-Rotinas/Hermes-like para corretoras).

Rotina = receita em linguagem natural + agenda + entrega. O executor usa o
MESMO cérebro dos agentes (LangChainService.process_message → grafo Smith com
todas as tools), então a rotina pode consultar InfoCap, web, RAG etc.

Agenda (schedule jsonb):
  {"kind": "daily", "time": "08:00", "weekdays": [0..6]?}  # 0=segunda
  {"kind": "interval", "minutes": N>=5}

Entrega (delivery jsonb):
  {"channel": "whatsapp", "number": "5547..."} — envia pelo WhatsApp da corretora
  {"channel": "none"} — só registra em routine_runs (histórico)

Fail-safes: claim condicional (nunca roda 2x o mesmo tick), 5 falhas seguidas
desativam a rotina, falha do scheduler nunca derruba a API.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MIN_INTERVAL_MINUTES = 5
MAX_FAILURES = 5
SCHEDULER_TICK_SECONDS = 60

DEFAULT_ROUTINE_TIMEOUT = 180
MIN_ROUTINE_TIMEOUT = 30
MAX_ROUTINE_TIMEOUT = 600
RUN_RETENTION_DAYS = 90
RETENTION_INTERVAL_HOURS = 24


def resolve_routine_timeout(env_value: Optional[str] = None) -> int:
    """Segundos de timeout por execução (asyncio.wait_for). Default 180; piso 30;
    teto 600 — protege o worker de uma rotina travada queimando tokens sem fim."""
    raw = env_value if env_value is not None else os.getenv("ROUTINE_EXEC_TIMEOUT_SECONDS")
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_ROUTINE_TIMEOUT
    return max(MIN_ROUTINE_TIMEOUT, min(MAX_ROUTINE_TIMEOUT, v))


def retention_cutoff_iso(now_utc: Optional[datetime] = None, days: int = RUN_RETENTION_DAYS) -> str:
    """ISO do limite de retenção: runs anteriores a (agora - days) podem ser apagados."""
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - timedelta(days=days)).isoformat()


def should_run_retention(
    last_run_utc: Optional[datetime],
    now_utc: Optional[datetime] = None,
    interval_hours: int = RETENTION_INTERVAL_HOURS,
) -> bool:
    """True se a limpeza de routine_runs deve rodar agora (nunca rodou ou passou o intervalo)."""
    if last_run_utc is None:
        return True
    now = now_utc or datetime.now(timezone.utc)
    return (now - last_run_utc) >= timedelta(hours=interval_hours)


def _tz(tz_name: str):
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(tz_name or "America/Sao_Paulo")
    except Exception:  # noqa: BLE001 — container sem tzdata
        return timezone(timedelta(hours=-3))


def validate_schedule(schedule: Dict[str, Any]) -> Tuple[bool, str]:
    """(ok, motivo). Regras duras — rotina inválida nunca entra no banco."""
    kind = str((schedule or {}).get("kind") or "").strip().lower()
    if kind == "interval":
        try:
            minutes = int(schedule.get("minutes"))
        except (TypeError, ValueError):
            return False, "interval precisa de minutes inteiro"
        if minutes < MIN_INTERVAL_MINUTES:
            return False, f"intervalo mínimo é {MIN_INTERVAL_MINUTES} minutos"
        return True, ""
    if kind == "daily":
        t = str(schedule.get("time") or "")
        parts = t.split(":")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            return False, "daily precisa de time no formato HH:MM"
        hh, mm = int(parts[0]), int(parts[1])
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            return False, "time fora do intervalo 00:00-23:59"
        weekdays = schedule.get("weekdays")
        if weekdays is not None:
            if not isinstance(weekdays, list) or not weekdays:
                return False, "weekdays deve ser lista de 0-6 (0=segunda)"
            if any((not isinstance(d, int)) or d < 0 or d > 6 for d in weekdays):
                return False, "weekdays deve conter só inteiros 0-6"
        return True, ""
    return False, "kind deve ser daily ou interval"


def compute_next_run(schedule: Dict[str, Any], tz_name: str, now_utc: Optional[datetime] = None) -> datetime:
    """Próxima execução em UTC. Sempre estritamente no futuro."""
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    kind = str((schedule or {}).get("kind") or "").strip().lower()

    if kind == "interval":
        minutes = max(MIN_INTERVAL_MINUTES, int(schedule.get("minutes") or MIN_INTERVAL_MINUTES))
        return now + timedelta(minutes=minutes)

    tz = _tz(tz_name)
    local_now = now.astimezone(tz)
    hh, mm = (int(p) for p in str(schedule.get("time") or "08:00").split(":")[:2])
    weekdays = schedule.get("weekdays")  # 0=segunda ... 6=domingo (padrão python)

    candidate = local_now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    for _ in range(8):  # acha o próximo dia válido (máx 1 semana + folga)
        if candidate > local_now and (not weekdays or candidate.weekday() in weekdays):
            return candidate.astimezone(timezone.utc)
        candidate += timedelta(days=1)
        candidate = candidate.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return candidate.astimezone(timezone.utc)  # inalcançável na prática


def render_task_prompt(routine: Dict[str, Any]) -> str:
    """Prompt de execução: o agente produz SÓ o conteúdo final da entrega.
    SPEC-019 E — se a rotina tem CONHECIMENTO (argumentos de venda, FAQ do
    produto, tom de voz do outreach), ele entra ANTES das instruções."""
    knowledge = str(routine.get("knowledge") or "").strip()
    knowledge_block = f"### CONHECIMENTO DA ROTINA\n{knowledge}\n\n" if knowledge else ""
    return (
        f"[ROTINA AGENDADA: {routine.get('name')}]\n"
        "Você está executando uma rotina automática desta corretora, sem ninguém "
        "esperando resposta interativa. Execute as instruções abaixo usando suas "
        "ferramentas quando necessário e produza APENAS o conteúdo final da entrega "
        "(sem meta-comentários, sem perguntas, sem 'aqui está').\n\n"
        f"{knowledge_block}"
        f"INSTRUÇÕES DA ROTINA:\n{routine.get('instructions')}"
    )


def describe_missing_dependency(channel: str, has_whatsapp: bool) -> Optional[str]:
    """Mensagem INSTRUTIVA quando falta peça para a entrega (SPEC-019 A2).
    None = tudo pronto. O chat repassa o passo a passo ao corretor."""
    if str(channel or "").lower() == "whatsapp" and not has_whatsapp:
        return (
            "A corretora ainda NÃO tem um canal WhatsApp conectado — a rotina seria criada "
            "mas nunca conseguiria entregar. Explique ao corretor o passo a passo: "
            "1) Dashboard → Personalização → Conectores; 2) clicar no card WhatsApp; "
            "3) escolher 'Conexão por QR code' e escanear com o número desejado; "
            "4) depois pedir a criação da rotina de novo. NÃO crie a rotina agora."
        )
    return None


def engine_enabled() -> bool:
    return str(os.getenv("ROUTINES_ENGINE_ENABLED", "true")).strip().lower() in ("1", "true", "yes", "on")


async def _deliver(routine: Dict[str, Any], output: str) -> Tuple[bool, str]:
    """Entrega o resultado. (ok, detalhe)."""
    delivery = routine.get("delivery") or {}
    channel = str(delivery.get("channel") or "none").strip().lower()
    if channel in ("none", "", "log"):
        return True, "registrado no histórico"
    if channel == "whatsapp":
        number = "".join(ch for ch in str(delivery.get("number") or "") if ch.isdigit())
        if not number:
            return False, "delivery.number ausente"
        from app.core.database import get_supabase_client
        from app.services.whatsapp_service import get_whatsapp_service

        # Qualquer canal WhatsApp ATIVO da corretora serve para entregar rotina
        # (a busca "estrita" por agente é regra do atendimento, não daqui).
        def _find_integration():
            supa = get_supabase_client()
            res = (
                supa.client.table("integrations")
                .select("*")
                .eq("company_id", str(routine["company_id"]))
                .eq("is_active", True)
                .execute()
            )
            rows = res.data or []
            # S17-12: número dedicado a auxiliares tem PRIORIDADE p/ rotinas
            # (isola o outreach do número de atendimento); senão, qualquer ativo.
            _rank = {"auxiliary": 0, "attendance": 1}
            rows.sort(key=lambda r: _rank.get(str(r.get("purpose") or ""), 2))
            return rows[0] if rows else None

        integration = await asyncio.to_thread(_find_integration)
        if not integration:
            return False, "corretora sem canal WhatsApp ativo — conecte em Personalização > Conectores > WhatsApp"
        ok = await asyncio.to_thread(get_whatsapp_service().send_message, number, output, integration)
        return bool(ok), "enviado no WhatsApp" if ok else "falha no envio WhatsApp"
    return False, f"canal de entrega desconhecido: {channel}"


async def _execute_routine(supabase, routine: Dict[str, Any]) -> None:
    """Roda UMA rotina (já claimada) e registra o resultado."""
    routine_id = routine["id"]
    run_row = {"routine_id": routine_id, "status": "running"}
    try:
        ins = await asyncio.to_thread(
            lambda: supabase.client.table("routine_runs").insert(run_row).execute()
        )
        run_id = ins.data[0]["id"] if ins.data else None
    except Exception:  # noqa: BLE001
        run_id = None

    status, output_preview, error = "ok", "", ""
    try:
        from app.services.billing_collection import execute_billing_collection_routine, is_billing_routine

        if is_billing_routine(routine):
            billing_timeout = max(
                resolve_routine_timeout(),
                int(os.getenv("BILLING_COLLECTION_TIMEOUT_SECONDS", "900")),
            )
            output = await asyncio.wait_for(
                execute_billing_collection_routine(supabase, routine),
                timeout=min(billing_timeout, 1800),
            )
        else:
            from app.core.config import settings
            from app.services.langchain_service import LangChainService

            service = LangChainService(settings.OPENAI_API_KEY, supabase)
        # SPEC-019 D1 — timeout por execução: rotina travada não segura o worker.
            output, _metrics = await asyncio.wait_for(
                service.process_message(
                    user_message=render_task_prompt(routine),
                    company_id=str(routine["company_id"]),
                    user_id=str(routine.get("created_by") or "routine-engine"),
                    session_id=f"routine:{routine_id}",
                    channel="routine",
                    agent_id=str(routine["agent_id"]) if routine.get("agent_id") else None,
                    collect_metrics=False,
                ),
                timeout=resolve_routine_timeout(),
            )
        output = str(output or "").strip()
        if not output:
            raise RuntimeError("agente devolveu resposta vazia")
        delivered, detail = await _deliver(routine, output)
        if not delivered:
            raise RuntimeError(f"entrega falhou: {detail}")
        output_preview = output[:500]
        logger.info(f"[ROUTINES] ✅ rotina {routine_id} ok ({detail})")
    except Exception as e:  # noqa: BLE001
        status, error = "error", f"{type(e).__name__}: {str(e)[:300]}"
        logger.error(f"[ROUTINES] ❌ rotina {routine_id}: {error}")

    def _finish():
        if run_id:
            supabase.client.table("routine_runs").update({
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "status": status,
                "output_preview": output_preview or None,
                "error": error or None,
            }).eq("id", run_id).execute()
        failures = 0 if status == "ok" else int(routine.get("consecutive_failures") or 0) + 1
        patch = {"consecutive_failures": failures, "updated_at": datetime.now(timezone.utc).isoformat()}
        if failures >= MAX_FAILURES:
            patch["is_active"] = False  # fail-safe: para de queimar tokens sozinha
            logger.error(f"[ROUTINES] 🔒 rotina {routine_id} DESATIVADA após {failures} falhas seguidas")
        supabase.client.table("routines").update(patch).eq("id", routine_id).execute()

    try:
        await asyncio.to_thread(_finish)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[ROUTINES] finish falhou: {type(e).__name__}")


async def run_due_routines(supabase) -> int:
    """Executa as rotinas vencidas (claim atômico por next_run_at). Retorna nº executadas."""
    now_iso = datetime.now(timezone.utc).isoformat()

    def _fetch():
        return (
            supabase.client.table("routines")
            .select("*")
            .eq("is_active", True)
            .lte("next_run_at", now_iso)
            .order("next_run_at")
            .limit(5)
            .execute()
        )

    res = await asyncio.to_thread(_fetch)
    due: List[Dict[str, Any]] = res.data or []
    ran = 0
    for routine in due:
        nxt = compute_next_run(routine.get("schedule") or {}, routine.get("timezone") or "America/Sao_Paulo")

        def _claim():
            return (
                supabase.client.table("routines")
                .update({"next_run_at": nxt.isoformat(), "last_run_at": now_iso})
                .eq("id", routine["id"])
                .eq("next_run_at", routine.get("next_run_at"))  # claim: só quem viu este tick
                .execute()
            )

        try:
            claim = await asyncio.to_thread(_claim)
            if not claim.data:
                continue  # outro worker levou
        except Exception as e:  # noqa: BLE001
            logger.error(f"[ROUTINES] claim falhou: {type(e).__name__}")
            continue
        await _execute_routine(supabase, routine)
        ran += 1
    return ran


async def routine_scheduler_loop() -> None:
    """Loop do agendador (startup da API). Nunca derruba o processo."""
    if not engine_enabled():
        logger.info("[ROUTINES] engine desabilitada (ROUTINES_ENGINE_ENABLED=false)")
        return
    logger.info("[ROUTINES] 🕰️ scheduler iniciado (tick %ss)", SCHEDULER_TICK_SECONDS)
    from app.core.database import get_supabase_client

    last_retention: Optional[datetime] = None
    while True:
        try:
            supabase = get_supabase_client()
            ran = await run_due_routines(supabase)
            if ran:
                logger.info(f"[ROUTINES] tick executou {ran} rotina(s)")
            # SPEC-019 D3 — retenção: apaga routine_runs > 90 dias, no máx. 1x/dia.
            if should_run_retention(last_retention):
                now = datetime.now(timezone.utc)
                cutoff = retention_cutoff_iso(now)
                try:
                    await asyncio.to_thread(
                        lambda: supabase.client.table("routine_runs").delete().lt("started_at", cutoff).execute()
                    )
                    last_retention = now
                    logger.info(f"[ROUTINES] retenção: runs anteriores a {cutoff[:10]} apagados")
                except Exception as e:  # noqa: BLE001
                    logger.error(f"[ROUTINES] retenção falhou: {type(e).__name__}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"[ROUTINES] tick falhou: {type(e).__name__}: {str(e)[:200]}")
        await asyncio.sleep(SCHEDULER_TICK_SECONDS)
