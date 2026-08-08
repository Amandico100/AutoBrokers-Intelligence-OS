-- =============================================================
-- MIGRATION: spec067_a_vigencia_mora_na_versao
-- SPEC:      SPEC-067 — LOTE 0, item 6 (escritor de vigência)
-- AUTOR:     execução SPEC-067 LOTE 0        DATA: 2026-08-08
-- OBJETIVO:  dar à vigência da SUSEP um lugar por VERSÃO, e transformar as
--            colunas do documento em espelho declarado da versão vigente.
--
-- APPLY:     acrescenta effective_from, effective_until, version_label,
--            susep_version_id e vigencia_fonte em normative_document_versions;
--            cria o índice parcial que impede duas versões abertas do mesmo
--            documento; comenta as colunas espelho de normative_documents.
-- VERIFY:    §VERIFY — SQL executável, devolve uma linha por conferência.
-- ROLLBACK:  §ROLLBACK — DROP das colunas e do índice criados aqui.
--
-- EXPAND-FIRST: sim — só adiciona. Nenhum leitor atual é alterado.
-- DESTRUTIVA:   não
-- =============================================================
--
-- O QUE ESTAVA ERRADO
-- -------------------
-- 📊 Medido em 08/08/2026: `normative_documents.effective_until` e
-- `version_label` existem como colunas e estão NULL em **35 de 35**.
-- `normative_document_versions` tem 29 linhas, `version` mínima 1 e máxima 1,
-- `superseded_at` preenchido em **zero**.
--
-- ⚠️ Um levantamento anterior concluiu que "não existe coluna onde escrever".
-- 📊 Isso é falso — as colunas existem desde `20260725215808`. O defeito é de
-- ESCRITOR: `insurance_corpus.py:510-528` encadeia versões e nunca rodou,
-- porque nenhum documento chegou à segunda captura.
--
-- Diagnóstico errado leva a conserto errado: "falta coluna" produziria uma
-- coluna nova ao lado de duas vazias, e três lugares para a mesma verdade.
--
--
-- ONDE A VIGÊNCIA PASSA A MORAR, E POR QUÊ
-- ----------------------------------------
-- **A verdade mora na VERSÃO. O documento guarda um espelho da vigente.**
--
-- O registro do REP2 (SPEC-067 §3.2) publica Data de Início e Data de Fim de
-- Comercialização **por versão**, na tabela de Versões do produto. A data
-- descreve a versão, não a linhagem. 📊 Um produto pode ter 100 versões — a
-- Porto Auto tem. Guardar a vigência só no documento significaria que a
-- chegada da versão 101 apaga a data da 100, e a apólice emitida sob a 100
-- perde para sempre o intervalo em que foi contratada.
--
-- E isso não é hipótese contábil: o cabeçalho de `insurance_corpus.py` já diz
-- que "uma apólice emitida em 2023 é regida pela condição vigente NA EMISSÃO".
-- Responder por essa apólice exige achar a versão pela DATA. Uma coluna que
-- guarda só a data corrente não responde essa pergunta nunca.
--
-- As colunas do documento **não são apagadas** — são declaradas espelho:
--   · `catalogo()`, `ja_temos()` e o payload do Qdrant já leem
--     `normative_documents.effective_from`;
--   · removê-las quebraria três leitores por uma questão de arrumação;
--   · expand-first (MIGRATIONS-AUTHORITY §7) manda adicionar antes de remover.
-- O que muda é que passam a ter **um escritor só**, e o COMMENT diz isso a
-- quem chegar depois.
--
--
-- DUAS DATAS QUE NÃO SÃO A MESMA COISA
-- ------------------------------------
-- `effective_until`  = fato da SUSEP  — "a comercialização terminou em X"
-- `superseded_at`    = fato NOSSO     — "capturamos uma versão mais nova em Y"
--
-- Confundir as duas é a escada de inferência que a SPEC-067 §3.2 proíbe. Um
-- documento pode ser substituído no nosso acervo sem que a SUSEP tenha
-- publicado data de fim (o produto sumiu da lista, e sumir não é uma data). Se
-- nesse caso escrevêssemos `effective_until = ontem`, o acervo passaria a
-- afirmar como registro oficial um número que inventamos.
--
-- Então: quando a nova chega, a anterior **sempre** ganha `superseded_at`, e
-- ganha `effective_until` **só se a SUSEP tiver dito qual é**. Sem isso ela
-- fica com `vigencia_fonte = 'indeterminado'` — que é o que a §3.3 manda
-- registrar, e nunca "não mudou".
--
--
-- O GUARDA QUE FAZ O ESCRITOR EXISTIR
-- -----------------------------------
-- `normative_versao_aberta_uk` — no máximo UMA versão sem `superseded_at` por
-- documento. É o que transforma "quem fecha a anterior" de intenção em
-- obrigação: sem fechar a de ontem, a de hoje não entra. Um encadeamento que
-- depende só de o código lembrar é o encadeamento que 📊 não rodou nenhuma vez
-- em 29 capturas.
--
-- 📊 Conferido antes de escrever: 29 linhas, 29 document_id distintos, 29
-- abertas, **0 documentos com duas abertas**. O índice sobe sobre os dados de
-- hoje sem conflito.
-- =============================================================


