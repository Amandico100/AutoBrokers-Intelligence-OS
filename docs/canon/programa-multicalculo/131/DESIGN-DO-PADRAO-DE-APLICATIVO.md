# DESIGN DO PADRÃO DE APLICATIVO (SPEC-131-B)

> Investigador de design · 12/10/2026 · READ-ONLY · sem PII. Lido: protocolo §7, DS-001, I2, SPEC-131 §4.6–4.10/§8, 14 imagens das 4 pastas.
> FATO = arquivo:linha/comando · REC = recomendação (nota) · 📊 medido · 💭 ilustrativo. Tela: "Aplicativo"; código: `auxiliary` (D-131-18). Sem avaliação fictícia (D-131-26).

## 0. Fatos de base
- **B1** Ícones: **lucide-react 0.446.0**, a única biblioteca; mapa `lib/icons.ts:53-116`, wrapper `components/ui/Icon.tsx:20` (traço 1.6). Nomes do §2.4 conferidos em `node_modules/lucide-react/dist/esm/icons/`.
- **B2** Já instalados: Radix tabs/popover/switch/toggle-group/radio-group/accordion/collapsible; `ui/sheet`, `skeleton`, `progress`.
- **B3** Tokens em `app/globals.css:12-114`; dark padrão (`layout.tsx:38`), light existe; `next.config.js:41` `images.unoptimized`.
- **B4** 📊 Contraste calculado dos tokens (python, 12/10): `text-faint` **2,75:1** no `surface` escuro, 3,2:1 no claro → **reprova AA**; `muted-foreground` 5,1:1 passa; branco sobre `emerald-600` (botão Ligar) **3,77:1** reprova; light: `primary` 4,1 e `warning` 3,97 sobre `surface` reprovam texto pequeno.
- **B5** 📊 16 aplicativos (6 disponíveis, 10 em breve); coluna `icon` com `aprovacao/success/radar/file-text/null/auxiliares`, não lida (`catalog.ts:258-261`). `connector_templates.name` já tem nome humano ("Portal da Seguradora", "WhatsApp", "InfoCap"); `conectores_prontos` guarda só slug (`catalog.ts:324`).

## 1. Diagnóstico — o que dá a nota 50
**Galeria** (`AuxiliaresClient.tsx`): (1) card sem ícone nem imagem `:71-125`, apesar da coluna `icon` · (2) **emoji** nas categorias, card e filtros `:101`, `:214` (fonte `catalog.ts:131-138`) — o "infantil", contra DS-001 §14 · (3) Checklist com 6 chips no card · (4) selos minúsculos e `emerald-600/amber-600` crus `:27-48`, `:110` · (5) seção `text-xs uppercase muted` + subtítulo `text-[11px] text-faint` `:240-243` (reprova AA, B4) · (6) nome `text-sm`, frase `text-xs` `:79`, `:88` · (7) 8 filtros de ~26 px `:183-216`, busca `w-40` `:223` · (8) sem foco visível `:76`; spinner em vez de esqueleto `:231` · (9) em breve com o peso dos disponíveis (10 de 16).
**Página** (`[slug]/AuxiliarDetalheClient.tsx`): (10) sem ícone nem capa; emoji acima do título `:102-114` · (11) 9 seções iguais `text-xs uppercase muted` `:27` numa coluna `max-w-3xl` (`page.tsx:36`) · (12) ajuda `text-[11px] text-faint` `:175, :208, :248, :269, :318, :333` — os "subtítulos apagados" · (13) slug cru `:163-179`, `:186-195` · (14) Instalar `:222-258`, Executar `:261-273`, Ligar no pé `:299-343` — estado ausente do topo · (15) Ligar `bg-emerald-600 text-white` `:328` = 3,77:1 · (16) Histórico por `last_run_at` mente `:346-360` (I2 F7) · (17) erro técnico cru `:72`.
**Modal** (`PainelDeRotinas.tsx`): (18) `max-w-lg max-h-[90vh]` `:1005-1007`, contra DS-001 §8.6 · (19) repete o não editável `:1029`, `:1049-1061` · (20) o quê/como fala/quando sem grupo, 2 colunas espremidas `:1154` · (21) 14 seguradoras quase todas desabilitadas `:1111-1143`; `{placeholders}` crus `:1321-1347` · (22) 📊 22 × `text-[11px]` (`grep -c`).

## 2. A GALERIA (`/dashboard/auxiliares`, menu "Aplicativos")

