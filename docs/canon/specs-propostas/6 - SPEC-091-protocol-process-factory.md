# SPEC-091 — PROTOCOL & PROCESS FACTORY
## Todo processo importante vira um protocolo executável, versionado, portátil, verificável e ensinável a qualquer LLM

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANDIDATE SPEC — pronta para aquecimento pelo Protocolo AutoBrokers AAA; ainda não executada  
**Data da redação:** 25/08/2026  
**Baseline de repositório observado:** `19f41eedc5808cf1099ede19d2a88be502854485` (`main`)  
**Branch sugerida para execução:** `feat/spec091-protocol-process-factory`  
**Autoridades superiores:** SPEC-052, SPEC-053, SPEC-055, SPEC-056, SPEC-058, SPEC-090 e `PROTOCOLO-AUTOBROKERS-AAA.md` v9  
**Autoridades preservadas:** Smith, Work Runs, Skill Registry, Tool Gateway, Capability Registry, Vault, Artifact Hub, Auxiliary Factory, Candidate/Intelligence Factory  
**Prepara diretamente:** SPEC-093, 098, 099, 100, 102, 103, 105, 106, 107, 108 e 109  
**Research Pack:** `SPEC-091-protocol-process-factory-RESEARCH-PACK.md`

---

# 0. RESULTADO EM UMA FRASE

> **Qualquer processo importante do AutoBrokers — criar uma SPEC, criar uma Skill, criar um Auxiliar, integrar um sistema, construir uma rota, executar uma migration, fazer rollback ou responder a um incidente — poderá ser empacotado como um contrato operacional portátil que um agente novo, sem memória da conversa anterior, consegue descobrir, carregar progressivamente, executar, provar, registrar e melhorar sem depender de conhecimento escondido na cabeça de um chat antigo.**

A arquitetura final:

```text
PROCESS / KNOW-HOW REAL
        ↓
PROTOCOL CANDIDATE
        ↓
PROTOCOL FACTORY
        ↓
CANONICAL PROTOCOL PACKAGE
        │
        ├─ SKILL.md ............. instruções portáveis
        ├─ protocol.yaml ........ contrato AutoBrokers
        ├─ references/ .......... contexto sob demanda
        ├─ scripts/ ............. operações determinísticas
        ├─ tests/ ............... evals, controles, mutações
        └─ assets/ .............. templates e fixtures
        ↓
VALIDATE / CLEAN-ROOM EXECUTION
        ↓
IMMUTABLE RELEASE
        ↓
EXECUTION PACKET
        ↓
CLAUDE CODE / CODEX / COPILOT / OUTRO HARNESS
        ou
AUTOBROKERS SKILL + WORK RUN
        ↓
PROTOCOL EXECUTION RECORD
        ↓
SPEC-090 LEARNING SIGNAL
        ↓
SPEC-106 DREAMS
        ↓
PROTOCOL IMPROVEMENT CANDIDATE
```

---

# 0.1 A DECISÃO MAIS IMPORTANTE DA SPEC

## NÃO CRIAR UM PROTOCOL REGISTRY PARALELO

A SPEC-056 já decidiu:

```text
Skill = procedimento versionado para produzir um resultado
```

e já implementou:

- Skill Registry;
- releases imutáveis;
- manifestos;
- content hash;
- progressive disclosure;
- Capability Packs;
- Tool Gateway;
- bindings;
- autorização independente da Skill.

Portanto:

> **Protocol não será uma segunda autoridade de “como fazer”.**

A 091 cria um **Protocol Profile / Protocol Package** compatível com Agent Skills e uma Factory para autoria, validação, portabilidade e aprendizagem.

Quando um Protocol precisar ser executado dentro do runtime do produto:

```text
Protocol Package
→ compile/publish
→ Skill Release existente
→ Tool Gateway
→ Work Run
```

O Skill Registry continua sendo a autoridade de runtime.

---

# 0.2 DOIS PLANOS, UMA ONTOLOGIA

## BUILD / ENGINEERING PLANE

Processos para construir, operar e evoluir o AutoBrokers.

Exemplos:

- criar SPEC;
- executar SPEC;
- criar Skill;
- criar Auxiliar;
- criar Connector;
- integrar Quiver/Segfy;
- criar rota;
- criar integração com seguradora;
- executar migration;
- incident response.

Autoridade source-controlled:

```text
Canonical Protocol Package no repositório
```

## PRODUCT / RUNTIME PLANE

Procedimentos usados pelo AutoBrokers para entregar outcomes ao corretor.

Autoridade:

```text
Skill Registry
+
Capability Registry
+
Tool Gateway
+
Work Run
```

Um Protocol do Build Plane pode ser compilado/exportado para uma Skill quando isso fizer sentido.

Não são duas verdades concorrentes.

São:

```text
SOURCE PACKAGE
→ DEPLOYED RUNTIME RELEASE
```

como código-fonte → artefato publicado.

---

# 0.3 PROTOCOLO NÃO É DOCUMENTAÇÃO

Um documento diz:

> “faça estes passos.”

Um Protocol precisa responder:

```text
qual outcome?
quando usar?
quando NÃO usar?
quais inputs?
quais pré-condições?
quais arquivos/fontes?
quais poderes?
quais invariantes?
quais passos?
como provar cada passo?
o que pode falhar?
como detectar?
qual fallback?
qual rollback?
qual Definition of Done?
quais evals?
quais mutações precisam ficar vermelhas?
quais evidências precisam ser registradas?
```

Sem prova executável:

```text
manual
```

Com contrato + controle + evidence:

```text
protocol
```

---

# 0.4 NÃO TRANSFORMAR TODO PROCESSO EM SKILL

O Factory deve decidir o objeto correto.

```text
PROCESS OBSERVADO
     ↓
CLASSIFIER
     ├─ Protocol
     ├─ Skill
     ├─ Workflow
     ├─ Runbook
     ├─ Playbook
     ├─ Checklist
     ├─ SOP projection
     └─ simplesmente documentação
```

A 091 não infla o Skill Registry com coisas que não são procedimentos executáveis.

---

# 1. POR QUE A 091 EXISTE AGORA

O projeto já acumulou muito conhecimento operacional:

- como escrever uma SPEC;
- como executar SPEC com AAA;
- como fazer um corredor;
- como testar atendimento;
- como publicar Skill;
- como criar Auxiliar;
- como operar Work Runs;
- como trabalhar com Atlas;
- como investigar banco;
- como fazer migrations;
- como fazer canário;
- como provar segurança;
- como não repetir arquitetura.

