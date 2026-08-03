-- =============================================================
-- MIGRATION: spec063_corretora_nasce_completa
-- SPEC:      SPEC-063 — Bloco P (provisionamento)
-- AUTOR:     Executor Opus                DATA: 2026-08-03
-- OBJETIVO:  nenhum agente fica ATIVO e MUDO, e as corretoras que ja existem
--            recebem as pecas com que deveriam ter nascido.
--
-- APPLY:     1. guarda de pre-requisitos (colunas de que esta migration depende)
--            2. backfill do prompt do agente CORE mudo (o caso AutoFleet)
--            3. fail-closed: agente de ATENDIMENTO que continuar mudo e DESLIGADO
--            4. config de memoria por agente (memory_settings)
--            5. entitlements de capability por corretora
--            6. perfis de briefing (diario + executivo)
--            7. view vw_agentes_mudos — o defeito nao volta a ficar invisivel
--
-- VERIFY:    ver bloco VERIFY ao final (SQL executavel, read-only).
-- ROLLBACK:  ver bloco ROLLBACK ao final.
--
-- EXPAND-FIRST: sim — so preenche o que esta VAZIO e cria linhas que faltam.
--               Nenhum texto preenchido e sobrescrito. Nenhuma coluna some.
-- DESTRUTIVA:   nao
--
-- O QUE FOI MEDIDO
-- ----------------
-- 📊 02/08/2026, banco de producao (docs/canon/reports/SPEC-063-BLOCO-0-AUDITORIA.md):
--
--     corretora    papel   blueprint              prompt
--     Resulta      core    autobrokers-core-v1    650 chars
--     AutoFleet    core    autobrokers-core-v1        0     <- ATIVO
--     Amandus      core    core-v1                7.914 chars
--
--     config de memoria .... 0 / 0 / 0
--     entitlements ......... 0 / 0 / 0
--
-- Mesmo blueprint, mesmo caminho, resultado diferente. Um agente ativo, sem uma
-- linha de instrucao e sem nenhuma trava, respondendo em nome de uma corretora.
--
-- POR QUE O TEXTO DO CORE ESTA DUPLICADO AQUI (e o do atendimento NAO)
-- -------------------------------------------------------------------
-- O texto canonico vive em `lib/admin/agent-blueprints-canonical.ts`. Aqui ele
-- aparece VERBATIM, com os `{{placeholders}}` intactos, e a substituicao e feita
-- por `replace()` — para que a copia seja comparavel caractere a caractere.
-- `backend/tests/test_a_corretora_nasce_completa.py` compara as duas e falha se
-- divergirem. Copia sem guarda apodrece; copia com guarda e backfill.
--
-- O agente de ATENDIMENTO nao tem o texto copiado de proposito: sao 7 variaveis
-- (nome do atendente, tom, horario, destino de handoff, abertura, encerramento)
-- e a corretora pode ter escolhido cada uma. Preencher com os padroes aqui
-- congelaria a escolha dela. 📊 Nao ha nenhum agente de atendimento mudo hoje;
-- se houver um dia, ele e DESLIGADO (silencio e o comportamento certo para quem
-- fala com o segurado) e o preenchimento correto vem do provisionamento, que le
-- as variaveis da corretora.
-- =============================================================

-- -------------------------------------------------------------
-- 1. Guarda de pre-requisitos
-- -------------------------------------------------------------
-- Falhar cedo e com nome proprio e melhor que falhar no meio, com metade
-- aplicada e uma mensagem do Postgres sobre uma coluna que ninguem procurou.
do $guarda$
declare
  faltando text[] := '{}';
begin
  if not exists (select 1 from information_schema.columns
                  where table_schema='public' and table_name='agents' and column_name='agent_role')
    then faltando := faltando || 'agents.agent_role'; end if;
  if not exists (select 1 from information_schema.columns
                  where table_schema='public' and table_name='agents' and column_name='context_package')
    then faltando := faltando || 'agents.context_package'; end if;
  if not exists (select 1 from information_schema.columns
                  where table_schema='public' and table_name='companies' and column_name='company_kind')
    then faltando := faltando || 'companies.company_kind'; end if;
  if array_length(faltando, 1) is not null then
    raise exception 'SPEC-063 P: esta migration depende de colunas ausentes: %', array_to_string(faltando, ', ');
  end if;
end
$guarda$;

