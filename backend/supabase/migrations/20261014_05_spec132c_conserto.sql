-- =============================================================
-- MIGRATION: 20261014_05_spec132c_conserto
-- SPEC:      SPEC-132-C — o conserto único (o WhatsApp do corretor como atalho do chat)
-- AUTOR:     builder do conserto (Opus 5.5)            DATA: 2026-10-14
-- OBJETIVO:  o estado DURÁVEL do atalho por TELEFONE (laudo do red team, P2 e P3):
--            · "qual corretora?" vai UMA vez por janela, e a fala que a provocou espera a escolha — sem depender do
--              Redis (antes: Redis fora = a escolha se perdia e o "2" caía como texto no chat da outra corretora);
--            · o teto de mensagens ENVIADAS por dia por telefone conta TODA mensagem que o número do AutoBrokers manda
--              (pergunta, "sem agente", ativação, resposta, a volta da cotação) — antes, só as falas do corretor.
--            Uma linha por telefone, chave = HMAC do telefone (nunca o número em claro); a fala guardada é CIFRADA
--            (portal_vault, o mesmo cofre do `canal_conversas.estado_cifrado` do QCM).
--
-- 📊 ANTES (14/10/2026, leitura do REPOSITÓRIO — o builder não tem banco; o gerente confere o banco vivo com o PRÉ):
--    · nenhuma tabela `whatsapp_atalho_estado` (`grep -rn whatsapp_atalho_estado backend/supabase` → só este arquivo).
--    · o padrão copiado: `canal_conversas` (20261007_01_spec133a_canal.sql) — estado_cifrado + enviadas_dia/enviadas_no_dia.
--
-- PRÉ (o GERENTE roda antes · esperado: 0 · 1):
--   select (select count(*) from pg_class where relnamespace='public'::regnamespace and relname='whatsapp_atalho_estado') ja_existe,
--          (select count(*) from pg_class where relnamespace='public'::regnamespace and relname='whatsapp_atalho_tentativas') migration_03;
--   ⚠️ migration_03 = 0 → aplique a 20261014_03 antes (o atalho inteiro depende dela).
--
-- APPLY (pelo GERENTE — o builder NÃO aplica; um arquivo, idempotente, expand-only):
--   A. tabela `whatsapp_atalho_estado` (telefone_hash PK · estado_cifrado · enviadas_dia · enviadas_no_dia ·
--      atualizado_em) + CHECKs (hash HMAC-SHA256 hex · contador ≥ 0).
--   B. RLS LIGADA, SEM policy, REVOKE de anon/authenticated (o backend usa service role). COMMENTs.
--   C. índice do atualizado_em (a limpeza futura — P7 do juiz, pendência).
--
-- VERIFY (read-only · esperado: 1 · 1 · 2 · 0 · 0):
--   select (select count(*) from pg_class where relnamespace='public'::regnamespace and relkind='r' and relrowsecurity
--             and relname='whatsapp_atalho_estado') tabela_com_rls,
--          (select count(*) from information_schema.columns where table_schema='public'
--             and table_name='whatsapp_atalho_estado' and column_name='enviadas_no_dia') col_contador,
--          (select count(*) from pg_constraint where conrelid='public.whatsapp_atalho_estado'::regclass
--             and conname in ('ck_whatsapp_atalho_estado_hash','ck_whatsapp_atalho_estado_contador')) checks,
--          (select count(*) from pg_policies where schemaname='public' and tablename='whatsapp_atalho_estado') policies,
--          (select count(*) from information_schema.role_table_grants where table_schema='public'
--             and table_name='whatsapp_atalho_estado' and grantee in ('anon','authenticated')) grants_publicos;
--
-- VERIFY comportamental (o DO desfaz o que testa — raise P0001 no fim; NADA fica):
--   do $$
--   declare res text[] := '{}';
--   begin
--     begin
--       begin insert into public.whatsapp_atalho_estado (telefone_hash) values ('5511912345678');
--             res := res || 'telefone_em_claro=ACEITO'::text;
--       exception when check_violation then res := res || 'telefone_em_claro=recusado'::text; end;
--       insert into public.whatsapp_atalho_estado (telefone_hash, enviadas_dia, enviadas_no_dia)
--         values (repeat('a',64), current_date, 1);
--       begin insert into public.whatsapp_atalho_estado (telefone_hash) values (repeat('a',64));
--             res := res || 'dois_estados_mesmo_telefone=ACEITO'::text;
--       exception when unique_violation then res := res || 'dois_estados_mesmo_telefone=recusado'::text; end;
--       begin update public.whatsapp_atalho_estado set enviadas_no_dia = -1 where telefone_hash = repeat('a',64);
--             res := res || 'contador_negativo=ACEITO'::text;
--       exception when check_violation then res := res || 'contador_negativo=recusado'::text; end;
--       raise exception 'DESFAZ %', array_to_string(res, ' · ') using errcode = 'P0001';
--     exception when sqlstate 'P0001' then raise notice '%', sqlerrm;
--     end;
--   end $$;
--   → esperado no NOTICE: DESFAZ telefone_em_claro=recusado · dois_estados_mesmo_telefone=recusado · contador_negativo=recusado
--
-- ROLLBACK (escrito ANTES):
--   drop table if exists public.whatsapp_atalho_estado;
--   ⚠️ depois dele o atalho CALA em todo envio (o teto de envios não é lido → recusa: fail-closed) até a tabela voltar;
--      nenhum outro dado se perde (só perguntas "qual corretora?" pendentes e o contador do dia).
--
-- EXPAND-FIRST: sim
-- DESTRUTIVA:   não
-- =============================================================

