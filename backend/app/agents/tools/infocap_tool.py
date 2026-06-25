"""
InfoCap Policy Lookup Tool (SPEC-014 C1 slice 3).

Read-only Core tool scoped to the broker company. Connection selection is not
implemented here: the backend InfoCap endpoints own the canonical tenant
connection resolution so Chat, detail and probe share the same rule.
"""

import logging
import os
from typing import Any, Dict, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class InfocapLookupInput(BaseModel):
    document: Optional[str] = Field(default=None, description="CPF/CNPJ do cliente.")
    name: Optional[str] = Field(default=None, description="Nome do cliente, quando nao houver CPF/CNPJ.")
    policy_ref: Optional[str] = Field(
        default=None,
        description="Referencia tecnica da apolice retornada pela listagem, preferencialmente infocap:<codfil>:<nosnum>.",
    )


def _internal_key() -> Optional[str]:
    return os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")


class InfocapPolicyLookupTool(BaseTool):
    name: str = "infocap_policy_lookup"
    description: str = (
        "Consulta apolices e detalhes operacionais na InfoCap da propria corretora. "
        "Use CPF/CNPJ ou nome para listar apolices; depois use o policy_ref retornado "
        "para detalhar uma apolice especifica. Nao inventa cobertura se a fonte nao trouxer."
    )
    args_schema: Type[BaseModel] = InfocapLookupInput

    company_id: str = ""

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, **kwargs):
        super().__init__(**kwargs)
        self.company_id = str(company_id or "")

    async def _arun(
        self,
        document: Optional[str] = None,
        name: Optional[str] = None,
        policy_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not document and not name and not policy_ref:
            return {"content": "Informe CPF/CNPJ, nome do cliente, ou um policy_ref para detalhar a apolice.", "found": False}
        key = _internal_key()
        if not key:
            return {"content": "Consulta InfoCap indisponivel: configuracao interna ausente.", "found": False}
        try:
            from app.core.database import create_async_supabase_client

            db = await create_async_supabase_client()

            if policy_ref:
                from app.api.infocap_connector import InfocapPolicyDetailPayload, infocap_policy_detail

                dpayload = InfocapPolicyDetailPayload(
                    company_id=self.company_id,
                    policy_ref=str(policy_ref),
                    unmasked=True,
                )
                det = await infocap_policy_detail(payload=dpayload, x_autobrokers_internal_key=key, db=db)
                return {"content": self._summarize_detail(det), "data": det, "found": bool(det.get("ok"))}

            from app.api.infocap_connector import InfocapLookupPayload, infocap_lookup

            payload = InfocapLookupPayload(
                company_id=self.company_id,
                document=document or None,
                name=name or None,
                unmasked=True,
            )
            result = await infocap_lookup(payload=payload, x_autobrokers_internal_key=key, db=db)
            return {"content": self._summarize(result), "data": result, "found": bool(result.get("ok"))}
        except Exception as e:  # noqa: BLE001
            logger.error(f"[InfocapPolicyLookupTool] erro: {type(e).__name__}")
            return {"content": "Nao consegui consultar a InfoCap agora. Tente novamente em instantes.", "found": False, "error": type(e).__name__}

    def _run(
        self,
        document: Optional[str] = None,
        name: Optional[str] = None,
        policy_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {"content": "Consulta InfoCap deve ser executada de forma assincrona.", "found": False}

    @staticmethod
    def _summarize_detail(d: Dict[str, Any]) -> str:
        if not d.get("ok"):
            st = d.get("status")
            if st in ("blocked_not_configured", "blocked_missing_credentials"):
                return "A InfoCap nao esta totalmente configurada para a sua corretora."
            if st == "ambiguous_connection":
                return "Ha mais de uma conexao InfoCap elegivel. E necessario limpar as conexoes duplicadas antes da consulta."
            if st == "source_limited":
                return "Use a referencia tecnica da apolice no formato infocap:<codfil>:<nosnum> retornada pela listagem antes de detalhar."
            return "Nao consegui obter os detalhes dessa apolice na InfoCap agora."
        pack = d.get("policy_evidence_pack") or {}
        secs = pack.get("coverage_sections") or []
        num = pack.get("policy_number") or pack.get("masked_policy_number") or "-"
        titular = pack.get("holder_name") or pack.get("holder_name_masked") or "-"
        lines = [
            "Detalhes da apolice (InfoCap):",
            f"- Seguradora: {pack.get('insurer_detected') or '-'} - Produto: {pack.get('product_detected') or '-'}",
            f"- Numero da apolice: {num} - Titular: {titular}" + (f" - CPF/CNPJ: {pack.get('document')}" if pack.get("document") else ""),
            f"- Situacao: {pack.get('policy_status') or '-'} - Vigencia: {pack.get('valid_from') or '-'} a {pack.get('valid_to') or '-'}",
        ]
        if pack.get("installments"):
            lines.append(f"- Parcelas retornadas: {len(pack.get('installments') or [])}")
        if secs:
            lines.append("- Coberturas estruturadas:")
            for section in secs[:20]:
                lines.append(f"   - {section.get('label')}" + (f" - {section.get('amount')}" if section.get("amount") else ""))
        else:
            lines.append("- A InfoCap confirmou a apolice e os dados operacionais, mas nao retornou itens estruturados de cobertura nesta consulta.")
            if pack.get("official_document_source_available"):
                lines.append("- Ha fonte documental oficial disponivel para a proxima etapa de evidencia documental; ela nao foi baixada nem analisada nesta consulta.")
        if pack.get("limitations"):
            lines.append("- Observacoes: " + "; ".join(pack.get("limitations")[:3]))
        return "\n".join(lines)

    @staticmethod
    def _summarize(r: Dict[str, Any]) -> str:
        status = r.get("status")
        cli = ""
        if r.get("client_document") or r.get("client_name"):
            cli = f"\n- Cliente: {r.get('client_name') or '-'} - CPF/CNPJ: {r.get('client_document') or '-'}"
        if r.get("ok") and status == "found":
            sel = r.get("selected") or {}
            pack = r.get("policy_evidence_pack") or {}
            num = sel.get("policy_number") or sel.get("masked_policy_number") or "-"
            titular = sel.get("holder_name") or sel.get("holder_name_masked") or "-"
            doc = sel.get("document") or r.get("client_document")
            detail_ref = sel.get("policy_locator_ref") or sel.get("policy_ref") or "-"
            lines = [
                "Apolice localizada na InfoCap:",
                f"- Seguradora: {sel.get('insurer_key') or '-'} - Produto: {sel.get('product') or '-'}",
                f"- Numero da apolice: {num} - Titular: {titular}" + (f" - CPF/CNPJ: {doc}" if doc else ""),
                f"- Situacao: {sel.get('policy_status') or '-'} - Vigencia: {sel.get('valid_from') or '-'} a {sel.get('valid_to') or '-'}",
                f"- policy_ref: {detail_ref} (use para detalhar os dados desta apolice).",
            ]
            if pack.get("structured_coverage_absent"):
                lines.append("- Cobertura: ausencia estruturada na resposta InfoCap; nao inventar cobertura.")
            return "\n".join(lines) + cli
        if status in ("multiple_matches", "ambiguous_customer", "ambiguous_policy"):
            from app.api.infocap_connector import _format_policy_options_for_summary

            options = _format_policy_options_for_summary(r.get("matches") or [])
            base = "Encontrei mais de uma apolice/cliente para esse termo. Peca para o corretor escolher uma opcao antes de detalhar."
            return (base + ("\n" + options if options else "") + cli).strip()
        if status in ("not_found", "client_found"):
            return ("Cliente localizado, mas sem apolice/documento vinculado retornado." + cli) if status == "client_found" else "Nao localizei cliente/apolice para esse termo na InfoCap."
        if status in ("blocked_not_configured", "blocked_missing_credentials"):
            return "A InfoCap nao esta totalmente configurada para a sua corretora: credencial/base ausente."
        if status == "ambiguous_connection":
            return "Ha mais de uma conexao InfoCap elegivel. E necessario limpar as conexoes duplicadas antes da consulta."
        return "Nao foi possivel concluir a consulta na InfoCap agora."
