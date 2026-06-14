# 42I0P — InfoCap & Policy Lookup Deep Recon / Contract Plan (READ-ONLY)

> **Status:** auditoria profunda · **READ-ONLY** (nenhum código/SQL/migration/schema/API/UI/runtime/prompt/RAG/Supabase/credencial alterado, sem deploy, sem consulta externa) · sem cópia bruta do Agent OS · sem PII/CPF/segredo.
> **Data:** 2026-06-14 · **Modelo:** Claude Opus 4.8 · **Branch:** main
> **Objetivo:** definir o **contrato e a arquitetura do Policy Lookup** do AutoBrokers — como o runtime sai de `policy_lookup_required` para `policy_selected` / `policy_lookup_blocked` / `policy_lookup_pending` / `policy_not_found` / `policy_multiple_matches` / `policy_evidence_ready`, usando InfoCap/Quiver/documento/evidência via tool/Vault, **sem virar RAG e sem motor paralelo**.

---

## Fontes auditadas
**Canon:** `README`, `PRD-001`, `ROADMAP-001`, `ADR-001-runtime`, `ADR-002-vault`, `ADR-003-atendimento` (§5 fontes, §13 apólice/elegibilidade, §16 preparação do acionamento, §34 InfoCap/Quiver, §35 mídia, §36 RAG, §48 guardrails), `SPEC-003` (RAG/memória), `SPEC-004` (intelligence/context), `SPEC-005` (§7 fluxo ponta-a-ponta, §12 InfoCap/Policy Evidence Contract), `SPEC-006` (Eletricista MVP).
**Design/recon:** `42B0-atendimento-corredores-deep-recon` (§9 InfoCap MVP, §11 corredor), `39A0-vault-connectors-hitl-recon`, `39A1-vault-data-model-report`.
**Código atual:** `lib/attendance/attendance-macro-state.ts`, `runtime-identity-policy.ts`, `corridor-runtime.ts`, `runtime-slot-catalog.ts`, `runtime-config-resolver.ts`, `runtime-safety-policy.ts`, `runtime-intake-policy.ts`, `handoff-dossier.ts`, `support-destinations.ts`; rotas `runtime/reply`, `runtime/step`, `handoff-dossier`, `cases`, `cases/[caseId]`.
**SQL:** `backend/supabase/migrations/20260612_attendance_corridor_mvp_foundation.sql`, `20260613_human_support_destinations_foundation.sql`, `docs/sql/39A1-vault-data-model.sql`, `backend/supabase/migrations/schema_completo.sql`.
**Legado Agent OS:** `AUTOBROKERS_AGENT_OS/{02_RUNTIME_CONVERSACIONAL,03_EXECUTION_PLANE,04_CONVERSA_COM_CLIENTE,05_SQUADS,06_SKILLS,07_CORREDORES,09_CONTRATOS,10_GUARDRAILS}` — **NÃO está sincronizado no workspace local**; usado apenas como **base conceitual** via ADR-003/42B0/SPEC-005, que já o consolidam (famílias `entrada`/`identidade`/`apolice`, matriz de skills por etapa, adapters InfoCap/Document AI, `apolice.ler_documento_oficial_pdf`, `midia.processar_documento_pdf_ou_anexo`). Nenhuma conversa real/intake foi aberta.

---

## 1. Resumo executivo

**Policy Lookup** é a etapa que pega a **identidade** já capturada (CPF/CNPJ em `attendance_cases.insured_document_ref`) e produz uma **evidência estruturada de apólice/cobertura** suficiente para o runtime **decidir** e, só então, continuar o corredor ou acionar. É o que destrava `policy_lookup_required`.

Decisão central: **Policy Lookup é tool/conector/evidência, não RAG e não LLM.** A LLM/Smith conversa e interpreta, mas **quem afirma cobertura é a evidência estruturada** (InfoCap/Quiver/documento/portal/humano), nunca o modelo. RAG explica regra/condição geral; não decide cobertura, não lista apólice.

Caminho de implementação seguro (defendido aqui): **(1) mock/manual resolver** para destravar o MVP sem API real → **(2) conector InfoCap read-only via Vault** → **(3) normalizador de evidência** → **(4) retomar corredor**. OCR/Document AI (Azure/Google) é **evolução posterior** para documento não estruturado/anexo, **não** dependência do MVP.

