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
from typing import Any, Callable, Dict, Optional

from app.services.insurer_dispatch_service import (
    client_summary_from_capture,
    guard_human_phase_reply,
    handle_insurer_message,
    new_dispatch_session,
    reply_human_phase,
    start_dispatch,
)

logger = logging.getLogger(__name__)

_TTL_SECONDS = 6 * 3600
_memory_store: Dict[str, str] = {}  # fallback p/ testes offline


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
    key = _key(company_id, insurer_phone)
    payload = json.dumps(session, ensure_ascii=False, default=str)
    redis = await _redis()
    if redis is not None:
        await redis.set(key, payload, ex=_TTL_SECONDS)
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
        return {"ok": False, "error": "dispatch_already_active", "session": existing}

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

    if state == "captured":
        summary = client_summary_from_capture(session)
        client_phone = str(session.get("client_phone") or "").strip()
        if summary and client_phone:
            try:
                send_to_client(client_phone, summary)
                session["client_notified"] = True
            except Exception as e:  # noqa: BLE001
                logger.error(f"[DISPATCH ROUTER] client notify failed: {type(e).__name__}")
        await clear_active_dispatch(company_id, from_phone)
        logger.info(f"[DISPATCH ROUTER] captured case={session.get('case_id')} protocol=***")
        return True

    if state == "needs_human":
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
        await save_active_dispatch(company_id, from_phone, session)
        logger.warning(f"[DISPATCH ROUTER] needs_human case={session.get('case_id')} reason={session.get('reason')}")
        return True

    await save_active_dispatch(company_id, from_phone, session)
    return True
