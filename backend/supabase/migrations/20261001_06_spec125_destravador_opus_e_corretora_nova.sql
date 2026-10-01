-- =============================================================
-- MIGRATION: 20261001_06_spec125_destravador_opus_e_corretora_nova
-- SPEC:      SPEC-125 — S9 · Opus 5.5 na 2ª opinião e na reserva do destravador (D8) +
--            corretora NOVA nasce com o destravador ligado (D9)
-- AUTOR:     builder S9 (Opus 5.5 xhigh)      DATA: 2026-10-01
-- OBJETIVO:  (D8) `destravador_segunda` passa a ter o Claude Opus 5.5 como primário e o
--            `destravador` passa a ter o Opus 5.5 como reserva — pelo caminho governado
--            (`llm_papeis`, com histórico), nunca env. (D9) quando uma corretora ganha um
--            agente de ATENDIMENTO, as linhas `cerebro_modos` (`on`, limiar 70, ramo `todos`)
--            nascem sozinhas, sem nome nem id de corretora em código (CLAUDE.md §13.9).
--
-- 📊 ANTES (01/10/2026, SELECT read-only pelo MCP):
--    · llm_papeis: destravador = openai gpt-6.1-sol high · reserva anthropic claude-sonnet-5-5 (v1);
--      destravador_segunda = anthropic claude-sonnet-5-5 · reserva openai gpt-6.1-sol high (v1).
--    · claude-opus-5-5: APPROVED, provider anthropic, classes [publico, interno, pii], sem
--      esforco_minimo_producao (o `dispatch` o usa com esforço NULO).
--    · cerebro_modos: 40 linhas, todas `on`/70/`todos` — 10 seguradoras × 4 corretoras
--      (migration 20261001_02). agents: 1 trigger (`atendimento_nasce_desligado`, BEFORE INSERT).
--
-- 🔴 D9 — POR QUE UM GATILHO NO BANCO, E NÃO O "PONTO ÚNICO QUE CRIA O AGENTE":
--    o código tem UM escritor de `agents` (`agent_service.create_agent`), mas agente também
--    nasce por SQL, seed e painel do banco (as 4 corretoras de hoje nasceram assim). Um gancho
--    no Python deixaria esses caminhos sem destravador — em silêncio. O gatilho pega TODA
--    escrita, pelo mesmo princípio de `atendimento_nasce_desligado` (o agente nasce DESLIGADO
--    no banco, qualquer que seja o caminho).
-- 🔴 D9 — DE ONDE VEM A LISTA DE SEGURADORAS ("uma verdade"): da PRÓPRIA `cerebro_modos` —
--    as seguradoras em que a plataforma tem o destravador `on` em alguma corretora. Nenhuma
--    lista nova (a 20261001_02 tem a dela, escrita uma vez); uma seguradora ligada depois para
--    todas passa a valer para as novas; tabela vazia → nada nasce → `off` (sem linha = off,
--    que continua sendo o desfazer). ⛔ `corridor_templates` foi descartada: 📊 16 das 17
--    linhas são `scope='tenant'` de UMA corretora — não é o catálogo da plataforma.
--    ⛔ Nunca sobrescreve: `on conflict do nothing` — uma seguradora `off` (ou com limiar
--    calibrado) de uma corretora continua como está.
-- 🔴 SECURITY DEFINER: `cerebro_modos` tem RLS ligada e ZERO policy (só o service role
--    escreve). Sem DEFINER, um agente criado por um papel sem bypass de RLS teria o INSERT do
--    agente DERRUBADO pelo gatilho. `search_path` fixo (pg_catalog, public).
--
-- APPLY:
--   A. llm_papeis (UPDATE → o trigger `llm_papeis_registrar_historico` grava a linha anterior e
--      sobe a versão; `llm_papeis_so_modelo_governado` confere catálogo/APPROVED/classe):
--      destravador_segunda: primário anthropic claude-opus-5-5 (esforço NULO), reserva openai
--      gpt-6.1-sol high (igual); destravador: reserva anthropic claude-opus-5-5 (esforço NULO).
--   B. função `tg_destravador_nasce_ligado()` + gatilho AFTER INSERT OR UPDATE OF agent_role,
--      company_id ON agents.
--
-- VERIFY (read-only; o bloco DO desfaz tudo o que testa):
--   -- 1) os papéis
--   select papel, provider, modelo_primario, esforco, provider_reserva, modelo_reserva,
--          esforco_reserva, versao from public.llm_papeis where papel like 'destravador%' order by 1;
--   -- esperado: destravador | openai | gpt-6.1-sol | high | anthropic | claude-opus-5-5 | NULL | 2
--   --           destravador_segunda | anthropic | claude-opus-5-5 | NULL | openai | gpt-6.1-sol | high | 2
--   select papel, versao, alterado_por from public.llm_papeis_historico
--    where alterado_por = 'migration 20261001_06' order by 1;           -- esperado 2 linhas
--   -- 2) o gatilho existe
--   select tgname from pg_trigger where tgrelid = 'public.agents'::regclass and not tgisinternal order by 1;
--   -- esperado: atendimento_nasce_desligado · destravador_nasce_ligado
--   -- 3) 🔴 corretora NOVA + agente de atendimento → 10 linhas `on`; a corretora EXISTENTE com uma
--   --    seguradora `off` continua `off`; agente de outro papel não cria nada. Tudo desfeito.
--   do $$
--   declare v_nova uuid := gen_random_uuid(); v_velha uuid; v_seg text; n_nova int; n_on int;
--           n_outro int; modo_velho text; n_esperado int;
--   begin
--     select count(distinct insurer_key) into n_esperado from public.cerebro_modos where modo = 'on';
--     begin
--       insert into public.companies (id, company_name) values (v_nova, 'verify-125-s9');
--       -- agente de OUTRO papel: nada nasce
--       insert into public.agents (company_id, name, slug, agent_role) values (v_nova, 'verify-core', 'verify-core', 'core');
--       select count(*) into n_outro from public.cerebro_modos where company_id = v_nova;
--       -- agente de ATENDIMENTO: as linhas nascem
--       insert into public.agents (company_id, name, slug, agent_role) values (v_nova, 'verify-att', 'verify-att', 'attendance');
--       select count(*), count(*) filter (where modo = 'on' and limiar = 70 and ramo = 'todos')
--         into n_nova, n_on from public.cerebro_modos where company_id = v_nova;
--       -- corretora EXISTENTE: uma seguradora vira `off`, e um agente NOVO de atendimento não a religa
--       select company_id, insurer_key into v_velha, v_seg from public.cerebro_modos limit 1;
--       update public.cerebro_modos set modo = 'off' where company_id = v_velha and insurer_key = v_seg
--         and ramo = 'todos';
--       insert into public.agents (company_id, name, slug, agent_role) values (v_velha, 'verify-att-2', 'verify-att-2-125', 'attendance');
--       select modo into modo_velho from public.cerebro_modos
--        where company_id = v_velha and insurer_key = v_seg and ramo = 'todos';
--       raise exception using errcode = 'P0001', message = 'desfaz-verify';
--     exception when sqlstate 'P0001' then null; end;
--     if n_outro <> 0 or n_nova <> n_esperado or n_on <> n_esperado or n_esperado <> 10
--        or modo_velho is distinct from 'off' then
--       raise exception 'VERIFY 20261001_06 FALHOU: outro=% nova=% on=% esperado=% velho=%',
--         n_outro, n_nova, n_on, n_esperado, modo_velho;
--     end if;
--     if exists (select 1 from public.companies where id = v_nova) then
--       raise exception 'VERIFY 20261001_06: a corretora de teste ficou gravada';
--     end if;
--     raise notice 'VERIFY 20261001_06 OK: core=0 · atendimento=% on/70/todos · off existente continua off', n_nova;
--   end $$;
--
-- ROLLBACK:  (escrito ANTES de aplicar)
--   drop trigger if exists destravador_nasce_ligado on public.agents;
--   drop function if exists public.tg_destravador_nasce_ligado();
--   -- (as linhas que o gatilho criou ficam: são `on` e o desfazer de cada uma é apagá-la — sem linha = off)
--   update public.llm_papeis
--      set provider = 'anthropic', modelo_primario = 'claude-sonnet-5-5', esforco = null,
--          motivo = 'ROLLBACK 20261001_06 — volta ao Sonnet 5.5', atualizado_por = 'rollback 20261001_06'
--    where papel = 'destravador_segunda';
--   update public.llm_papeis
--      set provider_reserva = 'anthropic', modelo_reserva = 'claude-sonnet-5-5', esforco_reserva = null,
--          motivo = 'ROLLBACK 20261001_06 — volta ao Sonnet 5.5', atualizado_por = 'rollback 20261001_06'
--    where papel = 'destravador';
--   delete from supabase_migrations.schema_migrations where name = 'spec125_destravador_opus_e_corretora_nova';
--   -- e regerar o snapshot: python scripts/gerar_snapshot_de_modelos.py --banco
--
-- EXPAND-FIRST: sim — 2 rotas trocadas (histórico em llm_papeis_historico), 1 função e 1
--               gatilho novos; nenhuma coluna, CHECK ou linha existente de cerebro_modos muda.
-- DESTRUTIVA:   não.
-- =============================================================

