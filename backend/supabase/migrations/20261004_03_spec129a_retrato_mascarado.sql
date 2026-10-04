-- =============================================================
-- MIGRATION: 20261004_03_spec129a_retrato_mascarado
-- SPEC:      SPEC-129-A — F4 · presos e rastro (§8, D-129A-6) · fecha a P-223 (e a P-126-09)
-- AUTOR:     builder F4 (Opus 5.5)            DATA: 2026-10-04
-- OBJETIVO:  nenhum CPF/telefone em claro em `work_steps`. Regra única, no banco:
--            um passo `dispatch_phase` guarda o retrato CRU só se for `monitoring` de run NÃO-terminal
--            (o único que `dispatch_router._ultimo_retrato` restaura, ≤ 24 h — B6). Todo o resto vira o
--            gêmeo mascarado `output_redacted` (ou um marcador, se o gêmeo faltar).
--
-- 📊 ANTES (04/10/2026, `execute_sql` só leitura):
--    · work_steps com '"(titular_cpf|telefone_contato|client_phone)"\s*:\s*"[0-9]' em output_summary: 17,
--      todas step_type='dispatch_phase', todas de runtime_kind='acionamento'; fora de dispatch_phase: 0.
--    · as 17 têm `output_redacted` (gêmeo) e NENHUM gêmeo casa o padrão (0/17).
--    · por passo/run: ura 6 · human_phase 5 · needs_human 4 · test_aborted 1 · monitoring 1 (run completed);
--      run vivo (waiting_input, desde 10/09): ura, human_phase, needs_human — nenhum `monitoring`.
--    · md5(output_summary::text) por linha das 17: no relatório da F4 (nunca o conteúdo).
--    · runs smith usam step_type analysis · artifact · routine · system — nunca dispatch_phase.
--
-- APPLY:  4 funções (create or replace) · 2 gatilhos (drop if exists + create) · privilégios das funções
--         (só service_role/postgres; anon e authenticated NÃO executam) · backfill pelo gatilho · varredura
--         das `monitoring` vencidas (> 24 h). Idempotente: a 2ª vez não muda linha nenhuma.
--         ⚠️ DESTRÓI o cru das 17 por DECISÃO JÁ DADA (ficha §4, D-129A-6).
--
-- VERIFY (read-only · esperado no dia: 0 · 17 · 2 · 1):
--   select (select count(*) from public.work_steps
--             where output_summary::text ~ '"(titular_cpf|telefone_contato|client_phone)"\s*:\s*"[0-9]') cru,
--          (select count(*) from public.work_steps where step_type='dispatch_phase' and output_summary = output_redacted) mascarados,
--          (select count(*) from pg_trigger where tgname in ('trg_work_steps_retrato','trg_acionamento_fechado_mascara')) gatilhos,
--          (select count(*) from pg_proc where proname='work_steps_mascarar_vencidos') funcao;
--
-- VERIFY comportamental: `backend/tests/test_spec129a_o_rastro_fecha_sem_cpf.py` (transação desfeita):
--   passo `ura` cru de run vivo → mascarado · `monitoring` de run vivo → cru · UPDATE de run JÁ fechado com
--   checkpoint novo → mascarado · passo de run `smith` → intocado · CONTROLE: sem o gatilho de fechamento,
--   o checkpoint do run fechado fica cru.
--
-- ROLLBACK (só a estrutura; o DADO mascarado NÃO volta, por desenho — desastre: PITR):
--   drop trigger if exists trg_acionamento_fechado_mascara on public.work_runs;
--   drop trigger if exists trg_work_steps_retrato on public.work_steps;
--   drop function if exists public.work_steps_mascarar_vencidos(int);
--   drop function if exists public.tg_acionamento_fechado_mascara();
--   drop function if exists public.tg_work_steps_retrato();
--   drop function if exists public.retrato_pode_ficar_cru(uuid, uuid, text);
--   -- ⚠️ com o código da F1 no ar, `_laco_manutencao` chama a rpc `work_steps_mascarar_vencidos`: sem ela,
--   --    a rpc falha e o laço só registra o erro.
--
-- EXPAND-FIRST: sim para a estrutura (só cria)
-- DESTRUTIVA:   SIM para o DADO das 17 linhas (PII) — decisão já dada (ficha §4 · D-129A-6 · P-223)
-- ORDEM:        _01 → _02 → _03
-- =============================================================

