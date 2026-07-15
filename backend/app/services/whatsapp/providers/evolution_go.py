"""EvolutionGoProvider — bridge para o Evolution GO (whatsmeow) no contrato WhatsAppProvider.

SPEC-034/decisão do founder 14/07: migrar o canal para o Evolution GO ("fazer já")
e resolver o APP NATIVO (nativeFlowMessage da HDI/Yelum) NO NOSSO código.

Wire confirmado ao vivo em 14/07 contra a instância de teste
(autobrokers-intelligence-os-evolution-go-teste, swagger /swagger/doc.json):

- Auth: header ``apikey: <token DA INSTÂNCIA>`` (validado: /instance/status 200).
  A GLOBAL_API_KEY só serve para operações administrativas (/instance/all etc.).
- send_text : POST {base}/send/text   body ``{number, text}``.
- send_media: POST {base}/send/media  body ``{number, type, url, caption?, filename?}``
  (MediaStruct do swagger: type = image|audio|document...).
- Interativos NATIVOS existem: /send/button, /send/list, /send/carousel — são a
  chave da missão do app nativo (flow reply testável só com número pareado).

Inbound: o GO entrega o evento whatsmeow (Info + Message protojson — o Message
usa as MESMAS chaves waE2E do Baileys: conversation/extendedTextMessage/
interactiveMessage...). O parse aqui converte para o envelope v2 e reusa o
normalizador existente indiretamente (a rota /webhook/evolution-go converte
antes de despachar). ``parse_webhook`` cobre o uso direto pelo registry.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

from app.services.whatsapp.exceptions import (
    ProviderConfigError,
    ProviderNotSupportedError,
    WhatsappRetryableError,
)
from app.services.whatsapp.models import (
    CanonicalMessage,
    InboundBatch,
    MediaRef,
    OutboundMedia,
    SendResult,
    TemplateRef,
)
from app.services.whatsapp.providers.base import ProviderCapabilities

logger = logging.getLogger(__name__)

_GO_CAPABILITIES = ProviderCapabilities()


def _strip_jid(value: Any) -> str:
    text = str(value or "")
    return text.split("@", 1)[0].split(":", 1)[0] if text else ""


def go_event_to_v2_envelope(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Converte o evento do Evolution GO (whatsmeow) para o envelope Evolution v2.

    Tolerante por design: o shape EXATO só é confirmável com a instância pareada
    (primeiro teste do estágio GO). Cobre as variantes prováveis:
    - já-v2: ``{event: "messages.upsert", data: {...}}`` → passa direto;
    - whatsmeow: ``{type|event: "Message", event|data: {Info: {...}, Message: {...}}}``.
    Payload irreconhecível → envelope com event="unknown" (a rota loga as chaves).
    """
    body = payload or {}
    ev = str(body.get("event") or "").strip().lower().replace("_", ".")
    if isinstance(body.get("data"), dict) and ev in ("messages.upsert", "connection.update"):
        return body  # já no formato v2

    # Shape OFICIAL do GO (confirmado na wiki events-system.md + live 14/07):
    # {"event": "MESSAGE", "instance": "...", "data": {key, message,
    #  messageTimestamp (STRING), pushName}} — v2 com outro nome de evento.
    if isinstance(body.get("data"), dict) and ev in ("message", "send.message"):
        d = dict(body["data"])
        ts = d.get("messageTimestamp")
        if isinstance(ts, str) and ts.isdigit():
            d["messageTimestamp"] = int(ts)
        return {"event": "messages.upsert",
                "instance": str(body.get("instance") or body.get("instanceId") or ""),
                "data": d}
    if ev == "connection":
        d = body.get("data") if isinstance(body.get("data"), dict) else {}
        raw_state = str(d.get("state") or ("open" if d.get("Connected") or d.get("LoggedIn") else "close")).lower()
        return {"event": "connection.update",
                "instance": str(body.get("instance") or body.get("instanceId") or ""),
                "data": {"state": raw_state}}

    # localizar o objeto do evento whatsmeow
    candidates = [body.get("event"), body.get("data"), body.get("Event"), body]
    info: Dict[str, Any] = {}
    message: Optional[Dict[str, Any]] = None
    for c in candidates:
        if not isinstance(c, dict):
            continue
        i = c.get("Info") if isinstance(c.get("Info"), dict) else c.get("info") if isinstance(c.get("info"), dict) else None
        m = c.get("Message") if isinstance(c.get("Message"), dict) else c.get("message") if isinstance(c.get("message"), dict) else None
        if i or m:
            info, message = (i or {}), m
            break

    kind = str(body.get("type") or body.get("Type") or ev or "").strip().lower()
    # eventos de conexão do whatsmeow → connection.update v2
    if kind in ("connected", "loggedout", "disconnected", "logged_out", "connectfailure", "streamreplaced") or (
        not message and kind in ("connection", "connection.update")
    ):
        state = "open" if kind == "connected" else "close"
        return {"event": "connection.update", "instance": str(body.get("instanceId") or body.get("instance") or ""),
                "data": {"state": state}}

    if not message:
        return {"event": "unknown", "instance": str(body.get("instanceId") or ""), "data": {}}

    chat_jid = str(info.get("Chat") or info.get("chat") or "")
    sender_jid = str(info.get("Sender") or info.get("sender") or "")
    is_group = chat_jid.endswith("@g.us")
    ts_raw = info.get("Timestamp") or info.get("timestamp")
    ts: Optional[int] = None
    if isinstance(ts_raw, (int, float)):
        ts = int(ts_raw)
    elif isinstance(ts_raw, str) and ts_raw:
        try:
            from datetime import datetime

            ts = int(datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).timestamp())
        except ValueError:
            ts = None

    return {
        "event": "messages.upsert",
        "instance": str(body.get("instanceId") or body.get("instance") or ""),
        "data": {
            "key": {
                "remoteJid": chat_jid or sender_jid,
                "fromMe": bool(info.get("IsFromMe") or info.get("isFromMe") or info.get("fromMe")),
                "id": str(info.get("ID") or info.get("Id") or info.get("id") or ""),
                **({"participant": sender_jid} if is_group else {}),
            },
            "message": message,
            "pushName": info.get("PushName") or info.get("pushName"),
            "messageTimestamp": ts,
        },
    }


