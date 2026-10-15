-- =============================================================
-- MIGRATION: 20261015_01_spec1310b2_linha_do_usuario
-- SPEC:      SPEC-131-0-B2 — L1 · a linha com dono (o WhatsApp do PRÓPRIO corretor conectado ao AutoBrokers)
-- AUTOR:     builder L1 (Opus 5.5)            DATA: 2026-10-15
-- OBJETIVO:  uma instância do Evolution GO por PESSOA: `integrations` ganha o DONO (`owner_user_id`) e o estado da
--            linha (jid/lid, conectada/desconectada, motivo, descartadas); o banco garante UMA linha ativa por pessoa e
--            UM número por linha ativa; nascem o anti-eco durável (`linha_mensagens_do_sistema`) e o registro dos avisos
--            ("teria enviado" — `linha_avisos_registro`).
--
-- 📊 ANTES (15/10/2026, leitura READ-ONLY do catálogo do banco vivo pelo builder — `SET TRANSACTION READ ONLY`):
--    · integrations: 25 colunas; `purpose text not null default 'attendance'`, `is_active boolean null default true`,
--      `paired_phone_e164 text`, `paired_jid text`; NENHUM CHECK (só pkey, fkeys agent/company, UNIQUE(provider,identifier));
--      RLS ligada com a policy "Users can manage own company integrations"; nenhuma FK de outra tabela aponta para ela.
--      📊 select purpose, is_active, count(*) from integrations group by 1,2 → attendance/false 4 · observer/true 4
--      (ZERO linhas 'linha_do_usuario' → o CHECK e os únicos parciais nascem sem conflito).
--    · company_members.user_id → FK `company_members_user_id_fkey` REFERENCES users_v2(id) ON DELETE CASCADE;
--      UNIQUE `company_members_user_id_company_id_key` (user_id, company_id) — a FK composta abaixo aponta para ele.
--    · server_version 17.6 · nenhuma tabela `linha%` existe.
--
-- PRÉ (o GERENTE roda ANTES do APPLY · esperado: 0 · 0 · 0):
--   select (select count(*) from public.integrations where purpose = 'linha_do_usuario') linhas_ja_existentes,
--          (select count(*) from pg_constraint where conrelid='public.integrations'::regclass and contype='c'
--             and pg_get_constraintdef(oid) ilike '%purpose%') checks_de_purpose,
--          (select count(*) from pg_tables where schemaname='public'
--             and tablename in ('linha_mensagens_do_sistema','linha_avisos_registro')) tabelas_ja_existentes;
--
-- APPLY (pelo GERENTE — o builder NÃO aplica; `set lock_timeout = '5s'` na MESMA transação, nunca SET SESSION):
--   A. integrations + owner_user_id uuid null · linha_jid text · linha_lid text · linha_conectada_em timestamptz ·
--      linha_desconectada_em timestamptz · linha_motivo text · descartadas_total bigint not null default 0
--      (default constante: só metadado no PG ≥ 11, sem reescrever a tabela).
--   B. FK owner_user_id → users_v2(id) ON DELETE CASCADE (a pessoa apagada leva a linha DELA; a sessão no provedor é
--      solta pelo Desconectar, não pelo banco) · FK COMPOSTA (owner_user_id, company_id) → company_members(user_id,
--      company_id) ON DELETE CASCADE: o dono TEM de ser membro da corretora da linha (MATCH SIMPLE: owner nulo — todos os
--      outros purposes — não é conferido). As duas NOT VALID → VALIDATE.
--   C. CHECK ck_integrations_linha_tem_dono: purpose='linha_do_usuario' ⇒ owner_user_id not null (NOT VALID → VALIDATE)
--      · CHECK ck_integrations_linha_motivo (slug curto) · CHECK ck_integrations_descartadas_nao_negativo.
--   D. únicos parciais: uq_integrations_linha_por_dono (owner_user_id) e uq_integrations_linha_por_numero
--      (paired_phone_e164) WHERE purpose='linha_do_usuario' AND is_active IS TRUE (o 2º com número só quando não nulo).
--      📊 tabela de 8 linhas → índice comum (sem CONCURRENTLY), instantâneo.
--   E. linha_mensagens_do_sistema (id, integration_id → integrations ON DELETE CASCADE, company_id → companies ON DELETE
--      CASCADE, message_id, hash_texto sha256-hex, enviada_em) — o anti-eco DURÁVEL (P-132C-02; D-1310B2-04) · único
--      (integration_id, message_id) quando há id · índice (integration_id, hash_texto, enviada_em) · índice (enviada_em)
--      para a limpeza > 7 dias (P-132C-04, job da L4). Nunca o texto: só o hash.
--   F. linha_avisos_registro (id, company_id, user_id, tipo, criado_em, enviado, motivo_nao_enviado) — o "teria enviado"
--      dos avisos desligados (D-132F-04); nunca o texto · FK composta (user_id, company_id) → company_members CASCADE ·
--      CHECK tipo slug · CHECK enviado OU motivo · índice (company_id, user_id, criado_em).
--   G. E e F: RLS LIGADA, SEM policy, REVOKE ALL de anon/authenticated (só o backend — service role — lê; o filtro
--      company_id está no código, CLAUDE.md §7). COMMENTs.
--
-- VERIFY (read-only · esperado: 7 · 2 · 3 · 2 · 2 · 2 · 0 · 0 · 0):
--   select (select count(*) from information_schema.columns where table_schema='public' and table_name='integrations'
--             and column_name in ('owner_user_id','linha_jid','linha_lid','linha_conectada_em','linha_desconectada_em',
--                                 'linha_motivo','descartadas_total')) colunas,
--          (select count(*) from pg_constraint where conrelid='public.integrations'::regclass and convalidated
--             and conname in ('fk_integrations_owner_user','fk_integrations_owner_membro')) fks_validadas,
--          (select count(*) from pg_constraint where conrelid='public.integrations'::regclass and convalidated
--             and conname in ('ck_integrations_linha_tem_dono','ck_integrations_linha_motivo',
--                             'ck_integrations_descartadas_nao_negativo')) checks_validados,
--          (select count(*) from pg_indexes where schemaname='public'
--             and indexname in ('uq_integrations_linha_por_dono','uq_integrations_linha_por_numero')) unicos_parciais,
--          (select count(*) from pg_class where relnamespace='public'::regnamespace and relkind='r' and relrowsecurity
--             and relname in ('linha_mensagens_do_sistema','linha_avisos_registro')) tabelas_com_rls,
--          (select count(*) from pg_indexes where schemaname='public'
--             and indexname in ('uq_linha_mensagens_do_sistema_id','ix_linha_mensagens_do_sistema_hash')) indices_anti_eco,
--          (select count(*) from pg_policies where schemaname='public'
--             and tablename in ('linha_mensagens_do_sistema','linha_avisos_registro')) policies,
--          (select count(*) from information_schema.role_table_grants where table_schema='public'
--             and table_name in ('linha_mensagens_do_sistema','linha_avisos_registro')
--             and grantee in ('anon','authenticated')) grants_publicos,
--          (select count(*) from public.integrations where purpose <> 'linha_do_usuario'
--             and owner_user_id is not null) outros_purposes_com_dono;
--
-- VERIFY comportamental (o DO desfaz o que testa — raise P0001 no fim do sub-bloco; NADA fica):
--   do $$
--   declare m1 record; m2 record; outra uuid; res text[] := '{}';
--   begin
--     select company_id, user_id into m1 from public.company_members where status='active' order by created_at limit 1;
--     select company_id, user_id into m2 from public.company_members
--      where status='active' and company_id=m1.company_id and user_id<>m1.user_id order by created_at limit 1;
--     select id into outra from public.companies where id <> m1.company_id order by created_at limit 1;
--     if m1.user_id is null or m2.user_id is null or outra is null then
--       raise exception 'VERIFY 20261015_01: falta corretora com 2 membros, ou uma 2ª corretora'; end if;
--     begin
--       begin insert into public.integrations (company_id, provider, identifier, token, instance_id, purpose, is_active)
--               values (m1.company_id, 'evolution-go', 'verify-lu-sem-dono', 'x', 'verify-lu-sem-dono', 'linha_do_usuario', true);
--             res := res || 'linha_sem_dono=ACEITA'::text;
--       exception when check_violation then res := res || 'linha_sem_dono=recusada'::text; end;
--       insert into public.integrations (company_id, provider, identifier, token, instance_id, purpose, is_active,
--                                        owner_user_id, paired_phone_e164)
--         values (m1.company_id, 'evolution-go', 'verify-lu-1', 'x', 'verify-lu-1', 'linha_do_usuario', true,
--                 m1.user_id, '+5511900000001');
--       begin insert into public.integrations (company_id, provider, identifier, token, instance_id, purpose, is_active,
--                                              owner_user_id)
--               values (m1.company_id, 'evolution-go', 'verify-lu-2', 'x', 'verify-lu-2', 'linha_do_usuario', true, m1.user_id);
--             res := res || 'duas_ativas_mesmo_dono=ACEITAS'::text;
--       exception when unique_violation then res := res || 'duas_ativas_mesmo_dono=recusadas'::text; end;
--       begin insert into public.integrations (company_id, provider, identifier, token, instance_id, purpose, is_active,
--                                              owner_user_id, paired_phone_e164)
--               values (m2.company_id, 'evolution-go', 'verify-lu-3', 'x', 'verify-lu-3', 'linha_do_usuario', true,
--                       m2.user_id, '+5511900000001');
--             res := res || 'mesmo_numero_2_linhas=ACEITO'::text;
--       exception when unique_violation then res := res || 'mesmo_numero_2_linhas=recusado'::text; end;
--       begin insert into public.integrations (company_id, provider, identifier, token, instance_id, purpose, is_active,
--                                              owner_user_id)
--               values (outra, 'evolution-go', 'verify-lu-4', 'x', 'verify-lu-4', 'linha_do_usuario', false, m2.user_id);
--             res := res || 'dono_de_fora_da_corretora=ACEITO'::text;
--       exception when foreign_key_violation then res := res || 'dono_de_fora_da_corretora=recusado'::text; end;
--       begin insert into public.linha_mensagens_do_sistema (integration_id, company_id, message_id, hash_texto)
--               select id, company_id, 'm1', 'texto em claro' from public.integrations where identifier='verify-lu-1';
--             res := res || 'anti_eco_texto_em_claro=ACEITO'::text;
--       exception when check_violation then res := res || 'anti_eco_texto_em_claro=recusado'::text; end;
--       raise exception 'DESFAZ %', array_to_string(res, ' · ') using errcode = 'P0001';
--     exception when sqlstate 'P0001' then raise notice '%', sqlerrm;
--     end;
--   end $$;
--   → esperado no NOTICE: DESFAZ linha_sem_dono=recusada · duas_ativas_mesmo_dono=recusadas
--                         · mesmo_numero_2_linhas=recusado · dono_de_fora_da_corretora=recusado
--                         · anti_eco_texto_em_claro=recusado
--   (se m2.user_id for membro da `outra` corretora o 4º item pode dar ACEITO — escolha outra corretora/membro e reexecute)
--
-- ROLLBACK (escrito ANTES; só com a L2/L3 fora do ar — sem elas nada lê estas peças; nenhuma linha de outro purpose usa
-- as colunas novas):
--   drop table if exists public.linha_avisos_registro;
--   drop table if exists public.linha_mensagens_do_sistema;
--   drop index if exists public.uq_integrations_linha_por_numero;
--   drop index if exists public.uq_integrations_linha_por_dono;
--   alter table public.integrations drop constraint if exists ck_integrations_descartadas_nao_negativo;
--   alter table public.integrations drop constraint if exists ck_integrations_linha_motivo;
--   alter table public.integrations drop constraint if exists ck_integrations_linha_tem_dono;
--   alter table public.integrations drop constraint if exists fk_integrations_owner_membro;
--   alter table public.integrations drop constraint if exists fk_integrations_owner_user;
--   delete from public.integrations where purpose = 'linha_do_usuario';   -- ⚠️ só se já houver linhas: perde os pareamentos
--   alter table public.integrations drop column if exists descartadas_total, drop column if exists linha_motivo,
--     drop column if exists linha_desconectada_em, drop column if exists linha_conectada_em,
--     drop column if exists linha_lid, drop column if exists linha_jid, drop column if exists owner_user_id;
--   ⚠️ o ROLLBACK apaga o estado das linhas (quem conectou conecta de novo pelo QR); nenhum dado de outro purpose se perde.
--
-- EXPAND-FIRST: sim
-- DESTRUTIVA:   não
-- =============================================================

