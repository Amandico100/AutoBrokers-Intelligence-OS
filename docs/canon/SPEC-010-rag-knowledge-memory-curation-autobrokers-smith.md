# SPEC-010 — AutoBrokers Knowledge OS, RAG, Memory & Curadoria no Smith

**Status:** handoff estratégico para novo chat/agente  
**Projeto:** AutoBrokers.ai / AutoBrokers Intelligence OS  
**Escopo:** base de conhecimento, RAG, memórias, curadoria, benchmark, sanitização, ingestão e inteligência operacional  
**Objetivo:** permitir que outro chat/agente assuma a frente de RAG/Knowledge com contexto completo, sem reinventar a arquitetura, sem quebrar o atendimento, e usando a estrutura robusta já existente no Smith.

---

## 1. Resumo executivo

O AutoBrokers.ai já possui um MVP de atendimento avançado: runtime determinístico, InfoCap real, seleção conversacional de apólice, Q&A seguro, conhecimento curado inicial, mídia/visão em desenvolvimento, dispatch dry-run e WhatsApp simulado. Porém, a inteligência global do produto ainda precisa de uma camada profissional de conhecimento e memória.

Esta SPEC define como transformar o AutoBrokers em um **Knowledge OS multi-tenant para corretoras de seguros**, usando a estrutura do Smith sempre que possível.

A base de conhecimento deve atender três frentes:

1. **Core/Jarvys — chat principal interno da corretora**  
   Deve conhecer gestão de corretora, seguros, relatórios, auditoria, vendas, marketing, financeiro, jurídico, condições gerais, processos, carteira, inventários, performance e operação.

2. **Attendance Agents — atendentes externos para segurados**  
   Devem responder e conduzir atendimentos com base em apólices, seguradoras, corredores, procedimentos, documentos, evidências e histórico.

3. **Auxiliares/Subagentes — rotinas especializadas**  
   Devem usar conhecimento específico por tarefa: follow-up, resumo, auditoria, análise, cobrança, vendas, renovação, sinistro, assistência, compliance e automações.

O objetivo não é criar um RAG genérico. O objetivo é criar uma **arquitetura de conhecimento viva, auditável, versionada, segura e escalável**, capaz de deixar o sistema mais próximo de um agente executivo inteligente, com memória, contexto, curadoria e evolução contínua.

---

## 2. Decisão arquitetural principal

### 2.1 Não criar RAG paralelo

O Smith já possui estruturas de RAG/knowledge/memory, incluindo componentes como Qdrant, search, rerank, ingestion, memory, LangChain e escopos de conhecimento. A frente de RAG do AutoBrokers deve **auditar e reutilizar** essa infraestrutura.

Não criar:

- outro banco vetorial paralelo sem justificativa;
- outro ingestion pipeline paralelo;
- outro motor de memória solto;
- outra estrutura de agentes fora do Smith;
- RAG que decida cobertura operacional sem evidência;
- base de conhecimento que vaze dados de uma corretora para outra.

### 2.2 RAG não é fonte de verdade de cobertura

Para atendimento de seguro, a regra é absoluta:

> RAG explica conceitos, procedimentos, regras gerais e contexto. RAG não confirma cobertura específica se o Evidence Pack / InfoCap / documento oficial estruturado / validação humana não confirmar.

A fonte operacional deve continuar sendo:

- InfoCap / conector oficial;
- policy_snapshot;
- coverage_evidence;
- policy_interpretation_context;
- coverage_readiness;
- validação humana quando necessário;
- dispatch_readiness.

RAG pode dizer: “em geral, assistência residencial pode incluir eletricista”.  
RAG não pode dizer: “sua apólice cobre eletricista” sem evidência.

---

## 3. Estado atual do projeto antes desta frente

### 3.1 Atendimento

Já existe:

- Attendance Runtime estruturado;
- corredor Allianz Residencial / Eletricista;
- triagem global no WhatsApp simulado;
- InfoCap real read-only;
- múltiplas apólices;
- policy-select por texto;
- evidence pack;
- coverage readiness;
- dispatch dry-run/HITL;
- Q&A seguro;
- Knowledge curado inicial;
- Media Evidence Pipeline;
- Vision future-ready;
- Goldens finais.

