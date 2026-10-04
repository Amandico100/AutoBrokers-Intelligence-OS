# SPEC-129-A — A espera durável

> SPEC executável · 04/10/2026 · v2 (revisor cego: 76, 8 consertos aplicados) · PROGRAMA MULTICÁLCULO, passo 1. Ficha:
> `programa-multicalculo/PLANO-MESTRE-MULTICALCULO.md` §4, §1.3, §13. Rito **AAA v13**, 🔴 **CRÍTICO por piso**. Branch
> `spec/129-A-a-espera-duravel` · base `5ab37e7`. Insumo: `SPEC-EXTRA-003` §7 fatia 1. 📊 Medições: 04/10, `execute_sql`
> só leitura, projeto `dcajcvlzcjbmyapmklil`.

## 0. POR QUE ESTA SPEC EXISTE

O cálculo do Agger dura 📊 413–420 s (ficha §1.3). Hoje o Work OS não sabe esperar isso:
1. **"Tentar de novo" nunca volta.** `runs.py:272` grava `retry_scheduled`; o varredor só olha `ESTADOS_ATIVOS` (`runs.py:35`,
   `:199-244`); só o conciliador de acionamento relê esse estado (`dispatch_router.py:388-390`, `:1959`).
2. **O worker conclui por cima da espera.** `workflows.py:462,552` gravam `waiting_approval`; `smith_worker.py:385-393` conclui
   em seguida; `_transicionar` não tem pré-condição (`runs.py:309-314`).
3. **"Reprocessar" é mudo.** `api/work_runs.py:204` recusa `retry_scheduled`; `:213` só muda para `queued`, sem outbox → preso.
4. **A espera do portal trava o processo.** `gateway.py:60` (150 s) e `:409` `time.sleep` em `async def _executar`
   (`workflows.py:517,545`): o event loop para, o heartbeat para, a lease de 120 s (`runs.py:33`) vence.
5. **O reinício mente** (worker-na-API): `smith_worker.py:290-293` promete "será retomado" num estado que ninguém relê.

Achados lendo o código, que entram porque o conserto dos cinco depende deles (COESÃO §3.4):
6. `adquirir_lease` lê e grava sem condição (`runs.py:121-164`): dois processos assumem o mesmo run; `waiting_*`/`cancelling` viram `running`.
7. `executar_passo` re-executa passo concluído (`workflows.py:111-140`: bate em `uq_work_steps_run_key`, reencontra, roda `fn()`).
8. `WorkApprovalService.decidir` (`services/work/approvals.py:269-305`) não acorda o run e não filtra `status='pending'` (`:288-292`).

📊 **E a fila perde mensagem:** os 21 `queued` têm outbox `published` e nenhum `run.leased`:
```sql
select r.workflow_key, o.status, count(*), (select string_agg(distinct e.event_type, ',') from work_events e
  where e.work_run_id = any(array_agg(r.id))) from work_runs r join work_queue_outbox o on o.work_run_id=r.id
 where r.status::text='queued' group by 1,2;
-- detect_signals | published | 20 | run.created,run.queued  ·  measure_outcomes | published | 1 | idem
```
INFERÊNCIA: `ack` após `adquirir_lease` falhar (`smith_worker.py:281-285`) ou stream perdido. **O Postgres tem de re-despachar.**

## 1. O EXECUTION CARD

```
OUTCOME ..............  um trabalho dorme minutos, acorda sozinho, sobrevive a reinício e nunca roda duas vezes; o velho
                        expira sem rodar; nenhum CPF em claro em work_steps. 📊 meta: 21 presos `expired` · 0 "sem fila"
                        tocados · 0 de 17 linhas com CPF · canário de 10 min com reinício → 1 conclusão
RISCO ................  7 — ALCANCE 3 (a cobrança pela ponte fala com o segurado) · REVERSIBILIDADE 3 (mensagem em dobro) ·
                        FREQUÊNCIA 1 (📊 0 rotinas ativas hoje; o Work OS roda a cada hora)
SUPERFÍCIE ...........  2 — vários comportamentos do Work OS + peça nova (o despertador, no laço que já existe)
PISO APLICADO ........  §3.2 — a COBRANÇA (`WORK_RUNS_ROUTINE_BRIDGE=1`, Founder) passa pelo código alterado · migrations de
                        estrutura, de DADO e gatilhos
NÍVEL ................  🔴 CRÍTICO · builders Opus 5.5 xhigh frescos · juiz ‖ red team Opus 5.5 · LENTE DO DADO · confirmação
O FIO ................  §2 · TESTE DO FIO (F0) primeiro, VERMELHO: `portal.operation` cria o job, DORME, o worker MORRE,
                        outro acorda, o portal termina, o run conclui UMA vez
PARALELISMO REAL .....  F1 (runs.py, smith_worker.py, _02) ‖ F4 (_01, _03) → F2 (workflows.py, gateway.py) ‖ F3
                        (api/work_runs.py, approvals.py) → F5 costura — arquivos e testes antigos por fatia no §7
UNIDADES .............  6 fatias F0–F5 (§7)
COESÃO ...............  CAS + lease + dormir + despertar + sentinelas = um contrato (F1, runs.py) · executar_passo + portal
                        = o mesmo hub (F2) · MANIFEST é hub → só na costura
TIME .................  gerente · 5 builders · juiz ‖ red team · lente do dado · atualizador
REFERÊNCIA ...........  interna: `backend/tests/test_spec055_work_os.py`, `backend/tests/trava_do_banco_real.py`
                        (`transacao_desfeita`), MIGRATIONS-AUTHORITY §7 · externa: §10 (5 URLs)
GATES ................  §9 (G1–G11), cada guarda novo com a MUTAÇÃO que o deixa vermelho
O ELO ................  "os 21 estão presos PORQUE a mensagem se perdeu entre a fila e a lease": A queued sem lease ✔ ·
                        B outbox published 21/21 ✔ · B→A nenhum `run.leased` ✔. Do conserto: o re-despacho CHEGA ao
                        `_executar_run` (C5 mede)
FAIXA DE RELÓGIO .....  💭 6–9 h · fatia ≤ 1h15 · tetos §10 (CRÍTICO: 250 turnos, 300 k)
```

