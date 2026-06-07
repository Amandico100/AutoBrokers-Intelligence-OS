# 37B2 — Chat-First Adapter Report

> **Status:** concluído, **commitado e pushado** · build validado com variáveis **dummy temporárias** (processo único, sem `.env.local`, sem secrets reais).
> **Data:** 2026-06-07 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Resumo executivo
A tela principal do AutoBrokers em `/dashboard` virou uma experiência **chat-first premium** (estilo ChatGPT/Claude/Linear) **sem reescrever o motor**. Empty state centrado com BrandMark + "Como posso ajudar sua corretora hoje?" + composer + 2 atalhos; header azul antigo removido; composer, bolhas e sub-componentes re-skinados para Névoa. **Toda a lógica foi preservada** (agentes, conversas, streaming SSE, realtime, voz, histórico, auth, company/user). `typecheck` + `build` verdes.

## 2. Arquivos alterados
**Modificados:**
- `app/dashboard/chat/page.tsx` — return reestruturado (header removido; empty state chat-first; conversa ativa com composer no rodapé); `InputArea` extraído como `const composer` reutilizado nos 2 estados; imports limpos (Bot/PlusCircle/Badge/Select/EmptyState removidos). **Nenhuma mudança em estados/handlers/efeitos/stream.**
- `components/ui/animated-ai-chat.tsx` — composer: azul → `primary`/`surface` (send, anexar, voz, web-search, seletor de agente, ring/glow). Só className.
- `components/MessageBubble.tsx` — bolha do usuário `bg-blue-600` → `bg-primary text-primary-foreground`; loader UCP azul → primary.
- `components/InputArea/AudioPreview.tsx`, `ImagePreview.tsx`, `StatusIndicator.tsx` — azul → `primary` (mantido vermelho destrutivo).

**Criados:**
- `components/chat/ChatWelcome.tsx` — BrandMark + frase principal + subfrase.
- `components/chat/ChatShortcutCards.tsx` — 2 atalhos discretos (pílulas).
- `docs/canon/design/2026-06-claude-design/37B2-report.md`.

## 3. Como o chat funcionava antes
`/dashboard` → re-exporta `ChatPage` (`/dashboard/chat`). Estrutura: header `h-16` azul ("Conversando com [agente]" + Novo Chat) → área de mensagens (mostrava `EmptyState` quando vazio) → `InputArea` no rodapé. Toda a lógica (fetch agentes/company, conversas, `POST /api/chat/stream` com parse SSE, realtime Supabase, voz n8n) vive no componente.

## 4. Como o chat-first foi adaptado
- **Header removido** (era o principal resíduo azul). Nova conversa segue acessível pela sidebar/topbar (AppShell, 37B1).
- **Empty state** (`messages.length === 0`): bloco centrado vertical/horizontal com `ChatWelcome` + composer + `ChatShortcutCards`.
- **Conversa ativa**: lista de `MessageBubble` (scroll, `max-w-3xl`) + composer fixo no rodapé com fade.
- Visual alinhado ao AppShell e à Névoa; sem cards de KPI, sem métricas, sem dashboard.

## 5. Como a lógica de streaming foi preservada
Nenhuma função/efeito/estado foi alterado: `handleSendMessage` (fetch `/api/chat/stream`, leitura do `ReadableStream`, parse `data:`/`[DONE]`/UCP), `handleSendVoice` (n8n), `loadConversation`, `ensureConversation`, `saveMessage`, realtime, auto-scroll (`messagesEndRef`) — **idênticos**. O `InputArea` é o **mesmo componente**, com **os mesmos props**, apenas referenciado via `const composer` (renderizado no centro quando vazio, no rodapé quando há mensagens). Backend, `/api/chat/stream` e tipos intactos.

## 6. Empty state implementado
`ChatWelcome`: BrandMark (40px) + **"Como posso ajudar sua corretora hoje?"** + subfrase ("Pergunte sobre atendimentos, seguradoras e documentos — ou crie um auxiliar…"). Composer logo abaixo. `ChatShortcutCards` abaixo do composer.

