-- SPEC-014 C-FIX-2 (D) — InfoCap recovery (FEITO) + singleton index. Substitui o uso prático do SPEC-014-03.
-- A recuperação da Resulta JÁ foi executada nesta sessão (via MCP, seguro/reversível):
--   * segredo movido da conexão errada (68e06728 "InfoCap 1") para a canônica (dfbfdea5 "InfoCap — Resulta Seguros");
--   * base_url global garantido na canônica;
--   * 68e06728 arquivada (status='archived', segredo limpo);
--   * resultado: 1 InfoCap não-arquivada para a Resulta, com segredo + base_url + 7 permissões.
-- ============================================================================
-- PRE-CHECK (precisa retornar 0 linhas antes do APPLY do índice)
-- ============================================================================
-- select c.company_name, tc.connector_template_id, count(*) as n
--   from public.tenant_connections tc join public.companies c on c.id=tc.company_id
--   where tc.status <> 'archived'
--   group by 1,2 having count(*) > 1;
-- OBS (2026-06-23): a RAFAEL SEGUROS (empresa de teste) ainda tem conexões duplicadas de teste.
--   Arquive-as pelo Dashboard → Conectores → menu (⋯) → "Arquivar conexão" antes de aplicar o índice.
--   A Resulta já está OK (1 InfoCap).

-- ============================================================================
-- APPLY (após o PRE-CHECK retornar 0 linhas)
-- ============================================================================
begin;
create unique index if not exists uniq_active_connection_per_template
  on public.tenant_connections (company_id, connector_template_id)
  where status <> 'archived';
commit;

-- ============================================================================
-- VERIFY
-- ============================================================================
-- select indexname from pg_indexes where tablename='tenant_connections' and indexname='uniq_active_connection_per_template';
-- select c.company_name, tc.name, tc.status, (tc.encrypted_secret_ref is not null) as has_secret, tc.connection_config
--   from public.tenant_connections tc join public.connector_templates ct on ct.id=tc.connector_template_id
--   join public.companies c on c.id=tc.company_id where ct.slug='infocap' order by c.company_name, tc.status;

-- ============================================================================
-- ROLLBACK
-- ============================================================================
-- begin; drop index if exists public.uniq_active_connection_per_template; commit;
