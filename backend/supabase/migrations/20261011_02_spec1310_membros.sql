-- =============================================================
-- MIGRATION: 20261011_02_spec1310_membros
-- SPEC:      SPEC-131-0 parte A — F1 · membros (D-131-0-14: funções + papel fechado + uma fonte do papel)
-- AUTOR:     builder da F1 (Opus 5.5)                              DATA: 2026-10-11
-- OBJETIVO:  (1) `company_members.funcoes text[]` — o que a pessoa FAZ na corretora (comercial · calculista ·
--            negociador), separado do papel de ACESSO; lista fechada por CHECK. As funções NÃO dão acesso a nada:
--            quem decide acesso continua sendo só `role`/`is_owner` (lib/admin/admin-auth-policy.ts).
--            (2) o papel de ACESSO fica FECHADO: CHECK `role IN ('owner','admin_company','member','attendant')`.
--            A mesma lista mora em `lib/admin/admin-auth-policy.ts` (`PAPEIS_DE_ACESSO`, `FUNCOES_DE_TRABALHO`) e o
--            teste `scripts/spec1310-membros.test.mjs` compara as duas — uma fonte, duas cópias vigiadas.
--
-- 📊 ANTES (11/10/2026, SELECT só leitura por psycopg em `set session characteristics as transaction read only`,
--    script scratchpad/f1_q.py):
--    · `select role, count(*) from company_members group by 1` → admin_company 8 · member 2 (nenhum outro valor:
--      o VALIDATE passa)
--    · `select status, count(*) ...` → active 10
--    · colunas: id, user_id, company_id, role varchar(40) NOT NULL default 'member', is_owner, status, created_at
--    · constraints: PK, UNIQUE (user_id, company_id), FK user_id→users_v2 CASCADE, FK company_id→companies CASCADE —
--      NENHUM CHECK em `role`
--    · funções do banco que citam company_members (`position('company_members' in pg_get_functiondef(oid))>0`): 0 ·
--      gatilhos em company_members: 0
--
-- 🔴 OS ESCRITORES DE `company_members` (prova de que nenhum grava outro papel —
--    `git grep -n -i company_members -- '*.ts' '*.tsx' '*.py' '*.sql' | grep -iE "insert|upsert|update|delete"`):
--    · app/api/dashboard/team/route.ts — POST upsert / PATCH update / DELETE: o papel só entra se estiver em
--      `PAPEIS_QUE_A_EQUIPE_DA` (admin_company · member · attendant), senão 400. ⊂ CHECK.
--    · 20260721_01_spec047_rls_e_company_members.sql:31 — o seed (copiou `users_v2.role`, que tem o CHECK
--      `users_v2_role_check` IN (admin_company, member)); já aplicado, não roda de novo. ⊂ CHECK.
--    · nenhum escritor em backend/, scripts/ ou função do banco.
--    `owner` entra na lista fechada porque `TENANT_WRITE_ROLES` o reconhece (o dono de verdade é `is_owner`).
--
-- APPLY (pelo GERENTE — o builder NÃO aplica):
--   A. ADD COLUMN IF NOT EXISTS funcoes text[] NOT NULL DEFAULT '{}' (o default vira metadado: nenhuma linha é
--      reescrita; as 10 linhas leem '{}').
--   B. CHECK ck_company_members_funcoes (funcoes <@ ARRAY['comercial','calculista','negociador']) NOT VALID + VALIDATE.
--   C. CHECK ck_company_members_role (role IN ('owner','admin_company','member','attendant')) NOT VALID + VALIDATE.
--   D. COMMENT nas duas colunas.
--
-- VERIFY (read-only):
--   select (select count(*) from information_schema.columns
--            where table_schema = 'public' and table_name = 'company_members' and column_name = 'funcoes'
--              and data_type = 'ARRAY' and udt_name = '_text' and is_nullable = 'NO') as coluna_funcoes,
--          (select count(*) from pg_constraint
--            where conrelid = 'public.company_members'::regclass
--              and conname in ('ck_company_members_funcoes', 'ck_company_members_role') and convalidated) as checks_validados,
--          (select count(*) from public.company_members where funcoes <> '{}') as com_funcao,
--          (select count(*) from public.company_members
--            where role not in ('owner', 'admin_company', 'member', 'attendant')) as papel_fora_da_lista;
--   -- esperado logo após o APPLY: 1 · 2 · 0 · 0
--   -- 🔴 a TRAVA consegue recusar (CLAUDE.md §9.3): as definições REAIS dos dois checks, copiadas do catálogo para uma
--   --    tabela temporária — papel inventado, papel 'admin' (que a política antiga conhece) e função inventada são
--   --    recusados; os válidos passam; nada fica gravado (on commit drop).
--   do $$
--   declare d_role text; d_func text; recusas int := 0;
--   begin
--     select pg_get_constraintdef(oid) into d_role from pg_constraint
--      where conrelid = 'public.company_members'::regclass and conname = 'ck_company_members_role';
--     select pg_get_constraintdef(oid) into d_func from pg_constraint
--      where conrelid = 'public.company_members'::regclass and conname = 'ck_company_members_funcoes';
--     if d_role is null or d_func is null then raise exception 'VERIFY 20261011_02 FALHOU: check ausente'; end if;
--     create temp table verify_1310_membros (role varchar(40) not null, funcoes text[] not null default '{}') on commit drop;
--     execute 'alter table verify_1310_membros add constraint ck_r ' || d_role;
--     execute 'alter table verify_1310_membros add constraint ck_f ' || d_func;
--     insert into verify_1310_membros values ('owner', '{}'), ('admin_company', '{comercial}'), ('member', '{calculista,negociador}'),
--                                            ('attendant', '{comercial,calculista,negociador}');
--     begin insert into verify_1310_membros values ('gerente_geral', '{}'); exception when check_violation then recusas := recusas + 1; end;
--     begin insert into verify_1310_membros values ('admin', '{}');         exception when check_violation then recusas := recusas + 1; end;
--     begin insert into verify_1310_membros values ('member', '{vendedor}'); exception when check_violation then recusas := recusas + 1; end;
--     begin insert into verify_1310_membros values ('member', '{comercial,vendedor}'); exception when check_violation then recusas := recusas + 1; end;
--     begin insert into verify_1310_membros values ('member', array[null]::text[]); exception when check_violation then recusas := recusas + 1; end;
--     if recusas <> 5 then raise exception 'VERIFY 20261011_02 FALHOU: % recusas (esperado 5)', recusas; end if;
--     raise notice 'VERIFY 20261011_02 OK: papel inventado, admin, função inventada (só e misturada) e nula recusados; 4 válidos aceitos';
--   end $$;
--
-- ROLLBACK (só se nenhum código depender de `funcoes`; a rota da equipe lê a coluna e a tela a mostra):
--   alter table public.company_members drop constraint if exists ck_company_members_role;
--   alter table public.company_members drop constraint if exists ck_company_members_funcoes;
--   alter table public.company_members drop column if exists funcoes;   -- ⚠️ perde as funções já marcadas
--
-- EXPAND-FIRST: sim (acrescenta coluna e travas; nada é removido nem reescrito)
-- DESTRUTIVA:   não (o CHECK do papel muda QUEM PODE ser gravado: piso CRÍTICO, §3.2 — por isso o 📊 acima)
-- IDEMPOTENTE:  sim (IF NOT EXISTS / checagem no catálogo; VALIDATE de check já validado é inócuo)
-- =============================================================