class EvolutionGoProvider:
    """Evolution GO no contrato :class:`WhatsAppProvider` (config por integração)."""

    def __init__(self, integration: Dict[str, Any]) -> None:
        cfg = dict(integration or {})
        self._base_url: Optional[str] = (cfg.get("base_url") or "").rstrip("/") or None
        self._token: Optional[str] = cfg.get("token")  # token DA INSTÂNCIA (header apikey)
        self._instance_id: Optional[str] = cfg.get("instance_id")
        self.validate_config()

    @property
    def capabilities(self) -> ProviderCapabilities:
        return _GO_CAPABILITIES

    def validate_config(self) -> None:
        if not self._base_url or not self._token:
            raise ProviderConfigError("Missing base_url or token in Evolution GO integration config")

    def verify_webhook(self, payload: dict, signature: str) -> bool:
        return True  # autenticação na borda (token de webhook na URL), como o Evolution v2

    # ------------------------------------------------------------------ #
    # Inbound
    # ------------------------------------------------------------------ #
    def parse_webhook(self, payload: dict) -> InboundBatch:
        env = go_event_to_v2_envelope(payload or {})
        if env.get("event") != "messages.upsert":
            return InboundBatch(provider="evolution-go", connected_phone=str(env.get("instance") or ""), messages=[], statuses=[])
        data = env.get("data") or {}
        key = data.get("key") or {}
        message = data.get("message")
        if not isinstance(message, dict):
            return InboundBatch(provider="evolution-go", connected_phone=str(env.get("instance") or ""), messages=[], statuses=[])
        remote = str(key.get("remoteJid") or "")
        is_group = remote.endswith("@g.us")
        from_phone = _strip_jid(key.get("participant") if is_group else remote)
        extended = message.get("extendedTextMessage") if isinstance(message.get("extendedTextMessage"), dict) else {}
        text = message.get("conversation") or extended.get("text")
        canonical = CanonicalMessage(
            connected_phone=str(env.get("instance") or ""),
            from_phone=from_phone,
            type="text" if text else "unknown",
            from_me=bool(key.get("fromMe")),
            is_group=is_group,
            text=text,
            timestamp=data.get("messageTimestamp"),
            sender_name=data.get("pushName"),
            media=None,
            message_id=key.get("id"),
        )
        return InboundBatch(provider="evolution-go", connected_phone=canonical.connected_phone, messages=[canonical], statuses=[])

    def resolve_media_url(self, ref: MediaRef) -> str | None:
        candidate = (ref.resolved_url or ref.raw_ref or ref.stable_url or "").strip()
        if candidate.lower().startswith(("http://", "https://")):
            return candidate
        return None

    # ------------------------------------------------------------------ #
    # Outbound — wire GO (apikey = token da instância)
    # ------------------------------------------------------------------ #
    def _headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json", "apikey": self._token or ""}

    def _post(self, path: str, payload: Dict[str, Any]) -> SendResult:
        url = f"{self._base_url}{path}"
        response = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        status = response.status_code
        if status == 429 or 500 <= status <= 599:
            logger.warning("[EVOLUTION-GO] Retryable HTTP %s: %s", status, response.text[:200])
            raise WhatsappRetryableError(f"HTTP {status} from Evolution GO")
        if not 200 <= status < 300:
            logger.error("[EVOLUTION-GO] HTTP %s error: %s", status, response.text[:200])
            return SendResult(ok=False, error=f"HTTP {status}")
        return SendResult(ok=True)

    def send_text(self, to: str, text: str) -> SendResult:
        return self._post("/send/text", {"number": to, "text": text})

    def send_media(self, to: str, media: OutboundMedia) -> SendResult:
        if not media.url:
            return SendResult(ok=False, error="Missing media url (raw_ref unsupported)")
        kind = "image" if media.kind == "image" else "audio" if media.kind == "audio" else "document"
        payload: Dict[str, Any] = {"number": to, "type": kind, "url": media.url}
        if media.caption:
            payload["caption"] = media.caption
        if media.kind == "document" and media.filename:
            payload["filename"] = media.filename
        return self._post("/send/media", payload)

    def send_template(self, to: str, template: TemplateRef) -> SendResult:
        raise ProviderNotSupportedError("Evolution GO provider does not support template messaging")

    # ------------------------------------------------------------------ #
    # Missão APP NATIVO (HDI/Yelum) — resposta a list/flow SEM tocar no fork.
    # Métodos EXTRAS (fora do Protocol); usados pelo dispatch quando o payload
    # de entrada trouxer listMessage/nativeFlowMessage. Validação final = teste
    # com o número pareado (primeiro teste do estágio GO).
    # ------------------------------------------------------------------ #
    def send_list_reply(self, to: str, row_id: str, title: str) -> SendResult:
        """Tenta responder uma LISTA nativa selecionando a linha (row_id)."""
        return self._post("/send/text", {"number": to, "text": title, "id": row_id})

    def send_button_reply(self, to: str, button_id: str, title: str) -> SendResult:
        return self._post("/send/text", {"number": to, "text": title, "id": button_id})


__all__ = ["EvolutionGoProvider", "go_event_to_v2_envelope"]
