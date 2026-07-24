# SPEC-055 — Durable Work Runs, Queue, Checkpoints & HITL

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANÔNICA E AUTORIZADA PARA EXECUÇÃO — aprovada pelo Founder em 24/07/2026  
**Autoridade superior:** `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`, `SPEC-053-autobrokers-work-os-core-harness.md` e `SPEC-054-foundation-hardening-schema-governance.md`  
**Runtime preservado:** Smith + LangGraph/LangChain + FastAPI + Supabase/Postgres + Redis + Qdrant + MinIO  
**Nome oficial do agente central:** **AutoBrokers**  
**Escopo:** transformar trabalhos de várias etapas, Rotinas, Auxiliares, ações em Portais e aprovações humanas em execuções duráveis, retomáveis, idempotentes, observáveis e prontas para operação comercial real.  
**Natureza desta SPEC:** esta SPEC autoriza implementação, migrations, worker dedicado, APIs, UI operacional, integração com os motores existentes, deploy e ativação em produção, respeitando os gates definidos abaixo.  
**Documento preparatório:** a SPEC-054 e seu relatório de execução devem estar verdes nos itens bloqueadores de segurança antes de liberar side effects reais por este runtime.

---

# 0. Comando direto ao executor — Fable, Opus, Codex ou equivalente

Você está autorizado a **implementar integralmente esta SPEC em linha reta**.

Esta não é uma especificação de protótipo, laboratório, demonstração descartável ou versão que ficará meses em shadow mode. O resultado final desta execução deve ser a **versão operacional de lançamento** do plano de execução durável do AutoBrokers.

O executor deve:

1. ler a documentação obrigatória;
2. confirmar o código e o schema atuais;
3. implementar o modelo canônico;
4. migrar os motores existentes sem criar um segundo runtime;
5. executar testes e regressões;
6. fazer deploy;
7. ativar a funcionalidade no produto;
8. comprovar funcionamento real no dashboard e nos fluxos da corretora;
9. publicar o relatório final.

Não transformar esta tarefa em outra auditoria ampla. Investigações curtas são permitidas apenas para confirmar contratos concretos antes de editar.

## 0.1 Doutrina de lançamento

```text
Construir uma vez com padrão de produção.
Testar dentro da mesma execução.
Corrigir dentro da mesma execução.
Ativar ao final da mesma execução.
```

Não criar:

- `work_runs_v2`;
- “versão beta” paralela;
- worker provisório que será substituído depois;
- fila temporária;
- approvals falsos apenas para UI;
- artifacts falsos;
- outro scheduler;
- outro runtime de agentes;
- outra fonte de verdade de execução.

Feature flags são permitidas somente como mecanismo de rollback, emergência e ativação controlada durante a mesma iniciativa. Elas não podem ser usadas para declarar a entrega concluída deixando o novo runtime permanentemente desligado.

## 0.2 Número de blocos

A execução deve ocorrer em **três blocos macro**, o menor número compatível com segurança e rollback:

1. **Bloco A — Fundação durável:** schema, fila, worker, estado, leases, eventos, checkpoints e idempotência;
2. **Bloco B — Integração operacional:** HITL, chat, Rotinas, Auxiliares, Portais, APIs, UI e custos;
3. **Bloco C — Migração, ativação e lançamento:** backfill, corte do caminho canônico, regressões, deploy, operação real e documentação.

Com gates verdes, avançar automaticamente.

## 0.3 Saída obrigatória

Ao final devem existir e estar ativos:

- `work_runs` como fonte universal de verdade de execução;
- steps e attempts estruturados;
- fila Redis Streams com recuperação e fallback pelo banco;
- worker Smith dedicado e horizontalmente escalável;
- leases e heartbeats;
- checkpoints LangGraph separados de conversas;
- pausa, retomada, cancelamento e retry;
- HITL real com `interrupt()` e `Command(resume=...)`;
- approvals ligadas a run, step e side effect;
- ledger de side effects idempotentes;
- integração canônica com Rotinas, Auxiliares e Portal Worker;
- timeline operacional no dashboard;
- cards de trabalho no chat;
- inbox de aprovações funcional;
- observabilidade e custo por run;
- recuperação após restart comprovada;
- zero duplicação de envio/ação nos testes de falha;
- funcionamento validado na Amandus, Resulta e AutoFleet;
- relatório final publicado.

---

# 1. Ordem de leitura e autoridade

Antes de alterar código ou banco:

1. atualizar a `main`;
2. registrar o commit inicial;
3. ler `SPEC-052`;
4. ler `SPEC-053`;
5. ler `SPEC-054` e seu relatório final de execução, quando existir;
6. ler `ADR-001-runtime.md` e `ADR-002-vault.md`;
7. ler `SPEC-002` e `SPEC-019` apenas como histórico não conflitante;
8. ler o código real de Graph, Rotinas, Auxiliares, Portais, approvals, custo e Redis;
9. confirmar o schema vivo em modo read-only.

Comandos mínimos:

```bash
git fetch origin
git checkout main
git pull origin main
git rev-parse HEAD
git status --short
```

Ordem normativa:

```text
SPEC-052
→ SPEC-053
→ SPEC-054
→ SPEC-055
→ SPECs subordinadas posteriores
→ ADRs e documentos históricos quando não conflitarem
→ código atual apenas como estado de implementação
```

Em conflito, não inventar uma arquitetura intermediária.

---

# 2. Resultado de produto

O AutoBrokers deve deixar de tratar trabalho longo como uma chamada web que precisa terminar rapidamente.

O corretor poderá pedir, por exemplo:

- “Analise os atendimentos da semana e me entregue os gargalos.”
- “Prepare um relatório da operação.”
- “Entre no portal e recupere o documento.”
- “Crie uma rotina que faça isso todas as manhãs.”
- “Aguarde minha aprovação antes de enviar.”
- “Continue de onde parou.”
- “Cancele esse trabalho.”
- “Tente novamente somente a etapa que falhou.”

O produto deve responder com comportamento operacional, não apenas texto:

```text
Pedido
→ Work Run criado
→ plano/timeline visível
→ execução em background
→ aprovação quando necessária
→ retomada automática
→ resultado entregue
→ histórico e evidência preservados
```

## 2.1 Objetivos de negócio

Esta SPEC deve permitir:

- reduzir tempo de espera do usuário;
- executar trabalhos que duram minutos ou horas;
- sobreviver a restart e falha de rede;
- evitar reenvio de mensagens, boletos ou ações;
- permitir que uma pessoa aprove ou corrija antes do side effect;
- transformar Rotinas e Auxiliares em trabalhadores confiáveis;
- suportar aumento de corretoras sem aumentar fragilidade;
- medir custo e resultado de cada trabalho;
- preparar o lançamento comercial com operação confiável;
- criar a base para Skills, artifacts, relatórios e Research Intelligence.

## 2.2 Experiência de lançamento

Quando esta SPEC terminar, o corretor não verá uma “função em testes”.

Ele verá:

- trabalhos em andamento;
- percentual ou etapa atual;
- motivo quando algo aguarda aprovação;
- ações humanas claras;
- resultado ou falha em linguagem humana;
- opção de cancelar, tentar novamente ou abrir detalhes;
- continuidade mesmo após fechar o navegador;
- histórico por corretora.

---

# 3. Princípios invioláveis

