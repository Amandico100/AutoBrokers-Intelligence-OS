# BATCH 35A - Inventario do Smith Runtime para AutoBrokers

Data: 2026-06-05  
Escopo: inventario, diagnostico e plano.  
Repositorio oficial: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-Intelligence-OS`  
ADR base: `docs/adr/ADR-001-runtime.md`

## 1. Resumo executivo

O runtime Smith V6.2 ja contem uma base operacional forte para o AutoBrokers Intelligence OS: Next.js, FastAPI, Supabase, Qdrant, MinIO, Redis, chat streaming, agents, subagents, delegations, HTTP tools, MCP, RAG, documentos, logs, custos, billing, widget e admin multi-tenant.

A conclusao tecnica deste inventario e que o Smith deve continuar como motor runtime principal, mas ainda precisa virar produto AutoBrokers por camadas controladas. O principal trabalho agora nao e importar legado: e renomear a identidade visivel, estabilizar a home AutoBrokers, organizar o modelo de Auxiliares sobre agents/subagents/delegations, validar RAG minimo e mapear atendimento/canais com cuidado.

Prontidao estimada por area:

| Area | Prontidao | Leitura |
| --- | ---: | --- |
| Admin Global como base | 68/100 | Ja existe gestao SaaS, empresas, usuarios, FinOps, logs e configs. Precisa virar Admin Global AutoBrokers. |
| Tenant dashboard como base | 55/100 | Existe chat, historico e configuracoes. Falta home operacional AutoBrokers e paginas de produto. |
| AutoBrokers/chat central | 72/100 | Chat ja funciona com agente, credito e stream. Falta prompt/identidade AutoBrokers e cards operacionais. |
| Agents/subagents/delegations | 74/100 | Base tecnica forte. Falta produto "Auxiliares", galeria, ativacao por corretora e historico de execucao. |
| RAG/documentos | 70/100 | Upload, Qdrant, MinIO, ingestion e documentos existem. Falta smoke controlado e curadoria AutoBrokers. |
| Logs/custos | 72/100 | Logs, token usage, creditos e planos existem. Falta consolidar worker/billing e dashboards finais. |
| Atendimento externo | 42/100 | Existem conversas/handoff como base, mas faltam fila, casos, segurados, seguradoras, corredores e canais reais. |
| Auxiliares | 58/100 | Motor existe, produto ainda nao. Precisa data model e UI de galeria/instalacao/execucoes. |

Nao foi encontrada necessidade de copiar pastas antigas. O Agent OS V2 deve entrar depois como fonte curada de pacotes, politicas, prompts, guardrails, corredores e evals, nunca como import bruto.

## 2. Decisoes do ADR consideradas

Decisoes obrigatorias extraidas de `ADR-001-runtime.md` e aplicadas neste inventario:

| Decisao | Impacto neste inventario |
| --- | --- |
| Runtime principal sera Smith V6.2 | O inventario parte do que ja existe no Smith e evita sugerir outro motor runtime. |
| Produto final se chama AutoBrokers.ai | Todo uso visivel de Smith deve virar branding tecnico temporario ou ser removido. |
| Agente central se chama AutoBrokers | `/dashboard/chat` deve evoluir para experiencia AutoBrokers, sem nome legado e sem Smith visivel. |
| AutoBrokers nao e personalizavel | Nome fixo no produto; prompt/modelo podem ser configurados, identidade nao. |
| Nao usar nomes legados no produto final | O bootstrap atual com "AutoBrokers Sandbox" e temporario; "Sandbox" sai antes de producao. |
| Nao existe pagina Estudos | Qualquer rota futura de conhecimento deve ser "Conhecimento", "Base de Conhecimento" ou curadoria, nao Estudos. |
| "Rotinas" viram "Auxiliares" | O produto deve falar em Auxiliares. Scheduler/execucoes sao detalhes tecnicos. |
| Auxiliares usam agents/subagents/delegations/tools/RAG/logs/custos | O menor caminho tecnico e reaproveitar o motor Smith, nao criar sistema paralelo. |
| Galeria/Marketplace primeiro | Criacao conversacional pelo AutoBrokers fica para fase posterior. |
| Conexoes por corretora, reutilizaveis | Precisa vault/connection registry por tenant para AutoBrokers, Atendimento, Auxiliares e corredores. |
| Agent OS V2 e cerebro/politica, nao runtime ativo | Conteudo V2 deve virar pacotes curados, nao copia de pastas. |
| LionClaw e referencia | Usar como inspiracao de UX, harness, permission guard e scheduler, nao como runtime. |

## 3. Estrutura do repo

Arvore resumida relevante:

```txt
AutoBrokers-Intelligence-OS/
  app/
    admin/
    api/
    dashboard/
    embed/
    landing/
    login/
    register/
    forgot-password/
    reset-password/
    pending-approval/
  backend/
    app/
      agents/
      api/
      core/
      mcp_servers/
      services/
      workers/
    supabase/
      migrations/
  components/
    admin/
    agent/
    dashboard/
    landing/
    ui/
  docling-service/
    app/
    Dockerfile
    docker-compose.yml
  docs/
    adr/
    audits/
  hooks/
  lib/
  public/
  types/
