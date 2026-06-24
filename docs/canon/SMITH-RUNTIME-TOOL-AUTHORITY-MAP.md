# SMITH-RUNTIME-TOOL-AUTHORITY-MAP

> Status: **R0 DOCUMENTAL**
> Data: 2026-06-24
> Objetivo: mapear a autoridade real de tools do Smith e preparar a Fase R2.

## 1. Regra canonica

O Smith/LangGraph e o runtime principal do Chat Principal. O Capability Registry deve se tornar a unica autoridade de disponibilidade/autorizacao de ferramentas. O Smith executa; o Registry governa; Vault/OAuth guardam conexoes e segredos.

`tools_config`, HTTP Tools e MCP podem continuar existindo como configuracao/execucao, mas nao como autoridade concorrente.

## 2. Prompt Efetivo futuro

O Portal Admin deve exibir, em modo diagnostico, um Prompt Efetivo redigido e somente leitura.

Contrato:

```text
prompt_effective_id
company_id_hash
agent_id
agent_role
platform_policy_version
global_blueprint_version
tenant_personalization_version
runtime_context_summary
bound_tools
active_capabilities
rag_context_summary
memory_context_summary
source_order
conflict_warnings
rendered_prompt_redacted
created_at
```

Blocos exibidos:

1. **Politica imutavel da plataforma** - somente leitura.
2. **Blueprint Global AutoBrokers** - versionado e publicado pelo Portal Admin.
3. **Personalizacao da corretora** - editavel dentro de limites seguros.
4. **Contexto de execucao** - caso, conversa, memoria, RAG, tools, capabilities.
5. **Prompt Efetivo** - somente leitura, redigido, auditavel.

Proibido:

- transformar politica imutavel em campo editavel do tenant;
- ter prompt oculto concorrente sem diagnostico;
- liberar ferramenta por texto de prompt.

## 3. Caminho real do Chat Principal

```text
app/dashboard/chat/page.tsx
-> /api/chat/stream
-> app/api/chat/stream/route.ts
-> backend /chat/stream
-> backend/app/api/chat.py
-> LangChainService / graph.py
-> tools vinculadas
-> resposta streaming
```

O chat textual atual nao usa `/api/n8n`.

## 4. N8N legacy

Classificacao:

```text
/api/n8n + lib/n8nClient
= transport legacy / compatibilidade
!= runtime principal
!= fonte de verdade
!= caminho da leitura de apolice
```

Evidencia:

- `app/api/n8n/route.ts` decide entre `use_langchain` e `webhook_url`.
- `lib/n8nClient.ts` ainda envia texto/voz para `/api/n8n`.
- `app/dashboard/chat/page.tsx` envia texto para `/api/chat/stream`, mas voz ainda chama `sendVoiceToN8N`.

Plano:

- congelar para novas funcionalidades;
- manter ate auditoria de voz/compatibilidade;
- nao remover nesta fase;
- nao usar para InfoCap, tools, RAG ou Prompt Efetivo.

## 5. Matriz de autoridade de tools

