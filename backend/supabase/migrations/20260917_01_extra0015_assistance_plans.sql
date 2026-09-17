-- =============================================================
-- MIGRATION: a base GLOBAL de planos e servicos de assistencia
-- SPEC:      SPEC-EXTRA-001.5 — BLOCO A (unidade A, fatia 1) · §5.2 e §11.1
-- AUTOR:     builder Opus 5 xhigh (AAA FAST v12.2)      DATA: 2026-09-17
-- OBJETIVO:  o agente passa a ter ONDE guardar o que cada plano cobre, com a
--            FONTE (documento + pagina + trecho) obrigatoria PELO BANCO.
--
-- APPLY:     cria `insurer_assistance_plans` e `insurer_assistance_services`
--            (aditiva, `IF NOT EXISTS`, nenhum objeto existente e tocado),
--            os 3 indices de §11.1, RLS ligada sem policy (o padrao das
--            tabelas globais deste projeto — ver MEDICAO 3 abaixo).
-- VERIFY:    SQL read-only no fim deste arquivo (secao VERIFY).
-- ROLLBACK:  -- filha primeiro, por causa da FK `plano_id`:
--            drop table if exists public.insurer_assistance_services;
--            drop table if exists public.insurer_assistance_plans;
--            -- 🔴 o rollback APAGA a curadoria humana. Em ambiente com linhas
--            --    publicadas, exportar as duas tabelas ANTES:
--            --    select count(*) from insurer_assistance_services
--            --     where curadoria = 'publicado';   -- > 0 ⇒ exportar antes
--            --    Trabalho humano perdido nao volta com `git revert`.
--
-- EXPAND-FIRST: sim — so cria. Nenhum DROP, nenhum ALTER, nenhum backfill.
-- DESTRUTIVA:   nao
--
-- =============================================================
-- 📊 AS MEDICOES QUE DECIDIRAM ESTE DDL (17/09/2026, banco de producao,
--    so SELECT — cada uma com o comando ao lado, protocolo §0.4)
--
-- MEDICAO 1 · as tabelas NAO existem ainda
--    select to_regclass('public.insurer_assistance_plans'),
--           to_regclass('public.insurer_assistance_services');
--    -> (None, None)
--
-- MEDICAO 2 · `revisado_por` NAO ganha FK — e a irma explica por que
--    A curadoria do DOCUMENTO ja existe ao lado, em `normative_documents`:
--      select column_name, data_type from information_schema.columns
--       where table_name='normative_documents'
--         and column_name in ('approved_by','approved_at');
--      -> approved_by uuid · approved_at timestamptz
--      select count(*) from pg_constraint
--       where conrelid='public.normative_documents'::regclass and contype='f';
--      -> 0   (nenhuma FK — `approved_by` e uuid solto)
--    `users_v2` existe e recebe 9 FKs de outras tabelas:
--      select count(*) from pg_constraint
--       where confrelid='public.users_v2'::regclass and contype='f';   -> 9
--    🔴 Mesmo assim `revisado_por` fica SEM FK, de proposito e escrito:
--    estas tabelas sao GLOBAIS (D-PILOTO-01) e `users_v2` e por corretora.
--    Uma FK daqui para la penduraria a base global na vida de um usuario de
--    UMA corretora: apagar esse usuario com RESTRICT travaria o apagamento,
--    e com CASCADE apagaria linha curada que serve TODAS. O par correto e o
--    da tabela irma, que ja resolveu isto assim.
--
-- MEDICAO 3 · RLS ligada, ZERO policy — e isso NAO e esquecimento
--      select relrowsecurity from pg_class where oid=<t>::regclass;
--      select count(*) from pg_policy where polrelid=<t>::regclass;
--    -> normative_documents         RLS True · policies 0
--    -> normative_document_versions RLS True · policies 0
--    -> portals                     RLS True · policies 0
--    -> ura_maps                    RLS True · policies 0
--    As quatro tabelas GLOBAIS ja vivas do projeto seguem o mesmo padrao: RLS
--    ligada e NENHUMA policy, isto e, ninguem le pelo `anon`/`authenticated` e
--    so o service role (que a ignora) le. O backend le com service role
--    (CLAUDE.md §7) e o filtro de verdade esta no codigo. Ligar uma policy de
--    leitura para `authenticated` AQUI abriria a base por um caminho que as
--    quatro irmas nao abrem — um segundo caminho de acesso ao mesmo dado
--    (CLAUDE.md §5).
--    ⚠️ Consequencia declarada: nenhum cliente PostgREST le estas tabelas
--    direto; quem le e o backend, por `assistance_plans_base.py`.
--
-- MEDICAO 4 · o corpus tem seguradora fora do censo da carteira, e tem tambem
--    o que NAO e seguradora:
--      select distinct insurer_key from normative_documents order by 1;
--      -> allianz azul bradesco hdi mapfre porto susep tokio yelum
--    `hdi` esta em `_INSURER_ALIASES` e fora das 61 siglas da carteira; `susep`
--    e o REGULADOR, nao uma seguradora. Por isso `insurer_key` aqui e text com
--    CHECK de FORMA (minusculas/digitos/_), e QUEM e seguradora e decidido no
--    contrato de escrita (`assistance_plans_base.chave_de_conhecimento`), que
--    usa `set(_INSURER_ALIASES.values())` — a lista que o proprio codigo
--    declara ser "a lista de quem E seguradora" (corridor_playbooks.py:8195).
--    ⚠️ CHECK de forma, nunca de lista: uma lista de seguradoras congelada no
--    banco vira a 2a fonte de verdade e diverge do codigo no primeiro alias
--    novo. O banco recusa LIXO ("Seguradora XYZ", vazio, maiuscula); quem
--    recusa DESCONHECIDA e o contrato, que le a lista viva.
-- =============================================================

