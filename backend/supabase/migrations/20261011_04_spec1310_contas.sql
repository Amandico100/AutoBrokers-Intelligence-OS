-- =============================================================
-- MIGRATION: 20261011_04_spec1310_contas
-- SPEC:      SPEC-131-0 parte A — F3 · as contas (U4 contas com uso e dono · U5 qual_agger + auditoria)
-- AUTOR:     builder da F3 (Opus 5.5)                              DATA: 2026-10-11
-- OBJETIVO:  (1) uma conta do Agger passa a dizer DE QUEM é: da CORRETORA (`uso='global'`, o robô dedicado), de uma
--            PESSOA da equipe (`uso='membro'` + `dono_user_id`) ou do canário (`uso='teste'`, login de pessoa só no
--            canário). (2) o pedido grava QUEM pediu e PARA QUAL serviço (`servico`, `solicitante_user_id`) — `origem`
--            NÃO muda (D-131-0-32: CHECK, prioridade e ~15 leitores). (3) cada cálculo grava em QUAL conta ele tem de
--            sair, por qual regra, se caiu na conta da corretora por falta da conta da pessoa, e o porquê
--            (`conta_exigida_id`, `conta_regra`, `conta_fallback`, `conta_motivo`) — decididos por
--            `app.services.multicalculo.qual_agger.decidir` (D-131-0-05/06/29).
--
-- 📊 ANTES (11/10/2026, SELECT em `set transaction read only` pelo psycopg, `backend/.env SUPABASE_DB_URL`):
--    · portal_accounts agger: 4 linhas — 2× `agger-da-corretora` `ativo` sem janela com senha, 2× `canario-129b`
--      `pausado` com janela sem senha (uma de cada em 2 corretoras). Nenhuma `agger-da-corretora` em `teste` (0).
--      → depois do backfill: 1 `global` + 1 `teste` por corretora; NENHUMA `membro`.
--    · constraints vivas de portal_accounts: ck_portal_accounts_robo_estado, ck_portal_accounts_robo_teste_tem_janela,
--      ck_portal_accounts_robo_teto, fk_portal_accounts_company, portal_accounts_company_id_portal_key_account_label_key,
--      portal_accounts_pkey e **uq_portal_accounts_id_company (id, company_id)** — ⚠️ esta UNIQUE (e a
--      fk_portal_accounts_company) NÃO têm arquivo de migration no repositório (o MIGRATIONS-AUTHORITY §1 já o diz); a
--      FK composta nova `fk_mc_calculos_conta_exigida` depende dela, exatamente como a `fk_mc_calculos_conta` (20261005_01).
--      O bloco A confere que ela existe e PARA se não existir.
--    · única trigger: trg_portal_accounts_robo_pausa (BEFORE UPDATE): pausa a conta de robô quando `username` ou
--      `secret_encrypted` mudam. O backfill escreve SÓ `uso` → a função não muda `robo_estado` (a condição é falsa);
--      o bloco C PROVA isso dentro da transação (retrato do `robo_estado` antes × depois; diferente → exceção).
--    · multicalculo_pedidos 6 linhas · multicalculo_calculos 17 linhas: as colunas novas nascem nulas (`conta_fallback`
--      false) = legado; nenhuma linha antiga é reescrita.
--    · users_v2.status ∈ {active, lead}; company_members 10 vínculos, todos `active`.
--
-- 🔴 A ORDEM com o código: o código desta fatia LÊ `uso`/`dono_user_id` no motor (`robos.candidatos`) e grava as colunas
--    novas quando a porta recebe `servico`. Esta migration entra ANTES do deploy (F5 aplica _02 → _03 → _04 com VERIFY).
--
-- ⚖️ DECISÃO DO BUILDER (registrada no handoff): o índice único "uma conta GLOBAL por corretora" NÃO entra (fica
--    comentado no fim, pronto). 📊 Hoje cabe (1 global por corretora), mas a SPEC §5/§5.1 mantém o RODÍZIO entre contas
--    `global` (o comando cadastra `robo-2`; os testes do motor da 129-B/129-C o exercitam). Nota: sem o índice 80 ·
--    com o índice 40 (mata o rodízio e reescreve 4 guardas). O gerente decide; descomentar é uma linha.
--
-- APPLY (pelo GERENTE — o builder NÃO aplica):
--   A. confere a pré-condição: a UNIQUE (id, company_id) de portal_accounts existe (sem arquivo no repo).
--   B. portal_accounts: ADD COLUMN uso text · dono_user_id uuid; FK fk_portal_accounts_dono_user → users_v2(id)
--      ON DELETE RESTRICT (NOT VALID + VALIDATE).
--   C. BACKFILL (só portal_key='agger' e uso nulo): `robo_estado='teste'` ou rótulo `canario%` → 'teste' (o login de
--      PESSOA nunca vira conta da corretora — vence o rótulo) · `agger-da-corretora` → 'global' · demais → 'global'.
--      Prova no mesmo bloco: nenhum `robo_estado` mudou (o gatilho não disparou efeito).
--   D. CHECKs (NOT VALID + VALIDATE, DEPOIS do backfill):
--        ck_portal_accounts_uso            uso nulo, ou portal agger com uso ∈ global·membro·teste
--        ck_portal_accounts_agger_tem_uso  portal agger ⇒ uso não nulo
--        ck_portal_accounts_dono_do_membro (uso = 'membro') ⇔ dono_user_id não nulo (em TODA linha)
--        ck_portal_accounts_membro_real    conta de pessoa: sem janela e nunca `robo_estado='teste'`
--   E. índice único parcial uq_portal_accounts_membro_por_pessoa (company_id, dono_user_id) WHERE uso='membro'.
--   F. multicalculo_pedidos: servico text NULL + CHECK in (qcm, cotacao, renovacao) · solicitante_user_id uuid NULL
--      + FK → users_v2 ON DELETE SET NULL.
--   G. multicalculo_calculos: conta_exigida_id uuid NULL + FK composta (conta_exigida_id, company_id) →
--      portal_accounts(id, company_id) ON DELETE RESTRICT · conta_regra text · conta_fallback boolean not null default
--      false · conta_motivo text (+ CHECKs de tamanho).
--   H. COMMENTs.
--
-- VERIFY (read-only):
--   select
--     (select count(*) from information_schema.columns where table_schema='public' and table_name='portal_accounts'
--        and column_name in ('uso','dono_user_id')) as cols_conta,                                       -- 2
--     (select count(*) from information_schema.columns where table_schema='public' and table_name='multicalculo_pedidos'
--        and column_name in ('servico','solicitante_user_id')) as cols_pedido,                           -- 2
--     (select count(*) from information_schema.columns where table_schema='public' and table_name='multicalculo_calculos'
--        and column_name in ('conta_exigida_id','conta_regra','conta_fallback','conta_motivo')) as cols_calc, -- 4
--     (select count(*) from pg_constraint where convalidated and conname in (
--        'fk_portal_accounts_dono_user','ck_portal_accounts_uso','ck_portal_accounts_agger_tem_uso',
--        'ck_portal_accounts_dono_do_membro','ck_portal_accounts_membro_real','ck_mc_pedidos_servico',
--        'fk_mc_pedidos_solicitante_user','fk_mc_calculos_conta_exigida','ck_mc_calculos_conta_regra',
--        'ck_mc_calculos_conta_motivo')) as travas_validadas,                                             -- 10
--     (select count(*) from pg_indexes where tablename='portal_accounts'
--        and indexname='uq_portal_accounts_membro_por_pessoa') as indice_membro,                          -- 1
--     (select count(*) from public.portal_accounts where portal_key='agger' and uso is null) as agger_sem_uso, -- 0
--     (select string_agg(uso || ':' || n, ',' order by uso) from (select uso, count(*) n from public.portal_accounts
--        where portal_key='agger' group by uso) x) as usos,                                              -- global:2,teste:2
--     (select count(*) from public.portal_accounts where portal_key='agger' and uso='global'
--        and robo_estado='teste') as pessoa_virou_global;                                               -- 0
--
--   -- 🔴 a TRAVA consegue recusar (CLAUDE.md §9.3) — as definições REAIS do catálogo copiadas para tabelas temporárias;
--   --    nada fica gravado (só tabela TEMPORÁRIA, ON COMMIT DROP).
--   do $$
--   declare d_uso text; d_agger text; d_dono text; d_real text; recusas int := 0; u1 uuid := gen_random_uuid();
--           u2 uuid := gen_random_uuid(); c1 uuid := gen_random_uuid();
--   begin
--     select pg_get_constraintdef(oid) into d_uso   from pg_constraint where conname = 'ck_portal_accounts_uso';
--     select pg_get_constraintdef(oid) into d_agger from pg_constraint where conname = 'ck_portal_accounts_agger_tem_uso';
--     select pg_get_constraintdef(oid) into d_dono  from pg_constraint where conname = 'ck_portal_accounts_dono_do_membro';
--     select pg_get_constraintdef(oid) into d_real  from pg_constraint where conname = 'ck_portal_accounts_membro_real';
--     create temp table verify_1310_contas (company_id uuid, portal_key text, uso text, dono_user_id uuid,
--                                           robo_estado text, robo_janela jsonb) on commit drop;
--     execute 'alter table verify_1310_contas add constraint c1 ' || d_uso;
--     execute 'alter table verify_1310_contas add constraint c2 ' || d_agger;
--     execute 'alter table verify_1310_contas add constraint c3 ' || d_dono;
--     execute 'alter table verify_1310_contas add constraint c4 ' || d_real;
--     -- o índice parcial REAL, com a mesma expressão do catálogo
--     execute replace(replace((select indexdef from pg_indexes where indexname = 'uq_portal_accounts_membro_por_pessoa'),
--                     'public.portal_accounts', 'verify_1310_contas'), 'uq_portal_accounts_membro_por_pessoa', 'verify_1310_uq');
--     -- aceitas (controle): a global, a teste, uma conta de pessoa de cada dono, uma conta comum (não agger)
--     insert into verify_1310_contas values (c1, 'agger', 'global', null, 'ativo', null),
--                                           (c1, 'agger', 'teste', null, 'teste', '{"dias":"seg"}'),
--                                           (c1, 'agger', 'membro', u1, 'ativo', null),
--                                           (c1, 'agger', 'membro', u2, 'ativo', null),
--                                           (c1, 'porto_corretor', null, null, null, null);
--     -- 1) conta de pessoa SEM dono → recusada
--     begin insert into verify_1310_contas values (c1, 'agger', 'membro', null, 'ativo', null);
--     exception when check_violation then recusas := recusas + 1; end;
--     -- 2) DUAS contas de pessoa do MESMO dono na MESMA corretora → recusada
--     begin insert into verify_1310_contas values (c1, 'agger', 'membro', u1, 'pausado', null);
--     exception when unique_violation then recusas := recusas + 1; end;
--     -- 3) conta do Agger sem uso → recusada
--     begin insert into verify_1310_contas values (c1, 'agger', null, null, 'ativo', null);
--     exception when check_violation then recusas := recusas + 1; end;
--     -- 4) dono numa conta global → recusada
--     begin insert into verify_1310_contas values (c1, 'agger', 'global', u1, 'ativo', null);
--     exception when check_violation then recusas := recusas + 1; end;
--     -- 5) conta de pessoa com horário (ou em estado de teste) → recusada
--     begin insert into verify_1310_contas values (c1, 'agger', 'membro', gen_random_uuid(), 'teste', '{"dias":"seg"}');
--     exception when check_violation then recusas := recusas + 1; end;
--     -- 6) uso inventado → recusado
--     begin insert into verify_1310_contas values (c1, 'agger', 'robo', null, 'ativo', null);
--     exception when check_violation then recusas := recusas + 1; end;
--     if recusas <> 6 then raise exception 'VERIFY 20261011_04 FALHOU: % recusas (esperado 6)', recusas; end if;
--     if (select count(*) from verify_1310_contas) <> 5 then raise exception 'VERIFY 20261011_04: controle não entrou'; end if;
--     raise notice 'VERIFY 20261011_04 OK: 6 recusas (sem dono, mesmo dono 2x, sem uso, dono na global, pessoa com horário, uso inventado) e 5 aceitas';
--   end $$;
--   -- e nada ficou: select count(*) from pg_class where relname like 'verify_1310%';   -- 0 (fora da transação)
--
-- ROLLBACK (só se nenhum código depender das colunas — o motor desta fatia LÊ `uso`: reverter o código ANTES):
--   drop index if exists public.uq_portal_accounts_membro_por_pessoa;
--   alter table public.portal_accounts drop constraint if exists ck_portal_accounts_membro_real;
--   alter table public.portal_accounts drop constraint if exists ck_portal_accounts_dono_do_membro;
--   alter table public.portal_accounts drop constraint if exists ck_portal_accounts_agger_tem_uso;
--   alter table public.portal_accounts drop constraint if exists ck_portal_accounts_uso;
--   alter table public.portal_accounts drop constraint if exists fk_portal_accounts_dono_user;
--   alter table public.multicalculo_calculos drop constraint if exists fk_mc_calculos_conta_exigida;
--   alter table public.multicalculo_calculos drop constraint if exists ck_mc_calculos_conta_regra;
--   alter table public.multicalculo_calculos drop constraint if exists ck_mc_calculos_conta_motivo;
--   alter table public.multicalculo_pedidos drop constraint if exists ck_mc_pedidos_servico;
--   alter table public.multicalculo_pedidos drop constraint if exists fk_mc_pedidos_solicitante_user;
--   -- as colunas (DESTRUTIVO — só com decisão do Founder, MIGRATIONS-AUTHORITY §8):
--   -- alter table public.multicalculo_calculos drop column if exists conta_exigida_id, drop column if exists conta_regra,
--   --   drop column if exists conta_fallback, drop column if exists conta_motivo;
--   -- alter table public.multicalculo_pedidos drop column if exists servico, drop column if exists solicitante_user_id;
--   -- alter table public.portal_accounts drop column if exists uso, drop column if exists dono_user_id;
--
-- EXPAND-FIRST: sim (só acrescenta colunas, travas e um índice; o backfill escreve só a coluna nova `uso`)
-- DESTRUTIVA:   não
-- IDEMPOTENTE:  sim (IF NOT EXISTS / checagem no catálogo; o backfill só toca `uso is null`)
-- =============================================================

