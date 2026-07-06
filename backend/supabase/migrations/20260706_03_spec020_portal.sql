-- SPEC-020 P1 — Portais no Smith (portal_jobs / portal_accounts / portal_sessions).
-- EXPAND-ONLY. O portal-worker (serviço próprio) faz poll em portal_jobs e roda
-- journeys Playwright determinísticas. Credenciais/sessões cifradas (Fernet) —
-- NUNCA em claro. Gate PORTAL_REAL_ENABLED (no worker) fica OFF até o founder ligar.
--
-- APPLY:   SQL Editor do Supabase (idempotente).
-- VERIFY:  select table_name from information_schema.tables
--          where table_name in ('portal_jobs','portal_accounts','portal_sessions');
-- ROLLBACK: drop table if exists public.portal_jobs;
--           drop table if exists public.portal_sessions;
--           drop table if exists public.portal_accounts;

-- Contas de portal por corretora (credencial cifrada no cofre do worker).
create table if not exists public.portal_accounts (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null,
  portal_key text not null,                 -- ex: 'vidros_lanternas'
  account_label text not null default 'principal',
  username text,                            -- login pode ficar claro; senha NUNCA
  secret_encrypted text,                    -- Fernet(PORTAL_VAULT_KEY) da senha
  health text not null default 'unknown',   -- unknown|ok|needs_human|failed
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (company_id, portal_key, account_label)
);
create index if not exists idx_portal_accounts_company on public.portal_accounts (company_id);

-- Sessões persistidas (storage_state cifrado) por conta — reaproveita login.
create table if not exists public.portal_sessions (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null,
  portal_key text not null,
  account_label text not null default 'principal',
  storage_state_encrypted text,             -- Fernet do storage_state JSON do Playwright
  verified_at timestamptz,
  health text not null default 'unknown',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (company_id, portal_key, account_label)
);

-- Fila de trabalhos do worker (poll, sem Redis novo).
create table if not exists public.portal_jobs (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null,
  portal_key text not null,
  journey text not null,                     -- ex: 'login_check', 'abrir_pedido'
  account_id uuid references public.portal_accounts(id) on delete set null,
  params jsonb not null default '{}'::jsonb,
  status text not null default 'queued',      -- queued|running|needs_human|done|failed
  evidence jsonb not null default '{}'::jsonb,
  screenshots jsonb not null default '[]'::jsonb,
  error text,
  attempts int not null default 0,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);
create index if not exists idx_portal_jobs_queued on public.portal_jobs (status, created_at) where status = 'queued';
create index if not exists idx_portal_jobs_company on public.portal_jobs (company_id);

comment on table public.portal_jobs is
  'SPEC-020: fila de journeys de portal. status queued->running->(done|needs_human|failed). worker faz poll a cada ~30s.';
