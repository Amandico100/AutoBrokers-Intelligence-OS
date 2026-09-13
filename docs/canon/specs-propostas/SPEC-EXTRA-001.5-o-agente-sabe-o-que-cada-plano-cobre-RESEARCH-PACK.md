# SPEC-EXTRA-001.5 — RESEARCH PACK
## A evidência por trás de "o agente sabe o que cada plano cobre"

**Versão:** 1.0 · 13/09/2026. **Natureza:** evidência para conversão; não é relatório de execução.
**Baseline:** `a0bb5fe` (worktree `AutoBrokers-FIX`, 0 atrás e 0 à frente de `origin/main`).
**Método:** leitura dos arquivos **reabertos nesta data** e consultas **read-only** (SELECT e contagem) ao banco de
produção pela `SUPABASE_DB_URL` de `backend/.env`. Nenhum teste de produto executado, nenhuma mensagem enviada,
nenhum portal acessado, nenhuma escrita. **Nenhuma consulta retornou conteúdo de mensagem, nome, documento ou
telefone.** Leitura de código não é prova de funcionamento.

**Legenda:** **CONFERIDO** = arquivo reaberto hoje, linha confirmada · **MEDIDO** = consulta rodada hoje, com o SQL ·
**NÃO EXISTE** = busca rodada e vazia, com o comando · **A MEDIR** = pendente do BLOCO 0.

---

## 1. Linhas de código conferidas hoje — as que a proposta cita

### 1.1 A camada de apólice e assistência

| ID | arquivo:linha | o que está lá | usado em |
|---|---|---|---|
| C01 | `backend/app/providers/policy_data_provider.py:41-52` | `class PolicyDataProvider(Protocol)` — **só** `provider_key`, `lookup(**kwargs) -> Dict[str,Any]`, `detail(**kwargs) -> Dict[str,Any]`. ⚠️ `vehicle` existe na implementação (`:112`) e **não** no Protocol | §2.2, §4.2 |
| C02 | `policy_data_provider.py:55,58` | `class InfocapPolicyDataProvider`, `provider_key="infocap"`. **Única** implementação concreta | §2.2 |
| C03 | `policy_data_provider.py:137,144,149` | `register_policy_data_provider` · `get_policy_data_provider(provider_key="infocap")` · registro no import. Registry **em memória**, sem env, sem tabela | §2.2 |
| C04 | `backend/app/services/assistance_policy.py:28` | `STANDARD_SERVICES = ("eletricista","chaveiro","hidraulica_encanador")` — **142 linhas no arquivo inteiro**; nenhuma seguradora, nenhum produto, nenhum nível | §0.1, §6.5 |
| C05 | `assistance_policy.py:4-6` | docstring: *"migração para tabela `platform_policies` com overrides por seguradora/produto/plano/corretora está prevista para quando o primeiro override existir"* | §6.5 |
| C06 | `assistance_policy.py:47-58` | `_is_residential` — gatilho por **substring** `"resid"` (`:54`) ou token `"resi"` (`:56`) sobre `line_kind_detected`/`product_detected`/`ramo` | §6.5 |
| C07 | `assistance_policy.py:123` | `locator_hash = None` fixo em `policy_rule_facts` — o fato de regra **perde o vínculo com a apólice** | §6.5 |
| C08 | `backend/app/services/policy_answer_composer.py:24` | **único** importador de `assistance_policy` em produção | §6.5 |
| C09 | `backend/app/agents/nodes.py:307-317` | o guarda anula a resposta final se `assistance_policy_applied` está no contrato e o texto não contém "eletricista" **e** "chaveiro" **e** ("hidraulica"\|"hidráulica"\|"encanador") | §6.5, M-B5 |
| C10 | `nodes.py:297-303` | o guarda **já** rejeita página citada que não está no texto determinístico — o padrão que M-A3 copia | §3.1, §16 ② |
| C11 | `backend/app/services/policy_document_evidence_service.py:204-209` | 🔴 `_BOILERPLATE_RE` contém **`susep`**: toda linha do PDF da apólice que menciona SUSEP é descartada | §0.3 ②, §7.2, M-C2 |
| C12 | `policy_document_evidence_service.py:230-318` | `_ASSISTANCE_HEADER_RE = assist[êe]ncia\s*24\s*h`; emite `kind="assistance_plan"` (`:286`) e `kind="assistance_services"` (`:302`); termos em `_SERVICE_TERM_RE` (`:231-235`) incluem `guincho` | §3.1, §6.2 ③a |
| C13 | `policy_document_evidence_service.py:387-407` | `_base_item` grava `page_number` e `chunk_id = "{doc}:p{n}:{i}"` — **o caminho da apólice TEM página** | §0.3 ④ |
| C14 | `policy_document_evidence_service.py:539-549` | 🔴 o fallback docling devolve **uma única página, `page_number: 1`**, com o markdown inteiro dentro | §0.3 ④, §7.1 |
| C15 | `backend/app/api/infocap_connector.py:3955,3973-3974,4015` | `tabela_itens` vira só o sinal `unknown_table_field_present` + a limitação *"sem semantica comprovada para cobertura"* | §6.2 ③b |
| C16 | `infocap_connector.py:4017` | `document_evidence_required = (not structured_available) and (official_doc_available or unknown_table)` — `tabela_itens` presente **já** manda ler o PDF | §6.2 |