```

Observacoes:

- `app/` contem o frontend Next.js, rotas publicas, admin, tenant dashboard e API routes server-side.
- `backend/` contem o FastAPI runtime, LangGraph/agents, RAG, billing, MCP, webhook e services.
- `components/admin/` concentra grande parte do produto operacional existente.
- `docling-service/` existe como servico separado para parsing/conversao de documentos.
- `.claude/` existe como tooling local no repo, mas nao e produto runtime e deve continuar protegido por `.gitignore`.

## 4. Inventario Admin

| Rota | Arquivo principal | Smith atual | AutoBrokers futuro | Acao | Prioridade |
| --- | --- | --- | --- | --- | --- |
| `/admin` | `app/admin/page.tsx` | Dashboard administrativo Smith | Admin Global AutoBrokers | Manter e renomear textos/cards | P0 |
| `/admin/login` | `app/admin/login/page.tsx` | Login Admin Smith | Login Admin Global | Renomear branding e textos | P0 |
| `/admin/companies` | `app/admin/companies/page.tsx` | Gerenciar empresas | Corretoras/Tenants | Manter; trocar "empresa" por corretora onde fizer sentido | P0 |
| `/admin/companies/[companyId]/agents` | `app/admin/companies/[companyId]/agents/page.tsx` | Agents por empresa | Agentes e Auxiliares por corretora | Manter; separar agente principal e Auxiliares | P1 |
| `/admin/pending-users` | `app/admin/pending-users/page.tsx` | Aprovacoes pendentes | Aprovacoes de usuarios | Manter | P1 |
| `/admin/all-users` | `app/admin/all-users/page.tsx` | Todos os usuarios | Usuarios globais | Manter | P1 |
| `/admin/team` | `app/admin/team/page.tsx` | Equipe da empresa | Equipe da corretora | Manter para admin da corretora | P1 |
| `/admin/conversations` | `app/admin/conversations/page.tsx` | Conversas/admin handoff | Supervisao de atendimentos/conversas | Reposicionar em Atendimento | P1 |
| `/admin/agent` | `app/admin/agent/page.tsx` | Configurar agente | Configurar AutoBrokers/agentes | Manter, mas renomear e limitar identidade do AutoBrokers | P0 |
| `/admin/documents` | `app/admin/documents/page.tsx` | Base de conhecimento | Conhecimento/curadoria | Manter | P1 |
| `/admin/knowledge-base/sanitize` | `app/admin/knowledge-base/sanitize/page.tsx` | Sanitizacao de documentos | Curadoria tecnica/documentos limpos | Manter como P2/P3 | P2 |
| `/admin/billing` | `app/admin/billing/page.tsx` | Plano da empresa | Plano/custos da corretora | Manter | P1 |
| `/admin/costs` | `app/admin/costs/page.tsx` | Custos antigo/alternativo | Possivel duplicata de FinOps | Revisar consolidacao | P2 |
| `/admin/finops/usage` | `app/admin/finops/usage/page.tsx` | Consumo LLM | Custos IA/uso | Manter | P1 |
| `/admin/finops/pricing` | `app/admin/finops/pricing/page.tsx` | Tabela de custos | Precificacao interna | Manter para Admin Global | P1 |
| `/admin/finops/plans` | `app/admin/finops/plans/page.tsx` | Planos | Planos das corretoras | Manter | P1 |
| `/admin/logs` | `app/admin/logs/page.tsx` | Logs do sistema | Observabilidade global | Manter | P1 |
| `/admin/conversation-logs` | `app/admin/conversation-logs/page.tsx` | Logs de conversacao | Observabilidade de atendimentos | Manter | P1 |
| `/admin/integrations` | `app/admin/integrations/page.tsx` | Integracoes | Conexoes/canais/tools por corretora | Reativar/renomear depois | P2 |
| `/admin/legal-documents` | `app/admin/legal-documents/page.tsx` | Termos/politicas | Termos e politicas | Manter | P2 |
| `/admin/settings` | `app/admin/settings/page.tsx` | Configuracoes | Configuracoes Admin/tenant | Manter | P1 |

Menu Admin atual:

- Master admin: dashboard, empresas, aprovacoes, usuarios, FinOps, logs, conversas, termos, configuracoes.
- Company admin: equipe, conversas, configurar agente, base de conhecimento, meu plano, configuracoes.

Principais gaps do Admin:

- Branding visivel ainda usa Smith em varios pontos.
- Precisa diferenciar Admin Global AutoBrokers de Admin da corretora.
- Precisa criar conceito de Auxiliares no Admin: templates globais, instalacoes por corretora e execucoes.
- Precisa uma tela de Conexoes/Vault por corretora, reutilizavel por AutoBrokers, Atendimento, Auxiliares e corredores.

## 5. Inventario Tenant

| Rota | Arquivo principal | Objetivo atual | Futuro AutoBrokers | Acao | Prioridade |
| --- | --- | --- | --- | --- | --- |
| `/dashboard` | `app/dashboard/page.tsx` | Boas-vindas simples com CTA para chat | Home operacional chat-first | Substituir por AutoBrokers Home | P0 |
| `/dashboard/chat` | `app/dashboard/chat/page.tsx` | Chat tenant com agente | AutoBrokers central da corretora | Manter como base e renomear | P0 |
| `/dashboard/historico` | `app/dashboard/historico/page.tsx` | Historico de conversas | Historico do AutoBrokers/conversas | Manter, conectar a atendimento depois | P1 |
| `/dashboard/configuracoes` | `app/dashboard/configuracoes/page.tsx` | Configuracoes do usuario | Perfil/configuracoes da corretora/usuario | Expandir depois | P2 |
| `/embed/[agentId]` | `app/embed/[agentId]/page.tsx` | Widget/chat externo | Widget/canal externo futuro | Manter como base, nao ativar cedo | P2 |

O tenant atual e enxuto demais para o produto final. Ele serve como base para:

- AutoBrokers central.
- Historico inicial.
- Configuracoes basicas.
- Futuro widget/canal externo.

Nao existe ainda:

- Home com cards operacionais.
- Fila de atendimentos.
- Casos.
- Segurados.
- Seguradoras/corredores.
- Auxiliares instalados.
- Galeria de Auxiliares.
- Conhecimento do tenant como experiencia propria.
- Status de integracoes/canais.

Direcao recomendada:

1. Transformar `/dashboard/chat` em AutoBrokers.
2. Transformar `/dashboard` em AutoBrokers Home com chat central, atalhos e cards.
3. Criar novas areas de produto depois: Atendimento, Auxiliares, Conhecimento, Canais, Gestao.
4. Nao criar pagina "Estudos".
5. Nao recriar "Conversa ao vivo" antiga; atendimento externo deve ser modulo separado.

## 6. Inventario Chat/AutoBrokers

Fluxo atual do chat tenant:

```txt
/dashboard/chat
  -> carrega usuario e empresa
  -> chama /api/user/company-data
  -> chama /api/agents para agentes ativos
  -> chama /api/conversations e /api/messages
  -> envia mensagens para /api/chat/stream
  -> Next API proxy resolve URL do backend
  -> FastAPI /chat/stream
  -> valida empresa, creditos, agente e handoff
  -> monta LangGraph do agente
  -> carrega RAG/tools/memoria conforme config
  -> streama resposta
  -> persiste conversations/messages/logs/usage
