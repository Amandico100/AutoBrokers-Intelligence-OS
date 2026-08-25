# SPEC-091 — RESEARCH PACK
## Protocol & Process Factory — Agent Skills, portability, progressive disclosure, eval-driven authoring, hooks e execução governada

**Data:** 25/08/2026  
**Baseline AutoBrokers observado:** `19f41eedc5808cf1099ede19d2a88be502854485`  
**SPEC associada:** `SPEC-091-protocol-process-factory.md`  
**Uso:** pesquisa para aquecimento AAA; não é bootstrap obrigatório de todo executor.

---

# 1. CONCLUSÃO EXECUTIVA

A pesquisa externa e o estado atual do AutoBrokers convergem em uma decisão:

> **Protocol não deve nascer como um Registry/runtime novo. Deve ser um pacote portátil de procedimento, usando o padrão Agent Skills onde isso ajuda, e compilar para a Skill Registry já existente quando for usado pelo runtime do AutoBrokers.**

Arquitetura:

```text
CANONICAL PROTOCOL PACKAGE
        ↓
Agent Skills-compatible
        ↓
validate / eval / clean-room
        ↓
immutable release
        ↓
├─ external harness export
└─ AutoBrokers Skill Release
```

Essa solução preserva a SPEC-056 e ganha portabilidade.

---

# 2. ESTADO REAL DO AUTOBROKERS — SPEC-056

A SPEC-056 já definiu:

```text
Skill = procedimento versionado para produzir um resultado
Capability = poder
Tool = implementação
Connector = acesso autenticado
Work Run = execução
```

Ela proibiu:

- segundo Skill Registry;
- segundo Capability Registry;
- prompt solto como Skill;
- tool autorizada por prompt;
- release mutável.

Portanto um `Protocol Registry` concorrente seria regressão arquitetural.

---

# 3. SKILL REGISTRY CURRENT

`backend/app/services/skills/registry.py` já implementa:

- compact index;
- shortlist;
- load one full release;
- triggers;
- SkillManifest;
- requirements;
- content hash;
- publication;
- immutable semantics.

O comentário do próprio serviço já usa progressive disclosure:

```text
compact index
→ resolve
→ load one manifest
→ load only toolset required
```

Isso é fortemente alinhado com o Agent Skills standard.

---

# 4. SPEC-056 EXECUTION REPORT

Em 25/07/2026 havia:

- 15 Tool Definitions;
- 15 published releases;
- 8 Skills;
- 7 Capability Packs;
- 14 role bindings.

O report também disse que, naquele momento, o full graph cutover ainda estava pendente.

O estado atual precisa ser medido porque o repository mudou depois.

---

# 5. CURRENT GATEWAY CUTOVER

`backend/app/agents/gateway_cutover.py` existe e foi alterado em agosto de 2026.

Ele possui:

```text
off
shadow
on
```

e uma propriedade segura importante:

> no modo on, Gateway só pode remover tools, nunca adicionar.

A 091 não deve presumir o mode atual.

Warm-up mede.

---

# 6. PROTOCOLO AAA v9 — EVIDÊNCIA INTERNA CRÍTICA

O AAA v9 mediu que a percepção de “execução muito lenta” não vinha principalmente dos juízes.

O maior custo observado era:

```text
reading toll before first product change
```

Também mediu que painéis rodando sobre documentos antes do código compravam mais documento, não melhor produto.

Regras relevantes para 091:

```text
agent gets a packet, never the whole canon
judge evaluates code/product, not SPEC prose
fresh judge confirms repairs
telemetry measures protocol itself
```

---

# 7. SPEC-092 — DOGFOOD REAL DO AAA v9

A execução recente da SPEC-092 registrou:

```text
6m45 from branch to first product code
87,855 bytes read
421,146 bytes of unnecessary PENDENCIAS avoided
0.000 docs/code ratio during implementation
```

Também mostrou algo importante:

- panel found 17 issues;
- fresh judge found 3 more;
- another fresh judge found 1 more;
- 3 of the 4 post-panel defects were caused by repairs.

Isso sustenta:

> **process quality must be measured across execution and repairs.**

---

# 8. AGENT SKILLS OPEN STANDARD

Current specification:

```text
skill-name/
├── SKILL.md
├── scripts/
├── references/
├── assets/
└── optional extra directories
```

`SKILL.md`:

- YAML frontmatter;
- required `name`;
- required `description`;
- Markdown body.

Optional:

- license;
- compatibility;
- metadata;
- experimental `allowed-tools`.

Reference:
https://agentskills.io/specification

---

# 9. AGENT SKILLS — PROGRESSIVE DISCLOSURE

The standard defines 3 levels:

```text
1 metadata
2 SKILL.md
3 resources/scripts
```

Approximate guidance:

```text
metadata ~100 tokens
SKILL.md <5000 tokens
SKILL.md <500 lines
resources on demand
```

This directly solves the AutoBrokers bootstrap problem measured by AAA v9.

---

# 10. AGENT SKILLS — REFERENCE DEPTH

The spec recommends focused reference files and avoiding deep chains.

This supports:

```text
SKILL.md
→ one-level relevant reference
```

rather than:

```text
SKILL.md
→ README
→ canon
→ report
→ appendix
→ historical plan
```

---

# 11. ANTHROPIC AGENT SKILLS

Anthropic describes Skills as:

- modular;
- filesystem-based;
- domain-specific;
- dynamically loaded;
- instructions + scripts + resources;
- progressive.

Reference:
https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

---

# 12. ANTHROPIC — CONTEXT AS A PUBLIC GOOD

Their authoring guidance explicitly warns that Skill content competes with:

- system prompt;
- conversation history;
- other Skills;
- current task.

This supports AutoBrokers context budgets per Protocol.

Reference:
https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

---

# 13. ANTHROPIC — DESCRIPTION QUALITY

Skill `description` is the primary discovery mechanism.

It must say:

```text
what it does
+
when to use it
```

A vague Protocol trigger is a reliability bug.

---

# 14. ANTHROPIC — EVAL-FIRST SKILL AUTHORING

Current best practices recommend:

1. identify gaps without Skill;
2. create evaluations;
3. establish baseline;
4. write minimal instructions;
5. run evals;
6. iterate.

This became a central requirement of the 091 Protocol Factory.

---

# 15. ANTHROPIC — TEST WITH MULTIPLE MODELS

Their guidance recommends testing Skills across model capability levels.

The general AutoBrokers adaptation is:

> critical Protocol should not only work because one specific model knows what the author meant.

---

# 16. ANTHROPIC — REPOSITORY SKILL TRUST BOUNDARY

Current Managed Agents docs warn:

A repository-mounted Skill can be changed by anyone who can commit to the trusted repo, and tools such as bash/web give instructions reach.

Therefore:

```text
Protocol package = executable instruction supply chain
```

It needs review and provenance.

Reference:
https://platform.claude.com/docs/en/managed-agents/skills

---

# 17. GITHUB COPILOT AGENT SKILLS

GitHub now supports Agent Skills across:

- cloud agent;
- code review;
- CLI;
- GitHub Copilot app;
- VS Code agent mode;
- JetBrains.

It recognizes project skills in:

```text
.github/skills
.claude/skills
.agents/skills
```

Reference:
https://docs.github.com/en/copilot/concepts/agents/about-agent-skills

---

# 18. GITHUB CLI SKILL MANAGEMENT

Current GitHub CLI can:

- search;
- preview;
- install;
- update;
- publish;
- pin Skill by version/SHA.

Important insight:

> **version pinning is normal ecosystem behavior.**

AutoBrokers Protocol exports should always identify source version/hash.

Reference:
https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills

---

# 19. GITHUB SECURITY WARNING

GitHub explicitly warns that Skills found online are not verified and may contain:

- prompt injection;
- hidden instructions;
- malicious scripts.

This validates the 091 quarantine/scan model for imported Protocols.

---

# 20. OPENAI SKILLS — CROSS-PRODUCT PORTABILITY

Current OpenAI Skills:

- reusable workflows;
- instructions;
- examples;
- code;
- automatic use when helpful;
- supported in ChatGPT;
- Codex;
- API.

OpenAI says its Skills follow the Agent Skills open standard and can be moved between products.

Reference:
https://help.openai.com/en/articles/20001066

---

# 21. OPENAI SKILLS — WORKSPACE GOVERNANCE

OpenAI workspace controls include:

- enable;
- upload;
- share;
- publish;
- install;
- owner/access;
- usage/invocations;
- compliance events.

Insight:

> a mature Protocol/Skill library eventually needs governance and analytics, not just files.

The 091 deliberately keeps P0 UX minimal and prepares a later Control Plane surface.

---

# 22. OPENAI UPLOAD SCANNING

Uploaded Skills are scanned and may be:

```text
available
needs review
blocked
```

This reinforces a supply-chain intake lifecycle.

---

# 23. OPENAI PLUGINS

Current OpenAI Plugins can package:

```text
Skills
+
Apps
+
App templates
```

The app keeps its own permissions/action controls.

This supports a central AutoBrokers principle:

> procedure does not grant external-system permission.

Reference:
https://help.openai.com/en/articles/20001256-plugins-in-chatgpt-and-codex

---

# 24. OPENAI WORKSPACE AGENTS

Current Workspace Agents can include:

- skills;
- apps;
- MCPs;
- schedules;
- API triggers;
- action constraints;
- memory.

Again:

```text
Agent
≠ Skill
≠ App
≠ Permission
```

Reference:
https://help.openai.com/en/articles/20001143-chatgpt-workspace-agents-for-enterprise-and-business

---

# 25. GITHUB HOOKS

GitHub Copilot hooks can run at:

- session start/end;
- user prompt;
- preToolUse;
- postToolUse;
- agentStop;
- subagentStop;
- errors.

Use cases:

- approve/deny;
- security validation;
- secret scanning;
- audit;
- metrics;
- error handling.

Reference:
https://docs.github.com/en/copilot/concepts/agents/hooks

---

# 26. HOOK LESSON FOR AUTOBROKERS

Some Protocol rules should be enforcement, not prose.

Example:

```text
DO NOT COMMIT SECRET
```

is weaker than:

```text
secret scanner before finish
```

But 091 should use generic gate semantics and harness adapters.

Do not tie canonical Protocol to Copilot hooks.

---

# 27. HOOK PERFORMANCE

GitHub warns synchronous hooks block Agent execution and recommends keeping them fast.

AutoBrokers:

```text
fast gate in hook
heavy evaluation outside hook
```

---

# 28. AGENT EVALS — ANTHROPIC

Anthropic's current guidance emphasizes that agents are multi-step and can fail at many points.

Good evals:

- use real tasks;
- evaluate end-to-end;
- inspect trajectories/traces;
- use production failures to build datasets;
- combine multiple grader strategies.

Reference:
https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

---

# 29. 2026 ANTHROPIC EVAL GUIDANCE

A July 2026 session emphasizes:

- single-turn eval misses agent failures;
- first eval set should come from real production failures;
- model changes must be evaluated end-to-end.

This supports Protocol Execution Records and failure-derived eval cases.

Reference:
https://www.anthropic.com/webinars/evals-for-ai-agents-how-product-builders-get-the-most-out-of-every-new-model

---

# 30. OPENAI — LONG-RUNNING WORK

OpenAI's current long-running work guidance also recommends packaging successful repeated workflows as reusable Skills instead of reteaching them.

Reference:
https://cdn.openai.com/pdf/8a9f00cf-d379-4e20-b06f-dd7ba5196a11/OAI_WhitePaper_Codex-maxxing26.pdf

---

