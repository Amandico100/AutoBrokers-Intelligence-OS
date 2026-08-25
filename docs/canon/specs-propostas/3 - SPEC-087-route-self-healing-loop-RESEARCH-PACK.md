# SPEC-087 — ROUTE SELF-HEALING LOOP — RESEARCH PACK

**Data:** 25/08/2026  
**Baseline:** `8b49fdb337a6c37eb2ad181f5bad544a55dc0827`  
**Uso:** material de investigação; não carregar inteiro no bootstrap do executor  
**SPEC associada:** `SPEC-087-route-self-healing-loop.md`

---

# 1. TESE

O AutoBrokers já possui quase todas as peças de um loop de aprendizado operacional:

```text
Atlas
Sentinela
Alfaiate
Simulador
Corpus
Régua
Mutations
Work Runs
Approval/RBAC
```

O que não existe como contrato único é:

```text
OBSERVE
→ CANDIDATE
→ PROVE
→ APPROVE
→ CANARY
→ ROLLBACK
```

A 087 cria esse contrato.

---

# 2. SPEC-080 — O QUE ELA PROVOU

A SPEC-080 foi escrita em 18/08 e nunca executada.

O controle de SPECs atual diz explicitamente:

```text
SPEC-080
“a tela que o Atlas viu vira passo proposto”
→ vira base da SPEC-087
```

Achado principal da 080:

uma tela de Allianz havia sido observada:

```text
8 vezes
4 sessões
21 dias
```

e o corredor não sabia responder.

A tela particular foi corrigida manualmente.

A classe de problema permaneceu.

---

# 3. QUATRO CURTOS-CIRCUITOS DA 080

A 080 encontrou:

## C1
`route_sentinel.classify_severity` mandava novas telas de menu para `structural`.

O Alfaiate só era chamado no ramo cosmético.

Resultado histórico:

```text
structural escalated = 4
cosmetic = 0
```

## C2
`playbook_tailor.anchor_from_text` criava anchor do texto cru.

O corredor casava contra texto normalizado.

Patch seria letra morta.

## C3
Writer:

```text
allianz:todos
```

Reader:

```text
allianz-residencial-whatsapp@v1
```

Namespaces diferentes.

## C4
Overlay só representava:

```text
reply = ""
noop = True
```

Não podia dizer:

```text
“responda 1”
```

Logo “aprovar proposta” não bastava.

---

# 4. O CÓDIGO ATUAL AINDA TEM AUTO-APPLY

`route_sentinel.py` atual mantém a doutrina histórica:

```text
COSMETIC
→ Alfaiate v2
→ Simulador
→ apply_auto_overlays
```

`playbook_tailor.py` atual diz explicitamente:

> auto-aplica tela informativa nova como overlay noop.

Isso conflita com a decisão atual do Founder:

```text
auto-propor/testar = SIM
auto-publicar = NÃO
```

A primeira fase executável da 087 deve desarmar essa exceção.

---

# 5. SIMULADOR — ÚTIL, MAS NÃO SUFICIENTE

`ura_simulator.py`:

- cria session real do motor;
- alimenta telas;
- compara resposta atual vs expected;
- detecta `needs_human`;
- detecta final state.

É valioso.

Mas a SPEC-084.2 provou:

> 19 rotas podiam responder 100% das telas e nenhuma passava o portão da Tool.

Portanto:

```text
SIMULATOR PASS
≠
SAFE TO PUBLISH
```

Ele vira uma estação.

---

# 6. 084.1 — LIÇÕES PARA SELF-HEALING

Principais achados aplicáveis:

- teste precisa chamar motor;
- regex verde não prova produto;
- corpus manda;
- handoff correto não é buraco;
- source mutation durante medição ocorreu;
- uma mutation estava commitada;
- native behavior e scope importam;
- “SEM_CORPUS” pode ser coleta ou bug.

Aplicação na 087:

candidate generator não pode inferir patch só porque não encontrou tela no corpus.

Pode ser falta de corpus.

---

# 7. 084.2 — LIÇÕES PARA SELF-HEALING

Principal:

```text
ROTA RESPONDE
≠
TOOL CONSEGUE LEVAR O DADO
```

