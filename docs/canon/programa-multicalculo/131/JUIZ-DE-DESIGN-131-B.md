# JUIZ DE DESIGN · SPEC-131-B · O aplicativo de Renovação

> Juiz fresco (Opus 5.5) · 13/10/2026 · READ-ONLY · branch `spec/131-B-o-aplicativo` @ `af7ea4f` (diff `c052550..af7ea4f`).
> Réguas abertas: DS-001 §5, §8.3–8.10, §14 · laudo `DESIGN-DO-PADRAO-DE-APLICATIVO.md` §2–§6 · intake (PLUGINSS GPT 1, GALERIA PLUGINS GPT, NETFLIX CARD, ASTRON 3, OPENAI AGENTS PRINCIPAL).
> **V** = visto em captura (16 PNG em `scratchpad/design131b/`) · **L** = lido no código (sem captura: o dashboard exige login). Sem captura não há "aprovado visualmente" (protocolo §7).
> 📊 contraste = WCAG 2.1, calculado em python sobre os tokens de `app/globals.css` e do `<style>` da página (13/10).

## VEREDITO

**NÃO ATINGE 90. Nota geral 82/100** (era 50). A página do cliente está perto da meta e é a melhor peça (**V**). A loja e a casca seguem o desenho do laudo quase item a item, mas o "uau" não está provado: nenhuma tela do dashboard foi vista, e as capas são todas geradas. **Três telas ficam abaixo de 80** (Configurar, Renovações, Meu perfil), por contraste no tema claro, alvos de toque menores que 44 px e selos de 11 px. Os consertos 1–5 levam a nota para ≈ 88–90. O 6 só fecha com captura.

| tela | nota | base |
|---|---|---|
| A · página do cliente `/r/` (renovação) | **86** | V (16 capturas) + HTML |
| B1 · loja (galeria) | 81 | L |
| B2 · página do aplicativo (cabeçalho, abas, Início) | 80 | L |
| B3 · aba Configurar (Renovação) | 78 | L |
| B4 · aba Renovações (lista, quadro, detalhe) | 78 | L |
| B5 · Meu perfil (conexões, WhatsApp, ausência) | 76 | L |
| **geral** (A pesa 35 %, porque é o que chega ao cliente) | **82** | |

## A · A página do cliente: o que as capturas mostram

**O que está certo (V):**
- A hierarquia: nome e frase ("a renovação do seu Compass está pronta"), depois **o seu seguro hoje × a renovação** e só então os cartões.
- "O que mudou" honesto: R$ 312 a mais por ano (+7 %), na mesma seguradora.
- Um CTA fixo com o preço e "Nada é cobrado agora."
- "Quem cuida de você": SUSEP, anos de carteira e "Você renova com a gente há 3 anos" — o tom de quem já é cliente.
- O passo a passo de sinistro ("não um 0800") e dúvidas que falam de renovação.
- Escuro e claro coerentes. Nenhum texto abaixo de 12 px.
- Contraste AA em todos os pares medidos: muted 5,40 · p-text 7,84 · escuro 6,45/8,30 · CTA 7,99 · selo laranja 7,18 · branco a 0,8 no cartão 5,78.
- A variante sem número troca o CTA por "responda a mensagem".

**O que derruba pontos (V):**
1. **Tom errado no cartão que se recomenda.** "Por que recomendamos" lista *"R$ 312 a mais que a sua apólice atual (7 %)"* com um ✓ verde (`r_com_dono_celular_light_inteira.png`, cartão 1). Um aumento de preço aparece como motivo e vitória. A fonte é `backend/app/services/multicalculo/comparacao.py:821` desenhado em `proposta_html.py:551` (`ul.why` + `ICO["check"]`).
2. **"Franquia reduzida" quer dizer duas coisas.** Na opção 1, a linha da franquia diz "Franquia reduzida R$ 5.170,54" (é o tipo da seguradora). A opção 2 *se chama* "Franquia reduzida" e custa R$ 2.585. Ainda há o ✓ "Franquia reduzida de R$ 5.171" (`comparacao.py:831`) e "Franquia de R$ 2.585 (R$ 2.585 menor)".
3. **No notebook há três eixos de alinhamento** (`r_com_dono_notebook_light_inteira.png`): o título vai centrado em 1200 px, o "hoje × renovação" fica num bloco de 720 px alinhado à esquerda, e os cartões ocupam 1200 px. O olho salta.
4. **O título mistura dois tamanhos numa linha.** "· vence em 20/10/2026" (0,6 em, azul) fica colado ao "pronta" e quebra feio no celular. E o nome ("Mariana,") vai em cinza `--ink-muted`: o carinho fica apagado.
5. Aspas misturadas: “Sua renovação” no título e "Sua renovação" na lista (`comparacao.py:813`). E "7 %" ao lado de "100%".
6. Polimento: o cartão sem número termina num vão vazio, onde ficaria o "Quero esta". "Preço válido até 13/10" aparece em cada cartão e de novo no rodapé.
   ⚠️ O dock que aparece no meio das capturas "inteira" é **artefato da captura** (`position:fixed`), não defeito.

