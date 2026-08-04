-- =============================================================
-- MIGRATION: spec065_o_pedido_nao_abre_duas_vezes
-- SPEC:      SPEC-065 — portal de vidros ponta a ponta (bloco 7.2)
-- AUTOR:     executor senior          DATA: 2026-08-04
-- OBJETIVO:  impedir que o MESMO pedido de vidros vire DOIS atendimentos na
--            seguradora, e dar ao job um caminho de volta para a conversa.
--
-- APPLY:     1) portal_jobs.idempotency_key text  — impressao digital do PEDIDO
--            2) portal_jobs.session_id      text  — de onde veio (caminho de volta)
--            3) portal_jobs.agent_id        uuid  — qual agente acionou
--            4) idx_portal_jobs_pedido_vivo — UNIQUE PARCIAL (company_id,
--               idempotency_key) enquanto o pedido esta vivo
--            5) COMMENT em cada coluna e no indice
--
-- VERIFY:    -- 1. as tres colunas existem e sao nulaveis
--            SELECT column_name, data_type, is_nullable
--              FROM information_schema.columns
--             WHERE table_schema='public' AND table_name='portal_jobs'
--               AND column_name IN ('idempotency_key','session_id','agent_id')
--             ORDER BY column_name;
--            -- esperado: 3 linhas, todas is_nullable='YES'
--
--            -- 2. o indice existe, e UNICO e tem o predicado certo
--            SELECT indexdef FROM pg_indexes
--             WHERE schemaname='public' AND tablename='portal_jobs'
--               AND indexname='idx_portal_jobs_pedido_vivo';
--            -- esperado: CREATE UNIQUE INDEX ... (company_id, idempotency_key)
--            --           WHERE ((idempotency_key IS NOT NULL) AND (status <> 'failed'))
--
--            -- 3. os 91 jobs historicos continuam intactos e sem chave
--            SELECT count(*) AS total,
--                   count(*) FILTER (WHERE idempotency_key IS NULL) AS sem_chave
--              FROM public.portal_jobs;
--            -- esperado: total = sem_chave  (nada foi backfillado de proposito)
--
--            -- 4. o guarda CONSEGUE falhar: dois pedidos vivos com a mesma
--            --    chave tem de estourar 23505. Rodar em transacao e desfazer.
--            BEGIN;
--              INSERT INTO public.portal_jobs
--                (company_id, portal_key, journey, params, status, idempotency_key)
--              SELECT company_id, 'vidros_lanternas', 'verify_23505', '{}'::jsonb,
--                     'queued', 'verify:23505'
--                FROM public.portal_jobs LIMIT 1;
--              INSERT INTO public.portal_jobs
--                (company_id, portal_key, journey, params, status, idempotency_key)
--              SELECT company_id, 'vidros_lanternas', 'verify_23505', '{}'::jsonb,
--                     'queued', 'verify:23505'
--                FROM public.portal_jobs LIMIT 1;
--              -- esperado: ERROR 23505 duplicate key ... idx_portal_jobs_pedido_vivo
--            ROLLBACK;
--
-- ROLLBACK:  DROP INDEX IF EXISTS public.idx_portal_jobs_pedido_vivo;
--            ALTER TABLE public.portal_jobs DROP COLUMN IF EXISTS idempotency_key;
--            ALTER TABLE public.portal_jobs DROP COLUMN IF EXISTS session_id;
--            ALTER TABLE public.portal_jobs DROP COLUMN IF EXISTS agent_id;
--            -- Nenhuma linha pre-existente e lida, atualizada ou apagada por
--            -- esta migration. O rollback devolve a tabela ao estado exato de
--            -- 04/08/2026 (14 colunas, 91 linhas).
--
-- EXPAND-FIRST: sim — so adiciona. Nenhuma coluna removida ou renomeada,
--               nenhum default alterado, nenhum UPDATE.
-- DESTRUTIVA:   nao
-- =============================================================
--
-- O PROBLEMA — medido, nao deduzido
-- ----------------------------------
-- 📊 04/08/2026, Supabase dcajcvlzcjbmyapmklil:
--
--     SELECT count(*), count(DISTINCT company||placa||data_dano||peca)
--       FROM portal_jobs WHERE journey='abrir_atendimento';
--     -->  39 jobs   para   5 pedidos distintos
--
-- Trinta e quatro jobs a mais do que pedidos. Um unico pedido — company
-- 04b5cdbc, placa QJQ0A91, dano em 05/07/2026, "vidro de porta" — tem 30
-- jobs, entre eles um `done`.
--
-- Ate hoje isso nao machucou ninguem, e por um motivo que nao vai durar:
-- 📊 `PORTAL_REAL_ENABLED` esta desligado e os 39 acionamentos morreram antes
-- do passo 7 (33 `needs_human`, 5 `failed`, 1 `done` sem protocolo). O portal
-- nunca chegou a abrir pedido de verdade.
--
-- POR QUE ISSO VIRA DANO NO DIA EM QUE LIGAR
-- -------------------------------------------
-- 📊 `docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md` §7, captura do Founder:
-- o `Nº do atendimento` aparece no passo 7, NO TOPO DA TELA, antes da escolha
-- da loja. **O pedido ja existe na seguradora antes de o fluxo terminar.**
--
--     "repetir o fluxo cria um segundo atendimento, nao corrige o primeiro"
--
-- E nada impedia a repeticao: `portal_jobs` nao tinha coluna de idempotencia,
-- `portal_tool.py::_arun` fazia `insert` direto, e quem chama e um LLM — o
-- segurado pergunta "e ai, abriu?" e o modelo pode chamar `portal_action` de
-- novo. 📊 O poll do `_arun` desiste em 150s (`POLL_TIMEOUT_S`) e responde
-- "ainda nao processou", com o job ainda vivo: a chamada seguinte duplicava.
--
-- O SEGUNDO BURACO, DO MESMO TAMANHO
-- -----------------------------------
-- `portal_jobs` nao tinha `session_id`. Quando o job termina depois dos 150s,
-- ou quando para em `needs_human`, nao existia caminho de volta ao segurado —
-- ele ficava esperando para sempre. A coluna nasce aqui para o Vigia poder
-- fechar esse ciclo.
--
-- POR QUE NENHUMA TABELA NOVA
-- ----------------------------
-- CLAUDE.md §5. A fila de portais e `portal_jobs` e continua sendo. Uma tabela
-- de "pedidos" ao lado da fila seria um segundo registro do mesmo fato, com as
-- duas metades divergindo na primeira falha de escrita.

