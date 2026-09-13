# CANDIDATE SPEC-098 — CADA COISA SABE DE QUEM É
## Identity, Scope & Company Soul Fabric

**Produto:** AutoBrokers Intelligence OS  
**Status:** PROPOSTA INICIAL / CANDIDATE SPEC — o executor deve refutar e transformar na SPEC definitiva  
**Data:** 03/09/2026  
**HEAD auditado:** `67506906f0b8f60d89585878f15958a9ea438f09`  
**Protocolo obrigatório:** AutoBrokers AAA **v11.2**  
**Research Pack obrigatório:** `SPEC-098-cada-coisa-sabe-de-quem-e-RESEARCH-PACK.md`  
**SHA-256 do Research Pack:** `5c14993a691ee2844ed31f769c301d30ecf357b332d5f693f82eb22f2e5a9215`  
**Classificação:** CONVERGÊNCIA + FOUNDATION HARDENING + PRODUCT IDENTITY  
**Nota estratégica:** **100/100**

> **OBSERVAÇÃO DE GOVERNANÇA DA PROPOSTA**  
> Esta é uma proposta inicial para a SPEC-098. Serve de insumo e de inspiração para criarmos uma SPEC definitiva.  
> A SPEC definitiva pode ser modelada, melhorada e modificada em tudo que for melhor para o projeto.  
> Esta observação vale para todas as propostas de SPEC produzidas por esta Foundry.

---

# 0. ⛔ RP0 — DOIS DOCUMENTOS OU NÃO COMEÇA

Esta Candidate SPEC **não pode ser executada corretamente sozinha**.

```text
SPEC-098-cada-coisa-sabe-de-quem-e.md
+
SPEC-098-cada-coisa-sabe-de-quem-e-RESEARCH-PACK.md
=
PACOTE DE PROPOSTA DA SPEC-098
```

O Research Pack explica:
- current repo seams;
- incidentes 047/048;
- Next vs FastAPI;
- Glossário atual;
- Hermes;
- OpenFGA;
- LangGraph/LangMem;
- Arkon;
- licença Arkon;
- adoption/rejection ledger;
- Lentes do Dado;
- alternativas descartadas.

Antes do warm-up:

```text
RP0_SPEC_READ = YES
RP0_RESEARCH_PACK_READ = YES
RP0_RESEARCH_PACK_SHA256 = 5c14993a691ee2844ed31f769c301d30ecf357b332d5f693f82eb22f2e5a9215
RP0_SHA_MATCH = YES
RP0_CURRENT_HEAD = <sha vivo>
RP0_PROTOCOL = <versão viva>
RP0_STALE_PREMISES = [...]
RP0_ARKON_DECISION_LEDGER_ACK = YES
RP0_EXTERNAL_REFS_ACK = YES
```

**Falhou RP0 → não codificar.**

---

# 1. RESULTADO EM UMA FRASE

> **Fazer com que todo request, conversa, Work Run, memória, ferramenta e ação do AutoBrokers saiba de forma canônica quem está atuando, em qual corretora, com qual escopo e sobre qual entidade — enquanto Company Facts, Company Soul, User Profile e Agent Role permanecem peças distintas — e exigir autorização atual novamente no instante de qualquer efeito sensível.**

---

# 2. O TESTE DO PRODUTO

Um mesmo usuário pertence à Resulta e à AutoFleet.

Ele seleciona AutoFleet e pergunta ao Core:

> “Como estamos trabalhando renovação?”

O AutoBrokers precisa usar:

```text
AUTO FLEET
├── facts da AutoFleet
├── Soul da AutoFleet
├── role/profile daquele usuário NA AutoFleet
├── memory/knowledge permitido naquele scope
└── nenhum dado da Resulta
```

Depois ele inicia um trabalho autorizado.

Durante o Work Run, um administrador remove seu acesso.

O sistema pode concluir cálculo local, mas antes de enviar mensagem, publicar conhecimento, chamar portal, alterar dado ou produzir outro efeito sensível:

```text
FRESH AUTHORIZATION
→ acesso não existe mais
→ efeito bloqueado
→ run registra o motivo
```

Se um snapshot de 40 minutos atrás ainda der poder para agir, a SPEC falhou.

---

# 3. POR QUE AGORA

A sequência do Masterplan entra num trecho em que **scope passa a contaminar tudo**:

```text
098 Identity/Scope/Soul
→ 099 Channel Fabric
→ 100 Skills/Capabilities
→ 101 Connectors
→ 102 Knowledge/Memory
→ ...
→ 110 External Harness
```

Se 098 ficar vaga, cada SPEC futura inventará seu próprio conceito de:
- team;
- user;
- company;
- purpose;
- entity;
- namespace;
- role;
- permission.

A 098 deve impedir essa fragmentação agora.

---

# 4. ESTADO ATUAL OBSERVADO

## 4.1 Multi-company moderno já existe

`company_members` modela user↔company, role, owner e status. `activeCompanyId` existe na sessão.

