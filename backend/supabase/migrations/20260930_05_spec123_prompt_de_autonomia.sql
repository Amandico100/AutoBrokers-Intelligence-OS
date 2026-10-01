-- =============================================================
-- MIGRATION: 20260930_05_spec123_prompt_de_autonomia
-- SPEC:      SPEC-123 — F5a · costura (a D8 no prompt que mora NO BANCO)
-- AUTOR:     builder F5a (Opus 5.5 xhigh)      DATA: 2026-09-30
-- OBJETIVO:  a regra "em duvida, encaminhe a <pessoa>" do `agents.agent_system_prompt` dos
--            agentes de ATENDIMENTO contradiz a D8 do Founder (o agente só chama pessoa
--            quando precisa; em dúvida, pergunta ao segurado ou responde com o que sabe).
--            A F7 pôs a autonomia no prompt do CÓDIGO; esta migration troca a FRASE do
--            banco — e só ela. Nada mais do texto de cada corretora muda.
--
-- 📊 ANTES (30/09/2026, SELECT read-only pelo MCP, agent_role='attendance'):
--    4 agentes, TODOS is_active=false, todos com company_id; cada um com EXATAMENTE 1
--    ocorrência da frase antiga e 0 da nova:
--      3 × 'em duvida, encaminhe a um atendente humano da corretora.'   (len 1535/1535/1533)
--      1 × 'em duvida, encaminhe a {{handoff_target}}.'                 (len 813, com variáveis)
--    md5 de cada texto ANTES (a prova do ROLLBACK exato — sem guardar o texto da corretora
--    no repositório, CLAUDE.md §13.9):
--      114005e16f3bede94196de7c0b6798d3 · a314fbcad23867b2a2ddc22546177f1b
--      00ac0f3bd8626141ddefafbe3fdf044a · f16490391ace7af2227fea16e663ce90
--
-- 🔴 MULTI-CORRETORA (§13.9): a frase nova não tem nome de corretora, de pessoa nem de
--    número; quem a recebe é escolhido pelo papel (`agent_role='attendance'`), nunca por id.
-- 🔴 DADO, NÃO ESTRUTURA: UPDATE de texto em 4 linhas; nenhuma coluna, CHECK, RLS ou GRANT.
--    Idempotente (o WHERE exige a frase antiga; rodar de novo não muda nada).
-- ⚠️ FORA DESTA MIGRATION: o molde de agente novo (`lib/admin/agent-blueprints-canonical.ts:115`)
--    ainda tem a frase antiga — um agente criado amanhã nasce com ela (registrado no relatório).
--
-- APPLY:  troca, por `replace`, a frase antiga pela nova nas duas formas, só em
--         agent_role='attendance' e só onde a antiga existe; um DO confere que nenhuma
--         antiga sobrou e que cada linha trocada tem exatamente UMA nova (senão aborta tudo).
-- VERIFY: (1) antigas=0 · novas=4 · (2) o texto de cada agente, com a frase nova trocada de volta
--         pela antiga, tem o md5 de ANTES (prova que só a frase mudou) · (3) is_active intacto.
-- ROLLBACK: o `replace` inverso (frase nova → antiga), nas duas formas; a prova é o md5 de ANTES.
-- =============================================================

-- ─────────────────────────────── APPLY ───────────────────────────────
begin;

update public.agents
   set agent_system_prompt = replace(agent_system_prompt,
         'em duvida, encaminhe a um atendente humano da corretora.',
         'em duvida, pergunte ao segurado o que falta ou responda com o que sabe, dizendo quando nao tiver certeza; encaminhe a um atendente humano da corretora em sinistro, condominio, empresarial, servico sem corredor de acionamento ou quando o cliente pedir.')
 where agent_role = 'attendance'
   and agent_system_prompt like '%em duvida, encaminhe a um atendente humano da corretora.%';

update public.agents
   set agent_system_prompt = replace(agent_system_prompt,
         'em duvida, encaminhe a {{handoff_target}}.',
         'em duvida, pergunte ao segurado o que falta ou responda com o que sabe, dizendo quando nao tiver certeza; encaminhe a {{handoff_target}} em sinistro, condominio, empresarial, servico sem corredor de acionamento ou quando o cliente pedir.')
 where agent_role = 'attendance'
   and agent_system_prompt like '%em duvida, encaminhe a {{handoff_target}}.%';

do $$
declare
  v_antigas int;
  v_dupla   int;
begin
  select count(*) into v_antigas from public.agents
   where agent_role = 'attendance' and agent_system_prompt like '%em duvida, encaminhe a %';
  select count(*) into v_dupla from public.agents
   where agent_role = 'attendance'
     and (length(agent_system_prompt) - length(replace(agent_system_prompt, 'em duvida, pergunte ao segurado o que falta', '')))
         / length('em duvida, pergunte ao segurado o que falta') > 1;
  if v_antigas <> 0 or v_dupla <> 0 then
    raise exception 'APPLY 20260930_05 abortado: antigas=% duplicadas=%', v_antigas, v_dupla;
  end if;
end $$;

commit;

-- ─────────────────────────────── VERIFY (read-only) ───────────────────────────────
-- select count(*) filter (where agent_system_prompt like '%em duvida, encaminhe a %')                    as antigas,  -- 0
--        count(*) filter (where agent_system_prompt like '%em duvida, pergunte ao segurado o que falta%')  as novas,    -- 4
--        count(*) filter (where is_active)                                                               as ativos,   -- 0
--        array_agg(md5(replace(replace(agent_system_prompt,
--          'em duvida, pergunte ao segurado o que falta ou responda com o que sabe, dizendo quando nao tiver certeza; encaminhe a um atendente humano da corretora em sinistro, condominio, empresarial, servico sem corredor de acionamento ou quando o cliente pedir.',
--          'em duvida, encaminhe a um atendente humano da corretora.'),
--          'em duvida, pergunte ao segurado o que falta ou responda com o que sabe, dizendo quando nao tiver certeza; encaminhe a {{handoff_target}} em sinistro, condominio, empresarial, servico sem corredor de acionamento ou quando o cliente pedir.',
--          'em duvida, encaminhe a {{handoff_target}}.')) order by 1) as md5_de_antes
--   from public.agents where agent_role = 'attendance';
-- esperado md5_de_antes = {00ac0f3bd8626141ddefafbe3fdf044a,114005e16f3bede94196de7c0b6798d3,
--                          a314fbcad23867b2a2ddc22546177f1b,f16490391ace7af2227fea16e663ce90}

-- ─────────────────────────────── ROLLBACK (escrito ANTES de aplicar) ───────────────────────────────
-- begin;
-- update public.agents set agent_system_prompt = replace(agent_system_prompt,
--   'em duvida, pergunte ao segurado o que falta ou responda com o que sabe, dizendo quando nao tiver certeza; encaminhe a um atendente humano da corretora em sinistro, condominio, empresarial, servico sem corredor de acionamento ou quando o cliente pedir.',
--   'em duvida, encaminhe a um atendente humano da corretora.')
--  where agent_role = 'attendance';
-- update public.agents set agent_system_prompt = replace(agent_system_prompt,
--   'em duvida, pergunte ao segurado o que falta ou responda com o que sabe, dizendo quando nao tiver certeza; encaminhe a {{handoff_target}} em sinistro, condominio, empresarial, servico sem corredor de acionamento ou quando o cliente pedir.',
--   'em duvida, encaminhe a {{handoff_target}}.')
--  where agent_role = 'attendance';
-- -- prova: array_agg(md5(agent_system_prompt) order by 1) = o conjunto de md5 de ANTES acima
-- commit;
