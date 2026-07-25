---
> **Status:** preflight READ-ONLY — SPEC-055 Durable Work Runs, Queue, Checkpoints & HITL
> **Data:** 25/07/2026 · **Base:** `main` @ `5aee5a0` (SPEC-054 concluída)
> **Veredito:** `READY_WITH_ONE_BLOCKER` — um pré-requisito só o Founder pode fornecer
---

# Preflight da SPEC-055

## 0. Integridade

Read-only. Nenhuma migration, write, deploy ou alteração de infraestrutura. Nenhum segredo lido ou reproduzido.

---

# 1. 🔴 BLOQUEADOR — o checkpointer está em memória em produção

Este é o achado que muda o plano da SPEC-055.

## Evidência

| Fato | Fonte |
|---|---|
| `SUPABASE_DB_URL` é `Optional[str]` | [`config.py:17`](../../../backend/app/core/config.py#L17) |
| Sem essa variável, o grafo cai para `MemorySaver()` | [`graph.py:53-57`](../../../backend/app/agents/graph.py#L53-L57) |
| A variável **não** está nas env vars do serviço `smith-api` | inventário do EasyPanel |
| Tabela `checkpoints` | **0 linhas** |
| `checkpoint_writes` | **0 linhas** |
| `checkpoint_blobs` | **0 linhas** |
| Threads distintas persistidas | **0** |

As tabelas do `AsyncPostgresSaver` **existem** (foram criadas pelo `setup()`), mas estão vazias. Isso confirma que o caminho ativo em produção é o fallback em memória.

## Consequência

```text
Hoje, o estado cognitivo de qualquer conversa
morre quando o container reinicia.
```

A SPEC-055 inteira — retomada por checkpoint, `interrupt`/`resume` para HITL, recuperação de Work Run órfão — **assume checkpoint durável**. Construir Work Runs sobre um checkpointer em memória entregaria durabilidade aparente: a linha em `work_runs` sobreviveria ao restart, mas o estado do grafo não, e o run retomaria do nada.

## O que resolve

Definir `SUPABASE_DB_URL` no serviço `smith-api` do EasyPanel, apontando para o pooler do Supabase em **transaction mode** (porta 6543), com `prepare_threshold=None` — que o código já trata corretamente em [`graph.py:83-88`](../../../backend/app/agents/graph.py#L83-L88).

**Isso exige a senha do banco, que o executor não possui e não deve solicitar por chat.** É a única dependência humana da SPEC-055.

**Não bloqueia o Bloco A** (modelo de dados). Bloqueia o **Bloco B** (worker, leases, resume) — sem checkpoint durável, o gate do Bloco B não pode ficar verde honestamente.

---

# 2. Estado atual das três histórias de execução

## 2.1 `routine_runs` — 39 linhas

```text
id, routine_id, started_at, finished_at, status, output_preview, error
```

| Falta | Impacto na SPEC-055 |
|---|---|
| `company_id` | não dá para filtrar por tenant sem join; FK de company impossível hoje |
| `idempotency_key` | reexecução duplica efeito |
| `attempt` / retry policy | não distingue 1ª de 5ª tentativa |
| lease / `heartbeat_at` | run órfão não é detectável |
| checkpoint ref | não retoma |
| vínculo com approval/artifact | HITL impossível |

Status observados: `ok`, `error`. **Rotinas ativas hoje: 0.** Migração é barata.

## 2.2 `auxiliary_runs` — 4 linhas

```text
id, company_id, tenant_auxiliary_id, template_id, conversation_id, session_id,
user_id, status, run_type, input, output, error_message, started_at,
finished_at, cost_usd, token_usage, metadata, created_at, updated_at
```

**É o modelo mais maduro dos três.** Já tem `company_id`, custo e tokens — exatamente o que a SPEC-055 §25 pede para budget. Falta idempotência, lease, attempt e steps.

Status observado: `succeeded`. 5 auxiliares instalados.

## 2.3 `portal_jobs` — 91 linhas

```text
id, company_id, portal_key, journey, account_id, params, status,
evidence, screenshots, error, attempts, created_at, started_at, finished_at
```

**Já tem `attempts` e claim atômico** no worker. É a peça de execução mais madura do sistema. Status: `done` (19), `needs_human` (67), `failed` (5).

> `needs_human` = 67 de 91. O Portal Worker **já pratica HITL na prática**, só que representado em status, não em modelo executável. A SPEC-055 §21.4 deve absorver isso, não substituir.

## 2.4 `approval_requests` — 8 linhas · **melhor base do que eu esperava**

```text
id, company_id, tenant_connection_id, permission_grant_id,
requested_by_user_id, approved_by_user_id, subject_type, subject_id,
action_type, status, risk_level, preview, request_payload,
approval_result, error_message, expires_at, approved_at, rejected_at,
executed_at, created_at, updated_at
```

Já contempla: sujeito polimórfico, tipo de ação, risco, **preview**, payload, expiração, e a separação entre `approved_at` e `executed_at` — que é justamente o que evita executar duas vezes uma aprovação.

Status: `approved`, `executed`, `rejected`. Tipos: `tenant_auxiliary/whatsapp_draft_message`, `tenant_auxiliary/whatsapp_send_message_dry_run`.

**Decisão:** a SPEC-055 §7.7 manda evoluir, não recriar. Confirmo: evoluir. Falta apenas `work_run_id`, `work_step_id`, `fingerprint` (para detectar que o conteúdo mudou depois da aprovação) e `decided_edit` (aprovar com edição).

---

# 3. Infraestrutura

| Peça | Estado | Nota |
|---|---|---|
| Redis | **disponível**, cliente sync e async singleton em [`core/redis.py`](../../../backend/app/core/redis.py) | usado hoje só para buffer de WhatsApp e locks de memória |
| Redis Streams | **não usado** | SPEC-055 §10 introduz |
| Worker dedicado | **não existe** | scheduler de rotinas roda in-process no FastAPI ([`main.py:83`](../../../backend/app/main.py#L83)) |
| Celery | existe, restrito a billing e sanitização | **não** deve virar o worker do Work OS — SPEC-055 §11.1 pede worker Smith |
| Portal Worker | processo separado, claim atômico, recuperação de órfão | **preservar e integrar** |
| `usage_events` | não existe | D4: write-path append-only entra aqui |

---

# 4. Modelo de dados proposto

Sete objetos. Nenhum substitui tabela existente — todos convivem até o cutover.

| Tabela | Papel | Origem do legado |
|---|---|---|
| `work_runs` | execução universal | `routine_runs` + `auxiliary_runs` |
| `work_steps` | etapa | novo |
| `work_attempts` | tentativa por etapa | `portal_jobs.attempts` |
| `work_events` | trilha append-only | novo |
| `work_effects` | reserva de efeito externo idempotente | novo — **peça central** |
| `work_queue_outbox` | outbox transacional | novo |
| `usage_events` | consumo técnico `PRE_LAUNCH_NON_BILLABLE` | D4 |

`approval_requests` **evolui** com `work_run_id`, `work_step_id`, `fingerprint`, `decided_edit`.

## Campos que a SPEC-054 já habilitou

O Bloco C preencheu os 46 `scope` com `side_effect` e `requires_approval`. Isso deixa de ser inferência: o Work Run consulta o scope da capability para saber **se aquele passo precisa de reserva de efeito e de aprovação**. Os helpers já existem em `capability_resolver` (`has_side_effect`, `requires_approval`, `max_calls_per_run`).

---

# 5. Separação de threads

```text
conversa:  chat:{company_id}:{session_id}     ← já existe (graph.py:841)
trabalho:  work:{company_id}:{run_id}         ← a criar
```

Hoje há uma única thread. A SPEC-053 §10.1 exige separação: um trabalho longo não pode poluir nem ser poluído pelo histórico de conversa.

---

# 6. Idempotência — o ponto mais delicado

Chave canônica (SPEC-053 §10.5):

```text
{company_id}:{run_id}:{step_id}:{action}:{payload_hash}
```

**`work_effects` como reserva, não como log.** O padrão correto é: reservar a chave **antes** de executar o efeito externo, com `UNIQUE`; se a reserva falhar, o efeito já foi feito. Isso resolve o caso real que existe hoje no Portal Worker: portal concluiu a ação e o worker morreu antes de gravar o status — na retomada, hoje, a ação repetiria.

Reconciliador para efeitos `reserved` sem confirmação após timeout.

---

# 7. Ordem de execução recomendada

| Bloco | Conteúdo | Depende de |
|---|---|---|
| **A** | 7 tabelas + evolução de `approval_requests` + RLS + FKs + índices | nada |
| **B** | Redis Streams + outbox dispatcher + Smith Worker + leases + heartbeat + recuperação + thread `work:` + HITL com `interrupt`/`resume` | **`SUPABASE_DB_URL`** |
| **C** | Bridges de Rotinas, Auxiliares, Portal Worker e Atendimento + usage events + UI de Trabalhos + cutover | A e B |

**O Bloco A pode começar imediatamente.** O Bloco B fica em gate até a variável existir.

---

# 8. Riscos

| Risco | Severidade | Mitigação |
|---|---|---|
| Checkpoint em memória | **Alta** | §1 — resolver antes do Bloco B |
| Duplicar efeito durante o cutover de rotinas | Alta | `work_effects` antes de qualquer bridge; dual-write curto |
| Worker novo competir com scheduler in-process | Alta | flag de corte; scheduler antigo desligado no mesmo deploy |
| Redis sem persistência perder fila | Média | outbox no Postgres é a fonte; Redis é só transporte |
| `portal_jobs` com 67 `needs_human` | Média | mapear para `waiting_approval` no backfill, não descartar |

---

# 9. Testes obrigatórios

Além do Broker Outcome Regression Pack (15/15 verde hoje):

- run sobrevive a restart do worker e retoma do último checkpoint;
- mesma `idempotency_key` duas vezes → **um** efeito;
- lease expirada é recuperada por outro worker sem duplicar;
- approval bloqueia de fato; `resume` sem approval válido falha;
- `fingerprint` divergente invalida aprovação (conteúdo mudou depois do aceite);
- cancelamento não desfaz efeito externo já confirmado;
- tenant A não lê nem retoma Work Run do tenant B;
- rotina e auxiliar executam por Work Run sem duplicar histórico.

---

# 10. Veredito

```text
READY_WITH_ONE_BLOCKER
```

O Bloco A está pronto para execução imediata. O Bloco B exige `SUPABASE_DB_URL` no `smith-api`.

## O que preciso do Founder

**Definir `SUPABASE_DB_URL` nas variáveis do serviço `smith-api` no EasyPanel**, com a connection string do pooler do Supabase em transaction mode (porta 6543).

Onde encontrar: painel do Supabase → *Project Settings* → *Database* → *Connection string* → aba **Transaction pooler**. É a string que começa com `postgresql://postgres.dcajcvlzcjbmyapmklil:...@...pooler.supabase.com:6543/postgres`.

**Não cole a string aqui no chat.** Adicione direto na variável do EasyPanel e me avise que está feito — eu confirmo pelo comportamento (a tabela `checkpoints` deixa de ficar zerada).

O código já está preparado: `prepare_threshold=None` para PgBouncer, pool com reciclagem e verificação de conexão.
