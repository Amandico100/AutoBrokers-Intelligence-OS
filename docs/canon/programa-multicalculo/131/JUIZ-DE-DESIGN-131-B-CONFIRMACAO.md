# JUIZ DE DESIGN DE CONFIRMAÇÃO · SPEC-131-B · O aplicativo de Renovação

> Juiz fresco (Opus 5.5, `claude-opus-5-5`) · 13/10/2026 · READ-ONLY · branch `spec/131-B-o-aplicativo` @ `b452d07` (conserto `66feb3e..b452d07`).
> **V** = visto em captura · **L** = lido no código.
> - **Painel:** 36 PNG em `scratchpad/design131b/painel/`, feitos das 15:51 às 15:58 pelo `next dev`, com dados sintéticos. As edições do K2 na árvore são das 14:00–15:57 e o K1 (16:20) só mexeu no backend, então as capturas **são do código atual**.
> - **Página do cliente:** 16 PNG **novos**, capturados por mim do HTML regenerado às 16:16, em `scratchpad/design131b/cliente2/` (390×844 e 1440×900, claro e escuro).
> 📊 O contraste foi medido em pixel nas capturas (WCAG 2.1, python/PIL, 13/10). A menor fonte e os alvos de toque da página do cliente vieram de `getComputedStyle` no Chromium headless.

## VEREDITO

**AINDA NÃO ATINGE 90. Nota geral 87/100** (era 82). A página do cliente passou da meta (**91**). O painel ficou organizado e calmo, e agora isso está **provado em captura**, mas quatro defeitos que o corretor vê seguram a nota:
1. A lista de renovações no notebook corta o nome do cliente.
2. No celular, o ícone do aplicativo sai cortado pela capa.
3. Os alvos de 44 px do conserto **não existem**: `min-h-11` não é classe no Tailwind 3.3.3.
4. Na página do cliente, a mesma opção mostra duas parcelas diferentes.

Os consertos 1–4 levam a nota a ≈ 90; com os oito, a ≈ 92–93 (💭 estimativa do juiz).

| tela | nota | era | base |
|---|---|---|---|
| A · página do cliente (renovação) | **91** | 86 | V (16 capturas novas) |
| B1 · loja | **85** | 81 | V (4) |
| B2 · página do aplicativo (cabeçalho e Início) | **83** | 80 | V (4) |
| B3 · Configurar | **88** | 78 | V (4) |
| B4 · Renovações (lista, quadro, detalhe) | **83** | 78 | V (12) |
| B5 · Meu perfil (conexões, WhatsApp, ausência) | **86** | 76 | V (12) |
| **geral** (A pesa 35 %; B1–B5 dividem 65 %) | **87** | 82 | |

## A · A página do cliente: o conserto chegou

**Fechado (V):**
- O aumento saiu do "Por que recomendamos". Agora o cartão traz ✓ Franquia: R$ 5.171 · Carro reserva 15 dias · 10x.
- A franquia tem rótulo "Franquia", e o tipo foi para a dica ("Tipo na seguradora: reduzida").
- As aspas são tipográficas e o percentual sai como "+7%".
- O nome "Mariana," vem em tinta forte, e "vence em 20/10/2026" ganhou linha própria.
- No notebook há **um eixo só**: título, "hoje × renovação" e "O que mudou" centrados (`r_com_dono_notebook_*_dobra.png`).
- 📊 Medido: menor fonte de **12 px**, **0** alvos abaixo de 44 px e `scrollWidth` igual à viewport nas 8 combinações.

**Ainda aberto:**
1. **BLOCKER (o cliente nota): duas parcelas para a mesma opção.**
   - No cartão "Sua renovação", o preço diz "ou 10x de **R$ 555,83** com juros". Logo abaixo, o motivo ✓ diz "Em até 10x de **R$ 554,94**" (`cliente2/r_com_dono_celular_light_inteira.png`, cartão 1).
   - A causa: o motivo vem de `parcelas_de` (`comparacao.py:424-431`, "demais parcelas"), mostrado em `comparacao.py:854-856`. O preço vem do `com_juros` da proposta (`proposta_html.py:511`).
