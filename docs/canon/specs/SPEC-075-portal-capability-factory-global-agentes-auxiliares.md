---
status: "PRONTA PARA EXECUÇÃO — solicitada pelo Founder em 15/08/2026"
spec: "SPEC-075"
titulo: "Portal Capability Factory Global — Portal Worker como plataforma reutilizável para Agentes, Auxiliares, Rotinas e Work Runs"
criada_em: "2026-08-15"
branch_sugerida: "feat/spec075-portal-capability-factory"
repo: "Amandico100/AutoBrokers-Intelligence-OS"
baseline_main_observada: "0ffcbed44ba012d9a41e23823729837b6defd076"
supabase_producao: "dcajcvlzcjbmyapmklil"
depende_de: "SPEC-073 verde + contratos da SPEC-074 incorporados; execução deve respeitar o estado real quando a branch for criada"
deploy_esperado: "smith-api + smith-worker + portal-worker; web somente se a matriz/readiness tenant-facing for alterada"
migration_esperada: "1 migration expand-only mínima para lineage/prioridade de portal_jobs, se o censo vivo confirmar que as colunas ainda não existem"
---

# SPEC-075 — Portal Capability Factory Global
## Portal Worker como plataforma reutilizável para Agentes, Auxiliares, Rotinas e Work Runs

> **Resultado desta SPEC:** entrar em portal deixa de ser uma habilidade artesanal presa a um Auxiliar, a um Agent ou a uma função específica. O AutoBrokers passa a ter **UMA plataforma governada de execução externa**, reutilizável por qualquer agente, Auxiliar, Rotina ou Work Run que possua a Skill, a Capability, a conexão e a autorização corretas.
>
> **Regra de ouro:** esta SPEC não cria outro Portal Worker, outro Tool Gateway, outro Skill Registry, outro Work Run, outro Factory, outro Vault nem outro catálogo de portais. Ela **liga as peças canônicas que já existem** e transforma o `portal-worker` existente em provider real do Work OS.

---

# 0. A decisão arquitetural — o que estamos construindo, em uma frase

Hoje o AutoBrokers já possui duas provas de valor fortes no mesmo motor:

```text
COBRANÇA FEITA
  → entra em vários portais autenticados
  → localiza inadimplentes
  → obtém boletos
  → consolida e entrega

ATENDIMENTO / VIDROS
  → entra no portal Maxpar/Autoglass
  → confere apólice
  → coleta/preenche dados
  → conduz questionário dinâmico
  → abre/acompanha atendimento governado
```

O próximo salto não é criar mais uma automação.

É transformar o que essas duas linhas provaram em uma **capacidade global de plataforma**:

```text
Agente / Auxiliar / Rotina / Chat / API / Admin
                         │
                         ▼
                    Work Run
                         │
                    Skill Release
                         │
                 Capability Pack
                         │
                    Tool Gateway
                         │
                 Portal Provider
                         │
                    portal_job
                         │
                  Portal Worker
                         │
              Journey do registry único
                         │
           Runtime da SPEC-073 / SPEC-074
                         │
        resultado + evidence + continuidade
                         │
        Tool Invocation + Work Step + Work Run
```

A consequência de produto é deliberada:

> **Adicionar uma nova seguradora à cobrança não cria um novo Auxiliar.**
>
> **Adicionar uma nova capacidade de portal não cria um novo Agent automaticamente.**
>
> **Criar um novo Auxiliar que precise de um portal não cria uma nova conexão.**
>
> **Uma credencial de portal conectada à corretora serve a todos os trabalhadores autorizados daquela corretora.**

É isso que torna o Portal Worker infraestrutura do AutoBrokers — e não uma coleção de scripts.

---

# 1. Por que esta SPEC existe agora

A SPEC-073 endurece o Portal Worker transversalmente:

- profiler;
- discovery mode;
- percepção API → DOM → adaptive → visão → humano;
- segurança transacional;
- evidência;
- recuperação sem retry cego;
- zero regressão das jornadas existentes.

A SPEC-074 usa essa base no primeiro workflow transacional realmente complexo: Maxpar/Autoglass ponta a ponta.

Depois disso, continuar adicionando portal por portal manualmente, com cada chamador criando seu próprio `portal_job`, sua própria espera, seu próprio contrato, seu próprio tratamento de erro e sua própria conexão, **recriaria o problema que as SPECs 053, 055, 056 e 058 foram escritas para eliminar**.

Esta SPEC fecha a próxima camada:

```text
073  torna o motor robusto
074  prova o motor num workflow complexo
075  transforma o motor em capability reutilizável da plataforma
```

---

# 2. Autoridade — antes de tocar em uma linha

O executor deve obedecer à ordem canônica. Antes de editar:

1. `CLAUDE.md`;
2. `docs/canon/EXECUTION-MASTER-PLAN.md`;
3. `docs/canon/FOUNDER-DECISIONS.md`;
4. `docs/canon/GLOSSARIO.md`;
5. `docs/canon/ONTOLOGIA-DO-TRABALHO.md`;
6. `docs/canon/CAMADAS-DE-CONEXAO.md`;
7. `docs/canon/PORTAIS-E-CORREDORES.md`;
8. `docs/canon/PENDENCIAS.md`;
9. `docs/canon/specs/SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`;
10. `SPEC-053-autobrokers-work-os-core-harness.md`;
11. `SPEC-054-foundation-hardening-schema-governance.md`;
12. `SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`;
13. `SPEC-056-skill-registry-tool-gateway.md`;
14. `SPEC-058-auxiliary-routine-factory.md`;
15. `docs/canon/MIGRATIONS-AUTHORITY.md` **antes de qualquer SQL**;
16. SPEC-073 executada ou seu estado real;
17. SPEC-074 executada ou seu estado real;
18. código atual;
19. schema vivo do Supabase, read-only.

Ordem normativa:

```text
CLAUDE.md
→ 052/053
→ 054/055/056/058
→ 073
→ 074
→ 075
→ código atual como estado de implementação
```

Se a branch da 075 encontrar a 073/074 ainda não executadas, **não duplicar as peças que elas definem**. Executar a dependência ou ajustar a ordem, preservando a arquitetura final. Não criar versão provisória paralela só para “destravar” a 075.

---

# 3. Preflight obrigatório

Antes de `checkout`, `pull`, `reset`, `stash pop`, merge ou migration:

```bash
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
git worktree list
git stash list
```

Esperado:

- raiz correta;
- registrar branch/HEAD real;
- workspace limpo ou estado local explicitamente preservado;
- não tocar em stash histórico;
- não trocar branch usada por outro worktree;
- não resetar trabalho não commitado.

Depois:

```bash
git fetch origin
git rev-parse origin/main
```

Criar a branch da SPEC a partir do estado canônico correto.

**Não assumir que o SHA deste documento ainda é o SHA atual.** `0ffcbed...` é a baseline observada em 15/08/2026, não uma ordem para retroceder a branch.

---

# 4. Estado medido que motivou a SPEC

## 4.1 O Work OS já existe — não devemos recriá-lo

📊 **Medição 15/08/2026 · Supabase produção `dcajcvlzcjbmyapmklil`.**

```text
work_runs ...................... 1.833
capabilities ................... 38
capability_packs ............... 10
skills ......................... 20
tool_definitions ............... 31
tool_invocations ............... 30
auxiliary_templates ............ 15
tenant_auxiliaries ............. 3
routines ....................... 1
portals ........................ 17
portal_accounts ................ 16
portal_jobs .................... 106
```

Conclusão:

> A 075 não tem justificativa para criar “Portal Work Runs”, “Portal Skills v2”, “Portal Capability Registry”, “Portal Auxiliary Factory” ou outra história universal. As autoridades já existem.

## 4.2 O Portal Worker já possui um registry único de execução

📊 `backend/portal_worker/journeys/__init__.py` já registra no mesmo mapa:

```text
allianz_corretor.login_check
allianz_corretor.cobranca_sweep
hdi_corretor.login_check
hdi_corretor.cobranca_sweep
tokiomarine_corretor.login_check
tokiomarine_corretor.cobranca_sweep
yelum_corretor.login_check
yelum_corretor.cobranca_sweep
mapfre_corretor.login_check
mapfre_corretor.cobranca_sweep
zurich_corretor.login_check
zurich_corretor.cobranca_sweep
vidros_lanternas.login_check
vidros_lanternas.abrir_atendimento
```

Também já existe:

```python
portais_com_cobranca()
```

que deriva a cobertura **do registry**, em vez de manter uma segunda lista.

Essa decisão deve ser preservada e generalizada.

## 4.3 O Tool Gateway já conhece a FAMÍLIA portal

📊 No banco vivo existem:

```text
portal.billing_read
portal.policy_read
portal.execute
```

com `implementation_kind='portal'`.

Também já existem capabilities:

```text
operational.portal.billing.read
operational.portal.policy.read
operational.portal.assistance.prepare
operational.portal.assistance.read
operational.portal.assistance.request
tenant.portal.execute
```

Portanto, **não criar outra família de permissão**.

## 4.4 Mas o provider portal ainda não está costurado de verdade ao Tool Gateway

📊 Medição 15/08/2026:

As três releases de tool de portal estão publicadas, mas seus manifests são apenas:

```json
{
  "provider": "portal_browser",
  "implementation_kind": "portal"
}
```

E:

```text
input_schema  = {}
output_schema = {}
```

📊 `tool_invocations` das três tools:

```text
portal.billing_read .... 0
portal.execute ......... 0
portal.policy_read ..... 0
```

Ao mesmo tempo, 📊 existem **106 `portal_jobs`**.

Conclusão objetiva:

> O catálogo canônico sabe que “portal” é uma tool, mas a execução real ainda acontece principalmente por caminhos especializados que inserem/acompanham `portal_jobs` diretamente. A 075 deve **ligar o catálogo ao motor real**, não criar um motor novo.

## 4.5 Cobrança Feita prova o padrão especializado atual

📊 `backend/app/services/billing_collection.py`:

```text
routine/auxiliar
→ descobre portais com cobranca no registry
→ procura portal_account da corretora
→ INSERT direto em portal_jobs
→ poll portal_jobs
→ consolida inadimplentes/boletos
→ regras de 48h / forma de pagamento / approval / governor
→ entrega
```

Esse serviço contém regras de negócio valiosas e **não será reescrito**.

A 075 muda somente o modo como ele solicita a execução do portal, preservando:

