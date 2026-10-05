-- =============================================================
-- MIGRATION: 20261005_01_spec129b_motor
-- SPEC:      SPEC-129-B — U1 O banco do motor de multicálculo (F1)
-- AUTOR:     builder F1 (Opus 5.5)            DATA: 2026-10-05
-- OBJETIVO:  a fila e o registro do multicálculo: pedidos (do SOLICITANTE), cálculos (a FILA, um por corretora × opção),
--            ofertas e eventos (com FK COMPOSTA de 4 colunas: ninguém grava oferta de uma corretora no cálculo de outra),
--            adesões canal → corretora, a empresa técnica do CANAL, o portal `agger` DESLIGADO e as colunas `robo_*` de
--            `portal_accounts` (lease do robô no BANCO, D-129B-10), com o gatilho que PAUSA o robô quando o login muda.
--
-- 📊 ANTES (05/10/2026, `execute_sql` só leitura — os números da F1, não os do BLOCO 0):
--    · `select pg_get_constraintdef(oid) from pg_constraint where conname='companies_company_kind_check'`
--      → CHECK ((company_kind = ANY (ARRAY['client'::text, 'platform_knowledge'::text, 'platform_blueprint_studio'::text])))
--    · `companies`: 5 linhas, 2 técnicas (platform_knowledge, platform_blueprint_studio, nomes começando por "AutoBrokers");
--      nenhum gatilho AFTER INSERT (só `update_companies_updated_at`, BEFORE UPDATE).
--    · `portal_accounts`: 16 linhas (8 portais × 2), nenhuma `agger`; nenhum gatilho; `uq_portal_accounts_id_company`
--      (id, company_id) existe; RLS ligada, 0 policy.  `portals`: 17, nenhum `agger`; sem CHECK em category.
--    · `multicalculo_*`: 0 tabelas.  Postgres 17.6 (UNIQUE NULLS NOT DISTINCT disponível).
--
-- APPLY:  (1) CHECK de `companies.company_kind` passa a admitir `platform_canal` (drop + add na MESMA transação, só se
--             ainda não admite; a regra `companies_kind_e_tecnica_coerentes_ck` intocada) e a empresa do canal nasce
--             UMA vez (`insert … where not exists … company_kind='platform_canal'`), técnica, sem agente, sem web.
--         (2) `portals.agger` com `is_active=false` (D-129B-11) — `on conflict (key) do nothing`.
--         (3) `portal_accounts` + 6 colunas `robo_*` (nulas = conta que não é de robô: as 16 de hoje) + 3 CHECKs +
--             gatilho BEFORE UPDATE `trg_portal_accounts_robo_pausa` (login/senha mudou numa conta de robô → `pausado`).
--         (4) 5 tabelas `multicalculo_*` + gatilho que confere o TIPO das empresas da adesão + view
--             `multicalculo_seguradora_dia` (security_invoker). RLS ligada SEM policy; REVOKE de anon/authenticated nas
--             5 tabelas, na view e na sequência dos eventos (a lição de 20260727_03). Idempotente.
--
-- VERIFY (read-only · esperado: 1 · 1 · 1 · 6 · 5 · 1 · 1 · 0 · 0 · 5 · 2):
--   select (select count(*) from pg_constraint where conname='companies_company_kind_check'
--             and pg_get_constraintdef(oid) like '%platform_canal%') kind_check,
--          (select count(*) from public.companies where company_kind='platform_canal' and is_technical
--             and split_part(company_name,' ',1)='AutoBrokers' and agent_enabled is false) canal,
--          (select count(*) from public.portals where key='agger' and is_active is false) agger_desligado,
--          (select count(*) from information_schema.columns where table_schema='public' and table_name='portal_accounts'
--             and column_name like 'robo\_%') colunas_robo,
--          (select count(*) from pg_class where relnamespace='public'::regnamespace and relkind='r' and relrowsecurity
--             and relname in ('multicalculo_adesoes','multicalculo_pedidos','multicalculo_calculos',
--                             'multicalculo_ofertas','multicalculo_eventos')) tabelas_com_rls,
--          (select count(*) from pg_class where relname='multicalculo_seguradora_dia'
--             and 'security_invoker=on' = any(reloptions)) view_invoker,
--          (select count(*) from pg_trigger where tgname='trg_portal_accounts_robo_pausa') gatilho_robo,
--          (select count(*) from pg_policies where tablename like 'multicalculo%') policies,
--          (select count(*) from information_schema.role_table_grants where grantee in ('anon','authenticated')
--             and table_schema='public' and table_name like 'multicalculo%') grants_publicos,
--          (select count(*) from public.portal_accounts where robo_estado is null) contas_de_hoje_intocadas_min,
--          (select count(*) from pg_constraint where conname in ('fk_mc_ofertas_calculo','fk_mc_eventos_calculo')
--             and array_length(conkey,1)=4) fks_compostas;
--   -- ⚠️ `contas_de_hoje_intocadas_min` = 16 hoje (o "5" acima é o piso que a regra exige: ≥ 5 nunca falha por crescer)
--
-- VERIFY comportamental (o DO desfaz o que testa — cada sub-bloco termina em raise P0001; nada fica):
--   do $$
--   declare a uuid; b uuid; canal uuid; ca uuid; cb uuid; p uuid; c1 uuid; c2 uuid; r text; res text[] := '{}';
--   begin
--     select id into a from public.companies where company_kind='client' order by created_at limit 1;
--     select id into b from public.companies where company_kind='client' and id<>a order by created_at limit 1;
--     select id into canal from public.companies where company_kind='platform_canal' limit 1;
--     if a is null or b is null or canal is null then raise exception 'VERIFY 20261005_01: faltam 2 clientes ou o canal'; end if;
--     begin  -- tudo dentro de UM sub-bloco: o raise final desfaz as linhas de apoio
--       insert into public.portal_accounts (company_id, portal_key, account_label, username, health, robo_estado, robo_janela)
--         values (a,'agger','verify-129b-a','u','unknown','ativo',null) returning id into ca;
--       insert into public.portal_accounts (company_id, portal_key, account_label, username, health, robo_estado)
--         values (b,'agger','verify-129b-b','u','unknown','ativo') returning id into cb;
--       insert into public.multicalculo_pedidos (company_id, origem, opcoes, corretoras, pedido_cifrado)
--         values (a,'auxiliar',array['padrao'],array[a],'x') returning id into p;
--       insert into public.multicalculo_calculos (pedido_id, solicitante_company_id, company_id, opcao, coberturas, account_id)
--         values (p,a,a,'padrao','{}',ca) returning id into c1;
--       -- 1 · conta de OUTRA corretora no cálculo → FK composta recusa
--       begin insert into public.multicalculo_calculos (pedido_id, solicitante_company_id, company_id, opcao, coberturas, account_id)
--               values (p,a,a,'economica','{}',cb); r := 'aceito';
--       exception when foreign_key_violation then r := 'recusado'; end;  res := res || ('conta_de_outra='||r);
--       -- 2 · oferta com a corretora TROCADA → FK composta (4 colunas) recusa
--       begin insert into public.multicalculo_ofertas (calculo_id, pedido_id, company_id, solicitante_company_id, seguradora, premio_total)
--               values (c1,p,b,a,'X',100); r := 'aceito';
--       exception when foreign_key_violation then r := 'recusado'; end;  res := res || ('oferta_trocada='||r);
--       -- 3 · CONTROLE da 2: a oferta certa entra
--       begin insert into public.multicalculo_ofertas (calculo_id, pedido_id, company_id, solicitante_company_id, seguradora, premio_total)
--               values (c1,p,a,a,'X',100); r := 'aceito';
--       exception when others then r := 'recusado:'||sqlstate; end;  res := res || ('oferta_certa='||r);
--       -- 4 · o mesmo evento 2× → unique (calculo_id, chave)
--       insert into public.multicalculo_eventos (calculo_id, pedido_id, company_id, solicitante_company_id, tipo, chave)
--         values (c1,p,a,a,'nova_oferta','k1');
--       begin insert into public.multicalculo_eventos (calculo_id, pedido_id, company_id, solicitante_company_id, tipo, chave)
--               values (c1,p,a,a,'nova_oferta','k1'); r := 'aceito';
--       exception when unique_violation then r := 'recusado'; end;  res := res || ('evento_repetido='||r);
--       -- 5 · `calculando` sem negócio → CHECK recusa · 6 · CONTROLE: com negócio passa
--       begin update public.multicalculo_calculos set status='calculando' where id=c1; r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('calculando_sem_negocio='||r);
--       begin update public.multicalculo_calculos set status='calculando', negocio_ref='n1', versao=0 where id=c1; r := 'aceito';
--       exception when others then r := 'recusado:'||sqlstate; end;  res := res || ('calculando_com_negocio='||r);
--       -- 7 · conta `teste` sem janela → CHECK recusa
--       begin update public.portal_accounts set robo_estado='teste' where id=ca; r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('teste_sem_janela='||r);
--       -- 8 · o gatilho: mudar o login de um robô → pausado · 9 · CONTROLE: mudar só a saúde → continua ativo
--       update public.portal_accounts set health='ok' where id=cb;
--       select robo_estado into r from public.portal_accounts where id=cb;  res := res || ('saude_muda='||r);
--       update public.portal_accounts set username='outro' where id=cb;
--       select robo_estado into r from public.portal_accounts where id=cb;  res := res || ('login_muda='||r);
--       -- 10 · adesão com um CLIENTE no lugar do canal → gatilho recusa · 11 · CONTROLE: o canal real entra
--       begin insert into public.multicalculo_adesoes (canal_company_id, corretora_company_id) values (a,b); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('adesao_de_cliente='||r);
--       begin insert into public.multicalculo_adesoes (canal_company_id, corretora_company_id) values (canal,b); r := 'aceito';
--       exception when others then r := 'recusado:'||sqlstate; end;  res := res || ('adesao_do_canal='||r);
--       -- 12 · ajuste com origem em OUTRA corretora → FK composta recusa
--       insert into public.multicalculo_calculos (pedido_id, solicitante_company_id, company_id, opcao, coberturas)
--         values (p,a,b,'padrao','{}') returning id into c2;
--       begin insert into public.multicalculo_calculos (pedido_id, solicitante_company_id, company_id, opcao, coberturas, origem_calculo_id)
--               values (p,a,a,'ajuste','{}',c2); r := 'aceito';
--       exception when foreign_key_violation then r := 'recusado'; end;  res := res || ('ajuste_de_outra='||r);
--       -- 13 · prêmio zero e PDF por URL → CHECK recusa
--       begin insert into public.multicalculo_ofertas (calculo_id, pedido_id, company_id, solicitante_company_id, seguradora, premio_total)
--               values (c1,p,a,a,'Y',0); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('premio_zero='||r);
--       begin insert into public.multicalculo_ofertas (calculo_id, pedido_id, company_id, solicitante_company_id, seguradora, premio_total, pdf_path)
--               values (c1,p,a,a,'Z',10,'https://x/y.pdf'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('pdf_url='||r);
--       raise exception using errcode='P0001', message='desfaz';
--     exception when sqlstate 'P0001' then null;
--     end;
--     res := res || ('anon_le=' || has_table_privilege('anon','public.multicalculo_ofertas','select')::text)
--                || ('authenticated_le_view=' || has_table_privilege('authenticated','public.multicalculo_seguradora_dia','select')::text);
--     if res is distinct from array['conta_de_outra=recusado','oferta_trocada=recusado','oferta_certa=aceito',
--          'evento_repetido=recusado','calculando_sem_negocio=recusado','calculando_com_negocio=aceito',
--          'teste_sem_janela=recusado','saude_muda=ativo','login_muda=pausado','adesao_de_cliente=recusado',
--          'adesao_do_canal=aceito','ajuste_de_outra=recusado','premio_zero=recusado','pdf_url=recusado',
--          'anon_le=false','authenticated_le_view=false'] then
--       raise exception 'VERIFY 20261005_01 FALHOU: %', res;
--     end if;
--     raise notice 'VERIFY 20261005_01 OK: %', res;
--   end $$;
--
-- ROLLBACK (🔴 executar é decisão do Founder — MIGRATIONS-AUTHORITY §8.6; RECUSA se houver dado):
--   do $$ begin
--     if exists (select 1 from public.multicalculo_pedidos) or exists (select 1 from public.multicalculo_adesoes)
--        or exists (select 1 from public.portal_accounts where portal_key='agger' or robo_estado is not null) then
--       raise exception 'ROLLBACK 20261005_01 recusado: há pedido, adesão ou conta de robô — apagar dado é decisão do Founder';
--     end if;
--   end $$;
--   drop view if exists public.multicalculo_seguradora_dia;
--   drop table if exists public.multicalculo_eventos;
--   drop table if exists public.multicalculo_ofertas;
--   drop table if exists public.multicalculo_calculos;
--   drop table if exists public.multicalculo_pedidos;
--   drop table if exists public.multicalculo_adesoes;
--   drop function if exists public.multicalculo_adesao_confere_tipos();
--   drop trigger if exists trg_portal_accounts_robo_pausa on public.portal_accounts;
--   drop function if exists public.portal_accounts_robo_pausa();
--   alter table public.portal_accounts drop constraint if exists ck_portal_accounts_robo_estado;
--   alter table public.portal_accounts drop constraint if exists ck_portal_accounts_robo_teto;
--   alter table public.portal_accounts drop constraint if exists ck_portal_accounts_robo_teste_tem_janela;
--   -- as COLUNAS robo_* ficam (nulas; DROP COLUMN só com decisão do Founder — §8.6)
--   delete from public.portals where key='agger';
--   delete from public.companies where company_kind='platform_canal';   -- FK RESTRICT recusa se o canal tiver rastro
--   alter table public.companies drop constraint companies_company_kind_check;
--   alter table public.companies add constraint companies_company_kind_check
--     CHECK ((company_kind = ANY (ARRAY['client'::text, 'platform_knowledge'::text, 'platform_blueprint_studio'::text])));
--
-- EXPAND-FIRST: sim (só adiciona; o CHECK de companies é ALARGADO, nunca estreitado; nada é removido nem renomeado)
-- DESTRUTIVA:   não
-- LOCK:         ACCESS EXCLUSIVE breve em `companies` (troca do CHECK, 5 linhas) e `portal_accounts` (add column, 16
--               linhas) — aplicar com `set lock_timeout='5s'` fora do horário de pico.
-- ORDEM:        ANTES do código da 129-B (porta, motor, robô) — o código antigo não lê nada daqui.
-- =============================================================

-- -----------------------------------------------------------------
-- (1) o CANAL: o CHECK alargado e a empresa técnica (D-129B-05)
-- -----------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_constraint
                  where conrelid = 'public.companies'::regclass and conname = 'companies_company_kind_check'
                    and pg_get_constraintdef(oid) like '%platform_canal%') then
    alter table public.companies drop constraint if exists companies_company_kind_check;
    alter table public.companies add constraint companies_company_kind_check
      check (company_kind = any (array['client'::text, 'platform_knowledge'::text,
                                       'platform_blueprint_studio'::text, 'platform_canal'::text]));
  end if;
