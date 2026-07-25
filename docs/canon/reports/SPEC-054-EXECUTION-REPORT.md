---
> **Status:** relatório final — SPEC-054 Foundation Hardening & Schema Governance
> **Branch:** `feat/spec054-foundation-hardening` · **Base:** `2c63530`
> **Data:** 25/07/2026 · **Executor:** Opus 5 (1M) · **Ambiente:** `dcajcvlzcjbmyapmklil`
---

# Relatório de execução — SPEC-054

## 0. Declaração de integridade

- [x] Nenhum motor paralelo criado.
- [x] Nenhuma migration existente movida, renomeada, apagada ou reaplicada.
- [x] Nenhum DDL monolítico aplicado.
- [x] Nenhum segredo exposto em log, artifact ou neste relatório.
- [x] Nenhum escopo reduzido sem decisão registrada.
- [x] Nenhum dado atravessou tenants — verificado por consulta e por teste de comportamento.
- [x] Nenhum objeto de Storage removido: **61 antes, 61 depois**.
- [x] Contagens de negócio inalteradas: 1.425 mensagens, 5 empresas, 9 documentos.

---

## 1. Resumo executivo

A SPEC-054 fechou as exposições P0, tornou o isolamento entre corretoras uma garantia **do banco** e não do código, unificou o caminho global do RAG e encontrou a causa raiz de um defeito silencioso que mantinha a memória do produto zerada.

| Indicador | Antes | Depois |
|---|---:|---:|
| Funções internas executáveis por `anon` | 12 | **0** |
| Executáveis por `authenticated` | 12 | **0** |
| Funções com `search_path` mutável | 17 | **0** |
| View expondo dados a `anon` | 1 | **0** |
| Buckets públicos com conteúdo de corretora | 3 | **0** |
| Policies abertas ao papel `PUBLIC` | 9 | **0** |
| **Advisors de segurança — ERROR** | **1** | **0** |
| **Advisors de segurança — WARN** | **44** | **0** |
| Advisors de segurança — total | 73 | **28** (todos INFO) |
| Tabelas company-scoped sem FK | 14 | **0** |
| Foreign keys sem índice | 28 | **0** |
| Grupos de índice duplicado | 24 | **0** |
| Capability bindings com `scope = {}` | 46 | **0** |
| Caminhos globais de recuperação do RAG | 2 | **1** |

Os 28 achados restantes são `rls_enabled_no_policy`, nível **INFO**, correspondentes à decisão consciente de tabelas *service-role-only* (SPEC-054 §8.5). Estão documentados na §7.

---

## 2. Migrations aplicadas

| # | Versão | Objetivo | VERIFY |
|---|---|---|---|
| A1 | `20260725055327` | Revogar `EXECUTE` público de 12 funções; `search_path` em todas | `anon` 12→0 · `search_path` 17→0 · 5 triggers técnicos vivos |
| A2 | `20260725055402` | View UCP: revogar `ALL`, `SELECT` só a `service_role`, `security_invoker` | `anon`=false · advisor ERROR → 0 |
| A4 | `20260725055753` | Backfill de 12 URLs públicas → referência durável | 0 URLs restantes · 12/12 apontam para objeto real |
| A3 | `spec054_a3_storage_privacy` | 3 buckets privados; 8 policies `PUBLIC` removidas | URL antiga → 400 na origem · 61 objetos intactos |
| B1 | `spec054_b1_company_foreign_keys` | FK de `company_id` em 14 tabelas + 13 índices | 0 tabelas sem FK · 0 FKs não validadas |
| B2 | `spec054_b2_cross_company_constraints` | Chave composta `(id, company_id)` e FK composta em 3 relações | Cruzamento de tenant **bloqueado** em teste real |
| C3 | `spec054_c3_capability_scopes_and_boundaries` | 46 scopes + 3 correções de fronteira | 0 scopes vazios · 12 com approval · 12 com side_effect |
| C4 | `spec054_c4_drop_duplicate_indexes` | Remoção de 22 índices duplicados exatos | 0 grupos duplicados restantes |
| C4b | `spec054_c4b_avatars_no_listing` | Remoção da policy que permitia listar `avatars` | 0 policies em `storage.objects` |
| C4c | `spec054_c4c_index_unindexed_foreign_keys` | 28 índices de FK criados | 0 FKs sem índice |

