# SPEC-077 — Auditoria antes de codar

**16/08/2026** · base `daeda65` (SPEC-075 concluída e no ar) · auditoria pedida pela própria SPEC-077 §4

---

# 0. Veredito

**READY — com três mudanças materiais na SPEC.**

A tese central da SPEC-077 está **certa e é o gargalo real**: hoje descobrir um portal custa o Founder no F12. A [SPEC-076](../specs/SPEC-076-vidros-do-pedido-ao-acompanhamento.md) §3 é literalmente um protocolo de captura manual — três ajustes de DevTools, HAR, `Ctrl+S`, prints, e uma volta ao portal dias depois.

Mas a auditoria encontrou **três fatos que a SPEC não conhecia**, e os três mudam o que deve ser construído:

| # | Fato medido | Consequência |
|---|---|---|
| 1 | O `browse` CLI — do qual **5 das 8 skills dependem** — tem o código-fonte **inacessível** (404 nos dois repositórios que ele próprio declara) | Não pode virar dependência de runtime. Nem de laboratório com dado real |
| 2 | O **Playwright que já usamos** tem CDP nativo (`new_cdp_session`) e interceptação (`context.route`) | Não precisamos do `browse` CLI **para nada**. O DeepTrace e a network policy saem de graça |
| 3 | Temos **142 MB de HAR de 6 seguradoras** parados no `docs/intake/`, com **223 respostas JSON** | O `browser-to-api` pode entregar valor **esta semana**, sem DeepTrace, sem Browserbase, sem CLI |

A conclusão que reorganiza a SPEC: **a 077 não é uma integração com Browserbase.** É a reimplementação, em Python, de **dois algoritmos MIT** que já podemos alimentar com dado que já temos.

O nome da SPEC atrapalha. Ele sugere uma dependência que a auditoria mostra ser desnecessária.

---

# 1. O upstream, medido

## 1.1 Estado e licença

📊 `main` em `6afe866`, de 09/07/2026 — **não avançou** desde a autoria da SPEC. 65 commits, 3.694 stars.

**Licença: MIT, por skill.** A raiz do repositório não tem `LICENSE` (a API do GitHub devolve `license: null`), mas **cada skill tem o seu** `skills/<nome>/LICENSE.txt` = MIT, "Copyright (c) 2026 Browserbase, Inc.", e cada `SKILL.md` traz `license: MIT` no frontmatter.

✅ **Podemos copiar e adaptar o código das 8 skills**, preservando o aviso de copyright. O que fica sem licença é só o invólucro (`README`, `package.json`, `scripts/`) — nada disso é conteúdo aproveitável.

## 1.2 Código vs prompt — a distinção que a SPEC não fez

| Skill | O que é, de fato | Depende de |
|---|---|---|
| `browser-to-api` | **7 mil linhas de Node, stdlib pura, offline** | **nada** |
| `browser-trace` | 7 `.mjs`, mas **não abre websocket** — faz `spawn('browse', ['cdp', ...])` | `browse` CLI |
| `autobrowse` | 3 `.mjs` grandes | `browse` CLI + `ANTHROPIC_API_KEY` + Stagehand |
| `webmcp-gen` | 4 `.mjs` | **Stagehand** + Chrome com flags |
| `safe-browser` | receita + demo de 15 KB | Claude Agent SDK |
| `ui-test` | **markdown puro**, 29 KB | `browse` CLI |
| `browser` | **markdown puro** — é o manual do CLI | `browse` CLI |
| `functions` | **markdown puro** | produto **pago** Browserbase |

🔴 **Três das oito não têm uma linha de código.** São prompts — bem escritos, mas prompts. "Assimilar" `ui-test` significa **adotar a disciplina**, não importar nada.

## 1.3 O problema do `browse` CLI

`browse@0.9.6` no npm, MIT declarado. Mas:

- `package.json` aponta `repository` para `github.com/browserbase/stagehand` → `packages/cli` → **404**
- o ponteiro anterior, `github.com/browserbase/cli` → **404**
- `packages/` do Stagehand contém `docs, evals, extension, integrations, protocol, sdk-go, sdk-python, sdk-ts` — **não há `cli`**

🔴 **O código que faz o trabalho não é auditável.** E não é periférico: é ele que abre o CDP (`browse cdp`) e captura os corpos de resposta (`browse network on`). As duas capacidades que mais nos interessam moram exatamente no que não dá para ler.

