# SPEC-096 — RESEARCH PACK
## Chat Runtime Performance & Interaction Shell

**Data:** 02/09/2026  
**Repo:** `Amandico100/AutoBrokers-Intelligence-OS`  
**Baseline confirmado:** `6c410c544f4f3f6363422dd73ec33b8d2a7fe908`  
**Protocolo atual:** AutoBrokers AAA **v10**  
**SPEC associada:** `SPEC-096-chat-runtime-performance-interaction-shell.md`

---

# 1. VEREDITO

O AutoBrokers não precisa de outro chat engine.

Ele já tem:
```text
Smith
LangGraph
astream_events
Postgres checkpointer
Work Runs
Approvals
Artifacts
Redis
SSE
```

O que falta é:

# **uma projeção de interação tipada, durável onde deve ser e efêmera onde deve ser.**

Arquitetura pesquisada:

```text
RUNTIME AUTHORITIES
      ↓
INTERACTION PROJECTOR
      ↓
ABIS v1
      ↓
CHAT SHELL
```

Score:

```text
Current runtime foundation ........... 94/100
Current chat interaction contract .... 55/100
Current reconnect durability ......... 45/100
Current long-work UX ................. 50/100
Proposed interaction architecture .... 100/100
```

---

# 2. BASELINE MUDOU — PROTOCOL AAA v10

Latest repo commits em 02/09/2026 incluem:
- introdução do Protocol AAA v10;
- auditor do próprio protocolo;
- correção para a tabela de referência ficar genérica.

A 096 deve usar v10.

Não v9.

---

# 3. PROTOCOL v10 — CONSEQUÊNCIA PARA A 096

Esta SPEC toca:
- Web;
- BFF;
- FastAPI;
- Supabase;
- Redis;
- LangGraph;
- segurança;
- UI principal.

Logo:
```text
RISCO 8
SUPERFÍCIE 3
```

Protocol current exige:
- Execution Card;
- external reference artifact para UI/design;
- gates;
- context diet;
- blocker test;
- unitização;
- cohesion/parallelism decision.

---

# 4. UX-001 — CHAT-FIRST É AUTORIDADE

`docs/canon/UX-001-navegacao.md`

Regras relevantes:
- Chat-first.
- Mobile-first.
- Progressive disclosure.
- Linguagem da corretora.
- Home é AutoBrokers.
- Não expor MCP/webhook/provider/RAG/LangGraph/tool/subagent/execution engine.
- Usuário comum não deve ver seletor confuso de agentes.

Isso define a tradução de runtime para stage humano.

---

# 5. CURRENT CHAT PAGE

`app/dashboard/chat/page.tsx`

Current:
- `use client`;
- `messages`;
- `isLoading`;
- `sessionId`;
- conversation;
- agents;
- selected agent;
- web search;
- company;
- Realtime;
- streaming fetch.

Useful:
- session persisted in URL;
- optimistic message;
- assistant pre-ID;
- Realtime handoff.

Debt:
- `isLoading` global.
- composer disabled while active.
- string-based protocol.
- no typed Work/Approval/Artifact parts.

---

# 6. AGENT SELECTOR RECOMMENDATION IS ALREADY IMPLEMENTED

Current composer passes:
```tsx
showAgentSelector={false}
```

Important:
The Candidate SPEC should NOT spend effort “implementing” this.

Convert to regression test.

---

# 7. CURRENT INPUT AREA

`components/InputArea/index.tsx`

Capabilities:
- text;
- images;
- file upload;
- PDFs/DOCX/PPTX/XLSX/TXT/CSV/MD;
- voice;
- web search;
- hidden agent selector support.

Important UX issue:

```text
handleSend()
→ uploadImageToSupabase()
→ onSendMessage()
```

Therefore file upload can happen before the user bubble is submitted.

Perceived latency includes upload.

---

# 8. CURRENT VOICE PATH

`app/dashboard/chat/page.tsx` still calls:
```text
sendVoiceToN8N
```

This is a distinct legacy path.

Do not force voice architecture into 096.

SPEC-112 owns Voice.

But 096 must not break voice and should make the future typed shell compatible.

---

# 9. CURRENT MESSAGE TYPE

`lib/types.ts`

