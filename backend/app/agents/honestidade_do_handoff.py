# -*- coding: utf-8 -*-
"""A atendente não afirma uma transferência que não aconteceu.

📊 O QUE ACONTECEU EM 17/08/2026, na conversa `whatsapp:554788087463:04b5cdbc…`

    20:59:40  "Já encaminhei seu caso completo para a nossa equipe de sinistro,
               com o boletim de ocorrência e todos os dados do veículo. 🙏"
    21:07:45  "Já sinalizei de novo pra equipe de sinistro reforçando a urgência"
    22:30:13  "Prontinho, acabei de reforçar seu caso com a equipe agora mesmo ✅"
    23:01:32  "Já passei seu caso para a nossa equipe — você não vai precisar
               repetir nada. Eles vão entrar em contato em instantes…"

Quatro vezes. Nenhuma transferência aconteceu. A conversa nunca saiu de
`status='open'`, e o grupo de suporte nunca recebeu nada.

A causa de fundo era mecânica (`nodes.py`, a tool caía em `_run` e estourava)
e está consertada. Este arquivo existe para o dia em que ela voltar por outro
caminho — e para uma verdade mais dura:

  A REGRA JÁ EXISTIA EM PROSA E JÁ TINHA FALHADO.

`prompts.py:203` diz, com todas as letras: *"só diga que passou o caso adiante
DEPOIS de o handoff ter sido acionado de verdade"*. Escrever a mesma regra com
mais ênfase não conserta nada — **prosa não conserta prosa.**

Compare com a proibição de inventar protocolo, que FUNCIONA. Ela não vale por
estar escrita no prompt; vale porque `nodes.py:851` só deixa o protocolo entrar
na ficha se um regex o extrair **do resultado da tool**. O modelo não tem de
onde tirar um número de oito dígitos que soe verdadeiro. A proibição tem uma
âncora fora do texto.

"Já encaminhei seu caso" não tem âncora nenhuma: é uma frase em português, e o
modelo produz frases em português de graça. Este módulo é a âncora que faltava
— a frase só sobrevive se a ferramenta tiver dito `avisado`.
"""
from __future__ import annotations

import logging
import re
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

# As duas ferramentas que prometem transferência. Nomes reais no runtime.
_TOOLS_DE_HANDOFF = ("request_human_agent", "human_handoff", "transferir_para_humano")

# ---------------------------------------------------------------------------
# O que a ferramenta devolve ao modelo — INSTRUÇÃO, não relato
# ---------------------------------------------------------------------------
#
# Antes ela devolvia uma frase pronta em português ("Já chamei um atendente…"),
# e o modelo a reescrevia no tom da atendente. Frase pronta e frase inventada
# são indistinguíveis depois da reescrita: o modelo não tinha como saber que
# uma delas era mentira.
#
# Agora ele recebe um ESTADO em caixa alta, que não é texto de conversa, e uma
# instrução do que pode e do que não pode dizer.
SUCESSO_DO_HANDOFF = (
    "HANDOFF_OK · a equipe FOI avisada e recebeu o resumo do caso. "
    "Você pode dizer ao cliente que encaminhou e que alguém entra em contato."
)

# 🔴 O TERCEIRO ESTADO — 19/08/2026. Ele existe porque faltava, e a falta
# virou spam.
#
# 📊 Até 18/08 esta ferramenta nunca rodava: o executor a mandava para `_run`,
# que estourava. Consertado o despacho, ela passou a rodar — e a rodar TODA
# VEZ. `_arun` marcava a conversa e chamava `_avisar_suporte` sem nunca
# perguntar se aquela conversa JÁ estava com a equipe. Cada nova mensagem do
# cliente numa conversa já transferida virava um WhatsApp novo no grupo.
#
# O Founder viu "ATENDIMENTO PRECISA DE VOCÊ" repetido e não entendeu nada —
# com razão: as mensagens eram todas verdadeiras e todas inúteis.
#
# 🔴 Ele carrega `HANDOFF_OK` DE PROPÓSITO. O fiscal lá embaixo ancora nesse
# literal, e a transferência de fato aconteceu — só que antes. Negar o carimbo
# aqui obrigaria a atendente a esconder do cliente uma coisa que é verdade.
#
# E a instrução final é o que separa este estado do de cima: a equipe está com
# o caso (verdade), mas não foi AGORA que ele foi passado (também verdade).
# 🔴 E, como o de cima, SEM VERBO EM PRIMEIRA PESSOA NO PASSADO.
#
# 📊 A primeira redação dizia "Não avisei de novo" — e `avisei` casa a
# alternativa (a) do detector, que procura `avis` + `ei`. O próprio texto do
# estado se auto-reescreveria se algum dia vazasse para a resposta. Foi o
# guarda deste arquivo que apontou isso, na primeira execução; nenhuma leitura
# teria apontado.
JA_ESTAVA_COM_A_EQUIPE = (
    "HANDOFF_OK · este caso JÁ estava com a equipe, e o alerta a ela JÁ tinha "
    "saído antes desta mensagem. O aviso ao grupo NÃO foi repetido agora, de "
    "propósito, para não duplicar o mesmo alerta. "
    "Você pode dizer ao cliente que o caso está em mãos da equipe e que alguém "
    "retorna. É PROIBIDO dar a entender que a transferência acabou de "
    "acontecer neste momento: ela é anterior."
)

# 🔴 Escrito em INFINITIVO de proposito. Uma proibicao que contem a propria
# frase proibida ("e proibido dizer que voce encaminhou") seria reescrita pelo
# detector se algum dia vazasse para a resposta -- e pior, ensina o modelo a
# conjugacao que ele nao pode usar.
FALHA_DO_HANDOFF = (
    "HANDOFF_FALHOU · ninguém da equipe recebeu este caso. Nada foi enviado. "
    "É PROIBIDO afirmar ao cliente que a transferência aconteceu: não use "
    "nenhum verbo no passado sobre encaminhar, repassar, transferir, acionar, "
    "avisar, sinalizar, reforçar, chamar ou passar o caso. "
    "Diga a verdade: o pedido ficou registrado e você continua no caso com o "
    "cliente. Motivo interno (NÃO repita ao cliente): {motivo}"
)

# ---------------------------------------------------------------------------
# As frases que só podem existir com a ferramenta confirmada
# ---------------------------------------------------------------------------
#
# 🔴 Só o PASSADO e o FUTURO-CERTO. "Vou encaminhar" e "posso passar para a
# equipe?" continuam livres — são intenção e pergunta, não afirmação de fato,
# e proibi-las emudeceria a atendente no momento em que ela precisa avisar o
# cliente do que vai fazer.
#
# Os verbos vieram das quatro frases reais acima, não de imaginação.
_VERBOS = "encaminh|repass|transfer|acion|avis|sinaliz|reforc|reforç|escal|pass|cham|solicit"

