"""Espelho dos acionamentos ativos (SPEC-017 — página Conversas do dashboard).

GET /api/dispatch/active?company_id= — sessões de dispatch ativas da corretora
(URA/fase humana com a seguradora), somente leitura. Chave interna Next↔Backend.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException

from app.services.dispatch_router import list_active_dispatches, load_active_dispatch

router = APIRouter()


def _require_internal_key(provided: Optional[str]) -> None:
    expected = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    if not expected or not provided or provided != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


@router.get("/api/dispatch/active")
async def dispatch_active(
    company_id: str,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    sessions = await list_active_dispatches(str(company_id))
    return {"ok": True, "dispatches": sessions}


@router.get("/api/dispatch/dossier")
async def dispatch_dossier(
    company_id: str,
    insurer_phone: str,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    """Dossiê de handoff da sessão ATIVA (SPEC-046 — Ficha do Atendimento).

    O MESMO texto que build_handoff_dossier entrega à equipe no WhatsApp,
    reconstruído da sessão viva no Redis — nada paralelo. Sessão expirada
    (TTL) → dossier ausente; a ficha mostra o espelho da conversa no lugar."""
    _require_internal_key(x_autobrokers_internal_key)
    session = await load_active_dispatch(str(company_id), str(insurer_phone))
    if not session:
        return {"ok": True, "dossier": None}
    from app.services.insurer_dispatch_service import build_handoff_dossier

    return {"ok": True, "dossier": build_handoff_dossier(session)}
