# 41A — Admin Global · Fábrica de Auxiliares Report

> **Status:** concluído, **commitado e pushado** · typecheck/build verdes · **só Web/Next** · **sem SQL/schema/migration** · sem motor de execução novo.
> **Data:** 2026-06-08 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Resumo executivo
Criada a fundação da **Fábrica de Auxiliares** no Admin Global: uma área `/admin/auxiliares` (master-only) onde o Admin **lista, cria, edita, ativa/desativa** templates globais (`auxiliary_templates`) e **instala** Auxiliares em corretoras (`tenant_auxiliaries`), com **dedupe** e visão de instalações. Para não depender de SQL manual e **sem alterar schema**, o backend é **resiliente ao schema**: descobre as colunas reais em runtime e grava apenas a interseção. Não cria motor de execução nem novos Auxiliares de negócio — apenas a gestão.

## 2. O que foi auditado no Admin (FASE 1)
- **Auth:** sessão admin via cookie `smith_admin_session` (`AdminSessionData{adminId, role:'master'|'company_admin', companyId}`). **Rotas `/api/admin/*` guardam por presença do cookie** (ex.: `app/api/admin/companies/route.ts`). Páginas vivem sob `app/admin/*`; `app/admin/layout.tsx` faz o guard de role (redireciona `company_admin` de rotas master-only) via `useAdminRole`.
- **Padrão visual:** páginas admin são client components em Tailwind puro (tabela + modal overlay + `Button/Input/Switch` + ícones lucide) — **não** usam Névoa/DetailShell. Segui esse padrão.
- **APIs reutilizáveis:** `GET /api/admin/companies` (lista corretoras) — reusado no modal de instalação.
- **Schema (achado decisivo):** o DDL de `auxiliary_templates`/`tenant_auxiliaries` **não está no repo** (criado manualmente no 38A1; o 38A0 era *proposta* e diverge do real — ex.: a tabela usa `is_active`, não o proposto `is_published`). Logo, **as colunas "ricas"** do formulário (`execution_mode`, `system_prompt`, `requires_human_approval`, etc.) **não são garantidas**. Como não posso alterar schema, adotei a estratégia de **probe de colunas** (sem STOP).

## 3. Arquivos alterados
**Novos:** `lib/admin/factory.ts`; `app/api/admin/auxiliaries/templates/route.ts`; `.../templates/[templateId]/route.ts`; `.../[templateId]/install/route.ts`; `.../[templateId]/installations/route.ts`; `app/admin/auxiliares/page.tsx`.
**Editado:** `app/admin/layout.tsx` (nav "Auxiliares Globais" no menu master + `/admin/auxiliares` em `masterOnlyRoutes`).
**Docs:** este relatório.

## 4. Rotas/páginas criadas
- **Página:** `/admin/auxiliares` ("Auxiliares Globais") — tabela de templates + modais de criar/editar, instalar e ver instalações.
- **Nav:** item no menu master; bloqueado para `company_admin` (redirect).

## 5. APIs criadas
| Método/Rota | Função |
|---|---|
| `GET /api/admin/auxiliaries/templates` | lista todos os templates (ativos+inativos) |
| `POST /api/admin/auxiliaries/templates` | cria template (slug único, JSON validado, probe de colunas) |
| `GET /api/admin/auxiliaries/templates/[id]` | um template |
| `PATCH /api/admin/auxiliaries/templates/[id]` | atualiza textos/flags/JSON (**slug imutável**) |
| `POST /api/admin/auxiliaries/templates/[id]/install` | instala em corretora (dedupe por company+slug) |
| `GET /api/admin/auxiliaries/templates/[id]/installations` | corretoras com o template (com nome) |
| (reuso) `GET /api/admin/companies` | lista de corretoras no modal |

## 6. Como o Admin Guard foi aplicado
Todas as novas rotas chamam `hasAdminCookie()` (presença de `smith_admin_session`) → 401 se ausente, **exatamente** o padrão das rotas admin existentes. Service role só no servidor (`lib/admin/factory.ts` é server-only — importa `next/headers`). A página `/admin/auxiliares` **não** acessa service role (faz `fetch` às APIs). `/admin/auxiliares` foi adicionado a `masterOnlyRoutes` (company_admin é redirecionado).

