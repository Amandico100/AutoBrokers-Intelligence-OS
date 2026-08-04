-- =============================================================
-- MIGRATION: o_repareamento_nao_duplica
-- SPEC:      SPEC-063 — atendimento e canais (bloco: parear sem duplicar)
-- AUTOR:     executor senior          DATA: 2026-08-04
-- OBJETIVO:  (1) guardar QUAL telefone esta pareado em cada canal e (2) por a
--            corretora dentro das chaves de deduplicacao, sem que nada do que
--            ja foi baixado seja reimportado.
--
-- APPLY:     1) integrations.paired_jid        text        — o JID que conectou
--            2) integrations.paired_phone_e164 text        — +5547...
--            3) integrations.paired_at         timestamptz — quando conectou
--            4) ux_attendance_transcripts_dedupe_tenant  UNIQUE
--               (company_id, observer_number, message_id)
--            5) uq_observed_events_msg_tenant            UNIQUE
--               (company_id, observer_number, message_id)
--            6) idx_observed_sessions_lookup_tenant      (nao unico)
--               (company_id, observer_number, counterparty, last_event_at DESC)
--            7) COMMENT em cada coluna e em cada indice novo
--
--            NAO faz: nenhum DROP, nenhum UPDATE, nenhum backfill. Os indices
--            ANTIGOS CONTINUAM VIVOS de proposito — ver "EXPAND-FIRST" abaixo.
--
-- VERIFY:    -- 1. as tres colunas existem e sao nulaveis
--            SELECT column_name, data_type, is_nullable
--              FROM information_schema.columns
--             WHERE table_schema='public' AND table_name='integrations'
--               AND column_name IN ('paired_jid','paired_phone_e164','paired_at')
--             ORDER BY column_name;
--            -- esperado: 3 linhas, todas is_nullable='YES'
--
--            -- 2. os tres indices novos existem, com a corretora na frente
--            SELECT indexname, indexdef FROM pg_indexes
--             WHERE schemaname='public'
--               AND indexname IN ('ux_attendance_transcripts_dedupe_tenant',
--                                 'uq_observed_events_msg_tenant',
--                                 'idx_observed_sessions_lookup_tenant')
--             ORDER BY indexname;
--            -- esperado: 3 linhas; as duas primeiras CREATE UNIQUE INDEX
--
--            -- 3. os indices ANTIGOS continuam vivos (expand-first)
--            SELECT count(*) AS antigos_vivos FROM pg_indexes
--             WHERE schemaname='public'
--               AND indexname IN ('ux_attendance_transcripts_dedupe',
--                                 'uq_observed_events_msg',
--                                 'idx_observed_sessions_lookup');
--            -- esperado: 3   (se vier menos, o codigo antigo perdeu o
--            --                on_conflict e passa a inserir duplicata)
--
--            -- 4. NENHUMA linha foi criada, apagada ou alterada
--            SELECT (SELECT count(*) FROM public.attendance_transcripts) AS transcricoes,
--                   (SELECT count(*) FROM public.observed_events)        AS eventos;
--            -- esperado: 69150 e 17651  (medido em 04/08/2026, pre-APPLY)
--
--            -- 5. o guarda novo CONSEGUE falhar — e o antigo NAO estorva.
--            --    Sem esta prova o indice pode existir sem guardar nada
--            --    (CLAUDE.md 9.3: guarda que nao tem como falhar nao guarda).
--            BEGIN;
--              -- (a) mesma corretora + mesmo message_id => 23505 esperado
--              INSERT INTO public.observed_events
--                (company_id, observer_number, counterparty, direction, msg_type, message_id)
--              SELECT company_id, observer_number, counterparty, direction, msg_type,
--                     'verify:23505:'||gen_random_uuid()::text
--                FROM public.observed_events LIMIT 1;
--              INSERT INTO public.observed_events
--                (company_id, observer_number, counterparty, direction, msg_type, message_id)
--              SELECT company_id, observer_number, counterparty, direction, msg_type, message_id
--                FROM public.observed_events WHERE message_id LIKE 'verify:23505:%' LIMIT 1;
--              -- esperado: ERROR 23505 duplicate key
--            ROLLBACK;
--
-- ROLLBACK:  DROP INDEX IF EXISTS public.ux_attendance_transcripts_dedupe_tenant;
--            DROP INDEX IF EXISTS public.uq_observed_events_msg_tenant;
--            DROP INDEX IF EXISTS public.idx_observed_sessions_lookup_tenant;
--            ALTER TABLE public.integrations DROP COLUMN IF EXISTS paired_jid;
--            ALTER TABLE public.integrations DROP COLUMN IF EXISTS paired_phone_e164;
--            ALTER TABLE public.integrations DROP COLUMN IF EXISTS paired_at;
--            -- Reversivel por inteiro: nenhuma linha pre-existente e lida,
--            -- atualizada ou apagada, e nenhum indice antigo e tocado.
--
-- EXPAND-FIRST: sim, e no sentido forte — os indices antigos NAO sao removidos
--               aqui. Ver secao 3.
-- DESTRUTIVA:   nao
-- =============================================================
--
-- O PEDIDO, LITERAL
-- -----------------
-- > "Eu quero primeiro conectar os WhatsApps da Regina e da Saionara. NAO
-- >  QUERO QUE AS CONVERSAS QUE JA FORAM BAIXADAS SEJAM DUPLICADAS. Quero
-- >  apenas conversas novas sendo baixadas."
--
-- O que esta em jogo, 📊 medido em 04/08/2026 no projeto dcajcvlzcjbmyapmklil:
--
--     SELECT count(*) FROM attendance_transcripts;  -->  69.150
--     SELECT count(*) FROM observed_events;         -->  17.651
--
-- O history_sync do WhatsApp reentrega o historico INTEIRO a cada pareamento.
-- Se a deduplicacao falhar, esses 86.801 registros voltam em dobro.
--
-- ---------------------------------------------------------------------------
-- 1. AS TRES COLUNAS — a identidade do que esta conectado
-- ---------------------------------------------------------------------------
-- Em 04/08/2026 o Founder nao soube dizer qual numero estava conectado no
-- celular da atendente, e nao havia como saber: o pareamento gravava
-- `channel_status` e `last_seen_at`, e descartava o telefone.
--
-- O unico campo que parecia responder era `identifier` — que no evolution-go e
-- o NOME DA INSTANCIA (`ab-obs-6c9c55e22f-1`). 📊 Nas tres integracoes observer
-- existentes hoje, `identifier` nunca foi um telefone.
--
-- Nulaveis, sem default e sem backfill: o telefone das linhas ja pareadas nao
-- esta em lugar nenhum deste banco. Inventa-lo a partir do nome da instancia e
-- exatamente o engano que estas colunas existem para acabar.

