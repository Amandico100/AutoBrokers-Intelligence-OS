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

# ===========================================================================
# SPEC-031: Assistência AUTO no WhatsApp (multi-seguradora)
# Playbooks minerados das conversas REAIS da AutoFleet com as seguradoras
# (guincho/bateria/pneu/chaveiro). Vidro NÃO entra aqui — vai pelo portal.
#
# Diferença estrutural vs. residencial:
# - A URA de auto transfere cedo para atendente e coleta LOCAL (texto livre) →
#   o grosso é conduzido pelo cérebro adaptativo guardado (human_phase), que já
#   existe. O playbook fixa só os menus estáveis + o FREIO de finalização.
# - `opening_template`: resumo estruturado do pedido (como a operadora real
#   colava ao cair no atendente humano da seguradora).
# - `finalize_anchors`: FREIO — quando a URA vai CONFIRMAR/ABRIR o serviço de
#   fato, o motor pausa (needs_human) em vez de confirmar sozinho. Conservador
#   de propósito: frear cedo é seguro; frear tarde despacharia um prestador.
# ===========================================================================

# Subserviços auto e a intenção (usada pelo cérebro p/ escolher a opção do menu).
_AUTO_SUBSERVICE_LABELS = {
    "guincho": "guincho (reboque)",
    "bateria": "recarga de bateria / pane elétrica",
    "pneu": "troca de pneu (borracheiro)",
    "chaveiro": "chaveiro para o veículo",
}

# Slots mínimos por subserviço auto. placa/veículo vêm da InfoCap (server-side).
_AUTO_SLOTS_COMMON = ["titular_cpf", "veiculo_placa", "local_atual", "problema_descricao", "quando", "telefone_contato"]
_AUTO_SUBSERVICES = {
    "guincho": {"required_slots": _AUTO_SLOTS_COMMON + ["local_destino"]},
    "bateria": {"required_slots": _AUTO_SLOTS_COMMON},
    "pneu": {"required_slots": _AUTO_SLOTS_COMMON},
    "chaveiro": {"required_slots": _AUTO_SLOTS_COMMON},
}

# Resumo estruturado do pedido (aberto ao cair no atendente humano da seguradora).
_AUTO_OPENING_TEMPLATE = (
    "Ola, aqui e a corretora. Preciso de {subservice_label} para o veiculo do nosso segurado.\n"
    "Placa: {veiculo_placa}\n"
    "Veiculo: {veiculo_descricao}\n"
    "Titular: {titular_nome} (CPF/CNPJ {titular_cpf})\n"
    "Local do veiculo: {local_atual}\n"
    "Destino: {local_destino}\n"
    "O que houve: {problema_descricao}\n"
    "Quando: {quando}\n"
    "Contato no local: {pessoa_no_local} - {telefone_contato}"
)

_AUTO_HUMAN_PHASE_GUIDANCE = (
    "Voce conduz, EM NOME DA CORRETORA, um acionamento de assistencia AUTO no WhatsApp da seguradora. "
    "Pode ser a URA (menu numerado ou botoes) ou um atendente humano. Responda menus escolhendo a opcao "
    "coerente com o subservico/dados do caso; responda pedidos de dado com o valor exato do caso "
    "(placa, CPF, endereco, telefone). Endereco/local: use o que o cliente informou; nao invente. "
    "Se a seguradora for CONFIRMAR/ABRIR o servico (agendar, 'posso continuar', 'confirmar'), NAO confirme: "
    "isso e o passo final e exige aprovacao da corretora. Use SOMENTE dados do caso, nunca invente numeros/"
    "protocolos/prazos. Se realmente nao der pra deduzir, responda exatamente: NAO_SEI."
)

# Captura comum de protocolo/OS + link de acompanhamento (auto).
_AUTO_CAPTURE_ANCHORS = {
    "protocol": r"(?:protocolo(?:\s+de\s+atendimento)?|n[úu]mero\s+da\s+(?:ordem|os|solicita[çc][ãa]o)|o\.?s\.?)\s*(?:de\s+atendimento)?\s*:?\s*(\d{5,12})",
    "schedule": r"agendad?[ao]?\s+para\s+(?:o\s+dia\s+)?(\d{1,2}/\d{1,2}/\d{2,4})(?:\s*(?:[àa]s|,)?\s*(\d{1,2}[:h]\d{0,2}))?",
    "tracking_link": r"(https?://\S+)",
}

