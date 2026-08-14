-- =============================================================
-- MIGRATION: espelho_cursor_incremental
-- SPEC:      SPEC-063 — Espelho bidirecional (P0 Egress, 13/08/2026)
-- AUTOR:     execucao Opus                DATA: 2026-08-13
-- OBJETIVO:  dar ao sync do Espelho uma marca d'agua DURAVEL por corretora,
--            para que ele pare de reler o acervo inteiro a cada 10 minutos.
--
-- APPLY:     · tabela `espelho_sync_cursor` (uma linha por corretora)
--            · indice `(company_id, created_at, id)` em attendance_transcripts
--            · SEED: cursor em now() para as corretoras evolution-go ativas
--
-- VERIFY:    SELECT to_regclass('public.espelho_sync_cursor');       -- nao nulo
--            SELECT indexname FROM pg_indexes
--              WHERE tablename='attendance_transcripts'
--                AND indexname='ix_attendance_transcripts_cursor';   -- 1 linha
--            SELECT count(*) FROM public.espelho_sync_cursor;        -- 3 (hoje)
--            SELECT count(*) FROM public.espelho_sync_cursor
--              WHERE last_created_at > now() - interval '1 hour';    -- todas
--            -- e o que mais importa, o plano da consulta do sync:
--            EXPLAIN SELECT id FROM public.attendance_transcripts
--              WHERE company_id = (SELECT company_id FROM public.espelho_sync_cursor LIMIT 1)
--                AND created_at >= now() - interval '1 day'
--              ORDER BY created_at, id LIMIT 500;   -- espera Index Scan
--
-- ROLLBACK:  DROP INDEX IF EXISTS public.ix_attendance_transcripts_cursor;
--            DROP TABLE IF EXISTS public.espelho_sync_cursor;
--            -- ⚠️ No rollback OPERACIONAL prefira NAO derrubar: basta reverter
--            -- o codigo e a tabela fica inerte. Nada mais a le.
--
-- EXPAND-FIRST: sim   (so cria; nenhuma coluna alterada ou removida)
-- DESTRUTIVA:   nao   (`attendance_transcripts`, `messages` e `conversations`
--                      nao sao tocadas -- nem uma linha lida, nem uma escrita)
-- =============================================================
--
-- POR QUE ESTA MIGRATION EXISTE
-- =============================
-- 📊 13/08/2026, pg_stat_statements de producao: `sincronizar_chats` releu a
-- janela de 7 dias do acervo a cada ciclo e chamou `espelhar_no_chat` para cada
-- linha. Resultado: 771.313 leituras de `messages` para 5.681 mensagens
-- escritas -- e a organizacao Supabase restringida por excesso de Egress, com
-- PostgREST, Storage e Auth respondendo 402.
--
-- A Alavanca A ja matou o custo POR LINHA. Esta migration mata o LACO: com um
-- cursor, o sync passa a ler so o que chegou desde a ultima passada.
--
--
-- 🔴 POR QUE O CURSOR E `created_at` E NAO `wa_timestamp`
-- =======================================================
-- Este e o ponto onde o desenho obvio perde mensagem em silencio, e a medicao
-- e brutal.
--
-- 📊 13/08/2026, `attendance_transcripts` por `source`:
--
--     source         linhas   atraso medio   atraso max   > 15 min
--     history_sync   99.951      3.981 h      16.293 h     99.845  (99,89%)
--     live            5.324          0,0 h        0,1 h          0
--
--   (atraso = created_at - wa_timestamp)
--
-- O WhatsApp entrega historico em bloco a cada reconexao. Uma mensagem ENVIADA
-- em setembro de 2024 foi INSERIDA aqui em agosto de 2026 -- 679 dias depois.
--
-- Um cursor por `wa_timestamp`, mesmo com sobreposicao generosa de 15 minutos,
-- nao veria 99,89% das linhas de history_sync: elas nascem "atras" do cursor.
-- A mensagem ficaria intacta no acervo e NUNCA apareceria no chat da corretora.
-- Trocar Egress alto por mensagem sumida em silencio seria um negocio pessimo.
--
-- Sao dois relogios na mesma linha, e cada um responde uma pergunta:
--
--     created_at    -> "esta linha CHEGOU ao AutoBrokers desde a ultima passada?"
--     wa_timestamp  -> "esta mensagem e recente o bastante para o chat?"
--
-- O cursor usa o primeiro. A elegibilidade (`deve_espelhar`, 30 dias) continua
-- usando o segundo. Uma linha de 2024 que chega hoje e ENCONTRADA pelo cursor e
-- RECUSADA pela elegibilidade -- que e exatamente o comportamento certo.
--
-- Ha um segundo motivo, independente e igualmente decisivo: `wa_timestamp` e
-- NULLABLE. Cursor sobre coluna que aceita NULL esta quebrado por construcao.
-- `created_at` e NOT NULL DEFAULT now(), e `id` e NOT NULL -- por isso o par
-- `(created_at, id)` da uma ordem TOTAL e uma paginacao estavel.
--
--
-- 🔴 POR QUE O SEED E `now()` E NAO ZERO
-- ======================================
-- Sem semente, a primeira rodada nao teria de onde partir. Partir do inicio
-- significaria varrer as 105.275 linhas do acervo de uma vez -- 26 vezes o
-- ciclo que causou o incidente, executado no minuto exato em que o Founder
-- acabou de pagar pelo plano Pro. O conserto reproduziria a pane.
--
-- Por isso o cursor nasce no PRESENTE. A recuperacao do periodo da interrupcao
-- e um ATO DELIBERADO, feito pelo endpoint que ja existe
-- (`POST /api/whatsapp-channel/espelho/trazer-conversas`), corretora por
-- corretora, com janela explicita e medicao entre uma e outra.
--
-- A mesma regra vale para a QUARTA corretora, que ainda nao existe: o codigo
-- trata "sem cursor" como "cria em now() e nao varre nada". Ausencia de cursor
-- nunca pode significar varredura completa -- nem hoje, nem em tres meses.