## 2. O FIO

```
criar:   WorkRunService.criar (runs.py:60) → RPC work_run_create → work_runs(queued) + outbox(pending)
fila:    _laco_dispatcher → OutboxDispatcher.despachar_lote (queue.py:171) → xadd → _laco_consumo → _agendar (smith_worker.py:252)
lease:   _executar_run → runs.adquirir_lease  ← 🔴 CAS, só runtime_kind='smith'
rodar:   _processar → portal_operation (workflows.py:478)
         → executar_passo("portal:<op>:criar", efeito="idempotente", guardar=("portal_job_id",))
             → asyncio.to_thread(gw.executar(req: wait_mode=ENFILEIRAR, idempotency_key="wr:<run>:<op>"))
             → portal_jobs(queued, work_run_id) — DUBLÊ na borda: o portal-worker
             → resultado COM portal_job_id = sucesso do passo (mesmo vindo como `needs_human`, gateway.py:321-328)
         → executar_passo("portal:<op>:aguardar") lê o job: não terminou → runs.dormir(…) → ESPERANDO
             (CAS running(meu token)→waiting_input + wake_at + wait_for, lease limpa)
         → _processar vê ESPERANDO → NÃO conclui  ← 🔴 hoje conclui por cima (smith_worker.py:393)
acordar: _laco_orfaos (smith_worker.py:151, 60 s) → runs.despertar_vencidos → CAS →queued + outbox `run.woken`
         → runs.redespachar_parados (parado > 10 min, §6) → outbox nova · idade vencida → `expired`
retomar: lease CAS → :criar `succeeded` devolve o job guardado (fn NÃO roda) → :aguardar lê `done`
         → traduzir_estado → runs.concluir (CAS running(meu token)→completed)
humano:  WorkApprovalService.decidir (só `pending`) → aprovado: CAS waiting_approval→queued + outbox · recusado: →cancelled
mão:     POST /api/work/runs/{id}/retry (api/work_runs.py:176) → runs.reprocessar → CAS + outbox
```

## 3. DECISÕES (vêm decididas, com nota — o Founder confirma se quiser)

| # | decisão | nota |
|---|---|---|
| D-129A-1 | **Espera = `waiting_input` (já no ENUM) + `wake_at`, `wait_for`**, só `smith` | 85 × rótulo `waiting` 60 (`ADD VALUE` não se desfaz) |
| D-129A-2 | **Acorda pelo relógio `wake_at`, no laço de órfãos que já existe** (60 s); a aprovação acorda na hora pelo mesmo `despertar` | 85 × gatilho em `portal_jobs` 55 (falha quebraria o UPDATE do portal-worker) × laço novo 0 |
| D-129A-3 | **CAS = UPDATE filtrado do PostgREST** (a linha ou nada) **+ re-despacho que se cura** | 82 × RPC plpgsql 74 (motor em SQL que o dublê não roda; o re-despacho é preciso de todo jeito) |
| D-129A-4 | **Passo de efeito EXTERNO interrompido não repete** → `failed efeito_incerto` ("reconcilie antes"), o princípio de `NEGOCIO_TALVEZ_COMMITADO` (`workflows.py:557-564`). `succeeded` nunca repete; `idempotente` repete. Reprocessar um `efeito_incerto` → 409 (não vira laço) | 85 × confiar no ledger 60 (o aviso ao grupo, `billing_collection.py:279-284`, fica FORA do `billing_sent_log`) |
| D-129A-5 | **Idade-limite por workflow** (`idade_maxima_s` no registro), padrão **2 h**, por `requested_at` (§6). Periódicos: a janela seguinte já fez o trabalho (📊 4.969 `detect_signals` concluídos); rotina volta na próxima ocorrência (`billing_collection.py:1792`). 💭 INFERÊNCIA: cobrança 2 h atrasada já saiu da janela útil | 80 × 24 h 55 × sem limite 0 (§13 da ficha) |
| D-129A-6 | **O retrato cru do acionamento só existe enquanto pode ser restaurado:** passo `monitoring` com ≤ 24 h de run não-terminal (o ÚNICO restaurado, B6). O resto é mascarado no banco (gatilhos em `work_steps` e no fechamento + varredura das `monitoring` vencidas). As **17**, sem exceção | 86 × higienizar na escrita 30 (quebra a restauração, `dispatch_router.py:1156-1160`) × cifrar 70 |
| D-129A-7 | **`needs_human` do portal → `waiting_input`** com relógio em backoff (5 → 10 → 20 → 40 → 60 min, teto 60; 💭 ≈ 27 despertares/24 h em vez de 288) e prazo 24 h | 75 × `waiting_approval` sem `approval_request` 20 (espera para sempre, `metric_proposal.py:104`) |

⚠️ Discordância com a P-126-09 (higienizar na escrita quebra a restauração do `monitoring`): fecha pelo D-129A-6.

## 4. BLOCO 0 — premissas que mudariam o desenho (gerente, ≤ 15 min)

📊 = medido (04/10) pelo redator e pelo revisor cego; o gerente reconfere no `main` (§0.4).