Hoje uma parte desse conhecimento está:

- em SPECs;
- em `CLAUDE.md`;
- em reports;
- em prompts antigos;
- em comentários de código;
- na memória de conversas;
- em arquivos de processo;
- e, perigosamente, na lembrança de quem executou.

A 091 transforma isso em conhecimento operacional reutilizável.

---

# 1.1 A DOR FOI MEDIDA PELO PRÓPRIO AAA v9

O protocolo AAA v9 encontrou que o maior custo recente não era o painel de juízes.

Era o **pedágio de entrada**:

```text
agentes lendo contexto demais
antes de produzir trabalho de produto
```

E também encontrou que o juiz estava sendo usado no alvo errado:

```text
julgar documento
em vez de julgar código funcionando
```

A 091 incorpora essas duas lições:

> **Protocol entrega pacote mínimo, não cânon inteiro.**

> **Qualidade é provada executando o processo e verificando o resultado, não criando voltas intermináveis sobre Markdown.**

---

# 2. ONTOLOGIA OFICIAL

## 2.1 Outcome

Resultado desejado.

Exemplo:

```text
“uma nova SPEC pronta para execução”
```

---

## 2.2 Process

Descrição abstrata de uma sequência recorrente de trabalho.

Pode ter sido:

- declarada;
- observada;
- descoberta por Trajectories;
- inferida de operações repetidas.

Process ainda não é necessariamente executável.

---

## 2.3 Protocol

Contrato operacional reutilizável e versionado que ensina um executor a produzir um Outcome e a provar que o produziu corretamente.

Protocol:

- não concede permissão;
- não substitui Skill;
- não é runtime;
- não é Agent;
- não é prompt solto.

---

## 2.4 Skill

Autoridade da SPEC-056.

Procedimento versionado que o runtime usa para produzir um resultado.

Quando Protocol é usado dentro do produto:

```text
Protocol source
→ Skill Release
```

---

## 2.5 Workflow

Sequência/state machine de execução concreta.

Pode implementar parte ou todo um Protocol.

---

## 2.6 Runbook

Protocol especializado para:

- incidente;
- manutenção;
- recuperação;
- operação técnica.

---

## 2.7 Playbook

Guia adaptativo.

Pode oferecer estratégias e alternativas, não necessariamente uma sequência única.

---

## 2.8 SOP

Projeção humano-legível de um Protocol.

SOP não é autoridade separada.

---

## 2.9 Checklist

Conjunto de verificações.

Pode ser recurso de um Protocol.

Não substitui o Protocol.

---

## 2.10 SPEC

Contrato de mudança de produto.

Define:

```text
o que precisa existir depois
```

Não é o procedimento reutilizável para criar qualquer SPEC.

Esse procedimento será:

```text
protocol engineering-create-spec
```

---

## 2.11 Agent

Executor cognitivo.

Não é o Protocol.

---

## 2.12 Hook / Gate

Controle programático executado em ponto conhecido.

Exemplo:

- preflight;
- pre-tool validation;
- post-tool verification;
- final gate.

---

## 2.13 Eval

Teste comportamental.

Pergunta:

> “o Protocol fez o agente entregar corretamente?”

---

## 2.14 Protocol Package

Diretório canônico que contém o Protocol e seus recursos.

---

## 2.15 Protocol Release

Snapshot imutável e hashado do Package aprovado.

---

## 2.16 Execution Packet

Pacote mínimo que um executor recebe para uma execução específica.

---

## 2.17 Protocol Execution Record

Registro estruturado do que realmente aconteceu.

---

## 2.18 Protocol Candidate

Proposta de criar ou melhorar Protocol.

Pode nascer de:

- Founder;
- operador;
- SPEC-090 Process Candidate;
- execução repetida;
- falha;
- Dreams;
- drift.

---

# 3. AUTORIDADES

```text
REUSABLE BUILD KNOW-HOW
→ Protocol Package (Git source-controlled)

RUNTIME PROCEDURE
→ Skill Registry

PERMISSION
→ Capability Registry

TOOL EXECUTION
→ Tool Gateway

DURABLE PRODUCT EXECUTION
→ Work Run

QUALITY GOVERNANCE
→ PROTOCOLO AUTOBROKERS AAA

PROCESS LEARNING
→ SPEC-090

BACKGROUND CONSOLIDATION
→ SPEC-106
```

Nenhuma peça da 091 pode tomar autoridade das demais.

---

# 4. FORMATO CANÔNICO DO PROTOCOL PACKAGE

Local sugerido:

```text
docs/canon/protocols/<protocol-key>/
```

Exemplo:

```text
docs/canon/protocols/engineering-create-spec/
├── SKILL.md
├── protocol.yaml
├── references/
│   ├── spec-structure.md
│   ├── authority-map.md
│   └── examples.md
├── scripts/
│   ├── preflight.py
│   ├── validate.py
│   └── evidence.py
├── tests/
│   ├── cases.yaml
│   ├── negative-cases.yaml
│   └── mutations.yaml
└── assets/
    ├── spec-template.md
    └── execution-report-template.md
```

`SKILL.md` segue o Agent Skills open standard.

`protocol.yaml` contém extensões estruturadas do AutoBrokers.

Diretórios adicionais são permitidos pelo padrão aberto.

---

# 4.1 POR QUE NÃO COLOCAR O CANÔNICO DIRETAMENTE EM `.claude/skills`

Repository Skills são instruções executáveis e fazem parte da trust boundary do Agent.

Colocar todos os Protocols diretamente numa pasta auto-discovered:

- aumenta superfície de prompt/instruction supply chain;
- pode ativar Protocol sem intenção;
- mistura canônico com adapter de harness.

Portanto:

```text
docs/canon/protocols/
= SOURCE

.generated/.agents/skills/
ou pacote exportado
= PROJECTION / ADAPTER
```

O warm-up valida a melhor implementação prática para Git/Windows/CI sem cópias manuais divergentes.

---

# 5. AGENT SKILLS COMO FORMATO DE PORTABILIDADE

A 091 adotará o padrão aberto Agent Skills como **formato externo de portabilidade**, não como autoridade de autorização.

Estrutura compatível:

```text
SKILL.md
scripts/
references/
assets/
```

Benefícios:

- Claude Code;
- Claude API/Managed Agents;
- GitHub Copilot;
- OpenAI Skills / Codex;
- outros clientes compatíveis.

Objetivo:

> **Escrever o know-how uma vez e transportar para vários harnesses.**

---

# 5.1 `allowed-tools` NÃO CONCEDE PODER

