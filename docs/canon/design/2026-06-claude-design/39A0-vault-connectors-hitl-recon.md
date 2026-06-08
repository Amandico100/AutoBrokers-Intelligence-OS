# 39A0 — Vault / Connectors / HITL Recon

> **Status:** recon read-only concluído · **somente docs criados** (relatório + SQL SELECT-only) · nenhum código/SQL/schema alterado, nenhum acesso ao banco, nenhuma API externa.
> **Data:** 2026-06-08 · **Modelo:** Claude Opus 4.8 · **Branch:** main · **Tipo:** auditoria + proposta.

## 1. Resumo executivo
O Smith Runtime já tem **fundações técnicas sólidas** para conectores/credenciais: catálogo MCP global (`mcp_servers`), conexões MCP OAuth **com tokens criptografados** (`agent_mcp_connections` + `mcp_oauth_service` + `EncryptionService` Fernet/AES), HTTP tools por agente (`agent_http_tools`), tools MCP por agente (`agent_mcp_tools`), integrações por empresa (`integrations` = Z-API/WhatsApp) e delegação a subagentes (`agent_delegations`). Há também um **handoff humano no chat** (`request_human_agent` → `conversations.status='HUMAN_REQUESTED'`). **O que falta é a camada de PRODUTO**: conexões **por corretora** reutilizáveis, **permissões por módulo**, **aprovação humana de AÇÕES** (HITL antes de executar) e **auditoria**. Tudo isso já está conceitualmente definido em **ADR-002 §19–20**, que manda exatamente esta auditoria antes de qualquer schema. **Recomendação: Caminho B** — criar uma camada de produto (`tenant_connections` + `permission_grants` + `approval_requests` + `vault_audit_log`) que **referencia** as estruturas técnicas existentes **sem duplicar segredos**.

## 2. O que foi auditado
- **Docs canônicos:** ADR-002 (Vault, completo), ADR-001, ADR-003, UX-001, UX-007, PRD-001, ROADMAP-001, 38A0/38A5.0/38A5.1.
- **Schema:** `agent_http_tools`, `agent_mcp_connections`, `agent_mcp_tools`, `mcp_servers`, `ucp_connections`, `integrations`, `agent_delegations`, `agents`, `conversations` (DDLs em `schema_completo.sql`).
- **Backend:** `services/encryption_service.py`, `services/mcp_oauth_service.py`, `services/mcp_gateway_service.py`, `agents/tools/human_handoff.py`, `agents/tools/__init__.py`, `agents/graph.py`, `api/mcp.py`, `api/ucp.py`, `api/agent_config.py`, `api/webhook.py`.
- **Frontend:** `app/dashboard/personalizacao/{conectores,seguradoras}` (mock do 37B4), `components/admin/{MCPConfigTab,UCPConfigTab}`.
- **Não aberto:** pastas externas (ResultVision/INTAKE/QUARENTENA), nenhum valor de credencial.

## 3. Estruturas existentes de tools/MCP/UCP/HTTP tools
- **MCP (Model Context Protocol):** catálogo global `mcp_servers` (provider OAuth, scopes, command, env_vars) + conexões OAuth por agente `agent_mcp_connections` (tokens criptografados) + tools habilitadas `agent_mcp_tools`. Serviços: `mcp_oauth_service` (OAuth + criptografia + refresh), `mcp_gateway_service` (execução). API: `api/mcp.py`; UI admin: `MCPConfigTab`.
- **HTTP tools:** `agent_http_tools` (method/url/headers/parameters/body_template por agente) — ferramentas REST genéricas anexadas a um agente.
- **UCP (Universal Commerce Protocol):** `ucp_connections` + `api/ucp.py` + serviços `ucp_*` (e-commerce/Shopify) — tangencial a seguros; reuso conceitual baixo.
- **Delegação:** `agent_delegations` (orchestrator → subagent) habilita SubAgentTool (base para Auxiliares chamarem subagentes).

## 4. Tabelas encontradas e papel de cada uma
| Tabela | Escopo | Papel | Segredos |
|---|---|---|---|
| `mcp_servers` | global | catálogo de servidores MCP (≈ connector template MCP) | `env_vars` pode conter |
| `agent_mcp_connections` | **por agente** | conexão OAuth + `access_token`/`refresh_token` | **sim (criptografados)** |
| `agent_mcp_tools` | por agente | tools MCP habilitadas | não |
| `agent_http_tools` | por agente | tools HTTP (url/headers/body) | possível em `headers` |
| `integrations` | **por empresa** | Z-API/WhatsApp (`token`, `instance_id`) | **sim** |
| `agent_delegations` | por agente | orchestrator → subagente | não |
| `agents` | por empresa | `llm_api_key`/`vision_api_key` criptografados | **sim (criptografados)** |
| `ucp_connections` | agente/empresa | conexões de commerce (UCP) | possível |
| `conversations` | por empresa | `status`/`human_handoff_reason` (handoff de chat) | não |

