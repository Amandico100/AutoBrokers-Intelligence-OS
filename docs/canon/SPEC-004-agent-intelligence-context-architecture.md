# SPEC-004 — Agent Intelligence, Context Assembly & Role Architecture

**Produto:** AutoBrokers Intelligence OS  
**Status:** Canônico proposto para revisão do CEO/Fundador  
**Versão:** v1.0  
**Data:** 2026-06-12  
**Autoridade:** Esta SPEC define a arquitetura de inteligência, papéis, fronteiras, montagem de contexto e evolução controlada dos agentes do AutoBrokers, sem substituir a SPEC-003 de Knowledge/RAG/Memory nem alterar o runtime Smith diretamente.

---

## 0. Sumário executivo

A SPEC-004 existe para impedir que o AutoBrokers vire apenas um “chat com RAG” ou um conjunto de prompts soltos. O objetivo é transformar o produto em um sistema agentico verticalizado para corretoras de seguros, preservando o runtime Smith, mas elevando a inteligência do produto para o contexto real de corretoras, atendimento, sinistros, assistências, vendas, auxiliares, conectores, rotinas e memória governada.

A decisão central é:

> O AutoBrokers deve ter um **Core inteligente** para a corretora, **agentes especializados** para domínios operacionais, **auxiliares instaláveis** para tarefas, **corredores estruturados** para atendimento, **RAG curado** para conhecimento longo, **memória governada** para contexto vivo e **gates de segurança** para qualquer ação sensível.

Esta SPEC separa claramente:

- Chat principal AutoBrokers;
- agentes de atendimento;
- auxiliares;
- corredores;
- subagentes especialistas;
- RAG;
- memória;
- tools/conectores;
- Vault;
- HITL;
- evals;
- futuro autoaprendizado controlado.

A regra de proteção é:

> Não criar motor paralelo ao Smith.  
> Não substituir o RAG existente.  
> Não reescrever LangGraph/LangChain sem necessidade.  
> Não transformar o legado em prompt bruto.  
> Não carregar documentos constitucionais inteiros em runtime.  
> Não misturar memória de corretora com conhecimento global.  
> Não promover aprendizado automaticamente.

---

## 1. Contexto e motivação

O AutoBrokers nasceu de uma necessidade operacional: automatizar atendimento e processos de corretoras de seguros. O projeto antigo, chamado aqui de Agent OS legado / AUTOBROKERS_AGENT_OS / ResultVision, criou materiais profundos para atendimento, corredores, guardrails, skills, templates, contratos, orquestração, dossiês e inteligência operacional.

O runtime novo, herdado do Smith, já possui uma base técnica robusta:

- agentes;
- subagentes;
- chat;
- LangGraph;
- tools;
- RAG;
- upload de documentos;
- Qdrant;
- MinIO;
- embeddings;
- memória;
- logs;
- custos;
- auxiliares;
- admin;
- multiempresa.

A SPEC-003 definiu a arquitetura de Knowledge/RAG/Memory. Porém ainda faltava uma camada acima: a arquitetura de **inteligência dos agentes**.

Sem essa camada, há risco de:

1. o chat principal responder como atendente de segurado;
2. o atendente de segurado se comportar como consultor estratégico da corretora;
3. auxiliares virarem prompts soltos;
4. corredores virarem documentos de RAG;
5. RAG virar “cérebro único”;
6. memória virar depósito sem governança;
7. conhecimento global misturar dado local;
8. prompts ficarem limitados demais;
9. agentes ficarem “burros”, engessados ou genéricos;
10. Claude/Codex criar estruturas paralelas ao Smith.

Esta SPEC resolve esse risco.

---

## 2. Princípios não negociáveis

### 2.1. Preservar o Smith

O Smith é o runtime técnico principal. Ele deve ser aproveitado, não substituído.

Componentes a preservar:

- `agents`;
- `documents`;
- upload → MinIO;
- chunking/ingestion;
- Qdrant `company_{company_id}`;
- filtros por `company_id` e `agent_id`;
- tenant-wide documents;
- `session_summaries`;
- `user_memories`;
- `memory_settings`;
- `conversation_logs`;
- tools;
- LangGraph;
- custos/tokens;
- admin de agentes;
- benchmark/sanitização quando aplicável.

