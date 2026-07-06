-- SPEC-020 — Seed dos portais de CORRETOR das demais seguradoras (registro global).
-- EXPAND-ONLY, idempotente por key. URLs públicas (portal_base_do_corretor do
-- registro de portais). Login/senha continuam por corretora em portal_accounts.
--
-- APPLY:   SQL Editor do Supabase (idempotente).
-- VERIFY:  select count(*) from public.portals;  -- deve incluir as novas
-- ROLLBACK: delete from public.portals where key in (
--   'hdi_corretor','mapfre_corretor','porto_corretor','sura_corretor',
--   'segurosunimed_corretor','sompo_corretor','suhai_corretor','sulamerica_corretor',
--   'tokiomarine_corretor','yelum_corretor','zurich_corretor');

insert into public.portals (key, name, login_url, category, insurer_key, sort_order)
select v.key, v.name, v.login_url, 'corretor', v.insurer_key, v.sort_order
from (values
  ('hdi_corretor',          'HDI Digital — Corretor',        'https://www.hdi.com.br/hdidigital/',                          'hdi',           70),
  ('mapfre_corretor',       'MAPFRE — Negócios',             'https://negocios.mapfre.com.br/',                             'mapfre',        80),
  ('porto_corretor',        'Porto — Corretor Online',       'https://corretor.portoseguro.com.br/corretoronline/',         'porto',         90),
  ('sura_corretor',         'SURA — Portal do Corretor',     'https://www.segurossura.com.br/acesso-portal/corretor.html',  'sura',          100),
  ('segurosunimed_corretor','Seguros Unimed — Corretor',     'https://www.segurosunimed.com.br/login-corretor',             'seguros_unimed',110),
  ('sompo_corretor',        'Sompo — Portal do Corretor',    'https://corretor.sompo.com.br/PortalCorretor_Th/Login.aspx',  'sompo',         120),
  ('suhai_corretor',        'Suhai — Área do Corretor',      'https://suhaiseguradora.com/area-do-corretor/',               'suhai',         130),
  ('sulamerica_corretor',   'SulAmérica — Corretor',         'https://corretor.sulamericaseguros.com.br/',                  'sulamerica',    140),
  ('tokiomarine_corretor',  'Tokio Marine — Portal Parceiros','https://portalparceiros.tokiomarine.com.br/',                'tokio_marine',  150),
  ('yelum_corretor',        'Yelum — Espaço Corretor',       'https://novomeuespacocorretor.yelumseguros.com.br/home',      'yelum',         160),
  ('zurich_corretor',       'Zurich — Espaço Parceiros',     'https://espacoparceiros.zurich.com.br/',                      'zurich',        170)
) as v(key, name, login_url, insurer_key, sort_order)
where not exists (select 1 from public.portals p where p.key = v.key);
