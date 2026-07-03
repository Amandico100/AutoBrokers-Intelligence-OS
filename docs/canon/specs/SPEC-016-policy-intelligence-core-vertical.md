# SPEC-016 — Policy Intelligence: Assistência Residencial End-to-End no Core

> Status: **IMPLEMENTADA em `feat/spec-016-policy-intelligence` — aguardando teste real controlado + aceite para merge/deploy**
> Onda: 1 (primeira vertical de produção)
> Executor: Fable (esforço alto) · Baseline: `e7c5044`
> Programa: `docs/canon/FABLE_RECOVERY_PROGRAM.md`
> Regras herdadas: P0/P0.1 irreversíveis · stash R1C.2 nunca aplicado inteiro · sem runtime paralelo · sem PII em log

---

## 1. Problema

O corretor pergunta em linguagem natural sobre clientes e apólices. Hoje:

1. **Follow-up anafórico falha**: "ela tem assistência?" sem o número da apólice no texto não força a tool InfoCap (`_extract_context_policy_number` em `backend/app/agents/nodes.py` exige o número literal ou regex numérico) → a LLM pode responder do histórico sem evidência e sem output guard.
2. **Evidência documental é rasa**: o pipeline R1C.1 classifica trechos do PDF por palavra-chave (`_EVIDENCE_PATTERNS`), sem fatos estruturados → não dá para responder franquia/limite/assistência com confiança nem aplicar regra de negócio.
3. **A regra de negócio do Founder não existe como política**: residencial + assistência 24h confirmada ⇒ eletricista/chaveiro/hidráulica; hoje só há regex de sinais.
4. **A resposta despeja evidência técnica**: `_summarize`/`_summarize_detail` produzem lista técnica, não resposta de copiloto humano.
5. **Nada disso tem prova ponta a ponta**: 271 testes offline provam contratos puros; nenhum prova o Chat real do turno 1 ao turno N.

## 2. Escopo (o que ESTA spec entrega em produção)

```text
E1  Contexto anafórico determinístico (o fix do "ela")
E2  Policy Facts mínimos (fatia 1 do ex-R1C.2, reconstruída)
E3  Política governada residential_24h_standard_v1 (fatia 2)
E4  Compositor humano de resposta (fatia 3)
E5  Porta PolicyDataProvider (contrato multi-provider, InfoCap como 1ª impl.)
E6  Harness E2E com InfoCap stub + goldens multi-turno
E7  Teste real controlado na Resulta + deploy com rollback por flag
```

## 3. Fora de escopo

WhatsApp/atendente externo (Onda 2) · remoção de legado UCP (Onda 1.5) · Registry/Prompt Efetivo (Onda 3) · Auxiliares (Onda 4) · portais/RAG novo (Onda 5) · implementação Quiver · qualquer migration destrutiva · qualquer mudança em Docling/MinIO/Qdrant além do que o pipeline R1C.1 já usa.

## 4. Arquitetura da vertical

```text
Pergunta do corretor (turno N)
  ├─► [E1] Policy Context Lock (determinístico, nodes.py)
  │     estado persistido: infocap_policy_context {cliente, numapo[]}
  │     termo de detalhe? → resolve "ela/essa/dessa apólice":
  │       1 apólice no contexto → força tool com policy_number
  │       2+ apólices          → força tool em modo escolha (opções)
  │       0 contexto           → LLM decide (comportamento atual)
  ├─► InfocapPolicyLookupTool → [E5] PolicyDataProvider(port)
  │     cadeia canônica existente (INALTERADA): cliente → /cliente →
  │     /cliente_ligacoes → /documento → identity gate P0 (fail-closed)
  ├─► [E2] PolicyFactsExtractor
  │     entrada: evidence pack + evidência documental R1C.1 (cacheada)
  │     saída:  policy_facts[] tipados com fonte/página/confiança
  ├─► [E3] AssistancePolicyEngine
  │     residential_24h_standard_v1 (versionada, auditável)
  ├─► [E4] HumanAnswerComposer → Policy Response Contract (existente)
  └─► Output guard existente (nodes.py) — inalterado no mecanismo,
      ampliado nos required_facts
```

### 4.1 E1 — Contexto anafórico (regra exata)

Em `_policy_context_tool_args` (nodes.py), acrescentar:

- SE pergunta contém termo de `_POLICY_DETAIL_TERMS` E `infocap_policy_context` tem `document|name`:
  - `len(policy_numbers) == 1` → tool call forçado com esse `policy_number` (mesmo sem número no texto);
  - `len(policy_numbers) > 1` E pergunta contém referência anafórica (`ela|essa|dessa|esta|a apolice|a apólice`) sem número → tool call de listagem (document/name sem policy_number) → contrato `ambiguous_policy` já existente pede a escolha;
  - número literal no texto continua tendo prioridade (comportamento atual preservado).
- `infocap_policy_context` ganha `selected_policy_number` (persistido no checkpoint): definido quando um detalhe retorna `found`; a partir daí "ela" resolve para a apólice selecionada mesmo com catálogo de 2+.
- Reset do contexto: novo cliente pesquisado (document/name diferente) substitui o contexto inteiro. Nunca cruza sessão/tenant (thread_id já é `company:session`).

### 4.2 E2 — Policy Facts mínimos (schema)

```text
PolicyFact {
  fact_type: coverage | assistance | deductible | limit | installment |
             exclusion | validity | premium
  label: str                      # humano, ex. "Assistência Residencial 24h"
  value: str|num|null             # ex. "R$ 1.500,00", "24h", null
  source: infocap_structured | official_document | policy_rule
  source_detail: {page?, snippet?, provider_field?, rule_id?}
  confidence: high | medium | low
  policy_locator_hash: str
}
```

Regras duras (herdam P0/R1B): código curto (`P`, `A`...) nunca vira label; campo financeiro sem semântica → `provider_field` (não vira fact); fact de `official_document` exige página+trecho; ausência de facts = ausência declarada (nunca inventa). Extração documental: evoluir `extract_policy_document_evidence` para emitir facts tipados a partir dos snippets classificados — mesmo pipeline, sem parser paralelo. Minerar do stash R1C.2 **apenas por leitura** (`git stash show -p` no repo principal, sem aplicar).

### 4.3 E3 — Política `residential_24h_standard_v1`

```text
id: residential_24h_standard_v1        version: 1    status: active
trigger (TODAS obrigatórias):
  - line_kind/ramo residencial confirmado pela fonte
  - PolicyFact{assistance} confirmando assistência residencial/24h
    (fonte estruturada OU documental; NUNCA só o ramo/produto — G37/G72)
effect:
  standard_services = [eletricista, chaveiro, hidraulica_encanador]
  statement = "com Assistência 24h confirmada nesta apólice, os serviços
               padrão incluem eletricista, chaveiro e hidráulica"
audit: toda aplicação gera trace {rule_id, version, facts_used[]}
override: estrutura preparada por (insurer, product, plan, company) — vazia na v1
```

Implementação: módulo Python puro + tabela `platform_policies` (id, version, definition jsonb, status) — migration aditiva única (APPLY→VERIFY→ROLLBACK; rollback = ignorar tabela, flag off). A LLM NUNCA decide a regra; ela apenas redige sobre o resultado.

### 4.4 E4 — Compositor humano

Entrada: status + facts + política aplicada + pergunta. Saída: resposta natural de copiloto, com: resposta direta primeiro; fonte citada quando documental ("apólice oficial, pág. X"); ausência honesta clara; opções numeradas quando ambíguo; sem jargão interno (nunca expor `nosnum`, locator, `evidence_pack`). O texto do compositor vira o `rendered_safe_answer` do contrato; `required_facts` ganham `assistance_policy_applied` quando E3 disparou. Guard existente permanece o mecanismo de imposição.

### 4.5 E5 — Porta PolicyDataProvider

Extrair de `infocap_connector.py` a INTERFACE (sem mover lógica ainda — o fatiamento físico é Onda 3):

```text
PolicyDataProvider(Protocol):
  lookup(query: PolicyQuery) -> PolicyReadResult      # DTO canônico existente
  detail(locator: PolicyLocator) -> PolicyReadResult
  provider_key: str                                    # "infocap", futuro "quiver"
```

`PolicyLocator` já é `provider:...` — formalizar o parse genérico. A tool passa a falar com a porta; a InfoCap é a implementação registrada. Critério: nenhuma assinatura nova menciona "infocap" fora da implementação concreta.

## 5. Estado conversacional

`infocap_policy_context` (checkpoint LangGraph, por `company:session`): `{document?, name?, policy_numbers[], selected_policy_number?, source}` — sem locator técnico, sem PII além do necessário, nunca logado com valores. Já persiste entre turnos hoje; E1 só o consome/atualiza melhor.

