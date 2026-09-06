-- =============================================================
-- MIGRATION: spec098_de_quem_e
-- SPEC:      SPEC-098 — U2.1 (o jeito de atender PROPOSTO) + U5 (o ator e a
--            conversa viajam até a peça e até a aprovação)
-- AUTOR:     execução Opus 5 — builder B      DATA: 2026-09-06
-- OBJETIVO:  cada coisa passa a saber DE QUEM É: a proposta de jeito de
--            atender fica separada do jeito ATIVO, e peça e aprovação passam
--            a saber de qual CONVERSA nasceram.
--
-- APPLY:     ① `brand_profiles` ganha `tone_proposto` (jsonb), `tone_proposto_origem`
--               (text), `tone_proposto_em` (timestamptz) e `tone_evidencia` (jsonb)
--               — o modelo PROPÕE aqui, a corretora PUBLICA em `tone` (R2).
--            ② COMMENT em `brand_profiles.tone` declarando que ele é o ATIVO.
--            ③ `artifacts.conversation_id` + FK **COMPOSTA**
--               `(conversation_id, company_id) → conversations (id, company_id)`,
--               `ON DELETE SET NULL (conversation_id)` + índice parcial.
--            ④ o mesmo par em `approval_requests.conversation_id`.
--            ⑤ COMMENT em `user_memories.user_id` — o campo mente sobre a
--               população que guarda (CLAUDE.md §12.1).
--            ⑥ limpeza D21: procedência que afirma origem de campo SEM VALOR.
-- VERIFY:    o bloco VERIFY no fim deste arquivo (SQL executável).
-- ROLLBACK:  o bloco ROLLBACK no fim deste arquivo.
--
-- EXPAND-FIRST: sim  (só acrescenta colunas; nada é removido nem reescrito)
-- DESTRUTIVA:   parcialmente — ⑥ APAGA 2 linhas de `brand_field_provenance`
--               (📊 medido em 06/09/2026), autorizado pela D21 da SPEC-098 §R10:
--               "a procedência só afirma origem de campo COM VALOR". Nenhuma
--               tabela, coluna ou índice é derrubado.
-- =============================================================
--
-- 📊 O ESTADO MEDIDO EM 06/09/2026 (SPEC-098 §1, `reality-report-098.md`):
--
--     brand_profiles ................................. 3 linhas
--       `tone` = `{}` (CONTEÚDO, não presença) ....... 3 de 3
--       `tone_proposto` ................. a coluna NÃO EXISTE
--     artifacts ..................................... 143 linhas
--       `requested_by` ................................. 0
--       coluna de conversa ................ NÃO EXISTE
--     approval_requests .............................. 10 linhas
--       `conversation_id` ................. NÃO EXISTE
--     brand_field_provenance ......................... 14 linhas
--       afirmando origem de campo SEM VALOR ............ 2
--
-- ---------------------------------------------------------------------------
-- 🔴 POR QUE `tone_proposto` É COLUNA SEPARADA, E NÃO UMA CHAVE DENTRO DE `tone`
-- ---------------------------------------------------------------------------
--
-- R2 da SPEC-098: **o modelo PROPÕE; a corretora PUBLICA.** Guardar a proposta
-- dentro do mesmo `tone` que o prompt renderiza faria a proposta VAZAR para o
-- segurado no instante em que fosse gravada — o modelo passaria a falar com um
-- jeito que ninguém aprovou. Duas colunas tornam o vazamento impossível por
-- construção: `render` lê `tone`, e `tone` só muda por ação de administrador.
--
-- ⚠️ `tone` é `NOT NULL` com default `{}` (📊 medido). `tone_proposto` é NULO
-- de propósito: "nunca foi proposto" e "foi proposto vazio" são fatos
-- diferentes, e o `{}` do ativo já significa "ainda não declarado".
--
-- ⚠️ UMA proposta por vez (R1): não nasce tabela de propostas. A segunda
-- captura sobrescreve a primeira, e `tone_proposto_em` diz de quando é.
--
-- ---------------------------------------------------------------------------
-- 🔴 POR QUE AS DUAS FKs SÃO COMPOSTAS — a simples deixava o elo atravessar
--    corretora
-- ---------------------------------------------------------------------------
--
-- ⛔ `REFERENCES conversations(id)` prova que a conversa EXISTE. Não prova que
-- ela é DESTA corretora. §7 do CLAUDE.md: *"RLS + filtro no repository +
-- constraints e foreign keys"* — e 📊 `artifacts` tem `rls=true` com
-- `policies=0`: o filtro no código é hoje a ÚNICA cerca. O par
-- `(conversation_id, company_id)` é a cerca que o banco impõe sozinho.
--
-- É a mesma forma da FK que a SPEC-097 U3.1 pôs em `attendance_sessions` e da
-- que a SPEC-090 BLOCO A pôs em `work_runs`. Mesma razão, mesma sintaxe.
--
-- 📊 Medido em 06/09/2026: `conversations` já tem o índice único
-- `uq_conversations_id_company` sobre `(id, company_id)` — a FK apenas o
-- referencia; nenhum índice novo nasce do lado da conversa.
--
-- ⚠️ `ON DELETE SET NULL (conversation_id)` — a LISTA DE COLUNAS não é enfeite:
-- 📊 `artifacts.company_id` e `approval_requests.company_id` são `NOT NULL`, e
-- um `SET NULL` sem lista tentaria anular as DUAS e estouraria no `DELETE` da
-- conversa. A sintaxe é PG15+; 📊 o banco é PostgreSQL 17.6.
--
-- 🔴 E `SET NULL`, não `CASCADE`: a peça é o ENTREGÁVEL (CLAUDE.md §6 —
-- "Artifact não é arquivo órfão", mas é resultado de 1ª classe) e a aprovação é
-- PROVA DE DECISÃO HUMANA. Apagar uma conversa não pode apagar o relatório que
-- o corretor mandou para o cliente nem o registro de quem autorizou o quê.
--
-- ---------------------------------------------------------------------------
-- 🔴 POR QUE OS ÍNDICES SÃO PARCIAIS
-- ---------------------------------------------------------------------------
--
-- 📊 Hoje 143 de 143 peças e 10 de 10 aprovações ficariam com `NULL` — e
-- continuarão em maioria, porque a Rotina e a Cobrança criam peça sem conversa.
-- Um índice cheio guardaria sobretudo nulos. `company_id` vem PRIMEIRO: toda
-- leitura do produto é de UMA corretora (§7), e é ela que corta o volume.
--
-- ---------------------------------------------------------------------------
-- 🔴 ⑥ A LIMPEZA D21 — o único DELETE, e por que ele é o conserto e não o
--    remendo
-- ---------------------------------------------------------------------------
--
-- 📊 2 linhas de `brand_field_provenance` afirmam de onde veio o `susep_code` e
-- a `service_area` de perfis onde esses campos são **NULOS**. É procedência de
-- um valor que não existe: a tela mostraria "extraído do site" ao lado de um
-- campo em branco. CLAUDE.md §12.1 — o texto errado é o sintoma; o dado que
-- mente é a causa. R10: *"a procedência só afirma origem de campo COM VALOR"*.
--
-- ⚠️ O DELETE é escrito por `USING`, casando `brand_profile_id` com o perfil, e
-- só apaga a linha cujo campo declarado está NULO **naquele perfil**. Ele é
-- idempotente por natureza: rodado de novo, casa 0 linhas.
--
-- =============================================================
-- APPLY
-- =============================================================

