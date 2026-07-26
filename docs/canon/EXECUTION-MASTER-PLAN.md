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
| 0 | Contexto persistente e correções canônicas | `chore/execution-foundation` | **CONCLUÍDO** | `3c8c752` | `317b041` | relatório da Fase 0 |
| 1 | SPEC-054 Bloco A — Fechamento P0 | `feat/spec054-foundation-hardening` | **CONCLUÍDO** — Gate 1 verde | `2c63530` | `98f4fcd` | preflight + relatório do Bloco A |
| 2 | SPEC-054 Blocos B/C — Baseline, Lote 1, memória | `feat/spec054-foundation-hardening` | **CONCLUÍDO** — Gate 2 verde | `2c63530` | ver relatório | [SPEC-054-EXECUTION-REPORT](reports/SPEC-054-EXECUTION-REPORT.md) |
| 3 | SPEC-055 — Work Runs, usage events, ponte Atendimento | `feat/spec055-durable-work-runs` | **CONCLUÍDO** — aguarda serviço do worker | `adc5395` | `21a2c48` | [SPEC-055-EXECUTION-REPORT](reports/SPEC-055-EXECUTION-REPORT.md) |
| 4 | SPEC-061 Fundação (antecipada) | `feat/spec061-control-plane-foundation` | NÃO INICIADO | — | — | — |
| 5 | SPEC-056 — Skills, Tool Gateway | `feat/spec056-skill-tool-gateway` | **CONCLUÍDO** — cutover do grafo pendente | `21a2c48` | `dddc3ca` | [SPEC-056-EXECUTION-REPORT](reports/SPEC-056-EXECUTION-REPORT.md) |
| 6 | SPEC-057 — Artifact Hub & Report Studio | `feat/spec057-artifact-hub` | NÃO INICIADO | — | — | — |
| 7 | SPEC-052 Cognitive Foundation Closure | `feat/spec052-cognitive-foundation-closure` | NÃO INICIADO | — | — | — |
| 8 | SPEC-058 — Auxiliary & Routine Factory | `feat/spec058-auxiliary-routine-factory` | NÃO INICIADO | — | — | — |
| 9 | SPEC-059 — Intelligence Fabric + Memory Fabric | `feat/spec059-briefing-proatividade` | **CONCLUÍDO** — verificado de forma independente, mergeado na `main`; gate 26/26, `tsc` limpo, RLS fail-closed nas 14 tabelas | `e9fedef` | `758bc5b` (com as 2 correções pós-merge de navegação) | [SPEC-059-EXECUTION-REPORT](reports/SPEC-059-EXECUTION-REPORT.md) |
| 10 | SPEC-060 — Research Intelligence | `feat/spec060-research-intelligence` | **CONCLUÍDO** — gate 29/29, `tsc` limpo, canário com dado real | `92e5cc0` | ver relatório | [SPEC-060-EXECUTION-REPORT](reports/SPEC-060-EXECUTION-REPORT.md) |
| 11 | SPEC-061 — Control Plane | `feat/spec061-control-plane-full` | **EM EXECUÇÃO** — Bloco A completo; Bloco B: Inbox + Central de Trabalhos; Bloco C: navegação zerada. Gate 34/34 | `affd55f` | `3b75e09` | [SPEC-061-EXECUTION-REPORT](reports/SPEC-061-EXECUTION-REPORT.md) |
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
| 25/07/2026 | 0 | `CLAUDE.md` criado — autoridade de processo | `cfbf4bc` |
| 25/07/2026 | 0 | Founder Decisions D1–D10 + P1 e Master Plan registrados | `45f7cac` |
| 25/07/2026 | 0 | Migrations Authority e Change Addenda declarados | `de2efd0` |
| 25/07/2026 | 0 | Template de relatório de execução criado | `f7e5d3b` |
| 25/07/2026 | 0 | Addendum SPEC-052 e índices canônicos atualizados | `317b041` |
| 25/07/2026 | 0 | **Fase 0 concluída** — 90 links validados, árvore limpa, sem write em produção | — |
| 25/07/2026 | 0 | Fase 0 promovida à `main` por merge revisado | `2c63530` |
| 25/07/2026 | 1 | Preflight do Bloco A concluído — `BLOCKED_BY_ACCESS` | `2c63530` |
| 25/07/2026 | 1 | **D11** aprovada — Supabase Free + Recovery Pack manual | — |
| 25/07/2026 | 1 | Recovery Pack validado — 56 objetos (7 MB), 4 rollbacks, checksums | — |
| 25/07/2026 | 1 | **A1 aplicada** `20260725055327` — `anon` em SECURITY DEFINER: 12 → **0** | — |
| 25/07/2026 | 1 | **A2 aplicada** `20260725055402` — advisors: 73 → 31, **zero ERROR** | — |
| 25/07/2026 | 1 | **A4 aplicada** `20260725055753` — 12 URLs públicas → path canônico | — |
| 25/07/2026 | 1 | Código de Storage escrito: resolver, proxy autenticado, upload server-side | — |
| 25/07/2026 | 1 | D12/D13/D14 registradas; merge e publicação da main | `98f4fcd` |
| 25/07/2026 | 1 | Deploy smith-web validado: login 200, proxy /api/storage 401 | `98f4fcd` |
| 25/07/2026 | 1 | **A3 aplicada** — 3 buckets privados, 8 policies PUBLIC removidas, 61 objetos intactos | — |
| 25/07/2026 | 1 | VERIFY: URL pública antiga 400 na origem; traversal 400; upload sem sessão 401 | — |
| 25/07/2026 | 1 | **GATE 1 VERDE — Bloco A concluído** | — |
| 25/07/2026 | 2 | B1 FKs de company em 14 tabelas + 13 índices; 0 órfãos | — |
| 25/07/2026 | 2 | B2 constraints cross-company; cruzamento de tenant bloqueado em teste | — |
| 25/07/2026 | 2 | B3 Lote 1 da SPEC-052: segundo caminho global do RAG removido | — |
| 25/07/2026 | 2 | B4 causa raiz da memória zerada encontrada e corrigida | — |
| 25/07/2026 | 2 | C1 HTTP Egress Guard + 24 testes de segurança verdes | — |
| 25/07/2026 | 2 | C2 MCP env allowlist; herança de os.environ eliminada | — |
| 25/07/2026 | 2 | C3 46/46 capability scopes + 3 correções de fronteira | — |
| 25/07/2026 | 2 | C4 22 índices duplicados removidos; 28 índices de FK criados | — |
| 25/07/2026 | 2 | C5 Broker Outcome Regression Pack: **15/15 GATE VERDE** | — |
| 25/07/2026 | 2 | Deploy API validado; advisors de segurança: **ZERO ERROR, ZERO WARN** | — |
| 25/07/2026 | 2 | **SPEC-054 CONCLUÍDA** | — |
| 25/07/2026 | 3 | Preflight da SPEC-055 publicado — bloqueador de checkpointer identificado | `adc5395` |
| 25/07/2026 | 3 | 055-A: 6 tabelas work_*, enums, FKs compostas, RLS — 7/7 garantias no banco | — |
| 25/07/2026 | 3 | Defeito corrigido: append-only bloqueava CASCADE legítimo (retenção/LGPD) | — |
| 25/07/2026 | 3 | 055-A: approval_requests evoluída, usage_events, RPC atômica run+outbox | — |
| 25/07/2026 | 3 | 055-B: effects, queue, runs, approvals, usage, Smith Worker | — |
| 25/07/2026 | 3 | 055-C: workflows, 4 pontes, API de Work Runs, ponte de Rotinas com flag | — |
| 25/07/2026 | 3 | Testes: 11/11 do Work OS · **Regression Pack 17/17 GATE VERDE** | — |
| 25/07/2026 | 3 | Deploy API validado; rotas /api/work vivas (401) | `21a2c48` |
| 25/07/2026 | 3 | **SPEC-055 CONCLUÍDA** | — |
| 25/07/2026 | 3 | Serviço `autobrokers-smith-worker` criado pelo Founder e no ar | — |
| 25/07/2026 | 3 | **GATE 055 CONFIRMADO**: checkpointer Postgres ativo (4 checkpoints, 31 writes) | — |
| 25/07/2026 | 3 | `system.healthcheck` completo em produção: created→queued→leased→started→step→succeeded | — |
| 25/07/2026 | 3 | Corrigido ruído de `TimeoutError` no consume — mascarava falha real | `4154c41` |
| 25/07/2026 | 5 | 056-A: 11 tabelas do Registry — 5/5 garantias no banco | — |
| 25/07/2026 | 5 | 056-B: SkillRegistry com progressive disclosure + ToolGateway único | — |
| 25/07/2026 | 5 | 056-C: 15 tools, 8 Skills, 7 packs, 14 bindings — zero efeito grave sem aprovação | — |
| 25/07/2026 | 5 | Testes: 16/16 do Gateway · **Regression Pack 19/19 GATE VERDE** | — |
| 25/07/2026 | 5 | **SPEC-056 CONCLUÍDA** — pendente: cutover do grafo + Context Assembly 2.0 | `dddc3ca` |
| 25/07/2026 | 1 | Gate de type-check: `tsc --noEmit` **exit 0**, zero erro | `bdaeafa` |
| 25/07/2026 | 1 | `next build`: **Compiled successfully**. Falha posterior e ambiental (secrets ausentes no worktree) em rotas nao tocadas | `8b9faee` |

