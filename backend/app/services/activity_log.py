"""ATIVIDADES (SPEC-036) — o feed do "olha quanta coisa fazemos por você".

Toda ação relevante dos agentes vira uma linha COMERCIAL em agent_activities:
alimenta a página Atividades do dashboard (tempo real) e o relatório de sábado.
Best-effort — nunca derruba quem chama. Nomes de papel, nunca nomes próprios.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

CATEGORIES = ("atendimentos", "acionamentos", "qualidade", "conhecimento", "inteligencia")

# Estados de acionamento → linha comercial no feed.
DISPATCH_STATE_TITLES = {
    "ura": ("acionamentos", "Acionamento iniciado — {label}",
            "Conversa aberta com a assistência 24h; acompanhamento automático ativo."),
    "human_phase": ("acionamentos", "Analista da {label} acionado",
                    "Caso entregue ao especialista da seguradora com o resumo completo."),
    "captured": ("acionamentos", "Protocolo garantido — {label}",
                 "Serviço confirmado junto à seguradora; monitorando a chegada do prestador."),
    "monitoring": ("acionamentos", "Monitoramento premium ativo — {label}",
                   "Acompanhando o prestador e mantendo o cliente informado até o fim."),
    "test_aborted": ("acionamentos", "Simulação completa — {label}",
                     "Fluxo executado de ponta a ponta em modo de validação."),
    "needs_human": ("acionamentos", "Dossiê entregue à equipe — {label}",
                    "Caso preparado e transferido com todos os dados mastigados."),
}


async def log_activity(company_id: str, category: str, title: str, detail: str = "") -> None:
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        await asyncio.to_thread(
            lambda: db.client.table("agent_activities").insert({
                "company_id": company_id, "category": category,
                "title": title[:180], "detail": detail[:400],
            }).execute()
        )
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[ATIVIDADES] log falhou: {type(e).__name__}")


async def log_dispatch_transition(company_id: str, session: dict, insurer_label: str) -> Optional[str]:
    """Chamado pelo Espelho a cada save: registra a TRANSIÇÃO de estado como
    atividade comercial (1x por estado, marcador na sessão)."""
    state = str(session.get("state") or "")
    if state == str(session.get("_act_logged_state") or ""):
        return None
    entry = DISPATCH_STATE_TITLES.get(state)
    if not entry:
        return None
    category, title_tpl, detail = entry
    await log_activity(company_id, category, title_tpl.format(label=insurer_label), detail)
    session["_act_logged_state"] = state
    return state
