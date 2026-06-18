# SPEC-009 — WhatsApp Real Webhook / Z-API Handoff & Future Execution Plan

> Projeto: AutoBrokers.ai / AutoBrokers Intelligence OS  
> Status atual: WhatsApp simulado aprovado até 42W1.2. Webhook real pausado temporariamente por instância Z-API desconectada/pagamento pendente.  
> Uso: entregar este documento para um novo chat/agente quando for retomar o WhatsApp real.

---

## 1. Decisão executiva

O bloco WhatsApp real **não deve avançar para 42W2 enquanto a Z-API estiver desconectada ou com pagamento pendente**. O sistema já possui simulação interna (`/api/attendance/whatsapp/simulate-inbound`) funcionando e validada, mas o teste de webhook real depende da instância Z-API ativa, conectada e configurada.

Enquanto a Z-API estiver indisponível, o projeto deve continuar evoluindo nas frentes que não dependem de provider real:

1. goldens/E2E regressivos do atendimento e WhatsApp simulado;
2. inteligência de perguntas sobre apólice/cobertura;
3. mídia/documentos em modo simulado;
4. hardening de segurança, logs, LGPD e readiness de produção;
5. documentação/handoff para retomada do 42W2.

---

## 2. Estado validado antes da pausa

### 2.1 Fluxo dashboard/simulador validado

O fluxo de atendimento no dashboard/simulador está validado:

1. cria caso;
2. coleta problema;
3. faz risco mínimo;
4. coleta CPF;
5. consulta InfoCap real;
6. retorna múltiplas apólices;
7. seleciona apólice;
8. consulta `/documento`;
9. gera `policy_snapshot`;
10. gera `coverage_evidence`;
11. gera `policy_interpretation_context`;
12. gera `coverage_readiness`;
13. prepara `dispatch-dry-run`;
14. faz HITL de cobertura;
15. mantém `external_action.sent=false`.

### 2.2 Fluxo WhatsApp simulado validado

O endpoint `/api/attendance/whatsapp/simulate-inbound` foi validado no fluxo completo:

1. `Oi` cria triagem;
2. `estou sem luz` faz upgrade para `allianz_residential_assistance`;
3. `só na cozinha` não quebra o fluxo;
4. resposta tardia de risco é aceita;
5. CPF aciona InfoCap automático;
6. múltiplas apólices são listadas;
7. `a primeira` seleciona a apólice correta;
8. mensagem seguinte não repete seleção de apólice;
9. `selected_subcorridor_key='electrician'`;
10. slots fluem;
11. `dispatch_readiness.packet_state='hitl_required'`;
12. `outbound.dry_run=true` e `sent=false`;
13. sinistro automóvel cai em triage/claim, sem virar residencial.

### 2.3 Commits/relatórios importantes

Relatórios canônicos no repo:

- `42W0-whatsapp-inbound-buffer-case-routing-security-report.md`
- `42W1-whatsapp-attendance-controlled-test-report.md`
- `42W1.1-whatsapp-global-corridor-routing-report.md`
- `42W1.2-whatsapp-conversation-state-repair-report.md`
- `42B6-dispatch-packet-dry-run-hitl-report.md`
- `SPEC-007-atendimento-producao-autonomo.md`
- `SPEC-008-producao-global-autobrokers.md`

---

## 3. Arquitetura correta do WhatsApp

### 3.1 Princípio central

O WhatsApp é **canal**, não cérebro. Ele não deve decidir cobertura, acionar seguradora nem governar o atendimento sozinho.

Arquitetura correta:

```txt
WhatsApp Provider Adapter
→ Inbound Normalization
→ Buffer/Debounce
→ Case Routing
→ Attendance Runtime
→ Tools/Vault/InfoCap/Dispatch Readiness
→ Outbound Policy
→ Provider Send ou Dry-run
```

### 3.2 Smith como base

Deve ser usada a estrutura existente do Smith:

- webhook Z-API existente no backend;
- `message_buffer_service` com Redis;
- `buffer_processor`;
- provider adapter `whatsapp/`;
- `integration_service`;
- `integration_secrets`/Fernet;
- aba WhatsApp de agentes/subagentes;
- tabelas/conceitos existentes de `integrations`, `conversations`, `messages`, `agents`, `attendance_cases`.

Não criar:

- runtime paralelo;
- novo provider paralelo;
- nova inbox paralela;
- orquestração via n8n;
- Evolution como provider principal neste momento.

### 3.3 Z-API vs Evolution

Decisão atual:

- **Z-API/Smith** é o provider inicial do MVP.
- **Evolution legado** é referência técnica/domínio para o futuro, mas não deve substituir o Smith agora.
- O adapter deve ser provider-agnóstico para permitir Evolution no futuro sem reescrever Attendance Runtime.

---

## 4. O que é o 42W2

Nome recomendado:

```txt
42W2 — WhatsApp Controlled Real Webhook Conversation
```

Objetivo:

Testar uma conversa real entrando pelo webhook Z-API, ainda em modo dry-run, usando o mesmo fluxo já validado no `simulate-inbound`.

Escopo:

1. regularizar/conectar Z-API;
2. configurar webhook real;
3. manter outbound real desligado;
4. receber mensagem real do WhatsApp;
5. validar dedupe/buffer;
6. criar/rotear case;
7. acionar Attendance Runtime;
8. retornar outbound dry-run/simulado ou envio real bloqueado;
9. confirmar que nenhum dispatch externo é enviado.

Fora de escopo:

- envio real para segurado em produção aberta;
- acionamento de seguradora/prestador;
- mídia completa;
- assinatura avançada se provider não suportar ainda;
- Evolution real.

---

## 5. Pré-requisitos para retomar 42W2

Antes do 42W2, confirmar:

1. Z-API paga/regularizada;
2. instância conectada;
3. número WhatsApp ativo;
4. webhook apontando para backend correto;
5. `ATTENDANCE_WHATSAPP_ENABLED=true` no backend;
6. `ATTENDANCE_BRIDGE_URL` configurada;
7. `BACKEND_INTERNAL_API_KEY` presente e igual no backend/web quando necessário;
8. `WHATSAPP_WEBHOOK_AUTH_MODE` definido;
9. se `shared_secret`, `WHATSAPP_WEBHOOK_SECRET` configurado;
10. `WHATSAPP_ATTENDANCE_OUTBOUND_REAL_ENABLED=false` no início;
11. integração WhatsApp vinculada ao `company_id` e `agent_id` corretos;
12. agent role `attendance`, audience `insured_external`;
13. InfoCap connection ready;
14. Redis ativo;
15. logs sem PII.

---

## 6. Prompt futuro para Claude — 42W2