-- -------------------------------------------------------------------------
-- 1. As tres colunas. Nulaveis de proposito.
-- -------------------------------------------------------------------------
-- `text` nulavel e ADD COLUMN sem default: no PG11+ nao reescreve a tabela e
-- nao invalida nada que ja le `select *` (o portal_worker le assim).

ALTER TABLE public.portal_jobs
    ADD COLUMN IF NOT EXISTS idempotency_key text;

ALTER TABLE public.portal_jobs
    ADD COLUMN IF NOT EXISTS session_id text;

ALTER TABLE public.portal_jobs
    ADD COLUMN IF NOT EXISTS agent_id uuid;

-- -------------------------------------------------------------------------
-- 2. O indice UNICO PARCIAL — e a defesa do predicado escolhido
-- -------------------------------------------------------------------------
--
-- PREDICADO:  idempotency_key IS NOT NULL AND status <> 'failed'
--
-- (a) `idempotency_key IS NOT NULL` — chave nula nao bloqueia NADA.
--     📊 Os 91 jobs historicos sao todos nulos (nenhum backfill: a chave e
--     calculada a partir dos `params`, e reconstrui-la para tras seria inventar
--     historia). E o Cobrador (`billing_collection.py::_enqueue_job`, journey
--     `cobranca_sweep`, 📊 52 dos 91 jobs) continua inserindo sem chave: ele
--     varre a carteira inteira e repetir a varredura e o comportamento certo.
--     Sem esta metade do predicado, o indice quebraria o Cobrador no primeiro
--     segundo sweep.
--
-- (b) `status <> 'failed'` — `failed` e a valvula de escape, e a UNICA.
--     Um acionamento que falhou por CPF errado, InfoCap fora do ar ou apolice
--     nao localizada TEM de poder ser refeito depois de corrigido: o pedido nao
--     existe na seguradora, nao ha nada a duplicar.
--     A valvula e alcancavel sem humano: 📊 `portal_worker/worker.py::
--     recover_stale_jobs` varre os `running` a cada tick e, depois de 2
--     tentativas, escreve `failed` no job orfao. Worker que morreu no meio nao
--     tranca o pedido para sempre.
--
-- (c) Por que a forma NEGATIVA (`<> 'failed'`) e nao a lista positiva
--     (`IN ('queued','running','needs_human','done')`):
--     as duas descrevem exatamente o mesmo conjunto HOJE — 📊 sao os cinco
--     unicos status que a tabela conhece (DDL da SPEC-020 e os 91 jobs reais).
--     Elas so divergem no dia em que alguem inventar um sexto status.
--         lista positiva  ->  o status novo escapa do guarda, em silencio
--         forma negativa  ->  o status novo entra protegido, por padrao
--     A escolha e pelo erro mais barato. Falso MERGE (dois pedidos legitimos
--     recebendo a mesma chave) devolve "ja existe um atendimento aberto" ao
--     agente — chato, visivel, e um humano desfaz. Falso SPLIT (o mesmo pedido
--     virando dois) cria um segundo atendimento na seguradora, e o mapa §7 e
--     explicito: "desistir depois daqui nao desfaz nada". Irreversivel ganha
--     de chato. Por isso o guarda erra para o lado de bloquear.
--
-- (d) Por que `done` tambem bloqueia, e para sempre:
--     `done` significa pedido aberto na seguradora. Reabrir o mesmo (placa,
--     peca, data) e exatamente o que o mapa proibe em §8.5. Pedido de verdade
--     diferente — o outro vidro, outro dia — tem peca ou data diferente, logo
--     chave diferente, logo passa.
--
-- (e) Por que a chave e COMPOSTA com `company_id`:
--     a funcao `chave_de_idempotencia` ja embute a corretora na string, mas
--     isso e uma promessa de codigo. CLAUDE.md §7 pede a fronteira tambem em
--     constraint. Com `(company_id, idempotency_key)` o isolamento entre
--     corretoras passa a ser estrutural: mesmo que a receita da chave mude,
--     duas corretoras nunca disputam a mesma linha.
--
-- LOCK: `CREATE UNIQUE INDEX` sem CONCURRENTLY pega ACCESS EXCLUSIVE. Aqui e
-- aceitavel e proposital: 📊 a tabela tem 91 linhas, e CONCURRENTLY proibiria
-- aplicar este arquivo dentro de uma transacao — o que tornaria os tres ALTER
-- e o indice passiveis de aplicacao pela metade. Uma trava de milissegundos
-- numa fila de 91 linhas vale menos que um APPLY atomico.

