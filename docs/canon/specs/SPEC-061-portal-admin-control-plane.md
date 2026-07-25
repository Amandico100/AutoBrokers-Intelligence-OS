# SPEC-061 — AutoBrokers Portal Admin Control Plane

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANÔNICA E AUTORIZADA PARA EXECUÇÃO — aprovada pelo Founder em 24/07/2026  
**Autoridade superior:** `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`, `SPEC-053-autobrokers-work-os-core-harness.md`, `SPEC-054-foundation-hardening-schema-governance.md`, `SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`, `SPEC-056-skill-registry-tool-gateway.md`, `SPEC-057-artifact-hub-report-studio.md`, `SPEC-058-auxiliary-routine-factory.md`, `SPEC-059-briefing-proatividade-garimpo-v3.md` e `SPEC-060-research-intelligence.md`  
**Runtime preservado:** Smith + LangGraph/LangChain + FastAPI + Supabase/Postgres + Redis + Qdrant + MinIO + Next.js  
**Nome oficial do agente central:** **AutoBrokers**  
**Escopo:** consolidar o Portal Admin Global como Control Plane operacional da plataforma, reunindo corretoras, saúde, Work Runs, approvals, Agents, Skills, Tools, MCPs, conexões, Vault, Portais, Artifacts, Auxiliares, Rotinas, Intelligence Fabric, Briefings, Garimpo, Research Intelligence, Conhecimento, Memórias, custos, segurança, evals, releases, rollouts, auditoria e operação de suporte em uma única experiência clara, segura e acionável.  
**Natureza desta SPEC:** autoriza migrations mínimas, autenticação e RBAC administrativos, backend/BFF, APIs, read models, comandos, auditoria, UI/UX, design system, migração de rotas, redirects, visual acceptance, deploy, cutover e ativação em produção.  
**Dependência de execução:** as SPECs 054–060 devem estar implementadas ou ser executadas no mesmo programa, na ordem canônica.

---

# 0. Comando direto ao executor — Fable, Opus, Codex ou equivalente

Você está autorizado a **implementar integralmente esta SPEC em linha reta**.

Esta não é uma SPEC para:

- criar apenas uma nova sidebar;
- reorganizar links sem consolidar as autoridades reais;
- transformar tabelas do Supabase em telas genéricas;
- criar um dashboard de cards sem decisões acionáveis;
- manter a segurança baseada em esconder botões no frontend;
- usar `localStorage` como autoridade de autenticação ou papel;
- misturar novamente Admin Global com Dashboard da Corretora;
- expor prompts, secrets, Vault refs, SessionRefs ou dados sensíveis por conveniência;
- criar outro runtime, scheduler, Registry, Artifact Hub, Intelligence Fabric ou Research Orchestrator;
- deixar páginas antigas concorrendo indefinidamente com a nova arquitetura;
- terminar com telas bonitas e comandos sem funcionar;
- deixar o Control Plane permanentemente atrás de feature flag.

Ao final da mesma iniciativa:

- `/admin` deverá ser exclusivamente o Control Plane Global da equipe AutoBrokers;
- donos, gestores e operadores de corretoras deverão usar `/dashboard`, não o Admin Global;
- autenticação, papel e permissions deverão ser validados server-side;
- o Founder deverá enxergar em poucos segundos o que exige atenção;
- o Admin deverá mostrar quais corretoras estão saudáveis, degradadas, bloqueadas ou não prontas;
- Work Runs, approvals, incidentes, conexões e rollouts deverão ser acionáveis;
- toda ação administrativa deverá possuir preview, autorização, idempotência e audit trail proporcional ao risco;
- o Cockpit da Corretora deverá consolidar operação, saúde, custos, conexões, Agents, Auxiliares, conhecimento e qualidade;
- as páginas das SPECs 052–060 deverão ser administráveis sem acessar tabelas brutas;
- erros deverão aparecer em linguagem humana, com detalhes técnicos em camada avançada;
- Visual Acceptance Pack deverá ser aprovado pelo Founder;
- desktop e mobile deverão funcionar;
- rotas históricas deverão redirecionar sem quebrar bookmarks relevantes;
- Amandus, Resulta e AutoFleet deverão passar pelos critérios de lançamento;
- o caminho canônico deverá permanecer ativo em produção ao encerrar o programa.

## 0.1 Doutrina de lançamento

```text
Ver o que importa.
Entender por que importa.
Conhecer o impacto e o escopo.
Executar pelo caminho canônico.
Confirmar o resultado.
Ter rollback.
Manter evidência e auditoria.
```

Testes, canários e gates pertencem à mesma entrega de lançamento. Eles não autorizam uma longa sequência de versões provisórias.

Feature flags são permitidas apenas para:

- rollback;
- canário;
- corte controlado;
- mitigação de incidente.

A entrega não termina enquanto a experiência canônica estiver permanentemente desligada.

## 0.2 Número de blocos

A execução deverá ocorrer em **três blocos macro**, o menor número compatível com segurança, migração e lançamento:

1. **Bloco A — Control Plane Foundation, autenticação, RBAC, shell, read models e Admin Inbox**;
2. **Bloco B — Cockpits, hubs operacionais, comandos e administração das SPECs 052–060**;
3. **Bloco C — Visual Acceptance, migração de rotas, cutover, canários e produção**.

Com os gates verdes, avançar automaticamente.

## 0.3 Saída obrigatória

Ao final deverão existir e estar ativos:

- Portal Admin Global separado do Dashboard da Corretora;
- autenticação administrativa server-side;
- RBAC administrativo granular;
- permissions estáveis e testáveis;
- sessões de suporte tenant-scoped e temporárias;
- step-up para ações críticas;
- Admin Audit Trail append-only;
- Admin Command Gateway;
- Control Plane BFF/read models;
- navegação final consolidada;
- busca global governada;
- Admin Inbox priorizada;
- Home executiva operacional;
- Cockpit 360º por corretora;
- central de Work Runs;
- central de approvals;
- gestão de Agents e saúde;
- gestão de Skills, Tools, MCPs e Capability Packs;
- gestão de Auxiliares e Rotinas;
- gestão de Artifacts, templates e entregas;
- gestão do Intelligence Fabric, Briefings, Garimpo e Demand Radar;
- gestão de Research providers, fontes, monitors e custos;
- gestão de Conhecimento Global, tenant e curadoria;
- gestão de conexões, WhatsApp, sistemas, Portais e Vault health;
- FinOps, billing, créditos, MRR e custos por domínio;
- segurança, incidentes, evals, releases, rollouts e rollback;
- estados de loading, vazio, erro, acesso negado, stale e degradado;
- linguagem humana em todas as páginas principais;
- detalhes técnicos em painel avançado;
- responsividade e acessibilidade;
- redirects das rotas históricas;
- remoção de autoridades visuais concorrentes;
- Visual Acceptance Pack aprovado;
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
10. ler SPEC-059 e relatório final;
11. ler SPEC-060 e relatório final;
12. ler `UX-001-navegacao.md`;
13. ler `DS-001-design-brief.md`;
14. ler `SPEC-036-auditoria-e-plano-portal-admin.md` apenas como auditoria histórica subordinada;
15. ler ADR-001, ADR-002 e ADR-003;
16. inventariar todas as páginas em `app/admin/`;
17. inventariar todas as rotas em `app/api/admin/`;
18. inventariar componentes, stores e helpers em `components/admin/`, `lib/admin/`, `hooks/` e backend admin;
19. confirmar schema vivo em modo read-only;
20. confirmar papéis e sessões reais;
21. confirmar rotas usadas por Amandus, Resulta e AutoFleet;
22. revisar o material visual `PORTAL ADMIN.zip` como evidência histórica, não como autoridade superior;
23. confirmar relatórios de execução das SPECs 054–060.

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
→ SPECs posteriores subordinadas
→ ADRs e documentos históricos quando não conflitarem
→ código atual como estado de implementação
```

Em conflito, não criar outra arquitetura.

---

# 2. Visão de produto

O Portal Admin não é um conjunto de páginas para visualizar banco de dados.

Ele é o **Control Plane do AutoBrokers.ai**.

Seu objetivo é permitir que o Founder e a equipe autorizada:

- compreendam a saúde da plataforma;
- saibam o que exige decisão;
- administrem todas as corretoras;
- ativem e suportem clientes;
- publiquem e revertam inteligência;
- acompanhem trabalho real;
- controlem risco, custo e qualidade;
- corrijam bloqueios;
- comprovem o que aconteceu;
- façam tudo isso sem SQL, sem abrir cinco sistemas e sem entender detalhes internos do Smith.

A promessa é:

> **O Portal Admin mostra o estado real do ecossistema AutoBrokers, prioriza o que precisa de ação e permite administrar a plataforma com segurança, clareza e autonomia.**

## 2.1 Resultado para o Founder

Ao abrir o Admin, o Founder deverá responder em menos de um minuto:

1. A plataforma está saudável?
2. Alguma corretora está bloqueada?
3. O que precisa da minha decisão?
4. Há trabalho falhando ou aguardando humano?
5. Alguma conexão crítica expirou?
6. Algum rollout ou release apresentou regressão?
7. Quanto está custando operar?
8. Quais Auxiliares, Skills e ferramentas estão gerando valor?
9. O que os corretores estão pedindo?
10. Qual ação devo tomar agora?

## 2.2 Resultado para a operação

A equipe operacional deverá:

- localizar a corretora;
- abrir seu Cockpit;
- entender o problema;
- ver dependências afetadas;
- executar a correção autorizada;
- acompanhar o Work Run;
- confirmar a recuperação;
- deixar tudo auditado.

## 2.3 Resultado para suporte

O suporte deverá:

- acessar somente o necessário;
- visualizar a experiência da corretora sem impersonação invisível;
- usar sessão temporária com motivo;
- não visualizar secrets;
- não alterar produção sem permission e confirmação;
- registrar toda intervenção.

## 2.4 O que o Control Plane não é

Não é:

- CRM de vendas;
- painel genérico de analytics;
- Supabase Studio com outra aparência;
- editor livre de prompts de produção;
- substituto do Dashboard da Corretora;
- local de execução direta de scripts arbitrários;
- novo runtime;
- novo banco soberano;
- nova fonte de verdade para objetos já governados pelas SPECs anteriores.

---

# 3. Estado atual auditado

## 3.1 Peças reais que devem ser preservadas

O repositório já possui superfícies e lógicas valiosas:

- `app/admin/layout.tsx`;
- dashboard administrativo;
- Companies e Cockpit da Corretora;
- página de ativação/readiness;
- Central de Agentes;
- Acionamentos;
- Espelho/Auditor;
- Insights/Garimpo histórico;
- Conversas e logs;
- FinOps, billing e costs;
- Portal Browser;
- Canais de seguradora;
- Auxiliares globais;
- Rotinas prontas;
- Blueprint Center;
- Prompt Efetivo;
- Knowledge Base;
- documentos;
- equipe e usuários;
- termos e configurações;
- helpers de rollout e rollback;
- stores de readiness, Auxiliares e blueprints;
- componentes de configuração de Agents;
- APIs e rotas server-side existentes.

Essas peças não devem ser descartadas sem inventário e migração.

## 3.2 Problemas atuais confirmados

### 3.2.1 `/admin` mistura duas superfícies

O layout atual atende:

- `master`;
- `company_admin`;
- e redireciona `member`.

Isso mistura Control Plane Global e gestão da própria corretora.

Decisão:

```text
/admin
= equipe AutoBrokers autorizada

