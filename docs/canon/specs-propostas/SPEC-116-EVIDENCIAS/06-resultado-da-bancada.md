# SPEC-116 · EVIDÊNCIAS 06 — o resultado da bancada (F6 · U13, medição)

> 23/09/2026 · branch `spec/116-model-router-e2e-bench` · HEAD `8518613` + mudanças NÃO commitadas da F6
> (o `commit_sha` gravado em `eval_runs` é `8518613…-sujo`). Corpus **v2** (`MANIFESTO.json`).
> Toda linha 📊 abaixo vem dos JSONs em `backend/tests/corpus/bancada/RESULTADOS/` (um por grupo) e de
> `eval_runs`/`eval_case_results` (gatilho `bancada`), releitura pelo comando indicado em cada tabela.

## 0. 🔴 O QUE PAROU A MEDIÇÃO — leia antes das tabelas

| fato 📊 | comando / fonte |
|---|---|
| **Anthropic sem crédito** a partir de **19:18:38Z**: `400 invalid_request_error — "Your credit balance is too low to access the Anthropic API"` | chamada de prova `claude-haiku-4-5-20251001` (bancada.construir_llm_padrao) às ~19:35Z; última linha Anthropic no ledger `bancada`: `claude-sonnet-5` 19:18:38Z |
| **OpenAI sem crédito** a partir de ~**19:41Z**: `"You have no credits remaining"` | `rastro.erro` dos braços `gpt-6-astra:high` / `gpt-6-luna:medium`; última linha OpenAI no ledger: `gpt-6-astra` 19:42:01Z |
| Gasto total da F6: **US$ 11,89** (ledger) ≈ **US$ 11,88** (`eval_runs.custo_usd`, braços reais) | `select sum(total_cost_usd) from token_usage_logs where service_type='bancada' and created_at>='2026-09-23T19:00Z'` (paginado: 2.234 linhas no total, US$ 11,97 incl. F5b US$ 0,07) |

**Consequência:** as duas contas acabaram muito antes do teto de US$ 100. Tudo o que é Anthropic depois de
19:18Z e tudo depois de 19:41Z é `BLOCKED_BY_INFRA` (fora do denominador — nunca contra o modelo).
⚠️ **Se a chave do `.env` local é a MESMA do produto, o atendimento e o chat (Sonnet 5) e o que depende da
OpenAI (memória, visão, portal, embeddings) estão SEM PROVEDOR AGORA.** 🧑 conferir e recarregar — é do Founder.

Outras perdas de infra, também separadas do modelo:
- **Rate limit (TPM)** por rodar 4 processos em paralelo: `gpt-6-sol` 500k TPM e `gpt-6-luna` 200k TPM (📊 texto do 429 no `rastro.erro`). Pior no N2 (📊 `gpt-6-luna:medium` 27/30 bloqueadas no atendimento N2). **Falha de método da F6**, não do modelo.
- **`gpt-5.6-terra` com tools é recusado**: `400 — "Function tools with reasoning_effort are not supported for gpt-5.6-terra in /v1/chat/completions"` — o catálogo declara `api_surface=chat_completions` para ele; com tools tem de ser `responses` (📊 90/90 bloqueadas no chat N1). **Defeito de CATÁLOGO** (produto), não do modelo; sem tools (memória) ele roda.
- **Dispatch sem medição válida:** `o_cerebro_ja_sabe` engole a exceção do provedor (`except Exception → (None, "")`) e a bancada contava como FAIL. 📊 Todos os braços reais deram exatamente o placar do `burro` (20 %) com `chamadas_ao_modelo = 0` em 45/45 tentativas nos braços Anthropic (sem crédito) e 35–43/45 nos OpenAI (rate limit, os 4 processos em paralelo). **Consertado na bancada** (ver §1.d) — os números da tabela do dispatch ficam como estão no JSON, mas **não valem**.

## 1. Passo 0 — os consertos de REALISMO feitos antes de medir

**(a) Forma real das tools no N2.** O `DubleDeTool` devolvia texto; as tools reais devolvem dict e o `tool_node` decide pelo tipo.
- `dubles.py`: `resposta` dict/list volta como **dict (cópia)**; texto continua texto.
- `bancada_gerar_corpus.py` (corpus **v1 → v2**, todos os casos com `versao: 2`): `infocap_policy_lookup` = `{content, data, found, policy_response_contract, cobertura}` — `content` pelo **construtor real** `InfocapPolicyLookupTool._build_llm_briefing`, contrato pelo **real** `_build_policy_response_contract`, `data` com as chaves de `infocap_connector._sanitize_policy/_canonical_customer_identity` (**mascarado no atendimento**, completo no core); `insurer_dispatch` = `{status:"dispatched", content:<texto real do modo teste>}`; `request_human_agent` = `SUCESSO_DO_HANDOFF` (importado); `portal_action` = `{content: format_result({"status":"queued"})}` (importado); `knowledge_base_search` = `{content, chunks, found, search_time_ms…}`; `create_routine` = `{content}`; `buscar_veiculo` = `{content, data, found}` (novo no atendimento N2); `raio_x_comercial` **continua texto** (o real devolve `str`). ⚠️ O `rascunho` do compositor é escrito à mão (o compositor real lê a base no banco) com os MESMOS fatos da v1.
- `bancada.py`: o texto do turno é o `final_response` do estado quando existe (como `graph.py` faz ao responder), senão a última AIMessage; `estado.contexto_da_apolice_por_turno` no rastro; e `FLAGS_DO_AGENTE = {"POLICY_INTELLIGENCE_V2": "true"}` aplicado só durante o motor do agente (a configuração que o Founder foi orientado a confirmar — P-E0015-06; desligada, o modelo nem redige a resposta pós-consulta).

**Prova, braço `duble:perfeito`, linha de controle v1 (texto, `git show HEAD:…`) × v2 (forma real)** — script `scratchpad/f6/prova_n2_forma.py`:

| caso | corpus | resultado | `infocap_policy_context` após cada turno | onde "Allianz" está na entrada do modelo no turno 2 |
|---|---|---|---|---|
| chat-n2-apolice-e-cobertura | v1 | PASS | `[[], []]` (nunca nasce) | só na AIMessage do turno 1 |
| chat-n2-apolice-e-cobertura | v2 | **FAIL** | `[[document,name,policy_numbers,selected_policy_number,selected_policy_ramo,source], idem]` ✅ | ToolMessage |
| atd-n2-guincho-feliz | v1 | PASS | `[[],[],[]]` | AIMessage |
| atd-n2-guincho-feliz | v2 | PASS | `[[],[],[]]` | AIMessage (turnos 2 e 3) ✅ |

📊 **O ELO, medido (e que refuta metade da premissa):** no **atendimento** o contexto da apólice **não nasce nem com a forma real** — o conector devolve só `client_name_masked/client_document_masked` para papel não-core, e `nodes._safe_infocap_policy_context` exige `client_document` ou `client_name` → `None` (📊 chamada direta com o `data` mascarado → `None`; com o do core → dict com `selected_policy_ramo='auto'`). A seguradora continua no turno 2 do atendimento **pela resposta do modelo**, não pelo contexto. ⚠️ Consequência de PRODUTO: a decisão "o ramo da apólice vence o do modelo" (`nodes.py`, `selected_policy_ramo` → `insurer_dispatch`) **nunca dispara no atendimento**. E com `POLICY_INTELLIGENCE_V2` **desligada** (medido: mesmo script com `F6_V2=false`) o turno da consulta termina no rascunho (`final_response`) que **não entra no histórico**, a ToolMessage é comprimida no turno seguinte, e **"Allianz" some da entrada do modelo no turno 2** (`'Allianz' em=[]`).

**🔴 Defeito de PRODUTO que a forma real expôs (v2 ligada, Chat Principal):** pergunta de detalhe com anáfora ("Ela cobre eletricista?") com contexto de apólice → `agent_node` força a consulta (`_policy_context_tool_args`) → `should_continue_after_tools` devolve `"agent"` (v2) → força DE NOVO (a última humana é a mesma). 📊 7 consultas forçadas seguidas, até a janela de 15 mensagens derrubar a pergunta; o `perfeito` responde sem ela e reprova. Um modelo real às vezes se salva (📊 `claude-sonnet-5` = PPB nesse caso), mas o laço existe. Registrado nos testes como `xfail(strict=True)` (3 casos + 1 parâmetro) — consertado o produto, ficam vermelhos. **Não consertei: é do produto, o gerente decide.**

**(b) Portal com o corpo do provedor do braço.** `modelo_do_portal.decidir(..., rota=None)` e `adaptive.decide_next_action(..., rota=None)`: com `rota` (um `ModeloDoPortal`), `montar_pedido` usa o provedor/superfície/esforço do braço; sem ela, nada muda. A bancada monta a rota pelo resolvedor (`rota_do_portal_para`) e posta o corpo pelo transporte do worker (`chamador_http_do_braco`: teto antes, custo por `usage_service.calculate_cost`, 1 linha no ledger `bancada` sem empresa). Testes: `test_sem_rota_injetada_nada_muda` (controle: gpt-4o, JSON mode, `temperature 0`, banco lido 1×) e `test_rota_injetada_monta_o_corpo_do_provedor_do_braco` ×3 (Sonnet 5 → `/v1/messages`, `output_config.effort`, **sem** temperature; GPT-6 Sol → `/v1/responses`, `reasoning.effort`, `store=false`, `text.format json_object`, sem temperature; gpt-4o-mini → chat completions **com** temperature). Mutação `modelo = await resolver_rota()` → 3 FAIL, controle PASS.

**(c) "Anomalia" de cache da Luna — REFUTADA.** 📊 Uma chamada crua `responses.create(model="gpt-6-luna")`: `usage.input_tokens_details = {'cache_write_tokens': 0, 'cached_tokens': 0}` — o GPT-6 **reporta** escrita de cache, e a langchain a mapeia para `input_token_details.cache_creation`. A OpenAI **cobra** escrita de cache no GPT-6 (EVIDENCIAS/04 l.14–19: Luna cache write US$ 0,125 = 1,25 × 0,10; Sol 2,50 = 1,25 × 2,00), e o catálogo tem `cache_write_multiplier 1.25` e `cached_input_multiplier 0.10` para os três GPT-6. Conferência da linha da Luna (10.971 in, 10.968 cw, 130 out): 3×0,10 + 10.968×0,125 + 130×0,50 por M = **US$ 0,001436** = o gravado. O ledger está **certo**; nada a consertar no `cost_callback`.

**(d) Infra engolida pelo motor.** `Medidor` conta `tentativas`; em `_rodar_caso`, FAIL/PARTIAL com chamada tentada e não concluída (sem falha injetada) vira `BLOCKED_BY_INFRA` com o motivo. Teste `test_erro_do_provedor_engolido_pelo_motor_e_infra_e_nao_falha_do_modelo` (controle: o braço que responde e erra continua FAIL). Os JSONs já gravados não foram reclassificados.

## 2. As tabelas (📊 todas; k=3; `dup` = efeitos duplicados; `infra` = tentativas BLOCKED_BY_INFRA)

⚠️ pass^k e crít^k contam só os casos em que NENHUMA das k tentativas foi bloqueada; com muita infra, o
denominador encolhe e o número engana (ex.: `gpt-6-luna:medium` atendimento N1 — 43/90 bloqueadas).

### memoria · N1 (15 casos, 0 críticos)
📊 memoria · N1 · k=3 · grupo `413ec73a-ea72-494a-834a-7392b7b6c7d1` · 15 casos (0 críticos) · gasto US$ 0.1376 · arquivo memoria_N1_413ec73a-ea72-494a-834a-7392b7b6c7d1.json

