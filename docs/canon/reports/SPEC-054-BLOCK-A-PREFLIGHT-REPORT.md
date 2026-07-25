---
> **Status:** relatório de preflight — READ-ONLY
> **SPEC:** SPEC-054 — Foundation Hardening & Schema Governance · **Bloco A**
> **Branch:** `feat/spec054-foundation-hardening`
> **Worktree:** `AutoBrokers-Opus-Exec`
> **Commit auditado:** `2c6353053b33e29e578c5c59a71101059ed37df8`
> **Data:** 25/07/2026
> **Veredito:** `BLOCKED_BY_ACCESS` — prontidão técnica `READY_WITH_REQUIRED_BACKFILL`
---

# Preflight do Bloco A — SPEC-054

## 0. Declaração de integridade

Durante este preflight **não** foram executados: migration, `REVOKE`, `GRANT`, `ALTER FUNCTION`, alteração de view, alteração de bucket, backfill, criação de signed URL, deploy, restart, write no Supabase ou alteração de infraestrutura.

Nenhuma mensagem foi enviada. Nenhum segredo, hash, token, URL sensível ou PII foi reproduzido. As únicas escritas foram este documento e arquivos `__pycache__` locais (gitignorados) gerados pela verificação de sintaxe.

---

# 1. Estado inicial

## 1.1 Repositório

| Campo | Valor |
|---|---|
| `main` incorporada | `2c6353053b33e29e578c5c59a71101059ed37df8` |
| Branch de trabalho | `feat/spec054-foundation-hardening` |
| Base da branch | `origin/main` (pós-merge da Fase 0) |
| Worktree | `AutoBrokers-Opus-Exec` |
| `git status` | limpo |
| Documentos da Fase 0 | todos presentes |

## 1.2 Projeto Supabase

| Campo | Valor |
|---|---|
| Ref | `dcajcvlzcjbmyapmklil` |
| Região | `us-east-2` |
| Status | `ACTIVE_HEALTHY` |
| Postgres | `17.6.1.127` (engine 17, canal `ga`) |
| Criado em | 2026-06-04 |
| Tamanho do banco | 27 MB |
| Conexões ativas no momento | 15 |
| `pg_cron` instalado | não |

## 1.3 Schema vivo

| Métrica | Valor |
|---|---|
| Tabelas `public` | 78 |
| Views `public` | 1 |
| RLS habilitado | 78 |
| **RLS com zero policies** | **28** |
| Migrations rastreadas | 21 (última `20260723183305`) |
| Usuários (`users_v2`) | 9 |
| Vínculos (`company_members`) | 10 |
| Empresas | 5 (das quais **3 técnicas**) |

## 1.4 Advisors de segurança — baseline pré-mudança

| Nível | Lint | Qtd |
|---|---|---:|
| **ERROR** | `security_definer_view` | **1** |
| WARN | `function_search_path_mutable` | 17 |
| WARN | `anon_security_definer_function_executable` | 12 |
| WARN | `authenticated_security_definer_function_executable` | 12 |
| WARN | `public_bucket_allows_listing` | 3 |
| INFO | `rls_enabled_no_policy` | 28 |
| | **Total** | **73** |

Este é o número que o VERIFY do Bloco A deve reduzir.

---

# 2. Infraestrutura e backup

## 2.1 O que foi possível confirmar

| Item | Estado | Fonte |
|---|---|---|
| Supabase — saúde | `ACTIVE_HEALTHY` | API de projeto |
| Supabase — versão | PG `17.6.1.127`, canal `ga` | API de projeto |
| Supabase — região | `us-east-2` | API de projeto |
| Tamanho do banco | 27 MB | consulta read-only |

## 2.2 O que NÃO foi possível confirmar

| Item | Estado |
|---|---|
| Backup do Supabase | **não auditável** pelas ferramentas disponíveis |
| PITR habilitado | **desconhecido** |
| Data do último backup | **desconhecida** |
| Retenção | **desconhecida** |
| Estratégia de restore | **inexistente documentalmente** |
| EasyPanel — serviços, réplicas, imagens, health | **sem acesso** |
| API / Web — versão em produção | **sem acesso** |
| Redis produção | **sem acesso** |
| Qdrant produção | **sem acesso** |
| MinIO produção | **sem acesso** |
| Evolution Go — instância viva | **sem acesso** |
| Workers — estado | **sem acesso** |

