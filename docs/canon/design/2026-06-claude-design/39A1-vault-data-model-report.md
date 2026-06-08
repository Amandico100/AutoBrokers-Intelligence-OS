# 39A1 — Vault Data Model Report

> **Status:** proposta executável criada · **somente docs/SQL** · **NÃO executado** · nenhum código/runtime/schema alterado, nenhum acesso ao banco.
> **Data:** 2026-06-08 · **Modelo:** Claude Opus 4.8 · **Branch:** main · **Tipo:** modelo de dados + SQL manual para revisão do Architect.

## 1. Resumo executivo
Proposta de **modelo de dados do Vault** (Caminho B do 39A0): 5 tabelas de produto — `connector_templates`, `tenant_connections`, `permission_grants`, `approval_requests`, `vault_audit_log` — que **referenciam** as estruturas técnicas existentes do Smith **sem duplicar segredos**. O DDL é **idempotente**, espelha as convenções reais do banco (`gen_random_uuid()`, RLS `service_role` + company via `users_v2`/`auth.uid()`, trigger `update_updated_at_column()`), inclui índices, seeds de catálogo (sem segredos) e RLS multi-tenant. Acompanha um **preflight SELECT-only**. **Nada foi executado** — o Architect revisa e o fundador roda manualmente.

## 2. Arquivos criados
- `docs/sql/39A1-vault-preflight.sql` — SELECT-only; confirma dependências (gen_random_uuid, tabelas base, colunas, policies-padrão, função updated_at, ausência das tabelas do Vault).
- `docs/sql/39A1-vault-data-model.sql` — DDL idempotente (5 tabelas + RLS + índices + triggers + seeds). **Não executar sem revisão.**
- `docs/canon/design/2026-06-claude-design/39A1-vault-data-model-report.md` — este relatório.

## 3. Por que o Caminho B foi confirmado
As estruturas técnicas do Smith (`agent_mcp_connections`, `agent_http_tools`, `agent_mcp_tools`, `integrations`) são **por agente** (exceto `integrations`, por empresa) e não têm conexão-por-corretora reutilizável, permissão por módulo, aprovação de ação ou auditoria. **A** (usar direto) é insuficiente; **C** (Vault novo migrando tudo) é arriscado. **B** adiciona a camada de produto **referenciando** o técnico (catálogo, OAuth/cripto, Z-API) — exatamente ADR-002 §19–20.

## 4. Por que connector_templates foi incluída
`mcp_servers` é catálogo **só de MCP**. O produto precisa de catálogo **multi-tipo** (WhatsApp/integration, OAuth, API key, login/senha, arquivo, portal, interno, HTTP tool). `connector_templates` é esse catálogo de produto (Admin Global publica; corretora ativa). Decisão do Architect: incluir agora.

## 5. Modelo de cada tabela
- **connector_templates** (global): `slug` único, `category`, `connector_kind`, `auth_type`, `risk_level` (CHECK low/medium/high/critical), `requires_approval_default`, `capabilities`/`required_fields`/`metadata` jsonb, `is_active`.
- **tenant_connections** (por corretora): FK `company_id`→companies (cascade), `connector_template_id`→connector_templates; `status`, `health_status`, `technical_ref_type` + `technical_ref_id` (**sem FK** — aponta para tipos técnicos diferentes), `encrypted_secret_ref` (**referência**, não valor), `connection_config`/`metadata`, `owner_user_id`, `last_checked_at`/`last_used_at`.
- **permission_grants** (company-scoped): FK company + tenant_connection (cascade); `subject_type`/`subject_id`, `allowed_actions` jsonb, `requires_approval`, `risk_level` (CHECK), `status`, `expires_at`.
- **approval_requests** (HITL genérico, company-scoped): FK company (cascade) + tenant_connection/permission_grant (set null); `subject_type`, `action_type`, `status`, `risk_level` (CHECK), `preview`/`request_payload`/`approval_result` jsonb, timestamps `approved_at`/`rejected_at`/`executed_at`.
- **vault_audit_log** (auditoria, company-scoped): FK company (cascade) + connection/approval (set null); `event_type`, `action`, `status`, `risk_level`, `metadata`, `ip_address`, `user_agent`.

## 6. Como o modelo evita duplicar segredos
`tenant_connections.encrypted_secret_ref` guarda **uma referência** ao segredo, não o segredo. Os valores cifrados continuam onde já existem (`integrations`, `agent_mcp_connections`) ou num store cifrado único via `EncryptionService` (Fernet/AES). `technical_ref_type`/`technical_ref_id` apontam para a estrutura técnica que detém o segredo. **Nenhuma coluna armazena token/senha em texto.** Seeds não contêm segredos.

## 7. Como o modelo suporta WhatsApp/Z-API
A conexão WhatsApp existente (`integrations`, provider `z-api`, por empresa) é referenciada por uma `tenant_connections` com `connector_template_id`=`whatsapp_zapi`, `technical_ref_type='integration'`, `technical_ref_id`=`integrations.id`. Sem copiar o token. `permission_grants` define que um Auxiliar pode `draft_message` (sem aprovação) e `send_message` (com aprovação); `approval_requests` faz o HITL do envio. MVP: **rascunho/dry-run**, envio só após aprovação.

