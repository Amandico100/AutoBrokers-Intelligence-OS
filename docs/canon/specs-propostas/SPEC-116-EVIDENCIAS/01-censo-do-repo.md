# CENSO MECÂNICO — toda escolha de modelo de IA no repositório

> MEDIDOR read-only · árvore `AutoBrokers-FIX` · HEAD `543cc82c0ca084b93615de85d3df8cff63530b0c` · 23/09/2026
> Nenhum arquivo do repo foi editado. Nenhum banco foi consultado (o que depende do banco está em (h)).
> 📊 = medido nesta sessão, com o comando ao lado. FATO / INFERÊNCIA marcados onde importa.

Convenção de comando (Git Bash, raiz do repo). `EX` = exclusões pedidas:
```
EX=(--hidden -g '!.git' -g '!node_modules' -g '!.next' -g '!dist' -g '!build' -g '!venv' -g '!.venv' -g '!__pycache__' -g '!package-lock.json' -g '!*.tsbuildinfo' -g '!docs/**')
LIT = regex de ID de modelo ENTRE ASPAS (gpt-*, o1/o3/o4*, claude-*, gemini-*, grok-*, deepseek*, mimo*, glm-*, mistral*, llama*, qwen*, kimi*, whisper*, tts-*, text-embedding*, embed-*, rerank*, nova-*, eleven_*, sonnet/opus/haiku/fable/mythos*)
rg -i -n -o "${EX[@]}" -e "$LIT" .   → 📊 425 ocorrências (salvas em scratchpad/literals.txt)
```

---

## (a) TABELA-MESTRA DE CALL SITES (quem chama provedor de verdade)

Legenda: **Fábrica** = passa por `LLMFactory.create_llm` (`backend/app/factories/llm_factory.py:75`). **POR FORA** = instancia o cliente direto. **Ledger** = grava em `token_usage_logs` (via `CostCallbackHandler` → `usage_service.track_cost_sync`, `cost_callback.py:159`) e `usage_events` (só com `company_id`, `cost_callback.py:246`).

Comando dos call sites: `rg -n "${EX[@]}" "create_llm\(" .` (📊 15 chamadores + a def) e
`rg -n "${EX[@]}" -g '!backend/tests/**' -e 'ChatOpenAI\(|ChatAnthropic\(|ChatGoogleGenerativeAI\(|OpenAIEmbeddings\(|AsyncOpenAI\(|cohere\.Client|chat\.completions|api\.openai\.com|audio\.transcriptions' .`

