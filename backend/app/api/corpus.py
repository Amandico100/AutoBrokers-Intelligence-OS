"""API do corpus normativo. SPEC-057 §Bloco H.

Rotas de **plataforma**, não de tenant. O corpus é o mesmo para todas as
corretoras — por isso nenhuma rota aqui recebe `company_id`, e nenhuma delas
pode ser chamada por um corretor.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.database import get_supabase_client
from app.services.knowledge.insurance_corpus import InsuranceCorpusService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/corpus", tags=["Corpus Normativo"])


def _autorizar(chave: Optional[str]) -> None:
    esperada = (os.getenv("BACKEND_INTERNAL_API_KEY")
                or os.getenv("ADMIN_API_KEY") or "").strip()
    if not esperada:
        raise HTTPException(503, "chave interna nao configurada")
    if (chave or "").strip() != esperada:
        raise HTTPException(401, "nao autorizado")


class DescobrirIn(BaseModel):
    insurer_key: str
    site: str
    limite: int = 60


class RegistrarIn(BaseModel):
    insurer_key: str
    insurer_name: str
    product_line: str
    doc_kind: str
    title: str
    source_url: str
    susep_process: Optional[str] = None
    effective_from: Optional[str] = None
    check_interval_days: int = 45


class CuradoriaIn(BaseModel):
    document_id: str
    user_id: Optional[str] = None
    interval_days: Optional[int] = None
    motivo: Optional[str] = None


@router.get("")
async def catalogo(insurer_key: Optional[str] = None,
                   product_line: Optional[str] = None,
                   x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    svc = InsuranceCorpusService(get_supabase_client())
    return {"ok": True, "documentos": svc.catalogo(
        insurer_key=insurer_key, product_line=product_line)}


@router.get("/candidatos")
async def candidatos(x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    return {"ok": True, "candidatos": InsuranceCorpusService(
        get_supabase_client()).candidatos()}


@router.post("/descobrir")
async def descobrir(payload: DescobrirIn, x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    r = await InsuranceCorpusService(get_supabase_client()).descobrir(
        insurer_key=payload.insurer_key, site=payload.site, limite=payload.limite)
    return r


@router.post("/registrar")
async def registrar(payload: RegistrarIn, x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    d = InsuranceCorpusService(get_supabase_client()).registrar(**payload.model_dump())
    return {"ok": True, "documento": d}


@router.post("/aprovar")
async def aprovar(payload: CuradoriaIn, x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    d = InsuranceCorpusService(get_supabase_client()).aprovar(
        payload.document_id, user_id=payload.user_id, interval_days=payload.interval_days)
    return {"ok": True, "documento": d}


@router.post("/rejeitar")
async def rejeitar(payload: CuradoriaIn, x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    ok = InsuranceCorpusService(get_supabase_client()).rejeitar(
        payload.document_id, motivo=payload.motivo or "", user_id=payload.user_id)
    return {"ok": ok}


@router.post("/ingerir/{document_id}")
async def ingerir(document_id: str, x_internal_key: Optional[str] = Header(None)):
    """Ingere um documento aprovado, agora, sem esperar o ciclo do worker."""
    _autorizar(x_internal_key)
    r = await InsuranceCorpusService(get_supabase_client()).ingerir(document_id)
    if not r.get("ok"):
        raise HTTPException(422, f"nao ingerido: {r.get('motivo')}")
    return r


@router.post("/reconferir")
async def reconferir(limite: int = 5, x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    return await InsuranceCorpusService(get_supabase_client()).reconferir_pendentes(
        limite=max(1, min(limite, 20)))
