# 37B5 — Tenant Consistency Cleanup Report

> **Status:** concluído, **commitado e pushado** · build validado com variáveis **dummy temporárias** (sem `.env.local`, sem secrets reais).
> **Data:** 2026-06-08 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Resumo executivo
Limpeza de consistência visual do tenant: **Histórico** e **Configurações** re-skinados para Névoa/Geist (sem azul antigo), **dead code de sidebar removido** (`UnifiedSidebar.tsx`, `Sidebar.tsx`), **/sandbox protegido** atrás de `?internal=1` com aviso, e resíduos de azul tenant-visíveis corrigidos (`TermsAcceptanceModal`, `AvatarUpload`). A **superfície do tenant ficou 100% sem azul/JARVYS/smith-logo**. Nada de backend/chat/migrations tocado. `typecheck` + `build` verdes.

## 2. Arquivos alterados
**Modificados:**
- `app/dashboard/historico/page.tsx` — re-skin Névoa (lógica de fetch preservada).
- `app/dashboard/configuracoes/page.tsx` — de-blue dos botões + aba "Aparência" (tema + futuros); forms reais preservados.
- `app/sandbox/page.tsx` — gate `?internal=1` + aviso "interno" (agora `async`, `searchParams` como Promise — Next 15).
- `components/TermsAcceptanceModal.tsx` — ícone/botão azul → Névoa (lógica preservada).
- `components/AvatarUpload.tsx` — anel de foco/borda/badge azul + hex hardcoded → tokens Névoa.
**Removidos (dead code confirmado por busca):**
- `components/UnifiedSidebar.tsx`, `components/Sidebar.tsx` (nenhum import em `app/`, `components/`, `lib/`).
**Criado:** este relatório.

## 3. Histórico
`/dashboard/historico` agora: header com ícone + **"Histórico"** + descrição ("Conversas recentes e registros do AutoBrokers."), lista de cards Névoa (`border-border`, hover `border-primary/40`, card inteiro clicável), empty state elegante com CTA `Button` (Névoa) "Iniciar primeira conversa", contagem de mensagens em chip mono. **A lógica real foi preservada** (`fetch('/api/conversations?include_counts=true')`, `handleOpenConversation`). Removido todo azul (`bg-blue-600`, `hover:border-blue-500`, `group-hover:text-blue-600`). Sem API nova, sem schema.

## 4. Configurações
`/dashboard/configuracoes`: removido o azul dos 2 botões (`bg-blue-600…` → `Button` padrão Névoa). Forms reais **preservados** (Dados Pessoais + Senha e Segurança, com `handleUpdateProfile`/`handleChangePassword`). Adicionada 3ª aba **"Aparência"** (shell seguro): card de **Tema** com `ThemeToggle` real + cards "em breve" para **Preferências do AutoBrokers** e **Integrações futuras**. Loading `h-screen`→`h-full`. Sem salvamento novo/perigoso.

## 5. Sandbox
`/sandbox` **mantido** (útil para inspeção), mas **protegido**: sem `?internal=1` mostra apenas um aviso — *"Sandbox visual interno — não faz parte do produto final"* + link "Abrir mesmo assim". Com `?internal=1` mostra o conteúdo completo (B0–B3). Decisão: gate por query (simples, sem quebrar build; página vira dinâmica `ƒ`). Não usei pasta `_internal` para evitar risco de roteamento. Não removido (preserva inspeções futuras).

## 6. Dead code
Busca: `rg "UnifiedSidebar|<Sidebar[ />]|from '.*/Sidebar'"` → **zero referências externas** (só auto-referências internas). Confirmado obsoleto (substituído por `TenantNav`/`TenantSidebar` no 37B1). **Removidos** `components/UnifiedSidebar.tsx` e `components/Sidebar.tsx` — isso também eliminou usos antigos de `smith-logo`/azul que viviam neles. `typecheck`/`build` seguem verdes.

## 7. Branding/azul residual (classificação)
- **Tenant (corrigido agora):** ✅ **0 ocorrências** em `app/dashboard`, `components/layout`, `components/patterns`, `components/modules`, `TermsAcceptanceModal`, `AvatarUpload`.
- **Admin global (batch dedicado):** maior volume — `components/admin/AgentConfigModal.tsx` (37), `app/admin/*`, demais `components/admin/*`. **Não tocado** (não misturar admin com tenant).
- **Auth/landing (batch dedicado):** `app/register` (7), `app/login` (3), `app/forgot-password` (2), `app/pending-approval` (5), `app/no-company` (4).
- **Embed/widget (não mexer — risco de compatibilidade):** `app/embed/[agentId]` (2), `components/embed/LeadForm` (2).
- **UCP/técnico:** `components/ucp/ProductCarousel` (3), tabs de admin (MCP/UCP/Memory).
- **Primitivos compartilhados (técnico):** `components/ui/switch.tsx` (1), `components/ui/slider.tsx` (1) — estado `checked` azul; usados pelo admin; deixados para não alterar admin agora.

## 8. O que NÃO foi alterado
Motor do chat, `/api/chat/stream`, `app/dashboard/chat/page.tsx`, `app/dashboard/page.tsx`, backend, Supabase/migrations, APIs, billing/RAG/Qdrant/MinIO/Redis/Stripe/workers, `package.json`, bottom nav/AppShell, Admin global, auth/landing/embed/UCP, `ui/switch`/`ui/slider`. Sem acesso a pastas externas.

## 9. Checks executados
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ passou (após ajuste Next 15 do `searchParams`) |
| `npm run build` | ✅ passou (env dummy) |
| `git diff --check` | ✅ limpo (só `LF→CRLF`) |
| deadcode grep (`UnifiedSidebar`/`Sidebar`) | ✅ zero referências |
| branding/azul no tenant | ✅ **0 ocorrências** |
| `/dashboard/chat` alterado? | ✅ não |

## 10. Riscos/remanescentes
- Resíduos de azul/branding seguem em **admin/auth/landing/embed/UCP** + `ui/switch`/`ui/slider` (classificados na §7) — alvo de um batch dedicado de cleanup global (fora do tenant).
- `/sandbox` agora exige `?internal=1`; ainda é rota acessível (não autenticada) — para produção, considerar bloquear via middleware/env.
- `AvatarUpload`/`TermsAcceptanceModal` são compartilhados com admin; o re-skin Névoa também melhora o admin nesses pontos (sem efeito colateral negativo).
- Build local depende de env (dummy/real).

## 11. Próximo batch recomendado
- **37B6 (cleanup global de branding):** re-skin de auth (`login`/`register`/`forgot-password`/`pending-approval`/`no-company`) e admin para Névoa, trocar `smith-logo`/`agentsmith.ai` e neutralizar `ui/switch`/`ui/slider`. Mantém embed/widget intactos por compatibilidade. OU
- **38A (dados):** ADR + modelo de execuções para tornar o **Auxiliar de Resumo** funcional (liga o detalhe mock ao runtime), conforme UX-007.
Sugiro **38A** se o objetivo agora é valor funcional; **37B6** se o objetivo é polir 100% do app antes de produção.

## 12. Recomendação de deploy
**Recomendo deploy Web** para inspeção visual do tenant consistente (Histórico, Configurações com aba Aparência, módulos do 37B4) em desktop e mobile. **API não precisa de deploy** (nenhum backend alterado). Validar: `/dashboard/historico` (lista/empty, sem azul); `/dashboard/configuracoes` (3 abas, tema funcionando, botões Névoa); `/sandbox` mostra aviso interno sem `?internal=1`; bottom nav mobile e ausência de scroll horizontal.