end $$;

-- Nome de CANAL, não de corretora (§13.9). Começa por "AutoBrokers": o mascarador do Atlas usa a 1ª palavra de cada
-- empresa (`templater.py:1439-1451`) e "AutoBrokers" já está lá pelas 2 técnicas. Sem agente, sem busca web, sem
-- visão, sem webhook, sem LLM próprio: a empresa existe para ser o SOLICITANTE dos pedidos do canal, nada mais.
insert into public.companies (company_name, company_kind, is_technical, status, plan_type, monthly_fee, setup_fee,
                              agent_enabled, use_langchain, allow_web_search, allow_vision, notes)
select 'AutoBrokers Canal de Cotação', 'platform_canal', true, 'active', 'internal', 0, 0,
       false, false, false, false,
       'SPEC-129-B D-129B-05: empresa TÉCNICA do canal de cotação. Lê ofertas de outra corretora só com adesão ativa.'
 where not exists (select 1 from public.companies where company_kind = 'platform_canal');

-- -----------------------------------------------------------------
-- (2) o portal do multicálculo — DESLIGADO (D-129B-11: a tela de credenciais não o oferece)
-- -----------------------------------------------------------------
insert into public.portals (key, name, login_url, category, cred_kind, is_active, sort_order)
values ('agger', 'Agger (multicálculo)', 'https://aggilizador.com.br', 'multicalculo', 'login_password', false, 900)
on conflict (key) do nothing;

