-- =============================================================
-- MIGRATION: 20260930_02_spec122_cerebro_modos
-- SPEC:      SPEC-122 — F3 · o cérebro V2 em MODO SOMBRA
-- AUTOR:     builder F2+F3 (Opus 5.5 xhigh)      DATA: 2026-09-30
-- OBJETIVO:  a CHAVE governada que diz, por corretora × seguradora × ramo, se o
--            cérebro V2 roda em SOMBRA (decide, não envia, a divergência vai à
--            linha do tempo) — ou não roda (`off`, o padrão: sem linha = off).
--
-- APPLY:     cria `public.cerebro_modos` (vazia), RLS ligada sem policy, CHECK que
--            só aceita `off` e `sombra` — o `on` é RECUSADO pelo próprio banco,
--            com a razão no nome da constraint e no COMMENT.
-- VERIFY:    o bloco VERIFY no fim deste arquivo (SQL executável, read-only).
-- ROLLBACK:  o bloco ROLLBACK no fim deste arquivo.
--
-- EXPAND-FIRST: sim  (só adiciona; nenhum dado existente muda)
-- DESTRUTIVA:   não
-- =============================================================
--
-- 📊 POR QUE EXISTE (BLOCO 0 + bancada da SPEC-122, 30/09/2026):
--    a bancada do cérebro do acionamento mediu 3 braços × variantes em 32
--    armadilhas reais. NENHUMA variante passou G1 (erro grave zero); a melhor
--    (V2: saída estruturada + contexto + proibições em código) fez 4 graves.
--    Então o que vai à seguradora NÃO muda, e a V2 só pode rodar AO LADO, em
--    sombra, para acumular a medição que a regra de ligar da proposta exige
--    ("2 semanas ou 50 telas reais sem erro grave").
--
-- 🔴 POR QUE UMA TABELA, E NÃO ENV NEM O CATÁLOGO DE CORREDORES:
--    · env não é autoridade (CLAUDE.md §5) e não sabe de corretora;
--    · o catálogo de corredores (`corridor_playbooks.py`) é código: ligar a
--      sombra exigiria um deploy, e quem liga é o Founder, pela caixa dele;
--    · nenhuma tabela existente guarda configuração por seguradora/ramo DO
--      CÉREBRO (`ura_maps` é versão de mapa; `playbook_overlays` é passo do
--      Alfaiate; `llm_papeis` é modelo por papel, sem seguradora).
--
-- 🔴 POR CORRETORA: a sombra custa uma chamada de modelo por tela da fase
--    humana, e o custo vai ao ledger (`token_usage_logs`, service_type
--    `cerebro_sombra`) na conta DELA. Ligar para uma não liga para outra.

create table if not exists public.cerebro_modos (
  company_id   uuid        not null references public.companies(id) on delete cascade,
  insurer_key  text        not null,
  -- `todos` vale para todos os ramos da seguradora; um ramo explícito vence.
  ramo         text        not null default 'todos',
  modo         text        not null default 'off',
  motivo       text,
  ligado_por   text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  constraint pk_cerebro_modos primary key (company_id, insurer_key, ramo),
  -- ⛔ O `on` (a V2 decidindo o que vai à seguradora) NÃO existe aqui: a bancada
  --    não aprovou. O nome da constraint é a mensagem que quem tentar vai ler.
  constraint ck_cerebro_modos_on_recusado_a_bancada_122_nao_aprovou
    check (modo in ('off', 'sombra')),
  constraint ck_cerebro_modos_insurer_minusculo
    check (insurer_key = lower(insurer_key) and length(insurer_key) between 2 and 40),
  constraint ck_cerebro_modos_ramo_minusculo
    check (ramo = lower(ramo) and length(ramo) between 2 and 40)
);

comment on table public.cerebro_modos is
  'SPEC-122 F3 — a chave do cérebro V2 por corretora × seguradora × ramo: off (padrão; sem linha = off) ou sombra (decide, NÃO envia; a divergência vai a work_events cerebro.sombra). O modo on está RECUSADO: a bancada da SPEC-122 (30/09/2026) não aprovou nenhuma variante (G1: zero erro grave; a V2 teve 4 em 32 armadilhas).';
comment on column public.cerebro_modos.modo is
  'off | sombra. on é recusado pela constraint ck_cerebro_modos_on_recusado_a_bancada_122_nao_aprovou e pelo código (acao_do_cerebro.validar_modo).';

-- -------------------------------------------------------------
-- RLS — LIGADA, sem policy (nega anon/authenticated; service role passa).
-- Mesma escolha de `tela_cega` (SPEC-087). ⚠️ CLAUDE.md §7: o filtro real é o
-- `company_id` no código (`acao_do_cerebro._ler_chaves`); isto é a rede.
-- -------------------------------------------------------------
alter table public.cerebro_modos enable row level security;
revoke all on table public.cerebro_modos from anon, authenticated;

-- =============================================================
-- VERIFY  (read-only — rodar DEPOIS do APPLY)
-- =============================================================
-- 1) a tabela existe, vazia, com RLS ligada e zero policy:
--
-- select c.relname, c.relrowsecurity,
--        (select count(*) from pg_policies p
--          where p.schemaname='public' and p.tablename=c.relname) policies,
--        (select count(*) from public.cerebro_modos) linhas
--   from pg_class c join pg_namespace n on n.oid=c.relnamespace
--  where n.nspname='public' and c.relname='cerebro_modos';
--  -- esperado: 1 linha, relrowsecurity=true, policies=0, linhas=0
--
-- 2) o CHECK do modo aceita EXATAMENTE off e sombra:
--
-- select conname, pg_get_constraintdef(oid) from pg_constraint
--  where conrelid='public.cerebro_modos'::regclass and contype='c' order by 1;
--  -- esperado: ck_cerebro_modos_on_recusado_a_bancada_122_nao_aprovou
--  --           CHECK (modo = ANY (ARRAY['off'::text, 'sombra'::text]))  (+ os 2 de minúsculas)
--
-- 3) 🔴 O CHECK CONSEGUE RECUSAR o `on` (§9.3). Em transação, desfeita:
--
-- begin;
--   insert into public.cerebro_modos (company_id, insurer_key, modo)
--   select id, 'porto', 'on' from public.companies limit 1;
-- rollback;
--  -- esperado: erro 23514 citando ck_cerebro_modos_on_recusado_a_bancada_122_nao_aprovou
--
-- 4) a FK de corretora, com ON DELETE CASCADE, e a PK composta:
--
-- select conname, pg_get_constraintdef(oid) from pg_constraint
--  where conrelid='public.cerebro_modos'::regclass and contype in ('f','p') order by 1;
--  -- esperado: fk → companies(id) ON DELETE CASCADE · pk (company_id, insurer_key, ramo)
--
-- 5) anon/authenticated sem privilégio:
--
-- select grantee, privilege_type from information_schema.role_table_grants
--  where table_schema='public' and table_name='cerebro_modos'
--    and grantee in ('anon','authenticated');
--  -- esperado: 0 linhas
--
-- =============================================================
-- ROLLBACK
-- =============================================================
-- A tabela nasce vazia; sem ela o código lê `off` (falha fechada). Se já tiver
-- linhas (o Founder ligou a sombra), elas somem com a tabela — é só a chave, o
-- histórico da sombra mora em `work_events`.
--
-- drop table if exists public.cerebro_modos;
