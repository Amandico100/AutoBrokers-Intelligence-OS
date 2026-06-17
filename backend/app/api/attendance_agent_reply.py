"""
Attendance Agent Reply — endpoint dedicado, STATELESS e guardrailado (42B5L-BE).

Gera UMA resposta conversacional do agente de Atendimento (insured_external) para
o segurado, usada como fallback inteligente pelo runtime de atendimento do Web.

Garantias (NÃO faz):
- não persiste mensagem do usuário nem do assistente;
- não altera conversations / messages / attendance_cases / corridor_runs;
- não cria dispatch / approval_request;
- não aciona WhatsApp / InfoCap / portal;
- não usa tools externas, RAG ingestion, memória ou grafo (apenas 1 chamada LLM);
- não usa o Core: recusa agent_id cujo agent_role != 'attendance' ou
  agent_audience != 'insured_external';
- não confirma cobertura; não expõe CPF/segredo/policy_snapshot cru.

Reusa a infraestrutura LLM existente do Smith (LLMFactory + get_api_key_for_provider).
"""
import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import UUID4, BaseModel, Field

from app.core.database import AsyncSupabaseClient, get_async_db
from app.core.utils import get_api_key_for_provider
from app.factories.llm_factory import LLMFactory

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_MESSAGE_LEN = 2000
MAX_REPLY_LEN = 1200
MAX_RECENT_TURNS = 6
LLM_TIMEOUT_S = 30


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class AgentReplyContext(BaseModel):
    case_summary: Optional[str] = None
    active_question: Optional[str] = None
    next_step: Optional[str] = None
    macro_state: Optional[str] = None
    status: Optional[str] = None
    risk_level: Optional[str] = None
    policy_verified: Optional[bool] = None
    coverage_summary: Optional[str] = None
    recent_turns: Optional[List[Dict[str, Any]]] = None
    knowledge: Optional[List[str]] = None  # 42R0: conceitos gerais (não confirma cobertura)


class AgentReplyGuardrails(BaseModel):
    audience: Optional[str] = None
    must: Optional[List[str]] = None
    never: Optional[List[str]] = None


class AgentReplyRequest(BaseModel):
    company_id: UUID4
    agent_id: UUID4
    message: str = Field(..., description="Mensagem do segurado (já sanitizada pelo Web)")
    context: Optional[AgentReplyContext] = None
    guardrails: Optional[AgentReplyGuardrails] = None


# ---------------------------------------------------------------------------
# Sanitização defensiva (defense-in-depth; o Web já deve sanitizar)
# ---------------------------------------------------------------------------
_LONG_DIGITS_RE = re.compile(r"\d[\d.\-/\s]{9,}\d")


def _mask_pii(text: Optional[str]) -> str:
    """Mascara sequências longas de dígitos (CPF/CNPJ/apólice) por precaução."""
    if not text:
        return ""
    return _LONG_DIGITS_RE.sub("[omitido]", str(text))


def _clip(text: Optional[str], n: int) -> str:
    s = (text or "").strip()
    return s[:n] if len(s) > n else s


def _build_system_prompt(ctx: Optional[AgentReplyContext], guardrails: Optional[AgentReplyGuardrails]) -> str:
    lines: List[str] = [
        "Você é o agente de atendimento da corretora falando diretamente com o SEGURADO.",
        "Você NÃO é o assistente interno da corretora (Core).",
        "Responda em português, curto e humano, estilo WhatsApp — no máximo 2 a 3 frases.",
        "Você pode responder uma dúvida geral simples, mas sempre volte ao próximo passo do atendimento.",
        "NUNCA confirme cobertura sem evidência. NUNCA diga que acionou seguradora ou prestador.",
        "NUNCA prometa prazo ou garantia. NUNCA peça dados desnecessários.",
        "NUNCA exponha CPF, estado interno, slots ou diagnósticos. NUNCA invente dados da apólice.",
        "Se a pergunta for sensível (jurídica, médica ou financeira), responda com cuidado e volte ao atendimento.",
        "Se não souber, diga de forma natural e siga o atendimento.",
    ]

    must = (guardrails.must if guardrails else None) or []
    never = (guardrails.never if guardrails else None) or []
    for m in must[:6]:
        lines.append(f"- DEVE: {_clip(str(m), 160)}")
    for n in never[:8]:
        lines.append(f"- NUNCA: {_clip(str(n), 160)}")

    if ctx:
        lines.append("")
        lines.append("Contexto do atendimento (use só para se situar, não repita literalmente):")
        if ctx.case_summary:
            lines.append(f"- Resumo: {_mask_pii(_clip(ctx.case_summary, 400))}")
        if ctx.active_question:
            lines.append(f"- Pergunta atual do atendimento: {_mask_pii(_clip(ctx.active_question, 300))}")
        if ctx.next_step:
            lines.append(f"- Próximo passo: {_mask_pii(_clip(ctx.next_step, 300))}")
        if ctx.policy_verified is not None:
            lines.append(f"- Apólice verificada: {'sim' if ctx.policy_verified else 'ainda não'}")
        if ctx.coverage_summary:
            lines.append(f"- Cobertura (resumo): {_mask_pii(_clip(ctx.coverage_summary, 300))}")
        if ctx.knowledge:
            lines.append("- Conhecimento de apoio (conceitos GERAIS; NÃO confirma cobertura específica):")
            for k in ctx.knowledge[:3]:
                lines.append(f"  • {_mask_pii(_clip(str(k), 240))}")
        if ctx.active_question:
            lines.append("")
            lines.append('Sempre conduza o segurado de volta à "Pergunta atual do atendimento" acima.')

    return "\n".join(lines)