```

Arquivos centrais:

| Camada | Arquivo |
| --- | --- |
| Tenant chat page | `app/dashboard/chat/page.tsx` |
| Chat proxy Next | `app/api/chat/stream/route.ts` |
| Backend chat API | `backend/app/api/chat.py` |
| LangGraph agent runtime | `backend/app/agents/graph.py` |
| Graph/cache service | `backend/app/services/langchain_service.py` |
| Billing checks | `backend/app/services/billing_core.py` |
| LLM factory | `backend/app/services/llm_factory.py` |

Por que o chat ja responde:

- O Web/API estao publicados.
- `app/api/chat/stream/route.ts` ja evita fallback silencioso para localhost.
- Existe agente ativo para a corretora sandbox.
- A empresa recebeu credito suficiente.
- Chaves LLM foram configuradas no ambiente.
- O backend consegue montar o grafo e streamar resposta.

O que ainda esta generico/temporario:

- Identidade ainda mostra Smith em UI e textos.
- O agente criado em bootstrap ainda usa nome temporario de sandbox.
- O prompt nao e AutoBrokers final.
- Nao ha pacotes de dominio AutoBrokers carregados.
- Nao ha cards operacionais na home.
- Nao ha alertas de integracoes, atendimentos ou Auxiliares.
- RAG ainda precisa smoke controlado com documento pequeno.

Recomendacao para AutoBrokers Home:

```txt
AutoBrokers Home
  Chat central do AutoBrokers
  Atalhos:
    - Ver atendimentos pendentes
    - Criar/ativar Auxiliar
    - Consultar base de conhecimento
    - Ver integracoes/canais
    - Ver custos/uso
  Cards:
    - Atendimentos em aberto
    - Ultimas conversas
    - Auxiliares ativos
    - Ultimas execucoes
    - Status WhatsApp/canais
    - Status de credito/uso
    - Alertas de configuracao
