-- SPEC-063 Bloco E — o acionamento para de morar só no Redis.
--
-- O PROBLEMA (medido em 03/08/2026)
-- ---------------------------------
-- 📊 `grep -c "work_run" backend/app/services/insurer_dispatch_service.py` → 0.
--
-- A máquina de estados do acionamento — a ÚNICA máquina de estados real do
-- produto — existia inteira em `dispatch:active:{company_id}:{digits}` no Redis,
-- TTL de 6h (24h em `monitoring`), com fallback para um dict de processo quando
-- o Redis não responde.
--
--     preparing → ready_to_send → [portão] → ura → human_phase → captured
--          └──────────────── needs_human ←──────────┘             → monitoring
--
-- Um restart do Redis, ou seis horas de silêncio, perdiam um acionamento EM VOO.
-- E não havia reconciliação nenhuma: um segurado com o guincho a caminho ficava
-- órfão e ninguém percebia. O Vigia (`dispatch_watchdog`) é cego para isso por
-- construção — ele varre as sessões que ESTÃO no Redis.
--
-- Viola CLAUDE.md §6 (Supabase = verdade operacional durável; Redis = fila,
-- lock, lease, cache) e a SPEC-055 (Work Run = execução universal).
--
-- POR QUE ESTA MIGRATION É TÃO PEQUENA
-- -------------------------------------
-- **Porque nenhuma tabela nova foi criada, de propósito.**
--
-- O acionamento passou a ser um Work Run (SPEC-055): `work_runs` para o estado,
-- `work_steps` para o checkpoint de cada fase, `work_events` para a linha do
-- tempo. Tudo isso já existe e já é lido pelo Control Plane (SPEC-061).
--
-- 📊 A alternativa — uma tabela de estado própria para o acionamento — já foi
-- tentada e morreu: `corridor_runs` tem 50 execuções abandonadas, todas em
-- `active`, e hoje mora no schema `graveyard`. CLAUDE.md §5 proíbe repetir isso.
--
-- Sobra exatamente uma coisa para o SQL: fazer a varredura de reconciliação
-- barata. Ela roda no boot e pergunta "quais acionamentos o banco diz que estão
-- em voo?" — filtrando por `workflow_key` e por status não-terminal. 📊 Hoje
-- `work_runs` tem 724 linhas, 562 delas de `intelligence.detect_signals` em dois
-- meses; sem índice parcial essa pergunta vira varredura sequencial no ano que
-- vem, e o boot fica mais lento quanto mais o produto trabalha.
--
-- Nada aqui é pré-requisito do código: sem este índice a reconciliação funciona
-- igual, só mais cara. Expand puro, zero risco de contract.
--
-- APPLY    o CREATE INDEX CONCURRENTLY abaixo + os dois COMMENT.
--          `CONCURRENTLY` **não roda dentro de transação** — aplicar avulso,
--          fora de bloco BEGIN/COMMIT.
-- VERIFY   -- 1. o índice existe e é o parcial certo
--          SELECT indexname, indexdef FROM pg_indexes
--           WHERE schemaname='public' AND tablename='work_runs'
--             AND indexname='idx_work_runs_acionamento_em_voo';
--          -- 2. o planejador realmente o usa na pergunta da reconciliação
--          EXPLAIN SELECT id, company_id, current_step_key, input_payload
--            FROM work_runs
--           WHERE workflow_key = 'acionamento.seguradora'
--             AND status NOT IN ('completed','failed','cancelled','expired')
--           ORDER BY created_at DESC LIMIT 50;
--          -- 3. quantos acionamentos duráveis já existem (0 antes do 1º deploy)
--          SELECT status, count(*) FROM work_runs
--           WHERE workflow_key='acionamento.seguradora' GROUP BY 1;
-- ROLLBACK DROP INDEX CONCURRENTLY IF EXISTS public.idx_work_runs_acionamento_em_voo;
--          COMMENT ON INDEX ... deixa de existir junto com o índice.
--          Nenhum dado é tocado: não há CREATE, ALTER de coluna, nem UPDATE.

-- A pergunta da reconciliação de boot, respondida por um índice do tamanho do
-- problema: só os acionamentos, só os que ainda não terminaram.
--
-- `runtime_kind = 'acionamento'` (e não o padrão 'smith') marca estes runs como
-- executados por FORA do Smith Worker: quem os move é o inbound do WhatsApp,
-- mensagem por mensagem. Eles não têm lease e nunca entram no outbox — por isso
-- `WorkRunService.recuperar_orfaos()` não os alcança (ele exige
-- `lease_expires_at < now()`, e lease nula não satisfaz o filtro).
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_work_runs_acionamento_em_voo
    ON public.work_runs (company_id, created_at DESC)
 WHERE workflow_key = 'acionamento.seguradora'
   AND status NOT IN ('completed', 'failed', 'cancelled', 'expired');

COMMENT ON INDEX public.idx_work_runs_acionamento_em_voo IS
  'SPEC-063 E — sustenta a reconciliacao de acionamentos orfaos no boot: '
  'acha em O(log n) os acionamentos que o banco diz EM VOO para comparar com o '
  'cache do Redis. Sem ele a varredura le a tabela inteira, que cresce com todo '
  'trabalho do produto (562 runs de intelligence.detect_signals em 2 meses).';

COMMENT ON COLUMN public.work_runs.runtime_kind IS
  'Quem MOVE este run. "smith" (padrao) = Smith Worker, via outbox + fila + '
  'lease. "acionamento" (SPEC-063 E) = o run e movido pelo inbound do WhatsApp '
  'da seguradora, fase por fase, ao longo de horas; nasce sem linha de outbox '
  'de proposito, porque enfileira-lo faria o worker marca-lo failed com '
  '"workflow_desconhecido" enquanto o acionamento esta VIVO. Mesma tabela, '
  'mesmo enum de status, mesma linha do tempo — o que muda e o executor.';
