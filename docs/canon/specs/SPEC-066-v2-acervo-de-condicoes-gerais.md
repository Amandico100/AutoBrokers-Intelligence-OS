---
> **Status:** canônica · executável por lotes
> **Versão:** 2.0 · **Criada em:** 08/08/2026 · **Substitui:** SPEC-066 v1.0 (01/08/2026)
> **Autoridade superior:** CLAUDE.md · SPEC-052 · SPEC-056
> **Branch:** `feat/spec066-condicoes-gerais`
---

# SPEC-066 v2 — O acervo de condições gerais

> **A frase que resume:** o agente não mente sobre cobertura — ele **cala**. E
> cala porque 📊 **375 de 379 respostas (98,9%) foram produzidas com zero
> trechos do RAG**. Esta SPEC enche esse silêncio com o contrato oficial, em
> lotes que se disparam um por vez.

**O que mudou da v1:** a v1 apostava no acervo estatístico da SUSEP (SES, 542
MB) e num gatilho que o código bloqueia. A v2 corta o SES, mede o gatilho, e
troca a fonte primária. Tudo abaixo foi medido em 07-08/08/2026.

---

## 1. A prova de que isto é necessário

📊 Perguntas **literais** de segurados, colhidas de `attendance_transcripts`:

| # | O que o segurado perguntou | quando |
|---|---|---|
| 1 | *"O seguro cobre pneu e rodas?"* → *"A roda como não cobre o seguro vou ver o que faço"* | 07/08 |
| 2 | *"qual o limite de acionamentos da assistência de linha branca no residencial da Allianz?"* — **repetida 2× na mesma conversa** | 28/07 |
| 3 | *"na assistência básica auto da Yelum tem assistência pra casa, tipo encanador?"* — **repetida 13:38 e 13:53** | 16/07 |
| 4 | *"qual o prazo q tenho para acionar o seguro?"* | 15/07 |
| 5 | *"Quais documentos precisamos mandar para o reembolso do vidro?"* | 15/07 |
| 6 | *"É sobre carro reserva, aqui na apólice diz 35 dias??"* | 24/07 |
| 7 | *"Minha televisão parou de funcionar / É coberto também?"* | 17/07 |
| 8 | *"o seguro dos equipamentos cobre a troca do parabrisa?"* (3 retroescavadeiras) | 24/07 |
| 9 | *"Preciso saber se tenho cobertura pra encanador"* → o agente pede CPF e **nunca conclui** | 15/07 |
| 10 | *"TRAGA A FRANQUIA DELA"* → *"A fonte não retornou franquia estruturada — não vou estimar valor sem evidência."* | 03/07 |

**A pergunta 3 não tinha como ser respondida: não existe um único documento da
Yelum no RAG.** E a Yelum tem corredor auto E residencial ativo nas duas
corretoras.

📊 **4 das 10 seguradoras com corredor AUTO ativo têm ZERO condições gerais:**
`yelum` · `hdi` · `zurich` · `alfa`.

