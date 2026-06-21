# 42X5B — WhatsApp Production Readiness Final (Resulta) + Canonical Outbound Gate + Consent

> Deixa o WhatsApp pronto em código/segurança/política para o piloto da Resulta, **sem mensagem real, sem token, sem pagamento**. Reaproveita a infraestrutura existente (webhook backend + bridge Next + provider) — **nenhuma estrutura paralela criada**.
> **Data:** 2026-06-21 · **Modelo:** Claude Opus 4.8 · base: `7afe90d`

## Declaração
```
WHATSAPP CORE RUNTIME READY: SIM
RESULTA PILOT BINDING CANONICAL: SIM
ATTENDANCE AGENT SEPARATE FROM CORE: SIM
Z-API REAL ADAPTER CODE READY: SIM (provider backend com DRY_RUN + mascaramento; política canônica adicionada)
Z-API REAL SEND: CONTINUA BLOQUEADO
PUBLIC WEBHOOK SECURITY READY: SIM (JÁ EXISTIA no backend — reusado, NÃO recriado)
TENANT RESOLUTION SERVER-SIDE: SIM (get_whatsapp_integration; nunca confia em company_id do payload)
OUTBOX / IDEMPOTENCY / RETRY READY: PARCIAL (idempotência por messageId via Redis OK; retry usa background task — fila durável = futuro)
CONSENT / OPT-IN READY: SIM (modelo puro + integrado à política; storage em metadata; UI/CRUD = dashboard tenant depois)
RESULTA ALLIANZ ELETRICISTA DRY-RUN CERTIFIED: PARCIAL (corredores global ativos + agente criado inativo; E2E live após ativar o agente)
NO REAL MESSAGE SENT: SIM
NO LEGACY DASHBOARD USED: SIM
NO PARALLEL ARCHITECTURE CREATED: SIM
NEXT STEP AFTER PAYMENT: 42X5C — INBOUND CANARY, THEN ONE OUTBOUND CANARY WITH HITL
```

## ⚠️ Correção ao plano do GPT (auditoria de código)
O GPT pediu **criar uma entrada pública de webhook Z-API com resolução de tenant server-side** (Parte A2). **Isso JÁ EXISTE no backend Python** e está completo — recriar no Next seria a estrutura paralela proibida. Auditei e confirmei em `backend/app/api/webhook.py`:
- `POST /api/v1/webhook/z-api` — webhook público.
- Auth: `WHATSAPP_WEBHOOK_AUTH_MODE` = `shared_secret` (header `x-webhook-secret` / `?secret=`) ou `provider_signature`.
- **Dedup por `messageId`** (Redis `SET NX` + `WHATSAPP_DEDUPE_TTL_SECONDS`) — idempotência inbound.
- **Resolução de tenant server-side** via `integration_service.get_whatsapp_integration` → `company_id` (não confia no payload).
- `get_or_create_conversation(phone, company_id)`.
- Bridge gated (42W0) → `POST /api/attendance/whatsapp/inbound` (Next, interno) → runtime (case + corredor + dry-run).
- **O backend OBEDECE ao `outbound.external_send_allowed`/`dry_run` que o bridge Next retorna** (`webhook.py` ~l.306). Logo, o bridge é a fonte única da política de envio.
→ Portanto **NÃO reconstruí webhook/tenant/idempotência**. Implementei só o que faltava de verdade: política canônica de envio + consentimento.

