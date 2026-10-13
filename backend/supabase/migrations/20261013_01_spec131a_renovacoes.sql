-- =============================================================
-- MIGRATION: 20261013_01_spec131a_renovacoes
-- SPEC:      SPEC-131-A — F1 · a lista, a tabela e a conferência (a madrugada da renovação)
-- AUTOR:     builder F1 (Opus 5.5)            DATA: 2026-10-12
-- OBJETIVO:  a ENTIDADE "renovação" com estado (a máquina inteira no CHECK; o código liga só até `enviada`), a trilha
--            de cada transição, a medida diária de completude, a ausência (férias → substituto), e no pedido do
--            multicálculo: a política de sessão da madrugada, o vínculo com a renovação e as opções da renovação
--            (`anterior`, `franquia_reduzida`).
--
-- 📊 ANTES (12/10/2026, SELECT só leitura pelo MCP, projeto dcajcvlzcjbmyapmklil):
--    · to_regclass de renovacoes / renovacao_eventos / renovacao_dias / membro_ausencias → nenhuma existe
--    · ck_mc_pedidos_opcoes → CHECK ((cardinality(opcoes) >= 1) AND (opcoes <@ ARRAY['padrao','economica',
--        'completa_mais','minima']))
--    · ck_mc_calculos_opcao → CHECK ((opcao = ANY (ARRAY['padrao','economica','completa_mais','minima','ajuste'])))
--    · multicalculo_pedidos: sem `politica_de_sessao` nem `renovacao_id`; `uq_multicalculo_pedidos_id_company` existe
--    · company_members: (user_id, company_id) UNIQUE (alvo das FKs da ausência); papéis `member` · `admin_company`
--
-- APPLY (pelo GERENTE — o builder NÃO aplica; um arquivo, idempotente, expand-only):
--   A. `renovacoes` (create if not exists) + UNIQUE (company_id, sistema, codfil, nosnum, fimvig) + UNIQUE (id,
--      company_id) (alvo das FKs "mesma corretora") + CHECKs: estado ∈ ligados ∪ reservados · motivo obrigatório em
--      pendente/falhou/perdida · documento mascarado com no máximo 2 dígitos · HMAC de 64 hex · nome curto SEM espaço
--      (só o primeiro nome) · sistema · codfil ≥ 1 · FKs (pedido_id, company_id) → multicalculo_pedidos e
--      (conta_agger_id, company_id) → portal_accounts; dono/responsável → users_v2 ON DELETE SET NULL.
--      Índices (company_id, estado) e (company_id, calcular_em).
--   B. `renovacao_eventos` (FK (renovacao_id, company_id) → renovacoes ON DELETE CASCADE) + índice.
--   C. `renovacao_dias` (PK company_id, dia) + CHECK estado + CHECKs de faixa.
--   D. `membro_ausencias` + CHECK(user_id <> substituto) + CHECK(ate >= de) + 2 FKs compostas → company_members.
--   E. `multicalculo_pedidos` + `politica_de_sessao` (CHECK in ('madrugada')) + `renovacao_id` (FK composta →
--      renovacoes) + índice parcial.
--   F. ck_mc_pedidos_opcoes e ck_mc_calculos_opcao ALARGADAS com 'anterior' e 'franquia_reduzida' (molde 20261006_04:
--      drop + add só se o texto ainda não admite; todo valor de hoje continua valendo).
--   G. RLS ligada nas 4 tabelas novas + policy de LEITURA por company_id do membro ativo; escrita só pelo backend
--      (service role): REVOKE insert/update/delete/truncate de anon e authenticated. COMMENTs.
--
-- VERIFY (read-only · esperado: 4 · 4 · 1 · 1 · 1 · 1 · 2 · 1 · 1 · 1 · 1 · 2 · 0):
--   select (select count(*) from pg_class where relnamespace='public'::regnamespace and relkind='r' and relrowsecurity
--             and relname in ('renovacoes','renovacao_eventos','renovacao_dias','membro_ausencias')) tabelas_com_rls,
--          (select count(*) from pg_policies where schemaname='public' and cmd='SELECT'
--             and tablename in ('renovacoes','renovacao_eventos','renovacao_dias','membro_ausencias')) policies_leitura,
--          (select count(*) from pg_constraint where conrelid='public.renovacoes'::regclass and conname='uq_renovacoes_item'
--             and pg_get_constraintdef(oid)='UNIQUE (company_id, sistema, codfil, nosnum, fimvig)') unique_item,
--          (select count(*) from pg_constraint where conname='ck_renovacoes_estado' and convalidated
--             and pg_get_constraintdef(oid) like '%''substituida''%' and pg_get_constraintdef(oid) like '%''registrada''%') ck_estado,
--          (select count(*) from pg_constraint where conname='ck_renovacoes_motivo' and convalidated) ck_motivo,
--          (select count(*) from pg_constraint where conname='ck_renovacoes_documento_mascarado' and convalidated) ck_doc,
--          (select count(*) from pg_indexes where schemaname='public'
--             and indexname in ('ix_renovacoes_company_estado','ix_renovacoes_company_calcular_em')) indices,
--          (select count(*) from pg_constraint where conrelid='public.renovacao_eventos'::regclass
--             and conname='fk_renovacao_eventos_renovacao' and confdeltype='c') fk_eventos_cascade,
--          (select count(*) from pg_constraint where conname='ck_membro_ausencias_outra_pessoa') ck_outra_pessoa,
--          (select count(*) from pg_constraint where conname='ck_mc_pedidos_politica_de_sessao') ck_politica,
--          (select count(*) from pg_constraint where conname='fk_mc_pedidos_renovacao') fk_pedido_renovacao,
--          (select count(*) from pg_constraint where conname in ('ck_mc_pedidos_opcoes','ck_mc_calculos_opcao')
--             and pg_get_constraintdef(oid) like '%''anterior''%' and pg_get_constraintdef(oid) like '%''franquia_reduzida''%'
--             and pg_get_constraintdef(oid) like '%''minima''%' and pg_get_constraintdef(oid) like '%''padrao''%') opcoes_alargadas,
--          (select count(*) from information_schema.role_table_grants where grantee in ('anon','authenticated')
--             and table_schema='public' and privilege_type in ('INSERT','UPDATE','DELETE','TRUNCATE')
--             and table_name in ('renovacoes','renovacao_eventos','renovacao_dias','membro_ausencias')) escrita_publica;
--
-- VERIFY comportamental (o DO desfaz o que testa — raise P0001 no fim do sub-bloco; NADA fica):
--   do $$
--   declare a uuid; r1 uuid; r text; res text[] := '{}';
--   begin
--     select id into a from public.companies where company_kind='client' order by created_at limit 1;
--     if a is null then raise exception 'VERIFY 20261013_01: falta uma corretora cliente'; end if;
--     begin
--       insert into public.renovacoes (company_id, sistema, codfil, nosnum, fimvig, estado)
--         values (a,'infocap',1,'999000001','2099-01-01','listada') returning id into r1;
--       res := res || 'listada=aceito'::text;
--       begin insert into public.renovacoes (company_id, sistema, codfil, nosnum, fimvig, estado)
--               values (a,'infocap',1,'999000001','2099-01-01','listada'); r := 'aceito';
--       exception when unique_violation then r := 'recusado'; end;  res := res || ('duplicada='||r)::text;
--       begin insert into public.renovacoes (company_id, sistema, codfil, nosnum, fimvig, estado)
--               values (a,'infocap',1,'999000002','2099-01-01','pendente'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('pendente_sem_motivo='||r)::text;
--       begin insert into public.renovacoes (company_id, sistema, codfil, nosnum, fimvig, estado, motivo)
--               values (a,'infocap',1,'999000003','2099-01-01','pendente','ramo_nao_cotado'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('pendente_com_motivo='||r)::text;
--       begin insert into public.renovacoes (company_id, sistema, codfil, nosnum, fimvig, estado)
--               values (a,'infocap',1,'999000004','2099-01-01','inventado'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('estado_inventado='||r)::text;
--       begin insert into public.renovacoes (company_id, sistema, codfil, nosnum, fimvig, estado, documento_mascarado)
--               values (a,'infocap',1,'999000005','2099-01-01','listada','000.000.000-00'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('documento_em_claro='||r)::text;
--       begin insert into public.renovacoes (company_id, sistema, codfil, nosnum, fimvig, estado, cliente_nome_curto)
--               values (a,'infocap',1,'999000006','2099-01-01','listada','Nome Sobrenome'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('nome_completo='||r)::text;
--       insert into public.renovacao_eventos (company_id, renovacao_id, de, para, por, motivo)
--         values (a, r1, null, 'listada', 'verify', null);
--       res := res || 'evento=aceito'::text;
--       begin insert into public.multicalculo_pedidos (company_id, origem, opcoes, corretoras, pedido_cifrado,
--                                                      politica_de_sessao, renovacao_id)
--               values (a,'auxiliar',array['anterior','franquia_reduzida','completa_mais']::text[],array[a],'x',
--                       'madrugada', r1); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('pedido_da_renovacao='||r)::text;
--       begin insert into public.multicalculo_pedidos (company_id, origem, opcoes, corretoras, pedido_cifrado,
--                                                      politica_de_sessao)
--               values (a,'auxiliar',array['padrao']::text[],array[a],'x','tarde'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('politica_inventada='||r)::text;
--       raise exception using errcode='P0001', message='desfaz';
--     exception when sqlstate 'P0001' then null;
--     end;
--     if res is distinct from array['listada=aceito','duplicada=recusado','pendente_sem_motivo=recusado',
--                                   'pendente_com_motivo=aceito','estado_inventado=recusado',
--                                   'documento_em_claro=recusado','nome_completo=recusado','evento=aceito',
--                                   'pedido_da_renovacao=aceito','politica_inventada=recusado']::text[] then
--       raise exception 'VERIFY 20261013_01 FALHOU: %', res;
--     end if;
--     raise notice 'VERIFY 20261013_01 OK: %', res;
--   end $$;
--
-- ROLLBACK (🔴 executar é decisão do Founder — MIGRATIONS-AUTHORITY §8.6; RECUSA se houver dado das tabelas novas ou
--           pedido/cálculo com as opções novas, que o CHECK estreitado não deixaria existir):
--   do $$ begin
--     if exists (select 1 from public.renovacoes) or exists (select 1 from public.membro_ausencias)
--        or exists (select 1 from public.multicalculo_pedidos where renovacao_id is not null
--                   or politica_de_sessao is not null or opcoes && array['anterior','franquia_reduzida']::text[])
--        or exists (select 1 from public.multicalculo_calculos where opcao in ('anterior','franquia_reduzida')) then
--       raise exception 'ROLLBACK 20261013_01 recusado: há dado da renovação — apagar dado é decisão do Founder';
--     end if;
--     alter table public.multicalculo_pedidos drop constraint if exists ck_mc_pedidos_opcoes;
--     alter table public.multicalculo_pedidos add constraint ck_mc_pedidos_opcoes
--       check (cardinality(opcoes) >= 1 and opcoes <@ array['padrao', 'economica', 'completa_mais', 'minima']::text[]);
--     alter table public.multicalculo_calculos drop constraint if exists ck_mc_calculos_opcao;
--     alter table public.multicalculo_calculos add constraint ck_mc_calculos_opcao
--       check (opcao in ('padrao', 'economica', 'completa_mais', 'minima', 'ajuste'));
--     alter table public.multicalculo_pedidos drop constraint if exists fk_mc_pedidos_renovacao;
--     alter table public.multicalculo_pedidos drop constraint if exists ck_mc_pedidos_politica_de_sessao;
--     drop index if exists public.ix_mc_pedidos_renovacao;
--     alter table public.multicalculo_pedidos drop column if exists renovacao_id;
--     alter table public.multicalculo_pedidos drop column if exists politica_de_sessao;
--     drop table if exists public.renovacao_eventos;
--     drop table if exists public.renovacao_dias;
--     drop table if exists public.membro_ausencias;
--     drop table if exists public.renovacoes;
--   end $$;
--
-- EXPAND-FIRST: sim (4 tabelas novas e vazias; 2 colunas NULÁVEIS no pedido; 2 CHECKs ALARGADAS, nunca estreitadas)
-- DESTRUTIVA:   não
-- LOCK:         ACCESS EXCLUSIVE breve em `multicalculo_pedidos` (add column nulável + CHECK + FK) e
--               `multicalculo_calculos` (troca da CHECK, que revalida as linhas — tabelas pequenas) — aplicar com
--               `set lock_timeout='5s'`.
-- ORDEM:        ANTES do código da 131-A ser implantado (o código grava em `renovacoes`; sem a tabela o passo falha
--               e nada sai no Agger — fail-closed).
-- =============================================================

-- -------------------------------------------------------------
-- A. renovacoes — a lista congelada e o estado de cada apólice que renova
-- -------------------------------------------------------------
create table if not exists public.renovacoes (
  id                  uuid primary key default gen_random_uuid(),
  company_id          uuid not null references public.companies(id) on delete cascade,
  sistema             text not null default 'infocap',
  codfil              integer not null default 1,
  nosnum              text not null,
  fimvig              date not null,
  ramo_sigla          text null,
  ramo_agger          integer null,
  seguradora_atual    text null,
  premio_atual        numeric(14,2) null,
  cliente_nome_curto  text null,
  documento_mascarado text null,
  documento_hmac      text null,
  dono_user_id        uuid null references public.users_v2(id) on delete set null,
  dono_motivo         text null,
  responsavel_user_id uuid null references public.users_v2(id) on delete set null,
  estado              text not null default 'listada',
  motivo              text null,
  pedido_id           uuid null,
  conta_agger_id      uuid null,
  conta_motivo        text null,
  proposta_ref        text null,
  calcular_em         date null,
  canario             boolean not null default false,
  criado_em           timestamptz not null default now(),
  atualizado_em       timestamptz not null default now(),
  versao              integer not null default 1
);

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'uq_renovacoes_item') then
    alter table public.renovacoes
      add constraint uq_renovacoes_item unique (company_id, sistema, codfil, nosnum, fimvig);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'uq_renovacoes_id_company') then
    alter table public.renovacoes add constraint uq_renovacoes_id_company unique (id, company_id);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_renovacoes_estado') then
    alter table public.renovacoes add constraint ck_renovacoes_estado check (estado in (
      -- ligados na 131-A
      'listada', 'pronta', 'pendente', 'calculando', 'calculada', 'falhou', 'aguardando_agger', 'apresentada',
      'enviada', 'substituida',
      -- reservados (nenhum escritor os grava nesta SPEC: a guarda é do código, `renovacao.py`)
      'vista', 'em_negociacao', 'recalculo', 'aceita', 'emissao_pendente', 'emitida', 'registrada', 'recusada',
      'perdida'));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_renovacoes_motivo') then
    alter table public.renovacoes add constraint ck_renovacoes_motivo
      check (estado not in ('pendente', 'falhou', 'perdida') or length(btrim(coalesce(motivo, ''))) > 0);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_renovacoes_documento_mascarado') then
    alter table public.renovacoes add constraint ck_renovacoes_documento_mascarado
      check (documento_mascarado is null or length(regexp_replace(documento_mascarado, '\D', '', 'g')) <= 2);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_renovacoes_documento_hmac') then
    alter table public.renovacoes add constraint ck_renovacoes_documento_hmac
      check (documento_hmac is null or documento_hmac ~ '^[0-9a-f]{64}$');
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_renovacoes_nome_curto') then
    alter table public.renovacoes add constraint ck_renovacoes_nome_curto
      check (cliente_nome_curto is null
             or (cliente_nome_curto !~ '\s' and length(cliente_nome_curto) between 1 and 40
                 and cliente_nome_curto !~ '\d'));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_renovacoes_sistema') then
    alter table public.renovacoes add constraint ck_renovacoes_sistema
      check (sistema in ('infocap', 'quiver', 'outro'));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_renovacoes_codfil') then
    alter table public.renovacoes add constraint ck_renovacoes_codfil check (codfil >= 1);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_renovacoes_nosnum') then
    alter table public.renovacoes add constraint ck_renovacoes_nosnum check (length(btrim(nosnum)) > 0);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_renovacoes_versao') then
    alter table public.renovacoes add constraint ck_renovacoes_versao check (versao >= 1);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'fk_renovacoes_pedido') then
    alter table public.renovacoes add constraint fk_renovacoes_pedido
      foreign key (pedido_id, company_id) references public.multicalculo_pedidos (id, company_id);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'fk_renovacoes_conta_agger') then
    alter table public.renovacoes add constraint fk_renovacoes_conta_agger
      foreign key (conta_agger_id, company_id) references public.portal_accounts (id, company_id);
  end if;
end $$;

create index if not exists ix_renovacoes_company_estado on public.renovacoes (company_id, estado);
create index if not exists ix_renovacoes_company_calcular_em on public.renovacoes (company_id, calcular_em);
create index if not exists ix_renovacoes_pedido on public.renovacoes (pedido_id) where pedido_id is not null;

-- -------------------------------------------------------------
-- B. renovacao_eventos — uma linha por transição (de, para, por, motivo)
-- -------------------------------------------------------------
create table if not exists public.renovacao_eventos (
  id           uuid primary key default gen_random_uuid(),
  company_id   uuid not null references public.companies(id) on delete cascade,
  renovacao_id uuid not null,
  de           text null,
  para         text not null,
  por          text not null,
  motivo       text null,
  dados        jsonb not null default '{}'::jsonb,
  criado_em    timestamptz not null default now()
);

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'fk_renovacao_eventos_renovacao') then
    alter table public.renovacao_eventos add constraint fk_renovacao_eventos_renovacao
      foreign key (renovacao_id, company_id) references public.renovacoes (id, company_id) on delete cascade;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_renovacao_eventos_dados') then
    alter table public.renovacao_eventos add constraint ck_renovacao_eventos_dados
      check (jsonb_typeof(dados) = 'object');
  end if;
end $$;

create index if not exists ix_renovacao_eventos_item
  on public.renovacao_eventos (company_id, renovacao_id, criado_em);

-- -------------------------------------------------------------
-- C. renovacao_dias — a medida do dia (a completude gravada pela conferência)
-- -------------------------------------------------------------
create table if not exists public.renovacao_dias (
  company_id                 uuid not null references public.companies(id) on delete cascade,
  dia                        date not null,
  estado                     text not null,
  esperadas                  integer null,
  calculadas                 integer null,
  pendentes                  integer null,
  falharam                   integer null,
  faltaram                   integer null,
  completude_pct             numeric(5,2) null,
  cotaveis                   integer null,
  calculadas_de_cotaveis_pct numeric(5,2) null,
  detalhes                   jsonb not null default '{}'::jsonb,
  atualizado_em              timestamptz not null default now(),
  primary key (company_id, dia)
);

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'ck_renovacao_dias_estado') then
    alter table public.renovacao_dias add constraint ck_renovacao_dias_estado
      check (estado in ('completo', 'incompleto', 'vermelho', 'sem_conexao'));
  end if;
  -- InfoCap fora: o dia é `sem_conexao` e as contagens ficam NULAS — nunca "0 renovações"
  if not exists (select 1 from pg_constraint where conname = 'ck_renovacao_dias_sem_conexao_sem_zero') then
    alter table public.renovacao_dias add constraint ck_renovacao_dias_sem_conexao_sem_zero
      check (estado <> 'sem_conexao' or (esperadas is null and completude_pct is null));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_renovacao_dias_faixas') then
    alter table public.renovacao_dias add constraint ck_renovacao_dias_faixas
      check ((completude_pct is null or completude_pct between 0 and 100)
             and (calculadas_de_cotaveis_pct is null or calculadas_de_cotaveis_pct between 0 and 100)
             and coalesce(esperadas, 0) >= 0 and coalesce(faltaram, 0) >= 0);
  end if;
