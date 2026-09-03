# SPEC-093 — RESEARCH PACK
## Claims Learning Shadow — human-governed claims intelligence, evidence, autonomy readiness e aprendizado operacional

**Data:** 25/08/2026  
**Baseline AutoBrokers observado:** `19f41eedc5808cf1099ede19d2a88be502854485`  
**SPEC associada:** `SPEC-093-claims-learning-shadow.md`  
**Uso:** material de pesquisa para aquecimento/revisão AAA. Não carregar inteiro no bootstrap de todo executor.

---

# 1. VEREDITO

A melhor estratégia para Claims no AutoBrokers agora é:

```text
HUMAN CLAIM HANDLING
+
SHADOW OBSERVATION
+
STRUCTURED TRAJECTORIES
+
EVIDENCE
+
PROCESS LEARNING
+
AUTONOMY READINESS
```

e NÃO:

```text
“vamos criar um agente autônomo de sinistros”
```

Nota:

```text
Claims Learning Shadow agora ........... 100/100
Full Claims automation agora ........... 58/100
Preparar bounded autonomy futura ....... 100/100
```

---

# 2. ESTADO ATUAL — PROMPT DE ATENDIMENTO

O prompt atual já possui uma boundary sensata.

Para sinistro:

- entende ocorrência;
- data/local;
- vítimas;
- terceiros;
- fotos;
- safety first;
- depois entrega para equipe humana;
- dossiê completo;
- cliente não repete.

Isso deve ser preservado.

---

# 3. ESTADO ATUAL — FICHA DO ATENDIMENTO

A Ficha atual agrega sem nova LLM:

```text
conversation
messages
attachments
dispatch
insurer mirror
attendance_sessions
InfoCap
dossier
timeline
policy
```

Ela é uma base natural para C1 claims assist.

Não criar outra ficha.

---

# 4. ESTADO ATUAL — INFOCAP

O mapa medido em 14/07/2026 indicava:

```text
GET /sinistro
```

como negado 403 para o perfil atual.

Isso significa:

1. não podemos fingir que InfoCap já é claims source completo;
2. o warm-up deve revalidar o perfil vivo;
3. o Claim Shadow precisa aceitar múltiplos sources;
4. source-of-truth pode variar por corretora.

---

# 5. ESTADO ATUAL — CLAIMS DOMAIN

Search no backend mostra referências a `sinistro`, mas não evidência de um Claims Core AutoBrokers com lifecycle completo.

A lacuna não deve ser preenchida com um sistema paralelo improvisado.

Primeiro inteligência derivada.

---

# 6. GUIDEWIRE — PADRÃO PRINCIPAL DE CLAIMS CORE + AI

Guidewire apresenta AI embutida no workflow de P&C.

Claims adjusters recebem:

- estimated severity;
- fraud signals;
- recommended next steps;
- policy context.

O humano revisa e atua nos casos complexos.

Referências:
- https://www.guidewire.com/products/technology/insurance-ai-from-guidewire
- https://www.guidewire.com/products/core-products/insurancesuite/claimcenter-claims-management-software

Lição AutoBrokers:

> intelligence should sit next to the handler and source system, not invent another system of record.

---

# 7. SPROUT.AI — CLAIMS DECISION INTELLIGENCE

Artigo de julho de 2026 define claims decision intelligence como camada que:

- lê claim evidence;
- interpreta policy context;
- identifica decision-critical facts;
- ajuda a produzir outcome consistente e explicável.

Importante:

> não substitui claims core.

Referência:
https://sprout.ai/resource/claims-decision-intelligence-the-missing-layer-between-your-claims-core-and-better-outcomes/

---

# 8. SPROUT — AUTOMATION ≠ CLAIMS AI

Em maio de 2026 a Sprout destacou a diferença:

```text
workflow automation
moves work

claims AI
improves interpretation/decision support
```

Acelerar workflow sem qualidade pode apenas acelerar decisão errada.

Referência:
https://sprout.ai/resource/claims-automation-vs-claims-ai-whats-the-difference-and-why-does-it-matter/