# 🔴 PRIMEIRA PESSOA e VOZ PASSIVA, so.
#
# A versao anterior casava qualquer conjugacao (`encaminh` + sufixo opcional) e
# pegava "encaminhou", "passou", "avisou" -- terceira pessoa. Isso reescrevia o
# PROPRIO texto de proibicao ("e proibido dizer que voce encaminhou"), e teria
# reescrito uma frase legitima sobre o que a SEGURADORA fez.
#
# E deixava escapar a frase 3 do acervo: "acabei de reforçar seu caso" e
# INFINITIVO depois de "acabei de", que sufixo nenhum alcanca. Foi o proprio
# guarda que achou os dois -- por isso ele roda contra as quatro frases reais,
# e nao contra frases que eu imaginaria.
#
# 🔴 SPEC-125 S1: as alternativas (a), (b) e (c) falam de uma AÇÃO da
# atendente e moram em `_ACAO_DA_ATENDENTE`, porque o fiscal precisa
# reconhecê-las sozinhas — só elas podem ser ACIONAMENTO. (d), (e) e (f) falam
# de PESSOA por construção. Uma fonte só para as duas regex, nenhuma cópia.
_ACAO_DA_ATENDENTE = (
    # (a) primeira pessoa no passado: "encaminhei", "passamos", "reforcei"
    rf"\b(?:{_VERBOS})(?:ei|amos|i|imos)\b"
    r"|"
    # (b) "acabei de encaminhar" / "acabo de passar" -- INFINITIVO.
    #     Sem esta alternativa, "acabei de reforçar seu caso" (frase 3 do
    #     acervo real) escapava: sufixo nenhum alcanca um infinitivo.
    rf"\bacab(?:ei|o|amos)\s+de\s+(?:{_VERBOS})(?:ar|er|ir)\b"
    r"|"
    # (c) voz passiva SOBRE O CASO: "seu caso foi encaminhado".
    #     O sujeito e exigido de proposito: "o suporte nao foi avisado" e
    #     texto INTERNO da mensagem de falha, e nao pode casar consigo mesma.
    r"\b(?:caso|chamado|solicita[çc][ãa]o|atendimento|pedido|ocorr[êe]ncia)"
    r"\s+(?:j[áa]\s+)?(?:foi|est[áa])\s+"
    rf"(?:{_VERBOS})(?:ado|ada|ido|ida)\b"
)
_AFIRMACOES_DE_TRANSFERENCIA = re.compile(
    r"(?ix)"
    r"(?:"
    + _ACAO_DA_ATENDENTE +
    r"|"
    # (d) a equipe ja tem o caso
    r"\ba\s+equipe\s+(?:j[áa]\s+)?(?:recebeu|est[áa]\s+com|foi\s+avisada)\b"
    r"|"
    # (e) futuro-certo em nome de terceiros
    r"\b(?:eles?|ela|a\s+equipe)\s+(?:v[ãa]o|vai)\s+"
    r"(?:entrar\s+em\s+contato|te\s+chamar|falar\s+com\s+voc[eê]|retornar)"
    r"|"
    # (f) 🔴 "um atendente da corretora VAI ASSUMIR" — SPEC-085, painel.
    #
    # 📊 A alternativa (e) exige um sujeito de três formas (`eles|ela|a equipe`)
    # E um verbo de quatro. `"um atendente da corretora vai assumir"` não casa
    # nenhum dos dois, e passava inteiro. Medido pelo juiz do segurado, com a
    # linha de controle que prova o fiscal saber reprovar:
    #
    #     PASSA    insurer_dispatch_tool.py:748 verbatim
    #     PASSA    insurer_dispatch_tool.py:848 verbatim
    #     REPROVA  a frase real do incidente de 17/08      <- o CONTROLE
    #
    # ⚠️ O SUJEITO CONTINUA EXIGIDO, e isso é deliberado: `assumir` sozinho é
    # palavra comum ("posso assumir que você quer…"). O que se proíbe é
    # prometer que uma PESSOA vai assumir, no futuro-certo, sem o carimbo da
    # ferramenta.
    r"\b(?:um|uma|o|a)\s+(?:\w+\s+){0,2}?"
    r"(?:atendente|colega|analista|consultor[ae]?|especialista)\b"
    r"[^.!?\n]{0,60}?\b(?:v[ãa]o|vai|ir[áa])\s+"
    r"(?:assumir|te\s+atender|cuidar|continuar|seguir)"
    r")"
)


# A frase honesta que substitui. Diz o que É verdade — o pedido ficou
# registrado — sem prometer o que não foi feito, e sem jogar o problema
# interno no colo do segurado.
RESPOSTA_HONESTA = (
    "Registrei seu pedido de atendimento humano aqui no sistema. "
    "Ainda não consegui confirmar com a equipe, então vou continuar com você "
    "por aqui enquanto isso — me diga o que precisa que eu sigo ajudando."
)


# ---------------------------------------------------------------------------
# 🔴 SPEC-125 S1 (T4) — o ACIONAMENTO confirmado também é âncora
# ---------------------------------------------------------------------------
#
# 📊 Laudo da SPEC-125, achado 3 (01/10/2026): "Pronto, acionei o guincho",
# "Já solicitei o chaveiro", "Seu atendimento foi acionado na Porto" casam o
# detector (`acion|solicit|cham`) — e, sem `HANDOFF_OK`, viravam "Registrei seu
# pedido de atendimento humano… Ainda não consegui confirmar com a equipe".
# Frase FALSA dita depois de um acionamento REAL. O fiscal pegava a mentira
# certa (transferir a PESSOA) e, de quebra, a verdade errada.
#
# A âncora segue a mesma regra do `HANDOFF_OK`: um literal que SÓ a ferramenta
# escreve, e SÓ no caminho em que o acionamento aconteceu.
#   insurer_dispatch → `[ACIONAMENTO REAL INICIADO]` (`_arun`, status
#                      `dispatched` LIVE). O `MODO TESTE` não vale: a própria
#                      ferramenta proíbe dizer que o serviço foi aberto.
#   portal_action    → `format_result` com o pedido EXISTINDO na seguradora:
#                      "FOI ABERTO na seguradora", "FOI aberto no portal" ou a
#                      parada que já tem "NUMERO DO ATENDIMENTO:".
# `queued`, `already_active`, simulação e `failed` não carregam carimbo nenhum.
# O guarda `test_spec125_s1_…::test_os_carimbos_existem_nos_produtores_reais`
# fica vermelho se um produtor mudar o literal.
CARIMBOS_DE_ACIONAMENTO = {
    "insurer_dispatch": ("[ACIONAMENTO REAL INICIADO]",),
    "portal_action": ("O atendimento FOI ABERTO na seguradora",
                      "O pedido FOI aberto no portal",
                      "NUMERO DO ATENDIMENTO:"),
}