`cd backend && python scripts/bancada.py --papel memoria --nivel N1 --k 3 --gravar --por-caso --teto-usd 3 --braco duble:perfeito --braco duble:burro --braco openai:gpt-4o-mini --braco openai:gpt-6-luna:low --braco openai:gpt-6-luna:medium --braco anthropic:claude-haiku-4-5-20251001 --braco anthropic:claude-sonnet-5:low --braco openai:gpt-5.6-terra:low` · releitura: `python scripts/bancada.py --relatorio 413ec73a-ea72-494a-834a-7392b7b6c7d1`

| braço | pass@1 | pass^k | crít^k | dup | infra | custo total | custo/sucesso | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| duble:perfeito | 100.0% | 100.0% | — | 0 | 0 | 0.0117 | 0.0003 | 0 | 0 |
| duble:burro | 53.3% | 53.3% | — | 0 | 0 | 0.0108 | 0.0004 | 0 | 1 |
| openai:gpt-4o-mini | 71.1% | 66.7% | — | 0 | 0 | 0.0020 | 0.0001 | 1048 | 1624 |
| openai:gpt-6-luna:low | 86.7% | 86.7% | — | 0 | 0 | 0.0021 | 0.0001 | 1688 | 2948 |
| openai:gpt-6-luna:medium | 86.7% | 86.7% | — | 0 | 0 | 0.0026 | 0.0001 | 1725 | 3440 |
| anthropic:claude-haiku-4-5-20251001 | 68.9% | 53.3% | — | 0 | 0 | 0.0231 | 0.0007 | 1125 | 1880 |
| anthropic:claude-sonnet-5:low | 77.8% | 66.7% | — | 0 | 0 | 0.0567 | 0.0016 | 1599 | 2112 |
| openai:gpt-5.6-terra:low | 82.2% | 80.0% | — | 0 | 0 | 0.0287 | 0.0008 | 1336 | 1826 |

### visao · N1 (10 imagens SINTÉTICAS — evidência fraca)
📊 visao · N1 · k=3 · grupo `23655440-a026-4ee3-b672-5db878fce6ae` · 10 casos (2 críticos) · gasto US$ 0.1107 · arquivo visao_N1_23655440-a026-4ee3-b672-5db878fce6ae.json

`cd backend && python scripts/bancada.py --papel visao --nivel N1 --k 3 --gravar --por-caso --teto-usd 3 --braco duble:perfeito --braco duble:burro --braco openai:gpt-4o-mini --braco openai:gpt-6-luna:low --braco openai:gpt-6-sol:low --braco anthropic:claude-sonnet-5:low --braco anthropic:claude-haiku-4-5-20251001 --braco anthropic:claude-opus-5-5:low` · releitura: `python scripts/bancada.py --relatorio 23655440-a026-4ee3-b672-5db878fce6ae`

| braço | pass@1 | pass^k | crít^k | dup | infra | custo total | custo/sucesso | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| duble:perfeito | 100.0% | 100.0% | 100.0% | 0 | 0 | 0.0046 | 0.0002 | 0 | 25 |
| duble:burro | 0.0% | 0.0% | 0.0% | 0 | 0 | 0.0032 | — | 0 | 0 |
| openai:gpt-4o-mini | 93.3% | 90.0% | 100.0% | 0 | 0 | 0.0535 | 0.0019 | 2081 | 3973 |
| openai:gpt-6-luna:low | 100.0% | 100.0% | 100.0% | 0 | 0 | 0.0024 | 0.0001 | 1674 | 2487 |
| openai:gpt-6-sol:low | 100.0% | 100.0% | 100.0% | 0 | 0 | 0.0470 | 0.0016 | 2123 | 2896 |
| anthropic:claude-sonnet-5:low | — | — | — | 0 | 30 | 0.0000 | — | None | None |
| anthropic:claude-haiku-4-5-20251001 | — | — | — | 0 | 30 | 0.0000 | — | None | None |
| anthropic:claude-opus-5-5:low | — | — | — | 0 | 30 | 0.0000 | — | None | None |

### portal_decisao · N1 (16 casos, todos críticos)
📊 portal_decisao · N1 · k=3 · grupo `9d13e47d-3dec-409c-a2f7-87a022e4fb6a` · 16 casos (16 críticos) · gasto US$ 0.4079 · arquivo portal_decisao_N1_9d13e47d-3dec-409c-a2f7-87a022e4fb6a.json

`cd backend && python scripts/bancada.py --papel portal_decisao --nivel N1 --k 3 --gravar --por-caso --teto-usd 4 --braco duble:perfeito --braco duble:burro --braco openai:gpt-4o --braco openai:gpt-4o-mini --braco openai:gpt-6-sol:low --braco openai:gpt-6-sol:medium --braco openai:gpt-6-luna:medium --braco anthropic:claude-sonnet-5:low --braco anthropic:claude-sonnet-5:medium --braco anthropic:claude-opus-5-5:medium --braco anthropic:claude-haiku-4-5-20251001` · releitura: `python scripts/bancada.py --relatorio 9d13e47d-3dec-409c-a2f7-87a022e4fb6a`

| braço | pass@1 | pass^k | crít^k | dup | infra | custo total | custo/sucesso | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| duble:perfeito | 100.0% | 100.0% | 100.0% | 0 | 3 | 0.0728 | 0.0016 | 0 | 0 |
| duble:burro | 0.0% | 0.0% | 0.0% | 0 | 3 | 0.0692 | — | 0 | 0 |
| openai:gpt-4o | 92.7% | 91.7% | 91.7% | 0 | 7 | 0.1412 | 0.0037 | 1940 | 2600 |
| openai:gpt-4o-mini | 86.7% | 86.7% | 86.7% | 0 | 3 | 0.0079 | 0.0002 | 1830 | 2208 |
| openai:gpt-6-sol:low | 100.0% | 100.0% | 100.0% | 0 | 5 | 0.0535 | 0.0012 | 2921 | 3484 |
| openai:gpt-6-sol:medium | 100.0% | 100.0% | 100.0% | 0 | 5 | 0.0597 | 0.0014 | 2976 | 4408 |
| openai:gpt-6-luna:medium | 100.0% | 100.0% | 100.0% | 0 | 3 | 0.0036 | 0.0001 | 2893 | 3606 |
| anthropic:claude-sonnet-5:low | — | — | — | 0 | 48 | 0.0000 | — | None | None |
| anthropic:claude-sonnet-5:medium | — | — | — | 0 | 48 | 0.0000 | — | None | None |
| anthropic:claude-opus-5-5:medium | — | — | — | 0 | 48 | 0.0000 | — | None | None |
| anthropic:claude-haiku-4-5-20251001 | — | — | — | 0 | 48 | 0.0000 | — | None | None |

