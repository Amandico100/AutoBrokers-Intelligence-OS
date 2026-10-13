-- =============================================================
-- MIGRATION: 20261014_01_spec131b_catalogo
-- SPEC:      SPEC-131-B — G1 · a loja e a casca (o aplicativo de Renovação)
-- AUTOR:     builder G1 (Opus 5.5)            DATA: 2026-10-13
-- OBJETIVO:  o catálogo GLOBAL ganha capa, dúvidas, destaque e o ícone linear de cada aplicativo; nascem as linhas
--            `renovacao`, `cotacao` e `quem-cobra-menos`; a vitrine `renovacao-maxima` sai da loja; e o MEMBRO de cada
--            corretora ganha o "Meu WhatsApp de trabalho" (só o NÚMERO e quando a pessoa confirmou — nada pareado).
--
-- 📊 ANTES (13/10/2026, SELECT só leitura pelo MCP, projeto dcajcvlzcjbmyapmklil):
--    · auxiliary_templates: 34 colunas, sem cover_url / faq / featured_rank; `icon` text nulo-ável com
--      aprovacao·success·message-circle·radar·file-text·NULL·auxiliares (×10) — nenhum é nome lucide que a tela leia
--    · 16 linhas (6 available · 10 coming_soon); UNIQUE (slug); CHECKs de categories (6 valores), catalog_state
--      (available·coming_soon), status, execution_mode, trigger_type; `category` NOT NULL default 'operacao'
--    · tenant_auxiliaries com slug in (renovacao-maxima, renovacao, cotacao, quem-cobra-menos) → 0 (troca grátis)
--    · company_members: id·user_id·company_id·role·is_owner·status·created_at·funcoes; UNIQUE (user_id, company_id);
--      sem whatsapp_trabalho_*
--
-- APPLY (pelo GERENTE — o builder NÃO aplica; um arquivo, idempotente, expand-only, global):
--   A. auxiliary_templates + `cover_url text null` (1600×900 WebP ≤ 150 KB, sem texto; só https) · `faq jsonb null`
--      (lista de {pergunta, resposta}) · `featured_rank int null` (1 = o destaque do topo) + CHECKs NOT VALID → VALIDATE.
--   B. UPDATE de `icon` para o nome lucide de cada slug (laudo de design §2.4). Só troca o que ainda não é o novo.
--   C. INSERT das linhas `renovacao` (substitui a vitrine), `cotacao` e `quem-cobra-menos` (sem rotina, D-131-21)
--      `on conflict (slug) do nothing`. Nenhum nome de corretora ou de pessoa (CLAUDE.md §13.9).
--   D. `renovacao-maxima`: is_active=false (sai da vitrine; 📊 0 instalações; a linha FICA — nada se apaga).
--   E. company_members + `whatsapp_trabalho_e164 text null` (CHECK E.164 BR: +55 · DDD 11–99 sem zero · celular
--      9+8 dígitos ou fixo [2-5]+7) + `whatsapp_trabalho_confirmado_em timestamptz null` (CHECK: só com número).
--      ⛔ nada em `integrations`; nada é pareado. COMMENTs.
--
-- VERIFY (read-only · esperado: 3 · 4 · 19 · 0 · 3 · 0 · 1 · 2 · 2):
--   select (select count(*) from information_schema.columns where table_schema='public' and table_name='auxiliary_templates'
--             and column_name in ('cover_url','faq','featured_rank')) cols_catalogo,
--          (select count(*) from pg_constraint where conrelid='public.auxiliary_templates'::regclass and convalidated
--             and conname in ('ck_aux_templates_cover_url','ck_aux_templates_faq','ck_aux_templates_featured_rank',
--                             'ck_aux_templates_icon_lucide')) checks_catalogo,
--          (select count(*) from public.auxiliary_templates where icon ~ '^[A-Z][A-Za-z0-9]+$') icones_lucide,
--          (select count(*) from public.auxiliary_templates where is_active and status='active'
--             and (icon is null or icon !~ '^[A-Z][A-Za-z0-9]+$')) ativos_sem_icone,
--          (select count(*) from public.auxiliary_templates where slug in ('renovacao','cotacao','quem-cobra-menos')
--             and is_active and status='active' and catalog_state='available') linhas_novas,
--          (select count(*) from public.auxiliary_templates where slug='renovacao-maxima' and is_active) vitrine_antiga,
--          (select count(*) from public.auxiliary_templates where featured_rank=1) destaques,
--          (select count(*) from information_schema.columns where table_schema='public' and table_name='company_members'
--             and column_name in ('whatsapp_trabalho_e164','whatsapp_trabalho_confirmado_em')) cols_membro,
--          (select count(*) from pg_constraint where conrelid='public.company_members'::regclass and convalidated
--             and conname in ('ck_company_members_whatsapp_e164','ck_company_members_whatsapp_confirmado')) checks_membro;
--
-- VERIFY comportamental (o DO desfaz o que testa — raise P0001 no fim do sub-bloco; NADA fica):
--   do $$
--   declare m uuid; t uuid; res text[] := '{}';
--   begin
--     select id into m from public.company_members order by created_at limit 1;
--     select id into t from public.auxiliary_templates where slug='renovacao';
--     if m is null or t is null then raise exception 'VERIFY 20261014_01: falta membro ou a linha renovacao'; end if;
--     begin
--       begin update public.company_members set whatsapp_trabalho_e164='+5511987654321' where id=m;
--             res := res || 'celular=aceito'::text; exception when check_violation then res := res || 'celular=RECUSADO'::text; end;
--       begin update public.company_members set whatsapp_trabalho_e164='+551133334444' where id=m;
--             res := res || 'fixo=aceito'::text; exception when check_violation then res := res || 'fixo=RECUSADO'::text; end;
--       begin update public.company_members set whatsapp_trabalho_e164='11987654321' where id=m;
--             res := res || 'sem_mais=ACEITO'::text; exception when check_violation then res := res || 'sem_mais=recusado'::text; end;
--       begin update public.company_members set whatsapp_trabalho_e164='+5501987654321' where id=m;
--             res := res || 'ddd_zero=ACEITO'::text; exception when check_violation then res := res || 'ddd_zero=recusado'::text; end;
--       begin update public.company_members set whatsapp_trabalho_e164='+551187654321' where id=m;
--             res := res || 'celular_curto=ACEITO'::text; exception when check_violation then res := res || 'celular_curto=recusado'::text; end;
--       begin update public.company_members set whatsapp_trabalho_e164=null, whatsapp_trabalho_confirmado_em=now() where id=m;
--             res := res || 'confirmado_sem_numero=ACEITO'::text; exception when check_violation then res := res || 'confirmado_sem_numero=recusado'::text; end;
--       begin update public.auxiliary_templates set cover_url='http://exemplo.invalido/capa.webp' where id=t;
--             res := res || 'capa_http=ACEITO'::text; exception when check_violation then res := res || 'capa_http=recusado'::text; end;
--       begin update public.auxiliary_templates set faq='{"a":1}'::jsonb where id=t;
--             res := res || 'faq_objeto=ACEITO'::text; exception when check_violation then res := res || 'faq_objeto=recusado'::text; end;
--       begin update public.auxiliary_templates set icon='auxiliares' where id=t;
--             res := res || 'icone_cru=ACEITO'::text; exception when check_violation then res := res || 'icone_cru=recusado'::text; end;
--       raise exception using errcode = 'P0001', message = 'desfaz o VERIFY';
--     exception when sqlstate 'P0001' then null;
--     end;
--     raise notice 'VERIFY 20261014_01 %: %',
--       case when array_to_string(res, ',') ~ '(RECUSADO|ACEITO)' then 'FALHOU' else 'OK' end, array_to_string(res, ', ');
--   end $$;
--   -- esperado: VERIFY 20261014_01 OK: celular=aceito, fixo=aceito, sem_mais=recusado, ddd_zero=recusado,
--   --           celular_curto=recusado, confirmado_sem_numero=recusado, capa_http=recusado, faq_objeto=recusado,
--   --           icone_cru=recusado
--
-- ROLLBACK (escrito ANTES; recusa se alguma corretora já instalou uma das linhas novas ou já gravou um WhatsApp):
--   do $$ begin
--     if exists (select 1 from public.tenant_auxiliaries where slug in ('renovacao','cotacao','quem-cobra-menos')) then
--       raise exception 'ROLLBACK 20261014_01 recusado: há corretora com o aplicativo novo instalado'; end if;
--     if exists (select 1 from public.company_members where whatsapp_trabalho_e164 is not null) then
--       raise exception 'ROLLBACK 20261014_01 recusado: há WhatsApp de trabalho gravado'; end if;
--   end $$;
--   alter table public.company_members drop constraint if exists ck_company_members_whatsapp_confirmado;
--   alter table public.company_members drop constraint if exists ck_company_members_whatsapp_e164;
--   alter table public.company_members drop column if exists whatsapp_trabalho_confirmado_em;
--   alter table public.company_members drop column if exists whatsapp_trabalho_e164;
--   update public.auxiliary_templates set is_active = true where slug = 'renovacao-maxima';
--   delete from public.auxiliary_templates where slug in ('renovacao','cotacao','quem-cobra-menos');
--   alter table public.auxiliary_templates drop constraint if exists ck_aux_templates_icon_lucide;
--   update public.auxiliary_templates set icon = case slug
--       when 'checklist-6h' then 'aprovacao' when 'cobranca-feita' then 'success'
--       when 'follow-up-whatsapp' then 'message-circle' when 'radar-mercado-regulacao' then 'radar'
--       when 'resumo-atendimentos' then 'file-text' when 'tarefas-agendadas' then null else 'auxiliares' end;
--   alter table public.auxiliary_templates drop constraint if exists ck_aux_templates_featured_rank;
--   alter table public.auxiliary_templates drop constraint if exists ck_aux_templates_faq;
--   alter table public.auxiliary_templates drop constraint if exists ck_aux_templates_cover_url;
--   alter table public.auxiliary_templates drop column if exists featured_rank;
--   alter table public.auxiliary_templates drop column if exists faq;
--   alter table public.auxiliary_templates drop column if exists cover_url;
--
-- EXPAND-FIRST: sim (só ADD COLUMN / CHECK / INSERT / UPDATE de rótulo; nenhum DROP)
-- DESTRUTIVA:   não (o UPDATE de `icon` troca rótulos que ninguém lia — o ROLLBACK devolve os valores de antes)
-- =============================================================