-- ① A PROPOSTA (R2) — separada do ativo. NULA enquanto ninguém propôs.
ALTER TABLE public.brand_profiles
  ADD COLUMN IF NOT EXISTS tone_proposto jsonb NULL;

ALTER TABLE public.brand_profiles
  ADD COLUMN IF NOT EXISTS tone_proposto_origem text NULL;

ALTER TABLE public.brand_profiles
  ADD COLUMN IF NOT EXISTS tone_proposto_em timestamptz NULL;

-- ①.b A EVIDÊNCIA — de onde a proposta saiu (quantas conversas lidas, quantas
--     descartadas por não serem atendimento, R11). Sem ela a tela não consegue
--     dizer "lidas N, descartadas M" e a proposta vira palpite sem procedência.
ALTER TABLE public.brand_profiles
  ADD COLUMN IF NOT EXISTS tone_evidencia jsonb NULL;

COMMENT ON COLUMN public.brand_profiles.tone_proposto IS
  'SPEC-098 R2/R3 — a proposta do modelo, UMA por vez. ⛔ NUNCA é renderizada '
  'no prompt: quem o prompt lê é `tone`. Publicar é mover daqui para lá, por '
  'ação de administradora, com versão em `brand_profile_versions`.';

COMMENT ON COLUMN public.brand_profiles.tone_proposto_origem IS
  'SPEC-098 R2 — de onde veio a proposta: `site` | `conversas` | `manual`. '
  'Procedência do que ainda não foi publicado.';