| # | premissa | comando | resultado | se falhar |
|---|---|---|---|---|
| B1 | status é ENUM sem CHECK; `waiting_input` existe; `wake_at` não | `select string_agg(e.enumlabel,'\|' order by e.enumsortorder) from pg_enum e join pg_type t on t.oid=e.enumtypid where t.typname='work_run_status';` + `pg_constraint` de `work_runs` + `information_schema.columns` | 📊 13 rótulos; nenhum CHECK de status; sem `wake_at`; há `next_attempt_at`; nenhum gatilho de `updated_at` (só `trg_work_runs_company_imutavel`) | D-129A-1 cai → 2º modelo |
| B2 | inventário dos presos | `select workflow_key,status::text,runtime_kind,count(*),min(created_at)::date,max(created_at)::date, count(*) filter (where lease_owner is null) from work_runs where status::text not in ('completed','failed','cancelled','expired') group by 1,2,3;` | 📊 `detect_signals` queued **20** (28/07–01/10) · `measure_outcomes` queued **1** · `claims.shadow` **running SEM lease 3** · `metric.proposal` waiting_approval **2** · `acionamento.seguradora` waiting_input **1** (10/09) · `retry_scheduled` **0** | refazer a §5 |
| B3 | `smith` ⇔ nasceu pela fila | `select runtime_kind,count(*) from work_runs group by 1;` + smith sem outbox | 📊 smith 6.466 · acionamento 6 · proposta 3 · sombra 3 · smith sem outbox **0** | ≠ 0 → exigir outbox |
| B4 | o caminho que ENVIA está vivo? | `select count(*) from routines where is_active;` + `routine_runs` 40 dias + `work_runs` da ponte e do portal | 📊 **0 rotinas ativas** · último `routine_run` 11/09 · ponte 9 completed · `portal.operation`/`bridge.portal.job`: **0 runs, nunca** · `routine_runs.status` sem CHECK (valores `ok`,`error`,`delegated`) | rotina ativa → canário fora da janela |
| B5 | o que vaza (P-223) | `select count(*),min(created_at)::date,max(created_at)::date from work_steps where output_summary::text ~ '"(titular_cpf\|telefone_contato\|client_phone)"\s*:\s*"[0-9]';` | 📊 **17** (18/08–10/09; a P-223 contava 12), todas `step_type='dispatch_phase'`; gêmeo em 17/17 sem CPF (as 3 chaves `...9999`). Por run: completed 10 · cancelled 4 · vivo 3 (passos `ura`, `human_phase`, `needs_human` — **nenhum `monitoring`**) | gêmeo nulo → marcador |
| B6 | quem LÊ o cru e quando | `grep -rn "output_summary" backend/app --include=*.py` + `dispatch_router.py:1916` e `:2033` + `insurer_dispatch_service.py:173` | 📊 único leitor: `_ultimo_retrato` (`:1916`); restaura só `fase=='monitoring'` com idade ≤ 24 h (`:2033`, `_JANELA_DE_VIDA_SEGUNDOS`). ⚠️ **Acionamento terminal REABRE**: `test_aborted` (completed) → `needs_human` (`:1205-1221`); e o checkpoint grava o passo cru ANTES do status (`:1168-1173`, `:1225`) | outro leitor → a janela do D-129A-6 cresce |
| B7 | MANIFEST em dia | `grep -c "20261002_1[01]" backend/supabase/migrations/MANIFEST.md` + `schema_migrations` | 📊 **2** (`6880e62`); banco = arquivo | a 1ª migration corrige |
| B8 | `work_events.event_type` livre | `pg_constraint` de `work_events` | 📊 só CHECK de `actor`/`severity` | — |
| B9 | quem perde a mensagem | `XINFO GROUPS autobrokers:work:stream` no `smith-worker` | CAIXA (opcional) | não muda o desenho |
| B10 | ramos da ponte fora de `executar_passo` | `sed -n 295,360p backend/app/services/work/workflows.py` | 📊 monitor (`:316-327`) e `config.workflow` (`:333-347`) sem passo | — (F2 os põe no passo) |

## 5. A REGRA DOS PRESOS (migration de DADO `20261004_01`, antes de qualquer código)

```
volta para a fila  ⇔  runtime_kind='smith'  E  workflow_key no registro  E  agora − requested_at ≤ limite do workflow
expira sem rodar   ⇔  runtime_kind='smith'  E  status ∈ (queued, retry_scheduled)  E  agora − requested_at > 2 h
nunca é tocado     ⇔  runtime_kind ∈ (acionamento, sombra, proposta) — os "sem fila" (runs.py:345-378)
```
📊 Sobre o inventário: **0 voltam · 21 expiram · 6 intocados** (o mais novo dos 21 tem 3 dias).
```sql
-- MIGRATION spec129a_presos_expiram · SPEC-129-A F4 · DADO · reversível pela marca · não destrutiva
-- APPLY
update public.work_runs set status='expired', finished_at=now(), error_code='expirado_sem_rodar_129a',
       error_message='Expirou sem rodar: ficou na fila além do limite (SPEC-129-A). A próxima janela já fez o trabalho.'
 where runtime_kind='smith' and status in ('queued','retry_scheduled') and lease_owner is null
   and requested_at < now() - interval '2 hours';
insert into public.work_events(company_id, work_run_id, event_type, actor_type, severity, message_human, payload_redacted)
select company_id, id, 'run.expired', 'system', 'warning', error_message, '{"spec":"129-A","migration":"_01"}'::jsonb
  from public.work_runs w where w.error_code='expirado_sem_rodar_129a'
   and not exists (select 1 from public.work_events e where e.work_run_id=w.id and e.event_type='run.expired');
-- VERIFY (esperado: 21 · 21 · 6 · 0)
select (select count(*) from work_runs where error_code='expirado_sem_rodar_129a') expirados,
       (select count(*) from work_events where payload_redacted->>'migration'='_01') eventos,
       (select count(*) from work_runs where runtime_kind<>'smith' and status::text not in ('completed','failed','cancelled','expired')) sem_fila_vivos,
       (select count(*) from work_runs where runtime_kind='smith' and status in ('queued','retry_scheduled')
          and requested_at < now()-interval '2 hours') presos_restantes;
-- ROLLBACK
update work_runs set status='queued', finished_at=null, error_code=null, error_message=null where error_code='expirado_sem_rodar_129a';
delete from work_events where event_type='run.expired' and payload_redacted->>'migration'='_01';
```
🔴 A lista dos `id` (SELECT com o mesmo WHERE) vai ao relatório ANTES do APPLY. A expiração em tempo de execução usa
OUTRO código (`expirado_pela_idade`), para que o ROLLBACK da `_01` nunca ressuscite o que o despertador expirou.