-- 1) a regra, num lugar só
create or replace function public.retrato_pode_ficar_cru(p_run uuid, p_company uuid, p_step_key text)
returns boolean
language sql stable security definer set search_path = public as $$
  select p_step_key = 'monitoring'
     and exists (select 1 from public.work_runs r
                  where r.id = p_run and r.company_id = p_company
                    and r.status::text not in ('completed', 'failed', 'cancelled', 'expired'))
$$;

-- 2) o gatilho de ESCRITA: todo INSERT/UPDATE de passo `dispatch_phase`
create or replace function public.tg_work_steps_retrato()
returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.step_type = 'dispatch_phase' then   -- IF aninhado: o passo do smith nem chama a regra
    if not public.retrato_pode_ficar_cru(new.work_run_id, new.company_id, new.step_key) then
      new.output_summary := coalesce(new.output_redacted, '{"_retrato":"mascarado (SPEC-129-A)"}'::jsonb);
    end if;
  end if;
  return new;
end $$;

drop trigger if exists trg_work_steps_retrato on public.work_steps;
create trigger trg_work_steps_retrato
  before insert or update on public.work_steps
  for each row execute function public.tg_work_steps_retrato();

-- 3) o gatilho de FECHAMENTO: todo UPDATE de acionamento terminal re-mascara os passos dele.
--    Falhar aqui NUNCA bloqueia o fechamento do run (warning e segue).
create or replace function public.tg_acionamento_fechado_mascara()
returns trigger
language plpgsql security definer set search_path = public as $$
begin
  begin
    update public.work_steps s
       set output_summary = coalesce(s.output_redacted, '{"_retrato":"mascarado (SPEC-129-A)"}'::jsonb)
     where s.work_run_id = new.id and s.company_id = new.company_id and s.step_type = 'dispatch_phase'
       and s.output_summary is distinct from coalesce(s.output_redacted, '{"_retrato":"mascarado (SPEC-129-A)"}'::jsonb);
  exception when others then
    raise warning 'tg_acionamento_fechado_mascara %: %', new.id, sqlstate;
  end;
  return new;
end $$;

drop trigger if exists trg_acionamento_fechado_mascara on public.work_runs;
create trigger trg_acionamento_fechado_mascara
  after update on public.work_runs
  for each row
  when (new.runtime_kind = 'acionamento' and new.status::text in ('completed', 'failed', 'cancelled', 'expired'))
  execute function public.tg_acionamento_fechado_mascara();

-- 4) a VARREDURA: `monitoring` vencido (> p_horas) deixa de ser restaurável → mascarado.
--    Chamada pelo `_laco_manutencao` do smith-worker (F1) via rpc, com a service role.
create or replace function public.work_steps_mascarar_vencidos(p_horas int default 24)
returns int
language sql security definer set search_path = public as $$
  with m as (
    update public.work_steps
       set output_summary = coalesce(output_redacted, '{"_retrato":"mascarado (SPEC-129-A)"}'::jsonb)
     where step_type = 'dispatch_phase' and step_key = 'monitoring'
       and coalesce(finished_at, updated_at) < now() - make_interval(hours => p_horas)
       and output_summary is distinct from coalesce(output_redacted, '{"_retrato":"mascarado (SPEC-129-A)"}'::jsonb)
    returning 1)
  select count(*)::int from m
$$;

-- 5) quem pode chamar: SECURITY DEFINER exposto ao PostgREST seria uma rpc pública (anon mascarando
--    passos de qualquer corretora; anon sondando se um run existe). Mesmo padrão de `work_run_create`.
revoke all on function public.retrato_pode_ficar_cru(uuid, uuid, text) from public, anon, authenticated;
revoke all on function public.tg_work_steps_retrato()                  from public, anon, authenticated;
revoke all on function public.tg_acionamento_fechado_mascara()         from public, anon, authenticated;
revoke all on function public.work_steps_mascarar_vencidos(int)        from public, anon, authenticated;
grant execute on function public.work_steps_mascarar_vencidos(int) to service_role;
grant execute on function public.retrato_pode_ficar_cru(uuid, uuid, text) to service_role;

-- 6) o DADO: backfill pelo próprio gatilho (uma regra só) + a varredura das `monitoring` vencidas
update public.work_steps set output_summary = output_summary where step_type = 'dispatch_phase';
select public.work_steps_mascarar_vencidos(24);
