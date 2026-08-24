-- SPEC-085 · FASE 0 — O TRAVAMENTO VIRA LINHA DE BANCO
-- ============================================================================
-- 24/08/2026 · branch feat/spec085-o-destravamento-nao-trava-em-silencio
--
-- POR QUE ESTA MIGRATION É PEQUENA
-- ================================
-- 📊 Medido em 24/08/2026, antes de escrever uma linha: a linha durável do
-- travamento **já existe em parte**. O `work_runs` do acionamento
-- `cb6478f5` carrega `error_code = 'needs_human:sentinela_stall'` — o motivo
-- COMPLETO — e o `work_steps` da fase guarda `state`, `reason`,
-- `missing_slots`, `slots`, `transcript` e `mirror_conversation_id`.
--
--     select string_agg(distinct k, ', ')
--       from work_steps s, jsonb_object_keys(s.output_summary) k
--      where s.work_run_id in (select id from work_runs
--                               where runtime_kind='acionamento');
--
-- 🔴 O que falta NÃO é a linha. É:
--   (a) uma amostra que uma PESSOA possa ler sem receber CPF  → output_redacted
--   (b) o desfecho do destravamento                            → unblock_state
--   (c) policy por corretora nas tabelas que guardam isso      → CLAUDE.md §7
--
-- POR QUE `work_runs`/`work_steps`, E NÃO TABELA NOVA NEM `human_review_tasks`
-- ===========================================================================
-- `CLAUDE.md` §5 proíbe criar executor em paralelo, e a SPEC-055 já define o
-- Work Run como a execução universal. O acionamento já mora lá.
--
-- ⚠️ E `human_review_tasks` foi considerada e RECUSADA com medição:
-- 📊 a SPEC-085 §F0.1 (e a P-225) dizem que ela "não tem escritor". **Tem** —
-- `app/services/evals/juiz_llm.py:196` insere nela quando o juiz de eval fica
-- sem confiança. Zero linhas porque nunca disparou, não porque falta escritor.
-- E a forma dela é de EVAL: `veredito boolean` ("o juiz acertou?") e
-- `amostra NOT NULL`. Travamento não tem veredito booleano; tem desfecho de
-- cinco estados. Dois produtores sem relação na mesma tabela não é
-- consolidação, é colisão.
--
-- 🔴 A ESCOLHA QUE PROTEGE A FASE 1
-- =================================
-- `work_steps.output_summary` **é o payload de restauração da sessão**:
--
--     snapshot_duravel → output_summary → _ultimo_retrato → sessao_restaurada
--     → _gravar_no_redis → session["slots"] → render_reply → A URA
--
-- Mascarar ALI faz um acionamento restaurado responder `###.###.###-##` à
-- seguradora. Por isso a coluna nova é um **GÊMEO**, nunca um substituto —
-- é literalmente a saída (i) da §F1.2 da SPEC, e ela cabe no schema sem
-- inventar nada.
--
-- ============================================================================
-- APPLY    este arquivo, inteiro. Idempotente: rodar duas vezes é inócuo.
-- VERIFY   o bloco VERIFY no fim deste arquivo (SELECTs, sem efeito).
-- ROLLBACK o bloco ROLLBACK no fim deste arquivo.
-- ============================================================================
--
-- ⚠️ EXPAND-FIRST. Nada é renomeado, nada é apagado, nenhuma coluna existente
-- muda de tipo ou de nulidade. Todo leitor de hoje continua lendo o mesmo.
--
-- ⚠️ ÍNDICE SEM `CONCURRENTLY`, DE PROPÓSITO. 📊 `work_runs` tem 2.632 linhas;
-- o `ACCESS EXCLUSIVE` de um índice parcial não-único aqui dura milissegundos.
-- `CONCURRENTLY` não roda dentro de transação — e a P-35 é exatamente uma
-- migration que ficou ESCRITA E NÃO APLICADA por causa disso. Um índice que
-- não entra protege menos que um lock de milissegundos.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. O GÊMEO MASCARADO — leitura humana, nunca restauração
-- ---------------------------------------------------------------------------
ALTER TABLE public.work_steps
    ADD COLUMN IF NOT EXISTS output_redacted jsonb;

