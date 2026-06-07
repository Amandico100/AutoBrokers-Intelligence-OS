# 37A1 — Adapted Execution Plan

> **Status:** baseline operacional de execução (documental)
> **Última atualização:** 2026-06-07 · **Produto:** AutoBrokers.ai · **Sistema:** AutoBrokers Intelligence OS
> **Base:** BATCH 37A0.1 (robust recon read-only) + Decisões do Architect (2026-06-07).
> Este documento **substitui** o `BATCHES-001-claude-code.html` como fonte de execução: os cards originais
> foram escritos sem inspeção do repo real e contêm colisões (corrigidas aqui).

---

## 1. Estado real do repo

| Item | Valor confirmado |
|---|---|
| Package manager | **npm** (`package-lock.json`; sem pnpm/yarn) |
| Framework | **Next.js 15.5.9, App Router**, pasta raiz `app/` (não `src/app/`) |
| React | 18.3 |
| Tailwind | **3.3.3**, config **`tailwind.config.ts`** (TypeScript, não `.js`) |
| ShadCN/Radix | Configurado: `components.json` (style default, baseColor neutral, `cssVariables: true`) + conjunto Radix completo + `class-variance-authority`/`clsx`/`tailwind-merge` |
| Utilitário `cn` | **`lib/utils.ts`** (alias `@/lib/utils`) — **já existe, não criar `lib/cn.ts`** |
| Tokens/tema | `app/globals.css` com vars ShadCN em **HSL**; primary roxo (`262 80% 50%`), dark bg `#030014`; `@import` de **Plus Jakarta Sans**; **Inter** em `app/layout.tsx`; **Geist não instalado** |
| Scripts | `dev`, `build`, `start`, `lint`, `typecheck` — **sem test runner** (checks = `npm run typecheck` + `npm run build` + verificação visual) |
| Layout raiz | `app/layout.tsx` = global (html/body, `ThemeProvider` dark, `Toaster`, fonte, favicon `/smith-logo.png`) — **NÃO é onde entra o AppShell** |
| Layout tenant | `app/dashboard/layout.tsx` = só `<div bg-[#2f2f2f]>` + `TermsAcceptanceModal` (sem sidebar) — **AQUI entra o AppShell** |
| Layout admin | `app/admin/layout.tsx` = shell próprio (não tocar) |
| Layout embed | `app/embed/[agentId]/layout.tsx` (não tocar) |
| Chat | `app/dashboard/page.tsx` re-exporta `ChatPage` de `app/dashboard/chat/page.tsx` (stream SSE, agentes, conversas, realtime, voz n8n); proxy `app/api/chat/stream/route.ts` → FastAPI `${backendUrl}/chat/stream` |
| Componentes UI existentes | `components/ui/*` (button, tabs, dialog, breadcrumb, card, badge, skeleton, sheet, drawer, …), `components/EmptyState.tsx`, `components/InputArea/*`, `MessageBubble`, `TypingIndicator`, `UnifiedSidebar`, `Sidebar` |
| Ícones | `lucide-react` instalado (base recomendada do B‑ICONS) |
| Branding residual visível | `/smith-logo.png` (favicon + EmptyState + admin + auth), `agentsmith.ai` (embed), `SmithWidget` (`public/widget.js`) — limpeza em batch dedicado, fora deste plano |

---

## 2. Decisões bloqueadoras respondidas (Architect, 2026-06-07)

1. **AppShell tenant em `app/dashboard/layout.tsx`** — nunca em `app/layout.tsx` (quebraria Admin/Login/Landing/Embed).
2. **Package manager = `npm`** — ignorar `pnpm` dos mockups. Checks oficiais: `npm run typecheck`, `npm run build`.
3. **Tokens Névoa → HSL mantendo as variáveis ShadCN** (`--background`, `--foreground`, `--card`, `--card-foreground`, `--popover`, `--popover-foreground`, `--primary`, `--primary-foreground`, `--secondary`, `--secondary-foreground`, `--muted`, `--muted-foreground`, `--accent`, `--accent-foreground`, `--destructive`, `--destructive-foreground`, `--border`, `--input`, `--ring`). Sem sistema paralelo; sem quebrar Admin/Login/Landing.
4. **Todas as rotas tenant sob `/dashboard/*`** — qualquer rota de mockup sem `/dashboard` é inconsistência e deve ser corrigida. Rotas-alvo: `/dashboard`, `/dashboard/atendimentos[/casos|/conversas|/segurados]`, `/dashboard/auxiliares[/galeria|/execucoes]`, `/dashboard/personalizacao[/conectores|/seguradoras|/conhecimento|/corretora|/equipe]`.
5. **B5 e B6 bloqueados** — B5 (Auxiliar de Resumo funcional) exige modelo de execuções/runs; B6 (Atendimento real/HITL) exige modelo de casos. Por ora apenas shells/mocks (B4). Liberam só com novos ADRs/modelos de dados.
6. **Pastas externas** (`ResultVision`, `AUTOBROKERS_RESULTA_INTAKE`, `AUTOBROKERS_AGENT_OS_WORKSPACE`, `QUARENTENA_LEGADO_2026-04-27`) = referência apenas. Não copiar, não ingerir, não abrir PII, não usar em RAG, não importar código, não tocar credenciais. Uso futuro só via Vault + curadoria + redaction.