1. **Smith continua sendo o único runtime cognitivo.**
2. **Supabase/Postgres é a fonte durável de verdade do trabalho.**
3. **Redis acelera fila, leases e sinalização; não é a única autoridade.**
4. **LangGraph guarda estado cognitivo e checkpoints; não substitui o catálogo operacional.**
5. **Conversa e trabalho usam threads diferentes.**
6. **Todo side effect precisa de idempotência.**
7. **Toda ação sensível precisa de autorização executável.**
8. **Approval textual no prompt não é HITL.**
9. **Run, step, attempt, approval, effect e event são objetos diferentes.**
10. **Rotina é gatilho, não execução universal.**
11. **Auxiliar é trabalhador de produto, não fila.**
12. **Portal Job permanece objeto especializado do Portal Worker, ligado ao Work Run.**
13. **Nenhum dado atravessa tenants.**
14. **Nenhum segredo entra em payload, checkpoint, evento ou log.**
15. **Retry não pode repetir side effect já confirmado.**
16. **O worker deve sobreviver a restart sem perder trabalho.**
17. **Código novo deve ser ativado ao final; não ficar eternamente em shadow.**
18. **Não apagar histórico durante esta SPEC.**
19. **Migração é expand-and-contract, com compatibilidade temporária e corte canônico.**
20. **Resultado do corretor é parte da Definition of Done.**

---

# 4. Estado atual que deve ser preservado

A implementação deve partir das peças existentes:

- grafo Smith `agent → tools → log`;
- `AsyncPostgresSaver` e tabelas de checkpoint;
- `thread_id={company_id}:{session_id}` para conversa;
- Capability Resolver;
- Tool Authority;
- Vault e `approval_requests`;
- `token_usage_logs` e callbacks de custo;
- `routine_engine` e `routine_runs`;
- `tenant_auxiliaries` e `auxiliary_runs`;
- `portal_jobs`, Portal Worker e `portal-evidence`;
- Redis já disponível;
- MinIO já disponível;
- LangSmith/tracing já disponível;
- chat streaming existente;
- isolamento por empresa ativa;
- triggers técnicos de WhatsApp;
- idempotência específica já existente na cobrança.

## 4.1 Lacunas atuais

- checkpointer é de conversa, não de trabalho;
- inexistência de `work_runs` universal;
- inexistência de step/attempt durável;
- inexistência de fila de trabalho durável distribuída;
- scheduler e runs ainda dependem de processo in-process;
- HITL real ausente;
- approvals existentes não retomam o grafo;
- cancelamento mid-flight ausente;
- progresso estruturado incompleto;
- side effects não possuem ledger universal;
- `routine_runs`, `auxiliary_runs` e `portal_jobs` são histórias paralelas;
- custo não é consolidado por Work Run;
- restart pode exigir reprocessamento manual;
- graph/workflow versioning para runs pausados não está formalizado.

---

# 5. Arquitetura canônica

```text
Chat / Rotina / Auxiliar / API / Portal / Admin
                    │
                    ▼
             Work Run Service
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
 Supabase/Postgres        Queue Outbox
 fonte durável                 │
          │                    ▼
          │              Redis Streams
          │                    │
          ▼                    ▼
  LangGraph Checkpoint ◀ Smith Worker Pool
          │                    │
          ├── Tools/Skills     ├── Portal Worker
          ├── Approvals        ├── HTTP/MCP
          ├── Side Effects     ├── LLM/Subagents
          └── Events           └── Delivery
                    │
                    ▼
          Timeline + resultado + artifacts
```

## 5.1 Autoridades

| Responsabilidade | Autoridade |
|---|---|
| estado comercial da execução | `work_runs` |
| etapas | `work_steps` |
| tentativas | `work_attempts` |
| timeline auditável | `work_events` |
| side effects | `work_effects` |
| aprovação | `approval_requests` evoluída |
| checkpoint cognitivo | LangGraph/Postgres checkpointer |
| fila transitória | Redis Streams |
| publicação confiável na fila | `work_queue_outbox` |
| arquivos/resultados futuros | Artifact Hub da SPEC-057 |
| secrets | Vault |
| capabilities | Capability Registry |
| custo | token/usage logs ligados ao run |

## 5.2 Não criar tabelas concorrentes

- não criar `work_approvals`; evoluir `approval_requests`;
- não criar `work_portal_jobs`; ligar `portal_jobs`;
- não criar `work_routines`; ligar `routines`;
- não criar `work_auxiliaries`; ligar `tenant_auxiliaries`;
- não criar outro checkpoint store;
- não criar outro audit log universal fora de `work_events`.

---

# 6. Quando criar um Work Run

Nem toda mensagem do chat precisa virar uma execução em background.

## 6.1 Permanece como resposta conversacional

- pergunta simples;
- explicação sem side effect;
- busca rápida que conclui dentro do request;
- resposta usando RAG sem workflow longo;
- cálculo simples;
- confirmação curta.

## 6.2 Deve criar Work Run

- tarefa com mais de uma etapa relevante;
- chamada externa com side effect;
- trabalho estimado acima do limite síncrono configurado;
- execução de Rotina;
- execução de Auxiliar;
- criação de relatório/artifact;
- portal autenticado;
- aprovação humana;
- retry necessário;
- delegação assíncrona;
- tarefa recorrente;
- tarefa que precisa sobreviver ao fechamento do navegador;
- trabalho solicitado explicitamente para segundo plano.

## 6.3 Fast path governado

É permitido executar um Work Run curto imediatamente pelo worker e devolver o resultado na mesma experiência de chat.

Mesmo nesse caso:

- o run é criado;
- a idempotência existe;
- o custo é medido;
- o histórico é persistido;
- o side effect passa pelo gate;
- a conclusão não depende do request permanecer aberto.

---

# 7. Modelo de dados canônico

Todas as migrations devem seguir o cabeçalho APPLY/VERIFY/ROLLBACK da SPEC-054.

## 7.1 `work_runs`

Campos mínimos:

```text
id uuid PK
company_id uuid NOT NULL FK companies
requester_user_id uuid NULL
requester_agent_id uuid NULL
parent_run_id uuid NULL FK work_runs
correlation_id uuid NOT NULL
source_type text NOT NULL
source_id text NULL
outcome_type text NOT NULL
outcome_title text NOT NULL
outcome_description text NULL
status text NOT NULL
priority smallint NOT NULL DEFAULT 50
risk_level text NOT NULL DEFAULT 'low'
visibility text NOT NULL DEFAULT 'company'
owner_user_id uuid NULL
runtime_kind text NOT NULL DEFAULT 'smith'
workflow_key text NOT NULL
workflow_version text NOT NULL
thread_id text NOT NULL UNIQUE
graph_version text NOT NULL
input_payload jsonb NOT NULL DEFAULT '{}'
input_fingerprint text NOT NULL
result_summary text NULL
result_payload jsonb NOT NULL DEFAULT '{}'
error_code text NULL
error_message text NULL
progress_percent smallint NOT NULL DEFAULT 0
current_step_key text NULL
idempotency_key text NOT NULL
cost_budget_brl numeric NULL
cost_actual_brl numeric NOT NULL DEFAULT 0
currency text NOT NULL DEFAULT 'BRL'
requested_at timestamptz NOT NULL
queued_at timestamptz NULL
started_at timestamptz NULL
paused_at timestamptz NULL
finished_at timestamptz NULL
cancel_requested_at timestamptz NULL
cancelled_at timestamptz NULL
next_attempt_at timestamptz NULL
lease_owner text NULL
lease_token uuid NULL
lease_expires_at timestamptz NULL
heartbeat_at timestamptz NULL
created_at timestamptz NOT NULL
updated_at timestamptz NOT NULL
```

### Constraints

