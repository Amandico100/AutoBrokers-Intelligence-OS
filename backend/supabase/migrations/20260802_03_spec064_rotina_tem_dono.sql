-- =============================================================
-- MIGRATION: spec064_rotina_tem_dono
-- SPEC:      SPEC-064 — Bloco A (ontologia) + D.5 (a Cobrança vira Auxiliar)
-- AUTOR:     lider tecnico            DATA: 2026-08-02
-- OBJETIVO:  fazer valer o corolário 1 da ontologia — "Rotina nunca existe
--            sozinha; toda Rotina pertence a um Auxiliar" — nos dados.
--
-- APPLY:     1. instala 'cobranca-feita' na corretora que já tem a Rotina,
--               com status 'inactive' (nasce DESLIGADO)
--            2. liga a Rotina de cobrança ao Auxiliar via tenant_auxiliary_id
--            3. índice para "as Rotinas deste Auxiliar"
--
-- VERIFY:    select r.name, r.is_active, ta.slug as auxiliar_dono, ta.status
--              from public.routines r
--              left join public.tenant_auxiliaries ta on ta.id = r.tenant_auxiliary_id;
--            -- esperado: "Cobranca de boletos atrasados" com dono
--            --           'cobranca-feita' em status 'inactive'
--
--            select count(*) from public.tenant_auxiliaries where status = 'active'
--             and last_run_at is null;
--            -- registro do estado: nada foi ligado por esta migration
--
-- ROLLBACK:  update public.routines set tenant_auxiliary_id = null
--             where tenant_auxiliary_id in (
--               select id from public.tenant_auxiliaries where slug = 'cobranca-feita');
--            delete from public.tenant_auxiliaries where slug = 'cobranca-feita';
--            drop index if exists public.routines_por_auxiliar_idx;
--
-- EXPAND-FIRST: sim. A coluna `routines.tenant_auxiliary_id` JÁ EXISTIA no
--               schema e estava sempre nula — a ligação era prevista e nunca
--               feita. Esta migration só preenche o que já cabia.
-- DESTRUTIVA:   não. A Rotina não é apagada nem movida: ela ganha dono.
--               `is_active` NÃO é tocado — quem estava desligado continua.
-- =============================================================
--
-- POR QUE ESTA MIGRATION EXISTE
-- -----------------------------
-- A auditoria de 02/08/2026 encontrou a inversão da ontologia escrita em
-- código, em uma linha:
--
--     backend/app/services/billing_collection.py:586
--     f"Auxiliar de Cobranca - {routine.get('name')}"
--
-- Uma Rotina que se apresentava como "Auxiliar" numa f-string. No banco, a
-- Cobrança estava em `routines` — e `tenant_auxiliaries` não tinha nenhuma
-- linha para ela.
--
-- O Founder pediu explicitamente que a Cobrança "apareça para todas as
-- corretoras poderem ativar". Aparecer no catálogo já acontece: o template
-- global é lido por todas. O que faltava era a Rotina ter dono — senão o
-- corretor liga o Auxiliar e nada acontece, porque o trabalho está pendurado
-- em outro lugar.
--
-- NOTA SOBRE "NASCE DESLIGADO"
-- ----------------------------
-- `tenant_auxiliaries.status` aceita: inactive | active | paused | disabled |
-- archived. **`inactive` é instalado-e-desligado** — é ele que a SPEC-064 D.1
-- quer dizer com "todos visíveis, todos desligados".

-- -------------------------------------------------------------
-- 1. A Cobrança é instalada onde a Rotina já mora — desligada
-- -------------------------------------------------------------
-- Só onde existe Rotina. Instalar nas outras seria ligar coisa que ninguém
-- pediu: o catálogo global já as torna visíveis, e instalar é ato do corretor.

insert into public.tenant_auxiliaries
  (company_id, template_id, slug, name, status, config, permissions, visibility)
select distinct
  r.company_id,
  t.id,
  t.slug,
  t.name,
  'inactive',                      -- nasce DESLIGADO (SPEC-064 D.1)
  '{}'::jsonb,                     -- sem sobreposição: herda o default do template
  coalesce(t.permissions, '{}'::jsonb),
  'company'
from public.routines r
cross join lateral (
  select id, slug, name, permissions
    from public.auxiliary_templates
   where slug = 'cobranca-feita'
   limit 1
) t
where r.name ilike '%cobran%'
on conflict (company_id, slug) do nothing;

-- -------------------------------------------------------------
-- 2. A Rotina ganha dono
-- -------------------------------------------------------------
-- `is_active` da Rotina NÃO é tocado. Se estava desligada, continua. Dar dono
-- não é ligar.

update public.routines r
   set tenant_auxiliary_id = ta.id,
       updated_at          = now()
  from public.tenant_auxiliaries ta
 where ta.company_id = r.company_id
   and ta.slug       = 'cobranca-feita'
   and r.name ilike '%cobran%'
   and r.tenant_auxiliary_id is null;

-- -------------------------------------------------------------
-- 3. "As Rotinas deste Auxiliar" é consulta de tela
-- -------------------------------------------------------------
-- A página de cada Auxiliar (Bloco C.3 §8) lista as Rotinas dele. Sem índice,
-- é varredura de tabela a cada abertura.

create index if not exists routines_por_auxiliar_idx
  on public.routines (tenant_auxiliary_id)
  where tenant_auxiliary_id is not null;

comment on column public.routines.tenant_auxiliary_id is
  'SPEC-064 Bloco A, corolário 1 — Rotina nunca existe sozinha: pertence a um Auxiliar instalado.';
