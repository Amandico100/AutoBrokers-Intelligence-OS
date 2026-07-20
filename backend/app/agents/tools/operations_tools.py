"""SPEC-040 Onda 2 — Tools de VISÃO OPERACIONAL do Chat Principal (Missão B).

Leitura determinística e token-eficiente: o serviço monta o digest pronto;
a LLM só apresenta. company_id é injetado pelo runtime (NUNCA vem da LLM) —
cada corretora enxerga SÓ a própria operação. Mapas do Atlas são estrutura
GLOBAL das URAs (sem dado de cliente). Read-only por construção.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Coroutine, Optional

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _run_sync(coro: Coroutine[Any, Any, str]) -> str:
    """Ponte sync->async (fix 19/07: o runtime do chat pode invocar a tool
    pelo caminho SÍNCRONO — o placeholder 'deve ser assíncrona' vazava para o
    corretor). Sem loop rodando: asyncio.run; com loop: executa em thread."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result(timeout=30)


class OperationsSummaryInput(BaseModel):
    periodo: Optional[str] = Field(
        default="hoje", description="Período do resumo: 'hoje' (últimas 24h) ou 'semana' (7 dias)")


class OperationsSummaryTool(BaseTool):
    name: str = "resumo_atendimentos"
    description: str = (
        "Resumo REAL da operação de atendimento da corretora: acionamentos em andamento agora "
        "(seguradora, etapa, protocolo), movimento do período (iniciados, protocolos, handoffs) "
        "e qualidade auditada. Use SEMPRE que o corretor perguntar como estão os atendimentos, "
        "acionamentos ou a operação. Os dados vêm prontos do sistema — apresente com clareza e "
        "NUNCA invente números."
    )
    args_schema: type = OperationsSummaryInput
    company_id: str = ""

    def _run(self, periodo: Optional[str] = "hoje") -> str:
        try:
            return _run_sync(self._arun(periodo))
        except Exception as e:  # noqa: BLE001
            logger.error(f"[OperationsSummaryTool] _run erro: {type(e).__name__}")
            return "Não consegui consultar a operação agora. Tente novamente em instantes."

    async def _arun(self, periodo: Optional[str] = "hoje") -> str:
        try:
            from app.services.operational_view import operations_summary

            return await operations_summary(self.company_id, periodo or "hoje")
        except Exception as e:  # noqa: BLE001
            logger.error(f"[OperationsSummaryTool] erro: {type(e).__name__}")
            return "Não consegui consultar a operação agora. Tente novamente em instantes."


class AtlasRoutesInput(BaseModel):
    seguradora: Optional[str] = Field(
        default=None, description="Chave da seguradora (ex.: porto, allianz, hdi). Vazio = lista geral.")
    ramo: Optional[str] = Field(default=None, description="Ramo (ex.: auto, residencial). Opcional.")
    servico: Optional[str] = Field(
        default=None, description="Serviço para traçar o caminho na URA (ex.: guincho, bateria, chaveiro). Opcional.")


class AtlasRoutesTool(BaseTool):
    name: str = "atlas_rotas"
    description: str = (
        "Consulta os MAPAS DE ROTA das URAs das seguradoras (Atlas): quais fluxos já conhecemos, "
        "cobertura de cada mapa e o caminho passo a passo até um serviço (ex.: 'qual o caminho do "
        "guincho na Porto?'). Estrutura global de processo — sem nenhum dado de cliente. "
        "Use quando o corretor perguntar como funciona o fluxo/URA/atendimento de uma seguradora."
    )
    args_schema: type = AtlasRoutesInput

    def _run(self, seguradora: Optional[str] = None, ramo: Optional[str] = None,
             servico: Optional[str] = None) -> str:
        try:
            return _run_sync(self._arun(seguradora, ramo, servico))
        except Exception as e:  # noqa: BLE001
            logger.error(f"[AtlasRoutesTool] _run erro: {type(e).__name__}")
            return "Não consegui consultar os mapas do Atlas agora. Tente novamente em instantes."

    async def _arun(self, seguradora: Optional[str] = None, ramo: Optional[str] = None,
                    servico: Optional[str] = None) -> str:
        try:
            from app.services.operational_view import atlas_routes_summary

            return await atlas_routes_summary(seguradora, ramo, servico)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[AtlasRoutesTool] erro: {type(e).__name__}")
            return "Não consegui consultar os mapas do Atlas agora. Tente novamente em instantes."
