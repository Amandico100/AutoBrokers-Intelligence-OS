"""API da Auxiliary & Routine Factory. SPEC-058 §9 e §12.

Duas superfícies bem diferentes:

* **tenant** — o corretor pede algo e recebe uma proposta. Nunca cria sozinho.
* **plataforma** — o Admin vê o catálogo, as instalações, a saúde e, sobretudo,
  as **oportunidades**: o que as corretoras pediram e o sistema ainda não faz,
  ordenado por quantas pediram.

A segunda é a que muda a forma de decidir roadmap. Hoje um pedido que o sistema
não atende morre na conversa e a priorização vira opinião.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.database import get_supabase_client
from app.services.auxiliaries.factory import AuxiliaryFactory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/factory", tags=["Auxiliary Factory"])


def _autorizar(chave: Optional[str]) -> None:
    esperada = (os.getenv("BACKEND_INTERNAL_API_KEY")
                or os.getenv("ADMIN_API_KEY") or "").strip()
    if not esperada:
        raise HTTPException(503, "chave interna nao configurada")
    if (chave or "").strip() != esperada:
        raise HTTPException(401, "nao autorizado")


class AvaliarIn(BaseModel):
    company_id: str
    texto: str = Field(description="O que o corretor pediu, em linguagem natural")
    user_id: Optional[str] = None
    source: str = "chat"
    agent_role: str = "core"


class LacunaIn(BaseModel):
    gap_type: str
    descricao: str
    company_id: Optional[str] = None
    capability_key: Optional[str] = None
    provider: Optional[str] = None
    request_id: Optional[str] = None


@router.post("/avaliar")
async def avaliar(payload: AvaliarIn, x_internal_key: Optional[str] = Header(None)):
    """Recebe um pedido e devolve o que fazer — sem criar nada.

    Separar avaliar de executar é deliberado: o corretor vê a proposta antes.
    Sistema que cria Auxiliar no meio da conversa produz coisas que ninguém
    pediu e ninguém sabe desligar.
    """
    _autorizar(x_internal_key)
    f = AuxiliaryFactory(get_supabase_client())
    return {"ok": True, **f.avaliar(
        company_id=payload.company_id, texto=payload.texto,
        user_id=payload.user_id, source=payload.source, agent_role=payload.agent_role)}


@router.post("/lacuna")
async def registrar_lacuna(payload: LacunaIn, x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    f = AuxiliaryFactory(get_supabase_client())
    return {"ok": True, **f.registrar_lacuna(
        gap_type=payload.gap_type, descricao=payload.descricao,
        company_id=payload.company_id, capability_key=payload.capability_key,
        provider=payload.provider, request_id=payload.request_id)}


# --------------------------------------------------------------------------
# Plataforma
# --------------------------------------------------------------------------

@router.get("/oportunidades")
async def oportunidades(x_internal_key: Optional[str] = Header(None)):
    """O que as corretoras pediram e ainda não fazemos, por peso.

    É roadmap com evidência em vez de opinião: cada linha carrega quantas vezes
    a mesma lacuna foi encontrada e desde quando.
    """
    _autorizar(x_internal_key)
    db = get_supabase_client()
    f = AuxiliaryFactory(db)
    lacunas = f.lacunas_por_prioridade(60)

    cliente = db.client
    try:
        pedidos = (cliente.table("auxiliary_requests")
                   .select("request_fingerprint, requested_outcome, "
                           "classified_work_pattern, status, created_at")
                   .order("created_at", desc=True).limit(400).execute()).data or []
    except Exception:  # noqa: BLE001
        pedidos = []

    # Agrupa por assinatura: a mesma dor pedida por corretoras diferentes é UMA
    # necessidade com peso, não N pedidos soltos.
    por_assinatura: dict[str, dict] = {}
    for p in pedidos:
        fp = p.get("request_fingerprint")
        if not fp:
            continue
        atual = por_assinatura.setdefault(fp, {
            "exemplo": p.get("requested_outcome"),
            "padrao": p.get("classified_work_pattern"),
            "vezes": 0, "atendidos": 0, "ultimo": p.get("created_at"),
        })
        atual["vezes"] += 1
        if p.get("status") in ("matched", "accepted", "delivered"):
            atual["atendidos"] += 1

    mais_pedidos = sorted(por_assinatura.values(), key=lambda x: x["vezes"], reverse=True)[:30]

    return {
        "ok": True,
        "lacunas": lacunas,
        "mais_pedidos": mais_pedidos,
        "resumo": {
            "lacunas_abertas": len(lacunas),
            "peso_total": sum(int(g.get("frequency_count") or 0) for g in lacunas),
            "pedidos_analisados": len(pedidos),
            "necessidades_distintas": len(por_assinatura),
        },
    }


@router.get("/catalogo")
async def catalogo(x_internal_key: Optional[str] = Header(None)):
    """Catálogo de templates com contagem de instalações e saúde."""
    _autorizar(x_internal_key)
    db = get_supabase_client().client

    templates = (db.table("auxiliary_templates")
                 .select("id, slug, name, category, short_description, status, "
                         "version, execution_mode, is_active")
                 .eq("is_active", True).order("name").execute()).data or []
    instalacoes = (db.table("tenant_auxiliaries")
                   .select("id, company_id, template_id, status, health, "
                           "current_revision, last_run_at").execute()).data or []
    releases = (db.table("auxiliary_template_releases")
                .select("template_id, version, runtime_kind, status, is_default")
                .execute()).data or []

    por_template: dict[str, list] = {}
    for i in instalacoes:
        por_template.setdefault(i.get("template_id"), []).append(i)
    rel_por_template: dict[str, list] = {}
    for r in releases:
        rel_por_template.setdefault(r.get("template_id"), []).append(r)

    saida = []
    for t in templates:
        insts = por_template.get(t["id"], [])
        rels = rel_por_template.get(t["id"], [])
        default = next((r for r in rels if r.get("is_default")), None)
        saida.append({
            **t,
            "instalacoes": len(insts),
            "ativas": sum(1 for i in insts if i.get("status") in ("active", "ativo")),
            "degradadas": sum(1 for i in insts if i.get("health") in ("degraded", "error")),
            "releases": len(rels),
            "runtime_kind": (default or {}).get("runtime_kind"),
            # Template sem release publicada é template que ninguem pode instalar
            # com garantia de imutabilidade — vale destacar.
            "sem_release_publicada": not any(r.get("status") == "published" for r in rels),
        })

    return {"ok": True, "templates": saida,
            "resumo": {
                "templates": len(saida),
                "instalacoes": len(instalacoes),
                "degradadas": sum(x["degradadas"] for x in saida),
                "sem_release": sum(1 for x in saida if x["sem_release_publicada"]),
            }}


@router.get("/instalacoes")
async def instalacoes(company_id: Optional[str] = None,
                      x_internal_key: Optional[str] = Header(None)):
    """Instalações, com a corretora e a saúde de cada uma."""
    _autorizar(x_internal_key)
    db = get_supabase_client().client

    q = (db.table("tenant_auxiliaries")
         .select("id, company_id, template_id, slug, name, status, health, "
                 "health_reason, current_revision, installed_at, last_run_at"))
    if company_id:
        q = q.eq("company_id", company_id)
    linhas = (q.order("installed_at", desc=True).limit(300).execute()).data or []

    empresas = {c["id"]: c.get("company_name")
                for c in ((db.table("companies").select("id, company_name")
                           .execute()).data or [])}
    for l in linhas:
        l["corretora"] = empresas.get(l.get("company_id"))
    return {"ok": True, "instalacoes": linhas}


@router.get("/timeline/{tenant_auxiliary_id}")
async def timeline(tenant_auxiliary_id: str, x_internal_key: Optional[str] = Header(None)):
    """Ciclo de vida de uma instalação, do proposal ao uninstall."""
    _autorizar(x_internal_key)
    db = get_supabase_client().client
    r = (db.table("auxiliary_events")
         .select("event_type, actor_kind, actor_id, detail, created_at")
         .eq("tenant_auxiliary_id", tenant_auxiliary_id)
         .order("created_at", desc=True).limit(200).execute())
    return {"ok": True, "eventos": r.data or []}
