# Índice e autoridade das SPECs canônicas

> [!IMPORTANT]
> Para qualquer tarefa relacionada a conhecimento, RAG, memória, Context Assembly, aprendizagem, ferramentas, Skills, conectores, MCPs, Auxiliares, Rotinas, Work Runs, approvals, artifacts, proatividade, briefings, Garimpo, pesquisa, crawling, fontes, citações, monitors ou Portal Admin, leia primeiro as SPECs **052** e **053**.

## Autoridade atual

1. `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md` — arquitetura cognitiva soberana: conhecimento, memória, contexto, aprendizagem e cérebro unificado.
2. `SPEC-053-autobrokers-work-os-core-harness.md` — arquitetura soberana do Work OS: Core Harness, Skills, Tool Gateway, execução durável, Auxiliares, Rotinas, artifacts e Control Plane.
3. [`SPEC-054-foundation-hardening-schema-governance.md`](SPEC-054-foundation-hardening-schema-governance.md) — fechamento P0, Storage privado, baseline reproduzível, integridade multi-tenant, hardening de HTTP/MCP, Authority Strict progressivo e idempotência preparatória.
4. [`SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`](SPEC-055-durable-work-runs-queue-checkpoints-hitl.md) — execução universal de lançamento: Work Runs, steps, attempts, Redis Streams, worker Smith, leases, checkpoints, HITL, approvals, side effects idempotentes e integração com Rotinas, Auxiliares e Portais.
5. [`SPEC-056-skill-registry-tool-gateway.md`](SPEC-056-skill-registry-tool-gateway.md) — catálogo canônico e versionado de Skills, Capability Packs e Tool Releases; Tool Gateway único; seleção dinâmica; migração de native/HTTP/MCP/Portal/delegation; biblioteca inicial de Skills e ativação em produção.
6. [`SPEC-057-artifact-hub-report-studio.md`](SPEC-057-artifact-hub-report-studio.md) — Artifact Hub único, Report Studio, templates versionados, renderer determinístico, relatório web/PDF, XLSX, CSV, PPTX, DOCX, gráficos, Evidence Pack, compartilhamento, entrega e Visual Acceptance Pack.
7. [`SPEC-058-auxiliary-routine-factory.md`](SPEC-058-auxiliary-routine-factory.md) — Factory único de Auxiliares e Rotinas; classificação de padrão de trabalho; criação por chat e dashboard; releases, instalações, revisões, triggers, readiness, custos, demanda e cutover dos caminhos legados.
8. [`SPEC-059-briefing-proatividade-garimpo-v3.md`](SPEC-059-briefing-proatividade-garimpo-v3.md) — Intelligence Fabric único: eventos, sinais, evidências, Findings, recomendações, Briefing Diário/Semanal, Garimpo v3, Demand Radar, feedback, outcome e migração da proatividade histórica.
9. [`SPEC-060-research-intelligence.md`](SPEC-060-research-intelligence.md) — Research Intelligence único: Research Orchestrator, providers, fontes, crawling, claims, citações, Evidence Packs, monitors, pesquisa regulatória/concorrentes/SEO-AEO/empresas e migração do web search histórico.
10. SPECs posteriores explicitamente subordinadas às SPECs 052–060.
11. SPECs anteriores apenas quando não houver conflito.

## Próxima sequência subordinada

- `SPEC-061` — Portal Admin Control Plane;
- `SPEC-062` — Evals, Billing, Rollout & Production Readiness.

## SPEC-054 — auditoria e execução

- [`../audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md`](../audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md) — censo read-only do Supabase e da `main`, cobrindo schema vivo, migrations, RLS, funções, Storage, multi-tenancy, SSRF, MCP, Authority Strict, idempotência, performance, rollout e critérios de aceite.
- [`SPEC-054-foundation-hardening-schema-governance.md`](SPEC-054-foundation-hardening-schema-governance.md) — documento de implementação autorizado em três blocos macro, com APPLY/VERIFY/ROLLBACK e canário Amandus → Resulta → AutoFleet.

## SPEC-055 — execução durável de lançamento

- [`SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`](SPEC-055-durable-work-runs-queue-checkpoints-hitl.md) — documento de implementação autorizado em três blocos macro. Ao final, `work_runs` deve ser a autoridade universal ativa, o worker deve estar em produção e os caminhos de Rotinas, Auxiliares e Portais devem criar/atualizar Work Runs sem execução paralela.

A SPEC-055 não é um laboratório. Testes, canários e flags são gates internos da mesma entrega de lançamento e não justificam deixar a funcionalidade permanentemente desligada.

## SPEC-056 — Skills e Tool Gateway de lançamento

