# Mercado B — xAI · Xiaomi MiMo · DeepSeek · Z.ai GLM · Kimi (+ benchmarks independentes)

> Pesquisa de 23/09/2026. Todas as fontes foram abertas nesse dia. Não saiu nada de memória.
> Escopo: xAI, MiMo, DeepSeek, Z.ai, Moonshot/Kimi, e mais Qwen, Meta Muse, StepFun e Mistral como varredura.
> OpenAI/Anthropic/Google entram **só** como comparação na tabela de benchmarks (os preços e termos deles são do outro pesquisador).

## 0. Método e fidelidade das fontes

| fonte | como foi lida | fidelidade |
|---|---|---|
| Artificial Analysis (AA) | 📊 `curl` do HTML das páginas `artificialanalysis.ai/evaluations/*`, `/leaderboards/models` e `/models/*` em 23/09/2026. O JSON embutido (Next.js) foi extraído com um parser Python (`models.json`, 673 modelos) | **alta**: são os números crus que o site plota. Índice = *Intelligence Index v4.3.2* |
| LiveBench | 📊 `curl https://livebench.ai/table_2026_06_25.csv` + `categories_2026_06_25.json` (o release ativo do site, que recebe modelos novos continuamente). A média por categoria e a média global foram **calculadas por mim**: média simples das tarefas, depois média das 7 categorias | alta nos números por tarefa. A média global é minha e pode diferir 0,1–0,5 do que o site mostra |
| OpenRouter | 📊 API pública: `/api/v1/models`, `/api/v1/models/{id}/endpoints`, `/api/v1/endpoints/zdr`, `/api/frontend/v1/all-providers` | alta. Preço, uptime e flags de ZDR/treino **por provedor**, lidos em 23/09/2026 |
| docs oficiais (x.ai, mimo.mi.com, api-docs.deepseek.com, docs.z.ai, platform.kimi.ai, AWS) | WebFetch (resumo feito por um LLM). Os docs do MiMo vieram em `.md` cru via `llms.txt` | média-alta. Tudo que é crítico foi pedido **verbatim** |
| GitHub/HN | WebFetch da issue | média: o status e a data vêm da página |

⚠️ Um alerta sobre a ferramenta: o WebFetch de páginas renderizadas por JavaScript (livebench.ai, mimo.mi.com/privacy) **inventou conteúdo** ao ecoar o meu prompt. Descartei esses resultados e fui aos dados crus. Duas datas também descartei: o HuggingFace do GLM-5.3-Flash mostrou "17/02/2026" e o thread do HN apareceu como "janeiro de 2025". Nenhuma das duas é confiável.

---

## 1. A proposta afirmou X → veredito

