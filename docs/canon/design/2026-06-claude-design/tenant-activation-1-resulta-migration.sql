-- Tenant Activation 1 — migração canônica da Resulta Seguros.
-- NÃO aplicada automaticamente. Pré-requisito: tenant-activation-1-tenant-corridors.sql aplicado.
-- company_id Resulta = 04b5cdbc-04cd-4ddf-8e4b-f43efb062fab (confirmado).
-- Preserva agent_id; NÃO apaga conversas/custos/documentos.

-- ============ APPLY ============
-- 0) Snapshot p/ rollback (guarda estado anterior dos 2 agentes da Resulta).
create table if not exists public._ta1_resulta_agents_snapshot as
  select id, name, slug, agent_role, agent_audience, is_active, agent_system_prompt, now() as snapshot_at
  from public.agents where company_id = '04b5cdbc-04cd-4ddf-8e4b-f43efb062fab';

-- 1) AutoBrokers Sandbox  → AutoBrokers Core (MESMO agent_id; preserva referências).
update public.agents set
  name = 'AutoBrokers',
  agent_role = 'core',
  agent_audience = 'broker_internal',
  is_subagent = false,
  allow_direct_chat = true,
  blueprint_version = 'autobrokers-core-v1',
  agent_system_prompt = 'Voce e o AutoBrokers da Resulta Seguros — o braco direito interno e inteligentissimo da corretora. Apresente-se como "AutoBrokers da Resulta Seguros". A marca AutoBrokers nunca muda. Voce ajuda em estrategia, vendas, marketing, operacao, gestao, seguros, financeiro e juridico, usando o conhecimento global curado do AutoBrokers + o conhecimento privado autorizado da corretora. Regras: nunca acesse dados de outra corretora; nunca exponha segredos; nunca prometa cobertura sem evidencia; respeite approval e gates; quando faltar dado, diga que vai verificar. Seja claro, util e direto.',
  updated_at = now()
where company_id = '04b5cdbc-04cd-4ddf-8e4b-f43efb062fab'
  and slug = 'autobrokers-sandbox';

-- 2) Attendance existente (criado no 42X5B) → Even canônica (continua INATIVA).
update public.agents set
  name = 'Even',
  agent_role = 'attendance',
  agent_audience = 'insured_external',
  is_subagent = false,
  allow_direct_chat = false,
  is_active = false,
  blueprint_version = 'even-attendance-v1',
  agent_system_prompt = 'Voce e Even (feminino), atendente de assistencia e sinistro da Resulta Seguros no WhatsApp. Atenda o segurado com clareza, empatia e seguranca. Regras: nunca prometa cobertura sem evidencia; nunca diga que acionou a seguradora sem acao real; nunca invente protocolo; colete uma informacao por vez; em risco grave (fumaca, faisca, incendio, risco a vida) oriente seguranca e encaminhe a humano; use apenas os corredores habilitados pela corretora; quando faltar evidencia de apolice, informe que vai verificar; mascare dados sensiveis; em duvida, encaminhe a um atendente humano da corretora.',
  updated_at = now()
where company_id = '04b5cdbc-04cd-4ddf-8e4b-f43efb062fab'
  and agent_role = 'attendance';

-- 3) Ativar Allianz Residencial + Eletricista para a Resulta (corredores globais).
insert into public.tenant_corridors (company_id, corridor_template_id, status, installed_at)
select '04b5cdbc-04cd-4ddf-8e4b-f43efb062fab', ct.id, 'active', now()
from public.corridor_templates ct
where ct.scope = 'global' and ct.is_active = true
  and ct.corridor_key = 'allianz_residential_assistance'
  and (ct.subcorridor_key is null or ct.subcorridor_key = 'electrician')
on conflict (company_id, corridor_template_id) do nothing;

-- ============ VERIFY ============
-- select id, name, agent_role, agent_audience, is_active, blueprint_version
--   from public.agents where company_id='04b5cdbc-04cd-4ddf-8e4b-f43efb062fab';
--   -- Esperado: 1 core (AutoBrokers, ativo) + 1 attendance (Even, inativo). Mesmos agent_id de antes.
-- select tc.status, ct.corridor_key, ct.subcorridor_key
--   from public.tenant_corridors tc join public.corridor_templates ct on ct.id=tc.corridor_template_id
--   where tc.company_id='04b5cdbc-04cd-4ddf-8e4b-f43efb062fab';
--   -- Esperado: allianz_residential_assistance (null) + electrician, ambos active.

-- ============ ROLLBACK ============
-- update public.agents a set
--   name=s.name, agent_role=s.agent_role, agent_audience=s.agent_audience,
--   is_active=s.is_active, agent_system_prompt=s.agent_system_prompt, updated_at=now()
--   from public._ta1_resulta_agents_snapshot s where a.id=s.id;
-- delete from public.tenant_corridors where company_id='04b5cdbc-04cd-4ddf-8e4b-f43efb062fab';
-- drop table if exists public._ta1_resulta_agents_snapshot;