# 31. OPENAI AGENTS SDK DIRECTION

OpenAI announced in April 2026 a stronger code/sandbox harness and separation of harness from compute.

For AutoBrokers:

> Protocol should be harness-portable, not assume one monolithic Agent runtime.

Reference:
https://openai.com/index/the-next-evolution-of-the-agents-sdk/

---

# 32. WHY PROTOCOL ≠ SKILL EXACTLY

Although both contain procedural knowledge:

## Protocol

Build/operations source contract.

May include:

- governance;
- evals;
- evidence requirements;
- mutation pack;
- clean-room transfer;
- rollback.

## Skill

Runtime procedure selected to produce a user outcome.

A Protocol may compile to Skill.

This avoids the semantic conflict while reusing the runtime authority.

---

# 33. WHY PROTOCOL PACKAGE SHOULD BE SOURCE-CONTROLLED

Engineering protocols need to be available:

- before product runtime starts;
- inside Claude Code/Codex;
- offline from Supabase where necessary;
- alongside exact repo versions.

Git is excellent for:

- review;
- diff;
- history;
- pinning;
- content hash;
- branch protection.

---

# 34. WHY THE RUNTIME SKILL RELEASE STILL LIVES IN DATABASE

For tenant product work, AutoBrokers needs:

- bindings;
- tenant scope;
- publication;
- runtime resolution;
- Capability Packs;
- Tool Gateway.

That already exists.

Do not move all runtime Skills back to Git.

---

# 35. SOURCE → PROJECTION MODEL

```text
Protocol package
source-controlled
        ↓
compiler/export
        ↓
Skill release / Agent Skill package
```

The projection stores source version/hash.

No manual divergence.

---

# 36. WHY NOT CANONICAL `.claude/skills`

Auto-discovered repo Skills have a broad trust effect.

AutoBrokers may have many engineering Protocols that should only be enabled for a specific task.

Canonical under:

```text
docs/canon/protocols
```

plus controlled export is safer and reduces accidental activation.

Warm-up must test whether another location is operationally better without weakening trust.

---

# 37. WHY CLEAN-ROOM MATTERS

The primary failure mode of procedural docs:

> author understands missing context and doesn't notice it's missing.

Fresh model/session exposes this.

This is equivalent to testing an API with a real external client instead of the same code path that created it.

---

# 38. WHY CROSS-MODEL MATTERS

If one model succeeds due to pretrained familiarity or hidden heuristics, Protocol quality may be overstated.

Critical Protocols should preserve outcome across at least two capable executors when feasible.

---

# 39. WHAT MUST BE EQUIVALENT ACROSS MODELS

Not prose.

Must be equivalent:

- invariants;
- outputs;
- side effects;
- gates;
- evidence;
- DoD.

---

# 40. ACTIVATION VS EXECUTION

Two independent qualities:

```text
Did agent select the right Protocol?
Did selected Protocol work?
```

Need separate evals.

---

# 41. FALSE ACTIVATION IS EXPENSIVE

Overbroad descriptions cause:

- irrelevant instructions;
- context pollution;
- wrong tool behavior.

Therefore negative trigger datasets are mandatory.

---

# 42. MINIMAL SKILL CONTENT

Anthropic current guidance favors concise, stepwise instructions and real examples.

AutoBrokers should avoid converting every historical failure into the core SKILL.md.

Instead:

```text
core invariant
+
conditional reference
```

---

# 43. GOTCHA POLICY

A gotcha is admitted when:

- real execution failed;
- evidence exists;
- durable lesson is generalizable.

Not because an author imagines an edge case.

---

# 44. DETERMINISTIC SCRIPTS

Skills ecosystem strongly supports scripts because code executes without loading every implementation detail into context.

Use scripts for:

- lint;
- hash;
- validation;
- schema check;
- file census;
- evidence extraction.

Do not ask LLM to reproduce stable algorithm every run.

---

# 45. PROTOCOL RUN RECORD AS LEARNING DATA

