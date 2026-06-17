# 42R0 — Attendance Knowledge/RAG Safe Context Layer for Intelligent Q&A Report

> **Status:** concluído · testes offline **279 verdes** (22 knowledge + 37 policy-qa + 39 intent + 32 selection + 44 whatsapp-inbound + 35 dispatch + 33 coverage + 37 evidence) · `py_compile` OK · `typecheck` EXIT=0 · build verde · **sem schema**, **sem RAG paralelo**, **RAG/knowledge não confirma cobertura**, **sem PII**, **goldens preservados**. Também corrigiu 2 bugs de qualidade do 42Q0.
> **Data:** 2026-06-17 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 0. Análise do teste do 42Q0 (do Founder)
O Q&A **passou funcionalmente**: cobertura não confirmada, status ativo, previsão sem protocolo, slot retomado sem repetir CPF/apólice, case final correto (`verified_by_connector`, `electrician`, dispatch `incomplete`). Mas o teste expôs **2 bugs de qualidade** (verbosidade/duplicação), que corrigi aqui:
- **Q&A com LLM ligado duplicava a pergunta** ("…Em qual área da casa… Para eu continuar: Perfeito. Em qual área da casa…"). Causa: o LLM já re-perguntava e meu código anexava "Para eu continuar: [slot]". **Fix:** só anexa a retomada se o LLM não terminou em pergunta / não repetiu o slot.
- **Mensagem de seleção verbosa** ("Vou seguir com os dados…" + reasoning do step "Vou continuar coletando…"). **Fix:** `buildPolicySelectedMessage` enxuto (só "Perfeito, selecionei a apólice com final ****99. Ela está vigente."); a continuação vem do step.

## 1. Inventário RAG/Knowledge do Smith
| Componente | Existe? | Uso no atendimento |
|---|---|---|
| `backend/app/services/qdrant_service.py`, `search_service.py`, `rerank_service.py`, `knowledge_scope.py`, `ingestion_service.py`, `memory_service.py`, `langchain_service.py` | ✅ (infra de RAG do Core) | **não acoplado ao atendimento** |
| `backend/app/api/attendance_agent_reply.py` | ✅ | **intencionalmente RAG-free** (stateless, 1 chamada LLM) — por segurança |
| Base de conhecimento de atendimento ingerida (chunks/documents) | ❌ | **não há conteúdo de atendimento ingerido ainda** |

**Reusado:** o caminho LLM existente (`attendance_agent_reply` + `runtime-llm-fallback`) — estendido para receber `knowledge`. **Não recriei** motor RAG. **Lacuna:** ingestão real de base de conhecimento de atendimento (Qdrant) → **42R1**.

## 2. Decisão de arquitetura
Como **não há KB de atendimento ingerida**, entreguei: (a) **curadoria interna segura** (conceitos gerais) que dá inteligência imediata; (b) **interface de recuperação future-ready** que, quando `ATTENDANCE_KNOWLEDGE_URL` existir, mescla snippets do RAG do Smith. **Knowledge nunca confirma cobertura** — isso é sempre do Evidence Pack.

## 3. Arquivos alterados/criados
- `lib/attendance/attendance-knowledge.ts` (**novo**) — `buildAttendanceKnowledgeQuery`, `retrieveAttendanceKnowledge` (curadoria + future-ready RAG), `knowledgeLeadForCategory`, `knowledgeForLlm`, `safeKnowledgeSummary` + base curada.
- `lib/attendance/policy-qa.ts` (**alterado**) — `PolicyQAContext.knowledge` + `buildPolicyQAContext(opts.knowledge)`.
- `app/api/attendance/cases/[caseId]/runtime/reply/route.ts` (**alterado**) — recupera knowledge, lidera a resposta com conceito geral (categorias conceituais), passa knowledge ao LLM, **de-dup da retomada**.
- `lib/attendance/whatsapp-policy-selection.ts` (**alterado**) — `buildPolicySelectedMessage` enxuto.
- `lib/attendance/runtime-llm-fallback.ts` (**alterado**) — contexto/assinatura aceitam `knowledge`.
- `backend/app/api/attendance_agent_reply.py` (**alterado**) — `AgentReplyContext.knowledge` + prompt ("conceitos GERAIS; NÃO confirma cobertura").
- `scripts/attendance-knowledge.test.mjs` (**novo**) + `package.json` (`test:knowledge`).
- `docs/canon/design/2026-06-claude-design/42R0-...md` (este).

## 4. Como o knowledge_context entra
`runtime/reply` (Q&A): classifica a pergunta → `retrieveAttendanceKnowledge` (curadoria por categoria/corredor) → injeta snippets no `PolicyQAContext.knowledge` → para categorias **conceituais** (cobertura/assistência/clarificação/processo) **lidera** a resposta com um conceito geral (`knowledgeLeadForCategory`) + a resposta determinística segura. Para **status/previsão/frustração**: **sem** knowledge lead (seguem evidência/regra). Se `ATTENDANCE_LLM_FALLBACK_ENABLED=true`, os conceitos vão também ao LLM (categorias de baixo risco). Como o **bridge WhatsApp chama o reply in-process**, vale igual no WhatsApp.

