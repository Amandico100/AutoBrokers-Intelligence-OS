-- =============================================================
-- MIGRATION: spec086_blocoB_work_waits
-- SPEC:      SPEC-086 — BLOCO B (a espera vira objeto)
-- AUTOR:     execução Opus 5             DATA: 2026-08-26
-- OBJETIVO:  "esperando o cliente" deixa de ser indistinguível de "parado
--            porque quebrou" — e a espera vencida passa a ser varrível.
--
-- APPLY:     cria `work_waits`.
-- VERIFY:    o bloco VERIFY no fim deste arquivo (SQL executável).
-- ROLLBACK:  o bloco ROLLBACK no fim deste arquivo.
--
-- EXPAND-FIRST: sim  (só adiciona)
-- DESTRUTIVA:   não
-- =============================================================
--
-- 📊 A RAZÃO, MEDIDA EM 26/08/2026:
--
--     work_waits ................................ NÃO EXISTIA
--     work_runs presos em `queued` ..............  5
--       o mais velho ............................ 29 DIAS
--     conversa documentada presa ................ ~730 horas (handoff_watchdog.py:3)
--
-- ⚠️ **E os cinco presos não são atendimento.** 📊 Os cinco são
-- `intelligence.detect_signals` — jobs de background. Isso não os torna menos
-- reais (ninguém foi avisado em 29 dias), mas **muda a leitura**: a SPEC os usa
-- como prova de que o atendimento apodrece, e eles provam outra coisa. A prova
-- do atendimento é a conversa de 730 horas, e essa é do documento certo.
--
-- ---------------------------------------------------------------------------
-- 🔴 `work_run_id` ACEITA NULO — e é isto que faz o bloco executar
-- ---------------------------------------------------------------------------
--
-- 📊 A proposta original declarava `work_waits.work_run_id NOT NULL`. Mas
-- conversa de WhatsApp **não cria Work Run**:
--
--     work_runs de acionamento na história inteira ......   4
--     conversations ..................................... 671
--
-- ⛔ Com `NOT NULL`, não haveria onde pendurar a espera da conversa comum — que
-- é exatamente o caso do piloto. **A âncora é a CONVERSA**; o `work_run_id`
-- entra quando existir.
--
-- ---------------------------------------------------------------------------
-- 🔴 UM WAIT ATIVO POR ESCOPO — e o UNIQUE é PARCIAL de propósito
-- ---------------------------------------------------------------------------
--
-- ⚠️ Um `UNIQUE (company_id, conversation_id, scope)` cheio impediria a MESMA
-- conversa de esperar duas vezes ao longo do tempo — e esperar de novo é o
-- normal: o cliente responde, some, volta. O que não pode é **duas esperas
-- ATIVAS ao mesmo tempo** no mesmo escopo, porque aí o vencimento dispara duas
-- vezes e a corretora recebe alerta em dobro.
--
-- =============================================================
-- APPLY
-- =============================================================