- carência de 48 horas;
- oldest-first;
- anti-duplicação de envio;
- `billing_sent_log`;
- regra “sem boleto por forma de pagamento → tarefa humana, não mensagem ao segurado”;
- governor de WhatsApp;
- approval;
- test mode;
- retomada;
- relatório.

## 4.6 O atendimento de vidros prova outro chamador especializado

`PortalActionTool` também cria/acompanha `portal_jobs`, com:

- InfoCap;
- dados da apólice;
- idempotência por pedido;
- `confirm` governado;
- resposta para o segurado;
- Vigia.

A 075 também não destrói isso. O contrato LangChain existente vira **adapter de compatibilidade** sobre a nova ponte global.

## 4.7 O worker é globalmente serial hoje

📊 `backend/portal_worker/worker.py` observado em 15/08/2026:

```python
POLL_SECONDS = 30
run_once() -> pega 1 job queued
await _run_job(...)
sleep(POLL_SECONDS)
```

Um único processo executa um job por vez.

Isso era suficiente quando o Portal Worker tinha poucos usos. Não é suficiente como plataforma para:

- atendimento ao vivo;
- cobrança agendada;
- consulta de apólice;
- renovação;
- documentos;
- sinistro;
- futuros Auxiliares;
- vários tenants ao mesmo tempo.

A 075 deve escalar **sem sacrificar segurança de sessão**.

---

# 5. Definições — palavras que o Claude NÃO pode misturar

## Portal

Sistema externo/web que o AutoBrokers acessa.

Exemplo:

```text
Allianz Corretor
Maxpar / Abra Seu Atendimento
HDI Corretor
MAPFRE Negócios
```

Portal não é Skill, Auxiliar nem Tool.

## Journey

Implementação executável de **uma capacidade concreta dentro de um portal**.

Exemplos:

```text
cobranca_sweep
login_check
abrir_atendimento
consultar_atendimento
listar_documentos
```

É código do provider `portal_worker`.

## Business Operation

Nome estável da operação de negócio independente do portal.

Exemplos desta SPEC:

```text
billing.overdue.list
portal.login.check
assistance.glass.prepare
assistance.glass.request
assistance.glass.read
policy.read
```

A mesma Business Operation pode ter implementações diferentes por portal.

## Tool

Interface técnica governada pelo Tool Gateway.

Exemplos:

```text
portal.billing_read
portal.policy_read
portal.assistance_prepare
portal.assistance_read
portal.assistance_request
```

Tool **não** é por seguradora.

## Capability

Permissão/poder governável.

Já existe em `capabilities`.

## Skill

Procedimento reutilizável que ensina como chegar a um resultado e declara tools/capabilities necessárias.

Skill **não** é “script do portal”.

## Auxiliar

Trabalhador instalado que usa Skills e Capability Packs.

Auxiliar **não** contém credenciais do portal.

## Rotina

Gatilho/agenda que inicia trabalho do Auxiliar/Skill.

## Agent

Executor cognitivo. Não é criado só porque existe um portal novo.

## Work Run

Execução universal de negócio.

## portal_job

Registro/queue especializada da chamada ao Portal Worker.

> `portal_job` **não substitui Work Run** e **não será eliminado** nesta SPEC. Ele é o filho técnico especializado de uma execução canônica.

---

# 6. O contrato global que a 075 estabelece

Ao final:

```text
QUEM quer trabalhar
  Agent | Auxiliar | Rotina | Work Run | API

não sabe:
  seletor CSS
  cookie
  senha
  token da sessão
  URL interna descoberta
  nome da função Python
  retry do browser
  proxy
  screenshot

sabe somente:
  resultado desejado
  Skill
  Tool autorizada
  dados de negócio
```

E o portal provider resolve:

```text
Tool autorizada
→ business operation
→ portal alvo
→ conta correta da corretora
→ journey registrada
→ sessão / browser / API interna legítima
→ execução
→ resultado canônico
```

---

# 7. Invariantes — se uma delas quebrar, a SPEC falhou

1. **Um Portal Worker.**
2. **Um registry de journeys.**
3. **Um Tool Gateway.**
4. **Um Capability Registry.**
5. **Um Skill Registry.**
6. **Um Auxiliary Factory.**
7. **Um Work Run universal.**
8. `portal_jobs` continua sendo a fila/história especializada, não uma segunda história comercial.
9. Nova seguradora da Cobrança Feita **não cria novo Auxiliar**.
10. Nova journey de uma operação já conhecida **não cria nova Tool**.
11. Nova Tool só existe se houver nova classe de capacidade de negócio.
12. Credencial conectada à corretora é reutilizada por todos os Auxiliares/Agents autorizados.
13. Nenhum Auxiliar guarda login/senha.
14. Nenhuma Skill guarda login/senha.
15. Nenhum LLM recebe senha/cookie/token.
16. Nenhum modelo escolhe `portal_key` ou `journey` arbitrariamente.
17. Todo side effect externo possui idempotência.
18. `MAYBE_COMMITTED` nunca vira retry cego.
19. Um portal com múltiplas corretoras/contas exige identidade de conta verificada.
20. Falha de autorização/conexão é fail-closed.
21. Falha de observabilidade não transforma ação negada em ação permitida.
22. Profiler/discovery nunca publica automaticamente capability live.
23. Fixture nunca contém PII/segredo real.
24. Cobrança que funciona antes precisa funcionar igual ou melhor depois.
25. Vidros que funciona antes precisa funcionar igual ou melhor depois.
26. Nenhum teste de infraestrutura dispara WhatsApp real.
27. Nenhum canário transacional roda sem autorização explícita do Founder.

---

# 8. Arquitetura final

```text
┌──────────────────────────────────────────────────────────────────┐
│                  AUTOBROKERS WORK OS                            │
│                                                                  │
│  Chat    Agent    Auxiliar    Rotina    API    Admin            │
│    │       │          │          │        │      │               │
│    └───────┴──────────┴──────────┴────────┴──────┘               │
│                           │                                      │
│                        Work Run                                  │
│                           │                                      │
│                    Skill / Capability Pack                       │
│                           │                                      │
│                       Tool Gateway                               │
│                           │                                      │
│              PortalExecutionGateway / Provider                  │
│                           │                                      │
│      connection + authorization + idempotency + lineage         │
│                           │                                      │
│                       portal_jobs                                │
└───────────────────────────┼──────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                     PORTAL WORKER                                │
│                                                                  │
│    JourneyDefinition registry único                             │
│             │                                                    │
│    runtime seguro SPEC-073                                      │
│             │                                                    │
│ API → DOM → adaptive → vision → HITL                            │
│             │                                                    │
│ checkpoint / evidence / screenshots / session / proxy           │
│             │                                                    │
│ JourneyResult                                                    │
└───────────────────────────┼──────────────────────────────────────┘
                            │
                            ▼
                   Portal externo real
```

---

# 9. BLOCO A — transformar o registry atual em contrato de capability de execução

## 9.1 Não criar `journey_registry_v2`

O atual `backend/portal_worker/journeys/__init__.py` continua autoridade.

Ele deve evoluir de:

```python
"portal.journey": (module, function)
```

para uma definição rica — **preservando compatibilidade**.

Proposta:

```python
@dataclass(frozen=True)
class JourneyDefinition:
    portal_key: str
    journey_key: str
    business_operation: str
    module: str
    function: str
    contract_version: str = "1"
    effect_class: str = "read"
    requires_account: bool = True
    supports_resume: bool = False
    supports_discovery: bool = True
    description: str = ""
```

O Claude pode nomear campos diferentemente se o código atual já possuir contrato equivalente. **Não pode criar um segundo registry.**

## 9.2 `effect_class` NÃO vira uma segunda autoridade comercial

A autoridade de permissão continua:

```text
capabilities
+ tool_definitions
+ Tool Gateway
+ approval
```

O `effect_class` no código da journey existe para um motivo de segurança:

> uma execução legada que ainda chegou ao Portal Worker fora do Gateway não pode fingir que uma journey material é read-only.

Regra:

```text
Tool diz READ + Journey diz MATERIAL
    → conflito
    → FAIL CLOSED
    → não executa

Tool diz MATERIAL + Journey diz READ
    → usa a proteção mais forte
```

Nunca relaxar proteção por divergência.

## 9.3 Business Operation

Adicionar operações estáveis aos registros existentes.

Exemplo inicial:

```text
allianz_corretor.cobranca_sweep      → billing.overdue.list
demais *.cobranca_sweep              → billing.overdue.list
*.login_check                         → portal.login.check
vidros_lanternas.abrir_atendimento   → assistance.glass.request
```

Após a SPEC-074:

```text
vidros_lanternas.consultar_atendimento → assistance.glass.read
vidros_lanternas.continuar_atendimento → assistance.glass.continue
```

**Não inventar nomes para journeys que ainda não existem.** A matriz é gerada a partir do código realmente presente.

## 9.4 Introspecção única

O registry deve oferecer funções puras:

```python
get_journey(portal_key, journey_key)
get_definition(portal_key, journey_key)
journeys_do_portal(portal_key)
portais_com_operacao(business_operation)
suporta(portal_key, business_operation)
matriz_de_capacidades()
```

Manter por compatibilidade:

```python
portais_com_cobranca()
```

mas implementá-la sobre:

```python
portais_com_operacao("billing.overdue.list")
```

Assim o Cobrador continua funcionando sem mudança de contrato externo.

## 9.5 Gate do Bloco A

- registry importa sem puxar todas as journeys;
- late import preservado;
- todas as chaves antigas resolvem para a mesma função;
- `portais_com_cobranca()` retorna exatamente a mesma lista pré-SPEC;
- nenhum portal novo é considerado suportado por suposição;
- conflito effect class reprova execução;
- testes da cobrança passam antes de avançar.

---

# 10. BLOCO B — PortalExecutionGateway: a ponte única do Work OS para o Portal Worker

Criar uma **ponte de provider**, não um segundo Tool Gateway.

Local sugerido:

```text
backend/app/services/portals/
    __init__.py
    gateway.py
    contracts.py
    connection_resolver.py   # somente se não existir resolver reutilizável
```

Se o repo já possuir um provider dispatcher canônico de Tool Gateway capaz de executar `implementation_kind='portal'`, **estender esse dispatcher** e reduzir `gateway.py` a adapter. Não criar concorrência.

## 10.1 Contrato de entrada

