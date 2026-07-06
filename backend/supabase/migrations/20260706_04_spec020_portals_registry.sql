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