-- A. o catálogo: capa, dúvidas, destaque -------------------------------------------------------------------------------
alter table public.auxiliary_templates add column if not exists cover_url text null;
alter table public.auxiliary_templates add column if not exists faq jsonb null;
alter table public.auxiliary_templates add column if not exists featured_rank integer null;

do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'ck_aux_templates_cover_url') then
    alter table public.auxiliary_templates add constraint ck_aux_templates_cover_url
      check (cover_url is null or (cover_url ~ '^https://' and length(cover_url) <= 500)) not valid;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_aux_templates_faq') then
    alter table public.auxiliary_templates add constraint ck_aux_templates_faq
      check (faq is null or jsonb_typeof(faq) = 'array') not valid;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_aux_templates_featured_rank') then
    alter table public.auxiliary_templates add constraint ck_aux_templates_featured_rank
      check (featured_rank is null or featured_rank between 1 and 99) not valid;
  end if;
end $$;
alter table public.auxiliary_templates validate constraint ck_aux_templates_cover_url;
alter table public.auxiliary_templates validate constraint ck_aux_templates_faq;
alter table public.auxiliary_templates validate constraint ck_aux_templates_featured_rank;

-- B. o ícone linear de cada aplicativo (o nome lucide; o mapa nome → componente mora em
--    components/aplicativos/casca/icones.ts; a matiz da capa, em lib/auxiliaries/catalog.ts APLICATIVO_VISUAL)
update public.auxiliary_templates as t set icon = v.icone, updated_at = now()
from (values
  ('checklist-6h', 'Sunrise'), ('cobranca-feita', 'ReceiptText'), ('follow-up-whatsapp', 'MessageSquareReply'),
  ('radar-mercado-regulacao', 'Radar'), ('resumo-atendimentos', 'ScrollText'), ('tarefas-agendadas', 'CalendarClock'),
  ('caca-comissao', 'HandCoins'), ('carteira-blindada', 'ShieldCheck'), ('clientes-perdidos', 'UserSearch'),
  ('contabilidade-pronta', 'BookOpenCheck'), ('digitacao-zero', 'ScanText'), ('organizacao-completa', 'FolderCheck'),
  ('protecao-completa', 'Umbrella'), ('renovacao-maxima', 'RefreshCcwDot'), ('resgatar-cliente', 'UserRoundCheck'),
  ('sinistralidade-avancada', 'ChartNoAxesCombined')
) as v(slug, icone)
where t.slug = v.slug and t.icon is distinct from v.icone;

