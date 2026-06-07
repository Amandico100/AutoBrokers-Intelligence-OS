# 37B1 — Tenant AppShell and Navigation Report

> **Status:** implementação concluída, **commitada e pushada** · build validado com variáveis **dummy temporárias** (processo único, sem `.env.local`, sem secrets reais).
> **Data:** 2026-06-07 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Resumo executivo
Casca visual do dashboard da corretora implementada: **TenantAppShell** com **sidebar desktop** (4 pilares + secundário + rodapé), **top bar mobile com drawer** e **bottom nav mobile** (4 pilares), tudo na paleta Névoa + Geist + ícones Lucide via wrapper. O **`/dashboard` continua chat-first** e o chat segue funcionando — a sidebar duplicada (`UnifiedSidebar`) foi removida das páginas internas, sem refatorar a lógica do chat. Criados shells simples e elegantes para `/dashboard/atendimentos`, `/dashboard/auxiliares` e `/dashboard/personalizacao`. `typecheck` + `build` verdes; nenhuma rota fora de `/dashboard`.

## 2. Arquivos alterados
**Criados:**
- `lib/navigation.ts` — modelo de navegação (PILLARS, SECONDARY, `isActiveRoute`).
- `components/BrandMark.tsx` — mark geométrico reutilizável (símbolo + wordmark).
- `components/layout/TenantNav.tsx` — corpo da navegação (marca, nova conversa, 4 pilares, secundário, rodapé logout/tema; busca perfil para nome da corretora).
- `components/layout/TenantSidebar.tsx` — sidebar desktop (lg+).
- `components/layout/TenantTopBar.tsx` — top bar mobile com drawer (ShadCN Sheet) reutilizando `TenantNav`.
- `components/layout/TenantBottomNav.tsx` — bottom nav mobile (4 pilares, safe-area).
- `components/layout/TenantAppShell.tsx` — composição (sidebar + topbar + main + bottomnav).
- `app/dashboard/atendimentos/page.tsx`, `app/dashboard/auxiliares/page.tsx`, `app/dashboard/personalizacao/page.tsx` — shells.
- `docs/canon/design/2026-06-claude-design/37B1-report.md` — este relatório.

**Modificados:**
- `app/dashboard/layout.tsx` — envolve `children` com `TenantAppShell`; **preserva `TermsAcceptanceModal`**; remove o `bg-[#2f2f2f]` legado.
- `app/dashboard/chat/page.tsx` — remove `UnifiedSidebar` + offset `lg:ml-64` (presentational; **lógica de chat intacta**).
- `app/dashboard/historico/page.tsx` — remove `UnifiedSidebar` + offset; conteúdo passa a rolar dentro do shell.
- `app/dashboard/configuracoes/page.tsx` — idem.
- `lib/icons.ts` — adiciona `historico` (History), `configuracoes` (Settings), `sair` (LogOut); `personalizacao` passa a `SlidersHorizontal` (alinha ao set do design).

## 3. Como o dashboard renderizava antes
Cada página (`chat`, `historico`, `configuracoes`) renderizava sua **própria** `UnifiedSidebar` (fixa `w-64`) + um wrapper `flex` com offset `lg:ml-64`. O `layout.tsx` era só um `<div bg-[#2f2f2f]>` + `TermsAcceptanceModal`. A navegação era o **menu antigo de 3 itens** (AutoBrokers / Histórico / Configurações), com `smith-logo.png` e acentos azuis.

## 4. Como o AppShell foi implementado
O `TenantAppShell` virou a casca única em `app/dashboard/layout.tsx`:
`flex h-screen` → **sidebar desktop** (à esquerda) + coluna de conteúdo (`TopBar` mobile + `main` rolável + `BottomNav` mobile). O `main` é o único container de altura (`flex-1 min-h-0 overflow-hidden`); cada página gerencia o próprio scroll. A bottom nav fica **no fluxo** (não `fixed`), então nunca cobre o input do chat e respeita a safe area.

## 5. Como evitou sidebar duplicada
A `UnifiedSidebar` foi **removida das 3 páginas internas** (imports + JSX + offset `lg:ml-64`). A navegação estrutural agora vem só do AppShell. O chat manteve seu botão "Novo Chat" no header (handler preservado); a lista de conversas recentes da sidebar antiga sai do chat nesta fase — o acesso ao histórico permanece via **Histórico** (`/dashboard/historico`). `UnifiedSidebar.tsx` ficou **sem uso** (dead code) e deve ser removido num cleanup futuro (ainda contém `smith-logo.png`).

