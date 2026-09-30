-- =============================================================
-- MIGRATION: 20260930_01_spec122_gpt_6_1_sol
-- SPEC:      SPEC-122 — F0 · o GPT-6.1 Sol sucede o Sol 6
-- AUTOR:     builder F0 (Opus 5.5 xhigh)      DATA: 2026-09-30
-- OBJETIVO:  cadastrar `gpt-6.1-sol` no catálogo governado (APPROVED), trocar
--            TODA rota que usa `gpt-6-sol` (primário ou reserva) pelo 6.1 com o
--            MESMO esforço, e deixar o `gpt-6-sol` DEPRECATED → gpt-6.1-sol.
--            Ordem do Founder (30/09/2026): o GPT-6.1 Sol no lugar do Sol 6 onde
--            usamos Sol, se real, com id correto, preço equivalente e compatível.
--            Troca de GERAÇÃO, não de esforço: nenhum esforço muda. Luna, Astra,
--            Opus 5.5 e Sonnet 5.5 não mudam. O dispatch continua Opus 5.5
--            primário; só a reserva dele (gpt-6-sol high) vira gpt-6.1-sol high.
--
-- EVIDÊNCIA (laudo do pesquisador, scratchpad s122/pesquisa/LAUDO-MODELOS.md):
--   📊 30/09/2026 GET /v1/models/gpt-6.1-sol → 200 · created 2026-09-27T23:47:54Z ·
--      shutdown_date null. GET /v1/models/gpt-6-sol → 200 · shutdown_date null;
--      a página de deprecations (30/09) NÃO o lista → DEPRECATED, não BLOCKED.
--   📊 30/09/2026 doc oficial (developers.openai.com/api/docs/pricing e
--      /models/gpt-6.1-sol): input 2 · cached input 0,10 · cache write 2,50 ·
--      output 10 por MTok; > 272K: 4 / 0,20 / 5 / 15. Janela 1.050.000, saída
--      128.000. Esforços low·medium(default)·high·xhigh·max — SEM `none`.
--      Entrada: texto e imagem (PDF não listado → pdf=false). Tools no Chat
--      Completions só sem tools → Responses obrigatória com tools. Sem
--      temperature/top_p.
--   📊 30/09/2026 canário real (canario_out.json): effort none → HTTP 400
--      unsupported_value; tool_choice forçado ACEITO; structured strict OK;
--      tool ida-e-volta com store=false OK; visão 512×256 OK.
--   📊 30/09/2026 (SELECT, antes, SET TRANSACTION READ ONLY): llm_pricing sem
--      `gpt-6.1-sol`; `gpt-6-sol` APPROVED, cached_input_multiplier 0.10,
--      substituido_por NULL; nenhuma linha com substituido_por='gpt-6-sol'.
--      llm_papeis com gpt-6-sol: 7 primários — atendimento high · chat_principal
--      medium · juiz_eval medium · portal_decisao medium · subagente medium ·
--      visao medium · visao_documento medium — e 1 reserva: dispatch high.
--      agents/companies com llm_model 'gpt-6%': 0 · memory_settings: só
--      gpt-4o-mini · nenhuma função nem column_default do banco cita 'gpt-6-sol'.
--
-- 🔴 cached_input_multiplier = 0.05 (0,10 / 2) — NÃO o 0.10 do Sol 6: copiar
--    faria o ledger cobrar o cache em dobro.
-- 🔴 niveis_de_esforco SEM `none`: o trigger `llm_papeis_so_modelo_governado` e o
--    `model_policy._validar` recusam `none` ANTES da rede (a API daria 400).
--
-- APPLY (ordem importa: o trigger só aceita rota para modelo APPROVED):
--   A. INSERT de gpt-6.1-sol (APPROVED); A2 põe a linha no valor desta
--      migration se ela já existia.
--   B. rotas: modelo_primario / modelo_reserva 'gpt-6-sol' → 'gpt-6.1-sol', o
--      MESMO esforço, motivo e atualizado_por novos (o trigger de histórico
--      grava a linha anterior e sobe a versão).
--   C. agents/companies com llm_model 'gpt-6-sol' → 'gpt-6.1-sol' (📊 0 linhas
--      hoje; fica por idempotência).
--   D. gpt-6-sol → DEPRECATED, substituido_por 'gpt-6.1-sol' + nota.
--   E. asserção: aborta a migration inteira se sobrar rota em gpt-6-sol, rota
--      em modelo não-APPROVED, ou se a linha nova vier com `none` / cache 0.10.
--
-- VERIFY:
--   select model_name, lifecycle, substituido_por, input_price_per_million,
--          output_price_per_million, cached_input_multiplier, cache_write_multiplier,
--          input_price_long, output_price_long, limiar_contexto_longo,
--          capacidades->'niveis_de_esforco' niveis, capacidades->>'tool_choice_forcado_ok' tc,
--          capacidades->>'sampling_ok' s, capacidades->>'pdf' pdf, preco_verificado_em
--     from public.llm_pricing where model_name in ('gpt-6-sol','gpt-6.1-sol') order by 1;
--   -- esperado: gpt-6-sol    DEPRECATED gpt-6.1-sol 2 10 0.10 1.25 4 15 272000 [none..max] ...
--   --           gpt-6.1-sol  APPROVED   NULL        2 10 0.05 1.25 4 15 272000
--   --                        ["low","medium","high","xhigh","max"] true false false 2026-09-30
--   select papel, provider, modelo_primario, esforco, provider_reserva, modelo_reserva,
--          esforco_reserva, versao
--     from public.llm_papeis where 'gpt-6.1-sol' in (modelo_primario, modelo_reserva) order by 1;
--   -- esperado 8 linhas: atendimento high (reserva opus 5.5) · chat_principal medium
--   --   (reserva opus 5.5) · dispatch opus 5.5 | openai gpt-6.1-sol high · juiz_eval medium ·
--   --   portal_decisao medium (reserva opus 5.5) · subagente medium · visao medium ·
--   --   visao_documento medium
--   select count(*) from public.llm_papeis where 'gpt-6-sol' in (modelo_primario, modelo_reserva);
--   -- esperado 0
--   select papel, versao, motivo from public.llm_papeis_historico
--    where alterado_por = 'migration 20260930_01' order by papel;   -- esperado 8
--   -- a trava de rota recusa o Sol 6 e o esforço none no 6.1, e aceita o 6.1 high
--   -- (SAVEPOINT; nada fica gravado):
--   do $$
--   declare v_a int; v_a2 int; recusou_6 boolean := false; recusou_none boolean := false;
--   begin
--     select versao into v_a from public.llm_papeis where papel = 'juiz_eval';
--     begin
--       update public.llm_papeis set provider='openai', modelo_primario='gpt-6-sol', esforco='medium'
--        where papel='juiz_eval';
--     exception when check_violation then recusou_6 := true; end;
--     begin
--       update public.llm_papeis set provider='openai', modelo_primario='gpt-6.1-sol', esforco='none'
--        where papel='juiz_eval';
--     exception when check_violation then recusou_none := true; end;
--     begin  -- CONTROLE: o 6.1 em high PASSA (e é desfeito pelo raise dentro do sub-bloco)
--       update public.llm_papeis set provider='openai', modelo_primario='gpt-6.1-sol', esforco='high'
--        where papel='juiz_eval';
--       raise exception using errcode = 'P0001', message = 'desfaz-controle';
--     exception when sqlstate 'P0001' then null; end;
--     select versao into v_a2 from public.llm_papeis where papel = 'juiz_eval';
--     if not recusou_6 or not recusou_none or v_a is distinct from v_a2 then
--       raise exception 'VERIFY 20260930_01 FALHOU: recusou_6=% recusou_none=% versao % -> %',
--         recusou_6, recusou_none, v_a, v_a2;
--     end if;
--     raise notice 'VERIFY 20260930_01 OK: Sol 6 recusado, none recusado no 6.1, 6.1 high aceito, versão intocada';
--   end $$;
--
-- ROLLBACK:  (escrito ANTES de aplicar)
--   -- D. o Sol 6 volta a APPROVED ANTES das rotas (o trigger exige APPROVED)
--   update public.llm_pricing
--      set lifecycle = 'APPROVED', substituido_por = null,
--          notas = replace(notas, ' · DEPRECATED: Founder 30/09/2026 — SPEC-122: sucedido pelo gpt-6.1-sol (mesmo preço; cache 0,10)', ''),
--          updated_at = now()
--    where model_name = 'gpt-6-sol';
--   -- B. as 8 rotas voltam (esforço intocado pela ida, então intocado pela volta)
--   update public.llm_papeis set modelo_primario = 'gpt-6-sol',
--          motivo = 'ROLLBACK 20260930_01 — volta ao Sol 6', atualizado_por = 'rollback 20260930_01'
--    where modelo_primario = 'gpt-6.1-sol'
--      and papel in ('atendimento','chat_principal','juiz_eval','portal_decisao','subagente',
--                    'visao','visao_documento');
--   update public.llm_papeis set modelo_reserva = 'gpt-6-sol',
--          motivo = 'ROLLBACK 20260930_01 — volta ao Sol 6', atualizado_por = 'rollback 20260930_01'
--    where modelo_reserva = 'gpt-6.1-sol' and papel = 'dispatch';
--   -- C. (0 linhas na ida — nada a desfazer)
--   -- A. só se nenhuma rota/agente o usar (a FK de llm_papeis recusa o delete se usar)
--   delete from public.llm_pricing where model_name = 'gpt-6.1-sol';
--   delete from supabase_migrations.schema_migrations where name = 'spec122_gpt_6_1_sol';
--   -- e regerar o snapshot: python scripts/gerar_snapshot_de_modelos.py --banco
--
-- EXPAND-FIRST: sim — linha nova no catálogo antes de qualquer referência a ela;
--               nenhuma coluna, CHECK ou trava muda.
-- DESTRUTIVA:   não — 8 rotas trocadas (histórico em llm_papeis_historico) e 1
--               lifecycle rebaixado; tudo reversível pelo ROLLBACK acima.
-- =============================================================

