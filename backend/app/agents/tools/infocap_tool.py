"""
InfoCap Policy Lookup Tool (SPEC-014 C1 slice 3) — capability `operational.infocap.policy_lookup.read`.

Permite ao Chat Principal (Core) consultar apólice/cobertura na InfoCap da PRÓPRIA corretora,
reutilizando o conector já provado (mesma lógica do atendimento). READ-ONLY, escopado à empresa,
credenciais isoladas por corretora (Vault). Defensivo: qualquer falha vira mensagem amigável.
"""

import logging
import os
from typing import Any, Dict, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class InfocapLookupInput(BaseModel):
    document: Optional[str] = Field(default=None, description="CPF ou CNPJ do cliente (só números ou formatado).")
    name: Optional[str] = Field(default=None, description="Nome do cliente (use se não tiver CPF/CNPJ).")


def _internal_key() -> Optional[str]:
    return os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")


class InfocapPolicyLookupTool(BaseTool):
    name: str = "infocap_policy_lookup"
    description: str = (
        "Consulta apólice e cobertura na InfoCap da SUA corretora por CPF/CNPJ ou nome do cliente. "
        "Retorna dados sanitizados (número/nome mascarados), seguradora, produto, vigência e situação. "
        "Use quando precisar verificar a apólice de um cliente. Não inventa cobertura: se não houver "
        "evidência, diz que não encontrou. Não acessa dados de outras corretoras."
    )
    args_schema: Type[BaseModel] = InfocapLookupInput

    company_id: str = ""

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, **kwargs):
        super().__init__(**kwargs)
        self.company_id = str(company_id or "")

    async def _arun(self, document: Optional[str] = None, name: Optional[str] = None) -> Dict[str, Any]:
        if not document and not name:
            return {"content": "Informe CPF/CNPJ ou nome do cliente para consultar a apólice.", "found": False}
        key = _internal_key()
        if not key:
            return {"content": "Consulta InfoCap indisponível (configuração interna ausente).", "found": False}
        try:
            # imports tardios para evitar ciclo de import no carregamento do módulo
            from app.core.database import create_async_supabase_client
            from app.api.infocap_connector import infocap_lookup, InfocapLookupPayload, INFOCAP_SLUG

            db = await create_async_supabase_client()
            # localizar a conexão InfoCap conectada da própria corretora
            conns = (
                await db.client.table("tenant_connections")
                .select("id, status, connector_templates(slug)")
                .eq("company_id", self.company_id)
                .execute()
            )
            conn_id = None
            for row in (conns.data or []):
                slug = (row.get("connector_templates") or {}).get("slug")
                if slug == INFOCAP_SLUG and str(row.get("status", "")).lower() in ("connected", "active", "healthy"):
                    conn_id = row.get("id")
                    break
            if not conn_id:
                return {"content": "A InfoCap ainda não está conectada para a sua corretora. Configure em Conectores.", "found": False, "status": "not_connected"}

            payload = InfocapLookupPayload(
                company_id=self.company_id, tenant_connection_id=str(conn_id),
                document=document or None, name=name or None,
            )
            result = await infocap_lookup(payload=payload, x_autobrokers_internal_key=key, db=db)
            return {"content": self._summarize(result), "data": result, "found": bool(result.get("ok"))}
        except Exception as e:  # noqa: BLE001
            logger.error(f"[InfocapPolicyLookupTool] erro: {type(e).__name__}")
            return {"content": "Não consegui consultar a InfoCap agora. Tente novamente em instantes.", "found": False, "error": type(e).__name__}

    def _run(self, document: Optional[str] = None, name: Optional[str] = None) -> Dict[str, Any]:
        # InfoCap é assíncrono; uso síncrono não suportado neste runtime.
        return {"content": "Consulta InfoCap deve ser executada de forma assíncrona.", "found": False}

    @staticmethod
    def _summarize(r: Dict[str, Any]) -> str:
        status = r.get("status")
        if r.get("ok") and status == "found":
            sel = r.get("selected") or {}
            return (
                "Apólice localizada na InfoCap:\n"
                f"- Seguradora: {sel.get('insurer_key') or '—'} · Produto: {sel.get('product') or '—'}\n"
                f"- Nº (mascarado): {sel.get('masked_policy_number') or '—'} · Titular: {sel.get('holder_name_masked') or '—'}\n"
                f"- Situação: {sel.get('policy_status') or '—'} · Vigência: {sel.get('valid_from') or '—'} a {sel.get('valid_to') or '—'}\n"
                "Observação: cobertura específica depende da leitura dos itens da apólice."
            )
        if status == "multiple_matches":
            return "Encontrei mais de uma apólice/cliente para esse termo. Confirme com mais dados (CPF/CNPJ) para selecionar a correta."
        if status in ("not_found", "client_found"):
            return "Não localizei apólice ativa para esse cliente na InfoCap."
        if status in ("blocked_not_configured", "blocked_missing_credentials"):
            return "A InfoCap não está totalmente configurada para a sua corretora (credencial/base ausente)."
        return "Não foi possível concluir a consulta na InfoCap agora."
