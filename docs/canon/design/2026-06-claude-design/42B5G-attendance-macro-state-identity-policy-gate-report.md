# 42B5G — Attendance Macro State Machine & Identity/Policy Gate Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/UI/WhatsApp/InfoCap real/dispatch/approval/Vault/Auxiliares/Core) · sem deploy automático.
> **Data:** 2026-06-13 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados/alterados
- `lib/attendance/attendance-macro-state.ts` (**novo**) — `MACRO_STATES`, `evaluateAttendanceMacroState`, `macroGateOverride`, `caseNeedsPolicy`, `hasValidIdentity`.
- `lib/attendance/runtime-identity-policy.ts` (**novo**) — `extractDocument` (CPF/CNPJ), `maskDocument`, mensagens de identidade/apólice.
- `app/api/attendance/cases/[caseId]/runtime/reply/route.ts` (**alterado**) — gate de identidade (resposta de CPF) + override de macro gate antes da coleta de corredor.
- `app/api/attendance/cases/[caseId]/runtime/step/route.ts` (**alterado**) — aplica o macro gate (pergunta identidade/apólice) quando o risco já foi resolvido.
- `docs/canon/design/2026-06-claude-design/42B5G-attendance-macro-state-identity-policy-gate-report.md` (este).

## 2. Documentos auditados
- Repo: `SPEC-005` (fluxo ponta a ponta §7.1: Entrada → Identificação do segurado → Identificação de apólice → Evidência → Corredor → slots → dispatch/HITL), `SPEC-006`, `SPEC-004`, `ADR-003-atendimento.md`, `ADR-002-vault.md`, os 5 módulos de runtime (B/C/D/E/F) e `docs/sql/42B3-...sql` (vocabulário de `attendance_cases.status`).
- Legado `AUTOBROKERS_AGENT_OS/02_RUNTIME_CONVERSACIONAL/...`: **não está sincronizado no workspace local** — usado apenas como base conceitual via SPEC-005 (que já o consolida). Nada de PII/conteúdo bruto copiado.

## 3. Como a macro state machine funciona
`evaluateAttendanceMacroState({ caseRow, filledSlots, riskHigh })` é **pura** e decide o macro estado + o próximo gate obrigatório, com precedência:
`handoff/closed` → **risco alto** → **coleta de risco** → **identidade** → **apólice/InfoCap** → **corredor**.
Estados (`MACRO_STATES`): `entry, needs_intent, identity_required, identity_collecting, policy_lookup_required, policy_lookup_blocked, policy_lookup_pending, policy_selected, operational_decision, corridor_selected, corridor_collecting_slots, handoff, closed`. O macro estado é persistido em `corridor_runs.diagnostics.runtime.macro_state` e `attendance_cases.metadata.attendance_macro_state` — **sem migration** (usa colunas jsonb existentes). `macroGateOverride(...)` traduz a decisão em um override de próxima resposta (identidade/apólice) ou `null` (corredor segue).

## 4. Como a identidade/CPF entra
- Quando o risco foi resolvido (low) e o caso precisa de apólice mas não tem `insured_document_ref`, o gate **interrompe** a coleta do corredor e pergunta o documento com motivo claro: *"Perfeito. Para eu localizar sua apólice antes de confirmar qualquer cobertura, pode me enviar o CPF do segurado?"* (`last_agent_action=ask:identity_document`).
- A resposta é interceptada antes do fluxo de slot: `extractDocument` reconhece **CPF (11)** ou **CNPJ (14)** com/sem pontuação (valida só formato/tamanho neste batch). Válido → grava `attendance_cases.insured_document_ref` + `metadata.identity.document_type`, status `policy_check`, macro `policy_lookup_required`. Inválido → reesclarece sem loop ruidoso.
- **Nunca** pede CPF em saudação/pedido vago; **nunca** repete se já existe documento; **nunca** loga o número completo (`maskDocument` → `***09 (len=11)`); **nunca** manda para RAG; receber CPF **não** confirma cobertura, só habilita o lookup futuro.

## 5. Como o gate de Apólice/InfoCap fica preparado
Com documento presente e apólice ainda não verificada → macro `policy_lookup_required`, status `policy_check`, `verification_status` permanece `unverified`/`pending_human`, `policy_source` **não** vira `infocap`. Mensagem: *"Obrigado. Vou usar esse dado para localizar a apólice em fonte segura…"* e `next_step` registra explicitamente que o **lookup será implementado no próximo batch** (não confirmar cobertura nem acionar até verificação). `diagnostics` registra que a apólice não foi verificada e que dispatch real está bloqueado.

## 6. Por que NÃO implementei InfoCap real agora
O batch é a **fundação de estado/gate**, não a integração. InfoCap exige conector + Vault + tratamento de PII/credenciais e desenho de read-only (SPEC-005 §12). Implementar agora misturaria escopo e risco. Aqui apenas **preparamos** o estado e o próximo passo para o lookup, garantindo que o sistema **não pule** identidade/apólice rumo a acionamento.

