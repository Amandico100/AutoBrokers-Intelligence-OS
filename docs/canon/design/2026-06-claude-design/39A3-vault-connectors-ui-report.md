# 39A3 — Vault Connectors + Approvals UI Report

> **Status:** concluído, **commitado e pushado** · typecheck/build verdes · **só UI/Next** (sem backend Python, sem SQL, sem serviço externo).
> **Data:** 2026-06-08 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Resumo executivo
Primeira **UI funcional** do Vault/Conectores/HITL, consumindo as APIs do 39A2. A corretora agora vê o **catálogo de conectores**, prepara **conexões em rascunho** (sem credencial), gerencia **permissões**, cria/aprova/rejeita **pedidos de aprovação (HITL)** e consulta a **auditoria** — tudo em Névoa, escopado por empresa (via APIs), mobile-first. **Nenhuma ação externa real**: aprovar só muda status.

## 2. Arquivos alterados
**Criados:**
- `components/vault/labels.ts` — helpers de apresentação (riskPill, connectionStatusPill, approvalStatusPill, slugIcon, fmtDateTime).
- `components/vault/CreateConnectionModal.tsx` — modal de criar conexão (rascunho, sem segredo).
- `components/vault/PermissionGrantPanel.tsx` — listar/criar permissões da conexão.
- `app/dashboard/personalizacao/conectores/aprovacoes/page.tsx` — fila HITL.
- `app/dashboard/personalizacao/conectores/auditoria/page.tsx` — auditoria recente.
- `docs/canon/design/2026-06-claude-design/39A3-vault-connectors-ui-report.md` — este relatório.
**Reescrito:**
- `app/dashboard/personalizacao/conectores/page.tsx` — de mock (37B4) para UI real (catálogo + minhas conexões + permissões + aprovação de teste).
**Reuso (sem alterar):** `lib/vault/api.ts`, `lib/vault/types.ts` (do 39A2), padrões `components/patterns/*`, ShadCN `dialog/button/input/label`. **Nenhum backend Python alterado.**

## 3. Telas criadas/alteradas
- **`/dashboard/personalizacao/conectores`** — header + abas **Catálogo** / **Minhas conexões** + atalhos para Aprovações e Auditoria. Catálogo = cards dos 8 templates (ícone, categoria, `auth_type` em tag, pílula de risco, CTA "Preparar conexão"). Minhas conexões = cards reais com status/saúde/data, expandíveis (permissões + "Criar aprovação de teste").
- **`/dashboard/personalizacao/conectores/aprovacoes`** — fila HITL (status/risco/preview/data + Aprovar/Rejeitar) + "Criar aprovação de teste" + aviso de que aprovar não executa nada.
- **`/dashboard/personalizacao/conectores/auditoria`** — lista de eventos (rótulo amigável + ação/status + risco + data).

## 4. APIs consumidas
Via `lib/vault/api.ts` (39A2): `fetchConnectorTemplates`, `fetchTenantConnections`, `createTenantConnection`, `fetchPermissions`, `createPermission`, `fetchApprovalRequests`, `createApprovalRequest`, `approveRequest`, `rejectRequest`, `fetchAuditLog`. Todas same-origin (cookie de sessão); `company_id` é resolvido **no servidor** (nunca no client).

## 5. Fluxo de conexão rascunho
Catálogo → "Preparar conexão" → `CreateConnectionModal` (só **Nome**; status `draft`) → `POST /api/vault/connections` (`connector_template_slug` + name). **Nenhum campo de credencial.** Se a API recusar segredo, mostra a mensagem amigável. Sucesso → aviso + troca para "Minhas conexões" + recarrega.

## 6. Fluxo de permissões
Na conexão expandida, `PermissionGrantPanel`: lista `permission_grants` e cria uma permissão segura — **quem** (AutoBrokers/Auxiliar/Atendimento), **ações** (read/draft_message/test_connection via chips), **exigir aprovação** (marcado por padrão), risco `medium`. `POST .../permissions`. Texto: "Permissões definem quem pode usar esta conexão. Ações sensíveis continuam exigindo aprovação humana."

