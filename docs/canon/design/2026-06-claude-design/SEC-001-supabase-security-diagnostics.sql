-- SEC-001 — Supabase Security Diagnostics (READ-ONLY).
-- Não altera nada. Rode no SQL editor do Supabase e leve o resultado ao report.
-- Cobre os riscos confirmados pela auditoria RAG0.1.

-- 1) RLS habilitado mas SEM policies (memória).
select n.nspname as schema, c.relname as table, c.relrowsecurity as rls_enabled,
       (select count(*) from pg_policies p where p.schemaname = n.nspname and p.tablename = c.relname) as policy_count
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind = 'r'
  and c.relname in ('memory_settings', 'user_memories', 'session_summaries', 'memory_processing_locks', 'tenant_connections', 'documents', 'messages')
order by c.relname;

-- 2) Policies existentes nessas tabelas (ver roles/qual/cmd).
select schemaname, tablename, policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public'
  and tablename in ('memory_settings', 'user_memories', 'session_summaries', 'messages', 'tenant_connections', 'documents')
order by tablename, policyname;

-- 3) Policies amplas para anon (realtime/SELECT) — atenção a messages.
select schemaname, tablename, policyname, roles, cmd, qual
from pg_policies
where schemaname = 'public'
  and ('anon' = any (roles) or roles is null)
order by tablename, policyname;

-- 4) Buckets públicos (avatars/chat-media/voice-messages).
select id, name, public, created_at
from storage.buckets
order by public desc, name;

-- 5) Funções SECURITY DEFINER + search_path mutável.
select n.nspname as schema, p.proname as function, p.prosecdef as security_definer,
       pg_get_function_identity_arguments(p.oid) as args,
       (select string_agg(cfg, ', ') from unnest(coalesce(p.proconfig, array[]::text[])) cfg) as proconfig
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.prosecdef = true
  and p.proname in ('check_and_increment_rate_limit', 'create_user_account', 'debit_company_balance',
                    'get_token_usage_by_company', 'get_token_usage_report', 'get_user_for_login')
order by p.proname;

-- 6) memory_processing_locks: tem primary key?
select c.relname as table,
       (select count(*) from pg_constraint k where k.conrelid = c.oid and k.contype = 'p') as pk_count
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relname = 'memory_processing_locks';

-- 7) documents: campos de governança presentes? (audience/sensitivity/status)
select column_name, data_type
from information_schema.columns
where table_schema = 'public' and table_name = 'documents'
  and column_name in ('audience', 'sensitivity', 'status', 'company_id')
order by column_name;

-- 8) tenant_connections: RLS + colunas de escopo (company_id).
select c.relrowsecurity as rls_enabled,
       (select count(*) from pg_policies p where p.schemaname='public' and p.tablename='tenant_connections') as policy_count
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and c.relname='tenant_connections';