```ts
Message {
  id
  conversation_id
  role
  content
  type: 'text' | 'voice'
  audio_url
  image_url
  sender...
}
```

No:
- Work part;
- approval part;
- Artifact part;
- turn ID;
- stream lifecycle.

This supports keeping durable text simple and introducing typed refs/projections.

---

# 10. CURRENT MESSAGE BUBBLE

`components/MessageBubble.tsx`

Current UI can render:
- Markdown;
- images;
- voice;
- human sender.

No first-class:
- Work Run;
- progress;
- approval;
- Artifact;
- recoverable error.

---

# 11. CURRENT NEXT STREAM PROXY

`app/api/chat/stream/route.ts`

Behavior:
```text
request body
→ fetch backend /chat/stream
→ pass body stream through
```

Headers:
```text
text/event-stream
no-cache
keep-alive
```

No:
- semantic transform;
- stream ID;
- sequence;
- replay;
- explicit auth derivation;
- reconnect endpoint.

The proxy is simple; keep it lean but make it security/identity aware.

---

# 12. CURRENT BACKEND STREAM

`backend/app/api/chat.py`

`ChatRequest` accepts:
```text
chatInput
audioData
imageUrl
fileUrl
sessionId
companyId
userId
agentId
assistantMessageId
options
```

The streaming endpoint:
- checks conversation status;
- billing;
- agent/company;
- guardrail;
- calls `stream_agent`;
- accumulates `full_response`;
- yields `{"token": token}`;
- persists assistant after stream;
- yields `[DONE]`.

---

# 13. CENTRAL TECHNICAL DEBT: `full_response`

Current logic:
```python
full_response += token
yield {"token": token}
```

Then:
```text
messages.content = full_response
```

This is exactly why UI status events cannot safely be sent as ordinary tokens.

Anything sent as token becomes transcript.

---

# 14. CURRENT SPEC-081 HAD ALREADY FOUND THIS

SPEC-081 evaluated:
- instruct model to announce before tool;
- new tool-start SSE event;
- heartbeat.

It selected the model announcement workaround because status events would contaminate persisted `full_response`.

096 should supersede the reason for that workaround by separating event types.

---

# 15. CURRENT STREAM FAILURE BEHAVIOR

Persistence happens after `stream_agent` finishes.

If stream raises before completion:
- error event is yielded;
- partial `full_response` may have been shown;
- normal persistence block is skipped.

Potential result:
```text
user saw partial answer
refresh
partial answer gone
```

Must be reproduced.

---

# 16. CURRENT USER MESSAGE PERSISTENCE

In web streaming path, frontend calls `/api/messages` separately.

Backend streaming persists assistant, but does not own the normal user-message write for that path.

This creates:
```text
two writers
two requests
one logical turn
```

Turn authority should unify lifecycle.

---

# 17. `/api/messages` SECURITY FINDING

`app/api/messages/route.ts`

Current:
- checks whether user/admin cookie exists;
- creates service-role Supabase client;
- accepts `conversation_id`;
- reads/writes messages.

The observed route does NOT resolve:
```text
conversation → authenticated user/company
```

before access.

This is a potential authenticated IDOR.

Because service role bypasses RLS, it is a serious seam.

Warm-up MUST attempt exploit against safe test tenants.

---

# 18. MIDDLEWARE MAKES THIS MORE IMPORTANT

Current `middleware.ts` has:

```text
isApiRoute = ... || pathname.startsWith('/api/')
```

and API routes return before dashboard session validation.

Therefore individual API routes must authenticate/authorize themselves.

Middleware does not save `/api/messages`.

---

# 19. CURRENT CONVERSATIONS API IS BETTER

`app/api/conversations/route.ts`

It:
- reads iron session;
- derives user ID;
- derives company on create;
- filters conversation by `user_id` on read.

This is a better pattern to reuse.

But:
```text
session_id query
→ fetches ALL messages
```

which is a performance debt for long conversations.

---

# 20. CURRENT CHAT TENANT TRUST FINDING

Current browser POST contains:
```text
companyId
userId
agentId
```

Next stream proxy passes body to FastAPI.

FastAPI chat endpoint uses `companyId` to load company/brain context.

The observed Next middleware treats all API paths as API routes and the proxy itself has no session-to-company derivation.