| # | arquivo:linha · função | superfície | resolução do modelo (env → DB → default LITERAL) | modelo EFETIVO em prod | Fábrica? | Ledger? | fallback |
|---|---|---|---|---|---|---|---|
| 1 | `agents/graph.py:194` `create_agent_graph` | **chat principal (core)** e **atendimento ao segurado** (via `langchain_service.process_message`, chamado por `webhook.py:1809`, `chat.py:261`, `routine_engine.py:328`) | `agents.llm_provider/llm_model` → `companies.llm_*` → provider `"openai"` (`llm_factory.py:93-95`), model `"gpt-4o"` (`:96`); core com model vazio ou em `ECONOMY_MODELS` → `CORE_CHAT_MODEL` default `"gpt-4o"` (`model_policy.py:21,34`) | **depende do banco** (h). Tenant novo nasce `gpt-4o-mini` (ver (c)) → core roda **gpt-4o**, atendimento roda **gpt-4o-mini** | sim | sim (`chat` / company) | provider desconhecido → **gpt-4o-mini** com só `logger.warning` (`llm_factory.py:191-195`) |
| 2 | `agents/tools/subagent_tool.py:335` | subagentes do core | `subagent_data.llm_*` → company → factory `gpt-4o`; o LOG grava default `"gpt-4-turbo"` (`:666`) | depende do banco | sim | sim | idem #1 |
| 3 | `api/webhook.py:1128` (fase humana do dispatch) | **dispatch/acionamento** (fala com a URA da seguradora) | `DISPATCH_LLM_PROVIDER` or `"openai"` · `DISPATCH_LLM_MODEL` or `"gpt-4o"` (`:1126-1127`) | **claude-opus-5** (env declarado) | sim | sim (`chat`, company) | env ausente → gpt-4o |
| 4 | `tasks/dispatch_watchdog.py:820` `_cerebro...` | dispatch (sentinela, roda no worker via `buffer_processor.py:1490`) | idem, `:818-819` | claude-opus-5 **se o env estiver no WORKER** (h) | sim | sim | idem |
| 5 | `services/dispatch_router.py:3399` (cérebro antes do segurado) | dispatch | idem, `:3397-3398` | claude-opus-5 | sim | sim | idem |
| 6 | `services/atlas/atlas_parser.py:91` `resolve_typed_choices` | atlas | `ATLAS_PARSER_PROVIDER` `"anthropic"` / `ATLAS_PARSER_MODEL` `"claude-sonnet-5"` (`:51-52`) | **claude-opus-5** | sim | **NÃO — `company_id="atlas"` (`:94`) cai em coluna `uuid` (`schema_completo.sql:1092`); o insert falha e o erro é engolido (`usage_service.py:282-284`)** | — |
| 7 | `services/attendance_distiller.py:151` `_call_llm` | distiller / lapidador (`prompt_optimizer.py:178`) / juiz do gate (`playbook_gate.py:79`) | `DISTILLER_PROVIDER` `"anthropic"`, `DISTILLER_STRONG_MODEL` `"claude-opus-5"`, `DISTILLER_LLM_MODEL` `"claude-sonnet-5"` (`:100-103`) | opus-5 / sonnet-5 (defaults) | sim | sim (`plataforma` ou GLOBAL_KNOWLEDGE_COMPANY_ID) | — |
| 8 | `services/knowledge/assistance_plans_extractor.py:634` | extrator de planos | `EXTRATOR_PLANOS_*` `anthropic`/`"claude-sonnet-5"` (`:76-77`) | claude-sonnet-5 | sim | sim | — |
| 9 | `services/agent_council.py:81` | agent council (desligado: `COUNCIL_ENABLED` default `"0"`, `:50`) | líder `COUNCIL_LEADER_*` `anthropic`/`"claude-opus-5"` (`:66-67`); membros `COUNCIL_MEMBERS` default `"openai:gpt-5.5,anthropic:claude-opus-5,moonshot:kimi-k3,xai:grok-4.5"` (`:54-55`) | desligado | sim | sim | **`moonshot`/`xai` não existem na fábrica → chave OPENAI (`core/utils.py:45`) → `gpt-4o-mini` (`llm_factory.py:194`)**: 2 dos 4 "conselheiros" seriam o mesmo mini |
| 10 | `services/broker_insights.py:204` | garimpo/insights (gate `GARIMPO_LLM` default `"0"`, `:168`) | `GARIMPO_LLM_*` `anthropic`/`"claude-sonnet-5"` (`:202-203`) | desligado se env ausente | sim | sim | — |
| 11 | `services/proactive_suggestions.py:127` | proactive suggestions (gate `SUGESTOES_LLM` default `"0"`, `:109`) | `SUGESTOES_LLM_*` `anthropic`/`"claude-opus-5"` (`:125-126`) | desligado se env ausente | sim | sim | — |
| 12 | `services/brand/capture.py:1044` | brand capture | `BRAND_CAPTURE_*` `anthropic`/`"claude-sonnet-5"` (`:1042-1043`) | claude-sonnet-5 | sim | sim (`brand_capture`) | — |
| 13 | `services/evals/juiz_llm.py:119` `julgar_com_llm` | eval/juiz | `EVAL_JUDGE_MODEL` `"claude-sonnet-5"` (`:72`) | **nunca roda** | chamada QUEBRADA: `create_llm(provider=..., model=..., temperature=0)` não casa com a assinatura `(company_config, agent_data, api_key, ...)` → `TypeError` engolido | — | 📊 zero chamadores: `rg -n "julgar_com_llm" backend` → só a `def` (`:99`) |
| 14 | `services/vision_service.py:93/97` `describe_image` | **visão** do chat principal (`chat.py:819`, com `agent_data`), do **atendimento** (`webhook.py:857`, `webhook.py:1501`, SEM `agent_data`) e do observer (`atlas/observer_media.py:487`, sem agent) | `agent.vision_model` (só se `gpt-`/`claude` + chave) → `_DEFAULT_OPENAI_VISION="gpt-4o-mini"` (`:22`) → `_DEFAULT_ANTHROPIC_VISION="claude-3-5-sonnet-20241022"` (`:23`, retirado) | **atendimento e observer: SEMPRE gpt-4o-mini** (OPENAI_API_KEY presente) | POR FORA | sim (`vision`) | vision_model `gemini-*` ou sem prefixo → cai calado em gpt-4o-mini; `ChatAnthropic(temperature=0.3)` quebra em Claude 5 |
| 15 | `services/langchain_service.py:277/284` `_analyze_image` (chamado em `:474`) | visão dentro do `process_message` (chat + atendimento) | `agent.vision_model` → `"gpt-4o-mini"` se OPENAI key (`:452`) → `"claude-haiku-4-5-20251001"` (`:457`) | gpt-4o-mini se o agente não tem `vision_model` | POR FORA | só com company_id (`:262`) | idem temperature 0.3 em ChatAnthropic |
| 16 | `api/attendance_media.py:129/136` `attendance_media_vision` | visão do atendimento (endpoint interno `/attendance/media/vision-analyze`) | só `agents.vision_model` (sem default; `:165`) | o do agente | POR FORA | **NÃO** (sem callback, sem track) | ChatAnthropic `temperature=0.2` → Claude 5 dá 400 |
| 17 | `api/auxiliaries.py:482` `_summarize` e `:629` `_draft_followup` | **auxiliares** (resumo de atendimentos; follow-up WhatsApp que escreve para o CLIENTE FINAL) | `AUXILIAR_LLM_MODEL` default `"claude-haiku-4-5-20251001"` (`:40`) | **QUEBRADO**: modelo Claude enviado a `ChatOpenAI` com chave OpenAI (`get_api_key_for_provider("openai", ...)`, `:479`, `:609`) | POR FORA | manual `track_cost_sync` (`:238`, `:746`) — só se a chamada volta | nenhum |
| 18 | `services/memory_service.py:237` `_get_memory_llm` | **memória** (resumo de sessão, fatos do usuário) | `memory_settings.memory_llm_model` (linha do banco) → `DEFAULT_MEMORY_SETTINGS["memory_llm_model"]="claude-haiku-4-5-20251001"` (`constants.py:77`) | **gpt-4o-mini** (INFERÊNCIA forte: linhas nascem só com as chaves — `20260803_02...sql:159`, `provision-tenant.ts:465` — e o DEFAULT da coluna é `'gpt-4o-mini'`, `schema_completo.sql:898`); sem linha → Claude via `ChatOpenAI` = quebra | POR FORA (`llm_factory` param nunca passado: 📊 `rg -n "MemoryService\(" backend/app` → 5 instâncias, nenhuma com `llm_factory`) | só com company_id (`:225`) | nenhum |
| 19 | `services/search_service.py:381` `_generate_hyde_doc` | **RAG** do chat e do atendimento (HyDE quando score < corte; `is_hyde_enabled` default True: `nodes.py:1650`, `graph.py:1484`) | literal `"gpt-4o-mini"` | gpt-4o-mini | POR FORA | só com company_id (`:372`) | falha → usa a própria query |
| 20 | `services/search_service.py:333/418` | embedding de consulta RAG | literal `"text-embedding-3-small"` | idem | POR FORA | sim, ESTIMADO por tiktoken (`:342-360`) | — |
| 21 | `services/ingestion_service.py:35/106` | ingestão (embedding) | `"text-embedding-3-small"` | idem | POR FORA | sim, estimado (`:167-188`) | — |
| 22 | `services/ingestion_service.py:380` `_chunk_agentic` | ingestão (chunking agêntico, estratégia `agentic`) | `"gpt-4o-mini"` | gpt-4o-mini | POR FORA | só com company_id (`:375`) | — |
| 23 | `services/attendance_distiller.py:613` | embedding de carta (RAG) | `"text-embedding-3-small"` | idem | POR FORA | **NÃO** | — |
| 24 | `services/knowledge/insurance_corpus.py:1118` | embedding do corpus normativo | idem | idem | POR FORA | **NÃO** | — |
| 25 | `services/global_knowledge_seed.py:58` | embedding do seed global | idem | idem | POR FORA | **NÃO** | — |
| 26 | `services/langchain_service.py:175/640/717` | embedding legado (`search_documents`, `process_document`) | idem | idem | POR FORA | **NÃO** | — |
| 27 | `services/rerank_service.py:26` | rerank RAG | literal `"rerank-multilingual-v3.0"` (`:20-22`) | Cohere v3.0 (COHERE_API_KEY presente) | POR FORA | **NÃO** (📊 `rg -n "track\|usage\|cost" backend/app/services/rerank_service.py` → 0) | sem chave → sem rerank |
| 28 | `services/audio_service.py:71/178` | **áudio/STT** (atendimento `webhook.py:870`, observer, `attendance_media.py:74`) | literal `"whisper-1"` | whisper-1 | POR FORA | sim (`audio`); caminho URL só com company_id (`:186`) | — |
| 29 | `services/llama_guard_service.py:52/71` | guardrail anti-jailbreak (`guardrails.py:247`) | literal `"meta-llama/llama-prompt-guard-2-86m"` (Groq) | **desligado em silêncio**: `GROQ_API_KEY` vazia → `groq_client=None` → `return False, ""` (`:67-68`) | POR FORA | NÃO | fail-OPEN sem cliente |
| 30 | `portal_worker/adaptive.py:393` `decide_next_action` | **portal worker** (acionamento em portal: decide o próximo clique) | `PORTAL_VISION_MODEL` default `"gpt-4o"` (`:405`); HTTP direto a `api.openai.com` (`:418`) | **gpt-4o** (env ausente) | POR FORA | **NÃO** | **qualquer status ≥ 400 (inclui 429/5xx) refaz com `_MODELO_DE_RESERVA="gpt-4o-mini"` (`:47`, `:428-429`) sem log** |
| 31 | `docling-service/app/tasks.py:139-143` | docling (descrição de imagem no PDF, só com `extract_images=True`, opt-in do admin) | `settings.VISION_MODEL` default `"gpt-4o-mini"` (`docling-service/app/config.py:23`) | gpt-4o-mini salvo env (desconhecido) | POR FORA (serviço separado) | **NÃO** | — |
| 32 | `services/benchmark_service.py:78/86/94/50` | benchmark de RAG (admin, `documents.py:629`) | literais `"gpt-4o"`, `"gpt-4o-mini"`, `"claude-sonnet-4-6"`, `"text-embedding-3-small"` | idem | POR FORA | sim (`benchmark`); embeddings não | — |
| 33 | `api/agent_config.py:466-489` `test_llm_connection` · `api/agents.py:573-580` `test_llm_integration` | admin "testar conexão" | modelo vindo da tela | — | POR FORA | NÃO | agent_config manda `temperature=0.7` a ChatAnthropic → **teste de Claude 5 falha** |
| 34 | `scripts/acervo/medir_o_rag.py:183` · `scripts/destilacao_max/reindexar_acervo.py:126` | scripts operacionais | `--modelo` default `"gpt-4o-mini"` (`:154`) · embedding | — | POR FORA | NÃO | — |

