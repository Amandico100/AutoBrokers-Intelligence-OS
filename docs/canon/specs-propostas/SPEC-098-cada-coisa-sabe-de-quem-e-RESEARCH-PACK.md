# SPEC-098 — RESEARCH PACK
## CADA COISA SABE DE QUEM É
### Identity, Scope & Company Soul Fabric

**Produto:** AutoBrokers Intelligence OS  
**Tipo:** COMPANION NORMATIVO DE EVIDÊNCIA — leitura obrigatória junto da Candidate SPEC-098  
**Data:** 03/09/2026  
**Repo:** `Amandico100/AutoBrokers-Intelligence-OS`  
**HEAD auditado:** `67506906f0b8f60d89585878f15958a9ea438f09`  
**Protocolo:** AutoBrokers AAA **v11.2**  
**Candidate SPEC associada:** `SPEC-098-cada-coisa-sabe-de-quem-e.md`  
**Nova referência externa avaliada:** `nduckmink/arkon`

> **OBSERVAÇÃO DE GOVERNANÇA DA PROPOSTA**  
> Esta é uma proposta inicial para a SPEC-098. Serve de insumo e de inspiração para criarmos uma SPEC definitiva.  
> A SPEC definitiva pode ser modelada, melhorada e modificada em tudo que for melhor para o projeto.  
> Esta observação vale para todas as propostas de SPEC produzidas por esta Foundry.

---

# 0. CONTRATO DE LEITURA — DOIS DOCUMENTOS, UM PACOTE

Este Research Pack não é apêndice opcional.

```text
SPEC-098-cada-coisa-sabe-de-quem-e.md
+
SPEC-098-cada-coisa-sabe-de-quem-e-RESEARCH-PACK.md
=
PACOTE DE PROPOSTA DA SPEC-098
```

A Candidate SPEC carrega outcome, invariantes, contratos, blocos, gates, testes e DoD. Este Research Pack carrega **de onde vieram as ideias, o que foi medido/observado, o que cada referência realmente sustenta, o que foi adotado/adaptado/rejeitado e por quê**.

## RP0 — Research Pack Receipt

Antes do warm-up/código:

```text
RP0_SPEC_READ = YES
RP0_RESEARCH_PACK_READ = YES
RP0_CURRENT_HEAD = <sha vivo>
RP0_PROTOCOL = <versão viva>
RP0_INTERNAL_AUTH_SEAMS_READ = YES
RP0_ARKON_SOURCE_READ = YES
RP0_ARKON_LICENSE_ACK = YES
RP0_EXTERNAL_REFERENCE_LEDGER_ACK = YES
RP0_STALE_PREMISES = [...]
```

**RP0 falhou → não codificar.**

---

# 1. POR QUE A SPEC-098 EXISTE

O AutoBrokers já é multi-tenant e já possui camadas de memória, agentes, Work Runs, connectors, approvals e usuários. O problema agora não é “adicionar login”.

O problema é garantir que todo pedaço do sistema consiga responder corretamente, de forma consistente:

```text
QUEM é o ator?
EM QUAL corretora ele está operando agora?
QUAL papel ele tem nessa corretora?
QUAL time/área, se aplicável?
QUAL entidade está em contexto?
QUAL Work Run / Thread está em contexto?
O QUE ele pode ver?
O QUE ele pode fazer?
QUAL identidade da corretora deve moldar a resposta?
QUAL perfil do usuário deve personalizar a resposta?
QUAL papel do agente limita seu comportamento?
QUAL dado pertence a qual scope?
```

Hoje essas respostas existem em partes diferentes e com maturidades diferentes.

A 098 deve criar **uma linguagem e um contrato únicos de Identity + Scope**, não um novo cérebro.

---

# 2. RESULTADO DE PRODUTO

A visão desejada:

```text
REQUEST / WORK / MESSAGE
        ↓
PRINCIPAL IDENTITY
        ↓
ACTIVE COMPANY
        ↓
MEMBERSHIP / ROLE
        ↓
OPTIONAL TEAM / PURPOSE
        ↓
ENTITY / RUN / THREAD CONTEXT
        ↓
CAPABILITY / AUTHORIZATION CONTEXT
        ↓
COMPANY FACTS + COMPANY SOUL
        ↓
USER PROFILE
        ↓
AGENT ROLE
        ↓
CONTEXT COMPOSER
        ↓
READ / PLAN / ACT
        ↓
FRESH AUTHORIZATION AT EFFECT
```

O objetivo não é transformar tudo em ACL. É impedir três doenças:

1. **identidade errada** — sistema fala/age como se estivesse em outro contexto;
2. **scope errado** — dado de A aparece ou é escrito em B;
3. **persona misturada** — Company Soul, memória, perfil de usuário, Agent Role e facts viram uma massa de prompt impossível de governar.

---

# 3. O QUE O MASTERPLAN JÁ CONGELOU

O Masterplan atual reserva a SPEC-098 para:

```text
Global
Corretora
Team
Usuário
Entidade
Run / Thread
```

E pede separar:

```text
company facts
company soul
user profile
agent role
```

