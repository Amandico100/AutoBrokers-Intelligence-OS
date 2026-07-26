"""Evidencia rastreavel. SPEC-059 §10.2 e §30.1.

A evidencia e uma **referencia** a fonte, com um recorte minimo do valor
observado. Nao e copia do dado bruto.

Isso nao e economia de espaco. Se o pipeline copiasse o transcript, o CPF do
segurado passaria a existir em dois lugares: na conversa, onde ha politica de
retencao, e aqui, onde nao havia. Apagar da origem deixaria de apagar de
verdade — e "apagamos seus dados" viraria mentira sem ninguem ter mentido de
proposito.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .redaction_service import redigir, relatorio_pii
from .schemas import TIER_EVENTO_SISTEMA, iso

logger = logging.getLogger(__name__)

# Recorte maximo do snapshot. Um snapshot grande e um transcript disfarcado.
MAX_CHAVES_SNAPSHOT = 12
MAX_TAMANHO_VALOR = 200


def sanear_snapshot(valores: Optional[dict]) -> dict:
    """Corta o snapshot ao essencial e redige o que sobrou."""
    saida: dict[str, Any] = {}
    for i, (chave, valor) in enumerate(sorted((valores or {}).items())):
        if i >= MAX_CHAVES_SNAPSHOT:
            saida["_truncado"] = True
            break
        if isinstance(valor, (int, float, bool)) or valor is None:
            saida[chave] = valor
        else:
            saida[chave] = redigir(str(valor), limite=MAX_TAMANHO_VALOR)
    return saida


class EvidenceService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    def gravar(self, *, company_id: str, signal_id: str, evidencias: list[dict]) -> int:
        """Grava as evidencias de um sinal. Devolve quantas entraram."""
        linhas = []
        for e in evidencias or []:
            resumo = redigir(str(e.get("summary_redacted") or ""), limite=500)
            linhas.append({
                "company_id": company_id,
                "signal_id": signal_id,
                "evidence_type": str(e.get("evidence_type") or "observacao"),
                "source_system": str(e.get("source_system") or "autobrokers"),
                "source_ref": str(e.get("source_ref") or "-")[:400],
                "trust_tier": int(e.get("trust_tier") if e.get("trust_tier") is not None
                                   else TIER_EVENTO_SISTEMA),
                "summary_redacted": resumo,
                "value_snapshot": sanear_snapshot(e.get("value_snapshot")),
                "content_hash": e.get("content_hash"),
                "observed_at": e.get("observed_at") or iso(),
                "valid_until": e.get("valid_until"),
                "sensitivity": str(e.get("sensitivity") or "internal"),
            })
        if not linhas:
            return 0
        try:
            r = self.db.table("intelligence_signal_evidence").insert(linhas).execute()
            return len(r.data or [])
        except Exception as exc:  # noqa: BLE001
            logger.error("[Evidence] gravacao falhou: %s", type(exc).__name__)
            return 0

    def do_sinal(self, company_id: str, signal_id: str, *, limite: int = 20) -> list[dict]:
        try:
            r = (self.db.table("intelligence_signal_evidence")
                 .select("evidence_type, source_system, source_ref, trust_tier, "
                         "summary_redacted, value_snapshot, observed_at, sensitivity")
                 .eq("company_id", company_id).eq("signal_id", signal_id)
                 .order("observed_at", desc=True).limit(limite).execute())
            return r.data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Evidence] leitura falhou: %s", type(exc).__name__)
            return []

    def dos_sinais(self, company_id: str, signal_ids: list[str]) -> dict[str, list[dict]]:
        """Evidencias de varios sinais numa consulta so — o briefing precisa disso."""
        if not signal_ids:
            return {}
        try:
            r = (self.db.table("intelligence_signal_evidence")
                 .select("signal_id, evidence_type, source_system, source_ref, "
                         "trust_tier, summary_redacted, value_snapshot, observed_at")
                 .eq("company_id", company_id).in_("signal_id", signal_ids)
                 .limit(400).execute())
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Evidence] leitura em lote falhou: %s", type(exc).__name__)
            return {}
        agrupado: dict[str, list[dict]] = {}
        for linha in r.data or []:
            agrupado.setdefault(linha["signal_id"], []).append(linha)
        return agrupado


def tier_de(evidencia: dict) -> int:
    """Tier declarado, com o pior caso na ausência.

    Existe como função por um motivo específico: `int(e.get("trust_tier") or 5)`
    é uma armadilha. **Tier 0 é o dado vivo autoritativo — o mais forte** — e
    `0 or 5` devolve 5. A leitura ingênua rebaixaria justamente a melhor
    evidência ao patamar de palpite de modelo, e o efeito seria silencioso:
    Findings construídos sobre dado do banco simplesmente não nasceriam.
    """
    valor = evidencia.get("trust_tier")
    if valor is None:
        return 5
    try:
        return max(0, min(5, int(valor)))
    except (TypeError, ValueError):
        return 5


def resumo_para_humano(evidencias: list[dict], *, maximo: int = 3) -> str:
    """Uma frase com as evidencias mais fortes, da mais forte para a mais fraca.

    A ordem e o ponto: o corretor le a primeira e para. Se a primeira for a
    inferencia do modelo em vez do numero do banco, a peca inteira perde
    credibilidade mesmo estando certa.
    """
    if not evidencias:
        return ""
    ordenadas = sorted(evidencias, key=tier_de)
    partes = [str(e.get("summary_redacted") or "").strip()
              for e in ordenadas[:maximo]]
    return "; ".join(p for p in partes if p)


def tier_dominante(evidencias: list[dict]) -> int:
    """O melhor Tier disponivel. Sem evidencia, assume inferencia (5).

    Assumir o pior na ausencia e deliberado: um sinal sem evidencia nao pode
    herdar a credibilidade de um dado vivo por descuido de quem escreveu o
    detector.
    """
    if not evidencias:
        return 5
    return min(tier_de(e) for e in evidencias)


def checar_privacidade(evidencias: list[dict]) -> dict:
    """Confere se sobrou PII no que vai ser mostrado. Entra no log de qualidade."""
    achados: dict[str, int] = {}
    for e in evidencias or []:
        r = relatorio_pii(str(e.get("summary_redacted") or ""))
        for marca, n in (r.get("achados") or {}).items():
            achados[marca] = achados.get(marca, 0) + n
    return {"limpo": not achados, "achados": achados}