-- -------------------------------------------------------------
-- APPLY
-- -------------------------------------------------------------

alter table public.normative_document_versions
  add column if not exists effective_from    date,
  add column if not exists effective_until   date,
  add column if not exists version_label     text,
  add column if not exists susep_version_id  text,
  add column if not exists vigencia_fonte    text;

-- A coerência do intervalo, na versão — a mesma regra que
-- `normative_vigencia_coerente` já impõe no documento.
do $$
begin
  if not exists (select 1 from pg_constraint
                  where conname = 'normative_versao_vigencia_coerente') then
    alter table public.normative_document_versions
      add constraint normative_versao_vigencia_coerente check (
        effective_until is null or effective_from is null
        or effective_until >= effective_from);
  end if;
end $$;

-- A procedência da data. `null` é permitido para não invalidar as 29 linhas
-- que já existem: elas não têm vigência nenhuma, e inventar uma procedência
-- para o que não tem data seria pior que o silêncio.
do $$
begin
  if not exists (select 1 from pg_constraint
                  where conname = 'normative_versao_vigencia_fonte_check') then
    alter table public.normative_document_versions
      add constraint normative_versao_vigencia_fonte_check check (
        vigencia_fonte is null
        or vigencia_fonte = any (array['susep_rep2',
                                       'texto_do_documento',
                                       'indeterminado']));
  end if;
end $$;

-- 🔴 O guarda. Uma versão aberta por documento.
create unique index if not exists normative_versao_aberta_uk
  on public.normative_document_versions (document_id)
  where superseded_at is null;

-- Achar a versão que valia numa data — a consulta que a apólice antiga exige.
create index if not exists normative_versao_por_data_idx
  on public.normative_document_versions (document_id, effective_from desc);

-- As colunas espelho, ditas em voz alta. CLAUDE.md §12.1: nome que mente sobre
-- o que guarda é defeito do campo, não do texto.
comment on column public.normative_documents.effective_from is
  'ESPELHO da versão vigente (normative_document_versions.effective_from). '
  'A verdade mora na versão — SPEC-067 LOTE 0 item 6. Escritor único: '
  'insurance_corpus.ingerir(). Não escrever aqui direto.';

comment on column public.normative_documents.effective_until is
  'ESPELHO da versão vigente. Preenchida só quando a SUSEP publicou Data de '
  'Fim de Comercialização; ausência NÃO significa "vigente para sempre", '
  'significa indeterminado (SPEC-067 §3.3).';

comment on column public.normative_documents.version_label is
  'ESPELHO do rótulo da versão vigente (ex.: "CG144"). '
  'A verdade mora em normative_document_versions.version_label.';

comment on column public.normative_document_versions.effective_from is
  'Data de Início de Comercialização, como publicada pelo REP2 da SUSEP. '
  'Fato do regulador — nunca inferido.';

comment on column public.normative_document_versions.effective_until is
  'Data de Fim de Comercialização publicada pelo REP2. NULL = a SUSEP não '
  'publicou. Não confundir com superseded_at, que é fato NOSSO.';

comment on column public.normative_document_versions.superseded_at is
  'Quando NÓS capturamos uma versão mais nova desta linhagem. Fato do acervo, '
  'não do regulador. Uma versão pode estar superseded com effective_until NULL.';

comment on column public.normative_document_versions.vigencia_fonte is
  'De onde vieram as datas: susep_rep2 (registro oficial) | '
  'texto_do_documento (extraído do PDF, menos confiável) | indeterminado.';

