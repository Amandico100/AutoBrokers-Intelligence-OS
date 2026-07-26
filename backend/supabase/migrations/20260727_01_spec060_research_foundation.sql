-- =============================================================
-- MIGRATION: spec060_research_foundation
-- SPEC:      SPEC-060 — Bloco A (Research Foundation, fontes e claims)
-- AUTOR:     Executor Opus                DATA: 2026-07-27
-- OBJETIVO:  registro canonico de pedido, plano, fonte, snapshot, claim,
--            citacao, finding, monitor, observacao, consumo e cache.
--
-- APPLY:     13 tabelas novas + indices + RLS + triggers de updated_at,
--            append-only e contador de citacoes. Nenhuma tabela existente
--            e alterada.
-- VERIFY:    ver bloco VERIFY ao final (SQL executavel).
-- ROLLBACK:  ver bloco ROLLBACK ao final (drop das 13 tabelas novas).
--
-- EXPAND-FIRST: sim — so cria.
-- DESTRUTIVA:   nao
--
-- AS SEIS GARANTIAS QUE O BANCO COBRA
-- -----------------------------------
-- A SPEC-060 tem seis regras que, se ficarem so no codigo, se perdem no
-- primeiro refactor. Elas viram CHECK aqui:
--
-- 1. Claim de alto risco nao vira `supported` sem citacao de fonte OFICIAL.
-- 2. Fonte Tier 5 (nao verificada) nunca SUSTENTA um claim.
-- 3. Snapshot publico (sem tenant) nao carrega contexto privado.
-- 4. Monitor exige Rotina — nenhum agendador paralelo.
-- 5. Observacao so vira Signal quando a mudanca e relevante.
-- 6. Cache publico nao e tenant-scoped ao mesmo tempo.
--
-- MODELO DE ACESSO: identico ao das SPECs 055/057/058/059 — RLS LIGADA e
-- ZERO policy. Nega tudo para `anon`/`authenticated`; o backend usa service
-- role e aplica o filtro de company_id no repositorio (CLAUDE.md §7).
-- =============================================================

-- -------------------------------------------------------------
-- 1. research_source_policies — §8.4 (PLATAFORMA)
-- -------------------------------------------------------------
create table if not exists public.research_source_policies (
  id                  uuid primary key default gen_random_uuid(),
  policy_key          text not null unique,
  domain_pattern      text not null,
  name                text not null,
  owner               text not null default 'platform',
  trust_tier          smallint not null,
  category            text not null default 'geral',
  country             text null,
  language            text null,
  official            boolean not null default false,
  robots_status       text not null default 'nao_verificado',
  terms_reviewed_at   timestamptz null,
  allowed_content     jsonb not null default '[]'::jsonb,
  allowed_methods     jsonb not null default '["direct_fetch"]'::jsonb,
  max_rate_per_minute smallint not null default 10,
  retention_class     text not null default 'short',
  cache_seconds       integer not null default 86400,
  citation_required   boolean not null default true,
  commercial_use      boolean not null default false,
  pii_policy          text not null default 'nunca',
  login_allowed       boolean not null default false,
  paywall             boolean not null default false,
  reviewed_by         text null,
  status              text not null default 'active',
  notes               text null,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  constraint research_source_policies_tier_ck check (trust_tier between 0 and 5),
  constraint research_source_policies_status_ck
    check (status in ('active', 'paused', 'blocked', 'draft')),
  constraint research_source_policies_retencao_ck
    check (retention_class in ('none', 'short', 'standard', 'long')),
  constraint research_source_policies_pii_ck
    check (pii_policy in ('nunca', 'redigida', 'permitida_com_base')),
  -- §34.3: login e paywall nunca sao contornados. Uma politica que declara
  -- login permitido sem corredor proprio seria a porta para scraping
  -- autenticado fora do Portal Worker — que a §43 mantem fora desta SPEC.
  constraint research_source_policies_sem_login_ck check (login_allowed = false)
);

create index if not exists ix_research_source_policies_dominio
  on public.research_source_policies (domain_pattern) where status = 'active';

