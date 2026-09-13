# SPEC-EXTRA-001.5 — RESEARCH PACK

**Versão:** 1.0 · 13/09/2026. **Natureza:** evidência para conversão; não é relatório de execução.
**Baseline:** `a0bb5fe` (worktree `AutoBrokers-FIX`, 0 atrás e 0 à frente de `origin/main`).
**Método:** arquivos **reabertos hoje** e consultas **read-only** (SELECT e contagem) ao banco de produção pela
`SUPABASE_DB_URL` de `backend/.env`. Nenhum teste de produto executado, nenhuma mensagem enviada, nenhum portal
acessado, nenhuma escrita. **Nenhuma consulta retornou conteúdo de mensagem, nome, documento ou telefone.**
Leitura de código não é prova de funcionamento. 🔴 **O número do executor vence** (protocolo §5 ①).

---

## 1. Linhas conferidas hoje — as que a proposta cita

### 1.1 Camada de apólice e assistência

| ID | arquivo:linha | o que está lá |
|---|---|---|
| C01 | `backend/app/providers/policy_data_provider.py:41-52` | `class PolicyDataProvider(Protocol)` — só `provider_key`, `lookup(**kwargs) -> Dict`, `detail(**kwargs) -> Dict`. ⚠️ `vehicle` existe na implementação (`:112`) e **não** no Protocol |
| C02 | `policy_data_provider.py:55,58,137,144,149` | `InfocapPolicyDataProvider` (**única** implementação) · `register_policy_data_provider` · `get_policy_data_provider(provider_key="infocap")` · registro no import. Registry **em memória**, sem env, sem tabela |
| C04 | `backend/app/services/assistance_policy.py:28` | `STANDARD_SERVICES = ("eletricista","chaveiro","hidraulica_encanador")` — **141 linhas no arquivo inteiro**; nenhuma seguradora, produto ou nível; "carro reserva" **não aparece** |
| C05 | `assistance_policy.py:4-6` | *"migração para tabela `platform_policies` com overrides por seguradora/produto/plano/corretora está prevista para quando o primeiro override existir"* |
| C06 | `assistance_policy.py:47-58` | `_is_residential` — gatilho por **substring** `"resid"` (`:54`) / token `"resi"` (`:56`) |
| C07 | `assistance_policy.py:123` | `locator_hash = None` fixo em `policy_rule_facts` — o fato de regra **perde o vínculo com a apólice** |
| C08 | `backend/app/services/policy_answer_composer.py:24` | **único** importador de `assistance_policy` em produção |
| C09 | `backend/app/agents/nodes.py:307-317` | o guarda anula a resposta final se `assistance_policy_applied` está no contrato e o texto não contém "eletricista" **e** "chaveiro" **e** ("hidraulica"\|"hidráulica"\|"encanador") |
| C10 | `nodes.py:297-303` | o guarda **já** rejeita página citada que não está no texto determinístico — o padrão que M-A3 copia |
| C11 | `policy_document_evidence_service.py:204-209` | `_BOILERPLATE_RE` contém **`susep`** — ⚠️ **mas veja C11b antes de concluir que isso bloqueia o elo** |
| **C11b** | `policy_document_evidence_service.py:238` (`is_boilerplate_fragment`), usado só em `:278`, `:291`, `:307`, `:340` e `policy_facts.py:163` | 🔴 **o filtro governa apenas FRAGMENTOS de evidência.** O **texto integral** (`build_document_plain_text:163`, entregue em `:781` como `document_text`) **não passa por ele** — e `extrair_susep` opera sobre texto. **A ponte não está demolida por um filtro**; falta o consumidor |
| **C11c** | `backend/app/services/corridor_playbooks.py:8225` | `normalize_insurer_key(insurer, para="corredor"\|"conhecimento")` — **a chave canônica EXISTE**. `_INSURER_ALIASES` (`:8155`) trata `tokio`/`tokio marine`/`tokio_marine`/`tokyo`; `_OPERADO_POR` (`:8214`, `{"itau":"porto"}`) só é aplicado com `para="corredor"`; o docstring `:8226-8231` explica por quê: *"uma carta do Itaú fica sob Itaú, senão o agente responde regra da Porto a segurado do Itaú"*. 📊 **14 chamadores** (25 ocorrências com definição e testes) |
| **C11d** | `backend/app/agents/tools/portal_params.py:90` | `normalize_insurer` — o nome **como o PORTAL conhece**. É outra coisa, e **não serve** para a chave de conhecimento |
| C12 | `policy_document_evidence_service.py:230-318` | `_ASSISTANCE_HEADER_RE = assist[êe]ncia\s*24\s*h`; emite `kind="assistance_plan"` (`:286`) e `kind="assistance_services"` (`:302`); `_SERVICE_TERM_RE` (`:231-235`) inclui `guincho` |
| C13 | `policy_document_evidence_service.py:387-407` | `_base_item` grava `page_number` e `chunk_id="{doc}:p{n}:{i}"` — **o caminho da apólice TEM página** |
| C14 | `policy_document_evidence_service.py:539-549` | 🔴 o fallback docling devolve **uma única página, `page_number: 1`**, com o markdown inteiro dentro |
| C15 | `backend/app/api/infocap_connector.py:3955,3973,4015,4017` | `tabela_itens` vira só o sinal `unknown_table_field_present` + a limitação *"sem semantica comprovada para cobertura"*; e é um dos gatilhos de `document_evidence_required` |

