-- ============================================================
-- 39A0 — VAULT / CONNECTORS / HITL DIAGNOSTICS  (SOMENTE LEITURA / SELECT)
-- AutoBrokers Intelligence OS · tools/MCP/conexões/credenciais + Auxiliares
-- Seguro para colar no Supabase SQL Editor. NÃO altera dados.
-- Sem UPDATE/INSERT/DELETE/ALTER/CREATE/DROP. Sem company_id fixo.
-- NUNCA seleciona valores de segredo (token/senha/key) — apenas existência/length.
-- ============================================================

-- ------------------------------------------------------------
-- 1) Tabelas relacionadas a tools/conexões/credenciais/aprovação (descoberta)
-- ------------------------------------------------------------
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND (
    table_name LIKE '%mcp%' OR table_name LIKE '%tool%' OR table_name LIKE '%connection%'
    OR table_name LIKE '%connector%' OR table_name LIKE '%integration%' OR table_name LIKE '%credential%'
    OR table_name LIKE '%vault%' OR table_name LIKE '%approval%' OR table_name LIKE '%ucp%'
    OR table_name LIKE '%delegation%' OR table_name LIKE '%permission%' OR table_name LIKE '%handoff%'
  )
ORDER BY table_name;

-- ------------------------------------------------------------
-- 2) Colunas das tabelas técnicas de tools/conexões (confirmar nomes reais)
-- ------------------------------------------------------------
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN (
    'agent_http_tools', 'agent_mcp_connections', 'agent_mcp_tools', 'mcp_servers',
    'ucp_connections', 'integrations', 'agent_delegations'
  )
ORDER BY table_name, ordinal_position;

-- ------------------------------------------------------------
-- 3) Policies RLS dessas tabelas
-- ------------------------------------------------------------
SELECT schemaname, tablename, policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN (
    'agent_http_tools', 'agent_mcp_connections', 'agent_mcp_tools', 'mcp_servers',
    'ucp_connections', 'integrations', 'agent_delegations'
  )
ORDER BY tablename, policyname;

-- ------------------------------------------------------------
-- 4) Constraints (PK/FK/CHECK) das tabelas técnicas
-- ------------------------------------------------------------
SELECT tc.table_name, tc.constraint_type, tc.constraint_name
FROM information_schema.table_constraints tc
WHERE tc.table_schema = 'public'
  AND tc.table_name IN (
    'agent_http_tools', 'agent_mcp_connections', 'agent_mcp_tools', 'mcp_servers',
    'ucp_connections', 'integrations'
  )
ORDER BY tc.table_name, tc.constraint_type;

-- ------------------------------------------------------------
-- 5) Catálogo MCP global (mcp_servers) — sem env_vars/command (podem ter segredo)
-- ------------------------------------------------------------
SELECT id, name, display_name, oauth_provider,
       (oauth_scopes IS NOT NULL) AS has_oauth_scopes,
       (env_vars IS NOT NULL)     AS has_env_vars,
       is_active, created_at
FROM public.mcp_servers
ORDER BY display_name;

-- ------------------------------------------------------------
-- 6) Conexões MCP por agente — SEM valores de token (apenas existência)
-- ------------------------------------------------------------
SELECT id, agent_id, mcp_server_id,
       (access_token IS NOT NULL)  AS has_access_token,
       (refresh_token IS NOT NULL) AS has_refresh_token,
       token_expires_at,
       (scopes_granted IS NOT NULL) AS has_scopes,
       is_active, connected_at
FROM public.agent_mcp_connections
ORDER BY created_at DESC
LIMIT 50;

-- ------------------------------------------------------------
-- 7) Tools MCP habilitadas por agente
-- ------------------------------------------------------------
SELECT agent_id, mcp_server_name, tool_name, variable_name, is_enabled, created_at
FROM public.agent_mcp_tools
ORDER BY created_at DESC
LIMIT 50;

-- ------------------------------------------------------------
-- 8) HTTP tools por agente — SEM headers (podem conter auth) e SEM body
-- ------------------------------------------------------------
SELECT id, agent_id, name, method, url,
       (headers IS NOT NULL AND headers <> '{}'::jsonb) AS has_headers,
       (body_template IS NOT NULL) AS has_body_template,
       is_active, created_at
FROM public.agent_http_tools
ORDER BY created_at DESC
LIMIT 50;

-- ------------------------------------------------------------
-- 9) Integrations (ex.: WhatsApp/Z-API) por empresa — SEM valores de token
-- ------------------------------------------------------------
SELECT id, company_id, provider,
       (token IS NOT NULL)        AS has_token,
       (client_token IS NOT NULL) AS has_client_token,
       is_active, agent_id, created_at
FROM public.integrations
ORDER BY created_at DESC
LIMIT 50;

-- ------------------------------------------------------------
-- 10) Agents com credencial de LLM/Vision (existência, NUNCA o valor)
-- ------------------------------------------------------------
SELECT count(*)                                          AS agents_total,
       count(*) FILTER (WHERE llm_api_key IS NOT NULL)   AS with_llm_key,
       count(*) FILTER (WHERE vision_api_key IS NOT NULL) AS with_vision_key
FROM public.agents;

-- ------------------------------------------------------------
-- 11) Contagens gerais (volume por tabela)
-- ------------------------------------------------------------
SELECT 'agent_http_tools'       AS tabela, count(*) AS rows FROM public.agent_http_tools
UNION ALL SELECT 'agent_mcp_connections', count(*) FROM public.agent_mcp_connections
UNION ALL SELECT 'agent_mcp_tools',       count(*) FROM public.agent_mcp_tools
UNION ALL SELECT 'mcp_servers',           count(*) FROM public.mcp_servers
UNION ALL SELECT 'ucp_connections',       count(*) FROM public.ucp_connections
UNION ALL SELECT 'integrations',          count(*) FROM public.integrations
UNION ALL SELECT 'agent_delegations',     count(*) FROM public.agent_delegations
ORDER BY tabela;

-- ------------------------------------------------------------
-- 12) Colunas de ucp_connections (confirmar shape sem assumir; sem valores sensíveis)
-- ------------------------------------------------------------
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'ucp_connections'
ORDER BY ordinal_position;

-- ------------------------------------------------------------
-- 13) HITL: conversas em handoff humano (status), sem PII de conteúdo
-- ------------------------------------------------------------
SELECT status, count(*) AS rows
FROM public.conversations
WHERE status ILIKE '%human%' OR human_handoff_reason IS NOT NULL
GROUP BY status
ORDER BY status;

-- ------------------------------------------------------------
-- 14) Existe alguma tabela de Vault/aprovação de PRODUTO? (esperado: NÃO)
-- ------------------------------------------------------------
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'tenant_connections', 'connection_vault', 'connector_templates',
    'permission_grants', 'approval_requests', 'vault_audit_log', 'knowledge_sources'
  )
ORDER BY table_name;