Warm-up MUST prove whether deployment has another trust guard.

If not:
```text
client-authoritative companyId = P0
```

---

# 21. CURRENT LANGGRAPH FOUNDATION

`backend/app/agents/graph.py`

Already:
- StateGraph;
- async Postgres checkpointer;
- connection pool;
- graph cache;
- Capability Registry tools;
- `astream_events`.

This is a strong foundation.

---

# 22. LANGGRAPH CURRENT OFFICIAL STREAM MODES

Official docs:

```text
values
updates
messages
custom
checkpoints
tasks
debug
```

With v2, each stream part has a type.

`custom` can be emitted from tools/nodes.

This directly supports an Interaction Projector.

Source:
https://docs.langchain.com/oss/python/langgraph/streaming

---

# 23. LANGGRAPH EVENT STREAMING

Newer docs describe:
```text
one underlying event flow
→ typed projections
```

including:
- messages;
- state;
- subgraphs;
- interrupts;
- custom extensions.

This is almost exactly the desired architecture.

Source:
https://docs.langchain.com/oss/python/langgraph/event-streaming

---

# 24. LANGGRAPH INTERRUPTS

Official:
```text
interrupt()
→ checkpointer
→ wait
→ Command(resume=...)
```

Same `thread_id`.

Important warning:
the node restarts from the beginning when resumed.

Therefore:
> code before interrupt must not create an unprotected irreversible side effect.

Source:
https://docs.langchain.com/oss/python/langgraph/interrupts

---

# 25. CURRENT WORK RUN FOUNDATION

Work Run API already exposes:
```text
status
progress_percent
current_step_key
risk_level
result_summary
steps
timeline
```

Also:
- cancel;
- retry;
- approvals.

Do not create chat-specific job engine.

---

# 26. CURRENT WORK RETRY IS HIGH VALUE

Existing retry rejects active runs and retries stopped statuses while preserving completed work/attempt history.

This is exactly the correct “retry the failed unit” pattern.

Chat button should call it.

---

# 27. WORK / CONVERSATION RELATION

Current architecture includes:
```text
work_runs.conversation_id
```

Therefore Work Card can be reconstructed after reload.

Potential exact `turn_id` relation can be added via ref table only if useful.

---

# 28. APPROVAL FOUNDATION

Current Work/Vault approval infrastructure exists.

096 should surface it.

Do not create:
```text
chat_approvals
```

---

# 29. ARTIFACT FOUNDATION

Candidate SPEC-095 defines:
- Artifact;
- Version;
- Render;
- Share;
- Delivery;
- inline reference pattern.

096 consumes Artifact refs.

No Artifact subsystem duplication.

---

# 30. OPENAI RESPONSES STREAMING REFERENCE

Current OpenAI API emits typed events such as:

```text
response.output_text.delta
```

with:
```text
item_id
output_index
sequence_number
type
```

Source:
https://platform.openai.com/docs/api-reference/responses-streaming/

Principle:
```text
event type + item identity + sequence
```

is superior to:
```text
data: arbitrary string
```

---

# 31. CHATGPT WORK — STRONG PRODUCT REFERENCE

Current July 2026 OpenAI product:
- Chat = fast conversational assistance.
- Work = longer, multi-step work with finished deliverables.
- user can follow progress;
- answer questions;
- change direction;
- approve important actions.

Source:
https://help.openai.com/en/articles/20001275

This directly validates the AutoBrokers boundary:

```text
short turn
vs
durable Work Run
```

---

# 32. OPENAI APPROVAL CARD REFERENCE

Current ChatGPT apps docs:
before action runs, ChatGPT can show an approval card describing app/action and options such as deny/allow.

Source:
https://help.openai.com/en/articles/11487775

Useful principle:
> side effect approval is a structured control, not casual transcript text.

---

# 33. CLAUDE ARTIFACTS REFERENCE

Claude creates substantial reusable output in a dedicated Artifact surface.

Official docs:
- standalone substantial content;
- dedicated window;
- edit/iterate;
- version selector;
- download;
- share/customize.

Source:
https://support.anthropic.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them

AutoBrokers:
```text
chat request
→ Artifact first-class result
```

---

# 34. VERCEL AI SDK — UI PARTS REFERENCE

