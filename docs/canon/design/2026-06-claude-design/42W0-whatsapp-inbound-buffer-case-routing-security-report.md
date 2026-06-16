# 42W0 — WhatsApp Inbound Buffer, Case Routing & Security Hardening Report

> **Status:** concluído · testes offline **149 verdes** (44 whatsapp-inbound + 35 dispatch + 33 coverage + 37 evidence) · `py_compile` OK · `typecheck` EXIT=0 · build verde · `git diff --check` limpo · **reusa a estrutura WhatsApp do Smith** (não recriou runtime) · **sem schema novo** · sem WhatsApp da seguradora/prestador · sem dispatch externo · **default não muda produção** (bridge gated por flag, envio real bloqueado por padrão).
> **Data:** 2026-06-16 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Inventário Smith WhatsApp (auditoria)
| Componente | Arquivo | Decisão |
|---|---|---|
| Webhook inbound Z-API | `backend/app/api/webhook.py` (`POST /api/v1/webhook/z-api`) | **reusei** (endurecido) |
| Buffer/debounce (Redis) | `backend/app/services/message_buffer_service.py` | **reusei** (já agrega N msgs, debounce/max-wait) |
| Flush do buffer | `backend/app/tasks/buffer_processor.py` (APScheduler 1s) | **reusei** (não toquei) |
| Provider adapter | `backend/app/services/whatsapp/{provider,zapi_provider,types}.py` | **reusei** (interface limpa + `SendResult` dry-run) |
| Shim de envio | `backend/app/services/whatsapp_service.py` | **reusei** |
| Segredos de integração | `backend/app/services/whatsapp/integration_secrets.py` (Fernet) | **reusei** (token/client_token cifrados; decrypt em memória) |
| Resolução company/agent | `backend/app/services/integration_service.py` | **reusei** (`get_integration_by_phone` já decifra + nunca loga valores) |
| Cérebro do atendimento | `lib/attendance/*` + `runtime/reply` | **reusei** (não criei runtime paralelo) |
| Core LangChain | `langchain_service.py` | **não toquei** (segue para agentes Core; atendimento externo desvia para o Attendance Runtime) |

**Reusei:** webhook, buffer, provider adapter, integration secrets, Attendance Runtime. **Não recriei:** runtime conversacional, provider, buffer. **Não toquei:** LangChain Core, schema/migrations, fluxo do dashboard.

## 2. Arquivos alterados/criados
- `lib/attendance/whatsapp-inbound.ts` (**novo**, puro) — normalização Z-API, máscara/hash de telefone, classificação de mídia, consolidação de buffer, **webhook auth mode**, **outbound policy (dry-run conservador)**.
- `lib/attendance/whatsapp-case-routing.ts` (**novo**, puro) — `resolveAttendanceCaseForWhatsAppInbound` + inferência de subcorredor.
- `app/api/attendance/whatsapp/inbound/route.ts` (**novo**) — **bridge interno** (chave Next↔Backend): case routing + persistência + delega ao `runtime/reply` + outbound dry-run.
- `app/api/attendance/cases/[caseId]/runtime/reply/route.ts` (**alterado**) — branch de **auth interna** aditivo (sessão do dashboard inalterada).
- `backend/app/api/webhook.py` (**alterado**) — **guard de auth do webhook**, **dedupe por messageId (Redis)**, **fork para o Attendance Runtime** (flag-gated, default OFF).
- `backend/app/core/config.py` (**alterado**) — settings 42W0 (auth mode/secret, dedupe TTL, flag de atendimento, bridge URL, internal key).
- `scripts/whatsapp-inbound.test.mjs` (**novo**) + `package.json` (**alterado**, `test:whatsapp-inbound`).
- `docs/canon/design/2026-06-claude-design/42W0-...md` (este).

## 3. Como reusei o WhatsApp do Smith
O webhook, o buffer e o provider continuam sendo os do Smith. A única mudança de fluxo: quando `ATTENDANCE_WHATSAPP_ENABLED=true` **e** o agente conectado é `agent_role='attendance'`, o `process_whatsapp_message_background` **desvia** do `LangChainService` (Core) para o **Attendance Runtime** via bridge, antes de salvar a mensagem (o bridge persiste). Com a flag desligada (default), nada muda.

## 4. Como conectei ao Attendance Runtime
`webhook.py` → (flag + attendance agent) → `POST /api/attendance/whatsapp/inbound` (bridge, chave interna) → case routing → cria/roteia `attendance_case` ligado à `conversation` existente → chama `POST /runtime/reply` (mesmo cérebro do dashboard, via **auth interna**) → resposta dry-run. O runtime/reply salva user+assistant em `messages`. **Nenhum prompt solto**; o Attendance Runtime governa. LLM nunca decide side-effects.

