-- ============================================================
-- 38B — SEED do Auxiliar "Follow-up WhatsApp"  (REVISAR ANTES DE RODAR)
-- AutoBrokers Intelligence OS · auxiliary_templates + tenant_auxiliaries
--
-- OPCIONAL: o Auxiliar já FUNCIONA sem este seed (o backend tolera a ausência do
-- tenant_auxiliary e ainda gera o rascunho + registra custo por company_id).
-- Este seed só habilita o REGISTRO de execuções em auxiliary_runs (histórico).
--
-- NÃO roda nada automaticamente. Sem hardcode de UUID (lookup por slug/nome).
-- Confirme os nomes de colunas de auxiliary_templates/tenant_auxiliaries no seu schema.
-- ============================================================

-- 1) Template global do catálogo (idempotente por slug).
insert into public.auxiliary_templates (slug, name, description, category, is_active)
select
  'follow-up-whatsapp',
  'Follow-up WhatsApp',
  'Gera rascunhos humanos de follow-up e envia para aprovação humana (dry-run, sem envio real).',
  'Comunicação',
  true
where not exists (
  select 1 from public.auxiliary_templates where slug = 'follow-up-whatsapp'
);

-- 2) Instalar para a corretora (ex.: RAFAEL SEGUROS) — lookup por nome, sem UUID fixo.
--    Ajuste o filtro de company conforme necessário.
insert into public.tenant_auxiliaries (company_id, template_id, slug, status)
select
  c.id,
  t.id,
  'follow-up-whatsapp',
  'active'
from public.companies c
cross join public.auxiliary_templates t
where t.slug = 'follow-up-whatsapp'
  and c.company_name = 'RAFAEL SEGUROS'
  and not exists (
    select 1 from public.tenant_auxiliaries ta
    where ta.company_id = c.id and ta.slug = 'follow-up-whatsapp'
  );

-- Verificação (somente leitura):
-- select slug, is_active from public.auxiliary_templates where slug = 'follow-up-whatsapp';
-- select company_id, slug, status from public.tenant_auxiliaries where slug = 'follow-up-whatsapp';