-- -------------------------------------------------------------
-- O PLANO: o que a seguradora vende, e em que nivel
-- -------------------------------------------------------------
create table if not exists public.insurer_assistance_plans (
    id              uuid primary key default gen_random_uuid(),

    insurer_key     text        not null,
    ramo            text        not null,
    produto         text        not null,
    plano           text        not null,
    nivel           integer     not null,

    vigencia_inicio date        not null,
    vigencia_fim    date        null,
    susep_process   text        null,

    documento_id    uuid        not null
        references public.normative_documents (id) on delete restrict,
    pagina          integer     not null,

    confianca       text        not null,
    curadoria       text        not null default 'rascunho',
    revisado_por    uuid        null,
    revisado_em     timestamptz null,

    content_hash    text        not null,

    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),

    -- 🔴 dois planos no mesmo nivel, no mesmo produto, e erro de curadoria:
    --    "existe plano acima?" deixaria de ter resposta unica.
    constraint uq_iap_plano  unique (insurer_key, ramo, produto, plano, vigencia_inicio),
    constraint uq_iap_nivel  unique (insurer_key, ramo, produto, nivel, vigencia_inicio),

    -- a fonte do PLANO, pelo banco (o irmao do `servico_tem_fonte`)
    constraint plano_tem_fonte check (
        documento_id is not null and pagina is not null and pagina >= 1),
    -- publicar e ato humano: sem revisor, nao publica
    constraint plano_publicado_foi_revisado check (
        curadoria <> 'publicado'
        or (revisado_por is not null and revisado_em is not null)),

    constraint plano_nivel_positivo  check (nivel >= 1),
    constraint plano_curadoria_valida check (
        curadoria in ('rascunho', 'proposto', 'publicado', 'rejeitado')),
    constraint plano_confianca_valida check (confianca in ('alta', 'media', 'baixa')),
    constraint plano_vigencia_coerente check (
        vigencia_fim is null or vigencia_fim >= vigencia_inicio),
    -- forma da chave, nunca lista (MEDICAO 4)
    constraint plano_insurer_key_canonica check (insurer_key ~ '^[a-z0-9_]{2,40}$'),
    constraint plano_ramo_canonico        check (ramo ~ '^[a-z0-9_]{2,40}$')
);

