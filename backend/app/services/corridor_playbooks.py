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

DESFECHO (SPEC-063, 03/08/2026): **nem todo corredor ABRE chamado.**
`outcome`, por seguradora e por subserviço, diz como o trabalho TERMINA:

    abre        segue o fluxo até o protocolo (Azul/vidros — e todo o resto)
    encaminha   a seguradora NÃO abre chamado por este canal: ela entrega um
                FORMULÁRIO (Porto/vidros) ou uma ORIENTAÇÃO (Zurich/vidros).
                O corredor entrega isso ao segurado e encerra como
                resolvido-por-encaminhamento. Encaminhar não é falhar — é o
                desfecho correto naquela seguradora.

E onde NÃO há menu observado, o subserviço simplesmente não é declarado:
`subservice_supported()` devolve False e o caso vira handoff. 📊 Vidros só está
ligado em azul, porto e zurich porque só nessas três o rótulo do menu foi
capturado em `ura_maps` (status='observed', 03/08/2026). Inventar rótulo de menu
é o defeito que manda o segurado para a opção errada da seguradora.
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
        # ENCANADOR (SPEC-063, 03/08/2026): mesma espinha do eletricista — mesma
        # opção de URA ("1 - casa"), mesmos dados de apólice/contato — e os slots
        # do problema trocados para VAZAMENTO. O eletricista pergunta se há
        # fumaça; o encanador pergunta se a água está escorrendo e se o registro
        # foi fechado. É o mesmo padrão de guardrail: a pergunta que separa
        # "pinga a torneira" de "está alagando" tem de ser feita ANTES do
        # acionamento, porque as duas frases pedem prioridades diferentes.
        # 💭 A URA da Allianz não pede estes campos — quem os usa é o
        # ESPECIALISTA humano da assistência (e a corretora, para priorizar).
        "encanador": {
            "tipo_servico_opcao": "1",
            "required_slots": ["titular_cpf", "endereco_numero", "telefone_contato", "problema_descricao",
                               "periodo_preferido", "vazamento_local", "agua_escorrendo",
                               "risco_confirmado_registro_fechado"],
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
        "schedule": r"agendad[ao] para o dia\s*(\d{1,2}(?:/\d{1,2}(?:/\d{2,4})?)?)\s*,?\s*entre\s*(\d{1,2}\s?h)\s*e\s*(\d{1,2}\s?h)",
    },
    # Resumo estruturado ao ESPECIALISTA humano (fluxo real 01/04/2026: a URA
    # transfere emergenciais ao analista — a operadora abre com o caso mastigado).
    "opening_template": (
        "Ola, aqui e a corretora. Preciso acionar {subservice_label} para a residencia do nosso segurado.\n"
        "Titular: {titular_nome} (CPF {titular_cpf})\n"
        "Endereco: o da apolice, numero {endereco_numero}\n"
        "Problema: {problema_descricao}\n"
        "Telefone de contato: {telefone_contato}\n"
        "Periodo preferido: {periodo_preferido}"
    ),
    "subservice_labels": {
        "eletricista": "eletricista", "chaveiro": "chaveiro",
        "encanador": "encanador", "eletrodomesticos": "reparo de eletrodomestico",
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

# ---------------------------------------------------------------------------
# DESFECHO do corredor (SPEC-063, 03/08/2026)
# ---------------------------------------------------------------------------
# Até aqui todo corredor tinha um só fim possível: chegar ao protocolo. Vidros
# provou que isso é falso. Na Porto, o fluxo de vidro TERMINA num formulário; na
# Zurich, numa orientação. Sem nomear esse desfecho, o motor ficaria esperando
# um protocolo que nunca vem, e o atendimento morreria em "monitorando".
OUTCOME_ABRE = "abre"            # vai até o protocolo (padrão de todo subserviço)
OUTCOME_ENCAMINHA = "encaminha"  # entrega link/orientação ao segurado e ENCERRA

# VIDRO NÃO É REBOQUE. Não se pergunta onde o veículo está nem para onde levar:
# ou o prestador vai até o veículo, ou o veículo vai à oficina de vidro na data
# combinada. Os slots saem de `_AUTO_SLOTS_COMMON` **menos** `local_atual` —
# derivação explícita para que ninguém precise conferir duas listas:
#   titular_cpf · veiculo_placa · problema_descricao (o dano) · quando (a data)
#   · telefone_contato
_VIDROS_SLOTS = [s for s in _AUTO_SLOTS_COMMON if s != "local_atual"]
_VIDROS_LABEL = "conserto ou troca de vidro"

# ---------------------------------------------------------------------------
# APELIDOS DE SUBSERVIÇO — um nome canônico por trabalho
# ---------------------------------------------------------------------------
# `pane seca` é o caso que obriga esta tabela a existir.
#
# 📊 Evidência de URA (`ura_maps` status='observed', 03/08/2026): NENHUMA das 10
# seguradoras tem opção própria de pane seca. Allianz e Alfa dizem
# "*3* - Guincho para *pane mecânica*"; a Zurich lista "pane seca" DENTRO da
# assistência 24h, junto de reboque e socorro mecânico; Bradesco, HDI e Yelum
# usam "Pane ou Defeito", genérico. Não há um único menu em que "pane seca"
# seja uma tecla.
#
# Declarar um subserviço `pane_seca` obrigaria a inventar essa tecla — e o
# corredor responderia à URA uma opção que não existe na tela. Um menu inventado
# é pior que subserviço nenhum. Então pane seca ENTRA PELO GUINCHO, e o
# classificador do Atlas (`infer_ramo_servico`, que já devolve "pane_seca")
# chega aqui e é traduzido, sem um segundo classificador para divergir.
_SUBSERVICE_ALIASES = {
    "pane_seca": "guincho", "pane seca": "guincho", "paneseca": "guincho",
    "combustivel": "guincho", "falta de combustivel": "guincho",
    "sem combustivel": "guincho",
    # o segurado fala no singular, e às vezes fala da peça
    "vidro": "vidros", "para-brisa": "vidros", "parabrisa": "vidros",
    "para brisa": "vidros", "retrovisor": "vidros",
    # residencial: um nome por trabalho. A Porto chama de "elétrica" e
    # "hidráulica" o que a Allianz e a HDI chamam de eletricista e encanador.
    "eletrodomestico": "eletrodomesticos", "eletrica": "eletricista",
    "hidraulica": "encanador", "encanamento": "encanador",
    "desentupidor": "desentupimento",
}


def canonical_subservice(subservice: str) -> str:
    """Nome canônico do subserviço: 'pane seca' → 'guincho', 'vidro' → 'vidros'.

    Sem apelido conhecido, devolve o próprio nome em minúsculas — NUNCA um
    palpite. Nome desconhecido continua desconhecido, e vira handoff lá na
    frente (`subservice_supported`)."""
    raw = str(subservice or "").strip().lower()
    if not raw:
        return ""
    return _SUBSERVICE_ALIASES.get(_norm(raw), raw)


def _ativar_vidros(playbook: Dict[str, Any], *, menu_value: str, outcome: str,
                   referral: Optional[Dict[str, Any]] = None) -> None:
    """Liga `vidros` NUMA seguradora — só onde o rótulo do menu foi observado.

    Chamar isto é uma afirmação de evidência: existe menu capturado, e ele diz
    exatamente `menu_value`. Seguradora sem essa captura NÃO recebe a chamada, e
    por isso `subservice_supported(pb, "vidros")` devolve False lá."""
    playbook.setdefault("subservices", {})["vidros"] = {
        "required_slots": list(_VIDROS_SLOTS),
        "outcome": outcome,
        **({"referral": dict(referral)} if referral else {}),
    }
    playbook.setdefault("subservice_menu_map", {})["vidros"] = menu_value
    playbook.setdefault("subservice_labels", {})["vidros"] = _VIDROS_LABEL


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
    "protocol": r"(?:protocolo(?:\s+de\s+atendimento)?|n[úu]mero\s+da\s+(?:sua\s+)?(?:ordem|os|solicita[çc][ãa]o|assist[êe]ncia)|para a assist[êe]ncia|sobre sua assist[êe]ncia|o\.?s\.?)[^\d]{0,24}(\d[\d-]{4,18}\d)",
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
     "dynamic": "vehicle_by_plate", "fallback_adaptive": True,
     "notes": "escolhe a opção cuja placa mascarada casa com a placa do caso (JC#-###9 ↔ JCL9A59); sem match → adaptativo"},
    {"step": "avisos_informativos",
     "anchor": (r"termo de privacidade|dicas importantes para conseguir te atender|fique tranquilo, vamos te ajudar|"
                r"vale lembrar:|voc[êe] sabia\?|op[çc][ãa]o inv[áa]lida|vamos tentar novamente|"
                r"precisando estamos por aqui|agradece o seu contato|aguarde em local seguro"),
     "reply": "", "noop": True,
     "notes": "mensagens informativas/erro da URA — NUNCA responder (o adaptativo respondia 'Ciente, pode prosseguir' e quebrava o menu)"},
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
    {"step": "destino_menu", "anchor": r"preciso saber o endere[çc]o de destino", "reply": "1",
     "notes": "1-Oficina mecânica ou outro endereço 2-Não sei (só estado/cidade)"},
    {"step": "destino_uf", "anchor": r"informe a \*?uf\*? \(sigla do estado\) \*?do destino", "reply": "{destino_uf}",
     "fallback_adaptive": True, "notes": "UF deduzida de local_destino pelo parser"},
    {"step": "destino_cidade", "anchor": r"e qual a cidade", "reply": "{destino_cidade}", "fallback_adaptive": True},
    {"step": "destino_logradouro", "anchor": r"informe apenas o nome do logradouro", "reply": "{destino_logradouro}",
     "fallback_adaptive": True},
    {"step": "destino_numero", "anchor": r"qual o n[úu]mero do endere[çc]o \(ou quil[ôo]metro", "reply": "{destino_numero}",
     "fallback_adaptive": True, "notes": "só dígitos ('Km 205' é rejeitado — o parser extrai '205')"},
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
    ] + [dict(s) for s in _ALLIANZ_FAMILY_AUTO_STEPS] + [
        {"step": "endereco_origem_menu", "anchor": r"selecione o endere[çc]o onde est[áa] o ve[íi]culo", "reply": "3",
         "notes": "Allianz 2026: 1-endereço da apólice 2-compartilhar localização 3-informar manual "
                  "(Alfa NÃO tem a opção 3 — lá o adaptativo decide)"},
    ],
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
         "reply_if_step_done": {"step": "pedir_cpf", "reply": "Seguro Auto"},
         "notes": "menu raiz: se JÁ digitamos o CPF nesta sessão o cliente exibido é o nosso → Seguro Auto direto; senão re-identifica (nunca acionar no CPF lembrado do cliente anterior)"},
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
         "notes": "responder o RÓTULO completo. 📊 lista real 03/08/2026: Guincho (reboque) / Bateria / "
                  "Troca de pneu / Conserto de vidro (Inclui retrovisor, farol ou lanterna) / "
                  "Chaveiro para o veículo / Táxi"},
        {"step": "bateria_submenu", "anchor": r"entendi\. o que voc[êe] precisa",
         "reply": "Recarga de bateria",
         "notes": "submenu após 'Bateria' (teste real 12/07: Recarga de bateria / Bateria nova / Na garantia — travava aqui)"},
        # VIDROS na Porto NÃO abre chamado aqui — DESFECHO = encaminha.
        # 📊 URA real 03/08/2026, três mensagens seguidas:
        #   "Certo. Para conserto ou reparo de vidro, retrovisor, farol ou
        #    lanterna, é necessário *preencher o formulário* de sinistro de
        #    vidros abaixo"
        #   "https://porto.vc/reparovidros"
        #   "Não se preocupe, esse acionamento *para vidros* não irá afetar a
        #    sua classe de bônus."
        # O link vem numa mensagem SOZINHA — por isso ele é capturado por
        # `capture_anchors.tracking_link` (qualquer http), e não por uma âncora
        # que exija a palavra 'formulário' na mesma mensagem. A URL NÃO fica
        # escrita aqui: quem a entrega é a seguradora, na hora.
        {"step": "vidros_formulario",
         "anchor": (r"necess[áa]rio \*?preencher o formul[áa]rio\*? de sinistro de vidros|"
                    r"para conserto ou reparo de vidro,? retrovisor,? farol ou lanterna"),
         "reply": "", "noop": True, "referral": True, "outcome": OUTCOME_ENCAMINHA,
         "notes": "não responder à URA: o trabalho passa a ser ENTREGAR o formulário ao segurado e encerrar"},
        {"step": "necessidade_guincho", "anchor": r"op[çc][ãa]o que descreve melhor a sua necessidade",
         "reply": "Remoção de veículo",
         "notes": "Remoção de veículo (pane) · 'Envolvimento em acidente' = sinistro → handoff antes de chegar aqui"},
        {"step": "menu_quando", "anchor": r"para quando voc[êe] precisa que esse servi[çc]o", "reply": "Tenho urgência",
         "notes": "botões: Tenho urgência / Agendar. A frase 'confirmada somente após a finalização' é COLETA."},
        {"step": "complemento", "anchor": r"digite ent[ãa]o um \*?complemento", "reply": "não tem",
         "notes": "complemento do endereço; sem complemento = 'não tem'"},
        {"step": "ponto_referencia",
         "anchor": r"(?:o local tem|pode me informar) algum \*?ponto de refer[êe]ncia",
         "reply": "{ponto_referencia}",
         "notes": "só a PERGUNTA — o RESUMO da solicitação também contém 'Ponto de referência:' e não deve disparar (teste 12/07 respondeu 'não tem' ao resumo)"},
        {"step": "destino_sabe", "anchor": r"onde o guincho deve levar seu ve[íi]culo", "reply": "Sim",
         "notes": "guincho: já sabemos o destino (local_destino do caso)"},
        {"step": "no_local", "anchor": r"[ée] voc[êe] que est[áa] no local para (?:acompanhar|aguardar)", "reply": "Sim",
         "notes": "quem está no local acompanha; dados de contato ajustáveis no menu de revisão"},
        {"step": "pode_ligar", "anchor": r"posso te ligar no n[úu]mero abaixo", "reply": "Sim",
         "notes": "autoriza contato telefônico do prestador"},
        {"step": "endereco_livre", "anchor": r"digite o endere[çc]o completo do local", "reply": "{local_atual}",
         "reply_repeat": "{local_destino}", "requires": ["local_atual"], "fallback_adaptive": True,
         "notes": "Porto aceita endereço em texto livre; 1ª vez = origem, 2ª = destino do guincho"},
        {"step": "endereco_correto", "anchor": r"est[áa] correto\s*\?", "reply": "Sim",
         "notes": "confirma o geocode do endereço QUE NÓS digitamos"},
        {"step": "aguarde",
         "anchor": r"aguarde um momento|que bom ter voc[êe] de volta|aguarde enquanto solicito|localizei o endere[çc]o|para informar o endere[çc]o, voc[êe] tem essas op[çc][õo]es|compartilhe a sua localiza[çc][ãa]o|preencha o formul[áa]rio abaixo|falta pouco para finalizarmos",
         "reply": "", "noop": True, "notes": "mensagens de espera/instrução — não responder"},
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

