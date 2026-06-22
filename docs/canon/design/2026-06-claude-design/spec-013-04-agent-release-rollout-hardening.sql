-- SPEC-013 Fase B (hardening) — Runbook 04: rollout/rollback ATÔMICO + snapshot + 1-ativo
-- Aplicar APÓS o runbook 03. NÃO aplicado por mim. Compatível com a tabela existente.
-- Acrescenta: coluna de snapshot pré-rollout, índice único parcial (1 rollout active por
-- company+blueprint) e 2 RPCs transacionais service-role-only (apply/rollback atômicos).
-- ============================================================================
-- APPLY
-- ============================================================================
begin;

-- 1) snapshot do estado do agente ANTES do rollout (permite rollback seguro até no 1º)
alter table public.agent_release_rollouts
  add column if not exists pre_rollout_snapshot jsonb;

-- 2) invariante: no máximo UM rollout 'active' por (company_id, blueprint_key)
create unique index if not exists uniq_arr_active
  on public.agent_release_rollouts (company_id, blueprint_key)
  where status = 'active';

-- 3) RPC atômica de APLICAÇÃO de rollout (valida + pausa anterior + atualiza agente +
--    insere registro com snapshot + auditoria — tudo numa transação).
create or replace function public.apply_release_rollout(
  p_release_id uuid,
  p_company_id uuid,
  p_agent_id uuid,
  p_new_agent jsonb,
  p_snapshot jsonb,
  p_blueprint_key text,
  p_applied_by uuid
) returns uuid
language plpgsql
as $$
declare
  v_prev_rollout uuid;
  v_prev_release uuid;
  v_new uuid;
begin
  if not exists (select 1 from public.agent_blueprint_releases where id = p_release_id and status = 'published') then
    raise exception 'release_nao_publicada';
  end if;
  if coalesce((select company_kind from public.companies where id = p_company_id), 'client') <> 'client' then
    raise exception 'empresa_nao_cliente';
  end if;
  if not exists (select 1 from public.agents where id = p_agent_id and company_id = p_company_id) then
    raise exception 'agente_incompativel';
  end if;

  select id, release_id into v_prev_rollout, v_prev_release
    from public.agent_release_rollouts
    where company_id = p_company_id and blueprint_key = p_blueprint_key and status = 'active'
    order by applied_at desc limit 1;

  if v_prev_rollout is not null then
    update public.agent_release_rollouts set status = 'paused' where id = v_prev_rollout;
  end if;

  update public.agents set
    name                = coalesce(p_new_agent->>'name', name),
    avatar_url          = coalesce(p_new_agent->>'avatar_url', avatar_url),
    llm_temperature     = coalesce((p_new_agent->>'llm_temperature')::numeric, llm_temperature),
    agent_system_prompt = coalesce(p_new_agent->>'agent_system_prompt', agent_system_prompt),
    context_package     = coalesce(p_new_agent->'context_package', context_package),
    blueprint_version   = coalesce(p_new_agent->>'blueprint_version', blueprint_version),
    updated_at          = now()
  where id = p_agent_id and company_id = p_company_id;

  insert into public.agent_release_rollouts
    (release_id, blueprint_key, company_id, tenant_agent_id, status, previous_release_id, pre_rollout_snapshot, applied_by, applied_at)
  values
    (p_release_id, p_blueprint_key, p_company_id, p_agent_id, 'active', v_prev_release, p_snapshot, p_applied_by, now())
  returning id into v_new;

  return v_new;
end
$$;

-- 4) RPC atômica de ROLLBACK: restaura o snapshot pré-rollout do rollout ativo.
create or replace function public.rollback_release_rollout(
  p_company_id uuid,
  p_blueprint_key text,
  p_by uuid
) returns uuid
language plpgsql
as $$
declare
  v_id uuid;
  v_agent uuid;
  v_snap jsonb;
begin
  select id, tenant_agent_id, pre_rollout_snapshot into v_id, v_agent, v_snap
    from public.agent_release_rollouts
    where company_id = p_company_id and blueprint_key = p_blueprint_key and status = 'active'
    order by applied_at desc limit 1;

  if v_id is null then raise exception 'rollout_ativo_inexistente'; end if;
  if v_snap is null then raise exception 'snapshot_indisponivel'; end if;

  update public.agents set
    name                = coalesce(v_snap->>'name', name),
    avatar_url          = v_snap->>'avatar_url',
    llm_temperature     = (v_snap->>'llm_temperature')::numeric,
    agent_system_prompt = v_snap->>'agent_system_prompt',
    context_package     = coalesce(v_snap->'context_package', context_package),
    blueprint_version   = v_snap->>'blueprint_version',
    updated_at          = now()
  where id = v_agent and company_id = p_company_id;

  update public.agent_release_rollouts
    set status = 'rolled_back', rollback_at = now(), rollback_by = p_by
  where id = v_id;

  return v_id;
end
$$;

-- service-role-only (nunca anon/authenticated)
revoke all on function public.apply_release_rollout(uuid, uuid, uuid, jsonb, jsonb, text, uuid) from public, anon, authenticated;
revoke all on function public.rollback_release_rollout(uuid, text, uuid) from public, anon, authenticated;
grant execute on function public.apply_release_rollout(uuid, uuid, uuid, jsonb, jsonb, text, uuid) to service_role;
grant execute on function public.rollback_release_rollout(uuid, text, uuid) to service_role;

commit;

-- ============================================================================
-- VERIFY
-- ============================================================================
-- select column_name from information_schema.columns where table_schema='public' and table_name='agent_release_rollouts' and column_name='pre_rollout_snapshot';
-- select indexname from pg_indexes where schemaname='public' and tablename='agent_release_rollouts' and indexname='uniq_arr_active';
-- select proname from pg_proc where proname in ('apply_release_rollout','rollback_release_rollout');
-- -- 1 rollout ativo por company+blueprint é garantido pelo índice único parcial.

-- ============================================================================
-- ROLLBACK
-- ============================================================================
-- begin;
--   drop function if exists public.apply_release_rollout(uuid, uuid, uuid, jsonb, jsonb, text, uuid);
--   drop function if exists public.rollback_release_rollout(uuid, text, uuid);
--   drop index if exists public.uniq_arr_active;
--   alter table public.agent_release_rollouts drop column if exists pre_rollout_snapshot;
-- commit;
