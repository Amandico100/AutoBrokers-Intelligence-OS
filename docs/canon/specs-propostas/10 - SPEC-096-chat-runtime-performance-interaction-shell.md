# SPEC-096 — O CHAT RESPONDE, MOSTRA O TRABALHO E CONTINUA
## Chat Runtime Performance & Interaction Shell — Streaming Semântico, Work Cards, Resume, Aprovações e Artifacts Inline

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANDIDATE SPEC — pronta para warm-up/refutação e execução segundo o Protocolo AutoBrokers AAA v10; ainda não executada  
**Data da redação:** 02/09/2026  
**Baseline de `main` observado:** `6c410c544f4f3f6363422dd73ec33b8d2a7fe908`  
**Branch sugerida:** `feat/spec096-chat-interaction-shell`  
**Origem:** evolução da Home chat-first definida em UX-001 + runtime Smith/LangGraph existente + Work OS + lacunas de progresso/reconexão observadas na SPEC-081 + Artifact/Delivery Hub da Candidate SPEC-095  
**Autoridades superiores:** SPEC-052, 053, 055, 056, 057, 059/064, 081, 085, 086, 090, 091, 093, 094, 095, UX-001, ADR-001 e `PROTOCOLO-AUTOBROKERS-AAA.md` **v10**  
**Autoridades preservadas:** Smith/LangGraph, LangGraph checkpointer, Work Run, Work Approval, Artifact, Tool Gateway, Capability Registry, Supabase, Redis, MinIO, existing channel runtimes  
**Prepara diretamente:** SPEC-097 Operations Workspace / Cases; SPEC-099 Channel Fabric; SPEC-100 Skill Factory; SPEC-109 Engine; SPEC-112 Voice  
**Research Pack:** `SPEC-096-chat-runtime-performance-interaction-shell-RESEARCH-PACK.md`

---

# LEGENDA DE VERDADE

- 🔒 **FROZEN** — decisão de produto/arquitetura.
- 📊 **MEASURED** — medido/reproduzido no repo ou em execução.
- 🔎 **REPO OBSERVED** — observado no estado atual do código.
- 🌐 **EXTERNAL** — referência externa atual.
- 💭 **HYPOTHESIS** — validar no warm-up.
- ⚠️ **DEBT** — legado que não deve ser perpetuado.
- ⛔ **BLOCKER** — precisa ficar verde antes de a unidade relacionada ser considerada pronta.

---

# 0. RESULTADO EM UMA FRASE

> **Ao enviar uma mensagem, o corretor recebe feedback imediato, vê somente o progresso que é verdadeiro e útil, pode continuar conversando enquanto trabalhos duráveis rodam, aprova ações no próprio contexto, recebe Artifacts como objetos clicáveis, volta depois de refresh/desconexão sem perder o estado e nunca dispara a mesma ação duas vezes por retry, reconexão ou clique repetido.**

```text
USUÁRIO
  ↓
ENVIA
  ↓
FEEDBACK LOCAL IMEDIATO
  ↓
TURN ACEITO PELO SERVIDOR
  ↓
AUTO BROKERS CLASSIFICA A INTERAÇÃO
  │
  ├── RESPOSTA IMEDIATA → texto em streaming
  ├── AÇÃO INTERATIVA  → estágio real → resultado
  └── TRABALHO DURÁVEL → WORK RUN
                            ↓
                     progress / approval / artifact
                            ↓
                    CHAT CONTINUA UTILIZÁVEL
```

# 0.1 BIG IDEA

A pergunta não é “como deixar o loading mais bonito?”.

É:

# **“Como fazer o chat ser a interface natural de um sistema muito mais poderoso do que um chatbot sem transformar essa complexidade em espera, poluição ou mentira?”**

# 0.2 DE ONDE VEIO

## UX-001

Já congelou:

```text
AutoBrokers = Home
Home = Chat
Chat-first
Mobile-first
Progressive disclosure
Linguagem de corretora
```

e proíbe expor ao usuário normal MCP, webhook, provider, RAG, LangGraph, tool, subagent e execution engine.

## SPEC-055

O Work OS já possui `work_runs`, `work_steps`, `work_events`, `progress_percent`, `current_step_key`, retry, cancel e approvals.

A 096 não cria “chat jobs”. Ela projeta Work Runs no chat.

## SPEC-081

Já encontrou o problema de espera percebida. Evento de progresso no SSE foi adiado porque `chat.py` faz `full_response += token` e persiste tudo como mensagem final. A 096 corrige a causa: **conteúdo durável e evento de interface têm tipos distintos**.

## SPEC-095

Artifact virou resultado versionado/entregável. A 096 recebe `artifact.ready` como referência estruturada, não URL despejada no Markdown.

# 0.3 O QUE JÁ É BOM

O chat atual já possui SSE real, streaming token a token, optimistic user message, `assistantMessageId`, sessão em `?session=`, Supabase Realtime para handoff, imagem/documento/áudio, web search, Markdown, LangGraph `astream_events`, checkpointer Postgres, Work Runs, retry/cancel, approvals, `work_runs.conversation_id` e Artifact Hub.

# 0.4 O GAP

Hoje o frontend recebe essencialmente:

```json
{"token":"..."}
```

faz `accumulatedResponse += token` e possui até heurística para detectar `{"type":"ucp_...` dentro da string parcialmente transmitida.

Isso mistura conteúdo humano e protocolo de máquina.

# 0.5 O BACKEND JÁ É MAIS RICO

LangGraph já oferece `messages`, `updates`, `custom`, `checkpoints`, `tasks` e interrupts. A solução é um **Interaction Projector**, não outro runtime.

```text
LANGGRAPH / WORK / APPROVAL / ARTIFACT
                    ↓
          INTERACTION PROJECTOR
                    ↓
      AUTOBROKERS INTERACTION STREAM v1
                    ↓
         TYPED CLIENT PROJECTIONS
```

# 0.6 PRINCÍPIO CENTRAL

# **O CHAT É A INTERACTION SHELL. ELE NÃO É A AUTORIDADE DA EXECUÇÃO.**

| Entidade | Autoridade |
|---|---|
| raciocínio | Smith + LangGraph |
| trabalho durável | Work Run |
| progresso durável | Work Steps / Events |
| aprovação | Work Approval existente |
| resultado | Artifact |
| efeito externo | Tool Gateway / Work Effect / canal |
| interface | Chat Interaction Shell |

# 0.7 TRÊS CLASSES

## `INSTANT_RESPONSE`
Resposta textual, sem efeito externo/durabilidade. Streaming normal.

## `INTERACTIVE_ACTION`
Uma/poucas capabilities, termina naturalmente no turno. Stage compacto e real.

## `DURABLE_WORK`
Elevar para Work Run quando houver múltiplas etapas, espera externa, approval, Artifact, side effect relevante, necessidade de sobreviver a reload, retry/lease ou duração indeterminada.

Não classificar só por segundos.

# 0.8 REFERÊNCIA CHAT VS WORK

O padrão atual do ChatGPT separa Chat para assistência rápida e Work para tarefas longas/multi-etapa, permitindo acompanhar progresso, responder perguntas, mudar direção e aprovar ações. AutoBrokers já tem Work OS; a adaptação é natural.

# 0.9 COMPOSER

Hoje `disabled={isLoading}` bloqueia o composer inteiro.

Depois:
- turno curto pode ter lock breve;
- quando houver `DURABLE_WORK`, após aceitação do Work Run o composer fica livre;
- novos assuntos continuam;
- instrução sobre o trabalho usa `work_run_id`.

# 0.10 AGENT SELECTOR

A recomendação já está implementada no baseline: `showAgentSelector={false}`. A 096 transforma isso em regression invariant; não reimplementa.

# 0.11 STAGES HUMANOS

Permitidos:
- Entendendo seu pedido
- Consultando a corretora
- Conferindo a apólice
- Consultando a seguradora
- Pesquisando fontes
- Conferindo documentos
- Preparando o relatório
- Aguardando sua confirmação
- Finalizando a entrega

Proibidos no tenant UI:
- Tool X
- Node Y
- MCP
- LangGraph
- Subagent
- Qdrant

# 0.12 STAGE SÓ QUANDO É VERDADE

Sem `setTimeout()` teatral. Stage nasce de graph event, Work Step, capability lifecycle, retrieval, approval ou Artifact state.

# 0.13 PROGRESS PERCENT

Mostrar percentual somente quando a autoridade Work Run possui progresso calibrado. Trabalho indeterminado mostra stage, não “37%” inventado.


# 1. ABIS v1 — AUTOBROKERS INTERACTION STREAM

Nome técnico interno. O usuário não vê a sigla.

# 1.1 OBJETIVO

Contrato provider-neutral entre runtime e interface.

OpenAI, Anthropic, LangGraph e futuro Engine podem emitir protocolos diferentes. A UI recebe vocabulário AutoBrokers.

# 1.2 ENVELOPE

```json
{
  "protocol": "autobrokers.interaction.v1",
  "event_id": "uuid",
  "sequence": 42,
  "stream_id": "uuid",
  "turn_id": "uuid",
  "conversation_id": "uuid",
  "message_id": "uuid|null",
  "work_run_id": "uuid|null",
  "type": "assistant.content.delta",
  "durability": "ephemeral|content|reference|milestone",
  "visibility": "user|internal",
  "occurred_at": "ISO-8601",
  "payload": {}
}
```

# 1.3 IDENTIDADE

Todo evento precisa de:

```text
event_id
sequence
stream_id
turn_id
conversation_id
type
```

Refs adicionais quando existirem.

# 1.4 SEQUENCE

Monotônica no stream/turn. Serve para order, dedupe, reconnect e gap detection.

Não confiar na ordem de arrival do browser como única garantia.

# 1.5 EVENT ID

Se o mesmo evento chega novamente após reconnect:

```text
already applied → ignore
```

# 1.6 DURABILITY

## `ephemeral`
UI-only:
```text
stage.started
stage.updated
heartbeat
transport.reconnecting
```
Nunca entra em `messages.content`.

## `content`
Conteúdo durável:
```text
assistant.content.delta
assistant.content.completed
```

## `reference`
Referência a authority:
```text
work.created
approval.required
artifact.ready
```
Não copiar o objeto inteiro.

## `milestone`
Lifecycle/métrica:
```text
turn.accepted
turn.completed
turn.failed
```

# 1.7 EVENT TYPES V1

```text
turn.accepted

attachment.uploading
attachment.ready
attachment.failed

stage.started
stage.updated
stage.completed

assistant.content.start
assistant.content.delta
assistant.content.completed

work.created
work.updated
work.waiting
work.completed
work.failed

approval.required
approval.resolved

artifact.ready

notice
policy.blocked
error

turn.completed
turn.cancelled
heartbeat
```

