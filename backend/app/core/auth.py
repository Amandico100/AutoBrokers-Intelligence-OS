"""
Authentication Dependencies for FastAPI

Provides authentication and authorization helpers for protected endpoints.
"""

import logging
import os
from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException, Request, status

from .config import settings
from .database import AsyncSupabaseClient, get_async_db

logger = logging.getLogger(__name__)


# =============================================================================
# A CHAVE DO BFF — o canônico (SPEC-098 R7)
# =============================================================================
#
# 🔴 O BURACO QUE ISTO FECHA, MEDIDO EM 06/09/2026 (SPEC-098 §1.3):
#
#     curl …smith-api…/api/sanitization/jobs?company_id=<uuid falso>  → 200
#     curl …smith-api…/api/mcp/servers?company_id=<uuid falso>        → 200
#
# O smith-api é PÚBLICO. Três arquivos (`sanitization.py`, `agent_config.py`,
# `mcp.py`) recebiam `company_id` de fora com ZERO guardas — nem chave interna,
# nem sessão. 📊 `grep -c 'Depends(\|_require_internal_key\|_autorizar'` nos três
# = 0, 0, 0. O comentário de `sanitization.py:46` dizia *"company_id is provided
# by the Next.js proxy"* e **nada verificava que o chamador era o proxy**.
# Comentário não é guarda.
#
# ⚠️ **Por que aqui, e não mais um `_autorizar` local.** 📊 Existem 12 cópias
# desse helper espalhadas por `app/api/`. Elas estão corretas e continuam
# valendo (`P-098-DRENO-CHAVE-INTERNA`); o que CLAUDE.md §5 proíbe é a 13ª cópia
# ao lado do buraco. Esta é a canônica, e é para ela que as 12 drenam depois.

#: O cabeçalho que separa o BFF (que tem a sessão do corretor) de um browser
#: qualquer. ⚠️ O mesmo literal de `chat.py::CABECALHO_INTERNO`.
CABECALHO_CHAVE_INTERNA = "X-Internal-Key"

#: O cabeçalho pelo qual o BFF diz **em qual corretora o corretor está agora**.
#: 🔴 Ele só vale acompanhado da chave: sem ela, é o navegador escolhendo tenant.
CABECALHO_EMPRESA_ATIVA = "X-Active-Company-Id"


def _chaves_internas() -> set:
    """As chaves que valem como 'sou o BFF' — a mesma dupla do `work_runs.py`.

    ⚠️ Lida a cada chamada, de propósito: um processo que subiu antes da chave
    existir passa a aceitá-la sem reiniciar, e um teste consegue trocá-la.
    """
    candidatas = (
        getattr(settings, "ADMIN_API_KEY", None),
        getattr(settings, "BACKEND_INTERNAL_API_KEY", None),
        os.getenv("ADMIN_API_KEY"),
        os.getenv("BACKEND_INTERNAL_API_KEY"),
    )
    return {str(c).strip() for c in candidatas if c and str(c).strip()}


async def require_internal_key(
    x_internal_key: Optional[str] = Header(None, alias=CABECALHO_CHAVE_INTERNA),
) -> None:
    """Dependency: só passa quem prova ser o BFF.

    🔴 **Chave errada vale como chave nenhuma** — 401 nos dois casos, e a mesma
    frase. Não existe estado intermediário, e é isso que impede alguém de
    descobrir, pela diferença entre as respostas, que a chave que ele tem
    "quase" serve. É a mesma regra de `chat.py::_modo_de_confianca`.

    ⚠️ **Chave não configurada no ambiente → 401, nunca "passa todo mundo".**
    Falha fechada: um `.env` incompleto derruba o painel, que é ruidoso e se
    conserta em minutos; o contrário abre o buraco de novo e é silencioso.
    """
    chave = (x_internal_key or "").strip()
    if chave and chave in _chaves_internas():
        return
    logger.warning("[Auth] chamada sem chave interna válida recusada")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="não autorizado",
    )


