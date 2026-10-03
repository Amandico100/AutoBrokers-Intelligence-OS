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


#: 🔴 QUANTO TEMPO SE ESPERA A SEGURADORA, em horas, quando ela não prometeu
#: nada. 📊 **48 h, medido:** o caso do pós-acionamento do acervo dura 6,9 dias
#: (mediana, `reality-report-0971.md`). ⛔ O padrão anterior era +24 h, e com o
#: teto de avisos do vigia isso fechava o atendimento **25 h depois do
#: protocolo**, com a seguradora ainda devendo resposta ([2] do red team).
PRAZO_POS_ACIONAMENTO_HORAS = 48


def prazo_pos_acionamento_horas(companhia: Any) -> int:
    """`acionamento_profile.prazo_pos_acionamento_horas` — **PURA**.

    ⚠️ Ausente = `PRAZO_POS_ACIONAMENTO_HORAS`. Uma corretora que atende
    seguradora lenta escreve 96; nenhuma precisa escrever 48 para ter o que a
    SPEC promete. ⛔ Valor ilegível ou ≤ 0 também cai no padrão: um prazo zero
    faria a espera nascer vencida e o vigia cobrar no primeiro tick.
    """
    perfil = (companhia or {}).get("acionamento_profile") if isinstance(companhia, dict) else None
    perfil = perfil if isinstance(perfil, dict) else {}
    try:
        horas = int(float(str(perfil.get("prazo_pos_acionamento_horas")).strip()))
    except Exception:  # noqa: BLE001
        return PRAZO_POS_ACIONAMENTO_HORAS
    return horas if horas > 0 else PRAZO_POS_ACIONAMENTO_HORAS


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

#: 🔴 SPEC-126 U4 — o LUGAR de risco, para as regras de K1 abaixo. ⚠️ Lugar sozinho não basta
#:    ("a vistoria é na rodovia" é agenda): K1 exige a PESSOA nele (sozinha, com criança, à noite).
_LUGAR_DE_RISCO = r"(?:rodovia|estrada|pista|acostamento|\bbr\b)"

#: 🔴 SPEC-126 U4 (D4) — os SERVIÇOS que se cancelam na seguradora. Cancelar UM DELES é K3 mesmo
#:    quando a mesma frase cancela também a vistoria ("cancela a vistoria e o guincho tb"): o que já
#:    saiu para a seguradora pesa mais que a agenda. ⛔ `vistoria/agendamento/visita/horario/data`
#:    NÃO estão aqui de propósito — são a agenda da regra `C`.
_SERVICO_ACIONADO = (r"(?:guincho|reboque|prestador|tecnico|chaveiro|eletricista|encanador|servico"
                     r"|chamado|acionamento|socorro|assistencia)")

#: 🔴 SPEC-126 U4 — o VERBO de cancelar, nas formas em que o segurado PEDE ou DIZ que cancela
#:    ("cancela", "cancelem", "cancele", "cancelar", "cancelo", "cancelei") e o substantivo só
#:    quando PEDIDO ("quero o cancelamento"). ⛔ Ficam de fora, medido no acervo (📊 02/10, 15.699
#:    falas `user`): "cancelou?" / "processo de cancelamento" / "taxa de cancelamento" / "evitar o
#:    cancelamento" — são pergunta de status ou conversa de inadimplência, não pedido; e a negação
#:    ("não cancela não, já chegou", "não precisa cancelar") é o contrário de cancelar.
_CANCELAR = (r"(?<!nao )(?<!nao precisa )(?<!nao precisam )(?<!sem )(?<!para nao )(?<!pra nao )"
             # CONSERTO X (RT-B2): "cancelaaaa" (a letra esticada do WhatsApp) caía em `N`
             r"\bcancel(?:a+|ar|em|e|o|ei|amos)\b"
             r"|\b(?:quero|queria|gostaria de|pedir|pedi|pediu|solicitar|solicito|solicitei|fazer|faz"
             r"|faca|pedido de) (?:o |um )?cancelamento\b")