- [`SPEC-056-skill-registry-tool-gateway.md`](SPEC-056-skill-registry-tool-gateway.md) — documento de implementação autorizado em três blocos macro. Ao final, o Capability Registry existente continua como autoridade, o Skill Registry complementa a governança, o Tool Gateway é o único caminho de seleção/execução, Skills iniciais estão publicadas e native/HTTP/MCP/Portal/delegation não mantêm autorização paralela.

A SPEC-056 também não é um catálogo visual ou uma fase beta. A entrega só termina quando Skills reais forem usadas pelo Core e pelos Work Runs em produção.

## SPEC-057 — Artifact Hub e Report Studio de lançamento

- [`SPEC-057-artifact-hub-report-studio.md`](SPEC-057-artifact-hub-report-studio.md) — documento de implementação autorizado em três blocos macro. Ao final, artifacts são objetos de primeira classe, MinIO privado armazena bytes, Work Runs/Skills geram versões e renders, o Report Studio funciona pelo chat e os formatos web/PDF/XLSX/CSV/PPTX/DOCX/SVG/PNG/Evidence Pack estão ativos.

A SPEC-057 exige um **Visual Acceptance Pack** separado como referência de design, mas ele não é outro runtime, sistema ou SPEC. Nenhum template de lançamento é considerado final sem aprovação visual do Founder.

## SPEC-058 — Auxiliary & Routine Factory de lançamento

- [`SPEC-058-auxiliary-routine-factory.md`](SPEC-058-auxiliary-routine-factory.md) — documento de implementação autorizado em três blocos macro. Ao final, o Factory escolhe entre Work Run único, Rotina, Auxiliar, workflow, executor especializado ou Agent-backed; templates possuem releases; instalações possuem revisões; criação por chat e dashboard funciona; Rotinas acionam Work Runs; templates iniciais estão ativos.

A SPEC-058 revoga definitivamente a equivalência “Auxiliares = Rotinas”. Nem toda tarefa recorrente cria um novo Agent. O runtime padrão é Skill Release + Capability Pack + Work Run, com Agent dedicado apenas quando houver justificativa técnica.

## SPEC-059 — Briefing, Proatividade & Garimpo v3 de lançamento

- [`SPEC-059-briefing-proatividade-garimpo-v3.md`](SPEC-059-briefing-proatividade-garimpo-v3.md) — documento de implementação autorizado em três blocos macro. Ao final, o sistema opera o pipeline evento → sinal → evidência → Finding → recomendação → Work Run → outcome; Briefings Diário/Semanal estão ativos; Garimpo v3 captura demanda; quiet hours/dedupe/cooldown reduzem ruído; recomendações possuem ações reais e medição.

A SPEC-059 substitui a proatividade superficial como autoridade. `broker_insights.py`, `proactive_suggestions.py`, `weekly_report.py`, `regression_sentinel.py`, o Admin Insights histórico e seus schedulers diretos permanecem apenas como fontes/adapters até o cutover. Nenhum deles pode continuar como motor soberano concorrente.

## SPEC-060 — Research Intelligence de lançamento

- [`SPEC-060-research-intelligence.md`](SPEC-060-research-intelligence.md) — documento de implementação autorizado em três blocos macro. Ao final, o Research Orchestrator governa pesquisa rápida, verificada, profunda, site audit, business discovery, claim checking e monitors; Tavily e Firecrawl são providers homologados; fontes, snapshots, claims e citações são persistidos; artifacts e Intelligence Signals estão integrados.

A SPEC-060 não autoriza scraping irrestrito. Firecrawl é capability global da plataforma, não cérebro soberano. Descoberta de empresas deve usar Places API/provider permitido, sem scraping da interface do Google Maps. `TavilyService` e `WebSearchTool` históricos permanecem apenas como adapters até o cutover.

## SPECs parcialmente superadas

As seguintes SPECs permanecem disponíveis como histórico e detalhamento técnico, mas não são mais autoridade soberana quando houver conflito:

### Arquitetura cognitiva — prevalece SPEC-052

- `../SPEC-003-knowledge-rag-memory.md`;
- `../SPEC-004-agent-intelligence-context-architecture.md`;
- `../SPEC-008-producao-global-autobrokers.md`;
- `../SPEC-010-rag-knowledge-memory-curation-autobrokers-smith.md`;
- `SPEC-034-harness-robusto-multiagente-atendimento.md`;
- `SPEC-040-ESPELHO-VISAO-OPERACIONAL-E-CENTRAL-COMPLETA.md` e documentos relacionados;
- `SPEC-044-tres-camadas-global-corretora-usuario.md`.

### Work OS — prevalece SPEC-053

- seções históricas de `SPEC-034` sobre harness quando conflitarem com Work Runs, Tool Gateway, Skills, HITL ou execução durável.

### Auxiliares e Rotinas — prevalece SPEC-058

