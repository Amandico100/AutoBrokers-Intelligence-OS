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

-- Read (43P-FINAL-2A): lê o storageState cifrado por uuid, com guarda cross-tenant
-- (o name do secret precisa pertencer à mesma company+account). Só service_role.
create or replace function public.portal_vault_read_session(
  p_company_id uuid,
  p_portal_account_id text,
  p_storage_ref text
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_secret text;
  v_name text;
begin
  select decrypted_secret, name into v_secret, v_name
    from vault.decrypted_secrets
   where id = p_storage_ref::uuid;
  if v_secret is null then
    return null;
  end if;
  -- Guarda cross-tenant: o secret tem de ter sido criado para esta company+account.
  if v_name is null or v_name not like ('portal_session__' || p_company_id::text || '__' || p_portal_account_id || '__%') then
    return null;
  end if;
  return v_secret;
end;
$$;

revoke all on function public.portal_vault_read_session(uuid, text, text) from public, anon, authenticated;
grant execute on function public.portal_vault_read_session(uuid, text, text) to service_role;

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
-- drop function if exists public.portal_vault_read_session(uuid, text, text);
-- drop function if exists public.portal_vault_store_session(uuid, text, text, text, text);
-- drop function if exists public.portal_vault_probe();