```python
@dataclass
class PortalExecutionRequest:
    company_id: str
    operation_key: str
    business_input: dict

    # lineage — injetado pelo runtime, nunca pelo LLM
    work_run_id: str | None
    work_step_id: str | None
    skill_release_id: str | None
    tool_release_id: str | None
    agent_id: str | None
    user_id: str | None
    session_id: str | None

    # origem governada
    insurer_key: str | None
    portal_key_hint: str | None     # somente chamador server-side confiável
    account_id_hint: str | None    # somente chamador server-side confiável

    # proteção
    idempotency_key: str | None
    priority: int
    wait_mode: str                # await | enqueue
```

**Nunca expor ao modelo:**

```text
journey_key
module
function
account_id
cookie
token
password
proxy
endpoint interno bruto
```

## 10.2 Resolução

O gateway executa:

```text
1. valida company_id
2. valida ToolGrant/Tool Release recebido do Tool Gateway
3. revalida capability no instante da execução
4. valida approval quando necessário
5. resolve business operation
6. resolve portal alvo permitido
7. resolve conexão/portal_account da MESMA company
8. resolve JourneyDefinition
9. valida efeito Tool × Journey
10. gera idempotency key quando material
11. abre tool_invocation
12. cria portal_job com lineage
13. aguarda OU devolve handle
14. traduz resultado
15. fecha tool_invocation
```

Nenhum desses passos fica a cargo do LLM.

## 10.3 Resolução de portal alvo

Existem três casos:

### Caso A — portal compartilhado por várias seguradoras

Maxpar:

```text
operation assistance.glass.*
→ portal_key = vidros_lanternas
→ insurer_name vai como DADO DE NEGÓCIO
```

### Caso B — um portal de corretor por seguradora

Cobrança:

```text
insurer_key = mapfre
operation = billing.overdue.list
→ resolve portal MAPFRE da corretora
→ journey que implementa billing.overdue.list
```

### Caso C — chamador interno já possui portal_key validado

`billing_collection` já deriva portal keys do registry.

Ele pode fornecer `portal_key_hint`, porque o valor nasceu de código/registro, não de texto do modelo.

Mesmo assim:

```text
hint não registrado
→ rejeita

hint sem journey para operação
→ not_supported
```

## 10.4 O modelo nunca escolhe uma função

Proibido:

```json
{
  "portal_key": "qualquer_coisa",
  "journey": "qualquer_funcao"
}
```

em schema exposto ao agente.

O modelo diz:

```text
“consultar parcelas vencidas da MAPFRE”
```

A infraestrutura resolve a implementação.

---

# 11. BLOCO C — completar o Tool Gateway de portal de verdade

## 11.1 Preservar tools existentes

Não apagar:

```text
portal.billing_read
portal.policy_read
portal.execute
```

## 11.2 `portal.execute` vira compatibilidade, não padrão para novas Skills

Hoje ele é muito amplo:

```text
risk = critical
side_effect = external_commitment
requires_approval = true
```

Isso é útil como guarda legado, mas ruim como linguagem de produto.

Novas Skills não devem depender de “execute qualquer portal”.

Criar tools estreitas somente onde já existe capability correspondente:

```text
portal.assistance_prepare
  capability operational.portal.assistance.prepare
  side_effect prepare
  approval false

portal.assistance_read
  capability operational.portal.assistance.read
  side_effect read
  approval false

portal.assistance_request
  capability operational.portal.assistance.request
  side_effect external_commitment
  approval true
```

`portal.execute` permanece enquanto `portal_action`/legado depender dele, com deprecation **de uso novo**, não remoção destrutiva.

## 11.3 Não criar tool por seguradora

PROIBIDO:

```text
portal.allianz.billing
portal.hdi.billing
portal.mapfre.billing
```

Correto:

```text
portal.billing_read
```

com provider selecionado pelo alvo/connection.

## 11.4 Schemas reais

As releases atuais de portal com `{}` devem ganhar nova release publicada com input/output formal.

### `portal.billing_read`

Input semântico:

```json
{
  "insurer_key": "mapfre",
  "filters": {
    "overdue_only": true,
    "minimum_overdue_hours": 48,
    "limit": 50
  },
  "download_documents": true
}
```

Output canônico:

```json
{
  "business_state": "success",
  "portal": "mapfre_corretor",
  "items": [],
  "documents": [],
  "needs_human": [],
  "evidence_ref": "..."
}
```

**A regra de negócio de quem mandar mensagem continua em `billing_collection`.** A tool apenas coleta.

### `portal.policy_read`

Input:

```json
{
  "insurer_key": "...",
  "policy_number": "...",
  "document": "...",
  "requested_fields": []
}
```

Sem senha/portal selector.

### Assistance tools

Schemas subordinados à SPEC-074.

Nunca inventar campo que não exista no contrato final da 074.

## 11.5 Execution manifest real

Nova release deve declarar, no mínimo:

```json
{
  "provider": "portal_worker",
  "implementation_kind": "portal",
  "provider_adapter": "portal_execution_gateway",
  "operation_key": "billing.overdue.list",
  "contract_version": "1"
}
```

Para provider dinâmico, `portal_key` NÃO fica no manifest da tool global.

## 11.6 Invocation real

Depois do cutover, toda chamada pelo Work OS cria:

```text
tool_invocation
   ↕
portal_job
```

Não declarar a 075 concluída enquanto `portal.*` continuar com **zero invocações reais** em canário autorizado.

---

# 12. BLOCO D — lineage: Portal Job deixa de ser órfão do Work Run

SPEC-055 foi explícita:

> não criar `work_portal_jobs`; **ligar `portal_jobs`**.

## 12.1 Migration mínima, expand-only

**Somente se o censo vivo confirmar que ainda faltam as colunas.**

Adicionar a `portal_jobs`:

```sql
work_run_id uuid null
work_step_id uuid null
tool_invocation_id uuid null
priority smallint not null default 50
```

FKs compatíveis com o schema real.

Índices:

```text
(status, priority desc, created_at asc)
work_run_id
work_step_id
tool_invocation_id
```

Não adicionar:

```text
portal_run_id
portal_work_run
portal_execution_history
```

## 12.2 Compatibilidade histórica

Os 106 jobs existentes continuam válidos:

```text
work_run_id = NULL
work_step_id = NULL
tool_invocation_id = NULL
priority = 50
```

Não backfillar lineage inventada.

## 12.3 APPLY / VERIFY / ROLLBACK

A migration deve começar com manifesto completo.

### APPLY

- adicionar colunas;
- FKs/indexes;
- default;
- comentários.

### VERIFY

Confirmar:

```text
contagem portal_jobs antes == depois
nenhum status alterado
nenhum params/evidence alterado
novas colunas existem
fila usa índice novo em EXPLAIN do claim
```

### ROLLBACK

Rollback de emergência pode remover **somente os novos índices/colunas se ainda não houver consumidor dependente**.

Se já houver jobs novos com lineage, rollback operacional preferido é:

```text
reverter código
ignorar colunas novas
não destruir informação recém-gravada
```

Não fazer DROP automático por reflexo.

---

# 13. BLOCO E — Work Run ↔ Portal Job: um trabalho, duas camadas corretas

## 13.1 Quando existe Work Run

Toda execução de:

- Auxiliar;
- Rotina;
- portal autenticado;
- assistência transacional;
- tarefa longa;
- side effect;
- aprovação;

já deve estar sob Work Run pela SPEC-055.

A chamada de portal recebe lineage desse Run.

## 13.2 `portal_job` não vira o Work Run

Work Run responde:

> qual resultado de negócio estamos produzindo?

Portal job responde:

> qual execução técnica de portal está acontecendo?

Exemplo:

```text
Work Run: Cobrar inadimplentes do dia
  Step 1: consultar Allianz
      portal_job A
  Step 2: consultar HDI
      portal_job B
  Step 3: consultar MAPFRE
      portal_job C
  Step 4: consolidar
  Step 5: entregar
```

Um Work Run pode ter vários portal jobs.

## 13.3 Timeline

Eventos mínimos:

```text
portal.requested
portal.queued
portal.started
portal.needs_human
portal.business_blocked
portal.maybe_committed
portal.completed
portal.failed
```

Gravar no `work_events` via infraestrutura existente.

Não criar `portal_events` universal.

## 13.4 Work Step

Quando a chamada parte de um workflow:

```text
work_step.tool_name/capability
↔ tool_invocation
↔ portal_job
```

A tela futura de Trabalho precisa conseguir responder:

> “Este relatório está esperando a MAPFRE?”

sem abrir três tabelas manualmente.

---

# 14. BLOCO F — Connection Resolver global: conecta uma vez, todos usam

Esta seção implementa diretamente a decisão do Founder:

> **Se o portal da Allianz estiver conectado, ele serve a qualquer Auxiliar autorizado que precise dele.**

## 14.1 Não colocar conexão dentro do Auxiliar

PROIBIDO:

```text
tenant_auxiliary.config.password
skill.manifest.cookie
agent.prompt.username
routine.config.portal_secret
```

## 14.2 A realidade atual está em mais de um lugar

Canônico atual reconhece:

```text
tenant_connections
portal_accounts
integrations
```

O próprio `conexoesDaCorretora()` já lê as três fontes.

A 075 não apaga nenhuma dessas tabelas.

## 14.3 Resolver server-side

Implementar/reutilizar um resolver Python único para portal:

```python
resolve_portal_connection(
    company_id,
    portal_key,
    insurer_key=None,
    required_account_label=None,
)
```

Retorna um envelope **sem segredo**:

```json
{
  "status": "connected",
  "portal_key": "mapfre_corretor",
  "account_id": "uuid",
  "account_label": "AUTO FLEET ...",
  "health": "ok",
  "connection_source": "portal_accounts"
}
```

Senha continua decifrada somente dentro do Portal Worker.

## 14.4 Multi-account é P0 de isolamento

MAPFRE já provou que um login pode enxergar mais de uma corretora/contexto.

Regra global:

```text
se um portal pode enxergar múltiplas contas:
  account_label esperado é obrigatório
  journey confirma a identidade após login
  divergência → needs_human / security stop
  nunca “usa o que estiver selecionado”
```

## 14.5 Inconsistência atual `insurance_portal`

📊 Em 15/08/2026 o schema/código canônico descreve `insurance_portal` como conector da corretora e a migration da SPEC-064 o ativa.

📊 No banco vivo consultado na mesma data, `connector_templates.slug='insurance_portal'` apareceu `is_active=false`, enquanto `portal_accounts` reais existem e o catálogo tenant-facing já considera uma conta saudável como conexão pronta.

