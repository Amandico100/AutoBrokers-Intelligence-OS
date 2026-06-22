-- SPEC-013 Fase B — Runbook 06: rollout correto e final (compatibilidade no banco +
-- rollback em cadeia + serialização + guarda de segredo). Aplicar APÓS o runbook 04.
-- CREATE OR REPLACE das 2 RPCs (idempotente). NÃO aplicado por mim.
-- ============================================================================
-- APPLY
-- ============================================================================
begin;

-- APLICAÇÃO: agora valida no PRÓPRIO banco blueprint_key/role/audience, serializa
-- com FOR UPDATE e recusa snapshot com chave de segredo.
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
  v_rel_bpk text;
  v_rel_role text;
  v_rel_aud text;
  v_ag_role text;
  v_ag_aud text;
begin
  -- release publicada + compatibilidade de blueprint/role/audience (defesa no banco)
  select blueprint_key, artifact->>'role', artifact->>'audience'
    into v_rel_bpk, v_rel_role, v_rel_aud
    from public.agent_blueprint_releases
    where id = p_release_id and status = 'published';
  if v_rel_bpk is null then raise exception 'release_nao_publicada'; end if;
  if v_rel_bpk <> p_blueprint_key then raise exception 'blueprint_incompativel'; end if;

  if coalesce((select company_kind from public.companies where id = p_company_id), 'client') <> 'client' then
    raise exception 'empresa_nao_cliente';
  end if;

  -- trava a instância tenant (serialização) e valida role/audience
  select agent_role, agent_audience into v_ag_role, v_ag_aud
    from public.agents where id = p_agent_id and company_id = p_company_id for update;
  if v_ag_role is null then raise exception 'agente_incompativel'; end if;
  if v_ag_role is distinct from v_rel_role then raise exception 'role_incompativel'; end if;
  if v_ag_aud is distinct from v_rel_aud then raise exception 'audience_incompativel'; end if;

  -- snapshot nunca pode conter chave de segredo
  if p_snapshot ?| array['token','secret','api_key','authorization','cookie','password','refresh_token','sessionref','storagestate','connecturl'] then
    raise exception 'snapshot_com_segredo';
  end if;

  -- trava e pausa o rollout ativo anterior (se houver)
  select id, release_id into v_prev_rollout, v_prev_release
    from public.agent_release_rollouts
    where company_id = p_company_id and blueprint_key = p_blueprint_key and status = 'active'
    order by applied_at desc limit 1
    for update;
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

-- ROLLBACK: restaura o snapshot do rollout ativo (estado anterior) E reativa o rollout
-- anterior (paused) quando existir — mantendo histórico coerente. No 1º rollout não há
-- anterior: restaura o estado original e fica sem rollout ativo.
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
  v_prev uuid;
begin
  select id, tenant_agent_id, pre_rollout_snapshot into v_id, v_agent, v_snap
    from public.agent_release_rollouts
    where company_id = p_company_id and blueprint_key = p_blueprint_key and status = 'active'
    order by applied_at desc limit 1
    for update;
  if v_id is null then raise exception 'rollout_ativo_inexistente'; end if;
  if v_snap is null then raise exception 'snapshot_indisponivel'; end if;

  -- restaura o agente ao estado pré-rollout (= estado da versão anterior, ou original no 1º)
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

  -- reativa o rollout anterior (mais recente pausado), se houver
  select id into v_prev
    from public.agent_release_rollouts
    where company_id = p_company_id and blueprint_key = p_blueprint_key and status = 'paused'
    order by applied_at desc limit 1
    for update;
  if v_prev is not null then
    update public.agent_release_rollouts set status = 'active' where id = v_prev;
  end if;

  return v_id;
end
$$;

commit;

-- ============================================================================
-- VERIFY
-- ============================================================================
-- select proname, prosrc ilike '%role_incompativel%' as has_compat_check
--   from pg_proc where proname='apply_release_rollout';
-- select proname, prosrc ilike '%reativa o rollout anterior%' as has_reactivation
--   from pg_proc where proname='rollback_release_rollout';

-- ============================================================================
-- ROLLBACK (reverter para o comportamento do runbook 04: basta reaplicar o APPLY
-- do runbook 04, que faz CREATE OR REPLACE das versões anteriores das 2 funções).
-- ============================================================================
