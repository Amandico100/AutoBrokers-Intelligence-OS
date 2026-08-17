-- =============================================================
-- MIGRATION: spec075_portal_job_lineage_priority
-- SPEC:      SPEC-075 — Bloco D (lineage) + Bloco N (priority/fairness)
-- AUTOR:     Claude Opus 5 (execução SPEC-075)   DATA: 2026-08-16
-- OBJETIVO:  `portal_jobs` deixa de ser órfão: passa a saber de que Work Run,
--            de que Tool e de que operação de negócio ele nasceu.
--
-- APPLY:     6 colunas novas em `portal_jobs`, todas NULL-áveis, mais 3 índices.
--            Nenhuma coluna existente é tocada. Nenhum dado é reescrito.
-- VERIFY:    ver bloco VERIFY ao final — SQL executável, não texto.
-- ROLLBACK:  ver bloco ROLLBACK ao final. Preferir deixar as colunas INERTES
--            (rollback só do código) a derrubá-las — ver a nota lá embaixo.
--
-- EXPAND-FIRST: sim
-- DESTRUTIVA:   não
-- =============================================================

-- -------------------------------------------------------------------------
-- POR QUE ESTA MIGRATION EXISTE
--
-- 📊 Censo feito em 16/08/2026 sobre todo o repositório: `portal_jobs` tem
-- hoje 17 colunas e NENHUMA delas diz de onde o trabalho veio. Existem quatro
-- escritores (o worker, o `portal_tool`, o `billing_collection` e o dashboard),
-- e um job criado por qualquer um deles é indistinguível dos outros depois de
-- gravado.
--
-- A consequência prática, e ela já dói: quando um acionamento dá errado, não há
-- como perguntar "de que conversa isso veio?" nem "que rotina disparou isso?".
-- O `workflows.py` já tem um workflow `bridge.portal.job` escrito para ligar
-- Work Run a portal_job — e 📊 grep no repositório inteiro mostra que ele NÃO
-- TEM CHAMADOR. A ponte foi construída e nunca foi ligada, porque faltava
-- exatamente o que esta migration acrescenta: onde guardar o vínculo.
--
-- 🔴 O QUE ESTA MIGRATION NÃO FAZ, DE PROPÓSITO
--
-- Não cria tabela nova. Não cria fila nova. Não mexe no índice único parcial
-- `idx_portal_jobs_pedido_vivo`, que é a proteção anti-duplicidade da SPEC-065
-- e que a SPEC-074 provou ser mais delicada do que parecia. Tocar nele aqui
-- seria misturar uma mudança aditiva com uma mudança de semântica de guarda.
-- -------------------------------------------------------------------------

begin;

-- -------------------------------------------------------------------------
-- 1. LINHAGEM — de onde este trabalho veio
--
-- Todas NULL-áveis, e isso é decisão, não descuido: os quatro escritores atuais
-- continuam inserindo sem elas no dia seguinte à aplicação. Uma coluna NOT NULL
-- aqui derrubaria a cobrança e o atendimento de vidros no primeiro insert.
-- Expand-first quer dizer exatamente isso — o schema aceita os dois mundos até
-- o código inteiro ter migrado.
--
-- Sem FK para `work_runs`/`tool_invocations` neste momento. 📊 A DDL dessas
-- tabelas não está no repositório (MIGRATIONS-AUTHORITY §4: 9 versões aplicadas
-- sem arquivo), então uma FK aqui referenciaria uma tabela cuja forma exata eu
-- não posso conferir. FK que falha na aplicação transforma uma migration
-- aditiva num incidente. O vínculo é conferido no código, e a FK entra numa
-- migration própria quando o schema dessas tabelas estiver rastreado.
-- -------------------------------------------------------------------------
alter table public.portal_jobs
  add column if not exists work_run_id uuid;

alter table public.portal_jobs
  add column if not exists work_step_id uuid;

alter table public.portal_jobs
  add column if not exists tool_invocation_id uuid;

-- A operação de NEGÓCIO (`billing.overdue.list`, `assistance.glass.request`).
-- 🔴 Guardada como texto e não como FK para um enum: o registro de operações
-- vive no CÓDIGO (`portal_worker/journeys/__init__.py`), e por um motivo
-- escrito lá — o portal-worker é um serviço separado no EasyPanel e desalinha
-- de banco por desenho. Um enum no banco poderia recusar uma operação que a
-- imagem no ar implementa, ou aceitar uma que ela não tem.
alter table public.portal_jobs
  add column if not exists operation_key text;

-- -------------------------------------------------------------------------
-- 2. PRIORIDADE E JUSTIÇA — Bloco N
--
-- 📊 Hoje o worker é estritamente FIFO: `ORDER BY created_at LIMIT 1`. Isso
-- significa que uma varredura de cobrança de 200 apólices, enfileirada às 3h,
-- fica na frente do acionamento de vidro de um segurado com o carro parado às
-- 9h. O segurado espera a fila inteira.
--
-- `priority` menor = mais urgente, como em `nice(1)` do Unix e no
-- `priority_weight` do Airflow. Default 100 deixa TODO job existente e todo
-- insert que não conhece a coluna exatamente onde está hoje — a ordenação por
-- prioridade só muda alguma coisa quando alguém escolhe uma prioridade
-- diferente de propósito.
-- -------------------------------------------------------------------------
alter table public.portal_jobs
  add column if not exists priority integer not null default 100;

