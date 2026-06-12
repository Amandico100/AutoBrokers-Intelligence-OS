# 42A5 — Auxiliary Blueprint Contract Foundation Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **sem schema/SQL/migration, sem RAG/Qdrant/MinIO, sem alterar executores existentes, sem backend Python**.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. O que foi padronizado
Um **contrato canônico de Auxiliar** (`auxiliary_contract_v1`) que declara: tipo, audiência, objetivo, non_goals, quando usar / quando não usar, inputs/outputs, `requires_knowledge`, `requires_memory`, `requires_tools`, `side_effects`, `risk_level`, `approval_policy`, `billing_policy` e `observability`. Isso permite ao AutoBrokers Core entender, sugerir e coordenar Auxiliares sem prompt solto e sem estrutura paralela.

## 2. Onde o contrato fica (sem schema novo)
- **Template:** `auxiliary_templates.default_config.contract` (jsonb já existente).
- **Instalação por corretora:** `tenant_auxiliaries.config.contract` (jsonb já existente), copiado no install.
- Quando **não há** contrato explícito, ele é **inferido** de campos existentes: `requires_human_approval`, `uses_external_actions`, `execution_mode`/`trigger_type`, `permissions` e `default_config.runtime`.

## 3. Por que não precisou de schema
As colunas jsonb (`default_config`, `config`, `permissions`, `input_schema`, `output_schema`) e os booleans (`requires_human_approval`, `uses_external_actions`) já existem. O contrato vive **dentro** desses jsonb. Nenhuma `CREATE TABLE`/`ALTER TABLE`/migration foi necessária (regra do batch). A rota de install já é resiliente a schema (`getTableColumns`/`pickColumns`).

## 4. Arquivos alterados
- `lib/auxiliaries/types.ts` — tipos do contrato (todos **aditivos/backward-compatible**).
- `lib/auxiliaries/contract.ts` (**novo**) — helpers puros: `normalizeAuxiliaryContract`, `inferAuxiliaryContract`, `getAuxiliaryContract`, `getAuxiliaryRiskLevel`, `getAuxiliarySideEffects`, `requiresHumanApprovalFromContract`, `sanitizeAuxiliaryContract`, `auxiliaryContractBadges`.
- `app/api/admin/auxiliaries/templates/[templateId]/install/route.ts` — grava `config.contract` normalizado (sanitizado) no install (novo e no rebind de agente).
- `app/admin/auxiliares/page.tsx` — bloco "Contrato do Auxiliar" no form (tipo/efeito/risco/quando usar/quando não usar) + preview de badges + badge na tabela; salva em `default_config.contract`.
- `app/dashboard/auxiliares/galeria/page.tsx` e `app/dashboard/auxiliares/meus/page.tsx` — badges/microcopy do contrato nos cards.
- `docs/canon/design/2026-06-claude-design/42A5-auxiliary-blueprint-contract-report.md` (este).

## 5. Como o contrato é inferido
`inferAuxiliaryContract`:
- `side_effects`: `uses_external_actions` + `requires_human_approval` → `approval_required`; só externo → `external_action`; só aprovação → `draft_only`; nada → `none`.
- `risk_level`: `external_action`→high; `approval_required`→medium; demais→low.
- `auxiliary_type`: runtime `workflow`→workflow; `smith_agent_blueprint`/agent_id→agent_based; senão deriva do efeito (read_only/draft_only/approval_required/external_action).
- `requires_tools`: slug com "whatsapp"→`{type:whatsapp, approval_required:true}`; outro efeito externo→`connector`.
- `approval_policy.required`: verdadeiro se aprovação/efeito externo.
- `billing_policy`: `{billable:true, cost_source:'token_usage_logs'}` (os executores já logam lá).
`normalizeAuxiliaryContract` = inferido **+ override explícito sanitizado** (enums validados, arrays normalizados).