Qualquer evolução deve ser incremental e compatível.

### 2.2. Não criar motor paralelo de RAG

A arquitetura de conhecimento deve usar o RAG existente do Smith, ampliado conforme SPEC-003:

- escopo local/tenant;
- escopo agent;
- escopo global curado;
- payloads enriquecidos;
- curadoria;
- versionamento;
- validade;
- isolamento.

Proibido criar um segundo pipeline de embeddings, segunda tabela de documentos ou segundo retriever sem aprovação explícita.

### 2.3. Separar inteligência de execução

O AutoBrokers Core pode pensar, recomendar, explicar, preparar e coordenar.

Ele não deve executar ações sensíveis diretamente.

A execução pertence a runtimes especializados, tools autorizadas, conectores, workflows, HITL e logs.

### 2.4. Separar prompt, RAG, memória e workflow

- Prompt/Blueprint: identidade, papel, estilo, limites, raciocínio esperado.
- RAG: conhecimento textual longo e consultável.
- Memória: fatos, contexto, histórico, preferências, estado e aprendizados governados.
- Workflow/Corredor: fases, slots, decisões, critérios e ações permitidas.

Nenhuma camada substitui a outra.

### 2.5. Inteligência máxima sem irresponsabilidade

Os agentes devem ser muito inteligentes, mas não livres de controle.

Inteligência máxima significa:

- saber fazer boas perguntas;
- entender contexto de seguros;
- sugerir próximos passos;
- reconhecer incerteza;
- usar documentos;
- consultar memória;
- respeitar workflow;
- gerar relatórios;
- vender melhor;
- humanizar atendimento;
- orientar a operação;
- pedir validação quando necessário;
- evitar invenção;
- registrar evidências.

Não significa:

- decidir cobertura sem base;
- prometer indenização;
- acionar portal sem autorização;
- enviar WhatsApp sem gate;
- aprender automaticamente sem curadoria;
- misturar informações entre corretoras;
- carregar todo o cérebro antigo em prompt.

---

## 3. Taxonomia oficial dos papéis agenticos

A partir desta SPEC, o AutoBrokers possui os seguintes tipos de inteligência.

### 3.1. AutoBrokers Core — chat principal da corretora

O AutoBrokers Core é o agente principal interno da corretora.

Ele conversa com o corretor, gestor, atendente ou operador dentro do dashboard.

Ele é o “Jarvys” da corretora.

Papel:

- conselheiro operacional;
- analista;
- mentor;
- secretário inteligente;
- estrategista;
- coordenador de auxiliares;
- orientador de atendimento;
- explicador de processos;
- detector de oportunidades;
- detector de gargalos;
- criador de rascunhos;
- criador de planos;
- assistente de configuração;
- agente central de inteligência da corretora.

Ele responde perguntas como:

- “Quais atendimentos estão parados?”
- “O que posso automatizar?”
- “Como melhorar minha taxa de renovação?”
- “Quais auxiliares devo ativar?”
- “Por que esse caso travou?”
- “Quais seguradoras exigem mais documentos?”
- “Crie um relatório dos atendimentos de hoje.”
- “Como melhorar o atendimento da minha equipe?”
- “Qual é o próximo passo neste sinistro?”
- “O que falta configurar na minha corretora?”

Ele não é:

- atendente direto de segurado;
- executor irrestrito;
- substituto do operador humano;
- corretor legalmente responsável;
- sistema de decisão de cobertura;
- motor de envio automático;
- fonte única de verdade para regra de seguradora.

### 3.2. Attendance Agent — agente de atendimento ao segurado/cliente

É o agente que conversa com o segurado ou cliente final, geralmente por WhatsApp ou canal operacional.

Papel:

- recepcionar;
- identificar;
- coletar dados;
- entender demanda;
- consultar apólice/base;
- seguir corredor;
- humanizar;
- preparar acionamento;
- escalar para humano quando necessário;
- registrar atendimento.

Ele opera dentro de corredores e guardrails.

Ele não deve:

- improvisar fora do corredor;
- fazer promessa de cobertura;
- negar ou aprovar sinistro sozinho;
- enviar acionamentos reais sem gate;
- inventar regra de seguradora;
- usar documentos globais como se fossem regra específica do caso.

### 3.3. Auxiliary Agent / Auxiliar

Auxiliares são capacidades instaláveis pela corretora.

Exemplos:

- Resumo de Atendimentos;
- Follow-up WhatsApp;
- Cobrança de parcelas;
- Relatório semanal;
- Conferência de documentos;
- Rascunho de mensagens;
- Oportunidades de renovação;
- Análise de funil comercial;
- Diagnóstico de configuração.

Um Auxiliar pode ser:

1. executor específico;
2. agente/subagente Smith;
3. workflow com etapas;
4. tarefa agendada futura;
5. híbrido com HITL.

Ele deve declarar:

- objetivo;
- entrada;
- saída;
- permissões;
- knowledge required;
- memory required;
- tools required;
- se pode executar ação ou apenas sugerir;
- se precisa aprovação humana;
- custo estimado;
- logs esperados;
- evals mínimos.

### 3.4. Corridor / Corredor

Corredores são workflows estruturados para atendimento e operação.

Exemplos:

- assistência residencial;
- assistência auto;
- sinistro auto;
- sinistro residencial;
- endosso;
- renovação;
- cobrança;
- venda consultiva;
- acompanhamento de proposta.

Corredor não é prompt solto e não é RAG.

Ele deve ter:

- objetivo;
- escopo;
- fases;
- estados;
- slots;
- perguntas inteligentes;
- critérios de entrada;
- critérios de saída;
- ações permitidas;
- ações proibidas;
- handoff;
- HITL;
- logs;
- golden tests;
- fallback;
- seguradoras suportadas;
- diferenças por produto.

### 3.5. SubAgent / Especialista

SubAgents são especialistas chamados por Core, Auxiliar ou Corredor.

Exemplos:

- especialista em apólice;
- especialista em documentos;
- especialista em cobertura;
- especialista em sinistro;
- especialista em assistência residencial;
- especialista em Allianz;
- especialista em follow-up;
- especialista em relatórios;
- especialista em vendas.

SubAgent pode ter RAG próprio (`agent_id`), prompt próprio e tools limitadas.

Ele não deve ter escopo maior do que precisa.

### 3.6. Tool Executor / Conector

É o componente que executa ação técnica.

Exemplos:

- consultar InfoCap;
- consultar Quiver;
- acessar portal de seguradora;
- enviar WhatsApp;
- criar tarefa;
- ler Drive;
- consultar Notion;
- disparar webhook;
- criar rascunho.

O Tool Executor não decide sozinho. Ele recebe uma intenção validada, permissões, credenciais via Vault e política de segurança.

### 3.7. Memory Fabric / Memória Governada

A memória é a camada que preserva contexto e aprendizado ao longo do tempo.

Ela pode conter:

- resumo de sessão;
- perfil do usuário;
- fatos da corretora;
- preferências;
- decisões;
- histórico de caso;
- pendências;
- padrões recorrentes;
- evidências de skill;
- resultados de auxiliares;
- avaliações;
- feedback humano.

Ela não deve conter:

- segredos;
- token;
- senha;
- conteúdo sensível sem necessidade;
- dados globais contaminados por tenant;
- aprendizado promovido automaticamente sem curadoria.

### 3.8. Global Knowledge Curator

É o papel humano/administrativo ou agente assistido que prepara conhecimento global.

Ele cuida de:

- condições gerais;
- playbooks;
- dossiês de seguradora;
- glossário;
- regras públicas;
- manuais operacionais;
- documentos de treinamento;
- materiais comerciais;
- templates globais;
- evals.

Ele publica conhecimento global como curado, versionado e seguro.

---

## 4. Mapa oficial de camadas de inteligência

### 4.1. Camada 1 — Constituição / Identidade

Contém princípios gerais, alma, voz e limites.

Usada para:

- orientar design;
- alinhar prompts;
- criar evals;
- definir tom institucional.

Não usada como:

- prompt bruto;
- base de decisão operacional;
- documento de atendimento;
- runtime integral.

### 4.2. Camada 2 — Blueprint / Prompt

Define o comportamento do agente específico.

Campos mínimos:

- role;
- mission;
- audience;
- scope;
- non-goals;
- decision boundaries;
- tone;
- reasoning style;
- tool policy;
- RAG policy;
- memory policy;
- handoff policy;
- output format;
- refusal/uncertainty policy.

### 4.3. Camada 3 — Context Assembly

Define o que entra no prompt em cada turno.

Ordem base:

1. system/global safety;
2. agent blueprint;
3. tenant profile;
4. user/session context;
5. current conversation state;
6. active workflow/corridor state;
7. relevant memory;
8. local agent RAG;
9. tenant-wide RAG;
10. global curated RAG, quando habilitado;
11. available tools and permissions;
12. output contract.

### 4.4. Camada 4 — RAG

Conhecimento textual longo.

Escopos:

- global curated;
- tenant-wide;
- agent-scoped;
- auxiliary-specific;
- carrier/product-specific;
- document/source-specific.

### 4.5. Camada 5 — Structured Knowledge

Conhecimento estruturado, não RAG.

Exemplos:

- corredores;
- slots;
- checklists;
- JSON de seguradora;
- regras de permissões;
- templates;
- tool contracts;
- HITL policies;
- status machines.

### 4.6. Camada 6 — Memory

Memória viva, derivada de conversas, ações e feedbacks.

Tipos:

- short-term conversation memory;
- session summary;
- user memory;
- brokerage memory;
- case memory;
- operational memory;
- routine memory;
- skill/evidence memory;
- eval memory.

### 4.7. Camada 7 — Tools / Actions

Execução controlada.

Toda tool precisa:

- permissão;
- escopo;
- input contract;
- output contract;
- logs;
- fallback;
- HITL quando necessário.

### 4.8. Camada 8 — Evaluation / Governance

Controle de qualidade.

Inclui:

- golden tests;
- replay tests;
- audit logs;
- feedback humano;
- safety checks;
- RAG retrieval checks;
- hallucination checks;
- permission checks.

---

## 5. Diferença entre Chat Principal, Atendimento e Auxiliares

### 5.1. Chat Principal AutoBrokers

Usuário: corretor, gestor ou operador.

Objetivo: ajudar a corretora a operar melhor.

Exemplo de pergunta:

> “Quais atendimentos estão pendentes hoje?”

Resposta esperada:

- analisar dados;
- resumir status;
- sugerir prioridade;
- indicar ações;
- oferecer próximos passos;
- não fingir que executou se não executou.

### 5.2. Atendimento

Usuário: segurado/cliente final.

Objetivo: resolver uma demanda específica de atendimento.

Exemplo:

> “Meu carro quebrou, preciso de guincho.”

Resposta esperada:

- acolher;
- coletar dados;
- identificar apólice;
- seguir corredor;
- explicar próximos passos;
- não prometer cobertura;
- escalar quando necessário.

### 5.3. Auxiliar

Usuário: corretor ou sistema.

Objetivo: executar tarefa específica.

Exemplo:

> “Resumo de Atendimentos.”

Resposta esperada:

- receber input;
- consultar dados;
- gerar output estruturado;
- registrar run;
- mostrar custo;
- não fazer ação externa sem permissão.

---

## 6. Política de inteligência máxima dos agentes

Agentes do AutoBrokers devem ser inteligentes por composição, não por improviso.

### 6.1. Fontes de inteligência

O agente fica inteligente quando combina:

- LLM forte;
- prompt/blueprint claro;
- contexto da corretora;
- memória relevante;
- RAG local;
- RAG global curado;
- corredores;
- tools;
- dossiês de seguradora;
- playbooks de atendimento;
- playbooks de vendas;
- feedback humano;
- evals.

### 6.2. Comportamentos esperados

O agente deve:

- raciocinar antes de responder;
- fazer perguntas quando faltar dado;
- explicar incertezas;
- separar fato de hipótese;
- sugerir próximos passos;
- priorizar segurança;
- adaptar linguagem ao usuário;
- resumir quando necessário;
- detalhar quando necessário;
- usar evidências;
- não inventar documento;
- não confundir seguradora;
- não confundir corretora;
- não confundir cliente final com operador interno.

