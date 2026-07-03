"""Alerta de desconexão do WhatsApp da corretora (SPEC-017 S17-3).

Exigência do Founder: se o QR cair, alguém da corretora recebe WhatsApp NA HORA
para reconectar. Regras:
- o alerta NUNCA sai pelo número de atendimento da corretora (ele caiu);
- sai pela INSTÂNCIA-PLATAFORMA de alertas do AutoBrokers (Evolution, env);
- destino = alert_target da integração (número/grupo configurado no dashboard),
  com fallback para o número global de operação da plataforma;
- NUNCA e-mail. Falha de alerta não pode explodir o webhook (log e segue).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _platform_alert_integration() -> Optional[Dict[str, Any]]:
    base_url = os.getenv("PLATFORM_ALERT_WA_BASE_URL")
    instance_id = os.getenv("PLATFORM_ALERT_WA_INSTANCE_ID")
    token = os.getenv("PLATFORM_ALERT_WA_TOKEN")
    if not (base_url and instance_id and token):
        return None
    return {"provider": "evolution", "base_url": base_url, "instance_id": instance_id, "token": token}


def _alert_number(integration: Dict[str, Any]) -> Optional[str]:
    target = integration.get("alert_target")
    if isinstance(target, str):
        try:
            target = json.loads(target)
        except Exception:  # noqa: BLE001
            target = {"number": target}
    if isinstance(target, dict):
        number = str(target.get("number") or target.get("group") or "").strip()
        if number:
            return number
    fallback = os.getenv("PLATFORM_ALERT_FALLBACK_NUMBER", "").strip()
    return fallback or None


def send_disconnect_alert(integration: Dict[str, Any], state: str) -> bool:
    """Envia o alerta de desconexão. True = enviado. Nunca levanta exceção."""
    try:
        platform = _platform_alert_integration()
        if not platform:
            logger.error("[WA ALERT] instância-plataforma de alertas não configurada (PLATFORM_ALERT_WA_*)")
            return False
        number = _alert_number(integration)
        if not number:
            logger.error("[WA ALERT] alert_target ausente na integração e sem fallback global")
            return False

        connected = str(integration.get("identifier") or "")
        masked = f"...{connected[-4:]}" if connected else "(sem número)"
        text = (
            "⚠️ *AutoBrokers — WhatsApp desconectado*\n\n"
            f"O WhatsApp de atendimento {masked} da corretora se desconectou "
            f"(status: {state}).\n\n"
            "Os segurados NÃO estão sendo atendidos por esse número até reconectar.\n"
            "Acesse: Dashboard → Personalização → Conectores → WhatsApp → *Reconectar (QR code)*."
        )

        from app.services.whatsapp.registry import resolve_provider

        provider = resolve_provider(platform)
        result = provider.send_text(number, text)
        success = bool(getattr(result, "success", False))
        logger.info(f"[WA ALERT] disconnect alert sent={success} target=...{number[-4:]}")
        return success
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WA ALERT] failed: {type(e).__name__}")
        return False
