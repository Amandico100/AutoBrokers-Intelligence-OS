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
# ─────────────────────────────────────────────────────────────────────────────
# 🔴 SPEC-119 F1 · AS QUATRO FORMAS QUE FALTAVAM — cada uma com a seguradora, a
#    frase REAL e a contagem, medidas no MESMO motor (Python) sobre o MESMO
#    texto (`norm_para_classificar`) em que vão rodar. CLAUDE.md §9.4.
#
# ⛔ O que NÃO entrou, e por quê: um padrão largo `servi[çc]o de (…)` casaria
#    **os disclaimers de cobertura** que a SPEC-083 §10 já avisou que envenenam
#    — 📊 `"esse servico de troca e coberto para lampadas comuns"`,
#    `"sua apolice nao contempla o servico de limpeza de exaustor"`,
#    `"o servico de encanador reparo hidraulico cobrira os custos"`. Por isso
#    cada padrão novo é ancorado no **VERBO DE ENVIO** da seguradora
#    (`enviaremos`, `vamos enviar`, `segue`), nunca na palavra `serviço` solta.
#
# 📊 Medido em 27/09/2026 — comando:
#    `python scratchpad/testar_padrao.py acervo.json "<o padrão>"`, que roda
#    `re.search` sobre `norm_para_classificar` de TODOS os eventos `in` de
#    `observed_events` (555 sessões, 10 seguradoras).
#
# ```
#   padrão                                        sessões          rótulos capturados
#   neste caso enviaremos o servico de (…) para   hdi 15 · yelum 15  guincho 28 · troca de pneus 4 · chaveiro 1
#   entao vamos enviar um (…)                     bradesco 5         reboque 8
#   segue o servico de (…)                        allianz 14         reboque 15
#   da pra resolver com a assistencia de um (…)   bradesco 2         tecnico 2
# ```
# ─────────────────────────────────────────────────────────────────────────────
PADRAO_OURO = (
    # o resumo da URA — 📊 112 sessões em 10 seguradoras, sobre texto normalizado
    re.compile(r"(?m)^servi[çc]o\s*:\s*([^\n;]{1,55})", re.IGNORECASE),
    # a confirmação de abertura — 📊 hdi e yelum
    #
    # 🔴 `(?:a|sua)`, e não só `sua`, por MEDIÇÃO — 27/09/2026. A HDI escreve as
    #    duas formas: *"sua solicitacao de guincho foi aberta com sucesso"* e
    #    *"a solicitacao de guincho para a assistencia 9257546 foi aberta com
    #    sucesso"*. 📊 só `sua` = hdi 13 · yelum 17; com `(?:a|sua)` = hdi **15**
    #    · yelum 17. As 2 sessões a mais percorrem um guincho inteiro.
    re.compile(r"\b(?:a|sua) solicita[çc][ãa]o de ([^*\n]{2,40}) foi aberta",
               re.IGNORECASE),
    # 🔴 hdi e yelum · a frase REAL: *"neste caso enviaremos o servico de guincho
    #    para atende-lo(a)."* — 📊 hdi 15 sessões · yelum 15; `guincho` 28,
    #    `troca de pneus` 4, `chaveiro` 1.
    #    ⚠️ A âncora `para atende` é o que separa o ENVIO do disclaimer.
    re.compile(r"neste caso enviaremos o servi[çc]o de ([^\n.]{2,40}) para atende",
               re.IGNORECASE),
    # 🔴 bradesco · a frase REAL: *"certo, entao vamos enviar um reboque. me diz:
    #    o veiculo esta em garagem subsolo?"* — 📊 5 sessões, `reboque` 8×.
    #    ⚠️ É a PRIMEIRA forma de padrão-ouro que a bradesco tem: até 27/09/2026
    #    ela estava em `SEM_PADRAO_OURO`.
    re.compile(r"entao vamos enviar um ([^\n.]{2,30})", re.IGNORECASE),
    # 🔴 allianz · a frase REAL: *"segue o servico de reboque, com previsao de 60
    #    min para a chegada no local"* — 📊 14 sessões, `reboque` 15×.
    #    ⚠️ Vírgula e ponto fora da classe, senão a captura engole a previsão.
    re.compile(r"segue o servi[çc]o de ([^\n,.]{2,30})", re.IGNORECASE),
    # 🔴 bradesco · a frase REAL: *"certo! esse problema da pra resolver com a
    #    assistencia de um tecnico. posso confirmar esse servico?"* — 📊 2 sessões,
    #    `tecnico` 2×.
    re.compile(r"da pra resolver com a assistencia de um ([^\n.]{2,30})",
               re.IGNORECASE),
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

# 🔴 As seguradoras SEM padrão-ouro, declaradas — nunca implícitas.
#
# ⚠️ Eram QUATRO até 27/09/2026. A **bradesco saiu**: ela nomeia o serviço em
#    *"certo, entao vamos enviar um reboque"* (📊 5 sessões) e em *"esse problema
#    da pra resolver com a assistencia de um tecnico"* (📊 2 sessões) — as duas
#    formas estão em `PADRAO_OURO` acima.
#
# 📊 As três que CONTINUAM cegas ao nível 1a, e o motivo medido de cada uma
#    (comando: varredura de `re.search` sobre todos os eventos `in` do acervo,
#    procurando qualquer frase em que a seguradora nomeie o serviço executado):
#
# ```
#   tokio    o desfecho é LINK, nunca serviço executado pela URA: *"o servico de
#            aviso de sinistro automovel esta pronto para voce ⬇ https://…"*.
#            📊 7 sessões. A SPEC-119 §4 já declara a Tokio como handoff.
#   zurich   fecha com *"sua assistencia foi solicitada! numero da solicitacao:
#            71020124"* — protocolo SIM, nome do serviço NÃO. 📊 2 sessões.
#   mapfre   🔴 o acervo NÃO TEM NENHUMA sessão de assistência. 📊 Das 18 telas
#            de menu de assunto, as respostas foram `pagamento` 14 ·
#            `sinistro` 3 · `carro reserva` 1. ZERO `assistencia`. Não há o que
#            ler: a tela de confirmação de guincho da Mapfre não existe no acervo.
# ```
SEM_PADRAO_OURO = ("tokio", "zurich", "mapfre")


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
    # ── azul ── 🔴 SPEC-119 · o menu de PRIMEIRO nível, que faltava ──────────
    #
    # 📊 12 sessões. A frase real: *"selecione uma opcao, por favor."* seguida de
    #    `assistencia emergencial / guincho, tecnico e chaveiro`, `sinistro`,
    #    `vidros e farois / atendimento para vidros, farois e retrovisores`,
    #    `martelinho de ouro`, `carro reserva`, `transporte por app`, …
    #    Respostas medidas: `assistencia emergencial` 9 · `carro reserva` 1 ·
    #    `martelinho de ouro` 1 · `sinistro` 1 · (e 4 pedidos de humano).
    #
    # 🔴 CLAUDE.md §9.5 — NAVEGAR × DECIDIR, e aqui as duas convivem na MESMA
    #    tela. `assistencia emergencial` **navega** (leva ao submenu
    #    `o que voce precisa?`, que já está cadastrado acima) → `None`.
    #    `vidros e farois` e `carro reserva` **decidem** o serviço → rótulo.
    {"seguradora": "azul", "sessoes": 12,
     "tela": r"selecione uma op[çc][ãa]o, por favor\.{0,3}\s*\n\s*assist[êe]ncia emergencial",
     "rotulos": {
         # DECIDEM — a tecla escolhe o conteúdo do atendimento
         "vidros e farois": "vidro",
         "martelinho de ouro": "martelinho",
         "carro reserva": "carro_reserva",
         # NAVEGAM — levam a outro menu; quem decide é o de baixo
         "assistencia emergencial": None,
         "sinistro": None, "transporte por app": None, "financeiro": None,
         "apolice": None, "cartao de credito porto": None,
         "contratar um seguro azul": None}},
    # ── porto E azul ── 🔴 SPEC-119 · a tela de REMOÇÃO, o guincho que faltava ─
    #
    # 📊 A frase real, em DUAS variações do mesmo texto:
    #    *"por favor, selecione a opcao que **descreve** melhor a sua
    #    necessidade."* (porto 10 ses · azul 5 ses) e *"…que **atende** melhor a
    #    sua necessidade."* (porto 6 ses), ambas com
    #    `remocao de veiculo / preciso de reboque para remover o veiculo do local`
    #    e `envolvimento em acidente / preciso informar sobre acidentes,
    #    incendios ou enchentes`.
    #
    # 📊 A resposta é UNÂNIME no acervo: `remocao de veiculo` em 21 de 21 sessões.
    # ⚠️ `(descreve|atende)` é ALTERNÂNCIA MEDIDA, não generalização: as duas
    #    formas estão no acervo, e nenhuma terceira.
    {"seguradora": "porto", "sessoes": 16,
     "tela": r"selecione a op[çc][ãa]o que (descreve|atende) melhor a sua necessidade",
     "rotulos": {"remocao de veiculo": "guincho",
                 "envolvimento em acidente": "acidente",
                 "nao encontrei o assunto": None, "voltar": None}},
    {"seguradora": "azul", "sessoes": 5,
     "tela": r"selecione a op[çc][ãa]o que (descreve|atende) melhor a sua necessidade",
     "rotulos": {"remocao de veiculo": "guincho",
                 "envolvimento em acidente": "acidente",
                 "nao encontrei o assunto": None, "voltar": None}},
    # ── porto ── o menu de PRIMEIRO nível: puro NAVEGAR, declarado ────────────
    #
    # 📊 17 sessões. *"como eu posso te ajudar?"* +
    #    `servicos para veiculo / assistencia emergencial como: guincho, tecnico,
    #    chaveiro ou taxi.` · `servicos para residencia / assistencia de eletrica,
    #    hidraulica e conserto de eletrodomesticos` · `sinistro de automovel` ·
    #    `assuntos financeiros` · `apolice e coberturas`.
    #
    # 🔴 TODAS as teclas são `None` DE PROPÓSITO, e isso é informação, não
    #    omissão: esta tela escolhe o RAMO e o ASSUNTO, nunca o serviço. Quem
    #    decide o serviço é a tela seguinte (`o que voce precisa?`, já cadastrada).
    #    ⚠️ Sem esta entrada escrita, o próximo leitor mediria o cardápio desta
    #    tela e contaria `guincho`, `chaveiro` e `taxi` como demanda — o defeito
    #    exato que o cabeçalho deste arquivo conserta.
    {"seguradora": "porto", "sessoes": 17,
     "tela": r"como eu posso te ajudar\?.{0,40}servi[çc]os para ve[íi]culo",
     "rotulos": {"servicos para veiculo": None, "servicos para residencia": None,
                 "sinistro de automovel": None, "assuntos financeiros": None,
                 "apolice e coberturas": None, "voltar": None}},
    # ── bradesco ─────────────────────────────────────────────────────────────
    {"seguradora": "bradesco", "sessoes": 7,
     "tela": r"qual o problema com o seu carro",
     # 🔴 `1` é PANE — e sozinho NÃO distingue TÉCNICO de guincho. A tela que
     #    separa é a seguinte, e ela existe: ver `DESEMPATE` abaixo.
     # ⚠️ 📊 A frase real da tela, medida em 27/09/2026 (6 sessões): *"entendi, mas
     #    pra eu te ajudar, preciso entender qual o problema com o seu carro:"* —
     #    o regex abaixo casa o trecho final dela.
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
    #
    # 🔴 SPEC-119 · AMPLIADO com os rótulos que a própria tela enumera. 📊 5
    #    sessões, a frase real: *"clique no botao abaixo para acessar o menu de
    #    servicos do seguro automovel 🚙"* + `guincho/assist.24h / guincho,
    #    chaveiro, pane e pneus furados` · `informacoes sinistro` ·
    #    `pagamentos/pix` · `2a via da apolice` · `roda, pneu e suspensao /
    #    reparo ou troca` · `servicos para vidros / reparo ou reposicao do
    #    para-brisa, vidros laterais ou traseiro` · `lataria ou pintura` ·
    #    `para-choque/martelinho` · `cartao digital` · `outros servicos`.
    #    Respostas medidas: `informacoes sinistro` 3 · `outros servicos` 2 ·
    #    `guincho/assist.24h` 2.
    {"seguradora": "tokio", "sessoes": 7,
     "tela": r"menu de servi[çc]os do \*?seguro autom[óo]vel",
     "rotulos": {"guincho/assist.24h": "guincho", "guincho/assist. auto": "guincho",
                 # DECIDEM
                 "servicos para vidros": "vidro",
                 "para-choque/martelinho": "martelinho",
                 # NAVEGAM ou saem do escopo de corredor
                 "informacoes sinistro": None, "pagamentos/pix": None,
                 "2a via da apolice": None, "roda, pneu e suspensao": None,
                 "lataria ou pintura": None, "cartao digital": None,
                 "outros servicos": None}},
    # ── zurich ── 🔴 SPEC-119 · eram 36 de 253 telas; agora as três telas reais ─
    #
    # 📊 ① O menu de PRIMEIRO nível, 5 sessões. A frase real: *"agora escolha um
    #    dos servicos para continuar 😊"* + `assistencia 24h / solicite a
    #    assistencia 24h para o seu carro ou moto` · `assistencia a vidros /
    #    consulte como solicitar assistencia para danos a vidros` · `sinistro` ·
    #    `carro reserva / solicite um carro reserva apos abrir o seu sinistro` ·
    #    `consultar pagamentos` · `consultar apolice` · `atendimento a oficinas` ·
    #    `outros servicos`. Respostas medidas: `assistencia 24h` 4 · `sinistro` 3.
    #
    # 🔴 `assistencia 24h` **NAVEGA** — e a prova é a própria tela seguinte, que a
    #    zurich escreve: *"aqui voce vai acionar a assistencia 24h, que atende
    #    reboque, socorro mecanico, chaveiro, pane seca ou troca de pneu"*. Cinco
    #    serviços atrás de UMA tecla: mapeá-la para `guincho` seria decidir pelo
    #    segurado (CLAUDE.md §9.5).
    {"seguradora": "zurich", "sessoes": 5,
     "tela": r"escolha um dos servi[çc]os para continuar",
     "rotulos": {"assistencia a vidros": "vidro",
                 "carro reserva": "carro_reserva",
                 "assistencia 24h": None, "sinistro": None,
                 "consultar pagamentos": None, "consultar apolice": None,
                 "atendimento a oficinas": None, "outros servicos": None}},
    # 📊 ② O menu de escolha, 2 sessões — a entrada que já existia.
    {"seguradora": "zurich", "sessoes": 2,
     "tela": r"me conte o que aconteceu",
     # ⚠️ 📊 A tarefa dizia "menu de panes com 13 opções". **Não existe** NESTA
     #    tela. O maior menu numerado aqui tem 8 opções. As 13 opções existem —
     #    na tela ③ abaixo, que é a que a tecla `4` abre.
     "teclas": {"1": "combustivel", "2": "pneu", "3": "chaveiro", "4": None,
                "5": "acidente", "6": "guincho", "7": None, "8": None}},
    # 📊 ③ 🔴 A TELA QUE A TECLA `4` ABRE — *"problemas no funcionamento (panes)"*
    #    não distingue bateria de reboque, e por isso ela vale `None` acima.
    #    Quem distingue é esta, e ela existe: 2 sessões, a frase real
    #    *"o que houve?"* com 13 opções.
    #
    # 🔴 A REGRA DE PREENCHIMENTO, escrita ao lado dela (CLAUDE.md §9.5): uma
    #    tecla só recebe rótulo quando **(a)** o texto da própria seguradora NOMEIA
    #    o serviço, ou **(b)** o acervo mostra o DESFECHO daquela tecla. Todas as
    #    outras ficam `None` — e `None` aqui significa *"a zurich não disse o
    #    bastante"*, nunca *"não tem serviço"*.
    #
    # ```
    #   1  problema de bateria                 -> bateria   (a) o rótulo NOMEIA
    #   4  problemas no cambio ou embreagem    -> guincho   (b) 📊 sessão 9f7dbd91:
    #                                                       a zurich pergunta "para
    #                                                       onde devemos levar seu
    #                                                       veiculo" e fecha com
    #                                                       "numero da solicitacao:
    #                                                       71020124" — é reboque
    #   2,3,5..13  (partida, alarme, freio, motor, vazamentos, suspensao,
    #              superaquecimento, ignicao, radiador, bomba, combustivel errado)
    #              -> None: o rótulo descreve o SINTOMA, e o desfecho (reboque ou
    #                 socorro no local) NÃO está no acervo. Inferir seria inventar.
    # ```
    {"seguradora": "zurich", "sessoes": 2,
     "tela": r"o que houve\?.{0,60}problema de bateria",
     "teclas": {"1": "bateria", "4": "guincho"}},
    # ── mapfre ── 🔴 SPEC-119 · a ÚNICA seguradora sem NENHUMA entrada, até hoje
    #
    # ⚠️ 📊 **SÃO DOIS BOTS DIFERENTES**, e a régua já registrava isso: a tecla se
    #    chama `assistencia 24h` num e `assistencia` no outro. Medido em 27/09/2026
    #    sobre as 39 sessões `insurer_key='mapfre'` (21 em `ramo=auto`):
    #
    # ```
    #   bot do SEGURADO ("eu sou a Maite")   3 sessões
    #     "otimo! voce esta no atendimento de seguros para veiculos. 🚗🏍
    #      sobre qual assunto voce quer falar?
    #      assistencia 24h / solicitacao e acompanhamento de guincho, socorro ou taxi
    #      sinistro / carro reserva / pequenos reparos / apolice e carteirinha / …"
    #     respostas medidas: `sinistro` 3 · `carro reserva` 1
    #
    #   bot da CORRETORA ("digite o seu codigo de corretor")   14 sessões
    #     "agora e so escolher sobre qual assunto voce quer falar:
    #      pagamento / apolice e proposta / sinistro
    #      assistencia / solicitacao ou acompanhamento de guincho, vidros e
    #      pequenos reparos / acesso portal e cotacao / vistoria previa /
    #      help desk / demais assuntos / voltar"
    #     respostas medidas: `pagamento` 22 · `demais assuntos` 1 · `sinistro` 1
    # ```
    #
    # 🔴 **E O ACHADO QUE A F2 E A F5 PRECISAM SABER:** em 18 telas de menu de
    #    assunto, `assistencia` foi escolhida **ZERO vezes**. O acervo da Mapfre
    #    **não tem uma única sessão de assistência** — só pagamento, sinistro e um
    #    carro reserva. Nenhuma entrada de menu pode produzir `guincho` na Mapfre,
    #    porque ninguém pediu guincho à Mapfre neste acervo. Isso é falta de
    #    CONVERSA, não cegueira de classificador (SPEC-119 §3, gate G2).
    #
    # ⚠️ `assistencia`/`assistencia 24h` valem `None`: elas NAVEGAM para o submenu
    #    de serviço, que não existe no acervo. Cadastrá-las como `guincho` seria
    #    exatamente o defeito do cardápio que o topo deste arquivo conserta.
    # ⚠️ 🔴 A ÂNCORA **NÃO** É `assistencia 24h`, e a diferença é um teste que
    #    nunca ficaria verde. 📊 O mascarador do corpus (`higiene_do_corpus`)
    #    troca o número: no arquivo versionado a linha lê
    #    `assistencia {valor}`. O produto classifica sobre o texto CRU (onde
    #    `24h` existe), mas qualquer guarda que leia o CORPUS veria `{valor}`.
    #    A âncora é a frase que sobrevive à máscara — e ela também é o que
    #    distingue este bot do outro: aqui é *"solicitacao **E** acompanhamento
    #    de guincho, socorro ou taxi"*; no bot da corretora é *"solicitacao
    #    **OU** acompanhamento de guincho, vidros e pequenos reparos"*.
    {"seguradora": "mapfre", "sessoes": 3,
     "tela": (r"sobre qual assunto voc[êe] quer falar\?"
              r".{0,60}solicita[çc][ãa]o e acompanhamento de guincho"),
     "rotulos": {"carro reserva": "carro_reserva",
                 "pequenos reparos": "vidro",
                 "assistencia 24h": None, "sinistro": None,
                 "apolice e carteirinha": None, "endosso": None,
                 "pagamentos": None}},
    {"seguradora": "mapfre", "sessoes": 14,
     "tela": r"escolher sobre qual assunto voc[êe] quer falar",
     "rotulos": {"assistencia": None, "pagamento": None,
                 "apolice e proposta": None, "sinistro": None,
                 "acesso portal e cotacao": None, "vistoria previa": None,
                 "help desk": None, "demais assuntos": None, "voltar": None}},
]

# 🔴 O DESEMPATE do bradesco — a tela POSTERIOR à tecla que não distingue.
#    📊 4 sessões, texto único, e resolve 2 das 8 rotas indistinguíveis do produto:
DESEMPATE: List[Dict[str, Any]] = [
    {"seguradora": "bradesco", "sessoes": 4,
     "depois_de": r"qual o problema com o seu carro",
     "tela": r"me conta o que aconteceu",
     # 🔴 CORRIGIDO em 27/09/2026 (SPEC-119 F1) — a tabela afirmava `bateria` por
     #    INFERÊNCIA ("estacionado e não liga" ⇒ bateria) e a bradesco diz outra
     #    coisa. CLAUDE.md §9.3: verdade vencida migra, não fica.
     #
     # 📊 Sessões `2c05415b` e `57149865`: depois da tecla `1`, a URA responde
     #    *"certo! esse problema da pra resolver com a assistencia de um
     #    **tecnico**. posso confirmar esse servico?"* — nunca `bateria`.
     # 📊 Sessões `0d5284f3`, `a10d095d` e `bc2cfead`: depois da tecla `2`, a URA
     #    responde *"certo, entao vamos enviar um **reboque**"*. `guincho` confere.
     #
     # ⚠️ CONSEQUÊNCIA DECLARADA, e ela é insumo da F5: `bradesco/auto` **não tem
     #    rota `tecnico`** (subserviços: bateria · chaveiro · guincho · pneu), e
     #    com esta correção `bradesco/auto/bateria` fica com ZERO sessões. Não é
     #    perda de amostra — é a medição de que **ninguém pediu recarga de bateria
     #    à bradesco neste acervo**; quem pede pane recebe TÉCNICO.
     "teclas": {"1": "tecnico",   # "o veículo estava estacionado e não liga"
                "2": "guincho"},  # "o veículo estava andando e parou de funcionar"
     "resolve": ("bradesco", "guincho", "tecnico")},
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


def _desempate_posterior(seguradora: str,
                         pares: List[Tuple[str, str]],
                         i_menu: int,
                         texto_menu: str,
                         playbook: Optional[Dict[str, Any]]) -> Optional[str]:
    """A tela POSTERIOR que separa o que a tecla do cardápio não distinguiu.

    🔴 Lê `DESEMPATE`, que até 23/08/2026 estava declarado e não era lido por
    ninguém. Ver o comentário no ponto de chamada.

    ⚠️ A busca é para FRENTE a partir do menu que empatou (`i_menu`): a tela de
    desempate vem DEPOIS, e olhar para trás pegaria a conversa anterior.
    """
    for des in DESEMPATE:
        if des.get("seguradora") != seguradora:
            continue
        if not re.search(des.get("depois_de") or r"$^", texto_menu,
                         re.IGNORECASE | re.DOTALL):
            continue
        rx_des = re.compile(des.get("tela") or r"$^", re.IGNORECASE | re.DOTALL)
        for k in range(i_menu + 1, len(pares)):
            if pares[k][0] != "in" or not rx_des.search(pares[k][1]):
                continue
            for direcao_r, resposta in pares[k + 1:]:
                if direcao_r != "out":
                    continue
                alvo = (des.get("teclas") or {}).get(_norm_rotulo(resposta))
                return _canonizar(alvo, playbook) if alvo else None
            return None
    return None


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
    #
    # 🔴 A ORDEM É **PADRÃO POR FORA, EVENTO POR DENTRO** — e ela vale uma
    #    classificação errada. Medido em 27/09/2026, SPEC-119 F1.
    #
    #    `PADRAO_OURO` é uma tupla ORDENADA POR PRECISÃO: o resumo
    #    (`^servico:`) é o que a seguradora escreve depois de decidir; as frases
    #    de envio (`enviaremos o servico de …`) são o que ela diz **no meio** do
    #    caminho, e a URA se corrige.
    #
    # 📊 A prova, sessão `886066e5` da hdi — uma TROCA DE PNEUS inteira:
    # ```
    #   "pneu furado"                                          (a corretora)
    #   "quantos pneus foram furados/danificados?"              (a URA)
    #   "neste caso enviaremos o servico de GUINCHO …"     ← a URA se engana
    #   "neste caso enviaremos o servico de TROCA DE PNEUS …"  ← e se corrige
    #   "resumo da solicitacao / … / servico: troca de pneus"  ← e assina
    # ```
    #    Com evento por fora, o primeiro `in` que casasse QUALQUER padrão
    #    vencia: a sessão saía `guincho`. Com padrão por fora, o resumo é
    #    procurado no acervo INTEIRO antes de qualquer frase de envio, e a
    #    sessão sai `pneu` — que é o que a hdi assinou.
    #
    # ⚠️ Não é troca de estilo: é a diferença entre `pneu` e `guincho` numa
    #    sessão que percorreu o corredor até o fim.
    for rx in PADRAO_OURO:
        for direcao, texto in pares:
            if direcao != "in":
                continue
            m = rx.search(texto)
            if m:
                rotulo = _norm_rotulo(m.group(1))
                # 🔴 UM NÚMERO NÃO É NOME DE SERVIÇO — SPEC-119 CONSERTO A.
                #
                # 📊 `DEMANDA-POR-ROTA.json` publicava a chave
                #    `porto/auto/?4145720 - 26`, num relatório versionado. A tela
                #    real é `"Serviço: 4145720 - 26"` — o número da ORDEM DE
                #    SERVIÇO da seguradora, capturado pelo mesmo grupo que captura
                #    `"Serviço: Guincho"`.
                #
                # ⚠️ Não se descarta a sessão: `continue` deixa os níveis seguintes
                #    (cardapio e texto do `out`) tentarem. Descartar aqui seria
                #    pular em silêncio, que a SPEC-083 §7 proíbe.
                if len(re.findall(r"[a-zà-ÿ]", rotulo)) < 3:
                    continue
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
                # ══════════════════════════════════════════════════════════
                # 🔴 NÍVEL 1b-bis · A TELA POSTERIOR, QUANDO A TECLA NÃO
                #    DISTINGUE — e `DESEMPATE` existia sem ninguém ler.
                # ══════════════════════════════════════════════════════════
                #
                # 📊 Medido em 23/08/2026: `grep -n DESEMPATE` devolvia só a
                #    própria declaração. A constante foi escrita, documentada
                #    ("a tela que separa é a seguinte, e ela existe: ver
                #    DESEMPATE abaixo") e **nunca consultada**.
                #
                # 🔴 O efeito: na bradesco, a tecla `1` do menu "qual o
                #    problema com o seu carro" é PANE, e PANE não distingue
                #    bateria de guincho — por isso ela mapeia para `None`, de
                #    propósito. Sem ler o desempate, a sessão inteira ficava
                #    sem serviço, e **as QUATRO rotas de `bradesco/auto`
                #    saíam SEM_CORPUS** com o acervo cheio: 📊 as sessões
                #    a10d095d e 0d5284f3 percorrem um guincho inteiro, até
                #    "Logo mais, a sua assistência já será acionada".
                #
                # ⚠️ E é exatamente a diferença que a ONDA G tem de separar:
                #    `SEM_CORPUS` por **coleta legítima** (ninguém pediu) x
                #    `SEM_CORPUS` por **BUG de reconhecimento** (pediram, e o
                #    produto não soube ler). Fundir as duas manda para coleta
                #    uma rota cujo acervo está cheio.
                #
                # ⚠️ Só dispara quando a tecla EXISTE no mapa e vale `None` —
                #    isto é, quando a própria tabela declarou "esta tecla não
                #    decide". Não é uma segunda chance para tecla desconhecida.
                if r in (menu.get("teclas") or {}):
                    _fino = _desempate_posterior(seguradora, pares, i, texto,
                                                 playbook)
                    if _fino:
                        return _fino, "nivel-1b-desempate"
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


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 SPEC-119 F5 · ESTE NOME MENTIA, E A MENTIRA CHEGOU AO FOUNDER
# ═════════════════════════════════════════════════════════════════════════════
#
# Chamava-se `DEMANDA_MEDIDA`. Quem lia entendia "a demanda desta rota". É
# outra coisa: **o total de um SERVIÇO somando TODAS as seguradoras, no retrato
# de 21/08/2026**. `("guincho", 72, 197)` são 72 escolhas de guincho em sete
# seguradoras — e a régua o imprimia igual nas dez linhas de guincho.
#
# 📊 O Founder leu `mapfre/auto/guincho · 72` e perguntou, com razão: *"como
#    pode ter 72 pedidos e não ter o corredor?"* Nunca houve 72 pedidos na
#    Mapfre. Medido em 28/09/2026 em `observed_events`: a Mapfre tem **ZERO**
#    sessões de guincho, e a maior rota de guincho é `allianz/auto` com 29.
#
# 🔴 CLAUDE.md §12.1: *"se o nome de um campo mente sobre o que ele guarda,
#    conserte o CAMPO — o texto errado é o sintoma, o nome errado é a causa, e
#    ela reinfecta todo leitor seguinte."* Por isso o nome agora carrega os dois
#    fatos que faltavam: **é GLOBAL POR SERVIÇO**, e **é de 21/08/2026**.
#
# ⛔ NÃO use isto como demanda de uma rota. A demanda por rota vive em
#    `scripts/demanda_por_rota.py`, medida em `observed_events` e datada.
#
# ⚠️ E as chaves são SINGULARES (`eletrodomestico`, `vidro`) enquanto os
#    playbooks e o classificador escrevem no PLURAL (`eletrodomesticos`,
#    `vidros`). 📊 `.get("eletrodomesticos")` devolvia nada -> `0`, e rotas COM
#    demanda apareciam como se ninguém pedisse. As chaves ficam como estão
#    porque é assim que a medição de 21/08 foi feita — mudá-las seria inventar
#    um número. O que muda é que ninguém mais busca uma ROTA aqui dentro.
DEMANDA_GLOBAL_POR_SERVICO_21_08_2026: List[Tuple[str, int, int]] = [
    # (servico, ESCOLHIDO, no_cardapio)
    ("guincho", 72, 197), ("bateria", 16, 106), ("encanador", 14, 132),
    ("eletricista", 12, 109), ("pneu", 10, 101), ("eletrodomestico", 9, 102),
    ("socorro_mecanico", 7, 70), ("chaveiro", 5, 210), ("conserto_residencial", 3, 0),
    ("tecnico", 3, 0), ("ar_condicionado", 2, 0), ("limpeza_caixa_dagua", 2, 0),
    ("pet", 2, 0), ("desentupimento", 1, 41), ("taxi", 1, 58), ("vidro", 1, 77),
    ("telhado", 0, 51), ("carro_reserva", 0, 75), ("martelinho", 0, 57),
]
