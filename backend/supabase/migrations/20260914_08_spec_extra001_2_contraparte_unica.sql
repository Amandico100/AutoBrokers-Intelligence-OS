-- =============================================================
-- MIGRATION: spec_extra001_2_contraparte_unica
-- SPEC:      SPEC-EXTRA-001.2 — BLOCO E (§11, M2) · a conversa-fantasma nº 176
-- AUTOR:     builder E (Opus 5)              DATA: 2026-09-14
-- OBJETIVO:  `conversations.contraparte` (a chave ÚNICA da pessoa do outro lado)
--            + índice único parcial que impede duas conversas de WhatsApp
--            ABERTAS para a mesma contraparte na mesma corretora.
--
-- APPLY:     (a) ADD COLUMN IF NOT EXISTS contraparte text  + COMMENT
--            (b) BACKFILL em SQL puro sobre `user_phone`
--            (c) ÍNDICE ÚNICO PARCIAL (company_id, contraparte)
--
-- 🔴 A ORDEM É OBRIGATÓRIA, E ELA NÃO É TODA DESTE ARQUIVO:
--
--      ① os ESCRITORES já preenchem `contraparte`      (deploy do código, ANTES)
--      ② (a) a coluna nasce  →  (b) o backfill roda
--      ③ 🔴 o ORQUESTRADOR conta as duplicatas (a consulta D0 abaixo)
--      ④ se D0 > 0: **o índice NÃO entra.** As duplicatas viram LISTA no
--         relatório e uma decisão registrada. ⛔ Esta migration NÃO fecha
--         conversa nenhuma para abrir caminho para o índice: fechar a mais
--         antiga em lote seria exatamente a D-PILOTO-02, e o que está nelas é
--         atendimento de gente. Só o script das fantasmas fecha conversa, e só
--         as que ninguém consegue abrir.
--      ⑤ com D0 = 0: (c) o índice entra.
--
--    ⚠️ Expand-first: (a) e (b) podem ser aplicadas com D0 > 0 — a coluna e o
--    backfill não travam ninguém. Quem trava é só o índice.
--
-- VERIFY:    D0 + V1–V4 abaixo — SQL executável; V3/V4 em BEGIN…ROLLBACK.
-- ROLLBACK:  `DROP INDEX IF EXISTS uq_conversations_contraparte_aberta`.
--            🔴 A COLUNA FICA. Expand-first: coluna órfã não quebra leitor, e
--            derrubá-la obrigaria a um segundo backfill no caminho de volta.
--
-- EXPAND-FIRST: sim
-- DESTRUTIVA:   não (nenhuma linha é apagada; o backfill só PREENCHE `contraparte`,
--               que nasce nula — nenhuma coluna existente é lida para escrita)
-- =============================================================

-- -------------------------------------------------------------------------
-- (a) A COLUNA
-- -------------------------------------------------------------------------
ALTER TABLE public.conversations
  ADD COLUMN IF NOT EXISTS contraparte text;

COMMENT ON COLUMN public.conversations.contraparte IS
  'SPEC-EXTRA-001.2 E2 — a chave ÚNICA da pessoa do outro lado: só dígitos do '
  'telefone, normalizado por `identidade_do_evento.contraparte_de`. NULO quando '
  'o `user_phone` não é telefone (um @lid cru): o índice único parcial ignora '
  'NULL, então a conversa-fantasma antiga continua existindo e não bloqueia '
  'ninguém — o que ela perde é o direito de ser reusada como se fosse alguém.';

