-- =============================================================
-- MIGRATION: `normative_documents.doc_kind` aceita `manual_de_assistencia`
-- SPEC:      SPEC-EXTRA-001.5 — BLOCO A (unidade A, fatia 1) · §11.2
-- AUTOR:     builder Opus 5 xhigh (AAA FAST v12.2)      DATA: 2026-09-17
-- OBJETIVO:  o manual de assistencia (o documento que DIZ o que cada plano
--            cobre) pode entrar no corpus sob o proprio nome.
--
-- 🔴 PISO CRITICO (protocolo §3.2): esta migration ALTERA UMA TRAVA de uma
--    tabela VIVA, com 194 linhas em producao, e a tabela e classe SEM_ARQUIVO
--    (o DDL so existe em docs/canon/sql/reconstruidas/…, PROIBIDO APLICAR).
--    Por isso o CHECK real foi LIDO DO CATALOGO, e o manifesto esta abaixo.
--
-- APPLY:     DROP + ADD do CHECK `normative_documents_doc_kind_check` em
--            TRANSACAO UNICA, com o valor novo acrescentado aos 9 antigos.
-- VERIFY:    secao VERIFY no fim deste arquivo.
-- ROLLBACK:  secao ROLLBACK no fim deste arquivo — 🔴 com GUARDA DE CONTAGEM.
--
-- EXPAND-FIRST: sim — o CHECK novo e SUPERCONJUNTO do antigo. Nenhuma linha
--               existente perde validade; nenhum leitor perde valor.
-- DESTRUTIVA:   nao — nenhuma linha e tocada, nenhuma coluna sai.
--
-- =============================================================
-- 📋 MANIFESTO (MIGRATIONS-AUTHORITY §5), medido em 17/09/2026 no banco de
--    producao, so SELECT, ANTES de qualquer escrita.
--
-- (1) O CHECK ATUAL, COLADO da saida do catalogo:
--
--   select conname, pg_get_constraintdef(oid) from pg_constraint
--    where conrelid='public.normative_documents'::regclass and contype='c';
--
--   normative_documents_doc_kind_check | CHECK ((doc_kind = ANY (ARRAY[
--     'condicoes_gerais'::text, 'condicoes_especiais'::text,
--     'condicoes_particulares'::text, 'manual_do_segurado'::text,
--     'nota_tecnica'::text, 'circular_susep'::text, 'tabela_coberturas'::text,
--     'glossario'::text, 'regulamento'::text])))
--
--   ⚠️ O NOME REAL da constraint e `normative_documents_doc_kind_check`.
--   📊 A tabela tem outros 4 CHECKs, e NENHUM deles e tocado aqui:
--      normative_documents_check_interval_days_check ·
--      normative_documents_status_check · normative_ingested_has_hash ·
--      normative_vigencia_coerente
--
-- (2) OS VALORES EM USO:
--
--   select doc_kind, count(*) from normative_documents group by 1 order by 2 desc;
--   -> condicoes_gerais 184 · manual_do_segurado 5 · circular_susep 5
--   -> TOTAL 194 linhas. 3 dos 9 valores em uso; 6 declarados e vazios.
--
-- (3) 🔴 DECLARACAO: NENHUMA LINHA EXISTENTE PERDE VALIDADE.
--     O CHECK novo contem os 9 valores antigos, LETRA POR LETRA, mais
--     `manual_de_assistencia`. Os 3 valores em uso estao entre os 9. Logo as
--     194 linhas continuam validas, e o ADD nao pode falhar por dado velho.
--     A conferencia por maquina esta no VERIFY V3 (contagem por doc_kind).
--
-- (4) ⚠️ POR QUE TRANSACAO UNICA, e nao e formalidade:
--     entre o DROP e o ADD a tabela viva fica SEM TRAVA, e ela TEM escritor
--     ativo (`insurance_corpus.py` reconfere o corpus sozinho). Fora de
--     transacao, uma ingestao que caia nessa janela grava um `doc_kind` que o
--     CHECK novo recusaria — e o ADD falha depois, deixando a tabela SEM
--     constraint nenhuma. Dentro da transacao, o lock do ALTER serializa.
-- =============================================================

begin;

alter table public.normative_documents
    drop constraint if exists normative_documents_doc_kind_check;

alter table public.normative_documents
    add constraint normative_documents_doc_kind_check
    check (doc_kind = any (array[
        'condicoes_gerais',
        'condicoes_especiais',
        'condicoes_particulares',
        'manual_do_segurado',
        'nota_tecnica',
        'circular_susep',
        'tabela_coberturas',
        'glossario',
        'regulamento',
        'manual_de_assistencia'      -- <- o UNICO valor novo
    ]));

commit;

-- =============================================================
-- VERIFY (read-only — a saida vai COLADA no relatorio)
-- =============================================================
-- V1 · o CHECK existe e CONTEM o valor novo
--   select pg_get_constraintdef(oid) like '%manual_de_assistencia%' as tem_o_valor_novo
--     from pg_constraint where conname='normative_documents_doc_kind_check';
--   -- esperado: t
--
-- V2 · e continua contendo os 9 antigos (nenhum sumiu na reescrita)
--   select pg_get_constraintdef(oid) from pg_constraint
--    where conname='normative_documents_doc_kind_check';
--   -- conferir a olho E por maquina: os 10 valores, sem sobra e sem falta
--
-- V3 · 🔴 A LINHA DE CONTROLE do manifesto — o dado nao mudou debaixo de nos
--   select doc_kind, count(*) from normative_documents group by 1 order by 2 desc;
--   -- 📊 esperado em 17/09: condicoes_gerais 184 · manual_do_segurado 5 ·
--   --    circular_susep 5   (total 194)
--   -- ⚠️ nao bateu? PARE: alguem mexeu, e o manifesto esta desatualizado.
--
-- V4 · adversarial, em BEGIN … ROLLBACK:
--   (a) update de 1 linha para doc_kind='manual_de_assistencia' -> ACEITA
--   (b) update de 1 linha para doc_kind='chute'                 -> check_violation
--   -- (b) e a LINHA DE CONTROLE de (a): sem ela, (a) passar so provaria que
--   --     a constraint sumiu, nao que ela cresceu.
--
-- =============================================================
-- ROLLBACK — 🔴 COM GUARDA DE CONTAGEM, e ela NAO e opcional
-- =============================================================
-- PASSO 0 (obrigatorio, antes de qualquer coisa):
--   select count(*) from normative_documents where doc_kind='manual_de_assistencia';
--   -- 🔴 > 0  ->  NAO RODAR O ROLLBACK. Ele deixaria a tabela violando o
--   --            proprio CHECK: as linhas ficariam invalidas e qualquer
--   --            UPDATE futuro nelas passaria a falhar. Reclassificar essas
--   --            linhas ANTES (decisao de curadoria, nao de migration).
--   --    = 0  ->  seguro seguir.
--
-- begin;
-- alter table public.normative_documents
--     drop constraint if exists normative_documents_doc_kind_check;
-- alter table public.normative_documents
--     add constraint normative_documents_doc_kind_check
--     check (doc_kind = any (array[
--         'condicoes_gerais','condicoes_especiais','condicoes_particulares',
--         'manual_do_segurado','nota_tecnica','circular_susep',
--         'tabela_coberturas','glossario','regulamento']));
-- commit;
--   -- (os 9 valores acima sao os LIDOS DO CATALOGO no manifesto (1),
--   --  nao uma lista de memoria)
-- =============================================================