**Não precisa de SQL nem credenciais no próximo batch (42I1).** O schema atual de `attendance_cases` já tem todos os campos necessários (`policy_source`, `policy_number`, `policy_snapshot`, `coverage_evidence`, `verification_status`, `insured_*`). O Vault (39A1) já tem o conector `infocap` semeado e `tenant_connections`/`approval_requests`/`vault_audit_log` para quando a API real entrar.

---

## 2. Estado atual do runtime

Sequência hoje (42B5B→G): **Entrada (intake)** → **gate de segurança/risco** → **identidade (CPF/CNPJ)** → **`policy_lookup_required`** (parada atual) → [futuro] corredor/slots → [futuro] decisão/dispatch/handoff.

No estado `policy_lookup_required` (gerado por `macroGateOverride`/identity branch em `runtime/reply` e `runtime/step`):
- `attendance_cases.status = policy_check`
- `attendance_cases.insured_document_ref = <CPF/CNPJ>` (gravado; **nunca logado completo** — `maskDocument`)
- `attendance_cases.metadata.attendance_macro_state = policy_lookup_required`
- `attendance_cases.metadata.identity.document_type = cpf|cnpj`
- `corridor_runs.last_agent_action = policy_lookup:pending`
- `corridor_runs.diagnostics.runtime.macro_state = policy_lookup_required`
- `verification_status` permanece `unverified`; `policy_source` **não** vira `infocap` (sem consulta real).
- Mensagem ao cliente: "Vou usar esse dado para localizar a apólice em fonte segura antes de confirmar cobertura ou seguir com acionamento." + `next_step` indica explicitamente que o lookup vem em batch futuro.

`evaluateAttendanceMacroState` já trata `should_require_policy_lookup` quando há identidade e `verification_status` não está `verified*`. **Falta o resolver** que produz o `policy_lookup_result` e atualiza os campos de apólice.

---

## 3. Estado atual do Vault / tools / conectores

`docs/sql/39A1-vault-data-model.sql` (camada de produto do Vault) já oferece tudo para um conector read-only governado:
- **`connector_templates`** — já **semeia `infocap`** (`category=insurance`, `connector_kind=api_key`, `auth_type=api_key`, `risk=high`, `requires_approval_default=true`, `capabilities=["read"]`), além de `quiver` e `insurance_portal`.
- **`tenant_connections`** — conexão por corretora; `encrypted_secret_ref` é **referência** (segredo nunca na tabela). `connection_config jsonb` para base_url/env.
- **`permission_grants`** — `subject_type` inclui `atendimento`; `allowed_actions` ex.: `["read"]`; `requires_approval`.
- **`approval_requests`** — HITL genérico; `action_type` ex.: `connector_test`/`portal_read`; `subject_type='atendimento'`.
- **`vault_audit_log`** — auditoria de `connection_tested`/`action_executed`/`action_failed`.

Smith técnico (39A0): `agent_http_tools`, `agent_mcp_connections/tools`, `integrations`, `agent_delegations`. **Regra herdada:** skill chama **tool**; tool chama adapter; nada de adapter direto no fluxo conversacional.

---

## 4. O que o Agent OS antigo ensina sobre apólice

Consolidado em ADR-003/42B0/SPEC-005 (sem abrir o legado bruto):
- **Atendimento não começa no corredor** (ADR-003 §8): entrada → entendimento → coleta → **identificação** → **apólice/elegibilidade** → classificação → decisão → preparação → corredor.
- **Família `entrada`** prepara terreno, **não** consulta apólice nem escolhe corredor definitivo nem promete cobertura.
- **Família `identidade`** descobre com segurança quem fala (titular/segurado/familiar/terceiro/não autorizado) — autorização antes de revelar dados de apólice (ADR-003 §12).
- **Família `apolice`** governa **buscar → selecionar → ler → interpretar → preparar** apólice, porque quase todo atendimento depende de cliente correto, apólice correta, se está ativa e cobertura.
- **Adapters** (InfoCap, Supabase, Evolution, Google Document AI, Azure Document Intelligence, Redis, n8n, portais): skill nunca chama adapter direto — chama **tool** (mapeia 1:1 com Vault/tools do Smith).
- **Skills de documento:** `apolice.ler_documento_oficial_pdf`, `midia.processar_documento_pdf_ou_anexo` → confirmam que **OCR/Document AI** é a camada de leitura robusta de PDF/anexo, **depois** do dado estruturado.
- **Guardrail mestre (ADR-003 §13/§48):** proibido "está coberto"/"a seguradora vai pagar"/"já acionei" sem fonte; correto: "vou verificar as informações da apólice antes de confirmar".

