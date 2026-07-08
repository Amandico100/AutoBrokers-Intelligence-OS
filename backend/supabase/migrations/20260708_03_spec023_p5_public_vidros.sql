-- SPEC-023 P5 - portais publicos nao devem pedir login/senha no dashboard.
-- O acesso de vidros atual e publico; credenciais por corretora nao se aplicam.

update public.portals
set
  cred_kind = 'public',
  updated_at = now()
where key in ('vidros_abraseuatendimento', 'vidros_agendeseuservico');