## 5. Buffer/debounce
**Reuso integral** do `message_buffer_service` (Redis) + `buffer_processor` (APScheduler): N mensagens do mesmo telefone numa janela curta viram **uma entrada consolidada** (`\n`), preservando ordem. Janela configurável por env (`BUFFER_DEBOUNCE_SECONDS=3`, `BUFFER_MAX_WAIT_SECONDS=10`, `BUFFER_TTL_SECONDS=60`). A consolidação também existe em TS puro (`consolidateBufferedMessages`) para o bridge/casos de teste. Ex.: "Oi" + "estou sem luz" + "só na cozinha" → `"Oi\nestou sem luz\nsó na cozinha"`.

## 6. Case routing
`resolveAttendanceCaseForWhatsAppInbound` (puro): case aberto não-final → `reply_existing`; case em `handoff` → `handoff_block` (registra inbound, **não responde**); case final/inexistente → `create_case`. Novo case: `channel='whatsapp'`, `conversation_id` existente, `assigned_agent_id`, corredor `allianz_residential_assistance/electrician` (subcorredor inferido só quando claro). Atendimento externo **sempre** vai ao Attendance Agent, nunca ao Core.

## 7. Dry-run por conexão
`resolveOutboundPolicy` (conservador): dry-run a menos que `environment='production'` **e** `external_send_authorized=true` **e** sem `DRY_RUN` global/integration. O bridge devolve `outbound.{dry_run, external_send_allowed}` e o texto; o webhook **só envia de verdade** se a política liberar — por padrão **não envia** (salva no histórico via reply, loga `outbound_dry_run`). `external_action_sent` do dispatch (42B6) continua intocado/false.

## 8. Segurança (P0/P1)
- **Webhook auth guard** (`WHATSAPP_WEBHOOK_AUTH_MODE`): `disabled` (dev, com warning) | `shared_secret` (header `X-Webhook-Secret`/`?secret=`, compare via `hmac.compare_digest`) | `provider_signature` (pronto p/ quando a Z-API assinar). Default `disabled` para não quebrar o deploy atual; **produção deve usar shared_secret**.
- **Dedupe por messageId**: Redis `SET NX` + TTL (`WHATSAPP_DEDUPE_TTL_SECONDS=120`) → duplicado é ignorado (`inbound_deduped`).
- **Token/client_token**: infra de cifra já existe (`integration_secrets`, Fernet); `integration_service` decifra só em memória e **nunca loga valores**. Nenhum endpoint/log deste batch retorna token/client_token. Telefone sempre mascarado; payload bruto nunca logado.
- **PII**: bridge/respostas usam telefone mascarado + hash pseudônimo; nome só primeiro nome; sem CPF/endereço completo/URL de mídia.

## 9. Observabilidade
`diagnostics.events[]` sanitizados no bridge: `inbound_received`, `case_routing:<action>`, `case_created`, `runtime_reply_called`, `outbound_dry_run`/`outbound_sent`, `handoff_blocked_auto_reply`, `media_ack`. Webhook loga `webhook_auth_failed`, `inbound_deduped`, roteamento de atendimento — tudo sem telefone cru/CPF/token/payload.

## 10. Mídia (sem travar)
Bridge classifica `audio|image|document|location`; sem texto → **ack humano seguro** (`mediaAckMessage`, não vaza URL) + registra referência. Não manda mídia bruta a LLM nem à seguradora. **TODO 42M0 — Media Evidence Pipeline** (transcrição/visão completas) documentado.

## 11. Human handoff
Case em `handoff` → bridge registra o inbound e **não responde** (`handoff_blocked_auto_reply`). O webhook já respeita `HUMAN_REQUESTED` (pula IA). Runtime que decidir handoff marca o case; sem auto-resposta posterior.

## 12. Testes que rodei (eu mesmo)
- `node scripts/whatsapp-inbound.test.mjs` → **44/44**: normalização+máscara (sem telefone/sobrenome crus), hash estável, classificação (texto/áudio/imagem/grupo/fromMe/vazio), identificadores mínimos, buffer consolidado em ordem, webhook auth (disabled/shared_secret ok/erro/faltando/signature), outbound policy (dry-run conservador, produção+autorizado envia), case routing (reply/handoff/closed/none), inferência de subcorredor.
- Regressão: dispatch **35/35**, coverage **33/33**, evidence **37/37**.
- `python -m py_compile` (webhook + config) OK · `npx tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo. Chat web/dashboard e fluxos InfoCap/dispatch **não foram alterados** (apenas auth aditiva no reply + fork gated no webhook).

## 13. Scripts de validação manual/dry-run (placeholders, sem segredo real)
```bash
# A) Webhook inbound texto (DRY_RUN global no backend). Em shared_secret, envie o header.
curl -sX POST "$BACKEND/api/v1/webhook/z-api" -H 'Content-Type: application/json' \
  -H "X-Webhook-Secret: <WHATSAPP_WEBHOOK_SECRET>" \
  -d '{"connectedPhone":"<CONN>","phone":"<PHONE>","messageId":"MID-1","text":{"message":"estou sem luz"}}'
