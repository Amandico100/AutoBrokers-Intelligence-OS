# 39A2 — Vault Service + HITL API Report

> **Status:** concluído, **commitado e pushado** · typecheck/build verdes · **só Next API** (sem backend Python, sem UI, sem serviço externo) · sem SQL/migration.
> **Data:** 2026-06-08 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Resumo executivo
Primeira camada **funcional** do Vault/Conectores/HITL: rotas Next server-side sobre as 5 tabelas criadas no 39A1. Permite **listar templates**, **criar/listar/atualizar conexões da corretora** (sem segredo), **criar/listar permissões**, **criar/aprovar/rejeitar pedidos de aprovação (HITL)** e **ler auditoria** — tudo **escopado por `company_id` da sessão**, com **bloqueio de segredos no payload** e **gravação de auditoria** em toda escrita. **Nenhuma ação externa real** (sem WhatsApp/OAuth/portal). UI fica para o 39A3.

## 2. Arquivos alterados
**Lib (novo):**
- `lib/vault/types.ts` — tipos (ConnectorTemplate, TenantConnection, PermissionGrant, ApprovalRequest, VaultAuditLog + inputs).
- `lib/vault/server.ts` — helpers server-only: reuso de `resolveSessionCompany`/`getSupabaseAdmin` (Auxiliares), `payloadHasSecret`, `isPlainObject`, `writeAudit`, constantes de status/risco, `SENSITIVE_KEYS`.
- `lib/vault/api.ts` — client helpers (uso na UI do 39A3).
**Next API (novo) — 8 arquivos de rota:**
- `app/api/vault/templates/route.ts`
- `app/api/vault/connections/route.ts`
- `app/api/vault/connections/[connectionId]/route.ts`
- `app/api/vault/connections/[connectionId]/permissions/route.ts`
- `app/api/vault/approvals/route.ts`
- `app/api/vault/approvals/[approvalId]/approve/route.ts`
- `app/api/vault/approvals/[approvalId]/reject/route.ts`
- `app/api/vault/audit/route.ts`
**Docs:** este relatório. **Nenhum arquivo Python/backend alterado.**

## 3. Endpoints criados
| Método | Rota | Função |
|---|---|---|
| GET | `/api/vault/templates` | templates ativos do catálogo |
| GET / POST | `/api/vault/connections` | listar / criar conexão da empresa |
| GET / PATCH | `/api/vault/connections/[connectionId]` | obter / atualizar (campos seguros) |
| GET / POST | `/api/vault/connections/[connectionId]/permissions` | listar / criar permission_grant |
| GET / POST | `/api/vault/approvals` | listar / criar approval_request (pending) |
| POST | `/api/vault/approvals/[approvalId]/approve` | aprovar (pending → approved) |
| POST | `/api/vault/approvals/[approvalId]/reject` | rejeitar (pending → rejected) |
| GET | `/api/vault/audit` | eventos recentes de auditoria |

## 4. Como company_id/user_id são resolvidos
Reuso de `resolveSessionCompany()` (de `lib/auxiliaries/server.ts`): lê o cookie iron-session, pega `session.userId`, busca `users_v2.company_id` com **service role server-side**. **O `company_id` nunca vem do client.** Todas as queries filtram por `company_id` e validam posse de `connectionId`/`approvalId`/`permission_grant_id` antes de qualquer escrita (anti-IDOR). Service role nunca é exposto ao client.

## 5. Como secrets são bloqueados
`payloadHasSecret(body)` varre o payload **profundamente** (objetos/arrays aninhados) procurando nomes de campo sensíveis por **match exato** (case-insensitive): `token, access_token, refresh_token, client_token, password, secret, api_key, key, credential, credentials`. Se encontrar, retorna **400** com `SECRET_REJECTION_MESSAGE` ("Credenciais devem ser configuradas por fluxo seguro de conexão, não por esta rota."). Aplicado em **todas** as rotas de escrita (connections POST/PATCH, permissions POST, approvals POST). Nenhuma rota lê/grava/retorna segredo; `tenant_connections.encrypted_secret_ref` **não** é setado por estas rotas.

## 6. Como conexões são criadas/listadas
- **GET** lista `tenant_connections` por `company_id` (desc por `created_at`).
- **POST** valida `connector_template_slug` (deve existir e estar **ativo**), exige `name`, aceita `status` (default `draft`, validado contra a lista permitida), `technical_ref_type`/`technical_ref_id`, `connection_config`/`metadata` (objetos). Grava `company_id`+`owner_user_id` da sessão. **Não** aceita segredo. Audit `connection_created`.
- **PATCH** atualiza só campos seguros (`name`, `status`, `health_status`, `connection_config`, `metadata`), valida enums, confirma posse, **não** permite trocar `company_id`. Audit `connection_updated`.

## 7. Como permissões são criadas/listadas
Sob `/connections/[connectionId]/permissions`: confirma que a conexão pertence à empresa; **GET** lista `permission_grants` (conexão + company); **POST** exige `subject_type`, normaliza `allowed_actions` (string[]), `risk_level` (validado, default `medium`), `requires_approval` (default **true**), `status='active'`, `created_by_user_id` da sessão. Audit `permission_granted`.

