-- =============================================================
-- MIGRATION: company_internal_numbers
-- SPEC:      SPEC-EXTRA-001.3 — BLOCO B
-- AUTOR:     executor Opus 5 (AAA FAST)      DATA: 2026-09-16
-- OBJETIVO:  os números da própria corretora, com dono e rótulo
--
-- APPLY:     cria a tabela, o índice único por (company_id, phone) e a RLS
-- VERIFY:    SQL read-only no fim deste arquivo
-- ROLLBACK:  drop table if exists public.company_internal_numbers;
--            (seguro: a tabela nasce nesta SPEC e o leitor do JSONB
--             `integrations.alert_target.internal_numbers` continua vivo)
--
-- EXPAND-FIRST: sim — `alert_target.internal_numbers` CONTINUA existindo e
--               continua sendo lido por `atlas/attendance_capture.py:109-117`;
--               o leitor novo entra NA FRENTE. A chave velha só é aposentada
--               numa SPEC futura, com backfill e prova.
-- DESTRUTIVA:   não
--
-- BACKFILL: 📊 16/09/2026 — nenhum. Medido antes de escrever:
--   select count(*) from integrations
--    where jsonb_array_length(coalesce(alert_target->'internal_numbers','[]'::jsonb)) > 0;
--   -> 0
-- =============================================================

create table if not exists public.company_internal_numbers (
  id           uuid primary key default gen_random_uuid(),
  company_id   uuid not null references public.companies(id) on delete cascade,
  phone        text not null,
  label        text not null,
  kind         text not null default 'outro'
               check (kind in ('fixo','comercial','socio','membro','outro')),
  created_by   uuid null references public.users_v2(id) on delete set null,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- 🔴 `unique (company_id, phone)` e NÃO `unique (phone)`: duas corretoras
-- diferentes podem ter o mesmo fixo de prédio, e o número de uma NUNCA cala a
-- outra (CLAUDE.md §7 · guarda G-B2).
create unique index if not exists ux_company_internal_numbers_company_phone
  on public.company_internal_numbers (company_id, phone);

alter table public.company_internal_numbers enable row level security;

-- ⚠️ O backend usa service role: a policy não protege contra erro de filtro no
-- código (CLAUDE.md §7). Ela existe para o acesso anon/authenticated, e a
-- proteção REAL é o `.eq("company_id", ...)` no repositório.
do $$
begin
  if not exists (select 1 from pg_policies
                  where schemaname='public' and tablename='company_internal_numbers'
                    and policyname='company_internal_numbers_por_corretora') then
    create policy company_internal_numbers_por_corretora
      on public.company_internal_numbers
      for all
      using (company_id in (select company_id from public.company_members
                             where user_id = auth.uid()))
      with check (company_id in (select company_id from public.company_members
                                  where user_id = auth.uid()));
  end if;
end $$;

comment on table public.company_internal_numbers is
  'SPEC-EXTRA-001.3 BLOCO B — números da própria corretora que o agente nunca '
  'atende, nunca põe na Fila e sobre os quais nunca fala no grupo.';

-- =============================================================
-- VERIFY (read-only)
-- =============================================================
-- select count(*) = 1 as tabela_existe
--   from information_schema.tables
--  where table_schema='public' and table_name='company_internal_numbers';
--
-- select count(*) = 1 as unique_por_corretora
--   from pg_indexes
--  where schemaname='public' and tablename='company_internal_numbers'
--    and indexdef ilike '%UNIQUE%(company_id, phone)%';
--
-- select relrowsecurity as rls_ligada
--   from pg_class where relname='company_internal_numbers';