2. Polimento: na variante sem número, o cartão ainda termina num vão vazio, onde ficaria o "Quero esta".

## B · O painel, visto em captura

- **Loja:**
  - Bom: destaque, segmentado, chips com ícone, grade 1/4 col vistas, selos na capa; no escuro a capa tem vida.
  - Contra:
    - O rodapé dos cards corta a frase que é a prova: "38 renovações calculadas este m…", "Desligado · a configuração fica gu…", "Falta conectar WhatsApp de aten…" (`loja_1440_*`).
    - O "Em breve" corta a descrição no meio da palavra.
    - No claro, o destaque é um vazio pálido de 400 px (`loja_1440_claro.png`). Falta o "uau".
- **Página do aplicativo:**
  - Bom: no notebook o cabeçalho está correto. O Início ficou mais curto ("Ler mais", 3 itens e "Ver as 4"), e "Como começar" vem logo depois de "O que é".
  - Contra:
    - **No celular, o tile de 72 px fica atrás da capa**: só aparece a metade de baixo (`crops/app-inicio_390_*_0.png`, todas as abas). Em `CabecalhoDoAplicativo.tsx:162` falta o `relative` que o card da loja tem (`CardDoAplicativo.tsx:86`).
    - "Como começar" no celular espreme o texto numa coluna de ≈ 150 px, com 5–6 linhas por passo, porque o link fica ao lado (`ComoComecar.tsx:38`, `:55`).
    - A capa 4:1 se repete em toda aba: Renovações começa a ≈ 515 px no notebook e o primeiro cartão a ≈ 780 px no celular.
- **Configurar:**
  - Bom: é a tela mais calma, e não assusta. O "O que fazer" virou leitura, sem escolha falsa, e "Com qual conta" mostra uma falta só, com link.
  - Contra:
    - O gatilho "Avançado" não tem padding vertical: o título encosta na borda (`AbaConfigurar.tsx:317`).
    - No celular, o segmentado "Do responsável | Da corretora" empilha, e a pílula escolhida ocupa só a largura do texto.
- **Renovações:**
  - Bom:
    - O cartão de celular é ótimo: nome inteiro, selo, preço com ▲/▼ e um "Enviar".
    - O quadro fica limpo nas duas larguras.
    - O detalhe ocupa a tela cheia no celular e é uma gaveta no notebook, com a barra de ações visível.
    - 📊 Os selos estão em 12 px sans, com texto `foreground-2`: **8,30:1** no claro.
  - Contra:
    - **Na lista do notebook, todas as colunas truncam:** "Cliente Exempl…", "Seguradora Fic…", "Pessoa Ex…", "Residenci…" (`app-renovacoes-lista_1440_*.png`). E com nomes sintéticos curtos.
      - São 9 colunas em `PecasDaRenovacao.tsx:276`, dentro de `max-w-5xl` (`app/dashboard/auxiliares/[slug]/page.tsx:94`), com 3 ícones de ação.    - O seletor Quadro/Lista mede ≈ 22 px no celular (`crops/lista390_toggle.png`).
- **Meu perfil:**
  - Bom: a estrutura é limpa; "Mudar"/"Tirar" estão claros, e a ausência é escrita como frase.
  - Contra:
    - 📊 "Conectado" em `text-success` sobre a superfície dá **4,16:1** no claro (`perfil-conexoes_1440_claro.png`; `vault/AggersDaEquipe.tsx:11`).
    - O desconectar ainda usa `confirm()` do navegador (`vault/AggersDaEquipe.tsx:203`). A guarda `a-loja-e-a-casca.test.mjs:341` não varre `components/vault`.
    - "Pausar" é `size="sm"` (≈ 34 px).
    - A faixa de abas (816 px) é mais estreita que o cartão (848 px).

