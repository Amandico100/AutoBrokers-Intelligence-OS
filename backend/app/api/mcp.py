"""
MCP API Routes - Gerenciamento de integrações MCP.
Credenciais OAuth são da PLATAFORMA (variáveis de ambiente).
"""

import html
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..core.auth import require_internal_key
from ..core.database import get_supabase_client
from ..services.langchain_service import invalidate_agent_graph_cache
from ..services.mcp_gateway_service import get_mcp_gateway

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# 🔴 SPEC-098 U4.a/R7 — A CHAVE DO BFF (o buraco que este arquivo era)
# =============================================================================
#
# 📊 Medido em 06/09/2026, ao vivo, contra o smith-api em produção:
#
#     GET …/api/sanitization/jobs?company_id=<uuid falso>   → 200
#     GET …/api/mcp/servers?company_id=<uuid falso>         → 200
#
# 📊 E `grep -c 'Depends(\|_require_internal_key\|_autorizar'` neste arquivo,
# antes desta linha existir: **0**. O `company_id` chegava de fora e era usado
# como se fosse credencial.
#
# ⚠️ O comentário que existia aqui — *"company_id is provided by the Next.js
# proxy after session validation"* — descrevia uma INTENÇÃO. Nada verificava que
# o chamador era o proxy. Comentário não é guarda; `Depends` é.
#
# 🔴 ORDEM DE IMPLANTAÇÃO (R7): **smith-web primeiro, smith-api depois.** A web
# passa a MANDAR `X-Internal-Key`; a api passa a EXIGIR. Na ordem inversa, o
# painel fica 401 até a web subir.



async def _validate_agent_belongs_to_company(agent_id: str, company_id: str) -> bool:
    """
    Valida que o agent_id pertence à company_id para evitar acesso indevido entre empresas.
    """
    try:
        supabase = get_supabase_client().client
        result = supabase.table("agents") \
            .select("id") \
            .eq("id", agent_id) \
            .eq("company_id", company_id) \
            .single() \
            .execute()
        return result.data is not None
    except Exception:
        return False


async def _validate_connection_belongs_to_company(connection_id: str, company_id: str) -> bool:
    """A conexão OAuth pertence a ESTA corretora?

    🔴 SPEC-098 · CONSERTO 1 (red team B1). `DELETE /connections/{id}` apagava a
    conexão do Gmail/Calendar por id, **sem chave, sem corretora e sem dono** —
    escrita destrutiva cross-tenant. `agent_mcp_connections` não tem
    `company_id`: quem sabe de quem é a conexão é o AGENTE dela. Então a
    pergunta é feita em dois saltos, com o mesmo cliente e o mesmo filtro que
    `_validate_agent_belongs_to_company` usa.

    ⛔ Erro de banco → **False**. Não conseguir provar a posse não é o mesmo que
    provar a posse (a mesma regra do `DELETE /chat/session`).
    """
    try:
        supabase = get_supabase_client().client
        conexao = supabase.table("agent_mcp_connections")             .select("agent_id")             .eq("id", connection_id)             .single()             .execute()
        agent_id = (conexao.data or {}).get("agent_id")
        if not agent_id:
            return False
        return await _validate_agent_belongs_to_company(str(agent_id), company_id)
    except Exception:
        return False


class EnableServerRequest(BaseModel):
    mcp_server_id: str
    company_id: str


# =========================================================================
# SERVERS
# =========================================================================

@router.get("/servers", dependencies=[Depends(require_internal_key)])
async def list_available_servers():
    """
    Lista todos os MCP servers disponíveis.
    Inclui informação se o provider OAuth está configurado na plataforma.
    """
    from ..services.mcp_oauth_service import get_mcp_oauth_service

    gateway = get_mcp_gateway()
    oauth = get_mcp_oauth_service()

    servers = await gateway.get_available_servers()

    # Adicionar info de configuração do provider
    for server in servers:
        provider = server.get("oauth_provider")
        if provider:
            server["provider_configured"] = oauth.is_provider_configured(provider)
        else:
            server["provider_configured"] = True  # Não precisa de OAuth

    return {"servers": servers}


