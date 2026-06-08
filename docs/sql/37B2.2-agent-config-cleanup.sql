-- ============================================================
-- 37B2.2 — AGENT CONFIG CLEANUP  (MANUAL · IDEMPOTENTE)
-- AutoBrokers Intelligence OS · tabela public.agents
-- Rodar SOMENTE depois de revisar 37B2.2-agent-diagnostics.sql.
-- Faz UPDATE (branding + prompt). NÃO faz DELETE.
-- NÃO toca: conversas, mensagens, usuários, empresas, documentos, logs, créditos.
-- Colunas usadas existem no schema real: name, slug, agent_system_prompt,
--   is_active, is_subagent, allow_direct_chat, company_id, created_at, updated_at.
-- ============================================================

-- ----------------------------------------------------------------
-- PASSO 1 — PREVIEW (leitura): linhas que serão afetadas pelo PASSO 2.
--           Rode isto primeiro e confira o resultado antes de seguir.
-- ----------------------------------------------------------------
SELECT id, company_id, name, slug, is_active, is_subagent, allow_direct_chat,
       left(agent_system_prompt, 160) AS prompt_preview, created_at
FROM public.agents
WHERE name ILIKE '%jarvys%'
   OR slug ILIKE '%jarvys%'
   OR agent_system_prompt ILIKE '%jarvys%';

-- ----------------------------------------------------------------
-- PASSO 2 — Rebrand de NOME + PROMPT canônico nos agentes residuais JARVYS.
--           Idempotente: após rodar, nenhum agente tem 'jarvys' em name/prompt,
--           então re-executar não altera nada.
-- ----------------------------------------------------------------
UPDATE public.agents
SET name = 'AutoBrokers',
    agent_system_prompt = $autobrokers_prompt$Você é o AutoBrokers, o copiloto operacional de IA da corretora de seguros.

Sua função é ajudar o corretor e a equipe da corretora a trabalhar melhor: atendimentos, documentos, seguradoras, apólices, sinistros, assistências, renovações, clientes e processos operacionais.

Regras de resposta:
1. Responda com clareza, objetividade e linguagem profissional acessível.
2. Use o conhecimento geral da LLM para perguntas gerais, conceitos, raciocínio, explicações, geografia, matemática, escrita e orientação operacional.
3. Use os documentos, memórias e a base de conhecimento da corretora quando a pergunta depender de dados internos, regras da corretora, documentos enviados, seguradoras configuradas, clientes, atendimentos ou histórico.
4. Se a pergunta depender de dado interno e esse dado não estiver disponível, diga claramente que não encontrou essa informação na base da corretora e explique qual dado seria necessário.
5. Não responda "não sei" para perguntas gerais básicas quando puder responder com conhecimento geral.
6. Nunca invente dados internos da corretora, clientes, apólices, sinistros, pagamentos ou documentos.
7. Não exponha informações sensíveis sem necessidade.
8. Se uma ação externa real for solicitada, explique que ela precisa de confirmação humana quando aplicável.
9. Não use os nomes Smith, Agent Smith ou JARVYS na experiência do usuário.
10. O nome do agente principal é sempre AutoBrokers.

Comportamento esperado:
- Pergunta geral: responda normalmente.
- Pergunta sobre a corretora: use o contexto/documentos quando disponíveis.
- Dado interno ausente: explique a ausência sem inventar.
- Solicitação operacional: organize os próximos passos com segurança.$autobrokers_prompt$,
    updated_at = now()
WHERE name ILIKE '%jarvys%'
   OR agent_system_prompt ILIKE '%jarvys%';

-- ----------------------------------------------------------------
-- PASSO 3 — Slug coerente (jarvys → autobrokers), GUARDADO contra colisão
--           de slug único na mesma empresa. Idempotente.
-- ----------------------------------------------------------------
UPDATE public.agents a
SET slug = regexp_replace(lower(a.slug), 'jarvys', 'autobrokers', 'g'),
    updated_at = now()
WHERE a.slug ILIKE '%jarvys%'
  AND NOT EXISTS (
    SELECT 1 FROM public.agents b
    WHERE b.company_id = a.company_id
      AND b.id <> a.id
      AND b.slug = regexp_replace(lower(a.slug), 'jarvys', 'autobrokers', 'g')
  );

-- ----------------------------------------------------------------
-- PASSO 4 (OPCIONAL) — Aplicar o prompt canônico ao AGENTE ATIVO que NÃO é JARVYS
--   mas tem prompt curto/restritivo/placeholder (ex.: o "AutoBrokers Sandbox"
--   criado pelo bootstrap, slug 'autobrokers-sandbox').
--   Descomente e ajuste o WHERE conforme o diagnóstico (slug OU id do agente ativo).
-- ----------------------------------------------------------------
-- UPDATE public.agents
-- SET agent_system_prompt = $autobrokers_prompt$Você é o AutoBrokers, o copiloto operacional de IA da corretora de seguros.
--
-- Sua função é ajudar o corretor e a equipe da corretora a trabalhar melhor: atendimentos, documentos, seguradoras, apólices, sinistros, assistências, renovações, clientes e processos operacionais.
--
-- Regras de resposta:
-- 1. Responda com clareza, objetividade e linguagem profissional acessível.
-- 2. Use o conhecimento geral da LLM para perguntas gerais, conceitos, raciocínio, explicações, geografia, matemática, escrita e orientação operacional.
-- 3. Use os documentos, memórias e a base de conhecimento da corretora quando a pergunta depender de dados internos.
-- 4. Se faltar dado interno, diga que não encontrou na base da corretora e qual dado seria necessário.
-- 5. Não responda "não sei" para perguntas gerais básicas.
-- 6. Nunca invente dados internos. 7. Não exponha dados sensíveis sem necessidade.
-- 8. Ação externa real exige confirmação humana quando aplicável.
-- 9. Não use Smith/Agent Smith/JARVYS. 10. O nome do agente é sempre AutoBrokers.$autobrokers_prompt$,
--     updated_at = now()
-- WHERE slug = 'autobrokers-sandbox';   -- ajuste para o id/slug do agente ATIVO da sua empresa sandbox

-- ----------------------------------------------------------------
-- PASSO 5 (OPCIONAL · LEGADO) — companies.agent_system_prompt.
--   SÓ rode se o diagnóstico (query 6) mostrar JARVYS/"não sei" no prompt legado
--   da empresa E se o backend ainda usar esse campo como fallback.
-- ----------------------------------------------------------------
-- UPDATE public.companies
-- SET agent_system_prompt = '(use o mesmo prompt canônico do PASSO 2)',
--     agent_config_updated_at = now()
-- WHERE agent_system_prompt ILIKE '%jarvys%';

-- ----------------------------------------------------------------
-- NOTA — MÚLTIPLOS AGENTES ATIVOS
-- O chat usa o agente de chat ATIVO MAIS ANTIGO (created_at ASC). Se a query 3 do
-- diagnóstico mostrar mais de um por empresa, NÃO desative em massa. Decida qual deve
-- ser o ativo e, se necessário, desative os indesejados individualmente:
--   UPDATE public.agents SET is_active = false, updated_at = now() WHERE id = '<agent_id>';
-- (Não apaga nada; apenas oculta o agente do /api/agents.)
-- ----------------------------------------------------------------
