-- 42C0 — Cleanup de Auxiliares de teste + backfill de contrato (RAFAEL SEGUROS)
-- ============================================================================
-- SEGURO · IDEMPOTENTE · TRANSACIONAL · REVERSÍVEL · NÃO DELETA NADA.
-- NÃO executar automaticamente — revisar antes (Architect/founder).
-- Não contém segredo/PII. Apenas status/arquivamento + config.contract.
--
-- Empresa alvo (RAFAEL SEGUROS):
--   company_id = 3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe
-- Auxiliares REAIS (MVP): resumo-atendimentos, follow-up-whatsapp
-- Auxiliares de TESTE (arquivar): teste-runtime-smith-agent,
--                                 teste-exclusivo-rafael, teste-publicado-global
--
-- Como usar:
--   1) Rodar a SEÇÃO 0 (pré-checagem, somente leitura) e conferir o estado.
--   2) Rodar a SEÇÃO 1 (BEGIN…COMMIT). Para PREVIEW sem persistir,
--      troque o COMMIT final por ROLLBACK.
--   3) (Opcional) usar a SEÇÃO 2 (rollback) se precisar reverter.
-- ============================================================================


-- ============================================================================
-- SEÇÃO 0 — PRÉ-CHECAGEM (SOMENTE LEITURA, não altera nada)
-- ============================================================================

-- 0.1 Instalações da RAFAEL (reais + teste) e se já têm contrato:
SELECT
    id,
    company_id,
    slug,
    status,
    (config -> 'contract') IS NOT NULL AS has_contract,
    config -> 'contract' ->> 'auxiliary_type' AS contract_type
FROM public.tenant_auxiliaries
WHERE company_id::text = '3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe'
  AND slug IN (
      'resumo-atendimentos',
      'follow-up-whatsapp',
      'teste-runtime-smith-agent',
      'teste-exclusivo-rafael',
      'teste-publicado-global'
  )
ORDER BY slug;

-- 0.2 Templates de teste (se existirem no catálogo global):
SELECT id, slug, name, status, is_active
FROM public.auxiliary_templates
WHERE slug IN (
    'teste-runtime-smith-agent',
    'teste-exclusivo-rafael',
    'teste-publicado-global'
)
ORDER BY slug;


-- ============================================================================
-- SEÇÃO 1 — CLEANUP + BACKFILL (TRANSACIONAL, REVERSÍVEL)
-- Para preview sem persistir: trocar o COMMIT final por ROLLBACK.
-- ============================================================================
BEGIN;

-- 1.1 Arquivar instalações de TESTE da RAFAEL (não deleta; idempotente).
UPDATE public.tenant_auxiliaries
SET status = 'archived'
WHERE company_id::text = '3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe'
  AND slug IN (
      'teste-runtime-smith-agent',
      'teste-exclusivo-rafael',
      'teste-publicado-global'
  )
  AND COALESCE(status, '') <> 'archived';

-- 1.2 Arquivar/ocultar TEMPLATES de teste no catálogo global (não deleta).
--     OBS: se a coluna "status" não existir em auxiliary_templates, remova-a
--     desta linha e mantenha apenas is_active = false.
UPDATE public.auxiliary_templates
SET status = 'archived',
    is_active = false
WHERE slug IN (
    'teste-runtime-smith-agent',
    'teste-exclusivo-rafael',
    'teste-publicado-global'
);

-- 1.3 Backfill do contrato — RESUMO DE ATENDIMENTOS (read-only / low).
--     Preserva o restante de config (ex.: runtime) via jsonb_set na chave contract.
UPDATE public.tenant_auxiliaries
SET config = jsonb_set(
    COALESCE(config, '{}'::jsonb),
    '{contract}',
    '{
        "kind": "auxiliary_contract_v1",
        "auxiliary_type": "read_only",
        "audience": "operator_internal",
        "goal": "Resume conversas de atendimento e destaca decisões, pendências e próximos passos.",
        "non_goals": ["não executar ação externa", "não enviar mensagens", "não decidir cobertura"],
        "when_to_use": ["resumir atendimentos", "organizar decisões e pendências", "preparar próximos passos para equipe"],
        "when_not_to_use": ["enviar comunicação externa", "acionar seguradora", "confirmar cobertura"],
        "inputs": {"required": [], "optional": []},
        "outputs": {"format": "structured", "fields": []},
        "requires_knowledge": [],
        "requires_memory": [{"type": "session", "required": false}],
        "requires_tools": [],
        "side_effects": "none",
        "risk_level": "low",
        "approval_policy": {"required": false, "reason": "Sem efeito externo; execução com log."},
        "billing_policy": {"billable": true, "cost_source": "token_usage_logs"},
        "observability": {"log_run": true, "log_cost": true, "log_approval": false}
    }'::jsonb,
    true
)
WHERE company_id::text = '3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe'
  AND slug = 'resumo-atendimentos';