### 6.3. Anti-engessamento

O agente não deve ser limitado a scripts fixos.

Corredores são guias operacionais, não prisões linguísticas.

O agente pode:

- reformular perguntas;
- humanizar;
- adaptar sequência quando permitido;
- sugerir estratégia;
- explicar;
- antecipar riscos;
- propor melhoria.

Mas não pode:

- pular etapa obrigatória;
- ignorar HITL;
- prometer resultado;
- usar tom inadequado;
- inventar regra.

---

## 7. Arquitetura de Context Assembly por tipo de agente

### 7.1. AutoBrokers Core

Contexto recomendado:

1. identidade do AutoBrokers Core;
2. perfil da corretora;
3. permissões do usuário;
4. dados operacionais disponíveis;
5. memória da corretora;
6. memória do usuário;
7. histórico recente;
8. RAG tenant-wide;
9. RAG global curado;
10. auxiliares instalados;
11. conectores ativos/inativos;
12. tools permitidas;
13. limites de execução.

Nunca carregar:

- corredores completos se a pergunta não for atendimento;
- documentos constitucionais completos;
- segredos;
- dados de outra corretora;
- dados brutos desnecessários.

### 7.2. Attendance Agent

Contexto recomendado:

1. identidade de atendimento;
2. canal;
3. estado do caso;
4. corredor ativo;
5. fase atual;
6. slots preenchidos;
7. pendências;
8. apólice/dados relevantes;
9. dossiê da seguradora;
10. RAG agent/tenant relevante;
11. histórico da conversa;
12. políticas de handoff;
13. limites de promessa/decisão.

Nunca carregar:

- estratégia interna da corretora sem necessidade;
- relatórios gerenciais;
- prompts de venda interna;
- conhecimento global não curado;
- dados de outro cliente.

### 7.3. Auxiliar

Contexto recomendado:

1. blueprint do auxiliar;
2. input do run;
3. permissões;
4. dados necessários;
5. memory/RAG requerido;
6. formato de saída;
7. custo/limite;
8. HITL se aplicável.

### 7.4. SubAgent especialista

Contexto recomendado:

1. missão específica;
2. escopo estreito;
3. pergunta/tarefa;
4. RAG especializado;
5. dados do caso;
6. output esperado;
7. limites.

SubAgent não deve receber contexto amplo por padrão.

---

## 8. Política de RAG por tipo de conhecimento

### 8.1. Deve ir para RAG

- condições gerais;
- manuais;
- playbooks longos;
- perguntas frequentes;
- materiais de treinamento;
- documentos de seguradoras;
- procedimentos textuais;
- políticas comerciais longas;
- documentos da corretora;
- roteiros explicativos.

### 8.2. Não deve ir para RAG como fonte primária

- corredor;
- state machine;
- slot schema;
- tool contract;
- permissões;
- Vault;
- HITL policy;
- action safety;
- workflow crítico;
- regra de execução;
- segredo;
- token;
- senha.

Esses itens devem ser estruturados.

### 8.3. Pode ter dupla forma

Alguns conteúdos podem ter:

- versão estruturada para execução;
- versão textual em RAG para explicação.

Exemplo:

- dossiê de seguradora em JSON para runtime;
- manual da seguradora em RAG para consulta e explicação.

---

## 9. Memória e autoaprendizado

### 9.1. Memória agora

A memória atual do Smith deve ser preservada:

- session summaries;
- user memories;
- memory settings;
- conversation logs.

Ela deve ser usada de forma segura e incremental.

### 9.2. Autoaprendizado futuro

Autoaprendizado real só deve existir com pipeline:

1. observação;
2. sugestão;
3. evidência;
4. classificação;
5. revisão humana;
6. sandbox;
7. eval;
8. aprovação;
9. promoção;
10. versionamento;
11. rollback.

Proibido:

- promover uma memória local para global automaticamente;
- alterar prompt canônico sozinho;
- criar regra operacional sem revisão;
- aprender dado sensível como regra geral.

