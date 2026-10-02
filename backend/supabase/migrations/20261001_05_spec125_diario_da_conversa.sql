-- =============================================================
-- MIGRATION: 20261001_05_spec125_diario_da_conversa
-- SPEC:      SPEC-125 — S6 · o diário da conversa (só os momentos de julgamento) + o placar
-- AUTOR:     builder S6 (Opus 5.5 xhigh)      DATA: 2026-10-01
-- OBJETIVO:  o diário de decisões (SPEC-123 F4) passa a registrar também os JULGAMENTOS do
--            agente de ATENDIMENTO (conversa com o segurado) e a guardar a fala/tela COMPLETA
--            para a corretora dona ler (ordem do Founder, 01/10: "o diário pode vir completo").
--
-- APPLY:     · `ck_diario_acao` ganha `respondeu_segurado` (os 5 valores de hoje FICAM);
--            · `ck_diario_resultado` ganha os sinais de ERRO LEVE que fecham a linha sozinhos:
--              `segurado_corrigiu` · `segurado_repetiu` · `segurado_pediu_pessoa` ·
--              `agente_repetiu_pergunta` (o fiscal da repetição disparou) — os 5 de hoje FICAM;
--            · coluna `momento` (o tipo de julgamento da conversa, D7) com CHECK de lista
--              fechada, e só em linha `origem='atendimento'`;
--            · colunas `tela_completa` e `valor_completo` (texto SEM máscara, nulas) — lidas só
--              pela corretora dona (filtro no código) e pelo master. A mascarada CONTINUA sendo
--              a que vai para log, evento, bancada e carta.
-- VERIFY:    o bloco VERIFY no fim deste arquivo (V1 catálogo · V2 adversarial num DO que
--            termina em `raise exception` — nada fica gravado · V3 contagem).
-- ROLLBACK:  o bloco ROLLBACK no fim deste arquivo (recusa rodar se algum valor novo já estiver
--            em uso — reverter deixaria linha inválida).
--
-- EXPAND-FIRST: sim  (as listas só CRESCEM; as colunas novas são nulas; nenhuma linha muda)
-- DESTRUTIVA:   não  (📊 a tabela tem 0 linhas em 01/10/2026 — `select count(*) from
--               diario_de_decisoes` → 0; o DROP+ADD dos CHECKs roda na MESMA transação do
--               `apply_migration`, então não há janela sem trava)
-- =============================================================
--
-- 📊 OS CHECKs DE HOJE (pg_get_constraintdef, 01/10/2026):
--    ck_diario_acao      = respondeu_ura · perguntou_segurado · chamou_pessoa · nao_agiu · respondeu_portal
--    ck_diario_resultado = pendente · protocolo_saiu · seguradora_recusou · humano_corrigiu · ura_fechou
--
-- 🔴 POR QUE `momento` É COLUNA E NÃO OUTRA `classe`:
--    as 5 classes são a POLÍTICA do destravador (o que o código deixa fazer sozinho). O momento
--    da conversa é OUTRA pergunta — "que tipo de julgamento foi este?" —, e "não chamou pessoa
--    onde a regra antiga chamaria" não é nenhuma das 5. Pôr na classe faria o nome mentir sobre
--    o que guarda (CLAUDE.md §12.1).
--
-- 🔴 POR QUE A COLUNA COMPLETA É SEPARADA DA MASCARADA:
--    a mascarada alimenta a bancada (`diario_para_bancada.py` → corpus no repositório), a carta
--    (`propor_carta_sync` → acervo GLOBAL de todas as corretoras) e a linha do tempo. A completa
--    só existe para a tela da corretora dona. Uma coluna por destino: ninguém pede a errada por engano.

alter table public.diario_de_decisoes drop constraint if exists ck_diario_acao;
alter table public.diario_de_decisoes add constraint ck_diario_acao
  check (acao in ('respondeu_ura', 'perguntou_segurado', 'chamou_pessoa', 'nao_agiu',
                  'respondeu_portal', 'respondeu_segurado'));

alter table public.diario_de_decisoes drop constraint if exists ck_diario_resultado;
alter table public.diario_de_decisoes add constraint ck_diario_resultado
  check (resultado in ('pendente', 'protocolo_saiu', 'seguradora_recusou', 'humano_corrigiu',
                       'ura_fechou', 'segurado_corrigiu', 'segurado_repetiu',
                       'segurado_pediu_pessoa', 'agente_repetiu_pergunta'));

alter table public.diario_de_decisoes add column if not exists momento text;
alter table public.diario_de_decisoes add column if not exists tela_completa text;
alter table public.diario_de_decisoes add column if not exists valor_completo text;

alter table public.diario_de_decisoes drop constraint if exists ck_diario_momento;
alter table public.diario_de_decisoes add constraint ck_diario_momento
  check (momento is null or momento in ('deduziu', 'respondeu_regra', 'nao_chamou_pessoa', 'chamou_pessoa'));
alter table public.diario_de_decisoes drop constraint if exists ck_diario_momento_e_da_conversa;
alter table public.diario_de_decisoes add constraint ck_diario_momento_e_da_conversa
  check (momento is null or origem = 'atendimento');

