-- =============================================================
-- MIGRATION: seguranca_view_cutover
-- SPEC:      Bloco 0 da SPEC-061 §7 — unico ERROR do Security Advisor
-- AUTOR:     Executor Opus                DATA: 2026-07-27
-- OBJETIVO:  fechar `public.v_gateway_cutover_progresso`, que era
--            SECURITY DEFINER e dava SELECT/INSERT/UPDATE/DELETE para
--            `anon` e `authenticated`.
--
-- APPLY:     alter view (security_invoker) + revoke + grant minimo.
-- VERIFY:    ver bloco VERIFY ao final.
-- ROLLBACK:  ver bloco ROLLBACK ao final.
--
-- EXPAND-FIRST: nao se aplica (nao ha coluna nem tabela).
-- DESTRUTIVA:   nao — nenhuma linha e tocada; muda quem PODE LER.
--
-- O QUE ESTAVA ERRADO, EM UMA FRASE
-- ---------------------------------
-- A tabela base `tool_gateway_shadow_diffs` tem RLS ligada e ZERO policy —
-- ou seja, `anon` e `authenticated` estao corretamente barrados NELA. A view,
-- por ser SECURITY DEFINER (padrao do Postgres quando nada e declarado),
-- executava com os poderes do dono (`postgres`) e **contornava exatamente
-- essa barreira**.
--
-- Resultado pratico: quem tivesse a chave publica do projeto — que por
-- definicao vive no navegador — conseguia ler pela view o que a tabela negava:
-- quais papeis de agente existem, quantas decisoes o Gateway toma por dia,
-- em quantas ele diverge do caminho antigo e quantas dao erro.
--
-- Nao e dado de segurado. E telemetria de plataforma, e ela responde a
-- pergunta "o AutoBrokers esta com quantos por cento de divergencia hoje?" —
-- que nao e pergunta de visitante anonimo.
--
-- POR QUE `security_invoker` E NAO SO `revoke`
-- --------------------------------------------
-- `revoke` sozinho resolve HOJE. Mas a view continuaria SECURITY DEFINER, e o
-- proximo `grant` distraido — ou o proximo `GRANT ALL ... TO anon` que o
-- Supabase aplica por padrao ao criar objetos — reabriria o buraco em
-- silencio, sem ninguem mexer nesta migration.
--
-- Com `security_invoker = on`, a view passa a ler COM OS PODERES DE QUEM
-- CHAMA. A RLS da tabela base volta a valer, e a permissao deixa de depender
-- de ninguem lembrar de revogar. A defesa passa a ser estrutural.
--
-- `ucp_connection_summary`, a outra view do schema, ja usa este mesmo modo —
-- esta migration alinha as duas.
-- =============================================================

alter view public.v_gateway_cutover_progresso set (security_invoker = on);

-- Ninguem que chega pelo navegador le telemetria de plataforma.
revoke all on public.v_gateway_cutover_progresso from anon;
revoke all on public.v_gateway_cutover_progresso from authenticated;
revoke all on public.v_gateway_cutover_progresso from public;

-- O backend usa service role, que ignora RLS por natureza. E o unico que
-- precisa ler — e, com `security_invoker`, o unico que CONSEGUE.
grant select on public.v_gateway_cutover_progresso to service_role;

comment on view public.v_gateway_cutover_progresso is
  'Telemetria do cutover do Tool Gateway, agregada por dia e papel. '
  'security_invoker=on e leitura apenas por service_role: a RLS de '
  'tool_gateway_shadow_diffs vale tambem aqui. Bloco 0 da SPEC-061 §7.';

-- =============================================================
-- VERIFY
-- =============================================================
-- select c.relname,
--        array_to_string(c.reloptions, ',') as opcoes,
--        (select string_agg(distinct g.grantee, ', ')
--           from information_schema.role_table_grants g
--          where g.table_schema='public' and g.table_name=c.relname) as grants
--   from pg_class c join pg_namespace n on n.oid=c.relnamespace
--  where n.nspname='public' and c.relname='v_gateway_cutover_progresso';
--   -- esperado: opcoes contem 'security_invoker=true'
--   --           grants SEM 'anon' e SEM 'authenticated'
--
-- -- E o Advisor precisa parar de acusar:
-- --   get_advisors(type='security') -> nenhum lint 'security_definer_view'
--
-- =============================================================
-- ROLLBACK
-- =============================================================
-- Restaura o estado anterior EXATO. Note que ele e o estado inseguro — este
-- rollback existe para uma emergencia de leitura, nao como alternativa valida.
--
-- alter view public.v_gateway_cutover_progresso set (security_invoker = off);
-- grant all on public.v_gateway_cutover_progresso to anon;
-- grant all on public.v_gateway_cutover_progresso to authenticated;
-- =============================================================
