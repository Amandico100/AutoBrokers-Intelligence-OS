-- SPEC-062 Bloco A — Release Evidence Fabric: avaliação com prova.
--
-- POR QUE ESTAS TABELAS EXISTEM
-- =============================
-- O sistema está a horas de ser apontado para o WhatsApp real de duas
-- corretoras. Hoje, se a qualidade de uma resposta piorar, ninguém descobre:
-- não há nada que compare o comportamento de hoje com o de ontem. O corretor
-- simplesmente para de usar, e a causa nunca aparece.
--
-- O `broker_outcome_regression_pack` já prova CONDUTA (o código faz o que
-- deve). Ele não prova QUALIDADE (a resposta continua boa). São perguntas
-- diferentes e precisam de mecânicas diferentes: conduta é determinística e
-- binária; qualidade é comparativa e tem nota.
--
-- DECISÕES DE MODELAGEM
-- =====================
-- 1. Dataset e VERSÃO são separados (§10.1/10.2). Um caso que muda de
--    expectativa sem mudar de versão apaga a única base de comparação — a nota
--    de hoje deixa de significar o mesmo que a de ontem.
--
-- 2. `eval_cases` é append-only por versão. Corrigir um caso cria versão nova.
--
-- 3. `eval_runs` guarda o COMMIT e o MODELO. Sem os dois, uma queda de nota não
--    tem causa investigável: foi o código ou foi o provedor trocando o modelo
--    por baixo?
--
-- 4. `expected` é jsonb e não texto: um caso determinístico expressa contrato
--    ("contém estes campos", "não contém CPF"), e contrato não cabe em string.
--
-- 5. Tudo é da PLATAFORMA, não da corretora — `company_id` é opcional e serve
--    para casos que usam dado real de um tenant. Quando presente, RLS e filtro
--    valem igual (CLAUDE.md §7).
--
-- APPLY   : este arquivo, idempotente (IF NOT EXISTS em tudo)
-- VERIFY  : bloco DO ao final; levanta exceção e aborta se algo não bater
-- ROLLBACK: no rodapé, comentado, por nome exato — nunca por LIKE

-- ---------------------------------------------------------------------------
-- 1. Datasets e versões
-- ---------------------------------------------------------------------------
create table if not exists public.eval_datasets (
  id            uuid primary key default gen_random_uuid(),
  slug          text not null unique,
  nome          text not null,
  dominio       text not null,
  descricao     text,
  risco         text not null default 'medio',
  is_active     boolean not null default true,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  constraint eval_datasets_risco_ck
    check (risco in ('baixo', 'medio', 'alto', 'critico'))
);

comment on table public.eval_datasets is
  'SPEC-062 §10.1 — conjunto de casos de um domínio. O risco governa o gate: '
  'domínio crítico não passa com nota parcial.';

create table if not exists public.eval_dataset_versions (
  id            uuid primary key default gen_random_uuid(),
  dataset_id    uuid not null references public.eval_datasets(id) on delete cascade,
  versao        integer not null,
  notas         text,
  congelada_em  timestamptz,
  created_at    timestamptz not null default now(),
  unique (dataset_id, versao)
);

comment on column public.eval_dataset_versions.congelada_em is
  'Versão congelada não aceita caso novo. Comparar notas entre versões '
  'diferentes compara coisas diferentes — o congelamento torna isso visível.';

-- ---------------------------------------------------------------------------
-- 2. Casos
-- ---------------------------------------------------------------------------
create table if not exists public.eval_cases (
  id            uuid primary key default gen_random_uuid(),
  version_id    uuid not null references public.eval_dataset_versions(id) on delete cascade,
  chave         text not null,
  entrada       jsonb not null,
  expected      jsonb not null default '{}'::jsonb,
  peso          numeric not null default 1,
  company_id    uuid references public.companies(id) on delete set null,
  tags          text[] not null default '{}',
  created_at    timestamptz not null default now(),
  unique (version_id, chave),
  constraint eval_cases_peso_ck check (peso > 0)
);

comment on column public.eval_cases.expected is
  'Contrato, não texto esperado. Ex.: {"contem":["apolice"],"nao_contem_pii":true}. '
  'Comparar string exata com saída de LLM produz teste que quebra sozinho.';

