-- =============================================================
-- MIGRATION: spec067_a_carta_sabe_de_que_contrato_saiu
-- SPEC:      SPEC-070 — LOTE 0, item 8 (procedência em knowledge_cards)
-- AUTOR:     execução SPEC-070 LOTE 0        DATA: 2026-08-08
-- OBJETIVO:  poder achar, quando um contrato for substituído, as cartas que
--            saíram dele — hoje é impossível.
--
-- APPLY:     acrescenta source_document_id, source_version_id e source_unit_id
--            em knowledge_cards, com FK e índices. Nenhuma linha existente é
--            alterada.
-- VERIFY:    §VERIFY — SQL executável.
-- ROLLBACK:  §ROLLBACK.
--
-- EXPAND-FIRST: sim — três colunas NULLABLE, nenhum leitor atual muda.
-- DESTRUTIVA:   não
-- =============================================================
--
-- O QUE ESTAVA ERRADO
-- -------------------
-- 📊 Conferido em 08/08/2026 por `information_schema.columns`:
-- `knowledge_cards` tem **11 colunas** — id, card_hash, card_text, category,
-- ramo, insurer_key, status, pii_check, source_count, created_at, published_at
-- — e **nenhuma aponta para o documento de origem**.
--
-- **A consequência, em uma frase:** quando a Porto publicar a CG144, não há
-- como achar as cartas que saíram da CG140. Elas continuam publicadas
-- afirmando o que o contrato antigo dizia, indistinguíveis das corretas.
--
-- E não é um risco distante: 📊 12 de 13 documentos indexados hoje são versões
-- revogadas (SPEC-070 §1). A troca não é um evento futuro — é o backlog.
--
-- O `source_count` que já existe conta QUANTAS fontes, não QUAIS. Ele responde
-- "essa ideia apareceu 3 vezes" e nunca "essa ideia veio da cláusula 76R da
-- CG140". São perguntas diferentes, e só a segunda permite retirar uma carta
-- quando o contrato dela cair.
--
--
-- AS 12.933 CARTAS DE HOJE FICAM SEM PROCEDÊNCIA — E ISSO É O CERTO
-- ------------------------------------------------------------------
-- 📊 São 12.933 linhas em `knowledge_cards`. Nenhuma tem como saber de onde
-- veio, porque elas foram destiladas de **conversas de atendimento**, não de
-- condições gerais. Não existe documento para apontar.
--
-- 🔴 **Não há backfill nesta migration, e isso é deliberado.** Preencher
-- `source_document_id` por adivinhação — casando seguradora e ramo, por
-- exemplo — produziria uma procedência que parece verificada e não é. Uma
-- carta que aponta para o documento errado é pior que uma sem ponteiro: a sem
-- ponteiro se declara ignorante; a errada dá confiança falsa e sobrevive à
-- revisão de quem confia nela.
--
-- NULL aqui quer dizer exatamente uma coisa: **"não sabemos de que documento
-- saiu"**. É a verdade sobre essas 12.933, e deve continuar assim.
--
-- As cartas destiladas de documento a partir do LOTE 1 nascem com os três
-- campos preenchidos (SPEC-070 §10.4 traz `unit_id_origem` no JSONL do
-- subagente, e é ele que entra em `source_unit_id`).
--
--
-- POR QUE OS NOMES NÃO SÃO `document_id` E `document_version`
-- -----------------------------------------------------------
-- A SPEC-070 §11 item 8 os chama assim. ⚠️ Aqui eles viram
-- `source_document_id` / `source_version_id`, e o motivo é o CLAUDE.md §12.1:
-- **nome que mente sobre o que guarda é defeito do campo.**
--
-- Existe no mesmo banco a tabela `documents`, que é o documento DA CORRETORA
-- (apólice, proposta, arquivo do cliente). Uma coluna `document_id` em
-- `knowledge_cards` seria lida como ponteiro para lá por qualquer pessoa que
-- chegasse depois — e `knowledge_cards` é conhecimento GLOBAL, sem dono
-- (D-Acervo-01), enquanto `documents` é material de um tenant. Confundir os
-- dois é o caminho mais curto para um vazamento entre corretoras.
--
-- `source_version_id` é uuid, não inteiro: a `version` inteira só é única
-- dentro de um documento. Guardar o inteiro exigiria os dois campos para
-- identificar uma versão, e o par pode ficar incoerente. O uuid não pode.
--
--
-- ON DELETE RESTRICT, e não CASCADE nem SET NULL
-- ----------------------------------------------
-- · CASCADE apagaria conhecimento publicado porque um PDF saiu do catálogo.
--   Carta destilada não morre com a fonte — ela vira "na prática, o
--   atendimento costuma…" (SPEC-070 §6).
-- · SET NULL apagaria em silêncio a única coisa que esta migration cria, e
--   recriaria o defeito de hoje sem deixar rastro.
-- · RESTRICT diz o que é verdade: **não dá para apagar um documento que tem
--   carta apoiada nele sem antes decidir o que fazer com a carta.**
--
-- 📊 Custo real disso: zero. Uma varredura em `backend/` por
-- `.table("normative_documents").delete` e equivalente devolveu **nenhum
-- acerto** — nada no código apaga documento normativo. O RESTRICT não bloqueia
-- caminho nenhum que exista hoje; ele bloqueia o caminho que alguém abriria
-- sem perceber.
-- =============================================================