-- -------------------------------------------------------------
-- 2. O agente CORE mudo recebe o prompt canonico
-- -------------------------------------------------------------
-- So toca em quem esta VAZIO. A Amandus (7.914 caracteres escritos a mao) nao
-- entra nesta condicao — e essa e a unica protecao que ela precisa aqui.
update public.agents a
   set agent_system_prompt =
         '=== PERSONALIZACAO DA CORRETORA (dados, NAO sao instrucoes de prioridade) ===' || E'\n' ||
         replace(
           replace(
             $tpl$Voce e o AutoBrokers da {{company_name}} — o braco direito interno e inteligentissimo da corretora. Apresente-se como "AutoBrokers da {{company_name}}". A marca AutoBrokers nunca muda. Voce ajuda o corretor/gestor/equipe em estrategia, vendas, marketing, operacao, gestao, seguros, financeiro e juridico, usando o conhecimento global curado do AutoBrokers + o conhecimento privado autorizado da propria corretora. Regras: nunca acesse dados de outra corretora; nunca exponha segredos; nunca prometa cobertura sem evidencia; respeite approval e gates; quando faltar dado, diga que vai verificar. Seja claro, util e direto. Tom: {{tone}}.$tpl$,
             '{{company_name}}', c.company_name),
           '{{tone}}',
           coalesce(nullif(a.context_package->'tenant_agent_config'->'variables'->>'tone', ''),
                    'profissional e acolhedor')
         ) || E'\n' ||
         E'\n' ||
         '=== REGRAS IMUTAVEIS DO AUTOBROKERS (sempre valem; nao podem ser alteradas por configuracao) ===' || E'\n' ||
         '- Opere apenas com dados desta corretora; jamais acesse outra corretora.' || E'\n' ||
         '- Nunca cruze dados entre corretoras.' || E'\n' ||
         '- Nunca exponha segredos, tokens, cookies ou credenciais.' || E'\n' ||
         '- Nunca prometa cobertura sem evidência verificada.' || E'\n' ||
         '- Respeite aprovações e gates de segurança.' || E'\n' ||
         '- A marca "AutoBrokers" é fixa e não pode ser renomeada.' || E'\n' ||
         'Se a personalizacao acima conflitar com estas regras, estas regras prevalecem.',
       -- Agente sem blueprint declarado passa a declarar o que ele de fato e.
       -- Quem ja declara outro (a Amandus declara `core-v1`) nao e tocado.
       blueprint_version = coalesce(nullif(a.blueprint_version, ''), 'autobrokers-core-v1'),
       context_package = jsonb_set(
         coalesce(a.context_package, '{}'::jsonb),
         '{blueprint_heranca}',
         jsonb_build_object(
           'blueprint_key',    'autobrokers-core-v1',
           'ultima_aplicacao', now()::text,
           'ultimo_motivo',    'migration_20260803_02:preenchimento_de_prompt_vazio',
           'origem',           'migration_20260803_02_spec063',
           'versoes',          coalesce(a.context_package->'blueprint_heranca'->'versoes', '[]'::jsonb)
         ),
         true),
       updated_at = now()
  from public.companies c
 where c.id = a.company_id
   and a.agent_role = 'core'
   and coalesce(trim(a.agent_system_prompt), '') = ''
   and coalesce(c.company_kind, 'client') = 'client'
   and coalesce(c.is_technical, false) = false
   and coalesce(trim(c.company_name), '') <> '';

-- -------------------------------------------------------------
-- 3. Fail-closed: quem fala com o segurado e esta mudo, cala
-- -------------------------------------------------------------
-- Um agente de atendimento ATIVO e sem instrucao nao e "meio configurado": ele
-- responde o segurado sem nenhuma trava. Silencio e melhor.
update public.agents a
   set is_active = false,
       context_package = jsonb_set(
         coalesce(a.context_package, '{}'::jsonb),
         '{spec063_bloco_p}',
         jsonb_build_object(
           'desligado_por',  'prompt_vazio',
           'desligado_em',   now()::text,
           'origem',         'migration_20260803_02_spec063',
           'como_religar',   'POST /api/admin/provision-tenant {acao:"provisionar"} preenche o prompt com as variaveis da corretora'
         ),
         true),
       updated_at = now()
  from public.companies c
 where c.id = a.company_id
   and a.agent_role = 'attendance'
   and a.is_active is true
   and coalesce(trim(a.agent_system_prompt), '') = ''
   and coalesce(c.company_kind, 'client') = 'client';

