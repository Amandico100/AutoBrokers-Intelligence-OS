-- =============================================================================
-- MIGRATION: spec_extra0016_redigir_output_full
-- SPEC:      SPEC-EXTRA-001.6 — B4.4 "PII fora de routine_runs.output_full"
-- AUTOR:     Claude Opus 5 (builder B4)            DATA: 2026-09-14
-- OBJETIVO:  apagar o CPF/CNPJ e o telefone do segurado dos relatórios de
--            execução da cobrança que JÁ estão gravados
--
-- APPLY:     um UPDATE de redação sobre uma LISTA DE IDS FIXADA (§ "O SELECT",
--            abaixo). Duas substituições por regex: "CPF/CNPJ <dígitos>" e
--            "WhatsApp: <dígitos>". Nenhuma coluna muda de tipo, nenhuma linha
--            é apagada, nenhuma estrutura é tocada.
-- VERIFY:    V0–V4, abaixo. SQL executável.
-- ROLLBACK:  🔴 NÃO EXISTE. Ver "A DECISÃO", abaixo — é irreversível POR
--            CONSTRUÇÃO, e o APPLY grava o `md5` de antes para provar QUAIS
--            linhas foram tocadas sem guardar o que havia nelas.
--
-- EXPAND-FIRST: não se aplica (não há estrutura nova)
-- DESTRUTIVA:   🔴 SIM — ALTERA DADO JÁ GRAVADO. Piso CRÍTICO do protocolo §3.2.
-- IDEMPOTENTE:  sim — rodar de novo é no-op: depois da 1ª passada não sobra
--               nenhum dígito depois de "CPF/CNPJ " nem de "WhatsApp: ", e as
--               duas regexes exigem um dígito para casar.
--
-- 📊 MEDIDO EM 13/09/2026, antes de uma linha de SQL (relatório da SPEC §1,
--    premissas 11 e 15, projeto `dcajcvlzcjbmyapmklil`):
--
--      select count(*) from routine_runs r
--        join routines t on t.id = r.routine_id
--       where t.config->>'kind' = 'billing_collection'
--         and r.output_full like '%CPF/CNPJ%';                          -> 7 de 49
--
--      ... and r.output_full ~ 'CPF/CNPJ[: ]+[0-9]';                    -> 6
--
--    Ou seja: 7 relatórios de execução com a seção "Clientes encontrados", 6
--    deles com dígitos de documento de segurado em claro. 📊 Dentro de cada um,
--    6 de 7 itens trazem documento (86%) e os 7 itens são OS MESMOS nos dois
--    dias — o mesmo segurado, repetido.
--
-- 🔴 QUEM ESCREVEU ISSO, E POR QUE PAROU DE ESCREVER
--    `billing_collection._format_report`, na seção "Clientes encontrados",
--    montava a linha com `item['cpf_cnpj']` e `item['whatsapp']` inteiros, e
--    `routine_engine` gravava o texto em `routine_runs.output_full`. A partir
--    desta SPEC ela grava `...0272` e `...0002` (`_mascarar_documento` e
--    `_mascarar_telefone`, guarda G12 com a mutação M12). Mascarar daqui para a
--    frente NÃO apaga o que já está lá — e é só por isso que esta migration
--    existe.
--
-- 🔴 A DECISÃO: IRREVERSÍVEL, E CORRETA (proposta §9 B4.4)
--    O dado apagado é PII de segurado que nunca deveria ter sido escrita num
--    relatório de execução: `routine_runs.output_full` é legível por qualquer
--    sessão autenticada da corretora, e um ROLLBACK só seria possível guardando
--    o texto original em algum lugar — ou seja, criando uma SEGUNDA cópia do
--    vazamento para poder desfazer a limpeza do primeiro. A mesma informação
--    continua existindo onde ela tem dono: o documento e o telefone estão na
--    InfoCap do cliente e o telefone de destino está em `billing_sent_log.
--    to_phone` (comentado como dado que não sai dali).
--    Alternativa registrada e NÃO escolhida: deixar como está e abrir
--    `P-E0016-PII-LEGADA-NO-OUTPUT-FULL` — custo de esquecer escrito na
--    proposta: "7 relatórios com CPF/CNPJ de segurado em claro, legíveis por
--    qualquer sessão autenticada da corretora".
--
-- 🔴 O SELECT — A LISTA DE IDS É FIXADA ANTES, NUNCA UM `where like` ABERTO
--    Um `update ... where output_full like '%CPF/CNPJ%'` cresce sozinho: entre
--    o momento em que alguém leu "são 7" e o momento em que o UPDATE roda, a
--    rotina pode ter executado de novo, e o número afetado deixa de ser o
--    número medido — o VERIFY passa a conferir uma afirmação que ninguém fez.
--    Rode ESTE select, cole os ids no lugar do marcador, e só então o APPLY:
--
--      select r.id,
--             md5(r.output_full)   as md5_antes,
--             length(r.output_full) as tamanho_antes,
--             r.started_at
--        from public.routine_runs r
--        join public.routines t on t.id = r.routine_id
--       where t.config->>'kind' = 'billing_collection'
--         and (r.output_full ~ 'CPF/CNPJ[: ]*[0-9]'
--              or r.output_full ~ 'WhatsApp: [0-9]')
--       order by r.started_at;
--
--    ⚠️ O `md5_antes` e o `tamanho_antes` vão COLADOS NO RELATÓRIO da SPEC. É o
--    que substitui o ROLLBACK: não devolve o texto, mas prova exatamente quais
--    linhas foram tocadas e que nenhuma outra foi.
--    ⛔ NUNCA colar no relatório o `output_full` em si: ele é o vazamento.
-- =============================================================================

