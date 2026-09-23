-- =============================================================
-- MIGRATION: spec116_bancada_na_eval_fabric
-- SPEC:      SPEC-116 — U11 (fatia F5a) · a BANCADA E2E estende a Eval Fabric
-- AUTOR:     builder F5a (Opus)          DATA: 2026-09-23
-- OBJETIVO:  a Eval Fabric da SPEC-062 passa a guardar o BRAÇO (provider,
--            model, effort…) de cada rodada e, por caso, o resultado com custo,
--            tokens, latência e rastro de tools — de onde saem pass@1, pass^k
--            e custo por sucesso por braço × papel.
--
-- POR QUE ESTENDER E NÃO CRIAR `bench_*` (D-116-04, nota 95 × 10)
--   A SPEC-062 já tem dataset → versão congelada → caso → run → resultado,
--   com RLS ligada e resultado append-only. Tabelas `bench_*` seriam um
--   segundo Eval Platform (CLAUDE.md §5). Cada TENTATIVA vira um eval_run
--   próprio; `grupo_bancada` junta as k tentativas e os braços de uma rodada.
--   A UNIQUE (run_id, case_id, evaluator_slug) NÃO é tocada.
--
-- 📊 BLOCO 0 (23/09/2026, SELECT em information_schema.columns, projeto
--    dcajcvlzcjbmyapmklil): eval_runs = id, version_id, commit_sha, modelo,
--    provedor, gatilho, status, total, passaram, nota, iniciado_em,
--    terminado_em · eval_case_results = id, run_id, case_id, evaluator_slug,
--    passou, nota, motivo, duracao_ms, created_at · 0 runs, 0 resultados
--    (`select count(*) from eval_runs` → 0; `… eval_case_results` → 0).
--
-- APPLY:     só ADD COLUMN IF NOT EXISTS (anuláveis, sem default que reescreva
--            tabela) + 3 CHECKs criados só se ausentes + 1 índice IF NOT EXISTS.
--            Nenhuma linha existente muda (são 0 hoje, e seriam intocadas).
-- VERIFY:    bloco DO no fim — aborta a transação se faltar coluna/CHECK/índice
--            ou se a UNIQUE original tiver sumido.
-- ROLLBACK:  no rodapé, comentado, por NOME EXATO (nunca por LIKE).
--
-- EXPAND-FIRST: sim (só acrescenta)
-- DESTRUTIVA:   não
-- RLS:          as duas tabelas já estão com RLS ligada e ZERO policies desde a
--               20260727_07 (service role only). Coluna nova herda — nada muda
--               em quem pode ler.
-- =============================================================

-- ---------------------------------------------------------------------------
-- 1. eval_runs — o BRAÇO e a rodada
-- ---------------------------------------------------------------------------
alter table public.eval_runs add column if not exists braco          jsonb;
alter table public.eval_runs add column if not exists papel          text;
alter table public.eval_runs add column if not exists nivel          text;
alter table public.eval_runs add column if not exists grupo_bancada  uuid;
alter table public.eval_runs add column if not exists tentativa      integer;
alter table public.eval_runs add column if not exists custo_usd      numeric;
alter table public.eval_runs add column if not exists tokens         jsonb;
-- ACRÉSCIMO ao texto da SPEC (reportado): o run que o teto de US$ corta fecha
-- com status 'error' e PRECISA dizer por quê. Sem esta coluna o motivo "teto_usd"
-- não teria onde morar, e um run cortado seria indistinguível de um que quebrou.
alter table public.eval_runs add column if not exists motivo_parada  text;

comment on column public.eval_runs.braco is
  'SPEC-116 U11 — o braço medido: {provider, model, effort, api_surface, '
  'prompt_hash, tools_hash, versao_da_rota}. Sem ele, uma nota não diz de QUAL '
  'modelo é.';
