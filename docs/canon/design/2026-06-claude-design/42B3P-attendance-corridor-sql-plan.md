# 42B3P — Attendance / Corridor SQL Plan (READ-ONLY)

> **Status:** plano técnico de banco · **READ-ONLY** · **NÃO é SQL executável** · nenhum schema/migration/Supabase/código/runtime alterado · sem deploy.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main
> **Aguarda:** revisão do Architect/Founder antes de qualquer DDL/migration.

## 1. Executive summary
Plano para o **SQL mínimo** do MVP de Atendimento/Corredores (SPEC-005/006), **sem criar SQL executável**. Recomenda **4 tabelas novas** (`attendance_cases`, `corridor_templates`, `corridor_runs`, `dispatch_packets`) que reusam o máximo do schema atual (`companies`, `conversations`/`messages`, `agents`, `agent_delegations`, **`approval_requests`/`vault_audit_log`**, `integrations`), replicam o **padrão de RLS/trigger já canônico** (39A1) e **não criam motor paralelo** (o workflow roda no Smith/LangGraph; o banco só guarda **estado**). O SQL final será dividido em fases e escrito/revisado pelo Architect.

## 2. Schema atual relevante (auditado)

| Tabela | Função atual | Reusar? | Relação com Atendimento | Risco |
|---|---|---|---|---|
| `companies` (id PK) | tenant | **Sim** | `company_id` em todas as novas tabelas | — |
| `users_v2` (id, company_id) | usuários | **Sim** | **fonte do RLS**: `company_id = (SELECT u.company_id FROM users_v2 u WHERE u.id = auth.uid())` | — |
| `agents` | agentes Smith | **Sim** | `assigned_agent_id` (Attendance agent) | — |
| `agent_delegations` | orchestrator→subagent | **Sim** | Attendance ↔ SubAgent especialista (apólice/seguradora) | — |
| `conversations` (id, user_id NOT NULL, session_id NOT NULL, **company_id nullable**, status, channel, agent_id, user_phone, human_handoff_reason…) | chat Smith | **Sim** | `attendance_cases.conversation_id` → conversations.id | `company_id` **nullable** e `user_id`/`session_id` **NOT NULL** → criar conversa de caso exige user_id/session_id |
| `messages` (conversation_id, **role CHECK user\|assistant**, content, type CHECK text\|voice, image_url, sender_user_id) | mensagens | **Sim, com ressalva** | espelho do canal do cliente | **`role` só aceita user/assistant** → mapear segurado→user, operador/agente→assistant (ator real em `sender_user_id`/metadata). Se precisar de papéis distintos (seguradora/prestador), planejar **relaxe controlado do CHECK** (42B3B) — não criar `attendance_messages` ainda |
| `conversation_logs` | turnos do LLM (rag_chunks/tokens/strategy) | **Sim** | observabilidade base do Attendance | — |
| `integrations` (provider, identifier, token, instance_id, agent_id, is_active) | canal WhatsApp (Z-API/Evolution) | **Sim** | `attendance_cases.channel_instance_id` (ref) | token é segredo — nunca expor; usar via service |
| **`approval_requests`** (company_id, subject_type **inclui `atendimento`**, action_type text, status, risk_level, preview/request_payload/approval_result jsonb, approved_at/executed_at) | **HITL genérico (Vault)** | **Sim (chave)** | `dispatch_packets.approval_request_id` → approval_requests.id | já pronto para ação sensível |
| `vault_audit_log` (company_id, event_type, approval_request_id, metadata) | auditoria Vault | **Sim** | auditar dispatch/handoff | — |
| `connector_templates`/`tenant_connections`/`permission_grants` | Vault produto (39A1) | **Sim** | canal/credencial (WhatsApp/InfoCap **já seedados**) | — |
| `documents` | RAG por tenant/agent | **Sim** | apólice via upload + RAG (apoio) | nunca intake bruto/PII |
| `auxiliary_templates`/`tenant_auxiliaries` | Auxiliares (produto) | parcial | Attendance pode acionar Auxiliar | — |