# Instruções fixas ao cliente para guincho/serviço no local.
_AUTO_CLIENT_INSTRUCTIONS_GUINCHO = [
    "Aguarde em local seguro, com as chaves e o documento do veículo.",
    "É preciso alguém maior de 18 anos no local para acompanhar o guincho.",
    "Você vai receber um SMS/link com a previsão de chegada do prestador.",
]
_AUTO_CLIENT_INSTRUCTIONS_LOCAL = [
    "Aguarde em local seguro próximo ao veículo.",
    "É preciso alguém maior de 18 anos no local para acompanhar o serviço.",
]

_AUTO_HANDOFF_TRIGGERS = [
    r"sinistro", r"colis[ãa]o", r"acidente", r"n[ãa]o localizamos", r"n[ãa]o encontrei .* ap[óo]lice",
    r"ap[óo]lice .* (?:vencid|cancelad|inativ)", r"sem cobertura", r"n[ãa]o (?:tem|possui) cobertura",
]


def _auto_playbook(insurer_key: str, contact_ref: str, ura_steps, finalize_anchors, *, version: int = 1) -> Dict[str, Any]:
    """Fábrica de playbook auto: mesma espinha, URA/freio por seguradora."""
    return {
        "playbook_id": f"{insurer_key}-auto-whatsapp",
        "version": version,
        "insurer_key": insurer_key,
        "line_kind": "auto",
        "channel": "whatsapp",
        "insurer_contact_ref": contact_ref,
        "description": f"Assistência 24h AUTO {insurer_key} via WhatsApp (guincho/bateria/pneu/chaveiro).",
        "subservices": {k: dict(v) for k, v in _AUTO_SUBSERVICES.items()},
        "opening_template": _AUTO_OPENING_TEMPLATE,
        "subservice_labels": dict(_AUTO_SUBSERVICE_LABELS),
        "ura_steps": ura_steps,
        "finalize_anchors": finalize_anchors,
        "human_phase_guidance": _AUTO_HUMAN_PHASE_GUIDANCE,
        "capture_anchors": dict(_AUTO_CAPTURE_ANCHORS),
        "client_instructions": list(_AUTO_CLIENT_INSTRUCTIONS_GUINCHO),
        "handoff_triggers": list(_AUTO_HANDOFF_TRIGGERS),
        "unknown_step_policy": "adaptive_then_handoff",
    }


# --- Allianz auto (número 1140901444 já configurado p/ residencial; menu Auto) --
ALLIANZ_AUTO_WHATSAPP_V1 = _auto_playbook(
    "allianz", "allianz_assistencia_24h",
    ura_steps=[
        {"step": "menu_tipo_seguro", "anchor": r"assist[êe]ncia 24h para qual seguro", "reply": "1",
         "notes": "1-Auto/Moto/Caminhão 2-Residência 3-Vida 4-Viagem 5-Outros → Auto"},
        {"step": "pedir_cpf", "anchor": r"digite o \*?cpf\*? ou \*?cnpj\*? do\(a\)? titular", "reply": "{titular_cpf}",
         "requires": ["titular_cpf"]},
        {"step": "menu_servico_auto", "anchor": r"o que voc[êe] precisa\??\s*\|?\s*\*?1", "reply": "{servico_opcao}",
         "requires": ["servico_opcao"],
         "notes": "1-pane elétrica/bateria 3-guincho pane mecânica 4-guincho sinistro 6-pneu 7-chaveiro"},
        {"step": "tipo_veiculo", "anchor": r"seu ve[íi]culo [ée]:\s*\|?\s*\*?1\s*-\s*automotor", "reply": "1",
         "notes": "1-automotor(combustão/híbrido) 2-elétrico. Default 1; caso elétrico, slot veiculo_eletrico=2"},
    ],
    finalize_anchors=[
        r"dados a seguir est[ãa]o corretos", r"posso confirmar", r"deseja confirmar",
        r"confirm\w* (?:o|a) (?:agendamento|abertura|solicita)",
    ],
)
ALLIANZ_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    "guincho": "3", "bateria": "1", "pneu": "6", "chaveiro": "7",
}

