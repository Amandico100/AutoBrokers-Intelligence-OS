# AUTOBROKERS — SPEC TRANSFORMATION MASTERPLAN
## Método definitivo para criar a próxima geração de SPECs
**Data:** 25/08/2026  
**Status:** Plano de criação — ainda não é uma SPEC de implementação  
**Objetivo:** transformar o rascunho estratégico do Founder em uma sequência executável de SPECs profundamente pesquisadas, verticalizadas para corretoras de seguros e compatíveis com a arquitetura canônica do AutoBrokers.

---

# 1. NORTE DO PROGRAMA

O AutoBrokers não deve virar uma coleção de frameworks.

> **Absorver os melhores padrões externos e manter uma única arquitetura AutoBrokers.**

```text
OPERAÇÃO
   ↓
TRAJECTORY
   ↓
LEARNING SIGNAL
   ↓
DREAMS
   ↓
KNOWLEDGE / SKILL / ROUTE CANDIDATE
   ↓
PROTOCOL FACTORY
   ↓
AAA EVAL
   ↓
PUBLICAÇÃO
   ↓
METAHARNESS
   ↓
OPERAÇÃO MELHOR
```

O Dashboard continua. ChatGPT, Claude, WhatsApp, Slack/Teams, Auxiliares e agentes podem chamar capacidades. A inteligência vertical permanece no **AutoBrokers Engine**.

---

# 2. REGRAS PARA NÃO DESTRUIR O QUE JÁ ESTÁ BOM

1. Um único runtime cognitivo: Smith + LangGraph/LangChain.
2. Um único Work OS.
3. Um único Tool Gateway.
4. Um único Skill Registry.
5. Um único Artifact Hub.
6. Uma única autoridade de memória/conhecimento.
7. Supabase continua fonte de verdade; Qdrant continua índice derivado.
8. Framework externo é referência/provider, não nova autoridade, salvo prova extraordinária.
9. Toda nova peça deve responder: **reusar, estender, substituir ou descartar?**
10. Toda mudança multi-tenant deve provar isolamento.
11. Todo trabalho que chega ao segurado precisa de verdade, fallback e handoff.
12. Toda SPEC precisa de resultado testável; “adicionar arquitetura” não é resultado.
13. Nenhuma SPEC pode usar inferência como se fosse medição.
14. Requisito de produto e proposta de implementação devem ficar separados.
15. Um executor pode corrigir a implementação proposta se o repositório provar que a premissa estava errada, sem violar o resultado/invariantes da SPEC.

---

# 3. O MÉTODO — AUTOBROKERS SPEC FOUNDRY

## FASE 0 — Registry Check
Antes de dar número a uma nova SPEC:
- verificar HEAD e branch atuais;
- listar SPECs existentes e reservas;
- verificar se a ideia já existe parcial ou totalmente;
- procurar migrations, services, tools, tests, pendências e execution reports;
- registrar o commit-base;
- classificar a ideia como NOVA, EVOLUÇÃO, CONVERGÊNCIA, CORREÇÃO, ABSORÇÃO ou DESCARTADA.

## FASE 1 — Idea Assessment
Perguntas obrigatórias:
1. Qual problema real de corretora isto resolve?
2. Quem sente o problema?
3. Com que frequência?
4. O resultado aumenta receita, reduz custo, reduz risco, aumenta capacidade ou qualidade?
5. Já existe algo no AutoBrokers?
6. A nova ideia melhora o que existe ou cria duplicação?
7. Existe solução mais simples?
8. É IA, humano ou híbrido?
9. É global, tenant, team, user ou entity-specific?
10. Deve ser SPEC própria, bloco de outra, experimento, pendência ou descartada?

Saída: **GO / MERGE / SPLIT / DEFER / KILL**.

## FASE 2 — Imersão no repositório
Inspecionar, conforme o tema:
- código real;
- schemas e migrations;
- testes;
- execution reports;
- pendências;
- CLAUDE.md e protocolo;
- telemetria;
- Work Runs;
- dados medidos em produção quando permitido;
- integrações atuais;
- UI real;
- falhas anteriores;
- commits recentes do domínio.

> **Código e dado atuais vencem documento antigo.**

## FASE 3 — Pesquisa externa profunda
Pesquisar por camadas:

### Tier A — Autoridade
- documentação oficial;
- source code oficial;
- RFC/spec oficial;
- release notes;
- papers.

### Tier B — Evidência de implementação
- issues;
- PRs;
- benchmarks;
- incident reports;
- engineering blogs;
- source examples.