## O que implementei (genuinamente faltante)
### 1. Política CANÔNICA de envio — `lib/attendance/whatsapp-outbound-gate.ts` (puro, DI)
`evaluateWhatsAppOutboundGate` resolve toda a ambiguidade num só lugar: `GLOBAL_KILL_SWITCH` + `ATTENDANCE_WHATSAPP_DRY_RUN` + `WHATSAPP_ATTENDANCE_OUTBOUND_REAL_ENABLED` + `EXTERNAL_ACTION_REAL_ENABLED` + `INSURER_WHATSAPP_REAL_SEND_ENABLED` (canal seguradora) + autorização explícita + **consentimento** + **approval (se proativo)** + sandbox. Falha fechado (dry-run). Como o backend obedece ao bridge, isto vira a política única real.
### 2. Consentimento/opt-in — `lib/attendance/whatsapp-consent.ts` (puro)
`evaluateConsent`: `opt_out` bloqueia sempre; resposta a inbound dentro da janela de sessão (24h) é permitida (consentimento implícito de atendimento iniciado pelo segurado); envio **proativo/campanha exige opt-in explícito**. Storage canônico em `attendance_cases.metadata.consent` (sem tabela nova).
### 3. Bridge inbound usa a política canônica
`app/api/attendance/whatsapp/inbound/route.ts` agora compõe `getProductionFlags` + consent + `evaluateWhatsAppOutboundGate` para o `outbound` (kill switch + production gates + consentimento). Antes usava só `resolveOutboundPolicy` (ignorava kill switch/gates/consent). Mais restritivo → seguro (nunca afrouxa).
### 4. Binding canônico da Resulta (via MCP, read-mostly)
- Resulta Seguros: ativa, `company_id=04b5cdbc-04cd-4ddf-8e4b-f43efb062fab` (confere com o dashboard).
- **Criado** o Attendance Agent canônico (`agent_role=attendance`, `agent_audience=insured_external`, **`is_active=false` / dry-run**, openai/gpt-4o-mini, prompt PT-BR seguro) — id `aee852d3-c52f-4b52-b71a-5078ad8662c2`. **Distinto** do agente interno do corretor. Inativo até o canary; pronto para personalizar.
- Corredores `allianz_residential_assistance` + subcorredor `electrician`: **globais e ativos** → já disponíveis a todos os tenants (a query do inbound usa `company_id is null OR =tenant`). Nenhuma duplicação/ativação por tenant necessária para corredores globais.

## Segurança (mantida)
- `external_send_allowed=true` só com TODAS as condições (kill switch off + flags + autorização + consentimento + approval se proativo). Default = dry-run.
- Backend já mascara telefone/nome/conteúdo e nunca loga token/URL/secret; provider em DRY_RUN.
- Nenhuma mensagem real; nenhum segredo; nenhuma flag ligada; agente criado **inativo**.

## Testes
- Novos: `attendance-whatsapp-outbound-gate` **12**, `attendance-whatsapp-consent` **11**.
- Regressão: `whatsapp-inbound` 44, `action-outbox` 42, `security-production-gates` 31 — verdes.
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde.

## 3 testes live (sem Z-API paga) para o Founder
1. **Simulate inbound (dry-run):** admin logado → `POST /api/attendance/whatsapp/simulate-inbound` com `{ from_phone:"5511999999999", text:"Meu chuveiro queimou e estou sem energia em parte da casa." }` → cria case Resulta, seleciona Allianz Residencial/Eletricista, responde dry-run, **não envia**.
2. **Preflight:** `GET /api/attendance/whatsapp/preflight` → mostra readiness sanitizado (chave interna, flag de envio, integração, agente attendance, InfoCap), sem segredo.
3. **Gate/consent (terminal):** `npm run test:whatsapp-outbound-gate` e `test:whatsapp-consent` → 12/11 verdes (kill switch/flags/consent/approval bloqueiam; default dry-run).

> Para o (1) rotear ao Attendance Runtime, ative o Attendance Agent da Resulta (hoje `is_active=false`). Enquanto inativo, o fluxo cai em triagem/genérico.

## Checklist operacional após pagamento (resumo; detalhe no runbook)
1. Reativar Z-API + conectar número Resulta.
2. Segredos Z-API no Vault/integração (server-side).
3. Webhook Z-API → `…/api/v1/webhook/z-api` com `WHATSAPP_WEBHOOK_AUTH_MODE=shared_secret` + secret.
4. Ativar o Attendance Agent da Resulta.
5. Inbound canary com `ATTENDANCE_WHATSAPP_DRY_RUN=true` (recebe, não responde real).
6. Outbound canary (1 msg, número consentido, janela de flags + `external_send_authorized=true`).
7. Desligar flags + kill switch on.
Detalhes/rollback/kill switch: `42X5B-zapi-resulta-production-runbook.md`.

## Deferido (registrado, não feito agora — correto)
- **Provedor Evolution Go** (gratuito/multi-tenant): o `preflight` já reconhece `evolution`/`wppconnect`; entra como provider adicional no mesmo registry (batch próprio).
- **Números de assistência das seguradoras (GLOBAIS)** e **links dos portais**: gravar no **corredor global** (fonte `docs/intake/sinistro e assistencias - contatos.xlsx`). Registrado para o próximo batch de dados globais (Founder pediu para gravar, fazer depois).
- **Fila/outbox durável + retry** (hoje background task + idempotência): evolução pós-canary.
- **UI de consentimento + Tenant Activation Center** (corretora conecta WhatsApp/portais no próprio dashboard): batch dedicado.
- **Provisionamento automático de Attendance Agent para todas as empresas**: auditar/planejar após o piloto.

## NEXT STEP AFTER PAYMENT
42X5C — inbound canary, depois UM outbound canary com HITL e kill switch acessível.
