-- SPEC-017 S17-13 — Handoff com claim: quem da corretora assumiu a conversa.
-- EXPAND-ONLY em public.conversations (zero impacto no fluxo atual).
--
-- APPLY:   executar no SQL Editor do Supabase (idempotente).
-- VERIFY:  select column_name from information_schema.columns
--            where table_name='conversations' and column_name like 'claimed%';
-- ROLLBACK: alter table public.conversations
--            drop column if exists claimed_by,
--            drop column if exists claimed_by_name,
--            drop column if exists claimed_at;

alter table public.conversations
  add column if not exists claimed_by uuid,
  add column if not exists claimed_by_name text,
  add column if not exists claimed_at timestamptz;

comment on column public.conversations.claimed_by is
  'users_v2.id de quem assumiu o atendimento (claim). NULL = ninguém (bot ou fila).';
