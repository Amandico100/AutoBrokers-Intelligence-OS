# Supabase — configuração viva e ledger (📊 medido 23/09/2026 ~10h, projeto dcajcvlzcjbmyapmklil, MCP execute_sql read-only)

## Colunas de modelo no schema (information_schema.columns ilike model/llm/provider/vision/embedding/reasoning)
agents.{llm_provider,llm_model,vision_model,reasoning_effort,llm_max_tokens,llm_temperature,llm_api_key,vision_api_key}
companies.{llm_provider,llm_model,vision_model,llm_api_key,vision_api_key}
memory_settings.memory_llm_model · llm_pricing.{provider,model_name} · token_usage_logs.model_name
usage_events.{provider,model,provider_cost_usd} · conversation_logs.{llm_provider,llm_model} · eval_runs.modelo
conduct_playbooks.model_used · credit_transactions.model_name
⚠️ agents.llm_api_key / companies.llm_api_key existem (chave por tenant em texto): hoje 0 presentes (8/8 agentes, todas companies) — superfície de BYOK a governar.

## Agentes (8 linhas)
| empresa | agente | papel | ativo | provider/model | vision_model | effort | temp |
|---|---|---|---|---|---|---|---|
| AMANDUS | JOANA | attendance | não | anthropic/claude-sonnet-5 | – | low | 0.40 |
| AMANDUS | AutoBrokers Sandbox | core | sim | anthropic/claude-sonnet-5 | – | low | 0.40 |
| Blueprint Studio | Even | attendance | não | anthropic/claude-sonnet-5 | – | medium | 0.70 |
| Blueprint Studio | AutoBrokers | core | não | anthropic/claude-sonnet-5 | **gpt-4o** | medium | 0.70 |
| AutoFleet | Maria Regina | attendance | não | anthropic/claude-sonnet-5 | – | medium | 0.70 |
| AutoFleet | AutoBrokers | core | sim | anthropic/claude-sonnet-5 | – | medium | **0.90** |
| Resulta | Amanda | attendance | não | anthropic/claude-sonnet-5 | – | medium | 0.70 |
| Resulta | AutoBrokers | core | sim | anthropic/claude-sonnet-5 | – | low | **0.90** |
companies: só Resulta tem llm_provider/model gravado (anthropic/claude-sonnet-5).

## memory_settings: 8/8 linhas = gpt-4o-mini (AutoFleet ×2, Resulta ×1, 5 sem company resolvida)
Código (constants.py:77) diz Haiku 4.5 → o banco vence → runtime = gpt-4o-mini (ledger confirma: memory = gpt-4o-mini-2024-07-18, 231 eventos, último 10/09).

## llm_pricing: 50 linhas, sem coluna de data de vigência/fonte
- claude-sonnet-5 = 3/15 (oficial 2/10 desde 10/08 segundo a proposta — a confirmar pela pesquisa)
- cached_input_multiplier = 0.50 e cache_read_multiplier = 0.10 IGUAIS para todas as linhas de todos os provedores
- AUSENTES: claude-opus-5-5, gpt-6-*, gemini-3.8-flash, gemini-3.1-flash-live-preview, grok-4.7, mimo, glm, deepseek atuais
- Presentes e mortos: claude-3-5-*, claude-3-7, claude-opus-4/4.1, o1-preview, gemini-1.5-*, chatgpt-4o-latest, grok-3, deepseek-chat (provider "other")
- sell_multiplier 2.68 em todas