-- A. as colunas da linha do usuário -------------------------------------------------------------------------------
alter table public.integrations add column if not exists owner_user_id uuid null;
alter table public.integrations add column if not exists linha_jid text null;
alter table public.integrations add column if not exists linha_lid text null;
alter table public.integrations add column if not exists linha_conectada_em timestamptz null;
alter table public.integrations add column if not exists linha_desconectada_em timestamptz null;
alter table public.integrations add column if not exists linha_motivo text null;
alter table public.integrations add column if not exists descartadas_total bigint not null default 0;

-- B. o dono existe e é membro da corretora da linha ------------------------------------------------------------------
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'fk_integrations_owner_user') then
    alter table public.integrations add constraint fk_integrations_owner_user
      foreign key (owner_user_id) references public.users_v2 (id) on delete cascade not valid;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'fk_integrations_owner_membro') then
    alter table public.integrations add constraint fk_integrations_owner_membro
      foreign key (owner_user_id, company_id) references public.company_members (user_id, company_id)
      on delete cascade not valid;
  end if;
end $$;
alter table public.integrations validate constraint fk_integrations_owner_user;
alter table public.integrations validate constraint fk_integrations_owner_membro;

-- C. a linha do usuário NUNCA sem dono · o motivo é um slug · o contador não fica negativo ----------------------------
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'ck_integrations_linha_tem_dono') then
    alter table public.integrations add constraint ck_integrations_linha_tem_dono
      check (purpose <> 'linha_do_usuario' or owner_user_id is not null) not valid;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_integrations_linha_motivo') then
    alter table public.integrations add constraint ck_integrations_linha_motivo
      check (linha_motivo is null or linha_motivo ~ '^[a-z0-9_]{1,64}$') not valid;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_integrations_descartadas_nao_negativo') then
    alter table public.integrations add constraint ck_integrations_descartadas_nao_negativo
      check (descartadas_total >= 0) not valid;
  end if;
