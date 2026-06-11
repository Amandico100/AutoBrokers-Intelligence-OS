# SPEC-002 — Auxiliares usam Smith Agents/Subagents como runtime

> **Status:** CANÔNICO (lei do projeto). Toda IA (Claude/Codex/qualquer chat) DEVE ler isto antes de mexer em Auxiliares, Agents ou Vault.
> **Data:** 2026-06-09 · Relacionado: ADR-001 (runtime), ADR-002 (Vault), UX-007 (auxiliares), ROADMAP-001.

## 1. Decisão oficial
```
AutoBrokers Auxiliares = camada de PRODUTO (catálogo, UX, instalação, governança).
Smith Agents/Subagents = RUNTIME técnico (inteligência, memória, tools, MCP, segurança, execução).
Vault                  = GOVERNANÇA (segredos, conectores, permissões, HITL, auditoria).
```
**Auxiliares NÃO são um novo motor de agentes.** O motor é o do Smith. Não criar motor paralelo.

## 2. Problema corrigido
Estávamos caminhando para uma estrutura paralela de Auxiliares que reimplementaria inteligência/execução por fora — desperdiçando a estrutura pronta do Smith (agents, subagents, memória, tools, MCP, segurança, delegations, RAG, logs). Isto fica **proibido**.

## 3. Camadas
- **Produto (Auxiliares):** `auxiliary_templates` (catálogo global, Admin), `tenant_auxiliaries` (instalação por corretora), `auxiliary_runs` (histórico), Galeria/Meus/Execuções, Admin → Auxiliares Globais.
- **Runtime (Smith):** `agents`/subagents por empresa, `agent_delegations`, tools (`agent_http_tools`/MCP/UCP), memória, segurança, `backend/app/api/agents.py` (`POST /api/agents/` via `AgentService`).
- **Governança (Vault):** `connector_templates`, `tenant_connections`, `permission_grants`, `approval_requests`, `vault_audit_log`; segredos cifrados; HITL; auditoria.

## 4. Tipos de runtime (declarados no template)
Todo Auxiliar avançado DEVE declarar runtime em `auxiliary_templates.default_config.runtime.kind`:
- **`specific_executor`** — tarefa fixa com executor dedicado já implementado (ex.: `resumo-atendimentos`, `follow-up-whatsapp`). `{ "kind":"specific_executor", "executor":"<slug>" }`.
- **`smith_agent_blueprint`** — usa um Agent/Subagent Smith como motor. Guarda o **blueprint** (sem segredos). `{ "kind":"smith_agent_blueprint", "agent_blueprint": { name, slug, is_subagent, allow_direct_chat, llm_provider, llm_model, agent_system_prompt, ... } }`.
- **`workflow`** — corredor/workflow (fase futura). `{ "kind":"workflow", "workflow":"<id>" }`.
- **`none`** — sem runtime técnico ainda (em preparação).

## 5. Modelo global × por empresa
- O **template global** guarda apenas um **blueprint** (modelo), **não** um agent compartilhado.
- Templates globais **NÃO compartilham um único agent** entre empresas.
- O **agent/subagent real é criado por empresa** ao instalar.

## 6. Instalação
Ao instalar um Auxiliar global numa corretora (`POST /api/admin/auxiliaries/templates/[id]/install`):
1. Cria/garante `tenant_auxiliaries` (idempotente por `company_id`+`slug`).
2. Lê `template.default_config.runtime`.
3. Se `kind = smith_agent_blueprint`: cria um Agent/Subagent Smith **daquela empresa** via `POST /api/agents/` (canônico, `X-Admin-API-Key`), a partir do blueprint **sanitizado**; salva `agent_id` em `tenant_auxiliaries.config.runtime.agent_id` (`kind:'smith_agent'`).
4. Se `kind = specific_executor`: grava `config.runtime.kind='specific_executor'` (não cria agent).
5. Se `kind = none/workflow`: instala sem agent.
6. **Idempotência:** se `config.runtime.agent_id` já existe, NÃO cria outro agent.

## 7. Personalização por corretora
O agent criado é da corretora — ela pode evoluí-lo em **Admin → Empresa → Agents** (prompt, modelo, tools, memória, segurança). O template global permanece como modelo; mudanças por corretora vivem no agent dela.

## 8. Regra de segredos (OBRIGATÓRIA)
Campos **proibidos** em blueprints/config/templates/logs/frontend/relatórios:
`llm_api_key, vision_api_key, token, client_token, access_token, refresh_token, api_key, password, secret, credential`.
Qualquer blueprint extraído de um agent existente DEVE passar por **sanitização profunda** (`sanitizeBlueprint`). Segredos vivem **só no Vault** (cifrados) e nos campos próprios do agent (cifrados pelo runtime), nunca em `auxiliary_templates.default_config` nem `tenant_auxiliaries.config`.

## 9. WhatsApp/Vault como caminho oficial
- Caminho oficial de credenciais WhatsApp: **Personalização → Conectores (Vault)** — token cifrado, `tenant_connection` → `integrations.id`, permissões, HITL, dry-run, auditoria.
- A aba de WhatsApp no **Agent Admin antigo** é **legado técnico**: não é caminho oficial para segredos; a rota `/api/admin/integrations` **já bloqueia** gravação de `token`/`client_token` (39A4.1).

