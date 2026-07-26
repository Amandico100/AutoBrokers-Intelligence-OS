-- =============================================================
-- MIGRATION: spec059_memory_fabric
-- SPEC:      SPEC-059 — Bloco A · Lote 4 da SPEC-052 (enxerto D1)
-- AUTOR:     Executor Opus                DATA: 2026-07-26
-- OBJETIVO:  dar objeto duravel a memoria da corretora e ao Knowledge
--            Candidate — o objeto comum de todas as fontes de aprendizado.
--
-- APPLY:     2 tabelas novas + indices + RLS + triggers de updated_at.
--            Nenhuma tabela existente e alterada.
-- VERIFY:    ver bloco VERIFY ao final.
-- ROLLBACK:  ver bloco ROLLBACK ao final.
--
-- EXPAND-FIRST: sim
-- DESTRUTIVA:   nao
--
-- POR QUE ESTAS DUAS E NAO MAIS
-- -----------------------------
-- `user_memories` e `session_summaries` JA EXISTEM e continuam sendo a
-- autoridade da memoria pessoal e da sessao. O que faltava era:
--
--   1. **memoria da corretora** — o que vale para a empresa, nao para a
--      pessoa. Hoje um fato aprendido com o dono se perde quando quem
--      pergunta e outro usuario da mesma corretora.
--   2. **Knowledge Candidate** — o objeto comum onde Destilador, Tecelao,
--      Sentinela, Garimpo e memoria depositam o que aprenderam, ANTES de
--      qualquer publicacao. Sem ele, cada fonte publicaria por conta propria,
--      que e exatamente o que a SPEC-052 §21 proibe.
--
-- Nao ha segundo motor de memoria: `memory_fabric.py` orquestra o
-- `MemoryService` que ja existe.
-- =============================================================

-- -------------------------------------------------------------
-- 1. company_memories — memoria da CORRETORA (nao da pessoa)
-- -------------------------------------------------------------
create table if not exists public.company_memories (
  id               uuid primary key default gen_random_uuid(),
  company_id       uuid not null references public.companies(id) on delete cascade,
  memory_key       text not null,
  category         text not null default 'operacao',
  statement        text not null,
  evidence         jsonb not null default '[]'::jsonb,
  confidence       numeric(4,3) not null default 0.500,
  source_kind      text not null default 'conversation',
  source_refs      jsonb not null default '[]'::jsonb,
  status           text not null default 'active',
  trust_tier       smallint not null default 4,
  occurrences      integer not null default 1,
  first_seen_at    timestamptz not null default now(),
  last_seen_at     timestamptz not null default now(),
  valid_until      timestamptz null,
  confirmed_by_user_id uuid null,
  confirmed_at     timestamptz null,
  superseded_by_id uuid null references public.company_memories(id) on delete set null,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  constraint company_memories_status_ck
    check (status in ('candidate','active','conflicted','superseded','revoked')),
  constraint company_memories_confidence_ck
    check (confidence >= 0 and confidence <= 1),
  constraint company_memories_tier_ck check (trust_tier between 0 and 5),
  -- Lei central 13 da SPEC-059: preferencia pessoal nao vira verdade da
  -- corretora sem confirmacao. Um fato declarado por uma pessoa entra como
  -- `candidate`; so vira `active` com confirmacao humana OU recorrencia.
  constraint company_memories_promocao_exige_prova_ck
    check (status <> 'active'
           or confirmed_by_user_id is not null
           or occurrences >= 2
           or trust_tier <= 3)
);

create unique index if not exists ux_company_memories_chave
  on public.company_memories (company_id, memory_key)
  where status in ('candidate','active','conflicted');

create index if not exists ix_company_memories_ativas
  on public.company_memories (company_id, status, last_seen_at desc);
create index if not exists ix_company_memories_validade
  on public.company_memories (valid_until) where status = 'active';

