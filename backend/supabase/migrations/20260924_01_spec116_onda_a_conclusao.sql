-- =============================================================
-- MIGRATION: 20260924_01_spec116_onda_a_conclusao
-- SPEC:      SPEC-116 — conclusão da Onda A (decisão do Founder 24/09/2026)
-- AUTOR:     builder SPEC-116 conclusão (Opus 5.5)      DATA: 2026-09-24
-- OBJETIVO:  (1) catálogo: só o que roda em produção é APPROVED; o legado vira
--            DEPRECATED; (2) todas as rotas saem do legado (GPT-6 Sol/Luna,
--            Opus 5.5, gpt-transcribe); (3) o trigger passa a aceitar em rota de
--            PRODUÇÃO só lifecycle APPROVED (primário E reserva) e esforço ≥
--            `capacidades.esforco_minimo_producao` quando o modelo o declara.
--
-- ⚠️ ORDEM NO ARQUIVO: catálogo → rotas → trigger → asserção final. A asserção
--   final (bloco DO) aborta a migration inteira se QUALQUER rota ficar fora da
--   regra nova — aplicar numa transação (o apply_migration do Supabase já é).
--
-- EVIDÊNCIA:
--   📊 24/09/2026 (SELECT llm_papeis, antes): 25 rotas; 9 em claude-sonnet-5,
--      7 em claude-opus-5, 1 em claude-haiku-4-5-20251001, 4 em gpt-4o-mini,
--      1 em whisper-1, 2 em gpt-6-sol (portal medium, visao low), 1 em
--      gpt-6-luna low (memoria), embedding e rerank. Todas as reservas NULAS.
--   📊 24/09/2026 (SELECT llm_pricing): gpt-6-sol/gpt-6-luna/claude-opus-5-5/
--      gpt-transcribe têm classes_de_dado {publico,interno,pii} — nada a
--      corrigir (EVIDENCIAS/04 §2: OpenAI e Anthropic sob DPA; o risco de PII
--      é Fable/Mythos "Covered Models", que não entram em rota).
--   gpt-transcribe: US$0,0045/min, /audio/transcriptions (EVIDENCIAS/04 l.54;
--      já no catálogo com unit=minute, api_surface=stt — só muda o lifecycle).
--   Opus 5.5: níveis low/medium/high/xhigh/max; todas as rotas Opus 5 tinham
--      esforço NULO → continuam NULO (default do provedor = medium).
--
-- APPLY:
--   A. llm_pricing: APPROVED ← gpt-6-sol, gpt-6-luna, gpt-transcribe
--      (claude-opus-5-5, text-embedding-3-small, rerank-multilingual-v3.0 já são);
--      DEPRECATED ← claude-sonnet-5, claude-opus-5 (substituido_por
--      claude-opus-5-5), claude-haiku-4-5, claude-haiku-4-5-20251001
--      (gpt-4o, gpt-4o-mini*, whisper-1, gemini-3-flash-preview já são);
--      gpt-6-luna.capacidades.esforco_minimo_producao = "medium".
--   B. llm_papeis: as rotas abaixo (o trigger de histórico versiona cada uma);
--      reserva que não seja APPROVED vira NULA.
--   C. função llm_papeis_so_modelo_governado() substituída (mesma segurança) +
--      trigger recriado (idempotente).
--   D. asserção: 0 rotas fora da regra de produção.
--
-- VERIFY:
--   -- 1) a tabela esperada
--   select papel, provider, modelo_primario, esforco, modelo_reserva
--     from public.llm_papeis order by papel;
--   -- esperado (25):
--   --   atendimento openai/gpt-6-sol high · atlas_parser anthropic/claude-opus-5-5 NULL
--   --   auxiliar openai/gpt-6-luna medium · brand_capture openai/gpt-6-luna medium
--   --   chat_principal openai/gpt-6-sol medium · chunking_agentico openai/gpt-6-luna medium
--   --   conselho_lider anthropic/claude-opus-5-5 NULL · dispatch anthropic/claude-opus-5-5 NULL
--   --   distiller openai/gpt-6-luna medium · distiller_forte anthropic/claude-opus-5-5 NULL
--   --   embedding openai/text-embedding-3-small NULL · extrator_planos openai/gpt-6-luna medium
--   --   garimpo openai/gpt-6-luna medium · hyde openai/gpt-6-luna medium
--   --   juiz_eval openai/gpt-6-sol medium · juiz_playbook anthropic/claude-opus-5-5 NULL
--   --   memoria openai/gpt-6-luna medium · portal_decisao openai/gpt-6-sol medium
--   --   prompt_optimizer anthropic/claude-opus-5-5 NULL · rerank cohere/rerank-multilingual-v3.0 NULL
--   --   subagente openai/gpt-6-sol medium · sugestoes anthropic/claude-opus-5-5 NULL
--   --   transcricao openai/gpt-transcribe NULL · visao openai/gpt-6-sol medium
--   --   visao_documento openai/gpt-6-sol medium          (todas as reservas NULAS)
--
--   -- 2) 0 rotas com modelo não-APPROVED (primário ou reserva)
--   select count(*) from public.llm_papeis r
--     left join public.llm_pricing p on p.model_name = r.modelo_primario
--     left join public.llm_pricing q on q.model_name = r.modelo_reserva
--    where p.lifecycle is distinct from 'APPROVED'
--       or (r.modelo_reserva is not null and q.lifecycle is distinct from 'APPROVED');
--   -- esperado: 0
--   select lifecycle, array_agg(model_name order by model_name) from public.llm_pricing
--    where lifecycle = 'APPROVED' group by 1;
--   -- esperado: claude-opus-5-5, gpt-6-luna, gpt-6-sol, gpt-transcribe,
--   --           rerank-multilingual-v3.0, text-embedding-3-small
--
--   -- 3) a RECUSA (cada `begin … exception` é um SAVEPOINT; nada fica gravado)
--   do $$
--   declare recusas int := 0; v_a int; v_m int; v_a2 int; v_m2 int;
--   begin
--     select versao into v_a from public.llm_papeis where papel = 'atendimento';
--     select versao into v_m from public.llm_papeis where papel = 'memoria';
--     begin  -- DEPRECATED em rota de produção
--       update public.llm_papeis set provider = 'anthropic', modelo_primario = 'claude-sonnet-5',
--              esforco = null where papel = 'atendimento';
--     exception when check_violation then recusas := recusas + 1; end;
--     begin  -- Luna abaixo do mínimo de produção
--       update public.llm_papeis set esforco = 'low' where papel = 'memoria';
--     exception when check_violation then recusas := recusas + 1; end;
--     begin  -- Luna sem esforço declarado (o mínimo exige declarar)
--       update public.llm_papeis set esforco = null where papel = 'memoria';
--     exception when check_violation then recusas := recusas + 1; end;
--     begin  -- CANDIDATE em rota de produção
--       update public.llm_papeis set provider = 'openai', modelo_primario = 'gpt-6-astra',
--              esforco = 'medium' where papel = 'atendimento';
--     exception when check_violation then recusas := recusas + 1; end;
--     begin  -- reserva DEPRECATED
--       update public.llm_papeis set provider_reserva = 'openai', modelo_reserva = 'gpt-4o-mini'
--        where papel = 'atendimento';
--     exception when check_violation then recusas := recusas + 1; end;
--     select versao into v_a2 from public.llm_papeis where papel = 'atendimento';
--     select versao into v_m2 from public.llm_papeis where papel = 'memoria';
--     if recusas <> 5 or v_a is distinct from v_a2 or v_m is distinct from v_m2 then
--       raise exception 'VERIFY 20260924_01 FALHOU: recusas=% (esperado 5)', recusas;
--     end if;
--     raise notice 'VERIFY 20260924_01 OK: 5 recusas, versões intocadas';
--   end $$;
--   -- CONTROLE (tem de PASSAR): begin; update public.llm_papeis set esforco='high'
--   --   where papel='memoria'; rollback;
--
--   -- 4) segurança (advisors não crescem)
--   select p.proname, p.prosecdef, p.proconfig,
--          has_function_privilege('anon', p.oid, 'execute') anon_exec,
--          has_function_privilege('authenticated', p.oid, 'execute') auth_exec
--     from pg_proc p where p.proname = 'llm_papeis_so_modelo_governado';
--   -- esperado: prosecdef=false · {search_path=pg_catalog, public} · false · false
--
-- ROLLBACK:  (escrito ANTES de aplicar; o trigger de histórico registra a volta)
--   -- 1) a trava volta a ser a de 20260923_05: re-executar o bloco
--   --    `create or replace function public.llm_papeis_so_modelo_governado() …`
--   --    daquele arquivo (lista usável APPROVED/CANDIDATE/DEPRECATED, sem mínimo).
--   -- 2) catálogo:
--   update public.llm_pricing set lifecycle = 'CANDIDATE', updated_at = now()
--    where model_name in ('gpt-6-sol','gpt-6-luna','gpt-transcribe');
--   update public.llm_pricing set lifecycle = 'APPROVED', updated_at = now()
--    where model_name in ('claude-sonnet-5','claude-opus-5','claude-haiku-4-5','claude-haiku-4-5-20251001');
--   update public.llm_pricing set capacidades = capacidades - 'esforco_minimo_producao'
--    where model_name = 'gpt-6-luna';
--   -- 3) rotas (📊 valores de 24/09/2026 antes desta migration):
--   update public.llm_papeis r set provider = v.p, modelo_primario = v.m, esforco = v.e,
--          motivo = 'rollback 20260924_01', atualizado_por = 'rollback'
--     from (values
--       ('atendimento','anthropic','claude-sonnet-5',null), ('atlas_parser','anthropic','claude-opus-5',null),
--       ('auxiliar','anthropic','claude-haiku-4-5-20251001',null), ('brand_capture','anthropic','claude-sonnet-5',null),
--       ('chat_principal','anthropic','claude-sonnet-5',null), ('chunking_agentico','openai','gpt-4o-mini',null),
--       ('conselho_lider','anthropic','claude-opus-5',null), ('dispatch','anthropic','claude-opus-5',null),
--       ('distiller','anthropic','claude-sonnet-5',null), ('distiller_forte','anthropic','claude-opus-5',null),
--       ('extrator_planos','anthropic','claude-sonnet-5',null), ('garimpo','anthropic','claude-sonnet-5',null),
--       ('hyde','openai','gpt-4o-mini',null), ('juiz_eval','anthropic','claude-sonnet-5',null),
--       ('juiz_playbook','anthropic','claude-opus-5',null), ('memoria','openai','gpt-6-luna','low'),
--       ('portal_decisao','openai','gpt-6-sol','medium'), ('prompt_optimizer','anthropic','claude-opus-5',null),
--       ('subagente','anthropic','claude-sonnet-5',null), ('sugestoes','anthropic','claude-opus-5',null),
--       ('transcricao','openai','whisper-1',null), ('visao','openai','gpt-6-sol','low'),
--       ('visao_documento','openai','gpt-4o-mini',null)
--     ) as v(papel, p, m, e)
--    where r.papel = v.papel;
--   -- (ordem do rollback: 1 → 2 → 3; com a trava velha as rotas legadas passam)
--
-- EXPAND-FIRST: sim para a estrutura (nenhuma coluna muda); a trava fica MAIS
--   estrita — a asserção D prova que o que fica gravado passa nela.
-- DESTRUTIVA:   não — o histórico (llm_papeis_historico) guarda cada linha anterior.
-- =============================================================