## 5. Como agents/subagents usam ferramentas hoje
No runtime LangGraph (`agents/graph.py` + `agents/tools/`), cada **agente** monta seu conjunto de tools a partir das tabelas **por agente**: HTTP tools (`agent_http_tools`), MCP tools (`agent_mcp_tools` via gateway), `request_human_agent` (handoff) e SubAgentTool (`agent_delegations`). Tokens MCP são descriptografados sob demanda (`mcp_oauth_service.decrypt`). **Tudo é ancorado em `agent_id`**, não em "conexão da corretora compartilhada".

## 6. Como Auxiliares poderiam reutilizar essas ferramentas
Hoje, reuso direto seria **por agente** (cada Auxiliar precisaria de um agente com as tools anexadas) — não é o modelo de produto desejado (conexão única da corretora, reusada por AutoBrokers/Atendimentos/Auxiliares). O Auxiliar de Resumo (38A2) **não usa tools** (só LLM sobre `messages`). Para o **Auxiliar de Cobrança** (próximo), seria preciso uma **conexão de empresa** (WhatsApp/e-mail) + **permissão de uso** + **aprovação** — ou seja, a camada de produto do Vault (ver §8/§19).

## 7. O que já existe para credenciais/conexões
- **Criptografia real:** `EncryptionService` (Fernet/AES-256, chave `ENCRYPTION_KEY`). Usado para `agent_mcp_connections.access_token/refresh_token` (via `mcp_oauth_service`) e `agents.llm_api_key/vision_api_key` (via `api/agent_config.py`).
- **OAuth funcional:** `mcp_oauth_service` (authorize/callback/refresh).
- **Conector de empresa existente:** `integrations` (Z-API/WhatsApp por `company_id`).
- **Catálogo global:** `mcp_servers`.

## 8. O que falta para um Vault de produto
- **Conexão por CORRETORA reutilizável** (não por agente): hoje só `integrations` (Z-API) é company-scoped; MCP/HTTP são por agente.
- **Catálogo de conectores de produto** (além de MCP): `connector_templates` com categoria/risco/escopos/UX.
- **Referência de segredo única** (`encrypted_secret_ref`) — reusar `EncryptionService` sem duplicar valores.
- **Health/estado/owner/last_used** por conexão.
- **Verificar:** se `integrations.token` (Z-API) é criptografado (o grep só confirmou criptografia em MCP/LLM keys) → **risco a corrigir**.

## 9. O que já existe para permissões
Permissões hoje são **implícitas e por agente/empresa**: `is_active`/`is_enabled` nas tools, `allow_direct_chat`/`is_subagent` nos agentes, `security_settings` (jsonb) no agente, e o **gate de saldo** (billing). **Não há** um modelo de "este módulo/Auxiliar pode usar esta conexão para esta finalidade".

## 10. O que falta para permissões por conector
Falta a entidade **Permission Grant** (ADR-002 §19.3): `(company_id, tenant_connection_id, subject_type, subject_id, allowed_actions, risk_level, requires_approval, expires_at, status)`. Hoje não existe nenhuma estrutura "conexão × módulo × ação".

## 11. O que já existe para HITL/handoff/aprovação humana
- **Handoff de chat:** tool `request_human_agent` → `conversations.status='HUMAN_REQUESTED'` + `human_handoff_reason`; `webhook.py` para o pipeline de IA quando em modo humano. Isso é **transferência de conversa para humano**, útil para Atendimentos.
- **Permissões read-only nos Auxiliares (UI):** `PermissionModal`/`PermissionList` (37B3) descrevem o que o Auxiliar pode/não pode — **visual**, sem enforcement de ação.

## 12. O que falta para HITL real em ações externas
Falta o fluxo **aprovar-antes-de-executar**: entidade **Approval Request** (ADR-002 §19.5) — preview da ação (destinatário, conteúdo, conector, risco, custo), estados `pending/approved/rejected`, e **enforcement** (a ação externa só dispara após aprovação). Hoje não existe. O Auxiliar de Resumo não precisa (read-only); **o de Cobrança precisará**.

