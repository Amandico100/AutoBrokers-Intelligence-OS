-- =============================================================
-- MIGRATION: spec061_control_plane_foundation
-- SPEC:      SPEC-061 Bloco A — §9 (modelo de dados minimo)
-- AUTOR:     Executor Opus                DATA: 2026-07-27
-- OBJETIVO:  as sete tabelas que dao ao Portal Admin uma AUTORIDADE
--            propria, verificavel no servidor.
--
-- APPLY:     7 create table if not exists + indices + 1 trigger.
-- VERIFY:    ver bloco VERIFY ao final.
-- ROLLBACK:  ver bloco ROLLBACK ao final (drop por nome exato).
--
-- EXPAND-FIRST: sim — so cria. Nenhuma tabela existente e alterada.
-- DESTRUTIVA:   nao
--
-- POR QUE ISTO E O PRIMEIRO PASSO DA SPEC-061
-- -------------------------------------------
-- Hoje o Portal Admin autoriza por UM bit: `master` ou nao. Quem entra ve
-- tudo e pode tudo — 39 telas e 114 rotas de API atras de um unico sim.
--
-- Isso torna impossivel escrever as frases que a §8.5 exige:
--
--   "o financeiro nao acessa conteudo sensivel de corretora"
--   "o auditor e somente leitura"
--   "o suporte nao altera cobranca"
--   "quem cria release nao precisa ser quem publica"
--
-- Nao e que essas regras estejam mal implementadas: elas nao TEM ONDE ser
-- expressas. Estas tabelas sao esse lugar.
--
-- POR QUE PERMISSION E CODIGO E PAPEL E DADO
-- ------------------------------------------
-- A lista de permissions (`admin.overview.read`, `work_runs.retry`, ...) e uma
-- constante do produto: ela muda quando uma tela nova nasce, junto com o
-- deploy que a criou. Mantê-la em tabela criaria um estado onde o codigo
-- cobra uma permission que o banco nao conhece — e a tela some sem ninguem
-- entender por que.
--
-- Quem recebe qual papel, e ate quando, e dado operacional: muda numa terca a
-- tarde, sem deploy. Por isso o BINDING e tabela e a MATRIZ e codigo.
--
-- RLS: ligada e sem policy em todas as sete. O backend usa service role; o
-- navegador nao le nenhuma delas diretamente — nem com sessao valida.
-- =============================================================

-- -------------------------------------------------------------
-- 9.1 Quem tem qual papel na plataforma
-- -------------------------------------------------------------
create table if not exists public.platform_admin_role_bindings (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null,
  role_key            text not null,
  status              text not null default 'active',
  starts_at           timestamptz not null default now(),
  -- Expiracao existe para que acesso administrativo possa ser TEMPORARIO por
  -- construcao. Acesso concedido "so por essa semana" que nao expira sozinho
  -- vira acesso permanente na primeira vez que alguem esquece.
  expires_at          timestamptz null,
  granted_by_user_id  uuid not null,
  reason              text null,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),

  constraint platform_admin_role_bindings_role_ck check (role_key in (
    'platform_owner', 'platform_admin', 'platform_operations',
    'platform_support', 'platform_finance', 'platform_security',
    'platform_curator', 'platform_release_manager', 'platform_auditor',
    'platform_viewer')),
  constraint platform_admin_role_bindings_status_ck
    check (status in ('active', 'suspended', 'revoked', 'expired')),
  constraint platform_admin_role_bindings_janela_ck
    check (expires_at is null or expires_at > starts_at)
);

-- §9.1 "Unique ativo por (user_id, role_key)". Parcial: um papel revogado no
-- passado nao pode impedir que a mesma pessoa o receba de novo — o historico
-- de concessoes precisa continuar existindo.
create unique index if not exists uq_platform_admin_role_ativo
  on public.platform_admin_role_bindings (user_id, role_key)
  where status = 'active';

create index if not exists ix_platform_admin_role_user
  on public.platform_admin_role_bindings (user_id, status);

-- Quem expira quando? Sem este indice, a varredura de expiracao leria a
-- tabela inteira a cada passagem.
create index if not exists ix_platform_admin_role_expira
  on public.platform_admin_role_bindings (expires_at)
  where status = 'active' and expires_at is not null;


