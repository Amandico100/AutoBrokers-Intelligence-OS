"""Roteador de despacho (SPEC-017 P5/P6) — a espinha do acionamento real.

Quando um dispatch está ATIVO, as mensagens que chegam DO NÚMERO DA SEGURADORA
no WhatsApp da corretora não são "cliente": são a URA/especialista respondendo.
Este módulo:
- guarda a sessão de dispatch ativa por (company_id, telefone da seguradora)
  em Redis (fallback memória p/ testes);
- intercepta o inbound ANTES do agente: alimenta handle_insurer_message;
- envia as respostas de URA pela MESMA integração da corretora (gate S17-6:
  só com INSURER_DISPATCH_LIVE ligado);
- ao capturar protocolo/agendamento, envia o resumo humanizado AO CLIENTE
  e encerra a sessão.

Fail-safe: needs_human → sessão pausa e marca handoff (nunca responde às cegas).
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from typing import Any, Callable, Dict, Optional

from app.services.insurer_dispatch_service import (
    build_handoff_dossier,
    client_summary_from_capture,
    guard_human_phase_reply,
    handle_insurer_message,
    new_dispatch_session,
    reply_human_phase,
    start_dispatch,
)

logger = logging.getLogger(__name__)

_TTL_SECONDS = 6 * 3600
_MONITOR_TTL_SECONDS = 24 * 3600  # updates da seguradora chegam por até ~1 dia
_memory_store: Dict[str, str] = {}  # fallback p/ testes offline

# Pós-protocolo: a seguradora manda updates espontâneos (HDI: "prestador a
# caminho, faltam 30 min"; "agendada para 29/01 às 09:30"). Repassar AO CLIENTE
# em tempo real = acompanhamento de verdade. Pesquisas/avaliações: ignorar.
_MONITOR_FORWARD_RE = (
    r"prestador(?:.{0,80})(?:a caminho|encontrad|realizar[áa]|chegada)|encontramos o prestador|"
    r"agendad[ao] para|previs[ãa]o de chegada|faltam aproximadamente|procurando um prestador|"
    r"foi aberta com sucesso|est[áa] a caminho"
)
_MONITOR_IGNORE_RE = (
    r"pesquisa|avalie|sua opini[ãa]o|recomendaria|grau de satisfa[çc][ãa]o|nota"
)


def _norm(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _key(company_id: str, insurer_phone: str) -> str:
    digits = "".join(ch for ch in str(insurer_phone or "") if ch.isdigit())
    return f"dispatch:active:{company_id}:{digits}"


async def _redis():
    try:
        from app.core.redis import get_async_redis_client

        return await get_async_redis_client()
    except Exception:  # noqa: BLE001 — testes offline
        return None


async def save_active_dispatch(company_id: str, insurer_phone: str, session: Dict[str, Any]) -> None:
    # ESPELHO (SPEC-034): todo transcript novo vai para o banco/dashboard antes
    # de persistir no Redis — ponto único de captura. Nunca bloqueia o motor.
    try:
        from app.services.dispatch_mirror import mirror_session

        await mirror_session(company_id, insurer_phone, session)
    except Exception:  # noqa: BLE001 — espelho é best-effort
        pass
    key = _key(company_id, insurer_phone)
    payload = json.dumps(session, ensure_ascii=False, default=str)
    ttl = _MONITOR_TTL_SECONDS if str(session.get("state") or "") == "monitoring" else _TTL_SECONDS
    redis = await _redis()
    if redis is not None:
        await redis.set(key, payload, ex=ttl)
    else:
        _memory_store[key] = payload


async def load_active_dispatch(company_id: str, insurer_phone: str) -> Optional[Dict[str, Any]]:
    key = _key(company_id, insurer_phone)
    redis = await _redis()
    raw = await redis.get(key) if redis is not None else _memory_store.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return None


async def clear_active_dispatch(company_id: str, insurer_phone: str) -> None:
    key = _key(company_id, insurer_phone)
    redis = await _redis()
    if redis is not None:
        await redis.delete(key)
    else:
        _memory_store.pop(key, None)


def _digits(phone: str) -> str:
    return "".join(ch for ch in str(phone or "") if ch.isdigit())


async def list_active_dispatches(company_id: str) -> list:
    """Sessões de dispatch ATIVAS da corretora (espelho na página Conversas).

    Retorna resumo por sessão: telefone da seguradora, estado, subserviço,
    transcript e capturas — somente leitura, escopo por company."""
    prefix = f"dispatch:active:{company_id}:"
    raws: Dict[str, str] = {}
    redis = await _redis()
    if redis is not None:
        try:
            async for key in redis.scan_iter(match=prefix + "*"):
                k = key.decode() if isinstance(key, (bytes, bytearray)) else str(key)
                raw = await redis.get(k)
                if raw:
                    raws[k] = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[DISPATCH ROUTER] list scan failed: {type(e).__name__}")
    else:
        raws = {k: v for k, v in _memory_store.items() if k.startswith(prefix)}

    sessions = []
    for key, raw in raws.items():
        try:
            s = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        sessions.append({
            "insurer_phone": key[len(prefix):],
            "case_id": s.get("case_id"),
            "state": s.get("state"),
            "subservice": s.get("subservice"),
            "playbook_ref": s.get("playbook_ref"),
            "client_phone": s.get("client_phone"),
            "captured": s.get("captured") or {},
            "transcript": s.get("transcript") or [],
            "created_at": s.get("created_at"),
        })
    sessions.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return sessions


async def start_live_dispatch(
    *,
    company_id: str,
    case_id: str,
    playbook_ref: str,
    subservice: str,
    slots: Dict[str, Any],
    client_phone: str,
    insurer_phone: str,
    sender: Callable[[str], Any],
) -> Dict[str, Any]:
    """Inicia um acionamento REAL (gate já aberto pelo chamador): cria a sessão,
    envia a abertura à seguradora via sender e ativa o roteamento do inbound.

    Fail-safes: sessão ativa existente bloqueia (nunca duplo acionamento);
    slots incompletos não enviam nada nem salvam sessão.
    """
    insurer = _digits(insurer_phone)
    existing = await load_active_dispatch(company_id, insurer)
    if existing:
        # Sessão MORTA não pode bloquear um novo acionamento (teste 2026-07-10:
        # lock preso após a seguradora derrubar a conversa). Supersede quando:
        # needs_human/captured/test_aborted/monitoring, seguradora encerrou, ou
        # sessão velha (>45min).
        stale = str(existing.get("state") or "") in ("needs_human", "captured", "test_aborted", "monitoring")
        stale = stale or str(existing.get("reason") or "") == "insurer_closed"
        try:
            from datetime import datetime, timezone

            created = datetime.fromisoformat(str(existing.get("created_at") or "").replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_s = (datetime.now(timezone.utc) - created).total_seconds()
            stale = stale or age_s > 45 * 60
        except Exception:  # noqa: BLE001
            stale = True  # created_at ilegível = sessão suspeita, não bloqueia
        if not stale:
            return {"ok": False, "error": "dispatch_already_active", "session": existing}
        await clear_active_dispatch(company_id, insurer)
        logger.info(f"[DISPATCH ROUTER] stale session superseded (state={existing.get('state')})")

    session = new_dispatch_session(
        case_id=case_id, company_id=company_id, playbook_ref=playbook_ref,
        subservice=subservice, slots=slots,
    )
    if session.get("state") != "ready_to_send":
        return {"ok": False, "error": session.get("reason") or "not_ready", "session": session}

    session["client_phone"] = _digits(client_phone)
    session["insurer_phone"] = insurer
    session = start_dispatch(session, sender=sender)
    await save_active_dispatch(company_id, insurer, session)
    logger.info(f"[DISPATCH ROUTER] live dispatch started case={case_id} state={session.get('state')}")
    return {"ok": True, "session": session}


async def _support_contact(company_id: str) -> str:
    """WhatsApp do SUPORTE HUMANO da corretora (handoff com dossiê).
    Fontes: companies.acionamento_profile.suporte_humano_whatsapp →
    integrations.alert_target (número de alerta S17-3). Vazio = só loga."""
    try:
        from app.core.database import create_async_supabase_client

        db = await create_async_supabase_client()
        res = await db.table("companies").select("acionamento_profile").eq("id", company_id).limit(1).execute()
        if res.data:
            prof = res.data[0].get("acionamento_profile") or {}
            raw = str(prof.get("suporte_humano_whatsapp") or "").strip()
            # GRUPO do WhatsApp (…@g.us) é destino válido — não reduzir a dígitos.
            if raw.endswith("@g.us"):
                return raw
            if _digits(raw):
                return _digits(raw)
        res2 = await db.table("integrations").select("alert_target").eq("company_id", company_id).limit(3).execute()
        for row in res2.data or []:
            raw = str(row.get("alert_target") or "").strip()
            if raw.endswith("@g.us"):
                return raw
            if _digits(raw):
                return _digits(raw)
    except Exception as e:  # noqa: BLE001 — offline/teste: sem contato
        logger.warning(f"[DISPATCH ROUTER] support contact lookup failed: {type(e).__name__}")
    return ""


async def _log_deflection(company_id: str, session: Dict[str, Any]) -> None:
    """Telemetria de deflexão: cada needs_human vira registro estruturado
    (corredor, motivo, quantos passos andou) — é o combustível da meta dos 3%."""
    entry = {
        "at": _now_iso(),
        "case_id": session.get("case_id"),
        "playbook_ref": session.get("playbook_ref"),
        "subservice": session.get("subservice"),
        "reason": str(session.get("reason") or ""),
        "steps_out": len([t for t in (session.get("transcript") or []) if t.get("direction") == "out"]),
    }
    logger.warning(f"[DEFLECTION] {json.dumps(entry, ensure_ascii=False)}")
    try:
        redis = await _redis()
        if redis is not None:
            key = f"deflection:{company_id}"
            await redis.lpush(key, json.dumps(entry, ensure_ascii=False))
            await redis.ltrim(key, 0, 199)
    except Exception:  # noqa: BLE001
        pass


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _followup_schedule(captured: Dict[str, Any]) -> tuple:
    """(followup_at, closing_at) INTELIGENTES (feedback founder 12/07):
    - serviço AGENDADO (dia/hora capturados) → follow-up 45min APÓS o horário
      marcado do prestador (não após o protocolo);
    - ETA em minutos → 45min após a previsão de chegada;
    - sem nada → 45min após agora.
    Janela educada: nunca mandar mensagem entre 21h e 8h30 (America/Sao_Paulo)
    — adia para as 9h da manhã seguinte."""
    from datetime import datetime, timedelta, timezone as _tz

    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/Sao_Paulo")
    except Exception:  # noqa: BLE001
        tz = _tz.utc
    now = datetime.now(tz)
    base = now
    captured = captured or {}
    sched = captured.get("schedule") or {}
    if sched.get("day"):
        try:
            parts = [p for p in str(sched["day"]).split("/") if p]
            d = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else now.month
            y = int(parts[2]) if len(parts) > 2 else now.year
            if y < 100:
                y += 2000
            hh, mm = 9, 0
            at = sched.get("at") or sched.get("from")
            if at:
                bits = str(at).replace(" ", "").replace("h", ":").strip(":").split(":")
                hh = int(bits[0])
                mm = int(bits[1]) if len(bits) > 1 and bits[1] else 0
            base = datetime(y, m, d, hh, mm, tzinfo=tz)
        except Exception:  # noqa: BLE001
            base = now
    elif captured.get("eta_minutes"):
        try:
            base = now + timedelta(minutes=int(captured["eta_minutes"]))
        except Exception:  # noqa: BLE001
            base = now

    def _polite(dt):
        if dt.hour >= 21:
            return (dt + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        if dt.hour < 8 or (dt.hour == 8 and dt.minute < 30):
            return dt.replace(hour=9, minute=0, second=0, microsecond=0)
        return dt

    follow = _polite(max(base + timedelta(minutes=45), now + timedelta(minutes=20)))
    closing = _polite(follow + timedelta(hours=2, minutes=30))
    return follow.astimezone(_tz.utc).isoformat(), closing.astimezone(_tz.utc).isoformat()


def _queue_key(company_id: str, insurer_phone: str) -> str:
    return f"dispatch:queue:{company_id}:{_digits(insurer_phone)}"


async def enqueue_dispatch(company_id: str, insurer_phone: str, request: Dict[str, Any]) -> int:
    """FILA multi-cliente: 2º acionamento para a MESMA seguradora espera o 1º
    terminar (1 conversa por número). Retorna a posição na fila (1-based)."""
    payload = json.dumps({**request, "queued_at": _now_iso()}, ensure_ascii=False, default=str)
    redis = await _redis()
    if redis is not None:
        size = await redis.rpush(_queue_key(company_id, insurer_phone), payload)
        await redis.expire(_queue_key(company_id, insurer_phone), 2 * 3600)
        return int(size)
    _memory_store.setdefault(_queue_key(company_id, insurer_phone) + ":list", [])
    _memory_store[_queue_key(company_id, insurer_phone) + ":list"].append(payload)
    return len(_memory_store[_queue_key(company_id, insurer_phone) + ":list"])


async def _pop_queued(company_id: str, insurer_phone: str) -> Optional[Dict[str, Any]]:
    redis = await _redis()
    raw = None
    if redis is not None:
        raw = await redis.lpop(_queue_key(company_id, insurer_phone))
    else:
        lst = _memory_store.get(_queue_key(company_id, insurer_phone) + ":list") or []
        raw = lst.pop(0) if lst else None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return None


async def _start_next_in_queue(
    company_id: str, insurer_phone: str,
    send_to_insurer: Callable[[str], Any], send_to_client: Callable[[str, str], Any],
) -> None:
    """Sessão liberou o número da seguradora → inicia o próximo da fila."""
    nxt = await _pop_queued(company_id, insurer_phone)
    if not nxt:
        return
    result = await start_live_dispatch(
        company_id=company_id, case_id=str(nxt.get("case_id") or "queued"),
        playbook_ref=str(nxt.get("playbook_ref") or ""), subservice=str(nxt.get("subservice") or ""),
        slots=nxt.get("slots") or {}, client_phone=str(nxt.get("client_phone") or ""),
        insurer_phone=insurer_phone, sender=send_to_insurer,
    )
    client_phone = _digits(str(nxt.get("client_phone") or ""))
    if result.get("ok") and client_phone:
        try:
            send_to_client(client_phone, "Chegou a sua vez! 🙂 Estou acionando a seguradora agora e te aviso assim que sair o protocolo.")
        except Exception:  # noqa: BLE001
            pass
    logger.info(f"[DISPATCH ROUTER] queue drained -> started={result.get('ok')}")


async def note_manual_outbound(company_id: str, insurer_phone: str, text: str) -> bool:
    """Registra no transcript uma mensagem MANUAL da corretora (humano clicou/
    digitou direto na conversa com a seguradora — fromMe). Sem isso o espelho
    fica incompleto quando um humano copilota a URA (teste 2026-07-12)."""
    session = await load_active_dispatch(company_id, insurer_phone)
    if not session or not str(text or "").strip():
        return False
    session.setdefault("transcript", []).append(
        {"direction": "out", "text": str(text)[:2000], "manual": True}
    )
    await save_active_dispatch(company_id, insurer_phone, session)
    return True


async def try_route_insurer_inbound(
    *,
    company_id: str,
    from_phone: str,
    text: str,
    send_to_insurer: Callable[[str], Any],
    send_to_client: Callable[[str, str], Any],
    human_reply_provider: Optional[Callable[..., Any]] = None,
) -> bool:
    """Se o inbound vier do número da seguradora com dispatch ativo, processa
    aqui e retorna True (o webhook NÃO deve seguir para o agente).

    send_to_insurer(texto) — responde a seguradora (mesma integração).
    send_to_client(telefone, texto) — avisa o segurado (protocolo/handoff).
    human_reply_provider(session, texto) — async; redige a resposta na fase
    humana da seguradora. TODA resposta passa pelo guard determinístico;
    2 reprovações seguidas → needs_human (nunca responde às cegas).
    """
    session = await load_active_dispatch(company_id, from_phone)
    if not session:
        return False

    # TEST_ABORTED = sessão ENCERRADA: nunca mais responder à seguradora
    # (teste Allianz 12/07: a URA mandou nova saudação após o cancelamento e a
    # sessão "zumbi" respondeu '1' reabrindo o fluxo). Só registra no espelho.
    if str(session.get("state") or "") == "test_aborted":
        session.setdefault("transcript", []).append({"direction": "in", "text": str(text)[:2000]})
        await save_active_dispatch(company_id, from_phone, session)
        return True

    # MONITORING (pós-protocolo): nunca responde à seguradora; repassa os
    # updates relevantes ao cliente e ignora pesquisas de satisfação.
    if str(session.get("state") or "") == "monitoring":
        norm = _norm(text)
        session.setdefault("transcript", []).append({"direction": "in", "text": str(text)[:2000]})
        if text.strip() and not re.search(_MONITOR_IGNORE_RE, norm) and re.search(_MONITOR_FORWARD_RE, norm):
            client_phone = str(session.get("client_phone") or "").strip()
            if client_phone:
                try:
                    send_to_client(client_phone, f"🔔 Atualização da sua assistência:\n{str(text).strip()[:600]}")
                except Exception as e:  # noqa: BLE001
                    logger.error(f"[DISPATCH ROUTER] monitor forward failed: {type(e).__name__}")
        await save_active_dispatch(company_id, from_phone, session)
        return True

    session = handle_insurer_message(session, text, sender=send_to_insurer)
    state = session.get("state")

    # Fase humana: LLM redige, guard fiscaliza, falha repetida pausa (fail-closed).
    if state == "human_phase" and human_reply_provider is not None and session.get("pending_insurer_messages"):
        draft = None
        try:
            draft = await human_reply_provider(session, text)
        except Exception as e:  # noqa: BLE001 — provider nunca derruba o roteador
            logger.error(f"[DISPATCH ROUTER] human reply provider error: {type(e).__name__}")
        verdict = guard_human_phase_reply(str(draft or ""), session)
        if verdict["ok"]:
            session = reply_human_phase(session, verdict["reply"], sender=send_to_insurer)
            session["human_phase_guard_fails"] = 0
        else:
            fails = int(session.get("human_phase_guard_fails") or 0) + 1
            session["human_phase_guard_fails"] = fails
            logger.warning(f"[DISPATCH ROUTER] human phase reply rejected ({verdict['reason']}) fails={fails}")
            if fails >= 2:
                session["state"] = "needs_human"
                session["reason"] = f"human_phase_guard:{verdict['reason']}"
                state = "needs_human"

    if state == "test_aborted":
        # Modo TESTE: fluxo executado até a confirmação final e CANCELADO — nada
        # foi aberto na seguradora. Avisar quem está testando e manter a sessão
        # no espelho para inspeção (supersede libera novo acionamento).
        client_phone = str(session.get("client_phone") or "").strip()
        if client_phone and not session.get("client_notified_test_abort"):
            try:
                send_to_client(
                    client_phone,
                    "🧪 Teste concluído: o acionamento na seguradora foi executado até a "
                    "confirmação final e CANCELADO antes de abrir o serviço (modo teste). "
                    "Nenhum prestador foi acionado.",
                )
                session["client_notified_test_abort"] = True
            except Exception as e:  # noqa: BLE001
                logger.error(f"[DISPATCH ROUTER] test abort notify failed: {type(e).__name__}")
        await save_active_dispatch(company_id, from_phone, session)
        logger.info(f"[DISPATCH ROUTER] test_aborted case={session.get('case_id')} reason={session.get('reason')}")
        await _start_next_in_queue(company_id, from_phone, send_to_insurer, send_to_client)
        return True

    if state == "captured":
        summary = client_summary_from_capture(session)
        client_phone = str(session.get("client_phone") or "").strip()
        if summary and client_phone:
            try:
                send_to_client(client_phone, summary)
                session["client_notified"] = True
            except Exception as e:  # noqa: BLE001
                logger.error(f"[DISPATCH ROUTER] client notify failed: {type(e).__name__}")
        # Protocolo capturado → MONITORING: seguimos ouvindo a seguradora para
        # repassar updates ao cliente + FOLLOW-UP proativo com timer ("o guincho
        # chegou?" ~45min; encerramento carinhoso ~3h) via check_dispatch_followups.
        session["state"] = "monitoring"
        session["followup_at"], session["closing_at"] = _followup_schedule(session.get("captured") or {})
        await save_active_dispatch(company_id, from_phone, session)
        logger.info(f"[DISPATCH ROUTER] captured->monitoring case={session.get('case_id')} protocol=***")
        await _start_next_in_queue(company_id, from_phone, send_to_insurer, send_to_client)
        return True

    if state == "needs_human":
        reason = str(session.get("reason") or "")
        # RETOMADA AUTOMÁTICA: a URA derrubou a conversa (timeout/erro) e o fluxo
        # é idempotente até o freio → reabre SOZINHO uma vez, sem humano.
        if reason == "insurer_closed" and int(session.get("retry_count") or 0) == 0:
            await clear_active_dispatch(company_id, from_phone)
            retry = await start_live_dispatch(
                company_id=company_id, case_id=str(session.get("case_id") or "retry"),
                playbook_ref=str(session.get("playbook_ref") or ""),
                subservice=str(session.get("subservice") or ""),
                slots=session.get("slots") or {},
                client_phone=str(session.get("client_phone") or ""),
                insurer_phone=from_phone, sender=send_to_insurer,
            )
            if retry.get("ok"):
                retry["session"]["retry_count"] = 1
                await save_active_dispatch(company_id, from_phone, retry["session"])
                logger.info(f"[DISPATCH ROUTER] insurer_closed -> auto-retry iniciado case={session.get('case_id')}")
                return True
        client_phone = str(session.get("client_phone") or "").strip()
        if client_phone and not session.get("client_notified_handoff"):
            try:
                send_to_client(
                    client_phone,
                    "Estou finalizando um detalhe do seu atendimento com a seguradora e um colega da equipe vai assumir daqui a pouquinho, tá bom? Já já te retorno 🙂",
                )
                session["client_notified_handoff"] = True
            except Exception as e:  # noqa: BLE001
                logger.error(f"[DISPATCH ROUTER] handoff notify failed: {type(e).__name__}")
        # DOSSIÊ MASTIGADO para o suporte humano da corretora (1x por sessão).
        if not session.get("dossier_sent"):
            support = await _support_contact(company_id)
            if support:
                try:
                    send_to_client(support, build_handoff_dossier(session, reason))
                    session["dossier_sent"] = True
                except Exception as e:  # noqa: BLE001
                    logger.error(f"[DISPATCH ROUTER] dossier send failed: {type(e).__name__}")
            else:
                logger.warning("[DISPATCH ROUTER] handoff SEM contato de suporte configurado (acionamento_profile.suporte_humano_whatsapp)")
        await _log_deflection(company_id, session)
        if reason == "insurer_closed":
            await clear_active_dispatch(company_id, from_phone)
            await _start_next_in_queue(company_id, from_phone, send_to_insurer, send_to_client)
        else:
            await save_active_dispatch(company_id, from_phone, session)
        logger.warning(f"[DISPATCH ROUTER] needs_human case={session.get('case_id')} reason={reason}")
        return True

    await save_active_dispatch(company_id, from_phone, session)
    return True