begin;

-- A. as funções de trabalho
alter table public.company_members add column if not exists funcoes text[] not null default '{}';

-- B. a lista fechada das funções
do $$
begin
  if not exists (select 1 from pg_constraint
                  where conrelid = 'public.company_members'::regclass and conname = 'ck_company_members_funcoes') then
    alter table public.company_members
      add constraint ck_company_members_funcoes
      check (funcoes <@ array['comercial', 'calculista', 'negociador']::text[]) not valid;
  end if;
end $$;

alter table public.company_members validate constraint ck_company_members_funcoes;

-- C. o papel de acesso fechado
do $$
begin
  if not exists (select 1 from pg_constraint
                  where conrelid = 'public.company_members'::regclass and conname = 'ck_company_members_role') then
    alter table public.company_members
      add constraint ck_company_members_role
      check (role in ('owner', 'admin_company', 'member', 'attendant')) not valid;
  end if;
end $$;

alter table public.company_members validate constraint ck_company_members_role;

-- D. o que cada coluna quer dizer
comment on column public.company_members.funcoes is
  'SPEC-131-0 A (D-131-0-14): o que a pessoa FAZ nesta corretora — comercial (tem carteira e Agger próprio), '
  'calculista (monta cálculos, não fala com cliente), negociador (conversa com o cliente). NÃO dá acesso: '
  'acesso é só role/is_owner. Lista fechada = lib/admin/admin-auth-policy.ts FUNCOES_DE_TRABALHO.';
comment on column public.company_members.role is
  'Papel de ACESSO nesta corretora — a ÚNICA fonte do papel (SPEC-131-0 A; users_v2.role é espelho legado). '
  'Lista fechada = lib/admin/admin-auth-policy.ts PAPEIS_DE_ACESSO.';

commit;