---

## 5. Macro fluxo completo: Entrada → Identidade → Apólice → Decisão → Corredor

```
Entrada (intake, 42B5F)
  → Gate de segurança/risco (42B5E)        [risco alto = handoff, precede tudo]
  → Identidade (42B5G)                      [CPF/CNPJ → insured_document_ref]
  → POLICY LOOKUP (este plano, 42I1+)       ← destrava policy_lookup_required
       ├─ lookup de cliente   (existe segurado para esse documento?)
       ├─ lookup de apólice   (quais apólices? ativa? ramo/produto/seguradora?)
       ├─ seleção de apólice  (1 match → seleciona; N → desambigua; 0 → not_found)
       ├─ leitura/interpretação de cobertura (assistência residencial cobre eletricista?)
       └─ evidência de cobertura (coverage_evidence estruturada + verification_status)
  → Decisão operacional        (classificar serviço; pode acionar? precisa humano?)
  → Corredor/Subcorredor       (retoma slots: affected_area, electrical_issue_type, ...)
  → Dispatch packet / Handoff / Acompanhamento  (somente com evidência pronta + HITL)
```

**Distinções (pergunta 3 do prompt):**
- **Identidade** = quem está falando + documento (CPF/CNPJ). Já implementada.
- **Lookup de cliente** = existe **segurado/cliente** vinculado a esse documento na base/InfoCap.
- **Lookup de apólice** = quais **apólices** desse cliente, status (ativa/vencida/cancelada), ramo, produto, seguradora.
- **Seleção de apólice** = escolher a apólice **correta** para a demanda (residencial × auto × vida; endereço; vigência).
- **Leitura/interpretação de cobertura** = a apólice selecionada cobre o serviço pedido (ex.: assistência residencial → eletricista)?
- **Evidência de cobertura** = registro **estruturado e auditável** (`coverage_evidence`) que autoriza afirmar/decidir.
- **Decisão operacional** = transformar tudo isso em próximo passo seguro (continuar corredor, pedir documento, handoff, bloquear).

---

## 6. Contrato de Policy Lookup (`policy_lookup_result`)

Contrato **único e genérico** (serve a todos os corredores/seguradoras), retornado por qualquer fonte (mock/manual/InfoCap/upload/humano):

```jsonc
{
  "status": "policy_selected | policy_lookup_pending | policy_lookup_blocked | policy_not_found | policy_multiple_matches | policy_evidence_ready",
  "source": "manual | mock | infocap | connector | upload | human | unknown",
  "source_ref": "string|null",            // referência opaca (ex.: id de consulta); NUNCA segredo/token
  "queried_document_type": "cpf | cnpj | null",
  "matches": [
    {
      "policy_ref": "string",              // id interno/ref, não o número cru quando evitável
      "insurer_key": "allianz | ...",
      "product": "string|null",
      "line_kind": "residential | auto | life | business | unknown",
      "policy_status": "active | expired | cancelled | suspended | unknown",
      "masked_policy_number": "****1234",
      "holder_name_masked": "M*** S***",
      "valid_from": "date|null",
      "valid_to": "date|null"
    }
  ],
  "selected": { /* um match acima, ou null */ },
  "coverage_evidence": { /* ver seção 7, ou null */ },
  "verification_status": "unverified | pending_human | verified_by_document | verified_by_connector | verified_by_human | not_applicable",
  "next_macro_state": "policy_selected | policy_lookup_blocked | corridor_collecting_slots | handoff | ...",
  "blockers": ["no_active_policy", "policy_not_for_line", "ambiguous_match", "needs_authorization", "..."],
  "requires_human": false,
  "notes": "string|null"                   // operator-facing; sem PII crua
}
```

**Estados de saída (perguntas 7–10):**
| status | significado | efeito no runtime |
|---|---|---|
| `policy_selected` | 1 apólice ativa e adequada selecionada | segue para leitura de cobertura / corredor |
| `policy_evidence_ready` | cobertura interpretada + evidência registrada | **destrava** decisão/corredor |
| `policy_multiple_matches` | várias apólices candidatas | desambiguar (perguntar qual) — **não** escolher sozinho |
| `policy_not_found` | nenhuma apólice para o documento | pedir dado/documento ou **handoff** |
| `policy_lookup_pending` | aguardando fonte (mock/manual/API/documento) | mantém parado, sem prometer |
| `policy_lookup_blocked` | bloqueio (sem autorização, fonte indisponível, ramo incompatível) | **handoff** ou pedir autorização |

