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
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from app.services.corridor_playbooks import (
    auto_subservice_menu_value,
    detect_finalize_anchor,
    detect_handoff_trigger,
    extract_capture_anchors,
    get_playbook,
    match_ura_step,
    missing_slots_for_subservice,
    render_opening_message,
    render_reply,
)

DISPATCH_STATES = (
    "preparing",
    "ready_to_send",
    "ura",
    "human_phase",
    "captured",
    "monitoring",      # protocolo capturado; só repassa updates da seguradora ao cliente
    "test_aborted",    # modo TESTE: fluxo completo executado e CANCELADO na confirmação final
    "needs_human",
    "blocked_gate",
)


def dispatch_live_enabled() -> bool:
    """S17-6: envio real à seguradora SÓ com a flag ligada + corretora avisada."""
    return str(os.getenv("INSURER_DISPATCH_LIVE", "")).strip().lower() in ("1", "true", "yes", "on")


def finalize_live_for(playbook_ref: str) -> bool:
    """Decisão do founder (2026-07-11): o freio de finalização existe SÓ para os
    TESTES (a IA executa o fluxo inteiro e CANCELA antes de abrir o serviço).
    Corredor VALIDADO passa a completar ponta a ponta sem humano:
    - DISPATCH_FINALIZE_MODE=live libera TODOS os corredores;
    - DISPATCH_FINALIZE_LIVE_PLAYBOOKS=ref1,ref2 gradua corredor a corredor."""
    mode = str(os.getenv("DISPATCH_FINALIZE_MODE", "test")).strip().lower()
    if mode == "live":
        return True
    live_refs = [x.strip() for x in str(os.getenv("DISPATCH_FINALIZE_LIVE_PLAYBOOKS", "")).split(",") if x.strip()]
    return str(playbook_ref or "") in live_refs


def _finalize_allowed(session: Dict[str, Any]) -> bool:
    return bool(session.get("finalize_approved")) or finalize_live_for(str(session.get("playbook_ref") or ""))


