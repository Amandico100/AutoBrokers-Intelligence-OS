-- =============================================================================
-- MIGRATION: spec_extra0016_redigir_preview_cortado
-- SPEC:      SPEC-EXTRA-001.6 — B4.4, complemento da 20260914_04
-- AUTOR:     Fable 5.1 (orquestrador)               DATA: 2026-09-14
-- OBJETIVO:  redigir o telefone CORTADO no fim de um `output_preview`
--
-- APPLY:     um UPDATE numa linha, ancorado no FIM do texto.
-- VERIFY:    V0 abaixo (esperado 0) e o V5 da _04 (esperado 0).
-- ROLLBACK:  nao existe — mesma justificativa da _03 e da _04 (PII de segurado
--            que nunca deveria estar ali; desfazer exigiria guardar uma copia).
--
-- EXPAND-FIRST: nao se aplica   ·   DESTRUTIVA: sim (altera dado)   ·   IDEMPOTENTE: sim
--
-- 📊 MEDIDO EM 14/09/2026, depois do APPLY da _04 (VERIFY V2 = 1):
--    `output_preview` e `output[:500]` (routine_engine.py:348). Numa das 5
--    linhas o corte de 500 caracteres caiu NO MEIO do telefone: sobraram
--    "WhatsApp: " + 5 digitos no fim do texto (id 17dfd8a9…, 492 chars), e a
--    regex da _04 exige 8 a 15 digitos. A regex aqui exige de 1 a 7 digitos
--    E o fim da string ($): so o resto cortado casa; um telefone inteiro nunca.
-- =============================================================================
-- ----------------------------------------------------------------- APPLY -----
update public.routine_runs
   set output_preview = regexp_replace(output_preview, '(WhatsApp: )[0-9]{1,7}$', '\1•••')
 where id = '17dfd8a9-0739-4191-913b-e6fb19ed2213'
   and output_preview ~ 'WhatsApp: [0-9]{1,7}$';
-- ---------------------------------------------------------------- VERIFY -----
-- V0) select count(*) from public.routine_runs r join public.routines t on t.id=r.routine_id
--      where t.config->>'kind'='billing_collection' and r.output_preview ~ 'WhatsApp: [0-9]';   -- esperado 0
-- V5 da _04) as duas colunas, as quatro regexes                                                   -- esperado 0
-- =============================================================================
