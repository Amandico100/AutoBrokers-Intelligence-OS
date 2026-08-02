-- =============================================================
-- MIGRATION: spec064_catalogo_auxiliares
-- SPEC:      SPEC-064 — Bloco D (o catálogo) + Bloco A (a ontologia)
-- AUTOR:     lider tecnico            DATA: 2026-08-02
-- OBJETIVO:  dar ao catálogo global os campos que o corretor lê antes de
--            ligar um Auxiliar, e travar "Rotina sem Auxiliar dono".
--
-- APPLY:     1. colunas de catálogo em auxiliary_templates
--            2. CHECK de estado e de categoria (vocabulário fechado)
--            3. índice para a listagem do catálogo
--            (o seed dos 15 auxiliares vai na migration 02;
--             a ligação Rotina→Auxiliar vai na 03)
--
-- VERIFY:    select column_name from information_schema.columns
--             where table_name='auxiliary_templates'
--               and column_name in ('headline','categories','catalog_state',
--                                   'data_sources','what_it_does',
--                                   'value_promise','missing_for_launch');
--            -- esperado: 7 linhas
--
--            select conname from pg_constraint
--             where conrelid='public.auxiliary_templates'::regclass
--               and conname like 'auxiliary_templates_%_chk';
--            -- esperado: catalog_state_chk e categories_chk
--
-- ROLLBACK:  alter table public.auxiliary_templates
--              drop constraint if exists auxiliary_templates_catalog_state_chk,
--              drop constraint if exists auxiliary_templates_categories_chk,
--              drop column if exists headline,
--              drop column if exists categories,
--              drop column if exists catalog_state,
--              drop column if exists data_sources,
--              drop column if exists what_it_does,
--              drop column if exists value_promise,
--              drop column if exists missing_for_launch;
--            drop index if exists public.auxiliary_templates_catalogo_idx;
--
-- EXPAND-FIRST: sim — só adiciona. Nada é removido nem renomeado.
-- DESTRUTIVA:   não
-- =============================================================

-- -------------------------------------------------------------
-- 1. Os campos que o corretor lê antes de decidir
-- -------------------------------------------------------------
-- A auditoria da SPEC-064 mediu o estado: o catálogo tinha `name`,
-- `short_description` e `description` — texto de engenheiro. Nada dizia o que o
-- corretor GANHA, nem de onde o auxiliar tira a informação, nem o que falta
-- para os que ainda não existem.
--
-- Sem esses campos a página do Bloco C não tem o que renderizar, e o auxiliar
-- novo continua nascendo com uma página escrita à mão do lado — que é como a
-- galeria acabou com `follow-up-whatsapp/` e `resumo-atendimentos/` fixos ao
-- lado da rota dinâmica `[slug]`.

alter table public.auxiliary_templates
  -- A frase que vende o RESULTADO, não a função.
  --   ✗ "Varre portais e envia boletos"
  --   ✓ "O boleto chega ao cliente antes de a apólice cancelar"
  add column if not exists headline text,

  -- Categorias pelo que o corretor ganha. É array porque Cobrança é
  -- "Tempo livre" E "Dinheiro que volta" ao mesmo tempo — e continua sendo
  -- UM auxiliar, que roda UMA vez. Categoria é etiqueta, não pasta
  -- (ONTOLOGIA-DO-TRABALHO.md, corolário 3).
  add column if not exists categories text[] not null default '{}'::text[],

  -- 'available'   → o corretor pode ligar agora
  -- 'coming_soon' → aparece com a descrição pronta e o botão desabilitado
  --
  -- Por que os "em breve" existem no catálogo: para que qualquer LLM futura
  -- saiba ONDE a próxima coisa mora antes de construí-la.
  add column if not exists catalog_state text not null default 'available',

  -- Transparência: o corretor precisa saber o que o auxiliar acessa.
  -- Ex.: {infocap, portal_seguradora, conversas, susep}
  add column if not exists data_sources text[] not null default '{}'::text[],

  -- [{"tarefa": "...", "frequencia": "..."}] — a lista do que ele faz.
  add column if not exists what_it_does jsonb not null default '[]'::jsonb,

  -- O que o corretor ganha, EM NÚMERO. Quando ainda não há número medido,
  -- diz o que SERÁ medido — nunca inventa (CLAUDE.md §12.1).
  add column if not exists value_promise text,

  -- Só para 'coming_soon': o que falta para existir. Torna o catálogo um mapa
  -- de roadmap legível, em vez de uma promessa vaga.
  add column if not exists missing_for_launch text;

-- -------------------------------------------------------------
-- 2. Vocabulário fechado — senão a categoria vira campo livre
-- -------------------------------------------------------------
-- Sem CHECK, em três meses existem "Dinheiro que volta", "dinheiro-que-volta"
-- e "Financeiro" como três categorias diferentes, e o filtro da tela quebra
-- sem ninguém perceber. É a mesma classe de defeito do campo que mente no
-- nome (CLAUDE.md §12.1).

do $$
begin
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.auxiliary_templates'::regclass
       and conname  = 'auxiliary_templates_catalog_state_chk'
  ) then
    alter table public.auxiliary_templates
      add constraint auxiliary_templates_catalog_state_chk
      check (catalog_state in ('available', 'coming_soon'));
  end if;

  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.auxiliary_templates'::regclass
       and conname  = 'auxiliary_templates_categories_chk'
  ) then
    alter table public.auxiliary_templates
      add constraint auxiliary_templates_categories_chk
      check (
        categories <@ array[
          'dinheiro_que_volta',   -- o que é seu e está parado
          'dinheiro_novo',        -- receita que existe e ninguém foi buscar
          'cliente_blindado',     -- a renovação antes de virar perda
          'negociacao',           -- o argumento que você não tem hoje
          'protecao_carteira',    -- não custa hoje, custa se acontecer
          'tempo_livre'           -- a hora que volta pra você
        ]::text[]
      );
  end if;
end $$;

-- -------------------------------------------------------------
-- 3. O índice da listagem
-- -------------------------------------------------------------
-- A página principal do Bloco C lista TODOS numa tela só, filtrando por
-- estado e categoria. É a consulta mais quente do módulo.

create index if not exists auxiliary_templates_catalogo_idx
  on public.auxiliary_templates (catalog_state, status)
  where status <> 'archived';

comment on column public.auxiliary_templates.headline is
  'SPEC-064 C.2 — a frase que vende o resultado, nunca a função técnica.';
comment on column public.auxiliary_templates.categories is
  'SPEC-064 C.4 — vocabulário fechado. Etiqueta, não pasta: um auxiliar pode ter várias e roda uma vez.';
comment on column public.auxiliary_templates.catalog_state is
  'SPEC-064 D.1 — available | coming_soon. Nenhum nasce ligado; coming_soon nem pode ser ligado.';