def _build_history(ctx: Optional[AgentReplyContext]) -> List[Any]:
    msgs: List[Any] = []
    turns = (ctx.recent_turns if ctx else None) or []
    for t in turns[-MAX_RECENT_TURNS:]:
        if not isinstance(t, dict):
            continue
        role = t.get("role")
        content = _mask_pii(_clip(t.get("content"), 600))
        if not content:
            continue
        if role == "assistant":
            msgs.append(AIMessage(content=content))
        else:
            msgs.append(HumanMessage(content=content))
    return msgs


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@router.post("/attendance/agent-reply")
async def attendance_agent_reply(
    request: Request,
    body: AgentReplyRequest,
    db: AsyncSupabaseClient = Depends(get_async_db),
) -> Dict[str, Any]:
    message = (body.message or "").strip()
    if not message:
        return {"ok": False, "error": "empty_message"}
    if len(message) > MAX_MESSAGE_LEN:
        message = message[:MAX_MESSAGE_LEN]

    company_id = str(body.company_id)
    agent_id = str(body.agent_id)

    # 1. Buscar e validar o agente (deve ser de atendimento, da mesma empresa)
    try:
        res = (
            await db.client.table("agents")
            .select(
                "id, company_id, agent_role, agent_audience, llm_provider, llm_model, "
                "llm_temperature, llm_max_tokens, reasoning_effort, is_active"
            )
            .eq("id", agent_id)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.error(f"[ATTENDANCE REPLY] agent fetch error: {e}")
        return {"ok": False, "error": "reply_unavailable"}

    agent = res.data[0] if res and res.data else None
    if not agent:
        raise HTTPException(status_code=404, detail={"ok": False, "error": "agent_not_found"})

    if str(agent.get("company_id")) != company_id:
        raise HTTPException(status_code=403, detail={"ok": False, "error": "forbidden_company"})

    if agent.get("agent_role") != "attendance" or agent.get("agent_audience") != "insured_external":
        # Nunca usar o Core (ou outro papel) para responder o segurado.
        raise HTTPException(status_code=403, detail={"ok": False, "error": "not_attendance_agent"})

    # 2. Resolver API key (provider/modelo do agente) — reusa infra do Smith
    llm_provider = agent.get("llm_provider") or ""
    llm_model = agent.get("llm_model") or ""
    try:
        api_key = get_api_key_for_provider(llm_provider, llm_model)
    except Exception as e:
        logger.error(f"[ATTENDANCE REPLY] api key error: {e}")
        return {"ok": False, "error": "reply_unavailable"}

    # 3. Montar prompt curto + contexto sanitizado + histórico
    system_prompt = _build_system_prompt(body.context, body.guardrails)
    messages: List[Any] = [SystemMessage(content=system_prompt)]
    messages.extend(_build_history(body.context))
    messages.append(HumanMessage(content=_mask_pii(message)))

    # 4. UMA chamada LLM stateless (sem grafo/tools/memória/persistência)
    try:
        llm = LLMFactory.create_llm(
            company_config=agent,
            agent_data=agent,
            api_key=api_key,
            company_id=company_id,
            agent_id=agent_id,
        )
        result = await asyncio.wait_for(llm.ainvoke(messages), timeout=LLM_TIMEOUT_S)
        reply = result.content if hasattr(result, "content") else str(result)
        if isinstance(reply, list):  # alguns providers retornam blocos
            reply = " ".join(str(p.get("text", p)) if isinstance(p, dict) else str(p) for p in reply)
        reply = _clip(reply, MAX_REPLY_LEN)
    except asyncio.TimeoutError:
        logger.warning(f"[ATTENDANCE REPLY] timeout company={company_id} agent={agent_id}")
        return {"ok": False, "error": "reply_timeout"}
    except Exception as e:
        logger.error(f"[ATTENDANCE REPLY] llm error: {e}")
        return {"ok": False, "error": "reply_unavailable"}

    if not reply:
        return {"ok": False, "error": "empty_reply"}

    # Log sanitizado: apenas ids e tamanhos (sem conteúdo/PII)
    logger.info(
        f"[ATTENDANCE REPLY] company={company_id} agent={agent_id} "
        f"msg_len={len(message)} reply_len={len(reply)}"
    )

    return {
        "ok": True,
        "reply": reply,
        "safe": True,
        "agent_id": agent_id,
        "mode": "attendance_stateless_reply",
    }