### 1.2 O corpus normativo — o pipeline que se reusa

| ID | arquivo:linha | o que está lá | usado em |
|---|---|---|---|
| C20 | `backend/app/services/knowledge/insurance_corpus.py:41` | `COLECAO_GLOBAL = "autobrokers_global"` (duplicata literal de `knowledge_scope.py:37`) | §3.1 |
| C21 | `insurance_corpus.py:49` | `_RE_SUSEP = r"\b(\d{5}\.\d{6}/\d{4}-\d{2})\b"` | §7.2 |
| C22 | `insurance_corpus.py:65` | `def extrair_susep(texto) -> Optional[str]` — **o extrator existe** | §7.2 |
| C23 | `insurance_corpus.py:58-62` | `_hash` — SHA-256 com espaço normalizado, **para PDF re-renderizado não parecer alteração** | §7.4 |
| C24 | `insurance_corpus.py:1433-1438` | hash igual + `status='ingested'` → **não reingere** | §7.4 |
| C25 | `insurance_corpus.py:177` | `extrair_texto_de_pdf` com **PyMuPDF** — escolhido porque 📊 devolvia 11.064 linhas onde o PyPDF2 devolvia 519 | §7.1 |
| C26 | `insurance_corpus.py:696` | `partir_documento` — o corte é **por seção**, e 🔴 **nenhum campo do payload carrega página** | §0.3 ④, §7.1 |
| C27 | `insurance_corpus.py:758-776,910-911` | a etiqueta (seguradora · ramo · título · vigência · SUSEP) é colada **dentro do texto** do pedaço | §0.3 ④ |
| C28 | `insurance_corpus.py:976-983` | `TIPOS` — o classificador produz **6** `doc_kind`; `manual_de_assistencia` **não** existe | §7.3 |
| C29 | `insurance_corpus.py:1887,1900,1908,1921-1942` | `aprovar()` · `rejeitar()` · `candidatos()` · `vencidos()` que **exige `approved_at is not null`** — **a fila de curadoria do documento já existe** | §0.3 ①, §5.4 |
| C30 | `insurance_corpus.py:1125-1171` | o payload do Qdrant recebe na raiz: `insurer_key`, `product_line`, `doc_kind`, `susep_process`, `effective_from`, `vigente`, `unit_id`, `parent_id`, `faceta` | §0.3 ④ |
| C31 | `insurance_corpus.py:1608` + `knowledge/acervo_arquivo.py` | `_guardar_a_fonte` arquiva os **bytes originais** no MinIO — 🔴 é daqui que §7.1 lê a página | §7.1 |
| C32 | `insurance_corpus.py` (docstring de abertura) | *"Uma apólice emitida em 2023 é regida pela condição vigente **na emissão**, não pela de hoje… pode estar confiantemente errado sobre cobertura — e o corretor repete isso para o cliente"* | §7.2, M-C3 |
| C33 | `backend/app/api/corpus.py:43,90-96` | `doc_kind` é campo obrigatório em `RegistrarIn`; `POST /api/corpus/aprovar` protegida por `BACKEND_INTERNAL_API_KEY`; **nenhuma rota recebe `company_id`** | §3.1 |

### 1.3 A busca e o escopo global