# --- Porto (URA numerada, muito forte no acervo) --------------------------------
PORTO_AUTO_WHATSAPP_V1 = _auto_playbook(
    "porto", "porto_assistencia_24h",
    ura_steps=[
        {"step": "pedir_cpf", "anchor": r"informe o \*?cpf ou cnpj\*? do\(a\)? titular", "reply": "{titular_cpf}",
         "requires": ["titular_cpf"]},
        {"step": "menu_seguro_auto", "anchor": r"localizei o seu \*?seguro auto", "reply": "1",
         "notes": "1-Atendimento para veículo"},
        {"step": "menu_atendimento", "anchor": r"de que atendimento voc[êe] precisa", "reply": "1",
         "notes": "1-Novo atendimento/serviço"},
        {"step": "menu_servico", "anchor": r"o que voc[êe] precisa\?.*guincho", "reply": "{servico_texto}",
         "requires": ["servico_texto"],
         "notes": "responder o RÓTULO do serviço (Guincho / Bateria / Troca de pneu / Chaveiro)"},
        {"step": "ponto_referencia", "anchor": r"ponto de refer[êe]ncia", "reply": "{ponto_referencia}",
         "notes": "referência do local; se não houver, 'não tem'"},
    ],
    finalize_anchors=[
        r"posso continuar o agendamento", r"ser[áa] confirmad[ao] somente ap[óo]s",
        r"qual per[íi]odo voc[êe] prefere", r"tenho urg[êe]ncia.*agendar", r"finaliza[çc][ãa]o do agendamento",
        r"confirmar o agendamento",
    ],
)
PORTO_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    "guincho": "Guincho", "bateria": "Bateria", "pneu": "Troca de pneu", "chaveiro": "Chaveiro para o veículo",
}
PORTO_AUTO_WHATSAPP_V1["ura_steps"].insert(4, {
    "step": "menu_quando", "anchor": r"para quando voc[êe] precisa que esse servi[çc]o", "reply": "1",
    "notes": "1-Tenho urgência 2-Agendar. Default urgência (agora); agendamento é passo de finalização.",
})

# --- HDI (URA por BOTÕES: responder o RÓTULO; transfere cedo p/ analista) --------
HDI_AUTO_WHATSAPP_V1 = _auto_playbook(
    "hdi", "hdi_assistencia_24h",
    ura_steps=[
        {"step": "menu_auto_ou_resid", "anchor": r"assist[êe]ncia para seu \*?autom[óo]vel\*? ou \*?resid[êe]ncia",
         "reply": "Automóvel"},
        {"step": "informar_nome", "anchor": r"informe o seu nome ou como gostaria de ser chamado",
         "reply": "{titular_nome}", "requires": ["titular_nome"]},
        {"step": "informar_placa", "anchor": r"qual a placa do ve[íi]culo", "reply": "{veiculo_placa}",
         "requires": ["veiculo_placa"]},
        {"step": "roda_travada", "anchor": r"alguma roda travada", "reply": "{roda_travada}",
         "notes": "sim/não conforme o caso; default 'não'"},
    ],
    finalize_anchors=[
        r"est[áa] correto\s*\?", r"agendamento para .* realizado", r"deseja confirmar",
        r"confirma\s+(?:a\s+)?(?:abertura|solicita|o agendamento)",
    ],
)
HDI_AUTO_WHATSAPP_V1["subservice_menu_map"] = {  # HDI decide o serviço na fase humana
    "guincho": "Guincho", "bateria": "Recarga de bateria", "pneu": "Troca de pneu", "chaveiro": "Chaveiro",
}

