-- =============================================================
-- MIGRATION: 20260929_01_spec121_sonnet_5_5
-- SPEC:      SPEC-121 — F7 · o Sonnet 5.5 entra, o Sonnet 5 sai
-- AUTOR:     builder F7 (Opus 5.5 xhigh)      DATA: 2026-09-29
-- OBJETIVO:  cadastrar `claude-sonnet-5-5` no catálogo governado (APPROVED) e
--            PROIBIR `claude-sonnet-5` (BLOCKED) em todo o AutoBrokers.
--            Ordem do Founder, 29/09/2026 (literal): "Instale o Sonnet 5.5 no
--            lugar do Sonnet 5, e o Sonnet 5 deve ser substituído. Não deve mais
--            estar no AutoBrokers. Precisa ser o Sonnet 5.5 ou senão o Opus 5.5.
--            Sonnet 5 está PROIBIDO de ser usado no sistema."
--
-- EVIDÊNCIA:
--   📊 29/09/2026 GET https://api.anthropic.com/v1/models/claude-sonnet-5-5 (chave do
--      backend/.env): max_input_tokens 1000000 · max_tokens 128000 · effort
--      low/medium/high/xhigh/max · thinking adaptive · image/pdf · structured outputs.
--   📊 29/09/2026 doc oficial (pricing + whats-new-sonnet-5-5): US$ 2 / 10 por MTok;
--      cache write 5m 2,50 · 1h 4 · hit 0,20 (0,1×); esforço padrão `high`.
--      QUEBRAM vindo do Sonnet 5: thinking disabled → 400 (o mais baixo é
--      `between_tools`, só com effort ≤ high); tool_choice any/tool → 400;
--      temperature/top_p/top_k não-default → 400.
--   📊 29/09/2026 (SELECT, antes): llm_pricing claude-sonnet-5 DEPRECATED
--      substituido_por NULL; 7 sonnets antigos com substituido_por='claude-sonnet-5';
--      llm_papeis: 0 rotas em claude-sonnet-5 (primário ou reserva);
--      agents.llm_model='claude-sonnet-5' em 8 linhas; companies em 1 linha;
--      nenhum column_default nem função do banco cita 'claude-sonnet-5'.
--
-- APPLY:
--   A. INSERT de claude-sonnet-5-5 (APPROVED) — se já existir, o UPDATE do
--      bloco A2 põe capacidades/preço/ciclo no valor desta migration.
--   B. claude-sonnet-5 → BLOCKED, substituido_por 'claude-sonnet-5-5' + nota.
--   C. os sonnets que apontavam substituido_por → 'claude-sonnet-5' passam a
--      apontar para 'claude-sonnet-5-5'.
--   D. agents.llm_model / companies.llm_model = 'claude-sonnet-5' →
--      'claude-sonnet-5-5' (o provedor já é 'anthropic' nas 9 linhas).
--   E. asserção: 0 rotas em modelo não-APPROVED; 0 agente/corretora em Sonnet 5.
--
-- VERIFY:
--   select model_name, lifecycle, substituido_por, input_price_per_million,
--          output_price_per_million, cache_read_multiplier, cache_write_multiplier,
--          capacidades->>'tool_choice_forcado_ok' tc, capacidades->>'sampling_ok' s,
--          capacidades->>'raciocinio_desligado' rd, preco_verificado_em
--     from public.llm_pricing where model_name in ('claude-sonnet-5','claude-sonnet-5-5') order by 1;
--   -- esperado: sonnet-5 BLOCKED → claude-sonnet-5-5 ·
--   --           sonnet-5-5 APPROVED NULL 2 10 0.1 1.25 false false between_tools 2026-09-29
--   select count(*) from public.llm_pricing where substituido_por = 'claude-sonnet-5';   -- esperado 0
--   select count(*) from public.llm_pricing where substituido_por = 'claude-sonnet-5-5'; -- esperado 8
--   select (select count(*) from public.agents where llm_model='claude-sonnet-5') ag5,
--          (select count(*) from public.companies where llm_model='claude-sonnet-5') co5,
--          (select count(*) from public.agents where llm_model='claude-sonnet-5-5') ag55,
--          (select count(*) from public.companies where llm_model='claude-sonnet-5-5') co55;
--   -- esperado: 0 · 0 · 8 · 1
--   select count(*) from public.llm_papeis r
--     left join public.llm_pricing p on p.model_name = r.modelo_primario
--     left join public.llm_pricing q on q.model_name = r.modelo_reserva
--    where p.lifecycle is distinct from 'APPROVED'
--       or (r.modelo_reserva is not null and q.lifecycle is distinct from 'APPROVED');
--   -- esperado: 0
--   -- a trava de rota recusa o Sonnet 5 e aceita o 5.5 (SAVEPOINT; nada fica gravado):
--   do $$
--   declare v_a int; v_a2 int; recusou boolean := false;
--   begin
--     select versao into v_a from public.llm_papeis where papel = 'juiz_eval';
--     begin
--       update public.llm_papeis set provider='anthropic', modelo_primario='claude-sonnet-5', esforco='high'
--        where papel='juiz_eval';
--     exception when check_violation then recusou := true; end;
--     begin  -- CONTROLE: o 5.5 PASSA (e é desfeito pelo raise dentro do sub-bloco)
--       update public.llm_papeis set provider='anthropic', modelo_primario='claude-sonnet-5-5', esforco='high'
--        where papel='juiz_eval';
--       raise exception using errcode = 'P0001', message = 'desfaz-controle';
--     exception when sqlstate 'P0001' then null; end;
--     select versao into v_a2 from public.llm_papeis where papel = 'juiz_eval';
--     if not recusou or v_a is distinct from v_a2 then
--       raise exception 'VERIFY 20260929_01 FALHOU: recusou=% versao % -> %', recusou, v_a, v_a2;
--     end if;
--     raise notice 'VERIFY 20260929_01 OK: Sonnet 5 recusado, Sonnet 5.5 aceito, versão intocada';
--   end $$;
--
-- ROLLBACK:  (escrito ANTES de aplicar)
--   -- D. as 9 linhas afetadas (📊 29/09/2026, SELECT id … where llm_model='claude-sonnet-5'):
--   update public.agents set llm_model = 'claude-sonnet-5' where id in (
--     '02dc72f7-42b5-4400-9722-b49535860824','0aa7ccd9-556d-4feb-aecb-3fb88f1bd7ed',
--     '20845996-2c16-433e-9756-37098108902a','4f109d3a-ef33-43eb-ac6c-70bdcbbe8d22',
--     'aee852d3-c52f-4b52-b71a-5078ad8662c2','b86835eb-5b8c-4bd8-adcf-73c277c6f057',
--     'c95de02a-a946-468d-a636-13e882781468','dcff8e6d-9a1e-403c-a404-e6e349694080')
--     and llm_model = 'claude-sonnet-5-5';
--   update public.companies set llm_model = 'claude-sonnet-5'
--    where id = '04b5cdbc-04cd-4ddf-8e4b-f43efb062fab' and llm_model = 'claude-sonnet-5-5';
--   -- C.
--   update public.llm_pricing set substituido_por = 'claude-sonnet-5', updated_at = now()
--    where model_name in ('claude-3-5-sonnet-20240620','claude-3-5-sonnet-20241022',
--      'claude-3-7-sonnet-20250219','claude-sonnet-4-20250514','claude-sonnet-4-5',
--      'claude-sonnet-4-5-20250929','claude-sonnet-4-6');
--   -- B.
--   update public.llm_pricing set lifecycle = 'DEPRECATED', substituido_por = null,
--          notas = replace(notas, ' · BLOCKED: Founder 29/09/2026 — SPEC-121: Sonnet 5 PROIBIDO; usar claude-sonnet-5-5 ou claude-opus-5-5', ''),
--          updated_at = now()
--    where model_name = 'claude-sonnet-5';
--   -- A. (só se nenhuma rota/agente o usar — a FK de llm_papeis recusa o delete se usar)
--   delete from public.llm_pricing where model_name = 'claude-sonnet-5-5';
--   -- e regerar o snapshot: python scripts/gerar_snapshot_de_modelos.py --banco
--
-- EXPAND-FIRST: sim — linha nova no catálogo antes de qualquer referência a ela;
--               nenhuma coluna, CHECK ou trava muda.
-- DESTRUTIVA:   não — 9 valores de llm_model trocados, com os ids no ROLLBACK.
-- =============================================================