O campo `allowed-tools` do Agent Skills é experimental e varia por implementação.

No AutoBrokers:

```text
Skill/Protocol may request
```

mas:

```text
Capability Registry + Tool Gateway decide
```

Sempre.

---

# 6. PROGRESSIVE DISCLOSURE OBRIGATÓRIO

A arquitetura usa níveis.

## L0 — Catalog metadata

Sempre disponível:

- name;
- description;
- protocol type;
- when to use;
- compatibility.

Alvo:

```text
~50–150 tokens por Protocol
```

## L1 — Core Instructions

`SKILL.md`.

Somente quando Protocol é ativado.

Meta:

```text
< 5.000 tokens
< 500 linhas
```

## L2 — References

Só quando etapa/condição exigir.

Exemplo:

> “Se houver migration, leia `references/migrations.md`.”

## L3 — Scripts / Validators

Executar sem carregar código inteiro no contexto.

## L4 — Evidence / Historical examples

Somente para diagnóstico específico.

---

# 6.1 REGRA CONTRA O “PEDÁGIO DE ENTRADA”

Um Protocol nunca pode dizer:

```text
“leia todo docs/canon”
```

ou:

```text
“leia PENDENCIAS.md inteiro”
```

Deve pedir:

```text
arquivos exatos
+
seções exatas
+
IDs exatos
+
gates exatos
```

O Execution Packet é a materialização disso.

---

# 7. PROTOCOL MANIFEST

`protocol.yaml` mínimo:

```yaml
protocol_key: engineering.create_spec
name: Create AutoBrokers SPEC
version: 1.0.0
protocol_type: engineering
status: candidate

outcome:
  description: Produce an executable Candidate SPEC
  artifact_type: markdown_spec

triggers:
  - create a new spec
  - design a new autobrokers feature

inputs:
  required: []
  optional: []

preconditions: []

invariants: []

dependencies:
  specs: []
  protocols: []
  skills: []
  capabilities: []

permissions:
  effect_class: read_only

quality:
  profile: autobrokers_aaa
  cannot_lower_runtime_risk: true

evidence_required: []

definition_of_done: []

failure_modes: []

rollback: []

eval_pack: tests/cases.yaml

compatibility:
  agent_skills: true

exports:
  - generic-agent-skill
```

---

# 7.1 CAMPOS OBRIGATÓRIOS REAIS

Todo Protocol publicado deve ter:

- `protocol_key`;
- title/name;
- semantic version;
- description;
- when-to-use;
- when-not-to-use;
- owner;
- source;
- status;
- Outcome;
- inputs;
- outputs/artifacts;
- preconditions;
- postconditions;
- touched surfaces;
- invariants;
- dependencies;
- required permissions;
- possible side effects;
- approval requirements;
- steps/phases;
- controls;
- evidence;
- failure modes;
- fallback;
- rollback when applicable;
- Definition of Done;
- quality profile;
- eval pack;
- compatibility;
- content hash.

---

# 8. UM PASSO BOM POSSUI CONTROL

Formato conceitual:

```yaml
- id: inspect-current-state
  action: Measure the current implementation before editing
  type: investigation

  evidence:
    - current commit
    - files touched
    - live schema facts

  control:
    assertion: No new registry is required
    method: search repository + inspect live schema

  on_fail:
    action: stop-and-replan
```

> **Action sem Control é instrução. Action + Control é Protocol.**

---

# 9. PASSOS NÃO PRECISAM SER TODOS LLM

Tipos:

```text
DETERMINISTIC
LLM
HUMAN
TOOL
SCRIPT
WORK_RUN
APPROVAL
INVESTIGATION
```

Preferir determinístico quando possível.

---

# 10. PROTOCOL FACTORY

Fluxo:

```text
INTAKE
↓
AUTHORITY CENSUS
↓
PROCESS CLASSIFICATION
↓
OUTCOME CONTRACT
↓
BASELINE / FAILURES
↓
EXTERNAL REFERENCES
↓
EVALS FIRST
↓
MINIMAL PROTOCOL
↓
STATIC VALIDATION
↓
CLEAN-ROOM EXECUTION
↓
DYNAMIC EVAL
↓
SECURITY / MUTATIONS
↓
PUBLISH RELEASE
↓
EXPORT ADAPTERS
↓
OBSERVE EXECUTIONS
```

---

# 10.1 INTAKE

Entrada:

- objetivo;
- problema;
- processo atual;
- fonte;
- criticidade.

Saída:

```text
Protocol?
Skill?
Workflow?
Runbook?
Playbook?
SOP only?
No reusable object?
```

---

# 10.2 AUTHORITY CENSUS

Antes de criar:

- existe Skill?
- existe protocol-like doc?
- existe script?
- existe workflow?
- existe SPEC?
- existe runner?
- existe Factory?

Regra:

> **não criar segunda autoridade porque o nome mudou.**

---

# 10.3 OUTCOME CONTRACT

Descrever:

```text
entrada
→ estado esperado
→ artefatos
→ efeitos
→ prova
```

Antes de escrever 300 linhas de instrução.

---

# 10.4 EVALS FIRST

Inspirado nas melhores práticas atuais de Agent Skills.

Antes de escrever Protocol grande:

1. executar tarefa representativa sem Protocol;
2. registrar onde falha;
3. criar 3+ casos;
4. estabelecer baseline;
5. escrever a menor instrução que fecha gaps;
6. testar;
7. iterar.

---

# 11. STATIC PROTOCOL LINTER

Criar validador determinístico.

Sugestão:

```text
protocol-lint
```

Ele verifica:

- Agent Skills frontmatter;
- `name`/description;
- protocolo schema;
- version;
- content hash;
- required fields;
- file references;
- paths existentes;
- links internos;
- SKILL.md size;
- reference depth;
- scripts declarados;
- executable flags where relevant;
- no obvious secrets;
- no hardcoded credentials;
- no unsafe absolute paths;
- tests exist;
- Definition of Done exists;
- negative cases exist;
- mutations exist for high-risk profiles;
- release immutability rules.

Não usar LLM para o que YAML/JSON/schema resolve.

---

# 12. PROTOCOL DRIFT CHECKER

Problema:

Protocol publicado pode estar correto no dia 1 e quebrar no dia 90.

Detectar:

- arquivo renomeado;
- command removed;
- test path changed;
- schema changed;
- endpoint changed;
- Tool key missing;
- Skill dependency superseded;
- Capability missing;
- external standard updated.

Saída:

```text
healthy
warning
broken
needs_revalidation
```

Drift não autoedita Protocol publicado.

