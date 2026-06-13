# 42H5 — Handoff Dossier UI in Case Detail Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/WhatsApp/envio externo/approval/dispatch) · sem deploy automático.
> **Data:** 2026-06-13 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados/alterados
- `app/dashboard/atendimentos/casos/[caseId]/HandoffDossierPanel.tsx` (**novo**) — painel client que consome o endpoint do dossiê (42H4).
- `app/dashboard/atendimentos/casos/[caseId]/CaseDetailClient.tsx` (**alterado**) — a antiga `Section "Dossiê / Handoff humano"` (estática, com "ainda não conectado neste MVP") foi substituída pelo `<HandoffDossierPanel />`.
- `docs/canon/design/2026-06-claude-design/42H5-handoff-dossier-ui-report.md` (este).

## 2. Endpoint consumido (42H4 — não alterado)
- `GET /api/attendance/cases/[caseId]/handoff-dossier` → `{ dossier }` (estruturado + `dossier.markdown`).
- O painel **só** chama esse endpoint; **nunca** Supabase direto, **nunca** envia mensagem, **não** cria `approval_request` nem `dispatch_packet`.

## 3. O que o painel faz
1. **Gerar/atualizar o dossiê** — botão "Gerar dossiê" (estado inicial) e, após carregado, "Atualizar dossiê".
2. **Auto-load** quando `handoff_required=true` ou `status='handoff'` (carrega ao montar); caso contrário, sob demanda no clique.
3. **Markdown copiável** em bloco `pre` rolável (`max-h-[360px]`, `whitespace-pre-wrap`).
4. **Copiar o dossiê** — `navigator.clipboard.writeText(dossier.markdown)` com fallback `textarea + execCommand` para contextos não seguros; feedback "Dossiê copiado" (2,5 s).
5. **Resumo visual** (mini-cards): Status, Prioridade, Risco, Coletados (count `slots.filled`), Faltantes (count `slots.missing`), Mensagens (`messages.message_count`).
6. **Destino humano**: se `support_destination.configured` → `primary.name` + `destinationTypeLabel(type)` + **`display_ref` mascarado**; senão → "Destino humano ainda não configurado. Configure em Personalização → Corretora → Suporte humano" (link).
7. **Aviso fixo**: "Nenhuma ação externa foi executada. Copiar este dossiê não envia mensagem para o segurado, seguradora ou suporte humano."

## 4. Badges de estado
| Condição | Badge |
|---|---|
| Erro ao carregar | **Erro** (danger) |
| Dossiê ainda não gerado | **Não gerado** (neutral) |
| Gerado, sem destino ativo | **Sem destino humano** (warning) |
| Gerado, com destino ativo | **Pronto para copiar** (success) |

## 5. Estados de UI
`loading` (spinner "Gerando dossiê…"), `error` (caixa danger + "Tentar novamente"), `!dossier` (CTA "Gerar dossiê"), `dossier` carregado (resumo + destino + markdown + aviso), `copied` (feedback no botão).

## 6. Segurança / PII
- Renderiza apenas `display_ref` (mascarado pela API/42H4) — **nunca** recebe nem mostra `destination_ref` cru, token, secret ou `tenant_connection`.
- Sem Supabase service role no client; sem `NEXT_PUBLIC_` de segredo; sem log de telefone/markdown/PII.
- O telefone do cliente, quando presente no markdown, vem do endpoint (necessário para o humano continuar o atendimento) — o painel apenas exibe o markdown já montado pelo backend.

## 7. Confirmações de comportamento
- **NÃO envia WhatsApp / mensagem.**
- **NÃO cria** `approval_request` nem `dispatch_packet`.
- **NÃO altera** banco/schema/Supabase/backend Python/RAG/prompts/agentes/WhatsApp.
- Apenas leitura do endpoint + cópia local para a área de transferência.

## 8. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema | ✅ nenhum |
| backend Python / Supabase no client | ✅ nenhum |
| RAG/prompts/agentes/WhatsApp/envio externo/approval/dispatch criado | ✅ nenhum |
| token/secret/`destination_ref` cru exposto | ✅ nenhum |

## 9. Deploy recomendado
- **Web apenas** (Next/UI). Sem backend Python, sem SQL/migration.

## 10. Testes manuais (após deploy Web)
1. **Atendimentos → Fila → abrir um caso** → a coluna principal mostra o painel **"Dossiê / Handoff humano"**.
2. Caso comum: badge **"Não gerado"** → clicar **"Gerar dossiê"** → carrega resumo + markdown + destino.
3. Caso com `handoff_required=true` ou `status='handoff'`: dossiê **auto-carrega** ao abrir.
4. **Copiar dossiê** → botão vira "Dossiê copiado"; colar em editor → markdown do endpoint (42H4).
5. Com destino ativo: linha "Destino configurado: Suporte humano principal — WhatsApp grupo — `120363****6552@g.us`" (**mascarado**).
6. Sem destino ativo: badge **"Sem destino humano"** + link para Personalização → Corretora → Suporte humano.
7. Conferir que **nenhuma** mensagem é enviada, nenhum `approval_request`/`dispatch_packet` é criado.
8. **Chat Core** inalterado (CORE-001/006/007).

## 11. Próximos passos
1. **42B5B** — Corridor Runtime Step Engine (Attendance agent + LangGraph + Context Package; 1 slot por vez; HITL via `approval_requests`).
2. **42B6** — Dispatch Packet + WhatsApp dry-run/HITL usando o destino primário/fallback configurado (42H1–H3).