-- C. as três linhas novas (catálogo GLOBAL; nenhum nome de corretora) -------------------------------------------------
insert into public.auxiliary_templates
  (slug, name, category, short_description, description, icon, status, version, execution_mode, trigger_type,
   requires_human_approval, uses_external_actions, default_config, is_active, headline, categories, catalog_state,
   data_sources, what_it_does, value_promise, missing_for_launch, required_connectors, faq, featured_rank)
values
(
  'renovacao', 'Renovação', 'comercial',
  'Calcula de madrugada cada renovação que vai vencer e deixa a apresentação pronta para o comercial enviar.',
  E'Toda madrugada, o AutoBrokers lê no sistema de gestão as apólices que vencem nos próximos dias, calcula cada renovação no Agger de quem cuida do cliente e confere se nenhuma ficou para trás.\n\nDe manhã, o comercial abre a aba Renovações, confere os cálculos e envia a apresentação pelo próprio WhatsApp. Nada sai sozinho para o cliente.',
  'RefreshCcwDot', 'active', 1, 'scheduled', 'scheduled', false, false,
  '{"visibility": {"type": "global"}}'::jsonb, true,
  'As renovações dos próximos dias amanhecem calculadas no Agger de quem cuida do cliente',
  array['cliente_blindado', 'dinheiro_que_volta']::text[], 'available',
  array['infocap', 'agger']::text[],
  '[{"tarefa": "Lê no sistema de gestão as apólices que vencem nos próximos dias", "frequencia": "toda madrugada"},
    {"tarefa": "Calcula cada renovação no Agger de quem cuida do cliente", "frequencia": "toda madrugada"},
    {"tarefa": "Confere se alguma renovação ficou sem cálculo e mostra o motivo", "frequencia": "todo dia, antes das 7h"},
    {"tarefa": "Prepara a apresentação da renovação para você enviar pelo seu WhatsApp", "frequencia": "quando você pedir"}]'::jsonb,
  'Nenhuma renovação esquecida: cada uma aparece calculada, ou com o motivo de não ter sido. Assim que a primeira madrugada rodar, o número de renovações calculadas no mês aparece aqui.',
  null, array['infocap']::text[],
  '[{"pergunta": "Quando as renovações ficam prontas?", "resposta": "Antes das 7h. O cálculo começa de madrugada e, às 5h30, uma conferência separada relê o sistema de gestão para ter certeza de que nenhuma ficou para trás."},
    {"pergunta": "Em qual Agger o cálculo é feito?", "resposta": "No Agger de quem cuida do cliente, para o cálculo já estar na conta certa quando ele abrir. Quem ainda não conectou o próprio Agger usa o da corretora."},
    {"pergunta": "O cliente recebe alguma coisa sozinho?", "resposta": "Não. Nada sai sem você. Você confere, toca em Enviar pelo WhatsApp e a mensagem abre no seu próprio WhatsApp, pronta para você mandar."},
    {"pergunta": "E o ramo que o AutoBrokers não cota?", "resposta": "Ele aparece na lista como pendente, com o motivo, para você renovar do jeito de sempre. Nenhuma renovação some."},
    {"pergunta": "Quem vê o quê?", "resposta": "Cada comercial abre direto nas renovações dos clientes dele. Quem administra a corretora vê todas."}]'::jsonb,
  1
),
(
  'cotacao', 'Cotação', 'comercial',
  'O cálculo de um seguro novo no Agger, com as regras que a corretora escolher.',
  E'Quando alguém da corretora pede uma cotação, o AutoBrokers calcula no Agger e monta a comparação das opções para o cliente.\n\nAqui você escolhe as regras da cotação. Elas valem só para cotação: a renovação e o Quem Cobra Menos têm as regras deles.',
  'Calculator', 'active', 1, 'manual', 'manual', false, false,
  '{"visibility": {"type": "global"}}'::jsonb, true,
  'O cálculo do seguro novo sai no Agger com as regras da sua corretora',
  array['dinheiro_novo']::text[], 'available',
  array['agger']::text[],
  '[{"tarefa": "Calcula no Agger a cotação que alguém da corretora pediu", "frequencia": "quando você pedir"},
    {"tarefa": "Monta a comparação das opções calculadas para o cliente", "frequencia": "a cada cotação"}]'::jsonb,
  'As regras da cotação ficam num lugar só e valem só para cotação. Quando houver cotações calculadas pelo AutoBrokers, o número aparece aqui.',
  null, array[]::text[], null, null
),
(
  'quem-cobra-menos', 'Quem Cobra Menos', 'comercial',
  'As regras de cálculo para quem chega pelo canal Quem Cobra Menos.',
  E'Quem chega pelo canal Quem Cobra Menos pede o seguro e recebe a cotação calculada no Agger da corretora.\n\nAqui você escolhe as regras desse cálculo. Elas valem só para o Quem Cobra Menos.',
  'BadgePercent', 'active', 1, 'manual', 'manual', false, false,
  '{"visibility": {"type": "global"}}'::jsonb, true,
  'Quem chega pelo canal recebe a cotação calculada, com as regras da sua corretora',
  array['dinheiro_novo']::text[], 'available',
  array['agger']::text[],
  '[{"tarefa": "Calcula no Agger da corretora a cotação de quem chegou pelo canal", "frequencia": "a cada pedido"}]'::jsonb,
  'As regras do Quem Cobra Menos valem só para quem chega pelo canal. Quando houver pedidos calculados, o número aparece aqui.',
  null, array[]::text[], null, null
)
on conflict (slug) do nothing;

