# SPEC-ATENDIMENTO-PRODUCAO-AUTOBROKERS

**Projeto:** AutoBrokers.ai / AutoBrokers Intelligence OS  
**Escopo:** Atendimento de segurados de ponta a ponta, com foco inicial em Allianz Residencial / Eletricista, replicável para outros corredores, seguradoras, ramos e canais.  
**Status:** Documento de consolidação estratégica e técnica para continuidade do desenvolvimento.  
**Data:** 2026-06-16  
**Autor operacional:** ChatGPT — suporte fundador AutoBrokers.ai  

---

## 0. Objetivo deste documento

Este documento existe para evitar perda de contexto e impedir que o desenvolvimento do atendimento AutoBrokers fique fragmentado, incompleto ou dependente da memória de uma conversa longa.

Ele consolida:

1. o objetivo final do atendimento;
2. o estado atual real do MVP;
3. a arquitetura correta;
4. as fontes/documentos que precisam ser lidos;
5. o que já foi implementado;
6. o que ainda falta;
7. os riscos de produção;
8. a ordem de execução dos próximos blocos;
9. os critérios de pronto;
10. o modelo replicável para outros corredores.

O objetivo final é permitir que um segurado envie mensagem para o WhatsApp da corretora e seja atendido de ponta a ponta por agentes de IA, de forma humana, inteligente, segura, rastreável, multi-tenant, sem inventar cobertura, sem expor PII, sem travar e sem depender de humano salvo em exceções reais.

---

## 1. Estado atual resumido

O atendimento AutoBrokers já possui uma base forte no dashboard/simulador:

- criação de caso;
- conversa com segurado;
- classificação de assistência residencial;
- risco mínimo;
- coleta de CPF;
- consulta real InfoCap via Vault/tenant;
- localização de cliente;
- localização de múltiplas apólices;
- seleção de apólice;
- leitura de detalhe via `/documento`;
- `policy_snapshot`;
- `coverage_evidence`;
- `policy_interpretation_context`;
- `coverage_readiness`;
- dispatch packet dry-run;
- HITL de cobertura;
- dossiê com evidência e dispatch;
- UI mínima no detalhe do caso;
- testes offline de evidence, coverage readiness e dispatch readiness.

O sistema ainda não está pronto para produção autônoma real porque ainda faltam:

- WhatsApp real de entrada conectado ao Attendance Runtime novo;
- buffer/debounce/deduplicação/idempotência;
- webhook seguro;
- credenciais WhatsApp cifradas;
- case routing por telefone/conversa/canal;
- mídia, áudio, localização, imagem e documentos no runtime de atendimento;
- Action Engine para execução externa;
- canal externo da seguradora/prestador;
- captura real de protocolo/prestador/previsão;
- acompanhamento até encerramento;
- observabilidade e replays E2E;
- homologação controlada por tenant/corredor;
- segurança de produção e rotação de chaves.

---

## 2. Nota por camada

### 2.1 Dashboard/simulador de atendimento

**Nota atual:** 84/100.

Funciona como MVP operacional para validar o fluxo de atendimento com InfoCap, apólice e dispatch dry-run. Ainda precisa testes E2E finais e refinamento de UI.

### 2.2 WhatsApp real do segurado

**Nota atual:** 45/100.

Existe arquitetura antiga/nova mapeada, mas ainda falta integrar o inbound real ao Attendance Runtime de forma segura e governada.

### 2.3 Execução externa / seguradora / prestador

**Nota atual:** 20/100.

Ainda não há Action Engine real, envio para seguradora, captura de protocolo, prestador, previsão nem acompanhamento automático.

### 2.4 Produção autônoma sem humano

**Nota atual:** 25/100.

Autonomia real exige canal, segurança, homologação, observabilidade, testes de regressão e autorização por nível.

---

## 3. Definições fundamentais

### 3.1 Smith / Agent Smith

Smith é o runtime técnico base: backend, LLM factory, LangGraph, APIs, ferramentas, segurança e orquestração técnica.

Smith não é o produto de seguros. Ele é a base técnica onde o produto AutoBrokers roda.

### 3.2 AutoBrokers