## 6. Sidebar desktop criada
`TenantSidebar` (lg+): `w-64`, borda sutil, fundo `surface`. Contém: **BrandMark** (símbolo + "AutoBrokers"), botão **Nova conversa** (→ `/dashboard`), **4 pilares** (AutoBrokers, Atendimentos, Auxiliares, Personalização) com barra de accent no item ativo, divisor, **secundário** (Histórico, Configurações) e **rodapé** (nome da corretora — dado real do perfil — + Sair + ThemeToggle).

## 7. Bottom nav mobile criada
`TenantBottomNav` (lg-): 4 pilares, ícones Lucide + rótulos curtos (Personalização → "Config"), item ativo em accent, `pb-[env(safe-area-inset-bottom)]`. Complementada pela `TenantTopBar` (marca + menu drawer com a navegação completa + nova conversa), garantindo acesso a Histórico/Configurações/Sair também no mobile.

## 8. Rotas criadas/alteradas
- Mantidas: `/dashboard` (chat-first), `/dashboard/chat`, `/dashboard/historico`, `/dashboard/configuracoes`.
- Criadas (shells, sob `/dashboard`): `/dashboard/atendimentos`, `/dashboard/auxiliares`, `/dashboard/personalizacao`.
- **Nenhuma** rota fora de `/dashboard` (sem `/atendimentos`, `/auxiliares`, `/personalizacao` na raiz). Build confirma todas como estáticas sob `/dashboard`.

## 9. O que NÃO foi alterado
`app/layout.tsx` raiz (não recebeu AppShell). Backend, Supabase/migrations, APIs (chat/stream/billing/RAG), `package.json`, EasyPanel, secrets. Admin intacto. Lógica de chat (stream, conversas, realtime, voz) intacta. `app/dashboard/page.tsx` segue re-exportando o chat.

## 10. Branding residual encontrado
- ✅ **Dashboard tenant agora sem `smith-logo`** (usa BrandMark).
- ⚠️ Visível (auth/landing, fora do dashboard): `login`, `register`, `forgot-password`, `reset-password`, `pending-approval`, `HeroSection` → `smith-logo.png`.
- ⚠️ Visível (admin): `admin/layout`, `admin/login` → `smith-logo.png`.
- ⚠️ Dead code (superseado por este batch): `UnifiedSidebar.tsx`, `Sidebar.tsx` → `smith-logo.png` (não renderizados).
- ⚠️ Embed: `agentsmith.ai` em `app/embed/[agentId]/page.tsx`.
- ✅ Sem `JARVYS`/`Agent Smith`/`Smith AI`/`Sistema Smith` no código.
→ Tudo pré-existente / fora do escopo do B1; sugerido batch de cleanup dedicado.

## 11. Checks executados e resultado
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ passou |
| `npm run build` | ✅ passou (envs dummy temporárias); rotas novas sob `/dashboard`; sem rota fora do padrão |
| `git diff --check` | ✅ limpo (só avisos benignos `LF→CRLF`) |
| branding scan | ✅ dashboard sem smith-logo; resíduos pré-existentes listados em §10 |

## 12. Riscos/remanescentes
- Conversas recentes saíram da sidebar do chat (acesso via Histórico). A lista "Recentes" integrada à sidebar volta no **B2**, quando o chat for adaptado (estado elevado/contexto).
- `UnifiedSidebar.tsx` e `Sidebar.tsx` viraram dead code com `smith-logo` → remover em cleanup.
- Header do chat ainda usa acentos `bg-blue-600` (B2 reescreve o chat-first).
- Build local exige env (dummy ou real); no EasyPanel completa com env real.
- `/sandbox` continua rota pública interna (proteger/remover antes de prod).

## 13. Próximo batch recomendado
**37B2 — Chat-first em `/dashboard`**: adaptar o empty state (saudação "Como posso ajudar sua corretora hoje?" + 2 atalhos "Ver atendimentos"/"Novo auxiliar"), composer e re-skin do chat na paleta Névoa, **reutilizando o stream existente via adapter** (sem tocar no backend) e reintroduzindo "Recentes" na sidebar.
