# SPEC-056 — Skill Registry & Tool Gateway do AutoBrokers

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANÔNICA E AUTORIZADA PARA EXECUÇÃO — aprovada pelo Founder em 24/07/2026  
**Autoridade superior:** `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`, `SPEC-053-autobrokers-work-os-core-harness.md`, `SPEC-054-foundation-hardening-schema-governance.md` e `SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`  
**Runtime preservado:** Smith + LangGraph/LangChain + FastAPI + Supabase/Postgres + Redis + Qdrant + MinIO  
**Nome oficial do agente central:** **AutoBrokers**  
**Escopo:** criar o catálogo canônico e versionado de Skills, consolidar a governança das ferramentas existentes em um único Tool Gateway, selecionar dinamicamente apenas as capacidades necessárias para cada trabalho, integrar tudo ao Work Run e ativar uma biblioteca inicial de Skills operacionais de lançamento.  
**Natureza desta SPEC:** autoriza migrations, backend, runtime, APIs, UI operacional mínima, seeds, testes, deploy, migração do legado e ativação em produção.  
**Dependência de execução:** os bloqueadores P0 da SPEC-054 e a fundação operacional da SPEC-055 devem estar implementados ou ser executados no mesmo programa de implementação, respeitando a ordem canônica.

---

# 0. Comando direto ao executor — Fable, Opus, Codex ou equivalente

Você está autorizado a **implementar integralmente esta SPEC em linha reta**.

Esta não é uma SPEC de laboratório, protótipo, catálogo visual vazio ou arquitetura que ficará desligada aguardando uma futura fase. Ao final da mesma iniciativa de execução:

- o AutoBrokers deverá selecionar Skills reais;
- o Smith deverá receber apenas as ferramentas relevantes para o trabalho atual;
- toda tool deverá passar pelo mesmo contrato de autorização e observabilidade;
- Skills publicadas deverão estar utilizáveis no chat e nos Work Runs;
- o Tool Gateway deverá estar ativo em produção;
- os caminhos legados não poderão continuar como autoridades concorrentes;
- Amandus, Resulta e AutoFleet deverão passar nos testes operacionais.

## 0.1 Doutrina de lançamento

```text
Construir com padrão definitivo.
Migrar o que já existe.
Testar na mesma execução.
Corrigir na mesma execução.
Ativar na mesma execução.
```

Não criar:

- `skill_registry_v2`;
- outro Capability Registry;
- outro Vault;
- outro MCP gateway paralelo;
- outro HTTP router paralelo;
- outro catálogo de Portal Skills;
- outro runtime de subagentes;
- catálogo visual sem execução real;
- Skill como prompt solto sem contrato;
- Tool liberada apenas porque foi mencionada no prompt;
- conexão ou segredo armazenado dentro de Skill;
- tools globais indiscriminadamente anexadas ao modelo;
- versão beta permanentemente desligada.

Feature flags são permitidas somente para rollback e corte controlado dentro da mesma iniciativa. A entrega não será considerada concluída com o gateway novo permanentemente em `shadow` ou `off`.

## 0.2 Número de blocos

A execução deverá ocorrer em **três blocos macro**, sequenciais e com avanço automático quando os gates estiverem verdes:

1. **Bloco A — Registry canônico e migração do legado**;
2. **Bloco B — Tool Gateway dinâmico e integração ao Smith/Work Runs**;
3. **Bloco C — Biblioteca inicial, UX, cutover e lançamento**.

Esse é o menor número de blocos compatível com segurança, rollback e resultado real.

## 0.3 Saída obrigatória

Ao final, devem existir e estar ativos:

- catálogo canônico de Skills;
- releases imutáveis e versionadas;
- manifestos validados;
- catálogo canônico de Tool Definitions;
- releases de tools com schemas e políticas;
- Capability Packs versionados;
- Skill Resolver;
- Tool Gateway único;
- seleção dinâmica por Outcome, Skill, papel, tenant, conexão, risco e fase do Work Run;
- revalidação no instante da execução;
- integração com Work Runs, steps, attempts, approvals, effects, custos e tracing;
- migração das HTTP tools existentes;
- migração das MCP tools existentes;
- migração das Portal Skills atuais;
- tools nativas registradas;
- delegação para subagentes governada;
- biblioteca inicial de Skills de lançamento;
- administração mínima no Portal Admin;
- diagnóstico tenant-facing de conexões necessárias;
- evals e testes por Skill/tool;
- Authority Strict ativo;
- zero ferramenta liberada por menção em prompt;
- zero segredo em prompt, Skill, manifest, log ou checkpoint;
- Amandus, Resulta e AutoFleet validados;
- relatório final publicado.

---

# 1. Ordem de leitura e autoridade

Antes de alterar código ou banco:

1. atualizar a `main`;
2. registrar o commit inicial;
3. ler a SPEC-052;
4. ler a SPEC-053;
5. ler a SPEC-054 e seu relatório de execução;
6. ler a SPEC-055 e seu relatório de execução, quando existir;
7. ler `SPEC-014-capability-registry-knowledge-os.md`;
8. ler `ADR-001-runtime.md` e `ADR-002-vault.md`;
9. ler o código real do Capability Resolver, Tool Authority, Graph, HTTP Router, MCP Gateway, MCP Factory, Portal Skills, Subagents e Vault;
10. confirmar o schema vivo em modo read-only.

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
→ SPECs posteriores subordinadas
→ ADRs e documentos históricos quando não conflitarem
→ código atual apenas como estado de implementação
```

Em conflito, não criar uma terceira arquitetura.

---

# 2. Resultado de produto

O corretor não deve precisar conhecer MCP, API, tool, provider, token, prompt ou modelo.

Ele deve pedir um resultado:

- “Analise este documento e me diga os pontos importantes.”
- “Pesquise as mudanças recentes desta seguradora.”
- “Consulte a apólice deste cliente.”
- “Mostre os gargalos da minha operação.”
- “Crie um briefing com o que exige minha atenção.”
- “Prepare os dados para um relatório.”
- “Envie isto somente depois que eu aprovar.”
- “Crie um Auxiliar que faça essa tarefa toda semana.”

O AutoBrokers deve transformar esse pedido em:

```text
Outcome
→ Skill adequada
→ contexto necessário
→ Capability Pack mínimo
→ tools autorizadas
→ Work Run/execução
→ resultado validado
```

## 2.1 Objetivos de negócio

Esta SPEC deve permitir que o AutoBrokers:

- resolva mais trabalhos sem configuração técnica manual;
- reduza erros de seleção de ferramenta;
- diminua tokens desperdiçados com tools irrelevantes;
- aumente confiabilidade em ações de negócio;
- aproveite InfoCap, documentos, portais e conexões da corretora;
- entregue pesquisas, análises e operações especializadas em seguros;
- permita adicionar novas capacidades sem bagunçar o Core;
- habilite novos Auxiliares sem criar um runtime por Auxiliar;
- atribua custo e resultado a Skill, tool, tenant e Work Run;
- proteja segredos e dados multi-tenant;
- transforme pedidos recorrentes em produtos instaláveis;
- permitir expansão rápida do arsenal sem reduzir a inteligência do modelo.

## 2.2 Experiência de lançamento

Quando esta SPEC estiver concluída:

- o AutoBrokers entenderá qual Skill usar;
- a resposta mostrará quando precisa de uma conexão;
- a UI não apresentará erro técnico quando uma capability estiver indisponível;
- o usuário poderá conectar a conta correta ou escolher outra abordagem;
- ações sensíveis passarão por approval executável;
- o trabalho continuará no Work Run;
- o Admin verá quais Skills e tools estão em produção;
- o Founder poderá desativar, publicar, reverter e auditar versões;
- nenhuma corretora enxergará segredo, manifest interno completo ou configuração de outra corretora.

---

# 3. Princípios invioláveis

1. **O Capability Registry existente continua sendo a autoridade de autorização.**
2. **Skill Registry não substitui Capability Registry; complementa-o.**
3. **Skill é procedimento de resultado, não permissão.**
4. **Capability é poder governável, não implementação.**
5. **Tool é implementação executável, não produto.**
6. **Connector é acesso autenticado, não capability.**
7. **MCP é protocolo, não cérebro, Skill ou produto.**
8. **Smith continua sendo o único runtime cognitivo.**
9. **Work Run continua sendo a autoridade universal de execução.**
10. **Vault continua sendo a autoridade de segredos.**
11. **Nenhuma Skill contém senha, token, cookie ou secret.**
12. **Nenhuma tool é autorizada por texto de prompt.**
13. **A autorização é revalidada no momento da chamada.**
14. **O modelo recebe somente as tools necessárias para a fase atual.**
15. **Subagente nunca recebe mais poderes do que o pai.**
16. **Atendimento externo não recebe arsenal genérico do Core.**
17. **Tools de escrita e side effects exigem idempotência.**
18. **Ações sensíveis exigem approval executável.**
19. **Conteúdo retornado por web/MCP é não confiável até validação.**
20. **Input e output usam schemas formais.**
21. **Toda release publicada é imutável.**
22. **Toda mudança de comportamento gera nova release.**
23. **Rollback é troca de release ativa, não edição de histórico.**
24. **Nenhum catálogo paralelo será criado por domínio.**
25. **Portal Skills serão especializações do Skill Registry, não outro Registry.**
26. **Tool Gateway governa todas as famílias de tools.**
27. **A plataforma pode pagar uma tool; o custo é atribuído ao tenant que a utilizou.**
28. **Conexões tenant-owned usam credenciais da própria corretora/usuário.**
29. **Não carregar tudo no prompt.**
30. **Resultado para o corretor integra a Definition of Done.**

---

# 4. Estado atual confirmado e peças que devem ser preservadas

## 4.1 Capability Resolver

Já existe um resolver que consulta:

- `capabilities`;
- `capability_bindings`;
- `tenant_capability_entitlements`;
- `tenant_connections`;
- papel do Agent;
- estado da conexão;
- saúde de alguns providers.

Ele falha fechado em erro e papel inválido.

Deve ser preservado e evoluído para:

- interpretar `scope`;
- interpretar `limits`;
- resolver connection correta;
- devolver políticas de runtime;
- suportar Capability Packs;
- produzir decisão auditável;
- revalidar no momento da chamada.

## 4.2 Tool Authority

Já existe uma camada de compatibilidade que mapeia tools legadas para capabilities e suporta modo estrito.

Estado anterior à SPEC-054:

- `AUTHORITY_STRICT_MODE` desligado por padrão;
- `tools_config` ainda influencia o comportamento legado;
- MCP é filtrado por capability somente no modo estrito;
- HTTP Router pode ser anexado amplamente.

A SPEC-054 deve endurecer essa base. A SPEC-056 fará o corte definitivo para o Tool Gateway.

## 4.3 Graph Smith

O grafo já:

- cria Knowledge Base Tool;
- resolve capabilities;
- adiciona web search;
- adiciona Human Handoff;
- adiciona CSV Analytics;
- adiciona HTTP Router;
- descobre MCP tools por Agent;
- cria ferramentas de delegação para subagentes.

O problema é que a montagem ainda ocorre de maneira predominantemente direta e global para o Agent.

A evolução será:

```text
Graph
→ Skill Runtime Context
→ Tool Gateway resolve toolset da fase
→ wrappers autorizados são expostos ao modelo
→ chamada passa novamente pelo Gateway
```

## 4.4 HTTP tools

Já existem:

- `agent_http_tools`;
- factory de schema Pydantic;
- `HttpToolRouter`;
- configuração dinâmica no banco.

Problemas históricos:

- autorização por menção no prompt;
- headers/config potencialmente acoplados à row;
- URL genérica;
- retorno textual sem envelope canônico;
- ausência de versionamento formal;
- ausência de release imutável;
- ausência de política de custo/risco/approval por tool.

A SPEC-054 fecha egress/SSRF. A SPEC-056 migra essas tools para o catálogo e Gateway.

## 4.5 MCP Gateway

Já existe gateway interno para:

- Google Calendar;
- Google Drive;
- Slack;
- GitHub.

Também existem tabelas de servidores, conexões e tools por Agent.

A SPEC-054 deve corrigir environment, sandbox e revalidação. A SPEC-056 deve:

- registrar MCP server e tools no catálogo único;
- versionar o snapshot de descoberta;
- homologar cada tool;
- impedir exposição automática de toda tool descoberta;
- selecionar tools por Skill e Capability Pack;
- preservar os servidores internos atuais;
- suportar futuramente MCP remoto sem mudar a autoridade.

## 4.6 Portal Skills

Existe uma definição TypeScript hardcoded de Portal Skill e runner/factory especializados.

Essa estrutura contém conceitos úteis:

- objetivo;
- inputs obrigatórios;
- ações permitidas/proibidas;
- passos;
- outputs;
- guardrails;
- promotion status.

Ela deve ser migrada para o Skill Manifest canônico.

Preservar:

- Portal Worker;
- Portal Map;
- SessionRef;
- Vault;
- evidências;
- runner especializado;
- regras de CAPTCHA/2FA/HITL.

Eliminar como autoridade canônica:

- array hardcoded separado;
- promoção limitada por boolean solto;
- catálogo de Portal Skills independente.

## 4.7 Subagentes

Já existe delegação por `agent_delegations` e criação de ferramentas para subagentes.

Deve ser preservada, mas governada como tool de delegação:

- capability explícita;
- Skill permite ou proíbe delegação;
- subset de tools;
- child Work Run quando assíncrono;
- limites de custo, tempo e profundidade;
- zero escalada de privilégio.

## 4.8 Lacunas atuais

- não existe Skill Registry canônico;
- não existem releases imutáveis de Skill;
- não existe manifesto universal;
- não existe Tool Definition universal;
- não existe release universal de tool;
- não existe Capability Pack versionado;
- seleção de tool não é dirigida por Outcome/Skill/fase;
- tool descriptions podem ser carregadas de origens não homologadas;
- não há envelope universal de output;
- uso/custo não está consolidado por Skill;
- Portal Skills vivem em catálogo separado;
- HTTP/MCP/native/subagent seguem caminhos distintos até a execução;
- Admin não possui visão única de Skill → capability → tool → conexão → uso.

---

# 5. Ontologia oficial

## 5.1 Outcome

Resultado desejado pelo usuário ou sistema.

Exemplos:

- analisar documento;
- consultar apólice;
- pesquisar mercado;
- entregar relatório;
- enviar mensagem aprovada;
- recuperar boleto;
- criar rotina.

Outcome não é Skill.

## 5.2 Skill

Identidade lógica de um procedimento reutilizável para produzir um Outcome.

Exemplos:

- `core.answer_with_evidence`;
- `documents.analyze_insurance_document`;
- `research.web_brief`;
- `insurance.policy_lookup`;
- `operations.csv_analysis`;
- `portals.billing_document_read`.

## 5.3 Skill Release

Versão imutável e executável da Skill.

Contém:

- instruções;
- critérios de uso;
- anti-critérios;
- inputs;
- outputs;
- etapas;
- policies;
- capabilities;
- tools;
- orçamento;
- riscos;
- approvals;
- fallbacks;
- evals;
- compatibilidade de runtime.

## 5.4 Capability

Poder governável e medível.

Exemplo:

```text
operational.infocap.policy_lookup.read
```

Capability não descreve como a ação é executada.

## 5.5 Capability Pack

Pacote versionado de capabilities e tools apropriado a uma classe de trabalho.

Exemplo:

```text
pack.research.readonly.v1
```

Pode conter:

- web search;
- leitura de páginas;
- RAG global;
- RAG tenant;
- geração de briefing;
- limites de chamadas;
- política read-only.

## 5.6 Tool Definition

Identidade lógica de uma função executável.

Exemplos:

- `knowledge.search`;
- `web.search`;
- `documents.extract`;
- `infocap.lookup_policy`;
- `portal.run_journey`;
- `google_drive.search_files`;
- `human.request_handoff`.

## 5.7 Tool Release

Contrato imutável de execução de uma Tool Definition:

- input schema;
- output schema;
- implementação;
- provider;
- risco;
- side effect;
- idempotência;
- timeout;
- retry;
- health;
- custo;
- aprovação;
- sandbox;
- egress;
- versão mínima do runtime.

## 5.8 Connector Template

Tipo de conexão suportada pelo Vault.

Exemplo:

- Google Drive;
- InfoCap;
- Slack;
- portal da seguradora.

## 5.9 Tenant Connection

Conexão real de uma corretora/usuário, com segredo referenciado no Vault.

## 5.10 Entitlement

Direito daquele tenant a usar uma capability, com limites e conexão aplicável.

## 5.11 Tool Invocation

Uma chamada concreta registrada e ligada a:

- tenant;
- Work Run;
- step;
- attempt;
- Skill Release;
- Tool Release;
- capability;
- approval/effect;
- custo;
- resultado.

## 5.12 Workflow

Ordem operacional de steps.

Uma Skill pode usar:

- um workflow determinístico;
- um Agent dinâmico;
- uma combinação dos dois.

## 5.13 MCP Tool, Resource e Prompt

No MCP:

- **tool** executa função;
- **resource** fornece contexto;
- **prompt** fornece template/instrução do servidor.

Nenhum deles é automaticamente confiável ou autorizado.

---

# 6. Arquitetura canônica

```text
Pedido / Work Run / Rotina / Auxiliar
                │
                ▼
          Outcome Router
                │
                ▼
          Skill Resolver
                │
                ▼
       Skill Release publicada
                │
                ▼
         Capability Resolver
                │
                ├── papel/Agent
                ├── tenant entitlement
                ├── conexão/Vault
                ├── provider health
                ├── risco/approval
                ├── budget/limits
                └── fase/step atual
                │
                ▼
       Capability Pack mínimo
                │
                ▼
           Tool Gateway
                │
      ┌─────────┼─────────┬──────────┬──────────┐
      ▼         ▼         ▼          ▼          ▼
   Native      HTTP      MCP       Portal     Delegation
      │         │         │          │          │
      └─────────┴─────────┴──────────┴──────────┘
                │
                ▼
 Input validation → authority → approval/effect → execution
                │
                ▼
 output schema → redaction → cost/trace → Work Run