### Tier C — Experiência de especialistas
- discussões de senior devs;
- fóruns técnicos;
- Reddit especializado quando útil;
- Hacker News;
- comunidades de LangGraph/agents.

Pesquisar também críticas, falhas, custo, lock-in e alternativas.

## FASE 4 — Verticalização para seguros
Toda referência externa precisa responder:
> “Como isto vira valor para uma corretora?”

Mapear: ator, tarefa, trigger, dado, ação, risco, saída, entrega, ganho, exceção e momento de humano.

## FASE 5 — Architecture Fit
Para cada padrão externo:
| Padrão | AutoBrokers já possui | Decisão |
|---|---|---|
| ... | ... | REUSAR / ESTENDER / ADAPTAR / NÃO USAR |

Checar autoridade, tenant isolation, permissions, Vault, HITL, idempotência, Work Runs, Tool Gateway, Artifact Hub, Memory Fabric, observabilidade, custo, latência, Engine e rollback.

## FASE 6 — Fronteira da SPEC
Uma SPEC nasce quando existe um outcome principal, fronteira coerente, dependências identificadas e DoD objetiva.

Separar quando há autoridade, risco, rollout ou blast radius independentes. Fundir quando uma parte sem a outra não entrega valor, compartilham state machine ou separá-las criaria duas verdades.

## FASE 7 — Matriz de verdade
- 📊 **MEDIDO** — reproduzido contra dado/código real;
- 🔎 **OBSERVADO NO REPO** — arquivo/linha/schema encontrado;
- 🌐 **REFERÊNCIA EXTERNA** — fonte citada;
- 💭 **HIPÓTESE** — ainda precisa ser medida;
- 🔒 **DECISÃO** — requisito/invariante congelada.

## FASE 8 — Desenho do produto
Definir experiência do corretor, operador e segurado; state machine; objetos; inputs; outputs; artifacts; permissions; HITL; falhas; recuperação; métricas de valor.

## FASE 9 — Desenho técnico
Conforme aplicável: arquitetura, componentes, APIs, tool contracts, schemas, migrations, events, connectors, model routing, cache, queues, locks, retries, idempotency, PII, prompt injection, egress, RLS, observability, performance, cost e rollback.

## FASE 10 — Prova antes do código
Matriz: unit, integration, contract, schema/data, regression, mutation, adversarial, control, E2E, canary, failure injection, production smoke, tenant isolation.

> **Teste precisa poder ficar vermelho pelo motivo certo.**

## FASE 11 — Context Diet
Profundidade não significa arquivo monolítico.

Cada entrega terá:

### A. `SPEC-xxx-<nome>.md`
Contrato de execução completo: outcome, invariantes, arquitetura, blocos, gates, testes, rollback e DoD.

### B. `SPEC-xxx-<nome>-RESEARCH-PACK.md`
Pesquisa profunda: referências, comparações, padrões externos, evidências, alternativas rejeitadas, decisões de verticalização e anexos.

O executor recebe primeiro a SPEC. O Research Pack é carregado sob demanda.

## FASE 12 — Entrega ao Founder
Ao terminar cada SPEC:
1. SPEC `.md`;
2. Research Pack `.md`;
3. resumo executivo;
4. o que muda;
5. ganho esperado;
6. riscos;
7. decisões;
8. descartes;
9. checklist da próxima SPEC;
10. perguntas/sugestões antes da próxima.

## FASE 13 — Warm-up AAA antes da execução
A SPEC criada aqui é **Candidate Spec** até o executor verificar o estado vivo.

Claude Code/Codex deve tentar refutar premissas, conferir código/schema/dados, reproduzir medições, procurar motor paralelo, regressão, PII/tenant leak e corrigir a proposta de implementação mantendo outcome/invariantes.

> Não gastar múltiplas rodadas de juízes refinando texto indefinidamente. O AAA v9 mediu melhor valor quando juízes julgam código/produto.

## FASE 14 — Execução AAA
Executor + auxiliares/forks quando úteis + red team + mutation + controles + E2E + juiz de contexto limpo + juiz de confirmação + telemetria + delivery/push comprovado.

## FASE 15 — Convergência
Execution report, commit/deploy, registry atualizado, pendências fechadas/superseded e aprendizados alimentando a próxima SPEC.

---

# 4. TEMPLATE OBRIGATÓRIO DE UMA SPEC EXTRAORDINÁRIA

