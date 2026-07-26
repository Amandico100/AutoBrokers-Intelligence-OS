-- =============================================================
-- MIGRATION: spec059_intelligence_fabric
-- SPEC:      SPEC-059 — Bloco A (Signal Intelligence Foundation)
-- AUTOR:     Executor Opus                DATA: 2026-07-26
-- OBJETIVO:  criar o registro canonico de sinal, evidencia, finding,
--            recomendacao, briefing, regra, demanda e evento de inteligencia.
--
-- APPLY:     14 tabelas novas + indices + RLS + triggers de updated_at e
--            append-only. Nenhuma tabela existente e alterada.
-- VERIFY:    ver bloco VERIFY ao final (SQL executavel, read-only).
-- ROLLBACK:  ver bloco ROLLBACK ao final (drop das 14 tabelas novas).
--
-- EXPAND-FIRST: sim — so cria. Nao remove, nao renomeia, nao altera.
-- DESTRUTIVA:   nao
--
-- MODELO DE ACESSO: identico ao das SPECs 055/057/058 — RLS LIGADA e
-- ZERO policy. Isso nega tudo para `anon` e `authenticated`; o backend usa
-- service role e aplica o filtro de company_id no repositorio (CLAUDE.md §7).
-- Nenhuma dessas tabelas e lida direto pelo browser.
-- =============================================================

-- -------------------------------------------------------------
-- 1. intelligence_signals — SPEC-059 §10.1
-- -------------------------------------------------------------
create table if not exists public.intelligence_signals (
  id                  uuid primary key default gen_random_uuid(),
  company_id          uuid not null references public.companies(id) on delete cascade,
  user_id             uuid null,
  signal_type         text not null,
  domain              text not null,
  subject_type        text not null,
  subject_id          text null,
  source_type         text not null,
  source_ref          text null,
  rule_key            text null,
  rule_version        text null,
  summary_redacted    text not null,
  status              text not null default 'candidate',
  severity            text not null default 'info',
  confidence          numeric(4,3) not null default 0.500,
  impact_score        numeric(5,2) null,
  urgency_score       numeric(5,2) null,
  actionability_score numeric(5,2) null,
  recurrence_score    numeric(5,2) null,
  freshness_score     numeric(5,2) null,
  priority_score      numeric(5,2) null,
  trust_tier          smallint not null default 3,
  window_start        timestamptz null,
  window_end          timestamptz null,
  dedupe_key          text not null,
  fingerprint         text not null,
  valid_until         timestamptz null,
  correlation_id      text null,
  causation_id        text null,
  work_run_id         uuid null,
  conversation_id     uuid null,
  occurrence_count    integer not null default 1,
  last_seen_at        timestamptz not null default now(),
  metadata            jsonb not null default '{}'::jsonb,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  constraint intelligence_signals_confidence_ck
    check (confidence >= 0 and confidence <= 1),
  constraint intelligence_signals_trust_tier_ck
    check (trust_tier between 0 and 5),
  constraint intelligence_signals_status_ck
    check (status in ('candidate','validated','clustered','promoted',
                      'suppressed','expired','invalidated')),
  constraint intelligence_signals_severity_ck
    check (severity in ('info','low','medium','high','critical')),
  constraint intelligence_signals_scores_ck
    check (coalesce(impact_score,0)        between 0 and 100
       and coalesce(urgency_score,0)       between 0 and 100
       and coalesce(actionability_score,0) between 0 and 100
       and coalesce(recurrence_score,0)    between 0 and 100
       and coalesce(freshness_score,0)     between 0 and 100
       and coalesce(priority_score,0)      between 0 and 100),
  constraint intelligence_signals_janela_ck
    check (window_end is null or window_start is null or window_end >= window_start)
);

-- Dedupe: a MESMA observacao nao vira dois sinais enquanto o primeiro estiver
-- vivo. Estados terminais ficam de fora do indice de proposito: um sinal
-- expirado nao pode impedir que o mesmo problema seja detectado de novo.
create unique index if not exists ux_intelligence_signals_dedupe_vivo
  on public.intelligence_signals (company_id, dedupe_key)
  where status in ('candidate','validated','clustered','promoted');

