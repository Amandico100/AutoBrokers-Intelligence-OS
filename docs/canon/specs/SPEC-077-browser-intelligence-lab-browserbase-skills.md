# SPEC-077 — Browser Intelligence Lab + Browserbase Skills Assimilation
## Trace-first · Browser-to-API · AutoBrowse supervision · adversarial UI QA · Safe Browser · optional Browserbase Remote · Portal Factory integration · zero duplicate architecture

**Status:** PROPOSTA PARA EXECUÇÃO APÓS A SPEC-075  
**Owner:** AutoBrokers.ai / Founder + Líder Técnico  
**Natureza:** arquitetura transversal de engenharia + runtime opcional, NÃO uma nova jornada de negócio  
**Prioridade estratégica:** 99/100  
**Fonte externa principal auditada:** `browserbase/skills`  
**Upstream observado durante a autoria:** commit `6afe8663693372e59e167dfa5be37932af09ae3d` (`main`, 09/07/2026)  
**Data de autoria:** 16/08/2026  
**Numeração:** o Founder reservou **SPEC-077**. Na autoria desta SPEC, `SPEC-076` não foi localizada na `main`. NÃO renumerar silenciosamente; outra frente pode reservar a 076 antes da execução.

---

# 0. DECISÃO EXECUTIVA DESTA SPEC

Esta SPEC NÃO instala “mais um browser agent” dentro do AutoBrokers.

Esta SPEC transforma os melhores padrões do repositório oficial **Browserbase Skills** em capacidades nativas do ecossistema AutoBrokers, reaproveitando o que as SPECs 073, 074 e 075 já construíram.

A decisão arquitetural é:

```text
NÃO:
Agente/Auxiliar
   ↓
Browserbase Skill diretamente
   ↓
browse CLI / shell / CDP irrestrito
   ↓
portal

SIM:
Agente / Auxiliar
   ↓
Skill de NEGÓCIO do AutoBrokers
   ↓
Capability Pack
   ↓
Tool Gateway
   ↓
PortalExecutionGateway
   ↓
Portal Worker
   ↓
Journey + Runtime + Guardrails
   ↓
BrowserProvider
   ├── LocalPlaywright (default)
   └── BrowserbaseRemote (opcional, governado)
   ↓
portal

E EM PARALELO, PARA ENGENHARIA:

Portal Capability Factory
   ↓
Portal Intelligence Lab
   ├── deep trace
   ├── browser-to-api
   ├── strategy training
   ├── adversarial QA
   ├── drift analysis
   └── candidate code/contracts
   ↓
GATES
   ↓
Journey/adapter aprovado
```

Browserbase Skills entram principalmente como **Engineering Skills / Portal Lab Recipes**, não como Skills de negócio entregues diretamente à corretora.

O corretor não deve ver no Portal Admin:

- `browser-trace`;
- `browser-to-api`;
- `autobrowse`;
- `safe-browser`;
- `ui-test`.

O corretor deve continuar vendo Skills e Auxiliares de negócio, como:

- cobrança;
- abrir assistência;
- renovar;
- cotar;
- consultar apólice;
- buscar documentos;
- acompanhar sinistro.

As Skills Browserbase ajudam o AutoBrokers **a construir, aprender, testar, diagnosticar e evoluir** essas capacidades — sem virar uma segunda ontologia de produto.

---

# 1. POR QUE ESTA SPEC EXISTE

As jornadas de portal do AutoBrokers foram historicamente descobertas por trabalho manual e iterativo:

```text
abrir portal
→ F12
→ Network
→ Preserve Log
→ HAR
→ HTML
→ screenshots
→ descobrir XHR/fetch
→ identificar API
→ entender perguntas
→ escrever journey
→ testar
→ corrigir
```

Esse processo funcionou e revelou APIs extremamente valiosas em Allianz, HDI, Tokio, Yelum, MAPFRE e Maxpar/Autoglass.

A SPEC-073 já criou uma fundação importante:

- `PortalProfiler` passivo;
- percepção em camadas;
- redaction;
- guardrails;
- runtime comum;
- discovery;
- vision fallback;
- zero-regression gates.

A SPEC-074 leva Maxpar/Autoglass a API-first e transação segura.

A SPEC-075 transforma Portal Worker em infraestrutura global via Capability Registry, Tool Gateway, PortalExecutionGateway, Work Runs, Portal Factory, fixtures, replay, readiness e concorrência segura.

O próximo salto é eliminar o caráter artesanal restante do desenvolvimento de portais.

Browserbase Skills contém padrões diretamente alinhados a essa necessidade:

- `browser-trace`: segundo cliente CDP passivo, network/console/runtime/page + screenshots + DOM, bissetado por página;
- `browser-to-api`: converte tráfego observado em OpenAPI 3.1 candidato, com schemas, confiança e coverage gaps;
- `autobrowse`: loop evaluate → trace → hipótese → strategy → nova execução, até convergir;
- `ui-test`: QA adversarial com planejamento por ângulos, subagentes, assertions estruturadas e screenshots de falha;
- `safe-browser`: browser restrito por allowlist e sem raw CDP para o agente;
- `browser`: abstração de browser local/remoto, snapshot estruturado antes de screenshot, Browserbase remote opcional;
- `webmcp-gen`: experimento para transformar funções same-origin em tools explícitas;
- `functions`: automações serverless Browserbase — útil como referência, mas NÃO será uma segunda fila/runtime nesta SPEC.

A SPEC-077 existe para absorver **o poder útil** desses padrões e rejeitar o que duplicaria o AutoBrokers.

---

# 2. FONTE EXTERNA — O QUE FOI MEDIDO NO BROWSERBASE SKILLS

## 2.1 Upstream observado

Repositório:

`https://github.com/browserbase/skills`

Commit observado durante a autoria:

`6afe8663693372e59e167dfa5be37932af09ae3d`

A implementação futura DEVE reconsultar a `main` atual do upstream antes de usar qualquer código ou instrução.

Não assumir que a versão analisada nesta SPEC ainda é a última quando a 077 for executada.

## 2.2 Skills relevantes

O README do upstream lista, entre outras:

- `browser`;
- `functions`;
- `browser-trace`;
- `browser-to-api`;
- `autobrowse`;
- `safe-browser`;
- `webmcp-gen`;
- `cookie-sync`;
- `fetch`;
- `search`;
- `ui-test`;
- `browser-use-to-stagehand`;
- `agent-experience`;
- `company-research`;
- `event-prospecting`;
- `competitor-analysis`.

Esta SPEC NÃO deve importar tudo indiscriminadamente.

## 2.3 Classificação AutoBrokers

| Skill upstream | Valor | Destino AutoBrokers | Decisão |
|---|---:|---|---|
| browser-trace | 100/100 | Portal Intelligence Lab + deep diagnostics | ADOTAR PADRÃO E CAPACIDADE |
| browser-to-api | 100/100 | Portal Factory / API Contract Candidate | ADOTAR FORTEMENTE |
| autobrowse | 97/100 | treinamento offline / candidate strategy | ADOTAR COM GUARDRAILS |
| ui-test | 98/100 | QA adversarial portal + dashboard | ADOTAR PADRÃO |
| safe-browser | 99/100 | network/action confinement | ADOTAR PRINCÍPIOS NO RUNTIME |
| browser | 92/100 | dev/lab + optional remote provider | ADOTAR PARCIALMENTE |
| webmcp-gen | 75/100 | experimento futuro | IMPLEMENTAR COMO EXPERIMENTAL |
| cookie-sync | 35/100 produção | lab dedicado | NÃO USAR COM CONTAS PRODUTIVAS |
| functions | 55/100 agora | referência futura | NÃO CRIAR SEGUNDO RUNTIME |
| fetch/search | 65/100 nesta SPEC | futura internet intelligence | FORA DO ESCOPO CENTRAL |
| company/event/competitor research | 40/100 nesta SPEC | futura inteligência comercial | FORA DO ESCOPO |
| browser-use-to-stagehand | 30/100 | migração de stack que não usamos | NÃO ADOTAR |

