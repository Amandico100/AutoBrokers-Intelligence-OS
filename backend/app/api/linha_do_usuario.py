"""SPEC-131-0-B2 · L1 — a API INTERNA da linha do usuário (o WhatsApp pessoal do corretor conectado ao AutoBrokers).

Endpoints INTERNOS (chave Next↔backend `X-AutoBrokers-Internal-Key`, o padrão de `contas_da_corretora.py`). O BFF
(`app/api/dashboard/meu-perfil/linha/**`) tira `company_id` e `user_id` SEMPRE da SESSÃO — nunca do cliente — e nas
ações manda também `por_user_id` (quem clicou), que TEM de ser o próprio `user_id`: a linha é de UMA pessoa.

    POST /api/linha-do-usuario/conectar     {company_id, user_id, por_user_id} → {tentativa_id, qr, estado, motivo}
    GET  /api/linha-do-usuario/estado       ?company_id&user_id → {estado, numero_mascarado, desde, motivo}
    GET  /api/linha-do-usuario/qr           ?company_id&user_id → {qr, estado, tentativa_id, motivo}
    POST /api/linha-do-usuario/desconectar  {company_id, user_id, por_user_id} → {ok, estado}

Estados: nao_conectada · aguardando_qr · conectada · desconectada · limite · desligada. Quando a chave
`LINHA_DO_USUARIO_LIGADA` não liga ESTA pessoa (ausente, ou ela fora da lista de user_id — `estado.ligada_para`) ou
ela não é membro ativo da corretora, o GET responde 200 `{estado:"desligada"}`; o teto cheio volta no CORPO
(`{estado:"limite"}`; no POST /conectar com 409). ⛔ Nenhum telefone em claro sai daqui; o QR só para quem pediu.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.database import get_supabase_client
from app.services.linha_do_usuario import estado as E
from app.services.linha_do_usuario import pareamento as P

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/linha-do-usuario", tags=["Linha do usuário"])


def _require_internal_key(provided: Optional[str]) -> None:
    expected = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    if not expected or provided != expected:
        raise HTTPException(status_code=401, detail="chave interna invalida")


def _db():
    return get_supabase_client().client


def _falhou(o_que: str, exc: Exception) -> HTTPException:
    # ⛔ nunca o corpo da exceção: pode trazer o telefone, o QR ou dado da conexão
    logger.error("[LINHA] %s falhou (%s)", o_que, type(exc).__name__)
    return HTTPException(status_code=500, detail="não consegui fazer isso agora — tente de novo em instantes")


async def _corpo_da_propria_pessoa(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = None
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="corpo inválido")
    if not body.get("company_id") or not body.get("user_id"):
        raise HTTPException(status_code=400, detail="company_id e user_id obrigatorios")
    if str(body.get("por_user_id") or "").strip().lower() != str(body.get("user_id") or "").strip().lower():
        raise HTTPException(status_code=422, detail="Só a própria pessoa conecta ou desconecta o WhatsApp dela.")
    return body


@router.post("/conectar")
async def conectar(request: Request,
                   x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    b = await _corpo_da_propria_pessoa(request)
    try:
        r = await P.conectar(_db(), b["company_id"], b["user_id"])
    except E.Recusa as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("conectar a linha", e)
    if r.get("estado") == "limite":
        return JSONResponse(status_code=409, content=r)
    return r


@router.get("/estado")
async def ler_estado(company_id: str, user_id: str,
                     x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    try:
        return await P.estado(_db(), company_id, user_id)
    except E.Recusa as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("ler o estado da linha", e)


@router.get("/qr")
async def ler_qr(company_id: str, user_id: str,
                 x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    try:
        return await P.qr(_db(), company_id, user_id)
    except E.Recusa as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("ler o QR da linha", e)


@router.post("/desconectar")
async def desconectar(request: Request,
                      x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    b = await _corpo_da_propria_pessoa(request)
    try:
        return await P.desconectar(_db(), b["company_id"], b["user_id"])
    except E.Recusa as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("desconectar a linha", e)