### 3.2 WhatsApp

Já existe:

- estrutura Smith/Z-API reaproveitada;
- inbound buffer/debounce/dedupe;
- bridge para Attendance Runtime;
- simulate-inbound;
- outbound dry-run;
- handoff bloqueando auto-resposta;
- Z-API real pausada por pagamento.

### 3.3 Knowledge/RAG atual

Já existe no produto uma interface admin de upload de Base de Conhecimento RAG, com elementos como:

- upload de arquivos PDF, DOCX, TXT, MD, CSV;
- vínculo com agente;
- modo RAG;
- chunking por IA Semântica;
- benchmark global;
- sanitização de documentos;
- listagem de documentos processados;
- documentos com status completo, chunks e agente vinculado.

Essa interface indica que a estrutura de curadoria já começou a existir. A frente de RAG precisa transformá-la em uma arquitetura canônica e produtiva.

---

## 4. Estruturas antigas relevantes para auditoria

O usuário possui uma pasta antiga chamada aproximadamente:

`AUTOBROKERS_AGENT_OS_WORKSPACE / 00_AGENT_OS_NOVO / AUTOBROKERS_AGENT_OS / 17_INTELIGENCIA_OPERACIONAL`

A captura enviada mostra subpastas e arquivos como:

- `01_REASONER_LLM`
- `02_CONTEXT_ASSEMBLY_E_MEMORY_ROUTER`
- `03_MEMORIA_CURTA_SESSAO`
- `04_MEMORIA_ESTRUTURADA`
- `05_MEMORIA_SEMANTICA_GLOBAL`
- `06_MEMORIA_EPISODICA_CONVERSAS_REAIS`
- `07_MEMORIA_PROCEDURAL_PLAYBOOKS`
- `08_INGESTAO_CURADORIA_E_QUALIDADE`
- `09_RUNTIME_LOADING_E_MEMORY_PACKS`
- `10_INTEGRACAO_COM_PASTAS_OFICIAIS`
- `11_TOOL_ORCHESTRATION_E_ACTION_SAFETY`
- `12_INTELLIGENCE_EVALS_SIMULATION_AND_REPAIR`
- `13_HUMAN_SERVICE_INTELLIGENCE_E_EXPERIENCIA_DO_SEGURADO`
- `14_AGENTIC_HARVEST`
- `00_MANIFESTO_DO_HARNESS_DE_INTELIGENCIA.md`
- `BROKERAGE.md`
- `CONTEXT_POLICY.md`
- `MEMORY.md`
- `MEMORY_CONTEXT_CANONICAL_INDEX.md`
- `PORTAL_BROWSER_ROUTINES_MASTER_PLAN.md`
- `README.md`
- `USER.md`

O novo chat/agente deve auditar essa estrutura como referência conceitual, mas não copiar cegamente. O antigo parecia focado principalmente em atendimento. O novo AutoBrokers precisa de inteligência muito mais ampla para toda a corretora.

---

## 5. Arquitetura de conhecimento desejada

### 5.1 Camadas principais

A arquitetura deve separar conhecimento em camadas:

#### A. Global AutoBrokers Knowledge

Conhecimento comum a todas as corretoras:

- fundamentos de seguros;
- termos técnicos;
- tipos de apólices;
- assistência vs. sinistro;
- seguros auto, residencial, vida, empresarial, saúde, rural, transporte, garantia, etc.;
- melhores práticas de corretagem;
- LGPD e compliance;
- vendas consultivas;
- marketing para corretoras;
- gestão operacional;
- financeiro e comissionamento;
- relatórios e indicadores;
- auditoria e qualidade;
- playbooks de atendimento;
- regras gerais de comunicação;
- padrões de linguagem AutoBrokers.

#### B. Knowledge por seguradora

Conhecimento específico de seguradoras:

- Allianz;
- Porto;
- Tokio Marine;
- Bradesco;
- SulAmérica;
- HDI;
- Mapfre;
- Liberty;
- Zurich;
- Suhai;
- outras.

Deve conter:

- canais;
- procedimentos;
- condições gerais;
- produtos;
- assistências;
- documentos necessários;
- prazos;
- exceções;
- linguagem de cuidado.

#### C. Knowledge por linha/produto/corredor

