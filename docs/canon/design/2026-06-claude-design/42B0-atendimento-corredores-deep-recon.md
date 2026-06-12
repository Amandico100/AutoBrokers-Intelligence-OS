# 42B0 — Atendimento & Corredores Deep Recon (READ-ONLY)

> **Status:** auditoria profunda · **READ-ONLY** (nenhum código/SQL/schema/RAG/prompt/agente alterado, sem deploy) · **sem cópia bruta do Agent OS**, **sem PII de conversas reais**, sem segredo.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main
> **Objetivo:** entender o Atendimento ponta-a-ponta (legado Agent OS + Smith atual + canon) e definir **como** construir Atendimento + Corredores **sem motor paralelo**, antes de qualquer schema/UI/runtime.

---

## 0. Sumário executivo

O Atendimento **não** é "uma conversa de WhatsApp" nem RAG. É **estado + workflow estruturado**. O Agent OS legado já tem uma arquitetura de corredores **extraordinariamente madura** (modelo de ~30 seções, contrato mínimo executável de ~22 campos, 11 estados de readiness, dispatch packet, guardrails, golden tests, separação canal-cliente×canal-execução, seleção de corredor/subcorredor) — mas é **fonte de domínio curada**, não código pronto (PRD §8.3). O Smith atual já oferece **tudo que o motor precisa** (LangGraph, Context Package, RAG, MemoryService, tools, **Vault/HITL `approval_requests`**, `conversations`/`messages`, `agent_delegations`).

**Decisão central:** **Corredor = conhecimento estruturado** (curado do legado, sem PII), executado **dentro do Smith** (Attendance agent + LangGraph + Context Package), com **HITL via Vault** e **dispatch packet** estruturado. O primeiro slice é **Allianz / Residencial / WhatsApp / Eletricista / dry-run / HITL** (eletricista é o subcorredor mais validado no legado).

---

## 1. O que é "Atendimento" no AutoBrokers (definições)

| Conceito | Definição | Audiência | Camada |
|---|---|---|---|
| **AutoBrokers Core** | chat interno da corretora (orienta/coordena) | corretor/gestor/operador | blueprint (42A3A) |
| **Attendance Agent** | agente que conduz o atendimento ao segurado dentro de um corredor | segurado | blueprint (42A4) + estruturado |
| **Caso de atendimento** | **entidade central**: representa o problema do segurado (estado, status, slots) | — | **schema/estado** |
| **Conversa** | mensagens cliente/operador/agente (canal do cliente) | segurado/operador | reuse `conversations`/`messages` |
| **Corredor** | workflow estruturado p/ seguradora×ramo×canal×serviço (fases/slots/ações/handoff) | — | **estruturado** (não RAG) |
| **Subcorredor** | especialização (eletricista, encanador, chaveiro, eletrodoméstico, desentupimento) | — | **estruturado** |
| **Skill** | unidade de raciocínio/decisão (ex.: selecionar corredor, verificar prontidão) | — | runtime/tool |
| **Tool/Conector** | executa ação técnica (WhatsApp, portal) via Vault | — | tool + Vault |
| **Auxiliar** | capacidade instalável (resumo, follow-up) | operador | produto (42A5) |
| **HITL** | aprovação humana antes de ação externa | humano | Vault `approval_requests` |
| **RAG** | conhecimento textual de apoio (condições, explicações) | — | apoio (não motor) |

> **Regra (ADR-003 §3):** Core ≠ Attendance. O Core ajuda o time; o Attendance lida com o segurado dentro de um corredor.

---

## 2. Estrutura ponta-a-ponta recomendada

Camadas (o corredor é **uma parte**, não o todo):

```
Canal (WhatsApp / dashboard / futuro portal-webchat)
 → Caso de Atendimento (entidade central: estado, status, prioridade)
 → Conversa (reuse conversations/messages — espelho do canal do cliente)
 → Intake / Entrada (intenção, canal, urgência, segurado, produto, dados mínimos)
 → Seleção de Corredor/Subcorredor (tipo → ramo → seguradora real → canal → registry → status)
 → Corredor (fases, slots, bloqueios, ações permitidas/proibidas, handoff)
 → Subcorredor (eletricista/encanador/chaveiro/eletrodoméstico/desentupimento)
 → Dispatch Packet (pacote de acionamento estruturado, idempotencyKey, missingData vazio p/ auto)
 → HITL / Aprovação (Vault approval_requests) ANTES de qualquer ação externa
 → Canal de execução (WhatsApp seguradora / 0800 / portal / browser — futuro)
 → Acompanhamento (status, retorno real: protocolo/prestador/previsão — nunca inventar)
 → Encerramento (resumo, resultado, pendências)
 → Logs / Evals / Memória (observabilidade + case memory futura)
```

