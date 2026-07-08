-- SPEC-023 P5 - mensagem de cobranca + catalogo Firecrawl.
-- EXPAND-ONLY:
-- - atualiza o template global da rotina de cobranca.
-- - atualiza rotinas de cobranca existentes apenas quando ainda usam o texto
--   default antigo.
-- - registra Firecrawl no catalogo global de conectores sem gravar segredo.

do $$
declare
  new_message text := 'Ola {nome_segurado},
Aqui e a {nome_atendente}, da {nome_corretora}, tudo bem?

A Seguradora {nome_seguradora} informou que a parcela *{numero_parcela}* do seguro do *{item_segurado}* ainda esta pendente.
Desta forma, a seguradora gerou um novo boleto para pagamento pra voce nao ficar sem cobertura, ok!?

Qualquer duvida estou a disposicao.

Segue o boleto abaixo.
Apolice: *{numero_apolice}*';
  old_message text := 'Ola, {cliente_nome}. Identificamos uma parcela pendente do seu seguro com vencimento em {vencimento}, no valor de R$ {valor}. Segue o boleto para regularizacao.';
begin
  update public.routine_templates
  set
    config_default = jsonb_set(
      jsonb_set(
        jsonb_set(coalesce(config_default, '{}'::jsonb), '{message_template}', to_jsonb(new_message), true),
        '{attendant_name}', to_jsonb('Even'::text), true
      ),
      '{insurer_name}', to_jsonb('ALLIANZ'::text), true
    ),
    updated_at = now()
  where name = 'Cobranca de boletos atrasados'
    and coalesce(config_default->>'kind', '') = 'billing_collection';

  update public.routines
  set
    config = jsonb_set(
      jsonb_set(
        jsonb_set(coalesce(config, '{}'::jsonb), '{message_template}', to_jsonb(new_message), true),
        '{attendant_name}', to_jsonb(coalesce(nullif(config->>'attendant_name', ''), 'Even')), true
      ),
      '{insurer_name}', to_jsonb(coalesce(nullif(config->>'insurer_name', ''), 'ALLIANZ')), true
    ),
    updated_at = now()
  where coalesce(config->>'kind', '') = 'billing_collection'
    and (
      config->>'message_template' is null
      or config->>'message_template' = old_message
      or config->>'message_template' ilike 'Ola, {cliente_nome}. Identificamos uma parcela pendente%'
    );
end $$;

insert into public.connector_templates
  (slug, name, description, category, provider, connector_kind, auth_type, risk_level,
   requires_approval_default, capabilities, required_fields, metadata, is_active)
values
  (
    'firecrawl',
    'Firecrawl',
    'Pesquisa, scrape, crawl e interacao web para agentes e auxiliares.',
    'knowledge',
    'firecrawl',
    'http_tool',
    'api_key',
    'medium',
    false,
    '["web_search","web_scrape","web_crawl","web_interact"]'::jsonb,
    '[{"key":"api_key","label":"API key","secret":true}]'::jsonb,
    '{
      "base_url":"https://api.firecrawl.dev/v2",
      "docs_url":"https://docs.firecrawl.dev",
      "notes":"Sem segredo no seed. API key deve ser configurada por fluxo seguro/env/vault.",
      "portal_usage":"Nao substitui o portal_worker para portais autenticados; pode auxiliar pesquisa web e paginas publicas."
    }'::jsonb,
    true
  )
on conflict (slug) do update
set
  name = excluded.name,
  description = excluded.description,
  category = excluded.category,
  provider = excluded.provider,
  connector_kind = excluded.connector_kind,
  auth_type = excluded.auth_type,
  risk_level = excluded.risk_level,
  requires_approval_default = excluded.requires_approval_default,
  capabilities = excluded.capabilities,
  required_fields = excluded.required_fields,
  metadata = excluded.metadata,
  is_active = true,
  updated_at = now();
