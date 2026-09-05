-- =============================================================
-- MIGRATION: spec097_episodio_tem_conversa
-- SPEC:      SPEC-097 — U3.1 (o episódio ganha identidade e desfecho)
-- AUTOR:     execução Opus 5             DATA: 2026-09-05
-- OBJETIVO:  o EPISÓDIO de atendimento passa a saber de qual conversa ele é —
--            e a saber como terminou, mesmo quando conversa nenhuma existe.
--
-- APPLY:     `attendance_sessions` ganha `conversation_id` (FK **COMPOSTA**
--            `(conversation_id, company_id) → conversations (id, company_id)`,
--            `ON DELETE SET NULL (conversation_id)`), `resolvido_em`,
--            `resolucao_motivo` (o MESMO CHECK da conversa) e o índice
--            `(company_id, conversation_id)`.
-- VERIFY:    o bloco VERIFY no fim deste arquivo (SQL executável).
-- ROLLBACK:  o bloco ROLLBACK no fim deste arquivo.
--
-- EXPAND-FIRST: sim  (só acrescenta; nada é removido nem reescrito)
-- DESTRUTIVA:   não
-- =============================================================
--
-- 📊 A RAZÃO, MEDIDA EM 05/09/2026 (SPEC-097 §1):
--
--     attendance_sessions ................... 12.755 linhas
--       com `conversation_id` ................ a coluna NÃO EXISTE
--     conversations ............................. 728
--       com `resolvido_em` .......................... 0
--     sessões por contato ....................... 5,8
--     sessões que casam 1:1 por telefone ...... 57,8%
--
-- 🔴 **O CASO DA OPERAÇÃO É O EPISÓDIO, NÃO A CONVERSA.** São 5,8 episódios
-- por contato: guardar o desfecho só na conversa juntaria numa marca só cinco
-- atendimentos diferentes do mesmo segurado — o guincho de março e a dúvida de
-- apólice de agosto teriam o mesmo "terminou".
--
-- ⚠️ E 42,2% dos episódios NUNCA terão conversa (E7). Para eles, `resolvido_em`
-- na conversa é uma coluna que não existe: ou o desfecho mora aqui, ou eles
-- ficam sem desfecho para sempre.
--
-- ---------------------------------------------------------------------------
-- 🔴 POR QUE A FK É COMPOSTA — e a simples deixava o elo atravessar corretora
-- ---------------------------------------------------------------------------
--
-- ⛔ `REFERENCES conversations(id)` prova que a conversa EXISTE. Não prova que
-- ela é DESTA corretora. O elo é o único dado novo desta SPEC, e nada impedia
-- um episódio da Resulta nascer apontando para uma conversa da AutoFleet: o
-- código degrada bem (a hidratação filtra por `company_id` e o episódio vira
-- "sem conversa"), mas o dado sujo fica no banco para sempre.
--
-- 🔴 §7: *"RLS + filtro no repository + constraints e foreign keys"*. O par
-- `(conversation_id, company_id)` é a constraint dessa lista, e ele repete o
-- que a SPEC-090 BLOCO A já fez em `work_runs` — mesma forma, mesma razão.
--
-- 📊 Medido em 05/09/2026: `conversations` **já tem** índice único sobre
-- `(id, company_id)` — a FK apenas o referencia, nenhum índice novo nasce aqui.
--
-- ⚠️ `ON DELETE SET NULL (conversation_id)` — a LISTA DE COLUNAS não é enfeite:
-- `attendance_sessions.company_id` é NOT NULL, e um `SET NULL` sem lista
-- tentaria anular as DUAS colunas e estouraria no `DELETE` da conversa. A
-- sintaxe é PG15+; 📊 o banco é PostgreSQL **17.6** (medido em 05/09/2026).
--
-- ---------------------------------------------------------------------------
-- 🔴 POR QUE `ON DELETE SET NULL`, e não CASCADE
-- ---------------------------------------------------------------------------
--
-- A conversa é o ESPELHO; o episódio é o FATO — ele tem o transcript da
-- operação. Apagar uma conversa não pode apagar o atendimento que aconteceu.
-- ⛔ `CASCADE` aqui destruiria acervo. `RESTRICT` impediria a limpeza legítima
-- de conversas. `SET NULL` devolve o episódio ao estado de órfão, que é um
-- estado que o produto já sabe tratar (E7).
--
-- =============================================================
-- APPLY
-- =============================================================

-- ① o ELO (R3). ⚠️ `NULL` é o valor normal: 📊 42,2% dos episódios ficam sem.
ALTER TABLE public.attendance_sessions
  ADD COLUMN IF NOT EXISTS conversation_id uuid NULL;

