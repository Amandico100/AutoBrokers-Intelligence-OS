# -*- coding: utf-8 -*-
"""O PÓS-ACIONAMENTO — as cartas, a taxonomia e o bloco do prompt. SPEC-097.1.

🔴 **TUDO AQUI É DADO OU FUNÇÃO PURA.** Nenhuma linha abre conexão, agenda
tarefa ou manda mensagem. Quem executa são os motores que já existem: o
corredor (`dispatch_router.registrar_checkpoint`), o vigia das esperas
(`handoff_watchdog.varrer_esperas_vencidas`) e o caminho de resposta do agente
de atendimento (`graph.py`). SPEC-097.1 §5 — nenhum motor novo.

⚠️ **E é UMA fonte só.** O mesmo `classificar_turno` que a régua importa é o
que gera o bloco do prompt; a mesma `SITUACOES_PARA_HUMANO` que o prompt lê é
a que o handoff e a régua leem. 📊 A SPEC-083 pagou três vezes por um padrão
medido com uma ferramenta e aplicado com outra (CLAUDE.md §9.4): aqui não há
segunda cópia para divergir.

📊 Medido em 05/09/2026 (`reality-report-0971.md` §2, 1.088 mensagens do
cliente depois do acionamento em 36 conversas): 56,3 % das mensagens têm ≤ 24
caracteres e a conversa tem 2,01 mensagens por turno — por isso a unidade de
tudo neste arquivo é o **TURNO** (a rajada), nunca a mensagem (R1).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ===========================================================================
# 0. A NORMALIZAÇÃO — o MESMO dialeto do SQL que mediu a taxonomia
#
# 🔴 CLAUDE.md §9.4: *"um padrão medido com um motor e aplicado com outro é um
# padrão sobre outra coisa"*. A cascata do §2 do relatório rodou em Postgres
# com `translate(lower(content), 'áàâã…', 'aaaa…')`. Aqui se faz o MESMO —
# minúsculas e acentos removidos — para que um número medido lá valha aqui.
# ⛔ E é por isso que NENHUM padrão deste arquivo tem acento: ele nunca veria
#    um.
# ===========================================================================


def _norm(texto: Any) -> str:
    """Minúsculas, sem acento, com espaços colapsados. **Pura.**"""
    bruto = str(texto or "")
    sem_acento = "".join(
        ch for ch in unicodedata.normalize("NFD", bruto)
        if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


# ===========================================================================
# 1. AS CATEGORIAS — a taxonomia MEDIDA, não inventada
#
# 📊 `reality-report-0971.md` §2, sobre 1.088 mensagens: documentos 124 ·
# agenda 42 · valores 27 · oficina 25 · peça 14 · cobrar terceiro 12 ·
# status 11 · carro reserva 9 · indenização 6 · cobertura 4 · prestador não
# chegou 3 · nova abertura 3 · reclamação 2 · cancelar 1 · social 88 ·
# mídia 84 · não classificado 633.
# ===========================================================================

CATEGORIAS: Dict[str, str] = {
    "A": "quer saber o andamento do caso",
    "B": "está tratando de documentos",
    "C": "quer marcar ou remarcar a vistoria",
    "D": "pergunta pelo carro reserva",
    "E": "pergunta de valor: franquia, reembolso ou taxa",
    "F": "quer saber se o seguro cobre",
    "G": "quer falar de oficina ou de credenciada",
    "H": "pergunta pela peça ou pela previsão do serviço",
    "I": "quer abrir um caso NOVO no mesmo fio",
    "J": "pede que a corretora cobre a seguradora ou a oficina",
    "K1": "diz que o prestador não chegou",
    "K2": "está reclamando",
    "K3": "quer cancelar ou desistir",
    "L": "pergunta de indenização ou de pagamento",
    "M": "só agradeceu ou cumprimentou",
    "N": "fragmento de turno: não dá para saber o que quer",
    "P": "pediu uma pessoa, ou há urgência de vida",
    "Z": "mandou mídia sem texto",
}

#: 🔴 O RUÍDO — o que **não** entra no denominador da régua (R8).
#: ⚠️ Sem esta linha a régua passaria de 95 % sem resolver nada: 📊 no acervo,
#: 88 mensagens são social, 84 mídia e 633 fragmentos (CLAUDE.md §9.5).
SEM_INTENCAO: Tuple[str, ...] = ("M", "N", "Z")

#: 🔴 R9 — O QUE VAI PARA HUMANO POR DESENHO. **FONTE ÚNICA**: o prompt, o
#: handoff e a régua leem ESTE objeto (o guarda prova a identidade em [Q4]).
#:
#: ⚠️ As entradas com `*` são CONDICIONAIS na SPEC (cobertura fora de carta,
#: documento ilegível depois de dois pedidos, negociação de valor). Elas
#: moram em `SITUACOES_CONDICIONAIS` porque uma lista que mistura "sempre" com
#: "às vezes" vira uma lista que ninguém consegue contar.
#: ⛔ `I` (nova abertura) NÃO está aqui: volta ao corredor de acionamento.
SITUACOES_PARA_HUMANO: Dict[str, str] = {
    "K1": "segurança antes do atendimento: cobrar a seguradora AGORA e responder aqui",
    "K2": "relacionamento não se automatiza: ouvir, pedir desculpa e resolver",
    "K3": "cancelar tem consequência na apólice: confirmar com o segurado",
    "J": "quem cobra a seguradora é uma pessoa da corretora",
    "L": "valor e data de pagamento só a seguradora dá",
    "P": "o segurado pediu uma pessoa, ou há urgência de vida",
    "Z": "mídia sem texto: anexar ao dossiê e ler",
}

#: As condicionais da R9 — viram humano **quando a condição bate**.
SITUACOES_CONDICIONAIS: Dict[str, str] = {
    "F": "cobertura ou direito que NÃO está numa carta",
    "B": "documento ilegível ou incompleto depois de dois pedidos",
    "E": "negociação de franquia ou de valor (não é 'como funciona')",
}


def vai_para_humano(rotulo: Any) -> bool:
    """Este rótulo é humano por desenho? — **PURA**, lê a fonte única."""
    return str(rotulo or "") in SITUACOES_PARA_HUMANO


# ===========================================================================
# 2. A CASCATA — a primeira regra que casa vence
#
# 🔴 A ORDEM É A REGRA. `"tem direito aquele carro reserva"` é D e não F;
# `"muito abuso... o prestador foi ao local mas nao foi"` é K2 e não K1. Uma
# cascata em que a ordem não importasse seria uma cascata que não decide.
# ⚠️ Cada padrão é ESPECÍFICO de propósito: 📊 58 % do acervo cai em `N`, e
# alargar um padrão para "pegar mais" é como se compra recall com precisão
# comprada de quem não devia.
# ===========================================================================

_CASCATA: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("K1", re.compile(
        r"prestador (ainda )?nao (veio|chegou|apareceu)|ninguem (veio|chegou|apareceu)"
        r"|(esperei|esperou|esperando) (um monte|ate agora|horas)"
        r"|(estou|to) (parado |presa |preso )?(no acostamento|na pista|na estrada)"
        r"|local de risco|guincho nao (veio|chegou)")),
    ("K2", re.compile(
        r"muito abuso|absurdo|descaso|um desrespeito|pessimo|nao e verdade"
        r"|e mentira|mas nao foi|reclama(cao|r) (disso|com)|to indignad")),
    ("K3", re.compile(r"cancelar|desistir|nao quero mais|desisti do")),
    ("L",  re.compile(r"indeniza|ser pag[ao]|pagamento (da|do)|prazo de pagamento")),
    ("I",  re.compile(
        r"abre? o (sinistro|chamado|atendimento)|abrir (outro|um novo|mais um)"
        r"|outro carro (tambem|meu)|de um outro veiculo")),
    ("J",  re.compile(
        r"cobra-los|cobrar (eles|de novo|a seguradora|a oficina|a loja)"
        r"|temos que cobrar|voces cobram|da uma cobrada")),
    ("D",  re.compile(r"carro reserva|carro de cortesia|fico sem carro|veiculo reserva")),
    ("E",  re.compile(
        r"franquia|reembols|consigo receber|custos que tive|taxa (de|do)"
        r"|quanto vou pagar|valor do (servico|conserto)")),
    ("C",  re.compile(
        r"vistoria|agendar|agendamento|remarcar|que horas|hoje a tarde"
        r"|amanha de manha|marcar (para|o dia)")),
    ("G",  re.compile(
        r"credenciada|oficina|outra opcao de|mais perto de casa|trocar de loja")),
    ("B",  re.compile(
        r"document|comprovante|nota fiscal|(a|o) (foto|pdf|arquivo)"
        r"|o que (falta|faltam)|(faltam|falta) algum|mandar (o|a|os|as) ")),
    ("H",  re.compile(
        r"\bpeca\b|\bpecas\b|previsao|para-brisa|\bvidro\b|chegou a peca"
        r"|quando (chega|fica pronto)|\bprazo\b")),
    ("F",  re.compile(
        r"(nao )?cobre|cobertura|tenho direito|como funciona|sabes como"
        r"|esta na apolice|entra no seguro")),
    ("A",  re.compile(
        r"algum retorno|deram (algum )?retorno|permanece a mesma"
        r"|(alguma|tem) novidade|saiu alguma|como (esta|anda) (o meu|meu|o) caso"
        r"|\bandamento\b|e ai\b|ja tem (alguma )?resposta|alguma resposta")),
    ("M",  re.compile(
        r"obrigad|deus (abencoe|te abencoe)|valeu|otimo, obrigad|agradeco")),
)

#: 🔴 `P` é URGÊNCIA e vem ANTES de tudo — inclusive de K1. Um segurado que
#: diz "tem gente ferida" não pode esperar a cascata concordar.
_URGENCIA = re.compile(
    r"quero falar com (uma pessoa|um atendente|alguem)|me passa para (uma pessoa|alguem)"
    r"|\bferid|\bvitima|ambulancia|acidente agora|urgencia medica|passando mal")


def classificar_turno(mensagens: Any) -> str:
    """O rótulo do TURNO (a rajada), não da mensagem. **PURA, sem LLM.**

    🔴 **R1 — a unidade é a rajada.** 📊 542 turnos contra 1.088 mensagens no
    acervo: metade das mensagens do cliente é a segunda metade de uma frase, e
    classificar cada uma delas produziria 56 % de fragmento onde há pergunta.

    Devolve a **primeira** categoria com intenção que casar; `'M'` quando só
    houve agradecimento; `'Z'` quando não veio texto nenhum; `'N'` quando nada
    casa — e `'N'` é uma resposta honesta, não uma falha.
    """
    if isinstance(mensagens, (str, bytes)):
        mensagens = [mensagens]
    partes: List[str] = [str(m or "") for m in (mensagens or [])
                         if str(m or "").strip()]
    if not partes:
        # ⚠️ 📊 84 mensagens do acervo são áudio/foto/PDF sem texto. Elas não
        #    são "não classificadas": são MÍDIA, e vão para humano (R9).
        return "Z"

    texto = _norm(" ".join(partes))
    if not texto:
        return "Z"
    if _URGENCIA.search(texto):
        return "P"
    for rotulo, padrao in _CASCATA:
        if padrao.search(texto):
            return rotulo
    return "N"


# ===========================================================================
# 3. AS SEIS CARTAS — linguagem de corretora, nunca de apólice (R6)
#
# 🔴 Cada uma termina numa PRÓXIMA AÇÃO COM DONO. 📊 O guarda [F] roda sobre
# elas o mesmo detector de língua técnica da 097 ([13]/R11): chave, variável,
# nome de campo, versão `@1` e frase de apólice reprovam.
# ⛔ Nenhuma promete prazo que a seguradora não deu (R3).
# ===========================================================================

CARTAS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "C1",
        "titulo": "Quando o carro reserva vale, e o que levar para retirar",
        "cobre": ("D",),
        "texto": (
            "O carro reserva vale pelos dias que estão na sua apólice e começa a "
            "contar quando você retira. Para retirar, o condutor precisa levar a "
            "CNH original e válida e um cartão de crédito no nome dele, com "
            "limite livre para a caução da locadora. Os dias são corridos e não "
            "podem ser divididos. Se o reparo ficar pronto ou a indenização for "
            "paga antes do fim dos dias, o carro tem de voltar na hora — se ficar "
            "mais, a locadora cobra as diárias a mais de você. "
            "Quer que eu confirme quantos dias a sua apólice tem?"
        ),
    },
    {
        "id": "C2",
        "titulo": "Como funciona a franquia, e quem recebe",
        "cobre": ("E",),
        "texto": (
            "A franquia é a parte que fica com você quando o reparo é feito pelo "
            "seguro. Ela é paga direto na oficina, quando o serviço ficar pronto "
            "— não é pago para a corretora nem para a seguradora. Em vidros e "
            "peças, a franquia costuma ser por peça. A própria oficina informa se "
            "dá para parcelar e em quantas vezes. Se você quiser, "
            "eu confirmo o valor exato do seu caso antes de você decidir."
        ),
    },
    {
        "id": "C3",
        "titulo": "A previsão é da seguradora, e eu te aviso quando ela mudar",
        "cobre": ("A", "H"),
        "texto": (
            "A previsão de chegada da peça e a data do serviço quem define é a "
            "seguradora, junto com a loja — eu não consigo garantir uma data por "
            "conta própria. O que eu faço é acompanhar e te avisar aqui assim que "
            "mudar, para você não precisar perguntar. Hoje o seu caso está na "
            "situação que está escrita no seu atendimento. Se passar do prazo que "
            "a seguradora deu, eu cobro de novo e te digo o que responderam."
        ),
    },
    {
        "id": "C4",
        "titulo": "O que precisa para a vistoria, e o que acontece depois",
        "cobre": ("C", "G"),
        "texto": (
            "A vistoria é o momento em que a oficina olha o veículo e monta o "
            "orçamento. Você pode levar no horário combinado com o documento do "
            "veículo e a sua identificação. Depois dela, a oficina manda o "
            "orçamento para a seguradora, e a seguradora responde autorizando ou "
            "pedindo ajuste. Se a oficina que ficou perto de você estiver sem "
            "agenda, me diz que eu procuro outra credenciada na sua região."
        ),
    },
    {
        "id": "C5",
        "titulo": "O que eu preciso de você para o caso andar",
        "cobre": ("B",),
        "texto": (
            "Para o seu caso seguir, ainda falta o que está anotado no seu "
            "atendimento. Pode mandar aqui mesmo, por foto ou por arquivo, um de "
            "cada vez. Assim que chegarem, eu confiro e te aviso — se algum "
            "documento vier ilegível, eu te falo na hora, em vez de deixar o seu "
            "caso parado esperando."
        ),
    },
    {
        "id": "C6",
        "titulo": "O prestador não chegou",
        "cobre": ("K1",),
        "texto": (
            "Sinto muito pela espera. Vou verificar agora com a seguradora onde "
            "está o prestador e volto aqui com o que eles responderem. Se você "
            "estiver em local de risco (pista, acostamento, à noite), saia do "
            "veículo e fique num lugar seguro — isso vem antes do atendimento."
        ),
    },
)

#: As cartas por id, para quem precisa de uma só.
CARTAS_POR_ID: Dict[str, Dict[str, Any]] = {c["id"]: c for c in CARTAS}


def mapa_de_cartas() -> Dict[str, str]:
    """`{rótulo: id da carta}` — **derivado de `CARTAS`, nunca escrito à mão.**

    🔴 E9: o bloco do prompt é GERADO daqui. Acrescentar uma carta muda o
    prompt no mesmo instante — que é o precedente de
    `conhecimento_de_assistencia` (o bloco de abertura sai dos playbooks).
    """
    mapa: Dict[str, str] = {}
    for carta in CARTAS:
        for rotulo in carta.get("cobre") or ():
            mapa.setdefault(str(rotulo), str(carta["id"]))
    return mapa


# ===========================================================================
# 4. O ESTADO EM PORTUGUÊS — `texto_da_espera`
#
# ⚠️ 📊 R2/E13: `esperando_oficina` **não é um kind**. "a loja" é palavra de
# TEXTO; o que está no banco são três kinds, e citar um quarto seria afirmar
# o que não está escrito (R3).
# ===========================================================================

_DE_QUEM: Dict[str, str] = {
    "esperando_seguradora": "esperando a seguradora",
    "esperando_cliente": "esperando você mandar o que falta",
    "esperando_humano": "esperando alguém da equipe da corretora",
}


def _dia_e_mes(bruto: Any) -> str:
    """`29/08` a partir de um ISO. `""` quando não dá para saber."""
    from datetime import datetime

    texto = str(bruto or "").strip()
    if not texto:
        return ""
    try:
        limpo = texto.replace("Z", "+00:00")
        return datetime.fromisoformat(limpo).strftime("%d/%m")
    except Exception:  # noqa: BLE001
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", texto)
        return "%s/%s" % (m.group(3), m.group(2)) if m else ""


def _dias_desde(bruto: Any) -> Optional[int]:
    from datetime import datetime, timezone

    texto = str(bruto or "").strip()
    if not texto:
        return None
    try:
        quando = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        if quando.tzinfo is None:
            quando = quando.replace(tzinfo=timezone.utc)
        dias = (datetime.now(timezone.utc) - quando).days
        return dias if dias >= 0 else None
    except Exception:  # noqa: BLE001
        return None


def texto_da_espera(espera: Any) -> str:
    """*"esperando a seguradora desde 29/08 (7 dias)"* — **PURA**.

    ⛔ Devolve `""` quando não há espera escrita. **Isso é R3:** sem linha em
    `work_waits`, não há de quem se esperar, e inventar um "estamos quase" é
    exatamente o que esta SPEC existe para impedir.
    """
    if not isinstance(espera, dict) or not espera:
        return ""
    if str(espera.get("status") or "ativo") != "ativo":
        return ""
    frase = _DE_QUEM.get(str(espera.get("kind") or ""))
    if not frase:
        # ⚠️ Um kind fora do CHECK do banco não vira frase: ele vira silêncio.
        return ""
    desde = _dia_e_mes(espera.get("created_at"))
    if desde:
        frase = "%s desde %s" % (frase, desde)
    dias = _dias_desde(espera.get("created_at"))
    if dias is not None and dias >= 1:
        frase = "%s (%d dia%s)" % (frase, dias, "s" if dias > 1 else "")
    return frase


# ===========================================================================
# 5. R11 — SÓ ATENDIMENTO VIRA CONHECIMENTO
#
# 🔴 🧑 Decisão do Founder (05/09): *"tudo que for pessoal deve ser
# descartado"*. 📊 A razão está medida: 633 das 1.088 mensagens caem em `N`, e
# a amostra de 60 mostrou creche, fim de semana e *"passa pra fulana"* no
# MESMO fio em que o caso anda — o celular da atendente é o celular dela.
#
# ⚠️ **A regra é de DESCARTE, não de admissão.** Descarta-se o que tem marca
# de vida pessoal ou de coordenação entre colegas **e** nenhuma palavra de
# seguro. Um fragmento sem marca nenhuma FICA: 📊 *"estou parado no
# acostamento"* não tem uma palavra de seguro dentro e é o turno que mais
# importa do acervo inteiro. Exigir vocabulário para admitir jogaria fora o
# segurado na estrada junto com o papo de creche.
# ===========================================================================

_DE_SEGURO = re.compile(
    r"seguro|seguradora|apolice|sinistro|protocolo|guincho|vidro|para-brisa"
    r"|oficina|credenciada|franquia|vistoria|indeniza|prestador|cobertura"
    r"|assistencia|chaveiro|\bpneu\b|bateria|reboque|laudo|boletim de ocorrencia"
    r"|carro reserva|corretora|endosso|\bparcela|\bboleto\b|renovacao|\bcaso\b"
    r"|atendimento|\bchamado\b|\bcobre\b|conserto|reparo|\bpeca\b|acionamento")

_DE_VIDA_PESSOAL = re.compile(
    r"fim de semana|final de semana|feriado|\bcreche\b|\bcrianc|\bfilh[oa]"
    r"|escola d[oa]|aniversario|\bpraia\b|churrasco|\bjantar\b|\bnamorad"
    r"|\bmarido\b|\besposa\b|\bkkk|\bhaha|bom diaaa|\bacademia\b"
    r"|\bmedico\b(?! do convenio)|\bferias\b")

_DE_COLEGA = re.compile(
    r"passa pra |passa para (a |o )?(fulana|ela|ele)|me coloca em copia"
    r"|chama ela|chama ele|voce ja almocou|vou almocar|sair mais cedo"
    r"|estou em reuniao|to em reuniao|bom dia meninas|assume essa|assumir essa")


def _texto_da_conversa(conversa: Any) -> str:
    """Todo o texto de uma conversa, junto. Aceita dict, lista ou string."""
    if conversa is None:
        return ""
    if isinstance(conversa, (str, bytes)):
        return str(conversa)
    if isinstance(conversa, (list, tuple)):
        return " ".join(_texto_da_conversa(x) for x in conversa)
    if isinstance(conversa, dict):
        for chave in ("mensagens", "messages", "turnos"):
            valor = conversa.get(chave)
            if isinstance(valor, (list, tuple)) and valor:
                pedacos = []
                for item in valor:
                    if isinstance(item, dict):
                        pedacos.append(str(item.get("content")
                                           or item.get("texto")
                                           or item.get("text") or ""))
                    else:
                        pedacos.append(str(item or ""))
                return " ".join(pedacos)
        for chave in ("texto", "content", "last_message_preview"):
            valor = conversa.get(chave)
            if valor:
                return str(valor)
    return ""


def e_atendimento_de_seguro(conversa: Any) -> bool:
    """Esta conversa pode virar carta e entrar na régua? — **PURA** (R11).

    ⛔ `False` para papo pessoal e coordenação entre colegas: nunca vira carta,
    nunca é lida por agente, nunca entra no denominador — e é CONTADA como
    descartada, porque descartar em silêncio é o defeito que a 097 já pagou.
    """
    texto = _norm(_texto_da_conversa(conversa))
    if not texto:
        return False
    if _DE_SEGURO.search(texto):
        # O fio mistura caso e vida; quando o caso aparece, o caso vence.
        return True
    return not (_DE_VIDA_PESSOAL.search(texto) or _DE_COLEGA.search(texto))


# ===========================================================================
# 6. O BLOCO DO PROMPT — GERADO, nunca constante (E9/U3.2)
#
# 🔴 Se ele fosse um texto fixo, acrescentar uma carta deixaria o agente
# ensinando a versão velha e NADA ficaria vermelho — foi o que aconteceu em
# 18/08 com `aparelho_marca_modelo` (o comentário em `graph.py` conta).
# ===========================================================================

_ABERTURA_DO_BLOCO = (
    "DEPOIS DO ACIONAMENTO (o caso já tem protocolo, prestador ou previsão):\n"
    "- O atendimento NÃO acabou quando o acionamento saiu. A pessoa continua "
    "perguntando, e quem responde é você.\n"
    "- Você só afirma o que está ESCRITO no atendimento: previsão, protocolo, "
    "valor, autorização e \"já está quase\" vêm do estado do caso, nunca de "
    "você. Quando não houver estado novo escrito, diga que não houve novidade "
    "e que a corretora está cobrando — e não prometa data nenhuma.\n"
    "- Quem pergunta pode ser o segurado, a oficina ou o parceiro. A verdade é "
    "a mesma para os três; se não der para saber quem é, responda sem chamar a "
    "pessoa de nada."
)

_FECHO_DO_BLOCO = (
    "QUANDO PASSAR PARA UMA PESSOA DA CORRETORA:\n"
    "%s\n"
    "- Ao passar, escreva de quem se está esperando, desde quando, o que falta "
    "e o que a pessoa da corretora tem de fazer. Nunca peça para \"concluir o "
    "acionamento\" de um caso que já foi acionado."
)


def bloco_do_prompt() -> str:
    """A seção de PÓS-ACIONAMENTO do prompt do agente de atendimento.

    🔴 **GERADO** de `mapa_de_cartas()` e de `SITUACOES_PARA_HUMANO` — as duas
    lidas do módulo em tempo de chamada, para que trocar qualquer uma delas
    mude o texto que chega ao modelo (é o que [J1] mede).
    """
    linhas = [_ABERTURA_DO_BLOCO, "", "O QUE RESPONDER, POR SITUAÇÃO:"]
    mapa = mapa_de_cartas() or {}
    if mapa:
        for rotulo, carta_id in sorted(mapa.items()):
            carta = CARTAS_POR_ID.get(carta_id) or {}
            linhas.append(
                "- quando a pessoa %s: responda com a carta %s (%s)."
                % (CATEGORIAS.get(rotulo, "pergunta"), carta_id,
                   carta.get("titulo") or "")
            )
    else:
        # ⚠️ Sem carta nenhuma o bloco DIZ isso, em vez de fingir cobertura.
        linhas.append("- nenhuma carta publicada: responda só com o que está "
                      "escrito no atendimento, e passe o resto para uma pessoa.")
    linhas.append("")
    humanos = "\n".join(
        "- %s → passe para uma pessoa da corretora: %s."
        % (CATEGORIAS.get(rotulo, rotulo), razao)
        for rotulo, razao in SITUACOES_PARA_HUMANO.items()
    )
    linhas.append(_FECHO_DO_BLOCO % humanos)
    return "\n".join(linhas)


#: ⚠️ O nome que a SPEC-097.1 §4 usa em prosa. Mesmo objeto — nunca uma
#: segunda função (§5).
bloco_de_pos_acionamento = bloco_do_prompt


__all__ = [
    "CARTAS", "CARTAS_POR_ID", "CATEGORIAS", "SEM_INTENCAO",
    "SITUACOES_PARA_HUMANO", "SITUACOES_CONDICIONAIS", "vai_para_humano",
    "classificar_turno", "mapa_de_cartas", "texto_da_espera",
    "e_atendimento_de_seguro", "bloco_do_prompt", "bloco_de_pos_acionamento",
]
