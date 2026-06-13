# 42B4C — Attendance Cases Index UI MVP Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem LangGraph/RAG/prompts/agentes/WhatsApp/envio externo) · sem deploy automático.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados/alterados
- `app/dashboard/atendimentos/casos/page.tsx` (**alterado**) — substituiu o `ModulePlaceholder` por um wrapper fino que renderiza o client (mantém `metadata`).
- `app/dashboard/atendimentos/casos/CasesIndexClient.tsx` (**novo**) — lista/tabela de casos (busca + filtros + acesso ao detalhe).
- `lib/mock/tenant-modules.ts` (**alterado**) — área `casos` "Em breve" → **"MVP ativo"** (coerente com a `fila`). Nenhum outro módulo alterado.
- `docs/canon/design/2026-06-claude-design/42B4C-attendance-cases-index-ui-mvp-report.md` (este).
- Reuso: `lib/attendance/labels.ts` (42B4B) para rótulos/tons.

## 2. Rota atualizada
`/dashboard/atendimentos/casos` — agora lista real (antes placeholder).

## 3. API consumida (existente 42B5A — não alterada)
- `GET /api/attendance/cases?limit=100` (lista).
- `POST /api/attendance/cases` (botão "Criar caso teste", sandbox).
Client **nunca** chama Supabase direto.

## 4. Decisões de UX
- **Complementar à Fila**, não duplica o Kanban: a Fila é visão **por coluna/status**; Casos é visão **lista/tabela** para busca, auditoria e acesso rápido ao detalhe.
- **Tabela responsiva** (overflow-x-auto, `min-w-[820px]`) com colunas: Segurado (+ summary 1 linha + badges Assistência/subcorredor/risco) · Protocolo · Status (pill) · Prioridade (pill) · Seguradora · Apólice (pill) · Atualizado · Ação ("Abrir" → `/dashboard/atendimentos/casos/{id}`).
- **Busca** client-side por nome/telefone/protocolo/summary/subcorredor/status.
- **Filtros**: status (derivado dos casos presentes) + subcorredor (quando houver). Mantido enxuto.
- Reuso dos padrões-mestre (`DetailHeader`, `StatusPill`, `Icon`) e `lib/attendance/labels.ts` → coerência com Fila e Detalhe. Dark/limpo/compacto, responsivo.
- Header com badge **"MVP ativo · sandbox"**; botões **Ver fila**, **Criar caso teste** (sandbox) e **Atualizar**.
- Estados: loading / error (retry) / empty ("Nenhum caso criado ainda. Crie um caso teste ou inicie um atendimento pela fila.") / loaded.

## 5. Segurança
- **Não** mostra CPF/`insured_document_ref`, `policy_snapshot` cru, prompt/config/`context_package`, tokens/segredos.
- Telefone só usado na busca (não é coluna destacada). Nada sugere acionamento real.

## 6. O que ficou fora (proposital)
Edição de caso pela lista; criação de dispatch packet; runtime LangGraph; envio WhatsApp/portal/InfoCap; filtros avançados (prioridade/verificação ficaram cobertos pela busca). Detalhe e ações seguras já existem no 42B4B.

## 7. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema | ✅ nenhum |
| backend Python / Supabase direto no client | ✅ nenhum |
| RAG/prompts/agentes/WhatsApp/envio externo | ✅ nenhum |
| PII sensível exposto | ✅ nenhum |

## 8. Deploy recomendado
- **Web apenas** (Next/UI). Sem backend Python, sem SQL/migration, sem reupload.

## 9. Testes manuais (após deploy Web)
1. Dashboard RAFAEL → **Atendimentos → Casos** → a lista real carrega (não mais o placeholder).
2. Os casos **Cliente Teste 42B5A** e **Cliente Teste UI** aparecem (se existirem).
3. **Busca** filtra por cliente/protocolo/status; **filtro de status/subcorredor** funciona.
4. **Abrir** num caso → vai para `/dashboard/atendimentos/casos/{id}` (detalhe 42B4B).
5. **Criar caso teste** → novo caso aparece após refresh.
6. **Chat Core** inalterado: CORE-001 (interno), CORE-007 (Resumo + Follow-up), CORE-006 (NEVOA-791).

## 10. Próximos passos
1. **42H1** — Human Support Destination Foundation (destino humano do dossiê).
2. **42B5B** — Corridor Runtime Step Engine (perguntar 1 slot por vez; preencher slots/`next_step`; HITL).
3. **42B6** — Dispatch Packet + WhatsApp dry-run/HITL.
4. Rodar **CORE-REGRESSION-001** após o deploy.