AutoBrokers é a camada de produto/domínio de corretoras de seguros. Define atendimento, corredores, apólices, seguradoras, auxiliares, personalização e processos.

### 3.3 Core / Jarvys

Assistente interno da corretora. Não atende segurado diretamente. Ajuda o usuário interno a consultar casos, entender status, acionar auxiliares, pedir relatórios e operar o sistema.

### 3.4 Attendance Agent

Agente que conversa com o segurado. Deve ser humano, inteligente, objetivo, seguro e governado por runtime. Ele não deve virar formulário, mas também não pode improvisar autorização/cobertura.

### 3.5 Corredor

Workflow estruturado de atendimento por família, seguradora, ramo, canal e serviço. Exemplo: Allianz Residencial / Eletricista.

O corredor define fases, slots obrigatórios, guardrails, decisões, readiness e critérios de execução.

### 3.6 Subcorredor

Especialização dentro de um corredor. Exemplo: Eletricista dentro de Assistência Residencial.

### 3.7 Auxiliar

Agente/rotina específica ativável por tenant, como follow-up, resumo, cobrança, renovação, auditoria de casos. Não é o runtime principal.

### 3.8 RAG

Base de conhecimento usada para explicar, contextualizar e recuperar documentos/regras. RAG não decide cobertura, não executa ação e não substitui evidence pack.

### 3.9 Tool

Ferramenta invocável pelo runtime, como InfoCap, WhatsApp, dispatch, storage, Document AI, OCR, mídia, dossiê. Tools precisam de contrato, autorização, logs e retorno sanitizado.

### 3.10 Vault

Camada de segurança para credenciais, conectores, permissões e HITL. Segredos nunca entram em prompt, RAG, memória, logs públicos ou frontend.

### 3.11 HITL

Human-in-the-loop. Deve ser exceção operacional, não dependência constante. No MVP, certas ações ainda ficam com HITL até homologação.

---

## 4. Princípios não negociáveis

1. O agente deve ser inteligente, mas não soberano sobre cobertura e execução.
2. Runtime determinístico decide estado, autorização, readiness e blockers.
3. LLM conversa, interpreta evidências e reduz atrito.
4. Tools buscam fatos e executam ações autorizadas.
5. RAG apoia, não governa.
6. Vault protege credenciais e permissões.
7. Nunca confirmar cobertura sem fonte/evidência.
8. Nunca acionar seguradora/prestador sem readiness e autorização.
9. Nunca expor CPF, telefone cru, endereço completo, token, senha ou payload bruto.
10. Nenhum n8n, workflow legado, prompt solto ou helper pode virar cérebro paralelo.
11. Toda fala ao cliente deve ser customer-safe.
12. Toda ação externa deve ter audit trail.
13. Todo caso deve ter próximo passo.
14. Toda exceção deve gerar dossiê ou HITL claro.
15. O sistema precisa ser replicável para novos corredores.

---

## 5. Fontes que devem ser lidas por quem continuar o projeto

### 5.1 Repositório novo

`Amandico100/AutoBrokers-Intelligence-OS`

Ler especialmente:

- `docs/canon/README.md`
- `docs/canon/PRD-001-visao-produto.md`
- `docs/canon/ROADMAP-001-execucao.md`
- `docs/canon/ADR-001-runtime.md`
- `docs/canon/ADR-002-vault.md`
- `docs/canon/ADR-003-atendimento.md`
- `docs/canon/SPEC-004-agent-intelligence-context-architecture.md`
- `docs/canon/SPEC-005-atendimento-runtime-architecture.md`
- `docs/canon/SPEC-006-allianz-residencial-corredor-eletricista-mvp.md`
- `docs/canon/design/2026-06-claude-design/39A4.0-whatsapp-architecture-recon.md`
- `docs/canon/design/2026-06-claude-design/42B6-dispatch-packet-dry-run-hitl-report.md`
- relatórios 42B5K, 42B5L, 42B7, 42I2.x, 42I3A, 42I3B.

Código-chave:

- `app/api/attendance/cases/*`
- `app/api/attendance/cases/[caseId]/runtime/*`
- `lib/attendance/*`
- `backend/app/api/attendance_agent_reply.py`
- `backend/app/api/infocap_connector.py`
- `app/dashboard/atendimentos/*`
- scripts de golden/evidence/readiness.

