"""Motor de acionamento de seguradora (SPEC-017 P4 / S17-5, S17-6).

Máquina de estados POR CASO que conversa com a seguradora usando um playbook:
  preparing -> ready_to_send -> [GATE] -> ura -> human_phase -> captured
                                   \\-> qualquer divergência -> needs_human

Regras duras:
- GATE (S17-6): `INSURER_DISPATCH_LIVE` OFF (default) = DRY-RUN completo —
  o plano/transcript é gerado e NADA é enviado à seguradora real.
- Passo de URA desconhecido = pausa + handoff (nunca responde às cegas).
- Protocolo/senha/agendamento SÓ por âncora capturada (nunca inventados).
- O envio real (quando o gate abrir) usa o MESMO número da corretora via seam.

Núcleo PURO: quem envia/recebe é injetado (sender). Persistência do estado do
dispatch fica no caso (metadata) — este módulo não fala com banco.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from app.services.corridor_playbooks import (
    detect_handoff_trigger,
    extract_capture_anchors,
    get_playbook,
    match_ura_step,
    missing_slots_for_subservice,
    render_reply,
)

DISPATCH_STATES = (
    "preparing",
    "ready_to_send",
    "ura",
    "human_phase",
    "captured",
    "needs_human",
    "blocked_gate",
)


def dispatch_live_enabled() -> bool:
    """S17-6: envio real à seguradora SÓ com a flag ligada + corretora avisada."""
    return str(os.getenv("INSURER_DISPATCH_LIVE", "")).strip().lower() in ("1", "true", "yes", "on")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_dispatch_session(
    *,
    case_id: str,
    company_id: str,
    playbook_ref: str,
    subservice: str,
    slots: Dict[str, Any],
) -> Dict[str, Any]:
    """Cria a sessão de dispatch. Slots incompletos → preparing com blockers."""
    playbook = get_playbook(playbook_ref)
    if not playbook:
        return {"state": "needs_human", "reason": "playbook_not_found", "playbook_ref": playbook_ref}

    sub = (playbook.get("subservices") or {}).get(str(subservice or "").lower(), {})
    merged_slots = dict(slots or {})
    # Opção de menu do subserviço (ex.: eletricista => tipo_servico "1").
    if sub.get("tipo_servico_opcao") and not merged_slots.get("tipo_servico_opcao"):
        merged_slots["tipo_servico_opcao"] = sub["tipo_servico_opcao"]
    # Default seguro: sem telefone extra => usa o registrado (opção 2).
    if not str(merged_slots.get("telefone_adicionar_opcao") or "").strip():
        merged_slots["telefone_adicionar_opcao"] = "1" if merged_slots.get("telefone_contato") else "2"

    missing = missing_slots_for_subservice(playbook, subservice, merged_slots)
    session = {
        "case_id": case_id,
        "company_id": company_id,
        "playbook_ref": playbook_ref,
        "subservice": str(subservice or "").lower(),
        "slots": merged_slots,
        "state": "preparing" if missing else "ready_to_send",
        "missing_slots": missing,
        "transcript": [],  # [{direction, text, at, dry_run}]
        "captured": {},
        "live": dispatch_live_enabled(),
        "created_at": _now(),
    }
    return session


def build_dry_run_plan(playbook_ref: str, subservice: str, slots: Dict[str, Any]) -> Dict[str, Any]:
    """P5: plano completo do acionamento SEM enviar nada — o que SERIA respondido
    em cada passo da URA com os dados do caso. Usado pela tool do atendente e
    pela revisão humana antes do gate abrir."""
    playbook = get_playbook(playbook_ref)
    if not playbook:
        return {"ok": False, "error": "playbook_not_found", "steps": [], "missing_slots": []}
    session = new_dispatch_session(
        case_id="dry-run", company_id="dry-run", playbook_ref=playbook_ref, subservice=subservice, slots=slots
    )
    if session.get("state") == "needs_human":
        return {"ok": False, "error": session.get("reason"), "steps": [], "missing_slots": []}
    if session.get("missing_slots"):
        return {"ok": False, "error": "missing_slots", "steps": [], "missing_slots": session["missing_slots"]}
    steps: List[Dict[str, str]] = [{"step": "abertura", "reply": "Olá"}]
    for step in playbook.get("ura_steps") or []:
        rendered = render_reply(step, session["slots"])
        steps.append({
            "step": str(step.get("step")),
            "reply": rendered["reply"] if rendered["ok"] else f"[PENDENTE: {','.join(rendered['missing'])}]",
        })
    return {
        "ok": True,
        "playbook_ref": playbook_ref,
        "subservice": session["subservice"],
        "missing_slots": [],
        "steps": steps,
        "live": dispatch_live_enabled(),
        "note": (
            "Acionamento REAL liberado." if dispatch_live_enabled()
            else "MODO SIMULAÇÃO: nada será enviado à seguradora até a liberação do Founder (INSURER_DISPATCH_LIVE)."
        ),
    }


def start_dispatch(
    session: Dict[str, Any],
    *,
    sender: Optional[Callable[[str], Any]] = None,
    opening_message: Optional[str] = None,
) -> Dict[str, Any]:
    """Inicia o acionamento (mensagem de abertura). Respeita o GATE."""
    if session.get("state") not in ("ready_to_send",):
        return session
    text = opening_message or "Olá"
    return _emit(session, text, sender=sender, next_state="ura")


def handle_insurer_message(
    session: Dict[str, Any],
    insurer_message: str,
    *,
    sender: Optional[Callable[[str], Any]] = None,
    human_phase_reply: Optional[str] = None,
) -> Dict[str, Any]:
    """Processa UMA mensagem da seguradora e decide a próxima ação.

    - captura âncoras SEMPRE (protocolo pode vir em qualquer fase);
    - gatilho de handoff → needs_human;
    - âncora de URA conhecida → resposta determinística;
    - sem âncora na fase ura → transição para human_phase;
    - human_phase: usa `human_phase_reply` (redigida pela LLM guardada) se dada.
    """
    playbook = get_playbook(session.get("playbook_ref") or "")
    if not playbook:
        session["state"] = "needs_human"
        session["reason"] = "playbook_not_found"
        return session

    session.setdefault("transcript", []).append(
        {"direction": "in", "text": str(insurer_message)[:2000], "at": _now()}
    )

    captured = extract_capture_anchors(playbook, insurer_message)
    if captured:
        session.setdefault("captured", {}).update(captured)

    trigger = detect_handoff_trigger(playbook, insurer_message)
    if trigger:
        session["state"] = "needs_human"
        session["reason"] = f"handoff_trigger:{trigger}"
        return session

    if session.get("captured", {}).get("protocol") and session.get("captured", {}).get("schedule"):
        session["state"] = "captured"
        return session

    step = match_ura_step(playbook, insurer_message)
    if step:
        rendered = render_reply(step, session.get("slots") or {})
        if not rendered["ok"]:
            session["state"] = "needs_human"
            session["reason"] = f"missing_slots:{','.join(rendered['missing'])}"
            session["missing_slots"] = rendered["missing"]
            return session
        return _emit(session, rendered["reply"], sender=sender, next_state="ura", step=step.get("step"))

    # Sem âncora de URA: fase humana da seguradora.
    if session.get("state") == "ura":
        session["state"] = "human_phase"
    if session.get("state") == "human_phase" and human_phase_reply:
        return _emit(session, human_phase_reply, sender=sender, next_state="human_phase")
    # Fail-safe: sem resposta preparada, não responde às cegas.
    session.setdefault("pending_insurer_messages", []).append(str(insurer_message)[:2000])
    return session


def client_summary_from_capture(session: Dict[str, Any]) -> Optional[str]:
    """Mensagem pronta para o CLIENTE quando protocolo+agendamento capturados."""
    captured = session.get("captured") or {}
    if not captured.get("protocol"):
        return None
    playbook = get_playbook(session.get("playbook_ref") or "") or {}
    lines: List[str] = []
    schedule = captured.get("schedule") or {}
    if schedule:
        lines.append(
            f"Prontinho! ✅ Sua assistência foi agendada para o dia {schedule.get('day')}, entre {schedule.get('from')} e {schedule.get('to')}."
        )
    else:
        lines.append("Prontinho! ✅ Sua assistência foi aberta na seguradora.")
    lines.append(f"O número do atendimento é {captured['protocol']}.")
    if captured.get("password"):
        lines.append(f"O prestador vai pedir uma senha de acesso: {captured['password']}.")
    for instruction in (playbook.get("client_instructions") or [])[:2]:
        lines.append(instruction)
    lines.append("Qualquer coisa até lá, é só me chamar por aqui 🙂")
    return "\n".join(lines)


def _emit(
    session: Dict[str, Any],
    text: str,
    *,
    sender: Optional[Callable[[str], Any]],
    next_state: str,
    step: Optional[str] = None,
) -> Dict[str, Any]:
    """Registra a mensagem de saída; envia SÓ se o gate estiver aberto."""
    live = bool(session.get("live")) and dispatch_live_enabled()
    entry = {"direction": "out", "text": str(text), "at": _now(), "dry_run": not live}
    if step:
        entry["step"] = step
    session.setdefault("transcript", []).append(entry)
    if live and sender is not None:
        sender(str(text))
    session["state"] = next_state
    return session
