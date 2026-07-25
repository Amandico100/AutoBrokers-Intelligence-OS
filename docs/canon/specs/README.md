# Índice e autoridade das SPECs canônicas

> [!IMPORTANT]
> Para qualquer tarefa relacionada ao cérebro, Work OS, segurança, execução, Skills, tools, artifacts, Auxiliares, proatividade, pesquisa, Portal Admin, evals, billing, rollout ou lançamento do AutoBrokers, leia primeiro as SPECs **052** e **053** e depois siga a sequência até a autoridade específica do domínio.

## Autoridade atual

1. `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md` — arquitetura cognitiva soberana: conhecimento, memória, contexto, aprendizagem e cérebro unificado.
2. `SPEC-053-autobrokers-work-os-core-harness.md` — arquitetura soberana do Work OS: Core Harness, Skills, Tool Gateway, execução durável, Auxiliares, Rotinas, artifacts e Control Plane.
3. [`SPEC-054-foundation-hardening-schema-governance.md`](SPEC-054-foundation-hardening-schema-governance.md) — fechamento P0, Storage privado, baseline reproduzível, integridade multi-tenant, hardening de HTTP/MCP, Authority Strict e idempotência preparatória.
4. [`SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`](SPEC-055-durable-work-runs-queue-checkpoints-hitl.md) — Work Runs universais, Redis Streams, worker Smith, leases, checkpoints, HITL, approvals e side effects idempotentes.
5. [`SPEC-056-skill-registry-tool-gateway.md`](SPEC-056-skill-registry-tool-gateway.md) — Skill Registry, Capability Packs, Tool Releases, Tool Gateway único, seleção dinâmica e cutover das autoridades de tools legadas.
6. [`SPEC-057-artifact-hub-report-studio.md`](SPEC-057-artifact-hub-report-studio.md) — Artifact Hub, Report Studio, templates versionados, renderer determinístico, formatos profissionais, compartilhamento, entrega e Visual Acceptance Pack.
7. [`SPEC-058-auxiliary-routine-factory.md`](SPEC-058-auxiliary-routine-factory.md) — Factory único de Auxiliares e Rotinas, classificação de trabalho, criação pelo chat/dashboard, releases, instalações, revisões, triggers e lifecycle.
8. [`SPEC-059-briefing-proatividade-garimpo-v3.md`](SPEC-059-briefing-proatividade-garimpo-v3.md) — Intelligence Fabric único: sinais, evidências, Findings, recomendações, Briefings, Garimpo v3, Demand Radar, feedback e outcomes.
9. [`SPEC-060-research-intelligence.md`](SPEC-060-research-intelligence.md) — Research Intelligence único: providers, fontes, crawling, snapshots, Claims, citações, Evidence Packs, monitors e pesquisas verticais.
10. [`SPEC-061-portal-admin-control-plane.md`](SPEC-061-portal-admin-control-plane.md) — Control Plane Global: autenticação/RBAC server-side, Admin Command Gateway, Home/Inbox, Cockpits, administração das SPECs 052–060, segurança, auditoria e migração do Portal Admin histórico.
11. [`SPEC-062-evals-billing-rollout-production-readiness.md`](SPEC-062-evals-billing-rollout-production-readiness.md) — autoridade final de lançamento: evals, Release Evidence, CI/CD, SLOs, observabilidade, billing, planos, Usage/Credit Ledgers, reconciliação, margem, carga, backup/restore, onboarding, readiness, rollout e decisão de go-live.
12. SPECs futuras somente quando subordinadas às SPECs 052–062 e aprovadas pelo Founder.
13. SPECs anteriores apenas quando não houver conflito.

## Estado do programa 052–062

A sequência arquitetural está documentalmente completa.

O próximo passo não é criar automaticamente uma SPEC-063.

```text
Executar SPEC-054
→ executar SPEC-055
→ executar SPEC-056
→ executar SPEC-057
→ executar SPEC-058
→ executar SPEC-059
→ executar SPEC-060
→ executar SPEC-061
→ executar SPEC-062
→ emitir Launch Decision
```

Cada execução deve produzir relatório final, APPLY/VERIFY/ROLLBACK e evidência dos canários Amandus → Resulta → AutoFleet.

## SPEC-054 — auditoria e execução

- [`../audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md`](../audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md) — censo read-only do Supabase e da `main`.
- [`SPEC-054-foundation-hardening-schema-governance.md`](SPEC-054-foundation-hardening-schema-governance.md) — implementação autorizada em três blocos, com fechamento P0, schema reproduzível e hardening.