Gera Candidate.

---

# 13. EXECUTION PACKET BUILDER

Não construir outro agent runtime.

Criar uma função/CLI/service estreito que monta o pacote.

Exemplo:

```text
protocol pack engineering.create_spec --task SPEC-093
```

Saída conceitual:

```text
PACKET
├─ Protocol key + release
├─ Outcome
├─ current task
├─ exact authorities
├─ exact relevant files
├─ invariants
├─ warm-up questions
├─ gates
├─ test commands
├─ report schema
└─ prohibited reads/actions
```

O executor/harness continua:

- Claude Code;
- Codex;
- Copilot;
- outro.

Packet Builder não toma decisões cognitivas.

---

# 14. PROTOCOL RESOLUTION

Para um catálogo grande:

```text
metadata catalog
→ shortlist
→ selected Protocol
→ load SKILL.md
```

Mesma filosofia do Skill Registry.

Não carregar 100 Protocols inteiros.

---

# 15. CLEAN-ROOM TEST

Gate central.

Um Protocol só é considerado portátil quando:

1. iniciar sessão nova;
2. sem memória da conversa autora;
3. fornecer somente:
   - task;
   - Protocol;
   - Execution Packet;
4. executor explica:
   - outcome;
   - uncertainties;
   - required evidence;
5. executa;
6. resultado passa nos gates.

> **Se precisa da conversa antiga para funcionar, o Protocol falhou.**

---

# 16. CROSS-HARNESS PORTABILITY TEST

Para Protocols críticos:

executar em pelo menos dois ambientes/model families quando disponível.

Exemplo:

```text
Claude Code
vs
Codex
```

ou:

```text
Claude Code
vs
GitHub Copilot
```

Não exigir output textual idêntico.

Exigir:

- same invariants;
- same gates;
- equivalent artifacts;
- no forbidden behavior;
- comparable outcome.

---

# 17. ACTIVATION EVAL

Protocol precisa ser descoberto quando deve.

Dataset:

```text
positive triggers
```

Métrica:

```text
activation_recall
```

---

# 18. NON-ACTIVATION EVAL

Tão importante quanto ativar.

Exemplo:

`create-spec` não deve disparar para:

> “resuma a SPEC-092”.

Métrica:

```text
false_activation_rate
```

---

# 19. EXECUTION EVAL

Avalia o resultado real.

Não apenas:

```text
“o modelo disse que seguiu”
```

Medir:

- arquivos;
- testes;
- banco;
- artifacts;
- side effects;
- final output.

---

# 20. TRACE / STEP EVAL

Agents falham no caminho.

Registrar:

- wrong file read;
- wrong tool;
- skipped gate;
- unnecessary retry;
- permission denial;
- failed step;
- repair.

Final output correto com trajetória perigosa não é 100/100.

---

# 21. MUTATION EVAL

Mutar deliberadamente:

- arquivo;
- config;
- assertion;
- expected schema;
- permission;
- critical instruction.

O Protocol deve detectar.

Se mutação não fica vermelha:

```text
gate is ornamental
```

---

# 22. NEGATIVE CONTROL

Todo Protocol high-impact tem controle de algo que **não deve acontecer**.

Exemplo `create-skill`:

```text
Skill não pode criar nova Capability automaticamente.
```

---

# 23. PORTABILITY EXPORTERS

Canonical Package pode gerar:

```text
generic Agent Skill zip
.claude/skills projection
.agents/skills projection
.github/skills projection
```

onde aplicável.

Não manter quatro cópias manuais.

Cada export:

- source release;
- source content hash;
- generated hash;
- compatibility notes.

---

# 24. AGENT SKILLS OPEN STANDARD

Preservar:

- `SKILL.md`;
- YAML frontmatter;
- concise description;
- progressive disclosure;
- `scripts/`;
- `references/`;
- `assets/`;
- compatibility metadata.

AutoBrokers-specific contract vive em:

```text
protocol.yaml
```

e metadata compatível.

Um harness que só entende Agent Skills continua conseguindo usar o core.

---

# 25. IMPORTED PROTOCOL / SKILL SUPPLY-CHAIN SECURITY

Agent Skills podem executar scripts e orientar tool use.

Imported Package é código/instrução não confiável.

Lifecycle:

```text
download
→ quarantine
→ scan
→ review
→ test
→ approved
→ available
```

Verificar:

- network calls;
- shell commands;
- file access;
- secrets;
- prompt injection;
- hidden instructions;
- binary assets;
- dependency install;
- destructive commands.

Nunca instalar “awesome-skill” direto em produção porque tem estrelas.

---

# 26. PROTOCOL RELEASES

Lifecycle:

```text
draft
→ candidate
→ validated
→ published
→ deprecated
→ superseded
→ revoked
```

Published release é imutável.

Mudança comportamental:

```text
new release
```

---

# 27. VERSIONING

Sugestão SemVer pragmática:

## MAJOR

- input/output incompatible;
- ontology changes;
- required authority changes;
- execution path fundamentally changes.

## MINOR

- new supported path;
- new optional reference;
- better failure handling;
- new compatible capability.

## PATCH

- typo;
- clarification with no behavior change;
- non-normative reference correction.

Content hash sempre decide se conteúdo mudou.

---

# 28. PROTOCOL EXECUTION RECORD

Para execução Build Plane, registrar machine-readable record.

Campos:

```json
{
  "protocol_key": "...",
  "protocol_version": "...",
  "protocol_hash": "...",

  "task_id": "...",
  "harness": "claude-code",
  "model": "...",

  "started_at": "...",
  "completed_at": "...",

  "baseline_commit": "...",
  "final_commit": "...",

  "input_files": [],
  "bytes_loaded": 0,
  "references_loaded": [],

  "steps": [],
  "gates": [],
  "mutations": [],

  "failures": [],
  "repairs": [],

  "artifacts": [],

  "outcome": "passed"
}
```

---

# 28.1 TELEMETRIA DO PROCESSO

Especialmente para engenharia:

- task received;
- branch created;
- time to first product change;
- bytes read before product work;
- code vs docs delta;
- build duration;
- verification duration;
- judge duration;
- number of repair cycles;
- defects caused by repairs;
- tests;
- cost/tokens when available.

Isso permite descobrir Protocol lento ou ruim por dado real.

---

# 29. WORK RUN INTEGRATION

Quando Protocol roda dentro do AutoBrokers runtime:

```text
Protocol/Skill
→ Work Run
```

Não criar `protocol_runs` concorrente para runtime product work.

