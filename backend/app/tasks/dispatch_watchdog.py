"""VIGIA + SENTINELA (SPEC-034 Onda 1) — vigilância e recuperação de acionamentos.

VIGIA: nenhum acionamento fica sem desfecho em silêncio. Varre as sessões ativas
e alerta o suporte humano (grupo/número da corretora) quando: nunca começou,
URA calada após nossa resposta, humano da seguradora sumiu, ou a sessão passou
do prazo sem estado terminal. Cada alerta dispara UMA vez (flags na sessão).

SENTINELA: quando a URA falou e NÓS não respondemos (passo não mapeado / falha),
tenta recuperar com o cérebro adaptativo (LLM forte + contexto do caso, com o
guard fiscal de sempre). Escada finita: máx 2 intervenções por sessão → depois
needs_human com dossiê + alerta. Loop infinito é impossível por construção.

Perfis de tempo POR FASE (ajuste do founder 13/07):
- URA (bot):        nós calados > 30s → Sentinela; URA calada > 120s → alerta.
- human_phase:      nós calados > 30s → Sentinela; humano sumido 10min → cutucada
                    educada; 20min → alerta ao suporte.
- monitoring:       cuida o follow-up scheduler (não é assunto daqui).

Roda no APScheduler do buffer a cada 20s. Falhas nunca derrubam o scheduler.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Perfis de tempo (segundos)
URA_UNANSWERED_S = 30
URA_SILENT_ALERT_S = 120
HUMAN_NUDGE_S = 600
HUMAN_ALERT_S = 1200
NEVER_STARTED_S = 300
SESSION_DEADLINE_S = 45 * 60
MAX_SENTINELA_ATTEMPTS = 2

HUMAN_NUDGE_TEXT = "Oi! Seguimos por aqui no aguardo, tá bom? 🙂"

# `encaminhado` entra aqui (P-46): o corredor terminou o trabalho por
# encaminhamento e não espera mais nada da seguradora. Fora desta lista, o Vigia
# cobraria resposta de uma conversa que acabou — e o encaminhamento entregue
# viraria alerta de travamento.
# `resolvido` entrou em 03/08: o follow-up confirmou o desfecho e fechou o ciclo.
# Sem ele aqui, o Vigia perseguiria para sempre uma conversa encerrada com
# sucesso — cutucando uma seguradora sobre um serviço que já foi prestado.
_TERMINAL_STATES = {"test_aborted", "needs_human", "monitoring", "captured",
                    "encaminhado", "resolvido"}


def _age_s(ts: Optional[str]) -> float:
    try:
        when = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - when).total_seconds()
    except Exception:  # noqa: BLE001
        return -1.0


def _last_entry(session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    transcript = session.get("transcript") or []
    return transcript[-1] if transcript else None


def diagnose(session: Dict[str, Any]) -> Optional[str]:
    """Classifica a situação de UMA sessão (puro, testável). Retorna:
    'stall_unanswered' | 'ura_silent' | 'human_silent_nudge' | 'human_silent_alert'
    | 'never_started' | 'deadline' | None (saudável)."""
    state = str(session.get("state") or "")
    if state in _TERMINAL_STATES:
        return None
    last = _last_entry(session)
    started_age = _age_s(session.get("created_at") or (last or {}).get("ts"))

    if state in ("preparing", "ready_to_send"):
        if started_age > NEVER_STARTED_S and not session.get("wd_never_started"):
            return "never_started"
        return None

    if not last:
        return None
    age = _age_s(last.get("at"))
    direction = str(last.get("direction") or "")

    if state == "ura":
        if direction == "in" and age > URA_UNANSWERED_S:
            return "stall_unanswered"
        if direction == "out" and age > URA_SILENT_ALERT_S and not session.get("wd_ura_silent"):
            return "ura_silent"
    elif state == "human_phase":
        if direction == "in" and age > URA_UNANSWERED_S:
            return "stall_unanswered"
        if direction == "out":
            if age > HUMAN_ALERT_S and not session.get("wd_human_alert"):
                return "human_silent_alert"
            if age > HUMAN_NUDGE_S and not session.get("wd_human_nudge"):
                return "human_silent_nudge"

    if started_age > SESSION_DEADLINE_S and not session.get("wd_deadline"):
        return "deadline"
    return None


async def _support_alert(company_id: str, text: str, wa, integration) -> None:
    try:
        from app.services.dispatch_router import _support_contact

        contact = await _support_contact(company_id)
        if contact and integration:
            wa.send_message(contact, text, integration)
        else:
            logger.warning(f"[VIGIA] sem contato de suporte p/ company {company_id}: {text[:120]}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[VIGIA] alerta falhou: {type(e).__name__}")


async def _sentinela_recover(
    company_id: str, insurer_phone: str, session: Dict[str, Any], wa, integration
) -> str:
    """Escada: tenta o cérebro adaptativo (guarded); esgotou → needs_human+dossiê.
    Retorna a ação tomada (telemetria/testes)."""
    from app.services.insurer_dispatch_service import (
        build_handoff_dossier,
        guard_human_phase_reply,
    )

    attempts = int(session.get("sentinela_attempts") or 0)
    last = _last_entry(session) or {}
    insurer_text = str(last.get("text") or "")

    if attempts < MAX_SENTINELA_ATTEMPTS:
        reply = await _adaptive_reply(company_id, session, insurer_text)
        verdict = guard_human_phase_reply(reply or "", session) if reply else {"ok": False}
        if reply and verdict.get("ok", False):
            session["sentinela_attempts"] = attempts + 1
            session.setdefault("transcript", []).append(
                {"direction": "out", "text": reply, "at": datetime.now(timezone.utc).isoformat(),
                 "via": "sentinela"}
            )
            try:
                wa.send_message(insurer_phone, reply, integration)
            except Exception as e:  # noqa: BLE001
                logger.error(f"[SENTINELA] envio falhou: {type(e).__name__}")
            logger.info(f"[SENTINELA] recuperação {attempts + 1}/{MAX_SENTINELA_ATTEMPTS} "
                        f"case={session.get('case_id')}")
            return "recovered"
        session["sentinela_attempts"] = attempts + 1  # tentativa consumida mesmo sem envio

    # Esgotou a escada → handoff com dossiê + alerta. Nunca fica em silêncio.
    session["state"] = "needs_human"
    session["reason"] = "sentinela_stall"
    dossier = build_handoff_dossier(session, reason="Travou na URA e a recuperação automática esgotou")
    await _support_alert(company_id, dossier, wa, integration)
    session["dossier_sent"] = True
    # SPEC-050 (auditoria): a ação mais importante do Vigia agora aparece no
    # feed de Atividades da corretora (antes era invisível fora dos logs).
    try:
        from app.services.activity_log import log_activity

        await log_activity(company_id, "acionamentos",
                           "Dossiê entregue à equipe — acionamento travou",
                           "A URA parou de responder e a recuperação automática esgotou; o caso foi passado com todos os dados.")
    except Exception:  # noqa: BLE001
        pass
    logger.warning(f"[SENTINELA] escada esgotada → needs_human case={session.get('case_id')}")
    return "handoff"


async def _adaptive_reply(company_id: str, session: Dict[str, Any], insurer_text: str) -> Optional[str]:
    """Cérebro forte (mesmo caminho do human_phase do webhook). Falha → None."""
    try:
        import os as _os

        from langchain_core.messages import HumanMessage, SystemMessage

        from app.core.utils import get_api_key_for_provider
        from app.factories.llm_factory import LLMFactory
        from app.services.insurer_dispatch_service import build_human_phase_messages

        # CÉREBRO v2 (SPEC-034 Onda 2): com Mapa de URA ativo, o cérebro enxerga
        # o território inteiro — telas conhecidas e o que cada opção faz.
        ura_map = None
        try:
            from app.services.corridor_playbooks import get_playbook
            from app.services.ura_map_service import get_active_map

            playbook = get_playbook(str(session.get("playbook_ref") or "")) or {}
            row = await get_active_map(
                str(playbook.get("insurer_key") or ""),
                str(playbook.get("line_kind") or "auto"),
            )
            ura_map = (row or {}).get("map")
        except Exception:  # noqa: BLE001 — mapa é opcional
            ura_map = None
        msgs = build_human_phase_messages(session, insurer_text, ura_map=ura_map)
        d_provider = _os.getenv("DISPATCH_LLM_PROVIDER") or "openai"
        d_model = _os.getenv("DISPATCH_LLM_MODEL") or "gpt-4o"
        llm = LLMFactory.create_llm(
            company_config={},
            agent_data={"llm_provider": d_provider, "llm_model": d_model},
            api_key=get_api_key_for_provider(d_provider, d_model),
            company_id=str(company_id),
            agent_id=None,
        )
        result = await llm.ainvoke(
            [SystemMessage(content=msgs["system"]), HumanMessage(content=msgs["user"])]
        )
        content = getattr(result, "content", None)
        return str(content).strip() if content else None
    except Exception as e:  # noqa: BLE001
        logger.error(f"[SENTINELA] cérebro adaptativo falhou: {type(e).__name__}")
        return None


async def check_dispatch_watchdog() -> int:
    """Varre as sessões ativas; devolve quantas ações tomou (telemetria)."""
    actions = 0
    try:
        from app.core.redis import get_async_redis_client
        from app.services.dispatch_router import save_active_dispatch
        from app.services.integration_service import get_integration_service
        from app.services.whatsapp_service import get_whatsapp_service

        redis = await get_async_redis_client()
        wa = get_whatsapp_service()
        integrations = get_integration_service()

        async for key in redis.scan_iter(match="dispatch:active:*"):
            k = key.decode() if isinstance(key, (bytes, bytearray)) else str(key)
            raw = await redis.get(k)
            if not raw:
                continue
            try:
                session = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
            except Exception:  # noqa: BLE001
                continue
            finding = diagnose(session)
            if not finding:
                continue
            parts = k.split(":")
            company_id = parts[2] if len(parts) >= 4 else ""
            insurer_phone = parts[3] if len(parts) >= 4 else ""
            integration = integrations.get_platform_whatsapp_integration(company_id) if company_id else None
            case = session.get("case_id")
            label = str(session.get("playbook_ref") or "?")

            if finding == "stall_unanswered":
                await _sentinela_recover(company_id, insurer_phone, session, wa, integration)
            elif finding == "ura_silent":
                session["wd_ura_silent"] = True
                await _support_alert(
                    company_id,
                    f"⚠️ VIGIA: a URA ({label}) está calada há {URA_SILENT_ALERT_S // 60}min+ após "
                    f"nossa resposta (caso {case}). Pode ter rejeitado em silêncio. "
                    f"Última nossa: \"{str((_last_entry(session) or {}).get('text') or '')[:160]}\"",
                    wa, integration,
                )
            elif finding == "human_silent_nudge":
                session["wd_human_nudge"] = True
                try:
                    wa.send_message(insurer_phone, HUMAN_NUDGE_TEXT, integration)
                    session.setdefault("transcript", []).append(
                        {"direction": "out", "text": HUMAN_NUDGE_TEXT,
                         "at": datetime.now(timezone.utc).isoformat(), "via": "vigia"}
                    )
                except Exception as e:  # noqa: BLE001
                    logger.error(f"[VIGIA] cutucada falhou: {type(e).__name__}")
            elif finding == "human_silent_alert":
                session["wd_human_alert"] = True
                await _support_alert(
                    company_id,
                    f"⚠️ VIGIA: atendente humano da seguradora ({label}) sem responder há 20min+ "
                    f"(caso {case}). Vale um olhar humano.",
                    wa, integration,
                )
            elif finding == "never_started":
                session["wd_never_started"] = True
                await _support_alert(
                    company_id,
                    f"🚨 VIGIA: acionamento do caso {case} ({label}) foi criado e NÃO começou "
                    f"em {NEVER_STARTED_S // 60}min (estado: {session.get('state')}). Verificar.",
                    wa, integration,
                )
            elif finding == "deadline":
                session["wd_deadline"] = True
                await _support_alert(
                    company_id,
                    f"⏰ VIGIA: acionamento do caso {case} ({label}) está há 45min+ sem desfecho "
                    f"(estado: {session.get('state')}). Transcript no dashboard (Acionamento).",
                    wa, integration,
                )
            await save_active_dispatch(company_id, insurer_phone, session)
            actions += 1
    except Exception as e:  # noqa: BLE001 — nunca derruba o scheduler
        logger.error(f"[WATCHDOG] varredura falhou: {type(e).__name__}")
    try:
        from app.services.cartographer_runner import check_cartographer_stalls

        actions += await check_cartographer_stalls()
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.core.heartbeat import beat

        await beat("vigia_sentinela", actions)
    except Exception:  # noqa: BLE001
        pass
    return actions