## 4.2 Next já possui um seam bom

`requireCompanyMember()` consulta membership atual a cada request quando há empresa ativa.

## 4.3 FastAPI ainda possui semântica antiga

`get_current_company_id()` consulta `users_v2.company_id`, a empresa primária.

## 4.4 Já houve incidente real

SPEC-047/048 documentaram que ignorar active company permitiu operação contra a empresa primária errada.

## 4.5 Há seams heterogêneos

Busca atual ainda encontra `session.companyId`, `users_v2.company_id` e ao menos um caminho candidate que prioriza `body.companyId`.

Isto exige censo/reprodução, não acusação automática de vulnerabilidade.

## 4.6 Scope canônico ainda termina em GLOBAL/COMPANY/USER

O Glossário não possui Team/Entity/Run/Thread como hierarchy transversal.

## 4.7 Memory existe, mas não substitui identidade

`company_memories`, `user_memories`, MemoryService/Fabric existem. A 098 não cria nova memória.

---

# 5. PROBLEMA REAL

O sistema possui **peças corretas localmente**, mas ainda não possui um contrato universal que responda:

```text
principal
active company
membership
role
team
purpose
entity
run
thread
company identity
user profile
agent role
memory namespace
fresh authorization
```

Sem isso surgem dois tipos de erro:

## Erro de segurança

Dado/ação no tenant ou scope errado.

## Erro de produto

Resposta com a identidade, memória, estilo ou contexto errado mesmo sem um leak explícito.

---

# 6. FRONTEIRA DA SPEC

A 098 entrega:

1. canonical identity/scope ontology;
2. ScopeContext contract;
3. active-company convergence Next/FastAPI/background;
4. typed Team/Entity/Run/Thread scopes mínimos;
5. Fresh Effect Authorization Gate;
6. audit snapshot vs permission distinction;
7. Company Facts vs Company Soul;
8. User Profile company-scoped;
9. Agent Role separation;
10. scoped Context Composer contract;
11. security/no-existence-leak rules;
12. UI/admin mínimo para Soul/Profile quando necessário;
13. observability, mutation, E2E e cutover.

---

# 7. FORA DE ESCOPO

Não fazer nesta SPEC:
- reescrever Auth inteira;
- instalar Arkon;
- instalar OpenFGA sem prova;
- criar authorization DSL enterprise;
- criar org chart/HR system;
- reimplementar Memory Factory da 102;
- dynamic MCP tool catalog da 100/110;
- Channel Fabric da 099;
- Trust Preflight completo da 107;
- failure-injection global da 114;
- novo cognitive runtime.

---

# 8. REFERÊNCIAS E O QUE FOI APROVEITADO

## AutoBrokers 047/048

**ADOPT:** active company + DB membership atual por request.

## Hermes Agent

**ADAPT:** separar Soul, User Profile, Memory e project/agent instructions por função.

## OpenFGA

**ADOPT PATTERN:** usuário multi-organização só tem acesso no contexto da organização ativa e sob relações/roles válidas.

## LangGraph/LangMem

**ADAPT:** namespaces hierárquicos resolvidos em runtime para memory isolation.

## Arkon

**ADOPT/ADAPT:** fresh scope/authorization antes de commit/efeito e stale-result guards.

**REJECT:** GLOBAL/DEPARTMENT como nossa hierarchy, Arkon como dependência e código Arkon no SaaS.

Leitura detalhada e URLs: Research Pack.

---

# 9. DECISÕES CONGELADAS

## D-098-01 — Um único contrato lógico de ScopeContext

Next, FastAPI, Work OS e futuras interfaces externas falam a mesma semântica, ainda que tenham adapters de linguagem diferentes.

## D-098-02 — Company é server-derived

Tenant-facing client nunca transforma `company_id` enviado em authority.

## D-098-03 — Active company exige membership atual

Selecionar uma company na sessão não basta se o vínculo foi revogado.

## D-098-04 — Snapshot é auditoria, não autorização

Work Run pode guardar o contexto inicial, mas efeito sensível revalida.

## D-098-05 — Team nunca atravessa Company

Team membership depende de company membership.

## D-098-06 — Entity/Run/Thread sempre descendem de Company

Nenhum child ref troca tenant.

## D-098-07 — Company Facts ≠ Company Soul

Facts são verificáveis; Soul é identidade comportamental/comunicacional.

## D-098-08 — User Profile ≠ User Memory

Profile operacional é `company + user`; memory continua governada pela Memory Fabric.

## D-098-09 — Agent Role ≠ Company Soul

Soul não muda capacidade, público ou limites funcionais do agente.

## D-098-10 — Company Soul não é raw system prompt

Preferir estrutura versionada + renderer bounded.

## D-098-11 — Auto-inference propõe, não sobrescreve Soul

090/brand capture pode gerar candidate; publicação exige caminho governado.

## D-098-12 — Cross-tenant existence hint é proibido

Nem count, título ou “há algo parecido” fora do tenant.

