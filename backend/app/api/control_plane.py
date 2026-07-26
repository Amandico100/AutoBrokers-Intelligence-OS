"""Control Plane — autoridade administrativa. SPEC-061 §5, §7, §8.

Por que a decisão mora AQUI e não no Next
-----------------------------------------
A matriz de papéis é uma autoridade. Duas cópias dela — uma em Python, outra em
TypeScript — divergem na primeira permission nova: alguém acrescenta a tela, o
backend passa a cobrar `releases.rollout`, o front não conhece a chave, e o
operador vê um botão que devolve 403. Ou pior, o inverso.

Então há **um** lugar que decide, e o BFF do Next pergunta a ele.

O custo é uma chamada interna por sessão administrativa — não por requisição:
o BFF guarda o resultado enquanto a sessão vive. O ganho é não ter como as duas
respostas discordarem.

O que este módulo NÃO faz
-------------------------
Não executa comando, não lê domínio, não compõe read model. Ele responde duas
perguntas e só: *quem é esta pessoa* e *o que ela pode*. Executar é o Command
Gateway; ler é o BFF.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/control-plane", tags=["Control Plane"])


def _autorizar(chave: Optional[str]) -> None:
    """Só o BFF fala com este router. Chave interna, nunca sessão de usuário."""
    import os

    esperada = (os.getenv("BACKEND_INTERNAL_API_KEY")
                or os.getenv("ADMIN_API_KEY") or "").strip()
    if not esperada or (chave or "").strip() != esperada:
        raise HTTPException(401, "chave interna inválida")


def _db():
    from app.core.database import get_supabase_client

    return get_supabase_client()


# ---------------------------------------------------------------------------
# Autoridade
# ---------------------------------------------------------------------------


class AutoridadeIn(BaseModel):
    user_id: str
    # §8.2 — quem já era `master` continua operando enquanto os papéis novos
    # não são atribuídos. Sem isto, aplicar a SPEC-061 deixaria o Founder de
    # fora do próprio Admin no primeiro deploy.
    papel_legado: Optional[str] = None


@router.post("/authority")
async def autoridade(payload: AutoridadeIn,
                     x_internal_key: Optional[str] = Header(None)):
    """Papéis, permissions e o menu que a pessoa pode ver."""
    _autorizar(x_internal_key)
    from app.services.control_plane.rbac import (PAPEIS,
                                                 AutoridadeAdministrativa)

    servico = AutoridadeAdministrativa(_db())
    papeis = servico.papeis(payload.user_id, papel_legado=payload.papel_legado)
    permissions = sorted(servico.menu(payload.user_id,
                                      papel_legado=payload.papel_legado))
    return {
        "ok": True,
        "user_id": payload.user_id,
        "papeis": papeis,
        "papeis_legiveis": [PAPEIS[p]["nome"] for p in papeis if p in PAPEIS],
        "permissions": permissions,
        # Sem papel ativo, o Admin não abre. É o fail-closed do §8.4 chegando
        # até a tela: menu vazio é mais honesto que menu cheio de 403.
        "tem_acesso": bool(papeis),
    }


class PodeIn(BaseModel):
    user_id: str
    permission_key: str
    papel_legado: Optional[str] = None


@router.post("/can")
async def pode(payload: PodeIn, x_internal_key: Optional[str] = Header(None)):
    """A decisão para UMA ação. É o que o Command Gateway consulta."""
    _autorizar(x_internal_key)
    from app.services.control_plane.rbac import AutoridadeAdministrativa

    d = AutoridadeAdministrativa(_db()).pode(
        payload.user_id, payload.permission_key,
        papel_legado=payload.papel_legado)
    return {"ok": True, "permitido": d.permitido, "motivo": d.motivo,
            "risco": d.risco, "exige_step_up": d.exige_step_up,
            "origem": d.origem, "papeis": d.papeis}


@router.get("/roles")
async def papeis_disponiveis(x_internal_key: Optional[str] = Header(None)):
    """O catálogo de papéis, para a tela de concessão."""
    _autorizar(x_internal_key)
    from app.services.control_plane.rbac import PAPEIS

    return {"ok": True, "papeis": [
        {"role_key": k, "nome": v["nome"], "descricao": v["descricao"],
         "quantidade_de_permissions": len(v["permissions"])}
        for k, v in PAPEIS.items()]}


# ---------------------------------------------------------------------------
# Trilha de auditoria — §9.3
# ---------------------------------------------------------------------------


class AuditoriaIn(BaseModel):
    actor_user_id: str
    action_key: str
    target_type: str
    result_status: str
    permission_key: Optional[str] = None
    target_id: Optional[str] = None
    company_id: Optional[str] = None
    reason: Optional[str] = None
    before: Optional[dict] = None
    after: Optional[dict] = None
    metadata: Optional[dict] = None
    support_session_id: Optional[str] = None
    work_run_id: Optional[str] = None
    correlation_id: Optional[str] = None
    result_code: Optional[str] = None


@router.post("/audit")
async def registrar_auditoria(payload: AuditoriaIn,
                              x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.control_plane.audit import TrilhaAdministrativa

    r = TrilhaAdministrativa(_db()).registrar(
        actor_user_id=payload.actor_user_id, action_key=payload.action_key,
        target_type=payload.target_type, result_status=payload.result_status,
        permission_key=payload.permission_key, target_id=payload.target_id,
        company_id=payload.company_id, reason=payload.reason,
        antes=payload.before, depois=payload.after,
        metadata=payload.metadata, support_session_id=payload.support_session_id,
        work_run_id=payload.work_run_id, correlation_id=payload.correlation_id,
        result_code=payload.result_code)
    if not r.get("ok"):
        raise HTTPException(400, str(r.get("erro") or "não foi possível registrar"))
    return r


@router.get("/audit")
async def listar_auditoria(limite: int = 100, company_id: Optional[str] = None,
                           actor_user_id: Optional[str] = None,
                           risco: Optional[str] = None,
                           x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.control_plane.audit import TrilhaAdministrativa

    return {"ok": True, "eventos": TrilhaAdministrativa(_db()).listar(
        limite=min(int(limite), 300), company_id=company_id,
        actor_user_id=actor_user_id, risco=risco)}


# ---------------------------------------------------------------------------
# Concessão de papel — §9.1
# ---------------------------------------------------------------------------


class ConcederIn(BaseModel):
    user_id: str
    role_key: str
    granted_by_user_id: str
    reason: Optional[str] = None
    expira_em_dias: Optional[int] = None


@router.post("/roles/grant")
async def conceder_papel(payload: ConcederIn,
                         x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.control_plane.rbac import ConcessaoDePapel

    r = ConcessaoDePapel(_db()).conceder(
        user_id=payload.user_id, role_key=payload.role_key,
        granted_by_user_id=payload.granted_by_user_id,
        reason=payload.reason, expira_em_dias=payload.expira_em_dias)
    if not r.get("ok"):
        raise HTTPException(400, str(r.get("erro") or "não foi possível conceder"))
    return r


class RevogarIn(BaseModel):
    user_id: str
    role_key: str
    revoked_by_user_id: str
    reason: Optional[str] = None


@router.post("/roles/revoke")
async def revogar_papel(payload: RevogarIn,
                        x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.control_plane.rbac import ConcessaoDePapel

    r = ConcessaoDePapel(_db()).revogar(
        user_id=payload.user_id, role_key=payload.role_key,
        revoked_by_user_id=payload.revoked_by_user_id, reason=payload.reason)
    if not r.get("ok"):
        raise HTTPException(400, str(r.get("erro") or "não foi possível revogar"))
    return r


# ---------------------------------------------------------------------------
# Admin Inbox — §13
# ---------------------------------------------------------------------------


class CaixaIn(BaseModel):
    admin_user_id: str
    permissions: list[str]
    pode_tudo: bool = False
    limite: int = 50


@router.post("/inbox")
async def caixa(payload: CaixaIn, x_internal_key: Optional[str] = Header(None)):
    """A caixa priorizada. As permissions vêm do BFF, que já as resolveu.

    Reenviar a lista em vez de reconsultar evita duas leituras da mesma
    autoridade na mesma requisição — e mantém uma resposta só como verdade.
    """
    _autorizar(x_internal_key)
    from app.services.control_plane.inbox import CaixaDeEntrada
    from app.services.control_plane.rbac import PERMISSIONS

    permissions = set(payload.permissions or [])
    if payload.pode_tudo:
        # O dono da plataforma. Expandir aqui, e não mandar 51 chaves pela
        # rede, mantém a matriz num lugar só.
        permissions = set(PERMISSIONS)

    return CaixaDeEntrada(_db()).montar(
        admin_user_id=payload.admin_user_id,
        permissions=permissions,
        limite=min(int(payload.limite), 200))


class MarcarIn(BaseModel):
    admin_user_id: str
    fonte: str
    chave: str
    estado: str
    adiar_ate: Optional[str] = None
    nota: Optional[str] = None


@router.post("/inbox/mark")
async def marcar_item(payload: MarcarIn,
                      x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.control_plane.inbox import CaixaDeEntrada

    r = CaixaDeEntrada(_db()).marcar(
        admin_user_id=payload.admin_user_id, fonte=payload.fonte,
        chave=payload.chave, estado=payload.estado,
        adiar_ate=payload.adiar_ate, nota=payload.nota)
    if not r.get("ok"):
        raise HTTPException(400, str(r.get("erro") or "não foi possível marcar"))
    return r


# ---------------------------------------------------------------------------
# Central de Trabalhos e Cockpit — §14, §15
# ---------------------------------------------------------------------------


@router.get("/work-runs")
async def trabalhos(company_id: Optional[str] = None, dias: int = 7,
                    estado: Optional[str] = None, limite: int = 50,
                    x_internal_key: Optional[str] = Header(None)):
    """Agregado primeiro, lista depois — CA-014.

    Uma lista dos últimos 40 responde bem com 5 corretoras e deixa de
    responder qualquer coisa com mil. O agregado continua respondendo.
    """
    _autorizar(x_internal_key)
    from app.services.control_plane.read_models import CentralDeTrabalhos

    central = CentralDeTrabalhos(_db())
    return {"ok": True,
            "resumo": central.resumo(company_id=company_id,
                                     dias=min(int(dias), 90)),
            "lista": central.listar(company_id=company_id, estado=estado,
                                    limite=min(int(limite), 200))}


@router.get("/work-runs/{run_id}")
async def trabalho(run_id: str, company_id: Optional[str] = None,
                   x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.control_plane.read_models import CentralDeTrabalhos

    r = CentralDeTrabalhos(_db()).detalhe(run_id, company_id=company_id)
    if not r.get("ok"):
        raise HTTPException(404, str(r.get("erro") or "não encontrado"))
    return r


@router.get("/cockpit/{company_id}")
async def cockpit(company_id: str, dias: int = 30,
                  x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.control_plane.read_models import CockpitDaCorretora

    r = CockpitDaCorretora(_db()).montar(company_id, dias=min(int(dias), 180))
    if not r.get("ok"):
        raise HTTPException(404, str(r.get("erro") or "não encontrada"))
    return r


@router.get("/roles/bindings")
async def vinculos(user_id: Optional[str] = None, limite: int = 100,
                   x_internal_key: Optional[str] = Header(None)):
    _autorizar(x_internal_key)
    from app.services.control_plane.rbac import ConcessaoDePapel

    return {"ok": True, "vinculos": ConcessaoDePapel(_db()).listar(
        user_id=user_id, limite=min(int(limite), 300))}