> **Padrão canônico a replicar** (de 39A1): `gen_random_uuid()`; `created_at/updated_at timestamptz`; trigger `public.update_updated_at_column()`; RLS = `service_role` full + `company members` via `users_v2`/`auth.uid()`; `text + CHECK` para enums (o schema **não** usa pg enums).

## 3. Tabelas novas mínimas recomendadas
Apenas **4** (justificadas pelas SPEC-005/006): `attendance_cases` (estado do caso), `corridor_templates` (registry estruturado), `corridor_runs` (instância/fase/slots), `dispatch_packets` (pacote de acionamento + HITL). Nada além disso no MVP (ver §15).

## 4. `attendance_cases` — plano
Estado central do caso. Campos (obrigatório **[req]** / nullable no MVP **[null]**):
- `id` uuid PK [req] · `company_id` uuid → companies.id [req]
- `conversation_id` uuid → conversations.id [null] (caso pode iniciar simulado)
- `assigned_agent_id` uuid → agents.id [null] · `assigned_user_id` uuid [null]
- `case_number` text [req, único por company] · `status` text [req] · `priority` text [null, default 'normal'] · `channel` text [req, default 'dashboard'] · `channel_instance_id` uuid [null] (ref integrations/tenant_connections)
- `customer_name` text [null] · `customer_phone` text [null, **PII**]
- `insured_name` text [null] · **`insured_document_ref` text [null]** (REFERÊNCIA/última-4/hash — **nunca CPF cru**) · `insured_address` jsonb [null]
- `intent` text [null] · `insurer_key` text [null] · `line_kind` text [null] · `macro_service` text [null]
- `selected_corridor_key` text [null] · `selected_subcorridor_key` text [null]
- `policy_source` text [null] (manual|upload|snapshot|infocap) · `policy_number` text [null] · `policy_snapshot` jsonb [null] · `coverage_evidence` jsonb [null] · `verification_status` text [null, default 'unverified']
- `risk_level` text [null, default 'low'] · `handoff_required` boolean [req, default false] · `handoff_reason` text [null]
- `summary` text [null] · `next_step` text [null] · `metadata` jsonb [req, default '{}']
- `created_at`/`updated_at` timestamptz [req] · `closed_at` timestamptz [null]

**Obrigatórios reais no MVP:** id, company_id, case_number, status, channel, handoff_required, timestamps. O resto é coletado ao longo das fases (slots vão em `corridor_runs`). **PII:** customer_phone/insured_* protegidos por RLS; documento como **ref**, não valor; sem CPF cru em metadata.

## 5. `corridor_templates` — plano (registry estruturado, NÃO RAG)
- `id` uuid PK · `company_id` uuid → companies.id **[null = global]** · `scope` text [req] (global|tenant)
- `corridor_key` text [req] · `subcorridor_key` text [null] · `display_name` text [req]
- `insurer_key` text [req] · `line_kind` text [req] · `macro_service` text [req] · `service_type` text [null]
- `channel_ref` text [null] · `source_of_truth` text [null]
- `status_documental` text [req] · `status_operacional` text [req] · `readiness` text [req]
- `requires_action_engine` boolean [req, default true] · `requires_dispatch_packet` boolean [req, default true] · `fallback_to_dossier` boolean [req, default true]
- `allowed_channels` jsonb [req, default '[]'] · `phases` jsonb [req, default '[]'] · `required_slots` jsonb [req, default '[]'] · `optional_slots` jsonb [req, default '[]'] · `guardrails` jsonb [req, default '[]'] · `golden_tests` jsonb [req, default '[]']
- `metadata` jsonb [req, default '{}'] · `is_active` boolean [req, default true] · `created_at`/`updated_at`
- **Unicidade:** `(coalesce(company_id,'global'), corridor_key, subcorridor_key)`.