-- -------------------------------------------------------------
-- 2. knowledge_candidates — objeto comum de aprendizado (SPEC-052 §21)
-- -------------------------------------------------------------
create table if not exists public.knowledge_candidates (
  id                  uuid primary key default gen_random_uuid(),
  company_id          uuid null references public.companies(id) on delete cascade,
  scope               text not null default 'company',
  source_kind         text not null,
  source_ref          text null,
  candidate_type      text not null default 'procedure',
  title               text not null,
  statement_redacted  text not null,
  evidence            jsonb not null default '[]'::jsonb,
  source_count        integer not null default 1,
  confidence          numeric(4,3) not null default 0.500,
  trust_tier          smallint not null default 4,
  risk_level          text not null default 'low',
  status              text not null default 'draft',
  dedupe_hash         text not null,
  contradicts_id      uuid null references public.knowledge_candidates(id) on delete set null,
  pii_check           jsonb not null default '{}'::jsonb,
  reviewed_by_user_id uuid null,
  reviewed_at         timestamptz null,
  review_note         text null,
  published_ref       text null,
  valid_until         timestamptz null,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  constraint knowledge_candidates_scope_ck
    check (scope in ('personal','company','global')),
  constraint knowledge_candidates_status_ck
    check (status in ('draft','pending_review','approved','rejected',
                      'published','superseded','conflicted')),
  constraint knowledge_candidates_risk_ck
    check (risk_level in ('low','medium','high','critical')),
  constraint knowledge_candidates_confidence_ck
    check (confidence >= 0 and confidence <= 1),
  constraint knowledge_candidates_tier_ck check (trust_tier between 0 and 5),
  -- §18.5 / D7: candidato GLOBAL nao carrega tenant. Se carregasse, a
  -- anonimizacao seria decorativa — bastaria ler a coluna para saber de qual
  -- corretora veio o aprendizado.
  constraint knowledge_candidates_global_e_anonimo_ck
    check (scope <> 'global' or company_id is null),
  -- SPEC-052 §10.4: alto risco exige fonte oficial E humano responsavel.
  constraint knowledge_candidates_alto_risco_exige_humano_ck
    check (status not in ('approved','published')
           or risk_level not in ('high','critical')
           or reviewed_by_user_id is not null),
  -- §21: nenhuma fonte publica direto. Publicado exige aprovacao registrada.
  constraint knowledge_candidates_publicado_exige_aprovacao_ck
    check (status <> 'published' or reviewed_at is not null)
);

create unique index if not exists ux_knowledge_candidates_dedupe
  on public.knowledge_candidates (
    coalesce(company_id, '00000000-0000-0000-0000-000000000000'::uuid),
    scope, dedupe_hash)
  where status in ('draft','pending_review','approved','published','conflicted');

create index if not exists ix_knowledge_candidates_fila
  on public.knowledge_candidates (status, scope, created_at desc);
create index if not exists ix_knowledge_candidates_company
  on public.knowledge_candidates (company_id, status) where company_id is not null;

-- -------------------------------------------------------------
-- Triggers de updated_at
-- -------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array['company_memories','knowledge_candidates'] loop
    execute format('drop trigger if exists tg_%1$s_updated_at on public.%1$s', t);
    execute format(
      'create trigger tg_%1$s_updated_at before update on public.%1$s '
      'for each row execute function public.update_updated_at_column()', t);
  end loop;
end $$;

-- -------------------------------------------------------------
-- RLS — LIGADA, sem policy
-- -------------------------------------------------------------
alter table public.company_memories     enable row level security;
alter table public.knowledge_candidates enable row level security;

-- =============================================================
-- VERIFY  (read-only)
-- =============================================================
-- select c.relname, c.relrowsecurity,
--        (select count(*) from pg_policies p
--          where p.schemaname='public' and p.tablename=c.relname) policies
--   from pg_class c join pg_namespace n on n.oid=c.relnamespace
--  where n.nspname='public' and c.relname in ('company_memories','knowledge_candidates');
--  -- esperado: 2 linhas, relrowsecurity=true, policies=0
--
-- select conname from pg_constraint where conname in (
--   'knowledge_candidates_global_e_anonimo_ck',
--   'knowledge_candidates_alto_risco_exige_humano_ck',
--   'knowledge_candidates_publicado_exige_aprovacao_ck',
--   'company_memories_promocao_exige_prova_ck') order by 1;
--  -- esperado: 4 linhas
--
-- -- candidato global com tenant deve FALHAR:
-- insert into knowledge_candidates (company_id, scope, source_kind, title,
--   statement_redacted, dedupe_hash)
-- values ((select id from companies limit 1), 'global', 'teste', 't', 't', 'h1');
--
-- =============================================================
-- ROLLBACK
-- =============================================================
-- drop table if exists public.knowledge_candidates cascade;
-- drop table if exists public.company_memories cascade;
-- =============================================================
