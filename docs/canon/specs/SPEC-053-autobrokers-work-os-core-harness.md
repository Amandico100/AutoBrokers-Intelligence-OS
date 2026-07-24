# SPEC-053 — AutoBrokers Work OS: Core Harness, Skills, Tool Gateway, Execução Durável e Control Plane

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANÔNICA — aprovada pelo Founder em 24/07/2026  
**Autoridade superior:** `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`  
**Runtime preservado:** Smith + LangGraph/LangChain + FastAPI + Supabase + Redis + Qdrant + MinIO  
**Nome oficial do agente central:** **AutoBrokers**  
**Escopo:** transformar o AutoBrokers Core em um sistema operacional de trabalho verticalizado para corretoras de seguros, com Skills, ferramentas, conectores, MCPs, Auxiliares, rotinas, tarefas duráveis, aprovações, artifacts, entregas, observabilidade e administração centralizada.  
**Natureza desta SPEC:** arquitetura e contratos. Esta SPEC não autoriza, por si só, deploy, migration ou alteração em produção.

---

## 0. Aviso de autoridade, leitura obrigatória e superação parcial

Esta SPEC é subordinada à SPEC-052 e detalha o **Lote 6 — Harness e ferramentas avançadas** da arquitetura cognitiva unificada.

Antes de planejar ou executar qualquer mudança nesta área, o agente de desenvolvimento DEVE ler, nesta ordem:

1. `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`;
2. esta `SPEC-053-autobrokers-work-os-core-harness.md`;
3. `../ADR-001-runtime.md`;
4. `../SPEC-002-auxiliares-runtime-smith.md`;
5. `SPEC-019-rotinas-auxiliares-claude-parity.md`;
6. `../SPEC-014-capability-registry-knowledge-os.md`;
7. documentos de Vault, HITL, Context Assembly e runtime citados nesta SPEC;
8. código real, migrations e testes atuais.

Em caso de conflito:

```text
SPEC-052
→ SPEC-053
→ SPECs subordinadas posteriores
→ ADRs e SPECs históricas quando não conflitarem
```

Esta SPEC **supera parcialmente** as seguintes decisões anteriores:

- a equivalência entre “Auxiliar” e “Rotina” presente na SPEC-019;
- o uso de `auxiliary_runs` ou `routine_runs` como histórias de execução universais;
- qualquer interpretação de que um Auxiliar precise ser sempre um Agent Smith dedicado;
- qualquer implementação em que o Core carregue indiscriminadamente todas as tools;
- qualquer aprovação baseada apenas em texto de prompt;
- qualquer tarefa longa executada apenas dentro de um request web ou loop in-process sem estado durável;
- qualquer artifact tratado apenas como texto solto ou arquivo sem catálogo, lineage, permissão e lifecycle.

Os documentos anteriores não devem ser apagados. Devem receber avisos de superação parcial quando a implementação desta arquitetura começar.

### 0.1 Correção da auditoria do Opus 4.8

A auditoria read-only usada como insumo foi realizada sobre um checkout anterior ao commit da SPEC-052. A SPEC-052 existe na `main` e é soberana.

Nenhum executor pode trabalhar a partir de um checkout antigo. Antes de auditar ou implementar:

```text
git fetch origin
git checkout main
git pull origin main
git rev-parse HEAD
```

O executor deve registrar o commit auditado no relatório de início e no relatório final.

---

## 1. Visão de produto

O AutoBrokers deve ser o ambiente de trabalho inteligente da corretora de seguros.

Ele não deve apenas responder perguntas. Deve ser capaz de:

- entender um resultado desejado;
- reunir o contexto correto;
- escolher a Skill adequada;
- selecionar somente as ferramentas necessárias;
- pesquisar e analisar;
- consultar sistemas vivos;
- delegar para especialistas;
- executar trabalhos de várias etapas;
- pedir aprovação quando necessário;
- gerar artifacts profissionais;
- entregar pelo canal escolhido;
- acompanhar o resultado;
- aprender com a execução sem criar verdade automática;
- oferecer automações e Auxiliares quando identificar recorrência.

Visão resumida:

```text
O corretor descreve o que precisa.
O AutoBrokers transforma o pedido em trabalho governado.
O sistema executa, comprova, entrega e acompanha o resultado.
```

### 1.1 Objetivos de negócio

O Work OS deve contribuir diretamente para:

- aumentar receita;
- melhorar conversão e retenção;
- recuperar oportunidades perdidas;
- reduzir inadimplência;
- reduzir retrabalho;
- reduzir tempo gasto em tarefas manuais;
- aumentar capacidade operacional sem aumentar equipe na mesma proporção;
- melhorar qualidade e velocidade de decisão;
- transformar dados dispersos em ações;
- aumentar dependência positiva do produto pelo valor acumulado;
- elevar ticket, retenção e expansão do AutoBrokers.

### 1.2 O diferencial defensável

O AutoBrokers não deve competir com ChatGPT, Claude, Hermes ou outros agentes horizontais em generalidade.

Deve combinar padrões operacionais semelhantes com ativos verticais que esses produtos não possuem com profundidade:

- InfoCap, Quiver e outros sistemas de gestão;
- WhatsApp operacional da corretora;
- apólices e documentos;
- Atlas de rotas;
- seguradoras e procedimentos;
- portais autenticados;
- atendimentos reais;
- dados financeiros e operacionais;
- conhecimento global proprietário de seguros;
- Auxiliares específicos para corretoras;
- experiência acumulada entre tenants, sempre anonimizada e governada.

---

## 2. Princípios arquiteturais invioláveis