**O prompt está certo** (`prompts.py:201` — *"NUNCA confirme cobertura sem
evidência da apólice"*). O agente não inventa. Falta o documento.

---

## 2. Os cinco bloqueios técnicos — e nenhum é a fonte

Todos medidos. Nenhum depende de terceiro.

### 🔴 B1 — O gatilho está bloqueado em dois pontos independentes

A v1 pressupunha *"a apólice traz o número de processo SUSEP"*. Ela mesma
deixou o item **desmarcado**. Medido:

- 📊 `infocap_connector.py` — 4.253 linhas, **zero ocorrências de `susep`**. O
  sanitizador monta dicionário fechado sem campo de processo.
- 🔴 `policy_document_evidence_service.py:168` — `_BOILERPLATE_RE` descarta
  **toda linha que contém "susep"** como ruído institucional. Mesmo que o
  número esteja impresso na apólice, **o extrator o elimina por desenho.**

⚠️ **Armadilha de nome:** `billing_sent_log.apolice_susep` existe e tem 4
linhas preenchidas — 📊 **nenhuma no formato de processo**. É alias de
`numero_apolice` (`billing_collection.py:195`). Nome que mente sobre o conteúdo
(CLAUDE.md §12.1).

### 🔴 B2 — Vigência não tem escritor

📊 `effective_until` e `version_label`: aparecem só em `SELECT` e como
parâmetro opcional. **Nada nunca as calcula.** NULL em 35 de 35 linhas.
`effective_from` é extraído por regex e falhou em **10 de 29**.

### 🔴 B3 — O índice guarda uma versão só, por desenho

📊 `insurance_corpus.py:242-245` — `delete_document(doc_id)` com
`doc_id = f"norm-{id}"`, **o mesmo id para todas as versões**. A versão nova
apaga a anterior do Qdrant.

📊 `normative_document_versions`: 29 linhas, `version` mínima 1 e máxima 1,
`superseded_at` preenchido em **zero**. O encadeamento nunca rodou.

### 🔴 B4 — A busca não filtra por data

📊 `qdrant_service.py:355-389` filtra seguradora e nada mais. `effective_from`
só aparece como texto de exibição.

> **B2 + B3 + B4 somados:** a pergunta *"qual versão valia quando esta apólice
> foi emitida?"* **não é respondível em nenhuma das três camadas** —
> armazenamento, índice e recuperação. É o maior item de trabalho desta SPEC.

### 🔴 B5 — O worker pula o corpus sem Firecrawl, e não precisa dele

📊 `smith_worker.py:213-240` — o portão `if not configurado(): return` está
**antes** de `reconferir_pendentes`. Mas `_baixar_pdf_direto` usa httpx, não
Firecrawl. **Os PDFs da SUSEP são GET direto e o worker não os processa** se a
chave não estiver nele.

---

## 3. A decisão de fonte — e o conflito que ela cria

📊 Medido em 08/08/2026:

```
site da seguradora    Bradesco HTTP 408 e 500 · Yelum exige CPF + nº de apólice
                      Tokio 403 sem User-Agent de navegador · HDI 500 (morto)
repositório SUSEP     200 · 1,08 s · sem autenticação · TODAS as versões com data
```

**A SUSEP passa a ser a fonte primária.** O site da seguradora vira conferência.

⚠️ **Conflito canônico registrado:**
`docs/canon/CURADORIA-POR-SUBAGENTES.md:161-166` fixa *"1. Site oficial da
seguradora · 2. SUSEP"*. A medição inverte. **Esta SPEC inverte a ordem e
registra o motivo**; se o Founder discordar, decide e o texto muda.

### O que NÃO entra, e por quê

| descartado | motivo medido |
|---|---|
| **SES / sinistralidade** (542 MB) | responde **zero** perguntas de segurado. É ativo de mesa de negociação — SPEC-065/067, outro produto |
| Ranking de reclamações | 📊 a própria SUSEP declara os dados **congelados** no 4º tri/2025 |
| Registro de corretores | 📊 SPA que exige JS; API pede JWT. E o agente fala com **segurados** |
| Varredura em massa | 📊 impossível: um campo só, `ConsultarPorSociedade` dá 404. Não há enumeração |

---

## 4. Trecho ou carta? — o projeto já decidiu: **os dois**

Não invente terceira posição. `SPEC-066 v1:291` — *"o mesmo caminho serve para
condição geral: muda a fonte, não o motor."*

| | **TRECHO CRU** | **CARTA DESTILADA** |
|---|---|---|
| o que é | o PDF picado em 1000 chars | uma frase, um fato |
| para que | citar o contrato **com fidelidade legal** | o agente responder rápido |
| quem faz | script, **sem LLM** | subagente **Opus 5** |
| por que existe | *"aqui está o texto para o pedido de reanálise"* | *"uma carta = uma ideia completa"* |
| autoridade | D17 (Founder): consistência — o mesmo PDF lido em dias diferentes não pode dar respostas diferentes | a carta é o chunk do RAG |

**A trava da carta de condição geral** (v1, Bloco B, vira teste obrigatório):

> Carta que fixa **percentual, valor ou prazo que varia por apólice NÃO ENTRA.**
> A carta ensina **onde verificar**.

O que se destila: exclusões · carências · forma da franquia (não o valor) ·
documentos exigidos · prazos previstos em norma.

---

## 5. Que modelo usa cada etapa

| etapa | modelo | por quê |
|---|---|---|
| baixar, picar, indexar o PDF | **nenhum** | é script. Zero julgamento, zero custo |
| escrever carta de condição geral | **Opus 5** | separar "o que o contrato diz" de "o que varia por apólice" é julgamento fino, e errar aqui faz o agente mentir com autoridade de documento |
| conferir lote antes de aplicar | **script** (`validar.py`) | vocabulário, PII, cobertura |

**Tudo pelo plano Max. Custo de API: zero.** O único custo é embedding —
📊 US$ 0,029 por 12.000 chunks.

---

## 6. OS LOTES

Critério de ordenação, explícito: **cartas de cobertura** (sinistro +
assistência + apólice), porque é onde a condição geral responde. Cobrança é
ruído — boleto não está no contrato. Desempate por **sessões observadas** e por
**ter corredor ativo**.

### 📦 LOTE 1 — Yelum e HDI · *o que não existe e é mais pedido*

📊 302 cartas de cobertura somadas · corredor auto **e** residencial ·
aparecem nas **duas** corretoras · **zero** condições gerais hoje.

| seguradora | ramo | processo SUSEP | versões | vigente |
|---|---|---|---|---|
| yelum | auto | `15414.100331/2004-96` | 54 | 30/04/2026 |
| yelum | carta verde | `15414.100428/2004-07` | — | — |
| yelum | residencial | **a descobrir** | — | — |
| hdi | RCF | `15414.900886/2016-74` | 35 | — |
| hdi | residencial | `15414.002160/2005-11` | 18 | — |
| hdi | auto/casco | **não achado** — o antigo `15414.001197/2004-41` não retorna | | |

> **É o lote que justifica a campanha.** O site da Yelum exige CPF e número de
> apólice; o repositório da SUSEP entrega sem porteiro.

💭 Duração estimada: 2-3 horas (6-8 documentos).

### 📦 LOTE 2 — Atualizar Allianz e Porto · *o que temos e está vencido*

📊 São as duas maiores em cartas (638 e 379) e **14 de 15 documentos do acervo
estão em versão vencida**.

| documento | nossa versão | vigente | versões |
|---|---|---|---|
| **Porto Condomínio** | **2012** | 11/12/2025 | 26 |
| Porto Auto | 01/01/2026 | 01/07/2026 | 100 |
| Porto Empresa | 11/04/2025 | 31/07/2026 | 25 |
| Allianz Auto | 10/12/2025 | 22/07/2026 | 72 |
| Allianz Residencial | 01/12/2025 | 18/06/2026 | 30 |
| Allianz Vida | 16/12/2025 | 15/07/2026 | 11 |
| Porto Residência | 05/12/2025 | ✅ em dia | 36 |

> Um contrato de **2012** respondendo sobre um condomínio de 2026 **erra com a
> autoridade de documento oficial**. É pior que não ter.

💭 Duração: 2-3 horas.

### 📦 LOTE 3 — Destravar o que é bug nosso

📊 Quatro das cinco ingestões travadas **têm URL viva**. Não é fonte morta.

| o que | conserto |
|---|---|
| Tokio (403) | mandar **User-Agent de navegador** no fetcher |
| Bradesco Auto (5,7 MB) | subir teto de tamanho/timeout |
| Tokio: processos gravados **truncados** | corrigir `15414.100335/2004` → `-74`; 50 versões esperando |
| Porto auto: `15414.100.233/2004-59` | ponto a mais — regex `_RE_PROCESSO_SOLTO` aceita qualquer coisa |
| 4 documentos nunca aprovados | `aprovar()` — `vencidos()` não os enxerga |

💭 Duração: 1-2 horas. **É o lote mais barato por documento entregue.**

### 📦 LOTE 4 — Zurich e Alfa

📊 Zurich 21 cartas de cobertura, Alfa 17 — corredor auto ativo, zero CG.
Zurich residencial `15414.003106/2009-17` (6 versões) · Alfa auto
`15414.100446/2004-81` (21 versões). A Alfa tem índice público com histórico.

💭 Duração: 1-2 horas.

### 📦 LOTE 5 — Normas que valem para todas

Circular SUSEP **621/2021** (`bnmapi.exe?router=upload/26980` — 📊 200,
90.170 B): prazo de **30 dias** para pagar sinistro após entrega dos
documentos; aviso de não renovação com 30 dias de antecedência.

> Toca a categoria `sinistro` inteira — 📊 **5.205 cartas**. É a resposta para
> *"mandei tudo faz 40 dias e não pagaram"*, e o prazo é **da norma**, não da
> apólice: vale para todas as seguradoras.

💭 Duração: 30 minutos. **Melhor razão valor/esforço da SPEC.**

### 📦 LOTE 6 — Sura e o que sobrar

Sura auto `15414.001554/2004-71` (20 versões). Baixa prioridade: 8 cartas de
cobertura, sem corredor.

### ⛔ O que fica FORA, e é decisão registrada

| fora | 📊 por quê |
|---|---|
| **Youse** | 139 cartas, mas **100 são de cobrança e 15 de cobertura**. Contrato não explica boleto |
| **Itaú** (1 carta) · **Sompo** (8) | os dois **saíram do auto massificado**. A Sompo vendeu o varejo à HDI em 2023; o Itaú hoje vende Porto |
| **Suhai** | 📊 **zero** cartas de cobertura |

---

## 7. O processo de um lote — passo a passo

```
1. DESCOBRIR   o número de processo (§8) · script + conferência humana
2. CONSULTAR   POST Produto.aspx/Consultar → lista de versões com data
3. ESCOLHER    a VIGENTE, e registrar as anteriores (não baixar todas)
4. BAIXAR      GET DownloadConsultaPublica/{id} → PDF
5. REGISTRAR   normative_documents com susep_process, effective_from e
               effective_until (B2 precisa existir antes deste passo)
6. INGERIR     motor existente: httpx → PyPDF2 → chunks de 1000/200 →
               embedding denso + esparso → payload com insurer_key na RAIZ
7. DESTILAR    subagentes Opus 5 leem os chunks e escrevem CARTAS
8. VALIDAR     validar.py — vocabulário, PII, cobertura
9. APLICAR     aplicar.py com a marca do lote
```

**Passos 1-6: sem LLM.** Passo 7: Opus 5, plano Max.

⚠️ **Reusar o motor.** A v1 §5 proíbe *"segundo pipeline de ingestão ao lado do
que existe"*. O motor atual é bom: GET direto primeiro (Firecrawl só como 2ª
opção), teto de 60 MB, mínimo de 400 chars (barra PDF escaneado), hash com
espaço normalizado (PDF re-renderizado não conta como mudança), e cabeçalho de
procedência inserido no texto.