---

# 3. PRÉ-REQUISITOS

A SPEC-077 só pode iniciar implementação depois de:

1. SPEC-073 verde e integrada;
2. SPEC-074 encerrada, ou explicitamente com gates externos estreitos que não afetem a arquitetura base;
3. SPEC-075 encerrada e com PortalExecutionGateway/Portal Factory funcionando;
4. regressão de Cobrança Feita verde;
5. Portal Worker único preservado;
6. Tool Gateway sem segunda autoridade;
7. Work Run lineage funcional conforme 075;
8. branch/worktree limpos e `origin/main` medido.

Se a SPEC-076 existir no momento da execução:

- ler;
- identificar dependências/conflitos;
- NÃO renumerar esta SPEC;
- registrar relação entre 076 e 077.

---

# 4. FASE ZERO — AUDITORIA OBRIGATÓRIA PELO LÍDER TÉCNICO ANTES DE CODAR

A primeira ação da execução desta SPEC NÃO é editar código.

É fazer uma auditoria curta, profunda e orientada a decisão.

O líder técnico deve usar o modelo de raciocínio mais forte disponível e, se o ambiente suportar, subagentes/juízes especializados.

## 4.1 O que auditar

### AutoBrokers atual

- resultado real das SPECs 073–075;
- Portal Worker runtime;
- `PortalProfiler`;
- `perception.py`;
- `guardrails.py`;
- `runtime.py`;
- journey registry;
- Portal Factory;
- PortalExecutionGateway;
- Tool Gateway;
- Work Runs;
- artifact/evidence storage;
- MinIO;
- current tests;
- current portal jobs;
- current connection model;
- current host allowlists;
- current vision provider abstraction;
- current health/readiness.

### Browserbase Skills atual

Auditar a `main` atual e comparar com o commit-base desta SPEC.

Obrigatório ler no upstream atualizado:

- `README.md`;
- `skills/browser-trace/SKILL.md`;
- `skills/browser-to-api/SKILL.md`;
- `skills/autobrowse/SKILL.md`;
- `skills/ui-test/SKILL.md`;
- `skills/safe-browser/SKILL.md`;
- `skills/browser/SKILL.md`;
- `skills/webmcp-gen/SKILL.md`;
- `skills/functions/SKILL.md`;
- scripts realmente chamados por essas skills;
- license/frontmatter aplicável ao código reutilizado.

## 4.2 O que a auditoria deve responder

1. Que capacidades da 077 já foram implementadas pela 073–075 e NÃO devem ser duplicadas?
2. Qual parte do `browser-trace` é superior ao `PortalProfiler` atual?
3. Qual parte deve continuar sendo lightweight profiler e qual deve ser deep trace on-demand?
4. É possível anexar um segundo CDP client ao Playwright atual sem mudar o executor?
5. Como capturar response bodies sem vazar PII?
6. Como browser-to-api entra na Portal Factory sem virar autoridade automática?
7. Como autobrowse treina estratégias sem autoeditar produção?
8. Como `ui-test` pode testar jornadas externas sem executar side effects indevidos?
9. O host allowlist da 075 já cobre a necessidade do `safe-browser` ou falta egress enforcement real?
10. Onde o Browserbase Remote se encaixa sem virar segundo Portal Worker?
11. Quais custos/PII/compliance impedem remote browser em produção hoje?
12. O que pode ser implementado 100% local e gratuito?
13. O que realmente exige `BROWSERBASE_API_KEY`?
14. Quais partes devem ser copiadas/adaptadas e quais devem continuar upstream/dev-only?
15. Existe alguma proposta nesta SPEC que ficou ultrapassada devido ao código executado pela 075?

## 4.3 Poder para melhorar a SPEC

O líder técnico ESTÁ autorizado a melhorar tecnicamente a execução desta SPEC quando encontrar alternativa claramente superior.

Mas deve distinguir:

**Melhoria técnica não material:** pode incorporar e documentar.

Exemplos:

- nome de classe melhor;
- reaproveitar Artifact Hub existente em vez de nova tabela;
- usar CDP nativo existente em vez de instalar browse CLI no runtime;
- reaproveitar um guardrail 075 em vez de criar outro.

**Mudança material:** precisa parar para Founder.

Exemplos:

- substituir Portal Worker;
- trocar Playwright por Stagehand/Browserbase como executor padrão;
- dar browser direto aos agentes;
- enviar PII produtiva para terceiro sem aprovação;
- criar segunda fila/runtime;
- mudar semântica de Cobrança;
- fazer Browserbase Cloud obrigatório para produção.

## 4.4 Saída da auditoria

Produzir antes de codar:

`docs/canon/reports/SPEC-077-AUDIT.md`

com:

- estado atual;
- divergências;
- capacidades já existentes;
- capabilities Browserbase selecionadas;
- arquitetura final recomendada;
- itens removidos por duplicação;
- riscos;
- decisão `READY` / `READY WITH BLOCKER`.

Se READY e não houver mudança material, EXECUTAR imediatamente sem pedir nova microaprovação.

---

# 5. PRINCÍPIO CENTRAL — DUAS CLASSES DE “SKILL” NÃO PODEM SER CONFUNDIDAS

## 5.1 Skill de negócio AutoBrokers

Exemplo:

- cobrar inadimplentes;
- abrir assistência de vidros;
- renovar seguro;
- consultar apólice.

É consumida por Agent/Auxiliar/Rotina via Work OS.

## 5.2 Engineering Skill / Portal Lab Recipe

Exemplo:

- tracear browser;
- inferir API;
- treinar estratégia;
- rodar QA adversarial;
- gerar candidate adapter.

É consumida por:

- Claude Code;
- engenheiro;
- agente interno de plataforma;
- Portal Factory.

NÃO é oferecida diretamente ao corretor.

## 5.3 Regra de nomenclatura

Para evitar confusão, no código e UI usar preferencialmente:

- `BusinessSkill` para Skill canônica do Work OS quando necessário diferenciar;
- `PortalLabRecipe` ou `EngineeringRecipe` para os procedimentos derivados de Browserbase Skills.

Nunca registrar `browser-trace` como se fosse uma Skill de cobrança/atendimento instalável pelo tenant.

---

# 6. ARQUITETURA-ALVO

```text
┌─────────────────────────────────────────────────────────────┐
│                     WORK OS / BUSINESS                      │
│ Agent · Auxiliar · Rotina · API · Chat                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                      Business Skill
                           │
                     Capability Pack
                           │
                       Tool Gateway
                           │
                  PortalExecutionGateway
                           │
                       portal_job
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                       PORTAL WORKER                         │
│ Journey Registry · Runtime · Guardrails · Perception       │
│ Profiler lightweight · Transaction checkpoints             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    BrowserProvider
              ┌────────────┴─────────────┐
              │                          │
      LocalPlaywright              BrowserbaseRemote
       DEFAULT PROD              OPTIONAL / GOVERNED
              │                          │
              └────────────┬─────────────┘
                           │
                         PORTAL


┌─────────────────────────────────────────────────────────────┐
│                  PORTAL INTELLIGENCE LAB                    │
│                                                             │
│ Portal Factory                                              │
│    ↓                                                        │
│ DeepTrace  → API Infer → Strategy Trainer → UI QA          │
│    ↓              ↓             ↓               ↓           │
│ evidence      OpenAPI       candidate        failures        │
│                  candidate    strategy/code                   │
│                        ↓                                    │
│                    Promotion Gate                           │
│                        ↓                                    │
│               Approved journey/adapter                     │
└─────────────────────────────────────────────────────────────┘
```

---

# 7. BLOCO A — UPSTREAM LOCK + SUPPLY-CHAIN SAFETY

Browserbase Skills é código externo.

Não executar cegamente:

`npx skills add browserbase/skills`

no ambiente de produção ou dentro do runtime principal.

## 7.1 Criar lock de upstream

Artefato sugerido:

`tools/portal_lab/upstream/browserbase-skills.lock.json`

Exemplo:

```json
{
  "repository": "browserbase/skills",
  "audited_commit": "<sha>",
  "audited_at": "<iso>",
  "selected_skills": {
    "browser-trace": "<sha/hash>",
    "browser-to-api": "<sha/hash>",
    "autobrowse": "<sha/hash>",
    "ui-test": "<sha/hash>",
    "safe-browser": "<sha/hash>",
    "browser": "<sha/hash>"
  },
  "license_review": "passed",
  "runtime_dependency": false
}
```

## 7.2 Política de atualização

Upstream update:

```text
check
→ diff
→ security review
→ compatibility tests
→ explicit update of lock
```

NUNCA:

```text
npm latest
→ auto-update
→ produção
```

## 7.3 Gate A

PASSA se:

- upstream commit pinado;
- selected files auditados;
- licença aplicável verificada;
- nenhum script externo executado sem leitura;
- nenhum secret enviado ao upstream.

---

# 8. BLOCO B — PORTAL INTELLIGENCE LAB

Criar uma camada de engenharia integrada à Portal Factory.

Nome recomendado:

`Portal Intelligence Lab`

Ela NÃO é outro runtime de produção.

## 8.1 Local sugerido

Preferência:

`tools/portal_lab/`

para harness/CLI/scripts de engenharia.

Código compartilhado com runtime pode ficar no pacote existente do Portal Worker, mas apenas quando realmente usado por produção.

## 8.2 CLI sugerida

Integrar à Factory existente, em vez de criar CLI concorrente.

Comandos conceituais:

```bash
portal-factory lab doctor
portal-factory lab trace --portal <key> --journey <name>
portal-factory lab api-infer --run <id>
portal-factory lab replay --run <id>
portal-factory lab train --task <task>
portal-factory lab qa --portal <key> --journey <name>
portal-factory lab diff --portal <key>
portal-factory lab promote --candidate <id>
portal-factory lab upstream-check browserbase
```

Se a Factory 075 já tiver nomes equivalentes, REUSAR.

## 8.3 Estado de um Lab Run

Não criar nova tabela sem necessidade.

Primeiro tentar representar como:

- Work Run interno/platform;
- Artifact Hub;
- MinIO;
- evidence existente.

Criar migration somente se o modelo existente não conseguir representar adequadamente:

- run id;
- portal;
- journey;
- source commit;
- trace artifact;
- candidate contract;
- status;
- promotion result.

## 8.4 Gate B

- nenhum runtime duplicado;
- nenhum scheduler novo;
- Lab callable pela Factory;
- artifacts rastreáveis;
- raw data fora do Git.

---

# 9. BLOCO C — DEEP BROWSER TRACE, SEM SUBSTITUIR PORTALPROFILER

O `PortalProfiler` da SPEC-073 continua existindo.

Ele é lightweight, barato, passivo e apropriado para operação normal.

O Browserbase `browser-trace` inspira uma segunda modalidade:

`DeepTrace`.

## 9.1 Diferença

### PortalProfiler

Always-on/light:

- metadados de requests;
- fingerprints;
- poucos eventos;
- sem bodies;
- evidence pequena;
- produção normal.

### DeepTrace

On-demand/debug/discovery:

- Network;
- Console;
- Runtime;
- Log;
- Page lifecycle;
- screenshots;
- DOM snapshots;
- request bodies quando permitido;
- response bodies quando permitido;
- per-page slicing;
- unified timeline.

## 9.2 Segundo CDP client passivo

O padrão upstream demonstra que um segundo cliente CDP pode observar uma sessão sem dirigir a página.

Implementar de forma que:

- journey continua sendo o único driver;
- tracer não envia comandos de ação;
- tracer não muda cookies;
- tracer não navega;
- tracer não clica;
- tracer não libera/reinicia uma sessão que não criou.

## 9.3 Local-first

DeepTrace deve funcionar, se tecnicamente possível, sobre o Chromium/Playwright já usado pelo Portal Worker.

Browserbase NÃO é requisito para trace local.

## 9.4 Event domains

Default:

- Network;
- Console;
- Runtime;
- Log;
- Page.

DOM mutation firehose somente em discovery explícito, pois é ruidoso.

## 9.5 Sampling

Produção normal:

- deep trace OFF.

Discovery/lab:

- screenshot/DOM por evento semântico ou intervalo >=2s;
- teto configurável;
- stop garantido em finally;
- nenhum background process órfão.

## 9.6 Per-page bisect

Gerar estrutura lógica por navegação/tela para reduzir custo cognitivo do Claude:

```text
run/
  summary.json
  unified-events.jsonl
  pages/
    000/
    001/
    002/
```

Cada page bucket deve responder:

- URL normalizada;
- duração;
- request count;
- failures;
- console exceptions;
- action sequence;
- nearest screenshot;
- nearest DOM snapshot.

## 9.7 Unified events

Intercalar:

```json
{"source":"agent","ts":...,"action":"click",...}
{"source":"browser","ts":...,"method":"Network.responseReceived",...}
```

Isso permite provar:

> “a action X foi seguida de HTTP 403 Y”

em vez de:

> “parece que o clique não funcionou”.

## 9.8 Gate C

- journey inalterada com trace desligado;
- deep trace passivo;
- stop/cleanup testado;
- 0 segredo cru persistido;
- run navegável por página.

---

# 10. BLOCO D — RESPONSE BODY CAPTURE CONTROLADO

O `browser-trace` upstream explica uma limitação importante: o firehose CDP não contém automaticamente response bodies.

Para inferir schemas de APIs, precisamos de bodies em modo Lab.

## 10.1 Regra

Body capture é:

- OFF por default;
- Lab/discovery only;
- allowlist de hosts/endpoints;
- size-limited;
- content-type-limited;
- redact-before-persist.

## 10.2 Não persistir bruto por acidente

Pipeline obrigatório:

```text
Network.getResponseBody / equivalent
→ memória temporária
→ redactor
→ shape extractor
→ sanctioned sanitized sample
→ persist
```

Raw body contendo PII não deve ser salvo “para redigir depois”.

## 10.3 Modos

`shape_only`

- tipos/chaves/tamanhos;
- default.

`sanitized_sample`

- valor sanitizado;
- só Lab explícito.

`raw_ephemeral`

- permitido somente em memória temporária, durante análise local controlada;
- nunca Git;
- retention zero ao finalizar run.

## 10.4 Gate D

Mutation obrigatória deve provar que, se o redactor for removido, o teste falha.

---

# 11. BLOCO E — BROWSER-TO-API NATIVO DA PORTAL FACTORY

A capacidade mais valiosa desta SPEC.

## 11.1 Entrada

DeepTrace sanitizado.

## 11.2 Saída

Um **OpenAPI Candidate**, nunca “API oficial”.

Artefatos:

```text
openapi-candidate.yaml
openapi-candidate.json
confidence.json
coverage.md
sanitized-samples/
api-diff.json
```

## 11.3 Endpoint lifecycle

```text
OBSERVED
↓
CANDIDATE
↓
REPLAYED_READONLY
↓
APPROVED_READONLY
↓
APPROVED_MATERIAL
```

Estados auxiliares:

- REJECTED;
- DRIFTED;
- BLOCKED;
- NEEDS_MORE_SAMPLES.

## 11.4 Nunca autoaprovar

O gerador pode inferir:

- path parameters;
- query params;
- request schemas;
- response schemas;
- status codes;
- content types;
- GraphQL operation names;
- JSON-RPC style actions.

Mas não pode decidir sozinho:

- que endpoint material é seguro;
- que auth pode ser reutilizada;
- que endpoint é contratual;
- que POST é idempotente;
- que um campo é opcional apenas porque faltou num sample.

## 11.5 Noise filtering

Implementar/adaptar filtros para:

- analytics;
- telemetry;
- pixels;
- fonts/assets;
- bot defense;
- session plumbing;
- static HTML.

Mas filtros devem ser auditáveis e permitir include override.

## 11.6 Coverage gaps

Gerar relatório:

```text
“Para aumentar a confiança deste contrato, ainda falta exercitar:
- fluxo sem cobertura;
- resposta vazia;
- segunda página;
- outro item coberto;
- erro 409;
...”
```

Isso substitui parte do trabalho manual de perguntar ao Founder quais prints faltam.

## 11.7 Python adapter

O upstream gera client JS de exemplo.

AutoBrokers é Python no Portal Worker.

Após endpoint APPROVED:

- gerar/escrever adapter Python tipado;
- preferir Pydantic/dataclasses existentes;
- HTTP client canônico do projeto;
- timeout/retry do runtime;
- host allowlist;
- session cookie/token legítimo do browser;
- redaction.

Não executar o `client.mjs` upstream diretamente em produção.

## 11.8 Gate E

- Maxpar trace pode reconstruir endpoints já medidos como prova;
- contrato candidato não vira approved sem gate;
- fixtures sanitizadas;
- adapter usa approved ops only.

---

# 12. BLOCO F — API DRIFT DETECTOR

Quando um portal muda, não queremos descobrir apenas por “element not found”.

## 12.1 Comparar

Approved API Contract
versus
new observed candidate.

## 12.2 Classificar

`none`

`additive`

`breaking_request`

`breaking_response`

`auth_changed`

`endpoint_removed`

`status_semantics_changed`

`unknown`

## 12.3 Ação

Additive:

- registra;
- pode continuar se campos usados permanecem.

Breaking:

- fail-closed na capability afetada;
- abre dossiê de drift;
- dispara Lab replay/análise;
- não autoedita produção.

---

# 13. BLOCO G — AUTOBROWSE: AUTO-MELHORIA SEM AUTO-MUTAÇÃO DE PRODUÇÃO

Esta é a parte mais poderosa e mais perigosa.

Adotar o loop conceitual:

```text
EVALUATE
↓
TRACE
↓
FIND FAILURE
↓
ONE HYPOTHESIS
↓
UPDATE CANDIDATE STRATEGY
↓
RE-RUN
↓
JUDGE
↓
KEEP or REVERT
```

## 13.1 Onde pode rodar

- fixtures;
- mock portals;
- localhost;
- dedicated test accounts;
- read-only live flows;
- Browserbase remote lab quando aprovado.

## 13.2 Onde NÃO pode rodar livremente

- conta produtiva criando atendimento;
- boleto material;
- cancelamento;
- alteração de pagamento;
- qualquer fluxo que gere side effect sem sandbox/idempotency específico.

## 13.3 PortalTaskDefinition

Cada treino precisa declarar:

```yaml
name: maxpar-question-engine-readonly
portal_key: maxpar
journey: abrir_atendimento
allowed_effects:
  - READ_ONLY
allowed_domains:
  - abraseuatendimento.com.br
  - api.autoglass.com.br
success_criteria:
  - policy_preflight_resolved
  - question_engine_detected
forbidden:
  - POST /atendimentos
  - POST /questionarios
max_iterations: 5
max_steps: 60
```

## 13.4 Uma hipótese por iteração

Não permitir “mudei 12 coisas e melhorou”.

Cada iteração registra:

- failure evidence;
- hypothesis;
- exact change;
- pass/fail;
- turns;
- duration;
- model cost;
- browser cost.

## 13.5 Candidate strategy

`strategy.md` é CANDIDATO.

Não é Skill de produção.

## 13.6 Graduation

Um candidate só pode “graduar” se:

- N execuções limpas consecutivas;
- zero forbidden actions;
- zero cross-tenant;
- zero secret leak;
- success criteria determinísticos;
- melhora de success rate ou redução de steps;
- juiz crítico aprova evidência;
- replay offline verde;
- mutations verdes.

Valor inicial sugerido:

- 5 passes consecutivos para read-only;
- 3 passes + canário explícito para flows materiais em ambiente autorizado.

## 13.7 Self-healing NÃO significa self-deploy

Produção pode:

- detectar drift;
- capturar trace;
- gerar candidate patch;
- gerar candidate strategy;
- abrir internal artifact/issue.

Produção NÃO pode:

- editar journey;
- commit;
- merge;
- deploy;

sozinha.

---

# 14. BLOCO H — CODEGEN PARA AUTOBROKERS, NÃO PARA STAGEHAND POR DEFAULT

O upstream suporta codegen de Playwright/Stagehand.

AutoBrokers deve adaptar o conceito.

## 14.1 Custom target

Criar, se realmente trouxer ganho:

`autobrokers-journey-python`

Ele gera apenas um candidate scaffold compatível com:

- journey registry;
- `JourneyResult`;
- `PortalRuntimeContext`;
- `PortalActionGuard`;
- `PortalApiSession`/adapter equivalente;
- redaction;
- approved API contract.

## 14.2 Candidate only

Generated code vai para:

`generated/candidates/`

ou diretório de Lab ignorado pelo Git até promoção.

Nunca sobrescreve journey existente.

## 14.3 Verificação

Generated candidate deve passar:

- static checks;
- contract tests;
- fixtures;
- mutation pack;
- replay;
- code review;
- canary.

---

# 15. BLOCO I — UI-TEST ADVERSARIAL COMO GATE DA PORTAL FACTORY

Inspirar-se fortemente no `ui-test` upstream.

## 15.1 Filosofia

O objetivo do teste não é confirmar que “parece funcionar”.

É tentar quebrar.

## 15.2 Três rodadas de planejamento

Antes de lançar subagentes:

1. functional;
2. adversarial;
3. coverage gaps.

Depois deduplicar.

## 15.3 Grupos paralelos

Exemplos:

- Group A: happy path + deterministic fields;
- Group B: errors/business rules;
- Group C: session/recovery;
- Group D: drift/UI;
- Group E: security/identity;
- Group F: transaction guards.

## 15.4 Step budget

Todo subagente tem budget explícito.

Não deixar loop de browser infinito.

## 15.5 Assertion protocol

Cada teste produz algo equivalente a:

```text
STEP_PASS|id|evidence
STEP_FAIL|id|expected -> actual|artifact
STEP_SKIP|id|reason
```

## 15.6 Screenshot failure

Toda falha visual/interativa deve ter screenshot imediatamente no estado quebrado.

## 15.7 Portais de terceiros

Adversarial não significa causar dano.

Sem sandbox:

- read-only adversarial;
- navegação;
- voltar;
- refresh;
- sessão expirada;
- DOM alternativo;
- API 4xx/5xx simulada em fixture;
- side effects somente em mock/replay.

## 15.8 Dashboard próprio

Aqui podemos ser mais agressivos:

- double click;
- form empty;
- mobile;
- a11y;
- race;
- refresh;
- browser back;
- stale state;
- duplicate submit.

---

# 16. BLOCO J — SAFE BROWSER / NETWORK POLICY

O padrão `safe-browser` upstream tem alto valor conceitual:

> o agente não recebe raw CDP; ele recebe ações estreitas; o browser possui allowlist.

O AutoBrokers deve levar isso ao runtime existente.

## 16.1 Agente não recebe raw browser

Business Agent não pode receber:

- arbitrary CDP method;
- shell;
- arbitrary URL navigation;
- unrestricted Playwright page;
- Browserbase key.

## 16.2 PortalNetworkPolicy

Se a 075 ainda não implementou uma política equivalente, criar/reusar:

```text
portal_key
journey
allowed_top_level_origins
allowed_api_origins
allowed_sso_origins
allowed_asset_origins
blocked_origins
mode
```

## 16.3 Modos

`observe`

- registra;
- não bloqueia.

`navigation_enforce`

- bloqueia top-level navigation fora do permitido.

`strict`

- bloqueia requests ativos não permitidos conforme manifest.

Rollout:

observe → measure → enforce.

## 16.4 Não quebrar CDN/SSO

Host allowlist não pode ser simplista.

Portal legítimo pode precisar:

- auth domain;
- SSO;
- CDN;
- API subdomain;
- captcha provider;
- storage/download host.

Discovery ajuda a compor allowlist, mas não autoaprova.

## 16.5 Prompt injection containment