1. **Um único cérebro lógico:** Smith continua sendo o runtime técnico central.
2. **Nenhum runtime paralelo:** não instalar Hermes, OpenClaw, Cowork ou outro framework como segunda autoridade.
3. **SPEC-052 governa contexto, memória, RAG e aprendizagem.**
4. **Supabase é a fonte durável de verdade operacional.**
5. **Redis é transitório:** fila, lock, debounce, lease e cache.
6. **Qdrant é índice derivado, não autoridade.**
7. **MinIO é o armazenamento de arquivos e artifacts.**
8. **Capability Registry governa acesso.**
9. **Vault governa segredos e conexões.**
10. **Skills são procedimentos; não são memória nem RAG.**
11. **MCP é protocolo; não é produto nem cérebro.**
12. **Auxiliar é camada de produto; não é sinônimo de Agent ou Rotina.**
13. **Rotina é gatilho/agendamento; não é trabalhador.**
14. **Work Run é a execução universal.**
15. **Artifact é resultado de primeira classe.**
16. **Ações externas sensíveis exigem gate executável.**
17. **Toda execução deve ser observável, mensurável e tenant-scoped.**
18. **Nenhum dado pode atravessar tenants.**
19. **Nenhum refactor gigante sem necessidade.**
20. **Consolidar e migrar antes de criar uma segunda versão da mesma peça.**

---

## 3. Referências modeladas — o que copiar e o que não copiar

Esta arquitetura incorpora padrões observados em produtos e runtimes modernos, sem copiar marcas ou instalar sistemas paralelos.

### 3.1 Claude Cowork

Padrões aproveitados:

- delegação de trabalhos completos;
- tarefas recorrentes com os mesmos recursos do ambiente interativo;
- conectores antes de computer use;
- acompanhamento do trabalho;
- entrega de relatórios, briefings e documentos finalizados;
- aprovação e controle humano.

Regra modelada:

```text
adapter/API oficial
→ conector autorizado
→ tool especializada
→ browser estruturado
→ computer use como último recurso
```

### 3.2 ChatGPT Work, Skills e Plugins

Padrões aproveitados:

- distinção entre conversa rápida e trabalho longo;
- Skills reutilizáveis com instruções, exemplos, código e recursos;
- plugins como pacotes de workflow compostos por Skills + Apps + templates;
- administração por workspace, função e permissão;
- artifacts e entregáveis finalizados.

Modelagem AutoBrokers:

```text
Capability Pack
├── Skills
├── ferramentas/conectores
├── templates
├── policies
└── evals
```

### 3.3 Hermes

Padrões aproveitados:

- Skills carregadas sob demanda;
- progressive disclosure;
- memória separada de procedimento;
- scheduler;
- delegação para subagentes;
- toolsets;
- provider/model routing;
- aprendizagem governada;
- isolamento e sandbox;
- continuidade entre canais.

Não copiar:

- filesystem local como fonte de verdade do produto SaaS;
- autoedição irrestrita de Skills globais;
- autonomia sem aprovação em ações de negócio;
- memória pessoal sem isolamento multi-tenant.

### 3.4 LangGraph

Padrões obrigatórios:

- checkpoint persistente;
- threads distintas para conversa e trabalho;
- interrupts para HITL;
- resume por comando;
- side effects idempotentes;
- recuperação a partir do último checkpoint válido;
- tracing de estados e etapas.

### 3.5 Model Context Protocol

Padrões obrigatórios:

- host como autoridade de permissão e consentimento;
- clientes isolados por servidor;
- capability negotiation;
- diferenciação entre tools, resources e prompts;
- OAuth 2.1 para servidores remotos quando aplicável;
- sandbox e menor privilégio;
- consentimento explícito para ações sensíveis;
- tool descriptions tratadas como conteúdo não confiável até homologação.

---

## 4. Ontologia oficial do AutoBrokers Work OS

A partir desta SPEC, estes termos possuem significado normativo.

### 4.1 Outcome

Resultado de negócio desejado pelo usuário.

Exemplos:

- “Quero entender por que a inadimplência aumentou.”
- “Quero receber um briefing toda manhã.”
- “Quero um relatório executivo da semana.”
- “Quero acompanhar concorrentes.”

O Outcome deve ser representado por um `OutcomeSpec`.

### 4.2 Skill

Procedimento versionado que ensina o sistema a produzir um resultado com consistência.

Uma Skill pode incluir:

- instruções;
- critérios de uso;
- inputs;
- passos;
- fontes;
- ferramentas necessárias;
- templates;
- scripts;
- políticas;
- verificação;
- evals;
- exemplos;
- falhas conhecidas.

Skill não é prompt solto.

### 4.3 Capability Pack

Pacote governado de capacidades carregado para uma classe de trabalho.

Pode conter:

- uma ou mais Skills;
- tools;
- MCPs;
- connectors;
- policies;
- templates;
- limites;
- evals.

### 4.4 Tool

Função técnica específica para leitura, cálculo ou ação.

Exemplos:

- consultar apólice;
- buscar cliente;
- ler agenda;
- criar rascunho de e-mail;
- gerar PDF;
- pesquisar web.

### 4.5 MCP

Protocolo para expor tools, resources e prompts.

MCP não deve aparecer como conceito técnico para o corretor. Na UI deve aparecer como “conexão”, “ferramenta” ou “recurso”, conforme o caso.

### 4.6 Connector

Vínculo autenticado com sistema externo.

Exemplos:

- Google Workspace;
- Microsoft 365;
- Slack;
- Notion;
- InfoCap;
- Quiver;
- WhatsApp;
- Firecrawl;
- portal de seguradora.

### 4.7 Agent e Subagent

Executores cognitivos Smith.

- Agent pode orquestrar e conversar.
- Subagent executa especialidade delimitada.
- Nenhum deles é automaticamente um produto instalável.

### 4.8 Workflow

Sequência de etapas coordenadas com estados, decisões e gates.

### 4.9 Auxiliar