| ID | arquivo:linha | o que está lá | usado em |
|---|---|---|---|
| C40 | `backend/app/services/knowledge_scope.py:37` | `GLOBAL_COLLECTION = "autobrokers_global"` | §3.1 |
| C41 | `knowledge_scope.py:383-389` | `build_global_search_kwargs()` **não passa `company_id`**; isola por `scope_match=GLOBAL_SCOPES` + `curation_published_only=True` | §3.3 |
| C42 | `knowledge_scope.py:59-61,64-87` | o tenant do RAG é o **nome da coleção** (`company_{id}`), não um campo de payload; `colecao_permitida` é o guarda | §3.3 |
| C43 | `backend/app/services/qdrant_service.py:891-909` | 🔴 o item devolvido tem **8 chaves**: `score`, `score_scale`, `content`, `document_id`, `agent_id`, `chunk_index`, `metadata`, `namespace`. **Nenhum campo de C30 volta** | §0.3 ④, §6.6 |
| C44 | `qdrant_service.py:88-99` | `_INDICES_DE_PAYLOAD`: `document_id`, `agent_id`, `metadata.file_type`, `scope`, `curation_status`, `namespace`, `insurer_key`, `faceta`, `temas`, `vigente`. 🔴 **`doc_kind` não está** | §6.6 |
| C45 | `qdrant_service.py:639-668` | assinatura de `search_similar` — **não há parâmetro `doc_kind`** | §6.6 |
| C46 | `qdrant_service.py:434` | `_filtro_de_seguradora` — o braço "desta OU sem", o molde que §6.6 copia para `doc_kind` | §6.6 |
| C47 | `backend/app/services/search_service.py:466` | `if include_global or os.getenv("KNOWLEDGE_GLOBAL_SEARCH","1")=="1"` — o global está **ligado por default** | §3.1 |
| C48 | `search_service.py:531-545,564-579` | as duas faixas do orçamento global (`normative` 12 · `cards`/`canon` 12) e a cota de faceta | §3.1 |

### 1.4 O catálogo de seguradoras

| ID | arquivo:linha | o que está lá | usado em |
|---|---|---|---|
| C50 | `backend/app/providers/susep_ses_provider.py:92-95` | `UNKNOWN` é **a string**, nunca `None` — *"`None` sumiria num `if coenti:` e viraria 'não filtrou nada'"* | §5.1 |
| C51 | `susep_ses_provider.py:165-167` | *"Uma sigla só entra no arquivo por igualdade de nome COMPLETO … ou por DECISÃO EXPLÍCITA de gente. Nunca por derivação de string em runtime."* | §5.1 |
| C52 | `susep_ses_provider.py:129-147,155-181,184-212` | `mapa_de_seguradoras()` · `mapa_de_siglas()` · `mapa_de_ramos()` — **único** leitor de `docs/canon/providers/susep/` | §3.1, §5.1 |
| C53 | `docs/canon/providers/susep/seguradora-coenti.json` | topo: `_doc, fonte, medido_em, criterio_de_casamento, placar, seguradoras (15), siglas (61), placar_das_siglas`. Cada sigla: `nome_no_sistema_de_gestao, coenti, canonica, criterio` | §0.1, §5.1, §7.3 |
| C54 | `docs/canon/providers/susep/ramo-cogrupo.json` | `grupos_ses` (22) + `ramos` (50); cada ramo: `cogrupo, grupo_ses, codigo_infocap, nome_infocap, ramo_ses_que_justifica, criterio, decidido_em` | §5.2 |
| C55 | `docs/canon/sql/reconstruidas/20260725215808_spec057_h1_normative_corpus.sql:54,81-85` | o DDL de `normative_documents` e o CHECK de `doc_kind` com **9 valores**. 🔴 Arquivo marcado **PROIBIDO APLICAR**; a tabela é **classe SEM_ARQUIVO** | §11.2 |
| C56 | `backend/tests/test_a_cobertura_tem_lastro_no_acervo.py` (254 linhas) | *"Toda afirmação de COBERTURA aponta uma tela do acervo"* — a referência interna do juiz | card, §3.1 |
| C57 | `backend/tests/test_cobertura_nao_mente_para_cima.py` (185 linhas) | 📊 cobertura contada por ocorrência inflava: Allianz painel 63% → real 37% | §8, M-D1 |

---

## 2. As medições — cada uma com a consulta que a produziu

> Todas rodadas em **13/09/2026** contra `SUPABASE_DB_URL`, com `psycopg` e `autocommit`, só SELECT.

### M1 · O corpus normativo

