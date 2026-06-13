-- ============================================================================
-- 20260613 — Human Support Destinations Foundation (registro canônico)
-- ----------------------------------------------------------------------------
-- Representa, de forma IDEMPOTENTE, a fundação do DESTINO HUMANO DE SUPORTE
-- (handoff) já aplicada manualmente no Supabase pelo Architect/Founder.
-- Objetivo: evitar DRIFT entre Supabase e repositório. NÃO executar aqui.
--
-- Base canônica: plano 42H1P.
-- Decisões: config oficial em Personalização → Corretora → Suporte humano;
-- API operacional futura em /api/attendance/support-destinations;
-- CREDENCIAIS/TOKENS NÃO ficam nesta tabela — sempre no Vault/tenant_connections
-- (aqui só destination_ref/display_ref + regras operacionais de handoff).
--
-- Padrão espelhado do schema real / 39A1 / 20260612: gen_random_uuid(),
-- public.update_updated_at_column(), RLS service_role + company via
-- users_v2/auth.uid(), enums como text + CHECK.
--
-- NÃO faz seed (nenhum destino de teste). NÃO altera attendance_cases,
-- corridor_runs, dispatch_packets, tenant_connections, approval_requests,
-- vault_audit_log, integrations, companies, users_v2, agents.
-- SEM segredos. SEM PII.
-- ============================================================================

begin;

-- 0. Extensão (idempotente)
create extension if not exists pgcrypto;

-- 1. Tabela — human_support_destinations
create table if not exists public.human_support_destinations (
  id uuid primary key default gen_random_uuid(),

  company_id uuid not null references public.companies(id) on delete cascade,

  name text not null,

  destination_type text not null
    check (destination_type in (
      'whatsapp_group',
      'whatsapp_individual',
      'email',
      'internal_queue',
      'webhook'
    )),

  channel_provider text not null default 'manual'
    check (channel_provider in (
      'zapi',
      'evolution',
      'meta_cloud',
      'manual'
    )),

  tenant_connection_id uuid null references public.tenant_connections(id) on delete set null,

  destination_ref text not null,
  display_ref text null,

  is_primary boolean not null default false,
  priority_order integer not null default 100 check (priority_order >= 0),
  fallback_enabled boolean not null default false,

  silence_minutes integer not null default 0 check (silence_minutes >= 0),

  active_hours jsonb not null default '{}'::jsonb,
  escalation_rules jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,

  is_active boolean not null default true,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  check (jsonb_typeof(active_hours) = 'object'),
  check (jsonb_typeof(escalation_rules) = 'array'),
  check (jsonb_typeof(metadata) = 'object')
);

-- 2. Trigger updated_at (reutiliza a função canônica existente)
drop trigger if exists trg_human_support_destinations_updated_at
on public.human_support_destinations;

create trigger trg_human_support_destinations_updated_at
before update on public.human_support_destinations
for each row
execute function public.update_updated_at_column();

-- 3. Índices
create index if not exists idx_human_support_destinations_company_id
on public.human_support_destinations(company_id);

create index if not exists idx_human_support_destinations_company_active
on public.human_support_destinations(company_id, is_active);

create index if not exists idx_human_support_destinations_company_primary
on public.human_support_destinations(company_id, is_primary);

create index if not exists idx_human_support_destinations_company_priority
on public.human_support_destinations(company_id, priority_order);

create index if not exists idx_human_support_destinations_tenant_connection_id
on public.human_support_destinations(tenant_connection_id);

-- No máximo 1 destino primário ATIVO por corretora.
create unique index if not exists ux_human_support_destinations_one_primary_active
on public.human_support_destinations(company_id)
where is_primary = true and is_active = true;

-- 4. RLS + policies (service_role full + company via users_v2/auth.uid())
alter table public.human_support_destinations enable row level security;

drop policy if exists "human_support_destinations_service_role_all"
on public.human_support_destinations;

create policy "human_support_destinations_service_role_all"
on public.human_support_destinations
for all
to service_role
using (true)
with check (true);

drop policy if exists "human_support_destinations_company_select"
on public.human_support_destinations;

create policy "human_support_destinations_company_select"
on public.human_support_destinations
for select
to authenticated
using (
  company_id = (
    select u.company_id
    from public.users_v2 u
    where u.id = auth.uid()
  )
);

drop policy if exists "human_support_destinations_company_insert"
on public.human_support_destinations;

create policy "human_support_destinations_company_insert"
on public.human_support_destinations
for insert
to authenticated
with check (
  company_id = (
    select u.company_id
    from public.users_v2 u
    where u.id = auth.uid()
  )
);

drop policy if exists "human_support_destinations_company_update"
on public.human_support_destinations;

create policy "human_support_destinations_company_update"
on public.human_support_destinations
for update
to authenticated
using (
  company_id = (
    select u.company_id
    from public.users_v2 u
    where u.id = auth.uid()
  )
)
with check (
  company_id = (
    select u.company_id
    from public.users_v2 u
    where u.id = auth.uid()
  )
);

commit;

-- ============================================================================
-- ROLLBACK MANUAL — NÃO RODAR POR PADRÃO
-- ----------------------------------------------------------------------------
-- begin;
-- drop table if exists public.human_support_destinations cascade;
-- commit;
--
-- Remove a tabela + índices/policies/trigger. NÃO toca em nada mais.
-- ============================================================================