Exemplos:

- assistência residencial;
- eletricista;
- encanador;
- chaveiro;
- assistência auto;
- guincho;
- pane seca;
- sinistro auto;
- sinistro residencial;
- renovação;
- endosso;
- segunda via;
- consulta de apólice;
- cobrança;
- venda nova;
- cross-sell.

#### D. Knowledge por corretora/tenant

Cada corretora deve ter conhecimento próprio:

- políticas internas;
- tom de voz;
- horários;
- equipe;
- grupos de WhatsApp;
- canais humanos;
- scripts internos;
- procedimentos preferidos;
- documentos padrão;
- carteira;
- seguradoras mais usadas;
- regras de atendimento;
- estilo do dono/corretor;
- processos comerciais;
- metas;
- exceções e preferências.

#### E. Knowledge por agente/subagente

Cada agente deve acessar apenas o que é necessário:

- Core/Jarvys: conhecimento amplo de gestão/estratégia/operação;
- Attendance Agent: conhecimento de atendimento externo e seguros, sem dados internos sensíveis desnecessários;
- Auxiliar de Follow-up: knowledge sobre follow-up, templates e cadências;
- Auxiliar de Resumos: knowledge sobre sumarização e padrões;
- Agente de Sinistro: knowledge de sinistro;
- Agente Comercial: knowledge de vendas/cotação/objeções.

---

## 6. Tipos de memória necessários

A estrutura precisa ir além de RAG documental. Ela deve ter memórias com funções diferentes.

### 6.1 Memória curta de sessão

Dura durante uma conversa ou atendimento.

Guarda:

- objetivo atual;
- pergunta pendente;
- slot em coleta;
- últimas respostas;
- estado emocional do usuário;
- contexto imediato;
- confirmação ou negação de risco.

Uso:

- evitar repetir perguntas;
- retomar o ponto certo;
- responder perguntas livres sem perder o fluxo.

### 6.2 Memória estruturada operacional

Dados estruturados do negócio:

- cases;
- apólices;
- dispatch packets;
- handoffs;
- seguradoras;
- corredores;
- status de atendimento;
- SLAs;
- destinos humanos;
- permissões;
- integrações.

Uso:

- decisões determinísticas;
- dashboards;
- action engine;
- auditoria.

### 6.3 Memória semântica global

Conhecimento vetorial/documental global.

Uso:

- explicar conceitos;
- enriquecer respostas;
- apoiar o Core;
- treinar agentes em domínio de seguros.

### 6.4 Memória semântica por tenant

Conhecimento da corretora.

Uso:

- “como a Rafael Seguros trabalha”;
- preferências;
- processos internos;
- padrão de atendimento;
- documentos próprios.

### 6.5 Memória episódica

Histórico de conversas reais e casos concluídos, com sanitização.

Uso:

- aprendizado com atendimentos reais;
- identificar padrões;
- criar melhorias;
- gerar playbooks.

Deve ter cuidado máximo com LGPD.

### 6.6 Memória procedural/playbooks

Como fazer tarefas.

Exemplos:

- como abrir assistência residencial;
- como fazer follow-up;
- como resumir atendimento;
- como responder cliente irritado;
- como coletar dados de sinistro;
- como criar relatório mensal;
- como auditar carteira.

### 6.7 Memória de preferências do corretor/dono

Muito importante para o “agente que pensa como a corretora”.

Guarda:

- estilo de decisão;
- tom de voz;
- tolerância a risco;
- seguradoras preferidas;
- abordagem comercial;
- regras de exceção;
- preferências de comunicação;
- forma de priorizar problemas.

### 6.8 Memória de performance e avaliação

Guarda:

- onde o agente errou;
- onde precisou de handoff;
- perguntas que não soube responder;
- falhas de RAG;
- documentos ausentes;
- intents mal classificadas;
- métricas de satisfação;
- tempo de resolução.

Uso:

- evals;
- auto-repair;
- melhoria contínua.

### 6.9 Memória agentic / evolução futura

Inspirada em Hermes/OpenClaw, mas controlada.

No futuro:

- crons;
- heartbeats;
- self-review;
- agentic harvest;
- aprendizado com conversas;
- propostas de melhoria;
- atualização assistida de knowledge;
- sugestões para CEO/founder.