create index if not exists ix_intelligence_signals_company_status
  on public.intelligence_signals (company_id, status, priority_score desc nulls last);
create index if not exists ix_intelligence_signals_company_tipo
  on public.intelligence_signals (company_id, signal_type, created_at desc);
create index if not exists ix_intelligence_signals_validade
  on public.intelligence_signals (valid_until)
  where status in ('candidate','validated','clustered','promoted');
create index if not exists ix_intelligence_signals_work_run
  on public.intelligence_signals (work_run_id) where work_run_id is not null;

-- -------------------------------------------------------------
-- 2. intelligence_signal_evidence — SPEC-059 §10.2
-- -------------------------------------------------------------
create table if not exists public.intelligence_signal_evidence (
  id               uuid primary key default gen_random_uuid(),
  company_id       uuid not null references public.companies(id) on delete cascade,
  signal_id        uuid not null references public.intelligence_signals(id) on delete cascade,
  evidence_type    text not null,
  source_system    text not null,
  source_ref       text not null,
  trust_tier       smallint not null,
  summary_redacted text not null,
  value_snapshot   jsonb not null default '{}'::jsonb,
  content_hash     text null,
  observed_at      timestamptz not null default now(),
  valid_until      timestamptz null,
  sensitivity      text not null default 'internal',
  created_at       timestamptz not null default now(),
  constraint intelligence_evidence_tier_ck check (trust_tier between 0 and 5),
  constraint intelligence_evidence_sensitivity_ck
    check (sensitivity in ('public','internal','restricted','sensitive'))
);

create index if not exists ix_intelligence_evidence_signal
  on public.intelligence_signal_evidence (signal_id, observed_at desc);
create index if not exists ix_intelligence_evidence_company
  on public.intelligence_signal_evidence (company_id, created_at desc);

-- -------------------------------------------------------------
-- 3. intelligence_findings — SPEC-059 §10.3
-- -------------------------------------------------------------
create table if not exists public.intelligence_findings (
  id                  uuid primary key default gen_random_uuid(),
  company_id          uuid not null references public.companies(id) on delete cascade,
  user_id             uuid null,
  finding_type        text not null,
  title               text not null,
  summary             text not null,
  fact_statement      text null,
  inference_statement text null,
  missing_data        text null,
  next_step           text null,
  status              text not null default 'active',
  severity            text not null default 'medium',
  confidence          numeric(4,3) not null default 0.500,
  priority_score      numeric(5,2) not null default 0,
  impact_summary      text null,
  why_now             text not null,
  valid_from          timestamptz not null default now(),
  valid_until         timestamptz null,
  dedupe_key          text not null,
  cluster_key         text null,
  owner_user_id       uuid null,
  acknowledged_at     timestamptz null,
  resolved_at         timestamptz null,
  dismissed_at        timestamptz null,
  snoozed_until       timestamptz null,
  last_delivered_at   timestamptz null,
  delivery_count      integer not null default 0,
  resolution_summary  text null,
  metadata            jsonb not null default '{}'::jsonb,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  constraint intelligence_findings_status_ck
    check (status in ('draft','active','acknowledged','snoozed','resolved',
                      'dismissed','expired','invalidated','conflicted')),
  constraint intelligence_findings_severity_ck
    check (severity in ('info','low','medium','high','critical')),
  constraint intelligence_findings_confidence_ck
    check (confidence >= 0 and confidence <= 1),
  constraint intelligence_findings_priority_ck
    check (priority_score between 0 and 100),
  -- Lei central 5 da SPEC-059: inferencia nao pode ser apresentada como fato.
  -- O banco recusa um Finding cujo bloco de fato esteja vazio quando ha
  -- inferencia: sem isso, a separacao vira convencao de codigo e some.
  constraint intelligence_findings_fato_antes_da_inferencia_ck
    check (inference_statement is null or fact_statement is not null)
);

create unique index if not exists ux_intelligence_findings_dedupe_vivo
  on public.intelligence_findings (company_id, dedupe_key)
  where status in ('draft','active','acknowledged','snoozed','conflicted');

create index if not exists ix_intelligence_findings_company_status
  on public.intelligence_findings (company_id, status, priority_score desc);