#: 🔴 SPEC-126 CONSERTO X (RT-B2) — CANCELAR SEM O VERBO "cancelar". 📊 Sonda do red team (02/10,
#:    `rt126_probe1.py` §2): "esquece o guincho", "deixa pra lá", "dispensa/desmarca/suspende o guincho",
#:    "manda voltar o guincho", "não precisa mandar mais ninguém", "o guincho pode ir embora", "pode
#:    liberar o de vocês", "aborta" → `N` → a segunda chance mandava o agente "resolver sem pessoa" o
#:    que só a corretora executa, e o prestador seguia a caminho (D4).
#: A ESCOLHA (o OBJETO decide — documentada no teste `test_spec126_conserto_x_cancelar_sem_o_verbo`):
#:   ① o verbo de dispensar + um SERVIÇO até 5 palavras depois ("esquece o guincho") → K3. ⛔ Se no
#:     meio ele PEDE o serviço ("esquece aquilo, manda o guincho"), não é K3: o objeto era outro.
#:   ② "esquece"/"deixa pra lá"/"aborta" como a ÚLTIMA coisa do turno → K3. No pós-acionamento a
#:     última palavra dele, sem objeto, é sobre o serviço que está na rua; errar aqui chama UMA pessoa
#:     à toa, errar do outro lado deixa o guincho ir.  ⛔ "deixa pra lá, já entendi" (o objeto é a
#:     explicação) não termina no "deixa" e não casa.
#:   ③ "esquece"/"deixa pra lá" + o sinal de que se resolveu ("já resolvi", "o carro pegou") → K3.
_DISPENSAR = (r"(?:esquece|esquecer|esqueca|esquecam|deixa pra la|deixa para la|deixe pra la"
              r"|deixa quieto|dispensa|dispensar|dispense|dispensem|desmarca|desmarcar|desmarque"
              r"|desmarquem|suspende|suspender|suspenda|suspendam|aborta|abortar|aborte|manda voltar"
              r"|mande voltar|mandem voltar|manda embora|mande embora|pode liberar|podem liberar)")
#: o pedido do serviço no meio da frase desfaz o ① ("esquece aquilo, MANDA o guincho").
#: 🔴 SPEC-126 CONSERTO 2 (pend. 4 da confirmação) — o OBJETO do "esquece" acaba na PONTUAÇÃO da oração.
#:    📊 sonda do juiz (02/10): "esquece a placa que mandei, o guincho é pro outro carro" (CORREÇÃO de um
#:    dado) e "deixa pra lá, cadê o guincho?" (impaciência — ele quer o guincho) iam para a pessoa com o
#:    rótulo CANCELAMENTO: o ① contava o "guincho" da oração SEGUINTE como objeto do "esquece".
#:    constante_justificada: entre o verbo de dispensar e o serviço só cabem palavras da MESMA oração
#:    (sem `,.;:!?`) — "esquece o guincho", "dispensa o reboque, vou levar empurrando" continuam K3; o
#:    "esquece, …" sem objeto continua nas regras ② (última coisa) e ③ (+ o sinal de que se resolveu).
_SEP_NA_ORACAO = r"[^\w,.;:!?]+"
_SEM_PEDIR_O_SERVICO = (r"(?:(?!manda\b|mande\b|mandem\b|mandar\b|envia\b|envie\b|aciona\b|acione\b|chama\b)\w+"
                        + _SEP_NA_ORACAO + r")")
#: 🔴 SPEC-126 CONSERTO 5 (BE-1 do juiz de escalação) — a PONTUAÇÃO logo depois do verbo não muda o
#:    objeto. 📊 `escal126/compara.py` (03/10): "esquece... o guincho", "esquece: o guincho", "esquece, o
#:    guincho", "esquece. o guincho", "dispensa! o guincho", "deixa pra lá... o guincho já pode ir" eram
#:    K3 antes do conserto 2 e viraram `N` → segunda chance, prestador na rua (D4).
#:    constante_justificada: a pontuação vale SÓ colada ao verbo (nenhuma palavra entre o verbo e ela) e
#:    com, entre ela e o serviço, no máximo o artigo/possessivo/demonstrativo. ⛔ "esquece a PLACA que
#:    mandei, o guincho…" (a palavra antes da vírgula é o objeto) e "deixa pra lá, CADÊ o guincho?" (a
#:    palavra depois da vírgula não é determinante) continuam fora.
_DETERMINANTE = (r"(?:o|a|os|as|um|uma|seu|sua|seus|suas|meu|minha|meus|minhas|esse|essa|esses|essas"
                 r"|este|esta|aquele|aquela)")