CREATE TABLE IF NOT EXISTS public.work_waits (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  -- 🔴 §7 — o backend usa service role e ATRAVESSA a RLS inteira. Esta coluna
  --    só protege junto com o filtro no código, e o teste de dois tenants é
  --    obrigatório. 📊 Precedente na casa: `work_effects` tem RLS ligada e
  --    ZERO policies.
  company_id        uuid NOT NULL
                      REFERENCES public.companies (id) ON DELETE CASCADE,

  -- 🔴 A ÂNCORA. Não é nula: uma espera que não sabe de quem é não é varrível.
  conversation_id   uuid NOT NULL,

  -- ⚠️ NULO PERMITIDO — ver o cabeçalho. 📊 4 runs contra 671 conversas.
  work_run_id       uuid REFERENCES public.work_runs (id) ON DELETE SET NULL,

  -- 🔴 OS VALORES DO CHECK, LISTADOS AQUI COMO O PROTOCOLO EXIGE:
  --      esperando_cliente     o segurado precisa responder
  --      esperando_seguradora  a URA ou o analista da seguradora
  --      esperando_humano      alguém da corretora
  kind              text NOT NULL,

  -- O que distingue duas esperas da mesma conversa. Texto livre de propósito:
  -- quem cria a espera sabe o escopo dela; o banco só garante unicidade.
  scope             text NOT NULL DEFAULT 'default',

  -- 🔴 OS VALORES DO CHECK:
  --      ativo        esperando agora
  --      satisfeito   o que se esperava aconteceu
  --      vencido      o prazo passou e ninguém agiu
  --      cancelado    a espera deixou de fazer sentido
  status            text NOT NULL DEFAULT 'ativo',

  vence_em          timestamptz NOT NULL,

  satisfeito_por    text,
  satisfeito_em     timestamptz,

  -- Quantas vezes o vigia já avisou sobre esta espera vencida.
  -- ⚠️ É o contador do BLOCO C: depois de N avisos ignorados, a conversa vira
  --    `resolucao_motivo='expirou'`.
  avisos            integer NOT NULL DEFAULT 0,

  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT ck_work_waits_kind
    CHECK (kind IN ('esperando_cliente', 'esperando_seguradora', 'esperando_humano')),

  CONSTRAINT ck_work_waits_status
    CHECK (status IN ('ativo', 'satisfeito', 'vencido', 'cancelado')),

  CONSTRAINT ck_work_waits_avisos
    CHECK (avisos >= 0),

  -- ⚠️ Os dois campos de satisfação andam juntos, pelo mesmo motivo do BLOCO A.
  CONSTRAINT ck_work_waits_satisfacao_coerente
    CHECK ((satisfeito_em IS NULL AND satisfeito_por IS NULL)
        OR (satisfeito_em IS NOT NULL AND satisfeito_por IS NOT NULL)),

  -- 🔴 A MESMA FK COMPOSTA DO BLOCO A DA SPEC-090: a espera de uma corretora
  --    não pode apontar para conversa de outra. O banco recusa, com o filtro do
  --    código certo ou errado.
  CONSTRAINT fk_work_waits_conversa_mesma_corretora
    FOREIGN KEY (conversation_id, company_id)
    REFERENCES public.conversations (id, company_id) ON DELETE CASCADE
);

-- 🔴 UM WAIT ATIVO POR ESCOPO — parcial. Ver o cabeçalho.
CREATE UNIQUE INDEX IF NOT EXISTS uq_work_waits_ativo_por_escopo
  ON public.work_waits (company_id, conversation_id, scope)
  WHERE status = 'ativo';

-- O índice do vigia: "quais esperas venceram?"
CREATE INDEX IF NOT EXISTS ix_work_waits_vencendo
  ON public.work_waits (vence_em)
  WHERE status = 'ativo';

-- O índice da pergunta da sexta-feira: "quantos ainda esperam?"
CREATE INDEX IF NOT EXISTS ix_work_waits_por_corretora
  ON public.work_waits (company_id, status, kind);

ALTER TABLE public.work_waits ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.work_waits IS
  'SPEC-086 BLOCO B — a espera como objeto. `work_run_id` aceita NULO de '
  'propósito: 4 work_runs de acionamento contra 671 conversas — a âncora é a '
  'CONVERSA. UNIQUE parcial: um wait ATIVO por escopo, mas esperar de novo '
  'depois é normal.';

-- =============================================================
-- VERIFY  (read-only, e o CONTROLE desfaz o que escreve)
-- =============================================================
--
-- V1 · a tabela existe, com RLS
--
--   select relname, relrowsecurity from pg_class where relname='work_waits';
--   -- esperado: work_waits | t
--
-- V2 · 🔴 OS VALORES DOS CHECKS
--
--   select conname, pg_get_constraintdef(oid) from pg_constraint
--    where conrelid='public.work_waits'::regclass and contype='c';
--
-- V3 · 🔴 O CONTROLE — seis linhas, e a última é a que dá direito à conclusão.
--      ⚠️ A transação é desfeita por `raise`: nada fica gravado.
--
--   (ver o corpo executado no relatório da SPEC — kind inválido, status
--    inválido, avisos negativos, DOIS ativos no mesmo escopo, cross-tenant,
--    e o wait VÁLIDO sem work_run)
--
-- V4 · a pergunta da sexta-feira
--
--   select kind, count(*) from work_waits
--    where company_id = $1 and status = 'ativo' group by 1;
--
-- =============================================================
-- ROLLBACK
-- =============================================================
--
--   drop table if exists public.work_waits;
--
-- ⚠️ Apaga as esperas em curso. O vigia deixa de avisar; nada mais quebra.
