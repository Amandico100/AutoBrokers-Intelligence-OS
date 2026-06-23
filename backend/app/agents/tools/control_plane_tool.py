"""
Control Plane Read Tool (SPEC-014 C1 slice 3) — capability `control_plane.read`.

Dá ao Chat Principal (Core) consciência do ESTADO OPERACIONAL da própria corretora:
auxiliares instalados, conexões, saldo, conhecimento, agentes. READ-ONLY, escopado à
empresa atual (nunca cross-tenant), sem segredos. Tudo defensivo: qualquer falha vira
"indisponível", nunca quebra o chat.
"""

import logging
from typing import Any, Dict, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ControlPlaneInput(BaseModel):
    topic: Optional[str] = Field(
        default=None,
        description="Opcional. Foco: 'auxiliares', 'conexoes', 'saldo', 'conhecimento', 'agentes'. Vazio = visão geral.",
    )


def _count(client, table: str, filters: Dict[str, Any]) -> Optional[int]:
    try:
        q = client.table(table).select("id", count="exact")
        for k, v in filters.items():
            q = q.eq(k, v)
        res = q.execute()
        return res.count if getattr(res, "count", None) is not None else len(res.data or [])
    except Exception:  # noqa: BLE001
        return None


class ControlPlaneReadTool(BaseTool):
    name: str = "control_plane_read"
    description: str = (
        "Consulta o estado operacional da SUA corretora (somente leitura): quantos auxiliares estão "
        "instalados/ativos, conexões configuradas, saldo de IA, documentos de conhecimento e status dos "
        "agentes. Use para responder 'minha corretora está pronta?', 'quais auxiliares eu tenho?', "
        "'quanto tenho de saldo?'. Não acessa dados de outras corretoras."
    )
    args_schema: Type[BaseModel] = ControlPlaneInput

    company_id: str = ""
    supabase_client: object = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, supabase_client, **kwargs):
        super().__init__(**kwargs)
        self.company_id = str(company_id or "")
        # mesmo padrão das outras tools do graph (campo público + atribuição direta)
        self.supabase_client = supabase_client

    def _gather(self) -> Dict[str, Any]:
        c = getattr(self.supabase_client, "client", self.supabase_client)
        cid = self.company_id
        out: Dict[str, Any] = {"company_id": cid}

        # Auxiliares instalados
        out["auxiliares_instalados"] = _count(c, "tenant_auxiliaries", {"company_id": cid})

        # Conexões (Vault)
        try:
            res = c.table("tenant_connections").select("status").eq("company_id", cid).execute()
            rows = res.data or []
            out["conexoes_total"] = len(rows)
            out["conexoes_conectadas"] = sum(1 for r in rows if str(r.get("status", "")).lower() in ("connected", "active", "healthy"))
        except Exception:  # noqa: BLE001
            out["conexoes_total"] = None

        # Saldo de IA
        try:
            res = c.table("company_credits").select("balance_brl").eq("company_id", cid).limit(1).execute()
            out["saldo_brl"] = (res.data or [{}])[0].get("balance_brl") if res.data else 0
        except Exception:  # noqa: BLE001
            out["saldo_brl"] = None

        # Conhecimento
        out["documentos_conhecimento"] = _count(c, "documents", {"company_id": cid})

        # Agentes (core/even)
        try:
            res = c.table("agents").select("agent_role, is_active").eq("company_id", cid).execute()
            rows = res.data or []
            out["core_ativo"] = any(r.get("agent_role") == "core" and r.get("is_active") for r in rows)
            out["even_presente"] = any(r.get("agent_role") == "attendance" for r in rows)
        except Exception:  # noqa: BLE001
            pass

        return out

    def _format(self, d: Dict[str, Any]) -> str:
        def fmt(v):
            return "indisponível" if v is None else v
        return (
            "Estado operacional da corretora (somente leitura):\n"
            f"- Auxiliares instalados: {fmt(d.get('auxiliares_instalados'))}\n"
            f"- Conexões: {fmt(d.get('conexoes_total'))} (conectadas: {fmt(d.get('conexoes_conectadas'))})\n"
            f"- Saldo de IA: R$ {fmt(d.get('saldo_brl'))}\n"
            f"- Documentos de conhecimento: {fmt(d.get('documentos_conhecimento'))}\n"
            f"- Core ativo: {fmt(d.get('core_ativo'))} · Even (atendimento) presente: {fmt(d.get('even_presente'))}"
        )

    def _run(self, topic: Optional[str] = None) -> Dict[str, Any]:
        try:
            data = self._gather()
            return {"content": self._format(data), "data": data, "found": True, "source": "control_plane"}
        except Exception as e:  # noqa: BLE001
            logger.error(f"[ControlPlaneReadTool] erro: {e}")
            return {"content": "Estado operacional indisponível no momento.", "found": False, "error": str(e)}

    async def _arun(self, topic: Optional[str] = None) -> Dict[str, Any]:
        return self._run(topic)
