-- =============================================================
-- MIGRATION: 20261001_03_spec124_visao_por_bancada
-- SPEC:      SPEC-124 — F2 · a visão certa (D3)
-- AUTOR:     builder F2 (Opus 5.5 xhigh)      DATA: 2026-10-01
-- OBJETIVO:  a leitura de documento passa ao modelo que a BANCADA POR CAMPO mediu com o mesmo acerto
--            e o menor custo por documento: `visao` = openai/gpt-6-luna medium com reserva de OUTRO
--            provedor anthropic/claude-sonnet-5-5 low; `visao_documento` = openai/gpt-6-luna medium,
--            SEM reserva (o docling só fala Chat Completions OpenAI — a reserva Anthropic não passa por ele).
--
-- EVIDÊNCIA (docs/canon/reports/SPEC-124-BANCADA-VISAO.md; JSONs no scratchpad da F2):
--   📊 01/10/2026 bancada `visao_campos` (10 documentos sintéticos × k=3, 12 campos cada, juiz por campo
--      normalizado; `python scripts/bancada.py --resumo-visao … --recalcular`):
--        gpt-6-luna medium        nota D3 100,0 % · 30/30 documentos perfeitos · US$ 0,00016/doc
--        gpt-6.1-sol medium       nota D3 100,0 % · 30/30                      · US$ 0,00566/doc (1ª passada,
--                                 sem cache) · 0,00226/doc (passadas 2–3, com cache de prompt)
--        claude-sonnet-5-5 low    nota D3 100,0 % · 30/30                      · US$ 0,00548/doc
--      📊 ledger (token_usage_logs, service_type='bancada', details.papel='visao', chamadas SEM cache):
--        Luna US$ 0,000202/chamada (n=23) · Sol 6.1 0,003673 (n=22) · Sonnet 5.5 0,005586 (n=40).
--      Empate técnico (0 pontos ≤ 2) → o mais barato (D3). G4: Luna acerta = Sol 6.1 e custa ~1/18.
--   📊 01/10/2026 bancada `visao` (o prompt de DESCRIÇÃO do produto, describe_image, 10 casos k=1):
--      Luna 10/10 · Sol 6.1 10/10 · Sonnet 5.5 low 10/10.
--   📊 01/10/2026 smoke: o pedido EXATO do docling 2.130 (Chat Completions, image_url + text,
--      max_completion_tokens 8192, reasoning_effort medium) com gpt-6-luna → HTTP 200, finish stop,
--      `usage` devolvido (966 in / 169 out / 120 de raciocínio).
--   📊 01/10/2026 (SELECT, antes): visao = openai/gpt-6.1-sol medium, reserva NULA, versao 4;
--      visao_documento = openai/gpt-6.1-sol medium, reserva NULA, versao 3. Luna e Sonnet 5.5 APPROVED;
--      Luna `esforco_minimo_producao` = medium (atendido); Sonnet aceita `low`.
--   ⚠️ o corpus é SINTÉTICO (não há documento real mascarado): o número é TETO, não piso.
--
-- APPLY:
--   A. visao: primário gpt-6-luna medium, reserva anthropic/claude-sonnet-5-5 low (só se diferente —
--      reaplicar não sobe a versão; o trigger de histórico grava a linha anterior).
--   B. visao_documento: primário gpt-6-luna medium, reserva NULA (idem).
--   C. asserção: aborta a migration inteira se o estado final não for o de A e B.
--
-- VERIFY:
--   select papel, provider, modelo_primario, esforco, provider_reserva, modelo_reserva, esforco_reserva,
--          versao, atualizado_por
--     from public.llm_papeis where papel in ('visao','visao_documento') order by 1;
--   -- esperado: visao           openai gpt-6-luna medium anthropic claude-sonnet-5-5 low  5 migration 20261001_03
--   --           visao_documento openai gpt-6-luna medium NULL      NULL              NULL 4 migration 20261001_03
--   select papel, versao, modelo_primario from public.llm_papeis_historico
--    where papel in ('visao','visao_documento') and alterado_por = 'migration 20261001_03' order by 1;
--   -- esperado 2 linhas (o estado ANTERIOR: gpt-6.1-sol)
--   -- e o produto lê a rota nova (o resolvedor, com o snapshot regerado):
--   --   python scripts/gerar_snapshot_de_modelos.py --banco
--   --   python -c "from app.factories import model_policy as M; r=M.resolver('visao'); print(r.model, r.effort, r.reserva.model, r.reserva.effort)"
--   --   -- esperado: gpt-6-luna medium claude-sonnet-5-5 low
--
-- ROLLBACK:  (escrito ANTES de aplicar; o trigger de histórico registra a volta)
--   update public.llm_papeis
--      set provider = 'openai', modelo_primario = 'gpt-6.1-sol', esforco = 'medium',
--          provider_reserva = null, modelo_reserva = null, esforco_reserva = null,
--          motivo = 'ROLLBACK 20261001_03 — volta ao GPT-6.1 Sol', atualizado_por = 'rollback 20261001_03'
--    where papel in ('visao', 'visao_documento');
--   delete from supabase_migrations.schema_migrations where name = 'spec124_visao_por_bancada';
--   -- e regerar o snapshot: python scripts/gerar_snapshot_de_modelos.py --banco
--
-- EXPAND-FIRST: sim — nenhuma coluna, CHECK, trava ou linha de catálogo muda; só 2 rotas.
-- DESTRUTIVA:   não — 2 rotas trocadas (histórico em llm_papeis_historico); reversível pelo ROLLBACK.
-- =============================================================