## 7. Composer/Input adaptado
`AnimatedAIChat` (dentro do `InputArea`): container `bg-surface` + `border-border` + `shadow-lg`; botão enviar `bg-primary text-primary-foreground`; anexar/voz/web-search e seletor de agente em `primary`; gravação mantém vermelho. Funcionalidades preservadas (texto, voz, imagem/paste, web-search, seletor de agente). Sub-previews (áudio/imagem/status) em Névoa.

## 8. Atalhos implementados
Exatamente 2, discretos (pílulas, sem cards grandes/cor chamativa):
- **Ver atendimentos** → `/dashboard/atendimentos`
- **Novo auxiliar** → `/dashboard/auxiliares`
Apenas navegação (sem modal, sem fluxo de criação).

## 9. Mobile/safe-area
A `TenantBottomNav` (37B1) fica **no fluxo** abaixo do `main`, então o composer (último item do `main`) **nunca fica atrás da bottom nav**. Empty state usa `min-h-full justify-center` com scroll; mensagens com `max-w-3xl` e padding. Sem overflow horizontal; sem header gigante; sem sidebar duplicada.

## 10. Recentes/histórico — **deixado para depois (documentado)**
Reintroduzir "Recentes" clicável na sidebar exigiria acoplar a sidebar (nível de layout) ao estado do chat (sessionId), o que pede **lifting de estado** ou **`?session=` + `useSearchParams`/Suspense** no chat — risco real ao motor que este batch deve preservar. Conforme a regra do prompt ("se ficar complexo, não implemente agora; documente"), **não implementei**. Acesso ao histórico permanece via **Histórico** (`/dashboard/historico`) e "Nova conversa" (sidebar/topbar). Recomendo um batch dedicado (ex.: 37B3.x) com `?session=` + Suspense.

## 11. O que NÃO foi alterado
Backend, Supabase/migrations, `/api/chat/stream` e demais APIs, `package.json`, EasyPanel/deploy, Admin, `app/layout.tsx` raiz, `app/dashboard/layout.tsx` (AppShell do 37B1), `app/dashboard/page.tsx` (re-export). Lógica de chat 100% preservada. `EmptyState.tsx` deixou de ser usado pelo chat (substituído por `ChatWelcome`) — permanece no repo como dead code (remover em cleanup).

## 12. Branding/azul residual encontrado
- ✅ **Experiência de chat tenant (/dashboard) sem azul**: `chat/page.tsx`, `animated-ai-chat.tsx`, `MessageBubble.tsx`, sub-previews — todos Névoa.
- ⚠️ Tenant não-chat (futuro cleanup): botões `bg-blue-600` em `/dashboard/historico` e `/dashboard/configuracoes`; `TermsAcceptanceModal` (botão azul, modal raro).
- ⚠️ Dead code: `UnifiedSidebar.tsx`, `Sidebar.tsx` (azul + `smith-logo`, não renderizados).
- ⚠️ Fora do tenant: auth/landing (`HeroSection`, login/register…), admin, embed, UCP, primitivos `ui/switch`/`ui/slider`, `AvatarUpload`.
- ✅ Sem `JARVYS`/`Agent Smith` no código.

## 13. Checks executados e resultado
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ passou |
| `npm run build` | ✅ passou (env dummy temporária; `/dashboard` e `/dashboard/chat` geradas) |
| `git diff --check` | ✅ limpo (só avisos benignos `LF→CRLF`) |
| scan azul/branding | ✅ chat tenant sem azul; resíduos não-chat listados em §12 |

## 14. Riscos/remanescentes
- Transição empty→conversa **remonta** o `InputArea` (muda de posição). Benigno: o texto já é limpo no envio; sem perda relevante de estado.
- Seletor de agente segue visível no composer (UX-001 prefere ocultar para usuário comum) — decisão de produto para um batch futuro; mantido para não quebrar o fluxo.
- "Recentes" pendente (ver §10).
- Resíduos azuis não-chat e dead code (ver §12) → batch de cleanup.

## 15. Próximo batch recomendado
**37B3 — Padrões-mestre (Galeria, Detalhe, Modal de permissão)** como componentes em sandbox/mock (Leva 2), reaproveitando tokens/ícones; OU um **37B2.1** curto para "Recentes" (com `?session=`+Suspense) e ocultar o seletor de agente. Sugiro 37B3 (padrões) para destravar os shells de módulo (B4) e deixar Recentes/seletor para um ajuste focado.