end $$;
alter table public.integrations validate constraint ck_integrations_linha_tem_dono;
alter table public.integrations validate constraint ck_integrations_linha_motivo;
alter table public.integrations validate constraint ck_integrations_descartadas_nao_negativo;

-- D. UMA linha ativa por pessoa · UM número por linha ativa ----------------------------------------------------------
create unique index if not exists uq_integrations_linha_por_dono
  on public.integrations (owner_user_id)
  where purpose = 'linha_do_usuario' and is_active is true;
create unique index if not exists uq_integrations_linha_por_numero
  on public.integrations (paired_phone_e164)
  where purpose = 'linha_do_usuario' and is_active is true and paired_phone_e164 is not null;

comment on column public.integrations.owner_user_id is
  'SPEC-131-0-B2 (D-1310B2-01): o DONO da linha do usuário (purpose=linha_do_usuario) — uma instância do Evolution GO '
  'por PESSOA, pareada no Meu perfil. Nulo para todos os outros purposes. O dono é membro da corretora da linha '
  '(fk_integrations_owner_membro).';
comment on column public.integrations.linha_jid is
  'SPEC-131-0-B2: o JID (@s.whatsapp.net) da própria conta da linha — "a conversa consigo mesmo" é casada por ele e/ou pelo LID.';
