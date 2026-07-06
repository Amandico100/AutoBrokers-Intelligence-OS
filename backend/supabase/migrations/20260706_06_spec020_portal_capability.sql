-- SPEC-020 P3 — Capability do portal_action + perfil de acionamento por corretora.
-- EXPAND-ONLY. tenant.portal.execute libera a tool portal_action (acessar portais).
-- acionamento_profile = identidade da CORRETORA usada como "solicitante/Corretor"
-- no portal (multi-tenant: cada corretora a sua). NUNCA o e-mail do segurado.
--
-- APPLY:   SQL Editor do Supabase (idempotente).
-- VERIFY:  select capability_key from public.capabilities where capability_key='tenant.portal.execute';
--          select column_name from information_schema.columns where table_name='companies' and column_name='acionamento_profile';
-- ROLLBACK: delete from public.capability_bindings where capability_key='tenant.portal.execute';
--           delete from public.capabilities where capability_key='tenant.portal.execute';
--           alter table public.companies drop column if exists acionamento_profile;

insert into public.capabilities
  (capability_key, name, category, owner, risk, requires_connection, requires_approval, provider, is_active)
values
  ('tenant.portal.execute', 'Acessar portais (vidros/corretor)', 'insurance_ops', 'tenant', 'high', false, false, null, true)
on conflict (capability_key) do nothing;

-- Fable (SPEC-020 P3) previu core/auxiliary; incluimos attendance porque o caso de
-- ouro (assistencia de vidros pelo atendente) e um fluxo de ATENDIMENTO. Seguranca
-- preservada: gate PORTAL_REAL_ENABLED off + journey para no 80% + needs_human.
insert into public.capability_bindings (agent_role, capability_key, enabled)
values
  ('core', 'tenant.portal.execute', true),
  ('auxiliary', 'tenant.portal.execute', true),
  ('attendance', 'tenant.portal.execute', true)
on conflict do nothing;

-- Perfil de acionamento por corretora (solicitante). Preenchido no dashboard.
alter table public.companies add column if not exists acionamento_profile jsonb not null default '{}'::jsonb;
comment on column public.companies.acionamento_profile is
  'SPEC-020: identidade da corretora usada como solicitante/Corretor nos portais {nome,email,telefone,cpf_cnpj,susep}.';
