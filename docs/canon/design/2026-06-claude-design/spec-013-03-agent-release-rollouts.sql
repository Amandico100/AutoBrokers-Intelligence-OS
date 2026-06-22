-- SPEC-013 Fase B P4 — Runbook 03: agent_release_rollouts (rollout de release → tenant)
-- Aplicar APÓS os runbooks 01 e 02. NÃO aplicado por mim. Transacional, RLS, índices.
-- Rastreia qual release está aplicada em cada instância de corretora + histórico/rollback.
-- ============================================================================
-- APPLY
-- ============================================================================
begin;

create table if not exists public.agent_release_rollouts (
  id uuid primary key default gen_random_uuid(),
  release_id uuid not null references public.agent_blueprint_releases(id) on delete cascade,
  blueprint_key text not null,
  company_id uuid not null references public.companies(id) on delete cascade,
  tenant_agent_id uuid references public.agents(id) on delete set null,
  status text not null default 'active'
    check (status in ('pending','canary','active','paused','failed','rolled_back')),
  previous_release_id uuid references public.agent_blueprint_releases(id) on delete set null,
  applied_by uuid,
  applied_at timestamptz not null default now(),
  rollback_by uuid,
  rollback_at timestamptz,
  error text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_arr_company_bp on public.agent_release_rollouts (company_id, blueprint_key, status);
create index if not exists idx_arr_release on public.agent_release_rollouts (release_id);

alter table public.agent_release_rollouts enable row level security;
revoke all on public.agent_release_rollouts from anon, authenticated;
drop policy if exists arr_service_all on public.agent_release_rollouts;
create policy arr_service_all on public.agent_release_rollouts
  for all to service_role using (true) with check (true);

commit;

-- ============================================================================
-- VERIFY
-- ============================================================================
-- select to_regclass('public.agent_release_rollouts') as tabela;
-- select relrowsecurity from pg_class where relname='agent_release_rollouts';
-- select policyname, cmd, roles from pg_policies where schemaname='public' and tablename='agent_release_rollouts';
-- select count(*) as rollouts from public.agent_release_rollouts;  -- 0 esperado inicialmente

-- ============================================================================
-- ROLLBACK
-- ============================================================================
-- begin;
--   drop table if exists public.agent_release_rollouts;
-- commit;