Trabalhador de produto instalado e configurado para uma corretora.

Um Auxiliar pode usar:

- specific executor;
- Smith Agent;
- Subagent;
- Skill;
- workflow;
- rotina;
- conjunto híbrido.

Auxiliar não é motor técnico.

### 4.10 Rotina

Gatilho que inicia um trabalho.

Tipos futuros previstos:

- horário único;
- recorrência;
- evento;
- condição;
- webhook governado;
- comando manual;
- resposta a sinal interno.

### 4.11 Work Run

Uma execução concreta, universal e auditável.

Todo trabalho relevante deve possuir `run_id`.

### 4.12 Work Step

Etapa de uma execução.

### 4.13 Approval

Decisão humana vinculada a um trabalho, etapa ou ação.

### 4.14 Artifact

Resultado persistido e administrável.

Exemplos:

- relatório web;
- PDF;
- planilha;
- CSV;
- apresentação;
- gráfico;
- dossiê;
- documento;
- pacote de evidências;
- arquivo gerado;
- conjunto de arquivos.

### 4.15 Delivery

Entrega de um artifact ou resultado por canal.

### 4.16 Learning Signal

Registro de evidência que pode contribuir para melhoria de produto, Skill, conhecimento ou experiência.

---

## 5. Fronteiras de produto

### 5.1 AutoBrokers Core

É a porta de entrada e o coordenador interno da corretora.

Responsabilidades:

- conversar com o corretor;
- entender Outcome;
- explicar;
- pesquisar;
- analisar;
- consultar dados vivos;
- selecionar Skill;
- planejar contexto;
- delegar;
- criar trabalhos;
- acompanhar progresso;
- solicitar aprovação;
- apresentar artifacts;
- criar ou instalar Auxiliares;
- criar rotinas;
- sugerir automação;
- explicar falhas em linguagem humana.

### 5.2 Atendimento

Agentes externos voltados ao segurado ou cliente.

Restrições:

- corredores definidos;
- menor privilégio;
- Evidence Pack;
- regras de cobertura;
- handoff humano;
- sem ferramentas genéricas de gestão, marketing ou administração;
- sem criação autônoma de Auxiliares;
- sem acesso global irrestrito.

### 5.3 Auxiliares

Trabalhadores internos especializados.

Podem ser:

- sob demanda;
- recorrentes;
- monitoradores;
- analistas;
- produtores de artifacts;
- operadores assistidos;
- coordenadores de workflow.

### 5.4 Portal Admin

Control Plane da plataforma.

Não é um segundo runtime. É a superfície administrativa das mesmas fontes de verdade.

---

## 6. Estado atual que deve ser preservado

A implementação futura deve partir do que existe.

Preservar:

- Smith StateGraph;
- Context Assembly;
- AsyncPostgresSaver;
- `agents` e `agent_delegations`;
- Capability Registry;
- Vault;
- token/cost metering;
- LangSmith tracing;
- MinIO;
- Redis;
- motor de rotinas existente;
- `routine_templates`;
- `auxiliary_templates`;
- `tenant_auxiliaries`;
- Atlas;
- RAG e memória sob a SPEC-052;
- Garimpo e mecanismos proativos como fundação evolutiva;
- delivery WhatsApp existente;
- Portal Worker.

Não reconstruir essas peças sem prova de que estão estruturalmente inválidas.

---

## 7. Problemas atuais que esta arquitetura resolve

1. Checkpointer orientado à conversa, sem modelo universal de trabalho.
2. Tarefas longas in-process, sem sobrevivência garantida a restart.
3. Approvals existentes em dados/UI, mas sem gate LangGraph executável uniforme.
4. Ausência de artifact como objeto de primeira classe.
5. Duas histórias de execução: `auxiliary_runs` e `routine_runs`.
6. Confusão entre Auxiliar, Agent e Rotina.
7. Tool authority ainda parcial/permissiva em caminhos legados.
8. HTTP genérico sem política de egress/SSRF suficientemente forte.
9. MCP subprocess herdando ambiente excessivo.
10. Tabelas ou políticas não totalmente reproduzíveis por migrations.
11. Relatórios predominantemente textuais.
12. Proatividade baseada mais em mensagem do que em evidência, impacto e execução.
13. Garimpo sem ciclo completo de demanda → produto → resultado.
14. Ausência de biblioteca formal de Skills.
15. Ausência de Tool Gateway com progressive disclosure.
16. Portal Admin sem Control Plane consolidado para o novo ecossistema.

---

## 8. Arquitetura canônica

```text
Usuário
  │
  ▼
AutoBrokers Core
  │
  ├── Outcome & Intent Router
  ├── Context Planner — SPEC-052
  ├── Skill Resolver
  ├── Capability/Policy Resolver
  ├── Model Router
  └── Work Planner
          │
          ▼
      Work Run Service
          │
          ├── Supabase: estado durável
          ├── Redis: fila, lease, locks
          ├── Smith Worker: execução
          ├── LangGraph: checkpoints/interrupts
          ├── Tool Gateway
          ├── Agents/Subagents/Executors
          ├── Approval Service
          ├── Artifact Service
          └── Delivery Service
                  │
                  ▼
 Dashboard / WhatsApp / E-mail / Link / Sistemas
                  │
                  ▼
 Observability / Billing / Garimpo / Learning Fabric
                  │
                  ▼
 Portal Admin Control Plane
```

---

## 9. Contratos centrais

Os nomes finais podem ser refinados na implementação, mas as responsabilidades não podem ser removidas.

### 9.1 OutcomeSpec

Campos mínimos:

```yaml
outcome_id: uuid
company_id: uuid
user_id: uuid
intent: report.executive_weekly
goal: "Entender desempenho da corretora na semana"
constraints: []
expected_outputs:
  - web_report
  - pdf
priority: normal
risk_level: medium
source: chat
```

