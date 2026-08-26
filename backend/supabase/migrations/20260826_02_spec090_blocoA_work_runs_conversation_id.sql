-- =============================================================
-- MIGRATION: spec090_blocoA_work_runs_conversation_id
-- SPEC:      SPEC-090 — BLOCO A (a chave de junção)
-- AUTOR:     execução Opus 5             DATA: 2026-08-26
-- OBJETIVO:  o acionamento passa a saber DE QUAL CONVERSA ele nasceu — e o
--            banco recusa a conversa de outra corretora.
--
-- APPLY:     `work_runs` ganha `conversation_id` (nulo permitido) e uma FK
--            COMPOSTA `(conversation_id, company_id)`.
-- VERIFY:    o bloco VERIFY no fim deste arquivo (SQL executável).
-- ROLLBACK:  o bloco ROLLBACK no fim deste arquivo.
--
-- EXPAND-FIRST: sim  (só adiciona coluna e constraints)
-- DESTRUTIVA:   não
-- =============================================================
--
-- 🔴 O QUE A MEDIÇÃO DE 26/08/2026 DERRUBOU DA PRÓPRIA SPEC
--
-- A SPEC abre dizendo que **as três ilhas não se falam**:
--
--     attendance_transcripts .... 152.300 com session_id
--        que casam com conversations.id ................. 0
--        que casam com observed_sessions.id ............. 0
--
-- 📊 Os dois zeros estão certos. ⚠️ **E são irrelevantes** — a SPEC testou
-- contra duas tabelas que nunca foram o alvo. Medido no mesmo banco:
--
--     session_id casa `attendance_sessions.id` .......... 95 de 95   100,0%
--     (company_id, counterparty) casa `conversations`
--       por (company_id, user_phone) .................... 63 de 63   100,0%
--
-- 🔴 **A camada de resolução de identidade que a SPEC diz faltar já existe.**
-- O transcript tem casa (`attendance_sessions`, 12.586 linhas) e tem telefone,
-- e o telefone junta com a conversa por igualdade simples de duas colunas.
--
-- ⛔ Então esta migration **não** cria ponte para transcript. Criar seria motor
-- paralelo (`CLAUDE.md` §5) sobre uma junção que já fecha em 100%.
--
-- 📊 O QUE FALTA DE VERDADE, e é só isto:
--
--     work_runs .................. 2.778 linhas, NENHUMA coluna de conversa
--       `acionamento.seguradora` ....... 4   (0,1%)  🔴 o único com conversa
--       jobs de inteligência ....... 2.774   (99,9%) não têm conversa nenhuma
--
-- ⚠️ **E o backfill que a SPEC orça como o trabalho que domina as ~4h tem
-- QUATRO LINHAS de alvo.** O valor desta coluna é o FUTURO: a partir do
-- piloto, todo acionamento nasce sabendo de qual conversa veio.
--
-- ✅ E o dado já está na mão de quem cria o run: `dispatch_mirror.py:55-60`
-- grava `session["mirror_conversation_id"]`. A SPEC acertou em cheio nisto —
-- *"escrito por quem CRIA o run — o dispatch já tem a conversa na mão"*.
--
-- ---------------------------------------------------------------------------
-- 🔴 A FK É COMPOSTA, E ESSE É O PONTO DESTA MIGRATION
-- ---------------------------------------------------------------------------
--
-- Uma FK simples `conversation_id → conversations(id)` prova que a conversa
-- EXISTE. ⛔ Não prova que ela é **da mesma corretora**.
--
-- `CLAUDE.md` §7: o backend usa service role e atravessa a RLS inteira. A
-- única proteção real é o filtro no código — e um filtro é uma linha que
-- alguém pode esquecer numa refatoração de terça-feira.
--
-- 🔴 A FK composta `(conversation_id, company_id) → conversations(id, company_id)`
-- transforma o isolamento em **constraint do banco**: um run da Resulta
-- apontando para conversa da AutoFleet é um INSERT que o Postgres RECUSA,
-- com o filtro do código certo ou errado.
--
-- ⚠️ E ela custa quase nada: `conversations.id` já é PK, então
-- `UNIQUE (id, company_id)` é trivialmente satisfeita pelos dados existentes —
-- é um índice a mais, não uma mudança de significado.
--
-- ⛔ **E o código NÃO passa a depender dela para não quebrar.** O escritor
-- valida a corretora ANTES de gravar e, na dúvida, grava NULO. A FK é a
-- segunda linha de defesa, não a primeira: se ela for quem recusa, o
-- acionamento inteiro morreria por causa de uma coluna de relatório.
--
-- =============================================================
-- APPLY
-- =============================================================

-- ① a coluna. NULA É VALOR LEGÍTIMO, e não é exceção: 📊 99,9% dos runs são
--    jobs de inteligência que não nascem de conversa nenhuma.
ALTER TABLE public.work_runs
  ADD COLUMN IF NOT EXISTS conversation_id uuid;