# --- Família YELUM/HDI (MESMO bot white-label "Assistência 24 horas"; Yelum =
# ex-Liberty, grupo HDI desde 2024). Fluxo REAL COMPLETO 16/03/2026 (Yelum,
# 100% bot até o protocolo) + 28/01/2026 (HDI). Botões por rótulo; timeout 12min.
# PONTO DE NÃO-RETORNO: "quer o atendimento para agora ou prefere agendar?" —
# responder Agora/Agendar ABRE o serviço na hora. O destino é seguro de informar.

# ...e essa pergunta tem TRÊS redações reais. 📊 Banco de produção, 03/08/2026,
# `observed_events` ILIKE '%prefere agendar%' (auto E residencial da família):
#
#   "Você está solicitando o atendimento *para* agora ou prefere agendar..."  hdi 9
#   "Você quer o atendimento *para* agora ou prefere agendar..."       hdi 2 · yelum 17
#   "Você precisa do atendimento agora ou prefere agendar..."          hdi 1 · yelum 4
#
# A terceira NÃO tem o "para" — e era a única que a âncora literal
# `atendimento para agora ou prefere agendar` não pegava. O freio ficava furado
# exatamente na tela que ABRE o serviço na hora. 📊 A ocorrência da HDI
# (02/06/2026, sessão 26c0546f) é RESIDENCIAL: a mesma sessão traz "Para esse CPF
# localizamos o serviço de *ENCANADOR*" e "Ela não possui mais utilizações de
# encanador".
#
# O "para" vira opcional, e a âncora vira UMA constante: ela é usada no passo de
# URA e nos freios de três playbooks, e três cópias literais divergem no dia em
# que a seguradora escrever a quarta redação.
_HDI_FAMILY_AGORA_OU_AGENDAR = r"atendimento (?:para )?agora ou prefere agendar"

_YELUM_FAMILY_STEPS = [
    {"step": "identificacao_dado",
     "anchor": r"informe \*?apenas um dos dados|informe \*?um dos dados abaixo|informe somente o \*?cpf ou cnpj\*? do t[íi]tular",
     "reply": "{titular_cpf}", "requires": ["titular_cpf"],
     "notes": "entrada: CPF/CNPJ do segurado OU placa (frota usa CNPJ)"},
    {"step": "continuar_com_placa", "anchor": r"identifiquei em seu cadastro a placa", "reply": "Automóvel",
     "notes": "após CPF, a URA acha a placa e pergunta veículo ou residencial"},
    {"step": "informar_nome", "anchor": r"informe o seu nome ou como gostaria de ser chamad", "reply": "Atendimento",
     "notes": "nome de quem opera o canal (a corretora)"},
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
     "notes": "guincho por pane: leva direto ao Guincho (fluxo real 16/03/2026)"},
    {"step": "endereco_como", "anchor": r"op[çc][õo]es para informar o endere[çc]o onde o ve[íi]culo est[áa]",
     "reply": "Digitar endereço", "notes": "variante jan/2026: Digitar endereço / Compartilhar / Informar o CEP / Não sei"},
    {"step": "endereco_direto_2026",
     "anchor": r"para informar o endere[çc]o onde o ve[íi]culo est[áa],? \*?escolha apenas uma",
     "reply": "{local_atual}", "requires": ["local_atual"],
     "notes": "URA jul/2026: aceita o endereço COMPLETO digitado — sem clique (validado no teste real 12/07)"},
    {"step": "descreva_situacao", "anchor": r"descreva em suas palavras", "reply": "{problema_descricao}",
     "requires": ["problema_descricao"], "fallback_adaptive": True,
     "notes": "campo livre após 'Não sei' na pane — descrição real do caso"},
    {"step": "endereco_rua", "anchor": r"digite \*?somente a rua", "reply": "{local_rua}",
     "fallback_adaptive": True, "notes": "rua deduzida de local_atual pelo parser; sem dedução → adaptativo"},
    {"step": "endereco_numero", "anchor": r"qual (?:[ée] )?o \*?n[úu]mero\*?\s*\?", "reply": "{local_numero}",
     "reply_repeat": "{destino_numero}", "fallback_adaptive": True,
     "notes": "1ª vez = nº da origem; 2ª vez = nº do destino"},
    {"step": "endereco_bairro", "anchor": r"qual (?:[ée] )?o \*?bairro", "reply": "{local_bairro}",
     "reply_repeat": "{destino_bairro}", "fallback_adaptive": True},
    {"step": "endereco_cidade", "anchor": r"qual (?:[ée] )?a \*?cidade", "reply": "{local_cidade}",
     "reply_repeat": "{destino_cidade}", "fallback_adaptive": True},
    {"step": "endereco_estado", "anchor": r"qual o \*?estado", "reply": "{local_uf}",
     "reply_repeat": "{destino_uf}", "fallback_adaptive": True},
    {"step": "confirma_endereco", "anchor": r"voc[êe] confirma o endere[çc]o", "reply": "Sim",
     "notes": "resumo geocodificado do QUE NÓS digitamos (origem e destino) — confirmar"},
    {"step": "complemento_ref", "anchor": r"quais s[ãa]o o complemento e/?ou refer[êe]ncia", "reply": "{ponto_referencia}",
     "notes": "default 'não tem'"},
    {"step": "garagem", "anchor": r"o ve[íi]culo est[áa] em uma garagem", "reply": "Não",
     "notes": "default Não; subsolo real → adaptativo"},
    {"step": "cambio_rodas", "anchor": r"c[âa]mbio\*? ou as \*?rodas\*? est[ãa]o travadas", "reply": "Não",
     "notes": "default Não; travado de verdade → adaptativo"},
    {"step": "eletrico_hibrido", "anchor": r"el[ée]trico ou h[íi]brido", "reply": "Não"},
    {"step": "rebaixado", "anchor": r"o ve[íi]culo [ée] rebaixado", "reply": "Não"},
    {"step": "situacao_risco", "anchor": r"situa[çc][õo]es de risco", "reply": "Nenhuma das anteriores",
     "notes": "se o caso indicar risco real, o adaptativo assume"},
    {"step": "ocupantes", "anchor": r"ocupantes tem alguma das particularidades|algu[ée]m da lista abaixo no local",
     "reply": "Nenhuma das anteriores"},
    {"step": "destino_como", "anchor": r"para onde devemos levar o ve[íi]culo", "reply": "Digitar endereço",
     "notes": "guincho: informar o destino do caso (rua/nº/bairro/cidade/UF do parser)"},
    {"step": "deseja_continuar", "anchor": r"deseja continuar (?:este|com o) atendimento", "reply": "Sim"},
    {"step": "falar_analista", "anchor": r"gostaria de falar com um de nossos analistas", "reply": "Sim",
     "notes": "72h/pós-atendimento (teste real 12/07): SIM → fila → analista humano recebe o resumo do caso e abre a nova solicitação"},
    {"step": "quando_agora", "anchor": _HDI_FAMILY_AGORA_OU_AGENDAR, "reply": "Agora",
     "notes": "PONTO DE NÃO-RETORNO (abre na hora). Só alcançado em modo LIVE — no teste o freio cancela antes."},
    {"step": "aguarde_fila",
     "anchor": (r"ainda n[ãa]o identificamos a sua resposta|voc[êe] est[áa] na fila|alto volume de atendimentos|"
                r"alta demanda de servi[çc]os|aguarde (?:um momento|s[óo] mais)|te transfiro para um|"
                r"transferido para fila|dicas (?:r[áa]pidas|sobre como funciona)|seja bem-?vindo ao atendimento|"
                r"estamos prontos para seguir com sua solicita|s[óo] preciso de mais algumas informa|"
                r"enviaremos o servi[çc]o de|foi abert[ao] com sucesso|no final desta conversa|"
                r"orienta[çc][õo]es importantes|problema na comunica[çc][ãa]o com o sistema|"
                r"necess[áa]rio falar com um de nossos especialistas|identificamos que voc[êe] deseja falar|"
                r"foi aberta uma assist[êe]ncia para a placa|n[ãa]o h[áa] mais nenhuma solicita[çc][ãa]o em andamento"),
     "reply": "", "noop": True, "notes": "fila/aviso/informativo — NÃO responder (o bot manda rajadas)"},
]
_YELUM_FAMILY_FINALIZE = [
    # Único gate real: responder 'Agora'/'Agendar' ABRE o serviço imediatamente.
    _HDI_FAMILY_AGORA_OU_AGENDAR,
    r"podemos confirmar", r"deseja confirmar",
]