**Seed (global, company_id NULL):** (a) família `corridor_key='allianz_residential_assistance'`, `subcorridor_key=NULL`, insurer_key='allianz', line_kind='residencial', macro_service='assistencia-residencial', readiness='mapped_from_real_conversations'; (b) `subcorridor_key='electrician'` com phases/required_slots/guardrails/golden_tests do Eletricista (§12), readiness ≤ `controlled_real_test`. **Sem PII.**

## 6. `corridor_runs` — plano (instância por caso)
- `id` uuid PK · `company_id` uuid → companies.id [req] · `case_id` uuid → attendance_cases.id [req] · `corridor_template_id` uuid → corridor_templates.id [req]
- `phase` text [req] · `status` text [req]
- **`slots` jsonb [req, default '{}']** · `diagnostics` jsonb [req, default '{}'] · `next_step` text [null] · `last_agent_action` text [null] · `metadata` jsonb [req, default '{}']
- `started_at`/`updated_at` [req] · `completed_at` [null]

**Por que slots em jsonb (não tabela):** os slots variam por subcorredor (eletricista≠encanador), são preenchidos incrementalmente e lidos juntos pelo runtime/dashboard. Uma tabela `corridor_slots` cedo geraria join complexo e schema rígido sem ganho no MVP (SPEC-005 recomenda jsonb). Migrar para tabela só se houver consulta cruzada por slot (futuro).

## 7. `dispatch_packets` — plano (pacote + HITL)
- `id` uuid PK · `company_id` uuid → companies.id [req] · `case_id` uuid → attendance_cases.id [req] · `corridor_run_id` uuid → corridor_runs.id [req]
- `status` text [req, default 'draft'] · `channel` text [null] · `provider` text [null]
- `idempotency_key` text [req, **único**] · `payload` jsonb [req, default '{}'] · `missing_data` jsonb [req, default '[]']
- **`approval_request_id` uuid → approval_requests.id [null]** · `execution_result` jsonb [req, default '{}'] · `metadata` jsonb [req, default '{}']
- `created_at`/`updated_at` [req] · `approved_at` [null] · `sent_at` [null]

**Relação com `approval_requests`:** ação externa **nunca** sai sem HITL. Fluxo: monta dispatch (`missing_data` vazio) → cria `approval_request` (`subject_type='atendimento'`, `action_type='corridor_dispatch'`/`'whatsapp_send_message'`, `request_payload`=preview, `risk_level`) → `dispatch_packets.approval_request_id` referencia → ao aprovar, executa (dry-run no MVP) → `vault_audit_log`. Reusa 100% o HITL do Vault (39A1).

## 8. Relações e foreign keys
- `attendance_cases.company_id` → `companies.id` (ON DELETE CASCADE).
- `attendance_cases.conversation_id` → `conversations.id` (ON DELETE SET NULL) — **OK** (conversations existe; `company_id` lá é nullable, então não dá para confiar nele — usar o `company_id` do próprio caso).
- `attendance_cases.assigned_agent_id` → `agents.id` (SET NULL).
- `corridor_runs.case_id` → `attendance_cases.id` (CASCADE) · `corridor_runs.corridor_template_id` → `corridor_templates.id` (RESTRICT).
- `dispatch_packets.case_id` → `attendance_cases.id` (CASCADE) · `dispatch_packets.corridor_run_id` → `corridor_runs.id` (CASCADE).
- `dispatch_packets.approval_request_id` → `approval_requests.id` (SET NULL) — **compatível** (39A1 usa o mesmo padrão).

**FKs arriscadas / sinalizar:** `channel_instance_id` **sem FK** (aponta para `integrations` **ou** `tenant_connections` — tipos diferentes; espelhar o padrão `tenant_connections.technical_ref_id` que é "SEM FK"). `messages` **não** ganha FK nova; reuso por `conversation_id` (com a ressalva do `role` CHECK, §2).