### dispatch · N1 (15, todos críticos) — ⚠️ SEM MEDIÇÃO VÁLIDA (ver §3)
📊 dispatch · N1 · k=3 · grupo `528c334a-7731-4591-98d9-08a4134c3671` · 15 casos (15 críticos) · gasto US$ 0.0254 · arquivo dispatch_N1_528c334a-7731-4591-98d9-08a4134c3671.json

`cd backend && python scripts/bancada.py --papel dispatch --nivel N1 --k 3 --gravar --por-caso --teto-usd 4 --braco duble:perfeito --braco duble:burro --braco anthropic:claude-opus-5 --braco anthropic:claude-opus-5-5:medium --braco anthropic:claude-opus-5-5:high --braco anthropic:claude-sonnet-5:medium --braco openai:gpt-6-sol:medium --braco openai:gpt-6-sol:high --braco openai:gpt-6-luna:medium` · releitura: `python scripts/bancada.py --relatorio 528c334a-7731-4591-98d9-08a4134c3671`

| braço | pass@1 | pass^k | crít^k | dup | infra | custo total | custo/sucesso | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| duble:perfeito | 100.0% | 100.0% | 100.0% | 0 | 0 | 0.0073 | 0.0002 | 0 | 0 |
| duble:burro | 20.0% | 20.0% | 20.0% | 0 | 0 | 0.0087 | 0.0010 | 0 | 0 |
| anthropic:claude-opus-5 | 20.0% | 20.0% | 20.0% | 0 | 0 | 0.0000 | 0.0000 | 282 | 346 |
| anthropic:claude-opus-5-5:medium | 20.0% | 20.0% | 20.0% | 0 | 0 | 0.0000 | 0.0000 | 276 | 305 |
| anthropic:claude-opus-5-5:high | 20.0% | 20.0% | 20.0% | 0 | 0 | 0.0000 | 0.0000 | 274 | 327 |
| anthropic:claude-sonnet-5:medium | 20.0% | 20.0% | 20.0% | 0 | 0 | 0.0000 | 0.0000 | 275 | 305 |
| openai:gpt-6-sol:medium | 20.0% | 20.0% | 20.0% | 0 | 0 | 0.0025 | 0.0003 | 698 | 2349 |
| openai:gpt-6-sol:high | 20.0% | 20.0% | 20.0% | 0 | 0 | 0.0069 | 0.0008 | 744 | 1891 |
| openai:gpt-6-luna:medium | 20.0% | 20.0% | 20.0% | 0 | 0 | 0.0001 | 0.0000 | 689 | 1667 |

### cobranca · N1 (10, 5 críticos)
📊 cobranca · N1 · k=3 · grupo `b77b939b-5c6f-4094-8042-de3d71c4a339` · 10 casos (5 críticos) · gasto US$ 2.2557 · arquivo cobranca_N1_b77b939b-5c6f-4094-8042-de3d71c4a339.json

`cd backend && python scripts/bancada.py --papel cobranca --nivel N1 --k 3 --gravar --por-caso --teto-usd 8 --braco duble:perfeito --braco duble:burro --braco anthropic:claude-sonnet-5 --braco anthropic:claude-sonnet-5:low --braco anthropic:claude-sonnet-5:medium --braco anthropic:claude-sonnet-5:high --braco anthropic:claude-opus-5-5:medium --braco anthropic:claude-opus-5-5:high --braco openai:gpt-6-sol:medium --braco openai:gpt-6-sol:high --braco openai:gpt-6-luna:medium --braco openai:gpt-5.6-terra:medium --braco anthropic:claude-haiku-4-5-20251001` · releitura: `python scripts/bancada.py --relatorio b77b939b-5c6f-4094-8042-de3d71c4a339`

| braço | pass@1 | pass^k | crít^k | dup | infra | custo total | custo/sucesso | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| duble:perfeito | 100.0% | 100.0% | 100.0% | 0 | 0 | 0.1714 | 0.0057 | 20 | 42 |
| duble:burro | 50.0% | 50.0% | 40.0% | 0 | 0 | 0.1714 | 0.0114 | 21 | 39 |
| anthropic:claude-sonnet-5 | 50.0% | 50.0% | 40.0% | 0 | 0 | 0.3697 | 0.0246 | 5030 | 13294 |
| anthropic:claude-sonnet-5:low | 53.3% | 50.0% | 40.0% | 0 | 0 | 0.2607 | 0.0163 | 3581 | 5681 |
| anthropic:claude-sonnet-5:medium | 53.3% | 50.0% | 40.0% | 0 | 0 | 0.3200 | 0.0200 | 4294 | 8615 |
| anthropic:claude-sonnet-5:high | 50.0% | 50.0% | 40.0% | 0 | 0 | 0.3181 | 0.0212 | 7525 | 17587 |
| anthropic:claude-opus-5-5:medium | 100.0% | — | — | 0 | 24 | 0.2034 | 0.0339 | 6064 | 14619 |
| anthropic:claude-opus-5-5:high | — | — | — | 0 | 30 | 0.0000 | — | None | None |
| openai:gpt-6-sol:medium | 73.3% | 60.0% | 60.0% | 0 | 0 | 0.2133 | 0.0097 | 3936 | 11980 |
| openai:gpt-6-sol:high | 69.6% | 25.0% | 0.0% | 0 | 7 | 0.2177 | 0.0136 | 4827 | 8501 |
| openai:gpt-6-luna:medium | 83.3% | 80.0% | 80.0% | 0 | 0 | 0.0100 | 0.0004 | 3439 | 5873 |
| openai:gpt-5.6-terra:medium | — | — | — | 0 | 30 | 0.0000 | — | None | None |
| anthropic:claude-haiku-4-5-20251001 | — | — | — | 0 | 30 | 0.0000 | — | None | None |

