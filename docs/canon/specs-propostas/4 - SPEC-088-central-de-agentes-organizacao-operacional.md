# SPEC-088 — A CENTRAL DE AGENTES VIRA UMA ORGANIZAÇÃO OPERACIONAL
## Grupos, papéis, contratos de delegação, especialistas, juízes e execução governada

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANDIDATE SPEC — pronta para aquecimento AAA; ainda não executada  
**Data da redação:** 25/08/2026  
**Baseline observado durante a redação:** `main` em `8b49fdb337a6c37eb2ad181f5bad544a55dc0827`  
**Branch sugerida quando for executar:** `feat/spec088-central-agentes-organizacao-operacional`  
**Depende conceitualmente de:** SPEC-052, 053, 055, 056, 058, 059, 060, 061, 085 e Candidates 086/087/089  
**Runtime preservado:** Smith + LangGraph/LangChain + FastAPI + Supabase/Postgres + Redis + Qdrant + MinIO  
**Autoridades preservadas:** Capability Registry, Skill Registry, Tool Gateway, Vault, Work Runs e Smith  
**Research Pack:** `SPEC-088-central-de-agentes-organizacao-operacional-RESEARCH-PACK.md`

---

# 0. RESULTADO EM UMA FRASE

> **A Central de Agentes deixa de ser uma coleção de nomes e heartbeats e passa a ser o mapa vivo de uma organização de inteligência: quem observa, quem coordena, quem executa, quem revisa, quem pode delegar para quem, com quais capacidades, por quanto tempo, sob qual orçamento, em qual Work Run e com qual prova de qualidade.**

Ao final desta SPEC:

```text
PEDIDO / EVENTO / WORK RUN
          ↓
   ADMISSION GATE
          ↓
“precisa mesmo de mais de um agente?”
          ↓
 ┌────────┼────────────────────────────────┐
 │        │                │               │
SINGLE  SPECIALIST    PARALLEL GROUP   WORKFLOW
AGENT   BOUNDED        2–5 workers     DETERMINISTIC
 │        │                │               │
 └────────┴────────────┬───┴───────────────┘
                      ↓
               LEAD / ORCHESTRATOR
                      ↓
             RESULT + EVIDENCE
                      ↓
              QUALITY GATE
                      ↓
              ENTREGA / AÇÃO
```

---

# 0.1 DECISÃO DE ARQUITETURA

A 088 **NÃO instala**:

- DeepSeek Harness;
- Ruflo;
- DeepAgents;
- OpenAI Agents SDK;
- Claude Agent Teams;
- Hermes;
- GrokBot;
- outro supervisor framework;
- outro runtime de Agents.

Ela absorve os melhores padrões deles e os implementa **dentro do Work OS já canônico**.

A regra continua:

> **AutoBrokers absorve padrões; Smith continua sendo o único runtime cognitivo.**

---

# 0.2 A RESPOSTA DEFINITIVA: AUXILIAR É SUBAGENTE?

# NÃO.

A ontologia canônica continua:

```text
AGENT / SUBAGENT
= executor cognitivo

SKILL
= procedimento

TOOL
= capacidade executável

WORKFLOW
= coordenação de etapas

ROTINA
= gatilho

WORK RUN
= execução

AUXILIAR
= PRODUTO instalado/configurado para uma corretora
```

Um Auxiliar pode usar:

```text
0 agentes
1 agente
vários subagentes
workflow determinístico
Skill
tools
rotinas
ou combinação
```

Exemplo:

```text
AUXILIAR “PANORAMA DA CORRETORA”
        │
        ├─ Skill: analisar produção
        ├─ Skill: analisar comissões
        ├─ Skill: analisar renovações
        │
        ├─ Agent Group:
        │    Comercial
        │    Financeiro
        │    Renovação
        │    Operações
        │    Reviewer
        │
        └─ Artifact: relatório executivo
```

O usuário compra o Auxiliar.

Os agents são infraestrutura interna.

---

# 0.3 O QUE ESTA SPEC NÃO DEVE VIRAR

Não transformar a 088 em:

- “criar 40 personagens”;
- marketplace de agentes;
- cada agente com prompt gigante próprio;
- cada Auxiliar com um Smith próprio;
- swarm mesh/ring/gossip/quorum;
- peer-to-peer sem autoridade central;
- cada serviço determinístico renomeado para Agent;
- chat entre agentes como fonte de verdade;
- memória pessoal irrestrita por agente;
- workflow escondido dentro do prompt;
- mais uma tabela de execução concorrente com `work_runs`;
- mais um Tool Gateway;
- nova UI bonita sem runtime real.

---

# 1. POR QUE ESTA SPEC EXISTE

## 1.1 O rascunho original estava certo sobre a dor

O rascunho da futura 088 dizia:

> “Está muito confuso para mim.”

e propunha:

> agrupar por propósito, cada grupo com sua página, fluxo e explicação.

A dor permanece legítima.

## 1.2 A implementação atual é um monitor, não uma organização

A página atual da Central mostra cards com:

```text
espelho
vigia_sentinela
followup
garimpo
auditor
alfaiate
sugestoes
cartografo
cerebro
```

e calcula basicamente:

```text
último pulso
ações no dia
health por tempo
blocos de “memória”
```

Isso responde:

> “está vivo?”

Não responde:

- isso é Agent ou serviço?
- qual missão?
- qual input/output?
- quando deve rodar?
- quem pode chamá-lo?
- para quem pode delegar?
- qual Skill usa?
- quais tools pode receber?
- qual orçamento?
- qual risco?
- qual Work Run está executando?
- por que existe?
- está entregando qualidade?
- está economizando ou queimando tokens?
- está duplicando outro componente?

## 1.3 O runtime antigo de SubAgent também envelheceu

O `SubAgentTool` atual nasceu antes da arquitetura Work OS madura.

Ele:

- carrega `agent_delegations`;
- inicia um ReAct efêmero;
- possui timeout/max iterations;
- usa contexto separado;
- registra custo/log;
- devolve resultado ao orquestrador.

Essas ideias são boas.

Porém ele ainda monta diretamente:

- Knowledge Base;
- Filesystem;
- Web Search;
- MCP;
- HTTP Router;
- CSV Analytics.

Isso é uma segunda superfície de montagem de tools.

A SPEC-056 já determinou que:

```text
Skill
↓
Capability Pack
↓
Tool Gateway
```

deve governar a exposição e execução.

A 088 fecha essa dívida.

---

# 2. PRINCÍPIO CENTRAL

> ## MAIS AGENTES NÃO SIGNIFICA MAIS INTELIGÊNCIA.

A unidade de otimização é:

```text
VALOR DO OUTCOME
−
CUSTO
−
LATÊNCIA
−
COORDENAÇÃO
−
RISCO
```

A pergunta antes de delegar é:

> **Existe trabalho realmente separável que fica melhor, mais rápido ou mais confiável em outro contexto especializado?**

Se não:

```text
SINGLE AGENT
```

vence.

---

# 3. AS CINCO FORMAS DE EXECUÇÃO

A 088 cria uma escolha explícita.

## 3.1 SINGLE_AGENT

Um Agent/Smith resolve.

Usar quando:

- problema simples;
- mesmo contexto;
- poucas tools;
- baixa amplitude;
- baixa necessidade de revisão independente;
- latência importa.

Exemplos:

- consultar uma apólice;
- explicar uma cobrança;
- buscar dado pontual;
- responder pergunta simples de carteira.

## 3.2 BOUNDED_SPECIALIST

Lead chama um especialista e recebe de volta um resultado estruturado.

É o padrão equivalente a:

```text
“agent as tool”
```

Lead continua dono do outcome e da resposta final.

Usar quando:

- tarefa é especializada;
- pode ser explicada em um envelope;
- resultado importa mais que a trajetória;
- não precisa falar diretamente com usuário.

Este será o padrão multi-agent DEFAULT.

## 3.3 PARALLEL_GROUP

Lead distribui tarefas independentes.

```text
                LEAD
       ┌─────────┼─────────┐
       ↓         ↓         ↓
   worker A  worker B  worker C
       └─────────┼─────────┘
                 ↓
             SYNTHESIS
```

