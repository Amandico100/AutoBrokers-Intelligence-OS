---
> **Status:** canonical  
> **Versão:** 2.4 — programa 052–062 completo, Lotes da SPEC-052 mapeados e execução governada  
> **Última atualização:** 2026-07-25  
> **Produto:** AutoBrokers.ai  
> **Sistema:** AutoBrokers Intelligence OS  
> **Função:** índice principal da documentação canônica ativa
---

# AutoBrokers Intelligence OS Canon

Esta pasta é a fonte de verdade documental ativa do AutoBrokers.ai.

## Governança de execução

Antes de qualquer implementação, leia nesta ordem:

| Documento | Função |
| --- | --- |
| [`../../CLAUDE.md`](../../CLAUDE.md) | regras invioláveis de processo; porta de entrada de toda sessão |
| [`EXECUTION-MASTER-PLAN.md`](EXECUTION-MASTER-PLAN.md) | onde estamos, o que vem a seguir, gates e estado por etapa |
| [`FOUNDER-DECISIONS.md`](FOUNDER-DECISIONS.md) | decisões do Founder — append-only |
| [`MIGRATIONS-AUTHORITY.md`](MIGRATIONS-AUTHORITY.md) | **obrigatório antes de qualquer SQL** — o repositório não é a fonte completa do schema |
| [`CHANGE-ADDENDA.md`](CHANGE-ADDENDA.md) | mudanças além do texto literal das SPECs |
| [`reports/SPEC-EXECUTION-REPORT-TEMPLATE.md`](reports/SPEC-EXECUTION-REPORT-TEMPLATE.md) | template obrigatório de relatório final por SPEC |

## Autoridade soberana atual

1. [`specs/SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`](specs/SPEC-052-cerebro-cognitivo-unificado-autobrokers.md)  
   Governa conhecimento, RAG, memória, Context Assembly, aprendizagem e o cérebro cognitivo unificado.  
   Mapa executor dos Lotes 1–5: [`specs/ADDENDUM-SPEC-052-EXECUTION-MAP.md`](specs/ADDENDUM-SPEC-052-EXECUTION-MAP.md).

2. [`specs/SPEC-053-autobrokers-work-os-core-harness.md`](specs/SPEC-053-autobrokers-work-os-core-harness.md)  
   Governa o Work OS: Core Harness, Skills, Tool Gateway, execução durável, Auxiliares, Rotinas, approvals, artifacts e Control Plane.

3. [`specs/SPEC-054-foundation-hardening-schema-governance.md`](specs/SPEC-054-foundation-hardening-schema-governance.md)  
   Governa fechamento P0, Storage privado, baseline reproduzível, integridade multi-tenant, HTTP/MCP hardening, Authority Strict e idempotência preparatória.

4. [`specs/SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`](specs/SPEC-055-durable-work-runs-queue-checkpoints-hitl.md)  
   Governa Work Runs universais, fila, worker Smith, leases, checkpoints, HITL, approvals e execução durável.

5. [`specs/SPEC-056-skill-registry-tool-gateway.md`](specs/SPEC-056-skill-registry-tool-gateway.md)  
   Governa Skill Registry, Capability Packs, Tool Releases, Tool Gateway único e seleção dinâmica.

6. [`specs/SPEC-057-artifact-hub-report-studio.md`](specs/SPEC-057-artifact-hub-report-studio.md)  
   Governa Artifact Hub, Report Studio, templates, renderer, relatórios, arquivos, gráficos, Evidence Packs, compartilhamento e entrega.

7. [`specs/SPEC-058-auxiliary-routine-factory.md`](specs/SPEC-058-auxiliary-routine-factory.md)  
   Governa a fábrica única de Auxiliares e Rotinas, releases, instalações, revisões, criação pelo chat/dashboard, triggers e lifecycle.

8. [`specs/SPEC-059-briefing-proatividade-garimpo-v3.md`](specs/SPEC-059-briefing-proatividade-garimpo-v3.md)  
   Governa o Intelligence Fabric: sinais, evidências, Findings, recomendações, Briefings, Garimpo v3, Demand Radar, feedback e outcomes.