ALTER TABLE public.integrations
    ADD COLUMN IF NOT EXISTS paired_jid text;

ALTER TABLE public.integrations
    ADD COLUMN IF NOT EXISTS paired_phone_e164 text;

ALTER TABLE public.integrations
    ADD COLUMN IF NOT EXISTS paired_at timestamptz;

-- ---------------------------------------------------------------------------
-- 2. A CORRETORA DENTRO DA CHAVE DE DEDUPLICACAO
-- ---------------------------------------------------------------------------
-- As chaves de hoje nao tem `company_id`:
--
--     ux_attendance_transcripts_dedupe   UNIQUE (observer_number, message_id)
--     uq_observed_events_msg             UNIQUE (observer_number, message_id)
--
-- E `observer_number` NAO e telefone: e `_digits()` do nome da instancia
-- (`observer_intake.py::_observer_number_of`). 📊 AutoFleet = `6955221`
-- (digitos de `ab-obs-6c9c55e22f-1`), Resulta = `045041`. Ha dois fallbacks
-- literais, e ambos ja estao em producao: 📊 167 eventos com `unknown` e 1
-- transcricao com `attendance-channel`.
--
-- Duas corretoras caindo no mesmo literal teriam a MESMA chave de dedupe: a
-- mensagem da segunda seria descartada em silencio pelo `ignore_duplicates`.
-- Isso e perda de dado que ninguem ve — a linha simplesmente nao nasce.
--
-- ⚠️ POR QUE AFROUXAR A CHAVE NAO REABRE O HISTORICO
--
-- Acrescentar coluna a uma chave unica a torna mais PERMISSIVA, e a pergunta
-- certa e se isso permite reimportar o que ja foi baixado. Nao permite, e o
-- motivo e estrutural: dentro de UMA corretora, `company_id` e constante, logo
-- (company_id, observer_number, message_id) colide exatamente quando
-- (observer_number, message_id) colide. O afrouxamento so vale ENTRE
-- corretoras, que e onde ele foi pedido.
--
-- 📊 Medido em 04/08/2026, antes de escrever este arquivo:
--
--     -- linhas que colidiriam com a chave NOVA
--     SELECT sum(n-1) FROM (SELECT count(*) n FROM attendance_transcripts
--       WHERE message_id IS NOT NULL
--       GROUP BY company_id, observer_number, message_id HAVING count(*)>1) a;
--     -->  0        (e 0 tambem em observed_events)
--
--     -- pares (observer_number, message_id) presentes em 2+ corretoras
--     SELECT count(*) FROM (SELECT observer_number, message_id
--       FROM attendance_transcripts WHERE message_id IS NOT NULL
--       GROUP BY 1,2 HAVING count(DISTINCT company_id)>1) b;
--     -->  0        (e 0 tambem em observed_events)
--
-- ZERO linhas colidem com a chave nova, nas duas tabelas. A construcao dos
-- indices nao pode falhar por duplicata, e nenhuma linha existente muda de
-- lado. A fusao entre corretoras e, hoje, teorica — mas com duas pareando em
-- dias, e a hora de fecha-la e antes, nao depois.

