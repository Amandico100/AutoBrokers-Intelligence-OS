"""AUDITOR v1 (SPEC-034 Onda 4) — nota de qualidade + regressão noturna.

CUSTO (decisão de projeto, pergunta do founder 13/07): CASCATA.
- Camada 0 (sempre, grátis): scorecard HEURÍSTICO determinístico — repetição de
  mensagem, re-pedir CPF, amnésia ("não tenho seu..."), conversa arrastada,
  frustração do cliente. Pega a maioria dos problemas por R$0.
- Camadas 1/2 (LLM-judge por amostragem; síntese semanal): PLANEJADAS, ainda
  NÃO implementadas — hoje só a heurística roda (method='heuristic' sempre).
  SPEC-050: docstring corrigida — antes anunciava envs AUDITOR_LLM/AUDITOR_SAMPLE
  que não existiam no código (auditoria não pode se apoiar em promessa).

REGRESSÃO (grátis): as conversas espelhadas de acionamento viram detector de
drift — se uma tela da URA que ONTEM tinha resposta hoje não casa com nenhum
passo do playbook, é sinal de mudança/regressão → alerta.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

_CPF_ASK_RE = re.compile(r"(?:me\s+)?(?:informe|informa|passe|preciso d[eo])\s+(?:o\s+)?cpf", re.I)
_AMNESIA_RE = re.compile(r"n[ãa]o tenho (?:seu|sua|o seu|registro)|n[ãa]o encontrei seu cadastro", re.I)
_FRUSTRATION_RE = re.compile(
    r"j[áa] falei|de novo\?|voc[êe] n[ãa]o entende|que merda|caralho|absurdo|p[ée]ssimo|ridículo|ridiculo", re.I)


def score_messages(messages: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
    """Scorecard heurístico (0-100). Puro, determinístico, custo zero."""
    flags: List[str] = []
    assistant = [str(m.get("content") or "") for m in messages or [] if m.get("role") == "assistant"]
    users = [str(m.get("content") or "") for m in messages or [] if m.get("role") == "user"]

    normalized = [a.strip().lower() for a in assistant if len(a.strip()) > 20]
    if len(normalized) != len(set(normalized)):
        flags.append("repetiu_mensagem")
    if sum(1 for a in assistant if _CPF_ASK_RE.search(a)) >= 2:
        flags.append("re_pediu_cpf")
    if any(_AMNESIA_RE.search(a) for a in assistant):
        flags.append("amnesia")
    if any(_FRUSTRATION_RE.search(u) for u in users):
        flags.append("cliente_frustrado")
    if len(messages or []) > 60:
        flags.append("conversa_arrastada")

    penalties = {"repetiu_mensagem": 20, "re_pediu_cpf": 25, "amnesia": 25,
                 "cliente_frustrado": 20, "conversa_arrastada": 10}
    score = max(0, 100 - sum(penalties[f] for f in flags))
    return score, flags


def detect_drift(playbook: Dict[str, Any], script: List[Dict[str, Any]]) -> List[str]:
    """Telas da URA que TINHAM resposta na conversa real e HOJE não casam com
    nenhum passo do playbook → drift/regressão. Puro e grátis."""
    from app.services.corridor_playbooks import match_ura_step

    drifted: List[str] = []
    for item in script or []:
        if not item.get("expected"):
            continue  # informativo — sem compromisso de resposta
        if not match_ura_step(playbook, str(item.get("screen") or "")):
            drifted.append(str(item.get("screen") or "")[:120])
    return drifted


async def audit_conversation(company_id: str, conversation_id: str) -> int:
    """Audita UMA conversa (heurística sempre) e grava o scorecard."""
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        # SPEC-050 (auditoria): dedup ESTRUTURAL por conversa/dia — o marcador
        # Redis diário era a única proteção; Redis fora do ar duplicava
        # scorecards a cada varredura.
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).date().isoformat()
        dup = await asyncio.to_thread(
            lambda: db.client.table("conversation_scorecards").select("id")
            .eq("conversation_id", conversation_id).gte("created_at", today)
            .limit(1).execute()
        )
        if dup.data:
            return -2  # já auditada hoje
        msgs = await asyncio.to_thread(
            lambda: db.client.table("messages").select("role, content")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=True).limit(120).execute()
        )
        score, flags = score_messages(list(reversed(msgs.data or [])))
        await asyncio.to_thread(
            lambda: db.client.table("conversation_scorecards").insert({
                "company_id": company_id, "conversation_id": conversation_id,
                "score": score, "flags": flags, "method": "heuristic",
            }).execute()
        )
        return score
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[AUDITOR] audit_conversation falhou: {type(e).__name__}")
        return -1


async def refresh_overlay_cache() -> int:
    """Carrega overlays ativos do Alfaiate para o cache do motor (fail-safe)."""
    try:
        from app.core.database import get_supabase_client
        from app.services.corridor_playbooks import set_overlay_cache

        db = get_supabase_client()
        res = await asyncio.to_thread(
            lambda: db.client.table("playbook_overlays").select("playbook_ref, anchor, note")
            .eq("status", "active").limit(500).execute()
        )
        cache: Dict[str, List[Dict[str, Any]]] = {}
        for row in res.data or []:
            cache.setdefault(str(row["playbook_ref"]), []).append(row)
        set_overlay_cache(cache)
        return sum(len(v) for v in cache.values())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[AUDITOR] refresh_overlay_cache falhou: {type(e).__name__}")
        return 0


async def check_auditor() -> int:
    """Task periódica: 1x/dia audita as conversas das últimas 24h (marcador em
    Redis, mesmo padrão do Garimpo). Sempre atualiza o cache de overlays."""
    audited = 0
    await refresh_overlay_cache()
    try:
        from datetime import datetime, timedelta, timezone

        today = datetime.now(timezone.utc).date().isoformat()
        try:
            from app.core.redis import get_async_redis_client

            redis = await get_async_redis_client()
            last = await redis.get("auditor:last_run")
            last = last.decode() if isinstance(last, (bytes, bytearray)) else last
            if last == today:
                return 0
            await redis.set("auditor:last_run", today, ex=2 * 86400)
        except Exception:  # noqa: BLE001
            pass

        from app.core.database import get_supabase_client

        db = get_supabase_client()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        convs = await asyncio.to_thread(
            lambda: db.client.table("conversations").select("id, company_id, session_id")
            .gte("last_message_at", cutoff).limit(200).execute()
        )
        per_company: Dict[str, int] = {}
        for conv in convs.data or []:
            if str(conv.get("session_id") or "").startswith("dispatch:"):
                continue  # acionamentos têm o Vigia/drift — scorecard é p/ atendimento
            cid = str(conv["company_id"])
            if await audit_conversation(cid, str(conv["id"])) >= 0:
                audited += 1
                per_company[cid] = per_company.get(cid, 0) + 1
        for cid, n in per_company.items():
            try:
                from app.services.activity_log import log_activity

                await log_activity(cid, "qualidade", f"Varredura de qualidade concluída — {n} conversa(s) auditada(s)",
                                   "Cada atendimento recebeu nota e verificação de excelência.")
            except Exception:  # noqa: BLE001
                pass
        if audited:
            logger.info(f"[AUDITOR] {audited} conversas auditadas")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[AUDITOR] check falhou: {type(e).__name__}")
    try:
        from app.core.heartbeat import beat

        await beat("auditor", audited)
        await beat("alfaiate")
    except Exception:  # noqa: BLE001
        pass
    return audited
