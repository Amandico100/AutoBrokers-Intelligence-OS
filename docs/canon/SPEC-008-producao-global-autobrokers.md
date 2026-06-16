# SPEC GLOBAL — AutoBrokers.ai Produção 100/100

**Arquivo sugerido:** `docs/canon/SPEC-008-producao-global-autobrokers.md`  
**Status:** documento estratégico/canônico de execução — versão de transição para produção  
**Escopo:** projeto completo AutoBrokers Intelligence OS: Atendimento, Core/Jarvys, Personalização, Auxiliares, RAG/Knowledge, Vault/Connectors, WhatsApp, Observabilidade, Segurança, Produto e Operação.  
**Última atualização de contexto:** 16/06/2026  
**Autoridade:** deve ser validado pelo fundador/CEO antes de virar regra operacional definitiva.

---

## 0. Objetivo deste documento

Esta SPEC existe para permitir que qualquer novo chat, Claude/Codex, arquiteto ou agente de execução entenda rapidamente:

1. O que é o AutoBrokers.ai.
2. Qual é o estágio atual real do MVP.
3. O que já está implementado.
4. O que ainda falta para produção.
5. Quais decisões estratégicas ainda precisam ser tomadas.
6. Como o sistema deve evoluir sem criar motor paralelo, gambiarras ou código macarrão.
7. Quais batches devem ser executados depois do bloco atual.
8. Como replicar a arquitetura para novos corredores, seguradoras, canais e corretoras.

O foco deste documento é o projeto completo. A SPEC específica de atendimento deve existir separadamente como:

`docs/canon/SPEC-007-atendimento-producao-autonomo.md`

Este documento global referencia a SPEC de atendimento, mas não a substitui.

---

## 1. Tese central do AutoBrokers.ai

AutoBrokers.ai é uma plataforma SaaS multi-tenant para corretoras de seguros.

A promessa central é transformar a corretora em uma operação com múltiplos agentes de IA que:

- atendem segurados;
- consultam apólices;
- interpretam documentos;
- conduzem assistência;
- apoiam sinistros;
- fazem follow-up;
- resumem atendimentos;
- apoiam vendas, renovações e gestão;
- operam com ferramentas reais;
- respeitam credenciais, permissões, LGPD e auditoria;
- escalam a capacidade operacional da corretora sem perder qualidade humana.

O sistema não deve ser um chatbot genérico. Ele deve ser um **sistema operacional de atendimento e inteligência para corretoras**.

---

## 2. Princípios não negociáveis

### 2.1 Smith é o runtime técnico; AutoBrokers é o produto

- **Smith / Agent Smith** é o runtime técnico: API, runtime de agentes, LLM, tools, LangGraph/LangChain, serviços, backend e base operacional.
- **AutoBrokers** é a camada de produto/domínio: corretoras, seguros, seguradoras, corredores, atendimento, apólices, canais, personalização, operação.

Nunca criar um segundo runtime paralelo fora do Smith.

### 2.2 Runtime determinístico governa; LLM interpreta

O runtime decide:

- estado;
- corredor;
- subcorredor;
- slots;
- risco;
- apólice;
- cobertura;
- readiness;
- dispatch;
- permissões;
- quando chamar tool;
- quando bloquear;
- quando escalar humano.

A LLM interpreta, conversa, explica, humaniza, reduz atrito e ajuda a entender contexto, mas não deve sozinha:

- confirmar cobertura sem evidência;
- acionar seguradora;
- enviar WhatsApp externo sensível;
- escolher apólice ambígua;
- expor PII;
- ignorar readiness/gates;
- criar regras operacionais próprias.

### 2.3 RAG apoia, não decide

RAG deve apoiar:

- explicação de regras;
- consulta de manuais;
- contexto de seguradoras;
- documentos internos da corretora;
- FAQs;
- treinamento de linguagem;
- entendimento de produtos.

RAG não deve ser fonte única para confirmação de cobertura quando houver necessidade de evidência de apólice, documento, InfoCap, seguradora ou validação humana.

### 2.4 Vault e permissões governam ferramentas

Toda credencial, conector e ação sensível devem passar por Vault/permissions/HITL.

- O agente nunca vê segredo.
- O frontend nunca recebe segredo bruto.
- Prompt nunca contém token, senha, service role, CPF completo desnecessário ou payload sensível.
- Logs devem ser sanitizados.
- Conector deve ser por tenant/corretora.