## 13. Como Conectores devem aparecer em Personalização
`/dashboard/personalizacao/conectores` (mock no 37B4) deve virar **galeria de conectores** (estilo ChatGPT Apps, ADR-002 §23/§37): cards (nome/ícone/categoria/status) → detalhe (o que faz, dados acessados, módulos que podem usar, permissões, risco) → `PermissionModal` → conectar/testar/revogar. Reusa padrões 37B3 (`GalleryGrid`/`GalleryCard`/`DetailShell`/`PermissionModal`/`StatusPill`). Estados de conexão: ADR-002 §31.

## 14. Como Seguradoras devem aparecer separadas de Conectores
Decisão de produto (UX-007/ADR-002 §24): **Seguradora é entidade própria, irmã de Conectores**, não um conector simples. Uma seguradora é um **"conector composto"** (WhatsApp + portal + 0800 + ramos + corredores). `/dashboard/personalizacao/seguradoras` lista seguradoras; cada uma **usa** conexões/canais do Vault + corredores. Conector = encanamento; Seguradora = entidade de domínio que consome conectores.

## 15. Relação com Atendimentos, corredores e portais
Atendimentos (ADR-003) usa o Vault para WhatsApp/telefonia/portais/sistema de gestão/corredores. Portais autenticados são **alto risco** (ADR-002 §25): MVP = só cadastro + teste de conexão; depois consulta assistida; execução só com HITL. Corredores/subcorredores são domínio de Atendimento que **referenciam** conexões do Vault.

## 16. Relação com Admin Global e catálogo global
Admin Global cria/publica o **catálogo de conectores** (`connector_templates`), define categorias/risco/permissões padrão, e (futuro) bloqueios globais + health + logs (ADR-002 §30). Hoje `mcp_servers` é o catálogo MCP; o catálogo de produto (multi-tipo: OAuth/API key/login-senha/arquivo) ainda não existe. A corretora apenas ativa/personaliza.

## 17. Riscos de segurança e LGPD
- **Segredos:** nunca expor ao client (ADR-002 §18); reusar `EncryptionService`; **confirmar** se `integrations.token` está criptografado (possível gap). RLS por `company_id` em toda tabela nova.
- **Isolamento multi-tenant:** conexões/tokens/permissões/aprovações estritamente por `company_id` (ADR-002 §17).
- **PII:** previews de aprovação e logs amigáveis não devem vazar dados sensíveis; logs técnicos separados (ADR-002 §33).
- **Intake bruto:** bloqueado para RAG sem curadoria (ADR-002 §13).

## 18. Riscos de arquitetura
- **Acoplar Vault ao `agent_id`** (Caminho A) → quebra o reuso por corretora e mistura runtime com produto.
- **Duplicar segredos** numa tabela nova → risco de inconsistência/exposição. Mitigar: `encrypted_secret_ref` aponta para o mecanismo existente (ex.: reusar `agent_mcp_connections`/`integrations` ou um store cifrado único).
- **Construir HITL/portais cedo demais** → risco operacional. Começar read-only + dry-run.

## 19. Recomendação de MVP
**Não implementar conectores reais agora.** MVP conceitual do Vault (ADR-002 §35):
1. **`tenant_connections`** (conexão por corretora: template, status, tipo, risco, `encrypted_secret_ref`, owner, health) — começando com **WhatsApp (Z-API existente)** e **conectores internos** (documentos/conversas).
2. **`permission_grants`** (conexão × módulo/Auxiliar × ações × requires_approval).
3. **`approval_requests`** (HITL: preview + aprovar/recusar) — usado pelo 1º Auxiliar com ação externa (Cobrança).
4. **`vault_audit_log`** (quem/quê/quando/resultado).
Tudo **server-side**, RLS por `company_id`, ação externa **bloqueada por padrão**. UI: galeria de conectores + permissões + aprovação (reuso 37B3).

## 20. Caminhos possíveis A/B/C
- **A) Usar `agent_mcp_connections`/`agent_http_tools`/`agent_mcp_tools` direto como produto.** Prós: zero schema novo, reuso máximo. **Contras: são por agente** (não por corretora), sem permissão/aprovação/auditoria de produto, sem catálogo multi-tipo, acoplam runtime↔produto. **Insuficiente.**
- **B) Camada de produto nova que referencia o técnico existente, sem duplicar segredos.** Prós: reuso de `EncryptionService`/OAuth/MCP/`integrations`; conexão por corretora + permissões + aprovação + auditoria; alinhado a ADR-002 §19–20; separa runtime de produto; evolui por fases. **Contras:** exige 3–4 tabelas novas (com aprovação) e adapters. **Recomendado.**
- **C) Vault totalmente novo + migrar todas as tools técnicas para ele.** Prós: modelo único e limpo. **Contras:** alto risco/retrabalho, mexe no runtime maduro do Smith, lento, desnecessário agora. **Rejeitado.**

