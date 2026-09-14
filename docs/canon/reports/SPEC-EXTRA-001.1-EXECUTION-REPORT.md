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
FAIXA DE RELÓGIO .....  💭 8–12 h declarada · real ≈15 h (14/09, uma janela; duas quedas por limite de sessão retomadas no mesmo contexto)
ORÇAMENTO ............  💭 ≤ 1 M de subagentes (teto do laço curto) · gasto 📊 ≈2,9 M (A 446k · E 302k · B 381k · C 344k · D 364k · juiz 347k · lente 210k · F 465k): +190% — 5 blocos, 2 lentes e 1 conserto para uma proposta de 106 KB; o teto era de 1 SPEC média, não desta
BLOCKER (o que é) ....  muda um byte do que o CORRETOR lê, o SEGURADO recebe ou o BANCO guarda (protocolo §2)
```

### 🔴 As três perguntas que fecham o card
```
① o PAINEL rodou?            SIM — laço curto (D-PILOTO-20): juiz fresco Opus (PASS 67: 0 blocker, 4 ESSENCIAL, 5 VALIOSA, 61/61 mutações
                            reais) + lente do dado Opus (80: 1 BLOCKER que nenhum guarda via — a entrega cortava em 20; o ELO reconstruído
                            sobre o dado vivo), cegos entre si, sobre `5f84bd9`; conserto ÚNICO (Builder F: 8 achados, 44 mutações)
② a AUDITORIA / juiz fresco? SIM — o juiz fresco É a auditoria do laço curto; a lente reconstruiu 9 frentes (29 afirmações 📊) e reconferiu o
                            VERIFY da migration; o juiz reconferiu o banco e reabriu as 5 referências externas
③ pendências por VALOR MARGINAL: P-E0011-DESEMPATE-POR-LMI-INERTE (falha seguro) · P-E0011-EXTRATOR-PAGINA-UNICA (produção passa páginas reais) ·
                            P-E0011-CONTENT-HASH-COLISAO (o hash vem dos bytes) · P-E0011-OPCOES-EM-TEXTO-SOBRE-DICT (chamadores já preferem
                            o texto classificado) — nenhuma muda um byte do que chega hoje
