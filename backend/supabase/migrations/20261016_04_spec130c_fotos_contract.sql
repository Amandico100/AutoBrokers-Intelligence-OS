-- =============================================================
-- MIGRATION: 20261016_04_spec130c_fotos_contract
-- SPEC:      SPEC-130-C — F1 · a marca (o CONTRACT da _03)
-- AUTOR:     gerente (Opus 5.5), a partir do arquivo do builder F1      DATA: 2026-10-16
-- OBJETIVO:  tirar o índice antigo que deixa UMA foto atual por corretora (o substituto, que exclui 'photo', já está no banco).
--
-- 🧑 QUEM APLICA: o Founder, no SQL Editor do Supabase — o apply_migration recusou o passo destrutivo (16/10).
-- 📊 ANTES (16/10, depois da _03 aplicada como versão 20261017004656): indice_novo 1 · indice_antigo 1 · fotos 0.
--
-- APPLY:  drop index brand_assets_one_current_per_kind (o substituto brand_assets_one_current_per_kind_exceto_foto garante
--         o mesmo para todo papel que não é foto) · COMMENT de storage_ref · o VERIFY comportamental (o DO no fim).
-- VERIFY: select (select count(*) from pg_indexes where tablename='brand_assets'
--                 and indexname='brand_assets_one_current_per_kind') as antigo,                -- 0
--                (select count(*) from pg_indexes where tablename='brand_assets'
--                 and indexname='brand_assets_one_current_per_kind_exceto_foto') as novo;     -- 1
--         + o aviso "VERIFY 20261016_03 OK: duas_fotos_entram;dois_atuais_do_mesmo_papel_recusados;..." do bloco abaixo.
-- ROLLBACK (guarda: nenhuma corretora com 2+ fotos atuais — o ROLLBACK da _03 tem o UPDATE que rebaixa as extras):
--   create unique index if not exists brand_assets_one_current_per_kind on public.brand_assets (company_id, kind) where is_current;
--   comment on column public.brand_assets.storage_ref is null;
-- EXPAND-FIRST: sim (o substituto já existe)   DESTRUTIVA: não (índice substituído; 0 linhas de foto)
-- =============================================================

set lock_timeout = '5s';

-- o substituto TEM de existir antes (a _03); sem ele, para aqui
do $$ begin
  if not exists (select 1 from pg_indexes where tablename = 'brand_assets'
                  and indexname = 'brand_assets_one_current_per_kind_exceto_foto') then
    raise exception '20261016_04 recusada: aplique a 20261016_03 primeiro (o índice substituto não existe)';
  end if;
end $$;

drop index if exists public.brand_assets_one_current_per_kind;

comment on column public.brand_assets.storage_ref is
  'O arquivo em si: data: URL (data:image/...;base64, — o logo enviado e as fotos, SPEC-133-A/130-C) ou URL https de onde a '
  'captura leu o logo. Nao e bucket/path: nenhum leitor resolve caminho de Storage aqui.';

-- 6. VERIFY comportamental — prova o OBJETO e não deixa nada para trás ----------------------------------------------------
do $$
declare
  v_company uuid;
  v_ok text := '';
begin
  select id into v_company from public.companies limit 1;
  if v_company is null then
    raise notice 'VERIFY 20261016_03: sem companies, comportamental pulado';
    return;
  end if;
  begin
    insert into public.brand_assets (company_id, kind, storage_ref, is_current, sort_order, source_kind)
      values (v_company, 'photo', 'data:image/webp;base64,VERIFY', true, 0, 'upload'),
             (v_company, 'photo', 'data:image/webp;base64,VERIFY', true, 1, 'upload');
    v_ok := v_ok || 'duas_fotos_entram;';
    begin
      insert into public.brand_assets (company_id, kind, storage_ref, is_current, source_kind)
        values (v_company, 'pattern', 'data:image/webp;base64,VERIFY', true, 'upload'),
               (v_company, 'pattern', 'data:image/webp;base64,VERIFY', true, 'upload');
      raise exception 'VERIFY 20261016_03 FALHOU: dois pattern atuais entraram';
    exception when unique_violation then v_ok := v_ok || 'dois_atuais_do_mesmo_papel_recusados;';
    end;
    begin
      insert into public.brand_assets (company_id, kind, storage_ref, is_current, sort_order, caption, source_kind)
        values (v_company, 'photo', 'data:image/webp;base64,VERIFY', true, 2, repeat('x', 81), 'upload');
      raise exception 'VERIFY 20261016_03 FALHOU: legenda de 81 entrou';
    exception when check_violation then v_ok := v_ok || 'legenda_81_recusada;';
    end;
    begin
      insert into public.brand_assets (company_id, kind, storage_ref, is_current, sort_order, source_kind)
        values (v_company, 'symbol', 'data:image/webp;base64,VERIFY', false, 3, 'upload');
      raise exception 'VERIFY 20261016_03 FALHOU: ordem em papel que nao e foto entrou';
    exception when check_violation then v_ok := v_ok || 'ordem_fora_de_foto_recusada;';
    end;
    begin
      update public.brand_profiles set awards = '{}'::jsonb where company_id = v_company;
      if found then
        raise exception 'VERIFY 20261016_03 FALHOU: awards objeto entrou';
      end if;
      v_ok := v_ok || 'awards_sem_perfil;';
    exception when check_violation then v_ok := v_ok || 'awards_objeto_recusado;';
    end;
    raise exception 'VERIFY_DESFAZ %', v_ok;   -- desfaz TUDO o que este bloco escreveu
  exception when raise_exception then
    if sqlerrm like 'VERIFY_DESFAZ%' then
      raise notice 'VERIFY 20261016_03 OK: %', substr(sqlerrm, 15);
    else
      raise;
    end if;
  end;
end $$;