```txt
BATCH 42W2 — WhatsApp Controlled Real Webhook Conversation

Contexto:
O bloco WhatsApp simulado foi validado até 42W1.2. O fluxo `/api/attendance/whatsapp/simulate-inbound` passou com:
- triage inicial;
- upgrade para residencial/eletricista;
- resposta tardia de risco tratada;
- CPF → InfoCap real;
- múltiplas apólices;
- seleção textual “a primeira”;
- selected_subcorridor_key='electrician';
- slots coletados;
- dispatch_readiness.packet_state='hitl_required';
- outbound.dry_run=true e sent=false;
- sinistro → triage/claim.

Agora a Z-API foi regularizada e conectada. Precisamos validar o webhook real, ainda em modo controlado e dry-run.

Objetivo:
Testar uma conversa real entrando pelo webhook Z-API e confirmar que o mesmo fluxo do simulate-inbound funciona sem envio externo real.

Auditar antes:
- docs/canon/SPEC-007-atendimento-producao-autonomo.md
- docs/canon/SPEC-008-producao-global-autobrokers.md
- docs/canon/design/2026-06-claude-design/42W0-whatsapp-inbound-buffer-case-routing-security-report.md
- docs/canon/design/2026-06-claude-design/42W1-whatsapp-attendance-controlled-test-report.md
- docs/canon/design/2026-06-claude-design/42W1.1-whatsapp-global-corridor-routing-report.md
- docs/canon/design/2026-06-claude-design/42W1.2-whatsapp-conversation-state-repair-report.md
- backend/app/api/webhook.py
- backend/app/services/message_buffer_service.py
- backend/app/tasks/buffer_processor.py
- backend/app/services/whatsapp/*
- backend/app/services/integration_service.py
- backend/app/core/config.py
- app/api/attendance/whatsapp/inbound/route.ts
- app/api/attendance/whatsapp/preflight/route.ts
- app/api/attendance/whatsapp/simulate-inbound/route.ts
- lib/attendance/whatsapp-inbound.ts
- lib/attendance/whatsapp-case-routing.ts
- lib/attendance/attendance-intent-resolver.ts
- lib/attendance/whatsapp-policy-selection.ts
- lib/attendance/runtime-invoke.ts

Escopo permitido:
- ajustes no webhook real;
- preflight real;
- diagnostics;
- buffer/debounce;
- idempotência;
- scripts de teste;
- melhorias na UI de status WhatsApp se necessário.

Escopo proibido:
- não enviar WhatsApp real ao cliente se outbound real estiver OFF;
- não acionar seguradora/prestador;
- não usar Evolution/n8n como runtime;
- não criar provider paralelo;
- não vazar token/client_token/telefone/CPF/payload bruto;
- não quebrar simulate-inbound.

Requisitos:
1. Preflight real Z-API:
   - verificar instância/conexão quando possível;
   - confirmar webhook ativo;
   - confirmar integration ativa;
   - confirmar dry-run/outbound real off;
   - confirmar bridge OK.

2. Webhook real:
   - receber payload real;
   - normalizar;
   - dedupe por messageId;
   - buffer/debounce;
   - rotear para Attendance Runtime;
   - gerar auto_reply;
   - salvar outbound dry-run;
   - não enviar real.

3. Teste controlado:
   - mandar mensagens reais do WhatsApp do fundador;
   - validar case criado channel='whatsapp';
   - validar logs/diagnostics;
   - validar que outbound real não foi enviado.

4. Segurança:
   - webhook auth mode explícito;
   - logs sanitizados;
   - token não aparece em response;
   - telefone mascarado/hash.

5. Testes:
   - regressão simulate-inbound;
   - webhook payload fixture real sanitizado;
   - dedupe;
   - buffer;
   - outbound dry-run;
   - E2E real manual documentado.

Rodar:
- npm run typecheck
- npm run build
- python -m py_compile backend
- scripts WhatsApp existentes
- git diff --check

Resposta final:
- envs conferidas;
- webhook URL;
- status da integração;
- resultado dos testes;
- se podemos avançar para outbound real controlado ou precisamos corrigir algo.
```

---

## 7. Riscos para 42W2

1. Z-API payload real pode diferir do fixture/simulação.
2. Webhook pode enviar eventos duplicados/status que precisam ser ignorados.
3. Buffer real pode alterar timing da conversa.
4. Outbound real pode ser acionado por erro de configuração se flag não estiver desligada.
5. Instância desconectada/pagamento pendente invalida teste real.
6. Webhook sem autenticação forte é risco de produção.
7. Logs podem vazar payload se algum trecho antigo ainda logar bruto.

Mitigação:

- começar com outbound real OFF;
- usar número do fundador;
- usar uma única corretora/tenant sandbox;
- verificar logs após cada teste;
- manter dispatch externo bloqueado;
- só habilitar envio real após homologação.

---

## 8. Caminho após 42W2

Se 42W2 passar:

1. 42W3 — WhatsApp outbound real controlado para segurado, não seguradora;
2. 42M0 — Media Evidence Pipeline;
3. 42B7.2 — Goldens finais com WhatsApp real/simulado;
4. 42X0 — Action Engine dry-run para canais externos;
5. 42X1 — Allianz external execution adapter;
6. SEC-001 — hardening produção.

Se 42W2 não puder ser executado:

1. executar 42B7.2 Goldens;
2. executar 42Q0 Policy Q&A/RAG;
3. executar 42M0 Media Evidence Pipeline;
4. retornar ao 42W2 quando Z-API estiver ativa.

---

## 9. Mensagem de handoff para novo chat

Use este resumo em novo chat:

```txt
Estamos no AutoBrokers.ai / AutoBrokers Intelligence OS. O atendimento dashboard e WhatsApp simulado foram validados até 42W1.2. Não criar runtime paralelo. Usar Smith/Z-API como provider inicial. Evolution/n8n é referência, não runtime. O fluxo validado: triage → upgrade corredor → risco → CPF → InfoCap real → múltiplas apólices → seleção textual → policy-select → slots → dispatch dry-run hitl_required. Z-API estava desconectada por pagamento pendente, então 42W2 real webhook ficou pausado. Quando Z-API estiver ativa, executar SPEC-009 / prompt 42W2. Enquanto isso, avançar com goldens, policy Q&A/RAG e media evidence pipeline.
```
