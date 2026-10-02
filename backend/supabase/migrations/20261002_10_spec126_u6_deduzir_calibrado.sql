-- =============================================================
-- MIGRATION: 20261002_10_spec126_u6_deduzir_calibrado
-- SPEC:      SPEC-126 — U6 · a DEDUÇÃO calibrada do destravador
-- AUTOR:     builder U6 (Opus 5.5 xhigh)      DATA: 2026-10-02
-- OBJETIVO:  a chave do DEDUZIR autônomo sai da constante GLOBAL do código
--            (`destravador.DEDUZIR_AUTONOMO_CALIBRADO = False`) para a linha de
--            `cerebro_modos` — por CORRETORA × SEGURADORA × RAMO —, desligada por padrão,
--            e só liga com a PROVA da rodada de calibração gravada ao lado.
--
-- 📊 ANTES (02/10/2026, SELECT read-only pelo MCP, project dcajcvlzcjbmyapmklil):
--    · colunas: company_id uuid · insurer_key text · ramo text ('todos') · modo text ('off') ·
--      motivo · ligado_por · created_at · updated_at · limiar smallint (70).
--    · 40 linhas, todas on/70/todos — 4 corretoras × 10 seguradoras
--      (alfa, allianz, azul, bradesco, hdi, mapfre, porto, tokio, yelum, zurich).
--    · constraints: pk (company_id, insurer_key, ramo) · fk companies ON DELETE CASCADE ·
--      ck insurer/ramo minúsculos · ck limiar 70..100 · ck modo off|sombra|on.
--
-- 🔴 POR QUE NA MESMA TABELA (SPEC-126 BLOCO 0 item 7, "sem tabela nova"): a chave do
--    destravador JÁ é por corretora × seguradora × ramo, e o leitor ÚNICO
--    (`acao_do_cerebro._ler_chaves`) já filtra por company_id no código (CLAUDE.md §7).
--    "Sem linha = desligado" continua sendo o desfazer; agora "deduzir_calibrado = false"
--    também é.
-- 🔴 POR QUE A PROVA NO BANCO E NO CÓDIGO: o CHECK recusa ligar sem n ≥ 10, acerto ≥ 90 % e
--    o controle "tecla 1" batido; o código (`destravador.prova_de_calibracao`) RECALCULA o
--    Wilson e recusa de novo (o código não confia no banco). Os números são as constantes
--    `DEDUZIR_N_MINIMO` / `DEDUZIR_ACERTO_MINIMO` / `DEDUZIR_WILSON_MINIMO` (com o porquê lá).
-- 🔴 O GATILHO D9 (`tg_destravador_nasce_ligado`, 20261001_06) insere sem estas colunas:
--    a corretora NOVA nasce com `deduzir_calibrado = false` (o padrão). Nada muda nele.
--
-- APPLY:
--   A. coluna `deduzir_calibrado boolean not null default false` (tabela de 40 linhas: o
--      default não reescreve nada que importe; todas nascem false).
--   B. coluna `calibracao jsonb` (nula) — a PROVA: {n, certos, controle_n, controle_certos,
--      modelo_proposta_certos, wilson_inf, wilson_sup, rodada, braco, segunda, medido_em}.
--   C. função IMUTÁVEL `cerebro_modos_prova_vale(jsonb)` e o CHECK
--      `ck_cerebro_modos_deduzir_so_com_prova` (deduzir_calibrado → a prova vale).
--   D. comments.
--
-- VERIFY (read-only; o bloco DO desfaz tudo o que testa):
--   -- 1) as colunas
--   select column_name, data_type, is_nullable, column_default from information_schema.columns
--    where table_schema = 'public' and table_name = 'cerebro_modos'
--      and column_name in ('deduzir_calibrado', 'calibracao') order by 1;
--   -- esperado: calibracao · jsonb · YES · NULL  |  deduzir_calibrado · boolean · NO · false
--   -- 2) NENHUMA linha ligada pela migration (o padrão é desligado)
--   select count(*) filter (where deduzir_calibrado) ligadas, count(*) total from public.cerebro_modos;
--   -- esperado: ligadas = 0 · total = 40 (ou o que houver)
--   -- 3) 🔴 O CHECK CONSEGUE RECUSAR (CLAUDE.md §9.3): ligar sem prova, com n = 9, com 8/10 e
--   --    sem bater o controle → recusados; a prova boa (10/10, controle 6/10 < modelo 9/10) →
--   --    ACEITA (controle) — e nada fica gravado.
--   do $$
--   declare v_cid uuid; r_sem boolean := false; r_n9 boolean := false; r_8de10 boolean := false;
--           r_ctl boolean := false; aceitou boolean := false; n int;
--   begin
--     select company_id into v_cid from public.cerebro_modos limit 1;
--     begin
--       insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, deduzir_calibrado)
--       values (v_cid, 'verify_126', 'todos', 'on', true);
--     exception when check_violation then r_sem := true; end;
--     begin
--       insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, deduzir_calibrado, calibracao)
--       values (v_cid, 'verify_126', 'todos', 'on', true, '{"n":9,"certos":9,"controle_n":9,"controle_certos":5,"modelo_proposta_certos":8,"rodada":"v"}');
--     exception when check_violation then r_n9 := true; end;
--     begin
--       insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, deduzir_calibrado, calibracao)
--       values (v_cid, 'verify_126', 'todos', 'on', true, '{"n":10,"certos":8,"controle_n":10,"controle_certos":5,"modelo_proposta_certos":8,"rodada":"v"}');
--     exception when check_violation then r_8de10 := true; end;
--     begin
--       insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, deduzir_calibrado, calibracao)
--       values (v_cid, 'verify_126', 'todos', 'on', true, '{"n":10,"certos":10,"controle_n":10,"controle_certos":7,"modelo_proposta_certos":7,"rodada":"v"}');
--     exception when check_violation then r_ctl := true; end;
--     begin  -- CONTROLE: a prova boa PASSA (e é desfeita pelo raise do sub-bloco)
--       insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, deduzir_calibrado, calibracao)
--       values (v_cid, 'verify_126', 'todos', 'on', true, '{"n":10,"certos":10,"controle_n":10,"controle_certos":6,"modelo_proposta_certos":9,"rodada":"v"}');
--       aceitou := true;
--       raise exception using errcode = 'P0001', message = 'desfaz-controle';
--     exception when sqlstate 'P0001' then null; end;
--     select count(*) into n from public.cerebro_modos where insurer_key = 'verify_126';
--     if not (r_sem and r_n9 and r_8de10 and r_ctl and aceitou) or n <> 0 then
--       raise exception 'VERIFY 20261002_10 FALHOU: sem=% n9=% 8de10=% ctl=% boa=% sobrou=%',
--         r_sem, r_n9, r_8de10, r_ctl, aceitou, n;
--     end if;
--     raise notice 'VERIFY 20261002_10 OK: sem prova/n9/8de10/controle recusados, prova boa aceita, nada gravado';
--   end $$;
--
-- ROLLBACK:  (escrito ANTES de aplicar)
--   -- o código lê com select("*") e trata a coluna ausente como "desligado": tirar as colunas
--   -- devolve o produto ao de antes (DEDUZIR desligado em toda corretora).
--   alter table public.cerebro_modos drop constraint if exists ck_cerebro_modos_deduzir_so_com_prova;
--   drop function if exists public.cerebro_modos_prova_vale(jsonb);
--   alter table public.cerebro_modos drop column if exists calibracao;
--   alter table public.cerebro_modos drop column if exists deduzir_calibrado;
--   delete from supabase_migrations.schema_migrations where name = 'spec126_u6_deduzir_calibrado';
--
-- EXPAND-FIRST: sim — duas colunas novas com default/nula, uma função e um CHECK novos; nenhuma
--               coluna, CHECK ou linha existente muda.
-- DESTRUTIVA:   não. Esta migration NÃO liga nada: ligar é UPDATE por linha, com a prova, depois
--               da rodada de calibração (o SQL sai de `evals.bancada.sql_de_religar`).
-- =============================================================

