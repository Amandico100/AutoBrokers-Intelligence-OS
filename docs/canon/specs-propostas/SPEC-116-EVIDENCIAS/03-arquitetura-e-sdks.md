# A GARGANTA DO MODELO — arquitetura, SDKs e proposta de evolução

> Investigação READ-ONLY · 23/09/2026 · árvore `AutoBrokers-FIX`, branch `docs/extra-002-investigacao-agger`, HEAD `543cc82`
> Nada foi editado no repo. Sondas e wheels ficaram só no scratchpad (`sondas/`, `wheels/`, `venv_novo/`).
> Marcação: 📊 = medido (comando ao lado) · 💭 = ilustrativo · FATO / INFERÊNCIA / RECOMENDAÇÃO separados.

Comandos-base usados (todos rodados a partir de `backend/`, salvo indicação):
```
S=<scratchpad>
python -u $S/sonda_fabrica.py                         # fábrica REAL com chaves falsas, libs PINADAS (global py3.14)
python -u $S/sondas/sonda_nova.py                     # kwargs da fábrica com libs PINADAS
$S/venv_novo/Scripts/python.exe $S/sondas/sonda_nova.py  # os MESMOS kwargs com libs ATUAIS
python -m pip index versions <pkg>                    # última estável no PyPI (23/09/2026)
Supabase MCP execute_sql (projeto dcajcvlzcjbmyapmklil, SÓ SELECT)
```
⚠️ "Instalada" abaixo = ambiente global do dev (Python 3.14.4, `C:\Users\amand\AppData\Local\Python\pythoncore-3.14-64`). **Não há venv no repo** (📊 `ls -d backend/venv backend/.venv .venv venv` → nada). O contêiner roda `python:3.11-slim` (`backend/Dockerfile:1`) e **não foi medido**.

---

## FINDINGS — por gravidade (teste do produto, protocolo §2)