---

# ESTADO EM 26/07/2026 — leia isto antes de qualquer execução

**commit de referência:** `202b3f7` na `main` · **gate:** 24/24 VERDE · tsc exit 0

## Etapas concluídas

| SPEC | Estado | O que ficou de pé |
|---|---|---|
| **054** | CONCLUÍDA | advisors 73→28 com ZERO error/warn · 46 scopes · buckets fechados |
| **055** | CONCLUÍDA | Work Runs com lease, heartbeat, outbox, HITL por fingerprint. Gate confirmado em produção |
| **056** | CONCLUÍDA | Skill Registry + Tool Gateway. 21 tools, 11 Skills, 28 capabilities |
| **052 L3** | CONCLUÍDA | Context Assembly 2.0 — Intent Router, Planner, Evidence Pack, precedência §6.4 |
| **057** | CONCLUÍDA | Brand Identity Fabric · Artifact Hub · 8 templates · Firecrawl medido · corpus normativo · cutover do grafo |
| **058** | Blocos A–E | Factory: schema, árvore de decisão, funil de demanda, painel Admin, chat propõe |

## Flags em produção

| Flag | Valor | Onde | Significa |
|---|---|---|---|
| `TOOL_GATEWAY_MODE` | `shadow` | api + worker | Gateway decide em paralelo, diff gravado, lista antiga vale |
| `CONTEXT_ASSEMBLY_MODE` | `shadow` (padrão) | — | Plano calculado e logado, nada é pulado |
| `AUTHORITY_STRICT_MODE` | **off** | — | Espera o diff do cutover provar equivalência |
| `WORK_RUNS_ROUTINE_BRIDGE` | `1` | api + worker | Rotina cria Work Run |
| `FIRECRAWL_API_KEY` | ativa | api + worker | **Créditos esgotados — ver D18** |