## 10. O que é PROIBIDO
- Criar motor paralelo de execução de Auxiliares.
- Compartilhar um agent global entre empresas.
- Salvar segredos em `default_config`/`config`/logs/frontend.
- Usar a rota antiga de WhatsApp como caminho oficial de segredo.
- Criar Auxiliar avançado **sem declarar runtime**.
- Rodar SQL/alterar schema sem aprovação do Architect/fundador.

## 11. Como novas IAs devem proceder
1. Ler esta SPEC + ADR-001/ADR-002 + UX-007 antes de mexer.
2. Auxiliar = produto; runtime = Smith agent/executor/workflow.
3. Reusar `POST /api/agents/` para criar agents (nunca insert cru em `agents`).
4. Reusar Vault para segredos/conectores/HITL.
5. Sem schema novo sem aprovação; preferir JSON (`default_config`/`config`) resiliente.
6. Sanitizar qualquer blueprint; nunca copiar segredo.

## 12. Checklist antes de criar um novo Auxiliar
- [ ] Tem `auxiliary_template` (catálogo) com `slug` único?
- [ ] `default_config.runtime.kind` declarado (`specific_executor` | `smith_agent_blueprint` | `workflow` | `none`)?
- [ ] Se `smith_agent_blueprint`: blueprint **sem segredos**? agent criado **por empresa** na instalação?
- [ ] Ações externas passam por **Vault + HITL** (approval_request)?
- [ ] Conectores/segredos no **Vault**, não no modal antigo?
- [ ] Sem motor paralelo? Sem SQL/schema sem aprovação?
- [ ] Execuções aparecem em `auxiliary_runs`?

---

# Apêndice A — Guia detalhado (41A.2)

## A1. Fluxo completo de criação
1. **Agent técnico (experimental/sandbox)** — crie/teste um Agent/Subagent em **Admin → Empresas → Agents** (prompt, modelo, tools, memória, segurança).
2. **Publicar como template** — **Admin → Auxiliares Globais → "Publicar Agent existente"**: extrai um **blueprint sanitizado** (sem segredos) e cria `auxiliary_templates` com `runtime.kind='smith_agent_blueprint'`.
3. **Instalar por corretora** — instala `tenant_auxiliaries`; se blueprint, cria/vincula um Agent **da corretora**.
4. **Personalizar localmente** — a corretora evolui o agent dela (documentos, tom, horários, integrações) em Admin → Empresa → Agents.
5. **Executar / Auditar** — execução via runtime; histórico em `auxiliary_runs`; ações externas via Vault + HITL + `vault_audit_log`.

## A2. Inteligência global × personalização local
- **Global (viaja no blueprint):** prompts base, regras, playbooks, raciocínio operacional, estrutura de atendimento, guardrails. Curada e versionada.
- **Local (fica na instância da corretora):** documentos, dados da corretora, tom local, horários, integrações, permissões, carteiras, seguradoras atendidas, contatos.
- **Conhecimento sensível/local NÃO é global por padrão.** Nunca empacotar dado de uma corretora no template global.

## A3. Tipos de Auxiliar (visibilidade)
- **global** — disponível a todas as corretoras na Galeria.
- **exclusivo de uma corretora** — `default_config.visibility = { type:'private', company_id }` (filtragem futura na Galeria; por ora pode ser instalado só na empresa).
- **experimental/sandbox** — `status='draft'` / `is_active=false`.
- **em preparação** — `runtime.kind='none'` (sem executor/agent ainda).

## A4. Relação com RAG
- O blueprint pode **declarar** que exige conhecimento, mas **documentos globais ≠ documentos locais**.
- O **agent local da corretora** recebe os **documentos locais** dela.
- **Conhecimento global** deve ser **curado e versionado** (fase 41C). Não misturar conhecimento de corretoras.

## A5. Relação com corredores/workflows
- Corredores/workflows usam **agents/subagents como executores de fases** — `runtime.kind='workflow'`.
- Corredor **não é** um Auxiliar simples; é orquestração de fases (fase 42A).

## A6. Regras para novas IAs (decisão de runtime)
- Tarefa fixa simples → **`specific_executor`**.
- Precisa de tools/MCP/RAG/memória/persona → **`smith_agent_blueprint`** (Smith Agent/Subagent).
- Processo com fases → **`workflow`** (corredor).
- Sempre **declarar runtime** antes de criar; nunca motor paralelo.

## A7. Como evitar duplicidade
- Instalação é **idempotente** por `(company_id, slug)`.
- Publicar um agent existente **da mesma empresa** com "instalar na origem" → **vincula o agent original** (`linked_original:true`), **não cria cópia**.
- Instalar o mesmo template em **outra empresa** → cria um novo agent a partir do blueprint.

## A8. Segredos (reforço)
- `FORBIDDEN_SECRET_KEYS` removidos por `sanitizeBlueprint` (profundo) em qualquer publicação.
- **GET legado** de `/api/admin/integrations` **não retorna** token/client_token — apenas flags (`has_token`, `token_configured`). Caminho oficial de credenciais = **Vault**.