### atendimento · N1 (30, 26 críticos)
📊 atendimento · N1 · k=3 · grupo `03af4327-80c5-4ec6-b21b-624299cd8542` · 30 casos (26 críticos) · gasto US$ 3.3268 · arquivo atendimento_N1_03af4327-80c5-4ec6-b21b-624299cd8542.json

`cd backend && python scripts/bancada.py --papel atendimento --nivel N1 --k 3 --gravar --por-caso --teto-usd 15 --braco duble:perfeito --braco duble:burro --braco anthropic:claude-sonnet-5 --braco anthropic:claude-sonnet-5:low --braco anthropic:claude-sonnet-5:medium --braco anthropic:claude-sonnet-5:high --braco anthropic:claude-opus-5-5:medium --braco anthropic:claude-opus-5-5:high --braco openai:gpt-6-sol:medium --braco openai:gpt-6-sol:high --braco openai:gpt-6-luna:medium --braco openai:gpt-5.6-terra:medium --braco anthropic:claude-haiku-4-5-20251001` · releitura: `python scripts/bancada.py --relatorio 03af4327-80c5-4ec6-b21b-624299cd8542`

| braço | pass@1 | pass^k | crít^k | dup | infra | custo total | custo/sucesso | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| duble:perfeito | 100.0% | 100.0% | 100.0% | 0 | 0 | 0.5187 | 0.0058 | 20 | 40 |
| duble:burro | 13.3% | 13.3% | 0.0% | 0 | 0 | 0.5154 | 0.0430 | 23 | 35 |
| anthropic:claude-sonnet-5 | 68.9% | 56.7% | 50.0% | 0 | 0 | 0.8187 | 0.0132 | 4853 | 13236 |
| anthropic:claude-sonnet-5:low | 80.0% | — | — | 0 | 50 | 0.2812 | 0.0088 | 4480 | 7396 |
| anthropic:claude-sonnet-5:medium | — | — | — | 0 | 90 | 0.0000 | — | None | None |
| anthropic:claude-sonnet-5:high | — | — | — | 0 | 90 | 0.0000 | — | None | None |
| anthropic:claude-opus-5-5:medium | — | — | — | 0 | 90 | 0.0000 | — | None | None |
| anthropic:claude-opus-5-5:high | — | — | — | 0 | 90 | 0.0000 | — | None | None |
| openai:gpt-6-sol:medium | 66.7% | 71.4% | 71.4% | 0 | 27 | 0.4710 | 0.0112 | 3339 | 5423 |
| openai:gpt-6-sol:high | 66.7% | 60.0% | 53.8% | 0 | 0 | 0.7038 | 0.0117 | 4211 | 8891 |
| openai:gpt-6-luna:medium | 80.9% | 100.0% | 100.0% | 0 | 43 | 0.0180 | 0.0005 | 3077 | 5839 |
| openai:gpt-5.6-terra:medium | — | — | — | 0 | 90 | 0.0000 | — | None | None |
| anthropic:claude-haiku-4-5-20251001 | — | — | — | 0 | 90 | 0.0000 | — | None | None |

### atendimento · N1 · TETO (só críticos)
📊 atendimento · N1 · k=3 · grupo `89661ceb-64ae-4ce1-8904-2a1f1a0fde1c` · 26 casos (26 críticos) · gasto US$ 4.2613 · arquivo atendimento_N1_critico_89661ceb-64ae-4ce1-8904-2a1f1a0fde1c.json

`cd backend && python scripts/bancada.py --papel atendimento --nivel N1 --k 3 --gravar --por-caso --teto-usd 12 --critico --braco duble:perfeito --braco duble:burro --braco openai:gpt-6-astra:high` · releitura: `python scripts/bancada.py --relatorio 89661ceb-64ae-4ce1-8904-2a1f1a0fde1c`

| braço | pass@1 | pass^k | crít^k | dup | infra | custo total | custo/sucesso | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| duble:perfeito | 100.0% | 100.0% | 100.0% | 0 | 0 | 0.4485 | 0.0057 | 24 | 59 |
| duble:burro | 0.0% | 0.0% | 0.0% | 0 | 0 | 0.4450 | — | 19 | 34 |
| openai:gpt-6-astra:high | 68.4% | 83.3% | 83.3% | 0 | 21 | 3.3678 | 0.0864 | 9809 | 18013 |

### atendimento · N2 (10 trajetórias, todas críticas) — ⚠️ quase só infra
📊 atendimento · N2 · k=3 · grupo `a2fb9be0-d25c-4789-9846-38d7f76ad300` · 10 casos (10 críticos) · gasto US$ 2.6106 · arquivo atendimento_N2_a2fb9be0-d25c-4789-9846-38d7f76ad300.json

`cd backend && python scripts/bancada.py --papel atendimento --nivel N2 --k 3 --gravar --por-caso --teto-usd 18 --braco duble:perfeito --braco duble:burro --braco anthropic:claude-sonnet-5 --braco anthropic:claude-sonnet-5:low --braco anthropic:claude-sonnet-5:medium --braco anthropic:claude-sonnet-5:high --braco anthropic:claude-opus-5-5:medium --braco anthropic:claude-opus-5-5:high --braco openai:gpt-6-sol:medium --braco openai:gpt-6-sol:high --braco openai:gpt-6-luna:medium --braco openai:gpt-5.6-terra:medium --braco anthropic:claude-haiku-4-5-20251001` · releitura: `python scripts/bancada.py --relatorio a2fb9be0-d25c-4789-9846-38d7f76ad300`