## D-098-13 — Nenhum framework externo vira nova authority

Arkon/OpenFGA/LangMem são referências, salvo prova extraordinária durante warm-up.

---

# 10. ONTOLOGIA — PRINCIPAL

**Principal** é quem está fazendo/solicitando a operação.

Candidate actor types a reconciliar com o Glossário e Work Events:

```text
user
agent
subagent
auxiliary / worker
system
platform_admin
external_client   ← futuro 110
```

Não criar user/agent duplicado. Criar uma referência canônica:

```text
canonical_actor_ref
actor_type
user_id?
agent_id?
```

---

# 11. ONTOLOGIA — SCOPE

Taxonomia lógica:

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

Nem todo objeto precisa percorrer a árvore inteira.

---

# 12. DATA SCOPE ≠ AUTHORIZATION ≠ CREDENTIAL ≠ MEMORY NAMESPACE

## Data Scope
Onde o dado vale.

## Authorization Scope
O que o principal pode fazer sobre um recurso.

## Credential Scope
Quem possui a credencial: platform/company/user.

## Memory Namespace
Onde um fato/memória é pesquisável.

**Mesmos IDs podem participar das quatro dimensões. As dimensões não podem ser colapsadas.**

---

# 13. SCOPE CONTEXT — CONTRATO SEMÂNTICO

Candidate:

```text
ScopeContext
  principal
    actor_type
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
    role?

  purpose?

  entity?
    entity_type
    entity_id

  run?
    work_run_id

  thread?
    conversation_id?
    thread_id?

  resolved_at
  source
  scope_fingerprint?
```

**ScopeContext descreve contexto. Ele não é a decisão final de autorização.**

---

# 14. ACTIVE COMPANY RESOLVER

Contrato:

```text
AUTHENTICATED PRINCIPAL
→ requested/selected active company from trusted server session/context
→ current company_members lookup
→ status active?
→ role / is_owner current
→ company status current if required
→ ScopeContext.company
```

Fallback à empresa primária só é aceitável onde o produto explicitamente define “nenhuma empresa ativa selecionada”.

---

# 15. NEXT ↔ FASTAPI CONVERGENCE

A implementação definitiva deve escolher um seam que garanta semântica idêntica.

Opções a avaliar no warm-up:

### A — Resolver compartilhado via DB/RPC

Pró: uma única policy logic.  
Contra: acoplamento/latência e contexto de sessão.

### B — Adapters TS/Python sobre contrato + fixtures canônicas

Pró: simples e local.  
Contra: risco de drift.

### C — Server-minted short-lived Scope Envelope

Next resolve contexto e envia envelope assinado a FastAPI; FastAPI valida envelope e **ainda revalida no efeito sensível**.

Pró: context propagation forte.  
Contra: token/key/expiry complexity.

### D — Backend resolve tudo de uma auth identity única

Pode ser melhor se arquitetura atual suportar sem duplicar sessão.

**A Candidate não congela a opção sem o censo vivo. Congela a semântica.**

---

# 16. FRESH EFFECT AUTHORIZATION GATE

Inspirado e validado pelo padrão Arkon, verticalizado para AutoBrokers.

Antes de efeito sensível:

```text
RELOAD principal status
RELOAD current company membership
RELOAD team membership if required
RELOAD target resource ownership/company
RELOAD capability/role requirement
COMPARE target with ScopeContext intent
ALLOW or DENY
WRITE audit evidence
```

Efeitos sensíveis incluem, conforme surface:
- mensagem externa;
- portal/connector action;
- mutation de cliente/apólice/case;
- knowledge/memory/Soul publication;
- approval execution;
- Artifact external share;
- billing;
- admin config.

---

# 17. AUDIT SNAPSHOT VS LIVE AUTHORIZATION

Work Run pode persistir:

```text
principal_snapshot
scope_snapshot
role_snapshot
scope_fingerprint
requested_at
```

Uso:
- auditoria;
- replay;
- explicação “com que contexto este trabalho começou?”.

Não uso:
- conceder permission no futuro.

---

# 18. STALE CONTEXT

O sistema precisa detectar quando o mundo mudou entre plan e effect.

Mecanismos candidatos:
- membership.updated_at;
- scope fingerprint;
- auth epoch;
- resource version;
- expected version;
- row/transaction lock em critical section curta.

O mecanismo final depende do tipo de recurso.

---

# 19. TEAM — MÍNIMO NECESSÁRIO

BLOCO 0 primeiro verifica schema atual.

Se faltar objeto canônico, candidate mínimo:

```text
teams
  id
  company_id
  name
  status

team_members
  company_id
  team_id
  user_id
  role?
  status
```

Invariantes:
1. Team pertence a uma company.
2. Team membership nunca concede company membership.
3. Só company member ativo pode ser team member ativo.
4. Revogar company membership invalida Team access.
5. Team de A nunca entra no context B.

---

# 20. ENTITY / RUN / THREAD

Typed refs, não ACL genérica infinita.

Candidate:

```text
ENTITY
client · policy · case · claim · renewal · other governed entity

RUN
work_run_id

THREAD
conversation_id / LangGraph thread
```

Cada ref é validada contra company ancestry.

---

# 21. PURPOSE

ScopeContext pode carregar finalidade:

```text
broker_chat
attendance
claims_shadow
reporting
admin_config
connector_execution
billing
external_harness
```

Purpose ajuda 099/100/110 a selecionar canais/capabilities/tool surface, mas **não substitui Capability/authorization**.

---

# 22. COMPANY FACTS

Facts são dados verificáveis.

Candidate sources:
- companies;
- onboarding;
- InfoCap/providers;
- approved profile edits;
- connector facts.

Company Facts podem ser consumidos por UI e Context Composer, sempre com provenance/freshness adequada.

---

# 23. COMPANY SOUL

## Objetivo

Representar a identidade de comunicação/relacionamento da corretora.

Candidate semantic schema:

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

## Soul não contém

- legal rules;
- coverage facts;
- insurer procedure;
- Skill;
- security policy;
- tool permissions;
- API keys;
- raw system prompt.

---

# 24. COMPANY SOUL — LIFECYCLE

Sources permitidas:

1. edição explícita por admin autorizado;
2. onboarding guiado;
3. candidate da 090;
4. brand capture como sugestão.

Lifecycle mínimo:

```text
candidate
→ review
→ approve
→ active version
→ supersede
```

A 102 pode depois generalizar candidate/review/publication. A 098 precisa apenas garantir que Soul não seja sobrescrita silenciosamente.

---

# 25. USER PROFILE

User Profile é contexto da pessoa **dentro da corretora**.

Candidate:

```text
company_id
user_id
display_name
language
response_preferences
communication_preferences
responsibilities[]
team_refs[]
profile_version
source
updated_at
```

Não duplicar membership role como campo editável de autorização.

---

# 26. USER PROFILE VS MEMORY

```text
PROFILE
curado / declarado / identidade operacional

MEMORY
aprendido ao longo do uso
```

A Memory Fabric continua authority de memória. 098 só entrega scope keys/contract para 102.

---

# 27. AGENT ROLE

Já existe como conceito canônico.

Agent Role define:
- função;
- audience;
- boundaries;
- objetivo.

Company Soul apenas estiliza/complementa dentro desses limites.

Invariante:

> **Nenhum texto de Soul/Profile/Memory amplia Capability, muda audience ou transforma um subagent read-only em writer.**

---

# 28. CONTEXT PRECEDENCE

Candidate:

```text
1 PLATFORM INVARIANTS / SAFETY
2 AGENT ROLE / AUDIENCE / BOUNDARIES
3 COMPANY FACTS
4 COMPANY SOUL
5 TEAM CONTEXT
6 USER PROFILE
7 ENTITY CONTEXT
8 RUN CONTEXT
9 THREAD WORKING CONTEXT
10 RETRIEVED MEMORY / KNOWLEDGE
```

Precedência mais baixa pode personalizar; nunca ampliar permissão ou quebrar regra superior.

---

# 29. CONTEXT COMPOSER

Um seam lógico em volta de Smith:

```text
resolve ScopeContext
→ load typed identity layers
→ select bounded sections
→ pass namespace keys to retrieval
→ render context for the target AgentRole
```

Não criar novo LLM router/runtime.

---

# 30. CONTEXT DIET

Não injetar todas as camadas integralmente.

Always-small:

```text
principal/company refs
Agent Role
Company Soul summary
critical Company Facts
```

On-demand:

```text
team details
entity facts
full company facts
user memories
knowledge
run history
thread history
```

Medir tokens/TTFT antes/depois.

---

# 31. MEMORY / RAG SCOPE CONTRACT

A 098 não refatora 102 antecipadamente.

Entrega apenas os identifiers e invariantes necessários:

```text
GLOBAL KNOWLEDGE
COMPANY MEMORY
TEAM MEMORY future/when justified
USER MEMORY within company
ENTITY/RUN/THREAD contextual retrieval
```

Qdrant continua derived index; Supabase/authorities continuam truth.

---

# 32. NO EXISTENCE LEAK

Cross-tenant unauthorized lookup deve resultar em comportamento indistinguível de inexistência conforme surface segura.

Proibido:

```text
“há 3 resultados em outra corretora”
“existe memória parecida fora do seu acesso”
“há um case com esse protocolo, mas você não pode vê-lo”
```

---

# 33. SOUL / PROFILE POISONING

Riscos:
- documento externo tenta redefinir Soul;
- usuário comum grava instruction maliciosa no profile;
- memory candidate vira system instruction;
- Soul tenta ampliar capability.

Defesas:
- typed fields;
- write authorization;
- candidate/review;
- bounded renderer;
- no raw untrusted text em privileged instruction layer;
- safety/AgentRole/capability sempre superiores.

SPEC-107 aprofundará Trust Gate.

---

# 34. ARKON — DECISÃO ESPECÍFICA

