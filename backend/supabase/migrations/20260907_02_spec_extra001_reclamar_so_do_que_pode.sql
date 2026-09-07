-- =============================================================
-- MIGRATION: spec_extra001_reclamar_so_do_que_pode
-- SPEC:      SPEC-EXTRA-001 — conserto do painel (red team P3 · lente produto+DADO P5)
-- AUTOR:     orquestrador (Fable 5.1)        DATA: 2026-09-07
-- OBJETIVO:  as duas funções do ledger deixam de confiar no chamador: `billing_reclamar_obrigacao`
--            recusa os estados TERMINAIS por construção, e `billing_reservar_obrigacao` devolve
--            id NULL no ramo `colisao_recibo` (o id de OUTRA obrigação não pode viajar como se fosse esta).
--
-- APPLY:     CREATE OR REPLACE das duas funções (mesmas assinaturas; nenhuma coluna, índice ou dado muda).
--            📊 Red team 07/09: `billing_reclamar_obrigacao(id, company, ARRAY['suprimido','incerto'])`
--            reclamaria — a regra "NUNCA" estava no comentário e ausente da função.
--            📊 Lente produto+DADO 07/09: no ramo `colisao_recibo` a função devolvia o id da linha
--            da OUTRA seguradora; o chamador de hoje só retém, mas nada impedia o próximo de marcar
--            estado na linha errada.
-- VERIFY:    (read-only, depois do APPLY)
--   -- V1) as duas funções existem com a assinatura do contrato
--   SELECT p.proname, pg_get_function_identity_arguments(p.oid) FROM pg_proc p
--     JOIN pg_namespace n ON n.oid=p.pronamespace
--    WHERE n.nspname='public' AND p.proname IN ('billing_reservar_obrigacao','billing_reclamar_obrigacao');
--   -- esperado: 2 linhas, assinaturas iguais às da 20260907_01
--   -- V2) o corpo da reclamação carrega a lista de terminais
--   SELECT pg_get_functiondef('public.billing_reclamar_obrigacao(uuid,uuid,text[])'::regprocedure) LIKE '%TERMINAIS%';
--   -- esperado: true
--   -- V3) o corpo da reserva devolve NULL na colisão
--   SELECT pg_get_functiondef('public.billing_reservar_obrigacao(uuid,text,text,text,text,text,text,text,uuid,uuid,uuid,boolean)'::regprocedure) LIKE '%colisao_recibo%NULL::uuid%';
--   -- esperado: true
--   -- V4) 🔴 o comportamento, com canario=true e limpeza por id (mesmo roteiro do V4 da 20260907_01):
--   --     reservar (ganhou=true) → reclamar com ARRAY['reservado','suprimido'] → esperado FALSE
--   --     (reservado não é reclamável e suprimido é terminal); reservar com OUTRO portal e o mesmo
--   --     recibo → esperado ganhou=false, status='colisao_recibo', id NULL.
-- ROLLBACK:  reaplicar as duas funções da 20260907_01 (CREATE OR REPLACE com os corpos anteriores).
--            Nenhum dado é tocado por esta migration.
--
-- EXPAND-FIRST: sim (só corpo de função)
-- DESTRUTIVA:   não
-- =============================================================

CREATE OR REPLACE FUNCTION public.billing_reclamar_obrigacao(
    p_id         uuid,
    p_company_id uuid,
    p_de_status  text[]
) RETURNS boolean
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $function$
DECLARE
    v_ok boolean;
    -- 🔴 TERMINAIS E NÃO-RECLAMÁVEIS, por construção — o chamador não escolhe:
    --   suprimido  → o cliente pediu para não receber (decisão dele)
    --   incerto    → ninguém sabe se aquela saiu (reenviar = cobrar duas vezes)
    --   contestado → "já paguei"/dúvida: para até a equipe conferir (a rota
    --                `liberar` com motivo muda o estado para `liberado` antes)
    --   reservado  → outra execução está com a reserva agora
    --   entregue_equipe / aceito_pelo_canal → a parcela JÁ saiu; só `liberado`
    --                (decisão humana registrada) reabre
    TERMINAIS constant text[] := ARRAY['suprimido','incerto','contestado','reservado',
                                       'entregue_equipe','aceito_pelo_canal'];