### 1.2 Corpus normativo — o pipeline que se reusa

| ID | arquivo:linha | o que está lá |
|---|---|---|
| C21 | `backend/app/services/knowledge/insurance_corpus.py:49` | `_RE_SUSEP = r"\b(\d{5}\.\d{6}/\d{4}-\d{2})\b"` |
| C22 | `insurance_corpus.py:65` | `def extrair_susep(texto) -> Optional[str]` — **o extrator EXISTE** |
| C23 | `insurance_corpus.py:58-62` | `_hash` — SHA-256 com espaço normalizado, **para PDF re-renderizado não parecer alteração** |
| C24 | `insurance_corpus.py:1433-1438` | hash igual + `status='ingested'` → **não reingere** |
| C25 | `insurance_corpus.py:177` | `extrair_texto_de_pdf` com **PyMuPDF** — 📊 escolhido porque devolvia 11.064 linhas onde o PyPDF2 devolvia 519 |
| C26 | `insurance_corpus.py:696` | `partir_documento` — o corte é **por seção**, e 🔴 **nenhum campo do payload carrega página** |
| C27 | `insurance_corpus.py:758-776,910-911` | a etiqueta (seguradora · ramo · título · vigência · SUSEP) é colada **dentro do texto** do pedaço |
| C28 | `insurance_corpus.py:976-983` | `TIPOS` — o classificador produz **6** `doc_kind`; `manual_de_assistencia` **não** existe |
| C29 | `insurance_corpus.py:1887,1900,1908,1921-1942` | `aprovar()` · `rejeitar()` · `candidatos()` · `vencidos()` que **exige `approved_at is not null`** — **a fila de curadoria do documento já existe** |
| C30 | `insurance_corpus.py:1125-1171` | o payload do Qdrant recebe na raiz `insurer_key`, `product_line`, `doc_kind`, `susep_process`, `effective_from`, `vigente`, `unit_id`, `parent_id`, `faceta` |
| C31 | `insurance_corpus.py:1608` + `knowledge/acervo_arquivo.py` | `_guardar_a_fonte` arquiva os **bytes originais** no MinIO — 🔴 é daqui que §7.1 lê a página |
| C32 | `insurance_corpus.py`, docstring de abertura | *"Uma apólice emitida em 2023 é regida pela condição vigente **na emissão**, não pela de hoje… pode estar confiantemente errado sobre cobertura — e o corretor repete isso para o cliente"* |
| C33 | `backend/app/api/corpus.py:43,90-96` | `doc_kind` obrigatório em `RegistrarIn`; `POST /api/corpus/aprovar` protegida por `BACKEND_INTERNAL_API_KEY`; **nenhuma rota recebe `company_id`** |

### 1.3 Busca e escopo global

