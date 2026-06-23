-- SPEC-013 FB-2 — Runbook 08: base canônica de Aprovadores (governança). NÃO aplicado por mim.
-- Apenas a tabela + RLS. NÃO liga nenhuma ação externa. UI/seleção entram numa etapa simples depois.
-- ============================================================================
-- APPLY
-- ============================================================================
begin;

create table if not exists public.company_approvers (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id) on delete cascade,
  user_id uuid not null references public.users_v2(id) on delete cascade,
  role text,
  scope text not null check (scope in ('external_action','portal','whatsapp','billing','knowledge_publish')),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (company_id, user_id, scope)
);

create index if not exists idx_company_approvers_company on public.company_approvers (company_id, scope, is_active);

alter table public.company_approvers enable row level security;
revoke all on public.company_approvers from anon, authenticated;
drop policy if exists company_approvers_service_all on public.company_approvers;
create policy company_approvers_service_all on public.company_approvers
  for all to service_role using (true) with check (true);

commit;

-- ============================================================================
-- VERIFY
-- ============================================================================
-- select to_regclass('public.company_approvers') as tabela;
-- select relrowsecurity from pg_class where relname='company_approvers';
-- select policyname from pg_policies where tablename='company_approvers';

-- ============================================================================
-- ROLLBACK
-- ============================================================================
-- begin; drop table if exists public.company_approvers; commit;