BEGIN
    IF p_id IS NULL OR p_company_id IS NULL OR p_de_status IS NULL
       OR array_length(p_de_status, 1) IS NULL THEN
        RETURN false;
    END IF;

    UPDATE public.billing_sent_log b
       SET status      = 'reservado',
           reserved_at = now(),
           attempts    = coalesce(b.attempts, 0) + 1,
           updated_at  = now()
     WHERE b.id         = p_id
       AND b.company_id = p_company_id       -- 🔴 CLAUDE.md §7, também no banco
       AND b.send_mode  = 'real'
       AND b.status     = ANY (p_de_status)
       AND b.status     <> ALL (TERMINAIS)   -- 🔴 a lista do chamador não vence esta
    RETURNING true INTO v_ok;

    RETURN coalesce(v_ok, false);
END;
$function$;

COMMENT ON FUNCTION public.billing_reclamar_obrigacao(uuid, uuid, text[]) IS
  'SPEC-EXTRA-001: reclama para nova tentativa uma obrigação que está em um dos estados passados — e NUNCA em suprimido, incerto, contestado, reservado, entregue_equipe ou aceito_pelo_canal, por construção (20260907_02). UPDATE condicional atômico; devolve false quando o estado já mudou.';

CREATE OR REPLACE FUNCTION public.billing_reservar_obrigacao(
    p_company_id     uuid,
    p_portal_key     text,
    p_recibo         text,
    p_modalidade     text,
    p_to_phone       text,
    p_to_last4       text,
    p_cliente_nome   text,
    p_apolice_susep  text,
    p_routine_id     uuid,
    p_work_run_id    uuid,
    p_integration_id uuid,
    p_canario        boolean
) RETURNS TABLE(id uuid, ganhou boolean, status text)
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $function$
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
            status, reserved_at, attempts, updated_at
        ) VALUES (
            p_company_id, v_portal, v_recibo, 'real', p_modalidade,
            nullif(btrim(coalesce(p_to_phone, '')), ''),
            nullif(btrim(coalesce(p_to_last4, '')), ''),
            p_cliente_nome, p_apolice_susep,
            p_routine_id, p_work_run_id, p_integration_id, coalesce(p_canario, false),
            'reservado', now(), 1, now()
        )
        ON CONFLICT (company_id, portal_key, recibo) WHERE send_mode = 'real'
        DO NOTHING
        RETURNING b.id, b.status INTO v_id, v_status;
    EXCEPTION WHEN unique_violation THEN
        -- A constraint ANTIGA `(company_id, recibo, send_mode)` também vigia.
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
        -- Mesmo recibo, OUTRA seguradora: não é esta obrigação. 🔴 O id da
        -- outra linha NÃO viaja (20260907_02): um chamador que marcasse estado
        -- nele escreveria na parcela errada. O chamador retém com incidente.
        RETURN QUERY SELECT NULL::uuid, false, 'colisao_recibo'::text;
        RETURN;
    END IF;

    RETURN QUERY SELECT v_id, false, v_status;
END;
$function$;

COMMENT ON FUNCTION public.billing_reservar_obrigacao(uuid, text, text, text, text, text, text, text, uuid, uuid, uuid, boolean) IS
  'SPEC-EXTRA-001: reserva ATÔMICA de uma obrigação de cobrança (send_mode=''real''). ganhou=true para um único chamador; false + status da linha existente para os demais; (NULL, false, colisao_recibo) quando o recibo é de OUTRA seguradora (20260907_02). Função porque o ON CONFLICT de índice único PARCIAL exige o predicado, e o PostgREST não o expressa.';
