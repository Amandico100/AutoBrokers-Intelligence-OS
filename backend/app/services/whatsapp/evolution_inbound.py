"""Normalizador de inbound do Evolution API v2 (SPEC-017 P1.2) — PURO.

Converte o webhook `messages.upsert` do Evolution para o dict legado que o
pipeline existente (ZAPIWebhookPayload/process_whatsapp_message_background)
já entende. Defensivo: campos ausentes viram None; grupos/status/fromMe são
sinalizados para o caller ignorar.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _text_from_message(message: Dict[str, Any]) -> Optional[str]:
    if not isinstance(message, dict):
        return None
    conversation = message.get("conversation")
    if isinstance(conversation, str) and conversation.strip():
        return conversation.strip()
    extended = message.get("extendedTextMessage")
    if isinstance(extended, dict):
        text = extended.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    for media_key in ("imageMessage", "videoMessage", "documentMessage"):
        media = message.get(media_key)
        if isinstance(media, dict):
            caption = media.get("caption")
            if isinstance(caption, str) and caption.strip():
                return caption.strip()
    return None


def _phone_from_jid(jid: Optional[str]) -> Optional[str]:
    if not isinstance(jid, str) or not jid:
        return None
    return jid.split("@")[0].split(":")[0] or None


def normalize_evolution_inbound(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Retorna dict normalizado:

    { skip: bool, skip_reason: str|None, message_id, phone, connected_phone,
      sender_name, text, is_group, from_me, timestamp }
    """
    out: Dict[str, Any] = {
        "skip": False, "skip_reason": None, "message_id": None, "phone": None,
        "connected_phone": None, "sender_name": None, "text": None,
        "is_group": False, "from_me": False, "timestamp": None, "media": None,
    }
    if not isinstance(payload, dict):
        return {**out, "skip": True, "skip_reason": "invalid_payload"}

    event = str(payload.get("event") or "").strip().lower().replace("_", ".")
    if event and event not in ("messages.upsert",):
        return {**out, "skip": True, "skip_reason": f"event:{event}"}

    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    key = data.get("key") if isinstance(data.get("key"), dict) else {}

    remote_jid = key.get("remoteJid") or data.get("remoteJid")
    from_me = bool(key.get("fromMe") or data.get("fromMe"))
    is_group = isinstance(remote_jid, str) and remote_jid.endswith("@g.us")
    message_id = key.get("id") or data.get("id") or data.get("messageId")

    msg_dict = data.get("message") if isinstance(data.get("message"), dict) else {}
    media = None
    for media_key, kind in (("imageMessage", "image"), ("documentMessage", "document"), ("documentWithCaptionMessage", "document"), ("audioMessage", "audio")):
        m = msg_dict.get(media_key)
        if media_key == "documentWithCaptionMessage" and isinstance(m, dict):
            m = ((m.get("message") or {}).get("documentMessage")) or m
        if isinstance(m, dict):
            media = {
                "kind": kind,
                "caption": (str(m.get("caption")).strip() or None) if m.get("caption") else None,
                "mimetype": m.get("mimetype") or None,
                "file_name": m.get("fileName") or m.get("title") or None,
                # webhookBase64=true: a Evolution manda a mídia JÁ decodificada
                # no próprio evento (campo base64 no message ou no data).
                "base64": msg_dict.get("base64") or data.get("base64") or None,
            }
            break

    out.update({
        "message_id": str(message_id) if message_id else None,
        "phone": _phone_from_jid(remote_jid),
        "connected_phone": _phone_from_jid(payload.get("sender")) or str(payload.get("instance") or "") or None,
        "sender_name": data.get("pushName") or None,
        "text": _text_from_message(msg_dict),
        "media": media,
        "is_group": is_group,
        "from_me": from_me,
        "timestamp": data.get("messageTimestamp"),
    })

    if from_me:
        return {**out, "skip": True, "skip_reason": "from_me"}
    if is_group:
        return {**out, "skip": True, "skip_reason": "group"}
    # Número pessoal do corretor conectado: Status (status@broadcast), canais
    # (@newsletter) e listas de transmissão (@broadcast) NUNCA viram atendimento.
    # Individuais legítimos (@s.whatsapp.net, @c.us, @lid) seguem passando.
    if isinstance(remote_jid, str) and remote_jid.endswith(("@broadcast", "@newsletter", "@call")):
        return {**out, "skip": True, "skip_reason": "non_individual"}
    if not out["phone"]:
        return {**out, "skip": True, "skip_reason": "no_phone"}
    if not out["text"] and not media:
        return {**out, "skip": True, "skip_reason": "no_text"}
    return out


def connection_state_from_payload(payload: Dict[str, Any]) -> Optional[str]:
    """Extrai estado de conexão de eventos `connection.update` (watchdog)."""
    if not isinstance(payload, dict):
        return None
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    state = data.get("state") or data.get("connection") or data.get("status")
    return str(state).strip().lower() if state else None
