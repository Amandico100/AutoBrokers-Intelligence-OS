"""Política governada de assistência residencial (SPEC-016 E3).

🔴 DESDE A SPEC-EXTRA-001.5 ESTE MÓDULO É **FALLBACK**, e está marcado como tal.

*"A migração para tabela `platform_policies` com overrides por seguradora/
produto/plano/corretora está prevista para quando o primeiro override
existir"*, dizia o cabeçalho abaixo. **O primeiro override é a SPEC-EXTRA-001.5**
(§6.4): a base `insurer_assistance_plans`/`insurer_assistance_services`.

A ordem passa a ser:

```
1. a BASE, por `services/skills/cobertura_e_assistencia.py`   -> origem='base'
2. só se NÃO houver linha publicada, E a apólice for residencial com
   assistência confirmada, E o serviço for um dos TRÊS daqui
   -> esta regra, MARCADA `origem='regra_generica'`, `confianca='baixa'`,
      e o texto diz que é padrão de MERCADO, não o contrato dele
```

⛔ Este arquivo **não é apagado** e **não ganha serviço novo**. Serviço novo vai
para a base, com documento e página. 📊 O que ele conhece são três
(`STANDARD_SERVICES`), e foi exatamente por responder "sim" a um quarto — carro
reserva, 94 mensagens medidas no acervo — que a 001.5 existe.

residential_24h_standard_v1 — regra de negócio do Founder, versionada em código.

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
from typing import Any, Dict, List, Optional

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
    """Residencial confirmado pela fonte — inclusive abreviações do provider
    (SPEC-016.1 D1: InfoCap retorna ramo_abrev "RESI")."""
    for key in ("line_kind_detected", "product_detected", "ramo", "line_kind"):
        norm = _strip_accents(str(pack.get(key) or ""))
        if not norm:
            continue
        if "resid" in norm:  # residencial, residência, residencia digital...
            return True
        if any(token == "resi" or token.startswith("resid") for token in norm.replace("/", " ").split()):
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


def policy_rule_facts(policy_result: Dict[str, Any],
                      pack: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Facts derivados da política aplicada (source=policy_rule), para o compositor.

    `pack` é opcional e serve para AMARRAR o fact à apólice (ver dentro)."""
    if not isinstance(policy_result, dict) or not policy_result.get("applied"):
        return []
    # 🔴 SPEC-EXTRA-001.5 §6.4: o fact da regra PERDIA o vínculo com a apólice.
    #
    # 📊 Até 17/09/2026 esta linha era `locator_hash = None`, fixo. Todo fact
    # derivado da política nascia órfão: nenhuma das telas ou consultas que
    # agrupam facts por `policy_locator_hash` conseguia dizer de QUAL apólice a
    # afirmação "tem eletricista" tinha saído. ⚠️ Um fact sem dono é
    # indistinguível de um fact de outra pessoa.
    #
    # O `pack` chega opcional para não quebrar chamador nenhum: sem ele o
    # comportamento é o de antes (None), e é o dono do pack que liga o vínculo.
    locator_hash = None
    if isinstance(pack, dict) and pack:
        from app.services.policy_facts import _locator_hash

        locator_hash = _locator_hash(pack)
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