| # | grav. | achado | evidência |
|---|---|---|---|
| F1 | **ALTA** (custo/latência de TODO atendimento) | O `reasoning_effort` gravado nos agentes é **ignorado para Anthropic**. 📊 Os 8 agentes de produção são `anthropic / claude-sonnet-5` com `reasoning_effort` = `low` (3) ou `medium` (5). A fábrica só passa effort para prefixo `o1`/`o3` (`llm_factory.py:200-201`); `_create_anthropic` não recebe o parâmetro (`llm_factory.py:180-181, 238-258`). Sonnet 5 roda **adaptive thinking ligado por padrão, effort `high`** quando nada é enviado (doc Anthropic, skill claude-api "Thinking & Effort"). Logo o atendimento roda em effort mais alto que o configurado. | sonda: `ANTHROPIC claude-sonnet-5 keys=['extra_headers','max_tokens','messages','model'] thinking=None output_config=None` · SQL `agents group by provider/model/role/reasoning_effort` |
| F2 | **ALTA** (ledger/preço — SPEC-062) | **Preço do Sonnet 5 errado no banco: 50 % acima.** 📊 `llm_pricing`: `claude-sonnet-5 in=3.00 out=15.00`. Página oficial (23/09): **$2 / $10**, "a subida para $3/$15 em 1/9 não ocorrerá". 📊 742 chamadas Sonnet 5 em 30 dias (US$ 14,88 registrados) → custo real ≈ 2/3 disso. O fallback em código (`usage_service.py:31-86`) nem tem `claude-sonnet-5`/`claude-opus-5`; modelo desconhecido vira preço de **gpt-4o-mini** (`usage_service.py:162-164`). | SQL `llm_pricing` + `token_usage_logs` 30d · https://platform.claude.com/docs/en/about-claude/pricing |
| F3 | **ALTA** (eval silenciosamente morto) | `juiz_llm.py:119` chama `LLMFactory.create_llm(provider=..., model=..., temperature=0)` — assinatura não existe. 📊 sonda: `TypeError LLMFactory.create_llm() got an unexpected keyword argument 'provider'`. O `except` (`juiz_llm.py:128-131`) transforma em `passou=False, confiança 0` → **todo veredito do juiz LLM é "falhou" desde que nasceu**, sem erro visível. | `sonda_fabrica.py` |
| F4 | **ALTA latente** (efeito duplicado) | Retry do turno inteiro por substring: `langchain_service.py:507-562` captura **qualquer** `Exception` e, se a mensagem contém `"connection"`, **re-executa `invoke_agent` com a mesma mensagem**. 📊 `openai/_exceptions.py:108` e `anthropic/_exceptions.py:87`: `APIConnectionError` tem mensagem `"Connection error."`. Um erro de rede do LLM **depois** de uma tool com efeito já ter rodado (no mesmo turno, 2ª ida ao modelo) refaz o turno → a tool pode rodar de novo. `portal_tool` e `auxiliary_run_tool` têm `idempotency_key`; handoff/envio/acionamento **não conferidos**. ⚠️ ELO (§0.3) NÃO medido: não provei que isso já aconteceu. | leitura + grep das mensagens do SDK |
| F5 | **MÉDIA** (400 garantido) | `_anthropic_supports_temperature` (`llm_factory.py:229-235`) bloqueia `temperature` só para a família 5; **Opus 4.7/4.8 também rejeitam qualquer sampling param (400)** (doc Anthropic). `claude-opus-4-8` está no allowlist (`langchain_service.py:138`) → agente com Opus 4.8 recebe `temperature` e quebra. 📊 sonda (libs pinadas): `ANTHROPIC claude-opus-4-8 keys=[...,'temperature'] temperature=0.7`. E o guarda `tests/test_llm_temperature_guard.py:28-36` **reimplementa** a regra (não chama o motor, CLAUDE.md §9.4) e **afirma** `claude-opus-4-8 AINDA recebe temperature` = verdade vencida (§9.3). | sonda + leitura |
| F6 | **MÉDIA** | Provedor desconhecido cai **silenciosamente** em `gpt-4o-mini` com a chave da OpenAI: `utils.py:45` (`key_map.get(provider, "OPENAI_API_KEY")`) + `llm_factory.py:191-195`. 📊 sonda: `xai grok-4 -> ChatOpenAI model=gpt-4o-mini`. O `CostCallback` recebe `model_name=model` **pedido** (`llm_factory.py:159`) → o ledger grava "grok-4" com tokens do gpt-4o-mini. O breaker também conta a falha na conta de `openai` (`relogio_do_modelo.py:305-308`). | sonda |
| F7 | **MÉDIA** (novo tenant nasce em modelo legado) | Blueprints/UI nascem em `openai / gpt-4o-mini`: `lib/admin/agent-blueprints-canonical.ts:65-66,103`, `lib/admin/agent-blueprints.ts:61`, `app/api/admin/sandbox/bootstrap-tenant/route.ts:104`. O atendimento (papel `attendance`) **não** é promovido pela política → uma corretora nova atende o segurado com gpt-4o-mini, enquanto as de produção estão em Sonnet 5 (mudança manual). Viola a intenção do §13.9 (produto igual para qualquer corretora). | grep |
| F8 | **MÉDIA** | `model_policy.py` (SPEC-013, "memória superada" pelo CLAUDE.md §4) **continua ativo** no runtime: promove papel `""`/`core` de modelo "econômico" para `CORE_CHAT_MODEL`/`gpt-4o` (`model_policy.py:29-35`). Efeitos colaterais: (a) os 14 chamadores de plataforma passam `agent_data` **sem** `agent_role` → são tratados como "core" → um `DISPATCH_LLM_MODEL=gpt-4o-mini` seria silenciosamente trocado por gpt-4o; (b) troca só o **modelo**, não o **provedor**: agente `anthropic` com `llm_model` vazio vira `ChatAnthropic(model="gpt-4o")` (`llm_factory.py:96,100`) → 404. Espelhado em TS (`lib/admin/agent-health.ts:153-158`). | leitura |
| F9 | **MÉDIA** | Histórico reconstruído **descarta blocos de thinking/reasoning e o `id`/`response_metadata`** da AIMessage: `utils.py:96-116` (`sanitize_ai_message`) usado em `nodes.py:1209-1211`. 📊 sonda: assistant turn reenviado tem só `['tool_use']`. Hoje funciona (📊 742 chamadas Sonnet 5 em 30 d sem erro conhecido), mas: Anthropic recomenda devolver thinking **inalterado** ("removê-los pode causar 400 de ordem/assinatura"; Fable 5.1/Opus 5.5 aplicam "preserved thinking" a contas novas desde 31/08); na Responses API da OpenAI, sem `reasoning` items/`resp_` id o raciocínio entre tool calls se perde e `use_previous_response_id` fica impossível. | sonda + skill claude-api/model-migration |
| F10 | **MÉDIA** | Dependências **não reprodutíveis**: `openai>=1.10.0`, `anthropic>=0.18.0`, `httpx>=0.26`, `langgraph-checkpoint-postgres>=2.0.0` (`requirements.txt:22,23,53,34`). O que o contêiner instala é decidido pelos limites das libs langchain no dia do build: 📊 `langchain_openai-1.0.3 METADATA: openai<3.0.0,>=1.109.1`; `langchain_anthropic-1.1.0: anthropic<1.0.0,>=0.73.0`. Hoje isso resolveria openai 2.54 / anthropic 0.125 (📊 `pip index versions`). Dois builds em dias diferentes = SDKs diferentes. | METADATA + pip index |
| F11 | **MÉDIA (segurança)** | `langgraph-checkpoint==3.0.1` pinado é afetado por **CVE-2026-27794 / GHSA-mhr3-j7m5-c7c9** (BaseCache pickle, corrigido em 4.0.0) e **CVE-2026-48775 / GHSA-fjqc-hq36-qh5p** (deserialização insegura ao carregar checkpoint, corrigido na linha 4). Exploração exige cache/armazém de checkpoint controlado pelo atacante (o grafo compila só com `checkpointer`, `graph.py:702`). | https://github.com/nakamasato/github-actions-practice/pull/2422 (lista os GHSA) |
| F12 | **BAIXA** | Tokens cacheados da OpenAI caem no balde errado: langchain-openai mapeia `cached_tokens` → `input_token_details.cache_read` (📊 `langchain_openai/chat_models/base.py:3566-3568`, v1.0.3); o `CostCallback` lê `cache_read` como "Anthropic" e `cached_tokens` como "OpenAI" (`cost_callback.py:107-113`) → OpenAI cacheado cobrado com o multiplicador de leitura Anthropic (0,10) em vez de 0,50. 📊 `token_usage_logs.cached_tokens` = 0 em todas as linhas de 30 d. Impacto hoje ≈ 0 (chat não usa OpenAI). | leitura do fonte instalado + SQL |
| F13 | **BAIXA** | Registro requested/resolved/actual inconsistente: streaming Anthropic grava o nome **configurado** (`claude-sonnet-5`), não-streaming OpenAI grava o **real da API** (📊 `gpt-4o-mini-2024-07-18` em 42 linhas de `memory`/`vision`). Não existe campo "pedido" vs "resolvido" (📊 `grep -rn "requested_model\|resolved_model" app` → 0). | SQL + grep |
| F14 | **BAIXA** | 22 construções diretas de `Chat*` em 10 arquivos **fora** da fábrica (sem breaker, várias sem timeout e sem `CostCallback`): `api/agents.py:573-580`, `api/agent_config.py:466-489`, `api/attendance_media.py:129,136`, `api/auxiliaries.py:482,629`, `services/benchmark_service.py:78-94`, `services/ingestion_service.py:380`, `services/langchain_service.py:277,284`, `services/memory_service.py:237`, `services/search_service.py:381`, `services/vision_service.py:93,97` + `audio_service.py:26` (`AsyncOpenAI`). 📊 `grep -rnE "(ChatOpenAI|ChatAnthropic|ChatGoogleGenerativeAI)\(" app | grep -v llm_factory | wc -l` → 22. | grep |
| F15 | **BAIXA** | Catálogos divergentes: UI oferece `claude-opus-4-1-20250805`, `claude-3-7-sonnet-20250219`, `o3`, `o3-pro`, `gemini-3.1-pro-preview`, `gemini-3-flash-preview`, `gemini-3-deep-think`, `grok-4`, `deepseek-chat`, `mistral-large-latest` (`components/admin/AgentConfigModal.tsx:105-298`) que o validador do backend **recusa** (`langchain_service.py:116-160` + `api/agent_config.py:124-131`); e **não** oferece `claude-sonnet-5`/`claude-opus-5`, que é o que a produção usa. `verbosity`, `top_p`, `top_k`, penalties são gravados pela UI e ignorados pela fábrica. | leitura |
| F16 | info | `anthropic-beta: prompt-caching-2024-07-31` (`llm_factory.py:245-249`) é obsoleto (caching é GA); inofensivo. O caching FUNCIONA no chat: 📊 30 d, `chat` Sonnet 5: 3.560.526 tokens lidos do cache / 521.162 escritos; `plataforma` (532 chamadas, 1,14 M tokens de entrada): **0** cache — os jobs de plataforma não põem `cache_control`. | SQL |

