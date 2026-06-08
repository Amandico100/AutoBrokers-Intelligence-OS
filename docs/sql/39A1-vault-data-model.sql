-- ============================================================
-- 39A1 — VAULT / CONNECTORS / HITL — DATA MODEL (DDL idempotente)
-- ------------------------------------------------------------
-- Revisar antes de rodar (Architect → fundador no Supabase SQL Editor).
-- NÃO armazena segredos. Cria a CAMADA DE PRODUTO do Vault (Caminho B).
-- NÃO conecta serviços reais. NÃO envia mensagens. NÃO executa ações externas.
-- NÃO altera tabelas técnicas existentes (integrations / agent_mcp_* / agent_http_tools).
-- Convenções espelhadas do schema real: gen_random_uuid(), RLS service_role +
-- company via users_v2/auth.uid(), trigger update_updated_at_column().
-- Rode 39A1-vault-preflight.sql ANTES.
-- ============================================================

-- ------------------------------------------------------------
-- TABELA 1 — connector_templates (catálogo global; Admin Global)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.connector_templates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text UNIQUE NOT NULL,
    name text NOT NULL,
    description text,
    category text NOT NULL,                 -- communication|knowledge|productivity|insurance|management_system|browser|internal
    provider text,
    connector_kind text NOT NULL,           -- internal|integration|mcp|http_tool|api_key|oauth|login_password|portal|browser
    auth_type text NOT NULL,                -- none|existing_integration|api_key|oauth|login_password|token|file|manual
    risk_level text NOT NULL DEFAULT 'medium',
    requires_approval_default boolean NOT NULL DEFAULT true,
    capabilities jsonb NOT NULL DEFAULT '[]'::jsonb,
    required_fields jsonb NOT NULL DEFAULT '[]'::jsonb,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT connector_templates_risk_chk
        CHECK (risk_level IN ('low', 'medium', 'high', 'critical'))
);

-- ------------------------------------------------------------
-- TABELA 2 — tenant_connections (conexão ativada por corretora)
--   NÃO guarda segredo: encrypted_secret_ref é REFERÊNCIA (não o valor).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.tenant_connections (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id uuid NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    connector_template_id uuid NOT NULL REFERENCES public.connector_templates(id),
    name text NOT NULL,
    status text NOT NULL DEFAULT 'draft',           -- draft|configuring|connected|disconnected|error|revoked|blocked
    health_status text NOT NULL DEFAULT 'unknown',  -- unknown|healthy|degraded|failed
    technical_ref_type text,                        -- integration|agent_mcp_connection|agent_http_tool|internal|external
    technical_ref_id uuid,                           -- SEM FK (aponta para tipos técnicos diferentes)
    encrypted_secret_ref text,                       -- referência ao segredo (não o segredo)
    connection_config jsonb NOT NULL DEFAULT '{}'::jsonb,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    owner_user_id uuid,
    last_checked_at timestamptz,
    last_used_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- TABELA 3 — permission_grants (conexão × módulo/Auxiliar × ações)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.permission_grants (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id uuid NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    tenant_connection_id uuid NOT NULL REFERENCES public.tenant_connections(id) ON DELETE CASCADE,
    subject_type text NOT NULL,             -- autobrokers|auxiliary_template|tenant_auxiliary|atendimento|user|role|agent
    subject_id uuid,
    allowed_actions jsonb NOT NULL DEFAULT '[]'::jsonb,  -- ex.: ["read","draft_message","send_message"]
    requires_approval boolean NOT NULL DEFAULT true,
    risk_level text NOT NULL DEFAULT 'medium',
    status text NOT NULL DEFAULT 'active',   -- active|paused|revoked|expired
    expires_at timestamptz,
    created_by_user_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT permission_grants_risk_chk
        CHECK (risk_level IN ('low', 'medium', 'high', 'critical'))
);

-- ------------------------------------------------------------
-- TABELA 4 — approval_requests (HITL genérico: aprovar ANTES de executar)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.approval_requests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id uuid NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    tenant_connection_id uuid REFERENCES public.tenant_connections(id) ON DELETE SET NULL,
    permission_grant_id uuid REFERENCES public.permission_grants(id) ON DELETE SET NULL,
    requested_by_user_id uuid,
    approved_by_user_id uuid,
    subject_type text NOT NULL,             -- autobrokers|auxiliary_template|tenant_auxiliary|atendimento|user|agent
    subject_id uuid,
    action_type text NOT NULL,              -- ex.: whatsapp_send_message|whatsapp_draft_message|connector_test|portal_read|portal_write|document_share
    status text NOT NULL DEFAULT 'pending', -- pending|approved|rejected|expired|executed|failed|cancelled
    risk_level text NOT NULL DEFAULT 'medium',
    preview jsonb NOT NULL DEFAULT '{}'::jsonb,
    request_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    approval_result jsonb NOT NULL DEFAULT '{}'::jsonb,
    error_message text,
    expires_at timestamptz,
    approved_at timestamptz,
    rejected_at timestamptz,
    executed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT approval_requests_risk_chk
        CHECK (risk_level IN ('low', 'medium', 'high', 'critical'))
);