create index if not exists ix_intelligence_findings_usuario
  on public.intelligence_findings (company_id, user_id, status)
  where user_id is not null;
create index if not exists ix_intelligence_findings_validade
  on public.intelligence_findings (valid_until)
  where status in ('draft','active','acknowledged','snoozed');

-- -------------------------------------------------------------
-- 4. intelligence_finding_signals — SPEC-059 §10.4
-- -------------------------------------------------------------
create table if not exists public.intelligence_finding_signals (
  finding_id uuid not null references public.intelligence_findings(id) on delete cascade,
  signal_id  uuid not null references public.intelligence_signals(id) on delete cascade,
  company_id uuid not null references public.companies(id) on delete cascade,
  role       text not null default 'supporting',
  weight     numeric(4,3) not null default 1.000,
  created_at timestamptz not null default now(),
  primary key (finding_id, signal_id),
  constraint intelligence_finding_signals_role_ck
    check (role in ('primary','supporting','contradicting','context'))
);

create index if not exists ix_finding_signals_signal
  on public.intelligence_finding_signals (signal_id);

-- -------------------------------------------------------------
-- 5. recommendations — SPEC-059 §10.5
-- -------------------------------------------------------------
create table if not exists public.recommendations (
  id                     uuid primary key default gen_random_uuid(),
  company_id             uuid not null references public.companies(id) on delete cascade,
  user_id                uuid null,
  finding_id             uuid null references public.intelligence_findings(id) on delete set null,
  recommendation_type    text not null,
  title                  text not null,
  summary                text not null,
  rationale              text not null,
  confidence             numeric(4,3) not null default 0.500,
  risk_level             text not null default 'low',
  priority_score         numeric(5,2) not null default 0,
  status                 text not null default 'draft',
  action_options         jsonb not null default '[]'::jsonb,
  recommended_action_key text null,
  selected_action_key    text null,
  skill_release_id       uuid null,
  tenant_auxiliary_id    uuid null,
  routine_id             uuid null,
  work_run_id            uuid null,
  artifact_id            uuid null,
  approval_required      boolean not null default false,
  approval_request_id    uuid null,
  estimated_cost_brl_min numeric(12,2) null,
  estimated_cost_brl_max numeric(12,2) null,
  measurement_plan       jsonb not null default '{}'::jsonb,
  dedupe_key             text not null,
  expires_at             timestamptz null,
  delivered_at           timestamptz null,
  viewed_at              timestamptz null,
  accepted_at            timestamptz null,
  rejected_at            timestamptz null,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),
  constraint recommendations_status_ck
    check (status in ('draft','eligible','delivered','viewed','accepted','rejected',
                      'snoozed','executing','executed','measured','expired','withdrawn')),
  constraint recommendations_risk_ck
    check (risk_level in ('low','medium','high','critical')),
  constraint recommendations_confidence_ck
    check (confidence >= 0 and confidence <= 1),
  constraint recommendations_priority_ck
    check (priority_score between 0 and 100),
  constraint recommendations_custo_ck
    check (estimated_cost_brl_max is null or estimated_cost_brl_min is null
           or estimated_cost_brl_max >= estimated_cost_brl_min),
  -- §14.3: aceitar recomendacao nao aprova efeito. Recomendacao de risco alto
  -- nasce obrigatoriamente exigindo aprovacao — o banco nao aceita o contrario.
  constraint recommendations_risco_alto_exige_aprovacao_ck
    check (risk_level not in ('high','critical') or approval_required = true)
);

create unique index if not exists ux_recommendations_dedupe_vivo
  on public.recommendations (company_id, dedupe_key)
  where status in ('draft','eligible','delivered','viewed','accepted','executing');

create index if not exists ix_recommendations_company_status
  on public.recommendations (company_id, status, priority_score desc);
create index if not exists ix_recommendations_finding
  on public.recommendations (finding_id) where finding_id is not null;
create index if not exists ix_recommendations_validade
  on public.recommendations (expires_at)
  where status in ('eligible','delivered','viewed');

