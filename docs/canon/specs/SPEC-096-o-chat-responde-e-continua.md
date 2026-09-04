# SPEC-096 · O CHAT RESPONDE, MOSTRA O TRABALHO E CONTINUA — o shell de interação do AutoBrokers

> **O que ela entrega:** (1) 🔴 **o browser deixa de escolher a corretora**: hoje o `companyId`, o `userId` e o `agentId`
> do chat vêm do corpo do POST e o proxy repassa cego — qualquer sessão logada consulta o cérebro e gasta o crédito de
> QUALQUER corretora; e `/api/messages` entrega qualquer conversa a quem tiver um cookie; (2) **o chat fala tipado**: em
> vez de `{"token": …}` para tudo (inclusive "créditos insuficientes", "nenhum agente", bloqueio de segurança e
> `str(e)`), um protocolo de eventos com tipo, sequência e identidade — conteúdo é conteúdo, estágio é estágio, erro é
> erro; (3) **o corretor vê o que está acontecendo, sem teatro**: UMA linha de atividade ("Consultando a carteira…")
> que nasce do evento real da tool, nunca de um `setTimeout`, como no Claude; (4) **nada se perde**: a pergunta do
> corretor é gravada pelo servidor antes de responder (hoje é o browser, em paralelo, e pode não acontecer), o clique
> duplo não cria dois turnos, a resposta parcial sobrevive à falha e ao Stop, e o servidor termina de responder mesmo
> se o browser fechou; (5) **a conversa longa abre rápido**: as últimas 60 mensagens e "carregar anteriores" (📊 p95 =
> 129 mensagens por conversa, máximo 1.326, 71 conversas acima de 80 — hoje tudo carrega de uma vez); (6) **o relatório
> nasce dentro da conversa** como card clicável (`artifact.ready`), como os Artifacts do Claude.
>
> **v1.1 · 04/09/2026 · protocolo v11.2 + opção B (três marchas) · marcha CRÍTICO** · v1.0 + aquecimento (Opus, contexto limpo, 16 perguntas, 141 mil tokens: **nota 82 → 16 emendas E1–E16 aplicadas**; as duas afirmações falsas assinadas — p50 e `version` — foram refutadas por comando; 3 blocos de números da §1 reproduzidos) (piso da §3.2: autenticação, sessão e
> o filtro `company_id`; migration com índice) · nasce da proposta `specs-propostas/10 - SPEC-096-chat-runtime-performance-
> interaction-shell.md` (02/09, 4.096 linhas) + o research pack (92 seções) + a medição de hoje (orquestrador +
> investigador/pesquisador) + a instrução do Founder de 04/09: **"sempre que tiver dúvida de como deve ser o chat, pense em
> como é o Claude"**. A proposta é ponto de partida; o que saiu dela está na §5, com o gatilho que a faz voltar.
> Branch `feat/spec096-chat` · base `origin/main` = `e1494ab`.

---

## 0. O TESTE DO PRODUTO

> **Terça, 09:12, a dona da Resulta abre o AutoBrokers pelo celular e escreve "quantas apólices da Porto vencem em
> setembro?". A pergunta aparece na hora, com o botão de enviar virando "Parar". Meio segundo depois, uma linha discreta
> abaixo dela: "● Consultando a carteira…". Três segundos depois a linha some e a resposta começa a escorrer, e a tela
> só acompanha porque ela está no fim — se ela tivesse rolado para cima para reler, a tela ficaria parada e um botão
> "Voltar ao fim" apareceria. Ela clica "Parar" no meio: o que já veio fica, marcado "parada por você", e a pergunta não
> some. Ela aperta Enter duas vezes por engano na pergunta seguinte: UMA pergunta, UMA resposta. O Wi-Fi cai no meio da
> resposta: a tela diz "Reconectando…" e, 1,5 s depois, recarrega a conversa sozinha (o servidor terminou de gravar por A.4 — não há replay do
> vivo nesta leva, §5); a resposta INTEIRA está lá. Ela pede "gera o Pulso 360": a resposta vem com um card "Pulso 360 · 2026 · Relatório executivo · Abrir ·
> Perguntar sobre isso", e o card continua lá amanhã. Quando a corretora fica sem crédito, o que aparece não é uma
> resposta do AutoBrokers: é um aviso com cara de aviso, e nada disso entra na memória da conversa. E a conversa do
> ano passado, com 400 mensagens, abre em menos de um segundo com as 60 últimas e "carregar anteriores" no topo.
> Nada do que ela viu tem nome de tool, nó, MCP ou LangGraph. E em nenhum momento o browser dela disse ao servidor
> QUAL corretora ela é — o servidor sabe.**

⛔ Qualquer bloco que não sirva a esse parágrafo sai desta SPEC.
⛔ Nenhum estágio nasce de relógio: estágio nasce de evento do runtime (`on_tool_start`), ou não nasce.
⛔ Nenhum texto de UI (estágio, aviso, erro) entra em `messages.content`, em `last_message_preview` nem na memória.

---

## 1. 📊 O QUE A MEDIÇÃO DE HOJE ACHOU — 04/09/2026 (SQL no projeto `dcajcvlzcjbmyapmklil`, leitura da árvore em `e1494ab`)