-- -----------------------------------------------------------------
-- (3) a conta de ROBÔ: colunas nulas = conta que não é de robô
-- -----------------------------------------------------------------
alter table public.portal_accounts add column if not exists robo_estado        text;
alter table public.portal_accounts add column if not exists robo_teto_por_hora int;
alter table public.portal_accounts add column if not exists robo_janela        jsonb;
alter table public.portal_accounts add column if not exists robo_ocupada_ate   timestamptz;
alter table public.portal_accounts add column if not exists robo_dono          text;
alter table public.portal_accounts add column if not exists robo_batida_em     timestamptz;

comment on column public.portal_accounts.robo_estado is
  'SPEC-129-B: null = conta comum · ativo · pausado · bloqueado (senha recusada) · ocupada (pessoa logada) · teste (login de PESSOA, só pedido origem=teste no canário, exige janela).';
comment on column public.portal_accounts.robo_dono is
  'SPEC-129-B D-129B-10: a LEASE do robô no banco — dono (id do motor) + robo_batida_em (vence em ~90 s). CAS, nunca Redis.';
comment on column public.portal_accounts.robo_janela is
  'SPEC-129-B: {"dias":"seg-sex","inicio":"07:00","fim":"20:00"} — fora dela o motor não usa a conta e fecha a sessão.';

