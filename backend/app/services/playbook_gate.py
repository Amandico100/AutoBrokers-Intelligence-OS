"""SPEC-040 Onda 4 — Gate de ativação de playbooks de conduta (NUNCA REGREDIR).

Nenhum playbook de conduta entra em produção sem passar no gate:

1. CHECKS DETERMINÍSTICOS (grátis, inegociáveis): estrutura completa
   (ficha_coleta com campo+como_pedir), ZERO PII em qualquer frase
   (templatize), tamanho são. PII reprova SEMPRE — sem force que valha.
2. JUIZ (modelo forte, DISTILLER_STRONG_MODEL): compara o candidato com o
   playbook ATIVO atual + os resumos de conduta dourados (nota das melhores
   atendentes humanas). Só ativa se nota_candidato >= nota_atual — regredir
   é estruturalmente impossível por este caminho.
3. CONSELHO (opcional, env COUNCIL_ENABLED): quando ligado, decisões
   estruturais passam pelos pareceres multi-modelo; veredito 'rejeitar'
   bloqueia, 'ajustar' segura o draft com as sugestões anotadas.

Ativação flip versionado: ativo atual -> retired (fica guardado);
ROLLBACK de 1 chamada reativa a versão anterior. Toda decisão é registrada
em Atividades (categoria qualidade) — auditável na Central.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_JUDGE_SYSTEM = (
    "Você é o juiz de playbooks de conduta de atendimento (corretoras de seguros, WhatsApp). "
    "Receberá o playbook CANDIDATO, o playbook ATUAL (se existir) e resumos de conduta de "
    "atendimentos humanos bem avaliados (padrão-ouro). Avalie: cobertura da coleta, ordem "
    "natural das perguntas, empatia, respeito à regra 'o que já temos na apólice se confirma, "
    "não se pergunta', segurança (sinistro/risco) e naturalidade de WhatsApp. "
    "Responda APENAS JSON válido:\n"
    "{\"nota_candidato\": 0-100, \"nota_atual\": 0-100 ou null, "
    "\"veredito\": \"aprovar|rejeitar\", \"riscos\": [\"...\"], \"melhorias\": [\"...\"]}\n"
    "Só aprove se o candidato for IGUAL OU MELHOR que o atual em TODOS os critérios de segurança."
)


def deterministic_checks(content: Dict[str, Any]) -> List[str]:
    """Problemas estruturais — lista vazia = passou. PII reprova sempre."""
    problems: List[str] = []
    if not isinstance(content, dict) or not content:
        return ["conteudo_vazio"]
    ficha = content.get("ficha_coleta")
    if not isinstance(ficha, list) or not ficha:
        problems.append("ficha_coleta_vazia")
    else:
        for i, f in enumerate(ficha):
            if not isinstance(f, dict) or not f.get("campo") or not f.get("como_pedir"):
                problems.append(f"ficha_item_{i}_incompleto")
    try:
        blob = json.dumps(content, ensure_ascii=False)
        if len(blob) > 12000:
            problems.append("playbook_grande_demais")
        from app.services.atlas.templater import templatize

        if templatize(blob) != blob:
            problems.append("pii_detectada")
    except Exception:  # noqa: BLE001
        problems.append("conteudo_ilegivel")
    return problems


async def _judge(candidate: Dict[str, Any], current: Optional[Dict[str, Any]],
                 golden: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.core.utils import get_api_key_for_provider
        from app.factories.llm_factory import LLMFactory
        from app.services.attendance_distiller import _provider_model

        provider, model = _provider_model(strong=True)
        llm = LLMFactory.create_llm(
            company_config={}, agent_data={"llm_provider": provider, "llm_model": model},
            api_key=get_api_key_for_provider(provider, model), company_id="", agent_id=None,
        )
        user = json.dumps({
            "candidato": candidate, "atual": current,
            "padrao_ouro_humano": golden[:12],
        }, ensure_ascii=False)[:14000]
        result = await llm.ainvoke([SystemMessage(content=_JUDGE_SYSTEM), HumanMessage(content=user)])
        s = str(getattr(result, "content", "") or "").strip().strip("`")
        s = s[4:] if s.lower().startswith("json") else s
        start, end = s.find("{"), s.rfind("}")
        return json.loads(s[start:end + 1]) if start >= 0 else None
    except Exception as e:  # noqa: BLE001
        logger.error(f"[GATE] juiz falhou: {type(e).__name__}")
        return None


def _load_playbook_sync(playbook_id: str) -> Optional[Dict[str, Any]]:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    rows = (db.client.table("conduct_playbooks").select("*")
            .eq("id", playbook_id).limit(1).execute().data or [])
    return rows[0] if rows else None


def _load_active_sync(ramo: str, servico: str) -> Optional[Dict[str, Any]]:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    rows = (db.client.table("conduct_playbooks").select("*")
            .eq("ramo", ramo).eq("servico", servico).eq("status", "active")
            .order("version", desc=True).limit(1).execute().data or [])
    return rows[0] if rows else None


def _set_status_sync(playbook_id: str, status: str) -> None:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    db.client.table("conduct_playbooks").update({"status": status}).eq("id", playbook_id).execute()


async def activate_playbook(playbook_id: str) -> Dict[str, Any]:
    """Roda o gate completo e, se aprovado, ativa (atual vira retired)."""
    pb = await asyncio.to_thread(_load_playbook_sync, playbook_id)
    if not pb:
        return {"ok": False, "error": "playbook_nao_encontrado"}
    if pb.get("status") == "active":
        return {"ok": True, "status": "active", "note": "ja_ativo"}

    content = pb.get("content") or {}
    problems = deterministic_checks(content)
    if problems:
        return {"ok": False, "gate": "deterministico", "problems": problems}

    ramo, servico = str(pb.get("ramo")), str(pb.get("servico"))
    current = await asyncio.to_thread(_load_active_sync, ramo, servico)

    from app.services.attendance_distiller import _load_group_summaries_sync

    golden = await asyncio.to_thread(_load_group_summaries_sync, ramo, servico)
    verdict = await _judge(content, (current or {}).get("content"), golden)
    if not verdict:
        return {"ok": False, "gate": "juiz", "error": "juiz_indisponivel"}

    nota_c = int(verdict.get("nota_candidato") or 0)
    nota_a = verdict.get("nota_atual")
    approved = str(verdict.get("veredito") or "").lower() == "aprovar" and (
        nota_a is None or nota_c >= int(nota_a))
    if current is None:
        approved = approved and nota_c >= 70  # sem atual: exige piso de qualidade
    if not approved:
        return {"ok": False, "gate": "juiz", "verdict": verdict,
                "note": "candidato nao supera o atual — draft mantido (nunca regredir)"}

    # Conselho (opcional): decisão estrutural quando LIGADO
    council_note = None
    try:
        from app.services.agent_council import convene_council

        council = await convene_council(
            f"Ativar playbook de conduta {ramo}/{servico} v{pb.get('version')}?",
            json.dumps({"resumo_juiz": verdict, "campos": [f.get("campo") for f in
                        (content.get("ficha_coleta") or [])]}, ensure_ascii=False),
            decision_kind="ativacao_playbook")
        if council.get("enabled"):
            cv = str(((council.get("synthesis") or {}).get("veredito")) or "").lower()
            council_note = cv or "sem_sintese"
            if cv == "rejeitar":
                return {"ok": False, "gate": "conselho", "council": council}
            if cv == "ajustar":
                return {"ok": False, "gate": "conselho", "council": council,
                        "note": "conselho pediu ajustes — draft mantido"}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[GATE] conselho indisponível (segue sem): {type(e).__name__}")

    # Flip versionado: atual -> retired (guardado p/ rollback); candidato -> active
    if current:
        await asyncio.to_thread(_set_status_sync, str(current.get("id")), "retired")
    await asyncio.to_thread(_set_status_sync, playbook_id, "active")

    try:
        from app.services.activity_log import log_activity

        await log_activity(
            "", "qualidade",
            f"Playbook de conduta ativado — {ramo}/{servico} v{pb.get('version')}",
            f"Gate: juiz {nota_c}" + (f" vs atual {nota_a}" if nota_a is not None else "")
            + (f"; conselho: {council_note}" if council_note else ""))
    except Exception:  # noqa: BLE001
        pass
    logger.info(f"[GATE] playbook {ramo}/{servico} v{pb.get('version')} ATIVADO "
                f"(juiz {nota_c} vs {nota_a})")
    return {"ok": True, "status": "active", "verdict": verdict, "council": council_note,
            "activated_at": datetime.now(timezone.utc).isoformat()}


async def rollback_playbook(ramo: str, servico: str) -> Dict[str, Any]:
    """Rollback de 1 chamada: ativo atual -> retired; versão anterior -> active."""
    from app.core.database import get_supabase_client

    db = get_supabase_client()

    def _versions() -> List[Dict[str, Any]]:
        return (db.client.table("conduct_playbooks").select("id, version, status")
                .eq("ramo", ramo).eq("servico", servico)
                .order("version", desc=True).limit(10).execute().data or [])

    rows = await asyncio.to_thread(_versions)
    active = next((r for r in rows if r.get("status") == "active"), None)
    if not active:
        return {"ok": False, "error": "nenhum_ativo"}
    previous = next((r for r in rows if r.get("status") == "retired"
                     and int(r.get("version") or 0) < int(active.get("version") or 0)), None)
    if not previous:
        return {"ok": False, "error": "sem_versao_anterior"}
    await asyncio.to_thread(_set_status_sync, str(active["id"]), "retired")
    await asyncio.to_thread(_set_status_sync, str(previous["id"]), "active")
    logger.info(f"[GATE] rollback {ramo}/{servico}: v{active.get('version')} -> v{previous.get('version')}")
    return {"ok": True, "from_version": active.get("version"), "to_version": previous.get("version")}