-- -------------------------------------------------------------
-- 6. recommendation_responses — SPEC-059 §10.6
-- -------------------------------------------------------------
create table if not exists public.recommendation_responses (
  id                           uuid primary key default gen_random_uuid(),
  company_id                   uuid not null references public.companies(id) on delete cascade,
  recommendation_id            uuid not null references public.recommendations(id) on delete cascade,
  user_id                      uuid null,
  action                       text not null,
  reason_code                  text null,
  comment_redacted             text null,
  snoozed_until                timestamptz null,
  selected_action_key          text null,
  created_work_run_id          uuid null,
  created_routine_id           uuid null,
  created_tenant_auxiliary_id  uuid null,
  created_at                   timestamptz not null default now(),
  constraint recommendation_responses_action_ck
    check (action in ('acknowledge','accept','reject','dismiss','snooze',
                      'not_relevant','already_solved','wrong_data',
                      'need_explanation','ask_autobrokers'))
);

create index if not exists ix_recommendation_responses_rec
  on public.recommendation_responses (recommendation_id, created_at desc);
create index if not exists ix_recommendation_responses_company
  on public.recommendation_responses (company_id, action, created_at desc);

-- -------------------------------------------------------------
-- 7. recommendation_outcomes — SPEC-059 §10.7
-- -------------------------------------------------------------
create table if not exists public.recommendation_outcomes (
  id                    uuid primary key default gen_random_uuid(),
  company_id            uuid not null references public.companies(id) on delete cascade,
  recommendation_id     uuid not null references public.recommendations(id) on delete cascade,
  work_run_id           uuid null,
  measurement_type      text not null,
  measurement_status    text not null default 'pending',
  baseline              jsonb not null default '{}'::jsonb,
  observed              jsonb not null default '{}'::jsonb,
  calculation           jsonb not null default '{}'::jsonb,
  automation_level      text not null default 'automated',
  confidence            numeric(4,3) not null default 0.500,
  value_summary         text null,
  measure_after         timestamptz null,
  measured_at           timestamptz null,
  confirmed_by_user_id  uuid null,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  constraint recommendation_outcomes_status_ck
    check (measurement_status in ('pending','in_progress','realized','partially_realized',
                                  'inconclusive','negative','expired')),
  constraint recommendation_outcomes_automation_ck
    check (automation_level in ('automated','confirmed','estimated')),
  constraint recommendation_outcomes_confidence_ck
    check (confidence >= 0 and confidence <= 1),
  -- Lei central 10: resultado nao medido e INCONCLUSIVO, nunca sucesso.
  -- Sem `measured_at` o banco recusa qualquer estado que afirme resultado.
  constraint recommendation_outcomes_sem_medicao_nao_afirma_ck
    check (measured_at is not null
           or measurement_status in ('pending','in_progress','inconclusive','expired'))
);

create unique index if not exists ux_recommendation_outcomes_por_rec
  on public.recommendation_outcomes (recommendation_id, measurement_type);
create index if not exists ix_recommendation_outcomes_janela
  on public.recommendation_outcomes (measure_after)
  where measurement_status in ('pending','in_progress');

