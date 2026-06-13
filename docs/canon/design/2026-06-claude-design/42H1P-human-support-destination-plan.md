# 42H1P — Human Support Destination Plan (READ-ONLY)

> **Status:** plano técnico/produto · **READ-ONLY** · **NÃO é SQL/código/UI/API/runtime** · nenhum banco/Supabase/WhatsApp alterado · sem deploy.
> **Data:** 2026-06-13 · **Modelo:** Claude Opus 4.8 · **Branch:** main
> **Aguarda:** revisão do Architect/Founder antes de qualquer DDL/código.

## 0. Sumário executivo
Quando o Attendance Agent **não conseguir resolver** (dúvida, falha, baixa confiança, sinistro complexo, falta de corredor/fonte, risco físico/jurídico, canal indisponível, erro de execução), ele deve **montar um dossiê** e **transferir para um destino humano configurado pela corretora**. Hoje a UI já mostra "Destino humano: ainda não conectado neste MVP". Este batch **planeja** a fundação (sem implementar): onde mora, modelo de dados mínimo, conexão com casos/dossiê, estratégia WhatsApp por fases, multi-tenant/segurança, UI/API futuras e a sequência de batches. **Nada de envio real ainda.**

## 1. Onde esta configuração deve morar — **DECISÃO FIXA**
- **Local oficial (fonte da verdade):** **Personalização → Corretora → Suporte humano** (`app/dashboard/personalizacao/corretora`). É **configuração da corretora/tenant**.
- **Atalho futuro opcional:** **Atendimentos → Configurações → Suporte humano** — apenas um atalho de conveniência; a **fonte oficial** continua sendo Personalização → Corretora.
- **Não** é: configuração do **Core chat**; **não** é hardcoded no agente; **não** é configuração por caso.
- **Reuso de UX:** seguir os padrões já funcionais de `personalizacao/conectores` (lista + adicionar + status + aprovações/auditoria).

Por quê: o destino humano é um recurso **da corretora** (reutilizável por todo o Atendimento), análogo a um conector — não pertence a um caso nem ao agente. A API e o uso operacional vivem no módulo Atendimento (ver §9), mas a **configuração** mora na Corretora.

## 2. Modelo de dados mínimo (futuro SQL — não criar agora)
Tabela recomendada: **`public.human_support_destinations`**.

| Campo | Tipo | Nota |
|---|---|---|
| `id` | uuid PK | |
| `company_id` | uuid NOT NULL → companies | isolamento tenant |
| `name` | text NOT NULL | nome amigável ("Plantão Sinistros", "Grupo Suporte") |
| `destination_type` | text CHECK | `whatsapp_group` \| `whatsapp_individual` \| `email` \| `internal_queue` \| `webhook` |
| `channel_provider` | text CHECK | `zapi` \| `evolution` \| `meta_cloud` \| `manual` |
| `tenant_connection_id` | uuid NULL → tenant_connections | vínculo ao **Vault** (onde fica o segredo) |
| `destination_ref` | text | id do grupo / número / e-mail / url (não é o token) |
| `display_ref` | text | versão **mascarada** para UI (ex.: `…-1234`) |
| `is_primary` | boolean default false | destino principal |
| `priority_order` | int default 100 | ordem de tentativa |
| `fallback_enabled` | boolean default false | usar como fallback |
| `silence_minutes` | int default 0 | silêncio entre alertas (anti-flood) |
| `active_hours` | jsonb default '{}' | janelas de atendimento |
| `escalation_rules` | jsonb default '[]' | regras de escalonamento |
| `metadata` | jsonb default '{}' | extensível, sem segredo |
| `is_active` | boolean default true | |
| `created_at` / `updated_at` | timestamptz | trigger `update_updated_at_column()` |

**Regra dura:** **credenciais/tokens/senha ficam FORA desta tabela** — sempre no **Vault** (`tenant_connections.encrypted_secret_ref`). Aqui só `destination_ref` (id do grupo/número/e-mail) + `display_ref` mascarado. Enums como `text + CHECK` (padrão do schema). Índices: `(company_id)`, `(company_id, is_active)`, `(company_id, is_primary)`.

## 3. Como se conecta com os casos
Reusa o que já existe em `attendance_cases` (migration `20260612`):
- `handoff_required` (bool) — caso marcado para humano.
- `handoff_reason` (text) — motivo (`manual_review`, `low_confidence`, `no_policy`, `risk`, …).
- `next_step` (text) — recomendação ao humano.
- `summary` + slots em `corridor_runs.slots` — base do dossiê.
- `metadata jsonb` — pode guardar `support_destination_id` usado, `handoff_at`, etc.

**Decisão:** **não** criar tabela de `handoff_events` agora. Registrar a transferência via **`vault_audit_log`** (`event_type='handoff_requested'/'handoff_sent_dry_run'`, `metadata`) e/ou **`approval_requests`** quando houver envio (HITL). Uma tabela `handoff_events` (timeline) só se/quando for preciso histórico rico — futuro.

