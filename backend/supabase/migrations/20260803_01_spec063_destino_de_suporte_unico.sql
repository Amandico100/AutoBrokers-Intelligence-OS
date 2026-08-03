-- SPEC-063 Bloco B — o destino de suporte humano tem UMA casa, e é da corretora.
--
-- O PROBLEMA
-- ----------
-- Existiam duas verdades que não se falavam:
--
--   human_support_destinations      a UI grava aqui (prioridade, horário,
--                                   escalonamento, fallback)
--   companies.acionamento_profile   o backend LIA daqui
--
-- 📊 Medido em 02/08/2026: `human_support_destinations` não aparecia uma única
-- vez em `backend/app/`. A corretora configurava o destino na tela e o dossiê
-- de handoff ia para outro lugar — ou para lugar nenhum.
--
-- E pior: 📊 Resulta e AutoFleet apontavam para o MESMO grupo de WhatsApp
-- (`120363427334937446@g.us`) no perfil legado. O dossiê de handoff carrega
-- nome, telefone e CPF do segurado. Isso é vazamento entre corretoras.
--
-- O QUE ESTA MIGRATION FAZ
-- ------------------------
-- Traz o legado para a tabela canônica, SEM apagar o legado (expand-first), e
-- deixa o conflito VISÍVEL numa view. Ela não resolve o compartilhamento —
-- resolver exige decisão humana sobre qual grupo é de quem. O código já recusa
-- enviar para destino compartilhado (fail-closed); esta migration garante que
-- o conflito apareça em vez de ficar escondido num JSONB.
--
-- Idempotente: rodar duas vezes não duplica linha nem altera o que já existe.
--
-- APPLY   os dois blocos abaixo, na ordem
-- VERIFY  SELECT * FROM vw_destinos_de_suporte_em_conflito;
--         SELECT c.company_name, h.destination_ref, h.metadata->>'origem'
--           FROM human_support_destinations h
--           JOIN companies c ON c.id = h.company_id
--          WHERE h.is_active ORDER BY 1;
-- ROLLBACK
--         DELETE FROM human_support_destinations
--          WHERE metadata->>'origem' = 'backfill_spec063_acionamento_profile';
--         DROP VIEW IF EXISTS vw_destinos_de_suporte_em_conflito;
--         (o `acionamento_profile` nunca foi tocado — o legado continua intacto)

-- ---------------------------------------------------------------------------
-- 1) BACKFILL — o que estava só no JSONB ganha linha na tabela canônica
-- ---------------------------------------------------------------------------
INSERT INTO human_support_destinations (
    company_id, name, destination_type, channel_provider,
    destination_ref, display_ref, is_primary, priority_order,
    fallback_enabled, silence_minutes, metadata, is_active
)
SELECT
    c.id,
    'Suporte humano (importado do perfil de acionamento)',
    CASE WHEN c.acionamento_profile->>'suporte_humano_whatsapp' LIKE '%@g.us'
         THEN 'whatsapp_group' ELSE 'whatsapp_number' END,
    'manual',
    c.acionamento_profile->>'suporte_humano_whatsapp',
    -- display_ref mostra o suficiente para reconhecer, não o suficiente para copiar
    CASE WHEN length(c.acionamento_profile->>'suporte_humano_whatsapp') > 10
         THEN left(c.acionamento_profile->>'suporte_humano_whatsapp', 6) || '****'
              || right(c.acionamento_profile->>'suporte_humano_whatsapp', 8)
         ELSE c.acionamento_profile->>'suporte_humano_whatsapp' END,
    true, 1, true, 15,
    jsonb_build_object(
        'origem', 'backfill_spec063_acionamento_profile',
        'importado_em', now()::text,
        'nota', 'A fonte legada (companies.acionamento_profile) NAO foi apagada.'
    ),
    true
FROM companies c
WHERE COALESCE(c.acionamento_profile->>'suporte_humano_whatsapp', '') <> ''
  AND NOT EXISTS (
      SELECT 1 FROM human_support_destinations h
       WHERE h.company_id = c.id AND h.is_active
  );

-- ---------------------------------------------------------------------------
-- 2) A VIEW QUE NÃO DEIXA O CONFLITO SUMIR
-- ---------------------------------------------------------------------------
-- Não é constraint. Uma constraint UNIQUE rejeitaria a segunda linha e a
-- corretora ficaria SEM destino sem ninguém entender por quê — o defeito
-- trocaria de lugar, não sumiria. A view mostra; o código recusa; a pessoa
-- decide de quem é o grupo.
CREATE OR REPLACE VIEW vw_destinos_de_suporte_em_conflito AS
SELECT
    d.destination_ref,
    count(DISTINCT d.company_id)                       AS corretoras,
    string_agg(DISTINCT c.company_name, ' | ')         AS quais,
    'O dossie de handoff leva CPF do segurado. Enquanto duas corretoras '
    'dividirem este destino, o envio e RECUSADO pelo codigo (fail-closed).'
                                                       AS por_que_importa
FROM human_support_destinations d
JOIN companies c ON c.id = d.company_id
WHERE d.is_active
GROUP BY d.destination_ref
HAVING count(DISTINCT d.company_id) > 1;

COMMENT ON VIEW vw_destinos_de_suporte_em_conflito IS
  'SPEC-063 B — destinos de suporte humano usados por mais de uma corretora. '
  'Linha aqui = handoff recusado por seguranca ate alguem separar os destinos.';