do $$
begin
  if not exists (select 1 from pg_constraint where conrelid = 'public.portal_accounts'::regclass
                  and conname = 'ck_portal_accounts_robo_estado') then
    alter table public.portal_accounts add constraint ck_portal_accounts_robo_estado
      check (robo_estado is null or robo_estado in ('ativo', 'pausado', 'bloqueado', 'ocupada', 'teste'));
  end if;
  if not exists (select 1 from pg_constraint where conrelid = 'public.portal_accounts'::regclass
                  and conname = 'ck_portal_accounts_robo_teto') then
    alter table public.portal_accounts add constraint ck_portal_accounts_robo_teto
      check (robo_teto_por_hora is null or robo_teto_por_hora between 1 and 600);
  end if;
  if not exists (select 1 from pg_constraint where conrelid = 'public.portal_accounts'::regclass
                  and conname = 'ck_portal_accounts_robo_teste_tem_janela') then
    -- D-129B-04: a conta de PESSOA só atende dentro de uma janela declarada
    alter table public.portal_accounts add constraint ck_portal_accounts_robo_teste_tem_janela
      check (robo_estado is distinct from 'teste'
             or (robo_janela is not null and jsonb_typeof(robo_janela) = 'object'));
  end if;
end $$;

-- D-129B-11: a tela de credenciais (ou qualquer escritor) que troca login/senha de um ROBÔ o PAUSA. Religar é um
-- segundo UPDATE, só do `robo_estado`, pelo comando do Founder — nunca efeito colateral de trocar a senha.
create or replace function public.portal_accounts_robo_pausa()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if old.robo_estado is not null
     and (new.username is distinct from old.username
          or new.secret_encrypted is distinct from old.secret_encrypted) then
    new.robo_estado := 'pausado';
  end if;
  return new;