## B · O dashboard (lido no código)

- **Loja** (`AuxiliaresClient.tsx`, `CardDoAplicativo.tsx`): o desenho do §2 está fiel — destaque, segmentado com contagem, chips com ícone lucide, capa 16:9, tile de 48 px sobreposto, prova real, "Em breve" compacto, grid 1/2/3/4, esqueleto, erro e vazio humanos.
  - O "uau": `cover_url` é nulo nos 16 aplicativos (migration `20261014_01`), então todo card é o mesmo gradiente com matiz trocada. No escuro (o padrão) o gradiente é `45% 38% / .55` sobre `#1c1f24`, com marca d'água a `opacity .12` (`CapaGerada.tsx:213`, `globals.css` bloco `.capa-aplicativo`). Pela conta, a capa é discreta demais para "joia". Precisa de captura.
  - Chips e segmentado em `h-10` (40 px) no celular (`:163`, `:208`).
- **Página** (`CabecalhoDoAplicativo.tsx`, `AbasDoAplicativo.tsx`, `AbaInicio.tsx`, `ComoComecar.tsx`):
  - Bom: o cabeçalho (capa, tile de 72 px, nome, selo e botão por estado, em `h-11`), as abas grudadas por `?aba=` e o "N de M prontos".
  - Contra: o Início da Renovação tem seis blocos e dois parágrafos de "O que é" — o pedido era menos texto. Os chips "Funciona com" são links de `h-8` (32 px, `:61`).
- **Configurar** (`renovacao/AbaConfigurar.tsx`, `configurar/pecas.tsx`):
  - Bom: a hierarquia certa (grupo, linha, ⓘ em Popover), Avançado fechado e a barra de salvar só com alteração.
  - Contra:
    - "O que fazer" oferece dois cartões, mas só um é escolhível (`:216`). Escolha falsa assusta.
    - "Com qual conta" empilha segmentado, frase e até três linhas de estado (`:245-283`). É denso.
    - O "Salvar" usa `bg-primary text-primary-foreground` (`pecas.tsx:151`) — 📊 **4,38:1 no claro**, reprova.
    - O ⓘ tem `h-9` (`pecas.tsx:54`).
- **Renovações** (`AbaRenovacoes.tsx`, `PecasDaRenovacao.tsx`, `DetalheDaRenovacao.tsx`, `QuadroOuLista.tsx`):
  - Bom: os atalhos com `aria-pressed`, os filtros na URL, a folha de filtros no celular, o cartão de celular com um "Enviar" `h-11`, o detalhe em tela cheia com a barra acima da área segura, o hoje × renovação no detalhe e os vazios humanos.
  - Contra:
    - Os selos saem em **`font-mono text-[11px]`**, porque `StatusPill` é usado sem `className` (`PecasDaRenovacao.tsx:15`, `:213`; `DetalheDaRenovacao.tsx:181-182`).
    - Alvos pequenos: Minhas/Todas `h-9` (`AbaRenovacoes.tsx:263`), Quadro/Lista `py-1.5 text-xs` ≈ 30 px (`QuadroOuLista.tsx:113`), "Limpar filtros" `h-9` (`:316`).
    - Os botões Enviar e "Ver N renovações" usam `bg-primary` (`PecasDaRenovacao.tsx:250`, `DetalheDaRenovacao.tsx:111`, `AbaRenovacoes.tsx:407`) — 4,38:1 no claro.
- **Meu perfil** (`configuracoes/page.tsx`, `perfil/*`):
  - Bom: estrutura limpa em cartões, o WhatsApp de trabalho com confirmação explícita e a ausência com "quem cobre".
  - Contra:
    - `confirm()` nativo do navegador (`MinhaAusencia.tsx:54`, `MeuWhatsAppDeTrabalho.tsx` no "Tirar", `AggersDaEquipe.tsx`), destoando do AlertDialog da casca.
    - "Salvar"/"Marcar" em `bg-primary` (`MeuWhatsAppDeTrabalho.tsx:106`, `MinhaAusencia.tsx:123`).
    - Textos explicativos longos.
- 📊 **Tema claro** (o escuro é o padrão e passa):
  - `text-primary` como texto: 4,10–4,38. Há 21 usos em `components/aplicativos` + `components/perfil`.
  - Branco sobre `primary`: 4,38.
  - Selo `warning`: 3,97. Selo `success`: 4,45.
  - No escuro: muted 5,11 · primary-fg/primary 7,40 · warning 7,55.
  - A casca resolveu os botões com `BOTAO_PRIMARIO` (`CardDoAplicativo.tsx:52`); as fatias G2/G3/perfil não o usaram.

