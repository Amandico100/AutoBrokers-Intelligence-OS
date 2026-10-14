modelo: claude-opus-5-5

# CONFIRMAÇÃO DE DESIGN · SPEC-132-B · COTAÇÃO (venda) e RENOVAÇÃO — depois do conserto `08c7138`

> Juiz NOVO (Opus 5.5) · 14/10/2026 · READ-ONLY no código · branch `spec/132-o-chat-e-a-cotacao`.
> **V** = visto em captura · **📊** = medido no navegador (Chromium do Playwright, headless clássico, um navegador, pela trava
> `pesado.sh`) · **T** = lido no texto servido do HTML.
> Capturas NOVAS: `scratchpad/design132c/` (script `captura.py`, 12 combinações = 3 páginas × 390/1440 × claro/escuro; dobra,
> inteira, partes do claro, e o "Comparar coberturas" ABERTO a 390 px). Páginas: os 3 HTML da corretora-piloto regerados às 11:59–12:00
> (`exemplos-resulta/Resulta-exemplo-{COTACAO,COTACAO-com-apolice,RENOVACAO}.html`). Para o D3 (só aparece com dado da Vega)
> usei o HTML de `design132b/venda-vega-pouco-dado-sem-numero.html` (T).

## VEREDITO

| página | antes | agora | meta |
|---|---|---|---|
| **COTAÇÃO (venda)** | 87 | **92** | ≥ 90 — **atingida** |
| **RENOVAÇÃO** | 88 | **91** | ≥ 90 — **atingida** |

