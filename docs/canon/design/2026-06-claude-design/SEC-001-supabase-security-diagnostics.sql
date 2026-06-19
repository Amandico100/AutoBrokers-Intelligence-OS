-- SEC-001 — Supabase Security Diagnostics (READ-ONLY, RESULTADO ÚNICO).
-- Não altera nada. Cole TUDO no SQL Editor e clique Run uma vez: retorna UMA
-- tabela com todas as checagens (o editor mostra só o último result set, por isso
-- consolidamos em um único SELECT via UNION ALL). Colunas: check / object / status / detail.

with checks as (
  -- 1) RLS + nº de policies (memória, tenant_connections, documents, messages)
  select 'rls_policies' as check, c.relname as object,
         case when c.relrowsecurity then 'rls_on' else 'RLS_OFF' end as status,
         'policies=' || (select count(*) from pg_policies p where p.schemaname='public' and p.tablename=c.relname)::text as detail
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
  where n.nspname='public' and c.relkind='r'
    and c.relname in ('memory_settings','user_memories','session_summaries','memory_processing_locks','tenant_connections','documents','messages')

  union all
  -- 2) Colunas de escopo nas tabelas de memória (explica se a migration pôde criar policy)
  select 'memory_columns', t.table_name, 'columns',
         coalesce(string_agg(t.column_name, ',' order by t.column_name), '(nenhuma de company_id/user_id/agent_id)')
  from information_schema.columns t
  where t.table_schema='public'
    and t.table_name in ('memory_settings','user_memories','session_summaries')
    and t.column_name in ('company_id','user_id','agent_id')
  group by t.table_name

  union all
  -- 3) Policies amplas para anon (atenção a messages/realtime)
  select 'anon_policy', tablename || '.' || policyname, 'anon_role', coalesce(cmd,'?')
  from pg_policies
  where schemaname='public' and ('anon' = any(roles))

  union all
  -- 4) Buckets públicos
  select 'bucket', name, case when public then 'PUBLIC' else 'private' end, ''
  from storage.buckets

  union all
  -- 5) Funções SECURITY DEFINER + search_path
  select 'security_definer', p.proname, 'definer',
         coalesce(array_to_string(p.proconfig, ','), 'NO_search_path')
  from pg_proc p join pg_namespace n on n.oid = p.pronamespace
  where n.nspname='public' and p.prosecdef = true
    and p.proname in ('check_and_increment_rate_limit','create_user_account','debit_company_balance',
                      'get_token_usage_by_company','get_token_usage_report','get_user_for_login')

  union all
  -- 6) memory_processing_locks: tem PK?
  select 'pk', 'memory_processing_locks',
         case when exists (
           select 1 from pg_constraint k join pg_class c on c.oid=k.conrelid join pg_namespace n on n.oid=c.relnamespace
           where n.nspname='public' and c.relname='memory_processing_locks' and k.contype='p'
         ) then 'has_pk' else 'NO_PK' end, ''
  where to_regclass('public.memory_processing_locks') is not null

  union all
  -- 7) documents: campos de governança
  select 'documents_governance', column_name, 'present', data_type
  from information_schema.columns
  where table_schema='public' and table_name='documents'
    and column_name in ('audience','sensitivity','status','company_id')
)
select check, object, status, detail
from checks
order by check, object;
