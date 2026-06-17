"""
Attendance Media — transcrição de áudio (42M0).

Reusa o AudioService do Smith (Whisper) para transcrever áudio do atendimento,
por URL (WhatsApp/Z-API) ou base64 (simulado/dashboard). STATELESS: não persiste
nada, não chama LLM/RAG, não aciona externo. Auth por chave interna Next↔Backend.

NUNCA loga URL/base64/conteúdo; só ids e tamanhos. NÃO confirma cobertura.
"""
import asyncio
import base64
import hmac
import io
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import AsyncSupabaseClient, get_async_db
from app.services.audio_service import AudioService

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_TRANSCRIPT_LEN = 4000
MAX_SUMMARY_LEN = 800
VISION_TIMEOUT_S = 30
_LONG_DIGITS_RE = re.compile(r"\d[\d.\-/\s]{9,}\d")


def _mask_pii(text: Optional[str]) -> str:
    if not text:
        return ""
    return _LONG_DIGITS_RE.sub("[omitido]", str(text))


def _require_internal_key(provided: Optional[str]) -> None:
    expected = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    if not expected:
        raise HTTPException(status_code=500, detail="Internal API key not configured")
    if not provided or not hmac.compare_digest(str(provided), str(expected)):
        raise HTTPException(status_code=401, detail="Unauthorized internal request")


class TranscribePayload(BaseModel):
    company_id: str
    agent_id: Optional[str] = None
    audio_url: Optional[str] = None
    audio_base64: Optional[str] = None


@router.post("/attendance/media/transcribe")
async def attendance_media_transcribe(
    payload: TranscribePayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)

    company_id = (payload.company_id or "").strip()
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")
    if not payload.audio_url and not payload.audio_base64:
        return {"ok": False, "error": "no_audio"}

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return {"ok": False, "error": "transcription_unavailable"}

    service = AudioService(api_key)
    try:
        if payload.audio_url:
            text = await service.transcribe_audio_from_url(
                payload.audio_url, company_id=company_id, agent_id=payload.agent_id
            )
        else:
            text = await service.transcribe_audio(
                payload.audio_base64, company_id=company_id, agent_id=payload.agent_id
            )
    except Exception as e:  # noqa: BLE001
        logger.error(f"[ATTENDANCE MEDIA] transcribe error: {type(e).__name__}")
        return {"ok": False, "error": "transcription_failed"}

    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "empty_transcription"}
    if len(text) > MAX_TRANSCRIPT_LEN:
        text = text[:MAX_TRANSCRIPT_LEN]

    # Log sanitizado: só ids e tamanho (sem conteúdo/url/base64).
    logger.info(f"[ATTENDANCE MEDIA] transcribed company={company_id} len={len(text)}")
    return {"ok": True, "text": text, "provider": "whisper", "safe": True}


# ---------------------------------------------------------------------------
# Vision (42M1) — reusa o padrão de visão do Smith (chat.py): vision_model do
# agente + ChatOpenAI/ChatAnthropic com mensagem multimodal. NÃO confirma cobertura.
# ---------------------------------------------------------------------------
class VisionPayload(BaseModel):
    company_id: str
    agent_id: Optional[str] = None
    case_id: Optional[str] = None
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    mime_type: Optional[str] = None
    purpose: str = "attendance_evidence"


_VISION_SYSTEM = (
    "Você analisa uma imagem enviada por um SEGURADO num atendimento de assistência residencial. "
    "Descreva objetivamente APENAS o que é visível e relevante (ex.: quadro elétrico, disjuntor, tomada, "
    "fiação, lâmpada, vazamento, cano, fechadura, dano, ou se parece um documento/apólice). "
    "Se houver sinais de risco (fogo, fumaça, faísca, derretimento, cheiro de queimado aparente), aponte. "
    "NÃO confirme cobertura, NÃO invente, NÃO leia dados pessoais. Responda em 2-3 frases."
)


def _build_vision_llm(vision_model: str):
    if vision_model.startswith("gpt-") or vision_model == "gpt-4o":
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return None
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=vision_model, api_key=key, temperature=0.2)
    if vision_model.startswith("claude"):
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            return None
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=vision_model, api_key=key, temperature=0.2)
    return None