| ID | arquivo:linha | o que está lá |
|---|---|---|
| C40 | `backend/app/services/knowledge_scope.py:37` | `GLOBAL_COLLECTION = "autobrokers_global"` |
| C41 | `knowledge_scope.py:383-389` | `build_global_search_kwargs()` **não passa `company_id`**; isola por `scope_match=GLOBAL_SCOPES` + `curation_published_only=True` |
| C42 | `knowledge_scope.py:59-61,64-87` | o tenant do RAG é o **nome da coleção** (`company_{id}`), não um campo de payload; `colecao_permitida` é o guarda |
| C43 | `backend/app/services/qdrant_service.py:891-909` | 🔴 o item devolvido tem **8 chaves**: `score`, `score_scale`, `content`, `document_id`, `agent_id`, `chunk_index`, `metadata`, `namespace`. **Nenhum campo de C30 volta** |
| C44 | `qdrant_service.py:88-99` | `_INDICES_DE_PAYLOAD`: `document_id`, `agent_id`, `metadata.file_type`, `scope`, `curation_status`, `namespace`, `insurer_key`, `faceta`, `temas`, `vigente`. 🔴 **`doc_kind` não está** |
| C45 | `qdrant_service.py:639-668` | assinatura de `search_similar` — **não há parâmetro `doc_kind`** |
| C46 | `qdrant_service.py:434` | `_filtro_de_seguradora` — o braço "desta OU sem", o molde que §6.5 copia para `doc_kind` |
| C47 | `backend/app/services/search_service.py:466` | `if include_global or os.getenv("KNOWLEDGE_GLOBAL_SEARCH","1")=="1"` — o global está **ligado por default** |

### 1.4 Catálogo de seguradoras, e as duas referências internas

| ID | arquivo:linha | o que está lá |
|---|---|---|
| C50 | `backend/app/providers/susep_ses_provider.py:92-95` | `UNKNOWN` é **a string**, nunca `None` — *"`None` sumiria num `if coenti:` e viraria 'não filtrou nada'"* |
| C51 | `susep_ses_provider.py:165-167` | *"Uma sigla só entra no arquivo por igualdade de nome COMPLETO … ou por DECISÃO EXPLÍCITA de gente. Nunca por derivação de string em runtime."* |
| C52 | `susep_ses_provider.py:129-147,155-181,184-212` | `mapa_de_seguradoras()` · `mapa_de_siglas()` · `mapa_de_ramos()` — **único** leitor de `docs/canon/providers/susep/` |
| C53 | `docs/canon/providers/susep/seguradora-coenti.json` | topo: `_doc, fonte, medido_em, criterio_de_casamento, placar, seguradoras (15), siglas (61), placar_das_siglas`. Cada sigla: `nome_no_sistema_de_gestao, coenti, canonica, criterio` |
| C54 | `docs/canon/providers/susep/ramo-cogrupo.json` | `grupos_ses` (22) + `ramos` (50); cada ramo: `cogrupo, grupo_ses, codigo_infocap, nome_infocap, ramo_ses_que_justifica, criterio, decidido_em` |
| C55 | `docs/canon/sql/reconstruidas/20260725215808_spec057_h1_normative_corpus.sql:54,81-85` | o DDL de `normative_documents` e o CHECK de `doc_kind` com **9 valores**. 🔴 Arquivo marcado **PROIBIDO APLICAR**; a tabela é **classe SEM_ARQUIVO** |
| C56 | `backend/tests/test_a_cobertura_tem_lastro_no_acervo.py` (254 linhas) | *"Toda afirmação de COBERTURA aponta uma tela do acervo"* — a referência interna do juiz |
| C57 | `backend/tests/test_cobertura_nao_mente_para_cima.py` (185 linhas) | 📊 cobertura contada por ocorrência inflava: Allianz painel 63% → real 37% |

---

## 2. As medições — cada uma com a consulta que a produziu

> Rodadas em **13/09/2026** contra `SUPABASE_DB_URL`, com `psycopg`, `autocommit`, só SELECT.

### M1 · O corpus normativo