## 8. Como aprovações são criadas/aprovadas/rejeitadas
- **POST /approvals** exige `action_type` + `subject_type`; valida posse de `tenant_connection_id`/`permission_grant_id` se enviados; cria com `status='pending'`, `risk_level` validado, `preview`/`request_payload` (objetos), `requested_by_user_id` da sessão. Audit `approval_requested`.
- **approve/reject** só atuam se `status='pending'` (senão **409**); usam `.eq('status','pending')` no UPDATE (guarda contra corrida); gravam `approved_at`/`rejected_at`, `approval_result` (`{approved_by|rejected_by, reason}`), e `approved_by_user_id` no approve. Audit `approval_approved`/`approval_rejected`. **Nada é executado** — apenas o estado da aprovação muda (execução real virá com adapters no futuro).

## 9. Como auditoria é gravada
`writeAudit(supabase, entry)` insere em `vault_audit_log` (best-effort; nunca derruba a operação). Eventos: `connection_created`, `connection_updated`, `permission_granted`, `approval_requested`, `approval_approved`, `approval_rejected`. Campos: `company_id`, `tenant_connection_id?`, `approval_request_id?`, `actor_user_id`, `event_type`, `action`, `status`, `risk_level`, `metadata`. **Nenhum segredo em `metadata`.**

## 10. O que NÃO foi implementado
UI (Conectores/Aprovações), backend FastAPI/adapters, envio de WhatsApp, teste real de Z-API, Google/Notion/Drive OAuth, InfoCap/Quiver reais, portal de seguradora, browser automation, execução de ação externa, Auxiliar de Cobrança, scheduler/worker. Sem SQL/migration. Sem alteração de billing/chat/Auxiliar de Resumo. Sem mexer em policies do Supabase.

## 11. Checks executados
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ passou |
| `npm run build` (env dummy) | ✅ passou (`✓ 92/92`; 8 rotas `/api/vault/*` registradas) |
| `git diff --check` | ✅ limpo (só `LF→CRLF`) |
| branding scan (`app/api/vault`,`lib/vault`) | ✅ **sem ocorrências** |
| secret-name scan | ✅ termos aparecem **apenas** na lista `SENSITIVE_KEYS` do sanitizer (bloqueio), **nunca como valores** |

## 12. Como testar manualmente sem UI
Logado no app (cookie de sessão), no DevTools:
```js
await fetch('/api/vault/templates').then(r=>r.json())            // 8 templates
await fetch('/api/vault/connections').then(r=>r.json())          // [] inicialmente
await fetch('/api/vault/connections', { method:'POST', headers:{'Content-Type':'application/json'},
  body: JSON.stringify({ connector_template_slug:'internal_documents', name:'Documentos da corretora' }) }).then(r=>r.json())
await fetch('/api/vault/approvals', { method:'POST', headers:{'Content-Type':'application/json'},
  body: JSON.stringify({ subject_type:'tenant_auxiliary', action_type:'whatsapp_draft_message', preview:{ to:'cliente', text:'rascunho' } }) }).then(r=>r.json())
// pegue o id retornado e aprove:
await fetch('/api/vault/approvals/<id>/approve', { method:'POST' }).then(r=>r.json())
await fetch('/api/vault/audit').then(r=>r.json())                // eventos gravados
// Teste de bloqueio de segredo (deve dar 400):
await fetch('/api/vault/connections', { method:'POST', headers:{'Content-Type':'application/json'},
  body: JSON.stringify({ connector_template_slug:'whatsapp_zapi', name:'x', connection_config:{ token:'abc' } }) }).then(r=>r.json())
```
Conferir no Supabase: linhas em `tenant_connections`/`approval_requests`/`vault_audit_log` escopadas à empresa.

## 13. Riscos/remanescentes
- **Sem secret flow ainda:** conectar serviços reais (Z-API/OAuth) exige um fluxo seguro de credenciais (39A2.x/39A3) que use `EncryptionService` e popule `encrypted_secret_ref`. Estas rotas deliberadamente **não** lidam com segredo.
- **RLS vs service role:** as rotas usam service role (consistente com Auxiliares); o isolamento é garantido no código por `company_id`. As policies do banco (39A1) são defesa em profundidade.
- **Sem execução:** aprovar um pedido só muda o status; nenhum efeito externo ocorre (intencional neste batch).
- **`key` bloqueado por match exato:** campos legítimos com nome exatamente `key` em `connection_config`/`metadata` seriam rejeitados (renomear). Substrings como `idempotency_key` não são bloqueadas.

## 14. Próximo batch recomendado
- **Deploy Web** (rotas Next novas) + smoke test (§12). **API backend não muda** → sem deploy de API.
- **39A3 — UI Conectores + Aprovações** (reuso 37B3): galeria de templates, conexões da corretora, permissões e fila de aprovações (HITL) consumindo `lib/vault/api.ts`.
- Depois: **39A2.x — secret flow** (conexão real WhatsApp/Z-API em modo rascunho via `EncryptionService` + `encrypted_secret_ref`) e **38B — Auxiliar de Cobrança** como primeiro consumidor do HITL.