AI SDK `useChat` uses:
```text
UIMessage.parts
```

Tool parts have states such as:
```text
input-streaming
input-available
output-available
output-error
```

Source:
https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-tool-usage

Pattern:
> render lifecycle as typed parts, not string parsing.

Do not make AI SDK runtime authority.

---

# 35. VERCEL AI SDK — RESUME REFERENCE

Official docs:
resumable chat stream needs:
- persistent messages;
- active stream ID;
- Redis;
- POST create;
- GET resume.

Source:
https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-resume-streams

AutoBrokers already has most infrastructure.

Absorb data model; implement native.

---

# 36. VERCEL AI SDK — DISCONNECT REFERENCE

Message persistence docs explain that default streaming can abort when client disconnects; they suggest consuming stream server-side and persisting completion, or adding resumability.

Source:
https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-message-persistence

Important:
browser connection should not automatically determine durable execution truth.

---

# 37. SSE STANDARD

MDN/W3C support:
```text
event:
data:
id:
retry:
```

EventSource can reconnect using last event ID.

Sources:
https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
https://w3c.github.io/eventsource/

AutoBrokers may use equivalent cursor with fetch-stream if POST semantics make native EventSource awkward.

---

# 38. UX RESPONSE-TIME REFERENCE

Nielsen Norman’s durable rule of thumb:
- ~0.1s feels immediate;
- ~1s preserves flow;
- ~10s is near attention limit without feedback.

Source:
https://www.nngroup.com/articles/response-times-3-important-limits/

Use as UX guidance, not work router.

---

# 39. INP / WEB RESPONSIVENESS

web.dev:
good INP target:
```text
<= 200ms at p75
```

Source:
https://web.dev/articles/inp

The first local interaction should render promptly even if network/model takes longer.

---

# 40. PERPLEXITY USER LOVE — SPEED + SOURCES

Fresh Aug 2026 G2:
- 4.4/5;
- 372 reviews;
- multiple reviewers praise fast answers, clean/intuitive UI and source-backed output.

Source:
https://www.g2.com/sellers/perplexity-ai

A recent reviewer specifically describes:
> UI stays out of the way, clean answer, sources alongside, follow-ups hold context.

Product lesson:
```text
transparency can be compact
```

---


# 41. CLAUDE USER SIGNAL

Current G2 category data/reviews in 2026 broadly praise:
- ease of use;
- natural structured writing;
- deep context.

Recurring downside:
- responsiveness can feel slow;
- long answers can hinder quick communication.

Lesson:
> quality is necessary, but shell must make waiting comprehensible and keep response surface concise.

---

# 42. CHATGPT USER SIGNAL

Current G2 reviews commonly praise:
- clean/intuitive interface;
- quick responses;
- self-explanatory workflow.

Lesson:
perceived speed and low-friction interaction are core product value, not cosmetic polish.

---

# 43. WHY NOT SHOW RAW SUBAGENTS

Raw agent/tool visibility creates:
- cognitive load;
- architecture coupling;
- product terminology leakage;
- future rename debt;
- security metadata risk.

UX-001 already forbids technical language.

Use human stages.

---

# 44. HUMAN STAGE DESIGN

Strong stages are:
```text
actionable
truthful
short
stable
domain-oriented
```

Weak:
```text
Thinking harder...
Running node 7...
Calling tool...
Subagent launched...
```

---

# 45. STAGES SHOULD BE PROJECTED

Many technical events may map to one product stage.

Example:

```text
context assembler
memory lookup
InfoCap client
schema normalize
```

→
```text
Consultando a carteira
```

This decouples UX from runtime refactors.

---

# 46. PROGRESS PERCENT

Percent requires a denominator.

For deterministic workflow:
```text
5 of 8 steps
```
may justify progress.

For research/LLM:
no reliable denominator.

Prefer indeterminate stage.

---

# 47. MODEL TEXT IS NOT PROGRESS EVIDENCE

A model saying:
> “estou consultando a carteira”

does not prove a tool started.

This was acceptable as a perceived-latency workaround in 081.

096 can replace it with runtime-derived progress.

---

# 48. TURN AUTHORITY — WHY IT IS NEEDED

Current entities:
```text
conversation
message
session
```