### 2.5 Nenhuma execução externa sem Action Engine

Dispatch Packet não é ação externa.

Para ação externa real, como WhatsApp da seguradora, portal, prestador ou API de assistência, deve haver:

1. Dispatch Packet estruturado.
2. Readiness aprovado.
3. Permissão do tenant.
4. Corredor homologado.
5. Canal externo configurado.
6. Política de HITL/autonomia.
7. Action Engine autorizando.
8. Logs e replay.
9. Retorno real antes de comunicar protocolo/prestador/previsão ao cliente.

---

## 3. Estado atual do projeto

### 3.1 Infra geral

Stack principal:

- Next.js / Web Dashboard;
- FastAPI / Backend Smith;
- Supabase;
- Redis;
- Qdrant;
- MinIO;
- LangGraph/LangChain;
- EasyPanel;
- GitHub principal: `Amandico100/AutoBrokers-Intelligence-OS`.

### 3.2 Core / Jarvys

Status: **MVP funcional, precisa evoluir para operador interno completo.**

O Core/Jarvys é o assistente interno da corretora, não o atendente do segurado.

Hoje ele já tem base de:

- identidade interna;
- auxiliares visíveis;
- RAG básico;
- conversa interna;
- separação de papéis.

Falta para produção:

- consultar casos de atendimento;
- consultar apólices via InfoCap de forma controlada;
- gerar relatórios;
- acionar auxiliares;
- criar tarefas;
- responder dúvidas internas da corretora usando dados reais;
- respeitar permissões por usuário;
- apresentar diagnósticos operacionais.

### 3.3 Atendimento externo / Attendance Agent

Status: **MVP avançado no dashboard/simulador; não produção WhatsApp ponta a ponta ainda.**

Concluído:

- caso de atendimento;
- corredor Allianz Residencial / Eletricista;
- coleta de risco;
- coleta de CPF;
- InfoCap via Vault;
- busca cliente;
- busca apólices;
- seleção de apólice;
- leitura de documento InfoCap;
- evidence pack;
- policy interpretation context;
- coverage readiness;
- dispatch dry-run;
- HITL coverage validation;
- dossiê;
- UI mínima;
- testes offline/goldens parciais.

Falta:

- WhatsApp inbound/outbound real conectado ao runtime de atendimento;
- buffer/debounce;
- roteamento de mensagens para cases;
- mídia/áudio/imagem/localização;
- Action Engine;
- canal de execução externo;
- acompanhamento até encerramento;
- goldens E2E de produção;
- observabilidade;
- hardening de segurança.

### 3.4 InfoCap

Status: **MVP real funcionando para cliente/apólice/documento, mas ainda limitado na leitura de coberturas detalhadas.**

Concluído:

- conexão por Vault;
- segredo cifrado no backend;
- diagnostics;
- login CorpAPI;
- `/cliente_cpf`;
- `/cliente_ligacoes`;
- `/documentos` fallback;
- `/documento`;
- múltiplas apólices;
- seleção por policy_ref;
- snapshot sanitizado;
- coverage_evidence;
- readiness;
- sem exposição de payload bruto.

Limitação atual:

- em alguns documentos, a InfoCap não retorna itens/coberturas detalhadas;
- então o sistema confirma existência/vigência da apólice, mas não deve afirmar cobertura específica;
- a leitura avançada de PDF/Document AI entra como próxima etapa de maturidade.

### 3.5 Dispatch / HITL

Status: **dry-run/HITL funcional.**

Concluído:

- `dispatch-dry-run`;
- dispatch readiness;
- dispatch packet sanitizado;
- `coverage-validation`;
- aprovação/reprovação/needs_more_info;
- bloqueio de envio externo;
- external_action sempre false no MVP;
- dossiê inclui readiness/dispatch.

Falta:

- Action Engine;
- envio externo controlado;
- approval_requests formal se necessário;
- captura de retorno externo;
- acompanhamento.

### 3.6 WhatsApp

Status: **arquitetura existente, mas ainda não conectada ao atendimento completo.**

Há estrutura Smith/Z-API:

- inbound webhook;
- conversations/messages;
- integração por company/agent;
- send message;
- buffer service citado;
- áudio service citado;
- dry-run global.