---

## 3. Batches adaptados

> Correções aplicadas vs. `BATCHES-001` original: **npm** (não pnpm); **`tailwind.config.ts`** (não `.js`); **reutilizar `lib/utils.ts`** (não criar `lib/cn.ts`); **reutilizar `components/ui/button|skeleton|tabs|breadcrumb` e `components/EmptyState`** (não criar gêmeos PascalCase — FS do Windows é case-insensitive); **AppShell em `app/dashboard/layout.tsx`** (não no raiz); **rotas sob `/dashboard/*`**; **tokens Névoa→HSL nas vars existentes**.

| Batch | Objetivo | Status | Arquivos prováveis (repo real) | Fora de escopo | Checks |
|---|---|---|---|---|---|
| **B-ICONS** | Set único de ícones (base **Lucide**, já instalada) via wrapper, p/ não inventar ícones | ✅ Pronto | `components/ui/Icon.tsx` (wrapper: name/size/strokeWidth=1.6/currentColor), `lib/icons.ts` (mapa nome→ícone Lucide) | Recriar logos de marca; refator amplo de usos atuais de lucide | `npm run typecheck` + `npm run build` |
| **B0_ADAPTED_TOKENS_PRIMITIVES** | Cravar **Névoa→HSL** nas vars ShadCN, **Geist** via `next/font`, primitivos faltantes e sandbox visual | ✅ Pronto (1º código) | `app/globals.css` (valores das vars), `tailwind.config.ts` (cores extras Névoa: surface-2, accent-soft, success/warning), `app/layout.tsx` (Geist via next/font; remover Inter), `components/ui/{Tile,StatusBadge,ErrorState}.tsx` (**reusar** button/skeleton/EmptyState existentes), `app/_sandbox/page.tsx` | Sidebar, chat, rotas de módulo, fetch; **não** criar `lib/cn.ts`; **não** duplicar button/skeleton/emptystate; **não** mexer em backend | typecheck + build + **validar Admin/Login/Landing legíveis** |
| **B1_DASHBOARD_APPSHELL** | Esqueleto navegável: sidebar desktop (4 pilares) + bottom-nav mobile, breadcrumb, back, page header | ✅ Pronto após B0 | `components/layout/{AppShell,AppSidebar,BottomNav,BrandMark,PageHeader,BackLink}.tsx`, `lib/nav.ts`, **`app/dashboard/layout.tsx`** (editar: envolver com AppShell, **preservar `TermsAcceptanceModal`**) | **NÃO** tocar `app/layout.tsx` raiz; conteúdo das telas; chat; histórico real | typecheck + build; Admin/Login/Embed/Landing intactos |
| **B2_CHAT_FIRST_ADAPTER** | `/dashboard` chat-first (marca, saudação, composer, **2 atalhos**) **reusando o stream existente** via adapter | ✅ Pronto após B1 | `app/dashboard/page.tsx` (editar), `components/chat/{ChatEmptyState,ChatComposer,ShortcutChip}.tsx`, `lib/chat.ts` (adapter sobre a lógica de `app/dashboard/chat/page.tsx`: SSE, conversas, realtime, voz) | **NÃO** alterar `/api/chat/stream` nem backend; **não** reescrever stream/realtime/voz; ocultar seletor de agente p/ usuário comum | typecheck + build; `/dashboard` ainda streama; erro amigável |
| **B3_PATTERNS_MASTER** | Padrões-mestre (Galeria, Detalhe, Modal de permissão) + transversais, isolados em sandbox com mock | ✅ Pronto após B0 (paralelo a B1/B2) | `components/patterns/{GalleryGrid,GalleryCard,CategoryFilter,SearchField,DetailHeader,PermissionModal,PermissionRow,RiskBar}.tsx`, `components/ui/{SegmentedControl,SideCard,KeyValueList,BottomSheet,ListRow,ChipTag}.tsx` (**reusar `tabs.tsx`/`dialog.tsx` existentes**), `app/_sandbox/page.tsx` (editar) | Telas de módulo reais, rotas, fetch, backend | typecheck + build; A/B/C no sandbox (modal↔bottom-sheet, tabs↔segmented) |
| **B4_MODULE_SHELLS** | Shells dos módulos sob `/dashboard/*` com dados mockados: Auxiliares, Conectores, Seguradoras, Atendimentos | ✅ Pronto após B1–B3 (shell/mock apenas) | `app/dashboard/auxiliares/{page,galeria/page,execucoes/page,[id]/page}.tsx`, `app/dashboard/personalizacao/{conectores,seguradoras,conhecimento,corretora,equipe}/...`, `app/dashboard/atendimentos/{casos,conversas,segurados}/...`, `components/modules/{InsurerCard,StatCard,ChannelRow,Timeline,HitlBanner}.tsx`, `lib/mock/*.ts` | Execução real, dados reais, OAuth, lógica de corredor, migrations; **HitlBanner é visual/mock (sem ação real)** | typecheck + build; todas as rotas abrem com estados vazio/loading/erro |
| **B5 — Auxiliar de Resumo funcional** | — | 🔴 **BLOQUEADO** | — | Exige modelo de execuções/runs (ADR + tabela). Não há store de runs no runtime. Liberar só após ADR de dados de Auxiliares. | — |
| **B6 — Atendimento real + HITL** | — | 🔴 **BLOQUEADO** | — | Exige modelo de casos/atendimentos. Não existe no runtime. Liberar só após ADR de dados de Atendimento. | — |