comment on column public.eval_runs.grupo_bancada is
  'SPEC-116 U11 — junta as k tentativas e os braços de UMA rodada da bancada. '
  'pass^k = todas as k tentativas do caso passaram, lidas por este grupo.';
comment on column public.eval_runs.tentativa is
  'SPEC-116 U11 — 1..k. Cada tentativa é um eval_run próprio (a UNIQUE de '
  'eval_case_results continua (run_id, case_id, evaluator_slug)).';
comment on column public.eval_runs.motivo_parada is
  'SPEC-116 U11 — por que o run parou antes do fim (ex.: teto_usd).';

-- ---------------------------------------------------------------------------
-- 2. eval_case_results — o caso, com custo, tokens, latência e rastro
-- ---------------------------------------------------------------------------
alter table public.eval_case_results add column if not exists resultado   text;
alter table public.eval_case_results add column if not exists custo_usd   numeric;
alter table public.eval_case_results add column if not exists tokens      jsonb;
alter table public.eval_case_results add column if not exists latencia_ms integer;
alter table public.eval_case_results add column if not exists rastro      jsonb;
alter table public.eval_case_results add column if not exists erro        text;

comment on column public.eval_case_results.resultado is
  'SPEC-116 U11 — PASS | FAIL | PARTIAL | BLOCKED_BY_INFRA. BLOCKED_BY_INFRA é '
  'falha NOSSA (dublê, ambiente, arnês) e nunca conta contra o modelo.';
comment on column public.eval_case_results.rastro is
  'SPEC-116 U11 — tools chamadas + args + efeitos registrados no dublê + '
  'falhas injetadas. Sem PII: os casos são mascarados no corpus.';

-- ---------------------------------------------------------------------------
-- 3. CHECKs — criados só se ausentes (idempotente)
-- ---------------------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_constraint
                  where conname = 'eval_case_results_resultado_ck'
                    and conrelid = 'public.eval_case_results'::regclass) then
    alter table public.eval_case_results
      add constraint eval_case_results_resultado_ck
      check (resultado is null
             or resultado in ('PASS', 'FAIL', 'PARTIAL', 'BLOCKED_BY_INFRA'));
  end if;

  if not exists (select 1 from pg_constraint
                  where conname = 'eval_runs_nivel_ck'
                    and conrelid = 'public.eval_runs'::regclass) then
    alter table public.eval_runs
      add constraint eval_runs_nivel_ck
      check (nivel is null or nivel in ('N1', 'N2', 'N3'));
  end if;

  if not exists (select 1 from pg_constraint
                  where conname = 'eval_runs_tentativa_ck'
                    and conrelid = 'public.eval_runs'::regclass) then
    alter table public.eval_runs
      add constraint eval_runs_tentativa_ck
      check (tentativa is null or tentativa >= 1);
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- 4. Índice — a pergunta que o relatório faz: "todos os runs deste grupo"
-- ---------------------------------------------------------------------------
create index if not exists ix_eval_runs_grupo_bancada
  on public.eval_runs (grupo_bancada, papel)
  where grupo_bancada is not null;

-- ---------------------------------------------------------------------------
-- VERIFY — aborta e nada persiste se algo não bater
-- ---------------------------------------------------------------------------
do $$
declare
  v_faltando text := '';
  v_col record;
  v_n int;
