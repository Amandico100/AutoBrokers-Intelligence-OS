# SPEC-014 — Capability Registry, Knowledge OS & Poderes Reais do Smith (Fase C)

> Status: **APROVADA** (decisões travadas pelo Founder em 2026-06-23). Sucede a Fase B (SPEC-013, encerrada em `3d60932`).
> Princípio inviolável: **usar o que já existe no Smith; NÃO criar estrutura paralela; tudo nasce LIGADO em produção** (só com os guardrails que são parte do produto correto e da lei).
> Auditoria factual de suporte: [phase-c-capability-recon-audit](design/2026-06-claude-design/phase-c-capability-recon-audit.md).

## 1. Por que esta SPEC existe
A Fase C **não constrói motores novos** — a auditoria provou que ~80% já existe (busca web Tavily, Docling, InfoCap completo, Vault/conectores/aprovações/auditoria com UI, MCP servers+OAuth para Drive/Calendar/Slack/GitHub, RAG Qdrant/MinIO/rerank, memória, atendimento, WhatsApp). O que falta é **uma camada única de governança** que decida *quem usa o quê* e o ato de **ligar em produção**. Hoje as ferramentas são habilitadas por **flags soltas espalhadas** (`allow_web_search`, `tools_config`, `agent_http_tools`, `agent_mcp_connections`) — origem da bagunça e das duplicidades. O **Capability Registry** elimina isso.

## 2. Glossário (definições que NÃO podem se confundir)
- **Capability**: uma habilidade governável, identificada por `capability_key` (ex.: `platform.web.search`). É o que se autoriza/mede/cobra. **Não** é a implementação.
- **Connector**: implementação concreta de acesso a um serviço (InfoCap, Google Drive). Já existem via Vault/`connector_templates` e MCP servers internos.
- **Provider**: quem hospeda o serviço externo (CorpAPI/InfoCap, Google, Slack). Eventual Composio/Nango seria *um* provider — nunca a fonte de verdade.
- **Tenant Connection**: conexão da corretora a um connector (`tenant_connections`, com `encrypted_secret_ref` no Vault). **Reutilizada como está.**
- **Vault Secret Ref**: referência opaca ao segredo cifrado; **nunca** o segredo.
- **HTTP Tool / MCP Tool**: camadas de execução do Smith (`agent_http_tools`, `agent_mcp_connections/tools`). Continuam sendo o "braço" que roda a ação.
- **Skill (de negócio)**: fluxo concreto sobre capabilities/portais (ex.: "consultar apólice"). Produto, não infra.
- **Corridor (corredor)**: trilha de atendimento (entrada→identidade→apólice→decisão). Já existe.
- **Auxiliary**: agente-produto sobre o Smith que **declara** as capabilities que exige.
- **Source Agent / Tenant Instance**: autoria global no Studio vs instância da corretora (SPEC-013).
- **Entitlement**: direito de um tenant a uma capability (plano/limite/risco).
- **Approval**: autorização humana para uma ação sensível (`approval_requests`, já existe).
- **Usage Event**: registro de uso para FinOps/auditoria (reusa `usage`/`token_usage_logs`).

## 3. Arquitetura única (sem paralelo)
```
Source Agent (Studio) → Release imutável (SPEC-013)
        ↓
Capability Binding  — quais capability_keys aquele PAPEL de agente pode usar
        ↓
Tenant Entitlement / Tenant Connection (Vault EXISTENTE) — a corretora habilitou/conectou?
        ↓
Smith HTTP Tool / MCP Tool / Adapter EXISTENTE — execução real
        ↓
Serviço interno (RAG, memória, Docling) ou externo (InfoCap, Google, Z-API)
```
**Regra:** uma ferramenta **não** é liberada porque alguém colou URL/token/MCP no editor do agente. Ela é liberada por `capability_key` + binding + entitlement. O Registry **governa**; o Smith **executa**; o Vault **guarda segredo**. Nada disso é reescrito.

## 4. Modelo de dados (mínimo; reusa o existente)
**Novas tabelas (poucas):**
- `capabilities` — `capability_key` (PK textual), `name`, `category` (enum: `knowledge|productivity|research|sales|insurance_ops|communication|internal`), `owner` (`platform|tenant|operational`), `provider`, `risk` (`low|medium|high`), `requires_connection bool`, `requires_approval bool`, `cost_model jsonb`, `is_active`, `metadata jsonb`.
- `capability_bindings` — `capability_key` × `agent_role` (`core|attendance|auxiliary|subagent`) com `enabled`, `scope jsonb` (limites por papel). Define a **matriz de autorização**.
- `tenant_capability_entitlements` — `company_id` × `capability_key` com `enabled`, `limits jsonb`, `connection_id` (FK opcional → `tenant_connections`). Liga capability à conexão real.