---

## PARTE 1 — A GARGANTA ATUAL

### 1.1 O fio de uma mensagem de chat (FATO, arquivo:linha)
```
langchain_service.process_message            services/langchain_service.py:311
 → _get_raw_agent (agents.*, papel exigido)   :188-252
 → get_api_key_for_provider (env GLOBAL)      core/utils.py:11-51        ← chave é da plataforma, não da corretora
 → get_or_create_graph (LRU 500, chave c:a:updated_at)  :48-96
   → create_agent_graph                       agents/graph.py:~155
     → LLMFactory.create_llm                  factories/llm_factory.py:75
        · modelo = agente > corretora > "gpt-4o"            :93-96
        · resolve_chat_model (SPEC-013)                      :100 → model_policy.py:29-35
        · piso de saída 8192 p/ core/attendance/insured      :107-119, :37-70
        · callbacks = [CostCallback, RelogioDoModeloCallback] :154-172
        · despacho por provedor (openai|anthropic|google|openrouter|else→gpt-4o-mini) :174-195
     → llm.bind_tools(tools)                  graph.py:649
     → StateGraph(agent ⇄ tools → log) + AsyncPostgresSaver   graph.py:674-703
 → invoke_agent → graph.ainvoke               graph.py:1811   (WhatsApp/rotina)
   ou stream_agent_eventos → astream_events(v1)  graph.py:2270 (web)
     → agent_node: llm_with_tools.ainvoke     agents/nodes.py:1255 (+ regenerações :1340, :1372)
```

### 1.2 Por provedor
| aspecto | OpenAI (`_create_openai` :198-226) | Anthropic (`_create_anthropic` :238-258) | Google (`_create_google` :261-276) | OpenRouter (:279-308) |
|---|---|---|---|---|
| API | **Chat Completions** (📊 sonda: `responses=False` para gpt-5.2, gpt-4o) | Messages | `google-ai-generativelanguage` (langchain-google-genai 3.1.0 — 📊 METADATA `Requires-Dist: google-ai-generativelanguage<1.0.0,>=0.9.0`; **não** usa `google-genai`) | ChatOpenAI + base_url (Chat Completions) |
| reasoning | `reasoning_effort` **só** se prefixo `o1`/`o3` (:200-201). gpt-5.x: 📊 `reasoning_effort=null` mesmo com `"high"` no agente | **nenhum** (sem `thinking`, sem `output_config.effort`) — F1 | **nenhum** (📊 `thinking_budget=None thinking_level=None`) | nenhum |
| temperature | removida p/ `o1`/`o3`/`gpt-5*` (:125-126) | removida p/ família 5 (:229-235) — F5 | sempre enviada | sempre enviada |
| tools | `bind_tools(tools)` sem `parallel_tool_calls`/`strict` (graph.py:649; nodes.py:1106; subagent_tool.py:347) | idem | idem | idem |
| structured output | **nenhum** `with_structured_output` no app (📊 grep → 0); JSON é extraído de texto (`juiz_llm.py:126`, `attendance_distiller.py:112`) | idem | idem | idem |
| streaming | `streaming=True` + `stream_options.include_usage` forçado (:208, :217-220) | `streaming=True` | `streaming=True` | idem OpenAI |
| usage | `usage_metadata` (input/output/reasoning/cache) — F12 | `cache_read`/`cache_creation` capturados (📊 funcionam) | input/output | idem OpenAI |
| prompt caching | automático do provedor | `cache_control: ephemeral` no bloco estático do system (`nodes.py:1155-1180`) só quando `llm_provider=="anthropic"` + header beta obsoleto | — | — |
| timeout / retries | `kwargs_de_relogio()` → `timeout=90`, `max_retries=2` (`relogio_do_modelo.py:99-166`) | idem | idem (baixa o default 6 do Google) | idem |
| max_tokens | `max_tokens`→`max_completion_tokens` (📊 payload) ; piso 8192 p/ quem conversa | `max_tokens` | `max_output_tokens` | `max_tokens` |