```

**Produto:** AutoBrokers Intelligence OS
**SPEC:** proposta `docs/canon/specs-propostas/SPEC-EXTRA-001.1-a-apolice-certa-inteira-em-uma-rodada.md` (executada como está — D-PILOTO-20: sem conversão; o MODELO de abertura prevalece sobre o prompt individual)
**Branch:** `feat/extra-001-1-apolice`
**Worktree:** `AutoBrokers-FIX` (📊 preflight 14/09/2026: `git fetch origin` · `HEAD..origin/main` = **0** · `origin/main..HEAD` = **0** · HEAD = `cff20efbfd320f0624d1914fb9c9f743a6807a4f` · `git status --short` limpo)
**Executor:** Fable 5.1 (orquestrador) · Opus 5 (builders, juiz fresco, lente do dado)
**Início:** 14/09/2026
**Commit inicial:** `cff20efbfd320f0624d1914fb9c9f743a6807a4f`
**Commit final:** `3320cee` (código + relatório; o commit do dossiê vem depois)
**Estado final:** **CONCLUÍDA COM RESSALVAS** — código na `main`; migration aplicada e provada; 14 guardas novos + 1 canônico, 105 mutações com efeito; o canário vivo dos 7 casos e a validação com a atendente dependem do Implantar (P-E0011-CANARIO-VIVO-NO-IMPLANTADO)

---

## 0. Declaração de integridade

- [x] Nenhum motor paralelo foi criado: a porta é `backend/app/providers/policy_data_provider.py` (a que existe desde a SPEC-016 E5); nenhum `backend/app/services/policy_provider/`; nenhum segundo catálogo (a chave é `docs/canon/providers/susep/*.json` via `susep_ses_provider.coenti_de/cogrupo_de`); nenhum segundo caminho de leitura documental (`policy_document_evidence_service`); nenhum segundo registro de tool call (`tool_invocations` via `RegistroDeInvocacao`).
- [x] Nenhuma migration existente foi movida, renomeada, apagada ou reaplicada (1 nova, de dado: `20260914_06`; a tabela de backup permanece).
- [x] Nenhum DDL monolítico foi aplicado.
- [x] Nenhum segredo foi exposto (TESTE-A/TESTE-B só por alias; o golden persistido sem nome, documento, número de apólice ou referência técnica; o corpus de perguntas com `[CPF]`/`[CNPJ]`/`[NOME]`).
- [x] Nenhum escopo foi reduzido sem decisão registrada (o que ficou fora está em §8 com o gatilho; as decisões em D-E0011-00…18; os addenda classificados).
- [x] Nenhum dado atravessou tenants (M-A4 com dois tenants reais em fixture; `company_id` no código em todas as operações da porta; chaves de cache com tenant E conexão; juiz ② e lente confirmam).
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

**Telemetria (5 linhas):** 📊 orquestrador ≈ 1,1 M tokens de contexto acumulado (uma janela, duas retomadas) · subagentes ≈ 2,9 M (8 agentes Opus 5, ≤ 2 ao mesmo tempo) · relógio ≈15 h · bateria inteira **1 rodada** (+ os guardas-script rodados 2× pelo juiz e 3× pelo orquestrador) · **14 guardas novos + 1 canônico, 105 mutações com o efeito declarado (61 no julgamento + 44 no conserto), 0 carimbo**.

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
| 16 | turnos "ainda não recebi uma pergunta sua": 2, os maiores (120/128 chunks) | 📊 **2 turnos**: 09/09 11:32 (117 s) e 10/09 12:47 (86 s). ⚠️ `usage` ausente nos dois (📊 lente do dado: `stages` NÃO é vazio — `["policy.reading","documents.reading"]` e `["documents.reading"]` — rótulos de etapa, sem tamanho; e há turnos de 10/09 COM `usage`, mas não os dois); `token_usage_logs` de 08–12/09 não tem chamada de chat acima de 63k tokens (as maiores são `service_type='memory'`); não há tabela de chunks no Postgres (Qdrant) | consultas em `messages` e `token_usage_logs` | 🔴 **DIVERGE (D3)**: os tamanhos 120/128 chunks e 135k/163k tokens **não são reconstruíveis pelo banco hoje** (vieram dos laudos I1/I2 sobre logs). O guarda M-E1 usa um turno SINTÉTICO do tamanho declarado (≥ 128 chunks; ≥ 160k tokens de contexto medidos no próprio teste), e a proposta de gravar o tamanho do bloco RAG no `payload.turn` vira parte do BLOCO E (para o próximo laudo medir) |
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
| **D11** (lente do dado) | com marcador ESTRUTURAL (≥2 linhas com duas datas `DD/MM/AAAA` na mesma linha) o acervo de 09–11/09 tem **10 respostas, 49 linhas, 36 com fim de vigência passado** — as 7 do marcador lexical são subconjunto; 3 respostas listaram vencidas sem as palavras do regex, e uma delas respondia a pergunta de cobertura/franquia que não pedia lista. 📊 6 das 7 tinham UMA única vigente na lista e mesmo assim perguntaram | o corpus mantém as 7 (reconstruídas byte a byte pela lente); as 3 extras viram **P-E0011-ACERVO-ESTRUTURAL-10** para entrar no corpus na 001.5/001.7; o número de hoje do defeito é 10/49/36 |

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

## 2. BLOCO A — a porta (Builder A · Opus 5 · 📊 446k tokens · ≈5 h em 2 sessões, a 1ª caída por 429 e retomada no mesmo contexto)

| entrega | o que mudou | prova |
|---|---|---|
| A.1 contrato | `policy_data_provider.py` 149 → 1.471 linhas: `PolicyDataProvider(Protocol)` com `capacidades()` + 5 operações (`buscar_cliente`, `listar_apolices`, `detalhar_apolice`, `documento_oficial`, `parcelas_em_aberto`; `company_id` keyword-only e primeiro) + 3 DEPRECIADOS (`lookup`, `detail`, `vehicle`); `register_policy_data_provider` RECUSA adaptador sem os 8 membros (`ValueError` com a lista); `policy_data_providers()`; `classificar_vigencia(inicio, fim, cancelado, hoje)` pura (`policy_status` é sinal, nunca veredito) | GA1: `mypy` "Success: no issues found in 3 source files"; adaptador sem `vehicle` reprovado pelo `mypy` E pelo registry; `_REGISTRY = ['infocap', 'pdf_only']` |
| A.2 modelo canônico | no mesmo arquivo (D-A-02: 95 × módulo novo 40): `CampoComOrigem` (TypeError sem origem), `Indisponivel` próprio (D-A-03: 92 × importar da 094 25 — 📊 `evidence_pack.py:61` é `str`, `bool()` True), `Dinheiro = Decimal` (D-A-01: 90 × centavos 55), `Cobertura` (com `divergencias` tupla — D-A-07: 📊 Danos Elétricos diverge em franquia E prêmio), `Parcela`, `PlanoDeAssistencia`, `Vigencia`, `Sinal`, `ApoliceDocumental`, `LinhaDeCoberturaDoDocumento`, `SeguradoraCanonica`/`RamoCanonico` (via `coenti_de`/`cogrupo_de`; UNKNOWN com o nome listado), `Apolice`, `ApoliceNaLista`, `ListaDeApolices` (`total`, `historico_oculto`), `ResultadoDeBusca`, `CapacidadeDoProvider`; `rotulos_de_cobertura.json` (14 grupos de sinônimos, critério medido no golden) — `policy_catalog.py` NÃO existe (D-A-05: 95) | `test_toda_linha_tem_origem.py` **37/37** · 4/4 mutações vermelhas |
| A.3 `reconciliar` puro | documento vence em cobertura/limite/franquia/cláusula/exclusão/plano; sistema de gestão em parcela/quitação/status/vigência; divergência mostra as duas; contador `cadastro_incompleto` com tolerância R$ 0,05; `cabecalho_divergente` (forma de pagamento das PARCELAS); casamento por rótulo normalizado OU grupo declarado, desempate por LMI só com 1º token comum (D-A-06), nunca substring; idempotente (D-A-09) | `test_o_contador_de_premio_acende.py` **34/34** · 6/6 mutações vermelhas · 📊 pelo motor: HDI 6→10, R$ 236,31 / 77,07%; Allianz 15→21, R$ 6.987,58 / 27,99%; controle sintético apagado; franquia 550 × 600 as duas presentes; forma de pagamento Cartão |
| A.4 dois adaptadores | `infocap_policy_provider.py` (851 linhas) ENVOLVE `infocap_lookup`/`infocap_policy_detail`/`infocap_vehicle_item`; `listar_apolices` = PARCIAL até o BLOCO B ler a lista inteira (D-A-04: (c) 80 × (b) 70 × (a) 20); `pdf_only_policy_provider.py` (270); `_fetch_policy_items` e `policy_document_cache_key` ganham `connection_id` (chave = company + connection + locator) | `test_a_segunda_corretora_nao_ve_a_primeira.py` **28/28** (2 tenants, `archived` nunca escolhida) · 5/5 mutações vermelhas (chave sem company; sem connection) |
| A.5 `FACT_SOURCES` | `("sistema_de_gestao","documento_oficial","regra_de_apolice")` escritos; `fonte_canonica()` aceita os legados; **4** leituras no compositor migradas (D-A-a: a proposta citava 2) | `test_spec016_policy_intelligence` **92/92** · `test_spec016_1_answer_quality` **51/51** (migrados sob §9.3: o teste antigo afirmava que o registry aceita adaptador incompleto — era o defeito) |
| A.6 fronteira | `test_a_porta_nao_vaza_o_fornecedor.py`: **18 ok · 7 VERMELHO ESPERADO · 0 de verdade** (exit 1 por construção até B/C/D): G1a `infocap_tool.py:582,622,650` importa o conector (B/C) · G1b `:61,:469` nomeia campo (C) · G1c `prompts.py` 7 linhas "InfoCap" em prosa (C) · G1d 4 `hasattr(provider` (D) | 4/4 mutações com o efeito declarado (par de controle: `infocap_policy_lookup` no prompt continua VERDE) |

Conferido pelo orquestrador (árvore parada): 37 + 34 + 28 verdes; `test_a_apolice_responde_item_por_item` 31/31 (bf963b0 intacto); os 4 guardas de P-PILOTO-20 **verdes** (14 · 92 · 51 · 21 — o `e2e_stub` precisou do mesmo conserto de harness: `app.providers.__path__` real, feito pelo orquestrador). 🔴 **Achado falso descartado com medição:** o builder reportou `vlvenc` "em centavos" (8231,0); 📊 o JSON cru da porta traz **82,31** — o ×100 era um defeito do montador do golden (número tratado como texto BR). Fixture corrigida no lugar; nenhuma pendência de conector. Divergências D-A-b (o conector não carrega `tabela_itens`/`sit_*_txt`/`observacoes` para o pack — `_safe_envelope_summary` guarda só nomes) e D-A-c (7 linhas de prosa hoje, não 8) vão para o BLOCO D e C.

## 3. BLOCO E — contexto, tokens, rastro, harness (Builder E · Opus 5 · 📊 302k tokens · ≈3 h com uma queda de sessão por 429 no meio, retomado no mesmo contexto)

| entrega | o que mudou | prova |
|---|---|---|
| E.1 a pergunta sobrevive ao bloco | `graph.py`: `TETO_DO_CONTEXTO_RECUPERADO_CHARS` (env, default **60.000** chars ≈ 💭 15k tokens; nota 86 × 120k 70 × 20k 55), corte por TRECHO inteiro (separador `"

---

"` que `search_service.py:985` usa), excedente DITO ("mostrando os N trechos mais relevantes de M"), pergunta repetida DEPOIS do bloco dentro do prompt de sistema; função pura `montar_bloco_recuperado`; `rag_chunks`/`rag_chars` no evento `final` → `payload.turn` (D3: o próximo laudo mede) | `test_a_pergunta_sobrevive_ao_bloco.py` **53/53** · mutações M1 (pergunta removida) M2 (`[:N]` silencioso) M3 (chamador concatena cru) → **3/3 vermelhas** |
| E.2 P-PILOTO-17 | migration `20260914_06_spec_extra0011_llm_max_tokens.sql` (backup por `agent_id`, ON CONFLICT DO NOTHING, ROLLBACK exato; RLS na tabela de backup); defaults de código → 8192 em `agent_config.py:82/:133/:288`, `models/agent.py:19`, `app/api/admin/sandbox/bootstrap-tenant/route.ts:106` (era 1200) | §5: V0–V5 colados; APPLY 2×; ROLLBACK exercitado e reaplicado; `npm run test:rotas-montam` → "A TABELA DE ROTAS MONTA" |
| E.3 piso do segurado | `PAPEIS_QUE_CONVERSAM += insured_external` (📊 0 instâncias hoje — latente) | `test_quem_fala_com_o_segurado_tambem_tem_piso.py` **21/21** · 3/3 mutações vermelhas · `test_a_resposta_chega_inteira` 26/26 continua verde |
| E.4 P-PILOTO-18 reescrita e fechada | `trace_id = "<session_id>|<client_request_id>"` (nota 88 × `client_request_id` puro 62 × chave em `input_summary` 55; 📊 6 ocorrências de `trace_id` em `backend/app`, todas de ESCRITA — nenhum leitor para quebrar; zero DDL); ContextVar `TURNO_EM_CURSO` marcado ANTES do `create_task` (`chat.py:1116`); `payload.turn.tool_calls` derivado por SELECT em `tool_invocations` (uma escrita, dois leitores; falha do SELECT nunca derruba o turno); `_RegistroInerte` com motivo + contador observável; MANIFEST: `tool_invocations` como NÃO RASTREADA com a DDL real | `test_a_ferramenta_do_turno_deixa_rastro.py` **45/45** (gate de bloco, fora do teto de 12) · 4/4 mutações vermelhas (trace sem a chave; `tool_args` cru; inerte sem contar) |
| E.5 P-PILOTO-20 fechada | harness dos 4 scripts carrega o módulo real `honestidade_do_handoff` antes de `nodes.py` | 📊 os 4 RODAM: `test_infocap_policy_output_guard` **14/14 verde** · `test_spec016_policy_intelligence` 76 ok / 6 falhas POR REGRA · `test_spec016_1_answer_quality` 49 / 2 · `test_spec016_e2e_stub` crash por regra — as falhas são da superfície de A/B/C/D (`fonte é infocap_structured`, `registry resolve provider`, `provider tem lookup e detail`, `facts documentais`, módulos `infocap_policy_provider`/`pdf_only_policy_provider`): VERMELHO ESPERADO que fecha com o BLOCO A e o BLOCO D (§2/§4) |

Pendências novas do bloco: **P-E0011-DEFAULT-DDL-2000** (🤖; `schema_completo.sql:454/:581` — DDL, segunda migration; custo: um INSERT fora dos modelos Python nasce com 2000, o piso segura o comportamento) · **P-E0011-REDACAO-POR-SUBSTRING** (🤖; `_CAMPOS_SENSIVEIS` casa por substring e `document_evidence_requested` sai `[omitido]` — over-redação, erro para o lado certo; custo: auditabilidade). Verificado pelo orquestrador (árvore parada): 53 + 21 + 45 verdes, 10/10 mutações vermelhas, 14/14 do guarda antigo.

## 5. Migrations (APPLY / VERIFY / ROLLBACK)

### `20260914_06_spec_extra0011_llm_max_tokens.sql` — migration de DADO (a única desta SPEC)

| Campo | Conteúdo |
|---|---|
| **Objetivo** | `agents.llm_max_tokens` deixa de mentir (P-PILOTO-17): 8 linhas → 8192, com backup por `agent_id` |
| **Destrutiva** | não; expand-first (backup nasce antes); idempotente |
| **V0 antes do APPLY (14/09)** | (attendance,1200,1) (attendance,2000,3) (core,1200,3) (core,2000,1) · alvos 8 · backup não existia — bateu com a medição |
| **VERIFY (saída real)** | V1 (attendance,8192,4) (core,8192,4) · V2 linhas_guardadas 8, ja_era_8192 0 · V3 (1200,4) (2000,4) · V4 nenhuma linha · V5 companies (2000,5) intacta |
| **G-MIG 2 (APPLY 2×)** | linhas_guardadas 8 · ja_era_8192 0 · em_8192 8 |
| **G-MIG 3 (ROLLBACK exercitado)** | em produção, com o produto pausado: (1200→1200, 4) (2000→2000, 4) por `agent_id`; reaplicado → V1/V2/V3 iguais; a tabela de backup permanece |
| **Advisors** | security antes: 122 INFO + 2 ERROR (views) + 6 WARN pré-existentes; depois do 1º APPLY: **+1 ERROR** `rls_disabled_in_public` na tabela de backup → `enable row level security` (2ª passada da mesma migration; `relrowsecurity = true`); arquivo emendado para o APPLY já nascer assim |
| **Aplicada em produção** | sim · 14/09/2026 · `spec_extra0011_llm_max_tokens` (MCP) · MANIFEST atualizado com o inventário antes/depois |
| **`companies.llm_max_tokens`** | NÃO tocada (D-E0011-01) — V5 é o controle |

## 4. BLOCOS B, C, D

### 4.1 BLOCO B — vigência e ramo na porta (Builder B · Opus 5 · 📊 381k tokens · ≈3 h)

| entrega | o que mudou | prova |
|---|---|---|
| B.1 a lista inteira | conector expõe `policies_all` ao lado de `matches[:10]` intacto (D-B-01: (b) 85 × (a) 25); `InfoCapProvider.listar_apolices` lê a lista inteira, classifica por `classificar_vigencia`, `historico_oculto = documents_count − elegíveis`, `capacidades().listar_apolices` PARCIAL → **SUPORTADA**; `resposta_do_lookup` evita a 2ª chamada à fonte (D-B-03: 88 × 35) | `test_vencida_nunca_vira_opcao.py` **40/40**: 📊 0 vencidas nas 3 listagens reais; caso real 11/10 e caso sintético 12 com a vigente na 11ª → encontrada; 4/4 mutações vermelhas (filtro desligado; `[:10]`) |
| B.2 a escolha na porta | `escolher_apolice(lista, *, ramo, hoje)` → `Escolha` (found / sem_vigente / ambiguous_policy / nenhuma; `auto_selected_reason` humano; `historico_oculto`; `ultima_vigente`; `frase_sem_vigente` da §6.2); famílias de ramo (`familia_de_ramo`); ramo pedido sem vigente NÃO filtra até zero e o motivo diz (D-B-07: 85 × 10); régua `problemas_de_lingua` com a cláusula de "próxima ação" desligada para fragmento, com par (D-B-08) | `test_so_pergunta_com_duas_do_mesmo_ramo.py` **32/32**: 1 auto + 1 resi → não pergunta; 2 auto → pergunta com 2 vigentes; vencida no meio fora; 0 vigentes → `sem_vigente` com data; `found_com_motivo` 25/25; `policy_status` "ativo" não vira vigente; 5/5 mutações vermelhas |
| B.3 a tool | auto-seleção para TODOS os papéis (`_client_facing` fora da condição); ramo por ① explícito ② ficha (`selected_policy_number` viaja) ③ 3 últimas humanas ④ serviço; `chaveiro` nos dois regex + `_desempatar_pelo_contexto` (📊 "trancado fora de casa" → `resi`; "chave do carro" → `auto`); os 3 imports do conector saíram (número humano e formatação de opções moram na porta; o conector DELEGA); `policy_options` só em ambiguous; briefing com `apolice_escolhida_porque` e `historico_oculto`; `sem_vigente` é status novo que curto-circuita o compositor (D-B-06: 85 × 40 — com `matches` vazio o guarda de :273 devolveria "qual delas?", a mentira da §6.2); o DETALHE continua vindo do `lookup` depreciado com `policy_number` (D-B-02: 90 × `detalhar_apolice` 20 — 📊 compositor e briefing consomem o `policy_evidence_pack` de ~40 chaves que só o conector monta; migra com o briefing, no C/D) | `test_o_ramo_sai_da_conversa_nao_da_ultima_frase.py` **51/51**: 9/9 frases com o ramo certo; 4 papéis com janela de 3; 3 papéis auto-selecionam; 5/5 mutações vermelhas (`_product_hint` na 1ª condição; `_client_facing` de volta; janela só attendance) |
| B.4 `nodes.py:1004–1020` | a janela das 3 últimas humanas vale para todos os papéis | idem |
| B.5 compositor | `_real_vigencia` delega a `classificar_vigencia`; `_compose_options` recebe `historico_oculto` (a frase "há N no histórico" volta a ser verdadeira) | `test_a_apolice_responde_item_por_item` 31/31 · spec016 92/51/21 · output_guard 14 · attendance_unleashed 26 · A: 37/34/28 · `mypy` 2 arquivos sem erro |

Fronteira depois do B: `importadores_fora_da_fronteira = 0` (G1a VERDE); restam **6** VERMELHO ESPERADO: G1b `infocap_tool.py:121,:670` (C) · G1c `prompts.py` 7 linhas (C) · G1d 4 `hasattr` (D). Divergências: D-B-a (a chave `pessoa_hdi` do golden veio da consulta por número — 1 match; a composição 6/2 vigentes foi reconstruída em `listagens_extra0011.json`); D-B-b (📊 5 das 7 perguntas fecham pela lista; q6/q7 fecham pelo ramo explícito); D-B-d `_parse_br_date` órfã → **P-E0011-PARSE-BR-DATE-ORFAO**; D-B-g a trava `SEM_REDE` precisa liberar loopback no Windows (`ProactorEventLoop`); D-B-h editar produto durante `--mutar` desfaz a edição (árvore parada). Conferido pelo orquestrador: 40 + 32 + 51 verdes; 14/14 mutações vermelhas; todos os guardas anteriores verdes.

### 4.2 BLOCO C — briefing, guarda de `nodes.py`, prompts (Builder C · Opus 5 · 📊 344k tokens · ≈2h20)

| entrega | o que mudou | prova |
|---|---|---|
| C.1 briefing | as coberturas vêm da `Apolice` RECONCILIADA da porta (`apolice_reconciliada_do_pack`, D-C-01: 90) com origem por linha, divergência em prosa (`como_frase`), aviso de cadastro incompleto, forma de pagamento das PARCELAS, plano; `opcoes_de_apolice (liste TODAS…)` (:405) SAIU → `apolices_vigentes_do_mesmo_ramo` só em `ambiguous_policy`, com o texto vindo da porta (`opcoes_em_texto`, D-C-02: 88 — nunca `policy_status` cru); a regra 3 do corretor (:467) virou condicionada; a regra 1b (:465) FICA byte a byte; regra 5 fala de origem; item 5 do segurado aponta para `seguradora_para_acionamento` gerada do catálogo (D-C-04); `policy_ref` do `args_schema` opaco e `numapo` → `numero_humano_de` (G1b); fallback para `coverage_sections` se a reconciliação falhar (D-C-06, com a mutação M-C2g provando que o caminho reconciliado é o que roda) | `test_a_cobertura_continua_inteira.py` **33/33**: 📊 HDI cadastro 6 → briefing **10** (Assistências Essenciais com origem documento; Danos Elétricos 550 × 600 as duas), Allianz 15 → **21**; PAR sem PDF: 6 e 15 com origem cadastro; 4/4 mutações vermelhas (apagar 1b; `[:5]`; sem reconciliar; divergência calada) |
| C.2 guarda `nodes.py:263–288` | a linha `:273` MEDIDA antes e depois (precedência real `A and (B or (C and D))`: anula sem "seguradora"+"número"; aceita com os dois) — reescrita com parênteses e motivo, veredito idêntico (D-C-03: 85 × sair 40); `policy_options` só entra em `required_facts` em `ambiguous_policy`/`policy_number_ambiguous` (D-C-e); com opções presentes continua anulando quem omite uma | `test_o_corretor_recebe_a_apolice_nao_a_lista.py` **87/87**: 📊 7 de 7 perguntas do corpus em `found` numa chamada (o acervo media 0 de 7); 0 briefings mandando listar (era 7 de 7); 7/7 com o porquê; PAR 2 auto vigentes → ambiguous com 2 opções e o guarda anula a resposta que omite uma; `test_infocap_policy_output_guard` 14/14 |
| C.3 prompts | as 7 prosas `InfoCap` saíram; `infocap_policy_lookup` (:37) fica (allowlist escrita); `CORE_BASE_PROMPT` ganhou a frase de vigência; `ATTENDANCE :189` ganhou "(só quando… 2+ vigentes do MESMO ramo)"; `:126/:185/:206` ficam | 📊 `infocap_em_prosa 0` · `CorpAPI 0` · mutação "InfoCap" no CORE → vermelho; PAR `infocap_policy_lookup` numa linha nova → continua VERDE |
| C.5 catálogo | `seguradora-coenti.json` seção `familias_de_acionamento` (`yelum` ← LIBE/LIBERTY/YELUM; `porto` ← ITAU/PORT/PORTO; critério por linha; D-C-05: 90 — 📊 ITAU tem coenti UNKNOWN e mesmo assim aciona por `porto`: identidade SUSEP ≠ acionamento); `susep_ses_provider.familia_de_acionamento` por IGUALDADE | mutação: linha `yelum` fora do JSON (cópia) → a frase some → vermelho |

Fronteira depois do C: `infocap_em_prosa 0 · campos 0 · importadores 0 · hasattr 4` → resta só **G1d** (BLOCO D). Divergências: D-C-a (`numapo` estava em :444/:519/:610, não :670); D-C-d (`test_spec017_attendance_unleashed` 1 asserção migrada sob §9.3: media a regra que a SPEC remove; 26 → 27); achado fora do escopo: `test_infocap_contract_capture.py` vermelho desde o BLOCO B por stub de harness (`app` sem `__path__`; o conector passou a importar a porta) — consertado pelo orquestrador (`app.providers` real no stub): **108/108**. Conferido pelo orquestrador: 87 + 33 verdes, 9/9 mutações com o efeito declarado; 31 · 14 · 27 · 40 · 32 · 37 continuam verdes.

### 4.3 BLOCO D — o PDF é lido sempre, e os campos que ninguém lia (Builder D · Opus 5 · 📊 364k tokens · ≈2h30)

| entrega | o que mudou | prova |
|---|---|---|
| D.1 o extrator lê as tabelas REAIS (D4, D-E0011-02) | `policy_document_evidence_service`: 5 regex para os 2 layouts (HDI `<rótulo> <LMI>   <prêmio>` sem `R$`; Allianz `R$ LMI R$ prêmio` + franquia `pct mínimo` / `- Sem Franquia` / `- N Hrs`), franquias em prosa (`deductible_prose`), parcelas do PDF (`installment_row`); lista DECLARADA de 12 rótulos que nunca são cobertura (Prêmio Líquido, Total a Pagar, LMG…); cobertura × plano decidido pelo nº de colunas de dinheiro (D-D-04: 92 — "Coberturas de Assistencias Essenciais 0,00 125,94" É cobertura; "Assistência 24h R$ 23,88" é plano E linha, D-D-03); estruturados de todas as páginas ANTES dos fragmentos e teto 40 → 60 (D-D-05: 📊 12 fragmentos de cláusula da p.1 consumiam o teto antes da tabela da p.2) | 📊 extrator real sobre `pdf_tabelas_reais_extra0011.json`: HDI `coverage_row` **10** · `deductible_prose` 6 · `installment_row` 4 · Σ 306,60 = preliq; Allianz `coverage_row` **20** + `assistance_plan` 1 · Σ 24.960,60 = preliq; linhas de prêmio lidas como cobertura **0** (era 1); reconciliado HDI **10**, Allianz **21** — `test_a_cobertura_continua_inteira` 33 → **40** (GC2f ponta a ponta pelo `document_text`) |
| D.2 o gatilho pelo destino | `_LER_SEMPRE_O_DOCUMENTO = True` nos 3 pontos de chamada da tool; `policy_document_evidence_requested(q, explicit)` continua para outros chamadores; cache documental durável por corretora+locator (D-D-b: os 180 s são do `/itens`, comentário corrigido) | `test_o_documento_e_lido_sempre_que_a_pergunta_e_de_apolice.py` **27/27**: 📊 7/7 perguntas do corpus leem o documento; **q1, q2, q3** não casavam palavra-chave (D-D-a: 4 de 7 pela palavra, não 3 — q2 pedia franquia e q3 carro reserva e nenhuma lia o PDF); controle `c1` → 0 de 1; 3/3 mutações vermelhas (gatilho por palavra; `return True`) |
| D.3 os campos que ninguém lia (D-A-b) | pack ganha `provider_signals` (`sit_renovacao_txt`, `sit_sinistro_txt`, `tabela_itens` com VALOR, redigidos por `_texto_de_provedor`), `coverage_sections[].item_observacoes`, `risk_objects[].observacoes`; adaptador: plano ← `tabela_itens` (estado `nao_sabemos_ainda`), sinais ← `sit_*` (nunca veredito), franquia em prosa ← `observacoes` (D-D-c: o único `/itens` mascarado não tem `observacoes` → cano testado com prosa sintética declarada + par + controle); franquia em prosa da HDI casada ANCORADA no cadastro (D-D-02: 88 — 📊 2 de 3 associações CONFIRMAM o cadastro: Incêndio 350 = 350, Vidros 150 = 150; a 3ª é a divergência real 600 × 550; as 3 sobras viram `Sinal("franquia_em_prosa_sem_dono")`, nunca adivinhadas) | `test_a_divergencia_aparece_inteira.py` **50/50**: HDI ponta a ponta — franquia de Danos Elétricos com AS DUAS (550 cadastro × 600 documento), prêmio 19,17 × 17,25 dito, forma de pagamento **Cartão de Crédito** + `cabecalho_divergente`, plano de `tabela_itens`, `sit_renovacao_txt` não decide vigência; Allianz 21, "Prêmio Líquido" ausente, `Despesas Fixas` com "168 Hrs" como texto; 5/5 mutações vermelhas |
| D.4 `vehicle` e os 4 `hasattr` | os 4 `hasattr(provider, "vehicle")` saíram (`infocap_tool`, `insurer_dispatch_tool:971`, `portal_tool:347`, `vehicle_tool:58`); `vehicle` FICA no contrato, depreciado (D-D-01: 90 × migrar já 45 — tocaria acionamento 017 e vidros 025 fora da superfície testada); `ItemDeRisco` + `Apolice.item_de_risco` preenchido pelo adaptador (pronto para a migração) → **P-E0011-VEHICLE-VIA-DETALHAR** | fronteira **20 ok · 0 VERMELHO ESPERADO · exit 0** (primeira vez); vidros/acionamento: `portal_de_vidros` ok · freio 30 · `traz_os_tres` ok · 074 api 87 · fluxo 49 · mutations 62; `mypy` 2 arquivos sem erro |

Pendências novas do bloco: **P-E0011-VEHICLE-VIA-DETALHAR** (🤖) · **P-E0011-FRANQUIA-EM-PROSA-SEM-DONO** (🧑/🤖: 3 das 6 franquias em prosa da HDI — mínimos 800/650/300 — não têm dono derivável; o corretor VÊ o sinal) · **P-E0011-TETO-DE-EVIDENCIA-60** (🤖) · **P-E0011-ITENS-OBSERVACOES-SEM-ACERVO** (🤖). Pré-existentes confirmados em worktree limpa (D-D-d): `test_spec017_dispatch.py` e `test_spec031_auto_dispatch.py` (`IndexError` / `missing_slots`), 0 referências à superfície desta SPEC. Conferido pelo orquestrador: 27 + 50 + 40 verdes; 13/13 mutações vermelhas; fronteira rc=0; 31 · 46 · 108 · 87 · 92 · 14 · 37 · 34 · 40 · 51 verdes.

## 5.1 CLAUDE.md §9.1 — a aplicação sobe (a SPEC tocou `app/api/admin/sandbox/bootstrap-tenant/route.ts`)
```
npm run test:rotas-montam        A TABELA DE ROTAS MONTA (regressão de 02/08 fechada)
npm run build                    EXIT=0 (14/09, log no scratchpad)
npx next start -p 3111           GET /api/dashboard/rotinas → HTTP 401 · POST /api/admin/sandbox/bootstrap-tenant → HTTP 401 (rotas de CÓDIGO
                                 respondendo com autenticação) · GET / → HTTP 200
```

## 6. Painel: juiz fresco + lente do dado · conserto · suíte

### 6.1 Juiz fresco (Opus 5, cego; sobre `5f84bd9`; 📊 347k tokens · ≈2h20) — **PASS · 67/100**
Critério do juiz: 100 = 17 itens de §19 ✅ e 0 blockers; BLOCKER −15 · ESSENCIAL −5 · VALIOSA −2 · item ❌ −3; item 14 (canário) pendente do Founder não desconta. Placar: **20 guardas verdes** (os 14 novos rodados 2×, os 4 de P-PILOTO-20, bf963b0, contract_capture) · **61 mutações com o efeito declarado / 0 erradas** (59 vermelhas + 2 pares de controle verdes de propósito); o arreio assevera a restauração. VERIFY da migration reconferido pelo juiz no banco. 3 perguntas adversariais: ① vazio/nulo 14/14 sem exceção (limites de data: vence hoje VIGENTE · venceu ontem VENCIDA · começa hoje VIGENTE · começa amanhã FUTURA · sem fim DESCONHECIDA) · ② duas corretoras: ContextVar não vaza; chaves separam tenant E conexão · ③ mesma mensagem 2×: mesma `Escolha`, `reconciliar` idempotente; `invocation_key` não idempotente por desenho declarado (📊 0 duplicadas em 277). §19: 12 ✅ · 4 ⚠️ (5: Allianz 21 por decisão; 12/13: provados em fixture; 16: §6–§12 vazios na hora do julgamento) · 1 ❌ (15: nada empurrado — correto, o push é o último passo do laço).

| # | achado | classe | destino |
|---|---|---|---|
| ① | `policy_document_cache_key` com `connection_id` não DECIDE o hit (`find_official_policy_document(company_id, locator_hash)`); G4d comparava a string | ESSENCIAL | conserto F.2 |
| ② | `escolher_apolice` chama FUTURA e DESCONHECIDA de "única apólice vigente" (📊 latente: 0 casos nas 35 linhas das listagens) | ESSENCIAL | conserto F.3 |
| ③ | o briefing do corretor imprime `situacao: Recebido e não entregue ao cliente` (status de entrega do fornecedor) na linha da apólice — 📊 2 de 2 do golden | ESSENCIAL | conserto F.4 |
| ④ | `rotulo_ambiguo`, `franquia_em_prosa_sem_dono`, `situacao_de_renovacao` são escritos e ninguém lê; a pendência dizia "o corretor VÊ" | ESSENCIAL | conserto F.5 |
| ⑤ | `chave_de_rastro(sessão, None) == sessão`: fora do painel a junção colheria a sessão inteira | VALIOSA | conserto F.7 |
| ⑥ | `policy_number_ambiguous` ainda entrega vencida como opção (filtro só em `ambiguous_policy`) | VALIOSA | conserto F.6 |
| ⑦ | `_desempatar_por_lmi` exige 1º token comum: inerte para "VIDROS" × "Quebra de Vidros" (falha seguro: acende sinal) | VALIOSA | **P-E0011-DESEMPATE-POR-LMI-INERTE** |
| ⑧ | 23 "InfoCap" em strings de `infocap_tool.py` que vão ao modelo (description, `_summarize`) | VALIOSA | conserto F.8 |
| ⑨ | teto de 60k mantém 12 de 128 trechos (9,4%) no turno do tamanho medido; nada mede a resposta do modelo | VALIOSA | **P-E0011-TETO-RAG-MEDIR-COM-MODELO** |
| ⑩ | MANIFEST mentiu por 2 commits ("pendente de execução"); árvore andou durante o julgamento (só docs) | FUTURA | corrigido em `fe1a649` |

Contra a referência da 094: no padrão em registro/recusa, `capacidades()` e teste estrutural+grep+fixture; FORA em (a) `capacidades()` síncrona por provider (a 094 é async por `company_id`), (b) sem exceções de fronteira (`parcelas_em_aberto` devolve `[]` em falha), (c) contrato + modelo + reconciliar + registry num arquivo de 1.908 linhas → **P-E0011-CAPACIDADES-POR-TENANT**, **P-E0011-EXCECOES-DE-FRONTEIRA**, **P-E0011-PORTA-EM-UM-ARQUIVO**. Referências externas reabertas em 14/09: 5 de 5 (ressalva: a frase da ACL sobre "regra de negócio na camada" aparece sob "might not be suitable", não como regra geral).

### 6.2 Lente do dado (Opus 5, cega; 📊 210k tokens · ≈55 min; 21 SELECT, 5 chamadas à porta implantada, 9 execuções do motor novo sobre texto real) — **80/100**
Critério: 100 = toda afirmação 📊 reconstruída igual; divergência sem explicação −5; PII −20; blocker −15. **Zero PII** nos 53 arquivos do diff, fixtures, corpus, relatório e `tool_invocations` (277/277 sem valor). 📊 Reconstruído IGUAL sobre dado vivo: acervo 7/31/24 (reconcilia byte a byte; e 6 das 7 tinham UMA vigente e perguntaram); 2 turnos "não recebi" (117 s / 86 s); `agents` 8/8 8192, backup 8 (4×1200 + 4×2000, `capturado_em` idêntico = prova do `on conflict`), RLS true, `companies` 2000×5, migration `20260914072141`; `tool_invocations` 277, 0 com 11/14 dígitos, `trace_id` sem `|` (deploy não aconteceu); golden HDI 6/70,29/306,60/`10.00%-550,00`/4×Cartão×Boleto/6 páginas e Allianz 15/17.973,02/24.960,60/5 páginas/6×boleto; empresa 11/10; `pdf_tabelas_reais` 27 de 27 linhas verbatim; 7 perguntas idênticas (razão 1,000 em 5; 0,85–0,97 nas 2 com `[NOME]`); contagens por cliente exatas; backup 8 de 8 `agent_id` existentes. **O ELO (dado vivo de hoje no motor novo):** HDI 31 itens → 10 coberturas com origem, Σ 306,60 = preliq, `cadastro_incompleto` R$ 236,31 / 77,07%, `cabecalho_divergente` Boleto × Cartão, Danos Elétricos 19,17 × 17,25 e 550 × 600 AS DUAS, 3 franquias sem dono; Allianz 39 itens → 21, R$ 6.987,58 / 27,99%, "Prêmio Líquido" fora.

| # | achado | classe | destino |
|---|---|---|---|
| 1 | 🔴 `evidence[:20]` em `policy_document_evidence_service.py:1040`: a produção entrega 20 dos 39 itens da Allianz → **20 coberturas em vez de 21** (some "Gastos com Defesa" R$ 70,15); GC2f montava o pack à mão | **BLOCKER** | conserto F.1 |
| 2 | MANIFEST dizia "pendente de execução" com a migration aplicada | ESSENCIAL | corrigido em `fe1a649` |
| 3 | acervo com marcador estrutural = 10 respostas / 49 linhas / 36 vencidas (as 7 lexicais são subconjunto) | ESSENCIAL | D11 + **P-E0011-ACERVO-ESTRUTURAL-10** |
| 4 | o extrator perde "Equip. Eletronicos" quando o documento vem numa página só (fallback docling) — produção passa páginas reais | VALIOSA | **P-E0011-EXTRATOR-PAGINA-UNICA** |
| 5 | `stages` dos 2 turnos não é `[]` (rótulos de etapa) | VALIOSA | corrigido (premissa 16) |
| 6 | tabela de backup: RLS true e 0 policies (só service role lê) | VALIOSA | escrito no MANIFEST |
| 7 | versão aplicada `20260914072141` ≠ nome do arquivo | VALIOSA | escrito no MANIFEST |
| 8 | cache documental keyable por colisão de `content_hash` (hash vem dos bytes do PDF; não morde hoje) | FUTURA | **P-E0011-CONTENT-HASH-COLISAO** |
| 9 | `policy_status` "ativo" nas 22 apólices dos 3 clientes, inclusive as de 2017 — o ELO do card medido no vivo | FUTURA | — |
| 10 | piso de PII do repositório: 📊 105 identificadores / 150 arquivos (base 89 de 23/08); nenhum desta SPEC | FUTURA | **P-E0011-PISO-DE-PII-105** |

### 6.3 Conserto único (Builder F · Opus 5 · 📊 465k tokens · ≈3h30, 1h45 em baterias `--mutar`)

| achado | conserto | prova |
|---|---|---|
| F.1 🔴 lente 1 `evidence[:20]` | `evidence[:MAX_EVIDENCE_ITEMS]` (60); 📊 medido: HDI 26 itens, Allianz 25 — o `[:20]` cortava "Gastos com Defesa" e "Assistência 24h"; a ordem já era estruturados antes de fragmentos (1º fragmento no índice 20/22) | `[GC2g]` novo em `test_a_cobertura_continua_inteira.py`: pelo caminho da PRODUÇÃO (`ensure_official_policy_evidence` com `DocumentService`/ingestão/`fetcher` dublados e as páginas reais) → `evidence_count == len(entregues)`, briefing HDI **10** / Allianz **21**; mutação `[:20]` → vermelho |
| F.2 juiz ① cache do documento por conexão | 📊 `documents` não tem coluna nem `metadata` para a conexão → a conexão entra no NOME do arquivo (`policy_document_filename_prefix(locator, connection)`, uma regra num lugar; sem conexão mantém a forma antiga — expand-first); `ensure_official_policy_evidence` decide o hit por `_buscar_documento_guardado(connection_id=)`; leitor antigo com conexão declarada = MISS, nunca hit errado | `[GC2g]`: 2 conexões do mesmo tenant, mesmo locator/conteúdo → A miss · A hit · B **miss** · 2 viagens à fonte; mutação (prefixo ignora a conexão) → vermelho. Efeito de implantação declarado: PDFs guardados sem conexão perdem o hit na 1ª leitura → **P-E0011-CACHE-DOCUMENTAL-SEM-CONEXAO-REAPROVEITAVEL** |
| F.3 juiz ② FUTURA/DESCONHECIDA "vigente" | `SITUACOES_QUE_NAO_SAO_VIGENTES`; com VIGENTE presente, FUTURA/DESCONHECIDA saem das opções e do `found` mas o motivo as cita ("há 1 apólice que começa em dd/mm"); sem vigente, continuam elegíveis com "começa a valer em …" / "o sistema de gestão não informa o fim da vigência"; a palavra "vigente" só para `VIGENTE`; nunca em `historico_oculto` | `[GB2f]` + 3 fixtures (`so_uma_futura`, `so_uma_sem_fim_de_vigencia`, `uma_vigente_e_uma_futura`) com par e régua de língua; mutações M-B2f/M-B2g vermelhas |
| F.4 juiz ③ `situacao:` crua no briefing | linha `vigencia_por_data: VIGENTE (07/05/2026 a 07/05/2027)` por `classificar_vigencia`; o status do fornecedor vira linha própria `situacao_administrativa_no_sistema_de_gestao: … (NAO decide vigencia e NAO se repassa ao cliente)` | `[GC1f]`: 📊 2/2 do golden e 6/6 de `pessoa_hdi` trazem a string e são VIGENTES por data; pares calendário-estáveis (2019 → VENCIDA, 2099 → FUTURA, cancelled → CANCELADA); mutação vermelha |
| F.5 juiz ④ sinais não lidos | `frase_do_sinal(sinal)` na porta (dicionário por código, frase genérica para desconhecido, nenhuma nomeia fornecedor); seção `avisos_da_apolice:` no briefing com todos os `sinais` menos os que já têm linha própria | `[GD2g]`: HDI → as 3 franquias sem dono (R$ 800/650/300) com "Confirme na seguradora"; sonda `rotulo_ambiguo` aceso E no briefing; par sem sinal → sem seção; M-D2f/M-D2g vermelhas. A afirmação "o corretor VÊ o sinal" passou a ser verdade |
| F.6 juiz ⑥ `policy_number_ambiguous` | 📊 `_arun` só chamava a porta sem `policy_number` — e o status só existe com ele; novo ramo `_desempatar_pelo_numero` (isola pela referência opaca); achado extra: `_summarize`/`_summarize_detail` imprimiam `opcoes_em_texto(matches)` cru ("Status: ativo" numa vencida) → `opcoes_vigentes_em_texto` | `[GB1e]` pela tool real: 1 vigente + 1 vencida com o mesmo número → found na vigente; par 2 vigentes → ambíguo com 2, `Status: VIGENTE`, zero `Status: ativo`; M-B1e vermelha |
| F.7 juiz ⑤ junção sem turno | escrita: `chave_de_rastro(sessão, None)` = `"<sessão>|-"` (`MARCA_SEM_TURNO`); leitura: a junção só monta a chave com `client_request_id`, senão `tool_calls_ausentes: "sem client_request_id"` | 📊 a leitura só roda no painel, que recusa com **400** um turno sem `client_request_id` (o widget devolve o `StreamingResponse` antes de `_gerar`) — a trava da leitura é profundidade inalcançável hoje → **P-E0011-JUNCAO-SEM-TURNO-INALCANCAVEL**; `[G1]`/`[G2]` migrados (§9.3), M4/M5 vermelhas |
| F.8 juiz ⑧ "InfoCap" na tool | 📊 23 → 4 (docstring 2 + comentários 2); zero literais que cheguem ao modelo (description, `_summarize`) | `[G1c]` mede `\bInfoCap\b` em `infocap_tool.py` sem prosa/logs, allowlist VAZIA; M-A1e vermelha + par M-A1f verde (identificador minúsculo) |

📊 Depois do conserto (orquestrador, árvore parada): 14 guardas novos **0 vermelhas** (37 · 34 · 28 · 23 · 49 · 47 · 51 · 100 · 50 · 27 · 64 · 53 · 21 · 50); os 4 de P-PILOTO-20 (14 · 92 · 51 · 21), bf963b0 31, contract_capture 108, evidence_pipeline 46, attendance_unleashed 27; **44 mutações dos guardas tocados, 0 erradas** (7 + 7 conferidas pelo orquestrador); `mypy` sem erro; nenhum `.bak`. Pendências novas: **P-E0011-JUNCAO-SEM-TURNO-INALCANCAVEL**, **P-E0011-CACHE-DOCUMENTAL-SEM-CONEXAO-REAPROVEITAVEL**, **P-E0011-OPCOES-EM-TEXTO-SOBRE-DICT**. Não consertado nesta rodada (registrado): juiz ⑦ (desempate por LMI), ⑨ (teto 12/128 sem modelo); lente 4 (página única), 8 (colisão de hash).

### 6.4 A suíte inteira
📊 1 rodada inteira (14/09, árvore parada em `3320cee`, `python -m pytest tests -q`): **1107 passed · 18 failed · 48 errors · 34 xfailed · 1 xpassed (24 min 49 s)**. Triagem nominal contra a linha de base (001.6 §5.5 sobre `cff20ef`: 1094 passed · 14 failed · 48 errors): nenhuma das 18 é do produto desta SPEC. 48 errors = `test_098_builder_b_unit.py` (ImportError no setup, fora da área, idêntico à base); pré-existentes na base: `a_resposta_chega_inteira`, `o_caso_se_explica_sozinho`, `a_atendente_aperta_o_botao`, `o_corpus_nao_vaza_pii`; arnês do meta-guarda (P-088-MUT — a sessão terminou com `rubrica.py` mutado por outro script e o arnês restaurou: `test_a_arvore_ficou_limpa_no_fim`, e os 9 scripts que rodaram sobre a árvore mutada: `nenhuma_mutacao_foi_commitada`, `observador_silencio`, `ontologia_e_unica`, `sem_corredor_de_vidro`, `spec031_finalize_v2`, `spec073_portal_worker_mutations` e os 3 `spec016_*`), mais `o_sinistro_deixa_rastro`, `a_central_diz_a_verdade` e `toda_linha_tem_origem` — 📊 os 3 `spec016` (92 · 51 · 21), `toda_linha` (37), `a_central`, `o_sinistro` e `a_arvore_ficou_limpa` **passam isolados** (4 passed em 29,6 s); `test_o_protocolo_tem_policia` é desta SPEC e ficou vermelha porque o relatório ainda não tinha a nota e a bateria (fecha com este commit). ⚠️ A 2ª rodada inteira não foi feita: a 1ª levou 25 min e o resultado atribuível à SPEC é zero.

## 7. Canário (depois do Implantar)

| Ambiente | Estado | Evidência | Data |
|---|---|---|---|
| Amandus (técnico) | não se aplica: o chat de apólice roda na corretora com InfoCap conectada (Resulta); a Amandus compartilha a conta (F-094-07) | — | — |
| Resulta | **pendente do Implantar** (`smith-api` + `smith-web`); os 7 casos estão em `docs/canon/ROTEIRO-CANARIO-EXTRA-001.1.md` (caso 7 = linha de controle) | P-E0011-CANARIO-VIVO-NO-IMPLANTADO | — |
| AutoFleet | não se aplica nesta SPEC (sem pergunta de apólice no acervo) | — | — |

**Flags/variáveis novas (nome, default; nenhuma obrigatória):** `TETO_DO_CONTEXTO_RECUPERADO_CHARS` (smith-api, 60000). **Auto-pause:** não se aplica.

### 7.1 Os 7 casos (preencher depois do Implantar, por alias e contagem)
| # | caso | resultado |
|---|---|---|
| 1–7 | ver o roteiro | pendente |

### 7.2 Validado pela atendente
Roteiro em `docs/canon/ROTEIRO-VALIDACAO-EXTRA-001.1-ATENDENTES.md`; estado: **não testado**.

## 8. O que ficou fora e por quê

| frente | por quê | gatilho de retorno |
|---|---|---|
| migrar os 4 chamadores de `vehicle()` para `detalhar_apolice().item_de_risco` | tocaria acionamento (017) e vidros (025) fora da superfície testada; o `hasattr` saiu e o modelo já tem `ItemDeRisco` (D-E0011-13) | P-E0011-VEHICLE-VIA-DETALHAR (SPEC-101 / 001.10) |
| migrar `detail` → `detalhar_apolice` no caminho do detalhe | o compositor e o briefing consomem o `policy_evidence_pack` que só o conector monta (D-E0011-10) | SPEC-101 |
| `companies.llm_max_tokens` e os `DEFAULT 2000` de DDL | decisão D-E0011-01; DDL exige segunda migration com manifesto | P-E0011-DEFAULT-DDL-2000 |
| renomear a tool `infocap_policy_lookup` | cutover de catálogo de outra SPEC; o identificador nunca chega ao usuário | P-E0011-CUTOVER-DO-NOME-DA-TOOL |
| base de produtos / planos de assistência | é a 001.5 inteira; a 001.1 deixa a chave e o `PlanoDeAssistencia` com `nao_sabemos_ainda` | EXTRA-001.5 |
| medir a resposta do modelo com o teto do RAG | não há LLM no laço; o canário do caso 5 mede | P-E0011-TETO-RAG-MEDIR-COM-MODELO |
| o canário vivo e a validação com a atendente | dependem do Implantar (Founder) | P-E0011-CANARIO-VIVO-NO-IMPLANTADO |

## 9. Decisões tomadas com nota (regra do Founder: escolher, anotar, avisar no fim)

| id | decisão | opções e notas | por quê |
|---|---|---|---|
| **D-E0011-01** | `companies.llm_max_tokens` NÃO sobe na migration | deixar **70** · subir para 8192 **55** | 📊 é o fallback da `llm_factory` para TODOS os papéis; o piso só cobre quem conversa de propósito — subir mudaria auxiliar/subagente |
| **D-E0011-02** | o extrator documental ganha os dois layouts reais (HDI sem `R$`; Allianz com franquia "pct valor") — ESSENCIAL fora do texto da proposta | fazer no BLOCO D **90** · registrar como pendência **30** (o golden 10/21 seria impossível e o outcome "inteira" não se cumpre) | D4 |
| **D-E0011-03** | golden reconciliado da Allianz = 21 (PDF), não 15 (cadastro); o controle de M-A3 é fixture sintética | 21 **95** · manter 15 **10** (seria afirmar que a apólice está inteira com 6 coberturas a menos) | D5 |
| **D-E0011-04** | M-E1 usa turno sintético ≥ 128 chunks (tamanho declarado) e o BLOCO E passa a gravar o tamanho do bloco RAG no turno | sintético **80** × esperar o próximo turno grande real **20** | D3 |
| **D-E0011-05…15** | as decisões dos builders A–E (teto 60k; `trace_id` composto; Decimal/mesmo arquivo/`Indisponivel` próprio/sem `policy_catalog.py`; casamento por grupo declarado; `policies_all`; detalhe pelo `lookup`; briefing da `Apolice` reconciliada; famílias no catálogo; `vehicle` depreciado fica; franquia ancorada no cadastro; RLS no backup) | notas em `FOUNDER-DECISIONS.md` | §2–§4 |
| **D-E0011-16** (conserto) | o cache documental decide o hit pela CONEXÃO no nome do arquivo (`documents` não tem coluna nem `metadata`; zero DDL); leitor antigo com conexão declarada = MISS | nome do arquivo **85** × coluna nova (DDL) **35** × ignorar a conexão **0** | juiz ① |
| **D-E0011-17** (conserto) | FUTURA e DESCONHECIDA só são elegíveis quando não há VIGENTE; havendo, saem das opções mas o motivo as cita; nunca entram no histórico oculto | **90** × tratar como vigente **0** × ocultar em silêncio **30** | juiz ② |
| **D-E0011-18** (conserto) | o status administrativo do fornecedor FICA no briefing, em linha própria com a trava ("não decide vigência; não se repassa ao cliente"); a vigência impressa é por data | linha própria **85** × apagar **50** (perderia o sinal de "não entregue ao cliente" que a corretora usa) | juiz ③ |

## 10. Riscos remanescentes
- 🔴 **O canário vivo não rodou** (Implantar pendente): tudo o que é 📊 nesta SPEC foi provado sobre o acervo real EM MEMÓRIA e sobre o dado vivo pela porta implantada (lente), não pela resposta de um modelo na produção. O caso 7 (controle) e o caso 5 (turno grande) são os que podem surpreender.
- ⚠️ **Primeira leitura depois do Implantar baixa os PDFs de novo** (cache documental por conexão — P-E0011-CACHE-DOCUMENTAL-SEM-CONEXAO-REAPROVEITAVEL): latência a mais uma vez por apólice, nada apagado.
- ⚠️ **O teto de 60k chars no bloco recuperado** descarta 116 de 128 trechos no turno do tamanho medido; é o comportamento declarado, mas a qualidade da resposta com 12 trechos só o canário mede.
- ⚠️ **3 franquias em prosa da HDI sem dono** chegam ao corretor como aviso; a resposta certa depende de a seguradora declarar qual cobertura carrega cada franquia (001.5).
- ⚠️ **`vehicle` continua no contrato, depreciado**: todo adaptador novo tem de implementá-lo até a SPEC-101 migrar os 4 chamadores.
- 💭 **Flag `POLICY_INTELLIGENCE_V2`**: o briefing reconciliado roda sob a flag v2 (já ligada em produção — `test_a_apolice_responde_item_por_item` cobre); com a flag desligada o fallback `_summarize` mostra a lista clássica com situação por data (F.6).

## 11. Rollback
- **Código:** `git revert` do intervalo `4e80a3d..` + hash final é compatível — a porta é aditiva (os 3 depreciados continuam), os 8 pontos de chamada antigos continuam funcionando, o conector só ganhou `policies_all`/`provider_signals`/`connection_id` (chaves e parâmetros novos). Reverter só o BLOCO C/D devolve a lista e o gatilho por palavra-chave sem quebrar A/B/E.
- **Migration `20260914_06`:** ROLLBACK escrito no arquivo e **exercitado em produção em 14/09** (8 valores voltaram um a um por `agent_id`); a tabela `agents_llm_max_tokens_backup_extra0011` NÃO se apaga. ⚠️ O piso de 8192 do `llm_factory` (commit `312939f`) não se reverte junto.
- **Cache documental:** os nomes antigos continuam válidos para quem não declara conexão; nada foi apagado.
- **Prompts:** as 7 prosas "InfoCap" e a frase de vigência do `CORE_BASE_PROMPT` são texto; reverter é editar o arquivo.

## 12. Entrega (`git push`, saída colada)

```
$ git rev-list --count HEAD..origin/main   → 0
$ git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   cff20ef..3320cee  HEAD -> main
```

**Serviços a implantar (Founder):** `smith-api` (porta, tool, grafo, prompts, extrator, chat) e `smith-web` (o default de tokens do tenant de sandbox). Ordem: `smith-api` → `smith-web`. **Variáveis novas:** nenhuma obrigatória (`TETO_DO_CONTEXTO_RECUPERADO_CHARS` opcional, default 60000). **Migration:** já aplicada. **Depois do Implantar:** os 7 casos do canário (`ROTEIRO-CANARIO-EXTRA-001.1.md`).

## 13. Nota do orquestrador — **87/100**

Critério (o mesmo da 001.6): 100 = os 17 itens de §19 com evidência, painel verde depois do conserto, orçamento e relógio dentro da faixa, canário vivo feito. Descontos: **−5** canário vivo pendente do Implantar (§19.14; não é do executor, mas a SPEC não está provada em produção) · **−4** orçamento 📊 ≈2,9 M contra o teto de 1 M e relógio ≈15 h contra 8–12 h · **−2** duas VALIOSAS do juiz abertas (desempate por LMI; teto do RAG sem medida de modelo) · **−2** duas VALIOSAS/FUTURAS da lente abertas (página única; colisão de hash). Sem desconto pelo que fechou: 0 blockers restantes; 105 mutações com efeito; o ELO reconstruído sobre o dado vivo; migration aplicada, verificada e revertida de prova; nenhum motor paralelo; nenhuma PII.

**A pergunta que o Founder faz (§19):** *quando eu perguntar pela apólice de um cliente, eu recebo a apólice certa, inteira, de uma vez — e consigo ver de onde veio cada número?* — 📊 Pelo motor sobre as 7 perguntas reais: sim, 7 de 7 em uma rodada, com o porquê; HDI 10 e Allianz 21 coberturas com origem por linha e a divergência dita. **Em produção: depois do Implantar.**