-- 1.4 Backfill do contrato — FOLLOW-UP WHATSAPP (approval_required / medium / whatsapp).
UPDATE public.tenant_auxiliaries
SET config = jsonb_set(
    COALESCE(config, '{}'::jsonb),
    '{contract}',
    '{
        "kind": "auxiliary_contract_v1",
        "auxiliary_type": "approval_required",
        "audience": "operator_internal",
        "goal": "Gera rascunhos humanos de follow-up para WhatsApp com aprovação humana.",
        "non_goals": ["não enviar mensagem real sem aprovação", "não executar disparo automático", "não contatar cliente sem revisão humana"],
        "when_to_use": ["preparar follow-up de clientes pendentes", "criar rascunho de WhatsApp", "organizar comunicação com aprovação humana"],
        "when_not_to_use": ["envio automático em massa", "cobrança sensível sem revisão", "comunicação externa sem aprovação"],
        "inputs": {"required": [], "optional": []},
        "outputs": {"format": "structured", "fields": []},
        "requires_knowledge": [],
        "requires_memory": [{"type": "session", "required": false}],
        "requires_tools": [{"type": "whatsapp", "required": true, "approval_required": true}],
        "side_effects": "approval_required",
        "risk_level": "medium",
        "approval_policy": {"required": true, "reason": "Envio externo por WhatsApp exige revisão/aprovação humana."},
        "billing_policy": {"billable": true, "cost_source": "token_usage_logs"},
        "observability": {"log_run": true, "log_cost": true, "log_approval": true}
    }'::jsonb,
    true
)
WHERE company_id::text = '3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe'
  AND slug = 'follow-up-whatsapp';

-- 1.5 VERIFICAÇÕES FINAIS (dentro da transação) ---------------------------

-- 1.5.a Auxiliares ATIVOS da RAFAEL após cleanup (devem sobrar os reais):
SELECT slug, status
FROM public.tenant_auxiliaries
WHERE company_id::text = '3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe'
  AND COALESCE(status, 'active') <> 'archived'
ORDER BY slug;

-- 1.5.b Auxiliares ARQUIVADOS da RAFAEL:
SELECT slug, status
FROM public.tenant_auxiliaries
WHERE company_id::text = '3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe'
  AND status = 'archived'
ORDER BY slug;

-- 1.5.c Contrato preenchido nos dois reais:
SELECT
    slug,
    config -> 'contract' ->> 'auxiliary_type' AS contract_type,
    config -> 'contract' ->> 'risk_level' AS risk_level,
    config -> 'contract' -> 'approval_policy' ->> 'required' AS approval_required
FROM public.tenant_auxiliaries
WHERE company_id::text = '3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe'
  AND slug IN ('resumo-atendimentos', 'follow-up-whatsapp')
ORDER BY slug;

-- 1.5.d Templates de teste arquivados/inativos:
SELECT slug, status, is_active
FROM public.auxiliary_templates
WHERE slug IN (
    'teste-runtime-smith-agent',
    'teste-exclusivo-rafael',
    'teste-publicado-global'
)
ORDER BY slug;

-- >>> Persistir as mudanças. Para PREVIEW sem persistir, troque por: ROLLBACK;
COMMIT;


-- ============================================================================
-- SEÇÃO 2 — ROLLBACK (NÃO EXECUTAR POR PADRÃO)
-- Reverte tudo o que a SEÇÃO 1 fez. Rodar manualmente só se necessário.
-- ============================================================================
-- BEGIN;
--
-- -- 2.1 Reativar instalações de teste da RAFAEL:
-- UPDATE public.tenant_auxiliaries
-- SET status = 'active'
-- WHERE company_id::text = '3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe'
--   AND slug IN ('teste-runtime-smith-agent', 'teste-exclusivo-rafael', 'teste-publicado-global');
--
-- -- 2.2 Reativar templates de teste:
-- UPDATE public.auxiliary_templates
-- SET status = 'active', is_active = true
-- WHERE slug IN ('teste-runtime-smith-agent', 'teste-exclusivo-rafael', 'teste-publicado-global');
--
-- -- 2.3 Remover o contrato backfillado dos dois reais (volta a inferir em runtime):
-- UPDATE public.tenant_auxiliaries
-- SET config = config - 'contract'
-- WHERE company_id::text = '3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe'
--   AND slug IN ('resumo-atendimentos', 'follow-up-whatsapp');
--
-- COMMIT;
-- ============================================================================