COMMENT ON COLUMN public.brand_profiles.tone_proposto_em IS
  'SPEC-098 R2 — quando a proposta foi feita. ⚠️ A segunda captura SOBRESCREVE '
  'a primeira (uma proposta por vez); esta coluna diz de quando é a que está lá.';

COMMENT ON COLUMN public.brand_profiles.tone_evidencia IS
  'SPEC-098 R11 — em que a proposta se apoia: `{lidas, descartadas, motivo}`. '
  'Conversa pessoal descartada é CONTADA, nunca sumida em silêncio.';

-- ② O ATIVO ganha nome. 📊 Em 06/09/2026 as 3 linhas têm `tone = {}` — e `{}`
--    aqui significa "ainda não declarado", nunca "declarado como vazio".
COMMENT ON COLUMN public.brand_profiles.tone IS
  'Jeito de atender ATIVO (SPEC-098 R3); `{}` = ainda não declarado. É ESTE que '
  'o prompt de atendimento renderiza. A proposta mora em `tone_proposto` e só '
  'chega aqui por publicação da administradora (R2). ⛔ Na tela o nome é '
  '"Jeito de atender" — nunca "tone", "Soul" ou "persona" (R1).';

-- ③ A PEÇA SABE DE QUAL CONVERSA NASCEU (P-096-ARTIFACT-SEM-CONVERSA).
ALTER TABLE public.artifacts
  ADD COLUMN IF NOT EXISTS conversation_id uuid NULL;

-- ③.b 🔴 FK COMPOSTA. Guardada por `pg_constraint` porque `ADD CONSTRAINT` não
--     tem `IF NOT EXISTS`.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conname = 'fk_artifacts_conversa'
       AND conrelid = 'public.artifacts'::regclass
  ) THEN
    ALTER TABLE public.artifacts
      ADD CONSTRAINT fk_artifacts_conversa
      FOREIGN KEY (conversation_id, company_id)
      REFERENCES public.conversations (id, company_id)
      ON DELETE SET NULL (conversation_id);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_artifacts_conversa
  ON public.artifacts (company_id, conversation_id)
  WHERE conversation_id IS NOT NULL;

COMMENT ON COLUMN public.artifacts.conversation_id IS
  'SPEC-098 U5.a/R8 — de qual CONVERSA esta peça nasceu. NULO é normal: Rotina '
  'e Cobrança criam peça sem conversa. FK composta com `company_id` — o elo não '
  'atravessa corretora. ON DELETE SET NULL: apagar a conversa não apaga a peça.';

-- ④ A APROVAÇÃO SABE DA CONVERSA (P-097-APPROVAL-SEM-CONVERSA).
ALTER TABLE public.approval_requests
  ADD COLUMN IF NOT EXISTS conversation_id uuid NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conname = 'fk_approval_requests_conversa'
       AND conrelid = 'public.approval_requests'::regclass
  ) THEN
    ALTER TABLE public.approval_requests
      ADD CONSTRAINT fk_approval_requests_conversa
      FOREIGN KEY (conversation_id, company_id)
      REFERENCES public.conversations (id, company_id)
      ON DELETE SET NULL (conversation_id);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_approval_requests_conversa
  ON public.approval_requests (company_id, conversation_id)
  WHERE conversation_id IS NOT NULL;