**Reusados como estão (NÃO duplicar):** `tenant_connections`, `connector_templates`, `permission_grants`, `approval_requests`, `vault_audit_log`, `usage`/`token_usage_logs`, `agent_http_tools`, `agent_mcp_connections/tools`, `documents`, `agents`.
> Versionamento de capability: **não** criar `capability_versions` agora — o versionamento de agente já vem das releases SPEC-013. Histórico de uso vai em usage events.

## 5. Catálogo inicial de capabilities (congelado)
| capability_key | category | owner | risk | requires_connection | conn/approval |
|---|---|---|---|---|---|
| `knowledge.global.search` | knowledge | platform | low | não | — |
| `knowledge.tenant.search` | knowledge | tenant | low | não | — |
| `memory.company.read_write` | internal | tenant | low | não | — |
| `memory.user.read_write` | internal | tenant | low | não | — |
| `control_plane.read` | internal | platform | low | não | estado da corretora (read-only) |
| `platform.web.search` | research | platform | low | não | Tavily, chave AutoBrokers, custo→corretora |
| `platform.document.extract` | productivity | platform | low | não | Docling |
| `operational.infocap.policy_lookup.read` | insurance_ops | operational | high | sim | Vault InfoCap + auditoria |
| `operational.policy_evidence.read` | insurance_ops | operational | medium | sim | depende do lookup |
| `tenant.google_drive.read` | productivity | tenant | medium | sim | OAuth |
| `tenant.google_calendar.read_write` | productivity | tenant | medium | sim | OAuth + approval p/ escrita |
| `tenant.slack.read_write` | communication | tenant | medium | sim | OAuth + approval p/ envio |
| `tenant.notion.read_write` | productivity | tenant | medium | sim | OAuth/API + approval p/ escrita |
| `operational.whatsapp.send` | communication | operational | high | sim | consentimento + approval |
| `operational.portal.policy.read` | insurance_ops | operational | high | sim | Portal Browser + HITL |
| `operational.portal.billing.read` | insurance_ops | operational | high | sim | Portal Browser + HITL |
| `operational.portal.assistance.read` | insurance_ops | operational | high | sim | Portal Browser + HITL |
| `operational.portal.assistance.prepare` | insurance_ops | operational | high | sim | prepara (sem abrir) |
| `operational.portal.assistance.request` | insurance_ops | operational | high | sim | abre **com approval** |

## 6. Matriz rígida de autorização (nunca "todos usam tudo")
- **AutoBrokers Core**: `knowledge.global/tenant.search`, `memory.*`, `control_plane.read`, `platform.web.search`, `platform.document.extract`, conexões tenant **autorizadas**, `operational.infocap.policy_lookup.read` **com contexto + escopo + auditoria**. Sem portais/WhatsApp como ferramenta livre.
- **Even / Atendimento**: `knowledge.tenant.search`, `operational.infocap.policy_lookup.read` + `operational.policy_evidence.read` por caso, `platform.document.extract` (doc do segurado), corredores, handoff, `operational.whatsapp.send` e `operational.portal.*` **só via corredor + gates + approval**. **Sem navegação web aberta por padrão.**
- **Auxiliares**: **só** as capabilities que o contrato declara (mínimo). Ex.: pesquisa→`platform.web.search`; leitura de docs→`platform.document.extract`; follow-up→`operational.whatsapp.send` (com consentimento/approval/conexão); cobrança→conectores + permissões exigidas.
- **Subagentes**: herdam o subconjunto do agente pai, nunca mais.
- **Portal Admin (master)**: governa o catálogo, bindings, custo, risco, limites, health.
- **Dashboard corretora**: conecta as próprias contas (estilo ChatGPT) e habilita entitlements.

## 7. Política de segredo (inegociável)
Nenhum segredo em prompt, release, config de agente, RAG, logs ou frontend. Segredos só via Vault (`encrypted_secret_ref`). Se um dia Composio/Nango entrar, é **provider** atrás do Registry — AutoBrokers continua fonte de verdade de capability, tenant, custo, approval e auditoria.

## 8. Decisão Composio vs Nango vs direto — **DIRETO/INTERNO**
Travada. Evidência (devs/comparativos 2026): Composio é closed-source, **sem config por tenant nem validação de auth por cliente**, observabilidade fraca — péssimo p/ SaaS multi-tenant de seguros que já tem Vault/approval/audit/isolamento. Já temos MCP interno + OAuth p/ os apps-chave (Drive/Calendar/Slack/GitHub) e Vault p/ API-key (InfoCap/Quiver/Z-API/portais). Regra dos seniores: **construir vale quando a superfície é estreita/estável (3–5 serviços)** — é o nosso caso. **Nango** só reconsiderar se passarmos de ~10–15 apps SaaS (manutenção OAuth vira meio-FTE). Composio/Nango ficam como provider opcional **atrás do mesmo Registry**, sem virar estrutura paralela.

