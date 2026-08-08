-- =============================================================
-- MIGRATION: spec067_o_indice_sabe_de_que_versao_veio
-- SPEC:      SPEC-067 — LOTE 0, item 7 (doc_id versionado no Qdrant)
-- AUTOR:     execução SPEC-067 LOTE 0        DATA: 2026-08-08
-- OBJETIVO:  dar a cada versão o endereço exato dos pontos que ela pôs no
--            índice, para que substituir a versão deixe de ser um ato cego.
--
-- APPLY:     acrescenta qdrant_doc_id e qdrant_collection em
--            normative_document_versions; faz o backfill das 29 linhas
--            existentes com o id que o código REALMENTE usou; cria o índice
--            único que impede duas versões de reivindicarem os mesmos pontos.
-- VERIFY:    §VERIFY — SQL executável.
-- ROLLBACK:  §ROLLBACK.
--
-- EXPAND-FIRST: sim — só adiciona. Nenhum ponto do Qdrant é tocado por esta
--               migration; ela apenas ANOTA o que já é verdade.
-- DESTRUTIVA:   não
-- =============================================================
--
-- O QUE ESTAVA ERRADO
-- -------------------
-- 📊 `insurance_corpus.py:236` monta `doc_id = f"norm-{doc['id']}"` — **o mesmo
-- id para todas as versões da mesma linhagem**. E a linha 243 chama
-- `delete_document(doc_id)` ANTES de inserir.
--
-- A consequência tem três camadas, e a terceira é a pior:
--
-- 1. A versão nova apaga a anterior do índice. Isso contraria a D-Acervo-02,
--    que manda o revogado sair da BUSCA e continuar endereçável.
--
-- 2. Existe uma janela em que o documento tem ZERO pontos no índice: entre o
--    delete e o upsert. Se a ingestão falhar no meio — e ela falha, 📊 vinte e
--    três documentos ficaram presos oito dias em 05/08 — o documento some da
--    busca enquanto `normative_documents.status` continua dizendo `ingested`.
--    O catálogo afirma presença; o índice não tem nada.
--
-- 3. 🔴 **Olhando um trecho recuperado, não há como saber de que versão ele é.**
--    O payload diz `norm-<uuid>` e mais nada. Para descobrir se aquele texto
--    ainda vale é preciso ir ao banco — e se banco e índice discordarem,
--    nenhum dos dois percebe. É um estado misto e invisível, que é exatamente
--    o que esta migration existe para tornar impossível.
--
--
-- O ESQUEMA
-- ---------
--     legado (11.409 pontos)   norm-<document_id>
--     a partir daqui           norm-<document_id>-v<n>
--
-- e cada linha de `normative_document_versions` guarda, em `qdrant_doc_id`, o
-- id dos pontos que ELA pôs lá.
--
-- Com isso a substituição vira expand-then-contract, na ordem certa:
--
--     1. insere a versão n com id novo        (o índice tem as DUAS)
--     2. confere que entrou
--     3. remove os ids das versões anteriores (o índice tem só a nova)
--
-- Não há mais janela vazia. Se o passo 3 não acontecer, o defeito é "duas
-- versões na busca" — visível, mensurável por `count(*) group by qdrant_doc_id`
-- — em vez de "nenhuma versão na busca", que é silencioso.
--
--
-- A TRANSIÇÃO — e por que ela não deixa estado misto
-- --------------------------------------------------
-- ⚠️ Mudar o esquema de id significa que os 11.409 pontos existentes ficam com
-- o esquema antigo. A pergunta certa não é "como renomear os pontos" (isso
-- custaria re-embedar 11.409 trechos) e sim **"como fazer o índice continuar
-- inteiramente explicado pelo banco"**.
--
-- 📊 Medido em 08/08/2026, e é o que torna a transição exata:
--
--     normative_documents  status='ingested'  ....... 29, chunks 11.409
--       destes, sem linha em ..._versions  .......... 0
--     normative_documents  status='discovered' ...... 6, chunks 0
--       destes, sem linha em ..._versions  .......... 6
--     normative_document_versions  ................ 29 linhas
--       document_id distintos  ..................... 29
--
-- Isto é: **cada um dos 11.409 pontos pertence a exatamente uma das 29 linhas
-- de versão**, e o id que o código usou para gravá-los é `'norm-' ||
-- document_id`. O backfill não infere nada — ele transcreve o que
-- `insurance_corpus.py:236` calculou. Depois dele não sobra um único ponto
-- órfão no índice: todo id de documento presente no Qdrant está nomeado por
-- uma linha do banco.
--
-- Nada é re-embedado. Nada é apagado. Custo em API: **zero**.
--
-- O legado só é removido quando a versão 2 daquela linhagem chegar — e aí o
-- código sabe exatamente o que remover, porque está escrito na linha da
-- versão 1. Documento que nunca mudar guarda o id antigo para sempre, e isso
-- está certo: o esquema do id é um detalhe de endereçamento, não um fato sobre
-- o contrato.
-- =============================================================


-- -------------------------------------------------------------
-- APPLY
-- -------------------------------------------------------------

alter table public.normative_document_versions
  add column if not exists qdrant_doc_id     text,
  add column if not exists qdrant_collection text;