Usar somente quando há paralelismo real.

## 3.4 DETERMINISTIC_WORKFLOW

Quando dependências são conhecidas:

```text
A
↓
B
↓
C
```

código/Work Run governa.

Não pedir a uma LLM para “descobrir” todo turno uma sequência que já conhecemos.

## 3.5 OWNERSHIP_HANDOFF

Troca de agente ativo.

Uso raro.

Exige motivo explícito.

Para interação humana, a Candidate SPEC-086 é soberana.

Para agents:

- só usar quando o especialista realmente precisa assumir a superfície;
- não usar como modo padrão de subtask.

---

# 4. A REGRA DE OURO DE ORQUESTRAÇÃO

```text
DETERMINÍSTICO ONDE SABEMOS A ORDEM
LLM ONDE PRECISAMOS DE JULGAMENTO
SUBAGENT ONDE PRECISAMOS DE ISOLAMENTO/ESPECIALIDADE
PARALELO ONDE AS TAREFAS SÃO INDEPENDENTES
HUMANO ONDE A AUTORIDADE É HUMANA
```

---

# 5. AGENT CENSUS — PRIMEIRO ARRUMAR A ONTOLOGIA

Antes de criar qualquer papel novo, classificar tudo que hoje aparece como “agente”.

`component_kind` conceitual:

```text
COGNITIVE_AGENT
COGNITIVE_SUBAGENT
DETERMINISTIC_SERVICE
WATCHER
WORKFLOW
SCHEDULER
AUXILIARY
ROUTINE
QUALITY_JUDGE
UI_ALIAS
```

Exemplo a CONFIRMAR, não assumir:

```text
Espelho        → serviço/observador?
Cartógrafo     → serviço determinístico?
Sentinela      → watcher?
Vigia          → watcher/workflow?
Cérebro        → agent?
Auditor        → judge/service?
Alfaiate       → proposer/compiler?
Follow-up      → policy/workflow/Auxiliar?
```

O warm-up decide por código real.

> **Não criar LLM onde um serviço determinístico já faz melhor.**

---

# 6. OS QUATRO GRUPOS DA CENTRAL

A UI e a organização lógica passam a usar quatro macrogrupos.

## GRUPO 1 — OBSERVA & REGISTRA

Missão:

> perceber fatos sem decidir negócio além do necessário.

Pode conter:

- Espelho;
- observadores;
- Cartógrafo;
- profilers;
- collectors;
- capture agents/services.

Predominantemente determinístico.

## GRUPO 2 — PLANEJA & ORQUESTRA

Missão:

> entender outcome, dividir trabalho e governar execução.

Pode conter:

- AutoBrokers/Core;
- planners;
- research lead;
- Work OS orchestrator.

## GRUPO 3 — EXECUTA & ACOMPANHA

Missão:

> executar trabalho especializado.

Pode conter:

- Atendimento;
- specialist agents;
- Auxiliares em execução;
- workflows;
- portal operators;
- research workers.

## GRUPO 4 — REVISA & MELHORA

Missão:

> detectar erro, avaliar, propor melhoria e impedir regressão.

Pode conter:

- Auditor;
- judges;
- Vigia/Sentinela;
- Route Self-Healing components;
- evaluator;
- future MetaHarness consumers.

Não confundir “revisar” com “publicar verdade”.

---

# 7. CENTRAL ≠ RUNTIME

A Central de Agentes é:

```text
CONTROL + OBSERVABILITY SURFACE
```

sobre fontes canônicas.

Não é:

```text
novo scheduler
novo agent loop
novo worker
```

Ela lê:

- Agents;
- Skills;
- Capability Packs;
- Work Runs;
- delegations;
- Work Events;
- usage;
- evals;
- health;
- Agent Assignments;
- group plans.

---

# 8. AGENT ROLE SPEC

Precisamos separar:

```text
“quem é o especialista”
```

de:

```text
“uma execução daquele especialista”
```

Contrato conceitual:

```json
{
  "role_key": "analysis.commercial",
  "version": "1.0.0",
  "display_name": "Analista Comercial",
  "component_kind": "COGNITIVE_SUBAGENT",

  "mission": "...",
  "use_when": [],
  "do_not_use_when": [],

  "input_schema_ref": "...",
  "output_schema_ref": "...",

  "skills": [],
  "capability_pack_refs": [],

  "risk_ceiling": "medium",
  "may_delegate": false,

  "default_model_class": "balanced",
  "default_effort": "medium",

  "limits": {
    "max_turns": 5,
    "timeout_seconds": 60
  },

  "quality_profile": "standard"
}
```

## 8.1 Não criar `agent_registry_v2`

O warm-up deve decidir se isso:

- evolui `agents`;
- usa Skill/Workflow releases;
- cria apenas release/version para papéis.

A 088 define contrato.

Não decreta tabela nova sem medir.

---

# 9. AGENT ROLE RELEASES

Papéis comportamentais em produção precisam ser versionáveis.

Uma mudança em:

- mission;
- tool scope;
- output contract;
- model policy;
- max turns;
- delegation;
- judge policy;

é mudança de comportamento.

Preferência:

```text
immutable release
+
active pointer
```

não editar “prompt do agente” e perder história.

Se SPEC-056/Agents já fornecer release equivalente:

reusar.

---

# 10. DELEGATION CONTRACT

`agent_delegations` hoje carrega essencialmente:

```text
orchestrator_id
subagent_id
task_description
max_context_chars
timeout
max_iterations
```

A 088 precisa evoluir o conceito para um contrato governado.

Campos conceituais:

```text
parent_role
child_role
allowed_work_types
allowed_skill_refs
allowed_capability_packs
context_policy
output_schema
budget_policy
timeout
turn_limit
depth_limit
parallel_limit
risk_ceiling
judge_policy
escalation_policy
```

---

# 11. NENHUMA ESCALADA DE PRIVILÉGIO

Capacidades efetivas do child:

```text
PARENT EFFECTIVE CAPABILITIES
∩
DELEGATION POLICY
∩
CHILD ROLE ALLOWLIST
∩
WORK/SKILL CAPABILITY PACK
∩
TENANT ENTITLEMENTS
∩
CONNECTED PROVIDERS
∩
CURRENT PHASE POLICY
```

O resultado é sempre uma INTERSEÇÃO.

Nunca união.

---

# 12. SUBAGENT TOOL NÃO MONTA MAIS TOOLS POR CONTA PRÓPRIA

Alvo de cutover:

```text
OLD

SubAgentTool
├─ KnowledgeBaseTool
├─ WebSearchTool
├─ MCPToolFactory
├─ HttpToolRouter
└─ CSVAnalytics
```

vira:

```text
NEW

Delegation Gateway
↓
resolve Skill / work context
↓
Capability Pack
↓
Tool Gateway
↓
effective child toolset
↓
Subagent Executor
```

A mesma autorização é revalidada no momento da chamada.

---

# 13. VISIBILIDADE = AUTORIDADE

Não basta:

> “não mostrar a tool no prompt”.

Também precisa:

```text
tool não aparece
+
tool não executa se chamada por caminho stale/malicioso
```

Hard gate.

---

# 14. DELEGATION ENVELOPE

O especialista NÃO recebe a conversa inteira por padrão.

Recebe um contrato de trabalho.

```json
{
  "delegation_id": "...",
  "root_run_id": "...",
  "parent_run_id": "...",
  "parent_step_id": "...",

  "mission": "Comparar produção por vendedor",
  "objective": "...",

  "success_criteria": [],
  "expected_output_schema": "...",

  "input_refs": [],
  "facts": [],
  "context_refs": [],

  "allowed_capability_pack": "...",
  "forbidden_actions": [],

  "evidence_requirements": [],

  "budget": {
    "tokens": null,
    "cost": null,
    "deadline": null
  },

  "depth": 1
}
```

---

# 15. O DELEGATION ENVELOPE DEVE SER COMPLETO

A Anthropic encontrou um problema clássico:

```text
“pesquise semicondutores”
```

é vago demais.

