"""SPEC-040 Onda 4 — Sentinela de Regressão (o Auditor que nunca dorme).

O requisito nº 1 do founder: EVOLUIR SEMPRE, REGREDIR NUNCA. Este módulo é o
alarme: compara a nota média das conversas das últimas 24h (scorecards do
Auditor) com a média dos 7 dias anteriores, POR corretora. Queda relevante =
alerta no canal de suporte da corretora + registro em Atividades — o problema
aparece para nós ANTES do cliente reclamar.

Determinístico e grátis (zero LLM): usa os scorecards que o Auditor já grava.
Roda 1x/dia (marcador Redis). Limiares por env:
- REGRESSION_MIN_SAMPLES (default 5): mínimo de conversas nas 24h p/ comparar.
- REGRESSION_DROP_POINTS (default 10): queda de nota que dispara o alerta.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_MARKER = "regression:last_run"


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _load_scorecards_sync(days: int = 8) -> List[Dict[str, Any]]:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    return (db.client.table("conversation_scorecards")
            .select("company_id, score, flags, created_at")
            .gte("created_at", since).order("created_at", desc=True)
            .limit(2000).execute().data or [])


def analyze_regressions(rows: List[Dict[str, Any]], now: datetime,
                        min_samples: int, drop_points: int) -> List[Dict[str, Any]]:
    """Puro e testável: [{company_id, recent_avg, baseline_avg, drop, samples, top_flags}]."""
    cutoff = now - timedelta(hours=24)
    by_company: Dict[str, Dict[str, list]] = {}
    for r in rows:
        try:
            created = datetime.fromisoformat(str(r.get("created_at")).replace("Z", "+00:00"))
        except ValueError:
            continue
        cid = str(r.get("company_id") or "")
        bucket = by_company.setdefault(cid, {"recent": [], "baseline": [], "flags": []})
        target = "recent" if created >= cutoff else "baseline"
        bucket[target].append(int(r.get("score") or 0))
        if target == "recent":
            bucket["flags"] += list(r.get("flags") or [])

    findings = []
    for cid, b in by_company.items():
        if len(b["recent"]) < min_samples or len(b["baseline"]) < min_samples:
            continue
        recent_avg = sum(b["recent"]) / len(b["recent"])
        baseline_avg = sum(b["baseline"]) / len(b["baseline"])
        drop = baseline_avg - recent_avg
        if drop >= drop_points:
            flag_counts: Dict[str, int] = {}
            for f in b["flags"]:
                flag_counts[str(f)] = flag_counts.get(str(f), 0) + 1
            top = sorted(flag_counts.items(), key=lambda x: -x[1])[:3]
            findings.append({"company_id": cid, "recent_avg": round(recent_avg, 1),
                             "baseline_avg": round(baseline_avg, 1), "drop": round(drop, 1),
                             "samples": len(b["recent"]),
                             "top_flags": [f for f, _ in top]})
    return findings


async def _alert(company_id: str, finding: Dict[str, Any]) -> None:
    """Alerta pelo MESMO canal do Vigia (grupo/número de suporte da corretora)."""
    try:
        from app.services.dispatch_router import _support_contact
        from app.services.integration_service import get_integration_service
        from app.services.whatsapp_service import get_whatsapp_service

        contact = await _support_contact(company_id)
        integration = get_integration_service().get_platform_whatsapp_integration(company_id)
        if not contact or not integration:
            logger.warning(f"[REGRESSAO] sem canal de alerta p/ company {company_id}")
            return
        flags = ", ".join(finding.get("top_flags") or []) or "sem padrão dominante"
        text = ("⚠️ QUALIDADE EM QUEDA — atendimento\n"
                f"Nota média caiu de {finding['baseline_avg']} para {finding['recent_avg']} "
                f"nas últimas 24h ({finding['samples']} conversas).\n"
                f"Padrões mais comuns: {flags}.\n"
                "Verificando a causa — nenhuma mudança nova será aplicada até estabilizar.")
        get_whatsapp_service().send_message(contact, text, integration)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[REGRESSAO] alerta falhou: {type(e).__name__}")


async def check_regression() -> int:
    """Task periódica (horária; executa 1x/dia via marcador). Nunca derruba o
    scheduler. Retorna o número de regressões detectadas."""
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        today = datetime.now(timezone.utc).date().isoformat()
        marker = await r.get(_MARKER)
        marker = marker.decode() if isinstance(marker, (bytes, bytearray)) else marker
        if marker == today:
            return 0
        await r.set(_MARKER, today, ex=3 * 86400)
    except Exception:  # noqa: BLE001
        pass

    try:
        rows = await asyncio.to_thread(_load_scorecards_sync)
        findings = analyze_regressions(
            rows, datetime.now(timezone.utc),
            _env_int("REGRESSION_MIN_SAMPLES", 5), _env_int("REGRESSION_DROP_POINTS", 10))
        for f in findings:
            await _alert(f["company_id"], f)
            try:
                from app.services.activity_log import log_activity

                await log_activity(f["company_id"], "qualidade",
                                   "Alerta de regressão de qualidade",
                                   f"nota {f['baseline_avg']} -> {f['recent_avg']} "
                                   f"({f['samples']} conversas 24h)")
            except Exception:  # noqa: BLE001
                pass
        try:
            from app.core.heartbeat import beat

            await beat("auditor", len(findings))
        except Exception:  # noqa: BLE001
            pass
        if findings:
            logger.warning(f"[REGRESSAO] {len(findings)} corretora(s) com queda de qualidade")
        return len(findings)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[REGRESSAO] check falhou: {type(e).__name__}")
        return 0
