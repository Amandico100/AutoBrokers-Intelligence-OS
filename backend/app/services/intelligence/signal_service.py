"""Ciclo de vida do Intelligence Signal. SPEC-059 §10.1 e §11.

Uma so porta de escrita: `registrar()`. Detector nenhum escreve na tabela
direto. Isso e o que garante que **todo** sinal passe por validacao de
taxonomia, redacao, evidencia obrigatoria e dedupe — em vez de cada detector
lembrar (ou esquecer) de fazer isso.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from . import priority_service as prio
from .dedupe_service import mesclar_preservando_linhagem, validade_de
from .evidence_service import EvidenceService, tier_dominante
from .redaction_service import redigir
from .schemas import SignalDraft, iso

logger = logging.getLogger(__name__)

ESTADOS_VIVOS = ("candidate", "validated", "clustered", "promoted")


class SignalService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)
        self.evidencias = EvidenceService(supabase_client)

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------

    def registrar(self, rascunho: SignalDraft) -> Optional[dict]:
        """Valida, deduplica e grava. `None` quando o rascunho e recusado.

        Recusa e resultado legitimo, nao erro: e assim que sinal sem
        evidencia, sinal critico apoiado em inferencia e tipo fora da
        taxonomia param na porta em vez de virarem alerta.
        """
        # O tier real e o da evidencia, nao o que o detector declarou. Um
        # detector otimista nao pode promover a propria hipotese a dado vivo.
        if rascunho.evidencias:
            rascunho.trust_tier = min(rascunho.trust_tier,
                                      tier_dominante(rascunho.evidencias))

        ok, motivo = rascunho.valido()
        if not ok:
            logger.warning("[Signal] rascunho recusado (%s): %s",
                           rascunho.signal_type, motivo)
            return None

        existente = self._vivo_por_dedupe(rascunho.company_id, rascunho.dedupe_key)
        if existente:
            return self._reforcar(existente, rascunho)

        linha = {
            "company_id": rascunho.company_id,
            "user_id": rascunho.user_id,
            "signal_type": rascunho.signal_type,
            "domain": rascunho.domain,
            "subject_type": rascunho.subject_type,
            "subject_id": (str(rascunho.subject_id)[:200] if rascunho.subject_id else None),
            "source_type": rascunho.source_type,
            "source_ref": rascunho.source_ref,
            "rule_key": rascunho.rule_key,
            "rule_version": rascunho.rule_version,
            "summary_redacted": redigir(rascunho.summary_redacted, limite=600),
            "status": "validated",
            "severity": rascunho.severity,
            "confidence": round(float(rascunho.confidence), 3),
            "impact_score": rascunho.impact_score,
            "urgency_score": rascunho.urgency_score,
            "actionability_score": rascunho.actionability_score,
            "recurrence_score": rascunho.recurrence_score,
            "freshness_score": rascunho.freshness_score,
            "priority_score": self._prioridade(rascunho),
            "trust_tier": rascunho.trust_tier,
            "window_start": rascunho.window_start,
            "window_end": rascunho.window_end,
            "dedupe_key": rascunho.dedupe_key,
            "fingerprint": rascunho.fingerprint(),
            "valid_until": rascunho.valid_until or validade_de(rascunho.signal_type).isoformat(),
            "correlation_id": rascunho.correlation_id,
            "work_run_id": rascunho.work_run_id,
            "conversation_id": rascunho.conversation_id,
            "metadata": rascunho.metadata or {},
        }
        try:
            r = self.db.table("intelligence_signals").insert(linha).execute()
            criado = (r.data or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            # Corrida com outro worker no mesmo dedupe: o indice parcial unico
            # resolveu. Buscar o vencedor e reforcar e o comportamento certo.
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                existente = self._vivo_por_dedupe(rascunho.company_id, rascunho.dedupe_key)
                if existente:
                    return self._reforcar(existente, rascunho)
            logger.error("[Signal] gravacao falhou (%s): %s",
                         rascunho.signal_type, type(exc).__name__)
            return None

        if criado.get("id"):
            self.evidencias.gravar(company_id=rascunho.company_id,
                                   signal_id=criado["id"],
                                   evidencias=rascunho.evidencias)
            registrar_evento(self.db, company_id=rascunho.company_id,
                             tipo="signal.created", subject_type="signal",
                             subject_id=criado["id"],
                             mensagem=criado.get("summary_redacted") or "",
                             detalhe={"signal_type": rascunho.signal_type,
                                      "rule_key": rascunho.rule_key,
                                      "trust_tier": rascunho.trust_tier})
        return criado

    def _prioridade(self, r: SignalDraft) -> float:
        dim = prio.Dimensoes(
            impacto=r.impact_score if r.impact_score is not None else 50.0,
            urgencia=r.urgency_score if r.urgency_score is not None else 40.0,
            confianca=float(r.confidence) * 100.0,
            actionability=r.actionability_score if r.actionability_score is not None else 50.0,
            recorrencia=r.recurrence_score if r.recurrence_score is not None else 20.0,
            freshness=r.freshness_score if r.freshness_score is not None else 100.0,
        )
        penalidades = []
        if len(r.evidencias) < 1:
            penalidades.append("evidencia_insuficiente")
        if r.trust_tier >= 5:
            penalidades.append("evidencia_insuficiente")
        return prio.calcular(dim, penalidades)

    def _vivo_por_dedupe(self, company_id: str, dedupe_key: str) -> Optional[dict]:
        try:
            r = (self.db.table("intelligence_signals")
                 .select("id, company_id, severity, confidence, occurrence_count, "
                         "priority_score, metadata, fingerprint, status")
                 .eq("company_id", company_id).eq("dedupe_key", dedupe_key)
                 .in_("status", list(ESTADOS_VIVOS)).limit(1).execute())
            return (r.data or [None])[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Signal] consulta de dedupe falhou: %s", type(exc).__name__)
            return None

    def _reforcar(self, existente: dict, rascunho: SignalDraft) -> dict:
        """A mesma observacao de novo: conta, nao duplica — §11.1.

        Recorrencia sobe, e com ela a prioridade. Um problema que acontece
        pela quinta vez merece mais atencao do que na primeira, e essa
        diferenca precisa aparecer sem criar cinco linhas.
        """
        mesclado = mesclar_preservando_linhagem(
            existente,
            {"severity": rascunho.severity, "confidence": rascunho.confidence,
             "fingerprint": rascunho.fingerprint(), "last_seen_at": iso()})
        ocorrencias = int(mesclado.get("occurrence_count") or 2)
        rascunho.recurrence_score = prio.recorrencia_por_contagem(ocorrencias)
        try:
            self.db.table("intelligence_signals").update({
                "occurrence_count": ocorrencias,
                "last_seen_at": mesclado["last_seen_at"],
                "severity": mesclado["severity"],
                "confidence": round(float(mesclado["confidence"]), 3),
                "recurrence_score": rascunho.recurrence_score,
                "priority_score": self._prioridade(rascunho),
                "valid_until": validade_de(rascunho.signal_type).isoformat(),
                "metadata": mesclado.get("metadata") or {},
            }).eq("id", existente["id"]).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Signal] reforco nao gravado: %s", type(exc).__name__)
        # Evidencia nova entra sempre: e ela que prova que "mudou algo desde a
        # ultima vez" — a condicao que o cooldown consulta em §11.3.
        self.evidencias.gravar(company_id=rascunho.company_id,
                               signal_id=existente["id"],
                               evidencias=rascunho.evidencias)
        return {**existente, "occurrence_count": ocorrencias, "reforcado": True}

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    def ativos(self, company_id: str, *, tipos: Optional[list[str]] = None,
               limite: int = 200) -> list[dict]:
        try:
            q = (self.db.table("intelligence_signals")
                 .select("*").eq("company_id", company_id)
                 .in_("status", list(ESTADOS_VIVOS)))
            if tipos:
                q = q.in_("signal_type", tipos)
            r = q.order("priority_score", desc=True).limit(limite).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[Signal] leitura falhou: %s", type(exc).__name__)
            return []
        # Expirados por validade sao filtrados na leitura para nunca aparecerem
        # como novidade — a varredura que muda o status roda depois, no tick.
        from .dedupe_service import expirou

        return [s for s in (r.data or []) if not expirou(s.get("valid_until"))]

    def expirar_vencidos(self, *, limite: int = 500) -> int:
        """Marca como `expired` o que passou da validade. §11.5."""
        try:
            r = (self.db.table("intelligence_signals").select("id")
                 .in_("status", list(ESTADOS_VIVOS))
                 .lt("valid_until", iso()).limit(limite).execute())
            ids = [x["id"] for x in (r.data or [])]
            if not ids:
                return 0
            self.db.table("intelligence_signals").update(
                {"status": "expired"}).in_("id", ids).execute()
            return len(ids)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Signal] expiracao falhou: %s", type(exc).__name__)
            return 0

    def marcar(self, company_id: str, signal_id: str, status: str,
               *, motivo: str = "") -> bool:
        if status not in ("candidate", "validated", "clustered", "promoted",
                          "suppressed", "expired", "invalidated"):
            return False
        try:
            self.db.table("intelligence_signals").update({"status": status}) \
                .eq("id", signal_id).eq("company_id", company_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Signal] transicao falhou: %s", type(exc).__name__)
            return False
        registrar_evento(self.db, company_id=company_id,
                         tipo=f"signal.{status}", subject_type="signal",
                         subject_id=signal_id, mensagem=motivo)
        return True


# ---------------------------------------------------------------------------
# Timeline — §10.12
# ---------------------------------------------------------------------------


def registrar_evento(db: Any, *, company_id: Optional[str], tipo: str,
                     subject_type: str, subject_id: Optional[str] = None,
                     mensagem: str = "", detalhe: Optional[dict] = None,
                     actor_kind: str = "system", actor_id: Optional[str] = None,
                     correlation_id: Optional[str] = None) -> None:
    """Grava na timeline append-only. Nunca levanta excecao.

    Timeline que derruba o pipeline quando falha inverte a prioridade: o
    registro existe para explicar o trabalho, nao para impedi-lo.
    """
    cliente = getattr(db, "client", db)
    try:
        cliente.table("intelligence_events").insert({
            "company_id": company_id,
            "event_type": tipo,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "actor_kind": actor_kind,
            "actor_id": actor_id,
            "message_human": redigir(mensagem or "", limite=400),
            "detail": detalhe or {},
            "correlation_id": correlation_id,
        }).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Intelligence] evento '%s' nao registrado: %s",
                       tipo, type(exc).__name__)