-- -------------------------------------------------------------
-- 9.2 Excecao nominal a matriz de papeis
-- -------------------------------------------------------------
--
-- `expires_at` e NOT NULL aqui, e nao por simetria: override e excecao, e
-- excecao sem prazo e a regra nova que ninguem escreveu. A §9.2 diz
-- "nao usar overrides como substituto da matriz de papeis" — o jeito de fazer
-- valer e impedir que o override sobreviva sozinho.
create table if not exists public.platform_admin_permission_overrides (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null,
  permission_key      text not null,
  effect              text not null,
  scope               jsonb not null default '{}'::jsonb,
  starts_at           timestamptz not null default now(),
  expires_at          timestamptz not null,
  reason              text not null,
  granted_by_user_id  uuid not null,
  created_at          timestamptz not null default now(),

  constraint platform_admin_perm_override_effect_ck
    check (effect in ('allow', 'deny')),
  constraint platform_admin_perm_override_janela_ck
    check (expires_at > starts_at),
  -- Sem motivo escrito, ninguem consegue revisar a excecao depois. "reason"
  -- vazio e o mesmo que nao ter reason.
  constraint platform_admin_perm_override_motivo_ck
    check (length(btrim(reason)) >= 10)
);

create index if not exists ix_platform_admin_override_user
  on public.platform_admin_permission_overrides (user_id, permission_key);


-- -------------------------------------------------------------
-- 9.3 Trilha de auditoria — append-only
-- -------------------------------------------------------------
create table if not exists public.admin_audit_events (
  id                    uuid primary key default gen_random_uuid(),
  occurred_at           timestamptz not null default now(),
  actor_user_id         uuid not null,
  actor_session_id      uuid null,
  actor_roles           text[] not null default '{}',
  permission_key        text null,
  action_key            text not null,
  risk_tier             text not null default 'low',
  target_type           text not null,
  target_id             text null,
  company_id            uuid null,
  support_session_id    uuid null,
  command_id            uuid null,
  idempotency_key       text null,
  work_run_id           uuid null,
  approval_request_id   uuid null,
  correlation_id        text null,
  trace_id              text null,
  reason_redacted       text null,
  before_redacted       jsonb null,
  after_redacted        jsonb null,
  result_status         text not null,
  result_code           text null,
  metadata_redacted     jsonb not null default '{}'::jsonb,

  constraint admin_audit_events_risk_ck
    check (risk_tier in ('low', 'medium', 'high', 'critical')),
  constraint admin_audit_events_result_ck
    check (result_status in ('succeeded', 'failed', 'denied', 'partial')),
  -- Acao critica sem motivo escrito nao entra. A pergunta que a auditoria
  -- precisa responder seis meses depois nao e "o que foi feito" — o `action_key`
  -- ja diz isso — e sim "por que alguem achou que devia".
  constraint admin_audit_events_critico_exige_motivo_ck
    check (risk_tier <> 'critical'
           or (reason_redacted is not null and length(btrim(reason_redacted)) >= 10))
);

create index if not exists ix_admin_audit_recente
  on public.admin_audit_events (occurred_at desc);
create index if not exists ix_admin_audit_ator
  on public.admin_audit_events (actor_user_id, occurred_at desc);
create index if not exists ix_admin_audit_empresa
  on public.admin_audit_events (company_id, occurred_at desc)
  where company_id is not null;
create index if not exists ix_admin_audit_acao
  on public.admin_audit_events (action_key, occurred_at desc);
create index if not exists ix_admin_audit_risco
  on public.admin_audit_events (risk_tier, occurred_at desc)
  where risk_tier in ('high', 'critical');

-- Append-only de verdade, no banco.
--
-- Uma trilha que o proprio administrador pode editar nao e trilha: e um
-- rascunho. E quem mais teria motivo para reescrever uma linha e exatamente
-- quem a trilha existe para registrar.
create or replace function public.admin_audit_events_append_only()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  raise exception
    'admin_audit_events e append-only: % nao e permitido (SPEC-061 §9.3)',
    tg_op;
end;
$$;

drop trigger if exists trg_admin_audit_events_append_only on public.admin_audit_events;
create trigger trg_admin_audit_events_append_only
  before update or delete on public.admin_audit_events
  for each row execute function public.admin_audit_events_append_only();