Também congela:
- Smith/LangGraph continua runtime único;
- Work OS continua único;
- Tool Gateway continua único;
- Skill Registry continua único;
- Artifact Hub continua único;
- memória/conhecimento não ganha segunda authority;
- Supabase continua truth;
- Qdrant é índice derivado.

Portanto, qualquer referência externa precisa caber nisso.

---

# 4. O GLOSSÁRIO ATUAL — O QUE JÁ É CANÔNICO

O Glossário atual define:

## Agent

```text
Agente = quem conversa
agent_role = papel
agent_audience = público
CORE = broker_internal
attendance = insured_external
```

## Capability vs Tool

```text
Capability = poder governável
Tool = implementação técnica
```

## Connector scope

```text
platform
company
user
```

## Memory / Knowledge

```text
Conhecimento global → knowledge_cards
Memória da corretora → company_memories
Memória do usuário → user_memories
```

## Current layering

```text
GLOBAL
CORRETORA
USUÁRIO
```

A 098 expande o vocabulário de scope sem apagar esses conceitos.

---

# 5. ACHADO CRÍTICO — NEXT E FASTAPI NÃO RESOLVEM COMPANY DO MESMO JEITO

Este é um dos maiores motivos para a 098.

## Next / tenant dashboard — caminho moderno

`lib/admin/admin-auth.ts` possui `requireCompanyMember()`.

Quando existe `activeCompanyId`, ele:
- lê a sessão;
- consulta `company_members` **a cada request**;
- exige `status='active'`;
- usa role/is_owner do vínculo daquela corretora;
- não confia apenas na sessão.

Isso é bom e já corrige um incidente real.

## FastAPI — caminho antigo

`backend/app/core/auth.py:get_current_company_id()`:
- autentica user;
- consulta `users_v2.company_id`;
- devolve a empresa primária.

Ele não conhece `activeCompanyId` nem resolve explicitamente o vínculo em `company_members`.

### Implicação

Hoje há **mais de uma semântica para “qual é a corretora atual?”**.

A 098 deve eliminar essa divergência lógica.

---

# 6. O INCIDENTE QUE JÁ PROVOU QUE ISSO NÃO É TEORIA

SPEC-047/048 registram que havia um seam que ignorava a empresa ativa. Com AutoFleet selecionada, uma edição podia atingir a Resulta porque partes do sistema continuavam usando a empresa primária.

A correção em caminhos modernos passou a revalidar `activeCompanyId` em `company_members` a cada request.

Conclusão:

> **Active company não é detalhe de UI. É parte da autorização e do scope de dados.**

A 098 não começa do zero: ela pega a lição desse incidente e a torna regra transversal.

---

# 7. SEAMS A AUDITAR — NÃO DECLARAR VULNERABILIDADE SEM REPRODUZIR

A busca no HEAD atual ainda encontra vários caminhos com `session.companyId` e `users_v2.company_id` diretos.

Um exemplo que merece warm-up explícito:

```text
app/api/n8n/route.ts
→ targetCompanyId = body.companyId || session.companyId
```

Isso parece inconsistente com a regra de que tenant context deve ser server-derived. Porém a Candidate **não declara exploit** sem reproduzir autenticação, caller e guardas ao redor.

Outros caminhos administrativos/billing também usam session company de maneiras próprias.

### Saída do BLOCO 0 da 098

Criar o **Identity/Scope Seam Census**:

```text
path
surface
principal type
company source
role source
active-company aware?
revalidates membership?
client-supplied scope?
background?
point-of-effect recheck?
status
```

---

# 8. COMPANY MEMBERS JÁ EXISTE — NÃO RECRIAR TENANCY

`company_members` já modela:

```text
user ↔ company
role
is_owner
status
UNIQUE pair
```

`users_v2.company_id` continua como empresa primária por compatibilidade.

`activeCompanyId` existe na sessão e a troca explícita valida membership.

A 098 não deve criar uma segunda tabela “tenant_users” só para parecer mais limpa.

Ela deve criar/estender o **resolver canônico**.

---

# 9. TEAM AINDA NÃO É UM SCOPE CANÔNICO GERAL

Há UI/rotas de equipe e `company_members`, mas a busca por `team_id` no código atual encontra principalmente documentos de proposta, não uma camada transversal de scope.

Isso sugere:

```text
“equipe de uma corretora” existe
≠
“Team Scope” está implementado em todo o sistema
```

A 098 deve decidir o mínimo necessário para permitir futuramente:
- canal atribuído a team;
- Auxiliar restrito a team;
- knowledge/memory restrito a team;
- Work visibility por team;
- reports por area/team;
sem construir um organograma enterprise completo.

---

# 10. ENTITY / RUN / THREAD — NÃO CONFUNDIR COM RBAC

Esses scopes respondem “**sobre o que estamos trabalhando?**”, não necessariamente “qual cargo a pessoa tem?”.

Candidate:

```text
ENTITY
policy:{id}
client:{id}
case:{id}
claim:{id}
renewal:{id}

RUN
work_run:{id}

THREAD
conversation:{id}
langgraph_thread:{id}
```

Eles devem ser descendentes do company context e nunca capazes de mudar tenant.

---

# 11. QUATRO COISAS QUE PRECISAM SER SEPARADAS

## 11.1 Data Scope

