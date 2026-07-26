-- =============================================================
-- MIGRATION: spec059_regras_skills_tools
-- SPEC:      SPEC-059 — Bloco C (regras iniciais) + §22.2 e §27.3
-- AUTOR:     Executor Opus                DATA: 2026-07-26
-- OBJETIVO:  publicar os 12 detectores como REGRAS versionadas e registrar
--            as capacidades, ferramentas e Skills de inteligencia.
--
-- APPLY:     seeds idempotentes (ON CONFLICT DO NOTHING / DO UPDATE) em
--            intelligence_rules, capabilities, capability_bindings,
--            tool_definitions, tool_releases, skills, skill_releases,
--            skill_tool_requirements, skill_capability_requirements,
--            skill_bindings.
-- VERIFY:    ver bloco VERIFY ao final.
-- ROLLBACK:  ver bloco ROLLBACK ao final (delete por chave, sem tocar no
--            que ja existia).
--
-- EXPAND-FIRST: sim — so insere. Nenhuma linha existente e alterada.
-- DESTRUTIVA:   nao
--
-- POR QUE A REGRA E DADO E O DETECTOR E CODIGO
-- --------------------------------------------
-- O limiar muda com calibragem; o algoritmo, nao. Separar os dois e o que
-- permite pausar um detector barulhento, mexer no limiar e fazer rollback
-- SEM DEPLOY — que e exatamente o que a §26.6 pede do Admin.
-- =============================================================

-- -------------------------------------------------------------
-- 1. Regras — os 12 detectores iniciais de §23
-- -------------------------------------------------------------
insert into public.intelligence_rules
  (rule_key, name, description, signal_type, scope, implementation_kind,
   configuration, minimum_evidence, minimum_confidence, minimum_trust_tier,
   cooldown_seconds, validity_seconds, status)
values
  ('operacao.aprovacao_parada',
   'Aprovação parada',
   'Aprovação pendente acima da janela, ainda válida e decidível.',
   'approval_pending', 'tenant', 'deterministic_python',
   '{"horas_minimas": 24}'::jsonb, 1, 0.900, 0, 21600, 259200, 'active'),

  ('operacao.work_run_falhando',
   'Trabalhos falhando pelo mesmo motivo',
   'Falhas acima do limiar agrupadas por causa provável, excluindo cancelamento.',
   'work_failure', 'tenant', 'deterministic_python',
   '{"minimo_falhas": 3, "janela_horas": 24}'::jsonb, 1, 0.900, 1, 10800, 172800, 'active'),

  ('operacao.work_run_travado',
   'Trabalho sem sinal de vida',
   'Lease vencida, status não terminal e recuperação automática não concluiu.',
   'work_stale', 'tenant', 'deterministic_python',
   '{"horas_travado": 2}'::jsonb, 1, 0.900, 0, 3600, 86400, 'active'),

  ('operacao.auxiliar_degradado',
   'Auxiliar ou Rotina degradado',
   'Saúde degradada ou falhas consecutivas em Auxiliar instalado ou Rotina.',
   'operational_backlog', 'tenant', 'deterministic_python',
   '{"falhas_consecutivas": 2}'::jsonb, 1, 0.900, 0, 21600, 172800, 'active'),

  ('operacao.artifact_nao_entregue',
   'Peça pronta e não entregue',
   'Artefato publicado sem abertura nem compartilhamento na janela.',
   'operational_backlog', 'tenant', 'deterministic_python',
   '{"horas_sem_leitura": 24}'::jsonb, 1, 0.900, 0, 86400, 172800, 'active'),

  ('conexoes.conexao_degradada',
   'Conexão indisponível',
   'Conexão ou canal em estado ruim, com o impacto nas Rotinas e Auxiliares.',
   'connection_health', 'tenant', 'deterministic_python',
   '{}'::jsonb, 1, 0.900, 0, 3600, 86400, 'active'),

  ('conexoes.orcamento_no_limite',
   'Consumo perto do limite',
   'Custo técnico do mês contra o limite declarado, com projeção linear.',
   'budget_risk', 'tenant', 'statistical',
   '{"limite_usd": 0, "percentual_alerta": 80}'::jsonb, 2, 0.800, 0, 86400, 604800, 'active'),

  ('qualidade.regressao_atendimento',
   'Queda de qualidade no atendimento',
   'Nota média das últimas 24h contra a média dos 7 dias anteriores.',
   'attendance_quality', 'tenant', 'statistical',
   '{"minimo_amostras": 5, "queda_pontos": 10}'::jsonb, 2, 0.800, 3, 86400, 604800, 'active'),

  ('qualidade.atendimento_parado',
   'Atendimentos parados',
   'Conversas não encerradas sem mensagem há mais que a janela, em horário útil.',
   'operational_backlog', 'tenant', 'deterministic_python',
   '{"horas_parado": 24}'::jsonb, 1, 0.900, 0, 21600, 172800, 'active'),

  ('automacao.tarefa_repetida',
   'Tarefa repetida',
   'Mesmo pedido com a mesma assinatura acima do limiar na janela.',
   'repeated_task', 'tenant', 'deterministic_python',
   '{"minimo_repeticoes": 3, "janela_dias": 14}'::jsonb, 1, 0.700, 3, 86400, 1209600, 'active'),

  ('automacao.lacuna_recorrente',
   'Pedido que o sistema ainda não atende',
   'Lacuna de capacidade registrada mais de uma vez para a mesma corretora.',
   'capability_gap', 'tenant', 'deterministic_python',
   '{"minimo_ocorrencias": 2}'::jsonb, 1, 0.900, 0, 86400, 2592000, 'active'),

  ('automacao.resultado_positivo',
   'O que ficou pronto',
   'Trabalhos concluídos na janela, agregados — nunca um sinal por trabalho.',
   'positive_outcome', 'tenant', 'deterministic_python',
   '{"janela_horas": 24, "minimo": 1}'::jsonb, 1, 0.900, 0, 86400, 604800, 'active')