### 1.1 · 🔴 O browser escolhe a corretora — e o proxy assina embaixo
📊 `app/dashboard/chat/page.tsx:364-378`: o POST para `/api/chat/stream` leva `companyId`, `userId` e `agentId` no corpo.
`app/api/chat/stream/route.ts:10-40`: `const body = await req.json()` → `fetch(backend/chat/stream, {body: JSON.stringify(body)})`
— **nenhuma leitura da sessão**. `middleware.ts:121-127`: `pathname.startsWith('/api/')` → `return response` antes de
qualquer validação. `backend/app/api/chat.py:293-400`: `companyId` do corpo carrega `companies.*` (`:393`), decide a
porteira de crédito (`:357`, `pode_consumir(companyId)`), monta o grafo por `company_id` + `agent_id` (`:482`) — **o
cérebro, a memória e o crédito são da corretora que o corpo disser**. O backend fica numa URL pública
(`NEXT_PUBLIC_API_URL`, `lib/backend-url.ts:21`); `/chat/stream` não exige chave interna (`grep -n "X-Internal-Key" chat.py` →
0) e as checagens de widget (domínio + limite) só rodam quando **não** há `userId` (`:432`, `if agent_data and not
chat_request.userId`) — quem manda um `userId` qualquer pula as duas. **INFERÊNCIA (a refutar no aquecimento, com um POST
real de uma sessão da AutoFleet com o `companyId` da Resulta, num turno canário):** P0 pelo teste do produto (§2): uma
corretora lê o conhecimento e gasta o crédito de outra. 📊 `grep -rn "chat/stream" app components lib public` → **um único chamador** (`page.tsx:364`); o widget usa `/api/chat` → `/chat` JSON (`app/embed/[agentId]/page.tsx:425`, `chat.py:82`) — **o BFF pode ignorar o `companyId` do corpo sem quebrar o widget.** O padrão certo já existe ao lado: `lib/auxiliaries/server.ts:31` (`resolveSessionCompany`: `activeCompanyId` validado em `company_members`, senão `users_v2.company_id` — o único helper que PROVA a filiação; 📊 nenhuma rota de chat o usa, e por isso trocar de empresa no seletor da SPEC-047 não troca o cérebro), `app/api/conversations/route.ts:21-27`
(iron-session → `userId`; `users_v2.company_id`) e `backend/app/api/work_runs.py:1-6` ("`company_id` nunca vem do cliente").

### 1.2 · 🔴 `/api/messages` entrega qualquer conversa a quem tiver um cookie
📊 `app/api/messages/route.ts:16-21` (POST) e `:93-99` (GET): `if (!userCookie && !adminCookie) → 401` — testa a
**presença** do cookie, não o dono; service role (`:26-30`); `conversation_id` do cliente; nenhum join com
`conversations.user_id`/`company_id`. IDOR autenticado: qualquer usuário de qualquer corretora lê (GET) e escreve (POST,
inclusive `role: 'assistant'`) em qualquer conversa cujo UUID conheça. RLS está ligada nas duas tabelas (📊
`pg_tables.rowsecurity = true`) e **não protege nada**: o cliente é service role (CLAUDE.md §7).

### 1.3 · Um turno, três escritores, e a pergunta pode não ser gravada
📊 `page.tsx:361`: `saveMessage(convId, 'user', …)` — **sem `await`**, em paralelo com o stream (`:364`). O backend grava
só a resposta (`chat.py:632-640`), **depois** do stream inteiro (`:608`, `full_response += token`), e só se `full_response.strip()`
(`:614`). Se o stream levanta no meio: `yield {"error": str(e)}` (`:655-657`) e a persistência **não roda** — o corretor viu
metade da resposta e o refresh mostra nada. 📊 `messages`: 12.502 `user` × 12.528 `assistant` — as duas contagens não batem, e
a diferença é a soma das duas assimetrias (resposta sem pergunta e pergunta sem resposta). **A resposta é gravada com o
`id` que o browser inventou** (`assistantMessageId`, `:636-637`); não há chave de idempotência da PERGUNTA: Enter duplo =
duas perguntas gravadas e dois streams (`animated-ai-chat.tsx:201-205` só testa `!disabled`, e `disabled` vira `true`
depois do primeiro `setIsLoading`, que é assíncrono ao segundo evento).

### 1.4 · Tudo é `{"token"}` — e o que não é resposta vira resposta
📊 `chat.py`: "Creditos insuficientes…" (`:362`), "⚠️ Nenhum agente configurado" (`:411`), "⚠️ Agente não encontrado"
(`:437`), o bloqueio do guardrail (`block_reason`, `:553`), "Erro temporário de segurança" (`:576`) — **todos** saem como
`{"token": …}`; `graph.py:1805`: a exceção vira o texto "[Erro interno no servidor…]" **dentro do stream de conteúdo**, e
por isso é gravada como resposta e vira memória (`MemoryService`, `graph.py:1770-1810`, lê `final_state.messages`). 📊
`{"error": str(e)}` (`:668`): a exceção crua vai ao browser. O único evento além do token é o heurístico
`{"type":"ucp_…` que o frontend procura **dentro do texto** com contador de chaves (`page.tsx:440-481`, 42 linhas). A
SPEC-081 (P-227/P-228) já tinha visto que um evento de progresso "contaminaria `full_response`" e escolheu o
contorno: o modelo ANUNCIA que vai consultar. **A causa é o contrato, não o modelo.**

### 1.5 · O que o runtime já emite e a tela não vê — e o que ele NÃO emite
📊 `graph.py:1663`: `astream_events(..., version="v1")`; só `on_chat_model_stream` do nó `agent` vira token e `on_chain_end` do
`agent` é o fallback — **dois eventos, mais nada**. 🔴 `on_tool_start`/`on_tool_end` **NUNCA são emitidos**: o nó `tools` não é o
`ToolNode` — `graph.py:651` é `partial(tool_node, tools=tools)` e `nodes.py:1089-1095` chama `tool._arun(...)`/`tool._run(...)`, os
métodos privados que pulam o CallbackManager (📊 `grep -c "\.ainvoke(" nodes.py` → 1, o LLM). E eventos `custom` não passam em `v1`
(docstring do `langchain_core` 1.4.9 instalado: *"Custom events will be only be surfaced with in the v2 version"*). **O estágio humano
vem de onde o runtime JÁ conta a verdade:** o `tool_call_chunk` com `name` dentro de `on_chat_model_stream` (o modelo decidiu chamar) e
`on_chain_start`/`on_chain_end` com `langgraph_node == "tools"` (a tool começou/terminou) — sem trocar o motor. 📊 38 tools declaradas
(`grep -rhn 'name: str = "' backend/app/agents/tools/*.py | wc -l`); o catálogo tool → frase está no pacote do builder. `TypingIndicator` (`page.tsx:683-686`) só aparece enquanto
a última mensagem do assistente está vazia: entre o primeiro token e o fim de uma tool de 20 s, **a tela fica muda**.

