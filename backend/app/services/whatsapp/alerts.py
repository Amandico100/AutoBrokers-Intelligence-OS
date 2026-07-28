"""Alerta de desconexão do WhatsApp da corretora (SPEC-017 S17-3 / SPEC-049).

Exigência do Founder: se o QR cair, alguém da corretora recebe WhatsApp NA HORA
para reconectar. Regras:
- o alerta NUNCA sai pelo número que caiu;
- DESTINO (nesta ordem): alert_target.number da integração; OU
  alert_target.use_support_destination=True → o MESMO destino do suporte
  humano/dossiês (companies.acionamento_profile.suporte_humano_whatsapp —
  aceita grupo @g.us); fallback env PLATFORM_ALERT_FALLBACK_NUMBER.
- REMETENTE (nesta ordem): instância-plataforma de alertas (envs
  PLATFORM_ALERT_WA_*); senão OUTRA integração ATIVA da mesma corretora que
  não seja a que caiu (ex.: observador/auxiliar); senão registra em
  Atividades (o dashboard mostra) e loga.
- NUNCA e-mail. Falha de alerta não pode explodir o webhook (log e segue).
"""

from __future__ import annotations

import asyncio
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
    provider = os.getenv("PLATFORM_ALERT_WA_PROVIDER", "evolution")
    return {"provider": provider, "base_url": base_url, "instance_id": instance_id, "token": token}


def _run_async(coro):
    """Roda uma corrotina a partir do contexto SÍNCRONO do background task."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def _alert_target_dict(integration: Dict[str, Any]) -> Dict[str, Any]:
    target = integration.get("alert_target")
    if isinstance(target, str):
        try:
            target = json.loads(target)
        except Exception:  # noqa: BLE001
            target = {"number": target}
    return target if isinstance(target, dict) else {}


def _alert_destination(integration: Dict[str, Any]) -> Optional[str]:
    """Número OU grupo (@g.us) de destino do alerta.

    A ordem é: destino explícito → SUPORTE HUMANO da corretora → fallback da
    plataforma.

    O suporte humano deixou de exigir a bandeira `use_support_destination` em
    28/07/2026. Decisão do Founder:

    > "QUANDO CONECTAR O SUPORTE HUMANO, O ALERTA JÁ ESTÁ EMBUTIDO JUNTO. NÃO
    >  PRECISA NEM FALAR NADA."

    E o raciocínio dele está certo: o grupo do suporte humano já é onde a
    corretora recebe o dossiê quando o agente não sabe seguir. É o mesmo grupo,
    com as mesmas pessoas, olhado pelas mesmas horas. Pedir que ela configure um
    SEGUNDO destino só para "WhatsApp caiu" é criar um passo que alguém vai
    esquecer — e o alerta que ninguém configurou é o alerta que não existe.

    A mensagem é que muda, não o destino.
    """
    target = _alert_target_dict(integration)
    number = str(target.get("number") or target.get("group") or "").strip()
    if number:
        return number

    company_id = str(integration.get("company_id") or "")
    if company_id:
        try:
            from app.services.dispatch_router import _support_contact

            contact = _run_async(_support_contact(company_id))
            if contact:
                return contact
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[WA ALERT] support destination lookup failed: {type(e).__name__}")

    fallback = os.getenv("PLATFORM_ALERT_FALLBACK_NUMBER", "").strip()
    return fallback or None


async def alerta_de_plataforma(titulo: str, corpo: str, *,
                               chave: Optional[str] = None,
                               severidade: str = "sev2",
                               company_id: Optional[str] = None) -> bool:
    """Alerta de PLATAFORMA — abre incidente na CAIXA DO ADMIN, não no WhatsApp.

    Decisão do Founder, 28/07/2026:

    > "QUERO QUE ENVIE MSG DENTRO DO PORTAL ADMIN E NÃO PARA UM WHATSAPP.
    >  WHATSAPP É PARA SUPORTE HUMANO DAS COISAS DE CADA CORRETORA."

    E a separação está certa. São dois públicos com dois problemas:

        WhatsApp da corretora  →  "seu WhatsApp caiu". Quem age é a equipe
                                  dela, no telefone, agora.
        Caixa do Admin         →  "o backup do storage falhou". Quem age é a
                                  plataforma, no computador, com histórico.

    Mandar infraestrutura para o WhatsApp de alguém troca confiança por ruído:
    depois do terceiro aviso que não é para você, você para de ler todos.

    `platform_incidents` já existe e a Inbox do Admin já a lê (SPEC-061 §16).
    Nada novo foi criado — o alerta passou a usar o caminho que estava lá.

    A `incident_key` é ESTÁVEL por tipo de problema. Um backup que falha de
    hora em hora abre UM incidente que continua aberto, não vinte e quatro
    cartões por dia — que é como uma caixa útil vira uma caixa que ninguém abre.
    """
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        raw = getattr(db, "client", db)
        chave_final = chave or f"auto:{titulo.lower().replace(' ', '_')[:60]}"

        def _gravar() -> bool:
            # Já existe um incidente aberto com esta mesma causa? Então só
            # atualiza o resumo. Reabrir o mesmo problema a cada hora não é
            # informação nova, é barulho.
            abertos = (raw.table("platform_incidents")
                       .select("id, status")
                       .eq("incident_key", chave_final)
                       .in_("status", ["open", "acknowledged"])
                       .limit(1).execute().data or [])
            if abertos:
                raw.table("platform_incidents").update({
                    "summary": titulo[:200],
                    "impact_summary": corpo[:1000],
                    "updated_at": _now_iso(),
                }).eq("id", abertos[0]["id"]).execute()
                return True

            raw.table("platform_incidents").insert({
                "incident_key": chave_final,
                "severity": severidade,
                "status": "open",
                "scope": "platform" if not company_id else "tenant",
                "summary": titulo[:200],
                "impact_summary": corpo[:1000],
                "source_refs": [{"tipo": "alerta_automatico"}],
            }).execute()
            return True

        return bool(await asyncio.to_thread(_gravar))
    except Exception as e:  # noqa: BLE001
        # Se nem o incidente conseguiu ser aberto, ao menos o log grita. Um
        # alerta que falha em silêncio é a segunda falha do mesmo evento.
        logger.error("[ALERTA] '%s' NÃO registrado (%s): %s",
                     titulo, type(e).__name__, corpo[:200])
        return False


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _sender_integration(integration: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Por onde ENVIAR: plataforma (env) > outra integração ativa da corretora."""
    platform = _platform_alert_integration()
    if platform:
        return platform
    company_id = str(integration.get("company_id") or "")
    fallen_instance = str(integration.get("instance_id") or "")
    if not company_id:
        return None
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        rows = (
            db.client.table("integrations")
            .select("provider, base_url, instance_id, token, channel_status")
            .eq("company_id", company_id).eq("is_active", True)
            .neq("instance_id", fallen_instance).limit(5).execute().data or []
        )
        for row in rows:
            if str(row.get("channel_status") or "") in ("close", "closed", "disconnected", "logout"):
                continue
            if row.get("base_url") and row.get("token"):
                return row
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[WA ALERT] sender fallback lookup failed: {type(e).__name__}")
    return None


