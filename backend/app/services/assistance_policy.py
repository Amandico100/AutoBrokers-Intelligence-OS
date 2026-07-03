"""Política governada de assistência residencial (SPEC-016 E3).

residential_24h_standard_v1 — regra de negócio do Founder, versionada em código
(migração para tabela `platform_policies` com overrides por seguradora/produto/
plano/corretora está prevista para quando o primeiro override existir; ver
FABLE_RECOVERY_PROGRAM.md D7).

Módulo PURO (sem I/O, sem LLM). A LLM nunca decide a regra — apenas redige
sobre o resultado. Toda aplicação gera trace auditável.

Gatilho (TODAS as condições):
  1. apólice do ramo residencial confirmada pela fonte;
  2. Policy Fact de assistência confirmado (estruturado ou documental);
  3. apólice não cancelada e não fora de vigência.
Ramo/produto sozinho NUNCA dispara a política (G37/G72).
"""

from __future__ import annotations

import unicodedata
from typing import Any, Dict, List

from app.services.policy_facts import has_confirmed_assistance

RULE_ID = "residential_24h_standard_v1"
RULE_VERSION = 1

STANDARD_SERVICES = ("eletricista", "chaveiro", "hidraulica_encanador")

SERVICE_LABELS = {
    "eletricista": "eletricista",
    "chaveiro": "chaveiro",
    "hidraulica_encanador": "hidráulica/encanador",
}

STATEMENT = (
    "Com a Assistência 24h confirmada nesta apólice residencial, os serviços "
    "padrão de assistência incluem eletricista, chaveiro e hidráulica/encanador."
)


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _is_residential(pack: Dict[str, Any]) -> bool:
    for key in ("line_kind_detected", "product_detected", "ramo", "line_kind"):
        if "residencial" in _strip_accents(str(pack.get(key) or "")):
            return True
    return False


def _is_operational(pack: Dict[str, Any]) -> bool:
    if bool(pack.get("cancelled")):
        return False
    if pack.get("active_now") is False:
        return False
    return True


def apply_residential_assistance_policy(
    pack: Dict[str, Any], facts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Avalia a política sobre o pack + facts. Determinístico e auditável."""
    pack = pack if isinstance(pack, dict) else {}
    facts = facts if isinstance(facts, list) else []

    residential = _is_residential(pack)
    assistance_confirmed = has_confirmed_assistance(facts)
    operational = _is_operational(pack)

    applied = residential and assistance_confirmed and operational
    if applied:
        reason = "residencial + assistência confirmada + apólice operacional"
    elif not residential:
        reason = "apólice não é do ramo residencial"
    elif not assistance_confirmed:
        reason = "assistência não confirmada por fact estruturado/documental (ramo sozinho não basta)"
    else:
        reason = "apólice cancelada ou fora de vigência"

    facts_used = [
        {
            "fact_type": f.get("fact_type"),
            "label": f.get("label"),
            "source": f.get("source"),
            "confidence": f.get("confidence"),
        }
        for f in facts
        if isinstance(f, dict) and f.get("fact_type") == "assistance"
    ]

    return {
        "applied": applied,
        "rule_id": RULE_ID,
        "version": RULE_VERSION,
        "services": list(STANDARD_SERVICES) if applied else [],
        "statement": STATEMENT if applied else None,
        "reason": reason,
        "facts_used": facts_used,
        "trace": {
            "rule_id": RULE_ID,
            "version": RULE_VERSION,
            "residential": residential,
            "assistance_confirmed": assistance_confirmed,
            "operational": operational,
            "facts_used": facts_used,
        },
    }


def policy_rule_facts(policy_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Facts derivados da política aplicada (source=policy_rule), para o compositor."""
    if not isinstance(policy_result, dict) or not policy_result.get("applied"):
        return []
    locator_hash = None
    facts: List[Dict[str, Any]] = []
    for service in policy_result.get("services") or []:
        facts.append(
            {
                "fact_type": "assistance",
                "label": f"Serviço padrão de assistência: {SERVICE_LABELS.get(service, service)}",
                "value": service,
                "source": "policy_rule",
                "source_detail": {
                    "rule_id": policy_result.get("rule_id"),
                    "version": policy_result.get("version"),
                },
                "confidence": "high",
                "policy_locator_hash": locator_hash,
            }
        )
    return facts
