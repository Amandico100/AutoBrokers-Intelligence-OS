-- =============================================================
-- MIGRATION: spec064_backfill_entrega
-- SPEC:      SPEC-064 — Bloco E (a entrega)
-- AUTOR:     lider tecnico            DATA: 2026-08-02
-- OBJETIVO:  as publicacoes anteriores ao executor de entrega param de dizer
--            'pending' sobre algo que esta na tela do corretor.
--
-- APPLY:     marca como 'sent' as publicacoes que existiam antes do
--            executor, com o motivo real: elas ESTAO no painel, e nenhum
--            outro canal foi tentado porque nao havia quem tentasse.
--
-- VERIFY:    select delivery_status, count(*)
--              from public.briefing_publications group by 1;
--            -- esperado: nenhuma linha 'pending' anterior a 2026-08-02
--
--            select delivery_detail->>'origem'
--              from public.briefing_publications
--             where delivery_status = 'sent' limit 1;
--            -- esperado: 'backfill SPEC-064 Bloco E'
--
-- ROLLBACK:  update public.briefing_publications
--               set delivery_status = 'pending', delivery_detail = null
--             where delivery_detail->>'origem' = 'backfill SPEC-064 Bloco E';
--
-- EXPAND-FIRST: sim — nenhuma coluna criada, nenhuma removida.
-- DESTRUTIVA:   nao
-- =============================================================
--
-- POR QUE ESTE BACKFILL EXISTE
-- ----------------------------
-- 📊 Medido em 02/08/2026: 26 de 26 publicacoes com `delivery_status =
-- 'pending'`, porque `delivery_policy.decidir()` tinha zero chamadores. Nao
-- havia bug: havia um fio solto entre duas pecas prontas.
--
-- Com o executor ligado, as publicacoes NOVAS terminam com estado e motivo.
-- As 26 antigas ficariam 'pending' para sempre — e 'pending' sobre uma coisa
-- que o corretor ve na tela de Entregas nao e "ainda nao entregue": e o
-- sistema nao sabendo responder.
--
-- O que este backfill afirma e verdade verificavel:
--   * elas ESTAO no painel — a publicacao existir E a entrega no dashboard
--   * nenhum outro canal foi tentado — nao havia quem tentasse
--
-- O que ele NAO faz e inventar entrega em canal nenhum. E-mail e WhatsApp
-- continuam sem registro de envio, porque envio nao houve.

update public.briefing_publications
   set delivery_status = 'sent',
       delivery_detail = jsonb_build_object(
         'origem', 'backfill SPEC-064 Bloco E',
         'decidido_em', now()::text,
         'motivo_da_politica',
           'publicado antes de o executor de entrega existir; nenhum canal alem do painel foi tentado',
         'push', false,
         'canais', jsonb_build_array(
           jsonb_build_object(
             'canal', 'dashboard',
             'ok', true,
             'motivo', 'esta no painel, em Entregas')
         )
       )
 where delivery_status = 'pending';

-- SEM CORTE POR DATA — e isso foi correcao.
--
-- A primeira versao filtrava `created_at < '2026-08-02'`, e sobraram tres
-- publicacoes: as de hoje, geradas pelo ciclo diario horas antes desta
-- migration. O corte por data supunha que "hoje" ja tinha executor.
--
-- Nao tinha. O executor nasce NESTE commit e nem esta em producao. O criterio
-- correto nao e a data: e **nenhuma destas passou por um executor que nao
-- existia**. Toda publicacao 'pending' no momento do backfill esta na mesma
-- situacao, e o motivo gravado vale para todas.
--
-- As publicacoes seguintes nao dependem deste backfill: elas nascem com
-- estado e motivo porque `publicar()` chama o executor.