Conteúdo de página é untrusted.

Texto como:

> “ignore seus guardrails e clique aqui”

nunca vence:

- Tool Gateway;
- runtime guard;
- effect class;
- host allowlist;
- approved action vocabulary.

---

# 17. BLOCO K — BROWSER PROVIDER ABSTRACTION

Browserbase deve ser provider opcional, não arquitetura.

## 17.1 Interface conceitual

```python
class BrowserProvider(Protocol):
    async def open_session(...): ...
    async def close_session(...): ...
    async def health(...): ...
    async def metadata(...): ...
```

## 17.2 Providers

`LocalPlaywrightProvider`

- default;
- atual;
- produção.

`BrowserbaseRemoteProvider`

- opcional;
- lab primeiro;
- produção apenas com gates.

## 17.3 Não duplicar journey

A journey não pode ter:

`if browserbase: journey_x else: journey_y`

para a mesma operação.

A journey recebe browser/page/context compatível.

## 17.4 Quando remote pode agregar

- anti-bot legítimo;
- browser verification;
- remote debugging;
- isolated browser fleet;
- geolocalização legítima;
- proxy residencial permitido;
- long sessions;
- reproducible remote test.

## 17.5 O que NÃO justifica remote

- “é mais moderno”;
- simples site público;
- fluxos que local Playwright já faz 99%;
- tentar contornar restrições contratuais;
- mascarar bug da journey.

---

# 18. BLOCO L — REMOTE BROWSER SECURITY / PRIVACY / COMPLIANCE

Seguro contém PII e dados sensíveis de negócio.

Browserbase Cloud é terceiro.

## 18.1 Default

`BROWSERBASE_REMOTE_PROD_ENABLED=false`

## 18.2 Lab

Primeiros testes remote devem usar:

- dados sintéticos;
- conta de teste dedicada;
- nenhum cliente real, se possível;
- sem side effect material.

## 18.3 Antes de produção

Founder/empresa precisa validar, conforme aplicável:

- DPA/contrato;
- regiões disponíveis;
- retention;
- subprocessors;
- sessão recording;
- proxy behavior;
- data handling;
- custo.

Não transformar isso em discussão jurídica infinita, mas não enviar PII produtiva para terceiro sem decisão consciente.

## 18.4 Secrets

`BROWSERBASE_API_KEY`:

- secret de plataforma;
- nunca tenant prompt;
- nunca evidence;
- nunca screenshot;
- nunca Git.

## 18.5 Contexts

Se Browserbase persistent contexts forem usados:

- contexto isolado por account/tenant quando necessário;
- ownership verificado;
- lifecycle explícito;
- não reutilizar contexto entre corretoras.

## 18.6 Cookie-sync

PROIBIDO em produção com Chrome pessoal do Founder/funcionários.

Pode ser usado somente:

- lab;
- conta de teste dedicada;
- consentimento explícito;
- ambiente isolado.

Produção continua usando o modelo canônico de credenciais do AutoBrokers.

---

# 19. BLOCO M — PROVIDER FAILOVER SEM DUPLICAR EFEITO

Nunca fazer:

```text
local falhou
→ abre Browserbase
→ repete tudo
```

sem considerar estado transacional.

## 19.1 READ_ONLY

Fallback local → remote pode ser automático se:

- idempotente;
- identity revalidated;
- policy allows;
- budget allows.

## 19.2 Antes do primeiro material effect

Pode recriar sessão em provider remoto se:

- nenhum checkpoint material armado/submitted;
- contexto pode ser reestabelecido;
- tenant/account revalidado.

## 19.3 Depois de material effect

Se estado:

- armed;
- submitted;
- unknown;
- maybe_committed;

NÃO trocar provider e repetir.

Primeiro reconcile.

## 19.4 Gate M

Mutation test: forçar provider failure imediatamente depois de material submission deve PROIBIR retry no segundo provider.

---

# 20. BLOCO N — BROWSERBASE VERIFIED / CAPTCHA / PROXIES

Essas capacidades existem no browser skill upstream, mas devem ser governadas.

## 20.1 Verified browser

Pode ser benchmarkado para portais que bloqueiam automação legítima.

## 20.2 CAPTCHA

Não assumir que “resolver CAPTCHA automaticamente” é permitido em todo portal.

Policy por portal:

- `human_required`;
- `provider_allowed`;
- `not_applicable`.

Default quando desconhecido:

`human_required`.

## 20.3 Proxies

Só usar para:

- estabilidade legítima;
- região necessária ao serviço;
- testes autorizados.

Nunca para burlar restrição contratual ou operar em contexto geográfico falso.

## 20.4 2FA / passkey

Permanece HITL quando necessário.

Browserbase não deve virar justificativa para automatizar autenticação que exige humano por política.

---

# 21. BLOCO O — WEBMCP EXPERIMENTAL

`webmcp-gen` é interessante, mas não deve ser fundação da arquitetura.

## 21.1 Lab only

Criar prova de conceito em 1 portal não material ou app interno.

## 21.2 Objetivo

Avaliar se registrar funções same-origin explícitas reduz fragilidade de DOM.

## 21.3 Não promover se

- exige browser flags inviáveis;
- depende de Stagehand runtime novo;
- duplica API adapter;
- amplia risco.

## 21.4 Gate

Somente virar capability real se superar API/DOM atual em estabilidade e manutenção.

---

# 22. BLOCO P — BROWSERBASE FUNCTIONS FORA DO CAMINHO CRÍTICO

Browserbase Functions permite serverless browser automation.

Nesta SPEC:

NÃO migrar `portal_jobs` para Browserbase Functions.

NÃO criar cron paralelo.

NÃO criar webhook runtime paralelo.

Pode ser benchmarkado posteriormente para:

- Lab jobs;
- read-only discovery;
- QA isolado.

Só virar provider futuro se provar ganho e continuar sob Work Run/Tool Gateway.

---

# 23. BLOCO Q — INTEGRAR AO PORTAL CAPABILITY FACTORY DA 075

A 077 deve tornar a Factory muito mais poderosa, não criar uma segunda Factory.

## 23.1 Onboarding futuro ideal

```text
portal-factory scaffold-portal sancor
↓
portal-factory lab trace ...
↓
portal-factory lab api-infer ...
↓
portal-factory lab coverage ...
↓
portal-factory scaffold-journey ...
↓
portal-factory replay ...
↓
portal-factory lab train ...
↓
portal-factory lab qa ...
↓
portal-factory readiness ...
↓
canary
↓
promote
```

## 23.2 Não criar por seguradora

Browserbase artifacts não mudam a regra da 075:

nova seguradora na Cobrança
→ nova journey/capability support
→ mesmo Auxiliar.

---

# 24. BLOCO R — PLATFORM-ONLY CAPABILITIES

Se a arquitetura 075 permitir Tool Gateway platform scope, criar capabilities internas estreitas, não browser raw:

- `platform.portal.trace.capture`;
- `platform.portal.trace.inspect`;
- `platform.portal.api.infer`;
- `platform.portal.strategy.evaluate`;
- `platform.portal.qa.run`;
- `platform.portal.remote.test`.

Essas capabilities:

- NÃO entram nos packs do tenant;
- NÃO aparecem para corretor;
- NÃO autorizam material side effect;
- servem engineering/admin.

Se o Work OS atual não tiver conceito limpo de platform-only tool, usar Portal Factory CLI diretamente e registrar isso como limite — não inventar um workaround inseguro.

---

# 25. BLOCO S — PORTAL ADMIN / UX

## 25.1 Tenant Portal Admin

Não mostrar Browserbase skills.

Mostrar somente resultado relevante:

- portal conectado;
- capabilities disponíveis;
- health;
- readiness;
- falha que precisa humano.

## 25.2 Global Admin / Engineering

Pode existir área:

`Portal Lab`

com:

- portal;
- journey;
- last trace;
- drift;
- approved API contract;
- candidate API changes;
- QA score;
- current browser provider;
- last canary;
- readiness;
- cost.

