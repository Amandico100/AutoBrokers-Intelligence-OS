-- ============================================================================
-- MIGRATION: a_carta_diz_que_pergunta_responde
-- SPEC:      SPEC-072 — Bloco 6 (a coluna `faceta`)
-- AUTOR:     execução SPEC-072            DATA: 2026-08-16
-- OBJETIVO:  dar lugar durável ao rótulo que hoje só existe dentro de um índice
--
-- APPLY:     coluna `faceta text` + índice parcial + COMMENT nela e em `temas`
-- VERIFY:    (SQL executável, no fim deste arquivo)
-- ROLLBACK:  (SQL executável, no fim deste arquivo)
--
-- EXPAND-FIRST: sim — a coluna nasce NULL e nenhum leitor a exige
-- DESTRUTIVA:   não
-- ============================================================================
--
-- 🔴 O ARGUMENTO MUDOU, E ISSO IMPORTA MAIS QUE A COLUNA
-- ----------------------------------------------------------------------------
-- A SPEC-072 abria dizendo que a coluna faria o agente filtrar por
-- `faceta='documento'`. **Isso era falso, e continuaria falso depois desta
-- migration:** a busca em runtime nunca lê `knowledge_cards`. Ela lê o Qdrant
-- (`search_service.py` → `knowledge_scope.py` → `qdrant_service.py`); todos os
-- `.table("knowledge_cards")` de `backend/app/` são administração ou curadoria.
--
-- O argumento verdadeiro é outro e é mais forte: hoje a `faceta` só existe de
-- forma utilizável **dentro do payload do Qdrant**, que é índice DERIVADO E
-- RECONSTRUÍVEL (CLAUDE.md §6). Um dado de primeira classe não pode morar só
-- num índice. 📊 E a prova de que isso não é teoria: até 15/08/2026 três
-- republicadores reescreviam o ponto `card-<id>` sem a faceta, porque
-- `insert_embeddings` faz upsert de PONTO INTEIRO — uma rodada de reindexação
-- apagaria o rótulo de 5.394 cartas de acervo.
--
-- Esta coluna é o lugar de onde ele volta.
--
-- ⚠️ ANTES DO BACKFILL: RECONCILIAR `faceta` × `temas`
-- ----------------------------------------------------------------------------
-- 📊 Das 380 cartas com `faceta='documento'`, só **201 (53%)** têm o tema
-- `documentacao`, e **673** cartas de acervo têm o tema sem ter a faceta. São
-- dois rótulos para perguntas diferentes, discordando em quase metade dos
-- casos. Preencher a coluna antes de reconciliar faz a coluna nascer mentindo.
--
-- Por isso esta migration NÃO preenche nada. Ela abre o lugar.
-- ============================================================================

ALTER TABLE public.knowledge_cards
    ADD COLUMN IF NOT EXISTS faceta text;

-- Índice PARCIAL: 📊 a esmagadora maioria das 17.928 cartas publicadas nasce de
-- conversa e nunca terá faceta. Indexar os NULLs seria pagar por linha que
-- nenhuma consulta procura.
CREATE INDEX IF NOT EXISTS ix_cards_faceta
    ON public.knowledge_cards (faceta)
    WHERE faceta IS NOT NULL;

COMMENT ON COLUMN public.knowledge_cards.faceta IS
    'Qual das 8 perguntas do contrato esta carta responde: escopo, exclusao, '
    'limite, franquia, prazo, documento, definicao, carencia. '
    'DIFERE de `temas` (assunto do atendimento, ex. cobranca_boleto) e de '
    '`category` (classe do destilador). '
    'SPEC-070 §5.1: null passa em todo filtro e NUNCA elimina — o rotulo da '
    'cota e prioridade, nao corte. Ver SPEC-072 Bloco 1 e P-178.';

-- 🔴 E O COMMENT DE `temas` ESTAVA MENTINDO — P-179.
-- `20260815_02_a_carta_ganha_tema.sql` listou 13 valores e **`documentacao` nao
-- estava entre eles** — o tema com 📊 2.786 cartas publicadas, o unico que a
-- SPEC-072 usa. Quem conferisse a documentacao autoritativa da coluna concluiria
-- que ele e ilegal.
-- Nao se conserta editando a migration aplicada (MIGRATIONS-AUTHORITY §8.8:
-- "corrigir sempre com migration nova"). Corrige-se aqui.
COMMENT ON COLUMN public.knowledge_cards.temas IS
    'Assunto(s) do atendimento. 24 valores medidos em 16/08/2026: '
    'cobranca_boleto, endosso, documentacao, prazo, regulacao, vistoria, '
    'reparo_oficina, sinistro_abertura, residencia, terceiro, franquia, '
    'indenizacao, reembolso, renovacao, pecas, boletim_ocorrencia, vidros, '
    'guincho, carro_reserva, roubo_furto, perda_total, chaveiro, funilaria, '
    'pneu. DIFERE de `ramo` (qual seguro), de `category` (classe do '
    'destilador) e de `faceta` (qual pergunta do contrato). '
    'Corrige o COMMENT de 20260815_02, que omitia `documentacao` (P-179).';

-- ============================================================================
-- VERIFY — rode DEPOIS do APPLY. Tudo read-only.
-- ============================================================================
-- 1) a coluna existe e e text
--    SELECT column_name, data_type FROM information_schema.columns
--     WHERE table_name = 'knowledge_cards' AND column_name = 'faceta';
--    -- esperado: faceta | text
--
-- 2) o indice parcial existe
--    SELECT indexname, indexdef FROM pg_indexes
--     WHERE tablename = 'knowledge_cards' AND indexname = 'ix_cards_faceta';
--    -- esperado: ... WHERE (faceta IS NOT NULL)
--
-- 3) nasceu vazia — expand-first
--    SELECT count(*) AS com_faceta FROM public.knowledge_cards
--     WHERE faceta IS NOT NULL;
--    -- esperado: 0
--
-- 4) nada foi tocado
--    SELECT count(*) FROM public.knowledge_cards;
--    -- esperado: 18.621 (ou o total do dia)
--
-- 5) os dois COMMENT estao la
--    SELECT column_name, col_description('public.knowledge_cards'::regclass,
--             ordinal_position) AS comentario
--      FROM information_schema.columns
--     WHERE table_name = 'knowledge_cards' AND column_name IN ('faceta','temas');
--    -- esperado: os dois nao-nulos, e o de `temas` citando `documentacao`
--
-- ============================================================================
-- ROLLBACK — escrito ANTES de aplicar
-- ============================================================================
-- DROP INDEX IF EXISTS public.ix_cards_faceta;
-- ALTER TABLE public.knowledge_cards DROP COLUMN IF EXISTS faceta;
-- -- o COMMENT de `temas` volta ao anterior:
-- COMMENT ON COLUMN public.knowledge_cards.temas IS
--     'Assunto(s) do atendimento — ver 20260815_02_a_carta_ganha_tema.sql';
--
-- ⚠️ O rollback e seguro em qualquer momento ANTES do backfill: a coluna nasce
-- NULL e nenhum codigo a exige. Depois do backfill, derruba-la perde o trabalho
-- de rotulagem — mas nao perde a `faceta`, que continua em `pii_check` e no
-- payload do Qdrant.
-- ============================================================================
