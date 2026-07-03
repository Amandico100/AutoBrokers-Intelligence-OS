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
--
-- APLICADA em 2026-07-03 (founder, SQL Editor) com compatibilização de schema:
-- a coluna real é `risk` (não risk_level) e o CHECK de `category` só aceita
-- knowledge/productivity/research/sales/insurance_ops/communication/internal.
-- Categorias usadas: http_tools=internal, handoff=communication, csv=productivity.
-- Nenhum código lê category/risk para decisão — taxonomia apenas. Este arquivo
-- reflete o que ESTÁ no banco.

insert into public.capabilities (capability_key, name, category, owner, risk, requires_connection, requires_approval, provider, is_active)
values
  ('tenant.http_tools.execute', 'Ferramentas HTTP do agente', 'internal', 'tenant', 'medium', false, false, null, true),
  ('operational.insurer.dispatch', 'Acionamento de seguradora (WhatsApp)', 'insurance_ops', 'operational', 'high', true, true, 'zapi', true),
  ('platform.human_handoff', 'Transbordo para humano', 'communication', 'platform', 'low', false, false, null, true),
  ('platform.csv_analytics', 'Análise de planilhas CSV', 'productivity', 'platform', 'low', false, false, null, true)
on conflict (capability_key) do nothing;

insert into public.capability_bindings (agent_role, capability_key, enabled)
values
  ('core', 'tenant.http_tools.execute', true),
  ('attendance', 'tenant.http_tools.execute', true),
  ('auxiliary', 'tenant.http_tools.execute', true),
  ('attendance', 'operational.insurer.dispatch', true),
  ('core', 'platform.human_handoff', true),
  ('attendance', 'platform.human_handoff', true),
  ('core', 'platform.csv_analytics', true)
on conflict do nothing;
