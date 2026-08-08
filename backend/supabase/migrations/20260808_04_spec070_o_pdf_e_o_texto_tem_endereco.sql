-- =============================================================
-- MIGRATION: spec067_o_pdf_e_o_texto_tem_endereco
-- SPEC:      SPEC-070 — LOTE 0, item 4 (guardar PDF e texto)
-- AUTOR:     execução SPEC-070 LOTE 0        DATA: 2026-08-08
-- OBJETIVO:  dar ao texto-fonte do acervo um lugar fora do índice de busca.
--
-- APPLY:     acrescenta text_storage_ref, source_bytes, source_media_type e
--            arquivado_em em normative_document_versions.
-- VERIFY:    §VERIFY — SQL executável.
-- ROLLBACK:  §ROLLBACK.
--
-- EXPAND-FIRST: sim. `storage_ref` já existia e continua significando a mesma
--               coisa — o arquivo ORIGINAL. Nada é renomeado.
-- DESTRUTIVA:   não
-- =============================================================
--
-- O QUE ESTAVA ERRADO — e é o mais grave dos quatro
-- --------------------------------------------------
-- 📊 `storage_ref` existe e está preenchido em **0 de 29**. O PDF é baixado
-- (`insurance_corpus._baixar_pdf_direto`), lido em memória e **descartado** —
-- a variável com os bytes morre no fim da função. O texto extraído é picado e
-- vai para o Qdrant; em lugar nenhum ele é gravado inteiro.
--
-- > **O texto-fonte do acervo existe hoje em um único lugar: dentro do Qdrant,
-- > picado em 11.409 pedaços.**
--
-- Isso inverte o CLAUDE.md §6, que declara Qdrant "índice derivado e
-- reconstruível". Ele não é derivado — ele é o original. E um índice que é o
-- original não pode ser reconstruído, reprocessado com um extrator melhor, nem
-- perdido sem perder o acervo.
--
-- E a janela para consertar está fechando: 📊 testado em 08/08/2026, a URL da
-- HDI devolve **500** e a da Allianz devolve **403**. Documento que baixamos
-- ontem já não baixa hoje. Cada reprocessamento adiado é conteúdo que pode não
-- existir mais na origem.
--
-- Isso importa concretamente para o LOTE 0 inteiro: os itens 1, 2 e 3
-- (PyMuPDF, cabeçalho por pedaço, corte por seção) só se aplicam ao acervo
-- existente se o PDF estiver guardado. Sem esta migration, "reprocessar os 29
-- documentos com o extrator novo" significa baixá-los de novo — e dois já não
-- respondem.
--
--
-- TRÊS ENDEREÇOS, PORQUE SÃO TRÊS COISAS
-- --------------------------------------
--   storage_ref       o arquivo como veio  (PDF, bytes intactos)
--   text_storage_ref  o texto extraído     (o que o extrator entendeu)
--   qdrant_doc_id     os pedaços indexados (migration 02)
--
-- Guardar só o PDF não basta: o texto é o que se compara entre extratores para
-- provar que o PyMuPDF melhorou. Guardar só o texto não basta: extrator novo
-- precisa do PDF. E `byte_size`, que já existe, mede o TEXTO
-- (`len(texto.encode("utf-8"))`, `insurance_corpus.py:518`) — por isso o
-- tamanho do arquivo original ganha coluna própria em vez de reaproveitar
-- aquela. Dois números diferentes no mesmo campo é a receita do §12.1.
--
-- ⚠️ `arquivado_em` não é enfeite: sem ele, `storage_ref is null` não distingue
-- "ainda não arquivamos" de "tentamos e não deu". Um estado que só se observa
-- quando nasce não é observado.
-- =============================================================


-- -------------------------------------------------------------
-- APPLY
-- -------------------------------------------------------------

alter table public.normative_document_versions
  add column if not exists text_storage_ref  text,
  add column if not exists source_bytes      integer,
  add column if not exists source_media_type text,
  add column if not exists arquivado_em      timestamptz;

