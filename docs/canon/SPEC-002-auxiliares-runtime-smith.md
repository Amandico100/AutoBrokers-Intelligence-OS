> [!WARNING]
> **STATUS: PARCIALMENTE SUPERADA PELA SPEC-053.**  
> Esta SPEC continua válida ao afirmar que Auxiliares são camada de produto, Smith é o runtime e Vault governa segredos/permissões. Porém, a ontologia atual, o modelo universal de `Work Run`, a separação entre Auxiliar, Skill, Workflow e Rotina, a execução durável, approvals e artifacts são governados por `specs/SPEC-053-autobrokers-work-os-core-harness.md`. Em qualquer conflito, as SPECs 052 e 053 prevalecem.

# SPEC-002 — Auxiliares usam Smith Agents/Subagents como runtime

> **Status:** CANÔNICO HISTÓRICO, subordinado às SPECs 052 e 053. Toda IA deve ler a arquitetura mais recente antes de mexer em Auxiliares, Agents, Rotinas, Skills ou Vault.
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
- **Produto (Auxiliares):** `auxiliary_templates` (catálogo global, Admin), `tenant_auxiliaries` (instalação por corretora), `auxiliary_runs` (histórico legado), Galeria/Meus/Execuções, Admin → Auxiliares Globais.
- **Runtime (Smith):** `agents`/subagents por empresa, `agent_delegations`, tools (`agent_http_tools`/MCP/UCP), memória, segurança, `backend/app/api/agents.py` (`POST /api/agents/` via `AgentService`).
- **Governança (Vault):** `connector_templates`, `tenant_connections`, `permission_grants`, `approval_requests`, `vault_audit_log`; segredos cifrados; HITL; auditoria.

> Nota atual: `auxiliary_runs` permanece como histórico/compatibilidade até migração governada para o modelo universal de Work Run definido pela SPEC-053.

## 4. Tipos de runtime (declarados no template)
Todo Auxiliar avançado DEVE declarar runtime em `auxiliary_templates.default_config.runtime.kind`:
- **`specific_executor`** — tarefa fixa com executor dedicado já implementado (ex.: `resumo-atendimentos`, `follow-up-whatsapp`). `{ "kind":"specific_executor", "executor":"<slug>" }`.
- **`smith_agent_blueprint`** — usa um Agent/Subagent Smith como motor. Guarda o **blueprint** (sem segredos). `{ "kind":"smith_agent_blueprint", "agent_blueprint": { name, slug, is_subagent, allow_direct_chat, llm_provider, llm_model, agent_system_prompt, ... } }`.
- **`workflow`** — corredor/workflow. `{ "kind":"workflow", "workflow":"<id>" }`.
- **`none`** — sem runtime técnico ainda (em preparação).

A SPEC-053 permite que um Auxiliar combine Skills, workflow, executor, Agent/Subagent e Rotinas; estes kinds são a representação histórica atual e devem ser migrados sem criar motor paralelo.

## 5. Modelo global × por empresa
- O **template global** guarda apenas um **blueprint** (modelo), **não** um agent compartilhado.
- Templates globais **NÃO compartilham um único agent** entre empresas.
- O **agent/subagent real é criado por empresa** ao instalar quando o runtime exigir Agent dedicado.

## 6. Instalação
Ao instalar um Auxiliar global numa corretora (`POST /api/admin/auxiliaries/templates/[id]/install`):
1. Cria/garante `tenant_auxiliaries` (idempotente por `company_id`+`slug`).
2. Lê `template.default_config.runtime`.
3. Se `kind = smith_agent_blueprint`: cria um Agent/Subagent Smith **daquela empresa** via `POST /api/agents/` (canônico, `X-Admin-API-Key`), a partir do blueprint **sanitizado**; salva `agent_id` em `tenant_auxiliaries.config.runtime.agent_id` (`kind:'smith_agent'`).
4. Se `kind = specific_executor`: grava `config.runtime.kind='specific_executor'` (não cria agent).
5. Se `kind = none/workflow`: instala sem agent.
6. **Idempotência:** se `config.runtime.agent_id` já existe, NÃO cria outro agent.
7. A execução futura deve convergir para `work_runs`, preservando compatibilidade até migração aprovada.

## 7. Personalização por corretora
O runtime local pode ser configurado conforme permissões, conexão, dados, tom e necessidades da corretora. O template global permanece como modelo; mudanças locais não podem contaminar automaticamente o template global.

## 8. Regra de segredos (OBRIGATÓRIA)
Campos **proibidos** em blueprints/config/templates/logs/frontend/relatórios:
`llm_api_key, vision_api_key, token, client_token, access_token, refresh_token, api_key, password, secret, credential`.
Qualquer blueprint extraído de um agent existente DEVE passar por **sanitização profunda** (`sanitizeBlueprint`). Segredos vivem **só no Vault** (cifrados) e nos campos próprios governados pelo runtime, nunca em `auxiliary_templates.default_config` nem `tenant_auxiliaries.config`.

