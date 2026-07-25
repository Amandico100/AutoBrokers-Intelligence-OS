# SPEC-062 — AutoBrokers Evals, Billing, Rollout & Production Readiness

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANÔNICA E AUTORIZADA PARA EXECUÇÃO — aprovada pelo Founder em 24/07/2026  
**Autoridade superior:** `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`, `SPEC-053-autobrokers-work-os-core-harness.md`, `SPEC-054-foundation-hardening-schema-governance.md`, `SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`, `SPEC-056-skill-registry-tool-gateway.md`, `SPEC-057-artifact-hub-report-studio.md`, `SPEC-058-auxiliary-routine-factory.md`, `SPEC-059-briefing-proatividade-garimpo-v3.md`, `SPEC-060-research-intelligence.md` e `SPEC-061-portal-admin-control-plane.md`  
**Runtime preservado:** Smith + LangGraph/LangChain + FastAPI + Supabase/Postgres + Redis + Qdrant + MinIO + Next.js  
**Nome oficial do agente central:** **AutoBrokers**  
**Escopo:** consolidar o sistema final de evidências de qualidade, evals, release gates, observabilidade, SLOs, custos, billing, planos, créditos, assinaturas, reconciliação, margem, segurança, carga, backup, restore, disaster recovery, onboarding, readiness, rollout, go-live e operação comercial do AutoBrokers.  
**Natureza desta SPEC:** autoriza migrations, serviços, adapters, CI/CD, datasets, evals, telemetria, configuração de infraestrutura, billing, Control Plane, runbooks, testes de carga, restore drills, canários, cutover, go-live e ativação comercial — sempre preservando as autoridades das SPECs 052–061.  
**Dependência de execução:** as SPECs 054–061 devem estar implementadas e aprovadas, ou ser executadas no mesmo programa, na ordem canônica, antes da autorização final de venda.

---

# 0. Comando direto ao executor — Fable, Opus, Codex ou equivalente

Você está autorizado a **implementar integralmente esta SPEC em linha reta**.

Esta não é uma SPEC para:

- criar apenas mais uma suíte de testes;
- produzir um dashboard de qualidade sem gates reais;
- executar uma bateria de testes e deixar o produto em “beta permanente”;
- criar outro sistema de billing paralelo;
- substituir o Work OS por uma plataforma de CI;
- duplicar o Portal Admin;
- criar outro ledger de custos sem migrar o legado;
- usar somente `token_usage_logs.billed` como autoridade financeira;
- transformar custo de provider em preço comercial automaticamente;
- cobrar retroativamente dados históricos sem decisão explícita do Founder;
- escolher preços, impostos ou condições comerciais sem aprovação humana;
- declarar o produto “perfeito” ou “100% seguro” sem evidência;
- usar apenas LLM-as-a-judge para aprovar segurança, billing, fatos ou isolamento;
- inventar SLOs sem benchmark;
- considerar backup válido sem testar restore;
- considerar canário uma fase indefinida;
- criar outro scheduler, runtime, Registry, Artifact Hub, Intelligence Fabric, Research Orchestrator ou Control Plane;
- concluir com funcionalidades essenciais permanentemente desligadas;
- autorizar venda enquanto bloqueadores P0/P1 permanecerem abertos.

Ao final da mesma iniciativa:

- existirá uma arquitetura única de evals e release evidence;
- toda release relevante possuirá manifesto, datasets, resultados, gates e rollback;
- testes determinísticos, evals de IA, segurança, carga e experiência estarão integrados;
- produção terá avaliação online governada e feedback para datasets;
- SLI, SLO e error budgets estarão definidos com base em benchmarks reais;
- custos serão atribuídos por corretora, Work Run, Skill, Tool, provider, Artifact e resultado;
- usage events terão identidade idempotente e lineage;
- planos, allowances, créditos, assinaturas e cobrança estarão reconciliáveis;
- nenhuma cobrança real ocorrerá sem catálogo comercial aprovado pelo Founder;
- os 1.235 logs históricos atualmente não faturados estarão classificados e protegidos contra cobrança retroativa automática;
- a data de início da cobrança comercial estará explicitamente registrada;
- backup, restore e disaster recovery terão sido exercitados;
- onboarding e readiness de corretora serão executáveis pelo Work OS;
- Amandus, Resulta e AutoFleet terão passado pelos gates de lançamento;
- existirá uma decisão formal `GO`, `GO_CONDITIONAL` ou `NO_GO`;
- o Founder poderá autorizar a venda com evidências compreensíveis;
- o caminho canônico ficará ativo em produção ao final.

## 0.1 Doutrina de lançamento

```text
Construir para produção.
Provar o que foi construído.
Medir qualidade, segurança, custo e resultado.
Corrigir dentro da mesma iniciativa.
Ativar com rollback pronto.
Vender somente o que está operacional e economicamente compreendido.
```

Testes, canários, shadow mode e flags são gates internos da mesma entrega de lançamento.

Eles não justificam:

- múltiplas versões descartáveis;
- meses de beta sem decisão;
- duplicação de sistemas;
- promessa comercial antes de prontidão;
- cobrança sem reconciliação.

## 0.2 Número de blocos

A execução deverá ocorrer em **três blocos macro**, o menor número compatível com qualidade e lançamento:

1. **Bloco A — Release Evidence, Evals, CI/CD, Observabilidade e SLOs**;
2. **Bloco B — Billing, Planos, Uso, Reconciliação e Unit Economics**;
3. **Bloco C — Resiliência, Onboarding, Readiness, Rollout e Go-Live**.

Com os gates verdes, avançar automaticamente.

## 0.3 Critérios legítimos de parada

O executor só deve parar para decisão do Founder quando houver:

- definição de preço, plano, trial, franquia, overage ou top-up;
- definição tributária, fiscal, contábil ou jurídica;
- contratação ou alteração de payment provider;
- decisão de cobrança retroativa;
- aceitação de risco residual P1;
- mudança material de promessa comercial;
- impossibilidade real de restore;
- perda ou risco de corrupção de dados;
- conflito entre autoridades canônicas;
- ausência de acesso de produção necessário;
- custo de infraestrutura não aprovado;
- incidentes P0/P1 durante rollout.

Não parar apenas por:

- número de testes;
- necessidade de unificar runners;
- necessidade de criar fixtures;
- necessidade de instrumentar código;
- necessidade de corrigir falhas encontradas;
- necessidade de refatorar billing existente;
- necessidade de produzir runbooks;
- necessidade de executar restore drill;
- necessidade de criar o painel administrativo correspondente.

---

# 1. Ordem de leitura e autoridade

Antes de qualquer alteração:

1. atualizar a `main`;
2. registrar o commit inicial;
3. ler integralmente as SPECs 052–062;
4. ler os relatórios finais de execução das SPECs 054–061, quando existentes;
5. confirmar no código quais partes já foram implementadas;
6. confirmar o schema vivo em modo read-only;
7. confirmar infraestrutura real no EasyPanel;
8. confirmar providers e credenciais sem reproduzir secrets;
9. confirmar o estado dos backups;
10. confirmar o estado do billing;
11. confirmar o estado dos testes e workflows CI;
12. confirmar os tenants canários;
13. produzir um preflight de diferenças entre documentação e realidade.

Comandos mínimos:

```bash
git fetch origin
git checkout main
git pull origin main
git rev-parse HEAD
git status --short
```

Ordem normativa:

```text
SPEC-052
→ SPEC-053
→ SPEC-054
→ SPEC-055
→ SPEC-056
→ SPEC-057
→ SPEC-058
→ SPEC-059
→ SPEC-060
→ SPEC-061
→ SPEC-062
→ ADRs e documentos históricos quando não conflitarem
→ código e infraestrutura como estado de implementação
```

A SPEC-062 não substitui as anteriores.

Ela governa a evidência necessária para afirmar que foram corretamente implementadas e que o produto pode operar e ser vendido.

---

# 2. Realidade auditada antes desta SPEC

## 2.1 GitHub

Na data desta SPEC:

- as SPECs 052–061 estavam documentadas na `main`;
- não havia implementação integral das SPECs 054–061 comprovada por relatórios finais;
- existiam dezenas de testes em `backend/tests/`;
- muitos testes eram runners independentes, e não uma única suíte com gates de release;
- existiam testes úteis de identidade, Atendimento, HITL, Portais, documentos, Policy Evidence e ondas históricas;
- existia tracing LangSmith;
- existia `conversation_scorecards` como mecanismo inicial de qualidade;
- não existia uma autoridade única de release evidence cobrindo todo o ecossistema.

## 2.2 Supabase vivo

O censo read-only confirmou:

```text
plans                  1
subscriptions          0
company_credits        2
credit_transactions    2
token_usage_logs       1.235
llm_pricing            45
payment_history        0
conversation_scorecards 9
```

O único plano cadastrado era:

```text
SANDBOX TESTE
Preço: R$ 0,00
Créditos exibidos: 15.000
```

Não havia assinatura ativa nem pagamento registrado.

## 2.3 Uso e faturamento

Dos 1.235 registros de `token_usage_logs`:

```text
billed=true       0
billed=false  1.235
sem company_id     0
custo total USD    2,010635
```