```

Nao implementar isso antes de fechar branding base e RAG smoke minimo.

## 7. Inventario Agents/Subagents

Tabelas e campos principais:

| Entidade | Tabela/arquivo | Papel atual | Reuso AutoBrokers |
| --- | --- | --- | --- |
| Agents | `agents` | Agentes por company, provider/model/prompt/tools/RAG/widget/memory | AutoBrokers, agentes de atendimento, Auxiliares tecnicos |
| Subagents | `agents.is_subagent`, `allow_direct_chat` | Especialistas delegaveis | Motor base dos Auxiliares |
| Delegations | `agent_delegations` | Permite agente principal chamar subagente | Relacao AutoBrokers -> Auxiliares/especialistas |
| HTTP tools | `agent_http_tools` | Ferramentas HTTP por agente | Integracoes InfoCap, portais, APIs internas |
| MCP connections | `agent_mcp_connections` | Conexoes MCP por agente | Ferramentas externas e conectores |
| MCP tools | `agent_mcp_tools` | Habilitacao de ferramentas MCP | Permissoes e escopo por agente/Auxiliar |

Arquivos importantes:

| Area | Arquivo |
| --- | --- |
| Agents API | `backend/app/api/agents.py` |
| Agent config API | `backend/app/api/agent_config.py` |
| Agent graph | `backend/app/agents/graph.py` |
| SubAgent tool | `backend/app/agents/tools.py` |
| LangChain graph service | `backend/app/services/langchain_service.py` |
| Admin agent modal | `components/admin/AgentConfigModal.tsx` |
| Subagent config tab | `components/admin/SubAgentConfigTab.tsx` |
| Agent list Next API | `app/api/agents/route.ts` |
| Company agents page | `app/admin/companies/[companyId]/agents/page.tsx` |

O que ja existe:

- CRUD de agents.
- Configuracao de provider/model/prompt/temperatura/tokens.
- Suporte a agent ativo/inativo.
- Subagents com `is_subagent`.
- Controle `allow_direct_chat`.
- Delegations entre agente principal e subagents.
- Cache/invalidation de grafo.
- HTTP tools dinamicas.
- MCP tools por agente.
- RAG por agente.
- Web search, human handoff, CSV analytics, UCP tools.
- Memory settings.
- Widget config.
- Security settings basicos no modal.

O que parece funcional:

- Chat direto com agente ativo.
- Criacao/listagem de agentes por empresa.
- Delegation no backend via `SubAgentTool`.
- Invalidation do grafo apos alteracoes.
- Ferramentas HTTP/MCP como infraestrutura.

O que esta incompleto para Auxiliares:

- Nao existe conceito de "Auxiliar" como produto.
- Nao existe galeria/marketplace.
- Nao existe template global de Auxiliar.
- Nao existe instalacao por corretora.
- Nao existe historico de execucoes de Auxiliares.
- Nao existe scheduler/trigger model claro no produto.
- Nao existe permission guard por acao de negocio.
- Nao existe approval/HITL de execucao operacional.

Nota de prontidao:

| Uso | Nota | Motivo |
| --- | ---: | --- |
| Agente central AutoBrokers | 72/100 | Base pronta, falta identidade/prompt/cards/dominio. |
| Subagents tecnicos | 74/100 | Motor existe, precisa produto/UX/permissoes. |
| Auxiliares MVP | 58/100 | Pode reaproveitar motor, mas faltam templates, instalacoes e execucoes. |

## 8. Inventario Tools/MCP/HTTP

Ferramentas atuais:

| Tipo | Onde aparece | Prontidao | Reuso AutoBrokers |
| --- | --- | ---: | --- |
| HTTP tools | `agent_http_tools`, `HttpToolRouter`, tab no `AgentConfigModal` | Alta | Base para InfoCap, APIs internas, portais via backend e Evolution depois |
| MCP tools | `backend/app/api/mcp.py`, `mcp_gateway_service`, `agent_mcp_connections`, `agent_mcp_tools` | Media/alta | Conectores externos, Google, Slack, GitHub, outros |
| Web search | `WebSearchTool` | Media | Pode ser P2; nao bloquear MVP |
| Human handoff | `HumanHandoffTool`, chat/handoff | Media | Base para atendimento humano |
| CSV analytics | `CSVAnalyticsTool` | Media | Util para relatorios e planilhas |
| UCP commerce tools | `ucp_*` | Baixa para seguros | Pode ser legado funcional do Smith; revisar/remover depois |
| WhatsApp Z-API | `backend/app/api/webhook.py`, zapi settings | Media | Referencia/adaptador; AutoBrokers deve priorizar Evolution depois |

Gaps para produto:

- Registry de conexoes por corretora.
- Vault/credenciais por corretora com escopo e auditoria.
- Permission guard por ferramenta/acao.
- Catalogo de ferramentas aprovadas para AutoBrokers, Atendimento e Auxiliares.
- Modo dry-run/aprovacao humana por tool action.
- Adaptadores AutoBrokers: Evolution, InfoCap, portais seguradoras, Quiver/outros.

Recomendacao:

Nao criar integracoes reais agora. Primeiro padronizar:

```txt
Connection Registry
Tool Permission Policy
Tool Execution Log
Approval/HITL
Dry-run por ambiente
```

## 9. Inventario RAG/Documentos

O que existe:

| Area | Arquivo/tabela | Papel |
| --- | --- | --- |
| Upload/listagem de documentos | `components/admin/DocumentManagementModal.tsx` | UI de base de conhecimento por empresa/agente |
| Proxy Next documents | `app/api/admin/proxy/documents/...` | Encaminha para backend |
| Backend documents API | `backend/app/api/documents.py` | Upload, listagem, chunks, benchmark, reprocess, delete |
| Documents table | `documents` | Documento, company, agent, status, chunks, metadata |
| Ingestion service | `backend/app/services/ingestion_service.py` | Chunking/embedding/indexacao |
| Search service | `backend/app/services/search_service.py` | Busca Qdrant, rerank e logs |
| Qdrant service | `backend/app/services/qdrant_service.py` | Collections, chunks, search/delete |
| MinIO service | `backend/app/services/minio_service.py` | Storage de arquivos |
| Sanitization service | `backend/app/services/sanitization_service.py` | Docling + MinIO para documentos limpos |
| Docling service | `docling-service/` | Conversao robusta para Markdown/texto |

Modos e estrategias:

- Ingestion modes na UI: `semantic` e `filesystem`.
- Estrategias: `agentic`, `semantic`, `page`, `recursive`, `csv`.
- Upload exige empresa e agente selecionado.
- Documentos se vinculam a `company_id` e `agent_id`.
- Qdrant trabalha com collections por company/contexto.
- Busca pode usar metadata filtering e tracking de custo de embedding.

RAG minimo recomendado agora:

1. Criar ou selecionar agente AutoBrokers sandbox.
2. Subir um documento pequeno `.md` ou `.txt`.
3. Processar via ingestion semantic simples.
4. Confirmar chunks no Admin.
5. Perguntar no chat algo que dependa do documento.
6. Confirmar se a resposta cita o conteudo do documento.

Docling:

- Nao e obrigatorio para primeiro RAG minimo.
- E importante para apolices, PDFs, comprovantes, imagens, tabelas e anexos.
- Deve entrar P1 depois do smoke RAG simples.
- Pode consumir mais RAM/build e deve ser validado isoladamente.

## 10. Inventario Logs/Custos

Tabelas principais:

| Tabela | Papel |
| --- | --- |
| `system_logs` | Logs administrativos/sistema |
| `conversation_logs` | Logs detalhados de conversas e chamadas de agente |
| `token_usage_logs` | Uso de tokens/modelos/servicos e custo |
| `company_credits` | Saldo/credito por empresa |
| `credit_transactions` | Movimentos de credito |
| `plans` | Planos |
| `subscriptions` | Assinaturas/status |

Fluxo de credito/custo:

```txt
Chat recebido
  -> BillingCore valida company_credits e subscription
  -> LLM/RAG/tool executa
  -> token_usage_logs registra uso
  -> worker de billing pode debitar creditos
  -> FinOps/Admin exibe uso e custos
