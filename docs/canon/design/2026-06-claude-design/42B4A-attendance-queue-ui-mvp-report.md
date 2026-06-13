# 42B4A — Attendance Queue UI MVP Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/WhatsApp/envio externo) · sem deploy automático.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados/alterados
- `app/dashboard/atendimentos/fila/AttendanceQueueClient.tsx` (**novo**) — client component da Fila (Kanban + busca + drawer de detalhe + criar caso teste + atualizar).
- `app/dashboard/atendimentos/fila/page.tsx` (**alterado**) — substituiu o `ModulePlaceholder` por um wrapper fino que renderiza o client (mantém `metadata`).
- `lib/mock/tenant-modules.ts` (**alterado**) — área `fila` passou de "Em breve" para **"MVP ativo"** (tone `info`). Nenhum outro módulo alterado.
- `docs/canon/design/2026-06-claude-design/42B4A-attendance-queue-ui-mvp-report.md` (este).

## 2. API consumida (existente, 42B5A — não alterada)
- `GET /api/attendance/cases?limit=100` — lista.
- `GET /api/attendance/cases/[caseId]` — detalhe (drawer).
- `POST /api/attendance/cases` — botão "Criar caso teste" (sandbox).
Client **nunca** chama Supabase diretamente; sempre via as rotas Next.

## 3. Colunas implementadas (Kanban com scroll horizontal)
| Coluna | Statuses |
|---|---|
| Primeiro contato | new, triage |
| Coletando dados | collecting, collecting_slots, policy_check, corridor_selected |
| Acionando seguradora | ready_for_dispatch, awaiting_approval, action_prepared |
| Aguardando retorno | following_up |
| Concluído | closed |
| Atenção | handoff, blocked, cancelled (+ status desconhecido) |

## 4. Decisões de UX
- **Visual atual** (dark, limpo, cards compactos): reusa os padrões-mestre `DetailHeader`, `StatusPill`, `Icon`, e tokens (`bg-card`, `border-border`, `text-muted-foreground`, `bg-surface-2`, `bg-brand-soft`). Inspirado no Kanban antigo (colunas de processo), **sem** copiar o design legado.
- **Estados:** loading (spinner), error (com retry), empty (com CTA), loaded (Kanban).
- **Cards:** nome (ou "Segurado não informado"), `case_number`, summary (line-clamp 2), badges "Assistência" · seguradora · subcorredor (ex.: "Eletricista"), pills de **Apólice (não verificada/pendente/verificada)**, **Prioridade**, **Risco** (quando ≠ low). `updated_at` formatado pt-BR. Borda de **atenção** (danger) para coluna Atenção e risco high/critical.
- **Busca** client-side por nome/telefone/case_number/summary/subcorredor (placeholder pedido).
- **Detalhe (Opção A):** ao clicar no card, drawer lateral chama `GET /api/attendance/cases/[caseId]` e mostra caso + corridor_run (fase/status, **ação externa bloqueada (HITL)**), **slots coletados/faltantes**, próximo passo, template (readiness/fases/guardrails/golden) e **contagem de dispatch_packets**. Sem edição.
- **Criar caso teste:** botão tracejado marcado como sandbox; payload seguro (Eletricista). **Atualizar:** refaz o fetch.
- **Sandbox/dry-run** sinalizado no subtítulo e no drawer ("nenhuma ação externa é executada").

## 5. O que ficou fora (proposital)
- **Sem drag-and-drop** (mudança de status exige regras de corredor/HITL — fora do MVP).
- Sem página de detalhe dedicada (drawer já valida o endpoint de detalhe).
- Sem edição de caso pela UI (PATCH existe na API, mas não exposto aqui).
- Sem WhatsApp/portal/InfoCap/envio externo; sem runtime LangGraph.
- Não mostra CPF/documento; telefone só usado na busca (não destacado no card).

## 6. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema | ✅ nenhum |
| backend Python / Supabase MCP | ✅ nenhum |
| RAG/prompts/agentes/WhatsApp/envio externo | ✅ nenhum |
| segredo/PII exposto | ✅ nenhum (sem CPF/config/agent internals) |

## 7. Deploy recomendado
- **Web apenas** (Next/UI). Sem backend Python, sem SQL/migration, sem reupload.

## 8. Testes manuais (após deploy Web)
1. Dashboard RAFAEL → **Atendimentos → Fila** → a fila real carrega (não mais o placeholder).
2. O caso criado no 42B5A aparece na coluna **Coletando dados** (status `collecting_slots`).
3. **Criar caso teste** → novo card aparece após o refresh.
4. Clicar no card → drawer mostra caso + corridor_run + slots filled/missing + template Allianz Eletricista + dispatch_packets = 0.
5. **Busca** filtra por nome/telefone/protocolo.
6. **Chat Core** inalterado: CORE-001 (interno), CORE-007 (Resumo + Follow-up), CORE-006 (NEVOA-791).

## 9. Próximos passos
1. **42B5** — runtime assistido do corredor (Attendance agent + LangGraph + Context Package; perguntar 1 slot por vez; HITL via `approval_requests`).
2. **42B4B** — UI de detalhe do caso / Conversas (espelho de mensagens).
3. **42B6** — dispatch_packet + WhatsApp dry-run/HITL.
4. Rodar **CORE-REGRESSION-001** após o deploy.