CREATE UNIQUE INDEX IF NOT EXISTS idx_portal_jobs_pedido_vivo
    ON public.portal_jobs (company_id, idempotency_key)
 WHERE idempotency_key IS NOT NULL
   AND status <> 'failed';

-- -------------------------------------------------------------------------
-- 3. O que cada coluna guarda — escrito na coluna, nao so no relatorio
-- -------------------------------------------------------------------------

COMMENT ON COLUMN public.portal_jobs.idempotency_key IS
  'SPEC-065 7.2 - impressao digital do PEDIDO, nao do job: corretora + placa + '
  'peca normalizada + data do dano (app/agents/tools/portal_params.py::'
  'chave_de_idempotencia). A descricao livre NAO entra: o segurado reconta a '
  'mesma historia com outras palavras e isso criaria pedidos "diferentes" que '
  'sao o mesmo. NULL = job sem guarda de duplicidade (91 jobs historicos e '
  'todo sweep do Cobrador).';

COMMENT ON COLUMN public.portal_jobs.session_id IS
  'SPEC-065 7.2 - de onde o acionamento veio (ex.: whatsapp:5548...:<agent>), '
  'para o job saber VOLTAR a conversa. Sem isto, um job que termina depois dos '
  '150s do poll da tool, ou que para em needs_human, nao tinha caminho de volta '
  'ao segurado: ele esperava para sempre.';

COMMENT ON COLUMN public.portal_jobs.agent_id IS
  'SPEC-065 7.2 - agente ATENDENTE da corretora que acionou (agents.id, mesmo '
  'agente usado no lookup da integracao de WhatsApp). Guardado no enfileiramento '
  'porque quem responde ao segurado depois precisa da MESMA integracao, '
  'redescobrir isso mais tarde e onde o heads-up sumia.';

COMMENT ON INDEX public.idx_portal_jobs_pedido_vivo IS
  'SPEC-065 7.2 - a chave vale ENQUANTO o pedido esta vivo. Bloqueia queued, '
  'running, needs_human e done, libera failed, que e a valvula de escape do '
  'acionamento que precisa ser refeito depois de corrigido. Existe porque o '
  'protocolo da seguradora nasce no passo 7 ANTES do fim do fluxo: reexecutar '
  'nao corrige, cria um SEGUNDO atendimento.';