-- -------------------------------------------------------------
-- A LINHA: o que o plano faz, com FONTE OBRIGATORIA
-- -------------------------------------------------------------
create table if not exists public.insurer_assistance_services (
    id             uuid primary key default gen_random_uuid(),
    plano_id       uuid not null
        references public.insurer_assistance_plans (id) on delete cascade,

    servico        text    not null,
    coberto        text    not null,

    limite_valor   numeric null,
    limite_unidade text    null,
    limite_texto   text    null,
    carencia_dias  integer null,
    condicao       text    null,

    documento_id   uuid    not null
        references public.normative_documents (id) on delete restrict,
    pagina         integer not null,
    trecho_hash    text    not null,

    confianca      text    not null,
    curadoria      text    not null default 'rascunho',
    revisado_por   uuid        null,
    revisado_em    timestamptz null,

    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now(),

    constraint uq_ias_servico unique (plano_id, servico),

    -- 🔴 OS TRES CHECKS DE §5.2 — os nomes sao contrato: os guardas M-A2/M-A4
    --    e a MUTACAO A os chamam pelo nome.
    constraint servico_tem_fonte check (
        documento_id is not null
        and pagina is not null and pagina >= 1
        and trecho_hash is not null and length(trecho_hash) = 64),
    constraint servico_publicado_foi_revisado check (
        curadoria <> 'publicado'
        or (revisado_por is not null and revisado_em is not null)),
    -- 💭 `limite_valor=200` sem unidade vira "200 dias de carro reserva" na
    --    cabeca de quem le. Pequeno e caro.
    constraint limite_tem_unidade check (
        limite_valor is null or limite_unidade is not null),

    constraint servico_coberto_valido check (coberto in ('sim', 'nao', 'condicionado')),
    constraint servico_curadoria_valida check (
        curadoria in ('rascunho', 'proposto', 'publicado', 'rejeitado')),
    constraint servico_confianca_valida check (confianca in ('alta', 'media', 'baixa')),
    constraint servico_limite_unidade_valida check (
        limite_unidade is null
        or limite_unidade in ('km', 'dias', 'acionamentos_ano', 'reais', 'unidades')),
    constraint servico_carencia_nao_negativa check (
        carencia_dias is null or carencia_dias >= 0),
    -- `servico` e CHAVE NOSSA, nao texto livre (§5.2). O vocabulario mora em
    -- docs/canon/providers/susep/servicos-de-assistencia.json; o banco guarda
    -- so a FORMA — a lista viva e do arquivo, para nao haver duas.
    constraint servico_chave_canonica check (servico ~ '^[a-z0-9_]{3,40}$')
);

-- -------------------------------------------------------------
-- Os tres indices de §11.1
-- -------------------------------------------------------------
create index if not exists ix_iap_chave
    on public.insurer_assistance_plans (insurer_key, ramo, produto, nivel);
create index if not exists ix_ias_servico
    on public.insurer_assistance_services (plano_id, servico);
create index if not exists ix_ias_curadoria
    on public.insurer_assistance_services (curadoria)
 where curadoria <> 'publicado';

-- -------------------------------------------------------------
-- RLS: ligada, sem policy — o padrao das 4 tabelas globais (MEDICAO 3)
-- -------------------------------------------------------------
alter table public.insurer_assistance_plans    enable row level security;
alter table public.insurer_assistance_services enable row level security;

-- -------------------------------------------------------------
-- A tabela nao tem dono, e isso fica escrito NO BANCO
-- -------------------------------------------------------------
comment on table public.insurer_assistance_plans is
    'GLOBAL — D-PILOTO-01. Planos de assistencia por seguradora. NAO tem company_id: '
    'o que a apolice da seguradora cobre e o mesmo para toda corretora. '
    'Escrita so por assistance_plans_base.py (service role).';
