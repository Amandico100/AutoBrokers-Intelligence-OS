# 42H2 — Human Support Destinations API Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/WhatsApp/envio externo/UI) · sem deploy automático.
> **Data:** 2026-06-13 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados
- `app/api/attendance/support-destinations/route.ts` (**novo**) — `GET` (listar) + `POST` (criar).
- `app/api/attendance/support-destinations/[destinationId]/route.ts` (**novo**) — `PATCH` (atualizar) + `DELETE` (soft disable).
- `lib/attendance/support-destinations.ts` (**novo**) — helpers (client/company, máscara, serialização, validação, ownership de connection, demote de primário).
- `docs/canon/design/2026-06-claude-design/42H2-human-support-destinations-api-report.md` (este).

## 2. Endpoints criados
| Método | Rota | Função |
|---|---|---|
| GET | `/api/attendance/support-destinations` | Lista destinos (active=true\|false\|all, type, provider). |
| POST | `/api/attendance/support-destinations` | Cria destino (company_id derivado; display_ref no server). |
| PATCH | `/api/attendance/support-destinations/[destinationId]` | Atualiza campos whitelisted. |
| DELETE | `/api/attendance/support-destinations/[destinationId]` | **Soft disable** (`is_active=false`, `is_primary=false`). |

Autenticação no padrão da 42B5A: Iron Session + `users_v2.company_id` + Supabase **service role só no server**.

## 3. Validações implementadas
- `name` (obrigatório no POST, ≤120), `destination_ref` (obrigatório no POST, ≤500).
- `destination_type` ∈ {whatsapp_group, whatsapp_individual, email, internal_queue, webhook}.
- `channel_provider` ∈ {zapi, evolution, meta_cloud, manual} (default `manual`).
- `priority_order`/`silence_minutes` inteiros ≥ 0; `is_primary`/`fallback_enabled`/`is_active` boolean.
- `active_hours` object; `escalation_rules` array; `metadata` object.
- PATCH é parcial (só campos enviados, whitelist); 400 se nenhum campo válido.
- 400 claro em qualquer valor inválido.

## 4. Estratégia de mascaramento (`display_ref`)
Calculado no server por `maskDestinationRef(ref, type)`:
- Grupo WhatsApp `…@g.us`: `120363422850006552@g.us` → `120363****6552@g.us`.
- E-mail: `suporte@corretora.com.br` → `su****@corretora.com.br`.
- URL/webhook: `webhook: <host>` (ou "webhook configurado").
- Telefone: `5547999999999` → `5547****9999`.
- Fallback: `destino configurado`.

## 5. Validação de `tenant_connection_id`
Se enviado (não-null), `tenantConnectionBelongsToCompany()` confirma que a `tenant_connections.id` existe **e pertence ao mesmo company_id**; senão 400. (O segredo continua no Vault; aqui só a referência.)

## 6. Destino primário
Índice único parcial garante **no máximo 1 primário ativo por corretora**. Antes de criar/atualizar com `is_primary=true`, `demoteActivePrimaries()` desmarca os primários ativos da corretora (exceto o próprio no PATCH). Conflito de unicidade (`23505`) → **409** com mensagem clara.

## 7. Confirmações de segurança
- **company_id sempre derivado do usuário logado**, nunca do body; todos os GET/PATCH/DELETE filtram por `company_id`.
- **`destination_ref` cru NUNCA é retornado** — `serializeDestination()` remove o campo e expõe `has_destination_ref: true` + `display_ref` mascarado.
- Nunca retorna token/segredo/credencial (não existem nesta tabela; ficam no Vault).
- Service role só no server. Logs seguros: ids/type/provider/contagens — **nunca** destination_ref/telefone completo/PII.

## 8. O que NÃO foi feito (fora de escopo)
UI; SQL/migration; envio WhatsApp/externo; `handoff_dossier`; `approval_request`; backend Python; alteração de banco/Supabase/RAG/prompts/agentes.

## 9. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema | ✅ nenhum |
| backend Python / Supabase no client | ✅ nenhum |
| RAG/prompts/agentes/WhatsApp/envio externo/UI | ✅ nenhum |
| segredo/PII no diff | ✅ nenhum |

## 10. Deploy recomendado
- **Web apenas** (Next route handlers). Sem backend Python, sem SQL/migration.

## 11. Testes manuais (após deploy Web)
1. **GET** `/api/attendance/support-destinations` → `{ "destinations": [] }`.
2. **POST** com `{name, destination_type:'whatsapp_group', channel_provider:'manual', destination_ref:'120363422850006552@g.us', is_primary:true, priority_order:1, silence_minutes:10, ...}` → 201; `is_primary:true`; **sem** `destination_ref` na resposta; `display_ref` mascarado (`120363****6552@g.us`); `has_destination_ref:true`.
3. **GET** → 1 destino.
4. **PATCH** `{ silence_minutes: 15 }` → 200; `silence_minutes:15`.
5. **DELETE** → 200 `{ ok: true }`; destino fica `is_active:false`.
6. **Chat Core** inalterado (CORE-001/006/007).

## 12. Próximos passos
1. **42H3** — UI em **Personalização → Corretora → Suporte humano** consumindo esta API.
2. **42H4** — gerador de `handoff_dossier`.
3. **42H5** — copiar/dry-run de handoff no detalhe do caso (HITL via `approval_requests`).
4. Depois: **42B5B** (Corridor Runtime Step Engine), **42B6** (Dispatch + WhatsApp dry-run/HITL).
