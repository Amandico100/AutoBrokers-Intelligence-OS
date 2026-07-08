-- SPEC-023 P3/P4 - Portais autenticados + auxiliar global de cobranca.
-- EXPAND-ONLY:
-- - config jsonb nas rotinas para especializacoes sem criar tabela paralela.
-- - config_default jsonb nos templates globais.
-- - ativa o template global "Cobranca de boletos atrasados".
-- - cria bucket privado portal-evidence para boletos/evidencias de portal.

alter table public.routines
  add column if not exists config jsonb not null default '{}'::jsonb;

alter table public.routine_templates
  add column if not exists config_default jsonb not null default '{}'::jsonb;

comment on column public.routines.config is
  'Configuracao estruturada da rotina. SPEC-023 usa kind=billing_collection sem criar motor paralelo.';

comment on column public.routine_templates.config_default is
  'Configuracao default do modelo global. Usar modelo copia para routines.config.';

insert into public.routine_templates
  (name, description, category, instructions, schedule_default, delivery_default, required, config_default, is_active, sort_order)
select
  'Cobranca de boletos atrasados',
  'Varre portais conectados, encontra parcelas atrasadas, baixa boletos e prepara cobranca por WhatsApp.',
  'Financeiro',
  'Acesse os portais das seguradoras selecionadas, identifique clientes com parcelas atrasadas, baixe os boletos disponiveis e gere um relatorio para a corretora. Nao envie mensagem ao cliente sem a configuracao/aprovacao da corretora.',
  '{"kind":"daily","time":"09:00","weekdays":[0,1,2,3,4]}'::jsonb,
  '{"channel":"whatsapp"}'::jsonb,
  '{"whatsapp":true,"portal":true,"infocap":true}'::jsonb,
  '{
    "kind":"billing_collection",
    "portal_keys":["allianz_corretor"],
    "approval_required":true,
    "send_mode":"test",
    "max_boletos_por_execucao":10,
    "management_provider":"infocap",
    "message_template":"Ola, {cliente_nome}. Identificamos uma parcela pendente do seu seguro com vencimento em {vencimento}, no valor de R$ {valor}. Segue o boleto para regularizacao."
  }'::jsonb,
  true,
  30
where not exists (
  select 1 from public.routine_templates where name = 'Cobranca de boletos atrasados'
);

update public.routine_templates
set
  description = 'Varre portais conectados, encontra parcelas atrasadas, baixa boletos e prepara cobranca por WhatsApp.',
  category = 'Financeiro',
  instructions = 'Acesse os portais das seguradoras selecionadas, identifique clientes com parcelas atrasadas, baixe os boletos disponiveis e gere um relatorio para a corretora. Nao envie mensagem ao cliente sem a configuracao/aprovacao da corretora.',
  schedule_default = '{"kind":"daily","time":"09:00","weekdays":[0,1,2,3,4]}'::jsonb,
  delivery_default = '{"channel":"whatsapp"}'::jsonb,
  required = '{"whatsapp":true,"portal":true,"infocap":true}'::jsonb,
  config_default = '{
    "kind":"billing_collection",
    "portal_keys":["allianz_corretor"],
    "approval_required":true,
    "send_mode":"test",
    "max_boletos_por_execucao":10,
    "management_provider":"infocap",
    "message_template":"Ola, {cliente_nome}. Identificamos uma parcela pendente do seu seguro com vencimento em {vencimento}, no valor de R$ {valor}. Segue o boleto para regularizacao."
  }'::jsonb,
  is_active = true,
  sort_order = 30,
  updated_at = now()
where name = 'Cobranca de boletos atrasados';

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'portal-evidence',
  'portal-evidence',
  false,
  20971520,
  array['application/pdf', 'image/jpeg', 'image/png']::text[]
)
on conflict (id) do update
set
  public = false,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types,
  updated_at = now();