- `../SPEC-002-auxiliares-runtime-smith.md` continua como fundação histórica de Auxiliares sobre Smith, mas a SPEC-058 prevalece em releases, instalações, revisões, Factory, criação, lifecycle e runtime padrão;
- `SPEC-019-rotinas-auxiliares-claude-parity.md` continua como fundação histórica do scheduler e tools conversacionais, mas a equivalência antiga entre Auxiliares e Rotinas está revogada;
- `UX-007-auxiliares.md` continua como referência de produto, mas criação livre deixa de ser “futura” e passa a ser obrigação operacional da SPEC-058;
- criação automática de Agent por todo template, execução direta de prompt bruto por Rotina e runs paralelos deixam de ser autoridade após o cutover.

### Proatividade, Briefings e Garimpo — prevalece SPEC-059

- seções de SPEC-034/035/036/037/040/049 sobre Garimpo, sugestões, relatórios semanais, regressão e superfícies de Insights permanecem como fundação histórica;
- mensagem semanal fixa, relatório textual isolado, alerta direto fora de Work Run, ranking simples de frases e marcador Redis sem autoridade durável são superados pela SPEC-059;
- `broker_insights` permanece como origem/projeção temporária, não como registro canônico de inteligência após o cutover.

### Pesquisa, web search, crawling e monitors — prevalece SPEC-060

- `backend/app/services/tavily_service.py`, `backend/app/agents/tools/web_search.py`, menções históricas a busca web e a capability `platform.web.search` permanecem como fundação técnica;
- retorno textual de três resultados, attachment direto da tool ao grafo, ausência de claims/citações e Tavily como caminho soberano são superados pela SPEC-060;
- Firecrawl, Tavily, Places e futuros providers devem operar pelo Research Orchestrator + Tool Gateway, sem publisher, RAG, scheduler ou motor paralelo.

### Capabilities, Skills e tools — prevalece SPEC-056

- `../SPEC-014-capability-registry-knowledge-os.md` continua como fundação histórica do Registry, mas a SPEC-056 prevalece em Skill Releases, Capability Packs, Tool Definitions/Releases, seleção dinâmica, Tool Gateway e cutover das autoridades legadas;
- definições hardcoded de Portal Skills continuam como evidência histórica, não como catálogo canônico;
- autorização por `tools_config`, menção em prompt, row isolada de HTTP tool ou descoberta automática MCP é superada pelo Tool Gateway.

### Artifacts, relatórios e entregáveis — prevalece SPEC-057

- relatórios textuais históricos, exports isolados, PDFs avulsos e templates espalhados continuam como evidência, mas toda nova geração deve passar pelo Artifact Hub;
- `weekly_report.py` continua como compatibilidade de entrega até o cutover das SPECs 057/059, não como autoridade do relatório completo;
- componentes Recharts existentes podem permanecer em telas antigas, mas novos artifacts seguem o Chart Spec e renderer definidos pela SPEC-057.

## Regra para agentes de desenvolvimento

```text
Leia a SPEC-052 para conhecimento, memória, contexto e aprendizagem.
Leia a SPEC-053 para Work OS, Auxiliares, Rotinas, artifacts e Control Plane.
Leia a SPEC-054 antes de alterar schema, migrations, RLS, Storage,
service-role, HTTP egress, MCP sandbox, Authority Strict ou idempotência.
Leia a SPEC-055 antes de alterar Work Runs, fila, worker, checkpoint,
HITL, approvals, side effects ou integração de execução.
Leia a SPEC-056 antes de alterar Skills, capabilities, toolsets,
HTTP/MCP/native/Portal tools, subagentes ou seleção dinâmica.
Leia a SPEC-057 antes de alterar artifacts, relatórios, templates,
renderers, PDF/XLSX/PPTX/DOCX, gráficos, compartilhamento ou entrega.
Leia a SPEC-058 antes de alterar Auxiliares, Rotinas, templates,
instalações, revisões, criação pelo chat/dashboard, triggers ou catálogo.
Leia a SPEC-059 antes de alterar sinais, Findings, recomendações,
briefings, Garimpo, proatividade, Demand Radar, feedback ou outcomes.
Leia a SPEC-060 antes de alterar pesquisa, Tavily, Firecrawl, web search,
crawling, fontes, claims, citações, monitors, SEO/AEO ou business discovery.

Não crie RAG, memória, publisher, runtime, scheduler, executor,
Skill Registry, Tool Gateway, Artifact Hub, Auxiliary Factory,
Intelligence Fabric, Research Orchestrator, Garimpo ou motor paralelo.
Não use decisões históricas que contradigam as SPECs 052–060.
Em ambiguidade, pare e solicite decisão do CEO/Founder.
```

## Nome oficial

O chat principal e agente central do produto se chama **AutoBrokers**.

“Jarvys/Jarvis” é apenas uma metáfora externa para explicar a ambição de produto e não deve ser usado em UI, código de produto, agentes ou documentação canônica como nome oficial.