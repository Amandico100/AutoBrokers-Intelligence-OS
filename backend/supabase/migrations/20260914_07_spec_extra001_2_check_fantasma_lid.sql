-- =============================================================
-- MIGRATION: spec_extra001_2_check_fantasma_lid
-- SPEC:      SPEC-EXTRA-001.2 — BLOCO E (§11, M1) · destrava P-PILOTO-13
-- AUTOR:     builder E (Opus 5)              DATA: 2026-09-14
-- OBJETIVO:  `ck_conversations_resolucao_motivo` passa a aceitar o sexto valor,
--            `fantasma_lid` — sem ele, `migrar_conversas_fantasma_lid.py --vivo`
--            fica recusado e as 175 conversas-fantasma continuam abertas.
--
-- APPLY:     DROP + ADD do CHECK com a lista de SEIS valores (a lista só CRESCE).
--            📊 Medido em 14/09/2026 (dry-run do script, BLOCO 0 premissa 9):
--               175 conversas-fantasma · 175 ABERTAS · 69 Resulta + 106 AutoFleet
--               10 com pausa humana presa · 2 com par real ainda aberto
--               166 sem par (só fecham) · 1.884 mensagens do lado fantasma
--            ⛔ NENHUMA mensagem é apagada: muda `status`, `resolvido_em` e
--               `resolucao_motivo`, e nada mais.
--            🔴 ISTO NÃO É O ENCERRAMENTO EM LOTE QUE A D-PILOTO-02 PROÍBE.
--               Aquela decisão fala das 467 conversas ABERTAS e REAIS da
--               AutoFleet, que o agente deve continuar respondendo. Estas 175
--               têm um identificador interno do WhatsApp no lugar do telefone:
--               ninguém consegue abri-las e ninguém consegue responder por elas.
--               Conjuntos diferentes — e o dry-run imprime a contagem dos dois.
--            🔴 O MESMO VALOR TEM DE EXISTIR NO PRODUTO
--               (`o_fim_do_atendimento.MOTIVOS`, `FANTASMA_LID`): sem ele lá,
--               `marcar_fim` levanta `ValueError` e o conserto fica pela metade.
--
-- VERIFY:    V1/V2/V3 abaixo — SQL executável, e o adversarial em BEGIN…ROLLBACK.
-- ROLLBACK:  o bloco do fim — e ele RECUSA reverter se alguma linha já usar
--            `fantasma_lid`, porque reverter apagaria a razão pela qual 175
--            conversas foram fechadas.
--
-- EXPAND-FIRST: sim (a lista fechada só ganha valor; nenhum valor sai)
-- DESTRUTIVA:   não (nenhuma linha é lida, escrita ou apagada por esta migration)
-- =============================================================

-- ⚠️ DROP + ADD, e não um `IF NOT EXISTS`: a constraint EXISTE (criada pela
-- `20260826_04:96`) e precisa ser SUBSTITUÍDA. `ADD CONSTRAINT` com o mesmo nome
-- falharia (42710), e por isso o DROP vem antes, na mesma transação implícita do
-- arquivo — não há janela em que a tabela fique sem o CHECK para um escritor
-- concorrente.
--
-- ⛔ Não use `NOT VALID`: a tabela tem 879 linhas (14/09/2026) e a validação é
-- instantânea; `NOT VALID` deixaria o CHECK sem valer para o que já está lá.
ALTER TABLE public.conversations
  DROP CONSTRAINT IF EXISTS ck_conversations_resolucao_motivo;

ALTER TABLE public.conversations
  ADD CONSTRAINT ck_conversations_resolucao_motivo
  CHECK (resolucao_motivo IS NULL OR resolucao_motivo IN (
    'acionamento_concluido',
    'encaminhado',
    'resolvido_pelo_segurado',
    'fechado_por_humano',
    'expirou',
    -- 🔴 O SEXTO. Conversa-fantasma de `@lid`: `user_phone` é um identificador
    -- interno do WhatsApp (~15 dígitos, sem `55`), não o telefone de ninguém.
    'fantasma_lid'
  ));

