-- ============================================================
-- 38A5.0 — FINOPS / CREDITS DIAGNOSTICS  (SOMENTE LEITURA / SELECT)
-- AutoBrokers Intelligence OS · billing/créditos/uso + Auxiliares
-- Seguro para colar no Supabase SQL Editor. NÃO altera dados.
-- Sem UPDATE/INSERT/DELETE/ALTER/CREATE/DROP. Sem company_id fixo.
-- Objetivo: confirmar o modelo real de cobrança e se os Auxiliares já são cobrados.
-- ============================================================

-- ------------------------------------------------------------
-- 1) Quais tabelas de finops/auxiliares existem?
-- ------------------------------------------------------------
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'company_credits', 'credit_transactions', 'token_usage_logs',
    'subscriptions', 'plans', 'payment_history', 'llm_pricing',
    'auxiliary_templates', 'tenant_auxiliaries', 'auxiliary_runs'
  )
ORDER BY table_name;

-- ------------------------------------------------------------
-- 2) Colunas das tabelas-chave (confirmar nomes reais antes de qualquer código)
-- ------------------------------------------------------------
SELECT table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN (
    'company_credits', 'credit_transactions', 'token_usage_logs',
    'subscriptions', 'plans', 'auxiliary_runs'
  )
ORDER BY table_name, ordinal_position;

-- ------------------------------------------------------------
-- 3) Constraints (CHECK / PK / FK) das tabelas de finops
-- ------------------------------------------------------------
SELECT tc.table_name, tc.constraint_type, tc.constraint_name
FROM information_schema.table_constraints tc
WHERE tc.table_schema = 'public'
  AND tc.table_name IN (
    'company_credits', 'credit_transactions', 'token_usage_logs',
    'subscriptions', 'plans', 'auxiliary_runs'
  )
ORDER BY tc.table_name, tc.constraint_type;

-- ------------------------------------------------------------
-- 4) Policies RLS dessas tabelas
-- ------------------------------------------------------------
SELECT schemaname, tablename, policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN (
    'company_credits', 'credit_transactions', 'token_usage_logs',
    'subscriptions', 'auxiliary_runs'
  )
ORDER BY tablename, policyname;

-- ------------------------------------------------------------
-- 5) RPC de débito atômico (usada por debit_credits): existe?
-- ------------------------------------------------------------
SELECT routine_name, routine_type, data_type AS return_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name ILIKE '%debit_company_balance%'
ORDER BY routine_name;

-- ------------------------------------------------------------
-- 6) Saldos atuais por empresa (sem PII; só id + saldo)
-- ------------------------------------------------------------
SELECT cc.company_id, c.company_name, cc.balance_brl, cc.updated_at
FROM public.company_credits cc
LEFT JOIN public.companies c ON c.id = cc.company_id
ORDER BY cc.updated_at DESC NULLS LAST
LIMIT 50;

-- ------------------------------------------------------------
-- 7) token_usage_logs por service_type + billed  (mostra se 'auxiliary_run' já entra na cobrança)
-- ------------------------------------------------------------
SELECT service_type,
       billed,
       count(*)                AS rows,
       coalesce(sum(total_cost_usd), 0) AS total_cost_usd,
       coalesce(sum(input_tokens), 0)   AS input_tokens,
       coalesce(sum(output_tokens), 0)  AS output_tokens
FROM public.token_usage_logs
GROUP BY service_type, billed
ORDER BY service_type, billed;

-- ------------------------------------------------------------
-- 8) credit_transactions por tipo (consumption = débito de uso)
-- ------------------------------------------------------------
SELECT type, count(*) AS rows, coalesce(sum(amount_brl), 0) AS sum_amount_brl
FROM public.credit_transactions
GROUP BY type
ORDER BY type;

-- ------------------------------------------------------------
-- 9) Execuções recentes de Auxiliares (status + custo gravado)
-- ------------------------------------------------------------
SELECT id, company_id, template_id, status,
       cost_usd, token_usage, created_at, finished_at
FROM public.auxiliary_runs
ORDER BY created_at DESC
LIMIT 25;

-- ------------------------------------------------------------
-- 10) RELAÇÃO Auxiliar ↔ cobrança:
--     token_usage_logs do service 'auxiliary_run' + run_id (details) vinculável a auxiliary_runs.
--     Confirma que cada execução virou um log de uso (que o worker cobra).
-- ------------------------------------------------------------
SELECT t.id              AS usage_log_id,
       t.company_id,
       t.model_name,
       t.input_tokens,
       t.output_tokens,
       t.total_cost_usd,
       t.billed,
       t.billed_at,
       (t.details ->> 'run_id') AS run_id,
       r.id              AS auxiliary_run_id,
       r.status          AS run_status,
       t.created_at
FROM public.token_usage_logs t
LEFT JOIN public.auxiliary_runs r
       ON r.id::text = (t.details ->> 'run_id')
WHERE t.service_type = 'auxiliary_run'
ORDER BY t.created_at DESC
LIMIT 50;

-- ------------------------------------------------------------
-- 11) Planos disponíveis (preço + créditos visuais) — referência de billing
-- ------------------------------------------------------------
SELECT id, name, slug, price_brl, monthly_price, display_credits, is_active
FROM public.plans
ORDER BY coalesce(display_order, sort_order, 0);

-- ------------------------------------------------------------
-- 12) Subscriptions por status (visão geral)
-- ------------------------------------------------------------
SELECT status, count(*) AS rows
FROM public.subscriptions
GROUP BY status
ORDER BY status;