### 1.6 · A conversa inteira carrega de uma vez, e cada token re-renderiza o Markdown inteiro
📊 `app/api/conversations/route.ts:139-146`: `select('*').eq(conversation_id).order(created_at)` — sem limite.
📊 banco: 723 conversas · 25.030 mensagens · p50 = 11, **p95 = 129, máx = 1.326** mensagens por conversa (a mediana é baixa; o histórico longo é WhatsApp — 📊 663
conversas WhatsApp × 15 web nos últimos 30 dias — e o BLOCO D existe para o p95/máx, não para a mediana); 71 conversas
acima de 80; bytes por mensagem avg 60, p95 231 (a conversa de 1.326 é WhatsApp — 📊 663 conversas WhatsApp × 15 web nos
últimos 30 dias: **o histórico longo é do atendimento, e ele reaproveita a mesma rota**). `page.tsx:485-492`: um
`setMessages` por token (💭 ≈ 800 por resposta); `MessageBubble.tsx:112`: `<ReactMarkdown>` sem `memo` — o documento
inteiro re-renderiza a cada token. Índice `idx_messages_by_conversation (conversation_id, created_at)` já existe para um
cursor `(created_at, id)`. 🔴 **E o proxy joga fora o `X-Accel-Buffering: no`** que o backend manda em 7 lugares (`chat.py:344…680`):
`stream/route.ts:61-67` monta headers novos com três chaves — o ELO (§0.3) que ninguém mediu: o header existe (A), o browser não o
recebe (B). 📊 Teste que prove token-antes-do-fim: `grep -rn "X-Accel" backend/tests scripts` → 0.

### 1.7 · O que já existe e serve — nada disto se reconstrói
SSE real com `X-Accel-Buffering: no` (`chat.py:671`); `astream_events` com checkpointer Postgres e cache de grafos
(`get_or_create_graph`, `:466`); `assistantMessageId` pré-alocado (`page.tsx:347`); `?session=` na URL sobrevivendo ao
refresh (`:21-27`); Realtime para handoff humano (`:152-206`); `messages.payload` jsonb já usado como envelope do espelho
WhatsApp, com o **padrão de idempotência que a 096 copia**: `messages_espelho_sem_duplicata_uidx UNIQUE (conversation_id,
(payload->>'wa_message_id')) WHERE not null`; `WorkRunService` (`runs.py:402`, aceita `conversation_id` — 📊 4 de 3.661 runs
o têm), `WorkApprovalService.decidir` (`approvals.py:194`), `ArtifactService` (📊 `artifacts` NÃO tem coluna de conversa, e 📊 `grep -rc conversation_id` nas 6 tools de relatório/pesquisa/auxiliar → 0:
**nenhuma tool sabe em que conversa está** — o `tool_node` injeta só `agent_id`, `user_id`, `session_id` (4 tools) e `company_id`,
`nodes.py:975-1042`), `listar_entregas` (094.1) e o link
autenticado do detalhe (095); Redis async (`core/redis.py:47`) e Redis Streams já em uso (`work/queue.py:56`); a chave
interna BFF→backend `X-Internal-Key` (`work_runs.py:26`, `artifacts.py:26`); `showAgentSelector={false}` (`page.tsx:653`);
o gancho `?pergunta=` da 095 (`:40-46`, `:317`). Guardas vivos que tocam o chat: os da 095 ([13]–[16] executam
`page.tsx` com o shim de React); `entregas-tudo-abre`/`entregas-mostra-o-historico` (aceitam `useSearchParams`);
`test_corretora_configura_e_o_chat_executa.py` (o chat executa Auxiliar pelo MESMO motor); os de atendimento que leem
`messages` pelo espelho.

### 1.8 · O que a proposta valia para este escopo
📊 A proposta (02/09, 4.096 linhas, 29 seções) acerta o diagnóstico (§3 blockers, §13-§17 do pack: `full_response`) e
propõe **três tabelas novas** (`chat_turns`, `chat_turn_refs`, replay em Redis), quatro rotas novas, três classes de
interação, um catálogo de 21 tipos de evento e 18 Golden Conversations. Nota do orquestrador para ela neste escopo:
**62/100** — o diagnóstico é o certo e o remédio tem o dobro do tamanho: 📊 `work_runs.conversation_id` está preenchido em
4/3.661 e `approval_requests` do chat são `metric.proposal` (1 pendente até hoje, de teste) — cards de Work/Approval no
chat seriam projeção de algo que não acontece; o turno cabe no `payload` da mensagem (o padrão do WhatsApp) sem tabela
nova; e replay por Redis é a resposta certa para um problema que a persistência-até-o-fim (A.3) resolve por menos.

---

## 2. AS REGRAS QUE ESTA SPEC FIXA

