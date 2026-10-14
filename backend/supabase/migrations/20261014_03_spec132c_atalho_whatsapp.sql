-- =============================================================
-- MIGRATION: 20261014_03_spec132c_atalho_whatsapp
-- SPEC:      SPEC-132-C — C1 · a verificação (o WhatsApp do corretor como atalho do chat)
-- AUTOR:     builder C1 (Opus 5.5)            DATA: 2026-10-14
-- OBJETIVO:  o "Meu WhatsApp de trabalho" passa a poder ser VERIFICADO POR POSSE (D-132C-02): a pessoa manda, do
--            celular dela, "ATIVAR <código>" ao número do AutoBrokers; o código (só o HASH) mora numa tabela nova, de
--            uso único, 15 min; o número verificado vira identidade (um número ↔ um membro por corretora).
--
-- 📊 ANTES (14/10/2026, leitura do REPOSITÓRIO — o builder não tem banco; o gerente confere o banco vivo com o PRÉ abaixo):
--    · company_members: whatsapp_trabalho_e164 + whatsapp_trabalho_confirmado_em (20261014_01 §E, CHECK E.164 BR);
--      UNIQUE (user_id, company_id) (20260721_01:25) — a FK composta abaixo aponta para ele, como `membro_ausencias`.
--    · integrations.purpose: `text not null default 'attendance'` (20260703_02); NENHUM CHECK no repositório
--      (`grep -rln purpose backend/supabase/migrations supabase/migrations` → 3 arquivos, nenhum com CHECK).
--
-- PRÉ (o GERENTE roda ANTES do APPLY · esperado: 0 linhas):
--   select conname, pg_get_constraintdef(oid) from pg_constraint
--    where conrelid='public.integrations'::regclass and contype='c' and pg_get_constraintdef(oid) ilike '%purpose%';
--   ⚠️ >0 linhas = existe um CHECK de purpose que o repositório não conhece: o bloco D abaixo PARA a migration (raise)
--      em vez de chutar a lista; escreva o CHECK novo (a lista de hoje + 'assistente') numa migration própria.
--
-- APPLY (pelo GERENTE — o builder NÃO aplica; um arquivo, idempotente, expand-only):
--   A. company_members + `whatsapp_trabalho_verificado_em timestamptz null` + CHECK (só com número) NOT VALID → VALIDATE.
--   B. índice ÚNICO parcial `uq_company_members_whatsapp_verificado` (company_id, whatsapp_trabalho_e164) WHERE
--      verificado_em is not null — o MESMO número verificado em dois membros da MESMA corretora é recusado pelo banco.
--      📊 a coluna nasce nula em todas as linhas → o índice nasce sem conflito.
--   C. tabela `whatsapp_atalho_codigos` (id, company_id, user_id, codigo_hash, expira_em, usado_em, invalidado_em,
--      tentativas, criado_em) · FK (user_id, company_id) → company_members ON DELETE CASCADE · CHECKs (hash sha256 hex,
--      expira depois de criar, tentativas ≥ 0) · índice ÚNICO parcial: UM código ATIVO (não usado, não invalidado) por
--      membro · índice do hash (o consumo procura por ele) · índice (company_id, user_id, criado_em) (o teto por hora).
--      Tabela `whatsapp_atalho_tentativas` (id, telefone_hash, criado_em) — o teto de tentativas ERRADAS por número
--      (💭 5/hora): só o HMAC do telefone e a hora, NENHUM conteúdo e nenhum telefone em claro (D-132C-03).
--      As duas: RLS LIGADA, SEM policy, REVOKE de anon/authenticated (o backend usa service role; o filtro company_id
--      está no código — CLAUDE.md §7). COMMENTs.
--   D. integrations.purpose: se existir CHECK que fale de purpose e não admita 'assistente' → RAISE (não se chuta a
--      lista). Sem CHECK (o esperado) → nada a fazer: 'assistente' já é aceito. COMMENT da coluna atualizado.
--
-- VERIFY (read-only · esperado: 1 · 1 · 1 · 2 · 2 · 2 · 0 · 0):
--   select (select count(*) from information_schema.columns where table_schema='public' and table_name='company_members'
--             and column_name='whatsapp_trabalho_verificado_em') col_verificado,
--          (select count(*) from pg_constraint where conrelid='public.company_members'::regclass and convalidated
--             and conname='ck_company_members_whatsapp_verificado') check_verificado,
--          (select count(*) from pg_indexes where schemaname='public' and indexname='uq_company_members_whatsapp_verificado') uq_numero,
--          (select count(*) from pg_class where relnamespace='public'::regnamespace and relkind='r' and relrowsecurity
--             and relname in ('whatsapp_atalho_codigos','whatsapp_atalho_tentativas')) tabelas_com_rls,
--          (select count(*) from pg_indexes where schemaname='public'
--             and indexname in ('uq_whatsapp_atalho_codigo_ativo','ix_whatsapp_atalho_codigos_hash')) indices_codigos,
--          (select count(*) from pg_constraint where conrelid='public.whatsapp_atalho_codigos'::regclass
--             and conname in ('fk_whatsapp_atalho_codigos_membro','ck_whatsapp_atalho_codigos_hash')) fk_e_check,
--          (select count(*) from pg_policies where schemaname='public'
--             and tablename in ('whatsapp_atalho_codigos','whatsapp_atalho_tentativas')) policies,
--          (select count(*) from information_schema.role_table_grants where table_schema='public'
--             and table_name in ('whatsapp_atalho_codigos','whatsapp_atalho_tentativas')
--             and grantee in ('anon','authenticated')) grants_publicos;
--
-- VERIFY comportamental (o DO desfaz o que testa — raise P0001 no fim do sub-bloco; NADA fica):
--   do $$
--   declare m1 record; m2 record; res text[] := '{}';
--   begin
--     select company_id, user_id into m1 from public.company_members where status='active' order by created_at limit 1;
--     select company_id, user_id into m2 from public.company_members
--      where status='active' and company_id=m1.company_id and user_id<>m1.user_id order by created_at limit 1;
--     if m1.user_id is null or m2.user_id is null then raise exception 'VERIFY 20261014_03: falta corretora com 2 membros'; end if;
--     begin
--       begin update public.company_members set whatsapp_trabalho_verificado_em=now(), whatsapp_trabalho_e164=null,
--                    whatsapp_trabalho_confirmado_em=null
--              where company_id=m1.company_id and user_id=m1.user_id;
--             res := res || 'verificado_sem_numero=ACEITO'::text;
--       exception when check_violation then res := res || 'verificado_sem_numero=recusado'::text; end;
--       update public.company_members set whatsapp_trabalho_e164='+5511987654321', whatsapp_trabalho_verificado_em=now()
--        where company_id=m1.company_id and user_id=m1.user_id;
--       begin update public.company_members set whatsapp_trabalho_e164='+5511987654321', whatsapp_trabalho_verificado_em=now()
--              where company_id=m2.company_id and user_id=m2.user_id;
--             res := res || 'mesmo_numero_2_membros=ACEITO'::text;
--       exception when unique_violation then res := res || 'mesmo_numero_2_membros=recusado'::text; end;
--       insert into public.whatsapp_atalho_codigos (company_id, user_id, codigo_hash, expira_em)
--         values (m1.company_id, m1.user_id, repeat('a',64), now() + interval '15 minutes');
--       begin insert into public.whatsapp_atalho_codigos (company_id, user_id, codigo_hash, expira_em)
--               values (m1.company_id, m1.user_id, repeat('b',64), now() + interval '15 minutes');
--             res := res || 'dois_ativos=ACEITO'::text;
--       exception when unique_violation then res := res || 'dois_ativos=recusado'::text; end;
--       begin insert into public.whatsapp_atalho_codigos (company_id, user_id, codigo_hash, expira_em)
--               values (m2.company_id, m2.user_id, '123456', now() + interval '15 minutes');   -- m2: sem ativo
--             res := res || 'codigo_em_claro=ACEITO'::text;
--       exception when check_violation then res := res || 'codigo_em_claro=recusado'::text; end;
--       raise exception 'DESFAZ %', array_to_string(res, ' · ') using errcode = 'P0001';
--     exception when sqlstate 'P0001' then raise notice '%', sqlerrm;
--     end;
--   end $$;
--   → esperado no NOTICE: DESFAZ verificado_sem_numero=recusado · mesmo_numero_2_membros=recusado · dois_ativos=recusado
--                         · codigo_em_claro=recusado
--
-- ROLLBACK (escrito ANTES; só se a C2 ainda não estiver no ar — sem ela nada lê estas peças):
--   drop table if exists public.whatsapp_atalho_tentativas;
--   drop table if exists public.whatsapp_atalho_codigos;
--   drop index if exists public.uq_company_members_whatsapp_verificado;
--   alter table public.company_members drop constraint if exists ck_company_members_whatsapp_verificado;
--   alter table public.company_members drop column if exists whatsapp_trabalho_verificado_em;
--   ⚠️ o ROLLBACK apaga as verificações feitas: quem verificou precisa verificar de novo (nenhum outro dado se perde).
--
-- EXPAND-FIRST: sim
-- DESTRUTIVA:   não
-- =============================================================