## 21. Caminho recomendado: **B**
Criar a **camada de produto** (`tenant_connections`, `permission_grants`, `approval_requests`, `vault_audit_log`) **referenciando** o técnico existente (catálogo `mcp_servers`, OAuth/cripto `mcp_oauth_service`+`EncryptionService`, `integrations` Z-API, `agent_http_tools`) **sem duplicar segredos**. É exatamente o que ADR-002 §19/§20 descreve, preserva o runtime do Smith, e habilita conexão-única-reusável + permissões + HITL + auditoria. (Confirma a hipótese inicial do fundador.)

## 22. O que precisa de SQL futuramente
DDL (com aprovação, em batch próprio): `tenant_connections`, `permission_grants`, `approval_requests`, `vault_audit_log` (+ possível `connector_templates` se o catálogo de produto for além de `mcp_servers`). Todas com `company_id` + **RLS**, índices, e FKs para `companies`/`agents`/templates. **Verificar/migrar** criptografia de `integrations.token` se estiver em texto puro. Nenhuma alteração nas tabelas técnicas existentes.

## 23. O que precisa de código futuramente
- **Backend:** serviço Vault (CRUD de conexões + resolução de segredo via `EncryptionService`), enforcement de `permission_grants`, fluxo de `approval_requests` (criar preview → aprovar → executar), `vault_audit_log`. Adapters para WhatsApp (Z-API) em **modo rascunho/dry-run**.
- **Next API:** rotas company-scoped (`/api/connectors`, `/api/approvals`) com auth/`company_id` (padrão dos Auxiliares) + chave interna Next↔Backend.
- **Frontend:** galeria/detalhe/permissão de Conectores (reuso 37B3) + tela de Aprovações (HITL) + integração no fluxo do Auxiliar de Cobrança.

## 24. O que deve ficar fora do MVP
Automação de portal com envio real, browser automation, envio externo sem aprovação, InfoCap/Quiver/Segfy reais com escrita, multi-provider complexo, rotação automática de tokens, marketplace público, ingestão bruta automatizada, classificação 100% automática (ADR-002 §35.3).

## 25. Perguntas para Architect/Fundador
1. Confirmar **Caminho B** e abrir um batch de **modelo de dados do Vault** (SQL gerado pelo Architect, rodado manualmente) com as 4 tabelas?
2. **Primeiro conector real** do MVP: WhatsApp (Z-API já existe) em **modo rascunho** + o **Auxiliar de Cobrança** como caso de uso do HITL? (recomendado)
3. O **catálogo de conectores** de produto deve ser tabela nova (`connector_templates`) ou estender `mcp_servers`? (recomendo tabela nova, pois cobre OAuth/API key/login-senha/arquivo, não só MCP).
4. **`integrations.token` (Z-API)** está criptografado? Se não, priorizar correção antes de expandir conectores.
5. HITL primeiro como **aprovação genérica** (uma tela de Aprovações) ou embutido no fluxo do Auxiliar? (recomendo entidade genérica + UI reusável).

## 26. Próximo batch recomendado
- **Antes:** rodar `docs/sql/39A0-vault-connectors-diagnostics.sql` no Supabase e me enviar os blocos **1, 9 e 14** (confirma que não há Vault de produto e o estado das `integrations`).
- **39A1 — Vault Data Model (proposta executável):** Architect gera o SQL (tenant_connections/permission_grants/approval_requests/vault_audit_log + RLS) para execução manual; depois **39A2** (serviço Vault + HITL backend) e **39A3** (UI de Conectores + Aprovações).
- **Alternativa de valor:** **38B — Auxiliar de Cobrança (rascunhos aprováveis)** como primeiro consumidor do HITL, puxando o Vault sob demanda.

---

## Decisão recomendada: **B) Camada de produto que referencia o técnico existente, sem duplicar segredos.**
Reaproveita criptografia/OAuth/MCP/`integrations` do Smith; adiciona conexão-por-corretora + permissões + aprovação humana + auditoria; preserva o runtime; e segue exatamente ADR-002 §19–20. **A** é insuficiente (tudo por agente, sem permissão/aprovação/auditoria); **C** é arriscado e desnecessário agora.