Warm-up pode ajustar naming, nunca colapsar as semânticas.

# 1.8 STAGE NÃO É MENSAGEM

Hard invariant:

```text
stage.started("Consultando a carteira")
```

não entra em:
- `messages.content`;
- `last_message_preview`;
- transcript de memória;
- learning transcript.

# 1.9 CONTEÚDO DURÁVEL CONTINUA LIMPO

`messages.content` deve ser apropriado para leitura, memória, auditoria e aprendizado.

# 1.10 REFERÊNCIA OPENAI

A Responses API atual usa eventos tipados como `response.output_text.delta` com `item_id`, `output_index`, `sequence_number` e `type`.

Absorver:
> **tipo + identidade + sequência**, não bag de strings.

# 1.11 REFERÊNCIA LANGGRAPH

Mapear:
```text
messages     → assistant content
updates/tasks→ candidate stages
custom       → domain progress
checkpoints  → internal lifecycle
interrupts   → approval/input required
```

Nunca transmitir `debug` ao tenant.

# 1.12 RAW TOOL EVENTS

Pode haver internamente:
```text
tool.started
tool.completed
tool.failed
```

Interaction Projector traduz para stage humano.

# 1.13 CUSTOM DOMAIN EVENTS

Tool pode emitir key controlada:

```json
{
  "domain_stage": "portfolio.consulting",
  "progress": null
}
```

Não texto arbitrário vindo da ferramenta.

# 1.14 STAGE CATALOG

Catálogo versionado, por exemplo:

```text
request.understanding
portfolio.consulting
policy.checking
insurer.consulting
documents.checking
research.searching
research.validating
report.preparing
approval.waiting
delivery.preparing
work.finalizing
```

# 1.15 REDACTION

Stage payload não carrega CPF, telefone, secrets, raw prompts, chunks ou credenciais.

---

# 2. CHAT TURN — UNIDADE DURÁVEL DA INTERAÇÃO

Hoje existem conversation, message, session e `assistantMessageId`, mas não foi encontrada uma authority canônica de turn.

A 096 cria somente se o warm-up confirmar a ausência.

# 2.1 `chat_turns`

Contrato:

```text
id
company_id
conversation_id

client_request_id
idempotency_key

user_message_id
assistant_message_id

status
interaction_class

stream_id
last_sequence

work_run_id?

submitted_at
accepted_at
first_ui_event_at
first_content_at
first_token_at
completed_at
failed_at

error_code
error_summary_redacted

metadata
created_at
updated_at
```

# 2.2 STATUS

```text
SUBMITTED
ACCEPTED
STREAMING
WAITING_INPUT
DELEGATED_TO_WORK
COMPLETED
FAILED
CANCELLED
```

Turn status não substitui Work Run status.

# 2.3 `client_request_id`

UUID por envio. Protege double-click, POST retry e network uncertainty.

Unique final deve respeitar tenant/conversation/user conforme schema vivo.

# 2.4 SERVER ACCEPT É A VERDADE

Fluxo atual:

```text
frontend optimistic bubble
→ /api/messages em background
→ /api/chat/stream
```

O streaming backend persiste assistant depois do stream, mas a user message no web streaming depende da escrita separada do frontend.

Logo pode haver:

```text
resposta gerada
+
user message não persistida
```

Depois:

```text
POST TURN
→ autenticar
→ derivar tenant/user
→ resolver/criar conversation
→ criar/encontrar turn idempotente
→ persistir user message
→ turn.accepted
→ iniciar runtime
```

Frontend continua otimista, mas server owns truth.

# 2.5 MESSAGE IDS

Server pode pré-alocar user/assistant message IDs ao aceitar o turn.

`assistantMessageId` deixa de ser apenas um truque frontend/Realtime e vira relação do turn.

# 2.6 `chat_turn_refs`

Criar se necessário para ordenar referências duráveis:

```text
id
company_id
turn_id
ordinal
ref_type
ref_id
created_at
```

Tipos:
```text
work_run
approval
artifact
research
```

Authority continua fora dessa tabela.

# 2.7 NÃO SALVAR CARD COMO JSON EM TEXTO

Proibido:

```text
messages.content = {"artifact":...}
```

Message text e typed refs são coisas diferentes.

---

# 3. ⛔ SECURITY BLOCKERS

# 3.1 `/api/messages` IDOR

O baseline observado:

- usa service role;
- exige apenas cookie presente;
- recebe `conversation_id`;
- lê/escreve `messages`;
- no route não valida que conversation pertence ao usuário/company autenticado.

O middleware geral também trata `/api/*` como API routes e não faz a validação de dashboard.

Antes de 096 depender dessa superfície, warm-up precisa tentar refutar o IDOR.

## Teste

```text
tenant A autenticado
→ usa conversation UUID de B
→ GET /api/messages?conversation_id=B
```

Esperado:
```text
404/denied
```

Nunca conteúdo.

POST igual.

# 3.2 CORREÇÃO

```text
session
→ derive user/company
→ resolve conversation sob esse scope
→ read/write messages
```

Reusar helper de autenticação já canônico. Não confiar em UUID secreto.

# 3.3 CHAT `companyId` CLIENT-AUTHORITATIVE

O BFF atual repassa body para FastAPI. O backend recebe `companyId/userId/agentId`.

O middleware Next permite `/api/*` sem auth global.

Warm-up precisa provar se existe proteção adicional no caminho de deploy.

Se não existir:

# **P0: browser não escolhe o tenant cujo cérebro, agente e conhecimento serão consultados.**

# 3.4 DASHBOARD TRUST MODE

Para dashboard:

```text
authenticated session
→ BFF derives user_id/company_id
→ backend internal request
```

Client envia apenas:
- prompt;
- authorized conversation/session ref;
- client_request_id;
- attachment refs;
- user-visible options.

# 3.5 WIDGET TRUST MODE

Widget é diferente:

```text
widget identity/token
domain whitelist
rate limit
tenant binding
```

Nunca usar o mesmo trust assumption do dashboard.

# 3.6 CROSS-TENANT MUTATION

Alterar `companyId` no browser e obter conhecimento de outra corretora:

**FAIL.**

# 3.7 SESSION DELETE FAIL-OPEN

O atual delete de checkpoint possui trecho fail-open se ownership check falhar.

A 096 não precisa redesenhar Session TTL, mas se tocar nessa rota para resume/reconnect:

- não perpetuar fail-open;
- usar ownership derived;
- adicionar mutation.

---

# 4. PERFORMANCE — MEDIR ANTES DE OTIMIZAR

# 4.1 MÉTRICAS

```text
T_UI_ACK       click → first local visual feedback
T_SERVER_ACCEPT click → turn.accepted
TTFSE          submit → first semantic server event
TTFT           runtime submit → first text token
TTFC           submit → first meaningful content
TTFW           submit → first Work Run card
T_COMPLETE     submit → turn completed
T_ARTIFACT     submit → artifact ready
```

# 4.2 PERCEIVED VS RUNTIME

Com upload:

```text
click → 3.4s upload → runtime → 1.2s first token
```

TTFT runtime = 1.2s.
Perceived click-to-content = 4.6s.

Medir ambos.

# 4.3 RESPONSIVENESS

Target de UX:
- INP p75 <= 200ms;
- feedback visual local ideal <=100ms.

# 4.4 LATENCY PRINCIPLE

Use ~0.1s/1s/10s como referência de percepção, não como router de negócio.

- rápido: feedback natural;
- acima de ~1s: mostrar activity real;
- longo/indeterminado: Work Card e chat liberado.

# 4.5 BREAKDOWN

Instrumentar:

```text
client submit
BFF accepted
backend accepted
auth/tenant resolved
guardrail
conversation/turn persistence
graph cache hit/miss
graph ready
context assembly
retrieval
model request
first model token
tool start/end
first visible stage
first content
final content
DB persistence
stream close
```

# 4.6 COLD VS WARM

Separar:
```text
warm process + warm graph
warm process + cold graph
cold API process
external provider cold
```

# 4.7 BENCHMARK CORPUS

```text
Q1 greeting/simple
Q2 policy factual
Q3 InfoCap lookup
Q4 commercial analysis
Q5 web research
Q6 document question
Q7 creates Work Run
Q8 approval
Q9 Artifact generation
Q10 failure/retry
```

# 4.8 NÃO TROCAR QUALIDADE POR LATÊNCIA MARGINAL

Otimizar wiring, queries, duplicate calls, cold setup, serialization, context diet e UI.

Troca de modelo só com eval de qualidade + custo + latency, e provavelmente pertence também à SPEC-111.


# 5. STREAM LIFECYCLE E RECONNECT

# 5.1 NETWORK STREAM NÃO É EXECUTION AUTHORITY

🔒 Se o browser fecha:

```text
SSE connection ended
```

isso NÃO implica:

```text
Work Run cancelled
```

Nem:

```text
side effect undone
```

Nem:

```text
turn safely retryable from zero
```

# 5.2 DUAS COISAS DIFERENTES

## Transport resume
Reabrir os eventos/UI de um turn ainda em andamento.

## Work resume
Retomar um Work Run/checkpoint depois de espera, aprovação ou falha.

Nunca misturar.

# 5.3 STREAM ID

Cada turn ativo pode ter:

```text
stream_id
last_sequence
```

O client mantém cursor aplicado.

# 5.4 REPLAY BUFFER

Proposta:

```text
Redis
chat:stream:{company}:{turn}
```

com TTL curto e:
- ordered events;
- sequence;
- event_id.

Não vira history permanente.

# 5.5 DURABLE FALLBACK

Se Redis replay expirou:

```text
load chat_turn
load persisted assistant content
load refs:
  Work Run
  Approval
  Artifact
```

e reconstruir estado útil.

O usuário não precisa receber todos os spinners antigos.

# 5.6 SSE STANDARD

Pode usar:
- event `id`;
- named event;
- `Last-Event-ID`;

ou um cursor equivalente no protocolo.

Se continuar com `fetch()` + ReadableStream, implementar explicitamente `after_sequence`.

A decisão técnica deve considerar POST/auth/browser support.

# 5.7 HEARTBEAT

Heartbeat serve para:

```text
transport health
```

Não para parecer que o sistema está pensando.

Nunca renderizar heartbeat como progresso humano.

# 5.8 RECONNECT UX

Durante interrupção:

```text
Reconectando…
```

discreto.

Depois:
- recuperar stream;
- não criar nova assistant message;
- não reexecutar tool;
- não duplicar token/event.

# 5.9 CONNECTION GAP

Se client tinha sequence 41 e recebe 44:

```text
gap detected
→ replay 42+
```