### Critério para virar o Gateway para `on`

`GET /api/work/cutover` → **300 decisões, 98% idênticas, zero erro**.
Só então `TOOL_GATEWAY_MODE=on`, e só depois `AUTHORITY_STRICT_MODE=1`.

## Bloqueios ativos

1. **D18 — corpus normativo:** 23 documentos na fila por crédito do Firecrawl.
   Retoma sozinho. Nenhuma ação de código.
2. **PDF no servidor:** exige Chromium na imagem do contêiner. Regra 1 do
   CLAUDE.md impede mudança de infra antes do preflight. O CSS de impressão já
   está pronto e testado; o download funciona pelo navegador.

## Pendências registradas

- **D19** — instalação guiada do Auxiliar (SPEC-058). Sugestão: após a 061.
- Migrations das SPECs 055–058 estão aplicadas no banco mas **não espelhadas**
  como arquivo em `backend/supabase/migrations/`. Dívida de governança do
  Executor; corrigir com dump de `supabase_migrations.schema_migrations`.

---

# ESTADO EM 26/07/2026 (fim do dia) — SPEC-059 concluída

**gate:** 26/26 VERDE · tsc exit 0 · 3 migrations aplicadas com VERIFY

## O que a SPEC-059 acrescentou

| Peça | O que faz |
|---|---|
| **Intelligence Fabric** | evento → sinal com evidência → Finding (fato separado de inferência) → recomendação com ação real → Work Run → outcome medido |
| **12 detectores** | publicados como regras versionadas, pausáveis e recalibráveis **sem deploy** |
| **Centro de Briefing** | `/dashboard/briefing` — Hoje, Esta semana, Oportunidades, Histórico, Preferências |
| **Central de Inteligência** | `/admin/inteligencia` — sinais, diagnósticos, demanda anônima, qualidade por regra |
| **Garimpo v3** | preserva a regex calibrada; muda o destino para `intelligence_signals` e para a Factory |
| **Demand Radar** | agregado e anônimo por construção (`tenant_hash` com sal) |
| **Memory Fabric** | Lote 4 da SPEC-052 — fecha sessões inativas fora do turno; `company_memories` e `knowledge_candidates` |
| **4 tools do Core** | o corretor pergunta "o que precisa da minha atenção?" e recebe o que está gravado |

