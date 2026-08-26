-- =============================================================
-- MIGRATION: spec087_blocoA_tela_cega
-- SPEC:      SPEC-087 — BLOCO A (a tela cega vira fila)
-- AUTOR:     execução Opus 5             DATA: 2026-08-26
-- OBJETIVO:  quando a seguradora manda uma tela que o corredor não sabe
--            responder, o produto passa a SABER disso.
--
-- APPLY:     cria `tela_cega` — fila de trabalho, não tabela de log.
-- VERIFY:    o bloco VERIFY no fim deste arquivo (SQL executável).
-- ROLLBACK:  o bloco ROLLBACK no fim deste arquivo.
--
-- EXPAND-FIRST: sim  (só adiciona)
-- DESTRUTIVA:   não
-- =============================================================
--
-- 📊 A RAZÃO, MEDIDA EM 26/08/2026 rodando `match_ura_step` sobre o corpus
-- versionado de telas reais — casamento MAIS GENEROSO possível (14 playbooks ×
-- 76 subserviços), então o número é PISO:
--
--     1.696 telas distintas em 10 seguradoras
--       378 CEGAS ................ 22,3%
--        27 delas são MENU (≥2 opções numeradas) — exigem resposta
--
--     zurich  auto        135/207  65,2%   🔴 a pior medida
--     yelum   auto         55/195  28,2%
--     allianz residencial  45/195  23,1%
--
-- ⚠️ **Uma em cada quatro telas que a seguradora manda, o corredor não conhece.**
--
-- 🔴 NÃO É TABELA DE LOG. É FILA DE TRABALHO: cada linha é uma tela que alguém
-- vai transformar em passo. O contador é o que ordena a fila.

create table if not exists public.tela_cega (
  id                   uuid        primary key default gen_random_uuid(),

  -- 🔴 `company_id` EXISTE AQUI, e a diferença para `route_drift` é o produto.
  --
  -- ⚠️ `route_drift` e `playbook_overlays` são globais de propósito: o Atlas é
  -- um só, e o mapa da URA é o mesmo para todas as corretoras. **Esta tabela
  -- não é mapa: é FILA DE TRABALHO DE UMA CORRETORA** — quem transforma a tela
  -- em passo trabalha para ela, e a contagem que ordena a fila é a dela.
  --
  -- ⛔ E o texto aqui vem MASCARADO (BLOCO C), então nem o conteúdo atravessa.
  company_id           uuid        not null references public.companies(id) on delete cascade,

  insurer_key          text        not null,
  ramo                 text        not null default 'todos',
  playbook_ref         text,

  -- ⛔ MASCARADO NA ORIGEM — `redaction_service.redigir`, BLOCO C.
  -- Escrever cru e mascarar depois é criar o vazamento e tapá-lo.
  texto_mascarado      text        not null,

  -- A chave da dedupe: md5 do texto NORMALIZADO (o mesmo `_norm` do casador).
  -- ⚠️ Normalizado, não cru: o mesmo menu com um espaço a mais é a MESMA tela,
  -- e sem isso a fila vira ruído em um dia.
  hash_normalizado     text        not null,

  -- 🔴 São os que mais doem: a URA pergunta e o corredor não sabe responder.
  e_menu               boolean     not null default false,

  visto_em             timestamptz not null default now(),
  visto_quantas_vezes  integer     not null default 1,

  -- 'aberta' | 'virou_passo' | 'ignorada'
  status               text        not null default 'aberta',
  created_at           timestamptz not null default now(),

  -- 🔴 O CHECK, com os valores ESCRITOS AQUI para quem lê a migration não
  -- precisar adivinhar — e o teste desta SPEC TENTA gravar um valor inválido
  -- exigindo que o banco RECUSE.
  --
  -- ⚠️ Na SPEC-093 a SPEC pediu `destravado_por_humano`, o CHECK não tinha, e
  -- isso só foi descoberto no meio da execução.
  constraint ck_tela_cega_status
    check (status in ('aberta', 'virou_passo', 'ignorada')),
  constraint ck_tela_cega_vezes
    check (visto_quantas_vezes >= 1)
);

