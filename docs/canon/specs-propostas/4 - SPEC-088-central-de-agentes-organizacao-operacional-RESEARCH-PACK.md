# SPEC-088 — RESEARCH PACK
## A Central de Agentes vira uma Organização Operacional

**Data:** 25/08/2026  
**Baseline AutoBrokers:** `8b49fdb337a6c37eb2ad181f5bad544a55dc0827`  
**Uso:** pesquisa, decisões e referências. Não carregar inteiro no bootstrap do executor.  
**SPEC associada:** `SPEC-088-central-de-agentes-organizacao-operacional.md`

---

# 1. PERGUNTA CENTRAL

Qual é o melhor formato para subagentes, grupos e “Central de Agentes” no AutoBrokers sem:

- virar swarm genérico;
- duplicar Work OS;
- confundir Auxiliar com Agent;
- entregar tools demais;
- multiplicar custo;
- perder tenant isolation;
- transformar cada serviço em LLM?

---

# 2. VEREDITO

O melhor padrão para AutoBrokers é:

# **CENTRALIZED ORCHESTRATOR + BOUNDED SPECIALISTS + DURABLE WORK RUNS**

Com cinco modos:

```text
single
bounded specialist
parallel group
deterministic workflow
explicit handoff
```

Default:

```text
single
```

Multi-agent é escalada de recursos.

Não arquitetura padrão de toda pergunta.

---

# 3. ESTADO REAL DO AUTOBROKERS

## 3.1 SPEC-053 já definiu a ontologia correta

Ela diz:

- Smith único runtime;
- Agent/Subagent executores cognitivos;
- Skill procedimento;
- Auxiliar produto;
- Rotina gatilho;
- Work Run universal;
- Capability Registry autorização;
- Tool Gateway tools.

Portanto não falta “ideia de agentes”.

Falta alinhar implementação antiga.

---

# 4. SPEC-056 já definiu a segurança correta

Princípios:

```text
subagent never gets more powers than parent
subset of tools
child Work Run when async
cost/time/depth limits
```

A 088 não inventa.

Ela torna real.

---

# 5. IMPLEMENTAÇÃO ANTIGA DO SUBAGENT

`backend/app/agents/tools/subagent_tool.py`

Pontos bons:

- context isolation;
- specialist description;
- timeout;
- max iterations;
- ReAct;
- token logging;
- LangSmith child traces.

Pontos vencidos:

- monta tools diretamente;
- MCP direto;
- HTTP Router direto;
- KnowledgeBase direto;
- Web Search direto;
- CSV direto;
- não nasce como Work Run child;
- retorna JSON string;
- fallback sync usa new event loop/thread.

Essa é a principal dívida técnica da 088.

---

# 6. `agent_delegations`

Migration v6.2 criou:

```text
orchestrator_id
subagent_id
task_description
max_context_chars
timeout_seconds
max_iterations
```

É um bom embrião.

Mas não representa:

- output schema;
- Skill;
- Capability Pack;
- risk;
- depth;
- fanout;
- budget;
- quality;
- context policy;
- delegation type.

A 088 deve evoluir/consolidar, não criar `v2` cegamente.

---

# 7. CENTRAL ATUAL

`app/admin/central-agentes/page.tsx`

É um dashboard de:

```text
id
name
description
last_run
actions_today
heartbeat health
memory blocks
```

IDs incluem:

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

Problema:

nomes de produto/serviços/agents estão misturados.

A primeira tarefa é census.

---

# 8. RASCUNHO 088 ORIGINAL

A nota original dizia apenas:

> “Está muito confuso para mim.”

e:

> agrupar por propósito.

A Candidate 088 preserva isso, mas transforma grouping em ontology + runtime governance.

---

# 9. OPENAI AGENTS SDK — PESQUISA ATUAL

Fonte:
https://openai.github.io/openai-agents-python/multi_agent/

A documentação atual separa duas formas principais.

## 9.1 Agents as tools

Manager mantém o controle.

Specialist executa bounded task.

Manager sintetiza.

Isto é perfeito para:

```text
AutoBrokers Core
↓
Analista Comercial
↓
resultado
↓
Core responde
```

Nota AutoBrokers:

# **99/100**

## 9.2 Handoffs

Especialista torna-se agente ativo.

Bom quando ele realmente deve falar.

Para AutoBrokers:

# **60/100 genérico**
# **95/100 quando ownership realmente precisa mudar**

Não usar como default.

---

# 10. OPENAI — CODE VS LLM ORCHESTRATION

A documentação também separa:

```text
LLM decides flow
```

e:

```text
code decides flow
```

e recomenda combinar.

Aplicação:

```text
known insurance workflow
→ code

open-ended research
→ LLM

known pipeline with cognitive steps
→ hybrid
```

Essa é uma decisão-chave.

---

# 11. ANTHROPIC — MULTI-AGENT RESEARCH

Fonte:
https://www.anthropic.com/engineering/multi-agent-research-system

Arquitetura:

```text
LeadResearcher
↓
parallel subagents
↓
synthesis
↓
citation agent
```

---

# 12. ONDE MULTI-AGENT GANHA

Anthropic observou ganhos fortes em:

- breadth-first;
- múltiplas direções independentes;
- pesquisa grande;
- muitas tools;
- contexto excede um Agent.

No internal research eval citado por eles:

```text
Opus lead + Sonnet workers
superou single Opus em 90,2%
```

Isso é evidência naquele benchmark, não uma lei geral.

Não copiar número como promessa do AutoBrokers.

---

# 13. CUSTO

A Anthropic também reporta:

```text
agent ≈ 4x chat tokens
multi-agent ≈ 15x chat tokens
```

na análise deles.

Lição:

> multi-agent precisa de outcome valioso.

Para lookup simples:

não.

Para relatório executivo:

talvez.

Para research profundo:

sim.

---

# 14. PARALELISMO

Anthropic:

- lead pode spawnar 3–5 em pesquisa complexa;
- workers podem usar ferramentas em paralelo;
- reported time reduction até 90% em determinados research flows.

AutoBrokers:

não transforma isso em default.

Adota:

```text
3–5 somente para high-value parallelizable tasks.
```

---

# 15. EARLY FAILURE — 50 AGENTS

Anthropic relata protótipos iniciais que:

- spawnavam 50 agents;
- pesquisavam indefinidamente;
- duplicavam trabalho;
- distraíam uns aos outros.

Isso valida hard caps.

---

# 16. DELEGATION PROMPT

O lead precisa passar:

- objetivo;
- output;
- ferramentas/fontes;
- boundaries.

AutoBrokers cria `DelegationEnvelope`.

---

# 17. ANTHROPIC — CONTEXT ENGINEERING

Fonte:
https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

Subagents funcionam como context isolation.

Worker pode usar muito contexto local e retornar síntese curta.

Isso é altamente relevante.

---

# 18. ANTHROPIC — CONTAINMENT

Fonte:
https://www.anthropic.com/engineering/how-we-contain-claude

Princípio:

à medida que agent ganha capability, blast radius cresce.

Aplicação:

```text
role risk ceiling
+
tool intersection
+
judge read-only
+
external effects governed
```

---

# 19. CLAUDE CODE SUBAGENTS — PESQUISA ATUAL

Fonte:
https://code.claude.com/docs/en/sub-agents

Campos úteis:

- description;
- tools;
- disallowedTools;
- model;
- maxTurns;
- skills;
- MCP;
- hooks;
- memory;
- effort;
- background;
- isolation.

Não copiar filesystem model.

Copiar:

```text
explicit role contract
```

---

# 20. CONTEXT ISOLATION

Claude subagent:

- own context;
- task-specific;
- summary back.

AutoBrokers:

`FRESH_MINIMAL` default.

---

# 21. CLAUDE CODE AGENT TEAMS

Fonte:
https://code.claude.com/docs/en/agent-teams

Hoje:

- experimental;
- disabled by default;
- lead + teammates;
- shared task list;
- peer messaging;
- token overhead.

Docs atuais recomendam começar com:

```text
3–5 teammates
```

para workflows apropriados.

Também dizem:

> três focados podem superar cinco dispersos.

Ótima regra.

---

# 22. SUBAGENT VS TEAM

Claude docs:

```text
subagent
→ focused
→ return to lead
→ lower cost

agent team
→ peer communication
→ complex collaboration
→ higher cost
```

AutoBrokers V1:

SUBAGENT pattern.

Peer teams ficam fora.

---

# 23. DEEPSEEK HARNESS — ESTADO ATUAL

Repo oficial:
https://github.com/deepseek-ai/deepseek-harness

Criado em 13/08/2026.

Está em:

```text
developer preview
```

e alerta explicitamente para breaking changes.

Logo:

```text
instalar como core = NÃO
estudar padrões = SIM
```

---

# 24. DEEPSEEK — EVERYTHING IS A PLUGIN

Architecture:

```text
model adapter
tool registry
session log
agent loop
```

como plugins/seams.

AutoBrokers já possui equivalentes com autoridades próprias.

Não copiar plugin architecture.

---

# 25. DEEPSEEK — SUBAGENT AS CAPABILITY SEAM

Excelente conceito:

> subagent é capability opcional, não parte inevitável do loop.

Nota para AutoBrokers:

# **100/100**

Delegation entra somente quando admission permite.

---

# 26. DEEPSEEK — START-TIME CAPABILITY CHECKS

O provider declara se suporta:

```text
outputSchema
depthLimit
toolFilter
persona
```

Pedido incompatível:

```text
UNSUPPORTED_CAPABILITY
```

não degrada silenciosamente.

AutoBrokers deve copiar este princípio.

---

# 27. DEEPSEEK — CONTINUABLE CHILD

Distingue:

```text
one-shot
```

de:

```text
continuable background child
```

AutoBrokers já tem a melhor fundação para isso:

```text
Work Run
```

Portanto:

```text
inline specialist
durable specialist
```

---

# 28. DEEPSEEK — TOOL FILTER

Child tool restrictions aplicadas no próprio scope e tool fica invisível + não executável.

AutoBrokers:

```text
Tool Gateway
```

deve fazer o mesmo.

---

# 29. DEEPSEEK — EXPERIMENTAL AGENT TEAMS

Possui:

- durable roster;
- mailbox;
- task DAG;
- CAS revision;
- blockedBy;
- owner.

Padrões úteis.

Mas AutoBrokers já tem:

```text
Work Runs
Work Steps
Work Events
```

Criar TeamTask paralelo seria duplicação.

---

# 30. LANGCHAIN MULTI-AGENT

Fonte:
https://docs.langchain.com/oss/python/langchain/multi-agent/subagents

Supervisor pattern:

- central agent;
- subagents as tools;
- no direct user;
- clean context;
- parallel possible.

É essencialmente o padrão selecionado.

---

# 31. DEEPAGENTS

Repo:
https://github.com/langchain-ai/deepagents

Padrões:

- subagents;
- isolated contexts;
- filesystem offload;
- skills;
- HITL;
- tracing.

AutoBrokers usa:

- isolated context;
- artifact refs;
- Skill Registry;
- Work Runs.

Não instala harness.

---

# 32. RUFLO

Conclusão anterior permanece.

Bom como laboratório.

Para 088:

## aproveitar

- hierarchical;
- parallel/pipeline/review;
- health;
- observability.

## não aproveitar

- swarm topologies;
- 314 tools;
- new memory;
- new workflow engine;
- peer consensus.

---

# 33. POR QUE AUXILIAR NÃO É AGENT

Exemplo:

Auxiliar de cobrança pode ser:

```text
routine
↓
deterministic query
↓
PDF/boletos
↓
WhatsApp send
```

Zero Agent.

Outro Auxiliar pode ser:

```text
routine
↓
analyst agent
↓
artifact
```

Outro:

```text
lead + 3 analysts
```

Produto não pode depender da implementação.

---

# 34. POR QUE NEM TODO NOME É AGENT

“Espelho” pode ser um consumidor de eventos.

“Sentinela” pode ser watcher.

“Cartógrafo” pode ser deterministic mapper.

Chamá-los agents não muda código.

Mas confunde:

- responsabilidades;
- custo;
- memória;
- tool access;
- health.

Census obrigatório.

---

# 35. GROUPS

Quatro grupos escolhidos:

```text
Observe & Record
Plan & Orchestrate
Execute & Follow
Review & Improve
```

São agrupamento organizacional/UI.

Não runtime.

---

# 36. MANAGER-FIRST

Por seguros:

lead central é melhor que peer swarm porque:

- audit;
- brand voice;
- policy;
- tenant;
- human approval;
- controlled side effects.

---

# 37. WHY NOT PEER MESH

Peer messaging livre aumenta:

- token;
- nondeterminism;
- authority ambiguity;
- coordination overhead.

Use apenas se future eval provar.

---

# 38. HARD DEPTH = 1

Por default:

```text
Lead → worker
```

É simples de auditar.

Depth 2 somente pattern explícito.

---

# 39. WHY 3–5 IS MAX PRACTICAL, NOT DEFAULT

Docs Claude e Anthropic usam 3–5 em tarefas paralelas.

AutoBrokers:

```text
normal = 0–2
research/report = 3
max = 5
```

por custo e domínio.

---

# 40. QUALITY JUDGES

Juiz não deve compartilhar trabalho do executor.

Ideal:

- recebe artifact;
- critérios;
- evidence;
- verdict.

Isso reduz self-review bias.

---

# 41. AAA PROFILE

Não usar em toda tarefa.

Bom para:

- SPEC validation;
- high-value report;
- critical release;
- major research.

Custo precisa justificar.

---

# 42. MEMORY

Claude Code permite persistent agent-specific memory.

