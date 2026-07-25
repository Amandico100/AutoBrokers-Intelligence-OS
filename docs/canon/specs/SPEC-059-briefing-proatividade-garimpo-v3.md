# SPEC-059 — AutoBrokers Briefing, Proatividade & Garimpo v3

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANÔNICA E AUTORIZADA PARA EXECUÇÃO — aprovada pelo Founder em 24/07/2026  
**Autoridade superior:** `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`, `SPEC-053-autobrokers-work-os-core-harness.md`, `SPEC-054-foundation-hardening-schema-governance.md`, `SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`, `SPEC-056-skill-registry-tool-gateway.md`, `SPEC-057-artifact-hub-report-studio.md` e `SPEC-058-auxiliary-routine-factory.md`  
**Runtime preservado:** Smith + LangGraph/LangChain + FastAPI + Supabase/Postgres + Redis + Qdrant + MinIO  
**Nome oficial do agente central:** **AutoBrokers**  
**Escopo:** consolidar o sistema operacional de inteligência proativa: sinais, evidências, diagnósticos, briefings, alertas, recomendações, Garimpo v3, demanda agregada, feedback, medição de resultado e conexão com Work Runs, Skills, Artifacts e Auxiliary Factory.  
**Natureza desta SPEC:** autoriza migrations, backend, APIs, UI, regras, detectores, Skills, Artifacts, migração do legado, deploy, cutover e ativação em produção.  
**Dependência de execução:** as SPECs 054–058 devem estar implementadas ou ser executadas no mesmo programa, respeitando a ordem canônica.

---

# 0. Comando direto ao executor — Fable, Opus, Codex ou equivalente

Você está autorizado a **implementar integralmente esta SPEC em linha reta**.

Esta não é uma SPEC para criar um painel bonito de “insights”, enviar uma mensagem genérica por semana, inventar oportunidades com LLM ou manter um motor proativo desligado indefinidamente.

Ao final da mesma iniciativa:

- o AutoBrokers deverá produzir um Briefing Diário útil e personalizado;
- o AutoBrokers deverá produzir um Briefing Executivo Semanal com dados reais;
- sinais críticos deverão gerar alertas somente quando houver evidência e policy;
- gargalos, riscos, oportunidades e demandas deverão ser detectados e priorizados;
- toda afirmação operacional relevante deverá apontar para evidência;
- fato, inferência, recomendação e hipótese deverão aparecer claramente separados;
- sugestões repetidas, irrelevantes ou sem mudança deverão ser suprimidas;
- o corretor deverá poder aceitar, rejeitar, dispensar, adiar ou pedir explicação;
- recomendações aceitas deverão criar Work Runs, Rotinas ou propostas de Auxiliares pelo caminho canônico;
- ações externas deverão respeitar HITL, `work_effects`, idempotência, orçamento e Vault;
- resultados deverão ser medidos quando possível, sem inventar ROI;
- o Garimpo deverá entender dores, desejos, tarefas repetitivas, pedidos, lacunas e sinais de churn;
- pedidos recorrentes deverão alimentar o Auxiliary Factory e o roadmap de produto;
- conhecimento durável elegível deverá seguir o fluxo de Knowledge Candidates da SPEC-052;
- o Portal Admin deverá permitir administrar sinais, regras, briefings, demandas, qualidade e resultados;
- os schedulers diretos históricos deverão convergir para Rotinas + Work Runs;
- Amandus, Resulta e AutoFleet deverão passar pelos critérios de lançamento;
- a funcionalidade deverá permanecer ativa em produção ao encerrar o programa.

## 0.1 Doutrina de lançamento

```text
Detectar com regras e dados reais.
Explicar com evidência.
Priorizar com critérios explícitos.
Recomendar somente o que pode ser executado.
Executar pelo Work OS quando autorizado.
Medir o resultado.
Aprender sem transformar inferência em verdade.
```

Não criar:

- outro scheduler;
- outro Work Run;
- outro Artifact Hub;
- outro Auxiliary Factory;
- outro sistema de memória;
- outro publisher de conhecimento;
- outro “motor de sugestões” paralelo;
- uma tabela nova para cada detector;
- recomendações baseadas apenas em texto persuasivo de LLM;
- números, percentuais ou ROI sem cálculo rastreável;
- mensagem proativa sem dedupe, cooldown ou limite;
- alertas críticos baseados somente em inferência de modelo;
- acesso global a conversas brutas de corretoras;
- armazenamento global de PII ou citações identificáveis;
- envio externo automático quando a policy exigir aprovação;
- captura de comportamento para manipulação comercial obscura;
- status de “sucesso” quando o resultado não foi medido;
- versão beta permanentemente desligada.

Feature flags são permitidas apenas para rollback e corte controlado durante a mesma iniciativa. A entrega não termina enquanto o caminho canônico estiver permanentemente desativado.

## 0.2 Número de blocos

A execução deverá ocorrer em **três blocos macro**, o menor número compatível com migração, segurança e lançamento:

1. **Bloco A — Signal Intelligence Foundation, Garimpo v3 e migração estrutural**;
2. **Bloco B — Briefings, recomendações, feedback, UI e integração operacional**;
3. **Bloco C — regras iniciais, cutover, canários, ajuste de ruído e lançamento**.

Com os gates verdes, avançar automaticamente.

## 0.3 Saída obrigatória

Ao final deverão existir e estar ativos:

- envelope canônico de evento/sinal;
- registro único de sinais normalizados;
- evidências rastreáveis;
- motor de deduplicação e agrupamento;
- Findings/diagnósticos com ciclo de vida;
- recomendações governadas;
- ações propostas ligadas a Skills, Work Runs, Rotinas e Auxiliares;
- perfis de briefing por empresa e usuário;
- Briefing Diário;
- Briefing Executivo Semanal;
- alertas críticos event-driven;
- briefing sob demanda pelo chat;
- Artifact de briefing web e PDF quando aplicável;
- feedback explícito do usuário;
- medição de outcome;
- Garimpo v3 tenant-scoped;
- demanda global anonimizada e agregada;
- clusters de pedidos e capability gaps;
- integração com Knowledge Candidates sem publicação direta;
- quiet hours, cooldown, frequência e limites;
- Centro de Briefing no dashboard;
- administração mínima no Portal Admin;
- migração de `proactive_suggestions.py`, `weekly_report.py`, `regression_sentinel.py` e `broker_insights.py` para adapters do pipeline canônico;
- remoção do envio semanal genérico como autoridade de proatividade;
- Amandus, Resulta e AutoFleet validados;
- relatório final de execução publicado.

---

# 1. Ordem de leitura e autoridade

Antes de editar código ou banco:

1. atualizar a `main`;
2. registrar commit inicial;
3. ler SPEC-052;
4. ler SPEC-053;
5. ler SPEC-054 e relatório final;
6. ler SPEC-055 e relatório final;
7. ler SPEC-056 e relatório final;
8. ler SPEC-057 e relatório final;
9. ler SPEC-058 e relatório final;
10. ler ADR-001, ADR-002 e ADR-003;
11. ler SPEC-034, SPEC-035, SPEC-036, SPEC-037, SPEC-040 e SPEC-049 apenas como histórico subordinado;
12. ler o código real de Garimpo, sugestões, relatório semanal, atividades, Auditor, Sentinela de Regressão, scheduler, Admin Insights, Work Runs, Skills, Artifacts, Auxiliary Factory, approvals, billing e delivery;
13. confirmar schema vivo em modo read-only;
14. confirmar volumes, fontes e qualidade atuais;
15. confirmar comportamento de Amandus, Resulta e AutoFleet.

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
→ SPECs posteriores subordinadas
→ ADRs e documentos históricos quando não conflitarem
→ código atual como estado de implementação
```

Em conflito, não criar outra arquitetura.

---

# 2. Visão de produto

O corretor não precisa de um sistema que apenas diga:

> “Talvez você devesse olhar seus atendimentos.”

Ele precisa receber:

- o que aconteceu;
- por que importa;
- quais evidências sustentam a conclusão;
- qual é o impacto provável;
- o que precisa de decisão agora;
- qual ação pode resolver;
- quanto custa executar;
- o que o AutoBrokers pode fazer por ele;
- qual resultado foi obtido depois.

A promessa desta SPEC é:

> **O AutoBrokers observa os sinais autorizados da corretora, transforma ruído em prioridades claras, propõe ações executáveis, realiza o trabalho quando autorizado e mede o resultado.**

## 2.1 O produto proativo correto

Proatividade não é enviar mais mensagens.

Proatividade é:

```text
perceber mudança relevante
→ comprovar
→ explicar
→ priorizar
→ oferecer uma ação real
→ executar com autorização
→ medir se ajudou
```

## 2.2 Diferencial vertical

A inteligência poderá utilizar, quando disponível e autorizada:

- atendimentos;
- qualidade de conversas;
- atividades executadas;
- Work Runs;
- approvals;
- Rotinas;
- Auxiliares;
- artifacts;
- integridade de conexões;
- InfoCap;
- Quiver e futuros sistemas de gestão;
- dados de cobrança;
- portais de seguradoras;
- Atlas;
- documentos;
- conhecimento global e tenant;
- feedback dos corretores;
- pesquisas externas futuras da SPEC-060.

O diferencial não será “ter insights de IA”. Será relacionar esses sinais a ações reais do ecossistema de seguros.

## 2.3 Resultado para a corretora

A corretora deverá sentir:

- “sei o que exige minha atenção hoje”;
- “não preciso procurar o problema em cinco telas”;
- “o sistema explica por que isso importa”;
- “posso mandar o AutoBrokers resolver”;
- “vejo o que foi feito e qual resultado gerou”;
- “não recebo alertas inúteis toda hora”.

---

# 3. Estado atual auditado e peças preservadas

## 3.1 Snapshot read-only de 24/07/2026

No Supabase vivo, antes da implementação desta SPEC:

- `broker_insights`: **0 registros**;
- `agent_activities`: **113 registros**;
- `conversation_scorecards`: **9 registros**;
- `observed_events`: **177 registros**;
- `observed_sessions`: **8 registros**;
- `approval_requests`: **8 registros**;
- corretoras não técnicas: **2**.

Distribuição observada de `agent_activities`:

- `atendimentos`: 108;
- `qualidade`: 4;
- `auxiliares`: 1.

Esse snapshot prova duas coisas:

1. já existem fontes reais úteis;
2. o volume ainda é pequeno e não autoriza inferências estatísticas agressivas.

A implementação não pode inventar profundidade que os dados ainda não sustentam.

## 3.2 Peças reais que devem ser preservadas

Preservar e evoluir:

- `broker_insights.py` como evidência histórica de captura;
- regex determinística de dores, desejos, pedidos e churn;
- refinamento LLM em lote com custo controlado;
- `proactive_suggestions.py` como adapter histórico;
- `weekly_report.py` como adapter histórico de entrega;
- `regression_sentinel.py` e seu detector determinístico;
- `conversation_scorecards`;
- `agent_activities`;
- `observed_events` e `observed_sessions` como fontes restritas;
- `activity_log.py`;
- `conversation_auditor`;
- `platform_outbound`;
- heartbeats;
- `app/admin/insights/page.tsx` como referência de superfície;
- `admin_spec034.py` como API histórica;
- Work Runs;
- Work Events;
- Skills e Tool Gateway;
- Artifact Hub;
- Auxiliary Factory;
- approvals;
- Vault;
- billing e tracing.

## 3.3 Problemas atuais que esta SPEC corrige

1. O Garimpo captura apenas frases isoladas e não forma um modelo operacional de demanda.
2. `broker_insights` mistura captura, sugestão e histórico em um schema mínimo.
3. A IA de Sugestões envia uma mensagem semanal com três blocos fixos.
4. O relatório semanal conta atividades, mas não gera diagnóstico executivo completo.
5. A Sentinela de Regressão envia WhatsApp diretamente, fora do Work Run e do pipeline de recomendação.
6. Os jobs proativos são registrados diretamente no APScheduler histórico.
7. Redis é usado como marcador de periodicidade, sem autoridade durável de publicação.
8. Não existe objeto canônico de sinal, finding, recomendação, briefing ou outcome.
9. Não existe evidência ligada formalmente a cada recomendação.
10. Não existe dedupe semântico robusto, cooldown por assunto ou supressão por ausência de mudança.
11. Não existe medição confiável da utilidade da recomendação.
12. O Admin atual mostra ranking superficial, sem decisão, outcome ou qualidade.
13. O corretor ainda não possui uma página clara de prioridades do dia.
14. Dados de fontes diferentes não têm um envelope comum.
15. Não há distinção técnica forte entre fato, inferência, recomendação e hipótese.
16. O sistema ainda não transforma demandas repetidas em candidatos governados a Auxiliares/Skills.
17. Tabelas históricas relevantes não possuem a governança completa exigida pela SPEC-054.

---

# 4. Leis centrais desta SPEC

1. **Todo alerta relevante deve possuir evidência.**
2. **Toda recomendação deve declarar confiança, risco e validade.**
3. **A LLM sintetiza; dados e regras comprovam.**
4. **Ausência de dado não significa zero.**
5. **Inferência não pode ser apresentada como fato.**
6. **Recomendação não é execução.**
7. **Execução ocorre pelo Work OS.**
8. **Toda ação externa sensível passa por policy/HITL.**
9. **Todo resultado mensurável deve voltar ao ciclo.**
10. **Resultado não medido é inconclusivo, não sucesso.**
11. **Garimpo não publica conhecimento global.**
12. **Demanda de produto não é memória nem RAG.**
13. **Preferência pessoal não vira verdade da corretora sem confirmação.**
14. **Alert fatigue é falha de produto.**
15. **Mensagens proativas devem respeitar horário, frequência e papel.**
16. **O usuário pode dispensar, adiar ou explicar relevância.**
17. **Sinais globais derivados de tenants são agregados e anonimizados.**
18. **Nenhum dado de outra corretora aparece em briefing, sinal ou recomendação.**
19. **Nenhum detector cria um novo scheduler ou runtime.**
20. **A mesma evidência não pode gerar ações duplicadas.**

---

# 5. Ontologia oficial

## 5.1 Event

Fato técnico ou de domínio emitido por um sistema autorizado.

Exemplo:

```text
work_run.failed
connector.degraded
approval.requested
conversation.closed
artifact.published
```

## 5.2 Signal Candidate

Possível indício extraído de um ou mais eventos, dados ou conversas, ainda não validado.

## 5.3 Intelligence Signal

Sinal normalizado, tenant-scoped, com tipo, evidência, confiança, janela e dedupe.

## 5.4 Evidence Reference

Referência segura e rastreável à fonte que sustenta o sinal.

Não é obrigatoriamente uma cópia do dado bruto.

## 5.5 Finding

Diagnóstico consolidado derivado de sinais relacionados.

Exemplos:

- “A qualidade do atendimento caiu de forma relevante”;
- “Existem aprovações paradas há mais de 24 horas”;
- “A mesma tarefa foi pedida quatro vezes nesta semana”.

## 5.6 Recommendation

Proposta governada de decisão ou ação para tratar um Finding ou aproveitar uma oportunidade.

## 5.7 Action Proposal

Ação concreta executável por Skill, Work Run, Rotina, Auxiliar, Artifact ou aprovação.

## 5.8 Briefing

Composição personalizada e priorizada de Findings, resultados, approvals e recomendações.

## 5.9 Alert

Entrega imediata de um Finding que ultrapassou o threshold de criticidade e relevância.

## 5.10 Garimpo

Sistema de captura e compreensão da voz dos corretores: dores, desejos, pedidos, tarefas repetitivas, objeções, dúvidas, satisfação e risco de churn.

## 5.11 Demand Cluster

Agrupamento anonimizado de necessidades semelhantes vindas de múltiplos pedidos/fontes.

## 5.12 Outcome

Resultado observado após uma recomendação ou ação.

## 5.13 Knowledge Candidate

Candidato a conhecimento durável definido pela SPEC-052. Não é sinônimo de Signal, Finding ou Demand Cluster.

---

# 6. Arquitetura canônica

```text
Eventos / dados vivos / conversas / Work Runs / approvals
                          │
                          ▼
                  Signal Collectors
                          │
                          ▼
            Redaction + Normalization + Dedupe
                          │
                          ▼
                  Intelligence Signals
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
        Rule Engine    Garimpo v3   Detectors
             │            │            │
             └────────────┼────────────┘
                          ▼
                  Findings Engine
                          │
                          ▼
          Priority + Confidence + Evidence
                          │
             ┌────────────┼─────────────┐
             ▼            ▼             ▼
       Briefing       Recommendation    Alert
             │            │             │
             └────────────┼─────────────┘
                          ▼
       Work Run / Skill / Auxiliary / Routine / HITL
                          │
                          ▼
             Artifact + Delivery + Outcome
                          │
                          ▼
          Feedback + Quality + Demand + Learning