```

## 6.1 Autoridades

| Responsabilidade | Autoridade |
|---|---|
| identidade da Skill | `skills` |
| versão executável da Skill | `skill_releases` |
| publicação/rollback | release ativa |
| autorização | Capability Registry |
| composição de capacidades | Capability Pack |
| identidade da tool | `tool_definitions` |
| contrato executável | `tool_releases` |
| segredo | Vault |
| conexão real | `tenant_connections` |
| execução | Work Run da SPEC-055 |
| side effect | `work_effects` |
| aprovação | `approval_requests` |
| contexto/RAG/memória | SPEC-052 |
| arquivos/artifacts | SPEC-057 |
| catálogo de Auxiliares | SPEC-058 |

## 6.2 Um único Tool Gateway

Criar ou consolidar:

```text
backend/app/services/tool_gateway/
```

Responsabilidades:

1. receber `ToolInvocationRequest`;
2. resolver tenant/run/step/attempt;
3. carregar Tool Release ativa/pinada;
4. validar Skill Release e binding;
5. validar capability;
6. validar entitlement;
7. validar papel e Agent;
8. validar conexão e provider;
9. validar risk/approval;
10. validar budget/rate limit;
11. validar input schema;
12. sanitizar e classificar dados;
13. reservar `work_effect` quando necessário;
14. executar adapter correto;
15. validar output schema;
16. redigir segredos/PII desnecessária;
17. registrar invocation, custo, latência e trace;
18. confirmar/reconciliar effect;
19. devolver envelope tipado.

Nenhuma família de tool deve contornar esse fluxo depois do cutover.

---

# 7. Modelo de dados canônico

Todas as migrations seguem APPLY/VERIFY/ROLLBACK da SPEC-054.

## 7.1 `skills`

```text
id uuid PK
skill_key text UNIQUE NOT NULL
name text NOT NULL
description text NOT NULL
category text NOT NULL
owner text NOT NULL
visibility text NOT NULL
business_domain text NULL
is_active boolean NOT NULL DEFAULT true
created_at timestamptz
updated_at timestamptz
```

Valores iniciais de `owner`:

- `platform`;
- `tenant`;
- `operational`.

Valores de `visibility`:

- `internal`;
- `admin`;
- `tenant_catalog`;
- `tenant_installed`;
- `system_only`.

## 7.2 `skill_releases`

```text
id uuid PK
skill_id uuid NOT NULL FK skills
version text NOT NULL
status text NOT NULL
manifest jsonb NOT NULL
instruction_markdown text NOT NULL
content_hash text NOT NULL
runtime_min_version text NULL
changelog text NULL
created_by_user_id uuid NULL
approved_by_user_id uuid NULL
created_at timestamptz
approved_at timestamptz NULL
published_at timestamptz NULL
deprecated_at timestamptz NULL
superseded_by_release_id uuid NULL
```

Constraints:

- unique `(skill_id, version)`;
- unique `(skill_id, content_hash)`;
- release publicada é imutável;
- somente uma release default ativa por Skill;
- mudança de manifest/instrução gera nova versão;
- status validado.

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

## 7.3 `skill_bindings`

Mapeia onde a Skill pode ser usada.

```text
id uuid PK
skill_id uuid NOT NULL
skill_release_id uuid NULL
target_type text NOT NULL
target_key text NOT NULL
company_id uuid NULL
agent_id uuid NULL
enabled boolean NOT NULL DEFAULT true
priority integer NOT NULL DEFAULT 50
config_override jsonb NOT NULL DEFAULT '{}'
valid_from timestamptz NULL
valid_until timestamptz NULL
created_at timestamptz
updated_at timestamptz
```

`target_type` inicial:

- `platform`;
- `agent_role`;
- `agent`;
- `auxiliary_template`;
- `tenant`;
- `system_workflow`.

Regras:

- binding tenant-scoped exige `company_id`;
- Agent deve pertencer à company quando company for informada;
- override não pode ampliar capabilities da release;
- binding desabilitado bloqueia uso;
- Skill de Atendimento exige target explícito.

## 7.4 `capability_packs`

```text
id uuid PK
pack_key text UNIQUE NOT NULL
name text NOT NULL
description text NOT NULL
category text NOT NULL
owner text NOT NULL
is_active boolean NOT NULL DEFAULT true
created_at timestamptz
updated_at timestamptz
```

## 7.5 `capability_pack_releases`

```text
id uuid PK
capability_pack_id uuid NOT NULL
version text NOT NULL
status text NOT NULL
manifest jsonb NOT NULL
content_hash text NOT NULL
published_at timestamptz NULL
created_at timestamptz
```

## 7.6 `capability_pack_members`

```text
id uuid PK
pack_release_id uuid NOT NULL
member_type text NOT NULL
member_key text NOT NULL
required boolean NOT NULL DEFAULT true
phase_key text NULL
conditions jsonb NOT NULL DEFAULT '{}'
limits jsonb NOT NULL DEFAULT '{}'
ordinal integer NOT NULL DEFAULT 0
```

`member_type`:

- `capability`;
- `tool`;
- `skill`.

## 7.7 `tool_definitions`

```text
id uuid PK
tool_key text UNIQUE NOT NULL
name text NOT NULL
description text NOT NULL
category text NOT NULL
implementation_kind text NOT NULL
owner text NOT NULL
provider text NULL
capability_key text NOT NULL FK capabilities
risk_level text NOT NULL
side_effect_class text NOT NULL
data_classification text NOT NULL
requires_connection boolean NOT NULL DEFAULT false
requires_approval boolean NOT NULL DEFAULT false
is_active boolean NOT NULL DEFAULT true
created_at timestamptz
updated_at timestamptz
```

`implementation_kind`:

- `native`;
- `adapter`;
- `http`;
- `mcp`;
- `portal`;
- `browser`;
- `computer_use`;
- `delegation`;
- `internal_service`.

`side_effect_class`:

- `none`;
- `read`;
- `prepare`;
- `write_reversible`;
- `write_irreversible`;
- `financial`;
- `communication`;
- `external_commitment`.

## 7.8 `tool_releases`

```text
id uuid PK
tool_id uuid NOT NULL
version text NOT NULL
status text NOT NULL
input_schema jsonb NOT NULL
output_schema jsonb NOT NULL
execution_manifest jsonb NOT NULL
content_hash text NOT NULL
runtime_min_version text NULL
created_at timestamptz
published_at timestamptz NULL
deprecated_at timestamptz NULL
```

Constraints equivalentes às Skill Releases.

## 7.9 `skill_capability_requirements`

```text
id uuid PK
skill_release_id uuid NOT NULL
capability_key text NOT NULL
requirement text NOT NULL
phase_key text NULL
scope_required jsonb NOT NULL DEFAULT '{}'
limits_required jsonb NOT NULL DEFAULT '{}'
ordinal integer NOT NULL DEFAULT 0
```

`requirement`:

- `required`;
- `optional`;
- `fallback`;
- `forbidden`.

## 7.10 `skill_tool_requirements`

```text
id uuid PK
skill_release_id uuid NOT NULL
tool_key text NOT NULL
phase_key text NULL
requirement text NOT NULL
max_calls integer NULL
approval_override text NULL
conditions jsonb NOT NULL DEFAULT '{}'
ordinal integer NOT NULL DEFAULT 0
```

Um override nunca reduz a proteção mínima definida pela Tool Release ou capability.

## 7.11 `tool_invocations`

Registro operacional queryable.

```text
id uuid PK
company_id uuid NOT NULL
work_run_id uuid NULL
work_step_id uuid NULL
work_attempt_id uuid NULL
skill_release_id uuid NULL
tool_release_id uuid NOT NULL
capability_key text NOT NULL
agent_id uuid NULL
user_id uuid NULL
connection_id uuid NULL
invocation_key text NOT NULL
status text NOT NULL
input_fingerprint text NOT NULL
input_summary jsonb NOT NULL DEFAULT '{}'
output_summary jsonb NOT NULL DEFAULT '{}'
provider_reference text NULL
approval_request_id uuid NULL
work_effect_id uuid NULL
started_at timestamptz
finished_at timestamptz NULL
latency_ms integer NULL
cost_amount numeric NOT NULL DEFAULT 0
currency text NOT NULL DEFAULT 'BRL'
error_code text NULL
trace_id text NULL
created_at timestamptz
```

Unique `(company_id, invocation_key)` quando a chamada exigir idempotência.

Não armazenar input/output bruto sensível.

## 7.12 Ligações com Work Runs

Adicionar de forma expand-only, quando ainda não existirem:

```text
work_runs.skill_release_id
work_runs.capability_pack_release_id
work_steps.skill_release_id
work_steps.tool_release_id
```

A release usada por um run não muda no meio da execução, exceto por migração explícita e segura.

## 7.13 RLS e acesso

- Skills/platform releases: leitura runtime service-only; metadados públicos ao tenant apenas quando apropriado.
- manifests completos: Admin/runtime, não tenant comum.
- tenant Skill/binding: company-scoped.
- tool definitions/releases: Admin/runtime.
- tool invocations: tenant vê somente seus dados resumidos; Admin vê global.
- segredo nunca aparece em nenhuma tabela desta SPEC.

---

# 8. Skill Manifest canônico

Cada release deve validar um schema formal.

## 8.1 Estrutura obrigatória

```yaml
schema_version: 1
skill_key: research.web_brief
version: 1.0.0
name: Pesquisa web com briefing executivo
category: research
owner: platform
business_domain: insurance
status: published

