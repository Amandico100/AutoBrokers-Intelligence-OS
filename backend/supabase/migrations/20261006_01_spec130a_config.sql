-- =============================================================
-- MIGRATION: 20261006_01_spec130a_config
-- SPEC:      SPEC-130-A — U2 A configuração comercial do multicálculo (F1)
-- AUTOR:     builder F1 (Opus 5.5)            DATA: 2026-10-06
-- OBJETIVO:  uma linha por corretora com a config COMERCIAL dela (comissão, alvo, validade, lembretes, pesos da nota,
--            textos), mesclada sobre `PADRAO_DO_PRODUTO` por `app/services/multicalculo/config.py:carregar`.
--            Sem linha = o padrão do produto (D-MC-62…72: "tudo como CONFIGURAÇÃO, nunca constante espalhada").
--
-- 📊 ANTES: nenhuma tabela `multicalculo_config` (nasce nesta SPEC). Molde de segurança: 20261005_01_spec129b_motor
--    (RLS ligada SEM policy + REVOKE de anon/authenticated — só o backend, com service role, lê e escreve, SEMPRE com
--    o filtro company_id no código: `config.carregar`, CLAUDE.md §7). Decisão do gerente da 130-A (06/10).
--
-- APPLY:  (1) `public.multicalculo_config` (company_id PK → companies ON DELETE CASCADE, config jsonb objeto,
--             atualizado_em, atualizado_por → users_v2 ON DELETE SET NULL) — `create table if not exists`.
--         (2) CHECK `ck_mc_config_objeto` (config é objeto JSON) — só se ainda não existe.
--         (3) RLS ligada, NENHUMA policy, REVOKE ALL de anon e authenticated. COMMENTs. Idempotente.
--
-- VERIFY (read-only · esperado: 1 · 1 · 1 · 0 · 0 · 1 · 4):
--   select (select count(*) from pg_class where relnamespace='public'::regnamespace and relname='multicalculo_config'
--             and relkind='r' and relrowsecurity) tabela_com_rls,
--          (select count(*) from pg_constraint where conname='ck_mc_config_objeto') check_objeto,
--          (select count(*) from pg_constraint where conrelid='public.multicalculo_config'::regclass and contype='p'
--             and pg_get_constraintdef(oid) = 'PRIMARY KEY (company_id)') pk_company,
--          (select count(*) from pg_policies where tablename='multicalculo_config') policies,
--          (select count(*) from information_schema.role_table_grants where grantee in ('anon','authenticated')
--             and table_schema='public' and table_name='multicalculo_config') grants_publicos,
--          (select count(*) from pg_description where objoid='public.multicalculo_config'::regclass and objsubid=0)
--            comentario,
--          (select count(*) from information_schema.columns where table_schema='public'
--             and table_name='multicalculo_config'
--             and column_name in ('company_id','config','atualizado_em','atualizado_por')) colunas;
--
-- VERIFY comportamental (o DO desfaz o que testa — raise P0001 no fim do sub-bloco; nada fica):
--   do $$
--   declare a uuid; r text; res text[] := '{}';
--   begin
--     select id into a from public.companies where company_kind='client' order by created_at limit 1;
--     if a is null then raise exception 'VERIFY 20261006_01: falta uma corretora cliente'; end if;
--     begin
--       insert into public.multicalculo_config (company_id, config) values (a, '{"comissao":{"piso":11}}');
--       res := res || 'objeto=aceito'::text;
--       begin insert into public.multicalculo_config (company_id, config) values (a, '{}'); r := 'aceito';
--       exception when unique_violation then r := 'recusado'; end;  res := res || ('segunda_linha='||r)::text;
--       begin update public.multicalculo_config set config='[1,2]' where company_id=a; r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('lista='||r)::text;
--       begin insert into public.multicalculo_config (company_id, config)
--               values ('00000000-0000-4000-8000-000000000000', '{}'); r := 'aceito';
--       exception when foreign_key_violation then r := 'recusado'; end;  res := res || ('sem_empresa='||r)::text;
--       raise exception using errcode='P0001', message='desfaz';
--     exception when sqlstate 'P0001' then null;
--     end;
--     res := res || ('anon_le=' || has_table_privilege('anon','public.multicalculo_config','select')::text)::text
--                || ('authenticated_escreve=' || has_table_privilege('authenticated','public.multicalculo_config','insert')::text)::text;
--     if res is distinct from array['objeto=aceito','segunda_linha=recusado','lista=recusado','sem_empresa=recusado',
--                                   'anon_le=false','authenticated_escreve=false'] then
--       raise exception 'VERIFY 20261006_01 FALHOU: %', res;
--     end if;
--     raise notice 'VERIFY 20261006_01 OK: %', res;
--   end $$;
--
-- ROLLBACK (🔴 executar é decisão do Founder — MIGRATIONS-AUTHORITY §8.6; RECUSA se houver config gravada):
--   do $$ begin
--     if exists (select 1 from public.multicalculo_config) then
--       raise exception 'ROLLBACK 20261006_01 recusado: há config de corretora — apagar dado é decisão do Founder';
--     end if;
--   end $$;
--   drop table if exists public.multicalculo_config;
--
-- EXPAND-FIRST: sim (tabela nova; nada existente é alterado)
-- DESTRUTIVA:   não
-- LOCK:         nenhum em tabela existente (a FK só lê `companies`/`users_v2`)
-- ORDEM:        ANTES do código da 130-A ler a config (sem a tabela, `carregar` levanta `ConfigIndisponivel` —
--               fail-closed; nunca o padrão às cegas)
-- =============================================================

create table if not exists public.multicalculo_config (
  company_id      uuid primary key references public.companies(id) on delete cascade,
  config          jsonb not null default '{}'::jsonb,
  atualizado_em   timestamptz not null default now(),
  atualizado_por  uuid null references public.users_v2(id) on delete set null
);

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'ck_mc_config_objeto') then
    alter table public.multicalculo_config
      add constraint ck_mc_config_objeto check (jsonb_typeof(config) = 'object');
  end if;
end $$;

-- RLS ligada SEM policy + REVOKE: o backend (service_role) é o único leitor; o filtro company_id mora no código.
alter table public.multicalculo_config enable row level security;
revoke all on table public.multicalculo_config from anon, authenticated;

comment on table public.multicalculo_config is
  'SPEC-130-A U2 — a config COMERCIAL do multicálculo por corretora (comissão, alvo, validade, lembretes, pesos da '
  'nota, textos), mesclada sobre PADRAO_DO_PRODUTO em app/services/multicalculo/config.py. Sem linha = o padrão. '
  'RLS sem policy: só o backend (service role) lê, sempre filtrando company_id.';
comment on column public.multicalculo_config.config is
  'Só as chaves que PADRAO_DO_PRODUTO conhece entram; valor de tipo errado ou régua incoerente é ignorado (vale o padrão).';
comment on column public.multicalculo_config.atualizado_por is
  'quem gravou (users_v2); nulo quando a escrita veio de um processo do produto';