-- -------------------------------------------------------------
-- A. CATÁLOGO (antes das rotas)
-- -------------------------------------------------------------
update public.llm_pricing
   set lifecycle = 'APPROVED',
       notas = coalesce(notas || ' · ', '') || 'APPROVED: Founder 24/09/2026 — conclusão da Onda A da SPEC-116',
       updated_at = now()
 where model_name in ('gpt-6-sol', 'gpt-6-luna', 'gpt-transcribe')
   and lifecycle is distinct from 'APPROVED';

update public.llm_pricing
   set capacidades = coalesce(capacidades, '{}'::jsonb) || '{"esforco_minimo_producao": "medium"}'::jsonb,
       updated_at = now()
 where model_name = 'gpt-6-luna'
   and (capacidades ->> 'esforco_minimo_producao') is distinct from 'medium';

update public.llm_pricing
   set notas = coalesce(notas || ' · ', '') ||
               'EVIDENCIAS/04 l.54: US$0,0045/min, /audio/transcriptions, keyword hints + contexto livre; verbose_json NÃO documentado',
       updated_at = now()
 where model_name = 'gpt-transcribe'
   and coalesce(notas, '') not like '%EVIDENCIAS/04 l.54%';

update public.llm_pricing
   set lifecycle = 'DEPRECATED',
       substituido_por = case when model_name = 'claude-opus-5' then 'claude-opus-5-5' else substituido_por end,
       notas = coalesce(notas || ' · ', '') || 'DEPRECATED: Founder 24/09/2026 — conclusão da Onda A da SPEC-116',
       updated_at = now()
 where model_name in ('claude-sonnet-5', 'claude-opus-5', 'claude-haiku-4-5', 'claude-haiku-4-5-20251001')
   and lifecycle is distinct from 'DEPRECATED';