## 9. WhatsApp/Vault como caminho oficial
- Caminho oficial de credenciais WhatsApp: **Personalização → Conectores (Vault)** — token cifrado, `tenant_connection` → `integrations.id`, permissões, HITL, dry-run, auditoria.
- A aba de WhatsApp no **Agent Admin antigo** é **legado técnico**: não é caminho oficial para segredos.

## 10. O que é PROIBIDO
- Criar motor paralelo de execução de Auxiliares.
- Compartilhar um agent global entre empresas.
- Salvar segredos em `default_config`/`config`/logs/frontend.
- Usar rota antiga como caminho oficial de segredo.
- Criar Auxiliar avançado sem runtime, Skill ou workflow declarado.
- Tratar Rotina como sinônimo de Auxiliar.
- Criar história de execução paralela ao Work Run canônico após sua implantação.
- Rodar SQL/alterar schema sem aprovação e inventário real.

## 11. Como novas IAs devem proceder
1. Ler SPEC-052 + SPEC-053 + esta SPEC + ADR-001/ADR-002 + UX-007.
2. Auxiliar = produto; runtime = Smith; Rotina = gatilho; Skill = procedimento; Work Run = execução.
3. Reusar serviços canônicos; nunca insert cru em `agents`.
4. Reusar Vault para segredos/conectores/HITL.
5. Não criar schema paralelo.
6. Sanitizar qualquer blueprint; nunca copiar segredo.
7. Planejar migração progressiva de `auxiliary_runs` para Work Run.

## 12. Checklist antes de criar um novo Auxiliar
- [ ] Tem `auxiliary_template` com `slug` único?
- [ ] Outcome e Skill estão definidos?
- [ ] Runtime necessário está declarado?
- [ ] Conectores e capabilities estão declarados?
- [ ] Blueprint sem segredos?
- [ ] Ações externas passam por Vault + approval executável?
- [ ] Há rotina somente quando houver gatilho/agendamento?
- [ ] Execuções convergem para Work Run?
- [ ] Sem motor paralelo?
- [ ] Há evals, custo e Admin Projection?

---

# Apêndice A — Guia histórico detalhado (41A.2)

## A1. Fluxo histórico de criação
1. **Agent técnico (experimental/sandbox)** — crie/teste um Agent/Subagent em **Admin → Empresas → Agents**.
2. **Publicar como template** — extrai um blueprint sanitizado e cria `auxiliary_templates`.
3. **Instalar por corretora** — instala `tenant_auxiliaries`; se blueprint, cria/vincula um Agent da corretora.
4. **Personalizar localmente** — documentos, tom, horários, integrações e permissões permanecem locais.
5. **Executar/Auditar** — execução pelo Smith; histórico legado em `auxiliary_runs`, com migração futura para Work Run.

## A2. Inteligência global × personalização local
- **Global:** prompts base, regras, playbooks, Skills, guardrails e estrutura curada/versionada.
- **Local:** documentos, dados, tom, horários, integrações, permissões, carteiras e contatos.
- Conhecimento sensível/local não é global por padrão.

## A3. Tipos de Auxiliar
- **global** — disponível a todas as corretoras;
- **privado** — exclusivo de tenant;
- **experimental/sandbox** — draft/inativo;
- **em preparação** — dependências incompletas.

## A4. Relação com RAG
- Blueprint/Skill pode declarar necessidade de conhecimento.
- Documentos globais e locais permanecem separados pela SPEC-052.
- Conhecimento sensível/local nunca é global automaticamente.

## A5. Relação com workflows e rotinas
- Workflow coordena fases.
- Agent/Subagent pode executar fases.
- Rotina apenas inicia um trabalho.
- Auxiliar pode combinar essas peças sem virar motor paralelo.

## A6. Decisão de runtime
- Tarefa fixa → `specific_executor`.
- Precisa de tools/MCP/RAG/memória → Smith Agent/Subagent ou Skill com tools.
- Processo com fases → workflow.
- Pedido recorrente → adicionar Rotina ao Auxiliar/Skill.

## A7. Como evitar duplicidade
- Instalação idempotente por `(company_id, slug)`.
- Agent global nunca compartilhado entre tenants.
- Work Run será a história universal após migração.

## A8. Segredos
- Sanitização profunda obrigatória.
- Vault é a autoridade.

---

# Apêndice B — Capability Matrix histórica

| Capacidade | Agent Orquestrador | SubAgent Especialista |
|---|---|---|
| Modelo | ✅ | ✅ |
| Prompt/persona | ✅ | ✅ |
| HTTP Tools | ✅ | ✅ |
| MCP | ✅ | ✅ |
| Memória/RAG | ✅ | ✅ |
| Segurança | ✅ | ✅ |
| Chat direto | ✅ | ⚠️ debug/treino |
| Widget público | ✅ | ❌ |
| WhatsApp direto | ✅ via Vault | ❌ |
| Especialistas próprios | ✅ | ❌ MVP |

O Tool Gateway e os Capability Packs da SPEC-053 passam a governar a exposição real dessas capacidades por trabalho.
