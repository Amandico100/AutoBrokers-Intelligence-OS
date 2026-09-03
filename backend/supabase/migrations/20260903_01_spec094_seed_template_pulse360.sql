-- =============================================================
-- MIGRATION: spec094_seed_template_pulse360
-- SPEC:      SPEC-094 — BLOCO G (o Artifact `executive.pulse360`)
-- AUTOR:     builder E/F/G                DATA: 2026-09-03
-- OBJETIVO:  semear a linha de `report_templates` do Pulso 360.
--
-- APPLY:     um INSERT de UMA linha em public.report_templates, com
--            ON CONFLICT (template_key) DO NOTHING. Nenhuma tabela, coluna,
--            constraint, indice, policy ou default e criado ou alterado.
--            Nenhum dado existente e reescrito.
--
-- VERIFY:    select template_key, category, narrative_shape, audience
--              from public.report_templates
--             where template_key = 'executive.pulse360';
--            -- esperado: exatamente 1 linha, category='executive',
--            --           narrative_shape='verdict_led', audience='internal'
--
--            -- e a prova de que a chave estrangeira dos artifacts fecha:
--            select count(*) from public.artifacts
--             where template_key = 'executive.pulse360';
--            -- antes do primeiro canario: 0, e SEM erro de FK
--
-- ROLLBACK:  delete from public.report_templates
--             where template_key = 'executive.pulse360'
--               and not exists (select 1 from public.artifacts
--                                where template_key = 'executive.pulse360');
--            -- 🔴 O `not exists` NAO e cerimonia: `artifacts.template_key` e
--            --    chave estrangeira para esta tabela. Apagar a linha com
--            --    artifacts vivos ou falha por FK, ou (com CASCADE) leva as
--            --    pecas ja entregues a corretora junto. Se houver artifact,
--            --    o rollback e NAO apagar: uma linha de catalogo a mais nao
--            --    faz mal a ninguem; uma peca entregue que some, sim.
--
-- EXPAND-FIRST: sim  (so adiciona)
-- DESTRUTIVA:   nao
-- =============================================================
--
-- Por que esta migration existe, se a SPEC-094 prometia zero migration:
--
-- 📊 `backend/tests/test_template_de_artefato_existe.py:89-106` exige que TODO
-- template do catalogo Python que nao estava no banco em 30/07/2026 apareca no
-- SQL de seed. E o defeito que aquele teste guarda foi medido e e caro:
-- `artifacts.template_key` e FK para `report_templates`, e em 30/07 havia 19
-- templates em codigo para 8 no banco. Toda criacao de artifact dos 11 que
-- faltavam morria em violacao de chave estrangeira, em silencio -- o banco
-- mostrava `artifacts = 0` com 17 briefings publicados em `pending`: nao havia
-- o que entregar.
--
-- Editar a seed da 057 para acrescentar uma linha e proibido (CLAUDE.md §8:
-- migration aplicada nao se altera; corrige-se com migration nova). Entao a
-- 094 tem UMA migration, e ela e de seed.
--
-- ⚠️ O `ArtifactService._garantir_template` tambem insere a linha na hora do
-- uso. Os dois caminhos existem de proposito e nao brigam: o servico conserta
-- o caso de alguem publicar antes do deploy da migration; a migration conserta
-- o caso de alguem CONSULTAR o catalogo antes de qualquer publicacao. Os dois
-- usam ON CONFLICT DO NOTHING, entao rodar os dois nao duplica nada.

insert into public.report_templates
  (template_key, name, description, category, narrative_shape, audience)
values
  ('executive.pulse360',
   'Pulso 360',
   'O período inteiro da corretora, com a métrica e a cobertura ao lado de cada número.',
   'executive',
   'verdict_led',
   'internal')
on conflict (template_key) do nothing;
