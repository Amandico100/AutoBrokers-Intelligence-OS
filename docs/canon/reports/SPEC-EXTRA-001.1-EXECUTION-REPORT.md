# Relatório de execução — SPEC-EXTRA-001.1: A apólice certa, inteira, em uma rodada

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `cff20ef`

```
OUTCOME ..............  pergunta sobre apólice (chat core e atendimento) → resposta na PRIMEIRA rodada, da apólice VIGENTE do
                        ramo deduzido, INTEIRA (cadastro + PDF reconciliados), com a origem escrita ao lado de cada linha
RISCO ................  7 = ALCANCE 3 (o segurado lê no WhatsApp) + REVERSIBILIDADE 2 (facts em memória; cache 180 s; 8 linhas
                        de `agents.llm_max_tokens` com backup) + FREQUÊNCIA 2 (toda pergunta de apólice) — recontado: fica 7
SUPERFÍCIE ...........  3 — 📊 BLOCO 0 achou chamadores do fornecedor FORA da lista da proposta: `app/comercial/*` (41 menções, SPEC-081/094,
                        legítimo e separado) e `billing_collection.py:1205` (001.6). Allowlist ESCRITA com motivo por linha (§1.3)
PISO APLICADO ........  §3.2 — migration que ALTERA DADO (8 linhas) + texto que chega ao segurado → CRÍTICO independente da conta
NÍVEL ................  CRÍTICO · laço curto (D-PILOTO-20): builders Opus · juiz fresco Opus + 3 perguntas adversariais · lente do DADO
UNIDADES .............  B0 medir · A porta+modelo+2 adaptadores+reconciliar · B vigência/ramo na porta · C briefing/guarda/prompt ·
                        D PDF sempre + campos ignorados + parser das tabelas reais · E teto de contexto/tokens/rastro/harness
COESÃO ...............  A é hub (policy_data_provider.py + policy_facts.py): UM dono, primeiro. B, C, D consomem A → SERIAL. E disjunta
PARALELISMO REAL .....  E ∥ A; depois B → C → D (B/C/D tocam infocap_tool.py e nodes.py). ≤ 3 agentes ao mesmo tempo
TIME .................  orquestrador Fable · builders Opus 5 (A, E, B, C, D) · juiz fresco Opus 5 · lente do dado Opus 5
REFERÊNCIA ...........  interna: `brokerage_analytics_provider.py` + `test_o_pulso_360_nao_pertence_a_infocap.py` (a porta que já passou);
                        `test_a_apolice_responde_item_por_item.py` (bf963b0). externa: as 5 de §16 da proposta (Cockburn, ACL, PEP 544,
                        PROV-O, Lost in the Middle)
GATES ................  GA, GB, GC, GD, GE, G-MIG, G-CANÁRIO da proposta §11 + 12 guardas com mutação vermelha + suíte + `git push`
O ELO ................  "a resposta vem errada PORQUE a porta é um cano": A medido (📊 7 de 7 respostas listaram, 31 linhas, 24 com fim
                        de vigência passado) · B medido (`lookup()` devolve o dict do fornecedor; `ambiguous_policy` por contagem pura em
                        `infocap_connector.py:1316`) · B CHEGA em A ✅ (o briefing `:405` imprime `matches` cru com `policy_status` "ativo"
                        em apólice vencida — 📊 golden: 3 residenciais HDI todas "ativo", só 1 vigente)
FAIXA DE RELÓGIO .....  💭 8–12 h declarada · real: em curso (início 14/09 ≈ 06:10 UTC)
ORÇAMENTO ............  💭 ≤ 1 M de subagentes (teto do laço curto) · gasto: em curso
BLOCKER (o que é) ....  muda um byte do que o CORRETOR lê, o SEGURADO recebe ou o BANCO guarda (protocolo §2)
```

### 🔴 As três perguntas que fecham o card
```
① o PAINEL rodou?            (preenche no fim) laço curto: juiz fresco + lente do dado
② a AUDITORIA / juiz fresco? (preenche no fim)
③ pendências por VALOR MARGINAL: (preenche no fim)
```

**Produto:** AutoBrokers Intelligence OS
**SPEC:** proposta `docs/canon/specs-propostas/SPEC-EXTRA-001.1-a-apolice-certa-inteira-em-uma-rodada.md` (executada como está — D-PILOTO-20: sem conversão; o MODELO de abertura prevalece sobre o prompt individual)
**Branch:** `feat/extra-001-1-apolice`
**Worktree:** `AutoBrokers-FIX` (📊 preflight 14/09/2026: `git fetch origin` · `HEAD..origin/main` = **0** · `origin/main..HEAD` = **0** · HEAD = `cff20efbfd320f0624d1914fb9c9f743a6807a4f` · `git status --short` limpo)
**Executor:** Fable 5.1 (orquestrador) · Opus 5 (builders, juiz fresco, lente do dado)
**Início:** 14/09/2026
**Commit inicial:** `cff20efbfd320f0624d1914fb9c9f743a6807a4f`
**Commit final:** (preenche no fim)
**Estado final:** EM EXECUÇÃO

---

## 0. Declaração de integridade

- [x] Nenhum motor paralelo foi criado: a porta é `backend/app/providers/policy_data_provider.py` (a que existe desde a SPEC-016 E5); nenhum `backend/app/services/policy_provider/`; nenhum segundo catálogo (a chave é `docs/canon/providers/susep/*.json` via `susep_ses_provider.coenti_de/cogrupo_de`); nenhum segundo caminho de leitura documental (`policy_document_evidence_service`); nenhum segundo registro de tool call (`tool_invocations` via `RegistroDeInvocacao`).
- [ ] Nenhuma migration existente foi movida, renomeada, apagada ou reaplicada.
- [x] Nenhum DDL monolítico foi aplicado.
- [x] Nenhum segredo foi exposto (TESTE-A/TESTE-B só por alias; o golden persistido sem nome, documento, número de apólice ou referência técnica; o corpus de perguntas com `[CPF]`/`[CNPJ]`/`[NOME]`).
- [ ] Nenhum escopo foi reduzido sem decisão registrada.
- [ ] Nenhum dado atravessou tenants.
- [x] `CLAUDE.md`, protocolo §0–§3/§5/§7.3, proposta inteira, research pack §1/§3.3/§6–§9, D-PILOTO-08/11/14/16/20, `MIGRATIONS-AUTHORITY.md` §1–§3, diagnóstico §1.1–§1.3, MODELO de abertura e prompt individual §6 lidos no início.

## 0.1 O PROTOCOLO AAA — as duas contas, a referência e o laço

| unidade | ALC | REV | FREQ | RISCO | SUP | piso? | time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| A porta + modelo + adaptadores + reconciliar | 3 | 2 | 2 | 7 | 3 | §3.2 (texto ao segurado) | builder Opus · verificador · juiz + lente |
| B vigência e ramo na porta | 3 | 2 | 2 | 7 | 2 | idem | builder Opus · verificador · juiz |
| C briefing, guarda de `nodes.py`, `CORE_BASE_PROMPT` | 3 | 1 | 2 | 6 | 2 | idem | builder Opus · verificador · juiz |
| D PDF sempre + campos ignorados + parser das tabelas reais | 3 | 2 | 2 | 7 | 2 | idem | builder Opus · verificador · juiz + lente |
| E teto de contexto · migration · piso · rastro · harness | 2 | 2 | 2 | 6 | 2 | migration altera DADO | builder Opus · verificador · juiz + lente (VERIFY) |

**Referência que o juiz abre:** `backend/app/providers/brokerage_analytics_provider.py` (porta que passou no gate da 094) e `backend/tests/test_o_pulso_360_nao_pertence_a_infocap.py` (o molde: asserção estrutural + `grep` no texto + comportamento com fixture de 4 conexões).

**Telemetria (5 linhas, preenche no fim):** tokens do orquestrador · tokens dos subagentes · relógio · rodadas de bateria · nº de guardas/mutações.

---

## 1. BLOCO 0 — o que foi medido antes de qualquer código (14/09/2026, sobre `cff20ef`)

### 1.1 Preflight (saída real)
```
git fetch origin                          (ok)
git rev-list --count HEAD..origin/main    0
git rev-list --count origin/main..HEAD    0
git branch --show-current                 feat/extra-001-1-apolice   (criada a partir de main = cff20ef)
git rev-parse HEAD                        cff20efbfd320f0624d1914fb9c9f743a6807a4f
git status --short                        (limpo)
```

### 1.2 A matriz `premissa → observação nova → comando/consulta → decisão`

| # | premissa da proposta (13/09, `a0bb5fe`) | observação de 14/09 (`cff20ef`) | comando / consulta | decisão |
|---|---|---|---|---|
| 1 | a porta existe em `policy_data_provider.py` (149 linhas; `lookup`, `detail`; `vehicle` só na concreta) | ✅ **confere**: 149 linhas; `Protocol` :41 com `lookup` :46 e `detail` :50; `vehicle` só em `InfocapPolicyDataProvider` :112; registry :134–149 | `sed -n 1,149p backend/app/providers/policy_data_provider.py` | evoluir o arquivo; nada em `services/policy_provider/` (📊 `ls` → não existe) |
| 2 | 5 módulos, 8 pontos de chamada | ✅ **confere** com uma correção de linha: `billing_collection.py` chama em **:1205/:1208/:1212** (a proposta dizia :793/:797 — o arquivo cresceu na 001.6) | `grep -rnE "get_policy_data_provider\|provider\.(lookup\|detail\|vehicle)" backend/app` | item 7 da tabela §5.1.1 continua NÃO migrando (001.6) |
| 3 | `hasattr(provider, "vehicle")` é o contrato de verdade | ✅ **confere e são 4**: `infocap_tool.py:259`, `insurer_dispatch_tool.py:971`, `portal_tool.py:347`, `vehicle_tool.py:58` | `grep -rn "hasattr(provider" backend/app` | os 4 saem no BLOCO D; GATE A1 exige 0 |
| 4 | fronteira: quem importa `infocap_connector` fora de `providers/` | 📊 **4 arquivos de produto**: `infocap_tool.py` (:582, :622, :650 — `_display_policy_number`, `_format_policy_options_for_summary`), `main.py:289` (o router — legítimo), `comercial/fonte_infocap.py:6` (docstring) e `billing_collection.py:1805` (comentário). `canario_095.py` é script | `grep -rn "infocap_connector" backend --include=*.py \| grep -v providers/ \| grep -v infocap_connector.py` | **allowlist escrita (§1.3)**: `main.py` (router). Os 3 imports de `infocap_tool.py` migram para a porta (BLOCO B/C) |
| 5 | campos de fornecedor fora da fronteira | 📊 **9 arquivos, 54 menções**: `comercial/fonte_infocap.py` 33 · `policy_document_evidence_service.py` 6 (`codfil`/`nosnum` na chave de cache e na redação) · `policy_facts.py` 4 (hash do locator) · `comercial/metricas/carteira.py` 4 · `comercial/manifesto.py` 2 · `infocap_tool.py` 2 (:61 descrição do `policy_ref`; :469 "não exponha nosnum") · `policy_answer_composer.py` 1 (docstring) · `comercial/metricas/registry.py` 1 · `executive_intelligence.py` 1 (docstring) | `grep -rniE "preliq\|nosnum\|codfil\|sit_renovacao_txt\|tabela_itens\|forma_pag\|inivig\|fimvig" backend/app --include=*.py \| grep -v providers/ \| grep -v infocap_connector.py` | 🔴 **DIVERGE (D1)**: a proposta previa 0 fora de `providers/`; há um segundo domínio inteiro (`app/comercial/*`, SPEC-081/094 — é o adaptador de ANALYTICS, outra porta, fronteira própria já gateada). A allowlist da 001.1 vale para a superfície de APÓLICE: `app/comercial/**` fica FORA da medição (motivo: outra porta); `codfil`/`nosnum` no hash do locator de `policy_facts.py` e `policy_document_evidence_service.py` são o locator OPACO (motivo: é a chave técnica que a própria porta define em :23). Superfície do card sobe a **3** |
| 6 | `prompts.py`: 8 linhas, 10 ocorrências (9 prosa + 1 identificador), `CorpAPI` 0 | ✅ **confere exatamente**: linhas 31, 37, 40, 42, 47, 131 (2), 133 (2), 193; `-i` = 10; `CorpAPI` = 0 | `grep -nE '\bInfoCap\b' backend/app/core/prompts.py` · `grep -o -i infocap … \| wc -l` | 9 de prosa saem (BLOCO C); `infocap_policy_lookup` na allowlist escrita do teste |
| 7 | `policy_facts.FACT_SOURCES` tem `infocap_structured`; fatos só em memória | ✅ 3 escritores em `policy_facts.py` (:120, :132, :265) + 2 leitores em `policy_answer_composer.py` (:103, :170). 📊 **nenhuma tabela persiste facts** (`grep -rn "policy_facts\|fact_type" backend/app --include=*.py` → só esses dois módulos + nodes/infocap_tool via composer) | grep | renomear expand-first sem backfill de banco (não há dado persistido) — BLOCO A |
| 8 | `agents`: 8 agentes, 4 core + 4 attendance, `llm_max_tokens` ∈ {1200×4, 2000×4} | ✅ **confere**: (attendance,1200,1) (attendance,2000,3) (core,1200,3) (core,2000,1). 📊 `companies.llm_max_tokens` = **2000 em 5 de 5** corretoras | `SELECT agent_role, llm_max_tokens, count(*) FROM agents GROUP BY 1,2` · idem em `companies` | migration §11.1 vale como está (a contagem bate → o ROLLBACK está atualizado) |
| 9 | default 2000 em 4 lugares | 📊 **5**: `schema_completo.sql:454`, `:581`, `agent_config.py:76/:133/:281`, `models/agent.py:19` **e `app/api/admin/sandbox/bootstrap-tenant/route.ts:106` = 1200** (o tenant de sandbox nasce com 1200) | grep `llm_max_tokens` em backend e app/ | os de CÓDIGO mudam para 8192 (BLOCO E); o DDL fica registrado como pendência (o código nunca deixa o banco decidir para quem conversa: piso) |
| 10 | quem lê `companies.llm_max_tokens` | 📊 **2 leitores**: `llm_factory.py:84` (fallback quando o agente não tem valor — e o piso só cobre `core`/`attendance`; auxiliar e subagente herdam o 2000 DE PROPÓSITO) e `agent_config.py:280` (tela da config da corretora) | grep | **decisão (§9): NÃO subir `companies`** — subir mudaria o teto de auxiliares/subagentes, que a `llm_factory` mantém baixo de propósito. Nota: deixar 70 · subir 55 |
| 11 | `PAPEIS_QUE_CONVERSAM = ("", "core", "attendance")`; `insured_external` fora; 0 agentes vivos desse papel | ✅ **confere** (`llm_factory.py:35`); 📊 0 agentes `insured_external` na base | sed + SELECT | ESSENCIAL latente, fecha no BLOCO E com M-E2 |
| 12 | `messages.payload.turn` sem chave de ferramenta | ✅ **confere**: chaves `stages, status, attempt, ttft_ms, total_ms, artifacts, error_code, client_request_id` (+ `usage, truncated, continuations, finish_reason` em turnos recentes). 📊 `tool_invocations` **existe**: 277 linhas, 140 desde 09/09; colunas medidas (id, company_id, work_run_id, work_step_id, work_attempt_id, skill_release_id, tool_release_id, capability_key, agent_id, user_id, connection_id, invocation_key, status, input_fingerprint, input_summary, output_summary, provider_reference, approval_request_id, work_effect_id, started_at, finished_at, latency_ms, cost_amount, currency, error_code, trace_id, created_at); constraints `uq_tool_invocations_key (company_id, invocation_key)`, `ck_tool_invocations_status`, FKs para companies/skill_releases/tool_releases/work_effects; 7 índices | `information_schema.columns`, `pg_constraint`, `pg_indexes` | P-PILOTO-18 é REESCRITA (o registro existe; falta a ligação com o turno); a DDL entra no `MANIFEST.md` como NÃO RASTREADA (BLOCO E) |
| 13 | 🔴 `tool_invocations` guarda argumento cru? | 📊 **NÃO**: amostra das 40 últimas — `input_summary` de `operational.infocap.policy_lookup.read` tem só as CHAVES (`document`, `user_query`, `policy_number`, `document_evidence_requested`); 📊 linhas com 11 dígitos seguidos em `input_summary`: **0 de 277** | `SELECT … jsonb_object_keys(input_summary)` · `input_summary::text ~ '\d{11}'` | não há P1; vira guarda de bloco (E) |
| 14 | os 4 guardas de P-PILOTO-20 quebram por import | ✅ **confere**: `python tests/test_infocap_policy_output_guard.py` e `test_spec016_policy_intelligence.py` → `ModuleNotFoundError: app.agents.honestidade_do_handoff` (o stub `app.agents.__path__=[]`). ⚠️ São scripts (`check()`), em `collect_ignore` do `conftest.py` — o pytest não os coleta; quem os roda é o meta-guarda | comando | harness registra o módulo real no stub (BLOCO E) |
| 15 | acervo: 7 de 7 listaram vencidas (31 linhas); 5 de 7 perguntaram; 2 em 1 rodada | 📊 **7 respostas com lista** (`role='assistant'`, 09–11/09, casando `mais de uma apólice\|qual delas\|responda com o número`); **31 linhas de opção** (4+2+3+11+6+3+3 — ⚠️ uma resposta tem 11 linhas: 10 apólices + a linha "recomendo a vigente"); **24 linhas com fim de vigência passado**, 7 vigentes; **7 de 7 perguntaram** "qual" (a proposta dizia 5 — o número de hoje vence); 0 de 7 responderam a única vigente | consulta com `regexp_split_to_table` sobre `messages.content`, contando datas `a DD/MM/YYYY < created_at` — conteúdo nunca sai da consulta | corpus das 7 perguntas gravado em `backend/tests/corpus/perguntas_do_chat/2026-09-09_10.json` (só as perguntas, `[CPF]`/`[CNPJ]`/`[NOME]`). 🔴 **DIVERGE (D2)**: 3 das 7 são de **09/09**, 4 de 10/09 |
| 16 | turnos "ainda não recebi uma pergunta sua": 2, os maiores (120/128 chunks) | 📊 **2 turnos**: 09/09 11:32 (117 s) e 10/09 12:47 (86 s). ⚠️ `payload.turn.stages` = `[]` e `usage` ausente nos dois; `token_usage_logs` de 08–12/09 não tem chamada de chat acima de 63k tokens (as maiores são `service_type='memory'`); não há tabela de chunks no Postgres (Qdrant) | consultas em `messages` e `token_usage_logs` | 🔴 **DIVERGE (D3)**: os tamanhos 120/128 chunks e 135k/163k tokens **não são reconstruíveis pelo banco hoje** (vieram dos laudos I1/I2 sobre logs). O guarda M-E1 usa um turno SINTÉTICO do tamanho declarado (≥ 128 chunks; ≥ 160k tokens de contexto medidos no próprio teste), e a proposta de gravar o tamanho do bloco RAG no `payload.turn` vira parte do BLOCO E (para o próximo laudo medir) |
| 17 | golden HDI: 6 garantias no cadastro, 10 linhas no PDF, Σ R$ 70,29 × preliq R$ 306,60, franquia Danos Elétricos 550 × 600 | ✅ **confere, pela porta** (conector implantado, em memória): cadastro **6** (Incêndio 133.000 · Roubo · Equip. Eletrônicos · Vidros · RC Familiar · Danos Elétricos 3.000 — Σ prêmios **R$ 70,29**), `preliq` **R$ 306,60**, franquia Danos Elétricos `10.00%-550,00`; PDF (6 páginas, `direct_text`): **10 linhas** (Incêndio 45,64 · RC Familiar 11,50 · Danos Elétricos 17,25 · Vidros 11,50 · Ruptura de Tubulações 19,88 · Roubo e Furto 11,50 · Vendaval 47,36 · Equip. Eletrônicos 11,50 · Valor Novo 4,53 · **Assistências Essenciais 125,94**) — Σ **R$ 306,60 = preliq**; 6 franquias em prosa (a 2ª: "10% … mínimo R$ 600,00"); **4 parcelas "Cartão de Crédito"** × cabeçalho `forma_pag` "Boleto Bancário" | `scratch/golden_pela_porta.py` → `POST /attendance/connectors/infocap/lookup` com chave interna; golden persistido em `backend/tests/fixtures/golden_apolices_extra0011.json` (sem PII, asserção de ausência no montador) | golden fixado. 🔴 **DIVERGE (D4)**: o extrator documental (`_COVERAGE_ROW_RE`, exige `R$`) produz **0 `coverage_row`** no PDF da HDI (as linhas são `<rótulo> <LMI>   <prêmio>` sem `R$`): as "10 linhas" existem no `document_text`, não nos `evidence_items`. O BLOCO D tem de ensinar o parser a ler os DOIS layouts reais — sem isso, "10 de 10" é impossível |
| 18 | golden Allianz condomínio: 15 coberturas; "apólice de controle em que a soma bate" | 📊 cadastro **15** (Σ prêmios **R$ 17.973,02**), `preliq` **R$ 24.960,60** → **28% faltando**; PDF (5 páginas): **21 linhas** (as 15 + Alagamento, Perda/Pagamento Aluguel, RC Guarda Veículos, Roubo de Bens de Condôminos, Ruptura de Tanques, Gastos com Defesa, Assistência 24h R$ 23,88) — Σ **R$ 24.960,60 = preliq**; parcelas 6× boleto (cabeçalho e parcelas concordam) | idem | 🔴 **DIVERGE (D5)**: a Allianz **não é** a apólice de controle — o contador acende nela também (R$ 6.987,58). A apólice reconciliada tem **21** coberturas, não 15. O par de controle de M-A3 passa a ser: cadastro cuja Σ bate com `preliq` (fixture de controle) × HDI/Allianz reais (acende). E o extrator também falha no layout da Allianz (`<rótulo> R$ <LMI> R$ <prêmio> <franquia "20 4.000,00" \| "- Sem Franquia" \| "- 168 Hrs">`): só 1 `coverage_row`, e é **"Prêmio Líquido"** (uma linha de prêmio lida como cobertura) |
| 19 | cliente com 11+ apólices não é hipótese | 📊 **confere no acervo**: a empresa da pergunta q4 tem `documents_count` **11** e `matches` **10** (truncamento real em `infocap_connector.py:1326`); a vigente está na posição 1 hoje | golden `listagens.empresa_11_apolices` | M-B1 usa o caso real (11/10) + o caso sintético (12 com a vigente na 11ª) |
| 20 | conexões InfoCap da Resulta: 3 (2 arquivadas, 1 inválida) + ativa | 📊 Resulta (`04b5cdbc`): **4** conexões — 3 `archived` (2 sem segredo, 1 `invalid_credentials`) + 1 `connected/healthy`; `6c9c55e2`: 1 `connected`; `3aa75902`: 1 `archived` | `tenant_connections ⋈ connector_templates` | a fixture de dois tenants de M-A4 modela exatamente isto |
| 21 | `nodes.py:1009-1018` só concatena as 3 humanas para atendimento; `core` recebe a última | ✅ **confere** (`:1011` `if _role in ("attendance","insured_external")`); `_client_facing` em `infocap_tool.py:128` tranca a auto-seleção (`:197`) | sed | estender a condição (BLOCO B) |
| 22 | `chaveiro` só em `_AUTO_INTENT_RE` | ✅ **confere** (`:27`); `_RESI_INTENT_RE` tem `fechadura da porta` (:30–32); `_product_hint_from_query` testa AUTO primeiro | sed | BLOCO B com desempate |
| 23 | briefing `:405` (opcoes_de_apolice) · `:465` (1b coberturas FICA) · `:467` (3. liste TODAS SAI) · `:453` (segurado, já certo) | ✅ **confere linha a linha** (`:405`, `:453`, `:465`, `:467`) | sed | BLOCO C |
| 24 | `nodes.py:263-273` anula resposta sem todas as opções; `:273` tem `and`/`or` de precedência duvidosa | ✅ `:263–:273`. A linha `:273` lê `not options and ("seguradora" not in lower or ("numero" not in lower and "número" not in lower))` — com `policy_options` vazio ela ANULA qualquer resposta que não tenha "seguradora" E "número" — o comportamento é medido por teste no BLOCO C antes de tocar | sed | BLOCO C |
| 25 | `policy_document_evidence_requested` por palavra-chave; `explicit` existe | ✅ `:132–:136`; `_INTENT_TERMS` a partir de `:47` | sed | BLOCO D |
| 26 | `graph.py` concatena o RAG cru sem teto | ✅ `:1377` (`rag_prefetch_content = rag_result.get("content") or ""`), `:1394–1405` (bloco), `:1515` (`composite_prompt = static_prompt + dynamic_context`), `:1517` `messages = [SystemMessage(composite_prompt), HumanMessage(user_message)]` | sed | ⚠️ a pergunta já é a ÚLTIMA mensagem (`HumanMessage` depois do `SystemMessage`); o que a proposta chama de "repetir depois do bloco" é repeti-la DENTRO do prompt de sistema, depois do bloco recuperado — e o teto declarado. BLOCO E implementa os dois e mede |
| 27 | catálogo nosso: `seguradora-coenti.json` (siglas 61) e `ramo-cogrupo.json`; leitor `susep_ses_provider` | ✅ 15 seguradoras canônicas, **61 siglas** (14 com coenti; 12 da carteira sem coenti listadas como UNKNOWN), placar 83,86%; 50 ramos, 22 grupos; `coenti_de` :258 e `cogrupo_de` :233 por IGUALDADE | python + sed | pendurar; `policy_catalog.py` só se provar necessidade (BLOCO A decide e escreve) |
| 28 | linha de base da suíte | 📊 mesma árvore da 001.6 (`cff20ef`): **1094 passed · 14 failed · 48 errors · 37 xfailed · 1 xpassed**, com as 14 triadas nominalmente no relatório da 001.6 §5.5 (nenhuma desta superfície; `test_a_resposta_chega_inteira` e `test_o_corpus_nao_vaza_pii` estão entre as pré-existentes e SÃO desta superfície → serão remedidas isoladas antes de tocar) | relatório 001.6 §5.5 (rodada de 14/09 03:46–04:11 UTC) | reaproveitada: a árvore não mudou entre a rodada e este BLOCO 0 |
| 29 | verificador de tipos para o GATE A1 | 📊 `mypy` e `pyright` **ausentes** na máquina; `mypy 2.3.1` instalado agora (`pip install mypy`) | comando | o GATE A1 roda `mypy` em subprocesso quando presente E o registry recusa adaptador incompleto em runtime (`register_policy_data_provider` → `ValueError` com a lista dos membros faltantes) — a segunda prova vale onde o `mypy` não existir |

### 1.3 A fronteira, escrita como allowlist (proposta §3.2)

| linha | motivo | quem tira |
|---|---|---|
| `backend/app/main.py:289,292` importa `app.api.infocap_connector.router` | é o roteador HTTP do conector (a API administrativa do próprio conector), não um consumidor de dado | ninguém — é a porta HTTP |
| `backend/app/comercial/**` conhece `inivig`/`fimvig`/`nosnum` | é o ADAPTADOR DE ANALYTICS da SPEC-081/094 (`fonte_infocap.py`), outra porta com fronteira própria já gateada (`test_o_pulso_360_nao_pertence_a_infocap.py`) | fora da superfície de apólice |
| `policy_facts.py:61-65` e `policy_document_evidence_service.py:119-123,462` usam `codfil`/`nosnum` | é o hash do **locator opaco** (`"<provider>:<parte>:<parte>"`, definido pela própria porta em `policy_data_provider.py:23`) e a lista de chaves REDIGIDAS da saída — não é leitura de dado do fornecedor | BLOCO A troca por `parse_policy_locator_ref` onde couber; o que sobrar fica com o motivo |

A allowlist tem 3 linhas — no limite que a proposta fixa para "a fronteira está no lugar certo".

### 1.4 Divergências entre a proposta e a árvore (o número de hoje vence)

| id | divergência | consequência |
|---|---|---|
| **D1** | campos de fornecedor fora de `providers/`: 54 menções em 9 arquivos, dominadas por `app/comercial/*` (outra porta) | allowlist §1.3; superfície 3; M-A1 mede a superfície de APÓLICE (`app/agents/**`, `app/services/policy_*`, `app/core/prompts.py`) |
| **D2** | as 7 perguntas reais são de 09/09 (3) e 10/09 (4), não "de 10/09" | corpus nomeado `2026-09-09_10.json` |
| **D3** | o tamanho dos dois turnos grandes não é reconstruível pelo banco | M-E1 sobre turno sintético ≥ 128 chunks; BLOCO E grava `rag_chunks`/`rag_chars` no `payload.turn` para o próximo laudo |
| **D4** | o extrator documental não lê a tabela da HDI (sem `R$`) nem a da Allianz (franquia "20 4.000,00"): 0 e 1 `coverage_row` (a única é "Prêmio Líquido") | BLOCO D ganha o parser dos dois layouts reais (ESSENCIAL — `CHANGE-ADDENDA`); sem ele o golden 10/21 é impossível |
| **D5** | a Allianz condomínio tem 21 coberturas no PDF (15 no cadastro) e Σ cadastro = 72% do `preliq`: NÃO é apólice de controle | golden reconciliado Allianz = **21**; par de controle de M-A3 = fixture sintética cuja Σ bate |
| **D6** | `billing_collection.py` chama a porta em :1205–:1212 (não :793–:797) | nada muda: o item 7 continua da 001.6 |
| **D7** | 7 de 7 perguntaram (não 5 de 7) | o número de hoje |
| **D8** | o default 2000/1200 mora em 5 lugares (o 5º é `app/api/admin/sandbox/bootstrap-tenant/route.ts:106`) | BLOCO E corrige os de código; toca `app/` → `test:rotas-montam` + `next start` no fim |
| **D9** | `companies.llm_max_tokens` = 2000 em 5/5 e é lido pela `llm_factory` como fallback de TODOS os papéis | decisão: não subir (§9) |
| **D10** | a pergunta do usuário já é a última mensagem do turno (`graph.py:1517`) | "repetir depois do bloco" = dentro do prompt de sistema, depois do bloco recuperado, com teto declarado (E) |

### 1.5 As 15 linhas do aquecimento (o que vou construir, em que ordem, e o que ainda não sabia)

1. A porta `PolicyDataProvider` já existe (SPEC-016 E5) e é um cano: devolve o dict da InfoCap; 5 módulos e 8 pontos de chamada falam com ela; `vehicle` só existe por `hasattr`.
2. Evoluo o arquivo que existe: modelo canônico com origem por campo (`CampoComOrigem` que não nasce sem origem), 5 operações + `capacidades()` + 3 depreciados no `Protocol`, dois adaptadores (InfoCap envolvendo o conector; PdfOnly), `reconciliar` puro na porta.
3. O golden foi montado pela porta: HDI 6 × 10 (Σ PDF = preliq), Allianz 15 × 21 (Σ PDF = preliq) — e o contador de prêmio acende nas duas (77% e 28% faltando).
4. O extrator documental não lê nenhuma das duas tabelas reais: é o defeito material que a proposta não apontava (D4) e vai para o BLOCO D.
5. Vigência: `ambiguous_policy` nasce por contagem pura no conector (`:1316`) e a lista é truncada em 10 (📊 real: 11 → 10); a classificação por data já existe no compositor (`_real_vigencia`) e sobe para a porta lendo a lista inteira, com `historico_oculto` de `documents_count`.
6. Ramo: a auto-seleção está trancada em `_client_facing`; o `core` recebe só a última humana (`nodes.py:1011`); `chaveiro` só no regex de auto — estendo condições, não reescrevo funções.
7. Briefing: `:405`/`:467` saem (listar apólices), `:465` fica (listar coberturas), `:453` já está certo; o guarda de `nodes.py:263` fica e passa a guardar só `ambiguous_policy` legítimo; `:273` é medido por teste antes de tocar.
8. `CORE_BASE_PROMPT` ganha a regra de vigência em uma frase; as 9 prosas "InfoCap" saem; `infocap_policy_lookup` fica na allowlist escrita (o rótulo da tela é "apólice").
9. PDF lido sempre que a tool de apólice é chamada (pelo destino, não por palavra), com a linha de controle "quantos clientes eu tenho?" que NÃO lê.
10. `forma_pag` do cabeçalho mente (boleto × 4 parcelas no cartão): a forma de pagamento vem das parcelas; `observacoes`, `sit_renovacao_txt`, `sit_sinistro_txt`, `tabela_itens` viram campos com origem.
11. BLOCO E: teto declarado no bloco RAG + pergunta repetida depois dele; migration de dado (8 linhas, backup, ROLLBACK exato); `insured_external` no piso; `tool_invocations` ligada ao turno (sem PII — 📊 0 de 277 com 11 dígitos); harness dos 4 guardas de P-PILOTO-20.
12. Ordem: A ∥ E → B → C → D; juiz fresco + lente do dado; conserto único; suíte; push.
13. Não sabia e medi: (a) a fronteira tem um segundo domínio (`app/comercial`) — allowlist de 3 linhas; (b) o tamanho dos turnos grandes não está no banco — turno sintético; (c) a Allianz não é controle — fixture sintética.
14. Não consigo provar sem o Implantar: o canário vivo (7 casos) — fica nomeado como pendente, como na 001.6.
15. As duas afirmações falsas do prompt individual: (1) "a porta não existe" — refutada por `find`/`grep` (149 linhas, 8 chamadores); (2) "tirar todas as 'liste TODAS' conserta" — refutada por `sed -n 465,467p` (duas linhas de distância; a de `:465` é a das coberturas, apagá-la reintroduz o 6 de 10).

---

## 2. BLOCO A — a porta (preenche ao fechar o bloco)

## 3. BLOCO E — contexto, tokens, rastro, harness (preenche ao fechar o bloco)

## 4. BLOCOS B, C, D (preenche ao fechar cada bloco)

## 5. Migrations (APPLY / VERIFY / ROLLBACK)

## 6. Painel: juiz fresco + lente do dado · conserto · suíte

## 7. Canário (depois do Implantar)

## 8. O que ficou fora e por quê

## 9. Decisões tomadas com nota (regra do Founder: escolher, anotar, avisar no fim)

| id | decisão | opções e notas | por quê |
|---|---|---|---|
| **D-E0011-01** | `companies.llm_max_tokens` NÃO sobe na migration | deixar **70** · subir para 8192 **55** | 📊 é o fallback da `llm_factory` para TODOS os papéis; o piso só cobre quem conversa de propósito — subir mudaria auxiliar/subagente |
| **D-E0011-02** | o extrator documental ganha os dois layouts reais (HDI sem `R$`; Allianz com franquia "pct valor") — ESSENCIAL fora do texto da proposta | fazer no BLOCO D **90** · registrar como pendência **30** (o golden 10/21 seria impossível e o outcome "inteira" não se cumpre) | D4 |
| **D-E0011-03** | golden reconciliado da Allianz = 21 (PDF), não 15 (cadastro); o controle de M-A3 é fixture sintética | 21 **95** · manter 15 **10** (seria afirmar que a apólice está inteira com 6 coberturas a menos) | D5 |
| **D-E0011-04** | M-E1 usa turno sintético ≥ 128 chunks (tamanho declarado) e o BLOCO E passa a gravar o tamanho do bloco RAG no turno | sintético **80** · esperar o próximo turno grande real **20** | D3 |

## 10. Riscos remanescentes

## 11. Rollback

## 12. Entrega (`git push`, saída colada)