Não seguir silenciosamente.

# 5.10 CLIENT RELOAD

Ao recarregar:
1. conversation;
2. latest message window;
3. active turns;
4. Work Runs ligados à conversation;
5. pending approvals;
6. refs;
7. reconnect active stream se disponível.

# 5.11 CURRENT CLIENT DISCONNECT RISK

O backend atual persiste `full_response` somente depois de `stream_agent` terminar.

Se a geração/connection falha no meio:
- client pode ter visto texto parcial;
- persistência final pode não acontecer.

Warm-up precisa reproduzir:
- tab close;
- Wi-Fi off;
- proxy timeout;
- client abort;
- backend process restart.

# 5.12 SHORT GENERATION AFTER CLIENT DISCONNECT

Duas opções válidas após medição:

### Option A — server consumes to completion
Bom para turn já aceito e sem side effect duplicável.

### Option B — mark interrupted and allow controlled retry
Se provider/runtime não sustenta consumo desacoplado.

Não deixar estado ambíguo.

# 5.13 VERCEL AI SDK COMO PATTERN, NÃO DEPENDÊNCIA

🌐 AI SDK documenta resume streams com:
- persistent chat;
- active stream ID;
- Redis;
- resume endpoint.

Absorver os princípios.

Não instalar pacote sem necessidade: AutoBrokers já tem Redis, Work Run e checkpointer.

# 5.14 ABORT VS RESUME

AI SDK inclusive alerta que o mecanismo específico de resume pode conflitar com abort.

AutoBrokers deve modelar:

```text
STOP DISPLAY/GENERATION
≠
CANCEL WORK
```

explicitamente.

---

# 6. STOP, CANCEL, RETRY E RESUME

# 6.1 UM BOTÃO NÃO PODE SIGNIFICAR QUATRO COISAS

Possíveis comandos:

```text
Parar resposta
Cancelar trabalho
Tentar de novo
Retomar
```

Cada um atua em uma authority.

# 6.2 STOP GENERATION

Para `INSTANT_RESPONSE`/`INTERACTIVE_ACTION` sem efeito já iniciado:

- abortar model stream quando seguro;
- turn → cancelled/interrupted;
- persistir estado consistente;
- não apagar user message.

# 6.3 CANCEL WORK

Para Work Run:

```text
existing WorkRunService.solicitar_cancelamento()
```

Não apenas fechar stream.

UI:
> “Cancelamento solicitado. O que já foi concluído será preservado.”

# 6.4 RETRY — LEI CENTRAL

🔒

# **Retry the failed unit; never blindly replay the user submission.**

## Transport uncertainty
Mesmo `client_request_id` → server retorna turn existente.

## Generation attempt failed
Nova attempt do mesmo turn, sem repetir efeitos.

## Work Run failed/paused/cancelled
Usar `/work/runs/{id}/retry` e semântica já existente.

## Approval
Resume a mesma execução/checkpoint.

## Delivery
Retry pela authority da entrega, com idempotência.

# 6.5 CURRENT WORK RETRY IS GOOD

O Work API já impede retry de run ainda ativo e preserva etapas concluídas.

Preservar.

# 6.6 DOUBLE CLICK

```text
click Send
click Send again
```

Mesmo `client_request_id`:
- uma user message;
- um turn;
- um runtime execution.

# 6.7 POST TIMEOUT

Browser não sabe se server recebeu.

Retry com mesma key:
```text
get existing accepted turn
```
não cria outro.

# 6.8 REFRESH DURING APPROVAL

Approval card reaparece porque approval é durável.

Não pedir ação novamente via mensagem LLM.

# 6.9 REFRESH DURING WORK

Work card reaparece a partir do Work Run.

# 6.10 RESUME AFTER INTERRUPT

LangGraph atual suporta checkpointer; padrão oficial permite `Command(resume=...)` no mesmo `thread_id`.

Se a authority de Work Approval já encapsular isso, usar aquela authority.

Não criar `chat_resume_state`.

---

# 7. WORK RUN CARD

# 7.1 QUANDO NASCE

Assim que a interação foi promovida/ligada a Work Run:

```text
work.created
```

# 7.2 CONTEÚDO

Card compacto:

```text
Relatório comercial de agosto

Consultando a carteira…
[progresso quando confiável]

Em andamento

Abrir detalhes
Cancelar   ← se permitido
```

# 7.3 NÃO MOSTRAR INTERNOS

Não:
```text
workflow_key=...
worker lease
attempt 3
node X
tool Y
```

# 7.4 HUMAN STAGE

Preferir:
```text
message_human do work_event
```
ou mapping controlado de `current_step_key`.

# 7.5 CARD É LIVE PROJECTION

Fonte:
- Work Run status;
- progress_percent;
- current_step_key;
- Work Events;
- approvals;
- Artifacts.

# 7.6 COMPLETION

```text
Concluído
Relatório pronto
[Abrir entrega]
```

Não duplicar a resposta final em 3 lugares.

# 7.7 FAILED

```text
Não foi possível concluir
<reason human/redacted>
[Tentar novamente]
[Ver detalhes]
```

# 7.8 WAITING EXTERNAL

Exemplos:
```text
Aguardando a seguradora
Aguardando documento
Aguardando sua confirmação
```

Não manter spinner como se compute estivesse rodando.

# 7.9 USER CAN KEEP CHATTING

Depois do Work Run criado:
- composer ativo;
- Work Card permanece na conversation;
- nova mensagem não duplica Work Run.

# 7.10 DIRECTING EXISTING WORK

“Pare isso.”
“Troque o período para agosto.”
“Quando terminar, mande para João.”

Core precisa resolver referência conversacional do Work Run.

Mudança de escopo:
- se Work Run suporta amendment, authority própria;
- senão cria nova Work Run/turn com vínculo causal;
- não mutar histórico silenciosamente.

# 7.11 MULTIPLE ACTIVE WORKS

Uma conversation pode ter mais de um Work Run.

Cada card tem identity.

Comando ambíguo:
> “pare isso”

se há dois ativos → perguntar qual.

# 7.12 CARD POSITION

Ligado ao turn que o criou, não sempre grudado no bottom.

Pode receber updates sem mover a timeline inteira.

# 7.13 COMPACT STATUS STRIP

Quando usuário rolou para longe, opcional:
```text
2 trabalhos em andamento
```

Não um dashboard.

---

# 8. APPROVAL CARD

# 8.1 AUTHORITY

Usar Work Approval/Vault approval existente.

Não `chat_approvals`.

# 8.2 EVENT

```text
approval.required
```

payload/ref mínimo:
```text
approval_id
work_run_id
action_label
target_label
risk_label
summary_redacted
allowed_actions
```

# 8.3 UX

```text
Preciso da sua aprovação

Enviar 24 cobranças pelo WhatsApp
Corretora: Resulta
Risco: ação externa

[Revisar]
[Rejeitar]
[Aprovar]
```

# 8.4 NO RAW TOOL INPUT

O usuário não vê JSON de capability.

# 8.5 DECISION

Botão chama authority existente.

Ao decidir:
- disable duplicate click;
- optimistic “Registrando…”;
- server response decides final state;
- card becomes approved/rejected;
- Work Run resumes.

# 8.6 APPROVED_WITH_EDIT

Se authority suporta:
- abrir edição dos campos autorizados;
- schema-driven;
- não textarea de JSON.

# 8.7 APPROVAL AFTER RELOAD

Card reidrata via pending approval relation.

# 8.8 NEVER LLM-APPROVE

Texto:
> “sim, pode”

pode ser interpretado como intenção, mas efeito de aprovação só acontece através da authority com escopo/identity e policy apropriados.

Definir se natural-language approval será suportado agora ou deferido.

Recomendação V1:
**botão/ação explícita para efeitos de risco alto**.

# 8.9 OPENAI APP APPROVAL AS UX REFERENCE

Referência atual mostra approval card com app/action antes de side effect.

Absorver:
- proposed action visible;
- decision explicit;
- risk/permission contextual.

---

# 9. ARTIFACT INLINE

# 9.1 AUTHORITY

Candidate SPEC-095.

# 9.2 EVENT

```text
artifact.ready
```

carrega ref:
```text
artifact_id
version_id
kind
title
summary
available_formats
```

Dados reais são buscados da Artifact authority.

# 9.3 CARD

```text
Pulso 360 · Agosto

Relatório executivo
Dados até 31/08/2026

[Abrir]
[Baixar PDF]
[Perguntar sobre isso]
```

# 9.4 NÃO ENFIAR HTML NO STREAM

Proibido:
```text
artifact HTML base64/huge JSON
```

# 9.5 FOLLOW-UP

“Por que a comissão caiu?”

Turn pode receber:
```text
artifact_ref
```

como contexto estruturado.

# 9.6 MULTIPLE ARTIFACTS

Turn pode produzir mais de um, mas UI agrupa sem flood.

# 9.7 CLAUDE ARTIFACTS COMO REFERÊNCIA

🌐 Claude usa Artifact separado da conversation para conteúdo substantial/reusável e mantém version selector.

AutoBrokers adapta:
- Artifact é objeto first-class;
- chat é onde se pede/explica;
- Artifact detail/Entregas é onde o entregável vive.

---

# 10. INTERACTION PARTS NA UI

# 10.1 MESSAGE NÃO É MAIS SÓ STRING VISUAL

UI turn pode projetar:

```text
UserMessage
AssistantContent
ActivityStage
WorkCard
ApprovalCard
ArtifactCard
Notice
ErrorCard
AttachmentPart
```

# 10.2 DURABLE TEXT MODEL

Não é obrigatório transformar `messages` numa tabela polymorphic gigante.

Preservar plain text + typed refs.

# 10.3 REFERENCE PATTERN — AI SDK

Vercel AI SDK atual usa `UIMessage.parts` e estados estruturados de tool:

```text
input-streaming
input-available
output-available
output-error
```

Absorver a separação de partes.

Não adotar o SDK como architecture authority.

# 10.4 REACT COMPONENTS

Criar família controlada:

```text
AssistantContent
InteractionActivity
WorkRunCard
ApprovalCard
ArtifactCard
TurnError
AttachmentChip
```

Reusar design tokens/patterns existentes.

# 10.5 NO GIANT CARD WALL

Default collapsed/compact.

Progressive disclosure.

---

# 11. ATTACHMENTS E PERCEIVED LATENCY

# 11.1 GAP ATUAL

InputArea hoje faz upload do image/file antes de chamar `onSendMessage`.

Logo o usuário pode clicar Send e esperar upload sem user bubble.

# 11.2 NOVO FLUXO

```text
click Send
→ local bubble imediato
→ attachment chip = uploading
→ server turn submitted/accepted quando requisitos prontos
→ upload ready
→ runtime starts
```

