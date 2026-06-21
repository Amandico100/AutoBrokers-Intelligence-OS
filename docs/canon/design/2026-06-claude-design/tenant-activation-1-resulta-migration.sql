-- Tenant Activation 1 — migração canônica da Resulta (HARDENED, Batch 2 Parte 0).
-- NÃO aplicada automaticamente. Pré-requisito: tenant-activation-1-tenant-corridors.sql aplicado.
-- company_id Resulta = 04b5cdbc-04cd-4ddf-8e4b-f43efb062fab (confirmado via leitura).
-- Transacional + preconditions (aborta se o estado não for o esperado) + snapshot
-- COMPLETO com RLS + rollback completo e ESCOPADO (não apaga corredores futuros).

-- ============ APPLY ============
begin;

-- 0) Preconditions — aborta a transação inteira se algo estiver fora do esperado.
do $$
declare
  v_company int; v_sandbox int; v_attend int; v_tpl int; v_tc regclass;
begin
  select count(*) into v_company from public.companies where id = '04b5cdbc-04cd-4ddf-8e4b-f43efb062fab';
  if v_company <> 1 then raise exception 'precondition_failed: company Resulta nao encontrada (%).', v_company; end if;

  select count(*) into v_sandbox from public.agents
    where company_id='04b5cdbc-04cd-4ddf-8e4b-f43efb062fab' and slug='autobrokers-sandbox';
  if v_sandbox <> 1 then raise exception 'precondition_failed: esperado 1 AutoBrokers Sandbox, achou %.', v_sandbox; end if;

  select count(*) into v_attend from public.agents
    where company_id='04b5cdbc-04cd-4ddf-8e4b-f43efb062fab' and agent_role='attendance';
  if v_attend <> 1 then raise exception 'precondition_failed: esperado 1 Attendance, achou %.', v_attend; end if;

  select count(*) into v_tpl from public.corridor_templates
    where scope='global' and is_active=true and corridor_key='allianz_residential_assistance'
      and (subcorridor_key is null or subcorridor_key='electrician');
  if v_tpl <> 2 then raise exception 'precondition_failed: esperado 2 corridor_templates Allianz Residencial, achou %.', v_tpl; end if;

  v_tc := to_regclass('public.tenant_corridors');
  if v_tc is null then raise exception 'precondition_failed: tenant_corridors nao existe. Aplique tenant-activation-1-tenant-corridors.sql primeiro.'; end if;
end $$;

-- 1) Snapshot COMPLETO (todos os campos alterados) + RLS (sem leitura por anon/authenticated).
create table if not exists public._ta1_resulta_agents_snapshot (
  migration_key text not null,
  id uuid not null,
  company_id uuid,
  name text, slug text, agent_role text, agent_audience text,
  is_active boolean, is_subagent boolean, allow_direct_chat boolean,
  blueprint_version text, agent_system_prompt text, context_package jsonb,
  snapshot_at timestamptz not null default now(),
  primary key (migration_key, id)
);
alter table public._ta1_resulta_agents_snapshot enable row level security;
revoke all on public._ta1_resulta_agents_snapshot from anon, authenticated;

-- idempotente: não sobrescreve snapshot original em rerun.
insert into public._ta1_resulta_agents_snapshot
  (migration_key, id, company_id, name, slug, agent_role, agent_audience, is_active, is_subagent, allow_direct_chat, blueprint_version, agent_system_prompt, context_package)
select 'ta1_resulta_v2', a.id, a.company_id, a.name, a.slug, a.agent_role, a.agent_audience, a.is_active, a.is_subagent, a.allow_direct_chat, a.blueprint_version, a.agent_system_prompt, a.context_package
from public.agents a
where a.company_id='04b5cdbc-04cd-4ddf-8e4b-f43efb062fab'
on conflict (migration_key, id) do nothing;