begin;

-- -----------------------------------------------------------------
-- (A) a pré-condição sem arquivo: UNIQUE (id, company_id) em portal_accounts
-- -----------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_constraint where conrelid = 'public.portal_accounts'::regclass
                  and conname = 'uq_portal_accounts_id_company') then
    raise exception '20261011_04: falta uq_portal_accounts_id_company (id, company_id) — a FK composta depende dela';
  end if;
end $$;

-- -----------------------------------------------------------------
-- (B) portal_accounts: de quem é a conta
-- -----------------------------------------------------------------
alter table public.portal_accounts add column if not exists uso          text;
alter table public.portal_accounts add column if not exists dono_user_id uuid;

do $$
begin
  if not exists (select 1 from pg_constraint where conrelid = 'public.portal_accounts'::regclass
                  and conname = 'fk_portal_accounts_dono_user') then
    alter table public.portal_accounts add constraint fk_portal_accounts_dono_user
      foreign key (dono_user_id) references public.users_v2(id) on delete restrict not valid;
  end if;
end $$;
alter table public.portal_accounts validate constraint fk_portal_accounts_dono_user;

-- -----------------------------------------------------------------
-- (C) backfill — só o Agger, só quem ainda não tem uso. O login de PESSOA (teste/canário) vence o rótulo.
-- -----------------------------------------------------------------
do $$
declare mudou int;
begin
  create temp table _antes_1310 on commit drop as
    select id, robo_estado from public.portal_accounts where portal_key = 'agger';

  update public.portal_accounts
     set uso = case
                 when robo_estado = 'teste' or account_label like 'canario%' then 'teste'
                 when account_label = 'agger-da-corretora'                   then 'global'
                 else 'global'
               end
   where portal_key = 'agger' and uso is null;

  -- 🔴 o gatilho trg_portal_accounts_robo_pausa roda neste UPDATE, mas só muda robo_estado quando login/senha mudam:
  --    a prova é o retrato
  select count(*) into mudou
    from _antes_1310 a join public.portal_accounts p on p.id = a.id
   where p.robo_estado is distinct from a.robo_estado;
  if mudou <> 0 then
    raise exception '20261011_04: o backfill de uso mudou o robo_estado de % conta(s) — nada aplicado', mudou;
  end if;
