-- =============================================================================
-- MIGRATION: spec_extra0016_redigir_output_preview
-- SPEC:      SPEC-EXTRA-001.6 — B4.4 "PII fora de routine_runs", a SEGUNDA coluna
-- AUTOR:     Claude Opus 5 (builder do CONSERTO, rodada 1)   DATA: 2026-09-14
-- OBJETIVO:  apagar o CPF/CNPJ e o telefone do segurado de
--            `routine_runs.output_preview` — a coluna que a TELA mostra hoje
--
-- APPLY:     um UPDATE de redação sobre uma LISTA DE IDS FIXADA (§ "O SELECT",
--            abaixo). As MESMAS duas substituições por regex da `_03`:
--            "CPF/CNPJ <dígitos>" e "WhatsApp: <dígitos>". Nenhuma coluna muda
--            de tipo, nenhuma linha é apagada, nenhuma estrutura é tocada.
-- VERIFY:    V0–V5, abaixo. SQL executável. 🔴 O V5 é o que faltou na `_03`.
-- ROLLBACK:  🔴 NÃO EXISTE. Mesma justificativa da `_03` — é irreversível POR
--            CONSTRUÇÃO, e o SELECT grava o `md5` de antes para provar QUAIS
--            linhas foram tocadas sem guardar o que havia nelas.
--
-- EXPAND-FIRST: não se aplica (não há estrutura nova)
-- DESTRUTIVA:   🔴 SIM — ALTERA DADO JÁ GRAVADO. Piso CRÍTICO do protocolo §3.2.
-- IDEMPOTENTE:  sim — rodar de novo é no-op: depois da 1ª passada não sobra
--               nenhum dígito depois de "CPF/CNPJ " nem de "WhatsApp: ", e as
--               duas regexes exigem um dígito para casar.
--
-- =============================================================================
-- 🔴 POR QUE ESTA MIGRATION EXISTE, SE A `_03` JÁ RODOU
-- =============================================================================
--
-- A `20260914_03` limpou `output_full`. Ela não olhou `output_preview`, e a
-- tela lê as DUAS:
--
--     backend/app/services/routine_engine.py:348    output_preview = output[:500]
--     app/dashboard/entregas/rotina/[runId]/page.tsx:140
--                                                   completo || output_preview
--
-- Ou seja: quando `output_full` é NULL, a tela mostra o PREVIEW. 📊 MEDIDO EM
-- 14/09/2026 pela lente do dado (projeto `dcajcvlzcjbmyapmklil`):
--
--     select count(*) from routine_runs r
--       join routines t on t.id = r.routine_id
--      where t.config->>'kind' = 'billing_collection'
--        and (r.output_preview ~ 'CPF/CNPJ[: ]*[0-9]'
--             or r.output_preview ~ 'WhatsApp: [0-9]');            -> 5
--
--     ... e destas, `output_full is null`:                         -> 4
--
-- 📊 Os 5 ids (8 primeiros caracteres, para não colar identificador inteiro em
--    documento): `ce166b0e`, `17dfd8a9`, `55eef75e`, `fddfe92d`, `89e1c389`.
--
-- 🔴 Quatro delas exibem PII de segurado EM CLARO na tela HOJE — a `_03` fechou
--    a porta da frente e deixou a dos fundos aberta. O defeito não é de execução
--    da `_03`: é de escopo. Por isso o V5 desta migration varre as DUAS colunas
--    juntas, que é a pergunta que ninguém tinha feito: *"sobrou PII de cobrança
--    em `routine_runs`, em QUALQUER coluna de texto?"*.
--
-- 🔴 E DAQUI PARA A FRENTE ELA NÃO REINFECTA — e isso foi CONFERIDO, não suposto:
--    `routine_engine.py:348` monta o preview com `output[:500]`, onde `output` é
--    o MESMO texto que `billing_collection._format_report` produz. A partir da
--    SPEC-EXTRA-001.6 aquele texto nasce com `_mascarar_documento` e
--    `_mascarar_telefone` (guarda G12, mutação M12). Não existe um segundo
--    escritor do preview: uma única linha o produz, a partir de uma única fonte.
--    Então mascarar na fonte cobre as duas colunas — e é por isso que esta
--    migration é de LIMPEZA HISTÓRICA, não de contenção contínua.
--
-- 🔴 A DECISÃO: IRREVERSÍVEL, E CORRETA (proposta §9 B4.4)
--    O dado apagado é PII de segurado que nunca deveria ter sido escrita num
--    relatório de execução: `routine_runs` é legível por qualquer sessão
--    autenticada da corretora, e um ROLLBACK só seria possível guardando o texto
--    original em algum lugar — ou seja, criando uma SEGUNDA cópia do vazamento
--    para poder desfazer a limpeza do primeiro. A mesma informação continua onde
--    ela tem dono: documento e telefone estão na InfoCap do cliente e o telefone
--    de destino está em `billing_sent_log.to_phone` (comentado como dado que não
--    sai dali).
--    Alternativa registrada e NÃO escolhida: deixar como está e abrir
--    `P-E0016-PII-LEGADA-NO-OUTPUT-PREVIEW` — custo de esquecer: "4 execuções
--    com CPF/CNPJ de segurado em claro NA TELA, hoje".
--
-- 🔴 O SELECT — A LISTA DE IDS É FIXADA ANTES, NUNCA UM `where ~` ABERTO
--    Um `update ... where output_preview ~ '...'` cresce sozinho: entre o momento
--    em que alguém leu "são 5" e o momento em que o UPDATE roda, a rotina pode
--    ter executado de novo, e o número afetado deixa de ser o número medido — o
--    VERIFY passa a conferir uma afirmação que ninguém fez.
--    Rode ESTE select, cole os ids no lugar do marcador, e só então o APPLY:
--
--      select r.id,
--             md5(r.output_preview)    as md5_antes,
--             length(r.output_preview) as tamanho_antes,
--             r.started_at::date       as dia
--        from public.routine_runs r
--        join public.routines t on t.id = r.routine_id
--       where t.config->>'kind' = 'billing_collection'
--         and (r.output_preview ~ 'CPF/CNPJ[: ]*[0-9]'
--              or r.output_preview ~ 'WhatsApp: [0-9]')
--       order by r.started_at;
--
--    ⚠️ `routine_runs` NÃO tem `created_at` — a ordenação é por `started_at`
--       (a `_03` descobriu isso na hora; está escrito aqui para ninguém
--       redescobrir).
--    ⚠️ O `md5_antes` e o `tamanho_antes` vão COLADOS NO RELATÓRIO da SPEC. É o
--       que substitui o ROLLBACK: não devolve o texto, mas prova exatamente
--       quais linhas foram tocadas e que nenhuma outra foi.
--    ⛔ NUNCA colar no relatório o `output_preview` em si: ele é o vazamento.
-- =============================================================================

