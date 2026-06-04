-- ============================================================
-- Agent Smith V6.2 — Upgrade Migration
-- ============================================================
-- QUANDO USAR: Se você já tem o Smith rodando (v6.0 ou v6.1)
--              e quer atualizar para v6.2.
--
-- ⚠️  NÃO rode isso em banco novo! Para banco novo use: schema_completo.sql
--
-- Este arquivo contém TODAS as migrations incrementais do v6.2:
--   1. Sanitization Jobs (Document Sanitizer)
--   2. Extract Images flag (Vision API)
--   3. CSV Ingestion Strategy
--   4. Performance Indexes
--   5. Conversations Indexes
--   6. HyDE default false
--   7. File System Search columns
--   8. SubAgent Delegation System
-- ============================================================


-- ============================================================
-- 1. SANITIZATION JOBS
-- Tabela para o Document Sanitizer
-- ============================================================

CREATE TABLE IF NOT EXISTS sanitization_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),

    -- Original file
    original_filename TEXT NOT NULL,
    original_file_path TEXT NOT NULL,
    original_file_size BIGINT NOT NULL,
    original_mime_type TEXT NOT NULL,

    -- Result
    sanitized_file_path TEXT,
    sanitized_file_size BIGINT,

    -- Status and progress
    status TEXT NOT NULL DEFAULT 'pending',
    progress INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,

    -- Processing metadata
    pages_count INTEGER,
    images_count INTEGER,
    tables_count INTEGER,
    processing_time_seconds REAL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '7 days')
);

-- RLS
ALTER TABLE sanitization_jobs ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'company_isolation_select' AND tablename = 'sanitization_jobs') THEN
        CREATE POLICY "company_isolation_select"
            ON sanitization_jobs FOR SELECT
            USING (company_id = (auth.jwt() ->> 'company_id')::uuid);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'company_isolation_insert' AND tablename = 'sanitization_jobs') THEN
        CREATE POLICY "company_isolation_insert"
            ON sanitization_jobs FOR INSERT
            WITH CHECK (company_id = (auth.jwt() ->> 'company_id')::uuid);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'company_isolation_delete' AND tablename = 'sanitization_jobs') THEN
        CREATE POLICY "company_isolation_delete"
            ON sanitization_jobs FOR DELETE
            USING (company_id = (auth.jwt() ->> 'company_id')::uuid);
    END IF;
END $$;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sanitization_jobs_company ON sanitization_jobs(company_id);
CREATE INDEX IF NOT EXISTS idx_sanitization_jobs_status ON sanitization_jobs(status);
CREATE INDEX IF NOT EXISTS idx_sanitization_jobs_expires ON sanitization_jobs(expires_at);


-- ============================================================
-- 2. EXTRACT IMAGES FLAG
-- Suporte a Vision API no Document Sanitizer
-- ============================================================

ALTER TABLE sanitization_jobs
    ADD COLUMN IF NOT EXISTS extract_images BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN sanitization_jobs.extract_images IS 'Se true, ativa Vision API para descrever imagens durante a sanitização';


-- ============================================================
-- 3. CSV INGESTION STRATEGY
-- Suporte a chunking de arquivos CSV
-- ============================================================

ALTER TABLE documents DROP CONSTRAINT IF EXISTS check_ingestion_strategy;

ALTER TABLE documents ADD CONSTRAINT check_ingestion_strategy
  CHECK (ingestion_strategy IS NULL OR ingestion_strategy::text = ANY (ARRAY[
    'recursive'::text,
    'semantic'::text,
    'page'::text,
    'agentic'::text,
    'csv'::text
  ]));


-- ============================================================
-- 4. PERFORMANCE INDEXES
-- Indexes para token_usage_logs e conversations
-- ============================================================

-- Billing worker: unbilled logs
CREATE INDEX IF NOT EXISTS idx_token_usage_unbilled
    ON token_usage_logs(created_at)
    WHERE billed = false;

-- Billing per company
CREATE INDEX IF NOT EXISTS idx_token_usage_company_unbilled
    ON token_usage_logs(company_id, created_at)
    WHERE billed = false;

-- Dashboard/reports
CREATE INDEX IF NOT EXISTS idx_token_usage_company_date
    ON token_usage_logs(company_id, created_at);

-- Webhook lookups
CREATE INDEX IF NOT EXISTS idx_conversations_company_user_channel
    ON conversations(company_id, user_id, channel);


-- ============================================================
-- 5. CONVERSATIONS INDEXES
-- Index composto para session_id + company_id
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_conversations_session_company
    ON conversations(session_id, company_id);