-- -------------------------------------------------------------
-- A. D8 — o Opus 5.5 na 2ª opinião e na reserva do destravador
-- -------------------------------------------------------------
update public.llm_papeis
   set provider = 'anthropic', modelo_primario = 'claude-opus-5-5', esforco = null,
       motivo = 'SPEC-125 D8 · Founder 01/10/2026 — Opus 5.5 na 2ª opinião do destravador',
       atualizado_por = 'migration 20261001_06'
 where papel = 'destravador_segunda'
   and modelo_primario is distinct from 'claude-opus-5-5';

update public.llm_papeis
   set provider_reserva = 'anthropic', modelo_reserva = 'claude-opus-5-5', esforco_reserva = null,
       motivo = 'SPEC-125 D8 · Founder 01/10/2026 — Opus 5.5 na reserva do destravador',
       atualizado_por = 'migration 20261001_06'
 where papel = 'destravador'
   and modelo_reserva is distinct from 'claude-opus-5-5';

-- -------------------------------------------------------------
-- B. D9 — a corretora que ganha agente de atendimento nasce com o destravador ligado
-- -------------------------------------------------------------
create or replace function public.tg_destravador_nasce_ligado()
returns trigger
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
begin
  if new.company_id is null or lower(coalesce(new.agent_role, '')) <> 'attendance' then
    return new;
  end if;
  -- as seguradoras em que a plataforma tem o destravador `on` (a própria cerebro_modos é a
  -- verdade); nunca sobrescreve uma linha da corretora (off, sombra ou limiar calibrado)
  insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, limiar, motivo, ligado_por)
  select new.company_id, s.insurer_key, 'todos', 'on', 70,
         'SPEC-125 D9: corretora com agente de atendimento nasce com o destravador ligado '
         || '(DEDUZIR autônomo desligado em código até calibrar)',
         'gatilho destravador_nasce_ligado (migration 20261001_06)'
    from (select distinct insurer_key from public.cerebro_modos where modo = 'on') s
  on conflict (company_id, insurer_key, ramo) do nothing;
  return new;
end $$;

comment on function public.tg_destravador_nasce_ligado() is
  'SPEC-125 D9 — quando uma corretora ganha agente attendance, nasce uma linha cerebro_modos on/70/todos por seguradora em que a plataforma já tem o destravador on. Nunca sobrescreve. SECURITY DEFINER porque cerebro_modos tem RLS sem policy.';

drop trigger if exists destravador_nasce_ligado on public.agents;
create trigger destravador_nasce_ligado
  after insert or update of agent_role, company_id on public.agents
  for each row execute function public.tg_destravador_nasce_ligado();