-- A. a coluna da verificação por posse --------------------------------------------------------------------------------
alter table public.company_members add column if not exists whatsapp_trabalho_verificado_em timestamptz null;

do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'ck_company_members_whatsapp_verificado') then
    alter table public.company_members add constraint ck_company_members_whatsapp_verificado
      check (whatsapp_trabalho_verificado_em is null or whatsapp_trabalho_e164 is not null) not valid;
  end if;
end $$;
alter table public.company_members validate constraint ck_company_members_whatsapp_verificado;

comment on column public.company_members.whatsapp_trabalho_verificado_em is
  'SPEC-132-C (D-132C-02): quando a pessoa PROVOU a posse do número mandando "ATIVAR <código>" do próprio celular ao '
  'número do AutoBrokers. Só o número VERIFICADO vira identidade no WhatsApp (o atalho do chat). Trocar o número no '
  'Meu perfil zera este campo. Nulo = não verificado (o "Quero renovar" continua usando o confirmado_em).';

-- B. um número verificado ↔ um membro, por corretora ------------------------------------------------------------------
create unique index if not exists uq_company_members_whatsapp_verificado
  on public.company_members (company_id, whatsapp_trabalho_e164)
  where whatsapp_trabalho_verificado_em is not null;

-- C. os códigos (só o hash) e o teto de tentativas erradas -----------------------------------------------------------
create table if not exists public.whatsapp_atalho_codigos (
  id             uuid primary key default gen_random_uuid(),
  company_id     uuid not null references public.companies(id) on delete cascade,
  user_id        uuid not null,
  codigo_hash    text not null,
  expira_em      timestamptz not null,
  usado_em       timestamptz null,
  invalidado_em  timestamptz null,
  tentativas     integer not null default 0,
  criado_em      timestamptz not null default now()
);

