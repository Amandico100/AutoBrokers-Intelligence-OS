# 42B3R — Register Attendance/Corridor DB Foundation Migration

> **Status:** migration canônica registrada · **SQL NÃO executado** · Supabase NÃO chamado · nenhum código/runtime/RAG/prompt alterado · sem deploy.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Por que esta migration foi criada agora
O Architect criou e o Founder **executou manualmente no Supabase** o SQL controlado **42B3**, criando a fundação de Atendimento/Corredores (4 tabelas + RLS + índices + triggers + 2 seeds globais). Para **evitar drift** entre o Supabase e o repositório, registramos essa fundação como uma **migration canônica idempotente** no controle de versão, fiel ao que foi aplicado.

## 2. O SQL já havia sido aplicado (fonte autoritativa)
A fonte autoritativa é **`docs/sql/42B3-attendance-corridor-mvp-foundation.sql`** (adicionada ao repo pelo Founder, commit `ee76872`), que contém: SEÇÃO 0 (preflight read-only), **SEÇÃO 1 (DDL + RLS + índices + seeds)** e SEÇÃO 2 (verificação) + rollback.

Resultado verificado no Supabase:
- Família: `allianz_residential_assistance` / subcorridor `null` / "Allianz Residencial — Assistência Residencial" / readiness `mapped_from_real_conversations` / **11 phases, 4 guardrails, 0 required_slots, 0 golden_tests**.
- Eletricista: `allianz_residential_assistance` / `electrician` / "Allianz Residencial — Eletricista" / readiness `ready_for_dry_run` / **12 phases, 8 required_slots, 6 guardrails, 10 golden_tests**.

## 3. A migration espelha a fonte autoritativa (fidelidade verificada)
A migration `backend/supabase/migrations/20260612_attendance_corridor_mvp_foundation.sql` contém a **SEÇÃO 1 da fonte autoritativa** (bloco `begin … commit`), **byte-idêntica** — comparação programática confirmou que o DDL/RLS/índices/seeds são iguais; a **única** diferença são **2 linhas de comentário** que anotei (`(upsert idempotente)`) nos cabeçalhos dos seeds 1.7/1.8. Zero drift funcional.

> Importante: minha primeira versão reconstruída (a partir do 42B3P) divergia da aplicada (vocabulário de status/phase, `line_kind` em PT, guardrails como strings). Ao descobrir a fonte autoritativa no repo, **substituí** a migration pelo espelho fiel do SQL real — exatamente para não introduzir drift.

## 4. O que a migration contém (igual ao aplicado)
- **Extension/função:** `create extension if not exists pgcrypto` + `create or replace function public.update_updated_at_column()`.
- **4 tabelas** (`create table if not exists`): `attendance_cases`, `corridor_templates`, `corridor_runs`, `dispatch_packets` — com os CHECKs reais (ex.: `attendance_cases.status` 14 valores; `corridor_runs.phase` em inglês `intake/identify_insured/…`; `dispatch_packets.status` `draft/missing_data/ready_for_approval/…`; `dispatch_packets.provider` inclui browserbase/stagehand/skyvern; `corridor_templates` com CHECK de coerência `scope×company_id`). FK real `dispatch_packets.approval_request_id → approval_requests(id)`.
- **Triggers** `updated_at` nas 4 tabelas.
- **Índices:** company_id, status, conversation_id, assigned_agent_id, corridor_key/subcorridor_key, case_id, corridor_template_id, approval_request_id, created_at/updated_at + **índice único** `corridor_templates_unique_key_idx` em `(coalesce(company_id, global-uuid), corridor_key, coalesce(subcorridor_key,'__family__'))`.
- **RLS + policies** (service_role full + company via `users_v2.company_id`/`auth.uid()`; `corridor_templates` globais legíveis por todos; insert/update tenant-only para templates de tenant).
- **Seeds globais (upsert idempotente** `with updated as (update … returning) insert … where not exists (select 1 from updated)`**):** família + eletricista, com `line_kind='residential'`, `macro_service='residential_assistance'`, phases em inglês, **guardrails como objetos** `{key,severity,rule}`, required_slots ricos (8) e golden_tests `GOLD-ELEC-001..010`. **Contagens batem** com o verificado no Supabase. Sem PII.

## 5. Idempotência
- Tabelas: `create table if not exists` → no-op se já existem (caso real).
- Função `create or replace`; triggers `drop … if exists` + `create`; índices `create index if not exists`; RLS `enable` + `drop policy if exists` + `create policy`.
- FK de `approval_requests`: inline (a tabela já existe via 39A1).
- Seeds: `with updated as (update … returning) insert … where not exists (…)` → **upsert** (atualiza se existe, insere se não). Tudo dentro de `begin … commit`.
> Rodar novamente **não** causa erro nem duplicação.

## 6. Confirmações
- **Não executei SQL** (apenas escrevi o arquivo `.sql` no repo).
- **Não chamei o Supabase** (nenhuma conexão/MCP/CLI).
- **Não alterei runtime/código/RAG/prompts** — nada em `app/`, `backend/app/`, `lib/`, `context_package`, agentes; `schema_completo.sql` apenas **lido**.
- **Sem segredos/PII** (seeds curados; documento como referência; telefone/dados de cliente são runtime, não seed).
- **Não alterei** `conversations`, `messages`, `agents`, `approval_requests`, `vault_audit_log`, `documents`, `integrations`. **Não criei** `attendance_messages`, `corridor_slots`, `corridor_phases`, `browser_sessions`, `infocap_credentials`, tabelas de web search/autoevolução.

## 7. Tabelas registradas (resumo)
| Tabela | Papel | RLS | Seeds |
|---|---|---|---|
| `attendance_cases` | estado central do caso | company-scoped (select/insert/update) | — |
| `corridor_templates` | registry de corredor/subcorredor (global/tenant) | global read + tenant write | família + eletricista |
| `corridor_runs` | instância do corredor (fase + slots jsonb) | company-scoped | — |
| `dispatch_packets` | pacote de acionamento + HITL (→ `approval_requests`) | company-scoped | — |

## 8. Checks
| Check | Resultado |
|---|---|
| `git diff --check` | ✅ limpo |
| `git status` mostra só os 2 arquivos (migration + report) | ✅ |
| migration == fonte autoritativa (Seção 1) | ✅ byte-idêntico (só 2 comentários a mais) |
| seeds jsonb parse + contagens (11/4 família; 12/8/6/10 eletricista) | ✅ batem |
| alteração em `app/` / `backend/app/` / `lib/` / `schema_completo.sql` | ✅ nenhuma |
| segredo/PII no diff | ✅ nenhum |
| SQL executado / Supabase chamado | ✅ não |

## 9. Próximos passos recomendados
1. **42A4** — Attendance Boundary Blueprint v1 (papel `attendance` separado do Core).
2. **42B5** — Runtime assistido do corredor (Attendance agent + LangGraph + Context Package; HITL via `approval_requests`; lê `corridor_templates`/`corridor_runs`, grava `dispatch_packets`).
3. **42B4** — UI Fila/Casos/Conversas MVP (reusa `conversations`/`messages` + lê `attendance_cases`/`corridor_runs`).
4. **42B7** — Golden tests do Eletricista (os 10 `GOLD-ELEC-*` já seedados viram base de eval).
5. Rodar **CORE-REGRESSION-001** a cada batch que tocar runtime.
> Em rebuild fresco do banco, rodar **39A1 (Vault)** antes desta migration (a FK de `approval_requests` exige a tabela). A fonte completa com preflight/verificação/rollback é `docs/sql/42B3-attendance-corridor-mvp-foundation.sql`.