## 6. O DESENHO DA ESPERA DURÁVEL

Peças existentes: `work_runs`, `work_queue_outbox`, Redis Streams, `_laco_orfaos`. **Nada novo de fila/scheduler/executor** (§5).
```
waiting_input    + wake_at + wait_for {"tipo","ref","prazo","passo","acordou","intervalo_s"}   espera de EVENTO
retry_scheduled  + wake_at (next_attempt_at continua, compat)                                  NOVA TENTATIVA
waiting_approval (+ approval_request)                                                           HUMANA — acorda na decisão
```
Travas no banco (`_02`): `ck_work_runs_wake_so_da_fila` (`wake_at` só em `smith`) e `ck_work_runs_espera_tem_relogio`
(`smith` em `waiting_input`/`retry_scheduled` sem `wake_at` → recusado).

**Os relógios (um por pergunta, nomeados):**
```
idade (limite 2 h, D-129A-5)  = agora − requested_at   ← NUNCA regravado; vale só para run SEM wait_for
espera                        = wait_for.prazo          ← absoluto, gravado no 1º dormir, preservado nos seguintes (mesmo ref);
                                                           run com wait_for nunca expira pela idade
parado (> 10 min)             = queued:  queued_at  (o despertar e a recuperação o regravam — é o que se quer: tempo na fila)
                                running: coalesce(heartbeat_at, started_at), com lease nula
acordar                       = wake_at ≤ agora
```
⚠️ Os CAS usam o relógio do cliente (o valor de "agora" vai no filtro): diferença entre workers ≪ lease de 120 s; anotado.

**TODA escrita de status nova ou mudada vira CAS e leva `.eq("runtime_kind","smith")`:**
`_transicionar(run_id, novo, campos, *, de, lease_token=None) -> bool` — perdeu → `False`, evento `run.cas_perdido`.

| de → para | quem | condição (além de `runtime_kind='smith'` e `company_id` da linha) |
|---|---|---|
| queued · running/planning com lease vencida → running | `adquirir_lease` | lease nula ou `< agora`; `cancelling` NÃO vira `running` |
| running → completed · failed · retry_scheduled · waiting_input · waiting_approval | worker / handler | `status='running'`, `lease_token=<meu>` |
| waiting_input · retry_scheduled → queued + outbox `run.woken` | `despertar_vencidos` | `wake_at ≤ agora` |
| waiting_approval → queued + outbox · cancelled · expired | `decidir` (só `pending`) · `expirar_vencidas` | `status='waiting_approval'` |
| waiting_* · retry_scheduled · queued → cancelled | `solicitar_cancelamento` | lease nula. ⛔ "sem fila" mantém o comportamento de hoje (`api/work_runs.py:155-168`) |
| failed · cancelled · paused · retry_scheduled → queued + outbox `run.retried` | `reprocessar` | workflow registrado; `efeito_incerto` → 409 |
| queued · retry_scheduled → expired (`expirado_pela_idade`) | despertador / re-despacho | idade > limite, sem `wait_for` |
| queued (parado) · running sem lease (parado) → + outbox `run.redriven` | `redespachar_parados` | relógio "parado" > 10 min |

📊 Por que o filtro em TODO CAS: as 3 `claims.shadow` estão `running` SEM lease — sem ele, `redespachar_parados` e a lease
nova as pegariam e o worker as mataria como `workflow_desconhecido` (`smith_worker.py:366-370`). `recuperar_orfaos`
também ganha o filtro (barato).

**Outbox depois do CAS**; morrer entre os dois → o re-despacho cura; outbox em dobro → uma lease ganha. ⚠️ `_agendar` dá `ack` em mensagem de run ainda em `_em_execucao` (`smith_worker.py:259-261`): um despertar nesse
instante espera o re-despacho (≤ 10 min) — aceito e testado (C5).

**O contrato fixo (F1 entrega em `runs.py`; F0, F2, F3 importam):**
```python
class Esperando: ...;  ESPERANDO = Esperando()      # sentinela: _processar NÃO conclui
class EfeitoIncerto(Exception): ...                 # o worker grava failed 'efeito_incerto'
runs.dormir(run_id, *, lease_token, acordar_em_s, wait_for) -> Esperando   # CAS running→waiting_input
runs.despertar_vencidos(workflows) · runs.redespachar_parados(workflows) · runs.reprocessar(run_id, company_id, ator)
runs.despertar_por_aprovacao(run_id, company_id, decisao) · contexto["lease_token"] no handler
```
**Passos** — `executar_passo(…, efeito="nenhum"|"idempotente"|"externo", guardar=(chaves,))` (F2):
```
succeeded → devolve output_summary[guardar] SEM chamar fn (nenhuma tentativa aberta)
running   → nenhum/idempotente: nova tentativa · externo: levanta EfeitoIncerto
guardar   → só chaves declaradas, só str/int/bool curtos (ids, estados): nunca texto livre, logo nunca PII
```
**O portal sem `time.sleep`:** gateway em `asyncio.to_thread`, sempre `ESPERA_ENFILEIRAR`; muda em três pontos (F2): respeita `req.idempotency_key` mesmo em leitura (hoje `:219-220` devolve `None` antes);
o ramo do pedido existente (`:310-313`) respeita `enqueue` e devolve o handle sem `_esperar_e_traduzir`; e o `:criar`
trata como SUCESSO todo resultado COM `portal_job_id` (o `enqueue` responde `needs_human` com motivo "enfileirado",
`:321-328`); sem `portal_job_id` é recusa e segue o `business_state`.