-- -------------------------------------------------------------
-- A. o GPT-6.1 Sol entra no catálogo
-- -------------------------------------------------------------
insert into public.llm_pricing (model_name, provider, display_name, input_price_per_million,
  output_price_per_million, unit, is_active, sell_multiplier, cache_read_multiplier,
  cache_write_multiplier, cached_input_multiplier, input_price_long, output_price_long,
  limiar_contexto_longo, lifecycle, tipo, api_surface, capacidades, classes_de_dado,
  preco_verificado_em, fonte_preco_url, notas)
values ('gpt-6.1-sol', 'openai', 'GPT-6.1 Sol', 2, 10, 'token', true, 2.68,
        0.05, 1.25, 0.05, 4, 15, 272000, 'APPROVED', 'chat', 'responses',
        '{"tools": true, "vision": true, "pdf": false, "contexto": 1050000,
          "max_output": 128000, "sampling_ok": false,
          "reasoning_param": "reasoning.effort",
          "niveis_de_esforco": ["low", "medium", "high", "xhigh", "max"],
          "raciocinio_ida_e_volta": true, "tool_choice_forcado_ok": true,
          "responses_obrigatoria_com_tools": true}'::jsonb,
        array['publico', 'interno', 'pii'], date '2026-09-30',
        'https://developers.openai.com/api/docs/pricing',
        'lançado 29/09/2026 (DevDay); cadastrado na SPEC-122 F0 (Founder 30/09/2026: sucede o gpt-6-sol). '
        || 'cached 0,10 · cache write 2,50 · >272K 4/0,20/5/15. Default effort medium; `none` -> 400 '
        || '(canário 30/09). Chat Completions: só sem tools. PDF não listado como entrada. '
        || 'Fonte técnica: https://developers.openai.com/api/docs/models/gpt-6.1-sol')
