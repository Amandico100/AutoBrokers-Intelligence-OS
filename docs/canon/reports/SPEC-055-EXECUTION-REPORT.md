---
> **Status:** relatório final — SPEC-055 Durable Work Runs, Queue, Checkpoints & HITL
> **Branch:** `feat/spec055-durable-work-runs` · **main:** `21a2c48`
> **Data:** 25/07/2026 · **Ambiente:** `dcajcvlzcjbmyapmklil`
---

# Relatório de execução — SPEC-055

## 0. Declaração de integridade

- [x] Nenhum motor paralelo criado — o Smith Worker executa **o mesmo Smith**.
- [x] Portal Worker, routine engine, Vault, Evolution Go e Observador preservados.
- [x] Nenhuma tabela existente substituída. `routine_runs`, `auxiliary_runs` e `portal_jobs` intactos.
- [x] `approval_requests` **evoluída** em expand-only, conforme §7.7 — nenhuma coluna alterada ou removida.
- [x] Nenhum segredo em log, evento ou payload.
- [x] Contagens de negócio inalteradas.

---

## 1. O que existe agora que não existia

| Garantia | Antes | Agora |
|---|---|---|
| Execução universal | 3 histórias incompatíveis | `work_runs` único |
| Trabalho sobrevive a restart | **não** | lease + heartbeat + recuperação |
| Efeito externo não repete | **não** | reserva idempotente em `work_effects` |
| Aprovação bloqueia de fato | não (era dado + UI) | estado `waiting_approval` + fingerprint |
| Trabalho longo fora do event loop web | **não** | Smith Worker dedicado |
| Trilha auditável do trabalho | **não** | `work_events` append-only |
| Fila não perde trabalho | n/a | outbox transacional + Redis Streams |
| Consumo medido por run | parcial | `usage_events` `PRE_LAUNCH_NON_BILLABLE` |

---

## 2. Migrations

| Versão | Conteúdo |
|---|---|
| `spec055_a1_work_runs_core_model` | 6 tabelas, 3 enums, RLS service-role-only, FKs compostas `(id, company_id)`, índices |
| `spec055_a1b_work_events_append_only_with_governed_purge` | correção de defeito — ver §4 |
| `spec055_a2_approvals_usage_events_and_atomic_create` | `approval_requests` evoluída, `usage_events`, RPC `work_run_create` |

### Garantias provadas no próprio banco — 7/7

| Tentativa | Resultado |
|---|---|
| `thread_id` fora do formato canônico | **REJEITADO** |
| `idempotency_key` duplicada no mesmo tenant | **REJEITADO** |
| Alterar `company_id` de um run | **REJEITADO** |
| `UPDATE` em `work_events` | **REJEITADO** |
| Step de outro tenant dentro do run | **REJEITADO pela FK composta** |
| `DELETE` em `work_events` sem purga governada | **REJEITADO** |
| Purga governada com intenção declarada | **funciona** |

E a idempotência na porta de entrada: chamar `work_run_create` duas vezes com a mesma chave devolve **o mesmo run** com `reused=true`, sem duplicar.

---

## 3. Código entregue

| Módulo | Responsabilidade |
|---|---|
| `services/work/effects.py` | reserva de efeito externo — **a peça que impede cobrar ou enviar duas vezes** |
| `services/work/queue.py` | Redis Streams com consumer group + `OutboxDispatcher` |
| `services/work/runs.py` | lease, heartbeat, recuperação de órfão, transições, timeline |
| `services/work/approvals.py` | HITL executável com fingerprint |
| `services/work/usage.py` | medição técnica (D4) — mede, não cobra |
| `services/work/workflows.py` | contrato de workflow + `executar_passo` + 4 pontes |
| `workers/smith_worker.py` | processo dedicado com 4 laços |
| `api/work_runs.py` | listar, detalhar, criar, cancelar, aprovar, `/api/work/health` |
| `services/routine_engine.py` | ponte para Work Run atrás de flag |

---

## 4. Defeito de design encontrado pelo próprio teste

O trigger append-only de `work_events` bloqueava `DELETE` de **qualquer** origem — inclusive o `CASCADE` legítimo disparado ao remover um run ou uma corretora.

Consequência, se tivesse passado: nenhum run com evento poderia ser removido, **nunca, por ninguém**. Isso tornaria impossível retenção de dados (§28), offboarding de corretora e o direito de exclusão previsto na LGPD.

**Correção:** `UPDATE` continua proibido em absoluto — a trilha de auditoria nunca é reescrita. Para `DELETE`, a única porta é uma operação governada que declara intenção explícita na transação (`app.work_events_purge`). Aplicação normal e cascade acidental continuam barrados.

Só apareceu porque executei o teste de limpeza de verdade, em vez de assumir que funcionava.

---

## 5. As três decisões de engenharia que mais importam

### 5.1 Reservar antes, confirmar depois