-- -------------------------------------------------------------
-- B. ROTAS
-- -------------------------------------------------------------
update public.llm_papeis r
   set provider = a.provider, modelo_primario = a.modelo, esforco = a.esforco,
       motivo = 'Founder 24/09/2026 — conclusão da Onda A da SPEC-116',
       atualizado_por = 'migration 20260924_01'
  from (values
    ('chat_principal',    'openai', 'gpt-6-sol',      'medium'),
    ('atendimento',       'openai', 'gpt-6-sol',      'high'),
    ('portal_decisao',    'openai', 'gpt-6-sol',      'medium'),
    ('visao',             'openai', 'gpt-6-sol',      'medium'),
    ('visao_documento',   'openai', 'gpt-6-sol',      'medium'),
    ('juiz_eval',         'openai', 'gpt-6-sol',      'medium'),
    ('subagente',         'openai', 'gpt-6-sol',      'medium'),
    ('memoria',           'openai', 'gpt-6-luna',     'medium'),
    ('hyde',              'openai', 'gpt-6-luna',     'medium'),
    ('chunking_agentico', 'openai', 'gpt-6-luna',     'medium'),
    ('distiller',         'openai', 'gpt-6-luna',     'medium'),
    ('extrator_planos',   'openai', 'gpt-6-luna',     'medium'),
    ('brand_capture',     'openai', 'gpt-6-luna',     'medium'),
    ('garimpo',           'openai', 'gpt-6-luna',     'medium'),
    ('auxiliar',          'openai', 'gpt-6-luna',     'medium'),
    ('transcricao',       'openai', 'gpt-transcribe', null)
  ) as a(papel, provider, modelo, esforco)
 where r.papel = a.papel
   and (r.provider, r.modelo_primario, r.esforco) is distinct from (a.provider, a.modelo, a.esforco);

