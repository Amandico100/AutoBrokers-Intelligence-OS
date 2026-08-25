-- SPEC-085 · BLOCO A — as duas linhas que dizem "concluído" sobre um travamento
-- ============================================================================
-- 24/08/2026 · branch feat/spec085-o-destravamento-nao-trava-em-silencio
--
-- 📊 O ESTADO MEDIDO ANTES, e são só quatro linhas na história do produto:
--
--   run       status      fase          error_code                        resumo
--   373b8395  cancelled   human_phase   —                                 "sessão encerrada"      ✅ certo
--   cb6478f5  completed   needs_human   needs_human:sentinela_stall       "Caso entregue…"        🔴 travamento como SUCESSO
--   448d3f08  completed   test_aborted  needs_human:missing_slots:…       "Simulação completa"    🔴 erro VENCIDO
--   e5279497  completed   monitoring    —                                 "Monitoramento…"        ✅ certo
--
-- 🔴 `cb6478f5` é O travamento durável do produto — o `sentinela_stall`, a única
-- família com prova em produção. Ele está gravado como concluído, o que o torna
-- invisível para qualquer consulta que pergunte "o que ficou em pé?".
--
-- ⚠️ `448d3f08` é DIFERENTE, e a diferença decide o conserto: a fase final dele
-- é `test_aborted`, que **é** desfecho — `completed` está CERTO. O que mente é o
-- `error_code`, herdado de um travamento anterior do mesmo caso, que nunca foi
-- limpo. Tratar os dois igual estragaria o segundo.
--
-- ⚠️ E as outras duas NÃO SÃO TOCADAS. É a linha de controle desta migration.
--
-- O código que impede a reincidência está em `dispatch_router.py`:
--   · a reconciliação usa `status_duravel_da_fase` em vez de `completed` fixo
--   · o checkpoint limpa `finished_at`/`result_summary` ao travar
--   · e limpa `error_code`/`error_message` ao concluir
-- ============================================================================
-- APPLY    este arquivo. Idempotente: os `WHERE` só casam o estado defeituoso.
-- VERIFY   o bloco no fim.
-- ROLLBACK o bloco no fim, com os valores medidos ANTES.
-- ============================================================================

BEGIN;

-- 1. O TRAVAMENTO deixa de ser sucesso.
--    `WHERE status='completed'` torna a migration idempotente e impede que ela
--    reescreva um run que uma pessoa já tenha assumido depois.
UPDATE public.work_runs
   SET status            = 'waiting_input',
       finished_at       = NULL,
       progress_percent  = GREATEST(5, LEAST(95, 9 * 15)),   -- ordem da fase `needs_human`
       unblock_state     = 'travado',
       result_summary    = 'Parou e precisa de uma pessoa da corretora. Motivo: sentinela_stall',
       updated_at        = now()
 WHERE runtime_kind    = 'acionamento'
   AND current_step_key = 'needs_human'
   AND status           = 'completed';

-- 2. O ERRO VENCIDO sai de quem concluiu de verdade.
--    ⚠️ A história não se perde: a etapa `needs_human` continua em `work_steps`
--    e a transição em `work_events`. O `error_code` do RUN descreve o DESFECHO.
UPDATE public.work_runs
   SET error_code    = NULL,
       error_message = NULL,
       updated_at    = now()
 WHERE runtime_kind = 'acionamento'
   AND status       = 'completed'
   AND current_step_key <> 'needs_human'
   AND error_code LIKE 'needs_human:%';

COMMIT;

-- ============================================================================
-- VERIFY — só SELECT.
-- ============================================================================
--   -- espera: 1 linha, `waiting_input` + `travado` + finished_at NULO
--   select left(id::text,8), status, current_step_key, unblock_state,
--          error_code, finished_at is null as sem_finished_at, progress_percent
--     from work_runs
--    where runtime_kind='acionamento' and unblock_state='travado';
--
--   -- espera: 0 — nenhum concluído carrega erro de travamento
--   select count(*) from work_runs
--    where runtime_kind='acionamento' and status='completed'
--      and error_code like 'needs_human:%';
--
--   -- 🔴 CONTROLE: as outras TRÊS continuam como estavam (espera 3)
--   select count(*) from work_runs
--    where runtime_kind='acionamento'
--      and (current_step_key, status) in
--          (('human_phase','cancelled'), ('test_aborted','completed'),
--           ('monitoring','completed'));
--
-- ============================================================================
-- ROLLBACK — com os valores medidos ANTES, nominalmente.
-- ============================================================================
--   BEGIN;
--   UPDATE public.work_runs SET
--     status='completed', finished_at='2026-08-18T08:03:00.260804+00',
--     progress_percent=100, unblock_state=NULL,
--     result_summary='Caso entregue à equipe da corretora — a parte automática do acionamento terminou aqui.'
--    WHERE id='cb6478f5-33f1-46be-8a1d-18c568d2c9eb';
--   UPDATE public.work_runs SET
--     error_code='needs_human:missing_slots:problema_eletrico_opcao',
--     error_message='O acionamento precisa de uma pessoa da corretora para continuar.'
--    WHERE id='448d3f08-495d-4ee6-b3c4-77f7c89a09b2';
--   COMMIT;
-- ============================================================================