Distribuição observada:

```text
chat             750 logs
rag_query        457 logs
vision            14 logs
embedding           9 logs
auxiliary_run       5 logs
```

Consequência:

> A captura de uso existe, mas o ciclo real de faturamento e reconciliação não está comprovadamente ativo em produção.

## 2.4 Créditos atuais

Foram observados saldos promocionais:

```text
AMANDUS SEGUROS  R$ 25,00
Resulta Seguros R$ 25,00
```

Cada saldo possuía origem `bonus`.

Esses valores devem ser preservados com provenance e não podem ser reinterpretados automaticamente como pagamento.

## 2.5 Pricing atual

A tabela `llm_pricing` possuía 45 modelos ativos, todos observados com `sell_multiplier = 2,68`.

O `UsageService` também possuía fallback hardcoded.

Conclusão:

- a tabela atual é útil como custo técnico inicial;
- ela não é catálogo comercial suficiente;
- um multiplicador único não representa margem real de todas as capacidades;
- preços podem ficar desatualizados;
- provider cost, preço ao cliente e crédito comercial precisam ser separados.

## 2.6 Segurança

Os Security Advisors ainda mostravam achados já cobertos pela SPEC-054:

- RLS sem policies em tabelas;
- funções `SECURITY DEFINER` executáveis por roles indevidas;
- view `SECURITY DEFINER`;
- `search_path` mutável;
- buckets públicos e listáveis;
- grants excessivos.

Portanto:

> A SPEC-062 não pode emitir `GO` enquanto os bloqueadores críticos da SPEC-054 permanecerem abertos.

## 2.7 Performance

Os Performance Advisors mostravam:

- foreign keys sem índice;
- policies RLS com initplan ineficiente;
- índices duplicados;
- muitos índices ainda sem uso observado.

A SPEC-062 não autoriza remover índices apenas porque o advisor diz “unused”.

A decisão deve ser baseada em:

- workload real;
- `EXPLAIN ANALYZE` seguro;
- benchmark;
- volume projetado;
- período de observação suficiente.

## 2.8 Veredito factual

```text
A arquitetura de produto está documentada.
Existem peças operacionais reais.
Mas o lançamento comercial ainda não está comprovado.

A SPEC-062 existe para transformar implementação em evidência,
evidência em decisão de lançamento,
e uso real em cobrança correta e sustentável.
```

---

# 3. Visão de produto e padrão de lançamento

O AutoBrokers somente será considerado pronto para venda quando atender simultaneamente a sete dimensões:

1. **Resultado para a corretora**;
2. **Qualidade e factualidade**;
3. **Segurança e privacidade**;
4. **Confiabilidade e recuperação**;
5. **Operabilidade e suporte**;
6. **Clareza comercial e billing correto**;
7. **Unit economics sustentável**.

## 3.1 Resultado para a corretora

A corretora deve conseguir:

- conversar com o AutoBrokers;
- obter respostas corretas e úteis;
- executar tarefas;
- usar Atendimento;
- instalar Auxiliares;
- receber Briefings;
- gerar Artifacts;
- pesquisar;
- utilizar Portais governados;
- receber entregas;
- acompanhar trabalhos;
- entender limites, custos e aprovações.

## 3.2 Resultado para o Founder

O Founder deve conseguir:

- saber o que está pronto;
- saber o que falhou;
- identificar regressões;
- controlar rollout;
- acompanhar custos;
- medir margem;
- corrigir tenants;
- comprovar segurança;
- recuperar o sistema;
- ativar uma nova corretora;
- emitir uma decisão de lançamento baseada em evidência.

## 3.3 O que “produção” significa

Produção não significa ausência absoluta de defeitos.

Significa:

- riscos conhecidos e controlados;
- bloqueadores eliminados;
- fallback e rollback;
- dados protegidos;
- resultados essenciais funcionando;
- limites honestos;
- suporte operacional;
- medição contínua;
- capacidade de correção sem reconstrução.

---

# 4. Leis invioláveis da SPEC-062

1. **Sem evidência, não existe aprovação de release.**
2. **Usage event não é automaticamente uma cobrança.**
3. **Provider cost não é automaticamente preço ao cliente.**
4. **Nenhuma cobrança retroativa automática é permitida.**
5. **Billing é append-only e reconciliável.**
6. **Todo side effect financeiro é idempotente.**
7. **Segurança, isolamento, matemática e billing não dependem somente de LLM-as-a-judge.**
8. **SLO nasce de benchmark e impacto empresarial.**
9. **Backup só é válido depois de restore comprovado.**
10. **Redis não é autoridade durável.**
11. **Qdrant é índice derivado e precisa de estratégia de reconstrução.**
12. **MinIO/Storage precisa de backup próprio.**
13. **Modelo `latest` não pode mudar comportamento crítico silenciosamente.**
14. **Release precisa registrar versões de código, modelos, prompts, Skills, Tools, schemas e rate cards.**
15. **Nenhum tenant pode acessar outro tenant.**
16. **P0 de segurança consome todo o error budget e bloqueia rollout.**
17. **A venda não começa antes do catálogo comercial aprovado.**
18. **Outcome não medido não é prova de valor.**
19. **Erro encontrado no canário deve ser corrigido dentro da iniciativa.**
20. **A SPEC-062 não cria outra autoridade de domínio.**

---

# 5. Ontologia oficial

## 5.1 Eval Case

Uma unidade de teste com:

- input;
- contexto;
- versão de dataset;
- resultado esperado;
- restrições;
- critérios;
- fixtures;
- dados sintéticos ou redigidos;
- tags de risco e domínio.

## 5.2 Eval Dataset

Coleção versionada de Eval Cases.

## 5.3 Evaluator

Método versionado que mede um aspecto do resultado.

Pode ser:

- código determinístico;
- regra;
- comparação estruturada;
- execução de ferramenta;
- revisão humana;
- LLM judge;
- pairwise comparison;
- teste visual;
- teste de segurança;
- teste de carga.

## 5.4 Eval Run

Execução de um conjunto de casos contra uma configuração identificável.

## 5.5 Release Candidate

Conjunto imutável que reúne:

- commit;
- migrations;
- imagens de container;
- configurações;
- modelos;
- prompts;
- Skill Releases;
- Tool Releases;
- Artifact Templates;
- Auxiliary Releases;
- Research providers;
- rate cards;
- feature flags;
- dependências.

## 5.6 Quality Gate

Regra que bloqueia, permite ou condiciona uma release.

## 5.7 SLI

Métrica observável de confiabilidade ou resultado.

## 5.8 SLO

Meta mensurável para um SLI em uma janela definida.

## 5.9 Error Budget

Quantidade tolerável de falha antes de pausar releases de risco e priorizar confiabilidade.

## 5.10 Usage Event

Registro imutável de uma unidade de consumo observada.

## 5.11 Rated Usage

Usage Event interpretado por uma Rate Card versionada.

## 5.12 Provider Cost

Custo real ou estimado pago ao fornecedor.

## 5.13 Customer Price

Preço comercial cobrado ao cliente.

## 5.14 Credit Grant

Crédito promocional, incluído, comprado, devolvido ou ajustado com provenance.

## 5.15 Billing Period

Janela comercial fechável e reconciliável.

## 5.16 Invoice

Documento comercial formado por linhas reconciliadas.

## 5.17 Margin Snapshot

Visão versionada de receita, custo direto, custo compartilhado e margem.

## 5.18 Readiness Assessment

Avaliação baseada em checks reais da plataforma, release ou corretora.

## 5.19 Launch Decision

Decisão imutável:

```text
GO
GO_CONDITIONAL
NO_GO
```

## 5.20 RPO e RTO

- **RPO:** perda máxima aceitável de dados;
- **RTO:** tempo máximo aceitável para recuperação.

---

# 6. Arquitetura canônica

## 6.1 Release Evidence Fabric

```text
Mudança de código/configuração
→ Release Candidate
→ Datasets e Evaluators
→ Eval Runs
→ Security/Performance/Cost Gates
→ Release Evidence Pack
→ Rollout
→ Online Evals
→ Incidentes/feedback
→ novos casos de dataset
```

## 6.2 Billing e Unit Economics

```text
Provider usage / Work Run / Tool invocation
→ Usage Event idempotente
→ Provider Cost
→ Rate Card
→ Rated Usage
→ Allowance / Créditos
→ Billing Period
→ Invoice Line
→ Payment Provider
→ Reconciliation
→ Margin Snapshot
```

## 6.3 Production Readiness

```text
Platform Readiness
+ Release Readiness
+ Tenant Readiness
+ Commercial Readiness
+ Security Readiness
+ Recovery Readiness
→ Launch Decision
```

## 6.4 Autoridades preservadas

| Responsabilidade | Autoridade |
|---|---|
| Execução de trabalho | Work Runs / SPEC-055 |
| Skills e tools | SPEC-056 |
| Artifacts | SPEC-057 |
| Auxiliares e Rotinas | SPEC-058 |
| Inteligência proativa | SPEC-059 |
| Pesquisa | SPEC-060 |
| Administração | SPEC-061 |
| Uso bruto LLM | `token_usage_logs` como fonte técnica |
| Usage comercial | Usage Ledger desta SPEC |
| Custos de provider | Provider Cost Events |
| Pricing | Rate Cards versionadas |
| Créditos | Credit Ledger append-only |
| Assinaturas | Billing Account + Subscription |
| Pagamentos | Payment Provider Adapter + Reconciliation |
| Evals | Release Evidence Fabric |
| Decisão de lançamento | Launch Decision |