end $$;

-- -----------------------------------------------------------------
-- (D) as travas — NOT VALID + VALIDATE, depois do backfill
-- -----------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_constraint where conrelid = 'public.portal_accounts'::regclass
                  and conname = 'ck_portal_accounts_uso') then
    alter table public.portal_accounts add constraint ck_portal_accounts_uso
      check (uso is null or (portal_key = 'agger' and uso in ('global', 'membro', 'teste'))) not valid;
  end if;
  if not exists (select 1 from pg_constraint where conrelid = 'public.portal_accounts'::regclass
                  and conname = 'ck_portal_accounts_agger_tem_uso') then
    alter table public.portal_accounts add constraint ck_portal_accounts_agger_tem_uso
      check (portal_key <> 'agger' or uso is not null) not valid;
  end if;
  if not exists (select 1 from pg_constraint where conrelid = 'public.portal_accounts'::regclass
                  and conname = 'ck_portal_accounts_dono_do_membro') then
    -- `is not distinct from`: numa linha sem uso (conta comum) a comparação é FALSE, nunca NULL — a trava vale nela
    alter table public.portal_accounts add constraint ck_portal_accounts_dono_do_membro
      check ((uso is not distinct from 'membro') = (dono_user_id is not null)) not valid;
  end if;
  if not exists (select 1 from pg_constraint where conrelid = 'public.portal_accounts'::regclass
                  and conname = 'ck_portal_accounts_membro_real') then
    -- o Agger de uma pessoa é uso REAL: sem horário na conta (o horário é regra do auxiliar) e nunca o estado do canário
    alter table public.portal_accounts add constraint ck_portal_accounts_membro_real
      check (uso is distinct from 'membro'
             or (robo_janela is null and robo_estado is distinct from 'teste')) not valid;
  end if;
