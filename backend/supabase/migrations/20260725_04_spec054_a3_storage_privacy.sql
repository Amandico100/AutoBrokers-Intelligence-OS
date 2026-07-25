-- =============================================================
-- MIGRATION: spec054_a3_storage_privacy
-- SPEC:      SPEC-054 - Foundation Hardening, Bloco A
-- DATA:      2026-07-25
-- ESTADO:    PENDENTE — NAO APLICAR ANTES DO DEPLOY DO PROXY
--
-- OBJETIVO:  Tornar privados os buckets com conteudo de corretora e
--            remover as policies abertas para o papel PUBLIC.
--
-- PRE-CONDICAO OBRIGATORIA (SPEC-054 §7.3.2 - expand antes de contract):
--   1. lib/storage/resolver.ts em producao;
--   2. app/api/storage/[...path]/route.ts em producao;
--   3. app/api/upload/route.ts atualizado em producao;
--   4. app/admin/conversations/page.tsx sem upload direto do browser;
--   5. migration A4 (backfill) aplicada  -> FEITO em 2026-07-25;
--   6. renderizacao das 12 midias validada pelo proxy autenticado.
--
--   Aplicar esta migration ANTES do deploy quebra a leitura de midia
--   no Admin. Nao ha risco para cliente externo: o preflight provou
--   que nenhuma URL publica foi enviada externamente.
--
-- APPLY:     buckets privados + remocao das policies PUBLIC de escrita
--            e leitura ampla; avatars mantem leitura publica apenas.
-- VERIFY:    ver bloco no fim do arquivo.
-- ROLLBACK:  backup/SPEC-054-A-20260725/rollback/03-rollback-a3-storage.sql
--            (preferir proxy server-side a reabrir bucket)
--
-- EXPAND-FIRST: sim  ·  DESTRUTIVA: nao - nenhum objeto e removido
-- =============================================================

-- ---------------------------------------------------------------
-- 1. Buckets privados
--    portal-evidence ja e privado e NAO e tocado.
-- ---------------------------------------------------------------
UPDATE storage.buckets
   SET public = false
 WHERE id IN ('chat-docs', 'chat-media', 'voice-messages');

-- ---------------------------------------------------------------
-- 2. Remover policies abertas ao papel PUBLIC
--    Acesso passa a ser exclusivamente por rota server-side
--    autorizada (service role), conforme SPEC-054 §7.3.5: nao criar
--    policy baseada em auth.uid() porque a identidade do produto
--    (users_v2 + iron-session) NAO esta mapeada ao Supabase Auth.
-- ---------------------------------------------------------------
DROP POLICY IF EXISTS "Qualquer um pode ver imagens"        ON storage.objects; -- SELECT chat-media
DROP POLICY IF EXISTS "Permitir upload via chat"            ON storage.objects; -- INSERT chat-media
DROP POLICY IF EXISTS "Admins podem deletar"                ON storage.objects; -- DELETE chat-media
DROP POLICY IF EXISTS "Anyone can read voice messages"      ON storage.objects; -- SELECT voice-messages
DROP POLICY IF EXISTS "Anyone can upload to voice-messages" ON storage.objects; -- INSERT voice-messages

-- ---------------------------------------------------------------
-- 3. avatars: leitura publica preservada, ESCRITA anonima removida
--    (SPEC-054 §7.3.1). Bucket esta vazio hoje - risco zero.
-- ---------------------------------------------------------------
DROP POLICY IF EXISTS "Public Upload Avatars" ON storage.objects;
DROP POLICY IF EXISTS "Public Update Avatars" ON storage.objects;
DROP POLICY IF EXISTS "Public Delete Avatars" ON storage.objects;
-- "Public Read" em avatars e PRESERVADA de proposito.

-- =============================================================
-- VERIFY (executar apos APPLY):
--
-- 1) Buckets:
-- select id, public from storage.buckets order by id;
-- ESPERADO: avatars=true; chat-docs=false; chat-media=false;
--           portal-evidence=false; voice-messages=false
--
-- 2) Policies restantes:
-- select polname from pg_policy where polrelid='storage.objects'::regclass order by 1;
-- ESPERADO: apenas "Public Read"
--
-- 3) Nenhum objeto perdido:
-- select count(*) from storage.objects;  -- ESPERADO: 61
--
-- 4) URL publica antiga deixa de funcionar (fora do banco):
-- curl -I https://<ref>.supabase.co/storage/v1/object/public/chat-media/<path>
-- ESPERADO: 400 ou 404
--
-- 5) Advisor public_bucket_allows_listing: 3 -> 0
-- =============================================================
