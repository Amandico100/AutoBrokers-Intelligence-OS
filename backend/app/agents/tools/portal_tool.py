"""SPEC-020 P3 — portal_action: o cerebro Smith aciona um portal (vidros/corretor).

Cerebro unico: o AGENTE decide (a partir da conversa com o segurado + dados da
apolice via InfoCap) e chama esta tool; o portal-worker EXECUTA a journey
deterministica e volta com o resultado (protocolo ou "precisa de voce"). A tool
NUNCA finaliza o pedido sozinha (confirm=False -> journey para no 80%); o envio
real e um passo de aprovacao separado. Gate PORTAL_REAL_ENABLED (no worker) off
ate o founder ligar.

Identidade do solicitante (multi-tenant): vem do PERFIL DE ACIONAMENTO da
corretora (companies.acionamento_profile), nunca do segurado nem inventado.
Logica pura (build_portal_params/format_result) em portal_params.py (testavel).
"""
from __future__ import annotations

import logging
import time
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .portal_params import build_portal_params, format_result

logger = logging.getLogger(__name__)

POLL_TIMEOUT_S = 150
POLL_EVERY_S = 5


class PortalActionInput(BaseModel):
    insurer_name: str = Field(description="Seguradora do segurado (ex: 'Yelum', 'Tokio Marine', 'Porto')")
    cpf_cnpj: str = Field(description="CPF/CNPJ do segurado (titular da apolice)")
    placa: str = Field(description="Placa do veiculo segurado")
    data_dano: str = Field(description="Data do dano DD/MM/AAAA")
    peca: Optional[str] = Field(default=None, description="Peca danificada (ex: 'vidro de porta', 'parabrisa') — o AGENTE decide pela conversa")
    como_ocorreu: Optional[str] = Field(default=None, description="Como ocorreu o dano (ex: 'encontrou o veiculo danificado', 'pedra na estrada')")
    onde_ocorreu: Optional[str] = Field(default=None, description="Onde ocorreu (ex: 'urbano', 'rodoviario')")
    descricao: Optional[str] = Field(default=None, description="Descricao livre do ocorrido (min 30 caracteres)")
    estado: Optional[str] = Field(default=None, description="UF para o servico (ex: 'SC')")
    cidade: Optional[str] = Field(default=None, description="Cidade para o servico")
    cep: Optional[str] = Field(default=None, description="CEP do segurado (acha a loja mais proxima)")
    session_id: Optional[str] = Field(default=None, description="(injetado pelo runtime — NAO preencher)")


class PortalActionTool(BaseTool):
    name: str = "portal_action"
    description: str = (
        "Aciona o portal da seguradora para o segurado (ex: abrir atendimento de VIDROS/lanternas). "
        "Use quando o segurado precisar de um servico de vidros e voce ja tiver os dados (apolice/placa + "
        "o que aconteceu). Voce DECIDE peca/como/onde pela conversa. A ferramenta abre o pedido no portal e "
        "volta com o protocolo ou com o que falta decidir. NAO finaliza sozinha o pedido."
    )
    args_schema: Type[BaseModel] = PortalActionInput
    company_id: str = ""
    supabase_client: object = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, supabase_client=None, **kwargs):
        super().__init__(**kwargs)
        self.company_id = str(company_id or "")
        self.supabase_client = supabase_client

    def _client(self):
        return getattr(self.supabase_client, "client", self.supabase_client)

    def _notify(self, session_id: str, text: str) -> None:
        """Manda uma mensagem AGORA pro segurado (via WhatsApp da corretora), pra ele
        nunca ficar no silencio enquanto o portal roda (~1 min). Best-effort: se o
        canal nao estiver disponivel, apenas ignora (o acionamento segue)."""
        try:
            parts = str(session_id or "").split(":")
            if len(parts) < 3 or parts[0] != "whatsapp":
                return  # so notifica em sessao real de WhatsApp
            phone = "".join(ch for ch in parts[1] if ch.isdigit())
            if not phone:
                return
            from app.services.integration_service import get_integration_service
            from app.services.whatsapp_service import get_whatsapp_service

            integration = get_integration_service().get_whatsapp_integration(self.company_id)
            if not integration:
                return
            get_whatsapp_service().send_message(phone, text, integration)
        except Exception:  # noqa: BLE001
            pass

    def _run(self, **flat) -> dict:
        session_id = str(flat.pop("session_id", "") or "")
        client = self._client()
        # Solicitante = identidade da CORRETORA (multi-tenant). REUSA os "Dados da
        # Corretora" existentes (primary_contact_*/cnpj); acionamento_profile e so
        # override opcional. Nunca o segurado, nunca inventado.
        profile = {}
        try:
            res = client.table("companies").select(
                "company_name, legal_name, primary_contact_name, primary_contact_email, "
                "primary_contact_phone, cnpj, acionamento_profile"
            ).eq("id", self.company_id).limit(1).execute()
            if res.data:
                row = res.data[0]
                ov = row.get("acionamento_profile") or {}
                profile = {
                    "nome": ov.get("nome") or row.get("primary_contact_name") or row.get("legal_name") or row.get("company_name"),
                    "email": ov.get("email") or row.get("primary_contact_email"),
                    "telefone": ov.get("telefone") or row.get("primary_contact_phone"),
                    "cpf_cnpj": ov.get("cpf_cnpj") or row.get("cnpj"),
                }
        except Exception:  # noqa: BLE001
            pass

        params, err = build_portal_params(flat, profile)
        if err:
            return {"content": err}

        # Enfileira o job para o portal-worker.
        try:
            ins = client.table("portal_jobs").insert({
                "company_id": self.company_id,
                "portal_key": "vidros_lanternas",
                "journey": "abrir_atendimento",
                "params": params,
                "status": "queued",
            }).execute()
            job_id = ins.data[0]["id"] if ins.data else None
        except Exception as e:  # noqa: BLE001
            logger.error(f"[PortalAction] enfileirar falhou: {type(e).__name__}")
            return {"content": f"Nao consegui enfileirar o acionamento ({type(e).__name__})."}

        # Ack IMEDIATO pro segurado: nunca deixa ele no silencio enquanto o portal
        # roda (~1 min). O resultado real volta como retorno da tool logo abaixo.
        self._notify(
            session_id,
            "🔧 Tô abrindo seu atendimento no portal agora — leva mais ou menos 1 minutinho. "
            "Já te trago o número do protocolo, só um instante 🙂",
        )

        # Aguarda o worker terminar (o segurado esta na conversa).
        deadline = time.time() + POLL_TIMEOUT_S
        while time.time() < deadline:
            time.sleep(POLL_EVERY_S)
            try:
                r = client.table("portal_jobs").select("status, evidence, error").eq("id", job_id).limit(1).execute()
                job = r.data[0] if r.data else {}
            except Exception:  # noqa: BLE001
                continue
            if str(job.get("status")) in ("done", "needs_human", "failed"):
                return {"content": format_result(job)}
        return {"content": format_result({"status": "queued"})}

    async def _arun(self, **flat) -> dict:
        return self._run(**flat)