Não copiar isso como “verdade” no produto.

AutoBrokers já decidiu:

```text
global
tenant
user
```

Agent-specific persistência pode existir apenas como:

- operational hints;
- working cache;
- learning signals.

---

# 43. AGENT-AS-TOOL SCORE

Para AutoBrokers:

# **99/100**

É exatamente o padrão natural do Core.

---

# 44. HANDOFF SCORE

Como default:

# **55/100**

Quando ownership real muda:

# **95/100**

---

# 45. PEER AGENT TEAM SCORE

Runtime default:

# **35/100**

Pesquisa especializada futura:

# **80/100**

Agora não.

---

# 46. DEEPSEEK HARNESS COMO DEPENDÊNCIA

# **20/100**

Developer preview + segundo harness.

---

# 47. DEEPSEEK PATTERNS

# **96/100**

Especialmente:

- seam;
- fail loud;
- depth/tool filters;
- one-shot vs continuable.

---

# 48. RUFLO RUNTIME

# **18–32/100**

Mantém conclusão anterior.

---

# 49. RUFLO PATTERNS

# **91/100**

---

# 50. DEEPAGENTS RUNTIME

# **35/100**

Porque já existe Smith/LangGraph.

---

# 51. DEEPAGENTS PATTERNS

# **94/100**

---

# 52. CENTRAL V2

Valor:

# **99/100**

Porque resolve:

- compreensão;
- governança;
- troubleshooting;
- cost;
- quality;
- product clarity.

---

# 53. PRINCIPAL ACHADO

A grande melhoria não é:

```text
“colocar mais agents”
```

É:

```text
dar ao sistema a capacidade de decidir
quando NÃO usar agents.
```

Isso é maturity.

---

# 54. REFERÊNCIAS INTERNAS INSPECIONADAS

- SPEC-053
- SPEC-056
- SPEC-058
- PLANO-CENTRAL-DE-AGENTES
- RASCUNHO-SPECS-FUTURAS
- Central page
- graph.py
- subagent_tool.py
- upgrade_v6.2.sql
- Workflows/Work Runs

---

# 55. REFERÊNCIAS EXTERNAS

OpenAI Agent orchestration  
https://openai.github.io/openai-agents-python/multi_agent/

OpenAI Handoffs  
https://openai.github.io/openai-agents-python/handoffs/

Anthropic Multi-Agent Research  
https://www.anthropic.com/engineering/multi-agent-research-system

Anthropic Context Engineering  
https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

Anthropic Containment  
https://www.anthropic.com/engineering/how-we-contain-claude

Claude Code Subagents  
https://code.claude.com/docs/en/sub-agents

Claude Code Agent Teams  
https://code.claude.com/docs/en/agent-teams

LangChain Multi-Agent / Subagents  
https://docs.langchain.com/oss/python/langchain/multi-agent/subagents

DeepAgents  
https://github.com/langchain-ai/deepagents

DeepSeek Harness  
https://github.com/deepseek-ai/deepseek-harness

DeepSeek Architecture  
https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md

DeepSeek Subagents  
https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/subagent.md

DeepSeek Agent Teams  
https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/agent-team.md

---

# 56. DECISÕES CONGELADAS

| Decisão | Veredito |
|---|---|
| Smith único runtime | SIM |
| Auxiliar = Subagent | NÃO |
| Manager-first | SIM |
| Agent-as-tool default | SIM |
| Handoff default | NÃO |
| Multi-agent every task | NÃO |
| Admission Gate | SIM |
| Tool Gateway para child | SIM |
| Capability intersection | SIM |
| Fresh context | SIM |
| Structured output | SIM |
| Inline child | SIM |
| Durable child Work Run | SIM |
| Depth default 1 | SIM |
| Max group 5 | SIM |
| Peer messaging V1 | NÃO |
| Judge read-only | SIM |
| Judge substitutes human approval | NÃO |
| Global role templates | SIM |
| Tenant-scoped invocation | SIM |
| Agent private truth memory | NÃO |
| Central UI grouped | SIM |
| Health beyond heartbeat | SIM |

---

# 57. VEREDITO

A Central de Agentes não deve ser:

> “um lugar onde vemos nossos bots.”

Ela deve ser:

> **o Control Plane da força de trabalho cognitiva do AutoBrokers.**

A arquitetura vencedora:

```text
OUTCOME
↓
ADMISSION
↓
LEAD
↓
SPECIALISTS ONLY WHEN NEEDED
↓
WORK RUNS
↓
TOOL GATEWAY
↓
RESULT ENVELOPES
↓
QUALITY GATE
↓
OUTCOME
```

Nota final:

# **100/100**