Essa camada deve ser planejada agora, mas não executada sem governança.

---

## 7. Escopos de acesso

Todo conhecimento deve ser escopado.

Campos recomendados:

- `scope`: global, tenant, insurer, corridor, agent, user, case, playbook;
- `company_id`;
- `agent_id`;
- `corridor_key`;
- `subcorridor_key`;
- `insurer_key`;
- `line_kind`;
- `macro_service`;
- `audience`: broker_internal, insured_external, admin, system;
- `sensitivity`: public, internal, confidential, restricted;
- `source_type`: manual, uploaded_file, policy_doc, conversation, playbook, system_generated, benchmark;
- `version`;
- `status`: draft, active, deprecated, quarantined;
- `provenance`;
- `quality_score`;
- `last_reviewed_at`.

---

## 8. Curadoria e ingestão

### 8.1 Upload bruto não é suficiente

A corretora não deve apenas “subir arquivos”. O sistema precisa transformar documentos em conhecimento confiável.

Pipeline recomendado:

1. Upload;
2. Detecção de tipo;
3. Sanitização;
4. Classificação de escopo;
5. Chunking semântico;
6. Extração de entidades;
7. Geração de resumo canônico;
8. Checagem de qualidade;
9. Benchmark global;
10. Aprovação/publicação;
11. Indexação no Qdrant/search;
12. Evals de recuperação;
13. Monitoramento.

### 8.2 Sanitização

Remover/mascarar:

- CPF;
- CNPJ quando não necessário;
- telefone;
- e-mail;
- endereço;
- nome de segurado;
- dados bancários;
- tokens;
- senhas;
- prints com dados sensíveis;
- URLs privadas;
- payloads brutos de API.

### 8.3 Chunking

Tipos de chunking:

- IA Semântica: preferencial para documentos explicativos;
- por seção: condições gerais, manuais, playbooks;
- por FAQ: perguntas e respostas;
- por procedimento: passo a passo;
- por tabela: quando houver planilhas;
- por cláusula: documentos contratuais e condições gerais.

Cada chunk deve ter:

- título;
- resumo;
- texto;
- escopo;
- tags;
- fonte;
- data;
- versionamento;
- confiança;
- regras de uso;
- restrições.

### 8.4 Benchmark Global

O botão/rotina de Benchmark Global deve comparar o documento com padrões globais AutoBrokers:

- qualidade;
- completude;
- clareza;
- risco jurídico;
- duplicidade;
- contradições;
- aplicabilidade;
- lacunas;
- se é útil para atendimento, vendas, gestão, jurídico, financeiro, etc.

Output esperado:

- score;
- recomendações;
- riscos;
- tags sugeridas;
- escopo sugerido;
- se pode publicar;
- se precisa revisão humana.

### 8.5 Sanitizar Documentos

A função de sanitização deve gerar versão segura para RAG.

Não basta esconder. Deve classificar:

- pode ir para RAG global?;
- pode ir para tenant?;
- pode ir para agente interno?;
- pode ir para atendente externo?;
- deve ir para vault/restrito?;
- deve ser descartado?;
- exige aprovação humana?

---

## 9. Como a corretora vai alimentar conhecimento

A interface de produto deve permitir:

### 9.1 Upload por tipo

- Manual da corretora;
- Condições gerais;
- Scripts de atendimento;
- Procedimentos internos;
- FAQs;
- Treinamentos;
- Modelos de mensagem;
- Relatórios;
- Documentos de seguradoras;
- PDFs de produtos;
- planilhas;
- base de objeções comerciais;
- histórico curado de casos.

### 9.2 Vincular a agentes

Ao subir conteúdo, a corretora deve escolher:

- Core/Jarvys;
- Attendance Agent;
- agente comercial;
- agente de sinistro;
- auxiliar específico;
- todos os agentes internos;
- todos os atendentes externos.

### 9.3 Definir escopo

- Global AutoBrokers;
- corretora específica;
- seguradora;
- linha de produto;
- corredor;
- subcorredor;
- tarefa.

### 9.4 Modo de ingestão

- RAG semântico;
- File system search;
- documento canônico;
- memória procedural;
- FAQ;
- playbook;
- knowledge pack;
- não indexar ainda, só armazenar.