comment on column public.normative_document_versions.susep_version_id is
  'Id de download da versão no REP2 '
  '(.../REP2/Produto.aspx/DownloadConsultaPublica/{id}).';


-- -------------------------------------------------------------
-- VERIFY — read-only, uma linha por conferência, `ok` tem de ser todo `true`
-- -------------------------------------------------------------
/*
select 'colunas de vigencia na versao' as confere,
       count(*) = 5 as ok, count(*) as valor
  from information_schema.columns
 where table_schema='public' and table_name='normative_document_versions'
   and column_name in ('effective_from','effective_until','version_label',
                       'susep_version_id','vigencia_fonte')
union all
select 'constraint de coerencia do intervalo',
       count(*) = 1, count(*)
  from pg_constraint where conname='normative_versao_vigencia_coerente'
union all
select 'constraint de procedencia da data',
       count(*) = 1, count(*)
  from pg_constraint where conname='normative_versao_vigencia_fonte_check'
union all
select 'guarda de UMA versao aberta por documento',
       count(*) = 1, count(*)
  from pg_indexes
 where schemaname='public' and indexname='normative_versao_aberta_uk'
union all
select 'indice de busca por data',
       count(*) = 1, count(*)
  from pg_indexes
 where schemaname='public' and indexname='normative_versao_por_data_idx'
union all
select 'as colunas espelho ficaram comentadas',
       count(*) = 3, count(*)
  from pg_description d
  join pg_class c on c.oid = d.objoid
  join pg_attribute a on a.attrelid = c.oid and a.attnum = d.objsubid
 where c.relname='normative_documents'
   and a.attname in ('effective_from','effective_until','version_label')
union all
-- CONTROLE — nenhuma linha existente foi perdida nem alterada.
select 'as 29 versoes continuam la, todas abertas',
       count(*) = 29 and count(*) filter (where superseded_at is null) = 29,
       count(*)
  from public.normative_document_versions;


-- CONTROLE 2 — o guarda CONSEGUE recusar.
--
-- Um índice único que nunca recusa nada não guarda nada, e conferir a
-- EXISTÊNCIA dele (a linha 'guarda de UMA versao aberta' acima) não prova que
-- ele morde. Este bloco tenta abrir uma segunda versão do mesmo documento
-- dentro de uma transação que termina em ROLLBACK — nada é gravado.
--
-- Rode SEPARADO das consultas acima:

begin;
  insert into public.normative_document_versions (document_id, version, content_hash)
  select document_id, 999, 'controle-do-verify'
    from public.normative_document_versions
   where superseded_at is null
   limit 1;
  -- ESPERADO:
  --   ERROR: duplicate key value violates unique constraint
  --          "normative_versao_aberta_uk"
  --
  -- Se este INSERT PASSAR, o guarda não está guardando e todo o VERIFY acima
  -- está celebrando um índice decorativo.
rollback;
*/


-- -------------------------------------------------------------
-- ROLLBACK — escrito antes de aplicar (MIGRATIONS-AUTHORITY §7)
-- -------------------------------------------------------------
/*
-- ⚠️ DESTRUTIVO: apaga as datas de vigência já gravadas. Exige decisão do
-- Founder (CLAUDE.md §8, proibição 6). Só faz sentido se a migration for
-- revertida ANTES de o escritor rodar — depois disso, o rollback joga fora
-- registro da SUSEP que pode não estar mais publicado na origem.

drop index if exists public.normative_versao_por_data_idx;
drop index if exists public.normative_versao_aberta_uk;

alter table public.normative_document_versions
  drop constraint if exists normative_versao_vigencia_fonte_check,
  drop constraint if exists normative_versao_vigencia_coerente;

alter table public.normative_document_versions
  drop column if exists vigencia_fonte,
  drop column if exists susep_version_id,
  drop column if exists version_label,
  drop column if exists effective_until,
  drop column if exists effective_from;

comment on column public.normative_documents.effective_from   is null;
comment on column public.normative_documents.effective_until  is null;
comment on column public.normative_documents.version_label    is null;

-- VERIFY do rollback:
--   select count(*) = 0 as revertido from information_schema.columns
--    where table_schema='public' and table_name='normative_document_versions'
--      and column_name in ('effective_from','effective_until','version_label',
--                          'susep_version_id','vigencia_fonte');
*/
