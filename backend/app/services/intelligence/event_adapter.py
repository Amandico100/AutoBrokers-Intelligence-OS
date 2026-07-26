"""Porta de entrada de eventos. SPEC-059 §7.

Duas rotas chegam ao mesmo pipeline:

* **varredura** — o `RuleEngine` olha o estado e conclui. Boa para "ha 4
  aprovacoes paradas": nao existe evento de "continuar parado".
* **evento** — algo aconteceu agora e alguem quer saber agora. Boa para
  "a conexao caiu": esperar o proximo tick e esperar demais.

As duas produzem `intelligence_signals`. O que este modulo faz e impedir que
a rota de evento vire um segundo caminho com regras proprias: ele normaliza,
valida e entrega ao MESMO `SignalService`.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from . import priority_service as prio
from .dedupe_service import chave_de_sinal
from .redaction_service import resumo_seguro
from .schemas import (TIER_DADO_VIVO, TIER_EVENTO_SISTEMA, EventEnvelope,
                      SignalDraft, evidencia)
from .signal_service import SignalService

logger = logging.getLogger(__name__)

# Traducao evento → tipo de sinal. Evento fora do mapa e ignorado de
# proposito: entrar no pipeline sem saber que tipo de sinal ele produz
# geraria um sinal generico que nao serve para regra nenhuma.
MAPA: dict[str, dict] = {
    "connector.degraded":      {"tipo": "connection_health", "sev": "high",  "tier": TIER_DADO_VIVO},
    "connector.expired":       {"tipo": "connection_health", "sev": "critical", "tier": TIER_DADO_VIVO},
    "approval.expiring":       {"tipo": "approval_pending",  "sev": "high",  "tier": TIER_DADO_VIVO},
    "work_run.failed":         {"tipo": "work_failure",      "sev": "medium", "tier": TIER_EVENTO_SISTEMA},
    "work_run.stale":          {"tipo": "work_stale",        "sev": "high",  "tier": TIER_DADO_VIVO},
    "routine.failed":          {"tipo": "operational_backlog", "sev": "medium", "tier": TIER_EVENTO_SISTEMA},
    "routine.paused":          {"tipo": "operational_backlog", "sev": "high", "tier": TIER_DADO_VIVO},
    "auxiliary.degraded":      {"tipo": "operational_backlog", "sev": "high", "tier": TIER_DADO_VIVO},
    "portal_job.needs_human":  {"tipo": "portal_blocker",    "sev": "high",  "tier": TIER_DADO_VIVO},
    "portal_job.failed":       {"tipo": "portal_blocker",    "sev": "medium", "tier": TIER_EVENTO_SISTEMA},
    "artifact.delivery_failed": {"tipo": "operational_backlog", "sev": "medium", "tier": TIER_EVENTO_SISTEMA},
    "budget.threshold_reached": {"tipo": "budget_risk",      "sev": "high",  "tier": TIER_DADO_VIVO},
    "capability_gap.detected": {"tipo": "capability_gap",    "sev": "low",   "tier": TIER_DADO_VIVO},
    "broker.request_detected": {"tipo": "repeated_task",     "sev": "low",   "tier": TIER_DADO_VIVO},
}

MENSAGEM: dict[str, str] = {
    "connector.degraded": "Uma conexão da corretora está instável.",
    "connector.expired": "Uma conexão da corretora expirou e precisa ser refeita.",
    "approval.expiring": "Uma aprovação está prestes a expirar.",
    "work_run.failed": "Um trabalho não conseguiu concluir.",
    "work_run.stale": "Um trabalho parou de dar sinal de vida.",
    "routine.failed": "Uma rotina falhou na última execução.",
    "routine.paused": "Uma rotina foi desligada depois de falhar várias vezes.",
    "auxiliary.degraded": "Um Auxiliar instalado está com problema.",
    "portal_job.needs_human": "Um acesso a portal precisa de uma ação sua para continuar.",
    "portal_job.failed": "Um acesso a portal não concluiu.",
    "artifact.delivery_failed": "Uma peça pronta não conseguiu ser entregue.",
    "budget.threshold_reached": "O consumo do mês atingiu o limite configurado.",
    "capability_gap.detected": "Um pedido seu não pôde ser atendido pelo sistema.",
    "broker.request_detected": "Um pedido recorrente foi identificado.",
}


def normalizar(
    *, event_type: str, company_id: Optional[str], source_system: str,
    subject_type: str, subject_id: Optional[str] = None,
    resumo: str = "", metadata: Optional[dict] = None, **extras: Any,
) -> Optional[EventEnvelope]:
    """Monta o envelope. `None` quando o evento nao passa na validacao."""
    env = EventEnvelope(
        event_type=event_type, company_id=company_id,
        source_system=source_system, subject_type=subject_type,
        subject_id=str(subject_id) if subject_id is not None else None,
        payload_summary_redacted=resumo_seguro(resumo or MENSAGEM.get(event_type, ""), 400),
        trust_tier=int((MAPA.get(event_type) or {}).get("tier", TIER_EVENTO_SISTEMA)),
        metadata=metadata or {},
        **{k: v for k, v in extras.items() if k in EventEnvelope.__dataclass_fields__},
    )
    ok, motivo = env.valido()
    if not ok:
        logger.warning("[EventAdapter] evento recusado (%s): %s", event_type, motivo)
        return None
    return env


def para_sinal(env: EventEnvelope) -> Optional[SignalDraft]:
    """Traduz envelope em rascunho de sinal. Puro."""
    regra = MAPA.get(env.event_type)
    if not regra or not env.company_id:
        return None

    resumo = env.payload_summary_redacted or MENSAGEM.get(env.event_type, env.event_type)
    return SignalDraft(
        company_id=env.company_id,
        signal_type=regra["tipo"],
        subject_type=env.subject_type,
        subject_id=env.subject_id,
        summary_redacted=resumo,
        dedupe_key=chave_de_sinal(
            company_id=env.company_id, signal_type=regra["tipo"],
            subject_type=env.subject_type, subject_id=env.subject_id,
            rule_key="event", rule_version=env.schema_version,
            parametros={"evento": env.event_type}),
        trust_tier=env.trust_tier,
        source_type="event", source_ref=env.event_id,
        rule_key="event", rule_version=env.schema_version,
        user_id=env.user_id,
        severity=regra["sev"],
        confidence=1.0 if env.trust_tier <= TIER_EVENTO_SISTEMA else 0.8,
        impact_score=60.0, urgency_score=prio.urgencia_por_prazo(0 if regra["sev"] == "critical" else None),
        actionability_score=70.0, freshness_score=100.0,
        correlation_id=env.correlation_id, work_run_id=env.work_run_id,
        conversation_id=env.conversation_id,
        metadata={**(env.metadata or {}), "event_type": env.event_type},
        evidencias=[evidencia(
            tipo="evento", sistema=env.source_system,
            ref=f"{env.subject_type}:{env.subject_id or '-'}",
            resumo=resumo, tier=env.trust_tier,
            valores={"event_type": env.event_type,
                     "occurred_at": env.occurred_at})],
    )


def emitir(supabase_client: Any, **campos: Any) -> Optional[dict]:
    """Normaliza, traduz e registra. Ponto unico para quem emite evento.

    Nunca levanta excecao: um evento que nao vira sinal e uma oportunidade
    perdida de avisar; uma excecao propagada e um trabalho do corretor
    interrompido por causa da telemetria.
    """
    try:
        env = normalizar(**campos)
        if env is None:
            return None
        rascunho = para_sinal(env)
        if rascunho is None:
            return None
        return SignalService(supabase_client).registrar(rascunho)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[EventAdapter] emissao falhou (%s): %s",
                       campos.get("event_type"), type(exc).__name__)
        return None