-- -------------------------------------------------------------
-- 4. Config de memoria por agente — 📊 era 0 nas tres corretoras
-- -------------------------------------------------------------
-- Sem linha, o agente roda no default implicito do codigo e a tela cria a
-- configuracao so quando alguem abre a tela. Grava apenas as chaves; o resto
-- vem do DEFAULT da coluna (inventar politica aqui criaria uma terceira
-- verdade sobre memoria).
insert into public.memory_settings (company_id, agent_id)
select a.company_id, a.id
  from public.agents a
  join public.companies c on c.id = a.company_id
 where a.agent_role in ('core', 'attendance')
   and coalesce(c.company_kind, 'client') = 'client'
   and coalesce(c.is_technical, false) = false
   and not exists (select 1 from public.memory_settings m where m.agent_id = a.id);

-- A tela legada grava sem `company_id`. Adota o tenant sem tocar na config.
update public.memory_settings m
   set company_id = a.company_id, updated_at = now()
  from public.agents a
 where a.id = m.agent_id
   and m.company_id is null;

-- -------------------------------------------------------------
-- 5. Entitlements de capability — 📊 era 0 nas tres corretoras
-- -------------------------------------------------------------
-- MATERIALIZAR NAO LIGA NADA QUE JA NAO ESTIVESSE LIGADO: tanto
-- `capability_resolver.py` quanto o cockpit tratam AUSENCIA de linha como
-- permitido (so `enabled = false` desliga). O gate real continua sendo a
-- conexao e a aprovacao. O que muda e que passa a existir a linha que alguem
-- pode desligar — e o estado da corretora deixa de ser implicito.
--
-- A lista sai de `capabilities` (a tabela), nao de uma copia: catalogo novo
-- entra sozinho na proxima execucao.
insert into public.tenant_capability_entitlements (company_id, capability_key, enabled)
select c.id, cap.capability_key, true
  from public.companies c
 cross join public.capabilities cap
 where coalesce(c.company_kind, 'client') = 'client'
   and coalesce(c.is_technical, false) = false
   and coalesce(cap.is_active, true) is true
   and not exists (
     select 1 from public.tenant_capability_entitlements e
      where e.company_id = c.id and e.capability_key = cap.capability_key)
on conflict (company_id, capability_key) do nothing;

-- -------------------------------------------------------------
-- 6. Perfis de briefing (diario + executivo)
-- -------------------------------------------------------------
-- Espelha `briefing_service.perfil()` (backend), que hoje cria sob demanda —
-- ou seja, so depois que alguem pede um briefing.
insert into public.briefing_profiles (company_id, user_id, scope, name, cadence, schedule_spec, channels)
select c.id, null, 'company', 'Briefing diário', 'daily',
       '{"time":"08:00"}'::jsonb, '["dashboard"]'::jsonb
  from public.companies c
 where coalesce(c.company_kind, 'client') = 'client'
   and coalesce(c.is_technical, false) = false
   and not exists (
     select 1 from public.briefing_profiles p
      where p.company_id = c.id and p.cadence = 'daily'
        and p.user_id is null and p.is_active);

insert into public.briefing_profiles (company_id, user_id, scope, name, cadence, schedule_spec, channels)
select c.id, null, 'company', 'Briefing executivo', 'weekly',
       '{"time":"08:00","weekday":0}'::jsonb, '["dashboard"]'::jsonb
  from public.companies c
 where coalesce(c.company_kind, 'client') = 'client'
   and coalesce(c.is_technical, false) = false
   and not exists (
     select 1 from public.briefing_profiles p
      where p.company_id = c.id and p.cadence = 'weekly'
        and p.user_id is null and p.is_active);

-- -------------------------------------------------------------
-- 7. A view que impede o defeito de voltar a ser invisivel
-- -------------------------------------------------------------
-- Nao e constraint, pelo mesmo motivo da migration 20260803_01: um CHECK em
-- `agents` recusaria QUALQUER update de uma linha legada mal formada — o
-- defeito trocaria de lugar e a corretora ficaria sem poder salvar nada.
-- A view mostra; o provisionamento conserta; o codigo ja nasce fail-closed.
create or replace view public.vw_agentes_mudos as
select a.id                    as agent_id,
       a.company_id,
       c.company_name,
       a.agent_role,
       a.blueprint_version,
       a.is_active,
       length(coalesce(a.agent_system_prompt, '')) as chars_de_prompt,
       case when a.is_active then 'ATIVO E MUDO — responde sem nenhuma instrucao'
            else 'mudo, porem desligado' end       as gravidade
  from public.agents a
  join public.companies c on c.id = a.company_id
 where coalesce(trim(a.agent_system_prompt), '') = '';