# 11.3 ATTACHMENT ID

Criar/ref usar identidade para não reupload em retry.

# 11.4 STATUS

```text
uploading
ready
failed
```

# 11.5 UPLOAD FAILURE

User message não deve parecer enviada ao runtime se arquivo obrigatório falhou.

Mostrar:
```text
Não consegui anexar o PDF.
[Tentar upload novamente]
[Enviar sem o arquivo] ← só se semanticamente permitido
```

# 11.6 LARGE FILE

Progress quando storage API expõe.

Não fake percent.

# 11.7 RETRY

Arquivo já armazenado:
```text
reuse attachment_ref
```

não reupload.

# 11.8 VOICE

Voice path atual ainda usa N8N no web chat.

SPEC-112 é a authority futura de voz natural.

096:
- não redesenha voz;
- mantém shell compatível com typed input/output;
- mede e documenta divergence;
- não cria segundo voice runtime.

Se alguma mudança em message/turn quebrar voice, blocker.


# 12. CONVERSATION LOAD PERFORMANCE

# 12.1 GAP ATUAL

`GET /api/conversations?session_id=...` busca:

```text
conversation
+
TODAS as messages
```

ordenadas do início ao fim.

`GET /api/messages` também retorna todas.

Isso funciona enquanto conversa é pequena.

Não é arquitetura para um segundo cérebro usado todos os dias.

# 12.2 INITIAL WINDOW

Carregar inicialmente:

```text
últimas N mensagens
```

N calibrado por tamanho/UX, não hardcode sem teste.

Exemplo candidate:
```text
40–80 mensagens
```

# 12.3 OLDER HISTORY

Scroll para cima:
```text
cursor
→ mensagens anteriores
```

Preservar posição de scroll.

# 12.4 CURSOR

Preferir:
```text
created_at + id
```
ou key monotônica real.

Não OFFSET em history grande.

# 12.5 RUNTIME CONTEXT NÃO DEPENDE DO DOM INTEIRO

LangGraph/checkpointer/memory authority fornece contexto.

Frontend não precisa carregar 2.000 mensagens para o cérebro lembrar.

# 12.6 VIRTUALIZATION

Só introduzir se profiling mostrar render cost relevante.

Primeiro:
- pagination;
- memoização;
- chunk updates.

# 12.7 TOKEN UPDATE RENDERING

Hoje cada pequeno token atualiza React state.

Benchmark:
- token frequency;
- renders/sec;
- CPU;
- mobile.

Se necessário:
```text
coalesce deltas 16–50ms
```

sem aumentar TTFT.

# 12.8 MARKDOWN COST

Streaming Markdown pode rerenderizar documento inteiro.

Medir.

Possible:
- buffer delta;
- render current block;
- finalize Markdown after content block finish.

Não premature optimization.

# 12.9 AUTOSCROLL

Regras:
- se usuário está perto do bottom → follow;
- se rolou para cima → não puxar;
- botão “Voltar ao fim”.

Não interromper leitura por update de Work Card.

---

# 13. CONVERSATION HISTORY / RECENTS

# 13.1 SESSION URL

Preservar `?session=`.

# 13.2 RECENT CHATS

UX-001 recomenda recentes.

Se já houver sidebar/drawer atual, auditar e preservar.

A 096 não cria “Projects”/memory workspace.

# 13.3 ACTIVE TURN BADGE

Recent conversation pode indicar:
```text
Em andamento
Aguardando você
Falhou
```
quando houver turn/work relacionado.

# 13.4 TITLE

Título generation não pode atrasar TTFT.

Background after first turn if needed.

# 13.5 CHATGPT PROJECTS PATTERN

Continuidade “voltar e não começar do zero” é boa referência.

Mas Company Soul/memory scope pertencem às 098/102/106.

096 só garante que a shell reabre a mesma conversation/turn/work corretamente.

---

# 14. ERROR MODEL

# 14.1 NÃO EXISTE “UM ERRO DE CHAT”

Categorias:

```text
TRANSPORT
AUTH
TENANT_SCOPE
VALIDATION
POLICY_BLOCK
BILLING_BLOCK
ATTACHMENT
MODEL
RETRIEVAL
TOOL
WORK
APPROVAL
ARTIFACT
PARTIAL_RESULT
HUMAN_REQUIRED
UNKNOWN
```

# 14.2 USER ERROR CARD

Exemplo:

```text
Não consegui consultar a carteira agora.

A conexão com o sistema de gestão não respondeu.

[Tentar novamente]
[Continuar sem essa consulta]  ← quando permitido
```

# 14.3 INTERNAL DETAILS

Opcional “Detalhes” para suporte:

```text
correlation_id
error_code
timestamp
```

Não stack trace.

# 14.4 CURRENT ERRORS AS TEXT TOKENS

Hoje alguns blockers como:
```text
Créditos insuficientes...
Nenhum agente configurado...
```
são enviados como token de assistant content.

096 deve converter para typed:
```text
policy.blocked
notice
error
```

quando não são uma resposta do AutoBrokers propriamente dita.

# 14.5 PARTIAL RESULT

Se tool falha depois de parte útil:

```text
resultado parcial
+
o que faltou
+
opções
```

Não descartar tudo e nem chamar complete.

# 14.6 ERROR PERSISTENCE

Erro de transporte ephemeral não precisa virar assistant message.

Erro de trabalho durável existe na Work authority.

Erro final que o usuário precisa rever pode ter durable notice/ref.

# 14.7 NO RAW EXCEPTION TO CLIENT

O backend atual pode enviar:
```json
{"error": str(e)}
```

no stream.

Substituir por:
- safe error code;
- human safe message;
- correlation ID.

Raw exception só observability.

---

# 15. USER MESSAGE PERSISTENCE & CONSISTENCY

# 15.1 CURRENT SPLIT WRITE

Web path hoje:
- conversation via Next API;
- user message via `/api/messages`;
- assistant via FastAPI stream.

Isso cria múltiplas autoridades de escrita num único turn.

# 15.2 TARGET

Turn acceptance no BFF/backend transacionalmente coerente:

```text
auth scope
→ conversation
→ turn
→ user message
→ stream
→ assistant message/content
```

# 15.3 EXACTLY-ONCE IS NOT ASSUMED

Distributed effects are at-least-once.

Use:
- idempotency;
- unique constraints;
- attempt records;
- effect authority.

# 15.4 USER MESSAGE CREATE

Unique by:
```text
turn_id + role=user
```
ou equivalente.

# 15.5 ASSISTANT FINALIZATION

Content stream can be incrementally buffered, but canonical final row should have explicit lifecycle.

Possible fields/table projection:
```text
status=streaming|complete|interrupted|failed
```

If adding to messages conflicts schema, keep in `chat_turns`.

# 15.6 PARTIAL CONTENT

If connection/runtime breaks after user saw 30 tokens:

Reopen must not silently show a different history.

Options:
- persist partial snapshot flagged interrupted;
- or final server consumption.

Choose based on measured architecture.

Recommendation:
- persist recoverable content periodically/finally without writing every token to Postgres;
- Redis stream is transient;
- on interruption save partial `assistant_message` with status via turn metadata.

# 15.7 LAST MESSAGE PREVIEW

Only durable user/assistant content.

Never stage/error debug JSON.

---

# 16. CONCURRENCY

# 16.1 CURRENT GLOBAL `isLoading`

Current UI assumes one active response.

After 096 there can be:
- one short active turn;
- multiple durable Work Runs;
- pending approval;
- Artifact results.

# 16.2 TURN SERIALIZATION

For the same conversation, only one **interactive generation turn** should mutate the LangGraph conversational thread at a time unless runtime proves concurrency-safe.

New user message while a short turn is still streaming:
- default either queue or require stop;
- do not race two graph invocations on same thread.

# 16.3 DURABLE WORK DETACH

Once a Work Run is created and detached from conversational generation:
- chat thread can accept a new turn;
- Work Run proceeds separately.

# 16.4 STATEFUL MUTATION

Two Work Runs targeting same mutable business object may need locks.

That belongs primarily to Work OS/097, but 096 must not hide conflict.

Show:
```text
Este atendimento já está sendo alterado por outro trabalho.
```

# 16.5 DUPLICATE INTENT

If user repeats:
> “gere o Pulso 360”

while same idempotent run is active, Core can resolve existing work rather than spawn duplicate when input fingerprint matches.

Specific dedupe belongs to Skill/Work authority.

# 16.6 TURN QUEUE

Avoid a visible “chat queue” unless needed.

If user submits while short turn active:
- local draft can remain;
- explicit “Enviar quando terminar” only if product validation supports.

V1 recommendation:
disable only during true interactive generation, then free immediately on durable handoff.

---

# 17. WORK / CHAT BOUNDARY

# 17.1 PROMOTION EVENT

When runtime decides a durable outcome:

```text
work.created
```

The assistant may also emit concise human text:
> “Vou preparar isso como um trabalho e aviso aqui quando estiver pronto.”

But the durable card is authority.

# 17.2 NO FAKE BACKGROUND

Only say “vou continuar” after Work Run exists durably.

# 17.3 WORK COMPLETION EVENT

When Work Run finishes:
- card updates;
- Artifact card if produced;
- optional concise assistant notification.

# 17.4 RETURNING USER

User opens conversation next day:
```text
Work completed while you were away.
```

derived from Work history.

# 17.5 CHANGE DIRECTION

ChatGPT Work reference supports steering.

AutoBrokers V1:
- if Work Run supports structured input amendment before irreversible step, allow;
- otherwise explain that a new run/revision will be created.

Never mutate effect history.

---

# 18. APPROVAL / INTERRUPT RELATION

# 18.1 LANGGRAPH INTERRUPT

Official pattern:
```text
interrupt(payload)
→ checkpointer saves state
→ UI gets input request
→ Command(resume=...)
```

AutoBrokers already has durable checkpointer.

# 18.2 EXISTING APPROVAL AUTHORITY FIRST

Do not replace WorkApprovalService with raw LangGraph interrupts.

Preferred:
```text
Graph/Work detects approval
→ Work Approval authority
→ ABIS approval.required
→ decision
→ authority resumes correct runtime/checkpoint
```

# 18.3 NODE RESTART WARNING

LangGraph docs note node restarts from beginning after interrupt.

Therefore side effects before interrupt must be idempotent/ordered correctly.

Mutation:
```text
send external message
→ interrupt approval
→ resume reruns node
→ sends twice
```
must fail.

# 18.4 APPROVAL CARD MUST SHOW EFFECT

Not:
> “Continuar?”

But:
> “Enviar 24 mensagens de cobrança pelo WhatsApp da corretora?”

