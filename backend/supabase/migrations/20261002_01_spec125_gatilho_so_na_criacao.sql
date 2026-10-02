-- =============================================================
-- MIGRATION: 20261002_01_spec125_gatilho_so_na_criacao
-- SPEC:      SPEC-125 — conserto único (parte Y3 · juiz P3, red team P7)
-- AUTOR:     builder do conserto Y (Opus 5.5)      DATA: 2026-10-02
-- OBJETIVO:  o gatilho `destravador_nasce_ligado` (20261001_06, D9) só cria as linhas
--            `cerebro_modos` quando a corretora GANHA um agente de atendimento:
--              · INSERT de agente de atendimento, ou
--              · UPDATE em que `agent_role` MUDA para atendimento
--                (`old.agent_role is distinct from new.agent_role`).
--            Um UPDATE qualquer que cite `agent_role`/`company_id` sem mudar o papel
--            (re-save do painel, provisionamento idempotente) NÃO recria as linhas que a
--            corretora APAGOU — "sem linha = off" é o desfazer declarado no D9.
--
-- 📊 ANTES (02/10/2026, SELECT read-only pelo MCP):
--    · gatilho: AFTER INSERT OR UPDATE OF agent_role, company_id ON agents — dispara em todo
--      UPDATE que liste a coluna, mesmo sem mudar o valor (o laudo do juiz, P3, reproduziu).
--    · `agents_agent_role_check`: core · attendance · auxiliary · subagent · corridor ·
--      connector · system. ⚠️ `insured_external` NÃO é valor de `agent_role` no banco — é de
--      `agent_audience`. O código Python o trata como papel do segurado
--      (`graph._PAPEIS_DO_SEGURADO`, `nodes._PAPEIS_DE_ATENDIMENTO`), então a função o aceita
--      também: hoje é inerte (o CHECK o recusa), e no dia em que o CHECK o aceitar o agente
--      do segurado nasce com o destravador como o de atendimento — uma lista, a do código.
--    · cerebro_modos: 40 linhas, todas `on`.
--
-- APPLY:  `create or replace function public.tg_destravador_nasce_ligado()` com a guarda do
--         UPDATE. O gatilho NÃO muda (a função decide; `create or replace` basta — nenhum drop).
--
-- VERIFY (read-only; o bloco DO desfaz tudo o que testa):
--   select tgname from pg_trigger where tgrelid = 'public.agents'::regclass and not tgisinternal order by 1;
--   -- esperado: atendimento_nasce_desligado · destravador_nasce_ligado
--   do $$
--   declare v_nova uuid := gen_random_uuid(); v_ag uuid; v_seg text;
--           n_ins int; n_depois_resave int; n_depois_mudanca int; n_esperado int;
--   begin
--     select count(distinct insurer_key) into n_esperado from public.cerebro_modos where modo = 'on';
--     begin
--       insert into public.companies (id, company_name) values (v_nova, 'verify-125-y3');
--       insert into public.agents (company_id, name, slug, agent_role)
--         values (v_nova, 'verify-att', 'verify-att-y3', 'attendance') returning id into v_ag;
--       select count(*) into n_ins from public.cerebro_modos where company_id = v_nova;
--       -- a corretora APAGA uma linha (desliga) e o painel re-salva o agente sem mudar o papel
--       select insurer_key into v_seg from public.cerebro_modos where company_id = v_nova limit 1;
--       delete from public.cerebro_modos where company_id = v_nova and insurer_key = v_seg;
--       update public.agents set agent_role = 'attendance', company_id = v_nova where id = v_ag;
--       select count(*) into n_depois_resave from public.cerebro_modos where company_id = v_nova;
--       -- CONTROLE: o papel MUDA (core → attendance) → as linhas nascem de novo
--       update public.agents set agent_role = 'core' where id = v_ag;
--       update public.agents set agent_role = 'attendance' where id = v_ag;
--       select count(*) into n_depois_mudanca from public.cerebro_modos where company_id = v_nova;
--       raise exception using errcode = 'P0001', message = 'desfaz-verify';
--     exception when sqlstate 'P0001' then null; end;
--     if n_ins <> n_esperado or n_depois_resave <> n_esperado - 1 or n_depois_mudanca <> n_esperado then
--       raise exception 'VERIFY 20261002_01 FALHOU: insert=% resave=% mudanca=% esperado=%',
--         n_ins, n_depois_resave, n_depois_mudanca, n_esperado;
--     end if;
--     if exists (select 1 from public.companies where id = v_nova) then
--       raise exception 'VERIFY 20261002_01: a corretora de teste ficou gravada';
--     end if;
--     raise notice 'VERIFY 20261002_01 OK: insert=% · re-save sem mudar papel=% (apagada continua apagada) · papel mudou=%',
--       n_ins, n_depois_resave, n_depois_mudanca;
--   end $$;
--
-- ROLLBACK:  (escrito ANTES de aplicar) — volta a função da 20261001_06, byte a byte:
--   create or replace function public.tg_destravador_nasce_ligado()
--   returns trigger language plpgsql security definer set search_path = pg_catalog, public as $$
--   begin
--     if new.company_id is null or lower(coalesce(new.agent_role, '')) <> 'attendance' then
--       return new;
--     end if;
--     insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, limiar, motivo, ligado_por)
--     select new.company_id, s.insurer_key, 'todos', 'on', 70,
--            'SPEC-125 D9: corretora com agente de atendimento nasce com o destravador ligado '
--            || '(DEDUZIR autônomo desligado em código até calibrar)',
--            'gatilho destravador_nasce_ligado (migration 20261001_06)'
--       from (select distinct insurer_key from public.cerebro_modos where modo = 'on') s
--     on conflict (company_id, insurer_key, ramo) do nothing;
--     return new;
--   end $$;
--   delete from supabase_migrations.schema_migrations where name = 'spec125_gatilho_so_na_criacao';
--
-- EXPAND-FIRST: sim — só o corpo de uma função muda; nenhuma tabela, coluna, linha ou gatilho.
-- DESTRUTIVA:   não. IDEMPOTENTE: sim (`create or replace`).
-- =============================================================