### 📊 O defeito transversal: os alvos de 44 px do K2 são no-op

`node_modules/tailwindcss` é **3.3.3**. Nessa versão, `min-h-*` só aceita `0/full/screen/min/max/fit`; a escala de espaçamento só chegou na 3.4. `tailwind.config.ts` não estende `minHeight`. Portanto `min-h-11`, `sm:min-h-9` e `sm:min-h-10` **não geram CSS**. Os arquivos afetados:
- `QuadroOuLista.tsx:114`
- `AbaRenovacoes.tsx:238` e `:391`
- `AbaConfigurar.tsx:135`
- `configurar/pecas.tsx:116` (o 1/2/3 sai com ≈ 28 px no celular)
- `app/dashboard/configuracoes/page.tsx:155`

A captura confirma: o Quadro/Lista mede ≈ 22 px. Já os `min-h-[44px]` (arbitrários) funcionam (`ComoComecar.tsx:55`, `AbaConfigurar.tsx:317`).

## O checklist (laudo §6) — 25 itens

| # | item | veredito | base |
|---|---|---|---|
| 1 | nenhum emoji | **OK** — nenhum nas 52 capturas | V |
| 2 | todo card com ícone | **OK** | V `loja_*` |
| 3 | sem `cover_url` → gerada | **OK** — capa gerada; URL quebrada só lida | V+L |
| 4 | em breve compacto | **OK** | V |
| 5 | grid 1/2/3/4 | **OK** — 1 col (390) e 4 col (1440) vistos; 2/3 lidos | V+L |
| 6 | sem estrela; número real | **OK** — o número aparece, mas cortado (conserto 7) | V |
| 7 | Tab com foco visível | **OK parcial** — o anel aparece no ✕ do detalhe; sem captura de teclado | V parcial |
| 8 | busca vazia → "Limpar busca" | **OK** | L |
| 9 | ícone, nome, frase, selo e botão sem rolar | **FALHA** — no celular o tile sai cortado pela capa | V `app-inicio_390_*` |
| 10 | nenhum slug cru | **OK** — InfoCap, Agger, "WhatsApp de atendimento" | V |
| 11 | `?aba=` direto | **OK** | V |
| 12 | passo com estado e link; "N de M" | **OK** — "3 de 6 prontos"; no celular fica espremido (conserto 5) | V |
| 13 | Atividade = `routine_runs` | **OK** — vazio humano visto | V+L |
| 14 | `text-[10/11px]` → 0 | **OK parcial** — 0 em `components/aplicativos` e `perfil`; 8 em `app/dashboard/auxiliares/checklist-6h/hoje/page.tsx` (fora da 131-B) | V+L |
| 15 | `emerald-/amber-` → 0 | **OK parcial** — `checklist-6h/hoje/page.tsx:432` (fora da 131-B) | L |
| 16 | contraste AA | **FALHA parcial** — "Conectado" 4,16 no claro; selos 8,30, botões e Configurar 5,04 passam | V (pixel) |
| 17 | Configurar: grupos, Avançado fechado, ⓘ | **OK** — Avançado apertado (conserto 8) | V |
| 18 | alterar mostra a barra; Descartar volta | **NÃO AVALIADO** em captura (sem estado alterado); OK em L | L |
| 19 | Lista ↔ Quadro mantém filtros | **OK** — as duas vistas capturadas; a persistência é lida | V+L |
| 20 | arrastar não muda nada | **OK** — sem DnD | L |
| 21 | "Precisa de você": nº = coluna | **OK** — 1 no atalho, 1 cartão com o selo no quadro | V |
| 22 | detalhe em tela cheia; barra acima da área segura | **OK** | V `detalhe_390_*` |
| 23 | Enviar → `wa.me`; Copiar = a mesma mensagem | **OK** — K1 | L |
| 24 | a Fila igual após a extração | **NÃO AVALIADO** — sem captura | — |
| 25 | `test:rotas-montam` + `next start` + 200 | **NÃO AVALIADO** — as capturas vieram do `next dev` (as rotas montam em dev), mas não de `next start` | — |