end $$;
alter table public.portal_accounts validate constraint ck_portal_accounts_uso;
alter table public.portal_accounts validate constraint ck_portal_accounts_agger_tem_uso;
alter table public.portal_accounts validate constraint ck_portal_accounts_dono_do_membro;
alter table public.portal_accounts validate constraint ck_portal_accounts_membro_real;

-- -----------------------------------------------------------------
-- (E) uma conta de pessoa por pessoa, por corretora
-- -----------------------------------------------------------------
create unique index if not exists uq_portal_accounts_membro_por_pessoa
  on public.portal_accounts (company_id, dono_user_id) where uso = 'membro';

-- -----------------------------------------------------------------
-- (F) o pedido: para qual serviço e quem pediu
-- -----------------------------------------------------------------
alter table public.multicalculo_pedidos add column if not exists servico             text;
alter table public.multicalculo_pedidos add column if not exists solicitante_user_id uuid;

do $$
begin
  if not exists (select 1 from pg_constraint where conrelid = 'public.multicalculo_pedidos'::regclass
                  and conname = 'ck_mc_pedidos_servico') then
    alter table public.multicalculo_pedidos add constraint ck_mc_pedidos_servico
      check (servico is null or servico in ('qcm', 'cotacao', 'renovacao')) not valid;
  end if;
  if not exists (select 1 from pg_constraint where conrelid = 'public.multicalculo_pedidos'::regclass
                  and conname = 'fk_mc_pedidos_solicitante_user') then
    alter table public.multicalculo_pedidos add constraint fk_mc_pedidos_solicitante_user
      foreign key (solicitante_user_id) references public.users_v2(id) on delete set null not valid;
  end if;