A 098 incorpora **somente** o que gera ganho específico:

### APROVADO

```text
Fresh Scope Resolution at Effect
Stale Result Protection
Concurrency Guard onde invariant exigir
```

### NÃO APROVADO

```text
Arkon como dependência
Department como nosso Team/Tenant
Arkon RBAC como authority
copy/paste de código
out-of-scope existence hints
```

A licença PolyForm Internal Use é mais uma razão para manter Arkon como referência, não componente do SaaS.

---

# 35. API / INTERNAL CONTRACTS — CANDIDATES

Interfaces semânticas, não nomes obrigatórios:

```text
resolve_scope_context(principal, trusted_active_company, purpose?, entity?, run?, thread?)

assert_resource_in_scope(scope_context, resource_ref)

check_capability(scope_context, capability, resource?)

revalidate_before_effect(scope_context, effect, resource?)

load_company_identity(scope_context)

load_user_profile(scope_context)

compose_identity_context(scope_context, agent_role)
```

Erros devem ser tipados e fail-closed.

---

# 36. UI / PRODUCT SURFACES

## Personalização → Corretora

Separar visualmente:

```text
DADOS DA CORRETORA
facts

JEITO DE ATENDER
Company Soul

EQUIPE
members / teams
```

## User settings/profile

Preferências pessoais dentro da company ativa.

## Company switcher

Ao trocar empresa, UI deve:
- invalidar caches scoped;
- atualizar header/context;
- recarregar profile/Soul;
- impedir tela antiga continuar mutando tenant anterior.

---

# 37. COMPANY SWITCH — ATOMICIDADE DE EXPERIÊNCIA

Switch A→B não é apenas trocar label.

Após sucesso:

```text
activeCompany session updated
→ scoped caches invalidated
→ queries cancelled/reloaded
→ current Case/Conversation from A closed or guarded
→ context composer B
→ user profile B
→ company soul B
```

Mutação disparada com tela A stale depois do switch precisa ser rejeitada pelo servidor.

---

# 38. BACKGROUND WORK

Todo job longo precisa carregar:

```text
intent / target
company_id
principal/actor snapshot
scope snapshot
resource refs
requested capability/effect
```

Mas writer sensível usa fresh gate no efeito.

Jobs system-owned sem user principal usam actor system + company scope explícito e capability própria.

---

# 39. CONCURRENCY STRATEGY

Escolher por invariant:

```text
UNIQUE       → impossibilidade estrutural
VERSION      → stale edits
IDEMPOTENCY  → duplicate effects
ROW LOCK     → critical section curta
ADVISORY LOCK→ lock lógico específico quando row lock não encaixa
LEASE        → worker ownership
```

Não adotar advisory lock em todo lugar só porque Arkon usa.

---

# 40. OBSERVABILITY

Events candidates:

```text
scope.resolved
scope.denied
scope.stale_detected
scope.changed_during_run
authz.revalidated
authz.revoked_mid_run
context.cross_scope_blocked
company_soul.loaded
company_soul.version_changed
user_profile.loaded
```

Metrics:
- resolver p50/p95;
- deny reason rate;
- stale-context rate;
- cross-company seam count;
- context bytes por layer;
- company switch correctness;
- fresh gate latency.

Logs sem PII/secrets.

---

# 41. SECURITY INVARIANTS

1. Client company id não concede access.
2. Membership revogada vale imediatamente para efeitos.
3. DB/auth failure não vira allow.
4. Team pertence à company.
5. Resource company precisa bater com ScopeContext.
6. Scope snapshot não é capability token.
7. Cross-tenant existence não vaza.
8. Soul/Profile não aumenta permission.
9. Qdrant/search sempre recebe filtro de tenant apropriado.
10. Service-role nunca transforma ausência de RLS em ausência de application guard.
11. External client futuro nunca escolhe tenant livremente.
12. Admin platform e tenant principal são identities distintas.

---

# 42. FAILURE MODES

1. A+B, active B, FastAPI usa A.
2. Role revogada, session ainda admin.
3. Work Run envia depois de revogação.
4. Soul A aparece em B.
5. Profile A aparece em B.
6. Team A usado em B.
7. Entity B anexada a Run A.
8. Thread B entra no prompt A.
9. Memory namespace sem company.
10. Body companyId é tratado como authority.
11. Admin/tenant contexts se confundem.
12. AgentRole é sobrescrito por Soul.
13. Memory injection vira identity instruction.
14. Stale edit sobrescreve Soul nova.
15. Search revela existence cross-tenant.
16. Resolver fail-open.
17. Snapshot vira autorização eterna.
18. Active company muda durante operação longa.
19. Qdrant filter incompleto.
20. Audit snapshot diverge do contexto realmente autorizado.

---

# 43. IMPLEMENTATION BLOCKS — CANDIDATE

## BLOCO 0 — Identity/Scope Seam Census

Mapear todos os seams TS/Python/background que resolvem user/company/role/team/resource. Reproduzir os candidates perigosos e fechar/descartar pendências tocadas.