end $$;

-- -------------------------------------------------------------
-- D. membro_ausencias — férias: o cálculo segue no Agger do dono, o AVISO vai ao substituto (D-131-08)
-- -------------------------------------------------------------
create table if not exists public.membro_ausencias (
  id                 uuid primary key default gen_random_uuid(),
  company_id         uuid not null references public.companies(id) on delete cascade,
  user_id            uuid not null,
  substituto_user_id uuid not null,
  de                 date not null,
  ate                date not null,
  criado_por         uuid null references public.users_v2(id) on delete set null,
  criado_em          timestamptz not null default now()
);

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'ck_membro_ausencias_outra_pessoa') then
    alter table public.membro_ausencias add constraint ck_membro_ausencias_outra_pessoa
      check (user_id <> substituto_user_id);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_membro_ausencias_periodo') then
    alter table public.membro_ausencias add constraint ck_membro_ausencias_periodo check (ate >= de);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'fk_membro_ausencias_membro') then
    alter table public.membro_ausencias add constraint fk_membro_ausencias_membro
      foreign key (user_id, company_id) references public.company_members (user_id, company_id) on delete cascade;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'fk_membro_ausencias_substituto') then
    alter table public.membro_ausencias add constraint fk_membro_ausencias_substituto
      foreign key (substituto_user_id, company_id) references public.company_members (user_id, company_id)
      on delete cascade;
  end if;