9. [`specs/SPEC-060-research-intelligence.md`](specs/SPEC-060-research-intelligence.md)  
   Governa Research Intelligence: providers, fontes, crawling, snapshots, Claims, citações, Evidence Packs, monitors e pesquisas verticais.

10. [`specs/SPEC-061-portal-admin-control-plane.md`](specs/SPEC-061-portal-admin-control-plane.md)  
    Governa o Portal Admin Global como Control Plane único: autenticação/RBAC, Admin Command Gateway, Home/Inbox, Cockpits, operação, inteligência, conexões, conhecimento, financeiro, segurança, auditoria e Support Access.

11. [`specs/SPEC-062-evals-billing-rollout-production-readiness.md`](specs/SPEC-062-evals-billing-rollout-production-readiness.md)  
    Governa a evidência final de lançamento: evals, Release Candidates, CI/CD, SLOs, observabilidade, Usage/Credit Ledgers, pricing, planos, assinaturas, invoices, reconciliação, margem, carga, backup/restore, onboarding, readiness, rollout e go-live.

12. SPECs futuras somente quando subordinadas às SPECs 052–062 e aprovadas pelo Founder.

13. ADRs, SPECs e relatórios históricos apenas quando não houver conflito.

Leia também o índice detalhado em [`specs/README.md`](specs/README.md).

## Estado do programa

A arquitetura 052–062 está documentalmente completa e os Lotes 1–5 da SPEC-052 receberam dono executor pela decisão **D1**.

```text
Documentação aprovada
→ Fase 0: contexto persistente e correções canônicas
→ execução SPEC-054 a SPEC-062, com os enxertos aprovados
→ relatório final por SPEC
→ Launch Decision
→ go-live e comercialização
```

A sequência autorizada, com dependências, gates e estado por etapa, está em [`EXECUTION-MASTER-PLAN.md`](EXECUTION-MASTER-PLAN.md).

Não criar automaticamente SPEC-063 apenas para adiar a implementação. Os Lotes 1–5 da SPEC-052 são executados dentro das SPECs existentes e do pacote **SPEC-052 Cognitive Foundation Closure**, conforme [`specs/ADDENDUM-SPEC-052-EXECUTION-MAP.md`](specs/ADDENDUM-SPEC-052-EXECUTION-MAP.md).

## Separação oficial

- **AutoBrokers.ai** é o produto.
- **AutoBrokers** é o agente principal voltado ao corretor.
- **Smith** é o runtime técnico invisível.
- **Supabase** é a fonte durável da verdade operacional.
- **Redis** é transitório: fila, locks, leases e cache.
- **Qdrant** é índice semântico derivado.
- **MinIO** armazena documentos e artifacts.
- **Vault** governa segredos e conexões.
- **Capability Registry** governa poderes.
- **Skill Registry** governa procedimentos versionados.
- **Tool Gateway** governa seleção e execução das ferramentas.
- **Work Runs** governam execuções duráveis.
- **Artifact Hub** governa resultados, versões, renders, compartilhamento e entrega.
- **Auxiliary Factory** governa proposta, instalação, revisão, lifecycle e composição de Auxiliares/Rotinas.
- **Intelligence Fabric** governa eventos, sinais, evidências, Findings, recomendações, Briefings, demanda e outcomes.
- **Research Intelligence** governa planos de pesquisa, providers, fontes, snapshots, Claims, citações, monitors e Evidence Packs.
- **Portal Admin Control Plane** governa administração global, permissions, read models, comandos, Cockpits e auditoria.
- **Release Evidence Fabric** governa datasets, evaluators, Release Candidates, quality gates e decisão de release.
- **Usage Ledger** governa consumo comercial idempotente.
- **Credit Ledger** governa créditos, consumo, bônus, refunds, adjustments e reversals.
- **Billing Reconciliation** governa coerência entre uso, rating, invoices e pagamentos.
- **Production Readiness** governa evidência para `GO`, `GO_CONDITIONAL` ou `NO_GO`.
- **ResultVision / Agent OS histórico** são referências de domínio, não runtimes ativos.

## Leis centrais

