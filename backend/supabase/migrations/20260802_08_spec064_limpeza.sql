-- =============================================================
-- MIGRATION: spec064_limpeza
-- SPEC:      SPEC-064 — Bloco H (a casa limpa) · O ULTIMO PASSO DA SPEC
-- AUTOR:     lider tecnico            DATA: 2026-08-02
-- OBJETIVO:  apagar o que a estrutura nova ja substituiu — e so agora, porque
--            "apagar e sempre o ultimo passo" (SPEC-064 §2).
--
-- APPLY:     1. conector 'portal_browser' -> inativo (o simulador saiu do repo)
--            2. conexoes de portal_browser -> arquivadas
--            3. tres templates de TESTE e as tres instalacoes -> removidos
--            4. rotina "Noticias Principais da Globo" -> removida
--            5. dois agentes "TESTE Runtime Smith" da Amandus -> removidos
--
-- VERIFY:    select count(*) from public.auxiliary_templates where category = 'Teste';
--            -- esperado: 0
--            select count(*) from public.routines where name ilike '%globo%';
--            -- esperado: 0
--            select count(*) from public.agents where name ilike 'TESTE%';
--            -- esperado: 0
--            select count(*) from public.connector_templates
--             where slug = 'portal_browser' and is_active;
--            -- esperado: 0
--            select count(*) from public.routines where tenant_auxiliary_id is null;
--            -- esperado: 0 — nenhuma Rotina sem Auxiliar dono
--
-- ROLLBACK:  irreversivel para os itens apagados (0 execucoes, sem dado de
--            cliente). O conector e as conexoes sao reversiveis:
--              update public.connector_templates set is_active = true
--               where slug = 'portal_browser';
--            Backup dos registros apagados no relatorio da SPEC.
--
-- EXPAND-FIRST: nao se aplica — e a fase de contract, e ela vem por ultimo.
-- DESTRUTIVA:   SIM, e de proposito. Escopo declarado abaixo, item a item.
--               Nenhum tem execucao, nenhum tem dado de cliente.
-- =============================================================
--
-- O QUE ESTA SENDO APAGADO, E POR QUE E SEGURO
-- ---------------------------------------------
-- 📊 Medido em 02/08/2026, antes de apagar:
--
--   teste-runtime-smith-agent ...... 0 execucoes, archived, sem prompt
--   teste-exclusivo-rafael ......... 0 execucoes, archived, sem prompt
--   teste-publicado-global ......... 0 execucoes, archived, sem prompt
--   as 3 instalacoes na Amandus .... 0 execucoes, last_run_at NULL
--   "Noticias Principais da Globo" . desligada, sem relacao com seguros
--   agentes "TESTE Runtime Smith" .. is_active=false, prompt de 95 caracteres
--
-- O Founder decidiu em 02/08 que a Amandus deixa de ser excecao: mesma
-- estrutura, mesmas possibilidades das outras. O que sai daqui e lixo de
-- teste — o Auxiliar de Cobranca dela, que e producao, fica.
--
-- E o conector `portal_browser`: 📊 todas as sessoes tinham
-- `real_action_allowed: false`, as contas tinham `credential_ref: null` e os
-- canarios da Resulta foram abortados em 21/06. Ele nunca acessou nada. As
-- cinco capabilities que apontavam para ele foram reapontadas na migration 07
-- para `portal_worker`, que e quem entra na Allianz de verdade.

-- -------------------------------------------------------------
-- 1. O conector do simulador sai do catalogo
-- -------------------------------------------------------------
-- Nao e apagado: e desativado. A linha continua legivel para quem for auditar
-- por que existiam dois caminhos de portal.

update public.connector_templates
   set is_active  = false,
       description = 'REMOVIDO na SPEC-064: era simulacao (real_action_allowed sempre false). '
                     'Quem acessa portal de seguradora e o portal_worker, pelo conector insurance_portal.',
       updated_at = now()
 where slug = 'portal_browser';

update public.tenant_connections tc
   set status   = 'archived',
       metadata = coalesce(tc.metadata, '{}'::jsonb)
                  || jsonb_build_object('arquivado_por', 'SPEC-064 Bloco H',
                                        'motivo', 'Portal Browser era simulacao e saiu do produto'),
       updated_at = now()
  from public.connector_templates ct
 where ct.id = tc.connector_template_id
   and ct.slug = 'portal_browser'
   and tc.status <> 'archived';

-- -------------------------------------------------------------
-- 2. As instalacoes de teste, antes dos templates (a FK aponta para eles)
-- -------------------------------------------------------------

delete from public.tenant_auxiliaries ta
 where ta.slug in ('teste-runtime-smith-agent', 'teste-exclusivo-rafael', 'teste-publicado-global')
   and ta.last_run_at is null;   -- guarda: so o que nunca rodou

delete from public.auxiliary_templates
 where slug in ('teste-runtime-smith-agent', 'teste-exclusivo-rafael', 'teste-publicado-global')
   and not exists (
     select 1 from public.tenant_auxiliaries t
      where t.template_id = auxiliary_templates.id);   -- guarda: sem instalacao viva

-- -------------------------------------------------------------
-- 3. A rotina da Globo
-- -------------------------------------------------------------
-- globo.com a cada 5 minutos, sem relacao com seguros. Desligada desde sempre.
-- O MODELO de rotina "Noticias do setor" fica: e legitimo, so nunca foi
-- adotado com uma fonte que faca sentido.

delete from public.routines
 where name ilike '%globo%'
   and coalesce(is_active, false) = false;

-- -------------------------------------------------------------
-- 4. Os agentes de teste da Amandus
-- -------------------------------------------------------------
-- is_active=false, prompt de 95 caracteres, criados em 11/06 para validar o
-- runtime. A guarda por `is_active = false` impede que esta migration toque um
-- agente que esteja trabalhando.

delete from public.agents
 where name ilike 'TESTE Runtime Smith%'
   and coalesce(is_active, false) = false;