O padrão ingênuo — executar e depois registrar — não protege nada: o crash acontece justamente na janela entre executar e registrar.

O caso é real e já existe hoje: o Portal Worker conclui a ação no portal da seguradora e o processo morre antes de gravar o status. Com **67 de 91 jobs** em `needs_human`, esse cenário não é hipotético.

Agora: reserva com `UNIQUE` **antes** do efeito; confirmação com referência do provider **depois**. Crash no meio deixa `unknown` — que exige reconciliação e **proíbe repetição automática**. Falha ao apenas *consultar* a reserva também é fail-closed: não saber se o efeito ocorreu é motivo para não executar.

### 5.2 Fingerprint separa aprovação de cheque em branco

O humano aprova um conteúdo específico. Se o texto for reescrito, o destinatário mudar ou o valor for outro entre o aceite e a execução, a aprovação **não vale**. Sem isso, "aprovado" viraria autorização genérica para qualquer coisa que o agente decidisse fazer depois.

A validação roda **imediatamente antes** do efeito externo, não no início do passo.

### 5.3 Outbox elimina o dual-write

```text
INSERT no Postgres → crash → Redis nunca soube do trabalho
publish no Redis   → crash → trabalho executado sem registro
```

A linha do run e a do outbox nascem na **mesma transação** (RPC). Um dispatcher separado publica. Redis vira transporte; a verdade é o Postgres — lei da SPEC-053 §2.5.

---

## 6. Testes

| Suíte | Resultado |
|---|---|
| Garantias no banco (migrations) | **7/7** |
| `test_spec055_work_os.py` | **11/11** |
| **Broker Outcome Regression Pack** | **17/17 · GATE VERDE** |
| `compileall` backend | exit 0 |

Dois casos novos entraram no pack, nomeados pelo resultado que protegem:
`EXE-01` — *"O corretor não é cobrado nem notificado em duplicidade"*
`EXE-02` — *"Trabalho longo sobrevive a restart e retoma"*

---

## 7. Deploy

| Item | Estado |
|---|---|
| API | deploy validado, `/health` 200 |
| `/api/work/health` e `/api/work/runs` | **401** — rotas registradas exigindo chave interna |
| Ponte de Rotinas | `WORK_RUNS_ROUTINE_BRIDGE` — **default OFF** |
| Worker in-process | `WORK_WORKER_IN_PROCESS` — **default OFF** |

Expand→contract respeitado: o código está em produção, desligado, pronto para ser ativado com um canário.

---

## 8. Pendências que exigem o Founder

### 8.1 Serviço dedicado do Smith Worker

O worker existe e está testado, mas **não tem onde rodar**. O alvo da SPEC-055 §11.1 é um serviço separado:

```text
Serviço EasyPanel: autobrokers-smith-worker
Comando:           python -m app.workers.smith_worker
Mesma imagem e mesmas variáveis da API
1 réplica para começar
```

Enquanto isso, `WORK_WORKER_IN_PROCESS=1` roda o worker dentro da API. **Não é o estado final**, mas já é melhor do que o scheduler anterior: com lease, um processo que morre tem seus runs recuperados em vez de deixá-los presos.

### 8.2 Confirmação do checkpointer

`SUPABASE_DB_URL` foi adicionada e a API redeployada, mas `checkpoints` continua em 0 — o que é esperado, porque **checkpoint só é escrito quando alguém usa o chat**. A confirmação vem sozinha no primeiro uso. Se continuar zerado após uma conversa real, o fallback ainda está ativo e volta a ser bloqueador.

### 8.3 Ativação por canário

Ordem recomendada, uma variável por vez, verificando entre elas:

1. `WORK_WORKER_IN_PROCESS=1` (ou o serviço dedicado)
2. verificar `/api/work/health`
3. criar um run `system.healthcheck` e ver concluir
4. `WORK_RUNS_ROUTINE_BRIDGE=1` — as 2 rotinas passam a executar por Work Run

---

## 9. Fora do escopo, conforme a SPEC

`work_runs` ainda **não** é a leitura canônica: `auxiliary_runs` continua sendo escrito por compatibilidade até o cutover (§20.2). O backfill histórico, a UI de "Trabalhos" no dashboard e o corte definitivo de `routine_runs` ficam para o cutover, que depende do worker em produção.

Skills, Capability Packs e Tool Gateway são da **SPEC-056** — o `workflows.py` deixa o contrato pronto para o registro definitivo.

---

## 10. Impacto para o corretor

Nada visível ainda — e isso é honesto. O que mudou é que, a partir de agora, quando o AutoBrokers disser *"estou preparando seu relatório"*, isso vira um trabalho com dono, etapas visíveis, retomada automática e uma garantia dura de que ninguém vai receber a mesma cobrança duas vezes.

É a fundação sobre a qual Relatório Executivo, Briefing Diário e Auxiliares vão rodar.