comment on table public.insurer_assistance_services is
    'GLOBAL — D-PILOTO-01. Linhas de servico com FONTE OBRIGATORIA (documento + pagina + '
    'trecho_hash) e curadoria com revisor humano para publicar. NAO tem company_id. '
    'Escrita so por assistance_plans_base.py (service role).';
comment on column public.insurer_assistance_services.trecho_hash is
    'sha256 (64 hex) do trecho NORMALIZADO que sustenta a linha. O trecho CRU nao e '
    'copiado: a fonte e o PDF arquivado. Conferido por assistance_plans_base.conferir_pagina.';
comment on column public.insurer_assistance_plans.insurer_key is
    'Chave canonica de CONHECIMENTO — normalize_insurer_key(x, para="conhecimento"). '
    'NUNCA para="corredor": aquela aplica _OPERADO_POR e arquivaria a regra do Itau sob Porto.';

-- =============================================================
-- VERIFY (read-only — a saida vai COLADA no relatorio)
-- =============================================================
-- V1 · os tres CHECKs nomeados da tabela de servicos existem
--   select conname from pg_constraint
--    where conrelid='public.insurer_assistance_services'::regclass and contype='c'
--      and conname in ('servico_tem_fonte','servico_publicado_foi_revisado','limite_tem_unidade')
--    order by conname;
--   -- esperado: as 3
--
-- V2 · 🔴 a base NAO TEM DONO (D-PILOTO-01)
--   select count(*) from information_schema.columns
--    where table_schema='public'
--      and table_name in ('insurer_assistance_plans','insurer_assistance_services')
--      and column_name in ('company_id','user_id','owner_user_id');
--   -- 🔴 esperado: 0. Maior que 0 REPROVA o gate.
--
-- V2b · CONTROLE de V2: a consulta CONSEGUE achar essas colunas noutra tabela
--   select count(*) from information_schema.columns
--    where table_schema='public' and table_name='tool_invocations'
--      and column_name in ('company_id','user_id','owner_user_id');
--   -- esperado: > 0 — senao V2 passa por vacuo
--
-- V3 · os dois UNIQUE do plano e o da linha
--   select conname, pg_get_constraintdef(oid) from pg_constraint
--    where conrelid in ('public.insurer_assistance_plans'::regclass,
--                       'public.insurer_assistance_services'::regclass)
--      and contype='u' order by conname;
--   -- esperado: uq_iap_nivel · uq_iap_plano · uq_ias_servico
--
-- V4 · as FKs e o ON DELETE de cada uma
--   select conname, pg_get_constraintdef(oid) from pg_constraint
--    where conrelid in ('public.insurer_assistance_plans'::regclass,
--                       'public.insurer_assistance_services'::regclass)
--      and contype='f' order by conname;
--   -- esperado: documento_id -> normative_documents ON DELETE RESTRICT (nas duas)
--   --           plano_id     -> insurer_assistance_plans ON DELETE CASCADE
--
-- V5 · os tres indices
--   select indexname from pg_indexes where schemaname='public'
--    and indexname in ('ix_iap_chave','ix_ias_servico','ix_ias_curadoria') order by 1;
--
-- V6 · AS INSERCOES ADVERSARIAIS — rodadas em BEGIN … ROLLBACK, TEM de falhar:
--   (a) documento_id NULL                 -> not_null_violation
--   (b) pagina = 0                        -> check_violation `servico_tem_fonte`
--   (c) curadoria='publicado' sem revisor  -> `servico_publicado_foi_revisado`
--   (d) limite_valor sem limite_unidade    -> `limite_tem_unidade`
--   (e) trecho_hash com 63 chars           -> `servico_tem_fonte`
--   (f) CONTROLE: a linha COMPLETA e valida -> ACEITA
-- =============================================================