Isso é uma **divergência de estado a auditar**, não licença para um `UPDATE is_active=true` cego.

A 075 deve:

1. medir por que o estado vivo divergiu;
2. verificar se há decisão/migration posterior;
3. preservar a UX que reconhece `portal_accounts` saudáveis;
4. corrigir a autoridade somente se houver evidência;
5. registrar em `CHANGE-ADDENDA.md` se a correção ficar fora do texto desta SPEC.

---

# 15. BLOCO G — idempotência global por efeito de negócio

## 15.1 Read-only

Leituras podem repetir quando seguro, mas ainda precisam de:

- limite de chamadas;
- timeout;
- dedup de jobs idênticos em janela curta quando fizer sentido;
- cache somente se a freshness permitir.

## 15.2 Material

Toda operação material precisa de chave derivada do negócio.

Exemplo vidros:

```text
company
+ policy/vehicle
+ item/lateralidade
+ data/ocorrência
+ operation
```

Não usar UUID aleatório como “idempotência”.

## 15.3 A chave vive no pai e no filho

```text
Work Run idempotency
Tool Invocation invocation_key
Portal Job idempotency_key
```

Cada nível representa uma granularidade diferente, mas todos precisam poder ser relacionados.

## 15.4 `MAYBE_COMMITTED`

Se houve:

```text
clique material
+ queda/timeout antes de confirmação
```

resultado:

```text
business_state = maybe_committed
safe_to_retry = false
```

Próximo passo:

```text
reconcile / consultar estado
```

Nunca:

```text
retry abrir atendimento
```

---

# 16. BLOCO H — resultado canônico de qualquer portal

O Tool Gateway não pode receber 20 formatos completamente diferentes.

Definir um `PortalExecutionResult`:

```python
@dataclass
class PortalExecutionResult:
    technical_status: str
    business_state: str
    operation_key: str
    portal_key: str

    captured: dict
    evidence: dict
    evidence_refs: list[str]

    provider_reference: str | None
    continuation: dict | None

    retryable: bool
    safe_to_retry: bool
    needs_human: bool
    human_reason: str | None

    error_code: str | None
    message: str
```

## 16.1 `business_state` inicial

```text
success
needs_human
business_blocked
not_supported
needs_connection
auth_expired
rate_limited
portal_changed
transient_failure
maybe_committed
failed
```

Subestados podem existir em `captured.reason`, por exemplo:

```text
coverage_absent
no_bill_by_payment_rule
policy_not_found
account_context_mismatch
```

Não explodir o enum para cada frase de portal.

## 16.2 Compatibilidade com `JourneyResult`

Journey continua retornando:

```text
done | needs_human | failed
```

por compatibilidade.

O adapter traduz para `PortalExecutionResult`.

Com o tempo, journeys podem passar a fornecer `business_state` explicitamente, mas a migração é incremental.

## 16.3 Regra essencial

`failed` técnico **não significa automaticamente** “não aconteceu nada”.

Se existe protocolo/provider_reference/checkpoint material:

```text
não comunicar ao cliente “não abriu”
```

até reconciliar.

---

# 17. BLOCO I — o Portal Capability Factory de desenvolvimento

Esta é a parte que torna **fácil adicionar novas capacidades**.

Criar uma ferramenta de engenharia, não um runtime paralelo.

Local sugerido:

```text
backend/scripts/portal_factory.py
```

Ela gera/audita estrutura; **não publica nem executa ação material sozinha**.

## 17.1 Comandos mínimos

```bash
python -m scripts.portal_factory audit
python -m scripts.portal_factory matrix
python -m scripts.portal_factory validate --portal <key>
python -m scripts.portal_factory validate --portal <key> --journey <key>
python -m scripts.portal_factory scaffold-portal --portal <key>
python -m scripts.portal_factory scaffold-journey --portal <key> --operation <op>
python -m scripts.portal_factory replay --portal <key> --journey <key> --case <fixture>
```

Pode haver outra CLI se o repo tiver padrão próprio. O contrato é o importante.

## 17.2 `audit`

Deve detectar:

- portal em `portals` sem journey;
- journey registrada cujo módulo/função não importa;
- journey sem fixture;
- operation duplicada em duas entries incompatíveis;
- capability/tool inexistente para operation exposta ao Work OS;
- tool portal sem release publicada;
- release com schema `{}` quando deveria ser tipada;
- `effect_class` divergente da tool;
- fixture com padrão de segredo/PII;
- portal account apontando para portal não registrado;
- doc matrix divergente do registry.

## 17.3 `scaffold-portal`

Cria somente skeleton:

```text
portal_worker/journeys/<portal>.py
fixtures/<portal>/...
tests/test_<portal>_portal_contract.py
```

NÃO:

- adiciona senha;
- cria portal no banco automaticamente;
- publica Tool;
- publica Skill;
- libera capability;
- faz commit;
- executa login real.

## 17.4 `scaffold-journey`

Antes de criar código pergunta à máquina:

```text
esta business operation já existe em outro portal?
```

Se SIM:

> reutilizar Tool/Skill/Capability existentes e implementar somente a journey.

Se NÃO:

> registrar como `capability_gap` / proposta e exigir classificação de risco antes de criar uma nova Tool.

Esse único gate impede inflação de catálogo.

---

# 18. Os três casos de onboarding — e o que cada um realmente cria

## Caso 1 — nova SEGURADORA, operação já existente

Exemplo:

> adicionar Sancor à Cobrança Feita.

Criar:

```text
portal/connection se realmente novo
journey cobranca_sweep
fixtures/testes
1 entrada no registry
canário
```

Não criar:

```text
novo Auxiliar
nova Skill
nova Tool
nova Capability
novo scheduler
```

## Caso 2 — nova CAPACIDADE num portal já conhecido

Exemplo:

> Allianz: consultar renovação.

Criar:

```text
business operation nova SE realmente diferente
journey nova
Tool/Capability/Skill somente se o Work OS ainda não possui conceito equivalente
fixtures/evals
```

## Caso 3 — novo Auxiliar usa capacidades já existentes

Exemplo futuro:

> Auxiliar de Renovações usa InfoCap + portal da seguradora.

Criar:

```text
Auxiliar template/release
Skill Release(s)
Capability Pack existente/novo se necessário
Rotina opcional
```

Não criar:

```text
browser novo
login novo
portal account novo se a corretora já conectou
journey duplicada
```

---

# 19. BLOCO J — fixtures e replay como contrato de onboarding

A factory precisa conseguir provar uma journey sem depender do portal real a cada teste.

## 19.1 Estrutura

```text
backend/tests/fixtures/portal_worker/
  <portal_key>/
    <journey_key>/
      <case_key>/
        manifest.json
        input.json
        network.json
        dom.json
        expected.json
        screenshot.webp      # opcional e anonimizada
        response.bin          # somente se seguro/necessário
```

Não é obrigatório ter todos os arquivos em todo caso.

## 19.2 `manifest.json`

```json
{
  "portal_key": "...",
  "journey_key": "...",
  "operation_key": "...",
  "captured_at": "2026-08-15",
  "source": "founder_har_sanitized",
  "pii": "removed",
  "secrets": "removed",
  "effect": "read",
  "expected_state": "success"
}
```

## 19.3 HAR bruto nunca entra

O Profiler/Claude transforma HAR privado em fixture sanitizada.

Nunca comitar:

- Authorization;
- Cookie;
- JWT;
- token_autorizacao;
- senha;
- CPF real;
- placa real;
- nome real;
- endereço real;
- telefone real;
- PDF real com PII.

## 19.4 Replay read-only

Para GET/POST semanticamente read-only, o harness pode reproduzir request/response sanitizados offline.

## 19.5 Replay de side effect

Nunca “reexecutar” POST material para testar.

O fixture representa:

```text
request planejada
boundary detectado
response observada/sanitizada
expected effect
```

E o teste verifica que o código **pararia/guardaria corretamente** antes do efeito quando em dry-run.

---

# 20. BLOCO K — integrar o Portal Profiler da SPEC-073 à Factory

`PORTAL_DISCOVERY_MODE` não vira outro produto.

Ele alimenta o Factory.

Fluxo:

```text
Profiler
  ↓
network sanitizado
DOM estruturado
screen fingerprint
screenshot
rotas
requests/responses candidatos
  ↓
Factory audit/proposal
  ↓
revisão técnica
  ↓
Journey code + fixture
  ↓
testes
```

## 20.1 API descoberta NÃO é API autorizada

Se o Profiler vê:

```text
POST /questionarios
```

isso significa:

> “existe uma chamada candidata”.

Não significa:

> “pode replayar em produção”.

A classificação de efeito é obrigatória antes.

## 20.2 Endpoint allowlist

Cada journey/API adapter deve permitir somente hosts/paths aprovados para aquele portal.

Descoberta não pode virar um HTTP client genérico com URL livre.

## 20.3 Drift

O Profiler deve poder comparar:

```text
fixture conhecida
×
runtime atual
```

Classificação:

```text
UNCHANGED
BENIGN_DRIFT
REVIEW_REQUIRED
BREAKING_DRIFT
```

Breaking drift em etapa material → fail closed.

---

# 21. BLOCO L — Portal Capability Score: saber o que está realmente pronto

Não queremos “funciona” como opinião.

Cada `(portal_key, journey_key)` ganha readiness calculada.

## 21.1 Estados de release operacional

```text
DRAFT
FIXTURE_GREEN
DRY_RUN_GREEN
CANARY_READONLY_GREEN
CANARY_TRANSACTIONAL_GREEN
LIVE_APPROVED
```

Não precisa criar tabela nova nesta SPEC. Pode ser derivado por ferramenta/report de:

- registry;
- testes;
- report da SPEC;
- evidências/canários.

Se for necessário persistir estado operacional depois, abrir Change Addendum em vez de improvisar tabela.

## 21.2 Score 0–100

| Dimensão | Pontos |
|---|---:|
| contrato + registry | 10 |
| fixtures + replay | 15 |
| caminho determinístico/API/DOM | 10 |
| casos negativos e erros | 10 |
| tenant/account identity | 10 |
| side effect + idempotência | 15 |
| evidence + redaction | 10 |
| recovery/resume | 5 |
| observabilidade/performance | 5 |
| canário real medido | 10 |
| **TOTAL** | **100** |