comment on table public.tela_cega is
  'SPEC-087 BLOCO A - fila de telas de URA que nenhum passo do corredor casa. '
  'Fila de TRABALHO, nao log: cada linha vira um passo. O texto vem MASCARADO.';

-- 🔴 A DEDUPE. É ela que torna a fila útil: a mesma tela chega dezenas de vezes,
-- e sem isto a fila vira ruído em um dia.
--
-- ⚠️ POR CORRETORA: a mesma tela vista pela Resulta e pela AutoFleet são duas
-- linhas de fila, porque são dois trabalhos — e a contagem de cada uma é a
-- prioridade dela.
create unique index if not exists uq_tela_cega_chave
  on public.tela_cega (company_id, insurer_key, ramo, hash_normalizado);

-- 📊 É o contador que ordena a fila: a tela vista 40 vezes vale mais que a
-- vista uma.
create index if not exists ix_tela_cega_fila
  on public.tela_cega (company_id, status, visto_quantas_vezes desc, visto_em desc);

create index if not exists ix_tela_cega_menu
  on public.tela_cega (company_id, e_menu, status)
  where e_menu = true;

-- -------------------------------------------------------------
-- RLS — LIGADA, sem policy (nega anon/authenticated; service role passa).
-- Mesma escolha das 14 tabelas da SPEC-059 e da `saudacoes_enviadas` da 093.
-- ⚠️ `CLAUDE.md` §7: o backend usa service role, então RLS sem policy NÃO
-- protege contra erro de filtro no código. O filtro por `company_id` no
-- repository é a trava real; isto é a rede.
-- -------------------------------------------------------------
alter table public.tela_cega enable row level security;

-- =============================================================
-- VERIFY  (read-only — rodar DEPOIS do APPLY)
-- =============================================================
-- 1) a tabela existe, com RLS ligada e zero policy:
--
-- select c.relname, c.relrowsecurity,
--        (select count(*) from pg_policies p
--          where p.schemaname='public' and p.tablename=c.relname) policies
--   from pg_class c join pg_namespace n on n.oid=c.relnamespace
--  where n.nspname='public' and c.relname='tela_cega';
--  -- esperado: 1 linha, relrowsecurity=true, policies=0
--
-- 2) o CHECK do status aceita EXATAMENTE três valores:
--
-- select conname, pg_get_constraintdef(oid) from pg_constraint
--  where conrelid='public.tela_cega'::regclass and contype='c' order by 1;
--  -- esperado: ck_tela_cega_status  CHECK (status IN ('aberta','virou_passo','ignorada'))
--  --           ck_tela_cega_vezes   CHECK (visto_quantas_vezes >= 1)
--
-- 3) 🔴 O CHECK CONSEGUE RECUSAR (§9.3). Em transação, desfeita:
--
-- begin;
--   insert into public.tela_cega (company_id, insurer_key, texto_mascarado,
--                                 hash_normalizado, status)
--   select id, 'allianz', 'x', 'h1', 'inventado' from public.companies limit 1;
-- rollback;
--  -- esperado: erro 23514. Se passar, o CHECK não guarda nada.
--
-- 4) o UNIQUE da dedupe existe:
--
-- select indexname, indexdef from pg_indexes
--  where schemaname='public' and tablename='tela_cega' order by 1;
--  -- esperado: uq_tela_cega_chave UNIQUE
--  --           (company_id, insurer_key, ramo, hash_normalizado)
--
-- 5) a FK de corretora, com ON DELETE CASCADE:
--
-- select conname, pg_get_constraintdef(oid) from pg_constraint
--  where conrelid='public.tela_cega'::regclass and contype='f';
--  -- esperado: FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
--
-- =============================================================
-- ROLLBACK
-- =============================================================
-- ⚠️ Apaga a fila de trabalho. Só com decisão explícita do Founder
-- (`CLAUDE.md` §8, proibição 6).
--
-- drop table if exists public.tela_cega;
