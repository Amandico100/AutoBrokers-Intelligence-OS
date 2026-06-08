# 37B3 — Master Patterns Report

> **Status:** concluído, **commitado e pushado** · build validado com variáveis **dummy temporárias** (sem `.env.local`, sem secrets reais).
> **Data:** 2026-06-07 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Resumo executivo
Criados os **3 padrões-mestre reutilizáveis** (Galeria, Detalhe, Modal de Permissão) + `StatusPill`, como componentes genéricos em `components/patterns/`, em Névoa/Geist/Lucide, **sem dados reais e sem backend**. Demonstração interativa em `/sandbox`. Nenhuma lógica de runtime, chat, backend ou migration foi tocada. `typecheck` + `build` verdes. Componentes prontos para o **B4** (shells de Auxiliares, Conectores, Seguradoras, Conhecimento, Atendimentos).

## 2. Arquivos alterados
**Criados:**
- `components/patterns/StatusPill.tsx`, `GalleryGrid.tsx`, `GalleryCard.tsx`, `GalleryFilters.tsx`, `DetailHeader.tsx`, `DetailSection.tsx`, `DetailShell.tsx`, `PermissionList.tsx`, `PermissionModal.tsx`, `index.ts` (barrel).
- `app/sandbox/PatternsShowcase.tsx` — demo client (estado de filtros/busca/modal). **Arquivo extra** (não estava na lista): necessário porque `app/sandbox/page.tsx` exporta `metadata` (server component) e a demo precisa de `useState`; isolei a interatividade num client component importado pela página.
- `docs/canon/design/2026-06-claude-design/37B3-report.md`.

**Modificados:**
- `lib/icons.ts` — adicionados ícones úteis (`check`, `negado`, `cadeado`, `banco`, `drive`, `cobranca`).
- `app/sandbox/page.tsx` — importa e renderiza `<PatternsShowcase />` numa nova seção (mantém `metadata`).

## 3. Componentes criados
- **StatusPill** — badge de status (6 tons: neutral/info/success/warning/danger/approval; cor + ponto + texto; approval com borda tracejada + pulso). HANDOFF §3.
- **GalleryGrid / GalleryCard / GalleryFilters** — padrão Galeria.
- **DetailHeader / DetailSection / DetailShell** — padrão Detalhe (header + abas Radix + bloco lateral).
- **PermissionList / PermissionModal** — padrão Modal de Permissão (HITL).
Todos usam `cn` (`lib/utils`), `Icon`/`lib/icons`, e reutilizam ShadCN existente (`button`, `dialog`, `tabs`) — **nada recriado**.

## 4. Padrão Galeria
`GalleryFilters` (busca + pílulas de categoria, **controlado**) + `GalleryGrid` (1/2/3 colunas) + `GalleryCard` (ícone, título, descrição, categoria, tags, `StatusPill`, CTA com chevron). Suporta estados via StatusPill (ativo, pronto, em breve, precisa configurar, bloqueado, aguardando aprovação) e `disabled` ("em breve"). Card vira `Link` (href), `button` (onClick) ou `div` (estático). Cards limpos, hover discreto, mobile-first.

## 5. Padrão Detalhe
`DetailShell` compõe `DetailHeader` (breadcrumb/voltar + ícone + título + subtítulo + StatusPill + ações) com **abas** (Radix `Tabs`, `defaultValue` — sem estado próprio) e um **bloco lateral** opcional. `DetailSection` é o bloco padrão (título + descrição + conteúdo). Demo: "Auxiliar de Resumo de Atendimentos" com abas Visão geral / Como funciona / Permissões / Execuções + resumo lateral (Categoria/Risco/Envio externo).

## 6. Padrão Modal de Permissão
`PermissionModal` (controlado por `open`/`onOpenChange`, sobre o `Dialog` do ShadCN) com ícone, título, descrição, `PermissionList` (grupos "vai poder" / "não vai poder" com check/X), faixa **HITL** opcional ("ações externas exigem aprovação humana") e CTAs primário/secundário. Linguagem de corretora (sem MCP/webhook/API key): "consultar conversas", "preparar mensagens", "enviar com aprovação".

## 7. Demonstração em /sandbox
`/sandbox` agora mostra, abaixo da fundação B0: **Estados** (todos os tons), **Galeria · Auxiliares** (com filtros/busca funcionais em mock), **Galeria · Conectores** (clique abre o modal), **Detalhe** (DetailShell com abas + lateral) e **Modal de Permissão** (botão de abrir). Tudo mock, sem backend. Rota interna, não linkada na navegação.

## 8. O que NÃO foi alterado
`app/dashboard/chat/page.tsx`, `components/InputArea/*`, backend, Supabase/migrations, APIs, `package.json`, Admin, AppShell/sidebar/bottom-nav, tokens (só adicionei ícones). Sem lógica real de Auxiliares/execução/scheduler/integração. Sem acesso a pastas externas.

## 9. Checks executados
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ passou |
| `npm run build` | ✅ passou (env dummy temporária) |
| `git diff --check` | ✅ limpo (só `LF→CRLF`) |
| scan azul/branding (patterns + sandbox) | ✅ **sem ocorrências** nos componentes novos |

## 10. Branding/resíduos encontrados
- ✅ **Componentes novos limpos**: sem `JARVYS`/`smith-logo`/azul; usam apenas tokens Névoa (`primary`, `surface`, `success`, `warning`, `danger`, `brand-soft`).
- ⚠️ Resíduos **pré-existentes** (fora do escopo do B3, cleanup futuro): azul em `/dashboard/historico` e `/dashboard/configuracoes`, `TermsAcceptanceModal`, `ui/switch`/`ui/slider`, `AvatarUpload`, auth/landing/admin/embed/UCP; dead code `UnifiedSidebar.tsx`/`Sidebar.tsx`.

## 11. Riscos/remanescentes
- `app/sandbox/PatternsShowcase.tsx` é client (interatividade); `page.tsx` segue server (metadata). Sem impacto.
- `/sandbox` continua rota pública interna (proteger/remover antes de prod).
- Os padrões são **mock/visuais**; a ligação com dados reais (RAG, agents, casos) acontece nos batches de módulo/dados.
- Build local depende de env (dummy/real).

## 12. Próximo batch recomendado
**37B4 — Shells dos módulos** sob `/dashboard/*` (Auxiliares: lista/galeria/execuções; Personalização: Conectores/Seguradoras/Conhecimento; Atendimentos: lista/caso) usando estes padrões + `lib/mock`, **sem backend novo**. Antes disso, confirmar que o ajuste do agente (37B2.2) foi aplicado no Supabase e o "Roma" responde corretamente.