begin
  for v_col in
    select * from (values
      ('eval_runs','braco'), ('eval_runs','papel'), ('eval_runs','nivel'),
      ('eval_runs','grupo_bancada'), ('eval_runs','tentativa'),
      ('eval_runs','custo_usd'), ('eval_runs','tokens'), ('eval_runs','motivo_parada'),
      ('eval_case_results','resultado'), ('eval_case_results','custo_usd'),
      ('eval_case_results','tokens'), ('eval_case_results','latencia_ms'),
      ('eval_case_results','rastro'), ('eval_case_results','erro')
    ) as t(tabela, coluna)
  loop
    if not exists (select 1 from information_schema.columns
                    where table_schema = 'public'
                      and table_name = v_col.tabela
                      and column_name = v_col.coluna) then
      v_faltando := v_faltando || v_col.tabela || '.' || v_col.coluna || ' ';
    end if;
  end loop;
  if v_faltando <> '' then
    raise exception 'VERIFY FALHOU — colunas ausentes: %', v_faltando;
  end if;

  select count(*) into v_n from pg_constraint
   where conname in ('eval_case_results_resultado_ck', 'eval_runs_nivel_ck',
                     'eval_runs_tentativa_ck');
  if v_n <> 3 then
    raise exception 'VERIFY FALHOU — % de 3 CHECKs presentes', v_n;
  end if;

  if to_regclass('public.ix_eval_runs_grupo_bancada') is null then
    raise exception 'VERIFY FALHOU — índice ix_eval_runs_grupo_bancada ausente';
  end if;

  -- A UNIQUE original NÃO pode ter mudado: cada tentativa é um run próprio.
  select count(*) into v_n from pg_constraint
   where conname = 'eval_case_results_run_id_case_id_evaluator_slug_key'
     and conrelid = 'public.eval_case_results'::regclass;
  if v_n <> 1 then
    raise exception 'VERIFY FALHOU — a UNIQUE (run_id, case_id, evaluator_slug) sumiu';
  end if;

  -- RLS continua ligada (a coluna nova não abre leitura para ninguém).
  select count(*) into v_n from pg_tables
   where schemaname = 'public'
     and tablename in ('eval_runs', 'eval_case_results')
     and rowsecurity = true;
  if v_n <> 2 then
    raise exception 'VERIFY FALHOU — RLS ligada em % de 2 tabelas', v_n;
  end if;

  raise notice 'VERIFY OK — 14 colunas, 3 CHECKs, 1 índice, UNIQUE intacta, RLS ligada';
end $$;

-- ---------------------------------------------------------------------------
-- VERIFY read-only para rodar DEPOIS (SELECT, fora da transação):
--   select table_name, column_name, data_type from information_schema.columns
--    where table_schema='public' and table_name in ('eval_runs','eval_case_results')
--      and column_name in ('braco','papel','nivel','grupo_bancada','tentativa',
--          'custo_usd','tokens','motivo_parada','resultado','latencia_ms','rastro','erro')
--    order by 1,2;                                   -- esperado: 14 linhas
--
-- ROLLBACK (não executar sem decisão registrada) — por nome exato:
--   drop index if exists public.ix_eval_runs_grupo_bancada;
--   alter table public.eval_runs drop constraint if exists eval_runs_tentativa_ck;
--   alter table public.eval_runs drop constraint if exists eval_runs_nivel_ck;
--   alter table public.eval_case_results drop constraint if exists eval_case_results_resultado_ck;
--   alter table public.eval_case_results drop column if exists erro;
--   alter table public.eval_case_results drop column if exists rastro;
--   alter table public.eval_case_results drop column if exists latencia_ms;
--   alter table public.eval_case_results drop column if exists tokens;
--   alter table public.eval_case_results drop column if exists custo_usd;
--   alter table public.eval_case_results drop column if exists resultado;
--   alter table public.eval_runs drop column if exists motivo_parada;
--   alter table public.eval_runs drop column if exists tokens;
--   alter table public.eval_runs drop column if exists custo_usd;
--   alter table public.eval_runs drop column if exists tentativa;
--   alter table public.eval_runs drop column if exists grupo_bancada;
--   alter table public.eval_runs drop column if exists nivel;
--   alter table public.eval_runs drop column if exists papel;
--   alter table public.eval_runs drop column if exists braco;
-- ⚠️ DROP COLUMN em produção exige decisão do Founder (MIGRATIONS-AUTHORITY §8.6).
--    Com runs de bancada gravados, o rollback APAGA a série medida; preferir
--    deixar as colunas (anuláveis, inertes) a derrubá-las.
