-- ============================================================
-- 39A1 — VAULT PREFLIGHT  (SOMENTE LEITURA / SELECT)
-- Rode ANTES de 39A1-vault-data-model.sql para confirmar dependências.
-- Não altera nada. Não seleciona valores de segredo (token/senha/key).
-- ============================================================

-- 1) gen_random_uuid disponível? (defaults das novas tabelas dependem disso)
SELECT proname
FROM pg_proc
WHERE proname IN ('gen_random_uuid', 'uuid_generate_v4')
ORDER BY proname;

SELECT extname FROM pg_extension WHERE extname IN ('pgcrypto', 'uuid-ossp') ORDER BY extname;

-- 2) Tabelas base necessárias (FKs / referências) existem?
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'companies', 'users_v2', 'agents', 'integrations',
    'auxiliary_templates', 'tenant_auxiliaries', 'auxiliary_runs',
    'agent_mcp_connections', 'agent_http_tools'
  )
ORDER BY table_name;

-- 3) Colunas de companies (confirmar PK id)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'companies'
ORDER BY ordinal_position;

-- 4) Colunas de users_v2 (confirmar id + company_id para RLS)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'users_v2'
ORDER BY ordinal_position;

-- 5) Colunas de integrations (alvo de technical_ref para Z-API/WhatsApp; sem valores)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'integrations'
ORDER BY ordinal_position;

-- 6) Colunas das auxiliary_* (referência de padrão de modelagem)
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('auxiliary_templates', 'tenant_auxiliaries', 'auxiliary_runs')
ORDER BY table_name, ordinal_position;

-- 7) Policies existentes (padrão a copiar: service_role + company via users_v2/auth.uid())
SELECT schemaname, tablename, policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN (
    'auxiliary_runs', 'tenant_auxiliaries', 'auxiliary_templates',
    'conversations', 'integrations'
  )
ORDER BY tablename, policyname;

-- 8) Função de updated_at reutilizável existe? (esperado: update_updated_at_column)
SELECT proname
FROM pg_proc
WHERE proname LIKE '%updated_at%'
ORDER BY proname;

-- 9) As tabelas do Vault de produto JÁ existem? (esperado: nenhuma)
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'connector_templates', 'tenant_connections', 'permission_grants',
    'approval_requests', 'vault_audit_log'
  )
ORDER BY table_name;

-- 10) integrations.token existe? (apenas existência da COLUNA, nunca o valor)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'integrations'
  AND column_name IN ('token', 'client_token', 'instance_id');
