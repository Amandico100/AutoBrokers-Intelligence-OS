# 42B5F — First Response & Low-Friction Intake Policy Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/UI/WhatsApp/dispatch/approval/Vault/Auxiliares/Core) · sem deploy automático.
> **Data:** 2026-06-13 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados/alterados
- `lib/attendance/runtime-intake-policy.ts` (**novo**) — política pura `evaluateFirstResponseIntake`.
- `lib/attendance/runtime-slot-catalog.ts` (**alterado**) — exporta `RISK_SAFETY_QUESTION_CORE` e a pergunta de risco passa a reutilizá-lo (sem mudança de texto).
- `app/api/attendance/cases/[caseId]/runtime/reply/route.ts` (**alterado**) — branch de intake quando não há pergunta ativa.
- `docs/canon/design/2026-06-claude-design/42B5F-first-response-low-friction-intake-report.md` (este).

`corridor-runtime.ts` e `runtime-safety-policy.ts` **não** mudaram (reutilizados).

## 2. Como a política de primeira resposta foi implementada
`evaluateFirstResponseIntake({ message, filledSlots })` é **pura, sem I/O**. Classifica a mensagem por ordem de prioridade segura:
1. **high_risk_described** — `extractSlotValue('risk_indicators', message).riskHigh === true` (cheiro de queimado/faísca/fumaça/choque/fogo/curto). Aplica a política 42B5E.
2. **problem_already_described** — bate `PROBLEM_RE` (luz/energia/tomada/disjuntor/chuveiro/vazamento/chave/guincho/eletrodoméstico/assistência…). Reconhece e pergunta risco.
3. **greeting_only** — a mensagem inteira é saudação/"tem alguém?"/"pode ajudar?".
4. **needs_help_unclear** — pedido vago ("preciso de ajuda", "tenho um problema") ou ≤3 palavras sem palavra-chave.
5. **fallback** — mensagem substantiva sem palavra-chave conhecida → tratada como problema descrito (reconhece + pergunta risco).

A rota só chama a política quando **não há pergunta ativa do agente** (`diagnostics.runtime.selected_slot` ausente **e** `last_agent_action` não começa com `ask:`) e o caso é editável.

## 3. Quando "Em que posso te ajudar?" aparece — e quando é proibido
- **Aparece** apenas em `greeting_only` (cliente só cumprimentou / perguntou se tem alguém): resposta `Olá! Em que posso te ajudar?`.
- **Proibido** quando o cliente já descreveu o problema (`problem_already_described`/fallback): nunca repete "em que posso te ajudar?"; responde reconhecendo e avançando: `Entendi. Vou te ajudar com isso. <pergunta de risco>`.
- Em pedido vago (`needs_help_unclear`): `Claro. Me conta rapidamente o que aconteceu para eu te ajudar.` (também não repete a saudação genérica).

## 4. Como evita perguntas desnecessárias
- Máximo **uma** pergunta principal por resposta; mensagens curtas, estilo WhatsApp, sem termos internos.
- **Não** pede CPF/apólice/seguradora na primeira resposta; **não** escolhe corredor definitivo; **não** abre checklist.
- `problem_description` só é atualizado se estiver vazio/genérico (`isGenericProblem` ignora "Atendimento iniciado pelo dashboard", "teste", "sandbox", etc.), evitando sobrescrever relato real e evitando tratar texto automático como problema.
- Dedupe: a mensagem `assistant` só é inserida se `force=true` ou se diferir da última `assistant`.

## 5. Como preserva o fluxo de slots (42B5B/C/D/E)
A política **só** atua quando não há pergunta ativa. Assim que ela reconhece um problema, **arma** a pergunta de risco definindo `selected_slot='risk_indicators'` e `last_agent_action='ask:risk_indicators'` — então a **próxima** `/runtime/reply` cai no fluxo normal de slot intake (extrai `risk_indicators` → `affected_area` → `electrical_issue_type`). O fluxo `step → reply → reply` testado continua idêntico (quando o `step` já perguntou risco, `hasActiveQuestion=true` e a política nem é consultada). A pergunta de risco é **reutilizada** do catálogo via `RISK_SAFETY_QUESTION_CORE` (sem duplicar texto).

## 6. High-risk first message
Se a primeira mensagem já traz risco alto, a rota aplica `evaluateRuntimeSafetyDecision` (42B5E): preenche `risk_indicators`, marca `priority/risk_level=high`, `handoff_required=true`, `handoff_reason=high_risk_electrical`, `status=handoff`, `phase=handoff`, responde a orientação de segurança e `last_agent_action='safety_handoff:first_response'`. Não pergunta "em que posso ajudar?" nem `affected_area`. `external_action_allowed=false`.

## 7. Side effects que NÃO acontecem
Sem WhatsApp/envio externo; sem `dispatch_packet`; sem `approval_request`; sem InfoCap/portal; sem confirmação de cobertura; sem dossiê automático; sem alteração de SQL/schema/migration, backend Python, RAG, prompts/agentes, UI, Vault, Auxiliares, Core. Logs sem telefone/mensagem/slots/PII.

## 8. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema · backend Python · RAG · prompts/agentes · UI · WhatsApp | ✅ nenhum |
| dispatch · approval · Vault · InfoCap/portal · dossiê automático | ✅ nenhum |
| Core chat / Auxiliares | ✅ inalterado |
| token/secret/PII no diff | ✅ nenhum |

## 9. Testes manuais (após deploy Web)
- **A — greeting:** caso novo → `reply` `{message:'Oi'}` → assistant `Olá! Em que posso te ajudar?`, `last_agent_action=intake:greeting`, status segue `collecting_slots`, sem CPF/apólice/risco.
- **B — problema descrito:** caso novo → `reply` `{message:'Estou sem luz só na cozinha'}` → assistant `Entendi. Vou te ajudar com isso. Antes de seguir…`, `selected_slot=risk_indicators`, `last_agent_action=ask:risk_indicators`, sem handoff.
- **C — high risk first:** `reply` `{message:'Tem cheiro de queimado e saiu uma faísca'}` → `status=handoff`, `priority/risk_level=high`, `handoff_reason=high_risk_electrical`, orientação de segurança, `last_agent_action=safety_handoff:first_response`, sem `affected_area`.
- **D — unclear:** `reply` `{message:'Preciso de ajuda'}` → assistant `Claro. Me conta rapidamente o que aconteceu para eu te ajudar.`, `last_agent_action=intake:clarify_need`.
- **E — fluxo de slots clássico:** `step` (pergunta risco) → `reply` "Não, sem cheiro…" → `affected_area` → `reply` "É só na cozinha" → `electrical_issue_type`.
- **F — Core regression:** Core interno + Auxiliares (Resumo + Follow-up) + NEVOA-791 intactos.

## 10. Deploy recomendado
- **Web apenas** (route handler + helpers puros). Sem backend Python, sem SQL/migration.

## 11. Próximos passos
- **42B6** — Dispatch Packet + WhatsApp dry-run/HITL (e, no handoff, gerar dossiê + transferir ao destino humano de 42H1–H5).
- Refinos futuros de intake: personalização de saudação com nome (quando confiável), retomada de caso existente (`resume_existing`), classificação de mídia sem contexto.
