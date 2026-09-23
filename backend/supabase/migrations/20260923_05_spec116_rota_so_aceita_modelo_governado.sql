-- =============================================================
-- MIGRATION: 20260923_05_spec116_rota_so_aceita_modelo_governado
-- SPEC:      SPEC-116 — conserto único (red team P3)
-- AUTOR:     builder do conserto (Opus xhigh)      DATA: 2026-09-23
-- OBJETIVO:  o BANCO recusa uma rota (llm_papeis) que o resolvedor recusaria.
--            📊 red team 23/09: `update llm_papeis set modelo_primario=
--            'claude-3-5-sonnet-20241022' where papel='atendimento'` PASSAVA no
--            banco (só há FK para llm_pricing); em ≤ 60 s o resolvedor recusa a
--            rota e TODA corretora recebe a "falha honesta" até alguém voltar a
--            linha. A regra aqui é a MESMA de `model_policy._validar`:
--              · o modelo (primário e reserva) está no catálogo;
--              · o provider da rota = o provider do catálogo;
--              · lifecycle ∈ (APPROVED, CANDIDATE, DEPRECATED) — BLOCKED,
--                HISTORICAL ou NULO são recusados (a lista USÁVEL, como no Python);
--              · a classe_de_dado da rota ∈ classes_de_dado do modelo (LGPD);
--              · o esforço, quando dado, está nos niveis_de_esforco do modelo
--                (se o catálogo os declara).
--
-- APPLY:     1 função `llm_papeis_so_modelo_governado()` (SECURITY INVOKER,
--            search_path fixo, sem EXECUTE para public/anon/authenticated) +
--            1 trigger BEFORE INSERT OR UPDATE em llm_papeis. Nenhum dado muda.
--            ⚠️ O nome do trigger ordena ANTES de `trg_llm_papeis_historico`
--            (g < h): a recusa acontece antes de versionar; e o RAISE aborta o
--            comando inteiro de qualquer forma (o histórico não fica).
--
-- VERIFY:    (read-only fora do SAVEPOINT; o bloco 3 tenta o UPDATE proibido e
--            desfaz — prova a recusa sem mudar nada)
--   -- 1) as 25 rotas ATUAIS passam na regra (simulação por SELECT)
--   select count(*) total,
--          count(*) filter (where p.model_name is null or p.provider is distinct from r.provider
--            or coalesce(p.lifecycle,'') not in ('APPROVED','CANDIDATE','DEPRECATED')
--            or not (r.classe_de_dado = any(coalesce(p.classes_de_dado,'{}'::text[])))
--            or (r.esforco is not null and p.capacidades ? 'niveis_de_esforco'
--                and not (p.capacidades->'niveis_de_esforco') ? r.esforco)) primario_recusado,
--          count(*) filter (where r.modelo_reserva is not null and (q.model_name is null
--            or q.provider is distinct from r.provider_reserva
--            or coalesce(q.lifecycle,'') not in ('APPROVED','CANDIDATE','DEPRECATED')
--            or not (r.classe_de_dado = any(coalesce(q.classes_de_dado,'{}'::text[]))))) reserva_recusada
--     from public.llm_papeis r
--     left join public.llm_pricing p on p.model_name = r.modelo_primario
--     left join public.llm_pricing q on q.model_name = r.modelo_reserva;
--   -- esperado (📊 23/09 antes de aplicar): 25 · 0 · 0
--
--   -- 2) segurança (advisors não crescem)
--   select p.proname, p.prosecdef, p.proconfig,
--          has_function_privilege('anon', p.oid, 'execute') anon_exec,
--          has_function_privilege('authenticated', p.oid, 'execute') auth_exec
--     from pg_proc p where p.proname = 'llm_papeis_so_modelo_governado';
--   -- esperado: prosecdef=false · proconfig={search_path=pg_catalog, public} · false · false
--   select tgname, tgenabled from pg_trigger
--    where tgrelid = 'public.llm_papeis'::regclass and not tgisinternal order by 1;
--   -- esperado: trg_llm_papeis_governado O · trg_llm_papeis_historico O
--
--   -- 3) a RECUSA, provada dentro de um SAVEPOINT (nada fica gravado)
--   do $$
--   declare recusas int := 0; v_antes int; v_depois int;
--   begin
--     select versao into v_antes from public.llm_papeis where papel = 'atendimento';
--     begin  -- modelo HISTORICAL
--       update public.llm_papeis set provider = 'anthropic',
--              modelo_primario = 'claude-3-5-sonnet-20241022' where papel = 'atendimento';
--     exception when check_violation then recusas := recusas + 1; end;
--     begin  -- provider divergente do catálogo
--       update public.llm_papeis set provider = 'anthropic', modelo_primario = 'gpt-4o'
--        where papel = 'atendimento';
--     exception when check_violation then recusas := recusas + 1; end;
--     begin  -- classe proibida: rota pii → modelo cujo catálogo não permite pii
--       update public.llm_papeis set provider = p.provider, modelo_primario = p.model_name
--         from (select model_name, provider from public.llm_pricing
--                where lifecycle in ('APPROVED','CANDIDATE','DEPRECATED')
--                  and not ('pii' = any(coalesce(classes_de_dado,'{}'::text[])))
--                limit 1) p
--        where papel = 'atendimento';
--       if not found then recusas := recusas + 1; end if;  -- catálogo sem modelo assim: nada a provar
--     exception when check_violation then recusas := recusas + 1; end;
--     begin  -- reserva BLOCKED/HISTORICAL
--       update public.llm_papeis set provider_reserva = 'openai', modelo_reserva = 'gpt-5.1'
--        where papel = 'atendimento';
--     exception when check_violation then recusas := recusas + 1; end;
--     select versao into v_depois from public.llm_papeis where papel = 'atendimento';
--     if recusas <> 4 or v_antes is distinct from v_depois then
--       raise exception 'VERIFY _05 FALHOU: recusas=% (esperado 4) versao % -> %',
--         recusas, v_antes, v_depois;
--     end if;
--     raise notice 'VERIFY _05 OK: 4 recusas, versao intocada (%)', v_depois;
--   end $$;
--   -- (cada `begin … exception` é um SAVEPOINT implícito do PL/pgSQL)
--
--   -- 4) CONTROLE: um UPDATE legítimo (mesma rota, só o motivo) continua passando
--   --    begin; update public.llm_papeis set motivo = motivo where papel='atendimento'; rollback;
--
-- ROLLBACK:  (escrito ANTES de aplicar — só remove a trava; nenhum dado muda)
--   drop trigger if exists trg_llm_papeis_governado on public.llm_papeis;
--   drop function if exists public.llm_papeis_so_modelo_governado();
--
-- EXPAND-FIRST: sim (só acrescenta uma trava; o que já está gravado passa — VERIFY 1)
-- DESTRUTIVA:   não
-- ⚠️ FORA DO ESCOPO (registrado): um UPDATE em llm_PRICING (ex.: marcar BLOCKED um
--   modelo que uma rota usa) não é barrado por esta trava — o resolvedor recusa, como hoje.
-- =============================================================

create or replace function public.llm_papeis_so_modelo_governado()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, public
as $fn$
declare
  v_usaveis constant text[] := array['APPROVED','CANDIDATE','DEPRECATED'];
  v_modelo  text;
  v_prov    text;
  v_esforco text;
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
    if v_linha.lifecycle is null or not (v_linha.lifecycle = any(v_usaveis)) then
      raise exception 'llm_papeis[%]: % tem lifecycle % (recusado) (%)',
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
  end loop;
  return new;
end;
$fn$;

revoke all on function public.llm_papeis_so_modelo_governado() from public;
revoke all on function public.llm_papeis_so_modelo_governado() from anon, authenticated;

comment on function public.llm_papeis_so_modelo_governado() is
  'SPEC-116 (conserto, red team P3): recusa rota para modelo fora do catálogo, provider divergente, lifecycle fora de APPROVED/CANDIDATE/DEPRECATED, classe de dado não permitida ou esforço não aceito — a mesma regra de model_policy._validar.';

drop trigger if exists trg_llm_papeis_governado on public.llm_papeis;
create trigger trg_llm_papeis_governado
  before insert or update on public.llm_papeis
  for each row execute function public.llm_papeis_so_modelo_governado();