```sql
select doc_kind, status, count(*) from normative_documents group by 1,2 order by 3 desc;
```
```
condicoes_gerais    ingested    89      circular_susep      ingested     5
condicoes_gerais    superseded  86      manual_do_segurado  ingested     3
condicoes_gerais    discovered   7      manual_do_segurado  discovered   2
condicoes_gerais    fetching     2                     TOTAL           194
```

```sql
select count(*) total, count(susep_process) com_susep, count(content_hash) com_hash,
       sum(coalesce(chunk_count,0)) soma_chunks, count(distinct qdrant_collection) colecoes,
       count(approved_at) aprovados from normative_documents;
```
```
total 194 · com_susep 190 · com_hash 183 · soma_chunks 42.091 · colecoes 1 · aprovados 31
```

```sql
select status, count(*) from normative_documents where coalesce(chunk_count,0)>0 group by 1;
select count(distinct insurer_key) from normative_documents where coalesce(chunk_count,0)>0;
select qdrant_collection, count(*) from normative_documents group by 1 order by 2 desc;
select count(*) total, count(next_check_at) com_next, count(last_checked_at) ja_checados,
       min(check_interval_days), max(check_interval_days) from normative_documents;
```
```
ingested 97 · superseded 86  |  insurer_keys com chunk>0: 9 (8 seguradoras + `susep`, o regulador)
autobrokers_global 183 · (null) 11
next_check_at 194/194 · last_checked_at 190 · intervalo 21 a 45 dias
```

```sql
select insurer_key, count(*), count(distinct product_line), count(susep_process)
  from normative_documents group by 1 order by 2 desc;
select product_line, count(*) from normative_documents group by 1 order by 2 desc;
```
```
bradesco 77 · mapfre 50 · tokio 25 · hdi 10 · allianz 9 · yelum 8 · porto 6 · susep 5 · azul 4
vida 101 · residencial 24 · auto 24 · empresarial 15 · equipamentos 14 · condominio 8 ·
garantia 5 · responsabilidade_civil 2 · geral 1
```

🔴 **A leitura que reordena a onda 1:** a maior fatia do corpus é **vida** — o ramo que os pilotos não vendem. Os
ramos dos pilotos somam **56** documentos (auto 24 + residencial 24 + condomínio 8).

```sql
select insurer_key, product_line, count(*) from normative_documents
 where status='ingested' and coalesce(chunk_count,0)>0 group by 1,2 order by 1,2;
```
Recorte dos ramos dos pilotos: allianz auto 2 · resi 1 · condomínio 1 — azul auto 3 — bradesco auto 3 · resi 7 ·
condomínio 2 — hdi auto 4 · resi 4 — mapfre auto 4 · resi 5 · condomínio 1 — porto auto 1 · resi 1 · condomínio 1 —
tokio auto 3 · resi 4 · condomínio 1 — yelum auto 2 · resi 1 · condomínio 1.

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
14 siglas com canônica: alfa allianz azul bradesco mapfre porto seguros_unimed sompo suhai
                        sulamerica sura tokio_marine yelum zurich
COM CG sob a mesma chave (6): allianz azul bradesco mapfre porto yelum
SEM CG (8):                   alfa seguros_unimed sompo suhai sulamerica sura tokio_marine zurich
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
constraints que mencionam insurer_key ...... NENHUMA LINHA
tabelas com a coluna ....................... 14
portals (15 valores) ....................... inclui `tokio_marine`
knowledge_cards (20 valores) ............... inclui `tokio`, e também axa · chubb · essor · itau ·
                                             unimed · youse, que não existem em portals
