"""SPEC-131-0 F2 — "Quem é quem no sistema de gestão": que código de produtor é de qual pessoa, e a regra do dono.

Endpoints INTERNOS (chave Next↔backend `X-AutoBrokers-Internal-Key`, o mesmo padrão de `app/api/portal.py`). O
`company_id` vem do BFF, que o tira da SESSÃO (nunca do cliente); escrever passa pelo porteiro lá. Aqui, toda leitura
e escrita vai por `app.services.sistema_de_gestao.dono`, que filtra `company_id` no código (CLAUDE.md §7).

⛔ Nada aqui escreve no sistema de gestão (só GET). ⛔ Nenhum nome de cliente sai daqui.
Registrado no `main.py` pela costura (F5); `tests/test_spec1310_o_fio.py` prova que monta e exige a chave.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

from app.core.database import get_supabase_client
from app.services.sistema_de_gestao import dono as DONO

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/contas-da-corretora", tags=["Contas da corretora"])


def _require_internal_key(provided: Optional[str]) -> None:
    expected = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    if not expected or provided != expected:
        raise HTTPException(status_code=401, detail="chave interna invalida")


def _db():
    return get_supabase_client().client


def _falhou(o_que: str, exc: Exception) -> HTTPException:
    # ⛔ nunca o corpo da exceção: pode trazer a linha ou dado da conexão
    logger.error("[CONTAS] %s falhou (%s)", o_que, type(exc).__name__)
    return HTTPException(status_code=500, detail="não consegui fazer isso agora — tente de novo em instantes")


async def _corpo(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = None
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="corpo inválido")
    if not body.get("company_id"):
        raise HTTPException(status_code=400, detail="company_id obrigatorio")
    return body


# ------------------------------------------------------------------------------------------------- vínculos
@router.get("/sistema-de-gestao/vinculos")
async def vinculos(company_id: str, sistema: Optional[str] = None,
                   x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    try:
        return {"vinculos": DONO.listar_vinculos(_db(), company_id, sistema or None),
                "membros": DONO.membros_ativos(_db(), company_id)}
    except DONO.Recusa as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("listar vínculos", e)


@router.post("/sistema-de-gestao/vincular")
async def vincular(request: Request,
                   x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    b = await _corpo(request)
    try:
        r = DONO.vincular(_db(), str(b["company_id"]), user_id=b.get("user_id"), sistema=b.get("sistema") or "infocap",
                          codfil=b.get("codfil", 1), codigo_produtor=b.get("codigo_produtor"),
                          nome_produtor=b.get("nome_produtor"), papel_cru=b.get("papel_cru"),
                          por_user_id=b.get("por_user_id"))
    except DONO.Recusa as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("vincular", e)
    return {"ok": True, **r}


@router.delete("/sistema-de-gestao/vincular")
async def desvincular(company_id: str, id: str,  # noqa: A002 — o nome do parâmetro é o da query
                      x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    try:
        n = DONO.desvincular(_db(), company_id, id)
    except DONO.Recusa as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("desvincular", e)
    if n == 0:
        raise HTTPException(status_code=404, detail="vínculo não encontrado nesta corretora")
    return {"ok": True, "removidos": n}


@router.get("/sistema-de-gestao/sugestoes")
async def sugestoes(company_id: str,
                    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    try:
        return await DONO.sugerir_vinculos(_db(), company_id)
    except DONO.Recusa as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("sugerir vínculos", e)


# ------------------------------------------------------------------------------------------------- a regra do dono
def _retrato_da_regra(company_id: str, sistema: str) -> dict:
    regra = DONO.regra_de_dono(_db(), company_id, sistema)
    padrao = DONO.regra_padrao_do_sistema(sistema)
    return {"regra": regra.como_dict() if regra else None,
            "padrao": padrao.como_dict() if padrao else None}


@router.get("/sistema-de-gestao/regra")
async def regra(company_id: str, sistema: str = "infocap",
                x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    try:
        return _retrato_da_regra(company_id, sistema)
    except DONO.Recusa as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("ler a regra", e)


@router.put("/sistema-de-gestao/regra")
async def gravar_regra(request: Request,
                       x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    """`regra: null` = voltar ao padrão do sistema. Senão a FORMA é validada (`dono.validar_regra`) antes de gravar."""
    _require_internal_key(x_key)
    b = await _corpo(request)
    sistema = str(b.get("sistema") or "infocap")
    try:
        if b.get("regra") is None:
            DONO.apagar_regra(_db(), str(b["company_id"]), sistema)
        else:
            DONO.gravar_regra(_db(), str(b["company_id"]), sistema, b.get("regra"), b.get("por_user_id"))
        return {"ok": True, **_retrato_da_regra(str(b["company_id"]), sistema)}
    except DONO.Recusa as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("gravar a regra", e)


@router.post("/sistema-de-gestao/medir")
async def medir(request: Request,
                x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    """A régua: a regra da corretora nas renovações dos próximos `dias` (padrão 30). Só contagens."""
    _require_internal_key(x_key)
    b = await _corpo(request)
    try:
        dias = int(b.get("dias") or 30)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="dias inválido")
    try:
        return await DONO.medir_regra(_db(), str(b["company_id"]), dias=dias)
    except DONO.Recusa as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("medir a regra", e)


# ------------------------------------------------------------------------------------------------- o MEU perfil
# SPEC-131-B G3 — "Meu perfil" (o WhatsApp de trabalho e a ausência) e a SITUAÇÃO de cada pessoa em Equipe. O BFF manda
# `company_id` e `user_id`/`por_user_id` da SESSÃO; o serviço (`perfil_do_membro`) filtra `company_id` e confere quem
# pode. ⛔ Nenhum número de telefone vai para log; o número só volta para a própria pessoa (GET /perfil).
def _perfil():
    from app.services import perfil_do_membro as PERFIL

    return PERFIL


@router.get("/perfil")
async def ler_perfil(company_id: str, user_id: str,
                     x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    P = _perfil()
    try:
        return P.ler_perfil(_db(), company_id, user_id)
    except P.Recusa as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("ler o perfil", e)


@router.put("/perfil/whatsapp-de-trabalho")
async def gravar_whatsapp_de_trabalho(request: Request,
                                      x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    """`{company_id, user_id, por_user_id, numero, confirmo: true}` grava · `numero: null` apaga. Só a própria pessoa."""
    _require_internal_key(x_key)
    b = await _corpo(request)
    P = _perfil()
    try:
        if b.get("numero") is None:
            return {"ok": True, **P.remover_whatsapp_trabalho(_db(), b["company_id"], b.get("user_id"),
                                                              por_user_id=b.get("por_user_id"))}
        return {"ok": True, **P.gravar_whatsapp_trabalho(_db(), b["company_id"], b.get("user_id"),
                                                         numero=b.get("numero"), confirmo=b.get("confirmo"),
                                                         por_user_id=b.get("por_user_id"))}
    except P.Recusa as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        if "ck_company_members_whatsapp" in str(e):
            # RT-P3/J-P3: a regra do Python É a do CHECK; se um dia divergirem, a pessoa lê a correção, nunca um 500.
            # ⛔ só o TIPO vai ao log (a mensagem do banco pode trazer o número)
            logger.warning("[CONTAS] o banco recusou o WhatsApp de trabalho (%s)", type(e).__name__)
            raise HTTPException(status_code=422, detail="Use um número do Brasil com DDD: celular com 9 dígitos "
                                                        "(começando com 9) ou fixo com 8 (começando de 2 a 5).")
        raise _falhou("gravar o WhatsApp de trabalho", e)


@router.post("/perfil/whatsapp-de-trabalho/codigo")
async def gerar_codigo_do_atalho(request: Request,
                                 x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    """SPEC-132-C C1 (D-132C-02) — `{company_id, user_id, por_user_id}` (da SESSÃO) → o código de 6 dígitos que a
    PRÓPRIA pessoa manda do celular dela ao número do AutoBrokers ("ATIVAR 123456"). Só o hash fica no banco.
    ⛔ o código não vai para log; volta só para quem pediu."""
    _require_internal_key(x_key)
    b = await _corpo(request)
    from app.services.atalho import verificacao as V

    if str(b.get("por_user_id") or "").strip().lower() != str(b.get("user_id") or "").strip().lower():
        raise HTTPException(status_code=422, detail="Só a própria pessoa pede o código do WhatsApp dela.")
    try:
        return {"ok": True, **V.gerar_codigo(_db(), company_id=b["company_id"], user_id=b.get("user_id"))}
    except V.Recusa as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("gerar o código do WhatsApp", e)


@router.post("/perfil/ausencias")
async def criar_ausencia(request: Request,
                         x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    """`{company_id, user_id, substituto_user_id, de, ate, por_user_id}` — OUTRA pessoa ativa da MESMA corretora."""
    _require_internal_key(x_key)
    b = await _corpo(request)
    P = _perfil()
    try:
        r = P.criar_ausencia(_db(), b["company_id"], user_id=b.get("user_id"),
                             substituto_user_id=b.get("substituto_user_id"), de=b.get("de"), ate=b.get("ate"),
                             por_user_id=b.get("por_user_id"))
    except P.Recusa as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("marcar a ausência", e)
    return {"ok": True, "ausencia": r}


@router.delete("/perfil/ausencias")
async def apagar_ausencia(company_id: str, id: str, por_user_id: str,  # noqa: A002 — o nome é o da query
                          x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    P = _perfil()
    try:
        return {"ok": True, **P.apagar_ausencia(_db(), company_id, ausencia_id=id, por_user_id=por_user_id)}
    except P.Recusa as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("apagar a ausência", e)


@router.get("/equipe/situacao")
async def situacao_da_equipe(company_id: str,
                             x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    """A coluna SITUAÇÃO de Equipe: Agger · WhatsApp de trabalho confirmado (sim/não) · ausência ativa."""
    _require_internal_key(x_key)
    P = _perfil()
    try:
        return P.situacao_da_equipe(_db(), company_id)
    except P.Recusa as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _falhou("ler a situação da equipe", e)