Não construir dashboard gigante se CLI + artifact report resolver no início.

---

# 26. BLOCO T — OBSERVABILITY

Métricas mínimas:

## Trace

- deep_trace_runs;
- trace_duration_ms;
- network_events;
- console_errors;
- response_body_samples;
- redaction_hits;
- trace_bytes;
- trace_dropped_events.

## API infer

- endpoints_observed;
- endpoints_candidate;
- endpoints_approved;
- schema_confidence;
- breaking_diffs;
- coverage_gaps.

## AutoBrowse

- iterations;
- pass_rate;
- steps;
- cost;
- strategy_regressions;
- forbidden_action_attempts.

## QA

- pass;
- fail;
- skip;
- mutation_kill_rate.

## Provider

- local_success_rate;
- remote_success_rate;
- fallback_count;
- session_cost;
- proxy_bytes;
- captcha_events;
- identity_failures.

---

# 27. BLOCO U — COST CONTROL

Browser automation pode ficar caro se trace, vision e remote forem usados o tempo todo.

## 27.1 Regra

Determinismo primeiro.

```text
API
→ DOM
→ lightweight profiler
→ adaptive
→ vision
→ deep trace / Lab
```

DeepTrace não é sempre-on.

## 27.2 Budgets

Configurações sugeridas:

- max trace duration;
- max screenshots;
- max body bytes;
- max AutoBrowse iterations;
- max browse steps;
- max remote session duration;
- max model spend per training task.

## 27.3 Attribution

Quando remote cloud for usado, custo deve ser atribuível a:

- portal;
- journey;
- lab run/work run;
- company quando aplicável.

---

# 28. BLOCO V — SECURITY / PII REDACTION

Reutilizar o redactor canônico.

Não criar redactor Browserbase paralelo.

## 28.1 Redigir

- Authorization;
- Cookie;
- Set-Cookie;
- API keys;
- JWT;
- CPF/CNPJ;
- placa;
- chassi;
- apólice;
- telefone;
- email;
- CEP/endereço;
- protocol/account ids conforme política;
- query params sensíveis;
- form bodies;
- local/session storage quando capturado.

## 28.2 Screenshot

Screenshot pode conter PII.

Não pode ir ao Git.

Se armazenado:

- bucket privado;
- TTL;
- company scope se aplicável;
- access log;
- redaction/blur quando possível antes de compartilhar.

---

# 29. BLOCO W — FAILURE-TO-LEARNING LOOP

Quando uma journey falha em produção:

## 29.1 Não auto-retry material

Guardrails continuam vencendo.

## 29.2 Produzir learning bundle

Se permitido:

```text
failure
→ lightweight evidence
→ optional deep trace on safe replay
→ candidate drift analysis
→ candidate API diff
→ candidate strategy
→ issue/artifact
```

## 29.3 Não self-patch live

AutoBrokers pode **aprender automaticamente** sem **mudar produção automaticamente**.

Essa distinção é obrigatória.

---

# 30. BLOCO X — PORTAL SIMULATOR / REPLAY

Para colher máximo valor de AutoBrowse/UI Test sem criar pedidos reais, construir/reusar simulador de portal baseado em fixtures.

## 30.1 Replay layers

- network fixture replay;
- HTML/DOM fixture;
- state machine fixture;
- error injection.

## 30.2 Error injection

Deve conseguir simular:

- 401;
- 403;
- 404;
- 409;
- 429;
- 500;
- timeout;
- empty body;
- malformed JSON;
- missing field;
- option reorder;
- text case change;
- selector drift;
- session expired;
- response after submit lost;
- maybe_committed.

---

# 31. MUTATION TESTS OBRIGATÓRIOS

Mínimo inicial: 35 mutações relevantes.

A suíte deve matar deliberadamente, entre outros:

1. tracer começa a clicar;
2. tracer persiste Authorization;
3. tracer persiste Cookie;
4. screenshot bruto vai para Git fixture;
5. body raw persiste antes de redaction;
6. candidate endpoint vira approved automaticamente;
7. POST observed vira approved material sem gate;
8. API schema de um sample é tratado como contrato obrigatório;
9. AutoBrowse altera journey de produção diretamente;
10. AutoBrowse aceita regressão de pass rate;
11. AutoBrowse ignora forbidden action;
12. strategy graduation com 1 única execução;
13. UI test reporta PASS sem evidence;
14. UI test não captura failure artifact;
15. remote provider recebe key em log;
16. remote provider reutiliza context entre tenants;
17. fallback local→remote após maybe_committed;
18. host allowlist é ignorada;
19. page content consegue solicitar raw CDP;
20. agent consegue navegar off-domain;
21. remote prod habilita sem flag;
22. cookie-sync usa profile pessoal;
23. Browserbase Function vira segunda fila;
24. Portal Lab cria tool tenant-facing por engano;
25. business Skill importa `browse` CLI;
26. endpoint drift breaking não bloqueia adapter;
27. redactor não mascara query param CPF;
28. redactor não mascara placa;
29. trace DOM captura secret hidden field;
30. same account concorrente abre dois remote contexts em write flow;
31. training usa conta real material sem approval;
32. selector position-based passa onde option order muda;
33. provider switch não revalida tenant;
34. deep trace failure derruba Cobrança;
35. upstream auto-update muda scripts sem audit.

Gate:

mutation kill rate = 100% para guardas P0/P1 listados acima.

---

# 32. MATRIZ DE REGRESSÃO

Antes/depois da 077, provar:

## Cobrança Feita

- Allianz;
- HDI;
- Tokio;
- Yelum;
- Zurich;
- MAPFRE quando live.

## Vidros

- preflight;
- coverage absent;
- question engine;
- transaction gate;
- resume;
- evidence.

## Runtime

- Portal Worker local sem Browserbase funciona igual;
- trace OFF não muda behavior;
- remote OFF não muda behavior;
- vision OFF continua fallback correto;
- Tool Gateway continua autoridade;
- Work Run lineage preservada.

---

# 33. EVALS COM CASOS REAIS

Usar um conjunto de tarefas representativo.

## 33.1 Discovery

- MAPFRE cobrança;
- Maxpar/Yelum question engine;
- Porto coverage absent;
- uma journey com SSO;
- uma journey com HTML mais frágil.

## 33.2 Métricas

Antes vs depois:

- tempo para descobrir endpoint;
- ações manuais do Founder;
- quantidade de prints/HAR manuais;
- tempo até fixture verde;
- tempo até journey verde;
- endpoint coverage;
- regression escapes;
- manutenção após drift.

## 33.3 Meta estratégica

Reduzir drasticamente o custo de onboarding de uma nova journey.

A 075 mede onboarding.

A 077 deve provar melhora adicional mensurável.

---

# 34. BROWSERBASE CLOUD BENCHMARK

Não tornar cloud obrigatório sem benchmark.

## 34.1 Comparar

Local Playwright
versus
Browserbase Remote

em 3 classes:

1. portal simples;
2. portal protegido;
3. portal com sessão longa.

## 34.2 Medir

- success rate;
- latency;
- session start time;
- failure rate;
- CAPTCHA frequency;
- proxy bytes;
- cost/run;
- operational complexity;
- PII exposure surface.

## 34.3 Decisão

Browserbase pode terminar a SPEC como:

- `lab_only`;
- `read_only_fallback`;
- `production_candidate`;
- `not_worth_it`.

Não forçar resultado positivo.

---

# 35. COMO O AGENTE/AUXILIAR GANHA O BENEFÍCIO SEM GANHAR O BROWSER CRU

Exemplo futuro:

```text
Auxiliar Renovação
→ Skill renovação
→ capability portal.policy_read
→ Tool Gateway
→ PortalExecutionGateway
→ journey Allianz
→ approved API adapter descoberto pelo Portal Lab
```

O Auxiliar ganha:

- journey mais rápida;
- menos drift;
- API-first;
- recovery melhor;
- remote fallback se aprovado.

Mas não ganha:

- Browserbase API key;
- CDP;
- shell;
- `browse` CLI;
- permission to invent URL.

