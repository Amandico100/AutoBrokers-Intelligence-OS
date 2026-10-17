-- =============================================================
-- MIGRATION: 20261016_03_spec130c_fotos_e_premios
-- SPEC:      SPEC-130-C — F1 · a marca (U3: fotos + prêmios)
-- AUTOR:     builder F1 (Opus 5.5)          DATA: 2026-10-16
-- OBJETIVO:  a corretora guarda até 8 FOTOS (ordem + legenda) em brand_assets e os PRÊMIOS em brand_profiles.awards.
--
-- 📊 ANTES (16/10/2026, read-only no projeto dcajcvlzcjbmyapmklil, pelo builder F1):
--    select count(*) from brand_assets where kind='photo'                       → 0   (nenhuma linha afetada pela troca do índice)
--    select count(*) from brand_assets                                          → 2   (2 logo_primary atuais, um por corretora)
--    pg_indexes brand_assets: brand_assets_one_current_per_kind = UNIQUE (company_id, kind) WHERE is_current
--    pg_policies brand_assets/brand_profiles                                    → 0 policies; relrowsecurity = true nas duas
--    col_description(brand_assets.storage_ref)                                  → NULL (o "bucket/path" era só comentário SQL
--                                                                                  da 20260725_05 :43, nunca um COMMENT ON)
--    information_schema.columns sort_order/caption/awards                       → nenhuma existe
--
-- APPLY:
--   1. brand_assets.sort_order smallint NULL (só foto tem ordem) + brand_assets.caption text NULL (≤ 80 caracteres).
--   2. CHECKs: caption ≤ 80 · sort_order ≥ 0 · sort_order só em kind='photo'.
--   3. índice ÚNICO novo brand_assets_one_current_per_kind_exceto_foto (company_id, kind) WHERE is_current AND kind <> 'photo'
--      é CRIADO (expand). O índice ANTIGO brand_assets_one_current_per_kind CONTINUA — o DROP dele mora na
--      20261016_04_spec130c_fotos_contract.sql (passo do Founder). Enquanto a _04 não roda, a 2ª foto atual da mesma
--      corretora bate no índice antigo (23505) e a tela mostra a frase do suporte (fotos.py FRASE_FALTA_A_MIGRATION).
--      Logo, símbolo, favicon etc. continuam com UM atual por papel; depois da _04, foto aceita várias (teto 8 em fotos.py).
--   4. brand_profiles.awards jsonb NOT NULL DEFAULT '[]' + CHECK array + CHECK ≤ 10 itens.
--   5. COMMENT ON COLUMN brand_assets.sort_order / caption e brand_profiles.awards (o que a coluna GUARDA de fato).
--      O COMMENT de brand_assets.storage_ref foi para a _04.
--   📊 APLICADO: versão 20261017004656, nome no banco `20261016_03a_spec130c_fotos_e_premios_expand` (SELECT de 17/10 do
--      juiz: indice_novo 1 · indice_antigo 1 · cols_assets 2 · checks_assets 3 · col_awards 1 · checks_awards 2 ·
--      policies 0). Este cabeçalho foi corrigido no conserto KB (juiz P2) para dizer o que FOI aplicado; nenhuma linha
--      executável deste arquivo mudou.
--   RLS: NADA muda. As duas tabelas seguem com RLS ligada e ZERO policy (fail-closed; só service_role passa); o filtro
--   company_id mora no código (fotos.py / brand.py). Nenhum GRANT é tocado.
--
-- VERIFY (read-only; esperado ANTES = 0 · 1 · 0 · 0 · 0 · 0 · 0 · erro de coluna; DEPOIS desta _03 = 1 · 1 · 2 · 3 · 1 · 2 ·
--   0 · 0 — o índice antigo AINDA existe (1) até a _04; depois da _04, indice_antigo = 0, conferido pelo VERIFY da _04):
--   select
--    (select count(*) from pg_indexes where tablename='brand_assets'
--       and indexname='brand_assets_one_current_per_kind_exceto_foto'
--       and indexdef ilike '%UNIQUE%' and indexdef ilike '%<> ''photo''%')                          as indice_novo,      -- 1
--    (select count(*) from pg_indexes where tablename='brand_assets'
--       and indexname='brand_assets_one_current_per_kind')                                          as indice_antigo,    -- 1 (0 só depois da _04)
--    (select count(*) from information_schema.columns where table_schema='public' and table_name='brand_assets'
--       and column_name in ('sort_order','caption'))                                                as cols_assets,      -- 2
--    (select count(*) from pg_constraint where conrelid='public.brand_assets'::regclass and contype='c'
--       and conname in ('brand_assets_caption_len_ck','brand_assets_sort_order_ck','brand_assets_sort_order_so_foto_ck')) as checks_assets, -- 3
--    (select count(*) from information_schema.columns where table_schema='public' and table_name='brand_profiles'
--       and column_name='awards' and is_nullable='NO')                                              as col_awards,       -- 1
--    (select count(*) from pg_constraint where conrelid='public.brand_profiles'::regclass and contype='c'
--       and conname in ('brand_profiles_awards_array_ck','brand_profiles_awards_teto_ck'))          as checks_awards,    -- 2
--    (select count(*) from pg_policies where tablename in ('brand_assets','brand_profiles'))        as policies,         -- 0
--    (select count(*) from brand_profiles where jsonb_typeof(awards) <> 'array')                    as awards_fora;      -- 0
--   O VERIFY COMPORTAMENTAL (duas fotos atuais na mesma corretora ENTRAM, dois logo_primary atuais são RECUSADOS) precisa
--   do índice antigo FORA — por isso mora na 20261016_04 (não há DO de verificação neste arquivo).
--
-- ROLLBACK (escrito ANTES do APPLY; rodar numa transação):
--   -- guarda: o índice antigo não sobe se alguma corretora tiver 2+ fotos atuais. Rebaixe as extras ANTES:
--   --   update brand_assets b set is_current=false where kind='photo' and is_current and exists (
--   --     select 1 from brand_assets o where o.company_id=b.company_id and o.kind='photo' and o.is_current
--   --       and (coalesce(o.sort_order,32767), o.created_at, o.id) < (coalesce(b.sort_order,32767), b.created_at, b.id));
--   do $$ begin
--     if exists (select 1 from public.brand_assets where kind='photo' and is_current
--                group by company_id having count(*) > 1) then
--       raise exception 'ROLLBACK 20261016_03 recusado: há corretora com 2+ fotos atuais; rebaixe as extras primeiro';
--     end if;
--   end $$;
--   create unique index if not exists brand_assets_one_current_per_kind on public.brand_assets (company_id, kind) where is_current;
--   drop index if exists public.brand_assets_one_current_per_kind_exceto_foto;
--   alter table public.brand_assets drop constraint if exists brand_assets_sort_order_so_foto_ck;
--   alter table public.brand_assets drop constraint if exists brand_assets_sort_order_ck;
--   alter table public.brand_assets drop constraint if exists brand_assets_caption_len_ck;
--   alter table public.brand_profiles drop constraint if exists brand_profiles_awards_teto_ck;
--   alter table public.brand_profiles drop constraint if exists brand_profiles_awards_array_ck;
--   -- ⚠️ as 3 linhas abaixo APAGAM legenda, ordem e prêmios cadastrados. Rode só se a coluna estiver vazia ou com o Founder:
--   --   select count(*) from brand_assets where caption is not null or sort_order is not null;   -- 0 para seguir
--   --   select count(*) from brand_profiles where awards <> '[]'::jsonb;                         -- 0 para seguir
--   alter table public.brand_assets drop column if exists caption;
--   alter table public.brand_assets drop column if exists sort_order;
--   alter table public.brand_profiles drop column if exists awards;
--   comment on column public.brand_assets.storage_ref is null;
--   -- Preferível ao rollback, se o problema for só a tela: deixar as colunas (expand) e não usar.
--
-- EXPAND-FIRST: sim (colunas, CHECKs e o índice novo; nada é removido aqui e nenhum dado é reescrito)
-- DESTRUTIVA:   não (nada sai nesta _03; o DROP do índice antigo — o passo destrutivo — é a 20261016_04, do Founder)
-- =============================================================