-- -------------------------------------------------------------
-- 2. research_sources — §10.3 (identidade GLOBAL da fonte)
-- -------------------------------------------------------------
--
-- Sem `company_id` de proposito: a identidade de "planalto.gov.br/lei-x" e a
-- mesma para todas as corretoras. O que e privado e a PESQUISA que a
-- consultou, nao a existencia da fonte.
create table if not exists public.research_sources (
  id                uuid primary key default gen_random_uuid(),
  canonical_url     text not null,
  url_fingerprint   text not null unique,
  normalized_domain text not null,
  source_type       text not null default 'web_page',
  publisher         text null,
  title             text null,
  country           text null,
  language          text null,
  trust_tier        smallint not null default 3,
  official          boolean not null default false,
  source_policy_id  uuid null references public.research_source_policies(id) on delete set null,
  first_seen_at     timestamptz not null default now(),
  last_seen_at      timestamptz not null default now(),
  status            text not null default 'active',
  metadata          jsonb not null default '{}'::jsonb,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  constraint research_sources_tier_ck check (trust_tier between 0 and 5),
  constraint research_sources_status_ck
    check (status in ('active', 'unreachable', 'blocked', 'retired')),
  -- Fonte marcada como oficial precisa de tier compativel. Sem isto, um
  -- blog poderia ser marcado `official` e passar a sustentar claim
  -- regulatorio — que e exatamente o que §8.3 impede.
  constraint research_sources_oficial_e_tier_ck
    check (official = false or trust_tier <= 1)
);

create index if not exists ix_research_sources_dominio
  on public.research_sources (normalized_domain, trust_tier);
create index if not exists ix_research_sources_oficiais
  on public.research_sources (official, trust_tier) where official;

-- -------------------------------------------------------------
-- 3. research_requests — §10.1
-- -------------------------------------------------------------
create table if not exists public.research_requests (
  id                   uuid primary key default gen_random_uuid(),
  company_id           uuid not null references public.companies(id) on delete cascade,
  user_id              uuid null,
  conversation_id      uuid null,
  work_run_id          uuid null,
  request_type         text not null default 'user',
  requested_by_kind    text not null default 'user',
  mode                 text not null,
  objective            text not null,
  question             text not null,
  scope                jsonb not null default '{}'::jsonb,
  constraints          jsonb not null default '{}'::jsonb,
  requested_outputs    jsonb not null default '[]'::jsonb,
  freshness_requirement text null,
  source_requirements  jsonb not null default '{}'::jsonb,
  time_budget_seconds  integer null,
  budget_brl           numeric(12,2) null,
  status               text not null default 'draft',
  result_summary       text null,
  limitations          text null,
  idempotency_key      text null,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  constraint research_requests_mode_ck
    check (mode in ('quick', 'verified', 'deep', 'site_audit',
                    'business_discovery', 'monitor', 'claim_check')),
  constraint research_requests_status_ck
    check (status in ('draft', 'planning', 'running', 'verifying',
                      'completed', 'partial', 'failed', 'cancelled', 'blocked')),
  constraint research_requests_origem_ck
    check (requested_by_kind in ('user', 'agent', 'routine', 'monitor',
                                 'platform', 'system'))
);

create unique index if not exists ux_research_requests_idempotente
  on public.research_requests (company_id, idempotency_key)
  where idempotency_key is not null;
create index if not exists ix_research_requests_company
  on public.research_requests (company_id, status, created_at desc);

-- -------------------------------------------------------------
-- 4. research_plans — §10.2
-- -------------------------------------------------------------
create table if not exists public.research_plans (
  id                     uuid primary key default gen_random_uuid(),
  company_id             uuid not null references public.companies(id) on delete cascade,
  research_request_id    uuid not null references public.research_requests(id) on delete cascade,
  work_run_id            uuid null,
  version                integer not null default 1,
  status                 text not null default 'draft',
  subquestions           jsonb not null default '[]'::jsonb,
  search_strategy        jsonb not null default '{}'::jsonb,
  source_strategy        jsonb not null default '{}'::jsonb,
  provider_strategy      jsonb not null default '{}'::jsonb,
  stop_rules             jsonb not null default '{}'::jsonb,
  verification_rules     jsonb not null default '{}'::jsonb,
  output_contract        jsonb not null default '{}'::jsonb,
  estimated_cost_brl_min numeric(12,2) null,
  estimated_cost_brl_max numeric(12,2) null,
  replan_reason          text null,
  approved_at            timestamptz null,
  created_at             timestamptz not null default now(),
  constraint research_plans_status_ck
    check (status in ('draft', 'published', 'superseded', 'abandoned'))
);

