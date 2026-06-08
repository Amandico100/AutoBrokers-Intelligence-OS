-- ============================================================
-- 37B2.2 — AGENT DIAGNOSTICS  (SOMENTE LEITURA / SELECT)
-- AutoBrokers Intelligence OS · tabela public.agents (+ legado public.companies)
-- Seguro para colar no Supabase SQL Editor. NÃO altera dados (apenas SELECT).
-- Objetivo: entender por que o chat usa "JARVYS Sandbox" e responde "Não sei".
-- ============================================================
--
-- FLUXO REAL (frontend: app/api/agents/route.ts):
--   SELECT id, name, is_subagent, allow_direct_chat
--   FROM agents
--   WHERE company_id = <empresa do usuário> AND is_active = true
--   ORDER BY created_at ASC
--   (depois filtra: !is_subagent OU allow_direct_chat)
--   O chat usa agents[0]  →  o agente de chat ATIVO MAIS ANTIGO.
-- Por isso um agente "JARVYS Sandbox" antigo é escolhido antes do "AutoBrokers Sandbox" novo.
-- ============================================================

-- 1) Agentes com branding residual JARVYS (nome / slug / prompt)
SELECT a.id, a.company_id, c.company_name, a.name, a.slug,
       a.is_active, a.is_subagent, a.allow_direct_chat,
       a.llm_provider, a.llm_model,
       left(a.agent_system_prompt, 200) AS prompt_preview,
       a.created_at
FROM public.agents a
LEFT JOIN public.companies c ON c.id = a.company_id
WHERE a.name ILIKE '%jarvys%'
   OR a.slug ILIKE '%jarvys%'
   OR a.agent_system_prompt ILIKE '%jarvys%'
ORDER BY a.company_id, a.created_at;

-- 2) AGENTE QUE A UI SELECIONA por empresa (replica a lógica do /api/agents = agents[0])
SELECT DISTINCT ON (a.company_id)
       a.company_id, c.company_name,
       a.id AS selected_agent_id, a.name, a.slug,
       a.llm_provider, a.llm_model,
       left(a.agent_system_prompt, 240) AS prompt_preview,
       a.created_at
FROM public.agents a
LEFT JOIN public.companies c ON c.id = a.company_id
WHERE a.is_active = true
  AND (a.is_subagent = false OR a.allow_direct_chat = true)
ORDER BY a.company_id, a.created_at ASC;  -- mais antigo = agents[0]

-- 3) Quantos agentes ATIVOS de chat existem por empresa (detecta duplicidade)
SELECT a.company_id, c.company_name, count(*) AS active_chat_agents
FROM public.agents a
LEFT JOIN public.companies c ON c.id = a.company_id
WHERE a.is_active = true
  AND (a.is_subagent = false OR a.allow_direct_chat = true)
GROUP BY a.company_id, c.company_name
HAVING count(*) > 1
ORDER BY active_chat_agents DESC;

-- 4) Agentes com prompt restritivo / vazio / sem modelo (possível causa de "Não sei")
SELECT a.id, c.company_name, a.name, a.slug, a.is_active,
       a.llm_provider, a.llm_model,
       (a.agent_system_prompt IS NULL OR a.agent_system_prompt = '') AS prompt_vazio,
       left(a.agent_system_prompt, 200) AS prompt_preview
FROM public.agents a
LEFT JOIN public.companies c ON c.id = a.company_id
WHERE a.agent_system_prompt ILIKE '%não sei%'
   OR a.agent_system_prompt ILIKE '%nao sei%'
   OR a.agent_system_prompt ILIKE '%apenas%context%'
   OR a.agent_system_prompt ILIKE '%somente%context%'
   OR a.agent_system_prompt ILIKE '%apenas%contexto%'
   OR a.agent_system_prompt IS NULL
   OR a.agent_system_prompt = ''
   OR a.llm_model IS NULL
ORDER BY a.company_id, a.created_at;

-- 5) Agentes AutoBrokers já existentes (conferir duplicidade antes/depois da limpeza)
SELECT a.id, c.company_name, a.name, a.slug, a.is_active, a.created_at
FROM public.agents a
LEFT JOIN public.companies c ON c.id = a.company_id
WHERE a.name ILIKE '%autobrokers%' OR a.slug ILIKE '%autobrokers%'
ORDER BY a.company_id, a.created_at;

-- 6) LEGADO: config de agente embutida em public.companies (modelo antigo).
--    O backend usa primariamente public.agents; companies.agent_system_prompt é legado/fallback.
SELECT c.id, c.company_name, c.status, c.agent_enabled, c.use_langchain,
       c.llm_provider, c.llm_model,
       left(c.agent_system_prompt, 200) AS company_prompt_preview
FROM public.companies c
WHERE c.agent_system_prompt ILIKE '%jarvys%'
   OR c.agent_system_prompt ILIKE '%não sei%'
   OR c.agent_system_prompt ILIKE '%nao sei%'
ORDER BY c.company_name;

-- 7) Empresas sandbox / demo / trial (para localizar o tenant de teste)
SELECT id, company_name, status, created_at
FROM public.companies
WHERE company_name ILIKE '%sandbox%'
   OR company_name ILIKE '%demo%'
   OR company_name ILIKE '%teste%'
   OR company_name ILIKE '%test%'
   OR status = 'trial'
ORDER BY created_at;
