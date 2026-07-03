-- SPEC-018 S3 — Capabilities formais para autoridades hoje "soltas" (EXPAND-ONLY).
-- Prepara o AUTHORITY_STRICT_MODE: HTTP tools e acionamento de seguradora
-- passam a ter capability própria no Registry (a flag continua OFF até a
-- migração de comportamento na S5).
--
-- APPLY:   executar no SQL Editor do Supabase (idempotente).
-- VERIFY:  select capability_key from public.capabilities
--            where capability_key in
--              ('tenant.http_tools.execute','operational.insurer.dispatch');
-- ROLLBACK: delete from public.capability_bindings where capability_key in (...);
--           delete from public.capabilities where capability_key in (...);

insert into public.capabilities (capability_key, name, category, owner, risk_level, requires_connection, requires_approval, provider, is_active)
values
  ('tenant.http_tools.execute', 'Ferramentas HTTP do agente', 'integrations', 'tenant', 'medium', false, false, null, true),
  ('operational.insurer.dispatch', 'Acionamento de seguradora (WhatsApp)', 'insurance_ops', 'operational', 'high', true, true, 'zapi', true)
on conflict (capability_key) do nothing;

insert into public.capability_bindings (agent_role, capability_key, enabled)
values
  ('core', 'tenant.http_tools.execute', true),
  ('attendance', 'tenant.http_tools.execute', true),
  ('auxiliary', 'tenant.http_tools.execute', true),
  ('attendance', 'operational.insurer.dispatch', true)
on conflict do nothing;