`Protocol Execution Record` para Build Plane é audit artifact, não novo execution engine.

---

# 30. AAA INTEGRATION

A 091 **não substitui nem duplica** `PROTOCOLO-AUTOBROKERS-AAA.md`.

Cada Protocol declara:

```text
minimum_quality_profile
```

Mas a tarefa atual é pontuada pelo AAA.

Regra:

> **Protocol pode exigir qualidade MAIS forte. Nunca reduzir a conta de risco/superfície.**

---

# 30.1 O PAINEL CONTINUA JULGANDO CÓDIGO/PRODUTO

A 091 não volta ao padrão proibido:

```text
painel de 5 juízes revisando o Markdown do Protocol
```

Validation de Protocol acontece por:

```text
warm-up
+
clean-room execution
+
real gates
+
evals
+
mutations
```

Quando o Protocol produz código:

AAA julga o código.

---

# 31. WARM-UP GENERATOR

Para Protocols de execução complexa, gerar questionário.

Objetivos:

- provar que executor entendeu;
- revelar ambiguidades;
- refutar premissas falsas;
- medir estado atual.

Para `execute-spec`:

- 12–15 perguntas;
- algumas com resposta óbvia mas errada;
- pelo menos duas afirmações explicitamente falsas para o executor refutar;
- “o que você NÃO entendeu?”;
- “o que a SPEC afirma que o código contradiz?”;
- “qual menor pacote de leitura necessário?”.

---

# 32. HOOKS / ENFORCEMENT

A 091 pode usar adapters de hooks quando harness suporta, mas não depender deles.

Tipos genéricos:

```text
session_start
pre_action
post_action
pre_side_effect
on_error
before_finish
```

Aplicações:

- secret scan;
- block dangerous command;
- schema validation;
- audit;
- test gate;
- evidence capture.

Hooks síncronos devem ser rápidos.

Heavy work fora do hook.

---

# 33. SECURITY GATE VS PROMPT RULE

Regra de segurança crítica não deve depender apenas de:

> “não faça X”.

Preferir:

```text
validator
hook
Capability Registry
database constraint
test
```

Prompt é camada cognitiva, não última linha de defesa.

---

# 34. PROTOCOL CANDIDATE FACTORY — INTEGRAÇÃO COM 090

A SPEC-090 pode produzir:

```text
PROCESS_CANDIDATE
AUTOMATION_OPPORTUNITY
CAPABILITY_GAP
```

A 091 recebe Process Candidate.

Decide:

```text
Protocol?
Skill?
Workflow?
Auxiliary?
Discard?
Need more evidence?
```

---

# 35. LEARNING LOOP

```text
Protocol Execution
↓
Execution Record
↓
Failures / Workarounds / Success
↓
Learning Signals
↓
SPEC-090 Candidate
↓
SPEC-106 Dreams
↓
Protocol Improvement Candidate
↓
SPEC-091 Factory
↓
new immutable release
```

Nenhum Protocol publicado se autoedita.

---

# 36. PROCESS DRIFT

Uma operação real pode divergir do Protocol.

Registrar:

```text
protocol_step_skipped
new_step_required
old_step_broken
tool_changed
dependency_changed
human_workaround
```

Frequência + outcome geram Candidate.

---

# 37. “WHAT THE AGENT ACTUALLY DID” > “WHAT THE PROTOCOL SAID”

Execution Record deve capturar comportamento.

O sistema aprende da diferença:

```text
DESIGNED PROCESS
vs
ACTUAL PROCESS
```

---

# 38. PROTOCOL DISCOVERY METRICS

- activation precision;
- activation recall;
- false activation;
- selection latency;
- number of Protocols catalogued;
- metadata token cost.

---

# 39. EXECUTION QUALITY METRICS

- success rate;
- first-pass success;
- repair rate;
- control failure rate;
- mutation detection;
- clean-room success;
- cross-harness success;
- rollback success;
- mean steps;
- mean tool calls;
- context bytes loaded;
- time to first useful action.

---

# 40. CONTEXT EFFICIENCY METRICS

A 091 deve medir:

```text
bytes offered
bytes actually loaded
tokens in SKILL.md
references loaded
unnecessary references
```

Objetivo:

> **o Protocol sabe muito, mas carrega pouco.**

---

# 41. PROTOCOL QUALITY SCORE

Score diagnóstico:

```text
discoverability
clarity
executability
control coverage
failure coverage
portability
context efficiency
security
observed success
```

Não substituir hard gates.

---

# 42. PRIMEIROS PROTOCOLS OBRIGATÓRIOS

A 091 não precisa transformar 40 processos numa única execução.

Precisa provar a Factory com um núcleo de alto valor.

## P0-1 — `engineering.create-spec`

Como criar Candidate SPEC excelente.

## P0-2 — `engineering.execute-spec`

Como executar uma SPEC sob AAA v9.

## P0-3 — `engineering.create-skill`

Como criar/evoluir Skill sobre SPEC-056.

## P0-4 — `engineering.create-auxiliary`

Como criar Auxiliar sobre SPEC-058.

## P0-5 — `engineering.create-connector`

Como adicionar conector sem furar Vault/Capability/Tool Gateway.

## P0-6 — `engineering.create-route`

Como criar/alterar rota/corredor usando Atlas, evidence e gates existentes.

Esses seis são suficientes para provar arquitetura e valor.

---

# 43. P1 — BACKLOG DE PROTOCOLS

Após Factory comprovada:

- `engineering.improve-skill`;
- `engineering.improve-auxiliary`;
- `engineering.improve-route`;
- `engineering.integrate-management-system`;
- `engineering.integrate-insurer`;
- `engineering.create-artifact`;
- `engineering.create-report`;
- `engineering.create-capability`;
- `engineering.create-agent-role`;
- `engineering.migrate-schema`;
- `engineering.deploy`;
- `engineering.rollback`;
- `ops.incident-response`;
- `ops.rotate-credential`;
- `ops.onboard-brokerage`;
- `ops.pair-channel`;
- `knowledge.ingest-source`;
- `knowledge.curate`;
- `knowledge.publish`;
- `knowledge.reindex`;
- `security.respond-to-leak`;
- `security.permission-review`.

Não criar tudo agora.

---

# 44. `engineering.create-spec`

Este é o Protocol canário da Factory.

Ele deve ensinar:

```text
INTAKE
↓
CURRENT-STATE CENSUS
↓
EXTERNAL RESEARCH
↓
OBJECTIVE / NON-GOALS
↓
AUTHORITY MAP
↓
INVARIANTS
↓
FAILURE MODES
↓
SECURITY
↓
BLOCKS
↓
GATES
↓
MUTATIONS
↓
RED TEAM
↓
ROLLBACK
↓
DoD
```

