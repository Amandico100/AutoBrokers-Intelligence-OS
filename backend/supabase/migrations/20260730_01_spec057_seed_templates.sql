-- SPEC-057 · semeia os 11 templates que existem em codigo e nao no banco.
--
-- O defeito, medido em 30/07/2026: `artifacts.template_key` e FK para
-- `report_templates.template_key`. O catalogo vive em Python
-- (app/services/artifacts/templates.py, 19 templates) e a migration original
-- nao semeou nenhum; 8 entraram por caminho manual e 11 ficaram de fora.
--
-- Entre os 11 estavam `briefing.daily_operational` e `briefing.weekly_executive`
-- — exatamente os dois que o briefing diario usa. Toda criacao de artifact
-- falhava por violacao de chave estrangeira, em silencio, e por isso o banco
-- mostrava `artifacts = 0` com 17 briefings publicados em `pending`: nao havia
-- o que entregar. Os seis templates de pesquisa tambem faltavam.
--
-- Idempotente: ON CONFLICT DO NOTHING. Nao altera os 8 que ja existem.

insert into public.report_templates (template_key, name, description, category, narrative_shape, audience) values
  ('briefing.daily_operational', 'Briefing Diário Operacional', 'O que precisa de você hoje, o que já foi resolvido e o que dá para delegar.', 'briefing', 'action_led', 'internal'),
  ('briefing.weekly_executive', 'Briefing Executivo Semanal', 'Visão gerencial da semana: mudanças, gargalos, resultados e decisões.', 'briefing', 'verdict_led', 'internal'),
  ('briefing.critical_alert_detail', 'Detalhe de Alerta Crítico', 'O que aconteceu, a evidência, o impacto e a ação — em uma página.', 'briefing', 'verdict_led', 'internal'),
  ('briefing.opportunity_dossier', 'Dossiê de Oportunidade', 'Uma oportunidade detectada: evidência, impacto, custo e o que fazer.', 'briefing', 'narrative_led', 'internal'),
  ('briefing.demand_radar_admin', 'Radar de Demanda', 'O que várias corretoras querem delegar — agregado e anônimo.', 'briefing', 'comparative', 'internal'),
  ('research.evidence_pack', 'Pacote de Evidências', 'Cada afirmação com a fonte que a sustenta, o trecho citado e a data.', 'research', 'precision_led', 'internal'),
  ('research.competitor_matrix', 'Comparativo de Concorrentes', 'Corretoras da região lado a lado: presença, produtos e posicionamento.', 'research', 'comparative', 'internal'),
  ('research.site_audit', 'Diagnóstico do Site', 'O que impede o site da corretora de ser encontrado e entendido.', 'research', 'precision_led', 'internal'),
  ('research.regulatory_radar', 'Radar Regulatório', 'O que mudou na regulação do seguro, desde quando vale e o que exige ação.', 'research', 'chronological', 'internal'),
  ('research.company_list', 'Lista de Empresas', 'Empresas do segmento e da região, com o motivo de cada uma estar na lista.', 'research', 'precision_led', 'internal'),
  ('research.change_report', 'O Que Mudou', 'Antes e depois de uma página acompanhada, e por que isso importa.', 'research', 'chronological', 'internal')
on conflict (template_key) do nothing;