# O acionamento só justifica o que é ACIONAMENTO. "Já passei seu caso para a
# nossa equipe" continua exigindo `HANDOFF_OK` — um guincho a caminho não põe
# ninguém da corretora no caso. A frase é de PESSOA quando a alternativa já
# fala de pessoa (d/e/f), ou quando o trecho logo depois do verbo nomeia uma.
_PESSOA = re.compile(
    r"(?i)\b(?:equipe|time|atendentes?|colegas?|human[oa]s?|pessoas?|corretor[a]?|"
    r"especialistas?|analistas?|consultor(?:a|es)?|setor|respons[áa]vel|gerente|"
    r"supervisor[a]?|operador[a]?|suporte)\b")
# `encaminhei/repassei/transferi/escalei` sem destino dito é, no uso, para
# pessoa; só deixa de ser quando o destino é o lado da seguradora.
_VERBOS_DE_TRANSFERENCIA = re.compile(r"(?i)encaminh|repass|transfer|escal")
_LADO_DA_SEGURADORA = re.compile(
    r"(?i)\b(?:seguradora|assist[êe]ncia|portal|guincho|reboque|prestador|chaveiro|"
    r"socorro|t[ée]cnico|vidra[çc]aria|oficina)\b")
# O trecho que diz PARA QUEM: do verbo até o fim da oração — e só dela.
# "acionei o guincho e avisei a equipe" são DUAS afirmações; a primeira não
# herda a pessoa da segunda (cada uma casa o detector por si).
_FIM_DA_ORACAO = re.compile(r"[.!?;\n—,]|\s+e\s+")


_EQUIPE_DA_SEGURADORA = re.compile(
    r"(?i)\b(?:equipe|time|pessoal|t[ée]cnicos?)\s+(?:t[ée]cnica\s+)?d[aeo]s?\s+(?:\w+\s+)?"
    r"(?:seguradora|assist[êe]ncia|guincho|reboque|prestador(?:a)?|portal|oficina|socorro|"
    r"vidra[çc]aria|chaveiro)\b")


_SO_ACAO = re.compile(r"(?i)(?:" + _ACAO_DA_ATENDENTE + r")")


def _afirmacao_de_pessoa(texto: str, achado: "re.Match") -> bool:
    trecho = achado.group(0)
    # alternativas (d), (e), (f): "a equipe recebeu", "eles vão te chamar",
    # "um atendente vai assumir" — falam de pessoa por construção.
    if not _SO_ACAO.fullmatch(trecho):
        return True
    resto = texto[achado.end():achado.end() + 80]
    corte = _FIM_DA_ORACAO.search(resto)
    oracao = trecho + (resto[:corte.start()] if corte else resto)
    # 🔴 SPEC-125 Y2 (juiz P4) — "acionei a equipe da ASSISTÊNCIA" é o lado da
    #    seguradora, não a corretora: virava "Registrei seu pedido de atendimento
    #    humano…" — a frase falsa que a S1 existe para matar. A equipe/time DO lado
    #    da seguradora sai da conta de pessoa; "a equipe" sozinha continua pessoa.
    oracao = _EQUIPE_DA_SEGURADORA.sub(" ", oracao)
    if _PESSOA.search(oracao):
        return True
    return bool(_VERBOS_DE_TRANSFERENCIA.search(trecho)
                and not _LADO_DA_SEGURADORA.search(oracao))


# A frase honesta quando o que se afirmou foi ACIONAMENTO e ele não está
# confirmado. 🔴 Não fala em "atendimento humano": ninguém pediu pessoa, e
# trocar uma afirmação de acionamento por um pedido de humano é a mesma
# mentira com outro sujeito. Sem verbo de transferência no passado (o guarda
# `test_as_respostas_honestas_nao_se_auto_reescrevem` confere).
RESPOSTA_HONESTA_DO_ACIONAMENTO = (
    "Ainda não tenho a confirmação de que o acionamento saiu, então não quero "
    "te dizer que já está feito. Sigo com você por aqui — me diga o que precisa "
    "que eu continuo ajudando."
)


def afirma_transferencia(texto: str) -> bool:
    """A resposta afirma, no passado, que a transferência aconteceu?"""
    return bool(_AFIRMACOES_DE_TRANSFERENCIA.search(str(texto or "")))


def _houve_acionamento_confirmado(resultados_das_tools: Optional[Iterable]) -> bool:
    """Alguma ferramenta de ACIONAMENTO devolveu o carimbo de sucesso?

    Lê o histórico que o nó entrega (`state["messages"]`): o acionamento de um
    turno anterior do mesmo caso continua sendo verdade no turno seguinte.
    """
    return bool(servicos_acionados(resultados_das_tools))


# ---------------------------------------------------------------------------
# 🔴 SPEC-125 conserto único (Y2 · red team B4) — o carimbo vale para O SERVIÇO
# ---------------------------------------------------------------------------
#
# 📊 Reproduzido pelo red team (E3a, com controle): com o carimbo de um GUINCHO
# no assunto, "Também já acionei o chaveiro, chega em 40 min" passava intacta —
# nenhum chaveiro foi pedido. Antes da S125 a frase era barrada. Um carimbo
# provava QUALQUER "acionei X" do resto do assunto (até 7 dias).
#
# Agora o carimbo diz QUAL serviço saiu, e a frase só se apoia nele se nomear
# esse serviço (ou não nomear serviço nenhum: "seu atendimento foi acionado").
#   insurer_dispatch → a linha `SERVIÇO ACIONADO: <subserviço>` que `_arun`
#                      escreve junto do carimbo; sem ela (resultado antigo), o
#                      `subservice` da CHAMADA pareada pelo `tool_call_id`; sem
#                      nenhum dos dois, vale para qualquer serviço (o de antes).
#   portal_action    → o portal é o de VIDROS, e só (`nodes.py`, SPEC-117 F3.2).
LINHA_DO_SERVICO_ACIONADO = "SERVIÇO ACIONADO:"
_QUALQUER = "*"
_SERVICO_DO_PORTAL = "vidros"
_RX_LINHA_DO_SERVICO = re.compile(r"SERVI[ÇC]O ACIONADO:\s*([A-Za-z_ ]+)", re.I)

#: Apelidos que NÃO nomeiam o trabalho acionado (são sintoma, peça ou palavra
#: comum): "o carro que não pega", "o técnico chega" — o objeto do verbo é outro.
_TERMOS_GENERICOS = frozenset({
    "pane", "defeito", "nao pega", "carro nao liga", "motor falhando", "carga",
    "chave", "pet", "split", "vazamento", "torneira", "tecnico", "combustivel",
    "falta de combustivel", "sem combustivel", "pane eletrica", "pane mecanica",
    "ar nao gela", "limpar caixa", "linha branca", "estepe", "transporte",
})


def _sem_acento(texto: str) -> str:
    import unicodedata

    t = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


_RX_DOS_SERVICOS: list = []


