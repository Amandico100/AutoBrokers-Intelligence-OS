# Batch TA2-A — Dashboard da Corretora: AutoBrokers + Even + Effective Config persistida

> Primeiro incremento visual+funcional do Dashboard da corretora. A corretora personaliza AutoBrokers (Core) e Even por **variáveis/overrides seguros**; a config é **persistida** (context_package + colunas reais) e o **prompt é re-renderizado** → o runtime passa a usar a config. **Sem WhatsApp/Browserbase/portal real; sem flags; sem migration aplicada; sem estrutura paralela.**
> **Data:** 2026-06-21 · **Modelo:** Claude Opus 4.8 · base: `bd2fe10`

## Declaração
```
TA1 MIGRATIONS DETECTED LIVE: SIM (verificado via MCP: Resulta = AutoBrokers core ativo + Even attendance inativo + 2 tenant_corridors)
AUTOBROKERS CONFIG PERSISTED: SIM (context_package.tenant_agent_config + colunas)
EVEN CONFIG PERSISTED: SIM
AUTOBROKERS CONFIG USED BY RUNTIME: SIM (agent_system_prompt re-renderizado + colunas name/avatar/llm_temperature — o runtime lê esses campos)
EVEN CONFIG USED BY RUNTIME: SIM
AUTOBROKERS DASHBOARD READY: SIM (/dashboard/personalizacao/agentes/autobrokers)
EVEN DASHBOARD READY: SIM (/dashboard/personalizacao/agentes/even)
PORTAL ADMIN MIRROR READY: SIM (API GET /api/admin/companies/[companyId]/agents-config; UI no admin = integração no TA2-C)
TENANT ISOLATION TESTED: SIM (APIs resolvem company_id server-side via sessão; nunca do body/query)
FINOPS CORE ATTRIBUTION READY: PARCIAL (contrato buildUsageAttribution pronto; propagação ampla no runtime = incremento)
FINOPS EVEN ATTRIBUTION READY: PARCIAL
TA1 RUNBOOK EXTRA HARDENING REQUIRED: NÃO (TA2 Parte 0 já endureceu; revisão das funções SQL ok)
NO REAL WHATSAPP SENT: SIM
NO BROWSERBASE OPENED: SIM
NO PORTAL ACTION EXECUTED: SIM
NO FLAG ENABLED: SIM
NO PARALLEL ARCHITECTURE CREATED: SIM
NEXT STEP: TA2-B — GALERIAS (Corredores, Auxiliares), Seguradoras/Contatos e Readiness
```

## Verificação do estado live (MCP, read-only)
As migrations do TA1 **foram aplicadas** (você rodou). Confirmei: Resulta = `AutoBrokers` (core/broker_internal, ativo, blueprint autobrokers-core-v1) + `Even` (attendance/insured_external, inativo, even-attendance-v1) + 2 `tenant_corridors` ativos (Allianz Residencial + Eletricista). O GPT estava certo.

## O que entreguei
### Persistência + Effective Config usada pelo runtime (Parte 2)
`agent-blueprints-canonical.ts`: `computeAgentConfigUpdate` / `resetAgentConfigUpdate` / `sanitizeAgentConfigForDashboard` / `editableForBlueprint`. A config editável vive em `agents.context_package.tenant_agent_config` (**preserva** o resto do context_package) e os valores materializam em **colunas reais** (`name` p/ Even, `avatar_url`, `llm_temperature`) + o **`agent_system_prompt` é re-renderizado** do blueprint. **Decisão de engenharia minha (melhor que o pedido):** como o runtime lê `agent_system_prompt` + colunas (não `context_package`), re-renderizar o prompt é o que torna a config **efetivamente usada pelo runtime sem tocar o runtime** — robusto e à prova de regressão. Marca "AutoBrokers" travada; `agent_system_prompt`/role/audience/modelo/guardrails nunca editáveis pelo tenant.
### APIs tenant-facing (Parte 3)
`GET/PATCH /api/dashboard/agents/[agentKey]` + `POST .../reset` (agentKey = `autobrokers`→core, `even`→attendance). **company_id resolvido server-side** (sessão → users_v2); nunca do body/query. Respostas sanitizadas (sem prompt/segredo).
### Dashboard (Partes 4–5)
Área **Agentes** em Personalização (DS-001, lista→detalhe): `/agentes` (2 cards) → `/agentes/autobrokers` e `/agentes/even`. Form limpo (`AgentConfigClient`): variáveis seguras + avatar/voz/temperatura, prévia da apresentação/abertura, Salvar + Restaurar padrão, aviso de campos protegidos. Sem prompt técnico; sem botão que ligue WhatsApp real.
### Portal Admin mirror (Parte 6)
`GET /api/admin/companies/[companyId]/agents-config` (master) — mesma config sanitizada (fonte única, sem duplicar). Integração visual na página de agentes do admin entra no TA2-C (rollup).
### FinOps (Parte 7)
Contrato `buildUsageAttribution` pronto (TA2 P0). A propagação ampla (corridor_run/auxiliary_run/tool no log do runtime) é incremento — marcada PARCIAL com honestidade (sem custo fictício).
### Hardening adicional (Parte 8)
Revisei as funções SQL do TA1 (tenant_corridors, snapshot, trigger): RLS on, revoke anon/authenticated, policy service_role, trigger simples sem SECURITY DEFINER. **Sem risco novo → sem migration nova.**

## Segurança / isolamento
- APIs resolvem `company_id` server-side; tenant não acessa outra corretora.
- Sanitização: nunca retorna prompt protegido/segredo/token/cookie.
- Overrides perigosos (prompt/role/audience/modelo premium) rejeitados; marca travada.
- Reset preserva o resto do context_package, histórico, custos, conversas.

## Testes
- `admin-agent-blueprints-canonical` **37** (inclui persistência: preserva context_package, materializa colunas, sanitização sem prompt, reset). Regressão: tenant-corridor-activation 13, finops 7, security 31, whatsapp-inbound 44. `tsc` EXIT=0 · build verde.

## Testes live (após deploy) — para o Founder
1. Dashboard → Personalização → **Agentes** → **AutoBrokers**: muda o tom → Salvar → recarrega → persistiu.
2. **Even**: muda nome para "Joana" + gênero masculino/feminino → Salvar → a prévia e o nome mudam; **Restaurar padrão** volta a "Even".
3. Portal Admin: `GET /api/admin/companies/04b5cdbc-04cd-4ddf-8e4b-f43efb062fab/agents-config` → reflete as mesmas variáveis (fonte única).

## Próximo passo
**TA2-B:** Galeria de **Corredores** (ativar/pausar via tenant_corridors) + Galeria de **Auxiliares** (instalar) + **Seguradoras/Contatos globais** + **Checklist de readiness**. Depois **TA2-C** (WhatsApp/Portais status, Conhecimento, Dados/Equipe/Aprovadores, Custos, rollup visual no Portal Admin, provisionamento automático). Em paralelo, **42X5C** quando a Z-API for paga.