## 2.3 Consequência

```text
FIRST_PRODUCTION_WRITE_BLOCKED
```

Conforme [`MIGRATIONS-AUTHORITY.md`](../MIGRATIONS-AUTHORITY.md) §9, nenhum write em produção é autorizado enquanto a reversibilidade não estiver comprovada. Este é o único bloqueio real do preflight — **todo o restante da auditoria foi concluído**.

Item **P1** de [`FOUNDER-DECISIONS.md`](../FOUNDER-DECISIONS.md) permanece aberto.

---

# 3. RPCs críticas

## 3.1 Assinaturas exatas confirmadas

Todas com `owner = postgres`, `SECURITY DEFINER = true` e **sem `search_path` fixado**:

| # | Assinatura exata | Retorno |
|---|---|---|
| 1 | `get_user_for_login(character varying)` | `jsonb` |
| 2 | `create_user_account(varchar,varchar,varchar,varchar,varchar,varchar,date,uuid,varchar,varchar,boolean)` | `TABLE(...)` |
| 3 | `create_user_account(varchar,varchar,varchar,varchar,varchar,varchar,date,uuid,varchar,varchar,boolean,uuid)` | `TABLE(...)` |
| 4 | `debit_company_balance(uuid,numeric)` | `numeric` |
| 5 | `get_token_usage_by_company(timestamptz,timestamptz)` | `TABLE(...)` |
| 6 | `get_token_usage_report(timestamptz,timestamptz)` | `TABLE(...)` |
| 7 | `check_and_increment_rate_limit(text,uuid,integer,integer)` | `integer` |

> **ATENÇÃO — achado que muda a migration:** a ACL das sete funções é
> `=X/postgres | postgres=X | anon=X | authenticated=X | service_role=X`.
> O `=X/postgres` significa que **`PUBLIC` também tem `EXECUTE`**, além dos grants explícitos.
> Revogar apenas de `anon` e `authenticated` **não fecha o buraco**. A migration precisa revogar de `PUBLIC` também.

## 3.2 Call sites — busca completa no repositório

