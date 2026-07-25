# SPEC-058 — AutoBrokers Auxiliary & Routine Factory

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANÔNICA E AUTORIZADA PARA EXECUÇÃO — aprovada pelo Founder em 24/07/2026  
**Autoridade superior:** `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`, `SPEC-053-autobrokers-work-os-core-harness.md`, `SPEC-054-foundation-hardening-schema-governance.md`, `SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`, `SPEC-056-skill-registry-tool-gateway.md` e `SPEC-057-artifact-hub-report-studio.md`  
**Runtime preservado:** Smith + LangGraph/LangChain + FastAPI + Supabase/Postgres + Redis + Qdrant + MinIO  
**Nome oficial do agente central:** **AutoBrokers**  
**Escopo:** consolidar a fábrica operacional de Auxiliares, Rotinas, instalação por corretora, criação por conversa, criação pelo dashboard, versionamento, dependências, aprovações, custos, execução, entrega, aprendizado de demanda e governança global.  
**Natureza desta SPEC:** autoriza migrations, backend, APIs, UI, migração do legado, publicação de templates globais, integração com Work Runs/Skills/Artifacts, deploy, cutover e ativação em produção.  
**Dependência de execução:** as SPECs 054–057 devem estar implementadas ou ser executadas no mesmo programa, na ordem canônica.

---

# 0. Comando direto ao executor — Fable, Opus, Codex ou equivalente

Você está autorizado a **implementar integralmente esta SPEC em linha reta**.

Esta não é uma SPEC para protótipo, catálogo fake, botão visual sem runtime, automação deixada em shadow por meses ou módulo que só demonstra possibilidades. Ao final da mesma iniciativa:

- o corretor deverá instalar Auxiliares globais reais;
- o corretor deverá criar um Auxiliar pela conversa com o AutoBrokers;
- o corretor deverá criar e editar um Auxiliar pelo dashboard;
- o sistema deverá decidir corretamente entre Work Run único, Rotina, Auxiliar instalado, workflow, executor especializado ou Agent/Subagent;
- Rotinas deverão acionar Work Runs, não outro motor;
- Auxiliares deverão utilizar Skills publicadas e Tool Gateway governado;
- Auxiliares deverão gerar artifacts reais quando o resultado pedir relatório, planilha, PDF, apresentação, briefing, dossiê ou Evidence Pack;
- ações externas deverão respeitar HITL, idempotência, orçamento e Vault;
- o Core deverá sugerir Auxiliares quando fizer sentido, sem fingir que criou ou executou algo;
- a Galeria, Meus Auxiliares, Criar Auxiliar e Execuções deverão funcionar com dados reais;
- o Portal Admin deverá administrar catálogo, releases, instalações, saúde, custos, adoção e demandas;
- os pedidos dos corretores deverão gerar sinais de produto sem vazar dados entre corretoras;
- os caminhos legados concorrentes deverão ser migrados ou reduzidos a adapters de compatibilidade;
- a funcionalidade deverá estar ativa em produção para Amandus, Resulta e AutoFleet.

## 0.1 Doutrina de lançamento

```text
Construir sobre as peças canônicas.
Migrar o que já funciona.
Refazer o que estiver mal modelado.
Eliminar autoridade paralela.
Testar e corrigir na mesma execução.
Ativar no mesmo programa.
```

Não criar:

- `auxiliary_templates_v2`;
- `tenant_auxiliaries_v2`;
- outro scheduler;
- outro Work Run;
- outro Skill Registry;
- outro Tool Gateway;
- outro Artifact Hub;
- um Agent Smith por instalação sem necessidade técnica comprovada;
- um prompt gigante como única definição de Auxiliar;
- um executor dedicado para cada nova ideia;
- uma tabela de runs concorrente com `work_runs`;
- uma rotina que chame diretamente a LLM fora do Work Run após o cutover;
- conectores ou segredos dentro do template;
- publicação automática de template global sem aprovação;
- criação livre de código pelo tenant;
- automação externa sem aprovação quando a policy exigir;
- UI que chame Rotina, Skill, Agent e Auxiliar como se fossem a mesma coisa;
- versão beta permanentemente desligada.

Feature flags são permitidas apenas para rollback e corte controlado durante a mesma iniciativa. A entrega não será considerada concluída enquanto o caminho canônico permanecer permanentemente desativado.

## 0.2 Número de blocos

A execução deverá ocorrer em **três blocos macro**, o menor número compatível com migração, segurança e lançamento:

1. **Bloco A — Modelo canônico, Factory, schema e migração estrutural**;
2. **Bloco B — Conversa, dashboard, catálogo, ciclo de vida e execução integrada**;
3. **Bloco C — Templates iniciais, cutover, UX acceptance e lançamento**.

Com gates verdes, avançar automaticamente.

## 0.3 Saída obrigatória

Ao final deverão existir e estar ativos:

- identidade global de template de Auxiliar;
- releases imutáveis de template;
- instalações por corretora e por usuário quando permitido;
- revisões versionadas de configuração;
- Factory Service único;
- Work Pattern Classifier;
- Dependency/Readiness Resolver;
- criação pelo chat;
- criação pelo dashboard;
- instalação guiada;
- test run limitado e seguro;
- ativação, pausa, retomada, atualização, rollback e desinstalação;
- Rotinas ligadas a Auxiliares/Skills e executadas por Work Runs;
- triggers manuais, agendados, por evento e por condição governada;
- artifacts e deliveries integrados;
- budgets e custos estimados;
- captura de demanda e capability gaps;
- Galeria real;
- Meus Auxiliares real;
- Criar Auxiliar real;
- Execuções reais;
- governança mínima no Portal Admin;
- templates iniciais operacionais;
- migração de `auxiliary_runs` e `routine_runs` para projeções de `work_runs`;
- remoção da mensagem antiga “Auxiliares = Rotinas”;
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
9. ler ADR-001, ADR-002 e ADR-003;
10. ler SPEC-002, SPEC-019 e UX-007 apenas como histórico subordinado;
11. ler o código real de `auxiliary_templates`, `tenant_auxiliaries`, `auxiliary_runs`, `routines`, `routine_runs`, `routine_templates`, `auxiliary_context`, `routine_tools`, `routine_engine`, Blueprint Studio, approvals, Work Runs, Skills, Tool Gateway, Artifacts, Vault, billing e Portal Admin;
12. confirmar schema vivo em modo read-only;
13. confirmar instalações e Rotinas existentes;
14. confirmar dados e comportamento de Amandus, Resulta e AutoFleet.

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
→ SPECs posteriores subordinadas
→ ADRs e documentos históricos quando não conflitarem
→ código atual como estado de implementação
```

Em conflito, não criar outra arquitetura.

---

# 2. Visão de produto

O corretor não compra “agentes”, “prompts”, “MCPs”, “cron jobs” ou “subagents”.

O corretor compra:

- tarefa concluída;
- problema resolvido;
- tempo recuperado;
- receita adicional;
- redução de custo;
- menos retrabalho;
- acompanhamento confiável;
- informação pronta para decidir;
- entrega no canal certo;
- segurança para delegar.

A promessa do módulo é:

> **Escolha, peça ou descreva um trabalho. O AutoBrokers monta o Auxiliar adequado, conecta as capacidades necessárias, executa com segurança e entrega o resultado finalizado.**

## 2.1 Inspiração sem cópia literal

A arquitetura incorpora padrões reconhecidos de agentes de trabalho modernos:

- trabalhos longos e entregáveis finalizados;
- Skills reutilizáveis;
- apps/conectores governados;
- tarefas agendadas;
- criação por conversa;
- instalação e catálogo;
- progressive disclosure;
- subagentes isolados quando necessários;
- histórico, pausa, retomada e edição;
- entrega multicanal;
- criação progressiva de novas capacidades.

Não copiar marca, interface ou ontologia de Claude Cowork, ChatGPT Work ou Hermes. O resultado deve parecer nativo do AutoBrokers e especializado em corretoras de seguros.

## 2.2 Diferencial vertical

O AutoBrokers poderá usar, quando conectado e autorizado:

- dados de atendimento;
- WhatsApp da corretora;
- documentos e apólices;
- InfoCap;
- Quiver e futuros sistemas de gestão;
- portais de seguradoras;
- Atlas de rotas;
- histórico operacional;
- conhecimento global e tenant;
- Work Runs;
- artifacts;
- ferramentas de pesquisa;
- conectores de produtividade.

Essas fontes tornam os Auxiliares mais úteis do que automações genéricas.

---

# 3. Estado atual confirmado e peças preservadas

## 3.1 Peças reais existentes

Preservar e evoluir:

- `auxiliary_templates`;
- `tenant_auxiliaries`;
- `auxiliary_runs` como legado/projeção;
- contrato `auxiliary_contract_v1`;
- Blueprint Studio e publicação global histórica;
- instalação por tenant;
- lifecycle de status;
- executores `resumo-atendimentos` e `follow-up-whatsapp`;
- `routines`, `routine_runs` e `routine_templates`;
- `routine_engine.py`;
- tools `create_routine`, `list_routines` e `manage_routine`;
- claim atômico, timeout e fail-safe de Rotinas;
- entrega WhatsApp;
- `auxiliary_context.py` e consciência do Core;
- Capability Registry;
- Vault;
- Work Runs;
- Skills/Tool Gateway;
- Artifact Hub;
- billing, usage e tracing.

## 3.2 Problemas atuais que esta SPEC corrige

1. UI histórica ainda declara “Auxiliares = Rotinas”.
2. Existem dois modelos de execução e dois históricos.
3. Instalação pode criar Agent por tenant sem necessidade.
4. Auxiliar ainda é metadata em parte do sistema, não composição operacional completa.
5. Rotina ainda executa prompt bruto diretamente pelo serviço legado.
6. `routine_runs` e `auxiliary_runs` competem com `work_runs`.
7. Templates e instalações não possuem releases/revisões imutáveis completas.
8. Criação livre por conversa não monta Auxiliar completo.
9. Dependências, custo e readiness não formam um gate unificado.
10. O Core conhece Auxiliares, mas ainda não possui Factory governado para criar/instalar/executar.
11. Demandas dos corretores não viram um funil estruturado de produto.
12. Admin não possui uma visão única de catálogo, instalações, uso, saúde, custos e oportunidades.

---

# 4. Ontologia oficial

## 4.1 AutoBrokers

Agente central e coordenador do trabalho da corretora.

Pode:

- compreender o pedido;
- executar um Work Run único;
- sugerir Skill;
- sugerir Auxiliar;
- montar proposta de Auxiliar;
- instalar ou alterar após autorização;
- acompanhar trabalho;
- explicar dependências e resultados.

Não é um Auxiliar.

## 4.2 Auxiliar

Produto instalado e configurado para realizar uma família clara de trabalhos para uma corretora ou usuário.

Um Auxiliar pode conter:

```text
Auxiliar
├── uma ou mais Skill Releases
├── workflow/padrão de execução
├── Capability Packs
├── policies
├── conectores requeridos
├── Rotinas opcionais
├── configuração tenant/user
├── orçamento
├── outputs/artifacts
└── Work Runs
```

## 4.3 Skill

Procedimento versionado para produzir um resultado. Governada pela SPEC-056.

## 4.4 Rotina

Gatilho persistente que inicia um trabalho.

Uma Rotina não é um Auxiliar e não contém um cérebro próprio.

## 4.5 Workflow

Sequência de steps executáveis e verificáveis.

## 4.6 Agent/Subagent

Executor cognitivo usado somente quando o trabalho exige raciocínio aberto, delegação ou contexto especializado. Não é criado automaticamente para toda instalação.

## 4.7 Executor especializado

Código determinístico ou integração especializada para uma tarefa bem definida.

## 4.8 Work Run

Execução concreta e autoridade universal de histórico.

## 4.9 Artifact

Entregável durável produzido pelo trabalho.

## 4.10 Template global

Produto reutilizável publicado pela plataforma.

## 4.11 Instalação

Materialização configurada do template em uma corretora ou para um usuário.

## 4.12 Revisão da instalação

Snapshot imutável de uma configuração aprovada.

## 4.13 Pedido de automação

Pedido explícito ou inferido de trabalho repetível, ainda não necessariamente atendido por uma capacidade existente.

## 4.14 Capability Gap

Lacuna que impede a criação ou execução segura: Skill, tool, conector, provider, permissão, dado, workflow ou artifact ausente.

---

# 5. Regra de classificação: nem todo pedido vira Auxiliar

O Factory deverá escolher o menor objeto adequado.

## 5.1 Padrões de trabalho

### `one_shot_work_run`

Usar quando:

- o trabalho ocorrerá uma vez;
- não há benefício em persistir configuração;
- o usuário quer apenas o resultado atual.

### `saved_routine`

Usar quando:

- existe uma Skill já publicada;
- o usuário quer a mesma execução em agenda simples;
- não há necessidade de uma identidade de produto mais ampla.

### `installed_auxiliary`

Usar quando:

- existe uma família persistente de responsabilidades;
- há configuração, conectores, políticas e histórico próprios;
- pode haver múltiplas Rotinas;
- o usuário precisa abrir, acompanhar e administrar um trabalhador.

### `workflow_instance`

Usar quando:

- há várias fases, dependências, approvals ou branches;
- a execução precisa acompanhar um caso até a conclusão.

### `specialized_executor`

Usar quando:

- a tarefa é determinística;
- código especializado é mais seguro, barato e confiável do que Agent genérico.

### `agent_backed_auxiliary`

Usar somente quando:

- o domínio exige raciocínio aberto recorrente;
- a Skill e o workflow não são suficientes;
- existe benefício real em um Agent/Subagent especializado;
- custo, contexto e governança foram justificados.

## 5.2 Árvore de decisão

```text
Pedido do usuário
→ já pode ser executado uma vez?
   → sim: Work Run único
→ é apenas recorrência de uma Skill existente?
   → sim: Rotina ligada à Skill
→ exige identidade, configuração, histórico e múltiplos trabalhos?
   → sim: Auxiliar instalado
→ exige várias fases/caso persistente?
   → sim: workflow
→ existe executor determinístico melhor?
   → sim: executor especializado
→ exige raciocínio especializado persistente?
   → sim: Agent-backed
→ falta capacidade?
   → registrar capability gap e explicar ao usuário