**Obrigatório para continuar o corredor:** `coverage_evidence` presente **ou** decisão explícita de `not_applicable` — e `verification_status` ≠ `unverified`. **Bloqueia:** `policy_lookup_pending`, `policy_not_found` sem alternativa, fonte indisponível. **Vira handoff:** `policy_lookup_blocked`, `needs_authorization`, negativa/ambiguidade que o runtime não resolve com segurança.

---

## 7. Modelo de evidência de cobertura (`coverage_evidence`)

Espelha o **Policy Evidence Contract** (SPEC-005 §12.4) e grava na coluna existente `attendance_cases.coverage_evidence`:

```jsonc
{
  "source": "manual | mock | infocap | connector | upload | human",
  "source_ref": "string",                 // ref opaca da consulta/documento; nunca segredo
  "verified_at": "timestamp",
  "verified_by": "agent | human | connector",
  "confidence": "low | medium | high",
  "coverage_summary": "Assistência residencial inclui mão de obra elétrica emergencial (texto curto, sem PII)",
  "limitations": ["carência X", "limite de acionamentos", "..."],
  "human_required": false
}
```

**Regra de ouro:** só é permitido **afirmar cobertura** se existir `coverage_evidence` com `confidence` adequada **e** `verification_status` verificado. Sem isso → "vou verificar" + (se necessário) handoff. A LLM nunca preenche `coverage_evidence` por conta própria — ela vem da fonte.

---

## 8. Reuso do schema atual vs schema futuro (perguntas 11–12)

**Reusar (sem tabela nova, sem migration no MVP):**
| Dado | Coluna atual |
|---|---|
| documento do segurado | `attendance_cases.insured_document_ref` (+ `metadata.identity`) |
| origem da apólice | `attendance_cases.policy_source` (`manual|upload|snapshot|infocap|connector|human|unknown`) |
| número da apólice | `attendance_cases.policy_number` (exibir/logar **mascarado**) |
| snapshot estruturado | `attendance_cases.policy_snapshot jsonb` (sem segredo, sem PII excessiva) |
| evidência de cobertura | `attendance_cases.coverage_evidence jsonb` (contrato da seção 7) |
| status de verificação | `attendance_cases.verification_status` |
| macro estado / lookup | `attendance_cases.metadata.attendance_macro_state` + `corridor_runs.diagnostics.runtime` |
| matches/result transitório | `corridor_runs.diagnostics.runtime.policy_lookup` (resultado resumido, sem PII crua) |
| auditoria de consulta via conector | `vault_audit_log` (event `action_executed`/`connection_tested`) |

**Schema futuro (somente se necessário, decisão do Architect):** tabela `policy_lookups` (histórico/auditoria de consultas: case_id, source, status, matches_count, created_at) — **só** quando houver necessidade real de timeline/retry/observabilidade de lookups. **Não** no MVP.

---

## 9. InfoCap read-only: arquitetura recomendada (42I2)

```
Attendance runtime (policy_lookup_required)
  → tool: policy_lookup(company_id, document, line_kind?)         [determinístico]
       → resolve tenant_connection (Vault) do connector_template 'infocap'
       → lê encrypted_secret_ref (segredo NUNCA no código/log/prompt)
       → chama InfoCap READ-ONLY (buscar cliente/apólice/coberturas/documento)
       → normaliza para policy_lookup_result (seção 6) + coverage_evidence (seção 7)
       → grava em attendance_cases (policy_*/coverage_evidence/verification_status)
       → vault_audit_log (action_executed) + (se requires_approval) approval_request
  → macro state avança: policy_selected / policy_evidence_ready / blocked / not_found
```
Princípios: **read-only** primeiro (ADR-003 §34, SPEC-005 §12.3 — buscar segurado/apólice/coberturas/documento; nunca escrita no MVP); credencial **sempre** no Vault/`tenant_connections`; consulta com `permission_grant` (`subject_type=atendimento`, `allowed_actions=["read"]`); auditoria obrigatória; falha de fonte → `policy_lookup_pending`/`blocked`, nunca inventar.

**Como o Smith/Attendance Agent chama isso (pergunta 15):** como **tool** declarada no Context Package do Attendance (não adapter direto). O agente decide *quando* chamar; a tool é determinística e governada pelo Vault. O runtime determinístico (estas APIs) continua sendo o trilho; o Smith é a inteligência conversacional.

---

## 10. OCR / Document AI: quando e como entra (perguntas 5–6, 10)

