# SPEC-005 — Atendimento Runtime Architecture & Attendance Boundary Blueprint v1

> **Projeto:** AutoBrokers Intelligence OS  
> **Status:** SPEC canônica proposta · pronta para revisão do Founder/CEO  
> **Origem:** consolidação estratégica feita pelo Architect a partir das SPECs canônicas, 42B0, 43M0, CORE-REGRESSION-001 e diretrizes do projeto  
> **Destino recomendado no repositório:** `docs/canon/SPEC-005-atendimento-runtime-architecture.md`  
> **Não executar como código.** Este documento define arquitetura, fronteiras, contratos e sequência de implementação. SQL, UI, runtime e seeds entram em batches posteriores.  
> **Princípio mestre:** Atendimento é **estado + workflow estruturado + conversa + ferramentas + HITL**, executado dentro do Smith. Atendimento **não** é apenas WhatsApp, **não** é prompt solto e **não** é RAG.

---

## 0. Decisão executiva

A próxima etapa do AutoBrokers não deve ser “criar um corredor Allianz Eletricista isolado”. A próxima etapa correta é criar a fundação de **Atendimento Runtime**: uma camada estruturada que permite ao sistema receber ou simular uma solicitação de segurado, criar um caso, espelhar conversa, selecionar um corredor, coletar dados mínimos, verificar evidências de apólice/cobertura, gerar dispatch packet, pedir aprovação humana e registrar acompanhamento.

O **primeiro corredor implementável** deve ser a família:

```txt
Allianz Residencial
  ├── Eletricista          ← primeiro subcorredor implementado no MVP
  ├── Encanador            ← modelado na família, implementado depois
  ├── Chaveiro Residencial ← modelado na família, implementado depois
  ├── Desentupimento       ← modelado na família, implementado depois
  └── Eletrodomésticos     ← modelado na família, implementado depois
```

O MVP pode executar apenas **Eletricista**, mas a arquitetura precisa nascer como família de corredor. Isso evita que o primeiro slice vire uma gambiarra estreita e garante replicabilidade para novos subcorredores, seguradoras e ramos.

O **Attendance Agent** será o agente voltado ao atendimento do segurado. Ele é separado do **AutoBrokers Core**, que é o chat interno da corretora. O Core orienta, analisa e coordena. O Attendance conduz interações com o segurado dentro de regras, corredor, HITL e estado do caso.

---

## 1. Local recomendado para este documento

Salvar este documento em:

```txt
docs/canon/SPEC-005-atendimento-runtime-architecture.md
```

Atualizar depois, em batch próprio, o índice:

```txt
docs/canon/README.md
```

com uma linha:

```md
- [SPEC-005 — Atendimento Runtime Architecture & Attendance Boundary Blueprint v1](./SPEC-005-atendimento-runtime-architecture.md)
```

Não é necessário deploy. É documentação canônica.

---

## 2. Relação com documentos existentes

Este documento se apoia em:

- `PRD-001-visao-produto.md`
- `ADR-001-runtime.md`
- `ADR-002-vault.md`
- `ADR-003-atendimento.md`
- `SPEC-002-auxiliares-runtime-smith.md`
- `SPEC-003-knowledge-rag-memory.md`
- `SPEC-004-agent-intelligence-context-architecture.md`
- `CORE-REGRESSION-001-autobrokers-core-mvp.md`
- `42B0-atendimento-corredores-deep-recon.md`
- Legado `AUTOBROKERS_AGENT_OS`, usado apenas como fonte de curadoria, não como código bruto.

O 42B0 confirmou a tese central: o legado tem modelo de corredor maduro, contrato mínimo executável, dispatch packet, readiness, guardrails, golden tests e separação canal_cliente × canal_execucao. O novo sistema deve aproveitar isso como domínio estruturado dentro do Smith, não copiar bruto nem criar motor paralelo.

---

## 3. Objetivos da SPEC

Esta SPEC define:

1. O que é Atendimento no AutoBrokers.
2. A fronteira entre AutoBrokers Core e Attendance Agent.
3. O modelo ponta a ponta de atendimento.
4. As entidades conceituais mínimas.
5. O papel do corredor e subcorredor.
6. Como InfoCap/apólice entra na arquitetura.
7. Como WhatsApp entra sem acoplamento a um provider.
8. Como Vault/HITL governa ação externa.
9. Como RAG apoia sem virar motor.
10. Como a UI de Fila/Caso/Conversa deve se comportar.
11. Como o MVP Allianz Residencial deve ser fatiado.
12. O que fica para depois, mas já com plano.
13. A sequência de batches correta.