## 21.3 Hard blockers anulam o score

Uma journey com 95 pontos NÃO pode ficar live se tiver:

- cross-tenant possível;
- effect class desconhecido;
- ação material sem idempotência;
- fixture com segredo;
- conta não verificada em login multi-account;
- retry cego pós-commit;
- autorização inexistente;
- ação não medida de alto risco.

Resultado:

```text
score = 95
live_eligible = false
blocker = "idempotency_missing"
```

## 21.4 “100” não significa “nunca falha”

Significa:

> todos os gates definidos foram medidos e passaram.

Portal externo ainda pode ficar fora do ar. O sistema excelente é o que falha **com segurança, diagnóstico e retomada**, não o que promete um mundo externo infalível.

---

# 22. BLOCO M — documentação automática, sem segunda verdade manual

Gerar a partir do registry + testes:

```text
docs/generated/portal-capability-matrix.md
docs/generated/portal-capability-matrix.json
```

Ou pasta já adotada pelo repo, se houver.

## 22.1 Colunas

```text
portal
journey
business operation
effect class
requires account
supports resume
API-first / DOM / adaptive / vision
fixture count
negative cases
readiness state
score
last canary
live eligible
blocking reason
```

## 22.2 Não editar à mão

O `.md` gerado traz cabeçalho:

```text
GERADO — NÃO EDITAR MANUALMENTE
fonte: registry + test manifests + canary evidence
```

## 22.3 Docs canônicos antigos

Quando medição nova contradizer mapa antigo:

- corrigir o mapa canônico;
- preservar a lição histórica útil;
- não deixar duas afirmações “atuais” opostas.

A captura Yelum/Porto já mostrou como isso importa: catálogo de cobertura deve vir da apólice/sessão, não de uma tabela decorada por marca.

---

# 23. BLOCO N — escalabilidade: do worker serial para concorrência segura

Esta é uma das partes mais importantes para uso global.

## 23.1 Problema atual

Um worker globalmente serial pode deixar:

```text
cliente aguardando vidro
```

atrás de:

```text
varredura de cobrança de seis portais
```

Isso é inaceitável quando o Portal Worker servir agentes e Auxiliares simultaneamente.

## 23.2 Não migrar a fila para Redis

`portal_jobs` continua fila durável.

Redis serve para:

- lease;
- lock;
- coordenação transitória.

Não criar `portal_job_stream` como segunda autoridade.

## 23.3 Concurrency configurável

Introduzir:

```text
PORTAL_WORKER_CONCURRENCY
```

Default inicial:

```text
1
```

Canário sobe progressivamente:

```text
1 → 2 → 4
```

somente após locks provados.

## 23.4 Lock por conta/sessão

Dois jobs não podem navegar ao mesmo tempo na mesma sessão autenticada sem prova de segurança.

Chave Redis:

```text
portal:lease:<company_id>:<portal_key>:<account_label>
```

Para portal público sem account:

```text
portal:lease:<company_id>:<portal_key>:public
```

Lease:

- TTL > heartbeat;
- renovação enquanto job roda;
- token de ownership;
- unlock somente pelo dono.

## 23.5 Redis indisponível

Se concurrency > 1 e Redis não estiver confiável:

```text
fail-safe → efetivo 1
```

Não rodar concorrente “sem lock porque Redis caiu”.

## 23.6 Replicas

Não escalar o número de réplicas do portal-worker antes de o lock distribuído estar provado.

Concorrência local sem lock distribuído não protege contra duas réplicas.

## 23.7 Priority

`portal_jobs.priority` herda o Work Run.

Default compatível:

```text
50
```

Claim:

```text
priority DESC
created_at ASC
```

Não hardcodar “assistência sempre 100” no worker.

Quem define a prioridade comercial é o Work Run/orquestração.

## 23.8 Fairness tenant

Um tenant com centenas de jobs não pode monopolizar todos os slots.

Adicionar limite configurável:

```text
PORTAL_MAX_INFLIGHT_PER_COMPANY
```

Default conservador:

```text
1
```

ou valor medido na implementação.

O objetivo:

```text
AutoFleet billing 50 jobs
≠
Resulta atendimento ao vivo espera 50 jobs terminarem
```

## 23.9 Não aumentar polling à toa

Com concurrency e prioridade, medir:

```text
queue_wait_ms
claim_rate
idle polls
```

Otimizar somente se medição pedir.

Não repetir o erro do Egress: polling “barato” pode ficar caro quando escala.

---

# 24. BLOCO O — retry/recovery universal por classe de efeito

## Read

```text
retry automático permitido
com backoff + limite
```

## Prepare

```text
retry permitido se nenhuma criação externa ocorreu
```

## Reversible UI

```text
retry somente se checkpoint comprovar estado
```

## External commitment

```text
pré-commit → retry conforme policy
pós-commit confirmado → não repetir
pós-commit incerto → reconcile
```

## 24.1 Stale recovery

A recuperação de `running` do worker deve usar os checkpoints transacionais da 073/074.

Não voltar simplesmente todo órfão para `queued` se uma journey material já passou da fronteira de efeito.

## 24.2 O retry pertence ao runtime

Journey declara fatos:

```text
onde está
qual efeito já ocorreu
se sabe reconciliar
```

Runtime decide retry conforme policy.

Não cada journey inventar um `for attempt in range(3)`.

---

# 25. BLOCO P — segurança transversal

## 25.1 Tenant

Toda query de:

- portal_accounts;
- portal_sessions;
- portal_jobs;
- tenant_connections;
- tool_invocations;
- work_runs;

precisa de tenant scope quando aplicável.

Service role sem `company_id` é P0.

## 25.2 Account ownership

Antes de decifrar segredo:

```text
account.id
AND account.company_id == job.company_id
AND account.portal_key == job.portal_key
```

Falha → security stop.

## 25.3 Secrets

Nunca chegam em:

```text
params persistidos
evidence
screenshot metadata
trace
LLM
fixture
log
artifact
```

## 25.4 Browser API session

API interna do portal usa **a sessão legítima obtida pelo navegador**.

Não persistir token capturado em código/config como se fosse API key eterna.

## 25.5 Host allowlist

Request API-first só pode sair para:

- domínio do portal;
- host de API explicitamente aprovado daquela journey.

Nenhuma URL arbitrária vinda do DOM/LLM.

## 25.6 Vision

Vision:

- interpreta;
- propõe ação semântica;
- nunca recebe segredo;
- nunca autoriza side effect;
- nunca transforma baixa confiança em clique material.

## 25.7 Discovery

Discovery mode:

- read-first;
- grava evidência sanitizada;
- não confirma automaticamente;
- não baixa conteúdo sensível sem necessidade;
- não publica Tool/Skill.

---

# 26. BLOCO Q — observabilidade de ponta a ponta

Queremos conseguir abrir um Work Run e responder:

```text
qual Auxiliar pediu?
qual Skill?
qual Tool?
qual portal?
qual account label?
qual journey?
quanto esperou na fila?
quanto demorou?
usou API, DOM, adaptive ou vision?
qual foi o resultado de negócio?
precisou humano? por quê?
houve efeito externo?
qual protocolo/provider ref?
quanto custou?
```

## 26.1 Métricas mínimas

Sem PII:

```text
portal.jobs.requested
portal.jobs.queue_wait_ms
portal.jobs.runtime_ms
portal.jobs.success
portal.jobs.needs_human
portal.jobs.failed
portal.jobs.business_blocked
portal.jobs.maybe_committed
portal.sessions.reused
portal.sessions.login_required
portal.perception.api_used
portal.perception.dom_used
portal.perception.adaptive_used
portal.perception.vision_used
portal.rate_limited
portal.drift.breaking
```

Dimensões permitidas:

```text
portal_key
journey_key
operation_key
business_state
company_id somente onde já permitido pela telemetria interna
```

Não incluir:

```text
CPF
placa
nome
apólice
URL com token
```

## 26.2 `/health`

Portal-worker health deve mostrar agregados operacionais, sem segredos:

```json
{
  "portal_worker": {
    "enabled": true,
    "concurrency_configured": 2,
    "concurrency_effective": 2,
    "redis_lock_ok": true,
    "registry_entries": 14,
    "queued": 0,
    "running": 0,
    "oldest_queue_age_s": 0
  }
}
```

Não fazer `/health` varrer milhares de rows.

## 26.3 Tool Invocation

A partir do cutover, `portal.*` precisa aparecer de verdade em `tool_invocations`.

Este é um critério de aceite, não um detalhe de observabilidade.

---

# 27. BLOCO R — integração com o Auxiliary Factory

A regra canônica da SPEC-058 é:

```text
resolver antes de criar
usar o menor objeto que resolve
Agent-backed é último recurso
```

A 075 aplica isso aos portais.

## 27.1 Auxiliar não recebe Portal Worker diretamente

Errado:

```text
Auxiliar → import portal_worker.journeys.mapfre_corretor
```

Correto:

```text
Auxiliar Release
→ Skill
→ Capability Pack
→ Tool Gateway
→ portal tool
```

## 27.2 Required connectors

Template global declara:

```text
insurance_portal
```

quando precisa portal autenticado.

A instalação não recebe credencial própria.

## 27.3 Cobrança Feita

Continua sendo UM Auxiliar.

Sua cobertura deriva das journeys registradas + contas conectadas.

Adicionar MAPFRE, Zurich ou outra seguradora:

```text
melhora o mesmo Auxiliar
```

não cria card novo.

## 27.4 Novo Auxiliar

Se um Auxiliar futuro precisa `portal.policy_read`, ele referencia uma Skill/Pack que já usa essa Tool.

O Factory deve concluir:

```text
capability existe
connection existe
journey existe para esta seguradora
→ READY
```

ou:

```text
capability existe
connection existe
journey falta
→ capability_gap = portal_implementation_missing
```

## 27.5 Capability Gap útil

Exemplo:

```json
{
  "kind": "portal_implementation_missing",
  "operation_key": "renewal.quote.read",
  "insurer_key": "tokio",
  "portal_key": "tokiomarine_corretor"
}
```

Sem PII.

Isso transforma pedidos reais de corretores em roadmap.

---

# 28. BLOCO S — integração com Agents

## 28.1 Agent não ganha todas as tools de portal

Tool Gateway já limita por Skill/Capability Pack.

Atendente de WhatsApp não recebe automaticamente:

```text
portal.billing_read
portal.policy_read
portal.execute
```

só porque são tools globais.

