# 42C0 — Auxiliares Cleanup MVP + Contract Backfill Plan

> **Status:** plano preparado · **SQL NÃO executado** · READ-ONLY no código (nenhum runtime/RAG/Smith/executor/schema alterado) · **nada deletado** (apenas arquivamento reversível + backfill de contrato).
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main
> **Aguardando:** revisão do Architect/founder antes de rodar o SQL.

## 1. Objetivo
Preparar uma limpeza **segura e reversível** dos Auxiliares para o MVP da RAFAEL SEGUROS, conforme o 43M0 e o checklist CORE-REGRESSION-001 (teste CORE-007 deve listar **apenas** os reais após o cleanup). Dois entregáveis: este relatório + um SQL revisável (`docs/sql/42C0-auxiliares-cleanup-mvp.sql`). **O SQL não foi executado.**

## 2. Entregáveis
- `docs/canon/design/2026-06-claude-design/42C0-auxiliares-cleanup-mvp-report.md` (este).
- `docs/sql/42C0-auxiliares-cleanup-mvp.sql` (SELECT de pré-checagem + UPDATEs transacionais reversíveis + verificações + rollback comentado).

## 3. Empresa e auxiliares alvo
- **Empresa (RAFAEL):** `company_id = 3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe` (não é segredo).
- **Reais (MVP, manter ativos + backfill de contrato):** `resumo-atendimentos`, `follow-up-whatsapp`.
- **Teste (arquivar/ocultar, sem deletar):** `teste-runtime-smith-agent`, `teste-exclusivo-rafael`, `teste-publicado-global`.

## 4. O que o SQL faz (passo a passo)
1. **Seção 0 — pré-checagem (somente leitura):** mostra as 5 instalações da RAFAEL (reais + teste), se já têm `config.contract`, e os 3 templates de teste no catálogo.
2. **Seção 1 — transacional (`BEGIN … COMMIT`):**
   - **1.1** `tenant_auxiliaries.status = 'archived'` para os 3 slugs de teste **só** na RAFAEL (idempotente; não deleta).
   - **1.2** `auxiliary_templates.status='archived', is_active=false` para os 3 slugs de teste (catálogo global; não deleta).
   - **1.3 / 1.4** Backfill de `config.contract` dos 2 reais via `jsonb_set(config, '{contract}', …)` — **preserva** o resto de `config` (ex.: `runtime`).
   - **1.5** Verificações finais (ativos da RAFAEL; arquivados; contrato preenchido; templates de teste).
   - `COMMIT` (com nota: trocar por `ROLLBACK` para preview sem persistir).
3. **Seção 2 — rollback comentado** (não executar por padrão).

## 5. Contratos que serão preenchidos
**resumo-atendimentos** → `auxiliary_type=read_only`, `audience=operator_internal`, `side_effects=none`, `risk_level=low`, `approval_policy.required=false`, `requires_tools=[]`, `requires_memory=[{session,false}]`, billing `token_usage_logs`, `observability.log_approval=false`. Goal/non_goals/when_to_use/when_not_to_use conforme o prompt.

**follow-up-whatsapp** → `auxiliary_type=approval_required`, `audience=operator_internal`, `side_effects=approval_required`, `risk_level=medium`, `approval_policy.required=true` (reason: "Envio externo por WhatsApp exige revisão/aprovação humana."), `requires_tools=[{whatsapp, required:true, approval_required:true}]`, `requires_memory=[{session,false}]`, billing `token_usage_logs`, `observability.log_approval=true`. Goal/non_goals/when_to_use/when_not_to_use conforme o prompt.

> Os dois contratos seguem **exatamente** o shape de `AuxiliaryContract` que o runtime lê em `normalizeAuxiliaryContract` (`lib/auxiliaries/contract.ts`) — incluindo `inputs`/`outputs` com defaults `{required:[],optional:[]}` / `{format:"structured",fields:[]}`. Assim o bloco `[AVAILABLE AUXILIARIES]` (42A7) passa a usar valores **explícitos** (não inferidos).

## 6. Verificações que o SQL traz
- Auxiliares **ativos** da RAFAEL após cleanup (esperado: sobram os reais; teste some).
- Auxiliares **arquivados** da RAFAEL (os 3 de teste, se existiam).
- `config.contract` dos 2 reais (type/risk/approval).
- Templates de teste **arquivados/inativos**.

## 7. Segurança e reversibilidade
- **Nada é deletado** — apenas `status`/`is_active` e a chave `config.contract`.
- **Idempotente:** re-rodar não causa efeito duplicado (guards `<> 'archived'`; `jsonb_set` sobrescreve com o mesmo valor).
- **Transacional:** tudo num `BEGIN…COMMIT`; preview com `ROLLBACK`.
- **Rollback** pronto (Seção 2): reativa teste (tenant+template) e remove o `contract` backfillado (volta a inferir em runtime).
- Sem segredo/PII; sem mexer em runtime/RAG/Qdrant/MinIO/upload/prompt/agentes/executores/WhatsApp/schema; sem migration.

## 8. Observações para a revisão
- Se a coluna **`status` não existir** em `auxiliary_templates`, remover `status='archived'` da linha 1.2 e manter apenas `is_active=false` (comentário no SQL).
- Se os slugs de teste **não estiverem instalados** na RAFAEL, os UPDATEs são **no-op** (seguro). A pré-checagem (Seção 0) confirma o que existe.
- O `company_id` da RAFAEL veio do contexto operacional dos batches anteriores; confirmar na pré-checagem antes do COMMIT.

## 9. Próximo passo
1. **Founder/Architect revisa** este relatório + o SQL.
2. Roda a **Seção 0** (pré-checagem) e confere o estado real.
3. Roda a **Seção 1** (com `ROLLBACK` para preview, depois `COMMIT`).
4. Re-roda o checklist **CORE-007** (deve listar apenas os reais) e **CORE-008/009** (contratos corretos).
5. Seguir para **42B0 — Atendimento/Corredores Recon (READ-ONLY)**.