## 7. Fluxo de aprovações (HITL)
Página Aprovações lista `approval_requests` (status/risco/preview seguro/data). **Aprovar/Rejeitar** só aparecem em `pending` e apenas mudam o status (`POST .../approve` | `.../reject`). "Criar aprovação de teste" gera um pedido `whatsapp_draft_message` com `dry_run:true` (na página e por conexão). Aviso fixo: aprovar **não executa** ação externa nesta fase.

## 8. Fluxo de auditoria
Página Auditoria consome `GET /api/vault/audit` e mostra eventos (`connection_created`, `permission_granted`, `approval_requested`, `approval_approved/rejected`…) com rótulos em pt-BR, ação/status, risco e data. Sem JSON cru, sem segredo.

## 9. Segurança/segredos
- **Sem qualquer campo** de token/senha/api_key/secret na UI (scan confirmou zero ocorrências). Conexões são rascunho/referência; o fluxo de credenciais virá em batch dedicado com `EncryptionService`.
- `company_id` nunca vem do client (resolvido nas rotas). Erros são amigáveis — sem stack trace.
- Aprovar/rejeitar **não dispara** nada externo.

## 10. Mobile
`max-w-4xl` + `px-4`, cards em coluna, `flex-wrap` em ações/badges, listas com `min-w-0`/`truncate`, modal ShadCN responsivo (`sm:max-w-md`), abas e chips que quebram linha. Sem scroll horizontal; bottom nav não cobre conteúdo (páginas rolam internamente).

## 11. O que NÃO foi implementado
Conexão real (WhatsApp/Z-API/OAuth/portal), envio de mensagem, fluxo de segredo/credencial, browser automation, execução pós-aprovação, rota dinâmica `[connectionId]` (detalhe é inline/expandido), backend/adapters, Auxiliar de Cobrança. Sem SQL/migration/schema. Sem mexer em chat/billing/Auxiliar de Resumo.

## 12. Checks executados
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ passou |
| `npm run build` (env dummy) | ✅ passou (`✓ 94/94`; rotas conectores/aprovacoes/auditoria registradas) |
| `git diff --check` | ✅ limpo (só `LF→CRLF`) |
| branding scan | ✅ **sem ocorrências** |
| secret-field scan | ✅ **zero** (nenhum campo nem menção de segredo na UI) |

## 13. Como testar manualmente (pós-deploy Web, logado)
1. `/dashboard/personalizacao/conectores` → aba **Catálogo**: ver os **8 templates**.
2. "Preparar conexão" em **Documentos internos** → nomear → criar (rascunho).
3. Aba **Minhas conexões** → ver a conexão → **Permissões** → "Adicionar permissão segura" (read/draft_message).
4. "Criar aprovação de teste" (na conexão ou na página Aprovações).
5. **Aprovações** → Aprovar/Rejeitar o pedido.
6. **Auditoria** → ver `connection_created`, `permission_granted`, `approval_requested`, `approval_approved/rejected`.

## 14. Riscos/remanescentes
- **Sem secret flow:** conectar serviços reais exige um batch com `EncryptionService` + `encrypted_secret_ref` (a UI hoje só cria rascunhos/referências).
- **`integrations.token` (Z-API):** confirmar criptografia antes de promover WhatsApp a conexão real (pendência do 39A0/39A1).
- **Sem execução pós-aprovação** (intencional): a ligação aprovação→ação externa virá com adapters.
- Detalhe de conexão é inline (sem rota própria) — suficiente no MVP; pode virar `[connectionId]` depois.

## 15. Próximo batch recomendado
- **Deploy Web** (só Next mudou) + smoke test (§13). **API backend não muda** → sem deploy de API.
- **39A4 — Secret flow** (conectar WhatsApp/Z-API em **modo rascunho** com `EncryptionService` + `encrypted_secret_ref`; teste de conexão sem envio).
- **38B — Auxiliar de Cobrança**: primeiro consumidor real do HITL (gera rascunho → `approval_requests` → aprovação → execução futura).