---

# 7. Componentes atuais que devem ser preservados

Preservar e evoluir:

- `backend/tests/`;
- testes de identidade;
- testes de Atendimento;
- testes de HITL;
- testes de Portais;
- testes de Policy Evidence;
- testes de documentos;
- `conversation_scorecards`;
- LangSmith tracing;
- CostCallback;
- `UsageService`;
- `token_usage_logs`;
- `llm_pricing`;
- `company_credits`;
- `credit_transactions`;
- `plans`;
- `subscriptions`;
- `payment_history`;
- billing worker existente quando funcional;
- FinOps atual;
- readiness atual;
- release rollout helpers;
- Admin Control Plane;
- Portal Worker;
- MinIO;
- Supabase backups disponíveis;
- Qdrant snapshots/rebuild;
- Redis como fila/cache transitório.

Preservar não significa manter limitações como autoridade definitiva.

---

# 8. Componentes que deixam de ser autoridade soberana

Após o cutover:

- runners independentes não serão gate suficiente;
- `conversation_scorecards` não será o único sistema de qualidade;
- `regression_sentinel.py` não será o único detector de regressão;
- `billed` boolean não será toda a idempotência financeira;
- `debit_company_balance` não será invoice engine;
- `sell_multiplier=2.68` não será regra comercial universal;
- fallback hardcoded não será preço comercial;
- `company_credits.balance_brl` isolado não será ledger suficiente;
- `payment_history` isolado não será reconciliação;
- readiness de poucos booleanos não será autorização de go-live;
- aprovação visual não substituirá eval funcional;
- canário não substituirá rollback;
- sucesso HTTP não provará resultado empresarial;
- métricas de disponibilidade não provarão correção de dados.

---

# 9. Modelo de dados — princípios

## 9.1 Regra de evolução

O executor deve:

1. inventariar tabelas existentes;
2. mapear equivalências;
3. adicionar colunas quando seguro;
4. criar novas tabelas somente quando o conceito ainda não existir;
5. migrar dados;
6. preservar lineage;
7. redirecionar writers;
8. remover autoridade paralela.

## 9.2 Imutabilidade

Devem ser imutáveis após publicação ou fechamento:

- dataset version;
- evaluator release;
- release candidate;
- eval result;
- usage event;
- rated usage fechado;
- invoice line fechada;
- payment event;
- launch decision;
- restore drill report.

Correções acontecem por:

- nova versão;
- adjustment;
- refund;
- reversal;
- supersession;
- novo decision record.

Nunca por edição silenciosa do histórico.

---

# 10. Modelo de dados de Evals e Releases

## 10.1 `eval_datasets`

```text
id
key unique
name
description
domain
owner
sensitivity
status draft|active|deprecated|archived
created_at
updated_at
```

## 10.2 `eval_dataset_versions`

```text
id
dataset_id
version
status draft|published|deprecated
case_count
content_hash
source_summary
pii_policy
created_by
published_by
created_at
published_at
unique(dataset_id, version)
```

## 10.3 `eval_cases`

```text
id
dataset_version_id
case_key
input_payload
context_fixture
expected_output
expected_facts
expected_tools
forbidden_behaviors
assertions
risk_tier
tags
source_lineage
created_at
unique(dataset_version_id, case_key)
```

Dados sensíveis devem ser:

- sintéticos;
- redigidos;
- tokenizados;
- ou executados em ambiente autorizado.

## 10.4 `evaluator_definitions`

```text
id
key
version
kind code|rule|llm|human|visual|security|performance
name
description
config
model_profile_id nullable
thresholds
calibration_version
status
content_hash
created_at
published_at
unique(key, version)
```

## 10.5 `eval_runs`

```text
id
release_candidate_id nullable
dataset_version_id
status queued|running|completed|failed|cancelled
run_type offline|online|shadow|replay
configuration_snapshot
started_at
completed_at
summary
artifact_id nullable
work_run_id nullable
created_by
```

## 10.6 `eval_case_results`

```text
id
eval_run_id
eval_case_id
evaluator_definition_id
status pass|fail|error|inconclusive
score
threshold
output_snapshot_ref
reason
facts
violations
latency_ms
cost_brl
trace_id
review_status
created_at
```

## 10.7 `release_candidates`

```text
id
release_key
version
status draft|evaluating|approved|rejected|deploying|active|rolled_back
code_sha
migration_manifest
container_manifest
configuration_manifest
model_manifest
prompt_manifest
skill_manifest
tool_manifest
artifact_template_manifest
auxiliary_manifest
rate_card_manifest
feature_flag_manifest
created_by
approved_by
created_at
approved_at
activated_at
```

## 10.8 `release_gate_results`

```text
id
release_candidate_id
gate_key
status pass|fail|waived|inconclusive
severity
summary
evidence_refs
waiver_reason nullable
waived_by nullable
expires_at nullable
created_at
```

P0 não pode ser waived.

## 10.9 `human_review_tasks`

```text
id
eval_run_id
eval_case_result_id nullable
review_type
status
assigned_to
instructions
blind_review boolean
review_result
created_at
completed_at
```

## 10.10 `online_eval_samples`

```text
id
company_id nullable
trace_id
work_run_id nullable
sample_reason
redaction_status
evaluation_status
retention_until
created_at
```

---

# 11. Taxonomia de datasets

Criar datasets canônicos para:

## 11.1 Core e conhecimento

- respostas gerais de seguros;
- fonte e provenance;
- separação Global/Tenant/User;
- validade;
- memória;
- contexto insuficiente;
- ausência de evidência.

## 11.2 Apólices e Evidence Pack

- cobertura confirmada;
- cobertura ausente;
- documento conflitante;
- vigência;
- franquia;
- segurado correto;
- locator técnico;
- `numapo` versus `nosnum`;
- proibição de afirmar cobertura sem evidência.

## 11.3 Work OS

- Work Run;
- pausa;
- retomada;
- retry;
- cancelamento;
- crash;
- lease expirado;
- idempotência;
- approval;
- side effect unknown;
- reconciliação.

## 11.4 Skills e Tools

- Skill correta;
- Skill errada;
- tool permitida;
- tool negada;
- capability ausente;
- connection ausente;
- budget;
- Tool Gateway;
- prompt injection;
- output schema.

## 11.5 Artifacts

- web;
- PDF;
- XLSX;
- CSV;
- PPTX;
- DOCX;
- gráficos;
- overflow;
- fontes;
- valores;
- identidade visual;
- links expirados;
- tenant isolation.

## 11.6 Auxiliares e Rotinas

- instalação;
- configuração;
- trigger;
- execução manual;
- agenda;
- edição;
- pausa;
- rollback;
- custo;
- criação por chat;
- criação pelo dashboard;
- anti-loop.

## 11.7 Proatividade

- Signal;
- Finding;
- fato versus inferência;
- evidência;
- prioridade;
- recomendação;
- quiet hours;
- dedupe;
- cooldown;
- outcome;
- sugestão irrelevante.

## 11.8 Research

- fonte oficial;
- claim;
- citation;
- contradição;
- atualidade;
- prompt injection web;
- robots/termos;
- dossiê;
- monitor;
- empresa/Places;
- no auto-publish RAG.

## 11.9 Portal Admin

- autenticação;
- RBAC;
- Support Access;
- Admin Command;
- preview;
- step-up;
- audit;
- Cockpit;
- busca;
- cross-tenant;
- mobile.

## 11.10 Atendimento e WhatsApp

- inbound routing;
- outbound;
- handoff;
- Observador silencioso;
- atendimento humano;
- mensagens duplicadas;
- canal errado;
- tenant errado;
- passkey/QR;
- falha de conexão;
- consentimento.

## 11.11 Portais

- login;
- session reuse;
- CAPTCHA;
- 2FA;
- download;
- boleto;
- evidência;
- credencial expirada;
- portal alterado;
- ação duplicada;
- HITL.

## 11.12 Billing

- usage duplicado;
- event replay;
- cobrança dupla;
- saldo insuficiente;
- bônus;
- refund;
- ajuste;
- mudança de plano;
- FX;
- webhook fora de ordem;
- invoice preview;
- provider indisponível;
- histórico pre-launch;
- reconciliação.

## 11.13 Multi-tenant e segurança

- Resulta não vê AutoFleet;
- Amandus não vê Resulta;
- cache não vaza;
- Artifact não vaza;
- memória não vaza;
- Support Access não atravessa tenant;
- tool não atravessa conexão;
- export não atravessa tenant;
- admin role adulterado;
- SSRF;
- secret leakage.

---

# 12. Hierarquia de evaluators

## 12.1 Determinístico primeiro

Usar código/regra para:

- schemas;
- tipos;
- status;
- IDs;
- matemática;
- billing;
- tenant isolation;
- permissões;
- tools;
- checksums;
- citations presentes;
- links;
- datas;
- idempotência;
- latência;
- disponibilidade;
- arquivos válidos.