do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'fk_whatsapp_atalho_codigos_membro') then
    alter table public.whatsapp_atalho_codigos add constraint fk_whatsapp_atalho_codigos_membro
      foreign key (user_id, company_id) references public.company_members (user_id, company_id) on delete cascade;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_whatsapp_atalho_codigos_hash') then
    -- o código em claro (6 dígitos) NUNCA cabe aqui: só o HMAC-SHA256 em hexadecimal
    alter table public.whatsapp_atalho_codigos add constraint ck_whatsapp_atalho_codigos_hash
      check (codigo_hash ~ '^[0-9a-f]{64}$');
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_whatsapp_atalho_codigos_validade') then
    alter table public.whatsapp_atalho_codigos add constraint ck_whatsapp_atalho_codigos_validade
      check (expira_em > criado_em);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_whatsapp_atalho_codigos_tentativas') then
    alter table public.whatsapp_atalho_codigos add constraint ck_whatsapp_atalho_codigos_tentativas
      check (tentativas >= 0);
  end if;
end $$;

create unique index if not exists uq_whatsapp_atalho_codigo_ativo
  on public.whatsapp_atalho_codigos (company_id, user_id)
  where usado_em is null and invalidado_em is null;
create index if not exists ix_whatsapp_atalho_codigos_hash
  on public.whatsapp_atalho_codigos (codigo_hash)
  where usado_em is null and invalidado_em is null;
