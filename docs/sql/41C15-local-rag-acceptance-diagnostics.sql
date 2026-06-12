-- 41C.1.5 — Local RAG Acceptance Diagnostics (SELECT-only)
-- ------------------------------------------------------------------------
-- SOMENTE LEITURA. Nenhum DDL, nenhuma migração, nenhuma escrita.
-- NUNCA seleciona conteúdo de chunk/documento, mensagens de cliente,
-- tokens, prompts completos, secrets ou PII.
-- Tolerante: se uma coluna não existir no seu schema, ajuste/remova o bloco.
-- Rodar bloco a bloco no SQL editor (Supabase) como admin.
-- ========================================================================

-- ============== BLOCO A — documents recentes (sem conteúdo) =============
-- Visão geral dos últimos documentos enviados (metadados apenas).
SELECT
    d.id,
    d.company_id,
    d.agent_id,
    d.file_name,
    d.file_type,
    d.status,
    d.chunks_count,
    d.ingestion_strategy,
    d.ingestion_mode,
    d.scope,
    d.knowledge_class,
    d.curation_status,
    d.qdrant_collection,
    d.created_at,
    d.updated_at,
    d.error_message
FROM public.documents d
ORDER BY d.created_at DESC
LIMIT 50;

-- ============== BLOCO B — contagens (company/agent/status/scope) ========
-- B1: por empresa + status
SELECT company_id, status, COUNT(*) AS n
FROM public.documents
GROUP BY company_id, status
ORDER BY company_id, status;

-- B2: por empresa + agente (agent_id NULL = tenant-wide)
SELECT company_id, agent_id, COUNT(*) AS n
FROM public.documents
GROUP BY company_id, agent_id
ORDER BY company_id, agent_id NULLS FIRST;

-- B3: por escopo (deve ser majoritariamente 'agent'/'tenant' nesta fase)
SELECT scope, COUNT(*) AS n
FROM public.documents
GROUP BY scope
ORDER BY n DESC;

-- ============== BLOCO C — agents / subagents (sem prompt) ===============
SELECT
    a.id,
    a.company_id,
    a.slug,
    a.name,
    a.is_subagent,
    a.retrieval_mode,
    a.is_hyde_enabled,
    a.allow_direct_chat
FROM public.agents a
ORDER BY a.company_id, a.is_subagent, a.name
LIMIT 100;

-- ============== BLOCO D — RLS / policies de documents ===================
-- D1: RLS habilitado?
SELECT n.nspname AS schema, c.relname AS table, c.relrowsecurity AS rls_enabled
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'documents';

-- D2: policies existentes (nome/cmd/roles), sem expor expressão sensível
SELECT schemaname, tablename, policyname, permissive, roles, cmd
FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'documents'
ORDER BY policyname;

-- ============== BLOCO E — conversation_logs com RAG (sem conteúdo) ======
-- Apenas métricas técnicas; NÃO selecionar user_question/assistant_response/rag_chunks.
SELECT
    cl.id,
    cl.company_id,
    cl.agent_id,
    cl.rag_chunks_count,
    cl.search_strategy,
    cl.retrieval_score,
    cl.rag_search_time_ms,
    cl.created_at
FROM public.conversation_logs cl
WHERE cl.rag_chunks_count IS NOT NULL
ORDER BY cl.created_at DESC
LIMIT 50;

-- E2: ALERTA de regressão — chunks recuperados mas score zerado/sem estratégia
-- (sintoma dos bugs 41C.1.2/41C.1.3/41C.1.4). Esperado: 0 linhas idealmente.
SELECT
    cl.id,
    cl.company_id,
    cl.agent_id,
    cl.rag_chunks_count,
    cl.search_strategy,
    cl.retrieval_score,
    cl.created_at
FROM public.conversation_logs cl
WHERE cl.rag_chunks_count >= 1
  AND COALESCE(cl.retrieval_score, 0) = 0
ORDER BY cl.created_at DESC
LIMIT 50;

-- ============== BLOCO F — ALERTA: scope global antes da ativação ========
-- Esperado nesta fase: 0 linhas. Qualquer linha aqui é um ALERTA
-- (conhecimento global não deve existir antes do batch oficial 41C.2C).
SELECT
    d.id,
    d.company_id,
    d.agent_id,
    d.file_name,
    d.scope,
    d.knowledge_class,
    d.curation_status,
    d.created_at
FROM public.documents d
WHERE d.scope IN ('global_autobrokers', 'global_carrier')
ORDER BY d.created_at DESC;

-- ============== BLOCO G — documents com status 'failed' =================
-- Falhas de ingestão (com motivo). Útil para distinguir DB × MinIO × Qdrant.
SELECT
    d.id,
    d.company_id,
    d.agent_id,
    d.file_name,
    d.file_type,
    d.status,
    d.error_message,
    d.created_at,
    d.updated_at
FROM public.documents d
WHERE d.status = 'failed'
ORDER BY d.created_at DESC
LIMIT 50;
