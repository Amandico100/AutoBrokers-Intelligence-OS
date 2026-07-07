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
    session_id: Optional[str] = Field(default=None, description="(injetado pelo runtime — NÃO preencher)")


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
    supabase_client: object = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, case_id: str = "", supabase_client=None, **kwargs):
        super().__init__(**kwargs)
        self.company_id = str(company_id or "")
        self.case_id = str(case_id or "")
        self.supabase_client = supabase_client

    _PLAYBOOK_REF = "allianz-residencial-whatsapp@v1"

    def _attendance_agent_id(self) -> Optional[str]:
        """Resolve o agente ATENDENTE (role attendance) — a integracao WhatsApp e
        vinculada a ele; sem o agent_id o lookup e ESTRITO e volta None (mesmo bug
        do heads-up de vidros). Best-effort."""
        client = getattr(self.supabase_client, "client", self.supabase_client)
        if client is None:
            return None
        try:
            res = client.table("agents").select("id").eq(
                "company_id", self.company_id).eq("agent_role", "attendance").eq(
                "is_active", True).limit(1).execute()
            if res.data:
                return str(res.data[0]["id"])
        except Exception:  # noqa: BLE001
            pass
        return None

    @staticmethod
    def _extract_slots(kwargs: dict) -> tuple:
        subservice = str(kwargs.get("subservice") or "").strip().lower()
        slots = {
            k: v for k, v in kwargs.items()
            if k not in ("subservice", "session_id") and v not in (None, "")
        }
        return subservice, slots

    def _run(self, **kwargs) -> dict:
        """Valida e monta o plano. NUNCA envia nada — o envio real (gate aberto)
        acontece só no _arun. Honestidade: sem envio, sem alegar acionamento."""
        from app.services.insurer_dispatch_service import build_dry_run_plan

        subservice, slots = self._extract_slots(kwargs)
        plan = build_dry_run_plan(self._PLAYBOOK_REF, subservice, slots)

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

        lines = [
            "[ACIONAMENTO PREPARADO EM SIMULAÇÃO (NADA foi enviado à seguradora)]",
            f"Subserviço: {plan['subservice']} · Playbook: {plan['playbook_ref']}",
            "Sequência que será enviada à seguradora:",
        ]
        for step in plan["steps"]:
            lines.append(f"  {step['step']}: {step['reply']}")
        lines.append(plan["note"])
        lines.append(
            "INSTRUÇÃO AO ATENDENTE: diga ao cliente que o pedido está registrado e será acionado em instantes; "
            "NÃO afirme que a seguradora já foi acionada nem invente protocolo/prazo."
        )
        return {"status": "ready_to_send", "content": "\n".join(lines), "plan": plan}

    async def _arun(self, **kwargs) -> dict:
        """Caminho LIVE (S17-6): com o gate aberto, cria a sessão real, envia a
        abertura à seguradora pela integração da corretora e ativa o roteador.
        Qualquer pré-condição faltando → resposta honesta SEM envio."""
        import os

        from app.services.insurer_dispatch_service import dispatch_live_enabled

        base = self._run(**kwargs)
        if base.get("status") != "ready_to_send" or not dispatch_live_enabled():
            return base

        digits = lambda s: "".join(ch for ch in str(s or "") if ch.isdigit())  # noqa: E731
        insurer_phone = digits(os.getenv("INSURER_CONTACT_ALLIANZ_ASSISTENCIA_24H", ""))
        if not insurer_phone:
            base["content"] += (
                "\nAVISO INTERNO: gate LIVE aberto mas o contato da seguradora não está configurado "
                "(INSURER_CONTACT_ALLIANZ_ASSISTENCIA_24H) — NADA foi enviado. Não afirme acionamento."
            )
            return base

        # Telefone do cliente vem da sessão WhatsApp (whatsapp:{phone}:{company}:{agent}).
        session_ref = str(kwargs.get("session_id") or "")
        parts = session_ref.split(":")
        client_phone = digits(parts[1]) if len(parts) >= 3 and parts[0] == "whatsapp" else ""
        if not client_phone:
            base["content"] += (
                "\nAVISO INTERNO: acionamento REAL só é iniciado na conversa de WhatsApp do cliente "
                "(telefone da sessão indisponível) — NADA foi enviado. Não afirme acionamento."
            )
            return base

        try:
            from app.services.integration_service import get_integration_service
            from app.services.whatsapp_service import get_whatsapp_service

            svc = get_integration_service()
            integration = svc.get_whatsapp_integration(self.company_id, self._attendance_agent_id())
            if not integration:  # fallback: integracao ativa sem agente
                integration = svc.get_whatsapp_integration(self.company_id)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[InsurerDispatch] integração indisponível: {type(e).__name__}")
            integration = None
        if not integration:
            base["content"] += (
                "\nAVISO INTERNO: canal WhatsApp da corretora indisponível — NADA foi enviado. "
                "Não afirme acionamento."
            )
            return base

        wa = get_whatsapp_service()

        def _sender(text: str) -> None:
            wa.send_message(insurer_phone, text, integration)

        from app.services.dispatch_router import start_live_dispatch

        subservice, slots = self._extract_slots(kwargs)
        result = await start_live_dispatch(
            company_id=self.company_id,
            case_id=self.case_id or f"wa-{client_phone}",
            playbook_ref=self._PLAYBOOK_REF,
            subservice=subservice,
            slots=slots,
            client_phone=client_phone,
            insurer_phone=insurer_phone,
            sender=_sender,
        )
        if not result.get("ok"):
            if result.get("error") == "dispatch_already_active":
                return {
                    "status": "already_active",
                    "content": (
                        "Já existe um acionamento EM ANDAMENTO com a seguradora para esta corretora. "
                        "NÃO abra outro. Informe ao cliente que o acionamento está em andamento e que "
                        "você avisa assim que a seguradora confirmar."
                    ),
                }
            base["content"] += "\nAVISO INTERNO: não foi possível iniciar o acionamento real — NADA foi enviado."
            return base

        return {
            "status": "dispatched",
            "content": (
                "[ACIONAMENTO REAL INICIADO]\n"
                "A conversa com a Allianz Assistência 24h foi aberta pelo WhatsApp da corretora. "
                "A URA será respondida automaticamente com os dados coletados e o cliente será avisado "
                "assim que o protocolo/agendamento sair.\n"
                "INSTRUÇÃO AO ATENDENTE: diga ao cliente que o acionamento FOI iniciado e que você retorna "
                "com o protocolo em instantes. NÃO invente protocolo/senha/prazo — eles chegam sozinhos."
            ),
        }
