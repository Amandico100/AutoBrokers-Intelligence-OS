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
# e o modelo a reescrevia no tom da Saionara. Frase pronta e frase inventada
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
_AFIRMACOES_DE_TRANSFERENCIA = re.compile(
    r"(?ix)"
    r"(?:"
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
    r"|"
    # (d) a equipe ja tem o caso
    r"\ba\s+equipe\s+(?:j[áa]\s+)?(?:recebeu|est[áa]\s+com|foi\s+avisada)\b"
    r"|"
    # (e) futuro-certo em nome de terceiros
    r"\b(?:eles?|ela|a\s+equipe)\s+(?:v[ãa]o|vai)\s+"
    r"(?:entrar\s+em\s+contato|te\s+chamar|falar\s+com\s+voc[eê]|retornar)"
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


def afirma_transferencia(texto: str) -> bool:
    """A resposta afirma, no passado, que a transferência aconteceu?"""
    return bool(_AFIRMACOES_DE_TRANSFERENCIA.search(str(texto or "")))


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
    if _houve_handoff_confirmado(resultados_das_tools):
        return texto

    logger.error(
        "[HANDOFF] 🔴 resposta afirmava transferência SEM handoff confirmado — "
        "reescrita. Trecho: %r", texto[:160])
    return RESPOSTA_HONESTA