### 1.3 Health / breaker / failover (FATO)
- Breaker por PROVEDOR, Redis com degrau em memória, fail-open (`relogio_do_modelo.py:294-515`). Alimentado pelo callback da fábrica (:535-560). Quem **pergunta** é o `buffer_processor` (`tasks/buffer_processor.py:436-477`, só leitura de estado) e o painel (`core/central_de_agentes.py:1310`).
- **Não existe failover** de provedor/modelo: breaker aberto = mensagem retida, nunca troca de modelo. Não há fallback declarativo por papel.
- Retry: só o do SDK (2). O único "retry de turno" é o F4 (substring "connection").

### 1.4 Idempotência de efeito quando o turno é refeito
- Turno refeito em 3 lugares: (a) F4 `langchain_service.py:549-562`; (b) regenerações do fiscal (`nodes.py:1340,1372`) — estas **só** reinvocam o modelo, não as tools, e o texto regenerado é usado apenas quando não há `tool_calls`; (c) "emenda" de corte por `max_tokens` (`graph.py:1978-2060`) — idem, só texto.
- Ledger de custo é idempotente por `run_id` (`cost_callback.py:260-266`).

### 1.5 Modelo efetivo registrado
- `CostCallbackHandler(model_name=model)` recebe o modelo **após** `resolve_chat_model` (resolvido, não o pedido) (`llm_factory.py:155-160`); `on_llm_end` prefere `llm_output.model_name` (real da API) quando existe (`cost_callback.py:72-76`) — com streaming geralmente não existe. Resultado: F13.

### 1.6 A tupla "blocked" (`llm_factory.py:234`)
Ela **não bloqueia modelo**: bloqueia o **parâmetro `temperature`** para `claude-sonnet-5`, `claude-opus-5`, `claude-haiku-5`, `claude-mythos*`, `claude-fable*`, porque a API devolve 400 para sampling params nesses modelos. Como é prefixo, cobre também `claude-opus-5-5` e `claude-fable-5-1`. Falha: não cobre **Opus 4.7/4.8** (também 400) — F5.

### 1.7 A linha 194 (`gpt-4o-mini`)
Sim: `provider` fora de {openai, anthropic, google, openrouter} → `_create_openai("gpt-4o-mini", ..., True, "medium", ...)` com a chave que `get_api_key_for_provider` achou — que para provedor desconhecido é `OPENAI_API_KEY` (`utils.py:45`). Silencioso, só um `logger.warning`. F6.

### 1.8 "Trocar só a string `model=` basta?" — resposta por caso (📊 sondas com os kwargs EXATOS da fábrica)

**(a) OpenAI de raciocínio novo que exige Responses API para tools+reasoning (ex.: gpt-6, gpt-5.x-pro): NÃO.**
- Libs pinadas (langchain-openai 1.0.3): 📊 `gpt-6 responses=False ... temperature=0.7`, `gpt-5.5-pro responses=False` → vai por Chat Completions; modelos "Responses-only" (a própria lib lista `gpt-5-pro`, `gpt-5.2-pro`, `gpt-5.4-pro`, `gpt-5.5-pro`, `gpt-5.6-sol`, `*codex*` — `langchain_openai 1.6.4 base.py:695-707`) **falham**; gpt-6 recebe `temperature` (a fábrica só tira de `o1/o3/gpt-5`) e **nenhum** effort (a fábrica só manda para `o1/o3`).
- Libs atuais (1.6.4): 📊 `gpt-6 responses=True keys=[input, max_output_tokens, model, stream, stream_options, temperature, tools]` — a lib passa sozinha para Responses quando `gpt-6` + tools (`base.py:1942-1945`), mas ainda leva `temperature=0.7` e `stream_options={'include_usage': True}`. O schema do SDK para Responses **não tem** `include_usage` (📊 `openai-3.19.0 types/responses/response_create_params.py:423-435`, só `include_obfuscation`) — se o servidor recusa, é por medir.
- O que se perde mesmo quando "funciona": reasoning items descartados no histórico (F9), `usage.reasoning_tokens` (📊 0 linhas com reasoning em 30 d), a emenda de corte (`MOTIVOS_DE_CORTE`, `graph.py:1978`) não reconhece o corte da Responses (`status=incomplete`/`incomplete_details.reason`) — INFERÊNCIA, não medido.

**(b) Claude novo: FUNCIONA, mas degrada/ignora configuração.**
- Sonnet 5/Opus 5/5.5/Fable: `temperature` já é omitida → a chamada sai. Effort do agente ignorado (F1); thinking roda no default do modelo (Sonnet 5/Opus 5: adaptive ligado, effort `high`; Opus 5.5: default `medium`); blocos de thinking descartados no histórico (F9); Opus 5.5 e Fable 5.1 **recusam** `tool_choice` forçado (`any`/`tool`) — o app não força hoje (📊 `grep -rn tool_choice app | wc -l` → 0).
- Com langchain-anthropic 1.1.0 pinado **não dá** para passar effort pelo caminho natural: 📊 sonda: `reasoning_effort was transferred to model_kwargs` (viraria parâmetro top-level desconhecido). Na 1.7.3: 📊 `ChatAnthropic(reasoning_effort="low")` → `thinking={'type':'adaptive','display':'summarized'} output_config={'effort':'low'}`.
- Precisa de: modelo no allowlist (`langchain_service.py:128-148`) + preço em `llm_pricing` + preço no fallback (F2). Opus 4.7/4.8: quebra por `temperature` (F5).

