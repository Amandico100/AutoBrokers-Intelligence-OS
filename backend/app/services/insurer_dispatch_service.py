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


def build_human_phase_messages(session: Dict[str, Any], insurer_message: str) -> Dict[str, str]:
    """Prompt da fase humana/adaptativa da seguradora (LLM redige, guard fiscaliza).

    INTELIGÊNCIA sem cabresto: além de responder o especialista humano, este cérebro
    também dá conta de uma URA que MUDOU (a Allianz trocou uma palavra/ordem do menu
    e nenhuma âncora determinística casou). Recebe a INTENÇÃO de cada passo do
    playbook + os dados do caso, e decide sozinho — inclusive escolher a opção certa
    de um menu numerado. Regras duras: só dados do caso, sem números inventados (o
    guard fiscaliza), e se realmente não der pra deduzir → NAO_SEI (pausa p/ humano)."""
    slots = session.get("slots") or {}
    captured = session.get("captured") or {}
    fatos = "\n".join(f"- {k}: {v}" for k, v in slots.items() if v not in (None, ""))
    if captured:
        fatos += "\n" + "\n".join(f"- capturado {k}: {v}" for k, v in captured.items())
    pending = session.get("pending_insurer_messages") or []
    contexto_pendente = (
        "\nMensagens anteriores da seguradora ainda sem resposta:\n" + "\n".join(f"- {m}" for m in pending[-3:])
    ) if pending else ""
    # Intenção de cada passo do playbook — pra o cérebro reconhecer um menu que mudou
    # de texto/ordem e ainda assim escolher certo (adaptativo, não engessado).
    playbook = get_playbook(session.get("playbook_ref") or "") or {}
    intents = []
    for st in (playbook.get("ura_steps") or []):
        nome, nota, resp = st.get("step"), st.get("notes"), st.get("reply")
        try:
            resp_render = str(resp or "").format(**{k: str(v) for k, v in slots.items()})
        except Exception:  # noqa: BLE001 — slot faltante fica com o placeholder mesmo
            resp_render = str(resp or "")
        linha = f"- {nome}: responder '{resp_render}'" + (f" — {nota}" if nota else "")
        intents.append(linha)
    guia_ura = ("\nCONHECIMENTO DO FLUXO (passos típicos e a resposta certa de cada um; "
                "use pra reconhecer um menu mesmo que a seguradora tenha trocado palavras/ordem):\n"
                + "\n".join(intents)) if intents else ""
    subservice = str(session.get("subservice") or "")
    system = (
        "Você conduz, EM NOME DA CORRETORA, um acionamento de assistência residencial no WhatsApp da "
        "seguradora (Allianz Assistência 24h) que JÁ está em andamento. Pode ser a URA (menu numerado) "
        "ou um atendente humano.\n"
        f"Subserviço deste caso: {subservice or 'não informado'}.\n"
        "COMO DECIDIR (seja inteligente, não robótico):\n"
        "- Se a mensagem for um MENU NUMERADO, escolha a opção coerente com o subserviço/dados do caso e "
        "responda SÓ com o número (ex.: '2'). Use o CONHECIMENTO DO FLUXO abaixo como guia, mesmo que o "
        "texto do menu tenha mudado.\n"
        "- Se pedir um dado do caso (CPF, número da residência, telefone), responda com o valor exato do caso.\n"
        "- Se for um atendente humano perguntando algo, responda em 1-2 frases curtas, PT-BR cordial.\n"
        "REGRAS INEGOCIÁVEIS:\n"
        "1. Use SOMENTE os dados do caso. NUNCA invente números, protocolos, prazos, valores ou dados.\n"
        "2. Não prometa nada em nome da seguradora; não confirme cobertura.\n"
        "3. Se realmente NÃO der pra deduzir a resposta a partir do caso e do fluxo, responda exatamente: NAO_SEI"
    )
    user = (
        f"Dados do caso (únicos números permitidos):\n{fatos}{guia_ura}{contexto_pendente}\n\n"
        f"Mensagem da seguradora agora:\n{insurer_message}\n\nSua resposta:"
    )
    return {"system": system, "user": user}


def _digit_runs(text: str, min_len: int = 5) -> List[str]:
    runs, cur = [], ""
    for ch in str(text or ""):
        if ch.isdigit():
            cur += ch
        else:
            if len(cur) >= min_len:
                runs.append(cur)
            cur = ""
    if len(cur) >= min_len:
        runs.append(cur)
    return runs


def guard_human_phase_reply(reply: str, session: Dict[str, Any]) -> Dict[str, Any]:
    """Guard determinístico da resposta da LLM na fase humana (fail-closed)."""
    text = str(reply or "").strip()
    if not text:
        return {"ok": False, "reason": "empty", "reply": ""}
    normalized = text.upper().replace("ÃO", "AO").replace(" ", "_")
    if "NAO_SEI" in normalized:
        return {"ok": False, "reason": "model_declined", "reply": text}
    if len(text) > 400:
        return {"ok": False, "reason": "too_long", "reply": text}
    captured = session.get("captured") or {}
    if "protocolo" in text.lower() and not captured.get("protocol"):
        return {"ok": False, "reason": "protocol_without_capture", "reply": text}
    allowed_digits = " ".join(
        str(v) for v in list((session.get("slots") or {}).values()) + list(captured.values())
    )
    for run in _digit_runs(text):
        if run not in allowed_digits:
            return {"ok": False, "reason": "invented_number", "reply": text}
    return {"ok": True, "reason": "", "reply": text}


def reply_human_phase(
    session: Dict[str, Any],
    reply: str,
    *,
    sender: Optional[Callable[[str], Any]] = None,
) -> Dict[str, Any]:
    """Emite a resposta GUARDADA na fase humana e limpa as pendências."""
    session = _emit(session, reply, sender=sender, next_state="human_phase")
    session["pending_insurer_messages"] = []
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