### 2.1 Estilo
| opção | nota | por quê |
|---|---|---|
| capa em todos (Netflix/Spotify) | 72 | WOW, mas 10 capas "em breve" dominam |
| só ícone (plugins ChatGPT) | 68 | calmo, mas é a tela que tirou 50 |
| **híbrido** | **90** | 1 destaque grande + capa em Ligados/Disponíveis + linha só-ícone em Em breve |

### 2.2 Estrutura
1. `DetailHeader` "Aplicativos" — *"Ligue o que trabalha por você."*
2. **Destaque** (coluna `featured_rank`; some se nulo): `aspect-[3/1]` desktop, `aspect-[4/3]` celular, `rounded-2xl`; selo "Em destaque", nome `text-3xl font-semibold`, frase `text-base text-foreground-2`, botão "Conhecer" h-11. Nota 85 (sem: 75).
3. **Barra**: segmentado `Todos · Ligados (n) · Disponíveis (n) · Em breve (n)` (ToggleGroup h-10); chips de categoria **sem emoji**, ícone 14 px (`Coins`, `TrendingUp`, `HeartHandshake`, `Scale`, `ShieldCheck`, `Clock`), rolagem horizontal no celular; busca `w-full sm:w-72` "Buscar aplicativo".
4. **Seções** Ligados · Disponíveis (inclui desligado e falta conectar) · Em breve: `<h2> text-lg font-semibold` + contagem; subtítulo `text-sm text-muted-foreground` (nunca `faint`); divisor `border-t border-border-soft mt-10 pt-8`.

### 2.3 O card (Ligados e Disponíveis)
De cima para baixo, um `Link` só (nome acessível = nome + estado):
- **Capa** `aspect-[16/9]`: imagem do Founder ou capa gerada; selo de estado no canto superior esquerdo sobre `bg-background/70 backdrop-blur`; esmaece para `surface` na base.
- **Ícone** em tile 48 px sobreposto (`-mt-6 ml-4`, `rounded-xl bg-surface-2 border ring-4 ring-surface`), ícone 24 px traço 1.6.
- **Nome** `text-base font-semibold tracking-tight line-clamp-1` · **frase** `text-sm text-muted-foreground line-clamp-2 min-h-[2.5rem]`.
- **Rodapé** (`border-t border-border-soft`): prova real ou estado (`text-xs text-foreground-2`) · "Abrir →" (`text-primary`).
- Classes: `group flex h-full flex-col overflow-hidden rounded-2xl border bg-surface`; hover `-translate-y-0.5 border-primary/40 shadow-card`, capa `scale-[1.03]`; `motion-reduce:transform-none`; `focus-visible:ring-2 ring-ring ring-offset-2`.
- **Selo**: ligado "Ligado" (success) · pausado "Desligado" (neutral) · falta_conectar "Falta conectar" (warning) · disponível sem selo · em_breve "Em breve". Sempre `StatusPill`, nunca `emerald-*/amber-*`.
- **Prova real ou nada**: ligado → "18 execuções · última há 2 dias" (💭 forma; fonte `routine_runs`, conserta I2 F7); Renovação → "N renovações calculadas este mês" (desta corretora); falta conectar → "Falta conectar InfoCap"; disponível → "Pronto para ligar". Sem estrela; número entre corretoras fica para a SPEC "A loja".
- **Capa gerada** (`components/aplicativos/CapaDoAplicativo.tsx`, NOVO, G1): sem foto e sem texto — `surface-2` + 2 radiais com a matiz `--app-h` + grade de pontos 1 px + o ícone como marca d'água 120 px `opacity-[.12]`. CSS em `app/globals.css` (bloco `.capa-aplicativo`; G1 acrescenta o arquivo): dark `radial-gradient(120% 90% at 0 0, hsl(var(--app-h) 45% 38%/.55), transparent 60%), radial-gradient(90% 80% at 100% 100%, hsl(calc(var(--app-h) + 25) 40% 30%/.35), transparent 60%)`; light com `55% 85%` e `50% 90%`. Zero bytes.
- **Capa do Founder**: coluna `cover_url` (G1); `<img loading="lazy">` com `onError` → gerada. Para ele: **1600×900 WebP ≤ 150 KB, sem texto**. Nota 82 (mapa no código 65).
- **Em breve (compacto)**: linha `rounded-xl border-border-soft bg-surface/60 p-3`; tile 40 px muted; nome `text-sm font-medium`; frase 1 linha; selo.
- **Grid** `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4`, contêiner `max-w-7xl`; Em breve `sm:2 xl:3`.
- **Vazios** (DS-001 §8.9): sem ligados → "Nenhum aplicativo ligado ainda." · busca → frase + [Limpar busca] · erro → "Não conseguimos carregar os aplicativos agora." + [Tentar de novo] · carregando → 6 `Skeleton`.