```

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
⚠️ **784 das 1.535 cartas de assistência não dizem de qual seguradora são.** Elas não substituem a base: uma carta
sem seguradora não responde *"o plano DELE tem carro reserva?"*.

### M6 · O acervo das perguntas (o gate das 30)

```sql
select count(*) from messages;
-- e, por termo, sem devolver conteúdo:
select '<termo>' termo, count(*) from messages where role in ('user','human') and content ilike '%<termo>%';
```
```
messages 33.565
guincho 121 · reserva 102 · vidro 93 · carro reserva 81 · cobre 45 · eletricista 36 ·
granizo 26 · chaveiro 24 · encanador 24 · reboque 18 · táxi 15 · hotel 4 · borracheiro 2
```
🔴 **O gate de 30 perguntas cabe no acervo com folga, em todas as seis categorias.** O executor extrai **só as
perguntas**, com PII removida.

### M7 · Onde a tabela NÃO fica

```sql
select table_name, count(*) ... from information_schema.tables ... ('documents','document_chunks', ...)
select column_name from information_schema.columns where table_name='documents';
```
```
documents 16 linhas (15 scope='connector', 1 scope='agent'; curation_status='published' nas 16)
🔴 `documents` NÃO tem coluna `doc_kind`. `doc_kind` é coluna de `normative_documents`.
document_chunks / insurer_assistance_plans / global_knowledge ... não existem
```

---

## 3. As três divergências do diagnóstico — e o número de hoje

| # | o diagnóstico diz | medição de hoje | veredito |
|---|---|---|---|
| D1 | §3: *"hoje **10 de 61** seguradoras com CG"* | **8** por chave própria (M1); **6** quando a chave tem de casar com o catálogo (M2) | o **§1.3 do mesmo documento já dizia 8**. O "10" é o número frouxo; o de hoje vence |
| D2 | §1.3: *"`knowledge_cards`: **857**, **39** de assistência, **4** nomeiam seguradora"* | **17.995** publicadas · **1.535** de assistência · **20** chaves (M5) | número de um recorte antigo; o denominador de hoje é outro |
| D3 | §1.3 e §3: *"a ligação apólice → CG pelo processo SUSEP **já casa hoje**"* | 🔴 **não existe código que case** — e o caminho está **bloqueado** (C11) | a maior correção; vira a onda 2 inteira, com uma linha de controle própria (M-C2) |

**Comandos que sustentam D3:**
```bash
grep -rn 'eq("susep_process"\|by_susep\|por_susep' backend/ --include=*.py        # VAZIO
grep -rni "susep" backend/app/services/policy_facts.py \
     backend/app/services/assistance_policy.py backend/app/services/policy_answer_composer.py \
     backend/app/providers/policy_data_provider.py backend/app/agents/tools/infocap_tool.py   # VAZIO
sed -n '204,209p' backend/app/services/policy_document_evidence_service.py       # `susep` no _BOILERPLATE_RE
```

⚠️ Uma quarta imprecisão, menor, do **pacote do redator** (não do diagnóstico): *"o corpus de condições gerais —
`documents`/`doc_kind`"*. **`doc_kind` não existe em `documents`** (M7). O corpus mora em `normative_documents`.

---

## 4. Roteiro de remedição — comandos para o BLOCO 0, não saídas já obtidas

```bash
git fetch origin && git rev-list --count HEAD..origin/main && git rev-list --count origin/main..HEAD
git branch --show-current && git rev-parse HEAD && git status --short

# a fronteira e o que se reusa
rg -n "PolicyDataProvider|get_policy_data_provider" backend/app --type py
rg -n "assistance_policy|assistance_policy_applied" backend/app --type py
rg -n "_BOILERPLATE_RE|extrair_susep|_RE_SUSEP" backend/app --type py
rg -n "doc_kind" backend/app backend/supabase/migrations --type py --type sql
rg -n "GLOBAL_COLLECTION|autobrokers_global|build_global_search_kwargs" backend/app --type py

# o schema REAL (a tabela é classe SEM_ARQUIVO — ler do catálogo, nunca do arquivo)
#   pg_get_constraintdef de normative_documents_doc_kind_check
#   information_schema.columns de normative_documents e normative_document_versions
#   pg_constraint ilike '%insurer_key%'      -> esperado: NENHUMA LINHA

# as pendências, por número — NUNCA o arquivo inteiro (📊 562 KB)
rg -n "P-PILOTO-04|P-PILOTO-20" docs/canon/PENDENCIAS.md

# a suíte, e os guardas que guardam esta superfície
pytest backend/tests/test_a_cobertura_tem_lastro_no_acervo.py \
       backend/tests/test_cobertura_nao_mente_para_cima.py \
       backend/tests/test_a_apolice_responde_item_por_item.py -q
