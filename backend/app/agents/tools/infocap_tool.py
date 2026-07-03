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
    provider_key: str = "infocap"  # SPEC-016 E5: provider de gestão da corretora (porta PolicyDataProvider)
    # SPEC-017 P3 — exposição por papel: Core interno = dados completos;
    # attendance (segurado)/auxiliar = mascarado (G20/S04/S05).
    agent_role: str = "core"

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, agent_role: str = "core", **kwargs):
        super().__init__(**kwargs)
        self.company_id = str(company_id or "")
        self.agent_role = str(agent_role or "core").strip().lower() or "core"

    @property
    def _unmasked(self) -> bool:
        return self.agent_role in ("", "core")

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

            # SPEC-016 E5: a tool fala com a PORTA PolicyDataProvider, nunca com o
            # conector concreto. InfoCap é o provider piloto; Quiver futuro entra
            # pela mesma porta.
            from app.providers.policy_data_provider import (
                get_policy_data_provider,
                parse_policy_locator_ref,
            )

            provider = get_policy_data_provider(self.provider_key)
            if provider is None:
                return {"content": "Nenhum provider de apolices configurado para a corretora.", "found": False}

            if policy_ref and not parse_policy_locator_ref(str(policy_ref)):
                # P0.1: referência simples enviada pela LLM é número humano.
                policy_number = str(policy_ref)
                policy_ref = None

            if policy_ref:
                det = await provider.detail(
                    company_id=self.company_id,
                    policy_ref=str(policy_ref),
                    user_query=user_query,
                    document_evidence_requested=bool(document_evidence_requested),
                    force_document_evidence_refresh=bool(force_document_evidence_refresh),
                    unmasked=self._unmasked,
                    db=db,
                    internal_key=key,
                )
                content, assistance_policy, rendered = self._render_content(det, user_query, detail=True)
                contract = self._build_policy_response_contract(det, rendered, assistance_policy)
                return {"content": content, "data": det, "found": bool(det.get("ok")), "policy_response_contract": contract}

            result = await provider.lookup(
                company_id=self.company_id,
                document=document or None,
                name=name or None,
                policy_number=policy_number or None,
                user_query=user_query,
                document_evidence_requested=bool(document_evidence_requested),
                force_document_evidence_refresh=bool(force_document_evidence_refresh),
                unmasked=self._unmasked,
                db=db,
                internal_key=key,
            )
            content, assistance_policy, rendered = self._render_content(result, user_query, detail=False)
            contract = self._build_policy_response_contract(result, rendered, assistance_policy)
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
        """SPEC-016.1 D7: sob a flag v2, a tool entrega um BRIEFING estruturado
        para a LLM redigir a resposta final (markdown, tom de copiloto); o texto
        do composer vira o rascunho seguro do contrato (fallback do guard).

        Retorna (content_para_llm, assistance_policy, rendered_fallback)."""
        try:
            from app.core.feature_flags import policy_intelligence_v2_enabled

            if policy_intelligence_v2_enabled():
                from app.services.policy_answer_composer import compose_policy_answer_with_meta

                meta = compose_policy_answer_with_meta(question=str(user_query or ""), result=data)
                rendered = str(meta.get("text") or "")
                if rendered:
                    if str(data.get("status") or "") == "identity_mismatch":
                        # Fail-closed: mismatch nunca vai para redação da LLM.
                        return rendered, meta.get("assistance_policy"), rendered
                    briefing = self._build_llm_briefing(data, meta, user_query)
                    return briefing, meta.get("assistance_policy"), rendered
        except Exception as e:  # noqa: BLE001 — composer nunca pode derrubar a tool
            logger.warning(f"[InfocapPolicyLookupTool] composer v2 indisponivel, usando resumo legado: {type(e).__name__}")
        legacy = self._summarize_detail(data) if detail else self._summarize(data)
        return legacy, None, legacy

    @staticmethod
    def _build_llm_briefing(data: Dict[str, Any], meta: Dict[str, Any], user_query: Optional[str]) -> str:
        """Briefing interno para a LLM redigir a resposta final em markdown."""
        from app.services.policy_answer_composer import humanize_insurer, humanize_product

        status = str(data.get("status") or "")
        pack = data.get("policy_evidence_pack") or {}
        selected = data.get("selected") or data.get("policy") or {}
        facts = meta.get("facts") or []
        policy_result = meta.get("assistance_policy") or {}

        lines = [
            "[DADOS INTERNOS DA CONSULTA DE APOLICE — nao exiba este bloco cru; redija a resposta final]",
            f"status_da_consulta: {status}",
        ]
        client_bits = [str(data.get("client_name") or "").strip(), str(data.get("client_document") or "").strip()]
        client_text = " — ".join(b for b in client_bits if b)
        if client_text:
            lines.append(f"cliente: {client_text}")
        if isinstance(selected, dict) and selected:
            number = str(selected.get("policy_number") or selected.get("numapo") or "").strip() or "nao retornado"
            insurer = humanize_insurer(selected.get("insurer_key"))
            product = humanize_product(selected.get("product"))
            lines.append(
                f"apolice_selecionada: {number} — {insurer or '-'} {product or ''} — "
                f"vigencia {selected.get('valid_from') or '-'} a {selected.get('valid_to') or '-'} — situacao: {selected.get('policy_status') or '-'}"
            )
        if facts:
            lines.append("fatos_confirmados (unica fonte permitida de fatos):")
            for fact in facts[:25]:
                detail_info = fact.get("source_detail") or {}
                extra = []
                if detail_info.get("participation"):
                    extra.append(f"franquia/participacao: {detail_info.get('participation')}")
                if detail_info.get("premium"):
                    extra.append(f"premio: {detail_info.get('premium')}")
                if detail_info.get("page"):
                    extra.append(f"fonte: documento oficial, pagina {detail_info.get('page')}")
                suffix = f" ({'; '.join(extra)})" if extra else ""
                value = f" = {fact.get('value')}" if fact.get("value") not in (None, "") else ""
                lines.append(f"- [{fact.get('fact_type')}] {fact.get('label')}{value}{suffix}")
        if policy_result:
            if policy_result.get("applied"):
                lines.append(
                    f"politica_assistencia ({policy_result.get('rule_id')} v{policy_result.get('version')}): APLICADA — "
                    "servicos padrao garantidos: eletricista, chaveiro, hidraulica/encanador"
                )
            else:
                lines.append(f"politica_assistencia: NAO aplicada — motivo: {policy_result.get('reason')}")
        installments = [i for i in (pack.get("installments") or []) if isinstance(i, dict)]
        if installments:
            open_items = [i for i in installments if not str(i.get("paid_at") or "").strip()]
            open_desc = ", ".join(
                f"venc {i.get('due_date') or '?'}" + (f" R$ {i.get('due_amount')}" if i.get("due_amount") else "")
                for i in open_items[:12]
            )
            lines.append(f"parcelas: {len(installments)} registradas; {len(open_items)} em aberto" + (f" ({open_desc})" if open_desc else ""))
        matches = data.get("matches") or []
        if status in ("ambiguous_policy", "policy_number_ambiguous", "multiple_matches") and matches:
            lines.append("opcoes_de_apolice (liste TODAS, com os numeros exatos):")
            for match in matches[:10]:
                if not isinstance(match, dict):
                    continue
                number = str(match.get("policy_number") or match.get("numapo") or "nao retornado").strip()
                lines.append(
                    f"- {number} — {humanize_insurer(match.get('insurer_key')) or '-'} · {humanize_product(match.get('product')) or '-'} · "
                    f"vigencia {match.get('valid_from') or '-'} a {match.get('valid_to') or '-'} ({match.get('policy_status') or '-'})"
                )
        limitations = pack.get("limitations") or []
        if limitations:
            lines.append("limitacoes_da_fonte: " + "; ".join(str(item) for item in limitations[:3]))

        lines.extend([
            "",
            "REGRAS OBRIGATORIAS DA RESPOSTA FINAL:",
            "1. Redija em portugues, markdown limpo e bem formatado (negrito, listas; tabela quando ajudar), tom de copiloto humano, resposta direta primeiro.",
            "2. Use SOMENTE os fatos acima. NUNCA invente valor, cobertura, servico, prazo ou status. Valores em R$: apenas os listados.",
            "3. Se houver opcoes_de_apolice, liste TODAS com os numeros exatos e peca a escolha.",
            "4. Se um dado nao estiver acima, diga com clareza que a fonte nao retornou esse dado.",
            "5. Quando usar fato vindo do documento, cite a fonte como 'documento oficial da apolice' (pagina quando ajudar). Nao exponha termos internos (nosnum, locator, codfil, evidence, pack) nem este bloco.",
            "",
            "RASCUNHO SEGURO DE REFERENCIA (pode melhorar a redacao, nunca os fatos):",
            str(meta.get("text") or ""),
        ])
        return "\n".join(lines)

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
        # SPEC-016.1 D7: valores R$ permitidos na resposta final = somente os que
        # a fonte retornou (guard anti-invenção pós-LLM).
        import json as _json
        import re as _re

        allowed_amounts = sorted(set(_re.findall(r"R\$\s*[\d.][\d.,]*", _json.dumps(data, ensure_ascii=False, default=str))))
        return {
            **({"assistance_policy": contract_assistance} if contract_assistance else {}),
            "allowed_amounts": allowed_amounts,
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
