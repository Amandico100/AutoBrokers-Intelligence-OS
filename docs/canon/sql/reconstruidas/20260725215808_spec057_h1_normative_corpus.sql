-- =============================================================
-- DDL RECONSTRUÍDO — NÃO É CAMINHO DE APLICAÇÃO
-- =============================================================
-- Versão no banco: 20260725215808  ·  nome: spec057_h1_normative_corpus
-- SPEC de origem:  SPEC-057 §Bloco H (corpus normativo)
-- Reconstruído em: 2026-08-08, pela SPEC-067 LOTE 0 item 12
-- Fonte:           catálogo do Postgres do projeto dcajcvlzcjbmyapmklil,
--                  lido por information_schema / pg_constraint / pg_indexes /
--                  pg_class / pg_trigger / pg_get_functiondef — read-only.
--
-- 🔴 PROIBIDO APLICAR ESTE ARQUIVO.
--    Ele mora em `docs/canon/sql/`, que a MIGRATIONS-AUTHORITY §1 declara
--    "material documental, nunca caminho de aplicação". Está aqui pelo motivo
--    do §6 regra 4: todo objeto do baseline precisa de dono documental.
--    A versão 20260725215808 JÁ ESTÁ aplicada em produção; reaplicar isto
--    repetiria DDL sobre tabelas com 35 e 29 linhas vivas.
--
-- POR QUE ELE EXISTE
-- ------------------
-- 📊 Medido em 08/08/2026: `normative_documents` e `normative_document_versions`
-- não têm arquivo `.sql` em `backend/supabase/migrations/` (grep por
-- `normative_documents`: zero acertos fora dos arquivos de `knowledge_cards`).
-- Elas são da classe SEM_ARQUIVO da MIGRATIONS-AUTHORITY §4: criadas por DDL
-- fora do repositório, com a versão registrada no banco.
--
-- ⚠️ CORREÇÃO DE UM ACHADO ANTERIOR, e ela importa mais que o arquivo.
-- Um levantamento anterior afirmou que estas tabelas "não têm versão em
-- supabase_migrations.schema_migrations, consulta por %normative%/%corpus%:
-- zero linhas". 📊 Isso é FALSO. A consulta, executada em 08/08/2026:
--
--     select version, name from supabase_migrations.schema_migrations
--      where name ilike '%normative%' or name ilike '%corpus%';
--       20260719175618  spec040_conduct_playbooks_cards   (pelo ilike '%cards%')
--       20260725215808  spec057_h1_normative_corpus       ← existe
--
-- A diferença é material. "Órfã sem versão" pediria uma versão nova, e criar
-- versão para objeto que já tem uma produz histórico duplicado — que é
-- exatamente o defeito que a MIGRATIONS-AUTHORITY existe para impedir. O que
-- falta é o ARQUIVO, não a versão. Este documento é o arquivo.
-- =============================================================


-- -------------------------------------------------------------
-- 1. normative_documents — a linhagem do documento
-- -------------------------------------------------------------
-- Uma linha por URL de origem (a UNIQUE é sobre `source_url`). É a linhagem,
-- não a versão: as versões vivem na tabela seguinte.

create table if not exists public.normative_documents (
  id                   uuid        not null default gen_random_uuid(),
  insurer_key          text        not null,
  insurer_name         text        not null,
  product_line         text        not null,
  doc_kind             text        not null,
  susep_process        text,
  title                text        not null,
  source_url           text        not null,
  version_label        text,
  effective_from       date,
  effective_until      date,
  status               text        not null default 'discovered',
  content_hash         text,
  byte_size            integer,
  chunk_count          integer     not null default 0,
  qdrant_collection    text,
  check_interval_days  integer     not null default 45,
  last_checked_at      timestamptz,
  next_check_at        timestamptz,
  last_change_at       timestamptz,
  fetch_error          text,
  fetch_attempts       integer     not null default 0,
  approved_at          timestamptz,
  approved_by          uuid,
  notes                text,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),

  constraint normative_documents_pkey   primary key (id),
  constraint normative_documents_url_uk unique (source_url),

  constraint normative_documents_doc_kind_check check (
    doc_kind = any (array['condicoes_gerais','condicoes_especiais',
                          'condicoes_particulares','manual_do_segurado',
                          'nota_tecnica','circular_susep','tabela_coberturas',
                          'glossario','regulamento'])),

  constraint normative_documents_status_check check (
    status = any (array['discovered','fetching','ingested','superseded',
                        'unreachable','rejected'])),

  constraint normative_documents_check_interval_days_check check (
    check_interval_days >= 1 and check_interval_days <= 365),

  -- "ingerido" tem de significar que existe conteúdo indexado. Sem isto o
  -- catálogo poderia afirmar presença de um documento que não responde nada.
  constraint normative_ingested_has_hash check (
    status <> 'ingested' or (content_hash is not null and chunk_count > 0)),

  constraint normative_vigencia_coerente check (
    effective_until is null or effective_from is null
    or effective_until >= effective_from)
);

create index if not exists normative_due_idx
  on public.normative_documents (next_check_at)
  where status = any (array['ingested','unreachable']);

create index if not exists normative_lookup_idx
  on public.normative_documents (insurer_key, product_line, doc_kind)
  where status = 'ingested';

