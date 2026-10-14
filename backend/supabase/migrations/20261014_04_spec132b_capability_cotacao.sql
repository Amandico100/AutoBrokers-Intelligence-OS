-- =============================================================
-- MIGRATION: 20261014_04_spec132b_capability_cotacao
-- SPEC:      SPEC-132-B — B4 · a costura (a ferramenta de cotação no agente CORE)
-- AUTOR:     builder B4 (Opus 5.5)            DATA: 2026-10-14
-- OBJETIVO:  o PODER governável que solta as três ferramentas da Cotação Rápida (`cotacao_preparar`,
--            `cotacao_disparar`, `cotacao_ajustar`) no chat do corretor — o `graph.py` só as anexa com a capability
--            `tenant.multicalculo.cotacao` ATIVA no Registry (`agents/capability_resolver.py`).
--
-- POR QUE VALE PARA QUALQUER CORRETORA (CLAUDE.md §13.9): o resolver lê `capability_bindings` POR PAPEL
--   (`.eq("agent_role", role)`, sem company_id) + `capabilities.is_active` + o entitlement da corretora só quando ele
--   DESLIGA (`tenant_capability_entitlements.enabled = false`). Sem `requires_connection` (o Agger é decidido na hora
--   pelo `qual_agger`: a conta da pessoa → a da corretora; sem nenhuma, a porta recusa com frase). Logo: UM binding
--   do papel `core` liga para toda corretora com agente core; uma corretora que não quiser desliga pelo entitlement.
--   🔴 `risk='high'` exige `scope` não vazio (SPEC-054 C, o resolver nega HIGH sem escopo) — o scope vai preenchido.
--
-- APPLY (pelo GERENTE — o builder NÃO aplica; idempotente, expand-only, global, nenhum dado de corretora):
--   A. `capabilities`: 1 linha nova (on conflict pela chave: rodar de novo não muda nada).
--   B. `capability_bindings`: 1 linha nova (core, enabled, scope) — `where not exists` (a tabela não tem DDL no
--      repositório — versão órfã, MIGRATIONS-AUTHORITY §4 —, então a idempotência não depende de qual é a chave única).
--   ⛔ Nenhuma coluna, nenhuma trava, nenhum GRANT, nenhum binding para `attendance`/`auxiliary` (o atendente do
--      segurado nunca cota; o graph.py também confere o papel).
--
-- VERIFY (read-only · esperado: 1 · 1 · 1 · 0 · 0):
--   select (select count(*) from public.capabilities where capability_key = 'tenant.multicalculo.cotacao'
--             and is_active and owner = 'tenant' and risk = 'high' and requires_connection = false) capability,
--          (select count(*) from public.capability_bindings where capability_key = 'tenant.multicalculo.cotacao'
--             and agent_role = 'core' and enabled) binding_core,
--          (select count(*) from public.capability_bindings where capability_key = 'tenant.multicalculo.cotacao'
--             and agent_role = 'core' and scope->'ferramentas' ? 'cotacao_disparar') scope_com_ferramentas,
--          (select count(*) from public.capability_bindings where capability_key = 'tenant.multicalculo.cotacao'
--             and agent_role <> 'core') binding_fora_do_core,
--          (select count(*) from public.tenant_capability_entitlements
--             where capability_key = 'tenant.multicalculo.cotacao' and enabled = false) corretoras_que_desligaram;
--
-- ROLLBACK (escrito ANTES; remove só o que esta migration criou):
--   delete from public.capability_bindings where capability_key = 'tenant.multicalculo.cotacao';
--   delete from public.tenant_capability_entitlements where capability_key = 'tenant.multicalculo.cotacao';
--   delete from public.capabilities where capability_key = 'tenant.multicalculo.cotacao';
--
-- EXPAND-FIRST: sim — só insere.
-- DESTRUTIVA:   não
-- =============================================================

insert into public.capabilities
  (capability_key, name, category, owner, risk, requires_connection, requires_approval, provider, is_active)
values
  ('tenant.multicalculo.cotacao', 'Cotação Rápida pelo chat (multicálculo)', 'insurance_ops', 'tenant', 'high',
   false, false, null, true)
on conflict (capability_key) do nothing;

-- 🔴 `requires_approval` no scope fica FALSE de propósito: a aprovação desta ação é o `confirmacao_id` de uso único
--    (D-132B-03) — o corretor confirma o resumo na própria conversa; um Approval do Work OS seria um segundo "sim".
insert into public.capability_bindings (agent_role, capability_key, enabled, scope)
select 'core', 'tenant.multicalculo.cotacao', true,
       '{"servicos": ["cotacao"],
         "ferramentas": ["cotacao_preparar", "cotacao_disparar", "cotacao_ajustar"],
         "read": true, "write": true, "tenant_scoped": true,
         "audience": ["internal"], "data_classes": ["pii_cliente_cifrado", "operational"],
         "side_effect": true, "requires_approval": false, "max_calls_per_run": 6}'::jsonb
where not exists (select 1 from public.capability_bindings
                   where agent_role = 'core' and capability_key = 'tenant.multicalculo.cotacao');
