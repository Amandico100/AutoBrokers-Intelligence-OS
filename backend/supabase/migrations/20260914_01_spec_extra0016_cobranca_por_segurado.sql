-- =============================================================================
-- MIGRATION: spec_extra0016_cobranca_por_segurado
-- SPEC:      SPEC-EXTRA-001.6 — B1 "ninguém é cobrado duas vezes"
-- AUTOR:     Claude Opus 5 (builder B1)            DATA: 2026-09-14
-- OBJETIVO:  o ledger passa a saber DE QUEM é a parcela, para a regra de N dias
--
-- APPLY:     1 coluna aditiva (`segurado_chave`) + 1 índice parcial +
--            1 SOBRECARGA de `billing_reservar_obrigacao` com 13 argumentos.
--            Nenhuma coluna existente é tocada. Nenhuma linha é reescrita.
--            A função de 12 argumentos CONTINUA existindo e intacta.
-- VERIFY:    V0–V6, abaixo. SQL executável, read-only (V4/V5 em transação com
--            `rollback`, para não deixar lixo no ledger).
-- ROLLBACK:  bloco ROLLBACK ao final — e a condição em que ele é seguro.
--
-- EXPAND-FIRST: sim   ·   DESTRUTIVA: não   ·   IDEMPOTENTE: sim
--
-- 📊 MEDIDO EM 13/09/2026, antes de uma linha de SQL (relatório da SPEC §1):
--      select count(*) from public.billing_sent_log;                        -> 0
--      select count(*) from public.billing_sent_log where send_mode='real'; -> 0
--      select count(*) from public.billing_sent_log where send_mode='test'; -> 0
--    A tabela está VAZIA: não há backfill, e a coluna nova nasce nula sem
--    mentir sobre nenhuma cobrança passada.
--
-- 🔴 POR QUE A FUNÇÃO GANHA UMA VERSÃO DE 13 ARGUMENTOS EM VEZ DE UM DEFAULT:
--    `CREATE OR REPLACE` com um parâmetro a mais NÃO substitui a função — cria
--    uma SOBRECARGA. Se o novo parâmetro tivesse DEFAULT, uma chamada com 12
--    argumentos passaria a casar com as DUAS e o Postgres devolveria 42725
--    (ambiguous function call) — em produção, na hora de reservar, com o boleto
--    na mão. Sem default, a chamada de 12 resolve só na antiga e a de 13 só na
--    nova: expand-first de verdade. A antiga é derrubada por uma migration
--    POSTERIOR, depois que o código novo estiver no ar
--    (P-E0016-RESERVA-12-ARGS). ⛔ Não é esta migration que a derruba.
--
-- 🔴 O CORPO DA FUNÇÃO NÃO FOI COPIADO À MÃO. Ele é o `pg_get_functiondef` do
--    objeto VIVO em 13/09/2026, com DUAS diferenças e nenhuma a mais:
--        + o parâmetro `p_segurado_chave text` na assinatura
--        + a coluna `segurado_chave` (e o valor) no INSERT
--    Conferir no V0: `EXCEPTION WHEN unique_violation` e o ramo
--    `colisao_recibo` continuam lá — é assim que a retenção de recibo repetido
--    (que é PRODUTO) desaparece sem ninguém ver.
--
-- ⚠️ ORDEM DE IMPLANTAÇÃO (proposta §15.1): esta migration entra ANTES da
--    imagem que chama a função de 13 argumentos. Invertido, a reserva levanta e
--    NENHUMA parcela sai — falha fechada, mas falha.
-- =============================================================================

-- ----------------------------------------------------------------- APPLY -----
begin;

alter table public.billing_sent_log
  add column if not exists segurado_chave text;