---

# 9. SPROUT — HUMAN CLAIMS HANDLER

Material de abril de 2026 posiciona AI como transformação do trabalho do handler, não simples substituição.

A maior oportunidade imediata fica ao redor da decisão central:

- prep;
- evidence;
- admin;
- consistency.

Referência:
https://sprout.ai/resource/ai-wont-replace-claims-handlers-but-it-will-transform-claims/

---

# 10. SNAPSHEET AI

Current product patterns:

- claims summarization;
- audits/QA;
- communication drafts;
- recommendations;
- key signal identification;
- photo/document tagging;
- multi-step AI actions;
- human tasks inserted by workflow logic.

Referência:
https://www.snapsheetclaims.com/products/snapsheet-ai

Lição:

> C1/C2 value is already material before full autonomy.

---

# 11. SHIFT TECHNOLOGY — ARISE 2026

Publicado em 10/06/2026.

Cinco níveis:

```text
Answers
Recommends
Initiates
Solves
Exceeds
```

As diferenças são definidas pelo grau de human involvement e judgment authority.

Referência:
https://www.shift-technology.com/en-gb/resources/reports-and-insights/arise-a-standard-framework-for-ai-agent-autonomy-in-insurance

---

# 12. ARISE L1 — ANSWERS

Recupera/sintetiza:

- policy;
- claim records;
- regulatory data;
- case history.

Não recomenda.

AutoBrokers C1 é próximo, mas inclui organização de case evidence.

---

# 13. ARISE L2 — RECOMMENDS

Analisa situação e recomenda next actions.

Humano continua autoridade.

Isso é future C2, não 093 V1.

---

# 14. ARISE L3 — INITIATES

Agent prepara workflow e decisões, humano autoriza.

Isso é future C3.

Não ativar em 093.

---

# 15. ARISE L4 — SOLVES

Straight-through sem review por transação dentro de domínio definido.

Shift relata produção em alguns microdomínios, inclusive glass.

Lição:

> full autonomy pode ser possível para domínios estreitos; não é argumento para generalizar Claims.

---

# 16. ARISE L5 — EXCEEDS

Não é meta atual.

A 093 deve impedir que marketing de “autonomy” vire permissão técnica.

---

# 17. GUIDE PARA NOSSA ESCADA

AutoBrokers:

```text
C0 Observe
C1 Assist
C2 Recommend
C3 Prepare
C4 Execute bounded
C5 Advanced autonomy
```

Nossa principal adição:

```text
C0
```

porque o objetivo atual é aprender sem interferência.

---

# 18. MCKINSEY — CLAIMS 2030

McKinsey há anos projeta coexistência entre:

- human intelligence;
- AI;
- straight-through simple claims;
- humans handling complex/unusual claims and exceptions.

Referências:
- https://www.mckinsey.com/industries/financial-services/our-insights/insurance-productivity-2030-reimagining-the-insurer-for-the-future
- https://www.mckinsey.com/industries/financial-services/our-insights/claims-2030-dream-or-reality

Lição:

> classify simple vs complex; do not build one autonomy setting for “claims”.

---

# 19. DELOITTE INSURANCE PREDICTIONS 2026

Deloitte prevê “augmented claims professional”:

```text
automation
→ structured/repeatable work

human
→ coverage interpretation
→ exceptions
→ disputed/ambiguous
→ vulnerable customers
→ complex liability
→ complaints
```

Referência:
https://www.deloitte.com/content/dam/assets-zone1/au/en/docs/industries/insurance/2025/insurance-predictions-2026.pdf

---

# 20. SHIFT CLAIMS

Shift Claims 2025/2026 direção:

- assess/prioritize;
- guide handlers;
- automate tasks;
- claim-specific agentic AI.

Também destaca que cada claim pode seguir trajetória própria, dificultando rules-only automation.

Referência:
https://www.shift-technology.com/resources/news/shift-technology-launches-shift-claims-to-power-claims-transformation-with-agentic-ai

---

