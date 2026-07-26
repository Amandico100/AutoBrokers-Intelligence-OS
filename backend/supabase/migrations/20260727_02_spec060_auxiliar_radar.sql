-- =============================================================
-- MIGRATION: spec060_auxiliar_radar
-- SPEC:      SPEC-060 — §37 (Auxiliar global "Radar de Mercado e Regulacao")
-- AUTOR:     Executor Opus                DATA: 2026-07-27
-- OBJETIVO:  registrar o Auxiliar do Radar no catalogo global.
--
-- APPLY:     um insert idempotente (ON CONFLICT (slug) DO NOTHING) em
--            public.auxiliary_templates.
-- VERIFY:    ver bloco VERIFY ao final.
-- ROLLBACK:  ver bloco ROLLBACK ao final (delete por slug — so a linha desta
--            migration, nunca por LIKE).
--
-- EXPAND-FIRST: sim — so insere. Nenhuma linha existente e alterada.
-- DESTRUTIVA:   nao
--
-- POR QUE ESTA MIGRATION NAO SEMEIA CAPACIDADES, TOOLS NEM SKILLS
-- ---------------------------------------------------------------
-- Porque elas JA EXISTEM no banco, semeadas em 26/07/2026 com
-- `execution_manifest->>'spec' = 'SPEC-060'`:
--
--   capabilities  8, todas com binding para o papel `core`:
--                 search, extract, deep, monitor, places, site_audit,
--                 claim_verify, regulatory
--   tools         research.search_web, research.fetch_source,
--                 research.create_monitor, research.site_audit,
--                 research.search_places, research.verify_claims
--                 — todas publicadas e apontando para
--                   app.agents.tools.research_tool
--   skills        research.quick_verified_answer, research.deep_dossier,
--                 research.claim_verify, research.regulatory_watch,
--                 research.website_seo_aeo_audit,
--                 research.business_lead_discovery
--                 — todas 1.0.0 publicadas e ligadas ao `core`
--
-- A versao anterior deste arquivo criava um segundo conjunto com chaves
-- proprias (`research.search`, `research.monitor`, `research.answer_with_sources`,
-- `research.site_diagnosis`, `research.find_companies`). Duas consequencias,
-- as duas ruins:
--
--   1. o Tool Gateway passaria a ter DUAS ferramentas de busca com o mesmo
--      efeito e manifestos diferentes — e nada diria qual e a certa;
--   2. o teto de 12 tools por execucao seria consumido por duplicatas, o que
--      degrada a escolha do modelo em toda conversa.
--
-- CLAUDE.md §5: consolidar e migrar antes de duplicar. O codigo desta SPEC
-- depende de CAPABILITIES (`platform.research.*`), nao de tool_keys, entao
-- adotar o catalogo existente nao exigiu nenhuma mudanca de codigo.
-- Registrado em CHANGE-ADDENDA como CA-016.
-- =============================================================

-- -------------------------------------------------------------
-- Auxiliar global "Radar de Mercado e Regulacao" — §37
-- -------------------------------------------------------------
--
-- Ele nao tem agendador, monitor nem compositor proprios:
--
--   instalar  -> MonitorService cria os monitores, cada um preso a uma Rotina
--   verificar -> routine_engine dispara research.monitor_check
--   fechar    -> uma Rotina declara `config.workflow = research.radar_weekly`
--   entregar  -> Artifact Hub compõe, Intelligence Fabric avisa
--
-- O Auxiliar e o NOME que a corretora reconhece para esse conjunto — que e
-- exatamente o que a §37 pede que um Auxiliar seja.
insert into public.auxiliary_templates
  (slug, name, category, short_description, description, icon, status,
   execution_mode, trigger_type, requires_human_approval,
   uses_external_actions, default_config, permissions, is_active)
values
  ('radar-mercado-regulacao',
   'Radar de Mercado e Regulacao',
   'mercado',
   'Avisa quando a regulacao de seguros muda, antes do cliente perguntar.',
   E'Acompanha as fontes oficiais do setor — SUSEP, CNSP e legislacao — e '
   'avisa quando algo muda de verdade.\n\n'
   'Uma vez por semana entrega o Radar Regulatorio: o que mudou, desde quando '
   'passa a valer e o que exige acao da corretora.\n\n'
   'Nao dispara por manchete: so fonte oficial, e so mudanca que altera texto '
   'de norma, prazo ou cobertura. Banner novo ou data de atualizacao trocada '
   'nao vira aviso.',
   'radar', 'active',
   'scheduled', 'scheduled', false, false,
   '{"runtime": {"kind": "workflow", "workflow": "research.radar_weekly"},
     "instalacao": {"servico": "app.services.research.radar",
                    "classe": "RadarDeMercado", "metodo": "instalar"},
     "cadencia_fechamento": "weekly",
     "capabilities": ["platform.research.monitor",
                      "platform.research.extract",
                      "platform.research.regulatory"],
     "skill": "research.regulatory_watch",
     "artifact_template": "research.regulatory_radar",
     "fontes": "oficiais (SUSEP, CNSP, legislacao)",
     "visibility": {"type": "global"}}'::jsonb,
   '[{"key": "research_monitor",
      "label": "Acompanhar fontes publicas oficiais",
      "required": true,
      "description": "Permite verificar periodicamente paginas oficiais do setor."},
     {"key": "create_artifact",
      "label": "Gerar o radar regulatorio",
      "required": true,
      "description": "Permite compor a peca semanal com o que mudou."}]'::jsonb,
   true)
on conflict (slug) do nothing;

-- =============================================================
-- VERIFY
-- =============================================================
-- select slug, status, execution_mode, trigger_type,
--        default_config->'runtime'->>'workflow' as workflow,
--        default_config->>'skill' as skill
--   from public.auxiliary_templates where slug='radar-mercado-regulacao';
--   -- esperado: 1 linha; status 'active'; workflow 'research.radar_weekly';
--   --           skill 'research.regulatory_watch'
--
-- -- A Skill e as capacidades que o Auxiliar declara precisam EXISTIR:
-- select
--   (select count(*) from public.skills
--     where skill_key='research.regulatory_watch' and is_active) as skill_ok,
--   (select count(*) from public.capabilities
--     where capability_key in ('platform.research.monitor',
--                              'platform.research.extract',
--                              'platform.research.regulatory')
--       and is_active) as caps_ok;
--   -- esperado: skill_ok=1, caps_ok=3
--
-- -- Nenhuma tool duplicada foi criada:
-- select count(*) from public.tool_definitions
--  where tool_key in ('research.search','research.monitor');
--   -- esperado: 0
--
-- =============================================================
-- ROLLBACK
-- =============================================================
-- delete from public.auxiliary_templates where slug='radar-mercado-regulacao';
--
-- ATENCAO: nao existe rollback de capabilities/tools/skills aqui de proposito.
-- Esta migration nao as criou, e um `delete ... like 'research.%'` apagaria o
-- catalogo semeado em 26/07 — que e usado pelo Core em producao.
-- =============================================================
