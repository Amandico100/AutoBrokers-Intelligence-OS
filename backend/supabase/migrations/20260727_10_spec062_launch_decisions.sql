-- SPEC-062 §33.5 — a Decisão de Lançamento, com a evidência do momento.
--
-- APLICADA EM PRODUÇÃO em 27/07/2026 (nome: spec062_launch_decisions).
-- Este arquivo é o registro canônico da versão aplicada.
--
-- Daqui a seis meses, "por que fomos ao ar naquele dia?" precisa de resposta
-- consultável — não de memória. A coluna `evidencia` guarda o retrato da
-- prontidão no instante da decisão.
--
-- Por isso a linha é imutável: reescrever a evidência depois do fato
-- transforma registro em narrativa. Mudou de ideia? Registre uma decisão nova.

create table if not exists public.launch_decisions (
  id            uuid primary key default gen_random_uuid(),
  decisao       text not null,
  decidido_por  text not null,
  motivo        text not null,
  company_id    uuid references public.companies(id) on delete set null,
  evidencia     jsonb not null default '{}'::jsonb,
  created_at    timestamptz not null default now(),
  constraint launch_decisao_ck check (decisao in ('go','no_go','adiado'))
);

create index if not exists ix_launch_decisions_recentes
  on public.launch_decisions (created_at desc);

alter table public.launch_decisions enable row level security;
revoke all on public.launch_decisions from anon, authenticated;

create or replace function public.tg_launch_decisions_append_only()
returns trigger language plpgsql as $fn$
begin
  raise exception 'launch_decisions e append-only: registre uma decisao nova';
end $fn$;

drop trigger if exists launch_decisions_append_only on public.launch_decisions;
create trigger launch_decisions_append_only
  before update or delete on public.launch_decisions
  for each row execute function public.tg_launch_decisions_append_only();

-- ROLLBACK (não executar sem decisão registrada), por nome exato:
--   drop trigger if exists launch_decisions_append_only on public.launch_decisions;
--   drop function if exists public.tg_launch_decisions_append_only();
--   drop table if exists public.launch_decisions;
