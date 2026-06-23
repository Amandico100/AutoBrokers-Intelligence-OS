# C-FIX-1 — Relatório de execução ("Runtime e conexões reais")

> Data: 2026-06-23. Escopo: Batch C-FIX-1 do [PHASE-C-FIX-PLAN](PHASE-C-FIX-PLAN.md). Sem Batch 2, sem RAG, sem Z-API/Allianz.
> Princípio cumprido: reusar Smith/Vault/MCP/Registry; nenhuma estrutura paralela; nada de estado de UI que mente sobre o runtime.

## Causa-raiz (o que estava quebrado)
1. **InfoCap no chat** devolvia "precisa ser assíncrona": o executor de tools (`nodes.py`) rodava TODAS as tools via `tool._run` (síncrono); só `delegate_to_subagent` usava `_arun`. O InfoCap é async → caía no stub `_run`.
2. **Runtime ignorava o Registry**: `graph.py` anexava InfoCap/Control Plane só pelo papel (`core`/vazio), sem ler entitlements/conexão. Cockpit dizia uma coisa, runtime fazia outra. Papel vazio virava "Core".
3. **Busca web**: provável `TAVILY_API_KEY` no serviço errado (web/Next) — o chat roda no backend (Python). E o cockpit mostrava "ligada" por flag, não por saúde real.
4. **InfoCap duplicada** na Resulta (2 conexões) sem regra de unicidade.
5. **Conectores burocráticos**: termos em inglês, ator único por permissão, aprovação para conectar, InfoCap sem campos de login/senha.

## Arquivos alterados / criados
**Backend (runtime):**
- `backend/app/agents/capability_resolver.py` (NOVO) — resolve capabilities ATIVAS pelo banco (Registry) + papel + conexão + saúde de provider. Papel vazio/ inválido = nada privilegiado. Fail-closed.
- `backend/app/agents/graph.py` — web search, control_plane e infocap anexados SÓ quando o resolver diz `active`. Remove o gate por flag/role solto.
- `backend/app/agents/nodes.py` — executor roteia `infocap_policy_lookup` para `_arun` (fix do bug async).
- `backend/app/api/infocap_connector.py` — base_url GLOBAL (fallback `INFOCAP_BASE_URL`) já em produção; + endpoint `GET /health/providers` (master/internal, sem segredo) para o cockpit refletir a verdade.
- `backend/app/core/config.py` — `INFOCAP_BASE_URL` (já existente desde o slice 3).
- `backend/tests/test_capability_resolver.py` (NOVO) — 11/11 offline.

**Frontend (conectores/cockpit):**
- `components/vault/ConfigureInfocapModal.tsx` (NOVO) — conectar InfoCap com **login/senha** (cifra no Vault; sem aprovação para conectar).
- `components/vault/PermissionGrantPanel.tsx` — **multi-ator** (Chat Principal + Atendimento + Auxiliares de uma vez), **linguagem humana** (Consultar informações / Preparar mensagem / Testar conexão), **Remover acesso** (revoga), aprovação só para ações sensíveis.
- `components/vault/labels.ts` — `actionLabel/actionHelp/actionIsSensitive/subjectLabel` (humanização para TODOS os conectores).
- `app/dashboard/personalizacao/conectores/page.tsx` — botão "Conectar (login e senha)" para InfoCap + modal; "aprovação de teste" restrita ao WhatsApp.
- `app/api/vault/connections/[connectionId]/permissions/route.ts` — `DELETE` (revogar, preserva histórico + auditoria).
- `lib/vault/api.ts` — `deletePermission`.
- `app/api/admin/companies/[companyId]/capabilities/route.ts` — busca `GET /health/providers` do backend; expõe `web_search_operational` real.
- `app/admin/companies/[companyId]/agents/page.tsx` — badge de busca web = saúde real (operacional / sem TAVILY / verificar).

**Dados (produção, via MCP, seguro/reversível):**
- InfoCap duplicada da Resulta (`InfoCap RESULTA`, draft, sem segredo) **arquivada**; canônica `InfoCap — Resulta Seguros` preservada (tem permissões/aprovações). Resulta agora tem **1** conexão InfoCap ativa.

**Migrations (runbooks — você aplica):**
- `SPEC-014-03-connection-singleton.sql` — índice único: 1 conexão não-arquivada por corretora+template (evita duplicidade). APPLY/VERIFY/ROLLBACK + pré-check.

## Estado antes → depois
| Item | Antes | Depois |
|---|---|---|
| InfoCap no chat | erro "assíncrona" | executa lookup real (após credencial) |
| Runtime x Registry | divergentes | runtime governado pelo Registry (fonte única) |
| Papel vazio | herdava Core | bloqueado |
| Busca web | flag mentirosa | governada + saúde real no cockpit |
| InfoCap Resulta | 2 conexões | 1 canônica (dup arquivada) + regra singleton (runbook) |
| Conectar InfoCap | sem campos | modal login/senha funcional |
| Permissões | inglês, 1 ator, sem remover | humano, multi-ator, revogável |
| Aprovação p/ conectar | obrigatória | removida (só ação sensível) |

## Testes
- `test_capability_resolver.py` 11/11; `test_model_policy.py` 10/10; `capabilities.test.mjs` 21/21; `agent-health.test.mjs` 10/10; tsc=0; build verde. py_compile OK em todo backend alterado.
- Não há como testar o runtime LangGraph offline (deps) — por isso o resolver tem teste puro e o roteiro de aceite manual abaixo.

## Limitações reais (honesto)
- Busca web e InfoCap no chat só ficam operacionais **após deploy** + `TAVILY_API_KEY` no **backend** + credencial InfoCap.
- Singleton só é imposto após aplicar `SPEC-014-03`.
- A galeria estilo ChatGPT completa (OAuth Drive/Notion/etc.) é o **Batch 2** — aqui só InfoCap (credencial) ficou plug-and-play.

## Suas tarefas (para validar)
1. **`TAVILY_API_KEY` no serviço BACKEND** (autobrokers-smith-api) + redeploy. *(Se estiver no serviço web, a busca não funciona.)*
2. **Deploy** do backend + frontend.
3. **Conectar InfoCap**: Dashboard Resulta → Conectores → InfoCap → "Conectar (login e senha)" → `resulta@api.com.br` + senha → Conectar. (base_url já é global.)
4. Aplicar runbook **`SPEC-014-03`** (singleton).

## Roteiro de aceite manual
1. Chat Resulta: "quais as últimas notícias do mercado de seguros?" → responde com fontes (web).
2. Chat: "minha corretora está pronta? auxiliares, conexões, saldo?" → números reais (control plane).
3. Chat (após InfoCap conectada): "consulta a apólice do CPF X" → resultado sanitizado ou "não encontrei". Antes de conectar: "InfoCap ainda não está conectada" (sem erro assíncrono).
4. Conectores → InfoCap → Permissões: marca Chat Principal + Atendimento + Auxiliares juntos; termos em português; "Remover acesso" funciona.
5. Cockpit (Admin → Empresa → Agentes → Capacidades): busca web "operacional" só com TAVILY no backend; InfoCap "conectar"→ativo após credencial.
6. Segurança: agente sem papel não recebe tools de Core; Resulta só vê InfoCap da Resulta.