# 18.5 APPROVAL EXPIRY

If approval expires/stales:
- card changes state;
- cannot approve old action;
- Work Run handles timeout.

---

# 19. SOURCE / CITATION UI

For Research/Executive answers:
- keep answer clean;
- citations/source pills compact;
- source detail on demand.

Perplexity user reviews strongly validate:
```text
fast answer
+
sources alongside
+
follow-ups keep context
```

# 19.1 NO SOURCE FLOOD

Do not show 18 raw URLs between every paragraph if the domain output can use compact citations/evidence.

# 19.2 EVIDENCE PACK

When answer has Evidence Pack:
- inline “Fontes” affordance;
- Artifact/evidence authority for deep inspection.

# 19.3 SOURCE STATUS IS NOT STAGE

“3 fontes encontradas” can be progress if produced by research tool.

Do not let model hallucinate count.

---

# 20. VISUAL INTERACTION PRINCIPLES

# 20.1 CLEAN ANSWER FIRST

User praise around current ChatGPT/Claude/Perplexity converges on:
- quick;
- clear;
- intuitive;
- uncluttered;
- follow-up continuity.

Therefore:
```text
ANSWER
```
remains visually dominant.

# 20.2 ONE ACTIVITY ROW

For normal interactive action:

```text
● Consultando a carteira…
```

single row updated in place.

Not:
```text
✓ Planejando
✓ Chamando ferramenta
✓ Buscando memória
✓ Qdrant
✓ Tool
✓ Validator
```

# 20.3 LONG WORK CARD

When durable, card replaces activity row as primary status surface.

# 20.4 DISCLOSURE

“Ver detalhes” can show:
- human steps;
- timestamps;
- evidence;
- status.

Not raw chain-of-thought.

# 20.5 MOBILE

Cards:
- full width;
- primary action thumb-friendly;
- no horizontal table;
- approval actions clear;
- composer stays accessible.

# 20.6 KEYBOARD

- Enter sends;
- Shift+Enter newline;
- Esc may stop current interactive generation if safe;
- focus stays logical after cards.

# 20.7 ACCESSIBILITY

- `aria-live` for status, not every token;
- avoid screen reader reading entire response again per delta;
- focus on approval when requested but do not steal unexpectedly;
- progressbar semantics only for actual percent;
- reduced motion.

# 20.8 MOTION

Subtle.
No ornamental fake “AI thinking” animation that hides status truth.

---

# 21. FRONTEND STATE MODEL

Replace broad:
```text
isLoading: boolean
```

with:

```text
turnStatus
transportStatus
activeInteractionClass
activeStage
activeWorkRefs
pendingApprovalRefs
artifactRefs
attachments
```

# 21.1 EXAMPLE

```ts
type TurnStatus =
  | 'submitting'
  | 'accepted'
  | 'streaming'
  | 'delegated'
  | 'waiting_input'
  | 'complete'
  | 'failed'
  | 'cancelled';
```

# 21.2 TRANSPORT

```text
connected
reconnecting
disconnected
```

does not overwrite turn/work status.

# 21.3 MESSAGE STATE

Do not infer:
```text
last message has empty content → typing
```

Use explicit active turn projection.

# 21.4 UCP TEXT HEURISTIC

Remove after ABIS migration proves equivalent/better typed behavior.

No regex/bracket parser on assistant text.

---

# 22. BFF / BACKEND CONTRACT

# 22.1 SINGLE DASHBOARD TURN ENDPOINT

Recommended public BFF:

```text
POST /api/chat/turns
GET  /api/chat/turns/{turn}/stream?after_sequence=
GET  /api/chat/turns/{turn}
POST /api/chat/turns/{turn}/cancel
```

Exact route naming can adapt.

# 22.2 BFF DERIVES IDENTITY

No client authority for:
- company;
- user;
- permissions;
- agent.

# 22.3 BACKEND INTERNAL REQUEST

BFF → FastAPI with trusted identity/internal key/service auth according to current architecture.

# 22.4 ONE STREAM PROTOCOL

Dashboard browser consumes ABIS.

Widget may consume subset.

# 22.5 VERSIONING

Header/event:
```text
autobrokers.interaction.v1
```

Breaking change → v2.

# 22.6 BACKWARD COMPATIBILITY

During cutover:
- legacy `/api/chat/stream` still available behind flag;
- shadow compare final text;
- new shell only cut over after parity.

# 22.7 NO DOUBLE MODEL CALL

Shadow protocol projection must observe same execution, not execute graph twice.

---

# 23. STREAM PERSISTENCE ARCHITECTURE

# 23.1 SUPABASE

Durable:
- conversation;
- messages;
- chat_turns;
- turn refs;
- Work/Approval/Artifact authorities.

# 23.2 REDIS

Transient:
- active stream replay;
- ephemeral events;
- connection cursor;
- short TTL.

# 23.3 LANGGRAPH CHECKPOINTER

Cognitive graph state/resume.

# 23.4 WORK RUN DB

Durable business execution.

# 23.5 NO NEW MESSAGE BUS

Do not introduce Kafka/NATS merely for chat UI.

Redis + existing DB sufficient until scale evidence says otherwise.

---

# 24. OBSERVABILITY

Every turn:
```text
turn_id
conversation_id
company_id
correlation_id
stream_id
interaction_class
```

Trace spans:
```text
auth
persist
guardrail
graph
context
retrieval
model
tool
work_handoff
artifact
stream
```

No PII in labels.

# 24.1 METRICS

```text
chat_turns_total
chat_turns_failed
chat_turns_cancelled
chat_transport_reconnects
chat_replay_gaps
chat_duplicate_submit_prevented
chat_active_turns
chat_durable_work_handoffs
chat_approval_requests
chat_artifacts_inline

chat_t_ui_ack_ms
chat_t_server_accept_ms
chat_ttfse_ms
chat_ttft_ms
chat_ttfc_ms
chat_t_complete_ms
```

# 24.2 DIMENSIONS

Low-cardinality only:
```text
interaction_class
route/category
cache_hit
result status
provider/model family if appropriate
```

Not user IDs.

# 24.3 LOG EVENTS

Structured, redacted.

No prompt/message full text by default.

---

# 25. PERFORMANCE DIAGNOSTIC

Need measure:
- Supabase queries before first token;
- graph cache hit;
- agent config load;
- company config load;
- guardrail;
- memory/context;
- Qdrant;
- provider;
- serialization;
- Next proxy buffering;
- gzip/proxy;
- React render.

# 25.1 X-ACCEL BUFFERING

Current backend sets `X-Accel-Buffering: no` in stream responses.

Preserve and test through production proxy.

# 25.2 PROXY BUFFER TEST

Automated test:
- backend emits event at t0;
- browser/probe receives without waiting stream end.

# 25.3 EVENT SIZE

Progress payloads small.

Never ship full Work Run state on every 100ms update.

# 25.4 RATE

Coalesce stage/work updates to useful human cadence.

No 60 events/sec progress flood.

# 25.5 TOKEN STREAM

Text token/delta can remain high frequency but frontend may batch paint.


# 26. EXECUTION CARD — PROTOCOLO AAA v10

A execução deve começar registrando um card equivalente:

```text
OUTCOME:
Chat do AutoBrokers responde com stream tipado, preserva mensagem/conversa,
projeta Work/Approval/Artifact, reconecta sem duplicar execução e corrige
os seams de tenant/persistência tocados pela mudança.

RISCO: 8/8
Motivo: Core chat + multi-tenant + service role + side effects + Work/Approval.

SUPERFÍCIE: 3/3
Backend + Web/BFF + DB + UX principal.

PISO: AAA

UNIDADES:
S0 Security & Tenant
A Turn + Persistence
B ABIS + Transport
C Interaction Shell + Work/Approval/Artifact
D Performance + History + Rollout

COESÃO:
Alta entre A/B/C; S0 precede tudo.

PARALELISMO REAL:
Audits/tests/reference work podem ocorrer em paralelo.
Writing on the same chat/persistence seams is serialized.

TIME:
MEASURED_AFTER_WARMUP — não pré-orçar sem diff/bench real.

REFERÊNCIAS:
repo current + LangGraph + OpenAI typed streaming + ChatGPT Work +
AI SDK patterns + Claude Artifacts + web responsiveness.

GATES:
security, persistence, protocol, reconnect, idempotency, visual,
performance, E2E, mutation, production canary.
```

---

# 27. WARM-UP FORENSE OBRIGATÓRIO

Antes de editar qualquer linha:

1. registrar `HEAD`, branch, status;
2. confirmar Protocol AAA v10;
3. ler UX-001;
4. ler SPEC-052/053/055;
5. ler SPEC-081 trecho P-227/P-228;
6. ler SPEC-085 retry/truth state;
7. ler Candidate SPEC-095;
8. abrir `app/dashboard/chat/page.tsx`;
9. abrir `components/MessageBubble.tsx`;
10. abrir `components/InputArea/index.tsx`;
11. abrir `lib/types.ts`;
12. abrir `/api/chat/stream` BFF;
13. abrir `/api/conversations`;
14. abrir `/api/messages`;
15. abrir middleware;
16. abrir backend `chat.py`;
17. abrir `graph.py`/`stream_agent`;
18. abrir graph cache;
19. abrir current checkpointer setup;
20. abrir Work Run API/service;
21. abrir Work Approval;
22. abrir Artifact API/service;
23. procurar `turn_id`, `chat_turn`, `stream_id`, `interaction_event`;
24. procurar resumable stream já existente;
25. procurar Redis Streams/pubsub existentes;
26. mapear todos writers de `messages`;
27. mapear todos readers de `messages`;
28. mapear role/type CHECK do schema vivo;
29. mapear conversation schema;
30. mapear `work_runs.conversation_id`;
31. mapear approval→Work relation;
32. mapear Artifact→Work relation;
33. medir mensagens por conversation no DB;
34. medir maior conversation;
35. medir bytes médios/p95 de message;
36. medir current page load de conversation curta/longa;
37. medir current TTFT corpus Q1–Q10;
38. medir graph cache hit/miss;
39. medir cold/warm;
40. medir upload latency;
41. testar browser disconnect;
42. testar refresh durante stream;
43. testar duplicate Enter/double click;
44. testar proxy buffering;
45. testar stream failure mid-token;
46. testar persistence failure do user message;
47. testar persistence failure do assistant message;
48. testar `/api/messages` cross-tenant;
49. testar `companyId` tampering no chat;
50. testar wrong `agentId`;
51. confirmar widget path/trust mode;
52. confirmar voice/n8n path;
53. registrar screenshots current desktop/mobile;
54. criar baseline Playwright/visual pack;
55. escolher Golden Conversations;
56. produzir **Chat Runtime Reality Report**.