on conflict (model_name) do nothing;

-- A2. idempotente: se a linha já existia, ela fica igual à desta migration
update public.llm_pricing
   set provider = 'openai', display_name = 'GPT-6.1 Sol', lifecycle = 'APPROVED', tipo = 'chat',
       api_surface = 'responses', unit = 'token', sell_multiplier = 2.68,
       input_price_per_million = 2, output_price_per_million = 10,
       cache_read_multiplier = 0.05, cache_write_multiplier = 1.25, cached_input_multiplier = 0.05,
       input_price_long = 4, output_price_long = 15, limiar_contexto_longo = 272000,
       capacidades = '{"tools": true, "vision": true, "pdf": false, "contexto": 1050000,
          "max_output": 128000, "sampling_ok": false,
          "reasoning_param": "reasoning.effort",
          "niveis_de_esforco": ["low", "medium", "high", "xhigh", "max"],
          "raciocinio_ida_e_volta": true, "tool_choice_forcado_ok": true,
          "responses_obrigatoria_com_tools": true}'::jsonb,
       classes_de_dado = array['publico', 'interno', 'pii'], substituido_por = null,
       retirada_em = null, preco_verificado_em = date '2026-09-30',
       fonte_preco_url = 'https://developers.openai.com/api/docs/pricing',
       is_active = true, updated_at = now()
 where model_name = 'gpt-6.1-sol';