-- ------------------------------------------------------------
-- TABELA 5 — vault_audit_log (auditoria de tudo no Vault)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.vault_audit_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id uuid REFERENCES public.companies(id) ON DELETE CASCADE,
    tenant_connection_id uuid REFERENCES public.tenant_connections(id) ON DELETE SET NULL,
    approval_request_id uuid REFERENCES public.approval_requests(id) ON DELETE SET NULL,
    actor_user_id uuid,
    event_type text NOT NULL,               -- connection_created|connection_tested|connection_revoked|permission_granted|permission_revoked|approval_requested|approval_approved|approval_rejected|action_executed|action_failed
    action text,
    status text,
    risk_level text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    ip_address text,
    user_agent text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- ÍNDICES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_connector_templates_slug      ON public.connector_templates (slug);
CREATE INDEX IF NOT EXISTS idx_connector_templates_active    ON public.connector_templates (is_active);
CREATE INDEX IF NOT EXISTS idx_connector_templates_category  ON public.connector_templates (category);

CREATE INDEX IF NOT EXISTS idx_tenant_connections_company         ON public.tenant_connections (company_id);
CREATE INDEX IF NOT EXISTS idx_tenant_connections_template        ON public.tenant_connections (connector_template_id);
CREATE INDEX IF NOT EXISTS idx_tenant_connections_company_status  ON public.tenant_connections (company_id, status);
CREATE INDEX IF NOT EXISTS idx_tenant_connections_company_tpl     ON public.tenant_connections (company_id, connector_template_id);

