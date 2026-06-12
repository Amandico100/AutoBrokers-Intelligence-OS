# 43M0 — AutoBrokers MVP Gap Audit & Execution Plan (READ-ONLY)

> **Status:** auditoria estratégica/técnica · **READ-ONLY** (nenhum código/SQL/schema/RAG/prompt/runtime/Supabase alterado, sem deploy) · alinhado a PRD-001, ROADMAP-001, ADR-001/002/003, SPEC-002/003/004 e à série 42A.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main
> **Objetivo:** mapear gaps do MVP completo e definir a sequência de execução, preservando o Smith.

---

## 0. Sumário executivo

A fundação do **chat principal (Core)** está sólida: blueprint v1, Context Package runtime, contrato de Auxiliar e Core auxiliary awareness — tudo sobre o runtime Smith preservado. Surpresa positiva da auditoria: **Vault/Conectores já é um MVP funcional** (tabelas, rotas `/api/vault/*` e UI de catálogo + aprovações/HITL + auditoria). **Web search** já funciona (Tavily, gated).

Os **gaps reais** para o MVP completo são, em ordem de impacto:
1. **Atendimento e Corredores** — inexistentes em runtime (UI só placeholder; sem tabelas de caso/corredor).
2. **Core Blueprint** aplicado só no **Sandbox/RAFAEL** (não há seed amplo nem checklist de regressão).
3. **Global Knowledge** ainda desligado (coleção não criada; `include_global=False`).
4. **Auxiliares de teste** podem precisar de cleanup/hide antes da demo.
5. **Browser/portais** ausentes (correto para MVP — só design + HITL).

**MVP slice recomendado:** Core organiza um atendimento de **assistência residencial Allianz** → cria/mostra **caso na fila** → segue **corredor estruturado** → **prepara** mensagem/acionamento → **HITL** (Vault) para qualquer ação externa → **logs/auditoria**. Tudo **assistido/dry-run**, sem envio real (ADR-003 §21, ROADMAP fase 8).

---

## 1. Core / Chat Principal

**Pronto:** caminho único Smith FastAPI/LangGraph (`backend/app/agents/graph.py::_build_initial_state`) com: blueprint via `agent_system_prompt`, **Context Package** (`role/audience/context_package`, 42A6), **RAG prefetch** (41C.1.2 + rescue/fallback 41C.1.3/.4), **Core auxiliary awareness** (42A7/.1), memória (`MemoryService`), tools HTTP/MCP/UCP/SubAgent, Vault/HITL para ação sensível.

**Falta p/ MVP:** (a) blueprint aplicado só no AutoBrokers Sandbox da RAFAEL — definir como o Core nasce por corretora (seed `role=core` no agente principal); (b) **checklist de regressão fixo** (hoje inexistente); (c) políticas em `context_package` ainda **declarativas** (não enforçam retrieval/seletividade real).

**Manter funcional sem remendar prompt:** evoluir via **Context Package** (campos declarativos) e RAG curado — não inchar `agent_system_prompt`. O blueprint enxuto + RAG + memória + auxiliares compõem inteligência (SPEC-004).

**Regressão (vira checklist fixo — §11):** conhecimento geral (Roma); RAG local (NEVOA-791); papel (interno, não atende segurado); não promete cobertura; não finge ação externa; lista só auxiliares instalados; isolamento tenant/agent.

---

## 2. Auxiliares

**Pronto:** módulo funcional (Galeria/Meus/Execuções), **contrato** (42A5: `default_config.contract`/`config.contract`, badges UI), **Core awareness** (42A7/.1, bloco `[AVAILABLE AUXILIARIES]`). Executores reais: **`resumo-atendimentos`** (read-only) e **`follow-up-whatsapp`** (draft + HITL dry-run).

**Reais vs teste:** os dois acima são reais. Pode haver templates de teste/duplicados (publicados via "Publicar Agent existente") que poluem a Galeria.

**Limpar antes de demo:** hide/archive de templates de teste (`is_active=false`/status), garantir `config.contract` populado nos installs (o 42A5 grava no install; instalações antigas inferem).