do not model one submission lifecycle.

A durable turn adds:
- idempotency;
- user/assistant pairing;
- timing;
- stream identity;
- status;
- Work/Approval/Artifact refs;
- retry semantics.

This is not a second runtime.

---

# 49. SERVER-OWNED USER MESSAGE

Current user message is written from frontend separately.

A server accepted turn should atomically/logically own:
```text
turn
+
user message
```

This prevents:
```text
answer without persisted question
```

---

# 50. CLIENT OPTIMISM STILL MATTERS

Server authority does not mean slow UI.

Client can show:
```text
Sending…
```
immediately.

Then:
```text
Accepted
```
after server event.

Truth levels stay distinct.

---

# 51. STREAM REPLAY DESIGN

Redis is appropriate for:
- ephemeral ordered events;
- short replay window.

Postgres is appropriate for:
- turn lifecycle;
- final messages;
- durable refs.

Work DB/checkpointer is appropriate for:
- business/cognitive durability.

This storage separation mirrors the broader AutoBrokers architecture:
```text
Redis transient
Supabase truth
```

---

# 52. WHY NOT PERSIST EVERY TOKEN

Would create:
- write amplification;
- cost;
- noisy rows;
- complex compaction.

Better:
- Redis event stream;
- final/paced durable snapshot;
- final message.

---

# 53. PARTIAL RESPONSE PROBLEM

Need explicitly decide what survives if model stream fails after visible text.

Options:
1. store partial message as interrupted;
2. server continues stream to completion;
3. retry generation with same turn while preserving user message.

Never silently discard without state.

---

# 54. MESSAGE HISTORY PERFORMANCE

Current specific conversation API loads all messages.

As second-brain usage grows, this becomes:
- response size;
- DB query;
- React render;
- Markdown render;
- mobile memory.

Pagination is part of 096, not generic data optimization.

---

# 55. CURSOR HISTORY

Recommended:
```text
latest page
→ cursor older
```

Not OFFSET.

Need stable ordering with:
```text
created_at + id
```
or DB sequence.

---

# 56. AUTOSCROLL

Token stream + Work card updates can constantly move layout.

Correct:
- follow only when user near bottom;
- do not yank if reading history;
- “back to latest” affordance.

---

# 57. SCREEN READER STREAMING

`aria-live` on entire growing Markdown can be painful.

Prefer:
- concise status announcement;
- final/segment announcements;
- controls properly labelled.

Accessibility is a quality gate.

---

# 58. ATTACHMENT LATENCY

Current upload-before-send means:
```text
model TTFT may be good
user still experiences silence
```

Need timing:
```text
click
upload
server accept
first content
```

Immediate local attachment bubble fixes perception without lying.

---

# 59. ATTACHMENT RETRY

If upload succeeded but runtime failed:
do not reupload file.

Need durable/ref identity.

---

# 60. WORK RUN CARD IS A PROJECTION

Do not store duplicated `chat_job_status`.

Query/subscribe to:
- Work Run;
- Work Events;
- progress;
- approval;
- Artifact.

Card survives reload because source survives.

---

# 61. WORK RUN SHOULD RELEASE COMPOSER

Once Work is durable:
the user should not stare at disabled input until completion.

This is a major difference between chatbot thinking and operating system work.

---

# 62. MULTIPLE WORKS

If user has:
```text
Pulso 360
Cobrança
Pesquisa
```
running from same conversation, cards need IDs and titles.

No singleton `activeWork`.

---

# 63. “STOP” SEMANTICS

Three commands:
```text
stop model response
cancel Work
reject approval
```

They are not interchangeable.

---

# 64. RETRY SEMANTICS

Core rule:
```text
retry failed unit
```

Examples:
- transport → reconnect;
- submit uncertainty → same idempotency key;
- model attempt → same turn/new attempt;
- Work → Work retry;
- delivery → delivery retry.

Never default to rerun the whole prompt.

---

# 65. APPROVAL AND INTERRUPT

LangGraph interrupt model reinforces:
- durable pause;
- same thread;
- explicit input;
- resume.

But existing AutoBrokers Work Approval is authority and should coordinate the interrupt rather than be bypassed.

---

# 66. SIDE EFFECT BEFORE INTERRUPT