## 9. Knowledge OS (entra no C1)
Seed Pack Global AutoBrokers (conteúdo curado: o que é Core/Even/Auxiliar, capacidades, regras) · RAG global curado · RAG privado por corretora · memória com escopo company/user/case · regras de publicação/revisão/sensibilidade · evals essenciais (Core/Even/RAG). **Regra absoluta: RAG nunca confirma cobertura** — cobertura só com evidência estruturada (InfoCap/documento/portal).

## 10. Skills de negócio em Portais (entra no C2, no roadmap explícito)
Sobre o Portal Browser **existente** (sessão, SessionRef, Vault, HITL) — **sem novo browser automation**: consulta de apólice · status · cobrança/boleto · assistência/sinistro · preparação de abertura · abertura **com approval**.

## 11. Biblioteca de Auxiliares (entra no C2, no roadmap explícito)
Primeiros 5 globais robustos + capabilities exigidas: **pesquisa** (`platform.web.search`), **resumo** (`knowledge.tenant.search`+`memory`), **follow-up** (`operational.whatsapp.send`), **cobrança** (conectores+portal billing), **leitura de documentos** (`platform.document.extract`).

## 12. Critérios de "pronto para produção" por capability
Configuração · health-check · credencial (quando aplicável) · teste real · logs/auditoria · custo atribuído · limites · gates corretos · rollback · owner definido · integração efetiva com o Smith. **Quando os 11 estão verdes, está em produção — sem "etapas futuras".**

## 13. Fase C em EXATAMENTE 2 batches (escopo congelado)
### C1 — Capability Registry + Knowledge OS + Core poderoso LIGADO
Tabelas (`capabilities`/`capability_bindings`/`tenant_capability_entitlements`) + catálogo + matriz · Admin de Capabilities (Portal Admin, folded) · Conectores reorganizados/categorizados no Dashboard · binding Source Agent→capabilities · **Tavily ligado** (env+flag) p/ Core · **Docling** promovido a `platform.document.extract` (health) · **InfoCap** promovido a `operational.infocap.policy_lookup.read` reutilizável pelo Core (governado) · `control_plane.read` p/ o Core · Seed Pack Global + RAG curado + memória escopada · diagnóstico/FinOps por capability · evals essenciais. **Linha de chegada:** Core em produção usando web+docs+InfoCap+conhecimento+memória+estado; admin de capabilities; galeria categorizada. *(É um lançamento real do Core.)*
- Migrations: SPEC-014-01 (registry) + seed do catálogo/bindings. Testes: unit (registry/matriz/catálogo puros) + integração (endpoints) + aceite real (Core responde usando web/InfoCap). Exclusões: OAuth tenant (C2), auxiliares (C2), portais (C2).

### C2 — Conectores tenant OAuth ao vivo + Auxiliares + Skills de Portal
Connect OAuth no Dashboard (Drive/Calendar/Slack/GitHub — direto/interno) com token no Vault · usage/custo/limite/health por capability · permissões por agente/auxiliar · **5 Auxiliares robustos** · **Skills de Portal** sobre o Portal Browser existente · **WhatsApp/Z-API ao vivo** (consentimento+approval) · **InfoCap real da Resulta** (credencial). **Linha de chegada:** corretora conecta apps e usa; auxiliares instaláveis e funcionando; atendimento ponta a ponta em produção.
- Migrations: SPEC-014-02 (se necessário p/ usage/entitlement) . Testes: unit + integração + aceite real (conectar Drive, rodar auxiliar, abrir assistência com approval). Dependências honestas: conta Z-API paga, credencial InfoCap, client IDs OAuth Google/Slack.

## 14. Checklist única do MVP (atualizada)
```
[x] Fase B concluída (3d60932)
[ ] C1 — Capability Registry + Knowledge OS + Core ligado (produção)
[ ] C2 — Conectores tenant + Auxiliares + Skills de Portal (produção)
[ ] Skills de negócio em Portais (dentro de C2)
[ ] Knowledge OS (dentro de C1)
[ ] Biblioteca de Auxiliares (dentro de C2)
[ ] Z-API / 42X5C ao vivo (dentro de C2)
[ ] Portal Allianz + SessionRef ao vivo (dentro de C2)
[ ] Allianz Residencial Eletricista ponta a ponta (após C2)
[ ] Evals + FinOps + gate final de produção (transversal C1/C2)
```

## 15. O que NÃO fazer
Não criar segundo motor de agentes, segundo Vault, segundo RAG, segundo OCR, segunda busca web, segundo browser, segundo sistema de conectores. Não deixar nada "pausado p/ futuro". Não colar segredo/URL/MCP livre no editor. Não adotar Composio+Nango juntos. Não recriar InfoCap/Docling/Tavily.