async def vinculo_vigente(db, company_id: str, user_id: str) -> bool:
    """A pessoa AINDA pertence a esta corretora, AGORA? (SPEC-098 R9)

    Duas metades, porque cada uma pega o que a outra não pega:

    * `company_members` com `status='active'` — a pessoa saiu da corretora;
    * `users_v2.status != 'suspended'` — a conta inteira foi suspensa (e aí
      nenhum vínculo dela vale, em corretora nenhuma).

    🔴 **Erro de banco LEVANTA — nunca devolve `True`, e nunca devolve `False`
    em silêncio.** Esta função é chamada no instante do efeito externo: um
    `except → False` viraria "toda mensagem para de sair quando o Supabase
    tosse", e um `except → True` viraria "todo mundo pode enviar quando o
    Supabase tosse". Quem chama decide o que fazer com a exceção — é a mesma
    regra do OpenFGA (§3): *DB error → nunca allow*.

    ⚠️ `company_members` tem 📊 `policies=0` com `rls=true` e o backend roda com
    service role: o `.eq("company_id", ...)` desta consulta é a cerca real
    (CLAUDE.md §7).
    """
    if not company_id or not user_id:
        return False

    cli = getattr(db, "client", db)

    vinculo = await _talvez_await(
        cli.table("company_members")
        .select("id")
        .eq("company_id", str(company_id))
        .eq("user_id", str(user_id))
        .eq("status", "active")
        .limit(1)
        .execute()
    )
    if not (getattr(vinculo, "data", None) or []):
        return False

    conta = await _talvez_await(
        cli.table("users_v2")
        .select("status")
        .eq("id", str(user_id))
        .limit(1)
        .execute()
    )
    linhas = getattr(conta, "data", None) or []
    if not linhas:
        # Vínculo apontando para usuário que não existe mais. Não é erro de
        # banco — é resposta: não vigente.
        return False
    return str(linhas[0].get("status") or "") != "suspended"


async def _talvez_await(resultado):
    """O mesmo código serve cliente async e cliente síncrono.

    ⚠️ `vinculo_vigente` é chamada tanto de rota FastAPI (cliente async) quanto
    de `platform_outbound` (que recebe o cliente que tiver). Duas versões do
    mesmo SELECT é exatamente o que este helper existe para impedir — é o mesmo
    helper de `services/work/runs.py`, pela mesma razão.
    """
    import inspect

    if inspect.isawaitable(resultado):
        return await resultado
    return resultado


async def require_master_admin(
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
    request: Request = None
) -> bool:
    """
    Dependency that validates Master Admin access via API Key.

    Use for: ops/system endpoints (billing processing, pricing management, plans CRUD)

    Validates the request has a valid admin API key in the X-Admin-API-Key header.

    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(_: bool = Depends(require_master_admin)):
            ...

    Raises:
        HTTPException 401: If API key is missing
        HTTPException 403: If API key is invalid
    """
    admin_key = os.getenv("ADMIN_API_KEY")

    if not admin_key:
        logger.error("[Auth] ADMIN_API_KEY not configured in environment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin authentication not configured"
        )

    if not x_admin_api_key:
        logger.warning(f"[Auth] Missing X-Admin-API-Key header from {request.client.host if request else 'unknown'}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin API key required"
        )

    if x_admin_api_key != admin_key:
        logger.warning(f"[Auth] Invalid admin API key attempt from {request.client.host if request else 'unknown'}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key"
        )

    logger.debug("[Auth] Admin authentication successful")
    return True


async def require_authenticated_user(
    request: Request,
    user_id: Optional[str] = Cookie(None, alias="user_id"),
    db: AsyncSupabaseClient = Depends(get_async_db)
) -> str:
    """
    Dependency that validates user is logged in via session cookie.

    SECURITY: Validates user_id against database to prevent session forgery.

    Use for: frontend admin panel endpoints (send-message, update-status)

    Usage:
        @router.post("/admin-action")
        async def admin_action(user_id: str = Depends(require_authenticated_user)):
            ...

    Returns:
        str: The authenticated user's ID

    Raises:
        HTTPException 401: If user is not logged in or session is invalid
        HTTPException 403: If account is suspended
    """
    if not user_id:
        logger.warning(f"[Auth] Missing user_id cookie from {request.client.host if request else 'unknown'}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in."
        )

    # Validate user exists and is active in database
    try:
        result = await db.client.table("users_v2") \
            .select("id, status") \
            .eq("id", user_id) \
            .single() \
            .execute()

        if not result.data:
            logger.warning(f"[Auth] User {user_id} not found in database")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session. Please log in again."
            )

        user_status = result.data.get("status")
        if user_status == "suspended":
            logger.warning(f"[Auth] User {user_id} is suspended")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account suspended. Contact support."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Auth] Database validation failed for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication check failed"
        ) from e

    logger.debug(f"[Auth] User {user_id} authenticated and validated")
    return user_id