end;
$$;
revoke all on function public.portal_accounts_robo_pausa() from public, anon, authenticated;

drop trigger if exists trg_portal_accounts_robo_pausa on public.portal_accounts;
create trigger trg_portal_accounts_robo_pausa
  before update on public.portal_accounts
  for each row execute function public.portal_accounts_robo_pausa();

-- -----------------------------------------------------------------
-- (4) as tabelas do motor
-- -----------------------------------------------------------------
create table if not exists public.multicalculo_adesoes (
  id                   uuid primary key default gen_random_uuid(),
  canal_company_id     uuid not null references public.companies(id) on delete restrict,
  corretora_company_id uuid not null references public.companies(id) on delete restrict,
  ativa                boolean not null default true,
  criada_em            timestamptz not null default now(),
  desativada_em        timestamptz,
  constraint uq_multicalculo_adesoes unique (canal_company_id, corretora_company_id),
  constraint ck_multicalculo_adesoes_distintas check (canal_company_id <> corretora_company_id),
  constraint ck_multicalculo_adesoes_desativada check (ativa = (desativada_em is null))
);

-- O canal é `platform_canal` e a corretora é `client` — conferido no BANCO também (a porta e o `aderir` conferem antes).
create or replace function public.multicalculo_adesao_confere_tipos()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if not exists (select 1 from public.companies where id = new.canal_company_id and company_kind = 'platform_canal') then
    raise exception using errcode = '23514', message = 'adesão: o canal precisa ser uma empresa platform_canal';
  end if;
  if not exists (select 1 from public.companies where id = new.corretora_company_id and company_kind = 'client') then
    raise exception using errcode = '23514', message = 'adesão: a corretora precisa ser uma empresa client';
  end if;
  return new;