Mas não deve encher uma SPEC só porque o template tem seções.

Cada seção precisa justificar presença.

---

# 45. `engineering.create-spec` — TESTE CENTRAL

Sessão limpa recebe:

```text
uma ideia nova
+
create-spec Protocol
+
pequeno contexto do repositório
```

Sem histórico da conversa Founder/autor.

Deve produzir Candidate SPEC comparável à qualidade das SPECs aprovadas.

---

# 46. `engineering.execute-spec`

Deve transformar SPEC + estado real em execução.

Preserva AAA v9:

- dieta;
- risco;
- superfície;
- warm-up;
- mechanical verify;
- panel after code;
- fresh judge;
- telemetry.

Não duplicar AAA inteiro dentro de SKILL.md.

Carregar somente se aplicável.

---

# 47. `engineering.create-skill`

Deve usar Skill Registry existente.

Hard gates:

- não criar second registry;
- no power grant;
- release immutable;
- progressive disclosure;
- tool/capability requirements;
- eval-first;
- activation/non-activation tests;
- Tool Gateway compatibility.

---

# 48. `engineering.create-auxiliary`

Deve usar Auxiliary Factory.

Decidir antes:

```text
one-shot Work Run?
Routine?
Auxiliary?
Workflow?
Agent/Subagent?
```

Não transformar qualquer automação em Auxiliar.

---

# 49. `engineering.create-connector`

Deve tratar:

- provider;
- auth;
- Vault;
- tenant/user ownership;
- OAuth/scopes;
- Capability;
- Tool Definitions;
- read/write distinction;
- approval;
- health;
- observability;
- failure;
- revocation;
- sandbox;
- test tenant;
- no secret in Skill/Protocol.

---

# 50. `engineering.create-route`

Deve incorporar o melhor do método atual de corredor:

- evidence real;
- observed events;
- no invention;
- insurer identity;
- PII hygiene;
- Atlas;
- route candidate;
- quality ruler;
- replay;
- controlled promotion;
- fallback/handoff;
- regressions.

Não reinventar o Atlas.

---

# 51. PROTOCOL FOR INTEGRATING A MANAGEMENT SYSTEM

P1, mas arquitetura já definida.

Exemplo:

```text
InfoCap
→ adapter
→ Quiver
→ adapter
→ Segfy
```

O Protocol deve separar:

```text
COMMON CONTRACT
from
PROVIDER ADAPTER
```

e provar:

- tenant identity;
- secrets;
- field mapping;
- pagination;
- rate limits;
- data freshness;
- source of truth;
- retries;
- read/write effects;
- test corpus;
- canary.

---

# 52. PROTOCOL LIBRARY INDEX

Gerar índice derivado.

Nunca editar manualmente se puder gerar.

Campos:

- key;
- name;
- description;
- version;
- type;
- status;
- tags;
- compatibility;
- hash;
- updated.

Esse índice ajuda discovery.

Não é uma nova authority DB.

---

# 53. REPOSITORY TRUST BOUNDARY

Alteração em Protocol publicado é alteração de comportamento de agente.

Portanto:

- code review;
- hash;
- provenance;
- protected branch;
- no auto-import from PR;
- validate packages in CI;
- review scripts.

Protocol supply chain é parte da segurança.

---

# 54. CI / CHECKS

Possíveis checks:

```text
protocol-lint
agent-skills validate
secret scan
reference existence
content hash
tests schema
exports in sync
```

Não obrigar LLM call em todo PR.

Dynamic eval pode rodar em release candidates / selected CI.

---

# 55. EXPORT IMMUTABILITY

Export generated from release X deve informar:

```text
source_protocol
source_version
source_hash
generated_at
adapter
```

Se pacote gerado divergir:

```text
FAIL
```

---

# 56. DEPRECATION

Deprecating Protocol:

- new executions stop selecting it;
- historical Execution Records remain;
- replacement pointed;
- exports updated;
- dependent Protocols warned.

---

# 57. DEPENDENCY GRAPH

Protocol dependencies podem ser representadas relationally/index.

Exemplo:

```text
execute-spec
→ autobrokers-aaa
→ migration-authority (conditional)
```

Não precisa Graph DB.

---

# 58. CONDITIONAL REFERENCES

Uma das maiores regras de eficiência.

Exemplo `execute-spec`:

```text
IF migration touched
→ load MIGRATIONS authority

IF frontend route touched
→ load route mounting verification

IF external message touched
→ load communication safety rules
```

Não carregar tudo em toda execução.

---

# 59. TEMPLATE USE

Templates melhoram consistência.

Assets podem incluir:

- SPEC skeleton;
- report skeleton;
- manifest;
- test case;
- migration plan;
- connector adapter.

Template não substitui raciocínio.

---

# 60. EXAMPLES

Use exemplos quando formato/qualidade depender deles.

Mas:

- poucos;
- reais/anônimos;
- versionados;
- não virar cânon gigantesco.

---

# 61. GOTCHAS

Cada Protocol pode ter:

```text
common-gotchas.md
```

Só adicionar gotcha baseado em falha real.

Não inventar 200 edge cases hipotéticos.

---

# 62. PROTOCOL FACTORY ADMIN/UX

P0 não precisa criar SaaS visual grande.

Entrega mínima:

- repository library;
- generated index;
- validator;
- packet builder;
- report records;
- optional Admin read model if barato/reusing current Control Plane.

Não criar “Protocol Studio” decorativo antes do runtime.

---

# 63. FUTURA VISÃO DE CONTROL PLANE

Depois:

- protocols;
- versions;
- executions;
- success;
- drift;
- candidates;
- dependencies;
- exports;
- owner;
- health.

Pode entrar na SPEC-108/Control Plane evolution.

---

# 64. BLOCK 0 — READ-ONLY CENSUS

Antes de implementar:

1. registrar HEAD;
2. inventariar Skill schema real;
3. inventariar current Skill releases;
4. verificar current Tool Gateway mode;
5. verificar current graph cutover;
6. inventariar `.claude/skills`, `.agents/skills`, `.github/skills`;
7. inventariar docs chamados “protocol”, “playbook”, “runbook”, “checklist”;
8. inventariar scripts de protocolo;
9. inventariar current `PROTOCOLO-AUTOBROKERS-AAA.md`;
10. medir tamanho/bootstrap obrigatório;
11. inventariar SPEC authoring/execution guides;
12. inventariar route/corridor methodology;
13. inventariar Connector patterns;
14. inventariar Auxiliary Factory;
15. medir Work Run integration;
16. medir Artifact/report conventions;
17. identificar authority duplication;
18. identificar process knowledge só em prompts/conversations;
19. identificar current test/eval helpers;
20. verificar open Agent Skills tooling disponível no ambiente.