# 21. FRAUD / ENTITY RESOLUTION

Shift demonstra valor de comparar históricos e padrões para fraud investigation.

Isso é future capability.

Na 093:

```text
record fraud check
```

não:

```text
accuse person
```

Referência:
https://www.shift-technology.com/resources/case-studies/ai-in-action/ai-insurance-advanced-resolution-techniques

---

# 22. CLAIMS AI PILOT TRAP

Sprout July 2026 destaca por que pilots stall:

- integration;
- compliance;
- adoption;
- fragmented data;
- decision logic vivendo na cabeça de handlers.

Isso descreve exatamente o problema que Claims Shadow resolve:

> capture tacit handler knowledge as evidence before autonomy.

Referência:
https://sprout.ai/resource/why-claims-ai-pilots-stall-before-production-and-how-to-escape-the-pilot-trap/

---

# 23. SUSEP — SEGURO AUTO

SUSEP orienta que, em sinistro auto, segurado deve observar condições contratuais e comunicar seguradora/corretor, além de manter comprovação do aviso.

Também reforça que documentos/procedimentos dependem das condições do contrato.

Referência:
https://www.gov.br/susep/pt-br/assuntos/meu-futuro-seguro/seguros-previdencia-e-capitalizacao/seguros/seguro-de-automoveis

Lição:

> document list is product/contract aware.

---

# 24. LEI Nº 15.040/2024

Novo marco legal de contrato de seguro entrou em vigor em 11/12/2025.

SUSEP ressalta princípios de clareza/transparência e o novo sistema jurídico do contrato de seguro.

Referências:
- https://www.gov.br/susep/pt-br/central-de-conteudos/noticias/2024/dezembro/lei-do-contrato-de-seguro-e-publicada
- https://www.gov.br/susep/pt-br/central-de-conteudos/noticias/2025/dezembro/lei-do-contrato-de-seguro-entra-em-vigor-trazendo-mais-clareza-e-seguranca-juridica-ao-mercado

---

# 25. RESOLUÇÃO CNSP Nº 496/2026

Publicada em 17/08/2026.

Traz regras gerais de contratos de seguros de danos e disciplina regulação/liquidação.

SUSEP informa, entre outros pontos:

- prazo máximo de 30 dias para regulação/manifestação de cobertura, sujeito ao escopo/applicability da norma;
- reconhecida cobertura, regra de liquidação/pagamento;
- exceções específicas;
- planos devem ser adaptados;
- aplicação obrigatória a contratos formados/renovados a partir de 05/01/2027, segundo transição descrita pela SUSEP.

Referência:
https://www.gov.br/susep/pt-br/central-de-conteudos/noticias/2026/agosto/nova-norma-do-cnsp-estabelece-regras-gerais-para-contratos-de-seguros-de-danos

Lição arquitetural:

# **temporal/applicability-aware knowledge é obrigatório.**

---

# 26. NÃO HARDCODE PRAZO

Uma regra:

```text
30 days
```

sem:

```text
effective date
contract applicability
insurance line
source
```

é uma future bug.

Isso entra como mutation test.

---

# 27. EVIDENCE HIERARCHY

Claims precisa separar:

```text
authoritative system
transaction/protocol
official document
insurer communication
handler-confirmed
customer-reported
model inference
```

Nunca misturar.

---

# 28. HUMAN STATEMENT

“a gente sempre pede isso”

é excelente:

```text
process candidate evidence
```

Mas não:

```text
insurer official requirement
```

---

# 29. DOCUMENT REQUEST PATTERN

Uma das melhores oportunidades de learning:

```text
claim type
× insurer
× product
× document
× when requested
× outcome
```

Depois de consistência:

```text
document checklist candidate
```

---

# 30. WAIT STATES

Claims analytics costuma medir cycle time.

AutoBrokers deve ir além:

```text
who owns the wait?
```

Isso torna bottleneck acionável.

---

# 31. OUTCOME

A maior qualidade do corpus depende de knowing outcomes.

Sem outcome, learn:

```text
what people did
```