/dashboard
= corretora, owner, gestor e equipe tenant
```

As páginas tenant hoje em `/admin/team`, `/admin/agent`, `/admin/documents`, `/admin/billing` e equivalentes deverão migrar ou redirecionar para rotas do Dashboard.

### 3.2.2 Sessão no navegador ainda influencia autoridade

O estado atual utiliza `smith_admin_session` no `localStorage` para nome, papel e companyId, combinado com cookie/API.

Isso pode continuar apenas como cache de apresentação durante a migração, nunca como autoridade.

Depois do cutover:

- sessão válida vem de cookie HttpOnly/server;
- papel vem do servidor;
- permission vem do servidor;
- tenant scope vem do servidor;
- frontend apenas reflete a decisão;
- alteração de `localStorage` não concede acesso.

### 3.2.3 Proteção de rota é parcialmente client-side

O layout atual redireciona rotas depois de carregar papel.

Isso não é suficiente.

Toda rota, API e comando deverá validar server-side.

### 3.2.4 Navegação cresceu por adição

O menu atual possui muitos destinos de primeiro nível e submenus com sobreposição conceitual.

A SPEC-036 já iniciou consolidação, mas as SPECs 052–060 adicionaram novos domínios que exigem nova arquitetura final.

### 3.2.5 Home atual não é Control Plane

O dashboard atual mostra:

- MRR;
- empresas;
- usuários;
- pendências;
- logs;
- erros.

Esses dados são úteis, mas não respondem qual problema precisa de decisão agora.

### 3.2.6 Central de Agentes usa heurística no cliente

A tela atual infere saúde com base em tempo desde `last_run` e thresholds hardcoded.

Depois do cutover:

- health vem de contrato canônico;
- threshold é server-side/versionado;
- estado mostra fonte e freshness;
- polling arbitrário não é autoridade.

### 3.2.7 Cockpit atual é parcial

A tela atual reúne conversas, scorecards, Garimpo histórico, documentos e plano.

Ela é boa fundação visual, mas precisa consumir:

- Work Runs;
- approvals;
- connections;
- Auxiliares;
- Rotinas;
- Artifacts;
- Findings;
- Briefings;
- Research;
- custos;
- readiness;
- incidentes;
- releases ativas.

### 3.2.8 Configuração de Agent é técnica e extensa

O material visual e o código atual apresentam uma modal com muitas abas:

- Identidade;
- Modelo;
- Personalidade;
- Memória;
- Segurança;
- HTTP Tools;
- MCP;
- Commerce;
- Widget;
- WhatsApp;
- Especialistas.

Essa estrutura preserva funções úteis, mas é inadequada como arquitetura final:

- mistura produto e infraestrutura;
- expõe conceitos técnicos;
- concentra configuração demais;
- aumenta risco de alteração acidental;
- não mostra release, diff, eval ou impacto.

Decisão:

- substituir a modal gigante por páginas em camadas;
- separar identidade, comportamento, capacidades, conexões, especialistas, releases e diagnóstico;
- usar preview/diff antes de aplicar;
- manter detalhes técnicos em modo avançado.

### 3.2.9 APIs e stores estão fragmentados

Existem rotas e stores úteis, mas cada módulo implementa parte do acesso, erro, auth, loading, filtro e ação.

A SPEC-061 cria uma camada de Control Plane BFF e um Admin Command Gateway, sem substituir as autoridades de domínio.

---

# 4. Leis centrais desta SPEC

1. **O Portal Admin é Control Plane, não runtime.**
2. **O Portal Admin não cria fontes de verdade concorrentes.**
3. **Toda leitura aponta para a autoridade do domínio.**
4. **Toda escrita passa por comando governado.**
5. **Frontend nunca é autoridade de permission.**
6. **`localStorage` nunca concede papel ou acesso.**
7. **Admin Global e Dashboard da Corretora são superfícies separadas.**
8. **Nenhum secret é exibido.**
9. **Status técnico deve possuir tradução humana.**
10. **Detalhe técnico existe, mas não domina a experiência.**
11. **Toda ação destrutiva mostra impacto, escopo e rollback.**
12. **Toda ação administrativa relevante é auditada.**
13. **Acesso de suporte a tenant é temporário, explícito e rastreável.**
14. **Bulk action exige blast radius visível.**
15. **Stale data nunca aparece como estado atual sem aviso.**
16. **Ausência de dado não aparece como saúde verde.**
17. **Read model pode ser derivado; autoridade continua no domínio.**
18. **Não criar uma página nova para cada tabela.**
19. **Não criar um menu novo para cada feature.**
20. **A mesma ação não pode existir em vários lugares com contratos diferentes.**
21. **Mobile não é desktop comprimido.**
22. **Acessibilidade faz parte da Definition of Done.**
23. **Rollout e rollback são partes da operação normal.**
24. **Canário é gate da entrega, não produto beta permanente.**
25. **Todo erro acionável deve sugerir próximo passo.**
26. **Toda permissão possui chave estável e teste.**
27. **Toda ação externa usa Work OS/HITL quando aplicável.**
28. **Prompts protegidos, memória e evidências sensíveis obedecem least privilege.**
29. **A UI não acessa Supabase diretamente para comandos administrativos.**
30. **O Founder precisa conseguir administrar o sistema sem conhecer o código.**

---

# 5. Fronteiras do Control Plane

## 5.1 Control Plane BFF

Criar/consolidar uma camada server-only:

```text
lib/admin/control-plane/
```

Responsabilidades:

- autenticar;
- resolver permissions;
- aplicar tenant scope;
- compor read models;
- normalizar status;
- traduzir erros;
- aplicar redaction;
- emitir comandos;
- registrar audit;
- vincular trace/correlation;
- controlar cache/freshness;
- não implementar a lógica soberana dos domínios.

## 5.2 Admin Command Gateway

Criar/consolidar:

```text
lib/admin/control-plane/command-gateway.ts
```

ou equivalente server-side.

Toda escrita administrativa passa pelo gateway.

O Gateway:

1. autentica;
2. resolve permission;
3. valida target e tenant scope;
4. carrega versão atual;
5. calcula preview/diff;
6. classifica risco;
7. exige step-up/approval quando aplicável;
8. reserva idempotency key;
9. chama serviço canônico;
10. registra resultado;
11. emite audit event;
12. retorna receipt humano e técnico.

## 5.3 Autoridades preservadas

| Domínio | Autoridade |
|---|---|
| conhecimento/memória | SPEC-052 |
| execução | Work Runs da SPEC-055 |
| approvals | `approval_requests` evoluída |
| Skills e tools | SPEC-056 |
| Artifacts | SPEC-057 |
| Auxiliares e Rotinas | SPEC-058 |
| Signals/Findings/Recommendations | SPEC-059 |
| pesquisa | SPEC-060 |
| segredos | Vault |
| billing/custos | serviços e tabelas canônicas de uso |
| Control Plane UI/BFF | SPEC-061 |

## 5.4 O BFF não pode

- executar LLM diretamente;
- executar tool fora do Tool Gateway;
- atualizar domínio por SQL improvisado;
- revelar secret;
- inventar health;
- duplicar evento de domínio;
- virar scheduler;
- virar worker;
- armazenar cópia completa de dados tenant sem necessidade.

---

# 6. Separação definitiva de superfícies

## 6.1 Portal Admin Global

Rota:

```text
/admin
```

Usuários:

- Founder;
- equipe AutoBrokers autorizada;
- suporte;
- operação;
- financeiro;
- segurança;
- curadoria;
- release management;
- auditoria.

## 6.2 Dashboard da Corretora

Rota:

```text
/dashboard
```

Usuários:

- owner da corretora;
- admin da corretora;
- gestor;
- operador;
- membro.

## 6.3 Regra de migração

Rotas tenant hoje sob `/admin` deverão:

- ganhar rota equivalente em `/dashboard`;
- preservar parâmetros e links importantes;
- redirecionar com status apropriado;
- não duplicar a mesma página em dois lugares;
- manter telemetria de uso durante a transição;
- ser removidas depois do período de compatibilidade definido na execução.

## 6.4 “Ver como corretora”

Não implementar impersonação silenciosa.

Criar **Support Access Session**:

- tenant explícito;
- motivo obrigatório;
- duração limitada;
- read-only por padrão;
- banner persistente;
- actions bloqueadas ou reautorizadas;
- audit trail;
- encerramento manual;
- expiração automática.

---

# 7. Identidade, autenticação e sessão administrativa

## 7.1 Autoridade de sessão

A autoridade será server-side:

- cookie HttpOnly;
- secure em produção;
- SameSite apropriado;
- expiração;
- rotação;
- revogação;
- binding a usuário e session id;
- invalidada ao suspender usuário ou remover papel.

## 7.2 `localStorage`

Pode armazenar somente:

- preferência de sidebar;
- tema;
- filtros não sensíveis;
- densidade visual;
- última página.

Não pode armazenar como autoridade:

- papel;
- permission;
- company scope;
- isOwner;
- status de autenticação;
- token privilegiado.

## 7.3 Sessões

Criar visão e controle de:

- sessões ativas;
- dispositivo/browser;
- IP redigido quando necessário;
- último uso;
- expiração;
- revogação individual;
- revogação total;
- sessão de suporte;
- sessão break-glass.

## 7.4 Step-up authentication

Exigir autenticação recente para ações P3/P4:

- rollback global;
- ativar release para todos;
- alterar policy crítica;
- suspender tenant;
- mudar papel privilegiado;
- abrir sessão de suporte com escrita;
- rotacionar conexão crítica;
- invalidar conhecimento global publicado;
- alterar limites comerciais globais;
- encerrar incidentes críticos;
- alterar segurança.

O mecanismo deve usar a fundação de autenticação existente, sem criar provider paralelo.

## 7.5 CSRF e origem

Toda ação mutável deve validar:

- sessão;
- origem;
- CSRF quando aplicável;
- método HTTP;
- content type;
- idempotency key;
- permission;
- version/ETag.

---

# 8. RBAC administrativo

## 8.1 Papéis iniciais

```text
platform_owner
platform_admin
platform_operations
platform_support
platform_finance
platform_security
platform_curator
platform_release_manager
platform_auditor
platform_viewer
```

Um usuário pode possuir mais de um papel.

## 8.2 Compatibilidade

O papel histórico `master` será mapeado inicialmente para `platform_owner`.

Nenhum `company_admin` será convertido automaticamente em papel global.

## 8.3 Permissions estáveis

Exemplos:

```text
admin.overview.read
admin.inbox.read
admin.inbox.manage
companies.read
companies.manage
companies.suspend
companies.support_access
users.read
users.manage
work_runs.read
work_runs.retry
work_runs.cancel
approvals.read
approvals.decide
agents.read
agents.manage
skills.read
skills.publish
skills.rollback
tools.read
tools.manage
mcps.read
mcps.manage
connections.read
connections.manage
connections.rotate
artifacts.read
artifacts.revoke
auxiliaries.read
auxiliaries.publish
routines.read
routines.manage
intelligence.read
intelligence.manage
research.read
research.manage
knowledge.read
knowledge.curate
knowledge.publish
memory.metadata.read
memory.sensitive.read
finance.read
finance.manage
security.read
security.manage
releases.read
releases.rollout
releases.rollback
audit.read
legal.manage
system.manage
```

## 8.4 Regras

- permission é verificada no servidor;
- menu é derivado das permissions;
- API retorna 403 estável;
- esconder botão é conveniência, não segurança;
- nenhuma permission global é inferida de `company_id`;
- permission sensível pode exigir step-up;
- overrides possuem expiração e audit;
- role binding suspenso perde acesso imediatamente.

## 8.5 Segregação de funções

Quando aplicável:

- quem cria release não precisa ser quem publica;
- quem investiga incidente não precisa encerrar;
- financeiro não acessa conteúdo tenant sensível;
- curador não acessa secrets;
- suporte não altera billing;
- auditor é read-only;
- security não vê conteúdo de conversas sem justificativa.

---

# 9. Modelo de dados mínimo do Control Plane

Todas as migrations seguem APPLY/VERIFY/ROLLBACK da SPEC-054.

Não criar tabelas de cópia para cada módulo.

## 9.1 `platform_admin_role_bindings`

```text
id uuid PK
user_id uuid NOT NULL
role_key text NOT NULL
status text NOT NULL
starts_at timestamptz NOT NULL
expires_at timestamptz NULL
granted_by_user_id uuid NOT NULL
reason text NULL
created_at timestamptz NOT NULL
updated_at timestamptz NOT NULL
```

Unique ativo por `(user_id, role_key)`.

## 9.2 `platform_admin_permission_overrides`

Uso excepcional:

```text
id
user_id
permission_key
effect allow|deny
scope jsonb
starts_at
expires_at
reason
granted_by_user_id
created_at
```

Não usar overrides como substituto da matriz de papéis.

## 9.3 `admin_audit_events`

Append-only:

```text
id uuid PK
occurred_at timestamptz NOT NULL
actor_user_id uuid NOT NULL
actor_session_id uuid NULL
actor_roles text[] NOT NULL
permission_key text NULL
action_key text NOT NULL
risk_tier text NOT NULL
target_type text NOT NULL
target_id text NULL
company_id uuid NULL
support_session_id uuid NULL
command_id uuid NULL
idempotency_key text NULL
work_run_id uuid NULL
approval_request_id uuid NULL
correlation_id text NULL
trace_id text NULL
reason_redacted text NULL
before_redacted jsonb NULL
after_redacted jsonb NULL
result_status text NOT NULL
result_code text NULL
metadata_redacted jsonb NOT NULL DEFAULT '{}'
```

Regras:

- sem secret;
- sem prompt integral;
- sem PII desnecessária;
- retenção definida;
- imutável para usuários normais;
- exportação controlada;
- filtros por ator, tenant, ação, risco e período.

## 9.4 `admin_support_sessions`

```text
id uuid PK
actor_user_id uuid NOT NULL
company_id uuid NOT NULL
mode read_only|controlled_write
reason text NOT NULL
status active|expired|closed|revoked
starts_at timestamptz NOT NULL
expires_at timestamptz NOT NULL
closed_at timestamptz NULL
approved_by_user_id uuid NULL
created_at timestamptz NOT NULL
```

## 9.5 `admin_inbox_states`

Guarda apenas estado pessoal sobre itens derivados:

```text
id
admin_user_id
source_type
source_id
state unread|read|acknowledged|snoozed|dismissed
snoozed_until nullable
note_redacted nullable
updated_at
```

O item continua pertencendo à autoridade de origem.

## 9.6 `platform_incidents`

Somente incidentes de plataforma ou múltiplos tenants:

```text
id
incident_key
severity
status
scope
summary
impact_summary
started_at
detected_at
acknowledged_at
resolved_at
owner_user_id
source_refs
work_run_id nullable
postmortem_artifact_id nullable
created_at
updated_at
```

Falha isolada de Work Run não vira automaticamente incidente.

## 9.7 `admin_saved_views`

```text
id
user_id
view_key
name
filters jsonb
columns jsonb
sort jsonb
is_default
created_at
updated_at
```

Sem dados sensíveis no payload.

---

# 10. Arquitetura de informação final

A sidebar global deverá possuir **oito hubs principais**.

```text
Visão Geral
Corretoras
Operação
Inteligência
Conexões
Conhecimento
Financeiro
Governança
```

Não adicionar novo item de primeiro nível sem revisão canônica.

## 10.1 Visão Geral

```text
Visão Geral
├── Resumo
├── Caixa de Entrada
└── Incidentes
```

## 10.2 Corretoras

```text
Corretoras
├── Todas
├── Cockpits
├── Ativação e prontidão
└── Pessoas e acessos
```

Detalhes de plano, conexão, custos e operação ficam dentro do Cockpit, não como menus duplicados.

## 10.3 Operação

```text
Operação
├── Trabalhos
├── Aprovações
├── Atendimentos e conversas
├── Portais e acionamentos
└── Artifacts e entregas
```

## 10.4 Inteligência

```text
Inteligência
├── Agents
├── Skills e Tool Gateway
├── MCPs e providers
├── Auxiliares e Rotinas
├── Briefings e recomendações
├── Garimpo e Demand Radar
└── Pesquisas e monitores
```

## 10.5 Conexões

```text
Conexões
├── Visão geral
├── WhatsApp
├── Sistemas de gestão
├── Portais e Atlas
├── Apps e conectores
└── Saúde do Vault
```

## 10.6 Conhecimento

```text
Conhecimento
├── Global
├── Corretoras
├── Curadoria
├── Knowledge Candidates
└── Memórias
```

Memórias mostra metadata e governança por padrão; conteúdo sensível exige permission e justificativa.

## 10.7 Financeiro

```text
Financeiro
├── Receita e planos
├── Uso e custos
├── Créditos e saldos
├── Providers
└── Faturas e cobrança
```

## 10.8 Governança

```text
Governança
├── Segurança
├── Evals e qualidade
├── Releases e rollouts
├── Auditoria
├── Termos e políticas
└── Sistema
```

---

# 11. Shell global do Admin

## 11.1 Componentes

- sidebar colapsável;
- header contextual;
- busca global;
- seletor de período quando aplicável;
- indicador de ambiente;
- status geral;
- Admin Inbox badge;
- usuário e papel efetivo;
- banner de Support Access;
- command palette;
- breadcrumbs;
- área principal;
- painel de detalhe lateral quando adequado.

## 11.2 Ambiente

Exibir claramente:

```text
PRODUÇÃO
STAGING
LOCAL
```

Ações em produção recebem tratamento visual proporcional ao risco.

## 11.3 Command palette

Atalho de teclado e busca para:

- abrir corretora;
- abrir Work Run;
- abrir approval;
- abrir Agent/Skill/Tool;
- abrir conexão;
- abrir incidente;
- executar ação permitida;
- navegar para página.

A command palette obedece permissions e não exibe resultados proibidos.

## 11.4 Tenant context

Quando uma corretora estiver selecionada:

- mostrar nome;
- status;
- tipo de ambiente;
- readiness;
- suporte ativo;
- voltar ao escopo global.

Nunca manter tenant selecionado de forma silenciosa ao abrir outro link com escopo diferente.

---

# 12. Home executiva

## 12.1 Princípio

A Home não deve ser uma grade de métricas sem hierarquia.

Estrutura:

1. **Estado geral**;
2. **Precisa de decisão**;
3. **Corretoras em risco**;
4. **Operação em andamento**;
5. **Mudanças e resultados**;
6. **Custos e qualidade**;
7. **Atalhos contextuais**.

## 12.2 Estado geral

Exemplos:

> “Operação estável. Duas corretoras precisam de reconexão e um rollout aguarda aprovação.”

> “Incidente P1 em provider de WhatsApp afetando Resulta e AutoFleet.”

Não mostrar “Tudo saudável” quando fontes estiverem stale ou indisponíveis.

## 12.3 Precisa de decisão

Unir:

- approvals;
- rollout gates;
- incidentes;
- Knowledge Candidates;
- findings críticos;
- conexão expirada;
- budget;
- ação humana em Portal;
- release aguardando publicação.

Cada item mostra:

- o que aconteceu;
- por que importa;
- quem/qual tenant é afetado;
- há quanto tempo;
- ação recomendada;
- risco;
- botão correto.

## 12.4 Métricas de contexto

Podem aparecer:

- MRR;
- empresas ativas;
- Work Runs em andamento;
- approvals pendentes;
- incidentes abertos;
- custos do período;
- taxa de sucesso;
- tenants degradados.

Mas sempre subordinadas às decisões.

---

# 13. Admin Inbox

## 13.1 Fontes

A Inbox é uma projeção de:

- approvals;
- Intelligence Findings;
- platform incidents;
- Work Runs com necessidade humana;
- connection health;
- rollout gates;
- security alerts;
- budget alerts;
- Knowledge Candidates;
- delivery failures;
- research monitor failures.

Não duplicar o objeto de origem.

## 13.2 Priorização

Cada item possui:

- severidade;
- urgência;
- impacto;
- confidence;
- freshness;
- actionability;
- tenant count;
- deadline;
- owner.

## 13.3 Estados pessoais

- não lido;
- lido;
- reconhecido;
- adiado;
- dispensado quando permitido.

Dispensar não altera o objeto de origem.

## 13.4 Dedupe

Itens com a mesma causa devem ser agrupados.

Exemplo:

> “Provider WhatsApp degradado — afeta 3 corretoras e 8 Rotinas.”

Não gerar oito cartões idênticos.

---

# 14. Cockpit 360º da Corretora

## 14.1 Cabeçalho

Mostrar:

- nome;
- tipo: real, teste ou técnica;
- status;
- plano;
- readiness;
- owner;
- última atividade;
- Support Access;
- ações principais.

## 14.2 Abas

```text
Visão geral
Operação
Atendimento
Agents e inteligência
Auxiliares e Rotinas
Conexões
Conhecimento e memória
Artifacts e relatórios
Custos e plano
Pessoas e permissões
Histórico e auditoria
Configuração avançada
```

## 14.3 Visão geral

- resumo humano;
- readiness;
- blockers;
- incidentes;
- approvals;
- Work Runs;
- conexões;
- custos;
- qualidade;
- resultados recentes;
- recomendações;
- próximos passos.

## 14.4 Readiness

Preservar e evoluir o rollup atual.

Itens deverão incluir:

- identidade da corretora;
- Core provisionado;
- Atendimento provisionado;
- configuração tenant;
- WhatsApp;
- aprovadores;
- handoff;
- knowledge;
- Agents;
- Auxiliares;
- conexões obrigatórias;
- billing;
- segurança;
- evals mínimos;
- readiness de lançamento.

## 14.5 Ações

- abrir Support Access;
- reconectar;
- provisionar;
- executar diagnóstico;
- pausar Rotina;
- retry Work Run;
- revisar approval;
- abrir Artifact;
- ajustar plano;
- suspender tenant;
- reativar tenant.

Toda ação usa o Admin Command Gateway.

---

# 15. Hub Operação

## 15.1 Trabalhos

Lista de Work Runs com:

- status;
- tenant;
- origem;
- Skill;
- Auxiliar/Rotina;
- etapa;
- progresso;
- duração;
- custo;
- approval;
- erro humano;
- owner;
- freshness.

Ações:

- abrir timeline;
- cancelar;
- retry permitido;
- retomar;
- reprocessar step;
- abrir Artifact;
- abrir efeito externo;
- atribuir responsável.

## 15.2 Aprovações

- pendentes;
- próximas de expirar;
- decididas;
- rejeitadas;
- expiradas.

Preview obrigatório:

- ação;
- destino;
- volume;
- custo;
- risco;
- fingerprint;
- evidência;
- Work Run;
- tenant.

## 15.3 Atendimentos e conversas

Consolidar:

- conversas;
- conversation logs;
- acionamentos;
- scorecards;
- Espelho;
- handoff;
- Observador conforme policy.

Separar:

- visão operacional;
- qualidade;
- logs técnicos.

## 15.4 Portais

Preservar Portal Browser/Worker.

Mostrar:

- contas;
- sessão;
- jobs;
- evidências;
- CAPTCHA/2FA;
- credencial expirada;
- jornada/Skill;
- Atlas;
- status humano.

## 15.5 Artifacts e entregas

- Artifact;
- versão;
- formato;
- tenant;
- Work Run;
- delivery;
- abertura;
- expiração;
- falha;
- revogação;
- reenvio idempotente.

---

# 16. Hub Inteligência

## 16.1 Agents

Substituir a modal extensa por páginas de detalhe.

Estrutura:

```text
Resumo
Identidade e papel
Release ativa
Comportamento permitido
Skills e Capability Packs
Tools e conexões
Especialistas/delegações
Memória e conhecimento
Canais
Segurança
Evals
Histórico e rollout
Diagnóstico avançado
```

Prompt efetivo:

- acesso restrito;
- redigido;
- sem secrets;
- diff por release;
- apenas diagnóstico;
- não editar produção diretamente.

## 16.2 Skills e tools

Administrar:

- Skills;
- releases;
- bindings;
- Capability Packs;
- Tool Definitions;
- Tool Releases;
- health;
- custo;
- evals;
- uso;
- dependências;
- rollout;
- rollback.

## 16.3 MCPs

- servidor;
- versão;
- transporte;
- tools descobertas;
- tools homologadas;
- schema diff;
- environment permitido;
- sandbox;
- connections;
- health;
- latência;
- custo;
- incidentes.

## 16.4 Auxiliares e Rotinas

- templates;
- releases;
- instalações;
- revisões;
- readiness;
- triggers;
- execuções;
- custos;
- outcomes;
- update disponível;
- rollout/rollback;
- requests/capability gaps.

## 16.5 Intelligence Fabric

- Signals;
- evidências;
- Findings;
- Recommendations;
- responses;
- outcomes;
- Briefings;
- regras;
- quality;
- false positives;
- Demand Radar.

## 16.6 Research

- requests;
- plans;
- providers;
- sources;
- claims;
- citations;
- monitors;
- costs;
- injections;
- Artifacts;
- Knowledge Candidates.

---

# 17. Hub Conexões

## 17.1 Visão geral

Mostrar:

- conectadas;
- degradadas;
- expiradas;
- aguardando autenticação;
- sem uso;
- dependências afetadas.

## 17.2 WhatsApp

- provider;
- instância;
- health;
- pareamento;
- último evento;
- fila;
- erros;
- dependências;
- observador;
- status de atendimento;
- reconectar;
- pausar dependências;
- testar.

## 17.3 Sistemas de gestão

- InfoCap;
- Quiver;
- futuros sistemas;
- escopos;
- health;
- última sincronização;
- entidades disponíveis;
- erro;
- dependências.

## 17.4 Apps e conectores

- Drive;
- Calendar;
- Slack;
- Notion;
- e-mail;
- outros homologados.

## 17.5 Vault

Mostrar somente:

- existe/não existe;
- health;
- expiração;
- escopos;
- última rotação;
- owner;
- dependências.

Nunca mostrar:

- secret;
- token;
- senha;
- ref descriptografável;
- SessionRef reutilizável.

---

# 18. Hub Conhecimento

## 18.1 Global

- corpus;
- documentos;
- versões;
- validade;
- fontes;
- publicação;
- revoke;
- reindex;
- coverage;
- qualidade;
- conflitos.

## 18.2 Corretoras

- documentos por tenant;
- status;
- extração;
- chunks;
- indexação;
- validade;
- owner;
- acesso;
- erros.

## 18.3 Curadoria

- quarantine;
- candidatos;
- dedupe;
- contradições;
- aprovação;
- publicação;
- rollback.

## 18.4 Memórias

Mostrar por padrão:

- tipo;
- owner;
- escopo;
- contagem;
- freshness;
- origem;
- status;
- política.

Conteúdo sensível exige:

- permission;
- justificativa;
- Support Access quando tenant;
- audit.

## 18.5 Knowledge Candidates

- fonte;
- provenance;
- validade;
- risco;
- cluster;
- status;
- Curador;
- Conselho;
- Publicador.

---

# 19. Hub Financeiro

## 19.1 Preservar FinOps

A lógica atual de FinOps deve ser preservada e integrada.

## 19.2 Visões

- MRR;
- planos;
- assinaturas;
- cobrança;
- saldos;
- créditos;
- custo de LLM;
- custo de tools;
- custo de providers;
- custo de storage;
- custo por tenant;
- custo por Skill;
- custo por Auxiliar;
- custo por Work Run;
- margem quando dados comerciais existirem.

## 19.3 Alertas

- saldo baixo;
- provider caro;
- anomalia;
- custo sem atribuição;
- tenant acima do plano;
- cobrança falhou;
- consumo sem outcome.

## 19.4 Ações

- ajustar plano;
- conceder crédito com permission;
- bloquear excesso conforme policy;
- abrir análise;
- exportar relatório;
- revisar cobrança.

Nenhuma alteração financeira sem audit e idempotência.

---

# 20. Hub Governança

## 20.1 Segurança

- incidentes;
- SSRF blocks;
- prompt injection;
- acesso negado;
- role changes;
- Support Access;
- break-glass;
- sessions;
- Vault health;
- storage exposure;
- cross-tenant tests;
- secrets rotation status.

## 20.2 Evals e qualidade

- golden tests;
- regressões;
- replay;
- pass rate;
- quality by release;
- citation coverage;
- unsupported claims;
- tool success;
- artifact quality;
- user feedback;
- release gates.

## 20.3 Releases e rollouts

- releases;
- canários;
- tenants alvo;
- progress;
- health;
- diff;
- snapshots;
- pause;
- resume;
- rollback;
- report.

## 20.4 Auditoria

- ator;
- ação;
- target;
- tenant;
- permission;
- risco;
- resultado;
- trace;
- before/after redigido;
- suporte;
- período.

## 20.5 Sistema

- serviços;
- versions;
- workers;
- filas;
- Redis;
- Supabase;
- Qdrant;
- MinIO;
- provider health;
- deploy;
- feature flags permitidas;
- config não sensível.

---

# 21. Padrão universal de páginas

## 21.1 Listagem

- busca;
- filtros;
- saved views;
- paginação cursor-based;
- ordenação;
- colunas configuráveis;
- exportação permitida;
- bulk action governada;
- estado vazio útil;
- freshness.

## 21.2 Detalhe

Cabeçalho:

- nome;
- tipo;
- status;
- owner;
- tenant;
- versão;
- health;
- freshness;
- ações.

Corpo:

- resumo;
- timeline;
- dependências;
- evidências;
- custos;
- related objects;
- configuração;
- audit;
- detalhes avançados.

## 21.3 Timeline

Unir eventos por correlation/causation:

- criado;
- alterado;
- publicado;
- executado;
- aprovado;
- falhou;
- recuperado;
- entregue;
- revertido.

## 21.4 Related objects

Exemplo para Work Run:

- Skill;
- Auxiliar;
- Rotina;
- approval;
- tools;
- effects;
- Artifact;
- Finding;
- Research;
- tenant;
- custos.

---

# 22. Admin Action Contract

Toda ação mutável declara:

```text
command_id
idempotency_key
actor
permission
support_session nullable
target_type
target_id
company_id nullable
expected_version/etag
risk_tier
reason
preview
diff
blast_radius
approval_requirement
step_up_requirement
rollback_plan
```

## 22.1 Risk tiers

```text
P0 — leitura
P1 — alteração reversível e local
P2 — alteração operacional com impacto limitado
P3 — ação sensível, rollout ou side effect relevante
P4 — ação crítica/global/break-glass
```

## 22.2 Confirmação

### P1

- confirmação simples;
- preview.

### P2

- preview;
- impacto;
- motivo;
- idempotência.

### P3

- step-up;
- diff;
- blast radius;
- rollback;
- confirmação explícita.

### P4

- step-up;
- permission específica;
- motivo obrigatório;
- possível segunda aprovação;
- texto de confirmação;
- audit reforçado;
- rollback testado.

## 22.3 Bulk actions

Mostrar antes de executar:

- número de tenants;
- objetos;
- dependências;
- ações externas;
- custo estimado;
- risco;
- estratégia de canário;
- rollback.

## 22.4 Command receipt

Depois da ação:

```text
O que foi solicitado
O que foi alterado
O que não foi alterado
Work Run/trace
Resultado
Próximo passo
Rollback disponível
```

---

# 23. Read models e composição

## 23.1 Princípio

A UI não deve executar dezenas de queries independentes sem coordenação.

Criar read models compostos server-side.

## 23.2 Exemplos

```text
AdminOverviewReadModel
AdminInboxReadModel
CompanyCockpitReadModel
WorkRunDetailReadModel
AgentControlReadModel
ConnectionHealthReadModel
FinanceOverviewReadModel
GovernanceOverviewReadModel
```

## 23.3 Freshness

Todo read model declara:

- `generated_at`;
- `sources_updated_at`;
- `freshness_status`;
- fontes degradadas;
- partial data;
- cache status.

## 23.4 Cache

Redis pode guardar read models transitórios.

Regras:

- chave inclui permission scope quando necessário;
- chave inclui tenant;
- TTL por domínio;
- invalidação por evento;
- stale-while-revalidate somente quando seguro;
- cache nunca vira autoridade;
- nenhum vazamento cross-tenant.

## 23.5 Materialized views

Usar apenas quando benchmark justificar.

Refresh deve usar mecanismo canônico, sem novo scheduler paralelo.

---

# 24. Busca global

## 24.1 Objetos pesquisáveis

- corretoras;
- usuários;
- Agents;
- Work Runs;
- approvals;
- Auxiliares;
- Rotinas;
- Skills;
- Tools;
- connections;
- Portais;
- Artifacts;
- Findings;
- Briefings;
- Research;
- incidentes;
- releases.

## 24.2 Regras

- permission-aware;
- tenant-aware;
- redigida;
- sem secret;
- sem conteúdo integral sensível no resultado;
- highlight seguro;
- navegação direta;
- audit para buscas sensíveis quando necessário.

## 24.3 Busca por IDs

Aceitar IDs técnicos em modo avançado, sem expô-los na UX principal.

---

# 25. Erros, estados e linguagem humana

## 25.1 Contrato de erro

```text
code estável
human_title
human_message
recommended_action
retryable
support_reference
technical_details permitido
correlation_id
```

## 25.2 Exemplo

Mostrar:

> “A conexão do WhatsApp da Resulta expirou. Duas Rotinas estão pausadas até a reconexão.”

Detalhe avançado:

```text
CONNECTION_EXPIRED
provider=evolution-go
correlation_id=...
```

Não mostrar por padrão:

> `ToolConnectionError: unauthorized provider adapter`.

## 25.3 Estados obrigatórios

- loading;
- vazio;
- parcial;
- stale;
- degradado;
- acesso negado;
- not found;
- conflito de versão;
- erro retryable;
- erro não retryable;
- manutenção;
- offline/reconnecting.

## 25.4 Empty states

Devem explicar:

- por que está vazio;
- se falta configuração;
- próxima ação;
- quando não é problema.

---

# 26. Segurança e privacidade

## 26.1 No client

Não enviar:

- service role;
- secret;
- token;
- senha;
- Vault ref sensível;
- prompt protegido integral;
- transcript sem necessidade;
- PII fora do escopo.

## 26.2 Server-side

- permission;
- tenant scope;
- RLS/defesa em profundidade;
- redaction;
- input validation;
- output validation;
- rate limit;
- CSRF;
- idempotência;
- audit;
- egress guard quando aplicável.

## 26.3 Support Access

- read-only padrão;
- motivo;
- expiração;
- banner;
- audit;
- escrita exige elevação;
- sem visualização de secret.

## 26.4 Memória, conversas e evidências

Conteúdo sensível não aparece em overview global.

Abertura exige:

- permission;
- propósito;
- tenant scope;
- audit;
- redaction quando possível.

## 26.5 Exportação

Toda exportação declara:

- escopo;
- volume;
- sensibilidade;
- formato;
- retenção;
- watermark quando necessário;
- audit.

---

# 27. Observabilidade do Control Plane

## 27.1 Métricas

- page load;
- API latency;
- read model latency;
- error rate;
- command success;
- permission denied;
- stale reads;
- cache hit;
- search latency;
- action rollback;
- support sessions;
- admin audit events;
- bulk actions;
- mobile usage;
- failed redirects.

## 27.2 Tracing

Command trace inclui:

- request;
- actor;
- permission;
- target;
- BFF;
- domain service;
- Work Run;
- approval;
- result;
- audit event.

## 27.3 Health

Health exibido deve vir de contratos canônicos, não de heurística visual isolada.

---

# 28. Design System do Control Plane

## 28.1 Direção

Preservar a linguagem aprovada:

- dark premium;
- AutoBrokers enterprise;
- Geist e Geist Mono;
- azul como inteligência/ação;
- verde saudável;
- dourado atenção;
- vermelho crítico;
- superfícies discretas;
- bordas suaves;
- hierarquia clara.

## 28.2 Não hardcodar por página

O estado atual usa muitos estilos inline e cores locais.

Criar componentes/tokens reutilizáveis:

```text
AdminShell
AdminSidebar
AdminHeader
EnvironmentBadge
HealthBadge
RiskBadge
TenantBadge
StatusBadge
MetricStrip
DecisionCard
InboxItem
ControlTable
DetailHeader
Timeline
EvidencePanel
DiffViewer
CommandPreview
ConfirmationDialog
SupportAccessBanner
EmptyState
ErrorState
FreshnessIndicator
AdvancedDetails
```

## 28.3 Densidade

Control Plane pode ser mais denso que o Dashboard da Corretora, mas precisa manter:

- hierarquia;
- progressive disclosure;
- legibilidade;
- espaços;
- filtros claros;
- detalhes em camadas.

## 28.4 Tabelas

Usar tabela quando comparação e volume justificarem.

No mobile:

- cards;
- drawer de filtros;
- colunas prioritárias;
- ações em menu;
- nada de tabela horizontal impossível de usar.

## 28.5 Ícones e cores

Nunca usar apenas cor para transmitir estado.

Toda cor deve ter:

- label;
- ícone quando útil;
- texto;
- contraste adequado.

---

# 29. Visual Acceptance Pack obrigatório

A SPEC-061 exige um pack visual próprio, subordinado à arquitetura, usando Claude Design ou equivalente.

Não é outra SPEC, runtime ou sistema.

## 29.1 Telas mínimas

1. Home executiva desktop;
2. Home executiva mobile;
3. Admin Inbox;
4. Cockpit da Corretora;
5. Work Run detail;
6. Approval preview;
7. Agent detail sem modal gigante;
8. Skill/Tool release detail;
9. Connection detail;
10. Auxiliar template/release;
11. Intelligence Finding/Recommendation;
12. Research provider/monitor;
13. Knowledge Curator queue;
14. Finance/FinOps;
15. Security incident;
16. Release rollout;
17. Audit log;
18. Support Access banner;
19. loading/empty/error/stale/access denied;
20. confirmation P3/P4.

## 29.2 Referências históricas

Usar como evidência:

- HTMLs Claude Design citados na SPEC-036;
- screenshots de `PORTAL ADMIN.zip`;
- Central de Agentes atual;
- Cockpit atual;
- design do Artifact Hub.

Não copiar automaticamente a modal de 11 abas.

## 29.3 Aprovação

Nenhuma tela crítica é considerada final sem:

- aprovação do Founder;
- desktop;
- mobile;
- contraste;
- teclado;
- conteúdo curto e longo;
- estado vazio;
- erro;
- stale;
- ação de risco;
- comparação com implementação real.

A fundação backend pode avançar em paralelo. O acabamento final depende do pack.

---

# 30. Acessibilidade e responsividade

## 30.1 Requisitos

- navegação por teclado;
- focus visível;
- labels;
- semantic HTML;
- ARIA quando necessário;
- contraste;
- screen reader;
- reduced motion;
- zoom;
- touch targets;
- mensagens de erro associadas;
- tabelas acessíveis;
- modal/dialog correto;
- não bloquear mobile.

## 30.2 Breakpoints

Definir comportamento, não apenas largura.

- desktop: sidebar + painel;
- tablet: sidebar colapsada;
- mobile: navegação drawer/bottom action conforme tela;
- detalhe: página, não modal gigante;
- tabelas: cards/colunas prioritárias.

---

# 31. APIs do Control Plane

## 31.1 Fundação

```text
GET    /api/admin/control-plane/me
GET    /api/admin/control-plane/navigation
GET    /api/admin/control-plane/overview
GET    /api/admin/control-plane/inbox
PATCH  /api/admin/control-plane/inbox/{sourceType}/{sourceId}
GET    /api/admin/control-plane/search
GET    /api/admin/control-plane/incidents
GET    /api/admin/control-plane/incidents/{id}
POST   /api/admin/control-plane/commands/preview
POST   /api/admin/control-plane/commands/execute
GET    /api/admin/control-plane/commands/{id}
GET    /api/admin/control-plane/audit
```

## 31.2 Corretoras

```text
GET    /api/admin/control-plane/companies
GET    /api/admin/control-plane/companies/{id}
GET    /api/admin/control-plane/companies/{id}/readiness
GET    /api/admin/control-plane/companies/{id}/timeline
POST   /api/admin/control-plane/companies/{id}/support-session
POST   /api/admin/control-plane/companies/{id}/diagnose
POST   /api/admin/control-plane/companies/{id}/suspend
POST   /api/admin/control-plane/companies/{id}/reactivate
```

## 31.3 Operação

```text
GET    /api/admin/control-plane/work-runs
GET    /api/admin/control-plane/work-runs/{id}
POST   /api/admin/control-plane/work-runs/{id}/retry
POST   /api/admin/control-plane/work-runs/{id}/cancel
POST   /api/admin/control-plane/work-runs/{id}/resume
GET    /api/admin/control-plane/approvals
GET    /api/admin/control-plane/approvals/{id}
POST   /api/admin/control-plane/approvals/{id}/decide
```

## 31.4 Domínios

As APIs específicas das SPECs 052–060 podem permanecer.

O BFF:

- compõe;
- normaliza;
- autoriza;
- não duplica lógica.

## 31.5 Contratos

Todas as APIs:

- autenticação server-side;
- permission;
- tenant scope;
- schema validation;
- cursor pagination;
- stable error codes;
- correlation id;
- freshness metadata;
- redaction;
- idempotency em writes;
- ETag/version em objetos editáveis;
- audit.

---

# 32. Migração das páginas atuais

## 32.1 Estratégia

```text
inventariar
→ classificar
→ escolher autoridade
→ criar nova rota/hub
→ adaptar API
→ redirect
→ observar uso
→ remover concorrência
```

## 32.2 Mapeamento inicial

| Rota histórica | Destino canônico |
|---|---|
| `/admin` | `/admin` — Home executiva |
| `/admin/central-agentes` | `/admin/inteligencia/agents` |
| `/admin/atlas` | `/admin/conexoes/portais-atlas` |
| `/admin/espelho` | `/admin/operacao/qualidade-atendimento` |
| `/admin/acionamentos` | `/admin/operacao/atendimentos` |
| `/admin/insights` | `/admin/inteligencia/garimpo` |
| `/admin/corretoras` | `/admin/corretoras` ou Cockpit selecionado |
| `/admin/companies` | `/admin/corretoras` |
| `/admin/conversas` | `/admin/operacao/atendimentos` |
| `/admin/conversation-logs` | camada avançada de conversas |
| `/admin/logs` | `/admin/governanca/auditoria` ou Sistema |
| `/admin/financeiro` | `/admin/financeiro` |
| `/admin/finops/*` | abas do Financeiro |
| `/admin/portal-browser` | `/admin/conexoes/portais-atlas` |
| `/admin/insurer-action-channels` | Conexões/Portais |
| `/admin/auxiliares` | `/admin/inteligencia/auxiliares` |
| `/admin/routine-templates` | `/admin/inteligencia/auxiliares?tab=rotinas` |
| `/admin/blueprint-center` | Agents/Releases |
| `/admin/prompt-effective` | Agent detail/Diagnóstico avançado |
| `/admin/knowledge-base` | `/admin/conhecimento` |
| `/admin/legal-documents` | `/admin/governanca/politicas` |
| `/admin/settings` | `/admin/governanca/sistema` |

O executor deve confirmar todas as rotas reais e produzir mapa final.

## 32.3 Rotas tenant históricas

- `/admin/team`;
- `/admin/conversations`;
- `/admin/agent`;
- `/admin/documents`;
- `/admin/billing`;
- `/admin/settings` quando tenant.

Devem migrar para o Dashboard da Corretora.

## 32.4 Redirects

- preservar query params permitidos;
- preservar companyId;
- evitar loop;
- registrar telemetry;
- página antiga não continua sendo editada depois do cutover.

---

# 33. Administração das empresas técnicas

Empresas técnicas não devem aparecer misturadas às corretoras comerciais.

Criar seção:

```text
Sistema
└── Empresas técnicas
```

Mostrar:

- purpose;
- status;
- owner;
- dependências;
- documentos;
- Agents;
- uso;
- risco;
- ações permitidas.

Não usar empresa técnica para criar cérebro paralelo.

---

# 34. Evals, releases e rollout

## 34.1 Preview de release

Mostrar:

- versão atual;
- nova versão;
- diff;
- objetos afetados;
- tenants;
- evals;
- regressões;
- custo;
- rollback snapshot.

## 34.2 Rollout

Fluxo padrão:

```text
Amandus
→ Resulta
→ AutoFleet
→ produção elegível restante
```

Isso é gate interno da mesma entrega.

## 34.3 Auto-pause

Rollout pode pausar automaticamente quando:

- eval crítico falha;
- erro cresce;
- custo excede threshold;
- tenant isolation falha;
- Work Runs degradam;
- Founder pausa.

## 34.4 Rollback

- snapshot;
- compatibilidade;
- ação idempotente;
- timeline;
- verificação;
- report.

Preservar helpers atuais de rollout onde corretos.

---

# 35. Performance e SLOs

## 35.1 Budgets iniciais

Definir depois de benchmark, mas implementar para:

- overview carregar rapidamente;
- listas paginadas;
- detalhe não depender de dezenas de requests client-side;
- command preview responder antes da execução;
- atualização live sem polling excessivo;
- mobile utilizável em rede comum.

## 35.2 Padrões

- server components onde apropriado;
- BFF;
- parallel server fetch seguro;
- cursor pagination;
- virtualization para listas grandes;
- cache governado;
- SSE/event stream quando justificar;
- polling com backoff como fallback;
- cancelamento de request;
- skeletons;
- não bloquear tela inteira por módulo secundário.

## 35.3 Sem falso tempo real

Se uma tela atualiza a cada 20 segundos, mostrar freshness.

Não chamar de “AO VIVO” sem contrato real de atualização.

---

# 36. Testes obrigatórios

## 36.1 Auth

- sessão válida;
- sessão expirada;
- sessão revogada;
- cookie inválido;
- localStorage adulterado;
- user suspenso;
- company admin tentando `/admin`;
- member tentando `/admin`;
- step-up expirado.

## 36.2 RBAC

Testar cada papel e permission.

Negativos:

- suporte não publica Skill;
- financeiro não abre memória sensível;
- curador não rotaciona conexão;
- viewer não executa comando;
- company admin não acessa global;
- role removido perde acesso.

## 36.3 Multi-tenant

- Resulta não vê AutoFleet;
- Support Access Resulta não abre AutoFleet;
- busca global obedece permission;
- cache não vaza;
- Cockpit não cruza IDs;
- export não cruza tenant;
- Artifact não vaza;
- memória não vaza.

## 36.4 Commands

- preview;
- stale version;
- idempotency;
- duplicate click;
- permission denied;
- step-up;
- approval;
- rollback;
- audit;
- bulk blast radius;
- partial failure.

## 36.5 UX

- desktop;
- tablet;
- mobile;
- teclado;
- screen reader;
- loading;
- vazio;
- stale;
- degradado;
- erro;
- acesso negado;
- long content;
- 1 tenant;
- muitos tenants.

## 36.6 Domain regression

Validar:

- Work Runs;
- approvals;
- Agents;
- Skills;
- Tools;
- MCPs;
- connections;
- Artifacts;
- Auxiliares;
- Rotinas;
- Intelligence;
- Research;
- Knowledge;
- billing;
- Portais;
- WhatsApp.

## 36.7 Broker Outcome Regression Pack

- login da corretora continua funcionando;
- Dashboard continua separado;
- Atendimento continua funcionando;
- pareamento continua funcionando;
- Rotinas continuam executando;
- Auxiliares continuam disponíveis;
- Portais continuam operando;
- Briefings continuam chegando;
- Artifacts continuam abrindo;
- nenhuma rota tenant foi perdida;
- Founder administra Amandus, Resulta e AutoFleet.

---

# 37. Experiências de lançamento

## 37.1 “O que precisa da minha atenção?”

A Home mostra:

- conexão Resulta expirada;
- Rotinas afetadas;
- approval pendente;
- ação de reconectar.

## 37.2 “Por que este trabalho falhou?”

Work Run detail mostra:

- step;
- tool;
- conexão;
- erro humano;
- tentativa;
- evidência;
- CTA de retry ou correção.

## 37.3 “Publicar nova Skill”

- release;
- evals;
- diff;
- canário;
- Resulta/AutoFleet;
- rollback.

## 37.4 “Acessar a Resulta para suporte”

- motivo;
- sessão read-only;
- banner;
- ações limitadas;
- audit.

## 37.5 “Qual Auxiliar gera mais valor?”

- uso;
- sucesso;
- custo;
- Artifact;
- outcome medido;
- feedback.

## 37.6 “O que os corretores estão pedindo?”

Demand Radar mostra clusters anonimizados e candidatos a Skill/Auxiliar.

## 37.7 “Quanto custa operar?”

Financeiro mostra custo por tenant, Skill, provider e Work Run.

## 37.8 “Existe risco de segurança?”

Governança mostra incidentes, bloqueios, Support Access, injection e cross-tenant tests.

---

# 38. Plano de execução em três blocos

## Bloco A — Foundation, auth, RBAC, shell e Inbox

Implementar:

- inventário final de rotas/APIs;
- separação `/admin` × `/dashboard`;
- sessão server-side;
- remoção de localStorage como autoridade;
- RBAC e permissions;
- migrations mínimas;
- Support Access;
- step-up;
- Admin Audit Events;
- Admin Command Gateway;
- Control Plane BFF;
- read models;
- freshness;
- shell;
- navegação;
- busca global;
- Home;
- Admin Inbox;
- incidentes;
- design tokens/componentes base;
- testes de auth/RBAC/multi-tenant.

### Gate A

- company admin não acessa Admin Global;
- master mapeado com segurança;
- permissions server-side;
- localStorage adulterado não concede acesso;
- audit funciona;
- Support Access funciona;
- Home e Inbox usam dados reais;
- zero secret no client;
- zero cross-tenant;
- shell mobile funcional.

## Bloco B — Hubs, Cockpits e comandos operacionais

Implementar:

- Cockpit 360º;
- readiness;
- Work Runs;
- approvals;
- Atendimentos/conversas;
- Portais;
- Artifacts;
- Agents;
- Skills/Tools/MCPs;
- Auxiliares/Rotinas;
- Intelligence/Garimpo;
- Research;
- Connections/Vault health;
- Knowledge/Memory;
- Financeiro;
- Governança;
- actions/preview/diff;
- rollout/rollback;
- erros humanos;
- detalhes avançados;
- observabilidade;
- testes de comandos e regressão.

### Gate B

- todas as SPECs 052–060 possuem superfície administrativa funcional;
- nenhuma ação mutável ocorre direto do client;
- preview/permission/idempotência/audit funcionam;
- Cockpit da Resulta e AutoFleet é útil;
- Work Run pode ser operado;
- approval pode ser decidido;
- release pode ser canariada e revertida;
- conexões mostram dependências;
- custos são atribuídos;
- detalhes sensíveis obedecem least privilege.

## Bloco C — Visual Acceptance, migração e produção

Implementar:

- Visual Acceptance Pack;
- ajustes aprovados;
- mapa final de rotas;
- redirects;
- migração de páginas históricas;
- remoção de navegação concorrente;
- remoção de auth client-side como autoridade;
- telemetry de redirects;
- accessibility review;
- performance benchmark;
- canário Amandus;
- canário Resulta;
- canário AutoFleet;
- correção de achados;
- deploy;
- ativação;
- relatório final.

### Gate C

- Founder aprova UX;
- Amandus, Resulta e AutoFleet verdes;
- nenhuma rota crítica perdida;
- nenhuma autoridade administrativa paralela;
- segurança verde;
- rollback pronto;
- performance aceitável;
- mobile funcional;
- Control Plane ativo em produção.

---

# 39. Definition of Done

A SPEC-061 só termina quando:

1. `/admin` é exclusivamente global.
2. corretoras usam `/dashboard`.
3. sessão é server-side.
4. `localStorage` não concede autoridade.
5. RBAC granular funciona.
6. permissions são testadas.
7. Support Access é temporário e auditado.
8. step-up funciona.
9. Admin Command Gateway é o caminho mutável.
10. Admin Audit Trail funciona.
11. Home mostra estado real.
12. Admin Inbox prioriza decisões.
13. busca global é permission-aware.
14. Cockpit 360º funciona.
15. readiness funciona.
16. Work Runs são operáveis.
17. approvals são operáveis.
18. Agents são administráveis sem modal gigante como UX principal.
19. Skills/Tools/MCPs são administráveis.
20. Auxiliares/Rotinas são administráveis.
21. Artifacts/entregas são administráveis.
22. Intelligence/Briefings/Garimpo são administráveis.
23. Research/providers/monitors são administráveis.
24. Connections/WhatsApp/Portais são administráveis.
25. Knowledge/Memory são administráveis com privacy.
26. FinOps/billing/custos são administráveis.
27. Segurança/evals/releases/rollouts são administráveis.
28. todas as ações relevantes têm preview.
29. ações sensíveis têm step-up/approval.
30. comandos são idempotentes.
31. erros têm linguagem humana.
32. detalhes técnicos ficam em camada avançada.
33. freshness é visível.
34. zero secret chega ao client.
35. zero tenant vaza.
36. desktop funciona.
37. mobile funciona.
38. acessibilidade mínima funciona.
39. Visual Acceptance Pack foi aprovado.
40. rotas antigas redirecionam.
41. páginas antigas não continuam soberanas.
42. Amandus passou.
43. Resulta passou.
44. AutoFleet passou.
45. APPLY/VERIFY/ROLLBACK existem.
46. relatório final existe.
47. Control Plane está ativo em produção.

---

# 40. Critérios de parada legítima

O executor só deve parar e pedir decisão do Founder quando encontrar:

- risco real de perda de dados;
- conflito impossível entre identidade global e tenant;
- necessidade de escolher política comercial que altere planos;
- necessidade de novo provedor de autenticação não previsto;
- acesso de produção não autorizado;
- decisão de marca relevante para o Visual Acceptance Pack;
- ação P4 sem responsável ou política;
- dependência anterior impossível de executar no mesmo programa;
- conflito legal/compliance sobre acesso de suporte.

Não parar por:

- número de páginas;
- necessidade de refatorar layout;
- necessidade de migrations;
- necessidade de RBAC;
- necessidade de redirects;
- necessidade de criar BFF;
- necessidade de testes;
- necessidade de design;
- necessidade de mobile;
- necessidade de deploy;
- necessidade de remover modal antiga;
- necessidade de consolidar rotas.

---

# 41. Fora do escopo desta SPEC

Ficam para SPEC-062:

- matriz comercial final de planos e preços;
- billing comercial completo das novas capacidades;
- eval framework global consolidado;
- launch readiness final de toda a plataforma;
- SLOs finais depois de benchmark;
- disaster recovery consolidado;
- capacidade/carga final;
- runbooks finais de operação 24/7;
- checklist legal/comercial de lançamento;
- sales enablement e onboarding comercial final.

Também ficam fora:

- CRM de vendas;
- sistema de tickets completo;
- BI genérico;
- editor SQL;
- shell de produção arbitrário;
- marketplace público;
- impersonação invisível;
- exposição de secrets;
- decisões autônomas de alto risco.

---

# 42. Próxima SPEC

A próxima autoridade será:

```text
SPEC-062 — AutoBrokers Evals, Billing, Rollout & Production Readiness
```

Ela deverá consolidar:

- evals ponta a ponta;
- golden datasets;
- quality gates;
- billing comercial;
- quotas e planos;
- FinOps final;
- observabilidade de lançamento;
- capacidade e carga;
- SLOs;
- incident response;
- backup e disaster recovery;
- segurança final;
- runbooks;
- rollout comercial;
- onboarding;
- critérios de venda;
- launch checklist;
- go-live.

Não deverá criar outro Control Plane, runtime, Registry, Work OS, Artifact Hub, Intelligence Fabric ou Research Orchestrator.
