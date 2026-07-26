-- =============================================================
-- MIGRATION: indices_read_models_061
-- SPEC:      Bloco 0 da SPEC-061 §19
-- AUTOR:     Executor Opus                DATA: 2026-07-27
-- OBJETIVO:  os quatro indices que faltavam para o padrao de leitura do
--            Cockpit da SPEC-061: "o que aconteceu nesta corretora,
--            do mais recente para o mais antigo".
--
-- APPLY:     4x create index if not exists.
-- VERIFY:    ver bloco VERIFY ao final.
-- ROLLBACK:  4x drop index (nomes exatos).
--
-- EXPAND-FIRST: sim — indice nao altera dado.
-- DESTRUTIVA:   nao
--
-- POR QUE ESTES QUATRO E NAO UMA VARREDURA
-- ----------------------------------------
-- §19 pede o oposto de "criar indice ate o advisor calar". O levantamento
-- cruzou as consultas que a SPEC-061 vai fazer com os indices existentes:
--
--   work_runs         (company_id, status)              JA EXISTIA
--   work_steps        (work_run_id)                     JA EXISTIA
--   work_attempts     (work_step_id)                    JA EXISTIA
--   tool_invocations  (work_run_id)                     JA EXISTIA
--   artifacts         (company_id, created_at)          JA EXISTIA
--   research_*        (company_id / monitor_id)         JA EXISTIA
--
-- Faltavam exatamente os quatro abaixo, e todos com a mesma forma:
-- **filtra por corretora, ordena por tempo decrescente**. Nenhum outro indice
-- foi criado.
--
-- HONESTIDADE SOBRE O GANHO
-- -------------------------
-- Hoje `tool_invocations`, `usage_events` e `work_attempts` estao com zero
-- linhas (foi o que este Bloco 0 encontrou e corrigiu). Com tabela vazia, o
-- plano usa Seq Scan de qualquer jeito e medir "antes e depois" produziria um
-- numero sem significado.
--
-- Estes indices existem para o volume que vem, e sao criados AGORA porque com
-- a tabela vazia o custo de criacao e desprezivel — criar depois, com milhoes
-- de linhas e o Admin em uso, exigiria CONCURRENTLY e uma janela.
--
-- O impacto na escrita e o de sempre: um indice a mais por INSERT. Nas quatro
-- tabelas o INSERT ja acontece dentro de trabalho assincrono, nunca no caminho
-- da resposta ao corretor.
-- =============================================================

-- "Ultimos trabalhos desta corretora" — a primeira tela do Cockpit.
create index if not exists ix_work_runs_company_recente
  on public.work_runs (company_id, created_at desc);

-- "Onde este trabalho falhou e quantas vezes tentou" — o diagnostico.
create index if not exists ix_work_attempts_company_status
  on public.work_attempts (company_id, status, created_at desc);

-- "Quais ferramentas esta corretora usou, e quais falharam."
create index if not exists ix_tool_invocations_company_recente
  on public.tool_invocations (company_id, created_at desc);

-- "Quanto esta corretora consumiu no periodo" — base de custo e billing.
create index if not exists ix_usage_events_company_recente
  on public.usage_events (company_id, created_at desc);

-- =============================================================
-- VERIFY
-- =============================================================
-- select tablename, indexname from pg_indexes
--  where schemaname='public'
--    and indexname in ('ix_work_runs_company_recente',
--                      'ix_work_attempts_company_status',
--                      'ix_tool_invocations_company_recente',
--                      'ix_usage_events_company_recente')
--  order by 1;
--   -- esperado: 4 linhas
--
-- -- E o plano precisa passar a usa-los quando houver volume:
-- explain (costs off)
--   select * from public.work_runs
--    where company_id = '...'::uuid order by created_at desc limit 20;
--   -- esperado com volume: Index Scan using ix_work_runs_company_recente
--   -- esperado hoje (43 linhas): Seq Scan — e correto, a tabela cabe numa pagina
--
-- =============================================================
-- ROLLBACK
-- =============================================================
-- drop index if exists public.ix_work_runs_company_recente;
-- drop index if exists public.ix_work_attempts_company_status;
-- drop index if exists public.ix_tool_invocations_company_recente;
-- drop index if exists public.ix_usage_events_company_recente;
-- =============================================================