**Voz / TTS / Gemini Live / Deepgram / ElevenLabs:** 📊 zero call sites no repo.
`rg -n --hidden -g '!node_modules' -g '!.git' "AUTOBROKERS_GEMINI|CLAUDE_API_KEY|GEMINI_API_KEY|DEEPGRAM_API_KEY|ELEVENLABS_API_KEY" -g '!docs/**' .` → **0 linhas**. Gemini só entra pela fábrica (provider `google`, chave `GOOGLE_API_KEY`, `core/utils.py:40`) se um agente do banco estiver configurado assim.
**Frontend:** 📊 nenhum SDK de LLM: `grep -E '"(openai|@anthropic-ai/sdk|@google/genai|@google/generative-ai|ai|@ai-sdk/[a-z]+|cohere-ai)"' package.json` → vazio; `rg "from ['\"](openai|@anthropic-ai|@google)" app lib components` → vazio. Todo modelo roda no backend.

---

## (b) ENVS DE MODELO/PROVEDOR → MODELO EFETIVO

Comando: `rg -n "${EX[@]}" -g '!backend/tests/**' -e '(getenv|environ\.get|environ\[|process\.env)[^A-Z]{0,4}[A-Z_]*(MODEL|MODELO|LLM|PROVIDER|VISION|EMBED|WHISPER|STT|TTS|RERANK|JUDGE|JUIZ|EFFORT)[A-Z_]*' .` (📊 31 linhas) + `config.py` pydantic.