set lock_timeout = '5s';

-- 1. as colunas da foto ---------------------------------------------------------------------------------------------------
alter table public.brand_assets add column if not exists sort_order smallint;
alter table public.brand_assets add column if not exists caption    text;

-- 2. os CHECKs (idempotentes pelo nome) -----------------------------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_constraint where conrelid = 'public.brand_assets'::regclass
                  and conname = 'brand_assets_caption_len_ck') then
    alter table public.brand_assets
      add constraint brand_assets_caption_len_ck check (caption is null or char_length(caption) <= 80);
  end if;
  if not exists (select 1 from pg_constraint where conrelid = 'public.brand_assets'::regclass
                  and conname = 'brand_assets_sort_order_ck') then
    alter table public.brand_assets
      add constraint brand_assets_sort_order_ck check (sort_order is null or sort_order >= 0);
  end if;
  -- ordem é coisa de foto: um logo com sort_order seria um dado que nenhum leitor entende.
  if not exists (select 1 from pg_constraint where conrelid = 'public.brand_assets'::regclass
                  and conname = 'brand_assets_sort_order_so_foto_ck') then
    alter table public.brand_assets
      add constraint brand_assets_sort_order_so_foto_ck check (sort_order is null or kind = 'photo');
  end if;
end $$;

-- 3. o índice: um atual por papel, EXCETO foto ----------------------------------------------------------------------------
-- expand-first: o novo nasce antes; só depois o antigo sai. Tabela de 📊 2 linhas: sem CONCURRENTLY (não roda em transação).
create unique index if not exists brand_assets_one_current_per_kind_exceto_foto
  on public.brand_assets (company_id, kind)
  where is_current and kind <> 'photo';