COMMENT ON COLUMN public.approval_requests.conversation_id IS
  'SPEC-098 U5.a/R8 — de qual CONVERSA veio o pedido de aprovação, quando o run '
  'a conhece. FK composta com `company_id`. ON DELETE SET NULL: a prova da '
  'decisão humana sobrevive à limpeza da conversa.';

-- ⑤ 🔴 O CAMPO QUE MENTE SOBRE A PRÓPRIA POPULAÇÃO (CLAUDE.md §12.1).
--    Não se conserta o nome nesta SPEC (isso é a 102, com backfill e prova);
--    conserta-se a MENTIRA para o próximo leitor, agora.
COMMENT ON COLUMN public.user_memories.user_id IS
  'SPEC-098 D22 — ⚠️ população = o SEGURADO da conversa, NÃO o membro da '
  'corretora. 📊 Medido em 06/09/2026: 0 de 41 membros têm linha aqui. O nome '
  'do campo mente; a 102 renomeia (P-098-USER-MEMORIES-E-DO-SEGURADO). Quem '
  'ler "user" e escrever memória de CORRETOR mistura duas populações.';

-- ⑥ LIMPEZA D21 — procedência que afirma origem de campo SEM VALOR (R10).
--   📊 Espera-se 2 linhas em 06/09/2026. Idempotente: na segunda vez, 0.
DELETE FROM public.brand_field_provenance p
 USING public.brand_profiles b
 WHERE p.brand_profile_id = b.id
   AND ((p.field_path = 'susep_code'   AND b.susep_code   IS NULL)
     OR (p.field_path = 'service_area' AND b.service_area IS NULL));