---

# 28. WARM-UP — PREMISSAS A REFUTAR

## R1
“O chat já é autenticado porque o dashboard é autenticado.”

Refutar: `/api/*` bypassa middleware dashboard e cada route precisa own guard.

## R2
“`/api/messages` é tenant-safe.”
Refutar com IDOR.

## R3
“`companyId` recebido do browser é só metadata.”
Refutar: verificar se escolhe company config/brain/tools.

## R4
“Mensagem do usuário e resposta pertencem à mesma operação durável.”
Hoje provavelmente não.

## R5
“Refresh durante stream reabre exatamente a resposta.”
Provar.

## R6
“Client disconnect não afeta execution.”
Provar por classe.

## R7
“`assistantMessageId` resolve toda duplicação.”
Testar user message, retry e duplicated POST.

## R8
“Work Run progress pode virar percent em qualquer workflow.”
Falsa como regra.

## R9
“Todo stage técnico é útil ao corretor.”
Falsa.

## R10
“O current spinner já dá feedback suficiente.”
Medir perceived latency.

## R11
“Todas messages devem carregar no primeiro paint.”
Falsa em escala.

## R12
“`sendVoiceToN8N` já usa o mesmo lifecycle.”
Provavelmente não; documentar sem puxar SPEC-112 para cá.

## R13
“Status de billing/config é resposta do assistente.”
Não; deve ser typed policy/notice.

## R14
“LangGraph precisa de outra infraestrutura para progress.”
Falsa; current streaming/custom modes existem.

## R15
“Resume stream e resume Work são a mesma coisa.”
Falsa.

## R16
“Stop streaming cancela side effect.”
Falsa.

## R17
“Aprovação pode ser uma pergunta de texto comum.”
Insuficiente para efeitos críticos.

## R18
“Artifact precisa ser serializado dentro da mensagem.”
Falsa.

## R19
“Mais eventos na tela significa mais transparência.”
Falsa; pode virar ruído.

## R20
“O que ainda não entendemos do runtime do chat?”
Resposta “nada” reprova warm-up.

---

# 29. GOLDEN CONVERSATIONS

Montar corpus real/sintético sem PII:

```text
G1 “bom dia”
G2 pergunta sobre regra de seguradora
G3 consulta simples de apólice
G4 InfoCap lookup
G5 Raio-X comercial
G6 web research
G7 PDF/document question
G8 gera Artifact
G9 cria Work Run longo
G10 exige approval
G11 falha de provider
G12 connection drop
G13 duplicate submit
G14 Human handoff
G15 attachment upload failure
G16 large conversation
G17 tenant attack
G18 widget public flow
```

---

# 30. IMPLEMENTATION BLOCK S0 — SECURITY FOUNDATION

## S0.1 Scope derivation
Dashboard BFF derives company/user from authenticated session.

## S0.2 Conversation ownership
Central helper:
```text
resolveAuthorizedConversation()
```
ou authority equivalente.

## S0.3 `/api/messages`
Remove raw IDOR seam or route becomes thin wrapper over authorized service.

## S0.4 Chat BFF
Client-provided tenant/agent cannot override session/company authority.

## S0.5 Widget
Separate trust path.

## S0.6 Tests
Cross-tenant read/write, chat company tamper, wrong conversation, wrong turn.

### GATE S0
No byte from tenant B is retrievable/affectable by A through chat/message endpoints.

---

# 31. BLOCK A — TURN FOUNDATION

## A1
Create/reuse `chat_turns`.

## A2
`client_request_id` + idempotency.

## A3
Server accepts turn and persists user message before runtime.

## A4
Canonical assistant message identity.

## A5
Lifecycle timestamps.

## A6
Turn refs if required.

## A7
Legacy compatibility.

### GATE A
Double POST with same client key produces:
```text
1 turn
1 user message
<=1 active execution
```

---

# 32. BLOCK B — ABIS v1

## B1
Event schema/types.

## B2
Interaction Projector.

## B3
Map LangGraph messages.

## B4
Map task/update/custom events to controlled stages.

## B5
Separate content vs ephemeral.

## B6
Typed policy/error.

## B7
Sequence/event IDs.

## B8
Protocol version.

### GATE B
A stage event can be injected and observed in UI without changing persisted assistant content by one byte.

---

# 33. BLOCK C — TRANSPORT & RECONNECT

## C1
stream_id.

## C2
Redis replay buffer.

## C3
after_sequence / SSE id.

## C4
heartbeat.

## C5
gap detection.

## C6
reload hydration.

## C7
partial stream handling.

## C8
disconnect test.

### GATE C
Network drop/reconnect:
- no duplicate tokens;
- no duplicate message;
- no duplicate tool;
- no duplicate Work Run.

---

# 34. BLOCK D — FRONTEND INTERACTION MODEL

## D1
Replace broad `isLoading`.

## D2
typed Interaction parts.

## D3
one compact Activity row.

## D4
clean answer.

## D5
mobile/accessibility.

## D6
remove UCP text parsing after parity.

## D7
preserve agent selector hidden.

### GATE D
User never sees raw tool/node JSON in normal tenant UI.

---

# 35. BLOCK E — WORK RUN CARD

## E1
Promote durable operations.

## E2
Bind current conversation/turn to Work Run.

## E3
Card live status.

## E4
Human stage.

## E5
Meaningful progress.

## E6
Cancel existing authority.

## E7
Retry existing authority.

## E8
Composer unlock.

### GATE E
Long Work continues after page navigation/reload and chat can accept unrelated new turn.

---

# 36. BLOCK F — APPROVAL CARD

## F1
Map existing approval authority.

## F2
Approval required event.

## F3
Approve/reject/edit permitted fields.

## F4
Duplicate click protection.

## F5
Reload.

## F6
Resume runtime.

### GATE F
Approval action executes at most once and resumes same durable work/checkpoint.

---

# 37. BLOCK G — ARTIFACT INLINE

## G1
Artifact ref event.

## G2
Artifact card.

## G3
Open/download actions delegated to 095.

## G4
Ask-about-artifact context.

## G5
Multiple artifacts grouping.

### GATE G
No raw Artifact HTML or PII-heavy payload is serialized into chat event stream.

---

# 38. BLOCK H — ATTACHMENTS

## H1
Immediate local bubble.

## H2
Attachment state.

## H3
Upload identity.

## H4
Retry without reupload.

## H5
Failure UX.

## H6
preserve PDF/DOCX/XLSX etc.

### GATE H
Slow upload no longer creates a blank/frozen UI after Send.

---

# 39. BLOCK I — HISTORY PERFORMANCE

## I1
Latest-message window.

## I2
Cursor older history.

## I3
scroll preservation.

## I4
render profiling.

## I5
delta paint batching only if needed.

### GATE I
Conversation much larger than initial window loads quickly and older messages remain reachable.

---

# 40. BLOCK J — LATENCY INSTRUMENTATION

## J1
timestamps end-to-end.

## J2
client RUM.

## J3
backend spans.

## J4
cache dimensions.

## J5
Q1–Q10 benchmark.

## J6
before/after report.

### GATE J
TTFT and perceived latency are both measurable separately.

---

# 41. BLOCK K — CUTOVER

## K1
legacy stream behind flag.

## K2
shadow protocol projection on same execution.

## K3
final-content parity.

## K4
canary tenants.

## K5
visual acceptance.

## K6
rollback.

### GATE K
No production cutover while new protocol final answer differs from legacy for reasons unrelated to intentional typed event cleanup.

---

# 42. DATA MIGRATION

Expand-first.

Potential:
```text
chat_turns
chat_turn_refs
messages.turn_id nullable
```

Only after live schema audit.

No destructive rewrite of historical messages.

# 42.1 BACKFILL

Old messages:
```text
turn_id = null
```
is acceptable.

Do not fabricate historical turns.

# 42.2 NEW MESSAGES

After cutover:
all dashboard Core user/assistant interactions should be tied to turn when applicable.

# 42.3 WORK RUN RELATION

Current `work_runs.conversation_id` exists.

Add `turn_id` to Work Run only if it materially improves exact lineage and schema authority approves.

Alternative:
`chat_turn_refs` relation.

Prefer least schema duplication.

---

# 43. API AUTHORIZATION RULES

Every endpoint:
- derive authenticated principal;
- derive tenant;
- validate resource under tenant;
- then use service role.

Never:
```text
cookie exists → arbitrary UUID accepted
```

# 43.1 RESPONSE SHAPE

Unauthorized cross-tenant UUID:
```text
404
```
where existence should not be disclosed.

# 43.2 ADMIN

Admin support access follows Control Plane/support access authority.

No “admin cookie means all conversations” shortcut.

# 43.3 WIDGET

No users_v2 session assumed.

Bind widget to agent/company server-side.

---

# 44. PRIVACY

ABIS payloads should be minimum necessary.

Do not send:
- memory records;
- prompts;
- system instructions;
- tool auth;
- raw insurer credentials;
- all Work input;
- hidden reasoning.

# 44.1 CHAIN OF THOUGHT

No hidden reasoning surfaced as “progress”.

Stage describes action class, not reasoning transcript.

# 44.2 LOGGING

Message content redacted/omitted in timing logs.

# 44.3 ERROR

No raw exception text.

---

# 45. ACCESSIBILITY / VISUAL ACCEPTANCE

Protocol v10 requires inspectable UI references and evidence.

Create acceptance pack with:
- empty state;
- streaming answer;
- action stage;
- Work card running;
- Work waiting;
- Approval;
- Artifact;
- Error;
- reconnect;
- upload;
- long conversation;
- mobile.

# 45.1 REFERENCE TARGETS

Use principles, not pixel copy:
- ChatGPT clean answer + Work long-task boundary;
- Claude Artifact first-class output;
- Perplexity compact sources;
- Linear-like density already part of design language.

# 45.2 VISUAL SCORECARD

Judge:
```text
clarity
density
hierarchy
state truth
mobile
accessibility
action discoverability
technical-noise absence
```

---

# 46. PERFORMANCE ACCEPTANCE

Must include:
- RUM p50/p75/p95;
- controlled benchmark;
- mobile browser profile;
- production canary.

No localhost-only “fast”.

# 46.1 REGRESSION BUDGET

If quality remains equal but:
```text
TTFT p95 worsens materially
```
investigate before cutover.

Exact threshold set from baseline.

# 46.2 NO FAKE SPEED

Optimistic bubble can be immediate.

But:
```text
turn.accepted
```
only after server acceptance.

UI must distinguish local “sending” from server “accepted”.

---

# 47. RELIABILITY ACCEPTANCE