---

## 8. De onde sai o número de processo

📊 Testados seis caminhos. **Um funciona hoje**, e um segundo é o que destrava
a escala:

| caminho | estado |
|---|---|
| Site da seguradora → PDF → regex | ✅ **é como os 28 atuais foram obtidos** |
| **PDF da apólice → regex** | 🟡 **destrava tudo** — exige remover `susep` do `_BOILERPLATE_RE` (B1) |
| InfoCap (JSON) | ❌ campo não existe |
| InfoCap (record cru) | ❓ **não medido** — exige chamar a API |
| CG que já temos | ❌ circular |
| Busca por seguradora na SUSEP | ❌ 404 |

> **A medição nº 1 desta SPEC:** verificar se o número está impresso nos 8 PDFs
> de apólice que temos. Ela decide se o gatilho vira automático ou continua
> manual. 📊 Não foi possível medir daqui — o texto mora no Qdrant/MinIO e
> `documents` não tem coluna de texto.

---

## 9. Qualidade — como se garante 100/100

| trava | o que faz |
|---|---|
| **Só a versão vigente entra no índice** | com `effective_from` e `effective_until` preenchidos (B2) |
| **A carta não fixa número que varia** | percentual, valor e prazo por apólice ficam de fora; a carta ensina onde ver |
| **Nenhum dado pessoal** | `templatize` — o PDF é público, mas exemplos dentro dele podem não ser |
| **Amostra de 20 antes da leva** | lidas **com os olhos**, com um trecho fora de escopo como **controle** |
| **Sem lastro, não escreve** | trecho que não sustenta a afirmação = carta não nasce |
| **Cita o documento e a versão** | toda carta de CG carrega de qual documento e de que vigência saiu |

