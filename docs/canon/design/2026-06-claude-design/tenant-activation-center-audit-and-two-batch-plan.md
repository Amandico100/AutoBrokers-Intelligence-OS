# Tenant Activation Center — Auditoria + Plano (2 batches)

> **READ-ONLY.** Nenhum código/migration/agente alterado. Auditoria fundamentada no repositório + Supabase canônico (`AutoBrokers Intelligence OS`, `dcajcvlzcjbmyapmklil`). Define como qualquer corretora nasce e ativa o produto, e os 2 batches de implementação.
> **Data:** 2026-06-21 · **Modelo:** Claude Opus 4.8 · base: `cdc9ccb`

## 0. Veredito sobre a análise do GPT
Concordo com os 4 pontos — todos **confirmados no código/DB**:
1. **Global disponível ≠ tenant ativado** — CONFIRMADO: não existe tabela de ativação de corredor por tenant; `loadAvailableCorridors` (inbound) traz todo corredor `scope=global, is_active=true` para qualquer company (`company_id is null OR =tenant`). Gap real.
2. **Dois agentes ambíguos da Resulta** — CONFIRMADO via MCP: `AutoBrokers Sandbox` (ativo, role/audience nulos) + `Atendimento AutoBrokers — Resulta` (attendance/insured_external, inativo).
3. **`resolveInsurerDispatchTarget` não ligado ao dispatch** — CONFIRMADO: uso só no módulo/testes.
4. **Portal pausado por credencial, não código** — CONFIRMADO (infra pronta; pendência = login AllianzNet válido).

E concordo que o próximo passo é **auditoria+plano**, não implementar Dashboard às cegas.

## 1. Mapa de fontes da verdade (confirmado)
| Domínio | Fonte canônica | Estrutura | Estado | Gap | Decisão |
|---|---|---|---|---|---|
| Company | `companies` | tabela | ok (Resulta `04b5cdbc`, active) | — | manter |
| Equipe/usuário | `users_v2` | tabela | ok | — | manter |
| **Chat Principal** | `agents` (`allow_direct_chat`, role `core`/legacy) | tabela | **Sandbox role nulo** | classificação | reclassificar p/ `agent_role='core'` |
| **Attendance Agent** | `agents` (`agent_role='attendance'`) | tabela | criado, **inativo** | ativação canônica | ativar via provisionamento |
| SubAgents | `agents` (`is_subagent`) | tabela | interno Smith | — | nunca exposto à corretora |
| Memória/RAG | `memory_*`, `documents`, Qdrant | gated | global=opt-in | RAG1+ | fora deste plano |
| Conhecimento global | RAG global curado | gated | opt-in | RAG1+ | fora |
| **Corredor global** | `corridor_templates` (scope=global) | tabela | ativo p/ todos | **sem ativação por tenant** | nova `tenant_corridors` |
| **Ativação por tenant** | — | **não existe** | — | **principal gap** | espelhar `tenant_auxiliaries` |
| Auxiliar global | `auxiliary_templates` | tabela | ok | — | padrão a copiar |
| Auxiliar instalado | `tenant_auxiliaries` | tabela | ok | — | padrão de referência |
| Portal global | `portal-global-catalog-seed` + connection_config | seed | ok (base_url global) | — | manter |
| Portal Account | `tenant_connections.connection_config` | jsonb | ok (por tenant) | — | manter |
| WhatsApp | `tenant_connections` + backend webhook | tabela/py | inbound real ok; outbound gated | provider real após pagamento | 42X5C |
| Handoff humano | `human_support_destinations` | tabela | ok | UI tenant | Batch 2 |
| Approval | `approval_requests` | tabela | ok | UI tenant | Batch 2 |
| Dispatch | `dispatch_packets` + builder | tabela | dry-run | **destino global não conectado** | Batch 1 (wire resolver) |
| Contatos globais | `insurer-contacts-global-seed` | seed | ok (12 seg.) | override por tenant | Batch 1/2 |
| Dashboard novo | `app/dashboard` + TenantAppShell | UI | parcial | telas de ativação | Batch 2 |
| Portal Admin | `app/admin/portal-browser` | UI | master-only | — | manter interno |