on conflict (rule_key) do nothing;


-- -------------------------------------------------------------
-- 2. Capacidades — o poder que governa as ferramentas
-- -------------------------------------------------------------
--
-- Duas, e nao uma: LER as prioridades e RESPONDER a uma recomendacao sao
-- poderes diferentes. Quem so consulta nao deveria poder aceitar em nome da
-- corretora, e uma capability unica tornaria essa distincao impossivel de
-- expressar depois, quando a SPEC-061 trouxer papeis finos.
insert into public.capabilities
  (capability_key, name, category, owner, risk, requires_connection,
   requires_approval, is_active, metadata)
values
  ('tenant.intelligence.read', 'Ver as prioridades da corretora', 'internal',
   'tenant', 'low', false, false, true,
   '{"spec": "SPEC-059", "read_only_projection": true}'::jsonb),
  ('tenant.intelligence.respond', 'Responder a uma recomendação', 'productivity',
   'tenant', 'low', false, false, true,
   '{"spec": "SPEC-059", "efeito": "prepare"}'::jsonb)
on conflict (capability_key) do nothing;

insert into public.capability_bindings (capability_key, agent_role, enabled, scope)
values
  ('tenant.intelligence.read', 'core', true,
   '{"read": true, "write": false, "tenant_scoped": true,
     "audience": ["internal"], "data_classes": ["operational"],
     "max_calls_per_run": 4, "requires_approval": false,
     "read_only_projection": true}'::jsonb),
  ('tenant.intelligence.respond', 'core', true,
   '{"read": true, "write": true, "tenant_scoped": true,
     "audience": ["internal"], "data_classes": ["operational"],
     "max_calls_per_run": 3, "requires_approval": false}'::jsonb)
on conflict do nothing;


