# 37B4 — Module Shells Report

> **Status:** concluído, **commitado e pushado** · build validado com variáveis **dummy temporárias** (sem `.env.local`, sem secrets reais).
> **Data:** 2026-06-07 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Resumo executivo
Os módulos do tenant (Atendimentos, Auxiliares, Personalização) agora são **páginas visuais organizadas** sob `/dashboard/*`, reutilizando os padrões-mestre do 37B3 (Galeria, Detalhe, Modal de Permissão, StatusPill). Tudo **visual/mock**, sem backend, sem migrations, sem execução real. Criei 2 helpers de módulo + 1 arquivo de mocks para manter as ~20 páginas enxutas. Chat (`/dashboard`, `/dashboard/chat`) intacto. `typecheck` + `build` (92/92 páginas) verdes; sem rotas fora de `/dashboard`.

## 2. Arquivos alterados
**Criados — componentes/mocks:**
- `components/modules/ModuleIndex.tsx` — central de módulo (header + grade de áreas + atalho ao AutoBrokers).
- `components/modules/ModulePlaceholder.tsx` — shell de subpágina (DetailHeader + estado "em construção").
- `lib/mock/tenant-modules.ts` — dados mock (áreas, galerias, seguradoras, permissões). Sem PII, sem chamadas reais.

**Criados — rotas (15 novas):** ver §3.
**Modificados:** `lib/icons.ts` (+5 ícones: fila, casos, conversas, corretora, galeria), `app/dashboard/atendimentos/page.tsx`, `app/dashboard/auxiliares/page.tsx`, `app/dashboard/personalizacao/page.tsx` (os 3 índices, antes shells simples do 37B1).
**Criado — relatório:** este arquivo.

## 3. Rotas criadas/alteradas (todas sob /dashboard)
- **Atendimentos:** `/dashboard/atendimentos` (central), `/fila`, `/casos`, `/conversas`, `/segurados`.
- **Auxiliares:** `/dashboard/auxiliares` (central + destaque), `/meus`, `/galeria`, `/execucoes`, `/galeria/resumo-atendimentos` (detalhe).
- **Personalização:** `/dashboard/personalizacao` (central), `/conectores`, `/seguradoras`, `/conhecimento`, `/corretora`, `/equipe`.
- ✅ Nenhuma rota na raiz (`app/atendimentos`, `app/auxiliares`, `app/personalizacao` **não existem**).

## 4. Atendimentos
Central limpa (`ModuleIndex`) com cards para Fila, Casos, Conversas e Segurados (status "Em breve") + atalho "Abrir o AutoBrokers". Subpáginas são shells elegantes (`ModulePlaceholder`): breadcrumb de volta, descrição e estado "Nenhuma ação real é executada ainda". Sem métricas inventadas, sem cópia do dashboard antigo.

## 5. Auxiliares
Central estilo Claude Routines: cards de **Meus Auxiliares / Galeria / Execuções** + bloco "Primeiro auxiliar" destacando **Resumo de Atendimentos**. `/galeria` usa `GalleryGrid` com os 4 modelos (Resumo "Pronto para ativar" navegável; demais "Em breve" desabilitados). `/galeria/resumo-atendimentos` é a **página de detalhe** (`DetailShell` + abas Visão geral/Como funciona/Permissões/Execuções + bloco lateral) com **"Ativar com segurança" → `PermissionModal`** (permissões mock + HITL). `/meus` mostra empty state com CTA "Ver galeria". Sem execução real, sem scheduler, sem criação por prompt, sem agentes no banco.

## 6. Personalização
Central (`ModuleIndex`) com Conectores, Seguradoras, Conhecimento, Corretora, Equipe. **Conectores** (`/conectores`) usa `GalleryGrid` (WhatsApp, Google Drive, Base de Dados, n8n, Portal Seguradora) com **"Conectar" → `PermissionModal`** (mock, linguagem de corretora, HITL). **Seguradoras** (`/seguradoras`) usa `GalleryGrid` (Allianz, Porto, Tokio, Bradesco, HDI) com status mock (Pronta/Em configuração/Portal pendente) — sem credenciais/portal/corredores reais. Conhecimento/Corretora/Equipe são shells (`ModulePlaceholder`). Decisão de produto respeitada: Seguradora é entidade irmã de Conectores.

