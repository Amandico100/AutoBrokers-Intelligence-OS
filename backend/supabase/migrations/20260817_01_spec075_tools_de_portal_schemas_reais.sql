-- =============================================================
-- MIGRATION: spec075_tools_de_portal_schemas_reais
-- SPEC:      SPEC-075 — Bloco C, CORRIGIDA depois de ler o banco vivo
-- AUTOR:     Claude Opus 5                     DATA: 2026-08-17
-- OBJETIVO:  Dar schema REAL às tools de portal, que existiam com
--            `input_schema = {}` e apontando para o provider antigo.
--
-- APPLY:     ✅ APLICADA em 17/08/2026 03:5x UTC, projeto dcajcvlzcjbmyapmklil.
-- VERIFY:    ✅ rodado, saída registrada no bloco VERIFY ao final.
-- ROLLBACK:  bloco ao final (desativa/re-defaulta; não apaga release).
--
-- EXPAND-FIRST: sim
-- DESTRUTIVA:   não
-- =============================================================

-- -------------------------------------------------------------------------
-- 🔴 ESTA MIGRATION SUBSTITUI A `20260816_03_spec075_tools_de_portal.sql`
--
-- Aquela nunca foi aplicada, e não deve ser. Ela estava errada em dois pontos
-- que só o banco vivo revelou — e os dois merecem registro, porque a causa é a
-- mesma e vai se repetir:
--
-- **Eu inferi o estado de produção a partir do repositório.** O relatório da
-- SPEC-075 (CA-051) afirma: *"`portal.execute` aparece em UM lugar do
-- repositório… não há linha em `tool_definitions`"*. Estava certo sobre o
-- repositório e **errado sobre o banco**.
--
-- 📊 O que o banco tinha, em 17/08/2026, antes desta migration:
--
--     portal.billing_read   1.0.0 published  input_schema {}  provider portal_browser
--     portal.policy_read    1.0.0 published  input_schema {}  provider portal_browser
--     portal.execute        1.0.0 published  input_schema {}  provider portal_browser
--
-- As três são das 9 versões aplicadas sem arquivo que a `MIGRATIONS-AUTHORITY`
-- §4 avisa que existem. O `grep` no repo não podia achá-las.
--
-- O segundo erro: eu inventei `side_effect_class = 'write_external'`. O
-- constraint `ck_tool_side_effect` recusou, e o valor certo é
-- **`external_commitment`** — que é melhor nome, porque descreve um compromisso
-- assumido com terceiro, que é exatamente o que abrir um atendimento pago é.
--
-- ⚠️ E uma lição operacional: `apply_migration` **não foi transacional**. As
-- duas primeiras linhas do INSERT entraram e a terceira falhou. Migration que
-- depende de rollback automático não pode ser escrita assim; esta é idempotente
-- em cada statement.
-- -------------------------------------------------------------------------

-- 1. A tool material que faltava.
insert into public.tool_definitions
  (tool_key, name, description, category, implementation_kind, owner,
   capability_key, risk_level, side_effect_class, data_classification,
   requires_connection, requires_approval, is_active)
values
  ('portal.assistance_request', 'Abrir atendimento de assistencia',
   'Abre um atendimento de vidro/lanterna no portal de assistencia. '
   'EFEITO MATERIAL: cria um pedido pago no nome do segurado.',
   'operations', 'portal', 'platform', 'operational.portal.assistance.request',
   'high', 'external_commitment', 'personal', false, true, true)
on conflict (tool_key) do nothing;

-- 2. A 1.0.0 deixa de ser default — NÃO é apagada nem editada.
--    Release publicada é imutável (SPEC-056); ela fica no histórico, que é o
--    ponto de ser imutável.
update public.tool_releases r
   set is_default = false
  from public.tool_definitions d
 where r.tool_id = d.id
   and d.tool_key in ('portal.billing_read','portal.policy_read',
                      'portal.assistance_request')
   and r.version = '1.0.0';

-- 3. A 1.1.0, com schema REAL e o provider certo.
--
-- 🔴 Nenhum dos três `input_schema` menciona `journey`, `module`, `function`,
-- `portal_key`, `account_id`, `cookie`, `token`, `password` ou `proxy`. Essa
-- ausência é a SPEC-075 §10.4 escrita em JSON Schema: o modelo diz o RESULTADO
-- que quer; quem escolhe a função é o registro do portal-worker, e quem escolhe
-- a conta é o resolver.
insert into public.tool_releases
  (tool_id, version, status, input_schema, output_schema, execution_manifest,
   content_hash, is_default, published_at)
