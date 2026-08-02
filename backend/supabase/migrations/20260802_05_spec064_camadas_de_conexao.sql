-- =============================================================
-- MIGRATION: spec064_camadas_de_conexao
-- SPEC:      SPEC-064 — correção vinda da decisão do Founder de 02/08/2026
-- AUTOR:     lider tecnico            DATA: 2026-08-02
-- OBJETIVO:  separar QUEM PAGA a conexão de QUEM A USA. Firecrawl e Tavily
--            são da plataforma; a corretora nunca deveria ter visto um card
--            pedindo a chave dela.
--
-- APPLY:     1. connector_templates.scope: platform | company | user
--            2. Firecrawl vira 'platform'; Tavily entra como 'platform'
--            3. arquiva a conexão Firecrawl que uma corretora chegou a criar
--
-- VERIFY:    select scope, count(*), string_agg(slug, ', ' order by slug)
--              from public.connector_templates where is_active group by scope;
--            -- esperado: platform com firecrawl e tavily;
--            --           company com infocap, insurance_portal, whatsapp…
--
--            select count(*) from public.tenant_connections tc
--              join public.connector_templates ct on ct.id = tc.connector_template_id
--             where ct.scope = 'platform' and tc.status <> 'archived';
--            -- esperado: 0 — nenhuma corretora conectando o que é da plataforma
--
-- ROLLBACK:  alter table public.connector_templates drop column if exists scope;
--            delete from public.connector_templates where slug = 'tavily';
--            -- a conexão arquivada NÃO é ressuscitada: era um rascunho vazio.
--
-- EXPAND-FIRST: sim
-- DESTRUTIVA:   não — arquivar não apaga; a linha continua legível.
-- =============================================================
--
-- O DEFEITO QUE ESTA MIGRATION CORRIGE — E ELE ERA MEU
-- ----------------------------------------------------
-- Na migration 04 eu declarei `firecrawl` como conector exigido por dois
-- Auxiliares (Primeira Mão e o Radar). Como nenhuma corretora tem o Firecrawl
-- "conectado", a tela do Bloco C passaria a dizer, para TODAS elas:
--
--     "Falta conectar: Firecrawl"
--
-- E o botão de ligar ficaria travado — num Auxiliar que funciona perfeitamente,
-- porque a chave do Firecrawl é do AutoBrokers e está no ambiente desde sempre.
--
-- A causa não era o campo: era a falta de um conceito. `connector_templates`
-- tratava tudo como se fosse a mesma coisa.
--
-- A REGRA, EM UMA FRASE
-- ---------------------
--   A DEFINIÇÃO do conector é SEMPRE global.
--   O que muda é QUEM SEGURA A CREDENCIAL.
--
--     platform  a AutoBrokers paga e todas usam.       Firecrawl, Tavily.
--               A corretora não vê card, não conecta
--               nada, e é cobrada pelo uso.
--
--     company   a corretora tem a conta dela.          InfoCap, portal da
--               Serve a todos os usuários e a todos     seguradora, Drive.
--               os Auxiliares dela.
--
--     user      cada pessoa tem a sua.                 Outlook, Gmail, Notion
--               Três usuários, três contas.             pessoal.
--
-- E o caso que parece exceção e não é: **o portal da seguradora**. O catálogo
-- de portais é da plataforma — nós é que mapeamos a Allianz. O login e a senha
-- são da corretora. Por isso ele é `company`: o scope diz quem segura a
-- credencial, não quem escreveu o mapa.

-- -------------------------------------------------------------
-- 1. A camada
-- -------------------------------------------------------------

alter table public.connector_templates
  add column if not exists scope text not null default 'company';

do $$
begin
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.connector_templates'::regclass
       and conname  = 'connector_templates_scope_chk'
  ) then
    alter table public.connector_templates
      add constraint connector_templates_scope_chk
      check (scope in ('platform', 'company', 'user'));
  end if;
end $$;

comment on column public.connector_templates.scope is
  'SPEC-064 — quem segura a credencial. platform: a AutoBrokers paga e todas usam (Firecrawl, Tavily) e a corretora NUNCA vê card. company: a conta da corretora (InfoCap, portal). user: a conta da pessoa (Outlook, Gmail).';

-- -------------------------------------------------------------
-- 2. Quem é de quem
-- -------------------------------------------------------------

update public.connector_templates
   set scope = 'platform',
       description = 'Busca e leitura de páginas da web. É a infraestrutura do AutoBrokers: você não conecta nada e não precisa de chave — o uso entra no seu consumo.',
       updated_at = now()
 where slug = 'firecrawl';

-- Tavily já é usado pelo sistema (TAVILY_API_KEY no ambiente) e nunca esteve
-- no catálogo. Sem registro, ninguém sabe que a plataforma oferece busca —
-- nem o Auxiliar, que não tem como declarar que depende dela.
insert into public.connector_templates
  (slug, name, description, category, provider, connector_kind, auth_type,
   risk_level, requires_approval_default, capabilities, required_fields,
   is_active, scope)
values (
  'tavily', 'Busca na web',
  'Pesquisa na internet com fonte e data. É a infraestrutura do AutoBrokers: você não conecta nada — o uso entra no seu consumo.',
  'knowledge', 'tavily', 'http_tool', 'api_key',
  'low', false,
  '["web_search"]'::jsonb, '[]'::jsonb,
  true, 'platform'
)
on conflict (slug) do update set
  scope = 'platform', is_active = true,
  description = excluded.description, updated_at = now();

-- Os internos também são da plataforma: são o próprio produto, não uma conta.
update public.connector_templates
   set scope = 'platform', updated_at = now()
 where slug in ('internal_conversations', 'internal_documents');

-- -------------------------------------------------------------
-- 3. A conexão que não devia ter existido
-- -------------------------------------------------------------
-- Uma corretora chegou a criar uma linha de Firecrawl (status 'draft', sem
-- segredo). Ela é resultado do card errado, não de um trabalho de alguém.
-- Arquivar, não apagar: a linha continua legível para quem for auditar.

update public.tenant_connections tc
   set status = 'archived',
       metadata = coalesce(tc.metadata, '{}'::jsonb)
                  || jsonb_build_object(
                       'arquivado_por', 'SPEC-064 camadas de conexao',
                       'motivo', 'Firecrawl e da plataforma: a corretora nao conecta nem paga chave propria.'),
       updated_at = now()
  from public.connector_templates ct
 where ct.id = tc.connector_template_id
   and ct.scope = 'platform'
   and tc.status <> 'archived';