**(c) Gemini novo: PROVAVELMENTE sim para texto; perde thinking e usa SDK legado.**
- `ChatGoogleGenerativeAI` 3.1.0 sobre `google-ai-generativelanguage`. Nenhum `thinking_level`/`thinking_budget` enviado (📊 sonda). O 4.x migrou para `google-genai` (REST só, sem gRPC; `with_structured_output` passa a `json_schema`) — https://github.com/langchain-ai/langchain-google/discussions/1422. Modelo precisa estar no allowlist (📊 `gemini-3.1-pro-preview` está na UI e no preço, **não** está em `SUPPORTED_PROVIDERS`). Não medido com chamada real.

**(d) Provedor OpenAI-compatível novo (xAI, DeepSeek, MiMo, Z.ai): NÃO.**
- Só existe o ramo `openrouter`. `llm_provider="xai"` → **gpt-4o-mini silencioso** (F6); validador recusa provedor fora da lista (`agent_config.py:115-121`). Pelo OpenRouter funciona, mas: `reasoning_content`/campos não-oficiais **não são extraídos** pela ChatOpenAI ("Non-standard response fields ... are not extracted. Use a provider-specific subclass", `langchain_openai 1.6.4 base.py:718-722`); `stream_options` e `temperature` sempre enviados; custo cai no preço do gpt-4o-mini se o id não estiver em `llm_pricing`; breaker contado como `openrouter`, sem distinguir destino.

---

## PARTE 2 — SDKs

📊 Pinadas: `backend/requirements.txt` (único manifesto do backend; `pyproject.toml` só tem ruff/uvicorn; sem lockfile). `backend/portal_worker/requirements.txt` e `docling-service/requirements.txt` **não têm SDK de LLM**. Frontend: 📊 nenhum de `openai`, `@anthropic-ai/sdk`, `ai`, `@ai-sdk/*`, `@langchain/*`, `@google/genai` em `package.json`; nenhuma chamada direta a `api.openai.com`/`api.anthropic.com`/`generativelanguage` em `app/ lib/ components/ hooks/`. Há ainda `groq>=0.4.0` (usado em `services/llama_guard_service.py`) e `langsmith>=0.1.0`.

