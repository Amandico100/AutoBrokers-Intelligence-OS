"""SPEC-042 — Lapidador: otimização reflexiva de conduta (padrão GEPA/DSPy).

O Alfaiate na forma final. Pega o FEEDBACK TEXTUAL das falhas reais (flags do
Auditor + sessões destiladas com nota baixa), reflete com o modelo FORTE e
propõe uma versão MELHOR do playbook de conduta — como DRAFT, que só assume
se passar no GATE nunca-regredir (SPEC-040 Onda 4). Auto-evolução com rede
dupla: o Lapidador propõe, o gate decide, o rollback protege, a Sentinela de
Regressão vigia em produção.

Custo: 1 chamada forte por (ramo, serviço) POR SEMANA e só quando há feedback
novo suficiente (LAPIDADOR_MIN_FEEDBACK, default 5). Sem feedback = zero.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_MARKER = "lapidador:last_run"
_WEEKLY_S = 7 * 86400

_REFLECT_SYSTEM = (
    "Você é o Lapidador: o otimizador de playbooks de conduta de atendimento "
    "(corretoras de seguros, WhatsApp). Receberá o playbook ATIVO, o FEEDBACK textual de "
    "falhas reais observadas e resumos de condutas humanas bem avaliadas. "
    "REFLITA sobre as falhas e proponha a versão MELHORADA do playbook — mantendo tudo que "
    "funciona e corrigindo especificamente o que o feedback aponta. "
    "Responda APENAS JSON válido no MESMO schema do playbook:\n"
    "{\"objetivo\": \"...\", \"acolhimento\": \"...\", "
    "\"ficha_coleta\": [{\"campo\": \"...\", \"como_pedir\": \"...\", \"quando\": \"...\", "
    "\"ja_temos_na_apolice\": true|false}], \"pre_checks\": [\"...\"], "
    "\"sensibilidade\": \"...\", \"encerramento\": \"...\", \"frases_exemplo\": [\"...\"], "
    "\"_mudancas\": [\"o que mudou e por quê, 1 linha por mudança\"]}\n"
    "Regras: campo ja_temos_na_apolice=true NUNCA vira pergunta; sem dado pessoal; "
    "uma pergunta por vez; português natural de WhatsApp."
)


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def collect_feedback_sync(ramo: str, servico: str, days: int = 14) -> List[str]:
    """Feedback TEXTUAL das falhas reais do grupo (determinístico, grátis)."""
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    feedback: List[str] = []

    try:  # sessões destiladas com nota baixa / flags
        rows = (db.client.table("attendance_sessions").select("summary")
                .gte("created_at", since).limit(500).execute().data or [])
        for r in rows:
            d = ((r.get("summary") or {}).get("distilled")) or {}
            if not d or str(d.get("ramo")) != ramo or str(d.get("servico")) != servico:
                continue
            for f in (d.get("flags") or []):
                feedback.append(f"atendimento {servico}: {f}")
            score = d.get("score")
            if score is not None and int(score) < 65:
                feedback.append(f"atendimento {servico} com nota baixa ({score}) — conduta a revisar")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[LAPIDADOR] feedback de sessões falhou: {type(e).__name__}")

    try:  # flags do Auditor nas conversas do agente
        rows = (db.client.table("conversation_scorecards").select("score, flags")
                .gte("created_at", since).limit(500).execute().data or [])
        for r in rows:
            if int(r.get("score") or 100) < 70:
                for f in (r.get("flags") or []):
                    feedback.append(f"conversa do agente: {f}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[LAPIDADOR] feedback de scorecards falhou: {type(e).__name__}")

    # dedupe preservando ordem
    seen = set()
    out = []
    for f in feedback:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out[:40]


async def optimize_playbook(ramo: str, servico: str,
                            min_feedback: Optional[int] = None) -> Dict[str, Any]:
    """Uma rodada de lapidação: feedback -> reflexão (modelo forte) -> DRAFT.
    O draft NUNCA assume sozinho — passa pelo gate da Onda 4."""
    from app.services.attendance_distiller import (
        _call_llm, _load_group_summaries_sync, _parse_json, _provider_model,
    )
    from app.services.playbook_gate import _load_active_sync, deterministic_checks

    need = min_feedback if min_feedback is not None else _env_int("LAPIDADOR_MIN_FEEDBACK", 5)
    feedback = await asyncio.to_thread(collect_feedback_sync, ramo, servico)
    if len(feedback) < need:
        return {"ok": False, "reason": "feedback_insuficiente",
                "feedback_count": len(feedback), "minimo": need}

    current = await asyncio.to_thread(_load_active_sync, ramo, servico)
    if not current:
        return {"ok": False, "reason": "sem_playbook_ativo",
                "note": "o Lapidador melhora o que existe; sem ativo, o Destilador cria o primeiro"}

    golden = await asyncio.to_thread(_load_group_summaries_sync, ramo, servico)
    user = json.dumps({
        "playbook_ativo": current.get("content"),
        "feedback_de_falhas": feedback,
        "condutas_douradas": golden[:10],
    }, ensure_ascii=False)[:14000]

    raw = await _call_llm(_REFLECT_SYSTEM, user, strong=True)
    candidate = _parse_json(raw)
    if not candidate or not candidate.get("ficha_coleta"):
        return {"ok": False, "reason": "reflexao_ilegivel"}

    mudancas = candidate.pop("_mudancas", [])
    problems = deterministic_checks(candidate)
    if problems:
        return {"ok": False, "reason": "candidato_reprovado_checks", "problems": problems}

    from app.services.attendance_distiller import _save_playbook_draft_sync

    _prov, model = _provider_model(strong=True)
    pid = await asyncio.to_thread(
        _save_playbook_draft_sync, ramo, servico, candidate, len(golden), model)
    if not pid:
        return {"ok": False, "reason": "draft_nao_salvo"}

    try:
        from app.core.heartbeat import beat

        await beat("alfaiate", 1)
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.services.activity_log import log_activity

        await log_activity("", "qualidade",
                           f"Lapidador propôs playbook otimizado — {ramo}/{servico}",
                           f"{len(feedback)} feedbacks refletidos; aguarda gate. "
                           + "; ".join(str(m) for m in mudancas[:3]))
    except Exception:  # noqa: BLE001
        pass
    logger.info(f"[LAPIDADOR] draft otimizado {ramo}/{servico} ({len(feedback)} feedbacks)")
    return {"ok": True, "draft_id": pid, "mudancas": mudancas,
            "feedback_count": len(feedback),
            "note": "draft criado — ativa SÓ se passar no gate (nunca regredir)"}


async def check_lapidador() -> int:
    """Task periódica (horária): rodada SEMANAL por grupo ativo com feedback
    novo. Zero custo sem feedback. Nunca derruba o scheduler."""
    try:
        now = datetime.now(timezone.utc)
        if now.hour not in range(3, 10):  # madrugada BRT, junto do destilador
            return 0
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        raw = await r.get(_MARKER)
        raw = raw.decode() if isinstance(raw, (bytes, bytearray)) else raw
        if raw:
            try:
                last = datetime.fromisoformat(str(raw))
                if (now - last).total_seconds() < _WEEKLY_S:
                    return 0
            except ValueError:
                pass
        await r.set(_MARKER, now.isoformat(), ex=30 * 86400)
    except Exception:  # noqa: BLE001
        pass

    optimized = 0
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()

        def _actives() -> list:
            return (db.client.table("conduct_playbooks").select("ramo, servico")
                    .eq("status", "active").limit(50).execute().data or [])

        for row in await asyncio.to_thread(_actives):
            try:
                res = await optimize_playbook(str(row.get("ramo")), str(row.get("servico")))
                if res.get("ok"):
                    optimized += 1
            except Exception as e:  # noqa: BLE001
                logger.error(f"[LAPIDADOR] grupo {row} falhou: {type(e).__name__}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[LAPIDADOR] check falhou: {type(e).__name__}")
    return optimized
