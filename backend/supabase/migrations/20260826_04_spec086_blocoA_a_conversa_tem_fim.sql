-- =============================================================
-- MIGRATION: spec086_blocoA_a_conversa_tem_fim
-- SPEC:      SPEC-086 — BLOCO A (a conversa passa a ter FIM)
-- AUTOR:     execução Opus 5             DATA: 2026-08-26
-- OBJETIVO:  o produto passa a saber a diferença entre *"terminou"*,
--            *"está esperando"* e *"foi abandonado"*.
--
-- APPLY:     `conversations.resolucao_motivo` ganha CHECK de lista fechada,
--            e um índice para a pergunta da sexta-feira.
-- VERIFY:    o bloco VERIFY no fim deste arquivo (SQL executável).
-- ROLLBACK:  o bloco ROLLBACK no fim deste arquivo.
--
-- EXPAND-FIRST: sim  (as duas colunas já existem; isto só as governa)
-- DESTRUTIVA:   não
-- =============================================================
--
-- 📊 A RAZÃO, MEDIDA EM 26/08/2026 — e a SPEC acertou nos quatro números:
--
--     conversations ............................... 671
--       com `resolvido_em` preenchido ............... 0
--       com `resolucao_motivo` preenchido ........... 0
--     status em uso ......................... open=614, active=57
--     CHECK em `conversations` .................. NENHUM
--
-- > **O produto nunca marcou uma conversa como resolvida. Nem uma, em 671.**
--
-- 🔴 E A TUBULAÇÃO JÁ ESTAVA INTEIRA — falta só quem decida.
--
-- 📊 `attendance_ficha.gravar()` **já escreve as duas colunas** quando a ficha
-- traz `resolvido_em` (`attendance_ficha.py:342-344`), e a fase `resolvido` já
-- existe em `derivar_fase`. ⛔ Nenhum chamador jamais preencheu o campo:
-- `grep '"resolvido_em"'` fora daquele arquivo devolve **zero**.
--
-- ⚠️ Então esta SPEC **liga o que existe**; não constrói escritor novo (§5).
--
-- ---------------------------------------------------------------------------
-- 🔴 OS VALORES DO CHECK, E POR QUE DOIS NÃO SÃO OS DA SPEC
-- ---------------------------------------------------------------------------
--
-- A SPEC lista quatro motivos, e um deles mente sobre o que guarda:
--
--     a SPEC pede             o que o produto realmente faz
--     ─────────────────────   ────────────────────────────────────────────
--     acionamento_aberto      🔴 "aberto" é o MEIO, não o fim
--     resolvido_pelo_segurado ✅
--     fechado_por_humano      ✅
--     expirou                 ✅
--
-- 📊 Medido em `insurer_dispatch_service.py:138`, o produto **já sabe** o que é
-- terminar, e são DOIS desfechos de sucesso, não um:
--
--     FASES_ENCERRADAS = ("needs_human", "test_aborted",
--                         "encaminhado", "resolvido")
--
--     `resolvido`     o serviço foi prestado e o ciclo fechou
--     `encaminhado`   a seguradora não abre chamado: entregou formulário
--                     ou orientação, e o entregável já está em mãos (P-46)
--
-- ⛔ **Marcar `resolvido_em` quando o protocolo sai seria contar história
-- falsa.** 📊 `derivar_fase` chama esse estado de `acompanhando` —
-- *"há protocolo; espera-se o prestador"*. Um guincho que nunca chegou entraria
-- na conta de *"terminou"*, e é exatamente o relatório confiante e falso que
-- estas SPECs existem para impedir.
--
-- 🔴 `CLAUDE.md` §12.1: *"se o nome de um campo mente sobre o que ele guarda,
-- conserte o campo — não só o texto"*. Então `acionamento_aberto` vira
-- **`acionamento_concluido`**, e `encaminhado` entra ao lado dele.
--
-- ⚠️ Registrado em `CHANGE-ADDENDA` como **ESSENCIAL**, com este parágrafo.
--
-- =============================================================
-- APPLY
-- =============================================================

-- ① 🔴 A LISTA FECHADA. Estes são TODOS os valores aceitos:
--
--      acionamento_concluido    o dispatch chegou a `resolvido`: serviço
--                               prestado, ciclo fechado
--      encaminhado              o dispatch chegou a `encaminhado`: o
--                               entregável (formulário/orientação) está em mãos
--      resolvido_pelo_segurado  o próprio segurado disse que resolveu
--      fechado_por_humano       a atendente encerrou pela tela
--      expirou                  🔴 venceu sem resposta — quem escreve é o
--                               BLOCO C, e é o motivo que separa "terminou" de
--                               "morreu esperando"
--
-- ⚠️ NULO continua válido: é a conversa que **ainda não acabou**, e são 671 hoje.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conname = 'ck_conversations_resolucao_motivo'
       AND conrelid = 'public.conversations'::regclass
  ) THEN
    ALTER TABLE public.conversations
      ADD CONSTRAINT ck_conversations_resolucao_motivo
      CHECK (resolucao_motivo IS NULL OR resolucao_motivo IN (
        'acionamento_concluido',
        'encaminhado',
        'resolvido_pelo_segurado',
        'fechado_por_humano',
        'expirou'
      ));
  END IF;
