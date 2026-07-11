"""Playbooks de corredor (SPEC-017 P4 / S17-4) — corredores como DADOS versionados.

Um playbook descreve como acionar a seguradora em um canal:
- fase URA: âncoras de menu → respostas determinísticas (sem LLM);
- dados mínimos por subserviço (slots);
- âncoras de captura (protocolo, senha, agendamento, ETA);
- gatilhos de handoff (fail-safe: passo desconhecido NUNCA responde às cegas).

FREIO (decisão do founder 2026-07-11): `finalize_anchors` detecta o passo em que a
seguradora vai CONFIRMAR/ABRIR o serviço de verdade. Ele existe SÓ para o modo
TESTE (a IA executa o fluxo inteiro e CANCELA antes de abrir — nada de acionamento
de mentira). Em modo LIVE (corredor validado) o freio não trava: o passo de
confirmação é respondido pelos próprios ura_steps e o fluxo completa ponta a ponta
sem humano. `finalize_abort_reply` = como cancelar educadamente no modo teste
(vazio = silêncio; a URA encerra por inatividade). Humano só em sinistro,
sem-corredor ou travamento real.

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
            "step": "menu_solicitar_para",
            "anchor": r"solicitar servi[çc]os de assist[êe]ncia para:",
            "reply": "1",
            "notes": "URA 2026: 1-Residência 2-Condomínio 3-Empresa",
        },
        {
            "step": "menu_qual_seguro",
            "anchor": r"qual o seguro que deseja utilizar",
            "reply": "1",
            "notes": "1-Residência/Condomínio/Empresa 2-Auto com serviços residenciais",
        },
        {
            # A URA lembra o CPF do ÚLTIMO atendimento (o WhatsApp é da corretora,
            # atende N clientes) — SEMPRE re-identificar para nunca acionar na
            # apólice do cliente anterior.
            "step": "cpf_anterior",
            "anchor": r"em nossa [úu]ltima conversa,? utilizamos o cpf",
            "reply": "2",
            "notes": "1-Sim (continuar com o CPF anterior) 2-Não, inserir outro CPF/CNPJ",
        },
        {
            "step": "atendimento_recente",
            "anchor": r"atendimento realizado recentemente",
            "reply": "2",
            "notes": "1-Sim, mesmo atendimento 2-Não, abrir novo serviço",
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
        {
            "step": "complemento_referencia",
            "anchor": r"informe o complemento do endere[çc]o",
            "reply": "{ponto_referencia}",
            "notes": "URA 2026 pede complemento/referência (texto livre); 'não' aceito",
        },
        {
            # Confirmação FINAL (RESUMO → 'Podemos confirmar o atendimento?').
            # Só é alcançada em modo LIVE — em modo teste o freio cancela antes.
            "step": "confirmar_atendimento",
            "anchor": r"podemos confirmar o atendimento",
            "reply": "1",
            "notes": "1-Sim 2-Não, reiniciar 3/0-Sair",
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
    # FREIO (modo teste): a URA residencial 2026 completa TUDO sozinha até o
    # protocolo — sem estas âncoras a LLM confirmaria um serviço real no teste.
    "finalize_anchors": [
        r"podemos confirmar o atendimento", r"posso confirmar", r"deseja confirmar",
    ],
    "finalize_abort_reply": "SAIR",  # a URA aceita SAIR a qualquer momento
    # Âncoras de captura no retorno da seguradora (formatos 2024 E 2026).
    "capture_anchors": {
        "protocol": r"(?:n[úu]mero (?:da assist[êe]ncia|de protocolo) [ée]|protocolo)\s*:?\s*\*?(\d{5,12})",
        "password": r"senha (?:de acesso|ser[áa]).*?(\d{4})",
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
# O grupo aceita dígitos com hífen: a Azul emite "protocolo ... 1-104106503215".
# HDI emite "a solicitação de GUINCHO para a assistência *9257546* foi aberta".
# Zurich agenda com "prevista para o dia X às Y"; Porto/Allianz dão ETA em minutos.
_AUTO_CAPTURE_ANCHORS = {
    "protocol": r"(?:protocolo(?:\s+de\s+atendimento)?|n[úu]mero\s+da\s+(?:ordem|os|solicita[çc][ãa]o)|para a assist[êe]ncia|sobre sua assist[êe]ncia|o\.?s\.?)[^\d]{0,24}(\d[\d-]{4,18}\d)",
    "schedule": r"(?:agendad?[ao]?|prevista?)\s+para\s+(?:o\s+dia\s+)?\*?(\d{1,2}/\d{1,2}/\d{2,4})\*?(?:\s*(?:[àa]s|,)?\s*\*?(\d{1,2}[:h]\d{0,2}))?",
    "eta": r"(?:previs[ãa]o(?:\s+de\s+chegada)?\s*:?|previsto para ser realizado[^\n]{0,20}?em|em at[ée])\s*(?:at[ée]\s+)?(\d{1,3})\s*min",
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


# --- Allianz auto (fluxo REAL 05/03/2026 minerado por completo) --------------------
_ALLIANZ_FAMILY_AUTO_STEPS = [
    # Família Allianz/Alfa (mesmo fornecedor de bot): URA numerada.
    {"step": "cpf_anterior", "anchor": r"em nossa [úu]ltima conversa,? utilizamos o cpf", "reply": "2",
     "notes": "URA lembra o CPF do último atendimento — SEMPRE re-identificar (2=inserir outro)"},
    {"step": "atendimento_recente", "anchor": r"atendimento realizado recentemente", "reply": "2",
     "notes": "1-mesmo atendimento 2-abrir novo serviço"},
    {"step": "pedir_cpf", "anchor": r"digite o \*?cpf\*? ou \*?cnpj\*? do\(a\)? titular", "reply": "{titular_cpf}",
     "requires": ["titular_cpf"]},
    {"step": "pedir_placa", "anchor": r"preciso da \*?placa\*? do ve[íi]culo", "reply": "{veiculo_placa}",
     "requires": ["veiculo_placa"]},
    {"step": "confirmar_veiculo", "anchor": r"confirme o ve[íi]culo para atendimento", "reply": "1",
     "notes": "1 = veículo achado pela placa informada; 2-Outro veículo 0-Sair"},
    {"step": "confirmar_telefone", "anchor": r"deseja adicionar outro n[úu]mero", "reply": "{telefone_adicionar_opcao}",
     "requires": ["telefone_adicionar_opcao"], "notes": "1=Sim (informa telefone_contato) 2=Não (usa o registrado)"},
    {"step": "informar_telefone", "anchor": r"informe \*?o n[úu]mero de celular completo\*? com ddd",
     "reply": "{telefone_contato}", "requires": ["telefone_contato"]},
    {"step": "telefone_anotado", "anchor": r"anotei seu n[úu]mero", "reply": "1"},
    {"step": "tipo_veiculo", "anchor": r"seu ve[íi]culo [ée]:\s*\|?\s*\*?1\s*-\s*automotor", "reply": "1",
     "notes": "1-automotor(combustão/híbrido) 2-elétrico. Default 1; caso elétrico, adaptativo"},
    {"step": "menu_servico_auto", "anchor": r"o que voc[êe] precisa\??\s*\|?\s*\*?1", "reply": "{servico_opcao}",
     "requires": ["servico_opcao"],
     "notes": "1-pane elétrica/bateria 3-guincho pane mecânica 4-guincho sinistro 6-pneu 7-chaveiro"},
    {"step": "quando", "anchor": r"para quando precisa do \*?(?:reboque|guincho|servi[çc]o|profissional)", "reply": "1",
     "notes": "1-Agora 2-Agendar; urgência é o default do corredor"},
    {"step": "oferta_mecanico", "anchor": r"continuar com a solicita[çc][ãa]o do guincho", "reply": "2",
     "notes": "URA oferece mecânico no lugar do guincho — o serviço é o que o CLIENTE pediu (2=continuar guincho)"},
    {"step": "rodas_travadas", "anchor": r"rodas? travadas?", "reply": "2",
     "notes": "default Não (2); se o caso indicar roda travada, o adaptativo assume"},
    {"step": "acesso_reboque", "anchor": r"local que o reboque consegue acessar", "reply": "1",
     "notes": "1-Sim; se o caso indicar acesso difícil, o adaptativo assume"},
    {"step": "pcd_criancas", "anchor": r"pessoa com defici[êe]ncia, crian[çc]a, gestante ou idoso", "reply": "2",
     "notes": "default Não; se houver no caso, o adaptativo assume"},
    {"step": "referencia_local", "anchor": r"informe uma refer[êe]ncia do local", "reply": "{ponto_referencia}",
     "notes": "texto livre; default 'não tem'"},
    {"step": "confirmar_atendimento", "anchor": r"podemos confirmar o atendimento", "reply": "1",
     "notes": "confirmação FINAL (RESUMO). Só alcançada em modo LIVE — no teste o freio cancela antes."},
]
_ALLIANZ_FAMILY_FINALIZE = [
    # Texto REAL 2026: RESUMO → "Podemos confirmar o atendimento?"
    r"podemos confirmar o atendimento",
    r"dados a seguir est[ãa]o corretos", r"posso confirmar", r"deseja confirmar",
    r"confirm\w* (?:o|a) (?:agendamento|abertura|solicita)",
]

ALLIANZ_AUTO_WHATSAPP_V1 = _auto_playbook(
    "allianz", "allianz_assistencia_24h",
    ura_steps=[
        {"step": "menu_tipo_seguro", "anchor": r"assist[êe]ncia 24h para qual seguro", "reply": "1",
         "notes": "1-Auto/Moto/Caminhão 2-Residência 3-Vida 4-Viagem 5-Outros → Auto"},
    ] + [dict(s) for s in _ALLIANZ_FAMILY_AUTO_STEPS],
    finalize_anchors=list(_ALLIANZ_FAMILY_FINALIZE),
)
ALLIANZ_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    "guincho": "3", "bateria": "1", "pneu": "6", "chaveiro": "7",
}
ALLIANZ_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "SAIR"  # URA aceita SAIR a qualquer momento

# --- Porto (fluxo REAL 25/03/2026: listas/botões — responder o RÓTULO; números
# são REJEITADOS: "Não entendi sua resposta. Selecione o botão abaixo") ----------
PORTO_AUTO_WHATSAPP_V1 = _auto_playbook(
    "porto", "porto_assistencia_24h",
    ura_steps=[
        # A URA lembra o último cliente e abre saudando ele pelo nome. 1ª vez que o
        # menu raiz aparecer: re-identificar ("Informar outro CPF/CNPJ"); quando ele
        # reaparecer (já com NOSSO cliente), seguir para "Seguro Auto" (reply_repeat).
        {"step": "menu_raiz", "anchor": r"escolha a op[çc][ãa]o desejada",
         "reply": "Informar outro CPF/CNPJ", "reply_repeat": "Seguro Auto",
         "notes": "menu raiz por rótulo; nunca acionar no CPF lembrado do cliente anterior"},
        {"step": "pedir_cpf", "anchor": r"(?:informe|digite) o (?:seu )?\*?cpf ou cnpj\*?", "reply": "{titular_cpf}",
         "requires": ["titular_cpf"], "notes": "2026: 'digite o seu *CPF ou CNPJ*'"},
        {"step": "menu_como_ajudar", "anchor": r"como eu posso te ajudar\?.*servi[çc]os para ve[íi]culo",
         "reply": "Serviços para veículo", "notes": "lista: Serviços para veículo / residência / Sinistro / ..."},
        {"step": "confirmar_veiculo", "anchor": r"quer atendimento para o ve[íi]culo", "reply": "Sim",
         "notes": "URA mostra o veículo da apólice (botões Sim/Não/Voltar)"},
        {"step": "menu_seguro_auto", "anchor": r"localizei o seu \*?seguro auto", "reply": "1",
         "notes": "variante antiga numerada — manter"},
        {"step": "menu_atendimento", "anchor": r"de que atendimento voc[êe] precisa", "reply": "Novo serviço",
         "notes": "lista: Novo serviço / Acompanhar / Cancelar / ..."},
        {"step": "menu_servico", "anchor": r"o que voc[êe] precisa\?.*guincho", "reply": "{servico_texto}",
         "requires": ["servico_texto"],
         "notes": "responder o RÓTULO completo (Guincho (reboque) / Bateria / Chaveiro para veículo / Técnico)"},
        {"step": "necessidade_guincho", "anchor": r"op[çc][ãa]o que descreve melhor a sua necessidade",
         "reply": "Remoção de veículo",
         "notes": "Remoção de veículo (pane) · 'Envolvimento em acidente' = sinistro → handoff antes de chegar aqui"},
        {"step": "menu_quando", "anchor": r"para quando voc[êe] precisa que esse servi[çc]o", "reply": "Tenho urgência",
         "notes": "botões: Tenho urgência / Agendar. A frase 'confirmada somente após a finalização' é COLETA."},
        {"step": "complemento", "anchor": r"digite ent[ãa]o um \*?complemento", "reply": "não tem",
         "notes": "complemento do endereço; sem complemento = 'não tem'"},
        {"step": "ponto_referencia", "anchor": r"ponto de refer[êe]ncia", "reply": "{ponto_referencia}",
         "notes": "referência do local; se não houver, 'não tem'"},
        {"step": "destino_sabe", "anchor": r"onde o guincho deve levar seu ve[íi]culo", "reply": "Sim",
         "notes": "guincho: já sabemos o destino (local_destino do caso)"},
        {"step": "no_local", "anchor": r"[ée] voc[êe] que est[áa] no local para (?:acompanhar|aguardar)", "reply": "Sim",
         "notes": "quem está no local acompanha; dados de contato ajustáveis no menu de revisão"},
        {"step": "pode_ligar", "anchor": r"posso te ligar no n[úu]mero abaixo", "reply": "Sim",
         "notes": "autoriza contato telefônico do prestador"},
        {"step": "aguarde", "anchor": r"aguarde um momento|que bom ter voc[êe] de volta|aguarde enquanto solicito",
         "reply": "", "noop": True, "notes": "mensagens de espera/boas-vindas — não responder"},
        {"step": "confirmar_solicitacao", "anchor": r"como voc[êe] quer prosseguir|posso confirmar sua solicita[çc][ãa]o",
         "reply": "Confirmar solicitação",
         "notes": "confirmação FINAL. Só alcançada em modo LIVE — no teste o freio cancela antes."},
    ],
    finalize_anchors=[
        # Texto REAL 2026: "Como você quer prosseguir? Confirmar solicitação ..."
        r"como voc[êe] quer prosseguir",
        r"posso confirmar sua solicita[çc][ãa]o",
        # URA antiga (manter por segurança):
        r"posso continuar o agendamento",
        r"gostaria de alterar alguma informa[çc][ãa]o",
        r"confirmar o agendamento",
    ],
)
PORTO_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    "guincho": "Guincho (reboque)", "bateria": "Bateria", "pneu": "Troca de pneu", "chaveiro": "Chaveiro para veículo",
}
PORTO_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "Sair e não agendar"

# --- HDI (MESMO bot white-label da Yelum — fluxo REAL 28/01/2026; botões por
# rótulo, timeout 12min, encerra após respostas não-identificadas) ----------------
HDI_AUTO_WHATSAPP_V1 = _auto_playbook(
    "hdi", "hdi_assistencia_24h",
    ura_steps=[
        {"step": "menu_auto_ou_resid",
         "anchor": r"assist[êe]ncia para seu \*?autom[óo]vel\*? ou \*?resid[êe]ncia|para seu \*?autom[óo]vel\*? ou \*?resid[êe]ncia",
         "reply": "🚗 Automóvel", "notes": "botões com emoji: '🚗 Automóvel' / '🏠 Residência'"},
        {"step": "identificacao_dado",
         "anchor": r"informe \*?apenas um dos dados|informe \*?um dos dados abaixo",
         "reply": "{titular_cpf}", "requires": ["titular_cpf"],
         "notes": "entrada 2026: CPF/CNPJ do segurado OU placa; CPF identifica frota/CNPJ também"},
        {"step": "informar_nome", "anchor": r"informe o seu nome ou como gostaria de ser chamado",
         "reply": "Atendimento", "notes": "nome de quem opera o canal (a corretora)"},
        {"step": "informar_placa", "anchor": r"qual a placa do ve[íi]culo", "reply": "{veiculo_placa}",
         "requires": ["veiculo_placa"]},
        {"step": "perfil", "anchor": r"em qual dessas op[çc][õo]es voc[êe] se enquadra", "reply": "Sou corretor(a)",
         "notes": "agimos em nome da corretora"},
        {"step": "pessoa_no_local", "anchor": r"[ée] a pessoa que est[áa] (?:no )?local para acompanhar", "reply": "Não"},
        {"step": "nome_pessoa_local", "anchor": r"qual [ée] o nome da pessoa que est[áa] no local",
         "reply": "{pessoa_no_local}", "requires": ["pessoa_no_local"]},
        {"step": "telefone_local", "anchor": r"n[úu]mero de (?:celular|telefone)\*? com ddd da pessoa que est[áa] no local",
         "reply": "{telefone_contato}", "requires": ["telefone_contato"]},
        {"step": "telefone_confirma", "anchor": r"o n[úu]mero de telefone \d+ est[áa] correto", "reply": "Sim"},
        {"step": "cor_menu", "anchor": r"informar a cor do ve[íi]culo de placa", "reply": "Outros"},
        {"step": "cor_texto", "anchor": r"qual a cor do ve[íi]culo de placa", "reply": "{veiculo_cor}",
         "notes": "campo livre; default 'não sei'"},
        {"step": "rodovia", "anchor": r"(?:o ve[íi]culo|saber se o ve[íi]culo) est[áa] em uma rodovia", "reply": "{rodovia}",
         "notes": "Sim/Não conforme local_atual; default Não"},
        {"step": "o_que_aconteceu", "anchor": r"pode me dizer o que aconteceu", "reply": "{servico_opcao}",
         "requires": ["servico_opcao"],
         "notes": "guincho→Pane ou Defeito · bateria→Recarga de bateria · pneu→Pneu Furado · chaveiro→Problema com a chave · colisão=SINISTRO (handoff antes)"},
        {"step": "pane_detalhe", "anchor": r"selecione a op[çc][ãa]o que condiz com a pane", "reply": "Problemas no motor",
         "notes": "guincho por pane: leva direto ao Guincho"},
        {"step": "endereco_como", "anchor": r"op[çc][õo]es para informar o endere[çc]o onde o ve[íi]culo est[áa]",
         "reply": "Digitar endereço", "notes": "Digitar endereço / Compartilhar / CEP / Não sei"},
        {"step": "aguarde_fila",
         "anchor": r"ainda n[ãa]o identificamos a sua resposta|voc[êe] est[áa] na fila|alto volume de atendimentos|aguarde (?:um momento|s[óo] mais)|te transfiro para um|dicas (?:r[áa]pidas|sobre como funciona)|seja bem-?vindo ao atendimento",
         "reply": "", "noop": True, "notes": "fila/aviso/boas-vindas — NÃO responder"},
        {"step": "deseja_continuar", "anchor": r"deseja continuar (?:este|com o) atendimento", "reply": "Sim"},
        {"step": "confirmar_endereco", "anchor": r"voc[êe] confirma o endere[çc]o", "reply": "Sim",
         "notes": "último passo antes da URA abrir sozinha. Só alcançado em modo LIVE — no teste o freio cancela antes."},
    ],
    finalize_anchors=[
        # A URA abre SOZINHA depois do endereço confirmado → o freio de teste fica
        # na confirmação do endereço. ('está correto?' genérico era FALSO freio:
        # disparava na confirmação de telefone no meio da coleta.)
        r"voc[êe] confirma o endere[çc]o",
        r"agendamento para .* realizado", r"deseja confirmar",
        r"confirma\s+(?:a\s+)?(?:abertura|solicita|o agendamento)",
    ],
)
HDI_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    "guincho": "Pane ou Defeito", "bateria": "Recarga de bateria",
    "pneu": "Pneu Furado", "chaveiro": "Problema com a chave",
}
HDI_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "Sair"  # 'Digite Sair para encerrar'

# --- Yelum (ex-Liberty): v2 minerado da conversa REAL completa da AutoFleet
# (2023→2026, dezenas de acionamentos). A URA identifica por PLACA/CPF, deriva
# o serviço do "o que aconteceu" e ABRE automaticamente após os últimos dados —
# por isso os freios ficam ANTES do trecho final.
YELUM_AUTO_WHATSAPP_V1 = _auto_playbook(
    "yelum", "yelum_assistencia_24h",
    ura_steps=[
        {"step": "menu_auto_ou_resid",
         "anchor": r"assist[êe]ncia para (?:o )?(?:seu|sua) \*?(?:autom[óo]vel|casa)\*? ou \*?resid[êe]ncia\*?|sua \*?casa\*? ou \*?carro\*?",
         "reply": "Automóvel", "notes": "variante antiga usa botões Casa/Carro"},
        {"step": "identificacao_dado",
         "anchor": r"informe \*?apenas um dos dados|informe somente o \*?cpf ou cnpj\*? do t[íi]tular",
         "reply": "{titular_cpf}", "requires": ["titular_cpf"],
         "notes": "URA 2026 pede CPF/CNPJ OU placa logo de cara"},
        {"step": "continuar_com_placa", "anchor": r"identifiquei em seu cadastro a placa", "reply": "Automóvel",
         "notes": "após CPF, a URA acha a placa e pergunta veículo ou residencial"},
        {"step": "informar_nome", "anchor": r"informe o seu nome ou como gostaria de ser chamad", "reply": "Atendimento",
         "notes": "nome de quem opera o canal (a corretora)"},
        {"step": "informar_placa", "anchor": r"qual a placa do ve[íi]culo", "reply": "{veiculo_placa}",
         "requires": ["veiculo_placa"]},
        {"step": "perfil", "anchor": r"em qual dessas op[çc][õo]es voc[êe] se enquadra", "reply": "Sou corretor(a)",
         "notes": "agimos em nome da corretora"},
        {"step": "pessoa_no_local", "anchor": r"[ée] a pessoa que est[áa] (?:no )?local para acompanhar", "reply": "Não"},
        {"step": "nome_pessoa_local", "anchor": r"qual [ée] o nome da pessoa que est[áa] no local", "reply": "{pessoa_no_local}",
         "requires": ["pessoa_no_local"]},
        {"step": "telefone_local", "anchor": r"n[úu]mero de (?:celular|telefone)\*? com ddd da pessoa que est[áa] no local",
         "reply": "{telefone_contato}", "requires": ["telefone_contato"]},
        {"step": "telefone_confirma", "anchor": r"o n[úu]mero de telefone \d+ est[áa] correto", "reply": "Sim"},
        {"step": "cor_menu", "anchor": r"informar a cor do ve[íi]culo de placa", "reply": "Outros"},
        {"step": "cor_texto", "anchor": r"qual a cor do ve[íi]culo de placa", "reply": "{veiculo_cor}",
         "notes": "campo livre; default 'não sei' (padrão da operadora real)"},
        {"step": "rodovia", "anchor": r"(?:o ve[íi]culo|saber se o ve[íi]culo) est[áa] em uma rodovia", "reply": "{rodovia}",
         "notes": "Sim/Não conforme local_atual; default Não"},
        {"step": "o_que_aconteceu", "anchor": r"pode me dizer o que aconteceu", "reply": "{servico_opcao}",
         "requires": ["servico_opcao"],
         "notes": "guincho→Pane ou Defeito · bateria→Recarga de bateria · pneu→Pneu Furado · chaveiro→Problema com a chave"},
        {"step": "pane_detalhe", "anchor": r"selecione a op[çc][ãa]o que condiz com a pane", "reply": "Problemas no motor",
         "notes": "guincho por pane: 'Problemas no motor' leva direto ao Guincho (fluxo real 02/07/2025)"},
        {"step": "situacao_risco", "anchor": r"situa[çc][õo]es de risco abaixo", "reply": "Nenhuma das anteriores",
         "notes": "se o caso indicar risco real, o cérebro adaptativo assume"},
        {"step": "ocupantes", "anchor": r"ocupantes tem alguma das particularidades|algu[ée]m da lista abaixo no local",
         "reply": "Nenhuma das anteriores"},
        {"step": "aguarde_fila",
         "anchor": r"ainda n[ãa]o identificamos a sua resposta|voc[êe] est[áa] na fila|alto volume de atendimentos|aguarde (?:um momento|s[óo] mais)|te transfiro para um|dicas (?:r[áa]pidas|sobre como funciona)|seja bem-?vindo ao atendimento",
         "reply": "", "noop": True, "notes": "fila/aviso/boas-vindas — NÃO responder"},
        {"step": "deseja_continuar", "anchor": r"deseja continuar (?:este|com o) atendimento", "reply": "Sim"},
    ],
    finalize_anchors=[
        # A Yelum ABRE sozinha após os últimos dados → frear ANTES do trecho final:
        r"solicitando o atendimento para agora ou prefere agendar",
        r"quer o atendimento para agora ou prefere agendar",
        r"para onde devemos levar o ve[íi]culo",
        r"podemos confirmar",
    ],
)
YELUM_AUTO_WHATSAPP_V1["version"] = 2
YELUM_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    "guincho": "Pane ou Defeito", "bateria": "Recarga de bateria",
    "pneu": "Pneu Furado", "chaveiro": "Problema com a chave",
}
YELUM_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "Sair"  # 'Digite Sair para encerrar'
# Passos do trecho FINAL (só alcançados em modo LIVE — no teste o freio cancela antes):
YELUM_AUTO_WHATSAPP_V1["ura_steps"].extend([
    {"step": "quando_agora", "anchor": r"atendimento para agora ou prefere agendar", "reply": "Agora",
     "notes": "urgência é o default do corredor"},
    {"step": "destino_como", "anchor": r"para onde devemos levar o ve[íi]culo", "reply": "Digitar endereço",
     "notes": "guincho: informar o destino do caso (adaptativo completa rua/número)"},
    {"step": "podemos_confirmar", "anchor": r"podemos confirmar", "reply": "Sim",
     "notes": "confirmação final (modo LIVE)"},
])

TOKIO_AUTO_WHATSAPP_V1 = _auto_playbook(
    "tokio", "tokio_assistencia_24h",
    ura_steps=[
        {"step": "perfil", "anchor": r"voc[êe] [ée] segurado, prestador ou corretor", "reply": "Corretor",
         "notes": "responder Corretor (botão)"},
    ],
    finalize_anchors=[r"posso confirmar", r"deseja confirmar", r"confirmar? (?:o|a) (?:agendamento|abertura)"],
)
TOKIO_AUTO_WHATSAPP_V1["subservice_menu_map"] = {"guincho": "Guincho", "bateria": "Bateria", "pneu": "Troca de pneu", "chaveiro": "Chaveiro"}

# --- ALFA (URA gêmea da Allianz — mesmo fornecedor; fluxo REAL 03/02/2026) --------
ALFA_AUTO_WHATSAPP_V1 = _auto_playbook(
    "alfa", "alfa_assistencia_24h",
    ura_steps=[
        {"step": "menu_tipo_seguro", "anchor": r"assist[êe]ncia 24h para qual seguro", "reply": "1",
         "notes": "1-Automóvel/Moto 2-Residencial 3-Outros → Auto"},
    ] + [dict(s) for s in _ALLIANZ_FAMILY_AUTO_STEPS],
    finalize_anchors=list(_ALLIANZ_FAMILY_FINALIZE),
)
ALFA_AUTO_WHATSAPP_V1["subservice_menu_map"] = {"guincho": "3", "bateria": "1", "pneu": "6", "chaveiro": "7"}
ALFA_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "SAIR"
# Alfa às vezes não abre guincho pelo WhatsApp ("no momento eu não consigo te
# ajudar" → central 4003-2532): vira handoff com o telefone no dossiê.
ALFA_AUTO_WHATSAPP_V1["handoff_triggers"] = ALFA_AUTO_WHATSAPP_V1["handoff_triggers"] + [
    r"n[ãa]o consigo te ajudar",
]

# --- AZUL (grupo Porto, URA própria NUMERADA — fluxo REAL 26/12/2025) -------------
AZUL_AUTO_WHATSAPP_V1 = _auto_playbook(
    "azul", "azul_assistencia_24h",
    ura_steps=[
        {"step": "menu_inicial_num",
         "anchor": r"como eu posso te ajudar\?.*\*?1\W{0,5}assist[êe]ncia 24h para o ve[íi]culo",
         "reply": "1", "notes": "variante NUMERADA antiga: 1-Assistência 24h para o veículo"},
        {"step": "menu_inicial",
         "anchor": r"como eu posso te ajudar\?.*assist[êe]ncia (?:24h para o ve[íi]culo|emergencial)",
         "reply": "Assistência emergencial",
         "notes": "lista 2025/26: 'Assistência emergencial — Guincho, técnico e chaveiro' (responder rótulo)"},
        {"step": "pedir_cpf", "anchor": r"informe o \*?cpf ou cnpj\*? do\(a\)? segurad", "reply": "{titular_cpf}",
         "requires": ["titular_cpf"]},
        {"step": "cor_menu", "anchor": r"informe a cor do ve[íi]culo", "reply": "Outra cor",
         "notes": "lista de cores; 'Outra cor' abre texto livre"},
        {"step": "cor_texto", "anchor": r"escreva qual a cor", "reply": "{veiculo_cor}",
         "notes": "default 'não sei'"},
        {"step": "menu_atendimento", "anchor": r"de que atendimento voc[êe] precisa", "reply": "1",
         "notes": "1-Novo serviço"},
        {"step": "menu_servico", "anchor": r"o que voc[êe] precisa\?\s*\|?\s*\*?1\*?\s*-\s*guincho", "reply": "{servico_opcao}",
         "requires": ["servico_opcao"],
         "notes": "1-Guincho 2-Bateria 3-Troca de pneu 4-Chaveiro (numerado)"},
        {"step": "bateria_submenu", "anchor": r"entendi\. o que voc[êe] precisa\?.*recarga de bateria",
         "reply": "Recarga de bateria", "notes": "submenu da bateria: Recarga / Bateria nova / Na garantia"},
        {"step": "quando", "anchor": r"para quando voc[êe] precisa que esse servi[çc]o", "reply": "1",
         "notes": "1-Tenho urgência (a frase 'confirmada somente após a finalização' faz parte desta COLETA)"},
        {"step": "no_local", "anchor": r"[ée] voc[êe] que estar[áa] no local para acompanhar", "reply": "2",
         "notes": "1-Sim 2-Não (informamos quem estará)"},
        {"step": "nome_no_local", "anchor": r"qual [ée] o nome de quem estar[áa] no local", "reply": "{pessoa_no_local}",
         "requires": ["pessoa_no_local"]},
        {"step": "telefone_contato", "anchor": r"informe um n[úu]mero de contato\. digite no formato",
         "reply": "{telefone_contato}", "requires": ["telefone_contato"], "format": "phone_br",
         "notes": "formato ESTRITO '(dd) 99999-9999' — o motor formata os dígitos"},
        {"step": "telefone_correto", "anchor": r"o n[úu]mero est[áa] correto", "reply": "1"},
        {"step": "ponto_referencia", "anchor": r"ponto de refer[êe]ncia", "reply": "{ponto_referencia}",
         "notes": "se não houver, 'não tem'"},
        {"step": "algo_mais", "anchor": r"posso te ajudar com algo mais", "reply": "Não",
         "notes": "pós-protocolo: encerrar com educação"},
        {"step": "confirmar_tudo", "anchor": r"tudo est[áa] correto", "reply": "1",
         "notes": "confirmação FINAL (RESUMO). Só alcançada em modo LIVE — no teste o freio cancela antes."},
    ],
    finalize_anchors=[
        r"tudo est[áa] correto", r"posso confirmar", r"confirmar o agendamento",
    ],
)
AZUL_AUTO_WHATSAPP_V1["subservice_menu_map"] = {"guincho": "1", "bateria": "2", "pneu": "3", "chaveiro": "4"}
AZUL_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "4"  # '4 - Sair e não agendar' no RESUMO

# --- BRADESCO (bot Europ; PLACA primeiro; fluxo REAL 05/01/2026) ------------------
BRADESCO_AUTO_WHATSAPP_V1 = _auto_playbook(
    "bradesco", "bradesco_assistencia_24h",
    ura_steps=[
        {"step": "menu_inicial", "anchor": r"voc[êe] quer assist[êe]ncia para", "reply": "Veículo",
         "notes": "Botão 1: Veículo / Botão 2: Residência (responder o rótulo)"},
        {"step": "informar_placa", "anchor": r"informa a \*?placa do ve[íi]culo", "reply": "{veiculo_placa}",
         "requires": ["veiculo_placa"], "notes": "sem espaço/traço (formato estrito)"},
        {"step": "cpf_fallback", "anchor": r"digite somente os n[úu]meros do \*?cpf\*? ou \*?cnpj\*?", "reply": "{titular_cpf}",
         "requires": ["titular_cpf"],
         "notes": "fallback quando a placa não é localizada"},
        {"step": "confirmar_veiculo", "anchor": r"podemos seguir o atendimento para este ve[íi]culo", "reply": "Sim",
         "notes": "URA mostra placa+modelo achados"},
        {"step": "problema", "anchor": r"qual o problema com o seu carro", "reply": "{servico_opcao}",
         "requires": ["servico_opcao"],
         "notes": "1-Pane(bateria/motor) 2-Acidente 3-Pneus 4-Chave 5-Combustível — o serviço deriva do problema"},
        {"step": "pane_detalhe_guincho", "anchor": r"me conta o que aconteceu:", "reply": "2",
         "only_subservices": ["guincho"],
         "notes": "guincho: 2-andando e parou (leva ao reboque)"},
        {"step": "pane_detalhe_bateria", "anchor": r"me conta o que aconteceu:", "reply": "1",
         "only_subservices": ["bateria"],
         "notes": "bateria: 1-estacionado e não liga (leva ao técnico/bateria)"},
        {"step": "hibrido_eletrico", "anchor": r"h[íi]brido/?el[ée]trico", "reply": "Não",
         "notes": "default Não; caso elétrico, adaptativo assume"},
        {"step": "garagem_subsolo", "anchor": r"garagem subsolo", "reply": "Não",
         "notes": "default Não; subsolo real → adaptativo"},
        {"step": "necessidades_especiais", "anchor": r"necessidades especiais ou mobilidade reduzida", "reply": "Não",
         "notes": "default Não; se houver no caso, adaptativo assume"},
        {"step": "quando", "anchor": r"envie a assist[êe]ncia agora ou prefere agendar", "reply": "Enviar agora",
         "notes": "passo de COLETA no MEIO do fluxo (era FALSO freio) — urgência é o default"},
        {"step": "via_local_rodovia", "anchor": r"\*?via local\*? ou \*?rodovia", "reply": "Via local",
         "notes": "default via local; rodovia real → adaptativo (orientação de concessionária)"},
        {"step": "levar_oficina", "anchor": r"quer levar o ve[íi]culo at[ée] uma oficina", "reply": "Sim",
         "notes": "guincho com destino conhecido"},
        {"step": "oficinas_referenciadas", "anchor": r"op[çc][õo]es de oficinas referenciadas", "reply": "Não quero",
         "notes": "v1: destino do caso; oferecer as referenciadas ao cliente é evolução da Faixa 6"},
        {"step": "destino_rodovia", "anchor": r"pra onde voc[êe] quer levar seu ve[íi]culo, se encontra em uma \*?rodovia", "reply": "Nao",
         "notes": "destino em rodovia? default não"},
        {"step": "confirmar_abertura", "anchor": r"posso confirmar a abertura", "reply": "Sim",
         "notes": "confirmação FINAL. Só alcançada em modo LIVE — no teste o freio cancela antes."},
    ],
    finalize_anchors=[
        # Freio REAL: revisão final "Origem/Destino ... Posso confirmar a abertura
        # da assistência?" ('enviar agora ou prefere agendar' é COLETA, não freio!)
        r"posso confirmar a abertura",
        r"as informa[çc][õo]es est[ãa]o corretas",
        r"posso confirmar", r"deseja confirmar",
    ],
)
BRADESCO_AUTO_WHATSAPP_V1["subservice_menu_map"] = {"guincho": "1", "bateria": "1", "pneu": "3", "chaveiro": "4"}
BRADESCO_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "Não"
# Placa não localizada 2x → URA manda para a plataforma Europ (sem atendimento
# neste canal): vira handoff com a orientação no dossiê.
BRADESCO_AUTO_WHATSAPP_V1["handoff_triggers"] = BRADESCO_AUTO_WHATSAPP_V1["handoff_triggers"] + [
    r"n[ãa]o podemos seguir com a sua solicita[çc][ãa]o",
]

# --- MAPFRE (exige DATA DE NASCIMENTO do titular; transfere cedo p/ humano) ------
MAPFRE_AUTO_WHATSAPP_V1 = _auto_playbook(
    "mapfre", "mapfre_assistencia_24h",
    ura_steps=[
        {"step": "pedir_cpf", "anchor": r"informe o \*?cpf\*? ou \*?cnpj do titular", "reply": "{titular_cpf}",
         "requires": ["titular_cpf"]},
        {"step": "nascimento", "anchor": r"data de nascimento da pessoa titular", "reply": "{titular_nascimento}",
         "requires": ["titular_nascimento"],
         "notes": "Mapfre valida identidade com dt. nascimento — coletar ANTES de acionar"},
        {"step": "menu_seguro", "anchor": r"sobre qual \*?seguro\*? voc[êe] quer falar", "reply": "Carro e moto"},
        {"step": "informar_placa", "anchor": r"informe o n[úu]mero da \*?placa do seu ve[íi]culo", "reply": "{veiculo_placa}",
         "requires": ["veiculo_placa"]},
    ],
    finalize_anchors=[r"podemos confirmar", r"posso confirmar", r"deseja confirmar"],
)
MAPFRE_AUTO_WHATSAPP_V1["subservice_menu_map"] = {"guincho": "Assistência 24H", "bateria": "Assistência 24H", "pneu": "Assistência 24H", "chaveiro": "Assistência 24H"}
# Mapfre exige nascimento em TODOS os subserviços auto.
MAPFRE_AUTO_WHATSAPP_V1["subservices"] = {
    k: {"required_slots": list(v["required_slots"]) + ["titular_nascimento"]}
    for k, v in _AUTO_SUBSERVICES.items()
}

# --- ZURICH (fluxo REAL 23/02/2026: listas por rótulo no topo, menus NUMERADOS
# no miolo, árvore de diagnóstico de pane, confirmação explícita no final) --------
ZURICH_AUTO_WHATSAPP_V1 = _auto_playbook(
    "zurich", "zurich_assistencia_24h",
    ura_steps=[
        {"step": "menu_assunto", "anchor": r"para qual dos assuntos voc[êe] precisa", "reply": "Carro e moto"},
        {"step": "menu_servicos", "anchor": r"escolha um dos servi[çc]os para continuar", "reply": "Assistência 24h"},
        {"step": "acionar_assistencia", "anchor": r"acionar a assist[êe]ncia 24h\*? ou \*?acionar o seguro", "reply": "Acionar assistência 24h",
         "notes": "colisão/roubo é SINISTRO (handoff), não assistência"},
        {"step": "pedir_cpf", "anchor": r"qual o seu \*?cpf/?cnpj", "reply": "{titular_cpf}", "requires": ["titular_cpf"]},
        {"step": "pedir_placa", "anchor": r"qual a \*?placa do ve[íi]culo", "reply": "{veiculo_placa}",
         "requires": ["veiculo_placa"]},
        {"step": "confirmar_veiculo", "anchor": r"esse [ée] o ve[íi]culo que precisa de assist[êe]ncia", "reply": "1",
         "notes": "1-Sim (veículo achado pela placa do caso)"},
        {"step": "o_que_aconteceu", "anchor": r"me conte o que aconteceu", "reply": "{servico_opcao}",
         "requires": ["servico_opcao"],
         "notes": "menu numerado: 1-combustível 2-pneu 3-chave 4-panes 5-sinistro 6-terceiros; a árvore de diagnóstico ('o que houve?', câmbio etc.) fica com o adaptativo"},
        {"step": "rodovia", "anchor": r"est[áa] em estrada/?rodovia", "reply": "2",
         "notes": "1-Sim 2-Não; default Não, rodovia real → adaptativo"},
        {"step": "garagem", "anchor": r"garagem subsolo ou elevada", "reply": "2",
         "notes": "1-Sim 2-Não; default Não"},
        {"step": "endereco_livre", "anchor": r"compartilhe sua localiza[çc][ãa]o fixa ou me diga o endere[çc]o",
         "reply": "{local_atual}", "requires": ["local_atual"],
         "notes": "aceita endereço em texto livre (Ex: Rua Sergipe, 1440 - Belo Horizonte)"},
        {"step": "endereco_detalhado", "anchor": r"digitar os dados do endere[çc]o de forma mais detalhada", "reply": "1",
         "notes": "fallback quando a localização/endereço não geocodifica; CEP/rua/nº pelo adaptativo"},
        {"step": "ref_opcional", "anchor": r"algum ponto de refer[êe]ncia que gostaria de informar", "reply": "2",
         "notes": "1-Sim 2-Não (menu NUMERADO — texto livre é rejeitado aqui)"},
        {"step": "endereco_correto", "anchor": r"os dados est[ãa]o corretos", "reply": "1",
         "notes": "confirma o resumo do ENDEREÇO (meio do fluxo — não é o freio)"},
        {"step": "tipo_assistencia", "anchor": r"qual o tipo de assist[êe]ncia voc[êe] gostaria", "reply": "1",
         "notes": "1-Imediata 2-Agendada"},
        {"step": "destino_livre", "anchor": r"para onde devemos levar seu ve[íi]culo", "reply": "{local_destino}",
         "notes": "guincho: destino em texto livre"},
        {"step": "telefone_e_esse", "anchor": r"seu telefone de contato para a assist[êe]ncia [ée]", "reply": "2",
         "notes": "2-Não → informamos o telefone do caso no passo seguinte (nunca herdar contato errado)"},
        {"step": "telefone", "anchor": r"confirmar? pra n[óo]s o seu \*?n[úu]mero de telefone", "reply": "{telefone_contato}",
         "requires": ["telefone_contato"]},
        {"step": "confirmar_solicitacao", "anchor": r"podemos confirmar a solicita[çc][ãa]o", "reply": "1",
         "notes": "confirmação FINAL. Só alcançada em modo LIVE — no teste o freio cancela antes."},
    ],
    finalize_anchors=[r"podemos confirmar a solicita[çc][ãa]o", r"posso confirmar", r"deseja confirmar"],
)
ZURICH_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    # Menu 2026 'me conte o que aconteceu' é NUMERADO: 1-combustível 2-pneu
    # 3-chave 4-panes 5-sinistro 6-reboque p/ terceiros. Bateria = pane (4) e o
    # detalhe (Problema de Bateria) o adaptativo escolhe na árvore de diagnóstico.
    "guincho": "4", "bateria": "4", "pneu": "2", "chaveiro": "3",
}
ZURICH_AUTO_WHATSAPP_V1["finalize_abort_reply"] = ""  # sem opção de sair no resumo: silêncio (URA encerra sozinha)


_PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    f"{p['playbook_id']}@v{p['version']}": p
    for p in (
        ALLIANZ_RESIDENCIAL_WHATSAPP_V1,
        ALLIANZ_AUTO_WHATSAPP_V1,
        PORTO_AUTO_WHATSAPP_V1,
        HDI_AUTO_WHATSAPP_V1,
        YELUM_AUTO_WHATSAPP_V1,
        TOKIO_AUTO_WHATSAPP_V1,
        ALFA_AUTO_WHATSAPP_V1,
        AZUL_AUTO_WHATSAPP_V1,
        BRADESCO_AUTO_WHATSAPP_V1,
        MAPFRE_AUTO_WHATSAPP_V1,
        ZURICH_AUTO_WHATSAPP_V1,
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
# Azul é do grupo Porto MAS tem WhatsApp e URA próprios → corredor próprio.
_INSURER_ALIASES = {
    "allianz": "allianz", "allianz seguros": "allianz",
    "porto": "porto", "porto seguro": "porto", "itau": "porto", "itau seguros": "porto",
    "azul": "azul", "azul seguros": "azul",
    "hdi": "hdi", "hdi seguros": "hdi",
    "yelum": "yelum", "liberty": "yelum", "liberty seguros": "yelum", "libe": "yelum",
    "tokio": "tokio", "tokio marine": "tokio", "tokyo": "tokio",
    "alfa": "alfa", "alfa seguradora": "alfa", "alfa seguros": "alfa",
    "bradesco": "bradesco", "bradesco seguros": "bradesco", "bradesco auto/re": "bradesco",
    "mapfre": "mapfre", "mapfre seguros": "mapfre",
    "zurich": "zurich", "zurich seguros": "zurich", "zurich santander": "zurich",
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

def match_ura_step(playbook: Dict[str, Any], insurer_message: str, subservice: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Primeiro passo de URA cuja âncora casa com a mensagem da seguradora.
    `only_subservices` restringe o passo a certos subserviços (a MESMA pergunta
    da URA pode exigir respostas diferentes por serviço)."""
    text = _norm(insurer_message)
    sub = str(subservice or "").strip().lower()
    for step in playbook.get("ura_steps") or []:
        only = step.get("only_subservices")
        if only and sub not in [str(x).lower() for x in only]:
            continue
        if re.search(step.get("anchor") or r"$^", text, re.IGNORECASE | re.DOTALL):
            return step
    return None


def _format_phone_br(value: str) -> str:
    """Formata dígitos no padrão estrito '(dd) 99999-9999' (a Azul REJEITA outro)."""
    d = "".join(ch for ch in str(value or "") if ch.isdigit())
    if d.startswith("55") and len(d) >= 12:
        d = d[2:]
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return str(value)


def render_reply(step: Dict[str, Any], slots: Dict[str, Any]) -> Dict[str, Any]:
    """Resposta do passo com slots aplicados. Slot faltante -> blocker (nunca chuta)."""
    template = str(step.get("reply") or "")
    missing = [f for f in (step.get("requires") or []) if not str(slots.get(f) or "").strip()]
    if missing:
        return {"ok": False, "missing": missing, "reply": None}
    try:
        reply = template.format(**{k: str(v) for k, v in slots.items()})
    except KeyError as exc:  # placeholder sem slot
        return {"ok": False, "missing": [str(exc).strip("'")], "reply": None}
    if step.get("format") == "phone_br":
        reply = _format_phone_br(reply)
    return {"ok": True, "missing": [], "reply": reply}


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
    m = re.search(anchors.get("eta") or r"$^", text, re.IGNORECASE)
    if m:
        out["eta_minutes"] = m.group(1)
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