Riscos/gaps:

- token/client_token em plaintext na tabela `integrations`;
- webhook inbound sem autenticação forte;
- dry-run global, não por conexão;
- atendimento Allianz/InfoCap ainda validado no dashboard, não via WhatsApp real;
- precisa roteamento para cases/attendance runtime;
- precisa dedupe/idempotência;
- precisa tratar mensagens fragmentadas;
- precisa mídia.

### 3.7 Auxiliares

Status: **conceito e alguns auxiliares básicos prontos; execução real ainda incompleta.**

Auxiliares visíveis atuais:

- Resumo de Atendimentos;
- Follow-up WhatsApp.

Falta:

- execução real por tenant;
- permissões via Vault;
- scheduling;
- aprovação quando enviar WhatsApp;
- UI de configuração;
- logs e resultados;
- integração com casos.

### 3.8 Personalização da corretora

Status: **parcial.**

Já há telas/inícios para personalização, suporte humano, agentes etc.

Falta fechar:

- perfil público da corretora;
- tom de voz;
- horários;
- canais;
- contatos humanos;
- seguradoras habilitadas;
- corredores habilitados;
- política de autonomia;
- política de HITL;
- credenciais por conector;
- regras por usuário;
- limites de execução.

### 3.9 RAG / Knowledge / Memory

Status: **base existe, precisa virar produto operacional.**

Concluído:

- conceitos canônicos;
- RAG local testado;
- global knowledge inicial;
- memory/context architecture.

Falta:

- painel para bases de conhecimento;
- ingestão por tenant;
- escopos de conhecimento;
- provenance;
- evals de RAG;
- uso no atendimento sem decidir cobertura;
- uso no Core/Jarvys;
- versionamento de documentos.

---

## 4. Arquitetura-alvo do projeto completo

A arquitetura-alvo deve ser organizada assim:

```txt
Canal do cliente
  ↓
WhatsApp / Web / Voz / Portal
  ↓
Ingress Adapter
  ↓
Buffer + Dedup + Session Resolver
  ↓
Attendance Runtime / Core Runtime
  ↓
Context Assembly
  ↓
Corredor / Subcorredor / Tool Planner
  ↓
Vault / Connectors / RAG / Memory / Media Tools
  ↓
Evidence + Readiness + Dispatch Packet
  ↓
Action Engine
  ↓
External Channel Adapter
  ↓
Retorno real
  ↓
Resposta ao cliente + acompanhamento + encerramento
```

Cada camada deve ser testável, auditável, substituível e governada.

---

## 5. Módulos do sistema

## 5.1 Dashboard

Responsável por:

- visão geral;
- atendimento/casos;
- fila;
- detalhe;
- simulador;
- personalização;
- agentes;
- auxiliares;
- conexões/vault;
- RAG/knowledge;
- relatórios;
- billing/uso;
- configurações por tenant.

Gaps principais:

- padronizar navegação;
- finalizar UI de personalização;
- tornar atendimento real via WhatsApp visível na fila;
- adicionar painéis de health/diagnostics;
- estado de conectores;
- auditoria por caso.

## 5.2 Backend Smith

Responsável por:

- runtime técnico;
- LLM factory;
- tools;
- FastAPI;
- connectors internos;
- agent reply;
- WhatsApp service;
- Infocap connector;
- segurança server-side;
- logs.

Gaps:

- padronizar conector provider adapter;
- criptografar credenciais WhatsApp;
- autenticar webhooks;
- implementar Action Engine;
- padronizar observability.

## 5.3 Supabase

Responsável por:

- Auth;
- empresas/tenants;
- agentes;
- atendimentos;
- conversas;
- mensagens;
- casos;
- corredores;
- dispatch;
- vault;
- knowledge metadata;
- billing.

Gaps:

- revisar RLS;
- advisors security/performance;
- políticas multi-tenant;
- índices;
- enum/status final;
- migrations limpas;
- backups.

## 5.4 Vault / Connectors

Responsável por:

- modelos de conectores;
- conexões por tenant;
- segredos cifrados;
- permissões;
- HITL;
- auditoria;
- bridge para runtime.

Conectores prioritários:

1. InfoCap;
2. WhatsApp Z-API;
3. WhatsApp Evolution futuro;
4. Google Drive/Docs;
5. Supabase;
6. Email/Gmail futuro;
7. Portais seguradoras futuro;
8. Document AI/Azure futuro.