Para um sistema que navega portal de seguradora com credencial de corretora e PII de segurado, executar um binário de origem não auditável é risco que não se compensa com conveniência — ainda mais quando **não precisamos dele**.

## 1.4 O que aprendi lendo o upstream, e vale ouro

Três frases do `browser-trace/REFERENCE.md` que valem a auditoria inteira:

> *"CDP allows multiple concurrent clients on the same target."*

É a permissão técnica para o observador passivo. **Playwright expõe isso nativamente** — `context.new_cdp_session(page)`.

> *"`browse cdp` does not embed response bodies in the firehose — that requires a synchronous `Network.getResponseBody` round-trip per request."*

📊 Isto responde a pergunta que a SPEC-077 §10 deixa em aberto e que eu teria descoberto do jeito caro: **o firehose de eventos NÃO traz corpos**. Cada corpo exige uma chamada síncrona. Isso muda o desenho do DeepTrace — captura de corpo é cara, tem de ser seletiva por allowlist, e não pode ser "ligue e veja".

> O join entre evento e corpo é por `requestId`, **"not URL or timestamp"**.

Detalhe de implementação que teria custado uma tarde de depuração.

---

# 2. O que as SPECs 073–075 já construíram

O auditor interno percorreu o código. Resultado, por proposta da 077:

| Proposta da 077 | Veredito | Onde já vive |
|---|---|---|
| Redaction canônico + envelope | ✅ **JÁ EXISTE** | `redaction.py`, `redigir_envelope()` |
| Detector de PII para fixture (mod-11 real) | ✅ **JÁ EXISTE** | `replay.py` §B |
| Manifesto de fixture + replay + `EfeitoNaoPrevisto` | ✅ **JÁ EXISTE** | `replay.py` §A/§C |
| Effect class + fases de checkpoint + guard | ✅ **JÁ EXISTE** | `guardrails.py` |
| Idempotência / `maybe_committed` | ✅ **JÁ EXISTE** | `guardrails.py` |
| Score, blockers, estados de release | ✅ **JÁ EXISTE — e excede o §25** | `prontidao.py` |
| Escada de percepção + visão | ✅ **JÁ EXISTE** | `perception.py` |
| Portal Factory CLI | 🟡 **CLI certo, comandos `lab` ausentes** | `portal_factory.py` |
| Host allowlist aplicada | 🟡 **Só no Maxpar** | `vidros_api.py` |
| Profiler (base do DeepTrace) | 🟡 **3 eventos, sem corpo, sem console** | `profiler.py` |
| Injeção de erro no replay | ❌ **NÃO EXISTE** | — |
| Browser provider abstraction | ❌ **NÃO EXISTE** | — |
| Network policy genérica | ❌ **NÃO EXISTE** | — |
| Métricas agregadas | ❌ **NÃO EXISTE** | — |

📊 Verificado por mim, não só pelo auditor:

```
page.on(...) no profiler   →  3 listeners (response, requestfailed, framenavigated)
console/pageerror          →  ninguém escuta (só um ad-hoc na Allianz)
CDP no repositório inteiro →  ZERO usos
```

**A 077 escrita como está duplicaria sete capacidades.** Ela foi escrita antes de a 075 existir; não é erro do autor, é o custo de escrever contra um alvo em movimento.

---

# 3. As três mudanças materiais que eu proponho

## 3.1 🔴 Cortar o `browse` CLI inteiro — e com ele, meia SPEC

**O que a SPEC diz:** adotar `browser-trace`, `ui-test`, `browser`, `autobrowse` — todas dependentes do CLI.

**O que eu proponho:** zero dependência do `browse`. Nunca, nem no laboratório.

**Por quê:** fonte não auditável (§1.3), e **não precisamos**:

| Precisamos de | O CLI dá | O Playwright já dá |
|---|---|---|
| CDP passivo | `browse cdp` | `context.new_cdp_session(page)` ✅ |
| corpos de resposta | `browse network on` | `cdp.send("Network.getResponseBody", {"requestId": …})` ✅ |
| allowlist com bloqueio | `Fetch.failRequest` | `context.route()` ✅ |
| console/exceções | `browse cdp` | `page.on("console")`, `page.on("pageerror")` ✅ |

📊 Confirmado na nossa instalação: `BrowserContext.new_cdp_session`, `context.route`, `page.route` e `CDPSession.send` **todos presentes**.

**Consequência:** some o Bloco A inteiro (upstream lock, supply-chain), some a dependência de Node no runtime, e some o risco. O que sobra do upstream é **conhecimento sob MIT** — que se lê e se reimplementa.