-- ----------------------------------------------------------------- APPLY -----
begin;

-- 🔴 As duas regexes, e o que cada peça faz:
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
-- ⚠️ Postgres: `.` em regex NÃO casa quebra de linha só com a flag `n`; aqui
--    nenhuma classe usa `.` como coringa, então o dialeto não muda o resultado
--    (CLAUDE.md §9.4 — "um padrão medido com um motor e aplicado com outro é um
--    padrão sobre outra coisa").

update public.routine_runs
   set output_full = regexp_replace(
                       regexp_replace(output_full,
                                      '(CPF/CNPJ[: ]*)[0-9][0-9./-]{9,17}', '\1•••', 'g'),
                       '(WhatsApp: )[0-9]{8,15}', '\1•••', 'g')
 where id in (<<IDS_FIXADOS_PELO_SELECT>>)
   and output_full is not null;

commit;

-- ---------------------------------------------------------------- VERIFY -----
-- V0 · quantas linhas o UPDATE afetou. Esperado: N = a contagem do SELECT acima
--      (📊 7 em 13/09/2026, das quais 6 com dígitos de documento).
--      O `UPDATE N` do psql/MCP já responde; esta linha confere o estado final.
select count(*) as ainda_com_pii
  from public.routine_runs r
  join public.routines t on t.id = r.routine_id
 where t.config->>'kind' = 'billing_collection'
   and (r.output_full ~ 'CPF/CNPJ[: ]*[0-9]' or r.output_full ~ 'WhatsApp: [0-9]');
-- esperado: 0

-- V1 · nenhum relatório de cobrança com dígito de documento depois do rótulo.
select count(*) as com_documento
  from public.routine_runs r
  join public.routines t on t.id = r.routine_id
 where t.config->>'kind' = 'billing_collection'
   and r.output_full ~ 'CPF/CNPJ[: ]*[0-9]';
-- esperado: 0

-- V2 · nenhum com telefone.
select count(*) as com_telefone
  from public.routine_runs r
  join public.routines t on t.id = r.routine_id
 where t.config->>'kind' = 'billing_collection'
   and r.output_full ~ 'WhatsApp: [0-9]';
-- esperado: 0

-- V3 · 🔴 O CONTROLE: `WhatsApp: sem telefone (...)` NÃO foi tocado. Sem esta
--      linha, uma regex boa demais que apagasse a explicação passaria verde nos
--      V1/V2 — e a atendente perderia POR QUE aquele segurado não tem contato.
select count(*) as explicacoes_intactas
  from public.routine_runs r
  join public.routines t on t.id = r.routine_id
 where t.config->>'kind' = 'billing_collection'
   and r.output_full like '%WhatsApp: sem telefone%';
-- esperado: >= 1 (📊 6 de 7 itens por dia têm documento; 2 dos 7 não têm telefone)

-- V4 · 🔴 O SEGUNDO CONTROLE: a redação NÃO comeu o relatório. O texto continua
--      lá, com a seção e o nome do cliente — só sem os números.
select count(*) as relatorios_inteiros
  from public.routine_runs r
  join public.routines t on t.id = r.routine_id
 where t.config->>'kind' = 'billing_collection'
   and r.output_full like '%Clientes encontrados:%'
   and r.output_full like '%CPF/CNPJ%';
-- esperado: 7 (as mesmas 7 linhas, com a seção e o rótulo intactos)

-- -------------------------------------------------------------- ROLLBACK -----
-- 🔴 NÃO EXISTE, e isso está escrito ANTES de aplicar (MIGRATIONS-AUTHORITY §7).
--
-- Desfazer exigiria ter guardado o texto original — isto é, manter uma segunda
-- cópia do CPF do segurado dentro do banco para poder restaurar a primeira. O
-- gesto que "protege" seria o próprio vazamento, com uma cópia a mais.
--
-- O que substitui o rollback:
--   · o `md5(output_full)` e o `length(output_full)` de ANTES, colhidos pelo
--     SELECT lá em cima e colados no relatório da SPEC — provam QUAIS linhas
--     mudaram e que nenhuma outra mudou;
--   · a informação em si não se perde: documento e telefone do segurado
--     continuam na InfoCap do cliente, e o telefone de destino continua em
--     `billing_sent_log.to_phone`.
--
-- ⚠️ Se o UPDATE afetar um número DIFERENTE do medido, a resposta NÃO é rodar
--    de novo: é parar, remedir com o SELECT e refazer a lista de ids. Um
--    `rollback` da transação antes do `commit` ainda é possível — depois do
--    `commit`, não.
