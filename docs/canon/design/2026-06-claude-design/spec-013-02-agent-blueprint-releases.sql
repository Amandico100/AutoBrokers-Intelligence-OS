-- SPEC-013 Fase B — Runbook 02: agent_blueprint_releases (releases globais imutáveis)
-- Aplicar APÓS o runbook 01. NÃO aplicado por mim. Transacional, RLS, imutabilidade
-- por trigger. A release é o artefato global sanitizado; instâncias citam blueprint_key+versão.
-- ============================================================================
-- APPLY
-- ============================================================================
begin;

create table if not exists public.agent_blueprint_releases (
  id uuid primary key default gen_random_uuid(),
  blueprint_key text not null,
  semantic_version text not null,
  status text not null default 'draft' check (status in ('draft','published','retired')),
  source_company_id uuid references public.companies(id) on delete set null,
  source_agent_id uuid references public.agents(id) on delete set null,
  artifact jsonb not null,
  artifact_hash text not null,
  schema_version text not null default 'blueprint-artifact-v1',
  changelog text,
  risk_level text not null default 'low' check (risk_level in ('low','medium','high')),
  declared_capability_keys text[] not null default '{}',
  created_by uuid,
  created_at timestamptz not null default now(),
  published_at timestamptz,
  retired_at timestamptz,
  unique (blueprint_key, semantic_version)
);

create index if not exists idx_abr_key_status on public.agent_blueprint_releases (blueprint_key, status);
create index if not exists idx_abr_status on public.agent_blueprint_releases (status);

-- Imutabilidade: release publicada não pode ser alterada nem apagada; só pode ir
-- de 'published' -> 'retired' (sem mudar o artefato/hash/chave/versão/capabilities).
create or replace function public.tg_abr_immutable()
returns trigger language plpgsql as $$
begin
  if (tg_op = 'DELETE') then
    if old.status = 'published' then
      raise exception 'release_imutavel: nao apague release publicada (retire em vez de apagar)';
    end if;
    return old;
  end if;
  if (old.status = 'published') then
    if (new.status = 'retired'
        and new.artifact is not distinct from old.artifact
        and new.artifact_hash = old.artifact_hash
        and new.blueprint_key = old.blueprint_key
        and new.semantic_version = old.semantic_version
        and new.declared_capability_keys = old.declared_capability_keys) then
      return new;
    end if;
    raise exception 'release_imutavel: release publicada so pode ser retirada, nunca alterada';
  end if;
  return new;
end $$;

drop trigger if exists trg_abr_immutable on public.agent_blueprint_releases;
create trigger trg_abr_immutable
  before update or delete on public.agent_blueprint_releases
  for each row execute function public.tg_abr_immutable();

alter table public.agent_blueprint_releases enable row level security;
revoke all on public.agent_blueprint_releases from anon, authenticated;
drop policy if exists abr_service_all on public.agent_blueprint_releases;
create policy abr_service_all on public.agent_blueprint_releases
  for all to service_role using (true) with check (true);

commit;

-- ============================================================================
-- VERIFY
-- ============================================================================
-- select to_regclass('public.agent_blueprint_releases') as tabela;
-- select relrowsecurity from pg_class where relname='agent_blueprint_releases';
-- select polname from pg_policies where tablename='agent_blueprint_releases';
-- select tgname from pg_trigger where tgrelid='public.agent_blueprint_releases'::regclass and not tgisinternal;
-- -- teste de imutabilidade (deve FALHAR ao tentar alterar uma publicada):
-- --   update public.agent_blueprint_releases set changelog='x' where status='published';

-- ============================================================================
-- ROLLBACK
-- ============================================================================
-- begin;
--   drop trigger if exists trg_abr_immutable on public.agent_blueprint_releases;
--   drop function if exists public.tg_abr_immutable();
--   drop table if exists public.agent_blueprint_releases;
-- commit;