-- -------------------------------------------------------------
-- B. toda rota do Sol 6 passa ao 6.1 — o MESMO esforço
-- -------------------------------------------------------------
update public.llm_papeis
   set modelo_primario = 'gpt-6.1-sol',
       motivo = 'SPEC-122 F0 · Founder 30/09/2026 — GPT-6.1 Sol sucede o Sol 6 (mesmo esforço)',
       atualizado_por = 'migration 20260930_01'
 where modelo_primario = 'gpt-6-sol';

update public.llm_papeis
   set modelo_reserva = 'gpt-6.1-sol',
       motivo = 'SPEC-122 F0 · Founder 30/09/2026 — GPT-6.1 Sol sucede o Sol 6 (mesmo esforço)',
       atualizado_por = 'migration 20260930_01'
 where modelo_reserva = 'gpt-6-sol';

-- -------------------------------------------------------------
-- C. nenhum agente nem corretora guarda o Sol 6 (📊 0 linhas em 30/09)
-- -------------------------------------------------------------
update public.agents    set llm_model = 'gpt-6.1-sol' where llm_model = 'gpt-6-sol';
update public.companies set llm_model = 'gpt-6.1-sol' where llm_model = 'gpt-6-sol';

-- -------------------------------------------------------------
-- D. o Sol 6 fica DEPRECATED (a bancada ainda o mede; a produção, não)
-- -------------------------------------------------------------
update public.llm_pricing
   set lifecycle = 'DEPRECATED',
       substituido_por = 'gpt-6.1-sol',
       notas = coalesce(notas, '') || ' · DEPRECATED: Founder 30/09/2026 — SPEC-122: sucedido pelo gpt-6.1-sol (mesmo preço; cache 0,10)',
       updated_at = now()
 where model_name = 'gpt-6-sol'
   and (lifecycle is distinct from 'DEPRECATED' or substituido_por is distinct from 'gpt-6.1-sol');

-- -------------------------------------------------------------
-- E. asserção — aborta a migration inteira se algo ficar fora
-- -------------------------------------------------------------
do $$
declare n_sol6 int; n_rotas int; n_ag int; n_co int; ciclo_61 text; ciclo_6 text;
        subst text; cache numeric; tem_none boolean;
begin
  select count(*) into n_sol6 from public.llm_papeis
   where 'gpt-6-sol' in (modelo_primario, modelo_reserva);
  select count(*) into n_rotas from public.llm_papeis r
    left join public.llm_pricing p on p.model_name = r.modelo_primario
    left join public.llm_pricing q on q.model_name = r.modelo_reserva
   where p.lifecycle is distinct from 'APPROVED'
      or (r.modelo_reserva is not null and q.lifecycle is distinct from 'APPROVED');
  select count(*) into n_ag from public.agents where llm_model = 'gpt-6-sol';
  select count(*) into n_co from public.companies where llm_model = 'gpt-6-sol';
  select lifecycle, cached_input_multiplier, (capacidades -> 'niveis_de_esforco') ? 'none'
    into ciclo_61, cache, tem_none from public.llm_pricing where model_name = 'gpt-6.1-sol';
  select lifecycle, substituido_por into ciclo_6, subst from public.llm_pricing where model_name = 'gpt-6-sol';
  if n_sol6 <> 0 or n_rotas <> 0 or n_ag <> 0 or n_co <> 0
     or ciclo_61 is distinct from 'APPROVED' or cache is distinct from 0.05 or tem_none is distinct from false
     or ciclo_6 is distinct from 'DEPRECATED' or subst is distinct from 'gpt-6.1-sol' then
    raise exception '20260930_01 FALHOU: rotas_sol6=% rotas_fora=% agentes=% corretoras=% ciclo_61=% cache=% none=% ciclo_6=% subst=%',
      n_sol6, n_rotas, n_ag, n_co, ciclo_61, cache, tem_none, ciclo_6, subst;
  end if;
end $$;