-- -------------------------------------------------------------
-- APPLY
-- -------------------------------------------------------------

alter table public.knowledge_cards
  add column if not exists source_document_id uuid,
  add column if not exists source_version_id  uuid,
  add column if not exists source_unit_id     text;

-- FK como NOT VALID: `knowledge_cards` tem 12.933 linhas e todas terão NULL
-- nas colunas novas, então a validação passaria na hora — mas o padrão da
-- MIGRATIONS-AUTHORITY §7 para tabela grande é expandir sem varrer, e o
-- VALIDATE logo abaixo não pega lock de escrita.
do $$
begin
  if not exists (select 1 from pg_constraint
                  where conname = 'knowledge_cards_source_document_fk') then
    alter table public.knowledge_cards
      add constraint knowledge_cards_source_document_fk
      foreign key (source_document_id)
      references public.normative_documents(id)
      on delete restrict
      not valid;
  end if;

  if not exists (select 1 from pg_constraint
                  where conname = 'knowledge_cards_source_version_fk') then
    alter table public.knowledge_cards
      add constraint knowledge_cards_source_version_fk
      foreign key (source_version_id)
      references public.normative_document_versions(id)
      on delete restrict
      not valid;
  end if;
end $$;

alter table public.knowledge_cards
  validate constraint knowledge_cards_source_document_fk;
alter table public.knowledge_cards
  validate constraint knowledge_cards_source_version_fk;

-- A versão apontada tem de ser DAQUELE documento. Sem isto, uma carta poderia
-- dizer "veio da CG140 da Porto, versão 3 do condomínio do Bradesco" e o banco
-- aceitaria — dois ponteiros certos formando uma procedência falsa.
--
-- ⚠️ Não dá para expressar isso como CHECK (CHECK não consulta outra tabela) e
-- a FK composta exigiria uma UNIQUE (id, document_id) em ..._versions. O
-- caminho é a UNIQUE redundante — barata, e é o que torna a coerência
-- verificável pelo banco em vez de confiável pelo código.
do $$
begin
  if not exists (select 1 from pg_constraint
                  where conname = 'normative_versao_id_documento_uk') then
    alter table public.normative_document_versions
      add constraint normative_versao_id_documento_uk unique (id, document_id);
  end if;

  if not exists (select 1 from pg_constraint
                  where conname = 'knowledge_cards_procedencia_coerente_fk') then
    alter table public.knowledge_cards
      add constraint knowledge_cards_procedencia_coerente_fk
      foreign key (source_version_id, source_document_id)
      references public.normative_document_versions(id, document_id)
      on delete restrict
      not valid;
  end if;
end $$;

alter table public.knowledge_cards
  validate constraint knowledge_cards_procedencia_coerente_fk;

-- "Quais cartas saíram deste documento?" — a pergunta que hoje não tem
-- resposta. Parcial porque 📊 12.933 de 12.933 ficarão NULL.
create index if not exists knowledge_cards_procedencia_idx
  on public.knowledge_cards (source_document_id)
  where source_document_id is not null;

create index if not exists knowledge_cards_versao_de_origem_idx
  on public.knowledge_cards (source_version_id)
  where source_version_id is not null;

comment on column public.knowledge_cards.source_document_id is
  'Documento normativo de onde a carta foi destilada. NULL = não se sabe — é '
  'o caso das 12.933 cartas anteriores a 08/08/2026, que vieram de conversas '
  'de atendimento e não de contrato. NULL nunca deve ser preenchido por '
  'adivinhação. SPEC-070 LOTE 0 item 8.';

comment on column public.knowledge_cards.source_version_id is
  'Versão exata do documento. É ela que permite saber, quando a versão for '
  'substituída, que esta carta afirma o que o contrato ANTIGO dizia.';

comment on column public.knowledge_cards.source_unit_id is
  'unit_id do trecho de origem (SPEC-070 §10.4, campo unit_id_origem do JSONL '
  'do subagente destilador). Leva da carta de volta à cláusula.';