## 3.2 🔴 Inverter a ordem: `browser-to-api` primeiro, alimentado por HAR

**O que a SPEC diz:** DeepTrace (Bloco C) → captura de corpo (D) → API infer (E).

**O que eu proponho:** **API infer primeiro**, comendo HAR. DeepTrace depois.

**Por quê — e este é o argumento mais forte da auditoria:**

📊 Já temos, parados em `docs/intake/MATERIAIS/`:

```
MAPFRE      574 entradas | 255 com corpo |  65 JSON | 29.2 MB
Maxpar/Porto 350 entradas | 164 com corpo |  28 JSON | 32.5 MB
Maxpar/Yelum 378 entradas | 139 com corpo |  45 JSON | 25.9 MB
Yelum       379 entradas | 323 com corpo |  45 JSON | 24.5 MB
Zurich      285 entradas | 257 com corpo |  20 JSON | 25.5 MB
Tokio       102 entradas |  49 com corpo |  20 JSON | 10.7 MB
                                          ───────
                                          223 respostas JSON, 6 seguradoras
```

Três coisas que isso destrava, e nenhuma delas precisa de DeepTrace:

**(a) Validação forte, hoje.** Eu minerei MAPFRE, Tokio, Yelum, Zurich e Maxpar **à mão**. Dá para perguntar ao inferidor: *"você acha o que eu achei?"*. Isso é um canário de 6 portais, não o de 1 que a SPEC §42 propõe.

**(b) Valor esta semana.** O Founder vai capturar 3 HARs novos da SPEC-076 nos próximos dias. Com o inferidor pronto, esses HARs viram contrato OpenAPI **automaticamente** — em vez de eu reler 58 MB com os olhos, como fiz na 074.

**(c) Ordem certa de risco.** `browser-to-api` é **offline puro, sem dependência, sem tocar em portal nenhum**. É a peça de maior valor e menor risco da SPEC inteira. Fazê-la por último é inverter a prioridade.

🔴 **Limitação que a SPEC não viu:** DeepTrace roda dentro do *nosso* worker. Na SPEC-076 quem navega é o **Founder**, no Chrome dele, com credencial dele e um cliente real — porque o robô ainda não completa o fluxo. **DeepTrace não ajuda a 076.** HAR-first ajuda.

## 3.3 🟠 Rebaixar AutoBrowse e Browserbase Remote para "não nesta SPEC"

**O que a SPEC diz:** AutoBrowse é bloco central (§13), Browserbase Remote é provider opcional (§17).

**O que eu proponho:** os dois saem do escopo executável e viram pendência com gatilho.

**AutoBrowse — por quê:**
- exige `ANTHROPIC_API_KEY` + `browse` CLI + scaffolds Stagehand
- o loop *"executa → lê trace → uma hipótese → repete"* é bom, mas **é o que eu já faço nesta conversa**, com subagentes e juízes críticos — e com julgamento humano no meio
- automatizá-lo antes de existir DeepTrace é construir o segundo andar sem o primeiro
- 📊 o valor marginal é baixo: o gargalo medido não é "iterar rápido", é **"descobrir o contrato"** — e isso é o `browser-to-api`

**Browserbase Remote — por quê:**
- 🔴 **não há um único portal medido que exija browser remoto.** O anti-bot da Allianz foi resolvido com `--headless=new` e User-Agent limpo (📊 medidas de 10 e 12/08). Zero evidência de necessidade
- construir `BrowserProvider` "para o caso de" é a definição de arquitetura especulativa
- envolve PII de segurado indo para terceiro, DPA, retenção, custo — decisão sua, não minha
- **a abstração custa pouco para adiar e muito para desfazer errada**

O que **fica** dos dois: a pendência escrita, com o gatilho nomeado. No dia em que um portal bloquear o Chromium local de verdade, a decisão terá evidência.

---

# 4. O que eu ACRESCENTO à SPEC

Quatro coisas que a 077 não previu e que a auditoria mostrou serem necessárias.

## 4.1 🔴 Injeção de erro no replay — a lacuna real do Bloco X

A 075 construiu replay maduro (manifesto, contagem de chamadas, `EfeitoNaoPrevisto`). Mas ele **só reproduz o que a fixture gravou**. Não há como injetar 401, 409, 429, timeout, JSON malformado, ordem de opções trocada.

Isso é o que o §30.2 pede, e é a **única** lacuna do Bloco X. É pequeno, é offline, e é o que dá dentes ao QA adversarial — sem ele, o `ui-test` testa só o caminho feliz da fixture.