- unique `(company_id, idempotency_key)`;
- `progress_percent` entre 0 e 100;
- `cost_budget_brl >= 0`;
- `cost_actual_brl >= 0`;
- `company_id` imutável após criação;
- `thread_id = work:{company_id}:{run_id}` gerado server-side;
- source e requester devem pertencer ao tenant quando aplicável;
- payload não pode conter segredo;
- status validado por check/enum canônico.

### `source_type`

Valores iniciais:

- `chat`;
- `routine`;
- `auxiliary`;
- `portal`;
- `api`;
- `admin`;
- `system`;
- `retry`;
- `child_run`.

## 7.2 `work_steps`

Campos mínimos:

```text
id uuid PK
work_run_id uuid NOT NULL FK work_runs
company_id uuid NOT NULL FK companies
step_key text NOT NULL
ordinal integer NOT NULL
name text NOT NULL
step_type text NOT NULL
status text NOT NULL
risk_level text NOT NULL DEFAULT 'low'
capability_key text NULL
tool_name text NULL
input_summary jsonb NOT NULL DEFAULT '{}'
output_summary jsonb NOT NULL DEFAULT '{}'
checkpoint_id text NULL
approval_request_id uuid NULL
idempotency_key text NOT NULL
attempt_count integer NOT NULL DEFAULT 0
max_attempts integer NOT NULL DEFAULT 1
timeout_seconds integer NULL
started_at timestamptz NULL
finished_at timestamptz NULL
created_at timestamptz NOT NULL
updated_at timestamptz NOT NULL
```

Constraints:

- unique `(work_run_id, step_key)`;
- unique `(company_id, idempotency_key)` quando representar side effect;
- `company_id` igual ao run;
- ordinal estável por workflow version;
- step concluído não volta a `running` sem nova attempt formal.

## 7.3 `work_attempts`

Cada tentativa de step deve registrar:

```text
id
company_id
work_run_id
work_step_id
attempt_number
worker_id
lease_token
status
started_at
finished_at
error_class
error_code
error_message_redacted
retryable
retry_after
metrics jsonb
trace_id
created_at
```

Unique `(work_step_id, attempt_number)`.

## 7.4 `work_events`

Timeline append-only:

```text
id bigserial/uuid
company_id
work_run_id
work_step_id nullable
attempt_id nullable
event_type
actor_type
actor_id nullable
severity
message_human
payload_redacted jsonb
created_at
```

Tipos mínimos:

- `run.created`;
- `run.queued`;
- `run.leased`;
- `run.started`;
- `run.progress`;
- `run.paused`;
- `run.resumed`;
- `run.cancel_requested`;
- `run.cancelled`;
- `run.succeeded`;
- `run.failed`;
- `step.started`;
- `step.completed`;
- `step.failed`;
- `step.retry_scheduled`;
- `approval.requested`;
- `approval.approved`;
- `approval.rejected`;
- `approval.edited`;
- `effect.reserved`;
- `effect.confirmed`;
- `effect.unknown`;
- `delivery.completed`;
- `worker.recovered`.

Não registrar:

- senha;
- token;
- cookie;
- PDF integral;
- conteúdo sensível desnecessário;
- payload bruto de cliente quando resumo é suficiente.

## 7.5 `work_effects`

Ledger de side effects:

```text
id
company_id
work_run_id
work_step_id
effect_type
provider
resource_key
idempotency_key
request_fingerprint
status
provider_reference
response_fingerprint
response_summary
reserved_at
started_at
confirmed_at
failed_at
unknown_at
created_at
updated_at
```

Unique `(company_id, idempotency_key)`.

Estados:

- `reserved`;
- `executing`;
- `confirmed`;
- `failed_retryable`;
- `failed_terminal`;
- `unknown`;
- `compensated`.

Regra:

```text
Antes do side effect: reservar.
Depois do side effect: confirmar com referência do provider.
Se a resposta se perder: status unknown; reconciliar antes de repetir.
```

## 7.6 `work_queue_outbox`

Evita dual-write inconsistente entre Postgres e Redis.

Campos:

```text
id
company_id
work_run_id
event_kind
payload_minimal jsonb
status
attempts
next_attempt_at
published_at
redis_entry_id
created_at
updated_at
```

A criação do run e a linha de outbox devem ocorrer na mesma transação/RPC server-side.

## 7.7 Evolução de `approval_requests`

Adicionar de forma expand-only:

```text
work_run_id uuid NULL
work_step_id uuid NULL
idempotency_key text NULL
action_fingerprint text NULL
decision text NULL
decision_payload jsonb DEFAULT '{}'
requested_preview jsonb DEFAULT '{}'
requested_at timestamptz
expires_at timestamptz NULL
resolved_at timestamptz NULL
resolved_by_user_id uuid NULL
revoked_at timestamptz NULL
resume_token_hash text NULL
```

Não armazenar resume token em texto puro.

Unique de aprovação ativa por `(company_id, idempotency_key)`.

## 7.8 Ligações com estruturas existentes

Adicionar `work_run_id` onde necessário:

- `routine_runs`;
- `auxiliary_runs`;
- `portal_jobs`;
- `approval_requests`;
- `token_usage_logs`;
- logs de entrega relevantes.

Essas colunas são compatibilidade e lineage, não criam novas autoridades.

---

# 8. Máquina de estados

## 8.1 Estados de `work_runs`

```text
created
queued
leased
running
waiting_approval
waiting_input
paused
retry_scheduled
cancel_requested
cancelled
succeeded
failed
manual_review
dead_letter
```

## 8.2 Transições permitidas

```text
created → queued
queued → leased
leased → running
leased → queued              lease expirou antes de iniciar
running → waiting_approval
running → waiting_input
running → paused
running → retry_scheduled
running → cancel_requested
running → succeeded
running → failed
running → manual_review
waiting_approval → queued    aprovado e retomado
waiting_approval → cancelled rejeitado/cancelado
waiting_approval → failed    expirado conforme policy
waiting_input → queued       resposta recebida
waiting_input → cancelled
paused → queued
retry_scheduled → queued
cancel_requested → cancelled
cancel_requested → manual_review side effect incerto
failed → queued              retry manual permitido
manual_review → queued       reconciliação autoriza
manual_review → succeeded    ação já confirmada externamente
manual_review → cancelled
queued/leased → cancel_requested
```

Transições fora da tabela devem falhar.

## 8.3 Estados de step

```text
pending
ready
running
waiting_approval
waiting_external
retry_scheduled
skipped
succeeded
failed
cancelled
manual_review
```

## 8.4 Regras terminais

- `succeeded`, `failed`, `cancelled` e `dead_letter` são terminais;
- reexecução cria nova attempt ou novo run explícito;
- nunca editar histórico para fingir que uma falha não aconteceu;
- retry manual de run terminal cria lineage `parent_run_id` quando a semântica exigir novo trabalho.

---

# 9. Criação atômica do Work Run

Criar uma função/service canônica:

```text
create_work_run(context, outcome, workflow, source, idempotency_key)
```

Responsabilidades:

1. validar empresa e requester;
2. validar capability;
3. validar orçamento e risco;
4. sanitizar payload;
5. calcular fingerprint;
6. inserir ou recuperar run idempotente;
7. criar steps iniciais quando o workflow já for conhecido;
8. criar evento `run.created`;
9. criar outbox `work.enqueue`;
10. retornar o mesmo run se a mesma key já existir.

A criação deve ocorrer em uma transação server-side ou RPC interna não pública.

Não aceitar `company_id`, papel, risco ou capability do client como autoridade.

---

# 10. Fila durável com Redis Streams

## 10.1 Decisão

Usar Redis Streams e consumer groups, preservando Supabase como autoridade durável.

