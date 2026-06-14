# 42B5J — Dashboard Conversation Simulator Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/UI** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/WhatsApp/InfoCap real/dispatch/approval) · sem deploy automático.
> **Data:** 2026-06-14 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 0. Auditoria
Lidos/confirmados: `SPEC-005`, `SPEC-006`, `SPEC-004`, `ADR-003`, relatórios `42B5H` e `42I1`; helpers `attendance-macro-state.ts`, `corridor-runtime.ts`, `runtime-config-resolver.ts`, `runtime-slot-catalog.ts`, `policy-lookup.ts`; rotas `cases/[caseId]` (GET) e `runtime/{reply,step,policy-lookup}`; `CaseDetailClient.tsx`, `HandoffDossierPanel.tsx` (padrão de painel client) e `lib/attendance/labels`. **Legado Agent OS não está sincronizado no workspace local** — seguido pelos docs canônicos (que já consolidam runtime conversacional/conversa com cliente).

## 1. Arquivos criados/alterados
- `app/dashboard/atendimentos/casos/[caseId]/AttendanceConversationSimulator.tsx` (**novo**) — painel client do simulador.
- `app/dashboard/atendimentos/casos/[caseId]/CaseDetailClient.tsx` (**alterado**) — import + render do simulador no topo da coluna principal, com `onChanged={load}` para sincronizar os demais painéis.
- `docs/canon/design/2026-06-claude-design/42B5J-dashboard-conversation-simulator-report.md` (este).

## 2. O que o simulador faz
Dentro do detalhe do caso, sem console e sem WhatsApp:
- **Cabeçalho** "Simulador de conversa" + badge "MVP · sem WhatsApp real" + botão Atualizar.
- **Resumo técnico enxuto** (mini-cards): Status (pill), Macro estado, Prioridade, Risco (pill se ≠ low), Verificação, Policy source, Slot atual, Última ação, Evidência (pronta/não).
- **Próximo passo** e **alertas**: handoff, risco alto, apólice não verificada, evidência registrada.
- **Lista de mensagens** estilo chat (Cliente/Segurado à direita, Agente à esquerda, cronológica, auto-scroll, estado vazio).
- **Campo de entrada** ("Digite uma mensagem como se fosse o segurado…") + botão **Enviar como cliente** (Enter envia; Shift+Enter quebra linha); loading/erro; recarrega após sucesso.
- Botão **Rodar próximo passo do agente** (step); 409 → aviso amigável ("Caso em handoff/fechado/cancelado não pode ser avançado automaticamente").
- Botão condicional **Simular consulta de apólice (mock)** — aparece quando `macro_state==='policy_lookup_required'` OU `last_agent_action==='policy_lookup:pending'` OU (`verification_status==='unverified'` e existe `insured_document_ref`).
- **Aviso fixo** de segurança: "Simulador MVP: nenhuma mensagem é enviada por WhatsApp. Nenhuma ação externa é executada automaticamente. A consulta de apólice é mock/manual (sem InfoCap real)."

## 3. Endpoints consumidos (nenhum novo)
- `GET /api/attendance/cases/[caseId]` — carrega caso + mensagens + corridor_run.
- `POST /api/attendance/cases/[caseId]/runtime/reply` — `{ message, source:'dashboard' }`.
- `POST /api/attendance/cases/[caseId]/runtime/step` — `{ source:'dashboard' }`.
- `POST /api/attendance/cases/[caseId]/runtime/policy-lookup` — `{ source:'mock', mode:'mock', fixture:'allianz_residential_electrician_covered' }`.

## 4. Como o E2E é testado pela UI
Abrir caso → digitar como segurado → Enviar → ver resposta do agente → Rodar próximo passo → quando chegar no gate de apólice, Simular consulta de apólice → Rodar próximo passo (retoma o corredor) → ver o caso avançar visualmente (status/macro/slot/evidência atualizam a cada ação).

## 5. Garantias de segurança
- `company_id` é resolvido server-side em todas as rotas (o simulador só chama os endpoints existentes).
- **CPF/CNPJ não é exibido** — `insured_document_ref` é usado apenas para condição do botão de lookup, nunca renderizado.
- Não expõe secrets/tokens/`destination_ref`/envs.
- Caso em `handoff/closed/cancelled` → entrada bloqueada + avisos; step retorna 409 tratado.
- Deixa explícito que o policy lookup é mock e que nada é enviado externamente; cobertura só aparece via `coverage_evidence`/flags do runtime (a UI não afirma cobertura por conta própria).

## 6. Confirmação de escopo
**Não** alterou SQL/schema/migrations, backend Python, RAG, prompts/agentes, WhatsApp, InfoCap real, dispatch, approval, Vault, Core chat nem Auxiliares. Apenas 1 componente novo + 2 linhas no `CaseDetailClient` + relatório. Nenhum motor paralelo: o simulador é uma **casca de UI** sobre o runtime determinístico existente.

## 7. Conexão futura com Smith/Attendance Agent
O simulador prova o runtime determinístico (estado/gates/slots) que o Attendance Agent/Smith chamará como **tools** (reply/step/policy-lookup) quando o canal real (WhatsApp) entrar. A mesma UI servirá para operação assistida (HITL) sobre a conversa real, sem mudar o motor.

## 8. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema · backend Python · RAG · prompts/agentes · WhatsApp · InfoCap real · dispatch/approval | ✅ nenhum |
| Core chat / Auxiliares | ✅ intactos |
| CPF/secret/PII exposto na UI | ✅ nenhum |

## 9. Testes manuais (após deploy Web)
Abrir **Atendimentos → Fila → caso** (ou Casos → caso). No painel "Simulador de conversa":
- **A — saudação:** "Oi" → "Olá! Em que posso te ajudar?".
- **B — problema:** "Estou sem luz só na cozinha" → reconhece + pergunta risco.
- **C — risco baixo:** "Não, sem cheiro de queimado nem faísca." → pede CPF.
- **D — CPF:** "123.456.789-09" → informa que vai localizar apólice; aparece botão "Simular consulta de apólice".
- **E — consulta mock:** clicar "Simular consulta de apólice" → evidência registrada, macro `policy_evidence_ready`.
- **F — retomada:** clicar "Rodar próximo passo do agente" → "Apólice localizada…" + pergunta `affected_area`.
- **G — risco alto (outro caso):** "Tem cheiro de queimado e saiu uma faísca." → orientação de segurança + handoff; depois "Rodar próximo passo" → aviso 409 amigável.
- **Core/Auxiliares/RAG** intactos (Core interno; Resumo + Follow-up; NEVOA-791).

## 10. Próximo batch recomendado
**42I2 — InfoCap Connector Read-only (via Vault)** (substitui o mock por consulta real, mantendo contrato e simulador). Em paralelo: **42B7** (golden tests do fluxo E2E). Depois: 42I3 (normalizer), 42B6 (dispatch dry-run/HITL), 42W1 (WhatsApp controlado).