## 7. Uso dos padrões-mestre do 37B3
- **GalleryGrid/GalleryCard:** auxiliares (galeria + destaque), conectores, seguradoras, e as áreas das centrais.
- **GalleryFilters:** disponível (usado no /sandbox); nos módulos as listas mock são curtas, então não adicionei filtro ainda (documentado).
- **DetailShell/DetailHeader/DetailSection:** detalhe do Resumo + headers de subpáginas (via `ModulePlaceholder`).
- **PermissionModal/PermissionList:** ativar Resumo + conectar conector.
- **StatusPill:** status em todos os cards.
- Reuso de `Button`/`Dialog`/`Tabs` ShadCN, `Icon`/`lib/icons`, `cn`. Nada recriado.

## 8. O que NÃO foi alterado
`app/dashboard/chat/page.tsx`, `app/dashboard/page.tsx`, `components/InputArea/*`, `app/layout.tsx`, AppShell/sidebar/bottom-nav, backend, Supabase/migrations, APIs, `package.json`, Admin, `/sandbox`. Sem lógica real de Auxiliares/execução/scheduler/integração. Sem acesso a pastas externas.

## 9. Checks executados
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ passou |
| `npm run build` | ✅ passou (env dummy; `✓ 92/92` páginas estáticas, incl. todas as novas rotas) |
| `git diff --check` | ✅ limpo (só `LF→CRLF`) |
| rotas na raiz | ✅ inexistentes (só `/dashboard/*`) |
| scan azul/branding (módulos novos) | ✅ **sem ocorrências** |
| `/dashboard/chat` alterado? | ✅ não |

## 10. Branding/resíduos encontrados
- ✅ **Módulos novos limpos** (tokens Névoa; sem azul/JARVYS/smith-logo).
- ⚠️ Resíduos **pré-existentes** (cleanup futuro): azul em `/dashboard/historico` e `/dashboard/configuracoes`, `TermsAcceptanceModal`, `ui/switch`/`ui/slider`, `AvatarUpload`, auth/landing/admin/embed/UCP; dead code `UnifiedSidebar.tsx`/`Sidebar.tsx`.

## 11. Riscos/remanescentes
- Tudo é **mock**: a ligação com dados reais (RAG, agents, casos, conexões, seguradoras) vem nos batches de dados/runtime (com Vault/ADRs).
- Páginas com modal (`conectores`, `resumo-atendimentos`) são `'use client'` (sem `metadata`); as demais são server com `metadata`.
- `GalleryFilters` ainda não aplicado nos módulos (listas curtas) — fácil de adicionar quando houver volume.
- `/historico` e `/configuracoes` ainda com visual antigo/azul (fora do escopo); `/sandbox` segue rota pública interna.
- Build local depende de env (dummy/real).

## 12. Próximo batch recomendado
- **37B5 (cleanup leve):** re-skin de `/dashboard/historico` e `/dashboard/configuracoes` para Névoa (tirar azul), remover dead code `UnifiedSidebar`/`Sidebar`, e trocar `smith-logo` em auth pages — deixando o tenant 100% consistente. OU
- **38A (dados):** ADR + modelo de execuções para tornar o **Auxiliar de Resumo** funcional (ligando o detalhe mock ao runtime), conforme UX-007.
Sugiro **37B5** (consistência visual completa do tenant) antes de entrar em dados.

## 13. Recomendação de deploy
**Recomendo deploy Web** para inspeção visual dos módulos reais (Atendimentos, Auxiliares com detalhe + modal, Personalização com conectores/seguradoras), desktop e mobile. **API não precisa de deploy** (nenhum backend alterado). Validar: navegação pelos 4 pilares, galeria de auxiliares → detalhe do Resumo → "Ativar" abre o modal; Personalização → Conectores → "Conectar" abre o modal; bottom nav mobile e ausência de scroll horizontal. Lembrete: `/sandbox` é rota pública interna (proteger/remover antes de produção).