end;
$$;
revoke all on function public.multicalculo_adesao_confere_tipos() from public, anon, authenticated;

drop trigger if exists trg_multicalculo_adesao_confere_tipos on public.multicalculo_adesoes;
create trigger trg_multicalculo_adesao_confere_tipos
  before insert or update of canal_company_id, corretora_company_id on public.multicalculo_adesoes
  for each row execute function public.multicalculo_adesao_confere_tipos();

create table if not exists public.multicalculo_pedidos (
  id             uuid primary key default gen_random_uuid(),
  company_id     uuid not null references public.companies(id) on delete restrict,   -- o SOLICITANTE
  origem         text not null,
  ramo           int  not null default 31,
  opcoes         text[] not null,
  corretoras     uuid[] not null,
  pedido_cifrado text not null,
  cpf_hmac       text,
  quadro_s       int  not null default 60,
  status         text not null default 'aberto',
  criado_em      timestamptz not null default now(),
  atualizado_em  timestamptz not null default now(),
  constraint uq_multicalculo_pedidos_id_company unique (id, company_id),
  constraint ck_mc_pedidos_origem check (origem in ('auxiliar', 'canal', 'teste')),
  constraint ck_mc_pedidos_opcoes check (cardinality(opcoes) >= 1
                                         and opcoes <@ array['padrao', 'economica']::text[]),
  constraint ck_mc_pedidos_corretoras check (cardinality(corretoras) >= 1),
  constraint ck_mc_pedidos_cifrado check (length(pedido_cifrado) > 0),
  constraint ck_mc_pedidos_cpf_hmac check (cpf_hmac is null or cpf_hmac ~ '^[0-9a-f]{64}$'),
  constraint ck_mc_pedidos_quadro check (quadro_s between 5 and 600),
  constraint ck_mc_pedidos_status check (status in ('aberto', 'fechado', 'cancelado'))
);
comment on column public.multicalculo_pedidos.pedido_cifrado is
  'SPEC-129-B: PedidoDeCalculo.para_dict() em JSON, cifrado com PORTAL_VAULT_KEY (Fernet). Só o motor decifra, em memória.';
comment on column public.multicalculo_pedidos.cpf_hmac is
  'SPEC-129-B: HMAC-SHA256(MULTICALCULO_HMAC_KEY, dígitos do CPF/CNPJ). Nunca hash sem sal.';