Com outcome, learn:

```text
what correlated with completion
```

Cuidado: correlação não vira causal truth automaticamente.

---

# 32. CLAIM TRAJECTORY VS TRANSCRIPT

Transcript:

```text
what people said
```

Trajectory:

```text
what happened
```

Para automation learning, Trajectory é muito mais valiosa.

---

# 33. CLAIM IDENTITY

Claim number/protocol é melhor que semantic merge.

No absence:

confidence-aware composite identity.

False merge é high-severity because it contaminates sensitive cases.

---

# 34. CLAIM VS ASSISTANCE

Auto insurance has services that may look “claim-like” but are assistance.

This boundary must be learned/explicit by insurer/product.

Never universal keyword classification.

---

# 35. READINESS SCORE

Score should be used like:

```text
diagnostic / prioritization
```

not:

```text
authorization
```

This is critical.

---

# 36. HARD BLOCKERS

Examples:

- coverage judgment;
- bodily injury;
- medical;
- liability;
- fraud adjudication;
- settlement;
- financial payment.

Volume does not remove governance.

---

# 37. OPERATIONAL DESIGN DOMAIN

Future straight-through claims must be bounded by:

```text
insurer
line
product
claim type
value/risk
documents
channel
regulatory version
exceptions
```

This is more rigorous than “simple claim”.

---

# 38. C0 SHADOW BENEFIT

C0 produces:

- process map;
- bottleneck map;
- evidence corpus;
- autonomy baseline;
- hidden manual work map.

Even without C1, strong ROI in product learning.

---

# 39. C1 ASSIST BENEFIT

Can improve:

- dossier completeness;
- document organization;
- timeline;
- status clarity;
- search effort;
- repeated questions.

Low autonomy, high value.

---

# 40. CLAIMS SHADOW + SPEC-090

Key integration:

```text
Claim Shadow
DOES NOT PUBLISH
```

Outputs:

```text
Evidence
Trajectory
Candidate
Gap
```

Then 090 decides target.

---

# 41. CLAIMS SHADOW + SPEC-091

Repeated human process:

```text
Process Candidate
```

goes to Protocol Factory.

This is how tacit knowledge becomes explicit.

---

# 42. CLAIMS SHADOW + SPEC-100

Only validated reusable microprocesses become Skills.

Not every observed sequence deserves Skill.

---

# 43. CLAIMS SHADOW + SPEC-102

Memory/Second Brain can later retrieve:

- company process;
- published insurer knowledge;
- past experience references.

But source permissions and claim PII remain protected.

---

# 44. CLAIMS SHADOW + SPEC-106 DREAMS

Critical user requirement:

> Dreams must join same architecture.

Therefore 106 must consume:

```text
Claim Trajectories
Claim Shadow Profiles
Candidates
Memories
Knowledge
Protocol Execution Records
```

and output only:

```text
merge/supersede/synthesis/reconfirm/gap candidates
```

No independent Dream brain.

---

# 45. CLAIMS SHADOW + SPEC-108

MetaHarness later monitors:

- extraction accuracy;
- candidate quality;
- leak rate;
- drift;
- readiness misuse;
- cost.

---

# 46. WHY NO CLAIM AUTONOMY NEXT

The shadow needs time/corpus.

Building C4 immediately would mean:

```text
architecture before evidence
```

Instead:

> launch Shadow and let it accumulate while AutoBrokers advances other high-value fronts.

---

# 47. RECOMMENDED NEXT BUSINESS MOVE

After 093, build immediate brokerage-level value on existing reliable data:

# **Executive Intelligence 360 / Pulso 360**

Reason:

- SPEC-081 already proves commercial InfoCap crossing;
- current corpus exists now;
- value is directly visible to broker;
- does not wait for months of Claims Shadow data;
- Shadow accumulates in parallel.

This is the recommended SPEC-094 preview.

---

# 48. SPEC-081 AS FOUNDATION FOR 094

SPEC-081 already established:

> model chooses WHAT, deterministic code DOES.