_PONTUACAO_E_O_SERVICO = (r"\s*[,.;:!?…]+\s*(?:" + _DETERMINANTE + r"\s+){0,2}" + _SERVICO_ACIONADO + r"\b")
#: 🔴 CONSERTO 2 (pend. 5) — "esquece, ACHEI a chave" (o chaveiro na rua): achar/abrir é o "resolvi" do
#:    chaveiro. 📊 sonda do juiz: caía em `N` e a segunda chance resolvia sem pessoa o que só ela cancela.
_RESOLVEU = (r"(?:ja )?(?:resolvi|resolvemos|resolveu|consegui|conseguimos|conseguiu|pegou|funcionou"
             r"|deu certo|ligou|nao precisa|nao preciso|chegou (?:um|outro)"
             r"|achei|achamos|encontrei|encontramos|abri|abrimos|abriu)")
#: ⛔ O "esqueça" que NÃO é ordem: 📊 acervo (02/10, 15.773 falas `user`) — "não SE esqueça de buscar uma
#:    assistência", "caso TU esqueça" (subjuntivo/conselho, não dispensa). O sujeito/pronome antes desfaz.
_NAO_E_ORDEM = r"(?<!nao )(?<!se )(?<!tu )(?<!voce )(?<!vc )(?<!ele )(?<!ela )(?<!eu )"
_CANCELAR_SEM_O_VERBO = (
    _NAO_E_ORDEM + r"(?<!nao precisa )\b" + _DISPENSAR + _SEP_NA_ORACAO + _SEM_PEDIR_O_SERVICO + r"{0,5}?"
    + _SERVICO_ACIONADO + r"\b"
    + r"|" + _NAO_E_ORDEM + r"(?<!nao precisa )\b" + _DISPENSAR + _PONTUACAO_E_O_SERVICO
    + r"|" + _NAO_E_ORDEM + r"\b(?:esquece|esqueca|deixa pra la|deixa para la|deixe pra la|deixa quieto"
      r"|aborta)(?: (?:isso|tudo|entao|ai|mesmo|por favor|pf|pfv|blz|ta|ok|moco|moca|amigo|amiga))*\W*$"
    + r"|" + _NAO_E_ORDEM + r"\b(?:esquece|esqueca|deixa pra la|deixa para la|deixe pra la|deixa quieto)\b\W+"
      r"(?:\w+\W+){0,4}?" + _RESOLVEU + r"\b"
    + r"|\b(?:pode|podem) (?:liberar|dispensar|mandar embora|mandar voltar) (?:o|a|os|as) "
      r"(?:de voces|de vcs|de vc|seu|seus)\b"
    + r"|" + _SERVICO_ACIONADO + r"\W+(?:\w+\W+){0,3}?(?:pode|podem) ir embora\b"
    + r"|\bnao (?:manda|mande|mandem|envia|envie|enviem) mais\b"
      r"(?! (?:mensage|msg|audio|foto|document|nada|link|o link|isso))"
    + r"|\bnao (?:precisa|precisam) (?:mais )?(?:mandar|enviar) (?:mais )?ninguem\b"
    + r"|\bnao (?:precisa|precisam) (?:mandar|enviar|vir) (?:ninguem )?mais\b"
      r"(?! (?:mensage|msg|audio|foto|document|nada))"
    + r"|\bnao (?:vem|venha|venham) mais nao\b(?!\s*\?)")

