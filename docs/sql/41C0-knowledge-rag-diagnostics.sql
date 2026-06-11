-- ============================================================
-- 41C.0 — KNOWLEDGE / RAG / MEMORY DIAGNOSTICS  (SOMENTE LEITURA / SELECT)
-- AutoBrokers Intelligence OS · inventário de documentos/RAG/memória.
-- Seguro para colar no Supabase SQL Editor. NÃO altera dados, NÃO cria schema.
-- NUNCA seleciona conteúdo de documento, token, chave, PII ou mensagem de cliente.
-- Alguns blocos podem não retornar nada se a tabela não existir — isso é esperado.
-- Para o Architect: priorize enviar de volta os blocos (a), (b), (c) e (j).
-- ============================================================

-- ------------------------------------------------------------
-- (a) Tabelas candidatas (document/knowledge/rag/vector/embedding/chunk/memory/file/benchmark/...)
-- ------------------------------------------------------------
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND (
    table_name ILIKE '%document%' OR table_name ILIKE '%knowledge%' OR table_name ILIKE '%rag%'
    OR table_name ILIKE '%vector%' OR table_name ILIKE '%embedding%' OR table_name ILIKE '%chunk%'
    OR table_name ILIKE '%memory%' OR table_name ILIKE '%file%' OR table_name ILIKE '%benchmark%'
    OR table_name ILIKE '%sanitiz%' OR table_name ILIKE '%session_summ%'
    OR table_name ILIKE '%user_memor%' OR table_name ILIKE '%conversation_log%'
  )
ORDER BY table_name;

-- ------------------------------------------------------------
-- (b) Colunas dessas tabelas (shape real — sem dados)
-- ------------------------------------------------------------
SELECT c.table_name, c.column_name, c.data_type, c.is_nullable
FROM information_schema.columns c
WHERE c.table_schema = 'public'
  AND c.table_name IN (
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public'
      AND (
        table_name ILIKE '%document%' OR table_name ILIKE '%knowledge%' OR table_name ILIKE '%rag%'
        OR table_name ILIKE '%vector%' OR table_name ILIKE '%embedding%' OR table_name ILIKE '%chunk%'
        OR table_name ILIKE '%memory%' OR table_name ILIKE '%file%' OR table_name ILIKE '%benchmark%'
        OR table_name ILIKE '%sanitiz%' OR table_name ILIKE '%session_summ%'
        OR table_name ILIKE '%user_memor%' OR table_name ILIKE '%conversation_log%'
      )
  )
ORDER BY c.table_name, c.ordinal_position;

-- ------------------------------------------------------------
-- (c) RLS e policies dessas tabelas (segurança / isolamento)
-- ------------------------------------------------------------
SELECT t.relname AS table_name, t.relrowsecurity AS rls_enabled, t.relforcerowsecurity AS rls_forced
FROM pg_class t
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname = 'public'
  AND (
    t.relname ILIKE '%document%' OR t.relname ILIKE '%knowledge%' OR t.relname ILIKE '%memory%'
    OR t.relname ILIKE '%sanitiz%' OR t.relname ILIKE '%session_summ%' OR t.relname ILIKE '%conversation_log%'
  )
ORDER BY t.relname;

SELECT schemaname, tablename, policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public'
  AND (
    tablename ILIKE '%document%' OR tablename ILIKE '%knowledge%' OR tablename ILIKE '%memory%'
    OR tablename ILIKE '%sanitiz%' OR tablename ILIKE '%session_summ%' OR tablename ILIKE '%conversation_log%'
  )
ORDER BY tablename, policyname;

-- ------------------------------------------------------------
-- (d) Índices de documents
-- ------------------------------------------------------------
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'documents'
ORDER BY indexname;

-- ------------------------------------------------------------
-- (e) Contagens por tabela-chave (ajuste conforme as que existirem em (a))
-- ------------------------------------------------------------
SELECT 'documents' AS tbl, count(*) AS rows FROM public.documents
UNION ALL SELECT 'agents', count(*) FROM public.agents
UNION ALL SELECT 'session_summaries', count(*) FROM public.session_summaries
UNION ALL SELECT 'user_memories', count(*) FROM public.user_memories
UNION ALL SELECT 'conversation_logs', count(*) FROM public.conversation_logs;

-- ------------------------------------------------------------
-- (f) documents por company/agent/status (counts) + amostra SEM conteúdo
-- ------------------------------------------------------------
SELECT company_id, agent_id, status, count(*) AS rows
FROM public.documents
GROUP BY company_id, agent_id, status
ORDER BY rows DESC
LIMIT 50;

SELECT
  id, company_id, agent_id, file_name, file_type, status,
  chunks_count, ingestion_mode, ingestion_strategy, qdrant_collection,
  (fs_storage_path IS NOT NULL) AS has_fs_path, created_at
FROM public.documents
ORDER BY created_at DESC
LIMIT 30;

-- ------------------------------------------------------------
-- (g) agents — flags de RAG/memória (sem prompts)
-- ------------------------------------------------------------
SELECT
  id, company_id, slug, is_active, is_subagent, allow_direct_chat,
  retrieval_mode, is_hyde_enabled, allow_vision, vision_model
FROM public.agents
ORDER BY created_at DESC
LIMIT 50;

-- ------------------------------------------------------------
-- (h) auxiliary_templates — runtime declarado + RAG no blueprint (se existir)
-- ------------------------------------------------------------
SELECT
  slug,
  is_active,
  (default_config -> 'runtime' ->> 'kind') AS runtime_kind,
  (default_config -> 'runtime' -> 'agent_blueprint' ->> 'retrieval_mode') AS blueprint_retrieval_mode,
  (default_config -> 'visibility' ->> 'type') AS visibility
FROM public.auxiliary_templates
ORDER BY slug;

-- ------------------------------------------------------------
-- (i) tenant_auxiliaries — binding de runtime/agent
-- ------------------------------------------------------------
SELECT
  slug,
  company_id,
  status,
  (config -> 'runtime' ->> 'kind') AS runtime_kind,
  (config -> 'runtime' ->> 'agent_id') AS runtime_agent_id
FROM public.tenant_auxiliaries
ORDER BY slug;

-- ------------------------------------------------------------
-- (j) Extensões vetoriais / busca textual
-- ------------------------------------------------------------
SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('vector', 'pgvector', 'pg_trgm', 'unaccent')
ORDER BY extname;

-- ------------------------------------------------------------
-- (k) memory tables — contagens (ajuste conforme (a))
-- ------------------------------------------------------------
SELECT 'memory_settings' AS tbl, count(*) AS rows FROM public.memory_settings
UNION ALL SELECT 'memory_processing_locks', count(*) FROM public.memory_processing_locks
UNION ALL SELECT 'sanitization_jobs', count(*) FROM public.sanitization_jobs;

-- ------------------------------------------------------------
-- (l) Existe alguma coluna de ESCOPO/GLOBAL em documents? (confirmar ausência)
-- ------------------------------------------------------------
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'documents'
  AND (column_name ILIKE '%scope%' OR column_name ILIKE '%global%' OR column_name ILIKE '%visibility%');