| # | afirmação da proposta | veredito | evidência (URL · data da leitura 23/09/2026) |
|---|---|---|---|
| 1 | Grok 4.7 lançado em 21/09/2026 | **CONFIRMADO** | x.ai/news/grok-4-7 ("Sep 21, 2026"); AA `releaseDate 2026-09-21` |
| 2 | id `grok-4.7` | **CONFIRMADO** | docs.x.ai/developers/grok-4-7 · docs.x.ai/developers/release-notes |
| 3 | contexto de 500K | **CONFIRMADO** | mesmas páginas ("500,000 tokens") |
| 4 | text/image | **CONFIRMADO**: entra texto e imagem, sai só texto | docs.x.ai/developers/grok-4-7 |
| 5 | reasoning low/medium/high/xhigh | **CONFIRMADO**. O default é `high` | release-notes |
| 6 | Responses API | **CONFIRMADO**, e Chat Completions também. Nuance: no Responses ele **sempre** devolve `reasoning.encrypted_content`, "even when `include` does not list it" | release-notes |
| 7 | US$2 in / 0,50 cached / 6 out (<200K); 4/1/12 acima de 200K | **CONFIRMADO** | release-notes. Nuances: (a) o endpoint regional US `https://us.api.x.ai/v1` custa **+10%**; (b) 📊 o OpenRouter cobrava **1,60/0,40/4,80** (20% abaixo da lista) em 22–23/09 (openrouter.ai/api/v1/models; tbreak.com) |
| 8 | MiMo V2.6 Pro: cache hit 0,0036 · input 0,435 · output 0,87 | **CONFIRMADO** (em USD, preço "overseas") | mimo.mi.com/models/en-US/mimo-v2.6-pro · batch-api.md |
| 9 | MiMo V2.6 Pro: 1M ctx, 128K de saída | **CONFIRMADO** | mesma página |
| 10 | deep thinking, tool call, structured output, web search, context caching | **CONFIRMADO** como a página lista. ⚠️ Há duas ressalvas **críticas**, na §3: `tool_choice` ≠ `auto` é descartado, e o esforço de raciocínio não é diferenciado | mimo.mi.com/static/docs/api/chat/openai-api.md · responses.md |
| 11 | batch 50% | **CONFIRMADO**. O batch Pro custa 0,0018/0,2175/0,435, com janela fixa de 24h, e vale só para v2.6-pro e v2.6-flash | mimo.mi.com/static/docs/quick-start/usage-guide/text-generation/batch-api.md |
| 12 | MiMo V2.6 Flash 0,14/0,28 | **CONFIRMADO** (cache hit 0,0028) | batch-api.md · OpenRouter `xiaomi/mimo-v2.6-flash` |
| 13 | MiMo V2.6 Pro UltraSpeed 4,35/8,70, "até 20x" | **CONFIRMADO**. O preço vem do OpenRouter (`xiaomi/mimo-v2.6-pro-ultraspeed`, cache 0,036); o "até 20x" é **alegação do fabricante**; o rate limit é só por contrato ("contact us") | OpenRouter API; mimo.mi.com/docs/en-US/news/latest/v2-6; rate-limit.md |
| 14 | DeepSeek V4.1 Flash, setembro/2026, native multimodal, API `deepseek-flash` | **CONFIRMADO**: lançado em 10/09/2026, com entrada de imagem | deepseek.com/en/news/deepseek-v4-1-flash/ · api-docs.deepseek.com/updates |
| 15 | "V4-Pro encaminhado **temporariamente** para V4.1-Flash" | **REFUTADO/DESATUALIZADO**. O post dizia *"We're phasing out V4-Pro… Starting Sept 14, all deepseek-v4-pro requests will route to V4.1-Flash"*. O changelog de 10/09 **reverteu** isso: *"we have decided to continue providing API services for DeepSeek V4 Pro after September 14, 2026, with the billing method remaining unchanged."* O que ficou "temporariamente" roteado para o V4.1-Flash são os **aliases** `deepseek-v4-flash` e `deepseek-v4-flash-vision-exp` | api-docs.deepseek.com/updates · news post |
| 16 | peak/off-peak 50%; "preço não verificado" | **CONFIRMADO + agora VERIFICADO**. `deepseek-flash`: cache hit 0,006/0,003 · miss **0,30/0,15** · output **1,20/0,60** (peak/off-peak). O pico é 01–04h e 06–10h UTC, de segunda a sexta. 💡 Em horário de Brasília o pico cai em **22h–01h e 03h–07h**, então o **horário comercial brasileiro inteiro é off-peak** | api-docs.deepseek.com/quick_start/pricing |
| 17 | GLM 5.3 (max): AA Intelligence Index 45 | **CONFIRMADO**: 📊 44,78 → 45, #2/114 na classe | artificialanalysis.ai/models/glm-5-3 |
| 18 | GLM 5.3: US$1,40/4,40, 1M ctx, 753B/40B, text-only | **CONFIRMADO** (cached 0,26; saída máxima de 128K) | AA · docs.z.ai/guides/overview/pricing · docs.z.ai/guides/llm/glm-5.3 |
| 19 | GLM-5.3-Flash **lançado em 23/09/2026** | **REFUTADO**. O lançamento foi em **26/08/2026**: AA `releaseDate 2026-08-26`, OpenRouter `created 2026-08-26`, codersera/eesel. Datado de 23/09 está só o post do blog AutoClaw | AA · OpenRouter API · autoclaw.z.ai/blog/model/glm-5.3-flash/ |
| 20 | GLM-5.3-Flash multimodal/agentic, 320B/18B | **CONFIRMADO**. Preço de lista **0,15/0,03/0,50**; a promoção de 50% acabou em 09/09. Pesos abertos sob MIT | docs.z.ai pricing · huggingface.co/zai-org/GLM-5.3-Flash |
| 21 | Kimi K3 no "agent council" | **EXISTE e está atual**: `kimi-k3`, lançado em 16/07/2026, **US$3 / 0,30 cached / 15**, 1.048.576 ctx, raciocínio sempre ligado (low/high/max, default max). No Bedrock desde 18/09/2026 | platform.kimi.ai/docs/pricing/chat-k3 · AWS model card |
| 22 | Grok 4.5 no "agent council" | **DESATUALIZADO**. É de 08/07/2026; foi superado pelo 4.6 (12/08) e pelo 4.7 (21/09). 📊 AA II: 4.5 = 38,8 · 4.6 = 44,3 · 4.7 = 46,4 | AA models.json |

---

## 2. Matriz por modelo (API nativa)

Todos os preços são 📊 em USD por 1M tokens, lidos em 23/09/2026.