-- =============================================================
-- VERIFY  (read-only, e os CONTROLES desfazem o que escrevem)
-- =============================================================
--
-- V1 · as 4 colunas novas de `brand_profiles` existem, todas anuláveis, e o
--      ATIVO continua intacto
--
--   select column_name, data_type, is_nullable
--     from information_schema.columns
--    where table_schema='public' and table_name='brand_profiles'
--      and column_name in ('tone_proposto','tone_proposto_origem',
--                          'tone_proposto_em','tone_evidencia');
--   -- esperado: 4 linhas · jsonb/text/timestamptz/jsonb · todas YES
--
--   select count(*) as perfis,
--          count(*) filter (where tone = '{}'::jsonb) as tone_vazio,
--          count(tone_proposto) as com_proposta
--     from brand_profiles;
--   -- esperado logo após o APPLY: 3 | 3 | 0
--   -- 🔴 `tone_vazio` MEDE CONTEÚDO. `tone IS NOT NULL` daria 3 e mentiria:
--   --    a coluna é NOT NULL, então ela NUNCA é nula (SPEC-098 BLOCO 0).
--
-- V2 · as duas colunas de conversa existem, com as FKs COMPOSTAS e o
--      `ON DELETE SET NULL` certo
--
--   select conrelid::regclass::text as tabela, conname, confdeltype,
--          pg_get_constraintdef(oid) as def
--     from pg_constraint
--    where conname in ('fk_artifacts_conversa','fk_approval_requests_conversa');
--   -- esperado: 2 linhas, ambas confdeltype='n' (SET NULL), ambas com
--   --   FOREIGN KEY (conversation_id, company_id)
--   --     REFERENCES conversations(id, company_id)
--   --     ON DELETE SET NULL (conversation_id)
--
-- V2.b · 🔴 O CONTROLE DA FK COMPOSTA — o elo CROSS-TENANT é RECUSADO e o elo
--        da MESMA corretora é ACEITO. Sem as duas metades, um "recusou"
--        provaria só que a linha era inválida por outro motivo.
--        ⚠️ Desfeito por `raise`: nada fica gravado.
--
--   do $$
--   declare v_art uuid; v_cv uuid; v_co uuid; v_outra uuid; v_art_outra uuid;
--           recusou boolean := false; aceitou boolean := false; v_erro text := '';
--   begin
--     select c.id, c.company_id into v_cv, v_co
--       from conversations c join artifacts a on a.company_id = c.company_id
--      limit 1;
--     select id into v_art from artifacts where company_id = v_co limit 1;
--     select id, company_id into v_art_outra, v_outra
--       from artifacts where company_id <> v_co limit 1;
--
--     begin update artifacts set conversation_id = v_cv where id = v_art_outra;
--     exception when foreign_key_violation then recusou := true;
--               when others then v_erro := v_erro||' cross='||SQLSTATE; end;
--
--     begin update artifacts set conversation_id = v_cv where id = v_art;
--           aceitou := true;
--     exception when others then v_erro := v_erro||' mesma='||SQLSTATE; end;
--
--     raise exception 'V2.b || cross-tenant recusado? % || mesma corretora '
--                     'aceita? % || outros:[%]', recusou, aceitou, v_erro;
--   end $$;
--   -- esperado: t | t | []
--
-- V3 · os dois índices parciais existem, e as colunas nascem vazias
--
--   select indexname from pg_indexes
--    where schemaname='public'
--      and indexname in ('ix_artifacts_conversa','ix_approval_requests_conversa');
--   -- esperado: 2 linhas
--
--   select (select count(conversation_id) from artifacts)          as pecas_com_conversa,
--          (select count(*) from artifacts)                        as pecas,
--          (select count(conversation_id) from approval_requests)   as aprov_com_conversa,
--          (select count(*) from approval_requests)                 as aprovacoes;
--   -- esperado logo após o APPLY: 0 | 143 | 0 | 10
--
-- V4 · os COMMENTs que declaram a verdade estão no lugar
--
--   select c.relname||'.'||a.attname as coluna,
--          left(col_description(c.oid, a.attnum), 60) as diz
--     from pg_class c join pg_attribute a on a.attrelid=c.oid
--    where (c.relname='brand_profiles' and a.attname in ('tone','tone_proposto'))
--       or (c.relname='user_memories'  and a.attname='user_id')
--       or (c.relname='artifacts'      and a.attname='conversation_id')
--       or (c.relname='approval_requests' and a.attname='conversation_id');
--   -- esperado: 5 linhas, nenhuma com `diz` nulo
--
-- V5 · 🔴 A LIMPEZA D21 CONTOU, e o CONTROLE: a procedência COM valor SOBREVIVE
--
--   select count(*) as procedencia_sem_valor
--     from brand_field_provenance p join brand_profiles b on p.brand_profile_id=b.id
--    where (p.field_path='susep_code'   and b.susep_code   is null)
--       or (p.field_path='service_area' and b.service_area is null);
--   -- esperado: 0   (📊 eram 2 antes do APPLY)
--
--   select count(*) as procedencia_restante from brand_field_provenance;
--   -- esperado: 12  (📊 eram 14 — o controle: só as 2 mentirosas saíram)
--
-- =============================================================
-- ROLLBACK
-- =============================================================
--
--   drop index if exists public.ix_approval_requests_conversa;
--   drop index if exists public.ix_artifacts_conversa;
--   alter table public.approval_requests
--     drop constraint if exists fk_approval_requests_conversa;
--   alter table public.artifacts
--     drop constraint if exists fk_artifacts_conversa;
--   comment on column public.brand_profiles.tone is null;
--   comment on column public.user_memories.user_id is null;
--
--   -- ⚠️ As COLUNAS não são derrubadas por padrão: `tone_proposto` passa a
--   --    guardar propostas reais e `conversation_id` o elo de peças e
--   --    aprovações reais — apagá-las apaga essa história. Só com decisão
--   --    explícita do Founder (MIGRATIONS-AUTHORITY §8.6):
--   --      alter table public.approval_requests drop column if exists conversation_id;
--   --      alter table public.artifacts         drop column if exists conversation_id;
--   --      alter table public.brand_profiles
--   --        drop column if exists tone_evidencia,
--   --        drop column if exists tone_proposto_em,
--   --        drop column if exists tone_proposto_origem,
--   --        drop column if exists tone_proposto;
--
--   -- ⛔ ⑥ NÃO TEM ROLLBACK: as 2 linhas de procedência mentirosa foram
--   --    apagadas e não há de onde recriá-las — nem deveria haver, porque
--   --    afirmavam a origem de um valor que não existe. Recriá-las seria
--   --    reintroduzir o defeito. Se o campo ganhar valor no futuro, a captura
--   --    grava procedência NOVA, com a data certa.
