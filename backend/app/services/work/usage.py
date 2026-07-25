"""Usage Events — captura técnica de consumo. Decisão **D4**.

O modelo de negócio do AutoBrokers é consumo. Executar as SPECs 055 a 060 sem
medir significaria um piloto inteiro sem noção de margem, e depois um backfill
de eventos que nunca foram capturados.

Este módulo **mede**. Não cobra.

    Usage Event  ≠  cobrança
    provider cost ≠  preço ao cliente

Tudo aqui nasce `PRE_LAUNCH_NON_BILLABLE`. Rating comercial, planos, invoices,
créditos e reconciliação são da **SPEC-062** e dependem de decisão do Founder.
Nenhum registro escrito aqui pode virar dívida automática — é a lei da
SPEC-062 §22.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

STATUS_PRE_LANCAMENTO = "PRE_LAUNCH_NON_BILLABLE"


class UsageService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    def registrar(
        self,
        *,
        company_id: str,
        source: str,
        work_run_id: Optional[str] = None,
        work_step_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        skill_slug: Optional[str] = None,
        capability_key: Optional[str] = None,
        tool_name: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        units: float = 0,
        unit_kind: str = "token",
        provider_cost_usd: float = 0,
        artifact_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Optional[dict]:
        """Grava um evento de consumo. Idempotente por `idempotency_key`.

        Falha aqui **não** derruba a execução: perder uma medição é ruim,
        interromper o trabalho do corretor por causa dela é pior.
        """
        chave = idempotency_key or (
            f"{company_id}:{work_run_id or '-'}:{work_step_id or '-'}:"
            f"{tool_name or model or source}:{uuid.uuid4().hex[:12]}"
        )

        registro = {
            "company_id": company_id,
            "work_run_id": work_run_id,
            "work_step_id": work_step_id,
            "correlation_id": correlation_id,
            "source": source,
            "skill_slug": skill_slug,
            "capability_key": capability_key,
            "tool_name": tool_name,
            "provider": provider,
            "model": model,
            "input_tokens": max(0, int(input_tokens or 0)),
            "output_tokens": max(0, int(output_tokens or 0)),
            "units": max(0, float(units or 0)),
            "unit_kind": unit_kind,
            "provider_cost_usd": max(0, float(provider_cost_usd or 0)),
            "artifact_id": artifact_id,
            "idempotency_key": chave,
            "billing_status": STATUS_PRE_LANCAMENTO,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            res = self.db.table("usage_events").insert(registro).execute()
            return (res.data or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).lower()
            if "duplicate" in msg or "unique" in msg:
                return None  # já medido — comportamento correto
            logger.warning("[Usage] evento não registrado (%s): %s", source, type(exc).__name__)
            return None

    def custo_do_run(self, company_id: str, work_run_id: str) -> dict:
        """Consumo acumulado de um run. Usado pelo budget da SPEC-055 §25."""
        try:
            res = (self.db.table("usage_events")
                   .select("input_tokens, output_tokens, provider_cost_usd, units")
                   .eq("company_id", company_id).eq("work_run_id", work_run_id).execute())
            linhas = res.data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[Usage] falha ao somar custo do run: %s", type(exc).__name__)
            return {"eventos": 0, "custo_usd": 0.0}

        return {
            "eventos": len(linhas),
            "input_tokens": sum(int(x.get("input_tokens") or 0) for x in linhas),
            "output_tokens": sum(int(x.get("output_tokens") or 0) for x in linhas),
            "custo_usd": round(sum(float(x.get("provider_cost_usd") or 0) for x in linhas), 6),
        }

    def orcamento_estourado(self, company_id: str, work_run_id: str,
                            budget_brl: Optional[float], cotacao_dolar: float = 6.0) -> bool:
        """Compara consumo com o teto do run.

        Retorna `False` quando não há teto — ausência de budget não é convite
        para gastar sem limite, mas travar por falta de configuração seria
        pior no ambiente atual. O teto real vira obrigatório na SPEC-062.
        """
        if not budget_brl or budget_brl <= 0:
            return False
        custo = self.custo_do_run(company_id, work_run_id)
        return (custo["custo_usd"] * cotacao_dolar) >= float(budget_brl)
