-- =============================================================
-- MIGRATION: spec065_o_portal_de_vidros_e_publico
-- SPEC:      SPEC-065 — portal de vidros ponta a ponta (bloco 7.1)
-- AUTOR:     lider tecnico            DATA: 2026-08-04
-- OBJETIVO:  destravar o acionamento de vidros nas DUAS travas que nao sao
--            decisao de ninguem — sao contradicoes do proprio registro.
--
-- APPLY:     1) tenant.portal.execute ganha provider ('portal_worker')
--            2) as tres capabilities de ASSISTENCIA param de exigir conexao
--
-- VERIFY:    select capability_key, provider, requires_connection
--              from public.capabilities where capability_key like '%portal%'
--             order by 1;
--            -- esperado: nenhum provider nulo;
--            --           as 3 'assistance' com requires_connection = false;
--            --           policy.read/billing.read/tenant.execute = true
--
--            select count(*) from public.capabilities
--             where capability_key like '%portal%' and provider is null;
--            -- esperado: 0
--
-- ROLLBACK:  update public.capabilities set provider = null
--              where capability_key = 'tenant.portal.execute';
--            update public.capabilities set requires_connection = true
--              where capability_key like 'operational.portal.assistance.%';
--
-- EXPAND-FIRST: sim — nada e removido; dois campos mudam de valor. O codigo
--               que le (capability_resolver) ja trata os dois estados.
-- DESTRUTIVA:   nao
-- =============================================================
--
-- TRAVA 1 — a permissao que nunca poderia ficar pronta
-- -----------------------------------------------------
-- 📊 Medido em 04/08/2026 (Supabase dcajcvlzcjbmyapmklil):
--
--     capability_key         provider   requires_connection
--     tenant.portal.execute  NULL       true
--
-- O resolver faz `PROVIDER_SLUGS.get(cap.provider or "", [])`. Com provider
-- nulo isso e uma lista VAZIA, e `any(s in connected for s in [])` e sempre
-- False. Resultado: **needs_connection para toda corretora, para sempre.**
--
-- Nao existe conexao que resolva. Nao ha tela onde clicar. A capability nasceu
-- inalcancavel em 06/07 e ficou assim quatro semanas, enquanto o time discutia
-- se o Atendente "podia" usar o portal. Podia; nunca teve como.
--
-- A SPEC-064 Bloco H ja tinha corrigido as CINCO capabilities `operational.*`.
-- Esta aqui — `tenant.*` — nao estava na lista e passou batido.
--
-- TRAVA 2 — exigir credencial de um portal que nao tem login
-- -----------------------------------------------------------
-- 📊 Medido em 04/08/2026, tabela `portals`:
--
--     category   cred_kind        n
--     corretor   login_password   15
--     vidros     public            2     <- abraseuatendimento + agendeseuservico
--
-- O proprio registro ja declara: **o portal de vidros e publico.** Nao tem
-- login, nao tem senha, nao ha o que cadastrar. E, ainda assim, as tres
-- capabilities de assistencia exigiam `requires_connection = true` — que o
-- resolver so satisfaz com uma linha em `portal_accounts`.
--
-- 📊 E existe UMA linha de portal_accounts no sistema inteiro: Resulta /
-- allianz_corretor, de 08/07. Ou seja: a AutoFleet — e qualquer corretora que
-- entrar amanha — resolvia `needs_connection` para abrir vidros, e a unica
-- forma de "conectar" seria cadastrar credencial de um portal que nao pede
-- credencial.
--
-- A separacao correta ja existe nos dados e e limpa:
--   assistencia (vidros)  -> publico      -> nao exige conexao
--   policy / billing      -> corretor     -> exige, e continua exigindo
--
-- Nenhuma protecao e perdida: o Cobrador entra na Allianz com login e senha, e
-- a exigencia dele fica de pe. O que cai e a exigencia de credencial para
-- abrir uma pagina que qualquer pessoa abre no navegador.
--
-- O QUE ESTA MIGRATION **NAO** FAZ
-- ---------------------------------
-- Nao liga `tenant.portal.execute` para o papel `attendance`. Aquilo continua
-- desligado, com o motivo escrito na propria linha:
--   "SPEC-053 5.2 - Atendimento externo nao recebe ferramenta generica".
--
-- E esta certo. A SPEC-053 5.2 diz, literalmente: "corredores definidos",
-- "menor privilegio", "sem ferramentas genericas". Uma capability chamada
-- `portal.execute` — entre em qualquer portal e faca qualquer coisa — e
-- exatamente a ferramenta generica que ela proibe para quem conversa com
-- desconhecidos no WhatsApp.
--
-- O `portal_action` nao e generico: e uma jornada fixa (`vidros_lanternas` /
-- `abrir_atendimento`), com parametros montados no servidor a partir da
-- InfoCap e `confirm=False` cravado no codigo. Isso e um CORREDOR DEFINIDO —
-- o que a 053 manda usar. E ele ja tem chave propria, ja ligada para o
-- Atendente: `operational.portal.assistance.prepare` (preparar, sem enviar) e
-- `operational.portal.assistance.request` (enviar, com aprovacao).
--
-- Nao havia conflito canonico entre a SPEC-053 e a SPEC-020. Havia um portao
-- conferindo a chave errada: o `graph.py` exigia a chave GENERICA para soltar
-- uma ferramenta ESPECIFICA. Isso se conserta no codigo, nao no banco.

-- 1) a permissao generica passa a nomear quem faz o trabalho
update public.capabilities
   set provider   = 'portal_worker',
       updated_at = now()
 where capability_key = 'tenant.portal.execute'
   and provider is null;

-- 2) assistencia = vidros = portal publico: nao ha conexao a exigir
update public.capabilities
   set requires_connection = false,
       updated_at          = now()
 where capability_key in (
   'operational.portal.assistance.read',
   'operational.portal.assistance.prepare',
   'operational.portal.assistance.request'
 )
   and requires_connection is distinct from false;