-- ---------------------------------------------------------------------------
-- 3. Evaluators
-- ---------------------------------------------------------------------------
create table if not exists public.evaluator_definitions (
  id            uuid primary key default gen_random_uuid(),
  slug          text not null unique,
  nome          text not null,
  tipo          text not null,
  config        jsonb not null default '{}'::jsonb,
  is_active     boolean not null default true,
  created_at    timestamptz not null default now(),
  constraint evaluator_tipo_ck
    check (tipo in ('deterministico', 'llm_judge', 'humano', 'pairwise'))
);

comment on table public.evaluator_definitions is
  'SPEC-062 §12 — hierarquia obrigatória: determinístico PRIMEIRO. Usar juiz '
  'LLM onde regra resolve troca uma resposta certa por uma opinião cara.';

-- ---------------------------------------------------------------------------
-- 4. Execuções
-- ---------------------------------------------------------------------------
create table if not exists public.eval_runs (
  id              uuid primary key default gen_random_uuid(),
  version_id      uuid not null references public.eval_dataset_versions(id) on delete cascade,
  commit_sha      text,
  modelo          text,
  provedor        text,
  gatilho         text not null default 'manual',
  status          text not null default 'running',
  total           integer not null default 0,
  passaram        integer not null default 0,
  nota            numeric,
  iniciado_em     timestamptz not null default now(),
  terminado_em    timestamptz,
  constraint eval_runs_status_ck
    check (status in ('running', 'passed', 'failed', 'error')),
  constraint eval_runs_nota_ck
    check (nota is null or (nota >= 0 and nota <= 1))
);

comment on column public.eval_runs.commit_sha is
  'Sem commit e modelo, uma queda de nota não tem causa investigável: foi o '
  'código ou foi o provedor trocando o modelo por baixo?';

create table if not exists public.eval_case_results (
  id              uuid primary key default gen_random_uuid(),
  run_id          uuid not null references public.eval_runs(id) on delete cascade,
  case_id         uuid not null references public.eval_cases(id) on delete cascade,
  evaluator_slug  text not null,
  passou          boolean not null,
  nota            numeric,
  motivo          text,
  duracao_ms      integer,
  created_at      timestamptz not null default now(),
  unique (run_id, case_id, evaluator_slug)
);

comment on column public.eval_case_results.motivo is
  'Obrigatório na falha e em português. "assert failed" não diz a ninguém o '
  'que o corretor vai sentir.';

-- ---------------------------------------------------------------------------
-- 5. Release Candidates e gates
-- ---------------------------------------------------------------------------
create table if not exists public.release_candidates (
  id              uuid primary key default gen_random_uuid(),
  commit_sha      text not null,
  branch          text,
  manifesto       jsonb not null default '{}'::jsonb,
  status          text not null default 'aberto',
  decidido_por    text,
  decidido_em     timestamptz,
  motivo          text,
  created_at      timestamptz not null default now(),
  unique (commit_sha),
  constraint release_status_ck
    check (status in ('aberto', 'aprovado', 'reprovado', 'implantado'))
);

comment on table public.release_candidates is
  'SPEC-062 §14 — o que foi para produção, com prova. Sem isto, "o que mudou '
  'desde ontem" só existe na memória de quem implantou.';

create table if not exists public.release_gate_results (
  id              uuid primary key default gen_random_uuid(),
  candidate_id    uuid not null references public.release_candidates(id) on delete cascade,
  gate            text not null,
  passou          boolean not null,
  detalhe         jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now(),
  unique (candidate_id, gate)
);

-- ---------------------------------------------------------------------------
-- 6. SLIs — a medição que vira SLO depois de haver tráfego real
-- ---------------------------------------------------------------------------
create table if not exists public.sli_samples (
  id              uuid primary key default gen_random_uuid(),
  sli             text not null,
  company_id      uuid references public.companies(id) on delete cascade,
  valor           numeric not null,
  unidade         text not null default 'ms',
  contexto        jsonb not null default '{}'::jsonb,
  observado_em    timestamptz not null default now()
);

comment on table public.sli_samples is
  'SPEC-062 §18 — SLO sem baseline é chute. Mede-se primeiro, promete-se '
  'depois. Sete dias de observação produzem a primeira base real.';

-- ---------------------------------------------------------------------------
-- 7. Índices — as perguntas que estas tabelas realmente respondem
-- ---------------------------------------------------------------------------
create index if not exists ix_eval_cases_versao
  on public.eval_cases (version_id);