## SPEC-055 — execução durável

- [`SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`](SPEC-055-durable-work-runs-queue-checkpoints-hitl.md) — Work Runs como autoridade universal, worker Smith em produção e integração de Rotinas, Auxiliares e Portais.

A SPEC-055 não é laboratório. Flags e canários são gates internos da entrega.

## SPEC-056 — Skills e Tool Gateway

- [`SPEC-056-skill-registry-tool-gateway.md`](SPEC-056-skill-registry-tool-gateway.md) — Capability Registry preservado, Skills versionadas, Tool Gateway único e biblioteca inicial ativa.

Tools native/HTTP/MCP/Portal/delegation não podem manter autorização paralela após o cutover.

## SPEC-057 — Artifact Hub e Report Studio

- [`SPEC-057-artifact-hub-report-studio.md`](SPEC-057-artifact-hub-report-studio.md) — artifacts como objetos de primeira classe, MinIO privado, Report Studio e formatos web/PDF/XLSX/CSV/PPTX/DOCX/SVG/PNG/Evidence Pack.

Exige **Visual Acceptance Pack** separado, subordinado à arquitetura e aprovado pelo Founder.

## SPEC-058 — Auxiliary & Routine Factory

- [`SPEC-058-auxiliary-routine-factory.md`](SPEC-058-auxiliary-routine-factory.md) — Factory escolhe Work Run único, Rotina, Auxiliar, workflow, executor especializado ou Agent-backed.

A equivalência histórica “Auxiliares = Rotinas” está revogada. O runtime padrão é Skill Release + Capability Pack + Work Run.

## SPEC-059 — Briefing, Proatividade & Garimpo v3

- [`SPEC-059-briefing-proatividade-garimpo-v3.md`](SPEC-059-briefing-proatividade-garimpo-v3.md) — pipeline evento → sinal → evidência → Finding → recomendação → Work Run → outcome.

`broker_insights.py`, `proactive_suggestions.py`, `weekly_report.py`, `regression_sentinel.py` e schedulers históricos são apenas fontes/adapters até o cutover.

## SPEC-060 — Research Intelligence

- [`SPEC-060-research-intelligence.md`](SPEC-060-research-intelligence.md) — Research Orchestrator governa pesquisa rápida, verificada, profunda, site audit, business discovery, claim checking e monitors.

Firecrawl é capability global, não cérebro soberano. Empresas usam Places API/provider permitido, sem scraping da interface do Google Maps.

## SPEC-061 — Portal Admin Control Plane

- [`SPEC-061-portal-admin-control-plane.md`](SPEC-061-portal-admin-control-plane.md) — `/admin` exclusivo do Control Plane Global, `/dashboard` para corretoras, permissions server-side, Admin Command Gateway e administração completa.

`localStorage`, redirects client-side, modais técnicas extensas e páginas que espelham tabelas não podem continuar como autoridades de autenticação, permissão ou produto.

## SPEC-062 — Evals, Billing, Rollout & Production Readiness

- [`SPEC-062-evals-billing-rollout-production-readiness.md`](SPEC-062-evals-billing-rollout-production-readiness.md) — programa final de implementação e lançamento em três blocos: Release Evidence; Billing/Unit Economics; Resiliência/Onboarding/Go-Live.

Regras invioláveis:

- Usage Event não é automaticamente cobrança.
- Provider cost não é automaticamente preço ao cliente.
- Os 1.235 logs históricos auditados não podem ser cobrados retroativamente por automação.
- O boundary comercial deve ser explícito.
- Billing deve ser append-only, idempotente e reconciliável.
- Backup somente é aceito após restore comprovado.
- `GO` exige evidências, zero P0/P1 e aprovação do Founder.

## SPECs parcialmente superadas

### Arquitetura cognitiva — prevalece SPEC-052

- `../SPEC-003-knowledge-rag-memory.md`;
- `../SPEC-004-agent-intelligence-context-architecture.md`;
- `../SPEC-008-producao-global-autobrokers.md`;
- `../SPEC-010-rag-knowledge-memory-curation-autobrokers-smith.md`;
- `SPEC-034-harness-robusto-multiagente-atendimento.md`;
- `SPEC-040-ESPELHO-VISAO-OPERACIONAL-E-CENTRAL-COMPLETA.md`;
- `SPEC-044-tres-camadas-global-corretora-usuario.md`.