create table if not exists public.multicalculo_calculos (
  id                     uuid primary key default gen_random_uuid(),
  pedido_id              uuid not null,
  solicitante_company_id uuid not null,
  company_id             uuid not null references public.companies(id) on delete restrict,  -- a corretora de REGISTRO
  opcao                  text not null,
  coberturas             jsonb not null,
  status                 text not null default 'na_fila',
  account_id             uuid,
  negocio_ref            text,
  versao                 int,
  origem_calculo_id      uuid,
  ajuste                 jsonb,
  prioridade             int  not null default 5,
  expira_em              timestamptz,
  disponivel_em          timestamptz not null default now(),
  tentativas             int  not null default 0,
  dono                   text,
  batida_em              timestamptz,
  disparado_em           timestamptz,
  primeira_oferta_em     timestamptz,
  quadro_pronto_em       timestamptz,
  fechado_em             timestamptz,
  erro                   text,
  criado_em              timestamptz not null default now(),
  constraint fk_mc_calculos_pedido foreign key (pedido_id, solicitante_company_id)
    references public.multicalculo_pedidos (id, company_id) on delete cascade,
  constraint fk_mc_calculos_conta foreign key (account_id, company_id)
    references public.portal_accounts (id, company_id) on delete restrict,
  constraint uq_mc_calculos_quatro unique (id, pedido_id, company_id, solicitante_company_id),
  -- o ajuste nasce do MESMO pedido e da MESMA corretora (D-MC-41) — no banco, não só na porta
  constraint fk_mc_calculos_origem foreign key (origem_calculo_id, pedido_id, company_id, solicitante_company_id)
    references public.multicalculo_calculos (id, pedido_id, company_id, solicitante_company_id),
  constraint ck_mc_calculos_opcao check (opcao in ('padrao', 'economica', 'ajuste')),
  constraint ck_mc_calculos_ajuste check ((opcao = 'ajuste') = (origem_calculo_id is not null)),
  constraint ck_mc_calculos_coberturas check (jsonb_typeof(coberturas) = 'object'),
  constraint ck_mc_calculos_status check (status in ('na_fila', 'disparando', 'calculando', 'fechado', 'falhou',
                                                     'incerto', 'cancelado', 'expirado')),
  constraint ck_mc_calculos_negocio check (status not in ('calculando', 'fechado')
                                           or (negocio_ref is not null and versao is not null)),
  constraint ck_mc_calculos_versao check (versao is null or versao >= 0),
  constraint ck_mc_calculos_tentativas check (tentativas >= 0)
);
create index if not exists idx_mc_calculos_fila on public.multicalculo_calculos (prioridade, disponivel_em)
  where status = 'na_fila';
create index if not exists idx_mc_calculos_em_voo on public.multicalculo_calculos (batida_em)
  where status in ('disparando', 'calculando');
create index if not exists idx_mc_calculos_pedido on public.multicalculo_calculos (pedido_id);
create index if not exists idx_mc_calculos_corretora on public.multicalculo_calculos (company_id, criado_em);
create index if not exists idx_mc_calculos_conta on public.multicalculo_calculos (account_id) where account_id is not null;

create table if not exists public.multicalculo_ofertas (
  id                     uuid primary key default gen_random_uuid(),
  calculo_id             uuid not null,
  pedido_id              uuid not null,
  company_id             uuid not null,
  solicitante_company_id uuid not null,
  seguradora             text not null,
  seguradora_codigo      int,
  pacote                 text not null default '',
  tipo_de_pacote         int,
  premio_total           numeric(14, 2) not null,
  premio_mensal          numeric(14, 2),
  franquia_valor         numeric(14, 2),
  franquia_tipo          text,
  coberturas             jsonb,
  parcelamentos          jsonb,
  tem_pdf                boolean not null default false,
  pdf_path               text,
  alertas                text[] not null default '{}',
  comissao_percentual    numeric(7, 3),          -- 🔴 INTERNO: só a corretora dona a vê (a porta corta)
  recebida_em            timestamptz not null default now(),
  atualizada_em          timestamptz not null default now(),
  constraint fk_mc_ofertas_calculo foreign key (calculo_id, pedido_id, company_id, solicitante_company_id)
    references public.multicalculo_calculos (id, pedido_id, company_id, solicitante_company_id) on delete cascade,
  constraint uq_mc_ofertas unique nulls not distinct (calculo_id, seguradora_codigo, pacote, tipo_de_pacote),
  constraint ck_mc_ofertas_premio check (premio_total > 0),
  constraint ck_mc_ofertas_pdf check (pdf_path is null or pdf_path ~ '^multicalculo/[0-9a-f-]+/[0-9a-f-]+/[^/]+$')
);
create index if not exists idx_mc_ofertas_pedido on public.multicalculo_ofertas (pedido_id, premio_total);