-- Quando este job pode ser pego. Serve a duas coisas ao mesmo tempo: backoff de
-- retry (não repita antes de X) e justiça entre corretoras (um tenant que
-- acabou de ocupar o worker cede a vez). NULL = pode agora, que é o
-- comportamento de todos os jobs que já existem.
alter table public.portal_jobs
  add column if not exists available_at timestamptz;

-- -------------------------------------------------------------------------
-- 3. ÍNDICES
-- -------------------------------------------------------------------------

-- O índice que o novo laço de coleta usa. Parcial em `queued` pela mesma razão
-- que o `idx_portal_jobs_queued` original: a fila é uma fração minúscula da
-- tabela, e um índice sobre a tabela inteira paga por linhas que ninguém
-- consulta.
--
-- 🔴 O `idx_portal_jobs_queued` ANTIGO fica. Ele ainda serve ao caminho atual,
-- e derrubá-lo no mesmo commit que cria o substituto é o oposto de
-- expand-first: se o código novo voltar atrás, o índice velho precisa estar lá.
create index if not exists idx_portal_jobs_fila_prioridade
  on public.portal_jobs (priority asc, created_at asc)
  where status = 'queued';

-- Para responder "que jobs este Work Run gerou?" sem varrer a tabela.
create index if not exists idx_portal_jobs_work_run
  on public.portal_jobs (work_run_id)
  where work_run_id is not null;

-- Para a matriz de capacidade e o relatório por operação.
create index if not exists idx_portal_jobs_operacao
  on public.portal_jobs (company_id, operation_key, created_at desc)
  where operation_key is not null;

-- -------------------------------------------------------------------------
-- 4. DOCUMENTAÇÃO NA PRÓPRIA COLUNA
--
-- Quem abrir a tabela daqui a um ano não vai abrir esta migration junto.
-- -------------------------------------------------------------------------
comment on column public.portal_jobs.work_run_id is
  'SPEC-075: o Work Run que gerou este trabalho. NULL em jobs criados pelos '
  'caminhos legados (portal_tool, billing_collection) enquanto o cutover roda.';
comment on column public.portal_jobs.work_step_id is
  'SPEC-075: o passo do Work Run. NULL quando o chamador nao usa Work Run.';
comment on column public.portal_jobs.tool_invocation_id is
  'SPEC-075: a invocacao de tool que autorizou este trabalho. Sem FK de '
  'proposito: a DDL de tool_invocations nao esta rastreada no repositorio.';
comment on column public.portal_jobs.operation_key is
  'SPEC-075: a operacao de negocio (billing.overdue.list, '
  'assistance.glass.request). Texto, nao enum: o registro vive no codigo do '
  'portal-worker, que e um servico separado e desalinha de banco por desenho.';
comment on column public.portal_jobs.priority is
  'SPEC-075: menor = mais urgente, como nice(1). Default 100 preserva o '
  'comportamento FIFO atual para todo job que nao escolher outra coisa.';
comment on column public.portal_jobs.available_at is
  'SPEC-075: nao pegar antes deste instante. Backoff de retry e justica entre '
  'corretoras. NULL = pode agora.';

commit;

-- =============================================================
-- VERIFY — SQL executável. Roda depois do APPLY, read-only.
-- Espera-se: 6 linhas na primeira consulta, 3 na segunda, e a
-- terceira devolvendo 0 (nenhum job existente foi alterado).
-- =============================================================
-- as 6 colunas nasceram, e com o tipo certo
-- select column_name, data_type, is_nullable, column_default
--   from information_schema.columns
--  where table_schema = 'public' and table_name = 'portal_jobs'
--    and column_name in ('work_run_id','work_step_id','tool_invocation_id',
--                        'operation_key','priority','available_at')
--  order by column_name;
--
-- os 3 indices existem
-- select indexname from pg_indexes
--  where schemaname = 'public' and tablename = 'portal_jobs'
--    and indexname in ('idx_portal_jobs_fila_prioridade',
--                      'idx_portal_jobs_work_run',
--                      'idx_portal_jobs_operacao')
--  order by indexname;
--
-- 🔴 nenhum job existente saiu do lugar: todos com a prioridade default
-- select count(*) as jobs_com_prioridade_diferente_do_default
--   from public.portal_jobs where priority <> 100;
--
-- o indice antigo CONTINUA la (expand-first)
-- select 1 from pg_indexes
--  where schemaname='public' and tablename='portal_jobs'
--    and indexname='idx_portal_jobs_queued';

-- =============================================================
-- ROLLBACK
--
-- 🔴 A recomendação é NÃO rodar isto. Reverter o CÓDIGO
-- (`PORTAL_EXECUTION_GATEWAY_MODE=legacy`) já desliga o uso das colunas, e
-- coluna NULL-ável sem escritor não custa nada — nem espaço relevante, nem
-- desempenho. Derrubar coluna é destrutivo e apaga a linhagem de jobs que já
-- foram gravados com ela; se o código voltar depois, essa história não volta.
--
-- Se ainda assim for preciso, nesta ordem (índices antes das colunas):
--
-- drop index if exists public.idx_portal_jobs_operacao;
-- drop index if exists public.idx_portal_jobs_work_run;
-- drop index if exists public.idx_portal_jobs_fila_prioridade;
-- alter table public.portal_jobs drop column if exists available_at;
-- alter table public.portal_jobs drop column if exists priority;
-- alter table public.portal_jobs drop column if exists operation_key;
-- alter table public.portal_jobs drop column if exists tool_invocation_id;
-- alter table public.portal_jobs drop column if exists work_step_id;
-- alter table public.portal_jobs drop column if exists work_run_id;
-- =============================================================