# Mensagens de pós-atendimento da seguradora (pesquisa/avaliação): nunca responder.
_SURVEY_NOOP_RE = (
    r"pesquisa de (?:satisfa[çc][ãa]o|qualidade)|avalie (?:sua|a sua|nosso)|sua opini[ãa]o [ée] muito importante|"
    r"o quanto voc[êe] recomendaria|grau de satisfa[çc][ãa]o|responda nossa pesquisa"
)


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
    # AUTO (SPEC-031): injeta a opção/rótulo do menu de serviço da seguradora
    # (guincho => "3" na Allianz, "Guincho" na Porto) nos slots que os passos usam.
    if str(playbook.get("line_kind") or "") == "auto":
        menu_value = auto_subservice_menu_value(playbook, subservice)
        if menu_value:
            merged_slots.setdefault("servico_opcao", menu_value)
            merged_slots.setdefault("servico_texto", menu_value)
        merged_slots.setdefault("roda_travada", "não")
        merged_slots.setdefault("quando", "agora")
        merged_slots.setdefault("veiculo_cor", "não sei")
        merged_slots.setdefault("rodovia", "Não")
    # Referência do local é opcional em TODAS as linhas ('não tem' é o padrão real).
    merged_slots.setdefault("ponto_referencia", "não tem")
    # Endereços decompostos (rua/nº/bairro/cidade/UF) p/ URAs que pedem separado.
    from app.services.corridor_playbooks import inject_address_slots

    inject_address_slots(merged_slots)

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
    # Abertura CURTA ("Olá") — é assim que a operadora real inicia; a URA não lê
    # texto longo. O resumo estruturado vai ao ANALISTA humano (fase humana).
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
    return _emit(session, opening_message or "Olá", sender=sender, next_state="ura")


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

    # Inbound sem texto (mídia/sticker da seguradora): registra e não responde.
    if not str(insurer_message or "").strip():
        return session

    session.setdefault("transcript", []).append(
        {"direction": "in", "text": str(insurer_message)[:2000], "at": _now()}
    )

    captured = extract_capture_anchors(playbook, insurer_message)
    if captured:
        session.setdefault("captured", {}).update(captured)

    got = session.get("captured", {})
    if got.get("protocol") and (got.get("schedule") or got.get("eta_minutes") or got.get("tracking_link")):
        session["state"] = "captured"
        return session

    # Seguradora ENCERROU a conversa (timeout/resposta inválida): parar de falar
    # e liberar a corretora para reabrir (visto no teste Yelum 2026-07-10).
    if re.search(
        r"conversa ser[áa] encerrada|estamos encerrando (?:esta|a) conversa|"
        r"tempo m[áa]ximo de espera.*excedid|encerrad[ao] por (?:inatividade|falta de intera)|"
        r"falta de intera[çc][ãa]o esta conversa foi encerrada|conversa foi encerrada",
        _norm_text(insurer_message),
        re.IGNORECASE,
    ):
        session["state"] = "needs_human"
        session["reason"] = "insurer_closed"
        return session

    # FREIO DE FINALIZAÇÃO (founder 2026-07-11): existe SÓ para o modo TESTE.
    # A seguradora vai CONFIRMAR/ABRIR o serviço de verdade → em teste, CANCELA
    # educadamente (abort_reply do playbook; sem abort, silêncio e a URA encerra).
    # Em modo LIVE (corredor validado) NÃO trava: o passo de confirmação é
    # respondido pelos próprios ura_steps e o fluxo completa ponta a ponta.
    finalize = detect_finalize_anchor(playbook, insurer_message)
    if finalize and not _finalize_allowed(session):
        session["reason"] = f"finalize_test_abort:{finalize}"
        abort = str(playbook.get("finalize_abort_reply") or "").strip()
        if abort:
            return _emit(session, abort, sender=sender, next_state="test_aborted", step="finalize_abort")
        session["state"] = "test_aborted"
        return session

    # Âncora de URA conhecida responde ANTES dos gatilhos de handoff: menus reais
    # listam "Sinistro"/"Acidente" como OPÇÕES (Porto opção 6, Bradesco opção 2) e
    # isso não significa que o caso é sinistro. Handoff só quando NENHUM passo
    # conhecido casou (a mensagem é sobre o caso, não um menu mapeado).
    step = match_ura_step(playbook, insurer_message, subservice=session.get("subservice"))
    if step:
        # Passo "noop": mensagem informativa (fila, aguarde, "ainda não
        # identificamos") — reconhecer e NÃO responder nada.
        if step.get("noop"):
            return session
        # reply_repeat: na 2ª+ vez que o MESMO passo aparecer, responder diferente
        # (ex.: menu raiz da Porto — 1ª vez re-identifica o cliente, 2ª segue).
        step_counts = session.setdefault("step_counts", {})
        step_name = str(step.get("step") or "")
        effective = dict(step)
        if step.get("reply_repeat") and int(step_counts.get(step_name) or 0) >= 1:
            effective["reply"] = step["reply_repeat"]
        # reply_if_step_done: se OUTRO passo já aconteceu nesta sessão, a resposta
        # muda (ex.: menu raiz da Porto depois do CPF digitado → serviço direto,
        # sem re-identificar um cliente que já é o nosso).
        cond = step.get("reply_if_step_done")
        if isinstance(cond, dict) and int(step_counts.get(str(cond.get("step") or "")) or 0) >= 1:
            effective["reply"] = str(cond.get("reply") or effective["reply"])
        if step.get("dynamic") == "vehicle_by_plate":
            # Menu de veículos: escolhe pela PLACA MASCARADA (teste Allianz 12/07:
            # '1' fixo pegou o carro ERRADO numa apólice com 2 veículos).
            from app.services.corridor_playbooks import pick_option_by_plate

            picked = pick_option_by_plate(insurer_message, str((session.get("slots") or {}).get("veiculo_placa") or ""))
            if picked:
                effective["reply"] = picked
            elif step.get("fallback_adaptive"):
                effective["reply"] = ""  # sem match seguro → adaptativo decide
        rendered = render_reply(effective, session.get("slots") or {})
        if step.get("dynamic") == "vehicle_by_plate" and not (rendered.get("reply") or "").strip():
            rendered = {"ok": False, "missing": ["veiculo_opcao"], "reply": None}
        if not rendered["ok"] and step.get("fallback_adaptive"):
            # Slot não deduzido (ex.: parser de endereço não achou o bairro) em
            # passo marcado fallback_adaptive → o cérebro adaptativo assume este
            # passo (ele tem o endereço completo do caso). Nunca chuta.
            pass
        elif not rendered["ok"]:
            session["state"] = "needs_human"
            session["reason"] = f"missing_slots:{','.join(rendered['missing'])}"
            session["missing_slots"] = rendered["missing"]
            return session
        else:
            # LOOP GUARD: nunca enviar a MESMA resposta À MESMA PERGUNTA 3x
            # (teste Yelum 2026-07-10: CPF repetido 4x até derrubar a conversa).
            if _would_loop(session, rendered["reply"], step_name):
                session["state"] = "needs_human"
                session["reason"] = "loop_guard"
                return session
            step_counts[step_name] = int(step_counts.get(step_name) or 0) + 1
            return _emit(session, rendered["reply"], sender=sender, next_state="ura", step=step_name)

    trigger = detect_handoff_trigger(playbook, insurer_message)
    if trigger:
        session["state"] = "needs_human"
        session["reason"] = f"handoff_trigger:{trigger}"
        return session

    # Pesquisa de satisfação/avaliação pós-atendimento: ignorar sempre.
    if re.search(_SURVEY_NOOP_RE, _norm_text(insurer_message), re.IGNORECASE):
        return session

    # Sem âncora de URA: fase humana da seguradora.
    if session.get("state") == "ura":
        session["state"] = "human_phase"
    # ANALISTA humano assumiu ("me chamo X, como posso ajudar?"): apresentar o
    # resumo estruturado do caso UMA vez, deterministicamente (é o que a
    # operadora real faz — colar o pedido completo para o analista).
    if (
        session.get("state") == "human_phase"
        and not session.get("summary_sent")
        and playbook.get("opening_template")
        and re.search(
            r"me chamo |meu nome [ée] |como posso (?:te )?ajudar|darei? (?:continuidade|prosseguimento)|"
            r"prosseguirei com o atendimento|irei realizar seu atendimento|vou te ajudar",
            _norm_text(insurer_message),
            re.IGNORECASE,
        )
    ):
        summary = render_opening_message(playbook, session.get("subservice") or "", session.get("slots") or {})
        session["summary_sent"] = True
        return _emit(session, summary, sender=sender, next_state="human_phase", step="resumo_analista")
    if session.get("state") == "human_phase" and human_phase_reply:
        if _would_loop(session, human_phase_reply, None):
            session["state"] = "needs_human"
            session["reason"] = "loop_guard"
            return session
        return _emit(session, human_phase_reply, sender=sender, next_state="human_phase")
    # Fail-safe: sem resposta preparada, não responde às cegas.
    session.setdefault("pending_insurer_messages", []).append(str(insurer_message)[:2000])
    return session


