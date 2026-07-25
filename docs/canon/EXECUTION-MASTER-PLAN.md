---
> **Status:** canônico — plano mestre vivo
> **Versão:** 1.0 · **Criado em:** 25/07/2026
> **Commit base auditado:** `3c8c75279d802af0a734b7e7447cc18d469e4f85`
> **Worktree de execução:** `AutoBrokers-Opus-Exec`
> **Função:** responder, em segundos e para qualquer sessão futura, **onde estamos** e **o que vem a seguir**
---

# Execution Master Plan — AutoBrokers Intelligence OS

## Como usar este documento

1. É o **primeiro arquivo** lido em toda sessão de execução, junto com [`FOUNDER-DECISIONS.md`](FOUNDER-DECISIONS.md).
2. O executor **atualiza a tabela de estado** ao iniciar e ao concluir cada etapa. É obrigação, não cortesia.
3. Estados: `NÃO INICIADO` · `EM EXECUÇÃO` · `EM GATE` · `CONCLUÍDO` · `BLOQUEADO`.
4. Um gate verde permite avançar **automaticamente**. Ver [`FOUNDER-DECISIONS.md#d6`](FOUNDER-DECISIONS.md) — não há aprovação manual entre blocos.
5. Uma etapa `BLOQUEADO` exige entrada correspondente em [`FOUNDER-DECISIONS.md`](FOUNDER-DECISIONS.md).

---

## Painel de estado

| # | Etapa | Branch | Estado | Commit inicial | Commit final | Relatório |
|---|---|---|---|---|---|---|
| 0 | Contexto persistente e correções canônicas | `chore/execution-foundation` | **EM EXECUÇÃO** | `3c8c752` | — | este documento + Fase 0 |
| 1 | SPEC-054 Bloco A — Fechamento P0 | `feat/spec054-foundation-hardening` | NÃO INICIADO | — | — | — |
| 2 | SPEC-054 Blocos B/C — Baseline, Lote 1, memória | `feat/spec054-foundation-hardening` | NÃO INICIADO | — | — | — |
| 3 | SPEC-055 — Work Runs, usage events, ponte Atendimento | `feat/spec055-durable-work-runs` | NÃO INICIADO | — | — | — |
| 4 | SPEC-061 Fundação (antecipada) | `feat/spec061-control-plane-foundation` | NÃO INICIADO | — | — | — |
| 5 | SPEC-056 — Skills, Tool Gateway, Context Assembly 2.0 | `feat/spec056-skill-tool-gateway` | NÃO INICIADO | — | — | — |
| 6 | SPEC-057 — Artifact Hub & Report Studio | `feat/spec057-artifact-hub` | NÃO INICIADO | — | — | — |
| 7 | SPEC-052 Cognitive Foundation Closure | `feat/spec052-cognitive-foundation-closure` | NÃO INICIADO | — | — | — |
| 8 | SPEC-058 — Auxiliary & Routine Factory | `feat/spec058-auxiliary-routine-factory` | NÃO INICIADO | — | — | — |
| 9 | SPEC-059 — Intelligence Fabric + Memory Fabric | `feat/spec059-intelligence-fabric` | NÃO INICIADO | — | — | — |
| 10 | SPEC-060 — Research Intelligence | `feat/spec060-research-intelligence` | NÃO INICIADO | — | — | — |
| 11 | SPEC-061 Blocos B/C — Control Plane completo | `feat/spec061-control-plane-full` | NÃO INICIADO | — | — | — |
| 12 | SPEC-062 — Evals, Billing, Resiliência, Rollout | `feat/spec062-evals-billing-readiness` | NÃO INICIADO | — | — | — |
| 13 | **Launch Decision** | — | NÃO INICIADO | — | — | — |

**Caminho crítico:** 1 → 2 → 3. Nada depois pode ser antecipado, porque tudo depende de execução durável existir.
**Paralelizável:** 6 e 7 não têm dependência de código entre si. 10 pode iniciar assim que 6 estiver em gate.