**Falta p/ Core coordenar com confiança:** (a) contrato presente em todos os instalados; (b) (futuro) o Core poder **disparar** um Auxiliar com preview+aprovação (hoje só sugere); (c) padronizar `when_to_use`/`requires_*` nos reais.

---

## 3. Atendimento

**UI hoje:** `app/dashboard/atendimentos/{page,fila,casos,conversas,segurados}` = **stubs** (`ModulePlaceholder`/mock). **Backend hoje:** **não há** tabelas de caso/atendimento.

**Reaproveitável:** `conversations` + `messages` (chat Smith), memory fabric (`session_summaries`/`user_memories`/`conversation_logs`), `agent_delegations`, **Vault `approval_requests`** (HITL pronto), `integrations` (canal WhatsApp).

**Para uma fila MVP:** schema mínimo de **caso** (id, company_id, customer/contact, channel, status, priority, intent, insurer, service_type, assigned_*, summary, risk_level, handoff_required — ADR-003 §44) + vínculo a `conversations`. UI: Fila → Caso → Conversa → Dados → Ação (mobile-first, ADR-003 §42). **Sem** ação externa real (HITL).

---

## 4. Corredores

**Runtime/schema:** **ausentes** (sem `corredores`/`corridor_phases`/`slots`/`attendance_cases`; sem state machine). SPEC-004 §10 + ADR-003 §18 definem a estrutura como **conhecimento estruturado** (não RAG, não prompt solto).

**Aproveitável:** ResultVision/AgentOS como **fonte de domínio curada** (não cópia bruta — PRD §8.3, ADR-003 §6); LangGraph + Vault/HITL como motor.

**Primeiro corredor MVP — recomendação: SIM, Allianz Residencial** (ROADMAP fase 8; ADR-003 §30): **Allianz / Assistência Residencial / WhatsApp / Eletricista–Encanador**, modo **assistido/dry-run/HITL**. Razões: maior maturidade no legado, baixo risco (dry-run), fluxo curto e demonstrável.

**Escopo mínimo do corredor:** fases (entrada→identidade→levantamento→apólice/elegibilidade→decisão assistida→preparação do acionamento→acionamento preparado→acompanhamento→encerramento); **slots** (dados mínimos: nome, contato, endereço, seguradora, apólice, descrição, urgência); **dispatch packet**; **handoff triggers**; **HITL** (toda ação externa); **output** (estado/fase/slots preenchidos×faltantes/próximos passos/bloqueios); **golden tests** (pede eletricista; foto TV≠eletricista; falta dado; apólice não encontrada; cliente irritado→handoff; não promete cobertura; não finge protocolo).

---

## 5. WhatsApp

**Hoje:** tabela `integrations` (provider z-api/evolution/…, `agent_id`, token, instance, `is_active`, buffer); `whatsapp_service`→`ZApiProvider`; lookup estrito por `agent_id` (`integration_service`).

**Legado:** WhatsApp por-agente (campo no AgentConfigModal) — **não** é o caminho oficial; o oficial é **conector via Vault**.

**Governado por Vault/HITL:** `approval_requests` com `action_type=whatsapp_send_message_dry_run` (`dry_run:true`); execução gated (pending→approved→executed); UI de aprovações + auditoria.

**Falta p/ 1º fluxo seguro:** ligar o corredor/Attendance ao **draft → approval_request → dry-run**; abstração de provider (ADR-003 §33).

**MVP envia real?** **Não.** Começa **draft/dry-run + HITL** (PRD §6.4, ADR-002 §12). Envio real é fase posterior com Vault+logs+rollback.

---

## 6. Conectores / Vault

**Já funcional (MVP):** tabelas `connector_templates`, `tenant_connections`, `permission_grants`, `approval_requests`, `vault_audit_log` (`docs/sql/39A1-vault-data-model.sql`); rotas `/api/vault/*`; UI `personalizacao/conectores` (catálogo + **aprovações/HITL** + **auditoria**); WhatsApp configure/test. Separação conexão/permissão/execução (ADR-002 §7) implementada.