-- TODO papel em claude-opus-5 (📊 24/09: atlas_parser, conselho_lider, dispatch,
-- distiller_forte, juiz_playbook, prompt_optimizer, sugestoes — e qualquer outro
-- que exista quando aplicar) → claude-opus-5-5, preservando o esforço se o 5.5 o aceita.
update public.llm_papeis r
   set provider = 'anthropic', modelo_primario = 'claude-opus-5-5',
       esforco = case
         when r.esforco is not null
          and jsonb_typeof(p.capacidades -> 'niveis_de_esforco') = 'array'
          and (p.capacidades -> 'niveis_de_esforco') ? r.esforco then r.esforco
         else null end,
       motivo = 'Founder 24/09/2026 — conclusão da Onda A da SPEC-116',
       atualizado_por = 'migration 20260924_01'
  from public.llm_pricing p
 where p.model_name = 'claude-opus-5-5'
   and r.modelo_primario = 'claude-opus-5';

-- reserva que não é APPROVED não fica (📊 24/09: todas NULAS — no-op esperado)
update public.llm_papeis r
   set provider_reserva = null, modelo_reserva = null, esforco_reserva = null,
       motivo = 'Founder 24/09/2026 — conclusão da Onda A da SPEC-116 (reserva não APPROVED removida)',
       atualizado_por = 'migration 20260924_01'
  from public.llm_pricing q
 where q.model_name = r.modelo_reserva
   and q.lifecycle is distinct from 'APPROVED';

-- -------------------------------------------------------------
-- C. A TRAVA: rota de PRODUÇÃO só aceita APPROVED e esforço ≥ mínimo
--    (a MESMA regra de model_policy._validar(producao=True))
-- -------------------------------------------------------------
create or replace function public.llm_papeis_so_modelo_governado()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, public
as $fn$
declare
  v_producao constant text[] := array['APPROVED'];
  v_escala   constant text[] := array['none','low','medium','high','xhigh','max'];
  v_modelo  text;
  v_prov    text;
  v_esforco text;
  v_minimo  text;
  v_tipo    text;
  v_linha   record;
