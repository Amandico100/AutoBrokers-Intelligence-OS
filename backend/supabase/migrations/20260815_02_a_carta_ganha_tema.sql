-- ===========================================================================
-- LEVA 5 · O ATIVO DA NOITE — a carta ganha TEMA
-- ===========================================================================
--
-- 📊 O QUE ESTA MIGRATION EXISTE PARA GUARDAR:
--
-- Uma noite de destilação com 22 subagentes e 4 juízes produziu 1.527 fatos
-- sobre 1.780 conversas. Um juiz comparativo mediu o resultado contra a
-- destilação que já existia sobre AS MESMAS conversas e o veredito foi:
--
--     substituir  ->  +336 inéditas  −596 sem equivalente  =  −260 cartas
--     qualidade cega:  antiga 16 × nova 9
--
-- **A redestilação não melhora o RAG.** O que sobrou de valor real, e é muito,
-- são os **1.400 rótulos de tema** — que a destilação antiga não tem, e que
-- `knowledge_cards` não tem onde guardar.
--
-- ---------------------------------------------------------------------------
-- POR QUE TEMA, E POR QUE ARRAY
-- ---------------------------------------------------------------------------
-- 📊 Medido pelo juiz de taxonomia sobre os 1.581 fatos:
--
--     31,3% dos fatos (495) pertencem a DOIS OU MAIS temas
--     380 casam 2 · 105 casam 3 · 10 casam 4+
--
-- Um campo de valor único **não guarda essa informação**, por mais valores que
-- se acrescente ao enum. E a prova é aritmética: mover os 48 registros de carro
-- reserva que estão fora do balde `outro` recuperaria 62 fatos do tema e
-- tiraria 60 colaterais do balde certo. Ganho líquido: 2. Soma zero.
--
-- Por isso `text[]`, e não uma coluna `tema text`.
--
-- ---------------------------------------------------------------------------
-- O QUE ISTO CONSERTA — medido com perguntas de segurado real
-- ---------------------------------------------------------------------------
-- 📊 "Tenho direito a carro reserva?" tem 156 fatos no acervo. O maior balde
-- do tema é `servico: "outro"`, com 37% de pureza. **Nenhum agente filtra por
-- `outro`** — é, por definição, o balde do que não se soube nomear. O recall
-- real dessa pergunta hoje é ZERO, e três destiladores relataram, sem se
-- falar, que "são as cartas mais difíceis de achar do meu conjunto".
--
-- Os 13 temas, com a massa de cada um:
--
--     reparo_oficina 465 · vistoria 246 · pecas 229 · terceiro 192
--     franquia 159 · carro_reserva 156 · indenizacao 111 · reembolso 69
--     perda_total 67 · boletim_ocorrencia 61 · funilaria 33
--     regulacao 25 · endosso 19
--
-- ---------------------------------------------------------------------------
-- APPLY / VERIFY / ROLLBACK
-- ---------------------------------------------------------------------------
-- APPLY:  coluna `temas text[]` + índice GIN (é o índice de array; um B-tree
--         não responde "contém este tema").
--
-- VERIFY: SELECT column_name, data_type FROM information_schema.columns
--          WHERE table_name='knowledge_cards' AND column_name='temas';
--          -- 1 linha, ARRAY
--
--         SELECT count(*) FROM pg_indexes
--          WHERE tablename='knowledge_cards' AND indexname='ix_cards_temas';
--          -- 1
--
--         SELECT count(*) FROM knowledge_cards WHERE temas IS NOT NULL;
--          -- 0 — esta migration NAO preenche nada
--
-- ROLLBACK: DROP INDEX IF EXISTS public.ix_cards_temas;
--           ALTER TABLE public.knowledge_cards DROP COLUMN IF EXISTS temas;
--           Sem perda: nenhuma linha é escrita aqui.
--
-- ⚠️ EXPAND-FIRST: a coluna nasce NULL e nada no produto a lê ainda. Aplicar
-- esta migration não muda comportamento nenhum — é a porta, não a mudança.
-- O backfill dos 1.400 rótulos é passo separado, e reversível.
-- ===========================================================================

ALTER TABLE public.knowledge_cards
    ADD COLUMN IF NOT EXISTS temas text[];

-- GIN, e não B-tree: a pergunta é "esta carta CONTÉM o tema X", que num array
-- é o operador `&&`/`@>`. B-tree indexaria o array inteiro como valor único e
-- não responderia nada útil.
CREATE INDEX IF NOT EXISTS ix_cards_temas
    ON public.knowledge_cards USING GIN (temas)
    WHERE temas IS NOT NULL;

COMMENT ON COLUMN public.knowledge_cards.temas IS
    'Sobre o que a carta ENSINA — multivalorado de propósito. 📊 31,3% dos '
    'fatos pertencem a 2+ temas, e um campo único não guarda isso. Difere de '
    '`ramo` (qual seguro) e de `category`/servico (que serviço foi acionado): '
    'temas responde a pergunta que o segurado faz. Valores medidos: '
    'reparo_oficina, vistoria, pecas, terceiro, franquia, carro_reserva, '
    'indenizacao, reembolso, perda_total, boletim_ocorrencia, funilaria, '
    'regulacao, endosso.';