-- -------------------------------------------------------------------------
-- (b) O BACKFILL — 🔴 a MESMA regra de `contraparte_de`, escrita no dialeto do
--     Postgres porque é aqui que ela vai rodar.
--
--     ⚠️ CLAUDE.md §9.4: "um padrão medido com um motor e aplicado com outro é
--     um padrão sobre outra coisa". A regra do Python é, por inteiro:
--
--        digitos = só os dígitos de user_phone
--        recusa se  digitos = ''                                      → NULL
--        recusa se  length(digitos) >= 13 AND digitos não começa '55' → NULL
--        (`_parece_telefone`, identidade_do_evento.py:60-66)
--
--     O `>= 13 sem 55` é o que separa LID de telefone: um celular BR completo
--     tem 13 dígitos e começa com `55`; 📊 um LID observado em produção tem 15 e
--     não começa com `55`. ⛔ Um critério de ">= 13 dígitos" sozinho condenaria
--     TODO celular brasileiro.
--
--     ⛔ `@lid` NÃO é resolvido aqui, e não pode ser: o telefone de verdade vem
--     do JID alternativo do EVENTO (`key.remoteJidAlt`), que o banco não tem.
--     Inventar telefone a partir de um LID criaria uma pessoa que não existe.
--     As fantasmas ficam com `contraparte` NULA — e são o script das fantasmas
--     (`migrar_conversas_fantasma_lid.py`, migration 20260914_07) que as fecha.
-- -------------------------------------------------------------------------
UPDATE public.conversations c
   SET contraparte = regexp_replace(c.user_phone, '[^0-9]', '', 'g')
 WHERE c.contraparte IS NULL
   AND c.user_phone IS NOT NULL
   AND regexp_replace(c.user_phone, '[^0-9]', '', 'g') <> ''
   AND NOT (
         length(regexp_replace(c.user_phone, '[^0-9]', '', 'g')) >= 13
     AND left(regexp_replace(c.user_phone, '[^0-9]', '', 'g'), 2) <> '55'
   );

-- -------------------------------------------------------------------------
-- (c) O ÍNDICE ÚNICO PARCIAL
--
-- 🔴 SÓ APLIQUE ESTE BLOCO DEPOIS DE D0 = 0. Com duplicata viva, o
--    `CREATE UNIQUE INDEX` falha (23505) e leva a migration inteira junto.
--
-- 📊 Sem `CONCURRENTLY` porque a tabela é pequena: **879 linhas** em 14/09/2026
--    (BLOCO 0, premissa 8). Acima de ~50 mil linhas, use `CONCURRENTLY` — e aí
--    fora de transação.
--
-- ⚠️ As quatro cláusulas do WHERE são o contrato, e cada uma tem um motivo:
--      channel='whatsapp'   outros canais têm outra noção de contraparte
--      agent_id IS NULL     conversa do ATENDIMENTO; agente dedicado é outra linha
--      status <> 'closed'   o histórico não bloqueia o presente: uma conversa
--                           encerrada pode ter a mesma contraparte de uma nova
--      contraparte NOT NULL as fantasmas antigas não travam ninguém
--
-- 🔴 `company_id` é a PRIMEIRA coluna: a mesma pessoa pode falar com duas
--    corretoras, e isolar não é bloquear (CLAUDE.md §7; VERIFY V4).
-- -------------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS uq_conversations_contraparte_aberta
  ON public.conversations (company_id, contraparte)
  WHERE channel = 'whatsapp'
    AND agent_id IS NULL
    AND status <> 'closed'
    AND contraparte IS NOT NULL;

COMMENT ON INDEX public.uq_conversations_contraparte_aberta IS
  'SPEC-EXTRA-001.2 E2 — UMA conversa de WhatsApp aberta por contraparte, por '
  'corretora. 📊 É o que impede a conversa-fantasma nº 176 (eram 175 em '
  '13/09/2026, e uma nasceu enquanto a SPEC era escrita).';

