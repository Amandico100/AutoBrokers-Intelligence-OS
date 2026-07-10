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
import re
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class InsurerDispatchInput(BaseModel):
    subservice: str = Field(description=(
        "Subserviço. Residencial: eletricista | chaveiro | encanador | eletrodomesticos. "
        "AUTO: guincho | bateria | pneu | chaveiro."))
    insurer_key: Optional[str] = Field(default=None, description=(
        "Seguradora da apólice (allianz | porto | hdi | yelum | tokio | alfa | azul | bradesco | mapfre | zurich). "
        "Descubra pela InfoCap; para assistência AUTO é OBRIGATÓRIO. Residencial sem isso assume Allianz."))
    titular_nascimento: Optional[str] = Field(default=None, description=(
        "[auto Mapfre] Data de nascimento do titular (dd/mm/aaaa) — a Mapfre valida identidade com ela"))
    line_kind: Optional[str] = Field(default=None, description="Linha: auto | residencial. Para carro use 'auto'.")
    titular_cpf: Optional[str] = Field(default=None, description="CPF do titular da apólice (somente dígitos)")
    # --- Residencial ---
    endereco_numero: Optional[str] = Field(default=None, description="[residencial] Número da residência do endereço da apólice")
    periodo_preferido: Optional[str] = Field(default=None, description="[residencial] Período: manha | tarde")
    risco_confirmado_sem_fumaca: Optional[str] = Field(default=None, description="[residencial elétrica] 'sim' se NÃO há fumaça/faísca/cheiro de queimado")
    aparelho_marca_modelo: Optional[str] = Field(default=None, description="[residencial eletrodomésticos] marca e modelo")
    aparelho_idade: Optional[str] = Field(default=None, description="[residencial eletrodomésticos] idade aproximada")
    # --- Auto ---
    veiculo_placa: Optional[str] = Field(default=None, description="[auto] Placa (a InfoCap resolve; NÃO invente)")
    local_atual: Optional[str] = Field(default=None, description="[auto] Onde o veículo está agora (endereço/CEP + referência)")
    local_destino: Optional[str] = Field(default=None, description="[auto guincho] Para onde levar o veículo")
    pessoa_no_local: Optional[str] = Field(default=None, description="[auto] Nome de quem está com o veículo no local")
    quando: Optional[str] = Field(default=None, description="[auto] 'agora' (urgência) ou uma data para agendar")
    ponto_referencia: Optional[str] = Field(default=None, description="[auto] Ponto de referência do local (ou 'não tem')")
    # --- Comuns ---
    telefone_contato: Optional[str] = Field(default=None, description="Telefone de contato com DDD (somente dígitos)")
    problema_descricao: Optional[str] = Field(default=None, description="Descrição curta do problema relatado pelo cliente")
    dados_confirmados: Optional[bool] = Field(default=None, description=(
        "[auto] true SOMENTE depois de você MOSTRAR ao cliente na conversa a placa, o veículo, o local, o destino "
        "e o telefone, e ele CONFIRMAR explicitamente. Sem essa confirmação o acionamento não sai."))
    session_id: Optional[str] = Field(default=None, description="(injetado pelo runtime — NÃO preencher)")


