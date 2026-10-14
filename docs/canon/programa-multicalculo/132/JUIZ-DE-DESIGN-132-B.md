modelo: claude-opus-5-5

# JUIZ DE DESIGN · SPEC-132-B · A página de COTAÇÃO (venda) e a de RENOVAÇÃO

> Juiz fresco (Opus 5.5) · 14/10/2026 · READ-ONLY · branch `spec/132-o-chat-e-a-cotacao` @ `e508d70`.
> **V** = visto em captura · **L** = lido no código · **📊** = medido no navegador (Chromium do Playwright, modo headless clássico,
> um navegador por vez pela trava `pesado.sh`).
> Capturas: `scratchpad/design132/` (102 PNG + `medidas.json`; script `captura.py`). Nome =
> `<pagina>_<largura>_<tema>_<dobra|inteira|parteNN>.png`. Páginas: `res-cotacao` (Resulta, sem apólice), `res-cotacao-apolice`,
> `res-renovacao`, `vega-pouco` (outra marca, pouco dado, sem número), `exemplo-venda` (Orion fictícia, dado cheio).
> Abri e olhei 26 capturas (as dobras 390/1440 claro e escuro de todas; as partes 390 da cotação com apólice e da Vega; as partes
> 1440 da cotação com apólice e da renovação; a parte 1440 da Orion com o bloco "Por que fechar" cheio).

⚠️ **Ressalva de versão.** Os HTML da Resulta são de 07:33; o `proposta_cotacao_html.py` mudou depois em UM ponto (`a49cd19`, 08:24,
+4/−2: a frase da economia). 📊 `git diff a49cd19~1 a49cd19 --stat`. Todo o resto da página é o código de hoje. A frase nova da economia
foi julgada no código (L, `proposta_cotacao_html.py:576-577`).

## VEREDITO

| página | nota | meta |
|---|---|---|
| **COTAÇÃO (venda)** | **87** | ≥ 90 — **não atingida** |
| **RENOVAÇÃO** | **88** | (131-B deu 93 com dados sintéticos; com a marca e os dados da Resulta aparecem 4 defeitos novos) |

A venda tem a espinha certa: no celular a dobra é exemplar (nome, carro, "Comparamos N… sem custo e sem compromisso", a recomendada
com a parcela gigante, franquia, validade, o porquê, e a barra fixa "Quero fechar"). A marca entra com bom gosto (Resulta: azul e
laranja; Vega: verde) e 📊 **0 fontes < 12 px** e **0 falhas de contraste AA** nas 20 combinações (página × largura × tema). O que
segura a nota abaixo de 90 é o que o Founder pediu por nome: o **"uau"** (o maior fato de venda, a economia, mora na 3ª tela; o
notebook tem meia tela vazia ao lado do título) e **"a corretora é diferenciada"** (o bloco "Por que fechar" da Resulta é um parágrafo
de história societária + dois quadrinhos que repetem o que a página já disse), mais três textos que um comprador estranharia.

## Nota por item — VENDA

| # | item | nota | base |
|---|---|---|---|
| 1 | Hierarquia acima da dobra — celular | **94** | V `res-cotacao_390_light_dobra.png`, `..._dark_dobra.png` |
| 1b | Hierarquia acima da dobra — notebook | **84** | V `res-cotacao-apolice_1440_light_dobra.png`: coluna esquerda vazia abaixo do título (~250 px), logo 30 px |
| 2 | Força de venda sem mentira | **83** | economia escondida; "Comparamos 16" quando 1 não deu preço e 4 eram outro produto; inversão de parcela (D3) |
| 3 | Objeções respondidas e onde estão | **90** | 7 perguntas certas, respostas honestas, fechadas por padrão (V `..._390_light_parte05.png`); "Nada é cobrado agora" na barra |
| 4 | Marca (logo, cores, SUSEP), contraste AA | **87** | 📊 0 falhas AA; logo pequeno, SUSEP 3×, placa branca larga no escuro (V `vega-pouco_1440_dark_dobra.png`) |
| 5 | Tipografia e ritmo | **88** | 📊 nenhuma fonte < 12 px; título do notebook comprimido demais (`wdth 86` + `-.028em`) |
| 6 | Cartões e "Comparar coberturas" no celular | **88** | V `..._390_light_parte01/02.png`: carrossel com a ponta do 2º cartão (bom); textos internos no cartão (D4) |
| 7 | Barra fixa | **90** | 📊 dock 92 px, 2 alvos ≥ 44 px; no celular a seguradora corta ("Brad…") |
| 8 | Pouco dado (Vega) | **85** | V `vega-pouco_390_light_parte02/06.png`: continua limpa; "Por que fechar" magro; 150 px de vão no fim sem barra |
| 9 | Poluição / linguiça | **84** | história societária; SUSEP 3×, validade 4×, "11 seguradoras" 4×; duas linhas do tempo seguidas; "Para guardar em PDF" |
| 10 | Português, termos, números | **82** | "nome próprio desta seguradora: a corretora confirma o que cobre"; "prêmio líquido… sem o IOF"; viúva "à / vista" |
| | **geral (ponderado: 1–3 pesam 2×)** | **87** | |