## 7. Como criar template global
Modal "Novo template": name, slug, categoria, descrições, ícone, status, `execution_mode`, `trigger_type`, `requires_human_approval`, `uses_external_actions`, **Ativo**, `system_prompt`, e 4 JSONs (`default_config`/`permissions`/`input_schema`/`output_schema`). Validações: name + slug obrigatórios, **slug formato kebab + único**, JSON válido. **Defaults seguros:** `execution_mode='manual'`, `trigger_type='manual'`, `requires_human_approval=true`, `uses_external_actions=false`, `is_active=true`, `version=1`, JSONs `{}`.

## 8. Como instalar em corretora
Modal "Instalar": seleciona corretora (de `/api/admin/companies`), status (active/paused). Cria `tenant_auxiliaries` com `{company_id, template_id, slug, name/display_name, status, config, permissions}` — **só as colunas que existem** (probe). Idempotente: se já existir `(company_id, slug)`, retorna "já instalado" sem duplicar.

## 9. Como evita duplicidade
Antes do insert, consulta `tenant_auxiliaries` por `company_id + slug`; se houver, devolve `{already:true}` e a UI mostra "já estava instalado". Slug de template é **único** (checado no create) e **imutável** (PATCH ignora slug) — evita quebrar instalações por slug.

## 10. Como se conecta à Galeria/Meus/Execuções (tenant)
- **Galeria** (`/dashboard/auxiliares/galeria`) lê `auxiliary_templates` ativos → o template criado/ativado aparece (a Galeria já faz merge por slug; templates novos sem página de detalhe aparecem como card sem link/“em preparação”).
- **Meus Auxiliares** lê `tenant_auxiliaries` → a instalação aparece (status do install).
- **Execuções** continua por `auxiliary_runs`; um template **sem executor** não gera runs (esperado — este batch não cria executor genérico).

## 11. O que NÃO foi implementado
Executor genérico por prompt, scheduler, criação por corretora, marketplace, avaliações, cobrança por auxiliar, envio real, RAG, corredores, Atendimento, portais, MCP real. **Sem SQL/migration/schema.** Sem Python.

## 12. Checks executados
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ passou |
| `npm run build` (env dummy) | ✅ passou (rotas `/admin/auxiliares` + APIs registradas) |
| `git diff --check` | ✅ limpo |
| branding scan (arquivos novos) | ✅ sem `blue-600`/branding errado (uso de tokens neutros/emerald) |
| service_role no client | ✅ ausente em `app/admin/auxiliares/page.tsx` (só server-side) |
| token/secret como campo de Auxiliar | ✅ ausente |

## 13. Como testar manualmente (pós-deploy Web)
1. `/admin/auxiliares` (logado como master) → ver Resumo de Atendimentos e Follow-up WhatsApp.
2. **Novo template:** name "TESTE Admin Auxiliar", slug `teste-admin-auxiliar`, categoria "Teste", `execution_mode=manual`, `trigger_type=manual` → Criar.
3. **Instalar** na RAFAEL SEGUROS (status active).
4. `/dashboard/auxiliares/meus` → ver o Auxiliar instalado.
5. Voltar ao Admin → **Power** (desativar/ativar) e **Building2** (ver instalações).
6. Tentar instalar de novo na mesma corretora → "já estava instalado" (sem duplicar).
7. Não executar o template de teste (sem executor). typecheck/build OK.

## 14. Riscos/remanescentes
- **Probe de colunas:** se `auxiliary_templates`/`tenant_auxiliaries` estiverem **vazias**, o probe cai para o conjunto mínimo (`slug,name,description,category,is_active` / `company_id,template_id,slug,status`) — campos ricos só persistem se a coluna existir. Hoje há linhas, então o probe reflete o schema real. Para persistir todos os campos ricos com garantia, um batch de **ampliação de schema** (SQL revisado pelo Architect) é o caminho — fora deste escopo.
- **Guard por presença de cookie** (padrão existente). Hardening futuro: validar `role==='master'` no server e expirar sessão.
- Templates novos **sem executor** aparecem na Galeria sem ação real — esperado; a fábrica gere catálogo/instalação, não execução.

## 15. Próximo batch recomendado
- **Deploy Web** (só Next mudou) + teste manual (§13).
- **41B — Admin Global / Catálogo de Conectores** (mesma fábrica para `connector_templates`).
- Depois: **41C — Conhecimento/RAG**, **40A — WhatsApp inbound**, **42A — Atendimento/corredores**, **43A — primeiro corredor assistido**.
- (Opcional) **Ampliação de schema de `auxiliary_templates`** (Architect) para persistir `execution_mode`/`system_prompt`/schemas de forma garantida.
