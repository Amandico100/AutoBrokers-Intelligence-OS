"""QUEM FALA NA SEGURADORA — a URA, ou uma pessoa? As tabelas MEDIDAS, numa casa só.

🔴 SPEC-EXTRA-001.4 BLOCO D1 — AS TABELAS MUDARAM DE CASA.

Elas moravam em `backend/scripts/zonas_do_acervo.py`, onde só a RÉGUA as lia. O
MOTOR decidia a fase humana por EXCLUSÃO ("nenhum passo casou") e o resumo do
caso por uma regex inline de 7 frases, escrita à mão, sem controle negativo.

📊 10/09/2026, sessão Allianz `432614de`: a atendente da Allianz se apresentou às
17:35:40 com a sessão em `needs_human` — e o motor não tinha como saber que era
uma PESSOA, nem de onde tirar essa certeza. A certeza existia, medida por
seguradora, com contagem de sessões ao lado de cada padrão — num script.

Agora: **uma fonte, dois consumidores** (proposta §8.1). O produto importa daqui;
`scripts/zonas_do_acervo.py` também. ⛔ Nenhuma segunda tabela de frases de
transferência (CLAUDE.md §5).

⚠️ **O DIALETO** (CLAUDE.md §9.4). Os padrões foram medidos sobre
`norm_para_classificar` = o `_norm` do corredor sobre o texto sem invisíveis. É
ESSA a função que o motor usa para aplicá-los — nunca `_norm_text` cru: 📊 17/09,
43 de 19.023 eventos `in` mudam entre as duas formas (soft hyphen, zero width).

⚠️ **Módulo LEVE.** Só a biblioteca padrão e o `_norm` do corredor — o hub
`insurer_dispatch_service` o carrega em testes que montam `app.services` à mão.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from app.services.corridor_playbooks import _norm

# ─────────────────────────────────────────────────────────────────────────────
# NÍVEL 1 · FRONTEIRAS — a URA anunciando que entrega o caso a um humano.
# 🔴 A marca é POR SEGURADORA. Uma regex só carimba nove de dez:
#    📊 a regex única da v2 removeu allianz 3.737 · porto 459 · yelum 278 ·
#    hdi 169 · azul 21 · zurich 10 · **bradesco 0 · tokio 0 · mapfre 0 · alfa 0**
#    — e declarava `zona='URA'` tudo que ela não pegasse. Quatro seguradoras
#    entrariam na fábrica com selo de limpeza que nenhuma medição sustenta.
# ─────────────────────────────────────────────────────────────────────────────
FRONTEIRAS: Dict[str, List[str]] = {
    "allianz": [
        r"vou transferir seu caso para um especialista",          # 📊 98 sessões — REPRODUZ EXATO
    ],
    "porto": [
        r"vou (precisar )?transferir (o )?seu atendimento",       # 📊 15 sessões — REPRODUZ EXATO
        r"irei te transferir para a central",                     # 📊 1 evento (session_id NULL → 0 sessões)
        # 🔴 MINERADO. A marca da SPEC via 15 de 19 acionamentos humanos.
        #    📊 `voce esta na fila para atendimento` casa EXATAMENTE as 19 que
        #    têm apresentação humana — cobertura 100%, contra 79% da anterior.
        #    Eventos removidos: 436 → 506.
        # ⚠️ `voce esta na fila para atendimento` SAIU daqui e virou
        #    `AVISO_DE_ESPERA`, que vale para as 10 — 📊 ela aparece em 40
        #    sessoes de 4 seguradoras, nao so na porto.
        r"seu analista ja vai falar com voce",                    # 📊 2 sessões
    ],
    "hdi": [
        r"necessario falar com um de nossos especialistas",       # 📊 7 sessões — REPRODUZ
        r"conversa foi encerrada pelo atendente",                 # 📊 8 sessões — REPRODUZ
        r"atendimento prestado pelo nosso analista",              # 📊 8 sessões — REPRODUZ
        # ⚠️ O padrão da v3 (`(vou|irei) (te )?(precisar )?transferir`) NÃO casava
        #    o texto real: o acervo escreve *"vou PRECISAR TE transferir"*, e o
        #    padrão exigia *"vou te precisar transferir"*. Conferido literalmente:
        #    select ('vou precisar te transferir…' ~ '<corrigido>') → true
        #    select ('vou precisar te transferir…' ~ '<v3>')        → false
        r"(vou|irei) (precisar )?te transferir|(vou|irei) transferir",  # 📊 6 sessões (SPEC dizia 3)
        r"vamos te direcionar para um de nossos especialistas",   # 📊 1 sessão — REPRODUZ
        # 🔴 MINERADO — +3 sessões que nenhum dos 5 acima pegava:
        r"enquanto te transfiro|te transfiro para",               # 📊 3 sessões
        r"analistas? (dara continuidade|vai seguir com seu atendimento)",  # 📊 3 sessões
    ],
    "yelum": [
        r"necessario falar com um de nossos especialistas",       # 📊 11 sessões — REPRODUZ EXATO
        r"conversa foi encerrada pelo atendente",                 # 📊 12 sessões — REPRODUZ EXATO
        # 🔴 MINERADO — a SPEC via 12 de 16 acionamentos humanos (perdia 25%):
        r"(vou|irei) (te )?transferi|te transfiro",               # 📊 9 sessões (+3)
        r"transferi(-lo|r).{0,40}(analista|especialista|setor)",  # 📊 6 sessões (+2)
        r"analistas? vai seguir com seu atendimento",             # 📊 1 sessão (+1)
        # ⚠️ Note `especiailista` — 📊 a própria URA erra a grafia numa sessão.
        #    Regex de literal exato não sobrevive a isso; a apresentação humana
        #    (nível 2, abaixo) sobrevive. É por isso que existem dois níveis.
    ],
    "azul": [
        r"vou precisar transferir o seu atendimento",             # 📊 2 sessões — REPRODUZ EXATO
        r"nossa conversa esta registrada sob n[o°º]",             # 📊 2 sessões — o humano, minerado
    ],
    "zurich": [
        r"irei te transferir para um de nossos atendentes",       # 📊 2 sessões — REPRODUZ
        r"vou transferir voce para a pessoa que vai continuar",   # 📊 1 sessão — REPRODUZ
        # 🔴 A v3 tinha `"zurich": []`. Não era medição — era o CORTE DA QUERY
        #    (`order by insurer_key limit 22`, e zurich é a última em ordem
        #    alfabética). Ausência de linhas no resultado lida como ausência de
        #    marca no acervo.
    ],
    "mapfre": [
        r"vou te direcionar para a pessoa que vai dar continuidade",  # 📊 2 sessões (SPEC dizia 3)
        # 🔴 As duas marcas seguintes são o MESMO EVENTO, e são ditas pelo
        #    HUMANO, não pela URA. Ficam porque marcam a SEGUNDA fronteira:
        #    📊 a sessão a68aa770 tem TRÊS atores — URA Maite → humano MAPFRE →
        #    humano da Localiza (empresa terceira).
        r"passando seu caso para eles|ja realizo a transferencia",   # 📊 1 sessão
    ],
    # 🔴 CORRIGIDO. A SPEC declarava `"bradesco": []` com
    #    *"✅ VAZIA CONFERIDA: não há transferência consumada no acervo"*.
    #    📊 É FALSO: 2 de 22 sessões têm transferência consumada COM humano se
    #    apresentando pelo nome. **A causa é uma palavra:** a busca foi por
    #    `transferir` (0 ocorrências) e o bradesco escreve **`transferindo`**.
    #
    #    🔴 E o bradesco era uma das QUATRO âncoras "limpas" da curva de
    #    referência da SPEC-084. A curva continua válida — ela vem da Allianz —
    #    mas o CONTROLE de validação passa a ter 3 âncoras limpas, não 4.
    #    ⚠️ E vira um dado melhor: ele estava a 21,2% COM contaminação de 2/22 e
    #    ficou abaixo do p95 — o que confirma, por outro caminho, que o número
    #    NÃO detecta contaminação leve.
    "bradesco": [
        r"estamos te transferindo para nossa equipe",             # 📊 2 sessões
    ],
    # ✅ VAZIAS CONFERIDAS COM PROVA POSITIVA, não com ausência de busca:
    "tokio": [],
    #   📊 CENSO das 79 telas `in` distintas, lidas uma a uma. `transferir` 0 ·
    #   `especialista` 0 · `encerrad` 0 · `meu nome e` 0 · `vou te ajudar` 0.
    #   A única auto-apresentação é *"eu sou a Marina, a assistente virtual da
    #   Tokio Marine"*. 🔴 LINHA DE CONTROLE: o lado `out` também é 100%
    #   mecânico — 27 formas em 100 eventos, todas `ola`/CPF/rótulo de botão.
    #   **Não há a quem um humano responder.** A tokio sai por link
    #   (`autoatendimento.tokiomarine.com.br`) ou telefone, não transfere no fio.
    "alfa": [],
    #   📊 LINHA DE CONTROLE que dá direito ao zero: a regex
    #   `(meu nome e |me chamo |sou o |sou a )` SEM o filtro devolveu **8 de 9
    #   sessões** — todas o falso positivo *"sou a assistente virtual da alfa"*.
    #   Com `AND NOT 'assistente virtual'`, cai para **0 de 9**. E a MESMA regex,
    #   no MESMO comando, devolveu 2 na mapfre. **O guarda consegue disparar** —
    #   logo o zero da alfa é *"não transfere"*, não *"não procurei"*.
}

# ─────────────────────────────────────────────────────────────────────────────
# 🔴 A APRESENTAÇÃO HUMANA — e por que ela é um GUARDA, não um classificador.
#
# ⚠️ **Esta seção mudou de lugar depois de ser medida.** Ela nasceu como "nível 2
#    do classificador" e a medição a moveu. O registro fica porque a próxima
#    pessoa vai ter a mesma ideia.
#
# > *"Quando um humano entra no atendimento, ele SE APRESENTA e diz que entrou.
# >  Em ~99,9% dos acionamentos o humano se apresenta antes."* — o Founder
#
# 📊 A pista foi testada nas 10 seguradoras e **valeu**: ela achou 11 sessões que
#    a `FRONTEIRAS` da SPEC perdia — porto +4, hdi +3, yelum +3, bradesco +2 (e o
#    bradesco tinha `[]` declarado *"VAZIA CONFERIDA"*, o que era falso).
#
# 🔴 **Mas o ganho foi ABSORVIDO pelas marcas mineradas.** Depois de a
#    `FRONTEIRAS` acima ganhar `voce esta na fila` (porto), `te transfiro` (hdi),
#    `vou transferi-lo` (yelum) e `transferindo` (bradesco), a apresentação como
#    CLASSIFICADOR rende, medido em 21/08/2026:
#
#    ```
#    padrão                                    sessões   já-fronteira   NOVAS
#    (meu nome e|me chamo|sou (o|a)) [a-z]        153        150          3
#    darei continuidade em seu atendimento         16         16          0
#    irei realizar seu atendimento|vou atender     22         22          0
#    seja bem-vindo(a) ao atendimento               7          7          0
#    estou assumindo                                0          0          0
#    ```
#
#    **ZERO ganho — e três falsos positivos**, todos medidos e nomeados:
#      🔴 `sou` sem `\b` casa DENTRO de `avi[sou o s]eu sinistro` (yelum)
#      🔴 `botao 1: sou o segurado` — rótulo de MENU, não pessoa (zurich)
#      🔴 e o corte falso arrastava 135 eventos da zurich para HUMANO, incluindo
#         `eu sou a laiz, assistente virtual` — o próprio robô
#
# > ## Por isso ela deixou de classificar e passou a GUARDAR.
#
# A pergunta que ela responde agora é a certa: **"a `FRONTEIRAS` perdeu alguém?"**
# Uma sessão com apresentação humana e SEM fronteira é uma marca que falta na
# tabela. 📊 O guarda ficou **VERMELHO** em porto, hdi, yelum e bradesco antes da
# mineração, e está **VERDE** depois — provado nos dois sentidos, que é o que a
# CLAUDE.md §9.3 exige.
#
# Ver `guarda_de_completude_da_fronteira()` no fim deste arquivo.
# ─────────────────────────────────────────────────────────────────────────────
#
# > *"Quando um humano entra no atendimento, ele SE APRESENTA e diz que entrou.
# >  Em ~99,9% dos acionamentos o humano se apresenta antes, dizendo o nome e
# >  que vai ajudar."* — o Founder
#
# 📊 TESTADA NAS 10 SEGURADORAS, e ela acha 11 sessões que a `FRONTEIRAS` perdia:
#
#   seguradora   apresentação   FRONTEIRAS da SPEC   ganho
#   porto            19               15              +4
#   hdi              12                9              +3
#   yelum            15               12              +3-4
#   bradesco          2                0              +2   (a lista vazia era falsa)
#   allianz          97               98               0   (chega 4s DEPOIS — é confirmação)
#   azul              2                2               0
#   mapfre            2                2               0   (e é o corte EXATO)
#   zurich·tokio·alfa 0            0/0/0               0   (`[]` conferida)
#
# 🔴 E em NENHUMA seguradora existe fronteira conhecida SEM apresentação depois.
#    📊 hdi 9/9 · yelum 12/12 · allianz 97/97 (mediana 4 segundos).
#    **A regra do Founder reproduz integralmente.**
# ─────────────────────────────────────────────────────────────────────────────
APRESENTACAO_HUMANA = [
    # 🔴 `\b` OBRIGATÓRIO em `sou`. Sem ele, 📊 o padrão casa DENTRO de
    #    `avi[sou o s]eu sinistro` — um falso positivo silencioso na yelum.
    # 🔴 E `(?!o segurado|o terceiro|...)`: 📊 `botao 1: sou o segurado` é rótulo
    #    de MENU. A apresentação humana traz um NOME, não um papel.
    r"(meu nome (e|eh)|me chamo)\s+[a-z]{3,}",
    r"\bsou (o|a)\s+(?!segurad|terceir|responsav|condutor|proprietari|titular|cliente)[a-z]{3,}\s+"
    r"(e (vou|irei|darei)|,)",
    r"darei continuidade (em|no) seu atendimento|dar (sequencia|continuidade) (em|no) seu atendimento",
    r"irei realizar seu atendimento|prestarei seu atendimento|vou atender sua demanda",
    r"seja bem.?vindo ?\(a\)? ao atendimento",
    r"estou assumindo|assumindo seu atendimento",
]

# 🔴 O CONTROLE NEGATIVO SEM O QUAL A REGRA DO FOUNDER COME O ACERVO INTEIRO.
#
# 📊 Sem ele, `meu nome é|me chamo|sou a` marca:
#      allianz  123 de 140 sessões (88%)   "sou a assistente virtual da allianz"
#      azul      16 de  19       (84%)     "sou a atendente virtual da azul"
#      alfa       8 de   9       (89%)     "sou a assistente virtual da alfa"
#      bradesco  12 de  22       (55%)     "sou a assistente virtual da bradesco"
#      zurich    11 de  14       (79%)     "meu nome é Laiz e sou a assistente virtual"
#      hdi        8 · yelum 11 · tokio 6 · mapfre 5
#
# **O robô também se apresenta.** E ele se apresenta MAIS que a gente.
# ═════════════════════════════════════════════════════════════════════════════
# 🔴 `MARCAS_DE_SESSAO_HUMANA` FOI REMOVIDA — e o motivo e o achado da rodada.
# ═════════════════════════════════════════════════════════════════════════════
#
# Ela existiu por meio dia. O JUIZ DE TRIAGEM leu 22 sessoes e marcou 9 como
# contendo fala humana; a regra descartava do corpus as 6 que nao tinham
# fronteira identificavel. Parecia conservadora e correta.
#
# 🔴 **O veredito do Founder sobre a amostra de 30 falas foi ZERO de 30.**
#    *"Toda a lista e URA, nenhuma de humano. Quando um humano assume,
#    normalmente e BEM CLARO."*
#
# E a reconferencia da sessao que motivou a regra — `44ff2017` — mostrou o
# tamanho do erro. Lida INTEIRA, ela e um **acionamento completo**:
#
# ```
#   "A apolice tem cobertura para tres servicos que ficam separados..."
#   "Qual servico deseja acionar?"              -> "Vamos colocar como troca de resistencia"
#   "Para esse atendimento o seguro arca apenas com a mao de obra do prestador"
#   "Segue as exclusoes: Chuveiros que nao sejam eletricos; Chuveiros blindados..."
#   "O agendamento e feito em intervalo de 2 horas..."
#   "Pode informar o nome e telefone do responsavel?"
#   "O prestador precisa levar escada? Se sim, qual altura?"
#   "O agendamento fica para 20/01 das 10hs as 12hs"
#   "Vou deixar registrado o telefone ... A senha para..."
# ```
#
# > ## E o ROTEIRO COMPLETO de `troca de resistencia de chuveiro` — um servico que o produto NAO TEM.
#
# Com as regras de cobertura, as exclusoes, a janela de agendamento, os dados
# coletados e a senha. **Descarta-la era jogar fora exatamente o que a SPEC-084
# precisa para escrever a rota** — e o Founder pediu isso por escrito:
#
# > *"o ideal e que consiga encontrar os atendimentos feitos pelos humanos da
# > corretora e transformar em subservicos para serem feitos pelos agentes de
# > atendimento, sem precisar de humano."*
#
# ⚠️ E as marcas que a regra usava (`ajudo em algo mais`, `assistencia 24 horas
# permanece a disposicao`) sao **linhas de fecho do canal de assistencia** — o
# robo e a gente usam as duas. Elas nao distinguem emissor.
#
# 🔴 A fronteira volta a ser **so a marca de transferencia** (`FRONTEIRAS`), que
#    e a que o Founder descreve: *"quando um humano assume, e BEM CLARO"*.
#
# ⚠️ E o guarda de completude (`guarda_de_completude_da_fronteira`) FICA: ele
#    continua sendo a rede que avisa se a tabela perdeu alguem.


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 `AVISO_DE_ESPERA` — a classe que o Founder nomeou, e ela NAO e fronteira.
# ═════════════════════════════════════════════════════════════════════════════
#
# > *"Nao e humano. E um robo avisando que foi chamado um humano e que esta
# > demorando. Mas ainda e o robo falando."* — o Founder, sobre a linha 16
# > da amostra de triagem.
#
# 📊 O texto, da porto: *"Antes de continuar, so um aviso: estamos com um alto
#    volume de atendimento no momento. Peco a sua paciencia..."*
#
# 🔴 **E URA — a LINHA fica no corpus.** O Founder esta certo: quem fala ali e o
#    robo, e a tela e tela de URA legitima.
#
# ⚠️ **E ela É fronteira — as duas coisas sao verdade e nao se contradizem.**
#    📊 Medido em 21/08/2026, contando quantas sessoes tem apresentacao humana
#    DEPOIS da marca:
#
# ```
#   voce esta na fila para atendimento              40 sessoes ->  38  (95%)
#   isso pode levar alguns instantes, ja ja...      48         ->  47  (98%)
#   estamos com um alto volume de atendimento        8         ->   8 (100%)
#   aguarde alguns instantes enquanto procuramos     2         ->   2
#   peco a sua paciencia                             1         ->   1
#                                                   ---            ---
#                                                    99             96
# ```
#
# > ## Em 96 de 99 sessoes, o humano chega logo depois. A linha e do robo; o que vem depois, nao.
#
# 🔴 E o desenho de `zonas()` ja resolve isso sem escolher um lado: a tela da
#    fronteira e devolvida como **URA** (*"e a URA anunciando"*), e o corte vale
#    do evento SEGUINTE em diante. A linha fica no corpus; a conversa humana, nao.
#
# ⚠️ Foi por medicao que esta lista mudou de lugar. A primeira leitura da nota do
#    Founder a pos em `NAO_E_FRONTEIRA` — e ai `voce esta na fila` (a marca que o
#    minerador mediu cobrindo 19 de 19 acionamentos humanos da porto) teria sido
#    DESLIGADA. **Uma leitura sem medicao teria desfeito o melhor achado da porto.**
AVISO_DE_ESPERA = [
    r"estamos com um alto volume de atendimento",
    r"pe[cç]o a sua paci[ee]ncia",
    r"aguarde alguns instantes enquanto procuramos um atendente",
    r"isso pode levar alguns instantes, mas ja ja voce sera atendido",
    r"voce esta na fila para atendimento",
]

APRESENTACAO_DO_ROBO = [
    r"assistente virtual|atendente virtual|assistente digital",
    r"atendimento (virtual|digital)",
    r"sou (um|uma) (bot|rob[oô])",
]

# ─────────────────────────────────────────────────────────────────────────────
# NAO_E_FRONTEIRA — o controle negativo, sem o qual a URA é cortada no meio.
#
# 🔴 Cortar numa negativa ou num menu joga fora o resto de uma sessão de URA
#    legítima — e o gate de hapax **nem acusa**, porque remover telas repetidas
#    BAIXA o percentual de texto único. O guarda ficaria verde enquanto o corpus
#    encolhe.
#
# 🔴 TESTE OBRIGATÓRIO: todo padrão de `FRONTEIRAS` roda contra `NAO_E_FRONTEIRA`
#    e tem de dar **ZERO**. Padrão que casa os dois não entra na tabela.
# ─────────────────────────────────────────────────────────────────────────────
NAO_E_FRONTEIRA: Dict[str, List[str]] = {
    "allianz": [
        r"previsao de chegada do especialista",     # 📊 3 ses — "especialista" é o PRESTADOR a caminho
        r"sou a assistente virtual da allianz",     # 📊 123 ses — é o BOT
        r"setor residencial selecionando a opcao",  # 📊 2 ses — NEGATIVA + MENU
    ],
    "porto": [
        # 🔴 O mais perigoso do acervo: parece fronteira e foi verificado linha a
        #    linha como CONTINUAÇÃO DE URA. 📊 A corretora respondeu "voltar" e o
        #    fluxo seguiu 100% robô, entregando depois cardápio e tela de ramo.
        r"antes de transferir sua conversa para um especialista",  # 📊 2 ses
        r"transferir (seus pontos|sua pontuacao)|programas de milhagem",  # 📊 1 ses
        r"vou precisar iniciar um novo atendimento",               # 📊 4 ses
        r"vou encerrar a conversa",                                # 📊 28 ses — a URA encerra
    ],
    "hdi": [
        r"antes de comecarmos, vou te passar algumas dicas|dicas rapidas:",  # 📊 17 ses
        r"sou a assistente virtual",                                          # 📊 8 ses (6 exclusivas)
        r"entendemos que voce gostaria de falar com um atendente",            # 📊 2 ses — NEGATIVA
        r"aguarde alguns instantes enquanto procuramos um atendente",         # 📊 1 ses — promessa
        # 📊 Uma regex ingênua em `encerrada` casaria 21 sessões contra as 8
        #    corretas → 17 falsos positivos. A frase completa filtra tudo isso.
    ],
    "yelum": [
        # 🔴 O par que exige o `pelo atendente` literal: 📊 `conversa foi encerrada
        #    pelo atendente` (12, humano) vs `por falta de interacao esta conversa
        #    foi encerrada` (12, TIMEOUT), das quais só 2 coincidem. Afrouxar o
        #    regex para `conversa foi encerrada` DOBRA o número e agrega 10 falsos.
        r"por falta de interacao esta conversa foi encerrada",   # 📊 12 ses — timeout
        r"o que achou do atendimento prestado pelo nosso analista",  # 📊 12 ses — pesquisa PÓS
        r"vou te passar algumas dicas sobre como funciona",      # 📊 11 ses — robô
        r"eu sou a assistente virtual",                          # 📊 11 ses — robô
        r"foi um prazer te atender",                             # 📊 4 ses — despedida
        r"entendemos que voce gostaria de falar com um atendente",  # 📊 1 ses — RECUSA
        r"nao temos nenhum especialista disponivel",             # 📊 1 ses — negativa
        r"sua resposta nao corresponde a nossa pergunta",        # 📊 1 ses — robô
    ],
    "zurich": [
        r"nao foi possivel te transferir",           # 📊 1 ses — NEGATIVA, não transferiu
        r"vou direcionar voce para nosso menu",      # 📊 1 ses — é MENU
        r"o que voce deseja fazer agora",            # 📊 1 ses — é MENU
        r"sou a assistente virtual da zurich|me chamo laiz|eu sou a laiz",  # 📊 11 ses — o BOT
    ],
    "bradesco": [
        r"qual opcao voce escolhe.*chamar atendente",       # 📊 2 ses — MENU (a oferta)
        r"podemos chamar alguem da nossa equipe pra ajudar",  # 📊 2 ses — OFERTA
        r"sou a assistente virtual da bradesco",            # 📊 12 ses — o BOT
        r"aguarde um momento enquanto aciono meu sistema",  # 📊 1 ses — LATÊNCIA
    ],
    "tokio": [
        r"clique no link.*conversar com um atendente",   # 📊 1 ses — LINK
        # 🔴 MINERADO: o da SPEC marca 1 sessão; este marca 7 (15,2%) e é de
        #    longe o mais perigoso se a regex de fronteira for genérica em
        #    `analista`. As 7 foram abertas evento a evento: nenhuma tem uma
        #    única mensagem humana depois.
        r"enviar (os )?documentos,? .*falar com um analista",  # 📊 7 ses
        r"para falar com um resolvedor no whatsapp clique no botao",  # 📊 1 ses
        r"eu sou a marina|sou a marina, assistente virtual",   # 📊 6 ses — o BOT
    ],
    "azul": [
        r"fale com um dos nossos especialistas, clicando no link",  # 📊 2 ses — LINK
        r"sou a atendente virtual da azul seguros",                # 📊 16 ses — o BOT
        r"botao 2: falar com atendente",                           # 📊 1 ses — MENU
        # ⚠️ 📊 `atendente` cru marca 16 de 19 sessões (84,2%) por causa da
        #    saudação do bot. NUNCA usar `atendente` sozinho como sinal.
    ],
    "mapfre": [
        # 🔴 CORRIGIDO. A SPEC-084 §2.5.1 lista `"que bom falar com voce!"` como
        #    fala HUMANA. 📊 É URA: está na sessão 9fae42e2 no evento 6, **quinze
        #    telas antes** de qualquer humano entrar, como saudação da Maite
        #    depois que o corretor digita o código. Classificá-la como humana
        #    removeria tela legítima da URA.
        r"que bom falar com voce",                     # 📊 é a URA saudando
        r"eu sou a maite, assistente virtual",         # 📊 5 ses — o BOT
        r"fale com o analista",                        # 📊 1 ses — link de portal
    ],
    "alfa": [
        r"sou a assistente virtual da alfa",           # 📊 8 de 9 ses — o BOT
        # ⚠️ 📊 `no momento eu nao consigo te ajudar… entre em contato com a
        #    nossa central` (3 ses) NÃO é fronteira: não há continuidade no
        #    canal. É ABANDONO PARA TELEFONE — um `DESFECHO_NEGATIVO`.
        r"no momento eu nao consigo te ajudar",        # 📊 3 ses
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# A NORMALIZAÇÃO PARA CLASSIFICAR — e por que ela não é o `_norm`
#
# 🔴 O `_norm` é o do MOTOR e não se toca: a SPEC-083 não muda corredor, e
#    reimplementá-lo seria o segundo normalizador que o CLAUDE.md §5 proíbe.
#
# ⚠️ Mas 📊 o acervo tem caracteres invisíveis que o `_norm` (NFKD + acento +
#    `*` + lower) NÃO remove, porque não são combinantes:
#      U+00AD SOFT HYPHEN     3 eventos / 2 sessões / 1 seguradora (zurich)
#      U+200B ZERO WIDTH SP   4 eventos
#    📊 Efeito medido: `combustí<U+00AD>vel` faz `combust[ií]vel` FALHAR — e a
#    perda vira só um número menor, que ninguém lê como defeito.
#
# **A limpeza dos invisíveis acontece ANTES de chamar o `_norm`, na geração do
# corpus.** O conserto do `_norm` é entrega da SPEC-084 → `PENDENCIAS.md`.
# ─────────────────────────────────────────────────────────────────────────────
_INVISIVEIS = dict.fromkeys(
    [0x00AD, 0x200B, 0x200C, 0x200D, 0xFEFF, 0x2060], None)


def limpar_invisiveis(texto: str) -> str:
    """Tira os caracteres de largura zero que o `_norm` não vê."""
    return unicodedata.normalize("NFC", str(texto or "")).translate(_INVISIVEIS)


def norm_para_classificar(texto: str) -> str:
    """`_norm` do motor, sobre o texto sem invisíveis. Nada mais."""
    return _norm(limpar_invisiveis(texto))



# Cache dos padrões compilados, por seguradora. ⚠️ Quem muta as tabelas limpa-o.
_CACHE: Dict[str, Tuple[Any, Any, Any, Any]] = {}


def _fronteira_de(seguradora: str) -> List[str]:
    """`FRONTEIRAS` da seguradora + o `AVISO_DE_ESPERA`, que vale para todas.

    📊 O aviso de espera vale para TODAS porque a medicao e transversal: 96 de 99
    sessoes com ele tem apresentacao humana depois, em 4 seguradoras diferentes.
    Uma marca que se comporta igual em quatro nao precisa de entrada por
    seguradora.
    """
    return list(FRONTEIRAS.get(seguradora, [])) + AVISO_DE_ESPERA


def _compilados(seguradora: str):
    if seguradora not in _CACHE:
        def _ou(lista):
            return re.compile("|".join(f"(?:{p})" for p in lista), re.DOTALL) if lista else None
        _CACHE[seguradora] = (
            _ou(_fronteira_de(seguradora)),
            _ou(NAO_E_FRONTEIRA.get(seguradora, [])),
            _ou(APRESENTACAO_HUMANA),
            _ou(APRESENTACAO_DO_ROBO),
        )
    return _CACHE[seguradora]


def e_fronteira(seguradora: str, texto_norm: str) -> Optional[str]:
    """A tela entrega o caso a um humano? Devolve `"FRONTEIRA"` ou `None`.

    🔴 A ordem é obrigatória: `NAO_E_FRONTEIRA` **vence** — ele existe para
    impedir que uma negativa (*"não foi possível te transferir"*) ou um menu
    (*"o que você deseja fazer agora"*) corte a URA no meio.

    🔴 **A apresentação humana NÃO classifica aqui.** Ela mede a completude da
    tabela, em `guarda_de_completude_da_fronteira()`. A razão está medida no
    comentário grande acima: como classificador ela rendia **zero** sessões
    novas e trazia **três** falsos.
    """
    fronteira, nao, _apres, _robo = _compilados(seguradora)
    if nao is not None and nao.search(texto_norm):
        return None
    if fronteira is not None and fronteira.search(texto_norm):
        return "FRONTEIRA"
    return None


def tem_apresentacao_humana(seguradora: str, texto_norm: str) -> bool:
    """Alguém se apresentou pelo nome — e não é o robô.

    🔴 O controle negativo (`APRESENTACAO_DO_ROBO`) não é opcional. 📊 Sem ele o
    padrão marca 88% das sessões da allianz, 84% da azul e 89% da alfa — porque
    **o robô também se apresenta, e se apresenta mais que a gente**.
    """
    _f, _n, apres, robo = _compilados(seguradora)
    if apres is None or not apres.search(texto_norm):
        return False
    return not (robo is not None and robo.search(texto_norm))


# ─────────────────────────────────────────────────────────────────────────────
# O QUE O MOTOR PERGUNTA — SPEC-EXTRA-001.4 D1 · D2 · D4
# ─────────────────────────────────────────────────────────────────────────────
def seguradora_do_corredor(playbook_ou_ref: Any) -> str:
    """`allianz` de `allianz-residencial-whatsapp@v1` — a chave das tabelas acima."""
    if isinstance(playbook_ou_ref, dict):
        chave = str(playbook_ou_ref.get("insurer_key") or "").strip().lower()
        if chave:
            return chave
        playbook_ou_ref = playbook_ou_ref.get("key") or playbook_ou_ref.get("playbook_ref") or ""
    return str(playbook_ou_ref or "").split("-", 1)[0].strip().lower()


def e_transferencia_para_pessoa(seguradora: str, texto: str) -> bool:
    """A URA ANUNCIOU que entrega o caso a uma pessoa — a âncora POSITIVA da fase
    humana (D1). Só `FRONTEIRAS` da seguradora; `NAO_E_FRONTEIRA` vence.

    ⚠️ Sem o `AVISO_DE_ESPERA`: ele diz "estamos na fila", não "transferi" — é o
    relógio de fila que o lê (`e_aviso_de_fila`), e ele não muda a fase.
    """
    t = norm_para_classificar(texto)
    _f, nao, _a, _r = _compilados(seguradora)
    if nao is not None and nao.search(t):
        return False
    return any(re.search(p, t, re.DOTALL) for p in FRONTEIRAS.get(seguradora, []))


def e_aviso_de_fila(texto: str) -> bool:
    """A URA disse que estamos NA FILA por uma pessoa (D4). Vale para todas."""
    t = norm_para_classificar(texto)
    return any(re.search(p, t, re.DOTALL) for p in AVISO_DE_ESPERA)


def e_o_robo_se_apresentando(texto: str) -> bool:
    """O controle negativo, sozinho: "sou a assistente virtual…"."""
    t = norm_para_classificar(texto)
    return any(re.search(p, t, re.DOTALL) for p in APRESENTACAO_DO_ROBO)


def uma_pessoa_se_apresentou(seguradora: str, texto: str) -> bool:
    """Alguém da seguradora se apresentou — e não é o robô (D2).

    📊 17/09, 19.023 eventos `in`: na zona humana, esta função e a regex inline
    que ela substitui no resumo do caso marcam AS MESMAS sessões nas 7
    seguradoras com humano (allianz 113 · porto 19 · yelum 17 · mapfre 13 ·
    hdi 12 · azul 2 · bradesco 2) — e na zona da URA a inline casava 77 telas
    do robô (youse 39 · zurich 13 · mapfre 10…), que esta função recusa.
    """
    return tem_apresentacao_humana(seguradora, norm_para_classificar(texto))