```

## 5.3 Proibição de inflação de Agents

O runtime padrão de um novo Auxiliar será:

```text
Skill Release + Capability Pack + Work Run
```

Um Agent dedicado por corretora não é o padrão.

O caminho histórico `smith_agent_blueprint → criar Agent ao instalar` deverá:

- permanecer apenas para templates explicitamente `agent_backed`;
- exigir justificativa no manifest;
- não ser usado por padrão;
- ser migrado para referências versionadas;
- impedir duplicação de Agents em reinstalação/update.

---

# 6. Arquitetura canônica

```text
Chat AutoBrokers / Dashboard / Admin / API
                     │
                     ▼
           Auxiliary Factory Service
                     │
       ┌─────────────┼──────────────┐
       ▼             ▼              ▼
Work Pattern     Template/Skill   Demand Signal
Classifier       Resolver         Recorder
       │             │              │
       └─────────────┴──────────────┘
                     │
                     ▼
       Dependency & Readiness Resolver
                     │
                     ▼
      Proposal + Cost + Risk + Approval
                     │
                     ▼
         Installation / Revision
                     │
       ┌─────────────┼──────────────┐
       ▼             ▼              ▼
   Manual Run     Routine        Event/Condition
       │             │              │
       └─────────────┴──────────────┘
                     │
                     ▼
                 Work Run
                     │
       Skill Registry + Tool Gateway
                     │
                     ▼
             Artifact / Delivery
                     │
                     ▼
 Dashboard / WhatsApp / E-mail / Portal Admin