O conserto resolveu o que segurava a venda: a economia está na 1ª tela (no cartão e, no notebook, "Seu seguro atual R$ 6.390 ›
Opção Recomendada R$ 4.784"), o notebook não tem mais meia tela vazia no topo, a história societária e o quadro SUSEP saíram, o
"Comparamos 16" virou "Cotamos em 16 … 11 com a mesma cobertura completa", e a "mais em conta" ficou coerente. Nenhum defeito
visual GRAVE novo. O que impede 95 é pouco e concreto (abaixo).

## Medidas (📊 `design132c/medidas.json`, 12 combinações)
- Fonte visível < 12 px: **0** em todas. Rolagem horizontal: **0** (`scrollWidth` = 390/1440). Erros de console: **0**. Alvos < 40 px: **0**.
- Contraste AA: **0 falhas reais** — o único acusado é o mesmo falso positivo do 1º laudo (`.dock-note` 3,79:1 no claro: fundo
  `color-mix` lido como preto; calculado 5,40:1).
- Barra fixa: venda 101 px no celular (era 92; o subtítulo passou a quebrar em 2 linhas em vez de cortar) / 92 px no notebook;
  renovação 109 / 92.
- Altura: com apólice 4.906 px (390, era 5.074) e **3.346 px (1440, era 4.368: −23%)**; sem apólice 4.535 / 3.247; renovação
  3.491 / 3.401 (era 3.578 / 3.467).

## Os defeitos do 1º laudo — VENDA

| # | status | evidência |
|---|---|---|
| D1 economia na 3ª tela | **RESOLVIDO** | V `res-cotacao-apolice_390_light_dobra.png` (chip verde "R$ 1.606 a menos por ano que o seu seguro atual" sob o preço); V `..._1440_light_dobra.png` (faixa "Seu seguro atual R$ 6.390 › R$ 4.784" na coluna esquerda). O rodapé explica a conta (líquido da apólice × à vista da Recomendada) — honesto e conservador. |
| D2 "Por que fechar" | **PARCIAL** | V `..._1440_light_parte02.png`: história societária e quadro SUSEP saíram; ficou o subtítulo-cadastro "Proteção e tranquilidade através de soluções eficientes" (frase de folder, não um fato) + o parágrafo do papel; no notebook a metade direita da seção fica vazia. Sem dado de marca a corretora ainda não parece "diferenciada" (depende do Configurar — pendência de produto já registrada). |
| D3 "mais em conta" mais cara na parcela | **RESOLVIDO** | T Vega: o número grande passou a ser o à vista (R$ 4.784,27 × R$ 4.168,45) e o cartão diz "Mais barata à vista. Parcelada, a opção 'Recomendada' sai mais em conta (sem juros)." Na Resulta, a ordem das parcelas já coincide (555,83 > 484,27) e a página segue na parcela. |
| D4 textos internos no cartão | **RESOLVIDO** | V `..._1440_light_parte01.png`: Tokio "Vidros · Completo", sem a frase interna; "R$ 200 mil para danos materiais e R$ 200 mil para danos corporais"; franquia R$ 5.171 igual no porquê e na linha. |
| D5 hero do notebook | **RESOLVIDO** | V `..._1440_light_dobra.png`: coluna esquerda com a faixa da economia, 2 checks e o cartão "Quem vai cuidar de você · Caio"; título sem letras coladas. |
| D6 linguiça | **RESOLVIDO no essencial** | T: nº SUSEP 3×→2× (topo + rodapé), "Para guardar em PDF" 0× na venda, "Como funciona" ‖ "Se acontecer" lado a lado no notebook (V `..._parte02.png`), "Se acontecer" num cartão só. Resta: o botão "Quero fechar" do fecho e o da barra ficam juntos na mesma tela (V `..._1440_light_parte03.png`). |
| 7 "Comparamos 16" | RESOLVIDO | V dobra: "Cotamos em 16 seguradoras para você — 11 com a mesma cobertura completa." |
| 8 viúva "à / vista" | RESOLVIDO | V dobra 390: "R$ 4.784,27 / à vista" quebra junto. |
| 9 barra corta a seguradora | PARCIAL | 📊 dock 101 px: não corta mais, mas o subtítulo vira "10x de R$ 555,83, / Bradesco" (2 linhas, botão pesado). |
| 10 "Avise a sua corretora" | RESOLVIDO | "Avise a Resulta Seguros pelo WhatsApp assim que puder." |
| 11 placa do logo no escuro | RESOLVIDO | V `res-cotacao_390_dark_dobra.png`: placa justa no logo. |
| 13 validade no meio do parágrafo | RESOLVIDO | V `..._1440_light_parte03.png`: "Preços válidos até 11/11/2026." em linha própria. |

## RENOVAÇÃO

| # | status | evidência |
|---|---|---|
| R1 um eixo no notebook | **RESOLVIDO** | V `res-renovacao_1440_light_dobra.png`/`parte01/02`: logo, título, "hoje × renovação", cartões e "Quem cuida" em x = 208. |
| R2 "Por que recomendamos" 3× | RESOLVIDO | V `parte01`: 2º e 3º dizem "Por que considerar". |
| R3 nota igual nos três | RESOLVIDO | sem "nossa nota" nos cartões. |
| R4 "Tipo na seguradora" | RESOLVIDO | "Sua parte no conserto se o carro bater." |
| R5 SUSEP | RESOLVIDO | topo "Corretora de seguros · SUSEP nº 202037116"; o número gigante solto saiu do "Quem cuida". |
| R6 "Mais completa" sem o que tem a mais | **ABERTO** | V `parte01`: o porquê promete "cobertura de pequenos reparos", mas a lista é idêntica à da "Sua renovação" e o rodapé do cartão diz "Mais 2 coberturas, iguais nas três" — o cliente paga R$ 382,74 a mais sem ver por quê, e a página se contradiz. |

## Defeitos novos ou que sobraram (nenhum grave)
1. **Renovação, notebook: metade direita vazia no topo** — V `res-renovacao_1440_light_dobra.png`: título e "hoje × renovação"
   ocupam 208–928 px; 928–1232 fica em branco até os cartões. É o mesmo defeito que a venda tinha (D5).
2. **Venda, celular: a economia aparece 2×** (chip no hero + bloco verde grande depois do "Comparar") — V `mont_apolice390_0.png`.
   Aceitável (o bloco explica a conta), mas o bloco tem "R$ 6.390 por / ano" quebrado no meio.
3. **"Comparar coberturas" aberto a 390 px** (medido agora pela 1ª vez): legível e com a coluna da recomendada marcada; o cabeçalho
   fixo das colunas cobre o rótulo "Parcelas" (V `res-cotacao-apolice_390_light_comparar2.png`) e a coluna "Mais em conta" do
   cabeçalho fica tingida de azul como se estivesse selecionada.
4. **Renovação: resto de texto de ferramenta** — T: "Para guardar em PDF: … Ctrl+P" e "Nossa nota, de 0 a 100, pesa…" no rodapé,
   mas a nota já não aparece nos cartões; "vence em 13/11/2026" 2× seguidas (título e cartão "Hoje").
5. Logo da corretora no topo: o "CORRETORA DE SEGUROS" interno do arquivo continua ilegível (limite do arquivo, não do CSS).

## O que ainda impede 95 — com o conserto
**Venda (92 → 95):**
- (a) "Por que fechar": usar `mission`/`tagline` só se não for frase genérica (sem "através de", "soluções", "eficientes") — senão
  o bloco abre direto em "Quem representa você é a corretora."; no ≥ 1024 px, 2 colunas: papel à esquerda, à direita os fatos que
  a página já tem e que vendem a corretora (Caio com nome e WhatsApp · "no sinistro, a Resulta abre o aviso e acompanha" ·
  "16 seguradoras cotadas para você"). E a pendência do Configurar (ano de fundação, diferenciais, nota do Google) segue com o Founder.
- (b) Barra no celular (< 400 px): subtítulo só "10x de R$ 555,83" (sem a seguradora) — volta a 1 linha, dock ≈ 92 px.
- (c) Esconder a barra fixa quando o botão do "Pronto para fechar?" estiver visível (IntersectionObserver) — some o botão duplicado.
- (d) `nbsp` em "por ano" no bloco da economia; no "Comparar" aberto, `scroll-margin`/`top` do rótulo da linha abaixo do cabeçalho fixo.

**Renovação (91 → 95):**
- (e) R6: a cobertura que só a "Mais completa" tem vira linha com o selo "a mais" no cartão e sai do "iguais nas três"
  (o rótulo "iguais nas três" só quando o conjunto for de fato igual nos três).
- (f) Topo do notebook: o cartão "Sua renovação" (preço + "Quero renovar") ou o "Quem cuida · Bruna" na coluna direita, como na venda.
- (g) Tirar do rodapé o "Para guardar em PDF" e a explicação da nota que não aparece; no cartão "Hoje", trocar "vence em" (repetido)
  por nada.

## Critério do Founder
- Venda para quem não é cliente: **sim** — a dobra diz quem, o quê, quanto, quanto economiza e o que fazer.
- Gatilhos honestos: **sim** — economia com a conta explicada, validade real, "Nada é cobrado agora", contagem exata das seguradoras;
  sem cronômetro, sem depoimento inventado.
- Objeções respondidas: **sim** — 7 perguntas, "Como funciona depois do sim", "Se acontecer".
- Sem poluição: **quase** — sobram o botão duplicado no fim e o rodapé da renovação.
- A cara da corretora: **boa na forma** (cores, logo, SUSEP, nome do corretor), **fraca no conteúdo** do "Por que fechar" enquanto
  o cadastro não der fatos.

## O que ficou por medir
- Impressão, axe/Lighthouse e página sem JavaScript não rodaram nesta confirmação (os testes `test_navegador_*` cobrem sem-JS).
- "Comparar lado a lado" ABERTO da renovação a 390 px: o clique não achou o texto "Comparar coberturas" (o rótulo lá é
  "Comparar lado a lado"); não capturado.
