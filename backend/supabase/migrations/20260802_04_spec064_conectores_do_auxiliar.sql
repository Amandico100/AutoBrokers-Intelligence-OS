-- =============================================================
-- MIGRATION: spec064_conectores_do_auxiliar
-- SPEC:      SPEC-064 — Bloco C/D + decisão do Founder de 02/08/2026
-- AUTOR:     lider tecnico            DATA: 2026-08-02
-- OBJETIVO:  o Auxiliar declara de QUAIS conexões precisa, e a conexão é da
--            CORRETORA — uma vez conectada, serve a todos os Auxiliares.
--
-- APPLY:     1. auxiliary_templates.required_connectors text[]
--            2. FK lógica por CHECK contra connector_templates.slug
--            3. seed: cada um dos 15 declara o que precisa
--            4. ativa 'insurance_portal' — é o conector do portal_worker,
--               que é o caminho que FUNCIONA
--
-- VERIFY:    select slug, required_connectors from public.auxiliary_templates
--             where status='active' order by slug;
--            -- esperado: 15 linhas, nenhuma nula
--
--            select a.slug, c
--              from public.auxiliary_templates a,
--                   unnest(a.required_connectors) c
--             where a.status='active'
--               and c not in (select slug from public.connector_templates);
--            -- esperado: 0 linhas (nenhum conector inventado)
--
-- ROLLBACK:  alter table public.auxiliary_templates
--              drop column if exists required_connectors;
--            update public.connector_templates set is_active = false
--             where slug = 'insurance_portal';
--
-- EXPAND-FIRST: sim
-- DESTRUTIVA:   não
-- =============================================================
--
-- A DECISÃO DE ARQUITETURA QUE ESTA MIGRATION IMPLEMENTA
-- ------------------------------------------------------
-- O Founder foi explícito em 02/08/2026:
--
--   "Se o portal da Allianz estiver conectado, ele deve servir para QUALQUER
--    auxiliar que precisar de acesso ao portal da Allianz, e não ter que fazer
--    novamente a conexão em cada auxiliar."
--
-- A boa notícia é que a metade difícil já estava certa: `tenant_connections`
-- e `portal_accounts` são por `company_id`, nunca por auxiliar. **A conexão já
-- é da corretora.**
--
-- O que faltava era o outro lado: nenhum Auxiliar DECLARAVA do que precisa.
-- Sem isso, a tela não tem como dizer "conecte o portal da Allianz para poder
-- ligar", e o corretor liga um Auxiliar que não vai funcionar — que é pior do
-- que não ligar, porque parece que está trabalhando.
--
-- `data_sources` (migration 01) é a frase que o corretor lê. `required_connectors`
-- é a lista que a máquina resolve. As duas coisas são diferentes de propósito:
-- uma é transparência, a outra é pré-requisito.

-- -------------------------------------------------------------
-- 1. A declaração
-- -------------------------------------------------------------

alter table public.auxiliary_templates
  add column if not exists required_connectors text[] not null default '{}'::text[];

comment on column public.auxiliary_templates.required_connectors is
  'SPEC-064 — slugs de connector_templates de que este Auxiliar depende. A conexão é da CORRETORA: conectou uma vez, serve a todos os Auxiliares que a pedirem.';

-- -------------------------------------------------------------
-- 2. O conector que representa o caminho que funciona
-- -------------------------------------------------------------
-- `insurance_portal` estava inativo, e `portal_browser` — que é 100% simulação
-- — também. Resultado: o portal_worker, que loga de verdade na Allianz e baixa
-- boleto, não era representado por conector nenhum.
--
-- Aqui `insurance_portal` é ativado como O conector de portal de seguradora.
-- O reaponte das capacidades (Bloco H) usa esta mesma linha.

update public.connector_templates
   set is_active  = true,
       name       = 'Portal da Seguradora',
       description = 'Acesso ao portal do corretor de cada seguradora, com a credencial da própria corretora. Uma conexão por seguradora, compartilhada por todos os Auxiliares que precisarem dela.',
       updated_at = now()
 where slug = 'insurance_portal';

-- -------------------------------------------------------------
-- 3. Cada Auxiliar declara do que precisa
-- -------------------------------------------------------------
-- Os que não dependem de nada externo ficam com array vazio — e é uma
-- informação útil: "este funciona sem você conectar nada".

update public.auxiliary_templates set required_connectors =
  case slug
    -- Disponíveis
    when 'cobranca-feita'          then array['insurance_portal','whatsapp_zapi']
    when 'checklist-6h'            then array[]::text[]           -- roda com o que já é seu
    when 'primeira-mao'            then array['firecrawl']
    when 'radar-mercado-regulacao' then array['firecrawl']
    when 'resumo-atendimentos'     then array['internal_conversations']
    when 'follow-up-whatsapp'      then array['internal_conversations','whatsapp_zapi']
    -- Em breve
    when 'caca-comissao'           then array['infocap','insurance_portal']
    when 'contabilidade-pronta'    then array['infocap']
    when 'clientes-perdidos'       then array['infocap']
    when 'protecao-completa'       then array['infocap']
    when 'resgatar-cliente'        then array['infocap','internal_conversations']
    when 'renovacao-maxima'        then array['infocap']
    when 'sinistralidade-avancada' then array['infocap']
    when 'carteira-blindada'       then array['infocap']
    when 'organizacao-completa'    then array['infocap','whatsapp_zapi']
    when 'digitacao-zero'          then array['internal_documents','infocap']
    else required_connectors
  end
where status = 'active';

-- -------------------------------------------------------------
-- 4. Nenhum conector inventado
-- -------------------------------------------------------------
-- CHECK não referencia outra tabela em Postgres, então a garantia vira
-- trigger. Sem ela, um `required_connectors = {allianz_portal}` (que não
-- existe) faria a tela pedir para conectar uma coisa inexistente — e o
-- corretor ficaria travado sem entender.

create or replace function public.auxiliary_required_connectors_existem()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  desconhecido text;
begin
  select c into desconhecido
    from unnest(coalesce(new.required_connectors, '{}'::text[])) c
   where c not in (select slug from public.connector_templates)
   limit 1;

  if desconhecido is not null then
    raise exception
      'required_connectors: "%" nao existe em connector_templates. Um Auxiliar nao pode pedir conexao que a plataforma nao sabe oferecer.',
      desconhecido;
  end if;
  return new;
end $$;

drop trigger if exists auxiliary_required_connectors_chk on public.auxiliary_templates;
create trigger auxiliary_required_connectors_chk
  before insert or update of required_connectors on public.auxiliary_templates
  for each row execute function public.auxiliary_required_connectors_existem();