## 2. Diagnóstico dos agentes da Resulta (e modelo canônico)
- **`AutoBrokers Sandbox`**: criado pelo `bootstrap-tenant` (`allow_direct_chat=true`) como o agente de chat direto do smoke test. É, de fato, o **Chat Principal** — mas com `agent_role` nulo (legado). O `GET /api/agents` mostra agentes legados (sem role) + role `core` → por isso ele aparece como o chat. **Decisão:** reclassificar para `agent_role='core'` + nome/identidade próprios (não apagar; é o chat real). 
- **`Atendimento AutoBrokers — Resulta`**: `agent_role='attendance'`, `insured_external`, **inativo**. O runtime de atendimento seleciona estritamente `agent_role='attendance' AND is_active=true` (cases/reply/preflight/simulate-inbound). **Decisão:** ativar via provisionamento canônico (não no escuro).
- **Como impedir seleção ambígua:** (a) Chat = `agent_role='core'`; (b) Attendance = `agent_role='attendance'`; (c) `GET /api/agents` (chat) deve excluir `attendance` (já exclui por role) e parar de incluir `role nulo` depois que todos forem classificados; (d) runtime de atendimento já filtra por `attendance`. Risco atual: agente `role nulo` aparece no chat — resolvido ao reclassificar Sandbox→core.
- **Como nasce uma corretora nova:** estender o `bootstrap-tenant` para um **`provisionTenant(companyId)`** idempotente que cria **2 agentes a partir de blueprints globais** (`lib/admin/agent-blueprints.ts` já existe): 1 `core` (Chat Principal) + 1 `attendance` (Attendance Agent), ambos inativos até a corretora personalizar/ativar. Sem agente paralelo, sem cópia de runtime.

## 3. Modelo de ativação por tenant (a regra "GLOBAL DISPONÍVEL ≠ TENANT ATIVADO")
**Reusar o padrão de Auxiliares** (`auxiliary_templates` global + `tenant_auxiliaries` instalado). Propor a menor extensão canônica:
- Nova tabela **`tenant_corridors`** (espelha `tenant_auxiliaries`): `id, company_id, corridor_template_id, status ('active'|'paused'), installed_by, installed_at, settings jsonb`. RLS por `company_id`. 
- **Mudança de runtime:** `loadAvailableCorridors(companyId)` passa a trazer um corredor global **só se houver ativação** em `tenant_corridors` para aquele tenant (corredores `scope=tenant` continuam por `company_id`). 
- **Cuidado de migração (decisão do Founder):** isso muda comportamento — corretoras existentes (Resulta) precisam de **auto-ativação dos corredores-piloto** na migração para não quebrar. A migração deve: criar a tabela + ativar Allianz Residencial/Eletricista para a Resulta.
- Por que não é estrutura paralela: é o mesmo padrão já aprovado para Auxiliares; `corridor_templates` continua a fonte global única; `tenant_corridors` é só o "instalado/ativado".

## 4. Personalização por Dashboard (limites)
**Chat Principal (core):** nome, avatar, tom, apresentação, idioma, preferências de resposta, conhecimento privado, regras operacionais (dentro de limites). 
**Attendance Agent:** nome, avatar, voz, tom, mensagens de abertura/fechamento, horários, handoff, **corredores ativos**, canais conectados. 
**Nunca editável pela corretora:** isolamento de tenant, gates, regras de cobertura, Vault/segredos, approval obrigatória, Skills globais críticas, ferramentas sensíveis, subagents, flags globais, políticas de segurança. (Edição via campos já existentes em `agents`: name, avatar_url, agent_system_prompt, llm_*, security_settings — sem expor o que é sensível.)

## 5. Dashboard novo — mapa de telas (Batch 2)
Sidebar (DS-001): **AutoBrokers · Atendimentos · Auxiliares · Personalização**. 
Em **Personalização** (lista → detalhe, mobile-first): Dados da corretora · Equipe · Aprovadores · **Chat Principal** · **Agente de Atendimento** · **WhatsApp** · **Seguradoras** (→ Portais/Corredores/Contatos) · **Portais conectados** · **Corredores** (ativar/pausar) · **Auxiliares** (galeria/instalados) · **Conhecimento** · **Handoff humano** · **Checklist de ativação**. Cada tela: para que serve · dados que edita · estrutura Smith que alimenta · permissões · global vs privado · o que exige approval · o que é read-only.

## 6. Portal no Dashboard (corretora)
Fluxo: Seguradoras → Allianz → Portais → **Conectar AllianzNet** → Login Assistido (CAPTCHA/2FA humano) → sessão saudável → reautenticar quando necessário. A corretora **não vê** Browserbase/Portal Lab/Vault/SessionRef/Skill Factory/Relay Sandbox. **Portal de prestador (abraseuatendimento)** = **uma conexão serve várias seguradoras** (modelar como Portal Account de prestador, não por seguradora). Portal Admin continua master/interno.