-- -------------------------------------------------------------
-- 8. briefing_profiles — SPEC-059 §10.8
-- -------------------------------------------------------------
create table if not exists public.briefing_profiles (
  id                          uuid primary key default gen_random_uuid(),
  company_id                  uuid not null references public.companies(id) on delete cascade,
  user_id                     uuid null,
  scope                       text not null default 'company',
  name                        text not null,
  is_active                   boolean not null default true,
  timezone                    text not null default 'America/Sao_Paulo',
  cadence                     text not null default 'daily',
  schedule_spec               jsonb not null default '{"time":"08:00"}'::jsonb,
  channels                    jsonb not null default '["dashboard"]'::jsonb,
  recipient_refs              jsonb not null default '[]'::jsonb,
  quiet_hours                 jsonb not null default '{"start":"20:00","end":"08:00"}'::jsonb,
  severity_threshold          text not null default 'medium',
  max_items                   smallint not null default 7,
  max_pushes_per_day          smallint not null default 3,
  enabled_categories          jsonb not null default '[]'::jsonb,
  disabled_categories         jsonb not null default '[]'::jsonb,
  detail_level                text not null default 'standard',
  include_completed_results   boolean not null default true,
  include_suggested_automations boolean not null default true,
  sensitive_data_policy       text not null default 'redacted',
  created_by_user_id          uuid null,
  created_at                  timestamptz not null default now(),
  updated_at                  timestamptz not null default now(),
  constraint briefing_profiles_scope_ck
    check (scope in ('company','personal','role','platform_default')),
  constraint briefing_profiles_cadence_ck
    check (cadence in ('daily','weekly','event_driven','manual')),
  constraint briefing_profiles_threshold_ck
    check (severity_threshold in ('info','low','medium','high','critical')),
  constraint briefing_profiles_detail_ck
    check (detail_level in ('minimal','standard','detailed')),
  constraint briefing_profiles_sensitive_ck
    check (sensitive_data_policy in ('redacted','allowed_for_role','never')),
  constraint briefing_profiles_limites_ck
    check (max_items between 1 and 30 and max_pushes_per_day between 0 and 20),
  -- Perfil pessoal sem dono seria um perfil "de ninguem" que mesmo assim
  -- filtra por usuario. O banco impede a combinacao incoerente.
  constraint briefing_profiles_pessoal_tem_dono_ck
    check (scope <> 'personal' or user_id is not null)
);

create unique index if not exists ux_briefing_profiles_empresa_cadencia
  on public.briefing_profiles (company_id, cadence,
                               coalesce(user_id, '00000000-0000-0000-0000-000000000000'::uuid))
  where is_active;

create index if not exists ix_briefing_profiles_ativos
  on public.briefing_profiles (is_active, cadence) where is_active;

-- -------------------------------------------------------------
-- 9. briefing_publications — SPEC-059 §10.9
-- -------------------------------------------------------------
create table if not exists public.briefing_publications (
  id                   uuid primary key default gen_random_uuid(),
  company_id           uuid not null references public.companies(id) on delete cascade,
  user_id              uuid null,
  briefing_profile_id  uuid null references public.briefing_profiles(id) on delete set null,
  briefing_type        text not null,
  period_start         timestamptz not null,
  period_end           timestamptz not null,
  status               text not null default 'draft',
  work_run_id          uuid null,
  artifact_id          uuid null,
  headline             text null,
  summary_text         text not null default '',
  payload              jsonb not null default '{}'::jsonb,
  item_count           smallint not null default 0,
  critical_count       smallint not null default 0,
  recommendation_count smallint not null default 0,
  content_hash         text not null,
  delivery_status      text not null default 'pending',
  delivery_detail      jsonb not null default '{}'::jsonb,
  published_at         timestamptz null,
  expires_at           timestamptz null,
  created_at           timestamptz not null default now(),
  constraint briefing_publications_type_ck
    check (briefing_type in ('daily_operational','weekly_executive','critical_alert',
                             'on_demand','opportunity_dossier')),
  constraint briefing_publications_status_ck
    check (status in ('draft','published','suppressed','failed')),
  constraint briefing_publications_delivery_ck
    check (delivery_status in ('pending','sent','partial','failed','skipped','not_applicable')),
  constraint briefing_publications_periodo_ck
    check (period_end >= period_start)
);

-- §28.3: publicacao e idempotente por perfil + tipo + periodo. Sem isso, um
-- tick duplicado do agendador entrega o mesmo briefing duas vezes — e o
-- corretor aprende a ignorar.
create unique index if not exists ux_briefing_publications_idempotente
  on public.briefing_publications (
    company_id,
    briefing_type,
    period_start,
    period_end,
    coalesce(briefing_profile_id, '00000000-0000-0000-0000-000000000000'::uuid),
    coalesce(user_id,             '00000000-0000-0000-0000-000000000000'::uuid)
  );

create index if not exists ix_briefing_publications_company
  on public.briefing_publications (company_id, briefing_type, period_start desc);

