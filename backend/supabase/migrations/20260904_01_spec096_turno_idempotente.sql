-- =============================================================
-- MIGRATION: spec096_turno_idempotente
-- SPEC:      SPEC-096 — BLOCO A.1 (o turno é idempotente)
-- AUTOR:     builder-backend-096            DATA: 2026-09-04
-- OBJETIVO:  a mesma tentativa de turno nunca vira duas respostas na conversa.
--
-- APPLY:     cria o índice único PARCIAL
--            `messages_turno_sem_duplicata_uidx` sobre
--            (conversation_id, role, payload->>'client_request_id'), só para
--            as linhas que carregam `client_request_id`.
-- VERIFY:    select indexdef from pg_indexes
--              where indexname = 'messages_turno_sem_duplicata_uidx';
--            -- espera-se 1 linha, e o indexdef termina com a
--            -- clausula parcial sobre (payload ->> 'client_request_id') IS NOT NULL
-- ROLLBACK:  drop index if exists public.messages_turno_sem_duplicata_uidx;
--
-- EXPAND-FIRST: sim   (só acrescenta um índice; nenhuma coluna muda)
-- DESTRUTIVA:   não
-- =============================================================
--
-- 🔴 POR QUE PARCIAL, e não um índice comum.
-- `payload->>'client_request_id'` é NULL em toda mensagem que já existe hoje
-- (📊 nenhum escritor gravava o campo antes desta SPEC) e continuará NULL nas
-- mensagens do WhatsApp, do widget e do agente de atendimento. Um índice único
-- sem a cláusula parcial trataria esses NULLs como comparáveis em alguns caminhos de
-- upsert e, pior, cobraria de todo escritor futuro um campo que não é dele.
-- Com ela, a regra vale exatamente para quem a pediu: o turno do painel.
--
-- ⚠️ `CONCURRENTLY` fica de fora de propósito: ele não roda dentro de bloco de
-- transação, e o aplicador desta migration roda em transação. 💭 Se o VERIFY
-- demorar ou travar escrita na `messages`, refaça o índice com CONCURRENTLY
-- fora de transação — a criação é idempotente e pode ser repetida.

-- 🔴 E POR QUE `role` ENTRA NA CHAVE.
-- 📊 04/09/2026, lido em `app/api/chat/stream/route.ts:151` (o BFF desta mesma
-- SPEC): a PERGUNTA do corretor também é gravada com
-- `payload.client_request_id` — é assim que o BFF reconhece a repetição antes
-- de chamar o backend. Sem o `role` na chave, a RESPOSTA do mesmo turno
-- colidiria com a PERGUNTA dele, e nenhuma resposta do painel entraria. Com
-- ele, a regra é a que se queria: uma pergunta e uma resposta por tentativa.
CREATE UNIQUE INDEX IF NOT EXISTS messages_turno_sem_duplicata_uidx
  ON public.messages (conversation_id, role, (payload->>'client_request_id'))
  WHERE payload->>'client_request_id' IS NOT NULL;

comment on index public.messages_turno_sem_duplicata_uidx is
  'SPEC-096 A.1 — uma tentativa de turno, uma resposta. Parcial: só vale para as mensagens que carregam client_request_id.';