# ===========================================================================
# FORMULÁRIO NATIVO (WhatsApp Flow) — a tela que não aceita texto
# ===========================================================================
# 📊 Desde 18/06/2026 a família HDI/Yelum substituiu as telas de condição do
# veículo por um **WhatsApp Flow** (aplicativo dentro do WhatsApp). A mensagem
# que o abre é sempre a mesma, e ela NÃO tem botões:
#
#   "Para que a remoção do veículo ocorra sem imprevistos, precisamos entender
#    o local e as condições do veículo."
#
# 📊 `observed_events` (banco de produção, consultado em 03/08/2026): essa
# mensagem aparece 4 vezes — hdi 18/06, hdi 15/07, hdi 18/07 e yelum 18/07 — e
# são os 4 acionamentos mais recentes da família. TODOS param nela: o corredor
# reconhece o marcador `[FORMULARIO NATIVO]` do parser de interativas e cai em
# `handoff_triggers` → needs_human. Nenhum deles chegou ao protocolo.
#
# O que destrava é RESPONDER o formulário por código. E responder exige o
# SCHEMA — quais telas, quais campos, e o **id** de cada opção. Ele está
# capturado: o clique humano de 18/07/2026 (`msg_type='flow_reply'`,
# `source='live'`) trouxe, dentro de `wa_flow_response_params.response_message`,
# o formulário inteiro com `data-source` de cada componente.
#
# Este bloco é a transcrição desse schema. É DADO versionado, como o resto dos
# corredores: nada aqui foi deduzido de tela parecida, e onde a captura veio
# vazia (ver `rb_Ocupantes` id "4") o vazio ficou vazio.
#
# UM REGISTRO, DUAS REFERÊNCIAS: HDI e Yelum são o MESMO bot white-label e usam
# o MESMO `flow_id`. O registro é um objeto só, apontado pelos dois playbooks —
# `native_flows` de um É `native_flows` do outro (`is`, não `==`). Duplicar
# criaria dois schemas para divergirem no dia em que a HDI mudar uma opção.
NATIVE_FLOW_CONDICOES_VEICULO = "857030507196739"

# Âncora da mensagem que ABRE o flow (o corpo vem antes do marcador do parser).
NATIVE_FLOW_PROMPT_ANCHOR = r"precisamos entender o local e as condi[çc][õo]es do ve[íi]culo"

_FLOW_CONDICOES_VEICULO_V2: Dict[str, Any] = {
    "flow_id": NATIVE_FLOW_CONDICOES_VEICULO,
    "flow_name": ("Automóvel - Detalhes do atendimento (veículo, local e ocupantes) V2 "
                  "[Redução de perguntas]"),
    "insurer_family": ("hdi", "yelum"),
    "prompt_anchor": NATIVE_FLOW_PROMPT_ANCHOR,
    # Procedência da transcrição — quem duvidar refaz a query.
    "observed": {
        "source": "observed_events.interactive → extra.paramsJSON → "
                  "wa_flow_response_params.response_message",
        "insurer_key": "hdi",
        "msg_type": "flow_reply",
        "event_source": "live",
        "wa_timestamp": "2026-07-18T21:51:52Z",
    },
    "screens": [
        {
            "id": "scr_SituacaoVeiculo",
            "title": "Situação do veículo",
            "components": [
                {
                    "name": "rb_EmGaragemOuEstacionamento",
                    "type": "RadioButtonsGroup",
                    "label": "O veículo está em uma garagem ou estacionamento?",
                    "required": True,
                    # `"visible": "${data.isVisibleGaragem}"` — bandeira que só o
                    # servidor da seguradora resolve. Offline não dá para avaliar,
                    # e o lado seguro é tratar como VISÍVEL: assim o campo continua
                    # obrigatório e o caso PEDE o dado, em vez de omitir em silêncio
                    # um campo que o formulário pode estar exigindo.
                    "visible_if": {"kind": "data", "key": "isVisibleGaragem"},
                    "slot": "veiculo_em_garagem",
                    # SEM padrão, de propósito. Esta resposta é o que decide se
                    # `rb_NivelDaRua` — que escolhe o EQUIPAMENTO — chega a ser
                    # perguntada. Chutar "Não" aqui seria a porta dos fundos da
                    # regra que proíbe chutar o nível da rua.
                    "default": None,
                    "options": [{"id": "1", "title": "Sim"}, {"id": "0", "title": "Não"}],
                    # Apelidos só onde a palavra JÁ significa a opção. "prédio",
                    # "condomínio" e "shopping" ficaram de fora: carro parado na
                    # rua em frente ao prédio não está em garagem nenhuma.
                    "aliases": {
                        "sim": "1", "s": "1", "garagem": "1", "estacionamento": "1",
                        "subsolo": "1",
                        "nao": "0", "n": "0", "rua": "0", "via publica": "0",
                        "na rua": "0", "estacionado na rua": "0",
                    },
                },
                {
                    "name": "rb_NivelDaRua",
                    "type": "RadioButtonsGroup",
                    "label": "Em relação ao nível da rua, onde o veículo está?",
                    "required": True,
                    # `"visible": "`${form.rb_EmGaragemOuEstacionamento} == '1'`"` —
                    # esta DÁ para avaliar offline, porque o form é o que estamos
                    # montando. Veículo fora de garagem: a tela não aparece, o campo
                    # não é exigido e não entra na resposta.
                    "visible_if": {"kind": "form", "field": "rb_EmGaragemOuEstacionamento",
                                   "equals": "1"},
                    "slot": "veiculo_nivel_rua",
                    # SEM padrão: escolhe o EQUIPAMENTO enviado (plataforma, asa
                    # delta, munck). Errar aqui manda o guincho que não sobe a rampa.
                    "default": None,
                    "options": [
                        {"id": "1", "title": "Subsolo",
                         "description": "Acesso por rampa interna ou níveis abaixo do solo."},
                        {"id": "2", "title": "Acima do nível da rua",
                         "description": "Acesso por rampa íngreme ou acima do nível da via"},
                        {"id": "3", "title": "Nível da rua - com restrição de acesso",
                         "description": "Acesso direto pela rua, mas com restrições de espaço ou manobra"},
                        {"id": "4", "title": "Nível da rua - com acesso livre",
                         "description": "Acesso direto pela rua, com livre espaço para remoção e manobra"},
                    ],
                    # "rampa" NÃO é apelido de nada: aparece na descrição do
                    # subsolo ("rampa interna") E na do acima do nível ("rampa
                    # íngreme}"). Palavra ambígua num campo que escolhe equipamento
                    # tem de ficar sem resposta, não virar moeda ao ar. Pelo mesmo
                    # motivo "nível da rua" sozinho não resolve: serve às opções 3 e 4.
                    "aliases": {
                        "subsolo": "1", "garagem subterranea": "1", "abaixo do solo": "1",
                        "acima": "2", "acima do nivel": "2", "elevado": "2", "rampa ingreme": "2",
                        "restricao": "3", "com restricao": "3", "restricao de acesso": "3",
                        "livre": "4", "acesso livre": "4",
                    },
                },
                {
                    "name": "ckb_SituacoesVeiculo",
                    "type": "CheckboxGroup",
                    "label": "O veículo possui alguma das características abaixo?",
                    "required": True,
                    "multiple": True,
                    "slot": "veiculo_situacoes",
                    # COM padrão: é a mesma resposta que o corredor já dava por
                    # texto nos passos `cambio_rodas`, `rebaixado` e
                    # `eletrico_hibrido` ("Não" em cada um) — e "nenhuma" é o que
                    # ela vira quando as três viram uma tela só.
                    "default": ["nenhuma_opcoes"],
                    "none_option": "nenhuma_opcoes",
                    "options": [
                        {"id": "cambio_travado", "title": "Câmbio ou rodas travadas"},
                        {"id": "veiculo_rebaixado", "title": "Veículo rebaixado"},
                        {"id": "veiculo_blindado", "title": "Veículo blindado"},
                        {"id": "eletrico_hibrido", "title": "Veículo elétrico ou híbrido"},
                        {"id": "nenhuma_opcoes", "title": "Nenhuma das opções"},
                    ],
                    "aliases": {
                        "cambio travado": "cambio_travado", "rodas travadas": "cambio_travado",
                        "roda travada": "cambio_travado", "travado": "cambio_travado",
                        "rebaixado": "veiculo_rebaixado",
                        "blindado": "veiculo_blindado",
                        "eletrico": "eletrico_hibrido", "hibrido": "eletrico_hibrido",
                        "nenhuma": "nenhuma_opcoes", "nenhum": "nenhuma_opcoes",
                        "nao": "nenhuma_opcoes", "nada": "nenhuma_opcoes",
                    },
                },
            ],
        },
        {
            "id": "scr_InformacoesLocal",
            "title": "Informações do Local",
            "components": [
                {
                    "name": "rb_InformacoesLocal",
                    "type": "RadioButtonsGroup",
                    "label": "Qual é a situação do local onde você está?",
                    "required": True,
                    "slot": "local_situacao",
                    # SEM padrão: muda a PRIORIDADE do atendimento. Responder
                    # "Local Seguro" por preguiça de perguntar é rebaixar, no
                    # escuro, o caso de quem está parado num lugar perigoso.
                    "default": None,
                    # No JSON o `data-source` é `${data.dt_InformacoesLocal}`; os
                    # valores vieram resolvidos em `screenState.data`.
                    "options": [
                        {"id": "6", "title": "Local Seguro"},
                        {"id": "2", "title": "Local escuro ou mal iluminado"},
                        {"id": "3", "title": "Área com pouca circulação de pessoas"},
                    ],
                    # Onde há dúvida, o apelido puxa para o lado MAIS protegido:
                    # "deserto"/"isolado" viram "pouca circulação", que sobe a
                    # prioridade. O caminho contrário — inferir "seguro" — é o que
                    # não se faz.
                    "aliases": {
                        "seguro": "6", "local seguro": "6",
                        "escuro": "2", "mal iluminado": "2", "sem iluminacao": "2",
                        "pouca circulacao": "3", "deserto": "3", "isolado": "3",
                    },
                },
            ],
        },
        {
            "id": "scr_IdentificacaoOcupantes",
            "title": "Identificação dos ocupantes",
            "components": [
                {
                    "name": "rb_Ocupantes",
                    "type": "RadioButtonsGroup",
                    "label": "Há alguém no local com as dependências abaixo?",
                    "required": True,
                    "slot": "ocupantes_particularidade",
                    # COM padrão: é literalmente a resposta que o corredor já dava
                    # no passo de texto `ocupantes` ("Nenhuma das anteriores").
                    "default": "1",
                    "options": [
                        {"id": "2", "title": "Criança"},
                        {"id": "3", "title": "Idoso"},
                        # 📊 O TÍTULO VEIO VAZIO NA CAPTURA. O JSON real traz
                        # {"id":"4","title":""}. Inventar "Gestante" aqui seria
                        # exatamente o defeito que este arquivo proíbe em menu de
                        # URA — só que pior, porque ninguém reconferiria depois.
                        # Sem título não há apelido, e por isso um caso que diga
                        # "gestante" NÃO casa com opção nenhuma: vira `missing` e
                        # o humano clica. Sai do escuro quando houver captura com
                        # o título preenchido.
                        {"id": "4", "title": "", "titulo_ausente": True},
                        {"id": "5", "title": "Pessoa com deficiência"},
                        {"id": "6", "title": "Cirurgia Recente"},
                        {"id": "1", "title": "Nenhuma das anteriores"},
                    ],
                    "aliases": {
                        "crianca": "2", "bebe": "2", "menor": "2",
                        "idoso": "3", "idosa": "3",
                        "pcd": "5", "deficiente": "5", "deficiencia": "5",
                        "cirurgia": "6", "cirurgia recente": "6", "operado": "6",
                        "nenhuma": "1", "nenhum": "1", "ninguem": "1", "nao": "1",
                    },
                },
            ],
        },
    ],
}

