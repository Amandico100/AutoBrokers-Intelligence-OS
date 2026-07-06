-- ============================================================================
-- SPEC-020 — RODE ESTAS 4 MIGRATIONS NO SQL EDITOR DO SUPABASE (em ordem).
-- Sao expand-only e idempotentes (pode rodar de novo sem efeito).
-- Gerado por Opus 4.8 em 2026-07-06. As 01/02 (SPEC-019) voce ja rodou.
-- ============================================================================


-- >>>>>>>>>>>>>>>>>> 20260706_03_spec020_portal.sql <<<<<<<<<<<<<<<<<<

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

-- >>>>>>>>>>>>>>>>>> 20260706_04_spec020_portals_registry.sql <<<<<<<<<<<<<<<<<<

-- SPEC-020 — Registro GLOBAL de portais (URLs iguais para TODAS as corretoras).
-- EXPAND-ONLY. O que muda por corretora é só o login/senha (em portal_accounts,
-- cifrado, escopado por company_id). Aqui ficam apenas endereços/metadados públicos.
--
-- APPLY:   SQL Editor do Supabase (idempotente).
-- VERIFY:  select key, name, category from public.portals order by sort_order;
-- ROLLBACK: drop table if exists public.portals;

create table if not exists public.portals (
  id uuid primary key default gen_random_uuid(),
  key text not null unique,                        -- ex: 'vidros_abraseuatendimento'
  name text not null,
  login_url text not null,
  category text not null default 'seguradora',     -- vidros | corretor | sinistro
  insurer_key text,                                -- allianz, alfa, azul, bradesco... (opcional)
  cred_kind text not null default 'login_password',
  is_active boolean not null default true,
  sort_order int not null default 100,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_portals_active on public.portals (is_active, sort_order);

comment on table public.portals is
  'SPEC-020: registro GLOBAL de portais (endereços iguais p/ todas as corretoras). Credencial por corretora fica em portal_accounts (cifrada).';

-- Seed inicial (idempotente por key). Portal de VIDROS primeiro (prioridade do founder).
insert into public.portals (key, name, login_url, category, insurer_key, sort_order)
select 'vidros_abraseuatendimento', 'Portal de Vidros — Abra Seu Atendimento', 'https://abraseuatendimento.com.br/#/', 'vidros', null, 10
where not exists (select 1 from public.portals where key = 'vidros_abraseuatendimento');

insert into public.portals (key, name, login_url, category, insurer_key, sort_order)
select 'vidros_agendeseuservico', 'Portal de Vidros — Agende Seu Serviço (Bradesco)', 'https://www.agendeseuservico.com/', 'vidros', 'bradesco', 20
where not exists (select 1 from public.portals where key = 'vidros_agendeseuservico');

insert into public.portals (key, name, login_url, category, insurer_key, sort_order)
select 'allianz_corretor', 'AllianzNet — Corretor', 'https://www.allianznet.com.br/ngx-epac/public/home', 'corretor', 'allianz', 30
where not exists (select 1 from public.portals where key = 'allianz_corretor');

insert into public.portals (key, name, login_url, category, insurer_key, sort_order)
select 'alfa_corretor', 'Alfa — Área do Corretor', 'https://areacorretor.alfaseguradora.com.br/', 'corretor', 'alfa', 40
where not exists (select 1 from public.portals where key = 'alfa_corretor');

insert into public.portals (key, name, login_url, category, insurer_key, sort_order)
select 'azul_corretor', 'Azul Seguros — Área Restrita', 'https://www.azulseguros.com.br/area-restrita/', 'corretor', 'azul', 50
where not exists (select 1 from public.portals where key = 'azul_corretor');

insert into public.portals (key, name, login_url, category, insurer_key, sort_order)
select 'bradesco_corretor', 'Bradesco — Portal de Negócios', 'https://wwws.bradescoseguros.com.br/portaldenegocios/index.asp', 'corretor', 'bradesco', 60
where not exists (select 1 from public.portals where key = 'bradesco_corretor');

-- >>>>>>>>>>>>>>>>>> 20260706_05_spec020_portals_seed_insurers.sql <<<<<<<<<<<<<<<<<<

-- SPEC-020 — Seed dos portais de CORRETOR das demais seguradoras (registro global).
-- EXPAND-ONLY, idempotente por key. URLs públicas (portal_base_do_corretor do
-- registro de portais). Login/senha continuam por corretora em portal_accounts.
--
-- APPLY:   SQL Editor do Supabase (idempotente).
-- VERIFY:  select count(*) from public.portals;  -- deve incluir as novas
-- ROLLBACK: delete from public.portals where key in (
--   'hdi_corretor','mapfre_corretor','porto_corretor','sura_corretor',
--   'segurosunimed_corretor','sompo_corretor','suhai_corretor','sulamerica_corretor',
--   'tokiomarine_corretor','yelum_corretor','zurich_corretor');

insert into public.portals (key, name, login_url, category, insurer_key, sort_order)
select v.key, v.name, v.login_url, 'corretor', v.insurer_key, v.sort_order
from (values
  ('hdi_corretor',          'HDI Digital — Corretor',        'https://www.hdi.com.br/hdidigital/',                          'hdi',           70),
  ('mapfre_corretor',       'MAPFRE — Negócios',             'https://negocios.mapfre.com.br/',                             'mapfre',        80),
  ('porto_corretor',        'Porto — Corretor Online',       'https://corretor.portoseguro.com.br/corretoronline/',         'porto',         90),
  ('sura_corretor',         'SURA — Portal do Corretor',     'https://www.segurossura.com.br/acesso-portal/corretor.html',  'sura',          100),
  ('segurosunimed_corretor','Seguros Unimed — Corretor',     'https://www.segurosunimed.com.br/login-corretor',             'seguros_unimed',110),
  ('sompo_corretor',        'Sompo — Portal do Corretor',    'https://corretor.sompo.com.br/PortalCorretor_Th/Login.aspx',  'sompo',         120),
  ('suhai_corretor',        'Suhai — Área do Corretor',      'https://suhaiseguradora.com/area-do-corretor/',               'suhai',         130),
  ('sulamerica_corretor',   'SulAmérica — Corretor',         'https://corretor.sulamericaseguros.com.br/',                  'sulamerica',    140),
  ('tokiomarine_corretor',  'Tokio Marine — Portal Parceiros','https://portalparceiros.tokiomarine.com.br/',                'tokio_marine',  150),
  ('yelum_corretor',        'Yelum — Espaço Corretor',       'https://novomeuespacocorretor.yelumseguros.com.br/home',      'yelum',         160),
  ('zurich_corretor',       'Zurich — Espaço Parceiros',     'https://espacoparceiros.zurich.com.br/',                      'zurich',        170)
) as v(key, name, login_url, insurer_key, sort_order)
where not exists (select 1 from public.portals p where p.key = v.key);

-- >>>>>>>>>>>>>>>>>> 20260706_06_spec020_portal_capability.sql <<<<<<<<<<<<<<<<<<

-- SPEC-020 P3 — Capability do portal_action + perfil de acionamento por corretora.
-- EXPAND-ONLY. tenant.portal.execute libera a tool portal_action (acessar portais).
-- acionamento_profile = identidade da CORRETORA usada como "solicitante/Corretor"
-- no portal (multi-tenant: cada corretora a sua). NUNCA o e-mail do segurado.
--
-- APPLY:   SQL Editor do Supabase (idempotente).
-- VERIFY:  select capability_key from public.capabilities where capability_key='tenant.portal.execute';
--          select column_name from information_schema.columns where table_name='companies' and column_name='acionamento_profile';
-- ROLLBACK: delete from public.capability_bindings where capability_key='tenant.portal.execute';
--           delete from public.capabilities where capability_key='tenant.portal.execute';
--           alter table public.companies drop column if exists acionamento_profile;

insert into public.capabilities
  (capability_key, name, category, owner, risk, requires_connection, requires_approval, provider, is_active)
values
  ('tenant.portal.execute', 'Acessar portais (vidros/corretor)', 'insurance_ops', 'tenant', 'high', false, false, null, true)
on conflict (capability_key) do nothing;

-- Fable (SPEC-020 P3) previu core/auxiliary; incluimos attendance porque o caso de
-- ouro (assistencia de vidros pelo atendente) e um fluxo de ATENDIMENTO. Seguranca
-- preservada: gate PORTAL_REAL_ENABLED off + journey para no 80% + needs_human.
insert into public.capability_bindings (agent_role, capability_key, enabled)
values
  ('core', 'tenant.portal.execute', true),
  ('auxiliary', 'tenant.portal.execute', true),
  ('attendance', 'tenant.portal.execute', true)
on conflict do nothing;

-- Perfil de acionamento por corretora (solicitante). Preenchido no dashboard.
alter table public.companies add column if not exists acionamento_profile jsonb not null default '{}'::jsonb;
comment on column public.companies.acionamento_profile is
  'SPEC-020: identidade da corretora usada como solicitante/Corretor nos portais {nome,email,telefone,cpf_cnpj,susep}.';