## 12.2 LLM judge

Usar para:

- clareza;
- utilidade;
- completude;
- tom;
- qualidade de síntese;
- explicação;
- comparação de respostas;
- identificação de inferência não rotulada.

Não usar como única autoridade para:

- segurança;
- compliance;
- cobrança;
- cálculo;
- direito de acesso;
- existência de cobertura;
- side effects;
- segredo;
- isolamento.

## 12.3 Revisão humana

Obrigatória para calibrar:

- LLM judges;
- casos de alto risco;
- falsos positivos;
- qualidade visual;
- linguagem comercial;
- decisões de waiver;
- novas categorias de erro.

## 12.4 Pairwise

Preferir comparação pairwise quando:

- avaliar mudança de modelo;
- comparar prompt/release;
- comparar template;
- medir regressão subjetiva.

## 12.5 Calibração

Todo evaluator LLM deverá possuir:

- modelo fixado;
- prompt versionado;
- dataset de calibração;
- concordância com humanos;
- taxa de falso positivo;
- taxa de falso negativo;
- versão;
- limite de custo;
- política de substituição.

---

# 13. Quality Gates

## 13.1 Gate P0 — segurança e integridade

Bloqueia release quando houver:

- vazamento cross-tenant;
- secret no client/log;
- função crítica pública;
- bucket sensível público;
- acesso administrativo indevido;
- side effect financeiro duplicável;
- perda de Work Run aceito;
- corrupção de ledger;
- migration não reversível sem plano;
- backup inexistente antes de alteração crítica.

P0 não aceita waiver.

## 13.2 Gate P1 — Broker Outcome Regression

Validar:

- login;
- chat;
- Atendimento;
- WhatsApp;
- documentos;
- RAG;
- Work Runs;
- approvals;
- Auxiliares;
- Rotinas;
- Artifacts;
- Portais;
- Briefings;
- Research;
- Admin;
- billing visibility.

## 13.3 Gate factual

- Claims críticos com fonte;
- cobertura com Evidence Pack;
- ausência declarada como ausência;
- data e vigência;
- contradições expostas;
- números reproduzíveis.

## 13.4 Gate de execução

- Skill correta;
- tool permitida;
- approval correto;
- efeito idempotente;
- retry correto;
- resultado persistido;
- evidência disponível.

## 13.5 Gate de Artifact

- formato abre;
- layout aceitável;
- números coerentes;
- links protegidos;
- conteúdo não corta;
- tenant correto;
- versão correta;
- acessibilidade mínima.

## 13.6 Gate de performance

- thresholds de latência;
- erro;
- throughput;
- queue delay;
- render;
- upload;
- signed URL;
- Admin BFF;
- billing ingestion.

Thresholds finais serão definidos após benchmark.

## 13.7 Gate de custo

- custo por execução medido;
- orçamento respeitado;
- provider cost conhecido;
- margin floor;
- nenhuma tool sem atribuição;
- nenhum Work Run sem cost lineage quando houve custo.

## 13.8 Gate de rollout

- canário verde;
- error budget disponível;
- rollback validado;
- migration compatível;
- alerts ativos;
- owner identificado.

---

# 14. Release Manifest

Toda Release Candidate deverá registrar:

```text
code_sha
schema_version
migration_list
container_digests
frontend_build
backend_build
worker_build
portal_worker_build
artifact_renderer_build
model_profiles
prompt_releases
skill_releases
tool_releases
auxiliary_releases
artifact_templates
research_providers
capability_catalog
rate_cards
plan_catalog
feature_flags
environment_config_hash
eval_dataset_versions
evaluator_versions
```

Segredos não entram no manifest.

Registrar apenas:

- nome da configuração;
- versão;
- hash;
- presença;
- validade;
- owner.

---

# 15. CI/CD canônico

## 15.1 Pull Request

Executar:

- lint;
- typecheck;
- unit tests;
- contract tests;
- migration lint;
- secret scan;
- dependency scan;
- schema compatibility;
- eval subset de risco;
- tenant isolation subset;
- build.

## 15.2 Merge em `main`

Executar:

- suíte completa determinística;
- golden datasets essenciais;
- build de containers;
- SBOM;
- assinatura/digest;
- criação de Release Candidate;
- Release Evidence preliminar.

## 15.3 Pré-deploy

- backup/checkpoint;
- migration dry-run;
- compatibilidade;
- capacidade;
- feature flags;
- rollback;
- provider health;
- budget;
- approvals.

## 15.4 Pós-deploy

- smoke tests;
- health;
- login;
- chat;
- Work Run;
- approval;
- Artifact;
- connection;
- billing event;
- Admin;
- tenant isolation.

## 15.5 Online

- amostragem de traces;
- error rate;
- factuality sample;
- delivery;
- custo;
- SLO;
- feedback;
- incident detection.

## 15.6 Resultado

Cada execução deve produzir um Artifact:

```text
Release Evidence Pack
```

Com:

- resumo executivo;
- versão;
- gates;
- falhas;
- waivers;
- custos;
- riscos;
- rollback;
- links para traces;
- decisão recomendada.

---

# 16. Modelo e provider governance

## 16.1 Sem mudança silenciosa

Não usar aliases `latest` em comportamento crítico sem:

- resolução para versão concreta;
- registro;
- eval;
- rollout.

## 16.2 Model Profile

Cada perfil define:

- provider;
- modelo;
- versão;
- temperatura;
- reasoning;
- timeout;
- max tokens;
- fallback;
- orçamento;
- datasets obrigatórios;
- data de validade do preço.

## 16.3 Mudança de modelo

Executar:

```text
baseline atual
→ candidato
→ offline eval
→ pairwise
→ custo/latência
→ canário
→ online eval
→ ativação
```

## 16.4 Fallback

Fallback deve ser:

- homologado;
- testado;
- compatível com tool calling;
- compatível com output schema;
- dentro do budget;
- observável.

Fallback não pode reduzir segurança silenciosamente.

## 16.5 Pricing freshness

Preços de provider devem possuir:

- fonte;
- moeda;
- unidade;
- data de vigência;
- data de verificação;
- status stale;
- owner;
- fallback policy.

Preço hardcoded é emergência, não autoridade comercial.

---

# 17. Online evaluation

## 17.1 Amostragem

Avaliar 100% de:

- permission denied;
- security violation;
- side effect financeiro;
- tenant mismatch;
- approval crítico;
- billing exception;
- incidentes;
- falha de delivery crítica.

Amostrar de forma governada:

- respostas gerais;
- Briefings;
- pesquisas;
- Artifacts;
- conversas.

## 17.2 Privacidade

Antes de enviar trace a serviço externo:

- redigir PII;
- remover secrets;
- verificar tenant policy;
- limitar retenção;
- registrar finalidade;
- usar provider autorizado.

## 17.3 Feedback loop

```text
falha real
→ redaction
→ triagem
→ Eval Case
→ dataset version
→ correção
→ release gate
```

Nada é copiado automaticamente para o RAG global.

---

# 18. SLI, SLO e Error Budgets

## 18.1 Princípio

SLO não deve ser escolhido por estética.

Deve refletir:

- impacto na corretora;
- volume real;
- capacidade atual;
- custo;
- criticidade;
- dependência externa.

## 18.2 SLIs obrigatórios

### Chat

- disponibilidade;
- time to first token;
- conclusão;
- erro;
- resposta com fonte quando exigida.

### Work Runs

- queue delay;
- success rate;
- retry rate;
- stale rate;
- lost runs;
- tempo até conclusão;
- resume success.

### Approvals

- tempo até criação;
- entrega;
- resume;
- duplicação.

### Tools e Connections

- autorização;
- sucesso;
- latency;
- provider error;
- connection health;
- circuit breaker.

### Artifacts

- render success;
- tempo;
- download;
- entrega;
- consistência entre formatos.

### Atendimento e WhatsApp

- inbound accepted;
- outbound delivered;
- duplicação;
- handoff;
- connection uptime.

### Portais

- login success;
- jornada success;
- CAPTCHA/HITL;
- evidence;
- recovery.

### Research

- source success;
- citation coverage;
- stale sources;
- claim verification;
- monitor success.

### Billing

- usage ingestion;
- duplicates;
- rating latency;
- reconciliation;
- invoice accuracy;
- payment webhook processing.

### Admin

- overview freshness;
- command success;
- permission denied correto;
- search latency;
- stale read models.

## 18.3 Contratos absolutos

Independentemente do benchmark:

- zero cross-tenant tolerado;
- zero cobrança duplicada tolerada;
- zero secret exposto tolerado;
- zero Work Run aceito perdido tolerado;
- 100% das invoices precisam reconciliar;
- 100% dos comandos P3/P4 precisam de audit;
- 100% dos side effects financeiros precisam de idempotency key.

## 18.4 Error budget policy

Quando o error budget for consumido:

- pausar releases de risco;
- priorizar confiabilidade;
- abrir incidente;
- corrigir;
- comprovar recuperação;
- retomar rollout.

Incidente que consumir parcela material do budget exige postmortem.

---

# 19. Observabilidade

## 19.1 Padrão