Nomes sugeridos:

```text
autobrokers:work:v1
autobrokers:work:events:v1
consumer group: smith-workers-v1
```

Não usar Redis Pub/Sub como fila principal, porque mensagens fire-and-forget não oferecem a recuperação necessária.

## 10.2 Payload da fila

Mínimo possível:

```json
{
  "work_run_id": "uuid",
  "company_id": "uuid",
  "queue_version": 1,
  "reason": "created|retry|resume|recovery",
  "not_before": "timestamp"
}
```

Nunca colocar:

- prompt integral;
- documento;
- senha;
- token;
- dados pessoais completos;
- payload operacional desnecessário.

O worker lê os detalhes do Supabase após validar lease e tenant.

## 10.3 Outbox dispatcher

Criar processo no worker ou serviço leve que:

1. busca outbox `pending` com `FOR UPDATE SKIP LOCKED` ou RPC equivalente;
2. publica no Stream;
3. grava `redis_entry_id`;
4. marca `published`;
5. tenta novamente com backoff em falha;
6. nunca perde o run se Redis estiver indisponível.

## 10.4 Consumer group

O worker deve:

- usar `XREADGROUP`;
- identificar-se por `worker_id` único;
- processar com limite de concorrência;
- `XACK` somente depois de estado durável coerente;
- monitorar PEL;
- usar `XAUTOCLAIM`/equivalente para entradas abandonadas;
- aplicar trimming sem apagar entradas ainda necessárias;
- expor lag, pending e idade da entrada mais antiga.

## 10.5 Fallback pelo banco

Se Redis estiver indisponível:

- criação de run continua gravando no Postgres;
- outbox permanece pendente;
- worker de recuperação pode reivindicar runs `queued` cuja outbox não avançou após o limite;
- quando Redis voltar, o dispatcher republica;
- idempotência impede execução dupla.

---

# 11. Smith Worker de produção

## 11.1 Serviço

Criar um processo dedicado, preferencialmente usando a mesma imagem/repositório do backend com comando próprio:

```text
autobrokers-smith-worker
```

Não criar outro cérebro.

O worker importa:

- serviços Smith;
- builders de grafo;
- Capability Resolver;
- Vault;
- Tool Authority;
- custos;
- tracing;
- repositories canônicos.

## 11.2 Responsabilidades

- consumir fila;
- adquirir lease;
- validar status;
- montar grafo versionado;
- executar ou retomar;
- emitir eventos;
- atualizar heartbeat;
- respeitar cancelamento;
- registrar attempt;
- lidar com interrupt;
- confirmar effects;
- consolidar resultado e custo;
- liberar lease;
- mover para retry/manual review/dead letter.

## 11.3 Não pertence ao worker

- decidir policy comercial fora dos manifests;
- armazenar secrets próprios;
- criar outro RAG;
- criar outro scheduler;
- escrever diretamente em tabelas sem repository/context;
- manter estado apenas em memória;
- reconhecer run somente pelo Redis.

## 11.4 Concorrência

Configurações mínimas:

```text
WORKER_CONCURRENCY_TOTAL
WORKER_CONCURRENCY_PER_TENANT
WORKER_CONCURRENCY_PORTAL
WORKER_CONCURRENCY_LLM
WORKER_CONCURRENCY_SIDE_EFFECT
```

Regras:

- evitar que uma corretora consuma todo o worker;
- alta prioridade não pode causar starvation permanente;
- portals podem ter limites menores;
- cada tool/provider pode declarar rate limit;
- fila deve suportar prioridade via streams separados ou seleção governada, sem criar vários runtimes.

---

# 12. Lease, heartbeat e recuperação

## 12.1 Aquisição de lease

Uma RPC interna atômica deve:

1. verificar status elegível;
2. verificar lease expirado ou ausente;
3. gerar `lease_token`;
4. registrar `lease_owner`;
5. definir `lease_expires_at`;
6. alterar para `leased`;
7. criar attempt;
8. retornar o run.

Toda atualização posterior do worker deve incluir:

```text
WHERE id = run_id
AND lease_token = token
AND company_id = company_id
```

## 12.2 Heartbeat

- heartbeat periódico menor que 1/3 do lease;
- renova lease somente se attempt continua ativa;
- failure de heartbeat não cancela imediatamente o processo, mas impede commit final depois de perder lease;
- worker que perdeu lease deve parar antes do próximo side effect.

## 12.3 Recuperação

Recovery scanner identifica:

- `leased/running` com lease expirado;
- attempts sem heartbeat;
- runs aguardando retry;
- outbox pendente;
- approvals expiradas;
- effects `unknown`.

Decisão:

- sem side effect iniciado: reenfileirar;
- side effect reservado, não executado: reenfileirar;
- side effect confirmado: avançar sem repetir;
- side effect `unknown`: `manual_review` ou reconciliador do provider;
- graph checkpoint válido: retomar;
- checkpoint incompatível: usar migration de estado ou manual review, nunca recomeçar cegamente.

---

# 13. Thread e checkpoint LangGraph

## 13.1 Separação obrigatória

Conversa:

```text
chat:{company_id}:{session_id}
```

Trabalho:

```text
work:{company_id}:{work_run_id}
```

Não reutilizar thread de conversa como thread do trabalho.

## 13.2 Configuração

Toda execução deve usar:

```python
config = {
    "configurable": {
        "thread_id": work_run.thread_id,
        "company_id": str(work_run.company_id),
        "work_run_id": str(work_run.id),
        "workflow_version": work_run.workflow_version,
    }
}
```

## 13.3 Graph versioning

Runs pausados podem existir enquanto o código evolui.

Obrigatório:

- persistir `workflow_key`, `workflow_version` e `graph_version`;
- resolver o builder por versão;
- não renomear/remover nodes usados por runs ativos sem migration de checkpoint;
- manter compatibilidade de versões com runs não terminais;
- publicar migration de state quando schema mudar;
- impedir resume com versão incompatível e mensagem genérica;
- encaminhar incompatibilidade para `manual_review`.

## 13.4 Side effects e checkpoints

Como um node pode recomeçar do início ao retomar:

- nenhum side effect não idempotente antes de `interrupt()`;
- side effect deve estar em node/task isolado;
- ledger deve ser consultado antes de executar;
- resultado confirmado deve ser reutilizado;
- efeitos devem ter chave determinística.

---

# 14. Work Graph canônico

A implementação pode aproveitar o grafo atual, mas deve separar um grafo de trabalho versionado do loop conversacional sem criar runtime paralelo.

Estrutura conceitual:

```text
START
→ load_run_context
→ plan_or_load_steps
→ select_next_step
→ preflight_policy
→ approval_gate? ── interrupt
→ execute_step
→ verify_step
→ record_effects
→ update_progress
→ more_steps? ── select_next_step
→ compose_result
→ finalize_run
→ END
```

## 14.1 Nodes mínimos

### `load_run_context`

- recarrega run e tenant;
- verifica lease;
- monta Context Assembly conforme SPEC-052;
- carrega somente dados necessários;
- não injeta secret no state.

### `plan_or_load_steps`

- usa workflow versionado;
- materializa steps estáveis;
- não replaneja steps já executados sem evento explícito;
- mudanças humanas geram nova versão/branch de plano auditável.

### `preflight_policy`

- capability;
- entitlement;
- conexão;
- risk;
- budget;
- Vault;
- idempotency;
- approval requirement.

### `approval_gate`

- cria/reutiliza approval;
- chama `interrupt()` com payload JSON serializável;
- não executa side effect antes da decisão;
- ao retomar, valida fingerprint e autorização.

