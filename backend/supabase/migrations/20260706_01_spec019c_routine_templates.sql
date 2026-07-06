-- SPEC-019 C — Galeria de Rotinas Prontas (routine_templates) — EXPAND-ONLY.
-- Catalogo GLOBAL de rotinas prontas que a corretora liga com 1 clique: "Usar
-- modelo" pre-preenche a Nova rotina do motor F2 (nao e agente/blueprint novo).
--
-- APPLY:   SQL Editor do Supabase (idempotente — pode rodar de novo sem efeito).
-- VERIFY:  select name, is_active, required from public.routine_templates order by sort_order;
-- ROLLBACK: drop table if exists public.routine_templates;

create table if not exists public.routine_templates (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text not null default '',
  category text not null default 'Geral',
  instructions text not null,
  schedule_default jsonb not null default '{}'::jsonb,
  delivery_default jsonb not null default '{"channel":"whatsapp"}'::jsonb,
  required jsonb not null default '{}'::jsonb,  -- {whatsapp,web,infocap,portal}: bool
  is_active boolean not null default true,
  sort_order int not null default 100,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.routine_templates is
  'SPEC-019 C: catalogo global de rotinas prontas. required={whatsapp,web,infocap,portal}:bool; "Usar modelo" pre-preenche a Nova rotina do motor F2 (routines).';

create index if not exists idx_routine_templates_active
  on public.routine_templates (is_active, sort_order);

-- Seed inicial (idempotente por name).
insert into public.routine_templates
  (name, description, category, instructions, schedule_default, delivery_default, required, is_active, sort_order)
select
  'Noticias do setor',
  'Todo dia de manha, um resumo curto das principais noticias de seguros no Brasil.',
  'Informacao',
  'Pesquise na web as principais noticias e novidades do setor de seguros no Brasil nas ultimas 24 horas. Faca um resumo em ate 5 topicos curtos, com linguagem direta para um corretor de seguros. Se houver algo relevante para corretoras (regulacao SUSEP, novos produtos, sinistralidade), destaque no fim.',
  '{"kind":"daily","time":"08:00"}'::jsonb,
  '{"channel":"whatsapp"}'::jsonb,
  '{"whatsapp":true,"web":true}'::jsonb,
  true, 10
where not exists (select 1 from public.routine_templates where name = 'Noticias do setor');

insert into public.routine_templates
  (name, description, category, instructions, schedule_default, delivery_default, required, is_active, sort_order)
select
  'Resumo do dia do agente',
  'No fim do dia, um panorama do que o agente atendeu e o que ficou pendente.',
  'Operacao',
  'Faca um resumo do dia da corretora: principais assuntos atendidos, apolices consultadas e pendencias que ficaram para amanha. Seja objetivo, em topicos, para o corretor ler rapido no fim do expediente.',
  '{"kind":"daily","time":"18:00"}'::jsonb,
  '{"channel":"whatsapp"}'::jsonb,
  '{"whatsapp":true}'::jsonb,
  true, 20
where not exists (select 1 from public.routine_templates where name = 'Resumo do dia do agente');

insert into public.routine_templates
  (name, description, category, instructions, schedule_default, delivery_default, required, is_active, sort_order)
select
  'Cobranca de boletos atrasados',
  'Entra nos portais, encontra boletos atrasados e envia no WhatsApp do cliente + relatorio. (Requer Portais — em breve.)',
  'Financeiro',
  'Acesse os portais das seguradoras configurados, identifique os boletos atrasados dos clientes da corretora e, para cada um, envie um lembrete educado no WhatsApp do cliente com o boleto. No fim, gere um relatorio para o corretor com quem foi cobrado e os valores.',
  '{"kind":"daily","time":"09:00"}'::jsonb,
  '{"channel":"whatsapp"}'::jsonb,
  '{"whatsapp":true,"portal":true}'::jsonb,
  false, 30
where not exists (select 1 from public.routine_templates where name = 'Cobranca de boletos atrasados');