Onde um dado se aplica.

```text
global / company / team / user / entity / run / thread
```

## 11.2 Authorization Scope

O que um principal pode fazer sobre um objeto.

## 11.3 Credential Scope

Quem segura a credencial:

```text
platform / company / user
```

## 11.4 Memory Namespace

Onde memória/conhecimento é armazenado/retrieved.

Essas quatro dimensões podem usar os mesmos IDs, mas **não são a mesma coisa**.

---

# 12. COMPANY FACTS ≠ COMPANY SOUL

## Company Facts

Fatos verificáveis/operacionais:

```text
nome legal/comercial
CNPJ
endereço
telefone
site
horário
carteira/linhas atendidas quando comprovadas
canais
configuração operacional
```

Fontes: companies, onboarding, connectors, InfoCap e dados aprovados.

## Company Soul

Identidade comportamental/comunicacional da corretora:

```text
tom
postura de atendimento
nível de formalidade
forma de explicar
princípios de relacionamento
posicionamento de serviço
preferências de linguagem
estilo de acolhimento
coisas estilísticas a evitar
```

Soul **não é**:
- cobertura;
- regra legal;
- política de segurança;
- procedure;
- Skill;
- conhecimento RAG;
- permissão.

---

# 13. USER PROFILE ≠ USER MEMORY

## User Profile

Contexto estável/curado sobre a pessoa **naquela corretora**:

```text
nome de exibição
papel na empresa
preferências de comunicação
idioma
formato de resposta preferido
área/time
responsabilidades declaradas
```

## User Memory

Fatos aprendidos ao longo do uso, governados pela Memory Fabric.

A 098 define identidade/perfil e seu scope. A 102 continua dona da fábrica de memória/conhecimento.

### Decisão recomendada

`UserProfile` deve ser scoped por `company_id + user_id`, porque a mesma pessoa pode ser dona em uma empresa e membro em outra.

Account-level preferences realmente globais podem existir separadamente, mas não são motivo para misturar o perfil operacional entre corretoras.

---

# 14. AGENT ROLE ≠ COMPANY SOUL

`AgentRole` responde:

```text
qual é sua função?
para quem fala?
qual seu objetivo?
quais limites funcionais?
```

`CompanySoul` responde:

```text
como esta corretora se comunica e se relaciona?
```

Exemplo:

```text
AgentRole = atendimento ao segurado
CompanySoul = próximo, claro, sem juridiquês, explica antes de pedir documento
```

Company Soul nunca pode ampliar permissões do Agent Role.

---

# 15. PRECEDÊNCIA DE CONTEXTO — CANDIDATE

Candidate de composição:

```text
1. Platform safety / canonical invariants
2. Agent Role / audience / functional boundaries
3. Company Facts
4. Company Soul
5. Team context
6. User Profile
7. Entity context
8. Run context
9. Thread working context
10. Retrieved memory / knowledge apropriado ao scope
```

“Mais específico” pode personalizar o de cima, mas não pode revogar safety nem aumentar autorização.

---

# 16. SCOPE CONTEXT — O OBJETO QUE FALTA

Candidate conceitual:

```text
ScopeContext
  principal
    kind
    canonical_actor_ref
    user_id?
    agent_id?

  company
    company_id
    membership_ref?
    role?
    is_owner?

  team?
    team_id
    team_role?

  purpose?

  entity?
    entity_type
    entity_id

  run?
    work_run_id

  thread?
    conversation_id / thread_id

  resolved_at
  source
  scope_fingerprint?
```

Isto não é autorização em si. É o contexto canônico que os policy checks consomem.

---

# 17. AUDIT SNAPSHOT ≠ PERMISSION TO ACT LATER

Uma das decisões mais importantes da 098:

Work Run deve poder guardar um snapshot do contexto em que nasceu:

```text
scope_snapshot
principal_snapshot
role_snapshot
```

para auditoria/replay.

Mas:

> **o snapshot não concede permissão eterna.**

Antes de um efeito sensível, o sistema revalida autoridade atual.

Exemplo:

```text
09:00 Work Run começa com Ana = admin da Resulta
09:40 Ana perde acesso
10:00 job termina cálculo
10:01 job tenta enviar/publicar/alterar
→ fresh authorization FAILS
→ nenhum efeito externo/durável sensível
→ Work Run registra authorization_revoked
```

---

# 18. ARKON — O QUE O DOCUMENTO DO USUÁRIO PROPÔS

Fonte recebida: `AVALIAÇÃO ARKON.txt`.

A avaliação recomenda **não instalar Arkon**, não criar “SPEC Arkon” e não trocar arquitetura; recomenda absorver padrões específicos nas SPECS existentes.

Para a 098, a proposta específica é:

> fresh scope resolution no ponto crítico; proteção contra stale authorization.

Também destaca:
- scope pode mudar durante worker;
- publication deve consultar authority atual;
- stale objects podem gerar visibility leak;
- advisory locks/constraints ajudam em races;
- Arkon GLOBAL/DEPARTMENT **não** deve ser traduzido para AutoBrokers tenant/team.

Essa direção foi considerada válida, com ajustes descritos abaixo.

---