- **Ordem:** (1) dado **estruturado** (InfoCap/Quiver) → (2) **mock/manual** para destravar → (3) conector read-only real → (4) **OCR/Document AI** (Azure Document Intelligence / Google Document AI) só quando a apólice vier como **PDF/anexo não estruturado** ou print.
- **Quando InfoCap vs OCR:** InfoCap/Quiver quando o dado existe estruturado na base da corretora (preferencial). OCR quando o cliente **envia** o documento/PDF/foto e não há fonte estruturada.
- **Como entra:** como **tool** (`apolice.ler_documento_oficial_pdf` / `midia.processar_documento_pdf_ou_anexo`) que produz o mesmo `policy_lookup_result`/`coverage_evidence` — o contrato é o mesmo, muda a fonte. Mídia: armazenar/associar ao caso primeiro (ADR-003 §35), interpretação avançada depois. **Não é dependência do MVP.**

---

## 11. RAG / memória: papel correto (pergunta 16)

- **RAG (apoio, não motor):** explica condições gerais, regras da seguradora, o que é assistência residencial, carências — texto curado por tenant. **Nunca** lista apólice, **nunca** decide cobertura, **nunca** recebe intake bruto/PII (ADR-003 §36, SPEC-003).
- **Memória de caso (futuro):** resumo/decisões/pendências do caso — continuidade, não verdade absoluta; sem promoção automática a global.
- **Nunca no prompt/RAG:** CPF/CNPJ, número de apólice cru, `policy_snapshot` com PII, credenciais InfoCap, tokens.

---

## 12. Segurança / LGPD / mascaração (pergunta 13)

- `insured_document_ref` e `policy_number`: armazenados, **mascarados** em UI/logs (`maskDocument`, `****1234`). Logs do runtime só: `case`, `macro_state`, `status`, `message_id`, `doc_type+len` — nunca o número.
- Segredos InfoCap: **só** no Vault/`tenant_connections.encrypted_secret_ref`; nunca repo/RAG/prompt/`NEXT_PUBLIC_`/cliente.
- **Autorização do solicitante:** antes de revelar dados de apólice, confirmar que o solicitante é titular/segurado/autorizado (ADR-003 §12); terceiro não autorizado → não expor + handoff.
- Isolamento multi-tenant por `company_id` em toda consulta; `policy_snapshot` guarda o mínimo necessário (política de retenção a definir — ver Riscos).

---

## 13. Como retomar o corredor após policy lookup (pergunta 17, batch 42B5H)

Quando `policy_lookup_result.status ∈ {policy_selected, policy_evidence_ready}` e `verification_status` ≠ `unverified`:
- macro state passa de `policy_lookup_required` → `corridor_collecting_slots`;
- `attendance_cases.status` volta a `collecting_slots` (ou `corridor_selected`);
- `corridor_runs.last_agent_action` deixa de ser `policy_lookup:pending`;
- o runtime retoma o **próximo slot do corredor** (`affected_area`, `electrical_issue_type`, …) via `computeRuntimeStep` + `macroGateOverride` (que agora retorna `null` porque o gate de apólice está resolvido).
Se `blocked`/`not_found`/`pending` → mantém parado/handoff conforme seção 6. **Nunca** confirmar cobertura sem `coverage_evidence` (pergunta 18).

---

## 14. MVP manual/mock recomendado (pergunta 19, batch 42I1)

**Primeiro batch de implementação = resolver mock/manual, só TS/Next, sem SQL, sem credenciais:**
- Endpoint `POST /api/attendance/cases/[caseId]/runtime/policy-lookup` (ou ação dentro do reply) que aceita um resultado **manual/mock** (operador informa apólice/cobertura) **ou** um fixture de teste, e grava `policy_lookup_result` → `attendance_cases.policy_*`/`coverage_evidence`/`verification_status` (`verified_by_human`/`pending_human`).
- Helper puro `lib/attendance/policy-lookup.ts`: `buildPolicyLookupResult(...)`, `applyPolicyLookupToCase(...)`, validação do contrato, mascaração.
- Destrava o fluxo E2E (entrada → risco → identidade → **apólice mock** → corredor) sem depender da API real.
- Modo `source: 'mock'|'manual'|'human'`; `external_action_allowed=false`; sem dispatch/WhatsApp.

---

## 15. Testes / goldens recomendados (pergunta 21)