1. Header / status / data / baseline.
2. Resultado em uma frase.
3. Valor para corretora/segurado/operação.
4. Por que agora.
5. Estado atual medido.
6. Problema real.
7. Escopo.
8. Fora de escopo.
9. Autoridades existentes.
10. Referências externas e o que será adaptado.
11. Alternativas descartadas.
12. Invariantes.
13. Ontologia.
14. State machine.
15. Arquitetura.
16. Data model / migrations.
17. APIs / Tools / Connectors.
18. UX.
19. Multi-tenant / roles / ACL.
20. Memory/RAG/Learning impact.
21. Models / routing / token and cost.
22. Security / PII / prompt injection / egress.
23. Observability / traces / events.
24. Failure modes / retries / fallback / HITL.
25. Performance / SLO.
26. Compatibility / migration / cutover.
27. Implementation blocks.
28. Gates por bloco.
29. Test matrix.
30. Controls.
31. Mutation/adversarial tests.
32. E2E/canary.
33. Rollback.
34. Success/value metrics.
35. Definition of Done.
36. Pendências conscientemente adiadas.
37. Research Pack / source index.
38. Warm-up questions para o executor.

---

# 5. SEQUÊNCIA DEFINITIVA — LINHA RETA

## Lane atual — atendimento

### 0. SPEC-092 — O formulário dentro do WhatsApp
**Estado:** já escrita; não reescrever.  
**Nota:** 99/100  
**Ação:** executar pelo AAA v9.

### 1. SPEC-089 — A Régua AAA é Honesta
**Nota:** 100/100  
Eliminar score impossível >100, denominador inconsistente e ponto sem evidência real. É pré-condição para auto-update e fábricas futuras.

### 2. SPEC-086 — Continuidade do Atendimento
**Nota:** 100/100  
Consolidar o que ainda falta após a 085: Resume Pack, humano assumir no meio do acionamento, continuidade no mesmo caso, follow-up state machine e encerramento verdadeiro.

### 3. SPEC-087 — Route Self-Healing Loop
**Nota:** 99/100  
Detectar mudança de URA/portal → propor patch → testar → AAA → aprovação → rollout → rollback. Absorve a antiga SPEC-080 e padrões Browserbase/autobrowse.

### 4. SPEC-090 — Fábrica de Inteligência de uma Nova Corretora
**Nota:** 100/100  
Conversas pareadas viram triagem, Atlas, rotas, aliases, instruções, candidates e relatório, sempre governados.

### 5. SPEC-091 — Protocol & Process Registry
**Nota:** 100/100  
Processos executáveis e versionados. Protocolos iniciais: SPEC, corredor, melhorar corredor, Skill, Auxiliar, Connector, sistema de gestão, RAG, publicação de memória/conhecimento, auxiliar por seguradora, canal e Artifact/Report.

### 6. SPEC-088 — Central de Agentes 2.0
**Nota:** 95/100  
Organizar agentes/trabalhadores por propósito e mostrar responsabilidade, runs, falhas, handoffs, entregas e saúde.

---

# 6. NOVO PROGRAMA DE TRANSFORMAÇÃO

### 7. SPEC-093 — Claims Learning Shadow
**Nota:** 99/100  
Coletar o que humanos fazem em sinistros para gerar dataset operacional, padrões, candidatos a rota e futura automação simples. Não automatiza sinistro complexo agora.

### 8. SPEC-094 — Artifact & Delivery Hub Completion
**Nota:** 100/100  
Fechar a dívida da SPEC-057 e transformar Entregas em uma área excelente: encontrar, abrir, compartilhar, acompanhar, versionar e navegar.

### 9. SPEC-095 — Executive Intelligence 360 / InfoCap
**Nota:** 100/100  
Evoluir SPEC-081: período vs anterior, seller momentum, comissão, repasse, contribuição após repasse, mix, concentração, renovação, projeção transparente e data confidence.

### 10. SPEC-096 — Chat Runtime Performance & Interaction Shell
**Nota:** 99/100  
TTFT, streaming, context latency, tool startup, composer, attachments/actions, mobile shortcuts e UX da primeira resposta.

### 11. SPEC-097 — Operations Workspace / Cases
**Nota:** 96/100  
Fila/Kanban real com casos, segurados, Work Runs e handoffs no mesmo modelo operacional.

### 12. SPEC-098 — Identity, Scope & Company Soul Fabric
**Nota:** 99/100  
Global, Corretora, Team, Usuário, Entidade e Run/Thread. Separar company facts, company soul, user profile e agent role. Corrigir identidade automática sem novo cérebro.