comment on column public.integrations.linha_lid is
  'SPEC-131-0-B2: o LID (@lid) da própria conta, quando o provedor o manda. Opaco: nunca se deduz telefone dele.';
comment on column public.integrations.linha_conectada_em is
  'SPEC-131-0-B2: quando a linha CONECTOU (a transição para conectada) — o "desde" da tela.';
comment on column public.integrations.linha_desconectada_em is
  'SPEC-131-0-B2: quando a linha caiu ou a pessoa desconectou — o "desde" da faixa de desconexão. Nada é apagado.';
comment on column public.integrations.linha_motivo is
  'SPEC-131-0-B2: por que a linha caiu (slug: desconectada_pelo_usuario, cancelada_pelo_usuario, loggedout, ...).';
comment on column public.integrations.descartadas_total is
  'SPEC-131-0-B2 (D-1310B2-05): quantas mensagens de OUTRAS conversas (grupo, status, broadcast, history sync, contatos) '
  'foram DESCARTADAS na entrada, sem gravar, logar nem chamar modelo. Só a contagem — nunca o conteúdo.';

-- E. o anti-eco durável (id + hash; nunca o texto) -------------------------------------------------------------------
create table if not exists public.linha_mensagens_do_sistema (
  id              uuid primary key default gen_random_uuid(),
  integration_id  uuid not null references public.integrations(id) on delete cascade,
  company_id      uuid not null references public.companies(id) on delete cascade,
  message_id      text null,
  hash_texto      text not null,
  enviada_em      timestamptz not null default now()
);