-- D. a vitrine antiga sai da loja (a linha fica; 📊 0 instalações) ------------------------------------------------------
update public.auxiliary_templates set is_active = false, updated_at = now()
where slug = 'renovacao-maxima' and is_active;

-- B'. a trava do ícone vem DEPOIS do UPDATE e do INSERT (antes, 'auxiliares' etc. a reprovariam)
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'ck_aux_templates_icon_lucide') then
    alter table public.auxiliary_templates add constraint ck_aux_templates_icon_lucide
      check (icon is null or icon ~ '^[A-Z][A-Za-z0-9]+$') not valid;
  end if;
end $$;
alter table public.auxiliary_templates validate constraint ck_aux_templates_icon_lucide;

comment on column public.auxiliary_templates.cover_url is
  'SPEC-131-B: a capa do aplicativo na loja (https, 1600x900 WebP <= 150 KB, sem texto). Nula = a capa gerada em CSS.';
comment on column public.auxiliary_templates.faq is
  'SPEC-131-B: as dúvidas do aplicativo — lista de {pergunta, resposta}. Global (nenhum nome de corretora).';
comment on column public.auxiliary_templates.featured_rank is
  'SPEC-131-B: 1 = o destaque grande no topo da loja; nulo = sem destaque.';
comment on column public.auxiliary_templates.icon is
  'SPEC-131-B: o nome do ícone lucide (PascalCase) — mapa em components/aplicativos/casca/icones.ts.';