## 6. Origem de dados e regras de fonte

| Pergunta | Fonte 1 | Fonte 2 (se 1 insuficiente) | Nunca |
|---|---|---|---|
| Dados operacionais (vigência, parcelas, status) | Provider estruturado | — | inventar |
| Cobertura/franquia/limite/exclusão | Provider estruturado | PDF oficial (R1C.1, cache) | RAG amplo, palpite |
| Serviços de assistência padrão | PolicyFact{assistance} + política E3 | — | inferir só do ramo |
| Conceitos gerais de seguro | conhecimento do modelo + knowledge global | — | vender como fato da apólice |

Cache documental: chave `company + provider + policy_locator_hash + content_hash` (existente). Segunda pergunta da mesma apólice NÃO refaz fetch (G67/G79).

## 7. Multi-tenant

Sem mudança de mecanismo: conexão via `tenant_connections`+Vault (resolução única backend); thread por `company:session`; documentos/Qdrant filtrados por company + document_type + locator (G74/G115). Goldens de isolamento re-executados no aceite.

## 8. Arquivos candidatos (ordem de toque)

```text
backend/app/agents/nodes.py                       E1 (context lock) + required_facts
backend/app/agents/state.py                       selected_policy_number no contexto
backend/app/services/policy_document_evidence_service.py   E2 (facts tipados)
backend/app/services/policy_facts.py              NOVO — extractor + tipos (puro)
backend/app/services/assistance_policy.py         NOVO — E3 (puro) + loader da tabela
backend/app/services/policy_answer_composer.py    NOVO — E4 (puro)
backend/app/agents/tools/infocap_tool.py          usa composer p/ rendered_safe_answer
backend/app/api/infocap_connector.py              só integração dos pontos acima + porta E5
backend/app/providers/policy_data_provider.py     NOVO — interface E5
backend/supabase/migrations/xxx_platform_policies.sql   migration aditiva (E3)
backend/tests/…                                   novos goldens + harness E2E
```

Proibido nesta SPEC: tocar `graph.py` além do necessário p/ estado; tocar prompts como "solução"; criar endpoint novo; criar storage/RAG paralelo.

## 9. Testes

**Unitários (puros, offline)** — G-A1 uma apólice + "ela tem assistência?" força tool; G-A2 duas apólices + anáfora → listagem/escolha; G-A3 escolha feita → "ela" gruda na selecionada; G-A4 novo cliente reseta contexto; G-F1..Fn facts: código curto não vira fact, financeiro sem semântica não vira fact, fact documental exige página; G-P1 política dispara com residencial+assistência confirmada; G-P2 NÃO dispara só com ramo (G37); G-P3 trace de auditoria emitido; G-C1..Cn compositor: resposta direta, fonte citada, ausência honesta, sem jargão técnico.

**Integração (offline, stubs)** — tool→porta→facts→política→composer→contrato→guard, nos status: found, ambiguous, mismatch (fail-closed intacto), source_limited, evidence_ready, cache hit.

**E2E com InfoCap stub (E6)** — servidor HTTP local com fixtures sintéticas servindo `/login, /lista_clientes, /cliente, /cliente_cpf, /cliente_ligacoes, /documentos, /documento` + PDF sintético; conversa completa de 6+ turnos contra o backend real (grafo real, LLM real ou fake-LLM determinístico para CI): busca → escolha → detalhe → "ela tem assistência?" → resposta com política → repetição usa cache. Suíte offline existente (271) permanece 100%.

**Teste real controlado (E7)** — protocolo D-Q6 do programa: apólice sintética na InfoCap da Resulta se possível; senão apólice real autorizada com logs redigidos; roteiro de 10 perguntas do Founder + operador; resultado anexado ao aceite.

## 10. Critérios de aceite

1. As 10 perguntas do roteiro real respondidas com cliente/apólice corretos, fonte correta e zero `identity_mismatch` indevido.
2. "ela tem assistência?" resolve sem repetir número — nos 3 cenários (1 apólice, 2+, pós-escolha).
3. Assistência residencial: resposta cita a política e os 3 serviços SOMENTE com assistência confirmada; com só o ramo, resposta declara que não há confirmação.
4. Cache hit comprovado (segunda pergunta sem novo fetch — verificado por log seguro).
5. Nenhum log com PII/URL/token (amostragem manual + greps automatizados).
6. Suíte completa verde: unit + integração + E2E stub + 271 legadas.
7. Aceite assinado: Founder + operador Resulta (checklist próprio).