create index if not exists normative_susep_idx
  on public.normative_documents (susep_process)
  where susep_process is not null;

alter table public.normative_documents enable row level security;

-- ⚠️ FATO, e é um risco registrado: RLS está LIGADA e há ZERO policies.
-- Para `anon` e `authenticated` isso equivale a negar tudo — o que aqui é o
-- comportamento certo, porque acervo normativo não tem dono e não é lido pelo
-- cliente. O backend usa `service_role`, que ignora RLS (CLAUDE.md §7): a
-- proteção real é o filtro no serviço, não a policy.


-- -------------------------------------------------------------
-- 2. normative_document_versions — cada captura, imutável
-- -------------------------------------------------------------

create table if not exists public.normative_document_versions (
  id              uuid        not null default gen_random_uuid(),
  document_id     uuid        not null,
  version         integer     not null,
  content_hash    text        not null,
  byte_size       integer,
  chunk_count     integer     not null default 0,
  storage_ref     text,
  excerpt         text,
  change_summary  text,
  fetched_at      timestamptz not null default now(),
  superseded_at   timestamptz,

  constraint normative_document_versions_pkey primary key (id),
  constraint normative_versions_uk unique (document_id, version),
  constraint normative_document_versions_document_id_fkey
    foreign key (document_id) references public.normative_documents(id)
    on delete cascade
);

alter table public.normative_document_versions enable row level security;

-- O guarda de append-only. Note o recorte: ele congela `content_hash`,
-- `version` e `fetched_at` — o QUE foi capturado e QUANDO. Deixa aberto
-- `superseded_at`, `storage_ref`, `excerpt` e `change_summary`, que são o que
-- se sabe DEPOIS sobre a mesma captura. É essa fresta que permite à SPEC-067
-- escrever a vigência e o endereço do arquivo sem tocar no que é imutável.
create or replace function public.normative_versions_append_only()
returns trigger
language plpgsql
set search_path to 'pg_catalog', 'public'
as $function$
BEGIN
  IF TG_OP = 'UPDATE' AND (
       NEW.content_hash IS DISTINCT FROM OLD.content_hash OR
       NEW.version      IS DISTINCT FROM OLD.version      OR
       NEW.fetched_at   IS DISTINCT FROM OLD.fetched_at) THEN
    RAISE EXCEPTION 'versao normativa e imutavel: registre uma nova';
  END IF;
  IF TG_OP = 'DELETE'
     AND coalesce(current_setting('app.normative_purge', true), 'off') <> 'on' THEN
    RAISE EXCEPTION 'DELETE em normative_document_versions exige app.normative_purge=on';
  END IF;
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $function$;

create trigger trg_normative_versions_append_only
  before delete or update on public.normative_document_versions
  for each row execute function public.normative_versions_append_only();


-- -------------------------------------------------------------
-- 3. VERIFY — o SQL que provou que este arquivo descreve o banco
-- -------------------------------------------------------------
-- Executado read-only em 08/08/2026 no projeto dcajcvlzcjbmyapmklil.
--
-- 3.1 colunas
--   select table_name, column_name, data_type, is_nullable, column_default
--     from information_schema.columns
--    where table_schema='public'
--      and table_name in ('normative_documents','normative_document_versions')
--    order by table_name, ordinal_position;
--   📊 27 colunas em normative_documents, 11 em normative_document_versions.
--
-- 3.2 constraints
--   select conrelid::regclass, conname, pg_get_constraintdef(oid)
--     from pg_constraint
--    where conrelid in ('public.normative_documents'::regclass,
--                       'public.normative_document_versions'::regclass);
--   📊 12 constraints, todas transcritas acima.
--
-- 3.3 índices
--   select tablename, indexname, indexdef from pg_indexes
--    where schemaname='public' and tablename like 'normative%';
--   📊 6 índices (3 vindos de pkey/unique + os 3 declarados acima).
--
-- 3.4 RLS e gatilhos
--   select relname, relrowsecurity,
--          (select count(*) from pg_policy where polrelid=c.oid) as policies
--     from pg_class c join pg_namespace n on n.oid=c.relnamespace
--    where n.nspname='public' and relname like 'normative%';
--   📊 normative_documents          rls=t  policies=0  triggers=0
--   📊 normative_document_versions  rls=t  policies=0  triggers=1
--
-- 3.5 estado dos dados no momento da reconstrução
--   📊 normative_documents ......................... 35 linhas
--   📊    com effective_from ....................... 22
--   📊    com effective_until ......................  0
--   📊    com version_label .......................   0
--   📊 normative_document_versions ................. 29 linhas
--   📊    version mínima 1, version máxima .........  1
--   📊    com storage_ref ..........................  0
--   📊    com superseded_at ........................  0
--
--   Ou seja: o encadeamento de versões existe em código
--   (`insurance_corpus.py:510-528`) e nunca rodou. Nenhum documento chegou à
--   segunda captura, então nenhuma anterior precisou ser fechada — e por isso
--   o defeito ficou invisível até agora.
--
-- 3.6 a versão está mesmo registrada
--   select version, name from supabase_migrations.schema_migrations
--    where version = '20260725215808';
--   📊 devolve 1 linha: 20260725215808 | spec057_h1_normative_corpus
-- =============================================================
