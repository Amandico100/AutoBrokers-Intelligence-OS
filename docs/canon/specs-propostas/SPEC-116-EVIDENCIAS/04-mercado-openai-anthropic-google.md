# Mercado A — OpenAI · Anthropic · Google (pesquisa de 23/09/2026)

> Todas as linhas foram lidas em fonte aberta em **23/09/2026** (data de acesso de toda URL abaixo, salvo nota).
> Marcação: 📊 = lido na fonte oficial nesta data · 💭 = inferência minha · ⚠️ = conflito entre fontes ou fonte secundária.
> Método: docs oficiais via WebFetch, e HTML/markdown cru via curl quando o resumo automático pareceu inconsistente
> (a página de preços do Gemini e a tabela de residência do Google Cloud foram lidas CRUAS, célula por célula).

---

## 0. Placar da proposta interna

| # | A proposta afirmou | Veredito | Fonte (acesso 23/09/2026) |
|---|---|---|---|
| 1 | GPT-6 Astra US$10/50, cached 1,00, 1,05M ctx | **CONFIRMADO** (+ cache write 12,50; >272K = 20/2/25/75; reasoning **low…max, SEM `none`**) | developers.openai.com/api/docs/models/gpt-6-astra · /api/docs/pricing |
| 2 | GPT-6 Sol US$2/10, cached 0,20, cache write 2,50, 1,05M ctx, 128K out | **CONFIRMADO** (nuance: **input máx. 922K**, a janela de 1,05M inclui a saída) | developers.openai.com/api/docs/models/gpt-6-sol |
| 3 | Sol reasoning none/low/medium/high/xhigh/max | **CONFIRMADO** — default **medium** | idem |
| 4 | Chat Completions só aceita function calling com `reasoning_effort=none`; Responses aceita tools com reasoning | **CONFIRMADO** — texto literal da doc: "Chat Completions supports function calling only with `reasoning_effort` set to `none`". Vale também para Luna | gpt-6-sol · gpt-6-luna |
| 5 | >272K custa mais | **CONFIRMADO** — 2× input/cache, 1,5× output (Sol longo: 4/0,40/5/15) | pricing |
| 6 | GPT-6 Luna US$0,10/0,50, cached 0,01 | **CONFIRMADO** (+ cache write 0,125; 1,05M ctx; 128K out; mesma restrição de tools no Chat Completions) | gpt-6-luna |
| 7 | URLs openai.com/index/introducing-gpt-6-sol-and-luna/ e /index/gpt-6-astra/ | **NÃO VERIFICÁVEL por leitura** (HTTP 403 ao robô); a 1ª aparece na busca com o título "Introducing GPT-6 Sol and Luna". O changelog oficial confirma: Astra 03/09/2026, Sol+Luna 22/09/2026 | developers.openai.com/api/docs/changelog |
| 8 | Sonnet 5 US$2/10 permanente desde 10/08/2026 | **CONFIRMADO** — o aumento para 3/15 previsto para 01/09 "no longer applies" | anthropic.com/news/claude-sonnet-5 · platform.claude.com/docs/en/about-claude/pricing |
| 9 | Opus 5.5 lançado 22/09/2026, US$4/20, cache read 0,20, cache write 5, fast 8/40 | **CONFIRMADO** (cache write 5 = TTL 5 min; **1h = US$8**; batch 2/10) | anthropic.com/claude-opus-5-5 · platform.claude.com/docs/en/models/opus-5-5/overview |
| 10 | "existe Haiku 5?" | **REFUTADO** — não existe Haiku 5. Atual = **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`). A Anthropic anunciou em 22/09 que **Sonnet 5.5 e Haiku 5.5** "will follow in the coming weeks" (sem data) | platform.claude.com/docs/en/models/overview · anthropic.com/claude-opus-5-5 |
| 11 | Fable 5.1 e Mythos existem na API? | **CONFIRMADO com ressalva**: `claude-fable-5-1` GA, US$10/50 (cache hit 0,25). `claude-mythos-5-1` = **"limited availability" (Glasswing)**, mesmo preço. 🔴 Ambos são "Covered Models": **exigem retenção de 30 dias e NÃO têm ZDR** | pricing · api-and-data-retention |
| 12 | Claude 5 rejeita `temperature`? | **CONFIRMADO** — valor não-default em `temperature`/`top_p`/`top_k` → **HTTP 400** em Opus 4.7 e posteriores (inclui Sonnet 5, Opus 5, Opus 5.5, Fable). O **SDK Python v1.0+ removeu** os três parâmetros (passar = `TypeError`) | platform.claude.com/docs/en/about-claude/model-deprecations (API parameter deprecations) · models/sonnet-5/overview |
| 13 | extended/adaptive thinking e effort | **CONFIRMADO + DETALHE**: `thinking.type:"enabled"+budget_tokens` **não é aceito** nos modelos atuais; controle é `output_config.effort` (low/medium/high/xhigh/max). Opus 5.5: thinking **sempre ligado** (`disabled` → 400), default effort **medium**. Sonnet 5: adaptive, default **high**. Haiku 4.5: extended thinking, sem effort | build-with-claude/effort · whats-new-opus-5-5 |
| 14 | gemini-3.8-flash estável, ~1,048M in / 65.536 out, texto/imagem/vídeo/áudio/PDF, FC, SO, thinking low/medium/high, computer use preview | **CONFIRMADO** (1.048.576 / 65.536; `minimal` NÃO suportado; **sem Live API**; lançado 02/09/2026 direto em GA) | ai.google.dev/gemini-api/docs/models/gemini-3.8-flash · blog.google/…/3-8-flash-and-3-8-flash-cyber/ |
| 15 | Gemini 3.8 Flash US$0,75/3,75 promocional até 31/12/2026 | **CONFIRMADO** — e 🔴 **dobra em 01/01/2027: US$1,50/7,50** (cache 0,075→0,15) | ai.google.dev/gemini-api/docs/pricing (markdown cru) |
| 16 | gemini-3-flash-preview deprecado? | **PARCIAL**: está na página de deprecações com **"no date announced"**, substituto `gemini-3.6-flash`; a página de preços o chama de "legacy Flash model". Sem data de desligamento hoje | ai.google.dev/gemini-api/docs/deprecations |
| 17 | gemini-3.1-flash-live-preview deprecado? qual Live atual? | **PARCIAL**: deprecado **sem data**, substituto **`gemini-3.8-live` (STABLE, set/2026)**; existe também `gemini-3.8-live-extended-thinking` | deprecations · models/gemini-3.8-live |

---

## 1. Matriz por modelo

Preços em US$/1M tokens: **input / cached input (leitura) / cache write / output**. "Longo" = acima do limiar de contexto longo.

### 1.1 OpenAI (fonte: developers.openai.com/api/docs/models/<id> e /api/docs/pricing — acesso 23/09/2026)

| Model ID | Status | Preço padrão | Longo (>272K) | Batch/Flex | Fast | Ctx / máx. input / out | Reasoning | Tools / restrição | SO | Modalidades | API | Rate limit T1→T5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `gpt-6-astra` | Ativo (lançado 03/09/2026) | 10 / 1,00 / 12,50 / 50 | 20 / 2 / 25 / 75 | 50% | 2× | 1,05M / 922K / 128K | low, medium, high, xhigh, max (**sem none**) | FC + web search, file search, code interpreter, **computer use**, hosted shell, apply patch, skills, MCP, tool search. ⚠️ no Chat Completions, FC com reasoning → 400 (erro literal em langchain #40346) | sim | texto+imagem → texto | Chat Completions, Responses, Batch | 500 RPM/500K TPM → 15K RPM/40M TPM |
| `gpt-6-sol` | Ativo (22/09/2026), cutoff 20/04/2026 | 2 / 0,20 / 2,50 / 10 | 4 / 0,40 / 5 / 15 | 1 / 0,10 / 1,25 / 5 | 4/0,40/5/20 | 1,05M / 922K / 128K | none, low, **medium (default)**, high, xhigh, max | mesmas tools do Astra; **Chat Completions: FC só com `reasoning_effort=none`** | sim | texto+imagem → texto (sem áudio) | Chat Completions, Responses, Batch | 500/500K → 15K/40M |
| `gpt-6-luna` | Ativo (22/09/2026), cutoff 18/05/2026 | 0,10 / 0,01 / 0,125 / 0,50 | 0,20 / 0,02 / 0,25 / 0,75 | 50% | 2× | 1,05M / 922K / 128K | none…max, default medium | idem Sol | sim | texto+imagem → texto | idem | 500/500K → 30K/180M |
| `gpt-5.6-sol` / `-terra` / `-luna` | Ativos (09/07/2026) | Sol 4/0,40/5/20 (promo até 21/11/2026) · Terra 2/0,20/2,50/12 · Luna 0,20/0,02/0,25/1,20 | 2×/1,5× | 50% | 2× | — | — | — | — | — | — | — |
| `gpt-5.4-mini` / `gpt-5.4-nano` | Ativos | mini 0,75/0,075/—/4,50 · nano 0,20/0,02/—/1,25 | — | 50% | — | — | — | — | — | — | — | — |
| `gpt-4o` | **Ativo, SEM aviso de deprecação**; cutoff 01/10/2023; default snapshot `gpt-4o-2024-08-06` | 2,50 / 1,25 / — / 10 | — | 1,25/—/—/5 | 4,25/2,125/—/17 | 128K / 16.384 out | não | FC | sim | texto+imagem | Chat Completions, Responses | — |
| `gpt-4o-mini` | **Ativo, SEM aviso**; único snapshot `gpt-4o-mini-2024-07-18` | 0,15 / 0,075 / — / 0,60 | — | 0,075/—/—/0,30 | — | 128K / 16.384 out | não | FC | sim | texto+imagem | idem | — |
| `text-embedding-3-small` | Ativo | 0,02 | — | batch disponível | — | — | — | — | — | texto | Embeddings | — |
| `text-embedding-3-large` | Ativo | 0,13 | — | — | — | — | — | — | — | — | — | — |
| 💭 Não há sucessor de embeddings na tabela de preços da OpenAI: **text-embedding-3-\* continua sendo a linha atual de embeddings da OpenAI** | | | | | | | | | | | | |
| `whisper-1` | 🔴 **DEPRECADO 26/08/2026 → desligamento 26/02/2027** | US$0,006/min | | | | | | | | áudio | /audio/transcriptions | |
| `gpt-4o-transcribe` / `-mini-transcribe` / `-transcribe-diarize` | 🔴 **idem, desligamento 26/02/2027** | 2,50/10 (≈US$0,006/min) · mini 1,25/5 (≈0,003/min) | | | | | | | | | | |
| `gpt-transcribe` (substituto) | Ativo (lançado 28/07/2026) | **US$0,0045/min** | | | | | | keyword hints, contexto livre, múltiplos idiomas esperados, streaming. ⚠️ a página NÃO lista idiomas nem diarização | | áudio → texto | /audio/transcriptions e realtime transcription | |
| `gpt-live-transcribe` (substituto streaming) | Ativo | US$0,017/min | | | | | | | | | realtime | |
| `gpt-realtime-2.1` / `-mini` | Ativos (06/07/2026) | áudio 32/0,40/64 · mini 10/0,30/20 | | | | | | | | | Realtime | |

Fontes: [gpt-6-sol](https://developers.openai.com/api/docs/models/gpt-6-sol) · [gpt-6-luna](https://developers.openai.com/api/docs/models/gpt-6-luna) · [gpt-6-astra](https://developers.openai.com/api/docs/models/gpt-6-astra) · [pricing](https://developers.openai.com/api/docs/pricing) · [gpt-4o](https://developers.openai.com/api/docs/models/gpt-4o) · [gpt-4o-mini](https://developers.openai.com/api/docs/models/gpt-4o-mini) · [text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small) · [gpt-transcribe](https://developers.openai.com/api/docs/models/gpt-transcribe) · [changelog](https://developers.openai.com/api/docs/changelog) · [deprecations](https://developers.openai.com/api/docs/deprecations) — todos acessados 23/09/2026.

Notas OpenAI:
- 📊 Residência regional custa **+10%** para modelos lançados após 05/03/2026 (GPT-6 incluso). EU para GPT-6 Sol/Luna = "Standard processing only" (sem Fast/Flex na UE). Fonte: [your-data](https://developers.openai.com/api/docs/guides/your-data).
- 📊 Changelog 02/09/2026: 429 com `slow_down` para tráfego rápido; 503 `server_is_overloaded`. Changelog 03/09: async tool calling, mid-turn steering, reasoning ajustável no meio da conversa (Responses).
- 💭 Para o nosso stack (ChatOpenAI em Chat Completions com tools): **Sol/Luna com tools obrigam OU `reasoning_effort="none"` OU `use_responses_api=True`**. O default (medium) + tools em Chat Completions tende a dar 400 (o erro equivalente já foi documentado para o Astra).

### 1.2 Anthropic (fonte: platform.claude.com/docs — acesso 23/09/2026)

| Model ID | Status / retirement (API 1P) | Input / cache hit / write 5m / write 1h / output | Batch | Fast | Ctx / out | Thinking | Effort (default) | Latência relativa | Cutoff confiável |
|---|---|---|---|---|---|---|---|---|---|
| `claude-fable-5-1` | Active; ≥ 01/09/2027 | 10 / 0,25 / 12,50 / 20 / 50 | 5/25 | — | 1M / 128K | Adaptive, sempre ligado | high | Slower | jun/2026 |
| `claude-mythos-5-1` | Active, **limited availability** | 10 / 0,25 / 12,50 / 20 / 50 | 5/25 | — | — | — | — | — | — |
| `claude-opus-5-5` | Active (lançado 22/09/2026); ≥ 22/09/2027 | 4 / **0,20** / 5 / 8 / 20 | 2/10 | **8/40** (research preview, só API 1P, header `fast-mode-2026-02-01`) | 1M / 128K (300K no Batch c/ beta) | Adaptive, **sempre ligado** (`disabled`/`enabled` → 400) | **medium** | Moderate | jun/2026 |
| `claude-opus-5` | Active; ≥ 24/07/2027 | 5 / 0,50 / 6,25 / 10 / 25 | 2,50/12,50 | 10/50 | 1M / 128K | Adaptive (disable aceito só com effort ≤ high) | high | — | — |
| `claude-sonnet-5` | Active (lançado 30/06/2026); ≥ 30/06/2027 | 2 / 0,20 / 2,50 / 4 / 10 | 1/5 | — | 1M / 128K | Adaptive (default on); **manual extended thinking → 400** | high | Fast | jan/2026 |
| `claude-sonnet-4-6` | Active; ≥ 17/02/2027 | 3 / 0,30 / 3,75 / 6 / 15 | 1,50/7,50 | — | — | — | — | — | — |
| `claude-haiku-4-5-20251001` (alias `claude-haiku-4-5`) | Active; 🔴 **retirement "not sooner than 15/10/2026"** — é o próximo candidato a deprecação | 1 / 0,10 / 1,25 / 2 / 5 | 0,50/2,50 | — | **200K / 64K** | Extended (manual) | **não suporta effort** | Fastest | fev/2025 |
| `claude-3-5-sonnet-20240620` / `-20241022` | 🔴 **RETIRED em 28/10/2025** — requisições falham | — | | | | | | | |
| `claude-3-5-haiku-20241022` | 🔴 **RETIRED em 19/02/2026** | — | | | | | | | |

Recursos comuns aos atuais: texto+imagem → texto, visão, PDF, Files API, tool use, prompt caching (mín. 512 tokens no Opus 5.5), structured outputs e **strict tool use**, Batch; API = **Messages** (`/v1/messages`).
Computer use: `computer_toolset_20260801` (~4.500 tokens de overhead); browser use: `browser_toolset_20260801` (~6.600 tokens). 🔴 Opus 5.5 **rejeita** `computer_20251124` na API 1P e no Google Cloud (Bedrock ainda aceita).
Tokenizer novo (Opus 4.7+): **~30% mais tokens para o mesmo texto** — 💭 afeta comparação de custo com Sonnet 4.6/Haiku 4.5.
Residência: `inference_geo` = `global` (default) ou `us` (**+10%**); **não há EU nem Brasil na API 1P**; `inference_geo` em Haiku 4.5 → 400.

Fontes: [models overview](https://platform.claude.com/docs/en/about-claude/models/overview) · [pricing](https://platform.claude.com/docs/en/about-claude/pricing) · [model-deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations) · [opus-5-5 overview](https://platform.claude.com/docs/en/models/opus-5-5/overview) · [whats-new-opus-5-5](https://platform.claude.com/docs/en/models/opus-5-5/whats-new-opus-5-5) · [sonnet-5 overview](https://platform.claude.com/docs/en/models/sonnet-5/overview) · [effort](https://platform.claude.com/docs/en/build-with-claude/effort) · [data-residency](https://platform.claude.com/docs/en/manage-claude/data-residency) · [anthropic.com/claude-opus-5-5](https://www.anthropic.com/claude-opus-5-5) · [anthropic.com/news/claude-sonnet-5](https://www.anthropic.com/news/claude-sonnet-5) — acesso 23/09/2026.

🔴 **Mudanças do Opus 5.5 que quebram código hoje em produção (fonte: whats-new-opus-5-5):**
1. `tool_choice` `{"type":"any"}` ou `{"type":"tool"}` → **400** "tool_choice: type "tool" and "any" are not supported for this model." Alternativa oficial: `auto` + `strict: true` ou structured outputs. 💭 `with_structured_output()` do LangChain usa tool forçada por padrão.
2. `thinking: disabled` ou `enabled+budget_tokens` → **400**.
3. **Thinking blocks presos ao modelo e à conversa**: Opus 5.5 → Sonnet 5 perde o raciocínio (bloco é descartado silenciosamente). Para contas criadas **a partir de 31/08/2026**, reenviar um bloco depois de mudar `system`, `tools` ou mensagem anterior → **400** (opt-out via header beta `thinking-binding-controls-2026-08-01` + `drop_block`).
4. `computer_20251124` rejeitado (API 1P e Google Cloud).
5. Texto entre tool calls vem em blocos `thinking` com texto vazio no `display` default — quem mostra "progresso" ao usuário fica mudo.
6. Refusal por classificador volta **HTTP 200** com `stop_reason:"refusal"` (biologia + cyber + `reasoning_extraction`).

### 1.3 Google (fonte: ai.google.dev — acesso 23/09/2026; preços lidos no markdown cru da página)

| Model code | Status | Input / cache / output (pago) | Batch/Flex | Priority | Ctx / out | Thinking | Tools | Modalidades | API |
|---|---|---|---|---|---|---|---|---|---|
| `gemini-3.8-flash` | **Stable**, lançado 02/09/2026 | **0,75 / 0,075 / 3,75 até 31/12/2026 → 1,50 / 0,15 / 7,50 a partir de 01/01/2027**; storage de cache 0,50→1,00 /1M tok/h | 0,375/1,875 (→0,75/3,75) | 1,35/6,75 (→2,70/13,50) | 1.048.576 / 65.536 | `thinking_level` low/medium(default)/high; **não desliga; `minimal` não suportado** | FC, structured outputs, code execution, Search/Maps grounding, URL context, file search, **computer use (Preview)**; **sem Live API** | texto, imagem, vídeo, áudio, PDF → texto | generateContent / Interactions; OpenAI-compat ("Chat completions: Supported" no Agent Platform) |
| `gemini-3.7-flash` / `gemini-3.6-flash` | Stable | 3.7 = mesmo preço do 3.8 | | | | 3.6 aceita `minimal` | | | |
| `gemini-3.5-flash-lite` | Stable | 0,30 / 0,03 / 2,50 | 0,15/1,25 | 0,54/4,50 | — | default `minimal` | | | |
| `gemini-3.1-pro-preview` (Pro atual) | **Preview** | 2 / 0,20 / 12 (≤200K) · 4 / 0,40 / 18 (>200K) | | | — | | | | |
| `gemini-3-flash-preview` | "legacy"; deprecado **sem data**, substituto `gemini-3.6-flash` | 0,50 / 0,05 / 3,00 (áudio in 1,00) | 0,25/1,50 | | 1.048.576 / 65.536 | | | | |
| `gemini-3.8-live` | **Stable** (set/2026) — **Live atual** | text 0,75 in / 4,50 out · áudio 3,00 in (≈US$0,005/min) / 12,00 out (≈0,018/min) | | | 131.072 / 65.536 | interleaved reasoning | FC assíncrona por padrão | texto, imagem, áudio, vídeo → texto+áudio; pt-BR suportado | Live API (WebSocket) |
| `gemini-3.1-flash-live-preview` | deprecado **sem data**, substituto `gemini-3.8-live` | mesmo preço do 3.8 Live | | | | | | | |
| `gemini-3.5-transcribe` | Stable | áudio 2,00 in (≈0,003/min) / 12,00 out → blended ≈ **US$0,005/min** | | | | | diarização, timestamps por palavra, vocabulário custom, detecção de idioma | áudio → texto | |
| `gemini-3.5-transcribe-live` | — | ≈ US$0,009/min blended | | | | | | | streaming |
| `gemini-embedding-2` | ⚠️ "Stable (abr/2026)" na página do modelo, mas "Preview" no overview | texto 0,20 · imagem 0,45 · áudio 6,50 · vídeo 12,00; batch 50% | | | 8.192 in; dims 128–3072 (MRL) | | | multimodal | embedContent |
| `gemini-embedding-001` | deprecado, **desligamento 14/05/2028** | | | | | | | | |

Fontes: [gemini-3.8-flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) · [pricing](https://ai.google.dev/gemini-api/docs/pricing) · [deprecations](https://ai.google.dev/gemini-api/docs/deprecations) · [models](https://ai.google.dev/gemini-api/docs/models) · [gemini-3.8-live](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live) · [thinking](https://ai.google.dev/gemini-api/docs/thinking) · [gemini-embedding-2](https://ai.google.dev/gemini-api/docs/models/gemini-embedding-2) · [blog 3.8 Flash](https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/) · [Agent Platform 3.8 Flash](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash) — acesso 23/09/2026.

Notas Google:
- 📊 Defaults do 3.8 Flash no Agent Platform: temperature 1.0, topP 0.95, topK 64. PDF faturado à taxa de imagem.
- 📊 Thought signatures: é obrigatório reenviar os blocos `thought` exatamente como recebidos no multi-turn com function calling.
- 💭 O 3.8 Flash substitui bem o `gemini-3-flash-preview` para texto/visão/PDF, **mas não substitui o Live**: o Live vai para `gemini-3.8-live`.

---

## 2. Privacidade / LGPD por provedor (🔴 bloqueante para PII)

| | OpenAI | Anthropic | Google (Gemini Developer API) |
|---|---|---|---|
| Treino com dados da API (default) | **Não** ("not used to train… unless customers explicitly opt in") | **Não** ("never used for model training without your express permission") | **Pago: não. 🔴 FREE TIER: SIM** ("Content used to improve our products") |
| Retenção padrão | Logs de abuse monitoring **até 30 dias**; `/v1/responses` guarda estado com **`store=true` por default** (até apagar) | Política comercial: "delete inputs and outputs… **within 30 days**" (privacy.claude.com, atualizada 01/07/2026). ⚠️ A doc técnica diz "conversation content is not retained by default" salvo Covered Models (30 dias) — as duas fontes divergem no texto. Conteúdo sinalizado: **até 2 anos**; scores de T&S: **até 7 anos** | Abuse monitoring: **55 dias** (usage-policies, via resumo); conteúdo sinalizado pode ter revisão humana. Grounding Search/Maps: **30 dias, sem opt-out** |
| ZDR | Sim — **ZDR** ou **Modified Abuse Monitoring**, **só com aprovação de vendas**; ZDR força `store=false` | Sim — **via vendas, por organização**. 🔴 **Não vale para Fable 5.1/Mythos 5.1/Fable 5/Mythos 5** (Covered Models, 30 dias obrigatórios). Batch, Files API e code execution **não** são ZDR | Página "ZDR" orienta: Interactions `store=false` (default é guardar), não usar `SessionResumptionConfig` no Live (até 24h), apagar arquivos da File API, **não usar `cached_content`** (cache explícito); cache implícito em RAM 24h "não viola ZDR" |
| DPA | Sim — openai.com/policies/data-processing-addendum | Sim — embutido nos Commercial Terms | Sim, para Paid Services — "Data Processing Addendum for Products Where Google is a Data Processor" |
| Subprocessadores | openai.com/policies/sub-processor-list (⚠️ fonte secundária registora.com: 24 entradas, Microsoft, CoreWeave, Cloudflare) | Trust Center (trust.anthropic.com), aviso de 15 dias | via DPA do Google |
| Regiões de processamento | Armazenamento: EUA, Europa, Austrália, Canadá, Japão, Índia, Singapura, Coreia do Sul, Reino Unido, EAU. **Processamento só em EUA, UE e EAU**. **Sem Brasil.** +10% | `inference_geo`: **global ou us** (+10%); workspace geo: **só us**. **Sem UE e sem Brasil na API 1P** | Developer API: **sem opção de residência**. No **Agent Platform (Vertex)**: `gemini-3.8-flash` com ML processing só em **multi-região US ou EU**; Brasil (`southamerica-east1`) com ML processing **só para `gemini-2.5-flash` (128K)**. Claude no Google Cloud: Opus 5.5 = US/EU/Singapura; Sonnet 5 = US/EU |

Fontes: [OpenAI your-data](https://developers.openai.com/api/docs/guides/your-data) · [OpenAI DPA](https://openai.com/policies/data-processing-addendum/) · [OpenAI sub-processors](https://openai.com/policies/sub-processor-list/) · [Anthropic api-and-data-retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention) · [Anthropic retenção comercial](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data) · [Anthropic data-residency](https://platform.claude.com/docs/en/manage-claude/data-residency) · [trust.anthropic.com](https://trust.anthropic.com/) · [Gemini terms](https://ai.google.dev/gemini-api/terms) · [Gemini ZDR](https://ai.google.dev/gemini-api/docs/zdr) · [Gemini usage-policies](https://ai.google.dev/gemini-api/docs/usage-policies) · [Gemini pricing (coluna "Used to improve our products")](https://ai.google.dev/gemini-api/docs/pricing) · [Agent Platform data residency](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/data-residency) (HTML cru, tabela lida célula por célula) — acesso 23/09/2026.

💭 Leitura para LGPD: **nenhum dos três oferece processamento no Brasil** para os modelos atuais; todos exigem transferência internacional (LGPD art. 33) amparada por cláusula contratual/DPA. As alavancas reais são: **conta paga (nunca o free tier do Gemini)**, **ZDR contratado** (OpenAI e Anthropic via vendas), `store=false` explícito (OpenAI Responses e Gemini Interactions), evitar Fable/Mythos para PII se ZDR for requisito, e não usar cache explícito do Gemini com PII se ZDR for requisito.

---

## 3. Deprecações com data (as que tocam o AutoBrokers)

| Modelo em uso | Situação em 23/09/2026 | Data | Substituto oficial | Fonte |
|---|---|---|---|---|
| `claude-3-5-sonnet-20240620` / `-20241022` | 🔴 **RETIRED — requisição falha** | desde **28/10/2025** | claude-sonnet-4-6 (hoje: claude-sonnet-5) | [anthropic deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations) |
| `claude-3-5-haiku-20241022` | 🔴 **RETIRED** | desde **19/02/2026** | claude-haiku-4-5-20251001 | idem |
| `claude-haiku-4-5` | Active, mas retirement **"not sooner than 15/10/2026"** | ≥ 15/10/2026 (aviso mínimo de 60 dias) | 💭 provável Haiku 5.5 ("coming weeks") | idem |
| `claude-sonnet-5` | Active | ≥ 30/06/2027 | — | idem |
| `claude-opus-5` | Active | ≥ 24/07/2027 | claude-opus-5-5 (migração recomendada) | idem |
| `whisper-1` | 🔴 **DEPRECADO** (anunciado 26/08/2026) | desligamento **26/02/2027** | `gpt-transcribe` / `gpt-live-transcribe` | [openai deprecations](https://developers.openai.com/api/docs/deprecations) |
| `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, `gpt-4o-transcribe-diarize` | 🔴 **DEPRECADOS** | **26/02/2027** | idem | idem |
| `gpt-4o` / `gpt-4o-mini` | **Ativos, sem deprecação anunciada** | — | — | [gpt-4o](https://developers.openai.com/api/docs/models/gpt-4o) · [gpt-4o-mini](https://developers.openai.com/api/docs/models/gpt-4o-mini) |
| `gpt-realtime`, `gpt-audio`, `gpt-4o-realtime/-audio`, `-mini` | Deprecados (20/07/2026) | **20/01/2027** | gpt-realtime-2.1, gpt-audio-1.5 | openai deprecations |
| `gpt-5-2025-08-07`, `-mini`, `-nano`, `o3-2025-04-16` | Deprecados (11/06/2026) | **11/12/2026** | gpt-5.6-* | idem |
| `o4-mini-2025-04-16`, `gpt-4-turbo`, `gpt-3.5-turbo-0125`… | Deprecados (22/04/2026) | **23/10/2026** | gpt-5.6-* | idem |
| Assistants API | **Desligada em 26/08/2026** | — | Responses + Conversations | idem |
| `text-embedding-3-small` | Ativo | — | — | openai model page |
| `gemini-3-flash-preview` | Deprecado, "legacy" | **sem data** | gemini-3.6-flash | [gemini deprecations](https://ai.google.dev/gemini-api/docs/deprecations) |
| `gemini-3.1-flash-live-preview` | Deprecado | **sem data** | **gemini-3.8-live** | idem |
| `gemini-3-pro-preview` | desligado | 09/03/2026 | gemini-3.1-pro-preview | idem |
| `text-embedding-004` (Google) | desligado | 14/01/2026 | gemini-embedding-2 | idem |
| `gemini-embedding-001` | deprecado | **14/05/2028** | gemini-embedding-2 | idem |
| `gemini-2.5-flash-image` | deprecado | **02/10/2026** | gemini-3.1-flash-image | idem |
| Parâmetros `temperature`/`top_p`/`top_k` (Claude ≥ 4.7) | Deprecados: valor não-default → 400; SDK Python v1.0 removeu | já em vigor | usar prompt | anthropic deprecations |

---

## 4. Benchmarks independentes (com data)

**Artificial Analysis — leaderboard lido em 23/09/2026** ([artificialanalysis.ai/leaderboards/models](https://artificialanalysis.ai/leaderboards/models); a página não mostra data de atualização; ⚠️ lido via resumo automático):

| Modelo (effort) | Intelligence Index | tokens/s | latência (s) | preço na coluna AA |
|---|---|---|---|---|
| Claude Opus 5.5 (max / xhigh / high / medium / low) | 58 / 56 / 54 / 51 / 42 | —/92/90/75/76 | —/155/34,9/22,8/4,8 | 5,98/3,46/1,82/1,34/0,55 |
| Claude Fable 5.1 (max) | 53 | 65 | 291 | 7,63 |
| GPT-6 Astra (max) | 53 | 53 | 361 | 3,26 |
| GPT-6 Sol (max / xhigh / high / medium / low / non-reasoning) | 48 / 44 / 43 / 40 / 34 / 28 | 126/119/100/114/118/103 | 107/44,8/8,1/1,96/1,44/0,97 | 1,06/0,53/0,37/0,25/0,13/0,33 |
| Gemini 3.8 Flash (high / medium / low) | 41 / 40 / 33 | 276 (high) | 13,8 (high) | 1,24/0,93/— |
| Claude Sonnet 5 (max / xhigh / high / medium / low / non-reasoning) | 38 / 34 / 32 / 28 / 24 / 23 | 78/66/66/64/61/62 | 146/35,3/9,1/2,4/1,8/1,07 | 5,09/2,87/1,79/1,00/0,51/— |
| GPT-6 Luna (max / high / medium / low / non-reasoning) | 37 / 32 / 29 / 21 / 18 | 157/141/143/152/140 | 143/7,1/5,3/1,6/0,74 | 0,07/0,03/0,02/0,0045/0,01 |
| GPT-5.6 Terra (high) | 34 | 77 | 3,3 | 0,34 |
| Gemini 3.1 Pro Preview | 30 | 116 | 23,7 | 0,67 |
| Gemini 3.5 Flash-Lite | 22 | 357 | 8,1 | 0,12 |
| Claude Haiku 4.5 | 17 | 109 | 23,1 | 0,21 |

⚠️ **Escala do índice mudou**: The Register (02/09/2026) cita Gemini 3.8 Flash = **59** e Opus 5 = 63 no mesmo índice; a página atual mostra 41. Compare só números da mesma página. Fonte: [The Register 02/09/2026](https://www.theregister.com/ai-and-ml/2026/09/02/with-gemini-38-flash-google-reminds-everyone-its-still-in-the-race/5294049).

**Números de fornecedor (não independentes):**
- OpenAI (via [Vellum 22/09/2026](https://www.vellum.ai/blog/gpt-6-sol-and-luna-benchmarks-explained) e [MarkTechPost 22/09/2026](https://www.marktechpost.com/2026/09/22/openai-releases-gpt-6-sol-and-luna-50-cheaper-api-pricing-and-benchmarks/)): AutomationBench 1.0.6 Sol xhigh 33,2% vs Fable 5.1 max 31,4% vs Opus 5 max 26,9%; OSWorld 2.0 offline Astra 72,6%, Sol xhigh 60,5%, Opus 5 med 60,3%, Luna max 58,1%; DeepSWE v1.1 Sol 68,8%, Luna 66,6%.
- Anthropic ([claude-opus-5-5](https://www.anthropic.com/claude-opus-5-5)): Opus 5.5 Terminal-Bench 4.0 66,4%; OSWorld 2.0 81,8% (parcial); GDPval-AA v2.1 1846 Elo. A própria Anthropic diz que "benchmark margins have become a less reliable guide".
- Google ([blog](https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/)): HLE-Verified 54,9%; CWE-Bench 47,2% pass@1; melhora em robustez a prompt injection (Gray Swan IPI), sem número.
- τ²-bench: saturado (top 99,1% em agregadores de set/2026); não achei número oficial de GPT-6/Opus 5.5/3.8 Flash. OpenRouter τ²-Airline: Gemini 3.7 Flash lidera com 80,6% em 22/09/2026 ([openrouter](https://openrouter.ai/benchmarks/tau2-bench-airline), via busca).

---

## 5. Relatos práticos de devs (classificados)

| Modelo | Relato | Classe | Fonte (acesso 23/09/2026) |
|---|---|---|---|
| Opus 5.5 | `ChatAnthropic` manda `tool_choice` forçado e `thinking disabled` → 400. PR #40766 corrigiu só `with_structured_output()`; `bind_tools()` e kwargs de chamada ainda passam. langchain-anthropic 1.7.3. Aberto 23/09 | **REPRODUCIBLE BUG + OFFICIAL ACKNOWLEDGEMENT** (quebra documentada pela Anthropic) **+ MULTIPLE INDEPENDENT REPORTS** | [langchain #40777](https://github.com/langchain-ai/langchain/issues/40777) · [langchain-aws #1310](https://github.com/langchain-ai/langchain-aws/issues/1310) · [deepagents #6509](https://github.com/langchain-ai/deepagents/issues/6509) · [crewAI #7725](https://github.com/crewAIInc/crewAI/issues/7725) · [vercel/ai #21364](https://github.com/vercel/ai/issues/21364) · [griptape #2351](https://github.com/griptape-ai/griptape/issues/2351) |
| Sonnet 5 / Opus 5 / 4.7+ | `temperature`/`top_k` repassados → 400 "`temperature` is deprecated for this model". PR de validação local (#40743) **fechado sem merge** em 22/09 | **MULTIPLE INDEPENDENT REPORTS + OFFICIAL** (doc) · **NÃO corrigido no LangChain** | [langchain #40721](https://github.com/langchain-ai/langchain/issues/40721) · [PR #40743](https://github.com/langchain-ai/langchain/pull/40743) · [kotaemon #867](https://github.com/Cinnamon/kotaemon/issues/867) · [verdikta #51](https://github.com/verdikta/verdikta-arbiter/issues/51) · [Vibe-Trading #1329](https://github.com/HKUDS/Vibe-Trading/issues/1329) |
| GPT-6 Astra | `ChatOpenAI` com tools ia para Chat Completions → 400 "Function tools with reasoning_effort are not supported for gpt-6-astra in /v1/chat/completions. To use function tools, use /v1/responses." | **REPRODUCIBLE BUG → FIXED** (Astra adicionado a `_RESPONSES_API_ONLY_PREFIXES`; versão de release não identificada) | [langchain #40346](https://github.com/langchain-ai/langchain/issues/40346) |
| GPT-6 Sol/Luna | Mesma restrição (doc oficial). Não confirmei se Sol/Luna já entraram na lista de roteamento automático do langchain-openai; vários projetos abriram issue de suporte em 22–23/09 | **OFFICIAL** (restrição) · roteamento no LangChain **NÃO VERIFICADO** | [pydantic-ai #8634](https://github.com/pydantic/pydantic-ai/issues/8634) · [LibreChat #16216](https://github.com/danny-avila/LibreChat/issues/16216) |
| GPT-6 (todas) | `bind_tools()` rejeita shell tool e Programmatic Tool Calling (ValueError local) | **REPRODUCIBLE BUG** (status não confirmado) | [langchain #40782](https://github.com/langchain-ai/langchain/issues/40782) |
| GPT-6 Sol/Luna | Thread oficial de lançamento: **sem reclamação técnica** até 23/09 10h (modelo tem < 24 h) | ANECDOTE (ausência de sinal ≠ ausência de bug) | [community.openai.com](https://community.openai.com/t/announcing-gpt-6-sol-and-gpt-6-luna-in-the-api-codex-and-chatgpt/1399925) |
| Gemini 3.8 Flash | "Corrupted thought signature" (400) analisando imagem via OpenRouter | **REPRODUCIBLE BUG** num projeto; corrigido do lado do cliente (PR #111559); sem reconhecimento do Google | [hermes-agent #111311](https://github.com/NousResearch/hermes-agent/issues/111311) |
| Gemini 3 Flash Preview (em produção hoje) | thought_signature inconsistente em function calls **paralelas** → 400 e possível perda silenciosa | **MULTIPLE INDEPENDENT REPORTS** | [forum Google](https://discuss.ai.google.dev/t/gemini-3-flash-preview-inconsistent-thought-signature-generation-in-parallel-function-calls-causes-400-errors-and-potential-silent-data-loss/118936) · [pipecat #3557](https://github.com/pipecat-ai/pipecat/issues/3557) |
| Gemini 3.8 Flash | ~40% mais tokens que o 3.7 (mais passos de raciocínio e tool calls iterativas) | OFFICIAL (Google, citado pela imprensa) | [The Register](https://www.theregister.com/ai-and-ml/2026/09/02/with-gemini-38-flash-google-reminds-everyone-its-still-in-the-race/5294049) · blog.google ("may consume more tokens") |
| Opus 5.5 | Reenviar thinking após editar system/tools → 400 em contas novas (≥ 31/08/2026) | **OFFICIAL** (comportamento documentado) | whats-new-opus-5-5 · [The New Stack](https://thenewstack.io/claude-opus-agent-migration/) |

Nenhum relato de *looping* ou *overthinking* reproduzível encontrado para GPT-6 Sol/Luna ou Opus 5.5 — 💭 esperado: saíram há < 48 h.

---

## 6. O que NÃO consegui verificar

1. Páginas `openai.com/index/introducing-gpt-6-sol-and-luna/` e `openai.com/index/gpt-6-astra/` — HTTP 403 ao robô; só confirmei que existem via busca e via changelog.
2. Idiomas suportados (pt-BR) e diarização do `gpt-transcribe` — a página do modelo não lista.
3. Se o langchain-openai já roteia `gpt-6-sol`/`gpt-6-luna` para a Responses API automaticamente, e a versão de release do fix do Astra.
4. Número exato de retenção de abuse monitoring do Gemini (55 dias) — veio de resumo automático da página usage-policies, não de leitura crua.
5. Divergência de texto da Anthropic sobre retenção padrão ("apagamos em 30 dias" no centro de privacidade vs "não retido por padrão" na doc técnica) — não consegui resolver; tratar 30 dias como o pior caso.
6. Rate limits por tier da Anthropic e do Gemini 3.8 Flash (só os da OpenAI foram lidos).
7. Bedrock em `sa-east-1` (São Paulo) para Claude 5.x — não pesquisado; a doc da Anthropic diz que o Bedrock tem endpoints regionais com "guaranteed data routing", sem lista de regiões conferida.
8. SWE-bench Verified/Pro, Terminal-Bench, BFCL e MCP-Atlas independentes para os modelos de 21–23/09 — não achei números independentes publicados.
9. Status de `gemini-embedding-2`: a página do modelo diz Stable e o overview diz Preview.
10. Latência em PT-BR / WhatsApp — nenhuma fonte independente; os números de latência acima são do Artificial Analysis (prompt padrão deles, não o nosso).