-- -------------------------------------------------------------
-- A. o Sonnet 5.5 entra no catálogo
-- -------------------------------------------------------------
insert into public.llm_pricing (model_name, provider, display_name, input_price_per_million,
  output_price_per_million, unit, is_active, cache_read_multiplier, cache_write_multiplier,
  cached_input_multiplier, lifecycle, tipo, api_surface, capacidades, classes_de_dado,
  preco_verificado_em, fonte_preco_url, notas)
values ('claude-sonnet-5-5', 'anthropic', 'Claude Sonnet 5.5', 2, 10, 'token', true,
        0.1, 1.25, 0.1, 'APPROVED', 'chat', 'messages',
        '{"tools": true, "reasoning_param": "output_config.effort",
          "niveis_de_esforco": ["low", "medium", "high", "xhigh", "max"],
          "sampling_ok": false, "vision": true, "pdf": true, "max_output": 128000,
          "contexto": 1000000, "tool_choice_forcado_ok": false,
          "raciocinio_ida_e_volta": true, "responses_obrigatoria_com_tools": false,
          "raciocinio_desligado": "between_tools",
          "raciocinio_desligado_esforco_max": "high"}'::jsonb,
        array['publico', 'interno', 'pii'], date '2026-09-29',
        'https://platform.claude.com/docs/en/about-claude/pricing',
        'lançado 28/09/2026; cadastrado na SPEC-121 (Founder 29/09/2026: substitui o Sonnet 5). '
        || 'cache hit 0,20 · write 5m 2,50 · 1h 4. Default effort high. thinking disabled -> 400: '
        || 'o mais baixo é between_tools (effort <= high); tool_choice any/tool -> 400; sampling -> 400. '
        || 'Fonte técnica: https://platform.claude.com/docs/en/models/sonnet-5-5/whats-new-sonnet-5-5')