```sql
select doc_kind, status, count(*) from normative_documents group by 1,2 order by 3 desc;
select count(*) total, count(susep_process) com_susep, count(content_hash) com_hash,
       sum(coalesce(chunk_count,0)) chunks, count(distinct qdrant_collection) colecoes,
       count(approved_at) aprovados from normative_documents;
select status, count(*) from normative_documents where coalesce(chunk_count,0)>0 group by 1;
select count(distinct insurer_key) from normative_documents where coalesce(chunk_count,0)>0;
select count(next_check_at), count(last_checked_at), min(check_interval_days),
       max(check_interval_days) from normative_documents;
```
```
condicoes_gerais  ingested 89 · superseded 86 · discovered 7 · fetching 2   (184)
circular_susep    ingested 5      manual_do_segurado  ingested 3 · discovered 2
TOTAL 194 · com_susep 190 · com_hash 183 · chunks 42.091 · colecoes 1 · aprovados 31
com chunk>0: ingested 97 · superseded 86   |  insurer_keys: 9 (8 seguradoras + `susep`, o regulador)
qdrant_collection: autobrokers_global 183 · (null) 11
next_check_at 194/194 · last_checked_at 190 · intervalo 21 a 45 dias
```

```sql
select insurer_key, count(*), count(distinct product_line), count(susep_process)
  from normative_documents group by 1 order by 2 desc;
select product_line, count(*) from normative_documents group by 1 order by 2 desc;
select insurer_key, product_line, count(*) from normative_documents
 where status='ingested' and coalesce(chunk_count,0)>0 group by 1,2 order by 1,2;
```
```
bradesco 77 · mapfre 50 · tokio 25 · hdi 10 · allianz 9 · yelum 8 · porto 6 · susep 5 · azul 4
vida 101 · residencial 24 · auto 24 · empresarial 15 · equipamentos 14 · condominio 8 ·
garantia 5 · responsabilidade_civil 2 · geral 1
ramos dos pilotos (indexados): allianz auto 2/resi 1/cond 1 — azul auto 3 — bradesco auto 3/resi 7/cond 2
  — hdi auto 4/resi 4 — mapfre auto 4/resi 5/cond 1 — porto auto 1/resi 1/cond 1
  — tokio auto 3/resi 4/cond 1 — yelum auto 2/resi 1/cond 1
```

🔴 **A leitura que reordena a onda 1:** a maior fatia do corpus é **vida** — o ramo que os pilotos não vendem. Os
ramos dos pilotos somam **56** documentos (auto 24 + residencial 24 + condomínio 8).

### M2 · O denominador: a carteira

```bash
python -c "import json,io; d=json.load(io.open('docs/canon/providers/susep/seguradora-coenti.json',encoding='utf-8')); print(d['placar_das_siglas'])"
```
```
siglas_no_censo 61 · com_coenti 14 · por_nome_completo 1 · por_decisao_explicita 13
cobertura_de_premio_pct 83,86 · premio_medido 21.814.941,56
medido_com: "a carteira viva de 2025 da corretora piloto, 3.861 linhas, soma de `pretot` por sigla"
siglas_da_carteira_sem_coenti: MAP · AXA · MAG · JUNT · AIG · ESSO · ITAU · BERK · CHUB · FATO · JNS · MITS
```

Cruzamento (mesmo script, `set` das `canonica` × as 8 `insurer_key` com CG):
```
14 canônicas: alfa allianz azul bradesco mapfre porto seguros_unimed sompo suhai sulamerica
              sura tokio_marine yelum zurich
COM CG sob a mesma chave (6): allianz azul bradesco mapfre porto yelum
SEM CG (8):  alfa seguros_unimed sompo suhai sulamerica sura tokio_marine zurich
```
🔴 **`tokio` (25 documentos) não casa com `tokio_marine`. `hdi` (10 documentos) não está entre as 61 siglas.**

### M3 · A chave que ninguém governa