-- -------------------------------------------------------------
-- 9.4 Sessao de suporte — acesso a UMA corretora, por tempo determinado
-- -------------------------------------------------------------
--
-- Sem isto, ajudar uma corretora exige um poder que serve para todas e nao
-- acaba nunca. A sessao de suporte troca isso por: esta corretora, este
-- motivo, ate esta hora.
create table if not exists public.admin_support_sessions (
  id                    uuid primary key default gen_random_uuid(),
  actor_user_id         uuid not null,
  company_id            uuid not null references public.companies(id) on delete cascade,
  mode                  text not null default 'read_only',
  reason                text not null,
  status                text not null default 'active',
  starts_at             timestamptz not null default now(),
  expires_at            timestamptz not null,
  closed_at             timestamptz null,
  approved_by_user_id   uuid null,
  created_at            timestamptz not null default now(),

  constraint admin_support_sessions_mode_ck
    check (mode in ('read_only', 'controlled_write')),
  constraint admin_support_sessions_status_ck
    check (status in ('active', 'expired', 'closed', 'revoked')),
  constraint admin_support_sessions_janela_ck
    check (expires_at > starts_at),
  constraint admin_support_sessions_motivo_ck
    check (length(btrim(reason)) >= 10),
  -- Escrever no lugar da corretora exige um segundo humano. Ler para ajudar
  -- e uma coisa; agir em nome dela e outra.
  constraint admin_support_sessions_escrita_exige_aprovacao_ck
    check (mode <> 'controlled_write' or approved_by_user_id is not null)
);

create index if not exists ix_admin_support_ativa
  on public.admin_support_sessions (company_id, status, expires_at desc);
create index if not exists ix_admin_support_ator
  on public.admin_support_sessions (actor_user_id, starts_at desc);


-- -------------------------------------------------------------
-- 9.5 Caixa de entrada do operador — estado PESSOAL
-- -------------------------------------------------------------
--
-- §9.5: "o item continua pertencendo a autoridade de origem". Esta tabela
-- guarda que EU li, EU adiei — nunca o item em si. Copiar o item para ca
-- criaria uma segunda verdade sobre o mesmo fato, e as duas divergiriam na
-- primeira atualizacao.
create table if not exists public.admin_inbox_states (
  id              uuid primary key default gen_random_uuid(),
  admin_user_id   uuid not null,
  source_type     text not null,
  source_id       text not null,
  state           text not null default 'unread',
  snoozed_until   timestamptz null,
  note_redacted   text null,
  updated_at      timestamptz not null default now(),

  constraint admin_inbox_states_state_ck
    check (state in ('unread', 'read', 'acknowledged', 'snoozed', 'dismissed')),
  -- Adiar sem data e dispensar com outro nome — e some do radar sem ninguem
  -- ter decidido isso.
  constraint admin_inbox_states_snooze_exige_data_ck
    check (state <> 'snoozed' or snoozed_until is not null)
);

create unique index if not exists uq_admin_inbox_item_por_pessoa
  on public.admin_inbox_states (admin_user_id, source_type, source_id);
create index if not exists ix_admin_inbox_pendente
  on public.admin_inbox_states (admin_user_id, state, updated_at desc);


-- -------------------------------------------------------------
-- 9.6 Incidentes de plataforma
-- -------------------------------------------------------------
--
-- §9.6 e explicita: "falha isolada de Work Run nao vira automaticamente
-- incidente". Incidente e o que afeta a PLATAFORMA ou VARIAS corretoras —
-- e por isso `scope` e obrigatorio e nomeado.
create table if not exists public.platform_incidents (
  id                      uuid primary key default gen_random_uuid(),
  incident_key            text not null unique,
  severity                text not null,
  status                  text not null default 'open',
  scope                   text not null,
  summary                 text not null,
  impact_summary          text null,
  started_at              timestamptz null,
  detected_at             timestamptz not null default now(),
  acknowledged_at         timestamptz null,
  resolved_at             timestamptz null,
  owner_user_id           uuid null,
  source_refs             jsonb not null default '[]'::jsonb,
  work_run_id             uuid null,
  postmortem_artifact_id  uuid null,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now(),

  constraint platform_incidents_sev_ck
    check (severity in ('sev1', 'sev2', 'sev3', 'sev4')),
  constraint platform_incidents_status_ck
    check (status in ('open', 'acknowledged', 'mitigated', 'resolved', 'closed')),
  constraint platform_incidents_scope_ck
    check (scope in ('platform', 'multi_tenant', 'provider', 'infrastructure')),
  -- Incidente grave fechado sem postmortem e a forma mais comum de repetir o
  -- mesmo incidente.
  constraint platform_incidents_sev1_fechado_exige_postmortem_ck
    check (severity <> 'sev1' or status <> 'closed'
           or postmortem_artifact_id is not null),
  constraint platform_incidents_resolvido_tem_data_ck
    check (status not in ('resolved', 'closed') or resolved_at is not null)
);

