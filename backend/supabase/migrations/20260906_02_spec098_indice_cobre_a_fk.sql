-- =============================================================
-- MIGRATION: spec098_indice_cobre_a_fk
-- SPEC:      SPEC-098 — U5.a (correção medida da 20260906_01)
-- AUTOR:     execução Opus 5 — builder B      DATA: 2026-09-06
-- OBJETIVO:  o índice das duas colunas de conversa passa a COBRIR a FK que a
--            migration 01 criou — a ordem das colunas estava invertida para
--            esse fim.
--
-- APPLY:     cria `ix_artifacts_conversa_fk` e `ix_approval_requests_conversa_fk`
--            com `(conversation_id, company_id)` (parciais) e DERRUBA os dois
--            índices `(company_id, conversation_id)` que a 01 criou minutos antes.
-- VERIFY:    o bloco VERIFY no fim deste arquivo.
-- ROLLBACK:  o bloco ROLLBACK no fim deste arquivo.
--
-- EXPAND-FIRST: sim  (cria os novos ANTES de derrubar os velhos, no mesmo
--               arquivo mas em blocos separados e nesta ordem)
-- DESTRUTIVA:   não  (índice derrubado é reconstruível a partir do arquivo; o
--               ROLLBACK o recria; nenhum dado é tocado)
-- =============================================================
--
-- 🔴 POR QUE ESTA MIGRATION EXISTE, E POR QUE NÃO EDITEI A 01
--
-- MIGRATIONS-AUTHORITY §8.8: *"Alterar migration já aplicada. Corrigir sempre
-- com migration nova."* A 01 foi aplicada em 06/09/2026 e VERIFICADA. O arquivo
-- dela fica como está, com o índice que ela realmente criou — o histórico não
-- se reescreve.
--
-- 📊 A RAZÃO, MEDIDA logo depois do APPLY da 01 (`get_advisors performance`):
--
--     INFO unindexed_foreign_keys
--       `public.artifacts` tem FK `fk_artifacts_conversa` SEM índice de cobertura
--       `public.approval_requests` tem FK `fk_approval_requests_conversa` idem
--
-- ⚠️ **`(company_id, conversation_id)` NÃO cobre a FK.** O Postgres usa o índice
-- pela COLUNA LÍDER, e quem apaga uma conversa procura por `conversation_id` —
-- sem `company_id` na mão. Com a coluna líder errada, todo `DELETE` de conversa
-- vira varredura sequencial de `artifacts` e de `approval_requests`.
--
-- 🔴 E a ordem nova serve às DUAS perguntas, não só à FK. CLAUDE.md §7 manda
-- `company_id` primeiro *"porque é ela que corta o volume"* — e aqui isso deixa
-- de valer: 📊 06/09/2026, `companies` = 3 e `conversations` = 728. Num índice
-- PARCIAL (`WHERE conversation_id IS NOT NULL`), `conversation_id` é ~240× mais
-- seletivo que a corretora, e a única leitura do produto é *"as peças DESTA
-- conversa"* — que traz as duas colunas juntas de qualquer jeito. §7 continua
-- garantido pela FK COMPOSTA e pelo filtro no repositório; ele nunca dependeu da
-- ordem deste índice.
--
-- ⚠️ Isto é uma correção de DESENHO medida, não uma remoção por advisor
-- `unused_index` — MIGRATIONS-AUTHORITY §8.7 proíbe a segunda, e ela não é o
-- caso: os dois novos nascem tão "não usados" quanto os velhos (📊 0 de 143
-- peças e 0 de 10 aprovações têm conversa hoje). O que muda é a coluna líder.
--
-- =============================================================
-- APPLY
-- =============================================================

-- ① os NOVOS primeiro (expand-first): a coluna da conversa lidera.
CREATE INDEX IF NOT EXISTS ix_artifacts_conversa_fk
  ON public.artifacts (conversation_id, company_id)
  WHERE conversation_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_approval_requests_conversa_fk
  ON public.approval_requests (conversation_id, company_id)
  WHERE conversation_id IS NOT NULL;

-- ② só então os velhos saem — dois índices sobre as mesmas duas colunas seriam
--    escrita duplicada em todo INSERT de peça, sem leitura que os dois sirvam.
DROP INDEX IF EXISTS public.ix_artifacts_conversa;
DROP INDEX IF EXISTS public.ix_approval_requests_conversa;

-- =============================================================
-- VERIFY  (read-only)
-- =============================================================
--
-- V1 · os dois novos existem com a coluna líder certa, e os dois velhos sumiram
--
--   select indexname, indexdef from pg_indexes
--    where schemaname='public'
--      and indexname in ('ix_artifacts_conversa','ix_approval_requests_conversa',
--                        'ix_artifacts_conversa_fk','ix_approval_requests_conversa_fk');
--   -- esperado: 2 linhas, ambas terminando em `_fk`, ambas com
--   --   (conversation_id, company_id) WHERE (conversation_id IS NOT NULL)
--
-- V2 · 🔴 O CONTROLE — as FKs continuam de pé e continuam COMPOSTAS. Derrubar
--      índice não pode ter derrubado constraint junto.
--
--   select conname, pg_get_constraintdef(oid)
--     from pg_constraint
--    where conname in ('fk_artifacts_conversa','fk_approval_requests_conversa');
--   -- esperado: 2 linhas, ambas FOREIGN KEY (conversation_id, company_id)
--
-- V3 · e o advisor cala: `get_advisors performance` não traz mais
--      `unindexed_foreign_keys` para `fk_artifacts_conversa` nem para
--      `fk_approval_requests_conversa`.
--
-- =============================================================
-- ROLLBACK
-- =============================================================
--
--   create index if not exists ix_artifacts_conversa
--     on public.artifacts (company_id, conversation_id)
--     where conversation_id is not null;
--   create index if not exists ix_approval_requests_conversa
--     on public.approval_requests (company_id, conversation_id)
--     where conversation_id is not null;
--   drop index if exists public.ix_approval_requests_conversa_fk;
--   drop index if exists public.ix_artifacts_conversa_fk;
