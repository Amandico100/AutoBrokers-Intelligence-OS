-- =============================================================
-- MIGRATION: 20260923_01_spec116_catalogo_e_papeis
-- SPEC:      SPEC-116 — F1 · U1 (catálogo) + U2 (rotas por papel)
-- AUTOR:     builder F1 (Opus xhigh)       DATA: 2026-09-23
-- OBJETIVO:  UM catálogo governado (llm_pricing expandido) e UMA tabela de
--            rotas por PAPEL (llm_papeis + histórico), com seed que REPRODUZ o
--            runtime de 23/09/2026 — nenhum modelo efetivo muda aqui.
--
-- APPLY:
--   1. llm_pricing ganha 15 colunas ANULÁVEIS (lifecycle, tipo, api_surface,
--      capacidades, classes_de_dado, substituido_por, retirada_em,
--      input/output_price_long, limiar_contexto_longo, base_url, api_key_env,
--      preco_verificado_em, fonte_preco_url, notas) + 4 CHECKs.
--   2. os 3 multiplicadores de cache ALARGAM de numeric(5,2) para numeric(9,6).
--      📊 medido 23/09: numeric(5,2) arredonda o cache do Fable 5.1 (0,025) para
--      0,03 e o do MiMo (0,0083) para 0,01 — o preço verdadeiro não cabe.
--      Alargar não perde nenhum valor existente (todos têm 2 casas).
--   3. o bloco $catalogo$ (JSON, fonte ÚNICA — o script
--      backend/scripts/gerar_snapshot_de_modelos.py lê ESTE texto) atualiza as
--      50 linhas existentes (preço só onde o JSON traz preço) e insere as novas.
--      Toda linha termina com lifecycle; o que sobrar sem lifecycle vira
--      HISTORICAL (rede de segurança — hoje não sobra nenhuma).
--   4. cria llm_papeis + llm_papeis_historico + trigger que versiona e grava o
--      histórico em todo UPDATE que muda a rota; RLS ligada + policy SÓ de
--      leitura (authenticated) nas duas.
--   5. seed das rotas pelo bloco $papeis$ com ON CONFLICT DO NOTHING — rodar de
--      novo NUNCA desfaz uma rota trocada depois (F6 / bancada).
--
-- VERIFY:
--   -- 1) as colunas novas existem, todas anuláveis; multiplicadores alargados
--   select column_name, data_type, is_nullable, numeric_precision, numeric_scale
--     from information_schema.columns
--    where table_schema='public' and table_name='llm_pricing'
--      and column_name in ('lifecycle','tipo','api_surface','capacidades','classes_de_dado',
--        'substituido_por','retirada_em','input_price_long','output_price_long',
--        'limiar_contexto_longo','base_url','api_key_env','preco_verificado_em',
--        'fonte_preco_url','notas','cache_read_multiplier','cache_write_multiplier',
--        'cached_input_multiplier') order by 1;
--   -- esperado: 18 linhas · is_nullable=YES · multiplicadores 9/6
--
--   -- 2) nenhuma linha sem lifecycle; contagem por ciclo
--   select coalesce(lifecycle,'<NULO>') lifecycle, count(*) from public.llm_pricing group by 1 order by 1;
--   -- esperado (74 linhas): APPROVED 7 · BLOCKED 3 · CANDIDATE 14 · DEPRECATED 14 · HISTORICAL 36 · <NULO> ausente
--
--   -- 3) preços corrigidos com fonte
--   select model_name, input_price_per_million, output_price_per_million, cache_read_multiplier,
--          cache_write_multiplier, preco_verificado_em, fonte_preco_url
--     from public.llm_pricing where model_name in ('claude-sonnet-5','claude-opus-5-5','gpt-6-sol','claude-fable-5-1');
--   -- esperado: sonnet-5 2/10 0.10/1.25 · opus-5-5 4/20 0.05/1.25 · gpt-6-sol 2/10 · fable 10/50 0.025
--
--   -- 4) rotas: 25 papéis, todas versão 1, todas apontando para modelo do catálogo
--   select count(*) total, count(*) filter (where versao=1) v1,
--          count(*) filter (where p.lifecycle in ('BLOCKED','HISTORICAL')) proibidos
--     from public.llm_papeis r join public.llm_pricing p on p.model_name=r.modelo_primario;
--   -- esperado: 25 · 25 · 0
--
--   -- 5) segurança (advisors não podem crescer): RLS + policy + função do trigger
--   select c.relname, c.relrowsecurity,
--          (select count(*) from pg_policies pp where pp.schemaname='public' and pp.tablename=c.relname) policies
--     from pg_class c where c.oid in ('public.llm_papeis'::regclass,'public.llm_papeis_historico'::regclass);
--   -- esperado: as duas com relrowsecurity=true e policies=1
--   select p.proname, p.prosecdef, p.proconfig,
--          has_function_privilege('anon', p.oid, 'execute') anon_exec,
--          has_function_privilege('authenticated', p.oid, 'execute') auth_exec
--     from pg_proc p where p.proname='llm_papeis_registrar_historico';
--   -- esperado: prosecdef=false · proconfig={search_path=pg_catalog, public} · anon_exec=false · auth_exec=false
--
-- ROLLBACK:  (escrito ANTES de aplicar)
--   drop trigger if exists trg_llm_papeis_historico on public.llm_papeis;
--   drop function if exists public.llm_papeis_registrar_historico();
--   drop table if exists public.llm_papeis_historico;
--   drop table if exists public.llm_papeis;
--   alter table public.llm_pricing
--     drop constraint if exists llm_pricing_lifecycle_valido,
--     drop constraint if exists llm_pricing_tipo_valido,
--     drop constraint if exists llm_pricing_api_surface_valida,
--     drop constraint if exists llm_pricing_classes_validas,
--     drop column if exists lifecycle, drop column if exists tipo,
--     drop column if exists api_surface, drop column if exists capacidades,
--     drop column if exists classes_de_dado, drop column if exists substituido_por,
--     drop column if exists retirada_em, drop column if exists input_price_long,
--     drop column if exists output_price_long, drop column if exists limiar_contexto_longo,
--     drop column if exists base_url, drop column if exists api_key_env,
--     drop column if exists preco_verificado_em, drop column if exists fonte_preco_url,
--     drop column if exists notas;
--   -- ⚠️ linhas NOVAS do catálogo (as 24 que não existiam em 23/09) saem por nome:
--   delete from public.llm_pricing where model_name in ('claude-opus-5-5','claude-fable-5-1',
--     'gpt-6-sol','gpt-6-luna','gpt-6-astra','gpt-5.6-sol','gpt-5.6-terra','gpt-5.6-luna',
--     'gpt-transcribe','gemini-3.8-flash','grok-4.7','mimo-v2.6-pro','mimo-v2.6-flash',
--     'deepseek-flash','glm-5.3','rerank-multilingual-v3.0','meta-llama/llama-prompt-guard-2-86m',
--     'gpt-4.1','gpt-4.1-mini','gpt-3.5-turbo','gpt-4-turbo','gemini-2.0-flash',
--     'gemini-3-pro-preview-11-2025','claude-3-opus-20240229');
--   -- ⚠️ PREÇOS corrigidos voltam ao valor medido em 23/09 (o que o banco tinha):
--   update public.llm_pricing set input_price_per_million=3, output_price_per_million=15 where model_name='claude-sonnet-5';
--   update public.llm_pricing set input_price_per_million=0.10, output_price_per_million=0.40 where model_name='gemini-3-flash-preview';
--   update public.llm_pricing set provider='other' where model_name in ('grok-3','grok-4','deepseek-chat','mistral-large-latest');
--   update public.llm_pricing set cache_read_multiplier=0.10, cache_write_multiplier=1.25, cached_input_multiplier=0.50;
--   -- (voltar à escala 5,2 é opcional: alter column ... type numeric(5,2) arredonda — só se preciso)
--
-- EXPAND-FIRST: sim — só ADD COLUMN anulável, ALARGA precisão, CREATE TABLE nova;
--               nenhuma coluna existente some, nenhum dado de corretora é tocado.
-- DESTRUTIVA:   não
-- =============================================================