end $$;
alter table public.multicalculo_pedidos validate constraint ck_mc_pedidos_servico;
alter table public.multicalculo_pedidos validate constraint fk_mc_pedidos_solicitante_user;

-- -----------------------------------------------------------------
-- (G) o cálculo: em qual conta, por qual regra, e por quê
-- -----------------------------------------------------------------
alter table public.multicalculo_calculos add column if not exists conta_exigida_id uuid;
alter table public.multicalculo_calculos add column if not exists conta_regra      text;
alter table public.multicalculo_calculos add column if not exists conta_fallback   boolean not null default false;
alter table public.multicalculo_calculos add column if not exists conta_motivo     text;

do $$
begin
  if not exists (select 1 from pg_constraint where conrelid = 'public.multicalculo_calculos'::regclass
                  and conname = 'fk_mc_calculos_conta_exigida') then
    -- a conta exigida é da MESMA corretora do cálculo — no banco, não só na porta (molde: fk_mc_calculos_conta)
    alter table public.multicalculo_calculos add constraint fk_mc_calculos_conta_exigida
      foreign key (conta_exigida_id, company_id) references public.portal_accounts (id, company_id)
      on delete restrict not valid;
  end if;
  if not exists (select 1 from pg_constraint where conrelid = 'public.multicalculo_calculos'::regclass
                  and conname = 'ck_mc_calculos_conta_regra') then
    alter table public.multicalculo_calculos add constraint ck_mc_calculos_conta_regra
      check (conta_regra is null or length(conta_regra) between 1 and 60) not valid;
  end if;
  if not exists (select 1 from pg_constraint where conrelid = 'public.multicalculo_calculos'::regclass
                  and conname = 'ck_mc_calculos_conta_motivo') then
    alter table public.multicalculo_calculos add constraint ck_mc_calculos_conta_motivo
      check (conta_motivo is null or length(conta_motivo) between 1 and 500) not valid;
  end if;