This is the bridge to SPEC-090 and Dreams.

Record:

- what Protocol expected;
- what executor did;
- where failed;
- what repair worked;
- final outcome.

Then:

```text
designed process vs actual process
```

becomes measurable.

---

# 46. WHY NOT A NEW `protocol_runs` PRODUCT TABLE

Work Run is already universal execution authority.

Build Plane protocol record is:

```text
audit/evidence artifact
```

not another scheduler/queue/history authority.

If runtime execution uses Protocol-derived Skill:

```text
Work Run
```

remains canonical.

---

# 47. WHY CREATE-SPEC IS THE BEST CANARY

It tests:

- research;
- context selection;
- authority discovery;
- architecture;
- security;
- completeness;
- progressive disclosure;
- quality.

And the user's workflow uses SPEC creation constantly.

High learning value.

---

# 48. WHY CREATE-SKILL IS THE SECOND CANARY

It proves the most important anti-duplication rule:

> Protocol Factory can build on Skill Registry without becoming another Skill Registry.

---

# 49. WHY CREATE-ROUTE IS P0

AutoBrokers already has deep corridor/Atlas knowledge and real evidence.

Turning this into a portable Protocol proves that process knowledge can be extracted from:

- code;
- SPECs;
- tests;
- execution reports.

---

# 50. WHY ONLY SIX P0 PROTOCOLS

Building 30 Protocols before proving the Factory would produce documentation debt.

P0 proves:

- structure;
- eval;
- portability;
- learning.

Then scale.

---

# 51. SUPPLY CHAIN MODEL

Imported package risk classes:

```text
internal
trusted-partner
reviewed-external
untrusted
blocked
```

No external package publishes directly.

---

# 52. SCRIPT SECURITY

Inspect:

- subprocess;
- shell=True;
- curl/wget;
- network;
- env reads;
- home directory;
- ssh;
- git credentials;
- destructive filesystem ops;
- package installs.

---

# 53. PROTOCOL CONTENT SECURITY

Prompt injection can live in Markdown too.

Review:

- instructions to ignore system;
- hidden HTML;
- obfuscated Unicode;
- links to untrusted dynamic content;
- commands unrelated to stated outcome.

---

# 54. CONTENT HASH

Hash all normative files:

```text
SKILL.md
protocol.yaml
referenced normative files
scripts
tests
assets if behaviorally relevant
```

Exclude generated timestamps.

---

# 55. VERSION PINNING

External agents may run:

```text
latest
```

for low-risk convenience.

Critical protocol executions should record exact version/hash.

---

# 56. PORTABILITY ADAPTERS

Potential output targets:

```text
generic Agent Skills zip
Claude Code
GitHub Copilot
OpenAI Skills/Codex
```

Adapters should only translate packaging/location.

They must not change normative logic.

---

# 57. `allowed-tools`

Because support is experimental/implementation-specific:

- can be emitted as compatibility hint;
- never used as authority;
- never used to bypass Tool Gateway.

---

# 58. PROTOCOL MANIFEST VS AGENT SKILLS METADATA

Agent Skills frontmatter intentionally stays lightweight.

Complex AutoBrokers fields belong in:

```text
protocol.yaml
```

This preserves portability without cramming proprietary schema into description.

---

# 59. PROTOCOL STATIC LINT

Recommended checks:

```text
Agent Skills schema
Protocol schema
paths
links
hash
size
version
required gates
tests
negative tests
mutations
secret scan
exports
```

---

# 60. PROTOCOL DYNAMIC EVAL

Recommended dimensions:

```text
activation
non-activation
understanding
execution
control
mutation
security
portability
context efficiency
```

---

# 61. QUALITY DOES NOT MEAN DETERMINISM EVERYWHERE

A Protocol for strategic architecture cannot specify every reasoning branch.

It should fix:

- invariants;
- evidence;
- gates;
- output contract.

Leave model discretion where flexibility adds value.

---