```

🔴 **Antes de qualquer SQL: `docs/canon/MIGRATIONS-AUTHORITY.md` inteiro.** 📊 9 versões aplicadas sem arquivo, 16
arquivos sem versão. Proibido sempre: `schema_completo.sql`, `upgrade_v6.2.sql`, `storage_buckets.sql`.

---

## 5. O que continua desconhecido — **A MEDIR no BLOCO 0**

1. **O contrato que a 001.1 vai entregar.** Esta proposta consome `Apolice`/`PlanoDeAssistencia` como a 001.1 os
   desenhou; se a 001.1 mudar nomes, a Skill muda com ela. **Não editar `policy_data_provider.py` aqui.**
2. **Quantas condições gerais nomeiam níveis de plano.** 📊 Sabemos que 56 documentos são dos ramos dos pilotos; não
   sabemos quantos separam "Essencial / Completo / VIP". **É o número que decide o tamanho real da onda 1.**
3. **Se as fontes arquivadas no MinIO estão completas** para os 56 — `_guardar_a_fonte` existe; a cobertura dele
   não foi medida.
4. **Se `tool_invocations` guarda `tool_args` cru hoje.** Se guardar, é **P1 de segurança** e a drenagem vem antes.
5. **O peso da carteira hoje**, pela porta — o `placar_das_siglas` é de 04/09 e mede 2025.
6. **Se P-PILOTO-20 já foi fechada pela 001.1.**
7. **Se algum agente resolve skill do `SkillRegistry` em runtime** (21 releases no banco; os únicos chamadores
   medidos são `gateway_cutover.py:153` e `auxiliaries/factory.py:333`). Decide §6.1.
8. **O custo da extração assistida** — nenhum orçamento de tokens por documento foi medido.

---

## 6. Armadilhas que o aquecimento tem de refutar

1. *"O corpus de condições gerais mora em `documents`, e `doc_kind` é coluna de lá."* **Não.** (M7)
2. *"A ligação apólice → condição geral pelo processo SUSEP já casa hoje."* **Não casa — e está bloqueada.** (D3, C11)
3. *"O pedaço indexado tem página, então a citação sai de graça."* **Não tem.** (C26, C43)
4. *"Criar `curation_status` é necessário porque não há fila de curadoria."* **Há.** (C29)
5. *"`insurer_key` é uma chave só, é só usar."* **São quatro, e duas já discordam.** (M3, M2)
6. *"Apagar `assistance_policy.py` é o conserto."* Apagar derruba o guarda de `nodes.py:307` junto. (C09, §6.5)
7. *"Basta ligar `citations: true` na API e a base fica certa."* A garantia é de **ponteiro válido**, não de
   afirmação correta. (§16 ②)
8. *"A condição geral atual da seguradora serve para qualquer apólice dela."* O próprio código avisa que não. (C32)
9. *"`doc_kind` já filtra a busca."* Não está no índice de payload nem na assinatura. (C44, C45)
10. *"É PADRÃO, então a migration é rotina."* A de §11.2 altera uma **trava** de tabela viva e **classe
    SEM_ARQUIVO** — piso CRÍTICO e manifesto completo. (C55, §11.2)

---

## 7. As três referências externas — reabertas em 13/09/2026

| # | URL | reaberta | o ponto que a SPEC §16 modela |
|---|---|---|---|
| ① | https://www.w3.org/TR/prov-o/ | 13/09/2026 | `wasQuotedFrom` + `wasAttributedTo` na mesma linha: de onde veio **e** quem publicou |
| ② | https://platform.claude.com/docs/en/docs/build-with-claude/citations (301 de `docs.anthropic.com`) | 13/09/2026 | *"citations are guaranteed to contain valid pointers to the provided documents"*; `page_location` com `start_page_number` *"1-indexed"*, ao lado de `char_location` e `content_block_location` |
| ③ | https://arxiv.org/abs/2305.14627 (Gao, Yen, Yu, Chen · EMNLP 2023) | 13/09/2026 | *"automatic metrics along three dimensions — fluency, correctness, and citation quality"*; 📊 *"on the ELI5 dataset, even the best models lack complete citation support 50% of the time"* |

⚠️ A ② redireciona (301) de `docs.anthropic.com` para `platform.claude.com`. **Registrar o redirect**, não trocar a
URL em silêncio. O pesquisador do executor reabre as três e escreve a data da reabertura dele.

---

## 8. Regra de integridade

Este pacote é **evidência para conversão**, não relatório de execução. Toda linha marcada **CONFERIDO** foi
reaberta em 13/09/2026 sobre `a0bb5fe`; toda marcada **MEDIDO** tem a consulta acima. **O número do executor
vence** (protocolo §5 ①) — e a divergência vai escrita, nunca corrigida em silêncio.