def _norm_text(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _would_loop(session: Dict[str, Any], reply: str, step: Optional[str] = None) -> bool:
    """True se as DUAS últimas saídas já foram a MESMA resposta À MESMA PERGUNTA
    (mesmo passo). Comparar só o texto dava FALSO POSITIVO (teste Allianz 12/07:
    a URA exige '1' legitimamente em passos seguidos — telefone ok=1,
    automotor=1, pane=1 — e o motor pausava achando que era loop)."""
    outs = [
        (t.get("text"), t.get("step"))
        for t in (session.get("transcript") or [])
        if t.get("direction") == "out"
    ]
    key = (reply, step)
    return len(outs) >= 2 and outs[-1] == key and outs[-2] == key


def build_human_phase_messages(session: Dict[str, Any], insurer_message: str,
                               ura_map: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
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
    # CÉREBRO v2 (SPEC-034): quando existe MAPA DE URA (Cartógrafo/Espelho), o
    # cérebro enxerga o TERRITÓRIO — todas as telas conhecidas e o que cada opção
    # faz — e decide pelo OBJETIVO mesmo se a tela atual mudou de texto.
    if ura_map:
        try:
            from app.services.ura_map_service import render_map_for_llm

            mapa_txt = render_map_for_llm(ura_map)
            if mapa_txt:
                guia_ura += ("\n\nMAPA COMPLETO DA URA DESTA SEGURADORA (telas conhecidas e o que "
                             "cada opção faz — localize a tela atual e escolha a opção que avança "
                             "para o objetivo do caso):\n" + mapa_txt)
        except Exception:  # noqa: BLE001 — mapa nunca derruba o prompt
            pass
    subservice = str(session.get("subservice") or "")
    line_kind = str(playbook.get("line_kind") or "residencial")
    insurer_key = str(playbook.get("insurer_key") or "seguradora")
    linha_txt = "AUTO (guincho, bateria, pneu, chaveiro)" if line_kind == "auto" else "residencial"
    # Freio de TESTE vale para TODAS as linhas (auto E residencial). Em modo LIVE
    # (corredor validado) a instrução vira: confirmar quando o RESUMO confere.
    if _finalize_allowed(session):
        finalize_rule = (
            "3. CONFIRMAÇÃO FINAL: quando a seguradora mostrar o RESUMO e pedir para confirmar, "
            "confira os dados com o caso; se conferem, CONFIRME com a opção afirmativa (ex.: '1' ou 'Sim'). "
            "Se algo divergir do caso, corrija com o dado certo ou responda NAO_SEI.\n"
        )
    else:
        finalize_rule = (
            "3. FREIO DE TESTE: se a seguradora for CONFIRMAR/ABRIR o serviço de fato (agendar, "
            "'posso continuar', 'podemos confirmar', RESUMO final), responda exatamente: NAO_SEI — "
            "este é um TESTE e o pedido NÃO pode ser aberto de verdade.\n"
        )
    system = (
        f"Você conduz, EM NOME DA CORRETORA, um acionamento de assistência {linha_txt} no WhatsApp da "
        f"seguradora ({insurer_key}) que JÁ está em andamento. Pode ser a URA (menu numerado/botões) "
        "ou um atendente humano.\n"
        f"Subserviço deste caso: {subservice or 'não informado'}.\n"
        "COMO DECIDIR (seja inteligente, não robótico):\n"
        "- Se a mensagem for um MENU, escolha a opção coerente com o subserviço/dados do caso e "
        "responda com o número OU o rótulo do botão (ex.: '2' ou 'Guincho'). Use o CONHECIMENTO DO FLUXO "
        "abaixo como guia, mesmo que o texto do menu tenha mudado.\n"
        "- Se pedir um dado do caso (CPF, placa, endereço/local, número, telefone), responda com o valor exato do caso.\n"
        "- Se for um atendente humano perguntando algo, responda em 1-2 frases curtas, PT-BR cordial.\n"
        "REGRAS INEGOCIÁVEIS:\n"
        "1. Use SOMENTE os dados do caso. NUNCA invente números, protocolos, prazos, valores ou dados.\n"
        "2. Não prometa nada em nome da seguradora; não confirme cobertura.\n"
        f"{finalize_rule}"
        "4. Se realmente NÃO der pra deduzir a resposta a partir do caso e do fluxo, responda exatamente: NAO_SEI"
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


def build_handoff_dossier(session: Dict[str, Any], reason: str = "") -> str:
    """Dossiê MASTIGADO para o humano assumir sem perguntar nada ao cliente
    (exigência do founder: 'entregar tudo mastigadinho'). Texto de WhatsApp."""
    playbook = get_playbook(session.get("playbook_ref") or "") or {}
    slots = session.get("slots") or {}
    captured = session.get("captured") or {}
    insurer = str(playbook.get("insurer_key") or "?").upper()
    linhas = [
        "🚨 *ATENDIMENTO PRECISA DE VOCÊ*",
        f"Seguradora: {insurer} · Serviço: {session.get('subservice') or '?'}",
        f"Motivo: {reason or session.get('reason') or 'handoff'}",
        "",
        "*Dados do caso:*",
    ]
    labels = {
        "titular_cpf": "CPF", "titular_nome": "Titular", "veiculo_placa": "Placa",
        "veiculo_descricao": "Veículo", "local_atual": "Local do veículo",
        "local_destino": "Destino", "problema_descricao": "Problema",
        "telefone_contato": "Telefone", "pessoa_no_local": "No local",
    }
    for key, label in labels.items():
        val = str(slots.get(key) or "").strip()
        if val:
            linhas.append(f"- {label}: {val}")
    if captured:
        linhas.append("")
        linhas.append("*Já capturado da seguradora:*")
        for k, v in captured.items():
            linhas.append(f"- {k}: {v}")
    tail = [t for t in (session.get("transcript") or []) if t.get("text")][-6:]
    if tail:
        linhas.append("")
        linhas.append("*Últimas mensagens com a seguradora:*")
        for t in tail:
            who = "corretora" if t.get("direction") == "out" else "seguradora"
            linhas.append(f"[{who}] {str(t.get('text'))[:160]}")
    linhas.append("")
    linhas.append(f"Cliente no WhatsApp: {session.get('client_phone') or '?'} — ele JÁ foi avisado que a equipe vai assumir.")
    linhas.append("Próxima ação sugerida: continuar a conversa com a seguradora do ponto acima (espelho completo na página Conversas).")
    return "\n".join(linhas)


def client_summary_from_capture(session: Dict[str, Any]) -> Optional[str]:
    """Mensagem pronta para o CLIENTE quando protocolo+agendamento capturados."""
    captured = session.get("captured") or {}
    if not captured.get("protocol"):
        return None
    playbook = get_playbook(session.get("playbook_ref") or "") or {}
    lines: List[str] = []
    schedule = captured.get("schedule") or {}
    if schedule and schedule.get("from"):
        lines.append(
            f"Prontinho! ✅ Sua assistência foi agendada para o dia {schedule.get('day')}, entre {schedule.get('from')} e {schedule.get('to')}."
        )
    elif schedule and schedule.get("day"):
        quando = f" às {schedule.get('at')}" if schedule.get("at") else ""
        lines.append(f"Prontinho! ✅ Sua assistência foi agendada para o dia {schedule.get('day')}{quando}.")
    elif captured.get("eta_minutes"):
        lines.append(f"Prontinho! ✅ Sua assistência foi aberta — previsão de chegada em até {captured['eta_minutes']} minutos.")
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
