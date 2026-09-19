-- =============================================================
-- MIGRATION: o motivo do rascunho fica GRAVADO, no plano e no servico
-- SPEC:      SPEC-EXTRA-001.5.1 — unidade B (D8), fatia 2
-- AUTOR:     builder Opus 5 xhigh (AAA FAST v12.2)      DATA: 2026-09-19
-- OBJETIVO:  quem abre a fila de curadoria consegue ler POR QUE um plano (ou um
--            servico) foi recusado — hoje o motivo so existe no log do processo
--            que o recusou, e o log ja nao esta mais la.
--
-- APPLY:     `ADD COLUMN IF NOT EXISTS motivo_do_rascunho text` nas duas tabelas
--            da base de planos, + um backfill idempotente que COPIA para a
--            coluna nova o motivo que o verificador escreveu em `condicao` com
--            o prefixo `[reprovado] ` (8 linhas medidas). Nada e apagado,
--            nada muda de estado, nenhuma trava e tocada.
-- VERIFY:    a secao VERIFY no fim deste arquivo (so SELECT).
-- ROLLBACK:  -- 🔴 a coluna guarda a UNICA copia do motivo dos 5 planos
--            --    (o log que o continha nao existe mais). Exportar antes:
--            --    select id, motivo_do_rascunho from public.insurer_assistance_plans
--            --     where motivo_do_rascunho is not null;
--            --    select id, motivo_do_rascunho from public.insurer_assistance_services
--            --     where motivo_do_rascunho is not null;
--            alter table public.insurer_assistance_plans    drop column if exists motivo_do_rascunho;
--            alter table public.insurer_assistance_services drop column if exists motivo_do_rascunho;
--            -- ⚠️ Nos SERVICOS o rollback nao perde nada: o backfill so COPIOU
--            --    o que continua em `condicao`. Nos PLANOS perde — e por isso
--            --    a exportacao acima vem antes, nao depois.
--
-- EXPAND-FIRST: sim — so adiciona. Nenhum DROP, nenhum ALTER de tipo, nenhum
--               estado de curadoria alterado por esta migration.
-- DESTRUTIVA:   nao
--
-- =============================================================
-- 📊 AS MEDICOES QUE DECIDIRAM ESTE DDL (19/09/2026, banco de producao, so
--    SELECT — cada uma com o comando ao lado, protocolo §0.4)
--
-- MEDICAO 1 · NAO HA CAMPO RAZOAVEL PARA REUSAR NO PLANO
--    select column_name, data_type from information_schema.columns
--     where table_name = 'insurer_assistance_plans' order by ordinal_position;
--    -> id · insurer_key · ramo · produto · plano · nivel · vigencia_inicio ·
--       vigencia_fim · susep_process · documento_id · pagina · confianca ·
--       curadoria · revisado_por · revisado_em · content_hash · created_at ·
--       updated_at
--    🔴 Todas as 18 tem significado proprio. Escrever o motivo em
--    `susep_process` ou em `content_hash` seria exatamente o defeito que o
--    CLAUDE.md §12.1 manda consertar — "se o nome do campo mente sobre o que
--    ele guarda, conserte o CAMPO" —, so que introduzido de proposito.
--    Decisao, com nota (protocolo §9): migration aditiva **88** ·
--    reusar campo existente **35** (mente para todo leitor seguinte) ·
--    nao gravar o motivo **20** (D8 nao fecha; o proximo revisor pergunta de novo).
--
-- MEDICAO 2 · O QUE EXISTE PARA MIGRAR
--    select curadoria, count(*) from public.insurer_assistance_plans group by 1;
--    -> proposto 33 · rascunho 5
--    select curadoria, count(*) from public.insurer_assistance_services group by 1;
--    -> proposto 73 · rascunho 8
--    select count(*) from public.insurer_assistance_services
--     where curadoria='rascunho' and condicao like '[reprovado]%';
--    -> 8    (o verificador escreve o motivo em `condicao`, sobrescrevendo-a)
--    select count(*) from public.insurer_assistance_plans
--     where curadoria='rascunho';   -- 5, e NENHUM tem motivo em lugar nenhum:
--    `plano_para_rascunho` so fazia `logger.info(...)`.
--
-- MEDICAO 3 · POR QUE OS SERVICOS TAMBEM GANHAM A COLUNA
--    `condicao` e a CONDICAO CONTRATUAL da cobertura ("danos causados por
--    acidente de origem externa, desde que facam parte do projeto original do
--    condominio" — linha fe94f9a5, medida hoje). `para_rascunho` sobrescrevia
--    esse texto com `[reprovado] <motivo>`: o motivo entrava e a condicao
--    contratual sumia, sem copia. Com a coluna propria, o motivo tem lugar e a
--    condicao sobrevive. O backfill abaixo COPIA (nunca move) o que ja foi
--    escrito, para que a leitura passe a ter uma fonte so.
-- =============================================================

begin;

alter table public.insurer_assistance_plans
  add column if not exists motivo_do_rascunho text;

comment on column public.insurer_assistance_plans.motivo_do_rascunho is
  'Por que este plano foi recusado para `rascunho`. Escrito por '
  'assistance_plans_base.plano_para_rascunho. Ate 19/09/2026 o motivo so '
  'existia no log do processo (SPEC-EXTRA-001.5.1, D8).';

alter table public.insurer_assistance_services
  add column if not exists motivo_do_rascunho text;

comment on column public.insurer_assistance_services.motivo_do_rascunho is
  'Por que esta linha foi recusada para `rascunho`. Escrito por '
  'assistance_plans_base.para_rascunho. ⚠️ NAO confundir com `condicao`, que e '
  'a condicao CONTRATUAL da cobertura (SPEC-EXTRA-001.5.1, D8).';

-- Backfill idempotente: so preenche o que esta vazio, e so o que tem a marca
-- que o verificador deixou. Rodar de novo nao toca em nada.
update public.insurer_assistance_services
   set motivo_do_rascunho = btrim(substring(condicao from 13))
 where motivo_do_rascunho is null
   and condicao like '[reprovado]%'
   and btrim(substring(condicao from 13)) <> '';

commit;

-- =============================================================
-- VERIFY — so SELECT. Rodar DEPOIS do commit.
-- =============================================================
-- V1 · as duas colunas existem, e sao `text`
--   select table_name, column_name, data_type, is_nullable
--     from information_schema.columns
--    where column_name = 'motivo_do_rascunho'
--    order by table_name;
--   ESPERADO: 2 linhas · insurer_assistance_plans · insurer_assistance_services
--             · text · YES
--
-- V2 · o backfill dos servicos pegou as 8, e NENHUMA ficou com o prefixo
--   select count(*) filter (where motivo_do_rascunho is not null)  as com_motivo,
--          count(*) filter (where motivo_do_rascunho like '[reprovado]%') as com_prefixo
--     from public.insurer_assistance_services where curadoria = 'rascunho';
--   ESPERADO: com_motivo = 8 · com_prefixo = 0
--
-- V3 · 🔴 CONTROLE — a condicao contratual NAO foi tocada pelo backfill
--   select count(*) from public.insurer_assistance_services
--    where condicao like '[reprovado]%';
--   ESPERADO: 8 — o backfill COPIA, nao move. Se der 0, alguem apagou `condicao`
--   e esta migration fez mais do que declarou.
--
-- V4 · 🔴 CONTROLE do estado — nenhuma linha mudou de curadoria
--   select curadoria, count(*) from public.insurer_assistance_plans group by 1
--   union all
--   select 'srv:' || curadoria, count(*) from public.insurer_assistance_services group by 1;
--   ESPERADO: proposto 33 · rascunho 5 · srv:proposto 73 · srv:rascunho 8
--   (identico a MEDICAO 2 — esta migration e DDL + copia, nunca curadoria)
--
-- V5 · nada publicado apareceu de lado nenhum
--   select count(*) from public.insurer_assistance_services where curadoria='publicado';
--   ESPERADO: 0
-- =============================================================
