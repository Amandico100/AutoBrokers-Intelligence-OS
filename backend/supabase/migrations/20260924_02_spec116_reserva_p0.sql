-- =============================================================
-- MIGRATION: 20260924_02_spec116_reserva_p0
-- SPEC:      SPEC-116-RESERVA — reserva cross-provider nos caminhos P0
-- AUTOR:     builder SPEC-116-RESERVA (Opus 5.5)        DATA: 2026-09-24
-- OBJETIVO:  declarar a RESERVA (outro provedor) nos 4 papéis P0. Nenhum outro
--            papel ganha reserva. Nenhuma coluna, função ou trigger muda.
--
-- EVIDÊNCIA:
--   📊 24/09/2026 (MCP execute_sql: select count(*) filter (where modelo_reserva
--      is null), count(*) from public.llm_papeis) → 25 nulas / 25 rotas.
--   📊 24/09/2026 (modelos_snapshot.json, catálogo depois de 20260924_01):
--      gpt-6-sol       APPROVED · classes {interno,pii,publico} · esforço none..max · sem mínimo
--      claude-opus-5-5 APPROVED · classes {interno,pii,publico} · esforço low..max  · sem mínimo
--   O trigger vigente (20260924_01 §C, llm_papeis_so_modelo_governado) confere a
--   reserva com a MESMA regra do primário: catálogo · provider igual ao do
--   catálogo · APPROVED · classe de dado (pii nos 4 papéis) · esforço nos níveis.
--   Reserva Opus com esforço NULO (padrão do provedor); reserva Sol do dispatch
--   com esforço 'high' (Sol aceita). → as 4 linhas passam na trava.
--
-- MAPA (Founder 24/09/2026):
--   atendimento    openai/gpt-6-sol high        → anthropic/claude-opus-5-5 (NULL)
--   chat_principal openai/gpt-6-sol medium      → anthropic/claude-opus-5-5 (NULL)
--   portal_decisao openai/gpt-6-sol medium      → anthropic/claude-opus-5-5 (NULL)
--   dispatch       anthropic/claude-opus-5-5    → openai/gpt-6-sol high
--
-- APPLY:  o UPDATE abaixo (idempotente: só toca linha que difere) + asserção.
--
-- VERIFY:
--   -- 1) a tabela primário → reserva
--   select papel, provider, modelo_primario, esforco,
--          provider_reserva, modelo_reserva, esforco_reserva
--     from public.llm_papeis where modelo_reserva is not null order by papel;
--   -- esperado (4):
--   --   atendimento    openai    gpt-6-sol       high   | anthropic claude-opus-5-5 NULL
--   --   chat_principal openai    gpt-6-sol       medium | anthropic claude-opus-5-5 NULL
--   --   dispatch       anthropic claude-opus-5-5 NULL   | openai    gpt-6-sol       high
--   --   portal_decisao openai    gpt-6-sol       medium | anthropic claude-opus-5-5 NULL
--   -- 2) os outros 21 papéis continuam SEM reserva
--   select count(*) from public.llm_papeis
--    where modelo_reserva is null
--      and papel not in ('atendimento','chat_principal','portal_decisao','dispatch');
--   -- esperado: 21   (e: select count(*) from public.llm_papeis where modelo_reserva is not null → 4)
--   -- 3) a reserva está na regra de produção (0 fora)
--   select count(*) from public.llm_papeis r join public.llm_pricing q on q.model_name = r.modelo_reserva
--    where q.lifecycle is distinct from 'APPROVED' or q.provider is distinct from r.provider_reserva
--       or r.provider_reserva = r.provider;
--   -- esperado: 0 (APPROVED, provider do catálogo, e CROSS-provider)
--   -- 4) a trava ainda RECUSA reserva ruim (SAVEPOINT; nada fica gravado)
--   do $$ declare recusas int := 0; begin
--     begin update public.llm_papeis set esforco_reserva = 'none'
--            where papel = 'atendimento';  -- Opus 5.5 não aceita 'none'
--     exception when check_violation then recusas := recusas + 1; end;
--     begin update public.llm_papeis set modelo_reserva = 'claude-sonnet-5'
--            where papel = 'dispatch';     -- DEPRECATED + provider divergente
--     exception when check_violation then recusas := recusas + 1; end;
--     if recusas <> 2 then raise exception 'VERIFY 20260924_02 FALHOU: recusas=%', recusas; end if;
--     raise notice 'VERIFY 20260924_02 OK: 2 recusas';
--   end $$;
--   -- 5) depois do VERIFY: regenerar backend/app/factories/modelos_snapshot.json
--   --    (o snapshot é o que o resolver usa com o banco fora — ele tem de trazer a reserva).
--
-- ROLLBACK:  (escrito ANTES de aplicar; o trigger de histórico registra a volta)
--   update public.llm_papeis
--      set provider_reserva = null, modelo_reserva = null, esforco_reserva = null,
--          motivo = 'rollback 20260924_02', atualizado_por = 'rollback'
--    where papel in ('atendimento','chat_principal','portal_decisao','dispatch')
--      and modelo_reserva is not null;
--   -- e regenerar o snapshot.
--
-- EXPAND-FIRST: sim (só dados; nenhuma estrutura muda).
-- DESTRUTIVA:   não (llm_papeis_historico guarda a versão anterior de cada linha).
-- =============================================================

update public.llm_papeis r
   set provider_reserva = a.provider_reserva,
       modelo_reserva   = a.modelo_reserva,
       esforco_reserva  = a.esforco_reserva,
       motivo = 'SPEC-116-RESERVA · Founder 24/09/2026 — reserva cross-provider P0',
       atualizado_por = 'migration 20260924_02'
  from (values
    ('atendimento',    'anthropic', 'claude-opus-5-5', null::text),
    ('chat_principal', 'anthropic', 'claude-opus-5-5', null::text),
    ('portal_decisao', 'anthropic', 'claude-opus-5-5', null::text),
    ('dispatch',       'openai',    'gpt-6-sol',       'high')
  ) as a(papel, provider_reserva, modelo_reserva, esforco_reserva)
 where r.papel = a.papel
   and (r.provider_reserva, r.modelo_reserva, r.esforco_reserva)
       is distinct from (a.provider_reserva, a.modelo_reserva, a.esforco_reserva);

-- ASSERÇÃO: exatamente os 4 papéis P0 com reserva, cross-provider; o resto nulo.
do $$
declare v_com int; v_errados text;
begin
  select count(*) into v_com from public.llm_papeis where modelo_reserva is not null;
  select string_agg(papel, ', ') into v_errados from public.llm_papeis
   where (modelo_reserva is not null)
         <> (papel in ('atendimento','chat_principal','portal_decisao','dispatch'))
      or (modelo_reserva is not null and provider_reserva = provider);
  if v_com <> 4 or v_errados is not null then
    raise exception '20260924_02: reservas fora do mapa (com reserva=%, errados=%)', v_com, v_errados;
  end if;
end $$;