# 19. ARKON — VALIDAÇÃO INDEPENDENTE NO REPOSITÓRIO

Repo verificado: `nduckmink/arkon`.

GitHub atual em 03/09/2026:
- criado em 30/04/2026;
- descrição: Enterprise AI Knowledge Hub & MCP Server;
- ~1.260 stars;
- ~270 forks;
- Python;
- main público.

## Padrões confirmados

### Verbatim
`preserve_verbatim` existe em migration, worker e search; source pode pular MRP e ser indexada raw.

### Concurrency
Há advisory locks e unique constraints para evitar versões concorrentes duplicadas; changelog documenta race real.

### Stale result
AI review runner refresca draft e descarta verdict de uma revision round antiga para não sobrescrever review mais novo.

### Conclusão

O Arkon é boa referência de **engenharia de stale state / race / governance**, mas não autoridade arquitetural para o AutoBrokers.

---

# 20. DECISÃO ARKON PARA A SPEC-098

| Ideia | Nota | Decisão |
|---|---:|---|
| Instalar Arkon | 15/100 | REJECT |
| Usar Arkon auth/scope model como nosso | 25/100 | REJECT |
| Department → tenant/team | 10/100 | REJECT |
| Fresh scope at effect | **100/100** | **ADOPT/ADAPT** |
| Stale-result protection | **98/100** | **ADAPT** |
| Advisory lock em toda alteração | 55/100 | NÃO GENERALIZAR |
| Lock/unique/idempotency quando race prova exigir | **96/100** | ADAPT |
| Out-of-scope existence hint cross-tenant | **0/100** | PROHIBIT |

### Invariante Arkon-inspired

> **Toda ação sensível deve usar autorização e ownership atuais no ponto de efeito. Contexto capturado no início serve para auditoria e planejamento, não como autorização permanente.**

---

# 21. LICENÇA ARKON — LIMITE EXPLÍCITO

O repo usa **PolyForm Internal Use License 1.0.0**.

Ela autoriza internal business use, mas não é licença permissiva de distribuição/SaaS.

Para AutoBrokers:

```text
conceito/padrão → pode inspirar design
código Arkon → NÃO copiar/incorporar como componente do SaaS sem análise jurídica/licença adequada
```

O Research Pack serve como referência de engenharia, não como autorização de reutilização de código.

---

# 22. REFERÊNCIA EXTERNA — HERMES AGENT

Documentação oficial consultada:

- https://hermes-agent.nousresearch.com/docs/user-guide/which-file-does-what
- https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/
- https://hermes-agent.nousresearch.com/docs/guides/use-soul-with-hermes
- https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files

Hermes separa explicitamente:

```text
SOUL.md   → identidade/persona/tom do agente
USER.md   → perfil do usuário
MEMORY.md → coisas aprendidas
AGENTS.md → instruções do projeto/contexto
```

### O padrão que aproveitamos

**Separar tipos de contexto por responsabilidade.**

### O que não copiamos

- arquivos markdown como storage do SaaS;
- frozen prompt snapshot como regra universal;
- SOUL do agente igual a Company Soul.

No AutoBrokers, Company Soul pertence à corretora; Agent Role pertence ao agente.

---

# 23. REFERÊNCIA EXTERNA — OPENFGA

Documentação oficial:

- https://openfga.dev/docs/modeling/organization-context-authorization
- https://openfga.dev/docs/modeling/roles-and-permissions
- https://openfga.dev/docs/modeling
- https://openfga.dev/docs/modeling/contextual-time-based-authorization

O padrão mais relevante é **organization context authorization**:

> usuário pode pertencer a múltiplas organizações, mas acesso precisa ser avaliado no contexto da organização selecionada.

Isso casa diretamente com `company_members + activeCompanyId`.

OpenFGA também modela roles/permissions e relações objeto↔objeto.

### Decisão

Usar como **referência de modelagem**, não instalar OpenFGA na 098 por default.

O repo já possui tenancy/RLS/capabilities; adicionar um authorization engine agora exigiria prova de necessidade superior.

---

# 24. REFERÊNCIA EXTERNA — LANGGRAPH / LANGMEM

Referências oficiais:

- https://langchain-ai.github.io/langmem/guides/dynamically_configure_namespaces/
- documentação LangGraph de long-term memory/store

Padrão útil:

```text
namespace hierárquico
→ user / agent / org / outros valores em runtime
```

A ferramenta de memory não precisa saber o storage físico; recebe namespace resolvido.

### Decisão AutoBrokers

A 098 define `ScopeContext` e namespace semantics. A 102 decide fábrica de memory/knowledge e como Supabase/Qdrant usam esse scope.

Não trocar nossa truth por InMemoryStore/LangMem.

---

# 25. REFERENCE ADOPTION LEDGER

