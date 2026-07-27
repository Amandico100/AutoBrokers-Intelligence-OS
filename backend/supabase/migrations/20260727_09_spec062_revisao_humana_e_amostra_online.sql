-- SPEC-062 §10.9 e §10.10 — o que o juiz não decidiu, e a amostra do tráfego real.
--
-- APLICADA EM PRODUÇÃO em 27/07/2026 (nome: spec062_revisao_humana_e_amostra_online).
-- Este arquivo é o registro canônico da versão aplicada.
--
-- `human_review_tasks`: confiança baixa do juiz LLM não vira aprovação nem
-- silêncio — vira fila. Silêncio é indistinguível de aprovação para quem lê o
-- painel, e é assim que um verde falso ganha confiança.
--
-- `online_eval_samples`: §17 — amostra do tráfego REAL, para descobrir queda de
-- qualidade que nenhum dataset previu. A amostra guarda REFERÊNCIA, não
-- conteúdo: PII de segurado vive só em `attendance_transcripts` (§19.3).

create table if not exists public.human_review_tasks (
  id            uuid primary key default gen_random_uuid(),
  run_id        uuid references public.eval_runs(id) on delete cascade,
  case_id       uuid references public.eval_cases(id) on delete cascade,
  company_id    uuid references public.companies(id) on delete set null,
  motivo        text not null,
  amostra       jsonb not null default '{}'::jsonb,
  status        text not null default 'pendente',
  veredito      boolean,
  revisado_por  text,
  revisado_em   timestamptz,
  observacao    text,
  created_at    timestamptz not null default now(),
  constraint human_review_status_ck
    check (status in ('pendente','revisado','descartado'))
);

create table if not exists public.online_eval_samples (
  id            uuid primary key default gen_random_uuid(),
  company_id    uuid references public.companies(id) on delete cascade,
  superficie    text not null,
  referencia    text,
  correlation_id text,
  vereditos     jsonb not null default '[]'::jsonb,
  precisa_revisao boolean not null default false,
  amostrado_em  timestamptz not null default now()
);

create index if not exists ix_review_pendente
  on public.human_review_tasks (status, created_at desc)
  where status = 'pendente';
create index if not exists ix_online_samples_empresa
  on public.online_eval_samples (company_id, amostrado_em desc);
create index if not exists ix_online_samples_revisao
  on public.online_eval_samples (precisa_revisao, amostrado_em desc)
  where precisa_revisao;

do $$
declare t text;
begin
  foreach t in array array['human_review_tasks','online_eval_samples'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon, authenticated', t);
  end loop;
end $$;

-- VERIFY (executado em 27/07/2026): rowsecurity = true, policies = 0 nas duas.
-- ROLLBACK (não executar sem decisão registrada), por nome exato:
--   drop table if exists public.online_eval_samples;
--   drop table if exists public.human_review_tasks;