**17 OK · 3 OK parcial (7, 14, 15) · 2 FALHA (9, 16) · 3 NÃO AVALIADO (18, 24, 25) = 25.** 19 itens têm base **vista**.

## Os 8 consertos que levam a ≥ 90

**BLOCKER de design (o corretor ou o cliente nota):**

1. **Fazer os 44 px existirem.**
   - Em `tailwind.config.ts`, `theme.extend.minHeight: ({ theme }) => theme('spacing')`. Uma linha, e conserta os 6 arquivos acima.
   - Ou usar `min-h-[44px]` / `sm:min-h-[36px]` no lugar.
   - Prova: Quadro/Lista com ≥ 44 px em `lista_390`. B3/B4 +2.
2. **O nome do cliente inteiro na lista.**
   - `PecasDaRenovacao.tsx:276`: tirar a coluna Ramo (4,5 rem) e levar o ramo para a sublinha do nome ("Auto · ***.***"). Nome em `minmax(11rem,2fr)`. Seguradora em uma linha só (a nova, com a atual no `title`). Estado em `auto`.
   - Na aba Renovações, `page.tsx:94` passa a `max-w-6xl`.
   - Prova: "Cliente Exemplo 1" e "Pessoa Exemplo" sem "…" em `lista_1440`. B4 +4.
3. **O tile por cima da capa.**
   - `CabecalhoDoAplicativo.tsx:162`: acrescentar `relative z-10` ao `TileDoIcone`, como em `CardDoAplicativo.tsx:86`.
   - B2 +3.
4. **Uma parcela só no cartão do cliente.**
   - Em renovação, o motivo "Em até Nx de R$ …" usa o mesmo par do preço (`com_juros` da proposta), ou sai da lista, porque já está sob o preço (`comparacao.py:854-856`).
   - Teste: o mesmo valor nos dois lugares. A +1.

**Polimento:**

5. **"Como começar" no celular.** `ComoComecar.tsx:38` → `flex flex-wrap gap-3 p-4`; o link em `:55` → `basis-full pl-10 sm:basis-auto sm:pl-0`.6. **Capa só no Início.** Nas abas Configurar e Renovações, `CapaGerada` com `aspect-[8/1]` ou nenhuma, e o tile sem sobreposição (`CabecalhoDoAplicativo.tsx:153-162`).7. **Loja sem frase cortada.**
   - A prova curta e sem truncar: "38 este mês" / `line-clamp-2` em `CardDoAplicativo.tsx:96`. O mesmo no `:120` (Em breve).
   - No claro, avivar a capa do destaque (`globals.css:237-239`, alfa .95/.9 → saturação +10).
8. **Perfil e Configurar.**
   - `vault/AggersDaEquipe.tsx:203`: `confirm()` → `Confirmar`, e estender a guarda a `components/vault`.
   - `:11`: `text-success` → `text-foreground dark:text-success` com ponto colorido.
   - "Pausar" em `h-11 sm:h-9`.
   - `AbaConfigurar.tsx:317`: `py-3` no gatilho do Avançado.

📊💭 Projeção do juiz: 1–4 → A 92 · B2 86 · B3 90 · B4 89 · ≈ **90**. 1–8 → ≈ **92–93**.

## O que ficou por medir

- Itens 24 e 25 (a Fila, `next start` + 200). O item 18 (a barra de salvar) não tem captura com estado alterado.
- axe/Lighthouse não rodou; contraste medido em pixel.
- ⚠️ Artefato: a loja diz Renovação "Ligado" e a página do aplicativo "Ligar" (harness `?tela=app`, outro mock). Não pesou; conferir no canário.