Gaps:

- consolidar todos os conectores no mesmo padrão;
- evitar `integrations` plaintext;
- permission grants por agente/auxiliar/corredor.

---

## 6. Atendimento — visão operacional integrada

A SPEC de Atendimento deve governar o fluxo detalhado. Aqui está o resumo global.

Fluxo ideal:

1. Cliente manda mensagem.
2. Buffer junta mensagens fragmentadas.
3. Runtime identifica sessão/case.
4. Classifica intenção.
5. Verifica risco.
6. Seleciona corredor/subcorredor.
7. Coleta identidade mínima.
8. Consulta InfoCap/apólice.
9. Seleciona apólice.
10. Lê documento/evidência.
11. Avalia cobertura/readiness.
12. Coleta slots operacionais.
13. Prepara dispatch.
14. Solicita Action Engine.
15. Aciona canal externo autorizado.
16. Captura retorno real.
17. Comunica cliente.
18. Acompanha.
19. Encerra.
20. Registra replay/eval.

Hoje estamos entre os passos 1-13 no dashboard/simulador, sem canal real completo e sem ação externa real.

---

## 7. WhatsApp — plano de produção

Próximo bloco principal: `42W0 — WhatsApp Inbound Buffer, Case Routing & Security Hardening`.

Objetivo:

- ligar WhatsApp real ao Attendance Runtime;
- garantir segurança antes de produção;
- preparar controlled test.

Requisitos:

1. Inbound adapter seguro.
2. Webhook auth/signature/token validation.
3. Idempotência por messageId.
4. Buffer/debounce por telefone/company/agent.
5. Case routing:
   - case aberto;
   - novo atendimento;
   - acompanhamento;
   - humano/handoff;
   - mensagem fora de escopo.
6. Media envelope:
   - texto;
   - áudio;
   - imagem;
   - documento;
   - localização.
7. Dry-run por conexão/tenant.
8. Outbound guard:
   - só responder cliente quando autorizado;
   - sem envio externo de seguradora.
9. Logs sanitizados.
10. Fixtures/evals.

---

## 8. Action Engine — plano

O Action Engine é a camada que autoriza execução externa.

Ele deve receber:

- dispatch_packet;
- dispatch_readiness;
- coverage_readiness;
- tenant policy;
- corridor policy;
- connector permissions;
- approval state;
- risk flags.

E decidir:

- deny;
- draft only;
- HITL required;
- ready for controlled send;
- send allowed;
- pause;
- escalate.

Estados sugeridos:

- `blocked`;
- `missing_data`;
- `hitl_required`;
- `ready_for_human_approval`;
- `approved_for_controlled_send`;
- `sent`;
- `external_pending`;
- `external_confirmed`;
- `external_failed`;
- `closed`.

No MVP, apenas dry-run/HITL. Depois, controlled send.

---

## 9. External Execution Adapters

Após WhatsApp de cliente, vem execução externa.

Tipos:

1. WhatsApp da seguradora;
2. Portal seguradora;
3. API de assistência;
4. Telefone/voz;
5. Email;
6. prestador.

Para Allianz Residencial/Eletricista, o primeiro adapter deve ser provavelmente WhatsApp/assistência, se houver canal operacional real configurado.

Requisitos:

- separar canal do cliente vs canal da seguradora;
- usar conversas diferentes;
- não expor bastidores ao cliente;
- capturar retorno real;
- interpretar menu/resposta;
- responder exatamente o que o canal pede;
- gravar transcript;
- extrair protocolo/prestador/previsão;
- confirmar ao cliente só após retorno real.

---

## 10. Mídia, Documentos e Document AI

A camada de mídia deve entrar após o WhatsApp básico.

Objetivos:

- receber áudio;
- transcrever;
- receber imagem;
- classificar;
- receber PDF/apólice;
- extrair texto/tabelas;
- redigir PII;
- criar media evidence;
- vincular ao case;
- permitir LLM interpretar com segurança.

Ferramentas futuras:

- Docling;
- Google Document AI;
- Azure Document Intelligence;
- OCR fallback;
- Vision LLM;
- embeddings/RAG.

Regra:

Mídia/documento não é verdade final. É evidência potencial que precisa de provenance e guardrails.

---