do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'ck_linha_mensagens_do_sistema_hash') then
    alter table public.linha_mensagens_do_sistema add constraint ck_linha_mensagens_do_sistema_hash
      check (hash_texto ~ '^[0-9a-f]{64}$');
  end if;
end $$;
create unique index if not exists uq_linha_mensagens_do_sistema_id
  on public.linha_mensagens_do_sistema (integration_id, message_id)
  where message_id is not null;
create index if not exists ix_linha_mensagens_do_sistema_hash
  on public.linha_mensagens_do_sistema (integration_id, hash_texto, enviada_em);
create index if not exists ix_linha_mensagens_do_sistema_limpeza
  on public.linha_mensagens_do_sistema (enviada_em);

-- F. o registro dos avisos ("teria enviado"; nunca o texto) ----------------------------------------------------------
create table if not exists public.linha_avisos_registro (
  id                  uuid primary key default gen_random_uuid(),
  company_id          uuid not null references public.companies(id) on delete cascade,
  user_id             uuid not null,
  tipo                text not null,
  criado_em           timestamptz not null default now(),
  enviado             boolean not null default false,
  motivo_nao_enviado  text null
);

do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'fk_linha_avisos_registro_membro') then
    alter table public.linha_avisos_registro add constraint fk_linha_avisos_registro_membro
      foreign key (user_id, company_id) references public.company_members (user_id, company_id) on delete cascade;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_linha_avisos_registro_tipo') then
    alter table public.linha_avisos_registro add constraint ck_linha_avisos_registro_tipo
      check (tipo ~ '^[a-z0-9_]{1,64}$');
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_linha_avisos_registro_motivo') then
    alter table public.linha_avisos_registro add constraint ck_linha_avisos_registro_motivo
      check (enviado or motivo_nao_enviado is not null);
  end if;
end $$;
create index if not exists ix_linha_avisos_registro_membro
  on public.linha_avisos_registro (company_id, user_id, criado_em);

-- G. só o backend lê ---------------------------------------------------------------------------------------------------
alter table public.linha_mensagens_do_sistema enable row level security;
alter table public.linha_avisos_registro enable row level security;
revoke all on public.linha_mensagens_do_sistema from anon, authenticated;
revoke all on public.linha_avisos_registro from anon, authenticated;

comment on table public.linha_mensagens_do_sistema is
  'SPEC-131-0-B2 (D-1310B2-04, P-132C-02): o que o AutoBrokers MANDOU pela linha do usuário — o id da mensagem e o '
  'SHA-256 do texto (nunca o texto), para a resposta do sistema não voltar como pergunta (anti-eco durável). Limpeza '
  '> 7 dias no job da L4 (P-132C-04). RLS sem policy: só o backend (service role), filtrando company_id no código.';
comment on table public.linha_avisos_registro is
  'SPEC-131-0-B2 (D-132F-04, D-1310B2-06): cada aviso do sistema pelo WhatsApp que SAIRIA para a pessoa — enviado ou '
  'não (com o motivo: ex. avisos_desligados = "teria enviado"). Nunca o texto. RLS sem policy: só o backend.';