_CASCATA: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("K1", re.compile(
        r"prestador (ainda )?nao (veio|chegou|apareceu)|ninguem (veio|chegou|apareceu)"
        r"|(esperei|esperou|esperando) (um monte|ate agora|horas)"
        r"|(estou|to) (parado |presa |preso )?(no acostamento|na pista|na estrada)"
        r"|local de risco|guincho nao (veio|chegou)"
        # 🔴 SPEC-126 U4 — laudo do juiz final da 125 (pend. 1): *"tô sozinha na rodovia à noite
        #    com duas crianças"* caía em `N`. A CONDIÇÃO de K1 (`CONDICAO_NO_ATENDIMENTO`) já dizia
        #    "pista, acostamento, à noite, sozinho"; a cascata não via nenhum dos três.
        #    ⛔ Não pega: "vou mandar os documentos à noite" (sem lugar), "a vistoria é na
        #    rodovia" (sem a pessoa parada nele).
        r"|sozinh[oa] (aqui )?(na|no|nessa|nesse) " + _LUGAR_DE_RISCO
        + r"|" + _LUGAR_DE_RISCO + r"\W+(\w+\W+){0,4}?(a noite|de noite|no escuro|sem luz)"
        + r"|(com|e) (as |os |meus |minhas |duas |dois |tres |uma |um |meu |minha )?"
          r"(criancas|crianca|bebes?|filhos pequenos|filha pequena|filho pequeno)\W+(\w+\W+){0,5}?"
        + _LUGAR_DE_RISCO
        + r"|" + _LUGAR_DE_RISCO + r"\W+(\w+\W+){0,5}?(com|e) (as |os |meus |minhas |duas |dois |tres )?"
          r"(criancas|crianca|bebes?)")),
    # 🔴 `mas nao foi` era largo demais — [4] do red team. 📊 *"a peça chegou
    #    mas não foi montada ainda"* virava RECLAMAÇÃO e ia para humano, quando
    #    é `H` (peça/previsão). ⚠️ O caso do acervo que a cascata precisa pegar
    #    é *"disseram que o prestador foi ao local mas nao foi"* — e ele casa
    #    por `muito abuso`, que vem na mesma rajada. O que se exige agora é a
    #    palavra da NEGAÇÃO DO SERVIÇO, não um "mas não foi" qualquer.
    ("K2", re.compile(
        r"muito abuso|absurdo|descaso|um desrespeito|pessimo|nao e verdade"
        r"|e mentira|mas nao (foi|apareceu) (ninguem|nada|feito|realizado|atendid)"
        r"|nao fizeram nada|reclama(cao|r) (disso|com)|to indignad"
        # 📊 *"nao quero mais esperar, ja faz 3 horas"* era K3 (`nao quero
        #    mais`) e virava "quer cancelar" — handoff pelo motivo errado.
        r"|nao (quero|aguento) mais esperar|nao aguento mais"
        # 🔴 SPEC-126 U4 — laudo do juiz final da 125 (pend. 1/2): o DANO feito pelo prestador, a
        #    COBRANÇA por fora e a AMEAÇA de processo caíam em `N`/`E` — e são relacionamento (R9).
        #    O dano exige QUEM fez (o prestador) E O QUÊ (o carro, a porta…): ⛔ "o guincho chegou,
        #    amassou nada não" não tem o objeto. A cobrança exige o verbo de cobrar: ⛔ "a franquia eu
        #    pago por fora?" é `E`. O processo exige a ameaça: ⛔ "processo do sinistro" não casa.
        r"|(guincheiro|prestador|motorista|tecnico|chaveiro|eletricista|encanador|guincho|reboque"
        r"|rapaz|moco|cara)\W+(\w+\W+){0,4}?(amassou|arranhou|riscou|danificou|quebrou|estragou"
        r"|amassaram|arranharam|riscaram|danificaram|quebraram|estragaram) "
        r"(o |a |meu |minha |o meu |a minha )?(carro|veiculo|moto|para-?choque|lataria|porta|roda"
        r"|para-brisa|retrovisor|portao|piso|parede|farol|capo)"
        r"|(cobr\w*|pediu|pediram|quer|querem|exigiu|exigiram)\W+(\w+\W+){0,5}?por fora\b"
        r"|(vou|vamos|irei|iremos|quero) (te |vos |voces |vcs )?(processar|denunciar|entrar na justica)"
        # ⛔ "procon"/"reclame aqui" SOZINHOS não: 📊 no acervo (02/10) eram um prêmio ("concorrendo
        #    ao prêmio reclame aqui", "o login do reclame aqui") e uma lista de serviços ("processos
        #    e procon"). Exige-se o GESTO de reclamar lá.
        r"|(vou|vamos|irei|ir|recorrer|denunciar|reclamar|abrir)\W+(\w+\W+){0,3}?(no |ao |pro |para o )procon\b"
        r"|(reclama\w*|registr\w*|abri|abrir|vou|vamos|irei|botar|colocar)\W+(\w+\W+){0,4}?"
        r"(no |na |pro |para o )reclame aqui")),
    # 🔴 CANCELAR A VISTORIA É AGENDA, NÃO DESISTÊNCIA — [4] do red team.
    #
    # ⛔ Esta regra vem ANTES de K3 de propósito, e é a razão de a cascata ter
    # ordem: `cancelar` sozinho casaria primeiro e mandaria para humano quem só
    # quer remarcar. 📊 *"preciso cancelar a vistoria e remarcar"* e *"gostaria
    # de cancelar o agendamento"* são as duas frases medidas.
    # ⚠️ E ela NÃO come *"quero cancelar o atendimento"* (turno 18 da fixture):
    # o que se cancela ali é o serviço, e isso tem consequência na apólice.
    #
    # 🔴 SPEC-126 U4 (D4) — CANCELAR O SERVIÇO QUE JÁ SAIU vem ANTES da agenda. Só quando o
    #    objeto do cancelamento é um SERVIÇO (`_SERVICO_ACIONADO`, até 5 palavras depois do verbo):
    #    "cancela a vistoria e o guincho tb" cancela o guincho também, e o guincho já está na rua.
    #    ⛔ "quero cancelar a vistoria" não tem serviço → segue para a regra `C` logo abaixo.
    ("K3", re.compile(r"(?:" + _CANCELAR + r")\W+(\w+\W+){0,5}?" + _SERVICO_ACIONADO + r"\b")),
    # 🔴 SPEC-126 CONSERTO X (RT-B2) — cancelar SEM o verbo; também ANTES da agenda: "desmarca o
    #    técnico" é o serviço, e a agenda (`C`) só vê vistoria/agendamento/visita/horário/data.
    ("K3", re.compile(_CANCELAR_SEM_O_VERBO)),
    # 🔴 SPEC-126 U4 — laudo do juiz final da 125 (pend. 2): "remarcar a vistoria" + "indenização"
    #    no MESMO turno saía `C` (a regra de agenda vinha antes de `L`) e a pergunta de dinheiro,
    #    que é da pessoa (R9), sumia. ⚠️ Só quando os DOIS estão: `L` sozinho já vinha depois de K3
    #    e continua; `C` sozinho continua `C`. Os dois termos são os MESMOS das regras L e C.
    ("L", re.compile(
        r"^(?=.*(?:indeniza|ser pag[ao]|pagamento (?:da|do)|prazo de pagamento))"
        r"(?=.*(?:cancel(?:a|ar|em|e)|remarca(?:r)?|desmarca(?:r)?|adiar|mudar|trocar) "
        r"(?:a |o |essa |esse |meu |minha )?(?:vistoria|agendamento|visita|horario|data))")),
    ("C", re.compile(
        # 🔴 SPEC-126 U4: o verbo em toda forma ("cancela", "cancelem", "remarca") — com o K3 novo
        #    casando "cancela" sozinho, "cancela a vistoria" iria para a pessoa se a agenda só
        #    reconhecesse o infinitivo.
        r"(cancel(a|ar|em|e)|remarca(r)?|desmarca(r)?|adiar|mudar|trocar) "
        r"(a |o |essa |esse |meu |minha )?(vistoria|agendamento|visita|horario|data)")),
    # 🔴 SPEC-126 U4 (D4) — TODA forma de cancelar o serviço. 📊 Antes era
    #    `cancelar|desistir|nao quero mais|desisti do`: "cancela o guincho", "pode cancelar",
    #    "cancelem", "desiste", "não precisa mais do guincho" caíam em `N` → a segunda chance
    #    mandava o agente "resolver sem pessoa" um pedido que só a corretora executa.
    #    ⛔ Não pega: "não precisa se preocupar" (sem "mais"), "não precisa mais de nada" (é
    #    despedida), "não cancela não" / "não precisa cancelar" (negação, em `_CANCELAR`).
    ("K3", re.compile(
        _CANCELAR
        + r"|(?<!nao )\bdesist(e|i|ir|o|imos|iu)\b|nao quero mais"
        + r"|nao (precisa|preciso|precisamos|vou precisar|vamos precisar) mais\b"
          r"(?! (nada|de nada|esperar|me preocupar|se preocupar|nos preocupar|preocupar))"
        + r"|nao (vou|vamos) mais precisar"
        + r"|ja (resolvi|resolvemos|consegui|conseguimos|deu certo)\b.{0,40}"
          r"\bnao (manda|mande|mandem|envia|envie|enviem|precisa)\b"
        + r"|\bnao (manda|mande|mandem|envia|envie|enviem)\b( mais)? (o |a )?(guincho|reboque|prestador"
          r"|tecnico|chaveiro|ninguem)")),
    ("L",  re.compile(r"indeniza|ser pag[ao]|pagamento (da|do)|prazo de pagamento")),
    ("I",  re.compile(
        r"abre? o (sinistro|chamado|atendimento)|abrir (outro|um novo|mais um)"
        r"|outro carro (tambem|meu)|de um outro veiculo")),
    # 📊 *"vcs cobram a seguradora pra mim?"* caía em `N` — a abreviação que o
    #    WhatsApp escreve ([4] do red team). `voces` e `vcs` são a mesma palavra.
    ("J",  re.compile(
        r"cobra-los|cobrar (eles|de novo|a seguradora|a oficina|a loja)"
        r"|temos que cobrar|(voces|vcs|vc) cobra|da uma cobrada")),
    ("D",  re.compile(r"carro reserva|carro de cortesia|fico sem carro|veiculo reserva")),
    ("E",  re.compile(
        r"franquia|reembols|consigo receber|custos que tive|taxa (de|do)"
        r"|quanto vou pagar|valor do (servico|conserto)")),
    ("C",  re.compile(
        r"vistoria|agendar|agendamento|remarcar|que horas|hoje a tarde"
        r"|amanha de manha|marcar (para|o dia)")),
    ("G",  re.compile(
        r"credenciada|oficina|outra opcao de|mais perto de casa|trocar de loja")),
    # 🔴 `mandar (o|a|os|as) ` casava **"pode mandar o guincho de novo?"** —
    #    [4] do red team, e o produto respondia a carta C5 (*"me manda os
    #    documentos"*) a quem está sem guincho. ⚠️ §9.5: o passo não travava,
    #    respondia ERRADO, e chegava ao cliente. O verbo agora exige o OBJETO:
    #    o que se manda aqui é papel, não caminhão.
    ("B",  re.compile(
        r"document|comprovante|nota fiscal|(a|o) (foto|pdf|arquivo)"
        r"|o que (falta|faltam)|(faltam|falta) algum"
        r"|(mandar|enviar|mando|envio) (o|a|os|as) "
        r"(document|comprovante|nota|foto|pdf|arquivo|laudo|boletim|papel)")),
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
#:
#: 🔴 SPEC-123 · conserto único (juiz B3 · red team B6) — O PEDIDO DE PESSOA É UM
#: DETECTOR SÓ, e é ESTE. A segunda chance do atendimento (`human_handoff.
#: por_que_vai_direto_a_pessoa`) lê as falas do segurado com `pediu_pessoa` — a
#: mesma régua que dá o rótulo `P` aqui. 📊 O padrão anterior só pegava
#: "quero falar com (uma pessoa|um atendente|alguem)" e "me passa PARA": "me passa
#: PRA uma pessoa", "quero uma pessoa", "atendente de verdade", "falar com o
#: corretor" e "humano de verdade" passavam (reprodução `rt-scripts/f7.py`).
#: ⚠️ Escrito para o texto do `_norm` (sem acento, minúsculo). ⛔ `vou falar com a
#: corretora` é o segurado contando o que VAI fazer, não pedindo — fica de fora.
#: constante_justificada: D8 do Founder — "o cliente que pede pessoa continua indo".
_PEDE_PESSOA = re.compile(
    r"(?<!vou )(?<!vamos )(?<!irei )\b(?:falar|conversar|tratar)\s+com\s+"
    r"(?:(?:(?:um|uma|o|a|algum|alguma)\s+)?"
    r"(?:pessoa|atendente|humano|ser humano|corretor|corretora|operador|operadora|alguem)"
    # ⛔ "falar com A GENTE" é "falar conosco" — 📊 lente de 01/10 (25.213 mensagens): o
    #    "pode falar com a gente por aqui" da URA casava. Só "gente" SEM artigo é pessoa.
    r"|gente)\b"
    r"|\b(?:me\s+)?(?:passa|passe|transfere|transfira|encaminha|encaminhe)\s+"
    r"(?:(?:pra|para|pro|com|a|o)\s+)?(?:(?:um|uma|algum|alguma)\s+)?"
    r"(?:pessoa|atendente|humano|alguem|corretor|corretora)\b"
    r"|\b(?:chama|chame)\s+(?:(?:um|uma|o|a)\s+)?(?:atendente|humano|alguem|corretor|corretora)\b"
    r"|\b(?:quero|queria|preciso de|prefiro|exijo)\s+(?:(?:um|uma|o|a)\s+)?"
    r"(?:pessoa|atendente|humano|atendimento humano)\b"
    r"|\batendente\s+(?:de verdade|humano|real)\b|\bpessoa\s+(?:de verdade|real)\b"
    r"|\bhumano de verdade\b|\batendimento humano\b|\bser humano\b"
    r"|\bnao quero (?:falar com )?(?:um )?(?:robo|bot|maquina)\b")