Nosso contrato exige:

```text
OBJETIVO
+
ESCOPO
+
O QUE NÃO FAZER
+
FONTES/PODERES
+
FORMATO
+
CRITÉRIO DE SUCESSO
```

Isso reduz:

- workers duplicados;
- lacunas;
- exploração sem fim;
- outputs impossíveis de sintetizar.

---

# 16. CONTEXT POLICY

Cada child começa com contexto LIMPO.

Padrão:

```text
fresh
```

Não:

```text
fork full conversation
```

sem necessidade.

`context_policy`:

```text
FRESH_MINIMAL
FRESH_WITH_REFERENCES
FORK_SUMMARY
FULL_FORK    # excepcional
```

---

# 17. CONTEXT OFFLOADING

Conteúdo volumoso:

- documentos;
- resultados de pesquisa;
- planilhas;
- traces;
- artifacts;

é passado por:

```text
stable ref / artifact ref / source ref
```

em vez de colar 80 mil tokens no prompt de cada worker.

---

# 18. AGENT RESULT ENVELOPE

O child retorna resultado estruturado.

```json
{
  "status": "succeeded",
  "summary": "...",
  "structured_result": {},
  "artifact_refs": [],
  "evidence_refs": [],
  "claims": [],
  "blockers": [],
  "confidence": 0.87,

  "tools_used": [],
  "cost": {},
  "latency_ms": 0,

  "recommended_next_action": null
}
```

O Lead recebe a síntese.

Logs detalhados permanecem na observabilidade.

---

# 19. RESULTADO DO CHILD NÃO É VERDADE AUTOMÁTICA

Especialista pode:

- errar;
- alucinar;
- interpretar mal.

O Lead:

- valida schema;
- valida evidence;
- aplica quality plan;
- decide se precisa reviewer;
- jamais transforma texto do child diretamente em ação sensível sem gates.

---

# 20. EXECUTION MODES

## MODE A — INLINE SPECIALIST

Curto.

```text
parent Work Run / step
↓
subagent efêmero
↓
resultado
```

Sem child Work Run se:

- execução curta;
- não precisa sobreviver restart;
- não tem side effect;
- baixo custo/risco.

É o sucessor governado do `SubAgentTool` atual.

## MODE B — DURABLE SPECIALIST

Longo ou assíncrono.

```text
root Work Run
↓
child Work Run
↓
agent assignment
↓
resultado/artifact
↓
parent continua
```

Obrigatório quando:

- pode passar do request;
- pode esperar;
- tem múltiplos steps;
- precisa approval;
- side effects;
- retry;
- background;
- custo relevante.

## MODE C — PARALLEL GROUP

2–5 children independentes.

## MODE D — REVIEW GROUP

workers geram resultado.

reviewer(s) avaliam independentemente.

## MODE E — DETERMINISTIC PIPELINE

Work OS governa sequência.

Agents entram somente nos steps cognitivos.

---

# 21. WORK RUN LINEAGE

A 088 precisa permitir visualizar:

```text
ROOT RUN
├─ STEP
│  ├─ CHILD RUN A
│  ├─ CHILD RUN B
│  └─ CHILD RUN C
└─ REVIEW RUN
```

Campos conceituais, se ainda não existirem:

```text
root_work_run_id
parent_work_run_id
parent_work_step_id
delegation_id
agent_assignment_id
```

Preferir expand-only.

Não criar `agent_runs`.

---

# 22. AGENT ASSIGNMENT

Uma invocação concreta.

```text
agent_assignment_id
work_run_id
role_release_id
delegation_id
company_id
status
started_at
finished_at
model_actual
capability_pack_actual
cost
tokens
```

Pode ser:

- tabela mínima;
- ou projeção derivada de Work Steps/Events se suficiente.

Warm-up decide.

---

# 23. ADMISSION GATE — PRECISA MESMO DE MULTI-AGENT?

Antes de delegar, classificar o trabalho.

Inputs:

```text
breadth
independence
shared_context_dependency
risk
tool diversity
expected context volume
expected value
latency sensitivity
quality requirement
```

Output:

```text
SINGLE_AGENT
BOUNDED_SPECIALIST
PARALLEL_GROUP
DETERMINISTIC_WORKFLOW
HUMAN
```

---

# 24. PRINCÍPIO DE ECONOMIA

Anthropic mediu que sistemas multi-agent podem consumir muitas vezes mais tokens que chat simples.

Portanto:

> **o modelo nunca ganha um cheque em branco para “montar uma equipe”.**

Há:

- hard concurrency cap;
- budget;
- depth;
- task count;
- stop conditions.

---

# 25. LIMITES DEFAULT AUTOBROKERS

Proposta inicial, sujeita a warm-up/evals.

## Operação de negócio

```text
delegation_depth_default = 1
parallel_workers_default = 2
parallel_workers_max     = 3
```

## Research / relatório complexo

```text
delegation_depth_default = 1
parallel_workers_default = 3
parallel_workers_max     = 5
```

## AAA / investigação excepcional

```text
max = 5
```

Mais de 5:

```text
não pode ser decisão livre do modelo.
```

Exige profile explícito/configuração administrativa.

---

# 26. PROFUNDIDADE

Default:

```text
Lead
↓
Worker
```

Worker não delega.

Depth 2 somente para patterns aprovados.

Exemplo:

```text
Research Lead
↓
Research Specialist
↓
Source Verifier
```

Nunca recursion aberta.

---

# 27. POR QUE NÃO COPIAR “20 SUBAGENTS”

Claude Code e outros harnesses podem suportar números altos.

Isso é limite técnico de produto genérico.

Não é recomendação econômica para corretoras.

AutoBrokers trabalha com:

- PII;
- actions;
- insurance operations;
- custo SaaS;
- latência para usuário.

Portanto limites são menores e orientados a outcome.

---

# 28. PARALLELISM GATE

Tasks podem rodar juntas somente se:

```text
não dependem do output uma da outra
+
não escrevem no mesmo recurso
+
não disputam o mesmo side effect
+
não precisam de contexto que o outro está produzindo
```

Caso contrário:

workflow.

---

# 29. GROUP PLAN

Quando paralelo for escolhido, produzir plano estruturado.

```json
{
  "group_plan_id": "...",
  "lead_role": "...",
  "objective": "...",
  "workers": [
    {
      "role": "analysis.commercial",
      "mission": "...",
      "dependencies": []
    }
  ],
  "synthesis": {},
  "quality_plan": {},
  "budget": {}
}
```

---

# 30. AGENT GROUP TEMPLATE

Um padrão reutilizável de composição.

Não é Auxiliar.

Exemplos:

```text
executive_brokerage_review@1
research_deep@1
artifact_quality_review@1
```

Pode ser referenciado por:

- Skill;
- workflow;
- Auxiliar;
- Core.

---

# 31. TEMPLATE GLOBAL, EXECUÇÃO TENANT-SCOPED

Definição de group pattern pode ser global.

Run é sempre:

```text
company_id scoped
```

Contexto, tools e connections são resolvidos por tenant no instante da execução.

---

# 32. NÃO CRIAR MARKETPLACE NA 088

A galeria/marketplace de Auxiliares pertence à Factory/roadmap posterior.

A 088 cria infraestrutura de execução.

Não expor:

> “escolha 15 agents”.

Corretor escolhe:

- outcome;
- Auxiliar;
- trabalho.

---

# 33. GRUPOS INICIAIS ÚTEIS

Não seedar dezenas.

Implementar 2–3 patterns que provem a arquitetura.

## 33.1 EXECUTIVE BROKERAGE REVIEW

Boa prova porque o domínio possui áreas separáveis.

```text
Lead Executivo
├─ Comercial
├─ Carteira/Comissões
├─ Renovações
└─ Operações/Atendimento
        ↓
Synthesizer
        ↓
Executive Reviewer
        ↓
Artifact
```

Usar somente dados realmente disponíveis.

Não implementar o relatório InfoCap completo nesta SPEC.

O objetivo é provar a coordenação.

## 33.2 DEEP RESEARCH

