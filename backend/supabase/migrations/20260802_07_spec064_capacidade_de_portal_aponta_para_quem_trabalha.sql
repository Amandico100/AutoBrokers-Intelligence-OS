-- =============================================================
-- MIGRATION: spec064_capacidade_de_portal_aponta_para_quem_trabalha
-- SPEC:      SPEC-064 — Bloco H (a casa limpa)
-- AUTOR:     lider tecnico            DATA: 2026-08-02
-- OBJETIVO:  as cinco capabilities de portal param de apontar para o
--            simulador e passam a apontar para quem entra na Allianz.
--
-- APPLY:     capabilities.provider: 'portal_browser' -> 'portal_worker'
--            nas 5 chaves operational.portal.*
--
-- VERIFY:    select capability_key, provider from public.capabilities
--             where capability_key like 'operational.portal%' order by 1;
--            -- esperado: 5 linhas, todas com provider = 'portal_worker'
--
--            select count(*) from public.capabilities where provider = 'portal_browser';
--            -- esperado: 0
--
-- ROLLBACK:  update public.capabilities set provider = 'portal_browser'
--             where capability_key like 'operational.portal%';
--
-- EXPAND-FIRST: sim — o codigo passa a aceitar OS DOIS providers antes desta
--               migration rodar (PROVIDER_SLUGS ganhou 'portal_worker' e
--               manteve 'portal_browser'). Assim a ordem deploy/migration nao
--               importa, e o rollback nao quebra nada.
-- DESTRUTIVA:   nao
-- =============================================================
--
-- O QUE A AUDITORIA DIZIA, E O QUE A MEDICAO MOSTROU
-- ---------------------------------------------------
-- A auditoria de entrada (02/08) afirmou: "apagar o Portal Browser sem
-- reapontar quebraria o Cobrador em silencio".
--
-- 📊 Medido antes de executar: **nao quebraria — porque nada checa.**
--
--     billing_collection.py consulta capability?  NAO
--     quem consulta operational.portal.*?         so lib/capabilities/registry.ts,
--                                                 que e uma LISTA ESTATICA
--
-- O Cobrador entra no portal, baixa boleto e envia sem passar pelo Capability
-- Resolver. A declaracao existe e nao e exercida.
--
-- Isso e PIOR do que a auditoria supos, e por um motivo que importa: o modelo
-- de governanca esta MENTINDO. Ele declara que ler cobranca no portal exige
-- uma conexao — e 📊 as cinco capabilities resolvem `needs_connection` para
-- TODAS as corretoras, hoje, enquanto o trabalho acontece do lado de fora.
--
-- Um registro que diz "bloqueado" sobre algo que esta rodando nao protege
-- nada: ele so garante que, no dia em que alguem ligar a checagem, o Cobrador
-- para de funcionar sem ninguem entender por que.
--
-- O CONSERTO TEM DUAS METADES
-- ---------------------------
--   1. esta migration: o provider passa a nomear quem faz o trabalho
--   2. o resolver passa a enxergar `portal_accounts` — que e onde a conexao
--      de portal realmente mora (`tenant_connections` nunca teve linha de
--      portal; 📊 a unica conta de portal do sistema e a da Resulta na
--      Allianz, com credencial, desde 08/07)
--
-- Só com as duas a declaracao vira verdade. Com uma so, ela continua
-- decorativa — em outro nome.

update public.capabilities
   set provider   = 'portal_worker',
       updated_at = now()
 where capability_key in (
   'operational.portal.policy.read',
   'operational.portal.billing.read',
   'operational.portal.assistance.read',
   'operational.portal.assistance.prepare',
   'operational.portal.assistance.request'
 );