# --- Yelum (ex-Liberty) e Tokio: evidência mais fina → playbook enxuto, adaptativo
YELUM_AUTO_WHATSAPP_V1 = _auto_playbook(
    "yelum", "yelum_assistencia_24h",
    ura_steps=[
        {"step": "pedir_cpf", "anchor": r"cpf\s*(?:ou\s*cnpj)?\s*do\(a\)? titular", "reply": "{titular_cpf}",
         "requires": ["titular_cpf"]},
    ],
    finalize_anchors=[r"posso confirmar", r"deseja confirmar", r"confirmar? (?:o|a) (?:agendamento|abertura)"],
)
YELUM_AUTO_WHATSAPP_V1["subservice_menu_map"] = {"guincho": "Guincho", "bateria": "Bateria", "pneu": "Troca de pneu", "chaveiro": "Chaveiro"}

TOKIO_AUTO_WHATSAPP_V1 = _auto_playbook(
    "tokio", "tokio_assistencia_24h",
    ura_steps=[
        {"step": "perfil", "anchor": r"voc[êe] [ée] segurado, prestador ou corretor", "reply": "Corretor",
         "notes": "responder Corretor (botão)"},
    ],
    finalize_anchors=[r"posso confirmar", r"deseja confirmar", r"confirmar? (?:o|a) (?:agendamento|abertura)"],
)
TOKIO_AUTO_WHATSAPP_V1["subservice_menu_map"] = {"guincho": "Guincho", "bateria": "Bateria", "pneu": "Troca de pneu", "chaveiro": "Chaveiro"}


_PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    f"{p['playbook_id']}@v{p['version']}": p
    for p in (
        ALLIANZ_RESIDENCIAL_WHATSAPP_V1,
        ALLIANZ_AUTO_WHATSAPP_V1,
        PORTO_AUTO_WHATSAPP_V1,
        HDI_AUTO_WHATSAPP_V1,
        YELUM_AUTO_WHATSAPP_V1,
        TOKIO_AUTO_WHATSAPP_V1,
    )
}


def get_playbook(playbook_ref: str) -> Optional[Dict[str, Any]]:
    return _PLAYBOOKS.get(str(playbook_ref or "").strip())


def list_playbooks() -> List[str]:
    return sorted(_PLAYBOOKS.keys())


# ---------------------------------------------------------------------------
# Seleção de playbook e contato por seguradora (SPEC-031)
# ---------------------------------------------------------------------------

# Sinônimos de seguradora → chave canônica (a InfoCap pode devolver variações).
_INSURER_ALIASES = {
    "allianz": "allianz", "allianz seguros": "allianz",
    "porto": "porto", "porto seguro": "porto", "azul": "porto",  # Azul é do grupo Porto
    "hdi": "hdi", "hdi seguros": "hdi",
    "yelum": "yelum", "liberty": "yelum", "liberty seguros": "yelum", "libe": "yelum",
    "tokio": "tokio", "tokio marine": "tokio", "tokyo": "tokio",
}


def normalize_insurer_key(insurer: str) -> str:
    """Normaliza nome/sigla de seguradora para a chave canônica de playbook."""
    raw = _norm(insurer)
    if raw in _INSURER_ALIASES:
        return _INSURER_ALIASES[raw]
    for alias, key in _INSURER_ALIASES.items():
        if alias in raw:
            return key
    return raw.split()[0] if raw else ""


def resolve_playbook_ref(insurer: str, line_kind: str = "auto", channel: str = "whatsapp") -> Optional[str]:
    """Resolve o playbook_ref pela seguradora + linha. None se não houver."""
    key = normalize_insurer_key(insurer)
    line = str(line_kind or "auto").strip().lower()
    line = "residencial" if line in ("residencial", "residencia", "resid", "casa", "home") else line
    for ref, pb in _PLAYBOOKS.items():
        if (pb.get("insurer_key") == key and pb.get("line_kind") == line
                and pb.get("channel") == str(channel or "whatsapp").strip().lower()):
            return ref
    return None


