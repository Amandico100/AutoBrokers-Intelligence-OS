"""Ferramenta DEDICADA de veículo/placa (SPEC-034 — fix 15/07).

Problema (founder): o Chat Principal "não conseguia buscar a placa". A placa não
vem no /documento (só financeiro) — vive no /itens da CorpAPI. A infocap_tool só
enriquece placa como efeito colateral de uma busca de apólice que caia em AUTO;
quando o corretor pede DIRETO "qual a placa do fulano?", faltava um caminho
explícito. Esta tool é esse caminho: CPF → /itens → placa/veículo/chassi, sempre.

Multi-tenant: company_id é injetado pelo runtime (NUNCA vem do LLM) — cada
corretora só lê a PRÓPRIA InfoCap. Read-only.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class VehicleLookupInput(BaseModel):
    document: str = Field(description="CPF ou CNPJ do titular da apólice (só dígitos ou formatado)")
    policy_number: Optional[str] = Field(default=None, description="Número da apólice (opcional, p/ desambiguar)")


class VehicleLookupTool(BaseTool):
    name: str = "buscar_veiculo"
    description: str = (
        "Busca os DADOS DO VEÍCULO de uma apólice de AUTO na InfoCap: placa, modelo/veículo, "
        "chassi, FIPE — e o contato do cliente (telefone/endereço) quando houver. "
        "Use SEMPRE que o corretor pedir a placa, o carro, o veículo ou o chassi de um cliente. "
        "Passe o CPF/CNPJ do titular. A placa vem da fonte oficial — NUNCA invente placa."
    )
    args_schema: type = VehicleLookupInput
    company_id: str = ""

    def _run(self, document: str, policy_number: Optional[str] = None) -> Dict[str, Any]:
        # Ponte sync->async (fix 19/07: mesmo bug das tools de visão operacional
        # — o runtime pode invocar pelo caminho síncrono).
        try:
            from app.agents.tools.operations_tools import _run_sync

            return _run_sync(self._arun(document, policy_number))  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001
            logger.error(f"[VehicleLookupTool] _run erro: {type(e).__name__}")
            return {"content": "Não consegui consultar o veículo agora. Tente novamente.", "found": False}

    async def _arun(self, document: str, policy_number: Optional[str] = None) -> Dict[str, Any]:
        try:
            import os

            from app.providers.policy_data_provider import get_policy_data_provider

            provider = get_policy_data_provider("infocap")
            if not provider or not hasattr(provider, "vehicle"):
                return {"content": "Fonte de veículos indisponível.", "found": False}
            key = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
            doc = "".join(ch for ch in str(document or "") if ch.isdigit())
            if len(doc) not in (11, 14):
                return {"content": "Informe um CPF (11) ou CNPJ (14) válido do titular.", "found": False}
            info = await provider.vehicle(
                company_id=self.company_id, document=doc,
                policy_number=(policy_number or None), internal_key=key,
            )
            veh = (info or {}).get("vehicle") or {}
            cli = (info or {}).get("client") or {}
            if not info.get("ok") or not (veh.get("placa") or veh.get("veiculo")):
                return {"content": ("Não encontrei apólice de AUTO vigente com veículo para esse CPF/CNPJ na InfoCap. "
                                    "Confirme o documento ou verifique se a apólice está ativa."),
                        "found": False}
            out = {
                "placa": str(veh.get("placa") or "").strip().upper(),
                "veiculo": str(veh.get("veiculo") or "").strip(),
                "chassi": str(veh.get("chassi") or "").strip(),
                "fipe": str(veh.get("fipe") or veh.get("codigo_fipe") or "").strip(),
            }
            if cli.get("telefone") or cli.get("phone"):
                out["telefone_cliente"] = str(cli.get("telefone") or cli.get("phone")).strip()
            content = f"Veículo da apólice: {out['veiculo'] or '—'} — placa {out['placa'] or '—'}"
            if out["chassi"]:
                content += f" — chassi {out['chassi']}"
            return {"content": content, "data": out, "found": True}
        except Exception as e:  # noqa: BLE001
            logger.error(f"[VehicleLookupTool] erro: {type(e).__name__}")
            return {"content": "Não consegui consultar o veículo agora. Tente novamente.", "found": False}
