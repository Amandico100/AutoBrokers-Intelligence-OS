# 42X4 — Provider Adapter Homologation Harness (Z-API, Evolution Go, Meta Cloud) Report

> **Status:** concluído · testes offline **621 verdes** (63 provider-adapters + 32 alignment + 61 registry + 42 outbox + 31 execution + 42 engine + 350 anteriores) · `typecheck` EXIT=0 · build verde · **NENHUMA chamada de API real** (`canSendReal=false` em todos os adapters) · **sem token/destino cru** · documentação oficial consultada.
> **Data:** 2026-06-17 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Fontes oficiais consultadas (2026-06)
- **Z-API** — https://developer.z-api.io/ (e `llms.txt`). Envio de texto via REST; **header `Client-Token`**; instance id + token na URL; resposta com `zaapId`/`messageId`/`id`; webhooks de status (sent/received/delivered/read).
- **Meta WhatsApp Cloud API** — https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages. `POST https://graph.facebook.com/{version}/{phone_number_id}/messages`; `Authorization: Bearer`; body `{ messaging_product:"whatsapp", recipient_type:"individual", to, type:"text", text:{ body, preview_url } }`; template `{ type:"template", template:{ name, language:{code}, components } }`; resposta `messages[].id` + `message_status`.
- **Evolution** — https://docs.evolutionfoundation.com.br/ + referência da Evolution API (`doc.evolution-api.com`, Postman v2). Evolution API: `POST {serverUrl}/message/sendText/{instance}`, header **`apikey`**, body `{ number, text }` (v2). **Evolution Go** (gateway de alta performance) é referenciado pela Evolution Foundation, mas o **endpoint exato do gateway Go não está confirmado oficialmente** no que consegui acessar → tratado como `partial`/`research_required`.

## 2. Status por provider
| provider | research_status | o que está validado | pendência |
|---|---|---|---|
| **zapi** | `verified` | endpoint send-text, header Client-Token, body `{phone,message}`, parse de `zaapId/messageId/id`, parse de webhook de status | credenciais reais no Vault; homologação |
| **meta_cloud** | `verified` | endpoint graph/messages, Authorization Bearer, body text + template, parse `messages[].id`/status, regra de template fora da janela 24h | phone_number_id + token no Vault; templates aprovados |
| **evolution_go** | `partial` | shape da família Evolution API v2 (`/message/sendText/{instance}`, header `apikey`, `{number,text}`) | **endpoint do gateway Evolution Go não confirmado** — `research_required` antes de real |
| **manual** | `verified` | sem envio automático (handoff humano) | — |

## 3. Por que nada envia real
`canSendReal=false` em **todos** os adapters; `send()` real não existe — só `mockSend` (que retorna `sent:false, mock:true`). Nenhuma linha chama Z-API/Evolution/Meta. O harness só **valida** config/payload, **simula** o envio e **parseia** respostas/webhooks. Combinado com os gates do 42X2 (`send_allowed=false`) e o registry do 42X3, o envio real é impossível neste batch.

## 4. Arquivos criados/alterados
- `lib/attendance/provider-adapters.ts` (**novo**, puro, self-contained) — `InsurerMessagingProviderAdapter` + adapters zapi/meta_cloud/evolution_go/manual; `validateConfig`/`validatePayload`/`buildTextPayload`/`mockSend`/`parseSendResponse`/`parseWebhook`; `PROVIDER_ERROR_CODES`; `buildProviderHomologationChecklist`; `summarizeProviderHarness`.
- `app/api/admin/insurer-action-channels/[configId]/homologation-check/route.ts` (**novo**) — diagnóstico do harness por config (POST), sanitizado, `can_send_real:false`.
- `lib/attendance/action-engine.ts` (**alterado**) — `BuildOutboxInput.provider_validation` + merge em `payload_sanitized`.
- `app/api/attendance/cases/[caseId]/runtime/action-outbox/prepare/route.ts` (**alterado**) — anexa `summarizeProviderHarness` ao outbox.
- `scripts/attendance-provider-adapters-homologation.test.mjs` (**novo**, 63 testes) + `package.json` (`test:provider-adapters`).
- `docs/canon/design/2026-06-claude-design/42X4-...md` (este).

## 5. Interface do adapter
`InsurerMessagingProviderAdapter`: `provider_key`, `label`, `canSendReal:false`, `research_status`, `docs_url`, `validateConfig`, `validatePayload`, `buildTextPayload`, `mockSend`, `parseSendResponse`, `parseWebhook?`. O adapter **não decide cobertura nem se pode enviar** — só prepara/valida/transporta (mock) quando os gates permitirem (eles nunca permitem neste batch).

## 6. Payload shapes usados (sandbox, mascarados)
- **zapi**: `POST https://api.z-api.io/instances/{instanceId}/token/{token}/send-text`, headers `[Content-Type, Client-Token]`, body `{ phone: ****1234, message: <mascarado> }`.
- **meta_cloud**: `POST https://graph.facebook.com/{version}/{phoneNumberId}/messages`, headers `[Authorization, Content-Type]`, body `{ messaging_product:"whatsapp", recipient_type:"individual", to:****1234, type:"text", text:{ body:<mascarado>, preview_url:false } }`.
- **evolution_go**: `POST {serverUrl}/message/sendText/{instance}` (shape Evolution API v2; **gateway Go a confirmar**), headers `[Content-Type, apikey]`, body `{ number:****1234, text:<mascarado> }`.
- **manual**: `human_handoff`, sem endpoint.
Headers guardam só **nomes** (nunca valores/tokens); destino sempre **mascarado**; corpo com dígitos longos omitidos.