Esse é o resultado correto.

---

# 36. ARQUIVOS/PASTAS PROVÁVEIS

A auditoria deve ajustar os nomes ao código real.

Possíveis novos:

```text
tools/portal_lab/
tools/portal_lab/upstream/browserbase-skills.lock.json
tools/portal_lab/trace/
tools/portal_lab/api_infer/
tools/portal_lab/training/
tools/portal_lab/qa/
backend/portal_worker/browser_provider.py
backend/portal_worker/deep_trace.py
backend/portal_worker/network_policy.py
backend/portal_worker/api_contracts.py
backend/tests/test_spec077_*.py
docs/canon/PORTAL-INTELLIGENCE-LAB.md
docs/canon/reports/SPEC-077-AUDIT.md
docs/canon/reports/SPEC-077-EXECUTION-REPORT.md
```

Possíveis alterados:

- Portal Factory 075;
- PortalRuntimeContext;
- profiler integration;
- health;
- admin global mínimo;
- tool/capability registry se platform-only capability for apropriada.

---

# 37. ARQUIVOS/SISTEMAS QUE NÃO DEVEM SER REESCRITOS

Salvo necessidade comprovada:

- Cobrança Feita business rules;
- existing journeys maduras;
- Work Run runtime;
- Tool Gateway authority;
- Auxiliary Factory;
- Redis queue model;
- Qdrant/RAG;
- Memory Fabric;
- WhatsApp runtime;
- MinIO architecture;
- Supabase Auth;
- portal account credential model;
- MAPFRE guard já provado;
- Maxpar transaction semantics da 074.

---

# 38. FEATURE FLAGS / MODES

Sugestões — adaptar aos padrões existentes.

```text
PORTAL_DEEP_TRACE_ENABLED=false
PORTAL_API_INFER_ENABLED=false
PORTAL_AUTOTRAIN_ENABLED=false
PORTAL_NETWORK_POLICY_MODE=observe
PORTAL_BROWSER_PROVIDER=local
BROWSERBASE_REMOTE_LAB_ENABLED=false
BROWSERBASE_REMOTE_PROD_ENABLED=false
```

Evitar flag explosion.

Se a 075 já criou registry/config central equivalente, usar aquilo.

---

# 39. ROLLOUT

## Fase 1 — local lab

- Browserbase Cloud OFF;
- trace local;
- API infer local;
- fixtures;
- QA;
- AutoBrowse on mock/read-only.

## Fase 2 — deep trace canary

- uma journey madura;
- trace on-demand;
- comportamento inalterado.

## Fase 3 — API infer

- reproduzir uma API já conhecida;
- provar OpenAPI candidate sem inventar.

## Fase 4 — AutoBrowse

- task read-only;
- candidate strategy;
- no production mutation.

## Fase 5 — adversarial QA

- simulator;
- dashboard;
- read-only live.

## Fase 6 — Browserbase remote lab

Somente se houver API key e aprovação.

## Fase 7 — read-only remote canary

Se benchmark justificar.

## Fase 8 — production candidate

Somente após privacy/security/cost gates.

---

# 40. ROLLBACK

## Local Lab

Desabilitar comandos/feature.

Produção não muda.

## DeepTrace

Flag OFF.

PortalProfiler lightweight continua.

## API infer

Candidate artifacts podem ser ignorados.

Approved adapters não são removidos automaticamente.

## AutoBrowse

Desligar trainer.

Production journeys intactas.

## Network policy

strict → observe.

## Browserbase remote

provider → local.

Mas se existir transaction unknown/maybe_committed, reconciliar antes de qualquer retry.

---

# 41. TESTES DE ACEITE POR CAPACIDADE

## Browser Trace

- attach passivo;
- captures network;
- captures console exception;
- captures page transition;
- screenshot/DOM linked by timestamp;
- bisect pages;
- cleanup after crash;
- no behavior change.

## Browser-to-API

- discover known Maxpar GET;
- detect request schema;
- detect response schema from sanitized sample;
- report missing response body when absent;
- noise filtered;
- confidence explicit;
- no autoapproval.

## AutoBrowse

- controlled task improves or reverts;
- one hypothesis per iter;
- forbidden action = failure;
- graduation requires repeated success.

## UI Test

- functional/adversarial/coverage rounds;
- parallel groups;
- evidence assertions;
- screenshot on fail;
- skip on budget.

## Safe Browser

- off-domain navigation blocked in enforce mode;
- required API domain allowed;
- agent cannot issue raw CDP;
- prompt injection cannot widen allowlist.

## Remote Provider

- local remains default;
- remote works in lab;
- context tenant isolation;
- key redacted;
- failure does not duplicate transaction.

---

# 42. CANÁRIOS

## Canary 1 — passive trace

Uma journey READ_ONLY madura.

Compare trace OFF vs ON.

Business result deve ser idêntico.

## Canary 2 — API inference

Use fluxo cuja API já conhecemos.

O inferidor deve descobrir contrato compatível.

## Canary 3 — drift fixture

Altere intencionalmente response fixture.

Detector deve classificar breaking.

## Canary 4 — QA

Teste dashboard/portal mock com bug plantado.

UI test deve encontrá-lo.

## Canary 5 — Browserbase Remote

Somente read-only, conta dedicada.

---

# 43. RELAÇÃO COM A SPEC-075

A 075 continua sendo a autoridade de:

- Portal Capability Factory;
- Tool Gateway bridge;
- connection resolver;
- portal_job lineage;
- readiness;
- concurrency;
- retry/effect class;
- Agents/Auxiliares.

A 077 NÃO reabre essas decisões.

A 077 amplia a Factory com capacidades de:

```text
OBSERVE
UNDERSTAND
INFER
TRAIN
TEST
DIAGNOSE
```

A 075 é a fábrica.

A 077 instala instrumentos de laboratório de nível muito superior dentro dela.

---

# 44. RELAÇÃO COM A SPEC-073

A 073 continua sendo a autoridade do runtime hardening.

`PortalProfiler` NÃO é removido.

`perception.py` NÃO é substituído por `browse snapshot`.

`guardrails.py` NÃO é substituído por `safe-browser`.

A 077:

- acrescenta DeepTrace;
- fortalece network confinement;
- usa trace para aprendizagem/QA;
- pode oferecer remote provider.

---

# 45. RELAÇÃO COM A SPEC-074

A 074 é o melhor benchmark inicial para a 077 porque já temos:

- HARs;
- HTMLs;
- API conhecida;
- question engine;
- transaction boundaries;
- coverage errors;
- selectors problemáticos.

A 077 deve conseguir mostrar que, se Maxpar fosse onboarding hoje:

- menos trabalho manual seria necessário;
- endpoints seriam inferidos automaticamente;
- coverage gaps seriam indicados;
- question engine seria descoberto;
- UI mutation tests pegariam option reorder;
- transaction guards não seriam quebrados.

---

# 46. SEGURANÇA CONTRA OVERENGINEERING

A SPEC falha se terminar com:

- dois Portal Workers;
- duas Portal Factories;
- duas filas;
- duas ontologias de Skill;
- dois Tool Gateways;
- Stagehand obrigatório;
- Browserbase obrigatório;
- um framework gigante apenas para trace;
- agentes tenant com shell/browser raw;
- auto-deploy por AutoBrowse.

Máximo poder NÃO significa máximo número de componentes.

Significa máximo ganho operacional por unidade de arquitetura.

---

# 47. SEQUÊNCIA RETA DE EXECUÇÃO

A execução deve ser preferencialmente UMA leva contínua após a auditoria.

## PASSO 0

Preflight Git/worktree/branch/HEAD/status.

## PASSO 1

Auditar upstream Browserbase atual.

## PASSO 2

Auditar resultado real 073–075.

## PASSO 3

Produzir SPEC-077-AUDIT.

## PASSO 4

Eliminar duplicações da proposta.

## PASSO 5

Criar upstream lock.

## PASSO 6

Integrar Portal Lab à Factory existente.

## PASSO 7