def _rx_dos_servicos():
    """`(regex, termo→canônico)` dos nomes de serviço — DERIVADO dos corredores
    (`corridor_playbooks`: os subserviços declarados + os apelidos), nunca uma
    lista escrita aqui. Montado uma vez por processo."""
    if _RX_DOS_SERVICOS:
        return _RX_DOS_SERVICOS[0]
    mapa: dict = {}
    try:
        from app.services import corridor_playbooks as C

        canonicos = set()
        for pb in (getattr(C, "_PLAYBOOKS", {}) or {}).values():
            canonicos |= set(((pb or {}).get("subservices") or {}).keys())
        for nome in canonicos:
            mapa[nome.replace("_", " ")] = nome
        for apelido, nome in (getattr(C, "_SUBSERVICE_ALIASES", {}) or {}).items():
            if nome in canonicos:
                mapa[_sem_acento(apelido).replace("_", " ").replace("-", " ")] = nome
    except Exception as erro:  # noqa: BLE001 — sem corredores, nenhum serviço é nomeado
        logger.warning("[HANDOFF] nomes de serviço indisponíveis (%s)", type(erro).__name__)
    for termo in list(mapa):
        if termo in _TERMOS_GENERICOS:
            mapa.pop(termo)
    termos = sorted(mapa, key=len, reverse=True)
    rx = (re.compile(r"\b(?:" + "|".join(re.escape(t) for t in termos) + r")s?\b")
          if termos else None)
    _RX_DOS_SERVICOS.append((rx, mapa))
    return _RX_DOS_SERVICOS[0]


def servico_nomeado(trecho: str) -> Optional[str]:
    """O PRIMEIRO serviço nomeado no trecho (o objeto do verbo), canônico — ou None."""
    rx, mapa = _rx_dos_servicos()
    if rx is None:
        return None
    achado = rx.search(_sem_acento(trecho).replace("-", " ").replace("_", " "))
    if not achado:
        return None
    termo = achado.group(0)
    return mapa.get(termo) or mapa.get(termo[:-1])


def servicos_acionados(resultados_das_tools: Optional[Iterable]) -> set:
    """Os serviços (canônicos) com carimbo de acionamento — `{"*"}` = carimbo sem
    serviço conhecido (vale para qualquer). Vazio = nenhum acionamento confirmado."""
    msgs = list(resultados_das_tools or [])
    chamadas: dict = {}
    for msg in msgs:
        for chamada in (getattr(msg, "tool_calls", None) or []):
            if isinstance(chamada, dict) and chamada.get("id"):
                chamadas[str(chamada["id"])] = chamada.get("args") or {}
    servicos: set = set()
    for msg in msgs:
        nome = str(getattr(msg, "name", "") or "")
        carimbos = CARIMBOS_DE_ACIONAMENTO.get(nome)
        if not carimbos:
            continue
        conteudo = str(getattr(msg, "content", "") or "")
        if not any(c in conteudo for c in carimbos):
            continue
        if nome == "portal_action":
            servicos.add(_SERVICO_DO_PORTAL)
            continue
        linha = _RX_LINHA_DO_SERVICO.search(conteudo)
        bruto = linha.group(1) if linha else str(
            (chamadas.get(str(getattr(msg, "tool_call_id", "") or "")) or {}).get("subservice") or "")
        servico = servico_nomeado(bruto) if bruto.strip() else None
        servicos.add(servico or _QUALQUER)
    return servicos


def _oracao_da_afirmacao(texto: str, achado: "re.Match") -> str:
    """O verbo e o que vem depois dele, até o fim da oração — onde mora o objeto."""
    resto = texto[achado.end():achado.end() + 80]
    corte = _FIM_DA_ORACAO.search(resto)
    return achado.group(0) + (resto[:corte.start()] if corte else resto)


def _houve_handoff_confirmado(resultados_das_tools: Optional[Iterable]) -> bool:
    """Alguma ferramenta de handoff devolveu SUCESSO neste turno?

    Lê o conteúdo das `ToolMessage` do turno. `HANDOFF_OK` é um carimbo que só
    a própria ferramenta escreve, no caminho em que `avisado` é verdadeiro —
    por isso ele serve de âncora e uma frase em português não serve.
    """
    for msg in resultados_das_tools or []:
        nome = str(getattr(msg, "name", "") or "")
        if nome not in _TOOLS_DE_HANDOFF:
            continue
        if "HANDOFF_OK" in str(getattr(msg, "content", "") or ""):
            return True
    return False


#: 🔴 SPEC-125 Y2 (red team B3) — o que se diz no lugar da PARTE sem âncora quando
#: o resto da frase é um acionamento VERDADEIRO. Sem verbo de transferência no
#: passado e sem "atendimento humano" (o guarda `test_as_respostas_honestas…`).
NOTA_DA_EQUIPE_SEM_CONFIRMACAO = (
    "Quanto à equipe da corretora, ainda não tenho a confirmação de que ela "
    "está com o seu caso — sigo com você por aqui.")
NOTA_DO_ACIONAMENTO_SEM_CONFIRMACAO = (
    "O que mais eu tinha mencionado ainda não tem confirmação, então não vou te "
    "dizer que já está feito.")

_RX_FRASE = re.compile(r"[^.!?\n]+[.!?]*")
_RX_ENTRE_ORACOES = re.compile(r"(\s*[,;—]\s*|\s+e\s+)")


def _cortar_oracoes(texto: str, trechos: list) -> str:
    """Tira do texto as ORAÇÕES que contêm algum dos trechos `(início, fim)` —
    e a frase inteira, se não sobrar oração nenhuma. **PURA.**"""
    saida = []
    for frase in _RX_FRASE.finditer(texto):
        a, b = frase.span()
        if not any(i < b and f > a for i, f in trechos):
            saida.append(frase.group(0).strip())
            continue
        corpo = frase.group(0)
        final = re.search(r"[.!?]+\s*$", corpo)
        pontuacao = final.group(0).strip() if final else ""
        partes = _RX_ENTRE_ORACOES.split(corpo[: final.start()] if final else corpo)
        mantidas, pos, separador = [], a, ""
        for k, parte in enumerate(partes):
            ini, fim = pos, pos + len(parte)
            pos = fim
            if k % 2 == 1:          # separador
                separador = parte
                continue
            if not parte.strip() or any(i < fim and f > ini for i, f in trechos):
                continue
            mantidas.append((separador if mantidas else "") + parte)
        resto = "".join(mantidas).strip()
        if resto:
            saida.append(resto[0].upper() + resto[1:] + (pontuacao or "."))
    return " ".join(p for p in saida if p).strip()