### 9.2 SkillManifest

```yaml
slug: executive-weekly-report
version: 1.0.0
status: published
category: analytics
owner: platform
supported_roles:
  - core
  - auxiliary
triggers:
  - intent: report.executive_weekly
inputs:
  required:
    - company_id
outputs:
  - artifact.web_report
  - artifact.pdf
capability_pack: analytics.reporting
context_requirements:
  - tenant_operational_data
  - user_preferences_optional
approval_policy: no_external_action
budget_policy: report_standard
procedure:
  - collect
  - validate
  - calculate
  - interpret
  - render
  - verify
verification:
  - calculations_reconciled
  - sources_present
  - tenant_scope_valid
```

### 9.3 CapabilityPack

```yaml
slug: analytics.reporting
version: 1.0.0
skills:
  - executive-weekly-report
tools:
  - infocap.read.analytics
  - csv.analytics
  - chart.render
  - artifact.publish
connectors:
  optional:
    - infocap
policies:
  egress: deny_by_default
  writes: artifact_only
  approval: none
limits:
  max_tool_calls: 30
  max_runtime_seconds: 600
```

### 9.4 WorkPlan

Campos:

- objetivo;
- etapas;
- dependências;
- ferramentas;
- modelo por etapa;
- budgets;
- pontos de aprovação;
- outputs;
- critérios de conclusão;
- política de retry;
- política de cancelamento.

### 9.5 WorkRun

Campos mínimos:

- `id`;
- `company_id`;
- `user_id`;
- `auxiliary_id`, opcional;
- `routine_id`, opcional;
- `skill_slug` e versão;
- `outcome_spec`;
- `status`;
- `priority`;
- `risk_level`;
- `budget`;
- `cost_accumulated`;
- `thread_id`;
- `current_step`;
- `progress`;
- `attempt`;
- `idempotency_key`;
- `created_at`, `started_at`, `paused_at`, `finished_at`;
- `heartbeat_at`;
- `lease_owner` e `lease_until`;
- `error_code` e mensagem humana;
- `result_summary`;
- `metadata`.

### 9.6 WorkStep

Campos:

- run;
- ordinal;
- tipo;
- executor;
- input hash;
- status;
- tentativas;
- checkpoint;
- tool calls;
- custo;
- timestamps;
- erro;
- output ref;
- approval ref.

### 9.7 ApprovalPolicy e ApprovalRequest

Campos:

- ação proposta;
- reason;
- risk;
- preview;
- dados afetados;
- ferramenta;
- custo previsto;
- prazo de validade;
- decisões permitidas;
- reviewer role;
- status;
- decisão;
- edição aprovada;
- auditoria.

### 9.8 ArtifactManifest

```yaml
artifact_id: uuid
company_id: uuid
run_id: uuid
type: report
format: html
classification: tenant_private
title: "Relatório Executivo — Semana 30"
version: 1
storage_ref: minio://...
mime_type: text/html
source_hash: sha256
render_template: executive-report-v1
created_by: work_run
expires_at: null
share_policy: authenticated
```

### 9.9 DeliverySpec

Campos:

- artifact/resultado;
- canal;
- destinatário;
- horário;
- approval;
- status;
- tentativas;
- confirmação;
- erro;
- tracking.

### 9.10 LearningSignal

Campos:

- origem;
- company;
- user role;
- demanda;
- Skill utilizada;
- Auxiliar solicitado;
- resultado;
- feedback;
- custo;
- tempo economizado;
- valor percebido;
- candidato a template;
- PII removida;
- status de curadoria.

---

## 10. Execução durável

### 10.1 Duas continuidades diferentes

```text
Conversa:
thread_id = chat:{company_id}:{session_id}

Trabalho:
thread_id = work:{company_id}:{run_id}
```

Não reutilizar o mesmo thread para conversas e trabalhos longos.

### 10.2 Fonte de verdade

- Supabase: estado empresarial do Work Run.
- LangGraph checkpointer: estado cognitivo e checkpoints.
- Redis: fila, lock, lease, debounce e notificações.
- MinIO: artifacts e anexos.

### 10.3 Worker

Criar ou consolidar um processo dedicado, conceitualmente:

```text
autobrokers-smith-worker
```

O worker:

- usa o mesmo código Smith;
- não é outro cérebro;
- consome fila;
- adquire lease;
- envia heartbeat;
- executa/retoma Work Runs;
- registra eventos;
- libera lease;
- recupera trabalhos órfãos;
- respeita limites por tenant;
- pode ser escalado horizontalmente no futuro.

### 10.4 Estados canônicos

```text
draft
queued
planning
running
waiting_approval
waiting_input
paused
retry_scheduled
cancelling
cancelled
failed
completed
expired
```

### 10.5 Idempotência

Toda etapa com side effect deve usar chave idempotente.

Formato recomendado:

```text
{company_id}:{run_id}:{step_id}:{action}:{payload_hash}
```

Nunca executar side effect antes de um interrupt sem garantir idempotência.

### 10.6 Retry

Política deve distinguir:

- erro transitório;
- erro de autenticação;
- erro de validação;
- erro de policy;
- erro do modelo;
- erro externo definitivo;
- aprovação expirada;
- artifact inválido.

### 10.7 Cancelamento

Cancelamento deve:

- impedir novas etapas;
- tentar interromper execução ativa;
- não desfazer automaticamente ações externas já confirmadas;
- registrar o ponto alcançado;
- preservar artifacts existentes;
- oferecer rollback quando definido pelo workflow.

### 10.8 Recuperação após restart

Work Run com lease expirada e status ativo deve ser reavaliado.

O sistema deve:

- localizar último checkpoint válido;
- verificar idempotência;
- retomar ou marcar para revisão;
- nunca duplicar side effects.

