-- =============================================================
-- 🔴 SUPERADA — NAO APLICAR. Ver 20260817_01_spec075_tools_de_portal_schemas_reais.sql
--
-- Esta migration nunca foi aplicada e nao deve ser. Dois erros, e os dois so
-- apareceram quando o banco vivo foi lido:
--
-- 1. Ela SUPOE que as tools nao existem. 📊 Elas existem desde antes, com
--    release 1.0.0 publicada e input_schema {} — sao das 9 versoes aplicadas
--    sem arquivo que a MIGRATIONS-AUTHORITY §4 registra. O `on conflict do
--    nothing` faria a migration passar sem fazer nada.
--
-- 2. Ela usa side_effect_class = `write_external`, que eu inventei. O
--    constraint ck_tool_side_effect recusa. O valor certo e
--    `external_commitment`.
--
-- Mantida no repositorio como registro. A que vale e a de 20260817_01.
-- =============================================================

-- =============================================================
-- MIGRATION: spec075_tools_de_portal
-- SPEC:      SPEC-075 — Bloco C (completar o Tool Gateway de portal)
-- AUTOR:     Claude Opus 5 (execução SPEC-075)   DATA: 2026-08-16
-- OBJETIVO:  As capacidades de portal deixam de ser uma tool única e opaca e
--            passam a ser tools ESTREITAS, com schema real e efeito declarado.
--
-- APPLY:     3 linhas em `tool_definitions` + 3 releases publicadas.
--            `portal.execute` NÃO é criada nem alterada — ver a nota §2.
-- VERIFY:    bloco VERIFY ao final, SQL executável.
-- ROLLBACK:  bloco ROLLBACK ao final (desativa, não apaga — release é imutável).
--
-- EXPAND-FIRST: sim
-- DESTRUTIVA:   não
-- =============================================================

-- -------------------------------------------------------------------------
-- 1. POR QUE TOOLS ESTREITAS, E NÃO UMA `portal.execute`
--
-- 📊 Censo de 16/08/2026: `portal.execute` aparece em UM lugar do repositório
-- inteiro — o mapa de nomes do `gateway_cutover.py:100`, usado só para o diff
-- em sombra. Não há linha em `tool_definitions` para ela. O que existe de
-- verdade é a `PortalActionTool` do LangChain, anexada direto ao grafo e
-- protegida pela capability `tenant.portal.execute`.
--
-- 🔴 Uma tool única chamada "execute portal" é o oposto do que a SPEC-075 pede.
-- Ela obriga o modelo a dizer QUAL journey rodar — e a §10.4 proíbe
-- exatamente isso: o modelo nunca escolhe uma função. Além disso, uma tool só
-- tem um `side_effect_class`, então autorizar leitura de cobrança passaria a
-- autorizar abertura de atendimento pago.
--
-- Tools estreitas resolvem os dois problemas de uma vez: o modelo diz o
-- RESULTADO que quer, e cada resultado carrega o seu próprio nível de risco.
--
-- E o que NÃO se faz: uma tool por seguradora (§11.3). `billing.overdue.list`
-- vale para as seis seguradoras que implementam a operação. Seguradora nova
-- entra no registry do portal-worker e passa a ser atendida pela MESMA tool —
-- sem migration, sem release nova, sem Auxiliar novo. É esse o teste de que a
-- arquitetura funciona.
-- -------------------------------------------------------------------------

begin;

insert into public.tool_definitions
  (tool_key, name, description, category, implementation_kind, owner,
   capability_key, risk_level, side_effect_class, data_classification,
   requires_connection, requires_approval, is_active)
values
  -- Leitura de cobrança. Serve às 6 seguradoras que implementam
  -- `billing.overdue.list` no registry do portal-worker.
  ('portal.billing_read', 'Parcelas vencidas no portal da seguradora',
   'Lista as parcelas em atraso da carteira no portal da seguradora indicada. '
   'Somente leitura: nao emite boleto, nao envia mensagem, nao altera nada.',
   'operations', 'portal', 'platform', 'operational.portal.billing.read',
   'medium', 'read', 'personal', true, false, true),

  -- Leitura de apólice. Read-only por construção.
  ('portal.policy_read', 'Consulta de apolice no portal',
   'Consulta dados de apolice e cobertura no portal da seguradora. '
   'Somente leitura.',
   'operations', 'portal', 'platform', 'operational.portal.policy.read',
   'medium', 'read', 'personal', true, false, true),

  -- 🔴 A ÚNICA material das três. `requires_approval = true` não é excesso:
  -- ela abre um atendimento PAGO no nome de um segurado real, e a SPEC-074
  -- mediu que o portal cobra por atendimento e que repetir cria um segundo.
  -- `risk_level=high` faz o Capability Resolver exigir `scope` explícito —
  -- capability de risco alto sem escopo é fail-closed lá.
  ('portal.assistance_request', 'Abrir atendimento de assistencia',
   'Abre um atendimento de vidro/lanterna no portal de assistencia. '
   'EFEITO MATERIAL: cria um pedido pago no nome do segurado.',
   'operations', 'portal', 'platform', 'operational.portal.assistance.request',
   'high', 'write_external', 'personal', false, true, true)
on conflict (tool_key) do nothing;