create unique index if not exists ux_research_plans_versao
  on public.research_plans (research_request_id, version);
create index if not exists ix_research_plans_request
  on public.research_plans (research_request_id, status);

-- -------------------------------------------------------------
-- 5. research_source_snapshots — §10.4
-- -------------------------------------------------------------
create table if not exists public.research_source_snapshots (
  id                      uuid primary key default gen_random_uuid(),
  company_id              uuid null references public.companies(id) on delete cascade,
  research_source_id      uuid not null references public.research_sources(id) on delete cascade,
  work_run_id             uuid null,
  research_request_id     uuid null references public.research_requests(id) on delete set null,
  provider_key            text not null,
  retrieved_at            timestamptz not null default now(),
  published_at            timestamptz null,
  modified_at             timestamptz null,
  http_status             integer null,
  content_type            text null,
  content_hash            text not null,
  structure_hash          text null,
  storage_ref             text null,
  clean_text_ref          text null,
  excerpt_redacted        text null,
  word_count              integer null,
  retention_class         text not null default 'short',
  valid_until             timestamptz null,
  robots_result           text null,
  terms_policy_result     text null,
  prompt_injection_status text not null default 'nao_avaliado',
  injection_score         numeric(4,3) not null default 0,
  contains_private_context boolean not null default false,
  metadata                jsonb not null default '{}'::jsonb,
  created_at              timestamptz not null default now(),
  constraint research_snapshots_injection_ck
    check (prompt_injection_status in ('nao_avaliado', 'limpo', 'suspeito',
                                       'quarentena', 'bloqueado')),
  constraint research_snapshots_retencao_ck
    check (retention_class in ('none', 'short', 'standard', 'long')),
  -- §10.4 e §24.2: snapshot sem tenant e COMPARTILHAVEL entre corretoras.
  -- Se ele pudesse carregar contexto privado, o cache publico viraria o
  -- caminho por onde a pergunta de uma corretora chega a outra.
  constraint research_snapshots_publico_e_anonimo_ck
    check (company_id is not null or contains_private_context = false)
);

create index if not exists ix_research_snapshots_fonte
  on public.research_source_snapshots (research_source_id, retrieved_at desc);
create index if not exists ix_research_snapshots_company
  on public.research_source_snapshots (company_id, retrieved_at desc)
  where company_id is not null;
create index if not exists ix_research_snapshots_hash
  on public.research_source_snapshots (content_hash);

-- -------------------------------------------------------------
-- 6. research_claims — §10.5
-- -------------------------------------------------------------
create table if not exists public.research_claims (
  id                      uuid primary key default gen_random_uuid(),
  company_id              uuid not null references public.companies(id) on delete cascade,
  research_request_id     uuid not null references public.research_requests(id) on delete cascade,
  work_run_id             uuid null,
  claim_key               text not null,
  claim_text              text not null,
  claim_type              text not null default 'factual',
  status                  text not null default 'draft',
  confidence              numeric(4,3) not null default 0.500,
  risk_level              text not null default 'low',
  freshness                text not null default 'stable',
  valid_from              timestamptz null,
  valid_until             timestamptz null,
  contradiction_status    text not null default 'nenhuma',
  verification_status     text not null default 'nao_verificado',
  citation_count          integer not null default 0,
  official_citation_count integer not null default 0,
  contradicting_count     integer not null default 0,
  notes                   text null,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now(),
  constraint research_claims_status_ck
    check (status in ('draft', 'supported', 'partially_supported',
                      'unsupported', 'contradicted', 'stale', 'withdrawn')),
  constraint research_claims_type_ck
    check (claim_type in ('factual', 'temporal', 'numeric', 'comparative',
                          'regulatory', 'causal', 'strategic', 'attributed_opinion')),
  constraint research_claims_risk_ck
    check (risk_level in ('low', 'medium', 'high', 'critical')),
  constraint research_claims_confidence_ck
    check (confidence >= 0 and confidence <= 1),
  constraint research_claims_contradicao_ck
    check (contradiction_status in ('nenhuma', 'possivel', 'confirmada', 'resolvida')),
  constraint research_claims_verificacao_ck
    check (verification_status in ('nao_verificado', 'verificado', 'reprovado',
                                   'inconclusivo')),
  -- GARANTIA 1 — §8.3 e §16.3. Claim de cobertura, obrigacao legal ou
  -- regulacao NAO pode ser apresentado como sustentado sem citacao de fonte
  -- OFICIAL. Sem este CHECK, a regra viveria so no verifier, e um caminho
  -- novo que esquecesse de chama-lo produziria afirmacao regulatoria com
  -- aparencia de verificada.
  constraint research_claims_alto_risco_exige_fonte_oficial_ck
    check (status <> 'supported'
           or risk_level not in ('high', 'critical')
           or official_citation_count > 0),
  -- Nenhum claim e 'supported' sem NENHUMA citacao. Sustentado por nada e
  -- exatamente o que a §16.1 existe para impedir.
  constraint research_claims_suportado_exige_citacao_ck
    check (status not in ('supported', 'partially_supported')
           or citation_count > 0)
);

