"""Qual SERVIÇO o segurado pediu — SPEC-083 §5.5, com a cascata de dois níveis.

═══════════════════════════════════════════════════════════════════════════════
🔴 O DEFEITO QUE ESTE ARQUIVO CONSERTA, E ELE ORDENA A SPEC-084 INTEIRA
═══════════════════════════════════════════════════════════════════════════════

A tabela de demanda vinha contando **o CARDÁPIO** — a tela que LISTA os serviços —
e chamando isso de demanda. 📊 Medido em 21/08/2026, a diferença não é de grau:

```
serviço                ESCOLHIDO   (cardápio)   💭 a SPEC-083 §10.2 dizia
guincho / reboque          72         197            ~205
bateria / pane elétrica    16         106            ~113
encanador / hidráulica     14         132            ~152
eletricista                12         109            ~176
troca de pneu              10         101            ~105
eletrodoméstico             9         102            ~105
socorro mecânico            7          70             ~91
🔴 chaveiro                 5         210            ~213
🔴 vidro / para-brisa       1          77             ~79
🔴 telhado                  0          51              —
🔴 carro reserva            0          75              —
🔴 martelinho de ouro       0          57              —
```

> ## `chaveiro` despenca de 1º (210) para 8º (5). `guincho` vira líder isolado, 4,5× o segundo.

🔴 **`carro reserva` e `martelinho de ouro` aparecem em 75 e 57 sessões de cardápio
e em ZERO escolhas no acervo inteiro.** São itens de menu, não demanda.

**Ordenar a SPEC-084 pela coluna do cardápio mandaria construir chaveiro e vidro
primeiro — dois serviços com 5 e 1 pedidos reais em 573 sessões.**

═══════════════════════════════════════════════════════════════════════════════
A SOLUÇÃO É A MESMA CASCATA QUE JÁ RESOLVEU O RAMO (§8)
═══════════════════════════════════════════════════════════════════════════════

```
NÍVEL 1a · O PADRÃO-OURO   a própria seguradora nomeia o serviço na tela de
                           RESUMO. É a fonte mais precisa que existe.
                           📊 existe em 6 das 10 seguradoras.
NÍVEL 1b · A RESPOSTA      o primeiro `out` depois da tela de cardápio,
                           decodificado CONTRA AQUELA TELA.
NÍVEL 2  · O TEXTO         o que a corretora digitou, como RESERVA, sempre que
                           o nível 1 não decidiu.
```

🔴 **É CASCATA, não alternativa exclusiva** — o gatilho do nível 2 é *"o nível 1
não decidiu"*, e essa é a mesma lição que a §8 aprendeu para o ramo.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# NÍVEL 1a · O PADRÃO-OURO — a seguradora nomeando o serviço no resumo.
#
# ⚠️ 🔴 **A regex que a SPEC-083 §10 publicou NÃO REPRODUZ.**
#    📊 `\nservi[çc]o:[ ]*([^\n0-9][^\n]{0,60})` devolve **1 sessão**, não 37.
#    O separador não é quebra de linha — é o **asterisco de negrito do WhatsApp**:
#    o texto real é `*Serviço:* *encanador*;`.
#
#    A regex abaixo reproduz os **37** e os 19 rótulos, um a um.
#
# ⚠️ E a âncora de asterisco não é enfeite: 📊 sem ela, `servi[çc]o:` solto captura
#    241 eventos `in` da allianz, dos quais só 78 são o resumo. O resto é
#    disclaimer de cobertura — *"está coberto apenas a mão de obra necessária para
#    o serviço:"*, *"o serviço não será prestado em aparelhos…"*. Puro ruído.
# ─────────────────────────────────────────────────────────────────────────────
# 🔴 A ÂNCORA É O INÍCIO DE LINHA, NÃO O ASTERISCO — e a diferença é entre
#    112 sessões e ZERO.
#
# ⚠️ **Terceira ocorrência da mesma família de defeito nesta execução** — as
#    outras duas foram o `re.DOTALL` e as classes de acento. O padrão foi medido
#    sobre o texto **CRU**, onde o negrito do WhatsApp existe
#    (`*Serviço:* *encanador*`). A cascata roda sobre o texto **NORMALIZADO**, e
#    `_norm` **remove o `*`**.
#
# 📊 Medido em 21/08/2026 sobre `norm_para_classificar` do acervo inteiro:
#
# ```
#   regex                             sessões   casa o disclaimer?
#   \*servi[çc]o\*?:   (o publicado)        0   —              MORTO
#   (?m)^servi[cç]o\s*:   (este)          112   NAO   ✅
#   servi[cç]o\s*:   (sem âncora)         158   SIM   🔴   envenenado
# ```
#
# 🔴 O CONTROLE que dá o direito: o disclaimer que a própria SPEC-083 §10 avisa
#    que polui — *"está coberto apenas a mão de obra necessária para o serviço:"*
#    — **não casa** o padrão ancorado em linha, e **casa** o largo.
PADRAO_OURO = (
    # o resumo da URA — 📊 112 sessões em 10 seguradoras, sobre texto normalizado
    re.compile(r"(?m)^servi[çc]o\s*:\s*([^\n;]{1,55})", re.IGNORECASE),
    # a confirmação de abertura — 📊 hdi e yelum
    re.compile(r"sua solicita[çc][ãa]o de ([^*\n]{2,40}) foi aberta", re.IGNORECASE),
)

# 🔴 O DESEMPATE, e ele resolve um caso que a SPEC não previa.
#
# 📊 A URA da Allianz **não nomeia "máquina de lavar" no campo `Serviço:`** — ela
#    escreve `Serviço: conserto de eletrodoméstico` e põe o aparelho na linha
#    seguinte: `Problema: máquina de lavar roupas`.
#
#    E o corredor `allianz-residencial` tem `maquina_de_lavar` **E**
#    `eletrodomesticos` como **rotas separadas**. Sem este desempate, a rota de
#    referência do produto sai `SEM_CORPUS` — ela existe no acervo e o filtro não
#    a encontra.
#
# ⚠️ 📊 O campo é texto livre e só a allianz o usa (16 sessões, `maquina de lavar
#    roupas` em 5). Por isso ele **refina**, nunca decide sozinho: só troca o
#    rótulo genérico por um subserviço que o **PRÓPRIO PLAYBOOK** declara —
#    nunca inventa serviço que o corredor não tem.
CAMPO_PROBLEMA = re.compile(r"(?m)^problema\s*:\s*([^\n;]{1,60})", re.IGNORECASE)

# os rótulos genéricos que pedem desempate — 📊 medidos no acervo
SERVICOS_GENERICOS = frozenset({"eletrodomesticos", "eletrodomestico",
                                "conserto residencial", "assistencia"})

# 🔴 As 4 seguradoras SEM padrão-ouro, declaradas — nunca implícitas:
#    `tokio` · `bradesco` · `zurich` · `mapfre` não têm nenhuma tela em que a
#    própria seguradora nomeie o serviço executado. Nelas o nível 1 depende
#    inteiramente da resposta ao cardápio (1b), e onde nem isso existe, a rota
#    fica sem demanda medida — o que vai para o relatório, não para o silêncio.
SEM_PADRAO_OURO = ("tokio", "bradesco", "zurich", "mapfre")


# ─────────────────────────────────────────────────────────────────────────────
# NÍVEL 1b · A RESPOSTA À TELA DE CARDÁPIO.
#
# 🔴 **A tecla só significa alguma coisa CONTRA A TELA que a ofereceu.**
#    📊 Duas medições provam que decodificar tecla sem casar a tela erra:
#
#    azul, duas variantes do MESMO menu:
#       botões:   guincho · bateria · chaveiro-veículo · técnico · táxi
#       numerada: 1 guincho · 2 bateria · 3 troca de pneu · 4 chaveiro · 5 vidro
#       🔴 a posição 3 é `chaveiro` numa e `pneu` na outra.
#
#    allianz, duas variantes de `vamos lá! informe o tipo de serviço`:
#       v1: 1 emergenciais · 2 eletrodomésticos · 3 outros
#       v2: 1 para minha casa · 2 substituição de telhas · 3 outros
#
#    Por isso a chave do dicionário é **a tela**, não a seguradora.
# ─────────────────────────────────────────────────────────────────────────────
MENUS_DE_SERVICO: List[Dict[str, Any]] = [
    # ── allianz ──────────────────────────────────────────────────────────────
    {"seguradora": "allianz", "sessoes": 21,
     "tela": r"o que voc[êe] precisa\?.{0,60}pane el[ée]trica, recarga de bateria",
     # ⚠️ 📊 ARMADILHA CONFIRMADA: este menu usa **travessão – (U+2013)**, não
     #    hífen. Um detector com `\d+\s*-\s` NÃO VÊ este menu e classifica as 21
     #    sessões como texto livre.
     "teclas": {"1": "bateria", "2": "alarme", "3": "guincho", "4": "guincho",
                "5": "combustivel", "6": "pneu", "7": "chaveiro"}},
    {"seguradora": "allianz", "sessoes": 15,
     "tela": r"de qual profissional\?",
     "teclas": {"1": "eletricista", "2": "encanador", "3": "desentupimento",
                "4": "chaveiro", "5": None}},
    {"seguradora": "allianz", "sessoes": 6,
     "tela": r"qual eletrodom[ée]stico precisa de conserto",
     "teclas": {"1": "eletrodomestico", "2": "ar_condicionado",
                "3": "eletrodomestico", "4": None}},
    {"seguradora": "allianz", "sessoes": 54,
     "tela": r"vamos l[áa]! informe o tipo de servi[çc]o.{0,80}emergenciais",
     # 🔴 NAVEGAÇÃO, não escolha: as teclas levam a submenus. `3` é a saída.
     "teclas": {"1": None, "2": None, "3": None}},
    {"seguradora": "allianz", "sessoes": 42,
     # 🔴 A TELA QUE NENHUM DETECTOR ACHARIA. 📊 42 sessões, e ela **não contém
     #    nenhuma palavra do vocabulário de serviço** (nada de guincho, chaveiro,
     #    vidro). Foi achada só rastreando o que vem DEPOIS da tecla `3`.
     #    ⚠️ E o destino dominante dela é a FUGA — ver `CAMINHO_DE_FUGA` abaixo.
     "tela": r"qual desses servi[çc]os,? voc[êe] precisa\?",
     "teclas": {"1": "dedetizacao", "2": "limpeza", "3": "limpeza_caixa_dagua",
                "4": "telhado", "5": "telhado", "6": "pet", "7": None, "8": None}},
    # ── alfa ─────────────────────────────────────────────────────────────────
    {"seguradora": "alfa", "sessoes": 5,
     "tela": r"o que voc[êe] precisa\?.{0,60}pane el[ée]trica, recarga de bateria",
     "teclas": {"1": "bateria", "2": "alarme", "3": "guincho", "4": "guincho",
                "5": "combustivel", "6": "pneu", "7": "chaveiro"}},
    # ── azul ── 🔴 as duas variantes, e elas são INCOMPATÍVEIS por posição ────
    {"seguradora": "azul", "sessoes": 8,
     "tela": r"o que voc[êe] precisa\?.{0,80}guincho \(reboque\).{0,40}bateria",
     "rotulos": {"guincho (reboque)": "guincho", "bateria": "bateria",
                 "chaveiro para veiculo": "chaveiro", "tecnico": "tecnico",
                 "taxi": "taxi"}},
    {"seguradora": "azul", "sessoes": 3,
     "tela": r"o que voc[êe] precisa\?.{0,40}\*1\*\s*-\s*guincho",
     "teclas": {"1": "guincho", "2": "bateria", "3": "pneu", "4": "chaveiro",
                "5": "vidro", "6": "alarme", "7": None, "8": None}},
    # ── bradesco ─────────────────────────────────────────────────────────────
    {"seguradora": "bradesco", "sessoes": 7,
     "tela": r"qual o problema com o seu carro",
     # 🔴 `1` é PANE — e sozinho NÃO distingue bateria de guincho. A tela que
     #    separa é a seguinte, e ela existe: ver `DESEMPATE` abaixo.
     "teclas": {"1": None, "2": "acidente", "3": "pneu", "4": "chaveiro",
                "5": "combustivel", "6": "taxi", "7": None}},
    # ── porto ────────────────────────────────────────────────────────────────
    {"seguradora": "porto", "sessoes": 13,
     "tela": r"o que voc[êe] precisa\?.{0,80}guincho \(reboque\)",
     "rotulos": {"guincho (reboque)": "guincho", "bateria": "bateria",
                 "chaveiro para veiculo": "chaveiro", "troca de pneu": "pneu",
                 "conserto de vidro": "vidro", "tecnico": "tecnico", "taxi": "taxi"}},
    {"seguradora": "porto", "sessoes": 3,
     "tela": r"listamos abaixo os servi[çc]os dispon[íi]veis.{0,60}eletrodom",
     "rotulos": {"eletrodomesticos": "eletrodomestico",
                 "encanador (hidraulica)": "encanador", "eletricista": "eletricista",
                 "chaveiro residencial": "chaveiro", "chuveiro": "chuveiro",
                 "reparo em telha": "telhado"}},
    # ── hdi e yelum — a FAMÍLIA compartilhada (📊 165 telas idênticas) ────────
    {"seguradora": "hdi", "sessoes": 6,
     "tela": r"qual (o|[ée] o) servi[çc]o que voc[êe] precisa",
     "rotulos": {"encanador": "encanador", "desentupimento": "desentupimento",
                 "eletricista": "eletricista", "chaveiro": "chaveiro",
                 "linha branca": "eletrodomestico", "ar condicionado": "ar_condicionado"}},
    {"seguradora": "yelum", "sessoes": 6,
     "tela": r"qual (o|[ée] o) servi[çc]o que voc[êe] precisa",
     "rotulos": {"encanador": "encanador", "desentupimento": "desentupimento",
                 "eletricista": "eletricista", "chaveiro": "chaveiro",
                 "linha branca": "eletrodomestico", "ar condicionado": "ar_condicionado"}},
    # ── tokio ── 📊 o menu para no nível ASSUNTO; não nomeia serviço ─────────
    {"seguradora": "tokio", "sessoes": 7,
     "tela": r"menu de servi[çc]os do \*?seguro autom[óo]vel",
     "rotulos": {"guincho/assist.24h": "guincho", "guincho/assist. auto": "guincho"}},
    # ── zurich ── 📊 a ÚNICA tela de escolha do acervo, 2 sessões ────────────
    {"seguradora": "zurich", "sessoes": 2,
     "tela": r"me conte o que aconteceu",
     # ⚠️ 📊 A tarefa dizia "menu de panes com 13 opções". **Não existe.** O maior
     #    menu numerado da zurich tem 8 opções. Os demais `*1*/*2*` são sim/não.
     "teclas": {"1": "combustivel", "2": "pneu", "3": "chaveiro", "4": None,
                "5": "acidente", "6": "guincho", "7": None, "8": None}},
]

# 🔴 O DESEMPATE do bradesco — a tela POSTERIOR à tecla que não distingue.
#    📊 4 sessões, texto único, e resolve 2 das 8 rotas indistinguíveis do produto:
DESEMPATE: List[Dict[str, Any]] = [
    {"seguradora": "bradesco", "sessoes": 4,
     "depois_de": r"qual o problema com o seu carro",
     "tela": r"me conta o que aconteceu",
     "teclas": {"1": "bateria",   # "o veículo estava estacionado e não liga"
                "2": "guincho"},  # "o veículo estava andando e parou de funcionar"
     "resolve": ("bradesco", "guincho", "bateria")},
]

# ⚠️ 📊 O caminho DOMINANTE da allianz não é escolha de serviço — é FUGA.
#    `3` (outros serviços) → `7` (outros) → *"vou transferir seu caso para um
#    especialista"* em **39 de 39 sessões** (27% do acervo da allianz).
#    🔴 Isso significa que os 81 `chaveiro` e 55 `eletrodomestico` do CARDÁPIO da
#    allianz são, em boa parte, a corretora **atravessando a URA para chegar num
#    humano** — não demanda. É a explicação medida do colapso 210 → 5.
CAMINHO_DE_FUGA = {
    "allianz": {"tela": r"qual desses servi[çc]os,? voc[êe] precisa\?",
                "tecla": "7", "sessoes": 39, "destino": "transferencia_humana"},
}


# ─────────────────────────────────────────────────────────────────────────────
# NÍVEL 2 · O TEXTO DIGITADO PELA CORRETORA — a reserva.
#
# 🔴 **`direction='out'` é OBRIGATÓRIO.** Sobre `in` o padrão casa o cardápio, e é
#    exatamente daí que veio o defeito que este arquivo conserta.
#
# 📊 Nenhum destes passa de 25% das sessões de nenhuma seguradora — nenhum é
#    `PADRAO_INDISCRIMINADO`, e todos marcam MENOS que o cardápio correspondente
#    (allianz: guincho 33 no cardápio × 17 no texto; chaveiro 81 × **0**).
#    **O nível 2 é sadio; o problema estava inteiramente no `in`.**
# ─────────────────────────────────────────────────────────────────────────────
PADROES_DE_SERVICO_TEXTO: Dict[str, str] = {
    "guincho":          r"guincho|reboque|rebocar",
    "bateria":          r"bateria|pane el[ée]trica|recarga",
    "encanador":        r"encanador|hidr[áa]ulic|vazamento",
    "eletricista":      r"eletricista|reparo el[ée]trico|tomada queimada",
    "pneu":             r"pneu|borracheiro|estepe",
    "eletrodomestico":  r"eletrodom[ée]stic|linha branca|m[áa]quina de lavar|lavadora",
    "socorro_mecanico": r"socorro mec[âa]nic|mec[âa]nico",
    "chaveiro":         r"chaveiro|chave.{0,12}(perdida|quebrada|trancad)",
    "vidro":            r"vidro|para.?brisa|retrovisor",
    "desentupimento":   r"desentupi",
    "ar_condicionado":  r"ar.condicionado",
    "telhado":          r"telhado|telha",
    "taxi":             r"t[áa]xi",
    "carro_reserva":    r"carro reserva",
    # 🔴 OS QUE A REGUA CHAMAVA DE SEM_CORPUS COM O ACERVO CHEIO — 22/08/2026.
    #
    # 📊 `?tecnico` tinha **109 linhas** (azul 33 + porto 76) e a rota aparecia
    #    SEM_CORPUS. O `?` e o balde de nao-classificado: o rotulo era LIDO da
    #    tela e nao tinha para onde ir. Mandar essa rota para coleta e o erro
    #    que a SPEC-084 §7.2 nomeia — coletar o que ja esta coletado.
    #
    # ⚠️ `t[ée]cnico` sozinho seria largo demais: "visita tecnica" aparece no
    #    fluxo de eletrodomestico e de bateria nova. Por isso ele exige a forma
    #    do ROTULO DE MENU, e nao a palavra solta.
    # ⚠️ E ELE E ANCORADO NO INICIO, de proposito -- 22/08/2026.
    #    A primeira versao aceitava `assist[ê]ncia de um técnico` em qualquer
    #    lugar do texto, e o NIVEL 2 le o que a CORRETORA escreveu. 📊 Uma
    #    sessao de encanador da allianz virou `tecnico` porque a atendente
    #    escreveu a palavra na conversa.
    #    🔴 A palavra da corretora NAO e o nome do servico. Este padrao so
    #    vale como ROTULO DE MENU, e por isso exige o inicio da string.
    "tecnico":              r"^t[ée]cnico$|^t[ée]cnico para ",
    "bateria_nova":         r"bateria nova|nova bateria",
    "limpeza_caixa_dagua":  r"limpeza de caixa d.?[áa]gua|limpeza da caixa",
    "consulta_veterinaria": r"consulta veterin[áa]ria|veterin[áa]ri",
}

# ⚠️ `eletricista` RESIDENCIAL não é "parte elétrica" de AUTO — a SPEC-083 §5.5
#    alerta para isso. 📊 Mas a medição INVERTEU a causa na porto: `parte el[ée]trica`
#    (auto) = **0 sessões**; as 24 vêm do menu residencial. O confundidor real não
#    é o ramo — é o CARDÁPIO, que este arquivo resolve exigindo `out`.


# ─────────────────────────────────────────────────────────────────────────────
# 🔴 A REGRA DO EMPATE — ela pega o que o teste dos 80% deixa passar.
# ─────────────────────────────────────────────────────────────────────────────
def empates_sao_cardapio(contagens: Dict[str, int], minimo: int = 3) -> List[Tuple[int, List[str]]]:
    """Serviços com a MESMA contagem na mesma seguradora são UMA TELA, não N sinais.

    📊 Medido em 21/08/2026 — o teste dos 80% só reprova a azul (88,9%), mas o
    teste do empate pega quatro:

    ```
    azul     guincho = chaveiro = vidro = martelinho = carro reserva = 16
    zurich   guincho = chaveiro = vidro = pneu = mecânico = 9
    alfa     guincho = chaveiro = bateria = pneu = 5
    tokio    vidro = martelinho = para-brisa = lataria = 7   (e 11 eventos)
    ```

    Em todos os quatro, a causa é **uma única tela de menu** que enumera os
    serviços numa frase só. `PADRAO_DE_CARDAPIO`.
    """
    por_contagem: Dict[int, List[str]] = {}
    for servico, n in contagens.items():
        if n > 0:
            por_contagem.setdefault(n, []).append(servico)
    return sorted(((n, sorted(s)) for n, s in por_contagem.items() if len(s) >= minimo),
                  reverse=True)


def _norm_rotulo(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.replace("*", "").lower()).strip()


def _canonizar(chave: Optional[str], playbook: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Traduz o rótulo da cascata para o nome do subserviço NO CORREDOR.

    🔴 **A autoridade é `canonical_subservice`, do produto — nunca uma tabela nova.**

    ⚠️ 📊 Achado por medição: a cascata devolvia `eletrodomestico` e o corredor
    chama a rota de `eletrodomesticos` (plural) e de `maquina_de_lavar`. Com as
    duas taxonomias soltas, a rota de referência saiu **`SEM_CORPUS`** — ela
    existia no acervo e o filtro não a encontrava.

    E quando o playbook é conhecido, o nome dele vence: 📊 `allianz-residencial`
    tem **`maquina_de_lavar` E `eletrodomesticos` como rotas separadas**, e a
    cascata não distingue as duas sozinha — quem distingue é o texto do rótulo.
    """
    if not chave:
        return None
    try:
        canon = M_CANONICAL(chave)
    except Exception:  # noqa: BLE001
        canon = chave
    if playbook is None:
        return canon
    subs = playbook.get("subservices") or {}
    if canon in subs:
        return canon
    if chave in subs:
        return chave
    return canon


