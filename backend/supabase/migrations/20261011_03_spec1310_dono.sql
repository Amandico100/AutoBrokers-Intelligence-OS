-- =============================================================
-- MIGRATION: 20261011_03_spec1310_dono
-- SPEC:      SPEC-131-0 parte A — F2 · o DONO da renovação (U2 vínculo produtor ↔ pessoa · regra do dono como dado)
-- AUTOR:     builder F2 (Opus 5.5)            DATA: 2026-10-11
-- OBJETIVO:  (1) `membro_produtores`: que código de produtor do sistema de gestão é de qual PESSOA da corretora.
--                O vínculo é `(user_id, company_id)` → `company_members` ON DELETE CASCADE (D-131-0-30): saiu da
--                equipe, o vínculo cai e a renovação dele vira "sem dono" — nunca de outra pessoa. O MESMO código não
--                pode ser de duas pessoas na mesma corretora (UNIQUE company_id, sistema, codfil, codigo_produtor); em
--                corretoras diferentes pode (cada uma tem o seu banco no sistema de gestão: 📊 o nosnum 91175 e o
--                cliente 3477 existem nos dois bancos medidos — BLOCO0-INFOCAP §2).
--            (2) `regras_de_dono`: a regra de quem é o dono, por corretora e sistema (D-131-0-31). Sem linha = vale o
--                padrão do sistema em `backend/app/data/providers/infocap/regra-de-dono-padrao.json`.
--                Lidas/escritas por `app/services/sistema_de_gestao/dono.py`, sempre com o filtro company_id (§7).
--
-- 📊 ANTES (11/10/2026, SELECT só leitura, psycopg com `set transaction read only`, backend/.env SUPABASE_DB_URL):
--    · select to_regclass('public.membro_produtores'), to_regclass('public.regras_de_dono') → (None, None)
--    · pg_constraint de company_members → company_members_user_id_company_id_key UNIQUE (user_id, company_id) — o
--      alvo da FK composta já existe; FKs user→users_v2 e company→companies, ambas ON DELETE CASCADE.
--    · select status, count(*) from company_members group by 1 → active 10 (3 corretoras client, 4 · 2 · 4 membros).
--
-- APPLY (pelo GERENTE — o builder NÃO aplica):
--   A. `public.membro_produtores` (create table if not exists) + CHECKs `ck_membro_produtores_sistema`,
--      `ck_membro_produtores_codigo`, `ck_membro_produtores_codfil` + UNIQUE `uq_membro_produtores_codigo` + FK composta
--      `fk_membro_produtores_membro` (user_id, company_id) → company_members ON DELETE CASCADE + índice da FK.
--      (Tabela NOVA e vazia: os CHECKs entram válidos — NOT VALID+VALIDATE é para tabela com linhas.)
--   B. `public.regras_de_dono` (create table if not exists; PK company_id, sistema) + CHECKs `ck_regras_de_dono_objeto`,
--      `ck_regras_de_dono_sistema`.
--   C. RLS ligada SEM policy + REVOKE ALL de anon e authenticated nas duas (molde 20261006_01_spec130a_config). COMMENTs.
--
-- VERIFY (read-only · esperado: 2 · 1 · 1 · 1 · 1 · 0 · 0 · 1 · 1 · 1):
--   select (select count(*) from pg_class where relnamespace='public'::regnamespace and relkind='r' and relrowsecurity
--             and relname in ('membro_produtores','regras_de_dono')) tabelas_com_rls,
--          (select count(*) from pg_constraint where conrelid='public.membro_produtores'::regclass
--             and conname='uq_membro_produtores_codigo'
--             and pg_get_constraintdef(oid)='UNIQUE (company_id, sistema, codfil, codigo_produtor)') unique_codigo,
--          (select count(*) from pg_constraint where conrelid='public.membro_produtores'::regclass
--             and conname='fk_membro_produtores_membro' and confdeltype='c'
--             and confrelid='public.company_members'::regclass) fk_membro_cascade,
--          (select count(*) from pg_constraint where conrelid='public.regras_de_dono'::regclass and contype='p'
--             and pg_get_constraintdef(oid)='PRIMARY KEY (company_id, sistema)') pk_regra,
--          (select count(*) from pg_constraint where conname='ck_regras_de_dono_objeto' and convalidated) check_objeto,
--          (select count(*) from pg_policies where tablename in ('membro_produtores','regras_de_dono')) policies,
--          (select count(*) from information_schema.role_table_grants where grantee in ('anon','authenticated')
--             and table_schema='public' and table_name in ('membro_produtores','regras_de_dono')) grants_publicos,
--          (select count(*) from pg_constraint where conname='ck_membro_produtores_sistema' and convalidated) ck_sistema,
--          (select count(*) from pg_constraint where conname='ck_membro_produtores_codigo' and convalidated) ck_codigo,
--          (select count(*) from pg_indexes where schemaname='public' and indexname='ix_membro_produtores_membro') idx_fk;
--
-- VERIFY comportamental (o DO desfaz o que testa — raise P0001 no fim do sub-bloco; NADA fica):
--   do $$
--   declare a uuid; b uuid; ua1 uuid; ua2 uuid; ub uuid; r text; res text[] := '{}';
--   begin
--     -- duas corretoras client com membros: A com DUAS pessoas, B com uma pessoa que NÃO é membro de A
--     select m.company_id into a from public.company_members m join public.companies c on c.id = m.company_id
--      where c.company_kind = 'client' group by m.company_id having count(*) >= 2 order by m.company_id limit 1;
--     select m.user_id into ua1 from public.company_members m where m.company_id = a order by m.user_id limit 1;
--     select m.user_id into ua2 from public.company_members m where m.company_id = a and m.user_id <> ua1
--      order by m.user_id limit 1;
--     select m.company_id, m.user_id into b, ub from public.company_members m join public.companies c on c.id = m.company_id
--      where c.company_kind = 'client' and m.company_id <> a
--        and not exists (select 1 from public.company_members x where x.company_id = a and x.user_id = m.user_id)
--      order by m.company_id, m.user_id limit 1;
--     if a is null or ua2 is null or b is null then
--       raise exception 'VERIFY 20261011_03: faltam duas corretoras client com membros (A com 2, B com 1 de fora de A)';
--     end if;
--     begin
--       insert into public.membro_produtores (company_id, user_id, sistema, codigo_produtor)
--         values (a, ua1, 'infocap', 'verify-999');
--       res := res || 'a_pessoa1=aceito'::text;
--       -- 🔴 o MESMO código para OUTRA pessoa da MESMA corretora → recusado
--       begin insert into public.membro_produtores (company_id, user_id, sistema, codigo_produtor)
--               values (a, ua2, 'infocap', 'verify-999'); r := 'aceito';
--       exception when unique_violation then r := 'recusado'; end;  res := res || ('a_pessoa2_mesmo_codigo='||r)::text;
--       -- o MESMO código em OUTRA corretora → aceito (bancos diferentes no sistema de gestão)
--       begin insert into public.membro_produtores (company_id, user_id, sistema, codigo_produtor)
--               values (b, ub, 'infocap', 'verify-999'); r := 'aceito';
--       exception when unique_violation then r := 'recusado'; end;  res := res || ('b_mesmo_codigo='||r)::text;
--       -- a pessoa da B vinculada na A (não é membro da A) → recusado pela FK composta
--       begin insert into public.membro_produtores (company_id, user_id, sistema, codigo_produtor)
--               values (a, ub, 'infocap', 'verify-998'); r := 'aceito';
--       exception when foreign_key_violation then r := 'recusado'; end;  res := res || ('pessoa_de_fora='||r)::text;
--       begin insert into public.membro_produtores (company_id, user_id, sistema, codigo_produtor)
--               values (a, ua1, 'sap', 'verify-997'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('sistema_estranho='||r)::text;
--       begin insert into public.membro_produtores (company_id, user_id, sistema, codigo_produtor)
--               values (a, ua1, 'infocap', '  '); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('codigo_vazio='||r)::text;
--       insert into public.regras_de_dono (company_id, sistema, regra) values (a, 'infocap', '{"campo":"indireto"}');
--       res := res || 'regra_objeto=aceito'::text;
--       begin insert into public.regras_de_dono (company_id, sistema, regra) values (a, 'infocap', '{}'); r := 'aceito';
--       exception when unique_violation then r := 'recusado'; end;  res := res || ('regra_segunda='||r)::text;
--       begin insert into public.regras_de_dono (company_id, sistema, regra) values (b, 'infocap', '[1]'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('regra_lista='||r)::text;
--       raise exception using errcode = 'P0001', message = 'desfaz';
--     exception when sqlstate 'P0001' then null;
--     end;
--     res := res || ('anon_le=' || has_table_privilege('anon','public.membro_produtores','select')::text)::text
--                || ('authenticated_escreve=' || has_table_privilege('authenticated','public.regras_de_dono','insert')::text)::text
--                || ('sobrou=' || ((select count(*) from public.membro_produtores where codigo_produtor like 'verify-%')
--                                  + (select count(*) from public.regras_de_dono where company_id in (a, b)
--                                     and regra = '{"campo":"indireto"}'::jsonb))::text)::text;
--     if res is distinct from array['a_pessoa1=aceito','a_pessoa2_mesmo_codigo=recusado','b_mesmo_codigo=aceito',
--                                   'pessoa_de_fora=recusado','sistema_estranho=recusado','codigo_vazio=recusado',
--                                   'regra_objeto=aceito','regra_segunda=recusado','regra_lista=recusado',
--                                   'anon_le=false','authenticated_escreve=false','sobrou=0'] then
--       raise exception 'VERIFY 20261011_03 FALHOU: %', res;
--     end if;
--     raise notice 'VERIFY 20261011_03 OK: %', res;
--   end $$;
--
-- ROLLBACK (🔴 executar é decisão do Founder — MIGRATIONS-AUTHORITY §8; RECUSA se houver vínculo ou regra gravados):
--   do $$ begin
--     if exists (select 1 from public.membro_produtores) or exists (select 1 from public.regras_de_dono) then
--       raise exception 'ROLLBACK 20261011_03 recusado: há vínculo ou regra de corretora — apagar dado é decisão do Founder';
--     end if;
--   end $$;
--   drop table if exists public.membro_produtores;
--   drop table if exists public.regras_de_dono;
--
-- EXPAND-FIRST: sim (duas tabelas novas; nada existente é alterado — a FK só LÊ company_members/companies/users_v2)
-- DESTRUTIVA:   não
-- IDEMPOTENTE:  sim (create table if not exists; constraints e índice só se ainda não existem)
-- LOCK:         a FK composta pega SHARE ROW EXCLUSIVE em company_members por instantes (tabela de 10 linhas)
-- ORDEM:        depois da 20261011_02 (membros) e antes do código da F2 ler as tabelas. Sem elas, `regra_de_dono` e
--               `membro_do_produtor` levantam erro de banco (fail-closed: nunca "sem dono" por tabela ausente).
-- =============================================================

-- A. o vínculo produtor ↔ pessoa ---------------------------------------------------------------------------------
create table if not exists public.membro_produtores (
  id               uuid primary key default gen_random_uuid(),
  company_id       uuid not null references public.companies(id) on delete cascade,
  user_id          uuid not null,
  sistema          text not null,
  codfil           integer not null default 1,
  codigo_produtor  text not null,
  nome_produtor    text null,
  papel_cru        text null,
  criado_por       uuid null references public.users_v2(id) on delete set null,
  criado_em        timestamptz not null default now()
);

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'ck_membro_produtores_sistema') then
    alter table public.membro_produtores
      add constraint ck_membro_produtores_sistema check (sistema in ('infocap', 'quiver', 'outro'));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_membro_produtores_codigo') then
    alter table public.membro_produtores
      add constraint ck_membro_produtores_codigo check (length(btrim(codigo_produtor)) > 0);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_membro_produtores_codfil') then
    alter table public.membro_produtores
      add constraint ck_membro_produtores_codfil check (codfil >= 1);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'uq_membro_produtores_codigo') then
    alter table public.membro_produtores
      add constraint uq_membro_produtores_codigo unique (company_id, sistema, codfil, codigo_produtor);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'fk_membro_produtores_membro') then
    alter table public.membro_produtores
      add constraint fk_membro_produtores_membro foreign key (user_id, company_id)
      references public.company_members (user_id, company_id) on delete cascade;
  end if;