## 28.2 Progressive disclosure

Durante um atendimento de vidro:

```text
Skill assistência
→ assistance_prepare/read/request
```

Durante cobrança:

```text
Skill cobrança
→ billing_read
```

## 28.3 Subagent

Subagente nunca ganha mais capability que o pai.

Se o Agent pai não pode solicitar assistência material, o subagente também não pode.

## 28.4 Fatos não passam por LLM

Preservar regra já provada:

- placa/apólice/veículo/endereço → InfoCap/provider;
- conta/portal/journey → resolver server-side;
- opções reais → API/DOM;
- LLM decide somente julgamento semântico legítimo.

---

# 29. BLOCO T — integração com Rotinas

Rotina não chama Portal Worker direto após o cutover.

Fluxo:

```text
Rotina
→ Work Run
→ Skill
→ Tool Gateway
→ PortalExecutionGateway
```

**Compatibilidade:** `billing_collection` pode continuar sendo executor especializado chamado pelo Work Run e, internamente, usar o gateway global para cada portal.

Não reescrever a lógica de cobrança como “Skill genérica” só para ficar bonito.

A estrutura canônica permite executor especializado.

---

# 30. BLOCO U — migração da Cobrança Feita SEM regressão

Esta é a linha de controle principal da SPEC.

## 30.1 O que muda

Somente:

```text
_enqueue_job / _poll_job
```

ou sua camada equivalente passa a usar o shared PortalExecutionGateway/adapter.

## 30.2 O que NÃO muda

- quais seguradoras são varridas;
- janela de atraso;
- download de boletos;
- normalização de valores/data;
- identificação do cliente;
- regras de forma de pagamento;
- tarefas humanas;
- approval;
- send mode;
- governor;
- mensagem;
- billing_sent_log;
- retomada oldest-first;
- entrega final.

## 30.3 Compatibilidade de retorno

Se `billing_collection` espera:

```python
job["status"]
job["evidence"]
job["error"]
job["screenshots"]
```

adapter continua entregando esse contrato durante migração.

Não obrigar a rotina inteira a mudar numa tacada só.

## 30.4 Shadow seguro

`PORTAL_EXECUTION_GATEWAY_MODE=shadow` pode:

- resolver qual operation/portal/journey escolheria;
- validar capability/conexão;
- comparar params sanitizados;
- registrar diff.

Mas **NÃO cria segundo `portal_job`**.

Shadow de execução não pode duplicar uma chamada externa.

## 30.5 Gate

Antes de cortar para `on`:

- mesmos portais;
- mesmos fixtures;
- mesmos items;
- mesmos boletos;
- mesmas regras de não-envio;
- zero WhatsApp real em teste;
- Allianz como controle histórico;
- HDI/Tokio/Yelum/MAPFRE/Zurich regressão verde conforme disponibilidade das journeys atuais.

---

# 31. BLOCO V — migração do PortalAction/vidros SEM regressão

## 31.1 Tool LangChain continua existindo

`portal_action` mantém:

- nome;
- schema externo enquanto necessário;
- texto de retorno;
- InfoCap preflight;
- idempotência;
- Vigia;
- heads-up para cliente;
- gate do agente.

## 31.2 Por baixo

A criação/espera do portal job migra para o provider global.

Assim:

```text
portal_action
```

vira adapter da Tool canônica, em vez de autoridade paralela.

## 31.3 Após SPEC-074

As Tools estreitas de assistência devem ser a autoridade para novas Skills.

`portal_action` permanece até o cutover de atendimento provar equivalência.

## 31.4 Nenhuma ação real no shadow

Mesma regra:

- shadow resolve;
- compara;
- não cria segundo pedido.

---

# 32. BLOCO W — prova de reutilização por um SEGUNDO trabalhador

Uma factory não está provada porque o Cobrador continua funcionando.

Precisamos provar reutilização.

Criar um teste/control harness que simula dois chamadores distintos:

```text
Auxiliar A → portal.billing_read
Agent B     → portal.policy_read ou assistance_read
```

Ambos devem:

- usar o mesmo connection resolver;
- usar o mesmo Tool Gateway;
- criar lineage correto;
- não compartilhar dados entre tenants;
- não precisar de login duplicado no template do Auxiliar;
- não importar journey diretamente.

Não é necessário criar um novo Auxiliar comercial fake no banco.

Pode ser fixture/teste de composição usando releases existentes.

---

# 33. BLOCO X — testes de contrato da Factory

## 33.1 Registry

- entry antiga continua resolvendo;
- module/function inexistente falha legível;
- operation query retorna somente support real;
- duplicate operation conflitante reprova;
- `portais_com_cobranca` não muda.

## 33.2 Tool Gateway

- capability ausente nega;
- connection ausente nega;
- approval ausente nega material;
- read não pede approval por engano;
- tool release inexistente nega;
- tool schema inválido reprova publicação/teste.

## 33.3 Resolver

- account de outro tenant é recusado;
- portal errado é recusado;
- account_label errado para multi-account é recusado;
- portal público funciona sem portal_account quando o contrato disser que não requer conta;
- portal autenticado sem conta → needs_connection.

## 33.4 Lineage

- Work Run → Step → Tool Invocation → Portal Job íntegro;
- job legado com NULL lineage continua executável pelo caminho compatível;
- nenhuma FK cross-tenant é aceita pelo service.

## 33.5 Retry

- read transient retry;
- material pré-commit retry se permitido;
- material pós-checkpoint não retry;
- maybe_committed chama reconcile;
- stale material não volta para fila cegamente.

## 33.6 Concurrency

- duas contas diferentes podem executar em paralelo;
- mesma account_label não executa em paralelo;
- dois tenants nunca usam o mesmo lock/acesso;
- lease expirado só é assumido após regra segura;
- Redis indisponível reduz concurrency efetiva a 1;
- dois workers respeitam o mesmo lock distribuído.

## 33.7 Priority/fairness

- priority maior sai antes;
- FIFO dentro da mesma prioridade;
- um tenant não ocupa todos os slots acima do limite configurado;
- job antigo não fica faminto indefinidamente.

## 33.8 Fixtures

- HAR com Authorization é recusado pelo sanitizador;
- CPF/telefone/placa real são detectados;
- fixture material não dispara network;
- expected business state validado.

---

# 34. Mutation tests obrigatórios

Cada proteção abaixo precisa ser quebrada de propósito e o teste precisa ficar vermelho.

1. remover filtro `company_id` de portal account;
2. aceitar account de outro portal;
3. ignorar account_label multi-account;
4. permitir journey desconhecida;
5. expor `journey_key` ao schema do LLM;
6. deixar Tool read executar Journey material;
7. deixar material sem approval;
8. remover idempotency de request material;
9. transformar maybe_committed em retryable;
10. requeue stale material pós-checkpoint;
11. permitir secret no evidence;
12. permitir Authorization em fixture;
13. permitir URL host fora da allowlist;
14. permitir vision confirmar side effect;
15. criar segundo portal job em shadow;
16. quebrar `portais_com_cobranca()` e provar regressão;
17. escolher primeira opção crítica desconhecida;
18. rodar dois jobs na mesma account em paralelo;
19. remover distributed lock com concurrency > 1;
20. permitir Redis down manter concurrency > 1;
21. ignorar priority;
22. ignorar max inflight tenant;
23. não registrar tool_invocation;
24. quebrar linkage portal_job→work_run;
25. criar connection por Auxiliar em vez de reutilizar company connection;
26. tool de nova seguradora criada desnecessariamente em vez de journey;
27. novo Auxiliar cria browser/worker próprio;
28. `portal.execute` vira permissão genérica para qualquer operation;
29. business_blocked vira failed/retry;
30. coverage_absent tenta outro ramo automaticamente.

**Meta:** 30/30 mutações mortas ou justificativa técnica documentada para qualquer mutação substituída por teste estrutural equivalente.

---

# 35. Matriz de regressão obrigatória

## Portal Worker base

- login/session persistence;
- proxy HDI;
- headless new;
- user agent limpo;
- HITL screenshot;
- encrypted sessions;
- storage uploads;
- timeout;
- stale recovery segura;
- account identity.

## Cobrança

- Allianz;
- HDI;
- Tokio;
- Yelum;
- MAPFRE;
- Zurich.

Cada uma conforme o que a journey atual realmente suporta. Não inventar live proof onde só há fixture.

## Vidros

- Yelum fixture/API/DOM;
- Porto fixture/API/DOM;
- coverage absent;
- dynamic questionnaire;
- 204 end;
- transaction guard;
- protocol/franchise/vistoria;
- no duplicate request;
- continuation/reconcile conforme SPEC-074 disponível.

## Work OS

- SPEC-055 work run tests;
- SPEC-056 gateway tests;
- SPEC-058 Auxiliary Factory tests;
- routes/startup se frontend/API tocados.

---

# 36. Evals de onboarding: quanto custa adicionar uma nova journey

A 075 só cumpre seu objetivo se reduzir trabalho repetitivo.

Criar um **Developer Acceptance Scenario**:

> “Adicionar uma nova seguradora fictícia à operação `billing.overdue.list`, usando fixtures apenas.”

O executor deve conseguir:

```text
1. scaffold journey
2. implementar parser
3. adicionar fixture
4. registrar entry
5. rodar validate
6. gerar matrix
7. passar tests
```

sem tocar em:

- Auxiliary Factory;
- Work Run Service;
- Tool Gateway core;
- `billing_collection` business rules;
- UI do Auxiliar;
- Skill global de cobrança;
- capability global.

Se precisar tocar nesses lugares, a Factory ainda não está global.

---

# 37. Readiness de um novo Auxiliar que usa portal

O Dependency Resolver do Factory deve conseguir responder:

```text
AUXILIAR: X
SKILLS: A, B
TOOLS: portal.billing_read
CAPABILITY: operational.portal.billing.read
CONNECTION: insurance_portal
PORTAL IMPLEMENTATIONS:
  Allianz ........ READY
  HDI ............ READY
  Tokio .......... READY
  MAPFRE .......... READY
  Sancor .......... MISSING JOURNEY
```

O card do Auxiliar não precisa expor essa tabela técnica ao corretor.

Para o corretor:

```text
“Seu portal está conectado. Este Auxiliar consegue trabalhar com 5 das 6 seguradoras configuradas. Sancor ainda não está automatizada.”
```

Sem fingir cobertura 100%.

---

# 38. Não transformar portal coverage em configuração manual do tenant

