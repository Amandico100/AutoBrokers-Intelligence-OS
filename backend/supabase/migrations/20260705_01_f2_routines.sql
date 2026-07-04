-- F2 — Motor de Rotinas (Claude-Rotinas/Hermes-like) — EXPAND-ONLY.
-- Rotina = receita em linguagem natural que um agente da corretora executa
-- sozinho no horário agendado, entregando o resultado onde o corretor pedir.
--
-- APPLY:   SQL Editor do Supabase (idempotente).
-- VERIFY:  select count(*) from public.routines;
-- ROLLBACK: drop table if exists public.routine_runs; drop table if exists public.routines;

create table if not exists public.routines (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null,
  created_by uuid,
  agent_id uuid,
  name text not null,
  instructions text not null,
  schedule jsonb not null default '{}'::jsonb,
  delivery jsonb not null default '{}'::jsonb,
  timezone text not null default 'America/Sao_Paulo',
  is_active boolean not null default true,
  last_run_at timestamptz,
  next_run_at timestamptz,
  consecutive_failures int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.routines is
  'F2: rotinas agendadas por corretora. schedule={kind:daily,time:HH:MM,weekdays:[0-6]?}|{kind:interval,minutes:N}; delivery={channel:whatsapp,number}|{channel:none}';

create index if not exists idx_routines_due
  on public.routines (next_run_at) where is_active = true;
create index if not exists idx_routines_company
  on public.routines (company_id);

create table if not exists public.routine_runs (
  id uuid primary key default gen_random_uuid(),
  routine_id uuid not null references public.routines(id) on delete cascade,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running',
  output_preview text,
  error text
);

create index if not exists idx_routine_runs_routine
  on public.routine_runs (routine_id, started_at desc);