### 13. SPEC-099 — Channel Fabric v2
**Nota:** 98/100  
`ChannelConnection` tenant-owned com assignment para team/user/purpose. Multi-WhatsApp, e-mail, Slack, Teams, webchat e auditoria do encaixe Meta Ads. Mensagens externas geram candidates com ACL.

### 14. SPEC-100 — Skill & Capability Factory v2
**Nota:** 100/100  
Agent Skills compatibility, progressive disclosure, scripts/references/assets, capability profiles, subagent isolation, skill evals, release e minimum tool surface. Inspirações: Agent Skills, DeepSeek, DeepAgents.

### 15. SPEC-101 — Connector & Management-System Adapter Factory
**Nota:** 99/100  
InfoCap como referência para Quiver, Segfy e futuros sistemas; OAuth, Vault, health, permissions, schema discovery. Composio apenas como provider long-tail.

### 16. SPEC-102 — Knowledge & Memory Factory
**Nota:** 100/100  
Nova base → ingestão → sanitização → provenance → dedup → contradiction → confidence → candidate → review → publication → supersession → forgetting.

### 17. SPEC-103 — Auxiliary Marketplace & Automation Studio
**Nota:** 98/100  
Official, Premium, Private/Custom e Partner/Community futuro. Preserva serviço sob demanda premium. Clarifica Auxiliar ≠ Agent ≠ Skill ≠ Rotina.

### 18. SPEC-104 — Research Intelligence Pack v2
**Nota:** 95/100  
Evoluir SPEC-060 com Tavily, Firecrawl, RSS, GitHub, YouTube, comunidades, fontes oficiais e research monitors. Agent-Reach é referência/adapters, não segundo Research Engine.

---

# 7. LOOP COGNITIVO

### 19. SPEC-105 — Trajectory / Replay / Fork
**Nota:** 99/100  
Work Run reconstruível: contexto, evidência, skill, tools, subagents, approvals, retries, decisions, costs e result. Search/replay/fork/compare. Inspiração DeepSeek/Ruflo.

### 20. SPEC-106 — Dreams & Nightly Consolidation
**Nota:** 99/100  
Operation → candidate → dedupe → contradiction → temporal → scope → publish/review/discard. Inclui forgetting/staleness. Mem0/Graphiti apenas benchmark controlado.

### 21. SPEC-107 — Trust & Untrusted Content Gate
**Nota:** 98/100  
Gate comum para web, PDF, email, Slack/Teams, WhatsApp, MCP e connectors: PII → sanitization → prompt-injection → provenance → context.

### 22. SPEC-108 — AutoBrokers MetaHarness
**Nota:** 100/100  
Harness Health por Core/Atendimento/Auxiliar/Skill/Corredor: outcome success, tool safety, evidence coverage, context efficiency, memory usefulness, latency, cost, drift, security, eval confidence e mutation health.

---

# 8. DISTRIBUIÇÃO DA INTELIGÊNCIA

### 23. SPEC-109 — AutoBrokers Engine v1
**Nota:** 100/100  
Engine headless de Outcomes/Actions de seguro. Começar read-heavy: policy.answer-with-evidence, brokerage.executive-pulse, renewals.radar, research.insurance. Depois actions transacionais governadas.

### 24. SPEC-110 — External Harness Gateway
**Nota:** 99/100  
ChatGPT, Claude e outros clients chamam o Engine via MCP/App/API/Agent-Skills-compatible interfaces. Dashboard continua existindo.

### 25. SPEC-111 — Model & Cost Fabric
**Nota:** 92/100  
Managed AI, BYOK API e External Harness; routing, budget, quota, trial, metering. Proibido usar credenciais de assinatura consumer Claude/ChatGPT como backend do SaaS.

### 26. SPEC-112 — AutoBrokers Voice
**Nota:** 88/100  
Realtime voice usando o MESMO Engine, memória, Skills e Work Runs; interrupção, latência, handoff e logging. Não cria segundo “Jarvis”.

---

# 9. VALOR COMPLEMENTAR

### 27. SPEC-113 — Broker Growth & Creative Studio
**Nota:** 88/100  
Infográficos, apresentações, carrosséis, blog/SEO/AEO e conteúdos, usando Research + Brand Fabric + Artifact Hub + Skills. Baoyu e similares são referências de composição.

---

# 10. FECHO DO PROGRAMA

