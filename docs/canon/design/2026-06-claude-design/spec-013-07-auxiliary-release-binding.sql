-- SPEC-013 B1.1 — Runbook 07: vínculo do Auxiliary Template à release imutável.
-- Colunas OPCIONAIS (não quebram specific_executor). NÃO aplicado por mim. Idempotente.
-- ============================================================================
-- APPLY
-- ============================================================================
begin;

alter table public.auxiliary_templates add column if not exists source_release_id uuid
  references public.agent_blueprint_releases(id) on delete set null;
alter table public.auxiliary_templates add column if not exists source_blueprint_key text;
alter table public.auxiliary_templates add column if not exists source_semantic_version text;
alter table public.auxiliary_templates add column if not exists source_company_id uuid
  references public.companies(id) on delete set null;
alter table public.auxiliary_templates add column if not exists runtime_policy jsonb not null default '{}'::jsonb;

create index if not exists idx_aux_templates_source_release on public.auxiliary_templates (source_release_id);

commit;

-- ============================================================================
-- VERIFY
-- ============================================================================
-- select column_name from information_schema.columns
--  where table_schema='public' and table_name='auxiliary_templates'
--    and column_name in ('source_release_id','source_blueprint_key','source_semantic_version','source_company_id','runtime_policy')
--  order by column_name;

-- ============================================================================
-- ROLLBACK
-- ============================================================================
-- begin;
--   drop index if exists public.idx_aux_templates_source_release;
--   alter table public.auxiliary_templates
--     drop column if exists source_release_id,
--     drop column if exists source_blueprint_key,
--     drop column if exists source_semantic_version,
--     drop column if exists source_company_id,
--     drop column if exists runtime_policy;
-- commit;