```
R1  IDENTIDADE  o BFF deriva userId e companyId da sessão iron-session (o helper canônico da §1.1); o corpo NÃO tem voz.
                O backend honra `userId` SÓ com `X-Internal-Key` válida (modo painel); sem chave = modo widget
                (userId forçado a None → domínio + limite, como hoje). Nunca os dois modos na mesma requisição.
R2  DONO        toda leitura/escrita de `messages` pelo BFF passa por `conversations.user_id = sessão` (usuário) ou por
                sessão ADMIN validada (não a presença do cookie). Conversa de outro dono = 404, nunca 403 com pista.
R3  UM TURNO    `client_request_id` (uuid do browser, um por envio) grava-se em `messages.payload` da PERGUNTA; índice
                único parcial por (conversation_id, client_request_id); repetição = MESMA pergunta, NOVA tentativa de
                resposta — nunca segunda pergunta. O servidor grava a pergunta ANTES de responder.
R4  TIPADO      o painel recebe `autobrokers.interaction.v1`: {protocol, seq, type, turn, payload}. Tipos v1:
                turn.accepted · stage.started · stage.completed · assistant.content.delta · assistant.content.completed ·
                artifact.ready · policy.blocked · notice · error · turn.completed · heartbeat. O widget continua no legado.
R5  CONTEÚDO    só `assistant.content.*` entra em `messages.content`. Estágio, aviso, erro: nunca. `policy.blocked`/`notice`
                não criam mensagem do assistente (📊 hoje criam, e viram memória).
R6  ESTÁGIO     nasce de `on_tool_start`/`on_tool_end` via CATÁLOGO (tool → frase da corretora, sem nome técnico); tool fora
                do catálogo → "Trabalhando nisso…"; NUNCA de setTimeout; payload do estágio = {key, label} e mais nada.
R7  ERRO        `error` = {code, correlation_id, message_human}; a exceção crua só no log do servidor. Códigos v1:
                model · tool · retrieval · transport · policy · billing · unknown.
R8  ATÉ O FIM   a geração corre numa task própria; o browser fechar/parar não cancela a geração nem a persistência.
                "Parar" é um POST explícito que cancela a task DESTE processo e grava o parcial com status `interrupted`.
R9  PARCIAL     toda falha depois do 1º token grava o que veio, com `payload.turn.status` = interrupted|failed e o code.
R10 HISTÓRICO   a conversa abre com as últimas 60 mensagens + `has_more` + cursor (created_at, id); "carregar anteriores"
                pagina por cursor, nunca OFFSET; a posição de rolagem não pula.
R11 TELA        uma linha de atividade por vez; autoscroll só perto do fim; deltas coalescidos por frame; `MessageBubble`
                memoizado; `showAgentSelector={false}` é invariante; nada de nome técnico na UI (UX-001).
R12 VOZ/WIDGET  `sendVoiceToN8N` e `/api/chat` (widget) NÃO mudam de contrato; a voz passa a derivar a corretora da sessão
                (📊 hoje `body.companyId || session.companyId`: o corpo vence).
```

---

## 3. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS (§7.3 · reaberto em 04/09/2026 pelo pesquisador)

**1 · Claude.ai — a régua do Founder ("na dúvida, olhe como o Claude faz")**
- `https://support.claude.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them` (📊 URL **mudou**: `support.anthropic.com` devolve **301** para `support.claude.com`; aberto em 04/09/2026) + `https://support.claude.com/en/articles/10684626-enabling-and-using-web-search`
- **o que ela faz:** (a) a pergunta aparece na hora, já ancorada; (b) **uma única linha de atividade** — 📊 o doc de web search diz *"You'll see an indicator that Claude is searching the web"*, no singular, e não uma árvore de tools; (c) **Stop** encerra e **preserva o parcial** — 🔎 OBSERVADO na tela, sem doc público; (d) Artifact como **cartão clicável ao lado da conversa** — 📊 *"a dedicated window to the right of the main chat"*, com *"Switch between different versions using the version selector"*; (e) erro com **Retry** sem apagar a pergunta — 🔎 OBSERVADO na tela; (f) autoscroll que **não puxa** quando o usuário rolou para cima — 🔎 OBSERVADO na tela.
- **MODELAMOS:** **uma linha de atividade por turno** (verbo + objeto), nunca a árvore de execução.
- **REJEITAMOS:** copiar o Artifact como *janela* fixa — nosso Artifact é entidade de 1ª classe do Hub (SPEC-057), com dono e tenant; janela é render, não modelo.
- **COMO O JUIZ INSPECIONA:** abre `claude.ai`, manda uma pergunta com busca, aperta Stop no meio, e compara com a nossa tela — o parcial ficou? o Retry manteve a pergunta? a linha era uma só?

**2 · OpenAI Responses — streaming semântico**
- `https://developers.openai.com/api/reference/resources/responses/streaming-events` (📊 endereço novo; `platform.openai.com/docs/api-reference/responses-streaming/` devolveu **403** em 04/09/2026)
- **o que ela faz:** cada evento carrega `type`, `item_id`, `output_index`, `sequence_number` — 💭 ex.: `{"type":"response.output_text.delta","item_id":"msg_123","sequence_number":1}`.
- **MODELAMOS:** **`seq` monotônico por turno** — é o que torna replay e dedupe possíveis.
- **REJEITAMOS:** os nomes de evento da OpenAI; nosso protocolo é versionado e próprio, sem acoplar provedor.
- **COMO O JUIZ INSPECIONA:** abre a página, confere os três campos, e roda um turno nosso pedindo os `seq` — têm de ser 1..n sem buraco.

**3 · LangGraph event streaming — projeção tipada**
- `https://docs.langchain.com/oss/python/langgraph/event-streaming` (aberto em 04/09/2026)
- **o que ela faz:** 📊 canais `messages` / `values` / `subgraphs` / `interrupts` / `extensions`, com eventos `content-block-delta`, `tool-started`, `tool-finished`, `tool-error`, `interrupted` — `version="v3"`.
- **MODELAMOS:** o **projetor de interação**: um fluxo bruto → projeções tipadas que a UI entende.
- **REJEITAMOS:** vazar `tool-started` cru para o cliente — o corretor vê estágio humano, não ferramenta.
- **COMO O JUIZ INSPECIONA:** compara a lista de eventos do doc com o nosso enum; nenhum `name` de tool pode aparecer no payload que sai do BFF.

**4 · LangGraph streaming (`stream_mode` / `custom`)**
- `https://docs.langchain.com/oss/python/langgraph/streaming` (aberto em 04/09/2026)
- **o que ela faz:** 📊 modos `values updates messages custom checkpoints tasks debug`; `get_stream_writer` emite dado próprio. ⚠️ **mudou desde 02/09:** exige **LangGraph ≥ 1.1** e recomenda event streaming para app novo — 📊 nosso `requirements.txt` pina **`langgraph==1.0.3`**.
- **MODELAMOS:** o `custom` writer como **único** canal de estágio de negócio.
- **REJEITAMOS:** `debug` e `tasks` no caminho de produção — ruído caro e vazamento de arquitetura.
- **COMO O JUIZ INSPECIONA:** abre o doc, confere a versão instalada, e confirma que o `version=` do `astream_events` é **`"v1"`** e que o estágio NÃO depende de `custom` (que em v1 não aparece) — ele sai das `tool_calls`/`tool_call_chunk`, medidos no BLOCO 0.4.