## 11. RAG e Knowledge

RAG global:

- regras gerais de atendimento;
- glossário de seguros;
- políticas internas;
- templates;
- manuais de seguradoras;
- documentação dos corredores.

RAG tenant:

- procedimentos da corretora;
- contatos;
- políticas de atendimento;
- seguradoras habilitadas;
- documentos internos.

RAG case/document:

- documentos enviados pelo cliente;
- apólice PDF;
- prints;
- transcrições;
- evidências.

Regras:

- RAG deve trazer fontes/provenance;
- RAG não deve decidir autorização;
- RAG não deve vazar conteúdo sensível;
- RAG precisa de evals.

---

## 12. Core/Jarvys — produto interno

Objetivo:

Ser o copiloto interno da corretora.

Funcionalidades-alvo:

1. Perguntar status de casos.
2. Buscar atendimentos travados.
3. Resumir dia.
4. Ver apólices via InfoCap.
5. Gerar relatório de produtividade.
6. Sugerir melhorias.
7. Acionar auxiliares.
8. Consultar RAG da corretora.
9. Explicar por que um atendimento está bloqueado.
10. Preparar handoff.
11. Criar tarefas.
12. Gerar mensagens aprováveis.

Gaps:

- tools internas;
- autorização por usuário;
- UI;
- memory operacional;
- integração com casos.

---

## 13. Auxiliares

Auxiliares são agentes/rotinas específicos, não runtime principal.

Prioridade:

1. Resumo de atendimentos.
2. Follow-up WhatsApp.
3. Casos travados.
4. Renovação.
5. Cobrança.
6. Pesquisa de satisfação.
7. Auditoria de risco.
8. Relatório diário.

Regras:

- Auxiliar usa Vault/tools, não credenciais próprias.
- Auxiliar não conversa sem permissão.
- Auxiliar gera draft quando exige aprovação.
- Auxiliar não governa atendimento principal.

---

## 14. Personalização e Tenant OS

Cada corretora precisa configurar:

- nome comercial;
- razão social;
- horários;
- responsáveis;
- canais;
- números WhatsApp;
- seguradoras;
- permissões;
- corredores habilitados;
- tom de voz;
- mensagens padrão;
- política de autonomia;
- política de handoff;
- LGPD;
- contatos de emergência;
- integrações.

Sem isso, não há produção multi-tenant segura.

---

## 15. Segurança e LGPD

P0 antes de produção real:

1. Repo privado.
2. Rotação de todas as chaves já expostas em chats/arquivos.
3. Cifrar WhatsApp integrations token/client_token.
4. Webhook auth.
5. RLS Supabase revisado.
6. Logs sem PII.
7. Secrets fora do frontend.
8. Admin API protegida.
9. Backups.
10. Auditoria de permissões.

P1:

- rate limit;
- IP allowlist quando possível;
- alertas;
- anomaly detection;
- retention policy;
- data export/delete.

---

## 16. Observabilidade, Replays e Evals

Produção exige:

- trace por atendimento;
- trace por message turn;
- tool calls;
- connector calls;
- readiness decisions;
- dispatch packets;
- action engine decisions;
- handoff reasons;
- latency;
- errors;
- retries;
- cost/tokens;
- eval score.

Goldens mínimos:

1. Allianz Residencial Eletricista — fluxo feliz com cobertura confirmada.
2. Allianz Residencial Eletricista — apólice localizada sem cobertura detalhada.
3. Multiple policies.
4. Risco alto.
5. CPF incorreto.
6. Cliente sem apólice.
7. Mensagens fragmentadas.
8. Áudio.
9. Imagem.
10. Localização.
11. Handoff.
12. Coverage rejected.
13. WhatsApp reconnect.
14. Duplicate webhook.
15. Timeout InfoCap.

---

## 17. Roadmap atualizado

### Etapa atual

- 42B6 validado no dashboard/simulador.

### Próximos batches

#### 42W0 — WhatsApp Inbound Buffer, Case Routing & Security Hardening

Inclui:

- buffer/debounce;
- webhook security;
- idempotência;
- routing to attendance case;
- Z-API provider adapter;
- dry-run por conexão;
- token encryption migration/compat;
- logs.

#### 42W1 — WhatsApp Attendance Runtime Controlled Test

Inclui:

- enviar e receber no WhatsApp real/controlado;
- conectar ao Attendance Runtime;
- testar CPF/InfoCap/dispatch dry-run pelo canal real;
- sem acionar seguradora.

#### 42B7.2 — Final E2E Goldens

Inclui:

- dashboard + WhatsApp + InfoCap + policy-select + dispatch.

#### 42X0 — Action Engine Dry-run

Inclui:

- approval policies;
- external action decision;
- adapter contract.

#### 42X1 — Allianz External Execution Adapter

Inclui:

- WhatsApp da seguradora ou canal definido;
- enviar dispatch controlado;
- capturar resposta;
- sem produção aberta.

#### 42X2 — Controlled Real Execution

Inclui:

- poucos casos reais;
- humano supervisionando;
- logs e replay.

#### SEC-001 — Production Security Hardening

Inclui:

- repo privado;
- rotação de chaves;
- RLS;
- advisors;
- secrets;
- logs;
- backup.

---

## 18. Critérios de produção

O AutoBrokers só deve ir para produção com atendimento real quando:

1. WhatsApp seguro.
2. Case routing confiável.
3. InfoCap real funcionando.
4. Dispatch dry-run funcionando.
5. Action Engine implementado.
6. Sem envio externo sem permissão.
7. Observability mínima.
8. Goldens E2E verdes.
9. Handoff humano funcional.
10. Credenciais rotacionadas.
11. Repo privado.
12. RLS revisado.
13. Tenant configurado.
14. Corredor homologado.
15. Plano de rollback.

---

## 19. Replicação para novos corredores

Modelo de replicação:

1. Definir família: residencial, auto, sinistro, renovação.
2. Definir seguradora.
3. Definir canal: WhatsApp, portal, telefone, API.
4. Definir subcorredor.
5. Mapear intent.
6. Mapear slots.
7. Mapear risco.
8. Mapear apólice/evidência.
9. Mapear readiness.
10. Criar dispatch contract.
11. Criar adapter externo.
12. Criar goldens.
13. Controlled test.
14. Homologar.
15. Ativar por tenant.

---

## 20. Handoff para novo chat

Quando abrir novo chat, enviar:

1. Esta SPEC global.
2. SPEC de atendimento.
3. Último resumo do teste 42B6.
4. Caminho repo principal.
5. Caminho repo legado ResultVision.
6. Próximo batch: 42W0.
7. Regra: não criar motor paralelo; usar Smith.
8. Regra: não expor segredo/PII.
9. Regra: WhatsApp antes de Action Engine, Action Engine antes de execução externa.
10. Regra: RAG apoia, não decide cobertura.

Prompt de abertura sugerido:

```txt
Você está assumindo o projeto AutoBrokers.ai / AutoBrokers Intelligence OS.
Leia primeiro:
- docs/canon/SPEC-007-atendimento-producao-autonomo.md
- docs/canon/SPEC-008-producao-global-autobrokers.md
- docs/canon/SPEC-005-atendimento-runtime-architecture.md
- docs/canon/SPEC-006-allianz-residencial-corredor-eletricista-mvp.md
- docs/canon/ADR-001-runtime.md
- docs/canon/ADR-002-vault.md
- docs/canon/ADR-003-atendimento.md

Estado atual:
- InfoCap real funcionando.
- Policy select funcionando.
- Evidence pack funcionando.
- Coverage readiness funcionando.
- Dispatch dry-run/HITL validado no dashboard.

Próxima missão:
Executar 42W0 — WhatsApp Inbound Buffer, Case Routing & Security Hardening.

Não criar runtime paralelo.
Não usar n8n como orquestrador.
Não expor segredo/PII.
Usar Smith como runtime.
Usar Vault para conectores.
Usar readiness/gates antes de ações externas.
```

---

## 21. Decisão final desta SPEC

O projeto está no caminho certo, mas ainda não está pronto para produção autônoma.

Nível atual estimado:

- Dashboard/simulador de atendimento: 88/100.
- InfoCap/evidence/readiness: 86/100.
- Dispatch dry-run/HITL: 84/100.
- WhatsApp real: 45/100.
- Ação externa real: 20/100.
- Produção autônoma ponta a ponta: 30/100.
- SaaS completo multi-tenant: 60/100.

Próxima etapa real de produção: **WhatsApp seguro conectado ao Attendance Runtime.**

