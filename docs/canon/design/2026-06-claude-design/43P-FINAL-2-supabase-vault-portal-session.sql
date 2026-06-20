-- 43P-FINAL-2 — Supabase Vault RPC para SessionRef de portal.
-- NÃO aplicado automaticamente. Aplicar no SQL editor (Supabase) como runbook.
-- Pré-requisito: extensão `supabase_vault` instalada (já está no projeto).
-- Princípio: SECURITY DEFINER + search_path fixo + execução só por service_role.
-- Armazena o storageState CIFRADO no Vault; retorna SÓ o uuid opaco (storage_ref).

-- ============ APPLY ============
-- Probe: o backend usa para detectar se a RPC existe (senão, falha fechado).
create or replace function public.portal_vault_probe()
returns boolean
language sql
security definer
set search_path = ''
as $$ select true $$;

revoke all on function public.portal_vault_probe() from public, anon, authenticated;
grant execute on function public.portal_vault_probe() to service_role;

-- Store: grava o segredo no Vault e devolve o uuid (opaco).
create or replace function public.portal_vault_store_session(
  p_company_id uuid,
  p_portal_account_id text,
  p_provider text,
  p_secret text,
  p_name text
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_id uuid;
begin
  -- vault.create_secret(secret, name, description) -> uuid
  v_id := vault.create_secret(
    p_secret,
    p_name,
    'portal session storageState | company=' || p_company_id::text || ' | account=' || p_portal_account_id || ' | provider=' || p_provider
  );
  return v_id;
end;
$$;

revoke all on function public.portal_vault_store_session(uuid, text, text, text, text) from public, anon, authenticated;
grant execute on function public.portal_vault_store_session(uuid, text, text, text, text) to service_role;

-- ============ VERIFY ============
-- 1) Funções existem e são SECURITY DEFINER com search_path vazio:
-- select proname, prosecdef, proconfig
--   from pg_proc where proname in ('portal_vault_probe','portal_vault_store_session');
-- Esperado: prosecdef = true; proconfig contém 'search_path='.
--
-- 2) Permissões: anon/authenticated NÃO podem executar:
-- select grantee, privilege_type
--   from information_schema.role_routine_grants
--   where routine_name in ('portal_vault_probe','portal_vault_store_session');
-- Esperado: apenas service_role (e owner) com EXECUTE.
--
-- 3) Smoke (como service_role, NÃO em produção com dado real):
-- select public.portal_vault_probe();                  -- true
-- select public.portal_vault_store_session(gen_random_uuid(),'acc_test','browserbase','{"k":"v"}','t_test'); -- uuid

-- ============ ROLLBACK ============
-- drop function if exists public.portal_vault_store_session(uuid, text, text, text, text);
-- drop function if exists public.portal_vault_probe();