### `execute_step`

- cria attempt;
- usa tool/agent/subagent/portal apropriado;
- respeita timeout e cancel token;
- não captura secret em output.

### `verify_step`

- valida resultado técnico;
- confirma evidência;
- classifica retryable/terminal/unknown;
- não aceita texto otimista como prova de side effect.

### `finalize_run`

- consolida resultado;
- calcula custo;
- grava evento terminal;
- agenda delivery quando aplicável;
- libera lease;
- emite atualização para UI.

---

# 15. HITL real e approvals

## 15.1 Reutilizar `approval_requests`

A tabela existente é a autoridade física de approvals e será evoluída.

O endpoint atual de criação/listagem deve ser preservado e ampliado.

## 15.2 Tipos de decisão

- `approve`;
- `reject`;
- `edit_and_approve`;
- `request_changes`;
- `cancel_run`.

## 15.3 Preview obrigatório

Toda approval deve mostrar em linguagem humana:

- o que será feito;
- por que será feito;
- para qual corretora;
- sistema/canal de destino;
- dados que serão usados;
- risco;
- custo estimado;
- efeito irreversível;
- prazo de validade;
- o que ocorre se rejeitar.

Exemplos:

```text
Enviar uma mensagem de cobrança para 8 clientes da Resulta.
Baixar um boleto no portal Allianz usando a conta X.
Publicar um relatório compartilhável.
Executar uma chamada HTTP de escrita.
```

Não mostrar segredo ou payload bruto.

## 15.4 Fingerprint

A approval autoriza um conteúdo específico.

Calcular fingerprint a partir de:

- action type;
- destination;
- normalized payload;
- provider;
- resource;
- quantidade;
- tenant;
- workflow version.

Se qualquer item material mudar:

- invalidar approval;
- criar nova solicitação;
- não reutilizar decisão antiga.

## 15.5 Autorização humana

Antes de resolver approval:

- sessão válida;
- vínculo ativo na empresa;
- papel autorizado;
- usuário não pode aprovar em empresa inativa;
- approval ainda pending;
- fingerprint ainda válido;
- run ainda aguarda aquela approval;
- risco compatível com o papel;
- decisão auditada.

## 15.6 Resume

Após decisão válida:

1. gravar decisão;
2. criar evento;
3. atualizar run para `queued`;
4. criar outbox `resume`;
5. worker adquire lease;
6. invocar grafo com `Command(resume=decision_payload)`;
7. continuar do checkpoint.

Nunca executar o resume diretamente dentro do request HTTP da aprovação.

## 15.7 Expiração e revogação

- approvals de ação externa devem expirar;
- approval pode ser revogada antes do side effect;
- após efeito confirmado, revogação não apaga o histórico;
- expiração segue policy por risco;
- approval expirada não retoma automaticamente.

---

# 16. Cancelamento, pausa e input humano

## 16.1 Cancelamento

Endpoint de cancelamento:

- valida tenant e papel;
- altera para `cancel_requested`;
- emite sinal Redis;
- worker verifica entre nodes e antes de effects;
- tools longas recebem cancel token quando possível;
- process group de MCP/browser deve ser encerrado;
- se side effect estiver em estado incerto, ir para `manual_review`.

## 16.2 Pausa

Pausa voluntária:

- somente em boundaries seguras;
- não interrompe transação externa no meio;
- salva checkpoint;
- libera lease;
- status `paused`;
- retoma por enqueue.

## 16.3 `waiting_input`

Usar quando o sistema precisa de uma informação, não de aprovação.

Exemplo:

- selecionar período do relatório;
- indicar seguradora;
- corrigir dado ausente;
- escolher canal.

A resposta deve ser validada e injetada por `Command(resume=...)` ou atualização de estado governada.

---

# 17. Retry policy

## 17.1 Classificação de erro

- `transient_network`;
- `provider_rate_limit`;
- `provider_unavailable`;
- `timeout`;
- `auth_expired`;
- `validation_error`;
- `policy_denied`;
- `approval_rejected`;
- `business_not_found`;
- `side_effect_unknown`;
- `code_error`;
- `checkpoint_incompatible`.

## 17.2 Retry automático

Permitido para erros transitórios e quando o effect ledger prova que não houve conclusão.

Backoff configurável:

```text
base_delay
multiplier
max_delay
jitter
max_attempts
```

## 17.3 Sem retry automático

- autenticação/credencial expirada sem reconexão;
- policy negada;
- approval rejeitada;
- validação de negócio;
- side effect unknown sem reconciliador;
- checkpoint incompatível;
- erro terminal do provider.

## 17.4 Dead letter

Um run só entra em `dead_letter` quando:

- excedeu tentativas;
- falhou recuperação automática;
- precisa de investigação técnica;
- não há risco de side effect oculto não tratado.

Dead letter deve aparecer no Admin mínimo e gerar alerta.

---

# 18. Idempotência universal

## 18.1 Camadas

### Run

Unique `(company_id, idempotency_key)`.

Exemplos:

- rotina: `routine:{routine_id}:{scheduled_at}`;
- auxiliar manual: `auxiliary:{installation_id}:{client_request_id}`;
- portal: `portal:{company_id}:{journey}:{business_key}`;
- chat: `chat:{session_id}:{message_id}:{outcome}`;
- approval resume: `resume:{approval_id}:{decision_version}`.

### Step

```text
{run_id}:{step_key}:{semantic_input_hash}
```

### Effect

```text
{company_id}:{provider}:{effect_type}:{business_resource}:{semantic_action_hash}
```

## 18.2 Effect reservation

Fluxo obrigatório:

```text
BEGIN
→ insert work_effects reserved ON CONFLICT
→ se confirmed: reutilizar resultado
→ se executing recente: não duplicar
→ se unknown: reconciliar/manual review
→ marcar executing
COMMIT
→ chamar provider
→ persistir provider_reference e confirmed
```

## 18.3 Reconciliadores

Providers críticos devem possuir estratégia de consulta:

- WhatsApp: message ID/status;
- Portal: protocolo/documento/hash;
- e-mail: provider message ID;
- HTTP: idempotency header/provider key;
- delivery: receipt;
- billing: recibo e modo.

Sem possibilidade de reconciliação, action deve permanecer `unknown` e exigir decisão humana.

## 18.4 Sem promessa falsa

A SPEC busca efeito **praticamente único/effectively-once**, não promete exactly-once distribuído impossível de provar.

---

# 19. Integração com Rotinas

## 19.1 Regra canônica

A Rotina continua sendo scheduler/gatilho.

Ao vencer `next_run_at`:

1. claim atômico da ocorrência;
2. calcular idempotency key;
3. criar/reutilizar Work Run;
4. criar `routine_runs` compatível ligado ao `work_run_id`;
5. atualizar próxima ocorrência;
6. Work Run executa pelo worker;
7. status final é projetado de volta em `routine_runs` durante compatibilidade.

## 19.2 Corte de autoridade

Após migração:

- `work_runs` é a autoridade de execução;
- `routine_runs` permanece como projeção/compatibilidade para UI e histórico;
- código novo não executa cérebro diretamente dentro do scheduler;
- scheduler não faz trabalho pesado;
- scheduler apenas cria o Work Run.

## 19.3 Recuperação

Se scheduler reiniciar após criar o run e antes de atualizar rotina:

- mesma idempotency key recupera o mesmo run;
- nenhuma ocorrência duplicada;
- reconciliation job corrige o link.

---

# 20. Integração com Auxiliares

## 20.1 Regra canônica

Auxiliar instalado pode ser executado:

- manualmente;
- por Rotina;
- pelo chat;
- por evento futuro;
- por Admin autorizado.

Toda execução cria Work Run.

## 20.2 `auxiliary_runs`

Durante compatibilidade:

- adicionar `work_run_id`;
- criar row ligada ao run;
- projetar status;
- impedir execução direta paralela;
- preservar histórico.

A consolidação final da fábrica de Auxiliares pertence à SPEC-058, mas desde esta SPEC a execução universal deve ser Work Run.

## 20.3 Contexto do Auxiliar

Work Run recebe:

- tenant auxiliary ID;
- template/version;
- configuração efetiva;
- Agent/subagent/executor escolhido;
- capabilities;
- conexões;
- budget;
- visibilidade e owner.

Não copiar secrets para `input_payload`.

---

# 21. Integração com Portal Worker

## 21.1 Preservar Portal Worker

Portal Worker é executor especializado e não deve ser absorvido por um browser genérico.

## 21.2 Orquestração

```text
Work Step portal
→ approval/preflight
→ reservar effect
→ criar/reutilizar portal_job ligado ao work_run_id/step_id
→ worker de portal processa
→ portal_job atualiza
→ bridge emite work_event
→ Smith Work Run retoma
→ verifica resultado/evidência
```

## 21.3 Estados

Mapear:

- `queued/running/done/failed/needs_human` de portal;
- para `waiting_external/succeeded/failed/waiting_input/manual_review` do step.

## 21.4 HITL do Portal

`needs_human` deve criar ou ligar uma solicitação humana apropriada:

- CAPTCHA;
- 2FA;
- confirmação de dados;
- intervenção em tela;
- credencial expirada.

Não usar approval de side effect quando o problema é input técnico; usar `waiting_input`/human task apropriada.

## 21.5 Idempotência

`portal_jobs` recebe:

- `work_run_id`;
- `work_step_id`;
- `idempotency_key`;
- unique tenant-scoped;
- provider/business reference.

Antes de repetir journey, verificar resultado/evidência já existente.

---

# 22. Integração com chat principal

## 22.1 Criação

Quando Outcome Router detectar trabalho durável:

- cria Work Run;
- envia resposta curta:

```text
Estou executando esse trabalho. Você pode acompanhar abaixo.
```

- renderiza Work Run Card.

## 22.2 Work Run Card

Deve mostrar:

- título humano;
- status humano;
- etapa atual;
- progresso;
- início;
- estimativa quando confiável;
- custo somente quando relevante;
- botão “Ver detalhes”;
- botão “Cancelar” quando permitido;
- botão de approval quando aguardando;
- resultado quando concluído.

## 22.3 Atualização

Preferência:

- SSE ou stream de eventos autenticado;
- fallback por polling;
- nenhum dado de outro tenant;
- reconexão após refresh;
- cursor por evento.

## 22.4 Resposta final

Ao concluir:

- mensagem no chat;
- resumo útil;
- links para resultados/artifacts quando existirem;
- próximos passos;
- não despejar log técnico.

---

# 23. UI operacional tenant-facing

Esta SPEC deve entregar a UX mínima de produção. Não esperar a SPEC-061 do Portal Admin.

## 23.1 Página “Trabalhos”

Criar ou consolidar no dashboard:

- Em andamento;
- Aguardando você;
- Concluídos;
- Falharam;
- Cancelados.

Filtros:

- período;
- origem;
- Auxiliar;
- Rotina;
- status;
- usuário;
- risco.

## 23.2 Detalhe do trabalho

Mostrar:

- título e objetivo;
- status em linguagem humana;
- timeline;
- etapas;
- approvals;
- resultados;
- erros humanos;
- tentativas;
- custo, se permitido;
- origem;
- responsável;
- ações disponíveis.

Logs técnicos ficam em seção avançada e redigida.

## 23.3 Inbox de aprovações

- pendentes primeiro;
- preview claro;
- aprovar;
- editar e aprovar;
- rejeitar;
- pedir alteração;
- expiração;
- histórico.

## 23.4 Estados vazios

A UI deve explicar o valor:

> “Quando o AutoBrokers executar relatórios, rotinas, pesquisas ou tarefas operacionais, você acompanhará tudo aqui.”

Não mostrar nomenclatura de infraestrutura como lease, PEL ou checkpoint ao corretor.

---

# 24. APIs de produção

Rotas sugeridas, adaptadas à arquitetura existente:

```text
POST   /api/work-runs
GET    /api/work-runs
GET    /api/work-runs/:id
GET    /api/work-runs/:id/events
GET    /api/work-runs/:id/stream
POST   /api/work-runs/:id/cancel
POST   /api/work-runs/:id/pause
POST   /api/work-runs/:id/resume
POST   /api/work-runs/:id/retry
GET    /api/work-approvals
GET    /api/work-approvals/:id
POST   /api/work-approvals/:id/decision
```

## 24.1 Contratos

- company sempre derivada da sessão;
- resposta nunca inclui secret;
- payloads validados por schema;
- listagem paginada;
- cursor de eventos;
- idempotency key em criação/comandos;
- ETag/version para impedir decisão concorrente;
- status HTTP coerente;
- erro humano separado de `error_code` técnico;
- Admin global usa rota/guard próprio.

## 24.2 API interna worker

Evitar expor comandos internos na internet quando o worker pode falar diretamente com DB/Redis.

Se endpoint interno for inevitável:

- autenticação service-to-service;
- audience;
- nonce/replay protection;
- rede restrita;
- nenhum segredo em URL;
- audit.

---

# 25. Custos e orçamento

## 25.1 Ligação

Adicionar `work_run_id` e `work_step_id` aos logs de uso relevantes.

Todo callback de LLM/tool deve receber contexto do run.

## 25.2 Orçamento

Antes e durante execução:

- estimativa inicial quando possível;
- budget da Skill/Auxiliar/tenant;
- custo acumulado;
- alert threshold;
- hard limit;
- approval para aumento acima da policy;
- nunca continuar indefinidamente por loop de retry.

## 25.3 Exibição

No tenant:

- não poluir tarefas comuns com custo técnico;
- mostrar quando exceder limite, exigir aprovação ou integrar ao plano.

No Admin:

- custo por run;
- por tenant;
- por origem;
- por workflow;
- por model/tool;
- anomalias.

Moeda operacional padrão: `BRL`, sem impedir providers faturados em outra moeda no ledger interno.

---

# 26. Segurança e isolamento

## 26.1 Tenant

Todas as novas tabelas:

- `company_id` obrigatório quando tenant-scoped;
- FK;
- índices company-first;
- RLS conforme classe;
- repository guard;
- testes Resulta × AutoFleet;
- work run de uma empresa nunca pode referenciar step/effect/approval de outra.

## 26.2 Secrets

Proibido persistir em run/checkpoint/event:

- API keys;
- senha de portal;
- cookies;
- session state integral;
- bearer token;
- passkey;
- refresh token.

Persistir apenas referências de Vault.

## 26.3 Input não confiável

Tool output, web, MCP e documentos são dados não confiáveis.

- não aceitar instruções embutidas como policy;
- não permitir que output altere company/capability;
- sanitizar erro;
- limitar tamanho;
- classificar origem.

## 26.4 Approval e IDOR

Toda ação por ID valida:

- company;
- membership;
- role;
- ownership/visibility;
- status;
- version;
- fingerprint.

## 26.5 Auditoria

Eventos críticos são append-only e não podem ser alterados pelo tenant.

---

# 27. Observabilidade

## 27.1 Métricas mínimas