### 28. SPEC-114 — Transformation Convergence & Production Readiness
**Nota:** 100/100  
Atualizar/superseder as antigas SPEC-062/068 quando necessário. Gate final: E2E, tenant isolation, billing, SLO, failure injection, security, privacy, rollback, canary, Admin, observability, Engine, channels, memory, learning, artifacts e Auxiliares.

---

# 11. REFERÊNCIAS EXTERNAS — ONDE ENTRAM

| Referência | Onde entra |
|---|---|
| DeepSeek Harness | SPEC-100, 105, 108 |
| Grok Bot | SPEC-088, 103 |
| Hermes | SPEC-098, 100 |
| Agent Skills | SPEC-100, 110 |
| DeepAgents | SPEC-100 |
| Browserbase Skills | SPEC-087, 101 |
| Composio | SPEC-101 |
| Agent-Reach | SPEC-104 |
| Mem0 | SPEC-106 benchmark |
| Graphiti | SPEC-106 benchmark |
| Ruflo | SPEC-105, 107, 108 |
| Baoyu/infographics | SPEC-113 |

---

# 12. IDEIAS DESCARTADAS COMO ARQUITETURA

Não viram SPEC própria:
1. DeepSeek Harness como novo runtime.
2. Ruflo como runtime do AutoBrokers.
3. Mem0 como nova autoridade de memória.
4. Graphiti como nova autoridade de memória.
5. Auxiliar = Subagente.
6. Dar centenas de tools diretamente ao modelo.
7. Agent-Reach como segundo Research Engine.
8. Slack/Teams bruto → memória automática.
9. Consumer subscription Claude/ChatGPT → backend do SaaS.
10. Marketplace comunitário aberto sem governança.
11. Sinistro complexo autônomo já.
12. Segundo cérebro para Voice.
13. Copiar frameworks inteiros por popularidade.

---

# 13. PRIMEIRA SPEC A SER CRIADA

## SPEC-089 — A RÉGUA AAA É HONESTA

### Objetivo
Garantir que a régua:
- nunca produza nota matematicamente impossível;
- não conceda ponto sem evidência;
- tenha denominator explícito;
- diferencie inaplicável de não provado;
- tenha mandatory gates não compensáveis;
- consiga reprovar;
- tenha mutation/control;
- seja confiável para 087 e fábricas futuras.

### Pesquisa obrigatória
1. reproduzir o 102/100 atual;
2. abrir `rubrica.py`;
3. abrir `medir_rota.py`;
4. abrir `test_a_rubrica_e_honesta.py`;
5. medir os 5 vermelhos atuais;
6. separar bug da régua, bug do corredor, teste vencido e denominator errado;
7. ler 083/084/084.1/084.2 e reports;
8. auditar rota de referência;
9. pesquisar calibration/rubric/eval design;
10. decidir score diagnóstico vs certificação binária.

### Decisões para discutir com o Founder
1. AAA deve ser certificação binária + score diagnóstico ou tiers AAA/AA/A?
   - recomendação: certificação binária + score diagnóstico.
2. Uma rota sem produção real pode ser “AAA”?
   - recomendação: diferenciar `AAA_READY` de `AAA_VALIDATED`.
3. Todas as rotas têm o mesmo denominator?
   - recomendação: score normalizado por itens aplicáveis + gates obrigatórios não compensáveis.

---

# 14. CICLO FOUNDER ↔ CHATGPT

```text
1. Preview/checklist da próxima SPEC
2. Founder adiciona opinião/regras/ideias
3. Imersão no repo
4. Pesquisa externa profunda
5. Verticalização para corretoras
6. Arquitetura e fronteira
7. SPEC + Research Pack
8. Downloads .md
9. Resumo da SPEC
10. Preview/checklist da próxima
11. Founder comenta
12. Repete
```

Depois:

```text
Claude Code / Codex
↓
AAA warm-up
↓
refuta premissas
↓
ajusta implementação proposta
↓
executa
↓
juízes julgam CÓDIGO/PRODUTO
↓
mutation / E2E / canary
↓
execution report
```

---

# 15. DEFINITION OF SUCCESS DO MASTERPLAN

O programa está bem desenhado se:
- nenhuma ideia boa ficou sem destino;
- nenhum framework virou autoridade paralela;
- cada SPEC tem outcome claro;
- dependências permitem linha reta;
- as primeiras SPECs aumentam confiabilidade e valor imediato;
- fábricas vêm antes de escala;
- aprendizagem vem com governança;
- Engine só é exposto depois de capacidade confiável;
- recursos complementares ficam mais para o fim;
- o programa termina com um gate de convergência e produção.
