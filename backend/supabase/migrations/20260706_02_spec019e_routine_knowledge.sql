-- SPEC-019 E — Conhecimento por rotina (routines.knowledge) — EXPAND-ONLY.
-- Conteudo injetado no prompt de execucao (### CONHECIMENTO DA ROTINA): argumentos
-- de venda, FAQ do produto, tom de voz do outreach. Rotinas complexas usam isso.
--
-- APPLY:   SQL Editor do Supabase (idempotente).
-- VERIFY:  select column_name from information_schema.columns
--          where table_name = 'routines' and column_name = 'knowledge';
-- ROLLBACK: alter table public.routines drop column if exists knowledge;

alter table public.routines add column if not exists knowledge text;

comment on column public.routines.knowledge is
  'SPEC-019 E: conhecimento injetado no prompt de execucao (render_task_prompt) antes das instrucoes.';