---

## Etapa 0 — Contexto persistente e correções canônicas

| Campo | Conteúdo |
|---|---|
| **Depende de** | auditoria global de 25/07/2026 aprovada |
| **Entrada** | `main` @ `3c8c752`, decisões D1–D10 do Founder |
| **Saída** | `CLAUDE.md`, Master Plan, Founder Decisions, Change Addenda, Migrations Authority, template de relatório, Addendum SPEC-052 |
| **Gate** | links válidos · nenhum conflito canônico aberto · worktree criado e limpo · commits lógicos |
| **Riscos** | nenhum — sem código, sem SQL, sem produção |
| **Decisões pendentes** | P1 (acessos de infraestrutura) — não bloqueia esta etapa |

Nesta etapa **não** se executa: migration, write no Supabase, alteração de bucket, deploy, merge na `main`.

---

## Etapa 1 — SPEC-054 Bloco A · Fechamento P0

| Campo | Conteúdo |
|---|---|
| **Depende de** | Etapa 0 · **preflight de infraestrutura** (P1) antes do primeiro write em produção |
| **Entrada** | SPEC-054 §7 · [auditoria SPEC-054](audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md) · [`MIGRATIONS-AUTHORITY.md`](MIGRATIONS-AUTHORITY.md) |
| **Saída** | grants revogados nas 6 RPCs críticas · `search_path` fixado · view `ucp_connection_summary` corrigida · buckets privados com signed URLs · backfill de paths |

**Estado confirmado na auditoria de 25/07/2026 — todos ABERTOS:**

| Item | Evidência |
|---|---|
| `get_user_for_login` executável por `anon`, retorna `password_hash` | banco vivo |
| `create_user_account` (2 overloads) executável por `anon` | banco vivo |
| `debit_company_balance` executável por `anon` | banco vivo |
| `get_token_usage_by_company` / `get_token_usage_report` por `anon` | banco vivo |
| 17 funções com `search_path` mutável | advisor |
| `ucp_connection_summary` sem `security_invoker`, `SELECT` para `anon` | banco vivo |
| `chat-docs` (30 obj), `chat-media` (26 obj), `voice-messages`, `avatars` públicos | banco vivo |

**Gate 1**

- advisors de segurança sem nenhum `ERROR`;
- nenhuma RPC interna crítica executável por `anon`/`authenticated`;
- login, signup, upload de documento, envio de mídia e voz verdes;
- WhatsApp inbound/outbound sem regressão;
- APPLY/VERIFY/ROLLBACK escritos por migration.

**Riscos**

| Risco | Mitigação |
|---|---|
| Revogar RPC quebra login/signup | confirmar que todas as chamadas são server-side com service role; teste antes/depois |
| Fechar bucket quebra links já enviados por WhatsApp | **inventário de URLs públicas → backfill → só então fechar** — ver P1 secundária 1 |

**Decisões pendentes:** P1 (acesso de infraestrutura + confirmação sobre URLs públicas).

---

## Etapa 2 — SPEC-054 Blocos B/C · Baseline, integridade, Lote 1 e memória

| Campo | Conteúdo |
|---|---|
| **Depende de** | Etapa 1 verde |
| **Entrada** | SPEC-054 §8 e §9 · manifesto de migrations |
| **Saída** | baseline reproduzível · FKs de company · constraints cross-company · **Lote 1 da SPEC-052** · **diagnóstico e correção da memória zerada** · HTTP Egress Guard · MCP env allowlist · Authority Strict em shadow · Broker Outcome Regression Pack v1 |

**Enxertos aprovados nesta etapa**