# O registro. Um objeto, indexado por flow_id — os dois playbooks apontam para
# ELE, não para cópias dele.
_NATIVE_FLOWS_FAMILIA_HDI_YELUM: Dict[str, Dict[str, Any]] = {
    NATIVE_FLOW_CONDICOES_VEICULO: _FLOW_CONDICOES_VEICULO_V2,
}


HDI_AUTO_WHATSAPP_V1 = _auto_playbook(
    "hdi", "hdi_assistencia_24h",
    ura_steps=[
        {"step": "menu_auto_ou_resid",
         "anchor": r"assist[êe]ncia para seu \*?autom[óo]vel\*? ou \*?resid[êe]ncia|para seu \*?autom[óo]vel\*? ou \*?resid[êe]ncia",
         "reply": "🚗 Automóvel", "notes": "botões com emoji: '🚗 Automóvel' / '🏠 Residência'"},
    ] + [dict(s) for s in _YELUM_FAMILY_STEPS],
    finalize_anchors=list(_YELUM_FAMILY_FINALIZE),
)
HDI_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    "guincho": "Pane ou Defeito", "bateria": "Recarga de bateria",
    "pneu": "Pneu Furado", "chaveiro": "Problema com a chave",
}
HDI_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "Sair"  # 'Digite Sair para encerrar'
# O schema do flow. 📊 E, desde 03/08/2026, o TRANSPORTE também existe:
# `/send/interactiveResponse` foi provada no ar, com o embrulho
# DocumentWithCaption — ver O-FORMULARIO-NATIVO-RESOLVIDO.md.
#
# Por isso o gatilho `r"formulario nativo"` saiu daqui. Ele existia porque "ter o
# schema não é ter o canal" — e era verdade. Mantê-lo agora desviaria para humano
# exatamente o caso que o produto passou a saber resolver sozinho, e o trabalho
# das últimas semanas não renderia nada.
#
# O que protege no lugar dele NÃO é uma regra escrita aqui — é o motor:
# `montar_resposta_de_flow` recusa responder formulário que não conhece, ou com
# campo obrigatório sem valor, e devolve `ok=False`. Aí sim o acionamento pausa,
# com o dossiê e o motivo. **Fail-closed por construção, não por lista.**
HDI_AUTO_WHATSAPP_V1["native_flows"] = _NATIVE_FLOWS_FAMILIA_HDI_YELUM