## 4. Como se conecta com o dossiê (`handoff_dossier`)
Especificação (gerador = batch 42H4; **não** implementar agora). O dossiê é um pacote derivado **somente de dados já no caso**:
```
handoff_dossier = {
  case_number, status, priority, channel,
  customer_name, (telefone mascarado),
  insurer_key, selected_corridor_key, selected_subcorridor_key,
  summary, next_step, risk_level,
  policy: { source, number?, verification_status, has_evidence },
  slots: { filled: [...], missing: [...] },
  last_customer_message?,            // da conversation/messages
  recommended_next_step
}
```
**Sem PII desnecessária** (sem CPF/`insured_document_ref`, sem `policy_snapshot` cru, sem token/prompt/config). Telefone mascarado. O dossiê é **texto/JSON estruturado** para o humano ler — não é envio.

## 5. Como se conecta com WhatsApp — por fases
- **MVP (agora/depois):** destino configurado + **dossiê visível/copiar** no detalhe do caso. **Envio real bloqueado** (ou manual pelo operador, fora do sistema).
- **Fase 2:** **dry-run** de envio + **`approval_requests`** (HITL) usando o **provider configurado no Vault** (`tenant_connections` WhatsApp). Auditar no `vault_audit_log`.
- **Fase 3:** envio automático **apenas** quando `readiness`/policy autorizarem (corredor homologado, fonte verificada, canal disponível) — alinhado à visão de autonomia controlada.
> Nunca: token na tabela de destinos; envio sem HITL nas fases iniciais.

## 6. Grupo vs número individual
- Permitir **ambos** (`whatsapp_group`, `whatsapp_individual`) + `email`/`internal_queue`/`webhook`.
- **Múltiplos destinos** por corretora: `is_primary` (principal) + `priority_order` + `fallback_enabled` (fallback opcional).
- `silence_minutes` evita flood; `active_hours` define janelas. Recomendação: 1 destino primário ativo + fallback opcional.

## 7. Multi-tenant e segurança
- `company_id` **obrigatório**; RLS canônico: `company_id = (select u.company_id from public.users_v2 u where u.id = auth.uid())` + `service_role` full (mesmo padrão 39A1).
- **Nunca expor** número/e-mail completo sem necessidade (usar `display_ref` mascarado) nem **token** (Vault).
- Envios futuros **auditados** em `vault_audit_log`. `authenticated` só vê a própria corretora; cross-tenant proibido.

## 8. UI mínima futura (42H3)
Tela em **Personalização → Corretora → Suporte humano**: lista de destinos; **adicionar/editar** (tipo, `destination_ref`, nome amigável, primary/fallback, `silence_minutes`, ativo); marcar primário; **testar destino em dry-run**. Reusar padrões de `personalizacao/conectores` (cards/lista + `StatusPill` + estados). Sem expor token; `display_ref` mascarado.

## 9. API futura
Operacional do módulo Atendimento (por isso o namespace `/api/attendance/...`, mesmo a config morando em Personalização → Corretora):
- `GET /api/attendance/support-destinations` — lista (por company_id).
- `POST /api/attendance/support-destinations` — criar.
- `PATCH /api/attendance/support-destinations/[id]` — editar/ativar/desativar.
- `DELETE` (ou disable via PATCH `is_active=false`).
- `POST /api/attendance/cases/[caseId]/handoff-dossier` — gerar dossiê (read-only do caso).
- `POST /api/attendance/cases/[caseId]/handoff-dry-run` — preparar handoff dry-run (cria `approval_request`, **sem envio real**).
Mesmo padrão de auth/isolamento da 42B5A (Iron Session + `users_v2.company_id` + service role; nunca Supabase no client).

## 10. O que NÃO fazer agora
Envio WhatsApp real; integração portal/0800; switch Z-API/Evolution; dispatch real; browser automation; InfoCap real; autonomia de produção. **Sem** tabela de credenciais própria (Vault é a fonte). **Sem** SQL/código neste batch.

## 11. Sequência recomendada de batches
| Batch | Objetivo | Tipo |
|---|---|---|
| **42H1** | SQL foundation `human_support_destinations` (+ RLS/índices/trigger) | SQL controlado (Architect) |
| **42H2** | API destinos (`/api/attendance/support-destinations`) | Web/API |
| **42H3** | UI **Personalização → Corretora → Suporte humano** | Web |
| **42H4** | Gerador de **handoff_dossier** (read-only do caso) | Web/API |
| **42H5** | Copiar / **dry-run** de handoff no detalhe do caso (HITL via `approval_requests`) | Web/API |
| **42B5B** | Corridor Runtime Step Engine (perguntar 1 slot por vez, preencher slots/next_step) | API |
| **42B6** | Dispatch Packet + WhatsApp dry-run/HITL | API/Web |

**Dependências:** 42H1→H2→H3 (destino configurável) é pré-requisito do **handoff seguro**. 42H4/H5 (dossiê) podem vir antes do envio real. 42B5B (runtime) deve ter o destino pronto para a **saída de exceção**. Rodar **CORE-REGRESSION-001** a cada batch que tocar runtime.

## 12. Checks deste batch
| Check | Resultado |
|---|---|
| `git status --short` mostra só o relatório | ✅ |
| `git diff --check` | ✅ limpo |
| código/SQL/migration/Supabase/runtime alterado | ✅ nenhum |
| segredo/token/credencial/PII real | ✅ nenhum |
| dado bruto do dashboard antigo copiado | ✅ nenhum |

---

> **READ-ONLY:** este batch não alterou banco/SQL/código/UI/API/backend/Supabase/runtime/WhatsApp — apenas criou este plano. Sem deploy.