Gates de candidate precisam cobrir:

```text
route
+
tool contract
+
native flow
+
side effect constraints
```

Outro achado:

replay podia excluir formulário nativo e premiar o buraco.

A 087 precisa exigir native flows quando route usa.

---

# 8. SPEC-089 CANDIDATE — CONTRATO QUE A 087 DEVE CONSUMIR

Decisões congeladas da 089:

```text
score 0–100
+
raw earned/max visível
+
score ≠ certification
+
hard gates non-compensable
+
UNKNOWN fail-closed
+
N/A só com prova
+
rubric version
+
route fingerprint
```

Certificações:

```text
AAA_READY
AAA_VALIDATED
```

Integração planejada:

```text
candidate patch
→ assessment before
→ assessment after
→ compare hard gates
```

A 087 não recria rubrica.

Consome `RouteAssessment`.

---

# 9. MELHORIA INCREMENTAL — POR QUE É NECESSÁRIA

Se uma rota está:

```text
72/100 NOT_READY
```

e um patch seguro resolve uma tela:

```text
81/100 NOT_READY
```

proibir publicação até AAA significaria:

> a rota não pode ficar menos ruim até ficar perfeita de uma vez.

Isso é contraproducente.

Por isso surge um conceito separado:

```text
PATCH_ELIGIBLE
```

sem chamar rota de AAA.

---

# 10. HARD GATE VENCE DELTA

Exemplo:

```text
before 72
after 95
```

mas:

```text
FINALIZE_SAFETY PASS → FAIL
```

Patch é rejeitado.

Não existe soma que compense.

---

# 11. BROWSERBASE SKILLS — PESQUISA ATUAL

O repositório oficial `browserbase/skills` hoje lista:

- `browser`;
- `functions`;
- `browser-trace`;
- `browser-to-api`;
- `autobrowse`.

O padrão é relevante.

Não significa que devemos instalar tudo.

---

# 12. BROWSER-TRACE — A SACADA

`browser-trace` captura:

- CDP firehose;
- Network;
- Console;
- Runtime;
- Page lifecycle;
- screenshots;
- DOM dumps.

E pode anexar um segundo cliente CDP read-only à automação principal.

A ideia:

```text
EXECUTOR
+
OBSERVADOR PASSIVO
```

é ótima para AutoBrokers.

É exatamente a separação que queremos:

```text
fazer
≠
aprender o que aconteceu
```

---

# 13. SPEC-077 JÁ TOMOU UMA DECISÃO IMPORTANTE

A auditoria 077 concluiu que o AutoBrokers não deveria tornar o `browse` CLI uma dependência de runtime só porque os Browserbase Skills o usam.

Razões à época:

- fonte do CLI não auditável no alvo inspecionado;
- Playwright já oferecia CDP;
- já existiam HARs grandes;
- copiar conceito/algoritmo era melhor que instalar dependência.

A 087 preserva essa filosofia:

> upstream é referência de padrão; implementação precisa respeitar stack e segurança do AutoBrokers.

---

# 14. BROWSER-TO-API

O skill oficial atual:

```text
browser-trace
→ network requests/responses
→ OpenAPI 3.1
→ coverage report
```

Padrões úteis:

- pair por request;
- template URLs;
- infer schemas;
- confidence/coverage.

Para AutoBrokers:

```text
API OBSERVED
```

não é:

```text
API SAFE TO CALL
```

Precisamos ainda provar:

- auth;
- side effect;
- idempotency;
- semantics;
- permission.

---

# 15. AUTOBROWSE

Upstream atual descreve:

```text
task.md
→ strategy.md
→ skill.md
```

com execuções iterativas e traces.

A referência documenta graduação quando passa em múltiplas execuções recentes.

Insight:

> o mesmo run que inspirou uma mudança não é validação suficiente da mudança.

Na 087:

- origin session;
- full corpus;
- neighbors;
- mutation.

---

# 16. STAGEHAND v4 — PESQUISA ATUAL

Browserbase anunciou Stagehand v4 em 10/08/2026.

Features públicas atuais incluem:

- self-healing actions;
- iframe support;
- browser-extension architecture;
- server-side caching de act/observe/extract.