Because node restarts on resume, irreversible side effect before interrupt is dangerous.

Pattern:
```text
prepare
→ approval
→ effect
```

not:
```text
effect
→ approval
```

unless effect idempotent and architecture explicitly allows.

---

# 67. ARTIFACT INLINE DESIGN

Artifact Card should carry:
- title;
- type;
- version/date;
- minimal summary;
- actions.

It should not turn main message into file-management panel.

---

# 68. ASK ABOUT ARTIFACT

A structured `artifact_ref` makes:
```text
“explique este relatório”
```
precise.

No need to paste the whole Artifact back into prompt by default.

---

# 69. POLICY BLOCKS ARE NOT ASSISTANT ANSWERS

Current streaming paths can emit:
- insufficient credits;
- missing agent;
- security block

as token text.

Typed events allow:
```text
policy.blocked
notice
```

This improves:
- transcript truth;
- memory;
- UX styling;
- retry logic.

---

# 70. ERROR TAXONOMY

Recommended:
```text
transport
auth
scope
validation
policy
billing
attachment
model
retrieval
tool
work
approval
artifact
partial
human_required
unknown
```

User message must be safe/actionable.

---

# 71. RAW EXCEPTION CURRENT DEBT

Current stream error path can serialize:
```python
str(e)
```

to browser.

096 should replace with:
```text
error_code
correlation_id
safe human message
```

---

# 72. TENANT SECURITY HAS PRIORITY OVER UX

Because current message route uses service role and the new design touches it, security is not deferred.

This is an example of Protocol AAA blocker test:
changing it can alter bytes/data visible to a brokerage.

---

# 73. CHAT `companyId` TRUST NEEDS LIVE EXPLOIT TEST

Static code suggests risk.

But Candidate SPEC should label:
```text
repo-observed potential P0
```

Warm-up must test actual deployed guard path.

Do not claim breach without exploit/evidence.

---

# 74. WIDGET TRUST IS DIFFERENT

Public widget legitimately lacks user session.

It needs server-bound tenant identity.

Dashboard route should not inherit widget trust.

---

# 75. NO PROVIDER COUPLING

ABIS must not contain event types like:
```text
openai.response.delta
anthropic.content_block
```

Those are adapter inputs.

UI event:
```text
assistant.content.delta
```

---

# 76. NO LANGGRAPH COUPLING IN CLIENT

Client should not know:
```text
Pregel
node
checkpoint tuple
namespace
```

Interaction projector hides it.

---

# 77. VERSIONED INTERACTION PROTOCOL

Why:
frontend/backend deploys may not be simultaneous.

Need explicit:
```text
autobrokers.interaction.v1
```

Unsupported major version:
fail safely/fallback.

---

# 78. BACKWARD CUTOVER

Legacy stream currently works.

Best migration:
```text
same graph execution
→ legacy content projection
→ ABIS projection
```

compare final text.

Never run model twice for shadow testing.

---

# 79. LATENCY MEASUREMENT

Need timestamps from client and server.

Clock skew:
- durations within same clock preferred;
- propagate server timings;
- use `performance.now()` for browser local durations;
- trace spans for backend.

---

# 80. PERFORMANCE SOURCES

Potential bottlenecks:
- conversation fetch;
- agent/company fetch;
- graph cache;
- guardrail;
- context assembly;
- retrieval;
- provider;
- tools;
- proxy buffering;
- React state frequency.

Measure before patch.

---

# 81. GRAPH CACHE

Current code comments already emphasize graph reuse/cache.

Measure:
```text
hit
miss
build_ms
```

A UI spec should not accidentally rebuild graph every turn.

---

# 82. MODEL ANNOUNCEMENT WORKAROUND

After typed stages are proven, audit tool descriptions/prompts that force:
> “announce before calling”.

Could cause duplication:
```text
AutoBrokers: “Vou consultar...”
Activity: “Consultando...”
```

Remove only after parity and only where announcement exists solely for progress.

Natural conversational transitions can remain.

---

# 83. NO EXTRA LLM CALL FOR STAGE LABEL

Stage mapping must be deterministic/catalog-based.

Do not call model:
> “summarize what the current tool is doing for UI”.

Wasteful and can hallucinate.

