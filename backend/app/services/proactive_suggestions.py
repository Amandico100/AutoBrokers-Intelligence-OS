"""IA DE SUGESTÕES PROATIVAS (SPEC-034 Onda 5) — auxiliar GLOBAL, ON por padrão.

Decisão do founder 13/07: não é um auxiliar que o corretor liga/desliga — vem
LIGADO por padrão para toda corretora. 1x por semana o motor:

1. Reúne o que sabe da corretora: insights do Garimpo (dores/desejos/churn),
   notas do Auditor, [futuro: vendas/renovações da InfoCap];
2. Compõe UMA mensagem com 3 blocos: 💡 OPORTUNIDADE, ⚠️ ALERTA e ❓ PERGUNTA
   ABERTA ("me diga 3 coisas que você precisa agora — vou tentar resolver");
3. Envia pelo WhatsApp da corretora (config em acionamento_profile.sugestoes)
   e registra em broker_insights (source=sugestoes_ia) — a RESPOSTA do corretor
   cai na conversa normal e o Garimpo captura sozinho (ciclo fechado).

CUSTO: 1 chamada de LLM por corretora POR SEMANA (modelo bom compensa aqui —
env SUGESTOES_LLM_MODEL, default gpt-4o). LLM indisponível → mensagem-template
determinística com a pergunta aberta: o motor NUNCA falha em silêncio.
Desligar (exceção): acionamento_profile.sugestoes.enabled = false.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

FALLBACK_TEXT = (
    "Oi! Aqui é a inteligência do AutoBrokers 🙂\n\n"
    "❓ Pensando na sua semana: me diga 3 coisas que você está precisando agora "
    "na corretora — pode ser meta, dificuldade, ideia. Eu registro e vou atrás "
    "de resolver ou te ajudar com cada uma."
)


def compose_prompt(company_name: str, insights: List[Dict[str, Any]],
                   avg_score: Optional[float]) -> Dict[str, str]:
    """Prompt da mensagem semanal (puro, testável)."""
    dores = [i for i in insights if i.get("kind") in ("dor", "risco_churn")][:5]
    desejos = [i for i in insights if i.get("kind") in ("desejo", "pedido_feature")][:5]
    contexto = ""
    if dores:
        contexto += "\nDores/riscos recentes do corretor:\n" + "\n".join(f"- {d.get('summary')}" for d in dores)
    if desejos:
        contexto += "\nDesejos/pedidos recentes:\n" + "\n".join(f"- {d.get('summary')}" for d in desejos)
    if avg_score is not None:
        contexto += f"\nNota média dos atendimentos na semana: {avg_score:.0f}/100."
    system = (
        "Você é a inteligência de negócios do AutoBrokers para corretoras de seguros no Brasil. "
        "Escreva UMA mensagem de WhatsApp curta (máx 900 caracteres), calorosa e direta, para o corretor, "
        "com EXATAMENTE 3 blocos: '💡 Oportunidade' (uma ação concreta de vendas/marketing/gestão para esta semana), "
        "'⚠️ Alerta' (algo a observar — renovações, cobrança, qualidade do atendimento) e "
        "'❓ Pergunta' (pergunta aberta pedindo as 3 maiores necessidades dele agora). "
        "Use os dados fornecidos quando existirem; NUNCA invente números ou fatos específicos da corretora. "
        "Sem saudação longa, sem assinatura."
    )
    user = f"Corretora: {company_name or 'corretora'}\n{contexto or 'Sem dados específicos esta semana.'}"
    return {"system": system, "user": user}


def suggestions_enabled(profile: Dict[str, Any]) -> bool:
    """ON por padrão; só desliga com enabled=false explícito."""
    cfg = (profile or {}).get("sugestoes") or {}
    return cfg.get("enabled") is not False


def target_whatsapp(profile: Dict[str, Any]) -> str:
    cfg = (profile or {}).get("sugestoes") or {}
    return str(cfg.get("whatsapp") or (profile or {}).get("suporte_humano_whatsapp") or "").strip()


def week_key(now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    iso = now.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


async def _llm_message(company_id: str, prompt: Dict[str, str]) -> Optional[str]:
    try:
        import os as _os

        from langchain_core.messages import HumanMessage, SystemMessage

        from app.core.utils import get_api_key_for_provider
        from app.factories.llm_factory import LLMFactory

        provider = _os.getenv("SUGESTOES_LLM_PROVIDER") or "openai"
        model = _os.getenv("SUGESTOES_LLM_MODEL") or "gpt-4o"
        llm = LLMFactory.create_llm(
            company_config={}, agent_data={"llm_provider": provider, "llm_model": model},
            api_key=get_api_key_for_provider(provider, model),
            company_id=str(company_id), agent_id=None,
        )
        result = await llm.ainvoke(
            [SystemMessage(content=prompt["system"]), HumanMessage(content=prompt["user"])]
        )
        text = str(getattr(result, "content", "") or "").strip()
        return text[:1200] if text else None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[SUGESTOES] LLM falhou (usa fallback): {type(e).__name__}")
        return None


async def run_weekly_suggestions() -> int:
    """Roda para todas as corretoras ativas (idempotente por semana via Redis)."""
    sent = 0
    try:
        try:
            from app.core.redis import get_async_redis_client

            redis = await get_async_redis_client()
            key = f"sugestoes:{week_key()}"
            if await redis.get(key):
                return 0
            await redis.set(key, "1", ex=14 * 86400)
        except Exception:  # noqa: BLE001
            pass

        from app.core.database import get_supabase_client
        from app.services.integration_service import get_integration_service
        from app.services.whatsapp_service import get_whatsapp_service

        db = get_supabase_client()
        wa = get_whatsapp_service()
        integrations = get_integration_service()
        companies = await asyncio.to_thread(
            lambda: db.client.table("companies").select("id, name, acionamento_profile").limit(200).execute()
        )
        for comp in companies.data or []:
            profile = comp.get("acionamento_profile") or {}
            if not suggestions_enabled(profile):
                continue
            target = target_whatsapp(profile)
            company_id = str(comp["id"])
            insights = await asyncio.to_thread(
                lambda cid=company_id: db.client.table("broker_insights")
                .select("kind, summary").eq("company_id", cid).eq("source", "garimpo")
                .order("created_at", desc=True).limit(20).execute()
            )
            prompt = compose_prompt(str(comp.get("name") or ""), insights.data or [], None)
            text = await _llm_message(company_id, prompt) or FALLBACK_TEXT
            integration = integrations.get_whatsapp_integration(company_id)
            if target and integration:
                try:
                    wa.send_message(target, text, integration)
                    sent += 1
                except Exception as e:  # noqa: BLE001
                    logger.error(f"[SUGESTOES] envio falhou company={company_id}: {type(e).__name__}")
            # Registro SEMPRE (mesmo sem canal — aparece no painel do admin).
            await asyncio.to_thread(
                lambda cid=company_id, t=text: db.client.table("broker_insights").insert({
                    "company_id": cid, "kind": "sugestao_enviada", "summary": t[:160],
                    "quote": t, "source": "sugestoes_ia",
                }).execute()
            )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[SUGESTOES] varredura falhou: {type(e).__name__}")
    return sent


async def check_suggestions() -> int:
    """Task periódica: dispara 1x por semana, segunda-feira, janela 12h-21h UTC
    (9h-18h no Brasil) — horário comercial, nunca madrugada."""
    now = datetime.now(timezone.utc)
    if now.weekday() != 0 or not (12 <= now.hour < 21):
        return 0
    return await run_weekly_suggestions()
