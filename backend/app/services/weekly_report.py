"""RELATÓRIO DE SÁBADO (SPEC-036) — "olha quanta coisa fizemos por você".

Todo sábado de manhã, cada corretora recebe no WhatsApp o resumo da semana,
montado a partir do feed de Atividades (agent_activities) — determinístico,
zero LLM. Formatação caprichada; números reais; fecho comercial.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_CAT_LABELS = {
    "atendimentos": "🗣️ Atendimentos aos seus clientes",
    "acionamentos": "🚗 Acionamentos de assistência conduzidos",
    "qualidade": "🛡️ Verificações de qualidade",
    "conhecimento": "📚 Conhecimento processado",
    "inteligencia": "🧠 Inteligência de negócio",
}


def compose_weekly_message(company_name: str, counts: Dict[str, int],
                           highlights: List[str]) -> str:
    """Puro e testável. Sem contagens → mensagem honesta de prontidão."""
    total = sum(counts.values())
    lines = [f"📊 *Resumo da semana — {company_name or 'sua corretora'}*", ""]
    if total == 0:
        lines.append("Semana tranquila por aqui — e a estrutura inteira de plantão: "
                     "atendente, vigilância 24h e monitoramento de qualidade prontos "
                     "para o próximo cliente. 🙂")
    else:
        lines.append(f"Essa semana trabalhamos por você: *{total} ações* executadas 👇")
        lines.append("")
        for cat, label in _CAT_LABELS.items():
            n = counts.get(cat, 0)
            if n:
                lines.append(f"{label}: *{n}*")
        if highlights:
            lines.append("")
            lines.append("✨ Destaques:")
            for h in highlights[:4]:
                lines.append(f"• {h}")
        lines.append("")
        lines.append("Tudo isso rodou automático — vale a pena investir na gente. 💙")
    return "\n".join(lines)


async def run_weekly_report() -> int:
    sent = 0
    try:
        from app.core.database import get_supabase_client
        from app.services.integration_service import get_integration_service
        from app.services.proactive_suggestions import suggestions_enabled, target_whatsapp
        from app.services.whatsapp_service import get_whatsapp_service

        db = get_supabase_client()
        wa = get_whatsapp_service()
        integrations = get_integration_service()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        companies = await asyncio.to_thread(
            lambda: db.client.table("companies")
            .select("id, company_name, acionamento_profile, is_technical").limit(200).execute()
        )
        for comp in companies.data or []:
            if comp.get("is_technical"):
                continue
            profile = comp.get("acionamento_profile") or {}
            if not suggestions_enabled(profile):
                continue
            company_id = str(comp["id"])
            acts = await asyncio.to_thread(
                lambda cid=company_id: db.client.table("agent_activities")
                .select("category, title").eq("company_id", cid)
                .gte("created_at", cutoff).limit(1000).execute()
            )
            counts: Dict[str, int] = {}
            highlights: List[str] = []
            for a in acts.data or []:
                counts[a["category"]] = counts.get(a["category"], 0) + 1
                if len(highlights) < 4 and a["title"] not in highlights:
                    highlights.append(a["title"])
            text = compose_weekly_message(str(comp.get("company_name") or ""), counts, highlights)
            target = target_whatsapp(profile)
            integration = integrations.get_platform_whatsapp_integration(company_id)
            if target and integration:
                try:
                    wa.send_message(target, text, integration)
                    sent += 1
                except Exception as e:  # noqa: BLE001
                    logger.error(f"[RELATORIO] envio falhou company={company_id}: {type(e).__name__}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[RELATORIO] varredura falhou: {type(e).__name__}")
    return sent


async def check_weekly_report() -> int:
    """Task periódica: sábado, 12h-18h UTC (9h-15h BR), 1x por semana (marcador)."""
    now = datetime.now(timezone.utc)
    if now.weekday() != 5 or not (12 <= now.hour < 18):
        return 0
    try:
        from app.core.redis import get_async_redis_client
        from app.services.proactive_suggestions import week_key

        redis = await get_async_redis_client()
        key = f"relatorio:{week_key(now)}"
        if await redis.get(key):
            return 0
        await redis.set(key, "1", ex=14 * 86400)
    except Exception:  # noqa: BLE001
        pass
    return await run_weekly_report()