```

## 6.1 Autoridades

| Responsabilidade | Autoridade |
|---|---|
| identidade global do Auxiliar | `auxiliary_templates` |
| versão publicada | `auxiliary_template_releases` |
| instalação tenant/user | `tenant_auxiliaries` |
| configuração versionada | `tenant_auxiliary_revisions` |
| Skills | Skill Registry |
| tools | Tool Gateway |
| agenda/gatilho | `routines` evoluída |
| execução | `work_runs` |
| artifacts | Artifact Hub |
| approvals | `approval_requests` |
| side effects | `work_effects` |
| segredos | Vault |
| custo | usage/billing + Work Run |
| demanda | `auxiliary_requests`/`capability_gaps` |
| auditoria | Work Events + Auxiliary Events |

## 6.2 Serviços

Criar/consolidar:

```text
backend/app/services/auxiliary_factory/
```

Componentes mínimos:

- `factory_service.py`;
- `work_pattern_classifier.py`;
- `template_resolver.py`;
- `proposal_builder.py`;
- `readiness_resolver.py`;
- `installation_service.py`;
- `revision_service.py`;
- `routine_binding_service.py`;
- `lifecycle_service.py`;
- `demand_signal_service.py`;
- `migration_adapter.py`;
- `policy.py`;
- `schemas.py`.

O serviço não cria runtime paralelo. Ele compõe os órgãos canônicos.

---

# 7. Manifesto canônico de Auxiliar

Cada `auxiliary_template_release` terá manifest validado.

## 7.1 Campos obrigatórios

```text
schema_version
auxiliary_key
name
short_description
business_outcome
problem_solved
categories
audience
visibility
when_to_use
when_not_to_use
non_goals
work_pattern
runtime_kind
skill_release_refs
workflow_ref nullable
capability_pack_refs
required_connectors
optional_connectors
required_data
required_knowledge
required_memory
input_contract
configuration_schema
output_contract
artifact_contract
routine_defaults
trigger_policy
side_effect_policy
approval_policy
risk_level
budget_policy
model_policy
rate_limits
recipient_policy
failure_policy
fallback_policy
observability_policy
success_metrics
eval_pack_ref
compatibility
upgrade_policy
support_policy
```

## 7.2 `runtime_kind`

Valores:

```text
skill_workflow
specific_executor
portal_workflow
delegated_subagent
agent_backed
hybrid
```

## 7.3 Customização permitida

O manifest deverá declarar o que o tenant pode alterar:

- nome visível;
- objetivo operacional restrito;
- filtros;
- período;
- destinatários autorizados;
- canais;
- agenda;
- limites;
- tom de comunicação;
- nível de detalhe;
- branding;
- seções de artifact;
- aprovação mais restritiva;
- fontes tenant permitidas.

Não permitir:

- remover guardrail obrigatório;
- elevar escopo sem entitlement;
- inserir segredo;
- adicionar código;
- apontar para URL arbitrária;
- trocar Skill por release não homologada;
- desligar approval obrigatório;
- acessar outro tenant;
- exportar conhecimento global.

## 7.4 Compatibilidade

Cada release deve declarar:

- versão mínima do runtime;
- versões mínimas de Skills;
- schemas de configuração suportados;
- migrations de configuração;
- breaking changes;
- estratégia de rollback.

Release publicada é imutável.

---

# 8. Modelo de dados canônico

Todas as migrations seguem APPLY/VERIFY/ROLLBACK da SPEC-054.

## 8.1 `auxiliary_templates`

Preservar como identidade global.

Campos mínimos:

```text
id uuid PK
auxiliary_key text UNIQUE NOT NULL
slug text UNIQUE NOT NULL
name text NOT NULL
short_description text NOT NULL
description text NOT NULL
category text NOT NULL
owner text NOT NULL
visibility text NOT NULL
status text NOT NULL
current_release_id uuid NULL
is_active boolean NOT NULL
created_at timestamptz
updated_at timestamptz
deprecated_at timestamptz NULL
```

## 8.2 `auxiliary_template_releases`

```text
id uuid PK
auxiliary_template_id uuid NOT NULL FK auxiliary_templates
version text NOT NULL
status text NOT NULL
manifest jsonb NOT NULL
configuration_schema jsonb NOT NULL
input_schema jsonb NOT NULL
output_schema jsonb NOT NULL
content_hash text NOT NULL
runtime_min_version text NULL
created_by_user_id uuid NULL
approved_by_user_id uuid NULL
created_at timestamptz
approved_at timestamptz NULL
published_at timestamptz NULL
deprecated_at timestamptz NULL
superseded_by_release_id uuid NULL
```

Constraints:

- unique `(auxiliary_template_id, version)`;
- unique `(auxiliary_template_id, content_hash)`;
- release publicada imutável;
- uma release default ativa por template;
- manifest validado;
- nenhuma secret key.

Estados:

```text
draft
validation_failed
review
approved
published
deprecated
disabled
```

## 8.3 `auxiliary_release_skills`

```text
id
auxiliary_template_release_id
skill_release_id
role
phase
is_required
sequence
configuration jsonb
```

## 8.4 `auxiliary_release_capability_packs`

```text
id
auxiliary_template_release_id
capability_pack_release_id
phase
is_required
```

## 8.5 `tenant_auxiliaries`

Preservar como instalação canônica.

```text
id uuid PK
company_id uuid NOT NULL FK companies
owner_user_id uuid NULL
template_id uuid NULL
template_release_id uuid NULL
auxiliary_key text NOT NULL
slug text NOT NULL
display_name text NOT NULL
scope text NOT NULL
status text NOT NULL
current_revision_id uuid NULL
installed_by_user_id uuid NULL
installed_from text NOT NULL
health_status text NOT NULL
last_work_run_id uuid NULL
last_run_at timestamptz NULL
next_run_at timestamptz NULL
activated_at timestamptz NULL
paused_at timestamptz NULL
disabled_at timestamptz NULL
created_at timestamptz
updated_at timestamptz
```

Scopes:

```text
personal
company
platform_managed
```

Unique:

- `(company_id, auxiliary_key, owner_user_id)` para pessoal;
- `(company_id, auxiliary_key)` para company, conforme índice parcial;
- evitar duplicação em reinstalação.

## 8.6 `tenant_auxiliary_revisions`

```text
id uuid PK
company_id uuid NOT NULL
tenant_auxiliary_id uuid NOT NULL
revision_number integer NOT NULL
status text NOT NULL
template_release_id uuid NULL
configuration jsonb NOT NULL
resolved_dependencies jsonb NOT NULL
policy_snapshot jsonb NOT NULL
budget_snapshot jsonb NOT NULL
connection_bindings jsonb NOT NULL
content_hash text NOT NULL
created_by_user_id uuid NULL
approved_by_user_id uuid NULL
created_at timestamptz
approved_at timestamptz NULL
activated_at timestamptz NULL
superseded_at timestamptz NULL
```

A revisão ativa é imutável. Alterar configuração cria nova revisão.

## 8.7 `routines` evoluída

Adicionar/reusar:

```text
tenant_auxiliary_id uuid NULL
skill_release_id uuid NULL
work_pattern text NOT NULL DEFAULT 'scheduled_skill'
trigger_kind text NOT NULL
trigger_spec jsonb NOT NULL
input_binding jsonb NOT NULL DEFAULT '{}'
delivery_policy jsonb NOT NULL DEFAULT '{}'
budget_policy jsonb NOT NULL DEFAULT '{}'
approval_policy jsonb NOT NULL DEFAULT '{}'
timezone text NOT NULL
is_active boolean NOT NULL
next_run_at timestamptz NULL
last_work_run_id uuid NULL
```

O campo histórico `instructions` pode permanecer para compatibilidade, mas não será autoridade quando houver Skill/manifest.

## 8.8 `auxiliary_requests`

Registra intenção e funil de criação.

```text
id uuid PK
company_id uuid NOT NULL
user_id uuid NULL
source text NOT NULL
request_text_redacted text NOT NULL
request_fingerprint text NOT NULL
requested_outcome text NOT NULL
classified_work_pattern text NULL
category text NULL
frequency text NULL
matched_template_id uuid NULL
matched_skill_release_id uuid NULL
status text NOT NULL
resolution text NULL
created_tenant_auxiliary_id uuid NULL
created_routine_id uuid NULL
created_work_run_id uuid NULL
capability_gap_count integer NOT NULL DEFAULT 0
accepted_at timestamptz NULL
rejected_at timestamptz NULL
created_at timestamptz
```

Não guardar PII desnecessária. Para aprendizado global usar versão anonimizada.

## 8.9 `capability_gaps`

```text
id
company_id nullable
auxiliary_request_id nullable
gap_type
capability_key nullable
provider nullable
description_redacted
frequency_count
first_seen_at
last_seen_at
status
resolution_ref nullable
```

Tipos:

- `missing_skill`;
- `missing_tool`;
- `missing_connector`;
- `missing_data`;
- `missing_provider`;
- `missing_artifact`;
- `policy_blocked`;
- `unsupported_trigger`;
- `unsupported_workflow`.

## 8.10 `auxiliary_events`

Timeline append-only de lifecycle:

- proposal.created;
- dependency.detected;
- dependency.resolved;
- test.started;
- test.completed;
- installed;
- revision.created;
- revision.approved;
- activated;
- paused;
- resumed;
- update.available;
- updated;
- rolled_back;
- degraded;
- recovered;
- disabled;
- uninstalled;
- request.matched;
- gap.recorded.

## 8.11 Runs legados

Adicionar `work_run_id` a `auxiliary_runs` e `routine_runs`.

Após o cutover:

- `work_runs` é autoridade;
- tabelas legadas são projeção/compatibilidade;
- novas features não consultam runs legados como fonte soberana;
- nenhum run deve ser executado duas vezes por causa das projeções.

---

# 9. Factory Service

## 9.1 Entrada

O Factory recebe:

```text
company_id
user_id
source
request_text
resolved_intent
available_context
requested_scope
requested_trigger
requested_delivery
constraints
```

## 9.2 Etapas

```text
1. Redigir e fingerprint do pedido
2. Extrair outcome
3. Classificar padrão de trabalho
4. Buscar template/Skill existente
5. Verificar se um Work Run único resolve
6. Determinar escopo pessoal/company
7. Resolver dependências
8. Resolver risco e approvals
9. Estimar custo
10. Montar proposta
11. Pedir somente dados faltantes
12. Testar em modo limitado
13. Criar instalação/revisão/Rotina
14. Ativar
15. Registrar eventos e demanda
```

## 9.3 Resolver antes de criar

O Factory deve preferir, em ordem:

1. executar Skill existente uma vez;
2. criar Rotina para Skill existente;
3. instalar template global existente;
4. compor Auxiliar tenant com releases homologadas;
5. registrar capability gap.

Não deve criar novo template global automaticamente.

## 9.4 Perguntas mínimas

Perguntar somente o que for realmente necessário:

- o resultado esperado;
- quando ou com que gatilho;
- escopo pessoal ou da corretora;
- dados/fontes;
- canal/destinatário;
- aprovação;
- limite de custo;
- filtros essenciais.

Não perguntar:

- qual modelo de IA;
- qual Agent;
- qual MCP;
- qual bucket;
- qual renderer;
- qual tabela;
- qual runtime.

## 9.5 Proposal Contract

Antes da ativação mostrar em linguagem humana:

```text
Nome
O que vai resolver
O que fará em cada execução
Quando trabalhará
Quais dados usará
Quais conexões precisa
O que poderá fazer sozinho
O que exigirá aprovação
O que entregará
Para quem entregará
Custo estimado por execução e mês
Limites
Primeiro teste
```

A proposta deve possuir payload estruturado e hash. Aprovação refere-se ao hash.

---

# 10. Criação pelo chat principal

## 10.1 Exemplos

> “Crie um auxiliar que toda sexta me envie um relatório dos atendimentos parados.”

> “Quero alguém que analise as planilhas que eu subir e me entregue os problemas.”

> “Todo dia às 17h veja o que ficou pendente e me avise no WhatsApp.”

> “Crie um auxiliar só para mim que prepare minhas reuniões de segunda.”

## 10.2 Comportamento do Core

O AutoBrokers deve:

1. reconhecer intenção de delegação/automação;
2. verificar se é one-shot, Rotina ou Auxiliar;
3. consultar templates/Skills disponíveis;
4. explicar a melhor opção;
5. montar proposta;
6. exibir dependências;
7. pedir confirmação;
8. criar Work Run de instalação/configuração;
9. executar test run quando necessário;
10. ativar;
11. devolver card do Auxiliar;
12. informar onde administrar no dashboard.

## 10.3 Tools canônicas

As tools legadas deverão convergir para operações do Factory:

```text
auxiliary.propose
auxiliary.install
auxiliary.create_custom
auxiliary.get
auxiliary.list
auxiliary.update
auxiliary.pause
auxiliary.resume
auxiliary.uninstall
auxiliary.test
auxiliary.run_now
auxiliary.list_runs
routine.create
routine.update
routine.pause
routine.resume
routine.delete
```

Todas passam pelo Tool Gateway.

## 10.4 Confirmações

O Core não precisa pedir confirmação repetida para leitura interna de baixo risco.

Exigir confirmação explícita para:

- instalar Auxiliar company-wide;
- criar rotina recorrente com custo relevante;
- conectar fonte nova;
- enviar externamente;
- habilitar ação automática;
- permitir destinatário externo;
- alterar approval policy;
- atualizar para release com mudança de comportamento;
- desinstalar e perder agendamentos.

## 10.5 Pedido não atendível

Quando faltar capacidade:

> “Ainda não consigo automatizar esta parte com segurança porque falta uma conexão com X. Registrei a necessidade. Hoje consigo entregar Y manualmente e deixar a estrutura pronta para quando a conexão estiver disponível.”

Não fingir criação.

---

# 11. Criação e gestão pelo dashboard

## 11.1 Navegação oficial

```text
Auxiliares
├── Meus Auxiliares
├── Galeria
├── Criar Auxiliar
└── Execuções
```

“Rotinas” não será o nome do módulo principal.

## 11.2 Meus Auxiliares

Cada card mostra:

- nome;
- problema resolvido;
- status humano;
- escopo pessoal/corretora;
- última execução;
- próxima execução;
- saúde;
- conexão pendente;
- custo no período;
- resultado recente;
- ação principal.

Filtros:

- ativos;
- pausados;
- precisam de atenção;
- pessoais;
- da corretora;
- categoria;
- conexão;
- custo;
- última atividade.

## 11.3 Galeria

Organizar por resultados, não tecnologia:

- Gestão e decisões;
- Atendimento e relacionamento;
- Cobrança e pendências;
- Documentos;
- Produtividade;
- Relatórios e análises;
- Pesquisa;
- Comercial;
- Marketing e presença digital, quando futuras Skills estiverem disponíveis.

Cada card deve responder:

- que problema resolve;
- resultado entregue;
- dados necessários;
- conexões necessárias;
- tempo de configuração;
- frequência típica;
- aprovação;
- custo estimado;
- formatos entregues;
- status de disponibilidade.

Não mostrar card instalável para algo sem runtime real. Pode mostrar “Em breve” somente quando houver decisão de produto, sem CTA enganoso.

## 11.4 Criar Auxiliar

Wizard em no máximo cinco etapas:

1. **O que você quer resolver?**
2. **Que dados e conexões serão usados?**
3. **Quando deve trabalhar?**
4. **O que pode fazer e o que precisa de aprovação?**
5. **Revisar, testar e ativar.**

O usuário pode escrever livremente; o sistema transforma em estrutura.

## 11.5 Detalhe do Auxiliar

Abas/seções:

- Visão geral;
- O que faz;
- Quando trabalha;
- Conexões;
- Permissões;
- Entregas;
- Execuções;
- Custos;
- Versões;
- Configurações.

Ações:

- Executar agora;
- Testar;
- Editar;
- Pausar;
- Retomar;
- Atualizar;
- Voltar versão;
- Duplicar como novo Auxiliar pessoal/company;
- Desinstalar.

## 11.6 Execuções

Usar `work_runs`.

Mostrar:

- Auxiliar;
- status;
- início/fim;
- duração;
- step atual;
- custo;
- resultado;
- artifacts;
- approvals;
- destinatários;
- erro humano;
- tentar novamente quando seguro;
- timeline.

Não expor logs técnicos por padrão.

---

# 12. Instalação, readiness e test run

## 12.1 Readiness Resolver

Verificar antes de ativar:

- Skill Releases publicadas;
- Capability Packs disponíveis;
- entitlements;
- conexões ativas;
- scopes;
- Vault refs;
- dados mínimos;
- artifact renderer;
- canal de entrega;
- destinatários;
- budget;
- approval policy;
- provider health;
- permissões do usuário;
- compatibilidade de versão.

Estados:

```text
ready
needs_configuration
needs_connection
needs_permission
needs_approval
budget_blocked
provider_unavailable
unsupported
```

## 12.2 Test run

O teste faz parte da instalação de lançamento, não é fase beta.

Preferências:

1. dados reais limitados e selecionados;
2. read-only;
3. rascunho sem envio;
4. um único destinatário controlado;
5. sem side effect externo quando não aprovado.

Mostrar:

- entrada usada;
- fontes;
- resultado;
- artifact;
- ação que seria executada;
- custo;
- risco;
- tempo;
- limitações.

## 12.3 Gate de ativação

Ativar somente se:

- schema validado;
- dependências resolvidas;
- test run verde quando obrigatório;
- approvals obtidas;
- budget definido;
- zero segredo na config;
- versão aprovada;
- tenant isolation verde.

---

# 13. Rotinas e triggers

## 13.1 Princípio

Rotina apenas decide **quando iniciar** um Work Run.

Depois do cutover:

```text
Rotina due
→ cria Work Run idempotente
→ Smith Worker executa
→ Skill/Tool Gateway
→ Artifact/Delivery
→ atualiza projeção da Rotina
```

O caminho legado que chama `LangChainService.process_message` diretamente deve ser migrado.

## 13.2 Tipos de trigger

### Manual

- botão “Executar agora”;
- comando no chat;
- API autorizada.

### Agendado

- uma vez;
- diário;
- dias da semana;
- semanal;
- mensal;
- intervalo;
- RRULE validada.

Timezone e DST obrigatórios.

### Evento

- novo documento;
- atendimento encerrado;
- mensagem recebida;
- Work Run concluído;
- conexão alterada;
- artifact publicado;
- evento operacional canônico.

Somente eventos publicados pelo ecossistema. Não consumir qualquer payload externo sem normalização.

### Condição

Exemplos:

- existem atendimentos parados acima do limite;
- valor de pendências supera limiar;
- conexão ficou degradada;
- número de falhas atingiu limite.

Condição é avaliada por uma rotina de leitura ou evento, não por loop descontrolado.

## 13.3 Anti-loop

Proibir:

- Rotina criar Rotina dentro de sua execução;
- Auxiliar se duplicar;
- evento de entrega disparar a mesma entrega novamente;
- cadeia infinita de Auxiliares;
- subagente criar Auxiliar sem approval.

Campos obrigatórios:

- causation_id;
- correlation_id;
- recursion_depth;
- max_depth;
- dedupe_key;
- cooldown.

## 13.4 Falhas

- falha transitória: retry conforme Work Run;
- falha de conexão: bloquear e orientar reconexão;
- falha repetida: marcar `degraded` e pausar apenas o gatilho afetado;
- falha de policy: bloquear sem retry;
- side effect unknown: reconciliar antes de repetir;
- budget excedido: pausar e pedir decisão.

---

# 14. Skills, tools, dados e memória

## 14.1 Skills

Auxiliar referencia releases, não textos soltos.

Uma instalação pode compor várias Skills em ordem definida.

## 14.2 Capability Packs

Somente packs necessários à fase atual serão carregados.

## 14.3 Conectores

Auxiliar usa conexões tenant/user existentes no Vault.

Nunca duplica credenciais.

## 14.4 Conhecimento

- fatos globais: SPEC-052;
- fatos da corretora: tenant knowledge;
- preferências do usuário: user memory;
- procedimento: Skill;
- parâmetros operacionais: revisão do Auxiliar;
- dados vivos: sistemas conectados.

Não salvar conhecimento permanente em `routine.instructions`.

## 14.5 Memória

O Auxiliar não ganha memória ilimitada por existir.

Manifest define:

- nenhum;
- sessão;
- usuário;
- corretora;
- caso;
- operacional.

Memória segue retenção, escopo e curadoria da SPEC-052.

---

# 15. Permissões, HITL e segurança

## 15.1 Roles

### Usuário comum

Pode:

- executar Auxiliar autorizado;
- criar Auxiliar pessoal de baixo risco;
- criar rotina pessoal read-only dentro de limite;
- ver suas execuções.

Não pode:

- instalar company-wide;
- ampliar escopo;
- liberar envio automático externo;
- alterar budget da empresa;
- remover approval obrigatório.

### Gestor/Owner

Pode:

- instalar company-wide;
- definir destinatários;
- aprovar ações externas;
- definir budgets;
- atualizar/pausar/desinstalar;
- ver resultados da empresa conforme papel.

### Platform Admin

Pode:

- criar template global;
- aprovar release;
- rollout;
- rollback;
- suspender template;
- investigar falhas redigidas;
- ver métricas agregadas.

Não pode acessar dados sensíveis de tenant sem trilha e necessidade operacional.

## 15.2 Approval policy

Níveis:

```text
none
first_run_only
every_external_action
batch_approval
recipient_change
threshold_based
always
```

Approval é vinculada a:

- revisão;
- Work Run;
- step;
- side effect;
- action fingerprint;
- destinatário;
- valor/volume;
- validade.

## 15.3 Segurança de configuração

- schema whitelist;
- sanitização profunda;
- nenhum segredo;
- nenhuma URL arbitrária;
- nenhuma expressão executável;
- nenhuma query SQL livre;
- nenhum HTML/JS livre;
- nenhuma instrução capaz de elevar permission;
- logs redigidos;
- tenant isolation em toda query.

## 15.4 Kill switches

- global por template/release;
- por tenant;
- por instalação;
- por Rotina;
- por tool/provider;
- por delivery;
- por categoria de side effect.

---

# 16. Custos, orçamento e limites

## 16.1 Estimativa

Antes de ativar mostrar:

- custo estimado por execução;
- frequência;
- custo mensal provável;
- custo de providers externos;
- faixa mínima/máxima;
- impacto de formatos/artifacts.

## 16.2 Budget

Configurações:

```text
max_cost_per_run_brl
max_cost_per_day_brl
max_cost_per_month_brl
max_runs_per_day
max_external_actions_per_day
max_recipients_per_run
```

Ao atingir limite:

- não cobrar/agir silenciosamente além do limite;
- pausar o gatilho;
- informar;
- permitir ajuste por papel autorizado.

## 16.3 Atribuição

Todo custo deve se ligar a:

- tenant;
- Auxiliar;
- revisão;
- Rotina;
- Work Run;
- Skill;
- Tool;
- Artifact;
- delivery.

## 16.4 Métricas de valor

Quando mensurável:

- horas economizadas estimadas;
- tarefas concluídas;
- mensagens preparadas/enviadas;
- pendências detectadas;
- artifacts visualizados;
- erros evitados;
- receita/oportunidade influenciada;
- SLA melhorado;
- custo por resultado.

Não inventar ROI.

---

# 17. Artifacts e entregas

Auxiliares devem solicitar Artifact Hub quando o resultado correto for:

- relatório;
- planilha;
- CSV;
- PDF;
- apresentação;
- documento;
- briefing;
- dossiê;
- gráfico;
- Evidence Pack.

## 17.1 Output Contract

Cada template declara:

- resultado principal;
- formatos;
- resumo no chat;
- artifact obrigatório/opcional;
- delivery padrão;
- retention;
- classificação;
- aprovação.

## 17.2 Delivery

Usar `artifact_deliveries` e `work_effects`.

Canais iniciais:

- dashboard;
- WhatsApp;
- e-mail;
- link autorizado.

Mensagem curta deve explicar:

- o que foi concluído;
- período/escopo;
- principais achados;
- link do artifact;
- ação necessária.

---

# 18. Catálogo global e publicação

## 18.1 Processo

```text
Ideia/demanda
→ análise de problema
→ outcome
→ template draft
→ composição de Skills/Tools
→ evals
→ security review
→ test tenant
→ Founder approval
→ release published
→ rollout
→ métricas
→ update/rollback
```

## 18.2 Requisitos de publicação

Nenhum template global será publicado sem:

- problema e público claros;
- runtime real;
- Skills publicadas;
- tools homologadas;
- dependências conhecidas;
- test run verde;
- tenant isolation;
- approval policy;
- budget policy;
- artifact/output funcional;
- evals;
- documentação humana;
- owner;
- support/failure policy;
- aprovação do Founder.

## 18.3 Atualizações

Classificar release:

- patch compatível;
- melhoria opcional;
- mudança de comportamento;
- breaking change;
- correção de segurança.

Auto-update somente quando:

- compatível;
- sem aumento de permission;
- sem novo side effect;
- sem aumento relevante de custo;
- permitido pela policy tenant.

Caso contrário, solicitar aprovação.

## 18.4 Rollback

- reativar release anterior;
- preservar revisão tenant;
- revalidar dependências;
- pausar Rotinas incompatíveis;
- não apagar histórico;
- registrar evento.

---

# 19. Demanda, aprendizado e expansão do arsenal

## 19.1 Princípio

O sistema deve aprender **o que os corretores querem delegar**, sem publicar automaticamente novas capacidades.

## 19.2 Sinais capturados

- pedido explícito de Auxiliar;
- pedido de repetição;
- tarefa executada várias vezes;
- pedido não atendido;
- conector faltante;
- Skill faltante;
- formato de artifact pedido;
- frequência;
- categoria;
- cargo do usuário;
- aceitação da proposta;
- abandono;
- instalação;
- uso recorrente;
- resultado;
- desinstalação e motivo.

## 19.3 Privacidade

Para agregação global:

- anonimizar tenant e usuário;
- remover PII;
- não carregar conteúdo bruto de atendimento;
- guardar somente problema/outcome/categoria/frequência e sinais autorizados;
- seguir SPEC-052.

## 19.4 Promoção para template global

Critérios sugeridos:

- pedidos de múltiplas corretoras;
- alta frequência;
- impacto econômico;
- capacidade disponível;
- risco controlável;
- custo sustentável;
- resultado mensurável;
- baixa customização específica.

A promoção exige Curadoria/Admin/Founder.

## 19.5 Proatividade

Nesta SPEC, o Core pode sugerir automação quando:

- o usuário explicitamente pedir recorrência;
- o mesmo pedido ocorrer repetidamente;
- um template instalado resolver diretamente a necessidade atual.

A detecção avançada de oportunidades e Garimpo v3 será aprofundada na SPEC-059.

---

# 20. Auxiliares iniciais de lançamento

Não publicar dezenas superficiais. Publicar um conjunto pequeno e real.

## 20.1 Resumo de Atendimentos

- migra executor existente;
- leitura tenant-scoped;
- resumo, tópicos, decisões, pendências e próximos passos;
- Work Run universal;
- artifact opcional;
- sem ação externa.

## 20.2 Follow-up WhatsApp Assistido

- identifica contexto autorizado;
- produz rascunho;
- approval antes de envio;
- destinatário validado;
- side effect idempotente;
- registra resultado.

## 20.3 Analista Executivo Semanal

- usa Report Studio;
- agrega dados disponíveis;
- produz web + PDF;
- resumo no WhatsApp/e-mail;
- rotina semanal opcional;
- cálculos determinísticos.

## 20.4 Organizador de Pendências

- lê atendimentos, atividades e Work Runs disponíveis;
- lista o que está parado;
- prioriza;
- gera plano de ação;
- pode ser manual ou diário;
- sem executar ação externa automaticamente.

## 20.5 Analisador de Documentos

- recebe documentos autorizados;
- utiliza Skill de análise;
- extrai fatos;
- aponta pendências;
- gera documento/planilha/Evidence Pack;
- não confirma cobertura específica sem Evidence Pack oficial.

## 20.6 Analisador de Planilhas

- importa dataset autorizado;
- valida schema;
- calcula métricas;
- encontra inconsistências;
- produz XLSX/CSV/relatório;
- protege contra formula injection.

## 20.7 Preparador de Reunião

- reúne agenda, artifacts, pendências e documentos autorizados;
- produz briefing e pauta;
- não envia convite sem approval;
- entrega dashboard/e-mail.

## 20.8 Cobrança Assistida

- preservar executor/fluxo existente quando operacional;
- consultar dados autorizados;
- gerar lista e mensagens;
- approval e recipient policy;
- portal/WhatsApp via Work Run;
- Evidence/ledger de efeitos.

## 20.9 Regras

- somente templates com dependências reais e evals verdes serão instaláveis;
- recursos da SPEC-059/060 podem ampliar esses Auxiliares depois;
- cotações e renovações automatizadas ficam fora desta SPEC;
- nenhum card falso.

---

# 21. Portal Admin mínimo desta SPEC

A SPEC-061 consolidará o Control Plane completo, mas a execução da SPEC-058 já deve fornecer administração funcional.

## 21.1 Catálogo

Mostrar:

- templates;
- releases;
- status;
- owner;
- categoria;
- runtime kind;
- Skills;
- tools;
- conectores;
- risco;
- custo médio;
- adoção;
- sucesso;
- última falha;
- tenants instalados.

Ações:

- criar draft;
- validar;
- aprovar;
- publicar;
- deprecar;
- desativar;
- rollout;
- rollback;
- executar evals.

## 21.2 Instalações

- tenant;
- usuário owner;
- release;
- revisão ativa;
- status;
- readiness;
- conexão;
- rotina;
- uso;
- custo;
- artifacts;
- saúde;
- erros;
- update disponível.

## 21.3 Demandas

- pedidos mais frequentes;
- capability gaps;
- templates mais solicitados;
- pedidos abandonados;
- instalações por categoria;
- uso e retenção;
- motivos de pausa/desinstalação;
- candidatos a novo Auxiliar.

## 21.4 Linguagem humana

Exibir:

> “Este Auxiliar está pausado porque a conexão do WhatsApp expirou.”

Não exibir por padrão:

> `tenant_connection entitlement resolution failure`.

Detalhes técnicos ficam em área avançada.

---

# 22. APIs e contratos

## 22.1 Tenant

```text
GET    /api/auxiliaries/catalog
GET    /api/auxiliaries/installed
POST   /api/auxiliaries/proposals
POST   /api/auxiliaries/install
POST   /api/auxiliaries/custom
GET    /api/auxiliaries/{id}
PATCH  /api/auxiliaries/{id}
POST   /api/auxiliaries/{id}/test
POST   /api/auxiliaries/{id}/activate
POST   /api/auxiliaries/{id}/pause
POST   /api/auxiliaries/{id}/resume
POST   /api/auxiliaries/{id}/run
POST   /api/auxiliaries/{id}/rollback
DELETE /api/auxiliaries/{id}
GET    /api/auxiliaries/{id}/runs
GET    /api/auxiliaries/{id}/artifacts
```

## 22.2 Rotinas

```text
GET    /api/routines
POST   /api/routines
PATCH  /api/routines/{id}
POST   /api/routines/{id}/pause
POST   /api/routines/{id}/resume
POST   /api/routines/{id}/run-now
DELETE /api/routines/{id}
```

## 22.3 Admin

```text
GET    /api/admin/auxiliary-templates
POST   /api/admin/auxiliary-templates
POST   /api/admin/auxiliary-templates/{id}/releases
POST   /api/admin/auxiliary-releases/{id}/validate
POST   /api/admin/auxiliary-releases/{id}/approve
POST   /api/admin/auxiliary-releases/{id}/publish
POST   /api/admin/auxiliary-releases/{id}/rollout
POST   /api/admin/auxiliary-releases/{id}/rollback
GET    /api/admin/auxiliary-installations
GET    /api/admin/auxiliary-demand
GET    /api/admin/capability-gaps
```

## 22.4 Regras

- autenticação server-side;
- company scope obrigatório;
- idempotency key em POST sensível;
- schema validation;
- ETag/version para edição concorrente;
- audit event;
- nenhuma service-role call genérica sem filtro explícito;
- resposta humana + código estável de erro.

---

# 23. Migração e cutover

## 23.1 Inventário

Antes de alterar:

- templates globais;
- instalações;
- Agents criados por template;
- executores específicos;
- Rotinas;
- routine templates;
- runs;
- approvals;
- conexões;
- páginas e endpoints;
- mocks;
- contratos inferidos;
- dados órfãos;
- duplicidades por slug/company.

## 23.2 Migração

1. criar releases para templates atuais;
2. normalizar manifests;
3. criar revisão inicial para cada instalação;
4. classificar runtime real;
5. ligar `auxiliary_runs`/`routine_runs` a `work_runs` quando possível;
6. migrar Rotinas para trigger specs;
7. preservar IDs e histórico;
8. remover criação automática de Agent onde desnecessária;
9. manter adapter temporário;
10. validar Resulta/AutoFleet.

## 23.3 UI

Remover/corrigir:

- comentário e microcopy “Auxiliares = Rotinas”;
- página que apresenta apenas Rotinas prontas;
- mocks;
- caminhos órfãos;
- nomenclatura técnica.

## 23.4 Cutover

Ao final:

- Factory Service é caminho único de criação/instalação;
- Work Runs são autoridade de execução;
- Rotinas somente disparam Work Runs;
- Tool Gateway governa operações;
- templates usam releases;
- instalações usam revisões;
- Core usa tools do Factory;
- dashboard e chat mostram o mesmo estado;
- writer legado direto é desativado;
- adapters ficam somente para leitura/compatibilidade temporária documentada.

---

# 24. Evals e testes obrigatórios

## 24.1 Unitários

- classifier;
- manifest validation;
- config sanitization;
- scope;
- readiness;
- custo;
- schedule;
- idempotency;
- lifecycle;
- update compatibility;
- demand redaction.

## 24.2 Contrato

- chat proposal ↔ API;
- API ↔ schema;
- Factory ↔ Work Run;
- Work Run ↔ Skill;
- Skill ↔ Tool Gateway;
- Work Run ↔ Artifact;
- routine ↔ work_run;
- approval ↔ effect.

## 24.3 Multi-tenant

Testes negativos:

- Resulta não vê AutoFleet;
- AutoFleet não edita Resulta;
- personal de usuário A não aparece para usuário B;
- artifact e run não vazam;
- template global não expõe segredo;
- Admin não recebe conteúdo bruto sem necessidade.

## 24.4 Scheduling

- timezone;
- mudança de dia;
- DST quando aplicável;
- intervalo mínimo;
- monthly edge cases;
- restart;
- duplicate tick;
- event dedupe;
- anti-loop;
- cooldown.

## 24.5 Side effects

- approval;
- edit/reject;
- exactly/effectively-once;
- unknown reconciliation;
- recipient allowlist;
- cancel before effect;
- retry after provider error.

## 24.6 UX

- desktop;
- mobile;
- criação pelo chat;
- criação pelo dashboard;
- instalação completa;
- erro de conexão;
- custo bloqueado;
- update;
- rollback;
- pausa;
- empty states;
- linguagem humana.

## 24.7 Broker Outcome Regression Pack

Validar:

- Auxiliar real é instalado;
- primeiro test run funciona;
- Rotina inicia Work Run;
- resultado aparece no dashboard;
- artifact abre;
- WhatsApp/e-mail entregam quando autorizados;
- custo é registrado;
- approval funciona;
- restart não perde trabalho;
- pausar interrompe próximos triggers;
- atualizar preserva configuração;
- rollback funciona;
- desinstalar não apaga histórico;
- login, Atendimento e pareamento continuam funcionando.

---

# 25. Plano de execução em três blocos

## Bloco A — Modelo, Factory e migração estrutural

Implementar:

- migrations;
- releases;
- revisões;
- manifest;
- classifier;
- readiness resolver;
- proposal builder;
- lifecycle;
- demand/gaps;
- adapters;
- ligações com Work Runs/Skills/Artifacts;
- testes unitários e multi-tenant.

Gate A:

- schema verde;
- baseline preservado;
- nenhum órfão/cross-tenant;
- Factory produz proposta válida;
- instalação idempotente;
- Work Run criado corretamente.

## Bloco B — Conversa, dashboard, triggers e gestão

Implementar:

- tools do Core;
- APIs;
- Galeria;
- Meus Auxiliares;
- Criar Auxiliar;
- Execuções;
- detalhe;
- instalação/test/activation;
- Rotinas evoluídas;
- manual/schedule/event/condition;
- approvals;
- budgets;
- artifacts/deliveries;
- Admin mínimo.

Gate B:

- criação pelo chat funciona;
- criação pelo dashboard funciona;
- status sincronizado;
- Rotina cria Work Run;
- test run não gera side effect indevido;
- approvals e custos funcionam.

## Bloco C — Templates, UX acceptance, cutover e produção

Implementar:

- migrar templates existentes;
- publicar conjunto inicial;
- substituir UI antiga;
- remover mocks;
- cutover writers;
- deploy;
- canário Amandus;
- canário Resulta;
- canário AutoFleet;
- corrigir achados;
- ativar produção;
- publicar relatório final.

Gate C:

- templates operacionais;
- zero caminho paralelo soberano;
- Amandus/Resulta/AutoFleet verdes;
- dashboards funcionais;
- observabilidade e rollback prontos;
- Founder aprova UX e resultado.

---

# 26. Definition of Done

A SPEC-058 só termina quando:

1. Auxiliar e Rotina são conceitos distintos em código, banco, UI e prompts.
2. O Factory escolhe corretamente o padrão de trabalho.
3. Nem toda instalação cria Agent.
4. Templates têm releases imutáveis.
5. Instalações têm revisões e rollback.
6. Rotinas acionam Work Runs.
7. `work_runs` é autoridade de execução.
8. Skills/Tool Gateway governam capacidades.
9. Artifacts são entregues quando apropriado.
10. Chat e dashboard criam/administram o mesmo objeto.
11. Dependências e conexões são verificadas antes da ativação.
12. Test run é real e seguro.
13. Approval e side effects idempotentes funcionam.
14. Custos e budgets são atribuídos.
15. Demanda e capability gaps são registrados com privacidade.
16. Portal Admin administra catálogo e instalações.
17. Templates iniciais estão ativos.
18. Mocks e autoridade legada concorrente foram removidos.
19. Amandus, Resulta e AutoFleet passaram.
20. Funcionalidade está ligada em produção.
21. APPLY/VERIFY/ROLLBACK e relatório final existem.

---

# 27. Critérios de parada legítima

O executor só deve parar e pedir decisão do Founder quando encontrar:

- risco real de perda de dados;
- impossibilidade de migrar sem downtime relevante;
- conflito entre autoridade canônica e produção viva não documentada;
- licença impeditiva;
- necessidade de credencial externa não disponível;
- decisão comercial sobre cobrança/preço não definida;
- side effect que legalmente exige validação específica;
- template inicial sem dados reais suficientes.

Não parar por:

- arquivo grande;
- necessidade de testes;
- necessidade de refatorar código legado;
- necessidade de criar migration;
- necessidade de corrigir UI;
- necessidade de executar deploy;
- necessidade de revisar várias camadas.

---

# 28. Fora do escopo desta SPEC

Ficam para SPECs seguintes:

- Garimpo v3 completo e proatividade avançada — SPEC-059;
- Firecrawl e pesquisa profunda avançada — SPEC-060;
- Control Plane completo — SPEC-061;
- billing comercial final, evals globais e launch readiness consolidado — SPEC-062;
- cotações e renovações automatizadas;
- marketing/growth/social publishing completo;
- criação de código arbitrário pelo tenant;
- marketplace público externo de terceiros.

A arquitetura deve permitir essas expansões sem refazer o núcleo.

---

# 29. Referências de arquitetura

O executor deverá consultar fontes primárias atuais durante implementação:

- OpenAI Skills e plugins: workflows reutilizáveis, criação por chat, instalação, apps e permissões de workspace;
- ChatGPT Work: trabalhos longos e entregáveis finalizados;
- ChatGPT Tasks: tarefas pontuais/recorrentes e gestão dedicada;
- Claude Cowork: conectores, trabalhos delegados e tarefas recorrentes;
- Hermes Agent: Skills on-demand, criação/atualização de Skills, scheduler, subagentes e delivery;
- LangGraph: persistence, interrupts, resume e durable execution;
- Redis Streams: consumer groups e recuperação;
- MCP: host authority, consentimento e least privilege.

As referências inspiram padrões. Não autorizam copiar marca, UI ou criar runtime paralelo.

---

# 30. Próxima SPEC

A próxima autoridade será:

```text
SPEC-059 — Briefing, Proatividade & Garimpo v3
```

Ela deverá usar:

- Work Runs;
- Skills;
- Tool Gateway;
- Artifact Hub;
- Auxiliary Factory;
- demand signals;
- broker insights;
- eventos operacionais;
- evidências;
- aprovação;
- medição de resultado.

Não deverá criar outro motor de sugestões, outro scheduler, outro catálogo de Auxiliares ou outro sistema de aprendizagem.