```

## 6.1 Autoridades

| Responsabilidade | Autoridade |
|---|---|
| evento durável de execução | Work Events / domain events canônicos |
| sinal normalizado | `intelligence_signals` |
| evidência | `intelligence_signal_evidence` |
| diagnóstico consolidado | `intelligence_findings` |
| recomendação | `recommendations` |
| feedback/decisão | `recommendation_responses` |
| outcome | `recommendation_outcomes` |
| perfil de briefing | `briefing_profiles` |
| publicação de briefing | `briefing_publications` |
| itens do briefing | `briefing_items` |
| regras/detectores configuráveis | `intelligence_rules` |
| demanda agregada | `demand_clusters` |
| execução | `work_runs` |
| artifacts | Artifact Hub |
| ações | Skill Registry + Tool Gateway |
| Auxiliares/Rotinas | Auxiliary Factory |
| memória e conhecimento | SPEC-052 |
| segredos | Vault |

## 6.2 Serviços

Criar/consolidar:

```text
backend/app/services/intelligence/
```

Componentes mínimos:

- `event_adapter.py`;
- `signal_service.py`;
- `redaction_service.py`;
- `evidence_service.py`;
- `dedupe_service.py`;
- `rule_engine.py`;
- `finding_engine.py`;
- `priority_service.py`;
- `recommendation_service.py`;
- `briefing_service.py`;
- `delivery_policy.py`;
- `feedback_service.py`;
- `outcome_service.py`;
- `garimpo_v3.py`;
- `demand_cluster_service.py`;
- `knowledge_candidate_adapter.py`;
- `legacy_adapter.py`;
- `policy.py`;
- `schemas.py`;
- `detectors/`.

Nenhum desses serviços cria outro runtime. Eles produzem ou consomem Work Runs, Skills e Artifacts.

---

# 7. Envelope canônico de evento

Todo evento consumido deverá ser normalizado para:

```text
schema_version
event_id
event_type
company_id
user_id nullable
actor_type
actor_id nullable
source_system
subject_type
subject_id nullable
occurred_at
ingested_at
correlation_id nullable
causation_id nullable
work_run_id nullable
conversation_id nullable
sensitivity
payload_classification
payload_ref nullable
payload_summary_redacted
metadata
```

## 7.1 Regras

- `company_id` obrigatório para eventos tenant-scoped;
- eventos globais não podem carregar PII de tenant;
- payload bruto sensível deve ficar na fonte original;
- o pipeline armazena referência e resumo redigido;
- `event_id` e `dedupe_key` impedem reprocessamento;
- eventos externos entram somente depois de autenticação e normalização;
- eventos sem origem confiável não podem gerar alerta crítico sozinho.

## 7.2 Eventos iniciais

- `work_run.created`;
- `work_run.started`;
- `work_run.failed`;
- `work_run.completed`;
- `work_run.stale`;
- `approval.requested`;
- `approval.expiring`;
- `approval.decided`;
- `connector.degraded`;
- `connector.expired`;
- `routine.failed`;
- `routine.paused`;
- `auxiliary.degraded`;
- `artifact.published`;
- `artifact.viewed`;
- `artifact.delivery_failed`;
- `conversation.closed`;
- `conversation.scorecard_created`;
- `attendance.backlog_changed`;
- `portal_job.needs_human`;
- `portal_job.failed`;
- `budget.threshold_reached`;
- `broker.request_detected`;
- `capability_gap.detected`;
- `recommendation.accepted`;
- `recommendation.dismissed`;
- `outcome.measured`.

---

# 8. Fontes e níveis de confiança

## 8.1 Tiers de evidência

### Tier 0 — dado vivo autoritativo

- banco operacional;
- InfoCap/Quiver por conector homologado;
- status de provider;
- Work Run persistido;
- approval persistida;
- artifact persistido.

### Tier 1 — evento determinístico do sistema

- falha registrada;
- mudança de status;
- deadline vencido;
- contador calculado;
- health check.

### Tier 2 — documento oficial/Evidence Pack

- apólice;
- documento oficial;
- condição geral válida;
- evidência de portal;
- fonte oficial.

### Tier 3 — análise derivada reproduzível

- média;
- variação;
- tendência;
- cluster;
- score calculado;
- detecção de anomalia determinística.

### Tier 4 — declaração do corretor

- desejo;
- dor;
- pedido;
- preferência;
- feedback explícito.

### Tier 5 — inferência da LLM

- hipótese;
- interpretação;
- síntese;
- possível causa;
- sugestão estratégica.

## 8.2 Regra de apresentação

- Tier 0–3 podem sustentar fatos quando válidos;
- Tier 4 sustenta “o corretor declarou”, não um fato universal;
- Tier 5 nunca aparece como fato;
- alertas críticos exigem Tier 0/1/2 ou combinação equivalente;
- recomendações estratégicas podem usar Tier 5, mas devem exibir confiança e base.

## 8.3 Contradição

Quando fontes relevantes contradizerem:

- marcar o Finding como `conflicted`;
- não executar ação sensível;
- mostrar a divergência;
- solicitar validação ou fonte adicional;
- registrar lineage.

---

# 9. Taxonomia de sinais

Tipos iniciais:

```text
operational_backlog
work_failure
work_stale
approval_pending
connection_health
provider_health
budget_risk
data_quality
attendance_quality
customer_experience
portal_blocker
commercial_opportunity
cost_saving_opportunity
process_automation_opportunity
broker_pain
broker_desire
feature_request
repeated_task
knowledge_gap
capability_gap
churn_risk
positive_outcome
compliance_risk
security_risk
research_update_future
```

Cada sinal declara:

- `signal_type`;
- domínio;
- assunto;
- subject;
- janela temporal;
- evidências;
- confiança;
- severidade;
- impacto estimado;
- urgência;
- actionability;
- freshness;
- recorrência;
- escopo;
- dedupe key;
- validade;
- status.

---

# 10. Modelo de dados canônico

Todas as migrations seguem APPLY/VERIFY/ROLLBACK da SPEC-054.

## 10.1 `intelligence_signals`

```text
id uuid PK
company_id uuid NOT NULL FK companies
user_id uuid NULL
signal_type text NOT NULL
domain text NOT NULL
subject_type text NOT NULL
subject_id text NULL
source_type text NOT NULL
source_ref text NULL
summary_redacted text NOT NULL
status text NOT NULL
severity text NOT NULL
confidence numeric NOT NULL
impact_score numeric NULL
urgency_score numeric NULL
actionability_score numeric NULL
recurrence_score numeric NULL
freshness_score numeric NULL
priority_score numeric NULL
trust_tier integer NOT NULL
window_start timestamptz NULL
window_end timestamptz NULL
dedupe_key text NOT NULL
fingerprint text NOT NULL
valid_until timestamptz NULL
correlation_id text NULL
causation_id text NULL
work_run_id uuid NULL
conversation_id uuid NULL
metadata jsonb NOT NULL DEFAULT '{}'
created_at timestamptz NOT NULL
updated_at timestamptz NOT NULL
```

Constraints:

- confidence entre 0 e 1;
- scores entre 0 e 100;
- unique parcial por `(company_id, dedupe_key, status ativo)` conforme estratégia segura;
- FK company;
- RLS tenant;
- nenhum payload sensível bruto em `metadata`.

Estados:

```text
candidate
validated
clustered
promoted
suppressed
expired
invalidated
```

## 10.2 `intelligence_signal_evidence`

```text
id uuid PK
company_id uuid NOT NULL
signal_id uuid NOT NULL FK intelligence_signals
evidence_type text NOT NULL
source_system text NOT NULL
source_ref text NOT NULL
trust_tier integer NOT NULL
summary_redacted text NOT NULL
value_snapshot jsonb NOT NULL DEFAULT '{}'
content_hash text NULL
observed_at timestamptz NOT NULL
valid_until timestamptz NULL
sensitivity text NOT NULL
created_at timestamptz NOT NULL
```

Regras:

- `source_ref` precisa ser autorizável;
- snapshot contém somente o necessário;
- não copiar transcript inteiro;
- evidência removida da fonte não pode ficar exposta por link público;
- acesso auditado.

## 10.3 `intelligence_findings`

```text
id uuid PK
company_id uuid NOT NULL
user_id uuid NULL
finding_type text NOT NULL
title text NOT NULL
summary text NOT NULL
fact_statement text NULL
inference_statement text NULL
status text NOT NULL
severity text NOT NULL
confidence numeric NOT NULL
priority_score numeric NOT NULL
impact_summary text NULL
why_now text NOT NULL
valid_from timestamptz NOT NULL
valid_until timestamptz NULL
dedupe_key text NOT NULL
cluster_key text NULL
owner_user_id uuid NULL
acknowledged_at timestamptz NULL
resolved_at timestamptz NULL
dismissed_at timestamptz NULL
snoozed_until timestamptz NULL
resolution_summary text NULL
metadata jsonb NOT NULL DEFAULT '{}'
created_at timestamptz NOT NULL
updated_at timestamptz NOT NULL
```

Estados:

```text
draft
active
acknowledged
snoozed
resolved
dismissed
expired
invalidated
conflicted
```

## 10.4 `intelligence_finding_signals`

Liga Findings aos Signals:

```text
finding_id
signal_id
role
weight
created_at
```

## 10.5 `recommendations`

```text
id uuid PK
company_id uuid NOT NULL
user_id uuid NULL
finding_id uuid NULL
recommendation_type text NOT NULL
title text NOT NULL
summary text NOT NULL
rationale text NOT NULL
confidence numeric NOT NULL
risk_level text NOT NULL
priority_score numeric NOT NULL
status text NOT NULL
action_options jsonb NOT NULL
recommended_action_key text NULL
selected_action_key text NULL
skill_release_id uuid NULL
tenant_auxiliary_id uuid NULL
routine_id uuid NULL
work_run_id uuid NULL
artifact_id uuid NULL
approval_required boolean NOT NULL
approval_request_id uuid NULL
estimated_cost_brl_min numeric NULL
estimated_cost_brl_max numeric NULL
measurement_plan jsonb NOT NULL DEFAULT '{}'
expires_at timestamptz NULL
delivered_at timestamptz NULL
viewed_at timestamptz NULL
accepted_at timestamptz NULL
rejected_at timestamptz NULL
created_at timestamptz NOT NULL
updated_at timestamptz NOT NULL
```

Estados:

```text
draft
eligible
delivered
viewed
accepted
rejected
snoozed
executing
executed
measured
expired
withdrawn
```

## 10.6 `recommendation_responses`

```text
id
company_id
recommendation_id
user_id
action
reason_code nullable
comment_redacted nullable
snoozed_until nullable
selected_action_key nullable
created_work_run_id nullable
created_routine_id nullable
created_tenant_auxiliary_id nullable
created_at
```

Ações:

```text
acknowledge
accept
reject
dismiss
snooze
not_relevant
already_solved
wrong_data
need_explanation
ask_autobrokers
```

## 10.7 `recommendation_outcomes`

```text
id
company_id
recommendation_id
work_run_id nullable
measurement_type
measurement_status
baseline jsonb
observed jsonb
calculation jsonb
automation_level
confidence
value_summary
measured_at
confirmed_by_user_id nullable
created_at
updated_at
```

Estados:

```text
pending
in_progress
realized
partially_realized
inconclusive
negative
expired
```

`automation_level`:

```text
automated
confirmed
estimated
```

## 10.8 `briefing_profiles`

```text
id
company_id
user_id nullable
scope
name
is_active
timezone
cadence
schedule_spec
channels
recipient_refs
quiet_hours
severity_threshold
max_items
max_pushes_per_day
enabled_categories
disabled_categories
detail_level
include_completed_results
include_suggested_automations
sensitive_data_policy
created_by_user_id
created_at
updated_at
```

Scopes:

```text
company
personal
role
platform_default
```

## 10.9 `briefing_publications`

```text
id
company_id
user_id nullable
briefing_profile_id nullable
briefing_type
period_start
period_end
status
work_run_id
artifact_id nullable
summary_text
item_count
critical_count
recommendation_count
content_hash
delivery_status
published_at
expires_at nullable
created_at
```

## 10.10 `briefing_items`

```text
id
company_id
briefing_publication_id
item_type
finding_id nullable
recommendation_id nullable
work_run_id nullable
artifact_id nullable
position
section
headline
summary
action_label nullable
priority_score
created_at
```

## 10.11 `intelligence_rules`

```text
id
rule_key UNIQUE
name
description
signal_type
scope
version
status
implementation_kind
configuration
minimum_evidence
minimum_confidence
cooldown_seconds
validity_seconds
severity_mapping
owner
created_at
updated_at
```

`implementation_kind`:

```text
deterministic_sql
deterministic_python
statistical
llm_assisted
hybrid
```

Regra publicada é versionada. Mudança relevante cria nova versão/release ou histórico equivalente.

## 10.12 `intelligence_events`

Timeline append-only:

- signal.created;
- signal.validated;
- signal.suppressed;
- finding.created;
- finding.escalated;
- finding.acknowledged;
- finding.resolved;
- recommendation.created;
- recommendation.delivered;
- recommendation.accepted;
- recommendation.dismissed;
- action.started;
- action.completed;
- outcome.measured;
- briefing.published;
- demand.clustered;
- knowledge_candidate.proposed.

## 10.13 `demand_clusters`

```text
id
cluster_key UNIQUE
category
canonical_problem
canonical_outcome
status
tenant_count
request_count
first_seen_at
last_seen_at
impact_score
frequency_score
feasibility_score
risk_score
candidate_auxiliary_key nullable
candidate_skill_key nullable
capability_gap_summary jsonb
reviewed_by_user_id nullable
created_at
updated_at
```

## 10.14 `demand_cluster_members`

Liga de forma redigida:

- `auxiliary_requests`;
- `capability_gaps`;
- `intelligence_signals`;
- `broker_insights` legado;
- feedbacks explícitos.

Não armazena conversa integral nem PII global.

## 10.15 `broker_insights` histórico

Decisão:

- preservar durante a migração;
- contar registros no preflight;
- transformar escritores históricos em adapters;
- migrar cada registro elegível para `intelligence_signals`;
- manter `broker_insights` como view/projeção de compatibilidade ou tabela read-only temporária;
- nenhuma nova feature deve usar `broker_insights` como autoridade após o cutover.

Como o snapshot auditado estava vazio, a migração tende a ser simples, mas o executor deve confirmar o volume no momento da execução.

---

# 11. Dedupe, agrupamento e validade

## 11.1 Dedupe determinístico

Cada sinal terá uma chave baseada em:

```text
company_id
+ signal_type
+ subject_type/subject_id
+ regra/versão
+ janela temporal
+ parâmetros relevantes normalizados
```

## 11.2 Dedupe semântico

Para dores, desejos e pedidos:

- embeddings ou classificação semântica podem auxiliar;
- o conteúdo permanece tenant-scoped;
- comparação global usa representação anonimizada;
- threshold deve ser testado;
- merge deve preservar lineage.

## 11.3 Cooldown

Um Finding não será reenviado quando:

- não houver evidência nova;
- prioridade não aumentar;
- prazo não estiver próximo;
- usuário já tiver dispensado dentro do cooldown;
- ação já estiver em andamento.

## 11.4 Escalonamento legítimo

Pode reenviar antes do fim do cooldown quando:

- severidade aumentar;
- indicador piorar acima do threshold;
- novo prazo crítico surgir;
- aprovação estiver prestes a expirar;
- provider voltar a falhar depois de recuperação;
- ação anterior falhar.

## 11.5 Expiração

Signals, Findings e Recommendations devem expirar conforme domínio.

Não mostrar oportunidade antiga como nova.

---

# 12. Priorização

## 12.1 Dimensões

Cada Finding recebe 0–100 em:

- impacto;
- urgência;
- confiança;
- actionability;
- recorrência;
- freshness;
- alinhamento estratégico.

## 12.2 Fórmula inicial

```text
priority_score =
  impacto * 0.30