-- -------------------------------------------------------------
-- A. visao (foto do segurado / do corretor) — Luna, reserva Sonnet 5.5 (outro provedor)
-- -------------------------------------------------------------
update public.llm_papeis
   set provider = 'openai', modelo_primario = 'gpt-6-luna', esforco = 'medium',
       provider_reserva = 'anthropic', modelo_reserva = 'claude-sonnet-5-5', esforco_reserva = 'low',
       motivo = 'SPEC-124 F2 · D3 — bancada por campo 01/10/2026: Luna 100 % = Sol 6.1 100 % a ~1/18 do custo; '
                || 'reserva de outro provedor Sonnet 5.5 low (100 %)',
       atualizado_por = 'migration 20261001_03'
 where papel = 'visao'
   and (provider, modelo_primario, esforco, provider_reserva, modelo_reserva, esforco_reserva)
       is distinct from ('openai', 'gpt-6-luna', 'medium', 'anthropic', 'claude-sonnet-5-5', 'low');

-- -------------------------------------------------------------
-- B. visao_documento (imagem dentro de PDF, pelo docling) — Luna, sem reserva
-- -------------------------------------------------------------
update public.llm_papeis
   set provider = 'openai', modelo_primario = 'gpt-6-luna', esforco = 'medium',
       provider_reserva = null, modelo_reserva = null, esforco_reserva = null,
       motivo = 'SPEC-124 F2 · D3/D4 — Luna (bancada por campo 01/10/2026); sem reserva: o docling só fala '
                || 'Chat Completions OpenAI (PictureDescriptionApiOptions)',
       atualizado_por = 'migration 20261001_03'
 where papel = 'visao_documento'
   and (provider, modelo_primario, esforco, provider_reserva, modelo_reserva, esforco_reserva)
       is distinct from ('openai', 'gpt-6-luna', 'medium', null::text, null::text, null::text);

-- -------------------------------------------------------------
-- C. asserção — o estado final é o desta migration, ou nada fica
-- -------------------------------------------------------------
do $$
declare n int;
begin
  select count(*) into n from public.llm_papeis
   where (papel = 'visao' and provider = 'openai' and modelo_primario = 'gpt-6-luna' and esforco = 'medium'
          and provider_reserva = 'anthropic' and modelo_reserva = 'claude-sonnet-5-5' and esforco_reserva = 'low')
      or (papel = 'visao_documento' and provider = 'openai' and modelo_primario = 'gpt-6-luna'
          and esforco = 'medium' and modelo_reserva is null);
  if n <> 2 then
    raise exception '20261001_03: estado final inesperado (% de 2 rotas certas)', n;
  end if;
end $$;
