"""Knowledge Candidate — a unica porta do aprendizado. SPEC-059 §21, SPEC-052.

A regra e curta e absoluta: **Garimpo, detector e recomendacao nunca publicam
conhecimento**. Eles propoem candidatos. Quem publica e o caminho da SPEC-052,
depois de curadoria.

Por que isso importa mais do que parece: um sistema que aprende sozinho e
publica sozinho aprende tambem os erros — e um erro publicado no conhecimento
global e repetido para TODAS as corretoras, com a autoridade de quem le uma
fonte oficial. O candidato existe para que haja um lugar onde alguem olha
antes.

O que pode e o que nao pode virar candidato esta em §21.1 e §21.2, e a
funcao `elegivel()` implementa exatamente essas duas listas.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .redaction_service import contem_pii, redigir, relatorio_pii, resumo_seguro
from .signal_service import registrar_evento

logger = logging.getLogger(__name__)

# §21.1 — o que PODE virar conhecimento duravel.
FONTES_ELEGIVEIS = frozenset({
    "procedimento_observado", "mudanca_operacional_confirmada",
    "duvida_recorrente_com_resposta", "padrao_de_qualidade_validado",
    "conhecimento_de_dominio_com_fonte", "aprendizado_de_seguradora_confirmado",
})

# §21.2 — o que NAO vira, nunca. A lista existe porque cada item dela ja foi,
# em algum produto, tratado como "aprendizado" — e virou ruido permanente.
TIPOS_INELEGIVEIS = frozenset({
    "desejo_individual", "preferencia_pessoal", "reclamacao_isolada",
    "feature_request", "score_de_produto", "recomendacao_momentanea",
    "dado_operacional_expiravel", "pii", "conversa_integral",
})

# Tipos de sinal do Garimpo: NENHUM deles e elegivel sozinho. Voz do corretor
# e Tier 4 — sustenta "ele declarou", nao "isto e verdade" (§8.2).
SINAIS_NAO_ELEGIVEIS = frozenset({
    "broker_pain", "broker_desire", "feature_request", "churn_risk",
    "repeated_task", "capability_gap", "positive_outcome",
})

RISCO_ALTO = frozenset({"cobertura", "indenizacao", "juridico", "compliance",
                        "regulatorio", "sinistro", "susep"})


def elegivel(*, origem: str, texto: str, trust_tier: int,
             fontes: int = 1) -> tuple[bool, str]:
    """(pode virar candidato, motivo). Pura — §21.1 e §21.2."""
    if origem in TIPOS_INELEGIVEIS or origem in SINAIS_NAO_ELEGIVEIS:
        return False, f"'{origem}' não é conhecimento durável (SPEC-059 §21.2)"
    if origem not in FONTES_ELEGIVEIS:
        return False, f"origem '{origem}' não está na lista de §21.1"
    if trust_tier >= 5:
        return False, "inferência de modelo não vira conhecimento"
    if trust_tier == 4 and fontes < 2:
        # Declaracao unica e relato. Duas fontes independentes dizendo o mesmo
        # e o minimo para virar candidato — e ainda assim passa por curadoria.
        return False, "declaração isolada precisa de uma segunda fonte"
    if contem_pii(texto):
        return False, "o texto ainda contém dado pessoal"
    if len(str(texto or "").strip()) < 40:
        return False, "texto curto demais para ser conhecimento"
    return True, "elegível"


def classificar_risco(texto: str) -> str:
    """Risco do candidato. Cobertura e obrigacao legal sempre sobem — §30.5."""
    alvo = (texto or "").lower()
    if any(p in alvo for p in RISCO_ALTO):
        return "high"
    return "low"


def hash_de_dedupe(texto: str, escopo: str) -> str:
    normalizado = " ".join(str(texto or "").lower().split())[:1000]
    return hashlib.sha256(f"{escopo}|{normalizado}".encode("utf-8")).hexdigest()[:40]


class KnowledgeCandidateAdapter:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------

    def propor(self, *, origem: str, titulo: str, texto: str,
               company_id: Optional[str] = None, escopo: str = "company",
               trust_tier: int = 3, fontes: int = 1,
               evidencias: Optional[list[dict]] = None,
               source_ref: Optional[str] = None,
               candidate_type: str = "procedure") -> Optional[dict]:
        """Propoe um candidato. `None` quando nao e elegivel.

        Recusar e o caminho comum e nao e falha: a maior parte do que o
        sistema observa e operacional e expiravel, nao conhecimento.
        """
        limpo = redigir(texto, limite=4000)
        ok, motivo = elegivel(origem=origem, texto=limpo,
                              trust_tier=trust_tier, fontes=fontes)
        if not ok:
            logger.debug("[KnowledgeCandidate] recusado (%s): %s", origem, motivo)
            return None

        # §18.5 e a restricao D7: candidato GLOBAL nao carrega tenant. O CHECK
        # do banco tambem recusa, mas recusar aqui devolve mensagem legivel.
        if escopo == "global":
            company_id = None

        risco = classificar_risco(limpo)
        linha = {
            "company_id": company_id,
            "scope": escopo,
            "source_kind": origem,
            "source_ref": source_ref,
            "candidate_type": candidate_type,
            "title": resumo_seguro(titulo, 200),
            "statement_redacted": limpo,
            "evidence": evidencias or [],
            "source_count": max(1, int(fontes)),
            "confidence": 0.6 if trust_tier <= 2 else 0.45,
            "trust_tier": int(trust_tier),
            "risk_level": risco,
            # Alto risco nunca nasce aprovado — §30.5 exige humano responsavel.
            "status": "pending_review",
            "dedupe_hash": hash_de_dedupe(limpo, escopo),
            "pii_check": relatorio_pii(limpo),
        }
        try:
            r = self.db.table("knowledge_candidates").insert(linha).execute()
            criado = (r.data or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                return self._reforcar(linha)
            logger.error("[KnowledgeCandidate] proposta falhou: %s", type(exc).__name__)
            return None

        registrar_evento(self.db, company_id=company_id,
                         tipo="knowledge_candidate.proposed",
                         subject_type="knowledge_candidate",
                         subject_id=criado.get("id"), mensagem=linha["title"],
                         detalhe={"origem": origem, "escopo": escopo, "risco": risco})
        return criado

    def _reforcar(self, linha: dict) -> Optional[dict]:
        """Mesmo candidato de outra fonte: soma fontes em vez de duplicar.

        `source_count` e o que distingue "uma pessoa disse" de "tres fontes
        independentes convergem" — e essa distincao e o criterio de curadoria.
        """
        try:
            atual = (self.db.table("knowledge_candidates")
                     .select("id, source_count, confidence")
                     .eq("dedupe_hash", linha["dedupe_hash"])
                     .eq("scope", linha["scope"]).limit(1).execute()).data
            if not atual:
                return None
            c = atual[0]
            fontes = int(c.get("source_count") or 1) + 1
            self.db.table("knowledge_candidates").update({
                "source_count": fontes,
                "confidence": min(0.95, float(c.get("confidence") or 0.5) + 0.1),
            }).eq("id", c["id"]).execute()
            return {**c, "source_count": fontes, "reforcado": True}
        except Exception:  # noqa: BLE001
            return None

    # ------------------------------------------------------------------
    # Contradicao — SPEC-052
    # ------------------------------------------------------------------

    def checar_contradicao(self, candidato: dict) -> Optional[dict]:
        """Procura candidato aprovado que afirme o oposto no mesmo assunto.

        Deteccao lexica e conservadora: negacao explicita sobre o mesmo
        conjunto de termos. Nao pretende ser semantica — pretende **nunca
        deixar passar em silencio** uma contradicao obvia, marcando as duas
        como `conflicted` para revisao humana.
        """
        texto = str(candidato.get("statement_redacted") or "").lower()
        termos = {t for t in texto.split() if len(t) > 5}
        if len(termos) < 4:
            return None
        try:
            q = (self.db.table("knowledge_candidates")
                 .select("id, statement_redacted, status")
                 .eq("scope", candidato.get("scope"))
                 .in_("status", ["approved", "published"]).limit(200))
            if candidato.get("company_id"):
                q = q.eq("company_id", candidato["company_id"])
            outros = (q.execute()).data or []
        except Exception:  # noqa: BLE001
            return None

        negacoes = ("não ", "nunca ", "jamais ", "deixou de ", "não é mais")
        tem_negacao_aqui = any(n in texto for n in negacoes)
        for o in outros:
            alvo = str(o.get("statement_redacted") or "").lower()
            outros_termos = {t for t in alvo.split() if len(t) > 5}
            sobreposicao = len(termos & outros_termos) / max(1, len(termos))
            if sobreposicao < 0.6:
                continue
            tem_negacao_la = any(n in alvo for n in negacoes)
            if tem_negacao_aqui != tem_negacao_la:
                self._marcar_conflito(candidato.get("id"), o["id"])
                return o
        return None

    def _marcar_conflito(self, novo_id: Optional[str], antigo_id: str) -> None:
        if not novo_id:
            return
        try:
            self.db.table("knowledge_candidates").update({
                "status": "conflicted", "contradicts_id": antigo_id,
                "review_note": "contradiz um conhecimento já aprovado — precisa de decisão humana",
            }).eq("id", novo_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[KnowledgeCandidate] conflito nao marcado: %s", type(exc).__name__)

    # ------------------------------------------------------------------
    # Curadoria
    # ------------------------------------------------------------------

    def fila(self, *, escopo: Optional[str] = None, limite: int = 50) -> list[dict]:
        try:
            q = (self.db.table("knowledge_candidates").select("*")
                 .in_("status", ["pending_review", "conflicted"]))
            if escopo:
                q = q.eq("scope", escopo)
            r = q.order("source_count", desc=True).limit(limite).execute()
            return r.data or []
        except Exception:  # noqa: BLE001
            return []

    def decidir(self, candidate_id: str, *, aprovar: bool, user_id: str,
                nota: Optional[str] = None) -> bool:
        """Curadoria humana. `approved` NAO publica — publicar e da SPEC-052."""
        try:
            self.db.table("knowledge_candidates").update({
                "status": "approved" if aprovar else "rejected",
                "reviewed_by_user_id": user_id,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "review_note": resumo_seguro(nota or "", 600) or None,
            }).eq("id", candidate_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[KnowledgeCandidate] decisao falhou: %s", type(exc).__name__)
            return False
        registrar_evento(self.db, company_id=None,
                         tipo="knowledge_candidate.decided",
                         subject_type="knowledge_candidate", subject_id=candidate_id,
                         actor_kind="admin", actor_id=user_id,
                         mensagem="aprovado para curadoria" if aprovar else "rejeitado")
        return True