**Fases canônicas do atendimento** (ADR-003 §8 + legado): entrada → entendimento → coleta/consolidação → identificação → apólice/elegibilidade → classificação → decisão → preparação do acionamento → corredor/subcorredor → acionamento assistido → captura de retorno → comunicação ao cliente → acompanhamento → handoff → encerramento → aprendizado.

**Separação de canais (legado, mandatória):** **canal_cliente** (linguagem humana, poucas perguntas, sem bastidor) × **canal_execucao** (resposta objetiva à seguradora, opção exata de menu, sem emoção). Misturar os dois é guardrail violado.

---

## 3. O que é estrutura × RAG × blueprint × tool × memória

| Conteúdo legado | Vira | Porquê |
|---|---|---|
| MODELO_DE_CORREDOR, CONTRATO_MINIMO, REGISTRY, STATUS, slots, fases, Action Engine, dispatch packet | **Estruturado** (schema/estado/registry) | é processo/estado, não texto consultável (SPEC-004 §4.5) |
| Guardrails (NO_AUTO_PROMOTION, QUARANTINE, severidades), Action Safety | **Blueprint do Attendance + regras estruturadas** | comportamento/limites, não RAG |
| 00_CONSTITUICAO, 01_ORQUESTRADOR, 02_RUNTIME_CONVERSACIONAL, 04_CONVERSA_COM_CLIENTE | **Blueprint** (Core/Attendance) | identidade/voz/raciocínio |
| Condições gerais, FLUXO_WHATSAPP, MENSAGENS_RASCUNHO, explicações longas | **RAG curado (apoio)** | texto longo consultável p/ explicar — **não** motor do corredor |
| Credenciais/portais | **Vault + tool/conector** | segredo nunca em prompt/RAG (ADR-002 §18) |
| Histórico/aprendizado de caso | **Memory** (futuro, curado) | continuidade, não verdade absoluta |
| Intake bruto (conversas reais, apólices, ACESSOS INFOCAP) | **Fonte de curadoria** (slots/golden), **NUNCA RAG bruto** | PII/credencial (ADR-002 §13, PRD §6.5) |
| 14_LEGADO_ASSIMILADO, 15_PROMPTS_PARA_CODEX, 99_PLANOS | **Descartar/não migrar agora** | ruído |

---

## 4. Como usar o Smith sem criar motor paralelo

| Necessidade do Atendimento | Reaproveitar no Smith |
|---|---|
| Orquestração do corredor (fases/decisão) | **LangGraph** (`backend/app/agents/graph.py`) — Attendance como agente; subcorredor via skill/SubAgent |
| Papel/limites do Attendance | **Context Package** (`agent_role=attendance`, 42A6) + blueprint (42A4) |
| Especialistas (apólice, seguradora) | **`agent_delegations`** (orchestrator→subagent) |
| Conversa/canal do cliente | **`conversations`/`messages`** (já existem) |
| Aprovação de ação externa (dispatch/WhatsApp) | **Vault `approval_requests` + `vault_audit_log`** (HITL pronto) |
| Canal WhatsApp | **`integrations`** + `whatsapp_service` (dry-run capável) |
| Conhecimento de apoio (condições gerais) | **RAG** (`SearchService`, isolado por tenant) |
| Memória de caso (futuro) | **MemoryService** + tabelas de memória |
| Observabilidade | **`conversation_logs`** (+ diagnostics/evals novos) |

**Não criar:** segundo runtime de chat, segundo RAG, segundo motor de Auxiliares, n8n como cérebro paralelo (guardrail do legado).

---

## 5. Primeiro slice MVP (confirmado)

**Allianz / Assistência Residencial / WhatsApp / Eletricista / dry-run / HITL.**

**Por que é o melhor primeiro slice:**
- **Eletricista** é o subcorredor **mais validado** por conversas reais no legado (`mapped_from_real_conversations`).
- Fluxo curto e demonstrável; risco baixo (dry-run/HITL).
- Usa o que já existe (Core, conversations, Vault/HITL, WhatsApp dry-run).
- Prova a tese: **"a corretora transforma uma solicitação de assistência residencial em um caso estruturado, segue um corredor, coleta dados (slots), prepara acionamento (dispatch packet) e escala/aprova ação externa (HITL)."**

**Fora do slice:** envio WhatsApp real automático; portal/browser real; InfoCap real obrigatório; outros subcorredores/seguradoras.

---

## 6. Entidades mínimas necessárias (reuse × novo)

> Recomendação conceitual — **SQL só em batch futuro controlado pelo Architect** (sem schema agora).

