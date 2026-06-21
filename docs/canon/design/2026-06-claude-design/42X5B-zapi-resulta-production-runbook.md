# 42X5B — Runbook: WhatsApp (Z-API) produção restrita — Resulta Seguros

> Operação após pagar/reativar a Z-API. **Sem valores secretos aqui.** Usa a
> infraestrutura JÁ existente (webhook backend Python + bridge Next + provider).
> Próximo passo real = 42X5C (canary inbound → 1 outbound com HITL).

## Arquitetura real (já existente — não recriar)
```
Segurado → WhatsApp da corretora → Z-API
  → POST /api/v1/webhook/z-api  (BACKEND Python — público, autenticado)
      · valida WHATSAPP_WEBHOOK_AUTH_MODE (shared_secret | provider_signature)
      · dedupe por messageId (Redis SET NX + WHATSAPP_DEDUPE_TTL_SECONDS)
      · resolve a corretora SERVER-SIDE via integração (get_whatsapp_integration) — nunca confia em company_id do payload
      · get_or_create_conversation(phone, company_id)
      → encaminha ao bridge Next (ATTENDANCE_BRIDGE_URL + chave interna), gated (42W0)
          · POST /api/attendance/whatsapp/inbound (INTERNO) → runtime (case + corredor + dry-run)
          · retorna auto_reply + outbound{ external_send_allowed, dry_run, blockers }  ← POLÍTICA CANÔNICA (42X5B)
      → backend SÓ envia se outbound.external_send_allowed===true && dry_run===false
          · whatsapp_service.send_message(phone, reply, integration)  (Z-API)
```

## Variáveis (configurar no EasyPanel/Vault — sem valores no repo)
**Backend (serviço Python):**
- `WHATSAPP_WEBHOOK_AUTH_MODE` = `shared_secret` (recomendado) ou `provider_signature`
- `WHATSAPP_WEBHOOK_SECRET` (quando shared_secret) — header `x-webhook-secret` ou `?secret=`
- `WHATSAPP_DEDUPE_TTL_SECONDS` (ex.: 86400)
- `ATTENDANCE_BRIDGE_URL` = URL do serviço Next (rota interna inbound)
- `BACKEND_INTERNAL_API_KEY` (= chave interna usada pelo bridge; idêntica no Next)
- Z-API por corretora (via integração/tenant_connections + Vault, NUNCA em tabela comum/log):
  - base URL da instância, `instance ID`, `token`, `Client Token`

**Next (serviço web):**
- `BACKEND_INTERNAL_API_KEY` (mesma do backend) ou `ADMIN_API_KEY`
- Flags de envio (todas default seguro):
  - `GLOBAL_KILL_SWITCH` = `true` (freio final; só `false` na janela)
  - `ATTENDANCE_WHATSAPP_DRY_RUN` = `true` (só `false` para enviar)
  - `WHATSAPP_ATTENDANCE_OUTBOUND_REAL_ENABLED` = `false`
  - `EXTERNAL_ACTION_REAL_ENABLED` = `false`
  - `INSURER_WHATSAPP_REAL_SEND_ENABLED` = `false` (só canal seguradora)

> A política canônica (`evaluateWhatsAppOutboundGate`) exige TODAS as condições + consentimento (+ approval se proativo). Faltando qualquer uma → dry-run (não envia).

## Passos (após pagamento)
1. **Reativar Z-API** e conectar o número da Resulta (QR no painel Z-API). Sem expor segredo.
2. **Configurar segredos** Z-API da Resulta no Vault/integração (server-side).
3. **Configurar webhook** no painel Z-API apontando para `…/api/v1/webhook/z-api` com o secret (header/query).
4. **Confirmar inbound SEM outbound:** manter `ATTENDANCE_WHATSAPP_DRY_RUN=true`. Enviar uma mensagem de teste → conferir que o case é criado e a resposta fica dry-run (não enviada).
5. **Registrar número consentido** (opt-in) para o canary outbound (metadata de consentimento).
6. **Outbound canary (1 mensagem, HITL):** na janela deliberada, ligar `GLOBAL_KILL_SWITCH=false` + `ATTENDANCE_WHATSAPP_DRY_RUN=false` + `WHATSAPP_ATTENDANCE_OUTBOUND_REAL_ENABLED=true` + `EXTERNAL_ACTION_REAL_ENABLED=true`, com `external_send_authorized=true` e consentimento válido → enviar para o número de teste.
7. **Desligar tudo** após o canary: flags de volta a `false`/dry-run, `GLOBAL_KILL_SWITCH=true`.

## Kill switch / parar tudo
- `GLOBAL_KILL_SWITCH=true` (bloqueia todo envio imediatamente) e/ou `ATTENDANCE_WHATSAPP_DRY_RUN=true`.
- Opt-out de um contato bloqueia envio para ele imediatamente (consent).

## Validar
- Cases/conversas/mensagens criados com `company_id` da Resulta.
- Logs sanitizados (telefone/nome/conteúdo mascarados; sem token/URL/secret).
- `outbound.external_send_allowed=false` enquanto qualquer condição faltar.

## Rollback / revogar
- Desligar flags + kill switch on.
- Revogar/limpar a integração Z-API da corretora (remove os secret refs).
- Remover o webhook no painel Z-API.

## Evolution (futuro — registrar)
O `preflight` já reconhece providers `evolution`/`evolution-api`/`wppconnect`. O caminho multi-tenant gratuito (Evolution Go) entra como **provider adicional** no mesmo registry/abstração — sem recriar webhook/bridge. Será um batch próprio.

## Números de assistência das seguradoras (GLOBAL — registrar p/ depois)
Os WhatsApps de assistência das seguradoras são **globais** (mesmo número para todas as corretoras) — fonte: `docs/intake/sinistro e assistencias - contatos.xlsx`. Devem ser gravados **no corredor (global)**, não preenchidos por corretora. (Mesma ideia para links de portais.) **Não** implementado neste batch — registrado como próximo passo de dados globais.
