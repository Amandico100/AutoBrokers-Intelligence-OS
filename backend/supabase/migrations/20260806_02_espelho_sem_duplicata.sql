-- =============================================================
-- MIGRATION: espelho_sem_duplicata
-- SPEC:      SPEC-063 — Espelho bidirecional
-- AUTOR:     execucao Opus                DATA: 2026-08-06
-- OBJETIVO:  tornar IMPOSSIVEL a mesma mensagem do WhatsApp entrar duas vezes
--            na mesma conversa — no banco, nao no Python.
--
-- APPLY:     indice UNICO parcial em (conversation_id, payload->>'wa_message_id')
--            para as linhas do espelho
-- VERIFY:    SELECT indexname FROM pg_indexes
--              WHERE schemaname='public' AND tablename='messages'
--                AND indexname='messages_espelho_sem_duplicata_uidx';
--            -- espera 1 linha
--            INSERT duplicado deve falhar com 23505.
-- ROLLBACK:  DROP INDEX IF EXISTS public.messages_espelho_sem_duplicata_uidx;
--
-- EXPAND-FIRST: sim   (so cria indice; nenhuma coluna alterada ou removida)
-- DESTRUTIVA:   nao   (CREATE UNIQUE INDEX falha se ja houver duplicata;
--                      📊 conferido em 06/08 23:30 UTC: zero duplicatas)
-- =============================================================
--
-- POR QUE ESTE INDICE EXISTE — a bomba que uma auditoria independente achou
--
-- O espelho deduplicava lendo as 40 mensagens mais recentes da conversa e
-- comparando o `wa_message_id` em Python. 📊 Ja existem conversas com 60, 53,
-- 48 e 46 mensagens — acima da janela.
--
-- O backfill grava da mais ANTIGA para a mais nova, entao a mensagem mais
-- antiga fica no fim da ordenacao por `created_at desc`: fora das 40. Na rodada
-- seguinte do sync (a cada 10 minutos) ela nao seria encontrada e entraria de
-- novo. E cada duplicata empurra mais mensagens para fora da janela — o
-- estrago acelera sozinho.
--
-- A guarda em Python continua (ela evita a ida ao banco no caso comum), mas ela
-- deixou de ser a unica: quem garante agora e o Postgres, que nao tem janela.
--
-- Parcial de proposito: so linhas do espelho com id do WhatsApp entram. O chat
-- interno e as mensagens do dashboard (que nascem com `wa_message_id: null`)
-- nao pagam por uma regra que nao e delas.

CREATE UNIQUE INDEX IF NOT EXISTS messages_espelho_sem_duplicata_uidx
  ON public.messages (conversation_id, (payload ->> 'wa_message_id'))
  WHERE payload ->> 'wa_message_id' IS NOT NULL;

COMMENT ON INDEX public.messages_espelho_sem_duplicata_uidx IS
  'A mesma mensagem do WhatsApp nao entra duas vezes na mesma conversa. '
  'O WhatsApp reentrega historico a cada reconexao e o sync do espelho roda de '
  '10 em 10 minutos: sem esta garantia no BANCO, a dedup dependeria de uma '
  'janela de 40 mensagens em Python que conversas longas ja ultrapassam.';
