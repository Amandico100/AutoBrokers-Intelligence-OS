# 42B5K — Conversational Recovery & Smart Fallback Layer Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só TS/Next/lib de atendimento** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/WhatsApp/InfoCap/dispatch/approval/Vault/Core/Auxiliares) · sem deploy automático.
> **Data:** 2026-06-14 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 0. Auditoria
Lidos/confirmados: `SPEC-004`, `SPEC-005`, `SPEC-006`, `ADR-003`, relatórios `42B5G/H/J`; `app/api/chat/route.ts` e `backend/app/api/chat.py` (Core/Smith — **não** alterados/chamados); rotas `runtime/{reply,step}`; helpers `corridor-runtime`, `runtime-slot-catalog`, `runtime-config-resolver`, `runtime-intake-policy`, `runtime-identity-policy`, `runtime-safety-policy`, `attendance-macro-state`. **Legado Agent OS não está sincronizado no workspace local** — seguido pelos docs canônicos consolidados (ADR-003 §36 RAG, §13 apólice; SPEC-004/005 runtime conversacional).

## 1. Arquivos alterados/criados
- `lib/attendance/runtime-message-router.ts` (**novo**) — classificador puro `classifyMessageRoute`.
- `lib/attendance/runtime-conversation-recovery.ts` (**novo**) — `buildRecoveryResponse` + `inferSlotsFromMessage`.
- `lib/attendance/corridor-runtime.ts` (**alterado**) — `computeRuntimeStep` auto-satisfaz `policy_evidence_status` quando há evidência confiável.
- `app/api/attendance/cases/[caseId]/runtime/reply/route.ts` (**alterado**) — precedência global de risco alto + recuperação no gate de identidade + recuperação no fluxo de slot; `safeReplyCase` (não expõe CPF).
- `docs/canon/design/2026-06-claude-design/42B5K-conversational-recovery-report.md` (este).

## 2. Usou fallback LLM/Smith?
**Não.** Não havia caminho seguro de LLM dentro do escopo (não chamar Core, não alterar backend Python, não improvisar integração perigosa). A recuperação é **determinística e honesta**: não inventa cobertura nem trivia. O **fallback inteligente (responder perguntas abertas via Attendance Agent/Smith) fica para batch futuro**, quando o agente de atendimento estiver conectado ao canal — este batch garante que sair do fluxo **não derruba o corredor**.

## 3. Como evitou motor paralelo
A camada é um **classificador + roteador determinístico** que decide *como tratar a mensagem* antes da extração de slot, reutilizando os componentes existentes (`extractSlotValue`, `computeRuntimeStep`, `evaluateRuntimeSafetyDecision`, slot catalog, config resolver). Não cria agente, não usa prompt solto, não duplica runtime. É a mesma camada que o Smith chamará como tool.

## 4. Classificador (`MessageRouteKind`)
`slot_answer` (default seguro) · `off_topic_general_question` · `frustration_or_repetition` · `unavailable_data` · `correction` · `clarification_question` · `delay_request` · `unsafe_or_high_risk` · `unknown`. Considera: mensagem, slot ativo, `last_agent_action`, `macro_state`, `filled`, `missing`. **Conservador:** na dúvida → `slot_answer` (preserva 42B5C/D/E/F/G/H).

## 5. Comportamentos
- **Off-topic** ("O que significa van nos nomes holandeses?"): reconhece que é pergunta geral, **não** responde trivia (evita alucinação), **re-steer** para a pergunta atual; **não** reinicia corredor, **não** re-pergunta risco, **não** preenche slot, **não** muda status; grava user+assistant; `diagnostics.runtime.conversation_recovery.kind=off_topic_general_question`; `external_action_allowed=false`.
- **Frustração/repetição** ("JÁ DISSE. ESTOU SEM LUZ SÓ NA COZINHA. PRECISO DE UM ELETRICISTA."): reconhece, **infere** `affected_area=cozinha` e `electrical_issue_type=no_power` (se faltantes), **não** re-pergunta o já dito e **avança** para o próximo slot útil.
- **Dado indisponível** (no gate de CPF: "Não estou com o CPF agora."): resposta natural, **mantém `identity_required`**, **não** trata como CPF inválido seco, **não** avança para `policy_lookup_required`.
- **Clarificação** ("por que precisa do meu CPF?"): explica o motivo + re-pergunta.
- **Adiamento** ("um momento"): aguarda + re-pergunta, mantém estado.
- **Evidência pronta** (Test D): `computeRuntimeStep` considera `policy_evidence_status` satisfeito quando há `coverage_evidence` + `verification_status` confiável → **não** pergunta número/documento de novo; segue para o próximo slot/readiness. Genérico (vale step e reply).
- **Risco alto (precedência)**: qualquer mensagem com risco alto **em pergunta ativa** → safety/handoff (42B5E), `status=handoff`, orientação de segurança, **sem** pedir CPF, **sem** continuar coleta. A primeira mensagem (sem pergunta ativa) continua tratada pela intake policy (42B5F).

## 6. Não podou a inteligência
O runtime governa estado/segurança, mas a resposta é contextual e humana e **não** repete perguntas desnecessárias. O determinismo aqui é um trilho de segurança; a inteligência aberta entra com o Smith no fallback futuro.

## 7. Segurança / escopo
`company_id` server-side; **CPF nunca exibido** (resposta usa `safeReplyCase`, que remove `insured_document_ref`; logs só com `maskDocument`/sem conteúdo). Sem segredo/token/env exposto. **Não** alterou SQL/schema/migrations, backend Python, RAG, prompts/agentes, WhatsApp, InfoCap, dispatch, approval, Vault, Core, Auxiliares. (Observação: as demais branches de `reply`/`step` ainda retornam o caso com `insured_document_ref`; recomenda-se um follow-up para aplicar `safeReplyCase` em todas — fora do escopo deste batch.)

## 8. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/schema/backend Python/RAG/prompts/agentes/WhatsApp/InfoCap/dispatch/Vault | ✅ nenhum |
| Core / Auxiliares | ✅ intactos |
| credencial/secret/CPF completo logado/exposto | ✅ nenhum (mascarado/omitido) |

## 9. Testes manuais (após deploy Web, via simulador 42B5J ou console)
- **A — off-topic:** no meio do atendimento, "O que significa van nos nomes holandeses?" → resposta curta + volta ao atendimento; sem handoff, sem re-perguntar risco, sem preencher slot errado.
- **B — frustração:** "JÁ DISSE. ESTOU SEM LUZ SÓ NA COZINHA. PRECISO DE UM ELETRICISTA." → reconhece, infere área/tipo, segue para o próximo dado faltante.
- **C — CPF indisponível:** no gate de CPF, "Não estou com o CPF agora." → resposta natural, mantém `identity_required`, não avança.
- **D — evidência pronta:** após policy lookup mock, o runtime não pergunta número/documento da apólice de novo.
- **E — risco alto:** "Tem cheiro de queimado e saiu faísca" → handoff (42B5E).
- **F — Core regression:** Core interno; Auxiliares (Resumo + Follow-up); RAG NEVOA-791.

## 10. Próximo batch recomendado
**42I2 — InfoCap Connector Read-only (via Vault)** (substitui o mock por consulta real, mantendo contrato/simulador), e/ou **42B5L — Attendance Agent LLM Fallback** (responder perguntas abertas/explicar com o Smith/Attendance Agent, governado pelos guardrails, fechando o off-topic com inteligência real). Em seguida: 42B7 (golden tests E2E), 42B6 (dispatch dry-run/HITL).