## BLOCO A — Canonical Principal + ScopeContext

Types, resolver semantics, invariants e fixtures canônicas.

## BLOCO B — Active Company Convergence

Next/FastAPI/background recebem a mesma company semantics. Migrar seams mais críticos primeiro.

## BLOCO C — Team / Entity / Run / Thread Scope

Adicionar somente o mínimo provado pelo censo.

## BLOCO D — Fresh Effect Authorization

Snapshot auditável + revalidation atual em ações sensíveis; revoke-mid-run.

## BLOCO E — Company Facts vs Company Soul

Data model/versioning, renderer e UI de Personalização.

## BLOCO F — User Profile + Agent Role

Profile company-scoped e AgentRole precedence.

## BLOCO G — Context Composer

Layered/bounded composition para Smith e namespace keys para memory/retrieval.

## BLOCO H — Scope Guards em Memory/RAG/Work

Não refatorar 102; garantir que context/filters existentes respeitem o contract mínimo.

## BLOCO I — Observability / Company Switch

Cache invalidation, audit, stale context telemetry.

## BLOCO J — Cutover / Legacy Seam Drain

Substituir helpers antigos, documentar exceções restantes e impedir novos seams opacos.

---

# 44. AAA v11.2 — EXECUTION CARD INICIAL

```text
OUTCOME .............. identidade/scope coerentes + Soul/Profile separados + fresh authz
RISCO ................ 8 candidato
SUPERFÍCIE ........... 3
PISO APLICADO ........ auth · company_id · possível migration → CRÍTICO
NÍVEL ................ CRÍTICO
UNIDADES ............. 10 candidates; recompor após censo
COESÃO ............... ScopeContext + active company + fresh gate formam backbone
PARALELISMO REAL ..... só adapters/UI disjuntos após contratos
TIME ................. v11.2: investigador + desenhista + builders necessários + painel 3 lentes + red team + integrador + juiz fresco
REFERÊNCIA ........... 047/048 + current auth + Hermes/OpenFGA/LangMem + Arkon
GATES ................ G0–G16
O ELO ................ active context correto TEM que chegar ao effect; provar revoke/switch
ORÇAMENTO ............. v11.2: economizar tokens/lentes, nunca mutation/security proof
```

Executor recalcula após BLOCO 0.

---

# 45. GATES

- **G0 RP0:** dois docs corretos.
- **G1 Current Principal:** usuário/agent ainda válido.
- **G2 Active Company:** selected context + current membership.
- **G3 No Client Authority:** body/query/header tenant id não concede acesso.
- **G4 Next/FastAPI Parity:** mesmos fixtures → mesma company/role decision.
- **G5 Revocation:** acesso removido impacta próximo efeito.
- **G6 Team Containment:** team nunca cruza company.
- **G7 Entity Ancestry:** entity/run/thread precisam pertencer ao scope.
- **G8 Snapshot ≠ Permission:** stale snapshot não autoriza.
- **G9 Company Soul Isolation:** A nunca aparece em B.
- **G10 User Profile Isolation:** company-user correto.
- **G11 AgentRole Supremacy:** Soul/Profile não amplia poder.
- **G12 Memory/RAG Scope:** retrieval respeita identifiers.
- **G13 No Existence Leak:** cross-tenant zero hints.
- **G14 Stale Update:** versões concorrentes não sobrescrevem silenciosamente.
- **G15 Context Budget:** identidade não destrói TTFT/context budget.
- **G16 Company Switch:** caches/context anteriores invalidados corretamente.

---

# 46. MUTATION MATRIX

1. substituir active company pela primary;
2. remover membership status active;
3. usar session role sem DB;
4. aceitar client company id;
5. pular fresh effect gate;
6. usar scope snapshot como allow;
7. team de A aceito em B;
8. entity B em run A;
9. Soul A renderizada em B;
10. globalizar UserProfile;
11. Soul sobrescrever AgentRole;
12. remover Qdrant company filter;
13. DB auth error → allow;
14. devolver out-of-scope count;
15. stale Soul write vence version atual;
16. switch company mantém cache A;
17. FastAPI ignora active company;
18. background system job sem explicit company.

Cada uma precisa matar um teste que passa no controle.

---

# 47. E2E

## E2E-1 — Multi-company switch

User A+B → active A → pergunta/consulta A → switch B → B; zero residual A.

## E2E-2 — Different roles

Mesmo user owner A/member B → capability decisions distintas.

## E2E-3 — Revoke mid-run

Start autorizado → revoke → effect denied → Work Event explains.

## E2E-4 — Company Soul

Soul Resulta e AutoFleet diferentes → switch muda comportamento esperado, nunca capability.

## E2E-5 — User Profile

Mesmo user com profiles A/B distintos → correct company profile loaded.

## E2E-6 — Team

Team A resource não é acessível no B context.

## E2E-7 — Entity/Run/Thread

Case/conversation B não entra em Work Run A.