end $$;
alter table public.multicalculo_calculos validate constraint fk_mc_calculos_conta_exigida;
alter table public.multicalculo_calculos validate constraint ck_mc_calculos_conta_regra;
alter table public.multicalculo_calculos validate constraint ck_mc_calculos_conta_motivo;

-- -----------------------------------------------------------------
-- (H) o que cada coluna quer dizer
-- -----------------------------------------------------------------
comment on column public.portal_accounts.uso is
  'SPEC-131-0 A (D-131-0-29): só portal agger — global (o robô dedicado da corretora: Quem Cobra Menos e quem não tem '
  'Agger próprio) · membro (o Agger de uma PESSOA da equipe: o robô entra, calcula e sai; só com conta exigida) · '
  'teste (login de pessoa do canário). Quem decide a conta: app.services.multicalculo.qual_agger.';
comment on column public.portal_accounts.dono_user_id is
  'SPEC-131-0 A (D-131-0-29): a PESSOA dona da conta uso=membro (users_v2). Só vale se for membro ATIVO desta '
  'corretora — o motor e o qual_agger reconferem a cada uso (fail-closed). Não confundir com robo_dono (a lease).';
comment on column public.multicalculo_pedidos.servico is
  'SPEC-131-0 A (D-131-0-32): qcm · cotacao · renovacao. Nulo = pedido legado/canário (nunca usa o Agger de uma pessoa).';
comment on column public.multicalculo_pedidos.solicitante_user_id is
  'SPEC-131-0 A: a PESSOA que pediu (cotação). Nulo no Quem Cobra Menos e nos pedidos legados.';
comment on column public.multicalculo_calculos.conta_exigida_id is
  'SPEC-131-0 A: a conta em que ESTE cálculo tem de sair (o motor usa só ela, nunca outra). Nulo = rodízio das contas '
  'da corretora (uso=global).';
comment on column public.multicalculo_calculos.conta_regra is
  'SPEC-131-0 A: a regra do qual_agger que escolheu a conta (ex.: qcm_global, cotacao_da_pessoa, renovacao_do_dono, '
  'recalculo_mesma_conta).';
comment on column public.multicalculo_calculos.conta_fallback is
  'SPEC-131-0 A: true = a conta da pessoa não pôde ser usada e o cálculo foi para o Agger da corretora (com aviso).';
comment on column public.multicalculo_calculos.conta_motivo is
  'SPEC-131-0 A: o porquê da escolha e o aviso a quem precisa saber, em português de gente (quem entrega é a 131/132).';

commit;

-- -----------------------------------------------------------------
-- ⚖️ OPCIONAL — decisão do gerente (ver o cabeçalho). Uma conta GLOBAL por corretora. 📊 cabe hoje (1 por corretora),
--    mas proíbe o rodízio `robo-2` que a SPEC §5.1 mantém. Para ligar: descomentar e aplicar.
-- create unique index if not exists uq_portal_accounts_global_por_corretora
--   on public.portal_accounts (company_id) where portal_key = 'agger' and uso = 'global';
-- -----------------------------------------------------------------