## 6. Como o contrato é exibido
- **Admin (`/admin/auxiliares`):** no form de template, selects de **Tipo / Efeito externo / Risco**, textos **Quando usar / Quando NÃO usar**, preview ao vivo de badges, e um badge de tipo na tabela. (Aprovação e ação externa continuam nos checkboxes existentes.)
- **Dashboard tenant (Galeria/Meus):** badges nos cards — ex.: "Somente leitura", "Rascunho", "Requer aprovação", "Ação externa", "Requer conector", "Requer conhecimento", "Risco baixo/médio/alto/crítico".

## 7. Como preserva os executores existentes
**Nada** nos executores foi tocado: `resumo-atendimentos` e `follow-up-whatsapp` (backend Python), `approval_requests`, WhatsApp dry-run, billing e RAG seguem idênticos. O contrato é **metadata** lido na UI/instalação; não altera fluxo de execução. Auxiliares legados sem contrato continuam funcionando via **inferência** (e a UI não bloqueia uso).

## 8. Como o Core poderá usar (readiness)
Com o contrato disponível, o AutoBrokers Core poderá futuramente responder (sem conexão automática agora):
- "Qual auxiliar devo usar?" → casa a intenção com `when_to_use`/`goal`/`auxiliary_type`.
- "Esse auxiliar envia mensagem real?" → `side_effects` / `requires_tools` (whatsapp/connector).
- "Esse auxiliar exige aprovação?" → `approval_policy.required`.
- "O que preciso configurar?" → `requires_knowledge` / `requires_tools` (conector via Vault).
O helper `normalizeAuxiliaryContract` já é a fonte única para isso (servidor ou client).

## 9. Como instalar em tenant
No install, o contrato normalizado/sanitizado é gravado em `tenant_auxiliaries.config.contract` (tanto no insert novo quanto no rebind de agente). **Sem** quebrar dedupe `(company_id, slug)`, **sem** duplicar agente, **sem** alterar runtime Smith. Sem segredos (sanitização profunda remove token/api_key/secret/password/credential/cookie/authorization/etc.).

## 10. Segurança
`sanitizeAuxiliaryContract` remove recursivamente qualquer chave sensível (`FORBIDDEN_CONTRACT_KEYS`) antes de normalizar/gravar. Nenhum segredo é salvo, logado ou renderizado. A normalização só aceita enums/arrays conhecidos (chaves desconhecidas perigosas são descartadas).

## 11. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| backend Python alterado | ✅ nenhum |
| SearchService/Qdrant/MinIO/RAG/upload | ✅ nenhum |
| SQL/migration/schema novo | ✅ nenhum |
| executores existentes alterados | ✅ nenhum |
| segredo/token/api_key em contrato | ✅ sanitizado/nenhum |

## 12. Riscos remanescentes
- Inferência é heurística: para Auxiliares legados sem contrato explícito, o tipo/risco pode não ser perfeito até o Admin definir o contrato no form (override explícito resolve).
- `requires_knowledge/memory` inferidos ficam vazios por padrão (conservador) — devem ser declarados no contrato quando relevantes.
- O Core ainda **não** consome o contrato automaticamente (readiness apenas) — fica para um batch futuro.

## 13. Deploy recomendado
- **Web apenas** (Next/libs/UI). **Sem** backend Python, **sem** SQL/migration, **sem** deploy de API.

## 14. Teste manual
1. Admin → Auxiliares Globais → editar um template → preencher Tipo/Efeito/Risco/Quando usar → salvar; reabrir e conferir que persistiu em `default_config.contract`.
2. Instalar o template numa corretora → conferir `tenant_auxiliaries.config.contract` populado (sem segredos).
3. Dashboard → Galeria e Meus Auxiliares → ver os badges (Somente leitura / Requer aprovação / Ação externa / Risco …).
4. Auxiliares existentes (resumo/follow-up) continuam abrindo e rodando normalmente.

## 15. Próximo batch recomendado
- **42A7 — Core consome contrato** (o AutoBrokers Core passa a ler `normalizeAuxiliaryContract` para sugerir/responder sobre Auxiliares) **ou** **41C.2C — Global Knowledge Collection**. Depois, **42B — Atendimento/Corredores**.