begin
  foreach v_tipo in array array['primario','reserva'] loop
    if v_tipo = 'primario' then
      v_modelo := new.modelo_primario; v_prov := new.provider; v_esforco := new.esforco;
    else
      v_modelo := new.modelo_reserva; v_prov := new.provider_reserva; v_esforco := new.esforco_reserva;
    end if;
    continue when v_modelo is null;

    select p.provider, p.lifecycle, p.classes_de_dado, p.capacidades
      into v_linha
      from public.llm_pricing p
     where p.model_name = v_modelo;

    if not found then
      raise exception 'llm_papeis[%]: modelo % (%) fora do catálogo', new.papel, v_modelo, v_tipo
        using errcode = 'check_violation';
    end if;
    if v_prov is distinct from v_linha.provider then
      raise exception 'llm_papeis[%]: provider % diverge do catálogo (%) para % (%)',
        new.papel, v_prov, v_linha.provider, v_modelo, v_tipo
        using errcode = 'check_violation';
    end if;
    if v_linha.lifecycle is null or not (v_linha.lifecycle = any(v_producao)) then
      raise exception 'llm_papeis[%]: % tem lifecycle % — rota de produção só aceita APPROVED (%)',
        new.papel, v_modelo, coalesce(v_linha.lifecycle, 'NULO'), v_tipo
        using errcode = 'check_violation';
    end if;
    if not (new.classe_de_dado = any(coalesce(v_linha.classes_de_dado, '{}'::text[]))) then
      raise exception 'llm_papeis[%]: % não pode ver dado % (permite %) (%)',
        new.papel, v_modelo, new.classe_de_dado, coalesce(v_linha.classes_de_dado, '{}'::text[]), v_tipo
        using errcode = 'check_violation';
    end if;
    if v_esforco is not null
       and jsonb_typeof(v_linha.capacidades -> 'niveis_de_esforco') = 'array'
       and not ((v_linha.capacidades -> 'niveis_de_esforco') ? v_esforco) then
      raise exception 'llm_papeis[%]: % não aceita esforço % (%)', new.papel, v_modelo, v_esforco, v_tipo
        using errcode = 'check_violation';
    end if;
    v_minimo := v_linha.capacidades ->> 'esforco_minimo_producao';
    if v_minimo is not null then
      if array_position(v_escala, v_minimo) is null then
        raise exception 'llm_papeis[%]: % declara esforco_minimo_producao inválido % (%)',
          new.papel, v_modelo, v_minimo, v_tipo
          using errcode = 'check_violation';
      end if;
      if v_esforco is null
         or array_position(v_escala, v_esforco) < array_position(v_escala, v_minimo) then
        raise exception 'llm_papeis[%]: % exige esforço ≥ % em produção (recebeu %) (%)',
          new.papel, v_modelo, v_minimo, coalesce(v_esforco, 'NULO'), v_tipo
          using errcode = 'check_violation';
      end if;
    end if;
  end loop;
  return new;
end;
$fn$;

revoke all on function public.llm_papeis_so_modelo_governado() from public;
revoke all on function public.llm_papeis_so_modelo_governado() from anon, authenticated;

comment on function public.llm_papeis_so_modelo_governado() is
  'SPEC-116 (conclusão da Onda A, 24/09/2026): rota de PRODUÇÃO só aceita modelo do catálogo, do mesmo provider, lifecycle APPROVED (primário e reserva), classe de dado permitida, esforço nos níveis do modelo e ≥ capacidades.esforco_minimo_producao quando declarado — a mesma regra de model_policy._validar(producao=True). A bancada não passa por aqui (override em memória).';

drop trigger if exists trg_llm_papeis_governado on public.llm_papeis;
create trigger trg_llm_papeis_governado
  before insert or update on public.llm_papeis
  for each row execute function public.llm_papeis_so_modelo_governado();

-- -------------------------------------------------------------
-- D. ASSERÇÃO: nada gravado fica fora da regra nova (aborta tudo se ficar)
-- -------------------------------------------------------------
do $$
declare v_ruins text;
begin
  select string_agg(r.papel || '→' || coalesce(r.modelo_primario, '∅') || '/' ||
                    coalesce(p.lifecycle, 'NULO') || '/' || coalesce(r.esforco, 'NULO'), ', ')
    into v_ruins
    from public.llm_papeis r
    left join public.llm_pricing p on p.model_name = r.modelo_primario
    left join public.llm_pricing q on q.model_name = r.modelo_reserva
   where p.lifecycle is distinct from 'APPROVED'
      or (r.modelo_reserva is not null and q.lifecycle is distinct from 'APPROVED')
      or ((p.capacidades ->> 'esforco_minimo_producao') is not null and (
            r.esforco is null
            or array_position(array['none','low','medium','high','xhigh','max'], r.esforco)
             < array_position(array['none','low','medium','high','xhigh','max'], p.capacidades ->> 'esforco_minimo_producao')));
  if v_ruins is not null then
    raise exception '20260924_01: rotas fora da regra de produção: %', v_ruins;
  end if;
end $$;