- runs criados/concluídos/falhos;
- duração p50/p95/p99;
- tempo em fila;
- tempo aguardando humano;
- retries;
- dead letters;
- effects unknown;
- duplicações evitadas;
- lease expirado;
- Redis lag/Pending Entries;
- worker heartbeat;
- custo por run;
- taxa de aprovação/rejeição;
- jobs por tenant;
- erro por workflow/tool/provider.

## 27.2 Tracing

LangSmith/trace deve incluir tags:

```text
company_id
work_run_id
work_step_id
attempt_id
workflow_key
workflow_version
source_type
risk_level
```

Sem dados sensíveis.

## 27.3 Alertas

P0:

- cross-tenant guard falhou;
- efeito unknown de alto risco;
- fila sem consumer;
- outbox acumulando;
- worker sem heartbeat;
- approval retomada com fingerprint divergente;
- run preso além do SLA;
- dead letter de portal/cobrança;
- repetição detectada de side effect.

---

# 28. Retenção e privacidade

Esta SPEC não deve apagar histórico existente.

Adicionar campos/contratos:

- `retention_class`;
- `contains_pii`;
- `redaction_status`;
- `expires_at` quando aplicável.

Política de purge completa deve ser governada posteriormente com jurídico/LGPD.

Enquanto isso:

- eventos preservam somente metadados necessários;
- payload detalhado é minimizado;
- artifacts seguem política da SPEC-057;
- logs técnicos têm retenção menor e redigida;
- exclusão de dados do cliente não pode apagar trilha financeira/legal necessária sem policy.

---

# 29. Compatibilidade e migração do legado

## 29.1 Expand

- criar tabelas novas;
- adicionar colunas `work_run_id`;
- adicionar indexes/constraints;
- criar services;
- manter leitores existentes.

## 29.2 Backfill

Backfill somente lineage útil:

- runs recentes de Rotina;
- runs recentes de Auxiliares;
- portal jobs necessários à continuidade/auditoria;
- approvals pendentes.

Não inventar steps detalhados para histórico que não os possui.

Runs históricos podem ser representados como:

```text
workflow_key = legacy_import
status = status terminal mapeado
result_summary = resumo existente
source_id = id legado
```

## 29.3 Switch

- produtores criam Work Run primeiro;
- estruturas legadas recebem link/projeção;
- UI nova lê Work Runs;
- scheduler deixa de executar diretamente;
- Auxiliar deixa de executar diretamente;
- Portal bridge passa a atualizar Work Run.

## 29.4 Contract

Dentro desta SPEC:

- desativar escritores paralelos;
- não apagar tabelas antigas;
- marcar código legado;
- registrar pendências de remoção futura;
- manter compatibilidade somente onde a UI antiga ainda precisar.

A conclusão não pode deixar dois caminhos igualmente canônicos.

---

# 30. Execução em três blocos

# BLOCO A — Fundação durável

## Objetivo

Criar a fonte universal de verdade e o worker robusto.

## Entregas

- migrations de `work_runs`, `work_steps`, `work_attempts`, `work_events`, `work_effects`, `work_queue_outbox`;
- evolução de `approval_requests`;
- links nas tabelas existentes;
- repositories tenant-scoped;
- service de criação atômica;
- Redis Streams e consumer group;
- outbox dispatcher;
- worker Smith;
- leases e heartbeat;
- recovery scanner;
- thread/checkpoint de trabalho;
- workflow/graph versioning;
- testes de fila, lease, restart e idempotência.

## Gate

- run criado e recuperado idempotentemente;
- Redis off não perde run;
- dois workers não executam o mesmo lease;
- restart retoma a partir do checkpoint;
- side effect simulado não duplica;
- tenant A não lê tenant B;
- deploy do worker saudável.

# BLOCO B — Integração operacional

## Objetivo

Fazer o runtime ser usado pelo produto real.

## Entregas

- HITL com interrupt/resume;
- decisão de approval;
- cancel/pause/retry;
- integração chat;
- página Trabalhos;
- inbox de aprovações;
- integração Rotinas;
- integração Auxiliares;
- integração Portal Worker;
- custos por run;
- timeline/event stream;
- alertas e métricas;
- erros em linguagem humana.

## Gate

- approval pausa e retoma após fechar navegador;
- rejeição impede side effect;
- edição invalida fingerprint antigo;
- Rotina gera um Work Run;
- Auxiliar gera um Work Run;
- Portal `needs_human` aparece corretamente;
- cancelamento para antes do próximo effect;
- UI atualiza após refresh;
- fluxo Resulta/AutoFleet isolado.

# BLOCO C — Migração, ativação e lançamento

## Objetivo

Cortar o caminho canônico, ativar produção e comprovar uso diário.

## Entregas

- backfill controlado;
- desligamento de escritores paralelos;
- flags em default de produção;
- worker em produção;
- regressões completas;
- canários Amandus/Resulta/AutoFleet;
- uma Rotina real segura;
- um Auxiliar real seguro;
- um Portal job seguro;
- uma approval real controlada;
- documentação e runbooks;
- relatório final.

## Gate

- nenhum caminho novo permanece desativado sem justificativa de rollback;
- nenhum run real preso;
- nenhum effect duplicado;
- fila e recovery saudáveis;
- UX tenant utilizável;
- pilotos passam;
- Broker Outcome Regression Pack verde;
- rollback ensaiado.

---

# 31. Testes obrigatórios

## 31.1 Unitários

- máquina de estados;
- idempotency keys;
- fingerprint de approval;
- classificação de erros;
- backoff;
- lease;
- sanitização;
- transition guards;
- progress calculation.

## 31.2 Banco

- constraints company;
- unique idempotency;
- outbox atômica;
- cross-company rejeitado;
- event append-only;
- status inválido rejeitado;
- lease token obrigatório;
- approval ligada ao run correto.

## 31.3 Redis/worker

- Redis indisponível;
- reconnect;
- pending entry;
- XAUTOCLAIM;
- worker crash antes do ACK;
- worker crash depois do effect confirmado;
- worker crash com effect unknown;
- dois consumers;
- lag;
- trimming seguro.

## 31.4 LangGraph

- checkpoint por thread de work;
- interrupt;
- Command resume;
- node reinicia sem repetir effect;
- state history;
- retry a partir do último ponto;
- workflow version compatível;
- versão incompatível vai para manual review.

## 31.5 HITL

- approve;
- reject;
- edit and approve;
- approval expirada;
- approval de outra company;
- usuário sem papel;
- fingerprint alterado;
- decisão concorrente;
- refresh/relogin e resume.

## 31.6 Integrações

- Rotina;
- Auxiliar;
- Portal;
- WhatsApp sandbox;
- custo;
- chat card;
- SSE/polling;
- cancelamento;
- retry manual.

## 31.7 Segurança

- secret não entra em checkpoint/event;
- tenant A/B;
- IDOR;
- service route;
- payload size;
- tool output não altera policy;
- approval resume token não exposto.

---

# 32. Broker Outcome Regression Pack

A implementação só é aceita se preservar e melhorar o trabalho das corretoras.

## Identidade

- login;
- empresa ativa;
- Resulta ↔ AutoFleet;
- papel por vínculo;
- 403 sem vínculo.

## Chat

- pergunta simples continua rápida;
- tarefa longa vira Work Run;
- card aparece;
- refresh preserva estado;
- conclusão volta ao chat.

## Rotina

- scheduler cria um único run;
- trabalho continua com API reiniciada;
- resultado chega ao canal correto;
- falha aparece de forma humana.

## Auxiliar

- execução manual;
- execução agendada;
- tenant correto;
- configuração correta;
- histórico visível.