**Reinício.** Dormindo, o run não tem dono; rodando, a lease vence e `recuperar_orfaos` o devolve (`runs.py:220-234`). No worker-na-API (`main.py:123`, desligado) o `CancelledError` grava
`retry_scheduled` com `wake_at`: "será retomado" vira verdade, ou "reconcilie" (D-129A-4). **Prazo:** vencido → `failed`
("o portal não respondeu em X min"), `portal_job` intocado (`gateway.py:416-418`); o despertador expira o que passou de
`prazo + 1 h`.

**A COBRANÇA** (`bridge.routine.execute`): (1) os TRÊS ramos da ponte (monitor, `config.workflow`, motor — B10) passam por
UM `executar_passo("executar_rotina", efeito="externo")`: morto no meio, não repete; (2) passo `succeeded` + morto antes
do `concluir` → `_execute_routine` não roda de novo; (3) lease por CAS; (4) idade-limite 2 h por `requested_at`; (5) o
`billing_sent_log` continua como segunda linha. Run da ponte que termina `expired` ou `efeito_incerto` grava evento
`warning` legível pelo corretor ("A cobrança de <rotina> não rodou: …") e fecha o `routine_runs` `delegated` com
`status='error'` (hoje só o sucesso o fecha, `workflows.py:378-383`).

⚠️ **Ordem de implantação.** Migrations antes do código. Até a implantação, só o `CancelledError` do worker-na-API
(desligado) grava `retry_scheduled` sem `wake_at`; ligado, o CHECK recusaria, o erro seria engolido (`runs.py:313-314`) e o
run ficaria `running` sem lease, invisível ao varredor (`runs.py:211`) — o re-despacho cobre.

## 7. AS FATIAS (um builder Opus 5.5 xhigh fresco por fatia; commit arquivo por arquivo)

| fatia | entrega | arquivos (dono único, inclusive os testes ANTIGOS que mudarem) | depende |
|---|---|---|---|
| **F0 · o fio** | §7.1 + dublês da BORDA (banco em memória com filtro do PostgREST e as travas `uq_work_steps_run_key`, `uq_work_runs_company_idempotency`, os 2 CHECKs; Redis Streams; portal-worker; relógio). **Commit VERMELHO** com a saída | `backend/tests/test_spec129a_o_fio_da_espera.py`, `backend/tests/dubles_do_work_os.py` | — |
| **F1 · o motor espera** | `_02`; o contrato do §6 em `runs.py`; CAS em toda transição; no worker: `ESPERANDO`, `lease_token`, despertador/re-despacho em `_laco_orfaos`, `EfeitoIncerto`, `work_steps_mascarar_vencidos` (rpc) em `_laco_manutencao`, frase honesta do `CancelledError` | `services/work/runs.py`, `workers/smith_worker.py`, `migrations/20261004_02_…sql`, `tests/test_spec129a_o_cas.py` · antigos: `test_spec055_work_os.py`, `test_spec020_worker_hardening.py`, `test_o_run_sem_fila.py`, `test_o_work_run_recebe_a_entrada.py` | F0 |
| **F2 · passos e portal** | `executar_passo(efeito, guardar)`; `idade_maxima_s` no registro; `portal_operation` `:criar`/`:aguardar`; `bridge_portal` com backoff (D-129A-7); a ponte num passo externo + evento + `routine_runs`; `system.espera_de_teste`; gateway (§6) | `services/work/workflows.py`, `services/portals/gateway.py`, `tests/test_spec129a_a_cobranca_nao_repete.py`, `tests/test_spec129a_o_loop_nao_trava.py` · antigos: `test_o_portal_nao_deixa_ninguem_esperando.py`, `test_spec075_contrato_da_factory.py` | F1 |
| **F3 · as portas** | Reprocessar por `runs.reprocessar` (antecipa `retry_scheduled`; "sem fila", sem executor ou `efeito_incerto` → 409 em português); cancelamento direto só `smith`; `/health` conta as esperas; `decidir` filtra `pending` e acorda/cancela; `expirar_vencidas` expira o run | `api/work_runs.py`, `services/work/approvals.py`, `tests/test_spec129a_as_portas.py` | F1 (‖ F2) |
| **F4 · presos e rastro** | `_01` (§5) e `_03` (§8); guarda `banco_real` em `transacao_desfeita` que aplica a `_03` e prova: passo não-`monitoring` gravado cru → sai mascarado; `monitoring` < 24 h de run vivo → cru; run fechado com checkpoint posterior → mascarado; `smith` intocado; e os 2 UPDATEs filtrados do CAS (o 2º devolve 0 linhas) | `migrations/20261004_01_…sql`, `migrations/20261004_03_…sql`, `tests/test_spec129a_o_rastro_fecha_sem_cpf.py` | — (‖ F1) |
| **F5 · costura** | fio VERDE; MANIFEST (3 linhas, sha256, VERIFY real); `scripts/canario_espera_duravel.py` (`--criar` escolhe a corretora pelo banco, §13.9; `--conferir <id>`); APPLY `_01 → _02 → _03`; dono dos testes antigos fora das listas | `migrations/MANIFEST.md`, `scripts/canario_espera_duravel.py` | F1–F4 |

🔴 `runs.py` e `workflows.py` são HUB: só o dono edita. Teste antigo de duas fatias → F5.