Usar OpenTelemetry para:

- traces;
- metrics;
- logs correlacionados.

Preservar LangSmith para observabilidade específica de IA.

Ligação:

```text
OpenTelemetry trace_id
↔ LangSmith trace
↔ Work Run
↔ Skill
↔ Tool Invocation
↔ Artifact
↔ Usage Event
↔ Release Candidate
```

## 19.2 Contexto permitido

- company_id;
- work_run_id;
- skill_release_id;
- tool_release_id;
- artifact_id;
- release_candidate_id;
- provider;
- modelo;
- status;
- custo;
- latency.

## 19.3 Contexto proibido

- senha;
- token;
- secret;
- conteúdo integral de Vault;
- CPF completo;
- documento sensível integral;
- transcript sem necessidade;
- prompt protegido integral.

## 19.4 Alertas

Alertas devem possuir:

- owner;
- severidade;
- threshold;
- runbook;
- dedupe;
- cooldown;
- tenant impact;
- correlation id.

---

# 20. Billing — decisão arquitetural

## 20.1 Autoridade interna

O AutoBrokers mantém internamente a autoridade sobre:

- Usage Events;
- rating;
- allowances;
- créditos;
- invoice lines;
- reconciliação;
- margin.

O payment provider:

- cria cobrança;
- recebe pagamento;
- envia webhook;
- não se torna fonte da verdade do consumo operacional.

## 20.2 Provider

O adapter existente de Stripe deve ser preservado quando funcional.

A SPEC não obriga Stripe se houver decisão comercial posterior.

O contrato precisa permitir outro provider sem reescrever o ledger.

## 20.3 Modelo comercial inicial recomendado

Para lançamento:

```text
mensalidade base
+ capacidades incluídas por plano
+ allowance de uso/créditos
+ alertas claros
+ hard stop ou aprovação antes de exceder
+ top-up ou upgrade
```

Não recomendar overage surpresa no primeiro lançamento.

O Founder precisa aprovar:

- nomes dos planos;
- preços em R$;
- allowances;
- limites;
- trial;
- top-up;
- grace period;
- política de suspensão;
- refund;
- impostos;
- formas de pagamento.

## 20.4 Linguagem para o corretor

Não usar tokens como principal unidade de valor.

Exibir:

- uso incluído;
- trabalhos;
- relatórios;
- pesquisas;
- automações;
- consumo estimado;
- saldo;
- próximos limites.

Detalhes de tokens ficam na camada avançada.

---

# 21. Usage Ledger

## 21.1 `usage_events`

```text
id
idempotency_key unique
company_id
user_id nullable
agent_id nullable
work_run_id nullable
step_id nullable
skill_release_id nullable
tool_release_id nullable
artifact_id nullable
provider
provider_event_id nullable
usage_type
quantity
unit
provider_cost_amount nullable
provider_cost_currency nullable
occurred_at
received_at
source
source_ref
metadata_redacted
status accepted|rejected|adjusted|quarantined
```

## 21.2 Fontes

- LLM tokens;
- embeddings;
- voz/minutos;
- OCR;
- Firecrawl;
- Tavily;
- Places;
- browser/computer use;
- WhatsApp provider;
- Artifact rendering;
- storage;
- e-mail;
- future providers.

## 21.3 Deduplicação

O evento deve ser identificado por:

```text
provider + provider_event_id
```

ou:

```text
source + source_ref + usage_type + sequence
```

## 21.4 Relação com `token_usage_logs`

`token_usage_logs` continua como fonte técnica histórica.

Novos writers devem:

- gerar Usage Event canônico;
- manter vínculo com log técnico;
- evitar dupla emissão;
- suportar backfill controlado.

---

# 22. Tratamento dos 1.235 logs históricos

## 22.1 Regra padrão

Os registros anteriores ao `commercial_go_live_at` serão classificados como:

```text
PRE_LAUNCH_NON_BILLABLE
```

Salvo decisão explícita do Founder.

## 22.2 Processo

1. snapshot;
2. checksum;
3. classificar por tenant e serviço;
4. detectar duplicados;
5. reconciliar custo técnico;
6. registrar boundary de lançamento;
7. criar Usage Events quarantined ou non-billable;
8. impedir worker legado de debitar retroativamente;
9. documentar decisão.

## 22.3 Proibição

Não executar:

```sql
update token_usage_logs set billed = false/true ...
```

como atalho de migração sem ledger, snapshot e plano de rollback.

## 22.4 Bônus existentes

Os R$ 25,00 atuais devem entrar como:

```text
credit_grant.type = promotional_bonus
```

Com:

- origem;
- tenant;
- valor;
- data;
- expiração, se houver;
- decisão comercial.

---

# 23. Rate Cards e Pricing

## 23.1 Separação

```text
Provider Cost Card
≠ Customer Rate Card
≠ Plan Catalog
```

## 23.2 `provider_cost_rates`

- provider;
- product/model;
- region;
- currency;
- unit;
- tier;
- valid_from;
- valid_until;
- source;
- verified_at;
- stale status.

## 23.3 `rate_cards`

- key;
- version;
- currency BRL;
- status;
- effective dates;
- pricing rules;
- rounding;
- minimum;
- owner;
- approval.

## 23.4 `rate_card_items`

Mapeia:

- usage type;
- unit;
- preço;
- allowance behavior;
- markup;
- caps;
- plan applicability.

## 23.5 Câmbio

Provider cost em USD precisa de política versionada:

- fonte cambial;
- data;
- spread;
- fallback;
- arredondamento;
- fechamento de período.

Não converter cada evento comercial com regra implícita.

---

# 24. Créditos e Ledger financeiro

## 24.1 Regra

Saldo é projeção do ledger.

Não é a única autoridade.

## 24.2 `credit_ledger_entries`

```text
id
company_id
entry_key unique
entry_type allowance|bonus|purchase|consumption|refund|adjustment|expiration|reversal
amount_brl
balance_after_brl
currency
usage_event_id nullable
rated_usage_id nullable
invoice_line_id nullable
payment_event_id nullable
reason
created_by
created_at
```

## 24.3 Evolução do legado

- preservar `company_credits` como projeção rápida;
- migrar `credit_transactions` para ledger ou torná-la projection/compatibilidade;
- impedir dois writers soberanos;
- débito deve ser atômico e idempotente;
- reversal, não edição.

## 24.4 Saldo insuficiente

O comportamento depende do plano:

- bloquear antes de executar;
- solicitar top-up;
- solicitar aprovação;
- permitir somente operação crítica gratuita;
- nunca deixar negativar silenciosamente.

---

# 25. Assinaturas, invoices e pagamentos

## 25.1 `billing_accounts`

- company_id;
- legal/billing identity;
- currency;
- provider customer ref;
- tax metadata protegida;
- status.

## 25.2 `subscriptions`

Evoluir a tabela atual para suportar:

- plan release;
- status;
- início;
- trial;
- ciclo;
- cancelamento;
- grace;
- provider refs;
- scheduled change.

## 25.3 `subscription_items`

- base plan;
- add-ons;
- seats;
- allowances;
- premium Auxiliaries;
- future modules.

## 25.4 `billing_periods`

- company;
- start/end;
- status open|rating|review|closed|invoiced|paid|void;
- usage cutoff;
- reconciliation status.

## 25.5 `rated_usage`

- usage event;
- rate card version;
- gross amount;
- allowance;
- discount;
- net amount;
- status;
- lineage.

## 25.6 Invoices

Persistir:

- invoice record;
- lines;
- totals;
- currency;
- provider ref;
- status;
- payment status;
- Artifact fiscal/comercial quando aplicável.

## 25.7 Webhooks

Todo webhook deve possuir:

- provider event ID;
- assinatura validada;
- idempotência;
- raw payload protegido;
- processed status;
- retry;
- dead letter;
- audit.

## 25.8 Reconciliação

Comparar:

```text
Usage Ledger
Rated Usage
Credit Ledger
Invoice
Payment Provider
Banco/recebimento quando aplicável
```

Toda divergência vira exception operável no Control Plane.

---

# 26. Unit Economics

## 26.1 Atribuição obrigatória

Medir custo por:

- tenant;
- usuário;
- Agent;
- Work Run;
- Skill;
- Tool;
- provider;
- Artifact;
- Auxiliar;
- Research job;
- canal;
- modelo;
- release.

## 26.2 Métricas

- receita recorrente;
- receita de uso;
- provider cost;
- infraestrutura variável;
- suporte variável;
- margem bruta;
- contribuição;
- custo por Work Run;
- custo por resultado;
- custo por tenant ativo;
- margem por plano;
- margem por Auxiliar;
- margem por provider.

## 26.3 Custo compartilhado

Separar:

- custo atribuível diretamente;
- custo compartilhado;
- custo fixo;
- custo de desenvolvimento;
- custo de suporte.

Não distribuir custo compartilhado de forma arbitrária sem política versionada.

## 26.4 Alertas

- margem negativa;
- uso anômalo;
- provider cost stale;
- allowance quase esgotada;
- tenant com custo desproporcional;
- Skill muito cara;
- retry excessivo;
- output sem valor medido.

---

# 27. Planos e entitlements