# 62. TOO MUCH DETAIL HURTS

Agent Skills best practices explicitly warn over-comprehensive Skills can hurt performance.

For AutoBrokers:

> Protocol should constrain what must not vary and leave non-critical implementation choices to capable models.

---

# 63. PROTOCOL VS PLAYBOOK

Use Protocol when:

- outcome can be verified;
- invariant matters;
- repeatability matters.

Use Playbook when:

- strategies vary;
- heuristics dominate;
- no single execution path.

A Playbook can be a reference loaded by Protocol.

---

# 64. PROTOCOL VS WORKFLOW

Protocol:

```text
contract + how + proof
```

Workflow:

```text
runtime sequence/state
```

A Protocol may invoke a Workflow.

---

# 65. PROTOCOL VS SPEC

SPEC:

```text
desired product change
```

Protocol `create-spec`:

```text
repeatable procedure to produce SPEC
```

Protocol `execute-spec`:

```text
repeatable procedure to turn SPEC into working product
```

---

# 66. PROTOCOL VS AAA

AAA:

```text
quality governance meta-protocol
```

091 should package/reference it more efficiently but not silently rewrite v9.

Any future change to AAA remains its own governed decision.

---

# 67. FUTURE META-HARNESS

SPEC-108 can eventually:

- resolve Protocol;
- choose quality profile;
- select agents;
- run judges;
- collect execution record;
- route repairs.

091 only creates the reusable know-how layer and proof contracts.

---

# 68. RESEARCH SCORECARD

| Reference | Relevance to 091 |
|---|---:|
| Agent Skills open standard | **100/100** |
| Anthropic Skills architecture | **100/100** |
| Anthropic Skill authoring eval-first | **100/100** |
| GitHub Skills portability/versioning | **99/100** |
| OpenAI Skills portability/governance | **99/100** |
| GitHub hooks | **94/100** |
| Anthropic agent evals | **99/100** |
| AutoBrokers AAA v9 | **100/100** |
| AutoBrokers Skill Registry | **100/100** |
| New Protocol Registry | **5/100** |

---

# 69. FINAL RECOMMENDATION

Build:

```text
PROTOCOL FACTORY
```

not:

```text
PROTOCOL RUNTIME
```

The Factory produces portable, tested procedural packages.

Runtime continues to be:

```text
Smith
+
Skill Registry
+
Tool Gateway
+
Work Runs
```

This is the cleanest way to obtain:

- repeatability;
- portability;
- context efficiency;
- learning;
- model independence;
- zero duplicated authority.

---

# 70. SOURCE INDEX

Agent Skills  
https://agentskills.io/  
https://agentskills.io/specification  
https://agentskills.io/skill-creation/best-practices  
https://agentskills.io/skill-creation/optimizing-descriptions

Anthropic  
https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview  
https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices  
https://platform.claude.com/docs/en/managed-agents/skills  
https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills  
https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents  
https://www.anthropic.com/webinars/evals-for-ai-agents-how-product-builders-get-the-most-out-of-every-new-model

GitHub  
https://docs.github.com/en/copilot/concepts/agents/about-agent-skills  
https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills  
https://docs.github.com/en/copilot/concepts/agents/hooks  
https://docs.github.com/en/copilot/reference/hooks-reference

OpenAI  
https://help.openai.com/en/articles/20001066  
https://help.openai.com/en/articles/20001256-plugins-in-chatgpt-and-codex  
https://help.openai.com/en/articles/20001143-chatgpt-workspace-agents-for-enterprise-and-business  
https://openai.com/index/the-next-evolution-of-the-agents-sdk/  
https://cdn.openai.com/pdf/8a9f00cf-d379-4e20-b06f-dd7ba5196a11/OAI_WhitePaper_Codex-maxxing26.pdf

---

# 71. FINAL RULE

> **A procedure is not reusable because it is written down. It is reusable when a fresh executor can discover it, execute it, prove it, and produce the same class of outcome without hidden context.**