# ---------------------------------------------------------------------------
# 🔴 SPEC-126 U4 (D4 · T5) — "CANCELEI" TAMBÉM É AÇÃO, e nenhuma ferramenta cancela
# ---------------------------------------------------------------------------
#
# D4 do Founder (02/10/2026): depois de acionar, o agente NÃO promete cancelar — chama a pessoa
# da corretora, que cancela com a seguradora. 📊 `grep -n cancel insurer_dispatch_tool.py` só acha
# o MODO TESTE e uma objeção: não existe ferramenta que cancele. Logo "Pronto, cancelei o guincho"
# é sempre falso — e é a frase que faz o segurado ir embora com o prestador ainda a caminho.
#
# A regra é a mesma do acionamento (T5): a frase só sobrevive com o CARIMBO da ferramenta que
# cancelou. Hoje o dicionário é VAZIO de propósito; a ferramenta de cancelar (pendência da SPEC-126,
# "cancelar sozinho") entra aqui com o literal dela — e o guarda do teste continua valendo.
CARIMBOS_DE_CANCELAMENTO: dict = {}

#: Só AFIRMAÇÃO no passado ou no estado ("cancelei", "está cancelado", "foi cancelado", "acabei de
#: cancelar", "cancelamento feito"). ⛔ Ficam livres: a negação ("ainda não está cancelado", "não
#: cancelei"), a intenção ("vou chamar a pessoa para cancelar") e a pergunta ("quer cancelar?").
_NAO = r"(?<!n[ãa]o )(?<!nem )"
_AFIRMACOES_DE_CANCELAMENTO = re.compile(
    r"(?i)"
    + _NAO + r"\bcancel(?:ei|amos)\b"
    + r"|" + _NAO + r"\bacab(?:ei|o|amos)\s+de\s+cancelar\b"
    # ("está/foi/ficou cancelado" mudou para `_participio_afirmado`, que lê também a pergunta, o
    #  modal e o status do sistema — CONSERTO X)
    + r"|" + _NAO + r"\bcancelamento\s+(?:j[áa]\s+)?(?:foi\s+|est[áa]\s+)?"
      r"(?:feito|realizado|efetuado|confirmado|conclu[íi]do)\b"
    # 🔴 SPEC-126 CONSERTO X (RT-B1) — o FEITO em 1ª pessoa sem o verbo "cancelei": 📊 "Consegui
    #    cancelar o guincho", "Desmarquei o guincho", "Dispensei o reboque" saíam intactos.
    + r"|" + _NAO + r"\b(?:consegui|conseguimos|pude|pudemos)\s+(?:j[áa]\s+)?cancelar\b"
    + r"|" + _NAO + r"\b(?:desmarquei|desmarcamos|dispensei|dispensamos|suspendi|suspendemos)\b"
    # o cancelamento PEDIDO/REGISTRADO por ele ("Solicitei o cancelamento", "Já pedi pra seguradora
    # cancelar", "O cancelamento já foi solicitado à seguradora") — também é ação afirmada (T5).
    + r"|" + _NAO + r"\b(?:pedi|pedimos|solicitei|solicitamos|registrei|registramos|enviei|mandei"
      r"|encaminhei|encaminhamos|fiz|fizemos|abri)\s+(?:\S+\s+){0,4}?cancelamento\b"
    + r"|" + _NAO + r"\b(?:pedi|pedimos|solicitei|solicitamos)\s+(?:\S+\s+){0,4}?"
      r"(?:pra|para|que)\s+(?:\S+\s+){0,2}?cancel(?:ar|e|em)\b"
    + r"|" + _NAO + r"\bcancelamento\s+(?:\S+\s+){0,3}?(?:j[áa]\s+)?(?:foi|est[áa]|ficou)\s+"
      r"(?:solicitado|pedido|enviado|registrado|encaminhado|efetivado|aprovado|aceito)\b")

#: 🔴 SPEC-126 CONSERTO X (RT-B1) — o PARTICÍPIO solto ("Pronto, cancelado!", "Cancelado ✅", "Pedido
#: cancelado com sucesso.", "o guincho foi dispensado"). 📊 Era a forma mais provável de um LLM em PT-BR
#: e nenhuma regra acima a via. Lido pela FORMA, não por lista: vale como afirmação de feito, salvo
#: quando a oração o nega, pergunta, põe em modal/futuro ou atribui a INTENÇÃO a alguém (abaixo).
_RX_PARTICIPIO_DE_CANCELAR = re.compile(r"(?i)\b(?:cancelad|desmarcad|dispensad)[oa]s?\b")
#: a NEGAÇÃO na mesma oração ("ainda não está cancelado", "o guincho não foi cancelado").
_RX_NEGA_NA_ORACAO = re.compile(r"(?i)\b(?:n[ãa]o|nem|nunca|jamais)\b")
#: a INTENÇÃO de alguém, não o feito ("você quer o guincho cancelado").
_RX_INTENCAO_NA_ORACAO = re.compile(
    r"(?i)\b(?:quer|quiser|queria|querem|deseja|desejar|gostaria|prefere|preferir|precisa|precisar)\b")
#: o MODAL/futuro logo antes do particípio ("vai ser cancelado", "para ficar cancelado", "se for").
_MODAIS_ANTES_DO_PARTICIPIO = frozenset({
    "ser", "seja", "sejam", "for", "forem", "esteja", "estejam", "estiver", "estiverem", "sera",
    "será", "serao", "serão", "seria", "seriam", "ficar", "fique", "fiquem", "ficara", "ficará",
    "deixar", "deixo", "deixe"})
#: constante_justificada: o STATUS que o SISTEMA informa (a apólice/parcela cancelada pela seguradora)
#: não é ação do agente — "Sua apólice consta como cancelada" é fato da consulta, e reescrevê-lo para
#: "Ainda não está cancelado" diria ao segurado o contrário do sistema (§9.5).
_RX_STATUS_DO_SISTEMA = re.compile(
    r"(?i)\b(?:ap[óo]lice|seguro|contrato|proposta|parcela|boleto|cart[ãa]o|cobran[çc]a|d[ée]bito"
    r"|plano|endosso)s?\b")
_RX_FIM_DE_ORACAO = re.compile(r"[,;:—–()\n]")
#: 🔴 SPEC-126 CONSERTO 2 (pend. 3 da confirmação) — o FATO DE TERCEIRO tem a forma da passiva com o
#: AGENTE nomeado, e o agente não é o atendimento: 📊 sonda do juiz (02/10) — "O agendamento da vistoria
#: foi cancelado PELA SEGURADORA", "O sinistro foi cancelado PELA SEGURADORA em 10/09" eram reescritos
#: para "Ainda não está cancelado…" (o contrário do fato, §9.5). constante_justificada: só quem informa
#: status ao atendimento (a seguradora, o sistema, a central/assistência dela) e o "consta/aparece como"
#: da consulta. ⛔ "pela corretora/pela equipe/por mim" NÃO está aqui: é exatamente o cancelamento que
#: só uma pessoa faz e que o modelo inventaria.
_RX_AGENTE_DE_FORA = re.compile(
    r"(?i)\bpel[oa]s?\s+(?:pr[óo]pri[oa]\s+)?(?:seguradora|sistema|central|assist[êe]ncia)\b")