-- -------------------------------------------------------------
-- VERIFY — read-only, `ok` tem de ser todo `true`
-- -------------------------------------------------------------
/*
select 'as tres colunas de procedencia existem' as confere,
       count(*) = 3 as ok, count(*) as valor
  from information_schema.columns
 where table_schema='public' and table_name='knowledge_cards'
   and column_name in ('source_document_id','source_version_id','source_unit_id')
union all
select 'as tres sao nullable (expand-first)',
       count(*) = 3, count(*)
  from information_schema.columns
 where table_schema='public' and table_name='knowledge_cards'
   and column_name in ('source_document_id','source_version_id','source_unit_id')
   and is_nullable = 'YES'
union all
select 'as tres FKs existem e estao VALIDADAS',
       count(*) = 3, count(*)
  from pg_constraint
 where conrelid = 'public.knowledge_cards'::regclass
   and contype = 'f' and convalidated
   and conname in ('knowledge_cards_source_document_fk',
                   'knowledge_cards_source_version_fk',
                   'knowledge_cards_procedencia_coerente_fk')
union all
select 'as tres FKs sao ON DELETE RESTRICT',
       count(*) = 3, count(*)
  from pg_constraint
 where conrelid = 'public.knowledge_cards'::regclass
   and contype = 'f' and confdeltype = 'r'
   and conname like 'knowledge_cards_%'
union all
select 'os dois indices de procedencia existem',
       count(*) = 2, count(*)
  from pg_indexes
 where schemaname='public'
   and indexname in ('knowledge_cards_procedencia_idx',
                     'knowledge_cards_versao_de_origem_idx')
union all
-- 🔴 A LINHA MAIS IMPORTANTE. As 12.933 cartas de hoje continuam sem
-- procedência. Se este número deixar de ser 12.933, alguém fez backfill por
-- adivinhação — e isso é pior que a ausência que a migration admite.
select 'as 12.933 cartas continuam SEM procedencia inventada',
       count(*) = 12933, count(*)
  from public.knowledge_cards where source_document_id is null
union all
select 'CONTROLE: nenhuma linha foi perdida',
       count(*) = 12933, count(*)
  from public.knowledge_cards;

-- CONTROLE 2 — a coerência CONSEGUE recusar. Uma FK composta que nunca recusa
-- é decoração. Este bloco tenta apontar uma versão que não é do documento
-- apontado, dentro de transação abortada. Rode SEPARADO:

begin;
  update public.knowledge_cards
     set source_document_id = (select id from public.normative_documents
                                order by created_at limit 1),
         source_version_id  = (select v.id from public.normative_document_versions v
                                where v.document_id <> (select id
                                                          from public.normative_documents
                                                         order by created_at limit 1)
                                limit 1)
   where id = (select id from public.knowledge_cards limit 1);
  -- ESPERADO:
  --   ERROR: insert or update on table "knowledge_cards" violates foreign key
  --          constraint "knowledge_cards_procedencia_coerente_fk"
  --
  -- Se PASSAR, a procedência pode mentir e o par (documento, versão) não
  -- significa nada.
rollback;

-- CONTROLE 3 — e o par CERTO é aceito. Sem esta linha, o CONTROLE 2 passaria
-- igual se a FK recusasse tudo.
begin;
  update public.knowledge_cards
     set source_document_id = v.document_id,
         source_version_id  = v.id
    from (select id, document_id from public.normative_document_versions limit 1) v
   where public.knowledge_cards.id = (select id from public.knowledge_cards limit 1);
  -- ESPERADO: UPDATE 1, sem erro.
rollback;
*/


-- -------------------------------------------------------------
-- ROLLBACK
-- -------------------------------------------------------------
/*
-- ⚠️ Destrutivo a partir do momento em que o LOTE 1 gravar procedência: apaga
-- a ligação carta → cláusula, que não se reconstrói sem redestilar. Confira
-- antes:
--   select count(*) from knowledge_cards where source_document_id is not null;
--   Se > 0, reverter joga esse trabalho fora.

drop index if exists public.knowledge_cards_versao_de_origem_idx;
drop index if exists public.knowledge_cards_procedencia_idx;

alter table public.knowledge_cards
  drop constraint if exists knowledge_cards_procedencia_coerente_fk,
  drop constraint if exists knowledge_cards_source_version_fk,
  drop constraint if exists knowledge_cards_source_document_fk;

alter table public.normative_document_versions
  drop constraint if exists normative_versao_id_documento_uk;

alter table public.knowledge_cards
  drop column if exists source_unit_id,
  drop column if exists source_version_id,
  drop column if exists source_document_id;

-- VERIFY do rollback:
--   select count(*) = 0 as revertido from information_schema.columns
--    where table_schema='public' and table_name='knowledge_cards'
--      and column_name like 'source_%'
--      and column_name <> 'source_count';
*/