---

## 11. Human-in-the-Loop executável

### 11.1 Regra

Prompt não é gate.

Aprovação sensível deve usar:

- estado persistente;
- interrupt LangGraph ou gate equivalente governado;
- registro em `approval_requests`/contrato canônico;
- UI de approve/edit/reject;
- resume explícito;
- auditoria.

### 11.2 Classes de risco

**R0 — leitura segura:** sem approval.  
**R1 — criação de draft/artifact privado:** normalmente sem approval.  
**R2 — entrega ou alteração reversível:** approval configurável.  
**R3 — comunicação externa, publicação ou escrita relevante:** approval obrigatório por padrão.  
**R4 — financeiro, jurídico, cobertura, cancelamento, exclusão ou ação irreversível:** approval obrigatório e reviewer qualificado.

### 11.3 Preview humano

A tela deve mostrar:

- o que será feito;
- por quê;
- onde;
- com quais dados;
- quem será afetado;
- custo estimado;
- riscos;
- conteúdo exato quando possível;
- alternativas;
- validade da aprovação.

### 11.4 Decisões

- aprovar;
- editar e aprovar;
- rejeitar;
- pedir esclarecimento;
- delegar aprovação;
- aprovar uma vez;
- criar regra futura, quando permitido.

---

## 12. Skill Registry

### 12.1 Fonte de verdade

Skills globais publicadas devem existir em catálogo versionado no Supabase e possuir assets versionados em repositório/MinIO conforme o tipo.

Não usar diretório local mutável de um worker como fonte de verdade global.

### 12.2 Progressive disclosure

O Core não deve carregar todas as Skills.

Fluxo:

```text
compact skill index
→ resolver por intent/outcome
→ carregar SkillManifest
→ carregar somente referências necessárias
→ carregar templates/scripts sob demanda
```

### 12.3 Lifecycle

```text
draft
→ review
→ tested
→ approved
→ published
→ deprecated
→ revoked
```

### 12.4 Escopos

- global AutoBrokers;
- privado de tenant;
- privado de usuário, somente quando fizer sentido;
- experimental/sandbox.

### 12.5 Autoevolução

Agentes podem propor patch para Skill.

Não podem publicar diretamente.

Fluxo:

```text
execução
→ falha/correção/aprendizado
→ Skill Candidate
→ diff proposto
→ testes
→ revisão
→ publicação versionada
```

### 12.6 Evals por Skill

Cada Skill publicada deve possuir:

- golden cases;
- entradas inválidas;
- casos sem dados;
- casos multi-tenant;
- casos de tool failure;
- custo esperado;
- limite de latência;
- critérios de artifact;
- regressão de versão.

---

## 13. Tool Gateway e Capability Packs

### 13.1 Problema

Anexar muitas tools ao agente reduz clareza, aumenta custo, risco e chance de seleção incorreta.

### 13.2 Regra canônica

O Core recebe apenas o pacote necessário para a tarefa.

```text
Outcome/Intent
→ Skill
→ Capability Pack
→ Policy
→ ferramentas liberadas
```

### 13.3 Hierarquia de execução

```text
1. função interna determinística
2. adapter/API oficial
3. conector autenticado
4. MCP homologado
5. browser estruturado
6. computer use, apenas último recurso
```

### 13.4 Tools da plataforma × tools do tenant

**Plataforma:** chave e custo do AutoBrokers, rate limit por tenant.  
Exemplos: Firecrawl, renderização, OCR homologado, serviço de relatórios.

**Tenant/usuário:** autenticação própria.  
Exemplos: Gmail, Outlook, Drive, Notion, Slack, conta Canva.

### 13.5 Homologação de MCP

Todo MCP deve possuir:

- owner;
- origem;
- versão;
- assinatura/hash quando possível;
- tools permitidas;
- scopes;
- variáveis liberadas;
- rede liberada;
- filesystem liberado;
- risk class;
- approval policy;
- timeout;
- rate limit;
- custo;
- healthcheck;
- evals;
- rollback/revogação.

### 13.6 Segurança

- deny by default;
- egress allowlist;
- bloqueio de IP privado e metadata endpoints;
- DNS rebinding protection;
- redirects revalidados;
- limite de response size;
- content-type validation;
- environment explícito, nunca `os.environ` completo;
- sandbox para processos;
- secrets via Vault;
- OAuth e PKCE quando aplicável;
- logs sem segredo;
- autorização vinculada a tenant/user.

---

## 14. Auxiliares, Rotinas e Work Runs

### 14.1 Decisão central

Não escolher “Auxiliar ou Rotina”. São peças complementares.

```text
Auxiliar = trabalhador instalado
Rotina = gatilho
Work Run = execução
Skill = método
Workflow = coordenação
Agent/Executor = motor
```

### 14.2 Modelo futuro

```text
auxiliary_templates
→ catálogo global

tenant_auxiliaries
→ instalação e configuração local

skills / skill_versions
→ procedimentos

routines / schedules
→ gatilhos

work_runs
→ histórico universal

work_steps
→ etapas

work_approvals
→ decisões

artifacts
→ entregáveis

deliveries
→ distribuição
```

### 14.3 Migração do legado

`auxiliary_runs` e `routine_runs` não devem ser apagados abruptamente.

Fases:

1. inventário;
2. contrato de compatibilidade;
3. dual-write temporário somente se indispensável;
4. backfill;
5. validação;
6. leitura canônica por `work_runs`;
7. desativação das escritas antigas;
8. retenção histórica;
9. remoção futura aprovada.

### 14.4 Factory conversacional

O usuário poderá dizer:

> “Crie um auxiliar que toda sexta-feira me mostre atendimentos parados.”

Fluxo:

```text
pedido
→ entender Outcome
→ decidir se é rotina, Auxiliar ou ambos
→ selecionar template/Skill
→ checar conectores
→ estimar custo
→ gerar blueprint humano
→ solicitar aprovação
→ instalar/configurar
→ executar teste
→ ativar
→ acompanhar
```

---

## 15. Artifacts como subsistema de primeira classe

### 15.1 Decisão

Artifacts constituem um domínio próprio e devem receber uma SPEC subordinada exclusiva.

Eles não devem ser criados como utilitários isolados dentro de cada Auxiliar.

Nome da futura frente:

```text
AutoBrokers Artifact Hub & Report Studio
```

### 15.2 Tipos iniciais

- relatório web;
- PDF;
- planilha XLSX;
- CSV;
- documento;
- apresentação;
- gráfico;
- dossiê;
- Evidence Pack exportável;
- briefing;
- pacote ZIP, quando necessário.

### 15.3 Componentes

- Artifact Registry;
- Template Registry;
- Renderers;
- Chart Service;
- Document Composer;
- Spreadsheet Composer;
- Presentation Composer;
- Web Report Renderer;
- PDF Renderer;
- storage MinIO;
- versionamento;
- share links;
- autorização;
- expiração;
- revogação;
- preview;
- delivery.

### 15.4 Templates

Templates devem declarar:

- tipo;
- versão;
- slots;
- brand tokens;
- dados obrigatórios;
- componentes permitidos;
- responsividade;
- acessibilidade;
- validação;
- renderer;
- formatos de exportação;
- exemplos;
- eval visual.

### 15.5 Segurança

- prefixo de storage por tenant;
- classificação;
- links autenticados por padrão;
- share token revogável quando autorizado;
- sem URL interna do MinIO exposta;
- PII e retenção governadas;
- watermark opcional;
- logs de visualização e download.

### 15.6 Relação com o chat

O AutoBrokers deve poder:

- mostrar preview dentro da conversa;
- explicar como o artifact foi produzido;
- oferecer ajustes;
- versionar nova edição;
- enviar;
- agendar nova geração;
- transformar o pedido em Auxiliar.

---

## 16. Work Experience do corretor

O usuário não deve ver complexidade técnica.

### 16.1 Estados em linguagem humana

- Preparando o plano;
- Buscando informações;
- Analisando dados;
- Aguardando sua aprovação;
- Criando o relatório;
- Enviando;
- Concluído;
- Preciso que você reconecte o InfoCap;
- Não consegui concluir esta etapa;
- Retomarei do último ponto seguro.

### 16.2 Chat como cockpit

O chat deve exibir:

- plano resumido;
- progresso;
- etapas concluídas;
- solicitações;
- approvals;
- artifacts;
- custo quando relevante;
- opção de cancelar;
- opção de automatizar;
- opção de criar Auxiliar;
- histórico e retomada.

### 16.3 Resultado antes da tecnologia

Evitar termos como:

- MCP;
- worker;
- thread_id;
- lease;
- checkpoint;
- service role;
- provider adapter.

A UI deve falar em resultados, conexões, etapas e decisões.

---

## 17. Portal Admin como Control Plane

### 17.1 Papel

O Portal Admin será a central de comando do ecossistema.

Ele deve permitir ao Founder/equipe:

- entender saúde da plataforma;
- investigar falhas;
- administrar tenants;
- governar Skills e Auxiliares;
- acompanhar custos;
- aprovar publicações;
- controlar rollouts;
- pausar recursos;
- revisar aprendizagem;
- administrar artifacts;
- gerenciar segurança;
- atuar sem depender de SQL para operações comuns.

### 17.2 Regra transversal

Toda SPEC subordinada deve incluir uma seção:

```text
Admin Projection
```

Ela deve declarar:

- dados visíveis;
- ações permitidas;
- ações sensíveis;
- métricas;
- alertas;
- filtros;
- linguagem humana;
- audit trail;
- rollback;
- feature flags.

### 17.3 Arquitetura de navegação recomendada

#### Visão Geral

- tenants saudáveis;
- incidentes;
- execuções;
- approvals;
- custo;
- falhas;
- oportunidades;
- serviços degradados.

#### Trabalhos

- fila;
- rodando;
- aguardando;
- pausados;
- falhos;
- concluídos;
- detalhes por etapa;
- retomar;
- cancelar;
- reexecutar etapa segura.

#### Auxiliares

- catálogo;
- versões;
- instalações;
- saúde;
- uso;
- resultado;
- rollout;
- suspensão;
- atualização.

#### Skills & Capabilities

- Skills;
- versões;
- dependências;
- tools;
- políticas;
- evals;
- publicação;
- revogação.

#### Conexões

- conectada;
- expirada;
- falta autenticação;
- escopos;
- última utilização;
- saúde;
- sem revelar segredo.

#### Artifacts

- tenant;
- tipo;
- tamanho;
- versão;
- validade;
- deliveries;
- visualizações;
- revogação.

#### Inteligência

- Garimpo;
- demandas;
- clusters;
- candidatos a Auxiliares;
- Knowledge Candidates;
- Skill Candidates;
- impacto e resultado.

#### Segurança

- tools bloqueadas;
- SSRF;
- policy denials;
- approvals;
- tentativas suspeitas;
- incidentes de isolamento;
- auditoria.

#### Evals & Releases

- suites;
- regressões;
- versão;
- rollout;
- feature flags;
- rollback.

### 17.4 UX em linguagem humana

Exemplo correto:

> “O Relatório Executivo da Resulta parou porque a conexão com o InfoCap expirou.”

Detalhe técnico opcional:

> `provider_auth_expired` — etapa `collect_operational_data`.

### 17.5 Autonomia administrativa

O Admin deve permitir, com políticas:

- pausar Skill;
- revogar tool;
- suspender Auxiliar;
- limitar tenant;
- alterar rollout;
- reprocessar artifact;
- retomar Work Run;
- rejeitar candidato;
- aprovar publicação;
- abrir diagnóstico;
- exportar auditoria.

---

## 18. Segurança e multi-tenancy

### 18.1 Quatro camadas de isolamento

```text
RLS
+ filtros obrigatórios no repositório/service
+ constraints e foreign keys
+ testes automáticos de isolamento
```

RLS não substitui filtros quando service role é usada.

### 18.2 Schema governance

Antes de criar novas tabelas:

- comparar produção;
- snapshot atual;
- migrations;
- constraints;
- policies;
- índices;
- triggers;
- funções.

Migrations devem ser:

- idempotentes;
- expand-first;
- verificáveis;
- com rollback documentado;
- seguras para dados existentes.

### 18.3 Secrets

- Vault somente;
- nenhum segredo em blueprint;
- nenhum segredo em logs;
- nenhum segredo em artifact;
- environment mínimo por processo;
- rotação e revogação;
- acesso auditado.

### 18.4 Dados e PII

- classificação de dados;
- minimização;
- finalidade;
- retenção;
- deleção;
- anonimização;
- proteção de histórico;
- global learning somente após gates da SPEC-052.

---

## 19. Custos, limites e billing

Cada Work Run deve medir:

- tokens por modelo;
- tool calls;
- custo de API;
- custo de scraping;
- tempo de worker;
- armazenamento;
- renderização;
- delivery;
- retries;
- custo total;
- custo por artifact;
- custo por resultado.

### 19.1 Budgets

Tipos:

- por run;
- por tenant/dia;
- por Auxiliar/mês;
- por Skill;
- por ferramenta;
- por usuário;
- soft limit;
- hard limit.

### 19.2 Comportamento

Ao se aproximar do limite:

- reduzir fan-out;
- usar modelo mais econômico quando seguro;
- pedir aprovação para exceder;
- pausar;
- não degradar silenciosamente qualidade crítica.

---

## 20. Observabilidade

Cada Work Run deve registrar:

- Outcome;
- intent;
- Skill e versão;
- Context Plan;
- fontes;
- tools;
- model routing;
- passos;
- checkpoints;
- approvals;
- artifacts;
- deliveries;
- custo;
- latência;
- retries;
- falhas;
- resultado;
- feedback;
- learning signals.

### 20.1 Eventos canônicos

Exemplos:

- `work.run.created`;
- `work.run.queued`;
- `work.run.started`;
- `work.step.started`;
- `tool.call.requested`;
- `approval.requested`;
- `approval.resolved`;
- `artifact.created`;
- `delivery.completed`;
- `work.run.completed`;
- `work.run.failed`;
- `learning.signal.created`.

### 20.2 Métricas de negócio

- trabalhos concluídos;
- taxa de sucesso;
- tempo economizado;
- valor recuperado/estimado;
- redução de pendências;
- adoção de Auxiliares;
- uso por função;
- sugestões aceitas;
- artifacts utilizados;
- retenção correlacionada.

---

## 21. Learning e demanda de produto

Todo pedido relevante pode alimentar o Garimpo v3.

Registrar:

- problema;
- tarefa;
- frequência;
- cargo;
- tenant;
- tentativa de solução;
- Skill usada;
- ferramenta faltante;
- Auxiliar solicitado;
- resultado;
- feedback;
- tempo/custo;
- padrão anonimizado.

### 21.1 Promoção para template global

Critérios:

- recorrência entre tenants;
- impacto;
- viabilidade;
- segurança;
- dados necessários;
- custo;
- resultado comprovado;
- generalização;
- ausência de PII.

---

## 22. Casos de uso inaugurais

A arquitetura deve ser validada por cinco experiências.

### 22.1 Relatório Executivo

- sob demanda e recorrente;
- dados reais;
- cálculos determinísticos;
- interpretação;
- gráficos;
- recomendações;
- relatório web + PDF;
- entrega.

### 22.2 Briefing Diário

- pendências;
- alertas;
- atendimentos críticos;
- compromissos;
- oportunidades;
- próximos passos;
- dashboard/WhatsApp/e-mail.

### 22.3 Criação de Auxiliar pelo chat

- pedido natural;
- blueprint;
- dependências;
- custo;
- aprovação;
- teste;
- instalação;
- ativação.

### 22.4 Detector de Gargalos e Oportunidades

- sinal real;
- evidência;
- impacto;
- recomendação;
- proposta de automação;
- medição.

### 22.5 Pesquisador Especializado em Seguros

- pesquisa profunda;
- fontes oficiais;
- citações;
- dossiê;
- artifact;
- rotina opcional.

---

## 23. Fora do primeiro ciclo

A arquitetura deve suportar, mas não implementar agora:

- Growth completo;
- publicação social autônoma;
- vídeo em escala;
- prospecção massiva;
- scraping de Google Maps como feature padrão;
- cotação;
- renovação completa;
- campanhas avançadas;
- múltiplos CMS;
- computer use irrestrito.

---

## 24. Sequência de SPECs subordinadas

### SPEC-054 — Foundation Hardening & Schema Governance

- censo real de schema;
- migrations;
- RLS;
- constraints;
- SSRF;
- MCP env/sandbox;
- Authority Strict;
- idempotência;
- testes multi-tenant.

### SPEC-055 — Durable Work Runs, Queue, Checkpoints & HITL

- Work Run;
- steps;
- worker;
- Redis queue;
- leases;
- checkpoints;
- pause/resume;
- approvals;
- retry/cancel/recovery.

### SPEC-056 — Skill Registry & Tool Gateway

- manifests;
- versions;
- Capability Packs;
- progressive disclosure;
- homologação de tools/MCPs;
- budgets;
- policies;
- evals.