CREATE INDEX IF NOT EXISTS idx_permission_grants_company        ON public.permission_grants (company_id);
CREATE INDEX IF NOT EXISTS idx_permission_grants_connection     ON public.permission_grants (tenant_connection_id);
CREATE INDEX IF NOT EXISTS idx_permission_grants_subject        ON public.permission_grants (subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_permission_grants_company_status ON public.permission_grants (company_id, status);

CREATE INDEX IF NOT EXISTS idx_approval_requests_company     ON public.approval_requests (company_id);
CREATE INDEX IF NOT EXISTS idx_approval_requests_status      ON public.approval_requests (status);
CREATE INDEX IF NOT EXISTS idx_approval_requests_connection  ON public.approval_requests (tenant_connection_id);
CREATE INDEX IF NOT EXISTS idx_approval_requests_subject     ON public.approval_requests (subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_approval_requests_created     ON public.approval_requests (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_vault_audit_company     ON public.vault_audit_log (company_id);
CREATE INDEX IF NOT EXISTS idx_vault_audit_connection  ON public.vault_audit_log (tenant_connection_id);
CREATE INDEX IF NOT EXISTS idx_vault_audit_approval    ON public.vault_audit_log (approval_request_id);
CREATE INDEX IF NOT EXISTS idx_vault_audit_created     ON public.vault_audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_vault_audit_event       ON public.vault_audit_log (event_type);

-- ============================================================
-- updated_at TRIGGERS (reutiliza a função canônica existente)
-- ============================================================
DROP TRIGGER IF EXISTS trg_connector_templates_updated_at ON public.connector_templates;
CREATE TRIGGER trg_connector_templates_updated_at BEFORE UPDATE ON public.connector_templates
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS trg_tenant_connections_updated_at ON public.tenant_connections;
CREATE TRIGGER trg_tenant_connections_updated_at BEFORE UPDATE ON public.tenant_connections
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS trg_permission_grants_updated_at ON public.permission_grants;
CREATE TRIGGER trg_permission_grants_updated_at BEFORE UPDATE ON public.permission_grants
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS trg_approval_requests_updated_at ON public.approval_requests;
CREATE TRIGGER trg_approval_requests_updated_at BEFORE UPDATE ON public.approval_requests
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ============================================================
-- RLS — habilitar + policies (service_role full + company via users_v2/auth.uid())
-- ============================================================
ALTER TABLE public.connector_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_connections  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.permission_grants   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approval_requests   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vault_audit_log     ENABLE ROW LEVEL SECURITY;

-- connector_templates: service_role gerencia; autenticados leem ativos
DROP POLICY IF EXISTS "service_role full access connector_templates" ON public.connector_templates;
CREATE POLICY "service_role full access connector_templates" ON public.connector_templates
    TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "authenticated read active connector_templates" ON public.connector_templates;
CREATE POLICY "authenticated read active connector_templates" ON public.connector_templates
    FOR SELECT TO authenticated USING (is_active = true);

-- tenant_connections (company-scoped)
DROP POLICY IF EXISTS "service_role full access tenant_connections" ON public.tenant_connections;
CREATE POLICY "service_role full access tenant_connections" ON public.tenant_connections
    TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "company members access tenant_connections" ON public.tenant_connections;
CREATE POLICY "company members access tenant_connections" ON public.tenant_connections
    FOR ALL TO authenticated
    USING (company_id = (SELECT u.company_id FROM public.users_v2 u WHERE u.id = auth.uid()))
    WITH CHECK (company_id = (SELECT u.company_id FROM public.users_v2 u WHERE u.id = auth.uid()));

-- permission_grants (company-scoped)
DROP POLICY IF EXISTS "service_role full access permission_grants" ON public.permission_grants;
CREATE POLICY "service_role full access permission_grants" ON public.permission_grants
    TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "company members access permission_grants" ON public.permission_grants;
CREATE POLICY "company members access permission_grants" ON public.permission_grants
    FOR ALL TO authenticated
    USING (company_id = (SELECT u.company_id FROM public.users_v2 u WHERE u.id = auth.uid()))
    WITH CHECK (company_id = (SELECT u.company_id FROM public.users_v2 u WHERE u.id = auth.uid()));

-- approval_requests (company-scoped)
DROP POLICY IF EXISTS "service_role full access approval_requests" ON public.approval_requests;
CREATE POLICY "service_role full access approval_requests" ON public.approval_requests
    TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "company members access approval_requests" ON public.approval_requests;
CREATE POLICY "company members access approval_requests" ON public.approval_requests
    FOR ALL TO authenticated
    USING (company_id = (SELECT u.company_id FROM public.users_v2 u WHERE u.id = auth.uid()))
    WITH CHECK (company_id = (SELECT u.company_id FROM public.users_v2 u WHERE u.id = auth.uid()));

-- vault_audit_log (company-scoped; leitura por membros, escrita por service_role)
DROP POLICY IF EXISTS "service_role full access vault_audit_log" ON public.vault_audit_log;
CREATE POLICY "service_role full access vault_audit_log" ON public.vault_audit_log
    TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "company members read vault_audit_log" ON public.vault_audit_log;
CREATE POLICY "company members read vault_audit_log" ON public.vault_audit_log
    FOR SELECT TO authenticated
    USING (company_id = (SELECT u.company_id FROM public.users_v2 u WHERE u.id = auth.uid()));

-- ============================================================
-- SEEDS — catálogo de conectores (idempotente; SEM segredos)
-- ============================================================
INSERT INTO public.connector_templates
    (slug, name, description, category, provider, connector_kind, auth_type, risk_level, requires_approval_default, capabilities)
VALUES
    ('internal_conversations', 'Conversas internas', 'Lê conversas/atendimentos da própria corretora.', 'internal', 'autobrokers', 'internal', 'none', 'low', false, '["read"]'::jsonb),
    ('internal_documents',     'Documentos internos', 'Usa documentos da corretora como fonte.', 'internal', 'autobrokers', 'internal', 'none', 'low', false, '["read_document"]'::jsonb),
    ('whatsapp_zapi',          'WhatsApp', 'Prepara e (com aprovação) envia mensagens via WhatsApp.', 'communication', 'z-api', 'integration', 'existing_integration', 'high', true, '["draft_message","send_message","read_message"]'::jsonb),
    ('google_drive',           'Google Drive', 'Lê documentos do Google Drive da corretora.', 'knowledge', 'google', 'oauth', 'oauth', 'medium', false, '["read_document"]'::jsonb),
    ('notion',                 'Notion', 'Lê páginas/bases do Notion da corretora.', 'productivity', 'notion', 'oauth', 'oauth', 'medium', false, '["read_document"]'::jsonb),
    ('infocap',                'InfoCap', 'Consulta dados operacionais (leitura).', 'insurance', 'infocap', 'api_key', 'api_key', 'high', true, '["read"]'::jsonb),
    ('quiver',                 'Quiver', 'Consulta dados operacionais (leitura).', 'insurance', 'quiver', 'api_key', 'api_key', 'high', true, '["read"]'::jsonb),
    ('insurance_portal',       'Portal de Seguradora', 'Cadastro/teste de conexão com portal (sem automação real no MVP).', 'insurance', NULL, 'portal', 'login_password', 'critical', true, '["portal_read"]'::jsonb)
ON CONFLICT (slug) DO NOTHING;

-- ============================================================
-- FIM. Nada além das 5 tabelas de produto + seeds de catálogo.
-- Nenhuma tenant_connection real, nenhum segredo, nenhuma ação externa.
-- ============================================================