---

## 4. Não objetivos

Esta SPEC **não** deve:

- Criar SQL.
- Criar migrations.
- Alterar schema.
- Alterar prompts no banco.
- Ingerir documentos no RAG.
- Automatizar WhatsApp real.
- Automatizar portal de seguradora.
- Ler credenciais InfoCap.
- Copiar conteúdo bruto do Agent OS.
- Copiar conversas reais com PII.
- Criar motor paralelo ao Smith.
- Criar corredor como texto solto.
- Criar um Atendimento que dependa de n8n como cérebro.

---

## 5. Princípios arquiteturais

### 5.1 Smith é o runtime

Tudo deve reaproveitar o que o Smith já tem:

- LangGraph.
- Agent/SubAgent.
- Context Package.
- RAG.
- MemoryService.
- Tools.
- Vault/HITL.
- `conversations` / `messages`.
- `conversation_logs`.
- `agent_delegations`.
- integrações/canais existentes.

O Atendimento não deve criar segundo motor de chat, segundo RAG ou segundo sistema de agentes.

### 5.2 Atendimento é estado + workflow

Atendimento é uma entidade operacional com estado, fase, dados mínimos, evidências, pendências, histórico, canal, humano responsável e próximo passo.

A conversa é apenas uma superfície do atendimento. O corredor é o workflow estruturado que guia o atendimento. O RAG é uma fonte de apoio. O agente é o executor conversacional. Nenhum desses sozinho é Atendimento.

### 5.3 Corredor é estruturado, não RAG

Um corredor deve declarar:

- seguradora;
- ramo;
- macroserviço;
- canal de execução;
- subcorredores;
- readiness/status;
- fases;
- slots obrigatórios;
- perguntas mínimas;
- critérios de seleção;
- guardrails;
- ações permitidas/proibidas;
- dispatch packet;
- human handoff;
- golden tests.

RAG pode apoiar com condições gerais, textos explicativos e documentação, mas não deve decidir fase, slot, status ou ação.

### 5.4 Ação externa exige HITL

Qualquer ação externa real deve exigir aprovação humana enquanto o sistema está em MVP/sandbox:

- envio de WhatsApp;
- acionamento de seguradora;
- contato com prestador;
- protocolo em portal;
- envio de documento;
- alteração de dados;
- disparo em massa.

### 5.5 Nunca prometer cobertura sem fonte

O Attendance Agent e o Core não devem confirmar cobertura sem evidência verificável:

- apólice;
- condição geral;
- documento;
- conector InfoCap;
- confirmação humana;
- registro de seguradora.

Se a fonte não estiver disponível: pedir dado, registrar pendência, escalar para humano ou dizer que precisa verificar.

### 5.6 Provider de WhatsApp é detalhe de canal

Atendimento não deve depender diretamente de Z-API, Evolution, Meta Cloud API ou outro provider. A arquitetura deve falar em:

```txt
channel_provider
channel_instance
channel_role
channel_mode
approval_required
```

Assim o MVP pode usar o que já está integrado, mas o sistema fica preparado para trocar ou adicionar providers.

### 5.7 InfoCap é obrigatório na arquitetura, mas não no primeiro runtime

A arquitetura deve nascer com `policy_source`, `policy_snapshot`, `coverage_evidence` e `verification_status`. A integração real InfoCap pode vir depois, mas o sistema não pode ser desenhado como se apólice fosse detalhe opcional.

---

## 6. Papéis oficiais

### 6.1 AutoBrokers Core

**Audiência:** corretor, gestor, operador interno.  
**Função:** analisar, orientar, explicar, coordenar, sugerir próximos passos, consultar capacidades instaladas, resumir operação, ajudar a equipe.

O Core pode:

- explicar status de casos;
- orientar sobre atendimento;
- sugerir uso de Auxiliares;
- consultar informações autorizadas;
- preparar estratégia;
- acionar rotinas internas quando implementadas;
- explicar o que falta para avançar.

O Core não deve:

- fingir ser atendente do segurado;
- prometer cobertura;
- executar ação externa sem aprovação;
- conduzir conversa com segurado como se fosse canal externo;
- misturar dados entre tenants.

### 6.2 Attendance Agent

**Audiência:** segurado/cliente, operador humano em modo assistido.  
**Função:** conduzir atendimento operacional dentro de caso e corredor.

