-- SPEC-013 Fase B — Runbook 01: classificação de empresa + Blueprint Studio
-- Aplicar no Supabase APÓS o deploy. NÃO aplicado por mim. Ordem: este runbook 01,
-- depois o runbook 02 (agent_blueprint_releases). Transacional e idempotente.
-- ============================================================================
-- APPLY
-- ============================================================================
begin;

do $$
begin
  if to_regclass('public.companies') is null then
    raise exception 'precondition_failed: tabela companies ausente';
  end if;
end $$;

-- 1) coluna de classificação (default seguro = client; tudo que existe continua client)
alter table public.companies add column if not exists company_kind text not null default 'client';

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'companies_company_kind_check') then
    alter table public.companies
      add constraint companies_company_kind_check
      check (company_kind in ('client','platform_knowledge','platform_blueprint_studio'));
  end if;
end $$;

create index if not exists idx_companies_company_kind on public.companies (company_kind);

-- 2) classifica a empresa de conhecimento global (se existir pelo nome canônico)
update public.companies
   set company_kind = 'platform_knowledge', updated_at = now()
 where company_name = 'AutoBrokers Global Knowledge'
   and company_kind <> 'platform_knowledge';

-- 3) cria o AutoBrokers Blueprint Studio (idempotente por nome). Empresa técnica da
--    plataforma: não-cliente, não-cobrável, oculta das listagens normais.
insert into public.companies (company_name, status, company_kind)
select 'AutoBrokers Blueprint Studio', 'active', 'platform_blueprint_studio'
where not exists (
  select 1 from public.companies where company_name = 'AutoBrokers Blueprint Studio'
);

commit;

-- ============================================================================
-- VERIFY (rodar após APPLY — esperado: Global Knowledge=platform_knowledge,
--         Blueprint Studio=platform_blueprint_studio, demais=client)
-- ============================================================================
-- select company_name, company_kind, status
--   from public.companies
--  where company_kind <> 'client'
--  order by company_kind;
-- select count(*) as clientes from public.companies where company_kind = 'client';

-- ============================================================================
-- ROLLBACK (escopado e seguro: só remove o Studio se ele NÃO tiver agentes)
-- ============================================================================
-- begin;
--   delete from public.companies c
--    where c.company_name = 'AutoBrokers Blueprint Studio'
--      and c.company_kind = 'platform_blueprint_studio'
--      and not exists (select 1 from public.agents a where a.company_id = c.id);
--   update public.companies set company_kind = 'client'
--    where company_name = 'AutoBrokers Global Knowledge';
--   -- Opcional (só se quiser remover a classificação por completo):
--   -- alter table public.companies drop column if exists company_kind;
-- commit;