create unique index if not exists ux_research_claims_chave
  on public.research_claims (research_request_id, claim_key);
create index if not exists ix_research_claims_company
  on public.research_claims (company_id, status, created_at desc);

-- -------------------------------------------------------------
-- 7. research_claim_citations — §10.6
-- -------------------------------------------------------------
create table if not exists public.research_claim_citations (
  id                 uuid primary key default gen_random_uuid(),
  company_id         uuid not null references public.companies(id) on delete cascade,
  claim_id           uuid not null references public.research_claims(id) on delete cascade,
  source_snapshot_id uuid not null references public.research_source_snapshots(id) on delete cascade,
  citation_role      text not null default 'supports',
  support_strength   numeric(4,3) not null default 0.500,
  source_excerpt     text null,
  locator            jsonb not null default '{}'::jsonb,
  source_trust_tier  smallint not null,
  source_official    boolean not null default false,
  created_at         timestamptz not null default now(),
  constraint research_citations_role_ck
    check (citation_role in ('supports', 'contradicts', 'context', 'methodology')),
  constraint research_citations_forca_ck
    check (support_strength >= 0 and support_strength <= 1),
  constraint research_citations_tier_ck check (source_trust_tier between 0 and 5),
  -- GARANTIA 2 — §8.3: Tier 5 e conteudo nao verificado (agregador sem
  -- origem, texto de IA sem fonte, pagina anonima). Ele pode entrar como
  -- CONTEXTO, nunca como sustentacao.
  constraint research_citations_tier5_nao_sustenta_ck
    check (citation_role <> 'supports' or source_trust_tier <= 4),
  -- Coerencia: `official` e propriedade de Tier 0/1.
  constraint research_citations_oficial_e_tier_ck
    check (source_official = false or source_trust_tier <= 1)
);

create unique index if not exists ux_research_citations_unica
  on public.research_claim_citations (claim_id, source_snapshot_id, citation_role);
create index if not exists ix_research_citations_claim
  on public.research_claim_citations (claim_id);

-- -------------------------------------------------------------
-- 8. research_findings — §10.7
-- -------------------------------------------------------------
create table if not exists public.research_findings (
  id                  uuid primary key default gen_random_uuid(),
  company_id          uuid not null references public.companies(id) on delete cascade,
  research_request_id uuid not null references public.research_requests(id) on delete cascade,
  work_run_id         uuid null,
  finding_type        text not null default 'sintese',
  title               text not null,
  summary             text not null,
  fact_statement      text null,
  inference_statement text null,
  limitations         text null,
  confidence          numeric(4,3) not null default 0.500,
  status              text not null default 'active',
  signal_id           uuid null,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  constraint research_findings_status_ck
    check (status in ('draft', 'active', 'superseded', 'withdrawn')),
  constraint research_findings_confidence_ck
    check (confidence >= 0 and confidence <= 1),
  -- Mesma lei da SPEC-059: inferencia nunca sem fato.
  constraint research_findings_fato_antes_da_inferencia_ck
    check (inference_statement is null or fact_statement is not null)
);

create index if not exists ix_research_findings_request
  on public.research_findings (research_request_id, status);

create table if not exists public.research_finding_claims (
  finding_id uuid not null references public.research_findings(id) on delete cascade,
  claim_id   uuid not null references public.research_claims(id) on delete cascade,
  company_id uuid not null references public.companies(id) on delete cascade,
  role       text not null default 'supporting',
  weight     numeric(4,3) not null default 1.000,
  created_at timestamptz not null default now(),
  primary key (finding_id, claim_id),
  constraint research_finding_claims_role_ck
    check (role in ('primary', 'supporting', 'contradicting', 'context'))
);