### A flag que precisa existir

📊 `conversation_auditor.py` tem 5 flags e **nenhuma mede falta de condições
gerais**. `capability_gaps` está **vazia** e só registra falta de ferramenta.

> **Sem essa flag, a campanha não tem como provar que melhorou nada** — e
> CLAUDE.md §9.2 exige linha de controle. Criar a flag é pré-requisito do
> LOTE 1.

### ⚠️ Medir antes de creditar

📊 Os limites de assistência da Porto (guincho 400 km, chave reserva 100 km)
**já estão** na CG140 indexada. Se o agente não os acha, o problema é **busca**,
não acervo — e nenhum documento novo conserta isso.

📊 Agravante: o **reranker Cohere está desligado**; sem ele os 3 trechos que
chegam ao modelo saem de um RRF de duas buscas não comparáveis.

**Antes do LOTE 1: fazer 5 perguntas de cobertura da Porto ao agente e ver se o
trecho certo aparece.** Se não aparecer, o primeiro conserto é de recuperação.

---

## 10. Como disparar um lote

O Founder manda uma frase:

```
Executar o LOTE N da SPEC-066 v2.
```

E a liderança:
1. lê o lote nesta SPEC
2. confere as pré-condições (§9)
3. roda os passos 1-6 (script)
4. dispara os subagentes Opus 5 do passo 7
5. valida, aplica, e mede o antes/depois com a flag de §9

**Um lote por vez. Cada um fecha sozinho.** Nenhum depende do seguinte.

---

## 11. Ordem recomendada

```
LOTE 5   normas gerais       30 min    ← melhor razão valor/esforço
LOTE 3   destravar bugs      1-2 h     ← mais barato por documento
LOTE 1   Yelum e HDI         2-3 h     ← o que mais falta
LOTE 2   atualizar vencidos  2-3 h     ← o de 2012 sai do ar
LOTE 4   Zurich e Alfa       1-2 h
LOTE 6   Sura                30 min
```

**Antes de qualquer lote:** B2 (vigência tem escritor) e a flag de §9.
**Sem B2, o LOTE 2 grava versão nova apagando a anterior** (B3) — e o acervo
perde a capacidade de responder pela apólice antiga, que é a razão de existir
desta SPEC.
