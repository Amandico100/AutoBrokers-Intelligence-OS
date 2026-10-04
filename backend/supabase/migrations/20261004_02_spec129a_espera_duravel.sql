-- =============================================================
-- MIGRATION: 20261004_02_spec129a_espera_duravel
-- SPEC:      SPEC-129-A — §6 O DESENHO DA ESPERA DURÁVEL · §8 (estrutura)
-- AUTOR:     builder F4 (Opus 5.5)            DATA: 2026-10-04
-- OBJETIVO:  um trabalho `smith` pode DORMIR com relógio: `wake_at` (quando acordar) e `wait_for`
--            ({"tipo","ref","prazo","passo","acordou","intervalo_s"} — o que espera), um índice parcial
--            para o despertador e duas travas no banco: o relógio só existe na fila, e espera de fila
--            sem relógio é recusada (ninguém a acordaria).
--
-- 📊 ANTES (04/10/2026, `execute_sql` só leitura):
--    · work_run_status: draft|queued|planning|running|waiting_approval|waiting_input|paused|
--      retry_scheduled|cancelling|cancelled|failed|completed|expired (D-129A-1: `waiting_input` já existe;
--      nenhum ADD VALUE).
--    · work_runs: sem `wake_at`, sem `wait_for`; há `next_attempt_at` (continua, compat); nenhum CHECK de status.
--    · smith em waiting_input/retry_scheduled: 0 → os dois CHECKs validam sem recusar linha nenhuma.
--
-- APPLY:  2 colunas (add if not exists) · índice parcial `idx_work_runs_despertar` (if not exists) ·
--         `ck_work_runs_wake_so_da_fila` e `ck_work_runs_espera_tem_relogio` (NOT VALID → VALIDATE, só se
--         ainda não existirem). Idempotente.
--
-- VERIFY (read-only · esperado: 2 · 1 · 2):
--   select (select count(*) from information_schema.columns where table_schema='public' and table_name='work_runs'
--             and column_name in ('wake_at','wait_for')) colunas,
--          (select count(*) from pg_indexes where schemaname='public' and indexname='idx_work_runs_despertar') indice,
--          (select count(*) from pg_constraint where conrelid='public.work_runs'::regclass
--             and conname in ('ck_work_runs_wake_so_da_fila','ck_work_runs_espera_tem_relogio') and convalidated) checks;
--
-- VERIFY comportamental (o DO desfaz o que testa — subtransação terminada em raise):
--   do $$
--   declare v_smith uuid; v_acion uuid; r_sem_relogio text := 'aceito'; r_acion text := 'aceito'; r_ctrl text := 'recusado';
--   begin
--     select id into v_smith from public.work_runs where runtime_kind='smith' and status='completed' limit 1;
--     select id into v_acion from public.work_runs where runtime_kind='acionamento'
--       and status::text in ('completed','cancelled') limit 1;
--     begin update public.work_runs set status='waiting_input' where id=v_smith;              -- sem wake_at
--       raise exception using errcode='P0001', message='desfaz';
--     exception when check_violation then r_sem_relogio := 'recusado'; when sqlstate 'P0001' then null; end;
--     begin update public.work_runs set wake_at=now() where id=v_acion;                       -- "sem fila" com relógio
--       raise exception using errcode='P0001', message='desfaz';
--     exception when check_violation then r_acion := 'recusado'; when sqlstate 'P0001' then null; end;
--     begin update public.work_runs set status='waiting_input', wake_at=now()+interval '5 minutes' where id=v_smith;
--       r_ctrl := 'aceito';                                                                     -- CONTROLE
--       raise exception using errcode='P0001', message='desfaz';
--     exception when check_violation then r_ctrl := 'recusado'; when sqlstate 'P0001' then null; end;
--     if (r_sem_relogio, r_acion, r_ctrl) is distinct from ('recusado','recusado','aceito') then
--       raise exception 'VERIFY 20261004_02 FALHOU: sem_relogio=% acionamento_com_wake=% controle=%', r_sem_relogio, r_acion, r_ctrl;
--     end if;
--     raise notice 'VERIFY 20261004_02 OK: smith sem relógio recusado · acionamento com wake_at recusado · smith com wake_at aceito';
--   end $$;
--
-- ROLLBACK (com o código ANTIGO já reimplantado — ele não relê waiting_input/retry_scheduled de `smith`):
--   with voltam as (
--     update public.work_runs set status='queued', wake_at=null, wait_for=null, queued_at=now(),
--            lease_owner=null, lease_token=null, lease_expires_at=null
--      where runtime_kind='smith' and status in ('waiting_input','retry_scheduled')
--     returning id, company_id, current_step_key)
--   insert into public.work_queue_outbox (company_id, work_run_id, event_kind, payload_minimal)
--   select company_id, id, 'run.recovered',
--          jsonb_build_object('run_id', id::text, 'company_id', company_id::text, 'retomar_de', current_step_key)
--     from voltam;                                       -- o código antigo não re-despacha: o outbox o faz
--   alter table public.work_runs drop constraint if exists ck_work_runs_espera_tem_relogio;
--   alter table public.work_runs drop constraint if exists ck_work_runs_wake_so_da_fila;
--   drop index if exists public.idx_work_runs_despertar;
--   -- as COLUNAS ficam (DROP COLUMN só com decisão do Founder — MIGRATIONS-AUTHORITY §8.6).
--
-- EXPAND-FIRST: sim (só adiciona; nada é removido nem renomeado)
-- DESTRUTIVA:   não
-- ORDEM:        _01 → _02 → _03 · ANTES do código da F1 (que grava wake_at/wait_for)
-- =============================================================

alter table public.work_runs add column if not exists wake_at  timestamptz;
alter table public.work_runs add column if not exists wait_for jsonb;

comment on column public.work_runs.wake_at  is
  'SPEC-129-A: quando o despertador (laço de órfãos do smith-worker) devolve o run à fila. Só runtime_kind=smith.';
comment on column public.work_runs.wait_for is
  'SPEC-129-A: o que o run espera — {"tipo","ref","prazo","passo","acordou","intervalo_s"}. Ids e estados; nunca PII.';

create index if not exists idx_work_runs_despertar on public.work_runs (wake_at)
  where runtime_kind = 'smith' and status in ('waiting_input', 'retry_scheduled');

do $$
begin
  if not exists (select 1 from pg_constraint
                  where conrelid = 'public.work_runs'::regclass and conname = 'ck_work_runs_wake_so_da_fila') then
    alter table public.work_runs add constraint ck_work_runs_wake_so_da_fila
      check (wake_at is null or runtime_kind = 'smith') not valid;
    alter table public.work_runs validate constraint ck_work_runs_wake_so_da_fila;
  end if;
  if not exists (select 1 from pg_constraint
                  where conrelid = 'public.work_runs'::regclass and conname = 'ck_work_runs_espera_tem_relogio') then
    alter table public.work_runs add constraint ck_work_runs_espera_tem_relogio
      check (runtime_kind <> 'smith' or status not in ('waiting_input', 'retry_scheduled') or wake_at is not null) not valid;
    alter table public.work_runs validate constraint ck_work_runs_espera_tem_relogio;
  end if;
end $$;