## Nota por item — RENOVAÇÃO

| # | item | nota | base |
|---|---|---|---|
| 1 | Dobra celular (hoje × renovação, "O que mudou") | **93** | V `res-renovacao_390_light_dobra.png` — continua o melhor bloco do programa |
| 1b | Notebook: eixo | **82** | V `res-renovacao_1440_light_dobra.png`: logo em x=148, título centrado, "hoje × renovação" em 388–1052, cartões em 148–1292, "Se acontecer" com subtítulo centrado e lista à esquerda (`..._parte02.png`) — três eixos |
| 2 | Relação (carinho, quem cuida) | **90** | "Quem cuida de você" com a Bruna, WhatsApp e site |
| 3 | Os cartões | **84** | "Por que recomendamos" nos TRÊS cartões; "nossa nota 91/100" idêntica nos três; "Tipo na seguradora: reduzida" nas duas franquias diferentes (V `..._1440_light_parte01.png`) |
| 4 | Marca e SUSEP | **84** | sem "Corretora de seguros · SUSEP" no topo (a venda tem); no "Quem cuida", o nº da SUSEP vira um número gigante solto "202037116 / registro na SUSEP" (V `..._1440_light_parte02.png`) |
| 5 | Tipo, contraste, barra | **92** | 📊 0 < 12 px, 0 falhas AA, dock 109 px no celular (2 linhas na nota) |
| | **geral** | **88** | |

**Diferença de qualidade venda × renovação:** a venda é mais rica e mais coerente no notebook (UM eixo de 1080 px — o conserto da
131-B foi aplicado nela, `CSS_DA_VENDA` `@media (min-width:1024px)`), mas a renovação ficou com o layout antigo centrado. A venda põe
a SUSEP no topo como autoridade; a renovação não. A renovação tem o comparativo "hoje × nova" acima da dobra; a venda COM apólice, que
tem o mesmo dado, não o traz para cima (D1). As duas devem convergir: a venda empresta à renovação o eixo e o topo; a renovação
empresta à venda o "hoje × nova" no alto.

## DEFEITOS — em ordem de impacto (os 6 primeiros impedem ≥ 90)

### D1 · A economia (o "uau" honesto) está na 3ª tela — VENDA
- V `res-cotacao-apolice_390_light_parte02.png` (y ≈ 1.700 px de 5.074) e `..._1440_light_parte02.png`. No hero não há uma palavra
  sobre ela. É o único número que diz ao cliente "você ganha dinheiro trocando", e é FATO (apólice lida e conferida).
- Código: `proposta_cotacao_html.py:569-577` (bloco `eco`) e a montagem do hero `:476-498`.
- **Conserto:** com `_economia(...)` não-nulo, pôr uma linha no cartão da oferta, logo abaixo do preço:
  `<p class="of-eco">R$ 1.606 a menos por ano que o seu seguro atual</p>` (cor `--pos` sobre um chip claro, 15–16 px, peso 600) e, no
  notebook, uma faixa "Hoje R$ 6.390/ano → Com a Resulta R$ 4.784/ano" na coluna esquerda sob o `lede`. O bloco `.eco` de baixo
  pode ficar (ele explica a conta) ou sair.
- **Texto (código atual, `:576`):** "Comparado ao prêmio líquido da sua apólice atual (R$ 6.390 por ano, sem o IOF)…" — "prêmio
  líquido" e "IOF" são jargão no bloco que deveria encantar. Proposta: "O seu seguro atual custa R$ 6.390 por ano (valor da apólice,
  sem impostos). Esta é a conta com a opção Recomendada." ⚠️ Para o juiz funcional: conferir se `premio_anual` da oferta é com IOF
  (aí a economia mostrada é MENOR que a real — honesto, mas o texto deveria dizer "com impostos" de um lado e "sem" do outro, ou
  comparar líquido com líquido).