### 5.2 Repositório antigo / ResultVision

`Amandico100/ResultVision`, branch `clean/agent-runtime-foundation-orphan`.

Usar como referência de domínio, não como runtime.

Arquivos relevantes:

- `server/lib/policyDataProvider/corpInfocapPolicyDataProvider.ts`
- `server/lib/policyDataProvider/types.ts`
- `server/lib/policyDataProvider/policy-selection.ts`
- `server/lib/insurer-whatsapp/*`
- `server/lib/whatsapp-inbox/*`
- `server/lib/n8n/*`
- `docs/plans/2026-04-09-insurer-whatsapp-assistance-engine.md`
- relatórios de Evolution/WhatsApp.

### 5.3 Agent OS antigo / cérebro

Pasta local informada:

`C:\Users\amand\Projetos\AUTOBROKERS RESULTA\.worktrees\hotfix-runtime-bundle\AUTOBROKERS_AGENT_OS_WORKSPACE\00_AGENT_OS_NOVO\AUTOBROKERS_AGENT_OS`

Pastas que devem ser auditadas:

- `00_CONSTITUICAO`
- `01_ORQUESTRADOR`
- `02_RUNTIME_CONVERSACIONAL`
- `03_EXECUTION_PLANE`
- `04_CONVERSA_COM_CLIENTE`
- `05_SQUADS`
- `06_SKILLS`
- `07_CORREDORES`
- `08_PLAYBOOKS_DE_CANAL`
- `09_CONTRATOS`
- `10_GUARDRAILS`
- `11_MIDIA_E_DOCUMENTOS`
- `12_REPLAYS_E_GOLDENS`
- `13_OBSERVABILIDADE_E_EVALS`
- `17_INTELIGENCIA_OPERACIONAL`
- `18_DOCS_100_WORKSPACE`, se existir.

Objetivo da leitura: assimilar conceitos, contratos, checklists, mensagens e edge cases. Não copiar arquitetura antiga bruta.

---

## 6. Fluxo ideal de atendimento de ponta a ponta

### 6.1 Entrada

O cliente envia mensagem no WhatsApp da corretora. O webhook recebe, valida autenticidade, identifica tenant/agente/conexão e normaliza payload.

### 6.2 Buffer/debounce

Se o cliente envia 3 mensagens seguidas, o sistema aguarda janela curta, consolida e responde uma vez de forma contextual.

Exemplo:

- “Oi”
- “estou sem luz”
- “só na cozinha”

O agente deve entender como um único turno: cliente precisa de assistência elétrica, área afetada cozinha.

### 6.3 Case routing

O runtime deve decidir se é:

- caso novo;
- continuação de caso ativo;
- acompanhamento de protocolo;
- dúvida sobre apólice;
- sinistro;
- reclamação;
- assunto fora do escopo;
- humano.

### 6.4 Abertura humanizada

O agente responde curto e humano, sem parecer formulário:

“Entendi. Vou te ajudar com isso. Antes de seguir, tem cheiro de queimado, faísca, fumaça ou algum risco imediato?”

### 6.5 Risco

Risco físico vem antes de cobertura. Se alto risco, orientar segurança e handoff.

### 6.6 Identidade

Coletar CPF/CNPJ ou outro identificador somente quando necessário para consultar apólice.

### 6.7 Consulta de apólice

Usar InfoCap via Vault/tenant:

- `/login`
- `/cliente_cpf`
- `/cliente_ligacoes`
- `/documentos`
- `/documento`

Retorno sempre sanitizado.

### 6.8 Seleção de apólice

Se uma apólice relevante: selecionar com segurança. Se múltiplas: pedir seleção ou usar dados adicionais, sem escolher arbitrariamente.

### 6.9 Evidence Pack

Montar evidência estruturada:

- apólice localizada;
- vigência;
- status;
- seguradora;
- produto;
- sinais de assistência;
- lacunas;
- confidence;
- human_required;
- limitações.

### 6.10 Interpretação inteligente

O agente deve interpretar evidências com inteligência, mas sem inventar.

Deve diferenciar:

- apólice localizada;
- cobertura específica confirmada;
- cobertura ambígua;
- cobertura não encontrada;
- validação humana necessária.

