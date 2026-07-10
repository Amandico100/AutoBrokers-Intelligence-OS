"""
Serviço WhatsApp (shim de compatibilidade) — 39A4.1.

Delega para o ZApiProvider (camada oficial de provider). Mantém a assinatura
send_message/send_audio/send_image usada por backend/app/api/webhook.py.

Segurança: nenhum log de URL/token/Client-Token aqui — toda a chamada Z-API
(e o mascaramento de telefone) vive em app/services/whatsapp/zapi_provider.py.
"""
import logging
from typing import Any, Dict, Optional

from app.services.whatsapp.zapi_provider import get_zapi_provider

logger = logging.getLogger(__name__)


class WhatsappService:
    """Compat: delega o envio Z-API para o ZApiProvider."""

    def __init__(self):
        logger.info("WhatsApp service initialized (delegates to ZApiProvider)")

    def send_message(self, to_number: str, text: str, integration: Dict[str, Any]) -> bool:
        """Envia texto. Retorna True em sucesso; levanta exceção em falha (contrato legado).

        SPEC-017 P1.2: provider != z-api envia pelo seam multi-provider
        (Evolution/uazapi); z-api mantém o caminho legado.
        S17-9: resposta longa vira balões curtos (humanização).
        """
        import time

        from app.services.whatsapp.balloons import split_whatsapp_balloons

        balloons = split_whatsapp_balloons(text) or [str(text or "")]
        provider_label = str((integration or {}).get("provider") or "z-api").strip().lower()

        if provider_label not in ("z-api", "zapi", ""):
            from app.services.whatsapp.registry import resolve_provider

            provider = resolve_provider(integration)
            send = lambda t: provider.send_text(to_number, t)  # noqa: E731
        else:
            send = lambda t: get_zapi_provider().send_text(to_number, t, integration)  # noqa: E731

        def _ok(result) -> bool:
            # SendResult do seam usa .ok; o provider z-api legado usa .success.
            # (Checar só .success foi a CAUSA das duplicatas: envio bom parecia
            # falha -> retry reenviava e a exceção matava os balões seguintes.)
            if hasattr(result, "ok"):
                return bool(result.ok)
            return bool(getattr(result, "success", False))

        for i, balloon in enumerate(balloons):
            if i > 0:
                time.sleep(0.7)  # cadência humana + evita throttle do provedor
            result = send(balloon)
            if _ok(result):
                continue
            # Falha: LOG COMPLETO (o bug do balão sumido era invisível) + retry.
            detail = getattr(result, "error", None) or getattr(result, "status_code", None) or getattr(result, "raw", None)
            logger.error(f"[WA SEND] balão {i + 1}/{len(balloons)} falhou (len={len(balloon)}): {str(detail)[:300]}")
            time.sleep(1.2)
            if _ok(send(balloon)):
                continue
            # Último recurso p/ balão grande: divide por linhas e envia pedaços.
            if len(balloon) > 400:
                lines = balloon.splitlines()
                mid = max(1, len(lines) // 2)
                pieces = ["\n".join(lines[:mid]).strip(), "\n".join(lines[mid:]).strip()]
                if all(_ok(send(p)) for p in pieces if p):
                    logger.warning(f"[WA SEND] balão {i + 1} entregue em 2 pedaços após falha")
                    continue
            raise Exception("Failed to send WhatsApp message")
        return True

    def send_audio(self, to_number: str, audio_url: str, integration: Dict[str, Any]) -> bool:
        return get_zapi_provider().send_audio(to_number, audio_url, integration).success

    def send_image(
        self, to_number: str, image_url: str, caption: str, integration: Dict[str, Any]
    ) -> bool:
        return get_zapi_provider().send_image(to_number, image_url, caption, integration).success

    def send_document(
        self,
        to_number: str,
        doc_url: str,
        filename: str,
        integration: Dict[str, Any],
        caption: str = "",
    ) -> bool:
        """Envia documento (ex.: boleto PDF) pelo seam multi-provider.

        Retorna bool; nunca levanta (falha vira False + log) — quem chama decide
        o fallback (ex.: mandar o link como texto). Contrato do seam usa `.ok`.
        """
        try:
            from app.services.whatsapp.models import OutboundMedia
            from app.services.whatsapp.registry import resolve_provider

            name = str(filename or "documento.pdf").strip() or "documento.pdf"
            mime = "application/pdf" if name.lower().endswith(".pdf") else None
            provider = resolve_provider(integration)
            result = provider.send_media(
                to_number,
                OutboundMedia(kind="document", url=doc_url, mime_type=mime, caption=caption or None, filename=name),
            )
            ok = bool(getattr(result, "ok", getattr(result, "success", False)))
            if not ok:
                logger.error(
                    "[WA SEND] documento falhou (%s): %s",
                    name,
                    str(getattr(result, "error", "") or "sem detalhe")[:200],
                )
            return ok
        except Exception as e:  # noqa: BLE001
            logger.error(f"[WA SEND] documento levantou excecao: {type(e).__name__}")
            return False


# Singleton instance
_whatsapp_service: Optional[WhatsappService] = None


def get_whatsapp_service() -> WhatsappService:
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsappService()
    return _whatsapp_service
