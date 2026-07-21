-- SPEC-047 — (1) RLS nas tabelas internas que estavam expostas; (2) vínculo
-- usuário↔corretora (multi-empresa: o mesmo e-mail acessa mais de uma).

-- 1) RLS ON nas 6 tabelas apontadas pelo advisor. São todas service-role-only
-- (backend/Next admin usam a service key, que bypassa RLS). Sem policies =
-- anon/authenticated ficam SEM acesso — exatamente o desejado.
ALTER TABLE public.billing_sent_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ura_maps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.broker_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.playbook_overlays ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_scorecards ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_activities ENABLE ROW LEVEL SECURITY;

-- 2) Vínculos usuário↔corretora. users_v2.company_id segue sendo a empresa
-- PRIMÁRIA (dado legado, nada quebra); company_members permite acessos extras.
-- A sessão do dashboard troca de empresa ativa validando contra esta tabela.
CREATE TABLE IF NOT EXISTS public.company_members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users_v2(id) ON DELETE CASCADE,
  company_id uuid NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  role varchar(40) NOT NULL DEFAULT 'member',
  is_owner boolean NOT NULL DEFAULT false,
  status varchar(20) NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, company_id)
);
ALTER TABLE public.company_members ENABLE ROW LEVEL SECURITY;

-- Seed: todo usuário real de dashboard vira membro da própria empresa
-- (exclui os usuários sintéticos de WhatsApp *_@whatsapp.smith.ai).
INSERT INTO public.company_members (user_id, company_id, role, is_owner, status)
SELECT u.id, u.company_id, COALESCE(u.role, 'member'), COALESCE(u.is_owner, false), 'active'
FROM public.users_v2 u
WHERE u.company_id IS NOT NULL
  AND u.email NOT LIKE '%@whatsapp.smith.ai'
  AND u.deleted_at IS NULL
ON CONFLICT (user_id, company_id) DO NOTHING;