| Fonte | Padrão | Decisão | Adaptação |
|---|---|---|---|
| SPEC-047/048 | active company + membership per request | ADOPT | tornar seam canônico transversal |
| current `requireCompanyMember` | DB current role | ADOPT | base do resolver Next |
| current FastAPI auth | primary company only | REPLACE/EXTEND | active-company aware |
| Glossário | GLOBAL/COMPANY/USER | ADOPT | expandir sem quebrar |
| Masterplan | TEAM/ENTITY/RUN/THREAD | ADOPT | typed scope path |
| Hermes | Soul/User/Memory separation | ADAPT | CompanySoul/UserProfile/Memory/AgentRole |
| OpenFGA | organization context | ADOPT PATTERN | selected company required |
| OpenFGA | relation permissions | ADAPT | resource/role modeling quando necessário |
| LangMem | hierarchical namespace | ADAPT | memory namespace via ScopeContext |
| Arkon | fresh scope at commit | ADOPT/ADAPT | fresh effect gate |
| Arkon | stale worker result guard | ADAPT | version/fingerprint where needed |
| Arkon | global/department scope | REJECT | nossa hierarchy é diferente |
| Arkon | code reuse | REJECT | license + architecture |

---

# 26. SCOPE TAXONOMY RECOMENDADA

```text
GLOBAL_AUTOBROKERS
└── COMPANY
    ├── TEAM
    │   └── USER
    ├── USER
    ├── ENTITY
    │   └── RUN
    │       └── THREAD
    └── RUN
        └── THREAD
```

Isto é uma **taxonomia lógica**, não obrigação de criar uma árvore física universal.

Um objeto só recebe os scopes que fazem sentido.

---

# 27. SCOPE PATH — ALTERNATIVA À EXPLOSÃO DE COLUNAS

Em vez de toda tabela ganhar:

```text
company_id
team_id
user_id
entity_id
run_id
thread_id
```

considerar contratos tipados/refs conforme domínio.

Exemplo conceitual:

```text
ScopePath = [
  company:resulta,
  team:sinistros,
  entity:case:abc,
  run:123
]
```

Mas o `company_id` continua coluna/guard crítico nas tabelas multi-tenant onde já é necessário para RLS/index/partitioning.

Não substituir `company_id` por JSON genérico.

---

# 28. TEAM — MODELO MÍNIMO

Antes de criar tabela, BLOCO 0 mede o que já existe.

Se faltar objeto Team, candidate mínimo:

```text
teams
  id
  company_id
  name
  status

team_members
  team_id
  company_id
  user_id
  role?
  status
```

Invariantes:
- team pertence a exatamente uma company;
- membership de team não concede company membership;
- usuário só entra em team se já pertencer à company;
- remover company membership invalida team access.

Não construir org chart, manager hierarchy ou HR suite.

---

# 29. PRINCIPAL / ACTOR IDENTITY

Precisamos de uma referência canônica capaz de representar:

```text
user
agent
subagent
auxiliary/worker
system
platform_admin
external_client future
```

Mas respeitar o Glossário e Work Events existentes.

Candidate:

```text
canonical_actor_ref
actor_type
user_id?
agent_id?
```

Não criar identity object duplicando users/agents.

---

# 30. PURPOSE — POR QUE O CONTEXTO EXISTE

Mesmo principal/company pode ter permissões diferentes por finalidade.

Candidate `purpose`:

```text
broker_chat
attendance
claims_shadow
reporting
billing
admin_config
connector_execution
external_harness
```

Purpose não substitui Capability, mas ajuda a montar minimum context/tool surface nas SPECS futuras.

---

# 31. CONTEXT COMPOSER — SEM NOVO CÉREBRO

A 098 deve oferecer um seam canônico para compor contexto para Smith:

```text
resolve ScopeContext
→ load CompanyFacts
→ load CompanySoul
→ load UserProfile scoped
→ load AgentRole
→ attach entity/run/thread facts
→ hand scope keys to memory/knowledge retrieval
→ build bounded context sections
```

Não criar um segundo agent runtime.

---

# 32. COMPANY SOUL — DATA MODEL CANDIDATE

Preferir objeto versionado/curado, não blob solto de prompt.

Candidate semantic fields:

```text
voice_tone
formality
explanation_style
relationship_style
service_principles[]
preferred_terms[]
avoid_style_terms[]
uncertainty_style
handoff_style
approved_examples?
version
status
updated_by
updated_at
```

### O que NÃO entra

```text
regras legais
procedimentos
coberturas
senhas
API keys
seguradora route
system prompt raw
capability grants
```

---

# 33. COMPANY SOUL — COMO NASCE

Sources candidates:

1. Founder/admin edit explícito.
2. Onboarding guiado.
3. `IDENTITY_CANDIDATE` produzido por 090/observação.
4. Brand capture como sugestão.

Regra:

> Auto-inference pode **propor**, não publicar Soul silenciosamente.

Candidate lifecycle mínimo:

```text
candidate
→ review
→ approve
→ active version
```

A fábrica genérica de candidate/review/publish continua sendo aprofundada na 102.

---

# 34. USER PROFILE — DATA MODEL CANDIDATE

```text
company_id
user_id
display_name
role_context
team_refs
language
response_preferences
communication_preferences
responsibilities[]
profile_version
updated_at
source
```

Não copiar role de autorização para texto editável de profile.

`role_context` de apresentação ≠ membership role authority.

---

# 35. AUTOMATIC IDENTITY — O PROBLEMA DO PRODUTO

O Masterplan registra que a identidade automática da corretora não estava funcionando como esperado.

A 098 deve diagnosticar:

- quem hoje escreve company profile;
- brand capture atual;
- quais campos são facts vs inferred persona;
- onde prompt composer lê identidade;
- se Core e Attendance recebem o mesmo bloco indevidamente;
- se user profile é carregado;
- se company memory é confundida com Soul;
- se mudança de company ativa troca contexto imediatamente.

Não “consertar” isso adicionando mais prompt hard-coded.

---

# 36. FRESH AUTHORIZATION GATE — ESPECIFICAÇÃO

Para efeitos sensíveis:

```text
READ current principal status
READ current company membership
READ current team membership if required
READ current resource ownership/company
READ current capability/role requirement
COMPARE with intended target
ALLOW / DENY
WRITE audit event
```

Efeitos candidatos:
- mensagem externa;
- portal/connector action;
- mutation de cliente/apólice/case;
- publication de knowledge/memory/Soul;
- approval execution;
- Artifact sharing externo;
- billing;
- admin config.

Não reconsultar tudo antes de cada operação read-only trivial.

---

# 37. STALE CONTEXT / VERSIONING

Possíveis mecanismos:

```text
scope_fingerprint
authorization_epoch
membership.updated_at
resource.version
expected_version
```

Não congelar um único mecanismo antes do warm-up.

Objetivo:
- detectar que o contexto mudou;
- evitar lost update;
- não aplicar decisão baseada em versão antiga.

---

# 38. CONCURRENCY

Arkon mostra advisory locks, unique constraints e stale-worker guards. AutoBrokers deve escolher mecanismo por invariant:

```text
unique constraint → impossibilidade estrutural
optimistic version → edit/review
row/advisory lock → critical section curta
idempotency key → efeitos repetidos
lease → worker ownership
```

Não usar advisory lock como martelo universal.

A 114 fará stress/failure-injection transversal; a 098 precisa apenas provar as races do identity/scope que introduzir.

---

# 39. NO EXISTENCE LEAK

Entre corretoras:

```text
“há um documento parecido em outra empresa”
“existe memória fora do seu scope”
“há três resultados sem acesso”
```

é proibido.

Cross-tenant search deve se comportar como se o outro tenant não existisse.

Dentro da mesma empresa, hints de resource restrito podem ser avaliados futuramente, mas não são P0.

---

# 40. PROMPT INJECTION / SOUL POISONING

Company Soul é contexto de alta influência.

Riscos:
- documento externo tentar redefinir Soul;
- usuário comum gravar “ignore regras” em profile;
- memory candidate virar instruction;
- Soul tentar ampliar Agent Role/capabilities.

Gates:
- source/author permission;
- typed fields;
- bounded rendering;
- review;
- no raw untrusted blob no system section;
- safety/capability hierarchy superior.

SPEC-107 aprofundará Untrusted Content Gate, mas 098 não pode abrir a porta.

---

# 41. CONTEXT BUDGET

Não carregar todas as camadas integralmente em todo turno.

Candidate:

```text
ALWAYS SMALL
platform invariants
agent role
company soul summary
principal/company refs

ON DEMAND
company facts detalhados
team context
entity facts
user memory
knowledge
run history
thread history
```

Objetivo: identidade consistente sem destruir TTFT/context cache.

---

# 42. OBSERVABILITY

Events/metrics candidates:

```text
scope.resolved
scope.denied
scope.stale_detected
scope.changed_during_run
authz.revalidated
authz.revoked_mid_run
company_soul.loaded
company_soul.version_changed
user_profile.loaded
context.cross_scope_blocked
```

Sem PII em log.

Métricas:
- resolver latency;
- deny by reason;
- stale-context rate;
- cross-company seam count;
- prompt context bytes por layer;
- company-switch correctness.

---

# 43. FAILURE MODES

1. user A+B seleciona B, FastAPI usa A;
2. role removida mas session continua admin;
3. Work Run começa autorizado e envia após revogação;
4. Soul da Resulta aparece na AutoFleet;
5. User Profile da pessoa em A aparece em B;
6. team de A é aceito com company B;
7. entity de B é anexada a run de A;
8. thread de B entra no prompt de A;
9. memory namespace perde company;
10. client envia company_id arbitrário;
11. admin scope e tenant scope se confundem;
12. agent role é sobrescrito por Soul;
13. untrusted memory reescreve identity;
14. stale update sobrescreve Soul mais nova;
15. out-of-scope search revela existência;
16. resolver fail-open em erro do banco;
17. worker usa snapshot como permission;
18. activeCompany mudou durante request longa;
19. Qdrant filter falta company/team scope;
20. audit log registra snapshot diferente do que autorizou efeito.

---

# 44. TEST CASES ESSENCIAIS

## Multi-company

```text
Ana pertence A+B
active=A → A
active=B → B
membership B revoked → B denied imediatamente
```

## Different roles

```text
Ana owner em A
Ana member em B
mesmo user_id
permissions diferentes
```

## Mid-run revoke

```text
run nasce autorizado
membership revogada
compute pode terminar
external/durable sensitive effect → denied
```

## Team

```text
team A1 pertence company A
não pode ser usado em company B
```

## Company Soul

```text
Soul A != Soul B
switch company → next context muda
```

