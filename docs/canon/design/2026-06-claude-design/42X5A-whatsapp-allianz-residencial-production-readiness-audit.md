# 42X5A — WhatsApp / Allianz Residencial — Production Readiness Audit (READ-ONLY)

> **Status:** auditoria read-only · **sem** enviar WhatsApp · **sem** Z-API pago/configurado · **sem** ligar flags. Mapeia o que falta para o piloto Allianz Residencial entrar em produção.
> **Data:** 2026-06-19 · **Modelo:** Claude Opus 4.8

## 0. Resumo
A espinha dorsal do atendimento WhatsApp **já existe e roda em dry-run/HITL**. O caminho crítico para monetizar (Allianz Residencial via WhatsApp) **não precisa de muito código novo** — precisa de: (a) ativar o provider real Z-API **gated** (42X5B), (b) um canary controlado (42X5C), (c) consentimento/opt-in e dashboard operacional. Nada disso deve ligar antes do gate + kill switch + HITL.

## 1. Inventário (o que existe hoje)
| Camada | Arquivo/rota | Estado |
|---|---|---|
| Inbound webhook | `app/api/attendance/whatsapp/inbound/route.ts` | **real** (recebe payload Z-API); exige `company_id`+`conversationId`+`phone`; auth via `checkWebhookAuth` |
| Inbound simulado | `app/api/attendance/whatsapp/simulate-inbound/route.ts`, `.../preflight/route.ts` | **real** (teste seguro sem webhook externo) |
| Normalização | `lib/attendance/whatsapp-inbound.ts` (`normalizeZapiInbound`, `classifyInboundEvent`, `consolidateBufferedMessages`) | **real** |
| Mascaramento PII | `maskPhone`, `phoneHash`, `safeName` | **real** (telefone/nome mascarados) |
| Roteamento de caso | `lib/attendance/whatsapp-case-routing.ts` (`resolveAttendanceCaseForWhatsAppInbound`) | **real** (vincula contato→conversa→case) |
| Multi-tenant | inbound carrega corredores `global + tenant` por `company_id` | **real** |
| Runtime atendimento | `runtime-*`, `corridor-runtime.ts`, `whatsapp-orchestration.ts`, reply/step/policy-lookup/policy-select | **real** (dry-run) |
| Allianz Residencial / Eletricista | corredores no banco (`corridors`, global+tenant) | **dados/registry** (validar seed do piloto) |
| InfoCap | `app/api/attendance/connectors/infocap/*` (setup/secret/probe/diagnostics) | **real read-only gated** (via Vault) |
| Policy QA / mídia | `policy-qa`, `attendance-media*` | **real** (dry-run) |
| Action Engine / Sandbox / Outbox | `action-engine.ts`, rotas `runtime/action-*` | **real (dry-run/HITL)** |
| Provider registry / harness | `insurer-channel-registry.ts`, `provider-adapters.ts`, harness 42X4 | **real** |
| Z-API provider | `backend/app/services/whatsapp/zapi_provider.py` | **real, mas em DRY_RUN** (não envia; mascara telefone; nunca loga token/URL/Client-Token) |
| Gate de envio | `resolveOutboundPolicy` + flags `INSURER_WHATSAPP_REAL_SEND_ENABLED` / `EXTERNAL_ACTION_REAL_ENABLED` / `GLOBAL_KILL_SWITCH` | **real (falha fechado)** |
| Handoff humano | `handoff-dossier`, `dispatch-dry-run` | **real (dry-run)** |

## 2. O que está SIMULADO (não real ainda)
- **Envio outbound**: `resolveOutboundPolicy` retorna `dry_run=true` a menos que `externalSendAuthorized===true` — ou seja, **default seguro = não envia**. O `ZApiProvider` simula envio quando DRY_RUN.
- **Corridor run** marca `external_action_allowed:false`, `hitl_required:true`, `mvp_mode:'dry_run_hitl'`.
- **Dispatch** para seguradora/prestador é dry-run (packet montado, não enviado).

## 3. O que falta implementar/decidir para produção
1. **Provider Z-API real gated (42X5B):** ligar o caminho real do `ZApiProvider` por trás do gate (`INSURER_WHATSAPP_REAL_SEND_ENABLED` + kill switch off + autorização por mensagem), idempotência por `message_id`, retry/fila, e nunca logar segredo.
2. **Webhook real protegido:** confirmar `checkWebhookAuth` em produção (token/HMAC) e o segredo no env (sem valor aqui).
3. **Opt-in/consentimento:** registrar consentimento do segurado antes de responder/enviar (LGPD).
4. **Dashboard operacional:** ver casos, status, HITL pendente, kill switch, logs sanitizados.
5. **Seed do piloto:** garantir corredor Allianz Residencial + subcorredor Eletricista ativos para a corretora-piloto.
6. **Idempotência/fila/retry** no outbound real (evitar duplicidade/perda).