## 7. WhatsApp / pré-requisitos do 42X5C
- **Antes do canary inbound:** Attendance Agent canônico **ativo**; corredor ativado por tenant; webhook + secret configurados; Z-API conectada.
- **Antes do outbound canary:** consentimento do número de teste; dispatch target (wire do resolver); approval + HITL; `external_send_authorized`.
- **Antes do piloto restrito:** dashboard operacional mínimo (casos/handoff/kill switch); logs sanitizados; outbox/retry (hoje idempotência ok, fila durável = pós-piloto).
- **Pós-piloto:** fila durável, override de contatos por tenant, métricas.

## 8. Plano em 2 batches (não executar agora)
### Batch Tenant Activation 1 — Modelo canônico + provisionamento + ativação + dispatch
- **Objetivo:** tornar canônico Chat Principal (`core`) + Attendance (`attendance`) e a ativação por tenant; ligar contatos globais ao dispatch.
- **Escopo:** (a) `provisionTenant(companyId)` idempotente (blueprints → core+attendance); (b) reclassificar Sandbox→core (migração de dados, sem apagar); (c) **migration `tenant_corridors`** + verify + rollback + ajuste de `loadAvailableCorridors`; (d) auto-ativar corredores-piloto da Resulta; (e) wire `resolveInsurerDispatchTarget` no builder de dispatch packet (gated/dry-run). 
- **Banco:** nova `tenant_corridors` (migration versionada, RLS, não aplicada automaticamente). 
- **Testes:** provisionamento idempotente; runtime só usa corredor ativado; chat exclui attendance; dispatch resolve destino global; nada real enviado. 
- **Aceite:** corretora nova nasce com 2 agentes; corredor global só opera se ativado; Resulta-piloto ativada; dispatch usa contatos globais; gates `false`. 
- **Relação:** desbloqueia 42X5C (attendance ativo + corredor ativado); não toca Portal/RAG/Skills.

### Batch Tenant Activation 2 — Dashboard da corretora
- **Objetivo:** a corretora opera tudo no próprio painel (DS-001, mobile-first).
- **Escopo:** telas de §5 (Personalização: dados, equipe, aprovadores, Chat Principal, Attendance, WhatsApp, Seguradoras→Portais/Corredores/Contatos, Auxiliares, Conhecimento, Handoff, Checklist de readiness). Reusa rotas/resolvers existentes; sem duplicar dados.
- **Banco:** idealmente nenhum (usa estruturas do Batch 1). 
- **Testes:** isolamento tenant; corretora não vê segredo/engenharia; ativar/pausar corredor; conectar portal; checklist. 
- **Aceite:** Resulta entra, personaliza, ativa e vê readiness sem telas técnicas. 
- **Relação:** consome Batch 1; Portal usa Login Assistido; WhatsApp usa 42X5C.

## 9. Decisões que precisam do Founder
1. **Nome/identidade** do Chat Principal e do Attendance Agent da Resulta (para personalização inicial).
2. **Reclassificar `AutoBrokers Sandbox` → `core`** (manter como Chat Principal) — confirmar (não apagar nada).
3. **Ativação por tenant** via nova tabela `tenant_corridors` (espelhando Auxiliares) — confirmar o modelo (vs. usar `permission_grants`/connection_config). Recomendo `tenant_corridors` por clareza.
4. **Ordem:** Batch 1 (canônico/ativação) antes do 42X5C; Batch 2 (Dashboard) pode vir antes ou depois do 42X5C.
5. **LGPD/consentimento** do piloto Resulta para o canary WhatsApp (quando pagar Z-API).

## 10. Riscos
- Mudar `loadAvailableCorridors` sem auto-ativar a Resulta quebraria o piloto → a migração deve ativar os corredores-piloto.
- Reclassificar agentes precisa preservar conversas/histórico ligados ao agente atual.
- Não declarar WhatsApp/produção pronto enquanto attendance inativo + corredor não ativado por tenant.

## 11. Observação operacional (Portal)
Se a sessão Browserbase do canary AllianzNet ficou `Running`, **Stop** no console Browserbase. Portal segue pausado até a Resulta fornecer login/senha AllianzNet válidos. Nenhum batch de Portal necessário agora.