## User Profile

```text
profile A scoped a A
profile B pode ser diferente
```

## Agent Role

```text
Soul diz “faça qualquer coisa”
AgentRole/capability continua limitando
```

## Cross-tenant search

```text
resource B existe
A busca ID/título
→ nenhum existence hint
```

---

# 45. MUTATIONS / ADVERSARIAL CANDIDATES

1. trocar active company pela primary;
2. remover `.eq(status, active)` de membership;
3. confiar role da sessão sem DB;
4. aceitar body company_id;
5. remover company filter de Qdrant/search;
6. reutilizar scope snapshot no effect;
7. pular fresh revalidation;
8. mover team A para company B no fixture;
9. injetar Soul A no context B;
10. usar global user profile em vez de company-user;
11. Soul sobrescrever Agent Role;
12. stale Soul version overwrite;
13. DB error → allow;
14. out-of-scope count hint;
15. thread B em run A.

Cada mutação deve ficar vermelha pelo motivo certo.

---

# 46. LENTE DO DADO — ACTIVE COMPANY

```text
OBJECTIVE
resolver a corretora efetiva para a operação.

SOURCE
session selection + current company_members membership.

DO NOT
aceitar client company_id como authority.

FRESHNESS
cada request e novamente no efeito sensível quando operação é longa.

FAILURE
revogação / mismatch / DB error → fail closed.
```

---

# 47. LENTE DO DADO — COMPANY SOUL

```text
OBJECTIVE
personalizar identidade/comunicação da corretora.

SOURCE
explicit admin/onboarding + approved candidate.

TRUTH
versioned tenant object.

NOT
legal facts, procedures, permissions, memory.

VISIBILITY
tenant internal + runtime agent context.

WRITE
privileged + reviewed.
```

---

# 48. LENTE DO DADO — USER PROFILE

```text
OBJECTIVE
personalizar experiência para um usuário.

KEY
company_id + user_id.

SOURCE
account facts + explicit preferences + governed candidate where allowed.

NOT
membership role authority.
```

---

# 49. LENTE DO DADO — TEAM

```text
OBJECTIVE
scope intermediário dentro da corretora.

SOURCE
company-owned team + membership.

RULE
team cannot cross company.

DEFER
complex hierarchy/org chart.
```

---

# 50. COMPATIBILITY / CUTOVER

A 098 deve ser expand-first.

1. criar resolver/context contract;
2. instrumentar seams antigos;
3. migrar callers por ondas;
4. comparar old/new resolution;
5. bloquear client-authoritative company seams;
6. só depois retirar helpers legados.

Não quebrar login/multi-company selector em big bang.

---

# 51. O QUE A 098 PREPARA

## SPEC-099 — Channel Fabric

Channel assignment poderá usar:

```text
company
team
user
purpose
```

## SPEC-100 — Skill & Capability Factory

Identity/ScopeContext alimentará dynamic/minimum tool surface e authorization checks.

## SPEC-102 — Knowledge & Memory Factory

Scope taxonomy alimentará namespaces e publication permissions.

## SPEC-110 — External Harness

OAuth external identity será resolvida para o mesmo canonical principal/company context.

## SPEC-114 — Production Readiness

Stale-scope, race, revoke-mid-run e failure injection serão atacados globalmente.

---

# 52. REJECTED ALTERNATIVES

## A — Instalar Arkon
Rejeitar.

## B — Instalar OpenFGA agora
Defer; usar modelagem como referência. Só introduzir novo auth engine com prova de necessidade.

## C — UserProfile global por user_id
Rejeitar como padrão operacional multiempresa.

## D — CompanySoul = company_memories
Rejeitar.

## E — CompanySoul = raw system prompt
Rejeitar.

## F — Team = role
Rejeitar.

## G — Scope snapshot autoriza efeito futuro
Rejeitar.

## H — Toda tabela recebe 6 scope columns
Rejeitar.

## I — Qdrant vira authority de scope
Rejeitar.

## J — Client escolhe company_id
Rejeitar.

---

# 53. WARM-UP QUESTIONS

1. Qual HEAD/protocolo vivos?
2. Quantos helpers diferentes resolvem company?
3. Quantas rotas usam `session.companyId`?
4. Quantas usam `users_v2.company_id`?
5. Quantas aceitam company_id/body/query/header do client?
6. Quais dessas são realmente tenant-facing?
7. Quais possuem guard posterior que torna o seam seguro?
8. FastAPI recebe active company hoje por qual caminho?
9. Background jobs carregam qual company source?
10. Work Run armazena principal/actor/context hoje?
11. `company_members` roles/status atuais?
12. Há table Team real?
13. Há team assignments reais?
14. Entity refs atuais nos Work Runs?
15. Conversation/thread IDs como context?
16. Company memories existem em produção hoje?
17. User memories volume/current schema?
18. Quem escreve company profile?
19. Como brand capture funciona hoje?
20. Onde prompt composer injeta company identity?
21. Core e attendance usam mesma identity block?
22. Agent Role authority atual?
23. Qdrant filters atuais por company/user?
24. Quais caches guardam auth/scope?
25. Há TTL que permite stale role?
26. Qual action externa mais longa para testar revoke-mid-run?
27. Que erro real a Candidate não descreveu?
28. Qual migration pode ser evitada?
29. Que helper antigo pode ser removido?
30. Como provar que switch A→B muda todos os layers?