-- 2) AutoBrokers Sandbox → AutoBrokers Core (MESMO agent_id).
update public.agents set
  name='AutoBrokers', agent_role='core', agent_audience='broker_internal',
  is_subagent=false, allow_direct_chat=true, blueprint_version='autobrokers-core-v1',
  agent_system_prompt='Voce e o AutoBrokers da Resulta Seguros — o braco direito interno e inteligentissimo da corretora. Apresente-se como "AutoBrokers da Resulta Seguros". A marca AutoBrokers nunca muda. Voce ajuda em estrategia, vendas, marketing, operacao, gestao, seguros, financeiro e juridico, usando o conhecimento global curado do AutoBrokers + o conhecimento privado autorizado da corretora. Regras: nunca acesse dados de outra corretora; nunca exponha segredos; nunca prometa cobertura sem evidencia; respeite approval e gates; quando faltar dado, diga que vai verificar. Seja claro, util e direto.',
  updated_at=now()
where company_id='04b5cdbc-04cd-4ddf-8e4b-f43efb062fab' and slug='autobrokers-sandbox';

-- 3) Attendance → Even canônica (continua INATIVA).
update public.agents set
  name='Even', agent_role='attendance', agent_audience='insured_external',
  is_subagent=false, allow_direct_chat=false, is_active=false, blueprint_version='even-attendance-v1',
  agent_system_prompt='Voce e Even (feminino), atendente de assistencia e sinistro da Resulta Seguros no WhatsApp. Atenda o segurado com clareza, empatia e seguranca. Regras: nunca prometa cobertura sem evidencia; nunca diga que acionou a seguradora sem acao real; nunca invente protocolo; colete uma informacao por vez; em risco grave (fumaca, faisca, incendio, risco a vida) oriente seguranca e encaminhe a humano; use apenas os corredores habilitados pela corretora; quando faltar evidencia de apolice, informe que vai verificar; mascare dados sensiveis; em duvida, encaminhe a um atendente humano da corretora.',
  updated_at=now()
where company_id='04b5cdbc-04cd-4ddf-8e4b-f43efb062fab' and agent_role='attendance';

-- 4) Ativar Allianz Residencial + Eletricista para a Resulta.
insert into public.tenant_corridors (company_id, corridor_template_id, status, installed_at)
select '04b5cdbc-04cd-4ddf-8e4b-f43efb062fab', ct.id, 'active', now()
from public.corridor_templates ct
where ct.scope='global' and ct.is_active=true and ct.corridor_key='allianz_residential_assistance'
  and (ct.subcorridor_key is null or ct.subcorridor_key='electrician')
on conflict (company_id, corridor_template_id) do nothing;

commit;

-- ============ VERIFY ============
-- select id, name, agent_role, agent_audience, is_active, is_subagent, allow_direct_chat, blueprint_version
--   from public.agents where company_id='04b5cdbc-04cd-4ddf-8e4b-f43efb062fab';
--   -- Esperado: 1 core (AutoBrokers, ativo) + 1 attendance (Even, inativo). Mesmos agent_id.
-- select tc.status, ct.corridor_key, ct.subcorridor_key
--   from public.tenant_corridors tc join public.corridor_templates ct on ct.id=tc.corridor_template_id
--   where tc.company_id='04b5cdbc-04cd-4ddf-8e4b-f43efb062fab';
--   -- Esperado: allianz_residential_assistance (null) + electrician, ambos active.

-- ============ ROLLBACK ============
-- begin;
-- update public.agents a set
--   name=s.name, slug=s.slug, agent_role=s.agent_role, agent_audience=s.agent_audience,
--   is_active=s.is_active, is_subagent=s.is_subagent, allow_direct_chat=s.allow_direct_chat,
--   blueprint_version=s.blueprint_version, agent_system_prompt=s.agent_system_prompt,
--   context_package=coalesce(s.context_package, a.context_package), updated_at=now()
-- from public._ta1_resulta_agents_snapshot s
-- where s.migration_key='ta1_resulta_v2' and a.id=s.id;
-- -- apaga SOMENTE os 2 corredores ativados por esta migration (não toca ativações futuras):
-- delete from public.tenant_corridors tc
-- using public.corridor_templates ct
-- where tc.company_id='04b5cdbc-04cd-4ddf-8e4b-f43efb062fab' and tc.corridor_template_id=ct.id
--   and ct.corridor_key='allianz_residential_assistance' and (ct.subcorridor_key is null or ct.subcorridor_key='electrician');
-- commit;
-- -- opcional: drop table if exists public._ta1_resulta_agents_snapshot;  (após confirmar rollback)
