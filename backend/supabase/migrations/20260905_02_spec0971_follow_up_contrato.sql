-- =============================================================================
-- SPEC-097.1 · U3.3 — O CONTRATO DO AUXILIAR `follow-up-whatsapp`
--
-- 🔴 MIGRATION DE DADO, não de schema: nenhuma tabela, coluna, índice ou
--    constraint é criada, alterada ou removida. Ela escreve TRÊS chaves dentro
--    de um `jsonb` que já existe (`auxiliary_templates.default_config`).
--
-- 📊 POR QUE ELA EXISTE, medido em 05/09/2026 (`reality-report-0971.md` §1):
--    o Auxiliar `follow-up-whatsapp` não está instalado em nenhum tenant (0/2),
--    o `FOLLOWUP_SYSTEM_PROMPT` é constante de CÓDIGO (`auxiliaries.py:502`),
--    `default_config` NUNCA é lido por aquele endpoint e `dry_run` é
--    hardcoded. Ou seja: quem abre a tela do Auxiliar não tem uma linha que
--    diga o que ele faz e o que ele NÃO faz.
--
-- ⚠️ E é só CONTRATO. O comportamento continua no código (E12): esta linha
--    não liga nada, não agenda nada e não autoriza envio. Ela DECLARA, para
--    quem lê o catálogo, as três verdades da SPEC:
--
--        gatilho    "manual"   — 🧑 decisão do Founder: o acompanhamento é uma
--                               FASE do atendimento, não uma Rotina; o Auxiliar
--                               segue sendo o rascunho que a atendente pede.
--        le_espera  true       — o rascunho lê `work_waits` e diz de quem se
--                               está esperando (U3.3).
--        envia      false      — ⛔ nada sai. `dry_run` é o contrato, e agora
--                               ele aparece TAMBÉM no corpo da resposta (E11).
--
-- ⛔ NÃO APLICADA PELO BUILDER (trava do pacote). Quem aplica é o Founder.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- APPLY
-- -----------------------------------------------------------------------------
-- 🔴 IDEMPOTENTE por construção: `jsonb || jsonb` sobrescreve a chave
--    `contrato` inteira, então rodar duas vezes dá exatamente o mesmo estado.
-- 🔴 EXPAND-FIRST: acrescenta uma chave nova; nenhuma chave existente é lida,
--    movida ou apagada, e um código antigo que ignore `contrato` segue igual.
UPDATE public.auxiliary_templates
   SET default_config = COALESCE(default_config, '{}'::jsonb)
                        || jsonb_build_object(
                             'contrato',
                             jsonb_build_object(
                               'gatilho',   'manual',
                               'le_espera', true,
                               'envia',     false
                             )
                           )
 WHERE slug = 'follow-up-whatsapp';

-- -----------------------------------------------------------------------------
-- VERIFY  — tem de devolver UMA linha, com as três chaves e `envia = false`
-- -----------------------------------------------------------------------------
-- SELECT slug,
--        default_config -> 'contrato' ->> 'gatilho'   AS gatilho,
--        default_config -> 'contrato' ->> 'le_espera' AS le_espera,
--        default_config -> 'contrato' ->> 'envia'     AS envia
--   FROM public.auxiliary_templates
--  WHERE slug = 'follow-up-whatsapp';
--
-- esperado:  follow-up-whatsapp | manual | true | false
--
-- ⚠️ CONTROLE (o que dá direito à conclusão): a MESMA consulta ANTES do APPLY
--    tem de devolver as três colunas NULAS. Se já vierem preenchidas, alguém
--    aplicou antes — e aí o que se está medindo é a corrida anterior, não esta.

-- -----------------------------------------------------------------------------
-- ROLLBACK — devolve o `default_config` ao que era, sem tocar no resto
-- -----------------------------------------------------------------------------
-- UPDATE public.auxiliary_templates
--    SET default_config = (COALESCE(default_config, '{}'::jsonb) - 'contrato')
--  WHERE slug = 'follow-up-whatsapp';
--
-- VERIFY do ROLLBACK: a consulta do VERIFY volta a devolver NULO nas três.