## Portal

- credencial permanece no Vault;
- job ligado ao run;
- needs human funciona;
- restart recupera;
- evidence privada;
- retry não duplica ação.

## Aprovação

- ação real controlada só ocorre após aprovação;
- rejeição bloqueia;
- approval de outra corretora é invisível;
- timeline registra a decisão.

## Operação

- nenhum trabalho perdido;
- nenhum side effect duplicado;
- nenhum vazamento entre corretoras;
- custo e duração registrados;
- Admin consegue localizar falha.

---

# 33. Deploy e ativação de lançamento

## 33.1 Serviços

Provável composição:

```text
smith-api
smith-worker
portal-worker
web
redis
supabase
qdrant
minio
```

`smith-worker` usa o mesmo código canônico, configuração própria e healthcheck.

## 33.2 Ordem

1. migrations expand-only;
2. backend compatível;
3. worker deployado, consumo inicialmente bloqueado por gate curto de verificação;
4. Web/API atualizados;
5. smoke tests;
6. ligar consumo;
7. migrar produtores;
8. canários;
9. tornar default;
10. desligar escritor paralelo;
11. monitorar janela inicial;
12. fechar relatório.

Isso faz parte de uma única entrega, não de cinco versões do produto.

## 33.3 Flags de emergência

Permitidas:

```text
WORK_OS_ENABLED
WORKER_CONSUMPTION_ENABLED
WORK_HITL_ENABLED
WORK_ROUTINE_BRIDGE_ENABLED
WORK_AUXILIARY_BRIDGE_ENABLED
WORK_PORTAL_BRIDGE_ENABLED
```

Ao final:

- `WORK_OS_ENABLED=true`;
- bridges canônicas ligadas;
- flags antigas documentadas para rollback;
- nenhuma flag pode esconder entrega incompleta.

---

# 34. Rollback

Rollback deve preservar dados e lineage.

## 34.1 Worker

- parar consumo;
- runs permanecem em Postgres;
- não apagar Stream;
- não apagar checkpoints;
- API pode continuar exibindo estado.

## 34.2 Bridges

- retornar produtor ao caminho legado temporariamente;
- manter `work_run_id` e eventos;
- não executar dois caminhos simultaneamente.

## 34.3 Migrations

- expand-only permanece;
- rollback emergencial é de código/flags;
- constraints novas podem ser removidas individualmente apenas se necessário;
- não remover histórico para reverter.

## 34.4 Side effect

- nunca repetir para “testar rollback”;
- reconciliar provider;
- status unknown exige manual review.

---

# 35. Condições de parada obrigatória

Parar e solicitar decisão do CEO/Founder apenas se:

1. SPEC-054 bloqueadora não estiver executada nos itens de segurança necessários;
2. backup/PITR estiver indisponível para migration de risco;
3. houver necessidade de apagar histórico/dado;
4. existirem side effects atuais sem business key possível e sem reconciliação;
5. a escolha de comportamento comercial for ambígua;
6. Portal Worker precisar ser substituído por outro runtime;
7. uma migration exigir lock incompatível com operação;
8. não for possível preservar login/WhatsApp/pilotos;
9. workflow versioning exigir invalidar runs ativos sem migration;
10. houver conflito direto com SPEC-052/053/054.

Falha comum de implementação não é motivo para parar: corrigir e continuar.

---

# 36. Critérios de aceite

A SPEC-055 somente está concluída quando:

1. `work_runs` é a autoridade universal;
2. schema e migrations estão versionados;
3. criação é atômica e idempotente;
4. outbox impede perda entre DB e Redis;
5. worker dedicado está em produção;
6. lease e heartbeat funcionam;
7. recovery scanner funciona;
8. thread de trabalho é separada do chat;
9. checkpoint retoma após restart;
10. workflow version é persistida;
11. HITL usa interrupt/resume real;
12. approval valida fingerprint e tenant;
13. cancelamento funciona;
14. retry respeita side effects;
15. effect ledger está ativo;
16. Rotinas criam Work Runs;
17. Auxiliares criam Work Runs;
18. Portal Jobs estão ligados a Work Runs;
19. `routine_runs`, `auxiliary_runs` e `portal_jobs` não são autoridades paralelas;
20. chat exibe card de trabalho;
21. página Trabalhos funciona;
22. inbox de approval funciona;
23. eventos/timeline funcionam;
24. custo por run funciona;
25. nenhum segredo aparece em state/log;
26. Resulta não lê AutoFleet;
27. nenhum teste duplica side effect;
28. Redis outage não perde trabalho;
29. worker crash não perde trabalho;
30. canários passam;
31. flags finais estão ligadas;
32. escritor paralelo está desligado;
33. relatório final está publicado;
34. zero runtime paralelo foi criado;
35. sistema está utilizável para operação real.

---

# 37. Relatório final obrigatório

Criar:

```text
docs/canon/reports/SPEC-055-execution-report-<YYYY-MM-DD>.md
```

Conteúdo mínimo:

1. commit inicial/final;
2. PR/branch;
3. migrations;
4. tabelas/colunas;
5. arquitetura implantada;
6. serviços/deploys;
7. fila/consumer group;
8. configuração de worker sem segredos;
9. graph/workflow versions;
10. integração com Rotinas;
11. integração com Auxiliares;
12. integração com Portais;
13. approvals/HITL;
14. idempotência/effects;
15. testes executados;
16. falhas simuladas;
17. canários;
18. métricas antes/depois;
19. Broker Outcome Regression Pack;
20. rollback;
21. pendências legítimas;
22. confirmação de zero perda de dados;
23. confirmação de zero side effect duplicado nos testes;
24. confirmação de zero runtime paralelo;
25. status `PASS`, `PASS WITH ACCEPTED EXCEPTION` ou `FAIL`.

Não incluir segredos, PII ou conteúdo integral de cliente.

---

# 38. O que não pertence à SPEC-055

Não implementar integralmente aqui:

- Skill Registry completo;
- Tool Gateway de produto completo;
- Artifact Hub completo;
- Report Studio completo;
- fábrica completa de Auxiliares;
- Briefing/Proatividade completos;
- Research Intelligence;
- Portal Admin Control Plane final;
- billing comercial completo;
- remoção definitiva de tabelas legadas;
- outro runtime.

A SPEC-055 deve deixar hooks e contratos para essas peças, sem antecipar implementações paralelas.

---

# 39. Referências técnicas modeladas

Esta arquitetura adota os princípios atuais de:

- persistência por thread/checkpoint;
- fault tolerance em boundaries;
- pending writes;
- `interrupt()` para pausar;
- `Command(resume=...)` para continuar;
- side effects idempotentes antes/depois de interrupts;
- Redis Streams com consumer groups, pending entries e replay;
- Postgres como autoridade durável;
- outbox para dual-write;
- versões de workflow para compatibilidade de runs pausados.

As referências externas orientam o padrão, mas a implementação deve respeitar a stack e as autoridades do AutoBrokers.

---

# 40. Próxima SPEC subordinada

Após a execução e aprovação desta SPEC:

```text
SPEC-056 — Skill Registry & Tool Gateway
```

Ela usará Work Runs, approvals, effects, custos e Context Assembly para criar:

- Skills versionadas;
- manifests;
- Capability Packs;
- seleção progressiva de tools;
- políticas de risco;
- dependências;
- tool routing;
- homologação;
- evals;
- publicação/rollback;
- tools de plataforma e tenant;
- carregamento sob demanda sem poluir o Core.

A SPEC-056 não poderá criar outro executor, fila, approval ou histórico de run.
