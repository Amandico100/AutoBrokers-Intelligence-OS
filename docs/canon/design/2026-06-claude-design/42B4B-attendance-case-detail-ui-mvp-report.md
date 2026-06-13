# 42B4B — Attendance Case Detail UI MVP + Autonomy/Handoff Alignment Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem LangGraph/RAG/prompts/agentes/WhatsApp/envio externo) · sem deploy automático.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados/alterados
- `app/dashboard/atendimentos/casos/[caseId]/page.tsx` (**novo**) — server wrapper fino (await params) que renderiza o client.
- `app/dashboard/atendimentos/casos/[caseId]/CaseDetailClient.tsx` (**novo**) — página de detalhe do caso.
- `lib/attendance/labels.ts` (**novo**) — helpers de rótulo/tom compartilhados (subcorridor/priority/verification/risk/status/fmtDate).
- `app/dashboard/atendimentos/fila/AttendanceQueueClient.tsx` (**alterado**) — link **"Abrir caso"** no drawer → `/dashboard/atendimentos/casos/{id}` (drawer atual preservado).
- `docs/canon/design/2026-06-claude-design/42B4B-attendance-case-detail-ui-mvp-report.md` (este).

## 2. Rota criada
`/dashboard/atendimentos/casos/[caseId]` — detalhe de caso.

## 3. API consumida (existente 42B5A — não alterada)
- `GET /api/attendance/cases/[caseId]` — carrega case + conversation + messages + corridor_run + corridor_template + dispatch_packets.
- `PATCH /api/attendance/cases/[caseId]` — ações seguras (whitelist do endpoint).
Client **nunca** chama Supabase direto.

## 4. Ações PATCH implementadas
| Botão | Patch |
|---|---|
| Marcar como handoff | `status=handoff`, `handoff_required=true`, `handoff_reason='manual_review'`, `next_step='Caso marcado para revisão humana. Preparar dossiê para transferência.'` |
| Marcar prioridade alta | `priority=high` |
| Encerrar caso | `status=closed`, `next_step='Caso encerrado manualmente em modo sandbox.'` |
| Reabrir / coletar dados | `status=collecting_slots`, `handoff_required=false`, `handoff_reason=null`, `next_step='Coletar dados mínimos e validar apólice antes de qualquer acionamento externo.'` |
Sem drag-and-drop, sem edição livre de slots, sem dispatch packet, sem envio externo.

## 5. Como a UI representa a autonomia progressiva
Seção **"Autonomia do atendimento"** (coluna lateral):
- **Modo atual:** "Sandbox / dry-run" (lido de `diagnostics.mvp_mode='dry_run_hitl'`).
- "Ação externa automática: **bloqueada neste MVP**".
- **Visão final:** "autonomia permitida quando corredor, fonte, canal e readiness estiverem homologados."
- **Preparada para o futuro:** se `diagnostics.autonomy_level` existir (manual/gated/autonomous_assisted/production_autonomous), a UI já o exibe — **sem** nova lógica de backend agora.
Reflete o alinhamento do Founder: ponta a ponta autônomo quando houver corredor/fonte/canal/segurança; humano é exceção.

## 6. Como a UI representa handoff / dossiê humano
- Seção **"Dossiê / Handoff humano"** (coluna principal): motivo (se houver), **resumo para o humano**, contagem de coletados/faltantes, próximo passo, e "Destino humano: ainda não conectado neste MVP".
- Seção **"Handoff humano"** (lateral): `handoff_required`/`handoff_reason` + "Configuração de suporte humano será conectada em batch futuro. Quando o agente não conseguir resolver, ele deve montar dossiê e transferir para o humano configurado."
- Botão **"Marcar como handoff"** materializa o conceito via PATCH (sem envio real).

## 7. Decisões de UX
- Visual atual (dark/limpo/cards/grid responsivo `lg:grid-cols-3`), reuso de `DetailHeader`/`StatusPill`/`Icon` e `lib/attendance/labels.ts`.
- **Sandbox/dry-run** sinalizado no header, pills e seções; deixa claro que **ação externa automática está bloqueada apenas no MVP atual** e que autonomia final depende de corredor/fonte/canal/readiness.
- **"Apólice não verificada"** + aviso quando `verification_status=unverified` ("não confirmar cobertura sem fonte").
- **Faltantes** destacados como pendência (pills warning); coletados em success.
- Conversa: lista mensagens (role→cliente/agente) ou "Ainda não há mensagens espelhadas neste caso."; **sem** envio de mensagem.
- Dispatch: "Nenhum pacote de acionamento criado ainda." + "Nenhuma ação externa foi executada neste caso."
- Estados: loading, error (retry), not found (link p/ fila), loaded.

## 8. Segurança
- **Não** mostra `insured_document_ref`, `policy_snapshot` cru, CPF/documento, prompt/config/`context_package`, service role ou tokens.
- `coverage_evidence` só como resumo ("Evidência registrada"/"Sem evidência"), nunca o conteúdo bruto.
- Logs client mínimos.

## 9. O que ficou fora (proposital)
Runtime LangGraph / Attendance agent; envio WhatsApp/portal/InfoCap; criação de dispatch packet; edição de slots; drag-and-drop; integração real de destino humano. (42B5/42B6.)

## 10. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema | ✅ nenhum |
| backend Python / Supabase direto no client | ✅ nenhum |
| RAG/prompts/agentes/WhatsApp/envio externo | ✅ nenhum |
| PII sensível exposto | ✅ nenhum |

## 11. Deploy recomendado
- **Web apenas** (Next/UI). Sem backend Python, sem SQL/migration, sem reupload.

## 12. Testes manuais (após deploy Web)
1. **Fila** → clicar num card → drawer → **"Abrir caso"** → abre `/dashboard/atendimentos/casos/{id}`.
2. Detalhe mostra: resumo, conversa (vazia), slots coletados/faltantes, apólice ("não verificada"), dispatch packets (0, "nenhuma ação externa"), dossiê/handoff, corredor (Allianz Eletricista), diagnóstico (ação externa **bloqueada**), autonomia (sandbox/dry-run).
3. **Ações:** "Marcar prioridade alta" → pill muda; "Marcar como handoff" → status `handoff` + dossiê; "Reabrir" → `collecting_slots`; "Encerrar" → `closed`. (Refaz fetch a cada ação.)
4. **Chat Core** inalterado: CORE-001 (interno), CORE-007 (Resumo + Follow-up), CORE-006 (NEVOA-791).

## 13. Próximos passos
1. **42B5** — runtime assistido do corredor (Attendance + LangGraph + Context Package; perguntar 1 slot por vez; HITL via `approval_requests`; preencher slots/`next_step` automaticamente).
2. **42B6** — dispatch_packet + WhatsApp dry-run/HITL.
3. **42B-handoff** — conectar destino humano real (Vault/conector) ao dossiê.
4. Rodar **CORE-REGRESSION-001** após o deploy.