### 7.1 O TESTE DO FIO (F0) — motor real, dublê só na borda
Motor real: `SmithWorker`, `OutboxDispatcher`, `WorkQueue`, `WorkRunService`, `portal_operation` + `executar_passo`,
`PortalExecutionGateway` (modo `on` por env; conta e journey semeadas). Borda: banco, Redis, portal-worker, relógio.
Dois `company_id` reais por SELECT só leitura. 🔴 **Sem
banco o teste FALHA com a causa; pular não conta como verde no G1.**
```
C1 dorme e acorda     job → waiting_input → relógio +10 min em passos de 60 s → `done` no 3º despertar → completed ·
                      run.succeeded ×1 · portal_jobs ×1 · :criar 1 tentativa · acordou = 3
C2 reinício dormindo  A morre em waiting_input → B (instância nova) acorda e conclui · contagens de C1
C3 reinício no meio   A morre DEPOIS do insert do job e ANTES do :criar `succeeded` → B retoma → MESMO job, SEM espera
                      bloqueante (o ramo "já existe" respeita enqueue)
C4 cancelar dormindo  → cancelled na hora; o despertar seguinte não o reabre
C5 mensagem perdida   o Redis descarta (ou o `ack` do run em execução engole) a mensagem → re-despacho > 10 min → conclui
C6 duas corretoras    A dormindo, B acordando → nenhuma escrita cruza company_id · uma sombra `running` sem lease → intocada
C7 controle           C1 com o código de 04/10 → falha pelo motivo esperado (§9.3)
```

## 8. AS MIGRATIONS — APPLY / VERIFY / ROLLBACK escritos ANTES (MIGRATIONS-AUTHORITY §7)

Cabeçalho do §7 da autoridade em cada arquivo; APPLY `_01 → _02 → _03` pelo MCP `apply_migration`.
**`20261004_02_spec129a_espera_duravel.sql`** — estrutura · expand-first · não destrutiva.
```sql
-- APPLY
alter table public.work_runs add column if not exists wake_at timestamptz;
alter table public.work_runs add column if not exists wait_for jsonb;
create index if not exists idx_work_runs_despertar on public.work_runs (wake_at)
  where runtime_kind = 'smith' and status in ('waiting_input','retry_scheduled');
do $$ begin
  if not exists (select 1 from pg_constraint where conname='ck_work_runs_wake_so_da_fila') then
    alter table public.work_runs add constraint ck_work_runs_wake_so_da_fila check (wake_at is null or runtime_kind='smith') not valid;
    alter table public.work_runs validate constraint ck_work_runs_wake_so_da_fila;
  end if;
  if not exists (select 1 from pg_constraint where conname='ck_work_runs_espera_tem_relogio') then
    alter table public.work_runs add constraint ck_work_runs_espera_tem_relogio check (runtime_kind <> 'smith'
      or status not in ('waiting_input','retry_scheduled') or wake_at is not null) not valid;
    alter table public.work_runs validate constraint ck_work_runs_espera_tem_relogio;
  end if;
end $$;
-- VERIFY (esperado: 2 · 1 · 2)
select (select count(*) from information_schema.columns where table_schema='public' and table_name='work_runs'
          and column_name in ('wake_at','wait_for')) colunas,
       (select count(*) from pg_indexes where indexname='idx_work_runs_despertar') indice,
       (select count(*) from pg_constraint where conname in ('ck_work_runs_wake_so_da_fila','ck_work_runs_espera_tem_relogio')
          and convalidated) checks;
-- VERIFY comportamental: DO terminado em raise exception — smith waiting_input sem wake_at → recusado · acionamento
--   com wake_at → recusado · smith com wake_at → ACEITO (controle)
-- ROLLBACK (código antigo já implantado)
update work_runs set status='queued', wake_at=null where runtime_kind='smith' and status in ('waiting_input','retry_scheduled');
-- + insert em work_queue_outbox para cada um (o código antigo não re-despacha)
alter table work_runs drop constraint if exists ck_work_runs_espera_tem_relogio;
alter table work_runs drop constraint if exists ck_work_runs_wake_so_da_fila;
drop index if exists idx_work_runs_despertar;   -- colunas ficam (DROP COLUMN só com decisão do Founder, autoridade §8.6)
```