| braço | pass@1 | pass^k | crít^k | dup | infra | custo total | custo/sucesso | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| duble:perfeito | 100.0% | 100.0% | 100.0% | 0 | 0 | 0.7835 | 0.0261 | 45 | 129 |
| duble:burro | 20.0% | 20.0% | 20.0% | 0 | 0 | 0.4462 | 0.0744 | 32 | 72 |
| anthropic:claude-sonnet-5 | 50.0% | — | — | 0 | 26 | 0.2458 | 0.1229 | 27936 | 43604 |
| anthropic:claude-sonnet-5:low | — | — | — | 0 | 30 | 0.0000 | — | None | None |
| anthropic:claude-sonnet-5:medium | — | — | — | 0 | 30 | 0.0000 | — | None | None |
| anthropic:claude-sonnet-5:high | — | — | — | 0 | 30 | 0.0000 | — | None | None |
| anthropic:claude-opus-5-5:medium | — | — | — | 0 | 30 | 0.0000 | — | None | None |
| anthropic:claude-opus-5-5:high | — | — | — | 0 | 30 | 0.0000 | — | None | None |
| openai:gpt-6-sol:medium | 16.7% | — | — | 0 | 24 | 0.3451 | 0.3451 | 29451 | 43920 |
| openai:gpt-6-sol:high | 20.0% | — | — | 1 | 20 | 0.7761 | 0.3881 | 33347 | 83048 |
| openai:gpt-6-luna:medium | 33.3% | — | — | 0 | 27 | 0.0139 | 0.0139 | 19853 | 45349 |
| openai:gpt-5.6-terra:medium | — | — | — | 0 | 30 | 0.0000 | — | None | None |
| anthropic:claude-haiku-4-5-20251001 | — | — | — | 0 | 30 | 0.0000 | — | None | None |

### chat_principal · N1 (30, 17 críticos)
📊 chat_principal · N1 · k=3 · grupo `61b8526f-6e53-475d-9249-84098bd73cab` · 30 casos (17 críticos) · gasto US$ 1.8335 · arquivo chat_principal_N1_61b8526f-6e53-475d-9249-84098bd73cab.json

`cd backend && python scripts/bancada.py --papel chat_principal --nivel N1 --k 3 --gravar --por-caso --teto-usd 15 --braco duble:perfeito --braco duble:burro --braco anthropic:claude-sonnet-5 --braco anthropic:claude-sonnet-5:low --braco anthropic:claude-sonnet-5:medium --braco anthropic:claude-sonnet-5:high --braco anthropic:claude-opus-5-5:medium --braco anthropic:claude-opus-5-5:high --braco openai:gpt-6-sol:medium --braco openai:gpt-6-sol:high --braco openai:gpt-6-luna:medium --braco openai:gpt-5.6-terra:medium --braco anthropic:claude-haiku-4-5-20251001` · releitura: `python scripts/bancada.py --relatorio 61b8526f-6e53-475d-9249-84098bd73cab`

| braço | pass@1 | pass^k | crít^k | dup | infra | custo total | custo/sucesso | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| duble:perfeito | 100.0% | 100.0% | 100.0% | 0 | 0 | 0.1741 | 0.0019 | 26 | 50 |
| duble:burro | 6.7% | 6.7% | 0.0% | 0 | 0 | 0.1702 | 0.0284 | 29 | 43 |
| anthropic:claude-sonnet-5 | 97.8% | 96.7% | 100.0% | 0 | 0 | 0.4306 | 0.0049 | 2361 | 8859 |
| anthropic:claude-sonnet-5:low | 100.0% | 100.0% | 100.0% | 0 | 0 | 0.4087 | 0.0045 | 2832 | 7853 |
| anthropic:claude-sonnet-5:medium | 100.0% | — | — | 0 | 53 | 0.1957 | 0.0053 | 3405 | 8725 |
| anthropic:claude-sonnet-5:high | — | — | — | 0 | 90 | 0.0000 | — | None | None |
| anthropic:claude-opus-5-5:medium | — | — | — | 0 | 90 | 0.0000 | — | None | None |
| anthropic:claude-opus-5-5:high | — | — | — | 0 | 90 | 0.0000 | — | None | None |
| openai:gpt-6-sol:medium | 100.0% | 100.0% | 100.0% | 0 | 24 | 0.1870 | 0.0028 | 2303 | 4102 |
| openai:gpt-6-sol:high | 100.0% | 100.0% | 100.0% | 0 | 4 | 0.2542 | 0.0030 | 2478 | 4360 |
| openai:gpt-6-luna:medium | 100.0% | 100.0% | 100.0% | 0 | 1 | 0.0130 | 0.0001 | 1860 | 3629 |
| openai:gpt-5.6-terra:medium | — | — | — | 0 | 90 | 0.0000 | — | None | None |
| anthropic:claude-haiku-4-5-20251001 | — | — | — | 0 | 90 | 0.0000 | — | None | None |

### chat_principal · N1 · TETO (só críticos)
📊 chat_principal · N1 · k=3 · grupo `45417ce7-3d65-4c83-86a0-0de6b02ae6bf` · 17 casos (17 críticos) · gasto US$ 0.4689 · arquivo chat_principal_N1_critico_45417ce7-3d65-4c83-86a0-0de6b02ae6bf.json

`cd backend && python scripts/bancada.py --papel chat_principal --nivel N1 --k 3 --gravar --por-caso --teto-usd 10 --critico --braco duble:perfeito --braco duble:burro --braco openai:gpt-6-astra:high` · releitura: `python scripts/bancada.py --relatorio 45417ce7-3d65-4c83-86a0-0de6b02ae6bf`