end $$;

create index if not exists ix_membro_ausencias_membro on public.membro_ausencias (company_id, user_id, de, ate);
create index if not exists ix_membro_ausencias_substituto on public.membro_ausencias (substituto_user_id, company_id);

-- -------------------------------------------------------------
-- E. multicalculo_pedidos — a política de sessão da madrugada e o vínculo com a renovação
-- -------------------------------------------------------------
alter table public.multicalculo_pedidos add column if not exists politica_de_sessao text null;
alter table public.multicalculo_pedidos add column if not exists renovacao_id uuid null;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'ck_mc_pedidos_politica_de_sessao') then
    alter table public.multicalculo_pedidos add constraint ck_mc_pedidos_politica_de_sessao
      check (politica_de_sessao is null or politica_de_sessao in ('madrugada'));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'fk_mc_pedidos_renovacao') then
    alter table public.multicalculo_pedidos add constraint fk_mc_pedidos_renovacao
      foreign key (renovacao_id, company_id) references public.renovacoes (id, company_id);
  end if;
end $$;

create index if not exists ix_mc_pedidos_renovacao on public.multicalculo_pedidos (renovacao_id)
  where renovacao_id is not null;

-- -------------------------------------------------------------
-- F. as opções da renovação (molde 20261006_04: só alarga, idempotente; a aspa impede casar um futuro `anterior_x`)
-- -------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_constraint
                  where conrelid = 'public.multicalculo_pedidos'::regclass and conname = 'ck_mc_pedidos_opcoes'
                    and pg_get_constraintdef(oid) like '%''anterior''%'
                    and pg_get_constraintdef(oid) like '%''franquia_reduzida''%') then
    alter table public.multicalculo_pedidos drop constraint if exists ck_mc_pedidos_opcoes;
    alter table public.multicalculo_pedidos add constraint ck_mc_pedidos_opcoes
      check (cardinality(opcoes) >= 1 and opcoes <@ array['padrao', 'economica', 'completa_mais', 'minima',
                                                          'anterior', 'franquia_reduzida']::text[]);
  end if;
  if not exists (select 1 from pg_constraint
                  where conrelid = 'public.multicalculo_calculos'::regclass and conname = 'ck_mc_calculos_opcao'
                    and pg_get_constraintdef(oid) like '%''anterior''%'
                    and pg_get_constraintdef(oid) like '%''franquia_reduzida''%') then
    alter table public.multicalculo_calculos drop constraint if exists ck_mc_calculos_opcao;
    alter table public.multicalculo_calculos add constraint ck_mc_calculos_opcao
      check (opcao in ('padrao', 'economica', 'completa_mais', 'minima', 'anterior', 'franquia_reduzida', 'ajuste'));
  end if;