-- -------------------------------------------------------------
-- 3. Ferramentas — §27.3
-- -------------------------------------------------------------
--
-- As nove operacoes de §27.3 estao todas disponiveis. Elas chegam ao Core
-- agrupadas em QUATRO ferramentas porque o teto do Tool Gateway e de 12 tools
-- por execucao (SPEC-053 §13.1) e o Core ja carrega perto disso: anexar nove
-- ferramentas novas degradaria a escolha do modelo em TODA conversa, inclusive
-- nas que nada tem a ver com briefing. Registrado em CHANGE-ADDENDA.
insert into public.tool_definitions
  (tool_key, name, description, category, implementation_kind, owner,
   capability_key, risk_level, side_effect_class, data_classification,
   requires_connection, requires_approval, is_active)
values
  ('intelligence.briefing', 'Briefing da corretora',
   'Entrega o briefing atual (diário, semanal ou sob demanda) com os itens que exigem atenção.',
   'analytics', 'native', 'platform', 'tenant.intelligence.read',
   'low', 'read', 'operational', false, false, true),
  ('intelligence.findings', 'Prioridades e explicação',
   'Lista os pontos de atenção ativos e explica por que cada um apareceu, com evidência.',
   'analytics', 'native', 'platform', 'tenant.intelligence.read',
   'low', 'read', 'operational', false, false, true),
  ('intelligence.respond', 'Responder a uma recomendação',
   'Aceita, dispensa, adia ou pede explicação sobre uma recomendação. Não executa efeito externo.',
   'analytics', 'native', 'platform', 'tenant.intelligence.respond',
   'low', 'prepare', 'operational', false, false, true),
  ('intelligence.preferences', 'Preferências de briefing',
   'Ajusta horário, canais, categorias e nível de detalhe do briefing.',
   'analytics', 'native', 'platform', 'tenant.intelligence.respond',
   'low', 'write_reversible', 'operational', false, false, true)
on conflict (tool_key) do nothing;

insert into public.tool_releases
  (tool_id, version, status, input_schema, output_schema, execution_manifest,
   content_hash, is_default, published_at)
select d.id, '1.0.0', 'published',
  case d.tool_key
    when 'intelligence.briefing' then
      '{"type":"object","properties":{"tipo":{"type":"string","enum":["hoje","semana","agora"]}}}'::jsonb
    when 'intelligence.findings' then
      '{"type":"object","properties":{"explicar_id":{"type":"string"}}}'::jsonb
    when 'intelligence.respond' then
      '{"type":"object","required":["recommendation_id","acao"],"properties":{"recommendation_id":{"type":"string"},"acao":{"type":"string"},"comentario":{"type":"string"}}}'::jsonb
    else
      '{"type":"object","properties":{"campo":{"type":"string"},"valor":{"type":"string"}}}'::jsonb
  end,
  '{"type":"object","properties":{"texto":{"type":"string"}}}'::jsonb,
  jsonb_build_object('runtime', 'native', 'module',
                     'app.agents.tools.intelligence_tool', 'spec', 'SPEC-059'),
  encode(sha256(('spec059:' || d.tool_key || ':1.0.0')::bytea), 'hex'),
  true, now()
from public.tool_definitions d
where d.tool_key in ('intelligence.briefing', 'intelligence.findings',
                     'intelligence.respond', 'intelligence.preferences')
  and not exists (select 1 from public.tool_releases r
                   where r.tool_id = d.id and r.version = '1.0.0');


-- -------------------------------------------------------------
-- 4. Skills — §22.2
-- -------------------------------------------------------------
insert into public.skills
  (skill_key, name, description, category, owner, visibility,
   business_domain, is_active)
values
  ('intelligence.daily_briefing',
   'O que precisa da minha atenção',
   'Entrega as prioridades do dia com evidência, e explica por que cada item apareceu.',
   'analytics', 'platform', 'internal', 'operacao', true),
  ('intelligence.explain_priority',
   'Por que estou vendo isso',
   'Explica a origem de um ponto de atenção: qual fato, qual fonte, qual período.',
   'analytics', 'platform', 'internal', 'operacao', true),
  ('intelligence.act_on_recommendation',
   'Resolver o que apareceu',
   'Aceita, adia ou dispensa uma recomendação e abre o caminho canônico quando aceita.',
   'analytics', 'platform', 'internal', 'operacao', true)
