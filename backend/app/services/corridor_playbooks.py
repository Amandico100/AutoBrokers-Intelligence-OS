"""Playbooks de corredor (SPEC-017 P4 / S17-4) — corredores como DADOS versionados.

Um playbook descreve como acionar a seguradora em um canal:
- fase URA: âncoras de menu → respostas determinísticas (sem LLM);
- dados mínimos por subserviço (slots);
- âncoras de captura (protocolo, senha, agendamento);
- gatilhos de handoff (fail-safe: passo desconhecido NUNCA responde às cegas).

Seed v1: Allianz Residencial WhatsApp — minerado da conversa real da corretora
com a Allianz Assistência 24h (fluxo comprovado, valores sintéticos).
O contato real da seguradora vem da configuração da corretora/plataforma
(insurer_contact_ref), NUNCA hard-coded aqui.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional


def _norm(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


# ---------------------------------------------------------------------------
# Seed: Allianz Residencial WhatsApp v1
# ---------------------------------------------------------------------------

ALLIANZ_RESIDENCIAL_WHATSAPP_V1: Dict[str, Any] = {
    "playbook_id": "allianz-residencial-whatsapp",
    "version": 1,
    "insurer_key": "allianz",
    "line_kind": "residencial",
    "channel": "whatsapp",
    "insurer_contact_ref": "allianz_assistencia_24h",  # resolvido por config da corretora
    "description": "Assistência 24h residencial Allianz via WhatsApp (URA numerada + especialista humano).",
    # Fase URA: âncora (regex sobre a mensagem da seguradora) -> resposta.
    # {campo} = slot do caso. Ordem importa (primeiro match vence).
    "ura_steps": [
        {
            "step": "menu_tipo_seguro",
            "anchor": r"assist[êe]ncia 24h para qual seguro",
            "reply": "2",
            "notes": "1-Auto 2-Residência/Empresa/Condomínio 3-Vida 4-Viagem 5-Outros",
        },
        {
            "step": "menu_qual_seguro",
            "anchor": r"qual o seguro que deseja utilizar",
            "reply": "1",
            "notes": "1-Residência/Condomínio/Empresa 2-Auto com serviços residenciais",
        },
        {
            "step": "pedir_cpf",
            "anchor": r"digite o \*?cpf\*? ou \*?cnpj\*?",
            "reply": "{titular_cpf}",
            "requires": ["titular_cpf"],
        },
        {
            "step": "confirmar_endereco",
            "anchor": r"confirme o endere[çc]o para atendimento",
            "reply": "1",
            "notes": "Opção 1 = endereço da apólice. Divergência de endereço → handoff.",
        },
        {
            "step": "numero_residencia",
            "anchor": r"informe o n[úu]mero da resid[êe]ncia",
            "reply": "{endereco_numero}",
            "requires": ["endereco_numero"],
        },
        {
            "step": "confirmar_telefone",
            "anchor": r"deseja adicionar outro n[úu]mero",
            "reply": "{telefone_adicionar_opcao}",
            "requires": ["telefone_adicionar_opcao"],
            "notes": "1=Sim (informar telefone_contato) · 2=Não (usa o registrado)",
        },
        {
            "step": "informar_telefone",
            "anchor": r"informe \*?o n[úu]mero de celular completo\*? com ddd",
            "reply": "{telefone_contato}",
            "requires": ["telefone_contato"],
        },
        {
            "step": "confirmar_telefone_anotado",
            "anchor": r"anotei seu n[úu]mero",
            "reply": "1",
        },
        {
            "step": "menu_tipo_servico",
            "anchor": r"informe o tipo de\s+servi[çc]o",
            "reply": "{tipo_servico_opcao}",
            "requires": ["tipo_servico_opcao"],
            "notes": "1=casa (encanador/eletricista/chaveiro) · 2=eletrodomésticos · 3=outros",
        },
    ],
    # Subserviços -> slots mínimos (do caso) antes de iniciar o acionamento.
    "subservices": {
        "eletricista": {
            "tipo_servico_opcao": "1",
            "required_slots": ["titular_cpf", "endereco_numero", "telefone_contato", "problema_descricao", "periodo_preferido", "risco_confirmado_sem_fumaca"],
        },
        "chaveiro": {
            "tipo_servico_opcao": "1",
            "required_slots": ["titular_cpf", "endereco_numero", "telefone_contato", "problema_descricao", "periodo_preferido"],
        },
        "encanador": {
            "tipo_servico_opcao": "1",
            "required_slots": ["titular_cpf", "endereco_numero", "telefone_contato", "problema_descricao", "periodo_preferido"],
        },
        "eletrodomesticos": {
            "tipo_servico_opcao": "2",
            "required_slots": ["titular_cpf", "endereco_numero", "telefone_contato", "aparelho_marca_modelo", "aparelho_idade", "problema_descricao", "periodo_preferido"],
        },
    },
    # Fase humana da seguradora: orientação para a LLM (guardada) responder.
    "human_phase_guidance": (
        "Você fala com o especialista da assistência em nome da corretora. "
        "Apresente-se como a corretora, confirme titular/CPF quando pedido, descreva o problema com os dados do caso, "
        "responda agendamento com o período preferido do cliente (manhã 9-13 / tarde 13-18, a partir do próximo dia útil). "
        "Use SOMENTE dados do caso. Nunca invente. Se pedirem algo que não está no caso, registre pendência e pare."
    ),
    # Âncoras de captura no retorno da seguradora.
    "capture_anchors": {
        "protocol": r"n[úu]mero da assist[êe]ncia [ée]\s*:?\s*(\d{5,12})",
        "password": r"senha de acesso.*?(\d{4})",
        "schedule": r"agendad[ao] para o dia\s*(\d{1,2}(?:/\d{1,2}(?:/\d{2,4})?)?)\s*,?\s*entre\s*(\d{1,2}h)\s*e\s*(\d{1,2}h)",
    },
    # Regras fixas a repassar ao cliente junto do agendamento.
    "client_instructions": [
        "É necessário haver um maior de 18 anos no local para receber o prestador.",
        "O prestador vai pedir uma senha de acesso: são os 4 últimos números do telefone informado.",
    ],
    # Fail-safe.
    "handoff_triggers": [r"sinistro", r"n[ãa]o localizamos", r"cpf.*inv[áa]lido", r"n[ãa]o foi poss[íi]vel"],
    "unknown_step_policy": "pause_and_handoff",  # nunca responder às cegas
}

_PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    f"{ALLIANZ_RESIDENCIAL_WHATSAPP_V1['playbook_id']}@v{ALLIANZ_RESIDENCIAL_WHATSAPP_V1['version']}": ALLIANZ_RESIDENCIAL_WHATSAPP_V1,
}


def get_playbook(playbook_ref: str) -> Optional[Dict[str, Any]]:
    return _PLAYBOOKS.get(str(playbook_ref or "").strip())


def list_playbooks() -> List[str]:
    return sorted(_PLAYBOOKS.keys())


# ---------------------------------------------------------------------------
# Motor puro: match de URA, preenchimento de resposta, captura de âncoras
# ---------------------------------------------------------------------------

def match_ura_step(playbook: Dict[str, Any], insurer_message: str) -> Optional[Dict[str, Any]]:
    """Primeiro passo de URA cuja âncora casa com a mensagem da seguradora."""
    text = _norm(insurer_message)
    for step in playbook.get("ura_steps") or []:
        if re.search(step.get("anchor") or r"$^", text, re.IGNORECASE | re.DOTALL):
            return step
    return None


def render_reply(step: Dict[str, Any], slots: Dict[str, Any]) -> Dict[str, Any]:
    """Resposta do passo com slots aplicados. Slot faltante -> blocker (nunca chuta)."""
    template = str(step.get("reply") or "")
    missing = [f for f in (step.get("requires") or []) if not str(slots.get(f) or "").strip()]
    if missing:
        return {"ok": False, "missing": missing, "reply": None}
    try:
        return {"ok": True, "missing": [], "reply": template.format(**{k: str(v) for k, v in slots.items()})}
    except KeyError as exc:  # placeholder sem slot
        return {"ok": False, "missing": [str(exc).strip("'")], "reply": None}


def detect_handoff_trigger(playbook: Dict[str, Any], insurer_message: str) -> Optional[str]:
    text = _norm(insurer_message)
    for pattern in playbook.get("handoff_triggers") or []:
        if re.search(pattern, text, re.IGNORECASE):
            return pattern
    return None


def extract_capture_anchors(playbook: Dict[str, Any], insurer_message: str) -> Dict[str, Any]:
    """Protocolo/senha/agendamento SOMENTE por âncora real (nunca inventados)."""
    anchors = playbook.get("capture_anchors") or {}
    text = _norm(insurer_message)
    out: Dict[str, Any] = {}
    m = re.search(anchors.get("protocol") or r"$^", text, re.IGNORECASE)
    if m:
        out["protocol"] = m.group(1)
    m = re.search(anchors.get("password") or r"$^", text, re.IGNORECASE | re.DOTALL)
    if m:
        out["password"] = m.group(1)
    m = re.search(anchors.get("schedule") or r"$^", text, re.IGNORECASE)
    if m:
        out["schedule"] = {"day": m.group(1), "from": m.group(2), "to": m.group(3)}
    return out


def missing_slots_for_subservice(playbook: Dict[str, Any], subservice: str, slots: Dict[str, Any]) -> List[str]:
    sub = (playbook.get("subservices") or {}).get(str(subservice or "").strip().lower())
    if not sub:
        return ["subservico_invalido"]
    return [f for f in sub.get("required_slots") or [] if not str(slots.get(f) or "").strip()]
