-- =============================================================
-- MIGRATION: messages_payload_do_espelho
-- SPEC:      SPEC-063 — Espelho bidirecional (conversa do WhatsApp no chat)
-- AUTOR:     execucao Opus                DATA: 2026-08-06
-- OBJETIVO:  dar a `public.messages` um lugar para guardar o id da mensagem
--            do WhatsApp, sem o qual o espelho nao consegue deduplicar.
--
-- APPLY:     ADD COLUMN payload jsonb (nullable, sem default) +
--            indice parcial por payload->>'wa_message_id'
-- VERIFY:    SELECT column_name FROM information_schema.columns
--              WHERE table_schema='public' AND table_name='messages'
--                AND column_name='payload';
--            -- espera 1 linha
--            SELECT indexname FROM pg_indexes
--              WHERE schemaname='public' AND tablename='messages'
--                AND indexname='messages_wa_message_id_idx';
--            -- espera 1 linha
-- ROLLBACK:  DROP INDEX IF EXISTS public.messages_wa_message_id_idx;
--            ALTER TABLE public.messages DROP COLUMN IF EXISTS payload;
--            (seguro: coluna nova, nullable, sem leitor fora do espelho)
--
-- EXPAND-FIRST: sim   (so adiciona; nada e removido nem alterado)
-- DESTRUTIVA:   nao
-- =============================================================
--
-- POR QUE ESTA MIGRATION EXISTE — 06/08/2026
--
-- O espelho gravava `topic`, `extension` e `payload` em `public.messages`.
-- Nenhuma das tres existe nessa tabela. Toda mensagem era recusada, e o
-- contador acumulou 4.059 APIError enquanto a corretora via conversas abertas
-- com o painel vazio.
--
-- O erro de leitura que produziu isso: consultei
-- `information_schema.columns WHERE table_name='messages'` **sem filtrar o
-- schema**. O Supabase tem `realtime.messages` alem de `public.messages`, e a
-- consulta devolveu as colunas das DUAS misturadas. `topic`, `extension`,
-- `inserted_at` e `updated_at` sao da tabela do Realtime. O `id` aparecendo
-- duas vezes no resultado era o aviso, e eu passei por cima dele.
--
-- `topic` e `extension` nao voltam: eram invencao minha. `payload` volta como
-- coluna de verdade porque ele carrega o `wa_message_id`, e sem ele o espelho
-- nao tem como saber que uma mensagem ja esta no chat — o WhatsApp reentrega o
-- historico a cada reconexao, e sem dedup a conversa duplicaria inteira.

ALTER TABLE public.messages
  ADD COLUMN IF NOT EXISTS payload jsonb;

COMMENT ON COLUMN public.messages.payload IS
  'Metadados da origem da mensagem. O espelho (SPEC-063) grava aqui '
  '{wa_message_id, origem, direcao, wa_type}: wa_message_id e a chave de '
  'deduplicacao contra a reentrega do WhatsApp; origem separa o que veio do '
  'dashboard do que voltou pelo webhook (o "eco").';

-- Indice PARCIAL: so as linhas que tem o id do WhatsApp entram. As mensagens
-- do chat interno (a maioria historica) nao pagam por um indice que nao usam.
CREATE INDEX IF NOT EXISTS messages_wa_message_id_idx
  ON public.messages ((payload ->> 'wa_message_id'))
  WHERE payload ? 'wa_message_id';