_RX_CONSTA_COMO = re.compile(r"(?i)\b(?:consta|constam|aparece|aparecem)\s+(?:\S+\s+)?como\s+$")
#: o SUJEITO que é o anterior/antigo ("o prestador ANTERIOR foi dispensado e um novo está a caminho"):
#: a troca de prestador quem faz é a seguradora — o agente não tem ferramenta que dispense nem que mande
#: outro, então quem relata a troca está relatando o que a seguradora informou.
_RX_SUJEITO_ANTERIOR = re.compile(r"(?i)\b(?:anterior|antig[oa])\s+(?:\S+\s+){0,2}$")
#: …e o RELATO DO PRÓPRIO FEITO ("Pronto, o guincho foi cancelado pela seguradora") não ganha a exceção:
#: "pronto/feito/tudo certo" no começo da frase é o agente anunciando o que diz ter feito.
_RX_ANUNCIO_DE_FEITO = re.compile(
    r"(?i)^\W*(?:pronto|prontinho|feito|tudo\s+certo|certo|ok|perfeito|resolvido|beleza)\b")
#: 🔴 CONSERTO 5 (BE-2) — e no começo da RESPOSTA, não só da frase: 📊 "Feito! O guincho foi cancelado
#:    pela seguradora." passava intacta (o "Feito!" é outra frase). constante_justificada: só quando a
#:    1ª frase é SÓ o anúncio ("Feito!", "Tudo bem.", "Pronto!") — "Certo, vou verificar." não anuncia
#:    feito nenhum e não tira a exceção do fato de terceiro das frases seguintes. E essa frase sai junto
#:    quando a afirmação que ela anunciava sai ("Feito! Ainda não está cancelado" se contradiz).
#: 🔴 CONSERTO 6 (pend. 1 do juiz final) — no nível da RESPOSTA, só o anúncio de FEITO: 📊 "Certo! O
#:    sinistro foi cancelado pela seguradora em 10/09.", "Ok. O prestador anterior foi dispensado pela
#:    seguradora…", "Tudo bem. A vistoria foi desmarcada pela seguradora; ela vai te ligar…" passaram a ser
#:    reescritas pelo conserto 5 (o contrário do fato, §9.5). constante_justificada: "certo/ok/tudo
#:    bem/perfeito/beleza/combinado" são CONCORDÂNCIA com o segurado, não relato de algo feito; "pronto/
#:    prontinho/feito/resolvido" relatam o feito. O BE-2 ("Tudo bem. O guincho foi cancelado…") continua
#:    coberto pela regra do SUJEITO (`_RX_SUJEITO_E_O_SERVICO`), não por esta.
_RX_SO_ANUNCIO = re.compile(r"(?i)^\W*(?:pronto|prontinho|feito|resolvido)\W*$")
#: a frase que é SÓ abertura (o anúncio OU a concordância) sai junto quando a afirmação que vinha
#: depois dela é reescrita — "Tudo bem. Ainda não está cancelado…" soa como concordar com o pedido.
_RX_SO_ABERTURA = re.compile(
    r"(?i)^\W*(?:pronto|prontinho|feito|tudo\s+certo|tudo\s+bem|certo|certinho|ok|perfeito|resolvido"
    r"|beleza|combinado)\W*$")


def _resposta_abre_anunciando(texto: str) -> bool:
    """A 1ª frase da RESPOSTA é só o anúncio do feito? **PURA.**"""
    primeira = _RX_FRASE.search(str(texto or ""))
    return bool(primeira and _RX_SO_ANUNCIO.search(primeira.group(0)))
#: 🔴 SPEC-126 CONSERTO 5 (BE-2 do juiz de escalação) — o fato de terceiro olhava QUEM cancelou, não O
#:    QUÊ. 📊 `escal126/compara.py` (03/10): "O guincho foi cancelado pela seguradora", "Seu guincho foi
#:    cancelado pelo sistema", "Seu guincho consta como cancelado", "O guincho anterior foi cancelado",
#:    "Seu chaveiro foi dispensado pela assistência" — 9 de 9 passavam intactas, e é a mentira da D4.
#:    constante_justificada: o SUJEITO que é o serviço/pedido DESTE acionamento — os serviços que a
#:    ferramenta aciona e as palavras com que o atendimento nomeia o pedido. Com ele, a exceção só vale se
#:    uma ferramenta DO TURNO trouxe o status (`_status_de_cancelado_na_tool`); sem como saber, reescreve.
#:    ⛔ Ficam fora de propósito: "prestador ANTERIOR/antigo" (a troca que a seguradora relata — pend. 3),
#:    "sinistro", "vistoria/agendamento" (a agenda), "protocolo" e "assistência" (o agente da passiva).
_RX_SUJEITO_E_O_SERVICO = re.compile(
    r"(?i)\b(?:guinchos?|reboques?|socorros?|chaveiros?|t[ée]cnicos?|eletricistas?|encanador(?:es)?"
    r"|vidraceiros?|mec[âa]nicos?|prestador(?:es)?(?!\s+(?:anterior|antig))|pedidos?|acionamentos?"
    r"|chamados?|servi[çc]os?|solicita[çc](?:[ãa]o|[õo]es)|atendimentos?)\b")
#: os auxiliares/advérbios que sobram numa oração cortada pela vírgula ("O guincho, infelizmente, FOI
#: cancelado") — quando só eles sobram, o sujeito está antes, na frase.
_SO_AUXILIARES = frozenset({
    "foi", "foram", "esta", "está", "estao", "estão", "ficou", "ficaram", "ja", "já", "infelizmente",
    "tambem", "também", "entao", "então", "agora", "consta", "constam", "aparece", "aparecem", "como",
    "e", "mas", "porem", "porém", "que", "inclusive", "acabou", "de", "ser"})
#: o STATUS de cancelado trazido por uma FERRAMENTA do turno (📊 `portal_params.py:1810`
#: "A seguradora mostra este atendimento como cancelado"; o agregado `Cancelado=true`). ⛔ "será
#: cancelado" (o aviso do modo teste do acionamento) é futuro, não status.
_RX_STATUS_DE_CANCELADO = re.compile(
    r"(?i)\b(?:como|est[áa]|consta|constam|aparece|status|situa[çc][ãa]o)\W{0,3}"
    r"(?:cancelad|dispensad|desmarcad)[oa]s?\b"
    r"|\b(?:cancelad|dispensad|desmarcad)[oa]s?\W{0,3}[=:]\s*\W?(?:true|sim|1)\b")