class InsurerDispatchTool(BaseTool):
    name: str = "insurer_dispatch"
    description: str = (
        "Prepara/aciona a assistência na seguradora pelo WhatsApp quando o levantamento estiver completo E a "
        "apólice tiver assistência confirmada. Cobre AUTO (guincho/bateria/pneu/chaveiro) e residencial "
        "(eletricista/chaveiro/encanador/eletrodomésticos). Para AUTO informe insurer_key (da InfoCap) e "
        "line_kind='auto'. Retorna o plano do acionamento ou os dados que ainda faltam. NUNCA diga ao cliente "
        "que acionou se o retorno indicar simulação; o passo final que despacha o prestador é sempre humano."
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

    _PLAYBOOK_REF = "allianz-residencial-whatsapp@v1"  # default residencial (compat)

    def _resolve_playbook_ref(self, kwargs: dict) -> tuple:
        """Resolve (playbook_ref, insurer_key) por insurer_key + linha. AUTO exige
        insurer_key; residencial sem insurer cai no default Allianz residencial."""
        from app.services.corridor_playbooks import resolve_playbook_ref

        insurer = str(kwargs.get("insurer_key") or "").strip()
        line = str(kwargs.get("line_kind") or "").strip().lower()
        subservice = str(kwargs.get("subservice") or "").strip().lower()
        if not line:
            line = "auto" if subservice in ("guincho", "bateria", "pneu") else ""
        if line == "auto":
            ref = resolve_playbook_ref(insurer, "auto") if insurer else None
            return ref, insurer
        if insurer:
            ref = resolve_playbook_ref(insurer, "residencial")
            if ref:
                return ref, insurer
        return self._PLAYBOOK_REF, "allianz"

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
            if k not in ("subservice", "session_id", "insurer_key", "line_kind", "dados_confirmados")
            and v not in (None, "")
        }
        return subservice, slots

    def _run(self, **kwargs) -> dict:
        """Valida e monta o plano. NUNCA envia nada — o envio real (gate aberto)
        acontece só no _arun. Honestidade: sem envio, sem alegar acionamento."""
        from app.services.insurer_dispatch_service import build_dry_run_plan

        subservice, slots = self._extract_slots(kwargs)
        playbook_ref, insurer_key = self._resolve_playbook_ref(kwargs)
        if not playbook_ref:
            return {"status": "error", "content": (
                f"Não tenho um corredor de assistência auto para a seguradora '{insurer_key or '?'}' ainda. "
                "Colete os dados e acione um atendente humano para seguir com a seguradora.")}

        # GUARDA ANTI-INVENÇÃO (incidente 2026-07-10: placa e telefone inventados
        # foram parar na seguradora). Determinístico, fora do alcance do LLM:
        is_auto = "auto" in str(playbook_ref)
        digits_only = "".join(ch for ch in str(kwargs.get("telefone_contato") or "") if ch.isdigit())
        if digits_only and re.search(r"(\d)\1{4,}", digits_only):
            return {"status": "missing_data", "missing": ["telefone_contato"], "content": (
                "O telefone informado parece placeholder (dígitos repetidos). Pergunte ao cliente o telefone "
                "REAL de quem estará com o veículo — nunca preencha com número genérico.")}
        if is_auto and not kwargs.get("dados_confirmados"):
            placa = str(kwargs.get("veiculo_placa") or "—")
            return {"status": "confirm_first", "content": (
                "ANTES de acionar, CONFIRME com o cliente NA CONVERSA (mensagem única): "
                f"placa {placa}, o que houve, local atual, destino e telefone de contato. "
                "Se o cliente corrigir qualquer dado, use o valor corrigido. Depois chame de novo com "
                "dados_confirmados=true. NÃO diga que já acionou.")}

        plan = build_dry_run_plan(playbook_ref, subservice, slots)

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
                    "veiculo_placa": "placa do veículo (a InfoCap costuma ter — confirme)",
                    "titular_nascimento": "data de nascimento do titular (a Mapfre exige para validar)",
                    "local_atual": "onde o veículo está agora (endereço com referência)",
                    "local_destino": "para onde levar o veículo (destino do guincho)",
                    "quando": "quando precisa (agora ou uma data para agendar)",
                    "pessoa_no_local": "quem vai estar com o veículo no local",
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

        from app.services.corridor_playbooks import insurer_contact_env_var, resolve_insurer_contact

        playbook_ref, insurer_key = self._resolve_playbook_ref(kwargs)
        line = "auto" if str(kwargs.get("line_kind") or "").lower() == "auto" or str(kwargs.get("subservice") or "").lower() in ("guincho", "bateria", "pneu") else "residencial"
        digits = lambda s: "".join(ch for ch in str(s or "") if ch.isdigit())  # noqa: E731
        insurer_phone = resolve_insurer_contact(insurer_key or "allianz", line_kind=line)
        if not insurer_phone:
            base["content"] += (
                f"\nAVISO INTERNO: gate LIVE aberto mas o contato da seguradora não está configurado "
                f"({insurer_contact_env_var(insurer_key or 'allianz', line)}) — NADA foi enviado. Não afirme acionamento."
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
            playbook_ref=playbook_ref,
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