end $$;

-- -------------------------------------------------------------
-- G. RLS: leitura pelo membro ATIVO da própria corretora; escrita só pelo backend (service role, que ignora a RLS —
--    por isso o filtro company_id mora no repositório `app/services/multicalculo/renovacao.py`, CLAUDE.md §7)
-- -------------------------------------------------------------
alter table public.renovacoes enable row level security;
alter table public.renovacao_eventos enable row level security;
alter table public.renovacao_dias enable row level security;
alter table public.membro_ausencias enable row level security;

revoke all on table public.renovacoes from anon;
revoke all on table public.renovacao_eventos from anon;
revoke all on table public.renovacao_dias from anon;
revoke all on table public.membro_ausencias from anon;
revoke insert, update, delete, truncate on table public.renovacoes from authenticated;
revoke insert, update, delete, truncate on table public.renovacao_eventos from authenticated;
revoke insert, update, delete, truncate on table public.renovacao_dias from authenticated;
revoke insert, update, delete, truncate on table public.membro_ausencias from authenticated;

do $$
declare t text;
begin
  foreach t in array array['renovacoes', 'renovacao_eventos', 'renovacao_dias', 'membro_ausencias'] loop
    if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = t
                     and policyname = t || '_leitura_da_corretora') then
      execute format(
        'create policy %I on public.%I for select to authenticated using (company_id in ('
        'select m.company_id from public.company_members m where m.user_id = auth.uid() and m.status = ''active''))',
        t || '_leitura_da_corretora', t);
    end if;
  end loop;
