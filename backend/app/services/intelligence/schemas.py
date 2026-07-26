"""Envelope canonico, taxonomias e tiers de confianca. SPEC-059 §7, §8, §9.

Tudo aqui e puro: sem banco, sem rede, sem LLM. E de proposito — o envelope e
a taxonomia sao o contrato que separa "o que aconteceu" de "quem observou", e
um contrato que precisa de infraestrutura para ser testado nao e testado.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Tiers de evidencia — §8.1
# ---------------------------------------------------------------------------

TIER_DADO_VIVO = 0        # banco operacional, conector homologado, Work Run
TIER_EVENTO_SISTEMA = 1   # falha registrada, prazo vencido, contador
TIER_DOCUMENTO = 2        # apolice, condicao geral, evidencia de portal
TIER_ANALISE = 3          # media, variacao, tendencia, cluster, anomalia
TIER_DECLARACAO = 4       # o corretor disse
TIER_INFERENCIA_LLM = 5   # hipotese do modelo

# §8.2: alerta critico exige Tier 0/1/2. Nao ha excecao configuravel — se
# houvesse, ela seria usada no primeiro dia em que alguem quisesse um alerta
# mais "esperto", e a partir dai o corretor recebe P0 baseado em palpite.
TIERS_QUE_SUSTENTAM_FATO = (TIER_DADO_VIVO, TIER_EVENTO_SISTEMA,
                            TIER_DOCUMENTO, TIER_ANALISE)
TIERS_QUE_SUSTENTAM_ALERTA_CRITICO = (TIER_DADO_VIVO, TIER_EVENTO_SISTEMA,
                                      TIER_DOCUMENTO)


def pode_ser_apresentado_como_fato(trust_tier: int) -> bool:
    return trust_tier in TIERS_QUE_SUSTENTAM_FATO


def pode_sustentar_alerta_critico(trust_tier: int) -> bool:
    return trust_tier in TIERS_QUE_SUSTENTAM_ALERTA_CRITICO


# ---------------------------------------------------------------------------
# Taxonomia de sinais — §9
# ---------------------------------------------------------------------------

TIPOS_DE_SINAL: tuple[str, ...] = (
    "operational_backlog",
    "work_failure",
    "work_stale",
    "approval_pending",
    "connection_health",
    "provider_health",
    "budget_risk",
    "data_quality",
    "attendance_quality",
    "customer_experience",
    "portal_blocker",
    "commercial_opportunity",
    "cost_saving_opportunity",
    "process_automation_opportunity",
    "broker_pain",
    "broker_desire",
    "feature_request",
    "repeated_task",
    "knowledge_gap",
    "capability_gap",
    "churn_risk",
    "positive_outcome",
    "compliance_risk",
    "security_risk",
    "research_update_future",
)

# Dominio de cada tipo. Serve para o corretor filtrar em linguagem de negocio
# ("qualidade", "operacao") em vez de por nome tecnico de sinal.
DOMINIO_POR_TIPO: dict[str, str] = {
    "operational_backlog": "operacao",
    "work_failure": "operacao",
    "work_stale": "operacao",
    "approval_pending": "operacao",
    "connection_health": "conexoes",
    "provider_health": "conexoes",
    "budget_risk": "custos",
    "data_quality": "dados",
    "attendance_quality": "qualidade",
    "customer_experience": "qualidade",
    "portal_blocker": "operacao",
    "commercial_opportunity": "comercial",
    "cost_saving_opportunity": "custos",
    "process_automation_opportunity": "automacao",
    "broker_pain": "voz_do_corretor",
    "broker_desire": "voz_do_corretor",
    "feature_request": "voz_do_corretor",
    "repeated_task": "automacao",
    "knowledge_gap": "conhecimento",
    "capability_gap": "automacao",
    "churn_risk": "relacionamento",
    "positive_outcome": "resultado",
    "compliance_risk": "conformidade",
    "security_risk": "seguranca",
    "research_update_future": "pesquisa",
}

# §12.4: score nao substitui regra de dominio. Estes tipos tem gate proprio e
# nunca disparam acao sensivel sozinhos, por mais alto que o score fique.
TIPOS_COM_GATE_PROPRIO: frozenset[str] = frozenset({
    "compliance_risk", "security_risk", "data_quality",
})

SEVERIDADES = ("info", "low", "medium", "high", "critical")

# Eventos iniciais — §7.2
TIPOS_DE_EVENTO: tuple[str, ...] = (
    "work_run.created", "work_run.started", "work_run.failed",
    "work_run.completed", "work_run.stale",
    "approval.requested", "approval.expiring", "approval.decided",
    "connector.degraded", "connector.expired",
    "routine.failed", "routine.paused", "auxiliary.degraded",
    "artifact.published", "artifact.viewed", "artifact.delivery_failed",
    "conversation.closed", "conversation.scorecard_created",
    "attendance.backlog_changed",
    "portal_job.needs_human", "portal_job.failed",
    "budget.threshold_reached",
    "broker.request_detected", "capability_gap.detected",
    "recommendation.accepted", "recommendation.dismissed",
    "outcome.measured",
)


def agora() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: Optional[datetime] = None) -> str:
    return (dt or agora()).isoformat()


# ---------------------------------------------------------------------------
# Envelope canonico de evento — §7
# ---------------------------------------------------------------------------


@dataclass
class EventEnvelope:
    """Forma unica de todo evento que entra no pipeline.

    O ponto do envelope nao e uniformizar por elegancia: e garantir que um
    evento vindo do Work OS, do WhatsApp e de um portal cheguem ao detector
    com os MESMOS campos de tenant, tempo, origem e sensibilidade. Sem isso,
    cada detector reinventa o parsing e cada um erra de um jeito diferente.
    """

    event_type: str
    company_id: Optional[str]
    source_system: str
    subject_type: str
    occurred_at: str = field(default_factory=iso)
    ingested_at: str = field(default_factory=iso)
    event_id: Optional[str] = None
    user_id: Optional[str] = None
    actor_type: str = "system"
    actor_id: Optional[str] = None
    subject_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    work_run_id: Optional[str] = None
    conversation_id: Optional[str] = None
    sensitivity: str = "internal"
    payload_classification: str = "operational"
    payload_ref: Optional[str] = None
    payload_summary_redacted: str = ""
    trust_tier: int = TIER_EVENTO_SISTEMA
    metadata: dict = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = self.dedupe_key()

    def dedupe_key(self) -> str:
        """Chave estavel do evento. Reprocessar nao duplica — §7.1."""
        base = "|".join([
            self.schema_version, self.event_type, str(self.company_id or "-"),
            self.subject_type, str(self.subject_id or "-"),
            str(self.occurred_at),
        ])
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:40]

    def valido(self) -> tuple[bool, str]:
        """(ok, motivo). Evento invalido nao entra — nao vira sinal fraco."""
        if self.event_type not in TIPOS_DE_EVENTO:
            return False, f"tipo de evento desconhecido: {self.event_type}"
        # §7.1: `company_id` obrigatorio para evento tenant-scoped. O unico
        # escopo global legitimo hoje e a plataforma falando de si mesma.
        if not self.company_id and self.source_system != "platform":
            return False, "evento tenant sem company_id"
        if self.trust_tier not in range(0, 6):
            return False, "trust_tier fora de 0..5"
        return True, ""

    def como_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Sinal — forma de escrita
# ---------------------------------------------------------------------------


@dataclass
class SignalDraft:
    """Um sinal antes de ir ao banco. Carrega a evidencia junto de proposito.

    Lei central 1 da SPEC-059: **todo alerta relevante deve possuir evidencia**.
    Se o rascunho permitisse sinal sem evidencia, a lei viraria disciplina de
    quem escreve o detector — e disciplina nao sobrevive ao vigesimo detector.
    """

    company_id: str
    signal_type: str
    subject_type: str
    summary_redacted: str
    dedupe_key: str
    trust_tier: int = TIER_EVENTO_SISTEMA
    subject_id: Optional[str] = None
    source_type: str = "detector"
    source_ref: Optional[str] = None
    rule_key: Optional[str] = None
    rule_version: Optional[str] = None
    user_id: Optional[str] = None
    severity: str = "info"
    confidence: float = 0.7
    impact_score: Optional[float] = None
    urgency_score: Optional[float] = None
    actionability_score: Optional[float] = None
    recurrence_score: Optional[float] = None
    freshness_score: Optional[float] = None
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    valid_until: Optional[str] = None
    correlation_id: Optional[str] = None
    work_run_id: Optional[str] = None
    conversation_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    evidencias: list[dict] = field(default_factory=list)

    @property
    def domain(self) -> str:
        return DOMINIO_POR_TIPO.get(self.signal_type, "operacao")

    def fingerprint(self) -> str:
        base = json.dumps({
            "c": self.company_id, "t": self.signal_type,
            "s": f"{self.subject_type}:{self.subject_id or ''}",
            "r": f"{self.rule_key or ''}@{self.rule_version or ''}",
            "d": self.dedupe_key,
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]

    def valido(self) -> tuple[bool, str]:
        if self.signal_type not in TIPOS_DE_SINAL:
            return False, f"signal_type fora da taxonomia: {self.signal_type}"
        if self.severity not in SEVERIDADES:
            return False, f"severidade invalida: {self.severity}"
        if not 0.0 <= float(self.confidence) <= 1.0:
            return False, "confianca fora de 0..1"
        if not self.evidencias:
            return False, "sinal sem evidencia — SPEC-059 lei central 1"
        if self.severity == "critical" and not pode_sustentar_alerta_critico(self.trust_tier):
            return False, (
                f"severidade critica exige Tier 0/1/2, recebeu Tier {self.trust_tier} "
                "— SPEC-059 §8.2")
        return True, ""


@dataclass
class EvidenceDraft:
    """Referencia a fonte. **Nao** e copia do dado bruto — §10.2."""

    evidence_type: str
    source_system: str
    source_ref: str
    summary_redacted: str
    trust_tier: int = TIER_EVENTO_SISTEMA
    value_snapshot: dict = field(default_factory=dict)
    observed_at: Optional[str] = None
    valid_until: Optional[str] = None
    sensitivity: str = "internal"

    def content_hash(self) -> str:
        base = json.dumps(
            {"s": self.source_ref, "v": self.value_snapshot},
            sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]


def evidencia(
    *, tipo: str, sistema: str, ref: str, resumo: str,
    tier: int = TIER_EVENTO_SISTEMA, valores: Optional[dict] = None,
    sensibilidade: str = "internal",
) -> dict:
    """Atalho para montar evidencia em detector. Devolve dict pronto."""
    e = EvidenceDraft(
        evidence_type=tipo, source_system=sistema, source_ref=ref,
        summary_redacted=resumo, trust_tier=tier,
        value_snapshot=valores or {}, sensitivity=sensibilidade)
    d = asdict(e)
    d["content_hash"] = e.content_hash()
    return d


def chave_dedupe(*partes: Any) -> str:
    """Chave de dedupe deterministica a partir das partes relevantes — §11.1."""
    base = "|".join(str(p) for p in partes if p is not None)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:40]
