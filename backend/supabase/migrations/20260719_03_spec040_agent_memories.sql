-- SPEC-040 Onda 5 — Memoria por agente da Central (padrao sleep-time).
-- Blocos de memoria consultaveis por operario (o que cada agente "sabe"),
-- reescritos em lote diario a partir dos dados REAIS (deterministico).
-- Global (sem company_id): e a memoria dos agentes da plataforma.
--
-- APPLY ------------------------------------------------------------------
create table if not exists public.agent_memories (
  id uuid primary key default gen_random_uuid(),
  agent_task text not null,
  block_key text not null,
  content text not null,
  data jsonb,
  version int not null default 1,
  updated_at timestamptz not null default now(),
  unique (agent_task, block_key)
);
create index if not exists ix_agent_memories_task
  on public.agent_memories (agent_task, updated_at desc);

alter table public.agent_memories enable row level security;
-- service-only: nenhuma policy — so o backend (admin le via endpoint master).

-- VERIFY -----------------------------------------------------------------
-- select count(*) from public.agent_memories;
-- ROLLBACK ---------------------------------------------------------------
-- drop table if exists public.agent_memories;