end $$;

comment on table public.renovacoes is
  'SPEC-131-A — a renovação de UMA apólice (a lista congelada do dia, por corretora). UNIQUE (company_id, sistema, '
  'codfil, nosnum, fimvig): o upsert nunca duplica; endosso que muda o fimvig = item novo e o velho `substituida`. '
  'O estado só muda pela máquina de app/services/multicalculo/renovacao.py (cada transição grava renovacao_eventos); '
  'os estados reservados existem no CHECK e nenhum escritor os grava nesta SPEC. Nunca telefone, nunca CPF/CNPJ em '
  'claro (só mascarado + HMAC), nome só o primeiro.';
comment on column public.renovacoes.estado is
  'ligados: listada · pronta · pendente · calculando · calculada · falhou · aguardando_agger · apresentada · enviada · '
  'substituida — reservados: vista · em_negociacao · recalculo · aceita · emissao_pendente · emitida · registrada · '
  'recusada · perdida. pendente/falhou/perdida exigem motivo (CHECK).';
comment on column public.renovacoes.calcular_em is
  'fimvig − antecedência (servicos.renovacao.antecedencia_dias). O passo calcular pega `pronta` com calcular_em <= dia '
  '(o atraso de ontem entra hoje).';
comment on column public.renovacoes.documento_mascarado is
  'CPF/CNPJ com no máximo os 2 últimos dígitos à vista (CHECK). O casamento é pelo documento_hmac '
  '(HMAC-SHA256 com MULTICALCULO_HMAC_KEY, o mesmo da porta).';
