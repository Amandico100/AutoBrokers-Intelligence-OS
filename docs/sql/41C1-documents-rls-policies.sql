-- ============================================================
-- 41C.1 — RLS POLICIES para public.documents  (MANUAL — REVISAR ANTES DE RODAR)
-- AutoBrokers Intelligence OS · isolamento de documentos por empresa (defense-in-depth).
--
-- Contexto: public.documents está com RLS ENABLED mas ZERO policies (41C.0).
-- documents count = 0 → não há risco de bloquear documento existente.
-- O backend opera via service_role (RLS é defesa em profundidade; ainda assim a policy é necessária).
-- Espelha o padrão company-scoped já usado em public.integrations / public.leads
-- (company_id = (select users_v2.company_id from users_v2 where id = auth.uid())).
--
-- Idempotente (drop policy if exists). NÃO cria coluna, NÃO cria scope/global, NÃO altera dados.
-- NÃO roda automaticamente — o fundador cola no Supabase SQL Editor.
-- ============================================================

-- 1) Garantir RLS habilitado.
alter table public.documents enable row level security;

-- 2) Service role: acesso total (backend usa service_role).
drop policy if exists "Service role full access to documents" on public.documents;
create policy "Service role full access to documents"
  on public.documents
  to service_role
  using (true)
  with check (true);

-- 3) Authenticated: gerenciar APENAS documentos da própria empresa.
--    company_id resolvido por users_v2.company_id do auth.uid() (anti cross-tenant).
drop policy if exists "Users can manage own company documents" on public.documents;
create policy "Users can manage own company documents"
  on public.documents
  to authenticated
  using (
    company_id = (select u.company_id from public.users_v2 u where u.id = auth.uid())
  )
  with check (
    company_id = (select u.company_id from public.users_v2 u where u.id = auth.uid())
  );

-- ------------------------------------------------------------
-- Verificação (somente leitura)
-- ------------------------------------------------------------
select relrowsecurity as rls_enabled, relforcerowsecurity as rls_forced
from pg_class
where oid = 'public.documents'::regclass;

select policyname, cmd, roles
from pg_policies
where schemaname = 'public' and tablename = 'documents'
order by policyname;

select count(*) as documents_count from public.documents;