| braço | pass@1 | pass^k | crít^k | dup | infra | custo total | custo/sucesso | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| duble:perfeito | 100.0% | 100.0% | 100.0% | 0 | 0 | 0.1001 | 0.0020 | 31 | 43 |
| duble:burro | 0.0% | 0.0% | 0.0% | 0 | 0 | 0.0966 | — | 26 | 50 |
| openai:gpt-6-astra:high | 100.0% | — | — | 0 | 39 | 0.2723 | 0.0227 | 3247 | 6128 |

### chat_principal · N2 (8, 6 críticos)
📊 chat_principal · N2 · k=3 · grupo `23e6cfa2-7aa7-4627-9cef-82f67081a919` · 8 casos (6 críticos) · gasto US$ 0.9017 · arquivo chat_principal_N2_23e6cfa2-7aa7-4627-9cef-82f67081a919.json

`cd backend && python scripts/bancada.py --papel chat_principal --nivel N2 --k 3 --gravar --por-caso --teto-usd 14 --braco duble:perfeito --braco duble:burro --braco anthropic:claude-sonnet-5 --braco anthropic:claude-sonnet-5:low --braco anthropic:claude-sonnet-5:medium --braco anthropic:claude-sonnet-5:high --braco anthropic:claude-opus-5-5:medium --braco anthropic:claude-opus-5-5:high --braco openai:gpt-6-sol:medium --braco openai:gpt-6-sol:high --braco openai:gpt-6-luna:medium --braco openai:gpt-5.6-terra:medium --braco anthropic:claude-haiku-4-5-20251001` · releitura: `python scripts/bancada.py --relatorio 23e6cfa2-7aa7-4627-9cef-82f67081a919`

| braço | pass@1 | pass^k | crít^k | dup | infra | custo total | custo/sucesso | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| duble:perfeito | 62.5% | 62.5% | 50.0% | 0 | 0 | 0.1573 | 0.0105 | 58 | 203 |
| duble:burro | 25.0% | 25.0% | 33.3% | 0 | 0 | 0.0736 | 0.0123 | 31 | 54 |
| anthropic:claude-sonnet-5 | 90.0% | — | — | 0 | 14 | 0.2325 | 0.0258 | 11704 | 18149 |
| anthropic:claude-sonnet-5:low | — | — | — | 0 | 24 | 0.0000 | — | None | None |
| anthropic:claude-sonnet-5:medium | — | — | — | 0 | 24 | 0.0000 | — | None | None |
| anthropic:claude-sonnet-5:high | — | — | — | 0 | 24 | 0.0000 | — | None | None |
| anthropic:claude-opus-5-5:medium | — | — | — | 0 | 24 | 0.0000 | — | None | None |
| anthropic:claude-opus-5-5:high | — | — | — | 0 | 24 | 0.0000 | — | None | None |
| openai:gpt-6-sol:medium | 72.2% | 50.0% | 50.0% | 0 | 6 | 0.2703 | 0.0208 | 12021 | 17556 |
| openai:gpt-6-sol:high | 66.7% | — | — | 0 | 18 | 0.1478 | 0.0369 | 9162 | 31967 |
| openai:gpt-6-luna:medium | 79.2% | 75.0% | 83.3% | 0 | 0 | 0.0203 | 0.0011 | 12528 | 16280 |
| openai:gpt-5.6-terra:medium | — | — | — | 0 | 24 | 0.0000 | — | None | None |
| anthropic:claude-haiku-4-5-20251001 | — | — | — | 0 | 24 | 0.0000 | — | None | None |


## 3. A REGRA DE ESCOLHA (§5), aplicada literalmente

Elegível = braço real · 0 efeito duplicado · crít^k = 100 % (papel sem críticos: condição vazia). Entre
elegíveis, maior pass@1; **empate = diferença ≤ 1 caso do conjunto** (memória 1/15 = 6,7 pp · visão 1/10 = 10 pp ·
portal 1/16 = 6,2 pp · cobrança 1/10 = 10 pp · atendimento N1 1/30 = 3,3 pp · chat N1 1/30 = 3,3 pp) → menor
custo/sucesso. ⚠️ A SPEC §5 diz "empate dentro de 2 pp"; apliquei o critério do pacote (≤ 1 caso); com 2 pp
nenhum resultado abaixo muda, exceto memória (Luna low 86,7 × Luna medium 86,7 — mesmo vencedor).

| papel · nível | elegíveis 📊 | conta | primário | reserva (outro provedor) |
|---|---|---|---|---|
| memoria N1 | 6 (sem críticos) | topo 86,7 % (Luna low, Luna medium); Terra low 82,2 % está dentro de 6,7 pp; custo/suc. Luna low US$ 0,000055 < Luna med 0,000067 < Terra 0,00077 | **openai:gpt-6-luna:low** | **anthropic:claude-sonnet-5:low** (77,8 %; Haiku 68,9 %) |
| visao N1 | 3 (Anthropic 100 % infra) | Luna low 100 %, Sol low 100 %, 4o-mini 93,3 % (dentro de 10 pp); custo/suc. Luna 0,000081 (Sol 0,0016; mini 0,0019) | **openai:gpt-6-luna:low** | **nenhuma medida** (Anthropic sem crédito) |
| portal N1 | 3 | Luna med / Sol low / Sol med = 100 %, crít^k 100 %; custo/suc. Luna 0,00008 (Sol low 0,0012) | **openai:gpt-6-luna:medium** | **nenhuma medida** |
| dispatch N1 | — | medição inválida (§0) | **sem decisão** | — |
| cobranca N1 | **NENHUM** | melhor crít^k: Luna medium 80 % (pass@1 83,3 %); baseline Sonnet 5 crít^k 40 % = o `burro` | **gerente decide** | — |
| atendimento N1 | 1: Luna medium | 80,9 % pass@1, crít^k 100 % **sobre só 2 casos julgáveis** (43/90 tentativas bloqueadas; 28 rate limit + 15 sem crédito) | ⚠️ Luna medium **por regra, sem confiança** | nenhuma |
| atendimento N2 | **NENHUM** | Sonnet 5 50 % (26/30 infra); Luna/Sol quase tudo infra | **sem decisão** | — |
| chat N1 | 5 | Sonnet low 100 %, Luna med 100 %, Sol med/high 100 %, Sonnet 97,8 % (dentro de 3,3 pp); custo/suc. Luna 0,00015 (Sonnet low 0,0045; Sonnet 0,0049) | **openai:gpt-6-luna:medium** | **anthropic:claude-sonnet-5:low** |
| chat N2 | **NENHUM** | melhor crít^k Luna medium 83,3 %; o `perfeito` tem 62,5 % (o laço do §1) | **sem decisão** | — |