-- ============================================================
-- 6. HYDE DEFAULT FALSE
-- Novos agentes com HyDE desativado por padrão
-- ============================================================

ALTER TABLE agents ALTER COLUMN is_hyde_enabled SET DEFAULT false;


-- ============================================================
-- 7. FILE SYSTEM SEARCH
-- Colunas para suporte a File System Search
-- ============================================================

-- Novas colunas em documents
ALTER TABLE documents ADD COLUMN IF NOT EXISTS ingestion_mode TEXT NOT NULL DEFAULT 'semantic';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS fs_storage_path TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS fs_token_count INTEGER;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS fs_section_count INTEGER;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS fs_outline JSONB;

-- Constraint para ingestion_mode
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE constraint_name = 'check_ingestion_mode') THEN
        ALTER TABLE documents ADD CONSTRAINT check_ingestion_mode
            CHECK (ingestion_mode::text = ANY (ARRAY['semantic'::text, 'filesystem'::text]));
    END IF;
END $$;

-- Tornar qdrant_collection nullable (filesystem não usa Qdrant)
ALTER TABLE documents ALTER COLUMN qdrant_collection DROP NOT NULL;

-- Nova coluna em agents
ALTER TABLE agents ADD COLUMN IF NOT EXISTS retrieval_mode TEXT NOT NULL DEFAULT 'semantic';

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE constraint_name = 'check_retrieval_mode') THEN
        ALTER TABLE agents ADD CONSTRAINT check_retrieval_mode
            CHECK (retrieval_mode::text = ANY (ARRAY['semantic'::text, 'filesystem'::text]));
    END IF;
END $$;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_ingestion_mode ON documents(ingestion_mode);
CREATE INDEX IF NOT EXISTS idx_documents_agent_ingestion ON documents(agent_id, ingestion_mode);


-- ============================================================
-- 8. SUBAGENT DELEGATION SYSTEM
-- Sistema de Multi-Agent Delegation
-- ============================================================

-- Tabela de delegações
CREATE TABLE IF NOT EXISTS agent_delegations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    orchestrator_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    subagent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    task_description TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    max_context_chars INTEGER DEFAULT 2000,
    timeout_seconds INTEGER DEFAULT 30,
    max_iterations INTEGER DEFAULT 5,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT no_self_delegation CHECK (orchestrator_id != subagent_id),
    CONSTRAINT unique_delegation UNIQUE (orchestrator_id, subagent_id)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_delegations_orchestrator
    ON agent_delegations(orchestrator_id)
    WHERE is_active = true;

-- Flags de SubAgent na tabela agents
ALTER TABLE agents
    ADD COLUMN IF NOT EXISTS is_subagent BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS allow_direct_chat BOOLEAN DEFAULT false;

COMMENT ON COLUMN agents.is_subagent IS 'Se true, esconde widget/WhatsApp/canais públicos no frontend';
COMMENT ON COLUMN agents.allow_direct_chat IS 'Se true, subagent aparece no chat test para o admin treinar/debugar';

-- Campo para traces de SubAgent
ALTER TABLE conversation_logs
    ADD COLUMN IF NOT EXISTS internal_steps JSONB DEFAULT NULL;

COMMENT ON COLUMN conversation_logs.internal_steps IS 'Traces de execução de SubAgents (ReAct loop steps, tokens, latência)';

-- RLS
ALTER TABLE agent_delegations ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'delegations_same_company' AND tablename = 'agent_delegations') THEN
        CREATE POLICY "delegations_same_company" ON agent_delegations
            FOR ALL
            USING (
                (SELECT company_id FROM agents WHERE id = orchestrator_id)
                =
                (SELECT company_id FROM agents WHERE id = subagent_id)
            );
    END IF;
END $$;

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_agent_delegations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_delegations_updated_at') THEN
        CREATE TRIGGER trigger_delegations_updated_at
            BEFORE UPDATE ON agent_delegations
            FOR EACH ROW
            EXECUTE FUNCTION update_agent_delegations_updated_at();
    END IF;
END $$;

-- Grants
GRANT ALL ON TABLE agent_delegations TO anon;
GRANT ALL ON TABLE agent_delegations TO authenticated;
GRANT ALL ON TABLE agent_delegations TO service_role;
GRANT ALL ON TABLE sanitization_jobs TO anon;
GRANT ALL ON TABLE sanitization_jobs TO authenticated;
GRANT ALL ON TABLE sanitization_jobs TO service_role;


-- ============================================================
-- ✅ UPGRADE COMPLETO!
-- Seu banco agora está atualizado para o Agent Smith V6.2
-- ============================================================