### D2 · "Por que fechar com a Resulta" não mostra uma corretora diferenciada — VENDA (com o dado real)
- V `res-cotacao-apolice_390_light_parte02/03.png`, `..._1440_light_parte02.png`. O texto é a história societária ("Em maio de 2009,
  um grupo de empresários de Florianópolis, comprou participação societária na LUZ CORRETORA DE SEGUROS, sediada até então…") — cita o
  nome de OUTRA corretora em caixa alta, tem vírgula entre sujeito e verbo (vem do cadastro) e não vende nada. Os fatos são 2 de 4
  quadros: "SUSEP / registro nº…" (já está no topo e no rodapé) e "11 seguradoras deram preço nesta cotação" (já está 3× acima).
  No notebook, metade da grade de 4 colunas fica vazia.
- Código: `multicalculo/proposta.py:1467` (`about_md` antes de `mission`), `proposta_cotacao_html.py:182-196` (`_sobre` corta em
  300 caracteres) e `:580-614`.
- **Conserto:** (a) `proposta.py:1467` → `tagline` ou `mission` primeiro, `about_md` só como reserva; (b) `_sobre(…, teto=160)` e só
  a 1ª frase — na Resulta sai "Buscamos soluções transparentes e eficazes para você e seu negócio estarem tranquilos."; (c) o quadro
  "SUSEP" sai da grade quando o topo já mostra a SUSEP (fica no topo e no rodapé); (d) a grade usa `grid-template-columns:
  repeat(auto-fit,minmax(200px,1fr))` para 2 fatos não deixarem meia linha vazia; (e) com menos de 2 fatos de marca, o bloco
  abre pelo `papel` ("Quem representa você é a corretora") como título, não como caixa secundária. (f) 🧑 pendência de produto: o
  Configurar da Cotação deveria pedir à corretora os 4 dados que fazem este bloco brilhar (`founded_year`, diferenciais, Google
  confirmado, nº de seguradoras parceiras) — a Orion com dado cheio prova que o bloco fica bom (V `exemplo-venda_1440_light_parte02.png`:
  "17 anos · SUSEP · 11 seguradoras · ★ 4,9").

### D3 · "Mais em conta" pode custar MAIS na parcela que a Recomendada — número estranho que contradiz o rótulo — VENDA
- V `vega-pouco_1440_dark_dobra.png` e texto da página: Recomendada **10x de R$ 478,43 sem juros** (total R$ 4.784,27); "Mais em
  conta" **10x de R$ 484,27 com juros, total R$ 4.843**. 📊 `texto.py amostras/venda-vega-pouco-dado-sem-numero.html`, linhas 25–44
  e 89–90. Quem paga parcelado vê a "mais em conta" com parcela maior e total MAIOR (R$ 4.843 > R$ 4.784), cobrindo menos.
- Código: `_parcela` (`proposta_cotacao_html.py:93-103`) escolhe a regra por opção (sem juros se houver; senão com juros), e o
  número grande dos cartões é a parcela (`_bloco_do_preco`, `:124-139`).
- **Conserto:** quando a ordem das parcelas (ou do total parcelado) não for a mesma ordem do à vista, (a) o número grande dos
  TRÊS cartões passa a ser o preço por ano à vista e a parcela desce para a linha de baixo; e (b) o cartão "Mais em conta" ganha a
  frase "À vista. Parcelado, a Recomendada sai mais barata (sem juros)." — é FATO e é um ótimo argumento de venda da recomendada.
  Guarda: teste com o modelo da Vega que fique VERMELHO com a regra de hoje.

### D4 · Textos internos e jargão dentro do cartão do cliente — VENDA (e a carteira)
- V `res-cotacao-apolice_1440_light_parte01.png` (Tokio): "Vidros · Completo · **nome próprio desta seguradora: a corretora
  confirma o que cobre**". Para quem está cotando, isto lê como "nem a corretora sabe o que cobre". Código:
  `proposta_apresentacao.py:338` (`FRASE_SEM_ORDEM`).
- **Conserto:** na venda, trocar por nada (sem etiqueta) ou por "plano próprio da Tokio — pergunte o que inclui"; a frase atual fica
  só para o painel do corretor.
- Junto: "Danos a outros carros e pessoas · R$ 200 mil + R$ 200 mil" → "R$ 200 mil para danos ao carro dos outros + R$ 200 mil para
  ferimentos" (o cliente não sabe o que é cada parcela); "Franquia reduzida: R$ 5.171" no porquê × "R$ 5.170,54" na linha logo
  acima (mesmo número, dois arredondamentos no mesmo cartão — usar o mesmo).

### D5 · Notebook: o hero tem meia tela vazia e o título está espremido — VENDA
- V `res-cotacao-apolice_1440_light_dobra.png`: abaixo do `lede` a coluna esquerda fica vazia até a seção seguinte (~250 px); o título
  de 54 px com `font-variation-settings:'wdth' 86` e `letter-spacing:-.028em` cola as letras ("Mariana, a cotação do"); o logo da
  Resulta tem 30 px e a linha "CORRETORA DE SEGUROS" dele vira um risco ilegível.
- Código: `CSS_DA_VENDA` `:272-273`, `:388-390`; `proposta_estilo.py:76` (`.brand img{height:30px}`).
- **Conserto:** (a) na coluna esquerda, sob o `lede`, uma faixa de 3 fatos com ícone de check, 15 px: "16 seguradoras cotadas ·
  Nada é cobrado agora · Corretora registrada na SUSEP" (todos já existem no modelo) + o mini-cartão do corretor ("Quem cuida de
  você: Caio, da Resulta" com o monograma) — é o lugar natural do "quem cuida" no notebook; (b) `wdth 92` e `letter-spacing:-.02em`
  a partir de 1024 px; (c) `.venda .brand img{height:36px}` (40 px ≥ 1024).

### D6 · Linguiça e repetição — VENDA
- 📊 contagem no texto servido (`design132/texto.py` → `texto-cotacao-apolice.txt`): o nº da SUSEP **3×** (topo, quadro "SUSEP",
  rodapé); a data de validade **4×** (hero, FAQ, "Pronto para fechar?", rodapé); "11 seguradoras/11 deram preço" **4×** (hero,
  porquê, subtítulo das opções, quadro); "Nada é cobrado agora" **2×** visível (fecho e nota da barra, que aparecem juntos no fim). "Como funciona
  depois do sim" e "Se acontecer alguma coisa" são duas linhas do tempo numeradas, seguidas, com o mesmo desenho (V
  `..._390_light_parte04/05.png`) — o olho lê como uma só lista de 7 passos. "Para guardar em PDF…" é instrução de ferramenta numa
  página de venda. O rodapé explica "A nossa nota, de 0 a 100" que só aparece escondida dentro do "Comparar coberturas".