create table if not exists public.multicalculo_eventos (
  id                     bigint generated always as identity primary key,
  calculo_id             uuid not null,
  pedido_id              uuid not null,
  company_id             uuid not null,
  solicitante_company_id uuid not null,
  tipo                   text not null,
  seguradora             text,
  seguradora_codigo      int,
  pacote                 text,
  tipo_de_pacote         int,
  familia                text,
  oferta_id              uuid references public.multicalculo_ofertas(id) on delete set null,
  chave                  text not null,
  t_s                    numeric(10, 3),
  criado_em              timestamptz not null default now(),
  constraint fk_mc_eventos_calculo foreign key (calculo_id, pedido_id, company_id, solicitante_company_id)
    references public.multicalculo_calculos (id, pedido_id, company_id, solicitante_company_id) on delete cascade,
  constraint uq_mc_eventos_chave unique (calculo_id, chave),
  constraint ck_mc_eventos_tipo check (tipo ~ '^[a-z_]{3,40}$'),
  constraint ck_mc_eventos_chave check (length(chave) between 1 and 300)
);
create index if not exists idx_mc_eventos_pedido on public.multicalculo_eventos (pedido_id, id);

-- D-129B-07 / D-MC-53: a seguradora por dia — SÓ MEDIR. security_invoker: quem lê é quem consulta, nunca o dono da view.
create or replace view public.multicalculo_seguradora_dia with (security_invoker = on) as
select (e.criado_em at time zone 'America/Sao_Paulo')::date                     as dia,
       e.company_id                                                             as corretora_company_id,
       e.seguradora_codigo,
       max(e.seguradora)                                                        as seguradora,
       count(distinct e.calculo_id)                                             as calculos,
       count(*) filter (where e.tipo in ('nova_oferta', 'oferta_atualizada'))    as ofertas,
       count(*) filter (where e.tipo = 'seguradora_recusou')                     as recusas,
       count(*) filter (where e.tipo = 'seguradora_recusou' and e.familia = 'CREDENCIAL')    as recusas_credencial,
       count(*) filter (where e.tipo = 'seguradora_recusou' and e.familia = 'PERMISSAO')     as recusas_permissao,
       count(*) filter (where e.tipo = 'seguradora_recusou' and e.familia = 'ACEITACAO')     as recusas_aceitacao,
       count(*) filter (where e.tipo = 'seguradora_recusou' and e.familia = 'COMERCIAL')     as recusas_comercial,
       count(*) filter (where e.tipo = 'seguradora_recusou' and e.familia = 'INSTABILIDADE') as recusas_instabilidade,
       count(*) filter (where e.tipo = 'seguradora_recusou' and e.familia = 'DADO')          as recusas_dado,
       count(*) filter (where e.tipo = 'seguradora_recusou' and e.familia = 'DESCONHECIDA')  as recusas_desconhecida
  from public.multicalculo_eventos e
 where e.seguradora_codigo is not null or e.seguradora is not null
 group by 1, 2, 3;

-- RLS ligada SEM policy + REVOKE: o backend (service_role) é o único leitor; o filtro company_id mora no código.
alter table public.multicalculo_adesoes  enable row level security;
alter table public.multicalculo_pedidos  enable row level security;
alter table public.multicalculo_calculos enable row level security;
alter table public.multicalculo_ofertas  enable row level security;
alter table public.multicalculo_eventos  enable row level security;

revoke all on table public.multicalculo_adesoes        from anon, authenticated;
revoke all on table public.multicalculo_pedidos        from anon, authenticated;
revoke all on table public.multicalculo_calculos       from anon, authenticated;
revoke all on table public.multicalculo_ofertas        from anon, authenticated;
revoke all on table public.multicalculo_eventos        from anon, authenticated;
revoke all on table public.multicalculo_seguradora_dia from anon, authenticated;
revoke all on sequence public.multicalculo_eventos_id_seq from anon, authenticated;
