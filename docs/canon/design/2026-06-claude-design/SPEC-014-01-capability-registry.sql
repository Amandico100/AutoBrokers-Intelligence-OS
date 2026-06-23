-- SPEC-014 C1 — Runbook 01: Capability Registry (tabelas + RLS + seed). NÃO aplicado por mim.
-- Reusa tenant_connections/permission_grants/approval_requests (NÃO duplica Vault).
-- O seed espelha lib/capabilities/catalog.ts (fonte única). Idempotente.
-- ============================================================================
-- APPLY
-- ============================================================================
begin;

-- 1. Catálogo global de capabilities
create table if not exists public.capabilities (
  capability_key text primary key,
  name text not null,
  category text not null check (category in ('knowledge','productivity','research','sales','insurance_ops','communication','internal')),
  owner text not null check (owner in ('platform','tenant','operational')),
  risk text not null check (risk in ('low','medium','high')),
  requires_connection boolean not null default false,
  requires_approval boolean not null default false,
  provider text,
  is_active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 2. Matriz de autorização: capability × papel do agente
create table if not exists public.capability_bindings (
  id uuid primary key default gen_random_uuid(),
  capability_key text not null references public.capabilities(capability_key) on delete cascade,
  agent_role text not null check (agent_role in ('core','attendance','auxiliary','subagent')),
  enabled boolean not null default true,
  scope jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (capability_key, agent_role)
);

-- 3. Entitlement por corretora (liga à conexão real do Vault quando preciso)
create table if not exists public.tenant_capability_entitlements (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id) on delete cascade,
  capability_key text not null references public.capabilities(capability_key) on delete cascade,
  enabled boolean not null default true,
  limits jsonb not null default '{}'::jsonb,
  connection_id uuid references public.tenant_connections(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (company_id, capability_key)
);
create index if not exists idx_tce_company on public.tenant_capability_entitlements (company_id, enabled);

-- RLS: service_role only (mesmo padrão de company_approvers)
alter table public.capabilities enable row level security;
alter table public.capability_bindings enable row level security;
alter table public.tenant_capability_entitlements enable row level security;
do $$ begin
  perform 1;
  revoke all on public.capabilities, public.capability_bindings, public.tenant_capability_entitlements from anon, authenticated;
end $$;
drop policy if exists cap_service_all on public.capabilities;
create policy cap_service_all on public.capabilities for all to service_role using (true) with check (true);
drop policy if exists capb_service_all on public.capability_bindings;
create policy capb_service_all on public.capability_bindings for all to service_role using (true) with check (true);
drop policy if exists tce_service_all on public.tenant_capability_entitlements;
create policy tce_service_all on public.tenant_capability_entitlements for all to service_role using (true) with check (true);

-- SEED do catálogo (espelha lib/capabilities/catalog.ts §5)
insert into public.capabilities (capability_key, name, category, owner, risk, requires_connection, requires_approval, provider) values
  ('knowledge.global.search','Conhecimento global AutoBrokers','knowledge','platform','low',false,false,'rag'),
  ('knowledge.tenant.search','Conhecimento privado da corretora','knowledge','tenant','low',false,false,'rag'),
  ('memory.company.read_write','Memória da corretora','internal','tenant','low',false,false,'memory'),
  ('memory.user.read_write','Memória do usuário','internal','tenant','low',false,false,'memory'),
  ('control_plane.read','Estado operacional da corretora','internal','platform','low',false,false,null),
  ('platform.web.search','Busca na web','research','platform','low',false,false,'tavily'),
  ('platform.document.extract','Leitura/OCR de documentos','productivity','platform','low',false,false,'docling'),
  ('operational.infocap.policy_lookup.read','Consulta de apólice (InfoCap)','insurance_ops','operational','high',true,false,'infocap'),
  ('operational.policy_evidence.read','Evidência de cobertura','insurance_ops','operational','medium',true,false,'infocap'),
  ('tenant.google_drive.read','Google Drive (leitura)','productivity','tenant','medium',true,false,'mcp:google-drive'),
  ('tenant.google_calendar.read_write','Google Calendar','productivity','tenant','medium',true,true,'mcp:google-calendar'),
  ('tenant.slack.read_write','Slack','communication','tenant','medium',true,true,'mcp:slack'),
  ('tenant.notion.read_write','Notion','productivity','tenant','medium',true,true,'notion'),
  ('operational.whatsapp.send','Enviar WhatsApp','communication','operational','high',true,true,'zapi'),
  ('operational.portal.policy.read','Portal — apólice (leitura)','insurance_ops','operational','high',true,false,'portal_browser'),
  ('operational.portal.billing.read','Portal — cobrança (leitura)','insurance_ops','operational','high',true,false,'portal_browser'),
  ('operational.portal.assistance.read','Portal — assistência (leitura)','insurance_ops','operational','high',true,false,'portal_browser'),
  ('operational.portal.assistance.prepare','Portal — preparar abertura','insurance_ops','operational','high',true,false,'portal_browser'),
  ('operational.portal.assistance.request','Portal — abrir assistência','insurance_ops','operational','high',true,true,'portal_browser')
on conflict (capability_key) do update set
  name=excluded.name, category=excluded.category, owner=excluded.owner, risk=excluded.risk,
  requires_connection=excluded.requires_connection, requires_approval=excluded.requires_approval,
  provider=excluded.provider, updated_at=now();

-- SEED da matriz (espelha lib/capabilities/catalog.ts §6). Gera bindings (capability × papel).
-- core
insert into public.capability_bindings (capability_key, agent_role) values
  ('knowledge.global.search','core'),('knowledge.tenant.search','core'),('memory.company.read_write','core'),
  ('memory.user.read_write','core'),('control_plane.read','core'),('platform.web.search','core'),
  ('platform.document.extract','core'),('operational.infocap.policy_lookup.read','core'),('operational.policy_evidence.read','core'),
  ('tenant.google_drive.read','core'),('tenant.google_calendar.read_write','core'),('tenant.slack.read_write','core'),('tenant.notion.read_write','core'),
  -- attendance
  ('knowledge.tenant.search','attendance'),('memory.company.read_write','attendance'),('memory.user.read_write','attendance'),
  ('platform.document.extract','attendance'),('operational.infocap.policy_lookup.read','attendance'),('operational.policy_evidence.read','attendance'),
  ('operational.whatsapp.send','attendance'),('operational.portal.policy.read','attendance'),('operational.portal.billing.read','attendance'),
  ('operational.portal.assistance.read','attendance'),('operational.portal.assistance.prepare','attendance'),('operational.portal.assistance.request','attendance'),
  -- auxiliary
  ('knowledge.tenant.search','auxiliary'),('memory.company.read_write','auxiliary'),('platform.web.search','auxiliary'),
  ('platform.document.extract','auxiliary'),('operational.whatsapp.send','auxiliary'),('tenant.google_drive.read','auxiliary'),
  ('tenant.notion.read_write','auxiliary'),('tenant.slack.read_write','auxiliary'),
  -- subagent
  ('knowledge.tenant.search','subagent'),('platform.web.search','subagent'),('platform.document.extract','subagent')
on conflict (capability_key, agent_role) do nothing;

commit;

-- ============================================================================
-- VERIFY
-- ============================================================================
-- select count(*) as caps from public.capabilities;                 -- esperado: 19
-- select agent_role, count(*) from public.capability_bindings group by 1 order by 1;
-- select policyname from pg_policies where tablename in ('capabilities','capability_bindings','tenant_capability_entitlements');

-- ============================================================================
-- ROLLBACK
-- ============================================================================
-- begin;
--   drop table if exists public.tenant_capability_entitlements;
--   drop table if exists public.capability_bindings;
--   drop table if exists public.capabilities;
-- commit;