-- -------------------------------------------------------------
-- A/B. a chave e a prova
-- -------------------------------------------------------------
alter table public.cerebro_modos
  add column if not exists deduzir_calibrado boolean not null default false;

alter table public.cerebro_modos
  add column if not exists calibracao jsonb;

-- -------------------------------------------------------------
-- C. a prova vale? (CASE garante a ORDEM: nada é convertido antes de o tipo ser conferido)
-- -------------------------------------------------------------
create or replace function public.cerebro_modos_prova_vale(p jsonb)
returns boolean
language sql
immutable
set search_path = pg_catalog, public
as $$
  select case
    when p is null or jsonb_typeof(p) <> 'object' then false
    when coalesce(jsonb_typeof(p->'n'), '') <> 'number'
      or coalesce(jsonb_typeof(p->'certos'), '') <> 'number'
      or coalesce(jsonb_typeof(p->'controle_n'), '') <> 'number'
      or coalesce(jsonb_typeof(p->'controle_certos'), '') <> 'number'
      or coalesce(jsonb_typeof(p->'modelo_proposta_certos'), '') <> 'number' then false
    when coalesce(p->>'rodada', '') = '' then false
    else (p->>'n')::numeric >= 10
     and (p->>'certos')::numeric between 0 and (p->>'n')::numeric
     and (p->>'certos')::numeric >= 0.90 * (p->>'n')::numeric
     and (p->>'controle_n')::numeric > 0
     and (p->>'modelo_proposta_certos')::numeric > (p->>'controle_certos')::numeric
  end
$$;

comment on function public.cerebro_modos_prova_vale(jsonb) is
  'SPEC-126 U6 — a prova da calibração do DEDUZIR vale? n >= 10, acerto >= 90 %, o modelo bateu o controle "tecla 1". O Wilson >= 70 % é recalculado no código (destravador.prova_de_calibracao).';

do $$
begin
  if not exists (select 1 from pg_constraint
                  where conrelid = 'public.cerebro_modos'::regclass
                    and conname = 'ck_cerebro_modos_deduzir_so_com_prova') then
    alter table public.cerebro_modos
      add constraint ck_cerebro_modos_deduzir_so_com_prova
      check (case when deduzir_calibrado then public.cerebro_modos_prova_vale(calibracao) else true end);
  end if;
end $$;

-- -------------------------------------------------------------
-- D. a tabela diz a verdade de hoje
-- -------------------------------------------------------------
comment on column public.cerebro_modos.deduzir_calibrado is
  'SPEC-126 U6 — o DEDUZIR desta corretora × seguradora × ramo age sozinho (com nota >= limiar e 2ª opinião de outro provedor concordando). Padrão false = rebaixa (pergunta ao segurado ou pessoa). Só true com a prova em calibracao (ck_cerebro_modos_deduzir_so_com_prova).';
comment on column public.cerebro_modos.calibracao is
  'SPEC-126 U6 — a PROVA da rodada de calibração (scripts/bancada.py --resumo-calibracao): n e certos (casos que agiram, certos nas k tentativas), o controle "tecla 1" no mesmo conjunto, Wilson, rodada, braços, data.';
