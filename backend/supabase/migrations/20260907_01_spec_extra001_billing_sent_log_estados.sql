-- =============================================================================
-- SPEC-EXTRA-001 · U1 — O LEDGER DA COBRANÇA GANHA ESTADO, DONO E RESERVA
--
-- 🔴 EXPAND-FIRST e ADITIVA. Nenhuma coluna existente é renomeada, movida,
--    apagada ou reescrita; nenhuma constraint antiga cai. `billing_sent_log`
--    continua exatamente como está para o modo `test` de 17/08/2026 — que é o
--    CONTROLE desta SPEC (`backend/tests/test_a_cobranca_esta_como_estava.py`,
--    34/34). O que entra aqui só é lido e escrito pelos modos REAIS
--    (`send_mode='real'`, modalidade `equipe` | `cliente`).
--
-- 📊 MEDIDO EM 07/09/2026 no banco de produção (`dcajcvlzcjbmyapmklil`), antes
--    de escrever uma linha de SQL:
--
--      SELECT count(*) FROM public.billing_sent_log;                    ->  0
--      SELECT count(*) FROM public.billing_sent_log WHERE send_mode<>'test'; -> 0
--      constraints:  billing_sent_log_pkey        PRIMARY KEY (id)
--                    billing_sent_log_uniq        UNIQUE (company_id, recibo, send_mode)
--                    fk_billing_sent_log_company  FK -> companies(id) ON DELETE RESTRICT
--      índices:      billing_sent_log_pkey · billing_sent_log_uniq
--                    billing_sent_log_company_idx · idx_billing_sent_log_company
--
--    A tabela está VAZIA. Não há backfill a fazer, e o `DEFAULT 'entregue'` de
--    `status` é conservador de propósito: se um dia aparecer linha antiga, ela
--    afirma o que a tabela afirmava antes ("o texto foi aceito"), e não um
--    estado novo que ninguém mediu.
--
-- 🔴 POR QUE A RESERVA É UMA FUNÇÃO NO BANCO, e não um `upsert` do PostgREST
--    (SPEC §0.5, emenda 2): a identidade da obrigação é um ÍNDICE ÚNICO
--    PARCIAL (`WHERE send_mode='real'`), e o `ON CONFLICT` de um índice parcial
--    exige repetir o predicado. O PostgREST não expressa isso — o
--    `ignore_duplicates=True` manda `ON CONFLICT (cols) DO NOTHING` sem o
--    `WHERE`, e o Postgres responde **42P10** ("no unique or exclusion
--    constraint matching the ON CONFLICT specification"). Reservar por RPC é o
--    que faz a reserva ser ATÔMICA de verdade em vez de um SELECT seguido de
--    INSERT com janela de corrida no meio.
--
-- ⚠️ E a constraint ANTIGA continua valendo: `billing_sent_log_uniq
--    (company_id, recibo, send_mode)` é MAIS estrita que a nova para
--    `send_mode='real'` (ignora `portal_key`). Duas seguradoras que emitissem o
--    MESMO número de recibo para a mesma corretora colidiriam nela — e o
--    `ON CONFLICT` do índice parcial não a cobre. Por isso a função tem um
--    `EXCEPTION WHEN unique_violation`: o segundo pedido nunca estoura, ele
--    volta como `ganhou=false`, que é a resposta certa nos dois casos.
--
-- ⛔ `to_phone` é dado da PRÓPRIA CORRETORA (a tabela já guarda `cliente_nome`
--    desde 2026-07) e existe para a resposta do cliente achar o caso dele. Ele
--    NUNCA vai para log, relatório de execução, artifact ou prompt — só
--    `to_last4` circula (CLAUDE.md §7).
--
-- ⛔ NÃO APLICADA PELO BUILDER (trava do pacote U1). Quem aplica é o
--    orquestrador. APPLY / VERIFY / ROLLBACK estão escritos ABAIXO, antes de
--    qualquer execução (CLAUDE.md §8).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- APPLY
-- -----------------------------------------------------------------------------
-- 🔴 IDEMPOTENTE: todo `ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`
--    e `CREATE OR REPLACE FUNCTION`. Rodar duas vezes dá o mesmo estado.

ALTER TABLE public.billing_sent_log
  ADD COLUMN IF NOT EXISTS status                    text NOT NULL DEFAULT 'entregue',
  ADD COLUMN IF NOT EXISTS modalidade                text,
  ADD COLUMN IF NOT EXISTS text_ok                   boolean,
  ADD COLUMN IF NOT EXISTS doc_ok                    boolean,
  ADD COLUMN IF NOT EXISTS to_phone                  text,
  ADD COLUMN IF NOT EXISTS to_last4                  text,
  ADD COLUMN IF NOT EXISTS integration_id            uuid,
  ADD COLUMN IF NOT EXISTS work_run_id               uuid,
  ADD COLUMN IF NOT EXISTS routine_id                uuid,
  ADD COLUMN IF NOT EXISTS reserved_at               timestamptz,
  ADD COLUMN IF NOT EXISTS sent_at                   timestamptz,
  ADD COLUMN IF NOT EXISTS updated_at                timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN IF NOT EXISTS attempts                  int NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_error                text,
  ADD COLUMN IF NOT EXISTS motivo                    text,
  ADD COLUMN IF NOT EXISTS encaminhado_ao_cliente_em timestamptz,
  ADD COLUMN IF NOT EXISTS encaminhado_por           uuid,
  ADD COLUMN IF NOT EXISTS retorno_do_cliente        text,
  ADD COLUMN IF NOT EXISTS retorno_em                timestamptz,
  ADD COLUMN IF NOT EXISTS canario                   boolean NOT NULL DEFAULT false;

-- De quem é cada coluna, escrito na coluna. Quem abrir a tabela daqui a um ano
-- não vai ter esta SPEC aberta ao lado.
COMMENT ON COLUMN public.billing_sent_log.status IS
  'Estado da obrigação: reservado | aceito_pelo_canal | entregue_equipe | parcial | incerto | falhou | adiado | liberado | suprimido | contestado | entregue (legado, o default). Escrito pelo motor da cobrança (billing_collection) e pela porta de saída (platform_outbound._entregar_agora).';
COMMENT ON COLUMN public.billing_sent_log.modalidade IS
  'equipe | cliente | test — QUEM recebeu. Nos modos reais anda junto com send_mode=''real''.';
COMMENT ON COLUMN public.billing_sent_log.text_ok IS
  'O TEXTO foi aceito pelo canal? (componente 1 do envio). NULL = ainda não houve tentativa.';
COMMENT ON COLUMN public.billing_sent_log.doc_ok IS
  'O PDF foi aceito pelo canal? (componente 2). NULL = não havia documento previsto. `doc_sent` (legado) continua espelhando isto no modo test.';
COMMENT ON COLUMN public.billing_sent_log.to_phone IS
  'Destino efetivo, só dígitos. Dado da PRÓPRIA CORRETORA, existe para a resposta do cliente achar o caso dele. ⛔ NUNCA vai para log, relatório, artifact ou prompt — fora daqui circula só to_last4 (CLAUDE.md §7).';
COMMENT ON COLUMN public.billing_sent_log.to_last4 IS
  'Últimos 4 dígitos do destino — a forma que PODE ser impressa e conferida por gente.';
COMMENT ON COLUMN public.billing_sent_log.integration_id IS
  'A conexão de WhatsApp FIXADA no início da execução. É relida por id e revalidada no instante do efeito; divergiu, não envia (reason=conexao_trocada).';
COMMENT ON COLUMN public.billing_sent_log.work_run_id IS
  'O Work Run que executou a rotina, quando ela roda pela ponte (WORK_RUNS_ROUTINE_BRIDGE). Sem FK de propósito: o ledger sobrevive ao expurgo de runs. P-098-RUN-NOS-JOBS.';
COMMENT ON COLUMN public.billing_sent_log.routine_id IS
  'A rotina de cobrança que produziu esta obrigação.';
COMMENT ON COLUMN public.billing_sent_log.reserved_at IS
  'Quando a obrigação foi RESERVADA — antes do efeito, nunca depois (padrão outbox: a intenção é gravada antes do envio).';
COMMENT ON COLUMN public.billing_sent_log.sent_at IS
  'Quando o canal ACEITOU o texto. ⚠️ Aceito pelo provedor é o teto de evidência: o Evolution Go não devolve id de mensagem, então isto nunca significa "o cliente leu".';
COMMENT ON COLUMN public.billing_sent_log.updated_at IS
  'Última escrita nesta linha. É por ela que a lista de Pendências ordena.';
COMMENT ON COLUMN public.billing_sent_log.attempts IS
  'Quantas vezes esta obrigação foi reservada/reclamada. Não é contador de mensagens.';
COMMENT ON COLUMN public.billing_sent_log.last_error IS
  'O último motivo técnico, sem PII e cortado. Para quem investiga, não para quem lê a tela.';
COMMENT ON COLUMN public.billing_sent_log.motivo IS
  'O motivo HUMANO do estado atual (ex.: o que a pessoa escreveu ao liberar o reenvio).';
COMMENT ON COLUMN public.billing_sent_log.encaminhado_ao_cliente_em IS
  'Quando alguém da corretora marcou, no painel, que encaminhou o pacote ao cliente. Só o humano escreve aqui — o sistema não presume encaminhamento.';
COMMENT ON COLUMN public.billing_sent_log.encaminhado_por IS
  'users_v2.id de quem marcou o encaminhamento.';
COMMENT ON COLUMN public.billing_sent_log.retorno_do_cliente IS
  'ja_paguei | nao_sou | nao_quero | segunda_via | duvida | outro — o que o cliente respondeu, classificado (U2).';
COMMENT ON COLUMN public.billing_sent_log.retorno_em IS
  'Quando o retorno do cliente chegou.';
COMMENT ON COLUMN public.billing_sent_log.canario IS
  'Linha produzida pelo canário autorizado (item sintético). Existe para a limpeza do canário apagar por id sem tocar em dado de corretora.';

-- A IDENTIDADE DA OBRIGAÇÃO, nos modos reais: (corretora, seguradora, recibo).
-- 🔴 Não inclui `send_mode`, `modalidade`, dia nem run — porque a parcela em
--    atraso é a MESMA obrigação amanhã, no outro modo e no outro run. Foi essa
--    ausência que permitia "cobrar de novo trocando o modo".
-- ⚠️ Parcial `WHERE send_mode='real'` para não tocar no modo `test`, onde
--    repetir é justamente o que se quer (nota 88 de 17/08/2026).
-- ⚠️ `portal_key` é nullable na tabela, e NULL não é igual a NULL num UNIQUE:
--    por isso o motor RETÉM o item sem seguradora identificada em vez de
--    gravá-lo com `portal_key` vazio ou nulo.
CREATE UNIQUE INDEX IF NOT EXISTS billing_sent_log_obrigacao_uniq
    ON public.billing_sent_log (company_id, portal_key, recibo)
 WHERE send_mode = 'real';

-- Por onde a resposta do cliente encontra o caso dele (U2), sempre com o
-- `company_id` na frente: nenhuma leitura atravessa tenant (CLAUDE.md §7).
CREATE INDEX IF NOT EXISTS billing_sent_log_to_phone_idx
    ON public.billing_sent_log (company_id, to_phone)
 WHERE send_mode = 'real';

-- -----------------------------------------------------------------------------
-- A RESERVA — atômica, e o único jeito de duas execuções não cobrarem duas vezes
-- -----------------------------------------------------------------------------
-- Devolve `ganhou=true` para UM chamador só. Quem recebe `false` NÃO envia:
-- lê o `status` que voltou e decide se reclama (`billing_reclamar_obrigacao`).
--
-- ⚠️ SECURITY INVOKER (o padrão) — o backend fala com service role, que já
--    ignora RLS; um SECURITY DEFINER aqui só ampliaria superfície sem ganho.
--    `search_path` fixo porque função com search_path mutável é achado de
--    advisor e vetor de sequestro de nome.
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
    -- Sem corretora, sem seguradora ou sem recibo não existe obrigação para
    -- reservar. Levantar aqui é melhor que gravar uma linha que nunca vai
    -- casar com nada (22023 = invalid_parameter_value).
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
        -- A constraint ANTIGA `billing_sent_log_uniq (company_id, recibo,
        -- send_mode)` também vigia esta tabela e é mais estrita que a nova.
        -- Bater nela é "já existe obrigação", não é erro para o chamador.
        v_id := NULL;
    END;

    IF v_id IS NOT NULL THEN
        RETURN QUERY SELECT v_id, true, v_status;
        RETURN;
    END IF;

    -- Não ganhou: devolve a linha que já existe, com o estado dela.
    SELECT b.id, b.status INTO v_id, v_status
      FROM public.billing_sent_log b
     WHERE b.company_id = p_company_id
       AND b.send_mode  = 'real'
       AND b.portal_key = v_portal
       AND b.recibo     = v_recibo
     LIMIT 1;

    IF v_id IS NULL THEN
        -- Caiu na constraint antiga (mesmo recibo, OUTRA seguradora). A linha
        -- existe, mas NÃO é esta obrigação. 🔴 Devolver o status dela seria
        -- dizer "já cobrado" sobre um cliente que nunca foi cobrado (aquecimento
        -- EXTRA-001, achado 8a). O chamador recebe um estado próprio e RETÉM o
        -- item com incidente — a equipe cobra; o robô não cala.
        SELECT b.id INTO v_id
          FROM public.billing_sent_log b
         WHERE b.company_id = p_company_id
           AND b.send_mode  = 'real'
           AND b.recibo     = v_recibo
         LIMIT 1;
        v_status := 'colisao_recibo';
    END IF;

    RETURN QUERY SELECT v_id, false, v_status;
END;
$function$;

COMMENT ON FUNCTION public.billing_reservar_obrigacao(uuid, text, text, text, text, text, text, text, uuid, uuid, uuid, boolean) IS
  'SPEC-EXTRA-001 U1: reserva ATÔMICA de uma obrigação de cobrança em billing_sent_log (send_mode=''real''). Devolve ganhou=true para um único chamador; os demais recebem false + o status da linha existente. Existe como função porque o ON CONFLICT de um índice único PARCIAL exige repetir o predicado, e o PostgREST não o expressa.';

-- -----------------------------------------------------------------------------
-- A RECLAMAÇÃO — só de estados que admitem nova tentativa
-- -----------------------------------------------------------------------------
-- Quem decide QUAIS estados é o chamador, e a lista é curta de propósito:
-- `falhou`, `adiado`, `liberado`, `parcial`. ⛔ `incerto`, `entregue_equipe`,
-- `aceito_pelo_canal`, `suprimido` e `contestado` NUNCA entram — um efeito
-- possível não é um efeito ausente, e a preferência do cliente não se
-- desfaz por retomada automática.
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
    RETURNING true INTO v_ok;

    RETURN coalesce(v_ok, false);
END;
$function$;

COMMENT ON FUNCTION public.billing_reclamar_obrigacao(uuid, uuid, text[]) IS
  'SPEC-EXTRA-001 U1: reclama para nova tentativa uma obrigação que está em um dos estados passados (falhou|adiado|liberado|parcial). UPDATE condicional atômico; devolve false quando o estado já mudou.';

-- -----------------------------------------------------------------------------
-- VERIFY  — rodar DEPOIS do APPLY; as cinco perguntas têm resposta esperada
-- -----------------------------------------------------------------------------
-- V1) as 20 colunas novas existem
-- SELECT count(*) AS colunas_novas
--   FROM information_schema.columns
--  WHERE table_schema='public' AND table_name='billing_sent_log'
--    AND column_name IN ('status','modalidade','text_ok','doc_ok','to_phone','to_last4',
--                        'integration_id','work_run_id','routine_id','reserved_at','sent_at',
--                        'updated_at','attempts','last_error','motivo','encaminhado_ao_cliente_em',
--                        'encaminhado_por','retorno_do_cliente','retorno_em','canario');
--   esperado: 20
--
-- V2) os dois índices parciais existem, com o predicado certo
-- SELECT indexname, indexdef FROM pg_indexes
--  WHERE schemaname='public' AND tablename='billing_sent_log'
--    AND indexname IN ('billing_sent_log_obrigacao_uniq','billing_sent_log_to_phone_idx');
--   esperado: 2 linhas, ambas com "WHERE (send_mode = 'real'::text)"
--
-- V3) as duas funções existem com a assinatura do contrato
-- SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args
--   FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
--  WHERE n.nspname='public' AND p.proname IN ('billing_reservar_obrigacao','billing_reclamar_obrigacao');
--   esperado: 2 linhas
--
-- V4) 🔴 A RESERVA RESERVA MESMO — duas chamadas, um vencedor (G25)
-- BEGIN;
--   SELECT * FROM public.billing_reservar_obrigacao(
--     (SELECT id FROM public.companies ORDER BY created_at LIMIT 1),
--     'verify_portal','VERIFY-EXTRA-001','equipe',NULL,NULL,'VERIFY',NULL,NULL,NULL,NULL,true);
--     -- esperado: ganhou = true,  status = 'reservado'
--   SELECT * FROM public.billing_reservar_obrigacao(
--     (SELECT id FROM public.companies ORDER BY created_at LIMIT 1),
--     'verify_portal','VERIFY-EXTRA-001','cliente',NULL,NULL,'VERIFY',NULL,NULL,NULL,NULL,true);
--     -- esperado: ganhou = FALSE, mesmo id, status = 'reservado'
--   -- e a reclamação recusa um estado que não está na lista:
--   SELECT public.billing_reclamar_obrigacao(
--     (SELECT id FROM public.billing_sent_log WHERE recibo='VERIFY-EXTRA-001'),
--     (SELECT id FROM public.companies ORDER BY created_at LIMIT 1),
--     ARRAY['falhou','adiado','liberado','parcial']);
--     -- esperado: false  (a linha está em 'reservado')
-- ROLLBACK;   -- 🔴 o VERIFY não deixa lixo: a transação inteira volta atrás
--
-- V5) o CONTROLE — nada do modo `test` mudou
-- SELECT count(*) FROM public.billing_sent_log WHERE send_mode='test';
--   esperado: o mesmo número de antes do APPLY (📊 0 em 07/09/2026)
--
-- -----------------------------------------------------------------------------
-- ROLLBACK  — nenhum leitor antigo depende de nada disto
-- -----------------------------------------------------------------------------
-- ⚠️ Só é seguro enquanto nenhuma linha `send_mode='real'` existir. Havendo
--    linhas reais, apagar as colunas apaga o estado de cobranças já enviadas —
--    as mensagens não se desfazem, e o ledger é a única prova de que saíram.
--    Nesse caso, o rollback correto é DESLIGAR os modos reais na tela e deixar
--    as colunas onde estão.
--
-- DROP FUNCTION IF EXISTS public.billing_reclamar_obrigacao(uuid, uuid, text[]);
-- DROP FUNCTION IF EXISTS public.billing_reservar_obrigacao(uuid, text, text, text, text, text, text, text, uuid, uuid, uuid, boolean);
-- DROP INDEX IF EXISTS public.billing_sent_log_to_phone_idx;
-- DROP INDEX IF EXISTS public.billing_sent_log_obrigacao_uniq;
-- ALTER TABLE public.billing_sent_log
--   DROP COLUMN IF EXISTS canario,
--   DROP COLUMN IF EXISTS retorno_em,
--   DROP COLUMN IF EXISTS retorno_do_cliente,
--   DROP COLUMN IF EXISTS encaminhado_por,
--   DROP COLUMN IF EXISTS encaminhado_ao_cliente_em,
--   DROP COLUMN IF EXISTS motivo,
--   DROP COLUMN IF EXISTS last_error,
--   DROP COLUMN IF EXISTS attempts,
--   DROP COLUMN IF EXISTS updated_at,
--   DROP COLUMN IF EXISTS sent_at,
--   DROP COLUMN IF EXISTS reserved_at,
--   DROP COLUMN IF EXISTS routine_id,
--   DROP COLUMN IF EXISTS work_run_id,
--   DROP COLUMN IF EXISTS integration_id,
--   DROP COLUMN IF EXISTS to_last4,
--   DROP COLUMN IF EXISTS to_phone,
--   DROP COLUMN IF EXISTS doc_ok,
--   DROP COLUMN IF EXISTS text_ok,
--   DROP COLUMN IF EXISTS modalidade,
--   DROP COLUMN IF EXISTS status;
-- =============================================================================
