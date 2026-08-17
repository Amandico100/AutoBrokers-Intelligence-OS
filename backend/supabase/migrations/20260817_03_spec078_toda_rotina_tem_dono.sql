-- =============================================================
-- MIGRATION: spec078_toda_rotina_tem_dono
-- SPEC:      SPEC-078 — Bloco C.1 e C.2
-- AUTOR:     Claude Opus 5                     DATA: 2026-08-17
-- OBJETIVO:  Fazer da regra canônica uma ESTRUTURA, não uma faxina.
--
-- APPLY:     ✅ APLICADA em 17/08/2026 ~14:4x UTC, projeto dcajcvlzcjbmyapmklil,
--            em 4 chamadas (`apply_migration` NÃO é transacional — medido na
--            SPEC-075; cada bloco é idempotente por si).
-- VERIFY:    ✅ rodado. Saída real no bloco VERIFY ao final.
-- ROLLBACK:  bloco ao final. Reversível sem perda.
--
-- ⚠️ DUAS CORREÇÕES DE TIPO descobertas ao aplicar, e registradas porque o
-- próximo a semear Auxiliar vai tropeçar nas mesmas:
--
--     categories           é text[]  — NÃO jsonb   (erro 42804)
--     required_connectors  é text[]  — NÃO jsonb
--     what_it_does         é jsonb   — array de frases, não texto (erro 22P02)
--     value_promise        é text
--
-- Eu havia escrito `'["tempo_livre"]'::jsonb` nas duas primeiras e uma frase
-- solta na terceira. O banco recusou as duas vezes, e está certo: o schema é a
-- autoridade, não a minha memória dele.
--
-- EXPAND-FIRST: sim
-- DESTRUTIVA:   não — não apaga nenhuma linha, não apaga nenhuma coluna
-- =============================================================
--
-- POR QUE ESTA MIGRATION EXISTE
--
-- `ONTOLOGIA-DO-TRABALHO.md:51`  "Rotina nunca existe sozinha."
-- `GLOSSARIO.md:18`              "routines (sempre com tenant_auxiliary_id)"
--
-- Em 02/08/2026 a `20260802_03_spec064_rotina_tem_dono.sql` fez esse corolário
-- valer NOS DADOS: deu dono à rotina que existia, casando por
-- `name ilike '%cobran%'`. E parou ali — não pôs constraint nenhuma.
--
-- 📊 MEDIDO EM 17/08/2026, quinze dias depois:
--
--     routines.tenant_auxiliary_id   nullable, sem default, sem NOT NULL
--     rotinas no sistema             2
--     rotinas SEM dono               1  ← criada em 17/08 às 13:01
--
-- A órfã pertence à corretora `6c9c55e2…`, que TEM `cobranca-feita` instalada.
-- Os dois lado a lado, sem se conhecerem: `lib/auxiliaries/catalog.ts:239-242`
-- conta rotinas por `tenant_auxiliary_id`, então o card diz "Nenhuma rotina
-- ainda" enquanto uma rotina de cobrança está agendada.
--
-- 📊 E não é descuido pontual: o repositório inteiro tem 42 linhas mencionando
-- `tenant_auxiliary_id` e **NENHUMA delas escreve a coluna em `routines`**. Os
-- quatro escritores de rotina (tela, chat, monitor, radar) não preenchem o dono.
-- Não existe caminho de código no produto que dê dono a uma rotina nova.
--
-- Corrigir os dados de novo produziria uma terceira órfã em setembro. Por isso
-- aqui a regra vira CONSTRAINT: o banco passa a recusar rotina sem dono.
-- =============================================================