```text
Um único cérebro lógico.
Um único runtime Smith.
Nenhum RAG, memória, publisher, scheduler ou executor paralelo.
Auxiliar é trabalhador de produto.
Rotina é gatilho.
Skill é procedimento versionado.
Capability é poder governável.
Tool é implementação.
Work Run é execução.
Artifact é resultado de primeira classe.
Signal é indício normalizado com evidência.
Finding separa fato de inferência.
Recommendation é proposta governada, não execução.
Outcome não medido é inconclusivo, não sucesso.
Research Claim precisa de fonte e validade.
Citation liga afirmação à evidência.
Pesquisa não publica conhecimento diretamente.
Provider externo não é autoridade soberana.
Firecrawl é capability da plataforma, não cérebro.
Descoberta de empresas usa API/provider permitido, não scraping de Google Maps UI.
Nem toda tarefa recorrente vira um Agent.
Auxiliary Factory escolhe o menor padrão de trabalho adequado.
Proatividade exige evidência, relevância, dedupe, cooldown e respeito ao usuário.
Toda ação recomendada é executada pelo Work OS quando autorizada.
Garimpo captura demanda, mas não publica conhecimento diretamente.
/admin é Control Plane Global da equipe AutoBrokers.
/dashboard é a superfície das corretoras.
Frontend e localStorage nunca são autoridade de papel ou permission.
Toda ação administrativa relevante passa pelo Admin Command Gateway e audit trail.
Support Access é explícito, temporário e rastreável.
Portal Admin não cria autoridade de domínio paralela.
Usage Event não é automaticamente cobrança.
Provider cost não é automaticamente preço ao cliente.
Billing é append-only, idempotente e reconciliável.
Uso histórico pre-launch não vira dívida automática.
Backup somente é aceito depois de restore comprovado.
Release sem Evidence Pack não recebe GO.
P0 de segurança ou cross-tenant bloqueia rollout.
Modelo latest não muda comportamento crítico silenciosamente.
Vault governa segredos.
Capability Registry governa acesso.
Tool Gateway governa todas as famílias de tools.
Artifact Hub governa todos os novos entregáveis.
Intelligence Fabric governa sinais, Findings, recomendações, Briefings e outcomes.
Research Intelligence governa busca, crawling, Claims, citações e monitors.
Portal Admin Control Plane governa administração e comandos seguros.
Release Evidence Fabric governa evals e gates.
Usage/Credit Ledgers governam uso e saldo comercial.
Supabase guarda metadata e autoridade; MinIO privado guarda bytes.
Schema e migrations são governados pela SPEC-054.
```

## Documentos canônicos principais

| Documento | Propósito |
| --- | --- |
| `PRD-001-visao-produto.md` | Visão de produto, público, módulos e naming. |
| `ADR-001-runtime.md` | Runtime oficial e fronteiras entre produto, Smith e domínio. |
| `ADR-002-vault.md` | Vault, credenciais, PII e dados sensíveis. |
| `ADR-003-atendimento.md` | Atendimento e migração curada de domínio. |
| `UX-001-navegacao.md` | Navegação histórica, subordinada à SPEC-061 para o Control Plane. |
| `DS-001-design-brief.md` | Direção visual histórica, subordinada aos Visual Acceptance Packs. |
| `UX-007-auxiliares.md` | UX histórica de Auxiliares, subordinada à SPEC-058. |
| `SPEC-002-auxiliares-runtime-smith.md` | Fundação histórica de Auxiliares sobre Smith. |
| `SPEC-005-atendimento-runtime-architecture.md` | Atendimento, casos, corredores, Evidence Pack e HITL. |
| `SPEC-006-allianz-residencial-corredor-eletricista-mvp.md` | Corredor Allianz Residencial/Eletricista. |
| `SPEC-014-capability-registry-knowledge-os.md` | Fundação histórica do Capability Registry. |
| `specs/SPEC-019-rotinas-auxiliares-claude-parity.md` | Fundação histórica do motor de Rotinas. |
| `specs/SPEC-036-auditoria-e-plano-portal-admin.md` | Auditoria histórica do Portal Admin. |
| `specs/SPEC-051-evolution-go-pareamento-passkey-observador.md` | Evolution Go, QR/passkey e Observador silencioso. |
| `specs/SPEC-052-cerebro-cognitivo-unificado-autobrokers.md` | Cérebro cognitivo unificado. |
| `specs/SPEC-053-autobrokers-work-os-core-harness.md` | Work OS e Harness avançado. |
| `specs/SPEC-054-foundation-hardening-schema-governance.md` | Hardening e schema governance. |
| `audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md` | Auditoria read-only da fundação. |
| `specs/SPEC-055-durable-work-runs-queue-checkpoints-hitl.md` | Execução durável. |
| `specs/SPEC-056-skill-registry-tool-gateway.md` | Skills e Tool Gateway. |
| `specs/SPEC-057-artifact-hub-report-studio.md` | Artifacts e Report Studio. |
| `specs/SPEC-058-auxiliary-routine-factory.md` | Factory de Auxiliares e Rotinas. |
| `specs/SPEC-059-briefing-proatividade-garimpo-v3.md` | Intelligence Fabric, Briefings e Garimpo v3. |
| `specs/SPEC-060-research-intelligence.md` | Research Intelligence. |
| `specs/SPEC-061-portal-admin-control-plane.md` | Portal Admin Control Plane. |
| `specs/SPEC-062-evals-billing-rollout-production-readiness.md` | Evals, billing, unit economics, resiliência, readiness e go-live. |
| `runbooks/RUNBOOK-PAREAMENTO-WHATSAPP-CORRETORA.md` | Pareamento de corretoras. |
| `runbooks/RUNBOOK-PASSKEY-WHATSAPP.md` | Fluxo de passkey. |
| `runbooks/RUNBOOK-EVOLUTION-GO-POOL-POSTGRES.md` | Diagnóstico do pool Postgres Evolution Go. |