def pediu_pessoa(mensagens: Any) -> bool:
    """O segurado (ou o motivo que o agente escreveu) PEDE uma pessoa? — **PURA**.

    Uma fala ou uma lista delas; cada uma conferida sozinha (uma rajada juntada
    poderia casar o fim de uma frase com o começo da outra)."""
    if isinstance(mensagens, (str, bytes)):
        mensagens = [mensagens]
    return any(_PEDE_PESSOA.search(_norm(m)) for m in (mensagens or []) if str(m or "").strip())


#: O RISCO À VIDA dito pelo segurado — a parte de `_URGENCIA` que NÃO é pedido de pessoa.
#: 🔴 SPEC-126 U4: a segunda chance lê ESTE padrão nas falas (`ha_risco_a_vida`), o mesmo que dá
#:    o rótulo `P` aqui — uma fonte só (§9.4).
_RISCO_A_VIDA = re.compile(
    r"\bferid|\bvitima|ambulancia|acidente agora|urgencia medica|passando mal")

_URGENCIA = re.compile(_PEDE_PESSOA.pattern + r"|" + _RISCO_A_VIDA.pattern)


def ha_risco_a_vida(mensagens: Any) -> bool:
    """O segurado diz que há risco à VIDA ("meu filho tá passando mal", "tem ferido")? — **PURA**.

    🔴 SPEC-126 U4 — laudo do juiz final da 125 (pend. 2): a urgência só pesava quando estava no
    MOTIVO que o modelo escreveu (`human_handoff._MOTIVOS_DE_REGRA['vitima']`). Dita pelo segurado
    num caso sem acionamento, ganhava a segunda chance. Cada fala conferida sozinha, como
    `pediu_pessoa`."""
    if isinstance(mensagens, (str, bytes)):
        mensagens = [mensagens]
    return any(_RISCO_A_VIDA.search(_norm(m)) for m in (mensagens or []) if str(m or "").strip())


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