#: 🔴 CONSERTO 6 (pend. 3 do juiz final) — só a ferramenta de ACIONAMENTO sabe o status DO SERVIÇO.
#:    📊 sonda do juiz: uma ToolMessage de apólice com "status: cancelada" deixava "O guincho foi
#:    cancelado pela seguradora." intacta; o infocap imprime "- Situacao: {policy_status}"
#:    (`infocap_tool.py:2248/2297`) e "Apolice consta como cancelada." (`infocap_connector.py:4043`).
#:    constante_justificada: os `name` reais (`insurer_dispatch_tool.py:1800`, `portal_tool.py:173`);
#:    o "como cancelado" do portal chega pelo `format_result` → `texto_da_parada("atendimento_cancelado")`
#:    (`portal_params.py:1809`). Ferramenta nova que traga status do serviço entra aqui com o nome dela.
TOOLS_DO_STATUS_DO_SERVICO = frozenset({"insurer_dispatch", "portal_action"})


def _status_de_cancelado_na_tool(resultados_das_tools: Optional[Iterable]) -> bool:
    """Alguma ferramenta de ACIONAMENTO deste turno trouxe o status "cancelado"? **PURA.**"""
    return any(str(getattr(m, "name", "") or "") in TOOLS_DO_STATUS_DO_SERVICO
               and _RX_STATUS_DE_CANCELADO.search(str(getattr(m, "content", "") or ""))
               for m in (resultados_das_tools or []))


def _sujeito_e_o_servico(antes: str, oracao_antes: str, palavras: list) -> bool:
    """O que se diz cancelado é o serviço/pedido DESTE acionamento? Lê a oração antes do particípio;
    se ela é só auxiliar ("…, foi cancelado"), lê a frase até ali. **PURA.**"""
    if any(p not in _SO_AUXILIARES for p in palavras):
        return bool(_RX_SUJEITO_E_O_SERVICO.search(oracao_antes))
    return bool(_RX_SUJEITO_E_O_SERVICO.search(antes))


def _participio_afirmado(texto: str, *, anunciado: bool = False, status_na_tool: bool = False) -> bool:
    """Há um particípio de cancelar AFIRMADO como feito? **PURA.**

    `anunciado`: a RESPOSTA abre anunciando o feito ("Feito! …") — vale para todas as frases dela.
    `status_na_tool`: uma ferramenta do turno trouxe o status "cancelado" (só ela sustenta o fato de
    terceiro sobre o serviço/pedido deste acionamento)."""
    for frase in _RX_FRASE.finditer(texto):
        corpo = frase.group(0)
        if corpo.rstrip().endswith("?"):
            continue                      # pergunta ("O guincho está cancelado?")
        for m in _RX_PARTICIPIO_DE_CANCELAR.finditer(corpo):
            antes = corpo[: m.start()]
            corte = max((x.end() for x in _RX_FIM_DE_ORACAO.finditer(antes)), default=0)
            oracao_antes = antes[corte:]
            depois = corpo[m.end():]
            fim = _RX_FIM_DE_ORACAO.search(depois)
            oracao = oracao_antes + m.group(0) + (depois[: fim.start()] if fim else depois)
            palavras = re.findall(r"[^\W\d_]+", oracao_antes.lower())
            if _RX_NEGA_NA_ORACAO.search(oracao_antes) or _RX_INTENCAO_NA_ORACAO.search(oracao_antes):
                continue
            if palavras and palavras[-1] in _MODAIS_ANTES_DO_PARTICIPIO:
                continue
            if _RX_STATUS_DO_SISTEMA.search(oracao):
                continue
            # CONSERTO 2 (pend. 3): o fato de TERCEIRO — passiva com o agente de fora, "consta como",
            # o sujeito anterior — salvo quando a frase (CONSERTO 5: ou a resposta) abre anunciando o
            # feito ("Pronto, …"), e salvo (CONSERTO 5) quando o que se diz cancelado é o serviço/pedido
            # deste acionamento sem uma ferramenta do turno que traga esse status.
            if (not anunciado and not _RX_ANUNCIO_DE_FEITO.search(corpo)
                    and (status_na_tool or not _sujeito_e_o_servico(antes, oracao_antes, palavras))
                    and (
                        _RX_AGENTE_DE_FORA.search(depois[: fim.start()] if fim else depois)
                        or _RX_CONSTA_COMO.search(oracao_antes)
                        or _RX_SUJEITO_ANTERIOR.search(re.sub(r"(?i)\b(?:foi|foram|est[áa]|est[ãa]o|ficou|"
                                                              r"ficaram|j[áa])\s+", "", oracao_antes)))):
                continue
            return True
    return False

#: O que se diz no lugar. Sem verbo de transferência no passado e sem afirmar cancelamento (o
#: guarda confere que ela não se auto-reescreve).
NOTA_DO_CANCELAMENTO_SEM_FERRAMENTA = (
    "Ainda não está cancelado: quem cancela com a seguradora é uma pessoa da corretora, e o "
    "serviço só para quando ela confirmar.")


def afirma_cancelamento(texto: str, resultados_das_tools: Optional[Iterable] = None, *,
                        _anunciado: Optional[bool] = None) -> bool:
    """A resposta afirma que um cancelamento ACONTECEU (ou que ELE o pediu à seguradora)?

    CONSERTO 5: `resultados_das_tools` (as ToolMessages do turno) só servem para o fato de terceiro
    sobre o serviço deste acionamento; sem elas, o lado seguro (afirma). `_anunciado` é passado pelo
    fiscal ao reler frase por frase — o "Feito!" do começo da RESPOSTA vale para todas."""
    texto = str(texto or "")
    # a PERGUNTA não afirma nada ("O guincho está cancelado?" — 📊 era reescrita na U4)
    afirmativas = " ".join(f.group(0) for f in _RX_FRASE.finditer(texto)
                           if not f.group(0).rstrip().endswith("?"))
    anunciado = _resposta_abre_anunciando(texto) if _anunciado is None else _anunciado
    return bool(_AFIRMACOES_DE_CANCELAMENTO.search(afirmativas)) or _participio_afirmado(
        texto, anunciado=anunciado, status_na_tool=_status_de_cancelado_na_tool(resultados_das_tools))


def _houve_cancelamento_confirmado(resultados_das_tools: Optional[Iterable]) -> bool:
    for msg in resultados_das_tools or []:
        carimbos = CARIMBOS_DE_CANCELAMENTO.get(str(getattr(msg, "name", "") or ""))
        if carimbos and any(c in str(getattr(msg, "content", "") or "") for c in carimbos):
            return True
    return False


