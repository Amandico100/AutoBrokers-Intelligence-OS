"""Compositor humano de resposta de apólice (SPEC-016 E4).

Módulo PURO. Transforma o resultado canônico da leitura de apólice em uma
resposta de copiloto: direta, com fonte, sem jargão técnico e sem inventar.

Regras:
- resposta direta primeiro (a pergunta do corretor manda);
- fonte citada: item estruturado da InfoCap ou documento oficial com página;
- ausência honesta quando a fonte não confirmar;
- opções numeradas em ambiguidade (número humano, seguradora, produto, vigência);
- NUNCA expor termos internos: nosnum, locator, codfil, evidence pack, DTO;
- fail-closed preservado em identity_mismatch (nenhum dado da apólice).

O texto produzido vira o `rendered_safe_answer` do Policy Response Contract —
o output guard existente continua sendo o mecanismo de imposição.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

from app.services.assistance_policy import apply_residential_assistance_policy, policy_rule_facts
from app.services.policy_facts import extract_policy_facts, has_confirmed_assistance

_INVALID_NUMBERS = {"", "0", "none", "null", "-"}

_ASSIST_INTENT_RE = re.compile(
    r"assist[êe]ncia|eletricista|chaveiro|encanador|hidr[áa]ulic|24\s*h", re.IGNORECASE
)
_COVERAGE_INTENT_RE = re.compile(r"cobertura|coberturas|garantia|garantias|\bcobre\b|coberto|coberta", re.IGNORECASE)
_DEDUCTIBLE_INTENT_RE = re.compile(r"franquia", re.IGNORECASE)
_INSTALLMENT_INTENT_RE = re.compile(r"parcela", re.IGNORECASE)


def _norm(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _display_number(record: Dict[str, Any]) -> str:
    number = str(record.get("policy_number") or record.get("numapo") or "").strip()
    if _norm(number) in _INVALID_NUMBERS:
        return "número não retornado pela fonte"
    return number


def _policy_header(selected: Dict[str, Any]) -> str:
    insurer = str(selected.get("insurer_key") or selected.get("insurer_detected") or "").strip()
    product = str(selected.get("product") or selected.get("product_detected") or "").strip()
    parts = [p for p in (product, insurer and f"({insurer})") if p]
    return " ".join(parts) if parts else "a apólice consultada"


def _client_line(result: Dict[str, Any]) -> Optional[str]:
    name = str(result.get("client_name") or "").strip()
    doc = str(result.get("client_document") or "").strip()
    if not name and not doc:
        return None
    pieces = [p for p in (name, doc and f"CPF/CNPJ {doc}") if p]
    return "Cliente: " + " — ".join(pieces) + "."


def _structured_assistance_labels(facts: List[Dict[str, Any]]) -> List[str]:
    return [
        str(f.get("label") or "").strip()
        for f in facts
        if f.get("fact_type") == "assistance" and f.get("source") == "infocap_structured" and f.get("label")
    ]


def _document_assistance_citations(facts: List[Dict[str, Any]]) -> List[str]:
    citations = []
    for f in facts:
        if f.get("fact_type") != "assistance" or f.get("source") != "official_document":
            continue
        detail = f.get("source_detail") or {}
        page = detail.get("page")
        snippet = str(detail.get("snippet") or "").strip()
        if page and snippet:
            citations.append(f'documento oficial da apólice, página {page}: "{snippet}"')
    return citations


def _service_labels(services: List[str]) -> str:
    labels = {"eletricista": "eletricista", "chaveiro": "chaveiro", "hidraulica_encanador": "hidráulica/encanador"}
    return ", ".join(labels.get(s, s) for s in services)


def _compose_assistance_answer(
    result: Dict[str, Any],
    pack: Dict[str, Any],
    facts: List[Dict[str, Any]],
    policy_result: Dict[str, Any],
) -> str:
    lines: List[str] = []
    if policy_result.get("applied"):
        sources: List[str] = []
        structured = _structured_assistance_labels(facts)
        if structured:
            sources.append(f'item estruturado da fonte: "{structured[0]}"')
        sources.extend(_document_assistance_citations(facts)[:1])
        source_text = "; ".join(sources) if sources else "fonte da apólice"
        lines.append(
            f"Sim — esta apólice residencial tem assistência confirmada ({source_text})."
        )
        lines.append(
            f"Pela política padrão de Assistência 24h residencial, os serviços incluídos são: {_service_labels(policy_result.get('services') or [])}."
        )
    elif has_confirmed_assistance(facts):
        structured = _structured_assistance_labels(facts)
        doc_citations = _document_assistance_citations(facts)
        source_text = structured[0] if structured else (doc_citations[0] if doc_citations else "fonte da apólice")
        lines.append(f'Sim — a apólice registra assistência confirmada ({source_text}).')
        lines.append(
            "Como não é uma apólice residencial, os serviços exatos dependem do plano contratado — posso detalhar pelo documento oficial se precisar."
        )
    else:
        lines.append(
            "Não encontrei confirmação de assistência nesta apólice: a fonte não retornou itens estruturados de assistência nesta consulta."
        )
        if pack.get("official_document_source_available") and not pack.get("document_evidence_ready"):
            lines.append(
                "Existe o documento oficial da apólice disponível — se quiser, eu busco e verifico a assistência direto nele."
            )
        else:
            lines.append(
                "Para confirmar com segurança, posso verificar o documento oficial da apólice assim que ele estiver disponível."
            )
    return "\n".join(lines)


def _compose_coverage_answer(pack: Dict[str, Any], facts: List[Dict[str, Any]]) -> str:
    coverage_facts = [f for f in facts if f.get("fact_type") == "coverage"]
    structured = [f for f in coverage_facts if f.get("source") == "infocap_structured"]
    lines: List[str] = []
    if structured:
        lines.append("As coberturas registradas na apólice são:")
        for f in structured[:20]:
            amount = f.get("value")
            lines.append(f"- {f.get('label')}" + (f" — {amount}" if amount else ""))
    else:
        doc_facts = [f for f in coverage_facts if f.get("source") == "official_document"]
        if doc_facts:
            lines.append("Encontrei estas coberturas no documento oficial da apólice:")
            for f in doc_facts[:10]:
                detail = f.get("source_detail") or {}
                lines.append(f'- página {detail.get("page")}: "{detail.get("snippet")}"')
        else:
            lines.append(
                "A fonte confirmou a apólice, mas não retornou itens estruturados de cobertura nesta consulta — não vou listar cobertura sem essa evidência."
            )
            if pack.get("official_document_source_available"):
                lines.append("Posso verificar o documento oficial da apólice para trazer as coberturas com página e trecho.")
    return "\n".join(lines)


def _compose_operational_summary(result: Dict[str, Any], pack: Dict[str, Any]) -> str:
    selected = result.get("selected") or result.get("policy") or {}
    header = _policy_header({**selected, **pack})
    number = _display_number({**pack, **selected})
    status = str(selected.get("policy_status") or pack.get("policy_status") or "").strip() or "situação não informada"
    valid_from = selected.get("valid_from") or pack.get("valid_from") or "-"
    valid_to = selected.get("valid_to") or pack.get("valid_to") or "-"
    holder = str(selected.get("holder_name") or "").strip()
    lines = [
        f"Encontrei a apólice {number} — {header}.",
        f"Situação: {status} · Vigência: {valid_from} a {valid_to}." + (f" Titular: {holder}." if holder else ""),
    ]
    return "\n".join(lines)


def _compose_options(matches: List[Dict[str, Any]]) -> str:
    lines = ["Encontrei mais de uma apólice. Qual delas você quer? Responda com o número da apólice:"]
    for idx, match in enumerate(matches[:10], start=1):
        number = _display_number(match)
        insurer = str(match.get("insurer_key") or "-").strip()
        product = str(match.get("product") or "-").strip()
        valid_from = match.get("valid_from") or "-"
        valid_to = match.get("valid_to") or "-"
        status = str(match.get("policy_status") or "-").strip()
        lines.append(f"{idx}. {number} — {insurer} · {product} · vigência {valid_from} a {valid_to} ({status})")
    return "\n".join(lines)


def compose_policy_answer(*, question: str, result: Dict[str, Any]) -> str:
    """Compõe a resposta operacional humana para o resultado canônico."""
    return compose_policy_answer_with_meta(question=question, result=result)["text"]


def compose_policy_answer_with_meta(*, question: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Como compose_policy_answer, mas retorna também os metadados da política
    de assistência para o Policy Response Contract da tool (E4b)."""
    result = result if isinstance(result, dict) else {}
    status = str(result.get("status") or "").strip()
    question_text = str(question or "")

    def _plain(text: str) -> Dict[str, Any]:
        return {"text": text, "assistance_policy": None}

    if status == "identity_mismatch":
        return _plain(
            "A identidade da apólice não foi confirmada com segurança. "
            "Por proteção, não vou exibir detalhes, cobertura, parcelas ou documento desta consulta. "
            "Me confirme o CPF/nome do cliente e o número da apólice para eu validar de novo."
        )
    if status in ("not_found", "policy_number_not_found"):
        return _plain("Não localizei apólice com esses dados na fonte da corretora. Confira o número ou me passe CPF/nome do cliente.")
    if status in ("multiple_matches", "ambiguous_customer"):
        return _plain("Encontrei mais de um cliente possível para esse termo. Me confirme o CPF ou o nome completo para eu seguir com segurança.")
    if status in ("ambiguous_policy", "policy_number_ambiguous"):
        text = _compose_options(result.get("matches") or [])
        client = _client_line(result)
        return _plain(text + (f"\n{client}" if client else ""))
    if status in ("blocked_not_configured", "blocked_missing_credentials"):
        return _plain("A conexão com o sistema de gestão ainda não está totalmente configurada para a sua corretora. Verifique a conexão em Personalização → Conectores.")
    if status == "ambiguous_connection":
        return _plain("Há mais de uma conexão ativa com o sistema de gestão. É preciso limpar as conexões duplicadas antes da consulta.")
    if status == "source_limited":
        return _plain("A fonte respondeu, mas não consegui isolar uma apólice única. Me passe o CPF, o nome completo do cliente ou o número da apólice.")
    if status == "client_found":
        base = "Localizei o cliente, mas nenhuma apólice vinculada foi retornada pela fonte nesta consulta."
        client = _client_line(result)
        return _plain(base + (f"\n{client}" if client else ""))
    if status != "found":
        return _plain("Não consegui concluir a consulta na fonte da corretora agora. Tente novamente em instantes.")

    pack = result.get("policy_evidence_pack") or {}
    facts = extract_policy_facts(pack)
    policy_result = apply_residential_assistance_policy(pack, facts)
    facts = facts + policy_rule_facts(policy_result)

    if _ASSIST_INTENT_RE.search(question_text):
        body = _compose_assistance_answer(result, pack, facts, policy_result)
    elif _COVERAGE_INTENT_RE.search(question_text):
        body = _compose_coverage_answer(pack, facts)
    elif _DEDUCTIBLE_INTENT_RE.search(question_text):
        deductibles = [f for f in facts if f.get("fact_type") == "deductible"]
        if deductibles:
            lines = ["Sobre franquia, a fonte registra:"]
            for f in deductibles[:5]:
                detail = f.get("source_detail") or {}
                page = detail.get("page")
                lines.append(f"- {f.get('label')}" + (f' (documento oficial, página {page})' if page else ""))
            body = "\n".join(lines)
        else:
            body = "A fonte não retornou franquia estruturada nesta consulta — não vou estimar valor sem evidência."
    elif _INSTALLMENT_INTENT_RE.search(question_text):
        installments = pack.get("installments") or []
        body = (
            f"A fonte retornou {len(installments)} parcela(s) para esta apólice."
            if installments
            else "A fonte não retornou parcelas estruturadas nesta consulta."
        )
    else:
        body = ""

    summary = _compose_operational_summary(result, pack)
    client = _client_line(result)
    parts = [body, summary if not body else None, client]
    # Pergunta específica: corpo primeiro + resumo curto no fim apenas se útil.
    if body:
        header_line = summary.splitlines()[0] if summary else ""
        parts = [body, header_line, client]
    return {
        "text": "\n".join(p for p in parts if p),
        "assistance_policy": policy_result,
    }