@router.post("/attendance/media/vision-analyze")
async def attendance_media_vision(
    payload: VisionPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    db: AsyncSupabaseClient = Depends(get_async_db),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    company_id = (payload.company_id or "").strip()
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")
    image = payload.image_url or (f"data:{payload.mime_type or 'image/jpeg'};base64,{payload.image_base64}" if payload.image_base64 else None)
    if not image:
        return {"ok": False, "status": "unsupported", "error": "no_image"}

    # Resolver vision_model do agente (mesmo padrão do chat.py).
    vision_model = None
    if payload.agent_id:
        try:
            res = (
                await db.client.table("agents").select("vision_model, agent_role").eq("id", payload.agent_id).limit(1).execute()
            )
            if res and res.data:
                vision_model = res.data[0].get("vision_model")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[ATTENDANCE VISION] agent fetch failed: {type(e).__name__}")
    if not vision_model:
        return {"ok": False, "status": "unsupported", "error": "vision_model_not_configured",
                "limitations": ["Agente sem vision_model configurado."], "provenance": "attendance_vision"}

    llm = _build_vision_llm(vision_model)
    if llm is None:
        return {"ok": False, "status": "unsupported", "error": "vision_provider_unavailable",
                "limitations": ["Provider de visão indisponível."], "provenance": "attendance_vision"}

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=_VISION_SYSTEM),
            HumanMessage(content=[{"type": "text", "text": "Descreva a imagem para o atendimento:"}, {"type": "image_url", "image_url": {"url": image}}]),
        ]
        result = await asyncio.wait_for(llm.ainvoke(messages), timeout=VISION_TIMEOUT_S)
        summary = result.content if hasattr(result, "content") else str(result)
        if isinstance(summary, list):
            summary = " ".join(str(p.get("text", p)) if isinstance(p, dict) else str(p) for p in summary)
        summary = _mask_pii(summary).strip()[:MAX_SUMMARY_LEN]
    except asyncio.TimeoutError:
        return {"ok": False, "status": "failed", "error": "vision_timeout", "provenance": "attendance_vision"}
    except Exception as e:  # noqa: BLE001
        logger.error(f"[ATTENDANCE VISION] error: {type(e).__name__}")
        return {"ok": False, "status": "failed", "error": "vision_failed", "provenance": "attendance_vision"}

    if not summary:
        return {"ok": False, "status": "failed", "error": "empty_summary", "provenance": "attendance_vision"}
    logger.info(f"[ATTENDANCE VISION] company={company_id} model={vision_model} summary_len={len(summary)}")
    return {
        "ok": True,
        "status": "processed",
        "visual_summary": summary,
        "confidence": "medium",
        "limitations": ["Resumo visual auxiliar; não confirma cobertura."],
        "provenance": f"vision:{vision_model}",
    }


# ---------------------------------------------------------------------------
# Document extract (42M1) — placeholder seguro. Extração madura (Docling/ingestion)
# fica para 42M2; aqui NÃO criamos parser frágil nem confirmamos cobertura.
# ---------------------------------------------------------------------------
class DocumentPayload(BaseModel):
    company_id: str
    agent_id: Optional[str] = None
    case_id: Optional[str] = None
    document_url: Optional[str] = None
    document_base64: Optional[str] = None
    mime_type: Optional[str] = None
    filename: Optional[str] = None
    purpose: str = "attendance_evidence"


_FILE_TYPE_BY_MIME = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "docx",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/csv": "csv",
}
_DOC_INSURERS = {"allianz": "Allianz", "porto": "Porto Seguro", "azul": "Azul", "hdi": "HDI", "tokio": "Tokio Marine", "bradesco": "Bradesco", "mapfre": "Mapfre", "suhai": "Suhai"}
_DATE_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
_POLICY_NUM_RE = re.compile(r"\b(?:ap[óo]lice|n[ºo°]\.?)\s*[:#]?\s*(\d{4,})\b", re.IGNORECASE)


def _file_type(mime: Optional[str], filename: Optional[str]) -> Optional[str]:
    if mime and mime.lower() in _FILE_TYPE_BY_MIME:
        return _FILE_TYPE_BY_MIME[mime.lower()]
    if filename and "." in filename:
        ext = filename.lower().rsplit(".", 1)[-1]
        return {"pdf": "pdf", "docx": "docx", "doc": "docx", "txt": "txt", "md": "md", "csv": "csv"}.get(ext)
    return None


def _detect_document_type(text: str) -> str:
    t = text.lower()
    if re.search(r"ap[óo]lice|seguradora|vig[êe]ncia|condi[çc][õo]es gerais|ramo\b", t):
        return "policy_document"
    if re.search(r"nota fiscal|recibo|comprovante|fatura|boleto|valor pago", t):
        return "invoice_or_receipt"
    if re.search(r"sinistro|laudo|boletim de ocorr[êe]ncia|aviso de sinistro", t):
        return "claim_report"
    if re.search(r"\bcnh\b|carteira de identidade|registro geral|\brg\b", t):
        return "identity_document"
    if re.search(r"matr[íi]cula do im[óo]vel|escritura|iptu|im[óo]vel", t):
        return "property_document"
    return "general_attachment"