And built/defined a report linking:

- policies;
- commission;
- producers;
- repasse;
- new vs renewal;
- renewal radar;
- Artifact Hub.

094 should evolve, not rebuild.

---

# 49. 094 SHOULD NOT BECOME A NEW REPORT ENGINE

Use:

```text
InfoCap layer
+
deterministic calculations
+
Artifact Hub
+
Research/Intelligence Fabric
+
AutoBrokers chat
```

One Executive Intelligence Engine, multiple views.

---

# 50. 094 CORE IDEA

Broker asks:

```text
“Como estamos este trimestre?”
```

AutoBrokers answers:

- executive verdict;
- current vs prior equal period;
- producer momentum;
- economics after repasse;
- insurer/branch concentration;
- renewal exposure;
- projection;
- confidence/data coverage.

---

# 51. 094 CLAIMS CONNECTION

Claims Shadow data is optional input later:

```text
claims burden
cycle time
insurer friction
```

Do not block 094 on 093 corpus.

---

# 52. FINAL RESEARCH DECISION

Claims is a perfect domain for the larger AutoBrokers thesis:

```text
OPERAÇÃO
→ TRAJECTORY
→ LEARNING
→ CANDIDATE
→ PROTOCOL/SKILL
→ AAA
→ PUBLISH
→ METAHARNESS
```

Do not jump from operation straight to autonomy.

---

# 53. SOURCE INDEX

Guidewire  
https://www.guidewire.com/products/technology/insurance-ai-from-guidewire  
https://www.guidewire.com/products/core-products/insurancesuite/claimcenter-claims-management-software

Sprout.ai  
https://sprout.ai/resource/claims-decision-intelligence-the-missing-layer-between-your-claims-core-and-better-outcomes/  
https://sprout.ai/resource/claims-automation-vs-claims-ai-whats-the-difference-and-why-does-it-matter/  
https://sprout.ai/resource/ai-wont-replace-claims-handlers-but-it-will-transform-claims/  
https://sprout.ai/resource/why-claims-ai-pilots-stall-before-production-and-how-to-escape-the-pilot-trap/

Snapsheet  
https://www.snapsheetclaims.com/products/snapsheet-ai

Shift Technology  
https://www.shift-technology.com/en-gb/resources/reports-and-insights/arise-a-standard-framework-for-ai-agent-autonomy-in-insurance  
https://www.shift-technology.com/resources/news/shift-technology-launches-shift-claims-to-power-claims-transformation-with-agentic-ai  
https://www.shift-technology.com/resources/case-studies/ai-in-action/ai-insurance-advanced-resolution-techniques

McKinsey  
https://www.mckinsey.com/industries/financial-services/our-insights/insurance-productivity-2030-reimagining-the-insurer-for-the-future  
https://www.mckinsey.com/industries/financial-services/our-insights/claims-2030-dream-or-reality

Deloitte  
https://www.deloitte.com/content/dam/assets-zone1/au/en/docs/industries/insurance/2025/insurance-predictions-2026.pdf

SUSEP  
https://www.gov.br/susep/pt-br/assuntos/meu-futuro-seguro/seguros-previdencia-e-capitalizacao/seguros/seguro-de-automoveis  
https://www.gov.br/susep/pt-br/central-de-conteudos/noticias/2024/dezembro/lei-do-contrato-de-seguro-e-publicada  
https://www.gov.br/susep/pt-br/central-de-conteudos/noticias/2025/dezembro/lei-do-contrato-de-seguro-entra-em-vigor-trazendo-mais-clareza-e-seguranca-juridica-ao-mercado  
https://www.gov.br/susep/pt-br/central-de-conteudos/noticias/2026/agosto/nova-norma-do-cnsp-estabelece-regras-gerais-para-contratos-de-seguros-de-danos

---

# 54. FINAL RULE

> **A Claim Trajectory is evidence of experience, not permission for autonomy.**

A melhor Claims AI do AutoBrokers nasce quando o sistema aprende primeiro exatamente onde o julgamento humano ainda importa.