# --- Yelum (ex-Liberty, grupo HDI): v3 minerado do fluxo REAL COMPLETO de
# 16/03/2026 (conversa "Liberty Fácil Assist" = Yelum rebatizada; 100% bot até o
# protocolo 9415275). Mesmos passos da família HDI + variantes antigas próprias.
YELUM_AUTO_WHATSAPP_V1 = _auto_playbook(
    "yelum", "yelum_assistencia_24h",
    ura_steps=[
        {"step": "menu_auto_ou_resid",
         "anchor": r"assist[êe]ncia para (?:o )?(?:seu|sua) \*?(?:autom[óo]vel|casa)\*? ou \*?resid[êe]ncia\*?|sua \*?casa\*? ou \*?carro\*?",
         "reply": "Automóvel", "notes": "variante antiga usa botões Casa/Carro"},
    ] + [dict(s) for s in _YELUM_FAMILY_STEPS] + [
        {"step": "podemos_confirmar", "anchor": r"podemos confirmar", "reply": "Sim",
         "notes": "confirmação final (modo LIVE)"},
    ],
    finalize_anchors=list(_YELUM_FAMILY_FINALIZE),
)
YELUM_AUTO_WHATSAPP_V1["version"] = 3
YELUM_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    "guincho": "Pane ou Defeito", "bateria": "Recarga de bateria",
    "pneu": "Pneu Furado", "chaveiro": "Problema com a chave",
}
YELUM_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "Sair"  # 'Digite Sair para encerrar'
# O gatilho `r"formulario nativo"` saiu daqui pelo mesmo motivo da HDI: o canal
# passou a existir e foi provado. Quem recusa formulário desconhecido é o motor.
# MESMO objeto do corredor da HDI (mesmo bot, mesmo flow_id). `is`, não `==`.
YELUM_AUTO_WHATSAPP_V1["native_flows"] = _NATIVE_FLOWS_FAMILIA_HDI_YELUM

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
         "notes": "📊 menu real 03/08/2026 (numerado): 1-Guincho (reboque) 2-Bateria 3-Troca de pneu "
                  "4-Chaveiro para o veículo 5-Conserto ou troca de vidro, retrovisor... "
                  "— na Azul vidro é TECLA, e o fluxo segue normal até o protocolo"},
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
        {"step": "ponto_referencia",
         "anchor": r"(?:o local tem|pode me informar) algum \*?ponto de refer[êe]ncia",
         "reply": "{ponto_referencia}",
         "notes": "só a PERGUNTA (o RESUMO também contém 'Ponto de referência:'); se não houver, 'não tem'"},
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
# Mapfre exige nascimento em TODOS os subserviços auto. O `**v` preserva as
# outras chaves do subserviço (outcome, tipo_servico_opcao): reconstruir só com
# `required_slots` apagava em silêncio tudo o mais que fosse declarado.
MAPFRE_AUTO_WHATSAPP_V1["subservices"] = {
    k: {**v, "required_slots": list(v["required_slots"]) + ["titular_nascimento"]}
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
        # VIDROS na Zurich é ITEM DE LISTA e é INFORMATIVO — DESFECHO = encaminha.
        # 📊 URA real 03/08/2026: "Você deseja acionar qual serviço? Acionar
        # seguro / Assistência {VALOR} / Assistência a vidros / Voltar ao menu".
        # Só o corredor de VIDROS responde este menu por rótulo: o rótulo dos
        # outros serviços vem com um VALOR variável da apólice, e adivinhá-lo
        # seria clicar na tecla errada. Para guincho/bateria/pneu/chaveiro este
        # passo não existe e quem decide continua sendo o adaptativo.
        {"step": "menu_acionar_servico_vidros", "anchor": r"deseja acionar qual servi[çc]o",
         "reply": "{servico_texto}", "requires": ["servico_texto"],
         "only_subservices": ["vidros"],
         "notes": "responder o rótulo 'Assistência a vidros' (vem de subservice_menu_map)"},
        # 📊 "*Assistência a vidros*: encontre informações sobre como pedir o
        # reparo ou a troca de vidros, para-brisa, faróis e retrovi[sores]" —
        # a Zurich ORIENTA; não abre chamado neste fluxo.
        {"step": "vidros_orientacao",
         "anchor": (r"assist[êe]ncia a vidros\*?\s*:?\s*encontre informa[çc][õo]es|"
                    r"como pedir o reparo ou a troca de vidros"),
         "reply": "", "noop": True, "referral": True, "outcome": OUTCOME_ENCAMINHA,
         "notes": "não responder à URA: entregar a orientação ao segurado e encerrar"},
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


# ===========================================================================
# VIDROS — ligado em TRÊS seguradoras, e desligado nas outras sete
# ===========================================================================
# 📊 `ura_maps` status='observed', banco de produção, 03/08/2026.
#
#   azul .... TECLA numerada: "*5* - Conserto ou troca de vidro, retrovi[sor]"
#             → desfecho ABRE: segue o fluxo normal até o protocolo.
#   porto ... item de LISTA: "Conserto de vidro (Inclui retrovisor, farol ou
#             lanterna)" → e o fluxo TERMINA num formulário → desfecho ENCAMINHA.
#   zurich .. item de LISTA: "Assistência a vidros" → texto informativo sobre
#             como pedir o reparo → desfecho ENCAMINHA.
#
# 📊 SEM evidência de vidro no menu de assistência: allianz, tokio, mapfre,
# yelum, hdi, alfa. (bradesco também não tem.) Nessas, `vidros` NÃO é declarado:
# `subservice_supported()` devolve False, `missing_slots_for_subservice()`
# devolve ["subservico_invalido"] e o caso vira handoff humano. É de propósito.
# Ligar vidros nas dez "porque o produto sabe falar de vidro" faria o corredor
# apertar uma tecla que não existe na tela daquela seguradora.
_VIDROS_REFERRAL_PORTO = {
    "kind": "formulario",
    "closes_as": "resolvido_por_encaminhamento",
    "link_capture": "tracking_link",  # o link chega numa mensagem sozinha
    "client_message": (
        "A Porto trata vidro, retrovisor, farol e lanterna por FORMULÁRIO de sinistro de vidros — "
        "não é chamado aberto pelo WhatsApp da assistência. Encaminhe ao segurado o link que a "
        "seguradora enviou NESTA conversa (nunca digite um endereço de memória) e repasse o que a "
        "própria URA diz: este acionamento para vidros não afeta a classe de bônus."
    ),
}
_VIDROS_REFERRAL_ZURICH = {
    "kind": "orientacao",
    "closes_as": "resolvido_por_encaminhamento",
    "link_capture": "tracking_link",
    "client_message": (
        "A Zurich responde vidros com ORIENTAÇÃO: onde encontrar como pedir o reparo ou a troca de "
        "vidros, para-brisa, faróis e retrovisores. Repasse ao segurado exatamente o que a seguradora "
        "enviou nesta conversa — sem completar com prazo, valor ou franquia que ela não disse."
    ),
}
_ativar_vidros(AZUL_AUTO_WHATSAPP_V1, menu_value="5", outcome=OUTCOME_ABRE)
_ativar_vidros(PORTO_AUTO_WHATSAPP_V1, menu_value="Conserto de vidro",
               outcome=OUTCOME_ENCAMINHA, referral=_VIDROS_REFERRAL_PORTO)
_ativar_vidros(ZURICH_AUTO_WHATSAPP_V1, menu_value="Assistência a vidros",
               outcome=OUTCOME_ENCAMINHA, referral=_VIDROS_REFERRAL_ZURICH)


# ===========================================================================
# SPEC-063: RESIDENCIAL fora da Allianz — HDI e Porto
# ===========================================================================
# Até 03/08/2026 havia UM corredor residencial (Allianz) e dez de auto. Estes
# dois nascem do que foi OBSERVADO, e só dele: onde a evidência acaba, o passo
# não existe e o motor cai no adaptativo guardado / handoff, como já faz hoje.
#
# Uma escolha explícita: onde o corredor de auto da MESMA seguradora já tinha
# uma âncora de identificação (CPF, menu raiz), ela é REUSADA e marcada nas
# `notes`. É a mesma URA, o mesmo bot e a mesma porta de entrada — reusar não é
# inventar. O que NÃO é reusado é qualquer passo com cara de auto (placa, cor do
# veículo, rodovia, garagem): esses não têm equivalente residencial observado.

_RESID_HUMAN_PHASE_GUIDANCE = (
    "Voce conduz, EM NOME DA CORRETORA, um acionamento de assistencia RESIDENCIAL no WhatsApp da "
    "seguradora. Pode ser a URA (menu numerado ou botoes) ou um atendente humano. Responda menus "
    "escolhendo a opcao coerente com o subservico/dados do caso; responda pedidos de dado com o valor "
    "exato do caso (CPF, endereco da apolice, telefone). O endereco e o DA APOLICE — nao invente, e "
    "nao use endereco de outro caso. Se a seguradora for CONFIRMAR/ABRIR o servico, NAO confirme: o "
    "passo final exige aprovacao da corretora. Se a seguradora disser que a apolice nao tem cobertura "
    "residencial ou que acabaram as utilizacoes, NAO insista: registre e devolva ao humano. Use "
    "SOMENTE dados do caso. Se nao der pra deduzir, responda exatamente: NAO_SEI."
)

# Resumo estruturado ao ESPECIALISTA humano da assistência (residencial).
# Só usa chaves de `_optional_keys()` — chave fora dali derruba o template
# inteiro para o texto genérico de auto.
_RESID_OPENING_TEMPLATE = (
    "Ola, aqui e a corretora. Preciso acionar {subservice_label} para a residencia do nosso segurado.\n"
    "Titular: {titular_nome} (CPF {titular_cpf})\n"
    "Endereco: o da apolice, numero {endereco_numero}\n"
    "Problema: {problema_descricao}\n"
    "Telefone de contato: {telefone_contato}\n"
    "Periodo preferido: {periodo_preferido}"
)

_RESID_HANDOFF_TRIGGERS = [
    r"sinistro", r"n[ãa]o localizamos", r"cpf.*inv[áa]lido", r"n[ãa]o foi poss[íi]vel",
    r"sem cobertura", r"n[ãa]o (?:tem|possui) cobertura",
]

# Os dados que cada TRABALHO exige — não os que cada seguradora exige.
# O eletricista pergunta de fumaça, o encanador pergunta do registro e o
# eletrodoméstico pergunta da marca, seja na Allianz ou na HDI. Guardrail que
# existe só num corredor não é guardrail: é coincidência.
_RESID_SLOTS_BASE = ["titular_cpf", "telefone_contato", "problema_descricao"]
_RESID_SLOTS_POR_TRABALHO = {
    "encanador": ["vazamento_local", "agua_escorrendo", "risco_confirmado_registro_fechado"],
    "eletricista": ["risco_confirmado_sem_fumaca"],
    "eletrodomesticos": ["aparelho_marca_modelo", "aparelho_idade"],
    "chaveiro": [],
    "desentupimento": [],
}


def _resid_slots(trabalho: str) -> List[str]:
    return list(_RESID_SLOTS_BASE) + list(_RESID_SLOTS_POR_TRABALHO.get(trabalho) or [])


# --- HDI residencial (📊 o corredor residencial mais bem observado do acervo) ---
# Mesmo bot white-label "Assistência 24 horas" do corredor de auto da HDI/Yelum:
# botões por rótulo, timeout de 12 min, protocolo no mesmo formato.
#
# NÃO há passo de endereço aqui, e isso é evidência, não esquecimento: a URA
# identifica a apólice pelo CPF e trabalha com o endereço dela. Se aparecer um
# passo pedindo endereço, ele vira `pending` e o humano assume — melhor que um
# slot obrigatório que ninguém usa, cobrado do cliente por precaução.
HDI_RESIDENCIAL_WHATSAPP_V1: Dict[str, Any] = {
    "playbook_id": "hdi-residencial-whatsapp",
    "version": 1,
    "insurer_key": "hdi",
    "line_kind": "residencial",
    "channel": "whatsapp",
    "insurer_contact_ref": "hdi_assistencia_24h",
    "description": ("Assistência 24h RESIDENCIAL HDI via WhatsApp "
                    "(encanador/desentupimento/eletricista/chaveiro/eletrodoméstico)."),
    "ura_steps": [
        {"step": "identificacao_dado",
         "anchor": (r"informe \*?apenas um dos dados|informe \*?um dos dados abaixo|"
                    r"informe somente o \*?cpf ou cnpj\*? do t[íi]tular"),
         "reply": "{titular_cpf}", "requires": ["titular_cpf"],
         "notes": "âncora REUSADA do corredor de auto da MESMA URA — a identificação é a mesma "
                  "porta para os dois ramos"},
        {"step": "desambiguacao_veiculo_ou_residencial",
         "anchor": r"identifiquei em seu cadastro a placa",
         "reply": "Residencial",
         "notes": "📊 'Identifiquei em seu cadastro a placa {PLACA}. Deseja continuar com o "
                  "atendimento para o veículo ou atendimento residencial? Botão 1: Automóvel "
                  "Botão 2: Residencial'. O corredor de AUTO responde 'Automóvel' nesta MESMA "
                  "tela — é o passo que separa os dois ramos, e errar aqui atende o carro de "
                  "quem pediu encanador"},
        {"step": "menu_servico_residencial",
         "anchor": r"qual [ée] o servi[çc]o que voc[êe] precisa solicitar",
         "reply": "{tipo_servico_opcao}", "requires": ["tipo_servico_opcao"],
         "notes": "📊 lista real: Encanador (conserto de vazamentos como torneiras, sifões, etc) / "
                  "Desentupimento (desentupimento residencial) / Eletricista / Chaveiro / "
                  "Eletrodoméstico — responder o RÓTULO, que vem do subserviço"},
        {"step": "servico_ja_aberto",
         "anchor": r"localizamos o servi[çc]o de .{0,80}?deseja acompanhar",
         "reply": "Novo serviço",
         "notes": "📊 'Para esse CPF localizamos o serviço de *ENCANADOR*. Deseja acompanhar? "
                  "Botão 1: Acompanhar Botão 2: Novo serviço Botão 3: Voltar'. O corredor abre o "
                  "que o cliente pediu HOJE. Acompanhar chamado antigo é outro trabalho e quem "
                  "decide é o atendente"},
        {"step": "utilizacoes_restantes",
         "anchor": r"(?:tem somente|possui)\s+\d+\s+utiliza[çc][õo]es",
         "reply": "", "noop": True,
         "notes": "📊 'Segurada tem somente 2 utilizações de encanador nessa apólice' — informativo "
                  "sobre o LIMITE da apólice: registrar no dossiê e seguir, nunca responder"},
    ],
    "subservices": {
        "encanador": {"tipo_servico_opcao": "Encanador", "required_slots": _resid_slots("encanador")},
        "desentupimento": {"tipo_servico_opcao": "Desentupimento", "required_slots": _resid_slots("desentupimento")},
        "eletricista": {"tipo_servico_opcao": "Eletricista", "required_slots": _resid_slots("eletricista")},
        "chaveiro": {"tipo_servico_opcao": "Chaveiro", "required_slots": _resid_slots("chaveiro")},
        "eletrodomesticos": {"tipo_servico_opcao": "Eletrodoméstico", "required_slots": _resid_slots("eletrodomesticos")},
    },
    # O rótulo do menu vai em `tipo_servico_opcao` (e NÃO em `subservice_menu_map`)
    # porque é essa a chave que o motor injeta em linha residencial. Declarar nas
    # duas seria manter dois lugares dizendo a mesma coisa, para divergirem depois.
    "subservice_labels": {
        "encanador": "encanador", "desentupimento": "desentupimento",
        "eletricista": "eletricista", "chaveiro": "chaveiro",
        "eletrodomesticos": "reparo de eletrodomestico",
    },
    "opening_template": _RESID_OPENING_TEMPLATE,
    "human_phase_guidance": _RESID_HUMAN_PHASE_GUIDANCE,
    # Mesmo bot do corredor de auto da HDI → mesmo formato de protocolo/ETA.
    # (o prefixo `_AUTO_` do nome é de onde a âncora foi minerada, não do ramo.)
    "capture_anchors": dict(_AUTO_CAPTURE_ANCHORS),
    # Sem regras fixas ao cliente observadas nesta URA. A do maior de 18 anos e a
    # da senha de acesso são da Allianz — copiá-las para cá seria inventar.
    "client_instructions": [],
    "handoff_triggers": _RESID_HANDOFF_TRIGGERS + [
        # 📊 "Ela não possui mais utilizações de encanador": limite ESGOTADO.
        # Não há acionamento possível — insistir só queima o tempo do segurado.
        r"n[ãa]o possui mais utiliza[çc][õo]es",
        # 🔴 AQUI o gatilho FICA — e é uma diferença deliberada em relação ao
        # corredor de auto da mesma seguradora, que o perdeu em 03/08/2026.
        #
        # O canal de resposta existe e foi provado. Mas este playbook **não
        # declara `native_flows`**: nenhum formulário do residencial foi
        # capturado ainda. Sem schema não há o que responder, e a única saída
        # honesta é pausar com o dossiê.
        #
        # Quando um formulário residencial for observado e virar schema, este
        # gatilho sai — e não antes.
        r"formulario nativo",
    ],
    "finalize_anchors": [
        # ponto de não-retorno da família HDI/Yelum — o "para" é OPCIONAL: 📊 a
        # tela residencial da HDI diz "Você precisa do atendimento agora ou
        # prefere agendar" (sessão 26c0546f, 02/06/2026, encanador) e a âncora
        # literal antiga não disparava justamente aqui.
        _HDI_FAMILY_AGORA_OU_AGENDAR,
        r"podemos confirmar", r"posso confirmar", r"deseja confirmar",
    ],
    "finalize_abort_reply": "Sair",  # 'Digite Sair para encerrar'
    "unknown_step_policy": "pause_and_handoff",  # corredor novo: pausa antes de improvisar
    "coverage_guardrails": [
        "📊 'Ela não possui mais utilizações de encanador' — a apólice residencial tem LIMITE de "
        "utilizações POR SUBSERVIÇO. Esgotado, não existe acionamento: é handoff com o motivo "
        "escrito, e a corretora oferece o serviço particular se o cliente quiser.",
        "📊 'Segurada tem somente 2 utilizações de encanador nessa apólice' — quando a URA disser "
        "quantas restam, isso vai ao dossiê: é o dado que evita gastar a última utilização num "
        "problema pequeno.",
    ],
}

# --- PORTO residencial (a rota existe; os subserviços são genéricos) --------------
# 📊 A Porto expõe a ROTA ("Serviços para residência") e descreve o que ela cobre
# ("Assistência de elétrica, hidráulica e conserto de eletrodomésticos"), mas
# NENHUM submenu de escolha do subserviço foi observado. Por isso este corredor
# NÃO declara rótulo de menu por subserviço: ele chega até a rota residencial e,
# do submenu em diante, quem conduz é o adaptativo guardado / o humano.
# Declarar um rótulo aqui seria adivinhar a tecla.
PORTO_RESIDENCIAL_WHATSAPP_V1: Dict[str, Any] = {
    "playbook_id": "porto-residencial-whatsapp",
    "version": 1,
    "insurer_key": "porto",
    "line_kind": "residencial",
    "channel": "whatsapp",
    "insurer_contact_ref": "porto_assistencia_24h",
    "description": "Assistência RESIDENCIAL Porto via WhatsApp (elétrica/hidráulica/eletrodomésticos).",
    "ura_steps": [
        {"step": "menu_raiz", "anchor": r"escolha a op[çc][ãa]o desejada",
         "reply": "Informar outro CPF/CNPJ",
         "notes": "âncora REUSADA do corredor de auto da Porto: a URA lembra o CPF do ÚLTIMO "
                  "atendimento (o WhatsApp é da corretora e atende N clientes) — re-identificar "
                  "SEMPRE. Sem `reply_repeat`: o rótulo residencial da 2ª volta não foi observado, "
                  "e chutar aqui manda o caso para a rota errada"},
        {"step": "pedir_cpf", "anchor": r"(?:informe|digite) o (?:seu )?\*?cpf ou cnpj\*?",
         "reply": "{titular_cpf}", "requires": ["titular_cpf"],
         "notes": "âncora REUSADA do corredor de auto da Porto (mesma porta de identificação)"},
        {"step": "menu_tipo_atendimento",
         "anchor": r"qual tipo de atendimento voc[êe] precisa",
         "reply": "Serviços para residência",
         "notes": "📊 lista real 03/08/2026: 'Serviços para veículo / Serviços para residência / "
                  "Consultar apólice / Voltar', com a linha residencial descrita como "
                  "'Assistência de elétrica, hidráulica e conserto de elet[rodomésticos]'"},
        {"step": "menu_como_ajudar_resid",
         "anchor": r"como eu posso te ajudar\?.*servi[çc]os para resid[êe]ncia",
         "reply": "Serviços para residência",
         "notes": "variante do MESMO menu observada no corredor de auto ('como eu posso te "
                  "ajudar?'), respondida aqui pelo rótulo residencial"},
        {"step": "aguarde",
         "anchor": (r"aguarde um momento|que bom ter voc[êe] de volta|aguarde enquanto solicito|"
                    r"falta pouco para finalizarmos"),
         "reply": "", "noop": True,
         "notes": "noop REUSADO do corredor de auto: mensagens de espera não se respondem"},
    ],
    "subservices": {
        "eletricista": {"required_slots": _resid_slots("eletricista")},
        "encanador": {"required_slots": _resid_slots("encanador")},
        "eletrodomesticos": {"required_slots": _resid_slots("eletrodomesticos")},
    },
    # As palavras da Porto, para o resumo ao analista humano. As CHAVES são as
    # canônicas do produto (eletricista/encanador/eletrodomesticos): a Porto
    # chamar de "elétrica" e "hidráulica" não pode virar um segundo vocabulário
    # — `canonical_subservice` traduz 'eletrica'/'hidraulica' para cá.
    "subservice_labels": {
        "eletricista": "assistencia de eletrica",
        "encanador": "assistencia de hidraulica",
        "eletrodomesticos": "conserto de eletrodomestico",
    },
    "opening_template": _RESID_OPENING_TEMPLATE,
    "human_phase_guidance": _RESID_HUMAN_PHASE_GUIDANCE,
    "capture_anchors": dict(_AUTO_CAPTURE_ANCHORS),
    "client_instructions": [],
    "handoff_triggers": _RESID_HANDOFF_TRIGGERS + [
        # 📊 "Parece que as apólices no CNPJ informado não tem cobertura para
        # serviços residenciais. Nestes casos é possível realizar a assistência
        # de forma particular." Serviço PARTICULAR não é acionamento de apólice:
        # é conversa comercial com o cliente, e ela é de gente.
        r"n[ãa]o tem cobertura para servi[çc]os residenciais",
        r"assist[êe]ncia de forma particular",
    ],
    "finalize_anchors": [
        r"como voc[êe] quer prosseguir", r"posso confirmar sua solicita[çc][ãa]o",
        r"posso confirmar", r"deseja confirmar",
    ],
    "finalize_abort_reply": "Sair e não agendar",
    "unknown_step_policy": "pause_and_handoff",
    "coverage_guardrails": [
        "📊 'Parece que as apólices no CNPJ informado não tem cobertura para serviços residenciais. "
        "Nestes casos é possível realizar a assistência de forma particular.' — apólice sem cobertura "
        "residencial NÃO vira acionamento. Vira handoff, e a oferta de serviço particular é decisão "
        "comercial da corretora com o cliente.",
        "📊 Nenhum submenu de subserviço residencial foi observado na Porto: do 'Serviços para "
        "residência' em diante o corredor não tem tecla mapeada.",
    ],
}


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
        HDI_RESIDENCIAL_WHATSAPP_V1,
        PORTO_RESIDENCIAL_WHATSAPP_V1,
    )
}


