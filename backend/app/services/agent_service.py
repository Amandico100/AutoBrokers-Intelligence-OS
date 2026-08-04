import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from slugify import slugify

from app.core import get_supabase_client
from app.models.agent import AgentCreate, AgentResponse, AgentUpdate
from app.services.portao_do_prompt import (
    PERSONALIZACAO_MINIMA_CHARS,
    conferir_prompt_gravado,
    desligar_se_nascer_mudo,
    problemas_da_escrita_de_prompt,
)

logger = logging.getLogger(__name__)

# =============================================================================
# In-memory cache for get_agent_by_id() — avoids 2 DB roundtrips per request
# =============================================================================
_agent_cache: Dict[str, Tuple[Any, float]] = {}
_AGENT_CACHE_TTL = 60  # seconds


def _get_cached_agent(agent_id: str) -> Optional[Any]:
    if agent_id in _agent_cache:
        data, ts = _agent_cache[agent_id]
        if time.time() - ts < _AGENT_CACHE_TTL:
            return data
        del _agent_cache[agent_id]
    return None


def _set_cached_agent(agent_id: str, data: Any) -> None:
    _agent_cache[agent_id] = (data, time.time())


def invalidate_agent_cache(agent_id: str = None) -> None:
    """Invalidate cached agent data. If agent_id is None, clears entire cache."""
    if agent_id:
        _agent_cache.pop(agent_id, None)
    else:
        _agent_cache.clear()