O que absorvemos:

```text
semantic recovery can find a new way to perform an action.
```

O que NÃO absorvemos:

```text
if semantic recovery worked, publish it.
```

Recovery vira evidence.

---

# 17. POR QUE SELF-HEALING ≠ AUTONOMOUS CODE MUTATION

Num sistema de seguros:

um patch errado pode:

- abrir serviço errado;
- selecionar cobertura errada;
- confirmar dado falso;
- cancelar solicitação;
- enviar PII;
- criar custo;
- gerar protocolo inválido.

Portanto o loop precisa de approval.

---

# 18. POR QUE ROLLBACK PODE SER AUTOMÁTICO

A release anterior já foi humana e explicitamente aprovada.

A nova também.

Se a nova viola um gate:

```text
rollback
```

não cria conhecimento novo.

Retorna ao último conhecimento aprovado.

É circuit breaker.

---

# 19. PATCH CANDIDATE — ALTERNATIVAS

## A. editar source diretamente e abrir diff
Nota: 50/100

Auditável, mas mistura candidate com implementation e dificulta sandbox.

## B. overlay ativo temporário
Nota: 20/100

Viola gate-before-write.

## C. immutable candidate + compiler
Nota: 98/100

Governança desacoplada do runtime.

Escolhido.

---

# 20. RELEASE SURFACE — NÃO CONGELADA

A Candidate Spec deliberadamente não escolhe ainda:

```text
playbook_overlays
vs
route_release registry
vs
source patch
```

porque isso depende do warm-up atual.

Critérios:

- runtime lê;
- versiona;
- rollback;
- não duplica corredor;
- suporta operações;
- auditável.

---

# 21. FINGERPRINT — NECESSIDADE

A 080 já disse que `md5(texto inteiro)` era uma cota superior grosseira.

Problemas:

- nome do profissional;
- data;
- protocolo;
- whitespace;
- markdown;
- texto personalizado.

A 087 exige structural fingerprint.

---

# 22. STRUCTURAL FINGERPRINT — EXEMPLO

Tela A:

```text
Olá João.
1 - Guincho
2 - Mecânico
```

Tela B:

```text
Olá Maria!
1 - Guincho
2 - Mecânico
```

Same structural fp.

Tela C:

```text
1 - Guincho
2 - Mecânico
3 - Táxi
```

Different structural fp.

---

# 23. EVIDENCE FLOOR

Por segurança:

- LOW pode usar repeated observation;
- HIGH precisa real outcome/review;
- CRITICAL não publica por inferência.

Os pisos exatos devem ser calibrados no warm-up.

---

# 24. NEIGHBOR GRAPH

Uma mudança pode estar num helper compartilhado.

Exemplo:

```text
anchor family
```

usada por:

```text
Allianz/guincho
Allianz/pneu
Allianz/bateria
...
```

Testar apenas target é insuficiente.

A 087 deriva impact set.

---

# 25. SCOPE MINIMIZATION

Se mudança só vale para:

```text
allianz/residencial/eletricista
```

não escrever helper global.

Generalização precisa de evidence.

---

# 26. STALE BASELINE

Candidate nasce contra release 5.

Release 6 entra por outra candidate.

Candidate antiga não pode publicar.

Necessário:

```text
compare-and-swap baseline release
```

---

# 27. STALE EVIDENCE

Insurer pode mudar duas vezes em horas.

Se evidence pack descreve screen A e Atlas agora vê screen B:

candidate precisa reavaliar.

---

# 28. SHADOW DIFFERENTIAL

Antes de agir com patch:

executar decisão baseline e patched em paralelo sem side effect.

Comparar.

Esse padrão ajuda a detectar divergência perigosa antes do canário real.

---

# 29. CANARY

Canary por allowlist é preferível a percentage em fase inicial.

Porque:

- volumes baixos;
- insurers específicas;
- corretoras piloto.

Percentual pode escolher o caso errado.

---

# 30. CIRCUIT BREAKER — HARD VS SOFT

Hard:

- forbidden side effect;
- wrong finalize;
- tenant leak;
- PII;
- Tool Contract fail.

Rollback imediato.

