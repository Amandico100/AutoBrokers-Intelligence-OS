"""SIMULADOR DE URA (SPEC-034 Onda 2) — gêmeo digital dos corredores.

Cada conversa real espelhada (Espelho) vira um SCRIPT: a sequência de telas que
a seguradora mandou. O simulador reapresenta essas telas ao motor de corredor e
compara as respostas do playbook ATUAL com as que funcionaram na vida real.

Usos: validar mudança de playbook ANTES de produção (Alfaiate, Onda 4);
transformar cada atendimento de hoje em teste de regressão de amanhã.
Puro — roda sem WhatsApp, sem Redis, sem rede.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def script_from_transcript(transcript: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extrai do transcript real os pares tela-da-URA → nossa-resposta-que-funcionou.
    Telas sem resposta nossa (informativos) entram com expected=None."""
    script: List[Dict[str, Any]] = []
    for entry in transcript or []:
        if entry.get("direction") == "in":
            script.append({"screen": str(entry.get("text") or ""), "expected": None})
        elif entry.get("direction") == "out" and script:
            if script[-1]["expected"] is None:
                script[-1]["expected"] = str(entry.get("text") or "")
    return [s for s in script if s["screen"].strip()]


def simulate(playbook_ref: str, subservice: str, slots: Dict[str, Any],
             script: List[Dict[str, Optional[str]]]) -> Dict[str, Any]:
    """Roda o motor de corredor contra o script. Divergência ≠ erro necessariamente
    (playbook pode ter melhorado) — é sinal para revisão humana/Auditor."""
    from app.services import insurer_dispatch_service as eng

    session = eng.new_dispatch_session(
        case_id="sim", company_id="sim", playbook_ref=playbook_ref,
        subservice=subservice, slots=dict(slots or {}),
    )
    session = eng.start_dispatch(session)
    divergences: List[Dict[str, Any]] = []
    unanswered: List[str] = []
    reached_finalize = False

    for step_idx, item in enumerate(script or []):
        screen = str(item.get("screen") or "")
        before = len([t for t in session["transcript"] if t["direction"] == "out"])
        session = eng.handle_insurer_message(session, screen)
        outs = [t for t in session["transcript"] if t["direction"] == "out"]
        replied = outs[before]["text"] if len(outs) > before else None
        expected = item.get("expected")

        # O simulador para em TODA fase encerrada, não só em `test_aborted`.
        #
        # 📊 Auditoria de 03/08: ele só reconhecia `test_aborted` e `needs_human`.
        # Um caso que terminasse em `encaminhado` — desfecho de SUCESSO, a
        # seguradora entregou o formulário — não era reconhecido como fim, e o
        # simulador seguia alimentando telas a um corredor que já tinha acabado.
        #
        # Ler a lista canônica em vez de escrever os nomes aqui é o que impede
        # este arquivo de envelhecer de novo no próximo desfecho novo.
        from app.services.insurer_dispatch_service import FASES_ENCERRADAS

        estado_atual = str(session.get("state") or "")
        if estado_atual in FASES_ENCERRADAS and estado_atual != "needs_human":
            reached_finalize = True
            break
        if session.get("state") == "needs_human":
            divergences.append({"step": step_idx, "screen": screen[:100],
                                "expected": expected, "got": f"needs_human:{session.get('reason')}"})
            break
        if expected and replied is None:
            unanswered.append(screen[:100])
        elif expected and replied and replied.strip().lower() != str(expected).strip().lower():
            divergences.append({"step": step_idx, "screen": screen[:100],
                                "expected": expected, "got": replied})

    return {
        "ok": not divergences and not unanswered,
        "reached_finalize": reached_finalize,
        "divergences": divergences,
        "unanswered_screens": unanswered,
        "final_state": session.get("state"),
    }