def _extract_policy_info(text: str) -> Dict[str, Any]:
    t = text.lower()
    insurer = next((label for key, label in _DOC_INSURERS.items() if key in t), None)
    product = None
    if re.search(r"residencial|resid[êe]ncia", t):
        product = "Residencial"
    elif re.search(r"autom[óo]vel|\bauto\b|ve[íi]culo", t):
        product = "Automóvel"
    dates = _DATE_RE.findall(text)[:2]
    pol = _POLICY_NUM_RE.search(text)
    policy_masked = None
    if pol:
        d = re.sub(r"\D", "", pol.group(1))
        if len(d) >= 2:
            policy_masked = f"****{d[-2:]}"
    mentions_electrician = bool(re.search(r"assist[êe]ncia.*el[ée]tric|eletricista|el[ée]tric", t))
    return {
        "insurer": insurer,
        "product": product,
        "valid_dates": dates or None,
        "masked_policy_number": policy_masked,
        "document_mentions_assistance_electrician": mentions_electrician,
    }


@router.post("/attendance/media/document-extract")
async def attendance_media_document(
    payload: DocumentPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    if not (payload.company_id or "").strip():
        raise HTTPException(status_code=400, detail="company_id is required")
    if not payload.document_url and not payload.document_base64:
        return {"ok": False, "status": "unsupported", "error": "no_document"}

    file_type = _file_type(payload.mime_type, getattr(payload, "filename", None))
    if not file_type:
        return {"ok": False, "status": "unsupported", "error": "unsupported_mime",
                "limitations": ["Tipo de documento não suportado para extração inline (PDF/DOCX/TXT/MD/CSV)."],
                "provenance": "attendance_document"}

    max_bytes = max(1, settings.ATTENDANCE_MEDIA_MAX_SIZE_MB) * 1024 * 1024
    # Obter bytes (base64 ou URL), com limite de tamanho.
    try:
        if payload.document_base64:
            raw = payload.document_base64.split(",", 1)[-1]
            data = base64.b64decode(raw)
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(payload.document_url)  # type: ignore[arg-type]
                resp.raise_for_status()
                data = resp.content
        if len(data) > max_bytes:
            return {"ok": False, "status": "unsupported", "error": "document_too_large",
                    "limitations": [f"Documento acima de {settings.ATTENDANCE_MEDIA_MAX_SIZE_MB}MB."], "provenance": "attendance_document"}
    except Exception as e:  # noqa: BLE001
        logger.error(f"[ATTENDANCE DOC] fetch error: {type(e).__name__}")
        return {"ok": False, "status": "failed", "error": "document_fetch_failed", "provenance": "attendance_document"}

    # Reuso do DocumentService do Smith (extração SÍNCRONA, sem Qdrant/ingestion).
    try:
        from app.services.document_service import get_document_service

        text, _pages = get_document_service().extract_text_internal(io.BytesIO(data), file_type)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[ATTENDANCE DOC] extract error: {type(e).__name__}")
        return {"ok": False, "status": "failed", "error": "extraction_failed", "provenance": "attendance_document"}

    text = (text or "").strip()
    if not text:
        return {"ok": False, "status": "failed", "error": "empty_text",
                "limitations": ["Não consegui extrair texto legível do documento."], "provenance": "attendance_document"}

    doc_type = _detect_document_type(text)
    policy_info = _extract_policy_info(text)
    summary = _mask_pii(text)[:MAX_SUMMARY_LEN].strip()
    key_facts: List[str] = []
    if policy_info.get("insurer"):
        key_facts.append(f"Seguradora citada: {policy_info['insurer']}")
    if policy_info.get("product"):
        key_facts.append(f"Produto/ramo citado: {policy_info['product']}")
    if policy_info.get("valid_dates"):
        key_facts.append(f"Datas de vigência citadas: {', '.join(policy_info['valid_dates'])}")
    if policy_info.get("document_mentions_assistance_electrician"):
        key_facts.append("Menciona assistência elétrica (em termos gerais)")

    logger.info(f"[ATTENDANCE DOC] company={payload.company_id} type={doc_type} text_len={len(text)} extracted")
    return {
        "ok": True,
        "status": "processed",
        "document_type": doc_type,
        "extracted_text_summary": summary,
        "key_facts": key_facts,
        "possible_policy_info": policy_info,
        "limitations": [
            "Resumo auxiliar do documento; NÃO confirma cobertura.",
            "Documento enviado pelo cliente NÃO substitui a validação oficial via InfoCap.",
        ],
        "confidence": "medium",
        "provenance": f"document_service:{file_type}",
        "redaction": ["texto_bruto_omitido", "url_omitida", "base64_omitido"],
    }