create or replace function public.tg_destravador_nasce_ligado()
returns trigger
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
begin
  if new.company_id is null
     or lower(coalesce(new.agent_role, '')) not in ('attendance', 'insured_external') then
    return new;
  end if;
  -- 🔴 SPEC-125 Y3: no UPDATE, só quando o PAPEL muda. Um re-save que não muda o papel não
  --    recria a linha que a corretora apagou (sem linha = off é o desfazer do D9).
  if tg_op = 'UPDATE' and old.agent_role is not distinct from new.agent_role then
    return new;
  end if;
  -- as seguradoras em que a plataforma tem o destravador `on` (a própria cerebro_modos é a
  -- verdade); nunca sobrescreve uma linha da corretora (off, sombra ou limiar calibrado)
  insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, limiar, motivo, ligado_por)
  select new.company_id, s.insurer_key, 'todos', 'on', 70,
         'SPEC-125 D9: corretora com agente de atendimento nasce com o destravador ligado '
         || '(DEDUZIR autônomo desligado em código até calibrar)',
         'gatilho destravador_nasce_ligado (migration 20261001_06 · 20261002_01)'
    from (select distinct insurer_key from public.cerebro_modos where modo = 'on') s
  on conflict (company_id, insurer_key, ramo) do nothing;
  return new;
end $$;

comment on function public.tg_destravador_nasce_ligado() is
  'SPEC-125 D9 — quando uma corretora ganha agente de atendimento (INSERT, ou UPDATE em que agent_role MUDA para attendance/insured_external), nasce uma linha cerebro_modos on/70/todos por seguradora em que a plataforma já tem o destravador on. Nunca sobrescreve e nunca recria linha apagada num re-save (20261002_01). SECURITY DEFINER porque cerebro_modos tem RLS sem policy.';
