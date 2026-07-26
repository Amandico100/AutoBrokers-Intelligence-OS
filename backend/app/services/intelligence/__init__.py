"""Intelligence Fabric — SPEC-059.

O pipeline que transforma ruido em prioridade:

    evento → sinal → evidencia → Finding → recomendacao → Work Run → outcome

Nenhum modulo daqui cria runtime. Todos consomem o que ja existe:
execucao pelo **Work OS** (SPEC-055), ferramenta pelo **Tool Gateway**
(SPEC-056), entrega pelo **Artifact Hub** (SPEC-057), automacao proposta pela
**Auxiliary Factory** (SPEC-058) e conhecimento pelo caminho da **SPEC-052**.

A regra que organiza o pacote inteiro: **a LLM sintetiza, os dados e as regras
comprovam**. Contagem, prazo, limiar, variacao e dedupe sao codigo
deterministico. O modelo entra para redigir e explicar — nunca para decidir
que um alerta critico existe.
"""

from __future__ import annotations

__all__ = [
    "schemas",
    "redaction_service",
    "policy",
    "signal_service",
    "evidence_service",
    "dedupe_service",
    "priority_service",
    "rule_engine",
    "finding_engine",
    "recommendation_service",
    "outcome_service",
    "feedback_service",
    "delivery_policy",
    "briefing_service",
    "garimpo_v3",
    "demand_cluster_service",
    "knowledge_candidate_adapter",
    "legacy_adapter",
    "event_adapter",
]