COMMENT ON COLUMN public.conversations.resolucao_motivo IS
  'SPEC-086 BLOCO A / SPEC-EXTRA-001.2 E2 — POR QUE o atendimento acabou. Lista '
  'fechada de SEIS valores (ver CHECK); a mesma de `o_fim_do_atendimento.MOTIVOS`. '
  'NULO = ainda não acabou. `expirou` separa "terminou" de "morreu esperando"; '
  '`fantasma_lid` é a conversa criada por um @lid, que ninguém consegue abrir.';

-- =============================================================
-- VERIFY  (read-only; o adversarial desfaz o que escreve)
-- =============================================================
--
-- V1 · o CHECK contém o valor novo
--
--   select pg_get_constraintdef(oid) from pg_constraint
--    where conname = 'ck_conversations_resolucao_motivo'
--      and conrelid = 'public.conversations'::regclass;
--   -- esperado: a definição contém 'fantasma_lid' E os cinco antigos
--
-- V2 · 🔴 O ADVERSARIAL — o banco RECUSA um motivo fora da lista, e ACEITA o novo.
--      ⚠️ Tudo dentro de BEGIN…ROLLBACK: nada fica gravado.
--
--   begin;
--   do $$
--   declare v_id uuid; recusou boolean := false; aceitou boolean := false;
--   begin
--     select id into v_id from public.conversations
--      where resolvido_em is null limit 1;
--     if v_id is null then raise notice 'V2 sem conversa aberta para testar'; return; end if;
--
--     -- (a) motivo FORA da lista → tem de ser recusado (23514)
--     begin
--       update public.conversations
--          set resolvido_em = now(), resolucao_motivo = 'motivo_que_nao_existe'
--        where id = v_id;
--     exception when check_violation then recusou := true;
--     end;
--
--     -- (b) o motivo NOVO → tem de ser aceito
--     begin
--       update public.conversations
--          set resolvido_em = now(), resolucao_motivo = 'fantasma_lid'
--        where id = v_id;
--       aceitou := true;
--     exception when check_violation then aceitou := false;
--     end;
--
--     raise notice 'V2 recusou_invalido=% aceitou_fantasma_lid=%', recusou, aceitou;
--     -- esperado: recusou_invalido=t  aceitou_fantasma_lid=t
--   end $$;
--   rollback;
--
-- V3 · nenhuma linha usa o valor novo ANTES do script (o `--vivo` é quem escreve)
--
--   select count(*) from public.conversations where resolucao_motivo = 'fantasma_lid';
--   -- esperado ANTES do `--vivo`: 0     · DEPOIS do `--vivo`: 175
--
-- V4 · e o VERIFY do próprio script, depois do `--vivo` (ele o imprime):
--
--   select count(*) from public.conversations
--    where status <> 'closed'
--      and (user_phone !~ '^55'
--           or length(regexp_replace(user_phone, '[^0-9]', '', 'g')) > 13);
--   -- esperado: 0
--
-- =============================================================
-- ROLLBACK  (não é automático: LEIA o resultado antes de rodar o ALTER)
-- =============================================================
--
--   -- ① a pergunta que decide se o rollback é legítimo
--   select count(*) as linhas_com_fantasma_lid from public.conversations
--    where resolucao_motivo = 'fantasma_lid';
--
--   -- ② 🔴 SE O NÚMERO NÃO FOR ZERO, **NÃO REVERTA** e registre.
--   --    Reverter exigiria apagar `resolucao_motivo` das linhas fechadas — ou
--   --    seja, apagar a RAZÃO pela qual 175 conversas foram fechadas, deixando
--   --    175 conversas `closed` sem motivo (e violando o CHECK de coerência
--   --    `ck_conversations_resolucao_coerente`, que exige os dois juntos).
--   --    O rollback do DADO é o que o script imprime linha a linha antes do
--   --    `--vivo`; este aqui é só o da ESTRUTURA.
--
--   -- ③ só com ① = 0:
--   alter table public.conversations
--     drop constraint if exists ck_conversations_resolucao_motivo;
--   alter table public.conversations
--     add constraint ck_conversations_resolucao_motivo
--     check (resolucao_motivo is null or resolucao_motivo in (
--       'acionamento_concluido','encaminhado','resolvido_pelo_segurado',
--       'fechado_por_humano','expirou'));
-- =============================================================
