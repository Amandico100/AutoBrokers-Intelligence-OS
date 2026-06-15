# 42B7 — Attendance E2E Golden Tests Report

> **Status:** concluído · typecheck verde · script `node --check` verde · skip-run verde · `git diff --check` limpo · **só tooling/test + docs** (sem alterar runtime/SQL/schema/backend funcional/RAG/prompts/WhatsApp/InfoCap/dispatch) · sem deploy.
> **Data:** 2026-06-14 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados/alterados
- `scripts/attendance-golden-tests.mjs` (**novo**) — suíte E2E do runtime de atendimento.
- `package.json` (**alterado**) — script `test:attendance-goldens`.
- `docs/canon/design/2026-06-claude-design/42B7-attendance-e2e-golden-tests-report.md` (este).

**Nenhuma alteração de runtime funcional** (não encontrei bug crítico que exigisse correção neste batch).

## 2. Auditoria
Lidos: SPEC-004/005/006, relatórios 42B5K.1, 42B5L-BE, 42B5L-FE; rotas `runtime/{reply,step,policy-lookup}` e `cases`; libs de runtime + `runtime-llm-fallback.ts`; `backend/app/api/attendance_agent_reply.py`. Os asserts foram derivados desses contratos (shapes de resposta, macro states, `diagnostics.runtime`).

## 3. Como executar
Requer o **Web no ar** e uma **sessão autenticada** (as rotas de runtime exigem Iron Session).
```bash
BASE_URL=http://localhost:3000 \
SESSION_COOKIE="<cole o Cookie de uma sessão autenticada do navegador>" \
ATTENDANCE_LLM_FALLBACK_ENABLED=true \   # opcional, para asserts do off-topic com LLM
node scripts/attendance-golden-tests.mjs
# ou
npm run test:attendance-goldens
```
- Sem `SESSION_COOKIE` → a suíte **faz skip** (exit 0) com instruções (não quebra CI).
- `SESSION_COOKIE`: copie o cabeçalho Cookie de uma aba logada (DevTools → Network → qualquer request → Request Headers → Cookie).
- `BACKEND_URL` (opcional): health do backend.
- CPF sempre fictício `123.456.789-09`; nunca impresso (mascarado).

## 4. Testes cobertos (automatizados)
| # | Cenário | Asserts principais |
|---|---|---|
| 2 | Fluxo normal completo | problema→risco→CPF→`policy_check`→policy lookup mock (`verified*`, `policy_evidence_ready`)→`step` retoma (`collecting_slots`)→coleta slots→conclusão reconhece "apólice/evidência registrada"; **sem** `insured_document_ref` em nenhuma resposta |
| 3 | Off-topic no gate de CPF | não avança (continua `identity_document`), `status=conversation_recovery`, `diagnostics.runtime.llm_fallback` presente; com flag ON → `used/attempted` e (se used) resposta menciona van/de/do/origem; com flag OFF → `used=false` determinístico |
| 4 | Clarificação ("por que o CPF?") | mantém `identity_document`, não avança p/ policy lookup, gera resposta |
| 5 | CPF indisponível | mantém `identity_document`, `intake.kind=unavailable_data` |
| 6 | Frustração (após risco) | `conversation_recovery`, inferiu `affected_area=cozinha` e `electrical_issue_type` nos slots |
| 7 | High risk | `status=handoff`, `priority/risk_level=high`, `handoff_required=true`, **não** pede CPF, **não** usa LLM; `step` pós-handoff → **409** |
| — | Safe response | toda resposta de runtime checada: sem `insured_document_ref` e sem dígitos do CPF |

**Core regression (manual — não automatizado):** o Core exige chat/backend/LLM e não é runtime determinístico; validar manualmente no chat principal:
- "Você é atendente do segurado ou assistente interno da corretora?" → **assistente interno**.
- "Quais auxiliares eu tenho?" → **Resumo de Atendimentos** + **Follow-up WhatsApp**.
- "Qual a palavra-chave do RAG?" → **NEVOA-791**.

## 5. Awareness de endpoint (importante)
O backend de fallback é **`POST /attendance/agent-reply`** (SEM o prefixo `/api`). O Web **não** expõe `/api/attendance/agent-reply`. O `runtime-llm-fallback.ts` chama `${BACKEND}/attendance/agent-reply` (server-side). Documentado no cabeçalho do script.

## 6. Garantias de segurança no teste
- Nunca usa CPF real; nunca imprime CPF (mascarado por `mask()`).
- `noCpfExposed()` falha o teste se qualquer resposta de runtime contiver `insured_document_ref` ou os dígitos do CPF.
- Não depende de WhatsApp/InfoCap real; policy lookup é o mock `allianz_residential_electrician_covered`.

## 7. Checks
| Check | Resultado |
|---|---|
| `node --check scripts/attendance-golden-tests.mjs` | ✅ OK |
| `node scripts/attendance-golden-tests.mjs` (sem cookie) | ✅ skip limpo (exit 0) |
| `npm run typecheck` | ✅ OK |
| `npm run build` | ⏭️ não reexecutado — nenhum arquivo `app/`/`lib/`/`backend/` alterado (só `scripts/`, `package.json` e `.md`); estado idêntico ao último build verde |
| `git diff --check` | ✅ limpo |
| SQL/schema/backend funcional/RAG/prompts/WhatsApp/InfoCap/dispatch | ✅ nenhum |

## 8. Limites conhecidos
- Requer Web no ar + `SESSION_COOKIE` (as rotas exigem auth); sem isso, skip. Não há, hoje, login programático no script (proposital — evita lidar com credenciais).
- Core regression é manual (Core depende de chat/LLM, fora do runtime determinístico).
- Off-topic com LLM só valida `used=true`/menção a "van" quando a flag está ON **e** o backend `/attendance/agent-reply` está deployado; caso contrário valida o caminho determinístico.
- A suíte assume os seeds globais do corredor Allianz/Eletricista (42B3) presentes na empresa da sessão.

## 9. Próximo recomendado
**42I2 — InfoCap Connector Read-only (via Vault)** (troca o policy lookup mock por consulta real mantendo contrato/simulador/goldens) ou **42B6 — Dispatch Packet dry-run/HITL**. Recomendo rodar esta suíte (com cookie) antes e depois de cada um para congelar o comportamento.
