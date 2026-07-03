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
    policy_number: Optional[str] = Field(default=None, description="Numero humano da apolice informado pelo corretor.")
    policy_ref: Optional[str] = Field(
        default=None,
        description="Referencia tecnica interna da apolice, quando disponivel, no formato infocap:<codfil>:<nosnum>.",
    )
    document_evidence_requested: Optional[bool] = Field(
        default=None,
        description="Use true quando a pergunta pedir cobertura, franquia, LMI, clausula, exclusao ou assistencia.",
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
        policy_number: Optional[str] = None,
        policy_ref: Optional[str] = None,
        document_evidence_requested: Optional[bool] = None,
        user_query: Optional[str] = None,
        force_document_evidence_refresh: bool = False,
    ) -> Dict[str, Any]:
        if not document and not name and not policy_number and not policy_ref:
            return {"content": "Informe CPF/CNPJ, nome do cliente, numero da apolice, ou um policy_ref para detalhar a apolice.", "found": False}
        key = _internal_key()
        if not key:
            return {"content": "Consulta InfoCap indisponivel: configuracao interna ausente.", "found": False}
        try:
            from app.core.database import create_async_supabase_client

            db = await create_async_supabase_client()

            if policy_ref:
                from app.api.infocap_connector import _parse_policy_ref_input

                ref_codfil, _ = _parse_policy_ref_input(str(policy_ref))
                if not ref_codfil:
                    policy_number = str(policy_ref)
                    policy_ref = None

            if policy_ref:
                from app.api.infocap_connector import InfocapPolicyDetailPayload, infocap_policy_detail

                dpayload = InfocapPolicyDetailPayload(
                    company_id=self.company_id,
                    policy_ref=str(policy_ref),
                    user_query=user_query,
                    document_evidence_requested=bool(document_evidence_requested),
                    force_document_evidence_refresh=bool(force_document_evidence_refresh),
                    unmasked=True,
                )
                det = await infocap_policy_detail(payload=dpayload, x_autobrokers_internal_key=key, db=db)
                content, assistance_policy = self._render_content(det, user_query, detail=True)
                contract = self._build_policy_response_contract(det, content, assistance_policy)
                return {"content": content, "data": det, "found": bool(det.get("ok")), "policy_response_contract": contract}

            from app.api.infocap_connector import InfocapLookupPayload, infocap_lookup

            payload = InfocapLookupPayload(
                company_id=self.company_id,
                document=document or None,
                name=name or None,
                policy_number=policy_number or None,
                user_query=user_query,
                document_evidence_requested=bool(document_evidence_requested),
                force_document_evidence_refresh=bool(force_document_evidence_refresh),
                unmasked=True,
            )
            result = await infocap_lookup(payload=payload, x_autobrokers_internal_key=key, db=db)
            content, assistance_policy = self._render_content(result, user_query, detail=False)
            contract = self._build_policy_response_contract(result, content, assistance_policy)
            return {"content": content, "data": result, "found": bool(result.get("ok")), "policy_response_contract": contract}
        except Exception as e:  # noqa: BLE001
            logger.error(f"[InfocapPolicyLookupTool] erro: {type(e).__name__}")
            return {"content": "Nao consegui consultar a InfoCap agora. Tente novamente em instantes.", "found": False, "error": type(e).__name__}

    def _run(
        self,
        document: Optional[str] = None,
        name: Optional[str] = None,
        policy_number: Optional[str] = None,
        policy_ref: Optional[str] = None,
        document_evidence_requested: Optional[bool] = None,
        user_query: Optional[str] = None,
        force_document_evidence_refresh: bool = False,
    ) -> Dict[str, Any]:
        return {"content": "Consulta InfoCap deve ser executada de forma assincrona.", "found": False}

    def _render_content(self, data: Dict[str, Any], user_query: Optional[str], detail: bool):
        """SPEC-016 E4: composição humana sob a flag v2, com fallback ao resumo legado."""
        try:
            from app.core.feature_flags import policy_intelligence_v2_enabled

            if policy_intelligence_v2_enabled():
                from app.services.policy_answer_composer import compose_policy_answer_with_meta

                meta = compose_policy_answer_with_meta(question=str(user_query or ""), result=data)
                if meta.get("text"):
                    return meta["text"], meta.get("assistance_policy")
        except Exception as e:  # noqa: BLE001 — composer nunca pode derrubar a tool
            logger.warning(f"[InfocapPolicyLookupTool] composer v2 indisponivel, usando resumo legado: {type(e).__name__}")
        legacy = self._summarize_detail(data) if detail else self._summarize(data)
        return legacy, None

    @staticmethod
    def _build_policy_response_contract(
        data: Dict[str, Any], rendered: str, assistance_policy: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        status = data.get("status") or "provider_error"
        pack = data.get("policy_evidence_pack") or {}
        required_facts = []
        if status in ("ambiguous_policy", "policy_number_ambiguous"):
            required_facts.append("policy_options")
        if status == "identity_mismatch":
            required_facts.append("identity_mismatch")
        if pack.get("structured_coverage_absent"):
            required_facts.append("coverage_absent")
        if pack.get("document_evidence_ready"):
            required_facts.append("document_evidence")
        if status == "source_limited":
            required_facts.append("source_limited")
        contract_assistance = None
        if isinstance(assistance_policy, dict) and assistance_policy.get("applied"):
            # SPEC-016 E4b: política governada aplicada — o guard garante que a
            # resposta final cite os serviços padrão.
            required_facts.append("assistance_policy_applied")
            contract_assistance = {
                "applied": True,
                "rule_id": assistance_policy.get("rule_id"),
                "version": assistance_policy.get("version"),
                "services": assistance_policy.get("services") or [],
            }
        return {
            **({"assistance_policy": contract_assistance} if contract_assistance else {}),
            "provider": "infocap",
            "result_kind": status,
            "coverage_evidence_status": pack.get("coverage_evidence_status") or (data.get("coverage_evidence") or {}).get("coverage_evidence_status"),
            "policy_options": data.get("matches") or [],
            "selected_policy": data.get("selected") or data.get("policy") or {},
            "source_limitation": data.get("message") or "; ".join(data.get("blockers") or []),
            "next_allowed_action": (
                "choose_policy"
                if status in ("ambiguous_policy", "policy_number_ambiguous")
                else "fail_closed"
                if status == "identity_mismatch"
                else "use_official_document_evidence_later"
                if pack.get("document_evidence_required") and not pack.get("document_evidence_ready")
                else "answer_from_document_evidence"
                if pack.get("document_evidence_ready")
                else "answer_from_structured_data"
                if status == "found"
                else "retry_or_refine"
            ),
            "rendered_safe_answer": rendered,
            "required_facts": required_facts,
        }

    @staticmethod
    def _document_evidence_lines(pack: Dict[str, Any]) -> list[str]:
        evidence = (pack.get("official_policy_document_evidence") or {}) if isinstance(pack, dict) else {}
        items = evidence.get("evidence_items") or []
        if not items:
            return []
        lines = [
            "- Evidencia documental da apolice oficial processada:",
        ]
        for item in items[:10]:
            page = item.get("page_number") or "-"
            etype = item.get("evidence_type") or "other"
            text = str(item.get("evidence_text") or "").strip()
            if text:
                lines.append(f"   - Pagina {page} [{etype}]: {text}")
        return lines

    @staticmethod
    def _summarize_detail(d: Dict[str, Any]) -> str:
        if not d.get("ok"):
            st = d.get("status")
            if st in ("blocked_not_configured", "blocked_missing_credentials"):
                return "A InfoCap nao esta totalmente configurada para a sua corretora."
            if st == "ambiguous_connection":
                return "Ha mais de uma conexao InfoCap elegivel. E necessario limpar as conexoes duplicadas antes da consulta."
            if st == "source_limited":
                return "A InfoCap localizou o pedido, mas ainda faltou resolver a apolice em uma opcao unica do catalogo. Informe CPF/nome do segurado ou o numero humano da apolice para eu resolver o detalhe com seguranca."
            if st == "identity_mismatch":
                return "A identidade da apolice nao foi confirmada. Por seguranca, nao vou exibir detalhes nem consultar documento desta apolice."
            if st == "policy_number_not_found":
                return "Nao localizei apolice com esse numero humano na InfoCap."
            if st == "policy_number_ambiguous":
                return "Esse numero humano apareceu em mais de uma apolice. Preciso de seguradora, ramo, vigencia ou cliente para escolher com seguranca."
            return "Nao consegui obter os detalhes dessa apolice na InfoCap agora."
        pack = d.get("policy_evidence_pack") or {}
        secs = pack.get("coverage_sections") or []
        from app.api.infocap_connector import _display_policy_number

        num = _display_policy_number(pack)
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
        elif pack.get("document_evidence_ready"):
            lines.extend(InfocapPolicyLookupTool._document_evidence_lines(pack))
        else:
            lines.append("- A InfoCap confirmou a apolice e os dados operacionais, mas nao retornou itens estruturados de cobertura nesta consulta.")
            if pack.get("official_document_source_available"):
                lines.append("- Ha fonte documental oficial disponivel, mas ela ainda nao foi processada nesta consulta.")
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
            from app.api.infocap_connector import _display_policy_number

            num = _display_policy_number(sel)
            titular = sel.get("holder_name") or sel.get("holder_name_masked") or "-"
            doc = sel.get("document") or r.get("client_document")
            active_now = sel.get("active_now")
            active_text = (
                "ativa"
                if active_now is True
                else "nao ativa"
                if active_now is False
                else "situacao de vigencia nao confirmada"
            )
            lines = [
                "Apolice localizada na InfoCap:",
                f"- Seguradora: {sel.get('insurer_key') or '-'} - Produto: {sel.get('product') or '-'}",
                f"- Numero da apolice: {num} - Titular: {titular}" + (f" - CPF/CNPJ: {doc}" if doc else ""),
                f"- Situacao: {sel.get('policy_status') or '-'} ({active_text}) - Vigencia: {sel.get('valid_from') or '-'} a {sel.get('valid_to') or '-'}",
            ]
            if pack.get("structured_coverage_absent"):
                if pack.get("document_evidence_ready"):
                    lines.extend(InfocapPolicyLookupTool._document_evidence_lines(pack))
                else:
                    lines.append("- A InfoCap confirmou a apolice e seus dados operacionais, mas nao retornou itens estruturados de cobertura, franquia ou assistencia nesta consulta. Nao vou concluir cobertura sem essa evidencia.")
                    if pack.get("official_document_source_available"):
                        lines.append("- Existe uma fonte documental oficial disponivel; ela ainda nao foi processada nesta consulta.")
            return "\n".join(lines) + cli
        if status in ("multiple_matches", "ambiguous_customer", "ambiguous_policy", "policy_number_ambiguous"):
            from app.api.infocap_connector import _format_policy_options_for_summary

            options = _format_policy_options_for_summary(r.get("matches") or [])
            base = "Encontrei mais de uma apolice/cliente para esse termo. Escolha pelo numero humano da apolice antes de detalhar."
            return (base + ("\n" + options if options else "") + cli).strip()
        if status == "identity_mismatch":
            return "A identidade da apolice nao foi confirmada. Por seguranca, nao vou exibir detalhes, cobertura, parcelas ou documento dessa consulta."
        if status == "policy_number_not_found":
            return "Nao localizei apolice com esse numero humano na InfoCap."
        if status in ("not_found", "client_found"):
            return ("Cliente localizado, mas sem apolice/documento vinculado retornado." + cli) if status == "client_found" else "Nao localizei cliente/apolice para esse termo na InfoCap."
        if status == "source_limited":
            return "A InfoCap respondeu, mas nao retornou dados suficientes para selecionar uma apolice unica. Refine com CPF, nome completo ou numero humano da apolice."
        if status in ("blocked_not_configured", "blocked_missing_credentials"):
            return "A InfoCap nao esta totalmente configurada para a sua corretora: credencial/base ausente."
        if status == "ambiguous_connection":
            return "Ha mais de uma conexao InfoCap elegivel. E necessario limpar as conexoes duplicadas antes da consulta."
        return "Nao foi possivel concluir a consulta na InfoCap agora."