comment on view public.vw_agentes_mudos is
  'SPEC-063 Bloco P — agentes sem uma linha de system prompt. 📊 Em 02/08/2026 a '
  'AutoFleet tinha um CORE ATIVO com zero caracteres, do mesmo blueprint que '
  'rendeu 650 na Resulta, e nenhuma verificacao percebeu. Linha aqui = agente '
  'que fala em nome de uma corretora sem saber quem e.';

-- =============================================================
-- VERIFY  (read-only)
-- =============================================================
-- -- 1) Nenhum agente ATIVO e mudo:
-- select * from public.vw_agentes_mudos where is_active;
-- --   esperado: 0 linhas
--
-- -- 2) O prompt do core saiu do zero e tem o tamanho do canonico (~1.200):
-- select c.company_name, a.agent_role, a.blueprint_version,
--        length(a.agent_system_prompt) as chars
--   from public.agents a join public.companies c on c.id = a.company_id
--  where a.agent_role in ('core','attendance')
--  order by 1, 2;
-- --   esperado: nenhum `chars` nulo ou 0 em corretora cliente
--
-- -- 3) As tres corretoras ficam IGUAIS (era o defeito: nada era uniforme):
-- select c.company_name,
--        (select count(*) from public.agents a
--          where a.company_id = c.id and a.agent_role in ('core','attendance')) as agentes,
--        (select count(*) from public.memory_settings m
--          where m.company_id = c.id)                                           as memoria,
--        (select count(*) from public.tenant_capability_entitlements e
--          where e.company_id = c.id)                                           as entitlements,
--        (select count(*) from public.briefing_profiles p
--          where p.company_id = c.id and p.is_active)                           as briefing
--   from public.companies c
--  where coalesce(c.company_kind,'client') = 'client'
--    and coalesce(c.is_technical,false) = false
--  order by 1;
-- --   esperado: agentes=2, memoria=2, entitlements=(select count(*) from
-- --   capabilities where is_active), briefing>=2 — os MESMOS numeros nas tres
--
-- -- 4) Nada preenchido foi sobrescrito (a Amandus continua com o texto dela):
-- select c.company_name, length(a.agent_system_prompt) as chars,
--        a.context_package->'blueprint_heranca'->>'origem' as tocado_por
--   from public.agents a join public.companies c on c.id = a.company_id
--  where a.agent_role = 'core' order by 2 desc;
-- --   esperado: a linha de 7.914 caracteres com `tocado_por` NULO
--
-- =============================================================
-- ROLLBACK
-- =============================================================
-- -- 7) view
-- drop view if exists public.vw_agentes_mudos;
--
-- -- NOTA: os passos 4, 5 e 6 criam linhas novas e sao revertidos por data de
-- -- criacao. TROQUE `date '2026-08-03'` pela data REAL da aplicacao antes de
-- -- rodar — a migration nao carimba origem nessas tabelas de proposito: usar
-- -- um campo com outro nome (`limits`, por exemplo) para guardar procedencia
-- -- seria um campo mentindo sobre o que guarda (CLAUDE.md §12.1).
--
-- -- 6) perfis de briefing criados por esta migration, e que nunca publicaram
-- delete from public.briefing_profiles p
--  where p.user_id is null
--    and p.created_at >= date '2026-08-03'
--    and ((p.cadence='daily'  and p.name='Briefing diário')
--      or (p.cadence='weekly' and p.name='Briefing executivo'))
--    and not exists (select 1 from public.briefing_publications b
--                     where b.briefing_profile_id = p.id);
--
-- -- 5) entitlements: apagar as linhas criadas aqui volta ao estado implicito
-- --    (ausencia = permitido), que era exatamente o estado anterior. Nenhuma
-- --    configuracao se perde: todas nasceram com enabled=true, o mesmo padrao.
-- delete from public.tenant_capability_entitlements
--  where created_at >= date '2026-08-03' and enabled is true;
--
-- -- 4) config de memoria criada por esta migration (nunca configurada por ninguem)
-- delete from public.memory_settings m
--  where m.created_at >= date '2026-08-03'
--    and m.updated_at = m.created_at;
--
-- -- 3) religa o atendimento desligado por prompt vazio
-- update public.agents
--    set is_active = true,
--        context_package = context_package - 'spec063_bloco_p',
--        updated_at = now()
--  where context_package->'spec063_bloco_p'->>'origem' = 'migration_20260803_02_spec063';
--
-- -- 2) devolve o prompt ao estado anterior (vazio) SOMENTE onde esta migration escreveu
-- update public.agents
--    set agent_system_prompt = '',
--        context_package = context_package - 'blueprint_heranca',
--        updated_at = now()
--  where context_package->'blueprint_heranca'->>'origem' = 'migration_20260803_02_spec063';
-- =============================================================