-- -------------------------------------------------------------
-- 9. research_monitors — §10.9
-- -------------------------------------------------------------
create table if not exists public.research_monitors (
  id                   uuid primary key default gen_random_uuid(),
  company_id           uuid not null references public.companies(id) on delete cascade,
  user_id              uuid null,
  name                 text not null,
  monitor_type         text not null default 'url',
  topic                text null,
  source_policy_filter jsonb not null default '{}'::jsonb,
  url_filters          jsonb not null default '[]'::jsonb,
  query_spec           jsonb not null default '{}'::jsonb,
  cadence              text not null default 'daily',
  schedule_spec        jsonb not null default '{"time":"07:00"}'::jsonb,
  timezone             text not null default 'America/Sao_Paulo',
  change_policy        jsonb not null default '{}'::jsonb,
  severity_policy      jsonb not null default '{}'::jsonb,
  channels             jsonb not null default '["dashboard"]'::jsonb,
  budget_brl           numeric(12,2) null,
  is_active            boolean not null default true,
  health               text not null default 'unknown',
  health_reason        text null,
  last_run_at          timestamptz null,
  last_change_at       timestamptz null,
  consecutive_failures smallint not null default 0,
  routine_id           uuid null,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  constraint research_monitors_type_ck
    check (monitor_type in ('url', 'domain', 'query', 'entity', 'norma',
                            'insurer', 'competitor', 'product', 'topic')),
  constraint research_monitors_cadence_ck
    check (cadence in ('hourly', 'daily', 'weekly', 'monthly')),
  constraint research_monitors_health_ck
    check (health in ('unknown', 'ok', 'degraded', 'error')),
  -- GARANTIA 4 — §7.6 e §22: monitor ATIVO exige Rotina. Sem isto, alguem
  -- criaria um laco proprio "so para monitores" e a SPEC-060 teria fabricado
  -- o agendador paralelo que a §0.2 proibe explicitamente.
  constraint research_monitors_ativo_exige_rotina_ck
    check (is_active = false or routine_id is not null)
);

create index if not exists ix_research_monitors_company
  on public.research_monitors (company_id, is_active);
create index if not exists ix_research_monitors_rotina
  on public.research_monitors (routine_id) where routine_id is not null;

-- -------------------------------------------------------------
-- 10. research_observations — §10.10
-- -------------------------------------------------------------
create table if not exists public.research_observations (
  id                    uuid primary key default gen_random_uuid(),
  company_id            uuid not null references public.companies(id) on delete cascade,
  research_monitor_id   uuid not null references public.research_monitors(id) on delete cascade,
  work_run_id           uuid null,
  source_snapshot_id    uuid null references public.research_source_snapshots(id) on delete set null,
  observation_type      text not null default 'check',
  change_class          text not null default 'none',
  significance_score    numeric(5,2) not null default 0,
  summary               text not null default '',
  evidence              jsonb not null default '{}'::jsonb,
  content_hash          text not null default '',
  previous_content_hash text null,
  signal_id             uuid null,
  status                text not null default 'recorded',
  observed_at           timestamptz not null default now(),
  created_at            timestamptz not null default now(),
  constraint research_observations_change_ck
    check (change_class in ('none', 'cosmetic', 'minor', 'relevant',
                            'major', 'unreachable')),
  constraint research_observations_status_ck
    check (status in ('recorded', 'promoted', 'suppressed', 'failed')),
  constraint research_observations_score_ck
    check (significance_score between 0 and 100),
  -- GARANTIA 5 — §22.3 e §28.2: mudanca cosmetica NAO vira Signal. Menu que
  -- mudou de ordem, banner de cookie e timestamp automatico sao a maior fonte
  -- de ruido de qualquer monitor. Se virassem alerta, o corretor desligaria o
  -- monitor na primeira semana — e perderia a mudanca que importa.
  constraint research_observations_signal_exige_relevancia_ck
    check (signal_id is null
           or (change_class in ('relevant', 'major') and significance_score >= 50))
);

create index if not exists ix_research_observations_monitor
  on public.research_observations (research_monitor_id, observed_at desc);
create index if not exists ix_research_observations_company
  on public.research_observations (company_id, change_class, observed_at desc);

