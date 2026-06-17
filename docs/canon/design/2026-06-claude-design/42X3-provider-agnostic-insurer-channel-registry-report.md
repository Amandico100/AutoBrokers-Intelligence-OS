# 42X3 — Provider-Agnostic Insurer Channel Registry, Admin Configuration & Homologation Sandbox Report

> **Status:** concluído · testes offline **526 verdes** (61 channel-registry + 42 outbox + 31 execution + 42 engine + 350 anteriores) · `typecheck` EXIT=0 · build verde · **sem schema novo** (usa `tenant_connections.connection_config`) · **provider-agnostic** (Z-API/Evolution Go/Meta Cloud/manual) · **NENHUM envio real** (`send_real_allowed=false` · `canSendReal=false` sempre) · **sem PII / sem destino cru / sem token**.
> **Data:** 2026-06-17 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. O que muda do 42X2 para o 42X3
O 42X2 entregou outbox + gates + adapter skeleton (preso conceitualmente a "WhatsApp"). O 42X3 generaliza isso: um **registry global de providers** de mensageria de seguradora (Z-API, Evolution Go, Meta Cloud, manual, future_custom), uma **camada de configuração admin** por seguradora/corredor/subcorredor/corretora, **capability matrix**, **payload builders por provider** e **estados de homologação** — tudo em sandbox. A arquitetura deixa de ser "Z-API + Allianz/Eletricista" e passa a ser **multi-provider, multi-seguradora, multi-corredor, multi-tenant**. Z-API vira **um provider**, não a arquitetura.

## 2. Arquivos criados/alterados
- `lib/attendance/insurer-channel-registry.ts` (**novo**, puro, self-contained) — `getInsurerMessagingProviderRegistry`, `resolveProviderCapabilities`, `validateProviderKey`, `buildInsurerChannelConfig`, `sanitizeInsurerChannelConfig`, `resolveActiveInsurerChannelConfig`, `evaluateInsurerChannelHomologation`, `buildProviderPayload`, `safeChannelConfigSummary`.
- `lib/attendance/insurer-channel-store.ts` (**novo**) — persistência defensiva em `tenant_connections.connection_config.insurer_action_channels[]` (sem schema novo; degrada com `vault_not_available`).
- `app/api/admin/insurer-action-channels/route.ts` (**novo**) — GET (lista sanitizada) + POST (cria).
- `app/api/admin/insurer-action-channels/[configId]/route.ts` (**novo**) — PATCH + DELETE.
- `app/admin/insurer-action-channels/page.tsx` (**novo**) — UI admin mínima (lista, adicionar, remover, aviso "envio real bloqueado").
- `lib/attendance/action-engine.ts` (**alterado**) — `buildOutboxEntry` aceita `channel`/`provider`/`destination_ref_masked`/`provider_payload`/`config_id` da config resolvida.
- `app/api/attendance/cases/[caseId]/runtime/action-outbox/prepare/route.ts` (**alterado**) — resolve config ativa, gera provider payload e alimenta o outbox.
- `scripts/attendance-insurer-channel-registry.test.mjs` (**novo**, 61 testes) + `package.json` (`test:insurer-channel-registry`).
- `docs/canon/design/2026-06-claude-design/42X3-...md` (este).

## 3. Providers suportados
| provider | canal | text | media | template | webhook | group | status | real (futuro) |
|---|---|---|---|---|---|---|---|---|
| `zapi` | insurer_whatsapp | ✅ | ✅ | — | ✅ | ✅ | available | ✅ |
| `evolution_go` | insurer_whatsapp | ✅ | ✅ | — | ✅ | ✅ | future | ✅ |
| `meta_cloud` | insurer_whatsapp | ✅ | ✅ | ✅ | ✅ | — | future | ✅ |
| `manual` | manual | — | — | — | — | — | manual | — |
| `future_custom` | insurer_whatsapp | ✅ | — | — | — | — | future | ✅ |
`resolveProviderCapabilities(key)` devolve a matriz; provider desconhecido → `found:false`.

## 4. Como configurar no admin
Tela `/admin/insurer-action-channels`: lista os canais por seguradora, mostra provider, corredor/subcorredor, status de homologação, modo, **destino mascarado** e o aviso "envio real bloqueado". Formulário cria um canal (seguradora + corredor/sub opcionais + provider + destino). APIs: `GET/POST /api/admin/insurer-action-channels`, `PATCH/DELETE /api/admin/insurer-action-channels/[configId]`. Exigem sessão admin/usuário com company; validam provider; **nunca** retornam destino cru/token; `send_real_allowed` sempre `false`.

## 5. Contrato `InsurerActionChannelConfig`
`config_id, company_id, insurer_key, corridor_key?, subcorridor_key?, channel, provider_key, mode (sandbox|dry_run|future_real_disabled), destination_ref_masked, destination_kind (phone|group|portal|email|manual), homologation_status (not_started|sandbox_ready|awaiting_credentials|awaiting_approval|homologated_future), capabilities, playbook_id?, priority, is_active, send_real_allowed:false, notes, created_at, updated_at`. O **destino cru é mascarado em `buildInsurerChannelConfig` e nunca armazenado**.

## 6. Persistência (sem schema novo)
`tenant_connections.connection_config.insurer_action_channels[]` (modelo Vault). O store faz find-or-create de uma `tenant_connection` determinística por company (`autobrokers_insurer_action_channels`, usando o `connector_template` seedado `whatsapp_zapi`). Se o Vault não estiver migrado no ambiente, o store lança `vault_not_available` e as rotas degradam com clareza (sem crash), espelhando o padrão defensivo do 42X2.