@router.get("/servers/{server_name}/tools", dependencies=[Depends(require_internal_key)])
async def discover_server_tools(
    server_name: str,
    agent_id: Optional[str] = Query(None)
):
    """Descobre as tools disponíveis em um MCP server."""
    gateway = get_mcp_gateway()
    result = await gateway.discover_server_tools(server_name, agent_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


# =========================================================================
# AGENT TOOLS
# =========================================================================

@router.post("/agent/{agent_id}/enable-server", dependencies=[Depends(require_internal_key)])
async def enable_server_for_agent(
    agent_id: str,
    request: EnableServerRequest
):
    """
    Habilita um MCP server para um agente.
    Descobre tools automaticamente e cria entradas no banco.
    """
    # Validação de segurança: agente deve pertencer à empresa
    if not await _validate_agent_belongs_to_company(agent_id, request.company_id):
        raise HTTPException(status_code=403, detail="Agente não pertence a esta empresa")

    gateway = get_mcp_gateway()
    result = await gateway.enable_server_for_agent(
        agent_id=agent_id,
        mcp_server_id=request.mcp_server_id,
        company_id=request.company_id
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    # Invalidar cache do grafo
    try:
        invalidate_agent_graph_cache(request.company_id, agent_id)
        logger.info(f"[MCP API] Cache invalidado para agent {agent_id}")
    except Exception as e:
        logger.warning(f"[MCP API] Erro ao invalidar cache: {e}")

    return result


@router.delete("/agent/{agent_id}/disable-server/{mcp_server_id}",
               dependencies=[Depends(require_internal_key)])
async def disable_server_for_agent(
    agent_id: str,
    mcp_server_id: str,
    company_id: str = Query(...)
):
    """Desabilita um MCP server para um agente."""
    # Validação de segurança: agente deve pertencer à empresa
    if not await _validate_agent_belongs_to_company(agent_id, company_id):
        raise HTTPException(status_code=403, detail="Agente não pertence a esta empresa")

    gateway = get_mcp_gateway()
    result = await gateway.disable_server_for_agent(agent_id, mcp_server_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    try:
        invalidate_agent_graph_cache(company_id, agent_id)
    except Exception:
        pass

    return result


@router.get("/agent/{agent_id}/tools", dependencies=[Depends(require_internal_key)])
async def list_agent_mcp_tools(agent_id: str, company_id: str = Query(...)):
    """Lista todas as MCP tools habilitadas para um agente.

    🔴 SPEC-098 · CONSERTO 1 (red team B1): esta rota ficou de fora do `Depends`
    da primeira passada e não recebia `company_id`. A proxy do Next carimbava a
    chave e conferia a corretora da sessão — e o backend ignorava a corretora
    aqui, então um corretor legítimo de A lia as tools do agente de B.
    """
    if not await _validate_agent_belongs_to_company(agent_id, company_id):
        raise HTTPException(status_code=403, detail="Agente não pertence a esta empresa")

    gateway = get_mcp_gateway()
    tools = await gateway.get_agent_mcp_tools(agent_id)

    formatted_tools = [
        {
            "variable_name": t["variable_name"],
            "display_name": f"🔗 {t['mcp_server_name']}: {t['tool_name']}",
            "description": t.get("description", ""),
            "type": "mcp",
            "mcp_server_id": t.get("mcp_server_id"),
            "mcp_server_name": t.get("mcp_server_name"),
        }
        for t in tools
    ]

    return {"tools": formatted_tools}


@router.patch("/agent/{agent_id}/tool/{tool_id}/toggle",
              dependencies=[Depends(require_internal_key)])
async def toggle_mcp_tool(
    agent_id: str,
    tool_id: str,
    enabled: bool = Query(True),
    company_id: str = Query(...)
):
    """Habilita/desabilita uma tool MCP específica."""
    # Validação de segurança: agente deve pertencer à empresa
    if not await _validate_agent_belongs_to_company(agent_id, company_id):
        raise HTTPException(status_code=403, detail="Agente não pertence a esta empresa")

    try:
        supabase = get_supabase_client().client
        supabase.table("agent_mcp_tools") \
            .update({"is_enabled": enabled}) \
            .eq("id", tool_id) \
            .eq("agent_id", agent_id) \
            .execute()

        try:
            invalidate_agent_graph_cache(company_id, agent_id)
        except Exception:
            pass

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# =========================================================================
# OAUTH - Credenciais da PLATAFORMA
# =========================================================================

@router.get("/oauth/providers", dependencies=[Depends(require_internal_key)])
async def list_oauth_providers():
    """
    Lista providers OAuth e se estão configurados na plataforma.
    Útil para o frontend saber quais integrações estão disponíveis.
    """
    from ..services.mcp_oauth_service import get_mcp_oauth_service

    oauth = get_mcp_oauth_service()

    providers = {
        "google": {
            "name": "Google",
            "configured": oauth.is_provider_configured("google"),
            "services": ["Google Calendar", "Google Drive"],
        },
        "github": {
            "name": "GitHub",
            "configured": oauth.is_provider_configured("github"),
            "services": ["GitHub"],
        },
        "slack": {
            "name": "Slack",
            "configured": oauth.is_provider_configured("slack"),
            "services": ["Slack"],
        },
    }

    return {"providers": providers}


@router.get("/oauth/url/{provider}", dependencies=[Depends(require_internal_key)])
async def get_oauth_url(
    provider: str,
    agent_id: str = Query(...),
    mcp_server_id: str = Query(...),
    company_id: str = Query(...)
):
    """
    Gera URL de autorização OAuth.
    Usa credenciais da PLATAFORMA (variáveis de ambiente).

    🔴 SPEC-098 · CONSERTO 1 (red team B1): o `state` assinado leva o `agent_id`
    dentro. Sem esta cerca, qualquer um mandava o backend assinar um convite de
    OAuth para o agente de OUTRA corretora.
    """
    if not await _validate_agent_belongs_to_company(agent_id, company_id):
        raise HTTPException(status_code=403, detail="Agente não pertence a esta empresa")

    from ..services.mcp_oauth_service import get_mcp_oauth_service

    oauth = get_mcp_oauth_service()
    result = await oauth.get_authorization_url(provider, agent_id, mcp_server_id)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


# 🔴 A ÚNICA ROTA DESTE ARQUIVO QUE FICA PÚBLICA — E POR QUÊ.
#
# Quem chama `/oauth/callback/{provider}` é o NAVEGADOR do corretor, redirecionado
# pelo Google/GitHub/Slack. Não passa pela nossa proxy e não pode carregar a chave
# interna: exigir `X-Internal-Key` aqui mataria todo o OAuth.
#
# ⚠️ O que faz o papel do guarda é o `state` ASSINADO com HMAC-SHA256
# (`_encode_state`/`_decode_state` em `mcp_oauth_service.py`): o `agent_id` chega
# de dentro da assinatura, não da barra de endereços. E o convite que gera esse
# `state` (`GET /oauth/url/...`) agora exige a chave E confere o agente contra a
# corretora — então ninguém consegue fazer o backend assinar um state alheio.
#
# 📊 Esta exceção está escrita também no varredor do router
# (`tests/test_098_builder_b_unit.py`, `ABERTAS_COM_RAZAO`): uma rota só fica
# fora do `Depends` com a razão ao lado dela.
@router.get("/oauth/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...)
):
    """
    Callback OAuth. Provider redireciona para cá após autorização.
    Troca code por tokens e salva para o agente.
    """
    from fastapi.responses import HTMLResponse

    from ..services.mcp_oauth_service import get_mcp_oauth_service

    oauth = get_mcp_oauth_service()
    result = await oauth.exchange_code_for_tokens(provider, code, state)

    # Proteção XSS: escape de valores antes de inserir no HTML
    safe_provider = html.escape(provider)

    if result.get("success"):
        html_content = """
        <html>
        <head><title>Conexão Realizada</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px; background: #1a1a1a; color: white;">
            <h1>✅ Conexão Realizada!</h1>
            <p>Você pode fechar esta janela.</p>
            <script>
                if (window.opener) {
                    window.opener.postMessage({ type: 'MCP_OAUTH_SUCCESS', provider: '%s' }, '*');
                }
                setTimeout(() => window.close(), 2000);
            </script>
        </body>
        </html>
        """ % safe_provider
        return HTMLResponse(content=html_content)
    else:
        safe_error = html.escape(result.get("error", "Erro desconhecido"))
        html_content = """
        <html>
        <head><title>Erro na Conexão</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px; background: #1a1a1a; color: white;">
            <h1>❌ Erro na Conexão</h1>
            <p>%s</p>
            <p>Você pode fechar esta janela e tentar novamente.</p>
        </body>
        </html>
        """ % safe_error
        return HTMLResponse(content=html_content, status_code=400)


@router.get("/agent/{agent_id}/connections", dependencies=[Depends(require_internal_key)])
async def list_agent_connections(agent_id: str, company_id: str = Query(...)):
    """Lista conexões OAuth de um agente.

    🔴 SPEC-098 · CONSERTO 1 (red team B1): sem chave e sem corretora, esta rota
    devolvia as CONTAS CONECTADAS de qualquer agente de qualquer corretora.
    """
    if not await _validate_agent_belongs_to_company(agent_id, company_id):
        raise HTTPException(status_code=403, detail="Agente não pertence a esta empresa")

    from ..services.mcp_oauth_service import get_mcp_oauth_service

    oauth = get_mcp_oauth_service()
    connections = await oauth.get_agent_connections(agent_id)

    return {"connections": connections}


@router.post("/agent/{agent_id}/disconnect/{mcp_server_id}",
             dependencies=[Depends(require_internal_key)])
async def disconnect_agent(
    agent_id: str,
    mcp_server_id: str,
    company_id: str = Query(...)
):
    """Desconecta um agente de um provider (remove tokens)."""
    # Validação de segurança: agente deve pertencer à empresa
    if not await _validate_agent_belongs_to_company(agent_id, company_id):
        raise HTTPException(status_code=403, detail="Agente não pertence a esta empresa")

    from ..services.mcp_oauth_service import get_mcp_oauth_service

    oauth = get_mcp_oauth_service()
    success = await oauth.disconnect_agent(agent_id, mcp_server_id)

    if not success:
        raise HTTPException(status_code=500, detail="Falha ao desconectar")

    try:
        invalidate_agent_graph_cache(company_id, agent_id)
    except Exception:
        pass

    return {"success": True}


@router.delete("/connections/{connection_id}", dependencies=[Depends(require_internal_key)])
async def delete_connection(connection_id: str, company_id: str = Query(...)):
    """Remove uma conexão completamente.

    🔴 SPEC-098 · CONSERTO 1 (red team B1) — ERA O PIOR DOS QUATRO: escrita
    DESTRUTIVA anônima. Sem chave, sem corretora e sem dono, qualquer pessoa na
    internet derrubava a integração de Gmail/Calendar de qualquer corretora — e
    não há tela nenhuma que diga por quê.
    """
    if not await _validate_connection_belongs_to_company(connection_id, company_id):
        raise HTTPException(status_code=403, detail="Conexão não pertence a esta empresa")

    from ..services.mcp_oauth_service import get_mcp_oauth_service

    oauth = get_mcp_oauth_service()
    success = await oauth.delete_connection(connection_id)

    if not success:
        raise HTTPException(status_code=500, detail="Falha ao remover conexão")

    return {"success": True}