### 9.3. Tipos de memória futura

- `user_memory`: preferências e perfil do usuário interno;
- `brokerage_memory`: fatos da corretora;
- `case_memory`: estado e histórico de caso;
- `operational_memory`: padrões e gargalos;
- `routine_memory`: histórico de auxiliares/rotinas;
- `skill_evidence`: evidências de melhoria;
- `global_learning_candidate`: candidato a conhecimento global, nunca publicado automaticamente.

---

## 10. Corredores

### 10.1. Finalidade

Corredores transformam atendimento em operação confiável.

Eles devem permitir inteligência sem perder controle.

### 10.2. Estrutura mínima

Todo corredor deve ter:

- `id`;
- `slug`;
- `name`;
- `domain`;
- `product`;
- `carrier_support`;
- `entry_conditions`;
- `exit_conditions`;
- `phases`;
- `slots`;
- `required_evidence`;
- `allowed_actions`;
- `forbidden_actions`;
- `handoff_triggers`;
- `hitl_policy`;
- `fallback_policy`;
- `evals`.

### 10.3. Fases canônicas iniciais de atendimento

1. entrada;
2. identidade;
3. levantamento;
4. apólice;
5. decisão assistida;
6. humanização;
7. acionamento preparado;
8. acompanhamento;
9. encerramento.

### 10.4. Corredor não decide cobertura sozinho

Corredor organiza, orienta e coleta.

Decisão sensível deve depender de:

- regra estruturada;
- documento;
- operador humano;
- seguradora;
- gate de segurança.

---

## 11. Auxiliares

### 11.1. Tipos de auxiliares

- read-only;
- draft-only;
- approval-required;
- scheduled;
- connector-based;
- workflow-based;
- report-based;
- agent-based.

### 11.2. Campos mínimos de blueprint

```json
{
  "slug": "resumo-atendimentos",
  "name": "Resumo de Atendimentos",
  "kind": "specific_executor",
  "goal": "Gerar resumo operacional dos atendimentos",
  "audience": "operador_interno",
  "inputs": [],
  "outputs": [],
  "requires_knowledge": [],
  "requires_memory": [],
  "requires_tools": [],
  "requires_approval": false,
  "side_effects": "none",
  "risk_level": "low"
}
```

### 11.3. Auxiliares com ação externa

Devem ser:

- gated;
- auditados;
- aprováveis;
- com preview;
- com rollback quando possível;
- com logs;
- com limite de escopo.

---

## 12. Tools, Vault e ações sensíveis

### 12.1. Tools não são inteligência

Tools executam.

Agentes decidem intenção, mas tools precisam de contrato.

### 12.2. Vault

Credenciais devem ficar no Vault.

Proibido:

- salvar senha em prompt;
- salvar token em memória;
- salvar credencial em RAG;
- expor segredo em log;
- incluir segredo em vector store.

### 12.3. Ações sensíveis

Exigem HITL ou policy:

- enviar WhatsApp;
- acionar seguro;
- abrir sinistro;
- acessar portal;
- alterar cadastro;
- enviar documento;
- cancelar apólice;
- cobrar cliente;
- emitir mensagem externa em nome da corretora.

---

## 13. Evals e qualidade

### 13.1. Cada agente precisa de evals

Tipos:

- factualidade;
- recuperação RAG;
- isolamento tenant;
- isolamento agent;
- segurança;
- tom;
- completude;
- handoff;
- não alucinação;
- uso correto de tools.

### 13.2. Goldens iniciais

AutoBrokers Core deve passar:

- explicar diferença entre auxiliar e atendimento;
- responder usando RAG local;
- não responder dado inexistente;
- sugerir auxiliar apropriado;
- não executar ação sensível sem aprovação;
- não vazar dado de outro agente;
- não confundir segurado com corretor.

Attendance Agent deve passar:

- acolher cliente;
- pedir dados mínimos;
- não prometer cobertura;
- seguir fase;
- escalar quando necessário.

Auxiliar deve passar:

- rodar com input correto;
- gerar saída estruturada;
- registrar execução;
- não executar side effect indevido.

---

## 14. Roadmap de implementação recomendado