## 5. Por que NÃO decide cobertura
- O lead é sempre **conceito geral** ("Em geral, a assistência residencial pode incluir eletricista, dependendo do produto…").
- A parte operacional vem **sempre** do determinístico baseado no Evidence Pack ("…no seu caso, o documento não trouxe os itens… vou deixar validar antes de acionar").
- Cobertura/previsão **nunca** são reescritas por LLM. Teste [4] garante: conceito geral + limite + **não afirma** cobertura específica.

## 6. Exemplos
- **"o que é assistência residencial?"** → *"Em geral, a assistência residencial pode incluir serviços emergenciais como eletricista, dependendo do produto contratado. …"*
- **"cobre eletricista?" (não confirmada)** → *"Em geral, a assistência elétrica cobre reparos emergenciais, dentro dos limites e condições da apólice. Localizei uma apólice Allianz Residencial vigente na InfoCap, mas o documento não trouxe os itens de cobertura detalhados… vou deixar essa cobertura validada pela equipe antes de qualquer acionamento. Para eu continuar: [slot]."*
- **"qual a diferença entre sinistro e assistência?"** (intent shift) → conceito de assistência x sinistro.

## 7. Fallback sem RAG
Sem `ATTENDANCE_KNOWLEDGE_URL`, usa **curadoria interna** (warning `rag_not_configured_using_builtin`). Sem snippet relevante (ex.: status), `unavailable_reason='no_relevant_knowledge'` e o Q&A segue **determinístico** sem travar. `diagnostics.runtime.policy_qa.knowledge` registra ids/scopes/provenance (sem dump de conteúdo, sem PII).

## 8. Flags/envs
- `ATTENDANCE_KNOWLEDGE_URL` (opcional, future) — quando existir um endpoint de RAG de atendimento, o retrieve mescla snippets reais. Hoje ausente → curadoria.
- `ATTENDANCE_LLM_FALLBACK_ENABLED` (existente) — knowledge vai ao LLM só nas categorias de baixo risco.

## 9. Testes que rodei (offline)
- `node scripts/attendance-knowledge.test.mjs` → **22/22**: query sem PII; recuperação por categoria; lead só conceitual; **cobertura não confirmada mesmo com knowledge**; fallback determinístico; summary sem dump.
- `policy-qa` **37**, intent **39**, selection **32**, whatsapp-inbound **44**, dispatch **35**, coverage **33**, evidence **37** = **279/279**.
- `python -m py_compile` (attendance_agent_reply) OK · `npx tsc --noEmit` EXIT=0 · `npm run build` verde. Goldens preservados (Q&A conservador; slot answers intactos).

## 10. Reteste (console, logado)
```js
const id = '<caseId em coleta, apólice já selecionada>';
const r = async (m) => (await (await fetch(`/api/attendance/cases/${id}/runtime/reply`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m,source:'dashboard'})})).json()).next_step.question;
console.log(await r('o que é assistência residencial?'));   // conceito geral + retomada
console.log(await r('cobre eletricista mesmo?'));            // conceito geral + NÃO confirma + retomada (sem duplicar)
console.log(await r('minha apólice está ativa?'));           // status por evidência (sem knowledge)
```
**Esperado:** perguntas conceituais ganham profundidade (conceito geral) **sem** confirmar cobertura; status segue evidência; **sem pergunta duplicada**.

## 11. Critério de pronto
| Critério | Status |
|---|---|
| usa conhecimento seguro em perguntas gerais | ✅ (curadoria) |
| não confirma cobertura sem evidence | ✅ (teste [4]) |
| Q&A funciona sem RAG | ✅ (fallback) |
| sem PII | ✅ (query/context/summary) |
| Smith/RAG reutilizado (não paralelo) | ✅ (LLM path estendido; RAG real = future-ready) |
| goldens continuam verdes | ✅ |

## 12. Gaps / próximos
- **42R1 — Ingestão real de KB de atendimento** (Qdrant): popular conhecimento por seguradora/corredor/corretora e ligar `ATTENDANCE_KNOWLEDGE_URL` ao RAG do Smith (provenance/redaction). A interface já está pronta.
- **42M0 — Media Evidence Pipeline:** reutilizar áudio/visão/documentos do Smith (auditar antes; sem motor paralelo).
- **42W2 — Webhook real Z-API** (pausado por pagamento).
- **42X0 — Action Engine externo dry-run.**

## 13. Checks
| Check | Resultado |
|---|---|
| `node scripts/attendance-knowledge.test.mjs` | ✅ 22/22 |
| policy-qa/intent/selection/whatsapp-inbound/dispatch/coverage/evidence | ✅ 37/39/32/44/35/33/37 |
| `python -m py_compile` | ✅ OK |
| `npx tsc --noEmit` | ✅ EXIT=0 |
| `npm run build` | ✅ verde |
| `git diff --check` | ✅ limpo |
| schema · RAG paralelo · RAG confirma cobertura · envio externo · PII · quebra goldens/dashboard | ✅ nenhum |