- **Conserto:** (a) tirar o quadro "SUSEP" da grade (D2c); (b) no fecho, só "Nada é cobrado agora." (a validade já está na mesma
  tela, na barra/hero); (c) "Se acontecer alguma coisa" vira um cartão compacto de 2 linhas (ícone de escudo + "Bateu, foi roubado
  ou precisou de guincho? Fala com a Resulta pelo WhatsApp: a gente abre o aviso na seguradora e acompanha até o fim.") em vez de
  4 passos; (d) "Para guardar em PDF" vai para dentro do `<footer>` com `font-size:13px` só ≥ 1024 px ou sai da venda; (e) no
  notebook, "Como funciona depois do sim" ‖ "Se acontecer" lado a lado (2 colunas ≥ 1024) — corta ~400 px de rolagem.

## Os que levam a 95+

7. **"Comparamos 16 seguradoras"** (hero, `:470-472`) quando 📊 11 deram preço comparável, 4 deram outro produto e 1 não deu preço
   (a própria página diz isso duas telas abaixo). Honesto e mais forte: "Cotamos em 16 seguradoras para você — 11 com a mesma
   cobertura completa. Sem custo e sem compromisso." (usa `conta["completas"]`).
8. **Viúva "à / vista"** no hero e nos cartões (V `res-cotacao_390_light_dobra.png`): `AP.nbsp` não liga "à vista". Em
   `_bloco_do_preco` (`:130`) usar `"à vista"` e `"R$ 4.784,27"` inteiros.
9. **Barra fixa no celular corta a seguradora** ("10x de R$ 555,83, Brad…"): abaixo de 400 px, `sub_de` sem a seguradora ou
   `font-size:13px` + `text-overflow` só no nome; `proposta_cotacao_html.py:679-681`.
10. **"Se acontecer alguma coisa" — passos sem ponto final e "Avise a sua corretora"** (genérico numa página que tem o nome dela):
    texto padrão em `config.py` `servicos.cotacao.pagina` → "Avise a {corretora} pelo WhatsApp assim que puder."
11. **Placa branca do logo no escuro mais larga que o logo** (V `vega-pouco_1440_dark_dobra.png`, ~150 px de placa para ~70 px de
    logo): `.plate{display:inline-block}` e `img{max-width:180px}` — `proposta_estilo.py:77-79`.
12. **Pouco dado, sem número: 150 px de vão no fim** (`.endpad{height:150px}`, `proposta_estilo.py:343`) existe para a barra; sem
    `.dock`, `body:not(:has(.dock)) .endpad{height:24px}`.
13. **"Pronto para fechar?"**: o "Preços válidos até 11/11/2026." entra no meio do parágrafo em 13 px (`span.valid`), quebrando o
    ritmo (V `..._390_light_parte06.png`) — sai (D6b) ou vira linha própria.

### Renovação — para voltar a ≥ 93
R1. **Um eixo no notebook** — aplicar à renovação o mesmo `@media (min-width:1024px)` da venda (wrap 1080 px, alinhado à
    esquerda; o "hoje × renovação" e os cartões na mesma coluna). `proposta_estilo.py`/`proposta_html.py` (o layout da carteira).
R2. **"Por que recomendamos" só no 1º cartão**; nos outros, "Por que considerar" (`proposta_html.py:549-551`, `V["porque"]` para
    `i > 0`).
R3. **Nota igual nos três = ruído**: se `max(nota) - min(nota) < 3`, esconder o campo "nossa nota" nos cartões
    (`proposta_html.py:585`); o mesmo valor 91 nos três (V `res-renovacao_1440_light_dobra.png`) não ajuda a escolher.
R4. **"Tipo na seguradora: reduzida"** nas duas franquias diferentes (R$ 5.170 e R$ 2.585) confunde (`proposta_html.py:606`): na
    renovação, só "Sua parte no conserto se o carro bater."; o tipo vai para o "Comparar".
R5. **SUSEP**: topo igual ao da venda ("Corretora de seguros · SUSEP nº …") e, no "Quem cuida", "SUSEP nº 202037116" em linha
    pequena (hoje é um número de 20 px solto, sem rótulo antes).
R6. **"Mais completa" que não mostra o que tem a mais**: o cartão diz só "+R$ 382,74" e a lista de coberturas é igual à da "Sua
    renovação" (V `..._1440_light_parte01.png`); a "cobertura de pequenos reparos" citada no porquê tem de aparecer como linha com o
    selo "a mais".

## O que está bom (e deve ficar)
- A dobra do celular da venda: nome + carro + "sem custo e sem compromisso" + recomendada com a parcela de 64 px + franquia +
  validade + porquê + barra fixa — tudo em 844 px, nas duas marcas e nos dois temas.
- Os gatilhos são fatos: N cotadas (com a conta exata embaixo), validade REAL (sem cronômetro), "Nada é cobrado agora", "Quem
  representa você é a corretora", o corretor com nome e WhatsApp. Nada de "Quem Cobra Menos", nível, duelo, depoimento ou contagem
  regressiva (V nas 5 páginas).
- O "Comparar coberturas" com "Mostrar só o que muda" e as etiquetas "melhor / mais simples" coloridas e com ícone (não só cor).
- As perguntas: as 7 que um comprador faz, com resposta curta e honesta, e a validade com a DATA real.
- Pouco dado: nenhum bloco inventado; a página continua limpa e a recomendada continua forte (V `vega-pouco_390_light_dobra.png`).
- Marca: a cor da corretora vira o cartão da oferta e o selo, a 2ª cor vira o selo "Nossa recomendação" — bom gosto nas duas marcas.

## Medidas (📊 `design132/medidas.json`, 20 combinações)
- Fonte visível < 12 px: **0** em todas.
- Rolagem horizontal: **0** (`scrollWidth == 390/1440` em todas).
- Contraste AA: **0 falhas reais**. O script acusou `.dock-note` 3,79:1 no claro, mas é falso positivo (fundo `color-mix` em
  0–1 lido como preto); calculado: `#626a70` sobre `#fbfdff` = **5,40:1**.
- Alvos de toque < 40 px: **0**. Barra fixa: 92 px (venda), 109 px (renovação no celular, nota em 2 linhas).
- Erros/avisos de console: **0**.
- Altura da página: venda 4.907 px (390) / 4.223 (1440); com apólice 5.074 / 4.368; renovação 3.578 / 3.467; Vega 4.585 / 3.928.

## O que ficou por medir
- **"Comparar coberturas" ABERTO no celular, o 2º cartão do carrossel e a página SEM JavaScript** — o script `design132/extra.py`
  esperou 30 min pela trava `pesado.sh` (a bateria `bat132` p3 a segurava) e foi encerrado sem rodar. O item 6 foi julgado só com o
  comparar fechado e os cartões do carrossel (V). Os testes `test_spec132b_a_pagina_de_venda.py::test_navegador_*` cobrem sem-JS e
  as medidas, mas não a legibilidade da tabela aberta a 390 px.
- Impressão e axe/Lighthouse não rodaram; contraste foi medido por script próprio (texto sobre o fundo efetivo).

💭 Projeção: D1–D6 → venda ≈ 92–93; + 7–13 → ≈ 95. R1–R6 → renovação ≈ 94.