-- ----------------------------------------------------------------- APPLY -----
begin;

-- 🔴 As duas regexes são as MESMAS da `_03`, byte a byte, e por isso mesmo:
--
--   (CPF/CNPJ[: ]*)      o rótulo, capturado para voltar intacto em \1.
--                        `[: ]*` porque o texto histórico tem "CPF/CNPJ 0001"
--                        (espaço) e o de outras versões tem "CPF/CNPJ: 0001".
--   [0-9][0-9./-]{9,17}  começa por DÍGITO (senão casaria "CPF/CNPJ ...0272",
--                        o formato NOVO, já mascarado, e a migration deixaria
--                        de ser idempotente) e segue por 9 a 17 caracteres de
--                        dígito ou pontuação — cobre CPF cru (11), CPF pontuado
--                        (14), CNPJ cru (14) e CNPJ pontuado (18).
--   (WhatsApp: )         o rótulo do telefone.
--   [0-9]{8,15}          8 a 15 dígitos: telefone com ou sem DDD, com ou sem 55.
--                        ⚠️ Exige dígito, então `WhatsApp: sem telefone (nao
--                        encontrado)` NÃO é tocado — e o V3 prova isso.
--
-- ⚠️ `output_preview` é `output[:500]`: o corte pode cair NO MEIO de um número.
--    `{9,17}` e `{8,15}` são faixas, não tamanhos fixos, então um documento
--    truncado em 10 dígitos continua casando. Um truncado em 8 ou menos NÃO
--    casa — e o V1/V2 abaixo o mostrariam como sobra, em vez de escondê-lo.
--
-- ⚠️ Postgres: `.` em regex NÃO casa quebra de linha só com a flag `n`; aqui
--    nenhuma classe usa `.` como coringa, então o dialeto não muda o resultado
--    (CLAUDE.md §9.4 — "um padrão medido com um motor e aplicado com outro é um
--    padrão sobre outra coisa").

update public.routine_runs
   set output_preview = regexp_replace(
                          regexp_replace(output_preview,
                                         '(CPF/CNPJ[: ]*)[0-9][0-9./-]{9,17}', '\1•••', 'g'),
                          '(WhatsApp: )[0-9]{8,15}', '\1•••', 'g')
 where id in (<<IDS_FIXADOS_PELO_SELECT>>)
   and output_preview is not null;

commit;

-- ---------------------------------------------------------------- VERIFY -----
-- V0 · o estado final da coluna que esta migration trata.
--      Esperado: 0. (📊 eram 5 em 14/09/2026.)
select count(*) as preview_ainda_com_pii
  from public.routine_runs r
  join public.routines t on t.id = r.routine_id
 where t.config->>'kind' = 'billing_collection'
   and (r.output_preview ~ 'CPF/CNPJ[: ]*[0-9]' or r.output_preview ~ 'WhatsApp: [0-9]');
-- esperado: 0

-- V1 · nenhum preview com dígito de documento depois do rótulo.
select count(*) as preview_com_documento
  from public.routine_runs r
  join public.routines t on t.id = r.routine_id
 where t.config->>'kind' = 'billing_collection'
   and r.output_preview ~ 'CPF/CNPJ[: ]*[0-9]';
-- esperado: 0

-- V2 · nenhum com telefone.
select count(*) as preview_com_telefone
  from public.routine_runs r
  join public.routines t on t.id = r.routine_id
 where t.config->>'kind' = 'billing_collection'
   and r.output_preview ~ 'WhatsApp: [0-9]';
-- esperado: 0

-- V3 · 🔴 O CONTROLE: `WhatsApp: sem telefone (...)` NÃO foi tocado. Sem esta
--      linha, uma regex boa demais que apagasse a explicação passaria verde nos
--      V1/V2 — e a atendente perderia POR QUE aquele segurado não tem contato.
select count(*) as explicacoes_intactas
  from public.routine_runs r
  join public.routines t on t.id = r.routine_id
 where t.config->>'kind' = 'billing_collection'
   and r.output_preview like '%WhatsApp: sem telefone%';
-- esperado: >= 1

-- V4 · 🔴 O SEGUNDO CONTROLE: a redação NÃO comeu o preview. O texto continua
--      lá, com a seção e o rótulo — só sem os números.
select count(*) as previews_inteiros
  from public.routine_runs r
  join public.routines t on t.id = r.routine_id
 where t.config->>'kind' = 'billing_collection'
   and r.output_preview like '%CPF/CNPJ%';
-- esperado: o MESMO número que o SELECT de fixação contou (📊 5 em 14/09)

-- V5 · 🔴 O V QUE FALTOU NA `_03`: as DUAS colunas, na mesma pergunta.
--      A `_03` provou que `output_full` estava limpa e ninguém perguntou pela
--      outra — e era a outra que a tela mostrava. Este VERIFY é a pergunta certa:
--      sobrou PII de cobrança em `routine_runs`, em QUALQUER coluna de texto?
--      Ele fica aqui para a próxima pessoa: rodar SÓ ele já responde.
select count(*) as linhas_com_pii_em_qualquer_coluna
  from public.routine_runs r
  join public.routines t on t.id = r.routine_id
 where t.config->>'kind' = 'billing_collection'
   and (   r.output_full    ~ 'CPF/CNPJ[: ]*[0-9]'
        or r.output_full    ~ 'WhatsApp: [0-9]'
        or r.output_preview ~ 'CPF/CNPJ[: ]*[0-9]'
        or r.output_preview ~ 'WhatsApp: [0-9]');
-- esperado: 0

-- -------------------------------------------------------------- ROLLBACK -----
-- 🔴 NÃO EXISTE, e isso está escrito ANTES de aplicar (MIGRATIONS-AUTHORITY §7).
--
-- Desfazer exigiria ter guardado o texto original — isto é, manter uma segunda
-- cópia do CPF do segurado dentro do banco para poder restaurar a primeira. O
-- gesto que "protege" seria o próprio vazamento, com uma cópia a mais.
--
-- O que substitui o rollback:
--   · o `md5(output_preview)` e o `length(output_preview)` de ANTES, colhidos
--     pelo SELECT lá em cima e colados no relatório da SPEC — provam QUAIS
--     linhas mudaram e que nenhuma outra mudou;
--   · a informação em si não se perde: documento e telefone do segurado
--     continuam na InfoCap do cliente, e o telefone de destino continua em
--     `billing_sent_log.to_phone`.
--
-- ⚠️ Se o UPDATE afetar um número DIFERENTE do medido, a resposta NÃO é rodar
--    de novo: é parar, remedir com o SELECT e refazer a lista de ids. Um
--    `rollback` da transação antes do `commit` ainda é possível — depois do
--    `commit`, não.