## O checklist (laudo §6) — 25 itens

| # | item | veredito | base |
|---|---|---|---|
| 1 | nenhum emoji em auxiliares/aplicativos/lib | **OK** — varredura Unicode fora de comentário = 0 | L |
| 2 | todo card com o ícone do §2.4 | **OK** — `APLICATIVO_VISUAL` 19 slugs + `LayoutGrid` | L |
| 3 | sem `cover_url` → gerada; URL quebrada → gerada | **OK** — `CapaGerada` `onError` | L |
| 4 | em breve compacto, demais com capa | **OK** — `LinhaEmBreve` | L |
| 5 | grid 1/2/3/4 | **OK** — `AuxiliaresClient.tsx:279` | L |
| 6 | sem estrela; número com SELECT | **OK** — `provaDoCard`, `routine_runs` `count: exact` | L |
| 7 | Tab com foco visível | **OK parcial** — cards, chips e abas sim; `BarraSalvar` e os botões do perfil sem `focus-visible` próprio | L |
| 8 | busca vazia → "Limpar busca" | **OK** — `:243-249` | L |
| 9 | ícone, nome, frase, selo e botão sem rolar | **OK** pela conta (≈ 600 px de 844) | L |
| 10 | nenhum slug cru nem Firecrawl | **OK** — `NOME_HUMANO_DA_CONEXAO` | L |
| 11 | `?aba=` direto; inválida → Início; voltar troca | **OK** — `abaValida`, `router.push` | L |
| 12 | passo com estado e link; "N de M" | **OK** — `ComoComecar.tsx` | L |
| 13 | Atividade = `routine_runs` | **OK** — `atividadeRecente` | L |
| 14 | `faint` só decorativo; `text-[10/11px]` → 0 | **FALHA** — `StatusPill` 11 px mono nas renovações (acima) | L |
| 15 | `emerald-/amber-` → 0 | **OK** | L |
| 16 | axe sem erro de contraste | **FALHA** no claro (📊 acima); página do cliente passa | L + V |
| 17 | Configurar: grupos, Avançado fechado, ⓘ com toque | **OK** — Popover; alvo de 36 px | L |
| 18 | alterar mostra a barra; Descartar volta | **OK** | L |
| 19 | Lista ↔ Quadro mantém filtros; a escolha volta | **OK** — URL + `useLeituraSalva` | L |
| 20 | arrastar não muda nada | **OK** — sem DnD | L |
| 21 | "Precisa de você" filtra, `aria-pressed`, nº = coluna | **OK parcial** — nº = coluna não conferido | L |
| 22 | detalhe em tela cheia; barra acima da área segura | **OK** — `h-[100dvh]`, `env(safe-area-inset-bottom)` | L |
| 23 | Enviar → `wa.me`; Copiar = a mesma mensagem | **OK** — `useAcoesDaRenovacao.ts:65`, `:111-131` | L |
| 24 | a Fila igual após a extração | **NÃO AVALIADO** — sem captura da Fila | — |
| 25 | rotas montam + `next start` + GET 200 | **NÃO AVALIADO** — `build.txt` termina em `BUILD_EXIT=124` (timeout de 115 min); o dev só deu 307/401 sem sessão | — |

**Resultado: 19 OK · 2 OK parcial (7, 21) · 2 FALHA (14, 16) · 2 NÃO AVALIADO (24, 25) = 25.** Todos os 25 foram "lidos". Só o 16 tem uma parte "vista" (a página do cliente).

## Os 10 consertos que mais sobem a nota

**Mudam o que o cliente ou o corretor vê. São BLOCKER de design, porque sem eles três telas ficam abaixo de 80:**

1. **(cliente) Tirar o aumento do "Por que recomendamos".**
   - Em `comparacao.py:815-823`, no contexto de renovação, não acrescentar "a mais que a sua apólice atual" aos motivos. Ele já está em "O que mudou".
   - Em `proposta_html.py:551`, o ✓ fica só para benefício.
   - Se a diferença ficar na lista, ela entra como `diffs` (ponto neutro), nunca como ✓.
   - Ganho: +3 em A.
2. **(cliente) Uma palavra para cada coisa na franquia.**
   - O rótulo `.fq .lbl` passa a ser "Franquia", e o tipo vai para o `hint`.
   - `comparacao.py:831`: "Franquia reduzida de R$ X" vira "Franquia de R$ X".
   - A diferença vira "Franquia R$ 2.585 menor que na Sua renovação".
   - Aspas tipográficas em `comparacao.py:813` e "7%" sem espaço em `:822`.
   - Ganho: +2 em A.