## 4. Depende de PAGAR/CONFIGURAR (não agora)
- Conta Z-API ativa (instância + token + Client-Token).
- Número WhatsApp do piloto conectado à instância.
- Webhook do Z-API apontando para `…/api/attendance/whatsapp/inbound` com auth.

## 5. Envs necessários no futuro (sem valores)
`ZAPI_BASE_URL`, `ZAPI_INSTANCE_ID`, `ZAPI_TOKEN`, `ZAPI_CLIENT_TOKEN`, `ZAPI_WEBHOOK_SECRET` (auth do inbound), e as flags `INSURER_WHATSAPP_REAL_SEND_ENABLED`, `EXTERNAL_ACTION_REAL_ENABLED`, `GLOBAL_KILL_SWITCH=false`. **Todos guardados no EasyPanel/Vault, nunca no repo.**

## 6. Fluxo mínimo do piloto (MVP comercial Allianz Residencial)
1. Segurado manda mensagem no WhatsApp → Z-API → inbound webhook (auth).
2. Normaliza, mascara PII, identifica corretora (tenant) e cria/atualiza case + corridor_run.
3. Attendance conduz Allianz Residencial; coleta identidade (CPF/CNPJ mascarado), localiza apólice (InfoCap read-only/HITL).
4. Encaminha ao subcorredor **Eletricista** quando aplicável.
5. Responde com segurança (sem prometer cobertura sem evidência); **humano no loop** quando necessário.
6. Registra case/histórico/evidência; **nenhuma ação externa sem gate**; **kill switch** disponível.
7. Dashboard permite acompanhar e intervir.

## 7. Primeiro canary seguro (sem risco)
- Usar `simulate-inbound`/`preflight` para validar ponta-a-ponta **sem** Z-API real.
- Depois, com Z-API conectado mas `INSURER_WHATSAPP_REAL_SEND_ENABLED=false`: inbound real entra, runtime processa, **outbound fica dry-run** (nada enviado). Valida recebimento real sem responder de verdade.
- Só então um **outbound canary com HITL**: 1 número de teste consentido, aprovação humana por mensagem, kill switch armado.

## 8. Blockers de produção
- **P0:** consentimento/opt-in LGPD; idempotência outbound; segredo do webhook protegido.
- **P1:** dashboard operacional + kill switch acessível ao operador; seed do piloto Allianz Residencial/Eletricista; retry/fila.
- **P2:** observabilidade/métricas; rate limit; rollback documentado.

## 9. Testes obrigatórios antes de conectar WhatsApp real
- `simulate-inbound` cobre Allianz Residencial + Eletricista ponta-a-ponta (dry-run).
- `resolveOutboundPolicy` nunca envia sem `externalSendAuthorized` (já testável).
- Webhook rejeita request sem auth.
- Nenhum segredo/PII em logs (telefone mascarado).
- Gates `false` bloqueiam envio real.

## 10. Roadmap (numerado)
- **42X5B — Z-API Real Provider Gated:** adapter real atrás do gate, idempotência, retry, dry-run, send-approval, kill switch. Nenhum envio sem ativação deliberada.
- **42X5C — Canary WhatsApp:** 1 número consentido, HITL, kill switch.
- **42X6 — Dashboard operacional + opt-in** (se ainda não existir).
- **Piloto Allianz Residencial** em produção restrita.

## 11. MVP comercial Allianz Residencial (definição)
A menor versão vendável e segura: **segurado fala no WhatsApp → atendimento Allianz Residencial conduzido pela IA com identidade + apólice (read-only) → encaminha Eletricista quando cabível → responde com segurança → humano no loop → case/histórico/evidência registrados → nenhuma ação externa sem gate → kill switch + dashboard.** Envio real só após 42X5B/42X5C com consentimento.

## 12. O que pode rodar em paralelo (sem bloquear)
- Portal (43P4.2B/43P4.3) e WhatsApp (42X5B/42X5C) avançam em trilhos separados; um não destrava o outro.
- RAG/Knowledge e Auxiliares são frentes independentes que **alimentam** a inteligência, mas não bloqueiam o piloto.

## 13. O que NÃO pode ir a produção ainda
- Envio WhatsApp real sem 42X5B + consentimento + kill switch.
- Ação de negócio (abrir sinistro/assistência) sem gate + evidência.
- Qualquer fluxo que prometa cobertura sem evidência estruturada.