---

# 65. WARM-UP — PERGUNTAS QUE O EXECUTOR PRECISA REFUTAR

## P1
“Não existe Skill Registry; a 091 precisa criar um.”

**FALSA.**

## P2
“Protocol pode liberar tools porque `allowed-tools` está no SKILL.md.”

**FALSA.**

## P3
“Todo Process deve virar Skill.”

**FALSA.**

## P4
“Protocol e Skill são sinônimos.”

**FALSA.**

## P5
“Um Protocol excelente pode ser validado só revisando Markdown.”

**FALSA.**

## P6
“Para garantir contexto, é melhor mandar o executor ler todo o Canon.”

**FALSA.**

## P7
“Aaa judges devem rodar antes do código para melhorar o Protocol.”

**FALSA para execução de SPEC segundo v9.**

## P8
“Published Protocol pode ser editado in-place se for só correção.”

**REFUTAR conforme tipo de mudança.**

## P9
“Protocol Execution Record deve substituir Work Run.”

**FALSA.**

## P10
“Se Claude Code executa bem, Protocol já é portátil.”

**FALSA.**

## P11
“Imported Agent Skill é só texto, então é baixo risco.”

**FALSA.**

## P12
“Se um arquivo citado pelo Protocol sumiu, o Agent se adapta.”

**Não é estratégia de produção.**

## P13
“O que você ainda NÃO entende sobre o estado atual?”

Resposta “nada” reprova o aquecimento.

---

# 66. BLOCO A — ONTOLOGY + PACKAGE + VALIDATOR

Entregar:

- ontology;
- canonical package;
- protocol schema;
- Agent Skills-compatible SKILL.md;
- content hash;
- lint;
- reference validator;
- secret scan integration;
- generated index.

### Gate A

Package mínimo válido passa.

Mutações estruturais falham.

---

# 67. BLOCO B — FACTORY + PACKET + EVALS + EXPORTS

Entregar:

- Candidate intake;
- authority census;
- Packet Builder;
- activation eval schema;
- execution eval schema;
- mutation schema;
- clean-room runner harness adapter or documented executor contract;
- exporters;
- Protocol Execution Record.

### Gate B

Mesmo Protocol exportado em dois adapters mantém source hash/behavioral gates.

---

# 68. BLOCO C — PRIMEIROS SEIS PROTOCOLS

Construir os P0.

Não copiar documentos gigantes.

Cada um usa progressive disclosure.

### Gate C

Todos passam static lint + clean-room tests.

---

# 69. BLOCO D — DOGFOOD E CUTOVER DE PROCESSO

Usar a Factory para criar/validar os próprios P0.

Canário principal:

```text
engineering.create-spec
```

Executar em sessão limpa.

Canário secundário:

```text
engineering.create-skill
```

produzindo uma Skill candidate controlada.

### Gate D

Nenhuma execução depende da conversa original.

---

# 70. CLEAN-ROOM DOGFOOD — CREATE SPEC

Fixture:

uma ideia de SPEC futura não implementada.

Dois executores frescos, quando possível:

```text
Claude Code
Codex
```

Mesmos inputs essenciais.

Comparar:

- authority map;
- non-goals;
- gates;
- invariants;
- security;
- mutations;
- DoD;
- context read;
- invented facts.

Não comparar estilo.

---

# 71. CLEAN-ROOM DOGFOOD — CREATE SKILL

Criar Skill de baixo risco em sandbox/candidate.

Verificar:

- existing Registry reused;
- no Capability invented;
- manifest valid;
- progressive disclosure;
- activation tests;
- no-activation tests;
- release not auto-published.

---

# 72. RED TEAM

Missão:

> **Fazer um Protocol aparentemente excelente depender de contexto escondido, conceder poder indevido, ficar obsoleto silenciosamente ou passar em review sem conseguir executar a tarefa real.**

Ataques:

1. stale file path;
2. stale command;
3. missing dependency;
4. vague trigger;
5. overbroad trigger;
6. conflicting Protocol;
7. hidden context required;
8. giant bootstrap;
9. malformed Agent Skills YAML;
10. malicious script;
11. secret in asset;
12. network exfiltration;
13. allowed-tools privilege escalation;
14. runtime Skill bypass;
15. Protocol edited after publish;
16. export diverges from source;
17. negative case missing;
18. fake Control that never fails;
19. mutation undetected;
20. one harness succeeds, another misreads;
21. same executor writes and self-certifies;
22. output looks good, effect wrong;
23. Protocol points to superseded Skill;
24. README says one thing, manifest another.

---

# 73. MUTATIONS OBRIGATÓRIAS

## M1
Create `protocol_registry_v2`.

**FAIL.**

## M2
Protocol grants Capability.

**FAIL.**

## M3
Published release edited in-place.

**FAIL.**

## M4
Remove control from critical step.

**FAIL.**

## M5
Delete referenced file.

**Drift/lint fails.**

## M6
Change canonical but not generated export.

**FAIL.**

## M7
Make trigger “helps with engineering”.

**Activation precision fails.**

## M8
Remove negative activation cases.

**Release gate fails.**

## M9
Clean-room executor receives hidden conversation context.

**Test invalid.**

## M10
Mutation of required assertion remains green.

**Release gate fails.**

## M11
Imported package contains hidden network script.

**Quarantine/security fails.**

## M12
`allowed-tools` claims dangerous tool while Capability denies.

**Runtime still denies.**

## M13
Protocol references whole `PENDENCIAS.md`.

**Context lint/warning or fail by profile.**

## M14
Protocol Execution Record becomes runtime authority instead of Work Run.

**Architecture test fails.**

## M15
AAA panel is run on Markdown before any product execution.

**Execution Protocol guard fails for SPEC workflow.**

---

# 74. ACCEPTANCE — PORTABILITY

A critical Protocol is accepted when a fresh capable model can:

1. discover it;
2. load it;
3. state the Outcome;
4. identify when not to use;
5. locate relevant references;
6. execute;
7. run controls;
8. stop on blocker;
9. report evidence;
10. produce equivalent result across supported harnesses.

---

# 75. ACCEPTANCE — CONTEXT

Targets:

- metadata concise;
- SKILL.md within open-standard guidance;
- no unnecessary canon;
- conditional refs;
- actual bytes measured.

A Protocol that saves execution correctness but costs 900 KB every session is not done.

---

# 76. ACCEPTANCE — SECURITY

- no secrets;
- no power grant;
- imported package trusted/scanned;
- no raw unbounded shell by default;
- effects still governed by existing authorities;
- human approvals preserved;
- package provenance;
- immutable release.

---

# 77. ACCEPTANCE — LEARNING

Execution Record can generate:

```text
failure
workaround
drift
success
improvement candidate
```

without autoediting production Protocol.

---

# 78. DEFINITION OF DONE

A SPEC-091 fecha quando:

- [ ] current Skill Registry measured;
- [ ] current Tool Gateway/cutover measured;
- [ ] Protocol ≠ second Registry frozen;
- [ ] Build Plane vs Product Plane documented;
- [ ] Protocol ontology frozen;
- [ ] Process/Skill/Workflow/Runbook/Playbook/SOP distinctions frozen;
- [ ] canonical Protocol Package exists;
- [ ] package is Agent Skills compatible;
- [ ] AutoBrokers extension manifest exists;
- [ ] progressive disclosure enforced;
- [ ] SKILL.md context budget enforced;
- [ ] no giant canon bootstrap;
- [ ] content hash exists;
- [ ] immutable releases;
- [ ] Protocol lifecycle exists;
- [ ] static linter exists;
- [ ] reference/path validator exists;
- [ ] secret/security scan path exists;
- [ ] drift checker exists;
- [ ] generated index exists;
- [ ] Packet Builder exists;
- [ ] Packet contains minimum necessary context;
- [ ] activation eval exists;
- [ ] non-activation eval exists;
- [ ] execution eval exists;
- [ ] step/trace eval exists;
- [ ] mutation eval exists;
- [ ] negative controls exist;
- [ ] clean-room test exists;
- [ ] cross-harness test contract exists;
- [ ] exporter architecture exists;
- [ ] no manual divergent copies;
- [ ] source/export hashes traceable;
- [ ] Protocol Execution Record exists;
- [ ] runtime execution still uses Work Runs;
- [ ] runtime procedure still uses Skill Registry;
- [ ] Capability Registry remains authority;
- [ ] Tool Gateway remains execution gate;
- [ ] AAA remains quality authority;
- [ ] Protocol cannot lower AAA risk;
- [ ] panel judges product/code, not Protocol prose;
- [ ] warm-up generator exists for complex execution;
- [ ] imported Protocol quarantine exists;
- [ ] supply-chain threat model exists;
- [ ] P0 create-spec published;
- [ ] P0 execute-spec published;
- [ ] P0 create-skill published;
- [ ] P0 create-auxiliary published;
- [ ] P0 create-connector published;
- [ ] P0 create-route published;
- [ ] create-spec clean-room passes;
- [ ] create-skill clean-room passes;
- [ ] at least one cross-model/harness portability run performed when environments available;
- [ ] execution telemetry measured;
- [ ] M1–M15 red;
- [ ] no hidden context dependency;
- [ ] report final published.

---

# 79. NOTAS DE IMPACTO

| Área | Nota |
|---|---:|
| Reuso do know-how | **100/100** |
| Velocidade de desenvolvimento | **100/100** |
| Consistência entre LLMs | **99/100** |
| Redução de contexto desperdiçado | **100/100** |
| Segurança de processos | **99/100** |
| Escalabilidade da equipe enxuta | **100/100** |
| Preparação para MetaHarness | **100/100** |
| Preparação para Dreams | **98/100** |
| Portabilidade Claude/Codex/Copilot | **99/100** |
| Evitar conhecimento preso em chat | **100/100** |

---

# 80. O MOAT INTERNO QUE A 091 CRIA

Hoje:

```text
boa execução
→ alguém aprende
→ talvez documente
→ próxima conversa recomeça parcialmente
```

Depois:

```text
boa execução
→ Protocol
→ release
→ qualquer executor competente
→ execução registrada
→ aprendizado
→ melhoria candidate
→ release melhor
```

Isso transforma know-how interno em software operacional.

---

# 81. RELAÇÃO COM A EQUIPE DE IA

A visão futura não é ter 50 Agents fixos.

É ter:

```text
MODELOS FORTES
+
PROTOCOLS
+
SKILLS
+
TOOLS
+
MEMORY
+
EVALS
```

O executor pode mudar.

O know-how permanece.

---

# 82. RELAÇÃO COM O FUTURO HEADLESS DO AUTOBROKERS

Esta SPEC também ajuda a estratégia:

```text
AutoBrokers Engine
+
portable capabilities
```

Porque um Protocol/Skill bem empacotado pode ser usado:

- dentro do Dashboard;
- em Claude;
- em ChatGPT/Codex;
- em Copilot;
- em outro harness futuro.

O frontend deixa de ser o lugar onde o know-how mora.

---

# 83. REFERÊNCIAS INTERNAS OBRIGATÓRIAS NO AQUECIMENTO

Ler somente o necessário:

- `PROTOCOLO-AUTOBROKERS-AAA.md` v9;
- SPEC-052;
- SPEC-053;
- SPEC-055;
- SPEC-056;
- SPEC-056 Execution Report;
- SPEC-058;
- SPEC-090 Candidate;
- current Skill Registry;
- current Tool Gateway;
- current gateway cutover;
- current Auxiliary Factory;
- current Work Runs;
- current corridor/Atlas quality protocol;
- current migrations authority;
- current SPEC-092 execution report as recent AAA-v9 measurement.

Não carregar relatórios históricos inteiros sem pergunta concreta.

---

# 84. REFERÊNCIAS EXTERNAS OBRIGATÓRIAS

- Agent Skills open specification;
- Anthropic Agent Skills + authoring best practices;
- GitHub Copilot Agent Skills;
- OpenAI Skills;
- GitHub Hooks;
- Anthropic agent eval guidance;
- current OpenAI/Codex long-running work guidance.

Detalhes no Research Pack.

---

# 85. LEI FINAL

> **O conhecimento operacional mais valioso do AutoBrokers não pode continuar existindo apenas em pessoas, prompts antigos, SPECs gigantes ou conversas que outra LLM não viu.**

Deve poder ser:

```text
DESCOBERTO
CARREGADO
EXECUTADO
PROVADO
VERSIONADO
PORTADO
OBSERVADO
MELHORADO
```

sem criar um segundo cérebro, um segundo Skill Registry ou um segundo runtime.

Essa é a Protocol & Process Factory.