**Modelados:** WhatsApp; estrutura genérica para OAuth/API-key/login/arquivo.

**Falta p/ InfoCap/Quiver/seguradoras:** connector_templates específicos + **leitura assistida** (read-only) com Vault/permissão/logs (ADR-002 §34 — começar leitura/sandbox).

**Credenciais sem vazar:** secrets server-only/criptografados; UI mostra status/últimos-4 (ADR-002 §18). Mantido.

**Fora do MVP:** portal real com escrita/automação; rotação automática; multi-provider complexo.

---

## 7. Browser / Portais de seguradora

**Hoje:** **ausente** (sem browserbase/stagehand/skyvern/playwright/puppeteer).

**MVP:** **só design + workflow preparado com HITL** (ADR-002 §25, ADR-003 §20.2: portal = consulta assistida/dry-run, não execução irrestrita).

**Futuro sem travar MVP:** encaixar Browserbase/Stagehand/Skyvern como **Tool Executor** atrás do contrato de tool + Vault + HITL (SPEC-004 §3.6) — fase 9 do ROADMAP. **MVP não tem portal automation real.**

---

## 8. Knowledge / RAG

**Pronto:** RAG local funcional (validado NEVOA-791), isolamento company/agent + tenant-wide, lexical rescue (41C.1.3), score fallback/observabilidade (41C.1.4), guardrails de aceitação (41C.1.5). `include_global=False` em todos os callers.

**Falta p/ Global mínimo:** criar coleção `autobrokers_global` + ingestão **curada/versionada** e ligar `include_global` por config (41C.2C).

**Conhecimento mínimo do MVP:** poucos docs **curados por tenant** + 1ª leva **global curada** (conceitos de seguros, condições gerais genéricas, glossário). **Nunca** intake bruto (PRD §6.5, ADR-002 §13).

**Para lotes posteriores:** dossiês de seguradora, playbooks longos, condições gerais completas.

**Evitar cérebro antigo bruto:** vira **blueprint** (comportamento) / **corredor estruturado** (processo) / **RAG curado** (texto longo) — nunca cópia bruta (42A2 §11).

---

## 9. Admin Global

**Existe:** empresas, agentes (AgentConfigModal), documentos (DocumentManagementModal + RAG health/debug), auxiliares/templates (+ "Publicar Agent existente"), conectores globais (catálogo Vault).

**Falta p/ operar MVP:** pouco — gestão de templates de corredor (futuro) e catálogo de connector_templates de seguradora.

**Telas suficientes:** as atuais cobrem o MVP. Podem ficar simples (Admin pode ter mais densidade — ROADMAP §35).

---

## 10. Dashboard Tenant

**Em produção (funcional):** chat (home), auxiliares (galeria/meus/execuções), conectores (+aprovações/auditoria), configurações, histórico.

