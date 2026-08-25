-- =============================================================
-- MIGRATION: spec093_blocoD_saudacao_do_religamento
-- SPEC:      SPEC-093 — BLOCO D (a saudação do religamento)
-- AUTOR:     execução Opus 5             DATA: 2026-08-25
-- OBJETIVO:  saber DESDE QUANDO o atendimento estava fora, e nunca saudar
--            a mesma pessoa duas vezes.
--
-- APPLY:     (1) `agents.desligado_em` — o instante do desligamento.
--            (2) `saudacoes_enviadas` — a chave de idempotência da saudação.
-- VERIFY:    ver o bloco VERIFY no fim deste arquivo (SQL executável).
-- ROLLBACK:  ver o bloco ROLLBACK no fim deste arquivo.
--
-- EXPAND-FIRST: sim  (só adiciona; nada é removido nem reescrito)
-- DESTRUTIVA:   não
-- =============================================================
--
-- 🔴 POR QUE A COLUNA NOVA, SE `agents` JÁ TEM `updated_at`
--
-- 📊 Medido em 25/08/2026: `updated_at` é sobrescrito por QUALQUER save de
-- configuração — `tenant-agent-store.ts` o reescreve em `patch`, em `reset` e
-- no próprio toggle. *"Desde quando estávamos fora"* não é recuperável a partir
-- dele: um ajuste de prompt no meio do desligamento apaga a resposta.
--
-- ⚠️ E a idade é o que decide se a pessoa é saudada ou vai para a fila humana
-- (≤12h · 12–24h · >24h nunca). Uma idade errada manda mensagem para quem
-- escreveu há uma semana — 📊 e 181 das 234 conversas têm mais de 7 dias.
--
-- 🔴 POR QUE TABELA PRÓPRIA, E NÃO `work_effects`
--
-- 📊 `work_effects` existe no banco, **não tem DDL em nenhuma das 68 migrations
-- do repositório** (foi aplicada direto no Supabase), tem **0 linhas** e
-- **nenhum chamador de produção**. Usá-la aqui seria escolher uma tabela sem
-- escritor para a primeira coisa que não pode falhar.

-- -------------------------------------------------------------
-- (1) DESDE QUANDO O ATENDIMENTO ESTAVA FORA
-- -------------------------------------------------------------
alter table public.agents
  add column if not exists desligado_em timestamptz;

comment on column public.agents.desligado_em is
  'SPEC-093 BLOCO D — instante da transição true→false de is_active. '
  'Escrita SÓ no desligamento; ligar LIMPA (null). Não use updated_at para '
  'isto: qualquer save de configuração o sobrescreve.';

-- -------------------------------------------------------------
-- (2) A SAUDAÇÃO NÃO SAI DUAS VEZES
-- -------------------------------------------------------------
--
-- 🔴 A CHAVE É A MENSAGEM, NÃO O CLIQUE. Desligar e ligar duas vezes gera a
-- MESMA chave → a segunda vez é no-op. Chavear no evento de toggle mandaria
-- duas saudações para a mesma pessoa.
create table if not exists public.saudacoes_enviadas (
  id                  uuid        primary key default gen_random_uuid(),
  company_id          uuid        not null references public.companies(id) on delete cascade,
  conversation_id     uuid        not null references public.conversations(id) on delete cascade,
  inbound_message_id  uuid        not null,
  enviada_em          timestamptz not null default now()
);

comment on table public.saudacoes_enviadas is
  'SPEC-093 BLOCO D — idempotência da saudação de religamento. Uma linha por '
  '(corretora, conversa, mensagem inbound que ficou sem resposta).';

-- ⚠️ ON DELETE CASCADE nas duas FKs, e é consciente: a linha aqui só existe
-- para impedir uma segunda saudação NAQUELA conversa. Some a conversa, some a
-- razão de guardar. `RESTRICT` impediria apagar uma conversa por causa de um
-- registro de anti-duplicata, que é o rabo abanando o cachorro.

