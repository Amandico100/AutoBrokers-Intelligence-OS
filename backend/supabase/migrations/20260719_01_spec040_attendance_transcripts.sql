-- SPEC-040 Onda 1 — Espelho de Atendimento (Parte 1): captura das conversas
-- da equipe da corretora com os segurados dela (numero corporativo autorizado).
-- PII vive AQUI e so aqui (RLS service-only; NUNCA vai ao RAG global).
-- Retencao do cru: purge diario (env ATTENDANCE_RETENTION_DAYS, default 90).
-- Schema identico a observed_events/observed_sessions de proposito: o codigo
-- de armazenamento e compartilhado (tabela parametrizada), sem logica duplicada.
--
-- APPLY ------------------------------------------------------------------
create table if not exists public.attendance_transcripts (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null,
  observer_number text not null,
  counterparty text not null,
  insurer_key text,
  direction text not null,
  msg_type text not null,
  text text,
  interactive jsonb,
  media_meta jsonb,
  message_id text,
  wa_timestamp timestamptz,
  session_id uuid,
  source text not null default 'live',
  created_at timestamptz not null default now()
);

create unique index if not exists ux_attendance_transcripts_dedupe
  on public.attendance_transcripts (observer_number, message_id);
create index if not exists ix_attendance_transcripts_lookup
  on public.attendance_transcripts (company_id, counterparty, wa_timestamp desc);
create index if not exists ix_attendance_transcripts_created
  on public.attendance_transcripts (created_at);

create table if not exists public.attendance_sessions (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null,
  observer_number text not null,
  counterparty text not null,
  insurer_key text,
  started_at timestamptz not null,
  last_event_at timestamptz not null,
  status text not null default 'open',
  ramo text,
  servico text,
  summary jsonb,
  created_at timestamptz not null default now()
);

create index if not exists ix_attendance_sessions_lookup
  on public.attendance_sessions (company_id, observer_number, counterparty, status);
create index if not exists ix_attendance_sessions_created
  on public.attendance_sessions (created_at);

alter table public.attendance_transcripts enable row level security;
alter table public.attendance_sessions enable row level security;
-- service-only por design: NENHUMA policy e criada — somente o service role
-- (backend) le/escreve. Dashboard da corretora nao enxerga transcripts crus.

-- VERIFY -----------------------------------------------------------------
-- select count(*) from public.attendance_transcripts;
-- select count(*) from public.attendance_sessions;
-- select relrowsecurity from pg_class where relname in
--   ('attendance_transcripts','attendance_sessions');  -- ambas true
--
-- ROLLBACK ---------------------------------------------------------------
-- drop table if exists public.attendance_transcripts;
-- drop table if exists public.attendance_sessions;