```text
Research Lead
├─ fontes oficiais
├─ notícias/mercado
└─ discussões/competição
↓
Evidence Verifier
↓
Synthesis
```

Reusar Research Intelligence.

## 33.3 QUALITY REVIEW

```text
Artifact / analysis
↓
Reviewer
↓
verdict + defects + evidence
```

---

# 34. QUANDO NÃO USAR AGENT GROUP

Explicitamente proibido por default em:

- lookup de apólice;
- simples pergunta de atendimento;
- roteamento básico;
- acionamento em corredor determinístico;
- envio de mensagem;
- cálculo simples;
- execução onde todos precisam do mesmo contexto a cada passo.

---

# 35. LEAD / MANAGER É O DONO DO OUTCOME

Padrão default:

> **o especialista não fala diretamente com o usuário.**

O Lead:

- recebe pedido;
- decide decomposição;
- manda envelope;
- reúne resultados;
- valida;
- sintetiza;
- responde.

Isso preserva:

- voz AutoBrokers;
- policy;
- contexto;
- guardrails;
- experiência.

---

# 36. AGENT HANDOFF É EXCEÇÃO

Handoff cognitivo direto só quando:

- experiência exige que especialista assuma;
- prompt/policy precisa mudar radicalmente;
- Lead não agrega valor como sintetizador.

Handoff humano segue SPEC-086.

Nenhum agent-to-agent handoff substitui approval humano.

---

# 37. PEER-TO-PEER AGENT TEAMS

A 088 NÃO implementa peer messaging livre como default.

Razão:

- coordination overhead;
- conflitos;
- autoridade difusa;
- mais tokens;
- mais difícil auditar.

Pode existir FUTURAMENTE como pattern explícito para pesquisa colaborativa.

Nesta SPEC:

```text
centralized orchestrator-worker
```

é autoridade.

---

# 38. DEEPSEEK HARNESS — O QUE ABSORVER

O DeepSeek Harness atual usa “everything is a plugin” e define capability seams substituíveis.

Insights úteis:

## 38.1 Subagent é capability, não parte inevitável do loop

Muito alinhado.

AutoBrokers:

```text
delegation
```

é uma capability do Work OS.

Não toda execução.

## 38.2 Fail loud on unsupported capability

DeepSeek valida antes de iniciar se provider suporta:

- output schema;
- depth;
- tool filter;
- persona.

AutoBrokers deve fazer o mesmo.

Se child precisa `tool_filter` e executor não consegue garantir:

```text
DELEGATION_REJECTED
```

Não aceitar e ignorar.

## 38.3 Continuable children

DeepSeek separa one-shot de child continuável.

AutoBrokers já tem Work Runs.

Modelar:

```text
inline specialist
vs
durable specialist
```

sem instalar o harness.

## 38.4 Tool filtering

O child precisa receber tool scope menor.

Já é princípio canônico da SPEC-056.

## 38.5 Team task DAG

A ideia de:

```text
task
blockedBy
owner
revision/CAS
```

é boa.

Mas AutoBrokers já possui Work Runs/Steps.

Não criar `TeamTask` paralelo.

Mapear dependencies para Work Steps/Group Plan.

---

# 39. CLAUDE SUBAGENTS — O QUE ABSORVER

Padrões:

- contexto isolado;
- descrição clara de quando usar;
- tool allowlist/denylist;
- modelo por papel;
- max turns;
- skills;
- background;
- isolation;
- fresh context.

AutoBrokers traduz para:

```text
Agent Role Spec
Delegation Policy
Capability Pack
Work Run
```

---

# 40. CLAUDE AGENT TEAMS — O QUE ABSORVER

Padrões úteis:

- lead;
- workers independentes;
- task list;
- dependencies;
- 3–5 como faixa prática para trabalho paralelo;
- reconhecer coordination overhead;
- começar por research/review.

Não copiar:

- peer messaging como default;
- shared checkout;
- team runtime experimental.

---

# 41. OPENAI — MANAGER VS HANDOFF

A distinção é incorporada:

## Manager / agent-as-tool

DEFAULT AutoBrokers.

```text
Core/Lead mantém controle
↓
specialist retorna bounded result
```

## Handoff

EXCEÇÃO.

```text
especialista assume interação
```

---

# 42. LANGCHAIN / DEEPAGENTS — O QUE ABSORVER

Padrões:

- subagent como tool;
- fresh isolated context;
- parallel calls quando independentes;
- structured response;
- separate context from parent;
- long-running/background child quando necessário.

Não instalar DeepAgents.

Smith já é LangGraph.

---

# 43. RUFLO — O QUE ABSORVER NA 088

Somente ideias que acrescentam.

## 43.1 Hierarchical coordination

Sim.

## 43.2 Agent health/score

Parcial.

Central deve mostrar:

- qualidade;
- custo;
- falhas;
- drift;
- não só heartbeat.

## 43.3 6–8 agents como recomendação genérica

NÃO copiar.

AutoBrokers começa menor.

## 43.4 mesh/ring/quorum/gossip

NÃO.

## 43.5 workflow primitives

A ideia de:

```text
parallel
pipeline
barrier
review
```

é boa.

Implementar sobre Work OS/LangGraph.

---

# 44. QUALITY PLAN

Todo Work Pattern pode declarar:

```text
STANDARD
HIGH
AAA
```

Não confundir com a certificação de rotas da SPEC-089.

Aqui é “esforço de revisão”.

---

# 45. STANDARD

```text
executor
+
deterministic checks
```

Uso:

trabalho comum.

---

# 46. HIGH

```text
executor
+
independent reviewer
+
structured verdict
```

Uso:

- relatório executivo;
- análise financeira;
- decisão importante;
- artifact externo.

---

# 47. AAA EXECUTION PROFILE

Somente tarefas de alto valor/risco que justificam custo.

Possível pattern:

```text
PLAN
↓
EXECUTOR(S)
↓
INDEPENDENT REVIEWER
↓
CRITICAL JUDGE
↓
SYNTHESIS / REPAIR
↓
FINAL GATE
```

Não executar três juízes em toda pergunta de chat.

---

# 48. JUDGE É PAPEL DIFERENTE DE WORKER

Judge:

- não corrige silenciosamente o próprio objeto;
- recebe artifact/result/evidence;
- não recebe chain-of-thought do worker;
- preferencialmente independente;
- não recebe side-effect tools;
- produz verdict estruturado.

---

# 49. JUDGE OUTPUT

```json
{
  "verdict": "PASS|FAIL|NEEDS_REPAIR",
  "score": 0,
  "blocking_findings": [],
  "non_blocking_findings": [],
  "evidence_refs": [],
  "repair_instructions": []
}
```

Score é diagnóstico.

Blocker é não compensável conforme quality profile.

---

# 50. JUDGE NÃO LIBERA AÇÃO HUMANA

Um Judge Agent pode dizer:

```text
PASS
```

Mas se a policy exige approval humano:

continua exigindo humano.

Agent jamais relaya consentimento.

---

# 51. REVIEW LOOP COM TETO

Proibido:

```text
worker ↔ judge
até ficarem felizes para sempre
```

Default:

```text
max_repair_rounds = 1
```

Profile excepcional:

```text
2
```

Depois:

- deliver with warning;
- human;
- fail.

Nunca loop infinito.

---

# 52. MODEL ROUTING POR PAPEL

Papel pode declarar classe, não provider hardcoded.

```text
fast
balanced
strong
vision
reasoning
```

Model Router escolhe provider/model disponível.

Evita amarrar:

```text
“Analista = Claude para sempre”
```

---

# 53. EFFORT BUDGET

Role/Group pode declarar:

```text
low
medium
high
critical
```

Isso influencia:

- model class;
- token budget;
- number of workers;
- reviewers;
- max turns.

---

# 54. COST BUDGET

O Group Plan estima antes:

```text
expected agents
expected model class
expected max turns
expected tool costs
```

Se ultrapassar budget tenant/platform:

- reduzir plan;
- pedir approval;
- usar single agent;
- não iniciar.

---

# 55. STOP CONDITIONS

Todo worker sabe quando parar.

Exemplos:

```text
success criteria satisfied
source count reached
evidence sufficient
budget exhausted
timeout
no new information
blocked
```

“Pesquisar mais” não é condição.

---

# 56. CANCELLATION

Cancelar root Work Run:

- impede novas delegações;
- sinaliza children;
- não interrompe side effect no meio;
- children cooperam;
- Work OS registra.

Nenhum child órfão continua queimando tokens.

---

# 57. BACKPRESSURE

Global e por tenant:

```text
max active specialist runs
max group fanout
max token budget
max provider concurrency
```

Não deixar 10 usuários dispararem 50 subagents cada.

---

# 58. AGENT COMMUNICATION

V1:

```text
worker → lead
```

Não:

```text
worker A ↔ worker B livre
```

Quando B precisa do output de A:

isso é dependência do Group Plan/Workflow.

---

# 59. PROVENANCE

Toda mensagem/result entre agents carrega:

```text
sender_assignment_id
receiver
work_run
source type
timestamp
```

Mas conteúdo vindo de outro agent continua não confiável até policy/validation.

---

# 60. AGENT MEMORY — NÃO CRIAR NOVA VERDADE

A Central atual mostra “memória do agente”.

A 088 precisa classificar isso.

Tipos permitidos:

```text
WORKING_STATE
ROLE_HINTS
CURATED_KNOWLEDGE_REFS
LEARNING_SIGNAL
```

Não:

```text
agente escreve regra de seguradora e passa a acreditar para sempre
```

---

# 61. MEMÓRIA GLOBAL / CORRETORA / USUÁRIO CONTINUA SOBERANA

Agents acessam memória conforme:

```text
context policy
+
tenant
+
user
+
role
+
Skill
```

Não possuem uma quarta verdade paralela chamada “memória do agente”.

---

# 62. LEARNING

Após uma execução, Agent pode gerar:

```text
Learning Signal
```

Não publica:

- Skill;
- memória global;
- regra;
- route;
- knowledge card.

Dreams/Factories posteriores decidem.

---

# 63. OBSERVABILIDADE — CORRELATION IDS

Toda delegação:

```text
trace_id
root_run_id
run_id
parent_run_id
step_id
delegation_id
assignment_id
agent_role
agent_role_release
tool_call_id
```

Isso prepara MetaHarness futuro.

---

# 64. HEALTH — HEARTBEAT NÃO É QUALIDADE

Separar:

## Runtime Health

- último pulso;
- erro;
- timeout;
- disponibilidade.

## Outcome Health

- success rate;
- task completion;
- blocker rate.

## Quality Health

- judge pass rate;
- eval pass rate;
- repair rate.

## Efficiency Health

- custo;
- tokens;
- latência;
- delegation overhead.

## Safety Health

- denied tools;
- approval violations;
- cross-tenant attempts;
- stale capability calls.

---

# 65. CENTRAL — NOVA HOME

A home deixa de mostrar apenas cards.

Topo:

```text
CENTRAL DE AGENTES

Saúde da organização
• 4 grupos
• X componentes ativos
• Y Work Runs com agents
• Z precisam de atenção

Hoje
• trabalhos concluídos
• custo
• taxa de sucesso
• delegações
• revisões
```

---

# 66. CENTRAL — GRUPOS

Quatro cards principais:

```text
OBSERVA & REGISTRA
PLANEJA & ORQUESTRA
EXECUTA & ACOMPANHA
REVISA & MELHORA
```

Cada grupo abre sua página/lista.

---

# 67. CENTRAL — CARD DE COMPONENTE

Mostrar:

```text
Nome
Tipo real
Missão
Status
Última execução
Work Runs ativos
Qualidade
Custo
Delegações
Capabilities
Release
```

Exemplo:

```text
AUDITOR
QUALITY_JUDGE

Missão
Reprovar resultados que violam critérios.

Hoje
14 reviews
12 PASS
2 NEEDS_REPAIR

Poderes
read-only
0 external writes
```

---

# 68. CENTRAL — LIVE WORK

Nova visualização de Work Run multi-agent:

```text
RELATÓRIO EXECUTIVO
root run 123

Lead Executivo       ● synthesizing
├─ Comercial         ✓ done
├─ Comissões         ✓ done
├─ Renovações        ● running
└─ Operações         ✓ done

Reviewer             ○ waiting

Custo      R$ / tokens
Tempo      ...
```

Não precisa WebSocket novo se polling/event stream existente for suficiente.

---

# 69. CENTRAL — DELEGATION MAP

Admin pode ver:

```text
CORE
├─ Research Specialist
├─ Commercial Analyst
└─ Executive Reviewer
```

Com cada edge:

```text
allowed
depth
timeout
quality
capability pack
```

Mas não editar conexão arbitrária sem validação.

---

# 70. CENTRAL — POR QUE O AGENTE EXISTE?

Cada role precisa mostrar:

```text
use_when
do_not_use_when
```

Isso é fundamental para detectar agentes decorativos.

---

# 71. AGENT DUPLICATION DETECTOR

Admin diagnostic:

```text
dois roles com missão/toolset/output muito semelhantes
```

gera:

```text
POSSIBLE_DUPLICATE
```

Não faz merge automático.

---

# 72. AGENT VALUE SCORE

Não virar gamificação vazia.

Score diagnóstico opcional:

```text
Outcome Success
Quality
Cost Efficiency
Latency
Safety
Utilization
```

MetaHarness futuro aprofunda.

Na 088 pode haver apenas projection mínima.

---

# 73. SECURITY — JUDGES READ-ONLY

Default:

```text
QUALITY_JUDGE
```

não recebe:

- send;
- write CRM;
- route_publish;
- finance action;
- external effect.

Pode:

- read evidence;
- inspect artifact;
- query data read-only conforme scope;
- produce verdict.

---

# 74. SECURITY — ATTENDANCE CHILDREN

Agente de Atendimento nunca pode delegar para:

- marketing;
- admin;
- global research unrestricted;
- finance write;
- custom MCP arbitrary.

A role policy de Atendimento é fechada.

---

# 75. SECURITY — EXTERNAL CONTENT

Resultado de Web/MCP/child:

```text
UNTRUSTED CONTENT
```

antes de voltar para lead.

Preservar/usar gates de sanitização e prompt-injection existentes/futuros.

---

# 76. SECURITY — BLAST RADIUS

Cada role declara:

```text
risk_ceiling
```

Exemplo:

```text
Researcher = read_only
Executive Analyst = read_only
Operator = medium
Route Publisher = not an agent authority
```

A capability intersection garante blast radius.

---

# 77. GLOBAL / CORRETORA / USUÁRIO

Separação:

## Global

- role templates;
- group templates;
- Skill releases;
- policies plataforma.

## Corretora

- entitlements;
- connections;
- allowed groups;
- budgets;
- config de Auxiliares;
- data/memory tenant.

## Usuário

- actor identity;
- permissions;
- preferences;
- personal memory;
- approvals.

Uma role global não ganha acesso global a dados.

---

# 78. AGENT ROLE NÃO É TENANT ROW POR DEFAULT

Evitar duplicar o mesmo “Analista Comercial” 300 vezes.

Preferência:

```text
global role release
+
tenant-scoped invocation/config
```

Tenant-specific role somente se existe necessidade real e governada.

---

# 79. EXISTING `agents` TABLE

Pode misturar hoje:

- user-facing agents;
- subagents;
- configs;
- tenant rows.

A 088 deve fazer inventory antes de decidir schema.

Não deletar/migrar em massa sem mapa.

---

# 80. `agent_delegations` MIGRATION

A tabela antiga tem valor.

Preferência:

evoluir/migrar para contrato novo.

Não criar:

```text
agent_delegations_v2
```

sem blocker.

Possíveis colunas/refs:

```text
role_release refs
policy json/ref
output schema
max depth
parallel limit
risk
quality profile
```

Ou substituir o uso da tabela por edges de catálogo já existente se SPEC-056 criou algo melhor.

Warm-up decide.

---

# 81. SUBAGENT EXECUTOR

Não precisa ser LangGraph completo para one-shot curto.

Mas precisa:

- cancellation;
- timeout;
- Tool Gateway;
- typed output;
- observability;
- capability scope;
- context envelope.

Durable child:

Work Run.

---

# 82. SYNC FALLBACK

O atual SubAgentTool tem fallback com:

```text
ThreadPoolExecutor + new_event_loop
```

e o próprio código alerta para bug sob carga.

A 088 deve medir uso real.

Se async é caminho canônico:

- deprecar fallback inseguro;
- não manter dois modos “porque já existe”.

---

# 83. FAIL LOUD

Se a execução pede:

```text
structured output
tool restriction
durable child
specific model class
```

e o executor/provider não suporta:

```text
UNSUPPORTED_DELEGATION_CAPABILITY
```

Não fazer downgrade silencioso.

---

# 84. STRUCTURED OUTPUT

Para roles críticos:

JSON Schema/Pydantic.

Não:

```text
“retorne mais ou menos assim”
```

Parser failure:

- repair uma vez se profile permite;
- depois fail.

---

# 85. DELEGATION SELECTION

O Lead não recebe 30 subagent tool definitions.

Resolver progressive disclosure:

```text
Outcome
↓
Skill
↓
candidate roles
↓
2–5 relevant specialists
↓
tool exposed
```

Não encher contexto.

---

# 86. ROUTER VS SUPERVISOR

Se input tem categorias claras:

```text
deterministic/light router
```

Se precisa julgamento contínuo:

```text
Lead supervisor
```

Não usar LLM supervisor para classificar algo que enum resolve.

---

# 87. EXEMPLO — RELATÓRIO EXECUTIVO

```text
Usuário:
“Me mostre como foi a corretora este mês.”

Admission:
high-value, multi-domain, parallelizable
→ PARALLEL_GROUP

Lead
├─ Commercial
│  Input: sales refs
│  Output: commercial_findings
├─ Portfolio/Commission
├─ Renewal
└─ Service Operations

Barrier
↓
Executive Synthesis
↓
Reviewer
↓
Artifact
```

Cada worker NÃO recebe dados que não precisa.

---

# 88. EXEMPLO — APÓLICE

```text
“Qual a franquia do João?”
```

Admission:

```text
SINGLE_AGENT
```

Core:

```text
Policy Skill
→ InfoCap/document
→ Evidence
→ answer
```

Criar 4 agents aqui é regressão.

---

# 89. EXEMPLO — PESQUISA SUSEP

```text
“Analise o impacto desta nova circular.”
```

Possível:

```text
Research Lead
├─ Official Source Researcher
├─ Market Impact Researcher
└─ Insurance Operations Analyst
↓
Evidence Reviewer
↓
Synthesis
```

---

# 90. EXEMPLO — ATENDIMENTO

```text
segurado pede guincho
```

Não usar “equipe de agentes” para conversar com URA.

Padrão:

```text
Atendimento
→ corredor
→ deterministic engine
→ adaptive fallback
→ human continuity 086
```

Multi-agent somente para exception/research realmente delimitada.

---

# 91. QUALITY EVALS

Para cada group template inicial:

criar eval cases:

```text
caso em que DEVE delegar
caso em que NÃO deve
caso onde parallel ajuda
caso onde parallel atrapalha
caso de privilege escalation
caso de budget
caso de duplicate work
caso de missing context
```

---

# 92. DELEGATION EVAL

Medir:

```text
delegation precision
delegation recall
duplicate_task_rate
unnecessary_delegation_rate
missing_context_rate
result_schema_pass_rate
child_tool_denial_rate
```

---

# 93. OUTCOME EVAL

O multi-agent só fica ativo se demonstra:

```text
quality uplift
ou
latency improvement
ou
context capacity
```

suficiente para justificar custo.

Não liberar porque “pareceu inteligente”.

---

# 94. A/B / SHADOW

Para group template:

rodar inicialmente:

```text
single-agent baseline
vs
multi-agent candidate
```

mesmos eval cases.

Medir:

- qualidade;
- latência;
- tokens;
- custo;
- failure rate.

---

# 95. RELEASE GATE DO GROUP TEMPLATE

Publicar somente se:

```text
quality >= baseline
AND
safety no regression
AND
cost within policy
AND
unnecessary delegation acceptable
```

Thresholds medidos no warm-up/evals.

---

# 96. BLOCO 0 — WARM-UP / FORENSE

Antes de editar:

1. confirmar HEAD/branch;
2. verificar existência de SPEC-088 canônica;
3. ler 052/053/055/056/058;
4. ler execution reports disponíveis;
5. ler 085/report;
6. ter Candidates 086/087/089 disponíveis;
7. listar `agents` reais;
8. listar `agent_delegations`;
9. listar `is_subagent`;
10. medir quantos agents por company;
11. medir quantas delegations ativas;
12. medir uso real de `SubAgentTool`;
13. medir toolsets de children;
14. medir calls MCP/HTTP dos children;
15. verificar se Tool Gateway da 056 está ativo e onde;
16. verificar se AUTHORITY_STRICT ainda existe/está ativo;
17. mapear direct tool assembly do graph;
18. mapear direct tool assembly do SubAgentTool;
19. mapear Work Run lineage atual;
20. buscar parent/child fields;
21. mapear Central de Agentes API;
22. mapear heartbeat IDs;
23. classificar cada “agent” da Central;
24. medir memória por agent e sua autoridade;
25. medir conversation_logs de subagents;
26. medir tokens/custos;
27. medir timeout/failures;
28. medir depth real (se existe);
29. procurar loops de delegation;
30. procurar cross-tenant defenses.

---

# 97. PERGUNTAS QUE O WARM-UP PRECISA REFUTAR

## P1
“Todo card da Central representa um LLM Agent.”

Provavelmente falso.

## P2
“Subagents atuais recebem subset menor e governado pelo Tool Gateway.”

Provar.

## P3
“`max_context_chars` realmente limita contexto.”

Provar.

## P4
“SubAgentTool só roda async.”

Provar uso do sync fallback.

## P5
“Work Runs já têm parent-child lineage.”

Provar.

## P6
“SPEC-056 está 100% cutover e graph.py antigo é só compat.”

Provar.

## P7
“Memória por agent é só projection.”

Provar.

## P8
“Delegation não pode atravessar tenant.”

Provar no schema vivo e app context.

---

# 98. BLOCO A — AGENT CENSUS + ONTOLOGY CUT

Entregas:

- inventory;
- `component_kind`;
- grupos;
- owner;
- mission;
- duplicados;
- legacy labels.

Não alterar comportamento ainda.

### Gate A

Todo card da Central possui:

```text
tipo real
missão
fonte
```

---

# 99. BLOCO B — ROLE / DELEGATION CONTRACT

Implementar/evoluir:

- role spec/release;
- delegation policy;
- context policy;
- output schema;
- limits;
- risk;
- quality.

### Gate B

Invalid delegation:

```text
blocked before model call
```

---

# 100. BLOCO C — DELEGATION GATEWAY + TOOL GATEWAY CUTOVER

Migrar SubAgentTool.

Não montar MCP/HTTP/RAG arbitrariamente.

### Gate C

Mutation:

child recebe tool não autorizada.

Teste vermelho.

---

# 101. BLOCO D — INLINE SPECIALIST

Preservar benefício do ReAct efêmero.

Adicionar:

- typed envelope;
- cancellation;
- limits;
- trace;
- policy;
- context isolation.

### Gate D

Caso simples:

```text
parent → specialist → typed result
```

sem child Work Run.

---

# 102. BLOCO E — DURABLE CHILD WORK RUN

Implementar lineage/adapters.

### Gate E

Kill/restart:

child continua/recupera.

Parent sabe:

```text
running / done / failed / waiting
```

---

# 103. BLOCO F — ADMISSION + GROUP PLAN

Implementar classificação e fanout.

### Gate F

Casos:

```text
simple lookup → zero delegation
report complex → parallel group
dependent tasks → workflow, não parallel
```

---

# 104. BLOCO G — PARALLEL 2–5 + BARRIER

Implementar sobre Work OS.

### Gate G