| pacote | pinado | instalado (dev global) | última estável 23/09 (📊 `pip index versions`) | breaking relevantes | ganho concreto p/ nós | risco | upgrade NECESSÁRIO? |
|---|---|---|---|---|---|---|---|
| langchain | ==1.0.8 | 1.0.8 | 1.4.2 | nenhum relevante medido (uso mínimo: text splitters vêm de outro pacote) | pouco | baixo | não |
| langchain-core | ==1.1.0 | 1.1.0 | 1.6.4 | chat message history deprecado (1.6.4) | exigido pelas integrações novas (`langchain-openai 1.6.4` e `langchain-anthropic 1.7.3` pedem `>=1.6.4` — 📊 METADATA) | médio (callbacks, content_blocks) | **sim, junto** com as integrações |
| langchain-openai | ==1.0.3 | 1.0.3 | 1.6.4 (22/09) | roteamento automático p/ Responses em `*-pro`, `codex`, `gpt-6`+tools (📊 `base.py:695-707, 1931-1948`) — muda o formato de `content`/`response_metadata` sem pedir | modelos Responses-only e gpt-6 com tools; `reasoning_effort` padrão → `reasoning.effort` (+summary); `context_management`; "GPT-6 request constraints" | **alto** para o chat (formato de mensagem, streaming de tool call — issue aberta #34660) | **sim, só** se formos usar gpt-6/`*-pro`/codex; para gpt-4o/gpt-5.2 não |
| langchain-anthropic | ==1.1.0 | 1.1.0 | 1.7.3 (22/09) | exige `anthropic>=0.120` e `core>=1.6.4`; `with_structured_output` auto → json_schema (1.7.3); system messages no meio da conversa enviadas in-place (1.7.3) | **`reasoning_effort`/`thinking`/`output_config` nativos** (📊 sonda), validações de Opus 5/Fable, `context_management`, `inference_geo` | médio | **sim — para consertar F1** (effort no Claude) sem gambiarra em `model_kwargs` |
| langchain-google-genai | ==3.1.0 | 3.1.0 | 4.4.0 | 4.0: troca `google-ai-generativelanguage`→`google-genai`, **sem gRPC**, `with_structured_output` default json_schema | thinking do Gemini 3.x, SDK mantido | médio | não (Gemini não está em uso — 📊 0 chamadas em 30 d) |
| langgraph | ==1.0.3 | 1.0.3 | 1.2.12 | promessa "sem breaking até 2.0"; 1.2.12 exige `langgraph-checkpoint>=4.1` (📊 METADATA) | segurança via checkpoint 4 | médio (checkpointer em produção) | **sim, por F11** (junto com checkpoint) |
| langgraph-checkpoint | ==3.0.1 | 3.0.1 | 4.2.0 | 4.0: pickle fallback desligado por padrão | fecha CVE-2026-27794 e CVE-2026-48775 | médio: checkpoints antigos gravados com pickle podem não abrir — **medir** | **sim (segurança)** |
| langgraph-checkpoint-postgres | >=2.0.0 (solto) | 3.0.5 | 3.1.2 | — | — | pin solto (F10) | pinar |
| openai | >=1.10.0 (solto) | 2.54.0 | **3.19.0** | **3.0 (12/08/2026): HTTPX2 vira o cliente; `httpx` deixa de ser instalado** — https://github.com/openai/openai-python/releases/tag/v3.0.0 | nada que langchain-openai 1.0.3 use | **alto** se subir sozinho; hoje o teto `<3` da langchain-openai 1.0.3 segura | não por si; pinar `==2.x` já |
| anthropic | >=0.18.0 (solto) | 0.116.0 | **1.8.0** | 1.x: `httpx`→`httpx2`, `temperature/top_p/top_k` removidos das assinaturas, Text Completions removido, Python>=3.10 (skill claude-api `python/claude-api/sdk-upgrade.md`) | via langchain-anthropic 1.7.3 (que aceita `>=0.120,<2`) | médio | **não** isolado; 0.12x basta para langchain-anthropic 1.7.3 |
| google-genai | (não pinado) | 2.22.0 | 2.25.0 | — | só relevante com langchain-google-genai 4.x | — | não |
| google-ai-generativelanguage | ==0.9.0 | — | — | vira órfão se subir o 4.x | — | — | — |
| httpx | >=0.26 (solto) | 0.27.2 | 0.28.1 | com openai 3 / anthropic 1 o SDK passa a usar **httpx2**: `relogio_do_modelo.py:238-240` faz `isinstance(..., httpx.TimeoutException/TransportError)` — deixaria de casar (o fallback por nome de classe `"timeout"/"connection"` ainda pega); integrações que patcham `httpx` (Sentry, LangSmith?) param de ver o tráfego do SDK sem erro | — | médio | não; pinar |

📊 Sonda com libs ATUAIS (venv descartável `venv_novo`: langchain-openai 1.6.4, langchain-anthropic 1.7.3, core 1.6.4, openai 3.19.0, anthropic 1.8.0, httpx2 2.13.1) sobre os kwargs EXATOS da fábrica de hoje:
```
OPENAI gpt-5.2     responses=False  keys=[max_completion_tokens, messages, model, stream, stream_options, tools]
OPENAI gpt-5.5-pro responses=True   keys=[input, max_output_tokens, model, stream, stream_options, tools]
OPENAI gpt-6       responses=True   keys=[... stream_options, temperature, tools]  temperature=0.7
ANTHROPIC claude-sonnet-5       temperature=None thinking=None output_config=None
ANTHROPIC+effort claude-sonnet-5 thinking={'type':'adaptive','display':'summarized'} output_config={'effort':'low'}
ANTHROPIC claude-opus-4-8       keys=[extra_body, ...]   (1.7.3 move temperature p/ extra_body; ainda chega à API → 400 no Opus 4.8)
HIST assistant content types: ['tool_use']   (thinking descartado pelo sanitize)
```

**Pergunta específica — langchain-openai atual suporta Responses API com bind_tools + reasoning effort + streaming dentro do LangGraph?** SIM, com ressalvas:
- Ativa-se com `use_responses_api=True` (ou automático quando há `reasoning=`, `include=`, `truncation=`, `context_management=`, `use_previous_response_id=True`, `output_version="responses/v1"`, built-in tools, modelo Responses-only, ou `gpt-6`+tools) — `base.py:1931-1948`. Effort: `reasoning={"effort": "...", "summary": "auto"}` ou `reasoning_effort=` (traduzido para `reasoning.effort`) — https://docs.langchain.com/oss/python/integrations/chat/openai. `output_version` default `None`/env `LC_OUTPUT_VERSION` (`base.py:1214-1216`).
- Issues relevantes: **#34660 ABERTA** (desde 08/01/2026) — no streaming da Responses API nenhum chunk traz o `function_call` completo com argumentos (https://github.com/langchain-ai/langchain/issues/34660); **#33717** — `response_metadata` diferente entre streaming e não-streaming (https://github.com/langchain-ai/langchain/issues/33717); **#40205 fechada** (PR #40208) — async tool calls da Responses (https://github.com/langchain-ai/langchain/issues/40205); JS: `encrypted_content` de reasoning perdido no streaming (https://github.com/langchain-ai/langchainjs/issues/10844). Estado de #33717 não conferido.
- Para nós, o bloqueio real não é a lib: é o histórico reconstruído à mão (F9), que joga fora `id` `resp_…` e os reasoning items.

---

## PARTE 3 — PROPOSTA DE EVOLUÇÃO (sem motor paralelo — CLAUDE.md §5)

### 3.0 O que já existe e não pode ser duplicado
- Fábrica única: `factories/llm_factory.py` (o próprio relógio declara isso, `relogio_do_modelo.py:14-17`).
- Breaker/relógio: `core/relogio_do_modelo.py`.
- Ledger/custo: `core/callbacks/cost_callback.py` + `services/usage_service.py` + `usage_events`.
- Preço: tabela `llm_pricing` (📊 50 linhas, colunas `model_name, provider, input/output_price_per_million, is_active, cache_*_multiplier, sell_multiplier`) + `scripts/seed_pricing.py` + `scripts/sync_openrouter_models.py`.

📊 Hoje há **7 catálogos** de modelo: `SUPPORTED_PROVIDERS` (`langchain_service.py:116-160`), `PRICING_TABLE` (`usage_service.py:31-86`), `llm_pricing` (banco), `ECONOMY_MODELS` (`model_policy.py:13-18`) + espelho TS (`agent-health.ts:154`), `LLM_MODEL_OPTIONS` (`AgentConfigModal.tsx:~100-300`), defaults de blueprint TS (3 arquivos), **12 defaults por env** espalhados (📊 `grep -rn "getenv.*MODEL" app`: DISPATCH×3, BRAND, GARIMPO, SUGESTOES, DISTILLER×2, ATLAS, EXTRATOR_PLANOS, EVAL_JUDGE, COUNCIL_LEADER, AUXILIAR_LLM_MODEL). Mais os prefixos em `_PROVEDOR_POR_PREFIXO` (`cost_callback.py:211-221`), `utils.py:27-36`, `llm_factory.py:125,200,234`.

### 3.1 Catálogo único (registry) — onde mora a autoridade

**Alternativas**
| | desenho | nota | custo (arquivos tocados) |
|---|---|---|---|
| **A** | **Evoluir `llm_pricing` para `llm_models`** (expand-first: colunas `lifecycle` APPROVED/CANDIDATE/DEPRECATED/BLOCKED/HISTORICAL, `api_surface` chat/responses/messages/genai, `capabilities` jsonb — tools, reasoning_param, sampling_ok, max_output, context, `allowed_data_classes`, `replaced_by`). O banco é a autoridade; Python lê com cache (o `UsageService` já faz isso, `usage_service.py:98-156`); um **snapshot gerado** (`app/factories/modelos_snapshot.json`) é o fallback offline e o insumo do CI; o TS consome `GET /api/agent/providers` (a UI **já chama** `/api/admin/proxy/agent/providers`, `AgentConfigModal.tsx:578`). | **88** | 1 migration + `usage_service.py` + `langchain_service.py` (SUPPORTED_PROVIDERS vira leitura) + `api/agent_config.py` + `AgentConfigModal.tsx` + `agent-health.ts` + 3 blueprints TS + script de snapshot + 1 teste ≈ **11** |
| B | Catálogo em código (`app/factories/catalogo_de_modelos.py`), banco só com preço, TS gerado por script | 74 | ≈ 9 + CI gerando TS; preço continua em dois lugares (banco e código) — é exatamente o F2 de hoje |
| C | Arquivo YAML versionado como autoridade, seed para o banco | 70 | ≈ 10; mudança de preço vira deploy; dois caminhos de escrita |

**RECOMENDAÇÃO: A (88).** É consolidar a peça que já existe e já é lida em runtime (`llm_pricing`), não criar outra. Preço e ciclo de vida no mesmo registro fecham F2/F15 de uma vez. ⚠️ Migration → CRÍTICO pelo piso §3.2 (estrutura) e exige `MIGRATIONS-AUTHORITY.md` antes.

### 3.2 Roteador por papel/perfil
| | desenho | nota | custo |
|---|---|---|---|
| **A** | **Reescrever `model_policy.py`** (mesmo arquivo, mesmo ponto de chamada `llm_factory.py:100`) como `resolver(papel, perfil, agente, corretora) → ModeloResolvido{provider, model, effort, thinking, api_surface, motivo}` lendo o registry; os 12 `getenv(...MODEL)` passam a declarar **papel** (`dispatch`, `distiller`, `judge`…) em vez de modelo. Remove `CORE_CHAT_MODEL`/`ECONOMY_MODELS` (SPEC-013 superada). | **86** | `model_policy.py`, `llm_factory.py`, os 13 chamadores de plataforma (só trocam `agent_data` por `papel=`), `agent-health.ts`, testes ≈ **17** |
| B | Roteador dentro da `LLMFactory` | 72 | mesmo número de arquivos, fábrica fica com 2 responsabilidades |
| C | Manter política atual e só corrigir provider-mismatch | 55 | 2 arquivos; não resolve F1/F7/F8 |

**RECOMENDAÇÃO: A (86).** O papel `""` deixa de ser "core" por acidente (F8).

### 3.3 Adapters por provedor
Dentro da própria fábrica (não arquivo-motor novo): `_create_openai/_anthropic/_google/_openrouter` passam a receber o `ModeloResolvido` e traduzem **capacidades → kwargs** (effort → `reasoning`/`output_config.effort`/`thinking_level`; `sampling_ok=false` → sem temperature; `api_surface=responses` → `use_responses_api=True`, sem `stream_options.include_usage`). Um provedor OpenAI-compatível novo (xAI, DeepSeek, Z.ai, MiMo) entra como **linha do registry** com `base_url` + `api_key_env`, reaproveitando `_create_openrouter` generalizado — nunca como `else → gpt-4o-mini`. Pré-requisito: **langchain-anthropic ≥1.7.3 + core ≥1.6.4** para effort nativo no Claude; langchain-openai 1.6.x só quando entrar modelo Responses-only. Custo ≈ 3 arquivos (`llm_factory.py`, `utils.py`, `relogio_do_modelo.py:131` PROVEDORES vindo do registry) + os 22 bypasses (F14) migrados em fatia própria. Nota 84.

⚠️ Obrigatório no mesmo pacote: parar de descartar thinking/reasoning no histórico (`utils.py:96-116`, `nodes.py:1209-1211`) — preservar blocos de conteúdo por provedor, deixando o `sanitize` só para o caso "trocou de provedor no meio da conversa".

### 3.4 Failover observável e idempotente
| | desenho | nota |
|---|---|---|
| **A** | Failover **declarativo no registry** (`fallback_de` por papel), acionado **só antes** do primeiro byte/primeira tool do turno, a partir do mesmo breaker (`provedor_disponivel`). Cada chamada grava `modelo_pedido`, `modelo_resolvido`, `modelo_real` (do `response_metadata.model_name`) e `motivo_do_failover` no `details` do ledger que já existe (`cost_callback.py:137-141`) e em `usage_events`. Substituir o retry por substring (F4) por: repetir **só a chamada ao modelo** (o SDK já faz) e nunca o grafo inteiro depois que houve `tools_used`. | **85** |
| B | `with_fallbacks()` do LangChain no `llm_with_tools` | 68 — troca de provedor no meio de um loop de tools com histórico em formato do outro provedor; perde thinking; invisível no ledger |
| C | Sem failover; só retenção (hoje) + F4 corrigido | 70 — aceitável no curto prazo |

**RECOMENDAÇÃO: C já (conserto de F4, 2 arquivos), A depois do registry.** Custo A ≈ `langchain_service.py`, `graph.py`, `cost_callback.py`, `usage_service.py`, `relogio_do_modelo.py`, testes ≈ 7.

### 3.5 Legacy gate testável em CI
Um teste (`backend/tests/test_nenhum_modelo_fora_do_catalogo.py`) que **chama o motor** (§9.4), não regex:
1. Para cada default de papel (o resolver da 3.2 exporta a lista de papéis) e cada chamada `create_llm` → `resolver(papel)` e exige `lifecycle ∈ {APPROVED, CANDIDATE}`.
2. Varre TS (blueprints, `LLM_MODEL_OPTIONS`) via o snapshot gerado e exige id registrado e não BLOCKED/HISTORICAL.
3. `LLMFactory.create_llm(provider="xai"...)` **tem de levantar**, não cair em gpt-4o-mini.
4. Para cada modelo APPROVED: constrói o objeto pela fábrica e inspeciona o **payload** (`_get_request_payload`) — sem `temperature` quando `sampling_ok=false`, com effort quando o agente tem effort. (É o que as sondas desta investigação fizeram.)
5. **Linha de controle obrigatória (§9.2/§9.5):** reintroduz `claude-opus-4-8` com `temperature` e `llm_provider="xai"` num fixture e exige VERMELHO.
Nota 90 com o registry (A da 3.1); 65 sem ele (o teste teria de copiar a lista — §9.4). Custo: 1 teste + 1 script de snapshot.

### 3.6 Ordem sugerida (cada item é uma unidade entregável)
1. **Consertos pontuais, sem registry** (LEVE/PADRÃO): F3 (juiz), F4 (retry por substring), F5 (Opus 4.7/4.8 + teste que chama o motor), F6 (provedor desconhecido levanta), F2 (UPDATE de preço do Sonnet 5 — dado, não estrutura) , pinar `openai`, `anthropic`, `httpx`, `checkpoint-postgres` nas versões hoje resolvidas.
2. Upgrade `langchain-core 1.6.4 + langchain-anthropic 1.7.3 + langgraph 1.2.x + langgraph-checkpoint 4.x` (CRÍTICO: checkpointer em produção) → destrava effort nativo (F1) e fecha F11.
3. Registry (3.1-A) + resolver (3.2-A) + gate (3.5).
4. Adapters/Responses API (3.3) só quando um modelo Responses-only for aprovado.
5. Failover (3.4-A).

---

## O que ficou por medir
- Versões **dentro do contêiner** de produção (`pip show` no `smith-api`) — só medi o ambiente global do dev.
- Se o servidor da OpenAI recusa `stream_options.include_usage` na Responses API (schema do SDK não tem o campo; sem chamada real).
- Se o descarte de thinking (F9) já causou algum 400 ou degradação em Sonnet 5 — contar erros 400 do provedor nos logs.
- Distribuição real de effort/latência do Sonnet 5 sem effort explícito vs `low` (F1) — exige A/B com chamadas reais (custa dinheiro).
- Se F4 já refez tool com efeito em produção (cruzar `token_usage_logs`/`work_runs` com logs "♻️ Connection Pool closed").
- Se checkpoints existentes abrem com `langgraph-checkpoint` 4.x (pickle fallback desligado).
- Idempotência de handoff/envio/acionamento quando o turno é refeito.
- Estado atual (aberta/fechada) da issue #33717.
- Comportamento do Gemini novo com chamada real.

## Estranho / fora de escopo
- `scratchpad/grp.py` (de outra sessão) **sombreia o módulo `grp` da stdlib** para qualquer script Python rodado com cwd no scratchpad (📊 `IndexError` em `pathlib → import grp`). Rodei as sondas em `sondas/` por isso.
- `token_usage_logs` 30 d: 📊 **zero** chamadas `gpt-4o` — o LLM de despacho (`DISPATCH_LLM_MODEL` default `gpt-4o`, `dispatch_router.py:3397-3398`, `webhook.py:1126-1127`, `dispatch_watchdog.py:818-819`) não rodou ou tem env apontando para outro modelo.
- `service_type=plataforma` gastou 📊 US$ 7,41 em 532 chamadas Sonnet 5 com **0** cache — quase o mesmo que o chat inteiro (US$ 7,47).
- `api/auxiliaries.py:40` default `claude-haiku-4-5-20251001` mas `api/auxiliaries.py:482,629` constroem `ChatOpenAI` — conferir se um Auxiliar com modelo Claude cai no cliente errado.
- `langchain_service._analyze_image` resolve chave para `gemini` (`:467-468`) mas não tem ramo Gemini (`:276-291`) → "[Modelo de visão não configurado ou suportado]".

## Referências externas (§7.3)
- https://platform.claude.com/docs/en/about-claude/pricing — preços oficiais (Sonnet 5 $2/$10). Modelamos: preço no registry. Juiz inspeciona: tabela "Model pricing".
- https://docs.langchain.com/oss/python/integrations/chat/openai — quando ChatOpenAI usa Responses, `reasoning`/`reasoning_effort`, `use_previous_response_id`. Rejeitamos: `use_previous_response_id` (estado no servidor da OpenAI, fora do nosso checkpointer).
- https://github.com/openai/openai-python/releases/tag/v3.0.0 — HTTPX2. Modelamos: pin explícito. Rejeitamos: upgrade isolado.
- https://github.com/langchain-ai/langchain-google/discussions/1422 — langchain-google-genai 4.0.
- https://github.com/langchain-ai/langchain/issues/34660 · /33717 · /40205 — Responses + streaming de tools.
- GHSA-mhr3-j7m5-c7c9 · GHSA-fjqc-hq36-qh5p (via https://github.com/nakamasato/github-actions-practice/pull/2422) — langgraph-checkpoint 4.
- Fonte das libs (wheels em `scratchpad/wheels/x/`): `langchain_openai-1.6.4/.../base.py:695-707,1931-1948,4520-4545`; `langchain_anthropic-1.7.3/chat_models.py:1281-1345,1610-1670,1750-1810`.
