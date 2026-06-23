-- SPEC-014 C-FIX-1 (D) — Conexão singleton por corretora (evita InfoCap/conector duplicado).
-- Reusa tenant_connections (sem tabela paralela). Arquivar, nunca apagar.
-- A duplicata InfoCap da Resulta (72936a93, draft, sem segredo) JÁ foi arquivada nesta sessão (status='archived').
-- ============================================================================
-- PRE-CHECK (rodar ANTES do APPLY — precisa retornar 0 linhas)
-- ============================================================================
-- Mostra qualquer corretora com mais de 1 conexão NÃO-arquivada para o mesmo template:
-- select company_id, connector_template_id, count(*)
--   from public.tenant_connections where status <> 'archived'
--   group by 1,2 having count(*) > 1;
--   -> Se aparecer algo, arquivar as duplicadas (status='archived', metadata.archived=...) antes do APPLY.

-- ============================================================================
-- APPLY
-- ============================================================================
begin;

-- 1 conexão ATIVA (não-arquivada) por corretora + template. Drafts duplicados também bloqueados.
create unique index if not exists uniq_active_connection_per_template
  on public.tenant_connections (company_id, connector_template_id)
  where status <> 'archived';

commit;

-- ============================================================================
-- VERIFY
-- ============================================================================
-- select indexname from pg_indexes where tablename='tenant_connections' and indexname='uniq_active_connection_per_template';
-- -- tentar criar 2a conexão infocap p/ a mesma corretora deve falhar com unique_violation.

-- ============================================================================
-- ROLLBACK
-- ============================================================================
-- begin; drop index if exists public.uniq_active_connection_per_template; commit;

-- ============================================================================
-- (Histórico) Arquivamento da duplicata InfoCap da Resulta — JÁ EXECUTADO:
-- update public.tenant_connections set status='archived',
--   metadata = metadata || '{"archived":{"reason":"infocap_duplicate"}}'::jsonb
--   where id='72936a93-f80c-43b7-957d-fa680248ed88' and encrypted_secret_ref is null;