Cobertura de capacidade é global:

```text
AutoBrokers sabe ou não sabe executar journey X naquele portal.
```

Credencial é tenant:

```text
esta corretora tem ou não tem acesso ao portal.
```

Não gravar no tenant:

```text
"supports_billing": true
```

se isso é verdade global do código.

A matriz global deriva do registry.

---

# 39. Portal API-first sem virar dependência frágil

A 073/074 estabelecem:

```text
API legítima → DOM → adaptive → vision → humano
```

A 075 torna isso padrão de onboarding.

Cada nova journey deve documentar:

```text
primary_path = api | dom
fallbacks = [...]
api_hosts = [...]
transaction_boundary = ...
```

Mas:

- API interna não é promessa eterna;
- DOM fallback deve existir onde viável;
- vision não vira executor padrão de tudo;
- endpoint descoberto não é hardcoded com token/session id;
- erro de schema precisa produzir drift, não dado silenciosamente errado.

---

# 40. Performance e custo

## 40.1 Métricas

Por `(operation, portal)`:

```text
queue p50/p95
runtime p50/p95
login rate
session reuse
API calls
DOM actions
vision calls
needs_human rate
retry rate
success rate
```

## 40.2 Vision

Vision é fallback.

Se 90% das execuções conhecidas começam a chamar visão, isso é sinal de:

```text
DOM/API adapter regrediu
```

não “o agente ficou mais inteligente”.

## 40.3 Browser

Não abrir browser novo para cada sub-etapa da mesma portal_job se o contexto seguro pode ser reutilizado dentro dela.

Não manter browser vivo esperando horas por usuário.

## 40.4 Sessão

Reuso por `company + portal + account_label` continua.

---

# 41. Gate de segurança comercial: Agents e Auxiliares podem usar, mas não podem se autorizar

Uma Capability disponível na plataforma NÃO significa que todo trabalhador pode executá-la.

Fluxo:

```text
Skill pede capability
→ Capability Binding permite papel/trabalhador
→ tenant entitlement
→ connection
→ Tool Gateway
→ approval se necessário
→ execução
```

Auxiliar não passa por cima de approval porque “é automático”.

Rotina não passa por cima porque “já estava agendada”.

Agent não passa por cima porque “decidiu sozinho”.

---

# 42. Aprovação — não confundir approval do Work OS com `confirm` de portal

São níveis diferentes.

```text
Approval do Work OS
  = alguém autorizou a ação de negócio

confirm / transaction boundary da journey
  = mecanismo técnico que impede o clique sem autorização válida
```

A journey material só atravessa o boundary quando o runtime consegue comprovar a aprovação/policy apropriada.

Nenhum `confirm=True` vindo diretamente do LLM.

---

# 43. UI e Admin — mínimo necessário, sem criar produto técnico para o corretor

## 43.1 Corretor

Não criar menu “Portal Worker”.

Ele vê:

- Conectores;
- Auxiliares;
- Trabalhos;
- Atendimento;
- resultado.

Infrastructure fica invisível.

## 43.2 Admin global

A matriz gerada pode alimentar uma tela read-only futura/existente:

```text
Portal Capability Matrix
```

com:

- coverage;
- readiness;
- last canary;
- drift;
- health.

Não criar dashboard enorme se o markdown/JSON + Admin atual resolve na primeira entrega.

## 43.3 Readiness de Auxiliar

A UI pode mostrar conexão faltante usando `required_connectors` já existente.

Não criar um segundo readiness engine.

---

# 44. O que a SPEC explicitamente NÃO fará

- não substitui Playwright por Stagehand;
- não instala Browser Use como segundo runtime;
- não instala Skyvern como segundo runtime;
- não usa Firecrawl para navegar portal autenticado principal;
- não cria portal-worker-v2;
- não cria registry v2;
- não cria fila Redis concorrente;
- não cria Work Run de portal separado;
- não cria Auxiliar por seguradora;
- não cria Tool por seguradora;
- não cria Skill por seguradora sem diferença real de procedimento;
- não move credenciais para templates;
- não põe navegador dentro do Smith Worker;
- não envia HAR bruto ao GitHub;
- não ativa operação material apenas porque fixture passou;
- não faz refactor cosmético de journeys que já funcionam;
- não mexe no RAG/Memory/Qdrant;
- não mexe em lógica de cobrança além da ponte de execução;
- não amplia escopo de WhatsApp;
- não usa a 075 para terminar medições da Regina da SPEC-074.

---

# 45. Arquivos que provavelmente serão alterados

**Confirmar pelo código real antes de editar.**

Core provável:

```text
backend/portal_worker/journeys/__init__.py
backend/portal_worker/worker.py
backend/app/services/skills/gateway.py ou executor/provider irmão já existente
backend/app/services/portals/*               # adapter global, se ainda não existir
backend/app/services/billing_collection.py   # somente adapter de enqueue/poll
backend/app/agents/tools/portal_tool.py       # somente adapter
backend/app/agents/tools/portal_params.py     # apenas se contrato exigir
backend/app/services/work/workflows.py        # lineage/provider bridge, se necessário
backend/app/services/auxiliaries/factory.py   # readiness/gap somente se necessário
backend/scripts/portal_factory.py
backend/tests/fixtures/portal_worker/*
backend/tests/test_spec075_*.py
docs/generated/portal-capability-matrix.*
docs/canon/CHANGE-ADDENDA.md
docs/canon/PENDENCIAS.md
docs/canon/specs/README.md
```

Migration:

```text
backend/supabase/migrations/<NEXT>_spec075_portal_job_lineage_priority.sql
```

Não escolher `<NEXT>` sem ler `MIGRATIONS-AUTHORITY` + migrations vivas.

---

# 46. Arquivos/sistemas que devem permanecer fora do diff salvo necessidade comprovada

```text
RAG
Qdrant
Memory Fabric
DocumentService
IngestionService
MinIO geral
Atlas/URA
corridor_playbooks
WhatsApp pairing
billing pricing
Supabase plan
front-end amplo
```

MinIO/Storage `portal-evidence` pode ser usado pelo runtime existente; não redesenhar armazenamento.

---

# 47. Sequência de execução em linha reta

> **Não pedir aprovação do Founder entre passos técnicos verdes.** Pare somente nas condições do `CLAUDE.md`.

## PASSO 0 — preflight

- Git/worktrees/stash;
- HEAD;
- branch;
- baseline tests;
- schema vivo read-only.

## PASSO 1 — confirmar dependências

- estado real SPEC-073;
- estado real SPEC-074;
- não duplicar nada que elas já criaram.

## PASSO 2 — snapshot de regressão

Rodar e guardar saída de:

- Portal Worker tests;
- Cobrança tests;
- Vidros tests;
- SPEC-055;
- SPEC-056;
- SPEC-058.

## PASSO 3 — censo dos escritores de `portal_jobs`

Grep completo.

Classificar:

```text
canonical candidate
compatibility writer
test/admin
legacy/dead
```

Não migrar um escritor que não existe mais.

## PASSO 4 — enriquecer o registry

`JourneyDefinition` compatível + introspecção.

Gate.

## PASSO 5 — testes/mutações do registry

Verde antes de seguir.

## PASSO 6 — preparar migration

APPLY/VERIFY/ROLLBACK escritos.

## PASSO 7 — aplicar migration expand-only

Somente após censo confirmar necessidade.

## PASSO 8 — VERIFY migration

Contagens/status intactos + EXPLAIN claim.

## PASSO 9 — criar contratos globais de PortalExecution

Input/result semântico.

## PASSO 10 — implementar connection resolver

Reusar fontes atuais; zero segredo em retorno.

## PASSO 11 — implementar PortalExecutionGateway/provider

Sem trocar chamadores ainda.

## PASSO 12 — unit tests do gateway

Tenant, capability, operation, account, effect class, idempotency.

## PASSO 13 — completar Tool Releases de portal

Schemas + execution manifests versionados.

Não editar release publicada in-place; criar release nova conforme SPEC-056.

## PASSO 14 — tools estreitas de assistência

Somente sobre capabilities já existentes e contratos da 074.

## PASSO 15 — costurar provider ao Tool Gateway executor real

Depois disso uma invocação autorizada consegue criar um portal job real por provider.

## PASSO 16 — lineage

Tool Invocation → Portal Job → Work Run/Step.

## PASSO 17 — fixture/replay harness

Sem rede material.

## PASSO 18 — Portal Factory CLI

Audit/scaffold/validate/replay/matrix.

## PASSO 19 — integrar outputs do Profiler

Sanitização + proposed candidates.

## PASSO 20 — readiness/score

Sem tabela nova por conveniência.

## PASSO 21 — docs geradas

Matrix MD/JSON.

## PASSO 22 — concurrency + Redis leases

Começa default 1.

## PASSO 23 — priority + fairness

Claim index + limits.

## PASSO 24 — recovery/retry class-aware

Checkpoint material respeitado.

## PASSO 25 — migrar Cobrança Feita para adapter

`shadow` primeiro, sem segundo job.

## PASSO 26 — prova de equivalência Cobrança

Fixtures + regressão 6 insurers.

## PASSO 27 — cutover Cobrança para `on`

Somente se equivalência verde.

## PASSO 28 — migrar `portal_action`/vidros para adapter

Preservar interface.

## PASSO 29 — prova de equivalência Vidros

Yelum + Porto fixtures/gates da 074.

## PASSO 30 — prova “segundo trabalhador”

Dois callers reutilizando mesma plataforma sem import direto de journey.

## PASSO 31 — mutation pack completo

30 proteções.

## PASSO 32 — deploy com concurrency=1

API/worker/portal-worker conforme diff.

## PASSO 33 — health/smoke

Sem execução material.

## PASSO 34 — Amandus canário read-only

Uma operation real read-only.

Provar:

```text
work_run
→ tool_invocation
→ portal_job
→ journey
→ resultado
```

## PASSO 35 — validar `tool_invocations` portal > 0

Sem isso, ponte não está provada.

## PASSO 36 — subir concurrency para 2 em canário

Somente com Redis lock green.

## PASSO 37 — teste de duas contas distintas

Paralelo sem colisão.

## PASSO 38 — teste mesma conta

Segundo job aguarda lease.

## PASSO 39 — Resulta / AutoFleet read-only

Somente com autorização/credenciais existentes, sem side effect.

## PASSO 40 — canário transacional

Somente se houver caso legitimamente autorizado pelo Founder e seguindo SPEC-074/approval.

