-- Tenant Activation 1 — tabela tenant_corridors (ativação de corredor por corretora).
-- NÃO aplicada automaticamente. Aplicar no SQL editor do Supabase.
-- Espelha o padrão tenant_auxiliaries: corridor_templates (global) → tenant_corridors (instalado/ativado).
-- Regra: corredor GLOBAL só opera para a corretora se houver linha aqui com status='active'.

-- ============ APPLY ============
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

alter table public.tenant_corridors enable row level security;

-- service_role (backend) faz tudo; o app acessa via service role como já faz nas demais tabelas.
drop policy if exists tenant_corridors_service_all on public.tenant_corridors;
create policy tenant_corridors_service_all on public.tenant_corridors
  for all to service_role using (true) with check (true);

-- (Opcional p/ acesso direto autenticado por tenant — mantém isolamento; o app usa service role)
-- create policy tenant_corridors_tenant_read on public.tenant_corridors
--   for select to authenticated using (company_id = (auth.jwt() ->> 'company_id')::uuid);

-- ============ VERIFY ============
-- select table_name from information_schema.tables where table_schema='public' and table_name='tenant_corridors';
-- select count(*) from public.tenant_corridors;
-- select polname, polcmd from pg_policies where tablename='tenant_corridors';

-- ============ ROLLBACK ============
-- drop table if exists public.tenant_corridors cascade;