-- ①.b 🔴 e a FK é COMPOSTA — a corretora entra na chave (§7). Guardada por
--     `pg_constraint` porque `ADD CONSTRAINT` não tem `IF NOT EXISTS`.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conname = 'fk_attendance_sessions_conversa'
       AND conrelid = 'public.attendance_sessions'::regclass
  ) THEN
    ALTER TABLE public.attendance_sessions
      ADD CONSTRAINT fk_attendance_sessions_conversa
      FOREIGN KEY (conversation_id, company_id)
      REFERENCES public.conversations (id, company_id)
      ON DELETE SET NULL (conversation_id);
  END IF;
END $$;

-- ② o DESFECHO no episódio (E8) — as duas colunas andam juntas.
ALTER TABLE public.attendance_sessions
  ADD COLUMN IF NOT EXISTS resolvido_em timestamptz NULL;

ALTER TABLE public.attendance_sessions
  ADD COLUMN IF NOT EXISTS resolucao_motivo text NULL;

-- ③ 🔴 O MESMO CHECK DA CONVERSA (`ck_conversations_resolucao_motivo`,
--    SPEC-086 BLOCO A). Dois vocabulários para "por que terminou" seriam duas
--    respostas para a pergunta da sexta-feira.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conname = 'ck_attendance_sessions_resolucao_motivo'
       AND conrelid = 'public.attendance_sessions'::regclass
  ) THEN
    ALTER TABLE public.attendance_sessions
      ADD CONSTRAINT ck_attendance_sessions_resolucao_motivo
      CHECK (resolucao_motivo IS NULL OR resolucao_motivo IN (
        'acionamento_concluido',
        'encaminhado',
        'resolvido_pelo_segurado',
        'fechado_por_humano',
        'expirou'
      ));
  END IF;
END $$;

-- ④ e a coerência: "acabou por um motivo, em momento nenhum" some de toda
--    consulta por período — que é justamente a pergunta que se faz.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conname = 'ck_attendance_sessions_resolucao_coerente'
       AND conrelid = 'public.attendance_sessions'::regclass
  ) THEN
    ALTER TABLE public.attendance_sessions
      ADD CONSTRAINT ck_attendance_sessions_resolucao_coerente
      CHECK ((resolvido_em IS NULL AND resolucao_motivo IS NULL)
          OR (resolvido_em IS NOT NULL AND resolucao_motivo IS NOT NULL));
  END IF;
END $$;

-- ⑤ o índice da junção (U3.1). 🔴 `company_id` PRIMEIRO: toda leitura do
--    produto é de UMA corretora (§7), e é ela que corta o volume.
CREATE INDEX IF NOT EXISTS ix_attendance_sessions_conversa
  ON public.attendance_sessions (company_id, conversation_id);

-- ⑥ o índice do desfecho — a pergunta "o que terminou nesta semana?" agora
--    também é feita ao episódio. PARCIAL: 📊 hoje 12.755 de 12.755 são NULAS.
CREATE INDEX IF NOT EXISTS ix_attendance_sessions_resolvidas
  ON public.attendance_sessions (company_id, resolvido_em DESC, resolucao_motivo)
  WHERE resolvido_em IS NOT NULL;

COMMENT ON COLUMN public.attendance_sessions.conversation_id IS
  'SPEC-097 U3.1 — a conversa DESTE episódio, quando a junção por telefone é '
  'única. NULO é normal: 📊 42,2% dos episódios não têm conversa (E7). '
  'ON DELETE SET NULL — apagar a conversa não pode apagar o atendimento.';

COMMENT ON COLUMN public.attendance_sessions.resolucao_motivo IS
  'SPEC-097 U3.1/E8 — POR QUE este EPISÓDIO acabou. Mesma lista fechada de '
  '`conversations.resolucao_motivo`. ⛔ `attendance_sessions.status=closed` '
  'NÃO é desfecho: ele é fechado por 6h de silêncio (attendance_distiller).';