outcome:
  type: research_brief
  description: Produzir briefing confiável com fontes e implicações para a corretora.
  success_criteria:
    - fontes relevantes
    - datas e provenance
    - síntese orientada à decisão

selection:
  triggers:
    - pesquisar mercado
    - analisar concorrentes
    - buscar atualização recente
  anti_triggers:
    - pergunta puramente interna da corretora
    - confirmação de cobertura específica
  required_intents:
    - research
  confidence_threshold: 0.70

inputs:
  schema: {...}
  required_context:
    - company_id
    - requester
  optional_context:
    - insurance_line
    - geography
    - competitors

workflow:
  kind: hybrid
  phases:
    - key: plan
    - key: search
    - key: verify
    - key: synthesize

capabilities:
  required:
    - platform.web.search
    - knowledge.global.search
  optional:
    - knowledge.tenant.search
  forbidden:
    - operational.whatsapp.send

capability_pack:
  key: pack.research.readonly
  version: 1.0.0

tools:
  required:
    - web.search
  optional:
    - web.read_page
    - knowledge.search
  max_exposed_per_phase: 6
  max_calls_total: 20

risk:
  level: low
  external_side_effect: false
  approval_policy: none

data_policy:
  input_classification: internal
  output_classification: internal
  allowed_sources:
    - public_web
    - global_knowledge
    - tenant_knowledge
  forbidden_data:
    - secrets

model_policy:
  profile: strong_research
  structured_output: true
  fallback_profile: balanced

budget:
  max_cost_brl: 5.00
  max_duration_seconds: 600

output:
  schema: {...}
  formats:
    - chat
  citations_required: true

fallbacks:
  - when: web_provider_unavailable
    action: use_curated_knowledge_and_disclose_limit

observability:
  emit_progress: true
  metrics:
    - source_count
    - verified_claims
    - cost
    - latency

evals:
  pack: eval.research.web_brief.v1
```

## 8.2 Instruções da Skill

`instruction_markdown` deve conter:

- missão;
- quando usar;
- quando não usar;
- ordem de raciocínio operacional;
- critérios de fonte;
- regras de citação;
- tratamento de ambiguidade;
- regras de segurança;
- estrutura do resultado;
- falhas conhecidas;
- política de escalada.

Não deve conter:

- API key;
- segredo;
- UUID de tenant;
- senha;
- URL privada;
- prompt de outra corretora;
- instrução para ignorar policies do runtime.

## 8.3 Versionamento

Usar semver:

- patch: correção sem mudança relevante de contrato;
- minor: nova capacidade compatível;
- major: mudança de input/output, risco ou workflow.

Runs em andamento permanecem pinados à release original.

---

# 9. Tool Release Manifest

Exemplo:

```yaml
schema_version: 1
tool_key: infocap.lookup_policy
version: 1.0.0
implementation_kind: adapter
implementation_ref: app.tools.infocap.lookup_policy
capability_key: operational.infocap.policy_lookup.read
provider: infocap
owner: operational

operation:
  class: read
  idempotent: true
  timeout_seconds: 30
  max_retries: 2
  concurrency_key: company

connection:
  required: true
  connector_slugs:
    - infocap
  credential_fields: []

security:
  risk_level: high
  approval_required: false
  data_classification: restricted
  input_secret_allowed: false
  output_redaction: policy_summary

input_schema: {...}
output_schema: {...}

cost:
  model: provider_call
  estimate: {...}

health:
  check_kind: adapter
  stale_after_seconds: 300

ui:
  display_name: Consultar apólice no InfoCap
  progress_label: Consultando a apólice
  success_label: Apólice localizada