END $$;

-- ② 🔴 OS DOIS CAMPOS ANDAM JUNTOS OU NÃO ANDAM.
--
-- ⚠️ Uma conversa com `resolucao_motivo` e sem `resolvido_em` é uma que "acabou
-- por um motivo, em momento nenhum" — e ela some de toda consulta por período,
-- que é justamente a pergunta da sexta-feira.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conname = 'ck_conversations_resolucao_coerente'
       AND conrelid = 'public.conversations'::regclass
  ) THEN
    ALTER TABLE public.conversations
      ADD CONSTRAINT ck_conversations_resolucao_coerente
      CHECK ((resolvido_em IS NULL AND resolucao_motivo IS NULL)
          OR (resolvido_em IS NOT NULL AND resolucao_motivo IS NOT NULL));
  END IF;
END $$;

-- ③ o índice da pergunta da sexta-feira: *"dos atendimentos desta semana,
--    quantos terminaram?"*. PARCIAL — 📊 hoje 671 de 671 são NULAS.
CREATE INDEX IF NOT EXISTS ix_conversations_resolvidas
  ON public.conversations (company_id, resolvido_em DESC, resolucao_motivo)
  WHERE resolvido_em IS NOT NULL;

COMMENT ON COLUMN public.conversations.resolucao_motivo IS
  'SPEC-086 BLOCO A — POR QUE o atendimento acabou. Lista fechada (ver CHECK). '
  'NULO = ainda não acabou. `expirou` é o que separa "terminou" de "morreu '
  'esperando" — sem ele os dois são o mesmo estado para o banco.';

-- =============================================================
-- VERIFY  (read-only, e o CONTROLE desfaz o que escreve)
-- =============================================================
--
-- V1 · 🔴 OS VALORES DO CHECK, como o protocolo exige
--
--   select conname, pg_get_constraintdef(oid) from pg_constraint
--    where conrelid='public.conversations'::regclass and contype='c';
--   -- esperado: ck_conversations_resolucao_motivo com os CINCO valores
--   --           ck_conversations_resolucao_coerente
--
-- V2 · 🔴 O CONTROLE — o banco RECUSA o inválido, E ACEITA o válido.
--      ⚠️ A transação é desfeita por `raise`: nada fica gravado.
--
--   do $$
--   declare v_id uuid; r_invalido boolean := false; r_meio boolean := false;
--           aceitou boolean := false; v_erro text := '';
--   begin
--     select id into v_id from conversations limit 1;
--
--     begin update conversations set resolvido_em = now(),
--                  resolucao_motivo = 'acionamento_aberto' where id = v_id;
--     exception when check_violation then r_invalido := true;
--               when others then v_erro := v_erro||' inv='||SQLSTATE; end;
--
--     begin update conversations set resolvido_em = null,
--                  resolucao_motivo = 'expirou' where id = v_id;
--     exception when check_violation then r_meio := true;
--               when others then v_erro := v_erro||' meio='||SQLSTATE; end;
--
--     begin update conversations set resolvido_em = now(),
--                  resolucao_motivo = 'acionamento_concluido' where id = v_id;
--           aceitou := true;
--     exception when others then v_erro := v_erro||' ok='||SQLSTATE; end;
--
--     raise exception 'V2 || motivo INVALIDO recusado? % || so metade recusada? % '
--                     '|| motivo VALIDO aceito? % || outros:[%]',
--       r_invalido, r_meio, aceitou, v_erro;
--   end $$;
--   -- esperado: t | t | t | []
--
-- V3 · a pergunta da sexta-feira
--
--   select resolucao_motivo, count(*)
--     from conversations
--    where company_id = $1 and resolvido_em >= now() - interval '7 days'
--    group by 1 order by 2 desc;
--
-- =============================================================
-- ROLLBACK
-- =============================================================
--
--   drop index if exists public.ix_conversations_resolvidas;
--   alter table public.conversations
--     drop constraint if exists ck_conversations_resolucao_coerente;
--   alter table public.conversations
--     drop constraint if exists ck_conversations_resolucao_motivo;
--
-- ⚠️ Derrubar o CHECK não apaga dado — só deixa de governar o que entra.