## 7. Como isto evita criar motor paralelo ao Smith
A macro state machine é uma **camada determinística de controle** (Next API/runtime), não um segundo cérebro. Ela governa estado, gates e segurança e reutiliza os componentes já existentes (`computeRuntimeStep`, `extractSlotValue`, `evaluateRuntimeSafetyDecision`, slot catalog, config resolver). O 42B5E/F viram componentes dentro da sequência.

## 8. Como preserva a inteligência da LLM
O gate só decide **estado / próximo gate obrigatório / segurança / o que precisa de fonte** — não escreve diálogo livre nem responde dúvidas. Quando conectado ao Smith, o Attendance Agent continua livre para conversar, explicar, raciocinar e adaptar tom; a macro state é um **trilho de segurança**, não um script de chatbot.

## 9. Como esta camada será usada pelo Smith sem virar motor paralelo
- **Next API/runtime** = ferramenta determinística de controle de estado/gates/segurança.
- **Smith Attendance Agent** = inteligência conversacional e raciocínio (chama estas APIs como tools via Context Package).
- **RAG** = conhecimento curado (explicar regra/condição), entra **depois**, sem controlar o fluxo.
- **InfoCap/Vault** = fonte primária de apólice (read-only), entra **depois** no `policy_lookup`.
- **Corredor** = workflow estruturado de slots.
- **Macro state** = trilho de segurança/estado, não script burro.

## 10. CPF é pedido no momento certo? High risk tem precedência?
- **CPF no momento certo:** só depois do gate de segurança (risco) e do problema descrito; nunca em saudação/pedido vago; nunca duplicado; sempre com motivo.
- **High risk precede tudo:** mensagem de risco alto → safety/handoff (42B5E) **antes** de qualquer identidade/apólice; não pede CPF, não faz lookup.

## 11. Comportamentos anteriores preservados (e a mudança intencional)
Preservados: greeting-only, unclear, high-risk handoff, pós-handoff 409, Core/Auxiliares/RAG. **Mudança intencional (alinhada ao pedido do Founder):** após a resposta de risco **baixo**, o próximo passo agora é o **gate de identidade (CPF)** em vez de `affected_area`. O `step` em caso novo continua perguntando risco primeiro (gate retorna `null` enquanto o risco não está resolvido). Os slots do corredor (`affected_area`, `electrical_issue_type`, …) voltarão a ser coletados quando o gate de apólice for resolvido (batch de InfoCap lookup).

## 12. Side effects que NÃO acontecem
Sem InfoCap real; sem confirmar cobertura; sem WhatsApp/envio externo; sem `dispatch_packet`/`approval_request`; sem portal; sem alteração de SQL/schema/migration, backend Python, RAG, prompts/agentes, UI, Vault, Auxiliares, Core. Logs sem CPF completo/telefone/PII.

## 13. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema · backend Python · RAG · prompts/agentes · UI · WhatsApp · InfoCap real · dispatch/approval | ✅ nenhum |
| Core chat / Auxiliares | ✅ inalterado |
| CPF/secret/PII no diff/logs | ✅ nenhum |

## 14. Testes manuais (após deploy Web)
- **A — saudação não pede CPF:** `reply {message:'Oi'}` → `Olá! Em que posso te ajudar?`, macro `needs_intent`-equivalente, sem CPF, sem policy_check.
- **B — vago não pede CPF:** `reply {message:'Preciso de ajuda'}` → pede detalhe curto, sem CPF, sem corredor final.
- **C — problema + low risk → identity gate:** criar caso → `reply 'Estou sem luz só na cozinha'` (pergunta risco) → `reply 'Não, sem cheiro de queimado nem faísca.'` → próximo passo **pede CPF** (`selected_slot=identity_document`, `last_agent_action=ask:identity_document`, `macro_state=identity_required`), sem dispatch, sem confirmar cobertura.
- **D — CPF preenche identity e avança:** `reply {message:'123.456.789-09'}` → grava `insured_document_ref` (log mascarado), `macro_state=policy_lookup_required`, `status=policy_check`, `next_step` indica consultar apólice em fonte confiável, sem cobertura/dispatch.
- **E — high risk:** `reply 'Tem cheiro de queimado e saiu uma faísca'` → handoff alto risco (42B5E), sem CPF, sem lookup.
- **F — Core regression:** Core interno; Auxiliares (Resumo + Follow-up); RAG NEVOA-791.

## 15. Próximos batches
- **42I0/42I1** — InfoCap Connector (read-only) + Policy Lookup: implementar o lookup que o `policy_lookup_required` aguarda; ao verificar, retomar os slots do corredor.
- **42B6** — Dispatch Packet + WhatsApp dry-run/HITL (somente após apólice verificada/handoff).
- Refino do macro: `resume_existing`, decisão operacional, seleção de subcorredor multi-ramo.