| Ferramenta | Tela Portal Admin/Dashboard | Persistencia atual | Rota de salvamento | Runtime que le | Capability correspondente | Status atual | Duplicidade/risco | Plano R2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Busca Web | Agent config / Capabilities | `agents.allow_web_search`, entitlements | `/api/admin/companies/[companyId]/capabilities` e rotas de agents | `graph.py` via `resolve_active_capabilities` | `platform.web.search` | Parcial funcional | legado `allow_web_search` pode divergir de capability | Registry manda; legado vira materializacao/diagnostico |
| Solicitar Humano | AgentConfigModal | `agents.tools_config.human_handoff` | rotas de agents | `graph.py` le `tools_config` | A definir/homologar | Funcional fora do Registry | autorizacao concorrente | migrar para capability/gate, manter config visual |
| CSV | AgentConfigModal | `agents.tools_config.csv_analytics` | rotas de agents | `graph.py` le `tools_config` | A definir/homologar | Funcional fora do Registry | autorizacao concorrente | declarar capability ou congelar se legado |
| Visao Computacional | Chat/anexos/config de agente | campos de agente e payload de chat | rotas de chat/agents | `chat.py` / LangChain vision | `platform.document.extract` ou capability especifica futura | Parcial | pode ser confundida com leitura de apolice | nao usar para InfoCap; governar por capability |
| RAG / Knowledge | Knowledge UI | `documents`, MinIO, Qdrant | `backend/app/api/documents.py` | `KnowledgeBaseTool` / `SearchService` | `knowledge.tenant.search`, `knowledge.global.search` | Funcional parcial | tool pode existir mesmo sem diagnostico claro | exibir no Prompt Efetivo e governar por capability |
| InfoCap | Capabilities / Conectores | `tenant_connections`, Vault, entitlements | rotas de connector/capability | `InfocapPolicyLookupTool` | `operational.infocap.policy_lookup.read` | Funcional com adapter falho | parser/id/envelope incorretos | R1 corrige adapter; R2 mostra autoridade |
| Documentos | Dashboard/Knowledge/Admin | `documents`, MinIO, Qdrant | `backend/app/api/documents.py` | KnowledgeBaseTool | `platform.document.extract`, `knowledge.*` | Pronto em partes | Docling nao entra automaticamente na ingestao | R3 vincula evidencia documental por `policy_ref` |
| HTTP Tools | AgentConfigModal | `agent_http_tools` | `app/api/agents/tools/route.ts` | `HttpToolRouter` em `graph.py` | Deve ser capability homologada | Parcial | pode virar conector paralelo | Registry autoriza; HTTP executa |
| MCP | MCP config/admin | tabelas MCP por agente | backend MCP routes | MCP gateway em `graph.py` | capability por provider | Parcial funcional | pode ser tratado como login/config livre | OAuth/Vault conecta; Registry autoriza; MCP executa |
| Google Drive | Conectores/MCP futuro | tenant connection/OAuth/MCP | rotas de conectores/MCP | nao comprovado como Core produtivo | `tenant.google_drive.read` | Nao produtivo no Core | fonte documental fora do evidence contract | manter conectado, nao usar produtivo ate R2/R3 |
| Notion | Conectores/MCP futuro | tenant connection/OAuth/API/MCP | rotas de conectores/MCP | nao comprovado como Core produtivo | `tenant.notion.read_write` | Nao produtivo no Core | knowledge paralelo informal | manter conectado, nao usar produtivo ate R2/R3 |
| Voz | Chat page | mensagens/audio/storage | `sendVoiceToN8N` -> `/api/n8n` | N8N legacy/LangChain/webhook | futura capability de voz/canal | Legacy | passa fora do caminho textual | auditar antes de migrar |
| N8N legacy | Nenhuma como runtime novo | `companies.use_langchain`, `webhook_url` | company/admin | `/api/n8n` route | nenhuma | Legacy congelado | bifurcacao transport | nao receber features novas |
| Portal Browser | Admin Portal Browser | registry/session refs/portal maps | rotas Portal Browser | Attendance/portal engine | `operational.portal.*` | Fundacao existente | risco alto se virar browser paralelo | usar somente capabilities + HITL |

## 6. Camadas atuais de prompt

| Camada | Local | Tipo | Risco |
| --- | --- | --- | --- |
| Prompt base Core | `backend/app/core/prompts.py` | politica/plataforma + blueprint base | pode ser obscurecido por instrucoes locais |
| Instrucoes do agente/tenant | `graph.py`, config do agente | personalizacao local | pode conflitar sem diagnostico |
| Contexto de execucao | conversa, data, RAG, memoria, anexos | runtime context | pode adicionar fatos sem proveniencia clara |
| Descricoes de tools | tool classes, HTTP, MCP | prompt operacional | pode virar prompt oculto |
| N8N/webhook legacy | `/api/n8n` quando usado | runtime/transport concorrente | nao deve governar Chat Principal |

## 7. Plano de migracao R2

1. Inventariar toda tool que entra em `graph.py`.
2. Associar cada tool a uma capability ou marcar como legado/congelado.
3. Fazer `tools_config` virar comportamento visual/local.
4. Impedir tool produtiva sem capability ativa, entitlement e conexao quando exigida.
5. Exibir no Portal Admin o Prompt Efetivo redigido.
6. Exibir divergencias: "switch ligado, runtime nao le", "conexao existe, capability desligada", "capability ativa, conexao ausente".
7. Congelar N8N como transport legacy.

## 8. Criterios de aceite R2

- Nenhuma tool produtiva e autorizada por `tools_config` isolado.
- HTTP Tools e MCP nao substituem Vault/OAuth.
- InfoCap so entra por `operational.infocap.policy_lookup.read`.
- Prompt Efetivo mostra tools realmente vinculadas.
- Portal Admin mostra diagnostico de divergencia.
- Chat textual continua em `/api/chat/stream`.
- N8N legacy nao recebe nova funcionalidade.
