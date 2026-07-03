"""Ferramenta de acionamento de seguradora para o ATENDENTE (SPEC-017 P5).

Papel attendance usa esta tool quando o levantamento estiver completo:
- valida elegibilidade operacional (slots mínimos do playbook);
- monta o PLANO exato do acionamento (dry-run enquanto o gate S17-6 estiver
  fechado — nada é enviado à seguradora sem liberação do Founder);
- devolve briefing para o atendente informar o cliente com honestidade
  ("estou acionando" só quando for real; em simulação, registra pendência).

Playbook v1: allianz-residencial-whatsapp@v1 (eletricista, chaveiro, encanador,
eletrodomésticos).
"""

import logging
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class InsurerDispatchInput(BaseModel):
    subservice: str = Field(description="Subserviço: eletricista | chaveiro | encanador | eletrodomesticos")
    titular_cpf: Optional[str] = Field(default=None, description="CPF do titular da apólice (somente dígitos)")
    endereco_numero: Optional[str] = Field(default=None, description="Número da residência do endereço da apólice")
    telefone_contato: Optional[str] = Field(default=None, description="Telefone de contato com DDD (somente dígitos)")
    problema_descricao: Optional[str] = Field(default=None, description="Descrição curta do problema relatado pelo cliente")
    periodo_preferido: Optional[str] = Field(default=None, description="Período preferido: manha | tarde (a partir do próximo dia útil)")
    risco_confirmado_sem_fumaca: Optional[str] = Field(default=None, description="Para elétrica: 'sim' confirmando que NÃO há fumaça/faísca/cheiro de queimado")
    aparelho_marca_modelo: Optional[str] = Field(default=None, description="Para eletrodomésticos: marca e modelo")
    aparelho_idade: Optional[str] = Field(default=None, description="Para eletrodomésticos: idade aproximada")


class InsurerDispatchTool(BaseTool):
    name: str = "insurer_dispatch"
    description: str = (
        "Prepara/aciona a assistência na seguradora (Allianz Residencial via WhatsApp) quando o levantamento "
        "estiver completo E a apólice tiver assistência confirmada. Retorna o plano do acionamento ou os dados "
        "que ainda faltam coletar. NUNCA diga ao cliente que acionou se o retorno indicar modo simulação."
    )
    args_schema: Type[BaseModel] = InsurerDispatchInput

    company_id: str = ""
    case_id: str = ""

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, case_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.company_id = str(company_id or "")
        self.case_id = str(case_id or "")

    def _run(self, **kwargs) -> dict:
        from app.services.insurer_dispatch_service import build_dry_run_plan, dispatch_live_enabled

        subservice = str(kwargs.get("subservice") or "").strip().lower()
        slots = {k: v for k, v in kwargs.items() if k != "subservice" and v not in (None, "")}
        plan = build_dry_run_plan("allianz-residencial-whatsapp@v1", subservice, slots)

        if not plan.get("ok"):
            if plan.get("missing_slots"):
                friendly = {
                    "titular_cpf": "CPF do titular",
                    "endereco_numero": "número da residência",
                    "telefone_contato": "telefone de contato",
                    "problema_descricao": "descrição do problema",
                    "periodo_preferido": "período preferido (manhã ou tarde)",
                    "risco_confirmado_sem_fumaca": "confirmação de que NÃO há fumaça/faísca/cheiro de queimado",
                    "aparelho_marca_modelo": "marca e modelo do aparelho",
                    "aparelho_idade": "idade aproximada do aparelho",
                }
                faltam = [friendly.get(s, s) for s in plan["missing_slots"]]
                return {
                    "status": "missing_data",
                    "missing": plan["missing_slots"],
                    "content": "Ainda faltam estes dados para acionar: " + "; ".join(faltam) + ". Pergunte UM de cada vez, com naturalidade.",
                }
            return {"status": "error", "content": f"Não foi possível preparar o acionamento ({plan.get('error')}). Acione um atendente humano."}

        live = bool(plan.get("live")) and dispatch_live_enabled()
        header = "ACIONAMENTO PRONTO" if live else "ACIONAMENTO PREPARADO EM SIMULAÇÃO (gate fechado — NADA foi enviado à seguradora)"
        lines = [f"[{header}]", f"Subserviço: {plan['subservice']} · Playbook: {plan['playbook_ref']}", "Sequência que será enviada à seguradora:"]
        for step in plan["steps"]:
            lines.append(f"  {step['step']}: {step['reply']}")
        lines.append(plan["note"])
        if not live:
            lines.append(
                "INSTRUÇÃO AO ATENDENTE: diga ao cliente que o pedido está registrado e será acionado em instantes; "
                "NÃO afirme que a seguradora já foi acionada nem invente protocolo/prazo."
            )
        return {"status": "ready_to_send" if not live else "dispatched", "content": "\n".join(lines), "plan": plan}
