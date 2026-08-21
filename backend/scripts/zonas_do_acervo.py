"""Quem está falando: a URA, ou uma pessoa? — a marcação de ZONA.

`direction='in'` é a **direção** da mensagem, não o **emissor**. Depois que a URA
transfere o caso, quem escreve `in` é o **atendente humano da seguradora**.

📊 Medido em 21/08/2026: **4.805 de 16.242 eventos `in` (29,6%)** são posteriores
à tela de transferência, em 140 sessões.

🔴 **E é por isso que este módulo existe, não por elegância.** O eixo B da rubrica
pergunta *"alguma tela do corpus não casa passo nenhum e pede algo?"*. Medido na
Allianz:

```
telas distintas que PEDEM algo:   zona humana 472   ·   zona URA 126   (3,7×)
```

**472 reprovações automáticas, permanentes e insanáveis.** Nenhuma rota da Allianz
seria liberada: todas bateriam o teto de 3 voltas. A SPEC não falharia com erro —
falharia **reprovando tudo**, e o executor procuraria o defeito no corredor a vida
inteira.

📊 **O CONTROLE que prova que as duas zonas são coisas diferentes** — se fossem a
mesma, os percentuais seriam parecidos:

```
zona                          eventos    texto em 1 sessão só
HUMANO                          4.674           44,8 %
URA          CONTROLE           3.509           11,7 %      ← 3,8× menos
```

**URA se repete; gente não.**

═══════════════════════════════════════════════════════════════════════════════
PROVENIÊNCIA — 📊 minerado em 21/08/2026 por 8 mineradores, um por seguradora.
Cada padrão traz a contagem de sessões medida ao lado. As correções em relação à
tabela escrita nas rodadas de juiz estão marcadas 🔴 no lugar.
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

import regua_motor as M

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
        r"voce esta na fila para atendimento",                    # 📊 19 sessões (+4)
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
    return M._norm(limpar_invisiveis(texto))


# ─────────────────────────────────────────────────────────────────────────────
# A CLASSIFICAÇÃO
# ─────────────────────────────────────────────────────────────────────────────
_CACHE: Dict[str, Tuple[Any, Any, Any, Any]] = {}

# 🔴 O `session_id` chega de dois jeitos e os dois significam "não tem sessão":
#    `None` quando vem direto do PostgREST, e a STRING `"None"` quando o acervo
#    passou por um `json.dump` no meio. ⚠️ Uma checagem `if not sid` pega o
#    primeiro e **deixa passar o segundo** — e a diferença apareceu como duas
#    sessões-fantasma no guarda de completude, com "seguradora" allianz e porto.
#    É a mesma família do bucket órfão que produziu o off-by-one da SPEC.
_SEM_SESSAO = (None, "", "None", "none", "null")


def _tem_sessao(sid: Any) -> bool:
    return sid not in _SEM_SESSAO


def _compilados(seguradora: str):
    if seguradora not in _CACHE:
        def _ou(lista):
            return re.compile("|".join(f"(?:{p})" for p in lista), re.DOTALL) if lista else None
        _CACHE[seguradora] = (
            _ou(FRONTEIRAS.get(seguradora, [])),
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


def zonas(eventos_da_sessao: Iterable[Dict[str, Any]],
          seguradora: str) -> Iterator[Tuple[Dict[str, Any], str, Optional[str]]]:
    """Devolve `(evento, zona, motivo)` para cada evento, em ordem de tempo.

    Zonas — 🔴 são TRÊS, não duas:

      URA      a seguradora falando por robô          → o corpus
      HUMANO   atendente da seguradora digitando      → preservada, insumo da 084
      ORFAO    `session_id is null`                   → fora de tudo + PENDENCIAS

    🔴 `ORFAO` existe porque **sem sessão não há "antes/depois da transferência"**.
    📊 493 eventos `in` (3,0%). E há fala humana entre eles: uma marca de
    fronteira da porto tem `session_id` nulo — sem esta zona ela entraria como URA.

    🔴 **NÃO existe zona CORRETORA.** A tela que cita a corretora **fica no
    corpus, mascarada**. 📊 Descartá-la tiraria 66 telas de URA, uma delas a tela
    do CPF da tokio — que é o ponto de entrada obrigatório do fio dela.
    """
    t_fronteira = None
    for e in sorted(eventos_da_sessao, key=lambda x: (x.get("wa_timestamp") or "")):
        if not _tem_sessao(e.get("session_id")):
            yield e, "ORFAO", "session_id nulo"
            continue
        n = norm_para_classificar(e.get("text") or "")
        if t_fronteira is None:
            motivo = e_fronteira(seguradora, n)
            if motivo:
                t_fronteira = e.get("wa_timestamp")
                # 🔴 A própria fronteira ainda é URA: é a URA anunciando.
                yield e, "URA", motivo
                continue
        yield e, ("HUMANO" if t_fronteira else "URA"), None


def guarda_de_completude_da_fronteira(
        acervo_por_seguradora: Dict[str, Dict[Any, List[Dict[str, Any]]]]
) -> Dict[str, Dict[str, Any]]:
    """🔴 A `FRONTEIRAS` perdeu alguém? — a pista do Founder virada guarda.

    Para cada seguradora, conta as sessões em que **alguém se apresenta pelo nome
    e não há nenhuma marca de fronteira antes**. Cada uma dessas é uma marca que
    falta na tabela.

    ```
    sessoes_com_apresentacao_sem_fronteira == 0   → VERDE
                                             > 0  → VERMELHO, e a tabela está incompleta
    ```

    🔴 **PROVADO NOS DOIS SENTIDOS** (CLAUDE.md §9.3), 📊 21/08/2026:

    ```
                 ANTES da mineração          DEPOIS
      porto        4 sem fronteira  🔴          0  ✅
      hdi          3                🔴          0  ✅
      yelum        3-4              🔴          0  ✅
      bradesco     2                🔴          0  ✅   (a tabela dizia `[]`)
      allianz      0                ✅          0  ✅
      zurich/tokio/alfa  0          ✅          0  ✅   (não há humano no acervo)
    ```

    **Um guarda que nunca esteve vermelho não prova nada.** Este esteve, em
    quatro seguradoras, e foi ele que produziu as marcas que a tabela ganhou.
    """
    fora: Dict[str, Dict[str, Any]] = {}
    for seg, sessoes in acervo_por_seguradora.items():
        com_apres: set = set()
        com_fronteira: set = set()
        for sid, eventos in sessoes.items():
            if not _tem_sessao(sid):
                continue
            for e, _zona, motivo in zonas(eventos, seg):
                if e.get("direction") != "in":
                    continue
                n = norm_para_classificar(e.get("text") or "")
                if motivo == "FRONTEIRA":
                    com_fronteira.add(sid)
                if tem_apresentacao_humana(seg, n):
                    com_apres.add(sid)
        orfas = com_apres - com_fronteira
        fora[seg] = {
            "com_apresentacao": len(com_apres),
            "com_fronteira": len(com_fronteira),
            "apresentacao_sem_fronteira": sorted(str(s)[:8] for s in orfas),
            "verde": not orfas,
        }
    return fora


# ─────────────────────────────────────────────────────────────────────────────
# O TESTE OBRIGATÓRIO DA TABELA (SPEC-084 §2.5.1.4)
# ─────────────────────────────────────────────────────────────────────────────
def cruzamento_fronteira_x_nao_fronteira() -> List[Tuple[str, str, str]]:
    """Todo padrão de `FRONTEIRAS` roda contra `NAO_E_FRONTEIRA`. Tem de dar ZERO.

    🔴 *"Um guarda sem controle negativo não distingue 'transferiu' de 'não
    conseguiu transferir'."* Devolve a lista de colisões — vazia é o esperado.
    """
    colisoes = []
    for seg, positivos in FRONTEIRAS.items():
        for negativo in NAO_E_FRONTEIRA.get(seg, []):
            # o padrão negativo é usado como TEXTO de exemplo, sem os metacaracteres
            exemplo = re.sub(r"[\\^$.|?*+()\[\]{}]", " ", negativo)
            exemplo = re.sub(r"\s+", " ", exemplo).strip()
            for p in positivos:
                if re.search(p, exemplo):
                    colisoes.append((seg, p, negativo))
    return colisoes


# 📊 Sessões cuja DIREÇÃO está invertida no banco — `direction='in'` assinado
#    pela corretora. Defeito de ingestão, achado pelo minerador da hdi:
#    *"7 sessões / 16 eventos com `in` começando por `{NOME} - resulta seguros`
#    ou `{NOME} - autofleet seguros`"*.
# 🔴 NÃO é a zona CORRETORA (que foi eliminada por medição) — é DADO ERRADO.
#    Sai do corpus e vai para `PENDENCIAS.md` com dono 🤖.
_RX_DIRECAO_INVERTIDA = re.compile(
    r"^\s*\{?nome\}?\s*-\s*(resulta|autofleet)|^\s*[a-z]{3,20}\s*-\s*(resulta|autofleet)")


def direcao_invertida(texto_norm: str) -> bool:
    """A mensagem `in` foi, na verdade, escrita pela corretora?

    ⚠️ CUIDADO — este é o oposto do caso legítimo. 📊 A URA da tokio SAÚDA a
    corretora pelo nome (*"olá, {NOME} - {CORRETORA} seguros! digite o cpf"*) e
    aquilo É tela de URA. O que distingue é a mensagem ser **só** a assinatura,
    sem tela em volta.
    """
    if not _RX_DIRECAO_INVERTIDA.match(texto_norm):
        return False
    # a tela da tokio continua com "digite o cpf/cnpj" etc. — texto longo.
    return len(texto_norm.strip()) <= 60
