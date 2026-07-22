"""Normalização inbound do Evolution GO, sem qualquer dependência de envio.

Este módulo é deliberadamente puro para que o Observador possa interpretar
eventos whatsmeow sem importar um provider capaz de enviar mensagens.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional


def go_event_to_v2_envelope(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Converte eventos GO/whatsmeow para o envelope Evolution v2."""
    body = payload or {}
    ev = str(body.get("event") or "").strip().lower().replace("_", ".")
    if isinstance(body.get("data"), dict) and ev in ("messages.upsert", "connection.update"):
        return body

    if (
        isinstance(body.get("data"), dict)
        and ev in ("message", "send.message")
        and isinstance(body["data"].get("key"), dict)
    ):
        data = dict(body["data"])
        timestamp = data.get("messageTimestamp")
        if isinstance(timestamp, str) and timestamp.isdigit():
            data["messageTimestamp"] = int(timestamp)
        return {
            "event": "messages.upsert",
            "instance": str(body.get("instance") or body.get("instanceId") or ""),
            "data": data,
        }

    if ev == "connection":
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        raw_state = str(
            data.get("state")
            or ("open" if data.get("Connected") or data.get("LoggedIn") else "close")
        ).lower()
        return {
            "event": "connection.update",
            "instance": str(body.get("instance") or body.get("instanceId") or ""),
            "data": {"state": raw_state},
        }

    force_from_me = ev in ("sendmessage", "send.message")
    candidates = [body.get("event"), body.get("data"), body.get("Event"), body]
    info: Dict[str, Any] = {}
    message: Optional[Dict[str, Any]] = None
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_info = (
            candidate.get("Info")
            if isinstance(candidate.get("Info"), dict)
            else candidate.get("info") if isinstance(candidate.get("info"), dict) else None
        )
        candidate_message = (
            candidate.get("Message")
            if isinstance(candidate.get("Message"), dict)
            else candidate.get("message") if isinstance(candidate.get("message"), dict) else None
        )
        if candidate_info or candidate_message:
            info, message = candidate_info or {}, candidate_message
            break

    kind = str(body.get("type") or body.get("Type") or ev or "").strip().lower()
    if kind in (
        "connected", "loggedout", "disconnected", "logged_out",
        "connectfailure", "streamreplaced",
    ) or (not message and kind in ("connection", "connection.update")):
        return {
            "event": "connection.update",
            "instance": str(body.get("instanceId") or body.get("instance") or ""),
            "data": {
                "state": "open" if kind == "connected" else "close",
                "reason": (
                    "re_pair_required" if kind in ("loggedout", "logged_out")
                    else "passkey_socket_restarted" if kind == "streamreplaced" else kind
                ),
            },
        }

    if not message:
        return {
            "event": "unknown",
            "instance": str(body.get("instanceId") or body.get("instance") or ""),
            "data": {},
        }

    chat_jid = str(info.get("Chat") or info.get("chat") or "")
    sender_jid = str(info.get("Sender") or info.get("sender") or "")
    from_me = force_from_me or bool(
        info.get("IsFromMe") or info.get("isFromMe") or info.get("fromMe")
    )
    # whatsmeow may address a direct chat by @lid while exposing the phone JID
    # in the alternate sender/recipient field. Preserve it for the privacy
    # boundary; never infer a phone number from the opaque LID itself.
    sender_alt = str(info.get("SenderAlt") or info.get("senderAlt") or "")
    recipient_alt = str(info.get("RecipientAlt") or info.get("recipientAlt") or "")
    chat_alt = str(info.get("ChatAlt") or info.get("chatAlt") or "")
    remote_alt = chat_alt or (recipient_alt if from_me else sender_alt)
    is_group = chat_jid.endswith("@g.us")
    timestamp_raw = info.get("Timestamp") or info.get("timestamp")
    timestamp: Optional[int] = None
    if isinstance(timestamp_raw, (int, float)):
        timestamp = int(timestamp_raw)
    elif isinstance(timestamp_raw, str) and timestamp_raw:
        try:
            timestamp = int(datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00")).timestamp())
        except ValueError:
            timestamp = None

    return {
        "event": "messages.upsert",
        "instance": str(body.get("instanceId") or body.get("instance") or ""),
        "data": {
            "key": {
                "remoteJid": chat_jid or sender_jid,
                "fromMe": from_me,
                "id": str(info.get("ID") or info.get("Id") or info.get("id") or ""),
                **({"remoteJidAlt": remote_alt} if remote_alt.endswith("@s.whatsapp.net") else {}),
                **({"participant": sender_jid} if is_group else {}),
            },
            "message": message,
            "pushName": info.get("PushName") or info.get("pushName"),
            "messageTimestamp": timestamp,
        },
    }


__all__ = ["go_event_to_v2_envelope"]
