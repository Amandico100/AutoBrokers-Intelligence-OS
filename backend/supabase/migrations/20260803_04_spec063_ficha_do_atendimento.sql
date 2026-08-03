-- SPEC-063 Bloco S — o atendimento passa a ter MEMÓRIA.
--
-- O PROBLEMA
-- ----------
-- 📊 `grep -niE "\bfase|phase|etapa|stage|slot" backend/app/agents/*.py` → ZERO.
-- O `AgentState` tem mensagens, empresa, usuário, sessão, prompts e métricas —
-- e nenhum campo de fase, de dado já coletado ou de objetivo do atendimento.
--
-- A memória do que já foi perguntado É A JANELA DE CONTEXTO: 60 mensagens.
-- Passou disso, o que foi coletado nas primeiras 20 some, e o único remédio no
-- código é o prompt mandando "RELEIA a conversa".
--
-- O próprio código registra que isso JÁ QUEBROU em produção com janela menor:
-- o agente repediu o CPF do mesmo cliente. Um sinistro de verdade passa de 60
-- mensagens com facilidade.
--
-- E a tool de acionamento obriga o modelo a RE-DECLARAR 15+ campos a cada
-- chamada, reconstruídos do texto. Perdeu a janela, perdeu a coleta.
--
-- POR QUE AQUI E NÃO NUM WORK RUN
-- --------------------------------
-- Work Run (SPEC-055) é para EXECUÇÕES — um acionamento, uma rotina rodando.
-- Tem lease, checkpoint, retomada. O atendimento não é uma execução: é uma
-- CONVERSA que dura dias e não tem começo e fim de processo.
--
-- A ficha é o entendimento acumulado dessa conversa, e mora na entidade que já
-- representa a conversa. Criar tabela de execução para guardar isso seria o
-- mesmo erro do `corridor_runs` — 📊 50 execuções abandonadas, todas `active`,
-- hoje no schema `graveyard`.
--
-- Nenhuma tabela nova. Nenhum motor paralelo. (CLAUDE.md §5 e §6.)
--
-- APPLY    os três ALTER abaixo (idempotentes)
-- VERIFY   SELECT count(*) FILTER (WHERE ficha_atendimento <> '{}'::jsonb) AS com_ficha,
--                 count(*) FILTER (WHERE resolvido_em IS NOT NULL)         AS resolvidas,
--                 count(*)                                                 AS total
--            FROM conversations;
--          \d conversations   -- as três colunas existem
-- ROLLBACK ALTER TABLE conversations DROP COLUMN IF EXISTS ficha_atendimento;
--          ALTER TABLE conversations DROP COLUMN IF EXISTS resolvido_em;
--          ALTER TABLE conversations DROP COLUMN IF EXISTS resolucao_motivo;
--          (nenhum dado pré-existente é tocado — só colunas novas)

-- A ficha: o que o sistema já sabe deste atendimento.
ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS ficha_atendimento jsonb NOT NULL DEFAULT '{}'::jsonb;

-- "Resolvido" deixa de ser um cronômetro.
--
-- Hoje a Fila mostra `concluido` quando `agora - última_mensagem > 48h`. Uma
-- conversa abandonada aparece como resolvida, e uma conversa resolvida em 10
-- minutos continua "aberta" por dois dias. O tempo não sabe o desfecho.
ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS resolvido_em timestamptz;

ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS resolucao_motivo text;

COMMENT ON COLUMN conversations.ficha_atendimento IS
  'SPEC-063 S — o que ja se sabe deste atendimento: fase, ramo, servico, '
  'seguradora, dados confirmados e o que falta. Existe para o agente NAO '
  'reperguntar o que o cliente ja respondeu quando a conversa passa das 60 '
  'mensagens da janela de contexto.';

COMMENT ON COLUMN conversations.resolvido_em IS
  'SPEC-063 S — quando o caso FOI RESOLVIDO, por decisao. Nao confundir com '
  'inatividade: a Fila marcava "concluido" por 48h de silencio, o que fazia '
  'conversa abandonada parecer resolvida.';

COMMENT ON COLUMN conversations.resolucao_motivo IS
  'SPEC-063 S — POR QUE foi resolvido. Sem motivo escrito nao ha como medir '
  'quantos atendimentos o sistema resolve de ponta a ponta.';

-- Achar rápido o que ainda está em pé, por corretora.
CREATE INDEX IF NOT EXISTS idx_conversations_em_aberto
    ON conversations (company_id, last_message_at DESC)
    WHERE resolvido_em IS NULL;