**Reaproveitar (sem tabela nova):**
- `conversations` / `messages` — espelho do canal do cliente.
- `approval_requests` + `vault_audit_log` — HITL do dispatch/ação externa.
- `integrations` — canal WhatsApp (provider/agent_id/dry-run).
- `agent_delegations` — Attendance ↔ SubAgent especialista.
- `conversation_logs` — observabilidade base.

**Criar (mínimo, futuro):**
- **`attendance_cases`** — estado central do caso (id, company_id, customer/contact, channel, status, priority, intent, insurer, service_type, assigned_*, summary, risk_level, handoff_required, conversation_id, metadata).
- **`corridor_templates`** — registry de corredor/subcorredor + readiness (corridorKey, insurerKey, lineKind, macroService, subcorridorKeys, statusDocumental, statusOperacional, channelRef, source_of_truth, golden_path). **Estruturado, não RAG.**
- **`corridor_runs`** — instância do corredor por caso (case_id, corridor_template_id, phase, **slots jsonb** preenchidos/faltantes, status, next_step, diagnostics).
- **`dispatch_packets`** — pacote de acionamento estruturado (case_id, corridor_run_id, payload jsonb, idempotency_key, missing_data, approval_request_id, status).

**Não precisa de tabela própria agora:** slots (jsonb em `corridor_runs`), dossiê/handoff (status + jsonb em `attendance_cases`), `attendance_messages` (reusar `messages`).

---

## 7. Dashboard necessário (mínimo MVP)

Reusar padrões existentes (patterns + conversations/messages). Páginas hoje **stub** (`atendimentos/{fila,casos,conversas,segurados}`) viram funcionais:
- **Fila** — lista de casos (status, prioridade, seguradora, serviço, último update).
- **Caso** — dados do segurado/caso, **fase do corredor**, **slots preenchidos × faltantes**, **próximo passo**, risco/handoff.
- **Conversa espelhada** — mensagens (canal do cliente).
- **Botões de ação:** preparar resposta · pedir dado · gerar dispatch packet · solicitar aprovação (HITL) · marcar handoff · encerrar.

Mobile-first, em camadas (Fila → Caso → Conversa → Dados → Ação), sem dashboard denso (ADR-003 §41-42).

---

## 8. WhatsApp e canais (fluxo MVP)

- **Entrada:** real **ou** simulada → **espelhada no dashboard** (conversa do caso).
- **Resposta:** sempre **draft** (rascunho) primeiro.
- **Envio real:** **bloqueado por padrão**; só via **`approval_request`** (HITL) + dry-run.
- **Z-API/Evolution:** atrás de `integrations` + `whatsapp_service` (abstração de provider — ADR-003 §33).
- **Vault:** governa credencial do canal; segredo nunca exposto.
- **canal_cliente × canal_execucao:** o WhatsApp do segurado (cliente) é distinto do WhatsApp/menu da seguradora (execução) — o dispatch packet alimenta o canal de execução com **opção exata de menu**, nunca emoção.

---

## 9. InfoCap / apólices / coberturas (MVP sem integração completa)

- **MVP:** dados **manuais** e/ou **upload de apólice** + **RAG tenant** (condições gerais curadas). **Sem** InfoCap real obrigatório.
- **Futuro:** conector **read-only** (Vault) p/ leitura assistida (ADR-002 §34) — `ACESSOS API INFOCAP.txt` é **credencial** (Vault, nunca repo/RAG).
- **Guardrail:** **nunca prometer cobertura sem fonte**; sem fonte confiável → **handoff humano** + linguagem "vou verificar" (ADR-003 §13/§48).

---

## 10. Browser / portais / 0800 (MVP)

- **Não automatizar real ainda** (ausente no código; correto p/ MVP — ADR-002 §25).
- **Preparar estrutura de canal:** o corredor registra **canal de execução recomendado** (whatsapp/portal/telefone) e gera **dispatch packet**; ação fica em **HITL**.
- **Futuro:** tool **Browserbase/Stagehand/Skyvern** como Tool Executor atrás de contrato + Vault + HITL (SPEC-004 §3.6, ROADMAP fase 9).

---

## 11. Corredor Allianz Residencial — inventário do legado (p/ a SPEC 42B1/42B2)