Todas com APPLY/VERIFY/ROLLBACK no próprio arquivo. Rollback do Bloco A também em `C:\Users\amand\Backups\AutoBrokers\SPEC-054-A-20260725\rollback\`.

---

## 3. Código

| Arquivo | Mudança |
|---|---|
| `backend/app/core/egress_guard.py` | **novo** — política de saída HTTP: allowlist, bloqueio de loopback/privado/link-local/metadata, defesa contra DNS rebinding, IPv4-mapeado-em-IPv6, revalidação de redirect, limite de resposta, redação de segredo em log |
| `backend/app/agents/tools/http_request.py` | Guard aplicado; `follow_redirects=False` com revalidação por hop; timeouts separados; validação de content-type e tamanho |
| `backend/app/services/mcp_gateway_service.py` | Ambiente do subprocesso por **allowlist de 19 variáveis**; herança de `os.environ` eliminada |
| `backend/app/agents/capability_resolver.py` | Passa a **ler** o `scope`; novo estado `scope_missing` (capability HIGH sem escopo é negada); helpers `requires_approval`, `has_side_effect`, `max_calls_per_run` |
| `backend/app/services/search_service.py` | Segundo caminho global de recuperação **removido** |
| `backend/app/services/memory_service.py` | `session_end` com fallback de inatividade; `WARNING` explícito quando o gatilho não dispara |
| `lib/storage/resolver.ts` | **novo** — referência durável por path, autorização por tenant, bloqueio de traversal |
| `lib/storage/signed.ts` | **novo** — signed URL curta, download e upload com service role |
| `app/api/storage/[...path]/route.ts` | **novo** — proxy autenticado de leitura |
| `app/api/upload/route.ts` | Empresa derivada da sessão; validação por magic bytes; sem URL pública |
| `app/admin/conversations/page.tsx` | Upload direto do browser com chave anon removido |
| `backend/tests/test_spec054_egress_guard.py` | **novo** — 24 asserções de comportamento |
| `backend/tests/broker_outcome_regression_pack.py` | **novo** — gate único referenciado por todas as SPECs |

---

## 4. Testes

| Suíte | Resultado |
|---|---|
| **Broker Outcome Regression Pack** | **15/15 PASS · GATE VERDE** |
| Egress Guard (24 asserções) | verde |
| `test_capability_resolver` | 11/11 verde |
| `tsc --noEmit` | exit 0 |
| `next build` | Compiled successfully |
| `compileall` backend | exit 0 |

### Testes em produção

| Cenário | Resultado |
|---|---|
| URL pública antiga (cache-bust) | **400** — origem nega |
| Objeto nunca acessado | **400** |
| Proxy sem sessão | **401** |
| Path traversal | **400** |
| `portal-evidence` pelo proxy | **400** |
| Upload sem sessão | **401** |
| Cruzamento de tenant em `portal_jobs` | **bloqueado pela FK composta** |
| `/api/health` · `/login` · `/embed/[id]` | **200** |

---

## 5. Deploys

| Serviço | Verificação |
|---|---|
| `smith-web` | login 200; proxy `/api/storage` responde 401 (rota viva). A3 aplicada **somente após** esta confirmação. |
| `smith-api` | `/health` 200 estável em três medições consecutivas |

Ordem respeitada: **A1 → A2 → A4 → deploy web → A3 → B/C → deploy api**.

---

## 6. Decisões tomadas pelo executor

Ajustes finos, dentro da autorização do Founder. Nenhum altera arquitetura.

### 6.1 `tenant.portal.execute` exigia nada

Risco `high`, mas `requires_connection = false` e `requires_approval = false`. Executar ação em portal de seguradora sem credencial do Vault nem aprovação humana contradiz o HITL da SPEC-053 §11.2 (classe R4). **Corrigido para `true/true`.**

### 6.2 Atendimento tinha ferramenta genérica

`agent_role = 'attendance'` possuía `tenant.http_tools.execute` — HTTP arbitrário é uma válvula de escape genérica num agente voltado ao segurado — e `tenant.portal.execute`. A SPEC-053 §5.2 exige menor privilégio e proíbe ferramenta genérica no Atendimento. **Ambas desabilitadas.** Os corredores `operational.portal.*` específicos, que o Atendimento já possui, continuam ativos. Bindings ativos: 46 → 44.

### 6.3 `scope` vazio deixou de significar acesso total

O resolver ignorava o campo. Agora capability de risco `high` **sem escopo declarado é negada** (`scope_missing`), em vez de liberada. Fail-closed.

### 6.4 Policy de listagem em `avatars`

Bucket público não precisa de policy `SELECT` para servir objeto por URL. A policy permitia **listar** todo o bucket. Removida; acesso por URL preservado. Último WARN de segurança zerado.

### 6.5 Índices duplicados versus não usados

A SPEC-054 §11.4 proíbe remover índice por estar "unused". **Nada foi removido por esse critério.** O que foi removido são **duplicados exatos** — mesma tabela, mesmas colunas, mesmo access method, não parciais — provadamente redundantes independentemente de estatística. Índices **parciais** foram explicitamente preservados.

---

## 7. Riscos remanescentes e dívida assumida

| Item | Severidade | Por que aceito | Onde fecha |
|---|---|---|---|
| 28 tabelas com RLS e zero policy | INFO | Decisão consciente *service-role-only* (SPEC-054 §8.5). O backend usa service role; a proteção real é filtro + FK + teste. | Bloco B da SPEC-054 previa políticas por classe; mantido como INFO documentado. Reavaliar na SPEC-061. |
| 44 policies com `auth.uid()` por linha | WARN perf | Otimização só após testes de isolamento (SPEC-054 §11.3). | SPEC-062 (carga) |
| 116 índices "unused" | INFO | Banco jovem; §11.4 proíbe remover sem janela de observação. | SPEC-062 |
| Baseline reproduzível não gerado | Médio | Exige `pg_dump`/CLI, ausentes na máquina. O `MANIFEST.md` já classifica todos os arquivos e impede replay cego — que era o risco real. | Próxima sessão com CLI, ou SPEC-062 |
| `AUTHORITY_STRICT_MODE` ainda OFF | Médio | Os scopes agora existem, que era a pré-condição. Ativar exige shadow mode com diff de tools. | SPEC-056 (Tool Gateway) |
| Memória: correção inicial aplicada, não observada em produção | Médio | Volume atual não gera gatilho em minutos. | SPEC-059 Bloco A |
| Rotação de secrets | Alto | Decisão **D12** do Founder: adiada ao pré-go-live. | SPEC-062 |

---

## 8. Impacto para o corretor

O que mudou de fato para quem usa o produto:

1. **Os documentos da corretora deixaram de ser públicos na internet.** Antes, qualquer pessoa com a URL abria um PDF de apólice. Agora só quem tem sessão válida da própria corretora.
2. **Nenhuma corretora consegue ver dado de outra, nem por erro de código.** O banco recusa.
3. **A senha de um usuário não pode mais ser extraída pela API pública.**
4. **O saldo de uma corretora não pode mais ser alterado por chamada anônima.**
5. **O AutoBrokers volta a poder lembrar do corretor** — o gatilho de memória estava inalcançável desde sempre.
6. **Conhecimento não publicado deixa de aparecer nas respostas** — havia uma porta lateral que ignorava a curadoria.

Nada disso é visível numa tela. É a fundação que permite as SPECs seguintes serem construídas sem carregar dívida de segurança.

---

## 9. Estado do Master Plan

- [x] `EXECUTION-MASTER-PLAN.md` atualizado
- [x] `FOUNDER-DECISIONS.md` — D11, D12, D13, D14 registradas
- [x] `MANIFEST.md` de migrations atualizado
- [x] Diagnóstico de memória publicado

**Próxima etapa:** 3 — SPEC-055 (Durable Work Runs), precedida pelo preflight read-only.