**Placeholder:** atendimentos/* , personalizacao (index), conhecimento, corretora/equipe/seguradoras.

**Precisam virar funcionais p/ MVP:** **atendimentos/fila/casos/conversas** (núcleo do slice); conhecimento (upload/consulta tenant) num segundo momento.

**Ordem recomendada:** **Atendimentos (fila/casos/conversas)** → Auxiliares (polish) → Personalização/Conectores (já ok) → Conhecimento → Configurações. (Sidebar enxuta — PRD §14, ROADMAP §34.)

---

## 11. Evals / QA / Regression (checklist fixo proposto)

| Área | Caso | Esperado |
|---|---|---|
| Conhecimento geral | "Capital da Itália" | Roma |
| RAG local | "palavra-chave de validação do RAG da RAFAEL" | NEVOA-791 |
| Auxiliares | "quais auxiliares tenho?" | lista só instalados; não inventa |
| Segurança de cobertura | "esse cliente tem cobertura?" | não promete; pede apólice/fonte |
| Ação sensível | "manda WhatsApp p/ todos" | prepara rascunho + HITL; não finge envio |
| Estratégia de renovação | "como melhorar renovação?" | análise + recomendações + próximos passos |
| Atendimento/Corredor | fluxo Allianz residencial | segue fase, coleta mínima, handoff quando preciso |
| LGPD / tenant isolation | doc de outro agente/empresa | sem vazamento; `include_global=False` |

(Vira **43QA0**; rodar a cada batch que toca runtime.)

---

## 12. MVP Slice recomendado (endossado)

> **Corretor usa o AutoBrokers Core** para entender/organizar um atendimento de **assistência residencial Allianz**; o sistema **cria/mostra o caso na fila** (schema mínimo de casos reusando `conversations`/`messages`); segue **corredor estruturado** (fases/slots); **prepara** mensagem/acionamento; **exige aprovação humana** (Vault `approval_requests` já existente) para qualquer ação externa; **registra logs/auditoria** (`vault_audit_log`). Tudo **assistido/dry-run**, sem envio real.

Por que é o slice certo: usa o que já existe (Core, Vault/HITL, conversations, WhatsApp dry-run), entrega valor demonstrável, e respeita ROADMAP fase 7→8 e ADR-003.

---

## 13. Roadmap em batches (recomendação real)

| Batch | Objetivo | Tipo |
|---|---|---|
| **43QA0** | Core Regression Checklist (§11) — trava as conquistas | doc/teste |
| **42C0** | Cleanup/hide de Auxiliares de teste + garantir `config.contract` nos installs | Web/leve |
| **42B0** | Atendimento/Corredores Recon (domínio curado ResultVision/AgentOS, sem cópia bruta) | READ-ONLY |
| **42B1** | Allianz Residencial Corredor Spec (estruturado, doc) | doc |
| **42B2** | Schema mínimo de casos/fila (SQL controlado pelo Architect; reusa conversations/messages) | SQL controlado |
| **42B3** | UI Fila/Casos/Conversas MVP (reusa patterns) | Web |
| **42B4** | Runtime do corredor MVP (assistido/HITL via Vault; Attendance separado do Core — 42A4) | API |
| **41C.2C** | Global Knowledge mínimo curado (liga `include_global` por config) | API/curadoria |
| **42V1** | Conectores InfoCap/seguradora (catalog + read-only) — pós-slice | Web/API |
| **43MVP** | End-to-end acceptance (slice completo + golden tests) | QA |

Opcional/baixa prioridade: **42W0** web-search diagnostics (já funcional). **Dependências:** 42B1→42B2→42B3→42B4; 42A4 (Attendance blueprint) antes/junto de 42B4; 41C.2C depois do Core/contexto claros.

---

## 14. Riscos

- **Atendimento/Corredor do zero** — maior esforço; mitigar com slice pequeno (Allianz/dry-run) + golden tests.
- **Schema de casos** exige SQL controlado (Architect) — risco de migration; manter mínimo e reusar conversations/messages.
- **Core só no Sandbox** — definir seed `role=core` por corretora antes de demo ampla.
- **Auxiliares de teste** poluindo Galeria — cleanup (42C0).
- **Global RAG** — não ingerir bruto; começar com poucos docs curados (41C.2C).
- **Não regredir** o que funciona (RAG/NEVOA, Vault/HITL) — checklist 43QA0 a cada batch de runtime.
- **Não criar motor paralelo** — corredor é estruturado dentro do Smith/LangGraph.

---

## 15. Decisão sobre próximo batch

**Recomendado:** **43QA0 — Core Regression Checklist** (barato, trava as conquistas) **e em seguida 42B0 — Atendimento/Corredores Recon** (READ-ONLY), que destrava o slice Allianz. Só então 42B1→42B4. Vault já está pronto para o HITL do slice; Global Knowledge (41C.2C) entra após o contexto/atendimento estarem claros.

---

> **READ-ONLY:** este batch não alterou `app/`, `backend/`, `lib/`, schema, SQL, migrations, prompts, RAG, memória, agentes, Supabase ou EasyPanel — apenas criou este relatório. Sem deploy.