**Disponível e maduro no Agent OS** (`07_CORREDORES/assistencia-residencial/whatsapp/allianz/`):
- **Pacote:** README, FLUXO_WHATSAPP_SEGURADORA, MATRIZ_DADOS_PERGUNTAS_E_ORIGENS, CAPTURA_PROTOCOLO_PRESTADOR_PREVISAO, MENSAGENS_RASCUNHO, LACUNAS_E_RISCOS, TESTES_GOLDEN, DIAGNOSTICS_REGISTRY.
- **Subcorredores (5):** **ELETRICISTA** (mais validado), **ENCANADOR**, **CHAVEIRO_RESIDENCIAL**, **DESENTUPIMENTO_E_OUTROS**, **ELETRODOMESTICOS** — cada um com use-case, **slots por origem** (cliente/apólice/dashboard/seguradora), perguntas mínimas, guardrails (quando NÃO usar), ações permitidas/proibidas, captura de retorno.
- **Governança:** MODELO_DE_CORREDOR, REGISTRY_MASTER, STATUS_DOS_CORREDORES, CONTRATO_MINIMO_DO_CORREDOR_EXECUTAVEL, CONTRATO_DASHBOARD_CORREDORES_RUNTIME, MATRIZ_DE_DECISAO_EXECUCAO_CANAL, POLITICA_DE_PREFLIGHT_SESSAO_E_CHALLENGE, POLITICA_DE_STATUS_READINESS_E_HOMOLOGACAO, SKILLS_E_ADAPTERS_DE_EXECUCAO.

**Recomendação p/ 42B2 (Eletricista):** curar (sem cópia bruta, sem PII) → slots (electricalIssueType, outageScope, affectedRoom, riskLevel, schedulePreference + policyholder/policyNumber/insuredLocation), perguntas mínimas (uma por vez), guardrails (eletrodoméstico→outro subcorredor; risco elétrico→dossiê; rede externa→não é papel), ações (navegar menu Allianz, resumo p/ especialista, capturar protocolo/prestador/previsão), dispatch packet, golden tests, **readiness ≤ controlled_real_test** (nunca production no MVP).

---

## 12. Riscos

| Risco | Mitigação |
|---|---|
| Corredor como **prompt solto** | corredor = estruturado (schema/estado), não prompt nem RAG |
| **Cópia bruta** do Agent OS | curar → estruturado/blueprint/RAG; nunca colar cru |
| **Intake/PII no RAG** | intake é fonte de curadoria; nunca RAG bruto; sem PII no repo |
| **Prometer cobertura** | guardrail: sem fonte → "vou verificar" + handoff |
| **Fingir acionamento** | só comunicar de retorno real; nunca inventar protocolo/prestador |
| **Misturar Core × Attendance** | papéis separados (Context Package `role`); 42A4 |
| **Motor paralelo** | reusar LangGraph/Vault/conversations; sem segundo runtime |
| **Schema amplo demais** | 4 tabelas mínimas + jsonb; SQL controlado pelo Architect |
| **WhatsApp/portal real cedo** | dry-run/HITL no MVP; real é fase posterior |
| **Falta de evals** | golden tests do corredor (42B7) antes de live test |
| **Promover status sem homologação** | NO_AUTO_PROMOTION; readiness ≤ controlled_real_test |
| **Escala multi-tenant** | tudo por `company_id`; isolamento (ADR-002 §17) |

---

## 13. Plano de execução (sequência recomendada)

| Batch | Objetivo | Tipo |
|---|---|---|
| **42A4** | Attendance Boundary Blueprint v1 (separar do Core; papel/limites) | doc → seed |
| **42B1** | Atendimento Runtime Architecture SPEC (entidades/estado/fases/reuse Smith) | SPEC |
| **42B2** | Allianz Residencial **Eletricista** Corredor SPEC (estruturado, curado, sem PII) | SPEC |
| **42B3** | SQL mínimo (`attendance_cases`/`corridor_templates`/`corridor_runs`/`dispatch_packets`) | SQL controlado (Architect) |
| **42B4** | UI Fila/Casos/Conversas MVP (reusa conversations/messages + patterns) | Web |
| **42B5** | Runtime assistido do corredor (Attendance agent + LangGraph + Context Package; HITL) | API |
| **42B6** | WhatsApp dry-run/HITL wiring (espelho + draft + approval) | API/Web |
| **42B7** | Golden tests do corredor (evals) | QA |
| **41C.2C** | Knowledge mínimo curado (apoio: condições gerais) | API/curadoria |
| **43MVP** | E2E acceptance (slice completo + golden) | QA |

**Dependências:** 42A4 antes/junto de 42B5; 42B1→42B2→42B3→42B4/42B5; rodar **CORE-REGRESSION-001** a cada batch de runtime.

**Próximo batch recomendado:** **42A4 (Attendance Blueprint)** + **42B1 (Atendimento Runtime Architecture SPEC)**.

---

> **READ-ONLY:** este batch não alterou `app/`, `backend/`, `lib/`, schema, SQL, migrations, prompts, RAG, memória ou agentes; não copiou conteúdo bruto do Agent OS nem PII do intake — apenas criou este relatório. Sem deploy.
