-- SPEC-017 S17-12 — Multi-número por corretora (EXPAND-ONLY).
-- Cada corretora pode ter N WhatsApps: atendimento (padrão), auxiliares
-- (cobrança, leads...), disparo — cada um com instância/webhook próprios.
--
-- APPLY:   executar no SQL Editor do Supabase.
-- VERIFY:  select column_name from information_schema.columns
--            where table_name='integrations' and column_name='purpose';
-- ROLLBACK: alter table public.integrations drop column if exists purpose;

alter table public.integrations
  add column if not exists purpose text not null default 'attendance';

comment on column public.integrations.purpose is
  'SPEC-017 S17-12: attendance | auxiliary:<slug> | dispatch — número dedicado por função';

create index if not exists idx_integrations_company_purpose
  on public.integrations (company_id, purpose)
  where is_active = true;
