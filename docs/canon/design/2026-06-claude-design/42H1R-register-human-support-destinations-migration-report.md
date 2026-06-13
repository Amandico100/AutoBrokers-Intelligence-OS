# 42H1R — Register Human Support Destinations Migration Report

> **Status:** migration canônica registrada · **SQL NÃO executado** · Supabase NÃO chamado · nenhum runtime/UI/API/RAG/prompt/agente alterado · sem deploy.
> **Data:** 2026-06-13 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Por que a migration foi criada
O Architect criou e o Founder **executou manualmente no Supabase** a fundação SQL do **destino humano de suporte** (`public.human_support_destinations`, conforme o plano 42H1P). Para **evitar drift** entre o banco e o repositório, registramos essa fundação como uma **migration canônica idempotente** no controle de versão, fiel ao que foi aplicado.

## 2. O SQL já havia sido aplicado (estado verificado)
- Tabela `public.human_support_destinations` existe; **RLS habilitado**; **0 registros**.
- Índices presentes: `human_support_destinations_pkey`, `idx_human_support_destinations_company_id`, `idx_human_support_destinations_company_active`, `idx_human_support_destinations_company_primary`, `idx_human_support_destinations_company_priority`, `idx_human_support_destinations_tenant_connection_id`, `ux_human_support_destinations_one_primary_active`.
A migration deste batch **representa** esse estado; **não foi executada** aqui.

## 3. O que a migration contém
Arquivo: `backend/supabase/migrations/20260613_human_support_destinations_foundation.sql` (bloco `begin … commit`, idempotente):
- **Extensão:** `create extension if not exists pgcrypto`.
- **Tabela** `human_support_destinations` (`create table if not exists`): `id`, `company_id` (FK companies, cascade), `name`, `destination_type` (CHECK whatsapp_group/whatsapp_individual/email/internal_queue/webhook), `channel_provider` (CHECK zapi/evolution/meta_cloud/manual), `tenant_connection_id` (FK **Vault** tenant_connections, set null), `destination_ref`, `display_ref`, `is_primary`, `priority_order` (CHECK ≥0), `fallback_enabled`, `silence_minutes` (CHECK ≥0), `active_hours jsonb` (CHECK object), `escalation_rules jsonb` (CHECK array), `metadata jsonb` (CHECK object), `is_active`, `created_at`/`updated_at`.
- **Trigger** `trg_human_support_destinations_updated_at` (reusa `public.update_updated_at_column()`).
- **6 índices** + **índice único parcial** `ux_human_support_destinations_one_primary_active` (no máx. 1 primário ativo por corretora).
- **RLS** habilitado + **4 policies** (`service_role` full; `company_select`/`company_insert`/`company_update` via `users_v2.company_id`/`auth.uid()`).
- **Rollback manual** em comentário (não roda por padrão).

## 4. Conformidade com o plano 42H1P
- **Credenciais/tokens FORA da tabela** — só `destination_ref`/`display_ref` (segredo continua no Vault `tenant_connections`, referenciado por `tenant_connection_id`).
- Config oficial morará em **Personalização → Corretora → Suporte humano**; **API operacional futura** em `/api/attendance/support-destinations` (batches 42H2/H3). Esta migration é apenas a fundação de dados.

## 5. Idempotência
`create table if not exists`, `create extension if not exists`, trigger `drop … if exists` + `create`, índices `create index if not exists` (incl. único parcial), RLS `enable` + `drop policy if exists` + `create policy`, tudo em `begin … commit`. Rodar novamente **não** causa erro nem duplicação. **Sem seed** (nenhum destino de teste).

## 6. Confirmações
- **Não executei SQL** (apenas escrevi o arquivo `.sql`).
- **Não chamei o Supabase** (nenhuma conexão/MCP/CLI).
- **Não alterei** runtime/UI/API/RAG/prompts/agentes/backend Python; `schema_completo.sql` apenas **lido**.
- **Não criei** API/UI/seed/envio WhatsApp/handoff_dossier/dispatch.
- **Não alterei** `attendance_cases`, `corridor_runs`, `dispatch_packets`, `tenant_connections`, `approval_requests`, `vault_audit_log`, `integrations`, `companies`, `users_v2`, `agents`.
- Sem segredos/PII.

## 7. Checks
| Check | Resultado |
|---|---|
| `git diff --check` | ✅ limpo |
| `git status` mostra só os 2 arquivos | ✅ (migration + report) |
| alteração em `app/` / `backend/app/` / `lib/` / `schema_completo.sql` | ✅ nenhuma |
| segredo/PII no diff | ✅ nenhum |
| SQL executado / Supabase chamado | ✅ não |

## 8. Próximos passos recomendados
1. **42H2** — API de destinos (`GET/POST/PATCH /api/attendance/support-destinations`), padrão da 42B5A (Iron Session + `users_v2.company_id` + service role).
2. **42H3** — UI em **Personalização → Corretora → Suporte humano** (lista/adicionar/primário/fallback/silêncio/ativo; testar em dry-run), reusando padrões de conectores.
3. **42H4** — gerador de `handoff_dossier` (read-only do caso).
4. **42H5** — copiar/dry-run de handoff no detalhe do caso (HITL via `approval_requests`).
5. Depois: **42B5B** (Corridor Runtime Step Engine) e **42B6** (Dispatch + WhatsApp dry-run/HITL).
> Em rebuild fresco do banco, garantir que **39A1 (Vault)** rode antes desta migration (a FK de `tenant_connections`).