on conflict (skill_key) do nothing;

insert into public.skill_releases
  (skill_id, version, status, manifest, instruction_markdown, content_hash,
   is_default, published_at, approved_at)
select s.id, '1.0.0', 'published',
  jsonb_build_object(
    'capability_pack', null,
    'triggers', case s.skill_key
      when 'intelligence.daily_briefing' then
        jsonb_build_array('atenção hoje', 'preciso olhar', 'prioridades',
                          'briefing', 'resumo do dia', 'o que aconteceu',
                          'como estamos', 'novidades', 'pendências')
      when 'intelligence.explain_priority' then
        jsonb_build_array('por que', 'de onde veio', 'como você sabe',
                          'qual a fonte', 'explica isso')
      else
        jsonb_build_array('resolve isso', 'pode fazer', 'aceito',
                          'não quero mais', 'já resolvi', 'me lembre amanhã')
    end,
    'spec', 'SPEC-059'),
  case s.skill_key
    when 'intelligence.daily_briefing' then
      E'Entregue o que está no briefing. Não invente número.\n\n'
      '- Todo número vem de um Finding já gravado; se não estiver lá, não existe.\n'
      '- Separe o que é FATO do que é leitura. Nunca apresente inferência como fato.\n'
      '- Quando não houver dado, diga que não há. "A qualidade permaneceu estável" '
      'sem conversas auditadas é uma afirmação falsa.\n'
      '- No máximo 5 a 7 itens. O resto fica no histórico.'
    when 'intelligence.explain_priority' then
      E'Responda com a evidência, não com adjetivos.\n\n'
      '- Diga qual foi o fato observado, de qual fonte e de qual período.\n'
      '- Se a conclusão depende de inferência, diga isso com todas as letras.\n'
      '- Se o corretor discordar do número, registre `wrong_data`: o dado vai '
      'ser conferido e a evidência NÃO é apagada.'
    else
      E'Aceitar uma recomendação NÃO aprova todo efeito futuro.\n\n'
      '- Registre a resposta e confirme em uma frase o que vai acontecer.\n'
      '- Ação de efeito externo continua passando por aprovação — diga isso.\n'
      '- Se não existir caminho para resolver, explique o que falta em vez de '
      'prometer.'
  end,
  encode(sha256(('spec059:' || s.skill_key || ':1.0.0')::bytea), 'hex'),
  true, now(), now()
from public.skills s
where s.skill_key in ('intelligence.daily_briefing',
                      'intelligence.explain_priority',
                      'intelligence.act_on_recommendation')
  and not exists (select 1 from public.skill_releases r
                   where r.skill_id = s.id and r.version = '1.0.0');

insert into public.skill_tool_requirements
  (skill_release_id, tool_key, requirement, max_calls, ordinal)
select r.id, t.tool_key, 'required', t.max_calls, t.ordinal
from public.skill_releases r
join public.skills s on s.id = r.skill_id
join (values
  ('intelligence.daily_briefing', 'intelligence.briefing', 2, 1),
  ('intelligence.daily_briefing', 'intelligence.findings', 3, 2),
  ('intelligence.explain_priority', 'intelligence.findings', 3, 1),
  ('intelligence.act_on_recommendation', 'intelligence.respond', 3, 1),
  ('intelligence.act_on_recommendation', 'intelligence.findings', 2, 2)
) as t(skill_key, tool_key, max_calls, ordinal) on t.skill_key = s.skill_key
where r.version = '1.0.0'
  and not exists (select 1 from public.skill_tool_requirements x
                   where x.skill_release_id = r.id and x.tool_key = t.tool_key);

insert into public.skill_capability_requirements
  (skill_release_id, capability_key, requirement, ordinal)