## Ledger token_usage_logs por modelo/serviço
| modelo | serviço | 7d | 30d | 45d | total | in45 | out45 | cache read45 | cache write45 | US$45 | 1ª | última | tenants |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|---|--:|
| claude-sonnet-5 | plataforma | 532 | 532 | 532 | 532 | 1.136.306 | 266.964 | 0 | 0 | 7,41 | 18/09 | 18/09 02:12 | **0** |
| claude-sonnet-5 | chat | 38 | 210 | 386 | 4.895 | 8.225.444 | 168.081 | 5.704.958 | 982.694 | 12,53 | 11/07 | 21/09 21:12 | 3 |
| text-embedding-3-small | rag_query | 93 | 213 | 320 | 778 | 15.188 | 0 | 0 | 0 | 0,0003 | 08/06 | 21/09 | 3 |
| gpt-4o-mini-2024-07-18 | memory | 0 | 38 | 55 | 233 | 1.523.433 | 3.656 | 0 | 0 | 0,23 | 26/07 | 10/09 | 3 |
| claude-opus-5 | chat | 0 | 5 | 26 | 57 | 122.130 | 35.213 | 0 | 0 | 1,49 | 28/07 | 10/09 | 2 |
| text-embedding-3-small | embedding | 5 | 10 | 12 | 21 | 57.836 | 0 | 0 | 0 | 0,0012 | 12/06 | 21/09 | 3 |
| gpt-4o-mini-2024-07-18 | vision | 0 | 4 | 6 | 20 | 175.986 | 597 | 0 | 0 | 0,027 | 04/07 | 10/09 | 2 |
| whisper-1 | audio | 0 | 0 | 4 | 4 | 76 | 0 | 0 | 0 | 0,0076 | 16/08 | 17/08 | 1 |
| gpt-4o-mini | chat | – | – | 0 | 330 | | | | | | 05/06 | 10/07 | 2 |
| gpt-4o | chat | – | – | 0 | 180 | | | | | | 23/06 | 10/07 | 1 |
| gpt-4o-mini | auxiliary_run | – | – | 0 | 5 | | | | | | 08/06 | 09/06 | 1 |

usage_events (espelho): sonnet-5/chat 4.653 · gpt-4o-mini/memory 231 · opus-5/chat 57 · gpt-4o-mini/vision 6 · firecrawl/tool 6.
conversation_logs 45d: anthropic/claude-sonnet-5 = 193.

## O ELO — superfícies que RODARAM mas NÃO aparecem no ledger
| superfície | prova de que rodou | no ledger? |
|---|---|---|
| distiller estágio 2 (Opus 5) | conduct_playbooks: 18 linhas model_used=claude-opus-5 | ❌ nenhum service distiller |
| garimpo / broker_insights | broker_insights 855 linhas, última **23/09 00:03** | ❌ (precisa confirmar que é LLM — censo) |
| portal worker (adaptive, gpt-4o default) | portal_jobs 38 em 45d (29 done · 4 failed · 4 needs_human), último 11/09; nenhum job grava modelo | ❌ nenhum gpt-4o em 45d |
| dispatch/acionamento (DISPATCH_LLM_MODEL=claude-opus-5 em prod) | a confirmar (tabelas de dispatch) | ❌ nenhum service dispatch |
| atlas parser (ATLAS_PARSER_MODEL=claude-opus-5) | a confirmar | ❌ |
| voz Gemini live / texto Gemini | a confirmar | ❌ nenhum gemini no ledger |
| auxiliares (Haiku 4.5 default) | a confirmar | ❌ último auxiliary_run 09/06 (gpt-4o-mini) |
| "plataforma" 532 chamadas em 18/09 com tenant NULL | lote da base de planos (001.5.2?) | ✅ mas sem tenant |

## Eval Platform JÁ EXISTE (SPEC-062): eval_datasets 3 · eval_cases 8 · evaluator_definitions 7 · eval_runs 0 · eval_case_results 0 · online_eval_samples 0
→ CLAUDE.md §5 proíbe Eval Platform paralela: o E2E Bench ESTENDE estas tabelas; as `bench_*` da proposta seriam motor paralelo.

## Baseline de sucesso do portal (📊 portal_jobs 45d): 29/38 done = 76% · 4 failed · 4 needs_human · 1 archived

## Complemento (📊 23/09 ~10h30)
- DEFAULT de coluna: memory_settings.memory_llm_model = 'gpt-4o-mini' (information_schema.columns.column_default) → toda linha nova nasce legada. agents.llm_model/vision_model/llm_provider sem default; agents.reasoning_effort default 'medium'.
- Chat por agente (token_usage_logs service_type=chat, 45d | 7d | último):
  Resulta core 197|4|17/09 · Resulta Amanda (attendance) 96|0|**10/09** · Sandbox core 34|32|21/09 · AutoFleet core 30|2|21/09 · AutoFleet Maria Regina (attendance) 29|0|**09/09** · sem agente (Resulta) 22|0|10/09 · Global Knowledge 4|0|10/08
  → o ATENDIMENTO está parado desde 10/09 (agentes attendance is_active=false). Baseline de atendimento terá de vir de REPLAY do acervo, não de tráfego vivo.