-- Quem ainda não tem o original guardado — a fila de reprocessamento do LOTE 0.
-- Parcial: 📊 hoje ela é 29 de 29, e a intenção é que encolha até zero.
create index if not exists normative_versao_sem_arquivo_idx
  on public.normative_document_versions (fetched_at)
  where storage_ref is null;

comment on column public.normative_document_versions.storage_ref is
  'Caminho no MinIO do arquivo ORIGINAL (o PDF como veio da origem). '
  '📊 NULL em 29 de 29 em 08/08/2026 — o PDF era descartado. SPEC-070 item 4.';

comment on column public.normative_document_versions.text_storage_ref is
  'Caminho no MinIO do texto extraído inteiro. É o que permite trocar de '
  'extrator e COMPARAR, e o que tira do Qdrant o papel de original.';

comment on column public.normative_document_versions.byte_size is
  'Tamanho do TEXTO extraído em bytes UTF-8 — não do arquivo. O tamanho do '
  'arquivo é source_bytes.';

comment on column public.normative_document_versions.source_bytes is
  'Tamanho do arquivo original em bytes. Diferente de byte_size, que é o texto.';

comment on column public.normative_document_versions.arquivado_em is
  'Quando o original foi guardado no MinIO. NULL com storage_ref NULL = nunca '
  'tentamos; distingue "não arquivado" de "falhou ao arquivar".';


-- -------------------------------------------------------------
-- VERIFY — read-only, `ok` tem de ser todo `true`
-- -------------------------------------------------------------
/*
select 'as quatro colunas de arquivo existem' as confere,
       count(*) = 4 as ok, count(*) as valor
  from information_schema.columns
 where table_schema='public' and table_name='normative_document_versions'
   and column_name in ('text_storage_ref','source_bytes',
                       'source_media_type','arquivado_em')
union all
select 'o indice da fila de reprocessamento existe',
       count(*) = 1, count(*)
  from pg_indexes
 where schemaname='public' and indexname='normative_versao_sem_arquivo_idx'
union all
select 'byte_size continua descrevendo o TEXTO, e agora diz isso',
       count(*) = 1, count(*)
  from pg_description d
  join pg_class c on c.oid = d.objoid
  join pg_attribute a on a.attrelid = c.oid and a.attnum = d.objsubid
 where c.relname='normative_document_versions' and a.attname='byte_size'
union all
-- O retrato do dia da aplicação. Não é um teste que tem de dar 29 para sempre:
-- é o marco contra o qual se mede o progresso do arquivamento.
select 'RETRATO: versoes ainda sem o original guardado',
       true, count(*)
  from public.normative_document_versions where storage_ref is null
union all
select 'RETRATO: versoes ainda sem o texto guardado',
       true, count(*)
  from public.normative_document_versions where text_storage_ref is null
union all
-- CONTROLE — nenhuma linha foi tocada.
select 'CONTROLE: as 29 versoes continuam la',
       count(*) = 29, count(*)
  from public.normative_document_versions;
*/


-- -------------------------------------------------------------
-- ROLLBACK
-- -------------------------------------------------------------
/*
-- ⚠️ Reverter apaga os PONTEIROS, não os arquivos. Os objetos ficam no MinIO,
-- órfãos — presentes, pagos e inalcançáveis. Antes de reverter, exporte:
--   select id, document_id, storage_ref, text_storage_ref
--     from normative_document_versions
--    where storage_ref is not null or text_storage_ref is not null;

drop index if exists public.normative_versao_sem_arquivo_idx;

alter table public.normative_document_versions
  drop column if exists arquivado_em,
  drop column if exists source_media_type,
  drop column if exists source_bytes,
  drop column if exists text_storage_ref;

comment on column public.normative_document_versions.storage_ref is null;
comment on column public.normative_document_versions.byte_size   is null;

-- VERIFY do rollback:
--   select count(*) = 0 as revertido from information_schema.columns
--    where table_schema='public' and table_name='normative_document_versions'
--      and column_name in ('text_storage_ref','source_bytes',
--                          'source_media_type','arquivado_em');
*/
