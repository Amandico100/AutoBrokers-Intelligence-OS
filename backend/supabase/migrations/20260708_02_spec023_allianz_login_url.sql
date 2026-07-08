-- SPEC-023 - AllianzNet corretor: URL validada no piloto.
-- Mantem o registro global alinhado com a journey allianz_corretor.

update public.portals
set
  login_url = 'https://www.allianznet.com.br/ngx-azb-epac/public/home',
  updated_at = now()
where key = 'allianz_corretor'
  and login_url <> 'https://www.allianznet.com.br/ngx-azb-epac/public/home';