def kinds_sem_frase() -> Tuple[str, ...]:
    """Os kinds do BANCO que este arquivo não sabe dizer em português.

    🔴 **`o_fim_do_atendimento.KINDS` é a fonte única** (achado da lente
    DADO+verdade: três listas dos mesmos três kinds). ⚠️ Este mapa **não** vira
    a lista derivada porque cada entrada é uma TRADUÇÃO, e traduções não se
    geram: `esperando_cliente` vira *"esperando você mandar o que falta"* para
    o segurado e *"o segurado"* para a equipe — audiências diferentes, frases
    opostas. O que se deriva é a COBERTURA.

    ⛔ Um kind novo no banco sem frase aqui vira SILÊNCIO em `texto_da_espera`
    (ele devolve `""`), e silêncio é o defeito mais caro desta SPEC. Esta função
    existe para que isso apareça — o guarda a chama, e ela devolve `()` quando
    está tudo coberto.
    """
    try:
        from app.services.o_fim_do_atendimento import KINDS
    except Exception:  # noqa: BLE001
        return ()
    return tuple(k for k in KINDS if k not in _DE_QUEM)


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


def bloco_do_prompt(prompt_versao: Any = None) -> str:
    """A seção de PÓS-ACIONAMENTO do prompt do agente de atendimento.

    🔴 **GERADO** de `mapa_de_cartas()` e de `SITUACOES_PARA_HUMANO` — as duas
    lidas do módulo em tempo de chamada, para que trocar qualquer uma delas
    mude o texto que chega ao modelo (é o que [J1] mede).

    🔴 SPEC-125 Z4: `prompt_versao` (`agents.prompt_versao`; vazio = o padrão do
    produto, v2) — na v2 "cobrar o guincho" é andamento e K1/K2/J só viram pessoa na
    condição (`CONDICAO_NO_ATENDIMENTO`); na v1 o bloco é o de antes, byte a byte.
    """
    try:
        from app.core.prompts import normalizar_prompt_versao

        v1 = normalizar_prompt_versao(prompt_versao) == "v1"
    except Exception:  # noqa: BLE001 — sem a régua da versão, o padrão do produto
        v1 = False
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
    if not v1:
        linhas.append(_COBRANCA_DO_ANDAMENTO)
        linhas.append("")
    humanos = "\n".join(
        ("- %s → passe para uma pessoa da corretora SÓ SE %s: %s."
         % (CATEGORIAS.get(rotulo, rotulo), CONDICAO_NO_ATENDIMENTO[rotulo], razao))
        if rotulo in CONDICAO_NO_ATENDIMENTO and not v1 else
        ("- %s → passe para uma pessoa da corretora: %s."
         % (CATEGORIAS.get(rotulo, rotulo), razao))
        for rotulo, razao in SITUACOES_PARA_HUMANO.items()
    )
    linhas.append(_FECHO_DO_BLOCO % humanos)
    return "\n".join(linhas)


