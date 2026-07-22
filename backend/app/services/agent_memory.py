"""SPEC-040 Onda 5 — Memória por agente da Central (padrão sleep-time).

Cada operário da Central ganha BLOCOS DE MEMÓRIA consultáveis — "o que o
agente sabe" — reescritos 1x/dia a partir dos dados REAIS do sistema.
Determinístico e custo ZERO de LLM: a memória é um digest factual (o padrão
Letta de reescrita no ocioso, aplicado ao nosso caso sem gastar token —
síntese com LLM pode ser plugada depois se agregar valor).

A Central lê via admin (require_master_admin). Conteúdo global de operação —
nomes de papel, nunca dado pessoal de segurado (fatos agregados/contagens).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_MARKER = "agent_memory:last_run"


def _upsert_block_sync(agent_task: str, block_key: str, content: str,
                       data: Optional[Dict[str, Any]] = None) -> None:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    db.client.table("agent_memories").upsert({
        "agent_task": agent_task, "block_key": block_key,
        "content": content[:2000], "data": data or None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="agent_task,block_key").execute()


def _since(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _rebuild_sync() -> int:
    """Reconstrói os blocos de todos os agentes. Fail-soft por bloco."""
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    written = 0

    def _write(task: str, key: str, content: str, data: Optional[Dict[str, Any]] = None) -> None:
        nonlocal written
        try:
            _upsert_block_sync(task, key, content, data)
            written += 1
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[MEMORIA AGENTES] bloco {task}/{key} falhou: {type(e).__name__}")

    # OBSERVADOR — o que já observamos por seguradora (30d)
    try:
        rows = (db.client.table("observed_sessions").select("insurer_key, company_id")
                .gte("started_at", _since(30)).limit(2000).execute().data or [])
        by_ins: Dict[str, int] = {}
        companies = set()
        for r in rows:
            by_ins[str(r.get("insurer_key") or "?")] = by_ins.get(str(r.get("insurer_key") or "?"), 0) + 1
            companies.add(str(r.get("company_id")))
        top = sorted(by_ins.items(), key=lambda x: -x[1])[:8]
        _write("observador", "cobertura",
               f"Últimos 30 dias: {len(rows)} sessões de seguradora observadas em "
               f"{len(companies)} corretora(s). Mais vistas: "
               + ", ".join(f"{k} ({v})" for k, v in top) + ".",
               {"por_seguradora": by_ins})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[MEMORIA AGENTES] observador falhou: {type(e).__name__}")

    # TECELÃO — mapas e cobertura
    try:
        rows = (db.client.table("ura_maps").select("insurer_key, ramo, status, map")
                .in_("status", ["active", "observed"]).limit(100).execute().data or [])
        parts = []
        for r in rows[:12]:
            cov = ((r.get("map") or {}).get("coverage") or {})
            parts.append(f"{r.get('insurer_key')}/{r.get('ramo')}: {cov.get('nodes', '?')} telas, "
                         f"{cov.get('pct', '?')}% [{r.get('status')}]")
        _write("tecelao", "mapas",
               f"{len(rows)} mapa(s) vivos. " + "; ".join(parts) + ".",
               {"mapas": len(rows)})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[MEMORIA AGENTES] tecelao falhou: {type(e).__name__}")

    # SENTINELA DE ROTAS — drifts recentes
    try:
        rows = (db.client.table("route_drift").select("insurer_key, severity, created_at")
                .gte("created_at", _since(30)).limit(200).execute().data or [])
        sev: Dict[str, int] = {}
        for r in rows:
            sev[str(r.get("severity") or "?")] = sev.get(str(r.get("severity") or "?"), 0) + 1
        _write("sentinela_rotas", "drifts",
               f"Últimos 30 dias: {len(rows)} mudança(s) de rota detectadas "
               f"({', '.join(f'{k}: {v}' for k, v in sev.items()) or 'nenhuma'}).",
               {"por_severidade": sev})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[MEMORIA AGENTES] sentinela falhou: {type(e).__name__}")

    # ESPELHO DE ATENDIMENTO — captura + destilação + serviços mais comuns
    try:
        rows = (db.client.table("attendance_sessions").select("company_id, summary")
                .gte("created_at", _since(30)).limit(2000).execute().data or [])
        distilled = [((r.get("summary") or {}).get("distilled") or {}) for r in rows]
        distilled = [d for d in distilled if d and not d.get("skipped")]
        servicos: Dict[str, int] = {}
        scores = []
        for d in distilled:
            servicos[str(d.get("servico") or "?")] = servicos.get(str(d.get("servico") or "?"), 0) + 1
            if d.get("score") is not None:
                scores.append(int(d["score"]))
        top_s = sorted(servicos.items(), key=lambda x: -x[1])[:6]
        media = f"{sum(scores) / len(scores):.0f}" if scores else "—"
        _write("espelho_atendimento", "captura",
               f"Últimos 30 dias: {len(rows)} sessões de atendimento capturadas, "
               f"{len(distilled)} destiladas. Serviços mais comuns: "
               + (", ".join(f"{k} ({v})" for k, v in top_s) or "—")
               + f". Nota média humana (baseline interno): {media}.",
               {"servicos": servicos, "amostras_score": len(scores)})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[MEMORIA AGENTES] espelho falhou: {type(e).__name__}")

    # AUDITOR — qualidade 7 dias
    try:
        rows = (db.client.table("conversation_scorecards").select("company_id, score")
                .gte("created_at", _since(7)).limit(1000).execute().data or [])
        scores = [int(r.get("score") or 0) for r in rows]
        media = f"{sum(scores) / len(scores):.0f}" if scores else "—"
        _write("auditor", "qualidade",
               f"Últimos 7 dias: {len(scores)} conversas auditadas, nota média {media}/100.",
               {"amostras": len(scores)})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[MEMORIA AGENTES] auditor falhou: {type(e).__name__}")

    # GARIMPO — insights por tipo (30d)
    try:
        rows = (db.client.table("broker_insights").select("kind")
                .gte("created_at", _since(30)).limit(1000).execute().data or [])
        kinds: Dict[str, int] = {}
        for r in rows:
            kinds[str(r.get("kind") or "?")] = kinds.get(str(r.get("kind") or "?"), 0) + 1
        _write("garimpo", "insights",
               f"Últimos 30 dias: {len(rows)} insight(s) de corretor — "
               + (", ".join(f"{k}: {v}" for k, v in sorted(kinds.items(), key=lambda x: -x[1])) or "nenhum")
               + ".", {"por_tipo": kinds})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[MEMORIA AGENTES] garimpo falhou: {type(e).__name__}")

    # ALFAIATE — playbooks de conduta por status
    try:
        rows = (db.client.table("conduct_playbooks").select("ramo, servico, status, version")
                .limit(200).execute().data or [])
        st: Dict[str, int] = {}
        for r in rows:
            st[str(r.get("status") or "?")] = st.get(str(r.get("status") or "?"), 0) + 1
        ativos = [f"{r.get('ramo')}/{r.get('servico')} v{r.get('version')}"
                  for r in rows if r.get("status") == "active"][:8]
        _write("alfaiate", "playbooks_conduta",
               f"Playbooks de conduta: {st.get('active', 0)} ativos, {st.get('draft', 0)} rascunhos, "
               f"{st.get('retired', 0)} guardados p/ rollback. Ativos: "
               + (", ".join(ativos) or "nenhum ainda") + ".", {"por_status": st})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[MEMORIA AGENTES] alfaiate falhou: {type(e).__name__}")

    return written


async def rebuild_agent_memories() -> int:
    """Reescreve todos os blocos + blocos vindos do Redis (cérebro/conselho)."""
    written = await asyncio.to_thread(_rebuild_sync)
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        raw = await r.get("council:last_convening")
        if raw:
            data = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
            await asyncio.to_thread(
                _upsert_block_sync, "conselho", "ultima_convocacao",
                f"Última convocação: {data.get('question')} — veredito "
                f"{data.get('verdict') or 'sem síntese'} ({data.get('members_ok')} pareceres, "
                f"{data.get('at')}).", data)
            written += 1
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.core.heartbeat import beat

        await beat("espelho", 0)  # a reescrita é silenciosa; pulso é dos donos dos dados
    except Exception:  # noqa: BLE001
        pass
    logger.info(f"[MEMORIA AGENTES] {written} bloco(s) reescritos")
    return written


async def check_agent_memories() -> int:
    """Task periódica; reescreve por janela de 6h (configurável). Custo zero."""
    try:
        import os

        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        try:
            hours = max(1, int(os.getenv("AGENT_MEMORY_INTERVAL_HOURS", "6")))
        except ValueError:
            hours = 6
        window = str(int(datetime.now(timezone.utc).timestamp() // (hours * 3600)))
        marker = await r.get(_MARKER)
        marker = marker.decode() if isinstance(marker, (bytes, bytearray)) else marker
        if marker == window:
            return 0
        await r.set(_MARKER, window, ex=3 * 86400)
    except Exception:  # noqa: BLE001
        pass
    try:
        return await rebuild_agent_memories()
    except Exception as e:  # noqa: BLE001
        logger.error(f"[MEMORIA AGENTES] check falhou: {type(e).__name__}")
        return 0


def load_all_memories_sync() -> List[Dict[str, Any]]:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    return (db.client.table("agent_memories")
            .select("agent_task, block_key, content, updated_at")
            .order("updated_at", desc=True).limit(200).execute().data or [])