create index if not exists ix_whatsapp_atalho_codigos_membro_hora
  on public.whatsapp_atalho_codigos (company_id, user_id, criado_em);

create table if not exists public.whatsapp_atalho_tentativas (
  id             uuid primary key default gen_random_uuid(),
  telefone_hash  text not null,
  criado_em      timestamptz not null default now()
);

do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'ck_whatsapp_atalho_tentativas_hash') then
    alter table public.whatsapp_atalho_tentativas add constraint ck_whatsapp_atalho_tentativas_hash
      check (telefone_hash ~ '^[0-9a-f]{64}$');
  end if;
end $$;
create index if not exists ix_whatsapp_atalho_tentativas_hora
  on public.whatsapp_atalho_tentativas (telefone_hash, criado_em);

alter table public.whatsapp_atalho_codigos enable row level security;
alter table public.whatsapp_atalho_tentativas enable row level security;
revoke all on public.whatsapp_atalho_codigos from anon, authenticated;
revoke all on public.whatsapp_atalho_tentativas from anon, authenticated;

comment on table public.whatsapp_atalho_codigos is
  'SPEC-132-C (D-132C-02): o código de 6 dígitos que a pessoa manda do PRÓPRIO celular ("ATIVAR <código>") ao número '
  'do AutoBrokers. Só o HMAC-SHA256 (nunca o código em claro), 15 min, uso único, um ativo por membro. RLS sem policy: '
  'só o backend (service role) lê, sempre filtrando company_id no código (app/services/atalho/verificacao.py).';
comment on column public.whatsapp_atalho_codigos.invalidado_em is
  'SPEC-132-C: o membro pediu um código novo antes de usar este — este deixa de valer (não é uso).';
comment on column public.whatsapp_atalho_codigos.tentativas is
  'SPEC-132-C: quantas vezes este código casou e a ativação foi RECUSADA (ex.: o número já é de outra pessoa).';
comment on table public.whatsapp_atalho_tentativas is
  'SPEC-132-C (D-132C-03): uma linha por "ATIVAR" ERRADO — só o HMAC do telefone e a hora (teto por número; '
  'acima dele, silêncio). Nenhum conteúdo de mensagem, nenhum telefone em claro.';

-- D. integrations.purpose aceita 'assistente' --------------------------------------------------------------------------
do $$
declare d text;
begin
  for d in select pg_get_constraintdef(oid) from pg_constraint
            where conrelid = 'public.integrations'::regclass and contype = 'c'
              and pg_get_constraintdef(oid) ilike '%purpose%'
  loop
    if d not ilike '%assistente%' then
      raise exception 'SPEC-132-C: integrations tem um CHECK de purpose que não admite ''assistente'' (%). '
                      'Escreva o CHECK novo (a lista de hoje + ''assistente'') numa migration própria.', d;
    end if;
  end loop;
end $$;

comment on column public.integrations.purpose is
  'SPEC-017 S17-12: attendance | auxiliary:<slug> | dispatch | observer — número dedicado por função. '
  'SPEC-132-C: assistente = o número da PLATAFORMA "AutoBrokers" com que os corretores conversam (empresa '
  'company_kind=platform_canal); a identidade é o whatsapp_trabalho VERIFICADO do membro.';
