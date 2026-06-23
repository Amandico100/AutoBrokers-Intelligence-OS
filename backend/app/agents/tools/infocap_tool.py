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
    policy_ref: Optional[str] = Field(default=None, description="Referência da apólice (policy_ref/nosnum) retornada numa consulta anterior. Informe para obter os DETALHES de cobertura daquela apólice específica.")


def _internal_key() -> Optional[str]:
    return os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")


class InfocapPolicyLookupTool(BaseTool):
    name: str = "infocap_policy_lookup"
    description: str = (
        "Consulta apólice e cobertura na InfoCap da SUA corretora. Conversa INTERNA com o corretor: "
        "pode entregar os dados ao corretor (ele é o dono). Use por CPF/CNPJ ou nome para LISTAR apólices; "
        "depois, para DETALHAR coberturas de uma apólice, chame de novo passando o `policy_ref` retornado. "
        "Não inventa cobertura: se a fonte não trouxer, diga que não veio. Não acessa dados de outras corretoras."
    )
    args_schema: Type[BaseModel] = InfocapLookupInput

    company_id: str = ""

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, **kwargs):
        super().__init__(**kwargs)
        self.company_id = str(company_id or "")

    async def _find_conn_id(self, db) -> Optional[str]:
        from app.api.infocap_connector import INFOCAP_SLUG
        conns = (
            await db.client.table("tenant_connections")
            .select("id, status, connector_templates(slug)")
            .eq("company_id", self.company_id)
            .execute()
        )
        for row in (conns.data or []):
            slug = (row.get("connector_templates") or {}).get("slug")
            if slug == INFOCAP_SLUG and str(row.get("status", "")).lower() in ("connected", "active", "healthy"):
                return row.get("id")
        return None

    async def _arun(self, document: Optional[str] = None, name: Optional[str] = None, policy_ref: Optional[str] = None) -> Dict[str, Any]:
        if not document and not name and not policy_ref:
            return {"content": "Informe CPF/CNPJ, nome do cliente, ou um policy_ref para detalhar a cobertura.", "found": False}
        key = _internal_key()
        if not key:
            return {"content": "Consulta InfoCap indisponível (configuração interna ausente).", "found": False}
        try:
            from app.core.database import create_async_supabase_client
            db = await create_async_supabase_client()
            conn_id = await self._find_conn_id(db)
            if not conn_id:
                return {"content": "A InfoCap ainda não está conectada para a sua corretora. Configure em Conectores.", "found": False, "status": "not_connected"}

            # Modo DETALHE: coberturas de uma apólice específica.
            if policy_ref:
                from app.api.infocap_connector import infocap_policy_detail, InfocapPolicyDetailPayload
                dpayload = InfocapPolicyDetailPayload(
                    company_id=self.company_id, tenant_connection_id=str(conn_id), policy_ref=str(policy_ref),
                )
                det = await infocap_policy_detail(payload=dpayload, x_autobrokers_internal_key=key, db=db)
                return {"content": self._summarize_detail(det), "data": det, "found": bool(det.get("ok"))}

            # Modo LISTA: localizar apólices por CPF/CNPJ ou nome.
            from app.api.infocap_connector import infocap_lookup, InfocapLookupPayload
            payload = InfocapLookupPayload(
                company_id=self.company_id, tenant_connection_id=str(conn_id),
                document=document or None, name=name or None,
            )
            result = await infocap_lookup(payload=payload, x_autobrokers_internal_key=key, db=db)
            return {"content": self._summarize(result), "data": result, "found": bool(result.get("ok"))}
        except Exception as e:  # noqa: BLE001
            logger.error(f"[InfocapPolicyLookupTool] erro: {type(e).__name__}")
            return {"content": "Não consegui consultar a InfoCap agora. Tente novamente em instantes.", "found": False, "error": type(e).__name__}

    def _run(self, document: Optional[str] = None, name: Optional[str] = None, policy_ref: Optional[str] = None) -> Dict[str, Any]:
        # InfoCap é assíncrono; uso síncrono não suportado neste runtime.
        return {"content": "Consulta InfoCap deve ser executada de forma assíncrona.", "found": False}

    @staticmethod
    def _summarize_detail(d: Dict[str, Any]) -> str:
        if not d.get("ok"):
            st = d.get("status")
            if st in ("blocked_not_configured", "blocked_missing_credentials"):
                return "A InfoCap não está totalmente configurada para a sua corretora."
            return "Não consegui obter os detalhes dessa apólice na InfoCap agora."
        pack = d.get("policy_evidence_pack") or {}
        secs = pack.get("coverage_sections") or []
        lines = [
            "Detalhes da apólice (InfoCap):",
            f"- Seguradora: {pack.get('insurer_detected') or '—'} · Produto: {pack.get('product_detected') or '—'}",
            f"- Nº (mascarado): {pack.get('masked_policy_number') or '—'} · Situação: {pack.get('policy_status') or '—'}",
            f"- Vigência: {pack.get('valid_from') or '—'} a {pack.get('valid_to') or '—'}",
        ]
        if secs:
            lines.append("- Coberturas:")
            for s in secs[:20]:
                lines.append(f"   • {s.get('label')}" + (f" — {s.get('amount')}" if s.get('amount') else ""))
        else:
            lines.append("- Coberturas detalhadas não vieram no documento desta apólice (existência confirmada, itens não retornados).")
        if pack.get("limitations"):
            lines.append("- Observações: " + "; ".join(pack.get("limitations")[:3]))
        return "\n".join(lines)

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
