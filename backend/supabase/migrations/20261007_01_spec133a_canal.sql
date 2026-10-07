-- =============================================================
-- MIGRATION: 20261007_01_spec133a_canal
-- SPEC:      SPEC-133-A — U2 convidados, limite, consentimento, lead e estado do CANAL (F1 · a porta de entrada)
-- AUTOR:     builder F1 (Opus 5.5)            DATA: 2026-10-07
-- OBJETIVO:  as 4 tabelas do canal de cotação ao consumidor (D-133A-04): quem pode falar com o canal (piloto FECHADO),
--            o consentimento (D-133A-05, histórico append-only), o lead por telefone e o ESTADO da conversa CIFRADO
--            (`portal_vault.encrypt`, o MESMO cofre do `pedido_cifrado` — nenhuma cifra nova) com os contadores do dia
--            (cotações e mensagens nossas: o limite e o teto anti-laço, D-133A-06).
--
-- 📊 ANTES (07/10/2026, psycopg `set transaction read only`):
--    · `select table_name from information_schema.tables where table_schema='public' and table_name like 'canal%'`
--      → 0 linhas (nenhuma tabela do canal).
--    · `select count(*) from companies where company_kind='platform_canal'` → 1 (a empresa técnica da 129-B).
--    · `select conname, pg_get_constraintdef(oid) from pg_constraint where conrelid='public.multicalculo_pedidos'::regclass
--       and contype in ('u','p')` → `uq_multicalculo_pedidos_id_company UNIQUE (id, company_id)` → a FK do lead é
--      COMPOSTA (pedido, company_id): um lead do canal nunca aponta para pedido de outra empresa.
--    · `leads` (0 linhas, `email NOT NULL` + UNIQUE por e-mail) e `invites` (convite de USUÁRIO) não servem a telefone
--      (BLOCO 0 §6) → tabelas próprias (nota 80 × evoluir `leads` 65).
--    Molde de segurança: 20261005_01 / 20261006_01 (RLS ligada SEM policy + REVOKE de anon/authenticated; só o backend,
--    com service role, lê e escreve, SEMPRE com o filtro company_id no código: `app/services/canal/repositorio.py`).
--
-- APPLY:  (1) `canal_convidados` (company_id, telefone E.164 só dígitos, apelido?, ativo, limite_dia?) UNIQUE (company_id, telefone)
--         (2) `canal_consentimentos` (company_id, telefone, aceito, versao_do_texto, registrado_em) — append-only
--         (3) `canal_leads` (company_id, telefone, primeiro_nome?, pedido_id? → FK COMPOSTA em multicalculo_pedidos)
--             UNIQUE (company_id, telefone)
--         (4) `canal_conversas` (company_id, telefone, estado_cifrado?, contadores do dia, aviso_limite_dia?)
--             UNIQUE (company_id, telefone)
--         CHECK de telefone (`^[1-9][0-9]{9,14}$`) e de tamanhos; índice do consentimento por (company_id, telefone,
--         registrado_em desc). RLS ligada, NENHUMA policy, REVOKE ALL de anon e authenticated. COMMENTs. Idempotente.
--
-- VERIFY (read-only · esperado: 4 · 0 · 0 · 3 · 1 · 4 · 4):
--   select (select count(*) from pg_class where relnamespace='public'::regnamespace and relkind='r' and relrowsecurity
--             and relname in ('canal_convidados','canal_consentimentos','canal_leads','canal_conversas')) tabelas_com_rls,
--          (select count(*) from pg_policies where tablename like 'canal\_%') policies,
--          (select count(*) from information_schema.role_table_grants where grantee in ('anon','authenticated')
--             and table_schema='public' and table_name like 'canal\_%') grants_publicos,
--          (select count(*) from pg_constraint where conname in ('uq_canal_convidados_tel','uq_canal_leads_tel',
--             'uq_canal_conversas_tel')) uniques_por_telefone,
--          (select count(*) from pg_constraint where conname='fk_canal_leads_pedido' and array_length(conkey,1)=2) fk_composta,
--          (select count(*) from pg_constraint where conname like 'ck\_canal\_%\_tel') checks_de_telefone,
--          (select count(*) from pg_description where objsubid=0 and objoid in ('public.canal_convidados'::regclass,
--             'public.canal_consentimentos'::regclass,'public.canal_leads'::regclass,'public.canal_conversas'::regclass)) comentarios;
--
-- VERIFY comportamental (o DO desfaz o que testa — raise P0001 no fim do sub-bloco; nada fica). DOIS tenants + CONTROLE:
--   do $$
--   declare canal uuid; b uuid; p uuid; r text; n int; res text[] := '{}';
--   begin
--     select id into canal from public.companies where company_kind='platform_canal' order by created_at limit 1;
--     select id into b from public.companies where company_kind='client' order by created_at limit 1;
--     if canal is null or b is null then raise exception 'VERIFY 20261007_01: faltam o canal ou uma corretora'; end if;
--     begin
--       insert into public.canal_convidados (company_id, telefone, apelido) values (canal, '5500900000001', 'verify');
--       res := res || 'convidado=aceito'::text;                                            -- CONTROLE: a forma certa entra
--       begin insert into public.canal_convidados (company_id, telefone) values (canal, '5500900000001'); r := 'aceito';
--       exception when unique_violation then r := 'recusado'; end;  res := res || ('mesmo_tel='||r)::text;
--       begin insert into public.canal_convidados (company_id, telefone) values (b, '5500900000001'); r := 'aceito';
--       exception when others then r := 'recusado:'||sqlstate; end;  res := res || ('mesmo_tel_outra_empresa='||r)::text;
--       select count(*) into n from public.canal_convidados where company_id=canal and telefone='5500900000001';
--       res := res || ('o_canal_le_so_o_dele='||n)::text;                                   -- 2 tenants: 1, nunca 2
--       begin insert into public.canal_convidados (company_id, telefone) values (canal, '+55 (00) 9000-0002'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('tel_formatado='||r)::text;
--       begin insert into public.canal_consentimentos (company_id, telefone, aceito, versao_do_texto)
--               values (canal, '5500900000001', true, 'v1'), (canal, '5500900000001', false, 'v1'); r := 'aceito';
--       exception when others then r := 'recusado:'||sqlstate; end;  res := res || ('consentimento_historico='||r)::text;
--       insert into public.multicalculo_pedidos (company_id, origem, opcoes, corretoras, pedido_cifrado)
--         values (b, 'auxiliar', array['padrao'], array[b], 'x') returning id into p;
--       begin insert into public.canal_leads (company_id, telefone, pedido_id) values (canal, '5500900000001', p); r := 'aceito';
--       exception when foreign_key_violation then r := 'recusado'; end;  res := res || ('lead_com_pedido_de_outra='||r)::text;
--       begin insert into public.canal_conversas (company_id, telefone, cotacoes_no_dia) values (canal, '5500900000001', -1);
--               r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('contador_negativo='||r)::text;
--       raise exception using errcode='P0001', message='desfaz';
--     exception when sqlstate 'P0001' then null;
--     end;
--     res := res || ('anon_le=' || has_table_privilege('anon','public.canal_conversas','select')::text)::text
--                || ('authenticated_escreve=' || has_table_privilege('authenticated','public.canal_convidados','insert')::text)::text;
--     if res is distinct from array['convidado=aceito','mesmo_tel=recusado','mesmo_tel_outra_empresa=aceito',
--                                   'o_canal_le_so_o_dele=1','tel_formatado=recusado','consentimento_historico=aceito',
--                                   'lead_com_pedido_de_outra=recusado','contador_negativo=recusado',
--                                   'anon_le=false','authenticated_escreve=false'] then
--       raise exception 'VERIFY 20261007_01 FALHOU: %', res;
--     end if;
--     raise notice 'VERIFY 20261007_01 OK: %', res;
--   end $$;
--
-- ROLLBACK (🔴 executar é decisão do Founder — MIGRATIONS-AUTHORITY §8.6; RECUSA se houver dado do canal):
--   do $$ begin
--     if exists (select 1 from public.canal_convidados) or exists (select 1 from public.canal_consentimentos)
--        or exists (select 1 from public.canal_leads) or exists (select 1 from public.canal_conversas) then
--       raise exception 'ROLLBACK 20261007_01 recusado: há convidado, consentimento, lead ou conversa — apagar dado é decisão do Founder';
--     end if;
--   end $$;
--   drop table if exists public.canal_conversas;
--   drop table if exists public.canal_leads;
--   drop table if exists public.canal_consentimentos;
--   drop table if exists public.canal_convidados;
--
-- EXPAND-FIRST: sim (4 tabelas novas; nada existente é alterado)
-- DESTRUTIVA:   não
-- LOCK:         nenhum em tabela existente (as FKs só leem `companies` e `multicalculo_pedidos`)
-- ORDEM:        ANTES do Implantar do código da 133-A F1 (sem as tabelas, `repositorio.convidado` falha → a entrada CALA:
--               fail-closed, nenhum envio). O código das corretoras não lê nada daqui.
-- =============================================================

-- (1) quem pode falar com o canal — piloto FECHADO (D-133A-04): o número entra por comando/admin, nunca no código
create table if not exists public.canal_convidados (
  id              uuid primary key default gen_random_uuid(),
  company_id      uuid not null references public.companies(id) on delete cascade,
  telefone        text not null,
  apelido         text null,
  ativo           boolean not null default true,
  limite_dia      integer null,
  criado_em       timestamptz not null default now(),
  atualizado_em   timestamptz not null default now(),
  constraint uq_canal_convidados_tel unique (company_id, telefone),
  constraint ck_canal_convidados_tel check (telefone ~ '^[1-9][0-9]{9,14}$'),
  constraint ck_canal_convidados_apelido check (apelido is null or char_length(apelido) <= 60),
  constraint ck_canal_convidados_limite check (limite_dia is null or limite_dia between 0 and 100)
);

-- (2) o consentimento (D-133A-05) — append-only: cada resposta é uma linha, com a versão do texto que a pessoa leu
create table if not exists public.canal_consentimentos (
  id               uuid primary key default gen_random_uuid(),
  company_id       uuid not null references public.companies(id) on delete cascade,
  telefone         text not null,
  aceito           boolean not null,
  versao_do_texto  text not null,
  registrado_em    timestamptz not null default now(),
  constraint ck_canal_consentimentos_tel check (telefone ~ '^[1-9][0-9]{9,14}$'),
  constraint ck_canal_consentimentos_versao check (char_length(versao_do_texto) between 1 and 40)
);
create index if not exists idx_canal_consentimentos_tel
  on public.canal_consentimentos (company_id, telefone, registrado_em desc);

-- (3) o lead por telefone — o último pedido do número; a FK COMPOSTA impede pedido de outra empresa
create table if not exists public.canal_leads (
  id              uuid primary key default gen_random_uuid(),
  company_id      uuid not null references public.companies(id) on delete cascade,
  telefone        text not null,
  primeiro_nome   text null,
  pedido_id       uuid null,
  criado_em       timestamptz not null default now(),
  atualizado_em   timestamptz not null default now(),
  constraint uq_canal_leads_tel unique (company_id, telefone),
  constraint ck_canal_leads_tel check (telefone ~ '^[1-9][0-9]{9,14}$'),
  constraint ck_canal_leads_nome check (primeiro_nome is null or char_length(primeiro_nome) <= 60),
  constraint fk_canal_leads_pedido foreign key (pedido_id, company_id)
    references public.multicalculo_pedidos (id, company_id) on delete set null (pedido_id)
);

-- (4) a conversa: o estado CIFRADO (portal_vault) e os contadores do dia (o limite e o teto anti-laço)
create table if not exists public.canal_conversas (
  id                uuid primary key default gen_random_uuid(),
  company_id        uuid not null references public.companies(id) on delete cascade,
  telefone          text not null,
  estado_cifrado    text null,
  cotacoes_dia      date null,
  cotacoes_no_dia   integer not null default 0,
  enviadas_dia      date null,
  enviadas_no_dia   integer not null default 0,
  aviso_limite_dia  date null,
  criado_em         timestamptz not null default now(),
  atualizado_em     timestamptz not null default now(),
  constraint uq_canal_conversas_tel unique (company_id, telefone),
  constraint ck_canal_conversas_tel check (telefone ~ '^[1-9][0-9]{9,14}$'),
  constraint ck_canal_conversas_contadores check (cotacoes_no_dia >= 0 and enviadas_no_dia >= 0)
);

-- RLS ligada SEM policy + REVOKE: o backend (service_role) é o único leitor; o filtro company_id mora no código.
alter table public.canal_convidados     enable row level security;
alter table public.canal_consentimentos enable row level security;
alter table public.canal_leads          enable row level security;
alter table public.canal_conversas      enable row level security;
revoke all on table public.canal_convidados     from anon, authenticated;
revoke all on table public.canal_consentimentos from anon, authenticated;
revoke all on table public.canal_leads          from anon, authenticated;
revoke all on table public.canal_conversas      from anon, authenticated;

comment on table public.canal_convidados is
  'SPEC-133-A D-133A-04 — quem pode falar com o canal de cotação (piloto FECHADO). Telefone E.164 só dígitos, com o 9º '
  'dígito (forma canônica de app/services/canal/repositorio.canonico). Não convidado = ZERO resposta. RLS sem policy: '
  'só o backend lê, sempre filtrando company_id.';
comment on column public.canal_convidados.limite_dia is
  'cotações por dia deste número; nulo = o padrão da config do canal (canal.limite_cotacoes_por_dia)';
comment on table public.canal_consentimentos is
  'SPEC-133-A D-133A-05 — cada resposta ao texto de consentimento (sim/não) e a versão do texto lida. Append-only.';
comment on table public.canal_leads is
  'SPEC-133-A — o lead do canal por telefone (primeiro nome, último pedido). FK composta (pedido_id, company_id).';
comment on table public.canal_conversas is
  'SPEC-133-A — o estado da conversa do canal, CIFRADO com portal_vault (PORTAL_VAULT_KEY), e os contadores do dia '
  '(cotações = o limite; enviadas = o teto anti-laço). Nada de dado pessoal em claro.';
comment on column public.canal_conversas.estado_cifrado is
  'Fernet(portal_vault) do JSON do estado da conversa; o código decifra só no backend, nunca em log';