class AgentService:
    def __init__(self):
        self.supabase = get_supabase_client()

    def create_agent(self, company_id: UUID, agent_data: AgentCreate) -> AgentResponse:
        try:
            slug = slugify(agent_data.slug or agent_data.name)
            data = agent_data.model_dump(exclude_unset=True)
            data["company_id"] = str(company_id)
            data["slug"] = slug

            # P-38 — AGENTE MUDO NÃO NASCE LIGADO.
            #
            # 📊 `lib/admin/agent-blueprints.ts:40` monta o payload com
            # `agent_system_prompt: s('agent_system_prompt') || undefined` — em
            # JSON, `undefined` faz a CHAVE SUMIR —, e a linha 41 manda
            # `is_active: true`. Chega aqui um insert com prompt NULL e ativo.
            # Este é o último ponto capaz de impedir isso, e o único que vê o
            # payload já montado. Desligar é recuperável; ativo e mudo, não.
            data = desligar_se_nascer_mudo(data, minimo_chars=1)

            # Insert into DB
            result = self.supabase.client.table("agents").insert(data).execute()

            if not result.data:
                raise Exception("Failed to create agent")

            return self._map_to_response(result.data[0])

        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    def get_agents_by_company(self, company_id: UUID) -> List[AgentResponse]:
        try:
            result = (
                self.supabase.client.table("agents")
                .select("*")
                .eq("company_id", str(company_id))
                .eq("is_active", True)
                .order("created_at", desc=True)
                .execute()
            )
            return [self._map_to_response(agent) for agent in result.data]
        except Exception as e:
            logger.error(f"Error fetching agents: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    def get_agent_by_id(self, agent_id: str):
        # Check cache first
        cached = _get_cached_agent(agent_id)
        if cached is not None:
            return cached

        try:
            result = (
                self.supabase.client.table("agents")
                .select("*")
                .eq("id", str(agent_id))
                .single()
                .execute()
            )

            if not result.data:
                return None

            response = self._map_to_response(result.data)
            _set_cached_agent(agent_id, response)
            return response

        except Exception as e:
            logger.error(f"[AgentService] Erro ao buscar agente: {e}")
            return None

    def _company_id_do_agente(self, agent_id: UUID) -> Optional[str]:
        """O tenant dono do agente — pré-requisito de qualquer escrita (§7)."""
        try:
            res = (
                self.supabase.client.table("agents")
                .select("company_id")
                .eq("id", str(agent_id))
                .limit(1)
                .execute()
            )
            linhas = getattr(res, "data", None) or []
            return str(linhas[0].get("company_id")) if linhas and linhas[0].get("company_id") else None
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[AgentService] Não consegui resolver company_id de {agent_id}: {e}")
            return None

    def update_agent(
        self, agent_id: UUID, agent_data: AgentUpdate, company_id: Optional[str] = None
    ) -> AgentResponse:
        try:
            update_data = agent_data.model_dump(exclude_unset=True)

            if update_data.get("name") or update_data.get("slug"):
                name_ref = update_data.get("slug") or update_data.get("name")
                if name_ref:
                    update_data["slug"] = slugify(name_ref)

            # P-38 — O PORTÃO, ANTES DA ESCRITA.
            #
            # 📊 Provado por execução em 04/08/2026:
            # `AgentUpdate(agent_system_prompt='').model_dump(exclude_unset=True)`
            # devolve `{'agent_system_prompt': ''}`. Sem esta linha, uma string
            # vazia entra por cima de um prompt que funcionava, o agente
            # continua ATIVO, e ninguém percebe até o segurado escrever.
            #
            # `exclude_unset` é o que separa os dois casos: quem não mandou a
            # chave não está escrevendo o prompt, e um PATCH de `llm_model` não
            # pode ser recusado por um campo que ele nem tocou.
            if "agent_system_prompt" in update_data:
                problemas = problemas_da_escrita_de_prompt(
                    update_data["agent_system_prompt"],
                    minimo_chars=PERSONALIZACAO_MINIMA_CHARS,
                )
                if problemas:
                    # 400, e não 500: o pedido é que está errado, e o nome do
                    # motivo tem de chegar em quem clicou em Salvar.
                    raise HTTPException(
                        status_code=400,
                        detail=f"prompt_invalido: {','.join(problemas)}",
                    )

            # §7 — o backend usa service role: RLS sem policy não protege nada
            # contra erro de filtro no código. Até aqui o update era escopado
            # SÓ por `id`.
            tenant = company_id or self._company_id_do_agente(agent_id)

            q = self.supabase.client.table("agents").update(update_data).eq("id", str(agent_id))
            if tenant:
                q = q.eq("company_id", str(tenant))
            result = q.execute()

            if not result.data:
                raise Exception("Failed to update agent")

            invalidate_agent_cache(str(agent_id))

            # A RELEITURA. Só corre quando o prompt foi tocado — é o único caso
            # em que o agente pode ter ficado mudo, e ela custa um roundtrip.
            # "Gravei" tem de ser afirmação sobre um fato lido de volta: trigger,
            # default de coluna e coluna truncada aparecem AQUI, e não na
            # primeira conversa do segurado.
            if "agent_system_prompt" in update_data:
                conferido = conferir_prompt_gravado(
                    self.supabase.client, tenant, str(agent_id), "agent_service.update_agent"
                )
                if not conferido.ok:
                    invalidate_agent_cache(str(agent_id))
                    raise HTTPException(status_code=500, detail=conferido.reason or "prompt_vazio_apos_escrita")

            return self._map_to_response(result.data[0])

        except HTTPException:
            # Recusa do portão não vira 500 genérico: o motivo tem nome próprio.
            raise
        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    def delete_agent(self, agent_id: UUID):
        try:
            # Soft delete
            result = (
                self.supabase.client.table("agents")
                .update({"is_active": False})
                .eq("id", str(agent_id))
                .execute()
            )

            if not result.data:
                raise HTTPException(status_code=404, detail="Agent not found")

            invalidate_agent_cache(str(agent_id))
            return {"message": "Agent archived successfully"}
        except Exception as e:
            logger.error(f"Error deleting agent {agent_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e



    def _map_to_response(self, data: Dict[str, Any]) -> AgentResponse:
        # Check WhatsApp Integration
        has_whatsapp = False
        try:
            agent_id = data.get("id")
            if agent_id:
                res = (
                    self.supabase.client.table("integrations")
                    .select("id")
                    .eq("agent_id", agent_id)
                    .eq("provider", "z-api")
                    .eq("is_active", True)
                    .limit(1)
                    .execute()
                )
                has_whatsapp = bool(res.data)
        except Exception:
            pass



        return AgentResponse(
            **data,
            has_whatsapp=has_whatsapp,
        )