**5 · Vercel AI SDK — `UIMessage.parts` + resumable streams**
- `https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-tool-usage` · `https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-resume-streams` (ambos abertos em 04/09/2026, v7)
- **o que ela faz:** 📊 estados de parte `input-streaming | input-available | output-available | output-error` e, **novo desde 02/09**, `approval-requested | approval-responded | output-denied`; o resume exige stream ID ativo, Redis e endpoint **GET**.
- **MODELAMOS:** o **PADRÃO** — mensagem como lista de partes tipadas, nunca string parseada.
- **REJEITAMOS:** a dependência: o SDK não vira autoridade de runtime; implementamos nativo sobre o Redis que já temos (`backend/app/core/redis.py`).
- **COMO O JUIZ INSPECIONA:** abre a página de tool usage e confere se a nossa mensagem tem `parts[]` com estado — `grep` por parsing de string no bubble reprova.

**6 · MDN Server-Sent Events — `id:` e reconexão**
- `https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events` (📊 last-modified **03/09/2026**)
- **o que ela faz:** 📊 campos `event: data: id: retry:`; *"The event ID to set the EventSource object's last event ID value"*; *"By default, if the connection between the client and server closes, the connection is restarted."*
- **MODELAMOS:** **cursor de retomada** — o cliente diz o último `id` visto e recebe só o que falta.
- **REJEITAMOS:** `EventSource` nativo — nosso turno é POST autenticado; usamos fetch-stream com cursor equivalente.
- **COMO O JUIZ INSPECIONA:** derruba a rede no meio de um turno, reconecta, e confere que não houve texto duplicado nem buraco.

**7 · Nielsen Norman — os três limites**
- `https://www.nngroup.com/articles/response-times-3-important-limits/` (Jakob Nielsen, 01/01/1993; aberto em 04/09/2026)
- **o que ela faz:** 📊 0,1 s *"reacting instantaneously"*; 1,0 s *"the user's flow of thought to stay uninterrupted"*; 10 s *"the limit for keeping the user's attention"*.
- **MODELAMOS:** **eco local em ≤ 0,1 s** e primeira evidência de trabalho antes de 1 s.
- **REJEITAMOS:** usar os limites como roteador de trabalho — 10 s não decide chat vs. Work Run; a natureza da tarefa decide.
- **COMO O JUIZ INSPECIONA:** cronometra do Enter até a bolha aparecer, com rede lenta simulada.

**O QUE ENVELHECEU DESDE 02/09** — 📊 três mudanças reais: (1) `support.anthropic.com` → `support.claude.com` (301 permanente); (2) `platform.openai.com/docs/api-reference/responses-streaming/` devolve **403**, trocado pelo espelho vivo `developers.openai.com`; (3) o LangGraph promoveu o *event streaming* a API recomendada (`version="v3"`, exige ≥1.1) e marcou o dict-access do `stream_mode` como deprecated — por isso o event-streaming subiu para #3 e o `stream_mode` caiu para #4. **Retirado:** Starlette/FastAPI da lista opcional — `www.starlette.io` não resolveu DNS em 04/09 (ENOTFOUND); a medição do §1.7 foi feita no **código instalado**, não na doc. **Acrescentado:** os estados `approval-requested`/`output-denied` do AI SDK, que encaixam no nosso cartão de aprovação.

📊 Reaberto pelo pesquisador em 04/09/2026 (Opus, 125 mil tokens): três referências envelheceram desde 02/09 (URLs da Anthropic e da OpenAI mudaram; o LangGraph promoveu o event streaming a API recomendada, com `version="v3"` e LangGraph ≥ 1.1 — 📊 o repositório pina `langgraph==1.0.3`, e esta SPEC NÃO sobe o motor).

---

## 4. OS BLOCOS

### BLOCO 0 · Gate zero e a prova viva do P0 (antes de qualquer código)
- **0.1** os guardas novos (§BLOCO G) ficam VERMELHOS numa cópia limpa de `e1494ab` pelos itens: (i) o BFF do stream repassa o
  `companyId` do corpo · (ii) `/api/messages` não confere o dono · (iii) o backend honra `userId` sem chave interna · (iv) crédito
  insuficiente sai como `token` · (v) exceção crua no stream · (vi) pergunta gravada pelo browser sem `await` · (vii) sem
  `client_request_id` · (viii) conversa carrega sem limite · (ix) `on_tool_start` ignorado · (x) parcial descartado na falha.
- **0.2** 📊 a prova do P0 por script, custo ZERO de modelo e nada gravado (E1): POST `{backend}/chat/stream {companyId:<Resulta>,
  agentId:<uuid inexistente>, sessionId:<novo>, chatInput:"x"}` → 200 SSE "⚠️ Agente não encontrado" (`:437`) = a Resulta FOI
  carregada (`:393` passou); CONTROLE: mesmo POST com `companyId:<uuid inexistente>` → 404 "Company not found". O par 200×404 é a
  diferença que **só** o `companyId` do corpo produz, e o `agentId` inexistente aborta antes do grafo (o INSERT em `messages` é `:644`,
  só com `full_response.strip()`): nenhum token de modelo, nenhuma linha gravada. Depois da SPEC, o mesmo POST (sem chave interna) devolve 401 — é a linha de controle do E.2.
- **0.3** 📊 TTFT/TTFSE/T_COMPLETE de 3 perguntas (Q1 saudação · Q2 factual da carteira · Q3 pede o Pulso) medidos ANTES,
  pelo mesmo script (um POST de modelo por pergunta, aceitável), para a régua "não piorou" do E.2.