Test:
- backend restart;
- Next restart;
- Redis unavailable;
- Supabase transient;
- LLM 429/500;
- tool timeout;
- browser offline;
- duplicate event;
- out-of-order event;
- event gap;
- replay TTL expired.

# 47.1 REDIS DOWN

For instant turn:
- stream can still work without replay if safe;
- reconnect degrades.

For Work:
- durable state remains Work DB/checkpointer.

No business execution lost solely because replay buffer unavailable.

---

# 48. FALLBACK MODE

If ABIS projector fails:

Prefer:
```text
safe final text
```
over raw technical events.

Can fallback to legacy content streaming if protocol compatibility allows.

Never bypass tenant guard.

---

# 49. FEATURE FLAGS

Suggested:
```text
CHAT_INTERACTION_V1
CHAT_RESUMABLE_STREAM
CHAT_WORK_CARDS
CHAT_APPROVAL_CARDS
CHAT_ARTIFACT_CARDS
```

Flags for canary/rollback, not permanent architecture fragmentation.

---

# 50. NO PARALLEL RUNTIME

Explicitly prohibited:
- Vercel AI SDK as second agent runtime;
- OpenAI Responses as direct parallel brain;
- separate chat agent;
- separate work scheduler;
- separate approval engine;
- separate Artifact generator.

External systems are references/protocol examples.


# 51. RED TEAM MISSION

> **Fazer a Interaction Shell parecer correta enquanto duplica uma ação, mistura tenants, perde uma mensagem, transforma progresso em memória ou afirma um estado que a autoridade não confirmou.**

Attack list:

1. GET messages de outra corretora;
2. POST message em conversation alheia;
3. trocar `companyId` no browser;
4. trocar `agentId`;
5. usar session UUID de outro user;
6. duplicate Send;
7. duplicate POST after timeout;
8. reconnect replay duplicate;
9. out-of-order sequence;
10. Redis lost;
11. stream mid-failure;
12. client tab closes;
13. Next proxy restarts;
14. FastAPI restarts;
15. assistant partial text not persisted;
16. user message save fails;
17. assistant save fails;
18. stage text leaks into message;
19. tool JSON leaks to Markdown;
20. UCP JSON visible;
21. Work Run created twice;
22. stop stream cancels UI but Work continues silently;
23. UI says Work cancelled before authority;
24. retry active Work;
25. approval double-click;
26. approval stale;
27. side effect before interrupt repeats on resume;
28. Artifact card points wrong version;
29. Artifact from tenant B;
30. approval from tenant B;
31. Work Run from tenant B;
32. fake progress percent;
33. fake timed stages;
34. model hallucinated “estou consultando” treated as actual progress;
35. billing block persisted as normal assistant advice;
36. raw exception exposed;
37. attachment upload silently fails but runtime answers as if file read;
38. attachment retries duplicate storage;
39. long history crashes mobile;
40. autoscroll steals user position;
41. screen reader rereads full message each token;
42. stream continues and new short turn races same LangGraph thread;
43. Work Run completion moves wrong card;
44. “pare isso” cancels wrong active Work;
45. widget uses dashboard trust model;
46. dashboard uses client-supplied tenant;
47. heartbeat persisted;
48. stage persisted to memory;
49. event replay includes PII;
50. debug projection reaches tenant UI.

---

# 52. MUTATIONS OBRIGATÓRIAS

## M1 — remove tenant validation from `/api/messages`
**FAIL.**

## M2 — trust request `companyId` over authenticated session
**FAIL.**

## M3 — persist `stage.started` in `full_response`
**FAIL.**

## M4 — duplicate same ABIS event
UI applies once.

## M5 — sequence gap 41→44
Client detects gap/replays, not silent continue.

## M6 — same `client_request_id` posted twice
One turn.

## M7 — same turn creates Work Run twice
**FAIL.**

## M8 — reconnect causes duplicate assistant text
**FAIL.**

## M9 — browser closes; durable Work disappears
**FAIL.**

## M10 — Stop response marks Work cancelled
**FAIL.**

## M11 — retry Work while status running
Must reject.

## M12 — approval button clicked twice
One decision/effect.

## M13 — approval resume reruns non-idempotent side effect
**FAIL.**

## M14 — raw tool name visible in tenant progress
**FAIL.**

## M15 — stage driven only by timer
**FAIL.**

## M16 — arbitrary workflow shows 63% with no calibrated authority
**FAIL.**

## M17 — Artifact HTML serialized in stream
**FAIL.**

## M18 — Artifact card can open cross-tenant Artifact
**FAIL.**

## M19 — attachment failed, runtime claims to have analyzed it
**FAIL.**

## M20 — retry reuploads already-ready attachment
**FAIL.**

## M21 — client loads all 10k messages initially
**FAIL** after pagination cutover.

## M22 — raw backend exception reaches user
**FAIL.**

## M23 — billing/config blocker stored as ordinary assistant content unless deliberately modelled as durable notice
**FAIL.**

## M24 — heartbeat enters conversation transcript
**FAIL.**

## M25 — hidden chain-of-thought sent as stage
**FAIL.**

## M26 — `showAgentSelector=true` for ordinary tenant user
**FAIL.**

## M27 — user can select another tenant’s Work Run by guessed id
**FAIL.**

## M28 — reconnect after replay TTL creates a fresh execution
**FAIL.**

## M29 — current stream protocol outputs content and typed cards but final persisted text differs from visible final assistant text
**FAIL**, except explicitly non-text UI refs.

## M30 — user sees “Concluído” while Work authority is `waiting_approval`
**FAIL.**

---

# 53. PROPERTY-BASED / INVARIANT TESTS

Generate:
- random event order with duplicates;
- reconnect points;
- turn statuses;
- Work statuses;
- approval states;
- attachment combinations.

Invariants:

```text
applied_sequence never decreases
same event_id has no second effect
same idempotency key has one turn
turn reference tenant == conversation tenant
work ref tenant == turn tenant
artifact ref tenant == turn tenant
approval ref tenant == turn tenant
ephemeral event never changes durable content
completed Work never has running UI after reconciliation
```

---

# 54. TEST MATRIX — TURN

- new conversation;
- existing conversation;
- two fast turns;
- double click;
- POST timeout;
- model error before token;
- model error after tokens;
- policy block;
- human mode;
- user message persistence failure;
- assistant persistence failure;
- reload.

# 55. TEST MATRIX — STREAM

- normal;
- no text, Work created;
- stage + text;
- text + tool + text;
- reconnect;
- duplicate;
- gap;
- heartbeat;
- Redis unavailable;
- proxy buffering;
- large token stream;
- mobile slow network.

# 56. TEST MATRIX — WORK

- created;
- queued;
- running;
- waiting approval;
- waiting external;
- completed;
- failed;
- cancelled;
- retry;
- multiple Work Runs;
- Work outlives conversation browser tab.

# 57. TEST MATRIX — APPROVAL

- approve;
- reject;
- approved_with_edit;
- double-click;
- stale;
- expired;
- reload;
- cross tenant;
- Work already cancelled;
- action side effect idempotency.

# 58. TEST MATRIX — ARTIFACT

- one;
- many;
- not ready;
- version selected;
- cross tenant;
- PDF available;
- only web available;
- Artifact superseded;
- ask follow-up.

# 59. TEST MATRIX — ATTACHMENT

- image;
- PDF;
- DOCX;
- XLSX;
- CSV;
- upload slow;
- upload fails;
- retry;
- multiple files if supported;
- file already stored;
- unsupported type;
- oversized;
- malicious filename.

# 60. TEST MATRIX — HISTORY

Synthetic:
```text
10
100
1,000
10,000 messages
```

Measure:
- API bytes;
- time to first render;
- memory;
- scroll;
- mobile.

# 61. TEST MATRIX — AUTH

- valid tenant;
- another user same company;
- user not owner depending policy;
- tenant B conversation;
- tenant B turn;
- tenant B Work;
- tenant B Artifact;
- tenant B approval;
- admin support authorized;
- widget;
- no cookie;
- expired session.

---

# 62. E2E-1 — SIMPLE ANSWER

```text
Enter
→ local bubble
→ server accepted
→ content start
→ deltas
→ content completed
→ persisted assistant
→ turn completed
```

No activity row if response is fast enough and no real stage worth showing.

# 63. E2E-2 — TOOL ACTION

```text
“qual a apólice da Maria?”
→ accepted
→ Consultando a carteira
→ stage completed
→ answer streams
→ persisted answer
```

No tool name.

# 64. E2E-3 — LONG REPORT

```text
“faça o Pulso 360 de agosto”
→ accepted
→ work.created
→ Work Card
→ composer unlocked
→ user asks another question
→ Work updates
→ Artifact ready
→ Artifact Card
```

# 65. E2E-4 — APPROVAL

```text
request side effect
→ Work Card
→ approval.required
→ Approval Card
→ user approves
→ one authority decision
→ same Work resumes
→ result
```

# 66. E2E-5 — REFRESH

```text
turn streaming
→ refresh
→ conversation reload
→ active turn found
→ replay from sequence
→ same assistant message
→ no duplicate execution
```

# 67. E2E-6 — REPLAY EXPIRED

```text
turn/work active
→ Redis replay TTL gone
→ reload
→ durable state reconstructs:
   message + work + approval/artifact refs
```

No reexecution.

# 68. E2E-7 — NETWORK DROP

```text
disconnect
→ UI reconnecting
→ runtime outcome depends on interaction class
→ reconnect/reconcile
```

No misleading “failed” just because browser lost socket.

# 69. E2E-8 — SECURITY

Tenant A substitutes B IDs.

Every layer:
```text
not found/denied
```

No timing/body leak materially revealing content.

# 70. E2E-9 — ATTACHMENT

```text
send PDF
→ bubble immediately
→ file uploading
→ ready
→ turn accepted/runtime starts
→ answer grounded in actual file
```

# 71. E2E-10 — PARTIAL FAILURE

```text
assistant streams intro
→ external data source fails
→ typed partial-result/error
→ durable text remains coherent
→ options displayed
```

---

# 72. BASELINE / CONTROL

Before code:

```text
CURRENT_TTFT.json
CURRENT_CHAT_VISUALS/
CURRENT_STREAM_TRANSCRIPT.ndjson
CURRENT_LONG_CONVERSATION_PROFILE.json
CURRENT_RECONNECT_RESULTS.md
CURRENT_SECURITY_PROBES.md
```

After:
same corpus, same environment.

# 72.1 CONTROL ANSWER QUALITY

Protocol change cannot lower answer quality.

Run semantic/output eval against same prompts.

# 72.2 CONTROL SIDE EFFECT

No new extra tool/Work calls.

# 72.3 CONTROL COST

Typed progress should not require extra LLM calls.

Target:
```text
zero extra model call purely for progress UI
```

---