-- -------------------------------------------------------------
-- 10. briefing_items — SPEC-059 §10.10
-- -------------------------------------------------------------
create table if not exists public.briefing_items (
  id                      uuid primary key default gen_random_uuid(),
  company_id              uuid not null references public.companies(id) on delete cascade,
  briefing_publication_id uuid not null references public.briefing_publications(id) on delete cascade,
  item_type               text not null,
  finding_id              uuid null references public.intelligence_findings(id) on delete set null,
  recommendation_id       uuid null references public.recommendations(id) on delete set null,
  work_run_id             uuid null,
  artifact_id             uuid null,
  position                smallint not null default 0,
  section                 text not null,
  headline                text not null,
  summary                 text not null default '',
  evidence_summary        text null,
  confidence              numeric(4,3) null,
  action_label            text null,
  action_payload          jsonb not null default '{}'::jsonb,
  priority_score          numeric(5,2) not null default 0,
  created_at              timestamptz not null default now(),
  constraint briefing_items_type_ck
    check (item_type in ('finding','recommendation','result','work_run','artifact',
                         'missing_data','automation')),
  constraint briefing_items_confidence_ck
    check (confidence is null or (confidence >= 0 and confidence <= 1))
);

create index if not exists ix_briefing_items_publicacao
  on public.briefing_items (briefing_publication_id, position);

-- -------------------------------------------------------------
-- 11. intelligence_rules — SPEC-059 §10.11 (tabela de PLATAFORMA)
-- -------------------------------------------------------------
create table if not exists public.intelligence_rules (
  id                  uuid primary key default gen_random_uuid(),
  rule_key            text not null unique,
  name                text not null,
  description         text not null default '',
  signal_type         text not null,
  scope               text not null default 'tenant',
  version             text not null default '1.0.0',
  status              text not null default 'active',
  implementation_kind text not null default 'deterministic_python',
  configuration       jsonb not null default '{}'::jsonb,
  minimum_evidence    smallint not null default 1,
  minimum_confidence  numeric(4,3) not null default 0.500,
  minimum_trust_tier  smallint not null default 3,
  cooldown_seconds    integer not null default 86400,
  validity_seconds    integer not null default 172800,
  severity_mapping    jsonb not null default '{}'::jsonb,
  owner               text not null default 'platform',
  last_run_at         timestamptz null,
  last_run_signals    integer not null default 0,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  constraint intelligence_rules_status_ck
    check (status in ('draft','active','paused','retired')),
  constraint intelligence_rules_kind_ck
    check (implementation_kind in ('deterministic_sql','deterministic_python',
                                   'statistical','llm_assisted','hybrid')),
  constraint intelligence_rules_scope_ck
    check (scope in ('tenant','platform')),
  constraint intelligence_rules_confidence_ck
    check (minimum_confidence >= 0 and minimum_confidence <= 1),
  -- §8.2: alerta critico exige Tier 0/1/2. Uma regra que produz sinal critico
  -- a partir de inferencia de modelo e exatamente o que a SPEC proibe.
  constraint intelligence_rules_llm_nao_e_critica_ck
    check (implementation_kind <> 'llm_assisted' or minimum_trust_tier >= 4)
);

create index if not exists ix_intelligence_rules_ativas
  on public.intelligence_rules (status, signal_type) where status = 'active';

-- -------------------------------------------------------------
-- 12. intelligence_events — SPEC-059 §10.12 (append-only)
-- -------------------------------------------------------------
create table if not exists public.intelligence_events (
  id                uuid primary key default gen_random_uuid(),
  company_id        uuid null references public.companies(id) on delete cascade,
  event_type        text not null,
  subject_type      text not null,
  subject_id        uuid null,
  actor_kind        text not null default 'system',
  actor_id          text null,
  message_human     text not null default '',
  detail            jsonb not null default '{}'::jsonb,
  correlation_id    text null,
  created_at        timestamptz not null default now(),
  constraint intelligence_events_actor_ck
    check (actor_kind in ('system','worker','user','agent','admin'))
);

create index if not exists ix_intelligence_events_company
  on public.intelligence_events (company_id, created_at desc);
create index if not exists ix_intelligence_events_subject
  on public.intelligence_events (subject_type, subject_id, created_at desc);

