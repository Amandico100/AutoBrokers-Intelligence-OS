"""GARIMPO v1 (SPEC-034 Onda 3) — inteligência de negócio das conversas.

Minera das conversas dos corretores: desejos, dores, pedidos de feature,
dúvidas recorrentes, elogios e risco de churn → tabela `broker_insights`
(por corretora; o admin enxerga o agregado). "Saber o que centenas de
corretores estão querendo" — decisão do founder 13/07.

CUSTO (decisão consciente): a captura v1 é DETERMINÍSTICA (regex de padrões de
desejo/dor — custo ZERO por mensagem). GARIMPO v2 (SPEC-049): camada LLM barata
LIGADA por padrão — 1 chamada/corretora/dia, entrada limitada, desligável com
GARIMPO_LLM=0. Conversas espelhadas de seguradora (dispatch:) ficam FORA.
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


# ------------------------------------------------------------------ #
# GARIMPO v2 (SPEC-049) — camada LLM BARATA em lote, por corretora/dia.
# A regex v1 pega o óbvio; a LLM pega o resto (dúvidas de seguros,
# necessidades implícitas, temas recorrentes). Custo controlado: 1 chamada
# por corretora por dia, entrada limitada, modelo econômico. Desligável
# com GARIMPO_LLM=0. Tiering da casa: Haiku aqui (volume), Sonnet no
# destilador braçal, Opus só no estrutural (playbooks).
# ------------------------------------------------------------------ #
_LLM_KINDS = {"desejo", "dor", "pedido_feature", "duvida_seguros", "necessidade", "elogio", "risco_churn"}
_LLM_MAX_CHARS = 8000
_LLM_MAX_INSIGHTS = 8

_LLM_SYSTEM = (
    "Você analisa mensagens que CORRETORES de seguros escreveram ao assistente da "
    "plataforma AutoBrokers. Extraia insights de negócio REAIS que o corretor "
    "expressou: desejos, dores, pedidos de funcionalidade, dúvidas sobre seguros, "
    "necessidades da operação, elogios, risco de churn. NÃO invente; NÃO inclua "
    "dados pessoais de clientes. Responda APENAS JSON válido: "
    '{"insights": [{"kind": "desejo|dor|pedido_feature|duvida_seguros|necessidade|elogio|risco_churn", '
    '"summary": "1 frase objetiva", "quote": "trecho literal curto"}]} '
    f"(no máximo {_LLM_MAX_INSIGHTS}; lista vazia se não houver nada relevante)."
)


async def _llm_refine_company(company_id: str, conv_ids: list) -> int:
    """Uma chamada barata por corretora: minera o que a regex não pega."""
    import os as _os

    if str(_os.getenv("GARIMPO_LLM", "1")).strip().lower() in ("0", "false", "off"):
        return 0
    try:
        import json as _json

        from langchain_core.messages import HumanMessage, SystemMessage

        from app.core.database import get_supabase_client
        from app.core.utils import get_api_key_for_provider
        from app.factories.llm_factory import LLMFactory

        db = get_supabase_client()
        chunks: List[str] = []
        used = 0
        for cid in conv_ids[:30]:
            msgs = await asyncio.to_thread(
                lambda cid=cid: db.client.table("messages").select("role, content")
                .eq("conversation_id", cid).order("created_at", desc=True).limit(60).execute()
            )
            for m in reversed(msgs.data or []):
                if str(m.get("role") or "") != "user":
                    continue
                text = str(m.get("content") or "").strip()
                if len(text) < _MIN_LEN:
                    continue
                if used + len(text) > _LLM_MAX_CHARS:
                    break
                chunks.append(f"- {text[:400]}")
                used += len(text)
        if len(chunks) < 2:  # pouco material = não vale a chamada
            return 0

        provider = _os.getenv("GARIMPO_LLM_PROVIDER") or "anthropic"
        model = _os.getenv("GARIMPO_LLM_MODEL") or "claude-haiku-4-5-20251001"
        llm = LLMFactory.create_llm(
            company_config={}, agent_data={"llm_provider": provider, "llm_model": model},
            api_key=get_api_key_for_provider(provider, model),
            company_id=company_id, agent_id=None,
        )
        result = await llm.ainvoke([
            SystemMessage(content=_LLM_SYSTEM),
            HumanMessage(content="Mensagens do corretor (últimas 24h):\n" + "\n".join(chunks)),
        ])
        raw = str(getattr(result, "content", "") or "").strip()
        start, end = raw.find("{"), raw.rfind("}")
        data = _json.loads(raw[start:end + 1]) if start >= 0 and end > start else {}
        saved = 0
        for ins in (data.get("insights") or [])[:_LLM_MAX_INSIGHTS]:
            kind = str(ins.get("kind") or "").strip()
            summary = str(ins.get("summary") or "").strip()[:200]
            quote = str(ins.get("quote") or "").strip()[:220]
            if kind not in _LLM_KINDS or not summary:
                continue
            dup = await asyncio.to_thread(
                lambda k=kind, s=summary: db.client.table("broker_insights").select("id")
                .eq("company_id", company_id).eq("kind", k).eq("summary", s).limit(1).execute()
            )
            if dup.data:
                continue
            await asyncio.to_thread(
                lambda k=kind, s=summary, q=quote: db.client.table("broker_insights").insert({
                    "company_id": company_id, "kind": k, "summary": s,
                    "quote": q or s, "source": "garimpo_llm",
                }).execute()
            )
            saved += 1
        if saved:
            logger.info(f"[GARIMPO LLM] {saved} insights refinados company={company_id[:8]}")
        return saved
    except Exception as e:  # noqa: BLE001 — a camada LLM nunca derruba o garimpo
        logger.warning(f"[GARIMPO LLM] refine falhou: {type(e).__name__}")
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
        per_company = {}
        convs_by_company: Dict[str, list] = {}
        for conv in convs.data or []:
            if str(conv.get("session_id") or "").startswith("dispatch:"):
                continue  # conversa com seguradora não é voz do corretor
            convs_by_company.setdefault(str(conv["company_id"]), []).append(str(conv["id"]))
            n = await mine_conversation(
                str(conv["company_id"]), str(conv["id"]), conv.get("user_id")
            )
            total += n
            if n:
                per_company[str(conv["company_id"])] = per_company.get(str(conv["company_id"]), 0) + n
        # Camada LLM (v2): 1 chamada por corretora com material do dia.
        for cid, ids in convs_by_company.items():
            n = await _llm_refine_company(cid, ids)
            total += n
            if n:
                per_company[cid] = per_company.get(cid, 0) + n
        for cid, n in per_company.items():
            try:
                from app.services.activity_log import log_activity

                await log_activity(cid, "inteligencia", f"{n} insight(s) do seu negócio capturado(s)",
                                   "Suas necessidades e ideias registradas para virarem melhorias e ações.")
            except Exception:  # noqa: BLE001
                pass
        if total:
            logger.info(f"[GARIMPO] {total} insights novos gravados")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[GARIMPO] mine_recent falhou: {type(e).__name__}")
    return total


async def check_garimpo() -> int:
    """Task periódica (scheduler): minera as últimas 24h, no máximo 1x/dia
    (marcador em Redis; sem Redis, roda mesmo — dedup por quote segura).

    SPEC-059 §29.1 — CUTOVER. Com `INTELLIGENCE_CUTOVER` ligado (padrão), a
    mineração passa a ser um Work Run agendado pelo tick do Smith Worker, e
    o resultado vira `intelligence_signals` em vez de linha solta em
    `broker_insights`. A regex desta módulo continua sendo a camada A do
    Garimpo v3 — ela é importada, não reescrita.

    O job continua registrado de propósito: desligar a flag devolve o
    comportamento antigo sem precisar de deploy. É rollback, não convivência.
    """
    try:
        from app.services.intelligence.legacy_adapter import cutover_ligado

        if cutover_ligado():
            return 0
    except Exception:  # noqa: BLE001 — sem o pacote, segue no caminho antigo
        pass

    mined = 0
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
        mined = await mine_recent(hours=24)
        return mined
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[GARIMPO] check falhou: {type(e).__name__}")
        return 0
    finally:
        try:
            from app.core.heartbeat import beat

            # SPEC-050: pulso COM contagem — antes batia sem número e a Central
            # mostrava o Garimpo com "0 ações" mesmo minerando.
            await beat("garimpo", mined)
        except Exception:  # noqa: BLE001
            pass