---

# 84. PRODUCT-SAFE STAGE COUNT

Typical turn:
```text
0–3 visible stage changes
```
not dozens.

Long Work detail may show richer step history in Work view.

---

# 85. PERCEIVED LATENCY MODEL

User experience roughly:
```text
feedback delay
+
uncertainty
+
lack of control
```

096 attacks all three:
- immediate local feedback;
- truthful stage;
- Work/Cancel/Approval control.

---

# 86. WHY THIS CAN FEEL MUCH FASTER WITHOUT CHEATING

Suppose backend remains 8s.

Old:
```text
0–8s typing dots
```

New:
```text
0.05s message appears
0.4s accepted
1.2s “Consultando a carteira”
3s answer starts
```

Actual completion may be similar, but uncertainty is much lower.

Still measure actual performance and optimize real bottlenecks too.

---

# 87. WHAT NOT TO STEAL FROM HORIZONTAL CHATS

Do not copy:
- model picker;
- reasoning mode selector;
- raw agent tree;
- developer tool traces;
- generic artifact types irrelevant to brokerages.

AutoBrokers should feel like a brokerage operating system.

---

# 88. SPEC-097 RELATION

096 handles:
```text
interaction shell
```

097 will handle:
```text
operational case workspace
```

Do not build full Cases inside chat.

But 096 must allow Case references/cards later.

---

# 89. FUTURE EXTENSIBILITY

ABIS references can later add:
```text
case.ready
recommendation.ready
claim.updated
renewal.updated
```

without changing text message architecture.

Keep v1 tight; extension registry possible.

---

# 90. SOURCE INDEX — INTERNAL

- `docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md`
- `docs/canon/UX-001-navegacao.md`
- `docs/canon/design/2026-06-claude-design/37B2-report.md`
- `app/dashboard/chat/page.tsx`
- `components/InputArea/index.tsx`
- `components/MessageBubble.tsx`
- `lib/types.ts`
- `app/api/chat/stream/route.ts`
- `app/api/conversations/route.ts`
- `app/api/messages/route.ts`
- `middleware.ts`
- `backend/app/api/chat.py`
- `backend/app/agents/graph.py`
- `backend/app/api/work_runs.py`
- SPEC-081
- SPEC-055
- Candidate SPEC-095

---

# 91. SOURCE INDEX — EXTERNAL

## OpenAI
https://platform.openai.com/docs/api-reference/responses-streaming/
https://help.openai.com/en/articles/20001275
https://help.openai.com/en/articles/11487775
https://help.openai.com/en/articles/6825453

## LangGraph
https://docs.langchain.com/oss/python/langgraph/streaming
https://docs.langchain.com/oss/python/langgraph/event-streaming
https://docs.langchain.com/oss/python/langgraph/interrupts

## Vercel AI SDK
https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-tool-usage
https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-resume-streams
https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-message-persistence
https://ai-sdk.dev/docs/reference/ai-sdk-ui/use-chat
https://ai-sdk.dev/docs/ai-sdk-ui/transport

## Anthropic
https://support.anthropic.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them
https://support.anthropic.com/en/articles/9547008-discovering-publishing-customizing-and-sharing-artifacts

## UX/Web
https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
https://w3c.github.io/eventsource/
https://web.dev/articles/inp
https://www.nngroup.com/articles/response-times-3-important-limits/

## User validation
https://www.g2.com/sellers/perplexity-ai
https://www.g2.com/categories/ai-chatbots

---

# 92. FINAL RESEARCH CONCLUSION

The best references converge on one architecture:

```text
FAST LOCAL FEEDBACK
+
TYPED STREAM
+
DURABLE WORK
+
STRUCTURED APPROVAL
+
FIRST-CLASS OUTPUT
+
RECONNECT
+
CLEAN UI
```

AutoBrokers already has the hard backend primitives.

The biggest risk is not lack of technology.

It is connecting them through a string-based chat contract that:
- loses semantics;
- blocks the composer;
- mixes progress with content;
- weakens retry/reconnect;
- can hide security/persistence seams.

The 096 should fix that contract once, then let every future agent/Skill/Artifact benefit.

> **Do not make the runtime simpler by hiding truth. Make the interface simpler by projecting truth.**