-- -------------------------------------------------------------
-- 11. research_provider_usage — §10.11
-- -------------------------------------------------------------
create table if not exists public.research_provider_usage (
  id                  uuid primary key default gen_random_uuid(),
  company_id          uuid null references public.companies(id) on delete cascade,
  work_run_id         uuid null,
  research_request_id uuid null references public.research_requests(id) on delete set null,
  provider_key        text not null,
  operation           text not null,
  request_count       integer not null default 1,
  units               numeric(12,3) null,
  unit_kind           text null,
  provider_cost       numeric(12,6) null,
  cost_currency       text null,
  cost_brl            numeric(12,4) null,
  cost_is_estimated   boolean not null default true,
  latency_ms          integer null,
  cache_hit           boolean not null default false,
  status              text not null default 'ok',
  error_code          text null,
  created_at          timestamptz not null default now(),
  constraint research_usage_status_ck
    check (status in ('ok', 'error', 'blocked', 'skipped', 'no_credit'))
);

create index if not exists ix_research_usage_company
  on public.research_provider_usage (company_id, created_at desc);
create index if not exists ix_research_usage_provider
  on public.research_provider_usage (provider_key, created_at desc);

-- -------------------------------------------------------------
-- 12. research_cache_entries — §10.12
-- -------------------------------------------------------------
create table if not exists public.research_cache_entries (
  id                 uuid primary key default gen_random_uuid(),
  scope              text not null default 'public',
  company_id         uuid null references public.companies(id) on delete cascade,
  cache_key          text not null,
  source_snapshot_id uuid null references public.research_source_snapshots(id) on delete cascade,
  result_ref         text null,
  result_payload     jsonb null,
  content_hash       text not null,
  fresh_until        timestamptz not null,
  stale_until        timestamptz null,
  policy_class       text not null default 'standard',
  created_at         timestamptz not null default now(),
  last_hit_at        timestamptz null,
  hit_count          integer not null default 0,
  constraint research_cache_scope_ck check (scope in ('public', 'tenant')),
  -- GARANTIA 6 — §24.2: cache publico e compartilhado entre corretoras.
  -- Um registro que fosse publico E carregasse tenant seria a porta por onde
  -- a pesquisa de uma corretora chega a outra.
  constraint research_cache_publico_sem_tenant_ck
    check ((scope = 'public' and company_id is null)
           or (scope = 'tenant' and company_id is not null))
);

create unique index if not exists ux_research_cache_chave
  on public.research_cache_entries (
    scope, coalesce(company_id, '00000000-0000-0000-0000-000000000000'::uuid), cache_key);
create index if not exists ix_research_cache_validade
  on public.research_cache_entries (fresh_until);

-- -------------------------------------------------------------
-- Triggers de updated_at
-- -------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array[
    'research_source_policies', 'research_sources', 'research_requests',
    'research_claims', 'research_findings', 'research_monitors'
  ] loop
    execute format('drop trigger if exists tg_%1$s_updated_at on public.%1$s', t);
    execute format(
      'create trigger tg_%1$s_updated_at before update on public.%1$s '
      'for each row execute function public.update_updated_at_column()', t);
  end loop;
end $$;

-- -------------------------------------------------------------
-- Contador de citacoes — o que torna a GARANTIA 1 executavel
-- -------------------------------------------------------------
--
-- Os contadores NAO sao mantidos pelo servico de proposito. Se fossem, o
-- CHECK de "alto risco exige fonte oficial" dependeria de o servico ter
-- atualizado o numero antes — e um caminho que esquecesse disso passaria pelo
-- CHECK com o contador velho. Mantidos por trigger, eles sao sempre verdade.
create or replace function public.research_claims_recontar_citacoes()
returns trigger
language plpgsql
set search_path to 'pg_catalog', 'public'
as $$
declare
  v_claim uuid;
begin
  v_claim := coalesce(new.claim_id, old.claim_id);
  update public.research_claims c
     set citation_count = (
           select count(*) from public.research_claim_citations x
            where x.claim_id = v_claim and x.citation_role = 'supports'),
         official_citation_count = (
           select count(*) from public.research_claim_citations x
            where x.claim_id = v_claim and x.citation_role = 'supports'
              and x.source_official),
         contradicting_count = (
           select count(*) from public.research_claim_citations x
            where x.claim_id = v_claim and x.citation_role = 'contradicts')
   where c.id = v_claim;
  return coalesce(new, old);
end $$;