## Cutover realizado

Os quatro motores proativos antigos **deixaram de enviar por conta própria**:
Garimpo, IA de Sugestões, relatório de sábado e Sentinela de Regressão. Os
algoritmos foram preservados e viraram fontes do pipeline.

## Flags novas em produção

| Flag | Valor | Significa |
|---|---|---|
| `INTELLIGENCE_CUTOVER` | `1` | pipeline canônico é a autoridade; `=0` faz rollback sem deploy |
| `INTELLIGENCE_TICK` | `1` | o laço de manutenção do Smith Worker enfileira briefings e detecção |
| `DEMAND_CLUSTER_SALT` | padrão | sal do hash de tenant no agregado global |

## Bloqueios ativos (inalterados)

1. **D18 — corpus normativo:** 23 documentos na fila por crédito do Firecrawl.
   Volta a importar na SPEC-060, que é pesquisa externa.
2. **PDF no servidor:** exige Chromium na imagem. Afeta agora também a peça do
   briefing e o Radar de Demanda em PDF.

## Pendente de ação do Founder

1. **Deploy da API e do worker** com o código da SPEC-059 — sem ele nada roda.
2. Após um ciclo, conferir que `briefing_publications` e `session_summaries`
   deixaram de ser zero.
3. Decidir quando ligar o **envio proativo externo** (hoje o briefing vive no
   dashboard e no chat; a política de canal está pronta e desligada).

## Próxima etapa

**SPEC-060 — Research Intelligence.** Ela deve **receber** sinais externos pelo
pipeline da SPEC-059, sem criar outro motor de pesquisa, outro RAG, outro
publisher, outro scheduler nem outro sistema proativo.

---

# ESTADO EM 27/07/2026 — SPEC-060 concluída

Branch `feat/spec060-research-intelligence`, a partir de `92e5cc0`.
**Gate 29/29 verde · `npx tsc --noEmit` limpo · canário com dado real no banco
de produção (nada persistido).**

## O que a SPEC-060 acrescentou