select r.id, c.capability_key, 'required', c.ordinal
from public.skill_releases r
join public.skills s on s.id = r.skill_id
join (values
  ('intelligence.daily_briefing', 'tenant.intelligence.read', 1),
  ('intelligence.explain_priority', 'tenant.intelligence.read', 1),
  ('intelligence.act_on_recommendation', 'tenant.intelligence.respond', 1),
  ('intelligence.act_on_recommendation', 'tenant.intelligence.read', 2)
) as c(skill_key, capability_key, ordinal) on c.skill_key = s.skill_key
where r.version = '1.0.0'
  and not exists (select 1 from public.skill_capability_requirements x
                   where x.skill_release_id = r.id
                     and x.capability_key = c.capability_key);

-- Binding por papel: so o Core. O atendente externo NAO recebe inteligencia
-- da corretora — SPEC-053 §5.2 e o mesmo motivo pelo qual a SPEC-054 tirou
-- dele o HTTP genérico.
insert into public.skill_bindings
  (skill_id, skill_release_id, target_type, target_key, enabled, priority)
select s.id, r.id, 'agent_role', 'core', true, 50
from public.skills s
join public.skill_releases r on r.skill_id = s.id and r.version = '1.0.0'
where s.skill_key in ('intelligence.daily_briefing',
                      'intelligence.explain_priority',
                      'intelligence.act_on_recommendation')
  and not exists (select 1 from public.skill_bindings b
                   where b.skill_id = s.id and b.target_type = 'agent_role'
                     and b.target_key = 'core');

-- =============================================================
-- VERIFY
-- =============================================================
-- select count(*) regras from intelligence_rules where status='active';
--   -- esperado: 12
-- select count(*) tools from tool_definitions where tool_key like 'intelligence.%';
--   -- esperado: 4, todas com release publicada:
-- select d.tool_key, r.status from tool_definitions d
--   join tool_releases r on r.tool_id = d.id
--  where d.tool_key like 'intelligence.%';
-- select s.skill_key, r.status, count(tr.id) tools
--   from skills s join skill_releases r on r.skill_id = s.id
--   left join skill_tool_requirements tr on tr.skill_release_id = r.id
--  where s.skill_key like 'intelligence.%' group by 1,2;
--   -- esperado: 3 Skills publicadas com 1 a 2 tools cada
-- select capability_key, agent_role, scope->>'max_calls_per_run'
--   from capability_bindings where capability_key like 'tenant.intelligence%';
--   -- esperado: 2 linhas, papel 'core', escopo preenchido
--
-- =============================================================
-- ROLLBACK
-- =============================================================
-- delete from skill_bindings where skill_id in
--   (select id from skills where skill_key like 'intelligence.%');
-- delete from skill_tool_requirements where skill_release_id in
--   (select r.id from skill_releases r join skills s on s.id=r.skill_id
--     where s.skill_key like 'intelligence.%');
-- delete from skill_capability_requirements where skill_release_id in
--   (select r.id from skill_releases r join skills s on s.id=r.skill_id
--     where s.skill_key like 'intelligence.%');
-- delete from skill_releases where skill_id in
--   (select id from skills where skill_key like 'intelligence.%');
-- delete from skills where skill_key like 'intelligence.%';
-- delete from tool_releases where tool_id in
--   (select id from tool_definitions where tool_key like 'intelligence.%');
-- delete from tool_definitions where tool_key like 'intelligence.%';
-- delete from capability_bindings where capability_key like 'tenant.intelligence%';
-- delete from capabilities where capability_key like 'tenant.intelligence%';
-- delete from intelligence_rules where rule_key in (
--   'operacao.aprovacao_parada','operacao.work_run_falhando',
--   'operacao.work_run_travado','operacao.auxiliar_degradado',
--   'operacao.artifact_nao_entregue','conexoes.conexao_degradada',
--   'conexoes.orcamento_no_limite','qualidade.regressao_atendimento',
--   'qualidade.atendimento_parado','automacao.tarefa_repetida',
--   'automacao.lacuna_recorrente','automacao.resultado_positivo');
-- =============================================================