M_CANONICAL = None   # injetado por `medir_rota`/`gerar_corpus` para evitar
                     # import circular; ver `ligar_resolvedor()`


def ligar_resolvedor(fn) -> None:
    """Recebe `canonical_subservice` do motor. 🔴 Sem tabela paralela."""
    global M_CANONICAL
    M_CANONICAL = fn


def servico_da_sessao(seguradora: str,
                      pares: List[Tuple[str, str]],
                      playbook: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], str]:
    """`[(direction, texto_normalizado), ...]` -> `(servico, nivel_que_decidiu)`.

    A cascata inteira: padrão-ouro → resposta ao cardápio → texto da corretora.
    """
    # ── NÍVEL 1a-bis · o DESEMPATE pelo campo `problema:` ────────────────────
    #    Só roda quando o padrão-ouro deu um rótulo GENÉRICO e o playbook tem um
    #    subserviço mais específico. Nunca inventa serviço que o corredor não tem.
    def _desempatar(servico_generico: str) -> Optional[str]:
        if not playbook or servico_generico not in SERVICOS_GENERICOS:
            return None
        subs = [x for x in (playbook.get("subservices") or {})
                if x != servico_generico]
        for _direcao, texto in pares:
            m = CAMPO_PROBLEMA.search(texto)
            if not m:
                continue
            problema = m.group(1).lower()
            for sub in sorted(subs, key=len, reverse=True):
                if re.search(re.escape(sub.replace("_", " ")), problema):
                    return sub
        return None

    # ── NÍVEL 1a · o padrão-ouro ─────────────────────────────────────────────
    for direcao, texto in pares:
        if direcao != "in":
            continue
        for rx in PADRAO_OURO:
            m = rx.search(texto)
            if m:
                rotulo = _norm_rotulo(m.group(1))
                # 🔴 O rotulo LITERAL da seguradora primeiro: e ele que
                #    distingue `maquina de lavar` de `eletrodomesticos` na
                #    allianz, onde as duas sao rotas separadas.
                if playbook:
                    for sub in (playbook.get("subservices") or {}):
                        if re.search(re.escape(sub.replace("_", " ")), rotulo):
                            return sub, "nivel-1a-padrao-ouro"
                for chave, padrao in PADROES_DE_SERVICO_TEXTO.items():
                    if re.search(padrao, rotulo):
                        achado = _canonizar(chave, playbook)
                        fino = _desempatar(achado or "")
                        if fino:
                            return fino, "nivel-1a-ouro+problema"
                        return achado, "nivel-1a-padrao-ouro"
                # 🔴 rotulo que a seguradora nomeia e o CODIGO nao tem: e achado
                #    para a SPEC-084, nao ruido. 📊 `consulta veterinaria`,
                #    `pet assistance`, `limpeza de caixa d agua`.
                return f"?{rotulo[:30]}", "nivel-1a-rotulo-desconhecido"

    # ── NÍVEL 1b · a resposta ao cardápio, decodificada CONTRA AQUELA TELA ───
    for menu in MENUS_DE_SERVICO:
        if menu["seguradora"] != seguradora:
            continue
        rx_tela = re.compile(menu["tela"], re.DOTALL | re.IGNORECASE)
        for i, (direcao, texto) in enumerate(pares):
            if direcao != "in" or not rx_tela.search(texto):
                continue
            for direcao2, resposta in pares[i + 1:]:
                if direcao2 != "out":
                    continue
                r = _norm_rotulo(resposta)
                if not r:
                    continue
                alvo = (menu.get("teclas") or {}).get(r)
                if alvo is None and "rotulos" in menu:
                    for rot, srv in menu["rotulos"].items():
                        if _norm_rotulo(rot) == r:
                            alvo = srv
                            break
                if alvo:
                    return _canonizar(alvo, playbook), "nivel-1b-resposta"
                break   # o PRIMEIRO `out` é a resposta

    # ── NÍVEL 2 · o texto da corretora — só `out`, nunca `in` ────────────────
    for direcao, texto in pares:
        if direcao != "out":
            continue
        if playbook:
            for sub in (playbook.get("subservices") or {}):
                if re.search(re.escape(sub.replace("_", " ")), texto):
                    return sub, "nivel-2-texto"
        for chave, padrao in PADROES_DE_SERVICO_TEXTO.items():
            if re.search(padrao, texto):
                return _canonizar(chave, playbook), "nivel-2-texto"
    return None, "-"


# 📊 O ranking medido em 21/08/2026 — a coluna que ordena a SPEC-084.
#    🔴 Guardado como DADO, não como comentário, para o inventário do Bloco D
#    poder citá-lo sem recalcular.
DEMANDA_MEDIDA: List[Tuple[str, int, int]] = [
    # (servico, ESCOLHIDO, no_cardapio)
    ("guincho", 72, 197), ("bateria", 16, 106), ("encanador", 14, 132),
    ("eletricista", 12, 109), ("pneu", 10, 101), ("eletrodomestico", 9, 102),
    ("socorro_mecanico", 7, 70), ("chaveiro", 5, 210), ("conserto_residencial", 3, 0),
    ("tecnico", 3, 0), ("ar_condicionado", 2, 0), ("limpeza_caixa_dagua", 2, 0),
    ("pet", 2, 0), ("desentupimento", 1, 41), ("taxi", 1, 58), ("vidro", 1, 77),
    ("telhado", 0, 51), ("carro_reserva", 0, 75), ("martelinho", 0, 57),
]
