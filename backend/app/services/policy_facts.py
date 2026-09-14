"""Policy Facts mínimos (SPEC-016 E2) — fatos tipados extraídos do evidence pack.

Módulo PURO (sem I/O, sem provider, sem LLM). Converte o evidence pack canônico
da leitura de apólice (InfoCap estruturada + evidência documental R1C.1) em uma
lista de fatos tipados com fonte, confiança e rastreabilidade.

Regras duras herdadas de P0/R1B (irreversíveis):
- código curto (ex.: "P", "A1") nunca vira label de fact;
- campo financeiro sem semântica comprovada (provider_field) nunca vira fact;
- fact de documento oficial exige página + trecho;
- ausência de dados = lista vazia (nunca inventa fato);
- facts nunca carregam CPF/nome do titular (isso fica no DTO por papel).
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

#: 🔴 O nome do FORNECEDOR saiu de dentro do modelo do DOMÍNIO
#: (SPEC-EXTRA-001.1 §5.3). O valor canônico chamava-se `infocap_structured`:
#: numa corretora que usasse Quiver, o fato de uma cobertura continuaria
#: dizendo que veio da InfoCap. É o tipo de defeito que, não corrigido agora,
#: "reinfecta todo leitor seguinte" (CLAUDE.md §12.1).
FACT_SOURCES = ("sistema_de_gestao", "documento_oficial", "regra_de_apolice")

#: **Expand-first, e o antigo continua sendo LIDO** (CLAUDE.md §8). Os novos
#: valores passam a ser escritos; os leitores aceitam os dois por `fonte_canonica`,
#: com o antigo registrado em log. 📊 Não há backfill de banco a fazer: medido no
#: BLOCO 0 (premissa 7) — `grep -rn "policy_facts|fact_type" backend/app` → os
#: facts vivem em MEMÓRIA, dentro do turno; nenhuma tabela os persiste.
FONTES_LEGADAS = {
    "infocap_structured": "sistema_de_gestao",
    "official_document": "documento_oficial",
    "policy_rule": "regra_de_apolice",
}


def fonte_canonica(valor: Any) -> str:
    """O valor antigo de `source` → o novo. O que já é novo passa direto.

    ⚠️ Um valor desconhecido **volta como veio**: converter o que não se
    reconhece esconderia a fonte nova de quem a lê.
    """
    texto = str(valor or "").strip()
    novo = FONTES_LEGADAS.get(texto)
    if novo is None:
        return texto
    logger.info("[POLICY FACTS] fonte legada %r lida como %r", texto, novo)
    return novo


FACT_TYPES = (
    "coverage",
    "assistance",
    "deductible",
    "limit",
    "installment",
    "exclusion",
    "premium",
    "validity",
    "clause",
)

# evidence_type (R1C.1) -> fact_type canônico
_EVIDENCE_TYPE_TO_FACT_TYPE = {
    "coverage": "coverage",
    "assistance": "assistance",
    "deductible": "deductible",
    "lmi": "limit",
    "premium": "premium",
    "installment": "installment",
    "clause": "clause",
    "exclusion": "exclusion",
}

_ASSISTANCE_LABEL_RE = re.compile(r"assist[êe]ncia", re.IGNORECASE)


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _locator_hash(pack: Dict[str, Any]) -> Optional[str]:
    locator = pack.get("policy_locator") if isinstance(pack, dict) else None
    if not isinstance(locator, dict):
        return None
    provider = str(locator.get("provider") or "").strip().lower()
    codfil = str(locator.get("codfil") or "").strip()
    nosnum = str(locator.get("nosnum") or "").strip()
    if not provider or not codfil or not nosnum:
        return None
    return hashlib.sha256(f"{provider}:{codfil}:{nosnum}".encode("utf-8")).hexdigest()[:24]


def _is_human_label(label: str) -> bool:
    """Label humano comprovado: nunca código curto/sigla sem dicionário."""
    text = str(label or "").strip()
    if len(text) < 4:
        return False
    letters = [ch for ch in text if ch.isalpha()]
    return len(letters) >= 4


def _fact(
    *,
    fact_type: str,
    label: str,
    value: Any,
    source: str,
    source_detail: Optional[Dict[str, Any]] = None,
    confidence: str = "medium",
    locator_hash: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "fact_type": fact_type,
        "label": str(label or "").strip(),
        "value": value,
        "source": source,
        "source_detail": dict(source_detail or {}),
        "confidence": confidence,
        "policy_locator_hash": locator_hash,
    }


def _facts_from_sections(pack: Dict[str, Any], locator_hash: Optional[str]) -> List[Dict[str, Any]]:
    facts: List[Dict[str, Any]] = []
    for section in pack.get("coverage_sections") or []:
        if not isinstance(section, dict):
            continue
        label = str(section.get("label") or "").strip()
        if not _is_human_label(label):
            continue
        fact_type = "assistance" if _ASSISTANCE_LABEL_RE.search(label) else "coverage"
        # A cobertura estruturada da InfoCap (`/itens.garantias`) traz prêmio e
        # franquia POR cobertura. Sem carregá-los aqui, o fato chegava à LLM só
        # com o limite — e a franquia, que era a pergunta, sumia no caminho.
        detail: Dict[str, Any] = {"provider_field": section.get("source") or "coverage_sections"}
        if section.get("premium"):
            detail["premium"] = section.get("premium")
        if section.get("deductible"):
            detail["participation"] = section.get("deductible")
        facts.append(
            _fact(
                fact_type=fact_type,
                label=label,
                value=section.get("amount"),
                source="sistema_de_gestao",
                source_detail=detail,
                confidence="high",
                locator_hash=locator_hash,
            )
        )
        if section.get("deductible"):
            facts.append(
                _fact(
                    fact_type="deductible",
                    label=f"Franquia — {label}",
                    value=section.get("deductible"),
                    source="sistema_de_gestao",
                    source_detail={"provider_field": section.get("source") or "coverage_sections"},
                    confidence="high",
                    locator_hash=locator_hash,
                )
            )
    return facts


def _facts_from_document_evidence(pack: Dict[str, Any], locator_hash: Optional[str]) -> List[Dict[str, Any]]:
    evidence = pack.get("official_policy_document_evidence")
    if not isinstance(evidence, dict):
        return []
    try:
        from app.services.policy_document_evidence_service import is_boilerplate_fragment
    except Exception:  # noqa: BLE001 — defesa em profundidade opcional
        is_boilerplate_fragment = lambda _t: False  # noqa: E731

    facts: List[Dict[str, Any]] = []
    for item in evidence.get("evidence_items") or []:
        if not isinstance(item, dict):
            continue
        fact_type = _EVIDENCE_TYPE_TO_FACT_TYPE.get(str(item.get("evidence_type") or "").strip().lower())
        if not fact_type:
            continue
        page = item.get("page_number")
        snippet = str(item.get("evidence_text") or "").strip()
        # Regra dura: fact documental exige página E trecho.
        if not isinstance(page, int) or page < 1 or not snippet:
            continue
        # SPEC-016.1 D2: boilerplate nunca vira fact (mesmo vindo de cache legado).
        if is_boilerplate_fragment(snippet):
            continue
        confidence = str(item.get("confidence") or "medium").strip().lower()
        if confidence not in ("high", "medium", "low"):
            confidence = "medium"
        detail_base = {"page": page, "snippet": snippet}

        structured = item.get("structured") if isinstance(item.get("structured"), dict) else {}
        kind = str(structured.get("kind") or "")
        if kind == "coverage_row":
            label = str(structured.get("label") or snippet[:80])
            facts.append(
                _fact(
                    fact_type="coverage",
                    label=label,
                    value=structured.get("lmi"),
                    source="documento_oficial",
                    source_detail={**detail_base, "premium": structured.get("premium"), "participation": structured.get("participation")},
                    confidence="high",
                    locator_hash=locator_hash,
                )
            )
            if structured.get("participation"):
                facts.append(
                    _fact(
                        fact_type="deductible",
                        label=f"Franquia — {label}",
                        value=structured.get("participation"),
                        source="documento_oficial",
                        source_detail=detail_base,
                        confidence="high",
                        locator_hash=locator_hash,
                    )
                )
            continue
        if kind == "assistance_plan":
            facts.append(
                _fact(
                    fact_type="assistance",
                    label=str(structured.get("plan") or snippet[:80]),
                    value=structured.get("premium"),
                    source="documento_oficial",
                    source_detail=detail_base,
                    confidence="high",
                    locator_hash=locator_hash,
                )
            )
            continue
        if kind == "assistance_services":
            services = structured.get("services") or []
            facts.append(
                _fact(
                    fact_type="assistance",
                    label="Serviços do plano de assistência",
                    value="; ".join(str(s) for s in services),
                    source="documento_oficial",
                    source_detail=detail_base,
                    confidence="high",
                    locator_hash=locator_hash,
                )
            )
            continue
        if kind == "policy_limit":
            facts.append(
                _fact(
                    fact_type="limit",
                    label="Limite máximo de garantia da apólice (LMGA)",
                    value=structured.get("amount"),
                    source="documento_oficial",
                    source_detail=detail_base,
                    confidence="high",
                    locator_hash=locator_hash,
                )
            )
            continue

        label = snippet[:80]
        facts.append(
            _fact(
                fact_type=fact_type,
                label=label,
                value=None,
                source="documento_oficial",
                source_detail=detail_base,
                confidence=confidence,
                locator_hash=locator_hash,
            )
        )
    return facts


def _validity_fact(pack: Dict[str, Any], locator_hash: Optional[str]) -> List[Dict[str, Any]]:
    valid_from = str(pack.get("valid_from") or "").strip()
    valid_to = str(pack.get("valid_to") or "").strip()
    if not valid_from and not valid_to:
        return []
    value = f"{valid_from or '?'} a {valid_to or '?'}"
    return [
        _fact(
            fact_type="validity",
            label="Vigência da apólice",
            value=value,
            source="sistema_de_gestao",
            source_detail={"provider_field": "valid_from/valid_to"},
            confidence="high",
            locator_hash=locator_hash,
        )
    ]


def extract_policy_facts(pack: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extrai Policy Facts tipados do evidence pack canônico.

    Nunca inventa: sem seção estruturada, sem evidência documental com página e
    sem vigência → lista vazia. Campos financeiros `provider_field` são
    ignorados até existir semântica comprovada por contrato.
    """
    if not isinstance(pack, dict):
        return []
    locator_hash = _locator_hash(pack)
    facts: List[Dict[str, Any]] = []
    facts.extend(_facts_from_sections(pack, locator_hash))
    facts.extend(_facts_from_document_evidence(pack, locator_hash))
    facts.extend(_validity_fact(pack, locator_hash))
    return facts


def has_confirmed_assistance(facts: List[Dict[str, Any]]) -> bool:
    """Assistência confirmada = fact assistance com confiança alta/média.

    Usado pela política residential_24h_standard_v1 (E3). Ramo/produto sozinho
    NUNCA confirma assistência (G37/G72).
    """
    for fact in facts or []:
        if not isinstance(fact, dict):
            continue
        if fact.get("fact_type") != "assistance":
            continue
        # ⚠️ Expand-first: o fact antigo (`infocap_structured`) continua sendo
        # ACEITO enquanto houver quem o escreva — 📊 `assistance_policy.py:132`
        # ainda escreve `policy_rule`. Rejeitá-lo aqui apagaria a assistência
        # confirmada de um turno inteiro, em silêncio.
        if fonte_canonica(fact.get("source")) not in FACT_SOURCES:
            continue
        if str(fact.get("confidence") or "").lower() in ("high", "medium"):
            return True
    return False