```

## 9.1 Tool Envelope de retorno

Toda tool deve retornar internamente:

```json
{
  "success": true,
  "data": {},
  "summary": "",
  "provider_reference": null,
  "citations": [],
  "warnings": [],
  "classification": "internal",
  "trust_level": "authoritative",
  "truncated": false,
  "cost": {"amount": 0, "currency": "BRL"},
  "metrics": {"latency_ms": 0}
}
```

O modelo pode receber uma projeção segura desse envelope, não necessariamente o objeto integral.

## 9.2 Trust levels

- `authoritative`: sistema oficial/documento primário;
- `verified`: validado por múltiplas fontes;
- `tenant_internal`: informação da corretora;
- `untrusted_external`: web/MCP externo;
- `generated`: inferência da LLM;
- `unknown`.

Conteúdo `untrusted_external` nunca pode substituir instruções do sistema, policies ou dados oficiais.

---

# 10. Skill Resolver

## 10.1 Ordem de seleção

1. Skill explicitamente fixada por workflow/Auxiliar/Rotina;
2. Skill exigida por Work Step;
3. Skill solicitada nominalmente pelo usuário;
4. shortlist determinística por Outcome, categoria, tags e papel;
5. escolha estruturada pela LLM entre candidatas autorizadas;
6. generic governed mode quando nenhuma Skill se aplica.

## 10.2 Shortlist

Não enviar o catálogo inteiro ao modelo.

Cada Skill deve possuir um cartão resumido:

```text
skill_key
name
one-line outcome
triggers
anti-triggers
required capabilities
risk
connection requirements
```

Default:

- no máximo 8 Skills candidatas;
- no máximo 3 finalistas;
- uma Skill principal;
- Skills auxiliares somente quando declaradas.

## 10.3 Confidence

Se confiança abaixo do threshold:

- fazer uma pergunta objetiva;
- escolher generic governed mode;
- ou criar Work Run de planejamento sem side effect.

Nunca escolher aleatoriamente uma Skill de escrita.

## 10.4 Regras por papel

### Core

Pode selecionar Skills amplas autorizadas, inclusive pesquisa, análise, documentos e operações governadas.

### Atendimento

Somente Skills de corredor/caso explicitamente permitidas.

Sem:

- pesquisa web aberta por padrão;
- marketing;
- relatórios corporativos;
- ferramentas administrativas;
- acesso livre a todos os tenants.

### Auxiliar

Somente Skills declaradas no template/instalação e subset autorizado pelo tenant.

### Subagente

Somente Skills e tools delegadas pelo pai.

---

# 11. Seleção dinâmica de tools

## 11.1 Progressive disclosure

O modelo não recebe todos os detalhes de todas as tools.

Fases:

1. recebe resumo da Skill;
2. recebe apenas tools da fase atual;
3. chama tool;
4. runtime pode trocar o conjunto na próxima fase;
5. instruções completas ficam no runtime/contexto da Skill selecionada.

## 11.2 Limites padrão

- ideal por chamada do modelo: 4–8 tools;
- máximo padrão: 12;
- máximo absoluto: 15, somente com justificativa;
- acima disso: dividir em fases, workflow ou subagente.

## 11.3 Critérios de seleção

Uma tool só é exposta quando todos forem verdadeiros:

- Tool Definition ativa;
- Tool Release publicada;
- Skill permite;
- Capability Pack permite;
- capability ativa;
- binding do papel ativo;
- entitlement não bloqueia;
- conexão necessária saudável;
- provider saudável;
- risco compatível;
- budget disponível;
- Work Run/step compatível;
- Tool Authority permite;
- release do runtime compatível.

## 11.4 Revalidação

Na chamada, o Gateway revalida os mesmos pontos críticos.

Não confiar apenas na seleção feita no início do run.

---

# 12. Famílias de tools

## 12.1 Native tools

Registrar no catálogo:

- Knowledge Search;
- Tenant Knowledge Search;
- Memory read/write governada;
- Web Search;
- Document Extract;
- CSV Analytics;
- Human Handoff;
- Control Plane read;
- InfoCap adapters;
- Rotinas/Work Run management;
- outros adapters internos existentes.

O wrapper LangChain pode continuar, mas a autorização e observabilidade passam pelo Gateway.

## 12.2 HTTP tools

Regras definitivas:

- nenhuma URL arbitrária fornecida pelo modelo;
- target/host vem da Tool Release homologada;
- path/query/body seguem schema;
- headers sensíveis vêm do Vault/connection;
- HTTP Egress Guard obrigatório;
- redirects e tamanho seguem policy;
- output schema obrigatório;
- escrita exige idempotência/approval conforme risco;
- tool específica é selecionada no Registry;
- `HttpToolRouter` não usa “mencionada no prompt” como autoridade;
- `agent_http_tools` vira configuração/compatibilidade de implementação, não catálogo soberano.

## 12.3 MCP tools

### Server catalog

Cada MCP server deve declarar:

- server key;
- versão;
- transporte;
- owner;
- provider;
- autenticação;
- scopes OAuth;
- env allowlist;
- filesystem roots;
- egress allowlist;
- timeout;
- limites de processo;
- health check;
- trust level;
- status de homologação.

### Descoberta

`tools/list` produz snapshot de descoberta.

O snapshot deve:

- ser versionado e hasheado;
- comparar alterações;
- não ativar tools novas automaticamente;
- exigir homologação;
- registrar input schema/description;
- sinalizar breaking changes;
- criar nova Tool Release quando aprovada.

### Isolamento

- uma conexão cliente por servidor/sessão conforme protocolo;
- servidor não recebe secrets de outro servidor;
- env mínimo;
- sandbox;
- processo cancelável;
- stdout/stderr limitados e sanitizados;
- remote MCP com autorização e audience/resource validation;
- tool descriptions tratadas como conteúdo não confiável.

### Recursos e prompts MCP

- resources entram no Context Assembly com provenance;
- prompts MCP não substituem system prompt;
- prompts precisam de homologação para uso automático;
- recursos sensíveis respeitam tenant e conexão.

## 12.4 Portal tools

Portal Skills se tornam Skill Releases com Tool Release:

```text
portal.run_journey
```

Parâmetros governados:

- portal;
- journey;
- account/session ref;
- business inputs;
- action mode;
- evidence requirements.

O runner/factory especializado continua.

Portal Map não vira Skill.

## 12.5 Browser e computer use

Hierarquia obrigatória:

```text
adapter/API oficial
→ conector autorizado
→ tool especializada
→ browser estruturado
→ computer use
```

Computer use é último recurso, com:

- sandbox;
- screenshot/evidence;
- allowlist de domínio;
- approval;
- cancelamento;
- limites;
- sem segredo no modelo.

## 12.6 Delegation tool

Subagente é acessado por tool governada.

A delegação deve declarar:

- tarefa;
- contexto mínimo;
- Skills permitidas;
- tools permitidas;
- max depth;
- max iterations;
- timeout;
- budget;
- output schema.

Subagente não recebe automaticamente todas as tools do pai.

---

# 13. Capability Packs iniciais

## 13.1 `pack.core.knowledge`

- conhecimento global;
- conhecimento tenant;
- memória de company/user;
- leitura apenas;
- sem side effect.

## 13.2 `pack.documents.analysis`

- extração;
- classificação;
- conhecimento;
- análise estruturada;
- sem envio externo.

## 13.3 `pack.research.readonly`

- web search;
- leitura de fontes;
- conhecimento global/tenant;
- citações;
- sem ação externa.

## 13.4 `pack.operations.analytics`

- control plane read;
- CSV analytics;
- dados operacionais autorizados;
- cálculos;
- sem escrita externa.

## 13.5 `pack.insurance.policy_lookup`

- InfoCap/gestor conectado;
- Policy Evidence;
- documentos da apólice;
- nenhuma confirmação sem evidência.

## 13.6 `pack.portal.readonly`

- Portal Worker;
- jornadas de leitura homologadas;
- evidence;
- HITL técnico;
- sem submit de ação de negócio.

## 13.7 `pack.communication.approved`

- preparar mensagem;
- approval;
- enviar por canal autorizado;
- idempotência;
- receipt.

Esses packs devem ser versionados e usados pelas primeiras Skills.

---

# 14. Biblioteca inicial de Skills de lançamento

A SPEC só é concluída com Skills reais publicadas e executadas.

## 14.1 `core.answer_with_evidence`

Outcome:

- responder perguntas da corretora com conhecimento global, tenant e provenance.

Regras:

- não confirmar cobertura específica sem Policy Evidence;
- diferenciar fato, inferência e recomendação;
- usar RAG como evidência, não como limitação da inteligência geral;
- sem tool externa quando não necessária.

## 14.2 `documents.analyze_insurance_document`

Outcome:

- analisar PDF/documento e entregar resumo, pontos críticos, riscos e próximos passos.

Usa:

- Document Extract;
- conhecimento global/tenant;
- classificação;
- evidence references.

## 14.3 `research.web_brief`

Outcome:

- pesquisa web atualizada com fontes, síntese e implicações para corretora.

Usa:

- web search atual existente;
- leitura de fontes permitidas;
- citations;
- sem ação externa.

Research Intelligence avançada será ampliada na SPEC-060, mas esta Skill deve funcionar no lançamento com o provider atual.

## 14.4 `operations.csv_analysis`

Outcome:

- analisar arquivo tabular e produzir indicadores, anomalias e recomendações.

Regras:

- cálculos determinísticos;
- LLM interpreta;
- não inventar dados;
- output estruturado.

## 14.5 `operations.control_plane_overview`

Outcome:

- responder sobre estado operacional da corretora usando dados autorizados.

Exemplos:

- agentes ativos;
- integrações;
- alertas;
- atividades;
- pendências disponíveis.

## 14.6 `insurance.policy_lookup`

Outcome:

- localizar e resumir apólice/evidência específica.

Regras:

- conexão válida;
- tenant correto;
- apólice correta;
- provenance;
- cobertura específica somente por evidência.

## 14.7 `operations.human_handoff`

Outcome:

- encaminhar necessidade humana conforme policy.

Não deve ser tool livre; Skill/Tool governada.

## 14.8 `portals.read_business_document`

Outcome:

- recuperar informação/documento em jornada homologada de portal.

Ativação somente para portais/journeys realmente operacionais.

Não declarar pronta se o runner real não estiver verde.

## 14.9 Critério de publicação

Cada Skill exige:

- manifest válido;
- release publicada;
- capability pack;
- tools publicadas;
- test cases;
- conexão/health quando aplicável;
- custo medido;
- observabilidade;
- resultado real demonstrado.

---

# 15. Integração com Work Runs

## 15.1 Criação

O Outcome Router pode:

- responder síncrono sem Work Run para perguntas simples;
- criar Work Run pinado à Skill Release;
- criar steps com Tool Releases previstas;
- permitir seleção dinâmica por fase.

## 15.2 Runtime context

O Smith Worker deve receber contexto imutável:

```text
company_id
user_id
agent_id
work_run_id
work_step_id
skill_release_id
capability_pack_release_id
allowed_tool_release_ids
budget
risk
connections autorizadas
```

Esses valores não aparecem como argumentos controláveis pela LLM.

## 15.3 Tool invocation

Cada chamada cria/atualiza:

- `tool_invocations`;
- Work Event;
- Work Attempt metrics;
- usage/cost;
- `work_effect` quando necessário;
- trace.

## 15.4 Pinned releases

Run iniciado em uma release permanece nela.

Nova release é usada apenas por novos runs, salvo migração manual explicitamente aprovada.

## 15.5 Aprovação

Gateway cria/interpreta approval conforme:

- capability;
- Tool Release;
- Skill policy;
- tenant policy;
- risco;
- destino;
- custo;
- side effect.

A policy mais restritiva vence.

---

# 16. Segurança, privacidade e prompt injection

## 16.1 Conteúdo externo

Web, MCP, documentos e páginas podem conter instruções maliciosas.

O runtime deve:

- marcar origem e trust level;
- separar conteúdo de instrução;
- ignorar ordens do conteúdo recuperado;
- não revelar segredos;
- não ampliar tools;
- não alterar approval policy;
- limitar tamanho;
- sanitizar formatos perigosos.

## 16.2 Schemas

- validar input antes da execução;
- rejeitar campos extras quando risk médio/alto;
- normalizar enums;
- impor limites de tamanho;
- validar output;
- falhar fechado quando output não cumprir contrato crítico.

## 16.3 Secrets

- apenas Vault/connection resolver acessa;
- segredo é injetado no adapter, não no modelo;
- Tool Invocation registra `connection_id`, nunca token;
- logs usam redaction;
- checkpoint não recebe segredo.

## 16.4 Tenant isolation

Gateway deriva company do Work Run/contexto confiável.

Nunca aceita `company_id` da chamada da LLM como autoridade.

## 16.5 Approval e idempotência

Tool de escrita não executa se:

- approval exigida está ausente/expirada;
- effect não foi reservado;
- conexão não pertence ao tenant;
- idempotency key está em estado desconhecido;
- budget foi excedido.

---

# 17. Custo, quotas e limites

## 17.1 Classes de custo

- gratuito interno;
- computação da plataforma;
- chamada de provider paga pela plataforma;
- chamada usando conta do tenant;
- operação de portal/browser;
- LLM/subagente;
- artifact futuro.

## 17.2 Atribuição

Todo custo deve ser associado a:

- company;
- Work Run;
- Skill Release;
- Tool Release;
- capability;
- provider.

## 17.3 Budget

Antes de expor/executar tool:

- verificar limite da Skill;
- limite do Work Run;
- entitlement;
- plano/créditos;
- limite diário/mensal;
- custo estimado.

## 17.4 Comportamento

- baixo custo dentro do plano: executar;
- custo relevante: mostrar previsão conforme policy;
- saldo insuficiente: explicar e oferecer alternativa;
- nunca consumir silenciosamente acima do budget.

---

# 18. Admin operacional mínimo

Não esperar a SPEC-061 para administrar o sistema.

## 18.1 Página Skills

Exibir:

- Skill;
- categoria;
- owner;
- release publicada;
- status;
- Outcomes;
- capabilities;
- Capability Pack;
- tools;
- risco;
- custo médio;
- uso;
- taxa de sucesso;
- última validação;
- tenants/Agents vinculados.

Ações:

- criar draft;
- validar;
- aprovar;
- publicar;
- deprecar;
- rollback;
- desabilitar emergencialmente;
- abrir manifest/diff;
- executar eval;
- visualizar runs.

## 18.2 Página Tools

Exibir:

- Tool Definition;
- release;
- implementação;
- provider;
- capability;
- risco;
- side effect;
- conexão;
- health;
- latência;
- custo;
- erro;
- Skills consumidoras.

Ações:

- homologar release;
- testar em sandbox controlado;
- publicar;
- desativar;
- rollback;
- inspecionar schema;
- inspecionar egress/env sem revelar segredo.

## 18.3 Capability Packs

Exibir composição, versões, Skills e uso.

## 18.4 MCP

Exibir:

- servers;
- status;
- transport;
- tools descobertas;
- tools homologadas;
- diff de descoberta;
- env/scopes declarados;
- health;
- tenants conectados.

Não exibir tokens.

## 18.5 UX humana

Exemplo correto:

> “A Skill de pesquisa está indisponível porque o provider de busca não está configurado.”

Evitar:

> `CapabilityResolver provider_unavailable tavily`.

Detalhes técnicos ficam em expansão avançada.

---

# 19. UX tenant-facing mínima

Quando uma Skill precisar de conexão:

- mostrar nome humano;
- explicar benefício;
- indicar quem precisa conectar;
- link para Conexões;
- permitir alternativa sem a conexão quando houver;
- não expor provider internamente sem necessidade.

Quando tool estiver bloqueada:

- explicar em linguagem humana;
- diferenciar falta de permissão, conexão, approval, saldo ou indisponibilidade;
- não sugerir colar token no chat.

A corretora pode ver:

- Skills disponíveis;
- Skills usadas por seus Auxiliares;
- conexões necessárias;
- uso e resultado.

Não pode ver:

- manifest proprietário integral de Skills globais;
- prompt interno completo;
- tool schemas sensíveis;
- regras de outro tenant;
- segredos;
- corpus global.

---

# 20. APIs mínimas

## Admin

```text
GET    /api/admin/skills
POST   /api/admin/skills
GET    /api/admin/skills/:id
POST   /api/admin/skills/:id/releases
POST   /api/admin/skill-releases/:id/validate
POST   /api/admin/skill-releases/:id/approve
POST   /api/admin/skill-releases/:id/publish
POST   /api/admin/skill-releases/:id/deprecate
POST   /api/admin/skills/:id/rollback
GET    /api/admin/tools
GET    /api/admin/tools/:id
POST   /api/admin/tool-releases/:id/validate
POST   /api/admin/tool-releases/:id/publish
POST   /api/admin/tools/:id/disable
GET    /api/admin/capability-packs
GET    /api/admin/mcp/discovery-diffs
```

## Tenant/runtime

```text
GET  /api/skills/available
GET  /api/skills/:key/status
GET  /api/connections/requirements
GET  /api/work-runs/:id/skills-tools
```

Execução de tool nunca deve ser endpoint público genérico que aceita qualquer tool name sem contexto.

O Gateway é invocado pelo runtime autenticado/Work Run.

---

# 21. Autoria, publicação e rollback

## 21.1 Plataforma

Skills e tools platform-owned podem ser authoradas em arquivos versionados do repositório e publicadas no Supabase.

Regra:

- Git contém fonte revisável, seeds e evals;
- Supabase contém catálogo ativo e releases imutáveis;
- hash deve coincidir;
- runtime executa release publicada do Supabase;
- publicação registra commit de origem.

## 21.2 Tenant skills

O modelo de autoria tenant será aprofundado posteriormente.

Esta SPEC pode suportar o schema, mas não deve liberar criação irrestrita de código/tool por tenant.

Tenant pode inicialmente:

- configurar parâmetros permitidos;
- habilitar/desabilitar Skill autorizada;
- usar Skill por Auxiliar;
- não alterar capabilities nem instruções de segurança.

## 21.3 Rollback

- selecionar release anterior publicada;
- novos runs usam anterior;
- runs existentes continuam pinados;
- registrar motivo e autor;
- não deletar release defeituosa;
- desabilitação emergencial é permitida.

---

# 22. Evals e quality gates

## 22.1 Por Skill

Cada Skill publicada possui:

- casos positivos;
- anti-casos;
- inputs incompletos;
- tool selection correta;
- resposta sem tool quando não necessária;
- conexão ausente;
- capability negada;
- approval;
- budget excedido;
- provider indisponível;
- output schema;
- segurança/prompt injection;
- tenant isolation.

## 22.2 Por Tool

- input válido;
- input inválido;
- campos extras;
- timeout;
- retry;
- output inválido;
- segredo redigido;
- provider erro;
- health;
- idempotência;
- approval;
- egress/sandbox;
- cancelamento.

## 22.3 Skill selection

Testar:

- escolha correta;
- não escolher Skill incompatível;
- não expor tools proibidas;
- tool count dentro do limite;
- Atendimento sem arsenal do Core;
- Subagente sem escalada;
- fallback correto.

## 22.4 Métricas

- taxa de seleção correta;
- taxa de sucesso;
- tool calls por run;
- tool calls desnecessárias;
- custo por Outcome;
- latência;
- aprovação solicitada corretamente;
- policy denials;
- conexão ausente;
- fallback;
- satisfação/resultado quando disponível.

A SPEC-062 ampliará os evals, mas esta SPEC não pode publicar Skill sem testes próprios.

---

# 23. Broker Outcome Regression Pack

## 23.1 Pergunta simples de seguros

- Skill correta ou generic governed mode;
- conhecimento usado;
- nenhuma web/tool desnecessária;
- nenhuma confirmação de cobertura sem evidência.

## 23.2 Documento

- upload privado;
- Skill de análise selecionada;
- Document Extract;
- resumo útil;
- provenance;
- tenant B não acessa.

## 23.3 Pesquisa atual

- Skill de pesquisa;
- web tool correta;
- fontes e datas;
- sem tool de escrita;
- custo registrado.

## 23.4 CSV

- Skill de análise;
- cálculos coerentes;
- sem invenção;
- output estruturado.

## 23.5 InfoCap

- Resulta usa somente conexão Resulta;
- AutoFleet usa somente sua conexão;
- conexão ausente gera orientação;
- apólice correta;
- evidence/provenance;
- sem vazamento.

## 23.6 Atendimento

- somente Skills permitidas;
- sem web aberta;
- sem Admin tools;
- corredor e handoff preservados.

## 23.7 Auxiliar

- somente Skills do contrato;
- somente tools do pack;
- Work Run registra Skill/tool;
- nenhuma conexão de outro tenant.

## 23.8 Subagente

- subset de capabilities;
- budget;
- timeout;
- resultado retorna ao pai;
- zero privilégio adicional.

## 23.9 Portal

- Portal Skill migrada;
- Portal Worker preservado;
- journey homologada;
- 2FA/CAPTCHA gera intervenção;
- evidence privada;
- idempotência.

## 23.10 Authority

- prompt mencionando tool não autorizada não libera;
- tool desabilitada não executa;
- entitlement bloqueado não executa;
- connection errada não executa;
- release depreciada não entra em novo run.

---

# 24. Plano de migração do legado

## 24.1 Inventário

Antes de editar:

- tools nativas anexadas no Graph;
- `tools_config`;
- `agent_http_tools`;
- `mcp_servers`;
- `agent_mcp_connections`;
- `agent_mcp_tools`;
- `agent_delegations`;
- Portal Skills hardcoded;
- capabilities/bindings/entitlements;
- connectors/connections;
- prompts que mencionam tools.

## 24.2 Mapeamento

Para cada ferramenta existente:

```text
legacy source
→ tool_key canônica
→ capability_key
→ Tool Release
→ Skill(s) consumidoras
→ connection/provider
→ risk/approval
```

## 24.3 Compatibilidade temporária

Durante a mesma execução:

- Gateway pode ler config legada via adapter;
- Graph compara toolset antigo e novo;
- logs mostram diferenças;
- não duplicar execução;
- nenhum side effect em shadow.

## 24.4 Corte

Ao final:

- `AUTHORITY_STRICT_MODE=on`;
- Graph usa Skill Resolver/Tool Gateway;
- prompt mention não autoriza;
- HTTP/MCP/native/delegation passam pelo Gateway;
- Portal Skill hardcoded não é autoridade;
- escritores/admin antigos são bloqueados ou redirecionados;
- compatibilidade permanece somente como adapter de dados quando necessária;
- feature nova fica ativa.

## 24.5 Não apagar histórico

- rows antigas preservadas;
- releases preservadas;
- configs antigas marcadas/mapeadas;
- remoção física somente em SPEC/cleanup posterior com evidência.

---

# 25. BLOCO A — Registry canônico e migração do legado

## Objetivo

Criar o modelo de dados, manifestos, validadores, seeds e mapeamento completo do que já existe.

## Entregas

- migrations;
- schemas Pydantic/TypeScript;
- repositories;
- Skill Manifest validator;
- Tool Manifest validator;
- tabelas e RLS;
- seeds das tools/capabilities existentes;
- seeds dos Capability Packs;
- seeds das Skills iniciais;
- migration map do legado;
- Portal Skills convertidas em draft/release;
- source hash/commit;
- Admin read-only inicial.

## Gate

- schema reproduzível;
- manifests válidos;
- nenhuma release publicada com segredo;
- todas as tools existentes mapeadas ou justificadas;
- nenhuma duplicidade de `tool_key`/`skill_key`;
- Skill release imutável;
- RLS/tenant tests verdes;
- rollback documentado.

---

# 26. BLOCO B — Tool Gateway e integração runtime

## Objetivo

Tornar o Gateway o único caminho autorizado de seleção e execução.

## Entregas

- ToolGatewayService;
- SkillResolver;
- CapabilityPackResolver;
- ToolRuntimeContext;
- wrappers LangChain dinâmicos;
- integração com Graph e Smith Worker;
- integração Work Run;
- tool invocation logging;
- cost/budget;
- approval/effect;
- native/http/mcp/portal/delegation adapters;
- output envelope;
- prompt injection defenses;
- progress events;
- connection requirements.

## Gate

- seleção correta;
- tool count dentro do limite;
- revalidação por chamada;
- zero side effect sem approval/effect;
- zero secret em logs;
- HTTP/MCP hardening verde;
- Work Run tracing completo;
- fallback correto;
- sem execução duplicada;
- performance aceitável.

---

# 27. BLOCO C — Biblioteca inicial, UX, cutover e lançamento

## Objetivo

Publicar as Skills reais, ativar o novo caminho e comprovar valor no dashboard.

## Entregas

- Skills 14.1–14.8 publicadas conforme disponibilidade real;
- packs publicados;
- Admin Skills/Tools/Pack/MCP funcional;
- tenant connection guidance;
- chat usando Skill Resolver;
- Work Run cards mostrando Skill/tool em linguagem humana;
- Authority Strict ON;
- caminhos legados sem autoridade;
- canário Amandus → Resulta → AutoFleet;
- deploy;
- relatório final.

## Gate

- Broker Outcome Regression Pack verde;
- Core usa Skills reais;
- Atendimento restrito;
- Auxiliar restrito;
- Portal preservado;
- Resulta/AutoFleet isoladas;
- Admin consegue publicar/rollback;
- uso/custo registrado;
- versão ativa em produção;
- nenhuma flag deixando o recurso permanentemente desligado.

---

# 28. Performance e SLOs iniciais

Metas iniciais, excluindo latência do provider externo:

- resolução de Skill em cache: p95 ≤ 250 ms;
- resolução de Capability Pack: p95 ≤ 150 ms;
- overhead de autorização do Gateway: p95 ≤ 200 ms;
- catálogo cacheado por release hash;
- invalidação após publish/disable;
- no máximo 12 tools expostas por model call por padrão;
- output externo limitado conforme Tool Release;
- health cache curto com fail-closed para risco alto;
- nenhuma query N+1 por toolset.

Não sacrificar autorização por latência.

---

# 29. Observabilidade

Registrar:

- Skill selecionada;
- candidatas e motivo resumido;
- release;
- pack;
- tools expostas;
- tools chamadas;
- denials;
- missing connection;
- approval;
- custo;
- latência;
- output validation;
- fallback;
- error class;
- tenant/run/step/trace.

Não registrar prompt integral ou dados sensíveis sem necessidade.

Dashboards mínimos:

- uso por Skill;
- sucesso por Skill;
- custo por Skill/tool/provider/tenant;
- top denials;
- top missing connections;
- tool errors;
- release regression;
- unused Skills/tools;
- tool count por chamada.

---

# 30. Arquivos e áreas prováveis

O executor confirma no código real.

## Backend

- `backend/app/agents/graph.py`;
- `backend/app/agents/capability_resolver.py`;
- `backend/app/services/tool_authority.py`;
- novo módulo `backend/app/services/skill_registry/`;
- novo módulo `backend/app/services/tool_gateway/`;
- `backend/app/agents/tools/http_request.py`;
- `backend/app/services/mcp_gateway_service.py`;
- `backend/app/agents/tools/mcp_factory.py`;
- `backend/app/agents/tools/subagent_tool.py`;
- wrappers native tools;
- Smith Worker/Work Run services da SPEC-055;
- usage/cost/tracing.

## Portal

- `lib/attendance/portal-skills.ts`;
- `lib/attendance/portal-skill-factory.ts`;
- `lib/attendance/portal-skill-runner.ts`;
- Admin Portal Browser Skills;
- Portal Worker bridge.

## Banco

- `backend/supabase/migrations/`;
- `skills`/releases/bindings;
- capability packs;
- tool definitions/releases;
- requirements;
- tool invocations;
- links em Work Runs;
- RLS/indexes/functions.

## Web/Admin

- páginas Admin Skills/Tools/Packs/MCP;
- APIs Admin;
- status de conexão tenant;
- Work Run details;
- UI de erro humano.

## Seeds/evals

Sugestão:

```text
backend/app/skills/<skill_key>/manifest.yaml
backend/app/skills/<skill_key>/instructions.md
backend/app/skills/<skill_key>/evals.yaml
backend/app/tools/<tool_key>/manifest.yaml
```

Esses arquivos são fonte revisável de seeds platform-owned; Supabase continua catálogo operacional ativo.

---

# 31. Formato obrigatório de migrations

Usar cabeçalho da SPEC-054:

```sql
-- SPEC-056 — <nome>
-- PURPOSE: <objetivo>
-- MODE: EXPAND-ONLY | CONTRACT | SECURITY-CLOSURE
-- PRECONDITIONS: <condições>
-- APPLY: <como aplicar>
-- VERIFY: <queries>
-- ROLLBACK: <passos>
-- DATA IMPACT: NONE | BACKFILL CONTROLADO
-- LOCK RISK: LOW | MEDIUM | HIGH
```

Preferir expand-and-contract.

Não alterar release publicada.

---

# 32. Testes obrigatórios

## Unitários

- manifest schemas;
- semver;
- content hash;
- release immutability;
- Skill selection;
- anti-triggers;
- Capability Pack;
- tool filtering;
- budget;
- approval merge;
- trust levels;
- output envelope;
- redaction.

## Integração

- Skill → capability → entitlement → connection → tool;
- Work Run → Skill Release;
- native tool;
- HTTP tool;
- MCP tool;
- Portal tool;
- delegation;
- provider unavailable;
- connection expired;
- approval;
- effect/idempotency;
- cost;
- rollback de release.

## Segurança

- prompt mention não libera tool;
- tool description maliciosa não altera policy;
- tenant A não usa conexão B;
- Atendimento não usa Core tools;
- Subagente não escala;
- secret não chega ao modelo;
- output externo não injeta instrução;
- HTTP SSRF bloqueado;
- MCP env mínimo;
- schema inválido falha.

## Produção

- Amandus;
- Resulta;
- AutoFleet;
- fluxos do Broker Outcome Pack;
- restart do worker;
- cache invalidation após publish/disable;
- rollback de Skill/tool.

---

# 33. Definition of Done

A SPEC somente está concluída quando:

1. Skill Registry canônico existe;
2. Tool Registry canônico existe;
3. Capability Packs existem;
4. releases publicadas são imutáveis;
5. Tool Gateway está ativo;
6. Graph/Worker usam seleção dinâmica;
7. Authority Strict está ON;
8. prompt mention não autoriza;
9. native/HTTP/MCP/Portal/delegation passam pelo Gateway;
10. capabilities/scopes/entitlements são aplicados;
11. connections são validadas;
12. secrets ficam no Vault;
13. tools são revalidadas por chamada;
14. Skill/tool releases estão ligadas ao Work Run;
15. tool invocations registram custo/latência/status;
16. side effects usam approval/idempotência;
17. Portal Skills foram migradas sem perder runner especializado;
18. Skills iniciais utilizáveis estão publicadas;
19. Admin mínimo funciona;
20. tenant recebe orientação humana de conexão/erro;
21. evals estão verdes;
22. Broker Outcome Pack está verde;
23. Amandus, Resulta e AutoFleet estão isoladas e funcionais;
24. nenhum catálogo/gateway/runtime paralelo foi criado;
25. feature está ativa em produção;
26. relatório final está publicado.

---

# 34. Relatório final obrigatório

Criar:

```text
docs/canon/reports/SPEC-056-execution-report-<YYYY-MM-DD>.md
```

Conteúdo:

1. commit inicial/final;
2. branch/PR;
3. migrations;
4. tabelas/constraints/RLS;
5. Skills criadas;
6. Tool Definitions/Releases;
7. Capability Packs;
8. legado migrado;
9. paths desativados;
10. testes;
11. evals;
12. Broker Outcome Pack;
13. canários;
14. métricas;
15. custo/latência;
16. segurança;
17. rollback;
18. pendências legítimas para SPEC-057/058/060;
19. zero perda de dados;
20. zero runtime/catalog/gateway paralelo;
21. status PASS, PASS WITH ACCEPTED EXCEPTION ou FAIL.

Sem segredos ou dados pessoais.

---

# 35. Condições de parada obrigatória

Parar e solicitar decisão do CEO/Founder apenas se:

1. SPEC-054/055 bloqueadora não estiver segura para side effects;
2. migration exigir apagar dados;
3. existir conflito com SPEC-052–055;
4. Tool Gateway exigir substituir Smith;
5. conexão atual não puder ser migrada sem perda;
6. Portal Skill real tiver comportamento comercial ambíguo;
7. Skill inicial exigir compromisso jurídico/comercial não definido;
8. provider exigir custo não aprovado ou contrato externo;
9. Resulta/AutoFleet perderem acesso legítimo;
10. ocorrer risco real de vazamento cross-tenant;
11. for necessário expor segredo ao modelo;
12. cutover exigir indisponibilidade relevante sem rollback.

Falhas comuns de implementação/teste devem ser corrigidas e a execução continua.

---

# 36. Decisões congeladas

1. Capability Registry existente é preservado.
2. Skill Registry complementa capabilities.
3. Tool Gateway único governa todas as tools.
4. Work Run governa execução.
5. Vault governa secrets.
6. Skills e Tool Releases são versionadas e imutáveis.
7. Tools são selecionadas dinamicamente.
8. Máximo padrão de 12 tools por model call.
9. Prompt não é autoridade.
10. HTTP Router perde autorização por menção.
11. MCP discovery não ativa tools automaticamente.
12. Portal Skills migram para o Registry único.
13. Portal Worker permanece especializado.
14. Subagentes recebem subset mínimo.
15. API/conector vem antes de browser/computer use.
16. A policy mais restritiva vence.
17. Tools platform-owned podem usar credencial AutoBrokers com custo atribuído ao tenant.
18. Tools tenant-owned usam conexão do tenant.
19. Admin mínimo entra nesta SPEC.
20. A entrega é de lançamento, não beta permanente.

---

# 37. Próxima SPEC subordinada

Após execução e aprovação desta SPEC:

```text
SPEC-057 — AutoBrokers Artifact Hub & Report Studio
```

Ela deverá usar Skills, Tool Gateway e Work Runs para criar uma camada única de resultados profissionais:

- artifact como objeto de primeira classe;
- PDF;
- relatório web;
- XLSX/CSV;
- gráficos;
- apresentações;
- documentos;
- dossiês;
- templates visuais;
- lineage;
- versões;
- MinIO;
- permissões;
- links compartilháveis/revogáveis;
- delivery;
- Report Studio integrado ao chat e Auxiliares.

A SPEC-057 não criará outro cérebro, worker, Skill Registry ou Tool Gateway.