- Documento válido + 1 apólice ativa residencial → `policy_selected`/`policy_evidence_ready` → corredor retoma em `affected_area`.
- Documento válido + nenhuma apólice → `policy_not_found` → pede documento ou handoff; **não** promete cobertura.
- Documento válido + várias apólices → `policy_multiple_matches` → desambigua, não escolhe sozinho.
- Apólice de ramo errado (auto p/ pedido residencial) → `policy_lookup_blocked` (`policy_not_for_line`).
- Fonte indisponível (mock falha) → `policy_lookup_pending`, mensagem "vou verificar", sem inventar.
- Solicitante não autorizado → bloqueio + handoff, sem expor dados.
- Pergunta "isso está coberto?" sem evidência → **não confirma** (guardrail).
- Regressão: Core interno / Auxiliares (Resumo + Follow-up) / RAG NEVOA-791 intactos; high-risk continua handoff antes de qualquer lookup.

---

## 16. Riscos (e o que precisa de decisão do Founder)

| Risco | Mitigação / decisão |
|---|---|
| **Formato real da API InfoCap desconhecido** (auth/endpoints/paginação) | manter mock/manual primeiro; inspecionar API antes de fixar envs (42I2) — **decisão do Founder: acesso/spec da API** |
| **Retenção/mascaração de `policy_snapshot`** (quanto guardar de PII) | guardar o mínimo; mascarar número/holder — **decisão do Founder: política de retenção** |
| **Autorização do solicitante** (titular × terceiro) antes de revelar apólice | exigir confirmação; terceiro → handoff — **decisão do Founder: regra de autorização** |
| LLM "inventar" cobertura | cobertura só de `coverage_evidence`; guardrail no runtime |
| Policy Lookup virar RAG | contrato/tool determinístico; RAG só explica |
| Segredo InfoCap vazar | Vault/`encrypted_secret_ref`; nunca repo/log/prompt |
| Travar o MVP esperando API real | mock/manual resolver (42I1) destrava sem API |
| Multi-match silencioso (escolher errado) | `policy_multiple_matches` exige desambiguação |

---

## 17. Próximos batches recomendados

```
42I0P  (este) — contrato/recon                         [READ-ONLY ✓]
42I1   — Policy Lookup Manual/Mock Resolver            [TS/Next, sem SQL, sem credenciais]
42I2   — InfoCap Connector Read-only (Vault)           [tool + Vault; credenciais via tenant_connections]
42I3   — Policy Evidence Normalizer                    [normaliza fontes → coverage_evidence]
42B5H  — Resume Corridor After Policy Lookup           [macro state volta a coletar slots]
42B5J  — Dashboard Conversation Simulator              [testar E2E no dashboard]
42B7   — Golden Tests do fluxo completo
42B6   — Dispatch Packet / WhatsApp dry-run            [só após evidência pronta + HITL]
42W1   — WhatsApp controlado
```
OCR/Document AI (Azure/Google) entra como camada de leitura robusta **entre 42I3 e 42B6**, quando o documento não vier estruturado.

---

## 18. O que NÃO fazer

- Não tratar Policy Lookup como RAG; não deixar a LLM afirmar cobertura.
- Não acionar seguradora/prestador/WhatsApp/portal antes de `coverage_evidence` pronta + HITL.
- Não colocar credenciais InfoCap em repo/env de app/RAG/prompt/cliente — só Vault.
- Não logar CPF/CNPJ/número de apólice completos; não copiar intake bruto/PII.
- Não criar tabela/migration no 42I1 (reusar campos existentes).
- Não criar motor paralelo ao Smith; o resolver é tool determinística chamada pelo Attendance Agent.
- Não escrever na InfoCap no MVP (read-only).
- Não escolher apólice sozinho em caso de múltiplos matches.

---

## Confirmações finais (READ-ONLY)
Este batch criou **apenas** este relatório. Nenhuma mudança em `app/`, `lib/`, `backend/`, schema, SQL, migrations, prompts, RAG, Supabase, agentes, UI, WhatsApp; nenhuma credencial criada/exposta; nenhuma consulta externa; nenhum CPF/segredo/PII no texto; legado tratado só conceitualmente. Sem deploy.

**Resumo do contrato `policy_lookup_result`:** status (selected/pending/blocked/not_found/multiple/evidence_ready) + source + matches[] (mascarados) + selected + `coverage_evidence` (SPEC-005 §12.4) + verification_status + next_macro_state + blockers + requires_human. Mapeia 100% nos campos atuais de `attendance_cases` → **sem SQL e sem credenciais no próximo batch (42I1, mock/manual)**.