-- -------------------------------------------------------------------------
-- 2. RELEASES — schema real, não `{"type":"object"}` genérico
--
-- 🔴 O schema é a fronteira que o modelo não atravessa. Note o que NÃO existe
-- em nenhum dos três `input_schema`: `journey`, `journey_key`, `module`,
-- `function`, `portal_key`, `account_id`, `token`, `cookie`, `password`.
--
-- Isso é a §10.1 e a §10.4 escritas em JSON Schema. O modelo diz a seguradora
-- (dado de negócio) e o que quer; quem escolhe a função é o registro do
-- portal-worker, e quem escolhe a conta é o resolver — nenhum dos dois aceita
-- palpite de texto gerado.
--
-- `additionalProperties: false` nos três. Sem isso, um campo extra inventado
-- pelo modelo atravessaria a validação e chegaria ao `business_input`.
-- -------------------------------------------------------------------------
insert into public.tool_releases
  (tool_id, version, status, input_schema, output_schema, execution_manifest,
   content_hash, is_default, published_at)
select d.id, '1.0.0', 'published',
  case d.tool_key
    when 'portal.billing_read' then
      '{"type":"object","additionalProperties":false,
        "required":["insurer_key"],
        "properties":{
          "insurer_key":{"type":"string",
            "description":"a seguradora, como dado de negocio (allianz, hdi, mapfre, tokiomarine, yelum, zurich)"},
          "max_boletos":{"type":"integer","minimum":1,"maximum":500},
          "download_boletos":{"type":"boolean"}}}'::jsonb
    when 'portal.policy_read' then
      '{"type":"object","additionalProperties":false,
        "required":["insurer_key"],
        "properties":{
          "insurer_key":{"type":"string"},
          "cpf_cnpj":{"type":"string"},
          "placa":{"type":"string"},
          "numero_apolice":{"type":"string"}}}'::jsonb
    else
      '{"type":"object","additionalProperties":false,
        "required":["insurer_name","cpf_cnpj","placa","data_dano"],
        "properties":{
          "insurer_name":{"type":"string"},
          "cpf_cnpj":{"type":"string"},
          "placa":{"type":"string"},
          "data_dano":{"type":"string","description":"DD/MM/AAAA"},
          "dano":{"type":"object"},
          "especificos":{"type":"object"},
          "solicitante":{"type":"object"},
          "confirm":{"type":"boolean",
            "description":"false vai ate a tela de confirmacao e PARA. true submete o pedido pago."}}}'::jsonb
  end,
  -- O resultado canônico do Bloco H. Todo portal responde a mesma forma, e é
  -- por isso que o chamador não precisa saber de que seguradora veio.
  '{"type":"object","required":["business_state"],"properties":{
      "business_state":{"type":"string","enum":["ok","nothing_to_do","needs_human",
        "not_supported","not_authorized","no_connection","portal_blocked",
        "maybe_committed","failed"]},
      "message":{"type":"string"},
      "motivo":{"type":"string"},
      "pode_repetir":{"type":"boolean"},
      "data":{"type":"object"}}}'::jsonb,
  jsonb_build_object(
    'runtime', 'portal',
    'module', 'app.services.portals.gateway',
    'entrypoint', 'PortalExecutionGateway.executar',
    'operation_key', case d.tool_key
      when 'portal.billing_read' then 'billing.overdue.list'
      when 'portal.policy_read' then 'portal.login.check'
      else 'assistance.glass.request' end,
    'spec', 'SPEC-075'),
  encode(sha256(('spec075:' || d.tool_key || ':1.0.0')::bytea), 'hex'),
  true, now()
from public.tool_definitions d
where d.tool_key in ('portal.billing_read', 'portal.policy_read',
                     'portal.assistance_request')
  and not exists (select 1 from public.tool_releases r
                   where r.tool_id = d.id and r.version = '1.0.0');

commit;

-- =============================================================
-- VERIFY
-- =============================================================
-- as 3 tools existem, e SÓ a de assistência exige aprovação
-- select tool_key, risk_level, side_effect_class, requires_approval, is_active
--   from public.tool_definitions
--  where tool_key like 'portal.%' order by tool_key;
--   -> portal.assistance_request | high   | write_external | true  | true
--      portal.billing_read       | medium | read           | false | true
--      portal.policy_read        | medium | read           | false | true
--
-- as 3 releases estão publicadas e são default
-- select d.tool_key, r.version, r.status, r.is_default
--   from public.tool_releases r join public.tool_definitions d on d.id = r.tool_id
--  where d.tool_key like 'portal.%' order by d.tool_key;
--
-- 🔴 nenhum input_schema deixa o modelo escolher função, conta ou credencial
-- select d.tool_key from public.tool_releases r
--   join public.tool_definitions d on d.id = r.tool_id
--  where d.tool_key like 'portal.%'
--    and (r.input_schema::text ~* '(journey|module|function|account_id|cookie|token|password|proxy)');
--   -> deve devolver ZERO linhas
--
-- as capabilities referenciadas existem
-- select t.tool_key, t.capability_key, c.capability_key is not null as capability_existe
--   from public.tool_definitions t
--   left join public.capabilities c on c.capability_key = t.capability_key
--  where t.tool_key like 'portal.%';

-- =============================================================
-- ROLLBACK
--
-- 🔴 Release publicada é IMUTÁVEL (SPEC-056). Não editar, não apagar. O
-- rollback correto é desativar a definição — a release fica no histórico, que
-- é o ponto de ela ser imutável.
--
-- update public.tool_definitions set is_active = false
--  where tool_key in ('portal.billing_read','portal.policy_read',
--                     'portal.assistance_request');
--
-- Isso basta: o `ToolGateway.selecionar()` filtra por `is_active`, então a tool
-- some da lista sem que nenhuma linha seja destruída.
-- =============================================================