Implementar DeepTrace local/passivo.

## PASSO 8

Implementar sanitizer/body shape capture.

## PASSO 9

Implementar per-page bisect/unified events.

## PASSO 10

Implementar API inference candidate pipeline.

## PASSO 11

Implementar contract confidence/coverage.

## PASSO 12

Implementar API drift diff.

## PASSO 13

Implementar AutoBrowse-style trainer controlado.

## PASSO 14

Implementar strategy judge/revert.

## PASSO 15

Implementar optional candidate codegen.

## PASSO 16

Implementar adversarial UI QA harness.

## PASSO 17

Integrar network policy/safe-browser principles.

## PASSO 18

Implementar platform-only internal capabilities se arquitetura 075 suportar.

## PASSO 19

Implementar BrowserProvider abstraction somente se ainda não existir equivalente.

## PASSO 20

Implementar BrowserbaseRemote provider LAB ONLY.

## PASSO 21

Implementar cost/security meters.

## PASSO 22

Rodar mutation suite.

## PASSO 23

Rodar regressão Cobrança + Vidros.

## PASSO 24

Canary passive trace.

## PASSO 25

Canary browser-to-api sobre API conhecida.

## PASSO 26

AutoBrowse task read-only.

## PASSO 27

UI adversarial test.

## PASSO 28

Remote Browserbase benchmark se permitido.

## PASSO 29

Readiness/score.

## PASSO 30

Docs + report final.

---

# 48. SUBAGENTES / JUÍZES RECOMENDADOS

O líder técnico pode usar em paralelo:

## Agente 1 — Upstream Browserbase Auditor

- lê skills/scripts;
- identifica capacidades e riscos;
- supply-chain/license.

## Agente 2 — Portal Runtime Architect

- compara com 073/075;
- procura duplicação;
- provider/network policy.

## Agente 3 — Trace/API Engineer

- DeepTrace;
- bodies;
- API infer;
- drift.

## Agente 4 — Learning/QA Engineer

- AutoBrowse;
- UI Test;
- evals;
- mutation.

## Agente 5 — Security/Privacy Judge

- PII;
- secrets;
- third-party Browserbase;
- tenant isolation;
- provider failover.

## Juiz Crítico

Tenta provar que:

- estamos duplicando 075;
- Browserbase virou dependência desnecessária;
- AutoBrowse pode autoeditar produção;
- trace pode vazar dados;
- remote provider pode duplicar side effect.

Líder consolida UMA decisão.

---

# 49. PONTOS DE PARADA REAIS

Parar para Founder apenas se:

1. Browserbase Cloud produtivo exigir decisão de PII/compliance/custo;
2. arquitetura atual não permitir provider sem reescrever Portal Worker;
3. Tool Gateway não conseguir platform-only capability de modo seguro;
4. qualquer solução precisar dar shell/browser raw a tenant agent;
5. side effect real for necessário para provar um gate;
6. migration destrutiva for proposta;
7. cross-tenant for encontrado;
8. upstream license não permitir reutilização pretendida.

Não parar por:

- nome de classe;
- minor test failure local;
- warning;
- limpeza estética;
- formato de report;
- skill upstream que decidimos não adotar.

---

# 50. DEFINITION OF DONE

A SPEC-077 só está pronta quando:

## Arquitetura

- Browserbase Skills assimiladas sem segunda arquitetura;
- Work OS continua autoridade;
- Portal Worker continua único executor;
- business Skills continuam business Skills;
- Lab recipes não aparecem para tenant.

## Trace

- deep trace funciona passivamente;
- per-page/unified timeline funciona;
- PII protegida;
- profiler lightweight preservado.

## API

- browser-to-api candidate pipeline funcional;
- contract confidence;
- coverage gaps;
- drift detector;
- approved endpoints separados de candidates.

## Learning

- AutoBrowse-style loop funciona em task segura;
- candidate strategy melhora ou reverte;
- não autoedita produção.

## QA

- adversarial harness encontra bug plantado;
- assertions/evidence;
- parallel agents controlados.

## Safety

- network policy;
- no raw CDP para agent;
- no provider-switch after unknown transaction;
- no cross-tenant;
- no secret leakage.

## Browserbase Remote

Pode terminar em `lab_only` e ainda considerar a SPEC concluída.

O importante é que a arquitetura suporte o provider sem depender dele.

## Regressão

- Cobrança verde;
- Vidros verde;
- local Playwright verde;
- remote OFF = comportamento atual.

---

# 51. MÉTRICA ESTRATÉGICA

O sucesso desta SPEC não é “instalamos Browserbase Skills”.

É:

> **quanto menos trabalho humano e menos código artesanal passa a ser necessário para descobrir, construir, testar, reparar e evoluir uma nova capacidade de portal com segurança?**

Medir:

- tempo Founder em F12;
- número de capturas manuais;
- tempo até API candidate;
- tempo até fixture;
- tempo até journey;
- regressões escapadas;
- tempo de reparo após drift;
- success rate.

Meta sugerida:

reduzir onboarding/repair effort em pelo menos 50% no primeiro ciclo comparável, sem aumentar incidentes.

---

# 52. RELATÓRIO FINAL OBRIGATÓRIO

`docs/canon/reports/SPEC-077-EXECUTION-REPORT.md`

Deve conter:

## Git

- base;
- branch;
- commits;
- diff.

## Upstream

- Browserbase commit auditado;
- files/skills assimiladas;
- itens rejeitados;
- license notes.

## Architecture

- final diagram;
- owners/authorities;
- no-duplicate proof.

## Trace

- run evidence;
- PII evidence;
- timing.

## API infer

- candidate contract;
- confidence;
- coverage gaps;
- drift test.

## Learning

- iterations;
- hypothesis table;
- before/after;
- graduation result.

## QA

- test counts;
- pass/fail/skip;
- bug planted/found.

## Security

- host policy;
- secrets;
- tenant;
- provider failover.

## Browserbase

- lab status;
- benchmark;
- cost;
- recommendation:
  - lab_only;
  - readonly_fallback;
  - production_candidate;
  - reject.

## Regression

- Cobrança;
- Vidros;
- Work OS.

## Mutations

- mutation kill matrix.

## Pendências

Somente dependências reais.

---

# 53. COMANDO FINAL AO CLAUDE/EXECUTOR

Você não está sendo contratado para “instalar um plugin”.

Sua missão é transformar o máximo valor comprovado do Browserbase Skills em infraestrutura nativa do AutoBrokers, preservando as autoridades já construídas.

Antes de codar:

AUDITE.

Se encontrar duplicação:

REUSE.

Se encontrar ideia melhor:

MELHORE tecnicamente.

Se a melhoria mudar autoridade, segurança, produto ou uso de terceiro com PII:

PARE para Founder.

Depois:

EXECUTE EM LINHA RETA.

Use subagentes e juiz crítico.

Não fragmente em dezenas de microaprovações.

Não transforme Browserbase em novo runtime.

Não dê browser cru aos agentes.

Não deixe AutoBrowse autoeditar produção.

Não trate API inferida como oficial.

Não vaze HAR/cookie/token/PII.

Não quebre Cobrança.

Não quebre Vidros.

O resultado desejado é:

```text
AutoBrokers Portal Worker
+ Portal Capability Factory
+ Portal Intelligence Lab
+ Deep Trace
+ Browser-to-API
+ Auto-improvement supervision
+ Adversarial QA
+ Network confinement
+ Optional Browserbase Remote
=
portal automation cada vez mais rápida de construir,
mais fácil de diagnosticar,
mais resistente a drift,
mais segura,
e reutilizável por todos os agentes e auxiliares
sem dar poder irrestrito a nenhum deles.
```

**QUALIDADE-ALVO:** 100/100 em rigor de engenharia, com fatos medidos e limites honestos.  
**VELOCIDADE:** executar a SPEC inteira em uma leva sempre que possível.  
**NO MÁXIMO:** dois macroblocos se contexto/qualidade realmente exigir.  
**NÃO INICIAR outra SPEC automaticamente ao concluir.**