-- -------------------------------------------------------------------------
-- 1. O AUXILIAR DE PLATAFORMA QUE TORNA O `NOT NULL` POSSÍVEL
--
-- Sem ele o NOT NULL é impossível, e a razão é um caso legítimo:
--
--     "todo dia às 8h me manda um resumo das notícias"
--
-- pedido no chat, gravado com `visibility='personal'`. Isso não é trabalhador
-- de catálogo — é instrução pessoal e descartável.
--
-- Transformar cada uma dessas num Auxiliar quebraria TRÊS regras de uma vez:
--   `ONTOLOGIA:209`  ✗ Auxiliar nascendo fora do catálogo
--   SPEC-064 G.2.4   "o chat nunca cria algo global"
--   `ONTOLOGIA:101`  não existe "Auxiliar pessoal" no cânone
--
-- A saída é UM Auxiliar de plataforma que seja dono de todas elas. Um, não um
-- por pedido — o catálogo não incha, e o corretor ganha um lugar óbvio para ver
-- "as coisinhas que eu pedi no chat".
-- -------------------------------------------------------------------------
insert into public.auxiliary_templates
  (slug, name, category, short_description, description, headline,
   catalog_state, status, execution_mode, trigger_type,
   requires_human_approval, uses_external_actions, version, is_active,
   categories, required_connectors, what_it_does, value_promise,
   default_config, permissions)
values
  ('tarefas-agendadas',
   'Tarefas Agendadas',
   'produtividade',
   'As tarefas recorrentes que você pediu no chat.',
   'Guarda as tarefas recorrentes que você criou conversando — "todo dia às 8h '
   'me manda...". Cada uma vira uma rotina com horário próprio, e todas ficam '
   'aqui, num lugar só, para você ver, pausar ou apagar.',
   'O que você pediu no chat, acontecendo sozinho, num lugar só',
   'available', 'active', 'scheduled', 'scheduled',
   false, false, 1, true,
   -- 🔴 text[], não jsonb. O banco recusou `'[...]'::jsonb` com 42804.
   array['tempo_livre']::text[],
   array[]::text[],
   -- 🔴 jsonb, e é um ARRAY DE FRASES, não uma frase. Recusou com 22P02.
   jsonb_build_array(
     'Executa no horario que voce pediu, sem voce lembrar',
     'Guarda num lugar so tudo que voce pediu pelo chat',
     'Deixa voce pausar ou apagar qualquer uma quando quiser'),
   'Voce para de lembrar de pedir a mesma coisa toda semana.',
   jsonb_build_object(
     'runtime',    jsonb_build_object('kind', 'workflow', 'workflow', 'bridge.routine.execute'),
     'visibility', jsonb_build_object('type', 'global'),
     'spec',       'SPEC-078'
   ),
   '[]'::jsonb)
on conflict (slug) do nothing;


-- -------------------------------------------------------------------------
-- 2. INSTALADO EM TODA CORRETORA
--
-- 🔴 Nasce `inactive`, NÃO `active`. Um Auxiliar que nasce ligado é um
-- trabalhador que ninguém contratou. Ele fica disponível e parado; as rotinas
-- que já existem seguem governadas pelo `is_active` DELAS até o Bloco A.3
-- passar a exigir o dono ligado.
--
-- ⚠️ `display_name` NÃO entra neste INSERT. A coluna não existe em
-- `tenant_auxiliaries` — foi ela que produziu o `install_failed` de 17/08.
-- -------------------------------------------------------------------------
insert into public.tenant_auxiliaries
  (company_id, template_id, slug, name, status, config, permissions)
select c.id, t.id, t.slug, t.name, 'inactive',
       jsonb_build_object('runtime', t.default_config->'runtime'),
       '[]'::jsonb
  from public.companies c
 cross join public.auxiliary_templates t
 where t.slug = 'tarefas-agendadas'
   and not exists (
     select 1 from public.tenant_auxiliaries ta
      where ta.company_id = c.id and ta.slug = 'tarefas-agendadas'
   );


-- -------------------------------------------------------------------------
-- 3. BACKFILL — cada órfã encontra o dono CERTO, não um dono qualquer
--
-- A ordem importa. Jogar tudo em `tarefas-agendadas` seria rápido e erraria:
-- uma rotina de cobrança pertence ao Auxiliar de Cobrança, e é dele que o
-- corretor espera vê-la. `tarefas-agendadas` é o destino de quem NÃO tem dono
-- natural, não o depósito de quem tem.
-- -------------------------------------------------------------------------