## 9. Status e enums
**Recomendação: `text + CHECK constraint`** (consistente com TODO o schema atual; flexível p/ MVP; sem pg enums nem lookup tables).
- `attendance_cases.status`: `new | triage | collecting | policy_check | ready_for_dispatch | awaiting_approval | dispatched | following_up | resolved | closed | cancelled | blocked`.
- `corridor_runs.phase` (SPEC/legado): `entrada | identificacao | levantamento | apolice | decisao | preparacao | acionamento | acompanhamento | encerramento`.
- `corridor_runs.status`: `active | blocked | awaiting_input | awaiting_approval | completed | aborted`.
- `dispatch_packets.status`: `draft | ready | awaiting_approval | approved | rejected | sent | failed | cancelled`.
- `corridor_templates.readiness` (legado): `draft | mapped | mapped_from_real_conversations | requires_execution_authorization | ready_for_live_test | controlled_real_test | production` (MVP **nunca** `production`).

## 10. RLS e segurança
Replicar **exatamente** o padrão 39A1 nas 4 tabelas:
- `ALTER TABLE … ENABLE ROW LEVEL SECURITY;`
- **service_role**: `USING (true) WITH CHECK (true)`.
- **company members** (authenticated): `company_id = (SELECT u.company_id FROM public.users_v2 u WHERE u.id = auth.uid())` (USING + WITH CHECK).
- **`corridor_templates` global**: linhas com `company_id IS NULL` legíveis por authenticated (`FOR SELECT USING (company_id IS NULL OR company_id = <tenant>)`); escrita só service_role/Admin.
- `dispatch_packets`/`attendance_cases`/`corridor_runs`: **isolados por company_id**; nunca cross-tenant.
- HITL continua governado por `approval_requests` (já com RLS).
- **Helper existe:** `users_v2.company_id` + `auth.uid()` (não precisa criar função nova). `update_updated_at_column()` já existe (reusar nos triggers).

## 11. Índices recomendados
- `attendance_cases`: `(company_id)`, `(company_id, status)`, `(conversation_id)`, **`(company_id, case_number)` UNIQUE**, `(selected_corridor_key)`, `(selected_subcorridor_key)`, `(created_at DESC)`, `(updated_at DESC)`.
- `corridor_templates`: `(corridor_key, subcorridor_key)`, `(scope)`, `(is_active)`, parcial `WHERE company_id IS NULL` (globais).
- `corridor_runs`: `(company_id)`, `(case_id)`, `(corridor_template_id)`, `(status)`, `(phase)`.
- `dispatch_packets`: `(company_id)`, `(case_id)`, `(corridor_run_id)`, **`(idempotency_key)` UNIQUE**, `(status)`, `(approval_request_id)`, `(created_at DESC)`.

## 12. Seeds MVP (planejados — sem SQL, sem PII)
- **Família global** `allianz_residential_assistance`: insurer_key=allianz, line_kind=residencial, macro_service=assistencia-residencial, allowed_channels=`["whatsapp","dashboard"]`, readiness=`mapped_from_real_conversations`, is_active=true.
- **Subcorredor global** `electrician`: phases (9 fases §9), `required_slots` (electricalIssueType, outageScope, affectedRoom, riskLevel, schedulePreference, policyholderName, policyNumber, insuredLocation, serviceCoverageName), `guardrails` (eletrodoméstico→outro subcorredor; risco elétrico→dossiê; rede externa→fora de escopo; não prometer cobertura; não inventar protocolo), `golden_tests` (estrutura entrada/estado-esperado/saída-proibida), readiness=`controlled_real_test` (máx MVP). **Tudo estruturado/curado; sem conversa real/PII.**