```sql
select conname, conrelid::regclass::text, pg_get_constraintdef(oid)
  from pg_constraint where pg_get_constraintdef(oid) ilike '%insurer_key%';
select table_name from information_schema.columns
 where table_schema='public' and column_name='insurer_key' order by 1;
select insurer_key, count(*) from portals group by 1 order by 1;
select insurer_key, count(*) from knowledge_cards
 where status='published' and insurer_key is not null group by 1 order by 1;
```
```
constraints que mencionam insurer_key ..... NENHUMA LINHA
tabelas com a coluna ...................... 14
portals (15 valores) ...................... inclui `tokio_marine`
knowledge_cards (20 valores) .............. inclui `tokio`, e axa · chubb · essor · itau · unimed ·
                                            youse, que não existem em portals
```
⚠️ **Isto NÃO significa que falte um normalizador** — ele existe (C11c) e já resolve `tokio` ↔ `tokio_marine`. O que
falta é o **banco** conhecer a chave (zero constraints) e a base nova **gravar já normalizado**, com
`para="conhecimento"`. 🔴 **Criar um `chave_canonica(valor)` de um argumento seria o terceiro normalizador e
colapsaria a distinção corredor × conhecimento** (CLAUDE.md §5).

### M4 · Zero plano estruturado

```sql
select table_name, column_name from information_schema.columns where table_schema='public'
 and (column_name ilike '%assist%' or column_name ilike '%nivel%' or column_name ilike '%plano%'
      or column_name ilike '%carencia%' or column_name ilike '%cobertura%');
select table_name from information_schema.tables where table_schema='public'
 and (table_name ilike '%plan%' or table_name ilike '%assist%' or table_name ilike '%cobert%');
```
```
colunas: companies.plan_type · conversation_logs.assistant_response · research_plans.replan_reason ·
         subscriptions.plan_id · users_v2.plan_id · users_v2.plan_status
tabelas: plans (plano do SaaS) · research_plans (pesquisa)
```
🔴 **Nenhuma tabela, nenhuma coluna de plano de assistência de seguradora. `insurer_assistance_plans` não existe.**

### M5 · As cartas

```sql
select status, count(*) from knowledge_cards group by 1 order by 2 desc;
select category, count(*) from knowledge_cards where status='published' group by 1 order by 2 desc;
select insurer_key, count(*) from knowledge_cards
 where status='published' and (category ilike '%assist%' or faceta ilike '%assist%')
 group by 1 order by 2 desc;
```
```
published 17.995 · superseded 681 · rejected_* 39
sinistro 9.200 · cobranca 3.790 · atendimento 2.094 · assistencia 1.535 · apolice 1.376
assistência por seguradora: (null) 784 · allianz 196 · porto 187 · yelum 163 · hdi 115 ·
                            tokio 25 · bradesco 22 · alfa 14 · azul 13 · zurich 7 · mapfre 4 · …
```
⚠️ **784 das 1.535 cartas de assistência não dizem de qual seguradora são.** Uma carta sem seguradora não responde
*"o plano DELE tem carro reserva?"*.

### M6 · O acervo das perguntas (o gate das 30)

```sql
select count(*) from messages;
select '<termo>' termo, count(*) from messages where role in ('user','human') and content ilike '%<termo>%';
```
```
messages 33.565
guincho 121 · reserva 102 · vidro 93 · carro reserva 81 · cobre 45 · eletricista 36 ·
granizo 26 · chaveiro 24 · encanador 24 · reboque 18 · táxi 15 · hotel 4 · borracheiro 2
```
🔴 **O gate de 30 perguntas cabe no acervo com folga, nas seis categorias.** O executor extrai **só as perguntas**,
com PII removida.

### M7 · Onde a tabela NÃO fica

```sql
select column_name from information_schema.columns where table_schema='public' and table_name='documents';
select scope, knowledge_class, curation_status, source_kind, count(*) from documents group by 1,2,3,4;
```
```
documents: 16 linhas (15 scope='connector', 1 scope='agent'; curation_status='published' nas 16)
🔴 `documents` NÃO tem coluna `doc_kind`. `doc_kind` é coluna de `normative_documents`.
document_chunks / insurer_assistance_plans / global_knowledge ... não existem
```

---

## 3. As três divergências do diagnóstico — e o número de hoje