comment on column public.billing_sent_log.segurado_chave is
  'QUEM e o segurado, para a regra "1 cobranca por segurado a cada N dias" (D-PILOTO-18). Formato: "doc:<digitos>" quando a seguradora devolveu CPF/CNPJ, "nome:<normalizado>" quando nao devolveu, "recibo:<n>" quando nao ha nem nome. NAO se chama cpf_cnpj porque nem sempre E um documento — nome que mente reinfecta todo leitor seguinte (CLAUDE.md 12.1). Dado da PROPRIA CORRETORA: nunca vai para log, relatorio de execucao, artifact, prompt ou RAG (CLAUDE.md 7).';

-- A janela por segurado. 🔴 SEM o portal na chave: a pergunta é "já falei com
-- esta pessoa esta semana?", e ela vale ENTRE seguradoras. Com o `company_id` na
-- frente, nenhuma leitura atravessa tenant (CLAUDE.md §7). Índice PARCIAL
-- (`WHERE send_mode='real'`) pelo mesmo motivo do índice único da 20260907_01:
-- o modo teste não é obrigação, e não deve ocupar o índice da obrigação.
create index if not exists billing_sent_log_segurado_idx
    on public.billing_sent_log (company_id, segurado_chave, sent_at desc)
 where send_mode = 'real';

create or replace function public.billing_reservar_obrigacao(
    p_company_id uuid, p_portal_key text, p_recibo text, p_modalidade text,
    p_to_phone text, p_to_last4 text, p_cliente_nome text, p_apolice_susep text,
    p_routine_id uuid, p_work_run_id uuid, p_integration_id uuid, p_canario boolean,
    p_segurado_chave text                   -- 🔴 13º: SEM DEFAULT, de propósito
)
 returns table(id uuid, ganhou boolean, status text)
 language plpgsql
 set search_path to 'public', 'pg_temp'
as $function$
DECLARE
    v_portal text := btrim(coalesce(p_portal_key, ''));
    v_recibo text := btrim(coalesce(p_recibo, ''));
    v_id     uuid;
    v_status text;
BEGIN
    IF p_company_id IS NULL OR v_portal = '' OR v_recibo = '' THEN
        RAISE EXCEPTION 'billing_reservar_obrigacao: company_id, portal_key e recibo sao obrigatorios'
            USING ERRCODE = '22023';
    END IF;

    BEGIN
        INSERT INTO public.billing_sent_log AS b (
            company_id, portal_key, recibo, send_mode, modalidade,
            to_phone, to_last4, cliente_nome, apolice_susep,
            routine_id, work_run_id, integration_id, canario,
            segurado_chave,
            status, reserved_at, attempts, updated_at
        ) VALUES (
            p_company_id, v_portal, v_recibo, 'real', p_modalidade,
            nullif(btrim(coalesce(p_to_phone, '')), ''),
            nullif(btrim(coalesce(p_to_last4, '')), ''),
            p_cliente_nome, p_apolice_susep,
            p_routine_id, p_work_run_id, p_integration_id, coalesce(p_canario, false),
            nullif(btrim(coalesce(p_segurado_chave, '')), ''),
            'reservado', now(), 1, now()
        )
        ON CONFLICT (company_id, portal_key, recibo) WHERE send_mode = 'real'
        DO NOTHING
        RETURNING b.id, b.status INTO v_id, v_status;
    EXCEPTION WHEN unique_violation THEN
        v_id := NULL;
    END;

    IF v_id IS NOT NULL THEN
        RETURN QUERY SELECT v_id, true, v_status;
        RETURN;
    END IF;

    SELECT b.id, b.status INTO v_id, v_status
      FROM public.billing_sent_log b
     WHERE b.company_id = p_company_id
       AND b.send_mode  = 'real'
       AND b.portal_key = v_portal
       AND b.recibo     = v_recibo
     LIMIT 1;

    IF v_id IS NULL THEN
        RETURN QUERY SELECT NULL::uuid, false, 'colisao_recibo'::text;
        RETURN;
    END IF;

    RETURN QUERY SELECT v_id, false, v_status;
END;
$function$;

commit;