create index if not exists ix_eval_results_run
  on public.eval_case_results (run_id, passou);
create index if not exists ix_eval_runs_recentes
  on public.eval_runs (version_id, iniciado_em desc);
create index if not exists ix_sli_samples_janela
  on public.sli_samples (sli, observado_em desc);
create index if not exists ix_sli_samples_empresa
  on public.sli_samples (company_id, observado_em desc)
  where company_id is not null;

-- ---------------------------------------------------------------------------
-- 8. Segurança — RLS ligada, ZERO policies (CLAUDE.md §7)
-- ---------------------------------------------------------------------------
-- Sem policy, anon e authenticated não leem nada. O backend usa service role e
-- passa por cima da RLS — por isso o filtro por `company_id` no repositório
-- continua obrigatório. RLS aqui é a rede, não o chão.
do $$
declare t text;
begin
  foreach t in array array[
    'eval_datasets','eval_dataset_versions','eval_cases','evaluator_definitions',
    'eval_runs','eval_case_results','release_candidates','release_gate_results',
    'sli_samples'
  ] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon, authenticated', t);
  end loop;
end $$;

-- ---------------------------------------------------------------------------
-- 9. Append-only nos resultados: nota não se reescreve
-- ---------------------------------------------------------------------------
-- Se um resultado ruim puder ser editado, a série histórica deixa de ser
-- prova. Rodar de novo cria um run novo — é assim que se corrige.
create or replace function public.tg_eval_results_append_only()
returns trigger language plpgsql as $$
begin
  raise exception 'eval_case_results e append-only: rode um novo eval_run';
end $$;

drop trigger if exists eval_results_append_only on public.eval_case_results;
create trigger eval_results_append_only
  before update or delete on public.eval_case_results
  for each row execute function public.tg_eval_results_append_only();

-- ---------------------------------------------------------------------------
-- VERIFY — aborta e nada persiste se algo não bater
-- ---------------------------------------------------------------------------
do $$
declare
  v_faltando text := '';
  v_t text;
  v_rls int;
  v_trg int;
begin
  foreach v_t in array array[
    'eval_datasets','eval_dataset_versions','eval_cases','evaluator_definitions',
    'eval_runs','eval_case_results','release_candidates','release_gate_results',
    'sli_samples'
  ] loop
    if to_regclass('public.' || v_t) is null then
      v_faltando := v_faltando || v_t || ' ';
    end if;
  end loop;

  if v_faltando <> '' then
    raise exception 'VERIFY FALHOU — tabelas ausentes: %', v_faltando;
  end if;

  select count(*) into v_rls from pg_tables
   where schemaname = 'public'
     and tablename in ('eval_datasets','eval_dataset_versions','eval_cases',
                       'evaluator_definitions','eval_runs','eval_case_results',
                       'release_candidates','release_gate_results','sli_samples')
     and rowsecurity = true;
  if v_rls <> 9 then
    raise exception 'VERIFY FALHOU — RLS ligada em % de 9 tabelas', v_rls;
  end if;

  select count(*) into v_trg from pg_trigger
   where tgname = 'eval_results_append_only' and not tgisinternal;
  if v_trg <> 1 then
    raise exception 'VERIFY FALHOU — gatilho append-only ausente';
  end if;

  raise notice 'VERIFY OK — 9 tabelas, RLS ligada em todas, append-only ativo';
end $$;

-- ---------------------------------------------------------------------------
-- ROLLBACK (não executar sem decisão registrada)
-- ---------------------------------------------------------------------------
-- Por nome exato. NUNCA por LIKE: um `drop ... like 'eval%'` derrubaria
-- qualquer tabela futura cujo nome comece igual.
--
--   drop trigger if exists eval_results_append_only on public.eval_case_results;
--   drop function if exists public.tg_eval_results_append_only();
--   drop table if exists public.eval_case_results;
--   drop table if exists public.eval_runs;
--   drop table if exists public.eval_cases;
--   drop table if exists public.eval_dataset_versions;
--   drop table if exists public.eval_datasets;
--   drop table if exists public.evaluator_definitions;
--   drop table if exists public.release_gate_results;
--   drop table if exists public.release_candidates;
--   drop table if exists public.sli_samples;
