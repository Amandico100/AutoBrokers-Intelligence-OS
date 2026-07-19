-- SPEC-040 Onda 3 — Inteligencia destilada do Espelho de Atendimento.
-- GLOBAIS (sem company_id de proposito): playbooks de conduta e knowledge
-- cards sao inteligencia da AUTOBROKERS — servem todas as corretoras.
-- Dado pessoal NUNCA chega aqui: o destilador mascara PII ANTES da LLM e o
-- filtro de 2 camadas rejeita card com qualquer residuo.
--
-- APPLY ------------------------------------------------------------------
create table if not exists public.conduct_playbooks (
  id uuid primary key default gen_random_uuid(),
  ramo text not null,
  servico text not null,
  version int not null default 1,
  status text not null default 'draft',  -- draft | active | retired
  content jsonb not null,
  source_stats jsonb,
  model_used text,
  created_at timestamptz not null default now()
);
create index if not exists ix_conduct_playbooks_lookup
  on public.conduct_playbooks (ramo, servico, status, version desc);

create table if not exists public.knowledge_cards (
  id uuid primary key default gen_random_uuid(),
  card_hash text not null unique,
  card_text text not null,
  category text,
  ramo text,
  insurer_key text,
  status text not null default 'pending_review',
  -- pending_review | approved | rejected | rejected_pii | published
  pii_check jsonb,
  source_count int not null default 1,
  created_at timestamptz not null default now(),
  published_at timestamptz
);
create index if not exists ix_knowledge_cards_status
  on public.knowledge_cards (status, created_at desc);

alter table public.conduct_playbooks enable row level security;
alter table public.knowledge_cards enable row level security;
-- service-only por design: NENHUMA policy — so o backend le/escreve.

-- VERIFY -----------------------------------------------------------------
-- select count(*) from public.conduct_playbooks;
-- select count(*) from public.knowledge_cards;
--
-- ROLLBACK ---------------------------------------------------------------
-- drop table if exists public.conduct_playbooks;
-- drop table if exists public.knowledge_cards;
