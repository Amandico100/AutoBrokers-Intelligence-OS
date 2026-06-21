-- Tenant Activation 1 — tabela tenant_corridors (HARDENED, Batch 2 Parte 0).
-- NÃO aplicada automaticamente. Aplicar ANTES da migração da Resulta.
-- Espelha tenant_auxiliaries: corridor_templates (global) → tenant_corridors (ativado).
-- Regra: corredor GLOBAL só opera se houver linha aqui com status='active'.

-- ============ APPLY ============
begin;

create table if not exists public.tenant_corridors (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id) on delete cascade,
  corridor_template_id uuid not null references public.corridor_templates(id) on delete cascade,
  status text not null default 'active' check (status in ('active','paused')),
  settings jsonb not null default '{}'::jsonb,
  installed_by uuid,
  installed_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (company_id, corridor_template_id)
);

create index if not exists idx_tenant_corridors_company on public.tenant_corridors (company_id);
create index if not exists idx_tenant_corridors_active on public.tenant_corridors (company_id, status);

-- updated_at automático em toda mutação.
create or replace function public.tg_tenant_corridors_set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at := now(); return new; end $$;

drop trigger if exists trg_tenant_corridors_updated_at on public.tenant_corridors;
create trigger trg_tenant_corridors_updated_at
  before update on public.tenant_corridors
  for each row execute function public.tg_tenant_corridors_set_updated_at();

-- RLS: o app acessa via service_role (que bypassa RLS). anon/authenticated NÃO leem direto.
alter table public.tenant_corridors enable row level security;
revoke all on public.tenant_corridors from anon, authenticated;

drop policy if exists tenant_corridors_service_all on public.tenant_corridors;
create policy tenant_corridors_service_all on public.tenant_corridors
  for all to service_role using (true) with check (true);

commit;

-- ============ VERIFY ============
-- select to_regclass('public.tenant_corridors');                 -- não-nulo
-- select polname, polcmd, roles from pg_policies where tablename='tenant_corridors';
-- select tgname from pg_trigger where tgrelid='public.tenant_corridors'::regclass and not tgisinternal;
-- select count(*) from public.tenant_corridors;

-- ============ ROLLBACK ============
-- drop table if exists public.tenant_corridors cascade;
-- drop function if exists public.tg_tenant_corridors_set_updated_at();