| Camada | Entrega |
|---|---|
| Schema | 13 tabelas `research_*`, RLS ligada e **zero policy** nas 13 · 6 garantias de conduta em CHECK · 2 triggers (recontagem de citações, append-only de observações) |
| Fundação | normalização/dedupe de URL · política e tier de fonte · sanitizador de conteúdo com quarentena · 4 providers com degradação declarada · roteador · registro de fontes e cache · verificador de claims |
| Orquestração | planner com regra de parada declarada antes de começar · orchestrator · monitores · auditoria de site · descoberta de empresas · adaptadores para Intelligence, Knowledge e Artifact |
| Work OS | 5 workflows: `research.execute`, `research.monitor_check`, `research.site_audit`, `research.business_discovery`, `research.radar_weekly` |
| Peças | 6 templates novos no catálogo da SPEC-057 (CA-018) |
| Auxiliar | **Radar de Mercado e Regulação** — instalação com efeito real (CA-019) |
| Superfície | `/dashboard/pesquisas` e `/admin/pesquisa`, ambas com link no menu |
| Melhorias da 059 | `origem.py` (CA-015) e contagem de `wrong_data` por regra (CA-017) |

## Cutover realizado

`RESEARCH_CUTOVER=1` (padrão): a `WebSearchTool` antiga deixa de ser anexada ao
Core; `platform.web.search` expande para `platform.research.search`, de modo
que **ninguém perde poder no cutover**. Rollback sem deploy: `RESEARCH_CUTOVER=0`.

## O que NÃO foi criado

Nenhuma capability, tool ou Skill nova de pesquisa: o catálogo já existia no
banco e foi **adotado** (CA-016). Nenhum agendador, nenhum motor de peça,
nenhum canal de entrega próprio.

## Bloqueios ativos

1. **D18 — crédito do Firecrawl.** Continua. **Não bloqueia a SPEC-060:** a
   leitura direta (`direct_fetch`) não depende de fatura e sustenta o pipeline.
   Toda falha distingue `SEM_CHAVE` de `SEM_CREDITO` de `INDISPONIVEL`, com
   motivo em português. Quando o crédito voltar, a fila anda sozinha.
2. **PDF no servidor:** exige Chromium na imagem. Afeta as peças de pesquisa em
   PDF; a versão web sai normalmente.
3. **Sem chave de Places**, a descoberta de empresas **recusa e explica** — não
   raspa o Maps.

## Pendente de ação do Founder

1. **Deploy da API e do worker** com o código das SPECs 059 e 060.
2. Aplicar `20260727_01_spec060_research_foundation.sql` no ambiente de deploy
   (já aplicado no banco de produção; a de Auxiliar, `20260727_02`, também).
3. Configurar as chaves de provider quando quiser leitura paga
   (`TAVILY_API_KEY`, `FIRECRAWL_API_KEY`, `GOOGLE_PLACES_API_KEY`). Sem elas o
   sistema funciona com leitura direta e **diz** o que não pôde fazer.
4. Instalar o Auxiliar **Radar de Mercado e Regulação** em uma corretora e
   conferir, após uma semana, que a peça semanal saiu.

## Próxima etapa

**SPEC-061 — Control Plane.** Ela herda duas dívidas já registradas: as 9
páginas órfãs do Admin (`ORFAS_ANTERIORES_A_SPEC059`, cobradas pelo caso NAV-01
do gate) e o CA-014 — toda tela do Admin precisa responder por N corretoras,
não por uma.

---

# BLOCO 0 DA SPEC-061 — CROSS-SPEC PRODUCTION PROOF GATE (27/07/2026)

Relatório: [CROSS-SPEC-PRODUCTION-PROOF-054-060-2026-07-27](reports/CROSS-SPEC-PRODUCTION-PROOF-054-060-2026-07-27.md)

**Gate 30/30 verde · `tsc` limpo · Security Advisor ERROR 0, WARN 0.**

## O que a produção desmentiu

O produto trabalhava **sem deixar rastro**: 43 Work Runs concluídos, e
`work_attempts` / `tool_invocations` em zero. Duas causas, as duas defeito
(CA-020):

