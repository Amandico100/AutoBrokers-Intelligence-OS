-- SEC-001 — Security Hardening Migration (IDEMPOTENTE, GUARDADA, NÃO-DESTRUTIVA).
-- Aplicar SOMENTE após rodar SEC-001-supabase-security-diagnostics.sql e revisar.
-- Tudo é guardado por checagem de existência (tabela/coluna/constraint), então
-- partes que não se aplicam ao seu schema simplesmente não rodam.
-- NÃO mexe em messages (realtime), buckets ou funções SECURITY DEFINER aqui —
-- esses ficam como follow-up manual revisado (ver report §riscos).

begin;

-- 1) memory_processing_locks: PRIMARY KEY em id (se a tabela e a coluna existirem e não houver PK).
do $$
begin
  if to_regclass('public.memory_processing_locks') is not null
     and exists (select 1 from information_schema.columns where table_schema='public' and table_name='memory_processing_locks' and column_name='id')
     and not exists (select 1 from pg_constraint k join pg_class c on c.oid=k.conrelid join pg_namespace n on n.oid=c.relnamespace
                     where n.nspname='public' and c.relname='memory_processing_locks' and k.contype='p')
  then
    execute 'alter table public.memory_processing_locks add constraint memory_processing_locks_pkey primary key (id)';
    raise notice 'PK adicionada em memory_processing_locks';
  end if;
end $$;

-- 2) Índices úteis para memória (guardados por existência de tabela/coluna).
do $$
begin
  if to_regclass('public.user_memories') is not null
     and exists (select 1 from information_schema.columns where table_schema='public' and table_name='user_memories' and column_name='company_id') then
    execute 'create index if not exists idx_user_memories_company on public.user_memories (company_id)';
  end if;
  if to_regclass('public.user_memories') is not null
     and exists (select 1 from information_schema.columns where table_schema='public' and table_name='user_memories' and column_name='user_id') then
    execute 'create index if not exists idx_user_memories_user on public.user_memories (user_id)';
  end if;
  if to_regclass('public.session_summaries') is not null
     and exists (select 1 from information_schema.columns where table_schema='public' and table_name='session_summaries' and column_name='company_id') then
    execute 'create index if not exists idx_session_summaries_company on public.session_summaries (company_id)';
  end if;
end $$;

-- 3) RLS + policy mínima de isolamento por company_id (guardado: só se a coluna existir).
--    Service role (backend) IGNORA RLS, então isto endurece acesso anon/auth sem
--    quebrar o backend. Revise no diagnostics se há acesso anon legítimo antes.
do $$
declare t text;
begin
  foreach t in array array['memory_settings', 'user_memories', 'session_summaries']
  loop
    if to_regclass('public.' || t) is not null
       and exists (select 1 from information_schema.columns where table_schema='public' and table_name=t and column_name='company_id') then
      execute format('alter table public.%I enable row level security', t);
      -- policy idempotente: cria só se ainda não existir.
      if not exists (select 1 from pg_policies where schemaname='public' and tablename=t and policyname=t || '_company_isolation') then
        execute format(
          'create policy %I on public.%I for all to authenticated using (company_id = (auth.jwt() ->> ''company_id'')::uuid) with check (company_id = (auth.jwt() ->> ''company_id'')::uuid)',
          t || '_company_isolation', t
        );
        raise notice 'RLS policy de isolamento criada em %', t;
      end if;
    else
      raise notice 'Pulado % (sem company_id ou tabela ausente) — tratar manualmente', t;
    end if;
  end loop;
end $$;

commit;

-- FOLLOW-UP MANUAL (NÃO automatizado aqui — alto risco):
--  a) messages: revisar policy anon SELECT ampla (realtime). Restringir por company/sessão
--     sem quebrar Realtime. Testar em staging.
--  b) buckets avatars/chat-media/voice-messages: avaliar tornar privados + signed URLs
--     (ver flag app-level MEDIA_PUBLIC_URLS_ENABLED). Só após plano de transição no frontend.
--  c) SECURITY DEFINER functions: fixar search_path explícito (set search_path = public, pg_temp)
--     e revisar grants, confirmando assinaturas exatas no diagnostics.