-- -------------------------------------------------------------
-- 1. Catálogo = llm_pricing EXPANDIDO (D-116-02: não é tabela nova de modelos)
-- -------------------------------------------------------------
alter table public.llm_pricing
  add column if not exists lifecycle              text,
  add column if not exists tipo                   text,
  add column if not exists api_surface            text,
  add column if not exists capacidades            jsonb default '{}'::jsonb,
  add column if not exists classes_de_dado        text[],
  add column if not exists substituido_por        text,
  add column if not exists retirada_em            date,
  add column if not exists input_price_long       numeric,
  add column if not exists output_price_long      numeric,
  add column if not exists limiar_contexto_longo  integer,
  add column if not exists base_url               text,
  add column if not exists api_key_env            text,
  add column if not exists preco_verificado_em    date,
  add column if not exists fonte_preco_url        text,
  add column if not exists notas                  text;

-- 📊 23/09: numeric(5,2) — o cache do Fable (0,025) e do MiMo (0,0083) não cabem.
alter table public.llm_pricing
  alter column cache_read_multiplier   type numeric(9,6),
  alter column cache_write_multiplier  type numeric(9,6),
  alter column cached_input_multiplier type numeric(9,6);

do $$
begin
  if not exists (select 1 from pg_constraint where conname='llm_pricing_lifecycle_valido'
                   and conrelid='public.llm_pricing'::regclass) then
    alter table public.llm_pricing add constraint llm_pricing_lifecycle_valido
      check (lifecycle is null or lifecycle in ('APPROVED','CANDIDATE','DEPRECATED','BLOCKED','HISTORICAL'));
  end if;
  if not exists (select 1 from pg_constraint where conname='llm_pricing_tipo_valido'
                   and conrelid='public.llm_pricing'::regclass) then
    alter table public.llm_pricing add constraint llm_pricing_tipo_valido
      check (tipo is null or tipo in ('chat','embedding','rerank','stt','guard'));
  end if;
  if not exists (select 1 from pg_constraint where conname='llm_pricing_api_surface_valida'
                   and conrelid='public.llm_pricing'::regclass) then
    alter table public.llm_pricing add constraint llm_pricing_api_surface_valida
      check (api_surface is null or api_surface in ('chat_completions','responses','messages',
             'generate_content','openai_compat','embeddings','rerank','stt','guard'));
  end if;
  if not exists (select 1 from pg_constraint where conname='llm_pricing_classes_validas'
                   and conrelid='public.llm_pricing'::regclass) then
    alter table public.llm_pricing add constraint llm_pricing_classes_validas
      check (classes_de_dado is null or classes_de_dado <@ array['publico','interno','pii']::text[]);
  end if;
end $$;

comment on column public.llm_pricing.lifecycle is
  'SPEC-116: APPROVED|CANDIDATE|DEPRECATED usáveis; BLOCKED (retirado pelo provedor) e HISTORICAL (fora de uso) o resolvedor RECUSA.';
comment on column public.llm_pricing.classes_de_dado is
  'SPEC-116 D-116-10: que classe de dado o modelo pode ver (publico|interno|pii). Rota pii só vai a modelo com pii.';
comment on column public.llm_pricing.capacidades is
  'SPEC-116: tools, reasoning_param, niveis_de_esforco[], sampling_ok, vision, pdf, max_output, contexto, tool_choice_forcado_ok, raciocinio_ida_e_volta, responses_obrigatoria_com_tools.';

