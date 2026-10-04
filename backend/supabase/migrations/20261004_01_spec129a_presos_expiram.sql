-- =============================================================
-- MIGRATION: 20261004_01_spec129a_presos_expiram
-- SPEC:      SPEC-129-A — F4 · presos e rastro (§5 A REGRA DOS PRESOS)
-- AUTOR:     builder F4 (Opus 5.5)            DATA: 2026-10-04
-- OBJETIVO:  os trabalhos `smith` parados na fila há mais de 2 h (idade por `requested_at`, NUNCA
--            `queued_at`) EXPIRAM SEM RODAR, com um evento `run.expired` legível. A janela seguinte
--            de cada workflow periódico já fez o trabalho (📊 4.969 `detect_signals` concluídos, §3 D-129A-5).
--
-- 📊 ANTES (04/10/2026 ~15:00 UTC, `execute_sql` só leitura, projeto dcajcvlzcjbmyapmklil):
--    select workflow_key,status::text,runtime_kind,count(*) from work_runs
--     where status::text not in ('completed','failed','cancelled','expired') group by 1,2,3;
--    → intelligence.detect_signals queued smith 20 · intelligence.measure_outcomes queued smith 1 ·
--      claims.shadow running sombra 3 (SEM lease) · metric.proposal waiting_approval proposta 2 ·
--      acionamento.seguradora waiting_input acionamento 1 · retry_scheduled 0.
--    O WHERE do APPLY casa 21 linhas (20 detect_signals + 1 measure_outcomes, 28/07 → 01/10);
--    a lista dos 21 `id` está no relatório da F4, ANTES do APPLY. `work_events` com `run.expired`: 0.
--
-- A REGRA (SPEC §5):
--    expira sem rodar ⇔ runtime_kind='smith' E status ∈ (queued, retry_scheduled) E sem lease
--                       E agora − requested_at > 2 h
--    nunca é tocado   ⇔ runtime_kind ∈ (acionamento, sombra, proposta) — os "sem fila"
--
-- 🔴 A MARCA: esta migration grava `error_code='expirado_sem_rodar_129a'` e o evento com
--    payload {"spec":"129-A","migration":"_01"}. A expiração em TEMPO DE EXECUÇÃO (o despertador da F1)
--    usa OUTRO código, `expirado_pela_idade` — o ROLLBACK abaixo filtra pela marca desta migration e
--    por isso NUNCA ressuscita o que o despertador expirou.
--
-- APPLY:  UM comando atômico: seleciona os presos (FOR UPDATE), muda para `expired` com a marca e grava um
--         `run.expired` por run com o STATUS DE ANTES no payload (`status_antes`) — é dele que o ROLLBACK
--         restaura (📊 hoje os 21 são `queued`; um `retry_scheduled` voltaria `retry_scheduled`, não `queued`).
--         Idempotente: na 2ª vez a seleção casa 0 linhas e nada é escrito.
--
-- VERIFY (read-only · esperado no dia 04/10: 21 · 21 · 6 · 0):
--   select (select count(*) from public.work_runs where error_code='expirado_sem_rodar_129a') expirados,
--          (select count(*) from public.work_events where event_type='run.expired'
--             and payload_redacted->>'spec'='129-A' and payload_redacted->>'migration'='_01') eventos,
--          (select count(*) from public.work_runs where runtime_kind<>'smith'
--             and status::text not in ('completed','failed','cancelled','expired')) sem_fila_vivos,
--          (select count(*) from public.work_runs where runtime_kind='smith'
--             and status in ('queued','retry_scheduled') and lease_owner is null
--             and requested_at < now()-interval '2 hours') presos_restantes;   -- o MESMO WHERE do APPLY
--
-- ROLLBACK (reversível pela marca; `updated_at` NÃO volta — `trg_work_runs_company_imutavel` o regrava):
--   update public.work_runs w
--      set status = coalesce(e.payload_redacted->>'status_antes', 'queued')::work_run_status,
--          finished_at = null, error_code = null, error_message = null
--     from public.work_events e
--    where e.work_run_id = w.id and e.company_id = w.company_id and e.event_type = 'run.expired'
--      and e.payload_redacted->>'spec' = '129-A' and e.payload_redacted->>'migration' = '_01'
--      and w.error_code = 'expirado_sem_rodar_129a' and w.status = 'expired';
--   -- work_events é append-only (`trg_work_events_no_update`): o DELETE exige a PURGA GOVERNADA,
--   -- declarada só nesta transação (set_config(..., true) = local à transação).
--   select set_config('app.work_events_purge','on',true);
--   delete from public.work_events where event_type='run.expired'
--      and payload_redacted->>'spec'='129-A' and payload_redacted->>'migration'='_01';
--   -- ⚠️ o rollback NÃO re-despacha: os 21 voltam ao status de antes com o outbox `published` de antes — o
--   --    mesmo estado preso de 04/10, e o re-despacho da F1 (`redespachar_parados`) os expira de novo
--   --    pela idade (`expirado_pela_idade`).
--
-- EXPAND-FIRST: não se aplica (migration de DADO; nenhuma estrutura muda)
-- DESTRUTIVA:   não — muda estado de 21 runs que não rodariam; reversível pela marca
-- ORDEM:        _01 → _02 → _03 (a _02 cria `ck_work_runs_espera_tem_relogio`; a _01 não depende dela)
-- =============================================================

with presos as (
  select id, status::text as status_antes
    from public.work_runs
   where runtime_kind = 'smith'
     and status in ('queued', 'retry_scheduled')
     and lease_owner is null
     and requested_at < now() - interval '2 hours'
     for update
), expirados as (
  update public.work_runs w
     set status        = 'expired',
         finished_at   = now(),
         error_code    = 'expirado_sem_rodar_129a',
         error_message = 'Expirou sem rodar: ficou na fila além do limite (SPEC-129-A). A próxima janela já fez o trabalho.'
    from presos p
   where w.id = p.id
  returning w.id, w.company_id, w.error_message, p.status_antes
)
insert into public.work_events (company_id, work_run_id, event_type, actor_type, severity, message_human, payload_redacted)
select x.company_id, x.id, 'run.expired', 'system', 'warning', x.error_message,
       jsonb_build_object('spec', '129-A', 'migration', '_01', 'status_antes', x.status_antes)
  from expirados x;