def send_disconnect_alert(integration: Dict[str, Any], state: str) -> bool:
    """Envia o alerta de desconexão. True = enviado. Nunca levanta exceção."""
    try:
        connected = str(integration.get("identifier") or "")
        masked = f"...{connected[-4:]}" if connected else "(sem número)"
        text = (
            "⚠️ *AutoBrokers — WhatsApp desconectado*\n\n"
            f"O WhatsApp de atendimento {masked} da corretora se desconectou "
            f"(status: {state}).\n\n"
            "Os segurados NÃO estão sendo atendidos por esse número até reconectar.\n"
            "Acesse: Dashboard → Personalização → Corretora → WhatsApp → *Gerenciar conexão*."
        )

        number = _alert_destination(integration)
        sender = _sender_integration(integration) if number else None
        if not number or not sender:
            reason = "sem destino de alerta configurado" if not number else "sem canal disponível para enviar"
            logger.error(f"[WA ALERT] alerta NÃO enviado ({reason})")
            try:
                from app.services.activity_log import log_activity

                _run_async(log_activity(
                    str(integration.get("company_id") or ""), "atendimentos",
                    "WhatsApp de atendimento desconectado",
                    f"Reconecte em Personalização → Corretora → WhatsApp. Aviso automático não saiu: {reason}.",
                ))
            except Exception:  # noqa: BLE001
                pass
            return False

        from app.services.whatsapp.registry import resolve_provider

        provider = resolve_provider(sender)
        result = provider.send_text(number, text)
        success = bool(getattr(result, "success", False))
        logger.info(f"[WA ALERT] disconnect alert sent={success} target=...{number[-4:]}")
        return success
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WA ALERT] failed: {type(e).__name__}")
        return False
