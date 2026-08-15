-- ===========================================================================
-- SPEC-071 · BLOCO 4.4 — o acervo passa a saber DE QUEM é cada conversa
-- ===========================================================================
--
-- 📊 O ACHADO (medido em 15/08/2026, projeto dcajcvlzcjbmyapmklil):
--
--     attendance_transcripts ............ 150.734 linhas
--     com insurer_key preenchido ........ 0        (zero, em 100% delas)
--     canais de URA identificados ....... 32
--     mensagens desses canais ........... ~8.350
--
-- O sistema captura e não sabe o que capturou. A consequência não é estética:
-- `espelho_chat.deve_espelhar` recusa mensagem de seguradora com
-- `if e_grupo or e_seguradora: return False`, e `e_seguradora` vem de
-- `bool(linha.get("insurer_key"))`. Com a coluna 100% nula, `bool(None)` é
-- False em TODAS as linhas — o portão existe e nunca dispara.
--
-- 📊 Resultado medido na mesa das atendentes hoje:
--     Resulta  ... 10,9% do que ela vê são conversas de robô (714 mensagens)
--     AutoFleet ..  6,8%                                      (652 mensagens)
--
-- Nenhuma delas é cliente. A Saionara abre a mesa e encontra a fila de espera
-- da MAPFRE, o menu da Maxpar e a pesquisa de satisfação da Localiza no meio
-- das pessoas que precisam dela.
--
-- ---------------------------------------------------------------------------
-- O QUE ESTA MIGRATION FAZ — e o que ela DELIBERADAMENTE não faz
-- ---------------------------------------------------------------------------
-- FAZ:  cria o índice que torna possível achar e marcar essas linhas.
-- NÃO FAZ: não escreve `insurer_key` em linha nenhuma.
--
-- A marcação é do código (backfill governado, com a allowlist como única fonte
-- de verdade), não de um UPDATE cravado aqui. Um UPDATE em SQL com a lista de
-- telefones digitada à mão criaria uma SEGUNDA fonte de verdade sobre quem é
-- seguradora — exatamente o motor paralelo que o CLAUDE.md §5 proíbe. Daqui a
-- dois meses ninguém saberia qual das duas manda.
--
-- ---------------------------------------------------------------------------
-- POR QUE O ÍNDICE É PRECISO ANTES
-- ---------------------------------------------------------------------------
-- 📊 Os três índices que existem hoje (20260719_01_spec040, linhas 27-32):
--     ux_attendance_transcripts_dedupe (observer_number, message_id)
--     ix_attendance_transcripts_lookup (company_id, counterparty, wa_timestamp)
--     ix_attendance_transcripts_created (created_at)
--
-- Nenhum atende "me dê as linhas desta corretora, desta contraparte, que ainda
-- não têm dono". O `lookup` chega perto, mas ordena por `wa_timestamp` e não
-- filtra por `insurer_key` — o planejador varre e descarta.
--
-- ⚠️ E o custo de varrer não é abstrato: este banco foi RESTRINGIDO em 07/08
-- por Egress. Varredura de 150 mil linhas repetida a cada lote do backfill é a
-- forma mais rápida de repetir aquele incidente com outro nome.
--
-- ---------------------------------------------------------------------------
-- APPLY
-- ---------------------------------------------------------------------------
--   · ix_attendance_transcripts_sem_dono — parcial, só as linhas SEM dono
--   · ix_attendance_transcripts_por_seguradora — as linhas COM dono
--
-- Os dois são CREATE INDEX IF NOT EXISTS: reaplicar não faz nada.
--
-- ⚠️ Sem CONCURRENTLY, de propósito. O `psql` do Supabase MCP roda em
-- transação implícita e CONCURRENTLY é recusado nela. 📊 A tabela tem 150.734
-- linhas — um índice parcial nessa escala leva segundos, e a janela é a
-- madrugada. Se um dia a tabela for grande de verdade, este comentário é o
-- aviso: aí é CONCURRENTLY, fora de transação, e não este arquivo.
--
-- ---------------------------------------------------------------------------
-- VERIFY  (esperado à direita)
-- ---------------------------------------------------------------------------
--   SELECT count(*) FROM pg_indexes
--    WHERE tablename='attendance_transcripts'
--      AND indexname IN ('ix_attendance_transcripts_sem_dono',
--                        'ix_attendance_transcripts_por_seguradora');   -- 2
--
--   EXPLAIN SELECT id FROM public.attendance_transcripts
--    WHERE company_id = '00000000-0000-0000-0000-000000000000'
--      AND insurer_key IS NULL AND counterparty = '551140029000';
--                                        -- deve dizer "Index Scan", nao "Seq Scan"
--
--   SELECT count(*) FROM public.attendance_transcripts
--    WHERE insurer_key IS NOT NULL;      -- 0 — esta migration NAO marca nada
--
-- ---------------------------------------------------------------------------
-- ROLLBACK
-- ---------------------------------------------------------------------------
--   DROP INDEX IF EXISTS public.ix_attendance_transcripts_sem_dono;
--   DROP INDEX IF EXISTS public.ix_attendance_transcripts_por_seguradora;
--
--   Sem perda: índice é estrutura derivada. Nenhuma linha é tocada por este
--   arquivo, então não existe dado a restaurar.
-- ===========================================================================

-- (1) As linhas que o backfill precisa ENCONTRAR.
--
-- Parcial (`WHERE insurer_key IS NULL`) por dois motivos: é uma fração da
-- tabela, e ele ENCOLHE conforme o backfill avança — o índice fica mais barato
-- exatamente enquanto está sendo mais usado. Um índice cheio faria o contrário.
CREATE INDEX IF NOT EXISTS ix_attendance_transcripts_sem_dono
    ON public.attendance_transcripts (company_id, counterparty)
    WHERE insurer_key IS NULL;

-- (2) As linhas que JÁ têm dono — a leitura do BLOCO 5.
--
-- A auditoria da realidade pergunta "me dê tudo que a MAPFRE falou com esta
-- corretora, em ordem de tempo". Sem isto, cada seguradora auditada custa uma
-- varredura da tabela inteira.
CREATE INDEX IF NOT EXISTS ix_attendance_transcripts_por_seguradora
    ON public.attendance_transcripts (company_id, insurer_key, wa_timestamp DESC)
    WHERE insurer_key IS NOT NULL;

COMMENT ON COLUMN public.attendance_transcripts.insurer_key IS
    'Quem é a contraparte, quando ela NÃO é um cliente: seguradora, assistência, '
    'locadora de carro reserva, reguladora ou rede de reparo. NULL = pessoa, ou '
    'ainda não sabemos — e os dois casos são diferentes. Quem preenche é a '
    'allowlist (observer_intake.insurer_allowlist), fonte única. Preenchido, '
    'este campo tira a conversa da mesa da atendente via deve_espelhar.';