# ALFAIATE (SPEC-034 Onda 4): overlays noop auto-aplicados em runtime — avisos
# NOVOS da URA passam a ser ignorados sem deploy. Cache em memória, populado
# pela task periódica (refresh_overlay_cache); vazio = comportamento original.
_OVERLAY_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def set_overlay_cache(data: Dict[str, List[Dict[str, Any]]]) -> None:
    global _OVERLAY_CACHE
    _OVERLAY_CACHE = dict(data or {})


def get_playbook(playbook_ref: str) -> Optional[Dict[str, Any]]:
    ref = str(playbook_ref or "").strip()
    base = _PLAYBOOKS.get(ref)
    overlays = _OVERLAY_CACHE.get(ref) or []
    if not base or not overlays:
        return base
    # Cópia rasa com ura_steps NOVO — nunca mutar o playbook-fonte (duplicaria
    # overlays a cada chamada).
    merged = dict(base)
    extra = [
        {"step": f"overlay_noop_{i}", "anchor": str(o.get("anchor") or ""),
         "reply": "", "noop": True, "notes": str(o.get("note") or "Alfaiate")}
        for i, o in enumerate(overlays) if o.get("anchor")
    ]
    merged["ura_steps"] = list(base.get("ura_steps") or []) + extra
    return merged


def list_playbooks() -> List[str]:
    return sorted(_PLAYBOOKS.keys())


# ---------------------------------------------------------------------------
# Seleção de playbook e contato por seguradora (SPEC-031)
# ---------------------------------------------------------------------------

# Sinônimos de seguradora → chave canônica (a InfoCap pode devolver variações).
# Azul é do grupo Porto MAS tem WhatsApp e URA próprios → corredor próprio.
_INSURER_ALIASES = {
    "allianz": "allianz", "allianz seguros": "allianz",
    "porto": "porto", "porto seguro": "porto",
    "itau": "itau", "itau seguros": "itau",
    "azul": "azul", "azul seguros": "azul",
    "hdi": "hdi", "hdi seguros": "hdi",
    "yelum": "yelum", "liberty": "yelum", "liberty seguros": "yelum", "libe": "yelum",
    "tokio": "tokio", "tokio marine": "tokio", "tokyo": "tokio",
    "alfa": "alfa", "alfa seguradora": "alfa", "alfa seguros": "alfa",
    "bradesco": "bradesco", "bradesco seguros": "bradesco", "bradesco auto/re": "bradesco",
    "mapfre": "mapfre", "mapfre seguros": "mapfre",
    "zurich": "zurich", "zurich seguros": "zurich", "zurich santander": "zurich",
    # Vistas nas conversas reais da Resulta em 29/07/2026, durante a destilação
    # do histórico. Sem elas, "sompo seguros" e "seguros sura" viravam chaves
    # diferentes de "sompo" e "sura", e o filtro por seguradora perdia carta.
    "sompo": "sompo", "sompo seguros": "sompo",
    "sura": "sura", "seguros sura": "sura",
    "metlife": "metlife", "met life": "metlife",
    "axa": "axa", "axa seguros": "axa",
    "youse": "youse",
    "suhai": "suhai", "suhai seguradora": "suhai",
    "mitsui": "mitsui", "msig": "mitsui", "mitsui sumitomo": "mitsui",
    "akad": "akad", "akad seguros": "akad",
    "caixa": "caixa", "caixa seguradora": "caixa", "caixa seguros": "caixa",
}