---

## 10. Diferença entre RAG, memória e knowledge pack

### 10.1 RAG

Busca trechos relevantes sob demanda.

Bom para:

- manuais;
- condições gerais;
- FAQs;
- documentos longos.

### 10.2 Memória

Guarda fatos/estado/preferências/experiência.

Bom para:

- lembrar como a corretora trabalha;
- lembrar preferências do usuário;
- lembrar padrões de conversas.

### 10.3 Knowledge Pack

Pacote carregado no contexto do agente para uma função.

Bom para:

- corredor eletricista;
- sinistro auto;
- atendimento inicial;
- renovação;
- auditoria mensal;
- relatório executivo.

### 10.4 File System Search

Busca em arquivos específicos, útil quando:

- o documento precisa ser consultado na íntegra;
- há conteúdo com estrutura complexa;
- precisa localizar fonte exata;
- RAG semântico pode perder contexto.

---

## 11. Core/Jarvys — conhecimento amplo da corretora

O chat principal interno precisa ser muito mais amplo que o atendimento.

Ele deve saber:

### Gestão

- carteira;
- produtividade;
- SLAs;
- gargalos;
- tarefas;
- equipe;
- auditoria;
- inventário operacional;
- planos de ação.

### Comercial

- vendas;
- funil;
- objeções;
- cross-sell;
- renovação;
- recuperação de cliente;
- scripts;
- propostas;
- campanhas.

### Financeiro/Contábil

- comissões;
- inadimplência;
- repasses;
- relatórios;
- previsões;
- conciliação;
- custos.

### Jurídico/Compliance

- LGPD;
- termos;
- responsabilidade na confirmação de cobertura;
- documentos obrigatórios;
- riscos de comunicação.

### Técnico de seguros

- produtos;
- condições gerais;
- assistências;
- coberturas;
- exclusões;
- franquias;
- prazos;
- sinistros.

### Operação

- portais;
- InfoCap;
- seguradoras;
- grupos humanos;
- atendimentos;
- dispatch;
- fluxos de exceção.

---

## 12. Attendance Agent — conhecimento externo seguro

Atendente externo não deve ter acesso ao mesmo nível de conhecimento interno do Core.

Pode acessar:

- informações gerais de assistência;
- perguntas frequentes;
- procedimentos seguros;
- status do próprio caso;
- evidências do próprio atendimento;
- apólice do próprio segurado, sanitizada;
- scripts aprovados;
- limitações.

Não deve acessar:

- dados financeiros da corretora;
- estratégias internas;
- outros clientes;
- métricas da equipe;
- dados de comissão;
- credenciais;
- conteúdos administrativos restritos.

---

## 13. Roteamento de conhecimento por agente

O context assembly deve decidir quais memórias entram:

Exemplo Core:

- Global AutoBrokers Knowledge;
- Tenant Knowledge;
- métricas e cases;
- playbooks;
- preferências do dono;
- histórico resumido;
- tools disponíveis.

Exemplo Attendance:

- corredor/subcorredor;
- policy_snapshot;
- coverage_evidence;
- coverage_readiness;
- knowledge de assistência;
- FAQ aprovada;
- media_evidence;
- handoff rules;
- pergunta pendente.

Exemplo Auxiliar Follow-up:

- playbook de follow-up;
- templates;
- histórico do caso;
- cadência;
- regras da corretora;
- limite de mensagens.

---

## 14. Estrutura de “inteligência máxima” sem perder controle

A LLM deve operar com máxima capacidade onde ela é forte:

- interpretação;
- síntese;
- linguagem;
- raciocínio com contexto;
- geração de hipóteses;
- análise de documentos;
- comparação;
- explicação;
- planejamento;
- recomendação.

Mas não deve decidir sozinha:

- confirmação de cobertura;
- envio de dispatch;
- acionamento de seguradora;
- alteração de dados críticos;
- uso de credenciais;
- envio externo;
- decisão jurídica final;
- aprovação financeira.

A inteligência máxima vem da combinação:

- LLM forte;
- contexto certo;
- RAG curado;
- memória correta;
- tools determinísticas;
- guardrails;
- evals;
- feedback humano;
- audit trail.