comment on constraint ck_diario_acao on public.diario_de_decisoes is
  'SPEC-123 F4 + SPEC-124 F1 + SPEC-125 S6: respondeu_ura · respondeu_portal · respondeu_segurado (o agente de atendimento respondeu sozinho ao segurado) · perguntou_segurado · chamou_pessoa · nao_agiu (sombra).';
comment on constraint ck_diario_resultado on public.diario_de_decisoes is
  'SPEC-123 F4 + SPEC-125 S6: o que aconteceu depois. Os 4 sinais de ERRO LEVE da conversa fecham a linha sozinhos (diario_de_decisoes.fechar_como_erro_leve): segurado_corrigiu · segurado_repetiu · segurado_pediu_pessoa · agente_repetiu_pergunta.';
comment on column public.diario_de_decisoes.momento is
  'SPEC-125 D7 — o tipo de julgamento do agente de atendimento: deduziu (um dado sem perguntar) · respondeu_regra (dúvida de cobertura/regra sem pessoa) · nao_chamou_pessoa (onde a regra antiga chamaria) · chamou_pessoa. Nulo nas linhas do acionamento/portal.';
comment on column public.diario_de_decisoes.tela_completa is
  'SPEC-125 S6 — a tela/fala COMPLETA, sem máscara (ordem do Founder 01/10). Lida SÓ pela corretora dona (filtro company_id no código) e pelo master. ⛔ Nunca vai a log, evento, bancada ou carta: para isso existe tela_mascarada.';
comment on column public.diario_de_decisoes.valor_completo is
  'SPEC-125 S6 — o que o agente respondeu/deduziu, sem máscara. Mesmas regras de tela_completa.';

-- =============================================================
-- VERIFY  (rodar DEPOIS do APPLY)
-- =============================================================
-- V1) catálogo:
-- select (select pg_get_constraintdef(oid) from pg_constraint where conname='ck_diario_acao') acao,
--        (select pg_get_constraintdef(oid) from pg_constraint where conname='ck_diario_resultado') resultado,
--        (select count(*) from pg_constraint where conrelid='public.diario_de_decisoes'::regclass and contype='c') checks,
--        (select string_agg(column_name||':'||data_type||':'||is_nullable, ',' order by column_name)
--           from information_schema.columns where table_schema='public' and table_name='diario_de_decisoes'
--            and column_name in ('momento','tela_completa','valor_completo')) cols,
--        (select count(*) from public.diario_de_decisoes) linhas;
--   → acao com os 6 · resultado com os 9 · checks=18 · 3 colunas text nulas · linhas=0
--
-- V2) ADVERSARIAL — os valores novos são ACEITOS (controle), os antigos CONTINUAM aceitos, e
--     cada trava nova CONSEGUE recusar. Termina em `raise exception`: NADA fica.
--   📊 rodado em 01/10/2026 (MCP execute_sql; DO com 13 inserts, cada um num sub-bloco). O erro É o placar:
--   VERIFY_PLACAR acao_nova=aceita;acao_antiga_portal=aceita;resultado_corrigiu=aceita;resultado_repetiu=aceita;
--   resultado_pediu=aceita;resultado_fiscal=aceita;resultado_antigo=aceita;momento_e_completa=aceita;
--   acao_inventada=ok(ck_diario_acao);resultado_inventado=ok(ck_diario_resultado);momento_inventado=ok(ck_diario_momento);
--   momento_no_acionamento=ok(ck_diario_momento_e_da_conversa);sombra_que_respondeu=ok(ck_diario_sombra_nao_agiu);
--   (8 controles aceitos — os novos E os antigos —, 5 recusas, cada uma pela SUA constraint)
--   V1 rodado: acao com 6 · resultado com 9 · checks=18 · momento/tela_completa/valor_completo text nulas · linhas=0 ·
--   versão 20261001221925 spec125_diario_da_conversa
--
-- V3) select count(*) from public.diario_de_decisoes;  → 0

-- =============================================================
-- ROLLBACK
-- =============================================================
-- do $$ begin
--   if exists (select 1 from public.diario_de_decisoes
--               where acao = 'respondeu_segurado' or momento is not null
--                  or resultado in ('segurado_corrigiu','segurado_repetiu','segurado_pediu_pessoa','agente_repetiu_pergunta')
--                  or tela_completa is not null or valor_completo is not null) then
--     raise exception 'ROLLBACK recusado: o diário já usa os valores/colunas da SPEC-125';
--   end if;
-- end $$;
-- alter table public.diario_de_decisoes drop constraint if exists ck_diario_momento_e_da_conversa;
-- alter table public.diario_de_decisoes drop constraint if exists ck_diario_momento;
-- alter table public.diario_de_decisoes drop column if exists valor_completo;
-- alter table public.diario_de_decisoes drop column if exists tela_completa;
-- alter table public.diario_de_decisoes drop column if exists momento;
-- alter table public.diario_de_decisoes drop constraint if exists ck_diario_resultado;
-- alter table public.diario_de_decisoes add constraint ck_diario_resultado
--   check (resultado in ('pendente','protocolo_saiu','seguradora_recusou','humano_corrigiu','ura_fechou'));
-- alter table public.diario_de_decisoes drop constraint if exists ck_diario_acao;
-- alter table public.diario_de_decisoes add constraint ck_diario_acao
--   check (acao in ('respondeu_ura','perguntou_segurado','chamou_pessoa','nao_agiu','respondeu_portal'));