-- 🔴 o DROP do índice antigo MUDOU-SE para 20261016_04 (o gerente, 16/10): o `apply_migration` recusou o arquivo inteiro
-- (passo destrutivo exige confirmação humana); esta parte EXPAND foi aplicada como versão 📊 20261017004656
-- (nome no banco `20261016_03a_spec130c_fotos_e_premios_expand`). O COMMENT de storage_ref e o VERIFY comportamental
-- (que precisa do índice antigo FORA) também foram para a _04.

-- 4. os prêmios -----------------------------------------------------------------------------------------------------------
alter table public.brand_profiles add column if not exists awards jsonb not null default '[]'::jsonb;
do $$
begin
  if not exists (select 1 from pg_constraint where conrelid = 'public.brand_profiles'::regclass
                  and conname = 'brand_profiles_awards_array_ck') then
    alter table public.brand_profiles
      add constraint brand_profiles_awards_array_ck check (jsonb_typeof(awards) = 'array');
  end if;
  if not exists (select 1 from pg_constraint where conrelid = 'public.brand_profiles'::regclass
                  and conname = 'brand_profiles_awards_teto_ck') then
    alter table public.brand_profiles
      add constraint brand_profiles_awards_teto_ck
      check (jsonb_typeof(awards) <> 'array' or jsonb_array_length(awards) <= 10);
  end if;
end $$;

-- 5. o que cada coluna GUARDA ---------------------------------------------------------------------------------------------
comment on column public.brand_assets.sort_order is
  'SPEC-130-C: ordem da FOTO na corretora (0 = primeira; as 4 primeiras vao as paginas). NULL para todo papel que nao e foto.';
comment on column public.brand_assets.caption is
  'SPEC-130-C: legenda da FOTO (ate 80 caracteres), escrita pela corretora. Vai a pagina do cliente.';
comment on column public.brand_profiles.awards is
  'SPEC-130-C: premios cadastrados pela corretora, [{nome, ano?}] (ate 10). "Corretora premiada" so com >= 1 (CDC art. 37). '
  'Escritor unico: app/services/brand/fotos.py salvar_premios.';