**`20261004_03_spec129a_retrato_mascarado.sql`** — dois gatilhos + função + DADO (P-223). Destrói PII **por decisão já
dada** (ficha §4). Regra única, em SQL: *um passo `dispatch_phase` guarda o cru só se for `monitoring` de run não-terminal.*
```sql
-- APPLY
create or replace function public.retrato_pode_ficar_cru(p_run uuid, p_company uuid, p_step_key text) returns boolean
language sql stable security definer set search_path=public as $$
  select p_step_key = 'monitoring' and exists (select 1 from work_runs r where r.id=p_run and r.company_id=p_company
         and r.status::text not in ('completed','failed','cancelled','expired')) $$;
create or replace function public.tg_work_steps_retrato() returns trigger language plpgsql security definer
set search_path=public as $$ begin
  if new.step_type='dispatch_phase' and not retrato_pode_ficar_cru(new.work_run_id, new.company_id, new.step_key) then
    new.output_summary := coalesce(new.output_redacted, '{"_retrato":"mascarado (SPEC-129-A)"}'::jsonb);
  end if; return new; end $$;
drop trigger if exists trg_work_steps_retrato on public.work_steps;
create trigger trg_work_steps_retrato before insert or update on public.work_steps for each row
  execute function public.tg_work_steps_retrato();
create or replace function public.tg_acionamento_fechado_mascara() returns trigger language plpgsql security definer
set search_path=public as $$ begin
  begin
    update work_steps s set output_summary = coalesce(s.output_redacted, '{"_retrato":"mascarado (SPEC-129-A)"}'::jsonb)
     where s.work_run_id=new.id and s.company_id=new.company_id and s.step_type='dispatch_phase'
       and s.output_summary is distinct from coalesce(s.output_redacted, '{"_retrato":"mascarado (SPEC-129-A)"}'::jsonb);
  exception when others then raise warning 'tg_acionamento_fechado_mascara %: %', new.id, sqlstate; end;
  return new; end $$;
drop trigger if exists trg_acionamento_fechado_mascara on public.work_runs;
create trigger trg_acionamento_fechado_mascara after update on public.work_runs for each row   -- TODO update de run fechado
  when (new.runtime_kind='acionamento' and new.status::text in ('completed','failed','cancelled','expired'))
  execute function public.tg_acionamento_fechado_mascara();
create or replace function public.work_steps_mascarar_vencidos(p_horas int default 24) returns int
language sql security definer set search_path=public as $$
  with m as (update work_steps set output_summary = coalesce(output_redacted, '{"_retrato":"mascarado (SPEC-129-A)"}'::jsonb)
    where step_type='dispatch_phase' and step_key='monitoring' and coalesce(finished_at, updated_at) < now() - make_interval(hours=>p_horas)
      and output_summary is distinct from coalesce(output_redacted, '{"_retrato":"mascarado (SPEC-129-A)"}'::jsonb) returning 1)
  select count(*)::int from m $$;
update public.work_steps set output_summary = output_summary where step_type='dispatch_phase';   -- backfill pelo gatilho
select public.work_steps_mascarar_vencidos(24);
-- VERIFY (esperado: 0 · 17 · 2 · 1) — 📊 dispatch_phase: 17 passos, 17 com gêmeo, 1 `monitoring` (de run fechado)
select (select count(*) from work_steps where output_summary::text ~ '"(titular_cpf|telefone_contato|client_phone)"\s*:\s*"[0-9]') cru,
       (select count(*) from work_steps where step_type='dispatch_phase' and output_summary = output_redacted) mascarados,
       (select count(*) from pg_trigger where tgname in ('trg_work_steps_retrato','trg_acionamento_fechado_mascara')) gatilhos,
       (select count(*) from pg_proc where proname='work_steps_mascarar_vencidos') funcao;
-- VERIFY comportamental (DO desfeito): passo `ura` cru de run vivo → mascarado · `monitoring` de run vivo → cru ·
--   UPDATE de run JÁ fechado com checkpoint novo → mascarado · passo de run `smith` → intocado
-- ROLLBACK drop dos 2 gatilhos e das 4 funções. O DADO não volta, por desenho; desastre: PITR. Antes do APPLY: md5 por
--   linha das 17 no relatório (nunca o conteúdo)
```
📊 Prova de que mascarar as 3 linhas do run VIVO não quebra a SPEC-085: seus passos são `ura`, `human_phase`,
`needs_human` (B5) e o único restaurável é `monitoring` ≤ 24 h (B6); o run está em `needs_human` desde 10/09. A reabertura
`test_aborted`→`needs_human` (B6) passa a gravar mascarado — `needs_human` nunca é restaurado. Os gatilhos não mudam
STATUS: "sem fila nunca é tocado" continua valendo para o estado.

**`20261004_01`** — §5. **MANIFEST:** 3 linhas (versão do banco, sha256[0:16], classe, VERIFY com saída real).

## 9. OS GATES (mutação dos guardas NOVOS, uma vez, worktree próprio, restaurado por cópia)

| # | gate | mutação que o deixa vermelho |
|---|---|---|
| G1 | fio C1–C7 verde; **sem banco = falha, não verde** | `_processar` conclui sem olhar `ESPERANDO` → C1 |
| G2 | cobrança: morto após o passo → `_execute_routine` ×1; no meio → +0 e `efeito_incerto`; `retry_scheduled` de 3 h (re-enfileirado) → `expired`, +0, evento visível, `routine_runs` fechado; 3 ramos da ponte | sem a checagem `succeeded` → ×2 |
| G3 | CAS: 2 leases → 1 ganha; `concluir` sobre `waiting_approval` → recusado; `cancelling` não vira `running`; o caso `banco_real` (2º UPDATE filtrado → 0 linhas) | `adquirir_lease` sem filtro → 2 ganham |
| G4 | despertador e re-despacho só `smith`, só workflow registrado; idade por `requested_at`; espera com `wait_for` nunca expira pela idade | tirar `runtime_kind` de `redespachar_parados` → a sombra `running` sem lease vira `queued` |
| G5 | Reprocessar grava outbox e o run RODA; "sem fila" e `efeito_incerto` → 409; cancelar direto não toca o acionamento | tirar o INSERT da outbox → `queued` para sempre |
| G6 | loop livre: ticker de 100 ms com atraso < 1 s durante `portal.operation`, inclusive C3 | ramo "já existe" sem `enqueue` com `PORTAL_GATEWAY_WAIT_S=3` → atraso ≥ 3 s |
| G7 | PII: VERIFY da `_03` = 0 cru e 17 mascarados; `guardar` com CPF → nada no banco; **lente do dado** reconta por caminho independente (PostgREST + `pii_da_sessao._classificar`) | tirar o gatilho `trg_acionamento_fechado_mascara` → checkpoint em run fechado volta cru |
| G8 | migrations pelo VERIFY · `grep -c "20261004_0[123]" backend/supabase/migrations/MANIFEST.md` → 3 | — |
| G9 | duas corretoras (C6; `as_portas` com `company_id` trocado → 404) | sem `.eq("company_id")` no despertador → C6 |
| G10 | bateria UMA vez, após o conserto, triada contra `docs/canon/reports/BATERIA-LINHA-DE-BASE.txt`; verdade vencida migra (§9.3) pelo dono do §7 | — |
| G11 | **pronto quando, em produção (CAIXA):** `system.espera_de_teste` dorme 10 min e acorda; reinício do `smith-worker` no meio → 1 `run.succeeded`, `ping` com 1 tentativa | — |

