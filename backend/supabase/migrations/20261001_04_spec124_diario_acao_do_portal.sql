-- MIGRATION: 20261001_04_spec124_diario_acao_do_portal
-- SPEC:      SPEC-124 F1 (D1/D5: a MESMA política do destravador no portal de vidros, com o MESMO diário)
-- AUTOR:     builder F1 da SPEC-124 (Opus 5.5), 01/10/2026
-- OBJETIVO:  o diário (`public.diario_de_decisoes`, SPEC-123 F4) passa a aceitar `acao = 'respondeu_portal'` —
--            a decisão do destravador que CONTINUOU o pedido do portal de vidros com um dado do caso (a resposta
--            foi ao portal, não à URA). `origem = 'portal'` já existia (ck_diario_origem). Nada mais muda.
--
-- 📊 ANTES (01/10/2026, MCP execute_sql):
--   pg_get_constraintdef(ck_diario_acao) = CHECK ((acao = ANY (ARRAY['respondeu_ura','perguntou_segurado',
--                                                 'chamou_pessoa','nao_agiu'])))
--   ck_diario_sombra_nao_agiu continua valendo: em sombra a linha é sempre `nao_agiu`.
--
-- EXPAND-FIRST: a lista NOVA é um SUPERCONJUNTO da antiga — toda linha que o CHECK antigo aceitava, o novo aceita.
--               Drop + add na MESMA transação (a migration roda numa transação só): não há janela sem CHECK.
-- DESTRUTIVA:   não (nenhum dado muda; nenhuma coluna; nenhuma policy; nenhum GRANT).
--
-- APPLY:     o bloco abaixo (idempotente: `drop constraint if exists` + `add`).
-- VERIFY:    1) select pg_get_constraintdef(oid) from pg_constraint
--                 where conrelid='public.diario_de_decisoes'::regclass and conname='ck_diario_acao';
--               → contém 'respondeu_portal' e os 4 de antes
--            2) num DO que TERMINA em `raise exception` (nada fica): uma linha `origem='portal'`,
--               `acao='respondeu_portal'`, `modo='on'` é ACEITA; a mesma com `acao='respondeu_inventada'` é RECUSADA
--               por `ck_diario_acao`; `acao='respondeu_portal'` com `modo='sombra'` é RECUSADA por
--               `ck_diario_sombra_nao_agiu` (a régua da sombra não afrouxou)
--            3) select count(*) from public.diario_de_decisoes where chave_idempotencia like 'verify-124-%' → 0
-- ROLLBACK:  (só se nenhuma linha usar o valor novo — senão o add abaixo falha e nada muda)
--            alter table public.diario_de_decisoes drop constraint if exists ck_diario_acao;
--            alter table public.diario_de_decisoes add constraint ck_diario_acao
--              check (acao in ('respondeu_ura', 'perguntou_segurado', 'chamou_pessoa', 'nao_agiu'));
--            E o código (`diario_de_decisoes.ACOES`, `destravador.ACAO_NO_DIARIO_DO_PORTAL`) volta junto.

alter table public.diario_de_decisoes drop constraint if exists ck_diario_acao;
alter table public.diario_de_decisoes add constraint ck_diario_acao
  check (acao in ('respondeu_ura', 'perguntou_segurado', 'chamou_pessoa', 'nao_agiu', 'respondeu_portal'));

comment on constraint ck_diario_acao on public.diario_de_decisoes is
  'SPEC-123 F4 + SPEC-124 F1: respondeu_ura (a URA do WhatsApp) · respondeu_portal (o portal de vidros, '
  'continuando o MESMO pedido) · perguntou_segurado · chamou_pessoa · nao_agiu (sombra / silencio).';