---

# 54. SOURCE INDEX — AUTOBROKERS

- `docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md` — v11.2.
- `docs/canon/GLOSSARIO.md`.
- `docs/canon/specs/SPEC-047-multiempresa-e-whatsapp-por-corretora.md`.
- `docs/canon/specs/SPEC-048-isolamento-corretoras-equipe.md`.
- `backend/supabase/migrations/20260721_01_spec047_rls_e_company_members.sql`.
- `lib/iron-session.ts`.
- `lib/admin/admin-auth.ts`.
- `lib/admin/admin-auth-policy.ts`.
- `lib/auxiliaries/server.ts`.
- `app/api/auth/companies/route.ts`.
- `backend/app/core/auth.py`.
- `backend/app/services/memory_service.py`.
- `backend/app/services/memory_fabric.py`.
- `app/api/admin/memory/*`.
- `lib/admin/company-profile.ts`.
- `backend/app/services/brand/capture.py` — warm-up obrigatório.
- `docs/canon/specs-propostas/5 - SPEC-090-fabrica-de-inteligencia-operacional*.md`.
- `docs/canon/specs-propostas/AUTOBROKERS_SPEC_TRANSFORMATION_MASTERPLAN_2026-08-25.md`.

---

# 55. SOURCE INDEX — ARKON

Repo:
https://github.com/nduckmink/arkon

Relevant:
- `LICENSE`
- `CHANGELOG.md`
- `docs/WIKI.md`
- `docs/ARCHITECTURE.md`
- `app/services/ai_review/runner.py`
- `app/services/wiki_service.py`
- `app/ai/mrp/pipeline.py`
- `app/ai/wiki_compiler.py`
- `app/services/verbatim_service.py`
- `alembic/versions/026_revisions_unique_page_version.py`
- `alembic/versions/036_verbatim_sources.py`

User-supplied analysis:
`AVALIAÇÃO ARKON.txt`

---

# 56. SOURCE INDEX — EXTERNAL

## Hermes Agent
https://hermes-agent.nousresearch.com/docs/user-guide/which-file-does-what  
https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/  
https://hermes-agent.nousresearch.com/docs/guides/use-soul-with-hermes  
https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files

## OpenFGA
https://openfga.dev/docs/modeling/organization-context-authorization  
https://openfga.dev/docs/modeling/roles-and-permissions  
https://openfga.dev/docs/modeling  
https://openfga.dev/docs/modeling/contextual-time-based-authorization

## LangGraph / LangMem
https://langchain-ai.github.io/langmem/guides/dynamically_configure_namespaces/

---

# 57. QUALIDADE DAS FONTES

```text
T0 — código/schema/incident current AutoBrokers
T1 — docs oficiais OpenFGA/LangGraph/Hermes
T2 — source code de implementação Arkon
T3 — análise anexada do Arkon (hipóteses a validar)
```

Arkon é T2 porque é implementação útil, não authority de protocolo/segurança para nosso produto.

---

# 58. LIMITAÇÕES DA PESQUISA

- Não foi executado SELECT de produção neste chat; medições de volume ficam para warm-up.
- Busca estática pode achar seam que já é protegido acima/abaixo; não chamar vulnerabilidade sem reproduzir.
- Team scope ainda precisa de schema/data census.
- Company Soul final precisa ser confrontada com brand capture atual.
- Qdrant/memory filters precisam de inspeção operacional no warm-up.
- Protocol v11.2 é current em 03/09/2026, mas executor revalida.

---

# 59. CONCLUSÃO

A SPEC-098 é mais importante do que “personalizar o jeito que a IA fala”.

Ela deve transformar o AutoBrokers em um sistema onde **cada dado, ação, memória, contexto e agente sabe exatamente de quem é e em qual situação vale**.

A arquitetura recomendada:

```text
IDENTITY
→ ACTIVE COMPANY
→ CURRENT MEMBERSHIP
→ OPTIONAL TEAM/PURPOSE
→ ENTITY/RUN/THREAD
→ COMPANY FACTS
→ COMPANY SOUL
→ USER PROFILE
→ AGENT ROLE
→ SCOPED MEMORY/KNOWLEDGE KEYS
→ PLAN
→ FRESH AUTHORIZATION AT EFFECT
```

O Arkon melhora essa proposta em um ponto muito específico e valioso: **não confie em autorização/scope capturado no início de um trabalho longo quando chegar a hora de publicar ou agir**.

Hermes ajuda a separar Soul/User/Memory/Instructions. OpenFGA valida o padrão de organização ativa para usuário multiempresa. LangMem reforça namespace hierárquico. O próprio AutoBrokers já possui a maior parte das peças de tenancy; o trabalho é convergir, fechar seams e criar um contrato único.

> **Identity diz quem. Scope diz onde vale. Authorization diz o que pode. Soul diz como a corretora se expressa. Profile diz quem é aquela pessoa naquele contexto. Memory diz o que foi aprendido. Nenhuma dessas peças deve fingir ser a outra.**