+ urgência * 0.20
+ confiança * 0.15
+ actionability * 0.15
+ recorrência * 0.10
+ freshness * 0.05
+ alinhamento * 0.05
- penalidades
```

Penalidades possíveis:

- evidência insuficiente;
- fonte stale;
- contradição;
- repetição;
- baixa relevância para o papel;
- ação já em andamento;
- usuário dispensou recentemente.

## 12.3 Níveis

```text
P0 crítico: >= 85 e critério de risco crítico satisfeito
P1 alto: 70–84
P2 médio: 50–69
P3 informativo: < 50
```

- P0 pode gerar alerta imediato conforme policy;
- P1 entra no topo do briefing e pode gerar push;
- P2 entra no briefing;
- P3 fica no histórico/agregado, salvo pedido explícito.

## 12.4 Não usar score cego

O score não substitui regra de domínio.

Exemplo: cobertura securitária, obrigação legal, segurança e vazamento de dados exigem gates próprios, mesmo com score alto.

---

# 13. Findings e separação entre fato e inferência

Cada Finding deve possuir quatro blocos internos:

```text
FACTS
INFERENCES
UNKNOWN / MISSING DATA
RECOMMENDED NEXT STEP
```

## 13.1 Exemplo correto

**Fato:** 7 Work Runs falharam nas últimas 24 horas, todos ligados ao mesmo conector.  
**Inferência:** a conexão pode estar degradada.  
**Dado faltante:** o provider ainda não confirmou incidente.  
**Próximo passo:** testar a conexão e pausar as Rotinas dependentes se a falha persistir.

## 13.2 Exemplo proibido

> “Seu sistema está quebrado e você está perdendo clientes.”

Sem evidência de perda de clientes, a frase é proibida.

## 13.3 Causas

Causa raiz só pode ser afirmada quando:

- houver evidência suficiente;
- a regra for determinística; ou
- um humano confirmar.

Caso contrário usar “possível causa”.

---

# 14. Recommendation Contract

Toda recomendação apresentada deve responder:

1. O que aconteceu?
2. Por que isso importa agora?
3. Quais evidências sustentam?
4. Qual a confiança?
5. Qual ação é recomendada?
6. O AutoBrokers pode executar?
7. O que exige aprovação?
8. Quanto pode custar?
9. Qual resultado será medido?
10. Até quando é relevante?

## 14.1 Opções de ação

Uma recomendação pode oferecer:

- abrir detalhes;
- conversar com o AutoBrokers;
- criar Work Run;
- executar Skill;
- instalar Auxiliar;
- criar Rotina;
- aprovar ação pendente;
- abrir Artifact;
- atribuir responsável;
- dispensar;
- adiar;
- marcar como irrelevante;
- informar que já foi resolvido.

## 14.2 Ação executável

Só mostrar CTA “Resolver” quando existir caminho real:

```text
Skill publicada
+ capabilities
+ conexão
+ dados mínimos
+ budget
+ policy
+ Work Run
```

Caso contrário mostrar:

- o que está faltando;
- o que pode ser feito agora;
- se a demanda foi registrada.

## 14.3 Aprovação

Recomendação aceita não significa aprovação de todo side effect futuro.

A aprovação deve respeitar:

- ação;
- destinatário;
- volume;
- valor;
- fingerprint;
- validade;
- revisão do Auxiliar;
- policy vigente.

---

# 15. Política de proatividade e combate a ruído

## 15.1 Quiet hours

Padrão inicial por tenant/user:

```text
20:00–08:00 no timezone configurado
```

Exceções:

- segurança;
- risco crítico;
- operação explicitamente 24h;
- usuário opt-in.

## 15.2 Limites padrão

- máximo de 3 pushes proativos não críticos por usuário/dia;
- no máximo 1 recomendação sobre o mesmo Finding dentro do cooldown;
- itens P2/P3 agrupados no briefing;
- mensagens sem ação clara não geram push;
- nenhuma pergunta semanal genérica obrigatória.

## 15.3 Preferências

O usuário pode:

- escolher canais;
- escolher horário;
- escolher frequência;
- reduzir categorias;
- aumentar threshold;
- pausar briefings;
- manter alertas críticos obrigatórios conforme papel/policy;
- escolher nível de detalhe.

## 15.4 Feedback negativo

`not_relevant`, `wrong_data` e `already_solved` devem:

- ajustar dedupe/cooldown;
- alimentar qualidade;
- não apagar evidência;
- não virar memória global;
- não reduzir thresholds críticos de segurança sem revisão.

## 15.5 Transparência

Toda mensagem proativa deve indicar por que apareceu:

> “Mostrei isso porque existem 4 aprovações aguardando há mais de 24 horas.”

---

# 16. Produto Briefing

## 16.1 Briefing Diário Operacional

Objetivo:

> dizer o que precisa de atenção hoje, o que já foi resolvido e o que pode ser delegado.

Estrutura:

1. **Resumo do dia em uma frase**;
2. **Precisa de você**;
3. **Riscos e bloqueios**;
4. **Oportunidades**;
5. **Trabalhos em andamento**;
6. **Resultados concluídos**;
7. **Automação sugerida**;
8. **Dados ausentes/importantes**.

Limites:

- 5–7 itens principais por padrão;
- ordem por prioridade;
- sem repetir informação;
- sem preencher seção vazia com texto genérico;
- links para detalhes.

## 16.2 Briefing Executivo Semanal

Objetivo:

> entregar visão gerencial, mudanças, decisões e impacto da semana.

Seções:

- resumo executivo;
- indicadores disponíveis;
- principais mudanças;
- gargalos;
- qualidade;
- trabalhos e Auxiliares;
- custos;
- resultados;
- riscos;
- oportunidades;
- decisões recomendadas;
- plano da próxima semana.

Formatos:

- web autenticado;
- PDF;
- resumo no chat/WhatsApp/e-mail;
- dados e cálculos via Artifact Hub.

O relatório histórico de sábado vira adapter/compatibilidade. O novo briefing não depende apenas de `agent_activities`.

## 16.3 Alerta crítico

Entrega imediata quando:

- threshold crítico;
- evidência suficiente;
- não suprimido;
- usuário/papel elegível;
- canal autorizado.

O alerta contém:

- problema;
- impacto;
- evidência curta;
- ação recomendada;
- CTA;
- timestamp;
- link para detalhes.

## 16.4 Briefing sob demanda

No chat:

> “O que precisa da minha atenção hoje?”

O AutoBrokers executa a Skill de briefing, consulta Signals/Findings/Work Runs e responde com dados atuais.

## 16.5 Briefing pessoal

Mostra somente:

- itens do usuário;
- approvals que ele pode decidir;
- Auxiliares pessoais;
- tarefas atribuídas;
- dados company-level permitidos pelo papel.

## 16.6 Briefing por cargo

### Owner/gestor

- riscos;
- custos;
- gargalos;
- resultados;
- oportunidades;
- decisões;
- saúde da operação.

### Operação

- pendências;
- filas;
- approvals;
- bloqueios;
- trabalhos falhos;
- próximos passos.

### Atendimento/supervisão

- conversas paradas;
- qualidade;
- handoffs;
- SLA;
- padrões de falha.

### Financeiro/cobrança

- pendências autorizadas;
- resultados de cobrança;
- falhas de entrega;
- approvals;
- custos operacionais permitidos.

Não assumir cargo somente por texto livre. Usar role/policy configurada.

---

# 17. Artifact e entrega do Briefing

## 17.1 Artifact types

Registrar templates no Artifact Hub:

```text
briefing.daily_operational
briefing.weekly_executive
briefing.critical_alert_detail
briefing.opportunity_dossier
briefing.demand_radar_admin
```

## 17.2 Um único conteúdo

```text
snapshot
→ cálculos
→ findings
→ recomendações
→ Briefing Spec
→ web/PDF/resumo
```

Web, PDF e mensagem curta devem usar a mesma publicação.

## 17.3 Canais iniciais

- dashboard;
- chat;
- WhatsApp;
- e-mail;
- link autorizado.

## 17.4 Delivery

Usar:

- `artifact_deliveries`;
- `work_effects`;
- recipient refs;
- approval policy;
- idempotency.

Nunca armazenar destino sensível diretamente no template global.

## 17.5 Leitura e reconhecimento

Registrar:

- entregue;
- aberto;
- item clicado;
- Finding reconhecido;
- recomendação aceita/dispensada.

Sem tracking invasivo fora da finalidade operacional.

---

# 18. Garimpo v3

## 18.1 Objetivo

Entender continuamente:

- dores;
- desejos;
- pedidos de funcionalidade;
- tarefas repetitivas;
- metas;
- objeções;
- dúvidas recorrentes;
- reclamações;
- elogios;
- risco de churn;
- oportunidades de automação;
- lacunas de dados, tools e conectores.

## 18.2 Fontes permitidas

- mensagens do corretor ao AutoBrokers;
- feedback explícito;
- pedidos de Auxiliares;
- tarefas repetidas no chat;
- rejeições e comentários de recomendações;
- solicitações de suporte;
- eventos de uso do produto agregados;
- motivos de pausa/desinstalação.

Não usar como voz do corretor:

- conversa do segurado;
- transcript de seguradora;
- evento do Observador sem autorização e finalidade;
- conteúdo de outro tenant;
- dado pessoal de cliente.

## 18.3 Pipeline

```text
mensagem/evento
→ redaction
→ candidate extraction
→ intent/kind
→ outcome desejado
→ tarefa/frequência
→ confidence
→ dedupe tenant
→ intelligence_signal
→ auxiliary_request/capability_gap quando aplicável
→ cluster global anonimizado
```

## 18.4 Camadas

### Camada A — determinística

Preservar e ampliar padrões para:

- desejo explícito;
- dor;
- pedido;
- repetição;
- urgência;
- churn;
- elogio;
- pedido de automação;
- “faça isso sempre”;
- “todo dia/semana/mês”.

### Camada B — LLM estruturada

Usar Skill/model policy econômica para:

- detectar necessidade implícita;
- resumir outcome;
- classificar categoria;
- separar problema de solução sugerida;
- identificar frequência;
- sugerir cluster.

A saída deve passar por schema e validação.

### Camada C — clustering

- tenant-level para repetição;
- global com conteúdo anonimizado;
- merge revisável;
- lineage preservado;
- nenhuma publicação automática.

## 18.5 Quote e retenção

- quote literal fica somente tenant-scoped;
- UI Admin global não mostra quote bruto por padrão;
- retenção de quote deve ser limitada;
- resumo global não pode identificar empresa/pessoa;
- fonte original continua protegida por policy;
- PII removida antes de qualquer LLM não autorizada.

## 18.6 Saídas

O Garimpo pode gerar:

- Signal;
- Finding tenant;
- `auxiliary_request`;
- `capability_gap`;
- Demand Cluster;
- feedback de produto;
- Knowledge Candidate elegível.

Não pode:

- publicar template global;
- criar Skill global;
- alterar RAG;
- alterar prompt de produção;
- enviar campanha;
- executar side effect.

---

# 19. Demand Radar e expansão do arsenal

## 19.1 Objetivo

Descobrir o que as corretoras querem delegar e quais novas capacidades realmente justificam investimento.

## 19.2 Score de demanda

Cada cluster pode receber:

- frequência;
- número de tenants;
- recorrência;
- impacto econômico;
- tempo manual estimado;
- capacidade atual;
- complexidade;
- risco;
- custo de provider;
- potencial de retenção;
- possibilidade de template global.

## 19.3 Estados

```text
new
triaged
researching
planned
building
released
rejected
merged
```

## 19.4 Promoção

```text
Demand Cluster
→ revisão de produto
→ definição de outcome
→ decidir Skill/Auxiliar/Tool/Conector
→ SPEC ou release subordinada
→ evals
→ Founder approval
→ publicação
```

## 19.5 Relação com Auxiliary Factory

Quando uma demanda já pode ser atendida:

- sugerir template existente;
- propor instalação;
- propor Rotina;
- executar Work Run único.

Quando não pode:

- registrar gap;
- explicar alternativa atual;
- não fingir automação.

---

# 20. Outcome Loop

## 20.1 Fluxo

```text
Recommendation
→ usuário aceita
→ Work Run/Rotina/Auxiliar
→ resultado/artifact/effect
→ janela de observação
→ medição
→ feedback
→ outcome
→ ajuste de qualidade
```

## 20.2 Measurement Plan

Antes de executar, quando aplicável, registrar:

- métrica;
- baseline;
- fonte;
- janela;
- target;
- método;
- limitações;
- responsável;
- forma de confirmação.

## 20.3 Exemplos mensuráveis

- backlog antes/depois;
- approvals concluídas;
- Work Runs recuperados;
- mensagens preparadas/enviadas;
- tempo até resolução;
- falhas reduzidas;
- artifact aberto;
- conexão recuperada;
- custo evitado calculável;
- tarefa repetitiva automatizada.

## 20.4 Tempo economizado

Pode ser estimado apenas quando:

- houver duração manual de referência;
- método estiver registrado;
- label for `estimated`;
- não for apresentado como fato financeiro.

## 20.5 Receita e ROI

Não afirmar receita gerada sem evidência.

Categorias:

```text
attributed
influenced
estimated
unmeasured
```

## 20.6 Resultado negativo

Se uma recomendação piorar o processo:

- registrar `negative`;
- pausar regra quando necessário;
- investigar;
- não ocultar;
- ajustar evals;
- comunicar quando impactar usuário.

---

# 21. Integração com Learning Fabric da SPEC-052

## 21.1 O que pode virar Knowledge Candidate

- procedimento estável observado em múltiplas fontes;
- mudança operacional confirmada;
- dúvida recorrente com resposta oficial;
- padrão de qualidade validado;
- conhecimento de domínio com fonte;
- aprendizado de seguradora confirmado.

## 21.2 O que não vira Knowledge Candidate

- desejo individual;
- preferência pessoal;
- reclamação isolada;
- feature request;
- score de produto;
- recomendação estratégica momentânea;
- dado operacional expirável;
- PII;
- conversa integral.

## 21.3 Fluxo

```text
Signal/Finding elegível
→ Knowledge Candidate
→ anonimização/classificação
→ dedupe/contradição
→ Curador/Conselho
→ Publicador
```

Garimpo, detector ou recomendação nunca publica diretamente.

---

# 22. Integração com Work OS

## 22.1 Work Runs

Toda geração relevante deverá criar Work Run:

- briefing sob demanda;
- briefing agendado;
- análise complexa;
- recomendação aceita;
- medição de outcome;
- clusterização pesada;
- artifact.

Detectores leves podem produzir Signals sem Work Run individual, mas processamento relevante e side effects devem ser rastreáveis.

## 22.2 Skills

Skills iniciais:

```text
intelligence.generate_daily_briefing
intelligence.generate_weekly_executive_briefing
intelligence.synthesize_finding
intelligence.create_recommendation
intelligence.measure_outcome
intelligence.cluster_broker_demand
intelligence.propose_automation
intelligence.explain_priority
```

Cada Skill possui schema, fontes, policy, budget e evals.

## 22.3 Tool Gateway

Somente tools autorizadas para a fase atual:

- leitura de Work Runs;
- leitura de approvals;
- leitura de atividades;
- leitura de scorecards;
- leitura de connections/health;
- leitura de Auxiliares/Rotinas;
- Artifact Hub;
- Auxiliary Factory;
- delivery governado;
- InfoCap/Quiver quando homologados.

## 22.4 Auxiliary Factory

Uma Recommendation pode propor:

- Work Run único;
- Rotina;
- instalação de Auxiliar;
- criação de Auxiliar custom;
- capability gap.

A proposta usa o Factory da SPEC-058, não cria objeto diretamente.

## 22.5 Artifacts

Briefings e dossiês usam o Artifact Hub.

## 22.6 Approvals

Ações sensíveis usam `approval_requests` evoluída pela SPEC-055.

---

# 23. Detectores iniciais de lançamento

Não começar com dezenas. Implementar detectores reais e testáveis.

## 23.1 Aprovação parada

Condição inicial configurável:

- approval pendente acima de janela;
- ainda válida;
- usuário elegível.

Ação:

- Finding;
- item no briefing;
- push quando P1/P0;
- CTA “Revisar”.

## 23.2 Work Run falhando repetidamente

- mesma categoria/provider;
- falhas acima de threshold;
- excluir cancelamentos intencionais;
- agrupar por causa provável.

Ação:

- diagnóstico;
- conexão/tool relacionada;
- pausar trigger dependente se policy permitir;
- oferecer investigação.

## 23.3 Work Run stale

- lease/heartbeat vencido;
- status não terminal;
- recovery ainda não concluiu.

Ação:

- iniciar recuperação automática da SPEC-055;
- alertar somente se recuperação falhar ou exigir humano.

## 23.4 Conexão degradada/expirada

- health real;
- dependências afetadas;
- Auxiliares/Rotinas impactados.

Mensagem:

> “A conexão do WhatsApp expirou. O Analista Executivo e duas Rotinas estão pausados até a reconexão.”

## 23.5 Regressão de qualidade

Preservar lógica determinística do `regression_sentinel.py`, evoluindo para:

- Signal;
- evidência de scorecards;
- Finding;
- recomendação;
- Work Run de investigação;
- delivery governado.

Não enviar WhatsApp diretamente depois do cutover.

## 23.6 Atendimentos parados

Somente quando houver definição de “parado” por estado/canal e dados suficientes.

- excluir encerrados;
- considerar horário útil;
- agrupar;
- não revelar PII no briefing geral.

## 23.7 Auxiliar/Rotina degradado

- falhas consecutivas;
- provider ou conexão;
- budget;
- artifact/delivery.

Ação:

- pausar gatilho afetado;
- não desinstalar;
- orientar correção;
- retomar depois da resolução.

## 23.8 Budget próximo do limite

- threshold configurável;
- projeção transparente;
- sem alarmismo;
- mostrar principais consumidores.

## 23.9 Artifact pronto e não entregue

- artifact publicado;
- delivery falhou ou não ocorreu;
- retry/idempotência;
- alerta somente quando relevante.

## 23.10 Tarefa repetida

- mesma intenção executada várias vezes;
- janela e frequência;
- confidence suficiente.

Ação:

> “Você pediu este relatório quatro vezes nas últimas duas semanas. Posso criar uma Rotina semanal para deixá-lo pronto automaticamente.”

## 23.11 Capability gap recorrente

- múltiplos pedidos;
- nenhuma capacidade homologada;
- registrar Demand Cluster;
- mostrar alternativa disponível.

## 23.12 Resultado positivo

- Work Run concluído;
- artifact entregue;
- objetivo mensurável.

Entrar no briefing como resultado, sem spam de congratulação a cada ação pequena.

---

# 24. Briefing Spec

Cada publicação terá payload estruturado:

```text
schema_version
briefing_type
company_id
user_id nullable
profile_id
period
headline
executive_summary
sections[]
  key
  title
  items[]
    item_type
    priority
    finding_ref
    recommendation_ref
    evidence_summary
    confidence
    action