def insurer_contact_env_var(insurer: str, line_kind: str = "auto") -> str:
    """Nome do env com o contato (WhatsApp) da assistência da seguradora.
    Ex.: INSURER_CONTACT_PORTO_ASSISTENCIA. Allianz mantém o env legado."""
    key = normalize_insurer_key(insurer).upper() or "DESCONHECIDA"
    return f"INSURER_CONTACT_{key}_ASSISTENCIA"


def resolve_insurer_contact(insurer: str, env: Optional[Dict[str, str]] = None, line_kind: str = "auto") -> str:
    """Telefone da assistência da seguradora (só dígitos). Nunca hard-coded no
    playbook: vem de env/config da plataforma. Allianz tem fallback legado."""
    import os as _os

    env = env if env is not None else _os.environ
    candidates = [insurer_contact_env_var(insurer, line_kind)]
    if normalize_insurer_key(insurer) == "allianz":
        candidates.append("INSURER_CONTACT_ALLIANZ_ASSISTENCIA_24H")
    for var in candidates:
        val = "".join(ch for ch in str(env.get(var) or "") if ch.isdigit())
        if val:
            return val
    return ""


def auto_subservice_menu_value(playbook: Dict[str, Any], subservice: str) -> str:
    """Opção/rótulo do menu da seguradora para o subserviço auto (guincho→'3' ou 'Guincho')."""
    return str((playbook.get("subservice_menu_map") or {}).get(str(subservice or "").strip().lower()) or "")


def render_opening_message(playbook: Dict[str, Any], subservice: str, slots: Dict[str, Any]) -> str:
    """Resumo estruturado do pedido para abrir a fase humana da seguradora (auto)."""
    template = playbook.get("opening_template")
    if not template:
        return "Olá"
    labels = playbook.get("subservice_labels") or {}
    data = {k: str(v) for k, v in (slots or {}).items()}
    data.setdefault("subservice_label", labels.get(str(subservice or "").lower(), "assistência 24h"))
    # Campos opcionais nunca quebram o template.
    for opt in ("veiculo_descricao", "titular_nome", "local_destino", "pessoa_no_local", "quando"):
        data.setdefault(opt, "-")
    try:
        return template.format_map({**{k: "-" for k in _optional_keys()}, **data})
    except Exception:  # noqa: BLE001
        return "Olá, preciso de assistência 24h para o veículo do nosso segurado."


def _optional_keys() -> List[str]:
    return [
        "subservice_label", "veiculo_placa", "veiculo_descricao", "titular_nome", "titular_cpf",
        "local_atual", "local_destino", "problema_descricao", "quando", "pessoa_no_local", "telefone_contato",
    ]


def detect_finalize_anchor(playbook: Dict[str, Any], insurer_message: str) -> Optional[str]:
    """FREIO: retorna o padrão casado quando a seguradora vai CONFIRMAR/ABRIR o
    serviço. O motor pausa (needs_human) em vez de confirmar sozinho — o passo
    final (que despacha o prestador) exige aprovação da corretora."""
    text = _norm(insurer_message)
    for pattern in playbook.get("finalize_anchors") or []:
        if re.search(pattern, text, re.IGNORECASE):
            return pattern
    return None


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
    sched = anchors.get("schedule")
    if sched:
        m = re.search(sched, text, re.IGNORECASE)
        if m:
            groups = m.groups()
            if len(groups) >= 3:
                out["schedule"] = {"day": m.group(1), "from": m.group(2), "to": m.group(3)}
            else:  # âncora de auto: dia (+ hora opcional)
                out["schedule"] = {"day": m.group(1), "at": (m.group(2) if len(groups) >= 2 else None)}
    link = anchors.get("tracking_link")
    if link:
        m = re.search(link, insurer_message, re.IGNORECASE)  # texto ORIGINAL (URL preserva caixa)
        if m:
            out["tracking_link"] = m.group(1)
    return out


def missing_slots_for_subservice(playbook: Dict[str, Any], subservice: str, slots: Dict[str, Any]) -> List[str]:
    sub = (playbook.get("subservices") or {}).get(str(subservice or "").strip().lower())
    if not sub:
        return ["subservico_invalido"]
    return [f for f in sub.get("required_slots") or [] if not str(slots.get(f) or "").strip()]