CREATE UNIQUE INDEX IF NOT EXISTS ux_attendance_transcripts_dedupe_tenant
    ON public.attendance_transcripts (company_id, observer_number, message_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_observed_events_msg_tenant
    ON public.observed_events (company_id, observer_number, message_id);

-- `observed_sessions` e um caso diferente e precisa ser dito com precisao:
-- 📊 `idx_observed_sessions_lookup` NAO e unico — e
-- `(observer_number, counterparty, last_event_at DESC)`, um indice de BUSCA.
-- Ele nao deduplica nada, e por isso nao ha o que trocar nele.
--
-- O risco que ele carrega e outro, e e do mesmo tamanho: e por ele que
-- `_store_event_sync` procura "a sessao aberta deste observador com este
-- interlocutor" — 📊 uma consulta que ate hoje nao filtrava `company_id`. Duas
-- corretoras com o mesmo `observer_number` falando com o mesmo numero
-- escreveriam na MESMA sessao. A irma desta tabela ja acertou:
-- 📊 `ix_attendance_sessions_lookup` e `(company_id, observer_number,
-- counterparty, status)`. O indice abaixo da a `observed_sessions` o mesmo
-- suporte, para o filtro por corretora que o codigo passa a fazer.

CREATE INDEX IF NOT EXISTS idx_observed_sessions_lookup_tenant
    ON public.observed_sessions (company_id, observer_number, counterparty, last_event_at DESC);

-- ---------------------------------------------------------------------------
-- 3. POR QUE OS INDICES ANTIGOS FICAM — a parte que mais importa
-- ---------------------------------------------------------------------------
-- A tentacao e trocar: dropar o antigo e ficar so com o novo. Trocar aqui
-- PRODUZ o desastre que esta migration existe para evitar, e o caminho e este:
--
-- O codigo grava com `upsert(..., on_conflict="observer_number,message_id")`.
-- O PostgREST repassa isso a um `ON CONFLICT (observer_number, message_id)`, e
-- o Postgres exige um indice unico que case EXATAMENTE com essas colunas. Sem
-- o indice antigo, a clausula deixa de casar e o INSERT morre com 42P10
-- ("no unique or exclusion constraint matching the ON CONFLICT
-- specification"). O que acontece a seguir depende do caminho:
--
--   observer_intake.py::_store_event_sync   tem fallback para `insert` simples
--   history_ingest.py::_store_history_event NAO tem — a excecao sobe e o
--                                           `except Exception: pass` de
--                                           `_ingest_conversation` a engole
--
-- Ou seja: uma troca de indice sem o deploy do codigo na mesma hora faz a
-- ingestao do historico gravar ZERO linha, em silencio, com o log dizendo que
-- correu bem. E a ordem inversa (codigo novo antes da migration) da no mesmo
-- pelo motivo espelhado.
--
-- Com os dois indices vivos, as DUAS grafias de `on_conflict` funcionam, e a
-- ordem entre aplicar a migration e subir o deploy deixa de importar. Nao ha
-- janela em que o produto fica errado.
--
-- O indice antigo e mais ESTRITO que o novo: enquanto ele existir, e ele quem
-- decide, e a fusao entre corretoras continua tecnicamente possivel. Isso e
-- aceito de propósito. 📊 Ela exige duas corretoras com o mesmo
-- `observer_number` E o mesmo `message_id`, e hoje ha 0 casos.
--
-- O DROP dos tres antigos e uma migration SEPARADA, depois de o codigo novo
-- estar em producao e provado. Escrita e pronta para colar quando for a hora:
--
--     DROP INDEX IF EXISTS public.ux_attendance_transcripts_dedupe;
--     DROP INDEX IF EXISTS public.uq_observed_events_msg;
--     DROP INDEX IF EXISTS public.idx_observed_sessions_lookup;
--
-- LOCK: `CREATE UNIQUE INDEX` sem CONCURRENTLY trava escrita na tabela
-- enquanto constroi. 📊 69.150 e 17.651 linhas: milissegundos. CONCURRENTLY
-- proibiria rodar este arquivo dentro de uma transacao, e ai os tres ALTER e
-- os tres indices poderiam ser aplicados pela metade — trocar um APPLY atomico
-- por uma trava de milissegundos seria o negocio errado.

-- ---------------------------------------------------------------------------
-- 4. O QUE CADA COISA GUARDA — escrito no banco, nao so no relatorio
-- ---------------------------------------------------------------------------

COMMENT ON COLUMN public.integrations.paired_jid IS
  'SPEC-063 - o JID que efetivamente conectou nesta linha (ex.: '
  '5547XXXXXXXXX@s.whatsapp.net), lido do /instance/status e do connection.update '
  'em app/services/whatsapp/numero_pareado.py. NULL = o provedor nao informou; '
  'nunca deduzir do identifier, que e o NOME DA INSTANCIA.';

COMMENT ON COLUMN public.integrations.paired_phone_e164 IS
  'SPEC-063 - o telefone pareado em E.164 (+55DDNNNNNNNNN), sem o sufixo de '
  'dispositivo do JID. Responde "qual numero esta conectado neste celular?", '
  'pergunta que em 04/08/2026 nao tinha resposta em lugar nenhum do sistema. '
  'PII: nunca em log, artifact ou RAG — mascarar com numero_pareado.mascarar().';

COMMENT ON COLUMN public.integrations.paired_at IS
  'SPEC-063 - quando esta linha conectou pela ultima vez. Diferente de '
  'last_seen_at (ultimo sinal de vida): este marca o PAREAMENTO, e e ele que '
  'explica por que um history_sync chegou numa rajada.';

COMMENT ON INDEX public.ux_attendance_transcripts_dedupe_tenant IS
  'SPEC-063 - dedupe do Espelho COM a corretora na chave. Convive de proposito '
  'com ux_attendance_transcripts_dedupe (sem company_id) para que as duas '
  'grafias de on_conflict funcionem durante o cutover; o antigo cai em migration '
  'separada, depois do deploy. 📊 04/08/2026: 0 linhas colidem com esta chave.';

COMMENT ON INDEX public.uq_observed_events_msg_tenant IS
  'SPEC-063 - dedupe do Atlas COM a corretora na chave. Mesma convivencia '
  'deliberada com uq_observed_events_msg. 📊 04/08/2026: 0 linhas colidem.';

COMMENT ON INDEX public.idx_observed_sessions_lookup_tenant IS
  'SPEC-063 - suporte a busca da sessao aberta filtrando por corretora, espelho '
  'de ix_attendance_sessions_lookup. O indice antigo (sem company_id) nao e '
  'unico e nunca deduplicou nada: o risco dele era a consulta de sessao aberta '
  'atravessar corretoras, nao duplicar linha.';