-- 🔴 O UNIQUE É O GUARDA DE VERDADE. A checagem em Python é o caminho rápido;
-- este índice é o que sobrevive a duas réplicas do drenador rodando juntas.
create unique index if not exists uq_saudacoes_enviadas_chave
  on public.saudacoes_enviadas (company_id, conversation_id, inbound_message_id);

create index if not exists ix_saudacoes_enviadas_empresa
  on public.saudacoes_enviadas (company_id, enviada_em desc);

-- -------------------------------------------------------------
-- RLS — LIGADA, sem policy (nega anon/authenticated; service role passa).
-- Mesma escolha das 14 tabelas da SPEC-059, pelo mesmo motivo: o backend usa
-- service role e o filtro por corretora é obrigatório no repository/service
-- (CLAUDE.md §7). RLS aqui é a rede, não a trava.
-- -------------------------------------------------------------
alter table public.saudacoes_enviadas enable row level security;

-- =============================================================
-- VERIFY  (read-only — rodar DEPOIS do APPLY)
-- =============================================================
-- 1) a coluna existe e é timestamptz:
--
-- select column_name, data_type, is_nullable
--   from information_schema.columns
--  where table_schema='public' and table_name='agents'
--    and column_name='desligado_em';
--  -- esperado: 1 linha, timestamp with time zone, YES
--
-- 2) a tabela existe, com RLS ligada e zero policy:
--
-- select c.relname, c.relrowsecurity,
--        (select count(*) from pg_policies p
--          where p.schemaname='public' and p.tablename=c.relname) policies
--   from pg_class c join pg_namespace n on n.oid=c.relnamespace
--  where n.nspname='public' and c.relname='saudacoes_enviadas';
--  -- esperado: 1 linha, relrowsecurity=true, policies=0
--
-- 3) o UNIQUE das três colunas existe (é ELE que impede a segunda saudação):
--
-- select indexname, indexdef from pg_indexes
--  where schemaname='public' and tablename='saudacoes_enviadas'
--  order by 1;
--  -- esperado: uq_saudacoes_enviadas_chave UNIQUE
--  --           (company_id, conversation_id, inbound_message_id)
--
-- 4) as duas FKs, com ON DELETE CASCADE:
--
-- select con.conname, pg_get_constraintdef(con.oid)
--   from pg_constraint con join pg_class t on t.oid=con.conrelid
--  where t.relname='saudacoes_enviadas' and con.contype='f' order by 1;
--  -- esperado: 2 linhas, ambas ON DELETE CASCADE
--
-- 5) 🔴 O UNIQUE CONSEGUE RECUSAR (§9.3 — prove que o guarda sabe falhar).
--    Em transação, e desfeita:
--
-- begin;
--   insert into public.saudacoes_enviadas (company_id, conversation_id, inbound_message_id)
--   select company_id, id, id from public.conversations limit 1;
--   insert into public.saudacoes_enviadas (company_id, conversation_id, inbound_message_id)
--   select company_id, id, id from public.conversations limit 1;  -- deve ESTOURAR
-- rollback;
--  -- esperado: erro 23505 na SEGUNDA linha. Se as duas passarem, o índice
--  --           não está guardando nada.
--
-- =============================================================
-- ROLLBACK
-- =============================================================
-- ⚠️ Destrutivo por natureza (apaga a marca de anti-duplicata). Só com decisão
-- explícita do Founder — CLAUDE.md §8 proibição 6.
--
-- drop table if exists public.saudacoes_enviadas;
-- alter table public.agents drop column if exists desligado_em;
--
-- 📊 Perder `saudacoes_enviadas` significa que o próximo religamento pode
-- saudar de novo quem já foi saudado. Perder `desligado_em` devolve o produto
-- ao estado de hoje: a idade do desligamento deixa de ser recuperável.
