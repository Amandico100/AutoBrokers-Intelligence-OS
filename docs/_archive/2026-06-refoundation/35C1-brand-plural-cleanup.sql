-- BATCH 35C1 - AutoBrokers plural branding cleanup
-- Target: Supabase SANDBOX only.
--
-- Manual execution only: copy this file into the Supabase SQL Editor after review.
-- Do not run against the current/old AutoBrokers production database.
--
-- Safety rules:
-- - idempotent updates
-- - no deletes
-- - no credit/user/company/document/cost changes
-- - no migration creation
-- - conversation history text is diagnosed, not rewritten by default

begin;

-- 1. Diagnostics: agents with old visible branding.
select
  id,
  company_id,
  name,
  slug,
  is_active,
  is_subagent,
  allow_direct_chat,
  updated_at
from public.agents
where coalesce(name, '') ~* '(jarvys|\mautobroker\M|agent smith|smith ai|\msmith\M)'
   or coalesce(slug, '') ~* '(jarvys|\mautobroker\M|\msmith\M)'
   or coalesce(agent_system_prompt, '') ~* '(jarvys|\mautobroker\M|agent smith|smith ai|\msmith\M)'
order by updated_at desc nulls last;

-- 2. Diagnostics: conversations with technical agent-name/title branding.
select
  id,
  company_id,
  agent_id,
  agent_name,
  title,
  updated_at
from public.conversations
where coalesce(agent_name, '') ~* '(jarvys|\mautobroker\M|agent smith|smith ai|\msmith\M)'
   or coalesce(title, '') ~* '^(jarvys|autobroker|agent smith|smith agent|smith|auto broker)( sandbox)?$'
   or coalesce(title, '') ~* '^(chat|conversa) (com|with) (jarvys|autobroker|agent smith|smith)'
order by updated_at desc nulls last;

-- 3. Diagnostics only: conversation logs may contain historical user/assistant text.
-- Do not update user_question or assistant_response by default.
select
  id,
  company_id,
  agent_id,
  session_id,
  created_at,
  left(coalesce(user_question, ''), 160) as user_question_sample,
  left(coalesce(assistant_response, ''), 160) as assistant_response_sample,
  left(coalesce(internal_steps::text, ''), 240) as internal_steps_sample
from public.conversation_logs
where coalesce(user_question, '') ~* '(jarvys|\mautobroker\M|agent smith|smith ai|\msmith\M)'
   or coalesce(assistant_response, '') ~* '(jarvys|\mautobroker\M|agent smith|smith ai|\msmith\M)'
   or coalesce(internal_steps::text, '') ~* '(jarvys|\mautobroker\M|agent smith|smith ai|\msmith\M)'
order by created_at desc nulls last
limit 50;

-- 4. Update agents to the approved visible naming.
update public.agents
set
  name = case
    when coalesce(name, '') ilike '%sandbox%'
      or coalesce(slug, '') ilike '%sandbox%'
      or coalesce(name, '') ilike '%jarvys%'
      or coalesce(slug, '') ilike '%jarvys%'
      then 'AutoBrokers Sandbox'
    else 'AutoBrokers'
  end,
  slug = case
    when coalesce(slug, '') ilike '%sandbox%'
      or coalesce(slug, '') ilike '%jarvys%'
      then 'autobrokers-sandbox'
    when coalesce(slug, '') ilike '%autobrokers%'
      then slug
    when coalesce(slug, '') ilike '%autobroker%'
      then replace(slug, 'autobroker', 'autobrokers')
    when coalesce(slug, '') ilike '%smith%'
      then regexp_replace(slug, 'smith', 'autobrokers', 'gi')
    else slug
  end,
  agent_system_prompt = regexp_replace(
    regexp_replace(
      regexp_replace(
        regexp_replace(
          regexp_replace(coalesce(agent_system_prompt, ''), 'JARVYS', 'AutoBrokers', 'gi'),
          '\mAutoBroker\M', 'AutoBrokers', 'g'
        ),
        'Agent Smith', 'AutoBrokers', 'gi'
      ),
      'Smith AI', 'AutoBrokers', 'gi'
    ),
    '\mSmith\M', 'AutoBrokers', 'gi'
  ),
  updated_at = now()
where coalesce(name, '') ~* '(jarvys|\mautobroker\M|agent smith|smith ai|\msmith\M)'
   or coalesce(slug, '') ~* '(jarvys|\mautobroker\M|\msmith\M)'
   or coalesce(agent_system_prompt, '') ~* '(jarvys|\mautobroker\M|agent smith|smith ai|\msmith\M)';

-- 5. Update conversation technical agent labels.
update public.conversations
set
  agent_name = case
    when coalesce(agent_name, '') ilike '%sandbox%'
      or coalesce(agent_name, '') ilike '%jarvys%'
      then 'AutoBrokers Sandbox'
    else 'AutoBrokers'
  end,
  updated_at = now()
where coalesce(agent_name, '') ~* '(jarvys|\mautobroker\M|agent smith|smith ai|\msmith\M)';

-- 6. Update only clearly automatic technical titles.
-- Real user-created conversation titles are intentionally left untouched.
update public.conversations
set
  title = regexp_replace(
    regexp_replace(
      regexp_replace(
        regexp_replace(
          regexp_replace(title, 'JARVYS', 'AutoBrokers', 'gi'),
          '\mAutoBroker\M', 'AutoBrokers', 'g'
        ),
        'Agent Smith', 'AutoBrokers', 'gi'
      ),
      'Smith Agent', 'AutoBrokers', 'gi'
    ),
    '\mSmith\M', 'AutoBrokers', 'gi'
  ),
  updated_at = now()
where coalesce(title, '') ~* '^(jarvys|autobroker|agent smith|smith agent|smith|auto broker)( sandbox)?$'
   or coalesce(title, '') ~* '^(chat|conversa) (com|with) (jarvys|autobroker|agent smith|smith)';

-- 7. Post-update diagnostics.
select
  id,
  company_id,
  name,
  slug,
  updated_at
from public.agents
where coalesce(name, '') ~* '(jarvys|\mautobroker\M|agent smith|smith ai|\msmith\M)'
   or coalesce(slug, '') ~* '(jarvys|\mautobroker\M|\msmith\M)'
   or coalesce(agent_system_prompt, '') ~* '(jarvys|\mautobroker\M|agent smith|smith ai|\msmith\M)'
order by updated_at desc nulls last;

select
  id,
  company_id,
  agent_id,
  agent_name,
  title,
  updated_at
from public.conversations
where coalesce(agent_name, '') ~* '(jarvys|\mautobroker\M|agent smith|smith ai|\msmith\M)'
   or coalesce(title, '') ~* '^(jarvys|autobroker|agent smith|smith agent|smith|auto broker)( sandbox)?$'
   or coalesce(title, '') ~* '^(chat|conversa) (com|with) (jarvys|autobroker|agent smith|smith)'
order by updated_at desc nulls last;

commit;