## 4.2 🔴 Um `HarImporter` como cidadão de primeira classe

A SPEC trata HAR como formato de entrada legado. Deveria ser o **contrário**: HAR é o formato universal que o Founder já sabe produzir, que qualquer navegador exporta, e do qual temos 142 MB.

O `api-infer` deve ter **duas fontes** com o mesmo pipeline a jusante:

```
HAR (Founder, hoje)        ─┐
                            ├→ normalizador → inferidor → OpenAPI candidato
DeepTrace (robô, depois)   ─┘
```

## 4.3 🟡 A network policy deve nascer em `observe`, e usar `context.route`

A SPEC propõe `PortalNetworkPolicy` com três modos. Concordo — mas ela deve ser implementada com `context.route`, não com CDP `Fetch`, por três razões: é a API que já usamos, é async-safe no Playwright, e não exige um segundo cliente CDP disputando o `Fetch` domain com o DeepTrace.

E deve nascer em `observe` para **medir antes de bloquear**. 📊 O motivo é concreto: os 6 portais de corretor navegam por `page.goto()` para URLs fixas e nunca foram medidos quanto a domínios auxiliares (SSO, CDN, captcha). Ligar `strict` sem medir derruba journeys que funcionam.

## 4.4 🟢 Um teste de "o Founder trabalhou menos?" — a métrica que a SPEC pede e não define

A §51 diz *"reduzir onboarding/repair effort em pelo menos 50%"* mas não define como medir. Proponho a medida concreta, contra a 074 como baseline:

| Medida | 074 (à mão) | Meta 077 |
|---|---|---|
| endpoints descobertos | 34, por leitura minha de 58 MB | inferidor acha ≥ 30 dos 34 |
| tempo até o contrato | uma sessão inteira | minutos de CPU |
| coverage gaps apontados | por mim, depois do fato | pelo relatório, antes |

Isso é falseável. "50% menos esforço" não é.

---

# 5. Como fica a estrutura — hoje e depois

## Hoje

```
        VOCÊ, no F12
             │  Preserve log · HAR with content · Ctrl+S · prints
             ▼
      142 MB de HAR parados no docs/intake
             │
             │  ← EU LEIO COM OS OLHOS  (foi assim na 074)
             ▼
      journey escrita à mão
             │
             ▼
   Portal Worker → Playwright → portal
             │
     profiler leve (3 eventos, sem corpo, sem console)
```

## Depois da 077

```
        VOCÊ, no F12                    O ROBÔ, navegando
             │                                │
             ▼                                ▼
           HAR  ────────┐          ┌──── DeepTrace (CDP nativo)
                        │          │      network+console+DOM+screenshot
                        ▼          ▼      por página, timeline unificada
                   ┌──────────────────┐
                   │   normalizador   │
                   └────────┬─────────┘
                            ▼
                   ┌──────────────────┐
                   │  browser-to-api  │  offline, sem dependência
                   └────────┬─────────┘
                            ▼
              OpenAPI candidato + confiança + coverage gaps
                            │
                   ┌────────┴─────────┐
                   ▼                  ▼
            drift detector      adapter Python
              (portal              candidato
               mudou?)                │
                                      ▼
                            ┌──────────────────┐
                            │ replay + injeção │  401 409 429 timeout
                            │    de erro       │  ordem trocada, drift
                            └────────┬─────────┘
                                     ▼
                            QA adversarial (disciplina do ui-test)
                                     ▼
                            prontidao.py  (JÁ EXISTE)
                                     ▼
                            journey aprovada
```

**O que NÃO muda:** Work OS, Tool Gateway, PortalExecutionGateway, Portal Worker, guardrails, idempotência, escada de percepção. A 077 instala instrumentos **dentro** da fábrica da 075 — não constrói uma segunda.

**O que o Agente/Auxiliar ganha:** journeys que nascem mais rápido, com contrato conhecido, e que avisam quando o portal muda. **O que ele NÃO ganha:** browser, CDP, shell, chave de terceiro, ou permissão de inventar URL.

---

# 6. Escopo recomendado, reordenado por valor