# ===========================================================================
# 🔴 SPEC-125 CONSERTO Z4 — "CADÊ O GUINCHO?" É ANDAMENTO, NÃO É PESSOA
#
# 📊 RODADA FINAL (02/10/2026): o C8 ("terceira vez que escrevo, que demora, cade o
# guincho??", caso já acionado, protocolo na conversa) chamou uma pessoa em TODAS as
# rodadas (BASE, DEPOIS, FINAL; 2/2 em cada). O motivo que o modelo escreveu foi "cliente
# irritado e cobrando o guincho… é necessário que a equipe cobre a seguradora" — as
# PALAVRAS deste bloco: "diz que o prestador não chegou → passe para uma pessoa (cobrar a
# seguradora AGORA)" e "está reclamando → passe para uma pessoa". O prompt v2 dizia o
# contrário ("irritação sozinha NÃO é motivo; 'cadê o guincho?' pede o estado"), e o bloco
# mais específico vencia. A causa era a regra INCONDICIONAL daqui.
#
# A ordem do Founder (01/10): pessoa só no grave — sinistro, risco à vida, condomínio/
# empresarial, serviço sem corredor, PEDIDO de pessoa. Cobrar o guincho é andamento:
# responde-se com o estado escrito do caso. `SITUACOES_PARA_HUMANO` continua a FONTE
# ÚNICA da razão (dossiê e régua leem a mesma); o que muda é QUANDO o agente passa.
# ===========================================================================