# QUEM OPERA A ASSISTÊNCIA DE QUEM.
#
# Isto NÃO é grafia alternativa — é fato de negócio: a carteira de auto do Itaú
# é operada pela infraestrutura da Porto, e o corredor de acionamento tem de
# apontar para lá. `test_spec031_auto_dispatch` cobre isso.
#
# Mas o Itaú vende vida e residencial em nome próprio, e um subagente
# destilando o lote 043 mostrou o efeito de misturar os dois usos: "uma regra
# específica do Itaú seria arquivada como Porto" — a mesma família do erro que
# atribuiu à Yelum o prazo de PIX da Youse.
#
# Uma tabela, duas leituras. ACIONAR pergunta "por onde eu ligo"; ARQUIVAR
# pergunta "de quem é esta regra". São perguntas diferentes e a resposta certa
# é diferente.
_OPERADO_POR = {"itau": "porto"}

# E a operação é POR CARTEIRA. 📊 O que a evidência diz é que a carteira de AUTO
# do Itaú roda na infraestrutura da Porto — nada foi observado sobre residencial.
# Enquanto só existia corredor residencial da Allianz, a distinção não aparecia.
# Com o corredor residencial da PORTO no ar, aplicar `_OPERADO_POR` a residencial
# mandaria uma apólice residencial do Itaú para o roteiro da Porto — exatamente
# o erro que a tabela acima descreve, com o sinal trocado.
_OPERADO_POR_LINHAS = {"itau": ("auto",)}


def normalize_insurer_key(insurer: str, para: str = "corredor") -> str:
    """Chave canônica da seguradora.

    `para="corredor"` (padrão): por onde se aciona. Aplica `_OPERADO_POR`.
    `para="conhecimento"`: de quem é a regra. NÃO aplica — uma carta do Itaú
    fica sob Itaú, senão o agente responde regra da Porto a segurado do Itaú.
    """
    # `_` e `-` viram espaço antes de comparar: "tokio_marine" chega assim de
    # importação antiga, e para o regex o sublinhado é letra — `\btokio\b` não
    # casaria, e a chave sobreviveria separada da `tokio` de todas as outras.
    raw = re.sub(r"[^a-z0-9]+", " ", _norm(insurer)).strip()
    # PALAVRA INTEIRA, não pedaço de palavra.
    #
    # Isto era `if alias in raw`. Com "axa" na lista, "caixa seguradora" virava
    # `axa` — duas seguradoras diferentes fundidas numa chave só, e o agente
    # respondendo regra da AXA para segurado da Caixa. Substring é aceitável
    # enquanto ninguém acrescenta um alias curto; o dia em que alguém
    # acrescenta, o erro é silencioso e sai errado para o cliente.
    def _final(chave: str) -> str:
        return _OPERADO_POR.get(chave, chave) if para == "corredor" else chave

    if raw in _INSURER_ALIASES:
        return _final(_INSURER_ALIASES[raw])
    for alias, key in _INSURER_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", raw):
            return _final(key)
    return _final(raw.split()[0]) if raw else ""


def resolve_playbook_ref(insurer: str, line_kind: str = "auto", channel: str = "whatsapp") -> Optional[str]:
    """Resolve o playbook_ref pela seguradora + linha. None se não houver."""
    line = str(line_kind or "auto").strip().lower()
    line = "residencial" if line in ("residencial", "residencia", "resid", "casa", "home") else line
    # Quem opera a assistência de quem vale POR CARTEIRA (ver `_OPERADO_POR_LINHAS`).
    key = normalize_insurer_key(insurer, para="conhecimento")
    operador = _OPERADO_POR.get(key)
    if operador and line in _OPERADO_POR_LINHAS.get(key, ()):
        key = operador
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
    # Fallback: Registro de Seguradoras (SPEC-034 — números da planilha,
    # validados pela corretora). O env continua mandando quando definido.
    try:
        from app.services.insurer_registry import registry_whatsapp

        return "".join(ch for ch in registry_whatsapp(normalize_insurer_key(insurer)) if ch.isdigit())
    except Exception:  # noqa: BLE001
        return ""


def auto_subservice_menu_value(playbook: Dict[str, Any], subservice: str) -> str:
    """Opção/rótulo do menu da seguradora para o subserviço auto (guincho→'3' ou 'Guincho').

    Vazio quando a seguradora não tem menu OBSERVADO para aquele subserviço —
    e vazio significa handoff, nunca 'escolhe a primeira opção'."""
    sub = canonical_subservice(subservice)
    return str((playbook.get("subservice_menu_map") or {}).get(sub) or "")


def subservice_supported(playbook: Dict[str, Any], subservice: str) -> bool:
    """Esta seguradora tem corredor observado para este subserviço?

    False = não há evidência (📊 vidros em allianz/tokio/mapfre/yelum/hdi/alfa/
    bradesco, por exemplo) → o caso vira handoff humano com o motivo escrito.
    Nunca é convite para improvisar um menu."""
    subs = playbook.get("subservices") or {}
    return canonical_subservice(subservice) in subs


def subservice_outcome(playbook: Dict[str, Any], subservice: str) -> str:
    """Como este corredor TERMINA: `abre` (vai até o protocolo) ou `encaminha`
    (a seguradora entrega formulário/orientação e o caso encerra resolvido).

    Subserviço inexistente devolve "" — não existe desfecho para trabalho que
    esta seguradora não faz por este canal."""
    sub = (playbook.get("subservices") or {}).get(canonical_subservice(subservice))
    if sub is None:
        return ""
    return str(sub.get("outcome") or OUTCOME_ABRE)


def subservice_referral(playbook: Dict[str, Any], subservice: str) -> Dict[str, Any]:
    """O encaminhamento declarado do subserviço (formulário/orientação), ou {}.

    Traz `client_message` (o que dizer ao segurado, sem inventar link nem prazo),
    `closes_as` e onde o link cai (`link_capture`)."""
    sub = (playbook.get("subservices") or {}).get(canonical_subservice(subservice)) or {}
    return dict(sub.get("referral") or {})


def detect_referral_step(playbook: Dict[str, Any], insurer_message: str) -> Optional[Dict[str, Any]]:
    """O passo de ENCAMINHAMENTO que casou com a mensagem da seguradora.

    É o espelho de `detect_finalize_anchor`, do outro lado do fluxo: em vez de
    'a seguradora vai abrir o serviço', diz 'a seguradora não vai abrir serviço
    nenhum aqui — ela entregou o caminho'. Quem chama decide encerrar o caso
    como resolvido-por-encaminhamento e repassar o `client_message` do
    subserviço ao segurado."""
    text = _norm(insurer_message)
    for step in playbook.get("ura_steps") or []:
        if not step.get("referral"):
            continue
        if re.search(step.get("anchor") or r"$^", text, re.IGNORECASE | re.DOTALL):
            return step
    return None


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
        "endereco_numero", "periodo_preferido",
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
    sub = canonical_subservice(subservice)  # 'pane seca' entra pelo caminho do guincho
    for step in playbook.get("ura_steps") or []:
        only = step.get("only_subservices")
        if only and sub not in [str(x).lower() for x in only]:
            continue
        if re.search(step.get("anchor") or r"$^", text, re.IGNORECASE | re.DOTALL):
            return step
    return None


_UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}
_STREET_RE = re.compile(
    r"\b(?:rua|r\.|av\.?|avenida|rod\.?|rodovia|estrada|travessa|tv\.?|alameda|al\.?|"
    r"servid[ãa]o|br-?\s?\d+|sc-?\s?\d+|pra[çc]a|largo|beco|via|linha)\b", re.IGNORECASE)


def parse_address_br(text: str) -> Dict[str, str]:
    """Heurística de endereço BR em texto livre → componentes para URAs que pedem
    rua/número/bairro/cidade/UF separados (Yelum/HDI/Allianz destino).

    Aceita formatos reais das conversas: "Rua B, 50, Sao Jose SC",
    "R. Abelardo Luz, 342 - Balneario, Florianópolis - SC, 88075-542",
    "Av Santa Tecla 2400, Bagé, RS". Campo não deduzido fica FORA do dict
    (o passo cai no cérebro adaptativo — nunca chuta)."""
    out: Dict[str, str] = {}
    raw = str(text or "").strip()
    if not raw:
        return out
    m = re.search(r"\b(\d{5})-?(\d{3})\b", raw)
    if m:
        out["cep"] = f"{m.group(1)}-{m.group(2)}"
        raw = raw.replace(m.group(0), " ")
    parts = [p.strip(" .") for p in re.split(r"[,\-–]| - ", raw) if p.strip(" .-")]
    if not parts:
        return out
    # UF: token final de 2 letras válido (pode vir grudado na cidade: "Sao Jose SC").
    tail_tokens = parts[-1].split()
    if tail_tokens and tail_tokens[-1].upper() in _UFS:
        out["uf"] = tail_tokens[-1].upper()
        rest = " ".join(tail_tokens[:-1]).strip()
        if rest:
            parts[-1] = rest
        else:
            parts = parts[:-1]
    # Rua: primeiro segmento com cara de logradouro (ou o primeiro segmento).
    street_idx = next((i for i, p in enumerate(parts) if _STREET_RE.search(p)), 0)
    street = parts[street_idx]
    # Número embutido no segmento da rua ("Av Santa Tecla 2400" / "km 205").
    m = re.search(r"\s(?:n[ºo°.]?\s*)?(\d{1,5})$", street) or re.search(r"\bkm\s*(\d{1,4})\b", street, re.IGNORECASE)
    if m:
        out["numero"] = m.group(1)
        street = street[: m.start()].strip(" ,")
    out["rua"] = street
    rest = parts[street_idx + 1:]
    # Número como segmento próprio ("Rua B, 50, ...").
    if "numero" not in out and rest and re.fullmatch(r"(?:n[ºo°.]?\s*)?\d{1,5}(?:\s*km)?", rest[0], re.IGNORECASE):
        out["numero"] = re.sub(r"\D", "", rest[0])
        rest = rest[1:]
    rest = [p for p in rest if p]
    if len(rest) >= 2:
        out["bairro"] = rest[0]
        out["cidade"] = rest[-1]
    elif len(rest) == 1:
        out["cidade"] = rest[0]
    return out


def inject_address_slots(slots: Dict[str, Any]) -> Dict[str, Any]:
    """Deriva slots de endereço decompostos a partir de local_atual/local_destino.
    Só preenche o que a heurística deduziu (faltante → adaptativo assume)."""
    for src, prefix in (("local_atual", "local"), ("local_destino", "destino")):
        parsed = parse_address_br(str(slots.get(src) or ""))
        for key, val in parsed.items():
            slots.setdefault(f"{prefix}_{key}", val)
    # Aliases usados pelos passos da Allianz (logradouro = rua).
    if slots.get("destino_rua"):
        slots.setdefault("destino_logradouro", slots["destino_rua"])
    return slots