| # | Bloco | Depende de | Valor | Risco |
|---|---|---|---|---|
| **1** | `HarImporter` + normalizador | nada | 🔴 alto | baixo |
| **2** | `api-infer`: OpenAPI candidato + confiança + coverage | 1 | 🔴 **o mais alto da SPEC** | baixo |
| **3** | Validação contra os 6 HARs que já temos | 2 | 🔴 alto (é a prova) | zero |
| **4** | Ciclo de vida do endpoint (`OBSERVED→…→APPROVED_MATERIAL`) | 2 | alto | baixo |
| **5** | Injeção de erro no replay | nada | alto | zero |
| **6** | DeepTrace com CDP nativo (sem CLI) | nada | alto | médio |
| **7** | Captura de corpo por allowlist + redação antes de persistir | 6 | alto | 🔴 **PII** |
| **8** | Drift detector (contrato aprovado × candidato novo) | 2, 4 | alto | baixo |
| **9** | `PortalNetworkPolicy` em `observe` | nada | médio | baixo |
| **10** | Comandos `lab` na Factory existente | 1–9 | médio | zero |
| **11** | QA adversarial (disciplina, não código importado) | 5 | médio | baixo |
| **12** | Métricas no `/health` | 6, 2 | baixo | zero |
| — | ~~AutoBrowse~~ | — | **pendência** | 🔴 alto |
| — | ~~Browserbase Remote~~ | — | **pendência** | 🔴 PII/custo |
| — | ~~webmcp-gen~~ | — | **rejeitado** | exige Stagehand |
| — | ~~`browse` CLI~~ | — | **rejeitado** | fonte não auditável |
| — | ~~Browserbase Functions~~ | — | **rejeitado** | segundo runtime |

---

# 7. O que a 075 deixou aberto, e se bloqueia a 077

**Não bloqueia nada.** Para o registro:

| Pendência | Bloqueia a 077? |
|---|---|
| P-196 migrations não aplicadas | ❌ não |
| P-197 ponte em `legacy` | ❌ não |
| P-198 Redis / concorrência 1 | ❌ não |
| P-199 allowlist nos 6 portais | 🟡 **a 077 §9 resolve isto** |
| P-200 Allianz sem fixture | 🟡 **o `api-infer` pode gerar a primeira** |
| P-201 18 mutações pendentes | ❌ não |

📊 Duas pendências da 075 são **resolvidas** por blocos da 077. Isso confirma a leitura do outro chat: as duas SPECs se complementam.

---

# 8. Pontos de parada — nenhum acionado hoje

A §49 lista 8 condições. Nenhuma se aplica ao escopo recomendado:

1. Browserbase produtivo → **fora do escopo**
2. arquitetura não permite provider → **provider adiado**
3. platform-only capability → usar a Factory CLI, e registrar o limite
4. shell/browser cru a agente → **jamais**
5. side effect real para provar gate → **nenhum bloco exige**
6. migration destrutiva → **nenhuma prevista**
7. cross-tenant → nenhum encontrado
8. licença → **MIT, resolvido**

🔴 **A única decisão que reservo para você** é a do Bloco 7 (captura de corpo de resposta). Corpo de resposta de portal de seguradora **contém PII de segurado** — CPF, apólice, endereço. O desenho que proponho nunca persiste bruto (`shape_only` por padrão, redação antes de gravar, `raw` só em memória), mas a decisão de capturar corpo em ambiente com dado real é sua, não minha. Se você preferir, o Bloco 7 roda **só sobre HAR que você já exportou** — e aí a decisão já foi tomada quando você clicou em exportar.

---

# 9. Resumo em uma tela

**O que a SPEC-077 acertou:** o gargalo é a descoberta manual de portal. `browser-to-api` é a peça de ouro. AutoBrowse não pode autoeditar produção. Browserbase não pode virar dependência. Skills de engenharia não são Skills de negócio.

**O que a auditoria corrigiu:**

1. o `browse` CLI é inauditável e **desnecessário** — o Playwright já faz tudo
2. `browser-to-api` deve vir **primeiro**, comendo os 142 MB de HAR que já temos
3. AutoBrowse e Browserbase Remote são especulativos hoje — viram pendência com gatilho
4. sete capacidades da SPEC **já existem** na 073/075 e seriam duplicadas
5. falta na SPEC: injeção de erro no replay, e HAR como entrada de primeira classe

**Veredito: READY.** Escopo recomendado: **12 blocos**, nenhuma dependência externa nova, nenhum runtime novo, nenhuma chave de terceiro, nenhum dado saindo de casa.

O nome que descreve o que isto realmente é:

> **Portal Intelligence Lab — descoberta de contrato a partir de tráfego observado.**

Browserbase é a fonte da ideia, sob MIT. Não é a dependência.