-- A. o estado do atalho por telefone ----------------------------------------------------------------------------------
create table if not exists public.whatsapp_atalho_estado (
  telefone_hash    text primary key,
  estado_cifrado   text null,
  enviadas_dia     date null,
  enviadas_no_dia  integer not null default 0,
  atualizado_em    timestamptz not null default now()
);

do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'ck_whatsapp_atalho_estado_hash') then
    -- o telefone em claro NUNCA cabe aqui: só o HMAC-SHA256 em hexadecimal (o mesmo de whatsapp_atalho_tentativas)
    alter table public.whatsapp_atalho_estado add constraint ck_whatsapp_atalho_estado_hash
      check (telefone_hash ~ '^[0-9a-f]{64}$');
  end if;
  if not exists (select 1 from pg_constraint where conname = 'ck_whatsapp_atalho_estado_contador') then
    alter table public.whatsapp_atalho_estado add constraint ck_whatsapp_atalho_estado_contador
      check (enviadas_no_dia >= 0);
  end if;
end $$;

-- C. a limpeza futura (pendência P7 do juiz) procura por idade -------------------------------------------------------
create index if not exists ix_whatsapp_atalho_estado_atualizado
  on public.whatsapp_atalho_estado (atualizado_em);

-- B. só o backend ------------------------------------------------------------------------------------------------------
alter table public.whatsapp_atalho_estado enable row level security;
revoke all on public.whatsapp_atalho_estado from anon, authenticated;

comment on table public.whatsapp_atalho_estado is
  'SPEC-132-C conserto (P2/P3 do red team): o estado do atalho por TELEFONE — a pergunta "qual corretora?" pendente '
  '(uma vez por janela, com a fala que a provocou, CIFRADA pelo portal_vault) e o contador de mensagens ENVIADAS hoje '
  'pelo número do AutoBrokers a este telefone (toda mensagem conta). Chave = HMAC do telefone, nunca o número. RLS sem '
  'policy: só o backend (service role) lê (app/services/atalho/estado.py).';
comment on column public.whatsapp_atalho_estado.estado_cifrado is
  'SPEC-132-C: {"perguntou_em": iso, "fala": texto} cifrado (portal_vault). Nulo = nada pendente.';
comment on column public.whatsapp_atalho_estado.enviadas_no_dia is
  'SPEC-132-C: quantas mensagens o número do AutoBrokers mandou a este telefone em `enviadas_dia` (dia de Brasília).';