create index if not exists ix_platform_incidents_abertos
  on public.platform_incidents (status, severity, detected_at desc)
  where status in ('open', 'acknowledged', 'mitigated');


-- -------------------------------------------------------------
-- 9.7 Visao salva do operador
-- -------------------------------------------------------------
create table if not exists public.admin_saved_views (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null,
  view_key    text not null,
  name        text not null,
  filters     jsonb not null default '{}'::jsonb,
  columns     jsonb not null default '[]'::jsonb,
  sort        jsonb not null default '{}'::jsonb,
  is_default  boolean not null default false,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create unique index if not exists uq_admin_saved_view_nome
  on public.admin_saved_views (user_id, view_key, name);
-- Uma visao padrao por tela e por pessoa. Duas "padrao" fariam a tela abrir
-- de um jeito diferente a cada vez, sem nada que explique.
create unique index if not exists uq_admin_saved_view_padrao
  on public.admin_saved_views (user_id, view_key)
  where is_default;


-- -------------------------------------------------------------
-- RLS: ligada, sem policy — o mesmo padrao das SPECs 054-060
-- -------------------------------------------------------------
--
-- Sem policy, `anon` e `authenticated` sao negados em TUDO. O backend usa
-- service role e filtra na camada de repositorio. Uma policy escrita aqui
-- seria uma segunda autoridade de autorizacao ao lado do RBAC do §8 — e duas
-- autoridades divergem.
alter table public.platform_admin_role_bindings        enable row level security;
alter table public.platform_admin_permission_overrides enable row level security;
alter table public.admin_audit_events                  enable row level security;
alter table public.admin_support_sessions              enable row level security;
alter table public.admin_inbox_states                  enable row level security;
alter table public.platform_incidents                  enable row level security;
alter table public.admin_saved_views                   enable row level security;

-- =============================================================
-- VERIFY
-- =============================================================
-- -- 1. As sete existem, com RLS e sem policy:
-- select c.relname, c.relrowsecurity,
--        (select count(*) from pg_policies p where p.tablename = c.relname) policies
--   from pg_class c join pg_namespace n on n.oid = c.relnamespace
--  where n.nspname='public' and c.relname in (
--    'platform_admin_role_bindings','platform_admin_permission_overrides',
--    'admin_audit_events','admin_support_sessions','admin_inbox_states',
--    'platform_incidents','admin_saved_views')
--  order by 1;
--   -- esperado: 7 linhas, relrowsecurity=true, policies=0
--
-- -- 2. As garantias de conduta recusam o que devem recusar (rode dentro de
-- --    um bloco DO encerrado por `raise exception`, para nao persistir):
--   -- papel inexistente                     -> check_violation
--   -- override sem prazo                    -> not_null_violation
--   -- override com reason curto             -> check_violation
--   -- auditoria critica sem motivo          -> check_violation
--   -- UPDATE/DELETE em admin_audit_events   -> excecao do trigger
--   -- suporte controlled_write sem aprovador-> check_violation
--   -- snooze sem data                       -> check_violation
--   -- sev1 fechado sem postmortem           -> check_violation
--   -- dois papeis ativos iguais             -> unique_violation
--
-- =============================================================
-- ROLLBACK
-- =============================================================
-- drop trigger if exists trg_admin_audit_events_append_only on public.admin_audit_events;
-- drop function if exists public.admin_audit_events_append_only();
-- drop table if exists public.admin_saved_views;
-- drop table if exists public.platform_incidents;
-- drop table if exists public.admin_inbox_states;
-- drop table if exists public.admin_support_sessions;
-- drop table if exists public.admin_audit_events;
-- drop table if exists public.platform_admin_permission_overrides;
-- drop table if exists public.platform_admin_role_bindings;
-- =============================================================