1. `work_attempts` não tinha writer nenhum, apesar da docstring prometer;
2. `tool_invocations` tinha writer no Gateway e **ninguém o chamava**.

`usage_events = 0` e `artifacts = 0` NÃO eram defeito: os 43 runs são workflows
internos de inteligência, que não chamam provider pago nem pedem peça.

## Corrigido

| # | O quê |
|---|---|
| CA-020 | tentativa de etapa + invocação de ferramenta passam a ser gravadas |
| CA-021 | `v_gateway_cutover_progresso` era SECURITY DEFINER com grant a `anon` |
| CA-022 | `tavily_extract` entra entre a leitura direta e o Firecrawl |
| CA-023 | 4 índices dos read models da 061 |

## Migrations aplicadas

`20260727_03_seguranca_view_cutover.sql` · `20260727_04_indices_read_models_061.sql`

## Baseline do Admin para a SPEC-061

| Métrica | Valor |
|---|---|
| Páginas em `app/admin/` (não dinâmicas) | 39 |
| Com link no menu | 24 |
| Órfãs | 9 (cobradas por `NAV-01`, lista impedida de crescer) |
| Rotas em `app/api/admin/` | 114 |
| `localStorage` no Admin | 2 arquivos, ambos de autenticação |

**114 rotas para 39 telas** é a evidência quantitativa do "Admin confuso".

## Pendente de ação do Founder

1. **Rotacionar as chaves expostas** do Tavily e do Google Places — ação física,
   com o roteiro exato na §9.1 do relatório. Nenhuma delas está no Git.
2. Após o deploy deste commit, uma conversa real em Amandus que use ferramenta,
   e conferir `tool_invocations` e `work_attempts` acima de zero.
3. Decidir a reclassificação do **D18**: com Tavily configurado, Firecrawl vira
   provider opcional/premium em vez de bloqueio.

## Próxima etapa

**SPEC-061 — Control Plane**, sobre objetos que agora existem e são confiáveis.

---

# ESTADO EM 27/07/2026 (fim do dia) — SPEC-061 em execução

Branch `feat/spec061-control-plane-full`, de `affd55f` a `7639b3e`.
Relatório: [SPEC-061-EXECUTION-REPORT](reports/SPEC-061-EXECUTION-REPORT.md)

**Gate 33/33 verde · `tsc` limpo · Security Advisor ERROR 0, WARN 0.**

## O que ficou pronto

| Bloco | Entrega | Estado |
|---|---|---|
| A | 7 tabelas do Control Plane, 9 garantias provadas | **completo** |
| A | RBAC server-side: 51 permissions, 10 papéis | **completo** |
| A | BFF, Command Gateway, trilha, tela "Quem pode o quê" | **completo** |
| B | Admin Inbox — "O que precisa de mim" | **completo** |
| B | Cockpit 360º, centrais de Work Runs e approvals, hubs, FinOps | **pendente** |
| C | Dívida de navegação do Admin: 9 → 0 | **completo** |
| C | Visual Acceptance Pack, migração de rotas, canário 3 tenants | **pendente** |

## O que mudou de verdade

O Admin autorizava por **um bit**. Agora cada papel pode só o que deve, toda
escrita administrativa passa por um portão, e a trilha diz por quê — sem vazar
segredo. A proteção saiu do navegador e foi para o servidor (CA-024).

## Correção de medição

A baseline de "9 páginas órfãs" do Bloco 0 estava **errada**: o teste lia só um
dos dois menus e contava link comentado como link. A dívida real era de quatro
páginas, e hoje é zero (CA-025).

## Pendente de ação do Founder

1. **Deploy** da API e do worker com este código.
2. Abrir `/admin/governanca` e conferir que o acesso histórico funciona — o
   papel `master` vira `platform_owner` automaticamente.
3. Atribuir papéis reais: hoje todos operam pelo mapeamento do legado.
4. Rotacionar as chaves expostas (roteiro na §9.1 do relatório do Bloco 0).

## Próxima etapa