## E2E-8 — FastAPI parity

Request via Next e backend internal route resolve same company/role outcome.

## E2E-9 — Search

Tenant A busca known resource B → no existence hint.

## E2E-10 — Stale Soul edit

Two editors/worker old version → stale write rejected/merged by explicit policy, not silent overwrite.

---

# 48. RED TEAM

Missão:

> **Fazer o AutoBrokers operar com a identidade certa na tela e a company errada no efeito.**

Atacar:
- stale session;
- revoked membership;
- company switch durante request;
- body company_id;
- confused deputy internal call;
- service-role bypass;
- stale Work Run;
- team/resource mismatch;
- Qdrant filter omission;
- Soul prompt injection;
- user profile poisoning;
- cross-tenant known UUID;
- cache key sem company;
- external job replay.

---

# 49. CONTROLS OBRIGATÓRIOS

Pares mínimos com veredito oposto:

```text
active A + member A → allow
active A + no membership A → deny

run started + still authorized → effect allow
run started + access revoked → effect deny

Soul A in context A → visible
Soul A in context B → absent

resource same company → resolvable
resource other company → indistinguishable from unavailable
```

---

# 50. PERFORMANCE / SLO

Medir:
- Scope resolver p50/p95;
- Fresh Effect Gate p95;
- Company switch→ready latency;
- Context Composer token/latency delta;
- extra DB queries/request.

Evitar “revalidar tudo toda hora” sem necessidade. Segurança atual no ponto de efeito; caching seguro para read context quando versionado/short-lived.

---

# 51. MIGRATION / CUTOVER

Princípio expand-first:

1. instrumentar seams;
2. criar types/resolver;
3. implementar fixtures/parity tests;
4. migrar critical writes/effects;
5. migrar reads;
6. adicionar Team/Soul/Profile schema somente se necessário;
7. monitorar divergência old/new;
8. remover helpers legacy comprovadamente mortos.

Nenhum big bang de auth.

---

# 52. ROLLBACK

Se resolver novo falhar:
- feature/call-site cutover pode voltar ao seam antigo apenas em superfícies que não reabram leak conhecido;
- schema aditivo permanece;
- Fresh Effect Gate pode fail closed, não ser desligado para “fazer passar” ação sensível;
- Soul/Profile UI pode ser ocultada sem perder dados versionados.

---

# 53. SUCCESS METRICS

Produto:
- company switch correct rate;
- identity mismatch reports;
- context personalization correctness;
- tenant-specific Soul usage;
- user profile usage.

Security/engineering:
- number of scope seams before/after;
- routes client-authoritative company before/after;
- Next/FastAPI parity;
- revoke-mid-run denial rate;
- stale scope detections;
- cross-tenant test coverage;
- resolver/fresh-gate p95.

---

# 54. DEFINITION OF DONE

- [ ] RP0 verde.
- [ ] Current HEAD/protocol revalidado.
- [ ] Identity/Scope Seam Census produzido.
- [ ] Dangerous candidates reproduced or cleared.
- [ ] Canonical Principal/ScopeContext exists.
- [ ] Active company semantics equal across critical Next/FastAPI/background paths.
- [ ] Client cannot choose tenant authority.
- [ ] Team/Entity/Run/Thread contract defined minimally.
- [ ] Fresh Effect Gate proven.
- [ ] Revoke-mid-run E2E green.
- [ ] Scope snapshot explicitly non-authoritative.
- [ ] Company Facts and Soul separated.
- [ ] Company Soul versioned/governed.
- [ ] User Profile company-scoped.
- [ ] AgentRole cannot be overridden by lower context.
- [ ] Context Composer bounded and measured.
- [ ] Memory/RAG receives correct scope keys.
- [ ] No cross-tenant existence hint.
- [ ] Stale update race covered.
- [ ] Company switch invalidates scoped caches.
- [ ] Mutations red.
- [ ] Red team executed.
- [ ] Security/data judge rebuilds tenant cases.
- [ ] Execution report + push + registry.

---

# 55. PENDÊNCIAS CONSCIENTEMENTE ADIADAS

- full ReBAC engine;
- custom roles builder;
- complex team hierarchy;
- cross-team resource sharing UI;
- advanced field-level permissions;
- dynamic tool catalog (100);
- generic candidate lifecycle (102);
- external OAuth principal (110);
- global stale-worker sweep/failure injection (114).

---

# 56. WARM-UP QUESTIONS AO CLAUDE CODE