comment on table public.renovacao_eventos is
  'SPEC-131-A — uma linha por transição de estado de uma renovação: de, para, por (quem/qual passo), motivo.';
comment on table public.renovacao_dias is
  'SPEC-131-A — a medida do dia por corretora, gravada pela conferência das 05:30 (conferencia_da_renovacao.py), que '
  'relê a InfoCap de novo: completude = (calculadas + pendentes com motivo) ÷ esperadas; vermelho = a conferência '
  'achou renovação que a preparação esqueceu; sem_conexao = InfoCap fora (contagens NULAS, nunca zero).';
comment on table public.membro_ausencias is
  'SPEC-131-A (D-131-08) — ausência de um membro: no período, o cálculo segue no Agger do dono e o AVISO vai ao '
  'substituto (outra pessoa da mesma corretora).';
comment on column public.multicalculo_pedidos.politica_de_sessao is
  'SPEC-131-A — "madrugada": só a renovação das 02:00 a pede (madrugada.py); o motor só "Prossegue" sobre sessão '
  'aberta com ela e dentro das travas da SPEC §4.';
comment on column public.multicalculo_pedidos.renovacao_id is
  'SPEC-131-A — a renovação que originou este pedido (o estado da renovação é DERIVADO dos cálculos deste pedido).';