# → {"status":"buffered"}  (flush em ~3s pelo buffer_processor)

# B) 3 mensagens rápidas → 1 consolidada (mesmo phone, dentro da janela):
for m in "Oi" "estou sem luz" "só na cozinha"; do \
  curl -sX POST "$BACKEND/api/v1/webhook/z-api" -H 'Content-Type: application/json' \
   -H "X-Webhook-Secret: <SECRET>" -d "{\"connectedPhone\":\"<CONN>\",\"phone\":\"<PHONE>\",\"messageId\":\"MID-$RANDOM\",\"text\":{\"message\":\"$m\"}}"; done
# → runtime recebe "Oi\nestou sem luz\nsó na cozinha"

# C) Mesmo messageId duas vezes → segunda é ignorada:
curl ... -d '{"...":"...","messageId":"DUP-1","text":{"message":"x"}}'   # 1ª: buffered
curl ... -d '{"...":"...","messageId":"DUP-1","text":{"message":"x"}}'   # 2ª: {"status":"ignored","reason":"duplicate"}

# D) Bridge direto (interno) — confirma case routing + outbound dry-run:
curl -sX POST "$APP/api/attendance/whatsapp/inbound" -H 'Content-Type: application/json' \
  -H "X-AutoBrokers-Internal-Key: <BACKEND_INTERNAL_API_KEY>" \
  -d '{"company_id":"<CO>","agent_id":"<AG>","user_id":"<U>","conversation_id":"<CV>","phone":"<PHONE>","text":"estou sem luz"}'
# → {"ok":true,"action":"create_case"|"reply_existing","auto_reply":"...","outbound":{"dry_run":true,"sent":false}}
```
**Habilitar o fluxo de atendimento por WhatsApp:** `ATTENDANCE_WHATSAPP_ENABLED=true`, `ATTENDANCE_BRIDGE_URL=<app>/api/attendance/whatsapp/inbound`, `BACKEND_INTERNAL_API_KEY=<mesma chave do app>`. Envio real só com `environment=production` + `external_send_authorized=true` (default permanece dry-run).

## 14. Pendências para segurança/produção (42W1/SEC)
- **Webhook signature real** da Z-API (hoje só `shared_secret` disponível); `provider_signature` está pronto mas inerte até a Z-API assinar.
- **Migrar credenciais legadas plaintext**: o decrypt tolera plaintext legado (com warning); recadastrar integrações pela camada cifrada para eliminar plaintext residual. **Listar/migrar** as integrations com token não-ciphertext.
- **Outbound real controlado** (42W1): habilitar envio por conexão homologada, com observabilidade e rate-limit.
- **Mídia (42M0)**: transcrição de áudio (já há `audio_service`) e visão de imagem dentro do Attendance Runtime, com evidence pack.
- **Bridge auth**: hoje compartilha a `BACKEND_INTERNAL_API_KEY`; avaliar chave dedicada + assinatura.

## 15. Critério de pronto
| Critério | Status |
|---|---|
| usa estrutura WhatsApp do Smith | ✅ |
| não cria runtime paralelo | ✅ (delega ao `runtime/reply`) |
| inbound normaliza payload | ✅ |
| buffer/debounce funciona | ✅ (reuso) |
| case routing funciona | ✅ |
| Attendance Runtime recebe mensagem | ✅ (bridge → reply, flag-gated) |
| resposta volta via dry-run/outbound seguro | ✅ |
| human_handoff bloqueia auto resposta | ✅ |
| logs sanitizados | ✅ |
| token não vaza | ✅ |
| relatório aponta riscos | ✅ (§14) |
| testes verdes | ✅ 149/149 |

## 16. Decisão: seguir para 42W1?
**Sim — pode seguir para 42W1 (WhatsApp Attendance Runtime Controlled Test).** A fundação está pronta e segura: inbound normalizado, buffer/dedupe reusados, case routing, bridge para o runtime, dry-run conservador, handoff respeitado, segurança endurecida — tudo **sem alterar o fluxo atual** (flag OFF) e **sem envio externo**. O 42W1 deve: ligar a flag em sandbox, rodar uma conversa real ponta-a-ponta (texto → CPF → InfoCap → coverage → dispatch dry-run) por WhatsApp em dry-run, validar respostas humanizadas e só então planejar o envio real homologado.

## 17. Checks
| Check | Resultado |
|---|---|
| `node scripts/whatsapp-inbound.test.mjs` | ✅ 44/44 |
| dispatch/coverage/evidence (regressão) | ✅ 35/33/37 |
| `python -m py_compile` (webhook+config) | ✅ OK |
| `npx tsc --noEmit` | ✅ EXIT=0 |
| `npm run build` | ✅ verde |
| `git diff --check` | ✅ limpo |
| runtime paralelo · n8n orquestrador · seguradora/prestador · dispatch externo · schema · PII/token exposto · quebra dashboard | ✅ nenhum |