### 2.4 Ícone e matiz de cada aplicativo
Ícones novos entram em `lib/icons.ts` (regra `:50-52`); `APLICATIVO_VISUAL: Record<slug,{icone: IconName; matiz: number}>` em `catalog.ts`; a migration grava a chave em `auxiliary_templates.icon`. Matizes frias + 1 âmbar (DS-001 §7.3).

| slug | lucide | h | | slug | lucide | h |
|---|---|---|---|---|---|---|
| checklist-6h | Sunrise | 38 | | caca-comissao | HandCoins | 150 |
| cobranca-feita | ReceiptText | 158 | | carteira-blindada | ShieldCheck | 205 |
| follow-up-whatsapp | MessageSquareReply | 200 | | clientes-perdidos | UserSearch | 230 |
| radar-mercado-regulacao | Radar | 262 | | contabilidade-pronta | BookOpenCheck | 175 |
| resumo-atendimentos | ScrollText | 215 | | digitacao-zero | ScanText | 225 |
| tarefas-agendadas | CalendarClock | 188 | | organizacao-completa | FolderCheck | 185 |
| **renovacao** | RefreshCcwDot | 203 | | protecao-completa | Umbrella | 210 |
| cotacao (nova) | Calculator | 195 | | resgatar-cliente | UserRoundCheck | 250 |
| quem-cobra-menos (nova) | BadgePercent | 165 | | sinistralidade-avancada | ChartNoAxesCombined | 240 |

Ícone no tile: dark `hsl(h 50% 72%)`, light `hsl(h 45% 38%)` (≥ 3:1). Conexões: InfoCap `Database` · Portal `Building2` · WhatsApp `MessageCircle` · Agger `Calculator`. **`scope=platform` não aparece** ("Firecrawl" é fornecedor).

## 3. A PÁGINA (`[slug]`, rota única)
**Cabeçalho** (`max-w-5xl`): "← Aplicativos" (`text-sm muted`, toque 44 px) · capa `aspect-[4/1]` (celular `aspect-[5/2]`) · tile 72 px `-mt-10 ring-4 ring-background` · `<h1> text-2xl sm:text-3xl font-semibold tracking-tight` · frase `text-base text-foreground-2` · selo · **"Funciona com"**: chips ícone + nome humano + ✓/!.
**Botão principal** (direita no desktop, largura total no celular, h-11; instalar ≠ ligar, SPEC-078): em_breve → desabilitado "Em breve" + o que falta · falta_conectar → "Conectar InfoCap" · não instalado → "Instalar" e abre `?aba=configurar` · desligado → **"Ligar"** (`bg-primary`) com confirmação curta (DS-001 §8.6 permite) · ligado → selo + "Desligar" fantasma ("não apaga nada"). Secundário "Abrir agora" se `tela_de_execucao`. Erro em português; `details[0]` vai para log.

**Abas** `?aba=` (Radix Tabs, `router.replace` sem rolar; barra `sticky top-0 bg-background/95 sm:backdrop-blur border-b`; gatilho h-11 `text-sm font-medium`; ativo `text-foreground` + sublinhado 2 px `primary`; rolagem horizontal no celular): `inicio` **Início** · `configurar` **Configurar** (ponto warning se falta passo) · `renovacoes` **Renovações** (com contagem; só quem tem, via `ABAS_DO_APLICATIVO`) · `duvidas` **Dúvidas**. Aba inválida → Início. Sem Configurar próprio → a aba mostra o `PainelDeRotinas` atual (Cobrança intocada, D-131-19).

**Início** (ordem da Shopify): (1) **O que é** — 2–3 frases `text-base leading-7 text-foreground-2 max-w-[65ch]` · (2) **O que faz** — `Check` 16 px + frequência `text-xs muted` (sai a pílula `text-[10px]`) · (3) **O que a corretora ganha** — cartão `bg-brand-soft border-primary/20 p-5`; com número real, `text-3xl tabular-nums` · (4) **Como começar** — passos derivados: conexões da corretora → conexões da pessoa ("Seu Agger", Meu perfil) → Configure → Ligue; cada um: círculo 28 px (nº ou ✓), título `text-sm font-medium`, 1 linha `text-sm muted`, pílula + link ("Conectar →", "Configurar →"); topo "2 de 4 prontos" + `Progress`; conectado = **"✓ Conectado · mudar"** · (5) **Atividade recente** — 3 últimas de `routine_runs` · (6) **Dúvidas** — 3 perguntas + "Ver todas".
Títulos `<h2> text-lg font-semibold`; divisor `border-t border-border-soft py-8`. **Saem**: "De onde ele tira a informação", slugs crus, Instalar/Ligar/Executar soltos, Histórico por `last_run_at`.

