"""ESPELHO (SPEC-034 Onda 1) — persistência total das conversas com seguradoras.

Problema (13/07): a conversa do motor de acionamento com a URA vivia SÓ no Redis
(TTL 6h) — invisível no dashboard, inauditável depois. O Espelho grava cada
mensagem in/out em conversations/messages (Supabase), exatamente como o agente
a vê (botões já renderizados como "Botão 1: ..."), lincada por caso.

Ponto único de captura: save_active_dispatch() chama mirror_session() antes de
persistir no Redis — todo caminho que anota transcript passa por lá (start,
inbound da URA, sentinela, follow-up, outbound manual).

Regras: best-effort — o Espelho NUNCA bloqueia nem derruba o roteamento.
Idempotente via session["mirror_idx"] (quantas entradas já foram espelhadas).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_INSURER_LABELS = {
    "allianz": "Allianz", "alfa": "Alfa", "porto": "Porto Seguro", "azul": "Azul Seguros",
    "bradesco": "Bradesco Seguros", "hdi": "HDI", "yelum": "Yelum", "zurich": "Zurich",
    "tokio": "Tokio Marine", "suhai": "Suhai", "mapfre": "Mapfre", "sura": "Sura",
    "sompo": "Sompo", "itau": "Itaú Seguros", "mitsui": "Mitsui",
}


def insurer_label_from_ref(playbook_ref: str) -> str:
    key = str(playbook_ref or "").split("-", 1)[0].strip().lower()
    return _INSURER_LABELS.get(key, key.capitalize() or "Seguradora")


def _enabled() -> bool:
    return os.getenv("DISPATCH_MIRROR", "1").strip() != "0"


async def mirror_session(company_id: str, insurer_phone: str, session: Dict[str, Any]) -> None:
    """Espelha as entradas NOVAS do transcript. Muta session (mirror_idx/conv id);
    o caller persiste a sessão em seguida (save_active_dispatch)."""
    try:
        transcript = session.get("transcript") or []
        idx = int(session.get("mirror_idx") or 0)
        if not _enabled() or len(transcript) <= idx:
            return
        new_entries = transcript[idx:]

        from app.core.database import get_supabase_client

        db = get_supabase_client()
        conv_id = session.get("mirror_conversation_id") or await _get_or_create_conversation(
            db, company_id, insurer_phone, session
        )
        if not conv_id:
            return
        session["mirror_conversation_id"] = conv_id

        rows = []
        for entry in new_entries:
            text = str(entry.get("text") or "").strip()
            if not text:
                continue
            role = "user" if str(entry.get("direction") or "") == "in" else "assistant"
            row = {"conversation_id": conv_id, "role": role, "content": text, "type": "text"}
            if entry.get("at"):
                row["created_at"] = str(entry["at"])
            rows.append(row)
        if rows:
            await asyncio.to_thread(lambda: db.client.table("messages").insert(rows).execute())
            last = rows[-1]
            inbound = sum(1 for r in rows if r["role"] == "user")
            update: Dict[str, Any] = {
                "last_message_preview": last["content"][:100],
                "last_message_at": last.get("created_at") or _now_iso(),
            }
            if inbound:
                update["unread_count"] = int(session.get("mirror_unread") or 0) + inbound
                session["mirror_unread"] = update["unread_count"]
            await asyncio.to_thread(
                lambda: db.client.table("conversations").update(update).eq("id", conv_id).execute()
            )
        session["mirror_idx"] = len(transcript)
        try:
            from app.core.heartbeat import beat

            await beat("espelho", len(rows))
        except Exception:  # noqa: BLE001
            pass
        # ATIVIDADES (SPEC-036): transição de estado vira linha comercial no feed.
        try:
            from app.services.activity_log import log_dispatch_transition

            await log_dispatch_transition(
                company_id, session, insurer_label_from_ref(session.get("playbook_ref")))
        except Exception:  # noqa: BLE001
            pass
    except Exception as e:  # noqa: BLE001 — o Espelho nunca derruba o motor
        logger.warning(f"[MIRROR] espelhamento falhou (segue sem espelho): {type(e).__name__}")


async def _get_or_create_conversation(
    db, company_id: str, insurer_phone: str, session: Dict[str, Any]
) -> Optional[str]:
    digits = "".join(ch for ch in str(insurer_phone or "") if ch.isdigit())
    case_id = str(session.get("case_id") or "sem-caso")
    session_id = f"dispatch:{digits}:{company_id}:{case_id}"
    found = await asyncio.to_thread(
        lambda: db.client.table("conversations")
        .select("id")
        .eq("company_id", company_id)
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )
    if found.data:
        return found.data[0]["id"]

    label = insurer_label_from_ref(session.get("playbook_ref"))
    subservice = str(session.get("subservice") or "").strip()
    title = f"Acionamento — {label}" + (f" ({subservice})" if subservice else "")
    user_id = None
    try:
        from app.services.integration_service import get_integration_service

        user_id = await asyncio.to_thread(
            lambda: get_integration_service().get_or_create_user(
                phone=digits, company_id=company_id, name=title
            )
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[MIRROR] get_or_create_user falhou: {type(e).__name__}")
    if not user_id:
        return None

    new_conv = {
        "company_id": company_id,
        "user_id": user_id,
        "session_id": session_id,
        "agent_id": None,
        "user_name": title,
        "user_phone": digits,
        "channel": "whatsapp",
        "agent_name": "Motor de Acionamento",
        "status": "open",
        "status_color": "green",
        "unread_count": 0,
        "last_message_preview": "",
        "last_message_at": _now_iso(),
    }
    created = await asyncio.to_thread(
        lambda: db.client.table("conversations").insert(new_conv).execute()
    )
    return created.data[0]["id"] if created.data else None


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
