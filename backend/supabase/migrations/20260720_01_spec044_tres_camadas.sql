-- SPEC-044 — Tres Camadas: Global / Corretora / Usuario (fundacao).
-- Expand-only. Defaults preservam o comportamento atual (tudo existente
-- continua sendo "da corretora"; nada muda sem acao explicita).
--
-- APPLY ------------------------------------------------------------------

-- B. Conhecimento pessoal: dono opcional do documento (NULL = da corretora)
alter table public.documents add column if not exists owner_user_id uuid;
create index if not exists ix_documents_owner
  on public.documents (company_id, owner_user_id);

-- C. Conectores pessoais: owner_user_id JA EXISTE na tabela; o que muda e o
-- indice singleton — passa a permitir 1 conexao DA CORRETORA + 1 PESSOAL por
-- usuario para o mesmo template (padrao ChatGPT Enterprise/Slack).
drop index if exists public.uniq_active_connection_per_template;
create unique index if not exists uniq_company_connection_per_template
  on public.tenant_connections (company_id, connector_template_id)
  where (status <> 'archived' and owner_user_id is null);
create unique index if not exists uniq_personal_connection_per_template
  on public.tenant_connections (company_id, connector_template_id, owner_user_id)
  where (status <> 'archived' and owner_user_id is not null);

-- D. Rotinas e auxiliares: visibilidade (company = todos da corretora;
-- personal = so o dono created_by/instalador ve e gerencia)
alter table public.routines add column if not exists visibility text not null default 'company';
create index if not exists ix_routines_visibility
  on public.routines (company_id, visibility, created_by);
alter table public.tenant_auxiliaries add column if not exists visibility text not null default 'company';
alter table public.tenant_auxiliaries add column if not exists owner_user_id uuid;

-- VERIFY -----------------------------------------------------------------
-- select column_name from information_schema.columns
--   where table_name='documents' and column_name='owner_user_id';
-- select indexname from pg_indexes where tablename='tenant_connections'
--   and indexname like 'uniq_%';  -- 2 indices novos, singleton antigo fora
-- select column_name from information_schema.columns
--   where table_name='routines' and column_name='visibility';
--
-- ROLLBACK ---------------------------------------------------------------
-- alter table public.documents drop column owner_user_id;
-- drop index uniq_company_connection_per_template;
-- drop index uniq_personal_connection_per_template;
-- create unique index uniq_active_connection_per_template
--   on public.tenant_connections (company_id, connector_template_id)
--   where (status <> 'archived');
-- alter table public.routines drop column visibility;
-- alter table public.tenant_auxiliaries drop column visibility;
-- alter table public.tenant_auxiliaries drop column owner_user_id;