## 13. Compatibilidade com SPEC-005 / SPEC-006
- `attendance_cases` = **Case Runtime** (SPEC-005): estado, conversa, seleção, evidência de apólice, handoff.
- `corridor_templates` = **Corridor registry/família** (SPEC-006): família Allianz Residencial + subcorredores; readiness/guardrails/golden.
- `corridor_runs` = **Corridor Runtime**: fases/slots/diagnostics.
- `dispatch_packets` = **Dispatch Packet + HITL** (SPEC-005/006): pacote estruturado + aprovação (Vault). Tudo dry-run/HITL no MVP; sem ação externa real.

## 14. Compatibilidade com Smith (sem motor paralelo)
O banco guarda **estado**; o **workflow roda no Smith**: LangGraph (`graph.py`) + **Attendance agent** (Context Package `role=attendance`, 42A6/42A4) + `agent_delegations` (SubAgents) + `conversations`/`messages` (conversa) + `MemoryService` (case memory futura) + RAG (`SearchService`, apoio) + **`approval_requests`/`vault_audit_log`** (HITL). Nenhuma engine de workflow nova; nenhum segundo RAG/chat.

## 15. O que NÃO criar agora
`attendance_messages` (reusar `messages`; só criar se o `role` CHECK realmente bloquear — então relaxe controlado), `corridor_slots`, `corridor_phases`, `insurer_portal_sessions`, `browser_sessions`, `infocap_credentials` (credencial vai no Vault, nunca tabela própria de segredo), `whatsapp_provider_instances` extras (já há `integrations`/`tenant_connections`), qualquer tabela de autoevolução/aprendizado, qualquer tabela de web search.

## 16. Plano de SQL futuro (fases — escrito/revisado pelo Architect)
- **42B3A — preflight/introspection:** SELECTs (information_schema/pg_policies) confirmando companies/users_v2/conversations/messages/approval_requests + ausência das 4 novas.
- **42B3B — DDL base:** 4 tabelas `IF NOT EXISTS` + CHECKs + triggers `update_updated_at_column()`. (+ eventual relaxe controlado do `messages.role` CHECK, se decidido.)
- **42B3C — RLS policies:** enable + service_role + company-members + global read p/ corridor_templates.
- **42B3D — indexes:** §11.
- **42B3E — seeds:** família Allianz + Eletricista (global; sem PII).
- **42B3F — verification queries:** counts, RLS, FKs, seeds presentes.
- **42B3G — rollback plan:** DROP reverso (dispatch_packets → corridor_runs → attendance_cases → corridor_templates) + remoção de policies/índices; idempotente.
> O SQL final **não** é gerado por este batch — é criado/revisado pelo Architect.

## 17. Riscos
Schema amplo demais (mitigar: só 4 tabelas + jsonb); FK errada (conversations.company_id nullable; channel_instance_id sem FK por design; messages.role CHECK); RLS permissiva (replicar o padrão restrito 39A1; testar cross-tenant); duplicar conversations/messages (reusar, não recriar); travar todos subcorredores cedo (só Eletricista executa; resto é seed de família); slots como tabela complexa cedo (usar jsonb); não deixar espaço p/ InfoCap (policy_source/coverage_evidence preveem); multi-provider WhatsApp (via integrations/tenant_connections); misturar global×tenant (scope + company_id NULL + RLS); **PII em metadata** (documento como ref, telefone protegido por RLS, sem CPF cru, sem intake bruto).

## 18. Recomendação final
**Recomendo avançar para SQL controlado** — o schema atual cobre o reuso (companies/users_v2/conversations/messages/approval_requests/vault_audit_log) e o padrão de RLS/trigger é claro e replicável. As 4 tabelas + jsonb são suficientes e mínimas. **Não** é preciso recon adicional de banco. Antes do DDL, decidir **um ponto**: reusar `messages` com role-mapping **ou** relaxar o `messages.role` CHECK (recomendo reuso com mapping no MVP; relaxe só se papéis distintos forem necessários). Próximo: **42B3A (preflight)** → **42B3B (DDL)** … sob controle do Architect; e **42A4 (Attendance Blueprint)** em paralelo para o runtime.