def pick_option_by_plate(insurer_message: str, placa: str) -> str:
    """Escolhe a opção do menu de veículos pela PLACA MASCARADA da URA.
    Ex.: '1 - 2500, placa JD#-###2 / 2 - HILUX SW4, placa JC#-###9' com placa
    do caso JCL9A59 → '2' (prefixo JC e final 9 casam). '' = sem match seguro."""
    case = re.sub(r"[^A-Z0-9]", "", str(placa or "").upper())
    if not case:
        return ""
    matches = []
    for opt, masked in re.findall(r"(\d+)\s*-\s*[^\n]*?placa\s+([A-Z0-9#\-]+)", str(insurer_message), re.IGNORECASE):
        m = re.sub(r"[^A-Z0-9#]", "", masked.upper())
        if not m or len(m) != len(case):
            # comprimento diferente ainda pode casar se só houver # de padding;
            # sem garantia, pula (nunca chuta veículo).
            if len(m) != len(case):
                continue
        ok = all(mc == "#" or mc == cc for mc, cc in zip(m, case))
        if ok:
            matches.append(opt)
    return matches[0] if len(matches) == 1 else ""


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


# ---------------------------------------------------------------------------
# FORMULÁRIO NATIVO: montar a resposta por código
# ---------------------------------------------------------------------------
# `render_reply` responde uma tela de texto. Isto responde uma tela de APP: em
# vez de uma string, um objeto com o id de cada opção — o `paramsJSON` que o
# WhatsApp Flow espera de volta.
#
# É PURO: entra schema + slots, sai dicionário. Sem rede, sem banco, sem hora.
# Dá para provar offline, e é por isso que o freio abaixo é confiável.


def native_flow(playbook: Dict[str, Any], flow_id: str) -> Optional[Dict[str, Any]]:
    """O schema do formulário nativo daquele `flow_id`, ou None.

    Indexado por `flow_id` porque é o que a seguradora manda (o parser de
    interativas já o entrega em `interactive.flow.flow_id`) — e porque duas
    seguradoras da mesma família apontam para o MESMO registro."""
    return (playbook.get("native_flows") or {}).get(str(flow_id or "").strip()) or None


def detect_native_flow(playbook: Dict[str, Any], insurer_message: str) -> Optional[Dict[str, Any]]:
    """O flow cuja mensagem de ABERTURA casa com a mensagem da seguradora.

    Serve ao caso em que o `flow_id` não chegou (mensagem só com o corpo): a
    frase que abre o formulário é estável e está guardada no schema. Sem
    `prompt_anchor` declarado, o flow não é adivinhado."""
    text = _norm(insurer_message)
    for flow in (playbook.get("native_flows") or {}).values():
        anchor = flow.get("prompt_anchor")
        if anchor and re.search(anchor, text, re.IGNORECASE | re.DOTALL):
            return flow
    return None


def _flow_components(flow_schema: Dict[str, Any]):
    for screen in flow_schema.get("screens") or []:
        for comp in screen.get("components") or []:
            if comp.get("name"):
                yield screen, comp


def _flow_vazio(valor: Any) -> bool:
    """Vazio é ausência de resposta. `False` é uma RESPOSTA."""
    if isinstance(valor, bool):
        return False
    if valor is None:
        return True
    if isinstance(valor, (list, tuple, set)):
        return not [v for v in valor if not _flow_vazio(v)]
    return not str(valor).strip()


def _flow_visivel(comp: Dict[str, Any], parcial: Dict[str, Any]) -> tuple:
    """(visível?, é condicional?) do componente, dadas as respostas já montadas.

    Três casos, e o do meio é o que importa:
      - sem `visible_if`            → visível, direto;
      - `${form.X} == 'v'`          → dá para avaliar: X já está montado, ou não;
      - `${data.X}`, ou X ainda sem resposta → INDETERMINADO.

    Indeterminado conta como VISÍVEL. É de graça: se X não foi respondido, X já
    está em `missing` e o caso já está travado — incluir o dependente só entrega
    a pergunta inteira de uma vez, em vez de devolvê-la de novo na rodada
    seguinte. Tratar como invisível é que seria caro: omitiria, calado, um campo
    que o formulário talvez esteja exigindo."""
    cond = comp.get("visible_if")
    if not cond:
        return True, False
    if cond.get("kind") == "form":
        campo = str(cond.get("field") or "")
        if campo not in parcial:
            return True, True  # indeterminado
        return str(parcial.get(campo)) == str(cond.get("equals")), False
    return True, True  # ${data.*}: só o servidor da seguradora sabe


def _resolver_opcao_de_flow(comp: Dict[str, Any], bruto: Any) -> Optional[str]:
    """id da opção para o valor do caso. `None` = NÃO reconhecido — e não
    reconhecido nunca vira o padrão (ver `montar_resposta_de_flow`)."""
    if isinstance(bruto, bool):
        bruto = "sim" if bruto else "nao"
    raw = str(bruto).strip()
    if not raw:
        return None
    options = comp.get("options") or []
    for o in options:  # 1) o caso já fala em id
        if raw == str(o.get("id")):
            return str(o.get("id"))
    token = _norm(raw).strip()
    for o in options:  # 2) título exato — opção SEM título não casa com nada
        titulo = _norm(o.get("title") or "").strip()
        if titulo and token == titulo:
            return str(o.get("id"))
    alias = (comp.get("aliases") or {}).get(token)  # 3) apelido declarado
    if alias:
        return str(alias)
    if len(token) >= 4:  # 4) contido em UM título só (dois = ambíguo = None)
        hits = [str(o.get("id")) for o in options
                if _norm(o.get("title") or "").strip() and token in _norm(o.get("title") or "")]
        if len(hits) == 1:
            return hits[0]
    return None


def montar_resposta_de_flow(flow_schema: Dict[str, Any], slots: Dict[str, Any]) -> Dict[str, Any]:
    """Monta o `paramsJSON` de resposta do formulário nativo a partir dos slots.

    Devolve::

        {"ok": bool, "flow_id": str, "flow_name": str,
         "params": dict | None,        # None quando ok=False — NUNCA parcial
         "missing": [nome_do_campo],   # mesma forma de `render_reply`
         "missing_detail": [{campo, pergunta, motivo, valor_recebido, opcoes,
                             condicional}],
         "defaults_used": [nome_do_campo]}

    TRÊS REGRAS, e as três existem porque formulário meio preenchido é pior que
    formulário nenhum — o primeiro despacha o equipamento errado, o segundo
    chama um humano:

    1. **Todo campo `required` visível precisa de valor.** Faltando um,
       `ok=False` e `params=None`. Não existe resposta parcial.
    2. **Padrão só cobre AUSÊNCIA.** Se o slot tem valor e ele não casa com
       nenhuma opção, isso é `valor_nao_reconhecido` — vira `missing`, não vira
       o padrão. É o que impede um caso que diz "gestante" (📊 opção cujo título
       veio VAZIO na captura) de ser silenciosamente rebaixado para "Nenhuma das
       anteriores".
    3. **Só se responde o que a tela mostra.** Campo cuja condição de
       visibilidade é FALSA não entra na resposta nem na lista de faltantes.

    O `flow_token` NÃO sai daqui: ele é da sessão, muda a cada conversa, e quem
    o injeta é o transporte na hora do envio. Manter a função pura é o que
    permite provar tudo isto offline."""
    slots = slots or {}
    params: Dict[str, Any] = {}
    missing: List[str] = []
    detail: List[Dict[str, Any]] = []
    defaults_used: List[str] = []

    def _falta(comp: Dict[str, Any], motivo: str, valor: Any = None, condicional: bool = False) -> None:
        missing.append(str(comp.get("name")))
        detail.append({
            "campo": str(comp.get("name")),
            "pergunta": str(comp.get("label") or ""),
            "motivo": motivo,
            "valor_recebido": valor,
            "condicional": condicional,
            "opcoes": [{"id": str(o.get("id")), "titulo": str(o.get("title") or "")}
                       for o in comp.get("options") or []],
        })

    for _screen, comp in _flow_components(flow_schema):
        nome = str(comp.get("name"))
        visivel, condicional = _flow_visivel(comp, params)
        if not visivel:
            continue

        # O caso pode falar o nome do CAMPO (quem já conhece o flow) ou o nome do
        # SLOT (o vocabulário do corredor). Os dois valem; o campo tem precedência.
        bruto = slots.get(nome)
        if _flow_vazio(bruto):
            bruto = slots.get(str(comp.get("slot") or ""))

        if _flow_vazio(bruto):
            padrao = comp.get("default")
            if padrao is not None:
                params[nome] = list(padrao) if isinstance(padrao, (list, tuple)) else padrao
                defaults_used.append(nome)
            elif comp.get("required"):
                _falta(comp, "sem_valor", None, condicional)
            continue

        if comp.get("multiple"):
            itens = bruto if isinstance(bruto, (list, tuple, set)) else re.split(r"[;,/|]|\be\b", str(bruto))
            ids: List[str] = []
            nao_reconhecidos: List[str] = []
            for item in itens:
                if _flow_vazio(item):
                    continue
                oid = _resolver_opcao_de_flow(comp, item)
                if oid:
                    ids.append(oid)
                else:
                    nao_reconhecidos.append(str(item).strip())
            if nao_reconhecidos:
                _falta(comp, "valor_nao_reconhecido", nao_reconhecidos, condicional)
                continue
            ids = list(dict.fromkeys(ids))
            nenhuma = comp.get("none_option")
            # "Nenhuma das opções" junto de uma característica real é contradição
            # da coleta, não do formulário: o fato positivo vence.
            if nenhuma and len(ids) > 1 and nenhuma in ids:
                ids = [i for i in ids if i != nenhuma]
            if not ids:
                if comp.get("required"):
                    _falta(comp, "sem_valor", None, condicional)
                continue
            params[nome] = ids
            continue

        oid = _resolver_opcao_de_flow(comp, bruto)
        if not oid:
            _falta(comp, "valor_nao_reconhecido", bruto, condicional)
            continue
        params[nome] = oid

    ok = not missing
    return {
        "ok": ok,
        "flow_id": str(flow_schema.get("flow_id") or ""),
        "flow_name": str(flow_schema.get("flow_name") or ""),
        "params": params if ok else None,
        "missing": missing,
        "missing_detail": detail,
        "defaults_used": defaults_used,
    }


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


def missing_slots_for_subservice(playbook: Any, subservice: str, slots: Dict[str, Any]) -> List[str]:
    """O que ainda falta para acionar. `["subservico_invalido"]` quando esta
    seguradora não faz este trabalho por este canal — que é handoff, não bloqueio
    de coleta.

    Aceita o playbook OU o `playbook_ref` (string). A ficha do atendente, em
    `graph.py::_slots_obrigatorios_do_caso`, passa o ref: com a assinatura antiga
    isso levantava AttributeError dentro do `try` do chamador e a ficha ficava
    permanentemente sem a linha "o que falta" — falha silenciosa, verde no CI."""
    if isinstance(playbook, str):
        playbook = get_playbook(playbook) or {}
    sub = ((playbook or {}).get("subservices") or {}).get(canonical_subservice(subservice))
    if not sub:
        return ["subservico_invalido"]
    return [f for f in sub.get("required_slots") or [] if not str(slots.get(f) or "").strip()]