---

## 15. Evals e qualidade

Criar evals para:

- recuperação RAG correta;
- não vazamento de PII;
- não confirmação indevida de cobertura;
- resposta com fonte/provenance;
- resposta humana;
- retomada de fluxo;
- diferença entre assistência e sinistro;
- perguntas ambíguas;
- contradição entre fonte global e fonte da corretora;
- conteúdo desatualizado;
- alucinação.

Cada knowledge pack deve ter goldens.

---

## 16. Agentic Harvest futuro

No futuro, o sistema deve capturar aprendizado:

- perguntas frequentes não respondidas;
- documentos ausentes;
- falhas de atendimento;
- handoffs recorrentes;
- frases boas usadas por humanos;
- respostas ruins do agente;
- lacunas de cobertura;
- novos procedimentos.

Mas nada deve entrar automaticamente na base ativa sem curadoria.

Fluxo:

1. agente detecta aprendizado;
2. gera proposta de knowledge item;
3. coloca em review;
4. humano aprova;
5. sanitiza;
6. versiona;
7. indexa;
8. eval roda;
9. publica.

---

## 17. Tarefas para o novo chat/agente de RAG

### Fase 1 — Auditoria

1. Auditar toda a estrutura RAG/Knowledge do Smith no repo.
2. Auditar tabelas Supabase relevantes.
3. Auditar admin UI de Base de Conhecimento RAG.
4. Auditar fluxos de upload, benchmark, sanitização e chunking.
5. Auditar integração com agentes/subagentes.
6. Auditar Qdrant/search/rerank/ingestion/memory.
7. Auditar pasta antiga `AUTOBROKERS_AGENT_OS/17_INTELIGENCIA_OPERACIONAL`.
8. Separar o que é reaproveitável, obsoleto e perigoso.

### Fase 2 — Modelo canônico

Criar documentos canônicos:

- Knowledge Scope Matrix;
- Memory Type Matrix;
- Ingestion Pipeline;
- Curation Rules;
- Sanitization Rules;
- RAG Usage Policy;
- Agent Knowledge Loading Policy;
- Tenant Knowledge Isolation;
- Evals Strategy.

### Fase 3 — Implementação mínima

1. Conectar `ATTENDANCE_KNOWLEDGE_URL` ao RAG real do Smith.
2. Garantir snippets com provenance.
3. Garantir escopo por company/agent/corridor.
4. Garantir sanitização.
5. Adicionar snippets ao Q&A sem decidir cobertura.
6. Criar testes.

### Fase 4 — Curadoria inicial

Criar pacotes:

- Global AutoBrokers Insurance Basics;
- Global Assistance Residential;
- Global Assistance Auto;
- Global Claims Basics;
- Broker Management Basics;
- Sales & Renewal Playbooks;
- Compliance/LGPD basics;
- Rafael Seguros tenant starter pack;
- Allianz Residential Assistance starter pack.

### Fase 5 — Produto/UI

Melhorar tela de RAG:

- upload guiado;
- escopo obrigatório;
- agente vinculado;
- preview de chunks;
- benchmark score;
- sanitização antes/depois;
- aprovação;
- status de indexação;
- evals;
- busca de teste;
- auditoria.

---

## 18. Prompt completo para novo chat/agente executar RAG

Copie e cole o texto abaixo em um novo chat quando for abrir a frente de RAG/Knowledge.