## 27.1 Catálogo versionado

Cada plan release define:

- preço;
- periodicidade;
- trial;
- features;
- capabilities;
- limits;
- allowances;
- seats;
- Auxiliares;
- Research;
- Artifact formats;
- retenção;
- suporte;
- overage/top-up;
- grandfathering.

## 27.2 Capability Registry

Planos não concedem poderes diretamente no frontend.

Fluxo:

```text
Plan Release
→ Subscription
→ Entitlements
→ Capability Registry
→ Tool Gateway / Auxiliary Factory / Research
```

## 27.3 Mudança de plano

Precisa de:

- preview;
- proration policy;
- data efetiva;
- impacto;
- entitlements;
- rollback/cancelamento;
- audit.

## 27.4 Trial

Trial precisa definir:

- duração;
- capabilities;
- limites;
- documentos;
- dados persistidos;
- conversão;
- expiração;
- comunicação.

---

# 28. Segurança final

## 28.1 Pré-condição

A SPEC-054 deve estar verde.

## 28.2 Controles

- RLS e defesa em profundidade;
- SECURITY DEFINER fechado;
- search_path fixo;
- Storage privado;
- SSRF guard;
- MCP sandbox;
- env allowlist;
- RBAC Admin;
- step-up;
- Support Access;
- audit;
- secret rotation;
- signed URLs;
- idempotência;
- input/output validation.

## 28.3 AppSec

Implementar:

- secret scanning;
- dependency scanning;
- SBOM;
- SAST;
- DAST focado;
- container scanning;
- license scan;
- API abuse tests;
- authentication tests;
- authorization matrix;
- OWASP ASVS 5.0 mapping proporcional.

## 28.4 AI Security

- prompt injection;
- indirect injection;
- data exfiltration;
- tool abuse;
- over-permission;
- poisoned document;
- malicious MCP resource;
- untrusted HTML/PDF;
- unsafe browser action;
- model fallback regression.

## 28.5 Terceiros

Manter inventário de:

- provider;
- finalidade;
- dados enviados;
- região;
- retenção;
- DPA/termos;
- subprocessors;
- owner;
- fallback;
- status.

---

# 29. Performance e carga

## 29.1 Ferramenta

Usar k6 ou ferramenta equivalente com thresholds que falham o pipeline.

## 29.2 Perfis de workload

### Launch

- tenants atuais;
- usuários atuais;
- tráfego realista;
- jobs simultâneos moderados.

### Peak

- picos de atendimento;
- múltiplas Rotinas;
- Briefings;
- Artifact rendering;
- webhook bursts.

### Burst

- reconexão de provider;
- retries;
- campanhas;
- monitor research;
- fila acumulada.

### Long-running

- deep research;
- Portais;
- relatórios;
- Work Runs com HITL.

## 29.3 Superfícies

Testar:

- login;
- chat streaming;
- webhook inbound;
- queue/outbox;
- worker;
- Supabase;
- Redis Streams;
- Qdrant;
- MinIO;
- Artifact renderer;
- Admin BFF;
- signed URL;
- billing ingestion;
- Research providers;
- Portal Worker.

## 29.4 Regras

- não executar carga destrutiva em produção sem janela e autorização;
- usar ambiente representativo;
- usar dados sintéticos;
- registrar configuração;
- repetir;
- comparar releases;
- produzir Capacity Report.

## 29.5 Capacidade

O relatório deve definir:

- capacidade observada;
- headroom;
- gargalo;
- scaling policy;
- concurrency por tenant;
- provider quotas;
- custos;
- threshold de expansão.

---

# 30. Backup e Disaster Recovery

## 30.1 Princípio

```text
Backup não testado = esperança, não recuperação.
```

## 30.2 Supabase/Postgres

Implementar e verificar:

- backup gerenciado disponível no plano;
- PITR quando contratado/necessário;
- logical dump periódico;
- retenção;
- encryption;
- acesso;
- restore para ambiente isolado;
- consistência pós-restore.

## 30.3 Storage e MinIO

Backups de banco não incluem bytes do Storage.

Implementar:

- versioning;
- lifecycle;
- backup/replication;
- inventory;
- checksums;
- restore de amostra;
- restore completo documentado.

## 30.4 Qdrant

Qdrant é derivado, mas recuperação precisa de:

- snapshots quando úteis;
- restore testado;
- reindex completo;
- comparação de contagens;
- retrieval golden tests.

## 30.5 Redis

Redis não é autoridade.

Testar:

- perda total;
- reconstrução de filas pelo outbox/Postgres;
- reclaim de Work Runs;
- locks expirados;
- ausência de perda durável.

## 30.6 Vault e configurações

- secrets nunca entram em dump comum;
- backup/rotation sob política específica;
- referências preservadas;
- procedimento de reconfiguração;
- break-glass auditado.

## 30.7 Evolution Go / WhatsApp

Definir backup e recuperação de:

- sessão;
- metadados;
- banco usado pelo serviço;
- pareamento;
- integração com tenant;
- comportamento quando sessão não puder ser restaurada.

## 30.8 RPO/RTO iniciais

O executor deverá propor e medir por domínio:

- dados operacionais;
- Work Runs;
- documentos;
- Artifacts;
- conhecimento;
- billing;
- sessões WhatsApp;
- índices derivados.

O Founder aprova o compromisso final.

## 30.9 Restore Drill

Executar:

1. selecionar snapshot;
2. restaurar em ambiente isolado;
3. aplicar secrets/config;
4. restaurar Storage;
5. restaurar/reconstruir Qdrant;
6. iniciar serviços;
7. executar smoke/evals;
8. medir RPO/RTO;
9. produzir Artifact;
10. apagar ambiente de teste de forma segura.

---

# 31. Incidentes e operação

## 31.1 Severidade

### P0

- vazamento de dados;
- cobrança indevida em massa;
- corrupção de ledger;
- perda de dados;
- plataforma indisponível ampla;
- secret comprometido.

### P1

- tenant bloqueado em operação crítica;
- provider central degradado;
- Work Runs perdidos;
- rollout com regressão ampla;
- restore não confiável.

### P2

- função importante degradada com workaround;
- Artifact/Research parcial;
- falha de Auxiliar específica.

### P3

- defeito menor;
- UX;
- erro isolado sem impacto crítico.

## 31.2 Runbook mínimo

Cada alerta crítico possui:

- sintomas;
- impacto;
- diagnóstico;
- contenção;
- recuperação;
- rollback;
- comunicação;
- evidence;
- owner;
- pós-incidente.

## 31.3 Comunicação

Definir templates para:

- aviso interno;
- aviso ao tenant;
- atualização;
- resolução;
- postmortem.

Sem prometer prazo não comprovado.

## 31.4 Postmortem

Sem culpabilização, contendo:

- timeline;
- impacto;
- detecção;
- causa;
- fatores contribuintes;
- resposta;
- o que funcionou;
- o que falhou;
- ações;
- owners;
- deadlines;
- novos Eval Cases.

---

# 32. Onboarding de corretora

## 32.1 Onboarding como Work Run

```text
Contrato/decisão comercial
→ criar tenant
→ owner
→ plano
→ billing
→ WhatsApp
→ Agents
→ conhecimento
→ approvers
→ conexões
→ Auxiliares
→ testes
→ treinamento
→ readiness
→ go-live tenant
```

## 32.2 Estados

```text
draft
configuring
blocked
ready_for_validation
ready
live
suspended
archived
```

## 32.3 Checks obrigatórios

- identidade da empresa;
- owner;
- usuários;
- termos;
- plano;
- billing account;
- saldo/allowance;
- AutoBrokers Core;
- Atendimento quando contratado;
- WhatsApp;
- handoff;
- approvers;
- conhecimento;
- documentos;
- conexões;
- Portais;
- Auxiliares;
- Rotinas;
- permissões;
- Briefings;
- entrega;
- suporte;
- backup aplicável;
- tenant isolation;
- smoke tests;
- treinamento.

## 32.4 Readiness não manual

O botão “pronta” não pode substituir checks.

A decisão deve guardar:

- checks;
- evidências;
- waivers;
- owner;
- data;
- release ativa;
- plano;
- rollback.

## 32.5 Artifact de onboarding

Gerar:

```text
Tenant Launch Pack
```

Com:

- configuração;
- conexões;
- capacidades;
- responsáveis;
- limites;
- suporte;
- treinamento;
- critérios de sucesso.

---

# 33. Readiness em quatro níveis

## 33.1 Platform Readiness

- infraestrutura;
- segurança;
- backup;
- restore;
- observabilidade;
- billing;
- suporte.

## 33.2 Release Readiness

- code;
- migrations;
- evals;
- performance;
- rollback;
- evidence.

## 33.3 Tenant Readiness

- configuração;
- conexão;
- dados;
- equipe;
- plano;
- testes.

## 33.4 Commercial Readiness

- oferta;
- preço;
- contrato;
- pagamento;
- cobrança;
- suporte;
- limites;
- margem.

## 33.5 Decisão

```text
GO
= todos os gates obrigatórios verdes

GO_CONDITIONAL
= somente condições não P0/P1, prazo curto, owner e mitigação

NO_GO
= qualquer bloqueador crítico, evidência ausente ou cobrança não reconciliável
```

