"""API de identidade da corretora. SPEC-057 §Bloco B.

A captura mora no backend, não no Next, por três razões:

1. É egresso para a internet, e o `egress_guard` da SPEC-054 vive aqui.
2. Decodificar PNG e derivar paleta é trabalho de CPU que não pertence a uma
   rota de renderização.
3. É uma capability do Registry — precisa passar pelo mesmo caminho de poder
   que qualquer outra ação do sistema.

O Next chama esta rota com a chave interna; a autorização por tenant já foi
feita lá, e aqui se confere de novo. Confiar que o chamador já validou é como
se perde isolamento entre corretoras.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.services.brand.capture import BrandCaptureService
from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/brand", tags=["Brand Identity"])

CAMPOS_EDITAVEIS = {
    "website_url", "instagram_url", "linkedin_url", "google_business_url",
    "facebook_url", "display_name", "legal_name", "tagline", "mission",
    "about_md", "services", "differentiators", "service_area", "founded_year",
    "susep_code", "contact", "insurers", "palette", "typography",
    "visual_style", "tone", "logo_asset_id", "is_published",
}


def _autorizar(chave: Optional[str]) -> None:
    esperada = (os.getenv("BACKEND_INTERNAL_API_KEY")
                or os.getenv("ADMIN_API_KEY") or "").strip()
    if not esperada:
        # Sem chave configurada, nega. A ausência de configuração não pode
        # significar "aberto" — foi a decisão da SPEC-054 §9.1 para egresso e
        # vale igual para ingresso.
        raise HTTPException(503, "chave interna nao configurada")
    if (chave or "").strip() != esperada:
        raise HTTPException(401, "nao autorizado")


class CapturaIn(BaseModel):
    company_id: str
    force: bool = False
    run_id: Optional[str] = None


class EdicaoIn(BaseModel):
    company_id: str
    values: dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None


@router.get("/profile")
async def obter(company_id: str, x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    db = get_supabase_client()
    svc = BrandCaptureService(db)

    perfil = svc.obter_ou_criar(company_id)
    pid = perfil.get("id")

    proc = (db.client.table("brand_field_provenance")
            .select("field_path, source_kind, source_detail, confidence, human_edited, captured_at")
            .eq("brand_profile_id", pid).execute()).data or []
    fontes = (db.client.table("brand_sources")
              .select("kind, url, status, http_status, fetched_at, duration_ms, error")
              .eq("brand_profile_id", pid).order("created_at", desc=True)
              .limit(12).execute()).data or []
    assets = (db.client.table("brand_assets")
              .select("id, kind, storage_ref, width, height, has_transparency, "
                      "ink_colors, source_url, confidence")
              .eq("company_id", company_id).eq("is_current", True).execute()).data or []

    return {
        "ok": True,
        "profile": perfil,
        "provenance": {p["field_path"]: p for p in proc},
        "sources": fontes,
        "assets": assets,
    }


@router.post("/capture")
async def capturar(payload: CapturaIn, x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    svc = BrandCaptureService(get_supabase_client())
    try:
        r = await svc.capturar(payload.company_id, run_id=payload.run_id,
                               forcar=payload.force)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[brand] captura falhou")
        raise HTTPException(500, f"falha na captura: {type(exc).__name__}") from exc

    return {
        "ok": r.status in ("captured", "partial"),
        "status": r.status,
        "erro": r.erro,
        "avisos": r.avisos,
        "completeness": r.completeness,
        "campos_propostos": sorted(r.campos.keys()),
        "assets": r.assets,
        "fontes": [{"kind": f["kind"], "status": f["status"],
                    "http_status": f.get("http_status")} for f in r.sources],
    }


@router.patch("/profile")
async def editar(payload: EdicaoIn, x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    valores = {k: v for k, v in (payload.values or {}).items() if k in CAMPOS_EDITAVEIS}
    if not valores:
        raise HTTPException(400, "nenhum campo editavel no corpo")

    svc = BrandCaptureService(get_supabase_client())
    perfil = svc.editar(payload.company_id, valores, payload.user_id)
    return {"ok": True, "profile": perfil, "campos": sorted(valores.keys())}


@router.get("/preview")
async def previa(company_id: str, template: str = "executive.panorama",
                 x_internal_key: Optional[str] = Header(None)):
    """Prévia de uma peça com a marca atual — o que o corretor vê antes de gerar.

    Vale mais do que um quadradinho de cor na tela: mostra a marca aplicada no
    lugar onde ela de fato vai ser julgada.
    """
    _autorizar(x_internal_key)
    from app.services.artifacts.render import render_html
    from app.services.artifacts.templates import POR_CHAVE

    svc = BrandCaptureService(get_supabase_client())
    marca = svc.snapshot_para_artefato(company_id)
    tpl = POR_CHAVE.get(template)
    if not tpl:
        raise HTTPException(404, "template desconhecido")

    html, diag = render_html(
        brand=marca, composition=tpl.composition,
        visual_style=marca.get("visual_style") or tpl.visual_style,
        title=f"{tpl.name} · {marca.get('name', '')}")
    return {"ok": True, "html": html, "diagnostico": diag,
            "marca_padrao": marca.get("is_fallback", False)}