- fanout limitado;
- cancel root cancels children cooperatively;
- barrier aguarda;
- failure policy explícita.

---

# 105. BLOCO H — REVIEWER/JUDGE

Implementar read-only quality role.

### Gate H

Judge com tool de escrita:

```text
DENIED
```

Reviewer reprova artifact defeituoso.

Controle:

artifact correto passa.

---

# 106. BLOCO I — CENTRAL UI V2

Evoluir página existente.

Não criar outro portal.

Entregas:

- group overview;
- component pages;
- Live Work;
- delegation map;
- health dimensions;
- costs;
- Work Run lineage.

---

# 107. BLOCO J — INITIAL GROUP TEMPLATES + EVALS

Implementar:

1. Executive Brokerage Review;
2. Deep Research;
3. Quality Review.

Somente se fontes/capabilities já existirem.

Não inventar dados.

---

# 108. BLOCO K — SHADOW / CANARY / CUTOVER

Comparar:

```text
single
vs
multi
```

Ativar por pattern.

---

# 109. FAILURE POLICY DO GROUP

Worker falhou.

Opções declaradas:

```text
FAIL_GROUP
CONTINUE_PARTIAL
RETRY_WORKER
FALLBACK_SINGLE
HUMAN
```

Nunca LLM decide pós-fato sem policy.

---

# 110. PARTIAL RESULT

Se report executivo tem 4 análises e uma falha:

Lead precisa saber se:

- pode entregar com aviso;
- precisa tentar novamente;
- deve falhar.

Group template declara.

---

# 111. TIMEOUT

Timeout child não vira:

> “não encontrei nada”.

Vira:

```text
TIMEOUT
```

Explicitamente.

---

# 112. MODEL FAILURE

Provider caiu:

Model Router pode usar fallback permitido.

Mas:

- role capabilities iguais;
- same output schema;
- same risk policy.

---

# 113. TOOL FAILURE

Tool failure:

- child reporta blocker;
- não inventa dado;
- Lead não interpreta empty como zero.

---

# 114. DUPLICATE WORK

Group Plan precisa atribuir boundaries.

Eval detecta overlap.

Workers repetindo a mesma pesquisa:

métrica:

```text
duplicate_task_rate
```

---

# 115. SECURITY TEST MATRIX

| Teste | Obrigatório |
|---|---:|
| child > parent capability | bloqueado |
| child wrong tenant | bloqueado |
| child direct MCP stale | bloqueado |
| judge write | bloqueado |
| depth overflow | bloqueado |
| fanout overflow | bloqueado |
| budget overflow | bloqueado |
| agent message as human approval | bloqueado |
| output schema invalid | fail/repair |
| cancellation | comprovado |
| stale role release | bloqueado/re-resolve |
| secret in envelope | bloqueado/redacted |

---

# 116. CONCURRENCY TEST MATRIX

- 2 children;
- 3 children;
- max configured;
- max+1 rejected;
- child timeout;
- parent cancel;
- two parents same specialist;
- provider rate limit;
- restart durable child;
- barrier partial failure.

---

# 117. CONTEXT TEST MATRIX

- fresh context não contém full parent history;
- required fact chega;
- forbidden PII não chega;
- artifact ref resolvível;
- max context enforced;
- sibling não vê sibling private context;
- judge vê evidence necessária, não hidden reasoning.

---

# 118. QUALITY TEST MATRIX

- unnecessary delegation;
- correct delegation;
- wrong specialist;
- duplicate workers;
- insufficient output;
- hallucinated claim without evidence;
- reviewer catches;
- reviewer false positive control;
- repair loop capped.

---

# 119. MUTATIONS OBRIGATÓRIAS

## M1
Trocar capability intersection por union.

Tem de ficar vermelho.

## M2
Child monta HttpToolRouter diretamente.

Vermelho.

## M3
Remover max depth.

Recursive case vermelho.

## M4
Remover fanout cap.

Vermelho.

## M5
Judge ganha write capability.

Vermelho.

## M6
Simple lookup passa a spawnar 3 workers.

Admission eval vermelho.

## M7
Output schema ignorado.

Vermelho.

## M8
Agent PASS substitui human approval.

Vermelho.

## M9
Parent cancel não chega a child.

Vermelho.

## M10
Cross-tenant delegation.

Vermelho.

---

# 120. RED TEAM

Missão:

> **transformar multi-agent em escalada de poder, explosão de custo ou teatro de complexidade sem os testes perceberem.**

Ataques:

- spawn loop;
- worker delega worker delega worker;
- 30 specialists;
- repeated duplicate research;
- child asks generic MCP;
- stale delegation row;
- direct HTTP legacy;
- prompt injection pede privilege;
- reviewer executa action;
- child returns fake approval;
- child reads tenant B;
- parent sends entire conversation;
- PII duplication;
- invalid JSON treated as success;
- timeout treated as empty result;
- peer message used as evidence;
- same role duplicated under two names;
- deterministic service reimplemented as LLM.

---

# 121. PERFORMANCE

Medir:

```text
time_to_first_token
total latency
parallel wall clock
single baseline
tokens
cost
tool calls
```

Multi-agent que melhora qualidade 1% e triplica latência em atendimento simples não passa.

---

# 122. COST ATTRIBUTION

Custo deve ser atribuível a:

```text
tenant
root work run
child run
role
group template
skill
model
tool
```

---

# 123. NO TOKEN SURPRISE

Antes de high-cost group:

policy pode exigir:

```text
budget approval
```

conforme tenant/config.

---

# 124. FEATURE FLAGS

Mínimo:

```text
AGENT_ORG_V2_ENABLED
GOVERNED_DELEGATION_ENABLED
DURABLE_CHILD_RUNS_ENABLED
AGENT_GROUPS_ENABLED
```

Não flag por papel.

---

# 125. ROLLOUT

## Phase 0 — Census only

UI classifica componentes.

## Phase 1 — Governed inline delegation

Cutover do SubAgentTool.

## Phase 2 — Durable child

Long tasks.

## Phase 3 — Group templates em shadow

single vs multi.

## Phase 4 — Controlled release

patterns comprovados.

---

# 126. ROLLBACK

Se delegation V2 falhar:

- desligar new group plans;
- preservar Work Runs/events;
- inline fallback somente se seguro;
- não reabilitar direct MCP/HTTP privilege;
- nunca sacrificar security para voltar rápido.

---

# 127. MIGRATIONS

Possíveis, NÃO decretadas:

- expand `agent_delegations`;
- role releases;
- parent/root refs em Work Runs;
- assignment projection.

O executor deve primeiro provar o que já existe no schema vivo.

Nenhuma tabela `_v2`.

---

# 128. ARQUIVOS PROVÁVEIS

Warm-up confirma.

```text
backend/app/agents/graph.py
backend/app/agents/tools/subagent_tool.py
backend/app/services/work/...
backend/app/services/tool_gateway...
backend/app/services/capability...
backend/app/api/agents.py

app/admin/central-agentes/page.tsx
app/api/admin/spec034/...

migrations expand-only

tests/
docs/canon/reports/SPEC-088-EXECUTION-REPORT.md
```

---

# 129. DEFINITION OF DONE

A SPEC-088 só fecha quando:

- [ ] Central atual auditada;
- [ ] todos os cards classificados por `component_kind`;
- [ ] nenhum serviço determinístico foi transformado em LLM sem evidência;
- [ ] quatro grupos operacionais definidos;
- [ ] Agent/Subagent/Auxiliar/Skill/Workflow/Rotina continuam distintos;
- [ ] Auxiliar não é Subagent;
- [ ] role contract existe;
- [ ] role behavior versionável;
- [ ] delegation contract existe;
- [ ] contexto de child é explícito;
- [ ] output de child é estruturado;
- [ ] privilege = interseção;
- [ ] SubAgentTool deixa de montar MCP/HTTP livremente;
- [ ] Tool Gateway governa child;
- [ ] revalidação ocorre no call time;
- [ ] unsupported capability falha alto;
- [ ] inline specialist funciona;
- [ ] durable specialist funciona;
- [ ] root/parent lineage existe;
- [ ] Work Run continua execução universal;
- [ ] nenhum `agent_runs`;
- [ ] Admission Gate existe;
- [ ] simple task não delega;
- [ ] parallel only for independent tasks;
- [ ] fanout hard cap existe;
- [ ] depth hard cap existe;
- [ ] budget existe;
- [ ] cancellation existe;
- [ ] result envelope existe;
- [ ] group plan existe;
- [ ] group template existe sem virar Auxiliar;
- [ ] Lead continua dono do outcome por default;
- [ ] peer-to-peer não é default;
- [ ] judges são read-only;
- [ ] judge não substitui approval humano;
- [ ] repair loop tem teto;
- [ ] agent memory não vira fonte de verdade;
- [ ] learning gera signal, não publicação;
- [ ] runtime/quality/cost/safety health separados;
- [ ] Central V2 mostra grupos;
- [ ] Central V2 mostra Live Work;
- [ ] Central V2 mostra delegation tree;
- [ ] Central V2 mostra custo/qualidade;
- [ ] initial group template avaliado contra single baseline;
- [ ] unnecessary delegation metric existe;
- [ ] duplicate work metric existe;
- [ ] M1–M10 provadas;
- [ ] cross-tenant verde;
- [ ] PII verde;
- [ ] cost attribution verde;
- [ ] no infinite delegation;
- [ ] no runtime paralelo;
- [ ] no new Tool Gateway;
- [ ] execution report produzido.

---

# 130. MÉTRICAS DE SUCESSO

Hard:

```text
privilege escalation ................... 0
cross-tenant delegation ................ 0
judge external side effect ............. 0
unbounded fanout ......................... 0
unbounded recursion ...................... 0
agent approval replacing human .......... 0
```

Quality:

```text
delegation precision
unnecessary delegation
duplicate work
schema pass
judge pass
repair rate
outcome success
```

Economics:

```text
cost per outcome
multi-agent premium
latency delta
token delta
```

Operations:

```text
active child runs
stuck child rate
timeout
cancel success
```

---

# 131. IMPACTO ESPERADO

## Arquitetura

**100/100**

Fecha a dívida entre as SPECs 053/056 e o SubAgent runtime antigo.

## Qualidade de trabalhos complexos

**98/100**

Principalmente:

- pesquisa;
- relatórios;
- análise multiárea;
- revisão crítica.

## Atendimento simples

**20/100 como multi-agent**

A 088 deve justamente IMPEDIR excesso aqui.

## Controle de custo

**96/100**

Se Admission/Budget forem bem implementados.

## Observabilidade

**99/100**

A Central passa a mostrar organização de verdade.

## Base para MetaHarness

**100/100**

A 108 poderá avaliar roles, groups e delegation health.

---

# 132. O QUE O CORRETOR VAI SENTIR

O corretor não precisa saber que existem 4 agents.

Ele percebe:

- análises mais completas;
- menos resposta superficial;
- relatórios com especialistas;
- qualidade mais consistente;
- trabalhos longos que continuam;
- menos erro de contexto.

O Admin/Founder percebe:

- quem fez;
- por quê;
- custo;
- resultado;
- falha;
- delegação;
- qualidade.

---

# 133. O QUE FICA PARA OUTRAS SPECS

Não engolir:

- Factory de Intelligence → 090;
- Protocol Factory → 091;
- Dreams → posterior;
- memória global/tenant/user aprofundada → Memory/Dreams SPEC;
- Marketplace Auxiliares → posterior;
- Channel Fabric/Slack/Teams → posterior;
- InfoCap Executive Reports → SPEC específica;
- MetaHarness completo → 108;
- desenvolvimento AAA de código → Protocolo AAA / Protocol Factory.

---

# 134. REFERÊNCIAS INTERNAS OBRIGATÓRIAS

- `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`
- `SPEC-053-autobrokers-work-os-core-harness.md`
- `SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`
- `SPEC-056-skill-registry-tool-gateway.md`
- `SPEC-058-auxiliary-routine-factory.md`
- `PLANO-CENTRAL-DE-AGENTES.md`
- `RASCUNHO-SPECS-FUTURAS.md`
- `app/admin/central-agentes/page.tsx`
- `backend/app/agents/graph.py`
- `backend/app/agents/tools/subagent_tool.py`
- `backend/supabase/migrations/upgrade_v6.2.sql`
- `backend/app/services/work/workflows.py`
- Candidates 086/087/089 fornecidas pelo Founder
- Protocolo AutoBrokers AAA v9

---

# 135. REFERÊNCIAS EXTERNAS

Detalhes no Research Pack.

## OpenAI Agents SDK

Padrões:

- manager vs handoff;
- agents as tools;
- code orchestration + LLM orchestration;
- structured routing.

## Anthropic Multi-Agent Research

Padrões:

- orchestrator-worker;
- parallel only when independent;
- delegation prompt completo;
- token economics;
- 3–5 workers em tarefas adequadas;
- outcome eval.

## Claude Code Subagents / Agent Teams

Padrões:

- isolated context;
- tool restrictions;
- max turns;
- team overhead;
- start with focused workers;
- teams experimental.

## LangChain / DeepAgents

Padrões:

- supervisor;
- subagent as tool;
- context isolation;
- typed result;
- background agents.

## DeepSeek Harness

Padrões:

- subagent as capability seam;
- fail loud;
- output schema;
- depth/tool filters;
- one-shot vs continuable child;
- durable task/roster concepts.

## Ruflo

Padrões selecionados:

- hierarchical orchestration;
- observability;
- health/evals;
- `parallel / pipeline / review`.

Não copiar swarm runtime.

---

# 136. AQUECIMENTO SUGERIDO AO CLAUDE CODE / CODEX

Antes da primeira alteração, responder com evidência:

1. Quantas rows existem em `agents`?
2. Quantas são `is_subagent=true`?
3. Quantas `agent_delegations` ativas?
4. Quais tenants possuem cada uma?
5. Quais subagents foram realmente invocados nos últimos 30 dias?
6. Quanto custaram?
7. Qual taxa de timeout?
8. Qual taxa de tool use?
9. Quais tools cada child efetivamente recebeu?
10. Mostre se Tool Gateway governa todas.
11. Ache um child que recebe tool por caminho legado.
12. `max_context_chars` é aplicado?
13. `max_iterations` é suficiente/útil?
14. Existe recursive delegation?
15. Existe parent/root lineage de Work Runs?
16. Existe child Work Run hoje?
17. `conversation_logs` é a única trilha de subagent?
18. Qual Agent da Central é realmente LLM?
19. Qual é deterministic service?
20. Qual é watcher?
21. Qual “memória por agent” é fonte e qual projection?
22. Quantos heartbeats são de processos, não Agents?
23. Onde AUTHORITY_STRICT está ligado?
24. A SPEC-056 foi realmente cutover?
25. Qual é o menor seam para Delegation Gateway?
26. Como Tool Gateway pode devolver child toolset?
27. Quais fields de Work Run precisam ser expandidos?
28. É possível derivar assignment sem tabela?
29. Ache uma task real onde multi-agent piora.
30. Ache uma onde 3 workers melhoram.
31. Tente fazer child escalar privilégio.
32. Tente fazer judge executar side effect.
33. Tente fazer worker usar tenant errado.
34. Tente criar loop de 10 agents.
35. Mostre o custo.
36. Refute qualquer desenho desta Candidate Spec que conflite com código vivo.

---

# 137. COMANDO FINAL AO EXECUTOR

Não me entregue uma Central com:

```text
20 cards
20 nomes
20 prompts
```

Entregue um sistema em que seja possível responder, para QUALQUER trabalho:

```text
quem é o dono?
por que delegou?
para quem?
qual contrato?
qual contexto?
quais poderes?
qual orçamento?
qual limite?
qual evidence?
quem revisou?
qual Work Run?
quanto custou?
deu certo?
```

A frase que governa a SPEC-088 é:

> **Agentes não formam uma organização porque têm nomes. Formam uma organização quando possuem missão, fronteiras, autoridade, contrato de entrega, supervisão e responsabilidade mensurável.**