- **0.4** 🔴 ANTES de escrever o BLOCO B: despejar TODO evento de `astream_events(version="v1")` num turno REAL com tool (Q3 pede o
  Pulso), imprimindo `event`, `name`, `metadata.langgraph_node` e — quando `on_chat_model_stream` — `chunk.tool_call_chunks`. O `tool_start`
  do B.2 depende de o `name` da tool aparecer num `tool_call_chunk`; isso é HIPÓTESE (E13) até esta medição. 📊 há dois provedores
  (`langchain_service.py:277,284`) e um segundo `bind_tools` (`nodes.py:560`) fora do filtro de nó — se o `name` não vier no chunk, o
  `tool_start` sai das `tool_calls` do `AIMessage` no `on_chain_end` do nó `agent` (medir qual das duas, e o builder usa a que existir).

### BLOCO S · Segurança — o piso (backend + BFF)
- **S.1** `app/api/chat/stream/route.ts`: `resolveSessionCompany()` (`lib/auxiliaries/server.ts:31`) → `{userId, companyId}` (401 sem
  sessão; é o helper que valida a filiação — e é o que faz o seletor de empresa da 047 chegar ao chat); repassa `X-Accel-Buffering: no`
  ao browser; ⚠️ (E2) a fronteira widget×painel é a ROTA, não o cookie: `/api/chat/stream` é SÓ do painel (📊 1 chamador), o widget usa
  `/api/chat` — o BFF não faz sniffing de domínio, só exige sessão; corpo aceito:
  `chatInput, sessionId, client_request_id, imageUrl, fileUrl, fileName, options, assistantMessageId`; `companyId/userId/agentId`
  do corpo são IGNORADOS (agent: o da conversa, ou o primeiro ativo da corretora — como o frontend faz hoje, mas no servidor);
  cabeçalho `X-Internal-Key` no fetch ao backend.
- **S.2** `backend/app/api/chat.py` `/chat/stream` e `/chat`: `_modo_de_confianca(request)` → `painel` (chave válida: honra
  `userId`, ABIS) | `widget` (sem chave: `userId=None`, checagens de widget, legado `{"token"}`). Sem chave + `userId` no corpo
  → o `userId` é descartado e o log registra `trust=widget_dropped_user`.
- **S.3** `app/api/messages/route.ts`: GET/POST derivam o dono (R2); POST aceita `role` só `user` (a resposta é do backend) e passa
  a ser usado só pela voz; GET ganha `before=`/`limit=` (BLOCO D).
- **S.4** `app/api/n8n/route.ts`: `session.companyId` vence; sem sessão → 401 (R12).
- **S.5** `DELETE /session` (`chat.py:689`) não é tocado; o fail-open vira P-096-SESSION-FAIL-OPEN.

### BLOCO A · O turno — a pergunta é do servidor, e é uma só
- **A.1** migration `backend/supabase/migrations/20260904_01_spec096_turno_idempotente.sql`: `CREATE UNIQUE INDEX IF NOT EXISTS
  messages_turno_sem_duplicata_uidx ON messages (conversation_id, (payload->>'client_request_id')) WHERE payload->>'client_request_id'
  IS NOT NULL` — expand-first, não destrutiva, APPLY/VERIFY/ROLLBACK escritos antes.
- **A.2** o BFF (S.1) grava a pergunta (`role='user'`, `payload: {client_request_id, turn: {submitted_at}}`) ANTES do fetch ao
  backend; conflito no índice → é retentativa: reaproveita a linha e segue para a geração (R3). O frontend deixa de chamar
  `/api/messages` para texto (`page.tsx:361`).
- **A.3** o backend grava a resposta com `payload.turn = {client_request_id, status, ttft_ms, total_ms, stages: [keys], artifacts:
  [refs], error_code}`; status ∈ complete | interrupted | failed; falha depois do 1º token grava o parcial (R9).
- **A.4** a geração corre em `asyncio.create_task` alimentando uma fila; o gerador SSE lê a fila; desconexão do cliente não
  cancela a task (R8). Registro em memória `TURNOS_ATIVOS[client_request_id] = task` (referência forte, anti-GC) para o Stop (C.3); a persistência da task usa `except BaseException` (E4: `CancelledError` herda de `BaseException` e o `except Exception` de hoje não a pega).

### BLOCO B · O protocolo — o chat fala tipado
- **B.1** `backend/app/api/chat_eventos.py` (puro): `Envelope(seq, type, turn, payload)`, o CATÁLOGO DE ESTÁGIOS (tool → {key,
  label}) e `estagio_da_tool(nome)`; `erro_seguro(exc) → {code, correlation_id, message_human}`.
- **B.2** `graph.py`: `stream_agent_eventos(...)` gera dicts `{"kind": token|tool_start|tool_end|error, ...}` a partir do MESMO laço de
  `astream_events` (mantém `v1`): `tool_start{name}` no primeiro `tool_call_chunk` com `name` (ou nas `tool_calls` do `AIMessage` no
  `on_chain_end` do `agent`, o que vier antes — dedup por `tool_call id`); `tool_end` no `on_chain_end` com `langgraph_node == "tools"`.
  Nunca `on_tool_start` (📊 §1.5: não existe) e nunca `custom`. `stream_agent` vira wrapper que só deixa passar `token` (compatibilidade:
  quem hoje consome string continua igual). A troca do motor (`version="v2"`/LangGraph ≥ 1.1 com `get_stream_writer`) é P-096-MOTOR-DE-EVENTOS.
