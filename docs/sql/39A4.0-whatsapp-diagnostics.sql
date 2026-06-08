-- ============================================================
-- 39A4.0 — WHATSAPP DIAGNOSTICS  (SOMENTE LEITURA / SELECT)
-- AutoBrokers Intelligence OS · integrations (Z-API/WhatsApp) + conversas + Vault
-- Seguro para colar no Supabase SQL Editor. NÃO altera dados.
-- NUNCA seleciona valor de segredo (token/client_token). Só existência/length.
-- identifier (telefone conectado) é mascarado para os últimos 4 dígitos.
-- ============================================================

-- ------------------------------------------------------------
-- 1) Colunas reais da tabela integrations (confirmar shape)
-- ------------------------------------------------------------
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'integrations'
ORDER BY ordinal_position;

-- ------------------------------------------------------------
-- 2) Integrações por provider + status (visão geral)
-- ------------------------------------------------------------
SELECT provider, is_active, count(*) AS rows
FROM public.integrations
GROUP BY provider, is_active
ORDER BY provider, is_active;

-- ------------------------------------------------------------
-- 3) Integrações (SEM segredos): presença/tamanho de token; identifier mascarado
-- ------------------------------------------------------------
SELECT
  id,
  company_id,
  agent_id,
  provider,
  is_active,
  ('...' || right(identifier, 4))      AS identifier_masked,
  (token IS NOT NULL)                  AS has_token,
  length(token)                        AS token_length,
  (client_token IS NOT NULL)           AS has_client_token,
  length(client_token)                 AS client_token_length,
  length(instance_id)                  AS instance_id_length,
  base_url,
  created_at
FROM public.integrations
ORDER BY created_at DESC
LIMIT 50;

-- ------------------------------------------------------------
-- 4) Vínculo empresa/agente das integrações (sem PII, sem segredo)
-- ------------------------------------------------------------
SELECT
  i.id,
  c.company_name,
  a.name AS agent_name,
  i.provider,
  i.is_active,
  ('...' || right(i.identifier, 4)) AS identifier_masked,
  i.created_at
FROM public.integrations i
LEFT JOIN public.companies c ON c.id = i.company_id
LEFT JOIN public.agents a ON a.id = i.agent_id
ORDER BY i.created_at DESC
LIMIT 50;

-- ------------------------------------------------------------
-- 5) Conversas por canal (whatsapp vs web) — sem conteúdo/PII
-- ------------------------------------------------------------
SELECT channel, count(*) AS rows
FROM public.conversations
GROUP BY channel
ORDER BY rows DESC;

-- ------------------------------------------------------------
-- 6) Conversas em handoff humano (status) — sem conteúdo/PII
-- ------------------------------------------------------------
SELECT status, count(*) AS rows
FROM public.conversations
WHERE status ILIKE '%human%' OR human_handoff_reason IS NOT NULL
GROUP BY status
ORDER BY status;

-- ------------------------------------------------------------
-- 7) RLS de integrations (avaliar isolamento por empresa)
-- ------------------------------------------------------------
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'integrations'
ORDER BY policyname;

-- ------------------------------------------------------------
-- 8) Tabelas do Vault de produto presentes? (para o adapter referenciar)
-- ------------------------------------------------------------
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'tenant_connections', 'connector_templates', 'permission_grants',
    'approval_requests', 'vault_audit_log'
  )
ORDER BY table_name;

-- ------------------------------------------------------------
-- 9) Integrações com agent_id nulo (risco de roteamento sem agente)
-- ------------------------------------------------------------
SELECT
  count(*)                                  AS integrations_total,
  count(*) FILTER (WHERE agent_id IS NULL)  AS sem_agente,
  count(*) FILTER (WHERE is_active)         AS ativas
FROM public.integrations;