-- Backfill. `is null` no WHERE: idempotente e nunca sobrescreve um id que o
-- escritor novo já tenha gravado.
update public.normative_document_versions v
   set qdrant_doc_id     = 'norm-' || v.document_id::text,
       qdrant_collection = coalesce(d.qdrant_collection, 'autobrokers_global')
  from public.normative_documents d
 where d.id = v.document_id
   and v.qdrant_doc_id is null;

-- Dois conjuntos de pontos não podem ter o mesmo endereço. Sem isto, um erro
-- de cálculo do id faria a versão nova apagar a anterior de novo — só que
-- agora em silêncio, porque o banco estaria dizendo que são a mesma coisa.
create unique index if not exists normative_versao_qdrant_doc_id_uk
  on public.normative_document_versions (qdrant_doc_id)
  where qdrant_doc_id is not null;

comment on column public.normative_document_versions.qdrant_doc_id is
  'Endereço dos pontos DESTA versão no Qdrant (payload.document_id). '
  'Esquema: norm-<document_id>-v<n>. As 29 linhas anteriores a 08/08/2026 '
  'guardam o esquema legado norm-<document_id>, sem sufixo — que é o id que '
  'insurance_corpus.py realmente usou. SPEC-067 LOTE 0 item 7.';

comment on column public.normative_document_versions.qdrant_collection is
  'Coleção onde esta versão foi indexada. Hoje sempre autobrokers_global.';


-- -------------------------------------------------------------
-- VERIFY — read-only, `ok` tem de ser todo `true`
-- -------------------------------------------------------------
/*
select 'as duas colunas existem' as confere,
       count(*) = 2 as ok, count(*) as valor
  from information_schema.columns
 where table_schema='public' and table_name='normative_document_versions'
   and column_name in ('qdrant_doc_id','qdrant_collection')
union all
select 'o backfill cobriu as 29 linhas',
       count(*) = 29, count(*)
  from public.normative_document_versions where qdrant_doc_id is not null
union all
select 'nenhuma linha ficou sem endereco',
       count(*) = 0, count(*)
  from public.normative_document_versions where qdrant_doc_id is null
union all
select 'todo endereco do backfill tem a forma legada norm-<uuid>',
       count(*) = 29, count(*)
  from public.normative_document_versions
 where qdrant_doc_id = 'norm-' || document_id::text
union all
select 'nenhum endereco repetido',
       count(*) = 0, count(*)
  from (select qdrant_doc_id from public.normative_document_versions
         where qdrant_doc_id is not null
         group by 1 having count(*) > 1) x
union all
select 'o indice unico existe',
       count(*) = 1, count(*)
  from pg_indexes
 where schemaname='public' and indexname='normative_versao_qdrant_doc_id_uk'
union all
-- CONTROLE — o índice do acervo continua inteiramente explicado pelo banco.
-- Todo documento com pontos no Qdrant tem linha de versão nomeando esses
-- pontos; nenhum ponto fica órfão. Se este virar false, existe conteúdo no
-- índice que o banco não sabe endereçar — e é exatamente o estado misto e
-- invisível que a migration existe para impedir.
select 'CONTROLE: nenhum documento ingerido sem endereco de versao',
       count(*) = 0, count(*)
  from public.normative_documents d
 where d.status = 'ingested'
   and not exists (select 1 from public.normative_document_versions v
                    where v.document_id = d.id and v.qdrant_doc_id is not null)
union all
-- CONTROLE 2 — a contagem de chunks do banco bate com a soma das versões.
-- Sem esta linha, um backfill que gravasse endereço em linhas erradas
-- passaria em todas as conferências acima.
select 'CONTROLE 2: os 11.409 chunks estao distribuidos pelas 29 versoes',
       (select coalesce(sum(chunk_count),0) from public.normative_document_versions
         where qdrant_doc_id is not null)
       = (select coalesce(sum(chunk_count),0) from public.normative_documents
           where status='ingested'),
       (select coalesce(sum(chunk_count),0) from public.normative_document_versions
         where qdrant_doc_id is not null);
*/


-- -------------------------------------------------------------
-- ROLLBACK
-- -------------------------------------------------------------
/*
-- Não destrutivo para o índice: nenhum ponto do Qdrant foi criado, movido ou
-- apagado por esta migration. Reverter só apaga a ANOTAÇÃO — e o efeito de
-- apagá-la é voltar a não saber de que versão vem cada ponto.

drop index if exists public.normative_versao_qdrant_doc_id_uk;

alter table public.normative_document_versions
  drop column if exists qdrant_collection,
  drop column if exists qdrant_doc_id;

-- ⚠️ Se o escritor novo já tiver rodado, alguma versão terá pontos gravados
-- com id `norm-<uuid>-v<n>` e o banco deixará de saber onde eles estão. Nesse
-- caso o rollback do SCHEMA exige também limpar esses pontos do Qdrant, ou o
-- índice fica com conteúdo que nada endereça. Confira antes:
--   select count(*) from normative_document_versions
--    where qdrant_doc_id like '%-v%';
--   Se > 0, NÃO reverta sem decidir o que fazer com esses pontos.

-- VERIFY do rollback:
--   select count(*) = 0 as revertido from information_schema.columns
--    where table_schema='public' and table_name='normative_document_versions'
--      and column_name in ('qdrant_doc_id','qdrant_collection');
*/