1. Qual é o HEAD atual e a versão do protocolo?
2. Quantos seams diferentes resolvem company hoje?
3. Liste todos os tenant-facing paths que aceitam company id do client e prove se são seguros ou defeituosos.
4. Quantos paths usam `session.companyId` diretamente?
5. Quantos FastAPI paths usam `get_current_company_id`?
6. Como activeCompany chega ao backend hoje?
7. Existe um ScopeContext equivalente já pronto?
8. Quais roles reais existem em company_members?
9. Team table existe? Quantos teams/members?
10. Que resource hoje precisa Team scope primeiro?
11. Quais entity refs existem em Work Runs?
12. Work Run guarda actor/principal hoje?
13. Quais ações sensíveis já fazem revalidation no effect?
14. Qual ação longa é melhor golden case para revoke-mid-run?
15. Company Soul já existe sob outro nome?
16. Brand capture escreve o quê e onde?
17. Como company identity entra no prompt hoje?
18. User Profile é carregado hoje?
19. Company memories e user memories atuais têm quais filtros?
20. Qdrant queries recebem company/user filters em todos os seams?
21. Há cache key sem company?
22. Que seam a Candidate julgou errado?
23. Qual migration pode ser evitada?
24. Qual mecanismo concurrency é apropriado para Soul: optimistic version, row lock ou outro?
25. Qual defeito real a SPEC não menciona?

---

# 57. RESEARCH PACK

Leitura obrigatória:

`SPEC-098-cada-coisa-sabe-de-quem-e-RESEARCH-PACK.md`

SHA-256:

`5c14993a691ee2844ed31f769c301d30ecf357b332d5f693f82eb22f2e5a9215`

---

# 58. NEXT — SPEC-099: CHANNEL FABRIC v2 — PLANO PARA O FOUNDER REVISAR

A 099 deve começar **depois** que a 098 definir a linguagem de scope, porque Channel não pode inventar sua própria tenancy.

## Problema a investigar

Hoje WhatsApp é a superfície principal, mas o produto precisa evoluir para conexões/canais tenant-owned que possam ser atribuídos por propósito e, quando fizer sentido, por team/user.

Candidate ontology:

```text
ChannelConnection
  company
  channel_type
  provider
  credential/connection ref
  assignments[]
  purpose[]
  health
  inbound/outbound capability
  audit
```

## O que a 099 deverá analisar

1. WhatsApp atual: Evolution API, Meta oficial e seus seams.
2. Multi-WhatsApp por corretora.
3. Qual número/canal pertence a qual agent/purpose/team.
4. Email inbound/outbound.
5. Slack/Teams para operação interna.
6. Webchat.
7. Meta Ads/lead source — sem confundir marketing source com conversation channel.
8. Channel ownership vs credential ownership.
9. Routing inbound para correto AgentRole/Team/User.
10. Human takeover e Conversation continuity.
11. consent/opt-out/templates/janelas onde aplicável.
12. health/reconnect/rotation.
13. message identity/dedupe/idempotency.
14. attachments.
15. delivery status.
16. channel-specific capabilities.
17. inbound content → candidate com ACL apropriada, nunca memory global automática.
18. audit e privacy.
19. fallback channel.
20. provider-agnostic contract sem abstração vazia.

## Referências externas previstas

- WhatsApp Cloud API / Meta docs;
- Evolution API current;
- Slack/Teams platform auth/event models;
- Twilio/Front/Intercom apenas para patterns quando úteis;
- SPEC-047 multiempresa/WhatsApp;
- SPEC-092 WhatsApp forms;
- SPEC-098 ScopeContext.

## Decisões que eu recomendo antes da 099

**R1.** `ChannelConnection` pertence sempre a uma company; assignment para team/user não muda ownership.  
**R2.** Channel e Connector não viram a mesma entidade: channel é superfície de comunicação; connector é conexão com sistema externo.  
**R3.** Um WhatsApp pode ter um purpose principal e rules de routing, mas evitar “um Agent por número” hard-coded.  
**R4.** Não construir omnichannel enterprise inteiro de uma vez; primeiro contract + WhatsApp excelente + extensibilidade provada com um segundo channel.  
**R5.** Mensagem externa sempre passa pelos guards de ownership/authorization existentes; Channel Fabric não cria bypass.

## Perguntas para você antes de eu escrever a Candidate 099

1. Você quer que a 099 já implemente **e-mail real**, ou prefere WhatsApp completo + contract de e-mail com uma integração mínima de prova?
2. Para pilotos, cada funcionária continuará com seu próprio WhatsApp pareado, ou a visão é migrar progressivamente para números/canais da corretora?
3. Você quer Teams/Slack já como canais **de conversa com o AutoBrokers**, ou inicialmente apenas notificações/operação interna?
4. Você concorda que Meta Ads seja tratado principalmente como **origem/atribuição de lead**, e não automaticamente como um channel equivalente a WhatsApp?
5. Quer permitir que um mesmo número WhatsApp atenda múltiplos purposes/agentes por routing, ou prefere um purpose dominante por conexão?

Essas respostas podem alterar a fronteira da 099 antes da pesquisa definitiva.

---

# 59. LEI FINAL DA 098

> **Identidade diz quem. Scope diz onde vale. Authorization diz o que pode. Soul diz como a corretora se expressa. Profile diz quem é aquela pessoa naquele contexto. Memory diz o que foi aprendido. O AutoBrokers só será seguro e realmente inteligente quando nenhuma dessas peças fingir ser a outra.**