| # | o diagnóstico diz | medição de hoje | veredito |
|---|---|---|---|
| D1 | §3: *"hoje **10 de 61** seguradoras com CG"* | **8** por chave própria (M1); **6** quando a chave tem de casar com o catálogo (M2) | o **§1.3 do mesmo documento já dizia 8**. O "10" é o número frouxo |
| D2 | §1.3: *"`knowledge_cards`: **857**, **39** de assistência, **4** nomeiam seguradora"* | **17.995** · **1.535** · **20** chaves (M5) | número de um recorte antigo; o denominador de hoje é outro |
| D3 | §1.3 e §3: *"a ligação apólice → CG pelo processo SUSEP **já casa hoje**"* | 🔴 **não existe código que case**: o extrator existe (C22) e o corpus tem o campo (190/194), mas **não há consumidor** | vira a onda 2, com a linha de controle **no caminho realmente usado** (M-C2) |

**Comandos que sustentam D3:**
```bash
grep -rn 'eq("susep_process"\|by_susep\|por_susep' backend/ --include=*.py        # VAZIO
grep -rni "susep" backend/app/services/policy_facts.py backend/app/services/assistance_policy.py \
     backend/app/services/policy_answer_composer.py backend/app/providers/policy_data_provider.py \
     backend/app/agents/tools/infocap_tool.py                                     # VAZIO
```
🔴 **O que NÃO sustenta D3, e a primeira versão desta proposta afirmava:** que `susep` em `_BOILERPLATE_RE`
bloqueava o elo. **Não bloqueia** — C11b. A medição que decide está no BLOCO 0 passo 5:
`extrair_susep(build_document_plain_text(pages))` sobre um PDF real. **Ainda não rodada.**

⚠️ Duas imprecisões do **pacote do redator** (não do diagnóstico): *"o corpus — `documents`/`doc_kind`"* (**`doc_kind`
não existe em `documents`**, M7) e *"localize o código que já casa [apólice ↔ CG]"* (**não existe**, D3).

---

## 4. Roteiro de remedição — comandos para o BLOCO 0, não saídas já obtidas

⚠️ O preflight está no PROMPT §5 e não se repete aqui. Os greps próprios desta superfície:

```bash
rg -n "PolicyDataProvider|get_policy_data_provider|assistance_policy" backend/app --type py
rg -n "_BOILERPLATE_RE|extrair_susep|_RE_SUSEP" backend/app --type py
rg -n "doc_kind" backend/app backend/supabase/migrations --type py --type sql
rg -n "GLOBAL_COLLECTION|autobrokers_global|build_global_search_kwargs" backend/app --type py
rg -n "P-PILOTO-04|P-PILOTO-20" docs/canon/PENDENCIAS.md     # por número; nunca o arquivo (📊 562 KB)
pytest backend/tests/test_a_cobertura_tem_lastro_no_acervo.py \
       backend/tests/test_cobertura_nao_mente_para_cima.py \
       backend/tests/test_a_apolice_responde_item_por_item.py -q
```

🔴 **O schema REAL vem do catálogo, nunca do arquivo** (a tabela é classe SEM_ARQUIVO): `pg_get_constraintdef` de
`normative_documents_doc_kind_check` · `information_schema.columns` de `normative_documents` e
`normative_document_versions` · `pg_constraint ilike '%insurer_key%'` → esperado **NENHUMA LINHA**.
🔴 **Antes de qualquer SQL: `MIGRATIONS-AUTHORITY.md` inteiro.**

---

## 5. O que continua desconhecido — **A MEDIR no BLOCO 0**

1. **O contrato que a 001.1 vai entregar.** Esta proposta consome `Apolice`/`PlanoDeAssistencia` como a 001.1 os
   desenhou. **Não editar `policy_data_provider.py` aqui.**
2. **Quantas condições gerais nomeiam níveis de plano.** Sabemos que 56 documentos são dos ramos dos pilotos; não
   sabemos quantos separam "Essencial / Completo / VIP". **É o número que decide o tamanho real da onda 1.**
3. 🔴 **Se as fontes arquivadas no MinIO existem para os 56** — `_guardar_a_fonte` (`insurance_corpus.py:1608`)
   existe, mas a cobertura **nunca foi medida**, e 📊 o comentário desse mesmo ponto registra `storage_ref`
   preenchido em **0 de 29** numa medição anterior. **A onda 1 e o CHECK `pagina NOT NULL` dependem disso**: sem o
   arquivo não há página que exista. É o passo 8 do BLOCO 0, e pode acrescentar re-arquivamento ao relógio.
