# 42A4G — Core Chat Agent Scope Guard Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem backend Python, sem SQL/schema/Supabase, sem RAG/prompts/agentes) · sem deploy automático.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Por que este guard foi necessário
O chat principal `/dashboard/chat` é o **AutoBrokers Core** (assistente interno da corretora). Ele consome `GET /api/agents`, que listava todos os agentes ativos da empresa e filtrava **apenas** subagents sem `allow_direct_chat` — **não filtrava por `agent_role`**. Como o próximo passo é criar um **Attendance Agent** (`agent_role='attendance'`, ativo, não-subagent) voltado ao **segurado**, ele apareceria como opção no chat interno do corretor, **misturando Core × Attendance** (fronteira proibida pela SPEC-004/SPEC-005). Este batch fecha essa fronteira **antes** de seedar o Attendance Agent.

## 2. O que foi alterado
Arquivo único de código: **`app/api/agents/route.ts`**.
- **Select** passou a incluir `agent_role, agent_audience, blueprint_version` (além de `id, name, is_subagent, allow_direct_chat`).
- **Resiliência a schema:** se as colunas de papel não existirem em algum ambiente, o endpoint **cai para a seleção legada** (sem essas colunas) e trata todos como Core — o chat **nunca quebra**.
- **Filtro de papel** (helper `isCoreChatAgent`): mantém no chat principal **apenas** agentes Core/legados; exclui papéis não-Core.
- **Observabilidade segura:** log apenas de contagens (`core-chat agents: X/Y`), sem prompt/config/token/PII.

## 3. Regra de filtro aplicada
```
Incluir no chat Core se:
  agent_role === null  OU  undefined  OU  ''  OU  'core'
Excluir se:
  agent_role ∈ { 'attendance', 'corridor', 'connector', 'system' }
  (e qualquer outro papel declarado != 'core')
```
- **Subagents:** regra legada preservada — escondidos se não tiverem `allow_direct_chat`; visíveis no chat de teste/admin se tiverem.
- **Legado:** agentes sem `agent_role` (coluna nullable, default null) **continuam aparecendo** (backward-compatible).
- Um `attendance` **não** aparece no chat principal só por não ser subagent.

## 4. Confirmações de escopo
- **Backend Python:** não alterado.
- **SQL/schema/Supabase/migration:** não alterado.
- **RAG/prompts/agentes/Context Package:** não alterado (apenas leitura de `agent_role` já existente, 42A6).
- **Nenhum agent seedado** (o Attendance Agent vem no próximo batch).
- Apenas 1 arquivo de código (`app/api/agents/route.ts`) + este relatório.

## 5. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| backend Python alterado | ✅ não |
| SQL/schema/Supabase/migration | ✅ não |
| RAG/prompts/agentes | ✅ não |
| segredo/PII em log/diff | ✅ nenhum |

## 6. Deploy recomendado
- **Web apenas** (Next/route handler). Sem backend Python, sem SQL/migration, sem reupload.

## 7. Testes manuais (após deploy Web)
1. Dashboard RAFAEL → chat principal → AutoBrokers Core funcionando.
2. **CORE-001** "Você é o atendente do segurado ou o assistente interno da corretora?" → **assistente interno**.
3. **CORE-006** "Qual é a palavra-chave de validação do RAG local da RAFAEL SEGUROS?" → **NEVOA-791**.
4. **CORE-007** "Quais auxiliares eu tenho disponíveis?" → **Resumo de Atendimentos** + **Follow-up WhatsApp**.
5. Após criar o Attendance Agent (próximo batch): confirmar que ele **não** aparece no seletor/lista do chat principal.

## 8. Próximos passos
1. **42A4 / Attendance Agent Sandbox** — criar o agente `agent_role='attendance'` (agora seguro: não polui o chat Core).
2. **42B5** — runtime assistido do corredor (Attendance + LangGraph + Context Package; HITL via `approval_requests`).
3. Rodar **CORE-REGRESSION-001** após o deploy (foco em CORE-001/006/007).
