-- =============================================================
-- MIGRATION: 20261001_07_spec125_prompt_v2
-- SPEC:      SPEC-125 — S4 · o prompt novo do atendimento e a versão antiga reativável SEM deploy (D3)
-- AUTOR:     builder S4 (Opus 5.5 xhigh)      DATA: 2026-10-01
-- OBJETIVO:  (1) `agents.prompt_versao` ('v1' | 'v2', padrão 'v2') — a chave, POR AGENTE (e o agente
--            é de UMA corretora: `agents.company_id`), que escolhe a base do prompt do atendimento.
--            Voltar ao prompt de hoje = UM update de uma linha, valendo no próximo turno (o leitor em
--            `graph._build_initial_state` lê a coluna a cada turno, por `id` E `company_id`, sem cache).
--            (2) troca, no prompt que mora NO BANCO dos agentes de atendimento, SÓ a frase que
--            contradizia a regra única de como perguntar ("colete uma informacao por vez" × "bloco de
--            até 4" × "de uma vez só, até 12" — laudo INV-ATENDIMENTO T11). Nada mais do texto muda.
--
-- 📊 ANTES (01/10/2026, SELECT read-only pelo MCP, agent_role in ('attendance','insured_external')):
--    4 agentes, todos `attendance`, todos is_active=false; cada um com EXATAMENTE 1 ocorrência de
--    '; colete uma informacao por vez;' (o texto do molde, sem acento — nenhum personalizado nessa frase);
--    a coluna `prompt_versao` NÃO existe (information_schema.columns).
--    md5 de cada texto ANTES (a prova do ROLLBACK exato — sem guardar o texto da corretora aqui, §13.9):
--      3aca755609e4814b1d29e7d6e341493c · 7725f1fc74462aedce1b4ccdf6599636
--      b03a531ea72007938c71b61c3aa899be · f5606ac4da7aa0d3df7db4802a038c48
--
-- 🔴 MULTI-CORRETORA (§13.9): nenhum nome nem id de corretora; quem recebe é escolhido pelo PAPEL e
--    pela frase exata do molde. Texto personalizado pela corretora (sem a frase do molde) não é tocado.
-- 🔴 O padrão 'v2' vale também para agente que nascer amanhã; o código declara o MESMO padrão
--    (`prompts.PROMPT_VERSAO_PADRAO`) para quando a coluna não puder ser lida.
--
-- APPLY:  (a) add column if not exists `prompt_versao text not null default 'v2'` + CHECK nomeado,
--         criado só se não existir; (b) `replace` da frase antiga pela nova, só em agentes de
--         atendimento e só onde a antiga existe; um DO confere 0 antigas e no máximo 1 nova por linha
--         (senão aborta tudo).
-- VERIFY: (1) a coluna existe, NOT NULL, default 'v2', CHECK ('v1','v2') · (2) antigas=0 · novas=4 ·
--         (3) o texto de cada agente, com a frase nova trocada de volta, tem o md5 de ANTES ·
--         (4) is_active intacto (0 ativos) · (5) 'v3' é recusado pelo CHECK (dentro de rollback).
-- ROLLBACK: (b) o `replace` inverso; (a) drop do CHECK e da coluna (só no rollback — expand-first).
--
-- ⚠️ ESTADO DA APLICAÇÃO (01/10/2026, MCP `apply_migration` nome `spec125_prompt_v2`):
--    · PARTE A (coluna + CHECK + comentário) — APLICADA, versão 20261002012519. VERIFY (1) conferido:
--      prompt_versao | NO | 'v2'::text · CHECK ((prompt_versao = ANY (ARRAY['v1','v2']))) · 4 agentes em 'v2',
--      0 ativos, md5 dos 4 textos IGUAIS aos de ANTES (a parte B não rodou).
--    · PARTE B (a frase do prompt do banco) — ⛔ DESCARTADA (conserto X6, 02/10/2026). NÃO APLICAR.
--      A troca da frase passou para o CÓDIGO, na montagem e só no v2
--      (`prompts.trocar_a_frase_do_banco_no_v2`, chamada em `build_composite_prompt`): com
--      `prompt_versao='v1'` o texto do banco chega ao modelo byte a byte, e a volta ao v1 continua
--      sendo UM update da chave — sem `replace` inverso. Aplicada, a B quebraria essa volta exata.
--      O texto abaixo fica só como registro, inteiro COMENTADO.
--
-- EXPAND-FIRST: sim (coluna nova com padrão; nada é removido)
-- DESTRUTIVA:   não (UPDATE de UMA frase em 4 linhas, reversível byte a byte pelo md5)
-- =============================================================

-- ─────────────────────────────── APPLY · PARTE A (APLICADA) ───────────────────────────────
begin;

alter table public.agents
  add column if not exists prompt_versao text not null default 'v2';

do $$
begin
  if not exists (select 1 from pg_constraint
                  where conname = 'agents_prompt_versao_check'
                    and conrelid = 'public.agents'::regclass) then
    alter table public.agents
      add constraint agents_prompt_versao_check check (prompt_versao in ('v1', 'v2'));
  end if;
end $$;

comment on column public.agents.prompt_versao is
  'SPEC-125 D3: base do prompt do ATENDIMENTO (v1 = o de 01/10/2026, intacto no código como '
  'ATTENDANCE_BASE_PROMPT_V1; v2 = objetivo e julgamento). Voltar: update agents set prompt_versao=''v1'' '
  'where id=<agente> and company_id=<corretora> — vale no próximo turno, sem deploy.';

commit;

-- ─────────────────────────────── APPLY · PARTE B — ⛔ DESCARTADA (X6) · NÃO APLICAR ───────────────────────────────
-- begin;

-- update public.agents
--    set agent_system_prompt = replace(agent_system_prompt,
--          '; colete uma informacao por vez;',
--          '; pergunte so o que falta e muda a proxima acao (o que e independente vai junto, o delicado vai sozinho);')
--  where agent_role in ('attendance', 'insured_external')
--    and agent_system_prompt like '%; colete uma informacao por vez;%';

-- do $$
-- declare
--   v_antigas int;
--   v_dupla   int;
-- begin
--   select count(*) into v_antigas from public.agents
--    where agent_role in ('attendance', 'insured_external')
--      and agent_system_prompt ilike '%uma informacao por vez%';
--   select count(*) into v_dupla from public.agents
--    where agent_role in ('attendance', 'insured_external')
--      and (length(agent_system_prompt)
--           - length(replace(agent_system_prompt, 'pergunte so o que falta e muda a proxima acao', '')))
--          / length('pergunte so o que falta e muda a proxima acao') > 1;
--   if v_antigas <> 0 or v_dupla <> 0 then
--     raise exception 'APPLY 20261001_07 abortado: antigas=% duplicadas=%', v_antigas, v_dupla;
--   end if;
-- end $$;

-- commit;

-- ─────────────────────────────── VERIFY (read-only) ───────────────────────────────
-- select column_name, is_nullable, column_default from information_schema.columns
--  where table_schema='public' and table_name='agents' and column_name='prompt_versao';
--   -- esperado: prompt_versao | NO | 'v2'::text
-- select pg_get_constraintdef(oid) from pg_constraint where conname='agents_prompt_versao_check';
--   -- esperado: CHECK ((prompt_versao = ANY (ARRAY['v1'::text, 'v2'::text])))
-- select count(*) filter (where agent_system_prompt ilike '%uma informacao por vez%')                 as antigas, -- 0
--        count(*) filter (where agent_system_prompt like '%pergunte so o que falta e muda a proxima acao%') as novas,  -- 4
--        count(*) filter (where is_active)                                                            as ativos,  -- 0
--        count(*) filter (where prompt_versao = 'v2')                                                 as em_v2,   -- 4
--        array_agg(md5(replace(agent_system_prompt,
--          '; pergunte so o que falta e muda a proxima acao (o que e independente vai junto, o delicado vai sozinho);',
--          '; colete uma informacao por vez;')) order by 1)                                           as md5_de_antes
--   from public.agents where agent_role in ('attendance', 'insured_external');
--   -- esperado md5_de_antes = {3aca755609e4814b1d29e7d6e341493c,7725f1fc74462aedce1b4ccdf6599636,
--   --                          b03a531ea72007938c71b61c3aa899be,f5606ac4da7aa0d3df7db4802a038c48}
-- -- o CHECK recusa valor fora da lista (rodar e desfazer):
-- begin; update public.agents set prompt_versao = 'v3' where id = (select id from public.agents limit 1); rollback;
--   -- esperado: ERROR 23514 violates check constraint "agents_prompt_versao_check"

-- ─────────────────────────────── ROLLBACK (escrito ANTES de aplicar) ───────────────────────────────
-- begin;
-- update public.agents set agent_system_prompt = replace(agent_system_prompt,
--   '; pergunte so o que falta e muda a proxima acao (o que e independente vai junto, o delicado vai sozinho);',
--   '; colete uma informacao por vez;')
--  where agent_role in ('attendance', 'insured_external');
-- -- prova: array_agg(md5(agent_system_prompt) order by 1) = o conjunto de md5 de ANTES acima
-- alter table public.agents drop constraint if exists agents_prompt_versao_check;
-- alter table public.agents drop column if exists prompt_versao;
-- commit;
-- ⚠️ Para só VOLTAR AO PROMPT DE HOJE não é preciso rollback nenhum: basta
--    update public.agents set prompt_versao = 'v1' where id = '<agente>' and company_id = '<corretora>';