- **B.3** `chat.py` modo painel: `turn.accepted {user_message_id, assistant_message_id}` → `stage.*` → `assistant.content.delta` →
  `artifact.ready` (📊 nenhuma tool sabe a conversa e a consulta por company+origin colide — 79,7% dos títulos repetem e a
  identidade da 095 cria VERSÃO, não peça: `created_at` não muda. Então: um `ContextVar` `pecas_do_turno` em `chat_eventos.py`, setado
  pelo turno antes do grafo — `asyncio.create_task` copia o contexto e as tools rodam dentro dele — e `ArtifactService.publicar`
  registra **só o `artifact_id`** nele (📊 E5: `publicar` seleciona `id, artifact_id, version, status, brand_snapshot` em
  `artifact_versions` — não conhece `title`/`kind`, que moram em `artifacts`, e tem `return` antecipado na republicação); o turno resolve
  `title`/`kind` num SELECT em `artifacts` por esses ids ao fim, e emite um `artifact.ready` por peça) → `assistant.content.completed` →
  `turn.completed`; `heartbeat` a cada 15 s sem evento. Porteira, agente ausente, guardrail → `policy.blocked`/`notice`, SEM
  mensagem gravada (R5). Exceção → `error` (R7) + parcial gravado (R9).
- **B.4** `POST /chat/stop` `{client_request_id}` (modo painel): cancela a task deste processo → grava `interrupted` com `payload.turn.stopped_by`
  (E11: 📊 hoje 1 processo/1 worker, `backend/Dockerfile:27` sem `--workers`; o campo torna o Stop-multiprocesso visível se surgir réplica —
  P-096-STOP-MULTIPROCESSO); não achou → 404 (o browser já abortou localmente).

### BLOCO C · O shell — a tela do Claude, com a verdade do runtime
- **C.1** `lib/chat/protocolo.ts`: tipos do envelope v1, `lerEventos(stream)` (parser SSE com `seq` e detecção de lacuna →
  `transport: 'gap'`), e o estado `Turno {status: idle|submitting|streaming|stopped|complete|failed, stage, transport}` que
  substitui `isLoading`.
- **C.2** `page.tsx`: `client_request_id` por envio (uuid), sem `/api/messages`; sem heurística UCP; deltas coalescidos por
  `requestAnimationFrame`; autoscroll só a ≤ 120 px do fim + botão "Voltar ao fim"; `payload.turn.artifacts` reidrata os cards;
  o `?pergunta=` da 095 intacto; `showAgentSelector={false}` intacto.
- **C.3** `components/chat/LinhaDeAtividade.tsx` (● label…), `components/chat/CardDeRelatorio.tsx` (título, tipo humano, "Abrir",
  "Perguntar sobre isso" → `?pergunta=`), `components/chat/AvisoDoTurno.tsx` (policy/notice/error com "Tentar de novo" = mesmo
  `client_request_id`, e "parada por você"); `InputArea`: botão Enviar vira "Parar" durante `streaming` (Esc também); composer
  bloqueado só em submitting|streaming.
- **C.4** `MessageBubble` memoizado (`React.memo` por `id`+`content`); voz e imagem como hoje.

### BLOCO D · O histórico abre rápido
- **D.1** `/api/conversations?session_id=` devolve as últimas 60 (consulta `order desc limit 61` → inverte) + `has_more` + `cursor`.
- **D.2** `/api/messages?conversation_id=&before=<created_at>|<id>&limit=60` (dono conferido, S.3).
- **D.3** `page.tsx`: "Carregar anteriores" no topo; preserva `scrollHeight` antes/depois. 🔴 (E9) o `useEffect(scrollToBottom,[messages])` (`:147-149`) MORRE (ele puxa a tela a cada mensagem e brigaria com "carregar anteriores" e com R11; o scroll passa a ser condicional, C.2). (E10) o dedupe do Realtime passa a ser por `payload.client_request_id` (fallback `id`), nao por `content` (`:189-195`), senao duas perguntas iguais somem da tela.

### BLOCO E · Canário vivo e telemetria
- **E.1** `backend/scripts/canario_096.py` (`AUTOBROKERS_CANARIO=1`, Resulta): cria conversa canário (título `canario:096`), 3 turnos
  pelo backend em modo painel: Q1 "responda só OK" (TTFSE/TTFT/T_COMPLETE, eventos tipados na ordem, pergunta e resposta gravadas
  com `payload.turn`), Q2 mesmo `client_request_id` (📊 1 pergunta gravada, 2ª tentativa), Q3 consumidor abandona no 5º evento (📊
  resposta completa gravada mesmo assim); ao fim apaga as próprias linhas (mensagens + conversa canário) com VERIFY.
- **E.2** linha de controle: o POST do BLOCO 0.2 devolve 401; e a régua "não piorou": TTFT do Q1 ≤ 1,3 × o do BLOCO 0.3.

### BLOCO G · Os guardas (desenhista, antes do código)
- `scripts/o-chat-responde-e-continua.test.mjs` — EXECUTA (shim de React + dublê de Supabase que registra consultas): o BFF do
  stream (sessão → identidade; corpo ignorado; grava a pergunta antes do fetch; conflito = retentativa), `/api/messages` (dono; 404;
  `before=`), `/api/conversations` (limite 60, cursor), `/api/n8n` (sessão vence), `page.tsx` (sem `/api/messages` para texto; sem
  UCP; `client_request_id` por envio; `showAgentSelector={false}`; `?pergunta=` continua), `lerEventos` (seq, lacuna, tipos),
  `CardDeRelatorio` e `AvisoDoTurno` (renderizam; "Tentar de novo" reusa o id). Cada asserção com o PAR (`controle()`).
- `backend/tests/test_o_chat_fala_tipado.py` — com `stream_agent_eventos` dublado: ordem dos eventos; `seq` monotônica; porteira
  → `policy.blocked` sem gravar; exceção → `error` sem `str(e)` + parcial `interrupted`; catálogo (tool conhecida → label; desconhecida
  → genérico; label sem nome técnico: regex `tool|node|mcp|langgraph|qdrant|subagent`); modo de confiança (sem chave + userId →
  widget); consumidor abandona → persistência acontece; `stream_agent` legado ainda entrega só tokens; a migration tem
  APPLY/VERIFY/ROLLBACK e é `IF NOT EXISTS`; `stream_agent_eventos` emite `tool_start` a partir de um `tool_call_chunk` (dublê do grafo) e
  NUNCA a partir de relógio; `pecas_do_turno` registrado por `ArtifactService.publicar` vira `artifact.ready`. E no mjs: o BFF do stream
  repassa `X-Accel-Buffering: no` (PAR: rota-controle que monta 3 headers → vermelho).