§9.1 não se aplica (nada em `app/`, `middleware.ts`, `next.config.js`, env) — entra se alguém tocar `app/`.
**Pronta quando** (ficha): dorme 10 min e acorda (C1, G11) · reinício sem duplicar (C2, C3, G11) · "tentar de novo" só para
o que pode rodar (G4, §5) · Reprocessar funciona (G5) · nenhum CPF em claro em `work_steps` (G7: 0 de 17) · manifesto (G8).

## 10. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS (§7.3)

| URL | o que faz | o que MODELAMOS | o que REJEITAMOS | como o juiz inspeciona |
|---|---|---|---|---|
| https://docs.temporal.io/workflow-execution/timers-delays | timer persistido; "Workers consume no additional resources while waiting" | run dormindo sem worker nem lease | trazer o Temporal (§5) | C2 |
| https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html (Wait for Callback + HeartbeatSeconds) | pausa até o token voltar; timeout contra espera eterna | `wait_for.ref` = token; `wait_for.prazo` = timeout | callback do portal-worker (D-129A-2) | C1; prazo vencido → `failed` |
| https://microservices.io/patterns/data/transactional-outbox.html | intenção no banco; "might publish a message more than once" | outbox após o CAS; duplicata morre na lease | 2PC Postgres+Redis | C5, G3 |
| https://www.postgresql.org/docs/current/sql-select.html (The Locking Clause, `SKIP LOCKED`) | "avoid lock contention with multiple consumers accessing a queue-like table" | quem não ganha a linha SEGUE: UPDATE filtrado com 0 linhas | `FOR UPDATE SKIP LOCKED` em RPC agora (D-129A-3) | G3 `banco_real` |
| https://redis.io/docs/latest/commands/xautoclaim/ | reclama pendente além de `min-idle-time`; o que saiu do stream é apagado da PEL | o Redis perde: o Postgres re-despacha | confiar só em `claim_abandonadas` (`queue.py:92`) | C5 |

## 11. A LISTA DE ATAQUES (juiz ‖ red team, cegos um ao outro, sobre o diff, os testes rodando e o banco)

1. Tocar o STATUS de um "sem fila" por qualquer caminho (lease, despertador, re-despacho, cancelar, Reprocessar, `decidir`, órfãos).
2. Dois workers: lease, despertar, outbox em dobro → duas execuções? `ack` de run em execução perde o despertar?
3. Cancelar na espera, entre o CAS e a outbox, e no passo.
4. Relógios: retry re-enfileirado escapa das 2 h? espera de 24 h expira ao acordar? `queued_at` regravado engana o "parado"?
5. `guardar` aceita texto livre, objeto aninhado ou PII?
6. Cobrança: algum ramo da ponte fora do passo externo? o aviso ao grupo sai duas vezes? a expirada some em silêncio?
7. `concluir`/`falhar` por cima de `waiting_approval`, `cancelled` ou lease alheia; `decidir` sobre aprovação já decidida.
8. Retrato: checkpoint em run fechado; reabertura `test_aborted`→`needs_human`; `monitoring` vivo restaurado; gatilho que falha bloqueia o fechamento?
9. Rollback da `_02` com runs dormindo; da `_01` com expirações de runtime (`expirado_pela_idade` não volta).
10. Duas corretoras: UPDATE com `company_id` de outra linha? `reprocessar` com `run_id` alheio?
11. O produto CHAMA o caminho? (C1 com o `SmithWorker` real; `system.espera_de_teste` registrado em produção)
12. `time.sleep` alcançável de handler registrado (`grep -rn "time.sleep" backend/app/services/work backend/app/services/portals`).
13. O backoff limita os ciclos do `needs_human`? `efeito_incerto` reprocessado vira laço?

## 12. PENDÊNCIAS TOCADAS

| pendência | destino |
|---|---|
| P-223 | **FECHADA** com G7 (0 de 17, sem exceção) |
| P-126-09 | **FECHADA** pelo D-129A-6 (discordância do §3 escrita) |
| P-126-24 | MANIFEST **já feito** (📊 `6880e62`); juiz fresco **CONTINUA** |
| P-093B-RLS | **CONTINUA** (a espera usa `work_runs`, não `work_waits`) |
| P-126-16 · P-198 · P-182 | **SAEM** (ficha v2.4) |
| nova P-129A-01 | quem perdeu as 21 mensagens (B9) — o re-despacho cobre; a causa fica por medir |
| nova P-129A-02 | despertar por EVENTO do portal (hoje ≤ 60 s) — 129-B/133-B |
| nova P-129A-03 | CPF em `work_runs.input_payload` do cálculo — a 129-B decide máscara ou cofre |
| nova P-129A-04 | reconciliar um `efeito_incerto` (hoje: 409 e mão humana) |

**A execução NÃO pode:** tocar status de "sem fila"; criar fila/laço/agendador; tocar `dispatch_router.py` ou o frontend;
ligar `PORTAL_EXECUTION_GATEWAY_MODE` em produção; nome de corretora em código, teste ou script (§13.9).

## 13. A CAIXA DO FOUNDER

| item | o que faz | custa esquecer | bloqueia? |
|---|---|---|---|
| **Implantar** `smith-worker` e `smith-api` após "migrations aplicadas" | põe o despertador no ar | o produto não espera | não |
| **Canário de 10 min** (G11): no `smith-api`, `--criar` (comando no relatório, provado no contêiner); aos ~3 min **Reiniciar** o `smith-worker`; aos 12 min `--conferir <id>` → "concluído · 1 execução" | prova o "pronto quando" | a 129-B espera |
| (opcional) B9 no `smith-worker` | diz quem perdeu as 21 mensagens | nada | não |
