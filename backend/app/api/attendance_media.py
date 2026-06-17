"""
Attendance Media — transcrição de áudio (42M0).

Reusa o AudioService do Smith (Whisper) para transcrever áudio do atendimento,
por URL (WhatsApp/Z-API) ou base64 (simulado/dashboard). STATELESS: não persiste
nada, não chama LLM/RAG, não aciona externo. Auth por chave interna Next↔Backend.

NUNCA loga URL/base64/conteúdo; só ids e tamanhos. NÃO confirma cobertura.
"""
import hmac
import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.audio_service import AudioService

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_TRANSCRIPT_LEN = 4000


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