-- 3.a — rotina de cobrança vai para o Auxiliar de Cobrança da MESMA corretora.
--       (📊 é o caso da órfã de 17/08: kind=billing_collection, e a corretora
--        tem `cobranca-feita` instalada.)
update public.routines r
   set tenant_auxiliary_id = ta.id
  from public.tenant_auxiliaries ta
 where r.tenant_auxiliary_id is null
   and r.config->>'kind' = 'billing_collection'
   and ta.company_id = r.company_id
   and ta.slug = 'cobranca-feita';

-- 3.b — o Radar grava o dono como STRING dentro de um JSONB
--       (`research/radar.py:152-154`, `config.auxiliar`). É exatamente o
--       defeito do CLAUDE.md §12.1: o campo mente sobre o que guarda. Aqui a
--       string vira a COLUNA; o código deixa de escrever no lugar errado no
--       Bloco C.3.
update public.routines r
   set tenant_auxiliary_id = ta.id
  from public.tenant_auxiliaries ta
 where r.tenant_auxiliary_id is null
   and r.config->>'auxiliar' is not null
   and ta.company_id = r.company_id
   and ta.slug = r.config->>'auxiliar';

-- 3.c — todo o resto vai para `tarefas-agendadas`.
update public.routines r
   set tenant_auxiliary_id = ta.id
  from public.tenant_auxiliaries ta
 where r.tenant_auxiliary_id is null
   and ta.company_id = r.company_id
   and ta.slug = 'tarefas-agendadas';


-- -------------------------------------------------------------------------
-- 4. A FK PRECISA MUDAR ANTES DO NOT NULL — E ESTE É O DETALHE QUE PEGA
--
-- 📊 A FK já existe, e ela é INCOMPATÍVEL com NOT NULL:
--
--     routines_tenant_auxiliary_id_fkey
--       FOREIGN KEY (tenant_auxiliary_id)
--       REFERENCES tenant_auxiliaries(id) ON DELETE SET NULL
--
-- Apagar um Auxiliar faria o Postgres tentar gravar NULL numa coluna NOT NULL
-- e a exclusão explodiria com erro de constraint — no meio de uma operação de
-- produto, sem explicação para quem clicou.
--
-- `RESTRICT` é a semântica honesta: Auxiliar com rotina não é apagado; a rotina
-- é apagada ou movida primeiro. Isso é o que o produto já quer dizer — desligar
-- é `status`, não `delete`.
-- -------------------------------------------------------------------------
alter table public.routines
  drop constraint if exists routines_tenant_auxiliary_id_fkey;

alter table public.routines
  add constraint routines_tenant_auxiliary_id_fkey
  foreign key (tenant_auxiliary_id)
  references public.tenant_auxiliaries(id)
  on delete restrict;


-- -------------------------------------------------------------------------
-- 5. A TRAVA
--
-- 🔴 Este é o statement que impede a quarta regressão. Se ele falhar, é porque
-- sobrou órfã — e nesse caso é para PARAR e olhar, nunca para relaxar a regra.
-- -------------------------------------------------------------------------
alter table public.routines
  alter column tenant_auxiliary_id set not null;


-- -------------------------------------------------------------------------
-- 6. E o dono tem de ser da MESMA corretora
--
-- Sem isto, o NOT NULL garante que existe dono e não garante que o dono é
-- daquela corretora — uma rotina da AutoFleet poderia apontar para um Auxiliar
-- da Resulta e atravessar o isolamento (CLAUDE.md §7).
--
-- O padrão de FK composta já é usado nesta mesma tabela:
--     fk_routines_agent_same_company (agent_id, company_id) → agents
-- -------------------------------------------------------------------------
create unique index if not exists ux_tenant_auxiliaries_id_company
  on public.tenant_auxiliaries (id, company_id);

alter table public.routines
  drop constraint if exists fk_routines_auxiliary_same_company;