---

# 34. Rollout final

## 34.1 Sequência

```text
Amandus
→ Resulta
→ AutoFleet
→ próxima corretora elegível
```

Essa sequência é gate interno da mesma entrega.

## 34.2 Amandus

Validar:

- todos os caminhos;
- administração;
- billing non-billable/internal;
- incident drill;
- restore smoke;
- carga inicial.

## 34.3 Resulta

Validar em operação real controlada:

- WhatsApp;
- Atendimento;
- Work Runs;
- Auxiliares;
- Briefing;
- Artifact;
- suporte;
- usage attribution;
- zero cobrança real antes da autorização.

## 34.4 AutoFleet

Validar:

- isolamento;
- segundo tenant real;
- diferenças de configuração;
- rollout;
- custos;
- operação;
- ausência de contaminação Resulta.

## 34.5 Critério temporal

Não exigir meses arbitrários.

Exigir:

- volume mínimo suficiente;
- execução dos casos críticos;
- ausência de P0/P1;
- SLO observado;
- billing reconciliado;
- suporte pronto;
- Founder approval.

## 34.6 Auto-pause

Pausar rollout quando:

- P0/P1;
- cross-tenant;
- cobrança divergente;
- error budget esgotado;
- custo fora do limite;
- Work Run perdido;
- rollback indisponível;
- provider crítico degradado;
- Founder pausar.

---

# 35. Experiências de lançamento obrigatórias

## 35.1 Chat

O corretor pergunta algo específico da corretora e recebe resposta com contexto e evidência adequados.

## 35.2 Trabalho completo

O corretor solicita uma tarefa, acompanha Work Run, aprova quando necessário e recebe resultado final.

## 35.3 Auxiliar

O corretor instala ou cria Auxiliar, configura Rotina e recebe entrega.

## 35.4 Artifact

Relatório web e PDF com números coerentes, fonte, versão e link seguro.

## 35.5 Pesquisa

Dossiê com Claims, citações, validade e fontes.

## 35.6 Proatividade

Briefing identifica situação real, explica evidência e oferece ação.

## 35.7 Portal

Jornada autenticada com HITL, evidência e side effect idempotente.

## 35.8 Atendimento

Mensagem entra no tenant correto, Atendimento responde ou faz handoff e nenhuma outra corretora vê o conteúdo.

## 35.9 Admin

Founder identifica problema, abre Cockpit, executa comando governado e confirma recuperação.

## 35.10 Billing

Usage Event é registrado, rated, reconciliado e exibido sem cobrança duplicada.

## 35.11 Recuperação

Serviço reinicia ou Redis é perdido e Work Run durável continua corretamente.

---

# 36. Serviços canônicos

Criar ou consolidar, sem runtime paralelo:

```text
EvaluationService
DatasetRegistry
EvaluatorRegistry
ReleaseEvidenceService
ReleaseGateService
OnlineEvaluationService
SLOService
UsageLedgerService
ProviderCostService
RatingService
CreditLedgerService
BillingPeriodService
InvoiceService
PaymentProviderAdapter
BillingReconciliationService
MarginService
ReadinessService
LaunchDecisionService
BackupVerificationService
OperationalDrillService
```

Esses serviços operam dentro da stack existente.

Não criar outro agente para billing ou evals quando serviço determinístico for suficiente.

---

# 37. APIs principais

## 37.1 Evals

```text
GET  /api/admin/control-plane/evals/datasets
POST /api/admin/control-plane/evals/datasets
POST /api/admin/control-plane/evals/runs
GET  /api/admin/control-plane/evals/runs/{id}
POST /api/admin/control-plane/evals/reviews/{id}/decide
```

## 37.2 Releases

```text
POST /api/admin/control-plane/releases/candidates
GET  /api/admin/control-plane/releases/{id}/evidence
POST /api/admin/control-plane/releases/{id}/evaluate
POST /api/admin/control-plane/releases/{id}/approve
POST /api/admin/control-plane/releases/{id}/rollout
POST /api/admin/control-plane/releases/{id}/rollback
```

## 37.3 Billing

```text
GET  /api/admin/control-plane/billing/overview
GET  /api/admin/control-plane/billing/usage
GET  /api/admin/control-plane/billing/reconciliation
POST /api/admin/control-plane/billing/reconciliation/run
GET  /api/admin/control-plane/billing/rate-cards
POST /api/admin/control-plane/billing/rate-cards/{id}/publish
GET  /api/admin/control-plane/billing/plans
POST /api/admin/control-plane/billing/plans/{id}/publish
GET  /api/admin/control-plane/billing/invoices
POST /api/admin/control-plane/billing/adjustments/preview
POST /api/admin/control-plane/billing/adjustments/execute
```

## 37.4 Readiness

```text
GET  /api/admin/control-plane/readiness/platform
GET  /api/admin/control-plane/readiness/releases/{id}
GET  /api/admin/control-plane/readiness/companies/{id}
POST /api/admin/control-plane/readiness/assess
POST /api/admin/control-plane/launch-decisions/preview
POST /api/admin/control-plane/launch-decisions/execute
```

## 37.5 Regras

Todas obedecem:

- server-side auth;
- RBAC;
- tenant scope;
- Admin Command Gateway;
- idempotência;
- ETag/version;
- audit;
- redaction;
- correlation id;
- human-readable errors.

---

# 38. Portal Admin — superfícies finais

A SPEC-061 deve ganhar, dentro de **Governança** e **Financeiro**, as seguintes superfícies:

## 38.1 Evals

- datasets;
- versões;
- casos;
- evaluators;
- runs;
- falhas;
- human review;
- comparação de releases;
- custo.

## 38.2 Release Readiness

- manifesto;
- gates;
- Evidence Pack;
- waivers;
- canários;
- error budget;
- rollback.

## 38.3 SLOs

- SLIs;
- targets;
- janela;
- budget;
- burn rate;
- incidentes;
- freshness.

## 38.4 Billing

- planos;
- rate cards;
- usage;
- créditos;
- assinaturas;
- invoices;
- pagamentos;
- reconciliação;
- exceptions;
- histórico pre-launch.

## 38.5 Unit Economics

- receita;
- custos;
- margem;
- custo por tenant;
- custo por Work Run;
- custo por Skill;
- providers;
- alertas.

## 38.6 Resilience

- backups;
- última verificação;
- restore drills;
- RPO/RTO;
- runbooks;
- incidentes.

## 38.7 Onboarding e Readiness

- checklist;
- tenants;
- bloqueios;
- evidências;
- launch decision.

A UI não pode permitir alterar ledger diretamente por formulário genérico.

---

# 39. Testes obrigatórios de billing

- usage event duplicado;
- webhook repetido;
- webhook fora de ordem;
- provider event sem ID;
- retry;
- quantidade negativa;
- rate card inexistente;
- rate card expirada;
- FX ausente;
- rounding;
- allowance;
- bônus;
- expiration;
- top-up;
- refund;
- reversal;
- mudança de plano;
- trial;
- cancelamento;
- grace;
- saldo insuficiente;
- concorrência de débito;
- invoice duplicada;
- pagamento duplicado;
- pagamento parcial;
- chargeback;
- reconciliation exception;
- histórico non-billable;
- tenant isolation;
- admin permission;
- audit.

---

# 40. Testes obrigatórios de resiliência

- restart da API;
- restart do worker;
- Redis indisponível;
- Redis perdido;
- Postgres conexão intermitente;
- Qdrant indisponível;
- MinIO indisponível;
- provider LLM indisponível;
- WhatsApp indisponível;
- Firecrawl/Tavily indisponível;
- Artifact renderer indisponível;
- timeout de Portal;
- Work Run stale;
- approval durante restart;
- outbox replay;
- restore Postgres;
- restore Storage;
- rebuild Qdrant;
- rotação de secret;
- rollback de migration;
- rollback de release.

---

# 41. Plano de execução em três blocos

## Bloco A — Release Evidence, Evals, CI/CD, Observabilidade e SLOs

Implementar:

- preflight das SPECs 054–061;
- inventário dos testes;
- runner unificado;
- classificação por domínio e risco;
- datasets;
- versions;
- Eval Cases;
- evaluators;
- calibration;
- Eval Runs;
- Release Candidates;
- release manifests;
- gates;
- Evidence Packs;
- CI/CD;
- secret/dependency/container scans;
- OTel;
- integração LangSmith;
- dashboards;
- SLIs;
- benchmark;
- SLO proposal;
- error budget;
- online evaluation;
- feedback loop;
- Control Plane.

### Gate A

- todos os testes existentes inventariados;
- suíte essencial automatizada;
- datasets críticos publicados;
- P0 deterministic gates ativos;
- release manifest reproduzível;
- Evidence Pack gerado;
- tracing ponta a ponta;
- SLO baseline medido;
- zero secret no dataset;
- zero cross-tenant;
- SPEC-054 crítica verde;
- Amandus passa baseline.

## Bloco B — Billing, Planos, Uso, Reconciliação e Unit Economics

Implementar:

- inventário do billing legado;
- snapshot dos 1.235 logs;
- commercial boundary;
- Usage Ledger;
- provider cost events;
- pricing freshness;
- Rate Cards;
- Credit Ledger;
- migration dos bônus;
- plans versionados;
- entitlements;
- subscriptions;
- billing periods;
- rated usage;
- invoice records;
- payment adapter;
- webhooks idempotentes;
- reconciliation;
- exceptions;
- refunds/adjustments;
- FinOps;
- margin;
- budget;
- tenant UI;
- Admin UI;
- testes completos.

### Gate B

- nenhum log histórico cobrado automaticamente;
- boundary registrado;
- usage idempotente;
- zero cobrança duplicada;
- credits reconciliam;
- invoices reconciliam;
- provider cost separado de customer price;
- plano comercial aprovado pelo Founder;
- sandbox preservado;
- Resulta/AutoFleet não recebem cobrança antes de autorização;
- margem calculável;
- rollback financeiro possível;
- security gates verdes.

## Bloco C — Resiliência, Onboarding, Readiness, Rollout e Go-Live

Implementar:

- load tests;
- thresholds;
- capacity plan;
- security review final;
- backup inventory;
- PITR/dumps;
- MinIO/Storage backup;
- Qdrant restore/rebuild;
- Redis loss drill;
- restore drill completo;
- RPO/RTO;
- incident runbooks;
- support process;
- onboarding Work Run;
- Tenant Launch Pack;
- readiness assessments;
- Amandus canary;
- Resulta canary;
- AutoFleet canary;
- correções;
- final Evidence Pack;
- Launch Decision;
- activation;
- comercialização autorizada;
- relatório final.

### Gate C

- load thresholds verdes;
- restore comprovado;
- RPO/RTO medidos;
- runbooks disponíveis;
- Admin operacional;
- onboarding operacional;
- Amandus verde;
- Resulta verde;
- AutoFleet verde;
- zero P0/P1 aberto;
- billing reconciliado;
- commercial catalog aprovado;
- rollback pronto;
- Founder emite `GO`.

---

# 42. APPLY / VERIFY / ROLLBACK

## 42.1 APPLY

Cada bloco deve possuir:

- branch;
- commit inicial;
- migrations versionadas;
- backup;
- ordem de deploy;
- flags temporárias;
- canário;
- execução de evals;
- documentação.

## 42.2 VERIFY

Verificar:

- schema;
- constraints;
- RLS;
- writes;
- ledgers;
- evals;
- traces;
- billing;
- security;
- load;
- restore;
- canários;
- Broker Outcome Regression Pack.

## 42.3 ROLLBACK

Todo bloco precisa definir:

- código anterior;
- migration backward/forward fix;
- feature flag;
- restore;
- ledger reversal;
- provider rollback;
- release rollback;
- tenant impact;
- comunicação.

Billing nunca é revertido apagando histórico.

Usar reversal/adjustment.

---

# 43. Definition of Done

A SPEC-062 somente termina quando:

1. as SPECs 054–061 foram implementadas ou formalmente comprovadas;
2. nenhum P0/P1 bloqueador permanece;
3. suíte de testes está unificada;
4. datasets críticos estão versionados;
5. evaluators estão versionados;
6. LLM judges estão calibrados;
7. Release Candidate existe;
8. Release Manifest existe;
9. Release Evidence Pack existe;
10. gates P0 são determinísticos;
11. CI bloqueia falhas críticas;
12. online evaluation funciona;
13. feedback vira Eval Case governado;
14. OTel funciona;
15. LangSmith está correlacionado;
16. SLIs existem;
17. baseline foi medido;
18. SLOs foram aprovados;
19. error budget policy funciona;
20. usage event é idempotente;
21. 1.235 logs históricos foram classificados;
22. nenhuma cobrança retroativa automática ocorreu;
23. commercial boundary existe;
24. provider costs possuem freshness;
25. Rate Cards são versionadas;
26. planos são versionados;
27. preços foram aprovados pelo Founder;
28. entitlements derivam de plano/assinatura;
29. Credit Ledger é append-only;
30. bônus de R$ 25,00 foram preservados com provenance;
31. assinaturas funcionam;
32. billing periods funcionam;
33. rated usage funciona;
34. invoice records funcionam;
35. payment webhooks são idempotentes;
36. reconciliação funciona;
37. exceptions são operáveis;
38. refunds/adjustments funcionam;
39. zero cobrança duplicada;
40. margem por tenant é calculável;
41. custo por Work Run é calculável;
42. custo por Skill/Tool/provider é calculável;
43. load tests foram executados;
44. thresholds passam;
45. capacity plan existe;
46. security review final passa;
47. Supabase backup foi verificado;
48. Storage/MinIO backup foi verificado;
49. restore Postgres foi testado;
50. restore de bytes foi testado;
51. Qdrant foi restaurado ou reconstruído;
52. Redis loss drill passou;
53. RPO foi medido;
54. RTO foi medido;
55. runbooks existem;
56. incident severities existem;
57. onboarding Work Run funciona;
58. Tenant Launch Pack é gerado;
59. readiness é baseado em evidência;
60. Amandus passou;
61. Resulta passou;
62. AutoFleet passou;
63. zero cross-tenant foi observado;
64. chat funciona;
65. Atendimento funciona;
66. WhatsApp funciona;
67. Work Runs funcionam;
68. approvals funcionam;
69. Auxiliares/Rotinas funcionam;
70. Artifacts funcionam;
71. Research funciona;
72. Briefings funcionam;
73. Portais funcionam nos casos homologados;
74. Admin Control Plane funciona;
75. billing tenant UI funciona;
76. rollback foi testado;
77. Launch Decision foi emitida;
78. `GO` foi aprovado pelo Founder;
79. release está ativa em produção;
80. venda está autorizada apenas para capacidades realmente operacionais;
81. relatório final foi publicado.

---

# 44. Saídas documentais obrigatórias

A execução deverá produzir:

```text
FINAL-SPEC-062-EXECUTION-REPORT.md
RELEASE-EVIDENCE-PACK
SECURITY-READINESS-REPORT
LOAD-CAPACITY-REPORT
BILLING-RECONCILIATION-REPORT
UNIT-ECONOMICS-REPORT
BACKUP-RESTORE-DRILL-REPORT
INCIDENT-RUNBOOKS
TENANT-ONBOARDING-RUNBOOK
TENANT-LAUNCH-PACK-TEMPLATE
GO-LIVE-DECISION
ROLLBACK-RUNBOOK
```

Todos devem ficar ligados à Release Candidate.

---

# 45. Decisões comerciais que permanecem com o Founder

Antes da ativação de cobrança, apresentar ao Founder:

1. nomes dos planos;
2. preços em R$;
3. periodicidade;
4. trial;
5. capabilities por plano;
6. allowances;
7. top-ups;
8. hard stop;
9. grace period;
10. política de suspensão;
11. refund;
12. descontos;
13. grandfathering;
14. impostos;
15. forma de pagamento;
16. contrato e termos;
17. suporte incluído;
18. retenção;
19. limite de usuários;
20. limite de Auxiliares/Research/Artifacts.

A LLM pode propor cenários e unit economics.

Não pode aprovar em nome do Founder, contador ou advogado.

---

# 46. Referências oficiais incorporadas

A implementação deve consultar as versões atuais de:

- LangSmith Evaluation: https://docs.langchain.com/langsmith/evaluation-concepts
- Google SRE — SLOs e error budgets: https://sre.google/workbook/implementing-slos/
- OpenTelemetry: https://opentelemetry.io/docs/concepts/observability-primer/
- k6 thresholds: https://grafana.com/docs/k6/latest/using-k6/thresholds/
- OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
- Supabase Backups: https://supabase.com/docs/guides/platform/backups
- Supabase Production Checklist: https://supabase.com/docs/guides/deployment/going-into-prod
- PostgreSQL Backup/Restore: https://www.postgresql.org/docs/current/backup.html
- Stripe usage-based billing, quando Stripe permanecer contratado: https://docs.stripe.com/billing/subscriptions/usage-based

A documentação externa orienta padrões.

As autoridades de produto continuam sendo as SPECs canônicas do AutoBrokers.

---

# 47. Encerramento do programa arquitetural

A SPEC-062 encerra a sequência arquitetural 052–062.

Depois de sua aprovação documental:

```text
Não criar automaticamente SPEC-063.

Executar as SPECs 054–062 em linha reta.
Gerar relatório final de cada SPEC.
Corrigir diferenças encontradas.
Produzir Visual Acceptance Packs das SPECs 057 e 061.
Obter decisões comerciais do Founder no Bloco B da SPEC-062.
Emitir Launch Decision.
```

Uma futura SPEC somente deve ser criada para:

- novo domínio de produto;
- nova integração estratégica;
- nova capacidade não coberta;
- mudança material aprovada pelo Founder.

Não para adiar a execução do programa já definido.

---

# 48. Declaração final

```text
O AutoBrokers não estará pronto porque a documentação diz que está.

Estará pronto quando:
- executar o trabalho real da corretora;
- proteger os dados;
- sobreviver a falhas;
- medir qualidade;
- cobrar corretamente;
- gerar margem compreensível;
- permitir suporte e rollback;
- e comprovar tudo isso com evidências reproduzíveis.
```