end $$;

-- o lado de cá da FK composta (o CASCADE de company_members procura por ele)
create index if not exists ix_membro_produtores_membro on public.membro_produtores (user_id, company_id);

-- B. a regra do dono -----------------------------------------------------------------------------------------------
create table if not exists public.regras_de_dono (
  company_id     uuid not null references public.companies(id) on delete cascade,
  sistema        text not null,
  regra          jsonb not null,
  atualizado_por uuid null references public.users_v2(id) on delete set null,
  atualizado_em  timestamptz not null default now(),
  primary key (company_id, sistema)
);

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'ck_regras_de_dono_objeto') then
    alter table public.regras_de_dono
      add constraint ck_regras_de_dono_objeto check (jsonb_typeof(regra) = 'object');
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_regras_de_dono_sistema') then
    alter table public.regras_de_dono
      add constraint ck_regras_de_dono_sistema check (sistema in ('infocap', 'quiver', 'outro'));
  end if;
end $$;

-- C. RLS ligada SEM policy + REVOKE: o backend (service_role) é o único leitor; o filtro company_id mora no código.
alter table public.membro_produtores enable row level security;
alter table public.regras_de_dono enable row level security;
revoke all on table public.membro_produtores from anon, authenticated;
revoke all on table public.regras_de_dono from anon, authenticated;

comment on table public.membro_produtores is
  'SPEC-131-0 F2 (D-131-0-30) — que código de produtor do sistema de gestão é de qual PESSOA da corretora. '
  'FK (user_id, company_id) → company_members ON DELETE CASCADE: saiu da equipe, o vínculo cai. Lido por '
  'app/services/sistema_de_gestao/dono.py (membro_do_produtor), sempre filtrando company_id.';
comment on column public.membro_produtores.codigo_produtor is
  'o código do produtor como o sistema de gestão o devolve (InfoCap: `codpro` do /prod_docs avulso), normalizado sem zeros à esquerda';
comment on column public.membro_produtores.papel_cru is
  'o papel ESCRITO no nome do produtor (FECHADOR, INDICADORA…) — procedência, nunca decide o dono nem vínculo trabalhista';
comment on table public.regras_de_dono is
  'SPEC-131-0 F2 (D-131-0-31) — a regra de quem é o DONO de uma apólice, por corretora e sistema. Sem linha = vale '
  'o padrão do sistema (backend/app/data/providers/<sistema>/regra-de-dono-padrao.json). RLS sem policy.';