completed_results[]
missing_data[]
methodology
sources_summary
created_at
valid_until
```

## 24.1 Regras narrativas

- linguagem objetiva e humana;
- sem jargão técnico por padrão;
- números com período e fonte;
- sem repetir headline no corpo;
- recomendações com verbo de ação;
- explicar incerteza;
- no máximo uma frase comercial leve;
- sem prometer resultado garantido.

## 24.2 Dados insuficientes

Exemplo correto:

> “Ainda não há conversas auditadas suficientes para comparar a qualidade desta semana.”

Exemplo proibido:

> “A qualidade permaneceu estável.”

---

# 25. Criação e gestão pelo dashboard

## 25.1 Navegação tenant

A experiência mínima:

```text
Dashboard/Home
└── Prioridades de hoje

Briefing
├── Hoje
├── Esta semana
├── Oportunidades
└── Histórico
```

Não criar dezenas de menus.

## 25.2 Card na Home

Mostrar:

- resumo do dia;
- até 3 prioridades;
- approvals;
- trabalhos em risco;
- botão “Ver briefing completo”;
- botão “Perguntar ao AutoBrokers”.

## 25.3 Página Hoje

- precisa de você;
- riscos;
- oportunidades;
- em andamento;
- concluído;
- automações sugeridas.

## 25.4 Página Esta semana

- Artifact do briefing executivo;
- KPIs disponíveis;
- mudanças;
- decisões;
- plano de ação.

## 25.5 Oportunidades

Cada card:

- título;
- por que apareceu;
- evidência;
- impacto;
- confiança;
- ação;
- custo estimado;
- validade;
- feedback.

## 25.6 Histórico

- briefings;
- alerts;
- recomendações;
- ações;
- outcomes;
- filtros.

## 25.7 Preferências

- horário;
- canais;
- frequência;
- categorias;
- detalhe;
- quiet hours;
- destinatários permitidos.

## 25.8 Chat

O AutoBrokers deve entender:

- “O que precisa da minha atenção?”;
- “Por que você está me mostrando isso?”;
- “Resolva isso”;
- “Crie uma rotina para evitar que aconteça de novo”;
- “Não quero mais este tipo de alerta”;
- “Me lembre amanhã”;
- “Isso já foi resolvido”.

Todas as ações usam tools canônicas.

---

# 26. Portal Admin mínimo desta SPEC

A SPEC-061 consolidará o Control Plane completo, mas esta SPEC deve entregar administração funcional.

## 26.1 Central de Inteligência

Visão geral:

- sinais nas últimas 24h/7d;
- Findings ativos;
- recomendações entregues;
- taxa de aceitação;
- taxa de dismiss;
- outcomes medidos;
- falsos positivos;
- briefings publicados;
- delivery failures;
- custo;
- fontes degradadas.

## 26.2 Sinais

Filtros:

- tenant;
- tipo;
- severidade;
- confiança;
- fonte;
- regra;
- status;
- período.

Ações:

- abrir evidência redigida;
- invalidar;
- suprimir;
- reprocessar;
- ver lineage.

## 26.3 Findings e recomendações

- prioridade;
- evidência;
- status;
- ação proposta;
- resposta;
- Work Run;
- outcome;
- expiração;
- custo.

## 26.4 Briefings

- publicação;
- perfil;
- tenant/user;
- conteúdo redigido;
- artifact;
- entrega;
- abertura;
- falha;
- reprocessar.

## 26.5 Garimpo e Demand Radar

- dores mais frequentes;
- desejos;
- tarefas repetidas;
- capability gaps;
- clusters;
- número de tenants;
- impacto;
- candidato a Skill/Auxiliar;
- status de produto.

Ações:

- fundir clusters;
- separar cluster;
- rejeitar ruído;
- encaminhar para Auxiliary Factory;
- propor Knowledge Candidate;
- criar item de roadmap;
- marcar resolvido.

## 26.6 Regras e detectores

- versão;
- status;
- threshold;
- precisão;
- falsos positivos;
- custo;
- tenants afetados;
- último run;
- health.

Ações:

- ativar/desativar;
- rollout;
- rollback;
- replay;
- executar evals;
- alterar configuração permitida.

## 26.7 Privacidade

O Admin mostra agregado/redigido por padrão.

Acesso a evidência tenant sensível:

- justificativa;
- role;
- audit log;
- menor privilégio;
- sem download massivo.

## 26.8 Linguagem humana

Mostrar:

> “Esta recomendação foi dispensada porque o problema já estava resolvido.”

Não mostrar por padrão:

> `finding status transitioned due to response code 4092`.

---

# 27. APIs e tools

## 27.1 Tenant

```text
GET    /api/intelligence/briefing/current
GET    /api/intelligence/briefings
GET    /api/intelligence/briefings/{id}
POST   /api/intelligence/briefings/generate
GET    /api/intelligence/findings
GET    /api/intelligence/findings/{id}
POST   /api/intelligence/findings/{id}/acknowledge
POST   /api/intelligence/findings/{id}/snooze
POST   /api/intelligence/findings/{id}/dismiss
GET    /api/intelligence/recommendations
GET    /api/intelligence/recommendations/{id}
POST   /api/intelligence/recommendations/{id}/respond
POST   /api/intelligence/recommendations/{id}/execute
GET    /api/intelligence/preferences
PUT    /api/intelligence/preferences
GET    /api/intelligence/outcomes
```

## 27.2 Admin

```text
GET    /api/admin/intelligence/overview
GET    /api/admin/intelligence/signals
GET    /api/admin/intelligence/findings
GET    /api/admin/intelligence/recommendations
GET    /api/admin/intelligence/briefings
GET    /api/admin/intelligence/demand-clusters
PATCH  /api/admin/intelligence/demand-clusters/{id}
GET    /api/admin/intelligence/rules
POST   /api/admin/intelligence/rules/{id}/validate
POST   /api/admin/intelligence/rules/{id}/rollout
POST   /api/admin/intelligence/rules/{id}/rollback
POST   /api/admin/intelligence/replay
GET    /api/admin/intelligence/quality
```

## 27.3 Tools do Core

```text
intelligence.get_briefing
intelligence.list_findings
intelligence.explain_finding
intelligence.list_recommendations
intelligence.respond_recommendation
intelligence.execute_recommendation
intelligence.update_preferences
intelligence.generate_briefing
intelligence.report_feedback
```

Todas passam pelo Tool Gateway.

## 27.4 Regras

- autenticação server-side;
- company scope;
- role/policy;
- idempotency key;
- schema validation;
- ETag/version quando editável;
- audit event;
- resposta humana + código estável;
- nenhum acesso cross-tenant;
- nenhuma query livre enviada pelo client.

---

# 28. Scheduling e triggers

## 28.1 Regra

Depois do cutover, o APScheduler histórico não é autoridade para briefings, Garimpo e sugestões.

Usar:

```text
Rotina/trigger
→ Work Run
→ Skill
→ Artifact/Delivery
```

## 28.2 Cadências iniciais

- Briefing Diário: agenda configurável, padrão de manhã;
- Briefing Semanal: agenda configurável;
- Garimpo: batch/event-driven governado;
- Outcome measurement: conforme janela;
- alertas críticos: event-driven;
- clustering global: batch de plataforma por Work Run.

## 28.3 Estado durável

Não depender somente de marcador Redis.

Publicação deve ser idempotente por:

```text
profile_id + briefing_type + period_start + period_end
```

## 28.4 Falhas

- provider indisponível: retry Work Run;
- Artifact falhou: não marcar publicado;
- delivery falhou: artifact continua disponível;
- source degradada: briefing declara limitação;
- sem dados: publica somente quando houver conteúdo útil ou pedido explícito.

---

# 29. Migração do legado

## 29.1 `broker_insights.py`

- preservar regex e testes úteis;
- mover extração para `garimpo_v3`;
- gravar Signals/auxiliary requests;
- transformar função antiga em adapter temporário;
- manter custo controlado;
- remover autoridade direta de `broker_insights` após cutover.

## 29.2 `proactive_suggestions.py`

- parar de montar mensagem fixa como autoridade;
- migrar para Recommendation + Briefing;
- delivery via Work Run/Artifact/Delivery;
- manter fallback apenas dentro da Skill e sem inventar conteúdo;
- remover envio direto após cutover.

## 29.3 `weekly_report.py`

- preservar contagem determinística como uma fonte;
- migrar para Briefing Executivo/Artifact Hub;
- mensagem WhatsApp vira resumo com link;
- remover scheduler direto após cutover.

## 29.4 `regression_sentinel.py`

- preservar algoritmo determinístico;
- emitir Signal/Finding;
- executar delivery pelo pipeline;
- remover envio direto depois do cutover.

## 29.5 `activity_log.py`

- preservar feed comercial;
- emitir evento canônico quando apropriado;
- não usar Activity como única evidência de outcome.

## 29.6 Scheduler histórico

Remover os jobs diretos de:

- Garimpo;
- sugestões;
- relatório semanal;
- regressão, quando migrado.

Não remover outros jobs fora do escopo.

## 29.7 Admin Insights histórico

- migrar `/api/admin/spec034/insights` para APIs canônicas;
- substituir ranking superficial;
- preservar rota temporária como adapter quando necessário;
- remover microcopy que promete insight sem dado.

---

# 30. Privacidade, segurança e LGPD

## 30.1 Minimização

- armazenar somente o necessário;
- usar referências para fontes sensíveis;
- redigir PII;
- limitar retenção de quotes;
- separar tenant de agregado global;
- não enviar dados sensíveis em briefing geral.

## 30.2 Observador

`observed_events` e `observed_sessions` não podem alimentar demanda global do corretor.

Uso permitido somente quando:

- finalidade operacional definida;
- tenant correto;
- dados minimizados;
- política e retenção aplicadas;
- nenhum contato do cliente aparece no briefing gerencial sem necessidade.

## 30.3 Dados sensíveis

- apólice;
- CPF;
- telefone;
- placa;
- sinistro;
- saúde;
- financeiro;
- credencial.

Devem permanecer fora de resumos amplos salvo necessidade, role e policy.

## 30.4 Segurança

- RLS;
- FK company;
- service role governada;
- logs redigidos;
- audit trail;
- signed URLs;
- Vault;
- no secret em metadata;
- no cross-tenant joins sem filtro;
- testes negativos obrigatórios.

## 30.5 Decisões de alto risco

Cobertura, indenização, obrigação legal, compliance e segurança:

- fonte oficial;
- Evidence Pack;
- confidence alta;
- humano responsável;
- nenhuma execução automática baseada só em recomendação.

---

# 31. Model policy e custos

## 31.1 Determinístico primeiro

Usar código/SQL para:

- contagens;
- thresholds;
- prazos;
- status;
- variações;
- dedupe;
- regras;
- prioridade base;
- saúde.

## 31.2 Modelo econômico

Usar para:

- classificar pedidos;
- resumir sinais;
- agrupar semanticamente;
- redigir briefing;
- explicar recomendação.

## 31.3 Modelo forte

Usar somente para:

- síntese executiva complexa;
- múltiplas fontes contraditórias;
- recomendação estratégica de alto valor;
- criação/revisão de regra ou template, fora do runtime comum.

## 31.4 Budget

Todo Work Run deve registrar:

- custo de modelo;
- custo de provider;
- custo de artifact;
- custo de delivery;
- tenant;
- briefing/recommendation;
- Skill;
- Tool.

## 31.5 Proibição

Não usar LLM em cada evento quando uma regra determinística resolve.

---

# 32. Observabilidade e métricas

## 32.1 Pipeline

- eventos ingeridos;
- sinais criados;
- sinais suprimidos;
- Findings ativos;
- recomendações criadas;
- briefings publicados;
- delivery success;
- latência;
- custo;
- erros;
- source health.

## 32.2 Qualidade

- precisão por regra;
- falsos positivos;
- dismiss rate;
- `wrong_data` rate;
- aceitação;
- execução;
- outcome positivo;
- outcome negativo;
- inconclusivos;
- repetição indesejada;
- usuário que desativa categoria;
- tempo até ação;
- tempo até valor.

## 32.3 Métricas de produto

- pedidos capturados;
- clusters;
- gaps resolvidos;
- Auxiliares instalados a partir de recomendação;
- Rotinas criadas;
- uso recorrente;
- retenção do Auxiliar;
- custo por resultado.

## 32.4 Alertas internos

- regra gerando volume anormal;
- queda de aceitação;
- `wrong_data` acima do threshold;
- delivery falhando;
- source stale;
- custo fora do padrão;
- cross-tenant test falhou;
- detector silencioso.

---

# 33. Evals e testes obrigatórios

## 33.1 Unitários

- envelope;
- redaction;
- dedupe;
- scoring;
- thresholds;
- cooldown;
- quiet hours;
- role personalization;
- expiration;
- recommendation contract;
- outcome calculation;
- demand clustering;
- Knowledge Candidate eligibility.

## 33.2 Contrato

- event → signal;
- signal → finding;
- finding → recommendation;
- recommendation → Work Run;
- Work Run → outcome;
- finding → briefing item;
- briefing → Artifact;
- Artifact → delivery;
- Garimpo → auxiliary request/gap;
- eligible learning → Knowledge Candidate.

## 33.3 Multi-tenant

Testes negativos:

- Resulta não vê AutoFleet;
- AutoFleet não recebe Finding da Resulta;
- usuário A não vê briefing pessoal B;
- quote tenant não aparece no agregado global;
- Admin agregado não expõe PII;
- artifact não vaza;
- recommendation action não cruza company.

## 33.4 Factualidade

Golden cases:

- sem dados suficientes;
- fonte contraditória;
- dado stale;
- recomendação de baixa confiança;
- alerta crítico;
- número calculado;
- inferência de causa;
- falta de Evidence Pack.

Critério:

- zero número inventado;
- fato/inferência separados;
- fonte e período corretos.

## 33.5 Noise tests

- mesmo sinal repetido;
- usuário dispensou;
- problema resolvido;
- prioridade não mudou;
- múltiplos sinais agrupáveis;
- quiet hours;
- max pushes;
- cooldown;
- escalation legítima.

## 33.6 Scheduling

- timezone;
- DST quando aplicável;
- duplicate tick;
- restart;
- retry;
- idempotência de publicação;
- delivery failure;
- perfil pausado;
- evento crítico.

## 33.7 Outcome

- baseline disponível;
- sem baseline;
- resultado parcial;
- negativo;
- inconclusivo;
- confirmação humana;
- estimativa marcada;
- Work Run falhou.

## 33.8 UX

- desktop;
- mobile;
- card Home;
- Briefing Hoje;
- Semanal;
- oportunidade;
- feedback;
- preferências;
- chat;
- access denied;
- loading;
- sem dados;
- erro de source;
- linguagem humana.

## 33.9 Broker Outcome Regression Pack

Validar:

- briefing diário útil;
- briefing não inventa dado;
- alerta crítico aparece;
- recommendation explica evidência;
- CTA cria caminho correto;
- approval funciona;
- Work Run conclui;
- Artifact abre;
- outcome é medido;
- feedback suprime repetição;
- quiet hours funciona;
- Resulta e AutoFleet isoladas;
- login, Atendimento, pareamento, Rotinas, Auxiliares e Portais continuam funcionando.

---

# 34. Experiências iniciais de lançamento

## 34.1 “O que precisa da minha atenção hoje?”

O AutoBrokers entrega briefing atual, não texto genérico.

## 34.2 “Resolva esta aprovação parada”

Abre approval correta ou cria Work Run governado.

## 34.3 “Evite que isso aconteça de novo”

Propõe Rotina/Auxiliar via Factory.

## 34.4 “Por que a qualidade caiu?”

Mostra fatos, possíveis causas, dados faltantes e plano de investigação.

## 34.5 “Você pede este relatório toda semana”

Detecta repetição e oferece automação.

## 34.6 Briefing Executivo Semanal

Entrega web + PDF com evidência, ações e resultados.

## 34.7 Demand Radar Admin

Mostra quais problemas múltiplas corretoras desejam delegar.

---

# 35. Plano de execução em três blocos

## Bloco A — Signal Intelligence Foundation e Garimpo v3

Implementar:

- migrations;
- RLS/FKs/índices;
- event envelope;
- signal/evidence/finding/recommendation schemas;
- briefing profiles/publications;
- demand clusters;
- services;
- redaction;
- dedupe;
- scoring;
- rule engine;
- Garimpo v3;
- adapters históricos;
- Skills base;
- testes unitários/multi-tenant.

Gate A:

- schema verde;
- zero órfão/cross-tenant;
- eventos viram Signals idempotentes;
- evidência é rastreável;
- Garimpo produz sinais e requests;
- nenhuma publicação/envio direto novo;
- dados sensíveis redigidos.

## Bloco B — Briefings, recomendações e produto

Implementar:

- Finding Engine;
- Recommendation Service;
- Outcome Service;
- Briefing Diário;
- Briefing Semanal;
- critical alerts;
- Artifact templates;
- delivery;
- feedback;
- preferences;
- Core tools;
- dashboard tenant;
- Admin mínimo;
- integração Auxiliary Factory;
- integração Work Runs/approvals;
- observabilidade.

Gate B:

- briefing sob demanda funciona;
- briefing agendado cria Work Run;
- Artifact abre;
- recommendation executável cria caminho canônico;
- feedback altera cooldown;
- outcome registra estado correto;
- nenhuma mensagem sem evidence/validity.

## Bloco C — Regras iniciais, cutover e produção

Implementar:

- detectores iniciais;
- migrar Garimpo;
- migrar sugestões;
- migrar relatório semanal;
- migrar regressão;
- remover schedulers diretos do escopo;
- substituir Admin Insights;
- remover writers paralelos;
- canário Amandus;
- canário Resulta;
- canário AutoFleet;
- calibrar thresholds/ruído;
- corrigir achados;
- ativar produção;
- publicar relatório final.

Gate C:

- P0/P1 reais funcionam;
- alert fatigue dentro dos limites;
- zero caminho paralelo soberano;
- Amandus/Resulta/AutoFleet verdes;
- Founder aprova UX e relevância;
- rollback e observabilidade prontos;
- funcionalidade ativa.

---

# 36. Definition of Done

A SPEC-059 só termina quando:

1. existe envelope canônico de evento.
2. Signals possuem evidência, confiança e validade.
3. Findings separam fato e inferência.
4. Recommendations possuem ação real ou declaram gap.
5. Briefing Diário funciona.
6. Briefing Executivo funciona.
7. alertas críticos usam threshold e evidence.
8. quiet hours, dedupe e cooldown funcionam.
9. feedback explícito funciona.
10. outcomes são medidos ou marcados inconclusivos.
11. Garimpo v3 captura demanda com privacidade.
12. clusters globais são anonimizados.
13. Knowledge Candidates seguem SPEC-052.
14. Work Runs executam briefings e ações.
15. Skills/Tool Gateway governam chamadas.
16. Artifact Hub entrega web/PDF/resumos.
17. Auxiliary Factory recebe propostas de automação.
18. schedulers diretos históricos foram migrados no escopo.
19. `broker_insights` não é autoridade nova.
20. Admin administra sinais, regras, demanda e resultados.
21. dashboard mostra prioridades em linguagem humana.
22. nenhum número é inventado.
23. nenhum tenant vaza.
24. custos são atribuídos.
25. Amandus, Resulta e AutoFleet passaram.
26. APPLY/VERIFY/ROLLBACK existem.
27. relatório final existe.
28. funcionalidade está ativa em produção.

---

# 37. Critérios de parada legítima

O executor só deve parar e pedir decisão do Founder quando encontrar:

- risco real de perda de dados;
- conflito entre schema vivo e autoridade canônica impossível de resolver com migration segura;
- necessidade de acesso a dado de produção não autorizado;
- definição comercial de canal/custo que mude cobrança do produto;
- threshold legal/compliance sem responsável definido;
- recomendação de alto risco sem fonte oficial;
- template visual que exija decisão de marca do Founder;
- dependência de SPEC anterior ainda não implementada e impossível de executar no mesmo programa.

Não parar por:

- arquivo grande;
- necessidade de refatorar scheduler legado;
- necessidade de migration;
- necessidade de criar UI;
- necessidade de calibrar regras;
- necessidade de testes;
- necessidade de deploy;
- volume pequeno de dados — nesse caso implementar comportamento honesto de insuficiência.

---

# 38. Fora do escopo desta SPEC

Ficam para SPECs seguintes:

- Firecrawl, pesquisa profunda, concorrentes, notícias e inteligência externa — SPEC-060;
- Control Plane completo e UX consolidada de todo o Portal Admin — SPEC-061;
- billing comercial final, evals globais e launch readiness consolidado — SPEC-062;
- cotações e renovações automatizadas;
- marketing/growth/social publishing completo;
- modelo preditivo de vendas sem base histórica suficiente;
- publicação automática de conhecimento;
- marketplace público de recomendações;
- decisões autônomas de cobertura, jurídico ou compliance.

A arquitetura deve receber sinais externos da SPEC-060 sem criar outro pipeline.

---

# 39. Referências primárias de arquitetura

Durante a implementação, consultar fontes oficiais atuais:

- OpenAI Scheduled Tasks e ChatGPT Work: briefings, monitoramento, recorrência e entrega de trabalho finalizado;
- Claude Cowork Scheduled Tasks: tarefas recorrentes com Skills, plugins e ferramentas conectadas;
- LangGraph Persistence e Interrupts: execução durável, checkpoints e HITL;
- Redis Streams: consumer groups, recovery e processamento idempotente;
- MCP: host authority, consentimento e least privilege;
- documentação oficial dos providers usados para delivery e dados.

As referências inspiram padrões. Não autorizam copiar marca, UI ou criar runtime paralelo.

---

# 40. Próxima SPEC

A próxima autoridade será:

```text
SPEC-060 — AutoBrokers Research Intelligence
```

Ela deverá usar:

- Work Runs;
- Skills;
- Tool Gateway;
- Artifact Hub;
- Auxiliary Factory;
- Intelligence Signals/Findings/Recommendations;
- Briefings;
- Evidence Pack;
- Vault;
- budgets;
- approvals;
- outcome measurement.

Não deverá criar outro motor de pesquisa, outro RAG, outro publisher, outro scheduler ou outro sistema proativo.