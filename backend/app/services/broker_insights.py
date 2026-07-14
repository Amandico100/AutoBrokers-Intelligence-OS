"""GARIMPO v1 (SPEC-034 Onda 3) — inteligência de negócio das conversas.

Minera das conversas dos corretores: desejos, dores, pedidos de feature,
dúvidas recorrentes, elogios e risco de churn → tabela `broker_insights`
(por corretora; o admin enxerga o agregado). "Saber o que centenas de
corretores estão querendo" — decisão do founder 13/07.

CUSTO (decisão consciente): a captura v1 é DETERMINÍSTICA (regex de padrões de
desejo/dor — custo ZERO por mensagem). Uma LLM barata pode refinar os achados
em lote (GARIMPO_LLM=1, desligada por padrão) — nunca roda na conversa inteira.
Conversas espelhadas de seguradora (dispatch:) ficam FORA do garimpo.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# (kind, padrão). Ordem importa: risco_churn antes de dor.
_PATTERNS: List[tuple] = [
    ("risco_churn", re.compile(
        r"vou cancelar|quero cancelar|pensando em cancelar|desistir d|n[ãa]o vale a pena|vou sair d", re.I)),
    ("pedido_feature", re.compile(
        r"voc[êe]s? poderiam|d[áa] pra (?:fazer|colocar|ter)|tem como (?:o sistema|voc[êe]s|a plataforma)"
        r"|falta (?:um|uma)|deveria ter|sinto falta d|seria [óo]timo se", re.I)),
    ("desejo", re.compile(
        r"eu queria|gostaria (?:que|de ter)|seria bom (?:se|ter)|meu sonho|preciso muito d"
        r"|quero aumentar|minha meta [ée]", re.I)),
    ("dor", re.compile(
        r"dificuldade|muito dif[íi]cil|problema com|demora demais|toma muito tempo|perco (?:muito )?tempo"
        r"|complicado demais|caro demais|n[ãa]o consigo|me atrapalha|dor de cabe[çc]a", re.I)),
    ("elogio", re.compile(
        r"muito bom|excelente|adorei|incr[íi]vel|me ajudou muito|parab[ée]ns|top demais|sensacional", re.I)),
]

_MIN_LEN = 15  # mensagens muito curtas não carregam contexto de insight


def extract_candidates(messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Camada 1 (grátis): varre mensagens do USUÁRIO e extrai candidatos a insight.
    Puro e determinístico — testável offline."""
    found: List[Dict[str, str]] = []
    seen = set()
    for msg in messages or []:
        if str(msg.get("role") or "") != "user":
            continue
        text = str(msg.get("content") or "").strip()
        if len(text) < _MIN_LEN:
            continue
        for kind, rx in _PATTERNS:
            m = rx.search(text)
            if m:
                # Janela em volta do gatilho: o trecho que carrega o insight.
                start = max(0, m.start() - 60)
                quote = text[start:start + 220].strip()
                key = (kind, quote[:80].lower())
                if key not in seen:
                    seen.add(key)
                    found.append({"kind": kind, "quote": quote,
                                  "summary": quote[:160]})
                break  # 1 insight por mensagem (o mais forte)
    return found


async def mine_conversation(company_id: str, conversation_id: str,
                            user_id: Optional[str] = None) -> int:
    """Minera UMA conversa e grava os insights novos. Devolve quantos gravou."""
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        msgs = await asyncio.to_thread(
            lambda: db.client.table("messages")
            .select("role, content")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=True).limit(200).execute()
        )
        candidates = extract_candidates(list(reversed(msgs.data or [])))
        if not candidates:
            return 0
        saved = 0
        for c in candidates:
            dup = await asyncio.to_thread(
                lambda c=c: db.client.table("broker_insights").select("id")
                .eq("company_id", company_id).eq("conversation_id", conversation_id)
                .eq("kind", c["kind"]).eq("quote", c["quote"]).limit(1).execute()
            )
            if dup.data:
                continue
            row = {"company_id": company_id, "conversation_id": conversation_id,
                   "user_id": user_id, "kind": c["kind"], "summary": c["summary"],
                   "quote": c["quote"], "source": "garimpo"}
            await asyncio.to_thread(
                lambda row=row: db.client.table("broker_insights").insert(row).execute()
            )
            saved += 1
        return saved
    except Exception as e:  # noqa: BLE001 — garimpo nunca derruba nada
        logger.warning(f"[GARIMPO] mine_conversation falhou: {type(e).__name__}")
        return 0


async def mine_recent(hours: int = 24, limit: int = 300) -> int:
    """Varre conversas com atividade recente (exclui espelhos de seguradora) e
    minera cada uma. Usada pela task periódica E pela retroativa (hours grande)."""
    total = 0
    try:
        from datetime import datetime, timedelta, timezone

        from app.core.database import get_supabase_client

        db = get_supabase_client()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        convs = await asyncio.to_thread(
            lambda: db.client.table("conversations")
            .select("id, company_id, user_id, session_id")
            .gte("last_message_at", cutoff)
            .order("last_message_at", desc=True).limit(limit).execute()
        )
        for conv in convs.data or []:
            if str(conv.get("session_id") or "").startswith("dispatch:"):
                continue  # conversa com seguradora não é voz do corretor
            total += await mine_conversation(
                str(conv["company_id"]), str(conv["id"]), conv.get("user_id")
            )
        if total:
            logger.info(f"[GARIMPO] {total} insights novos gravados")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[GARIMPO] mine_recent falhou: {type(e).__name__}")
    return total


async def check_garimpo() -> int:
    """Task periódica (scheduler): minera as últimas 24h, no máximo 1x/dia
    (marcador em Redis; sem Redis, roda mesmo — dedup por quote segura)."""
    try:
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).date().isoformat()
        try:
            from app.core.redis import get_async_redis_client

            redis = await get_async_redis_client()
            key = "garimpo:last_run"
            last = await redis.get(key)
            last = last.decode() if isinstance(last, (bytes, bytearray)) else last
            if last == today:
                return 0
            await redis.set(key, today, ex=2 * 86400)
        except Exception:  # noqa: BLE001 — sem redis, segue (dedup protege)
            pass
        return await mine_recent(hours=24)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[GARIMPO] check falhou: {type(e).__name__}")
        return 0
    finally:
        try:
            from app.core.heartbeat import beat

            await beat("garimpo")
        except Exception:  # noqa: BLE001
            pass