Concluir os Blocos B e C da SPEC-061 — cockpits, hubs, comandos e o Visual
Acceptance Pack. Depois, **SPEC-062** (evals, billing, resiliência, rollout).

---

# ADENDO 27/07/2026 — o primeiro deploy real da SPEC-061

O Founder implantou API, web e worker e **não conseguiu abrir nenhuma tela
nova**: leu "Seu papel não inclui ver esta caixa", sendo ele o único
administrador da plataforma.

Três defeitos meus, corrigidos (CA-027, CA-028):

1. `PAPEL_LEGADO` usava a chave `"master"`; o valor real da sessão é
   `master_admin`. O teste conferia que o destino existe, não que a porta abre.
2. Eu fiz o Admin depender do backend estar no ar. Rede de segurança: o master
   de plataforma mantém acesso pelo cookie assinado, e a tela **avisa** quando
   está nesse modo.
3. A Inbox lia `approval_requests.action_key` (é `action_type`) e o Cockpit lia
   `company_integrations` (é `integrations`). O leitor tolerante engolia os
   dois — aprovação nunca apareceria, e a caixa diria "nada precisa de você".

`amandico10@hotmail.com` recebeu `platform_owner` sem prazo.

**Gate 34/34** — com `COL-01`, que compara cada consulta do Admin com o schema
real do banco.

## Entregue nesta rodada

- `/admin/inbox` — "O que precisa de mim"
- `/admin/trabalhos` — Central de Trabalhos, com reprocessar e cancelar pelo
  Command Gateway
- `/admin/governanca` — conceder e retirar papel, com motivo registrado
- `POST /api/work/runs/{id}/retry` — não existia

## Pendente da SPEC-061

Cockpit 360º (read model pronto, a tela `/admin/corretoras` da SPEC-036 ainda
não o adotou — não foi criada uma segunda tela, o que seria a duplicação que o
CLAUDE.md §5 proíbe), central de approvals com ação, hubs de Skills/Tools/
Auxiliares/Artifacts/Conhecimento, FinOps, command palette, sessões e step-up,
Visual Acceptance Pack e migração das rotas históricas.

---

# ADENDO 27/07/2026 (noite) — ajustes vindos do uso real

## Modelos

`claude-opus-5` **não estava** na lista de modelos permitidos, e essa lista não
é catálogo: `agent_config.py` a usa para VALIDAR. Configurar um agente com
opus-5 era recusado. Acrescentado; `claude-opus-4-8` fica por compatibilidade
com agentes já gravados.

Defaults trocados para opus-5 em `agent_council.py` e `attendance_distiller.py`.

**O que cada variável de modelo faz** — a pergunta do Founder:

| Variável | Para quê | Onde vive |
|---|---|---|
| `DISPATCH_LLM_MODEL` | o modelo que conversa com o **WhatsApp da seguradora** durante um acionamento | env da API/worker |
| `ATLAS_PARSER_MODEL` | lê e interpreta as rotas dos portais das seguradoras | env |
| `DISTILLER_STRONG_MODEL` | destila playbooks de conduta a partir de atendimentos | env |
| `COUNCIL_LEADER_MODEL` | consolida o conselho de modelos | env |
| **modelo do ATENDIMENTO** | **não vem de env** — vem de `agents.llm_model` no banco, por agente | banco |

`DISPATCH_LLM_MODEL` é **uma só** variável para **um só** uso. Ter duas linhas
com valores diferentes não são dois propósitos: é conflito.

## AMANDUS SEGUROS

Estava com `company_kind='client'` **e** `is_technical=true` — contraditórios.
`is_technical` tirava a corretora do Cockpit, do briefing, do relatório semanal
e a marcava como "origem interna" para os detectores.

Corrigida, com CHECK `companies_kind_e_tecnica_coerentes_ck` impedindo a volta.

## Entregue

`/admin/aprovacoes` — Central de aprovações (§16), ordenada por idade, com
prévia da ação e motivo obrigatório na recusa.

**Gate 35/35 · tsc limpo.**