-- =============================================================
-- D0 · 🔴 A CONSULTA QUE O ORQUESTRADOR RODA **ANTES** DO BLOCO (c)
-- =============================================================
--
--   select company_id, contraparte, count(*) as abertas,
--          array_agg(id order by created_at) as conversas
--     from public.conversations
--    where channel = 'whatsapp'
--      and agent_id is null
--      and status <> 'closed'
--      and contraparte is not null
--    group by company_id, contraparte
--   having count(*) > 1
--    order by count(*) desc;
--
--   esperado: 0 linhas  → aplique (c)
--   D0 > 0            → 🔴 NÃO aplique (c). A lista (company_id, contraparte,
--                        ids) vai para o relatório, e a decisão de o que fazer
--                        com cada par é registrada. ⛔ Nada é fechado em lote.
--   ⛔ A saída colada no relatório NÃO leva a coluna `contraparte` (é telefone):
--      cole `company_id`, a contagem e os `id`s. PII não entra em relatório.
--
-- =============================================================
-- VERIFY  (read-only; V3/V4 desfazem o que escrevem)
-- =============================================================
--
-- V1 · a coluna e o índice existem, com a cláusula WHERE do contrato
--
--   select column_name, data_type, is_nullable
--     from information_schema.columns
--    where table_schema='public' and table_name='conversations'
--      and column_name='contraparte';
--   -- esperado: 1 linha · text · YES
--
--   select indexdef from pg_indexes
--    where schemaname='public' and indexname='uq_conversations_contraparte_aberta';
--   -- esperado: CREATE UNIQUE INDEX … (company_id, contraparte)
--   --           WHERE ((channel='whatsapp') AND (agent_id IS NULL)
--   --                  AND (status <> 'closed') AND (contraparte IS NOT NULL))
--
-- V1b · o backfill fez o que prometeu, e o CONTROLE de que ele não fez demais
--
--   select count(*) filter (where contraparte is not null) as com_chave,
--          count(*) filter (where contraparte is null)     as sem_chave,
--          count(*) filter (where contraparte is null
--                             and user_phone is not null
--                             and length(regexp_replace(user_phone,'[^0-9]','','g')) > 13)
--            as fantasmas_sem_chave
--     from public.conversations;
--   -- 🔴 CONTROLE: `fantasmas_sem_chave` tem de ser > 0 (eram 175 em 14/09).
--   --    Se der 0, a cláusula de recusa do backfill não rodou e os LIDs
--   --    entraram como se fossem telefone — que é o defeito, não o conserto.
--
-- V2 · nenhuma duplicata aberta sobrou (a mesma D0, como número)
--
--   select count(*) from (
--     select 1 from public.conversations
--      where channel='whatsapp' and agent_id is null
--        and status <> 'closed' and contraparte is not null
--      group by company_id, contraparte having count(*) > 1) d;
--   -- esperado: 0
--
-- V3 · 🔴 ADVERSARIAL — a SEGUNDA conversa aberta da mesma contraparte é RECUSADA
--
--   begin;
--   do $$
--   declare v_company uuid; v_contraparte text; recusou boolean := false;
--   begin
--     select company_id, contraparte into v_company, v_contraparte
--       from public.conversations
--      where channel='whatsapp' and agent_id is null
--        and status <> 'closed' and contraparte is not null limit 1;
--     if v_company is null then raise notice 'V3 sem linha para testar'; return; end if;
--     begin
--       insert into public.conversations
--              (company_id, channel, agent_id, status, contraparte, session_id, user_phone)
--       values (v_company, 'whatsapp', null, 'open', v_contraparte,
--               'verify-v3-' || gen_random_uuid()::text, '5511900000001');
--     exception when unique_violation then recusou := true;
--     end;
--     raise notice 'V3 recusou_segunda_aberta=%', recusou;
--     -- esperado: t
--   end $$;
--   rollback;
--
-- V4 · 🔴 O PAR — a MESMA contraparte em OUTRA corretora é ACEITA
--      (o isolamento não pode virar bloqueio: CLAUDE.md §7)
--
--   begin;
--   do $$
--   declare v_a uuid; v_b uuid; v_contraparte text; aceitou boolean := false;
--   begin
--     select company_id, contraparte into v_a, v_contraparte
--       from public.conversations
--      where channel='whatsapp' and agent_id is null
--        and status <> 'closed' and contraparte is not null limit 1;
--     select id into v_b from public.companies where id <> v_a limit 1;
--     if v_a is null or v_b is null then raise notice 'V4 sem duas corretoras'; return; end if;
--     begin
--       insert into public.conversations
--              (company_id, channel, agent_id, status, contraparte, session_id, user_phone)
--       values (v_b, 'whatsapp', null, 'open', v_contraparte,
--               'verify-v4-' || gen_random_uuid()::text, '5511900000001');
--       aceitou := true;
--     exception when unique_violation then aceitou := false;
--     end;
--     raise notice 'V4 outra_corretora_aceita=%', aceitou;
--     -- esperado: t
--   end $$;
--   rollback;
--
-- V5 · e o PAR do `status`: conversa FECHADA não bloqueia a nova
--      (mesmo roteiro do V4, com a primeira em `status='closed'` — esperado: t)
--
-- =============================================================
-- ROLLBACK
-- =============================================================
--
--   drop index if exists public.uq_conversations_contraparte_aberta;
--   -- 🔴 A COLUNA `contraparte` FICA (expand-first). Os escritores continuam
--   --    preenchendo-a e nenhum leitor quebra: sem o índice, ela é só um dado
--   --    a mais. Derrubar a coluna obrigaria a um segundo backfill na volta.
-- =============================================================