## 11. Rollback

Flag única `POLICY_INTELLIGENCE_V2` (env): OFF ⇒ comportamento do baseline `e7c5044` (context lock antigo, sem facts/política/composer — código novo inerte). Migration `platform_policies` é aditiva: fica órfã sem efeito com a flag OFF. Remoção da flag só após 2 semanas estáveis em produção.

## 12. Métricas (log seguro, sem PII)

`policy_context_lock_hits` (por cenário A1/A2/A3) · `facts_extracted_count` por fonte · `assistance_policy_applied_count` · `document_cache_hit_rate` · `identity_mismatch_count` · `guard_replacement_count` (quanto o guard corrigiu a LLM) · latência p50/p95 do turno com tool.

## 13. Riscos

| Risco | Mitigação |
|---|---|
| Regra anafórica disparar tool em falso positivo | termos restritos + exigir contexto com cliente; métrica de lock hits; flag |
| Facts documentais com classificação errada | fact exige página+trecho; confidence; ausência honesta como default |
| Política aplicada sem assistência real | trigger exige fact de assistência confirmado (nunca ramo) — testes G-P2 |
| Regressão no fail-closed P0 | goldens P0 existentes rodam no CI da SPEC; qualquer falha bloqueia merge |
| Latência do pipeline documental no 1º hit | fetch só sob demanda (existente) + cache; medir p95 |

## 14. Plano de deploy

1. Branch `feat/spec-016-policy-intelligence` a partir de `main` (worktree de execução dedicado; auditoria intocada).
2. Merge para `main` somente com suíte completa verde + revisão adversarial.
3. Deploy no ambiente EasyPanel com `POLICY_INTELLIGENCE_V2=false` → smoke → ligar flag só para a company da Resulta (gate por company se necessário: leitura da flag + allowlist de company_id em env).
4. Teste real controlado (E7) → aceite → flag global ON.
5. Rollback: flag OFF (segundos), revert do merge se necessário (documentado).

---

## 15. Registro de implementação (2026-07-03)

Fatias entregues na branch, cada uma com TDD (RED antes de GREEN) e commit próprio:

| Fatia | Commit | Conteúdo |
|---|---|---|
| E1 | 60c40ba | Context lock anafórico v2 em `nodes.py` (+ `feature_flags.py`) |
| E2 | 082f16a | `services/policy_facts.py` — facts tipados sem invenção |
| E3 | 8f9c17d | `services/assistance_policy.py` — residential_24h_standard_v1 |
| E4 | 4dbd8dc | `services/policy_answer_composer.py` + integração tool/contrato/guard |
| E5 | d3df42a | `providers/policy_data_provider.py` — porta multi-provider (Quiver-ready) |
| E6 | c3e4e64 | Harness E2E com InfoCap stub HTTP local + guard de pergunta conceitual (G-A5) |

Verificação: suíte completa 100% verde — 9 arquivos de teste, 376 checks
(271 legadas + 84 SPEC unit/integração + 21 E2E; E2E rodado 10x sem flake).

Desvios conscientes em relação ao texto original desta SPEC:

1. **Sem migration nesta onda.** A política `residential_24h_standard_v1` está
   versionada em código puro (`assistance_policy.py`). A tabela
   `platform_policies` fica para quando existir o primeiro override por
   seguradora/produto/corretora (Onda 2+). Motivo: gate de migration exige
   aprovação e não há necessidade funcional agora — menos risco, mesmo efeito.
2. **`state.py` não precisou mudar** — `infocap_policy_context` já era dict; o
   campo `selected_policy_number` entra pelo mesmo canal seguro.
3. **E2E cobre a cadeia conector→facts→política→compositor→guard com httpx real
   e servidor stub local**, mais a conversa multi-turno no nível dos nós do
   grafo. O streaming LangGraph completo com LLM real fica para o teste real
   controlado (E7) — offline não há provedor LLM.
4. **`httpx` instalado no Python local apenas para o harness E2E** (já é
   dependência real do backend em produção; nada novo em requirements).
5. **Guard adicional G-A5**: pergunta conceitual ("o que é franquia?") não é
   convertida em consulta operacional forçada — achado da revisão adversarial.