-- -------------------------------------------------------------
-- 13. demand_clusters — SPEC-059 §10.13 (PLATAFORMA, anonimizado)
-- -------------------------------------------------------------
create table if not exists public.demand_clusters (
  id                      uuid primary key default gen_random_uuid(),
  cluster_key             text not null unique,
  category                text not null default 'automation',
  canonical_problem       text not null,
  canonical_outcome       text not null default '',
  status                  text not null default 'new',
  tenant_count            integer not null default 0,
  request_count           integer not null default 0,
  first_seen_at           timestamptz not null default now(),
  last_seen_at            timestamptz not null default now(),
  impact_score            numeric(5,2) not null default 0,
  frequency_score         numeric(5,2) not null default 0,
  feasibility_score       numeric(5,2) not null default 0,
  risk_score              numeric(5,2) not null default 0,
  demand_score            numeric(5,2) not null default 0,
  candidate_auxiliary_key text null,
  candidate_skill_key     text null,
  capability_gap_summary  jsonb not null default '{}'::jsonb,
  reviewed_by_user_id     uuid null,
  review_note             text null,
  merged_into_id          uuid null references public.demand_clusters(id) on delete set null,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now(),
  constraint demand_clusters_status_ck
    check (status in ('new','triaged','researching','planned','building',
                      'released','rejected','merged')),
  constraint demand_clusters_merge_ck
    check (status <> 'merged' or merged_into_id is not null)
);

create index if not exists ix_demand_clusters_prioridade
  on public.demand_clusters (status, demand_score desc);

-- -------------------------------------------------------------
-- 14. demand_cluster_members — SPEC-059 §10.14
-- -------------------------------------------------------------
--
-- NAO carrega company_id de proposito. O cluster e a visao de PLATAFORMA;
-- guardar aqui de qual corretora veio cada pedido devolveria a identificacao
-- que a anonimizacao existe para remover (§18.5). O vinculo com a corretora
-- fica no objeto de origem, dentro do tenant.
create table if not exists public.demand_cluster_members (
  id                uuid primary key default gen_random_uuid(),
  cluster_id        uuid not null references public.demand_clusters(id) on delete cascade,
  member_type       text not null,
  member_id         uuid null,
  member_fingerprint text not null,
  tenant_hash       text not null,
  summary_redacted  text not null,
  occurred_at       timestamptz not null default now(),
  created_at        timestamptz not null default now(),
  constraint demand_cluster_members_type_ck
    check (member_type in ('auxiliary_request','capability_gap','intelligence_signal',
                           'broker_insight','explicit_feedback'))
);

create unique index if not exists ux_demand_cluster_members_unico
  on public.demand_cluster_members (cluster_id, member_type, member_fingerprint, tenant_hash);
create index if not exists ix_demand_cluster_members_cluster
  on public.demand_cluster_members (cluster_id, occurred_at desc);

-- -------------------------------------------------------------
-- Triggers de updated_at (reaproveita a funcao ja existente)
-- -------------------------------------------------------------
do $$
declare
  t text;
begin
  foreach t in array array[
    'intelligence_signals','intelligence_findings','recommendations',
    'recommendation_outcomes','briefing_profiles','intelligence_rules',
    'demand_clusters'
  ] loop
    execute format(
      'drop trigger if exists tg_%1$s_updated_at on public.%1$s', t);
    execute format(
      'create trigger tg_%1$s_updated_at before update on public.%1$s '
      'for each row execute function public.update_updated_at_column()', t);
  end loop;
end $$;

-- -------------------------------------------------------------
-- Append-only de intelligence_events
-- -------------------------------------------------------------
-- Mesmo padrao de `auxiliary_events` e `work_events`: UPDATE proibido sempre,
-- DELETE so com a chave de purga ligada. A valvula existe porque retencao e
-- LGPD precisam de um caminho legitimo — e um append-only sem essa valvula
-- transforma "apagar dado de quem pediu" em impossivel.
create or replace function public.intelligence_events_append_only()
returns trigger
language plpgsql
set search_path to 'pg_catalog', 'public'
as $$
begin
  if tg_op = 'UPDATE' then
    raise exception 'intelligence_events e append-only';
  end if;
  if tg_op = 'DELETE'
     and coalesce(current_setting('app.intelligence_events_purge', true), 'off') <> 'on' then
    raise exception 'DELETE exige app.intelligence_events_purge=on';
  end if;
  return case when tg_op = 'DELETE' then old else new end;