## 7. Como a config integra com o Action Engine
No `action-outbox/prepare`: resolve-se a config ativa mais específica (`resolveActiveInsurerChannelConfig`) por `insurer_key`/`corridor_key`/`subcorridor_key`; o canal do provider é mapeado para o `ActionChannel` do engine (`manual`→`human_broker_manual`); gera-se o `buildProviderPayload` (mascarado) e tudo é passado a `buildOutboxEntry` (`channel`/`provider`/`destination_ref_masked`/`provider_payload`/`config_id`). **Sem config ativa → cai em `human_broker_manual`** (comportamento atual preservado). O `send_allowed` continua `false` (gates do 42X2).

## 8. Resolução da config mais específica
`resolveActiveInsurerChannelConfig` pontua: subcorredor exato (+4) > corredor exato (+2) > seguradora. Uma config que exige um corredor/subcorredor **diferente** do contexto é descartada. Empate → menor `priority`, depois mais recente. Testado: subcorredor vence; sem sub-match cai no corredor; seguradora sem config → `null`; config inativa ignorada.

## 9. Payload builders por provider
`buildProviderPayload(provider_key, ctx)` devolve o shape sanitizado: `zapi` (`send-text`/`send-image`), `evolution_go` (`sendText`/`sendMedia`), `meta_cloud` (`messaging_product:whatsapp`, `type:text`), `manual` (`handoff:true`). **Todos** com `dry_run:true`, `sent:false`, destino mascarado, corpo com dígitos longos omitidos, **sem token** — e **nunca chamam API**. Provider desconhecido → `supported:false`.

## 10. Estados de homologação
`evaluateInsurerChannelHomologation(config, {credentialPresent})`: `manual`→`sandbox_ready`; sem destino→`destination_missing`; com destino sem credencial→`missing_credentials`; com destino+credencial→`sandbox_ready`. **Nenhum** estado libera envio real: `send_real_allowed:false` e o blocker `real_send_disabled_42x3` sempre presente.

## 11. Como suporta Z-API / Evolution Go / Meta Cloud
Cada um é um `provider_key` no registry com sua capability matrix, `auth_model` e `destination_format` próprios; o payload builder gera o shape específico de cada API. Trocar/escolher provider = mudar a config no admin — **sem tocar no Action Engine**. Meta Cloud já prevê `template` e ausência de grupos; Evolution Go espelha a Z-API mas marcado `future`.

## 12. Como adicionar nova seguradora/corredor
1) Criar (se necessário) o playbook no `action-engine` (corredor escolhe playbook). 2) Cadastrar a config no admin (seguradora + corredor/sub + provider + destino). 3) Pronto — o outbox passa a usar a config. **Adicionar seguradora/corredor não exige recriar engine nem provider.**

## 13. Por que ainda não envia real
`send_real_allowed:false` em toda config/summary/resposta; `canSendReal=false` nos adapters; payloads `dry_run`; nenhum caminho chama Z-API/Evolution/Meta. O envio real (42X4+) exigirá a soma do 42X2 (flags/kill switch/approval/rate-limit) com um adapter homologado por provider + `tenant_connection` `connected` + segredo no Vault.

## 14. Segurança/PII
Destino cru nunca é armazenado nem retornado (só `****1234`); token/client_token nunca aparece; payload só sanitizado; provider desconhecido e destino inválido bloqueiam. Testado: configs/summary/payloads sem destino cru e sem CPF.

## 15. Testes que rodei (offline)
- `node scripts/attendance-insurer-channel-registry.test.mjs` → **61/61**: registry (5 providers, status); capabilities; config build/sanitize (sem destino cru); resolveActive (mais específica/inativa/sem match); outbox usa config + fallback manual; payload builders (4 providers, sem envio/sem PII); homologation (4 estados, sempre bloqueado); summary sem PII.
- Regressão: outbox **42**, execution **31**, engine **42**, document **15**, vision/doc **21**, media **36**, knowledge **22**, policy-qa **37**, intent **39**, selection **32**, whatsapp-inbound **44**, dispatch **35**, coverage **33**, evidence **37** = **465**. **Total 526/526.**
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde.

## 16. Reteste (console admin, logado)
```js
const list = await (await fetch('/api/admin/insurer-action-channels')).json();
console.log(list.ok, list.configs); // sanitizado, send_real_allowed:false
const created = await (await fetch('/api/admin/insurer-action-channels', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ insurer_key:'allianz', corridor_key:'allianz_residential_assistance', subcorridor_key:'electrician', provider_key:'zapi', destination_ref:'5544999998888' })})).json();
console.log(created.config.destination_ref_masked, created.send_real_allowed); // ****8888, false
```
**Esperado:** config criada com destino **mascarado**, `send_real_allowed:false`; a próxima preparação de outbox para esse caso passa a usar provider `zapi` e o payload sandbox.

## 17. Critério de pronto
| Critério | Status |
|---|---|
| registry provider-agnostic existe | ✅ (5 providers) |
| admin pode configurar canal | ✅ (GET/POST/PATCH/DELETE + UI) |
| outbox usa config | ✅ (prepare resolve + payload) |
| payloads provider-specific em sandbox | ✅ (zapi/evolution/meta/manual) |
| send real continua bloqueado | ✅ (`send_real_allowed=false` sempre) |
| serve a todos corredores/corretoras/providers | ✅ |
| testes verdes | ✅ 526/526 |

## 18. Próximos passos (42X4+)
- **42X4 — Insurer WhatsApp real adapter homologado** (por provider), ainda com envio bloqueado por default (flags + approval + Vault + rate-limit + kill switch).
- **42X5 — Primeiro envio real único**, aprovado manualmente, em canal controlado e observável.
- **42P0 (portal)**, **42V0 (voz/0800)**, **SEC-001 (hardening final)**.
