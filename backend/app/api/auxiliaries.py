"""
Auxiliaries API — execução do Auxiliar "Resumo de Atendimentos" (MVP, read-only).

Camada de produto sobre o runtime Smith (ADR-001 §10, UX-007). Lê conversas/mensagens
da MESMA empresa, gera um resumo estruturado com LLM e registra a execução em
`public.auxiliary_runs`. NÃO envia nada externo, NÃO altera conversas.

Tabelas usadas (criadas manualmente no Supabase — 38A1):
- public.tenant_auxiliaries (instalação por empresa)
- public.auxiliary_runs (execuções)
- public.conversations / public.messages (fonte, somente leitura)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import AsyncSupabaseClient, get_async_db
from app.core.utils import get_api_key_for_provider

logger = logging.getLogger(__name__)

router = APIRouter()

RESUMO_SLUG = "resumo-atendimentos"
DEFAULT_MAX_MESSAGES = 80
DEFAULT_MODEL = "gpt-4o-mini"
RECENT_CONVERSATIONS_SCAN = 20

SYSTEM_PROMPT = (
    "Você é um analista de operações de uma corretora de seguros.\n"
    "Sua tarefa é resumir UMA conversa/atendimento com base APENAS nas mensagens fornecidas.\n"
    "Não invente informações. Se algo não estiver claro nas mensagens, retorne lista vazia.\n"
    "Responda SOMENTE com um objeto JSON válido, em português do Brasil, com as chaves:\n"
    "{\n"
    '  "summary": "resumo objetivo do atendimento (3 a 6 frases)",\n'
    '  "topics": ["principais assuntos tratados"],\n'
    '  "decisions": ["decisões ou acordos registrados"],\n'
    '  "pending_items": ["pendências e o que falta resolver"],\n'
    '  "next_steps": ["próximos passos sugeridos para a corretora"],\n'
    '  "confidence": "low | medium | high"\n'
    "}\n"
    "Use linguagem clara e profissional. Foque na operação da corretora "
    "(cliente, apólice, sinistro, assistência, renovação, documento, cobrança)."
)


class ResumoRunRequest(BaseModel):
    company_id: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_output() -> Dict[str, Any]:
    return {
        "summary": "",
        "topics": [],
        "decisions": [],
        "pending_items": [],
        "next_steps": [],
        "confidence": "low",
    }


@router.post("/resumo-atendimentos/run")
async def run_resumo_atendimentos(
    payload: ResumoRunRequest,
    db: AsyncSupabaseClient = Depends(get_async_db),
):
    """Executa o Auxiliar de Resumo de Atendimentos para a empresa autenticada (read-only)."""
    company_id = (payload.company_id or "").strip()
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")

    # 1. Localizar tenant auxiliary ATIVO (escopo: company + slug + active)
    try:
        ta_resp = (
            await db.client.table("tenant_auxiliaries")
            .select("id, company_id, slug, status")
            .eq("company_id", company_id)
            .eq("slug", RESUMO_SLUG)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"[AUX] tenant_auxiliaries lookup failed: {e}")
        raise HTTPException(status_code=500, detail="Falha ao localizar o Auxiliar.")

    if not ta_resp.data:
        raise HTTPException(
            status_code=404,
            detail="O Auxiliar 'Resumo de Atendimentos' não está ativo para esta empresa.",
        )
    tenant_auxiliary_id = ta_resp.data[0]["id"]

    # 2. Selecionar conversa (sempre validada por company_id — anti-IDOR)
    conversation_id = (payload.conversation_id or "").strip() or None
    if conversation_id:
        conv_resp = (
            await db.client.table("conversations")
            .select("id, company_id")
            .eq("id", conversation_id)
            .eq("company_id", company_id)
            .limit(1)
            .execute()
        )
        if not conv_resp.data:
            raise HTTPException(status_code=404, detail="Conversa não encontrada para esta empresa.")
    else:
        conversation_id = await _pick_recent_conversation_with_messages(db, company_id)
        if not conversation_id:
            raise HTTPException(
                status_code=422,
                detail="Nenhuma conversa com mensagens encontrada para resumir.",
            )

    # 3. Registrar execução (status=running)
    run_input = {
        "conversation_id": conversation_id,
        "source": "manual",
        "max_messages": DEFAULT_MAX_MESSAGES,
    }
    run_id = await _create_run(db, company_id, tenant_auxiliary_id, run_input, payload.user_id)
    if not run_id:
        raise HTTPException(status_code=500, detail="Falha ao registrar a execução.")

    # 4. Ler mensagens (ordenadas, limitadas, escopadas pela conversa validada)
    try:
        msgs_resp = (
            await db.client.table("messages")
            .select("role, content, created_at")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=False)
            .limit(DEFAULT_MAX_MESSAGES)
            .execute()
        )
        messages: List[Dict[str, Any]] = msgs_resp.data or []
    except Exception as e:  # noqa: BLE001
        logger.error(f"[AUX] messages read failed: {e}")
        await _fail_run(db, run_id, "Falha ao ler as mensagens da conversa.")
        raise HTTPException(status_code=500, detail="Falha ao ler as mensagens da conversa.")

    if not messages:
        await _fail_run(db, run_id, "Conversa sem mensagens.")
        raise HTTPException(status_code=422, detail="A conversa selecionada não tem mensagens.")

    # 5. Gerar resumo via LLM
    try:
        output, usage, model_name = await _summarize(messages)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[AUX] LLM summarization failed: {e}")
        await _fail_run(db, run_id, "Falha ao gerar o resumo com a IA.")
        raise HTTPException(status_code=502, detail="Falha ao gerar o resumo com a IA.")

    # 6. Custo (best-effort — nunca derruba a execução)
    cost_usd = 0.0
    try:
        from app.services.usage_service import get_usage_service

        svc = get_usage_service()
        in_tok = int(usage.get("input_tokens") or 0)
        out_tok = int(usage.get("output_tokens") or 0)
        cost_usd = float(svc.calculate_cost(model_name, in_tok, out_tok))
        svc.track_cost_sync(
            service_type="auxiliary_run",
            model=model_name,
            input_tokens=in_tok,
            output_tokens=out_tok,
            company_id=company_id,
            details={
                "auxiliary": RESUMO_SLUG,
                "run_id": run_id,
                "tenant_auxiliary_id": tenant_auxiliary_id,
            },
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[AUX] usage logging failed (non-fatal): {e}")

    # 7. Sucesso
    await _succeed_run(db, run_id, output, usage, cost_usd, model_name, conversation_id)

    return {
        "success": True,
        "run": {
            "id": run_id,
            "status": "succeeded",
            "output": output,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


async def _pick_recent_conversation_with_messages(
    db: AsyncSupabaseClient, company_id: str
) -> Optional[str]:
    """Conversa mais recente da empresa que tenha ao menos uma mensagem."""
    try:
        convs = (
            await db.client.table("conversations")
            .select("id, last_message_at")
            .eq("company_id", company_id)
            .order("last_message_at", desc=True)
            .limit(RECENT_CONVERSATIONS_SCAN)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"[AUX] conversations scan failed: {e}")
        return None

    for conv in convs.data or []:
        conv_id = conv.get("id")
        if not conv_id:
            continue
        check = (
            await db.client.table("messages")
            .select("id")
            .eq("conversation_id", conv_id)
            .limit(1)
            .execute()
        )
        if check.data:
            return conv_id
    return None


async def _create_run(
    db: AsyncSupabaseClient,
    company_id: str,
    tenant_auxiliary_id: str,
    run_input: Dict[str, Any],
    user_id: Optional[str],
) -> Optional[str]:
    row = {
        "company_id": company_id,
        "tenant_auxiliary_id": tenant_auxiliary_id,
        "run_type": "manual",
        "status": "running",
        "input": run_input,
        "started_at": _now(),
        "metadata": {"source": "manual", "user_id": user_id},
    }
    try:
        resp = await db.client.table("auxiliary_runs").insert(row).execute()
        if resp.data:
            return resp.data[0]["id"]
    except Exception as e:  # noqa: BLE001
        logger.error(f"[AUX] create run failed: {e}")
    return None


async def _fail_run(db: AsyncSupabaseClient, run_id: str, error_message: str) -> None:
    try:
        await db.client.table("auxiliary_runs").update(
            {
                "status": "failed",
                "error_message": error_message,
                "output": _empty_output(),
                "finished_at": _now(),
            }
        ).eq("id", run_id).execute()
    except Exception as e:  # noqa: BLE001
        logger.error(f"[AUX] fail-run update error: {e}")


async def _succeed_run(
    db: AsyncSupabaseClient,
    run_id: str,
    output: Dict[str, Any],
    usage: Dict[str, Any],
    cost_usd: float,
    model_name: str,
    conversation_id: str,
) -> None:
    try:
        await db.client.table("auxiliary_runs").update(
            {
                "status": "succeeded",
                "output": output,
                "token_usage": usage,
                "cost_usd": cost_usd,
                "finished_at": _now(),
                "metadata": {
                    "provider": "openai",
                    "model": model_name,
                    "source": "manual",
                    "conversation_id": conversation_id,
                },
            }
        ).eq("id", run_id).execute()
    except Exception as e:  # noqa: BLE001
        logger.error(f"[AUX] succeed-run update error: {e}")


def _format_transcript(messages: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for m in messages:
        role = "Cliente" if m.get("role") == "user" else "Atendente/IA"
        content = (m.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "Transcrição do atendimento:\n\n" + "\n".join(lines)


def _parse_output(raw: str) -> Dict[str, Any]:
    out = _empty_output()
    data: Any = {}
    try:
        data = json.loads(raw)
    except Exception:  # noqa: BLE001
        data = {}
    if isinstance(data, dict):
        out["summary"] = str(data.get("summary") or "")
        for key in ("topics", "decisions", "pending_items", "next_steps"):
            val = data.get(key)
            out[key] = [str(x) for x in val if str(x).strip()] if isinstance(val, list) else []
        conf = str(data.get("confidence") or "low").lower()
        out["confidence"] = conf if conf in ("low", "medium", "high") else "low"
    return out


def _extract_usage(resp: Any) -> Dict[str, Any]:
    meta = getattr(resp, "usage_metadata", None)
    if isinstance(meta, dict) and meta:
        return {
            "input_tokens": meta.get("input_tokens", 0),
            "output_tokens": meta.get("output_tokens", 0),
            "total_tokens": meta.get("total_tokens", 0),
        }
    rmeta = getattr(resp, "response_metadata", {}) or {}
    tu = rmeta.get("token_usage") or {}
    return {
        "input_tokens": tu.get("prompt_tokens", 0),
        "output_tokens": tu.get("completion_tokens", 0),
        "total_tokens": tu.get("total_tokens", 0),
    }


async def _summarize(messages: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """Chama o LLM (reuso de langchain_openai já presente no runtime) e retorna (output, usage, model)."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    model_name = DEFAULT_MODEL
    api_key = get_api_key_for_provider("openai", model_name)

    transcript = _format_transcript(messages)
    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        temperature=0.2,
        max_tokens=1200,
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    resp = await llm.ainvoke(
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=transcript)]
    )
    raw = resp.content if isinstance(resp.content, str) else str(resp.content)
    return _parse_output(raw), _extract_usage(resp), model_name