```txt
Você agora será o agente responsável pela frente AutoBrokers Knowledge OS / RAG / Memory / Curadoria.

Contexto:
O AutoBrokers.ai é uma plataforma SaaS multi-tenant para corretoras de seguros, baseada no Smith/Agent Smith. O projeto já possui Attendance Runtime, Core/Jarvys, auxiliares, corredores, InfoCap, WhatsApp simulado, Q&A seguro e mídia/evidência. Agora precisamos estruturar a camada robusta de conhecimento, RAG e memórias usando a infraestrutura existente do Smith.

Sua missão:
Construir uma arquitetura de conhecimento extremamente profissional para tornar o Core/Jarvys, os atendentes e os auxiliares muito mais inteligentes, sem criar RAG paralelo, sem vazar dados, sem confirmar cobertura sem evidência e sem quebrar a arquitetura Smith.

Obrigatório:
1. Auditar primeiro. Não sair codando.
2. Reutilizar Smith RAG/Knowledge/Memory/Qdrant/Ingestion/Search/Rerank/Memory quando existirem.
3. Auditar a interface admin de Base de Conhecimento RAG: upload, vincular agente, modo RAG, IA Semântica, Benchmark Global, Sanitizar Documentos.
4. Auditar a estrutura antiga AUTOBROKERS_AGENT_OS/17_INTELIGENCIA_OPERACIONAL como referência conceitual, não como runtime principal.
5. Separar conhecimento global AutoBrokers, conhecimento por seguradora, por corredor, por corretora/tenant, por agente e por usuário.
6. Desenhar os tipos de memória: curta sessão, estruturada, semântica global, semântica tenant, episódica, procedural, preferências do corretor, performance/evals, agentic future.
7. Criar matriz de acesso por audiência: broker_internal, insured_external, admin, system.
8. Garantir que RAG nunca confirme cobertura específica sem Evidence Pack/InfoCap/validação humana.
9. Criar pipeline de curadoria: upload → sanitização → classificação → chunking → benchmark → aprovação → indexação → evals.
10. Criar ou atualizar SPECs canônicas e relatório de execução.

Arquivos/docs a auditar:
- docs/canon/SPEC-003-knowledge-rag-memory.md
- docs/canon/SPEC-004-agent-intelligence-context-architecture.md
- docs/canon/SPEC-005-atendimento-runtime-architecture.md
- docs/canon/SPEC-007-atendimento-producao-autonomo.md
- docs/canon/SPEC-008-producao-global-autobrokers.md
- docs/canon/design/2026-06-claude-design/42R0-attendance-knowledge-rag-safe-context-report.md
- backend/app/services/qdrant_service.py
- backend/app/services/search_service.py
- backend/app/services/rerank_service.py
- backend/app/services/ingestion_service.py
- backend/app/services/memory_service.py
- backend/app/services/langchain_service.py
- backend/app/services/knowledge_scope.py
- admin UI de Base de Conhecimento RAG
- tabelas Supabase de documents/chunks/knowledge/memory, se houver
- pasta antiga AUTOBROKERS_AGENT_OS/17_INTELIGENCIA_OPERACIONAL

Entregáveis mínimos:
1. Relatório de auditoria da estrutura atual.
2. Knowledge Scope Matrix.
3. Memory Type Matrix.
4. RAG Usage Policy.
5. Ingestion & Curation Pipeline.
6. Tenant Isolation Policy.
7. Agent Knowledge Loading Policy.
8. Plano de implementação 42R1.
9. Primeiro batch implementável que conecte ATTENDANCE_KNOWLEDGE_URL ao RAG real do Smith com snippets sanitizados e provenance.

Critério de sucesso:
- O sistema usa RAG real do Smith.
- Os snippets têm escopo, fonte e provenance.
- O Core/Jarvys pode usar conhecimento amplo interno.
- Attendance Agent usa apenas conhecimento seguro externo.
- RAG não confirma cobertura sem evidência.
- Nenhum dado sensível vaza entre tenants.
- Existe caminho de curadoria para a corretora alimentar conhecimento próprio.
- A arquitetura prepara o AutoBrokers para memória avançada e evolução futura estilo Hermes/OpenClaw, mas com governança.
```

---

## 19. Critério de pronto desta frente

Esta frente estará pronta quando:

- a arquitetura de conhecimento estiver documentada;
- o RAG real do Smith estiver conectado ao Q&A;
- houver escopo multi-tenant seguro;
- houver curadoria e sanitização;
- houver primeira base global AutoBrokers;
- houver primeira base tenant Rafael Seguros;
- houver evals;
- Core/Jarvys e Attendance usarem knowledge corretamente;
- nenhum dado sensível vazar;
- cobertura continuar governada por evidence/InfoCap/HITL.

---

## 20. Observação final

A meta não é apenas responder perguntas. A meta é criar o cérebro institucional da corretora dentro do AutoBrokers.

O Knowledge OS deve fazer o AutoBrokers evoluir de um SaaS com agentes para um sistema operacional inteligente para corretoras de seguros.
