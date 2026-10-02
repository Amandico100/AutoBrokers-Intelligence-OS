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
    for msg in resultados_das_tools or []:
        carimbos = CARIMBOS_DE_ACIONAMENTO.get(str(getattr(msg, "name", "") or ""))
        if not carimbos:
            continue
        conteudo = str(getattr(msg, "content", "") or "")
        if any(c in conteudo for c in carimbos):
            return True
    return False


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


def guardar_a_verdade_do_handoff(resposta: str, resultados_das_tools=None) -> str:
    """O fiscal. Devolve a resposta intacta, ou a versão honesta.

    Mesma forma de `_guard_infocap_policy_final_response` (`nodes.py:236`), e
    no mesmo ponto do fluxo: um fiscal determinístico depois do modelo. Não é
    motor novo — é a segunda instância de um padrão que o produto já tem.
    """
    texto = str(resposta or "")
    if not texto.strip():
        return texto
    if not afirma_transferencia(texto):
        return texto
    resultados = list(resultados_das_tools or [])
    if _houve_handoff_confirmado(resultados):
        return texto

    # 🔴 SPEC-125 S1 — cada afirmação precisa da SUA âncora. A de PESSOA só se
    # apoia em `HANDOFF_OK` (que já faltou, acima); a de ACIONAMENTO se apoia
    # no carimbo do acionamento. Uma frase mista ("acionei o guincho e avisei a
    # equipe") cai pela parte que não tem âncora.
    de_pessoa = [a for a in _AFIRMACOES_DE_TRANSFERENCIA.finditer(texto)
                 if _afirmacao_de_pessoa(texto, a)]
    if not de_pessoa and _houve_acionamento_confirmado(resultados):
        return texto

    logger.error(
        "[HANDOFF] 🔴 resposta afirmava %s SEM confirmação — reescrita. Trecho: %r",
        "transferência" if de_pessoa else "acionamento", texto[:160])
    return RESPOSTA_HONESTA if de_pessoa else RESPOSTA_HONESTA_DO_ACIONAMENTO