**Dúvidas**: `Accordion` `max-w-3xl`; pergunta `text-base font-medium`, resposta `text-sm leading-6 muted`. Fonte: coluna `faq jsonb` global (80; em TS 65). 💭 Renovação: quando fica pronta · qual Agger · o cliente recebe sozinho · ramo sem cotação · quem vê o quê.

## 4. CONFIGURAR (no lugar do modal)
`max-w-3xl`. Grupo = `<h2> text-base font-semibold` + 1 linha `text-sm muted` + cartão `rounded-xl border bg-surface divide-y divide-border-soft`; linha `grid gap-2 p-4 sm:grid-cols-[1fr_1.3fr] sm:gap-6`, rótulo `text-sm font-medium` + ⓘ à esquerda, controle à direita (print OPENAI AGENTS PRINCIPAL).

| grupo | Renovação | componente |
|---|---|---|
| **O que fazer** | Só calcular · Calcular e preparar o envio · (enviar e negociar: "em breve", D-131-24) · opções 1·2·3 (padrão 3, D-131-27) | 3 cartões `RadioGroup`; `ToggleGroup` |
| **Quando** | "Preparar [10] dias antes" (D-131-01) · linha só-leitura `Clock` "Fica pronto antes das 7h" | número com −/+ h-10 |
| **Com qual conta** | Agger: "Do responsável (recomendado)" / "Da corretora" · "✓ Agger da corretora conectado · mudar" ou "! 2 pessoas sem Agger · ver equipe" · WhatsApp só-leitura: "Sai do celular de quem clica" | segmentado + linha de estado |
| **Avançado** (`Collapsible` fechado) | exceções ramo/valor · reajuste · seguradoras "da corretora / própria" (chips de LISTA; sem acesso em "mostrar 9") · `Switch` "Se o Agger do responsável falhar, usar o da corretora" | `Switch`, chips `aria-pressed` |

- ⓘ abre **`Popover`** (tooltip não abre com toque). O já decidido não vira campo.
- Barra `sticky bottom-0` só com alteração: "Alterações não salvas" [Descartar] [Salvar] h-11; 409 → "Outra pessoa salvou antes. Recarregue."

## 5. O TRABALHO FEITO (Renovações)
**Extrair `components/aplicativos/QuadroOuLista.tsx`** de `AttendanceQueueClient.tsx` (G2 dona dos dois). Vai: segmentado Quadro×Lista (`:229-252`) + preferência `localStorage` em try/catch (`:96`, `:113-129`, chave por parâmetro); coluna com cabeçalho grudado e contagem (`:316-345`); `snap` (`:310`); teto de pintura (`:101`, `:351-358`); lista (`:367-373`); slot vazio. Fica: polling, filtro de dono, ordem/títulos, `abrir`. Assinatura: `QuadroOuLista<T>({itens, colunas:{id,titulo,descricao?,tom,esconderSeVazia?}[], colunaDe, chave, Card, Linha, onAbrir, preferencia, vazio, barra?, cardsPorColuna=50})`. **Sem arrastar** (`:29-30`).

- **Topo**: atalhos-filtro reais (`aria-pressed`): Precisa de você · Prontas para enviar · Enviadas sem resposta · Vencem em 7 dias. Barra: **Minhas · Todas** (comercial → Minhas; admin → Todas) · período · Ramo · Seguradora · Estado · busca "Nome, CPF ou placa". Celular: "Filtros (n)" em `Sheet side="bottom"`. **Filtros na URL** (`&de=minhas&periodo=7d&item=<id>`): "voltar" fecha o detalhe.
- **Lista ≥ 1024 px**: linhas 56 px por dia de vencimento (cabeçalho grudado). Colunas: Cliente (nome + doc mascarado) · Ramo · Vence (+ "em 8 dias") · Seguradora atual → recomendada · Prêmio atual → novo + Δ% (`tabular-nums`, seta + sinal) · Responsável · Estado · ações-ícone 36 px com `aria-label` (Ver apresentação · WhatsApp · Copiar · ⋯ fechada/perdida com motivo). Chevron `aria-expanded` → 3 cálculos. 640–1023: 2ª linha.
- **Quadro**: colunas SPEC §4.7 (4 últimas escondidas até ter item); card de `caso-visual.tsx` (`:193`): nome · ramo + vence em · prêmio + Δ · responsável · **um** selo "Precisa de você".
- **Celular**: cartões (nome · vence em · prêmio + Δ · estado · **"Enviar"** h-11); quadro uma coluna por vez.
- **Detalhe** (`&item=`): desktop `Sheet side="right"` 520 px; celular tela cheia `h-[100dvh]` com barra `sticky bottom-0 pb-[env(safe-area-inset-bottom)]`: **[Enviar pelo WhatsApp]** · **[Ver apresentação]** · Copiar (D-131-24). Conteúdo: cabeçalho com **próximo passo** · 3 cálculos com Δ · comissão (quem pode) · linha do tempo.

