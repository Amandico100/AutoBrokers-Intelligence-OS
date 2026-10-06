-- =============================================================
-- MIGRATION: spec130a_seed_template_proposta
-- SPEC:      SPEC-130-A — F2a (U5: a página da proposta no Artifact Hub)
-- AUTOR:     builder F2a                  DATA: 2026-10-06
-- OBJETIVO:  semear a linha de `report_templates` da PROPOSTA (`proposal.quote`).
--
-- APPLY:     um INSERT de UMA linha em public.report_templates, com
--            ON CONFLICT (template_key) DO NOTHING. Nenhuma tabela, coluna,
--            constraint, índice, policy, GRANT ou default é criado ou alterado.
--            Nenhum dado existente é reescrito. Os valores cabem nas CHECKs da
--            20260725_06: category 'client_facing', narrative_shape
--            'comparative', audience 'client'.
--
-- VERIFY:    select template_key, category, narrative_shape, audience, is_active
--              from public.report_templates
--             where template_key = 'proposal.quote';
--            -- esperado: exatamente 1 linha, category='client_facing',
--            --           narrative_shape='comparative', audience='client',
--            --           is_active=true
--
--            -- e a prova de que a chave estrangeira dos artifacts fecha:
--            select count(*) from public.artifacts
--             where template_key = 'proposal.quote';
--            -- antes da primeira proposta publicada: 0, e SEM erro de FK
--
-- ROLLBACK:  delete from public.report_templates
--             where template_key = 'proposal.quote'
--               and not exists (select 1 from public.artifacts
--                                where template_key = 'proposal.quote');
--            -- 🔴 O `not exists` não é cerimônia: `artifacts.template_key` é FK
--            --    para esta tabela (ON DELETE SET NULL). Apagar a linha com
--            --    propostas vivas deixaria as peças entregues ao segurado sem
--            --    template — e o renderizador (o gancho do catálogo) deixaria de
--            --    ser achado para a versão seguinte. Com proposta viva, o
--            --    rollback é NÃO apagar.
--
-- EXPAND-FIRST: sim  (só adiciona)
-- DESTRUTIVA:   não
-- =============================================================
--
-- Por que existe: `backend/tests/test_template_de_artefato_existe.py` exige que
-- todo template do catálogo Python ausente do banco em 30/07/2026 esteja numa
-- seed versionada (a FK `artifacts.template_key → report_templates` já matou
-- criação de artefato em silêncio: 19 templates em código, 8 no banco). O
-- `ArtifactService._garantir_template` também insere na hora do uso; os dois
-- usam ON CONFLICT DO NOTHING e não brigam (molde da 20260903_01).

insert into public.report_templates
  (template_key, name, description, category, narrative_shape, audience)
values
  ('proposal.quote',
   'Proposta de seguro',
   'As opções comparadas igual com igual, a recomendada e o caminho para fechar pelo WhatsApp.',
   'client_facing',
   'comparative',
   'client')
on conflict (template_key) do nothing;