on conflict (model_name) do nothing;

-- A2. idempotente: se a linha já existia, ela fica igual à desta migration
update public.llm_pricing
   set provider = 'anthropic', lifecycle = 'APPROVED', tipo = 'chat', api_surface = 'messages',
       input_price_per_million = 2, output_price_per_million = 10,
       cache_read_multiplier = 0.1, cache_write_multiplier = 1.25, cached_input_multiplier = 0.1,
       capacidades = '{"tools": true, "reasoning_param": "output_config.effort",
          "niveis_de_esforco": ["low", "medium", "high", "xhigh", "max"],
          "sampling_ok": false, "vision": true, "pdf": true, "max_output": 128000,
          "contexto": 1000000, "tool_choice_forcado_ok": false,
          "raciocinio_ida_e_volta": true, "responses_obrigatoria_com_tools": false,
          "raciocinio_desligado": "between_tools",
          "raciocinio_desligado_esforco_max": "high"}'::jsonb,
       classes_de_dado = array['publico', 'interno', 'pii'], substituido_por = null,
       preco_verificado_em = date '2026-09-29',
       fonte_preco_url = 'https://platform.claude.com/docs/en/about-claude/pricing',
       is_active = true, updated_at = now()
 where model_name = 'claude-sonnet-5-5';

-- -------------------------------------------------------------
-- B. o Sonnet 5 fica PROIBIDO
-- -------------------------------------------------------------
update public.llm_pricing
   set lifecycle = 'BLOCKED',
       substituido_por = 'claude-sonnet-5-5',
       notas = coalesce(notas, '') || ' · BLOCKED: Founder 29/09/2026 — SPEC-121: Sonnet 5 PROIBIDO; usar claude-sonnet-5-5 ou claude-opus-5-5',
       updated_at = now()
 where model_name = 'claude-sonnet-5'
   and (lifecycle is distinct from 'BLOCKED' or substituido_por is distinct from 'claude-sonnet-5-5');

-- -------------------------------------------------------------
-- C. quem apontava para o Sonnet 5 passa a apontar para o 5.5
-- -------------------------------------------------------------
update public.llm_pricing
   set substituido_por = 'claude-sonnet-5-5', updated_at = now()
 where substituido_por = 'claude-sonnet-5';

-- -------------------------------------------------------------
-- D. nenhum agente nem corretora guarda mais o Sonnet 5
-- -------------------------------------------------------------
update public.agents    set llm_model = 'claude-sonnet-5-5' where llm_model = 'claude-sonnet-5';
update public.companies set llm_model = 'claude-sonnet-5-5' where llm_model = 'claude-sonnet-5';

-- -------------------------------------------------------------
-- E. asserção — aborta a migration inteira se algo ficar fora
-- -------------------------------------------------------------
do $$
declare n_rotas int; n_ag int; n_co int; n_subst int; ciclo text;
begin
  select count(*) into n_rotas from public.llm_papeis r
    left join public.llm_pricing p on p.model_name = r.modelo_primario
    left join public.llm_pricing q on q.model_name = r.modelo_reserva
   where p.lifecycle is distinct from 'APPROVED'
      or (r.modelo_reserva is not null and q.lifecycle is distinct from 'APPROVED');
  select count(*) into n_ag from public.agents where llm_model = 'claude-sonnet-5';
  select count(*) into n_co from public.companies where llm_model = 'claude-sonnet-5';
  select count(*) into n_subst from public.llm_pricing where substituido_por = 'claude-sonnet-5';
  select lifecycle into ciclo from public.llm_pricing where model_name = 'claude-sonnet-5-5';
  if n_rotas <> 0 or n_ag <> 0 or n_co <> 0 or n_subst <> 0 or ciclo is distinct from 'APPROVED' then
    raise exception '20260929_01 FALHOU: rotas=% agentes=% corretoras=% substituido_por=% ciclo_55=%',
      n_rotas, n_ag, n_co, n_subst, ciclo;
  end if;
end $$;