-- -------------------------------------------------------------------------
-- 1. A marca d'agua, por corretora
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.espelho_sync_cursor (
    -- Uma linha por corretora. `company_id` e a chave primaria de proposito:
    -- torna IMPOSSIVEL uma corretora ter dois cursores em desacordo, que seria
    -- a forma mais silenciosa de perder mensagem.
    company_id      uuid PRIMARY KEY
                    REFERENCES public.companies(id) ON DELETE CASCADE,

    -- Ate onde o sync ja processou, no relogio de INGESTAO.
    last_created_at timestamptz NOT NULL,

    -- Desempate para `created_at` iguais. NULL so na semeadura.
    last_id         uuid,

    -- Observabilidade barata: "este cursor esta andando?" e uma pergunta que a
    -- gente vai querer responder as 3h da manha.
    updated_at      timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.espelho_sync_cursor IS
  'Marca d''agua do sync do Espelho, por corretora. Usa o relogio de INGESTAO '
  '(attendance_transcripts.created_at), NUNCA wa_timestamp: 📊 99,89% das '
  'linhas history_sync chegam com mais de 15 min de atraso sobre o wa_timestamp '
  '(media 3.981 h, maximo 16.293 h), e um cursor por wa_timestamp as perderia '
  'em silencio. Ausencia de linha significa "comece em now()", NUNCA "varra '
  'tudo" -- ver o cabecalho da migration 20260813_01.';

COMMENT ON COLUMN public.espelho_sync_cursor.last_created_at IS
  'Relogio de INGESTAO. Responde "esta linha chegou desde a ultima passada?". '
  'Quem responde "esta mensagem merece o chat?" e wa_timestamp, via deve_espelhar.';

-- RLS fail-closed. A tabela e operacional e so o backend (service role) a
-- escreve; habilitar sem policy garante que nenhuma chave anon/authenticated
-- a alcance, hoje ou depois de alguem expor um endpoint novo sem pensar.
ALTER TABLE public.espelho_sync_cursor ENABLE ROW LEVEL SECURITY;

-- -------------------------------------------------------------------------
-- 2. O indice que serve a consulta incremental
-- -------------------------------------------------------------------------
-- 📊 Os indices existentes nao atendem a este access pattern:
--   · idx_attendance_transcripts_company  (company_id)          -- sem a data
--   · ix_attendance_transcripts_created   (created_at)          -- sem o tenant
--   · ix_attendance_transcripts_lookup    (company_id, counterparty,
--                                          wa_timestamp DESC)   -- counterparty
--                                          no meio o inutiliza aqui, e a data
--                                          e a do EVENTO, nao a da ingestao
--
-- Nenhum deles e inutil: cada um serve outro consumidor. O que falta e este.
--
-- A ordem das colunas nao e negociavel: `company_id` primeiro porque o filtro e
-- sempre por tenant (isolamento, CLAUDE.md §7); `created_at` depois porque e a
-- faixa; `id` por ultimo porque e so o desempate da ordenacao total.
CREATE INDEX IF NOT EXISTS ix_attendance_transcripts_cursor
    ON public.attendance_transcripts (company_id, created_at, id);

COMMENT ON INDEX public.ix_attendance_transcripts_cursor IS
  'Serve a varredura incremental do Espelho: WHERE company_id=? AND '
  'created_at >= cursor ORDER BY created_at, id. Ordem total e estavel — sem o '
  'desempate por id, duas linhas com o mesmo created_at poderiam trocar de '
  'lugar entre uma pagina e a proxima, e uma delas nunca apareceria.';

-- -------------------------------------------------------------------------
-- 3. SEED — no presente, nunca no comeco dos tempos
-- -------------------------------------------------------------------------
-- `ON CONFLICT DO NOTHING`: rodar esta migration duas vezes nao pode empurrar
-- um cursor que ja andou de volta para o presente -- isso pularia tudo que
-- chegou no meio. Idempotente de verdade, nao "idempotente se ninguem usou".
INSERT INTO public.espelho_sync_cursor (company_id, last_created_at, last_id)
-- `NULL::uuid` e nao `NULL`: sem o cast o Postgres infere `text` e recusa a
-- insercao inteira (42804). A primeira tentativa desta migration morreu aqui.
SELECT DISTINCT i.company_id, now(), NULL::uuid
  FROM public.integrations i
  JOIN public.companies c ON c.id = i.company_id
 WHERE i.provider = 'evolution-go'
   AND i.is_active
ON CONFLICT (company_id) DO NOTHING;