## 7. Error mapping (provider-neutro)
`invalid_destination`, `auth_missing`, `auth_failed_future`, `provider_unavailable`, `rate_limited`, `instance_disconnected`, `message_rejected`, `webhook_signature_invalid`, `unknown_provider_error`.

## 8. Checklist de homologação
`buildProviderHomologationChecklist(provider, ctx)` → 13 itens: `official_docs_reviewed`, `endpoint_documented`, `auth_model_documented`, `destination_format_validated`, `payload_shape_validated`, `webhook_status_handling_documented`, `error_mapping_implemented`, `mock_send_passing`, `real_credentials_in_vault`, `kill_switch_tested`, `approval_flow_tested`, `canary_send_planned`, `rollback_plan`. `ready_for_real_future` é **sempre false** no 42X4 (os 5 últimos itens são blockers até 42X5+).

## 9. Integração com o Outbox
`action-outbox/prepare` anexa `summarizeProviderHarness(provider, ctx)` ao `payload_sanitized.provider_validation`: `provider_research_status`, `provider_validation_status`, `provider_validation_errors`, `homologation_blockers`, `provider_mock_capable`, `can_send_real:false`. `send_allowed` continua `false`.

## 10. Diagnostic route
`POST /api/admin/insurer-action-channels/[configId]/homologation-check` → `provider`, `research_status`, `docs_url`, `config_validation`, `payload_validation`, `payload_preview` (mascarado), `mock_send`, `checklist`, `summary`, `blockers`, `can_send_real:false`. Exige admin; sem destino cru/token.

## 11. Testes que rodei (offline)
- `node scripts/attendance-provider-adapters-homologation.test.mjs` → **63/63**: registry (4 adapters, canSendReal false, research_status correto); zapi (config/payload/mock/parse/webhook); meta_cloud (shape text, template fora da janela, parse wamid); evolution_go (apikey, warning research_required); manual (handoff); checklist (blockers, ready_for_real_future false); harness summary; 9 error codes; sem vazamento de telefone/CPF em nenhum payload.
- Regressão: alignment **32**, registry **61**, outbox **42**, execution **31**, engine **42**, document **15**, vision/doc **21**, media **36**, knowledge **22**, policy-qa **37**, intent **39**, selection **32**, whatsapp-inbound **44**, dispatch **35**, coverage **33**, evidence **37** = **558**. **Total 621/621.**
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde.

## 12. Reteste (console admin, logado)
```js
// configId de uma config criada no admin (ex.: zapi allianz/electrician)
const r = await (await fetch(`/api/admin/insurer-action-channels/${configId}/homologation-check`, { method:'POST' })).json();
console.log(r.provider, r.research_status, r.can_send_real); // zapi, verified, false
console.log(r.mock_send.sent, r.mock_send.provider_message_id); // false, mock-...
console.log(r.checklist.ready_for_real_future, r.checklist.blockers); // false, [...]
```
**Esperado:** validação + mock + checklist com blockers; `can_send_real:false`; nada enviado.

## 13. Como ativar no futuro
Trocar `mockSend` por `sendReal` exigirá, por adapter: `canSendReal=true` homologado + credencial real no Vault (`tenant_connection`/`encrypted_secret_ref`) + flags do 42X2 (`EXTERNAL_ACTION_REAL_ENABLED` etc.) + `approval_requests` + rate-limit + kill switch + checklist 100% (incluindo canary + rollback). Tudo já modelado; falta só a homologação real e o transporte.

## 14. Critério de pronto
| Critério | Status |
|---|---|
| adapters por provider em harness | ✅ (zapi/meta/evolution_go/manual) |
| payloads validados | ✅ |
| mockSend funciona | ✅ (`sent:false`) |
| diagnostic route existe | ✅ |
| outbox recebe provider validation | ✅ |
| canSendReal=false sempre | ✅ |
| nenhuma API real chamada | ✅ |
| docs oficiais consultadas (relatório prova) | ✅ (§1) |
| decisão de próximo provider real clara | ✅ (§15) |
| testes verdes | ✅ 621/621 |

## 15. Decisão de próximo provider real
- **Z-API → pode ir para 42X5** (primeiro adapter real controlado), **assim que a conta Z-API estiver paga/conectada**, atrás de flags + Vault + approval + kill switch + canary. É o provider `verified` e mais próximo de uso.
- **Meta Cloud → segue depois** do Z-API: `verified`, mas exige onboarding da Business Platform (phone_number_id, system user token, templates aprovados). Pronto para harness; real só após esse onboarding.
- **Evolution Go → fica para depois**: `partial` — o endpoint exato do gateway Go precisa ser confirmado na documentação/OpenAPI oficial antes de qualquer real (`research_required`). Mantido bloqueado.

## 16. Próximos passos
- **42X5 — primeiro adapter real controlado (Z-API)**: `sendReal` atrás de toda a pilha de segurança; canary único com aprovação humana explícita por mensagem.
- Se a Z-API seguir pausada: **Portal (Browserbase/Skyvern) dry-run** ou **SEC-001 (hardening final)**.
- Evolution Go: confirmar OpenAPI do gateway antes de promover de `partial`→`verified`.