### 6.11 Coleta de dados operacionais

Coletar somente o necessário:

- área afetada;
- tipo de problema;
- endereço/locação;
- contato no local;
- disponibilidade;
- dados adicionais exigidos pelo corredor.

### 6.12 Dispatch Readiness

Avaliar se pode preparar acionamento:

- identidade pronta;
- apólice selecionada;
- cobertura confirmada ou aprovada;
- risco ok;
- slots completos;
- endereço pronto;
- canal externo autorizado;
- tenant autorizado.

### 6.13 Dispatch Packet

Montar pacote sanitizado para execução, inicialmente dry-run/HITL.

### 6.14 Action Engine

Autoriza ou bloqueia side effects. Deve checar:

- tenant;
- corredor;
- canal;
- permissão;
- homologação;
- readiness;
- HITL;
- idempotência.

### 6.15 Canal externo

Para produção futura, o sistema precisa falar com a seguradora/prestador:

- WhatsApp da seguradora;
- portal;
- API;
- telefone/voz, se necessário.

### 6.16 Retorno real

Capturar:

- protocolo;
- prestador;
- previsão;
- negativa;
- pendência;
- pedido de dados;
- transferências.

### 6.17 Comunicação ao segurado

Responder de forma humana, sem bastidor e sem prometer o que não existe.

### 6.18 Acompanhamento

Monitorar até encerrar:

- retorno do prestador;
- reagendamento;
- atraso;
- conclusão;
- reclamação;
- CSAT;
- dossiê final.

---

## 7. O que está implementado hoje no fluxo Allianz Residencial / Eletricista

### 7.1 Implementado

- Case API.
- Runtime step/reply.
- Intake de risco.
- Coleta de CPF.
- InfoCap via Vault.
- Secret storage seguro para InfoCap.
- Diagnostics de conexão.
- Probe de InfoCap.
- Lookup por CPF em `/cliente_cpf`.
- Busca de apólices por cliente.
- Leitura de detalhe por `/documento`.
- Normalização de apólice.
- Multiple matches.
- Policy select.
- Evidence pack.
- Policy interpretation context.
- Coverage readiness.
- Dispatch dry-run.
- Coverage validation HITL.
- Handoff dossier.
- UI mínima.
- Testes offline.

### 7.2 Ainda não implementado

- WhatsApp inbound real conectado ao attendance runtime novo.
- WhatsApp outbound customer-safe usando gates do novo atendimento.
- Cifra de tokens WhatsApp em `integrations`.
- Autenticação de webhook inbound.
- Buffer/debounce real de mensagens do atendimento novo.
- Media/document evidence pipeline.
- Policy Q&A robusto com RAG/documentos.
- Action Engine real.
- Canal de execução Allianz real.
- Parsing de retorno real da seguradora.
- Acompanhamento automático.
- Encerramento/CSAT.
- E2E real em ambiente controlado.

---

## 8. WhatsApp: arquitetura recomendada

### 8.1 Caminho recomendado

Usar provider adapter com Z-API primeiro, Evolution depois se necessário.

Não usar n8n como orquestrador principal.

n8n pode ser adapter opcional, nunca cérebro.

### 8.2 Requisitos de WhatsApp inbound

- webhook autenticado;
- validação de provider;
- deduplicação por message id;
- idempotência;
- buffer/debounce;
- normalização de texto, áudio, mídia, localização;
- identificação de tenant e agente;
- case routing;
- persistência de mensagens;
- rate limit;
- logs mascarados;
- dry-run por conexão;
- replay.

### 8.3 Requisitos de WhatsApp outbound

- mensagem customer-safe;
- aprovação quando necessário;
- checagem de `dispatch_readiness`;
- checagem de status da conversa;
- não enviar quando humano assumiu;
- não enviar quando caso bloqueado;
- fallback se provider falhar;
- log de entrega;
- idempotência.

---

## 9. Mídia, documentos e imagens

A mídia enviada pelo segurado não pode ir direto para a LLM.

Pipeline necessário:

1. receber mídia;
2. baixar de forma segura;
3. classificar tipo;
4. verificar tamanho/risco;
5. armazenar no MinIO/Supabase Storage;
6. redigir PII se necessário;
7. transcrever áudio;
8. OCR/imagem quando útil;
9. extrair evidência;
10. vincular ao case;
11. promover para evidence apenas se confiável;
12. nunca enviar OCR bruto ao cliente.

Documentos de apólice/PDF devem entrar depois da InfoCap estruturada. A ordem correta é:

1. API estruturada InfoCap;
2. detalhe `/documento`;
3. PDF/anexo se necessário;
4. Document AI / Azure / OCR;
5. evidence pack;
6. LLM interpreta com contexto seguro.

---

## 10. Inteligência do agente

O agente deve ser semelhante a um atendente excelente, não a um formulário.

Ele precisa:

- entender linguagem natural;
- acolher o cliente;
- consolidar mensagens fragmentadas;
- responder perguntas fora do fluxo;
- explicar limites;
- interpretar evidência;
- voltar ao fluxo sem parecer robótico;
- não repetir pergunta;
- lembrar o que já foi informado;
- lidar com ansiedade e urgência;
- usar tom humano;
- nunca inventar cobertura;
- chamar humano só quando necessário.

Arquitetura correta:

- Runtime determinístico decide estado e autorização.
- LLM/Smith gera linguagem, interpreta contexto e responde dúvidas.
- Tools buscam fatos.
- RAG recupera conhecimento.
- Evidence pack governa cobertura.
- HITL entra em exceções.

---

## 11. RAG e conhecimento

RAG deve ser usado para:

- regras gerais da seguradora;
- FAQ da corretora;
- manuais de atendimento;
- explicação de termos;
- playbooks;
- conhecimento de assistência residencial;
- padrões de resposta;
- histórico não sensível.

RAG não deve:

- decidir cobertura;
- substituir apólice;
- substituir InfoCap;
- acionar seguradora;
- carregar segredos;
- guardar CPF ou dados sensíveis.

Necessário implementar:

- RAG global AutoBrokers;
- RAG por tenant;
- RAG por corredor;
- RAG por seguradora;
- provenance;
- avaliação de resposta;
- filtros de segurança.

---

## 12. Action Engine

O Action Engine é a camada que autoriza side effects.

Ele deve receber dispatch packet e readiness, decidir se pode executar e chamar adapter autorizado.

Critérios para execução automática:

- tenant autorizou;
- canal homologado;
- corredor homologado;
- subcorredor homologado;
- cobertura confirmada ou aprovação humana;
- risco baixo;
- slots completos;
- sem blockers;
- ferramenta disponível;
- idempotency key válida;
- limite de tentativas;
- observabilidade ativa.

No MVP, manter execução externa em dry-run/HITL.

---

## 13. Canal externo Allianz / seguradora

Ainda falta construir.

O agente precisará:

- iniciar conversa no canal da seguradora;
- responder menus;
- enviar dados corretos;
- ler resposta;
- capturar protocolo;
- capturar prestador;
- capturar previsão;
- tratar pedido adicional;
- voltar ao segurado;
- acompanhar até finalizar.

Para Allianz Residencial, precisamos mapear o canal real:

- WhatsApp da Allianz Assistência?
- portal?
- API?
- telefone?
- portal do corretor?

Sem isso, não existe atendimento autônomo completo.

---

## 14. Observabilidade e Evals

Produção exige:

- trace por case;
- trace por tool;
- trace por mensagem;
- diagnostics por corredor;
- logs sem PII;
- replays;
- goldens;
- alertas;
- dashboard de casos travados;
- taxa de fallback humano;
- taxa de sucesso;
- tempo médio;
- erro por provider;
- replay de WhatsApp;
- teste de regressão antes de deploy.

---

## 15. Segurança e LGPD

Antes de produção:

- tornar repo privado;
- rotacionar chaves expostas;
- cifrar credenciais WhatsApp;
- auditar logs;
- remover plaintext tokens;
- validar webhook;
- revisar RLS;
- revisar permissões;
- limitar service role;
- mascarar dados;
- criar política de retenção;
- criar auditoria de Vault;
- bloquear payload bruto no frontend;
- criar runbook de incidente.

---

## 16. Próximos blocos de implementação

### Bloco 1 — Teste real 42B6