- **MUTAÇÕES** (por cópia): header `X-Accel-Buffering` removido do BFF → [S.1]; corpo volta a vencer a sessão → [S.1]; `eq(user_id)` removido → [S.3]; chave interna ignorada → [S.2];
  `policy.blocked` volta a `token` → [B.3]; `str(e)` de volta → [B.3]; `await` removido da gravação da pergunta → [A.2]; índice
  sem `WHERE` → [A.1]; limite removido → [D.1]; `on_tool_start` ignorado → [B.2]; parcial não gravado → [A.3];
  `setTimeout` num estágio → [C.3]; `showAgentSelector={true}` → [C.2]; limiar do autoscroll 120→∞ (sempre rola) → [16] (E14).

---

## 5. O QUE SAIU DA PROPOSTA — e o gatilho que faz cada coisa voltar

| saiu | por quê (📊/💭) | volta quando |
|---|---|---|
| tabelas `chat_turns` e `chat_turn_refs` | o turno cabe em `messages.payload` com o índice do padrão WhatsApp; 💭 duas tabelas para 15 conversas web/mês | um leitor precisar consultar turnos SEM passar por mensagens (ex.: SLA por turno no Control Plane) |
| replay buffer em Redis + `after_sequence` | A.4 grava até o fim: o refresh mostra a resposta inteira; 💭 replay é para ver o parcial AO VIVO depois de reconectar | uma corretora reclamar de perder o AO VIVO em resposta longa (> 30 s) — medido, não presumido |
| Work Run Card e Approval Card no chat | 📊 4/3.661 runs com conversa; approvals do chat = `metric.proposal` de teste | a 097 (casos) ou a primeira Skill que crie Work Run do chat com `conversation_id` |
| três classes de interação (INSTANT/INTERACTIVE/DURABLE) como decisão do runtime | 📊 nada hoje promove turno a Work Run; a classe seria um rótulo sem efeito | o mesmo gatilho da linha acima |
| composer livre durante trabalho durável | depende da linha acima; V1 da própria proposta recomenda travar na geração interativa | idem |
| `T_UI_ACK`/INP como gate | 💭 não há Playwright no repositório de testes de tela; medir INP exige browser real | quando o pacote de tela ganhar Playwright (P-095-PDF cita o mesmo custo) |
| catálogo de 21 tipos de evento | 11 bastam para o que existe; `attachment.*`, `work.*`, `approval.*` sem produtor | cada um volta com o seu produtor |
| Golden Conversations G1–G18 | 3 perguntas canário + os guardas cobrem o que a SPEC muda; 18 exigem corpus sem PII que não existe | a 111 (evals) |
| virtualização da lista | a própria proposta: só com profiling; D.1 resolve o carregamento | conversa web com > 500 mensagens carregadas (📊 hoje 0) |
| upload como parte tipada (`attachment.*`) | o upload é 1 chamada antes do envio; 💭 raro no painel | quando o upload de documento virar fluxo do produto (SPEC-108 docs) |
| natural-language approval | a 055 é a autoridade e V1 da proposta já recusa | nunca por esta SPEC |
| subir o LangGraph (1.0.3 → ≥ 1.1) para `custom`/event streaming v3 | 📊 §1.5: o estágio sai das `tool_calls` sem trocar motor; subir motor é infraestrutura, não UI | P-096-MOTOR-DE-EVENTOS: quando uma tool precisar emitir progresso PRÓPRIO ("3 fontes encontradas") |

---

## 6. PENDÊNCIAS QUE NASCEM AQUI (vão para `PENDENCIAS.md` ao fechar)
P-096-SESSION-FAIL-OPEN (o `DELETE /session` fail-open, `chat.py:689`) · P-096-REPLAY-AO-VIVO (§5 linha 2) · P-096-STOP-MULTIPROCESSO
(o Stop cancela só neste processo; com 2+ réplicas da API precisa de Redis) · P-096-MEMORIA-LE-ERRO (📊 a memória já guardou
"[Erro interno…]" como resposta em conversas antigas; limpar é decisão) · P-096-VOZ-N8N (a voz ainda passa pelo n8n; SPEC-112) · P-096-MOTOR-DE-EVENTOS (§5 última linha) · P-096-COMPANY-DATA-IGNORA-ATIVA (`/api/user/company-data:40` usa `users_v2.company_id` e ignora `activeCompanyId`; depois de S.1
usar `resolveSessionCompany`, a tela do topo e o cérebro do chat podem discordar de empresa — alinhar) · P-096-ARTIFACT-SEM-CONVERSA (a peça
nasce sem `conversation_id`; o registro por ContextVar liga o turno à peça, mas a tabela continua sem o elo — a 097/098 decidem a coluna).

## 7. A CAIXA DO FOUNDER
- **Nada a decidir antes de executar.** O P0 (§1.1) é fechado sem pergunta: derivar a corretora da sessão é a regra do CLAUDE.md §7.
- **Depois:** (a) quer o replay ao vivo (§5) — custa 💭 4h; (b) o Stop em multiprocesso quando houver 2 réplicas; (c) se a memória
  das conversas antigas deve ser limpa do "[Erro interno…]".

## 8. GATE FINAL
```
gate zero: os 10 vermelhos em cópia limpa · guardas G verdes · mutações 12/12 vermelhas · npm run test:rotas-montam ·
next build · tsc --noEmit · suíte inteira (árvore parada) · canário E.1 com saída colada · linha de controle E.2 (401) ·
TTFT não piorou · nenhum nome técnico na UI (grep) · nenhum PII no relatório · red team + 2 lentes + juiz fresco ·
git push origin HEAD:main com a saída no relatório
```
