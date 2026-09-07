# -*- coding: utf-8 -*-
"""A porta pela qual o canário da SPEC-EXTRA-001 roda ONDE o produto roda.

Por que existe
==============
📊 07/09/2026: toda mensagem fria passa pelo governador de vazão, e sem Redis ele
recusa (falha fechada). A máquina do orquestrador não tem Redis; o contêiner do
smith-api tem. Sem esta rota, o canário vivo dependeria de alguém abrir o
console do EasyPanel e rodar um script à mão — e "alguém" é o Founder.

O que ela NUNCA faz
===================
- não aceita destino, allowlist ou tenant no corpo: o tenant é fixo (Resulta),
  o destino vem de `CANARIO_TESTE_B` e a allowlist de `BILLING_CANARIO_ALLOWLIST`,
  os dois no AMBIENTE do contêiner. Quem tem a chave interna não escolhe para
  quem o canário manda mensagem;
- não relaxa controle nenhum: governador, porta única, reserva e allowlist
  (remetente E destinatário) valem como para qualquer corretora;
- não roda sem a chave interna (`require_internal_key`, SPEC-098 U4: chave
  ausente ou errada = 401, uma frase só).
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import require_internal_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/canario", tags=["Admin Canário"])


@router.get("/extra001/plano", dependencies=[Depends(require_internal_key)])
async def plano_extra001():
    """O que o canário faria, com o censo. Não toca em nada."""
    from app.services.canario_extra001 import RESULTA, plano

    try:
        return {"ok": True, **plano(RESULTA)}
    except Exception as exc:  # noqa: BLE001
        logger.error("[CANARIO EXTRA-001] plano falhou: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail=f"plano falhou: {type(exc).__name__}")


@router.post("/extra001", dependencies=[Depends(require_internal_key)])
async def rodar_extra001(
    limpar: bool = Query(True, description="apaga o que o canário criou (por id + company + marca)"),
    esperar_retorno_s: int = Query(0, ge=0, le=600,
                                   description="segundos para esperar uma resposta REAL de TESTE-B pelo webhook"),
):
    """Executa Q1–Q6 dentro do serviço implantado. Só com a allowlist no ambiente."""
    from app.services.canario_extra001 import RESULTA, rodar

    if not os.getenv("BILLING_CANARIO_ALLOWLIST", "").strip() or not os.getenv("CANARIO_TESTE_B", "").strip():
        raise HTTPException(
            status_code=409,
            detail="canário desarmado: faltam BILLING_CANARIO_ALLOWLIST e/ou CANARIO_TESTE_B no ambiente")
    try:
        return {"ok": True, **(await rodar(RESULTA, limpar=limpar, esperar_retorno_s=esperar_retorno_s))}
    except Exception as exc:  # noqa: BLE001
        logger.error("[CANARIO EXTRA-001] rodar falhou: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail=f"canário falhou: {type(exc).__name__}")