Validar dispatch dry-run e HITL no ambiente após deploy.

### Bloco 2 — SPEC Global do projeto

Criar documento separado para chat principal, personalização, auxiliares, onboarding, tenant, billing, RAG, produtos e produção SaaS.

### Bloco 3 — Handoff Pack para novo chat

Criar documento de transição para nova conversa com:

- estado atual;
- links;
- IDs;
- decisões;
- próximos batches;
- critérios;
- scripts.

### Bloco 4 — 42W0 WhatsApp Inbound Buffer, Case Routing & Security Hardening

Implementar inbound seguro.

### Bloco 5 — 42W1 WhatsApp Attendance Runtime Controlled Test

Conectar WhatsApp real ao Attendance Runtime em dry-run/controlado.

### Bloco 6 — 42B7.2 E2E Goldens

Criar suíte final para dashboard + WhatsApp + InfoCap + dispatch.

### Bloco 7 — 42X0 Action Engine Dry-run

Camada formal de autorização de execução externa.

### Bloco 8 — 42X1 Allianz Execution Adapter

Canal de execução externo, primeiro em dry-run.

### Bloco 9 — 42X2 Controlled Real Test

Teste real supervisionado.

### Bloco 10 — SEC-001 Production Hardening

Segurança, LGPD, logs, rotação, repo privado, monitoramento.

---

## 17. Critérios para dizer que o atendimento está 100% pronto para produção

O atendimento só estará pronto quando:

1. WhatsApp real recebe e responde.
2. Mensagens fragmentadas são consolidadas.
3. Áudio, imagem e localização são tratados.
4. Case routing funciona.
5. Cliente é identificado.
6. Apólice é localizada.
7. Cobertura é confirmada por evidência ou validação.
8. Dados operacionais são coletados.
9. Dispatch packet é montado.
10. Action Engine autoriza.
11. Canal externo é acionado.
12. Retorno real é capturado.
13. Protocolo/prestador/previsão são comunicados.
14. O caso é acompanhado até encerramento.
15. Handoff acontece só em exceções.
16. Logs são seguros.
17. Goldens passam.
18. Tenant autorizou.
19. Corredor está homologado.
20. Observabilidade está ativa.

---

## 18. Como replicar para outros corredores

Para criar novo corredor:

1. definir família;
2. definir seguradora;
3. definir canal;
4. definir subcorredores;
5. listar slots;
6. definir risco;
7. definir fontes de apólice;
8. definir coverage rules;
9. definir dispatch packet;
10. definir canal externo;
11. criar goldens;
12. criar fixtures;
13. habilitar tenant;
14. homologar;
15. liberar em dry-run;
16. liberar com HITL;
17. liberar autonomia controlada.

---

## 19. Prompt de handoff para novo chat

Use este resumo ao abrir novo chat:

"Estamos no AutoBrokers Intelligence OS. O atendimento Allianz Residencial / Eletricista já tem runtime no dashboard, InfoCap real via Vault, seleção de apólice, policy evidence pack, coverage readiness e dispatch dry-run/HITL. Falta validar o teste real 42B6, criar SPEC global, depois seguir para 42W0 WhatsApp Inbound Buffer + Case Routing + Security Hardening. O objetivo é atendimento de segurado via WhatsApp ponta a ponta, inteligente, humanizado, com Smith como runtime, sem motor paralelo, usando RAG apenas como apoio, coverage por evidência, Vault para credenciais e Action Engine para side effects. Leia SPEC-ATENDIMENTO-PRODUCAO-AUTOBROKERS.md antes de sugerir qualquer batch." 

---

## 20. Conclusão

O projeto está no caminho certo. O bloco InfoCap deixou de ser protótipo e virou uma camada funcional de apólice/evidência. O dispatch dry-run/HITL fechou a preparação operacional segura. O próximo salto é conectar isso ao WhatsApp real com segurança, buffer, roteamento e observabilidade.

Não devemos pular diretamente para acionamento real. A ordem correta é:

1. validar 42B6 real;
2. consolidar specs;
3. fazer 42W0 com segurança;
4. fazer 42W1 controlado;
5. goldens E2E;
6. Action Engine;
7. canal externo;
8. homologação;
9. produção.