-- E. o "Meu WhatsApp de trabalho" no MEMBRO (por corretora) --------------------------------------------------------------
alter table public.company_members add column if not exists whatsapp_trabalho_e164 text null;
alter table public.company_members add column if not exists whatsapp_trabalho_confirmado_em timestamptz null;

do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'ck_company_members_whatsapp_e164') then
    alter table public.company_members add constraint ck_company_members_whatsapp_e164
      check (whatsapp_trabalho_e164 is null
             or whatsapp_trabalho_e164 ~ '^\+55[1-9][1-9](9[0-9]{8}|[2-5][0-9]{7})$') not valid;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_company_members_whatsapp_confirmado') then
    alter table public.company_members add constraint ck_company_members_whatsapp_confirmado
      check (whatsapp_trabalho_confirmado_em is null or whatsapp_trabalho_e164 is not null) not valid;
  end if;
end $$;
alter table public.company_members validate constraint ck_company_members_whatsapp_e164;
alter table public.company_members validate constraint ck_company_members_whatsapp_confirmado;

comment on column public.company_members.whatsapp_trabalho_e164 is
  'SPEC-131-B (D-131-41): o WhatsApp de TRABALHO desta pessoa NESTA corretora, E.164 com +55. Só o número, para o '
  'cliente responder ao dono ("Quero renovar"). Nunca pareado aqui; nunca o número de atendimento nem o do QCM.';
comment on column public.company_members.whatsapp_trabalho_confirmado_em is
  'SPEC-131-B (D-131-41): quando a própria pessoa confirmou o número. Nulo = não confirmado (o "Quero renovar" não usa).';
