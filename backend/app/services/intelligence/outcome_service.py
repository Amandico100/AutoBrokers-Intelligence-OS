"""Medicao de resultado. SPEC-059 §20.

A lei que este modulo existe para cumprir e a numero 10:

    **Resultado nao medido e inconclusivo, nao sucesso.**

Isso parece obvio e quase nenhum produto faz. O caminho facil e marcar
"resolvido" quando a acao roda sem erro — mas rodar sem erro nao e o mesmo
que resolver o problema. Aqui a unica forma de um outcome virar `realized` e
a metrica declarada no plano ter melhorado de fato, comparada com a linha de
base capturada ANTES.

O CHECK `recommendation_outcomes_sem_medicao_nao_afirma_ck` no banco e a
segunda linha de defesa: mesmo que alguem escreva codigo errado aqui, o
Postgres recusa `realized` sem `measured_at`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .signal_service import registrar_evento

logger = logging.getLogger(__name__)


@dataclass
class Medicao:
    status: str
    observado: Optional[float]
    baseline: Optional[float]
    resumo: str
    confianca: float = 0.9
    calculo: Optional[dict] = None


def avaliar(baseline: Optional[float], observado: Optional[float], *,
            direcao: str = "menor_melhor",
            tolerancia_percentual: float = 10.0) -> Medicao:
    """Compara linha de base e observado. Puro — §20.1.

    `direcao` importa: em "aprovacoes pendentes" cair e bom; em "nota media"
    subir e bom. Tratar as duas igual produziria a conclusao invertida na
    metade dos casos, que e pior do que nao medir.
    """
    if baseline is None or observado is None:
        return Medicao(
            "inconclusive", observado, baseline,
            "Não foi possível comparar: falta a linha de base ou a leitura atual.",
            confianca=0.3)

    try:
        b, o = float(baseline), float(observado)
    except (TypeError, ValueError):
        return Medicao("inconclusive", None, None,
                       "Os valores medidos não são comparáveis.", confianca=0.2)

    if b == 0 and o == 0:
        return Medicao("inconclusive", o, b,
                       "Nada a comparar: o indicador estava e continua em zero.",
                       confianca=0.5)

    delta = o - b
    base_para_percentual = abs(b) if b else 1.0
    variacao = 100.0 * delta / base_para_percentual
    melhorou = (delta < 0) if direcao == "menor_melhor" else (delta > 0)
    calculo = {"baseline": b, "observado": o, "delta": round(delta, 4),
               "variacao_percentual": round(variacao, 2), "direcao": direcao,
               "tolerancia_percentual": tolerancia_percentual}

    if abs(variacao) < tolerancia_percentual:
        return Medicao("inconclusive", o, b,
                       f"Praticamente sem mudança ({variacao:+.1f}%). "
                       f"Não dá para dizer que a ação fez diferença.",
                       confianca=0.7, calculo=calculo)

    if melhorou:
        resolvido_por_completo = (direcao == "menor_melhor" and o == 0)
        return Medicao(
            "realized" if resolvido_por_completo or abs(variacao) >= 50 else "partially_realized",
            o, b,
            f"O indicador foi de {b:g} para {o:g} ({variacao:+.1f}%).",
            confianca=0.9, calculo=calculo)

    return Medicao("negative", o, b,
                   f"O indicador piorou: de {b:g} para {o:g} ({variacao:+.1f}%).",
                   confianca=0.9, calculo=calculo)


DIRECAO_POR_METRICA = {
    "aprovacoes_pendentes": "menor_melhor",
    "falhas_na_janela": "menor_melhor",
    "atendimentos_parados": "menor_melhor",
    "pedidos_manuais_repetidos": "menor_melhor",
    "conexao_saudavel": "maior_melhor",
    "nota_media_24h": "maior_melhor",
}


class OutcomeService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------

    def abrir(self, *, company_id: str, recommendation_id: str,
              plano: dict, work_run_id: Optional[str] = None) -> Optional[dict]:
        """Abre a medicao no momento em que a acao comeca. §20.2.

        Aberta ANTES da acao de proposito: e o unico instante em que a linha
        de base ainda e a de antes.
        """
        metrica = (plano or {}).get("metrica")
        if not metrica:
            return None
        janela = int((plano or {}).get("janela_horas") or 72)
        linha = {
            "company_id": company_id,
            "recommendation_id": recommendation_id,
            "work_run_id": work_run_id,
            "measurement_type": str(metrica),
            "measurement_status": "in_progress",
            "baseline": {"valor": (plano or {}).get("baseline"),
                         "fonte": (plano or {}).get("fonte"),
                         "capturado_em": datetime.now(timezone.utc).isoformat()},
            "automation_level": str((plano or {}).get("automation_level") or "automated"),
            "confidence": 0.5,
            "measure_after": (datetime.now(timezone.utc)
                              + timedelta(hours=janela)).isoformat(),
            "calculation": {"metodo": (plano or {}).get("metodo"),
                            "limitacoes": (plano or {}).get("limitacoes")},
        }
        try:
            r = self.db.table("recommendation_outcomes").upsert(
                linha, on_conflict="recommendation_id,measurement_type").execute()
            return (r.data or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            logger.error("[Outcome] abertura falhou: %s", type(exc).__name__)
            return None

    def vencidos(self, *, limite: int = 50) -> list[dict]:
        """Medicoes cuja janela de observacao terminou."""
        try:
            r = (self.db.table("recommendation_outcomes").select("*")
                 .in_("measurement_status", ["pending", "in_progress"])
                 .lt("measure_after", datetime.now(timezone.utc).isoformat())
                 .limit(limite).execute())
            return r.data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Outcome] varredura falhou: %s", type(exc).__name__)
            return []

    def medir(self, outcome: dict) -> Optional[dict]:
        """Le o indicador agora, compara e fecha a medicao."""
        company_id = str(outcome["company_id"])
        metrica = str(outcome.get("measurement_type") or "")
        baseline = ((outcome.get("baseline") or {}).get("valor"))

        observado = self._ler_indicador(company_id, metrica, outcome)
        if observado is None:
            return self._fechar(outcome, Medicao(
                "inconclusive", None, baseline,
                "Não consegui ler o indicador para comparar. "
                "Sem leitura, o resultado fica inconclusivo — não conto como sucesso.",
                confianca=0.2))

        medicao = avaliar(baseline, observado,
                          direcao=DIRECAO_POR_METRICA.get(metrica, "menor_melhor"))
        return self._fechar(outcome, medicao)

    def _ler_indicador(self, company_id: str, metrica: str,
                       outcome: dict) -> Optional[float]:
        """Le o valor atual da metrica. `None` quando nao da para ler.

        Devolver 0 no lugar de `None` seria transformar "nao consegui ler" em
        "esta zerado" — e, em metrica de "menor melhor", isso viraria sucesso
        perfeito inventado.
        """
        try:
            if metrica == "aprovacoes_pendentes":
                r = (self.db.table("approval_requests").select("id", count="exact")
                     .eq("company_id", company_id).eq("status", "pending").execute())
                return float(getattr(r, "count", None) or len(r.data or []))
            if metrica == "falhas_na_janela":
                desde = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
                r = (self.db.table("work_runs").select("id", count="exact")
                     .eq("company_id", company_id).eq("status", "failed")
                     .gte("finished_at", desde).execute())
                return float(getattr(r, "count", None) or len(r.data or []))
            if metrica == "atendimentos_parados":
                from .detectors.qualidade import analisar_paradas

                desde = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
                conversas = (self.db.table("conversations")
                             .select("id, status, channel, last_message_at, updated_at, session_id")
                             .eq("company_id", company_id)
                             .gte("last_message_at", desde).limit(400).execute()).data or []
                conversas = [c for c in conversas
                             if not str(c.get("session_id") or "").startswith("dispatch:")]
                return float(len(analisar_paradas(conversas, datetime.now(timezone.utc))))
            if metrica == "conexao_saudavel":
                r = (self.db.table("tenant_connections")
                     .select("health_status, status").eq("company_id", company_id)
                     .limit(100).execute()).data or []
                ruins = sum(1 for c in r
                            if str(c.get("health_status") or c.get("status") or "").lower()
                            in ("expired", "degraded", "error", "disconnected", "revoked"))
                return 1.0 if not ruins else 0.0
            if metrica == "nota_media_24h":
                desde = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
                r = (self.db.table("conversation_scorecards").select("score")
                     .eq("company_id", company_id).gte("created_at", desde)
                     .limit(500).execute()).data or []
                notas = [float(x.get("score") or 0) for x in r]
                return round(sum(notas) / len(notas), 2) if notas else None
            if metrica == "pedidos_manuais_repetidos":
                desde = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
                r = (self.db.table("auxiliary_requests").select("id", count="exact")
                     .eq("company_id", company_id).gte("created_at", desde).execute())
                return float(getattr(r, "count", None) or len(r.data or []))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Outcome] leitura de '%s' falhou: %s", metrica, type(exc).__name__)
        return None

    def _fechar(self, outcome: dict, m: Medicao) -> Optional[dict]:
        agora = datetime.now(timezone.utc).isoformat()
        campos = {
            "measurement_status": m.status,
            "observed": {"valor": m.observado, "lido_em": agora},
            "calculation": {**(outcome.get("calculation") or {}), **(m.calculo or {})},
            "confidence": round(float(m.confianca), 3),
            "value_summary": m.resumo,
            # Sem leitura nao ha `measured_at`: e isso que impede o banco de
            # aceitar qualquer estado que afirme resultado.
            "measured_at": agora if m.observado is not None else None,
        }
        try:
            self.db.table("recommendation_outcomes").update(campos) \
                .eq("id", outcome["id"]).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[Outcome] fechamento falhou: %s", type(exc).__name__)
            return None

        try:
            self.db.table("recommendations").update({"status": "measured"}) \
                .eq("id", outcome["recommendation_id"]).execute()
        except Exception:  # noqa: BLE001
            pass

        registrar_evento(self.db, company_id=outcome["company_id"],
                         tipo="outcome.measured", subject_type="recommendation",
                         subject_id=outcome.get("recommendation_id"),
                         mensagem=m.resumo,
                         detalhe={"status": m.status, "metrica": outcome.get("measurement_type")})

        if m.status == "negative":
            # §20.6 — resultado negativo nao se esconde. Fica registrado como
            # evento proprio para o Admin ver na qualidade da regra.
            registrar_evento(self.db, company_id=outcome["company_id"],
                             tipo="outcome.negative", subject_type="recommendation",
                             subject_id=outcome.get("recommendation_id"),
                             mensagem="A recomendação não ajudou — o indicador piorou.",
                             detalhe=m.calculo or {})
        return {**outcome, **campos}

    def confirmar_por_humano(self, *, company_id: str, outcome_id: str,
                             user_id: str, status: str,
                             resumo: Optional[str] = None) -> bool:
        """§20.4 — confirmacao humana sobe o nivel de automacao para `confirmed`."""
        if status not in ("realized", "partially_realized", "inconclusive", "negative"):
            return False
        try:
            self.db.table("recommendation_outcomes").update({
                "measurement_status": status,
                "automation_level": "confirmed",
                "confirmed_by_user_id": user_id,
                "measured_at": datetime.now(timezone.utc).isoformat(),
                "value_summary": resumo or "confirmado pelo corretor",
                "confidence": 0.99,
            }).eq("id", outcome_id).eq("company_id", company_id).execute()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("[Outcome] confirmação humana falhou: %s", type(exc).__name__)
            return False

    def do_periodo(self, company_id: str, *, dias: int = 7) -> list[dict]:
        desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
        try:
            r = (self.db.table("recommendation_outcomes")
                 .select("id, recommendation_id, measurement_type, measurement_status, "
                         "value_summary, automation_level, measured_at, confidence")
                 .eq("company_id", company_id).gte("created_at", desde)
                 .order("measured_at", desc=True).limit(50).execute())
            return r.data or []
        except Exception:  # noqa: BLE001
            return []