# 73. ROLLOUT

## Stage 0
Security fixes + instrumentation only.

## Stage 1
Turn authority and typed content events shadowing legacy.

## Stage 2
InteractionActivity.

## Stage 3
Reconnect.

## Stage 4
Work Cards.

## Stage 5
Approval + Artifact cards.

## Stage 6
History pagination/attachment improvements.

## Stage 7
Canary.

## Stage 8
Default on.

No simultaneous big-bang.

# 73.1 PILOTS

Use:
- Amandus/internal;
- Resulta controlled;
- AutoFleet only when authorized;
- synthetic tenant B for isolation attacks.

# 73.2 FEATURE FLAG CUTOVER

New and legacy cannot both trigger graph.

Only projection/UI path changes.

# 73.3 ROLLBACK

Rollback Interaction Shell without deleting:
- turn rows;
- messages;
- Work Runs;
- Artifacts;
- approvals.

Legacy text stream can remain emergency fallback until proven.

---

# 74. OBSERVABILITY DASHBOARD / REPORT

At minimum report:

```text
Turn success rate
TTFT p50/p75/p95
First semantic event
Reconnect rate
Reconnect success
Duplicate prevented
Work handoff rate
Approval wait
Artifact inline rate
Client error rate
Cross-tenant denied probes
```

Not necessarily build a giant dashboard in tenant UI.

Operational/Admin telemetry.

---

# 75. SUCCESS CRITERIA

Qualitative:
- user knows system reacted;
- understands what it is doing at human level;
- can keep working;
- never needs technical runtime vocabulary;
- refresh does not destroy confidence.

Quantitative:
- zero known tenant leak;
- zero duplicate effect in mutation/E2E;
- message persistence consistency;
- measurable latency;
- no stage contamination;
- old conversation initial load bounded;
- Work/Approval/Artifact rehydrate.

---

# 76. DEFINITION OF DONE — SECURITY

- [ ] `/api/messages` tenant safe.
- [ ] chat tenant derived server-side.
- [ ] agent identity authorized.
- [ ] conversation ownership.
- [ ] turn ownership.
- [ ] Work ref ownership.
- [ ] Artifact ref ownership.
- [ ] Approval ref ownership.
- [ ] widget trust separate.
- [ ] cross-tenant mutation suite green.
- [ ] no raw exception leak.

# 77. DEFINITION OF DONE — TURN

- [ ] canonical turn identity.
- [ ] idempotent submit.
- [ ] user message server-owned.
- [ ] assistant relationship.
- [ ] lifecycle status.
- [ ] metrics timestamps.
- [ ] duplicate POST control.
- [ ] partial/interrupted status.

# 78. DEFINITION OF DONE — STREAM

- [ ] ABIS versioned.
- [ ] typed events.
- [ ] sequence.
- [ ] event IDs.
- [ ] content separated from ephemeral.
- [ ] no UCP-in-text dependency.
- [ ] replay.
- [ ] gap detection.
- [ ] reconnect.
- [ ] heartbeat transport-only.
- [ ] proxy no buffering.

# 79. DEFINITION OF DONE — UX

- [ ] clean answer first.
- [ ] one compact stage row.
- [ ] no technical tool names.
- [ ] no fake stages.
- [ ] no fake percent.
- [ ] agent selector remains hidden.
- [ ] mobile.
- [ ] keyboard.
- [ ] screen-reader behavior.
- [ ] autoscroll respects user.
- [ ] visual acceptance pack.

# 80. DEFINITION OF DONE — WORK

- [ ] durable classification.
- [ ] Work card.
- [ ] progress from authority.
- [ ] waiting states.
- [ ] cancel.
- [ ] retry.
- [ ] reload.
- [ ] composer unlocked after durable handoff.
- [ ] multiple active Works handled.
- [ ] ambiguous command asks instead of cancelling wrong run.

# 81. DEFINITION OF DONE — APPROVAL

- [ ] existing authority reused.
- [ ] card.
- [ ] action detail/risk.
- [ ] duplicate decision impossible.
- [ ] resume same work.
- [ ] reload.
- [ ] stale handled.
- [ ] no side effect duplicated around interrupt.

# 82. DEFINITION OF DONE — ARTIFACT

- [ ] Artifact ref event.
- [ ] card.
- [ ] exact authorized object.
- [ ] version correct.
- [ ] open.
- [ ] format action from 095.
- [ ] ask-about-artifact.
- [ ] no huge payload in stream.

# 83. DEFINITION OF DONE — ATTACHMENT

- [ ] immediate feedback.
- [ ] upload state.
- [ ] failure state.
- [ ] attachment identity.
- [ ] retry reuse.
- [ ] runtime never pretends failed file was analyzed.
- [ ] voice path preserved/documented.

# 84. DEFINITION OF DONE — PERFORMANCE

- [ ] current baseline measured.
- [ ] actual TTFT measured.
- [ ] perceived latency measured.
- [ ] INP measured.
- [ ] cold/warm.
- [ ] cache hit/miss.
- [ ] production canary.
- [ ] long conversation bounded.
- [ ] no extra model call for decorative progress.

# 85. DEFINITION OF DONE — RESILIENCE

- [ ] reload.
- [ ] tab close.
- [ ] network drop.
- [ ] Redis loss.
- [ ] backend restart.
- [ ] BFF restart.
- [ ] duplicate event.
- [ ] gap.
- [ ] replay expiry.
- [ ] rollback.

---

# 86. NÃO É DEFINITION OF DONE

Não puxar para a 096:
- Company Soul;
- memory scope redesign;
- Dreams;
- Operations Case Workspace;
- full Voice architecture;
- Model/Cost Fabric;
- external harness;
- marketplace;
- general notification center;
- new Work runtime;
- new Artifact system;
- team scope model final;
- all chat history redesign beyond what performance needs.

Esses itens têm SPECS próprias.

---

# 87. REJECTED — STATUS COMO TEXTO DO MODELO

🚫

“Vou consultar...” pode continuar como linguagem natural quando fizer sentido, mas não é authority de progress.

---

# 88. REJECTED — EVENTO DE TOOL DENTRO DE `full_response`

🚫

Polui transcript, memória e resposta.

---

# 89. REJECTED — INSTALAR VERCEL AI SDK E DEIXAR ELE VIRAR O CHAT RUNTIME

🚫

Absorver patterns, não entregar authority.

---

# 90. REJECTED — NOVO WORK ENGINE PARA CHAT

🚫 Work OS já existe.

---

# 91. REJECTED — NOVA TABELA DE APPROVAL PARA UI

🚫 authority já existe.

---

# 92. REJECTED — SALVAR TODA EPHEMERAL PROGRESS NO POSTGRES

🚫

Redis/transient + Work Events quando realmente durável.

---

# 93. REJECTED — PROGRESSO SIMULADO

🚫.

---

# 94. REJECTED — BLOQUEAR COMPOSER ATÉ TRABALHO DE 20 MINUTOS TERMINAR

🚫.

---

# 95. REJECTED — CANCELAR WORK AO FECHAR TAB

🚫.

---

# 96. REJECTED — REENVIAR O PROMPT INTEIRO EM QUALQUER ERRO

🚫.

Retry age na unidade falha.

---

# 97. REJECTED — CARREGAR TODA CONVERSA

🚫.

Pagination/cursor.

---

# 98. REJECTED — USER ESCOLHE SUBAGENTE/TOOL

🚫.

AutoBrokers coordena.

---

# 99. REJECTED — MOSTRAR CHAIN OF THOUGHT COMO TRANSPARÊNCIA

🚫.

Mostrar ações/estados verificáveis, não raciocínio privado.

---

# 100. REJECTED — “RÁPIDO” SEM MEDIR

🚫.

---

# 101. DECISÕES CONGELADAS

| Tema | Decisão |
|---|---|
| Chat é shell, não runtime authority | **SIM** |
| Smith/LangGraph preservado | **SIM** |
| Work Run para durable work | **SIM** |
| 3 interaction classes | **SIM** |
| ABIS typed events | **SIM** |
| Raw tool names tenant UI | **NÃO** |
| Stage fake/timer | **NÃO** |
| Percent fake | **NÃO** |
| Turn identity/idempotency | **SIM** |
| Server owns user message acceptance | **SIM** |
| Client `companyId` authority | **NÃO** |
| `/api/messages` raw UUID trust | **NÃO** |
| Redis replay | **SIM, se benchmark/infra confirmarem** |
| Stream = execution authority | **NÃO** |
| Work survives tab | **SIM** |
| Stop response = Cancel Work | **NÃO** |
| Retry prompt blindly | **NÃO** |
| Existing Work retry reused | **SIM** |
| Approval authority reused | **SIM** |
| Artifact authority reused | **SIM** |
| Artifact inline card | **SIM** |
| Composer unlocked after durable handoff | **SIM** |
| Agent selector normal user | **NÃO**; já hidden |
| History initial load all | **NÃO** |
| Actual + perceived latency | **MEDIR AMBOS** |
| Extra LLM call for progress | **NÃO** |
| Voice architecture redesign | **SPEC-112** |
| Memory/Soul redesign | **SPECS 098/102/106** |

---

# 102. SCORE

| Dimensão | Nota |
|---|---:|
| Importância para produto | **100/100** |
| Impacto percebido | **100/100** |
| Reuso do runtime existente | **100/100** |
| Segurança | **100/100 após S0** |
| Durabilidade | **100/100** |
| UX | **100/100** |
| Compatibilidade Work OS | **100/100** |
| Preparação Engine | **100/100** |
| Complexidade de execução | **93/100** |
| Prioridade agora | **100/100** |

---

# 103. O GANHO REAL

Antes:

```text
usuário envia
→ input bloqueia
→ spinner
→ string cresce
→ talvez haja tool/work por trás
→ refresh pode quebrar percepção
→ resultado técnico precisa caber na mensagem
```

Depois:

```text
usuário envia
→ feedback imediato
→ turn aceito
→ progresso real e humano
→ resposta OU Work Run
→ chat continua
→ approval no contexto
→ Artifact no contexto
→ reconnect/reconcile
→ retry sem duplicação
```

---

# 104. O MOAT

Não é “streaming mais bonito”.

É:

> **Uma camada de interação própria para um Intelligence OS agentic, capaz de apresentar trabalho, confiança e controle sem expor a complexidade interna.**

---

# 105. LEI FINAL

> **O usuário deve perceber ação imediatamente, entender o estado com verdade e nunca precisar ficar preso à conexão do navegador para que o trabalho exista.**

E:

> **Tudo que é progresso de interface desaparece quando deixa de ser útil; tudo que é trabalho, decisão ou resultado permanece na sua authority correta.**

Essa é a SPEC-096.
