-- =============================================================
-- MIGRATION: 20260923_04_spec116_mapa_onda_a
-- SPEC:      SPEC-116 — F6 · U13 (mapa de modelos, Onda A — PARCIAL)
-- AUTOR:     gerente SPEC-116 (Opus 5.5)      DATA: 2026-09-23
-- OBJETIVO:  trocar SÓ as rotas que a bancada provou (memória, visão,
--            portal_decisao) e corrigir a superfície de API da gpt-5.6-terra.
--            Chat principal, atendimento, dispatch e cobrança NÃO mudam: a
--            bancada parou por crédito zerado antes de medir N2 e dispatch.
--
-- EVIDÊNCIA (📊 23/09/2026, eval_case_results via eval_runs.gatilho='bancada',
--            reconstruída pelo gerente por SELECT independente do relatório):
--   memoria        gpt-4o-mini 32/45 (71,1%) · gpt-6-luna low 39/45 (86,7%)
--   visao          gpt-4o-mini 28/30 · gpt-6-luna low 30/30 · gpt-6-sol low 30/30
--                  (imagens SINTÉTICAS — evidência fraca, declarada)
--   portal_decisao gpt-4o 38/41 (92,7%) · gpt-4o-mini 39/45 · gpt-6-luna medium 45/45 ·
--                  gpt-6-sol low 43/43 · gpt-6-sol medium 43/43
--   D-116-18: Onda A = potência primeiro → portal e visão em GPT-6 Sol (empate de
--   qualidade com a Luna; margem para o P0); memória (P1, volume) em Luna low.
--   Reserva: NULA — os braços Anthropic não foram medidos (crédito zerado).
--   gpt-5.6-terra: 📊 100% dos casos com tools deram 400 em chat_completions com
--   esforço → a superfície correta é a Responses API.
--
-- APPLY:     3 UPDATEs em llm_papeis (o trigger grava llm_papeis_historico e
--            sobe a versão) + 1 UPDATE em llm_pricing (terra).
--
-- VERIFY:
--   select papel, modelo_primario, esforco, versao, motivo from public.llm_papeis
--    where papel in ('memoria','visao','portal_decisao') order by 1;
--   -- esperado: memoria gpt-6-luna low v2 · portal_decisao gpt-6-sol medium v2 · visao gpt-6-sol low v2
--   select papel, versao, linha_anterior->>'modelo_primario' antes, linha_nova->>'modelo_primario' depois
--     from public.llm_papeis_historico where papel in ('memoria','visao','portal_decisao') order by 1;
--   -- esperado: 3 linhas, antes gpt-4o-mini / gpt-4o / gpt-4o-mini
--   select model_name, api_surface, capacidades->>'responses_obrigatoria_com_tools'
--     from public.llm_pricing where model_name='gpt-5.6-terra';
--   -- esperado: responses · true
--
-- ROLLBACK:  (escrito ANTES; volta cada rota à linha anterior — o trigger registra a volta)
--   update public.llm_papeis set provider='openai', modelo_primario='gpt-4o-mini', esforco=null,
--     motivo='rollback SPEC-116 mapa onda A', atualizado_por='rollback' where papel='memoria';
--   update public.llm_papeis set provider='openai', modelo_primario='gpt-4o-mini', esforco=null,
--     motivo='rollback SPEC-116 mapa onda A', atualizado_por='rollback' where papel='visao';
--   update public.llm_papeis set provider='openai', modelo_primario='gpt-4o', esforco=null,
--     motivo='rollback SPEC-116 mapa onda A', atualizado_por='rollback' where papel='portal_decisao';
--   update public.llm_pricing set api_surface='chat_completions',
--     capacidades = capacidades - 'responses_obrigatoria_com_tools' where model_name='gpt-5.6-terra';
--
-- EXPAND-FIRST: não se aplica (só DADO de configuração; nenhuma estrutura muda)
-- DESTRUTIVA:   não — o histórico guarda a linha anterior de cada rota
-- =============================================================

update public.llm_papeis
   set provider = 'openai', modelo_primario = 'gpt-6-luna', esforco = 'low',
       motivo = 'SPEC-116 Onda A: bancada 23/09 memoria N1 luna-low 86,7% vs gpt-4o-mini 71,1% (D-116-18)',
       atualizado_por = 'migration 20260923_04'
 where papel = 'memoria' and modelo_primario = 'gpt-4o-mini';

update public.llm_papeis
   set provider = 'openai', modelo_primario = 'gpt-6-sol', esforco = 'low',
       motivo = 'SPEC-116 Onda A: bancada 23/09 visao N1 sol-low 30/30 vs gpt-4o-mini 28/30 (sinteticas; D-116-18 potencia primeiro)',
       atualizado_por = 'migration 20260923_04'
 where papel = 'visao' and modelo_primario = 'gpt-4o-mini';

update public.llm_papeis
   set provider = 'openai', modelo_primario = 'gpt-6-sol', esforco = 'medium',
       motivo = 'SPEC-116 Onda A: bancada 23/09 portal N1 sol-medium 43/43 vs gpt-4o 38/41; luna-medium 45/45 fica como desafiante da Onda B (D-116-18)',
       atualizado_por = 'migration 20260923_04'
 where papel = 'portal_decisao' and modelo_primario = 'gpt-4o';

update public.llm_pricing
   set api_surface = 'responses',
       capacidades = coalesce(capacidades, '{}'::jsonb) || '{"responses_obrigatoria_com_tools": true}'::jsonb,
       notas = coalesce(notas || ' · ', '') || 'SPEC-116 F6: 400 em chat_completions com tools+esforco (bancada 23/09)',
       updated_at = now()
 where model_name = 'gpt-5.6-terra';