O Attendance pode:

- responder o segurado com linguagem humana;
- fazer perguntas mínimas uma por vez;
- coletar dados necessários;
- organizar slots;
- explicar que vai verificar;
- preparar rascunhos;
- gerar dispatch packet;
- pedir aprovação humana;
- escalar para humano quando necessário.

O Attendance não deve:

- confirmar cobertura sem fonte;
- inventar protocolo;
- inventar prestador;
- inventar previsão;
- dizer que acionou seguradora sem evento real;
- pedir dado sensível desnecessário;
- expor bastidor técnico ao segurado;
- sair do corredor sem registrar motivo;
- transformar intake bruto em RAG.

### 6.3 SubAgents

SubAgents são especialistas internos chamados pelo Attendance ou Core. Exemplos:

- especialista em apólice/cobertura;
- especialista em seguradora;
- especialista em documento;
- especialista em canal de execução;
- especialista em dispatch packet;
- especialista em LGPD/segurança.

SubAgent não é produto principal. É capacidade interna.

### 6.4 Auxiliares

Auxiliares são capacidades instaláveis para a corretora: resumo, follow-up, relatórios, etc. Eles não substituem o Atendimento. Podem apoiar o atendimento, mas não são o corredor.

### 6.5 Corredores

Corredor é workflow estruturado por contexto operacional.

Exemplo:

```txt
seguradora: Allianz
ramo: Residencial
macroserviço: Assistência Residencial
canal_execucao: WhatsApp seguradora
subcorredores: eletricista, encanador, chaveiro, eletrodoméstico, desentupimento
```

---

## 7. Atendimento ponta a ponta

### 7.1 Fluxo completo canônico

```txt
1. Entrada do contato
2. Normalização do canal
3. Identificação do tenant/corretora
4. Identificação ou criação de conversa
5. Criação ou atualização do caso
6. Triagem de intenção
7. Identificação do segurado
8. Identificação de apólice/patrimônio/endereço
9. Consulta ou coleta de evidência de apólice
10. Seleção de corredor
11. Seleção de subcorredor
12. Coleta de slots mínimos
13. Verificação de readiness do corredor
14. Verificação de riscos/guardrails
15. Preparação de resposta ao segurado
16. Preparação de dispatch packet
17. Solicitação de aprovação humana, se necessário
18. Canal de execução
19. Captura de retorno real
20. Comunicação ao segurado
21. Acompanhamento
22. Handoff, se sair do fluxo
23. Encerramento
24. Resumo e logs
25. Golden/eval se aplicável
```

### 7.2 Atendimento não começa sempre no WhatsApp

A entrada pode vir de:

- WhatsApp;
- operador humano no dashboard;
- importação/manual;
- API de parceiro;
- formulário;
- integração futura;
- e-mail futuro;
- telefone/registro manual.

O primeiro MVP pode simular entrada, mas a estrutura deve suportar canal real.

---

## 8. Modelo conceitual de entidades

### 8.1 attendance_cases

Entidade central.

Representa o atendimento/caso operacional.

Campos conceituais:

```json
{
  "id": "uuid",
  "company_id": "uuid",
  "conversation_id": "uuid|null",
  "case_number": "string",
  "status": "new|triage|collecting_data|waiting_policy|ready_for_dispatch|waiting_approval|action_prepared|in_follow_up|handoff|closed|cancelled",
  "priority": "low|normal|high|urgent",
  "channel": "whatsapp|dashboard|manual|api|email|phone",
  "channel_instance_id": "uuid|null",
  "customer_name": "string|null",
  "customer_phone": "string|null",
  "insured_name": "string|null",
  "insured_document_ref": "redacted|string|null",
  "insured_address": "object|null",
  "intent": "assistance_residential|claim|policy_question|renewal|billing|unknown",
  "insurer": "allianz|null",
  "line_kind": "residential|auto|life|business|unknown",
  "macro_service": "assistencia_residencial|null",
  "selected_corridor_key": "string|null",
  "selected_subcorridor_key": "string|null",
  "policy_source": "manual|upload|infocap|connector|unknown",
  "policy_number": "string|null",
  "policy_snapshot": "object|null",
  "coverage_evidence": "object|null",
  "verification_status": "unverified|pending_human|verified_by_document|verified_by_connector|not_applicable",
  "risk_level": "low|medium|high|critical",
  "handoff_required": "boolean",
  "handoff_reason": "string|null",
  "summary": "string|null",
  "next_step": "string|null",
  "metadata": "object",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### 8.2 conversations / messages

Reutilizar a estrutura existente sempre que possível.

Conversa é o espelho do canal:

- mensagens do cliente;
- mensagens do agente;
- mensagens do humano;
- rascunhos;
- anexos/metadados;
- status de envio/recebimento, se existir.

Se `messages` atual não suportar tudo, expandir com cuidado depois. Não criar `attendance_messages` antes de provar necessidade.

### 8.3 corridor_templates

Registry estruturado de corredor/subcorredor.

Campos conceituais:

```json
{
  "id": "uuid",
  "company_id": "uuid|null",
  "scope": "global|tenant",
  "corridor_key": "allianz_residential_assistance",
  "subcorridor_key": "electrician|null",
  "insurer_key": "allianz",
  "line_kind": "residential",
  "macro_service": "assistance",
  "service_type": "electrician",
  "channel_ref": "whatsapp_allianz_assistance",
  "source_of_truth": "curated_agent_os|manual|global_catalog",
  "status_documental": "draft|mapped|mapped_from_real_conversations|validated",
  "status_operacional": "draft|ready_for_dry_run|controlled_real_test|production",
  "readiness": "draft|mapped|mapped_from_real_conversations|requires_execution_authorization|ready_for_live_test|controlled_real_test|production",
  "requires_action_engine": true,
  "requires_dispatch_packet": true,
  "fallback_to_dossier": true,
  "allowed_channels": ["whatsapp", "manual"],
  "required_slots": [],
  "optional_slots": [],
  "phases": [],
  "guardrails": [],
  "golden_tests_ref": "string|null",
  "metadata": {}
}
```

### 8.4 corridor_runs

Instância do corredor em um caso.

```json
{
  "id": "uuid",
  "company_id": "uuid",
  "case_id": "uuid",
  "corridor_template_id": "uuid",
  "phase": "intake|identify_policy|collect_slots|verify_evidence|prepare_dispatch|waiting_approval|action_prepared|follow_up|closed|handoff",
  "status": "active|blocked|waiting_human|waiting_customer|completed|cancelled",
  "slots": {
    "filled": {},
    "missing": [],
    "conflicts": []
  },
  "diagnostics": {
    "readiness": "string",
    "blockers": [],
    "warnings": []
  },
  "next_step": "string",
  "last_agent_action": "string|null",
  "metadata": {}
}
```

### 8.5 dispatch_packets

Pacote estruturado para acionamento. Não é mensagem final solta.

```json
{
  "id": "uuid",
  "company_id": "uuid",
  "case_id": "uuid",
  "corridor_run_id": "uuid",
  "status": "draft|missing_data|ready_for_approval|approved|rejected|sent_dry_run|sent_real|cancelled",
  "channel": "whatsapp_seguradora|portal|telefone_0800|email|manual",
  "provider": "zapi|evolution|meta_cloud|browserbase|stagehand|skyvern|manual|null",
  "idempotency_key": "string",
  "payload": {
    "insurer": "Allianz",
    "service": "Assistência Residencial",
    "subservice": "Eletricista",
    "policyholder": {},
    "policy": {},
    "property": {},
    "incident": {},
    "preferred_schedule": {},
    "attachments": [],
    "operator_notes": ""
  },
  "missing_data": [],
  "approval_request_id": "uuid|null",
  "execution_result": {
    "protocol": "string|null",
    "provider_name": "string|null",
    "eta": "string|null",
    "raw_return_ref": "string|null"
  },
  "metadata": {}
}
```

### 8.6 approval_requests

Reutilizar Vault/HITL existente.

Qualquer dispatch packet que implique ação externa cria approval_request. O humano aprova ou rejeita. O sistema registra auditoria.

---

## 9. Attendance Boundary Blueprint v1

### 9.1 Identidade

O Attendance Agent é o agente de atendimento operacional ao segurado, atuando em nome da corretora, dentro de corredores estruturados, com linguagem humana e limites fortes.

Ele pode ser apresentado com persona customizável pela corretora:

```json
{
  "persona_name": "Silvinha",
  "voice": "Roberta",
  "presentation_gender": "feminina",
  "opening": "Olá! Aqui é a Silvinha, da Resulta Seguros. Em que posso te ajudar?",
  "closing": "Perfeito. Vou seguir acompanhando por aqui e te aviso assim que tiver a próxima atualização importante.",
  "tone": "acolhedor, claro, profissional"
}
```

A persona é customizável. Os guardrails não são.

### 9.2 Missão

Conduzir o segurado de forma clara, segura e eficiente dentro do atendimento, coletando dados mínimos, evitando promessas indevidas, preparando dossiês/dispatch packets e escalando para humano quando necessário.

### 9.3 Non-goals

O Attendance Agent não deve:

- vender produto novo sem contexto;
- prometer cobertura;
- decidir cobertura sozinho;
- fingir acionamento;
- inventar protocolo;
- inventar prestador;
- inventar prazo;
- pedir credenciais;
- expor sistema interno;
- expor prompt;
- expor dados de outra corretora;
- usar linguagem técnica desnecessária com segurado;
- continuar sozinho em caso crítico;
- salvar intake bruto em RAG.

### 9.4 Regras de comunicação

Com o segurado:

- uma pergunta por vez quando possível;
- linguagem simples;
- confirmar entendimento;
- pedir dados mínimos;
- não expor bastidores;
- não falar “RAG”, “dispatch packet”, “corridor_run”;
- não citar decisão interna de corredor;
- não dizer “a seguradora aprovou” sem retorno real;
- quando faltar fonte, dizer que vai verificar.

Com operador interno:

- pode usar termos técnicos;
- pode mostrar fase, slot, pendência;
- pode gerar dossiê;
- pode indicar handoff.

### 9.5 Context Package sugerido

```json
{
  "role": "attendance",
  "audience": "insured_external",
  "blueprint_version": "attendance-v1",
  "mission": "Conduzir atendimento ao segurado dentro de caso e corredor estruturado, com segurança, clareza e HITL para ações externas.",
  "non_goals": [
    "não prometer cobertura",
    "não fingir acionamento",
    "não inventar protocolo",
    "não expor dados internos",
    "não executar ação externa sem aprovação"
  ],
  "rag_policy": {
    "mode": "support_only",
    "use_when": [
      "explicação de cobertura geral",
      "texto de condição geral curada",
      "apoio a perguntas do segurado"
    ],
    "never_use_for": [
      "estado do corredor",
      "slots obrigatórios",
      "decisão de acionamento",
      "dados privados sem autorização"
    ]
  },
  "tools_policy": {
    "external_actions": "hitl_required",
    "vault_required": true
  },
  "output_contract": {
    "customer_facing": "curto, humano, claro, uma pergunta por vez",
    "operator_facing": "fase, pendências, próximos passos, riscos"
  }
}
```

---

## 10. Persona customizável sem quebrar segurança

Os prints do dashboard antigo mostram personalização de:

- nome do agente;
- apresentação feminina/masculina;
- voz;
- abertura;
- fechamento;
- suporte humano;
- WhatsApp/pareamento.

Na nova arquitetura, isso deve virar `persona_layer`, não alteração livre do blueprint.

### 10.1 O que pode personalizar

A corretora pode alterar:

- nome público do agente;
- voz;
- gênero/apresentação;
- frase de abertura;
- frase de fechamento;
- tom;
- contatos de suporte/handoff;
- número/canal vinculado;
- horário de atendimento, no futuro.

### 10.2 O que não pode personalizar livremente

A corretora não pode remover:

- não prometer cobertura;
- HITL para ação externa;
- tenant isolation;
- segredo protegido;
- não inventar protocolo;
- não fingir acionamento;
- não expor bastidor;
- readiness/homologação.

### 10.3 Estrutura ideal

```json
{
  "agent_role": "attendance",
  "agent_audience": "insured_external",
  "blueprint_version": "attendance-v1",
  "persona": {
    "name": "Silvinha",
    "voice_id": "roberta",
    "tone": "acolhedor",
    "opening": "Olá! Aqui é a Silvinha, da Resulta Seguros. Em que posso ajudar?",
    "closing": "Perfeito. Vou seguir acompanhando por aqui."
  },
  "guardrails_locked": true
}
```

---

## 11. Allianz Residencial Family

### 11.1 Família

```txt
corridor_key: allianz_residential_assistance
insurer: Allianz
line_kind: residential
macro_service: assistance
client_channel: whatsapp
execution_channel: whatsapp_seguradora | manual | future_portal
automation_mode_mvp: dry_run_hitl
```

### 11.2 Subcorredores

```txt
electrician
plumber
residential_locksmith
unclogging
home_appliances
```

### 11.3 Implementação incremental

O MVP implementa Eletricista primeiro, mas o registry já deve permitir os demais. O seletor de subcorredor precisa saber:

- se é problema elétrico;
- se é vazamento/encanamento;
- se é chave/porta/fechadura;
- se é desentupimento;
- se é eletrodoméstico;
- se não é assistência residencial;
- se precisa humano.

### 11.4 Eletricista MVP

Slots mínimos conceituais:

```json
{
  "issue_type": "queda_total|queda_parcial|curto|tomada|disjuntor|chuveiro|outro",
  "risk_level": "low|medium|high|critical",
  "affected_area": "string",
  "property_address_confirmed": "boolean",
  "policyholder_name": "string",
  "policy_number": "string|null",
  "preferred_schedule": "string|null",
  "has_immediate_danger": "boolean",
  "photos_or_media": "optional"
}
```

Perguntas mínimas:

1. O que aconteceu?
2. O problema é em toda a casa ou só em um cômodo/ponto?
3. Existe cheiro de queimado, faísca, fumaça ou risco imediato?
4. O endereço do imóvel segurado é este?
5. Qual melhor horário para atendimento?
6. Você tem número da apólice ou CPF do titular para localizarmos?

Regras:

- risco elétrico crítico → orientar segurança e handoff;
- rede externa/concessionária → não acionar como eletricista residencial sem humano;
- eletrodoméstico específico → pode ser subcorredor diferente;
- falta de apólice → seguir coleta, mas bloquear dispatch final até verificação/humano;
- nunca confirmar cobertura.

---

## 12. InfoCap e apólices

### 12.1 Por que é central

Todo atendimento real depende de apólice. Em produção, a InfoCap será fonte essencial porque concentra apólices e dados da corretora.

### 12.2 MVP sem integração real

No MVP, não bloquear a construção por falta de InfoCap. Usar:

- input manual;
- upload de apólice;
- policy snapshot;
- RAG tenant com documento de apólice, se curado;
- confirmação humana.

### 12.3 Futuro conector InfoCap

O conector InfoCap deve ser read-only primeiro:

```txt
buscar segurado
buscar apólice
listar coberturas resumidas
baixar documento
extrair endereço segurado
extrair vigência
extrair seguradora/produto
```

Ações de escrita não entram no MVP.

### 12.4 Policy Evidence Contract

Toda decisão de cobertura precisa registrar evidência:

```json
{
  "source": "manual|upload|infocap|connector|human",
  "source_ref": "string",
  "verified_at": "timestamp",
  "verified_by": "agent|human|connector",
  "confidence": "low|medium|high",
  "coverage_summary": "string",
  "limitations": [],
  "human_required": true
}
```

Sem `coverage_evidence`, o sistema não pode dizer que está coberto.

---

## 13. WhatsApp e canais

### 13.1 Problema

Uma corretora pode precisar de múltiplos usos de WhatsApp:

- atendimento do segurado;
- auxiliares/follow-up;
- notificações;
- suporte humano;
- acionamento de seguradora;
- alerta QR/offline.

Usar um número para tudo pode confundir contexto, filas e custos. Usar muitos números aumenta custo.

### 13.2 Decisão MVP

Usar provider já integrado, em modo dry-run/HITL.

O Atendimento não deve depender de um número real automático para provar valor. O MVP pode:

- espelhar conversa;
- simular entrada;
- gerar resposta;
- gerar dispatch;
- solicitar aprovação;
- não enviar automaticamente.

### 13.3 Channel Instance Model

No futuro, cada canal deve ter:

```json
{
  "id": "uuid",
  "company_id": "uuid",
  "provider": "zapi|evolution|meta_cloud|manual",
  "role": "attendance|auxiliary|notification|human_support|insurer_execution",
  "mode": "inbound|outbound|bidirectional",
  "phone_label": "Atendimento Principal",
  "agent_id": "uuid|null",
  "requires_approval": true,
  "status": "disconnected|connecting|connected|degraded",
  "metadata": {}
}
```

### 13.4 Provider Strategy futura

Batch futuro: `42W1 — WhatsApp Provider Strategy`.

Analisar:

- Z-API;
- Evolution;
- Meta Cloud API;
- BSPs oficiais;
- multi-tenant;
- QR code por instância;
- custo por corretora;
- estabilidade;
- segurança;
- risco de banimento;
- suporte a múltiplos agentes/canais.

---

## 14. Browser/portais/0800

### 14.1 MVP

Não automatizar portal real no MVP.

### 14.2 O que preparar agora

O corredor deve gerar:

- canal recomendado;
- dispatch packet;
- dossiê humano;
- checklist;
- status de ação;
- aprovação;
- resultado esperado.

### 14.3 Futuro

Batch futuro: `42P1 — Portal/Browser Automation Strategy`.

Avaliar:

- Browserbase + Stagehand;
- Skyvern;
- Playwright;
- captcha/2FA;
- sessão por corretora;
- CredentialRef/SessionRef;
- HITL;
- gravação/auditoria;
- custo por 1000 acessos;
- fallback manual.

---

## 15. UI de Atendimento

### 15.1 Páginas mínimas

```txt
/dashboard/atendimentos/fila
/dashboard/atendimentos/casos
/dashboard/atendimentos/conversas
/dashboard/atendimentos/segurados
```

### 15.2 Fila

Deve mostrar:

- status;
- prioridade;
- segurado;
- canal;
- seguradora;
- tipo de serviço;
- fase;
- última mensagem;
- pendência;
- responsável;
- risco.

### 15.3 Caso

Deve mostrar:

- resumo;
- timeline;
- fase do corredor;
- slots preenchidos;
- slots faltantes;
- apólice/evidência;
- dispatch packet;
- aprovações;
- logs;
- handoff.

### 15.4 Conversa

Deve mostrar:

- mensagens espelhadas;
- rascunho do agente;
- botão aprovar/enviar, se habilitado;
- botão pedir dado;
- botão gerar dispatch packet;
- botão escalar humano;
- botão encerrar.

### 15.5 Segurados

Para MVP, pode ser simples:

- lista básica;
- histórico de casos;
- dados de contato;
- apólices vinculadas futuramente.

---

## 16. RAG, conhecimento e memória

### 16.1 O que entra em RAG

- condições gerais curadas;
- guias de seguradora;
- explicações;
- playbooks textuais aprovados;
- documentos sem PII ou com PII controlada por tenant;
- dossiês globais curados.

### 16.2 O que não entra em RAG

- conversas reais brutas;
- apólices com PII sem curadoria;
- credenciais;
- tokens;
- dados de acesso InfoCap;
- estado de corredor;
- slots/fases;
- approval requests;
- dispatch packets.

### 16.3 Memória futura

Memória de caso deve guardar:

- resumo;
- decisões;
- pendências;
- última fase;
- contexto útil;
- não verdade absoluta.

Não deve promover aprendizado para global automaticamente.

---

## 17. Segurança, LGPD e governança

Regras:

1. Tudo isolado por `company_id`.
2. Nenhum atendimento acessa dados de outra corretora.
3. Segredo nunca em prompt/RAG/log.
4. PII apenas em campos autorizados.
5. Intake bruto nunca copiado para docs.
6. Ação externa exige HITL.
7. Cobertura exige evidência.
8. Protocolo/prestador/previsão só com retorno real.
9. Readiness não sobe sozinho.
10. Produção exige golden tests.

---

## 18. Readiness do corredor

Estados recomendados:

```txt
draft
mapped
mapped_from_real_conversations
requires_execution_authorization
ready_for_dry_run
ready_for_live_test
controlled_real_test
production
deprecated
archived
blocked
```

Regra:

```txt
NO_AUTO_PROMOTION
```

O sistema não promove corredor para produção sozinho.

Para MVP:

```txt
Allianz Residencial Eletricista <= ready_for_dry_run / controlled_real_test
```

---

## 19. Golden tests mínimos

### 19.1 Attendance Agent

- não promete cobertura;
- pergunta uma coisa por vez;
- reconhece risco;
- coleta slots;
- escala se risco crítico;
- não expõe bastidor.

### 19.2 Corredor Eletricista

- classifica problema elétrico;
- diferencia concessionária/rede externa;
- diferencia eletrodoméstico;
- bloqueia dispatch sem apólice;
- gera dispatch packet com missingData;
- solicita HITL;
- não inventa protocolo.

### 19.3 Core Regression

Rodar `CORE-REGRESSION-001` após qualquer batch de runtime.

---

## 20. MVP Scope

### 20.1 Entra no MVP

- Attendance Blueprint v1.
- Entidade caso.
- Fila básica.
- Conversa espelhada.
- Corredor Allianz Residencial Family.
- Subcorredor Eletricista implementado.
- Slots jsonb.
- Dispatch packet.
- HITL via approval_requests.
- WhatsApp dry-run/rascunho.
- RAG local como apoio.
- Policy snapshot/manual/upload.
- Logs básicos.
- Golden tests.

### 20.2 Não entra no MVP

- envio WhatsApp automático em produção;
- portal real;
- Browserbase/Skyvern;
- InfoCap real obrigatório;
- todos os subcorredores implementados;
- autoevolução;
- web search;
- global knowledge pesado;
- multi-provider WhatsApp completo;
- voz/áudio real;
- relatórios avançados.

---

## 21. Plano pós-MVP

### 21.1 InfoCap

```txt
42I0 — InfoCap Connector Design
42I1 — InfoCap Read-only Connector
42I2 — Policy Snapshot Extraction
42I3 — Coverage Evidence Automation
```

### 21.2 WhatsApp

```txt
42W1 — WhatsApp Provider Strategy
42W2 — Multi-instance Channel Model
42W3 — Provider Adapter Abstraction
42W4 — Controlled Real Send
```

### 21.3 Portais

```txt
42P1 — Portal/Browser Automation Strategy
42P2 — Browser Session Vault
42P3 — Portal Dry-run
42P4 — Controlled Portal Action
```

### 21.4 Subcorredores

```txt
42B8 — Encanador
42B9 — Chaveiro
42B10 — Desentupimento
42B11 — Eletrodomésticos
```

### 21.5 Autoevolução

```txt
44E0 — Self-Evolution Governance SPEC
44E1 — Learning Candidate Table
44E2 — Human Review
44E3 — Sandbox Promotion
44E4 — Eval-based Promotion
```

---

## 22. Sequência de batches recomendada agora

### Documentação canônica criada pelo Architect

1. `SPEC-005 — Atendimento Runtime Architecture & Attendance Boundary Blueprint v1`  
   Este documento.

2. `SPEC-006 — Allianz Residencial Corridor Family & Eletricista MVP`  
   Próximo documento estratégico a ser criado pelo Architect.

### Depois: execução pelo Claude/Codex

```txt
42S0 — Save SPEC-005 in repo + README link
42A4S — Seed Attendance Sandbox Agent (sem produção)
42B2 — SPEC-006 Allianz Residencial Family / Eletricista MVP
42B3 — SQL mínimo de casos/corredores/dispatch
42B4 — UI Fila/Casos/Conversas MVP
42B5 — Runtime assistido do corredor
42B6 — WhatsApp dry-run/HITL
42B7 — Golden tests
43MVP — E2E acceptance
```

---

## 23. Critérios de aceite da SPEC-005

A SPEC está aprovada se:

- separa Core e Attendance;
- define caso como entidade central;
- trata corredor como workflow estruturado;
- preserva Smith;
- não usa RAG como motor;
- inclui InfoCap/policy evidence na arquitetura;
- abstrai WhatsApp provider;
- define HITL;
- considera persona customizável sem quebrar segurança;
- modela Allianz como família, não Eletricista isolado;
- define MVP e pós-MVP;
- cria base para SQL/UI/runtime posterior.

---

## 24. Próxima decisão

Depois desta SPEC, a próxima entrega estratégica deve ser:

```txt
SPEC-006 — Allianz Residencial Corridor Family & Eletricista MVP
```

Ela deve detalhar:

- registry da família;
- subcorredores;
- Eletricista completo;
- slots;
- fases;
- perguntas;
- dispatch packet específico;
- guardrails;
- mensagens de segurado;
- dossiê interno;
- golden tests;
- readiness;
- critérios de implementação.

Somente depois de SPEC-006 devemos criar SQL.

---

## 25. Resumo final

O AutoBrokers não deve construir “um robô de WhatsApp”. Deve construir uma plataforma de atendimento operacional agentica, multi-tenant, com estado, corredor, evidência, ferramentas, HITL, RAG e memória.

O MVP não precisa acionar seguradora real sem humano. Precisa provar que o sistema consegue transformar uma solicitação de assistência em um caso estruturado e conduzir todo o processo com segurança.

A arquitetura vencedora é:

```txt
Core interno
  → cria/orienta/coordena

Attendance Agent
  → conversa com segurado dentro do caso

Case Runtime
  → estado, status, prioridade, evidência

Corridor Runtime
  → fases, slots, subcorredor, next step

Dispatch Packet
  → pacote estruturado para canal de execução

Vault/HITL
  → aprovação antes de ação externa

Smith
  → runtime agentico preservado
```

Essa é a fundação correta para crescer para 1000 corretoras, múltiplos canais, múltiplos corredores, múltiplas seguradoras e automação real futura.