Soft:

- latency;
- small score delta;
- one non-critical divergence.

Investigar.

---

# 31. ROUTE VS MAP

Atlas active map:

```text
descreve realidade observada
```

Route active release:

```text
descreve comportamento autorizado
```

Não juntar.

---

# 32. ALFAIATE — REFRAME

O nome “Alfaiate” pode permanecer.

Mas semanticamente:

```text
ALFAIATE = proposer/compiler
```

não:

```text
publisher
```

Isso alinha com governança.

---

# 33. WORK RUN

Uma candidate pode ser um Work Run.

Exemplo:

```text
route.self_heal.assess
```

Stages:

```text
evidence
candidate
compile
replay
assessment
await approval
```

Não precisa criar worker.

---

# 34. IDENTITY

Candidate key precisa de:

```text
route_ref
baseline release
drift signature
```

Senão o mesmo drift gera candidates duplicadas.

---

# 35. APPROVAL FINGERPRINT

O aprovador deve aprovar exatamente:

```text
candidate V3
compiled hash X
assessment Y
baseline Z
```

Se editor muda anchor depois:

approval morre.

---

# 36. REJECTION FEEDBACK

Rejeição humana é um ótimo sinal de aprendizagem.

Reason codes ajudam a medir:

```text
candidate generator está errando semântica?
evidence está fraca?
scope está largo?
```

Não usar automaticamente para mudar runtime.

---

# 37. ROUTE RELEASE LINEAGE

Toda release precisa apontar parent.

Isso viabiliza:

- diff;
- rollback;
- audit;
- stale candidate.

---

# 38. PII

Browser artifacts podem ser muito mais perigosos do que texto de URA.

HAR pode conter:

- Authorization;
- cookies;
- CPF;
- names;
- addresses.

Nunca colocar bruto no candidate.

---

# 39. GLOBAL LEARNING

Uma route Allianz observada na Resulta pode beneficiar outra brokerage.

Mas o learning global deve transportar:

```text
route fact
```

não:

```text
customer data
```

---

# 40. O QUE NÃO FAZER

| Ideia | Veredito |
|---|---|
| auto-publish noop | NÃO |
| auto-publish structural | NÃO |
| Simulador como juiz único | NÃO |
| score como compensação de gate | NÃO |
| candidate = active overlay | NÃO |
| LLM edita source e mergeia | NÃO |
| new route engine | NÃO |
| new browser runtime | NÃO |
| Temporal | NÃO |
| Browserbase Skills como dependência obrigatória | NÃO |
| global helper sem neighbor test | NÃO |
| candidate baseado só na sessão que o inspirou | NÃO |

---

# 41. REFERÊNCIAS EXTERNAS

Browserbase Skills:
https://github.com/browserbase/skills

Browser Trace:
https://github.com/browserbase/skills/blob/main/skills/browser-trace/SKILL.md

Browser to API:
https://github.com/browserbase/skills/blob/main/skills/browser-to-api/SKILL.md

AutoBrowse:
https://github.com/browserbase/skills/tree/main/skills/autobrowse

Stagehand:
https://github.com/browserbase/stagehand

Stagehand v4 announcement:
https://www.browserbase.com/blog/stagehand

---

# 42. REFERÊNCIAS INTERNAS INSPECIONADAS

- SPEC-080
- ESTADO-DAS-SPECS
- SPEC-083
- SPEC-084.1 report
- SPEC-084.2 report
- SPEC-085/report
- Candidate SPEC-089 via prior program context
- `route_sentinel.py`
- `playbook_tailor.py`
- `ura_simulator.py`
- SPEC-077 audit

---

# 43. VEREDITO

A antiga 080 tentava construir:

```text
Atlas → passo proposto → Founder
```

A 087 deve construir:

```text
Atlas
→ Drift
→ Evidence
→ Candidate
→ Compiler
→ Sandbox
→ Replay
→ Mutation
→ AAA Assessment
→ Authorized Human
→ Canary
→ Circuit Breaker
→ Release / Rollback
```

É um salto de “aprovar um passo” para:

# **governar evolução contínua da inteligência operacional.**

Nota estratégica:

# **100/100**