-- ---------------------------------------------------------------- VERIFY -----
-- V0) 🔴 o corpo novo é o antigo + o campo — e nada a menos.
--   select pg_get_functiondef(p.oid)
--     from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--    where n.nspname = 'public' and p.proname = 'billing_reservar_obrigacao'
--      and p.pronargs = 13;
--   esperado: contém 'EXCEPTION WHEN unique_violation', 'colisao_recibo',
--             'ON CONFLICT (company_id, portal_key, recibo) WHERE send_mode'
--             e 'segurado_chave'. Um diff contra a versão de 12 argumentos tem
--             de mostrar SÓ o parâmetro e a coluna/valor do INSERT.
--
-- V1) a coluna existe e é nula.
--   select column_name, data_type, is_nullable
--     from information_schema.columns
--    where table_schema='public' and table_name='billing_sent_log'
--      and column_name='segurado_chave';
--   esperado: 1 linha, text, is_nullable='YES'
--
-- V2) o índice existe com o predicado certo.
--   select indexdef from pg_indexes where indexname='billing_sent_log_segurado_idx';
--   esperado: contém "WHERE (send_mode = 'real'::text)" e "(company_id, segurado_chave, sent_at DESC)"
--
-- V3) as DUAS assinaturas convivem, sem ambiguidade.
--   select p.pronargs, pg_get_function_identity_arguments(p.oid)
--     from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--    where n.nspname='public' and p.proname='billing_reservar_obrigacao'
--    order by 1;
--   esperado: 2 linhas — uma com 12 tipos, outra com 13
--
-- V4) 🔴 a reserva continua reservando, e agora grava o segurado.
--   begin;
--     select * from public.billing_reservar_obrigacao(
--       (select id from public.companies order by created_at limit 1),
--       'verify_portal','VERIFY-0016','equipe',null,null,'VERIFY',null,null,null,null,true,'doc:00000000000');
--       -- esperado: ganhou=true, status='reservado'
--     select segurado_chave from public.billing_sent_log where recibo='VERIFY-0016';
--       -- esperado: 'doc:00000000000'
--     select * from public.billing_reservar_obrigacao(
--       (select id from public.companies order by created_at limit 1),
--       'verify_portal','VERIFY-0016','cliente',null,null,'VERIFY',null,null,null,null,true,'doc:00000000000');
--       -- esperado: ganhou=FALSE, MESMO id (a segunda não cria linha nova)
--   rollback;   -- 🔴 o VERIFY não deixa lixo
--
-- V5) CONTROLE — a chamada de 12 argumentos ainda resolve, sem 42725.
--   begin;
--     select * from public.billing_reservar_obrigacao(
--       (select id from public.companies order by created_at limit 1),
--       'verify_portal','VERIFY-0016-B','equipe',null,null,'VERIFY',null,null,null,null,true);
--       -- esperado: executa (não levanta "function is not unique")
--     select segurado_chave from public.billing_sent_log where recibo='VERIFY-0016-B';
--       -- esperado: NULL (a versão antiga não conhece a coluna, e isso é o certo)
--   rollback;
--
-- V6) CONTROLE — nada do modo test mudou.
--   select count(*) from public.billing_sent_log where send_mode='test';  -- esperado: 0
--
-- -------------------------------------------------------------- ROLLBACK -----
-- ⚠️ SÓ é seguro enquanto não houver linha `send_mode='real'` (📊 0 em 13/09).
--    Havendo, derrubar a coluna apaga DE QUEM era a cobrança já enviada — e as
--    mensagens não se desfazem. Nesse caso o rollback correto é pôr a rotina em
--    'none' na tela e deixar a coluna onde está (ela é aditiva e inerte para
--    quem não a lê).
-- ⚠️ E a ORDEM importa: derrubar a função de 13 argumentos com a imagem nova no
--    ar faz TODA reserva levantar. Rollback do código primeiro, do schema depois.
--
-- drop function if exists public.billing_reservar_obrigacao(uuid,text,text,text,text,text,text,text,uuid,uuid,uuid,boolean,text);
-- drop index if exists public.billing_sent_log_segurado_idx;
-- alter table public.billing_sent_log drop column if exists segurado_chave;
-- =============================================================================
