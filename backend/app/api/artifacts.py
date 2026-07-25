"""API do Artifact Hub. SPEC-057 §Bloco B.

Uma observação sobre `/shared/{token}`: é a única rota do sistema cujo
resultado vai para alguém sem sessão. Por isso ela devolve o **mesmo** vazio
para token inexistente, expirado, revogado e esgotado. Distinguir os motivos
seria confirmar a existência de tokens para quem estivesse tentando adivinhar.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.database import get_supabase_client
from app.services.artifacts.service import ArtifactService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/artifacts", tags=["Artifact Hub"])


def _autorizar(chave: Optional[str]) -> None:
    esperada = (os.getenv("BACKEND_INTERNAL_API_KEY")
                or os.getenv("ADMIN_API_KEY") or "").strip()
    if not esperada:
        raise HTTPException(503, "chave interna nao configurada")
    if (chave or "").strip() != esperada:
        raise HTTPException(401, "nao autorizado")


class CriarIn(BaseModel):
    company_id: str
    title: str
    template_key: str
    payload: dict = Field(default_factory=dict)
    composition: list[dict] = Field(default_factory=list)
    subtitle: Optional[str] = None
    summary: Optional[str] = None
    origin: str = "chat"
    work_run_id: Optional[str] = None
    requested_by: Optional[str] = None
    data_sources: list[dict] = Field(default_factory=list)
    subject_ref: dict = Field(default_factory=dict)
    publicar: bool = True


class CompartilharIn(BaseModel):
    company_id: str
    artifact_id: str
    version_id: Optional[str] = None
    dias: int = 30
    audiencia: Optional[str] = None
    max_views: Optional[int] = None
    white_label: bool = True
    user_id: Optional[str] = None


@router.get("")
async def listar(company_id: str, x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    return {"ok": True, "artifacts": ArtifactService(get_supabase_client()).listar(company_id)}


@router.post("")
async def criar(payload: CriarIn, x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    svc = ArtifactService(get_supabase_client())

    from app.services.artifacts.templates import POR_CHAVE
    tpl = POR_CHAVE.get(payload.template_key)
    if not tpl:
        raise HTTPException(404, f"template desconhecido: {payload.template_key}")

    try:
        r = svc.criar(
            company_id=payload.company_id, title=payload.title,
            template_key=payload.template_key, payload=payload.payload,
            composition=payload.composition or tpl.composition,
            subtitle=payload.subtitle, summary=payload.summary,
            origin=payload.origin, work_run_id=payload.work_run_id,
            requested_by=payload.requested_by, data_sources=payload.data_sources,
            subject_ref=payload.subject_ref)
        render = svc.renderizar(company_id=payload.company_id,
                                version_id=r["version"]["id"])
        publicado = None
        if payload.publicar:
            publicado = svc.publicar(company_id=payload.company_id,
                                     version_id=r["version"]["id"],
                                     user_id=payload.requested_by)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("[artifact] criacao falhou")
        raise HTTPException(500, f"falha ao gerar: {type(exc).__name__}") from exc

    return {
        "ok": True,
        "artifact_id": r["artifact"]["id"],
        "version_id": r["version"]["id"],
        "publicado": bool(publicado),
        "marca_padrao": (r["brand"] or {}).get("is_fallback", False),
        "diagnostico": render["diagnostico"],
        "bytes_html": len(render["html"].encode()),
    }


@router.get("/{artifact_id}/html")
async def html_da_versao(artifact_id: str, company_id: str,
                         x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    db = get_supabase_client().client
    v = (db.table("artifact_versions").select("id")
         .eq("artifact_id", artifact_id).eq("company_id", company_id)
         .order("version", desc=True).limit(1).execute()).data
    if not v:
        raise HTTPException(404, "artefato sem versao")
    r = (db.table("artifact_renders").select("inline_content")
         .eq("artifact_version_id", v[0]["id"]).eq("format", "html")
         .maybe_single().execute()).data
    if not r or not r.get("inline_content"):
        raise HTTPException(404, "render indisponivel")
    return {"ok": True, "html": r["inline_content"]}


@router.post("/share")
async def compartilhar(payload: CompartilharIn,
                       x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    try:
        s = ArtifactService(get_supabase_client()).compartilhar(
            company_id=payload.company_id, artifact_id=payload.artifact_id,
            version_id=payload.version_id, dias=payload.dias,
            audiencia=payload.audiencia, max_views=payload.max_views,
            white_label=payload.white_label, user_id=payload.user_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    base = (os.getenv("PUBLIC_APP_URL") or os.getenv("NEXT_PUBLIC_APP_URL") or "").rstrip("/")
    return {"ok": True, "token": s["token"], "expires_at": s["expires_at"],
            "url": f"{base}/r/{s['token']}" if base else None}


@router.get("/shared/{token}")
async def abrir(token: str, x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    r = ArtifactService(get_supabase_client()).abrir_compartilhado(token)
    if not r:
        # Mesmo vazio para todos os motivos — ver docstring do módulo.
        raise HTTPException(404, "indisponivel")
    return {"ok": True, **r}