#: constante_justificada: a condição em que cada situação R9 vira pessoa NO ATENDIMENTO.
#:   K1/K2 — a ordem do Founder (01/10) e o C8 acima; J — quem cobra a seguradora é uma
#:   pessoa, mas só quando ELE pede a cobrança (cobrar o andamento a nós não é pedir isso).
CONDICAO_NO_ATENDIMENTO: Dict[str, str] = {
    "K1": ("ele estiver em local de risco (pista, acostamento, à noite, sozinho), pedir uma "
           "pessoa, ou o atendimento NÃO tiver acionamento escrito (nenhum protocolo nem "
           "pedido registrado) — fora disso responda com o estado escrito e "
           "ofereça pedir à equipe que cobre a seguradora"),
    "K2": ("ele pedir uma pessoa — reclamar, cobrar ou estar irritado SOZINHO não é motivo: "
           "acolha numa frase e responda com o estado escrito do caso"),
    "J": ("ELE pedir que a corretora cobre a seguradora ou a oficina (ou aceitar a sua oferta "
          "de cobrar) — perguntar \"cadê?\" não é esse pedido"),
}

_COBRANCA_DO_ANDAMENTO = (
    "QUANDO ELE COBRA (\"cadê o guincho?\", \"que demora\", \"já é a terceira vez\"):\n"
    "- É ANDAMENTO, não é motivo para chamar uma pessoa. Consulte o estado ESCRITO do caso — "
    "a ficha (fase, protocolo), o que a seguradora já respondeu na conversa, a hora do pedido — "
    "e responda com ele em uma ou duas frases: acolha a demora numa frase (\"entendo, é chato "
    "esperar\"), diga o que está escrito (\"o guincho foi pedido às <hora do pedido>, protocolo "
    "<o do caso>; a seguradora ainda não mandou a previsão\") e ofereça a próxima ação (\"quer que eu peça "
    "para a equipe cobrar a seguradora agora?\").\n"
    "- Chame uma pessoa só se ele pedir uma pessoa ou a cobrança, se houver risco no local, "
    "ou se o caso não tiver acionamento escrito (nenhum protocolo nem pedido registrado)."
)


#: ⚠️ O nome que a SPEC-097.1 §4 usa em prosa. Mesmo objeto — nunca uma
#: segunda função (§5).
bloco_de_pos_acionamento = bloco_do_prompt


__all__ = [
    "CARTAS", "CARTAS_POR_ID", "CATEGORIAS", "SEM_INTENCAO",
    "SITUACOES_PARA_HUMANO", "SITUACOES_CONDICIONAIS", "vai_para_humano",
    "classificar_turno", "ha_risco_a_vida", "mapa_de_cartas", "texto_da_espera",
    "e_atendimento_de_seguro", "bloco_do_prompt", "bloco_de_pos_acionamento",
]