| RPC | Call site | Cliente | Exposto ao browser? |
|---|---|---|---|
| `get_user_for_login` | [`lib/auth.ts:290`](../../../lib/auth.ts#L290) | `supabaseAdmin` (`SUPABASE_SERVICE_ROLE_KEY`) | não |
| `create_user_account` | [`lib/auth.ts:241`](../../../lib/auth.ts#L241) | `supabaseAdmin` (`SUPABASE_SERVICE_ROLE_KEY`) | não |
| `debit_company_balance` | [`backend/app/workers/billing_core.py:204`](../../../backend/app/workers/billing_core.py#L204) | backend service role | não |
| `get_token_usage_report` | [`app/api/admin/costs/route.ts:35`](../../../app/api/admin/costs/route.ts#L35) | `supabaseAdmin` (`SUPABASE_SERVICE_ROLE_KEY`) | não |
| `get_token_usage_by_company` | [`app/api/admin/costs/route.ts:53`](../../../app/api/admin/costs/route.ts#L53) | `supabaseAdmin` (`SUPABASE_SERVICE_ROLE_KEY`) | não |
| `check_and_increment_rate_limit` | [`backend/app/api/middleware/widget_security.py:59`](../../../backend/app/api/middleware/widget_security.py#L59) | backend service role | não |

> **FATO:** **zero** call sites usam a chave `anon` ou `authenticated`. As demais ocorrências no repositório estão em `schema_completo.sql` (histórico) e em documentação.
> **CONCLUSÃO:** o risco de revogação para as seis RPCs é **mínimo**. Nenhum caminho legítimo do produto depende de execução pública.

## 3.3 Decisão por função

### `get_user_for_login(character varying)`

Retorna `jsonb` **incluindo `password_hash`**. Chamada exclusivamente por `lib/auth.ts:290` com service role.

- **APPLY:** `REVOKE EXECUTE FROM PUBLIC, anon, authenticated`; `GRANT EXECUTE TO service_role`; fixar `SET search_path = pg_catalog, public`.
- **Evolução preferencial (SPEC-054 §7.1.5):** substituir a RPC por consulta server-side explícita com seleção mínima. Como há apenas 1 consumidor, isso é viável dentro do Bloco A; se o custo de regressão for alto, manter revogada e marcada `deprecated`.
- **VERIFY:** `has_function_privilege('anon', <oid>, 'EXECUTE') = false`; login continua funcionando; `password_hash` não aparece em nenhuma resposta HTTP.
- **ROLLBACK:** `GRANT EXECUTE TO service_role` (restaurar apenas o caminho de serviço, **nunca** reabrir para `anon`).
- **Risco:** baixo.

### `create_user_account(...)` — duas overloads

Aceitam `company_id`, `role` e `is_owner` do chamador. Chamada por `lib/auth.ts:241` com service role.

- **APPLY:** revogar `PUBLIC`/`anon`/`authenticated` das **duas** assinaturas exatas; `GRANT` só a `service_role`; fixar `search_path`.
- **Identificar a assinatura canônica em uso:** `lib/auth.ts:241` deve ser lido no Bloco A para determinar se usa 11 ou 12 argumentos. A overload não usada só é removida após confirmação de zero consumidores.
- **VERIFY:** signup legítimo funciona; tentativa de signup enviando `role=admin_company`/`is_owner=true` pelo client é ignorada ou rejeitada; `anon` não executa.
- **ROLLBACK:** restaurar grant de `service_role` apenas.
- **Risco:** baixo–médio (signup é caminho crítico; exige teste antes/depois).

### `debit_company_balance(uuid,numeric)`

Altera `company_credits` sem validar chamador, sinal ou idempotência. Chamada por `billing_core.py:204`.

- **APPLY:** revogar público; `GRANT` a `service_role`; fixar `search_path`; validar `p_amount > 0`.
- **Escopo do Bloco A:** o mínimo transacional seguro. A idempotência com ledger é da **SPEC-062** (D4). Se o contrato atual não permitir validação sem breaking change, criar assinatura versionada nova e manter a anterior revogada/deprecated.
- **VERIFY:** `anon` não executa; débito continua funcionando pelo worker; valor negativo é rejeitado.
- **ROLLBACK:** restaurar assinatura anterior com grant de `service_role`.
- **Risco:** médio — toca billing. Testar com o worker antes de encerrar o bloco.

### `get_token_usage_by_company` e `get_token_usage_report`

Agregam custo de **todas** as corretoras sem filtro de tenant. Chamadas por `app/api/admin/costs/route.ts` com service role.

- **APPLY:** revogar público; `GRANT` só a `service_role`; fixar `search_path`.
- **Observação fora do escopo do Bloco A:** [`app/api/admin/costs/route.ts:19`](../../../app/api/admin/costs/route.ts#L19) autoriza apenas pela **presença** do cookie `smith_admin_session`, sem validar papel server-side. Isso é o problema descrito na SPEC-061 §3.2.2 e pertence à **Etapa 4** do Master Plan. Registrar, não corrigir aqui.
- **VERIFY:** `anon`/`authenticated` não executam; página Admin de custos continua funcionando.
- **Risco:** baixo.

### `check_and_increment_rate_limit(text,uuid,integer,integer)`

Chamada por `widget_security.py:59` (backend). Não estava na lista original de P0 da auditoria de 24/07, mas é `SECURITY DEFINER`, executável por `anon` e **sem `search_path`**.

- **APPLY:** revogar público; `GRANT` a `service_role`; fixar `search_path`.
- **Risco:** baixo — mas verificar se o widget público depende de execução anônima. **Único ponto que exige leitura cuidadosa antes do REVOKE.**

## 3.4 Funções trigger e demais

### `SECURITY DEFINER` com `anon EXECUTE`, tipo TRIGGER (4)

`block_technical_attendance_capture()` · `enforce_technical_whatsapp_integration()` · `isolate_technical_observed_event()` · `isolate_technical_observed_session()`

Todas com `search_path=public` fixado. Trigger functions **não precisam** de `EXECUTE` público — os triggers continuam funcionando após o `REVOKE`.

### `SECURITY DEFINER` normal com `anon EXECUTE` (1)

`is_technical_company(uuid)` — `search_path=public`. Revogar público; avaliar se algum caminho legítimo a chama diretamente.

### Sem `search_path`, não `SECURITY DEFINER` (8)

`get_agent_ucp_capabilities(uuid)` · `set_auxiliary_updated_at()` · `tg_abr_immutable()` · `tg_tenant_corridors_set_updated_at()` · `update_agent_delegations_updated_at()` · `update_documents_updated_at()` · `update_ucp_updated_at()` · `update_updated_at_column()`

Risco menor (executam com privilégio do chamador), mas compõem os 17 avisos `function_search_path_mutable`. Fixar `search_path` é barato e fecha o aviso.

### Já corretas — preservar (3)

`portal_vault_probe()` · `portal_vault_read_session(uuid,text,text)` · `portal_vault_store_session(uuid,text,text,text,text)` — `SECURITY DEFINER`, `search_path = ""`, **sem** grant para `anon`. **São o modelo a seguir.**

---

# 4. View `ucp_connection_summary`

## 4.1 Estado confirmado

| Campo | Valor |
|---|---|
| Owner | `postgres` |
| `reloptions` | **vazio** — sem `security_invoker` |
| ACL | `postgres=arwdDxtm \| anon=arwdDxtm \| authenticated=arwdDxtm \| service_role=arwdDxtm` |
| Origem | `ucp_connections uc LEFT JOIN agents a`, filtro `uc.is_active = true` |
| Colunas expostas | `id, agent_id, company_id, store_url, manifest_version, preferred_transport, capabilities_count, is_active, last_used_at, created_at, agent_name` |

> **Achado adicional:** a ACL não é apenas `SELECT`. `arwdDxtm` concede **todos** os privilégios (incluindo `INSERT`/`UPDATE`/`DELETE`) a `anon` e `authenticated`. A view não é auto-atualizável por causa do `LEFT JOIN`, o que na prática impede a escrita — mas o grant é indevido e deve ser removido integralmente.

## 4.2 Consumidores

Busca completa no repositório: `ucp_connection_summary` aparece **somente** em `backend/supabase/migrations/schema_completo.sql` (histórico) e em documentação canônica.

> **FATO: zero consumidores no código da aplicação.**

## 4.3 Decisão

Sendo interna, aplica-se o primeiro ramo da SPEC-054 §7.2:

- **APPLY:** `REVOKE ALL ON public.ucp_connection_summary FROM PUBLIC, anon, authenticated;` e `GRANT SELECT TO service_role;`. Adicionalmente, definir `security_invoker = true` como defesa em profundidade, caso a view volte a ser exposta no futuro.
- **VERIFY:** `has_table_privilege('anon', 'public.ucp_connection_summary', 'SELECT') = false`; advisor `security_definer_view` sai do nível ERROR; nenhuma tela quebra (não há consumidor).
- **ROLLBACK:** restaurar `GRANT SELECT` apenas a `service_role`.
- **Risco:** **muito baixo** — é a correção mais segura do Bloco A e a única que zera o único `ERROR` dos advisors.

---

# 5. Storage

## 5.1 Inventário dos buckets

| Bucket | Público | Objetos | MB | Policies | Primeiro | Último |
|---|---|---:|---:|---:|---|---|
| `avatars` | **sim** | 0 | 0 | 4 | — | — |
| `chat-docs` | **sim** | 30 | 3,48 | **0** | 05/07 | 21/07 |
| `chat-media` | **sim** | 26 | 3,52 | 3 | 04/07 | 21/07 |
| `voice-messages` | **sim** | 0 | 0 | 2 | — | — |
| `portal-evidence` | não | 5 | 0,53 | 0 | 11/07 | 15/07 |

`chat-docs` é público **apenas pela flag do bucket** — não tem policy nenhuma. `portal-evidence` está correto: privado, sem policy, acessível só por service role.

## 5.2 Policies em `storage.objects`

**Todas as 9 policies têm `roles` vazio, o que significa role `PUBLIC`:**

| Policy | Cmd | Bucket | Efeito |
|---|---|---|---|
| `Anyone can upload to voice-messages` | INSERT | voice-messages | **upload anônimo** |
| `Anyone can read voice messages` | SELECT | voice-messages | leitura anônima |
| `Permitir upload via chat` | INSERT | chat-media | **upload anônimo** |
| `Qualquer um pode ver imagens` | SELECT | chat-media | leitura anônima |
| `Admins podem deletar` | DELETE | chat-media | exige `auth.role()='authenticated'` |
| `Public Upload Avatars` | INSERT | avatars | **upload anônimo** |
| `Public Read` | SELECT | avatars | leitura anônima |
| `Public Update Avatars` | UPDATE | avatars | **update anônimo** |
| `Public Delete Avatars` | DELETE | avatars | **delete anônimo** |

## 5.3 Estrutura de paths — boa notícia

| Métrica | Resultado |
|---|---|
| Objetos com path estruturado (`a/b`) | **61 de 61 (100%)** |
| Objetos flat (sem `/`) | 0 |
| Primeiro segmento | `04b5cdbc-…` (company real) em 60 objetos; `teste-fable/` em 1 |

> Os paths **já seguem** o formato `<company_id>/...` exigido pela SPEC-054 §7.3.3. **Não é necessário backfill de paths.** Apenas 1 objeto de teste em `chat-docs/teste-fable/` está fora do padrão.

Distribuição por MIME:

| Bucket | Conteúdo |
|---|---|
| `chat-docs` | 19 `audio/ogg` + 11 `application/pdf` |
| `chat-media` | 20 `image/jpeg` + 6 `image/png` |
| `portal-evidence` | 5 `application/pdf` |

> Observação: os áudios estão em `chat-docs`, não em `voice-messages` — que está vazio. Registrar, não corrigir no Bloco A.

## 5.4 URLs públicas persistidas no banco

Varredura de todas as colunas `text`/`varchar`/`jsonb` do schema `public` com nome relacionado a URL/path/media/file/link:

| Origem | Não-nulo | Com URL pública Supabase |
|---|---:|---:|
| **`messages.image_url`** | 12 | **12** |
| `messages.audio_url` | 0 | 0 |
| `agents.avatar_url` | 1 | 0 |
| `users_v2.avatar_url` | 0 | 0 |
| `documents.minio_path` | 9 | 0 *(MinIO, não Supabase Storage)* |
| `observed_events.media_meta` | 10 | 0 |
| `attendance_transcripts.media_meta` | 0 | 0 |
| `sanitization_jobs.*_file_path` | 0 | 0 |

As 12 URLs apontam todas para `chat-media`, criadas entre 04/07 e 15/07.

## 5.5 Classificação de risco — a pergunta decisiva

| Classe | Objetos | Detalhe |
|---|---:|---|
| Sem referência | 49 | não referenciados em nenhuma coluna do banco |
| **Referência interna** | **12** | `messages.image_url`, exibidas apenas no dashboard autenticado |
| Referência histórica | 0 | — |
| **URL pública enviada externamente** | **0** | ver abaixo |
| Desconhecido | 0 | — |

### Prova de que nenhuma URL foi enviada a cliente

| Verificação | Resultado |
|---|---:|
| Mensagens com `role <> 'user'` contendo mídia | **0** |
| `platform_sends` com URL de storage | **0** (tabela vazia) |
| `billing_sent_log` com URL de storage | **0** (4 linhas, nenhuma) |
| `conversation_logs` com URL de storage | **0** |
| `agent_activities` com URL de storage | **0** |
| `attendance_sessions` com URL de storage | **0** |

As 12 mensagens têm **`role = 'user'`** — são mídias que o cliente **enviou para dentro**, não links que o sistema enviou para fora. Distribuição: 8 `channel=web`, 3 `channel=whatsapp`, 1 `web` em `HUMAN_REQUESTED`.

> **CONCLUSÃO:** o risco `BLOCKED_BY_CLIENT_LINK_RISK` **está descartado por evidência**. Nenhuma URL pública de Storage foi entregue a um segurado ou corretor por WhatsApp, e-mail ou qualquer canal externo.
>
> O impacto de fechar os buckets é **interno**: 12 imagens deixariam de renderizar na tela de conversas do Admin até o resolver de signed URL existir.

## 5.6 Consumidores de URL pública no código

| Local | Cliente | O que faz |
|---|---|---|
| [`app/api/upload/route.ts:136`](../../../app/api/upload/route.ts#L136) | `supabaseAdmin` (**SERVICE_ROLE**) | upload server-side e retorna `getPublicUrl` ao browser |
| [`app/admin/conversations/page.tsx:534`](../../../app/admin/conversations/page.tsx#L534) | `supabase` de [`lib/supabase.ts:6`](../../../lib/supabase.ts#L6) (**ANON**) | **upload direto do browser** para `chat-media` |
| [`app/admin/conversations/page.tsx:540`](../../../app/admin/conversations/page.tsx#L540) | ANON | `getPublicUrl` de `chat-media` |
| [`app/admin/conversations/page.tsx:613`](../../../app/admin/conversations/page.tsx#L613) | ANON | **upload direto do browser** para `voice-messages` |
| [`app/admin/conversations/page.tsx:621`](../../../app/admin/conversations/page.tsx#L621) | ANON | `getPublicUrl` de `voice-messages` |

> **`createSignedUrl` tem ZERO ocorrências no repositório.** Não existe hoje nenhum caminho de URL assinada. Ele precisa ser construído **antes** de fechar os buckets.

O upload direto do browser com chave `anon` é a dependência real: quando `chat-media` e `voice-messages` deixarem de ter policy pública de INSERT, esse fluxo quebra. É exatamente o cenário que a SPEC-054 §7.3.2 antecipa ao exigir expand antes de contract.

## 5.7 Proposta para o Bloco A

**Ordem obrigatória — nunca inverter:**

```text
1. criar resolver central de Storage (path canônico + URL legada)
2. criar rota server-side de upload autorizado para chat-media e voice-messages
3. criar rota server-side de download/stream com signed URL curta
4. migrar app/admin/conversations/page.tsx para as rotas server-side
5. backfill: converter as 12 linhas de messages.image_url de URL absoluta para PATH
6. testar renderização das 12 mídias e do fluxo de upload
7. SÓ ENTÃO: tornar buckets privados e substituir as policies
8. verificar que a URL pública antiga deixou de funcionar
```

**Backfill necessário:** 12 linhas em `messages.image_url` — converter
`https://<ref>.supabase.co/storage/v1/object/public/chat-media/<path>` → `<path>`,
com o resolver aceitando ambos os formatos durante a transição.

**Volume total:** 61 objetos, 7,5 MB, 1 tenant. É o menor custo de migração que este problema jamais terá — adiar só aumenta.

**Estado final por bucket:**

| Bucket | Final | Policies |
|---|---|---|
| `portal-evidence` | privado (preservar) | nenhuma — service role |
| `chat-docs` | **privado** | nenhuma — acesso por rota server-side |
| `chat-media` | **privado** | nenhuma — acesso por rota server-side |
| `voice-messages` | **privado** | nenhuma — acesso por rota server-side |
| `avatars` | leitura pública opcional | escrita autenticada, owner-scoped |

> **Nota de arquitetura:** a SPEC-054 §7.3.5 alerta que não se deve criar policy baseada em `auth.uid()` quando a identidade do produto não está mapeada ao Supabase Auth. Este é exatamente o caso — o produto usa identidade própria (`users_v2` + `iron-session`). Portanto **a rota server-side autorizada é o caminho correto**, não policy de Storage.

---

# 6. Smoke baseline

Executado apenas de forma estática e read-only. **Nenhuma mensagem enviada, nenhuma chamada externa, nenhum serviço reiniciado.**

| Verificação | Resultado |
|---|---|
| Python disponível | 3.14.4 |
| `compileall backend/app` | **exit 0** — 184 módulos, zero erro de sintaxe |
| Arquivos de teste em `backend/tests` | 60 |
| `tsc --noEmit` | **não executado** — `node_modules` ausente no worktree novo |
| Integridade do banco | 78 tabelas, 61 objetos de storage, contagens registradas em §1 e §5 |
| Empresas técnicas isoladas | 3, com triggers de sandbox ativos e verificados |
| `git status` | limpo antes e depois |

## Pendência de baseline

O baseline de TypeScript precisa ser estabelecido **antes** do primeiro write: rodar `npm install` no worktree e registrar `tsc --noEmit` verde. Sem isso não há como provar que uma alteração em `lib/auth.ts` ou nas rotas de Storage não introduziu regressão de tipos.

Os 60 runners de teste **não** foram executados: a maioria depende de ambiente e alguns fazem inspeção de fonte. A consolidação em um pack único é **CA-006** e pertence ao Bloco C.

---

# 7. Plano de execução do Bloco A

## 7.1 Migrations

### `<timestamp>_spec054_a1_rpc_security.sql`

- **APPLY:** para cada uma das 7 assinaturas exatas — `REVOKE EXECUTE ON FUNCTION ... FROM PUBLIC, anon, authenticated;` seguido de `GRANT EXECUTE ... TO service_role;` e `ALTER FUNCTION ... SET search_path = pg_catalog, public;`. Revogar `EXECUTE` público das 4 trigger functions e de `is_technical_company`. Fixar `search_path` nas 8 funções restantes sem configuração. Aplicar `ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;` para o owner `postgres`.
- **VERIFY:** `select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.prosecdef and has_function_privilege('anon',p.oid,'EXECUTE');` deve retornar **0**.
- **ROLLBACK:** `GRANT EXECUTE TO service_role` por assinatura; **nunca** reabrir para `anon`/`PUBLIC`.
- **Destrutiva:** não. **Expand-first:** n/a (grants).

### `<timestamp>_spec054_a2_ucp_view_security.sql`

- **APPLY:** `REVOKE ALL ON public.ucp_connection_summary FROM PUBLIC, anon, authenticated;` · `GRANT SELECT TO service_role;` · `ALTER VIEW ... SET (security_invoker = true);`
- **VERIFY:** `has_table_privilege('anon','public.ucp_connection_summary','SELECT') = false`; advisor `security_definer_view` deixa de aparecer como ERROR.
- **ROLLBACK:** `GRANT SELECT ON public.ucp_connection_summary TO service_role;` e `RESET` da opção.
- **Destrutiva:** não.

### `<timestamp>_spec054_a3_storage_privacy.sql` — **somente após os passos de código**

- **APPLY:** `update storage.buckets set public=false where id in ('chat-docs','chat-media','voice-messages');` · `DROP` das 6 policies com role `PUBLIC` em `chat-media`, `voice-messages` e `avatars` de escrita · criar policy mínima de leitura para `avatars`.
- **VERIFY:** URL pública antiga retorna 400/404; rota server-side entrega o objeto; contagem de objetos inalterada (61); tenant A não acessa objeto de tenant B.
- **ROLLBACK:** preferir **proxy server-side compatível** em vez de reabrir o bucket. Reabertura só com registro de incidente.
- **Destrutiva:** não — nenhum objeto é removido.

### `<timestamp>_spec054_a4_backfill_message_media.sql`

- **APPLY:** converter as 12 linhas de `messages.image_url` de URL absoluta para path relativo.
- **VERIFY:** `select count(*) from messages where image_url like '%/storage/v1/object/public/%'` = **0**; as 12 mídias renderizam pelo resolver.
- **ROLLBACK:** reconstruir a URL absoluta a partir do path (transformação reversível).
- **Destrutiva:** não — transformação reversível, 12 linhas.

## 7.2 Alterações de código

| Arquivo | Mudança |
|---|---|
| `lib/auth.ts` | consulta server-side com seleção mínima; nunca retornar `password_hash` ao browser; preservar lockout e migração SHA-256 → bcrypt |
| **novo** `lib/storage/resolver.ts` | resolver central: aceita path canônico **e** URL legada; emite signed URL curta |
| **novo** `app/api/storage/[...path]/route.ts` | download/stream autorizado por sessão |
| `app/api/upload/route.ts` | retornar **path**, não URL pública |
| `app/admin/conversations/page.tsx` | trocar upload direto ANON pelas rotas server-side; usar resolver na renderização |
| `backend/app/api/middleware/widget_security.py` | verificar se o widget público depende de execução anônima da RPC de rate limit |

## 7.3 Ordem de deploy

```text
1. migration A1 (RPCs)          — sem dependência de código
2. migration A2 (view UCP)      — sem dependência de código
3. deploy do código de Storage  — resolver + rotas + upload/render
4. migration A4 (backfill 12)   — após o resolver estar em produção
5. verificar renderização das 12 mídias
6. migration A3 (buckets)       — ÚLTIMO passo
7. VERIFY completo + advisors
```

**Ponto exato do primeiro write em produção:** aplicação da migration **A1**. Tudo antes disso é código, teste e leitura.

## 7.4 Flags e canário

| Flag | Default | Função |
|---|---|---|
| `STORAGE_PRIVATE_MODE` | `false` | liga o resolver de signed URL sem fechar o bucket |
| `STORAGE_LEGACY_URL_COMPAT` | `true` | resolver aceita URL absoluta antiga |

Canário: **Amandus** (técnica) → **Resulta** → **AutoFleet**. Como 60 dos 61 objetos pertencem a uma única corretora, o canário de Storage é naturalmente concentrado — registrar isso no relatório final.

## 7.5 Risco residual

| Risco | Severidade | Mitigação |
|---|---|---|
| Backup não confirmado | **Alta** | **P1 — bloqueia o write** |
| Revogar `check_and_increment_rate_limit` quebrar widget público | Média | ler `widget_security.py` e o fluxo do widget antes do REVOKE |
| Signup quebrar por overload errada | Média | confirmar assinatura exata usada em `lib/auth.ts:241`; testar antes/depois |
| Upload do Admin quebrar | Média | expand-first: rota server-side entra em produção antes do bucket fechar |
| 12 mídias deixarem de renderizar | Baixa | backfill + resolver com compatibilidade legada |
| `debit_company_balance` afetar billing | Média | testar com o worker; idempotência fica na SPEC-062 |

---

# 8. Veredito

```text
BLOCKED_BY_ACCESS
```

**Motivo único:** backup, PITR e retenção do Supabase não puderam ser confirmados, e não há acesso a EasyPanel, Redis, Qdrant, MinIO nem Evolution Go. Sem reversibilidade comprovada, nenhum write em produção é autorizado — regra do `MIGRATIONS-AUTHORITY.md` §9.

**Prontidão técnica, assim que P1 for resolvida:**

```text
READY_WITH_REQUIRED_BACKFILL
```

- as 7 RPCs têm **zero** call sites públicos → revogação de risco mínimo;
- a view UCP tem **zero** consumidores → correção trivial que zera o único `ERROR` dos advisors;
- os paths de Storage **já estão** no formato canônico → **nenhum backfill de path**;
- **nenhuma URL pública foi enviada a cliente** → risco de link quebrado descartado por evidência;
- **backfill obrigatório:** 12 linhas em `messages.image_url`, reversível;
- **pré-requisito de código:** resolver de Storage e rotas server-side antes de fechar os buckets.

Vereditos descartados: `BLOCKED_BY_CLIENT_LINK_RISK` (provado que não há), `BLOCKED_BY_CRITICAL_CONFLICT` (nenhum conflito), `BLOCKED_BY_BACKUP` (não é que o backup falhou — é que não foi possível verificá-lo; a causa raiz é acesso).

---

# 9. O que o Founder precisa fornecer

| # | Item | Impacto |
|---|---|---|
| **1** | Confirmar backup/PITR do Supabase: habilitado? retenção? último ponto? | **desbloqueia o write** |
| **2** | Acesso read-only ao EasyPanel (serviços, imagens, health) | preflight de infraestrutura |
| **3** | Acesso read-only a Redis, Qdrant, MinIO e Evolution Go | preflight de infraestrutura |
| 4 | Confirmar se o widget público existe em produção e é usado | define o tratamento de `check_and_increment_rate_limit` |
| 5 | Confirmar que `backend/docker-compose.yml` não espelha produção | eleva ou mantém **CA-005** |

Itens 1 a 3 correspondem a **P1** em [`FOUNDER-DECISIONS.md`](../FOUNDER-DECISIONS.md).

---

# 10. Encerramento

- `git status`: **limpo**.
- Arquivos documentais criados nesta etapa: **este relatório**.
- Nenhum commit de código.
- Nenhuma correção aplicada.
- Bloco A **não** iniciado.