COMMENT ON COLUMN public.work_runs.conversation_id IS
  'SPEC-090 BLOCO A — de qual conversa este run nasceu. NULO é legítimo: '
  '📊 99,9% dos runs são jobs de inteligência sem conversa. ⛔ NULO também é '
  'a resposta honesta quando a ligação não pôde ser PROVADA: um '
  'conversation_id errado produz relatório confiante e falso.';

-- ② o alvo da FK composta. `id` já é PK, então esta UNIQUE não muda nada nos
--    dados — ela só dá ao Postgres o índice que a FK composta exige.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conname = 'uq_conversations_id_company'
       AND conrelid = 'public.conversations'::regclass
  ) THEN
    ALTER TABLE public.conversations
      ADD CONSTRAINT uq_conversations_id_company UNIQUE (id, company_id);
  END IF;
END $$;

-- ③ 🔴 A FK COMPOSTA — o isolamento entre corretoras vira constraint.
--
--    ON DELETE SET NULL: apagar a conversa não pode apagar o histórico do
--    trabalho. O run continua existindo; o que se perde é o ponteiro, e isso
--    é exatamente o que NULO significa nesta coluna.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conname = 'fk_work_runs_conversation_mesma_corretora'
       AND conrelid = 'public.work_runs'::regclass
  ) THEN
    ALTER TABLE public.work_runs
      ADD CONSTRAINT fk_work_runs_conversation_mesma_corretora
      FOREIGN KEY (conversation_id, company_id)
      REFERENCES public.conversations (id, company_id)
      ON DELETE SET NULL;
  END IF;
END $$;

-- ④ o índice da leitura do BLOCO D: "os runs desta conversa".
--    PARCIAL — 📊 99,9% das linhas são NULAS e não precisam entrar no índice.
CREATE INDEX IF NOT EXISTS ix_work_runs_conversa
  ON public.work_runs (company_id, conversation_id)
  WHERE conversation_id IS NOT NULL;

-- =============================================================
-- VERIFY  (read-only, e o CONTROLE desfaz o que escreve)
-- =============================================================
--
-- V1 · a coluna existe e aceita NULO
--
--   select column_name, data_type, is_nullable
--     from information_schema.columns
--    where table_name = 'work_runs' and column_name = 'conversation_id';
--   -- esperado: conversation_id | uuid | YES
--
-- V2 · as duas constraints existem
--
--   select conname, contype, pg_get_constraintdef(oid)
--     from pg_constraint
--    where conname in ('uq_conversations_id_company',
--                      'fk_work_runs_conversation_mesma_corretora');
--   -- esperado: 2 linhas, contype 'u' e 'f'
--
-- V3 · 🔴 O CONTROLE — o banco RECUSA conversa de outra corretora?
--      ⚠️ A transação é desfeita por `raise` no fim: nada fica gravado.
--
--   do $$
--   declare
--     v_a uuid; v_b uuid; v_conv_b uuid; v_recusou boolean := false;
--   begin
--     select id into v_a from companies order by created_at limit 1;
--     select id into v_b from companies where id <> v_a order by created_at limit 1;
--     select id into v_conv_b from conversations where company_id = v_b limit 1;
--     if v_conv_b is null then raise notice 'sem conversa na 2a corretora'; end if;
--
--     begin
--       insert into work_runs (id, company_id, conversation_id, source_type,
--                              outcome_type, status, risk_level, runtime_kind,
--                              workflow_key, workflow_version, thread_id)
--       values (gen_random_uuid(), v_a, v_conv_b, 'chat', 'teste', 'draft',
--               'low', 'acionamento', 'teste.controle', '1.0.0', 'work:controle');
--     exception when foreign_key_violation then
--       v_recusou := true;
--     end;
--
--     raise exception 'CONTROLE — cross-tenant recusado? %', v_recusou;
--   end $$;
--   -- esperado: ERROR:  CONTROLE — cross-tenant recusado? t
--
-- V4 · quantos runs têm ligação (depois do backfill)
--
--   select workflow_key,
--          count(*) total,
--          count(conversation_id) ligados,
--          count(*) - count(conversation_id) nulos
--     from work_runs
--    group by 1 order by 2 desc;
--
-- =============================================================
-- ROLLBACK
-- =============================================================
--
--   drop index if exists public.ix_work_runs_conversa;
--   alter table public.work_runs
--     drop constraint if exists fk_work_runs_conversation_mesma_corretora;
--   alter table public.conversations
--     drop constraint if exists uq_conversations_id_company;
--   alter table public.work_runs drop column if exists conversation_id;
--
-- ⚠️ Derrubar a coluna apaga as ligações já gravadas. O backfill as
-- reconstrói (é determinístico), mas as gravadas NO ATO por acionamentos
-- novos não voltam: o `mirror_conversation_id` vive na sessão, não no banco.