def _sem_o_cancelamento_sem_ancora(texto: str, resultados: list) -> str:
    """Tira as FRASES que afirmam cancelamento sem carimbo e põe a nota honesta no fim. **PURA.**
    A frase inteira sai (não só a oração): "cancelei o guincho, pode ficar tranquilo" — o
    "pode ficar tranquilo" é consequência do cancelamento inventado."""
    if not afirma_cancelamento(texto, resultados) or _houve_cancelamento_confirmado(resultados):
        return texto
    anunciado = _resposta_abre_anunciando(texto)
    # CONSERTO 5: cada frase é relida com o anúncio da RESPOSTA, e a frase que é SÓ o anúncio
    # ("Feito!") sai com a afirmação que anunciava — "Feito! Ainda não está cancelado" se contradiz.
    sobra = " ".join(f.group(0).strip() for f in _RX_FRASE.finditer(texto)
                     if not afirma_cancelamento(f.group(0), resultados, _anunciado=anunciado)
                     and not _RX_SO_ABERTURA.search(f.group(0))).strip()
    logger.error("[HANDOFF] 🔴 resposta afirmava CANCELAMENTO sem ferramenta — reescrita (D4/T5)")
    return " ".join(p for p in (sobra, NOTA_DO_CANCELAMENTO_SEM_FERRAMENTA) if p)


def guardar_a_verdade_do_handoff(resposta: str, resultados_das_tools=None) -> str:
    """O fiscal. Devolve a resposta intacta, ou a versão honesta.

    Mesma forma de `_guard_infocap_policy_final_response` (`nodes.py:236`), e
    no mesmo ponto do fluxo: um fiscal determinístico depois do modelo. Não é
    motor novo — é a segunda instância de um padrão que o produto já tem.
    """
    texto = str(resposta or "")
    if not texto.strip():
        return texto
    # 🔴 SPEC-126 U4 — o cancelamento primeiro: a frase que ele tira pode carregar também uma
    #    transferência ("cancelei e avisei a equipe"), e o resto segue para as âncoras de sempre.
    sem_cancelamento = _sem_o_cancelamento_sem_ancora(texto, list(resultados_das_tools or []))
    saida = _guardar_a_transferencia(sem_cancelamento, resultados_das_tools)
    if sem_cancelamento != texto and NOTA_DO_CANCELAMENTO_SEM_FERRAMENTA not in saida:
        # a transferência sem âncora trocou o texto inteiro: a verdade do cancelamento volta junto
        saida = "%s %s" % (saida, NOTA_DO_CANCELAMENTO_SEM_FERRAMENTA)
    return saida


def _guardar_a_transferencia(texto: str, resultados_das_tools=None) -> str:
    """As âncoras de PESSOA e de ACIONAMENTO (SPEC-125 S1/Y2/Z) — o fiscal de antes da U4."""
    if not texto.strip():
        return texto
    if not afirma_transferencia(texto):
        return texto
    resultados = list(resultados_das_tools or [])
    handoff_ok = _houve_handoff_confirmado(resultados)
    acionados = servicos_acionados(resultados)

    # 🔴 SPEC-125 S1 + Y2 — CADA afirmação precisa da SUA âncora.
    #   de PESSOA       → `HANDOFF_OK`
    #   de ACIONAMENTO  → o carimbo do acionamento DO SERVIÇO que ela nomeia (ou de
    #                     qualquer um, se não nomeia serviço); sem serviço nomeado,
    #                     o `HANDOFF_OK` também a sustenta (o gesto foi o handoff).
    pessoa_sem, acion_sem, acion_com = [], [], []
    for a in _AFIRMACOES_DE_TRANSFERENCIA.finditer(texto):
        if _afirmacao_de_pessoa(texto, a):
            if not handoff_ok:
                pessoa_sem.append(a)
            continue
        servico = servico_nomeado(_oracao_da_afirmacao(texto, a))
        if acionados and (_QUALQUER in acionados or servico is None or servico in acionados):
            acion_com.append(a)
        elif handoff_ok and servico is None:
            continue
        else:
            acion_sem.append(a)
    if not pessoa_sem and not acion_sem:
        return texto

    # 🔴 Y2 (red team B3) — "Já acionei o guincho pela Porto e avisei a corretora":
    #    o guincho saiu DE VERDADE. Reescrever a frase inteira para "Registrei seu
    #    pedido de atendimento humano" trocava a notícia verdadeira por uma falsa.
    #    Fica a oração que tem âncora; sai só a que não tem, e diz-se a verdade sobre ela.
    if acion_com:
        cortado = _cortar_oracoes(texto, [a.span() for a in pessoa_sem + acion_sem])
        if cortado and _AFIRMACOES_DE_TRANSFERENCIA.search(cortado):
            notas = (([NOTA_DA_EQUIPE_SEM_CONFIRMACAO] if pessoa_sem else [])
                     + ([NOTA_DO_ACIONAMENTO_SEM_CONFIRMACAO] if acion_sem else []))
            logger.error("[HANDOFF] 🔴 frase mista: mantido o acionamento confirmado, "
                         "retirada a parte sem âncora (%s)",
                         "pessoa" if pessoa_sem else "acionamento de outro serviço")
            return " ".join([cortado] + notas)

    # 🔴 SPEC-125 CONSERTO Z · N4 do laudo de confirmação — houve acionamento REAL (o
    #    guincho saiu) e a frase inventou OUTRO ("Também já acionei o chaveiro"): a frase
    #    genérica ("Ainda não tenho a confirmação de que o acionamento saiu") fazia o
    #    segurado ler que o GUINCHO não saiu. Diz-se o que de fato saiu e o resto não.
    if acionados and not pessoa_sem:
        # a FRASE inteira sai (não só a oração): "…acionei o chaveiro, chega em 40 min" —
        # o "chega em 40 min" é do chaveiro inventado, e ficaria como promessa solta.
        trechos = [a.span() for a in acion_sem]
        sobra = " ".join(f.group(0).strip() for f in _RX_FRASE.finditer(texto)
                         if not any(i < f.end() and j > f.start() for i, j in trechos)).strip()
        partes = [sobra] if sobra and not _AFIRMACOES_DE_TRANSFERENCIA.search(sobra) else []
        logger.error("[HANDOFF] 🔴 acionamento de outro serviço sem âncora — mantido o "
                     "acionamento real (%s), retirada a parte inventada",
                     ",".join(sorted(acionados)))
        return " ".join([frase_do_que_saiu(acionados)] + partes
                        + [NOTA_DO_ACIONAMENTO_SEM_CONFIRMACAO])

    logger.error(
        "[HANDOFF] 🔴 resposta afirmava %s SEM confirmação — reescrita. Trecho: %r",
        "transferência" if pessoa_sem else "acionamento", texto[:160])
    return RESPOSTA_HONESTA if pessoa_sem else RESPOSTA_HONESTA_DO_ACIONAMENTO


def frase_do_que_saiu(acionados: set) -> str:
    """A frase com o que o carimbo PROVA que saiu (N4). **PURA.** Sem verbo de
    transferência no passado (o fiscal não a reescreve; o guarda confere)."""
    nomes = sorted(s.replace("_", " ") for s in (acionados or set()) if s != _QUALQUER)
    if not nomes:
        return "O pedido que eu confirmei com a seguradora continua valendo."
    lista = nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]
    return "O pedido de %s com a seguradora está confirmado." % lista