| env | lido em | default no código | prod (declarado) | MODELO EFETIVO |
|---|---|---|---|---|
| `CORE_CHAT_MODEL` | `factories/model_policy.py:34` | `"gpt-4o"` | ausente | **gpt-4o** para todo core cujo `llm_model` seja nulo ou ∈ {gpt-4o-mini, gpt-4o-mini-2024-07-18, gpt-3.5-turbo, gpt-4.1-mini} |
| `DISPATCH_LLM_PROVIDER` / `_MODEL` | `webhook.py:1126-1127`, `dispatch_watchdog.py:818-819`, `dispatch_router.py:3397-3398` | `openai` / `gpt-4o` (3 cópias) | anthropic / claude-opus-5 | claude-opus-5 (⚠️ o watchdog roda no worker — confirmar env lá) |
| `ATLAS_PARSER_PROVIDER` / `_MODEL` | `atlas/atlas_parser.py:51-52` | anthropic / claude-sonnet-5 | model = claude-opus-5 | claude-opus-5 (invisível no ledger, #6) |
| `ATLAS_PARSER_ENABLED` | `atlas_parser.py:45` | `"1"` (ligado) | ausente | ligado |
| `AUXILIAR_LLM_MODEL` | `api/auxiliaries.py:40` | claude-haiku-4-5-20251001 | ausente | **quebrado** (Claude em ChatOpenAI) |
| `EVAL_JUDGE_MODEL` | `evals/juiz_llm.py:72` | claude-sonnet-5 | ausente | código morto e quebrado |
| `GARIMPO_LLM` / `_PROVIDER` / `_MODEL` | `broker_insights.py:168,202-203` | `0` / anthropic / claude-sonnet-5 | ausente | desligado |
| `SUGESTOES_LLM` / `_PROVIDER` / `_MODEL` | `proactive_suggestions.py:109,125-126` | `0` / anthropic / claude-opus-5 | ausente | desligado |
| `BRAND_CAPTURE_PROVIDER` / `_MODEL` | `brand/capture.py:1042-1043` | anthropic / claude-sonnet-5 | ausente | claude-sonnet-5 |
| `DISTILLER_PROVIDER` / `_LLM_MODEL` / `_STRONG_MODEL` | `attendance_distiller.py:100-103` | anthropic / claude-sonnet-5 / claude-opus-5 | ausente | sonnet-5 / opus-5 |
| `EXTRATOR_PLANOS_PROVIDER` / `_MODEL` | `knowledge/assistance_plans_extractor.py:76-77` | anthropic / claude-sonnet-5 | ausente | claude-sonnet-5 |
| `COUNCIL_ENABLED` / `_MEMBERS` / `_LEADER_PROVIDER` / `_LEADER_MODEL` | `agent_council.py:50,54,66-67` | `0` / lista com gpt-5.5, kimi-k3, grok-4.5 / anthropic / claude-opus-5 | ausente | desligado (e 2 membros virariam gpt-4o-mini) |
| `PORTAL_VISION_MODEL` | `portal_worker/adaptive.py:405` | gpt-4o (reserva gpt-4o-mini `:47`) | ausente | **gpt-4o → gpt-4o-mini em qualquer erro** |
| `PORTAL_VISION_PROVIDER` | `portal_worker/perception.py:397` | openai | ausente | **decorativo**: só é reportado em `portal_worker/main.py:130`; `decide_next_action` chama OpenAI fixo |
| `PORTAL_VISION_ENABLED` | `perception.py:386` | desligado | ausente | desligado (modo percepção) |
| `VISION_MODEL` / `VISION_API_URL` (docling) | `docling-service/app/config.py:23-24` | gpt-4o-mini / api.openai.com | env do docling desconhecido | gpt-4o-mini provável |
| `EMBEDDING_DIMENSION` | `qdrant_service.py:127`, `config.py:50` | 1536 | 1536 | coerente com text-embedding-3-small (literal em 9 lugares; NÃO é env) |
| `PISO_DE_SAIDA_DA_CONVERSA` | `llm_factory.py:37` | 8192 | ausente | 8192 (vale também p/ papel `""`, isto é, todo chamador sem agente) |
| `AUTOBROKERS_GEMINI_LIVE_MODEL` / `_TEXT_MODEL` | **nenhum leitor** | — | gemini-3.1-flash-live-preview / gemini-3-flash-preview | **não afetam nada deste repo** |
| `POLICY_INTELLIGENCE_V2`, `TOOL_GATEWAY_MODE`, `PORTAL_EXECUTION_GATEWAY_MODE` | — | — | declarados | não escolhem modelo |
| `OPENROUTER_BASE_URL` | `config.py:154`, `scripts/sync_openrouter_models.py:33` | openrouter.ai/api/v1 | — | OPENROUTER_API_KEY vazia → provider `openrouter` falha (`core/utils.py:48-49` levanta) |
| `GROQ_API_KEY` (não é *_MODEL, mas decide o guardrail) | `llama_guard_service.py:35` | — | vazia | guardrail anti-jailbreak DESLIGADO |
| não-modelo (ruído do regex) | `WHATSAPP_CHANNEL_PROVIDER`, `PLATFORM_ALERT_WA_PROVIDER` | — | — | — |

Chaves com ZERO leitor no repo: `CLAUDE_API_KEY`, `GEMINI_API_KEY`, `DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY` (comando em (a)).

---

## (c) DEFAULTS DE NASCIMENTO

| onde nasce | arquivo:linha | provider / modelo gravado | efeito em runtime |
|---|---|---|---|
| **Corretora provisionada — agente CORE** | `lib/admin/agent-blueprints-canonical.ts:65-66` → `lib/admin/provision-tenant.ts:221-222` (`materializarAgente`) | `openai` / `gpt-4o-mini` | promovido a **gpt-4o** (`model_policy.py:33-34`) |
| **Corretora provisionada — agente de ATENDIMENTO (fala com o segurado)** | `agent-blueprints-canonical.ts:102-103` | `openai` / `gpt-4o-mini` | **fica gpt-4o-mini** (a promoção é só do core) |
| blueprint "modelo NUNCA é override do tenant" | `agent-blueprints-canonical.ts:248-249` | usa o default do blueprint | trava o gpt-4o-mini |
| visão do atendente | `provision-tenant.ts` `allow_vision: bp.role === 'attendance'` sem `vision_model` | — | default gpt-4o-mini (#14/#15) |
| memória de cada agente | `provision-tenant.ts:465` e migration `20260803_02_spec063_corretora_nasce_completa.sql:159` inserem só `(agent_id, company_id)` | DEFAULT da coluna = `'gpt-4o-mini'` (`schema_completo.sql:898`) | **gpt-4o-mini** |
| sandbox de tenant | `app/api/admin/sandbox/bootstrap-tenant/route.ts:103-104,128` | `openai` / `gpt-4o-mini`, `reasoning_effort: 'low'` | idem |
| auxiliar instalado (runtime `smith_agent_blueprint`) | `app/api/admin/auxiliaries/templates/[templateId]/install/route.ts:58-59` → `lib/admin/agent-blueprints.ts:60-61` | `openai` / `gpt-4o-mini` | gpt-4o-mini |
| tela de auxiliares (admin) | `app/admin/auxiliares/page.tsx:128-129, 343-344` | `openai` / `gpt-4o-mini` | idem |
| release de blueprint (fallback) | `lib/admin/blueprint-release.ts:182-183` | `openai` / `gpt-4o-mini` | idem |
| agente sem modelo (backend) | `llm_factory.py:93-96` | `openai` / `gpt-4o` | gpt-4o; ⚠️ provider `anthropic` com modelo vazio vira `ChatAnthropic(model="gpt-4o")` = erro |
| `agents.reasoning_effort` | `schema_completo.sql:470`, `models/agent.py:46` | `'medium'` | só vale para `o1*`/`o3*` (`llm_factory.py:200`); gpt-5 e Claude 5 ignoram |
| log de conversa (rótulo) | `agents/nodes.py:2059`, `subagent_tool.py:666` | `"gpt-4-turbo"` | rótulo ≠ modelo real (fábrica usa gpt-4o) |

📊 Sem DEFAULT de modelo nas colunas `agents.llm_model` / `companies.llm_model` (`schema_completo.sql:450-451, 577-578`, sem `DEFAULT`).

---

## (d) CATÁLOGOS / LISTAS DUPLICADOS (📊 11 fontes)

| # | fonte | papel | Claude 5? | legado presente |
|---|---|---|---|---|
| 1 | `backend/app/services/langchain_service.py:116-160` `SUPPORTED_PROVIDERS` | **allowlist que VALIDA** config (`agent_config.py:129-130`) | opus-5, sonnet-5 (sem haiku-5) | claude-3-5-sonnet-20241022, claude-3-5-haiku, claude-3-opus, gemini-1.5/2.0; **sem** gemini-3-flash-preview/3.1-pro |
| 2 | `components/admin/AgentConfigModal.tsx:97-300` `LLM_MODEL_OPTIONS` ("Dezembro 2025") | dropdown do admin | **NÃO** (topo = claude-opus-4-6) | gpt-4o, gpt-4o-mini, o1, claude-3-7 |
| 3 | `AgentConfigModal.tsx:1981-1985` dropdown de VISÃO | escolhe `vision_model` | NÃO | **só `gpt-4o` e `claude-3-5-sonnet-20240620` (retirado)** |
| 4 | `backend/app/services/usage_service.py:31-93` `PRICING_TABLE` | preço de fallback | **NÃO** | 3-5, 1.5 |
| 5 | `usage_service.py:163-165` | preço de modelo desconhecido = **gpt-4o-mini** | — | — |
| 6 | `backend/scripts/seed_pricing.py:~30-93` | seed de `llm_pricing` | **NÃO** | idem |
| 7 | `backend/app/api/pricing.py:233-281` `CURATED_MODELS` | whitelist OpenRouter (sync de preço) | n/a | — |
| 8 | `backend/scripts/sync_openrouter_models.py:40-88` `CURATED_MODELS` | cópia do #7 | n/a | — |
| 9 | `backend/app/factories/model_policy.py:13-21` `ECONOMY_MODELS` + `DEFAULT_CORE_MODEL` | política de promoção | — | — |
| 10 | `lib/admin/agent-health.ts:154-158` `ECONOMY` / `effectiveCoreModel` | cópia TS do #9 (**ignora `CORE_CHAT_MODEL`**) | — | — |
| 11 | `backend/app/services/atlas/atlas_parser.py:149-152` `prices` | estimativa de custo do Atlas | sonnet-5 só (prod usa **opus-5** → cai em 3/15) | gpt-4o |
| + | `llm_factory.py:234` (família sem temperature) · `core/callbacks/cost_callback.py:212-221` (prefixo→provedor) · `core/utils.py:27-35` (prefixo→chave) | três mapas de "que família é esta" | — | — |

📊 Claude 5 sem preço em NENHUM catálogo do repo: `rg -n "claude-opus-5|claude-sonnet-5|claude-haiku-5" backend/app/services/usage_service.py backend/scripts/seed_pricing.py backend/app/api/pricing.py backend/supabase supabase` → **0 linhas**.

---

## (e) CHAMADAS INVISÍVEIS AO LEDGER (`token_usage_logs`)

| # | call site | por quê |
|---|---|---|
| 1 | `atlas_parser.py:91-94` (Opus 5 em prod) | `company_id="atlas"` → insert em coluna `uuid` falha; `usage_service.py:282-284` só loga erro |
| 2 | `portal_worker/adaptive.py:416-429` (gpt-4o + reserva mini) | `httpx` direto, sem track; a 2ª chamada da reserva também |
| 3 | `api/attendance_media.py:122-136` | cliente sem callback |
| 4 | `docling-service/app/tasks.py:139-161` | serviço separado, sem ledger |
| 5 | `rerank_service.py` (Cohere) | sem track |
| 6 | embeddings: `attendance_distiller.py:613`, `insurance_corpus.py:1118`, `global_knowledge_seed.py:58`, `langchain_service.py:640,717`, `benchmark_service.py:316,491`, `scripts/destilacao_max/reindexar_acervo.py:126` | sem track (search/ingestion rastreiam por ESTIMATIVA tiktoken) |
| 7 | `agent_config.py:466-489`, `agents.py:573-580` (teste de conexão) | sem callback (pequeno) |
| 8 | `llama_guard_service.py` (Groq) | sem track (e desligado) |
| 9 | condicionais: HyDE (`search_service.py:372`), chunking agêntico (`ingestion_service.py:375`), memória (`memory_service.py:225`), `_analyze_image` (`langchain_service.py:262`), whisper por URL (`audio_service.py:186`) | só gravam **se houver `company_id`** |
| 10 | auxiliares (`auxiliaries.py:238, 746`) | track manual — mas a chamada hoje falha antes (#17) |
| 11 | **visível mas mal precificada**: todo modelo sem linha em `llm_pricing` é cobrado como **gpt-4o-mini** (`usage_service.py:163-165`) — Claude 5 não está em catálogo nenhum do repo | 💭 se `llm_pricing` do banco também não tiver `claude-opus-5`, o custo do dispatch/atlas/distiller sai ~33× menor (US$0,15/0,60 vs o preço real) — **depende do banco (h)** |

---

## (f) CONTAGEM POR CLASSE

Base: 📊 425 literais entre aspas fora de `docs/` (comando no topo). Classificação linha a linha (tabela de trabalho em `scratchpad/grp.py` + saída acima):

| classe | n | onde (resumo) |
|---|---|---|
| **A** produção ativa (literal usado de fato numa chamada/lógica de roteamento) | 32 | HyDE e agentic chunk gpt-4o-mini, embeddings, whisper-1, rerank v3.0, prompt-guard, benchmark, prefixos da fábrica/utils |
| **B** default/fallback ativo | 30 | fábrica (gpt-4o, gpt-4o-mini desconhecido), model_policy (5), dispatch ×3, portal (gpt-4o + reserva), vision_service, langchain vision default, envs `or "claude-*"` ×11, memória, auxiliar, rótulos gpt-4-turbo ×2, usage_service fallback de preço |
| **C** config de tenant | 1 | sandbox bootstrap |
| **D** config de blueprint | 6 | canonical ×2, agent-blueprints, blueprint-release, auxiliares page ×2 |
| **E** catálogo/UI | 83 | AgentConfigModal 46, SUPPORTED_PROVIDERS 29, agent-health 5, outros 3 |
| **F** pricing/billing | 165 | usage_service 49, seed_pricing 44, pricing.py 27, sync_openrouter 27, cost_callback 7, atlas prices 5, tiktoken 6 |
| **G** teste/fixture/tooling | 84 | 78 em `backend/tests` e `scripts/*.test.mjs` + 6 em scripts de medição |
| **H** compat legada | 3 | `schema_completo.sql:898`, `vision_service.py:23` (3-5 retirado), `memory_service.py:49` |
| **I** doc histórica em comentário | 15 | comentários com "era gpt-4o-mini", etc. |
| **J** ledger/histórico imutável | 0 | nenhuma migration aplicada carrega ID de modelo além do dump |
| ruído (não é modelo) | 6 | "rerank"/"reranker" como rótulo, "RerankService" |

**docs/** (não classificado): 📊 família ampla `rg -i -c "${EX sem docs}" -e "$FAM" docs` → **1.604 ocorrências em 384 arquivos**; literais entre aspas → **80 em 27 arquivos**; `gpt-4o-mini` → 22.

---

## (g) FINDINGS — por gravidade (legado em caminho P0 primeiro)

**F1 · 🔴 P0 — o atendente de toda corretora nova fala com o segurado em `gpt-4o-mini`.**
`lib/admin/agent-blueprints-canonical.ts:102-103` (`default_llm_provider: 'openai'`, `default_llm_model: 'gpt-4o-mini'`) é o que `provision-tenant.ts:221-222` grava; `:248-249` proíbe o tenant de trocar ("anti custo premium"). A promoção de `model_policy.py:32` vale **só para core** (`is_core_chat_role`, `:24-26`), então `attendance` mantém o mini (`test_model_policy.py:41` afirma isso como correto).
Comando: `rg -n "default_llm_model" lib/admin/agent-blueprints-canonical.ts` → `66: 'gpt-4o-mini'`, `103: 'gpt-4o-mini'`. ⚠️ ELO não medido: o modelo dos agentes JÁ existentes em prod está no banco (h).

**F2 · 🔴 P0 — toda foto do segurado é lida por `gpt-4o-mini`, qualquer que seja o agente.**
`webhook.py:857` e `webhook.py:1501` chamam `describe_image(...)` **sem `agent_data`** → `resolve_vision_model(None)` → `vision_service.py:43-44` devolve `_DEFAULT_OPENAI_VISION = "gpt-4o-mini"` (`:22`), pois OPENAI_API_KEY existe. Idem observer (`atlas/observer_media.py:487`). INFERÊNCIA: no mesmo fluxo `process_message` recebe `image_url=final_image_url` (`webhook.py:1816`) e descreve a imagem de novo em `langchain_service.py:448-474` (default também gpt-4o-mini) — possível chamada dupla por foto; precisa rodar o caminho.
Comando: `rg -n "describe_image\(" -A4 backend/app/api/webhook.py` (nenhum `agent_data=`).

**F3 · 🔴 P1 — memória roda em `gpt-4o-mini`; o "saiu do mini" só existe na constante.**
`memory_service.py:221`: `settings.get("memory_llm_model", ...)`, onde `settings` é a LINHA de `memory_settings` (`:111-120`). A migration `20260803_02...sql:156-162` e `provision-tenant.ts:465` inserem só `(company_id, agent_id)` "o resto vem do DEFAULT da coluna" → `memory_llm_model text DEFAULT 'gpt-4o-mini'` (`schema_completo.sql:898`). E quando NÃO há linha, o default `claude-haiku-4-5-20251001` (`constants.py:77`) vai para `ChatOpenAI(... api_key=OPENAI_API_KEY)` (`memory_service.py:237-242`) → quebra. O guarda `test_o_cache_a_porta_e_o_modelo_da_memoria.py:154` só lê o texto de `constants.py` (CLAUDE.md §9.4: guarda a constante, não o motor).
Comando: `rg -n "memory_llm_model" backend app lib -g '!**/tests/**'` → só `schema_completo.sql:898`, `constants.py:77`, `memory_service.py:49,221`.

**F4 · 🔴 P1 — auxiliares de resumo e de follow-up ao cliente final estão QUEBRADOS desde 07/08.**
`auxiliaries.py:40` `DEFAULT_MODEL = os.getenv("AUXILIAR_LLM_MODEL", "claude-haiku-4-5-20251001")`, mas `_summarize` (`:477-489`) e `_draft_followup` (`:607-629`) usam `ChatOpenAI` + `get_api_key_for_provider("openai", ...)`. Um modelo Claude na API da OpenAI não existe. Commit que trocou só a string: `git log -S'claude-haiku-4-5-20251001' -- backend/app/api/auxiliaries.py` → `3e2c8a5 2026-08-07`. O guarda (`test_o_cache...py:161-166`) confere `"gpt-4o-mini" not in` e `"AUXILIAR_LLM_MODEL" in` — texto, nunca a chamada.
⚠️ ELO: não medi a resposta real (INFERÊNCIA; confirmar com uma chamada ou nos logs `[AUXILIAR]`).

**F5 · 🔴 P1 — portal worker (acionamento): `gpt-4o`, com rebaixamento silencioso a `gpt-4o-mini` e sem ledger.**
`portal_worker/adaptive.py:405` `PORTAL_VISION_MODEL` default `"gpt-4o"` (ausente em prod); `:428-429` qualquer `status_code >= 400` (inclui 429 e 5xx) refaz com `_MODELO_DE_RESERVA = "gpt-4o-mini"` (`:47`) — sem log, sem métrica, HTTP direto (`:418`), fora do ledger. O próprio comentário (`:397-403`) documenta que o mini errava esta tarefa. `PORTAL_VISION_PROVIDER` (`perception.py:397`) é decorativo.
Comando: `rg -n "_MODELO_DE_RESERVA|PORTAL_VISION" backend/portal_worker`.

**F6 · 🟠 P1 — RAG do chat e do atendimento: HyDE hardcoded `gpt-4o-mini`.**
`search_service.py:381-386`; disparado quando o score fica abaixo do corte (`:731`, `:791-793`) e `is_hyde_enabled` default True (`nodes.py:1650`, `graph.py:1484`). O documento hipotético gerado pelo mini decide quais trechos chegam ao modelo principal. Mesma família: chunking agêntico `ingestion_service.py:380-385` (`gpt-4o-mini`).

**F7 · 🟠 P1 — o Atlas (Opus 5 em prod) é invisível no ledger.**
`atlas_parser.py:94` `company_id="atlas"` → `CostCallbackHandler(service_type="chat", company_id="atlas")` → insert em `token_usage_logs.company_id uuid` (`schema_completo.sql:1092`, FK `:2925`) falha → `usage_service.py:282-284` engole. `usage_events` também recebe `"atlas"` (`cost_callback.py:258`). ELO não medido no banco (h).

**F8 · 🟠 P1 — custo de Claude 5 pode estar sendo registrado a preço de gpt-4o-mini.**
`usage_service.py:163-165`: modelo desconhecido → preço do `gpt-4o-mini`. Nenhum catálogo do repo tem `claude-opus-5`/`sonnet-5`/`haiku-5` (comando em (d)). Se `llm_pricing` em prod também não tiver, dispatch (opus-5), distiller, atlas e extrator saem subcontados. **Depende do banco (h)**.

**F9 · 🟠 P2 — fallback silencioso de provedor para `gpt-4o-mini` na fábrica.**
`llm_factory.py:191-195`: provider fora de {openai, anthropic, google, openrouter} → `gpt-4o-mini` com a chave que veio, só `logger.warning`. Atinge o conselho (`agent_council.py:54-55`: `moonshot:kimi-k3`, `xai:grok-4.5` → chave OpenAI por `core/utils.py:45` → mini). Idem `llm_factory.py:96`: provider `anthropic` sem modelo vira `ChatAnthropic(model="gpt-4o")`.

**F10 · 🟠 P2 — visão com Claude 5 quebra em 3 caminhos por fora da fábrica.**
A fábrica sabe que Claude 5 rejeita `temperature` (`llm_factory.py:229-235`), mas `vision_service.py:93` (`0.3`), `langchain_service.py:284-289` (`0.3`), `attendance_media.py:136` (`0.2`) e `agent_config.py:470-471` (`0.7`) mandam temperature a `ChatAnthropic`. Configurar `vision_model=claude-opus-5` num agente o deixa cego (falha engolida → `None`). O guarda `test_llm_temperature_guard.py` lê só `llm_factory.py` (`:8`).

**F11 · 🟠 P2 — UI oferece modelo retirado e esconde Claude 5.**
`AgentConfigModal.tsx:1981-1985`: visão só `gpt-4o` ou `claude-3-5-sonnet-20240620` (retirado → 404; o próprio repo diz em `langchain_service.py:453-456`). `LLM_MODEL_OPTIONS` (`:97`, "Dezembro 2025") não tem nenhum Claude 5, enquanto o backend (`langchain_service.py:133-134`) aceita. `vision_service.py:23` ainda aponta `claude-3-5-sonnet-20241022` como fallback (só sem OPENAI key; o teste `test_o_cache...py:168-170` confere a mesma string só em `langchain_service.py`).

**F12 · 🟡 P2 — guardrail anti-jailbreak desligado sem alarme.**
`llama_guard_service.py:35-41,67-68`: `GROQ_API_KEY` vazia em prod → `validate_jailbreak` devolve benigno sempre. Só um `logger.warning` no boot.

**F13 · 🟡 P2 — `CORE_CHAT_MODEL` ausente → core promovido a `gpt-4o`**, e a cópia TS (`lib/admin/agent-health.ts:154-158`) mostra `gpt-4o` fixo, ignorando o env. `model_policy.py:21,34`.

**F14 · 🟡 P3 — juiz de eval morto e quebrado.** `evals/juiz_llm.py:119` chama `create_llm(provider=..., model=..., temperature=0)`, assinatura inexistente (`llm_factory.py:75-82`); 📊 zero chamadores de `julgar_com_llm`. A migration `20260824_01...sql:30` cita o arquivo como se funcionasse.

**F15 · 🟡 P3 — rótulo de modelo mente no log de conversa.** `nodes.py:2059` e `subagent_tool.py:666` gravam `"gpt-4-turbo"` quando o agente não tem modelo; a fábrica usa `gpt-4o` (`llm_factory.py:96`). CLAUDE.md §12.1 (campo que mente).

**F16 · 🟡 P3 — `reasoning_effort` só chega a `o1*`/`o3*`** (`llm_factory.py:200`); `gpt-5*` e Claude 5 ignoram o campo que a UI e o banco (`'medium'`) prometem.

**F17 · 🟡 P3 — envs de Gemini Live/Text declarados em prod não têm leitor neste repo**; chaves `CLAUDE_API_KEY`, `GEMINI_API_KEY`, `DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY` idem (comando em (a)). Ou a voz mora em outro repo/serviço, ou são envs órfãs.

---

## (h) O QUE FICOU POR MEDIR (e a query exata)

1. **Modelo real de cada agente em prod** (decide F1/F13): `select c.name, a.agent_role, a.llm_provider, a.llm_model, a.vision_model, a.is_hyde_enabled from agents a join companies c on c.id=a.company_id where a.is_active order by 1,2;`
2. **Default da coluna de memória em prod** (decide F3): `select column_default from information_schema.columns where table_name='memory_settings' and column_name='memory_llm_model';` e `select memory_llm_model, count(*) from memory_settings group by 1;`
3. **Preço de Claude 5 em `llm_pricing`** (decide F8): `select model_name, input_price_per_million, output_price_per_million, is_active from llm_pricing where model_name ilike 'claude%5%' or model_name ilike 'gemini-3%';`
4. **Ledger do Atlas** (F7): `select count(*) from token_usage_logs where created_at > now()-interval '30 days' and model_name ilike 'claude-opus-5%' and service_type='chat' and company_id is null;` + logs `[UsageService] ❌ Failed to log usage` com `invalid input syntax for type uuid: "atlas"`.
5. **Mix real de modelos no ledger** (o espelho de tudo acima): `select service_type, model_name, count(*), sum(total_cost_usd) from token_usage_logs where created_at > now()-interval '14 days' group by 1,2 order by 3 desc;` — a linha `gpt-4o-mini` × `service_type` mostra quais caminhos deste censo estão vivos.
6. **Auxiliares quebrados** (F4): uma chamada a `/api/auxiliaries/resumo-atendimentos/run` ou os logs; e `select status, count(*) from auxiliary_runs ... group by 1` (nome da tabela não conferido).
7. **Envs no WORKER e no PORTAL-WORKER**: `DISPATCH_LLM_*` presentes no contêiner do worker (o watchdog roda lá, `buffer_processor.py:1490`)? env do **docling-service** (`VISION_MODEL`)?
8. **Se o grafo de atendimento roda hoje**: `webhook.py:1568-1571` registra que em 03/09 `attendance_agent_active()` era falso em 4/4 agentes e o grafo não rodava. Se ainda for assim, F1/F6 no atendimento estão latentes e F2 (visão no pré-grafo) é o que roda.
9. **Chamada dupla de visão por foto** (F2): rodar uma mensagem com imagem e contar linhas `service_type='vision'` por `message`.
10. ✅ MEDIDO depois: 📊 `git log --all --oneline -S AUTOBROKERS_GEMINI` → **0 commits** em todas as branches locais e remotas (`origin/main` incluída). A voz Gemini nunca existiu neste repositório; quem lê essas envs é outro serviço, ou ninguém. (`git log --all -S CORE_CHAT_MODEL` → nasceu em `6c5cb8a` "FB-1 — stronger Core model policy (temporary…)".)

## FORA DO ESCOPO (visto de passagem)

- `attendance_media.py:157-160` busca `agents` por `id` SEM filtrar `company_id`, embora receba `company_id` no payload — um `agent_id` de outra corretora escolheria o `vision_model` dela (CLAUDE.md §7; leitura cruzada de config, não de dado de segurado).
- `llm_factory.py:247` header beta `prompt-caching-2024-07-31` (antigo; inofensivo).
- `backend/.env.example:104-106,122` marcam `GROQ_API_KEY` e `OPENROUTER_API_KEY` como **OBRIGATÓRIO** — em prod estão vazias.
- A árvore tem mudanças não commitadas anteriores a esta sessão (`git status`: `test_a_atendente_na_ura_cala_o_robo.py` modificado, 3 docs apagados, 8 não rastreados) — não tocadas.