COMMENT ON COLUMN public.work_steps.output_redacted IS
    'SPEC-085 F1.2(i) — retrato do passo com PII mascarada, para leitura '
    'humana e auditoria. NUNCA é lido pela restauração da sessão: quem '
    'restaura lê output_summary. Mascarar output_summary faria um acionamento '
    'restaurado responder a máscara à seguradora.';

-- ---------------------------------------------------------------------------
-- 2. O DESFECHO DO DESTRAVAMENTO
-- ---------------------------------------------------------------------------
-- 🔴 Por que uma coluna, e não derivar de `status` + `owner_user_id`:
-- derivar obriga TODO leitor a reescrever a mesma regra de quatro ramos, e o
-- `CLAUDE.md` §9.3 já ensinou o custo disso — "duas listas que precisam
-- concordar e são escritas separado divergem". Uma coluna, um escritor.
--
-- ⚠️ NULL é o estado normal: um run que nunca travou não tem desfecho de
-- destravamento. É a LINHA DE CONTROLE da §F0.3 item 2 escrita no schema —
-- se tudo tivesse valor, a coluna não mediria travamento, mediria existência.
ALTER TABLE public.work_runs
    ADD COLUMN IF NOT EXISTS unblock_state text;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'work_runs_unblock_state_check'
    ) THEN
        ALTER TABLE public.work_runs
            ADD CONSTRAINT work_runs_unblock_state_check
            CHECK (unblock_state IS NULL OR unblock_state IN (
                'travado',              -- o robô parou e ninguém assumiu ainda
                'retomado_pelo_robo',   -- a retomada automática pegou (BLOCO D)
                'assumido_por_humano',  -- uma pessoa clicou ASSUMIR (BLOCO E)
                'resolvido',            -- o atendimento fechou depois do travamento
                'abandonado'            -- arquivado com motivo escrito (BLOCO E)
            ));
    END IF;
END $$;

COMMENT ON COLUMN public.work_runs.unblock_state IS
    'SPEC-085 F0.1 — desfecho do travamento. NULL = este run nunca travou. '
    'Quem destravou vai em owner_user_id; quando, em updated_at; a linha do '
    'tempo, em work_events.';

-- ---------------------------------------------------------------------------
-- 3. O ÍNDICE DA FILA — só as linhas que travaram
-- ---------------------------------------------------------------------------
-- Parcial de propósito: 📊 hoje 4 runs de acionamento contra 2.632 no total.
-- O índice cheio pagaria por 2.628 linhas que a Fila nunca vai olhar.
CREATE INDEX IF NOT EXISTS work_runs_travamento_idx
    ON public.work_runs (company_id, unblock_state, created_at DESC)
    WHERE unblock_state IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 4. AS POLICIES — CLAUDE.md §7, e o piso da §2.4 do protocolo
-- ---------------------------------------------------------------------------
-- 📊 Medido em 24/08/2026:
--
--     work_runs    RLS ligado   policies 0
--     work_steps   RLS ligado   policies 0
--     work_events  RLS ligado   policies 0
--
-- 🔴 `CLAUDE.md` §7 é literal: "o backend usa service role: RLS sem policy não
-- protege NADA contra erro de filtro no código". E a FASE 0 passa a escrever
-- dado de travamento — com o motivo, os slots que faltaram e a tela da URA —
-- nessas três tabelas. Ampliar a escrita antes de fechar a leitura é o
-- inverso da ordem correta.
--
-- ⚠️ A DIREÇÃO DA MUDANÇA É SEGURA, E ISSO É MEDIDO, NÃO SUPOSTO: com RLS
-- ligado e ZERO policies, hoje `authenticated` e `anon` recebem ZERO linhas.
-- Toda policy aqui só pode ABRIR o que já estava fechado, nunca fechar o que
-- estava aberto. Nenhum leitor de hoje perde acesso.
--
-- ⚠️ E A FORMA É COPIADA, NÃO INVENTADA: é a mesma de
-- `human_support_destinations` (migration 20260803), que está viva em produção:
--     company_id = (SELECT u.company_id FROM users_v2 u WHERE u.id = auth.uid())
-- Inventar uma segunda maneira de escrever "esta linha é da minha corretora"
-- é criar a divergência que o §7 existe para impedir.

DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['work_runs', 'work_steps', 'work_events'] LOOP
        -- service role: o backend, que já filtra no repository
        IF NOT EXISTS (SELECT 1 FROM pg_policies
                        WHERE schemaname = 'public' AND tablename = t
                          AND policyname = t || '_service_role_all') THEN
            EXECUTE format(
                'CREATE POLICY %I ON public.%I AS PERMISSIVE FOR ALL '
                'TO service_role USING (true) WITH CHECK (true)',
                t || '_service_role_all', t);
        END IF;

        -- usuário autenticado: só a própria corretora, e só leitura
        IF NOT EXISTS (SELECT 1 FROM pg_policies
                        WHERE schemaname = 'public' AND tablename = t
                          AND policyname = t || '_company_select') THEN
            EXECUTE format(
                'CREATE POLICY %I ON public.%I AS PERMISSIVE FOR SELECT '
                'TO authenticated USING (company_id = ('
                '  SELECT u.company_id FROM public.users_v2 u WHERE u.id = auth.uid()))',
                t || '_company_select', t);
        END IF;
    END LOOP;
END $$;

COMMIT;

-- ============================================================================
-- VERIFY — roda depois do APPLY. Só SELECT; nenhum efeito.
-- ============================================================================
-- 🔴 O VERIFY CONFERE O OBJETO, NUNCA O LEDGER. `MIGRATIONS-AUTHORITY.md` e
-- 📊 a própria branch atual provam por quê: 3 migrations estão aplicadas de
-- fato e ausentes de `schema_migrations`.
--
--   -- 1. as duas colunas existem?  (espera 2 linhas)
--   select table_name, column_name, data_type
--     from information_schema.columns
--    where table_schema='public'
--      and (table_name='work_steps' and column_name='output_redacted'
--        or table_name='work_runs'  and column_name='unblock_state');
--
--   -- 2. o CHECK existe e recusa lixo?  (espera 1 linha, e o insert falha)
--   select conname from pg_constraint where conname='work_runs_unblock_state_check';
--
--   -- 3. o índice existe?  (espera 1 linha)
--   select indexname from pg_indexes
--    where schemaname='public' and indexname='work_runs_travamento_idx';
--
--   -- 4. as SEIS policies existem?  (espera 6 linhas)
--   select tablename, policyname, cmd, roles::text
--     from pg_policies
--    where schemaname='public'
--      and tablename in ('work_runs','work_steps','work_events')
--    order by tablename, policyname;
--
--   -- 5. 🔴 A LINHA DE CONTROLE: nenhum run existente foi tocado.
--   --    (espera 0 — a coluna nasce NULL para todos, inclusive os 4
--   --     acionamentos e os 2.619 runs de intelligence.*)
--   select count(*) from work_runs where unblock_state is not null;
--
-- ============================================================================
-- ROLLBACK — desfaz por completo. Nenhum dado é perdido: as duas colunas
-- nascem vazias e nada as escreve até o código da FASE 0 subir.
-- ============================================================================
--   BEGIN;
--   DO $$ DECLARE t text; BEGIN
--     FOREACH t IN ARRAY ARRAY['work_runs','work_steps','work_events'] LOOP
--       EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t||'_service_role_all', t);
--       EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t||'_company_select', t);
--     END LOOP;
--   END $$;
--   DROP INDEX IF EXISTS public.work_runs_travamento_idx;
--   ALTER TABLE public.work_runs  DROP CONSTRAINT IF EXISTS work_runs_unblock_state_check;
--   ALTER TABLE public.work_runs  DROP COLUMN IF EXISTS unblock_state;
--   ALTER TABLE public.work_steps DROP COLUMN IF EXISTS output_redacted;
--   COMMIT;
-- ============================================================================