### SPEC-057 — Artifact Hub & Report Studio

- artifacts;
- templates;
- renderers;
- web reports;
- PDF;
- planilhas;
- gráficos;
- compartilhamento;
- delivery.

### SPEC-058 — Auxiliary & Routine Factory

- catálogo;
- instalação;
- criação conversacional;
- schedules;
- templates;
- migração de runs;
- versões;
- custo;
- lifecycle.

### SPEC-059 — Briefing, Proatividade & Garimpo v3

- briefing;
- detecção;
- evidências;
- sugestões;
- aprendizado;
- demanda de produto.

### SPEC-060 — Research Intelligence

- Firecrawl/plataforma;
- pesquisa profunda;
- fontes;
- citações;
- dossiês;
- monitoramento.

### SPEC-061 — Portal Admin Control Plane

- UX consolidada;
- trabalhos;
- Auxiliares;
- Skills;
- conexões;
- artifacts;
- segurança;
- inteligência;
- rollouts.

### SPEC-062 — Evals, Billing, Rollout & Production Readiness

- goldens;
- segurança;
- custos;
- cobrança;
- Resulta;
- Autofleet;
- rollout;
- rollback;
- critérios de lançamento.

---

## 25. Estratégia de implementação

### 25.1 Nada de execução monolítica

Cada SPEC subordinada deve ser executada em lotes pequenos e reversíveis.

### 25.2 Ciclo obrigatório

```text
read-only audit atualizada
→ plano de mudança
→ revisão estratégica
→ branch dedicada
→ implementação
→ testes
→ relatório
→ revisão
→ merge
→ deploy controlado
→ verificação
```

### 25.3 Regras para Fable/Codex/qualquer executor

- Não decidir arquitetura durante a execução.
- Não expandir escopo sem autorização.
- Não alterar produção durante auditoria.
- Não criar tabela sem inventário real.
- Não criar motor paralelo.
- Não substituir serviço existente sem migration plan.
- Não apagar legado antes de backfill e prova.
- Não usar `latest` em imagens críticas.
- Não exibir segredo.
- Não executar deploy sem gate explícito.
- Registrar commit inicial e final.
- Produzir lista de arquivos alterados.
- Produzir APPLY/VERIFY/ROLLBACK.
- Separar fatos, inferências e decisões.

---

## 26. Critérios de aceite da SPEC-053

Esta SPEC estará corretamente refletida nas implementações posteriores quando:

- Smith continuar sendo o único runtime;
- SPEC-052 governar contexto e conhecimento;
- Auxiliar e Rotina estiverem separados conceitualmente;
- Work Run for a execução universal;
- conversa e trabalho usarem threads diferentes;
- tarefas sobreviverem a restart;
- approvals forem executáveis;
- side effects forem idempotentes;
- tools forem carregadas sob demanda;
- Skills forem versionadas e testadas;
- MCPs forem homologados;
- secrets estiverem no Vault;
- artifacts forem objetos de primeira classe;
- Portal Admin receber projeções operacionais;
- custos forem atribuídos;
- multi-tenancy tiver proteção em camadas;
- Learning Signals forem governados;
- os cinco casos inaugurais funcionarem ponta a ponta;
- nenhuma estrutura paralela for criada.

---

## 27. Invioláveis finais

1. O nome é **AutoBrokers**.
2. “Jarvys/Jarvis” é metáfora, não marca.
3. Um único cérebro.
4. Um único runtime Smith.
5. Work OS não substitui a SPEC-052.
6. Auxiliar não é Rotina.
7. Rotina não é Agent.
8. Skill não é RAG.
9. MCP não é produto.
10. Artifact não é arquivo órfão.
11. Approval não é frase de prompt.
12. Redis não é fonte de verdade.
13. Qdrant não é fonte de verdade.
14. Nenhum side effect sem idempotência.
15. Nenhum tool gateway permissivo por padrão.
16. Nenhum segredo no ambiente inteiro de subprocessos.
17. Nenhum dado entre tenants.
18. Nenhuma publicação global automática.
19. Nenhuma UI técnica incompreensível para o Admin.
20. Nenhum refactor gigante quando uma migração progressiva resolve.

---

## 28. Referências técnicas consultadas

Referências de modelagem, não dependências obrigatórias:

- LangGraph Persistence, Interrupts e Human-in-the-Loop;
- OpenAI ChatGPT Work, Skills e Plugins;
- Anthropic Claude Cowork, Scheduled Tasks e Computer Use;
- Model Context Protocol Architecture, Tools, Authorization e Security Best Practices;
- Nous Research Hermes Agent, Skills System, Toolsets, Memory, Delegation e Scheduling;
- ADR-001, SPEC-002, SPEC-014, SPEC-019 e SPEC-052 do AutoBrokers.

Qualquer adoção concreta de biblioteca ou serviço externo exigirá auditoria própria de licença, segurança, custo, maturidade, lock-in e compatibilidade multi-tenant.

---

## 29. Decisão final

```text
O AutoBrokers será o ambiente de trabalho inteligente da corretora.

O Core entenderá resultados, reunirá contexto e coordenará o trabalho.
Skills definirão como produzir resultados com qualidade.
Capability Packs carregarão somente as ferramentas necessárias.
Work Runs tornarão tarefas duráveis, auditáveis e retomáveis.
Approvals manterão o humano no controle.
Artifacts transformarão inteligência em entregáveis profissionais.
Auxiliares darão persistência e especialização ao trabalho.
Rotinas iniciarão trabalhos no momento certo.
O Portal Admin permitirá administrar todo o ecossistema com clareza.

Tudo será executado pelo mesmo Smith,
sob a arquitetura cognitiva da SPEC-052,
sem segundo cérebro, sem motor paralelo e sem remendos desnecessários.
```