-- -------------------------------------------------------------
-- 2. As linhas do catálogo. 🔴 FONTE ÚNICA: o gerador do snapshot lê o texto
--    entre as marcas $catalogo$. Preço só onde há fonte (EVIDENCIAS 04/05,
--    acesso 23/09/2026); linha sem campo de preço MANTÉM o preço do banco.
--    Multiplicador = preço do cache ÷ preço de entrada (ex.: Sonnet 5 0,20/2 = 0,10).
-- -------------------------------------------------------------
drop table if exists _spec116_catalogo;
create temp table _spec116_catalogo as
select e as linha from jsonb_array_elements($catalogo$
[
{"model_name":"claude-sonnet-5","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"APPROVED","classes_de_dado":["publico","interno","pii"],"input_price_per_million":2,"output_price_per_million":10,"cache_read_multiplier":0.1,"cache_write_multiplier":1.25,"cached_input_multiplier":0.1,"capacidades":{"tools":true,"reasoning_param":"output_config.effort","niveis_de_esforco":["low","medium","high","xhigh","max"],"sampling_ok":false,"vision":true,"pdf":true,"max_output":128000,"contexto":1000000,"tool_choice_forcado_ok":true,"raciocinio_ida_e_volta":true,"responses_obrigatoria_com_tools":false},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://platform.claude.com/docs/en/about-claude/pricing","notas":"2/10 permanente desde 10/08/2026 (o aumento p/ 3/15 de 01/09 no longer applies). cache hit 0,20 · write 5m 2,50 · 1h 4. Default effort high."},
{"model_name":"claude-opus-5","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"APPROVED","classes_de_dado":["publico","interno","pii"],"input_price_per_million":5,"output_price_per_million":25,"cache_read_multiplier":0.1,"cache_write_multiplier":1.25,"cached_input_multiplier":0.1,"substituido_por":"claude-opus-5-5","capacidades":{"tools":true,"reasoning_param":"output_config.effort","niveis_de_esforco":["low","medium","high","xhigh","max"],"sampling_ok":false,"vision":true,"pdf":true,"max_output":128000,"contexto":1000000,"tool_choice_forcado_ok":true,"raciocinio_ida_e_volta":true,"responses_obrigatoria_com_tools":false},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://platform.claude.com/docs/en/about-claude/pricing","notas":"cache hit 0,50 · write 5m 6,25 · retirada >= 24/07/2027; migração recomendada p/ Opus 5.5."},
{"model_name":"claude-opus-5-5","display_name":"Claude Opus 5.5","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"APPROVED","classes_de_dado":["publico","interno","pii"],"input_price_per_million":4,"output_price_per_million":20,"cache_read_multiplier":0.05,"cache_write_multiplier":1.25,"cached_input_multiplier":0.05,"capacidades":{"tools":true,"reasoning_param":"output_config.effort","niveis_de_esforco":["low","medium","high","xhigh","max"],"sampling_ok":false,"vision":true,"pdf":true,"max_output":128000,"contexto":1000000,"tool_choice_forcado_ok":false,"raciocinio_ida_e_volta":true,"responses_obrigatoria_com_tools":false},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://platform.claude.com/docs/en/about-claude/pricing","notas":"lançado 22/09/2026. cache hit 0,20 · write 5m 5 · 1h 8. Thinking SEMPRE ligado; tool_choice any/tool -> 400. Default effort medium."},
{"model_name":"claude-haiku-4-5-20251001","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"APPROVED","classes_de_dado":["publico","interno","pii"],"input_price_per_million":1,"output_price_per_million":5,"cache_read_multiplier":0.1,"cache_write_multiplier":1.25,"cached_input_multiplier":0.1,"capacidades":{"tools":true,"reasoning_param":"thinking.budget_tokens","niveis_de_esforco":[],"sampling_ok":true,"vision":true,"pdf":true,"max_output":64000,"contexto":200000,"tool_choice_forcado_ok":true,"raciocinio_ida_e_volta":true,"responses_obrigatoria_com_tools":false},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://platform.claude.com/docs/en/about-claude/pricing","notas":"retirada 'not sooner than 15/10/2026' — próximo candidato a deprecação. Não suporta effort."},
{"model_name":"claude-haiku-4-5","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"APPROVED","classes_de_dado":["publico","interno","pii"],"input_price_per_million":1,"output_price_per_million":5,"cache_read_multiplier":0.1,"cache_write_multiplier":1.25,"cached_input_multiplier":0.1,"capacidades":{"tools":true,"reasoning_param":"thinking.budget_tokens","niveis_de_esforco":[],"sampling_ok":true,"vision":true,"pdf":true,"max_output":64000,"contexto":200000,"tool_choice_forcado_ok":true,"raciocinio_ida_e_volta":true,"responses_obrigatoria_com_tools":false},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://platform.claude.com/docs/en/about-claude/pricing","notas":"alias de claude-haiku-4-5-20251001."},
{"model_name":"claude-fable-5-1","display_name":"Claude Fable 5.1","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"CANDIDATE","classes_de_dado":["publico","interno"],"input_price_per_million":10,"output_price_per_million":50,"cache_read_multiplier":0.025,"cache_write_multiplier":1.25,"cached_input_multiplier":0.025,"capacidades":{"tools":true,"reasoning_param":"output_config.effort","niveis_de_esforco":["low","medium","high","xhigh","max"],"sampling_ok":false,"vision":true,"pdf":true,"max_output":128000,"contexto":1000000,"tool_choice_forcado_ok":true,"raciocinio_ida_e_volta":true,"responses_obrigatoria_com_tools":false},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://platform.claude.com/docs/en/about-claude/pricing","notas":"Covered Model: retenção obrigatória de 30 dias, SEM ZDR -> sem pii (D-116-10). cache hit 0,25 · write 5m 12,50."},
{"model_name":"claude-sonnet-4-6","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"DEPRECATED","classes_de_dado":["publico","interno","pii"],"input_price_per_million":3,"output_price_per_million":15,"cache_read_multiplier":0.1,"cache_write_multiplier":1.25,"cached_input_multiplier":0.1,"substituido_por":"claude-sonnet-5","capacidades":{"tools":true,"reasoning_param":"thinking.budget_tokens","niveis_de_esforco":[],"sampling_ok":true,"vision":true},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://platform.claude.com/docs/en/about-claude/pricing","notas":"retirada >= 17/02/2027."},
{"model_name":"claude-sonnet-4-5","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"DEPRECATED","classes_de_dado":["publico","interno","pii"],"substituido_por":"claude-sonnet-5","capacidades":{"tools":true,"sampling_ok":true,"vision":true}},
{"model_name":"claude-sonnet-4-5-20250929","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"DEPRECATED","classes_de_dado":["publico","interno","pii"],"substituido_por":"claude-sonnet-5","capacidades":{"tools":true,"sampling_ok":true,"vision":true}},
{"model_name":"claude-opus-4-5","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"DEPRECATED","classes_de_dado":["publico","interno","pii"],"substituido_por":"claude-opus-5-5","capacidades":{"tools":true,"sampling_ok":true,"vision":true}},
{"model_name":"claude-opus-4-5-20251101","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"DEPRECATED","classes_de_dado":["publico","interno","pii"],"substituido_por":"claude-opus-5-5","capacidades":{"tools":true,"sampling_ok":true,"vision":true}},
{"model_name":"claude-opus-4-6","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"DEPRECATED","classes_de_dado":["publico","interno","pii"],"substituido_por":"claude-opus-5-5","capacidades":{"tools":true,"sampling_ok":true,"vision":true}},
{"model_name":"claude-opus-4-7","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"DEPRECATED","classes_de_dado":["publico","interno","pii"],"substituido_por":"claude-opus-5-5","capacidades":{"tools":true,"sampling_ok":false,"vision":true}},
{"model_name":"claude-opus-4-8","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"DEPRECATED","classes_de_dado":["publico","interno","pii"],"substituido_por":"claude-opus-5-5","capacidades":{"tools":true,"sampling_ok":false,"vision":true}},
{"model_name":"claude-3-5-sonnet-20240620","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"BLOCKED","classes_de_dado":["publico","interno","pii"],"substituido_por":"claude-sonnet-5","retirada_em":"2025-10-28","notas":"RETIRED pelo provedor em 28/10/2025 — requisição falha."},
{"model_name":"claude-3-5-sonnet-20241022","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"BLOCKED","classes_de_dado":["publico","interno","pii"],"substituido_por":"claude-sonnet-5","retirada_em":"2025-10-28","notas":"RETIRED pelo provedor em 28/10/2025 — requisição falha."},
{"model_name":"claude-3-5-haiku-20241022","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"BLOCKED","classes_de_dado":["publico","interno","pii"],"substituido_por":"claude-haiku-4-5-20251001","retirada_em":"2026-02-19","notas":"RETIRED pelo provedor em 19/02/2026."},
{"model_name":"claude-3-7-sonnet-20250219","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"],"substituido_por":"claude-sonnet-5"},
{"model_name":"claude-3-opus-20240229","display_name":"Claude 3 Opus","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"],"is_active":false,"substituido_por":"claude-opus-5-5","notas":"literal do censo (SPEC-116 EVIDENCIAS/01); sem preço verificado."},
{"model_name":"claude-opus-4-20250514","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"],"substituido_por":"claude-opus-5-5"},
{"model_name":"claude-opus-4-1-20250805","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"],"substituido_por":"claude-opus-5-5"},
{"model_name":"claude-sonnet-4-20250514","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"],"substituido_por":"claude-sonnet-5"},
{"model_name":"claude-fable-5","provider":"anthropic","tipo":"chat","api_surface":"messages","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno"],"substituido_por":"claude-fable-5-1"},

{"model_name":"gpt-6-sol","display_name":"GPT-6 Sol","provider":"openai","tipo":"chat","api_surface":"responses","lifecycle":"CANDIDATE","classes_de_dado":["publico","interno","pii"],"input_price_per_million":2,"output_price_per_million":10,"cache_read_multiplier":0.1,"cache_write_multiplier":1.25,"cached_input_multiplier":0.1,"input_price_long":4,"output_price_long":15,"limiar_contexto_longo":272000,"capacidades":{"tools":true,"reasoning_param":"reasoning.effort","niveis_de_esforco":["none","low","medium","high","xhigh","max"],"sampling_ok":false,"vision":true,"max_output":128000,"contexto":1050000,"tool_choice_forcado_ok":true,"raciocinio_ida_e_volta":true,"responses_obrigatoria_com_tools":true},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://developers.openai.com/api/docs/pricing","notas":"lançado 22/09/2026. cached 0,20 · cache write 2,50 · >272K 4/0,40/5/15. Chat Completions: tools só com reasoning_effort=none. Default effort medium."},
{"model_name":"gpt-6-luna","display_name":"GPT-6 Luna","provider":"openai","tipo":"chat","api_surface":"responses","lifecycle":"CANDIDATE","classes_de_dado":["publico","interno","pii"],"input_price_per_million":0.1,"output_price_per_million":0.5,"cache_read_multiplier":0.1,"cache_write_multiplier":1.25,"cached_input_multiplier":0.1,"input_price_long":0.2,"output_price_long":0.75,"limiar_contexto_longo":272000,"capacidades":{"tools":true,"reasoning_param":"reasoning.effort","niveis_de_esforco":["none","low","medium","high","xhigh","max"],"sampling_ok":false,"vision":true,"max_output":128000,"contexto":1050000,"tool_choice_forcado_ok":true,"raciocinio_ida_e_volta":true,"responses_obrigatoria_com_tools":true},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://developers.openai.com/api/docs/pricing","notas":"lançado 22/09/2026. cached 0,01 · cache write 0,125 · >272K 0,20/0,02/0,25/0,75."},
{"model_name":"gpt-6-astra","display_name":"GPT-6 Astra","provider":"openai","tipo":"chat","api_surface":"responses","lifecycle":"CANDIDATE","classes_de_dado":["publico","interno","pii"],"input_price_per_million":10,"output_price_per_million":50,"cache_read_multiplier":0.1,"cache_write_multiplier":1.25,"cached_input_multiplier":0.1,"input_price_long":20,"output_price_long":75,"limiar_contexto_longo":272000,"capacidades":{"tools":true,"reasoning_param":"reasoning.effort","niveis_de_esforco":["low","medium","high","xhigh","max"],"sampling_ok":false,"vision":true,"max_output":128000,"contexto":1050000,"tool_choice_forcado_ok":true,"raciocinio_ida_e_volta":true,"responses_obrigatoria_com_tools":true},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://developers.openai.com/api/docs/pricing","notas":"lançado 03/09/2026. cached 1,00 · cache write 12,50 · >272K 20/2/25/75. Sem effort none. Teto de qualidade da bancada."},
{"model_name":"gpt-5.6-sol","display_name":"GPT-5.6 Sol","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"CANDIDATE","classes_de_dado":["publico","interno","pii"],"input_price_per_million":4,"output_price_per_million":20,"cache_read_multiplier":0.1,"cache_write_multiplier":1.25,"cached_input_multiplier":0.1,"capacidades":{"tools":true,"reasoning_param":"reasoning.effort","sampling_ok":false},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://developers.openai.com/api/docs/pricing","notas":"4/0,40/5/20 promocional até 21/11/2026. Longo 2x/1,5x (limiar não registrado nas evidências). api_surface a confirmar na F2."},
{"model_name":"gpt-5.6-terra","display_name":"GPT-5.6 Terra","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"CANDIDATE","classes_de_dado":["publico","interno","pii"],"input_price_per_million":2,"output_price_per_million":12,"cache_read_multiplier":0.1,"cache_write_multiplier":1.25,"cached_input_multiplier":0.1,"capacidades":{"tools":true,"reasoning_param":"reasoning.effort","sampling_ok":false},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://developers.openai.com/api/docs/pricing","notas":"2/0,20/2,50/12. Longo 2x/1,5x (limiar não registrado nas evidências). api_surface a confirmar na F2."},
{"model_name":"gpt-5.6-luna","display_name":"GPT-5.6 Luna","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"CANDIDATE","classes_de_dado":["publico","interno","pii"],"input_price_per_million":0.2,"output_price_per_million":1.2,"cache_read_multiplier":0.1,"cache_write_multiplier":1.25,"cached_input_multiplier":0.1,"capacidades":{"tools":true,"reasoning_param":"reasoning.effort","sampling_ok":false},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://developers.openai.com/api/docs/pricing","notas":"0,20/0,02/0,25/1,20. api_surface a confirmar na F2."},
{"model_name":"gpt-4o","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"DEPRECATED","classes_de_dado":["publico","interno","pii"],"input_price_per_million":2.5,"output_price_per_million":10,"cache_read_multiplier":0.5,"cache_write_multiplier":1,"cached_input_multiplier":0.5,"capacidades":{"tools":true,"reasoning_param":null,"niveis_de_esforco":[],"sampling_ok":true,"vision":true,"max_output":16384,"contexto":128000,"tool_choice_forcado_ok":true,"raciocinio_ida_e_volta":false,"responses_obrigatoria_com_tools":false},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://developers.openai.com/api/docs/pricing","notas":"ativo no provedor, sem deprecação anunciada; DEPRECATED no produto (D-116-11) até a bancada provar o substituto do papel. cached 1,25."},
{"model_name":"gpt-4o-mini","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"DEPRECATED","classes_de_dado":["publico","interno","pii"],"input_price_per_million":0.15,"output_price_per_million":0.6,"cache_read_multiplier":0.5,"cache_write_multiplier":1,"cached_input_multiplier":0.5,"capacidades":{"tools":true,"reasoning_param":null,"niveis_de_esforco":[],"sampling_ok":true,"vision":true,"max_output":16384,"contexto":128000,"tool_choice_forcado_ok":true,"raciocinio_ida_e_volta":false,"responses_obrigatoria_com_tools":false},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://developers.openai.com/api/docs/pricing","notas":"ativo no provedor, sem deprecação anunciada; DEPRECATED no produto (D-116-11). cached 0,075."},
{"model_name":"gpt-4o-mini-2024-07-18","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"DEPRECATED","classes_de_dado":["publico","interno","pii"],"input_price_per_million":0.15,"output_price_per_million":0.6,"cache_read_multiplier":0.5,"cache_write_multiplier":1,"cached_input_multiplier":0.5,"capacidades":{"tools":true,"sampling_ok":true,"vision":true,"max_output":16384,"contexto":128000},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://developers.openai.com/api/docs/pricing","notas":"snapshot único do gpt-4o-mini; é o id que o provedor devolve (ledger)."},
{"model_name":"gpt-transcribe","display_name":"GPT Transcribe","provider":"openai","tipo":"stt","api_surface":"stt","lifecycle":"CANDIDATE","classes_de_dado":["publico","interno","pii"],"input_price_per_million":0.0045,"output_price_per_million":0,"unit":"minute","preco_verificado_em":"2026-09-23","fonte_preco_url":"https://developers.openai.com/api/docs/pricing","notas":"US$0,0045/min. Substituto oficial do whisper-1 (D-116-13)."},
{"model_name":"whisper-1","provider":"openai","tipo":"stt","api_surface":"stt","lifecycle":"DEPRECATED","classes_de_dado":["publico","interno","pii"],"input_price_per_million":0.006,"output_price_per_million":0,"unit":"minute","substituido_por":"gpt-transcribe","retirada_em":"2027-02-26","preco_verificado_em":"2026-09-23","fonte_preco_url":"https://developers.openai.com/api/docs/deprecations","notas":"deprecado 26/08/2026, desligamento 26/02/2027. US$0,006/min."},
{"model_name":"text-embedding-3-small","provider":"openai","tipo":"embedding","api_surface":"embeddings","lifecycle":"APPROVED","classes_de_dado":["publico","interno","pii"],"input_price_per_million":0.02,"output_price_per_million":0,"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://developers.openai.com/api/docs/pricing","notas":"KEEP (D-116-12): OpenAI não tem sucessor; troca = reindexação + eval de retrieval."},
{"model_name":"gpt-4.1","display_name":"GPT-4.1","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"],"is_active":false,"notas":"literal do censo (SPEC-116 EVIDENCIAS/01); sem preço verificado."},
{"model_name":"gpt-4.1-mini","display_name":"GPT-4.1 mini","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"],"is_active":false,"notas":"literal do censo (ECONOMY_MODELS); sem preço verificado."},
{"model_name":"gpt-3.5-turbo","display_name":"GPT-3.5 Turbo","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"],"is_active":false,"notas":"literal do censo (ECONOMY_MODELS); deprecado pelo provedor."},
{"model_name":"gpt-4-turbo","display_name":"GPT-4 Turbo","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"],"is_active":false,"retirada_em":"2026-10-23","notas":"rótulo que mente no log (nodes.py/subagent_tool.py); desligamento 23/10/2026."},
{"model_name":"chatgpt-4o-latest","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"gpt-5.1","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"gpt-5.2","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"gpt-5.2-chat-latest","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"gpt-5.2-pro","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"o1","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"o1-mini","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"o1-preview","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"o1-pro","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"o3","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"o3-mini","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"o3-pro","provider":"openai","tipo":"chat","api_surface":"chat_completions","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},

{"model_name":"gemini-3.8-flash","display_name":"Gemini 3.8 Flash","provider":"google","tipo":"chat","api_surface":"generate_content","lifecycle":"CANDIDATE","classes_de_dado":["publico"],"input_price_per_million":0.75,"output_price_per_million":3.75,"cache_read_multiplier":0.1,"cache_write_multiplier":1,"cached_input_multiplier":0.1,"api_key_env":"GOOGLE_API_KEY","capacidades":{"tools":true,"reasoning_param":"thinking_level","niveis_de_esforco":["low","medium","high"],"vision":true,"pdf":true,"max_output":65536,"contexto":1048576,"raciocinio_ida_e_volta":true,"responses_obrigatoria_com_tools":false},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://ai.google.dev/gemini-api/docs/pricing","notas":"0,75/0,075/3,75 SÓ ATÉ 31/12/2026 -> 1,50/0,15/7,50 a partir de 01/01/2027. Sem Live API. Classe só publico até o Founder confirmar tier PAGO + chave local (D-116-06)."},
{"model_name":"gemini-3-flash-preview","provider":"google","tipo":"chat","api_surface":"generate_content","lifecycle":"DEPRECATED","classes_de_dado":["publico","interno","pii"],"input_price_per_million":0.5,"output_price_per_million":3,"cache_read_multiplier":0.1,"cache_write_multiplier":1,"cached_input_multiplier":0.1,"api_key_env":"GOOGLE_API_KEY","substituido_por":"gemini-3.8-flash","preco_verificado_em":"2026-09-23","fonte_preco_url":"https://ai.google.dev/gemini-api/docs/pricing","notas":"'legacy', deprecado sem data (substituto oficial gemini-3.6-flash). Banco tinha 0,10/0,40 (errado)."},
{"model_name":"gemini-3.1-pro-preview","provider":"google","tipo":"chat","api_surface":"generate_content","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"],"input_price_per_million":2,"output_price_per_million":12,"cache_read_multiplier":0.1,"cache_write_multiplier":1,"cached_input_multiplier":0.1,"input_price_long":4,"output_price_long":18,"limiar_contexto_longo":200000,"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://ai.google.dev/gemini-api/docs/pricing","notas":"Preview; não é candidato desta SPEC."},
{"model_name":"gemini-3-pro-preview","provider":"google","tipo":"chat","api_surface":"generate_content","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"],"retirada_em":"2026-03-09","notas":"desligado 09/03/2026."},
{"model_name":"gemini-3-pro-preview-11-2025","display_name":"Gemini 3 Pro Preview 11-2025","provider":"google","tipo":"chat","api_surface":"generate_content","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"],"is_active":false,"notas":"literal do censo; sem preço verificado."},
{"model_name":"gemini-3-deep-think","provider":"google","tipo":"chat","api_surface":"generate_content","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"gemini-2.5-pro","provider":"google","tipo":"chat","api_surface":"generate_content","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"gemini-2.5-flash","provider":"google","tipo":"chat","api_surface":"generate_content","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"gemini-2.5-flash-lite","provider":"google","tipo":"chat","api_surface":"generate_content","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"gemini-2.0-flash","display_name":"Gemini 2.0 Flash","provider":"google","tipo":"chat","api_surface":"generate_content","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"],"is_active":false,"notas":"literal do censo; sem preço verificado."},
{"model_name":"gemini-1.5-pro","provider":"google","tipo":"chat","api_surface":"generate_content","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},
{"model_name":"gemini-1.5-flash","provider":"google","tipo":"chat","api_surface":"generate_content","lifecycle":"HISTORICAL","classes_de_dado":["publico","interno","pii"]},

{"model_name":"grok-4.7","display_name":"Grok 4.7","provider":"xai","tipo":"chat","api_surface":"openai_compat","lifecycle":"CANDIDATE","classes_de_dado":["publico"],"input_price_per_million":2,"output_price_per_million":6,"cache_read_multiplier":0.25,"cache_write_multiplier":1,"cached_input_multiplier":0.25,"input_price_long":4,"output_price_long":12,"limiar_contexto_longo":200000,"base_url":"https://api.x.ai/v1","api_key_env":"XAI_API_KEY","capacidades":{"tools":true,"reasoning_param":"reasoning.effort","niveis_de_esforco":["low","medium","high","xhigh"],"vision":true,"contexto":500000,"tool_choice_forcado_ok":true,"raciocinio_ida_e_volta":true},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://docs.x.ai/developers/release-notes","notas":"lançado 21/09/2026. cached 0,50; >200K 4/1/12. Laboratório: só dado sintético (D-116-06)."},
{"model_name":"grok-4","provider":"xai","tipo":"chat","api_surface":"openai_compat","lifecycle":"HISTORICAL","classes_de_dado":["publico"]},
{"model_name":"grok-3","provider":"xai","tipo":"chat","api_surface":"openai_compat","lifecycle":"HISTORICAL","classes_de_dado":["publico"]},
{"model_name":"mimo-v2.6-pro","display_name":"MiMo V2.6 Pro","provider":"xiaomi","tipo":"chat","api_surface":"openai_compat","lifecycle":"CANDIDATE","classes_de_dado":["publico"],"input_price_per_million":0.435,"output_price_per_million":0.87,"cache_read_multiplier":0.008276,"cache_write_multiplier":1,"cached_input_multiplier":0.008276,"base_url":"https://api.xiaomimimo.com/v1","api_key_env":"MIMO_API_KEY","capacidades":{"tools":true,"reasoning_param":"thinking","niveis_de_esforco":["none","high"],"vision":true,"max_output":128000,"contexto":1000000,"tool_choice_forcado_ok":false,"raciocinio_ida_e_volta":true},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://mimo.mi.com/models/en-US/mimo-v2.6-pro","notas":"cache hit 0,0036. Esforço sem nível (none desliga; o resto liga igual). tool_choice != auto é descartado. Controladora CN, retém 30 d: só publico."},
{"model_name":"mimo-v2.6-flash","display_name":"MiMo V2.6 Flash","provider":"xiaomi","tipo":"chat","api_surface":"openai_compat","lifecycle":"CANDIDATE","classes_de_dado":["publico"],"input_price_per_million":0.14,"output_price_per_million":0.28,"cache_read_multiplier":0.02,"cache_write_multiplier":1,"cached_input_multiplier":0.02,"base_url":"https://api.xiaomimimo.com/v1","api_key_env":"MIMO_API_KEY","capacidades":{"tools":true,"reasoning_param":"thinking","niveis_de_esforco":["none","high"],"vision":true,"max_output":128000,"contexto":1000000,"tool_choice_forcado_ok":false,"raciocinio_ida_e_volta":true},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://mimo.mi.com/static/docs/quick-start/usage-guide/text-generation/batch-api.md","notas":"cache hit 0,0028. Só publico."},
{"model_name":"deepseek-flash","display_name":"DeepSeek V4.1 Flash","provider":"deepseek","tipo":"chat","api_surface":"openai_compat","lifecycle":"CANDIDATE","classes_de_dado":["publico"],"input_price_per_million":0.3,"output_price_per_million":1.2,"cache_read_multiplier":0.02,"cache_write_multiplier":1,"cached_input_multiplier":0.02,"base_url":"https://api.deepseek.com","api_key_env":"DEEPSEEK_API_KEY","capacidades":{"tools":true,"reasoning_param":"reasoning_effort","niveis_de_esforco":["low","high","max"],"vision":true,"max_output":384000,"contexto":1000000,"raciocinio_ida_e_volta":true},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://api-docs.deepseek.com/quick_start/pricing","notas":"V4.1 Flash (id deepseek-flash). Pico 0,30/0,006/1,20; off-peak 50% (horário comercial BR inteiro é off-peak). reasoning_content OBRIGATÓRIO de volta (400). API nativa na China: só via host terceiro com ZDR; só publico."},
{"model_name":"deepseek-chat","provider":"deepseek","tipo":"chat","api_surface":"openai_compat","lifecycle":"HISTORICAL","classes_de_dado":["publico"]},
{"model_name":"glm-5.3","display_name":"GLM-5.3","provider":"zai","tipo":"chat","api_surface":"openai_compat","lifecycle":"CANDIDATE","classes_de_dado":["publico"],"input_price_per_million":1.4,"output_price_per_million":4.4,"cache_read_multiplier":0.185714,"cache_write_multiplier":1,"cached_input_multiplier":0.185714,"base_url":"https://api.z.ai/api/paas/v4","api_key_env":"ZAI_API_KEY","capacidades":{"tools":true,"reasoning_param":"reasoning_effort","niveis_de_esforco":["low","high","max"],"vision":false,"max_output":128000,"contexto":1000000,"raciocinio_ida_e_volta":true},"preco_verificado_em":"2026-09-23","fonte_preco_url":"https://docs.z.ai/guides/overview/pricing","notas":"cached 0,26. Thinking não desliga (disabled -> 400). Só texto. Singapura/matriz CN: só publico."},
{"model_name":"mistral-large-latest","provider":"mistral","tipo":"chat","api_surface":"openai_compat","lifecycle":"HISTORICAL","classes_de_dado":["publico"]},

{"model_name":"rerank-multilingual-v3.0","display_name":"Cohere Rerank Multilingual v3.0","provider":"cohere","tipo":"rerank","api_surface":"rerank","lifecycle":"APPROVED","classes_de_dado":["publico","interno","pii"],"input_price_per_million":0,"output_price_per_million":0,"unit":"search","api_key_env":"COHERE_API_KEY","notas":"PREÇO DESCONHECIDO: preço por busca não está nas evidências SPEC-116 (04/05). 0/0 = desconhecido para o UsageService. Chamada hoje fora do ledger (rerank_service.py)."},
{"model_name":"meta-llama/llama-prompt-guard-2-86m","display_name":"Llama Prompt Guard 2 86M (Groq)","provider":"groq","tipo":"guard","api_surface":"guard","lifecycle":"DEPRECATED","classes_de_dado":["publico"],"input_price_per_million":0,"output_price_per_million":0,"api_key_env":"GROQ_API_KEY","notas":"guardrail anti-jailbreak; DESLIGADO em prod (GROQ_API_KEY vazia). Registrado, NÃO decidido (pendência)."}
]
$catalogo$::jsonb) as e;

-- 2a. linhas que JÁ existem: atualiza metadados; preço só se o JSON trouxer.
update public.llm_pricing p set
  provider                 = coalesce(c.linha->>'provider', p.provider),
  tipo                     = coalesce(c.linha->>'tipo', p.tipo),
  api_surface              = coalesce(c.linha->>'api_surface', p.api_surface),
  lifecycle                = c.linha->>'lifecycle',
  classes_de_dado          = case when c.linha ? 'classes_de_dado'
                                  then array(select jsonb_array_elements_text(c.linha->'classes_de_dado'))
                                  else p.classes_de_dado end,
  capacidades              = coalesce(c.linha->'capacidades', p.capacidades, '{}'::jsonb),
  substituido_por          = coalesce(c.linha->>'substituido_por', p.substituido_por),
  retirada_em              = coalesce((c.linha->>'retirada_em')::date, p.retirada_em),
  input_price_per_million  = coalesce((c.linha->>'input_price_per_million')::numeric, p.input_price_per_million),
  output_price_per_million = coalesce((c.linha->>'output_price_per_million')::numeric, p.output_price_per_million),
  cache_read_multiplier    = coalesce((c.linha->>'cache_read_multiplier')::numeric, p.cache_read_multiplier),
  cache_write_multiplier   = coalesce((c.linha->>'cache_write_multiplier')::numeric, p.cache_write_multiplier),
  cached_input_multiplier  = coalesce((c.linha->>'cached_input_multiplier')::numeric, p.cached_input_multiplier),
  input_price_long         = coalesce((c.linha->>'input_price_long')::numeric, p.input_price_long),
  output_price_long        = coalesce((c.linha->>'output_price_long')::numeric, p.output_price_long),
  limiar_contexto_longo    = coalesce((c.linha->>'limiar_contexto_longo')::integer, p.limiar_contexto_longo),
  unit                     = coalesce(c.linha->>'unit', p.unit),
  base_url                 = coalesce(c.linha->>'base_url', p.base_url),
  api_key_env              = coalesce(c.linha->>'api_key_env', p.api_key_env),
  preco_verificado_em      = coalesce((c.linha->>'preco_verificado_em')::date, p.preco_verificado_em),
  fonte_preco_url          = coalesce(c.linha->>'fonte_preco_url', p.fonte_preco_url),
  notas                    = coalesce(c.linha->>'notas', p.notas),
  updated_at               = now()
from _spec116_catalogo c
where p.model_name = c.linha->>'model_name';

-- 2b. linhas NOVAS. Sem preço no JSON -> 0/0 e is_active=false (o UsageService
--     trata como preço DESCONHECIDO, nunca como o do mini).
insert into public.llm_pricing (model_name, provider, display_name, input_price_per_million,
  output_price_per_million, unit, is_active, cache_read_multiplier, cache_write_multiplier,
  cached_input_multiplier, lifecycle, tipo, api_surface, capacidades, classes_de_dado,
  substituido_por, retirada_em, input_price_long, output_price_long, limiar_contexto_longo,
  base_url, api_key_env, preco_verificado_em, fonte_preco_url, notas)
select c.linha->>'model_name', c.linha->>'provider',
       coalesce(c.linha->>'display_name', c.linha->>'model_name'),
       coalesce((c.linha->>'input_price_per_million')::numeric, 0),
       coalesce((c.linha->>'output_price_per_million')::numeric, 0),
       coalesce(c.linha->>'unit', 'token'),
       coalesce((c.linha->>'is_active')::boolean, true),
       coalesce((c.linha->>'cache_read_multiplier')::numeric, 1),
       coalesce((c.linha->>'cache_write_multiplier')::numeric, 1),
       coalesce((c.linha->>'cached_input_multiplier')::numeric, 1),
       c.linha->>'lifecycle', c.linha->>'tipo', c.linha->>'api_surface',
       coalesce(c.linha->'capacidades', '{}'::jsonb),
       array(select jsonb_array_elements_text(c.linha->'classes_de_dado')),
       c.linha->>'substituido_por', (c.linha->>'retirada_em')::date,
       (c.linha->>'input_price_long')::numeric, (c.linha->>'output_price_long')::numeric,
       (c.linha->>'limiar_contexto_longo')::integer,
       c.linha->>'base_url', c.linha->>'api_key_env',
       (c.linha->>'preco_verificado_em')::date, c.linha->>'fonte_preco_url', c.linha->>'notas'
  from _spec116_catalogo c
 where not exists (select 1 from public.llm_pricing p where p.model_name = c.linha->>'model_name')
on conflict (model_name) do nothing;

drop table if exists _spec116_catalogo;

-- 2c. rede de segurança: nada fica sem ciclo de vida. Desconhecido = HISTORICAL
--     (o resolvedor recusa). 📊 com o JSON acima, hoje não sobra nenhuma.
update public.llm_pricing set lifecycle = 'HISTORICAL', updated_at = now()
 where lifecycle is null;

-- -------------------------------------------------------------
-- 3. Rotas por PAPEL. Config de PLATAFORMA — SEM company_id, de propósito
--    (CLAUDE.md §7): é dado global de produto que diz "que modelo faz que
--    trabalho"; não carrega dado de corretora, de segurado nem segredo. A
--    escolha POR corretora, se um dia existir, entra como override governado
--    no resolvedor, nunca como cópia desta tabela por tenant.
-- -------------------------------------------------------------
create table if not exists public.llm_papeis (
  papel             text primary key,
  descricao         text,
  provider          text not null,
  modelo_primario   text not null
                      references public.llm_pricing(model_name) on update restrict on delete restrict,
  esforco           text,
  provider_reserva  text,
  modelo_reserva    text
                      references public.llm_pricing(model_name) on update restrict on delete restrict,
  esforco_reserva   text,
  classe_de_dado    text not null,
  risco             text not null,
  versao            integer not null default 1,
  motivo            text not null,
  atualizado_em     timestamptz not null default now(),
  atualizado_por    text,
  constraint llm_papeis_classe_valida  check (classe_de_dado in ('publico','interno','pii')),
  constraint llm_papeis_risco_valido   check (risco in ('baixo','medio','alto','critico')),
  constraint llm_papeis_esforco_valido check (esforco is null or esforco in ('none','low','medium','high','xhigh','max')),
  constraint llm_papeis_esforco_reserva_valido
                                       check (esforco_reserva is null or esforco_reserva in ('none','low','medium','high','xhigh','max')),
  constraint llm_papeis_reserva_completa
                                       check ((modelo_reserva is null) = (provider_reserva is null))
);

comment on table public.llm_papeis is
  'SPEC-116 U2: rota de modelo por PAPEL (trabalho). Global de plataforma, sem company_id: não guarda dado de cliente. Todo UPDATE versiona e grava llm_papeis_historico (rollback = reaplicar a linha anterior).';

-- Histórico: auditoria. SEM FK para llm_papeis de propósito — a trilha de quem
-- trocou o quê precisa sobreviver até à remoção de um papel.
create table if not exists public.llm_papeis_historico (
  id              bigint generated always as identity primary key,
  papel           text not null,
  linha_anterior  jsonb not null,
  linha_nova      jsonb not null,
  versao          integer not null,
  motivo          text,
  alterado_em     timestamptz not null default now(),
  alterado_por    text
);
create index if not exists ix_llm_papeis_historico_papel
  on public.llm_papeis_historico (papel, versao desc);

comment on table public.llm_papeis_historico is
  'SPEC-116 U2: uma linha por troca de rota (antes/depois, versão, motivo, quem). Escrita só pelo trigger.';

-- Trigger: versiona e grava histórico quando a ROTA muda. SECURITY INVOKER,
-- search_path fixo, sem EXECUTE para anon/authenticated (advisors não crescem).
create or replace function public.llm_papeis_registrar_historico()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, public
as $fn$
begin
  if (to_jsonb(new) - 'versao' - 'atualizado_em' - 'atualizado_por' - 'motivo')
     is not distinct from
     (to_jsonb(old) - 'versao' - 'atualizado_em' - 'atualizado_por' - 'motivo') then
    return new;   -- nada da ROTA mudou: sem versão nova, sem histórico
  end if;
  new.versao        := old.versao + 1;
  new.atualizado_em := now();
  insert into public.llm_papeis_historico
    (papel, linha_anterior, linha_nova, versao, motivo, alterado_por)
  values
    (new.papel, to_jsonb(old), to_jsonb(new), new.versao, new.motivo, new.atualizado_por);
  return new;
end;
$fn$;

revoke all on function public.llm_papeis_registrar_historico() from public;
revoke all on function public.llm_papeis_registrar_historico() from anon, authenticated;

drop trigger if exists trg_llm_papeis_historico on public.llm_papeis;
create trigger trg_llm_papeis_historico
  before update on public.llm_papeis
  for each row execute function public.llm_papeis_registrar_historico();

-- RLS: o mesmo desenho de llm_pricing (📊 23/09: RLS ligada + UMA policy
-- SELECT "Anyone can read pricing"), só que mais estreito — leitura para
-- `authenticated`, nenhuma policy de escrita (quem escreve é o service role,
-- que ignora RLS, ou uma migration).
alter table public.llm_papeis enable row level security;
alter table public.llm_papeis_historico enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='llm_papeis'
                   and policyname='llm_papeis_leitura') then
    create policy llm_papeis_leitura on public.llm_papeis
      for select to authenticated using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='llm_papeis_historico'
                   and policyname='llm_papeis_historico_leitura') then
    create policy llm_papeis_historico_leitura on public.llm_papeis_historico
      for select to authenticated using (true);
  end if;
end $$;

-- -------------------------------------------------------------
-- 4. SEED das rotas = o runtime de 23/09/2026 (EVIDENCIAS/01 tabelas a/b +
--    env de produção). 🔴 FONTE ÚNICA: o gerador do snapshot lê o texto entre
--    as marcas $papeis$. ON CONFLICT DO NOTHING: reaplicar nunca desfaz troca.
-- -------------------------------------------------------------
insert into public.llm_papeis (papel, descricao, provider, modelo_primario, esforco,
  provider_reserva, modelo_reserva, esforco_reserva, classe_de_dado, risco, motivo, atualizado_por)
select r->>'papel', r->>'descricao', r->>'provider', r->>'modelo_primario', r->>'esforco',
       r->>'provider_reserva', r->>'modelo_reserva', r->>'esforco_reserva',
       r->>'classe_de_dado', r->>'risco',
       'seed SPEC-116: reproduz o runtime de 23/09 (EVIDENCIAS/01)', 'migration 20260923_01'
  from jsonb_array_elements($papeis$
[
{"papel":"chat_principal","descricao":"chat do corretor com o AutoBrokers (agente core) — graph.py via llm_factory","provider":"anthropic","modelo_primario":"claude-sonnet-5","esforco":null,"classe_de_dado":"pii","risco":"alto"},
{"papel":"atendimento","descricao":"atendente que fala com o SEGURADO (attendance/insured_external) — graph.py via llm_factory","provider":"anthropic","modelo_primario":"claude-sonnet-5","esforco":null,"classe_de_dado":"pii","risco":"critico"},
{"papel":"subagente","descricao":"subagentes do core e agentes custom — subagent_tool.py via llm_factory","provider":"anthropic","modelo_primario":"claude-sonnet-5","esforco":null,"classe_de_dado":"pii","risco":"medio"},
{"papel":"dispatch","descricao":"acionamento: fala com a URA da seguradora — webhook.py, dispatch_watchdog.py, dispatch_router.py (env DISPATCH_LLM_MODEL=claude-opus-5 em prod)","provider":"anthropic","modelo_primario":"claude-opus-5","esforco":null,"classe_de_dado":"pii","risco":"critico"},
{"papel":"atlas_parser","descricao":"Atlas: escolhas tipadas das telas — atlas_parser.py (env ATLAS_PARSER_MODEL=claude-opus-5 em prod)","provider":"anthropic","modelo_primario":"claude-opus-5","esforco":null,"classe_de_dado":"interno","risco":"medio"},
{"papel":"distiller","descricao":"destilador estágio 1 (braçal) — attendance_distiller.py DISTILLER_LLM_MODEL","provider":"anthropic","modelo_primario":"claude-sonnet-5","esforco":null,"classe_de_dado":"pii","risco":"medio"},
{"papel":"distiller_forte","descricao":"destilador estágio 2: playbook — attendance_distiller.py DISTILLER_STRONG_MODEL (strong=True)","provider":"anthropic","modelo_primario":"claude-opus-5","esforco":null,"classe_de_dado":"pii","risco":"alto"},
{"papel":"prompt_optimizer","descricao":"lapidador semanal de playbook — prompt_optimizer.py:178 (_call_llm strong=True, hoje o MESMO env do distiller_forte)","provider":"anthropic","modelo_primario":"claude-opus-5","esforco":null,"classe_de_dado":"pii","risco":"medio"},
{"papel":"juiz_playbook","descricao":"juiz do gate de playbook — playbook_gate.py (DISTILLER_STRONG_MODEL, hoje o MESMO env do distiller_forte)","provider":"anthropic","modelo_primario":"claude-opus-5","esforco":null,"classe_de_dado":"pii","risco":"medio"},
{"papel":"extrator_planos","descricao":"extração de planos de assistência de PDF público — assistance_plans_extractor.py","provider":"anthropic","modelo_primario":"claude-sonnet-5","esforco":null,"classe_de_dado":"publico","risco":"medio"},
{"papel":"garimpo","descricao":"insights do corretor (GARIMPO_LLM, desligado por default) — broker_insights.py","provider":"anthropic","modelo_primario":"claude-sonnet-5","esforco":null,"classe_de_dado":"pii","risco":"baixo"},
{"papel":"sugestoes","descricao":"sugestões proativas (SUGESTOES_LLM, desligado por default) — proactive_suggestions.py","provider":"anthropic","modelo_primario":"claude-opus-5","esforco":null,"classe_de_dado":"pii","risco":"baixo"},
{"papel":"brand_capture","descricao":"leitura do site público da corretora — brand/capture.py","provider":"anthropic","modelo_primario":"claude-sonnet-5","esforco":null,"classe_de_dado":"publico","risco":"baixo"},
{"papel":"juiz_eval","descricao":"juiz LLM da Eval Fabric (SPEC-062) sobre corpus mascarado — evals/juiz_llm.py (hoje quebrado, F3 conserta)","provider":"anthropic","modelo_primario":"claude-sonnet-5","esforco":null,"classe_de_dado":"interno","risco":"medio"},
{"papel":"conselho_lider","descricao":"líder do agent council (COUNCIL_ENABLED=0) — agent_council.py","provider":"anthropic","modelo_primario":"claude-opus-5","esforco":null,"classe_de_dado":"pii","risco":"medio"},
{"papel":"visao","descricao":"visão de foto do segurado/corretor — vision_service.py, langchain_service._analyze_image, attendance_media.py, observer","provider":"openai","modelo_primario":"gpt-4o-mini","esforco":null,"classe_de_dado":"pii","risco":"alto"},
{"papel":"visao_documento","descricao":"descrição de imagem dentro de PDF (docling-service VISION_MODEL)","provider":"openai","modelo_primario":"gpt-4o-mini","esforco":null,"classe_de_dado":"pii","risco":"medio"},
{"papel":"memoria","descricao":"memória: resumo de sessão e fatos do usuário — memory_service.py (memory_settings DEFAULT gpt-4o-mini)","provider":"openai","modelo_primario":"gpt-4o-mini","esforco":null,"classe_de_dado":"pii","risco":"alto"},
{"papel":"hyde","descricao":"documento hipotético do RAG (chat e atendimento) — search_service.py:381","provider":"openai","modelo_primario":"gpt-4o-mini","esforco":null,"classe_de_dado":"pii","risco":"medio"},
{"papel":"chunking_agentico","descricao":"chunking agêntico na ingestão — ingestion_service.py:380","provider":"openai","modelo_primario":"gpt-4o-mini","esforco":null,"classe_de_dado":"interno","risco":"medio"},
{"papel":"auxiliar","descricao":"auxiliares instalados: resumo e follow-up ao CLIENTE FINAL — auxiliaries.py (AUXILIAR_LLM_MODEL)","provider":"anthropic","modelo_primario":"claude-haiku-4-5-20251001","esforco":null,"classe_de_dado":"pii","risco":"alto"},
{"papel":"portal_decisao","descricao":"portal worker: decide o próximo clique — portal_worker/adaptive.py (PORTAL_VISION_MODEL ausente -> gpt-4o). Reserva NULA: o rebaixamento calado ao mini é defeito (F3 tira)","provider":"openai","modelo_primario":"gpt-4o","esforco":null,"classe_de_dado":"pii","risco":"critico"},
{"papel":"transcricao","descricao":"áudio do segurado -> texto — audio_service.py","provider":"openai","modelo_primario":"whisper-1","esforco":null,"classe_de_dado":"pii","risco":"alto"},
{"papel":"embedding","descricao":"embeddings de consulta e ingestão (RAG) — search_service, ingestion_service, etc.","provider":"openai","modelo_primario":"text-embedding-3-small","esforco":null,"classe_de_dado":"pii","risco":"medio"},
{"papel":"rerank","descricao":"rerank do RAG — rerank_service.py (Cohere)","provider":"cohere","modelo_primario":"rerank-multilingual-v3.0","esforco":null,"classe_de_dado":"pii","risco":"medio"}
]
$papeis$::jsonb) as r
on conflict (papel) do nothing;