alter table public.routines
  add constraint fk_routines_auxiliary_same_company
  foreign key (tenant_auxiliary_id, company_id)
  references public.tenant_auxiliaries(id, company_id)
  on delete restrict;


-- =============================================================
-- 📊 VERIFY — SAÍDA REAL, 17/08/2026 logo após o APPLY:
--
--     orfas                              0
--     rotinas_total                      2
--     rotinas_ativas                     0
--     coluna_ainda_nullable              0
--     corretoras_sem_tarefas_agendadas   0   (5 de 5 instaladas)
--     dono_de_outra_corretora            0
--     agentes_atendimento_ligados        0
--
-- E as DUAS provas de que a trava MORDE — sem elas o VERIFY acima passaria
-- igual num banco onde a constraint nem existisse:
--
--     insert sem dono            → ERRO 23502 null value in column
--                                  "tenant_auxiliary_id" violates not-null
--     insert com dono de OUTRA   → ERRO 23503 violates foreign key constraint
--     corretora                    "fk_routines_auxiliary_same_company"
--
-- E o CONTROLE, que é o que dá direito à conclusão: um insert VÁLIDO
-- (dono certo, mesma corretora) **passou** — e foi apagado em seguida.
-- Sem ele, uma constraint que recusasse tudo teria o mesmo placar.
--
-- ⚠️ Nota de método: tentei fazer insert+delete num CTE só e o `delete` NÃO
-- enxergou a linha do `insert` (Postgres: CTEs veem o mesmo snapshot). A linha
-- de prova ficou no banco até eu conferir e apagar em statement separado. Vale
-- para qualquer prova destrutiva futura: dois statements, e confira.
--
-- Os comandos, para repetir:
--
-- select 'orfas' as o, count(*) from public.routines where tenant_auxiliary_id is null
-- union all
-- select 'dono_de_outra_corretora', count(*)
--   from public.routines r join public.tenant_auxiliaries ta on ta.id = r.tenant_auxiliary_id
--  where ta.company_id <> r.company_id
-- union all
-- select 'corretoras_sem_tarefas_agendadas', count(*)
--   from public.companies c
--  where not exists (select 1 from public.tenant_auxiliaries ta
--                     where ta.company_id = c.id and ta.slug = 'tarefas-agendadas')
-- union all
-- select 'coluna_ainda_nullable', count(*)
--   from information_schema.columns
--  where table_name = 'routines' and column_name = 'tenant_auxiliary_id'
--    and is_nullable = 'YES';
--
-- ESPERADO: 0, 0, 0, 0.
--
-- E a prova de que a trava MORDE (sem ela o VERIFY acima passaria mesmo com a
-- coluna solta). Tem de levantar erro 23502:
--
-- insert into public.routines (company_id, name, instructions, schedule, delivery)
-- values ((select id from public.companies limit 1), 'prova', 'prova prova',
--         '{"kind":"daily","time":"09:00"}'::jsonb, '{"channel":"none"}'::jsonb);
-- -- ESPERADO: ERROR 23502 null value in column "tenant_auxiliary_id"
-- =============================================================


-- =============================================================
-- ROLLBACK — reverte sem perder nada. Não apaga rotina, não apaga auxiliar.
--
-- alter table public.routines alter column tenant_auxiliary_id drop not null;
-- alter table public.routines drop constraint if exists fk_routines_auxiliary_same_company;
-- alter table public.routines drop constraint if exists routines_tenant_auxiliary_id_fkey;
-- alter table public.routines
--   add constraint routines_tenant_auxiliary_id_fkey
--   foreign key (tenant_auxiliary_id) references public.tenant_auxiliaries(id)
--   on delete set null;
--
-- O auxiliar `tarefas-agendadas` e as instalações dele FICAM. Removê-los
-- deixaria rotinas apontando para linha inexistente — o rollback criaria um
-- problema pior que o original. Para desfazer também isso, mova as rotinas
-- para outro dono ANTES, e só então apague.
-- =============================================================