3. **(corretor) Um botão primário só.**
   - Trocar `bg-primary text-primary-foreground` por `BOTAO_PRIMARIO` em `configurar/pecas.tsx:151`, `PecasDaRenovacao.tsx:250`, `DetalheDaRenovacao.tsx:111`, `AbaRenovacoes.tsx:407`, `MeuWhatsAppDeTrabalho.tsx:106` e `MinhaAusencia.tsx:123`.
   - Trocar os links `text-primary` por `text-foreground dark:text-primary underline-offset-4`, como já faz `ComoComecar.tsx:213`.
   - Ganho: +3 em B3/B4/B5.
4. **(corretor) Selos legíveis.**
   - Passar `className="font-sans text-xs"` nos `StatusPill` de `PecasDaRenovacao.tsx:15`, `:213` e `DetalheDaRenovacao.tsx:181`, ou criar um `SeloDoAplicativo`-like comum.
   - No claro, texto do selo `warning`/`success` em `text-foreground-2`, com o ponto colorido. Isto conserta 3,97/4,45 sem tocar em token global (D-131-43).
   - Ganho: +2 em B4.
5. **(corretor) 44 px no celular.**
   - `AbaRenovacoes.tsx:263` e `:316` → `h-11 sm:h-9`.
   - `QuadroOuLista.tsx:113` → `min-h-11 text-sm sm:min-h-9 sm:text-xs`.
   - `CabecalhoDoAplicativo.tsx:61` (links) → `h-11 sm:h-8`.
   - `pecas.tsx:54` → `h-11 w-11 -m-3`.
   - `AuxiliaresClient.tsx:163`, `:208` → `h-11 sm:h-10`.
   - Ganho: +2 em B1/B3/B4.

**Polimento (sobe, mas não derruba):**

6. **O "uau" da loja.**
   - Capas do Founder (`cover_url`, 1600×900 WebP ≤ 150 KB) para Renovação (o destaque), Cotação e Quem Cobra Menos.
   - Enquanto não chegam, avivar a capa gerada no escuro: `45% 38% / .55` → `55% 46% / .75` e `40% 30% / .35` → `48% 38% / .5`, e a marca d'água de `.12` para `.2` (`CapaGerada.tsx:213`).
   - **E capturar a loja** em 390/1366, claro e escuro. Sem isso o item fica "lido".
7. **(cliente, notebook) Um eixo só.**
   - A partir de 1024 px, o título centrado e todas as seções de 720 px **centradas** (inclusive o "hoje × renovação").
   - `.hero h1 .vence` → `display:block; font-size:18px; margin-top:8px` (`proposta_html.py:1276` + CSS).
   - `.hello` em `--ink-strong`.
8. **(Configurar) Sem escolha falsa e sem parede de estado.**
   - "O que fazer" vira uma linha só de leitura: "Calcula e deixa pronto. Quem envia é o comercial", mais "Enviar e negociar · em breve" esmaecido (`AbaConfigurar.tsx:216-218`).
   - Em "Com qual conta", mostrar só as linhas que pedem ação; com tudo certo, uma linha "✓ Tudo conectado · ver" (`:259-282`).
9. **(página do aplicativo) Menos texto no Início.**
   - "O que é" com o 1º parágrafo e "Ler mais".
   - "O que faz" com no máximo 3 itens.
   - Com passo faltando, "Como começar" sobe para logo depois de "O que é" (`AbaInicio.tsx:63-114`).
10. **(perfil) Confirmações da casa.** Trocar o `confirm()` nativo por `AlertDialog` em `MinhaAusencia.tsx:54`, no "Tirar" de `MeuWhatsAppDeTrabalho.tsx` e no desconectar de `AggersDaEquipe.tsx`.

Projeção (💭 estimativa do juiz, não medida): 1–5 → ≈ 87 · 1–10 com captura confirmando → ≈ 90–91.

## O que ficou por medir

- **Nenhuma tela do dashboard foi vista**: a loja, a página do aplicativo, o Configurar, Renovações e Meu perfil. Falta um usuário de teste e uma captura em 390×844 e 1366×768, claro e escuro. Sem isso, B1–B5 não passam de "lido".
- **axe/Lighthouse não rodou.** O contraste foi calculado só nos pares de tokens.
- **Item 24** (a Fila igual depois da extração) e **item 25** (`test:rotas-montam` + `next start` + 200 em `/dashboard/auxiliares/renovacao?aba=renovacoes`): sem prova. O build estourou o tempo (`BUILD_EXIT=124`).
- O "nº = coluna" do item 21 e o comportamento de `ToggleGroup`/`Tabs` com teclado ficaram por inspecionar.