## 4. Baseline × vencedor, caso a caso (📊 tentativas P/F/B)

- **atendimento N1 (Sonnet 5 × Luna medium)** — base falha, Luna passa: `atd-n1-cpf-para-brisa` FFF×PBP (não chamou `infocap_policy_lookup`) · `atd-n1-portal-farol` FFF×PBB, `-lanterna` FFP×PBB, `-parabrisa-reparo` FPP×BPB (não chamou `portal_action`) · `atd-n1-risco-alagamento` FFF×BPB e `humano-bati-carro` FFF×BBB, `humano-cade-guincho` FPF×BBB (não chamou `request_human_agent`) · `sem-id-eletricista` PFP×PBB, `sem-id-mecanico` FFP×PBP (não pediu CPF). Luna falha, base passa: `sem-id-pane` PPP×PBF, `sem-id-ventania-vidro` PPP×FBF (não pediu CPF).
- **chat N1** — `chat-n1-o-que-e-franquia` Sonnet FPF (chamou `knowledge_base_search` numa pergunta conceitual) × Luna PPP.
- **portal** — `portal-n1-80-lado-sem-base-pergunta` gpt-4o FFF (`action='check'`) × Luna PPP; e `portal-n1-7-lojas-nao-agenda` gpt-4o-mini FFF (`ask_human`). A reserva calada antiga (mini) era 📊 86,7 % × 92,7 % do gpt-4o.
- **memória** — gpt-4o-mini FFF × Luna low PPP: `mem-n1-prefere-tarde`, `-quer-dados-completos`, `-so-vigentes`. Sonnet low e Haiku guardaram CPF/nome que não deviam (`mem-n1-cpf-nao-guarda` Sonnet FFF, Haiku FFP; `mem-n1-nome-nao-guarda` Sonnet FFF).
- **cobrança** — Sonnet 5 FFF × Luna PPP: `cob-n1-p09a-nao_quero`, `-p21a-outro` (não chamou `request_human_agent`) e `-p19a-duvida` — ⚠️ este é **falha de ORÁCULO**: `nao_deve_conter: ["é golpe"]` casa dentro de "Não **é golpe**, sou da Corretora…" (negação reprovada). Não alterei o oráculo.

**Variância (casos que alternam PASS/FAIL nas k=3, sem contar infra) 📊:** atendimento N1 — Sonnet 5 **7 casos**, Sol high 5, Sol med 3, Luna 3 · memória — Haiku 5, Sonnet low 3 · cobrança — Sol med 3 · chat N1 — Sonnet 1.

## 5. Falha de MODELO × falha de ARNÊS

| suspeita de arnês / produto | evidência 📊 |
|---|---|
| laço da consulta forçada (v2 + contexto, core) | `perfeito` FFF em `chat-n2-apolice-e-cobertura`, `-429-retomada`, `-500-no-meio` |
| oráculo que reprova negação | `cob-n1-p19a-duvida` |
| `gpt-5.6-terra` com tools no catálogo errado | 400 do provedor, 100 % dos casos com tools |
| dispatch que engole erro | 20 % = `burro` para todos os braços, 0 chamadas concluídas |
| visão Anthropic | 100 % infra — **crédito**, não arnês (a mesma chamada crua dá o 400 de saldo) |

**O teto de qualidade (GPT-6 Astra high, só críticos):** atendimento N1 📊 pass@1 68,4 %, crít^k 83,3 % (21 bloqueadas — a conta OpenAI acabou durante ele); chat N1 📊 pass@1 100 % em 12 tentativas julgadas (39 bloqueadas). Opus 5.5 high **não rodou** (Anthropic sem crédito). Atendimento N2 e chat N2 no teto: **interrompidos** (sem crédito) — um `eval_run` ficou `running`. Conclusão possível hoje: no atendimento N1 **até o teto erra** casos críticos (ex.: `sem-id-*` sem pedir CPF, `portal-*` sem `portal_action`) → parte do que a régua chama de falha pode ser do prompt/arnês; sem Opus 5.5 high e sem o N2 não dá para separar.

## 6. O que ficou por medir

- **Tudo Anthropic depois de 19:18Z** (Sonnet 5 medium/high em quase tudo, Opus 5.5 medium/high, Haiku 4.5 nos papéis com tools, visão Anthropic, dispatch baseline Opus 5) e **tudo OpenAI depois de 19:41Z** (teto N2). ⛔ Destrava: 🧑 crédito nas duas contas.
- Refazer **sem paralelismo** (1 processo por provedor) atendimento N2, chat N2, dispatch e os braços Luna/Sol do atendimento N1 que caíram em rate limit.
- `gpt-5.6-terra` com tools: só depois de o catálogo apontar `responses`.
- BLOCKED por decisão: hyde, extrator_planos, juiz, transcrição (sem ouro/áudio — `bancada.PAPEIS`); Gemini, Grok, MiMo, DeepSeek, GLM (sem chave local — D-116-06).
- Gasto: ledger US$ 11,89 × `eval_runs` US$ 11,88 (braços reais) — diferença de US$ 0,01 não investigada (dublê não chama provedor e não entra em nenhum dos dois).
