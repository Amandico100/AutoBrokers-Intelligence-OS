"""Resposta do corretor a uma recomendacao. SPEC-059 §10.6 e §15.4.

O feedback faz tres coisas, e nesta ordem:

1. registra a decisao (append-only, para a qualidade poder ser medida depois);
2. ajusta o silencio daquele assunto;
3. quando aceito, **abre o caminho canonico** — Work Run, Rotina ou proposta
   de Auxiliar pela Factory. Nunca executa efeito direto.

O que ele explicitamente NAO faz: apagar evidencia. `wrong_data` significa que
o numero saiu errado, e apagar a evidencia justamente nesse caso destruiria a
unica pista de por que ele saiu errado.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .delivery_policy import ajustar_cooldown_por_feedback
from .redaction_service import redigir
from .signal_service import registrar_evento

logger = logging.getLogger(__name__)

ACOES = ("acknowledge", "accept", "reject", "dismiss", "snooze",
         "not_relevant", "already_solved", "wrong_data",
         "need_explanation", "ask_autobrokers")

# Feedback que silencia o assunto e por quanto tempo (dias).
SILENCIO_POR_ACAO = {
    "not_relevant": 30, "dismiss": 7, "already_solved": 14,
    "reject": 7, "wrong_data": 3,
}


class FeedbackService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    def registrar(self, *, company_id: str, recommendation_id: str, acao: str,
                  user_id: Optional[str] = None, motivo: Optional[str] = None,
                  comentario: Optional[str] = None,
                  dias_adiar: int = 1,
                  action_key: Optional[str] = None) -> dict:
        """Grava a resposta e move a recomendacao. Devolve o que aconteceu."""
        if acao not in ACOES:
            return {"ok": False, "erro": f"ação desconhecida: {acao}"}

        agora = datetime.now(timezone.utc)
        rec = self._carregar(company_id, recommendation_id)
        if not rec:
            return {"ok": False, "erro": "recomendação não encontrada"}

        resposta = {
            "company_id": company_id,
            "recommendation_id": recommendation_id,
            "user_id": user_id,
            "action": acao,
            "reason_code": motivo,
            "comment_redacted": redigir(comentario or "", limite=800) or None,
            "snoozed_until": ((agora + timedelta(days=max(1, dias_adiar))).isoformat()
                              if acao == "snooze" else None),
            "selected_action_key": action_key,
        }
        try:
            self.db.table("recommendation_responses").insert(resposta).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[Feedback] registro falhou: %s", type(exc).__name__)
            return {"ok": False, "erro": "não consegui registrar sua resposta"}

        novo_status = self._status_apos(acao)
        campos: dict[str, Any] = {"status": novo_status}
        if acao == "accept":
            campos["accepted_at"] = agora.isoformat()
            campos["selected_action_key"] = action_key or rec.get("recommended_action_key")
        if acao in ("reject", "not_relevant"):
            campos["rejected_at"] = agora.isoformat()
        if acao == "acknowledge":
            campos["viewed_at"] = agora.isoformat()
        try:
            self.db.table("recommendations").update(campos) \
                .eq("id", recommendation_id).eq("company_id", company_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Feedback] transição da recomendação: %s", type(exc).__name__)

        self._silenciar_assunto(company_id, rec, acao, agora, dias_adiar)

        registrar_evento(self.db, company_id=company_id,
                         tipo=f"recommendation.{acao}",
                         subject_type="recommendation", subject_id=recommendation_id,
                         actor_kind="user", actor_id=user_id,
                         mensagem=_frase(acao),
                         detalhe={"motivo": motivo, "action_key": action_key})

        return {"ok": True, "status": novo_status, "recomendacao": rec,
                "mensagem": _frase(acao),
                "executar": acao == "accept",
                "action_key": campos.get("selected_action_key")}

    def _carregar(self, company_id: str, rec_id: str) -> Optional[dict]:
        try:
            r = (self.db.table("recommendations").select("*")
                 .eq("id", rec_id).eq("company_id", company_id)
                 .maybe_single().execute())
            return r.data if r else None
        except Exception:  # noqa: BLE001
            return None

    def _status_apos(self, acao: str) -> str:
        return {
            "accept": "accepted", "reject": "rejected", "not_relevant": "rejected",
            "dismiss": "rejected", "snooze": "snoozed", "already_solved": "rejected",
            "wrong_data": "withdrawn", "acknowledge": "viewed",
            "need_explanation": "viewed", "ask_autobrokers": "viewed",
        }.get(acao, "viewed")

    def _silenciar_assunto(self, company_id: str, rec: dict, acao: str,
                           agora: datetime, dias_adiar: int) -> None:
        """Leva o feedback ao Finding — e no Finding que o cooldown mora.

        Silenciar so a recomendacao deixaria o Finding vivo e produzindo uma
        recomendacao nova amanha, com outro id. O corretor veria o mesmo aviso
        de novo e concluiria, com razao, que dispensar nao funciona.
        """
        finding_id = rec.get("finding_id")
        if not finding_id:
            return
        dias = SILENCIO_POR_ACAO.get(acao, dias_adiar if acao == "snooze" else 0)
        if dias <= 0:
            return
        campos: dict[str, Any] = {
            "snoozed_until": (agora + timedelta(days=dias)).isoformat(),
            "status": "snoozed",
        }
        if acao == "already_solved":
            campos = {"status": "resolved", "resolved_at": agora.isoformat(),
                      "resolution_summary": "o corretor informou que já estava resolvido"}
        if acao == "not_relevant":
            campos = {"status": "dismissed", "dismissed_at": agora.isoformat(),
                      "resolution_summary": "o corretor marcou como não relevante"}
        try:
            self.db.table("intelligence_findings").update(campos) \
                .eq("id", finding_id).eq("company_id", company_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Feedback] silêncio do Finding: %s", type(exc).__name__)

    # ------------------------------------------------------------------

    def qualidade(self, *, company_id: Optional[str] = None,
                  dias: int = 30) -> dict:
        """Metricas de §32.2. Numeros medidos, nada estimado."""
        desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
        try:
            q = (self.db.table("recommendation_responses")
                 .select("action, created_at, company_id").gte("created_at", desde))
            if company_id:
                q = q.eq("company_id", company_id)
            respostas = (q.limit(3000).execute()).data or []
        except Exception:  # noqa: BLE001
            respostas = []
        try:
            q2 = (self.db.table("recommendations")
                  .select("id, status, created_at, company_id").gte("created_at", desde))
            if company_id:
                q2 = q2.eq("company_id", company_id)
            recs = (q2.limit(3000).execute()).data or []
        except Exception:  # noqa: BLE001
            recs = []

        por_acao: dict[str, int] = {}
        for r in respostas:
            por_acao[r["action"]] = por_acao.get(r["action"], 0) + 1

        entregues = sum(1 for r in recs
                        if r.get("status") in ("delivered", "viewed", "accepted",
                                               "rejected", "executing", "executed",
                                               "measured", "snoozed"))
        aceitas = por_acao.get("accept", 0)
        dispensadas = (por_acao.get("dismiss", 0) + por_acao.get("not_relevant", 0)
                       + por_acao.get("reject", 0))
        erradas = por_acao.get("wrong_data", 0)

        def taxa(n: int) -> Optional[float]:
            # Sem entrega nao ha taxa. Devolver 0 diria "ninguem aceitou",
            # quando o certo e "ainda nao ha o que medir" — lei central 4.
            return round(100.0 * n / entregues, 1) if entregues else None

        return {
            "periodo_dias": dias,
            "recomendacoes_criadas": len(recs),
            "entregues": entregues,
            "respostas": len(respostas),
            "por_acao": por_acao,
            "taxa_aceitacao": taxa(aceitas),
            "taxa_dispensa": taxa(dispensadas),
            "taxa_dado_errado": taxa(erradas),
            "observacao": (None if entregues else
                           "ainda não há recomendações entregues suficientes para calcular taxas"),
        }

    def cooldown_sugerido(self, cooldown_atual: int, acao: str) -> int:
        return ajustar_cooldown_por_feedback(cooldown_atual, acao)


def _frase(acao: str) -> str:
    return {
        "accept": "Combinado — vou cuidar disso.",
        "reject": "Certo, não vou insistir nisso.",
        "dismiss": "Dispensado. Não mostro de novo tão cedo.",
        "snooze": "Te lembro depois.",
        "not_relevant": "Anotado: esse tipo de aviso não é útil para você.",
        "already_solved": "Ótimo. Marquei como resolvido.",
        "wrong_data": "Obrigado por avisar — o número vai ser conferido.",
        "need_explanation": "Vou explicar de onde isso veio.",
        "ask_autobrokers": "Vamos conversar sobre isso.",
        "acknowledge": "Anotado.",
    }.get(acao, "Anotado.")
