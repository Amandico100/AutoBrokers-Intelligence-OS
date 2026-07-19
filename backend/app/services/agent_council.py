"""SPEC-040 Onda 4 — Conselho de Agentes (multi-modelo, decisões estruturais).

Segunda opinião de MÚLTIPLOS modelos fortes para decisões RARAS e importantes
(ativação de playbook com mudança grande, drift estrutural, arquitetura de
atendimento). NUNCA no caminho quente da conversa.

DESLIGADO por default (env COUNCIL_ENABLED=0) — decisão do founder 19/07:
o sistema funciona 100% sem o Conselho; ligado, ele agrega valor nas decisões
estruturais. Ligar = COUNCIL_ENABLED=1 no ambiente.

Membros (env COUNCIL_MEMBERS, "provider:model" separados por vírgula):
default "openai:gpt-5.5,anthropic:claude-opus-4-8,moonshot:kimi-k3,xai:grok-4.5".
Membro sem API key/provider suportado é PULADO com nota — nada quebra.
Líder consolida: COUNCIL_LEADER_MODEL (default claude-opus-4-8/anthropic).

Custo controlado por construção: contexto cap 3000 chars, parecer curto,
pareceres em PARALELO, e o Conselho só é convocado em decisão estrutural.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_CTX_CAP = 3000

_MEMBER_SYSTEM = (
    "Você é membro do conselho técnico de uma plataforma de agentes de IA para "
    "corretoras de seguros (atendimento WhatsApp, acionamento de seguradoras). "
    "Dê um parecer CURTO (máximo 120 palavras) e objetivo sobre a decisão proposta. "
    "Formato obrigatório:\nVEREDITO: aprovar|ajustar|rejeitar\nRISCOS: ...\nSUGESTÃO: ..."
)

_LEADER_SYSTEM = (
    "Você é o líder do conselho técnico. Recebeu os pareceres dos membros sobre uma "
    "decisão estrutural. Consolide em APENAS JSON válido:\n"
    "{\"veredito\": \"aprovar|ajustar|rejeitar\", \"consenso\": true|false, "
    "\"justificativa\": \"1-2 frases\", \"ajustes_sugeridos\": [\"...\"]}\n"
    "Critério: em divergência, prevalece a opção mais SEGURA para o atendimento em produção."
)


def council_enabled() -> bool:
    return (os.getenv("COUNCIL_ENABLED", "0") or "0").strip() == "1"


def council_members() -> List[Tuple[str, str]]:
    raw = os.getenv("COUNCIL_MEMBERS") or \
        "openai:gpt-5.5,anthropic:claude-opus-4-8,moonshot:kimi-k3,xai:grok-4.5"
    out: List[Tuple[str, str]] = []
    for item in raw.split(","):
        if ":" in item:
            provider, model = item.strip().split(":", 1)
            if provider and model:
                out.append((provider.strip().lower(), model.strip()))
    return out


def _leader() -> Tuple[str, str]:
    return (os.getenv("COUNCIL_LEADER_PROVIDER") or "anthropic",
            os.getenv("COUNCIL_LEADER_MODEL") or "claude-opus-4-8")


async def _ask_model(provider: str, model: str, system: str, user: str) -> Optional[str]:
    """Uma chamada; membro sem chave/provider vira None (pulado, sem quebrar)."""
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.core.utils import get_api_key_for_provider
        from app.factories.llm_factory import LLMFactory

        api_key = get_api_key_for_provider(provider, model)
        if not api_key:
            return None
        llm = LLMFactory.create_llm(
            company_config={}, agent_data={"llm_provider": provider, "llm_model": model},
            api_key=api_key,
            company_id=str(os.getenv("GLOBAL_KNOWLEDGE_COMPANY_ID") or ""), agent_id=None,
        )
        result = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
        return str(getattr(result, "content", "") or "").strip() or None
    except Exception as e:  # noqa: BLE001
        logger.info(f"[CONSELHO] membro {provider}:{model} indisponível ({type(e).__name__})")
        return None


async def convene_council(question: str, context: str = "",
                          decision_kind: str = "estrutural") -> Dict[str, Any]:
    """Convoca o Conselho. Desligado -> {'enabled': False} e o chamador segue
    normalmente (o Conselho NUNCA é pré-requisito de funcionamento)."""
    if not council_enabled():
        return {"enabled": False, "opinions": [], "synthesis": None}

    user = f"DECISÃO ({decision_kind}): {question}\n\nCONTEXTO:\n{str(context or '')[:_CTX_CAP]}"

    async def _member(provider: str, model: str) -> Dict[str, Any]:
        text = await _ask_model(provider, model, _MEMBER_SYSTEM, user)
        if not text:
            return {"member": f"{provider}:{model}", "ok": False, "skipped": "sem_chave_ou_indisponivel"}
        return {"member": f"{provider}:{model}", "ok": True, "opinion": text[:1200]}

    opinions = list(await asyncio.gather(*[_member(p, m) for p, m in council_members()]))
    given = [o for o in opinions if o.get("ok")]

    synthesis: Optional[Dict[str, Any]] = None
    if given:
        lp, lm = _leader()
        pareceres = "\n\n".join(f"[{o['member']}]\n{o['opinion']}" for o in given)
        raw = await _ask_model(lp, lm, _LEADER_SYSTEM,
                               f"DECISÃO: {question}\n\nPARECERES:\n{pareceres[:6000]}")
        if raw:
            s = raw.strip().strip("`")
            s = s[4:] if s.lower().startswith("json") else s
            try:
                start, end = s.find("{"), s.rfind("}")
                synthesis = json.loads(s[start:end + 1]) if start >= 0 else None
            except Exception:  # noqa: BLE001
                synthesis = {"veredito": "ajustar", "consenso": False,
                             "justificativa": "síntese ilegível — tratar como cautela", "raw": raw[:400]}

    result = {"enabled": True, "opinions": opinions, "synthesis": synthesis,
              "convened_at": datetime.now(timezone.utc).isoformat()}

    # telemetria: última convocação + atividade + pulso na Central (best-effort)
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        await r.set("council:last_convening", json.dumps(
            {"question": question[:200], "kind": decision_kind,
             "members_ok": len(given), "verdict": (synthesis or {}).get("veredito"),
             "at": result["convened_at"]}, ensure_ascii=False), ex=30 * 86400)
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.core.heartbeat import beat

        await beat("conselho", 1)
    except Exception:  # noqa: BLE001
        pass
    logger.info(f"[CONSELHO] convocado ({decision_kind}): {len(given)} pareceres, "
                f"veredito={(synthesis or {}).get('veredito')}")
    return result