4. **Se `tool_invocations` guarda `tool_args` cru hoje.** Se guardar, é **P1 de segurança** e a drenagem vem antes.
5. **O peso da carteira hoje**, pela porta — o `placar_das_siglas` é de 04/09 e mede 2025.
6. **Se P-PILOTO-20 já foi fechada pela 001.1.**
7. **Se algum agente resolve skill do `SkillRegistry` em runtime** (21 releases no banco; os únicos chamadores
   medidos são `gateway_cutover.py:153` e `auxiliaries/factory.py:333`). Decide a escolha "tool × skill release".
8. **O custo da extração assistida** — nenhum orçamento de tokens por documento foi medido.

---

## 6. Armadilhas que o aquecimento tem de refutar

1. *"O corpus de condições gerais mora em `documents`, e `doc_kind` é coluna de lá."* **Não.** (M7)
2. *"A ligação apólice → CG pelo processo SUSEP já casa hoje."* **Não casa** — falta o consumidor. 🔴 **E a
   contra-armadilha:** *"está bloqueada porque `susep` está no `_BOILERPLATE_RE`"* também é **falso** — o filtro só
   governa fragmentos; o texto integral não passa por ele. (D3, C11b)
3. *"O pedaço indexado tem página, então a citação sai de graça."* **Não tem.** (C26, C43)
4. *"Criar `curation_status` é necessário porque não há fila de curadoria."* **Há.** (C29)
5. *"Não existe normalizador de seguradora, então a SPEC escreve um."* 🔴 **Existe** —
   `normalize_insurer_key(..., para="conhecimento")`, 14 chamadores. Escrever outro é o terceiro. (C11c, C11d)
6. *"Apagar `assistance_policy.py` é o conserto."* Apagar derruba o guarda de `nodes.py:307` junto — e o caminho vivo
   é `graph.py:447` → `infocap_tool.py:319` → `policy_answer_composer.py:376`: **uma tool nova ao lado seria a
   segunda porta para a mesma pergunta.** (C09)
7. *"Basta ligar `citations: true` na API e a base fica certa."* A garantia é de **ponteiro válido**, não de
   afirmação correta. (§15 ② da proposta)
8. *"A condição geral atual da seguradora serve para qualquer apólice dela."* O próprio código avisa que não. (C32)
9. *"`doc_kind` já filtra a busca."* Não está no índice de payload nem na assinatura. (C44, C45)
10. *"É PADRÃO, então a migration é rotina."* A de §11.2 altera uma **trava** de tabela viva e **classe
    SEM_ARQUIVO** — piso CRÍTICO e manifesto completo. (C55)

---

## 7. As três referências externas — reabertas em 13/09/2026

| # | URL | o ponto que a proposta §15 modela |
|---|---|---|
| ① | https://www.w3.org/TR/prov-o/ | `wasQuotedFrom` + `wasAttributedTo` na mesma linha: de onde veio **e** quem publicou |
| ② | https://platform.claude.com/docs/en/docs/build-with-claude/citations (301 de `docs.anthropic.com`) | *"citations are guaranteed to contain valid pointers to the provided documents"*; `page_location` com `start_page_number` *"1-indexed"*, ao lado de `char_location` e `content_block_location` |
| ③ | https://arxiv.org/abs/2305.14627 (Gao, Yen, Yu, Chen · EMNLP 2023) | *"automatic metrics along three dimensions — fluency, correctness, and citation quality"*; 📊 *"on the ELI5 dataset, even the best models lack complete citation support 50% of the time"* |

⚠️ A ② redireciona (301). **Registrar o redirect**, não trocar a URL em silêncio. O pesquisador do executor reabre as
três e escreve a data da reabertura dele.

---

## 8. Regra de integridade

Este pacote é **evidência para conversão**, não relatório de execução. Toda linha da §1 foi reaberta em 13/09/2026
sobre `a0bb5fe`; toda medição da §2 tem a consulta acima. **O número do executor vence** — e a divergência vai
escrita, nunca corrigida em silêncio.