---

## 4. Riscos protegidos

- **Não tocar `app/layout.tsx` para AppShell** — o AppShell tenant vai em `app/dashboard/layout.tsx`; o layout raiz é global (Admin/Login/Landing/Embed dependem dele).
- **Não quebrar Admin/Login/Embed/Landing** — a troca de tokens (B0) afeta `app/globals.css` (compartilhado); validar essas superfícies após cada mudança de tema.
- **Não substituir o chat streaming** — preservar `app/dashboard/chat/page.tsx`, `app/api/chat/stream/route.ts`, `/api/conversations|messages|agents`, realtime Supabase e voz n8n; B2 só re-skina via adapter.
- **Não criar tokens paralelos** — Névoa entra como **valores HSL** nas variáveis ShadCN já existentes.
- **Não duplicar componentes ShadCN com casing diferente** — reutilizar `components/ui/button.tsx`, `skeleton.tsx`, `tabs.tsx`, `breadcrumb.tsx` e `components/EmptyState.tsx`; nada de `Button.tsx`/`Tabs.tsx` (FS Windows é case-insensitive → risco de sobrescrita).
- **Não abrir/ingerir PII** — pastas `INTAKE`/`QUARENTENA`/`WORKSPACE`/`ResultVision` (incl. `ACESSOS API INFOCAP.txt`, apólices, `output/auth_cookies.txt`) só via Vault + curadoria futura.

---

## 5. Próximo batch recomendado

**BATCH 37B0 — `B-ICONS` + `B0_ADAPTED_TOKENS_PRIMITIVES`**

Primeiro batch de código real, de menor risco de produto (não cria rota, não mexe no chat nem no AppShell):
- B‑ICONS: `components/ui/Icon.tsx` + `lib/icons.ts` (base Lucide).
- B0: Névoa→HSL em `app/globals.css` (mantendo as vars ShadCN), Geist via `next/font` em `app/layout.tsx`, cores extras em `tailwind.config.ts`, primitivos faltantes (`Tile`, `StatusBadge`, `ErrorState`) **reusando** os existentes, e `app/_sandbox/page.tsx`.
- **PRONTO:** `npm run typecheck` + `npm run build` verdes; `/app/_sandbox` mostra primitivos + 6 tons de StatusBadge com os hex Névoa; Geist carregada (sans+mono); **Admin/Login/Landing continuam legíveis**.

Sequência seguinte: 37B1 (AppShell em `app/dashboard/layout.tsx`) → 37B2 (chat-first adapter) → 37B3 (padrões) → 37B4 (shells). **B5/B6 ficam fora até existirem os modelos de dados.**