### Work OS — prevalece SPEC-053

- seções históricas de SPEC-034 sobre harness quando conflitarem com Work Runs, Skills, Tool Gateway, HITL ou execução durável.

### Auxiliares e Rotinas — prevalece SPEC-058

- `../SPEC-002-auxiliares-runtime-smith.md` permanece como fundação histórica;
- `SPEC-019-rotinas-auxiliares-claude-parity.md` permanece como fundação do scheduler histórico;
- `UX-007-auxiliares.md` permanece como referência de produto;
- criação de Agent para todo template, prompt bruto por Rotina e runs paralelos deixam de ser autoridade.

### Proatividade e Garimpo — prevalece SPEC-059

- decisões históricas das SPECs 034/035/036/037/040/049 permanecem como fundação;
- mensagem semanal fixa, relatório textual isolado, alerta fora de Work Run e ranking simples são superados;
- `broker_insights` é origem/projeção temporária, não registro canônico final.

### Pesquisa — prevalece SPEC-060

- `TavilyService`, `WebSearchTool` e a capability histórica `platform.web.search` são adapters até o cutover;
- retorno textual curto sem Claims/citações e tool anexada diretamente ao grafo deixam de ser autoridade.

### Portal Admin — prevalece SPEC-061

- SPEC-036, UX-001, DS-001, relatórios Claude Design, screenshots e páginas atuais são evidências históricas/visuais;
- Admin compartilhado com company admins, sessão client-side, health inferido localmente e páginas isoladas são superados.

### Capabilities, Skills e tools — prevalece SPEC-056

- SPEC-014 permanece como fundação histórica do Capability Registry;
- definitions hardcoded de Portal Skills e autorização por prompt/tools_config deixam de ser autoridade.

### Artifacts — prevalece SPEC-057

- relatórios textuais, exports isolados, PDFs avulsos, templates espalhados e Recharts de telas históricas são evidência/compatibilidade, não autoridade dos novos entregáveis.

### Evals, FinOps, billing e readiness — prevalece SPEC-062

- runners independentes, `conversation_scorecards`, regression sentinel, relatórios históricos de FinOps, `token_usage_logs.billed`, `company_credits.balance_brl`, multiplicador único e readiness baseado em poucos booleanos permanecem como fundação/adapters;
- nenhum deles isoladamente pode aprovar release, gerar invoice, decidir margem ou autorizar go-live;
- custo técnico, preço comercial, créditos, assinaturas, invoices e pagamentos devem passar pelo ledger/reconciliação da SPEC-062.

## Regra para agentes de desenvolvimento

```text
Leia SPEC-052 para conhecimento, memória, contexto e aprendizagem.
Leia SPEC-053 para Work OS e arquitetura geral.
Leia SPEC-054 antes de alterar schema, segurança, Storage, HTTP/MCP ou Authority.
Leia SPEC-055 antes de alterar Work Runs, fila, worker, HITL ou side effects.
Leia SPEC-056 antes de alterar Skills, capabilities, tools, MCPs ou subagentes.
Leia SPEC-057 antes de alterar artifacts, relatórios, renderers ou entregas.
Leia SPEC-058 antes de alterar Auxiliares, Rotinas, Factory, triggers ou catálogo.
Leia SPEC-059 antes de alterar sinais, Findings, Briefings, Garimpo ou outcomes.
Leia SPEC-060 antes de alterar pesquisa, crawling, fontes, Claims ou monitors.
Leia SPEC-061 antes de alterar /admin, RBAC, Control Plane, Cockpits ou comandos.
Leia SPEC-062 antes de alterar evals, CI/CD, SLOs, pricing, billing, créditos,
assinaturas, reconciliação, margem, backup/restore, onboarding, readiness,
rollout ou autorização de lançamento.

Não crie RAG, memória, publisher, runtime, scheduler, executor,
Skill Registry, Tool Gateway, Artifact Hub, Auxiliary Factory,
Intelligence Fabric, Research Orchestrator, Control Plane,
Eval Platform, Billing Engine, Ledger ou Readiness Engine paralelo.
Não use decisões históricas que contradigam as SPECs 052–062.
Em ambiguidade material, pare e solicite decisão do CEO/Founder.
```

## Nome oficial

O chat principal e agente central do produto se chama **AutoBrokers**.

“Jarvys/Jarvis” é apenas metáfora externa e não deve aparecer em UI, código ou documentação canônica como nome oficial.
