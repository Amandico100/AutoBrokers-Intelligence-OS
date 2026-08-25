"""A saudação do religamento — SPEC-093, BLOCO D. A porta do Next↔Backend.

```
GET  /api/saudacao-religamento/previa?company_id=   a contagem e a lista
POST /api/saudacao-religamento/enviar               só com `confirmado=true`
```

🔴 **A prévia é `GET` e o envio é `POST`, e isso não é decoração.** 📊 O robô
teve **4 conversas de WhatsApp em toda a história do produto**: a primeira vez
que o envio rodar será a maior coisa que ele já mandou sozinho. Um verbo que um
prefetch de navegador pode disparar não pode ser o que manda mensagem.

⛔ E o `confirmado` é do CORPO, nunca da query: link com `?confirmado=true` é
compartilhável, colável e clicável por engano.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Header, HTTPException

from app.services.saudacao_do_religamento import enviar_saudacoes, previa

router = APIRouter()


def _require_internal_key(provided: Optional[str]) -> None:
    expected = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    if not expected or not provided or provided != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


@router.get("/api/saudacao-religamento/previa")
async def saudacao_previa(
    company_id: str,
    x_autobrokers_internal_key: Optional[str] = Header(
        default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    """Quem receberia a saudação, e quantos. ⛔ Não manda nada.

    ⛔ `conversas[].quem` sai mascarado — primeiro nome e os quatro últimos
    dígitos (`CLAUDE.md` §13.3: presença, nunca conteúdo).
    """
    _require_internal_key(x_autobrokers_internal_key)
    return {"ok": True, **(await previa(str(company_id)))}


@router.post("/api/saudacao-religamento/enviar")
async def saudacao_enviar(
    payload: Dict[str, Any] = Body(...),
    x_autobrokers_internal_key: Optional[str] = Header(
        default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    """Envia a saudação pelo caminho FRIO — governada por `platform_outbound`.

    🔴 No **primeiro** religamento de cada corretora, `confirmado=false` devolve
    a prévia e **não envia nada**. Uma tela é o guarda mais barato que existe.
    """
    _require_internal_key(x_autobrokers_internal_key)
    company_id = str(payload.get("company_id") or "").strip()
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id_obrigatorio")
    # ⛔ `confirmado` é do CORPO, e só `True` literal vale. `"false"` é uma
    # string verdadeira em Python — e é assim que um formulário manda.
    confirmado = payload.get("confirmado") is True
    return await enviar_saudacoes(company_id, confirmado=confirmado)