### Fase 0 — Concluída

- RAG local funcionando;
- MinIO/Qdrant saudáveis;
- upload completo;
- retrieval no chat funcionando;
- RLS em documents;
- agent isolation;
- scope fields;
- global include off.

### Fase 1 — Esta SPEC

Criar documentação canônica da arquitetura de inteligência.

Sem código.  
Sem SQL.  
Sem deploy.

### Fase 2 — Context Package mínimo

Criar estrutura mínima para representar contexto montado por tipo de agente, ainda sem grande runtime novo.

Objetivo:

- preparar Core para saber quem ele é;
- preparar attendance para saber que é atendimento;
- preparar auxiliares para declarar knowledge/memory/tools;
- manter Smith.

### Fase 3 — Global Knowledge Curated

Ativar coleção global curada conforme SPEC-003, com include_global controlado.

Não ingerir tudo.  
Começar com poucos documentos curados.

### Fase 4 — AutoBrokers Core Blueprint v1

Criar prompt/blueprint do chat principal:

- papel;
- inteligência;
- tom;
- limites;
- uso de RAG;
- uso de memória;
- diferença entre analisar e executar;
- perguntas inteligentes;
- resposta estratégica.

### Fase 5 — Attendance Blueprint v1

Criar blueprint de atendimento separado do Core.

### Fase 6 — Corredor mínimo

Implementar primeiro corredor estruturado simples ou documentar schema antes de runtime.

### Fase 7 — Auxiliares avançados

Criar auxiliares com requires_knowledge/requires_memory/requires_tools.

### Fase 8 — Memory Fabric governado

Evoluir memória com pipeline de promoção controlada.

---

## 15. Batches recomendados a partir desta SPEC

### 42A0 — Canonical Agent Intelligence Recon

Objetivo: Claude Code audita código atual e docs canônicos para mapear onde `agents.prompt`, `agents.config`, `auxiliary_templates.default_config`, LangGraph state, SearchService e memory tables entram no runtime.

Saída: relatório apenas.

### 42A1 — Save SPEC-004 + README link

Objetivo: salvar esta SPEC em `docs/canon/SPEC-004-agent-intelligence-context-architecture.md` e linkar no README.

Sem código.

### 42A2 — Context Assembly Design Report

Objetivo: desenhar como o Context Package deve ser representado sem quebrar Smith.

Sem implementação ainda.

### 42A3 — AutoBrokers Core Blueprint v1

Objetivo: criar blueprint/prompt canônico do chat principal.

Pode ser documento primeiro; depois seed no agente.

### 42A4 — Attendance Boundary Blueprint v1

Objetivo: separar agente de atendimento do chat principal.

### 42A5 — Auxiliary Blueprint Contract

Objetivo: padronizar `requires_knowledge`, `requires_memory`, `requires_tools`, `side_effects`, `risk_level`.

### 41C.2C — Global Knowledge Collection + Curated Ingestion

Só depois das definições de inteligência e contexto.

---

## 16. Critérios de aprovação da SPEC-004

A SPEC está aprovada quando:

- diferencia claramente Core, Attendance, Auxiliar, Corredor e SubAgent;
- preserva Smith;
- não cria motor paralelo;
- define como prompt/RAG/memória/workflow se combinam;
- define o que pode e não pode entrar no RAG;
- define autoaprendizado como futuro governado;
- define roadmap de implementação;
- orienta Claude/Codex a não simplificar a arquitetura;
- permite criar agentes muito inteligentes sem abrir riscos.

---

## 17. Regra final

> O AutoBrokers não deve ser um chatbot de seguros.  
> O AutoBrokers deve ser o sistema operacional agentico da corretora.  
> O chat principal é o cérebro conversacional interno.  
> Os atendentes são operadores especializados.  
> Os auxiliares são capacidades instaláveis.  
> Os corredores são trilhos operacionais.  
> O RAG é conhecimento consultável.  
> A memória é contexto governado.  
> As tools executam com permissão.  
> HITL protege o mundo real.  
> O Smith continua sendo o runtime técnico.  
> A camada AutoBrokers transforma o runtime em produto vertical extraordinário.
