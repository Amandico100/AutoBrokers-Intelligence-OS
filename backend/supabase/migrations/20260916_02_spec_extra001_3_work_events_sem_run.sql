-- =============================================================
-- MIGRATION: work_events.work_run_id deixa de ser obrigatório
-- SPEC:      SPEC-EXTRA-001.3 — BLOCO E (achado do BLOCO 0)
-- AUTOR:     executor Opus 5 (AAA FAST)      DATA: 2026-09-16
-- OBJETIVO:  o diário do atendimento pode registrar o que é de uma CONVERSA
--
-- 🔴 POR QUE ELA EXISTE — e ela NÃO estava na proposta (§13 previa uma só).
--
-- 📊 Medido em 16/09/2026, antes de escrever uma linha de código:
--
--   insert into work_events (company_id,event_type,actor_type,severity,
--                            message_human,payload_redacted)
--        values (<empresa>,'teste.b0','system','info','teste','{}'::jsonb);
--   -> NotNullViolation: null value in column "work_run_id" of relation
--      "work_events" violates not-null constraint
--
-- Consequência, e ela explica um número que a proposta atribuía a outra causa:
-- `handoff_watchdog._anotar_no_diario` (:446) NUNCA passou `work_run_id`, e
-- engole a própria exceção. 📊 `select count(*) from work_events where
-- event_type like 'handoff%'` -> 0 em toda a base. A proposta lia esse 0 como
-- "o re-alerta nunca disparou"; ele é TAMBÉM "o diário nunca conseguiu
-- escrever". Sem esta migration, o outcome desta SPEC — *todo envio ao grupo
-- fica contado* — é impossível por construção, e o resumo das 19h leria uma
-- tabela que ninguém consegue preencher.
--
-- ⚠️ É a mesma trava que P-PILOTO-14 registra para `claims_shadow`.
--
-- APPLY:     alter table public.work_events alter column work_run_id drop not null;
-- VERIFY:    SQL read-only no fim deste arquivo
-- ROLLBACK:  -- ⚠️ só é seguro enquanto NÃO houver linha com work_run_id nulo:
--            --   select count(*) from work_events where work_run_id is null;  -- tem de ser 0
--            -- Havendo linhas, APAGÁ-LAS é decisão do Founder (append-only).
--            alter table public.work_events alter column work_run_id set not null;
--
-- EXPAND-FIRST: sim — afrouxa, não aperta. Nenhuma linha existente muda,
--               nenhum leitor perde coluna, nada é apagado.
-- DESTRUTIVA:   não
--
-- ⚠️ A FK composta continua valendo e continua protegendo o §7:
--   fk_work_events_run_same_company (work_run_id, company_id)
--     REFERENCES work_runs(id, company_id)
-- Em MATCH SIMPLE (o padrão do Postgres) uma FK composta com QUALQUER coluna
-- nula é satisfeita sem checar — então um evento sem run continua impedido de
-- apontar para o run de outra corretora, porque ele não aponta para run nenhum.
-- =============================================================

do $$
begin
  if exists (select 1 from information_schema.columns
              where table_schema='public' and table_name='work_events'
                and column_name='work_run_id' and is_nullable='NO') then
    alter table public.work_events alter column work_run_id drop not null;
  end if;
end $$;

-- =============================================================
-- VERIFY (read-only)
-- =============================================================
-- select is_nullable = 'YES' as run_id_opcional
--   from information_schema.columns
--  where table_schema='public' and table_name='work_events'
--    and column_name='work_run_id';
--
-- select count(*) = 1 as fk_composta_intacta
--   from pg_constraint
--  where conrelid='public.work_events'::regclass
--    and conname='fk_work_events_run_same_company';
