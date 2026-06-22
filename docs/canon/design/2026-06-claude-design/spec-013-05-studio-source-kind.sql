-- SPEC-013 Fase B — Runbook 05: taxonomia de Source Agent (studio_source_kind)
-- Aplicar APÓS os runbooks 01–04. NÃO aplicado por mim. Não duplica agent_role:
-- classifica a finalidade do agente de AUTORIA no Studio. Idempotente.
-- ============================================================================
-- APPLY
-- ============================================================================
begin;

alter table public.agents add column if not exists studio_source_kind text;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'agents_studio_source_kind_check') then
    alter table public.agents
      add constraint agents_studio_source_kind_check
      check (
        studio_source_kind is null
        or studio_source_kind in ('global_core','global_attendance','global_auxiliary','source_subagent')
      );
  end if;
end $$;

-- classifica os Source Agents existentes do Studio (Core/Even) de forma idempotente
update public.agents a
  set studio_source_kind = case
        when a.agent_role = 'core' then 'global_core'
        when a.agent_role = 'attendance' then 'global_attendance'
        else a.studio_source_kind
      end
  from public.companies c
  where c.id = a.company_id
    and c.company_kind = 'platform_blueprint_studio'
    and a.studio_source_kind is null
    and a.agent_role in ('core','attendance');

create index if not exists idx_agents_studio_source_kind
  on public.agents (studio_source_kind)
  where studio_source_kind is not null;

commit;

-- ============================================================================
-- VERIFY
-- ============================================================================
-- select a.name, a.agent_role, a.studio_source_kind
--   from public.agents a join public.companies c on c.id=a.company_id
--   where c.company_kind='platform_blueprint_studio' order by a.agent_role;
-- esperado: AutoBrokers→global_core, Even→global_attendance

-- ============================================================================
-- ROLLBACK
-- ============================================================================
-- begin;
--   drop index if exists public.idx_agents_studio_source_kind;
--   alter table public.agents drop constraint if exists agents_studio_source_kind_check;
--   alter table public.agents drop column if exists studio_source_kind;
-- commit;