async def get_current_company_id(
    user_id: str = Depends(require_authenticated_user),
    db: AsyncSupabaseClient = Depends(get_async_db),
    x_internal_key: Optional[str] = Header(None, alias=CABECALHO_CHAVE_INTERNA),
    x_active_company_id: Optional[str] = Header(None, alias=CABECALHO_EMPRESA_ATIVA),
) -> str:
    """
    Dependency that returns the company_id of the authenticated user.

    SECURITY: Chains with require_authenticated_user to ensure user is valid,
    then looks up their company_id from the database.

    Use for: billing, checkout, and other endpoints that need company context.

    Usage:
        @router.get("/my-subscription")
        async def get_subscription(company_id: str = Depends(get_current_company_id)):
            ...

    Returns:
        str: The authenticated user's company_id

    Raises:
        HTTPException 401: If user is not authenticated (from require_authenticated_user)
        HTTPException 400: If user is not associated with a company

    -------------------------------------------------------------------------
    🔴 A EMPRESA ATIVA (SPEC-098 R6) — argumento de decisão, nunca estado guardado
    -------------------------------------------------------------------------

    📊 Medido em 06/09/2026: esta função lia `users_v2.company_id` — a corretora
    **PRIMÁRIA** — e alimentava 9 rotas de `billing.py` e `stripe_checkout.py`.
    📊 3 dos 10 vínculos de `company_members` são de pessoas com MAIS DE UMA
    corretora (os sócios): para elas, "a primária" e "a que está aberta na tela"
    são coisas diferentes, e a cobrança obedecia à errada.

    Agora o BFF pode DIZER qual está ativa — e só ele:

        `X-Active-Company-Id` + `X-Internal-Key` válida  → a ATIVA (revalidada)
        `X-Active-Company-Id` sem chave                  → o header é IGNORADO,
                                                            vale a primária
        erro de banco em qualquer ponto                  → 500, nunca a primária

    ⚠️ **Por que ignorar o header em vez de recusar a request**: sem chave, o
    header não é uma tentativa de ataque com resposta útil — é ruído (um proxy,
    um cliente antigo). Ignorá-lo devolve exatamente o comportamento de hoje, e
    o comportamento de hoje é seguro. Recusar quebraria chamadas legítimas por
    causa de um cabeçalho que não deveria ter efeito nenhum.

    🔴 **E a chave sozinha não basta: o vínculo é REVALIDADO.** O BFF já validou
    em `company_members` antes de mandar — mas confiar nisso faria o header ser
    autorização, e ele é só *afirmação*. Vínculo não vigente → **403**, nunca o
    silêncio de cair na primária: cair na primária devolveria dado da corretora
    ERRADA com status 200, que é o defeito mais caro que existe aqui.

    ⚠️ **Ordem de implantação (R7):** o Next passa a MANDAR o header; a api
    passa a ACEITÁ-LO. Nada quebra se a web for implantada depois — sem o
    header, esta função faz o de sempre.
    """
    chave = (x_internal_key or "").strip()
    ativa = (x_active_company_id or "").strip()

    if ativa and chave and chave in _chaves_internas():
        try:
            vigente = await vinculo_vigente(db, ativa, user_id)
        except Exception as e:
            # 🔴 Não sei responder ≠ pode. Fecha em 500 — nunca degrada para a
            # primária, que seria devolver a corretora errada com cara de sucesso.
            logger.error("[Auth] não deu para conferir o vínculo do usuário %s "
                         "com a empresa ativa: %s", user_id, type(e).__name__)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not verify user company.",
            ) from e
        if not vigente:
            logger.warning("[Auth] usuário %s pediu empresa ativa sem vínculo vigente", user_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem acesso a esta corretora.",
            )
        logger.debug("[Auth] empresa ATIVA aceita para o usuário %s", user_id)
        return ativa

    try:
        result = await db.client.table("users_v2") \
            .select("company_id") \
            .eq("id", user_id) \
            .single() \
            .execute()

        if not result.data:
            logger.warning(f"[Auth] User {user_id} not found when getting company_id")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session."
            )

        company_id = result.data.get("company_id")
        if not company_id:
            logger.warning(f"[Auth] User {user_id} has no company_id")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not associated with a company."
            )

        logger.debug(f"[Auth] User {user_id} belongs to company {company_id}")
        return company_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Auth] Error getting company_id for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not verify user company."
        ) from e
