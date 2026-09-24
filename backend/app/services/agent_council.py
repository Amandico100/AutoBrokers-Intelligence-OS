"""SPEC-040 Onda 4 — Conselho de Agentes (multi-modelo, decisões estruturais).

Segunda opinião de MÚLTIPLOS modelos fortes para decisões RARAS e importantes
(ativação de playbook com mudança grande, drift estrutural, arquitetura de
atendimento). NUNCA no caminho quente da conversa.

DESLIGADO por default (env COUNCIL_ENABLED=0) — decisão do founder 19/07:
o sistema funciona 100% sem o Conselho; ligado, ele agrega valor nas decisões
estruturais. Ligar = COUNCIL_ENABLED=1 no ambiente.

Membros (env COUNCIL_MEMBERS, "provider:model" separados por vírgula):
default "openai:gpt-6-sol,anthropic:claude-opus-5-5" (os APPROVED — SPEC-116, 24/09/2026).
🔴 SPEC-116 U8: cada membro é resolvido UM A UM pelo CATÁLOGO governado
(`llm_pricing`, via Model Router). Membro fora do catálogo, com lifecycle
BLOCKED/HISTORICAL, de provedor desconhecido ou sem chave é PULADO com log
explícito — ⛔ nunca vira `gpt-4o-mini` (antes: `moonshot`/`xai` caíam na chave
OpenAI e a fábrica respondia com o mini: 2 dos 4 "conselheiros" eram o mesmo).
Líder: a ROTA `conselho_lider`; `COUNCIL_LEADER_PROVIDER/_MODEL` ficam IGNORADOS.

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
    # SPEC-116 (24/09/2026): o default antigo tinha 3 membros fora do catálogo
    # (gpt-5.5, kimi-k3, grok-4.5) e 1 DEPRECATED (opus 5) — todos PULADOS pela
    # regra de produção do resolvedor. Default = os APPROVED.
    raw = os.getenv("COUNCIL_MEMBERS") or \
        "openai:gpt-6-sol,anthropic:claude-opus-5-5"
    out: List[Tuple[str, str]] = []
    for item in raw.split(","):
        if ":" in item:
            provider, model = item.strip().split(":", 1)
            if provider and model:
                out.append((provider.strip().lower(), model.strip()))
    return out


#: SPEC-116 U8 — os papéis do Conselho no Model Router.
PAPEL_LIDER = "conselho_lider"
#: Membro não tem rota: é o modelo DECLARADO em COUNCIL_MEMBERS, aceito só se o
#: catálogo o governa (papel sem rota → modelo do "agente", resolvedor passo 3).
PAPEL_MEMBRO = "conselho_membro"
#: A classe de dado do Conselho é a do líder (a rota `conselho_lider` declara pii).
CLASSE_DO_CONSELHO = "pii"


def _leader() -> Tuple[str, str]:
    """(provedor, modelo) da ROTA `conselho_lider` — só para log/telemetria."""
    from app.factories.llm_factory import LLMFactory

    r = LLMFactory.resolver_para({}, {}, papel=PAPEL_LIDER)
    return r.provider, r.model


def resolver_membro(provider: str, model: str):
    """O `ModeloResolvido` de UM membro, pelo catálogo — ou `None` (PULADO, com log).

    ⛔ Nunca devolve outro modelo no lugar do pedido.
    """
    try:
        from app.factories.llm_factory import LLMFactory

        return LLMFactory.resolver_para(
            {}, {"llm_provider": provider, "llm_model": model},
            papel=PAPEL_MEMBRO, classe_de_dado=CLASSE_DO_CONSELHO)
    except Exception as e:  # noqa: BLE001 — ModeloNaoResolvido e afins
        logger.warning("[CONSELHO] membro %s:%s PULADO — não resolvido pelo catálogo (%s: %s)",
                       provider, model, type(e).__name__, str(e)[:200])
        return None


async def _ask_model(provider: str, model: str, system: str, user: str, *,
                     papel: Optional[str] = None) -> Optional[str]:
    """Uma chamada. `papel` → a ROTA decide (líder); sem papel → o membro
    declarado, se o catálogo o governar. Não resolvido / sem chave → None
    (pulado, sem quebrar)."""
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.factories.llm_factory import LLMFactory

        if papel:
            resolvido = LLMFactory.resolver_para({}, {}, papel=papel)
        else:
            resolvido = resolver_membro(provider, model)
            if resolvido is None:
                return None
        # Plataforma: company_id nulo; papel/pedido/resolvido no ledger.
        llm = LLMFactory.create_llm(
            company_config={}, agent_data={"llm_provider": provider, "llm_model": model},
            company_id=None, agent_id=None, service_type="plataforma",
            modelo_resolvido=resolvido,
        )
        result = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
        return str(getattr(result, "content", "") or "").strip() or None
    except Exception as e:  # noqa: BLE001
        logger.info(f"[CONSELHO] {papel or 'membro'} {provider}:{model} indisponível "
                    f"({type(e).__name__})")
        return None


async def convene_council(question: str, context: str = "",
                          decision_kind: str = "estrutural") -> Dict[str, Any]:
    """Convoca o Conselho. Desligado -> {'enabled': False} e o chamador segue
    normalmente (o Conselho NUNCA é pré-requisito de funcionamento)."""
    if not council_enabled():
        return {"enabled": False, "opinions": [], "synthesis": None}

    user = f"DECISÃO ({decision_kind}): {question}\n\nCONTEXTO:\n{str(context or '')[:_CTX_CAP]}"

    async def _member(provider: str, model: str) -> Dict[str, Any]:
        if resolver_membro(provider, model) is None:
            return {"member": f"{provider}:{model}", "ok": False,
                    "skipped": "fora_do_catalogo_ou_proibido"}
        text = await _ask_model(provider, model, _MEMBER_SYSTEM, user)
        if not text:
            return {"member": f"{provider}:{model}", "ok": False, "skipped": "sem_chave_ou_indisponivel"}
        return {"member": f"{provider}:{model}", "ok": True, "opinion": text[:1200]}

    opinions = list(await asyncio.gather(*[_member(p, m) for p, m in council_members()]))
    given = [o for o in opinions if o.get("ok")]

    synthesis: Optional[Dict[str, Any]] = None
    if given:
        try:
            lp, lm = _leader()
        except Exception as e:  # noqa: BLE001 — sem rota do líder: sem síntese, com log
            logger.warning("[CONSELHO] líder sem rota (%s) — pareceres sem síntese", type(e).__name__)
            lp, lm = "", ""
        pareceres = "\n\n".join(f"[{o['member']}]\n{o['opinion']}" for o in given)
        raw = await _ask_model(lp, lm, _LEADER_SYSTEM,
                               f"DECISÃO: {question}\n\nPARECERES:\n{pareceres[:6000]}",
                               papel=PAPEL_LIDER)
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