end $$;

drop trigger if exists tg_intelligence_events_append_only on public.intelligence_events;
create trigger tg_intelligence_events_append_only
  before update or delete on public.intelligence_events
  for each row execute function public.intelligence_events_append_only();

-- -------------------------------------------------------------
-- RLS — LIGADA, sem policy (nega anon/authenticated; service role passa)
-- -------------------------------------------------------------
do $$
declare
  t text;
begin
  foreach t in array array[
    'intelligence_signals','intelligence_signal_evidence','intelligence_findings',
    'intelligence_finding_signals','recommendations','recommendation_responses',
    'recommendation_outcomes','briefing_profiles','briefing_publications',
    'briefing_items','intelligence_rules','intelligence_events',
    'demand_clusters','demand_cluster_members'
  ] loop
    execute format('alter table public.%I enable row level security', t);
  end loop;
end $$;

-- =============================================================
-- VERIFY  (read-only — rodar apos o APPLY)
-- =============================================================
-- 1) as 14 tabelas existem e estao com RLS ligada e zero policy:
--
-- select c.relname, c.relrowsecurity,
--        (select count(*) from pg_policies p
--          where p.schemaname='public' and p.tablename=c.relname) policies
--   from pg_class c join pg_namespace n on n.oid=c.relnamespace
--  where n.nspname='public' and c.relkind='r'
--    and c.relname in ('intelligence_signals','intelligence_signal_evidence',
--        'intelligence_findings','intelligence_finding_signals','recommendations',
--        'recommendation_responses','recommendation_outcomes','briefing_profiles',
--        'briefing_publications','briefing_items','intelligence_rules',
--        'intelligence_events','demand_clusters','demand_cluster_members')
--  order by 1;
--  -- esperado: 14 linhas, relrowsecurity=true, policies=0
--
-- 2) toda tabela tenant tem FK de company com ON DELETE CASCADE:
--
-- select conrelid::regclass tabela, confdeltype
--   from pg_constraint
--  where contype='f' and confrelid='public.companies'::regclass
--    and conrelid::regclass::text like any (array['%intelligence%','%recommend%','%briefing%'])
--  order by 1;
--  -- esperado: confdeltype='c' em todas
--
-- 3) as garantias de conduta estao declaradas no banco:
--
-- select conname from pg_constraint where conname in (
--   'intelligence_findings_fato_antes_da_inferencia_ck',
--   'recommendation_outcomes_sem_medicao_nao_afirma_ck',
--   'recommendations_risco_alto_exige_aprovacao_ck',
--   'intelligence_rules_llm_nao_e_critica_ck') order by 1;
--  -- esperado: 4 linhas
--
-- 4) append-only de intelligence_events funciona:
--
-- insert into intelligence_events (event_type, subject_type) values ('t','t');
-- update intelligence_events set message_human='x';  -- deve FALHAR
-- delete from intelligence_events where event_type='t';  -- deve FALHAR
--
-- =============================================================
-- ROLLBACK
-- =============================================================
-- Reversao integral. Nenhum objeto pre-existente e tocado por esta migration,
-- entao o drop das 14 tabelas devolve o banco ao estado anterior.
--
-- drop trigger if exists tg_intelligence_events_append_only on public.intelligence_events;
-- drop function if exists public.intelligence_events_append_only();
-- drop table if exists public.demand_cluster_members cascade;
-- drop table if exists public.demand_clusters cascade;
-- drop table if exists public.intelligence_events cascade;
-- drop table if exists public.intelligence_rules cascade;
-- drop table if exists public.briefing_items cascade;
-- drop table if exists public.briefing_publications cascade;
-- drop table if exists public.briefing_profiles cascade;
-- drop table if exists public.recommendation_outcomes cascade;
-- drop table if exists public.recommendation_responses cascade;
-- drop table if exists public.recommendations cascade;
-- drop table if exists public.intelligence_finding_signals cascade;
-- drop table if exists public.intelligence_findings cascade;
-- drop table if exists public.intelligence_signal_evidence cascade;
-- drop table if exists public.intelligence_signals cascade;
-- =============================================================