select d.id, '1.1.0', 'published',
  case d.tool_key
    when 'portal.billing_read' then
      '{"type":"object","additionalProperties":false,"required":["insurer_key"],
        "properties":{"insurer_key":{"type":"string","description":"a seguradora, como dado de negocio: allianz, hdi, mapfre, tokiomarine, yelum ou zurich"},
        "max_boletos":{"type":"integer","minimum":1,"maximum":500},
        "download_boletos":{"type":"boolean"}}}'::jsonb
    when 'portal.policy_read' then
      '{"type":"object","additionalProperties":false,"required":["insurer_key"],
        "properties":{"insurer_key":{"type":"string"},"cpf_cnpj":{"type":"string"},
        "placa":{"type":"string"},"numero_apolice":{"type":"string"}}}'::jsonb
    else
      '{"type":"object","additionalProperties":false,
        "required":["insurer_name","cpf_cnpj","placa","data_dano"],
        "properties":{"insurer_name":{"type":"string"},"cpf_cnpj":{"type":"string"},
        "placa":{"type":"string"},"data_dano":{"type":"string","description":"DD/MM/AAAA"},
        "dano":{"type":"object"},"especificos":{"type":"object"},
        "solicitante":{"type":"object"},
        "confirm":{"type":"boolean","description":"false vai ate a tela de confirmacao e PARA. true submete o pedido pago."}}}'::jsonb
  end,
  '{"type":"object","required":["business_state"],"properties":{
      "business_state":{"type":"string","enum":["ok","nothing_to_do","needs_human",
        "not_supported","not_authorized","no_connection","portal_blocked",
        "maybe_committed","failed"]},
      "message":{"type":"string"},"motivo":{"type":"string"},
      "pode_repetir":{"type":"boolean"},"data":{"type":"object"}}}'::jsonb,
  jsonb_build_object(
    'runtime', 'portal', 'provider', 'portal_worker',
    'implementation_kind', 'portal',
    'module', 'app.services.portals.gateway',
    'entrypoint', 'PortalExecutionGateway.executar',
    'operation_key', case d.tool_key
      when 'portal.billing_read' then 'billing.overdue.list'
      when 'portal.policy_read' then 'portal.login.check'
      else 'assistance.glass.request' end,
    'spec', 'SPEC-075'),
  encode(sha256(('spec075:' || d.tool_key || ':1.1.0')::bytea), 'hex'),
  true, now()
from public.tool_definitions d
where d.tool_key in ('portal.billing_read', 'portal.policy_read',
                     'portal.assistance_request')
  and not exists (select 1 from public.tool_releases r
                   where r.tool_id = d.id and r.version = '1.1.0');

-- 🔴 `portal.execute` NÃO é tocada. SPEC-075 §11.2: ela vira compatibilidade,
-- não padrão para Skills novas. Desativá-la agora quebraria o mapa de cutover
-- (`gateway_cutover.py:100`, `portal_action → portal.execute`) sem que nada
-- ainda use as novas.

-- =============================================================
-- VERIFY — 📊 saída real, rodada em 17/08/2026 logo após o APPLY:
--
--   schemas que deixam o modelo escolher funcao/conta/credencial
--       -> NENHUM
--   a unica tool que exige aprovacao
--       -> portal.assistance_request
--   capabilities referenciadas que NAO existem
--       -> NENHUMA
--
--   portal.assistance_request  external_commitment  approval=t  1.1.0 default  508 bytes  portal_worker
--   portal.billing_read        read                 approval=f  1.0.0          2 bytes    portal_browser
--   portal.billing_read        read                 approval=f  1.1.0 default  341 bytes  portal_worker
--   portal.execute             external_commitment  approval=t  1.0.0 default  2 bytes    portal_browser
--   portal.policy_read         read                 approval=f  1.0.0          2 bytes    portal_browser
--   portal.policy_read         read                 approval=f  1.1.0 default  228 bytes  portal_worker
-- =============================================================
-- select d.tool_key, d.side_effect_class, d.requires_approval, r.version,
--        r.is_default, length(r.input_schema::text) as tam_schema,
--        r.execution_manifest->>'provider' as provider
--   from public.tool_definitions d
--   join public.tool_releases r on r.tool_id = d.id
--  where d.tool_key like 'portal.%' order by d.tool_key, r.version;
--
-- 🔴 este devolve ZERO linhas, ou a §10.4 foi violada:
-- select d.tool_key from public.tool_releases r
--   join public.tool_definitions d on d.id = r.tool_id
--  where d.tool_key like 'portal.%' and r.version = '1.1.0'
--    and r.input_schema::text ~* '(journey|module|function|portal_key|account_id|cookie|token|password|proxy)';

-- =============================================================
-- ROLLBACK
--
-- Release publicada é imutável: não editar, não apagar. Reverter é devolver o
-- default à 1.0.0 e desativar a tool nova.
--
-- update public.tool_releases r set is_default = (r.version = '1.0.0')
--   from public.tool_definitions d
--  where r.tool_id = d.id
--    and d.tool_key in ('portal.billing_read','portal.policy_read');
-- update public.tool_definitions set is_active = false
--  where tool_key = 'portal.assistance_request';
-- =============================================================