## 6. Referências (protocolo §7.3) e régua do juiz
| tela | URL | modelamos | rejeitamos |
|---|---|---|---|
| capa gerada | https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF | capa "Top 50" = cor + forma, sem foto | texto na capa |
| galeria | https://www.raycast.com/store | ícone + nome + 1 linha + número REAL de uso | ranking |
| cabeçalho | https://developer.apple.com/app-store/product-page/ | ícone + nome + subtítulo de 1 linha + 1 botão | keywords, compra |
| Início | https://apps.shopify.com/shopify-forms | o que é → destaques → funciona com → suporte | preço, apps parecidos |
| Configurar | https://primer.style/ui-patterns/saving · https://primer.style/ui-patterns/progressive-disclosure | salvar explícito; Avançado recolhido | autosave |
| trabalho | https://linear.app/docs/board-layout | lista ↔ quadro, mesmos filtros | arrastar |
| AA | https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html | 4,5:1 | — |
Interna (vence): os prints de plugins GPT e OpenAI Agents da pasta de intake.

**Checklist** (390×844 e 1366×768, dark e light): 1 `rg` de emoji em `app/dashboard/auxiliares components/aplicativos lib/auxiliaries` → 0 · 2 todo card com o ícone do §2.4 · 3 sem `cover_url` → gerada; URL quebrada → gerada · 4 em breve compacto, demais com capa · 5 grid 1/2/3/4 · 6 nenhuma estrela; todo número com SELECT que bate · 7 Tab com foco visível · 8 busca vazia → "Limpar busca" · 9 ícone, nome, frase, selo e botão sem rolar · 10 nenhum slug (`insurance`, `zapi`, `_`) nem Firecrawl · 11 `?aba=configurar` abre direto; inválida → Início; "voltar" troca de aba · 12 cada passo com estado e link; "N de M" confere · 13 Atividade = `routine_runs` · 14 novos: `text-faint` só decorativo, `text-[10px]/[11px]` → 0 · 15 `rg "emerald-|amber-"` → 0 · 16 axe/Lighthouse sem erro de contraste · 17 Configurar: 4 grupos, Avançado fechado, ⓘ abre com toque · 18 alterar mostra a barra; Descartar volta · 19 Lista ↔ Quadro mantém filtros e a escolha volta · 20 arrastar não muda nada · 21 "Precisa de você" filtra, `aria-pressed`, número = coluna · 22 celular: detalhe tela cheia, barra acima da área segura · 23 "Enviar" abre `wa.me`; "Copiar" copia a mesma mensagem · 24 `/dashboard/atendimentos/fila` igual após a extração · 25 `npm run test:rotas-montam` + `next start` + `GET /dashboard/auxiliares/renovacao?aba=renovacoes` → 200 (CLAUDE.md §9.1).

## 7. Riscos e custos
- **Contraste (B4)**: 131-B **não mexe em token global**; proíbe `faint` informativo e usa `muted-foreground`. Ajuste de token (light `--primary` L≤40, `--warning` L≤34, `--success` L≤36; dark `--faint` L≥54) → SPEC "A loja" (80).
- **Imagens**: `unoptimized` → sem a regra de 150 KB uma capa de 3 MB trava o celular.
- **Movimento**: `backdrop-blur` só `sm:` (Android barato); hover em CSS; `motion-reduce`.
- **Peso**: aba por `import()` (contrato G1); lista pagina em 100. **Extração** pode mudar a Fila → item 24.
- **Escopo**: `cover_url`, `faq`, `featured_rank` + UPDATE de `icon` na migration de G1 (expand-only, global). **PII**: os prints de `TELAS ATUAIS` mostram telefones — nunca usar.