drop trigger if exists tg_research_citations_recontar on public.research_claim_citations;
create trigger tg_research_citations_recontar
  after insert or update or delete on public.research_claim_citations
  for each row execute function public.research_claims_recontar_citacoes();

-- -------------------------------------------------------------
-- Append-only de observacoes
-- -------------------------------------------------------------
-- Observacao e registro historico do que a fonte era num instante. Reescrever
-- destruiria a base do diff — e o diff e a unica prova de que a mudanca
-- aconteceu. `status` e `signal_id` sao a excecao: eles marcam o
-- encaminhamento, nao o que foi observado.
create or replace function public.research_observations_append_only()
returns trigger
language plpgsql
set search_path to 'pg_catalog', 'public'
as $$
begin
  if tg_op = 'UPDATE' then
    if (to_jsonb(new) - array['status', 'signal_id'])
       is distinct from (to_jsonb(old) - array['status', 'signal_id']) then
      raise exception 'research_observations e append-only: so status e signal_id mudam';
    end if;
    return new;
  end if;
  if tg_op = 'DELETE'
     and coalesce(current_setting('app.research_observations_purge', true), 'off') <> 'on' then
    raise exception 'DELETE exige app.research_observations_purge=on';
  end if;
  return case when tg_op = 'DELETE' then old else new end;
end $$;

drop trigger if exists tg_research_observations_append_only on public.research_observations;
create trigger tg_research_observations_append_only
  before update or delete on public.research_observations
  for each row execute function public.research_observations_append_only();

-- -------------------------------------------------------------
-- RLS — LIGADA, sem policy
-- -------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array[
    'research_source_policies', 'research_sources', 'research_requests',
    'research_plans', 'research_source_snapshots', 'research_claims',
    'research_claim_citations', 'research_findings', 'research_finding_claims',
    'research_monitors', 'research_observations', 'research_provider_usage',
    'research_cache_entries'
  ] loop
    execute format('alter table public.%I enable row level security', t);
  end loop;
end $$;

-- =============================================================
-- VERIFY  (read-only)
-- =============================================================
-- 1) 13 tabelas com RLS ligada e zero policy:
-- select c.relname, c.relrowsecurity,
--        (select count(*) from pg_policies p
--          where p.schemaname='public' and p.tablename=c.relname) policies
--   from pg_class c join pg_namespace n on n.oid=c.relnamespace
--  where n.nspname='public' and c.relkind='r' and c.relname like 'research\_%'
--  order by 1;
--
-- 2) as seis garantias estao declaradas:
-- select conname from pg_constraint where conname in (
--   'research_claims_alto_risco_exige_fonte_oficial_ck',
--   'research_citations_tier5_nao_sustenta_ck',
--   'research_snapshots_publico_e_anonimo_ck',
--   'research_monitors_ativo_exige_rotina_ck',
--   'research_observations_signal_exige_relevancia_ck',
--   'research_cache_publico_sem_tenant_ck') order by 1;
--   -- esperado: 6 linhas
--
-- 3) provas negativas (cada INSERT deve FALHAR):
--    - claim 'supported' com risk_level='critical' e sem citacao oficial
--    - citacao 'supports' com source_trust_tier=5
--    - snapshot com company_id NULL e contains_private_context=true
--    - monitor is_active=true sem routine_id
--    - observacao com signal_id e change_class='cosmetic'
--    - cache scope='public' com company_id preenchido
--
-- =============================================================
-- ROLLBACK
-- =============================================================
-- drop trigger if exists tg_research_observations_append_only on public.research_observations;
-- drop trigger if exists tg_research_citations_recontar on public.research_claim_citations;
-- drop function if exists public.research_observations_append_only();
-- drop function if exists public.research_claims_recontar_citacoes();
-- drop table if exists public.research_cache_entries cascade;
-- drop table if exists public.research_provider_usage cascade;
-- drop table if exists public.research_observations cascade;
-- drop table if exists public.research_monitors cascade;
-- drop table if exists public.research_finding_claims cascade;
-- drop table if exists public.research_findings cascade;
-- drop table if exists public.research_claim_citations cascade;
-- drop table if exists public.research_claims cascade;
-- drop table if exists public.research_source_snapshots cascade;
-- drop table if exists public.research_plans cascade;
-- drop table if exists public.research_requests cascade;
-- drop table if exists public.research_sources cascade;
-- drop table if exists public.research_source_policies cascade;
-- =============================================================
