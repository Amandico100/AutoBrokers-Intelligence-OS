-- SPEC-045 — Registro de envios de PLATAFORMA a segurados (cobranca,
-- campanhas, avisos). Duas funcoes: (1) NOTA DE CONTEXTO quando o cliente
-- responde e cai no atendimento ("recebeu cobranca da parcela X ha 2 dias");
-- (2) trilha auditavel dos envios de auxiliares. Expand-only.
--
-- APPLY ------------------------------------------------------------------
create table if not exists public.platform_sends (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null,
  phone text not null,
  kind text not null,            -- billing | campaign | report | alert | other
  summary text,                  -- humano: "cobranca da parcela 3 (Allianz)"
  sent_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);
create index if not exists ix_platform_sends_lookup
  on public.platform_sends (company_id, phone, sent_at desc);

alter table public.platform_sends enable row level security;
-- service-only: nenhuma policy — so o backend le/escreve.

-- VERIFY -----------------------------------------------------------------
-- select count(*) from public.platform_sends;
-- ROLLBACK ---------------------------------------------------------------
-- drop table if exists public.platform_sends;
