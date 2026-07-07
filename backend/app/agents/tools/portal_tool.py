"""SPEC-020 P3 + SPEC-025 — portal_action: o cerebro Smith aciona um portal (vidros).

Cerebro unico: o AGENTE decide (a partir da conversa com o segurado) e chama esta
tool; o portal-worker EXECUTA e volta com o resultado. SPEC-025: os FATOS da
apolice (placa, veiculo, chassi, endereco, seguradora) sao buscados AQUI, na
InfoCap (/itens + /cliente_cpf), server-side — o LLM NUNCA fornece placa/local
(era isso que fazia o agente inventar ABC1D23/Sao Paulo). O LLM so passa o que e
julgamento: CPF (da conversa), qual apolice (se varias), data do dano e o relato.

A tool NUNCA finaliza o pedido sozinha (confirm=False -> journey para na tela de
confirmacao); o envio real e um passo de aprovacao separado. Gate
PORTAL_REAL_ENABLED (no worker) off ate o founder ligar.

Identidade do solicitante (multi-tenant): PERFIL DE ACIONAMENTO da corretora
(companies), nunca do segurado nem inventado. Logica pura em portal_params.py.
"""
from __future__ import annotations

import asyncio
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
    cpf_cnpj: str = Field(description="CPF/CNPJ do segurado (titular da apolice) — da conversa")
    data_dano: str = Field(description="Data do dano DD/MM/AAAA")
    policy_number: Optional[str] = Field(
        default=None,
        description="Numero da apolice AUTO escolhida (SO quando o cliente tiver mais de uma apolice auto ativa)")
    peca: Optional[str] = Field(default=None, description="Peca danificada (ex: 'vidro de porta', 'parabrisa', 'retrovisor') — voce decide pela conversa")
    como_ocorreu: Optional[str] = Field(default=None, description="Como ocorreu o dano (ex: 'encontrou o veiculo danificado', 'pedra na estrada')")
    onde_ocorreu: Optional[str] = Field(default=None, description="Onde ocorreu (ex: 'urbano', 'rodoviario')")
    descricao: Optional[str] = Field(default=None, description="Descricao livre do ocorrido (min 30 caracteres)")
    placa_informada: Optional[str] = Field(
        default=None,
        description="APENAS se a ferramenta pediu a placa (apolice sem placa na InfoCap) e o CLIENTE informou. NUNCA deduza/invente.")
    session_id: Optional[str] = Field(default=None, description="(injetado pelo runtime — NAO preencher)")


class PortalActionTool(BaseTool):
    name: str = "portal_action"
    description: str = (
        "Abre o atendimento de VIDROS/farois/lanternas/retrovisores no portal da seguradora. "
        "Use quando o segurado precisar de servico de vidros e voce ja tiver: CPF, data do dano e o relato "
        "do que aconteceu. A ferramenta busca SOZINHA os dados reais da apolice (placa, veiculo, endereco, "
        "seguradora) na InfoCap — NAO peca placa/CEP/endereco ao cliente. Se houver mais de uma apolice AUTO "
        "ativa, ela devolve as opcoes para voce perguntar qual. Ela avisa o cliente que esta abrindo e volta "
        "com o resultado. NAO finaliza sozinha o pedido."
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
        nunca ficar no silencio enquanto o portal roda (~1 min). Best-effort."""
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

    def _load_profile(self) -> dict:
        """Solicitante = identidade da CORRETORA (multi-tenant). REUSA os 'Dados da
        Corretora' (primary_contact_*/cnpj); acionamento_profile e override opcional."""
        profile = {}
        try:
            res = self._client().table("companies").select(
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
        return profile

    async def _fetch_infocap(self, cpf: str, policy_number: Optional[str]) -> dict:
        """SPEC-025: fatos reais da apolice AUTO (placa/veiculo/endereco) via porta
        PolicyDataProvider (InfoCap /itens + /cliente_cpf). Nunca inventa."""
        import os

        from app.core.database import create_async_supabase_client
        from app.providers.policy_data_provider import get_policy_data_provider

        key = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
        provider = get_policy_data_provider("infocap")
        if provider is None or not hasattr(provider, "vehicle") or not key:
            return {"ok": False, "status": "provider_unavailable"}
        db = await create_async_supabase_client()
        return await provider.vehicle(
            company_id=self.company_id, document=cpf,
            policy_number=policy_number, db=db, internal_key=key,
        )

    async def _arun(self, **flat) -> dict:
        session_id = str(flat.pop("session_id", "") or "")
        cpf = str(flat.get("cpf_cnpj") or "").strip()
        if not cpf:
            return {"content": "Preciso do CPF/CNPJ do segurado (da conversa) para acionar."}

        # 1) FATOS da apolice — InfoCap server-side (o LLM nao fornece placa/local).
        info = await self._fetch_infocap(cpf, str(flat.get("policy_number") or "").strip() or None)
        status = str(info.get("status") or "")
        if status == "multiple_auto_policies":
            opts = info.get("options") or []
            linhas = "; ".join(
                f"{o.get('numapo')} — {o.get('seguradora')} ({o.get('veiculo') or 'veiculo?'} placa {o.get('placa') or '?'})"
                for o in opts[:5]
            )
            return {"content": f"O cliente tem mais de uma apolice AUTO ativa. Pergunte QUAL e chame de novo "
                               f"com policy_number. Opcoes: {linhas}"}
        if status == "no_auto_policy":
            return {"content": "Nao encontrei apolice AUTO para este CPF na InfoCap. Confirme com o cliente "
                               "se o seguro do carro e por esta corretora (ou se o CPF esta certo)."}
        if not info.get("ok"):
            return {"content": "A InfoCap nao respondeu agora (nao consegui buscar os dados da apolice). "
                               "Tente de novo em instantes; se persistir, acione um humano."}

        # 2) params = fatos (InfoCap) + julgamento (LLM) + solicitante (corretora)
        params, err = build_portal_params(flat, self._load_profile(), info)
        if err:
            return {"content": err}

        # 3) Enfileira o job para o portal-worker.
        try:
            ins = self._client().table("portal_jobs").insert({
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

        # Ack IMEDIATO pro segurado: nunca deixa ele no silencio enquanto o portal roda.
        veic = (params.get("segurado") or {}).get("veiculo") or "seu veiculo"
        self._notify(
            session_id,
            f"🔧 To abrindo seu atendimento de vidros agora ({veic}, placa {params.get('placa')}) — "
            "leva mais ou menos 1 minutinho. Ja te trago a confirmacao, so um instante 🙂",
        )

        # 4) Aguarda o worker terminar (o segurado esta na conversa). asyncio.sleep:
        # NAO bloqueia o event loop (o time.sleep antigo travava o atendente inteiro).
        deadline = time.time() + POLL_TIMEOUT_S
        while time.time() < deadline:
            await asyncio.sleep(POLL_EVERY_S)
            try:
                r = self._client().table("portal_jobs").select("status, evidence, error").eq("id", job_id).limit(1).execute()
                job = r.data[0] if r.data else {}
            except Exception:  # noqa: BLE001
                continue
            if str(job.get("status")) in ("done", "needs_human", "failed"):
                return {"content": format_result(job)}
        return {"content": format_result({"status": "queued"})}

    def _run(self, **flat) -> dict:
        return {"content": "portal_action deve ser executada de forma assincrona."}