## 8. Como o modelo suporta MCP/OAuth
MCP/OAuth permanece no runtime (`mcp_servers` + `agent_mcp_connections` cifrados via `mcp_oauth_service`). Uma `tenant_connections` pode referenciar `technical_ref_type='agent_mcp_connection'` quando a corretora "promover" uma conexão MCP a conector de produto. O catálogo de produto (`connector_templates` kind=`oauth`/`mcp`) descreve a experiência; o token segue cifrado no técnico.

## 9. Como o modelo suporta seguradoras/corredores no futuro
Seguradora é entidade de domínio (ADR-002 §24, UX-001), **não** uma `connector_templates`. No futuro, uma `insurer`/`seguradora` referenciará várias `tenant_connections` (portal, WhatsApp da assistência, 0800, API) + corredores. Este modelo já habilita isso: a seguradora "usa" conexões do Vault via `permission_grants` por `subject_type='atendimento'`/`agent`. Portais entram como `connector_kind='portal'`, `risk_level='critical'`, sem automação real no MVP.

## 10. Como o modelo suporta HITL
`approval_requests` é **genérico** (serve Auxiliares, Atendimentos, AutoBrokers, Conectores). Fluxo: criar `pending` com `preview`/`request_payload` → usuário aprova (`approved`) → runtime executa → `executed` (ou `failed`). `permission_grants.requires_approval` decide quando exigir HITL. Ação externa **bloqueada por padrão** (defaults `requires_approval_default=true`, `requires_approval=true`).

## 11. Como o modelo suporta auditoria
`vault_audit_log` registra todo evento (`connection_*`, `permission_*`, `approval_*`, `action_executed/failed`) com `company_id`, ator, conexão, approval, risco e `metadata` — base para logs amigáveis (corretora) e técnicos (admin), com `ip_address`/`user_agent`.

## 12. RLS e isolamento multi-tenant
Espelha o padrão real do banco:
- **service_role full access** em todas (o app usa service role via Next/backend).
- **company-scoped** para `tenant_connections`/`permission_grants`/`approval_requests` (FOR ALL) e `vault_audit_log` (read), via `company_id = (SELECT company_id FROM users_v2 WHERE id = auth.uid())` — idêntico à policy de `conversations`.
- **connector_templates**: service_role gerencia; `authenticated` lê apenas `is_active=true` (como "Anyone can read MCP servers", porém restrito a ativos/autenticados).
> **Nuance:** o app autentica via iron-session + service role (que **ignora** RLS); as policies company-scoped são **defesa em profundidade** e consistência com `conversations`. `auth.uid()` só resolve sob Supabase Auth/JWT — documentado para o Architect decidir se quer reforço adicional.

## 13. Seeds criados
8 `connector_templates` (idempotentes, `ON CONFLICT (slug) DO NOTHING`, **sem segredos**): `internal_conversations` (low), `internal_documents` (low), `whatsapp_zapi` (high, approval), `google_drive` (medium), `notion` (medium), `infocap` (high, approval), `quiver` (high, approval), `insurance_portal` (critical, approval). Apenas catálogo — nenhuma `tenant_connections`.

## 14. O que o SQL NÃO faz
Não cria WhatsApp/portal/InfoCap/Quiver reais; não envia mensagem; não faz browser automation; não cria `tenant_connections` reais; não armazena segredos; não altera `integrations`/`agent_mcp_*`/`agent_http_tools`; não cria serviço/backend/API/UI; não roda migration automática. É só schema de produto + seeds + RLS.

## 15. Como validar no Supabase
1. Rodar **`docs/sql/39A1-vault-preflight.sql`** → confirmar `gen_random_uuid`, `update_updated_at_column`, tabelas base, e que as 5 tabelas do Vault **não** existem ainda. Conferir as policies de `conversations`/`auxiliary_*` (padrão copiado).
2. Architect revisa **`docs/sql/39A1-vault-data-model.sql`**.
3. Fundador cola e roda o DDL no SQL Editor.
4. Pós-criação: `SELECT slug, category, risk_level, requires_approval_default FROM connector_templates ORDER BY slug;` (8 linhas) e `SELECT tablename, policyname FROM pg_policies WHERE tablename IN ('tenant_connections','permission_grants','approval_requests','vault_audit_log','connector_templates');`.

## 16. Riscos/remanescentes
- **`auth.uid()` vs iron-session:** policies company-scoped são defesa em profundidade; o acesso real é via service role. Decidir se há fluxo `authenticated` direto que exija reforço.
- **`integrations.token` cifrado?** confirmar (39A0 §17); se em texto puro, corrigir antes de promover WhatsApp a conector.
- **CHECK em `risk_level`** é estrito (4 valores). Demais enums ficaram texto livre (documentados) para evoluir sem migração.
- **`technical_ref_id` sem FK** (polimórfico) — integridade garantida em código, não no banco (decisão consciente).
- **`update_updated_at_column()`** deve existir (preflight confirma); se não, criar antes (ver preflight bloco 8).

## 17. Próximo batch recomendado
- **Antes:** rodar o preflight + (após revisão do Architect) o DDL; me enviar a saída da validação (§15).
- **39A2 — Vault service + HITL backend:** serviço de conexões (CRUD + resolução de segredo via `EncryptionService`), enforcement de `permission_grants`, ciclo de `approval_requests`, `vault_audit_log`; adapter WhatsApp (Z-API) em **modo rascunho**.
- **39A3 — UI Conectores + Aprovações** (reuso 37B3).
- **Alternativa de valor:** **38B — Auxiliar de Cobrança** como primeiro consumidor do HITL.