-- =============================================================
-- VERIFY  (read-only, e o CONTROLE desfaz o que escreve)
-- =============================================================
--
-- V1 · as colunas e a FK existem, com o ON DELETE certo
--
--   select column_name, data_type, is_nullable
--     from information_schema.columns
--    where table_schema='public' and table_name='attendance_sessions'
--      and column_name in ('conversation_id','resolvido_em','resolucao_motivo');
--   -- esperado: 3 linhas, todas YES em is_nullable
--
--   select conname, confdeltype, pg_get_constraintdef(oid)
--     from pg_constraint
--    where conrelid='public.attendance_sessions'::regclass and contype='f';
--   -- esperado: `fk_attendance_sessions_conversa` com confdeltype = 'n'
--   --           (SET NULL) e definição
--   --           FOREIGN KEY (conversation_id, company_id)
--   --             REFERENCES conversations(id, company_id)
--   --             ON DELETE SET NULL (conversation_id)
--
-- V1.b · 🔴 O CONTROLE DA FK COMPOSTA — o elo CROSS-TENANT é RECUSADO e o
--        elo da MESMA corretora é ACEITO. Sem as duas metades, um "recusou"
--        provaria só que a linha era inválida por outro motivo.
--        ⚠️ Desfeito por `raise`: nada fica gravado.
--
--   do $$
--   declare v_ep uuid; v_cv uuid; v_co uuid; v_outra uuid;
--           recusou boolean := false; aceitou boolean := false; v_erro text := '';
--   begin
--     select id, company_id into v_cv, v_co from conversations limit 1;
--     select id into v_ep from attendance_sessions
--      where company_id = v_co limit 1;
--     select company_id into v_outra from conversations
--      where company_id <> v_co limit 1;
--
--     begin update attendance_sessions set conversation_id = v_cv
--            where id = (select id from attendance_sessions
--                         where company_id = v_outra limit 1);
--     exception when foreign_key_violation then recusou := true;
--               when others then v_erro := v_erro||' cross='||SQLSTATE; end;
--
--     begin update attendance_sessions set conversation_id = v_cv
--            where id = v_ep; aceitou := true;
--     exception when others then v_erro := v_erro||' mesma='||SQLSTATE; end;
--
--     raise exception 'V1.b || cross-tenant recusado? % || mesma corretora '
--                     'aceita? % || outros:[%]', recusou, aceitou, v_erro;
--   end $$;
--   -- esperado: t | t | []
--
-- V2 · 🔴 O CONTROLE — o banco RECUSA o motivo inválido E ACEITA o válido.
--      ⚠️ A transação é desfeita por `raise`: nada fica gravado.
--
--   do $$
--   declare v_id uuid; r_invalido boolean := false; r_meio boolean := false;
--           aceitou boolean := false; v_erro text := '';
--   begin
--     select id into v_id from attendance_sessions limit 1;
--
--     begin update attendance_sessions set resolvido_em = now(),
--                  resolucao_motivo = 'fechado' where id = v_id;
--     exception when check_violation then r_invalido := true;
--               when others then v_erro := v_erro||' inv='||SQLSTATE; end;
--
--     begin update attendance_sessions set resolvido_em = null,
--                  resolucao_motivo = 'expirou' where id = v_id;
--     exception when check_violation then r_meio := true;
--               when others then v_erro := v_erro||' meio='||SQLSTATE; end;
--
--     begin update attendance_sessions set resolvido_em = now(),
--                  resolucao_motivo = 'resolvido_pelo_segurado' where id = v_id;
--           aceitou := true;
--     exception when others then v_erro := v_erro||' ok='||SQLSTATE; end;
--
--     raise exception 'V2 || motivo INVALIDO recusado? % || so metade recusada? % '
--                     '|| motivo VALIDO aceito? % || outros:[%]',
--       r_invalido, r_meio, aceitou, v_erro;
--   end $$;
--   -- esperado: t | t | t | []
--
-- V3 · o índice existe e a contagem de elos (antes do backfill: 0)
--
--   select indexname from pg_indexes
--    where schemaname='public' and tablename='attendance_sessions'
--      and indexname in ('ix_attendance_sessions_conversa',
--                        'ix_attendance_sessions_resolvidas');
--   -- esperado: 2 linhas
--
--   select count(*) filter (where conversation_id is not null) as com_elo,
--          count(*) as total
--     from attendance_sessions;
--   -- esperado logo após o APPLY: com_elo = 0 · total ≈ 12.755
--
-- =============================================================
-- ROLLBACK
-- =============================================================
--
--   drop index if exists public.ix_attendance_sessions_resolvidas;
--   drop index if exists public.ix_attendance_sessions_conversa;
--   alter table public.attendance_sessions
--     drop constraint if exists ck_attendance_sessions_resolucao_coerente;
--   alter table public.attendance_sessions
--     drop constraint if exists ck_attendance_sessions_resolucao_motivo;
--   alter table public.attendance_sessions
--     drop constraint if exists fk_attendance_sessions_conversa;
--   -- ⚠️ As COLUNAS não são derrubadas por padrão: elas passam a guardar o
--   --    desfecho de atendimentos reais, e apagá-las apaga essa história.
--   --    Só com decisão explícita do Founder (§8.6):
--   --      alter table public.attendance_sessions
--   --        drop column if exists resolucao_motivo,
--   --        drop column if exists resolvido_em,
--   --        drop column if exists conversation_id;