## Documentos parcialmente superados

As SPECs 003, 004, 008, 010, 034, 040 e 044 continuam como histórico, mas a SPEC-052 prevalece em arquitetura cognitiva.

As SPECs 002 e 019 e o UX-007 continuam como fundação histórica, mas a SPEC-058 prevalece em Auxiliares, Rotinas, Factory, releases, instalações, revisões, criação e lifecycle.

A SPEC-014 continua como fundação do Capability Registry, mas a SPEC-056 prevalece em Skill Releases, Capability Packs, Tool Releases, seleção e Tool Gateway.

Relatórios textuais, exports, PDFs avulsos e templates espalhados continuam como evidência histórica, mas a SPEC-057 prevalece em Artifact Hub e Report Studio.

As decisões históricas das SPECs 034/035/036/037/040/049 sobre Garimpo, sugestões, relatório semanal e regressão permanecem como fundação; a SPEC-059 prevalece em Intelligence Fabric e cutover.

`TavilyService`, `WebSearchTool` e a capability histórica `platform.web.search` permanecem como adapters; a SPEC-060 prevalece em Research Intelligence.

SPEC-036, UX-001, DS-001, relatórios Claude Design, screenshots e páginas atuais permanecem como fundação; a SPEC-061 prevalece em `/admin`, RBAC, Control Plane, Cockpits, comandos, auditoria e cutover.

Runners independentes, `conversation_scorecards`, regression sentinel, relatórios históricos de FinOps, `token_usage_logs.billed`, `company_credits.balance_brl`, multiplicadores genéricos e readiness baseada em poucos booleanos permanecem como fundação/adapters; a SPEC-062 prevalece em Release Evidence, billing, ledgers, reconciliação, margem, resiliência, onboarding, rollout e go-live.

## Regra operacional

Quando documentos canônicos divergirem:

```text
SPEC-052
→ SPEC-053
→ SPEC-054 para schema e segurança
→ SPEC-055 para execução durável
→ SPEC-056 para Skills, capabilities e tools
→ SPEC-057 para artifacts e entregas
→ SPEC-058 para Auxiliares e Rotinas
→ SPEC-059 para Intelligence Fabric
→ SPEC-060 para Research Intelligence
→ SPEC-061 para Portal Admin Control Plane
→ SPEC-062 para evals, billing, resiliência, readiness e go-live
→ SPEC futura explicitamente subordinada
→ ADR aplicável
→ documento histórico
```

Em ambiguidade material, o agente deve solicitar validação do CEO/Founder.
