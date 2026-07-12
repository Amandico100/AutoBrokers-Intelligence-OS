"""Normalizador de inbound do Evolution API v2 (SPEC-017 P1.2) — PURO.

Converte o webhook `messages.upsert` do Evolution para o dict legado que o
pipeline existente (ZAPIWebhookPayload/process_whatsapp_message_background)
já entende. Defensivo: campos ausentes viram None; grupos/status/fromMe são
sinalizados para o caller ignorar.

INTERATIVAS (incidente 2026-07-12): as URAs das seguradoras mandam BOTÕES,
LISTAS (modais) e FORMULÁRIOS nativos (flows). Antes, essas mensagens caíam em
skip:no_text — o atendente ficava CEGO para elas (e o espelho do dashboard,
incompleto). Agora são renderizadas em texto NO MESMO FORMATO dos exports do
WhatsApp usados para minerar os corredores ("Botão 1: X" / linhas de lista),
então as âncoras dos playbooks casam sem mudança. Os metadados (ids, flow)
seguem em `interactive` para respostas estruturadas futuras.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

# Wrappers que embrulham a mensagem real (interativas costumam vir dentro).
_WRAPPER_KEYS = (
    "viewOnceMessage", "viewOnceMessageV2", "viewOnceMessageV2Extension",
    "ephemeralMessage", "documentWithCaptionMessage",
)


def _unwrap_message(message: Dict[str, Any]) -> Dict[str, Any]:
    seen = 0
    while isinstance(message, dict) and seen < 4:
        wrapped = None
        for key in _WRAPPER_KEYS:
            inner = message.get(key)
            if isinstance(inner, dict) and isinstance(inner.get("message"), dict):
                wrapped = inner["message"]
                break
        if wrapped is None:
            return message
        message = wrapped
        seen += 1
    return message if isinstance(message, dict) else {}


def _clean(text: Any) -> str:
    return str(text).strip() if isinstance(text, str) and text.strip() else ""


def _interactive_from_message(message: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """(texto_renderizado, metadados) para botões/listas/templates/flows.

    O texto imita o formato dos exports do WhatsApp (fonte dos playbooks):
    - botões:  corpo + "Botão 1: X" por botão;
    - lista:   corpo + "Título — descrição" por linha + nome do botão do modal;
    - flow:    corpo + marcador [FORMULARIO NATIVO: <cta>] (não responder por texto).
    """
    if not isinstance(message, dict):
        return None

    # --- buttonsMessage (quick replies clássicos) ---
    btns_msg = message.get("buttonsMessage")
    if isinstance(btns_msg, dict):
        body = _clean(btns_msg.get("contentText")) or _clean(btns_msg.get("text"))
        options: List[Dict[str, str]] = []
        for b in btns_msg.get("buttons") or []:
            if not isinstance(b, dict):
                continue
            title = _clean((b.get("buttonText") or {}).get("displayText"))
            if title:
                options.append({"id": _clean(b.get("buttonId")), "title": title})
        if body or options:
            lines = [body] if body else []
            lines += [f"Botão {i}: {o['title']}" for i, o in enumerate(options, 1)]
            return "\n".join(lines), {"kind": "buttons", "options": options}

    # --- templateMessage (hydratedTemplate) ---
    tpl = message.get("templateMessage")
    if isinstance(tpl, dict):
        hyd = tpl.get("hydratedTemplate") or tpl.get("hydratedFourRowTemplate") or {}
        if isinstance(hyd, dict):
            body = _clean(hyd.get("hydratedContentText"))
            options = []
            for b in hyd.get("hydratedButtons") or []:
                if not isinstance(b, dict):
                    continue
                qr = b.get("quickReplyButton")
                if isinstance(qr, dict) and _clean(qr.get("displayText")):
                    options.append({"id": _clean(qr.get("id")), "title": _clean(qr.get("displayText"))})
            if body or options:
                lines = [body] if body else []
                lines += [f"Botão {i}: {o['title']}" for i, o in enumerate(options, 1)]
                return "\n".join(lines), {"kind": "buttons", "options": options}

    # --- listMessage (modal de opções) ---
    lst = message.get("listMessage")
    if isinstance(lst, dict):
        body = _clean(lst.get("description")) or _clean(lst.get("title"))
        button_label = _clean(lst.get("buttonText"))
        options = []
        for section in lst.get("sections") or []:
            for row in (section or {}).get("rows") or []:
                if not isinstance(row, dict):
                    continue
                title = _clean(row.get("title"))
                if title:
                    options.append({
                        "id": _clean(row.get("rowId")), "title": title,
                        "description": _clean(row.get("description")),
                    })
        if body or options:
            lines = [body] if body else []
            for o in options:
                lines.append(o["title"] + (f"\n{o['description']}" if o.get("description") else ""))
            meta = {"kind": "list", "options": options}
            if button_label:
                meta["button_label"] = button_label
            return "\n".join(lines), meta

    # --- interactiveMessage (native flow: quick_reply/single_select/flow) ---
    inter = message.get("interactiveMessage")
    if isinstance(inter, dict):
        body = _clean((inter.get("body") or {}).get("text")) or _clean((inter.get("header") or {}).get("title"))
        nfm = inter.get("nativeFlowMessage") or {}
        options = []
        flow_meta: Optional[Dict[str, Any]] = None
        for b in (nfm.get("buttons") or []):
            if not isinstance(b, dict):
                continue
            name = _clean(b.get("name"))
            try:
                params = json.loads(b.get("buttonParamsJson") or "{}")
            except Exception:  # noqa: BLE001
                params = {}
            if name == "quick_reply":
                title = _clean(params.get("display_text"))
                if title:
                    options.append({"id": _clean(params.get("id")), "title": title})
            elif name == "single_select":
                for section in params.get("sections") or []:
                    for row in (section or {}).get("rows") or []:
                        title = _clean(row.get("title"))
                        if title:
                            options.append({
                                "id": _clean(row.get("id")), "title": title,
                                "description": _clean(row.get("description")),
                            })
            elif name in ("flow", "mpm", "wa_payment_details", "review_and_pay"):
                flow_meta = {
                    "name": name,
                    "cta": _clean(params.get("flow_cta")) or _clean(params.get("display_text")),
                    "flow_id": params.get("flow_id") or params.get("flow_name"),
                    "flow_token": params.get("flow_token"),
                }
        if flow_meta:
            lines = [body] if body else []
            lines.append(f"[FORMULARIO NATIVO: {flow_meta.get('cta') or 'formulário'}] (exige clique — não aceita texto)")
            return "\n".join(lines), {"kind": "flow", "flow": flow_meta, "options": options}
        if body or options:
            lines = [body] if body else []
            for o in options:
                lines.append(o["title"] + (f"\n{o['description']}" if o.get("description") else ""))
            return "\n".join(lines), {"kind": "list" if any(o.get("description") for o in options) else "buttons", "options": options}

    return None


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
    # RESPOSTAS interativas (clique em botão/lista — ex.: humano copilotando a
    # URA com fromMe, ou cliente respondendo lista): extrair o rótulo escolhido.
    btn_resp = message.get("buttonsResponseMessage")
    if isinstance(btn_resp, dict):
        picked = _clean(btn_resp.get("selectedDisplayText")) or _clean(btn_resp.get("selectedButtonId"))
        if picked:
            return picked
    tpl_resp = message.get("templateButtonReplyMessage")
    if isinstance(tpl_resp, dict) and _clean(tpl_resp.get("selectedDisplayText")):
        return _clean(tpl_resp.get("selectedDisplayText"))
    lst_resp = message.get("listResponseMessage")
    if isinstance(lst_resp, dict):
        picked = _clean(lst_resp.get("title")) or _clean((lst_resp.get("singleSelectReply") or {}).get("selectedRowId"))
        if picked:
            return picked
    inter_resp = message.get("interactiveResponseMessage")
    if isinstance(inter_resp, dict):
        picked = _clean((inter_resp.get("body") or {}).get("text"))
        if picked:
            return picked
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
        "interactive": None,
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
    msg_dict = _unwrap_message(msg_dict)
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

    text = _text_from_message(msg_dict)
    interactive = None
    if not text and not media:
        rendered = _interactive_from_message(msg_dict)
        if rendered:
            text, interactive = rendered

    out.update({
        "message_id": str(message_id) if message_id else None,
        "phone": _phone_from_jid(remote_jid),
        "connected_phone": _phone_from_jid(payload.get("sender")) or str(payload.get("instance") or "") or None,
        "sender_name": data.get("pushName") or None,
        "text": text,
        "media": media,
        "interactive": interactive,
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