- **Lote 1 da SPEC-052** (D1): eliminar o segundo caminho global de RAG em [`backend/app/services/search_service.py:290-323`](../../backend/app/services/search_service.py#L290-L323), manter apenas `autobrokers_global`, reforçar filtros de validade, namespace, audience, visibility e provenance.
- **Lote 4 parcial** (D1): diagnosticar por que `user_memories = 0` e `session_summaries = 0` com 523 `conversation_logs` e `MemoryService` completo. É **defeito silencioso**, não backlog.

**Gate 2**

- ambiente vazio sobe do baseline sem erro;
- produção recebe incrementais sem drift destrutivo;
- FKs de company validadas, zero órfãos;
- teste real com dois tenants (`anon`, `authenticated` A, `authenticated` B, `service_role`, multiempresa);
- SSRF verde (loopback, RFC1918, metadata, redirect, DNS rebinding);
- MCP recebe apenas env allowlisted;
- **um único caminho global de recuperação** comprovado por teste;
- memória produzindo registros reais **ou** causa raiz documentada com plano;
- Broker Outcome Regression Pack executável por um comando.

**Riscos:** baseline recriar objeto diferente do vivo · RLS bloquear rota legítima · Authority Strict remover tool necessária. Mitigação: diff de DDL, shadow mode, canário Amandus.

---

## Etapa 3 — SPEC-055 · Work Runs, fila, HITL, usage events, ponte Atendimento

| Campo | Conteúdo |
|---|---|
| **Depende de** | Etapa 2 verde |
| **Entrada** | SPEC-055 integral · contratos da SPEC-053 §9 |
| **Saída** | `work_runs`, `work_steps`, `work_attempts`, `work_events`, `work_effects`, `work_queue_outbox` · Redis Streams · Smith Worker dedicado · leases e heartbeat · thread `work:{company}:{run}` separada · HITL real com interrupt · bridges de Rotinas, Auxiliares e Portal Worker · **usage events append-only** · **ponte Atendimento/corredores** |

**Enxertos aprovados**

- **D4** — write-path técnico de usage events, marcado `PRE_LAUNCH_NON_BILLABLE`. **Sem** preço, plano, invoice, cobrança ou overage.
- **D1** — ponte Atendimento/corredores para Work Runs, **preservando** as restrições da SPEC-053 §5.2: corredor definido, menor privilégio, Evidence Pack, sem ferramentas genéricas de gestão.

**Problemas atuais que esta etapa fecha**

- scheduler de rotinas rodando in-process em [`backend/app/main.py:83`](../../backend/app/main.py#L83);
- `thread_id` único `{company}:{session}` em [`backend/app/agents/graph.py:841`](../../backend/app/agents/graph.py#L841);
- ausência total de `interrupt()` no backend — approval hoje não é gate;
- duas histórias de execução (`auxiliary_runs`, `routine_runs`).

**Gate 3**

- trabalho sobrevive a restart do worker e da API;
- side effect com mesma chave idempotente executa **uma** vez;
- approval bloqueia de fato e resume retoma do último checkpoint válido;
- cancelamento não desfaz ação externa já confirmada, e registra o ponto alcançado;
- rotina e auxiliar executam por Work Run sem duplicar histórico;
- usage event gravado para todo run, step e tool call.

**Riscos:** duplicação de side effect durante o cutover de rotinas · perda de run em recuperação de lease. Mitigação: dual-write temporário, reconciliador, replay tests.

---

## Etapa 4 — SPEC-061 Fundação (antecipada)

| Campo | Conteúdo |
|---|---|
| **Depende de** | Etapa 3 verde |
| **Entrada** | SPEC-061 §5 a §9 e §22 · decisão **D3** |
| **Saída** | autenticação admin server-side · RBAC e permissions · Control Plane BFF · Admin Command Gateway · shell e navegação · audit trail de comandos |

**Fora desta etapa:** Home executiva, Admin Inbox, Cockpits 360º, Hubs completos, migração das 33 páginas históricas — permanecem na Etapa 11.

**Motivo da antecipação (D3):** as superfícies administrativas das SPECs 056–060 nascem diretamente no Control Plane definitivo, e o risco de autoridade em `localStorage` fecha cedo.

**Gate 4**

- nenhuma rota ou comando admin decide papel no cliente;
- `localStorage` não concede acesso — alteração manual não muda nada;
- todo comando administrativo passa pelo Gateway e gera audit trail;
- `/admin` e `/dashboard` com fronteira declarada (migração completa fica na Etapa 11).

---

## Etapa 5 — SPEC-056 · Skills, Tool Gateway e Context Assembly 2.0

| Campo | Conteúdo |
|---|---|
| **Depende de** | Etapas 3 e 4 verdes |
| **Entrada** | SPEC-056 integral · **Lote 3 da SPEC-052** (D1) |
| **Saída** | `skills`, `skill_releases`, `capability_packs`, `tool_definitions`, `tool_releases`, `tool_invocations` · Tool Gateway único · progressive disclosure · biblioteca inicial de Skills · **Outcome Router, Context Planner, Evidence Builder** |

**Enxerto aprovado (D1 · Lote 3):** o Context Assembly 2.0 é irmão natural do Skill Resolver e vive no Bloco B desta SPEC — Outcome/Intent Router, Context Planner, Evidence Builder, precedência, deduplicação, orçamento de contexto e model routing.

**Gate 5**

- Core recebe **apenas** as tools do Capability Pack da Skill selecionada;
- `tools_config` deixa de ser autoridade; `AUTHORITY_STRICT_MODE` validado em canário;
- `scope` preenchido para toda capability sensível (hoje 46 bindings com `scope = {}`);
- entitlements por tenant existentes (hoje zero);
- Evidence Pack com provenance chega ao modelo;
- nenhuma família de tools mantém autorização paralela após o cutover.

---

## Etapa 6 — SPEC-057 · Artifact Hub & Report Studio

| Campo | Conteúdo |
|---|---|
| **Depende de** | Etapa 5 verde |
| **Entrada** | SPEC-057 integral |
| **Saída** | Artifact Registry, Template Registry, renderers, Chart Service · web report, PDF, XLSX, CSV, PPTX, DOCX, SVG/PNG, Evidence Pack · share links, expiração, revogação · delivery multicanal · Report Studio |

**Gate 6**

- **Visual Acceptance Pack aprovado pelo Founder** — gate humano, obrigatório;
- relatório executivo real ponta a ponta, com números conferidos contra a fonte;
- cálculo determinístico separado de narrativa da LLM, com verificação;
- nenhuma URL interna do MinIO exposta; links autenticados por padrão;
- prefixo de storage por tenant; tenant A não lê artifact do tenant B.

**Riscos:** escopo de formatos é grande. **D5 proíbe reduzi-lo unilateralmente** — se houver dificuldade, completar o restante e registrar em `CHANGE-ADDENDA.md`.

---

## Etapa 7 — SPEC-052 Cognitive Foundation Closure

| Campo | Conteúdo |
|---|---|
| **Depende de** | Etapa 6 (pode correr em paralelo — sem dependência de código) |
| **Entrada** | SPEC-052 §7 e §16 · [`specs/ADDENDUM-SPEC-052-EXECUTION-MAP.md`](specs/ADDENDUM-SPEC-052-EXECUTION-MAP.md) |
| **Saída** | **Lote 2** — Global Knowledge Publisher único · **Lote 5** — primeiro corpus global governado · provenance completa · gates de publicação |

**Não é uma SPEC nova.** É execução explícita e nominada da SPEC-052, conforme **D1**.

**Escopo do Publisher (Lote 2):** endpoint administrativo global · upload sem `agent_id` obrigatório · owner `platform` · quarentena → extração → sanitização → classificação → curadoria → revisão → aprovação → publicação · reindexação · revogação · seeds usando o mesmo publisher.

**Escopo do corpus (Lote 5):** 50–100 documentos de fontes oficiais — legislação, condições gerais, seguradoras prioritárias, fundamentos, vendas e gestão — com Knowledge Cards e goldens. **Corpus real e curado, nunca quantidade artificial.** Hoje o sistema tem 9 documentos no total.

**Restrição (D7):** o material de INTAKE **não** pode ser usado como fonte deste corpus.

**Gate 7**

- nenhum uploader, seed, Destilador ou agente publica fora do Publisher;
- nenhum draft aparece no runtime;
- metadados obrigatórios da SPEC-052 §7.4 presentes em todo documento publicado;
- validade, namespace, audience e visibility aplicados na recuperação;
- goldens verdes; teste de vazamento do global verde;
- página Memórias não expõe o corpus proprietário.

---

## Etapa 8 — SPEC-058 · Auxiliary & Routine Factory

| Campo | Conteúdo |
|---|---|
| **Depende de** | Etapas 5, 6 e 7 verdes |
| **Entrada** | SPEC-058 integral |
| **Saída** | Factory única · `auxiliary_template_releases`, `tenant_auxiliary_revisions`, `auxiliary_requests`, `capability_gaps` · criação pelo chat e pelo dashboard · readiness resolver · test run · triggers · lifecycle · Auxiliares iniciais de lançamento |

**Gate 8**

- criação por conversa ponta a ponta: pedido → blueprint → dependências → custo → aprovação → teste → instalação → ativação;
- a Factory escolhe o **menor padrão de trabalho adequado** — não cria Agent para todo template;
- `auxiliary_runs` e `routine_runs` legados migrados, com leitura canônica por `work_runs`;
- nenhum Auxiliar ativa sem readiness verde.

---

## Etapa 9 — SPEC-059 · Intelligence Fabric + Memory Fabric completo

| Campo | Conteúdo |
|---|---|
| **Depende de** | Etapa 8 verde |
| **Entrada** | SPEC-059 integral · **Lote 4 da SPEC-052** (D1) |
| **Saída** | pipeline evento → sinal → evidência → Finding → recomendação → Work Run → outcome · Briefings · Garimpo v3 · Demand Radar · **Memory/Learning Fabric completo** |

**Enxerto aprovado (D1 · Lote 4):** implementação completa do Memory Fabric — session summaries, memória pessoal e da corretora, Knowledge Candidate, Destilador, Tecelão, Sentinela, Curador, Conselho, deduplicação e checagem de contradição. O diagnóstico inicial já terá ocorrido na Etapa 2.

**Gate 9**

- Briefing com evidência real, dedupe, cooldown e quiet hours;
- Finding separa **fato** de **inferência** de forma verificável;
- recomendação é proposta governada, nunca execução automática;
- outcome não medido é reportado como **inconclusivo**, jamais como sucesso;
- Garimpo captura demanda sem publicar conhecimento diretamente;
- memória produzindo registros reais e revisáveis.

---

## Etapa 10 — SPEC-060 · Research Intelligence

| Campo | Conteúdo |
|---|---|
| **Depende de** | Etapas 6 e 9 (pode iniciar após 6 em gate) |
| **Entrada** | SPEC-060 integral |
| **Saída** | Research Orchestrator · providers (Tavily, Firecrawl, Places, direct fetch) · Source Registry · snapshots · Claims e citações · contradições · monitors · Evidence Packs · Auxiliar global `Radar de Mercado e Regulação` |

**Gate 10**

- toda afirmação relevante tem Claim com fonte, validade e citação verificável;
- conteúdo web tratado como **não confiável**; sanitização e defesa de prompt injection testadas;
- SSRF coberto;
- Firecrawl como capability da plataforma com custo atribuído por tenant;
- descoberta de empresas por API/provider permitido — **sem scraping da interface do Google Maps**;
- pesquisa **não** publica conhecimento diretamente.

---

## Etapa 11 — SPEC-061 Blocos B/C · Control Plane completo

| Campo | Conteúdo |
|---|---|
| **Depende de** | Etapas 4 e 10 verdes |
| **Entrada** | SPEC-061 §10 a §38 |
| **Saída** | Home executiva · Admin Inbox · Cockpit 360º da Corretora · Hubs Operação, Inteligência, Conexões, Conhecimento, Financeiro, Governança · busca global · read models · migração das páginas históricas |

**Gate 11**

- `/admin` exclusivo da equipe AutoBrokers; `/dashboard` exclusivo das corretoras;
- **Visual Acceptance Pack aprovado pelo Founder**;
- nenhuma página espelha tabela crua; nenhuma ação existe em dois lugares com contratos diferentes;
- Support Access explícito, temporário e rastreável;
- as 33 páginas históricas migradas ou redirecionadas, sem perda de função;
- o Founder administra o sistema sem precisar de SQL.

---

## Etapa 12 — SPEC-062 · Evals, Billing, Resiliência, Rollout

| Campo | Conteúdo |
|---|---|
| **Depende de** | **todas** as etapas anteriores verdes |
| **Entrada** | SPEC-062 integral · usage events já capturados desde a Etapa 3 |
| **Saída** | Release Evidence Fabric · eval datasets e evaluators · quality gates · CI/CD · SLOs e error budgets · Usage/Credit Ledgers · rate cards · planos e assinaturas · invoices e reconciliação · unit economics · carga · backup/restore comprovado · onboarding · readiness em quatro níveis |

**Pré-condição absoluta:** a SPEC-062 §2.6 proíbe emitir `GO` enquanto os bloqueadores críticos da SPEC-054 permanecerem abertos.

**Gate 12**

- Evidence Pack completo por Release Candidate;
- zero P0/P1 de segurança e cross-tenant;
- **restore comprovado** — backup sem restore testado não é aceito;
- reconciliação coerente entre uso, rating, invoices e pagamentos;
- os 1.235 logs históricos **não** cobrados retroativamente por automação;
- créditos promocionais existentes preservados com provenance;
- rollout Amandus → Resulta → AutoFleet com evidência;
- **D8 resolvida** — pareamento físico confirmado.

---

## Etapa 13 — Launch Decision

Decisão exclusiva do Founder, com base no Evidence Pack da Etapa 12:

```text
GO  ·  GO_CONDITIONAL  ·  NO_GO
```

Registrada como nova entrada em [`FOUNDER-DECISIONS.md`](FOUNDER-DECISIONS.md).

---

## Enxertos aprovados — visão consolidada

| Enxerto | Origem | Etapa |
|---|---|---|
| Lote 1 SPEC-052 — unificação global | D1 | 2 |
| Lote 4 parcial — diagnóstico de memória | D1 | 2 |
| Usage events append-only `PRE_LAUNCH_NON_BILLABLE` | D4 | 3 |
| Ponte Atendimento/corredores → Work Runs | D1 | 3 |
| Fundação antecipada da SPEC-061 | D3 | 4 |
| Lote 3 SPEC-052 — Context Assembly 2.0 | D1 | 5 |
| Lotes 2 e 5 — Publisher e corpus | D1 | 7 |
| Lote 4 completo — Memory/Learning Fabric | D1 | 9 |

Nenhum outro enxerto é permitido sem entrada em [`CHANGE-ADDENDA.md`](CHANGE-ADDENDA.md) e, quando material, em [`FOUNDER-DECISIONS.md`](FOUNDER-DECISIONS.md).

---

## Registro de execução

> Uma linha por evento relevante. Append-only.

| Data | Etapa | Evento | Commit |
|---|---|---|---|
| 25/07/2026 | — | Auditoria global read-only concluída; veredito `NEEDS_CANONICAL_FIXES` | `3c8c752` |
| 25/07/2026 | 0 | Decisões D1–D10 fechadas pelo Founder | — |
| 25/07/2026 | 0 | Worktree `AutoBrokers-Opus-Exec` criado em `chore/execution-foundation` | `3c8c752` |
