"""Priorizacao de Findings e sinais. SPEC-059 §12.

Puro e deterministico de proposito. Prioridade calculada por LLM e
irreproduzivel: o mesmo quadro produz ordens diferentes em dias diferentes, e
ninguem consegue explicar ao corretor por que o item que estava em primeiro
sumiu. Aqui a conta e sempre a mesma e pode ser mostrada.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .schemas import TIPOS_COM_GATE_PROPRIO

# §12.2 — pesos da formula inicial.
PESOS: dict[str, float] = {
    "impacto": 0.30,
    "urgencia": 0.20,
    "confianca": 0.15,
    "actionability": 0.15,
    "recorrencia": 0.10,
    "freshness": 0.05,
    "alinhamento": 0.05,
}

# §12.2 — penalidades. Sao subtracoes diretas do score final.
PENALIDADES: dict[str, float] = {
    "evidencia_insuficiente": 20.0,
    "fonte_stale": 10.0,
    "contradicao": 15.0,
    "repeticao": 8.0,
    "baixa_relevancia_para_o_papel": 10.0,
    "acao_em_andamento": 25.0,
    "dispensado_recentemente": 30.0,
}

P0, P1, P2, P3 = "P0", "P1", "P2", "P3"


@dataclass
class Dimensoes:
    """As sete dimensoes de §12.1, cada uma de 0 a 100."""

    impacto: float = 0.0
    urgencia: float = 0.0
    confianca: float = 0.0
    actionability: float = 0.0
    recorrencia: float = 0.0
    freshness: float = 0.0
    alinhamento: float = 50.0  # neutro quando a corretora nao declarou meta

    def como_dict(self) -> dict:
        return {
            "impacto": self.impacto, "urgencia": self.urgencia,
            "confianca": self.confianca, "actionability": self.actionability,
            "recorrencia": self.recorrencia, "freshness": self.freshness,
            "alinhamento": self.alinhamento,
        }


def _limitar(v: float) -> float:
    return max(0.0, min(100.0, float(v)))


def calcular(dim: Dimensoes, penalidades: Optional[list[str]] = None) -> float:
    """Score 0–100. A conta de §12.2, sem atalho."""
    bruto = (
        _limitar(dim.impacto) * PESOS["impacto"]
        + _limitar(dim.urgencia) * PESOS["urgencia"]
        + _limitar(dim.confianca) * PESOS["confianca"]
        + _limitar(dim.actionability) * PESOS["actionability"]
        + _limitar(dim.recorrencia) * PESOS["recorrencia"]
        + _limitar(dim.freshness) * PESOS["freshness"]
        + _limitar(dim.alinhamento) * PESOS["alinhamento"]
    )
    desconto = sum(PENALIDADES.get(p, 0.0) for p in (penalidades or []))
    return round(_limitar(bruto - desconto), 2)


def nivel(score: float, *, risco_critico: bool = False) -> str:
    """P0..P3 conforme §12.3.

    `risco_critico` e a segunda condicao do P0 e nao e opcional: score alto
    sozinho **nao** produz P0. Um item pode pontuar 92 por ser urgente,
    frequente e acionavel sem nada de critico acontecendo — e acordar o
    corretor por causa disso e o comeco do alert fatigue.
    """
    s = float(score or 0)
    if s >= 85 and risco_critico:
        return P0
    if s >= 70:
        return P1
    if s >= 50:
        return P2
    return P3


def exige_gate_de_dominio(signal_type: str) -> bool:
    """§12.4 — cobertura, obrigacao legal, seguranca e dado tem gate proprio."""
    return signal_type in TIPOS_COM_GATE_PROPRIO


def freshness_por_idade(horas: float, meia_vida_horas: float = 24.0) -> float:
    """Decaimento simples: 100 agora, ~50 na meia-vida, tendendo a 0.

    Sem decaimento, uma oportunidade de duas semanas atras continua brigando
    de igual para igual com o problema de hoje — e §11.5 proibe mostrar
    oportunidade antiga como nova.
    """
    if horas <= 0:
        return 100.0
    fator = 0.5 ** (float(horas) / max(1e-6, float(meia_vida_horas)))
    return round(_limitar(100.0 * fator), 2)


def urgencia_por_prazo(horas_restantes: Optional[float]) -> float:
    """Urgencia a partir do prazo. Sem prazo conhecido, urgencia e neutra.

    Devolver 0 quando nao ha prazo seria dizer "nao e urgente", que e uma
    afirmacao. Ausencia de dado nao significa zero — lei central 4.
    """
    if horas_restantes is None:
        return 40.0
    h = float(horas_restantes)
    if h <= 0:
        return 100.0
    if h <= 4:
        return 92.0
    if h <= 12:
        return 80.0
    if h <= 24:
        return 70.0
    if h <= 72:
        return 55.0
    if h <= 168:
        return 35.0
    return 20.0


def recorrencia_por_contagem(ocorrencias: int) -> float:
    """1 vez = 20; cresce e satura em 100 na quinta ocorrencia."""
    n = max(1, int(ocorrencias or 1))
    return round(_limitar(20.0 * n), 2)


def resumo_explicavel(dim: Dimensoes, penalidades: Optional[list[str]],
                      score: float) -> dict:
    """A conta em forma legivel — alimenta "por que voce esta me mostrando isso".

    §15.5 exige transparencia. Guardar as parcelas junto do resultado e o que
    permite responder essa pergunta sem recalcular nada depois.
    """
    return {
        "dimensoes": dim.como_dict(),
        "pesos": PESOS,
        "penalidades": list(penalidades or []),
        "desconto": round(sum(PENALIDADES.get(p, 0.0) for p in (penalidades or [])), 2),
        "score": score,
        "nivel": nivel(score),
    }