| | **Grok 4.7** | **MiMo-V2.6-Pro** | **MiMo-V2.6-Flash** | **DeepSeek V4.1 Flash** | **GLM-5.3** | **GLM-5.3-Flash** | **Kimi K3** |
|---|---|---|---|---|---|---|---|
| model ID | `grok-4.7` | `mimo-v2.6-pro` (e `-ultraspeed`) | `mimo-v2.6-flash` | `deepseek-flash` (aliases antigos → V4.1) | `glm-5.3` | `glm-5.3-flash` (e `glm-5.3-flashx`) | `kimi-k3` |
| status | GA desde 21/09 | GA desde 21–22/09 | GA desde 21–22/09 | GA desde 10/09; **V4-Pro continua** | GA desde 18/08 | GA desde 26/08 | GA desde 16/07 |
| input / cached / output | 2 / 0,50 / 6 (<200K); 4 / 1 / 12 (>200K) | 0,435 / 0,0036 / 0,87 | 0,14 / 0,0028 / 0,28 | peak 0,30 / 0,006 / 1,20 · off-peak 0,15 / 0,003 / 0,60 | 1,40 / 0,26 / 4,40 | 0,15 / 0,03 / 0,50 (FlashX 0,37/0,075/1,25) | 3 / 0,30 / 15 (cache write 5 min US$3, 1h US$6) |
| batch / desconto | ZDR desliga o batch | **50%** | **50%** | off-peak 50% | OpenRouter `:batch` 0,72/2,40 | OpenRouter `:batch` 0,06/0,20 | OpenRouter `:batch` 2,28/11,40 |
| contexto / saída máx. | 500K / "no text output limit" (OpenRouter: 450K) | 1M / 128K | 1M / 128K | 1M / **384K** | 1M / 128K | 1M / 128K (OpenRouter até 943K) | 1.048.576 / não publicado |
| raciocínio · parâmetro | `reasoning.effort` low/medium/**high**/xhigh | `thinking` ou `reasoning.effort`, mas **sem nível**: `none` desliga e todo o resto liga igual | idem | `thinking:{type}` + `reasoning_effort` low/**high**/max (medium e xhigh são mapeados) | **sempre ligado**, não desliga (erro 1210); low/high/**max** | `reasoning_effort` low/high/max | **sempre ligado**; low/high/**max** |
| tools · paralelo · strict | sim · paralelo por padrão · até 350 tools · `tool_choice` auto/required/none/forçado · schema com raiz objeto | sim · `strict` existe · ⚠️ **`tool_choice` ≠ auto é removido pelo backend** | idem | sim · strict **só em `/beta`**, com subconjunto de JSON Schema e tudo required + `additionalProperties:false` | sim · OpenRouter anuncia `parallel_tool_calls` | sim · `parallel_tool_calls` | sim |
| structured output | sim (OpenRouter `structured_outputs`) | sim | sim | JSON output; `structured_outputs` via OpenRouter | sim | sim | sim |
| visão | imagem | imagem, vídeo, áudio | imagem, vídeo, áudio | imagem | ❌ texto apenas | imagem, vídeo, arquivo | imagem (e vídeo no nativo; no Bedrock sem vídeo) |
| OpenAI Chat Completions | sim | sim (também Anthropic) | sim | sim (também Anthropic `/anthropic`) | sim | sim | sim |
| OpenAI Responses | sim (é o preferido; encrypted reasoning) | sim, mas **sem** `background`, `previous_response_id`, `context_management` | idem | sim, "natively supports" desde 13/08 | não verificado | não verificado | no Bedrock, sim |
| rate limits | 📊 Tier 0: **150 RPS / 50M TPM**; os tiers sobem por gasto acumulado desde 01/01/2026 (US$50/250/1k/5k) | 📊 **100 RPM / 10M TPM** por conta e por modelo; UltraSpeed só por contrato | 100 RPM / 10M TPM | não publicado ("dynamic", não verificado) | não verificado | não verificado | 📊 Tier 0 (US$1): 3 RPM, concorrência 1 · Tier1 (US$10): 100 RPM · Tier5 (US$3k): 300 RPM, 5M TPM, 100 concorrentes |
| base_url | `https://api.x.ai/v1` · `https://us.api.x.ai/v1` (US, +10%) | `https://api.xiaomimimo.com/v1` | idem | `https://api.deepseek.com` (`/beta`, `/anthropic`) | `https://api.z.ai/api/paas/v4` | idem | `https://api.moonshot.ai/v1` (a doc migrou para platform.kimi.ai) |
| pesos abertos | não | sim (MIT, segundo a AA) | não verificado | sim (MIT) | sim | sim (MIT) | sim |

Fontes da matriz: docs.x.ai/developers/{grok-4-7, release-notes, tools/function-calling, rate-limits} · mimo.mi.com/models/en-US/mimo-v2.6-pro · mimo.mi.com/static/docs/{api/chat/openai-api.md, api/chat/responses.md, api/guidance/rate-limit.md, …/batch-api.md} · api-docs.deepseek.com/{quick_start/pricing, guides/tool_calls, guides/thinking_mode, updates} · docs.z.ai/guides/{overview/pricing, llm/glm-5.3} · github.com/NousResearch/hermes-agent/issues/85890 (GLM não desliga o thinking) · platform.kimi.ai/docs/{pricing/chat-k3, pricing/limits, guide/kimi-k3-quickstart} · openrouter.ai/api/v1/models.

**Disponibilidade e pagamento**: nenhum deles exige aprovação para o tier básico. O Kimi é pré-pago a partir de US$1; o xAI sobe de tier pelo gasto. **Não verifiquei** se cartão brasileiro é aceito em cada um nem se há bloqueio por região. É o primeiro teste manual a fazer.

### Varredura: outros modelos que podem ser materialmente melhores (📊 AA, 23/09/2026)

| modelo | criador | II | AutomationBench | τ³-Banking | preço in/out | custo/tarefa AA | nota |
|---|---|---|---|---|---|---|---|
| Muse Spark 1.3 (max) | Meta | **48,1** | 57,9% | **50,5%** | 1,25/4,25 | US$1,60 | fechado; 220 tok/s. API e termos **não verificados** |
| Qwen3.8 Max (0902) | Alibaba | 45,4 | 56,2% | **51,3%** (1º) | 2/6 | US$5,41 (verboso) | fechado; OpenRouter só via Alibaba (SG/CN) |
| Qwen3.8-Flash-Next | Alibaba | 39,8 | 55,9% | 45,4% | 0,15/0,47 | US$0,37 | pesos abertos (180B) |
| Step 5 Preview | StepFun | 43,7 | 51,0% | — | 1/2,7 | US$0,72 | preview |
| Mistral Medium 3.5 | Mistral | 14,2 | 6,3% | 15,1% | 1,5/7,5 | — | **não competitivo** em agentic hoje |

---

## 3. 🔴 A incompatibilidade que atravessa todos: raciocínio que precisa voltar

Todos os modelos desta lista são modelos de raciocínio. Em loop de tool calls, cada um exige, ou recomenda, que o raciocínio do turno anterior seja **devolvido** na requisição seguinte. O `ChatOpenAI` do LangChain **não faz isso** com o campo `reasoning_content`.

| provedor | o que exige | o que acontece se faltar | fonte |
|---|---|---|---|
| DeepSeek | `reasoning_content` "must be fully passed back… even for turns where the model did not perform a tool call" | **HTTP 400** | api-docs.deepseek.com/guides/thinking_mode |
| Kimi K3 | "replay the assistant message with its reasoning_content field intact" | degradação; no Bedrock via Converse, `InternalServerException` | platform.kimi.ai quickstart · AWS model card Kimi K3 |
| MiMo | "recommended to keep all previous reasoning_content" | degradação (não é erro) | mimo openai-api.md |
| Grok 4.7 | `encrypted_content` sempre vem no Responses; é preciso reenviar para manter a cadeia | depois de 2 rodadas de tools o modelo **para de raciocinar e pode entrar em loop** quando um salto via Chat Completions perde o campo | github.com/duolahypercho/codex-router/issues/888 · github.com/openclaw/openclaw/issues/126299 ("Could not decrypt the provided encrypted_content") |
| GLM-5.3 | o thinking não desliga (`disabled` dá 400, código 1210) | 400 se o adapter mandar `thinking: disabled` | hermes-agent#85890 |

📊 Situação no LangChain (lida em 23/09/2026): `langchain-ai/langchain#40219`, **aberta** em 05/09/2026, PR #40254 ainda não mesclado: *"_get_request_payload drops reasoning_content… causing 400 errors on tool calls"*. As anteriores, #37390 (fechada) e #34166, mostram que o problema **volta**. Na mesma família: `langchainjs#10883`, `n8n#29661`, `microsoft/agent-framework#5538`. → **MULTIPLE INDEPENDENT REPORTS, sem fix liberado.**

**Consequência para o AutoBrokers.** "Entrar via ChatOpenAI com base_url" **não funciona** hoje para DeepSeek com tools. Para Kimi, MiMo e Grok, funciona degradado. É preciso um adapter próprio que preserve `reasoning_content` / `encrypted_content` por mensagem, ou o OpenRouter (`reasoning_details`), com teste de loop de ≥ 3 rodadas de tools como guarda.

Outras diferenças em relação ao OpenAI:
- **MiMo**: `tool_choice` forçado é silenciosamente trocado por `auto`. Qualquer passo do corredor que dependa de "chame ESTA tool" deixa de ser garantido. Também ignora `temperature`/`top_p` no thinking (fixa 1,0/0,95).
- **DeepSeek**: `strict` só em `/beta`. No thinking, ignora `temperature` e as penalties. O Chat Completions não aceita inserir tool call no meio da conversa; o Responses e o `/anthropic` aceitam.
- **Grok**: schema de tool com raiz que não seja objeto dá 400. O Chat Completions não devolve reasoning.

---

## 4. Privacidade e LGPD por provedor (fonte oficial)

A norma de referência é a **LGPD, art. 33**, com a **Res. CD/ANPD nº 19/2024**: desde **23/08/2025**, transferência internacional por contrato só vale com as **cláusulas-padrão da ANPD** ou com cláusulas aprovadas pela ANPD (gov.br/anpd/…/resolucao-cd-anpd-no-19-de-23-de-agosto-de-2024; mayerbrown.com, 08/2025). **Nenhum** dos provedores abaixo publica cláusulas-padrão ANPD, e **nenhum** processa no Brasil.

| provedor | entidade / lei | onde processa | retenção da API | treino | ZDR / DPA | risco LGPD |
|---|---|---|---|---|---|---|
| **xAI (SpaceXAI)** | EUA | `api.x.ai` **sem garantia de região**; `us.api.x.ai` mantém inferência e retenção nos EUA (+10%) | **30 dias**, criptografado, para auditoria de abuso | "never trains on your API inputs or outputs without your explicit permission" | ZDR **só enterprise**, via vendas; desliga batch, Files e stateful. DPA no Enterprise ToS. SOC 2 Type 2; GDPR | **MÉDIO**: EUA, DPA disponível, ZDR contratável. Falta cláusula ANPD (negociar) |
| **Xiaomi MiMo** | Xiaomi Technology Netherlands B.V. + Xiaomi Technologies Singapore Pte. Ltd. | data center em **Singapura**, com transferência possível para a **Holanda** (busca na política de 25/06/2026). O OpenRouter lista datacenters SG e NL e **sede CN** | 📊 OpenRouter: `retainsPrompts: true, retentionDays: 30` | 📊 OpenRouter: `training: false`. ⚠️ **Não consegui ler o texto da política** (a página é SPA e o `.md` dá 404) | ZDR: **não** (o endpoint Xiaomi não está na lista ZDR do OpenRouter); DPA não localizado | **ALTO**: controladora CN, texto não verificado, retém 30 dias |
| **DeepSeek** | Hangzhou DeepSeek AI Co., Ltd.; **lei da RPC**, foro em Hangzhou (ToS de 22/04/2026) | *"we directly collect, process and store your Personal Data in People's Republic of China"* (Privacy Policy de 10/02/2026) | "as long as necessary" | a política prevê opt-out de treino; 📊 OpenRouter: **`training: true`, `retainsPrompts: true`** | **sem DPA**, sem ZDR. A política diz não cobrir dados de usuários finais de apps de terceiros | **BLOQUEANTE na API nativa**: China, treino, sem DPA. Viável **só via host terceiro** (§5) |
| **Z.ai (Zhipu)** | JINGSHENG HENGXING TECHNOLOGY PTE. LTD., subsidiária de Zhipu em Singapura | "generally processed in **Singapore**" | a API **"do not store any of the content… processed in real-time and not saved"** (política de 29/09/2025) | 📊 OpenRouter: `training: false, retainsPrompts: false`; o endpoint Z.AI está **na lista ZDR** | ZDR de fato pela política; DPA não localizado | **MÉDIO-ALTO**: SG com matriz CN. Houve controvérsia de "unauthorized data transmission" com o ZCode (36kr, 2026), **não verificada** (a página não carregou) |
| **Moonshot (Kimi)** | MOONSHOT AI PTE. LTD., Singapura | "secure servers located in **Singapore**" | enquanto a conta existir | ⚠️ a política (30/04/2025) diz usar "prompts, audios, images, videos, files" para "optimize our models", **sem opt-out** explícito. 📊 O OpenRouter diz `training: false, retainsPrompts: false` e põe o endpoint na lista ZDR, **provavelmente por contrato próprio do OpenRouter** | DPA não mencionado | **ALTO na API direta** (treino por padrão); **MÉDIO via OpenRouter ou Bedrock** |

Fontes: docs.x.ai/developers/faq/security · mimo.mi.com/docs/terms/privacy-policy (só a busca) · cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html · cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html · docs.z.ai/legal-agreement/privacy-policy · platform.kimi.ai/docs/agreement/userprivacy · 📊 openrouter.ai/api/frontend/v1/all-providers (`dataPolicy`) · openrouter.ai/api/v1/endpoints/zdr.

---

## 5. Nativo × hosts terceiros × OpenRouter

### 5.1 OpenRouter (docs lidas em 23/09/2026)
- **Markup**: "no markup on inference pricing". A taxa aparece na **compra de crédito: 5,5%** (mínimo US$0,80) no cartão e 5% em cripto. BYOK: 5% acima de US$25k/mês no PAYG. (openrouter.ai/docs/faq)
- **Logging**: zero por padrão. O opt-in dá 1% de desconto. "OpenRouter itself has a ZDR policy."
- **ZDR**: `provider: {"zdr": true}` por requisição, ou pela conta. Cache em memória "não conta como retenção". ⚠️ O ZDR **não cobre plugins** (web search). (openrouter.ai/docs/features/zdr)
- **Roteamento e fallback**: automático entre provedores quando um erra.
- **Responses API**: **stateless**. `store:true` e `previous_response_id` → **400**. Tem reasoning e encrypted reasoning.
- **Reasoning em loop de tools**: preserva via `reasoning` / `reasoning_details` no assistant. **Não documenta** o `reasoning_content` específico de DeepSeek, Kimi e MiMo. Teste obrigatório.
- ⚠️ **Quantização**: vários hosts servem **fp4 ou fp8**. É preciso fixar o provedor (`provider.order`, `quantizations`) para não receber um modelo degradado sem saber.

### 5.2 📊 Endpoints e ZDR por modelo (OpenRouter, 23/09/2026)

| modelo | nativo no OpenRouter | ZDR? | hosts ZDR mais baratos e sediados nos EUA | uptime do nativo (30 min) |
|---|---|---|---|---|
| Grok 4.7 | xAI 1,60/4,80 | ✅ `xai/zdr` (mesmo preço), `xai/zdr/priority` 3,20/9,60 | só a xAI | 📊 `xai/zdr` 96,2% · `xai` 91,8% (status degradado) |
| MiMo-V2.6-Pro | Xiaomi 0,435/0,87 | ❌ Xiaomi fora da lista | **DeepInfra fp8** (mesmo preço) | Xiaomi 100% · DeepInfra sem dado |
| MiMo-V2.6-Flash | Xiaomi 0,14/0,28 | ❌ | DeepInfra fp8, **80,7% (degradado)** | Xiaomi 99,9% |
| DeepSeek V4.1 Flash | DeepSeek 0,15/0,60 (tabela off-peak) | ❌ DeepSeek fora da lista | Together 0,30/1,20 · Fireworks 0,22/0,66 (**100%**) · DeepInfra fp8 0,14/0,42 · BaseTen · CoreWeave fp8 0,20/0,65 · Parasail · Modal (25+ hosts) | DeepSeek 99,98% |
| GLM-5.3 | Z.AI 1,40/4,40 | ✅ Z.AI na lista | Together/Fireworks/Parasail/Modal 1,40/4,40 · DeepInfra fp4 0,56/2,50 · Novita fp8 0,78/2,46 | Z.AI 99,85% |
| GLM-5.3-Flash | Z.AI 0,15/0,50 | ✅ | Together/Fireworks/BaseTen 0,15/0,50 · DeepInfra fp4 0,075/0,25 · CoreWeave nvfp4 | Z.AI 99,90% |
| Kimi K3 | Moonshot 3/15 | ✅ Moonshot na lista | Together/Fireworks/BaseTen 3/15 · Fireworks `us` 3,30/16,50 · DeepInfra bf16 2,85/14,25 · Relace fp4 1,95/9,75 | Moonshot 99,7% |

### 5.3 Nuvens (residência)
- **AWS Bedrock** (docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html, 23/09/2026): tem **Kimi K3** (desde 18/09/2026; 3/15, Global CRIS; US CRIS a 3,30/16,50; Chat Completions/Responses/Converse; structured outputs; prompt caching) e **Grok 4.6** (ainda **não o 4.7**; 2/6 Global, 2,20/6,60 US). DeepSeek só até **V3.2**, GLM só até **5**, **sem MiMo**. ⚠️ Em **sa-east-1 (São Paulo)** os dois só estão disponíveis via **Global cross-Region**, que "routes anywhere worldwide". **Não há inferência in-region no Brasil.** No Kimi K3 via Converse, o reasoning de turnos anteriores gera `InternalServerException` (afeta LangChain no default); a AWS recomenda Chat Completions ou Responses.
- **Vertex / Foundry**: Grok 4.6 chegou ao Vertex em 21/08 e ao Foundry em 26/08 (preview) (runtimewire.com). Grok 4.7, DeepSeek V4.1, GLM-5.3 e MiMo nessas nuvens: **não verificado**.

**Paridade de features, terceiro × nativo.** Os hosts de pesos abertos (Together, Fireworks, DeepInfra) expõem tools, structured output e reasoning via OpenAI-compatible. O **cache hit** costuma ser mais caro que no nativo: DeepSeek nativo 0,003 contra Together 0,006 e Fireworks 0,007. O **batch/off-peak nativo** não existe no host. A quantização varia.

---

## 6. Benchmarks independentes (📊 AA lido em 23/09/2026, Intelligence Index v4.3.2)

Cada modelo está na configuração de esforço **max** ou a indicada. "—" = a AA ainda não mediu. Custo/tarefa é o *cost per Intelligence Index task* da AA.

| modelo | II | AutomationBench-AA (SaaS workflows) | compl./violação | τ³-Banking (atendimento + políticas) | Terminal-Bench 4.0 | GDPval-AA (Elo) | AA-LCR (contexto longo) | Omniscience (↑ = menos alucinação) | in/out US$ | custo/tarefa | tok/s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Claude Opus 5.5 (max) | **57,6** | **69,5%** | 74,7 | — | **59,6%** | **1846** | 84,7% | **46,4** | 4/20 | 5,98 | — (xhigh 147) |
| GPT-6 Astra (max) | 52,7 | 68,5% | 69,4 | 41,4% | 59,1% | 1542 | 80,7% | 43,4 | 10/50 | 3,26 | 53 |
| GPT-6 Sol (max) | 47,5 | 61,6% | 43,9 | — | 43,9% | 1487 | 83,7% | 27,1 | 2/10 | 1,06 | 124 |
| GPT-6 Luna (max) | 37,3 | 53,2% | — | — | 12,6% | 1367 | 83,3% | 0,7 | 0,10/0,50 | **0,07** | 159 |
| Claude Sonnet 5 (max) | 38,2 | 36,5% | — | 37,3% | 14,1% | 1449 | 82,0% | 16,5 | 2/10 | 5,09 | 135 |
| Gemini 3.8 Flash (high) | 40,9 | 59,9% | 67,2 | 44,9% | 19,7% | 1412 | 81,3% | 29,6 | 0,75/3,75 | 1,24 | **291** |
| **Grok 4.7 (xhigh)** | 46,4 | 65,6% | 47,6 | — | 25,8% | 1695 | 76,7% | 32,0 | 2/6 | 3,74 | 72 (a página diz 39) |
| Grok 4.6 (high) | 44,3 | 66,7% | 63,8 | 50,7% | 21,2% | 1605 | 80,3% | 30,5 | 2/6 | 1,86 | 56 |
| Grok 4.5 (high) | 38,8 | 57,9% | — | 42,1% | 10,6% | 1370 | 79,3% | 25,3 | 2/6 | 1,04 | — |
| **MiMo-V2.6-Pro** | 46,3 | 58,6% | 41,2 | — | 34,8% | 1673 | **86,3%** | 8,4 | 0,435/0,87 | **0,13** | 64 |
| **DeepSeek V4.1 Flash (max)** | 39,5 | **68,9%** | **76,6** | — | 26,8% | 1600 | 84,0% | −5,3 | 0,30/1,20 | 0,27 | **303** |
| DeepSeek V4 Pro 0813 | 36,0 | 56,7% | — | 39,6% | 14,1% | 1441 | 80,3% | 0,8 | 1,32/3,96 | 0,67 | 87 |
| **GLM-5.3 (max)** | 44,8 | 62,2% | 54,8 | **50,3%** | 41,9% | 1646 | 79,7% | 14,3 | 1,40/4,40 | 2,01 | 74 |
| **GLM-5.3-Flash** | 41,8 | 60,4% | 47,3 | 47,2% | 32,8% | 1641 | 80,0% | 7,5 | 0,15/0,50 | 0,25 | 78 |
| **Kimi K3 (max)** | 43,6 | 58,3% | 37,9 | 46,0% | 12,6% | 1524 | **88,7%** | 19,7 | 3/15 | 2,00 | 40 |
| Qwen3.8 Max (0902) | 45,4 | 56,2% | — | **51,3%** | 38,9% | 1668 | 80,3% | 12,0 | 2/6 | 5,41 | 54 |
| Muse Spark 1.3 (max) | 48,1 | 57,9% | — | 50,5% | 33,3% | 1674 | 83,0% | 25,0 | 1,25/4,25 | 1,60 | 220 |

Fonte de todas as linhas: 📊 artificialanalysis.ai/evaluations/{automationbench-aa, tau3-banking, terminalbench-4-0, gdpval-aa, aa-briefcase} e /leaderboards/models, extraídas com curl e parser em 23/09/2026. Os arquivos estão em `scratchpad/aa/*.html` e `aa/models.json`.

Leituras que importam:
- **Tool use com usuário + política** é o que mais parece com o nosso atendimento. A AA **aposentou o τ²** (saturado: 📊 GLM-5.2 99,1%) e passou ao **τ³-Banking**. Nele, **Grok 4.7, MiMo-V2.6 e DeepSeek V4.1 Flash ainda não têm nota**. Isso é uma lacuna real.
- 📊 **OpenRouter τ²-Bench Airline** (rodado continuamente nos endpoints de produção, snapshot de 23/09/2026 06:00 UTC, openrouter.ai/benchmarks/tau2-bench-airline): Gemini 3.7 Flash 80,6 · Claude Opus 5 79,2 · DeepSeek V4 Pro 77,2 · **GLM 5.3 77,1** · **MiMo V2.6 Flash 76,6** · Grok 4.6 76,0 · **DeepSeek V4.1 Flash 75,7** · **Kimi K3 72,0** · GPT-6 Luna 66,0.
- **Verbosidade encarece.** 📊 Na AA, o Grok 4.7 gerou 240M tokens no índice ("notably slow and very verbose"); o preço de lista baixo vira US$3,74 por tarefa. O Qwen3.8 Max vira US$5,41.
- **Alucinação.** 📊 No AA-Omniscience, DeepSeek V4.1 Flash (−5,3), GLM-5.3-Flash (7,5) e MiMo (8,4) ficam muito abaixo de Opus 5.5 (46,4) e GPT-6 Astra (43,4). Para extração de memória estruturada e para responder sobre apólice, esse é o risco principal dos baratos.

### 6.1 📊 LiveBench (release 2026-06-25 com modelos acrescentados; médias calculadas por mim a partir do CSV em 23/09/2026)

| modelo | Global | Agentic Coding | IF (instruções) | Reasoning |
|---|---|---|---|---|
| Claude Opus 5.5 max | 83,2 | 71,7 | 65,7 | 92,2 |
| GPT-6 Astra max | 82,2 | 57,3 | 75,6 | 92,7 |
| **DeepSeek V4.1 Flash max** | **81,1** | **77,3** (a maior da tabela) | 70,0 | 86,7 |
| GPT-6 Sol max | 79,2 | 52,9 | 68,6 | 88,7 |
| Kimi K3 | 79,2 | 62,2 | 71,4 | 90,7 |
| Qwen3.8 Max | 78,5 | 64,6 | 74,1 | 88,2 |
| Grok 4.7 xhigh | 77,4 | 54,0 | 75,3 | 82,7 |
| GLM-5.3 | 76,1 | 60,9 | 69,3 | 85,8 |
| Claude Sonnet 5 xhigh | 76,0 | 59,4 | 63,9 | 88,7 |
| Gemini 3.8 Flash high | 75,8 | 54,2 | **81,4** | 89,3 |
| GPT-6 Luna max | 72,0 | 51,2 | 55,9 | 81,8 |
| GLM-5.3-Flash | 71,6 | 56,8 | 52,8 | 77,6 |
| MiMo-V2.6 | **ausente** do LiveBench | | | |

### 6.2 Outros
- 📊 **Vals AI** (vals.ai/models/deepseek_deepseek-v4.1-flash, 23/09/2026): DeepSeek V4.1 Flash no Vals Index **57,86%**, #15 geral; US$0,303 por teste contra **US$6,47 do Kimi K3** (57,81%).
- **SWE-bench Verified, BFCL, OSWorld, WebArena, MCP-bench, long-horizon** para estes modelos: **não encontrei número independente e datado**. Os números de DeepSWE, Toolathlon e Terminal-Bench 2.1 nos posts de lançamento (MiMo, GLM-5.3-Flash, Grok) são **do fabricante** e ficaram fora da tabela.

---

## 7. Relatos práticos de devs (classificados)

| modelo | relato | classe | fonte · data |
|---|---|---|---|
| **MiMo-V2.6-Pro** (API nativa) | em sessão agentic com 74 tools: até **120 tool calls paralelas por turno**; repete 13× a mesma chamada inválida ignorando o erro; ignora cursor de paginação; 2× `repetition_truncation` (260–285 s cada) | REPRODUCIBLE BUG, aberto, sem resposta da Xiaomi | github.com/XiaomiMiMo/MiMo/issues/98 · aberto em 22/09/2026 |
| MiMo-V2.6-Pro/Flash | loop infinito de tool calls; turno com 2000+ chamadas repetidas até ~125K tokens de saída; `ToolCallFloodingError` com batch de 17 | MULTIPLE INDEPENDENT REPORTS | MiMo-Code #2482, #2496, #2497, #2498, #2509 |
| MiMo-V2.6-Pro | argumento de string com U+0003 corrompe tool call estruturada | REPRODUCIBLE BUG | XiaomiMiMo/MiMo#95 |
| MiMo-V2.6-Flash | tool call malformada vaza texto para o usuário | ANECDOTE (um repositório) | H4fizWasabie/theoses2#341 |
| **DeepSeek V4.1 Flash** | desde 22/09 **não devolve `tool_calls`** e vaza a marcação DSML no `content`; "100% reproducible" na janela de 22/09 10:21–10:56 UTC+8 | REPRODUCIBLE BUG, aberto, sem ack da DeepSeek | CommandCodeAI/command-code#909 · 22/09/2026 |
| DeepSeek V4.x | `reasoning_content` não devolvido → 400 no LangChain, n8n e agent-framework | MULTIPLE INDEPENDENT REPORTS; o fix LangChain não saiu (#40219 aberto) | langchain#40219 (05/09/2026), #37390, #34166; n8n#29661 |
| DeepSeek V4.1 Flash | loop por `finish_reason` "unknown" no OpenCode; hang no pi agent; loop no Hermes | MULTIPLE INDEPENDENT REPORTS (dependem do harness) | opencode-cmd-provider#211 · anomalyco/opencode#50677 · hermes-agent#86303 |
| **Grok 4.7** | perde o encrypted reasoning quando passa por um salto Chat Completions, **para de raciocinar depois de 2 rodadas de tools e pode entrar em loop** | REPRODUCIBLE BUG (de integração) | duolahypercho/codex-router#888 |
| Grok 4.6/4.7 | 400 "Could not decrypt the provided encrypted_content", 5×/dia em produção | REPRODUCIBLE (integração) | openclaw/openclaw#126299 |
| Grok 4.7 | "slower & more expensive… burn tokens"; "ultimate grandmaster of parallel tool-calls" | ANECDOTE (HN) | news.ycombinator.com/item?id=49788838 (thread do lançamento; a data da página não foi capturada com confiança) |
| Grok 4.7 | o lançamento atrasou quase 2 semanas: o RL penalizava demais o tamanho e o modelo **desistia cedo de tarefas difíceis** (segundo Musk) | OFFICIAL ACKNOWLEDGEMENT (pré-lançamento, dado como corrigido) | supergok.com/grok-4-7-delayed · bighatgroup.com (06/09/2026) |
| **GLM-5.3** | `thinking: disabled` → 400 (código 1210) | OFFICIAL (comportamento documentado) | hermes-agent#85890 |
| GLM-5.3-Flash | 400 com tool output contendo imagem, na tradução Responses→Chat | REPRODUCIBLE (proxy de terceiro) | CommandCodeAI/command-code#795 · 03/09/2026 |
| Kimi K3 | Bedrock/Converse: `InternalServerException` com reasoning de turnos anteriores, o que afeta LangChain e Strands no default | OFFICIAL ACKNOWLEDGEMENT (AWS) | AWS model card Kimi K3 |

**Deriva em 50–200 tool calls.** O único relato com esse volume é o MiMo#98 (74 tools, multi-round). Para os outros, **não encontrei** medição pública de deriva longa. Os indicadores indiretos da AA vão em direções opostas: turnos médios por tarefa no AA-Briefcase de 📊 Qwen3.8 Max 172, GLM-5.3-Flash 147, DeepSeek 109, MiMo 85, Kimi 83; completions por violação de política no AutomationBench de 📊 DeepSeek 76,6 (o melhor de todos) contra Kimi 37,9 e MiMo 41,2.

---

## 8. Os 3 melhores em custo × agentic (fonte independente)

1. **DeepSeek V4.1 Flash**. 📊 AutomationBench-AA 68,9% (**2º do mercado**, 0,6 pp atrás do Opus 5.5 max). O menor índice de violação de política (76,6 completions/violação). LiveBench Agentic Coding 77,3 (o maior). US$0,27/tarefa, 303 tok/s, off-peak durante todo o horário comercial brasileiro. **Contra:** API nativa bloqueada pela LGPD (China, treino, sem DPA); regressão de tool calls em 22/09; 400 de `reasoning_content` no LangChain; τ³-Banking ainda não medido; Omniscience −5,3. **Caminho viável:** host dos EUA com ZDR (Fireworks, Together, DeepInfra) mais um adapter de reasoning.
2. **GLM-5.3-Flash** (e o GLM-5.3 max para atendimento com política). 📊 AutomationBench 60,4%, τ³-Banking 47,2% (o GLM-5.3 max tem **50,3%**, 3º do mercado), Terminal-Bench 4.0 32,8%, OpenRouter τ² Airline 77,1 (GLM 5.3). O Flash custa US$0,25/tarefa a 0,15/0,50, é multimodal, tem pesos MIT, e o **próprio Z.AI e 20+ hosts americanos estão na lista ZDR**. **Contra:** o GLM-5.3 max é caro por tarefa (US$2,01, verboso); o Flash é fraco em IF (LiveBench 52,8); alucinação alta.
3. **MiMo-V2.6-Pro**. 📊 II 46,3, **o maior entre pesos abertos**, empatado com o Grok 4.7 por **1/28 do custo** (US$0,13 contra US$3,74/tarefa). Melhor AA-LCR da lista (86,3%). Multimodal com áudio e vídeo. **Contra:** o bug de colapso de tool use (#98) é **exatamente** o nosso perfil (dezenas de tools, multi-round); `tool_choice` forçado é ignorado; o nativo retém 30 dias e a controladora é CN; fora do nativo, o único host ZDR é a DeepInfra; τ³ não medido.

Fora do top 3, com registro:
- **Grok 4.7** tem o melhor GDPval (1695) e AutomationBench (65,6%) fora de OpenAI e Anthropic, e tem ZDR. Mas custa **US$3,74/tarefa** e é lento. Em custo e em τ³ ele **perde para o próprio Grok 4.6** (US$1,86; τ³ 50,7%), que já está no Bedrock.
- **Kimi K3** tem o melhor contexto longo (AA-LCR 88,7%), mas é o mais caro dos abertos (3/15), tem o pior Terminal-Bench (12,6%) e 37,9 completions/violação. **Não justifica** o preço.
- **Qwen3.8 Max** e **Muse Spark 1.3** (Meta) lideram o τ³-Banking (51,3% e 50,5%). Os termos de API e a privacidade deles **não foram verificados**, e vale investigar.

---

## 9. O que NÃO consegui verificar

- **O texto da política de privacidade e do acordo de usuário do MiMo**: a página é SPA, o `.md` dá 404 e o `platform.xiaomimimo.com` redireciona. Só tenho o resumo de busca (Singapura/Holanda) e as flags do OpenRouter (sem treino, retenção de 30 dias).
- **O DPA** de Xiaomi, Z.ai e Moonshot, e se **algum** provedor aceita as cláusulas-padrão ANPD.
- A controvérsia de dados do ZCode/Zhipu (a página da 36kr não carregou).
- **Rate limits** de DeepSeek e Z.ai.
- **Aceitação de cartão brasileiro** e restrição de região em cada provedor.
- Grok 4.7 em Bedrock, Vertex ou Foundry (só o 4.6 está confirmado). DeepSeek V4.1, GLM-5.3 e MiMo em Vertex ou Azure.
- Notas no **τ³-Banking** para Grok 4.7, MiMo-V2.6 e DeepSeek V4.1 Flash (a AA ainda não mediu). MiMo-V2.6-Flash na AA (sem página) e no LiveBench (ausente).
- SWE-bench Verified, BFCL, OSWorld, BrowseComp, WebArena e MCP-bench independentes e datados para estes modelos.
- Medição pública de **deriva em 50–200 tool calls**, fora o MiMo#98.
- **Se o OpenRouter devolve corretamente o `reasoning_content`** de DeepSeek, Kimi e MiMo em loop de tools. A doc não diz. Exige teste.
- O preço de 1,60/4,80 do Grok 4.7 no OpenRouter: é promoção de lançamento e **não tem data de término** publicada.
- A política de privacidade da Meta (Muse Spark), da Alibaba (Qwen) e da StepFun para API.