```

O que ja funcionou no sandbox:

- Chat bloqueou corretamente quando faltava credito.
- Apos credito/agente, chat respondeu.
- Admin mostra logs e activity cards.
- FinOps/plans/pricing existem.

Gaps:

- Confirmar se worker/billing real esta ativo no ambiente ou se apenas API/Web estao rodando.
- Consolidar telas duplicadas de custos (`/admin/costs` e `/admin/finops/*`).
- Definir politica AutoBrokers para credito sandbox, trial, plano real e limites por corretora.
- Garantir que logs nao imprimem segredos.

## 11. Inventario Auxiliares

### Modelo conceitual recomendado

```txt
Auxiliar Global
  Template criado pelo Admin Global AutoBrokers
  Define objetivo, prompt, ferramentas permitidas, gatilhos, permissoes, RAG, custo esperado e aprovacoes

Auxiliar Instalado
  Instancia ativada por uma corretora
  Vincula conexoes da corretora, parametros, agenda, mensagens e limites

Execucao do Auxiliar
  Rodada manual, agendada, por evento ou por comando
  Gera steps, logs, custo, resultado e possiveis aprovacoes humanas
```

### Tabelas existentes reaproveitaveis

| Tabela | Reuso |
| --- | --- |
| `agents` | Representar AutoBrokers, agentes de atendimento e subagents/Auxiliares tecnicos |
| `agent_delegations` | Delegar tarefas do AutoBrokers para Auxiliares/subagents |
| `agent_http_tools` | Ferramentas HTTP dos Auxiliares |
| `agent_mcp_connections` | Conexoes MCP por agente/Auxiliar |
| `agent_mcp_tools` | Ferramentas MCP habilitadas |
| `documents` | Conhecimento por empresa/agente/Auxiliar |
| `conversation_logs` | Auditoria de interacoes do Auxiliar |
| `token_usage_logs` | Custos das execucoes |
| `system_logs` | Eventos operacionais |

### Tabelas novas provaveis

| Tabela sugerida | Papel |
| --- | --- |
| `auxiliary_templates` | Galeria global de Auxiliares aprovados |
| `auxiliary_installations` | Auxiliares ativados por corretora |
| `auxiliary_runs` | Execucoes de um Auxiliar instalado |
| `auxiliary_run_steps` | Passos internos, tools, resultados parciais |
| `auxiliary_approvals` | HITL/aprovacoes humanas |
| `auxiliary_schedules` | Agendas, triggers e recorrencias |
| `tenant_connections` | Conexoes/credenciais por corretora |
| `tool_permission_grants` | Permissoes por tool/action/contexto |

### Endpoints existentes reaproveitaveis

- CRUD agents/subagents.
- Delegations.
- HTTP tools.
- MCP connections/tools.
- Chat/stream.
- Documents/RAG.
- Billing/logs.

### Endpoints novos provaveis

- `GET /api/auxiliaries/templates`
- `POST /api/auxiliaries/templates`
- `POST /api/auxiliaries/install`
- `GET /api/auxiliaries/installed`
- `POST /api/auxiliaries/{id}/run`
- `GET /api/auxiliaries/{id}/runs`
- `POST /api/auxiliaries/{runId}/approve`
- `GET/POST /api/connections`
- `GET/POST /api/tool-permissions`

### UI minima

Admin Global:

- Galeria de Auxiliares.
- Criar/editar template.
- Definir tools permitidas, custo esperado, prompt, publico-alvo e riscos.

Corretora:

- Galeria de Auxiliares disponiveis.
- Ativar Auxiliar.
- Configurar conexoes/parametros.
- Ver Auxiliares instalados.
- Rodar manualmente.
- Ver historico de execucoes.
- Aprovar acoes pendentes.

### Sem worker vs com worker

Pode ser feito sem worker:

- Execucao manual de Auxiliar.
- Delegation chamada a partir do AutoBrokers.
- Testes de tools em modo dry-run.
- Historico simples.

Exige worker/Celery:

- Agenda recorrente.
- Retentativas.
- Execucoes longas.
- Processamento em lote.
- Monitoramento de jobs.
- Docling pesado.

Exige aprovacao humana:

- Enviar mensagem real.
- Abrir/alterar portal externo.
- Usar credenciais sensiveis.
- Gerar cobranca.
- Alterar dados de cliente/apolice.
- Executar qualquer acao irreversivel.

Fase 2:

- Criacao conversacional de Auxiliares pelo AutoBrokers.
- Marketplace sofisticado.
- Autonomia multi-step com permissao graduada.
- Scheduler visual completo.

## 12. Gaps para AutoBrokers

| Gap | Severidade | Motivo | Proximo passo |
| --- | --- | --- | --- |
| Branding Smith/nome legado visivel | P0 | Produto final nao pode exibir Smith nem nomes legados | Branding base controlado |
| AutoBrokers Home ausente | P0 | Tenant atual e chat simples, nao home operacional | Criar home chat-first |
| Prompt/identidade AutoBrokers ausente | P0 | Agente ainda generico/sandbox | Definir config/prompt AutoBrokers |
| Auxiliares como produto ausentes | P1 | Motor existe, mas nao ha galeria/instalacao/execucoes | Planejar data model |
| RAG nao validado com documento AutoBrokers | P1 | Base existe, mas falta smoke de produto | RAG minimo |
| Connection Vault por corretora | P1 | Conexoes precisam ser reutilizadas e seguras | Modelar conexoes/permissoes |
| Permission Guard/HITL | P1 | Tools e Auxiliares precisam aprovacao e limites | Politica + tabelas |
| Atendimento externo | P1 | Faltam fila/casos/segurados/corredores/canais | Mapear modulo |
| Worker/scheduler | P1/P2 | Necessario para Auxiliares recorrentes | Subir depois do MVP manual |
| Docling | P2 | Importante para documentos reais, mas pesado | Validar apos RAG simples |
| Z-API vs Evolution | P2 | Smith usa Z-API; AutoBrokers tende a Evolution | Criar provider abstraction depois |
| UCP/commerce | P3 | Pode ser irrelevante para seguros | Revisar/remover depois |

## 13. Riscos tecnicos

| Risco | Severidade | Observacao | Mitigacao |
| --- | --- | --- | --- |
| Branding antigo ficar no produto | P0 | Smith ou nomes legados ainda aparecem em UI, assets e prompts | Patch de branding base antes de expandir produto |
| Service role exposto por engano | P0 se ocorrer | Nao foi confirmada exposicao no inventario, mas Web tem server routes sensiveis | Auditar imports client/server antes de public launch |
| Copia bruta de legado | P0 | Contraria ADR e causa contaminacao | Manter fronteira do repo e importar apenas pacotes curados |
| Chat depender de credito sem UX clara | P1 | Ja houve bloqueio por credito | Manter mensagens claras e painel de credito |
| Ausencia de worker | P1 | Billing/execucoes recorrentes podem ficar incompletos | Subir worker quando entrar em Auxiliares/RAG pesado |
| Tools sem permission guard de negocio | P1 | Risco em portais, WhatsApp, InfoCap e dados reais | Dry-run, HITL e policy por tool |
| RAG com documentos reais sem curadoria | P1 | Pode responder errado ou vazar contexto | Smoke com docs pequenos; depois curadoria/pacotes |
| Docling pesado | P2 | Pode consumir recursos e falhar build | Isolar como P1/P2, apos RAG minimo |
| Z-API ativado cedo | P2 | Canal real nao deve entrar antes de provider abstraction | WhatsApp real off ate desenho EvolutionProvider |
| Duplicidade de telas FinOps/costs | P2 | Pode confundir Admin | Consolidar depois |

## 14. Roadmap recomendado

| Batch | Objetivo | Arquivos provaveis | Risco | Duracao estimada | Prioridade | Criterio de sucesso |
| --- | --- | --- | --- | --- | --- | --- |
| `BATCH_35B_BRANDING_BASE` | Remover Smith/nome legado visivel e fixar AutoBrokers | `app/*`, `components/*`, `public/*`, prompts default | Medio | 1-2 turnos | P0 | UI nao mostra Smith/nome legado; chat ainda funciona |
| `BATCH_35C_AUTOBROKER_HOME_PLAN` | Planejar home AutoBrokers chat-first antes de patch | `app/dashboard/*`, `components/dashboard/*` | Baixo | 1 turno | P0 | Layout/escopo aprovado |
| `BATCH_35D_AUTOBROKER_HOME_PATCH` | Criar primeira home AutoBrokers com chat, atalhos e cards basicos | `app/dashboard/page.tsx`, `app/dashboard/chat`, componentes | Medio | 2-3 turnos | P0 | Usuario entra no dashboard e entende AutoBrokers |
| `BATCH_35E_RAG_MINIMAL_SMOKE` | Testar upload de documento pequeno e resposta com base | Admin documents, backend docs, Qdrant | Medio | 1-2 turnos | P1 | Documento indexado e chat responde sobre ele |
| `BATCH_35F_AUXILIAR_MODEL_PLAN` | Definir data model e UX minima de Auxiliares | docs/plan, schema plan | Baixo | 1 turno | P1 | Modelo aprovado sem migration |
| `BATCH_35G_AUXILIAR_GALLERY_MVP` | Criar Galeria/ativacao manual usando agents/subagents | admin/tenant UI, endpoints | Alto | 3-5 turnos | P1 | Corretora ativa Auxiliar manualmente |
| `BATCH_35H_CONNECTION_VAULT_POLICY` | Modelar conexoes e permissoes por corretora | schema plan, admin UI plan | Alto | 2-3 turnos | P1 | Politica de conexoes aprovada |
| `BATCH_35I_ATTENDANCE_PRODUCT_MAP` | Mapear atendimento externo sobre Smith + legado de referencia | docs/audit/plan | Baixo | 1-2 turnos | P1 | Lacunas de fila/casos/canais claras |
| `BATCH_35J_WORKER_SCHEDULER_BOOT` | Subir/validar worker para jobs e billing | backend workers, deploy docs | Alto | 2-4 turnos | P1/P2 | Worker processa jobs sem quebrar chat |
| `BATCH_35K_AGENT_OS_V2_PACKAGE_IMPORT_PLAN` | Planejar importacao curada do cerebro V2 | docs/plan, knowledge packages | Medio | 2 turnos | P2 | Lista de pacotes, destinos e validacoes |

Ordem recomendada:

```txt
35B -> 35C -> 35D -> 35E -> 35F -> 35G
```

Racional: primeiro limpar identidade e Home, depois provar conhecimento/RAG, depois construir Auxiliares.

## 15. Proximo batch recomendado

Proximo batch recomendado:

```txt
BATCH_35B_BRANDING_BASE
```

Objetivo:

- Remover branding visivel Smith/nome legado do produto final.
- Fixar o nome AutoBrokers para o agente central.
- Manter runtime e estrutura Smith por baixo, sem refactor profundo.
- Nao mexer em RAG, Worker, Docling, WhatsApp, InfoCap, n8n, corredores ou Agent OS V2.

Criterios de sucesso:

- Admin login/dashboard e tenant chat funcionam apos patch.
- UI nao exibe Smith/nome legado em rotas principais.
- AutoBrokers aparece como agente central.
- Documentacao tecnica pode mencionar Smith apenas em ADR/docs internos.

Pontos que ficaram fora deste batch por decisao:

- Nao foi executado build.
- Nao foi executado typecheck.
- Nao foram rodadas migrations.
- Nao houve acesso ao EasyPanel/Supabase.
- Nao houve copia de conteudo legado.
- Nao houve implementacao de features.