## PASSO 41 — matrix final + report

Atualizar docs/Pendências.

## PASSO 42 — fechar SPEC

Nenhum motor paralelo; zero regressão; handoff de próximas capabilities.

---

# 48. Gates automáticos por bloco

## Gate A — contrato/registry

```text
registry único
compatibilidade 100%
portais_com_cobranca igual baseline
mutações verdes
```

## Gate B — Work OS bridge

```text
capability revalidation
tool schema
portal provider
lineage
zero secret
```

## Gate C — Factory

```text
fixture
replay
scaffold
validate
matrix
```

## Gate D — escala

```text
concurrency 1 igual baseline
lock distribuído
priority
fairness
Redis-down safe
```

## Gate E — zero regressão

```text
Cobrança
Vidros
Work Run
Tool Gateway
Auxiliary Factory
```

## Gate F — live proof

```text
Amandus read-only
portal tool_invocation real
no P0/P1
```

---

# 49. Rollback

## Registry

Git revert do commit. Compat aliases permitem retorno.

## Migration

Preferir deixar colunas inertes em rollback de código.

## PortalExecutionGateway

Flag:

```text
PORTAL_EXECUTION_GATEWAY_MODE=legacy|shadow|on
```

ou mecanismo equivalente já existente.

Rollback:

```text
on → legacy
```

sem migration destrutiva.

## Concurrency

```text
PORTAL_WORKER_CONCURRENCY=1
```

retorna ao comportamento serial.

## Tool releases

Rollback por release default anterior, seguindo SPEC-056.

Não editar release imutável.

## Cobrança

Adapter deve permitir voltar ao writer legado enquanto canário estiver aberto.

## Vidros

Mesmo princípio.

---

# 50. O que fica pendente legitimamente

A 075 deve terminar com PENDÊNCIAS somente quando dependem de mundo externo.

Exemplos legítimos:

```text
🧑 acesso real a portal ainda não fornecido
🧑 QR/2FA/passkey
🧑 atendimento real da Regina para fechar tela final SPEC-074
🧑 autorização para side effect real
🤖 journey de seguradora ainda não implementada
🤖 fixture de um portal ainda ausente
```

Não deixar como pendência:

```text
“ligar Tool Gateway depois”
“fazer lineage depois”
“criar testes depois”
“integrar Auxiliary Factory depois”
```

Essas são o objetivo desta SPEC.

---

# 51. Definition of Done

A SPEC-075 está concluída quando TODAS as afirmações abaixo são verdadeiras.

## Arquitetura

- [ ] existe um único caminho canônico Work OS → Tool Gateway → Portal Provider → Portal Worker;
- [ ] caminhos legados críticos são adapters ou estão explicitamente em cutover;
- [ ] não existe segundo registry;
- [ ] não existe segundo worker/runtime;
- [ ] `portal_jobs` está ligado a Work Run/Tool Invocation quando chamado pelo caminho canônico.

## Reutilização

- [ ] um Agent autorizado consegue usar capability de portal sem conhecer journey;
- [ ] um Auxiliar autorizado consegue usar a mesma capability;
- [ ] uma Rotina aciona pelo Work Run;
- [ ] a conexão da corretora é reutilizada;
- [ ] nova seguradora de cobrança não exige novo Auxiliar/Tool/Skill.

## Factory

- [ ] scaffold existe;
- [ ] validate existe;
- [ ] replay existe;
- [ ] matrix existe;
- [ ] fixture contract existe;
- [ ] capability gap é registrado quando implementação falta.

## Segurança

- [ ] zero cross-tenant;
- [ ] zero segredo em evidence/fixture/log;
- [ ] approval material comprovado;
- [ ] idempotência material comprovada;
- [ ] maybe_committed não repete;
- [ ] account identity multi-account protegida;
- [ ] hosts allowlisted.

## Escala

- [ ] concurrency configurável;
- [ ] mesma account serializada por lease;
- [ ] duas accounts podem executar em paralelo;
- [ ] Redis down não produz corrida;
- [ ] priority funciona;
- [ ] fairness mínima por tenant funciona.

## Regressão

- [ ] Cobrança Feita igual ou melhor;
- [ ] nenhum envio real ocorrido em regressão;
- [ ] Vidros igual ou melhor;
- [ ] Work Run tests verdes;
- [ ] Tool Gateway tests verdes;
- [ ] Auxiliary Factory tests verdes;
- [ ] 30 mutações mortas.

## Prova real

- [ ] pelo menos uma Tool `portal.*` possui `tool_invocation` real canário;
- [ ] essa invocation aponta para um `portal_job`;
- [ ] o `portal_job` aponta para Work Run/Step quando aplicável;
- [ ] resultado chegou ao chamador;
- [ ] matrix/readiness registra a prova.

---

# 52. Critérios de qualidade — o que significa “Portal Worker próximo de 100/100”

Não significa:

```text
“nunca haverá erro externo”
```

Significa:

```text
não escolhe sem saber
não cruza tenant
não perde segredo
não duplica efeito
não confunde falha com negócio
não repete pós-commit
não cria arquitetura por seguradora
não cria login por Auxiliar
não bloqueia atendimento atrás de rotina pesada
sabe qual camada falhou
sabe como retomar
sabe quando pedir humano
sabe provar o que fez
```

A meta de excelência é:

> **qualquer falha possível vira um estado seguro e diagnosticável, não uma ação errada silenciosa.**

---

# 53. Exemplos futuros — para provar que a arquitetura não é só “cobrança + vidro”

Estes são exemplos de validação arquitetural, não autorização para implementá-los nesta SPEC.

## Renovação

```text
Auxiliar Renovação Máxima
→ Skill renewal.review
→ portal.policy_read / future renewal tools
→ mesma connection
→ journey da seguradora
```

## Cotação

```text
Agent comercial
→ Skill quote.prepare
→ capability de cotação
→ portal provider
```

Side effect de cotação/publicação teria policy própria.

## Comissão

```text
Auxiliar Caça Comissão
→ read portal
→ baixar demonstrativo
→ artifact
```

## Sinistro

```text
Atendente
→ Skill de abertura
→ prepare/read/request
→ HITL conforme risco
```

## Documentos

```text
Core/Auxiliar
→ portals.read_business_document
→ portal.policy_read / document read capability
```

Todos usam **o mesmo motor**.

---

# 54. A métrica estratégica da SPEC

Depois da 075, medir mensalmente:

```text
novas journeys adicionadas
% que reutilizaram Tool/Skill existentes
tempo mediano do discovery ao fixture green
tempo mediano do fixture green ao canário
% execuções API-first
% DOM
% vision
% needs_human
% portal_changed
% safe recovery
incidentes de duplicidade material
incidentes cross-tenant
```

Metas de direção, não promessas sem baseline:

- reutilização de Tool/Skill deve tender a subir;
- tempo para nova seguradora deve cair;
- vision deve ficar minoritária nos caminhos maduros;
- duplicidade material = zero;
- cross-tenant = zero.

---

# 55. Relatório final obrigatório

Usar template canônico da SPEC.

Incluir:

## Git

```text
HEAD inicial
branch
commits
HEAD final
diff stat
```

## Schema

```text
censo antes
migration APPLY
VERIFY real
ROLLBACK definido
censo depois
```

## Registry

```text
entries antes/depois
business operations
compat aliases
matrix gerada
```

## Tool Gateway

```text
releases criadas
schemas
provider adapter
portal tool invocations antes/depois
```

## Work OS

```text
Work Run → Step → Invocation → Portal Job
```

com IDs de canário redigidos apenas no relatório interno permitido.

## Factory

```text
scaffold
validate
replay
score
matrix
```

## Performance

```text
concurrency 1
concurrency 2
queue wait
locks
fairness
```

## Regressão

Tabela:

```text
Allianz cobrança
HDI cobrança
Tokio cobrança
Yelum cobrança
MAPFRE cobrança
Zurich cobrança
Yelum vidros
Porto vidros
```

marcando:

```text
FIXTURE
DRY_RUN
CANARY_READONLY
CANARY_TRANSACTIONAL
NOT_RUN
```

Nunca promover fixture a “produção validada”.

## Mutations

30 proteções e resultado.

## Pendências

Somente externas/materialmente bloqueadas.

## Declaração final

> “Nenhum runtime, registry, scheduler, queue universal, Tool Gateway, Skill Registry, Auxiliary Factory ou Work Run paralelo foi criado.”

---

# 56. Handoff depois da SPEC-075

Com 073 + 074 + 075 concluídas, o programa de portais muda de natureza.

Antes:

```text
“precisamos automatizar a seguradora X”
→ projeto quase do zero
```

Depois:

```text
“precisamos que a seguradora X faça a operação Y”
→ discovery
→ decidir se Y já é operation conhecida
→ journey + fixture
→ validate
→ canário
→ entra no arsenal global
```

Essa é a base necessária para escalar:

- cobrança;
- renovação;
- cotação;
- comissões;
- documentos;
- assistência;
- sinistro;
- pós-venda;
- qualquer futuro Auxiliar ou Agent autorizado.

A próxima SPEC de domínio não deve voltar a construir infraestrutura genérica de browser. Ela deve **consumir esta Factory** e acrescentar operações de negócio concretas.

---

# 57. Comando final ao Claude Code

> Execute esta SPEC como uma **integração e cutover das autoridades que já existem**, não como uma reescrita do Portal Worker.
>
> O sucesso não é ter mais arquivos. É fazer com que o mesmo browser worker que hoje cobra boletos e abre vidros se torne uma capability governada, reutilizável e escalável do Work OS.
>
> Preserve tudo que funciona. Antes de mudar um caminho da Cobrança Feita ou do Portal de Vidros, capture a baseline. Depois da mudança, prove equivalência. Uma abstração nova que não consegue passar pela linha de controle antiga não entra.
>
> Em toda decisão de desenho, prefira:
>
> ```text
> reusar > criar
> compor > duplicar
> fato > LLM
> API legítima > DOM > visão
> read > write
> reconcile > retry cego
> capability estreita > poder genérico
> connection da corretora > conexão por Auxiliar
> Work Run > histórico paralelo
> fixture + canário > confiança por leitura de código
> ```
>
> Não pare por microdecisões. Pare somente pelas condições legítimas do `CLAUDE.md`: risco de dados, segurança/cross-tenant, decisão comercial/material, acesso físico, custo extraordinário ou conflito canônico.

