# AUDITORIA READ-ONLY — Fundação para a SPEC-054

## Foundation Hardening & Schema Governance do AutoBrokers

**Produto:** AutoBrokers Intelligence OS  
**Data da auditoria:** 24/07/2026  
**Status:** CONCLUÍDA — READ-ONLY  
**Projeto Supabase auditado:** `AutoBrokers Intelligence OS`  
**Project ref:** `dcajcvlzcjbmyapmklil`  
**Commit GitHub auditado:** `bfda921a4446872355f2084fa9d546493d38c80b`  
**Autoridade superior:** SPEC-052 e SPEC-053  
**Objetivo:** produzir o diagnóstico factual que orientará a criação da SPEC-054, sem alterar banco, código, infraestrutura, Edge Functions, buckets, permissões, migrations ou produção.

---

## 0. Declaração de integridade da auditoria

Durante esta auditoria:

- nenhuma migration foi aplicada;
- nenhum SQL de escrita foi executado;
- nenhuma policy foi criada, alterada ou removida;
- nenhum grant foi alterado;
- nenhum bucket foi modificado;
- nenhum arquivo de produção foi alterado;
- nenhum deploy foi realizado;
- nenhum serviço foi reiniciado;
- nenhum dado de negócio foi exportado;
- nenhum segredo, hash, token, senha ou credencial foi reproduzido neste documento.

As únicas escritas realizadas são este relatório documental e sua referência no GitHub.

---

# 1. Resumo executivo

A base atual do AutoBrokers é funcional e possui boas fundações, mas **não está pronta para receber o crescimento do Work OS sem uma etapa de hardening**.

O diagnóstico central é:

```text
O problema não é ausência total de segurança ou ausência total de arquitetura.
O problema é uma fundação que evoluiu rápido, com boas peças,
mas acumulou deriva entre banco, migrations, código, grants, policies e runtime.
```

Principais conclusões:

1. O Supabase de produção possui **78 tabelas públicas, uma view pública e três tabelas no graveyard**.
2. Todas as 78 tabelas públicas têm RLS habilitado.
3. Porém, **28 tabelas têm RLS habilitado e zero policies**.
4. Isso bloqueia `anon`/`authenticated`, mas **não protege operações feitas com `service_role`**, que é o cliente usado amplamente pelo backend e pelo Next.js server-side.
5. Há **exposições críticas de funções `SECURITY DEFINER` executáveis por `anon` e `authenticated`**.
6. Uma dessas funções pode retornar o `password_hash` de um usuário a partir do e-mail.
7. Outra permite criar conta informando `company_id`, papel e condição de proprietário.
8. Outra permite debitar saldo de uma empresa informando `company_id` e valor.
9. Funções de relatório de custo podem retornar dados agregados de todas as corretoras.
10. Há uma view `ucp_connection_summary` criada pelo usuário `postgres`, sem `security_invoker`, com privilégios concedidos a `anon` e `authenticated`.
11. O bucket `chat-docs` está público e contém documentos; `chat-media`, `voice-messages` e `avatars` também possuem exposição pública ampla.
12. O histórico oficial do Supabase registra somente 21 migrations, iniciadas em 08/07/2026, enquanto o repositório contém migrations fundamentais anteriores e estruturas criadas manualmente.
13. Há tabelas reais sem migration canônica reproduzível no diretório oficial de migrations.
14. Existem 14 tabelas reais com `company_id` sem foreign key para `companies`; felizmente, nenhum órfão foi encontrado nelas no momento da auditoria.
15. O Capability Registry possui 46 bindings, mas **todos os 46 têm `scope = {}`**.
16. Não há nenhum entitlement por tenant registrado.
17. `AUTHORITY_STRICT_MODE` continua desligado por padrão.
18. A ferramenta HTTP dinâmica possui risco de SSRF e vazamento em logs, embora atualmente não exista nenhuma HTTP tool cadastrada.
19. O MCP Gateway herda todo o `os.environ` para subprocessos e ainda não possui sandbox; atualmente não há MCPs cadastrados, portanto o risco está dormente.
20. Rotinas e portal worker possuem claims atômicos e mecanismos úteis de recuperação, mas ainda não têm idempotência universal de side effects.
21. O banco atual não apresenta órfãos ou cruzamentos de tenant nas verificações executadas sobre rotinas, portais e auxiliares.
22. A correção deve ser progressiva, em blocos pequenos, com APPLY/VERIFY/ROLLBACK e sem recriar Smith, Vault, scheduler ou runtime.

## Veredito

```text
A fundação não deve ser reescrita.
Ela deve ser normalizada, fechada e tornada reproduzível.

A SPEC-054 deve começar por segurança crítica,
depois consolidar schema/migrations/RLS,
e só então endurecer tools, MCPs e Authority Strict.
```

---

# 2. Fontes e método

## 2.1 Fontes de verdade consultadas

### Banco vivo

Foram consultados em modo read-only:

- catálogo `pg_class` e `pg_namespace`;
- `information_schema.columns`;
- constraints;
- foreign keys;
- índices;
- triggers;
- functions e grants;
- policies RLS;
- buckets e policies do Storage;
- `supabase_migrations.schema_migrations`;
- Supabase Security Advisors;
- Supabase Performance Advisors;
- contagens e verificações de integridade sem leitura de conteúdo sensível.

### GitHub `main`

Foram auditados, entre outros:

- `docs/canon/specs/SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`;
- `docs/canon/specs/SPEC-053-autobrokers-work-os-core-harness.md`;
- `docs/canon/ADR-001-runtime.md`;
- `docs/canon/SPEC-002-auxiliares-runtime-smith.md`;
- `docs/canon/specs/SPEC-019-rotinas-auxiliares-claude-parity.md`;
- `backend/app/core/database.py`;
- `backend/app/agents/graph.py`;
- `backend/app/agents/capability_resolver.py`;
- `backend/app/services/tool_authority.py`;
- `backend/app/agents/tools/http_request.py`;
- `backend/app/services/mcp_gateway_service.py`;
- `backend/app/agents/tools/mcp_factory.py`;
- `backend/app/services/routine_engine.py`;
- `backend/portal_worker/worker.py`;
- migrations de Rotinas, Portais, Capability Registry e isolamento multiempresa;
- testes de isolamento existentes.

### Snapshot histórico de maio

O arquivo `SUPABASE_SCHEMA_SNAPSHOT_AUTOBROKERS_2026_05.md` foi usado somente como evidência histórica.

Ele foi gerado em 28/05/2026 e descreve majoritariamente a estrutura antiga ResultVision/Agent OS, com tabelas como:

- `brokers`;
- `cases`;
- `case_events`;
- `broker_*`;
- `rag.documents`;
- `rag.chunks`;
- `protocol_*`.

Essa estrutura não representa o schema operacional atual do Smith e **não pode ser usada como baseline de migration da SPEC-054**.

## 2.2 Regra de rigor

- **CONFIRMADO:** verificado diretamente no banco vivo ou no código da `main`.
- **RISCO:** consequência técnica possível ou provável das evidências.
- **DECISÃO RECOMENDADA:** deverá ser congelada na SPEC-054 antes da execução.

---

# 3. Censo real do banco

## 3.1 Objetos principais

| Schema | Tabelas | Views | Materialized views |
|---|---:|---:|---:|
| `public` | 78 | 1 | 0 |
| `graveyard` | 3 | 0 | 0 |

## 3.2 RLS

| Métrica | Resultado |
|---|---:|
| Tabelas públicas | 78 |
| Tabelas com RLS habilitado | 78 |
| Tabelas com RLS e zero policies | 28 |
| Tabelas com coluna `company_id` | 46 |

### Correção da auditoria anterior

O relatório anterior afirmou que `routines`, `routine_runs`, `portals`, `portal_accounts`, `portal_sessions` e `portal_jobs` não tinham RLS.

Isso não está correto no banco vivo atual.

**Todas possuem RLS habilitado.**

O problema real é:

```text
RLS habilitado
+ zero policy
+ backend usando service_role
= nenhuma proteção adicional contra erro de filtro no backend.
```

O próprio código declara que o cliente principal usa `SUPABASE_KEY` como service role:

```text
backend/app/core/database.py:27-35
```

O frontend server-side também cria cliente com `SUPABASE_SERVICE_ROLE_KEY`:

```text
lib/auth.ts:7-12
```

## 3.3 Tabelas com RLS e zero policies

Foram confirmadas, entre outras:

- `_ta1_resulta_agents_snapshot`;
- `agent_activities`;
- `agent_memories`;
- `attendance_sessions`;
- `attendance_transcripts`;
- `billing_sent_log`;
- `broker_insights`;
- `company_members`;
- `conduct_playbooks`;
- `conversation_scorecards`;
- `invites`;
- `knowledge_cards`;
- `observed_events`;
- `observed_sessions`;
- `password_reset_tokens`;
- `payment_history`;
- `plans`;
- `platform_sends`;
- `playbook_overlays`;
- `portal_accounts`;
- `portal_jobs`;
- `portal_sessions`;
- `portals`;
- `route_drift`;
- `routine_runs`;
- `routine_templates`;
- `routines`;
- `ura_maps`.

### Interpretação correta

Algumas dessas tabelas foram intencionalmente tratadas como `service-role-only`.

Isso é aceitável como decisão de produto **somente se**:

1. nenhuma rota exposta usar cliente de usuário diretamente;
2. todos os repositories aplicarem filtro tenant obrigatório;
3. o serviço validar `company_id` derivado da sessão, nunca do client;
4. houver testes reais contra dois tenants;
5. grants desnecessários forem revogados;
6. as tabelas internas forem preferencialmente movidas para schema não exposto quando apropriado.

A migration da SPEC-047 documenta explicitamente que o modelo atual confia no service role:

```text
backend/supabase/migrations/20260721_01_spec047_rls_e_company_members.sql:3-14
```

A SPEC-054 deve substituir confiança implícita por defesa em profundidade.

---

# 4. Achados P0 — segurança crítica

## P0.1 — Funções `SECURITY DEFINER` expostas a `anon`

### Estado confirmado

No schema `public` existem:

- 15 funções `SECURITY DEFINER`;
- 12 executáveis por `anon`;
- 12 executáveis por `authenticated`;
- 7 sem `search_path` fixado.

`SECURITY DEFINER` executa com os privilégios do criador da função. Em um schema exposto pelo PostgREST, isso exige grants mínimos e contrato extremamente restrito.

### Funções mais críticas

#### `get_user_for_login(p_email)`

A função:

- é `SECURITY DEFINER`;
- pode ser executada por `anon` e `authenticated`;
- recebe somente um e-mail;
- retorna JSON com informações do usuário;
- inclui o campo `password_hash`;
- inclui `company_id`, estado da conta e `webhook_url`.

O código legítimo chama essa função pelo cliente server-side com service role:

```text
lib/auth.ts:20-35
```

Portanto, **não há necessidade técnica de permitir `anon` ou `authenticated` executarem essa RPC diretamente**.

**Risco:** enumeração de contas e exposição de hashes de senha pela API pública.

**Decisão recomendada para a SPEC-054:**

- revogar EXECUTE de `PUBLIC`, `anon` e `authenticated`;
- permitir somente role interna necessária;
- mover a função para schema privado ou eliminá-la em favor de consulta server-side explícita;
- nunca retornar `password_hash` por uma RPC pública;
- fixar `search_path` mínimo.

#### `create_user_account(...)`

Existem duas overloads da função.

Ambas:

- são `SECURITY DEFINER`;
- são executáveis por `anon` e `authenticated`;
- aceitam `company_id`;
- aceitam `role`;
- aceitam `is_owner`;
- permitem papel `admin_company`.

A criação legítima ocorre no servidor com service role:

```text
lib/auth.ts:194-256
```

**Risco:** criação direta de conta vinculada a empresa/papel informado pelo chamador, contornando a regra de que empresa e papel nunca vêm do client.

**Decisão recomendada:**

- revogar execução pública das duas overloads;
- manter somente uma assinatura canônica;
- criar conta apenas por rota server-side validada;
- derivar empresa, papel, ownership e convite no servidor;
- impedir chamadas diretas via PostgREST.

#### `debit_company_balance(p_company_id, p_amount)`

A função:

- é `SECURITY DEFINER`;
- é executável por `anon` e `authenticated`;
- altera `company_credits`;
- aceita qualquer `company_id` e valor;
- não valida chamador, tenant, sinal ou limite do valor.

**Risco:** alteração indevida de saldo de qualquer empresa.

**Decisão recomendada:**

- revogar execução pública imediatamente;
- aceitar somente service role ou função interna privada;
- validar `p_amount > 0`;
- exigir idempotency key/ledger transaction;
- impedir débito direto sem registro atômico em `credit_transactions`;
- usar uma única função transacional para saldo + ledger.

#### `get_token_usage_by_company` e `get_token_usage_report`

As funções:

- são `SECURITY DEFINER`;
- são executáveis por `anon` e `authenticated`;
- agregam consumo de todas as corretoras;
- não filtram pelo tenant do chamador.

**Risco:** exposição de nomes de empresas, uso de modelos e custos agregados.

**Decisão recomendada:**

- revogar execução pública;
- manter somente Admin/service role;
- criar versão tenant-scoped separada, se necessária;
- fixar `search_path`.

### Funções trigger também expostas

Funções como:

- `block_technical_attendance_capture`;
- `enforce_technical_whatsapp_integration`;
- `isolate_technical_observed_event`;
- `isolate_technical_observed_session`;

são trigger functions e não precisam de EXECUTE público.

**Decisão recomendada:** revogar EXECUTE de `PUBLIC`, `anon` e `authenticated`, preservando o funcionamento dos triggers.

## P0.2 — View `ucp_connection_summary` com segurança de owner

### Estado confirmado

A única view pública:

```text
public.ucp_connection_summary
```

possui:

- owner `postgres`;
- nenhuma opção `security_invoker`;
- leitura de `ucp_connections` e `agents`;
- exposição de `company_id`, `agent_id`, `store_url`, versão e estado;
- privilégios concedidos a `anon` e `authenticated`.

Views criadas pelo owner privilegiado podem contornar RLS das tabelas subjacentes se não forem `security_invoker`.

**Decisão recomendada:**

- alterar para `security_invoker = true`, se realmente for consumida por usuários;
- ou revogar acesso de `anon`/`authenticated` e mantê-la interna;
- conceder apenas `SELECT`, não grants genéricos;
- adicionar filtro/contrato tenant;
- testar com dois tenants.

## P0.3 — Buckets públicos e documentos

### Estado confirmado

| Bucket | Público | Objetos atuais | Observação |
|---|---:|---:|---|
| `avatars` | sim | 0 | policies permitem operações públicas amplas |
| `chat-docs` | sim | 30 | contém documentos; aproximadamente 3,65 MB |
| `chat-media` | sim | 26 | imagens do chat; aproximadamente 3,69 MB |
| `voice-messages` | sim | 0 | upload e leitura públicos |
| `portal-evidence` | não | 5 | configuração privada correta |

### Policies preocupantes

Foram encontradas policies que permitem, para role `public`:

- upload em `voice-messages`;
- leitura em `voice-messages`;
- upload em `chat-media`;
- leitura em `chat-media`;
- delete/update/upload de `avatars`.

Além disso, `chat-docs` está marcado como bucket público.

### Risco

- documento de corretora acessível por URL pública;
- upload anônimo usado para abuso de armazenamento;
- substituição ou exclusão de avatar por qualquer cliente;
- vazamento de anexos e mídia;
- ausência de path tenant-scoped obrigatório;
- custo e risco de conteúdo malicioso.

### Decisão recomendada

- tornar `chat-docs`, `chat-media` e `voice-messages` privados;
- manter `avatars` público somente para leitura, com escrita autenticada e path por owner;
- usar signed URLs de curta duração;
- exigir paths no formato `company_id/user_id/...`;
- policies separadas para upload/read/delete;
- validar MIME pelo conteúdo, não somente extensão/header;
- limite de tamanho e quota por tenant;
- varredura/sanitização antes de uso por LLM;
- backfill de paths existentes antes de fechar acesso;
- verificar todas as referências atuais para não quebrar UI.

`portal-evidence` deve ser preservado como bucket privado.

---

# 5. Achados P1 — deriva de schema e migrations

## 5.1 Histórico de migrations incompleto

### Estado confirmado

O Supabase registra somente **21 migrations**, iniciadas em 08/07/2026 e terminando em 23/07/2026.

Porém, o repositório possui migrations estruturais anteriores, por exemplo:

- `20260703_03_spec018_capability_seeds.sql`;
- `20260705_01_f2_routines.sql`;
- `20260706_03_spec020_portal.sql`.

Essas estruturas existem no banco, mas suas migrations não aparecem no histórico oficial de `supabase_migrations.schema_migrations`.

Há também DDLs importantes fora da pasta oficial de migrations, como a fundação de `auxiliary_templates` em documentos de design.

### Consequência

Um ambiente novo criado somente a partir das migrations oficialmente rastreadas não reproduzirá o banco atual.

Um executor que tentar “aplicar tudo que existe no repositório” sobre produção também pode:

- repetir DDL;
- alterar defaults;
- recriar functions;
- sobrescrever policies;
- divergir do schema vivo;
- perder ajustes manuais;
- quebrar dados existentes.

### Decisão recomendada

A SPEC-054 deve estabelecer um **baseline canônico de produção**, sem reaplicar cegamente o passado.

Fluxo recomendado:

```text
inventário vivo
→ snapshot de DDL sem dados
→ classificação: canônico / legado / órfão / manual
→ migration baseline declarativa
→ migrations incrementais posteriores
→ teste em branch de banco
→ produção somente após diff vazio esperado
```

## 5.2 `schema_completo.sql` não deve ser aplicado como migration comum

Arquivos monolíticos históricos podem ser úteis para investigação, mas não devem ser executados sobre produção como fonte cega de verdade.

A autoridade deve ser:

1. banco vivo inventariado;
2. SPEC-054;
3. baseline versionado;
4. migrations incrementais futuras.

## 5.3 Snapshot de maio é histórico

O snapshot de 28/05/2026 pertence majoritariamente à arquitetura anterior.

Ele deve ser movido/rotulado como:

```text
historical_resultvision_schema_reference
```

Não deve ser confundido com snapshot atual do Smith.

---

# 6. Achados P1 — integridade relacional

## 6.1 `company_id` sem foreign key

Foram encontradas 14 tabelas reais com `company_id` e sem FK para `public.companies(id)`:

- `_ta1_resulta_agents_snapshot`;
- `agent_activities`;
- `attendance_sessions`;
- `attendance_transcripts`;
- `billing_sent_log`;
- `broker_insights`;
- `conversation_scorecards`;
- `observed_events`;
- `observed_sessions`;
- `platform_sends`;
- `portal_accounts`;
- `portal_jobs`;
- `portal_sessions`;
- `routines`.

A view `ucp_connection_summary` também contém `company_id`, mas não é tabela.

### Integridade atual

Foram executadas verificações read-only e **nenhum registro órfão foi encontrado** nas tabelas operacionais auditadas.

Também não foram encontrados:

- rotina ligada a Agent de outra corretora;
- portal job ligado a conta de outra corretora;
- auxiliary run ligado a tenant auxiliary de outra corretora.

Isso é uma boa notícia: as FKs podem ser adicionadas progressivamente sem necessidade aparente de limpeza massiva.

### Estratégia recomendada

Para tabelas grandes ou sensíveis:

```sql
ADD CONSTRAINT ... FOREIGN KEY ... NOT VALID;
VALIDATE CONSTRAINT ...;
```

A migration deve definir conscientemente:

- `ON DELETE CASCADE`;
- `ON DELETE RESTRICT`;
- `ON DELETE SET NULL`;
- retenção legal/auditável.

Não usar o mesmo comportamento para todas as tabelas.

## 6.2 `routines`

A migration original cria:

- `company_id` sem FK;
- `created_by` sem FK;
- `agent_id` sem FK.

Evidência:

```text
backend/supabase/migrations/20260705_01_f2_routines.sql:11-27
```

Decisão recomendada:

- FK de `company_id` para `companies`;
- FK opcional de `agent_id` para `agents`;
- validação de que o Agent pertence à mesma company;
- `created_by` alinhado ao sistema de identidade canônico;
- não acoplar a migração ao futuro Work Run ainda.

## 6.3 `routine_runs`

Hoje possui apenas FK para `routine_id`.

Não possui:

- `company_id` materializado;
- `idempotency_key`;
- lease;
- worker identity;
- retry policy estruturada;
- cancelamento;
- checkpoint;
- relacionamento com approval/artifact.

Esses itens serão evoluídos na SPEC-055. A SPEC-054 deve apenas garantir integridade e preparar a migração, sem criar um segundo executor.

## 6.4 Portais

`portal_accounts`, `portal_sessions` e `portal_jobs` não têm FK de company.

`portal_jobs.account_id` possui FK para `portal_accounts`, mas o banco não impede que a conta pertença a outra company.

O código atual aplica filtros e não foi encontrado cruzamento de dados no banco.

Decisão recomendada:

- adicionar FKs de company;
- criar constraint/trigger ou chave composta para garantir `job.company_id = account.company_id`;
- preservar criptografia existente;
- preservar `portal-evidence` privado.

## 6.5 `agent_memories`

A tabela atual não possui:

- `company_id`;
- `agent_id`;
- `user_id`;
- FK;
- policy.

Sua unicidade é apenas:

```text
(agent_task, block_key)
```

Isso pode ser intencional para memória técnica global de um agente de sistema, mas não é suficiente para a Memory Fabric multi-tenant da SPEC-052.

Decisão recomendada:

- inventariar os sete registros atuais;
- classificar cada um como `platform`, `tenant`, `agent` ou `user`;
- manter os globais em escopo explícito;
- migrar memória de tenant/agent para chave composta com escopo;
- nunca inferir que toda memória atual é global.

## 6.6 `broker_insights`

`user_id` é `text`, não FK.

Decisão recomendada:

- preservar compatibilidade de fontes externas;
- adicionar `actor_user_id uuid` quando a origem for usuário interno;
- manter identificador textual externo separado;
- company FK obrigatória.

---

# 7. Achados P1 — Capability Registry e autoridade

## 7.1 Estado real

- capabilities: 24;
- bindings: 46;
- entitlements por tenant: 0;
- HTTP tools cadastradas: 0;
- MCP servers cadastrados: 0;
- MCP connections cadastradas: 0;
- MCP tools cadastradas: 0.

## 7.2 Todos os scopes estão vazios

Distribuição:

| Papel | Bindings | `scope = {}` |
|---|---:|---:|
| `attendance` | 16 | 16 |
| `auxiliary` | 10 | 10 |
| `core` | 17 | 17 |
| `subagent` | 3 | 3 |

O resolver atual consulta apenas:

- binding ligado;
- capability ativa;
- entitlement explicitamente desligado;
- conexão saudável;
- provider disponível.

Ele **não lê nem aplica o campo `scope`**.

Evidência:

```text
backend/app/agents/capability_resolver.py:50-92
```

Como não há entitlements, a ausência de registro significa que o binding global prevalece.

## 7.3 `AUTHORITY_STRICT_MODE` desligado por padrão

O código confirma:

```text
backend/app/services/tool_authority.py:3-10
backend/app/agents/graph.py:33-38
```

Com a flag desligada:

- tools legadas seguem `tools_config`;
- MCPs seguem o cadastro do agente;
- HTTP router entra mesmo sem capability funcional, desde que exista Agent.

O modo estrito existe, mas ainda não é autoridade padrão.

## 7.4 Capability de portal inconsistente

A capability `tenant.portal.execute` está marcada como:

- risco alto;
- sem conexão obrigatória;
- sem approval obrigatório.

Isso conflita com a arquitetura de HITL e com a realidade dos portais.

Decisão recomendada:

- dividir leitura, preparação e execução;
- leitura pode ter política própria;
- side effect deve exigir approval conforme risco;
- conexão/Vault deve ser obrigatória;
- `scope` deve declarar portal, journey, empresa, volume e dados permitidos.

## 7.5 Estratégia para ligar Authority Strict

Não ligar globalmente de uma vez.

Fluxo:

```text
preencher scopes
→ criar entitlements explícitos
→ materializar capabilities MCP por servidor
→ shadow evaluation
→ comparar ferramentas carregadas antes/depois
→ canary Amandus
→ Resulta
→ Autofleet
→ default ON
→ remover caminho permissivo
```

---

# 8. Achados P1 — HTTP Tool e SSRF

## 8.1 Estado atual

Não existe nenhuma linha em `agent_http_tools`.

Portanto, o risco está **dormente**, não explorado pelo catálogo atual.

## 8.2 Código atual

A ferramenta aceita URL configurada no banco e executa `httpx` diretamente:

```text
backend/app/agents/tools/http_request.py:98-138
```

Não foram encontrados no executor:

- allowlist de host;
- bloqueio de loopback;
- bloqueio de RFC1918;
- bloqueio de metadata cloud;
- resolução DNS validada;
- proteção contra DNS rebinding;
- política de porta;
- política de esquema;
- limite de tamanho real antes do download;
- validação de content-type;
- classificação de response;
- sanitização de conteúdo retornado à LLM.

O código também registra parâmetros e body processado nos logs:

```text
backend/app/agents/tools/http_request.py:36-40
backend/app/agents/tools/http_request.py:80-90
```

Isso pode registrar PII ou dados de operação.

## 8.3 Autorização por tool

`allowed_tools` é opcional e não faz parte do schema que a LLM envia.

Na prática, o principal gate é:

- Agent possui uma linha ativa em `agent_http_tools`;
- broad capability `tenant.http_tools.execute`, somente quando strict está ligado.

Isso não equivale a uma policy por host, método, risco e operação.

## 8.4 Decisão recomendada

A SPEC-054 deve criar o **HTTP Egress Guard** compartilhado, sem criar ferramenta paralela.

Requisitos mínimos:

- `https` por padrão;
- host allowlist por connector/tool;
- resolução DNS antes da chamada;
- bloquear IP privado, loopback, link-local e metadata;
- revalidar cada redirect ou desabilitar redirect;
- bloquear portas não autorizadas;
- timeout por conexão/leitura/total;
- limite de response bytes durante streaming;
- content-type allowlist;
- headers secretos vindos do Vault;
- logs redigidos;
- no raw body em log;
- idempotency key para escrita;
- approval para métodos/ações sensíveis;
- tool call ligada a capability e tenant;
- teste SSRF automatizado.

---

# 9. Achados P1 — MCP Gateway

## 9.1 Pontos positivos

O gateway atual:

- só reconhece servidores internos mapeados;
- não executa pacote arbitrário informado pela LLM;
- verifica que o Agent pertence à company ao habilitar um servidor;
- busca tokens por Agent;
- redige alguns padrões sensíveis dos logs;
- usa timeout de subprocesso.

Evidência:

```text
backend/app/services/mcp_gateway_service.py:38-71
backend/app/services/mcp_gateway_service.py:128-162
```

## 9.2 Environment excessivo

O subprocesso recebe:

```python
env = dict(os.environ)
```

Evidência:

```text
backend/app/services/mcp_gateway_service.py:73-90
```

Isso significa que um MCP interno comprometido ou com bug pode receber:

- chaves de LLM;
- credenciais Supabase;
- segredos do portal worker;
- tokens de providers;
- outras variáveis não relacionadas à sua função.

## 9.3 Ausência de sandbox

O processo é iniciado sem:

- usuário isolado;
- filesystem restrito;
- cwd temporário;
- limite de CPU/memória;
- seccomp/AppArmor;
- egress específico;
- allowlist de arquivos;
- kill de process group;
- contrato explícito de variáveis.

Evidência:

```text
backend/app/services/mcp_gateway_service.py:302-327
```

## 9.4 Revalidação em tempo de execução

`call_mcp_tool` não revalida, no ponto final da execução:

- se a tool ainda está habilitada para o Agent;
- se o Agent ainda pertence à company ativa;
- se a capability continua ativa;
- se o approval continua válido.

O objeto DynamicMCPTool carrega somente `agent_id`, servidor e nome da tool:

```text
backend/app/agents/tools/mcp_factory.py:21-90
```

A filtragem ocorre antes, ao montar o grafo. Defesa em profundidade exige rechecagem antes do side effect.

## 9.5 Decisão recomendada

- construir env por allowlist explícita;
- nunca herdar `os.environ` completo;
- token de uma conexão por execução;
- capability e tenant revalidados na chamada;
- approval token associado ao run/step;
- subprocess sandbox;
- egress por servidor;
- logs estruturados sem stdout bruto sensível;
- schema de output e tamanho máximo;
- cancelamento do process group;
- catálogo homologado e versionado;
- manter os servidores atuais internos como fundação, não criar gateway paralelo.

---

# 10. Achados P1 — Rotinas, jobs e idempotência

## 10.1 Rotinas

O motor atual possui qualidades importantes:

- filtra integração por `company_id`;
- executa pelo mesmo cérebro Smith;
- usa timeout;
- registra `routine_runs`;
- faz claim comparando `next_run_at`;
- desativa após falhas consecutivas;
- não há run preso no momento da auditoria.

Evidência:

```text
backend/app/services/routine_engine.py:31-104
backend/app/services/routine_engine.py:122-160
```

Estado atual dos 39 runs:

- 36 `ok`;
- 3 `error`;
- 0 `running`;
- 0 stale.

### Lacunas

- sem idempotency key por ocorrência agendada;
- claim avança `next_run_at` antes da conclusão;
- se a entrega externa ocorrer e o registro final falhar, não existe garantia universal contra reenvio;
- `routine_runs` não possui `company_id`;
- retenção apaga runs >90 dias sem política central de auditoria;
- execução ocorre no processo da API.

A SPEC-054 deve preservar o motor e preparar a fundação. A execução durável será detalhada na SPEC-055.

## 10.2 Portal worker

Pontos positivos:

- claim atômico `queued → running`;
- timeout;
- recuperação de jobs órfãos;
- credenciais e sessões cifradas;
- bucket privado para evidência;
- estado atual sem job queued/running/stale.

Evidência:

```text
backend/portal_worker/worker.py:44-83
backend/portal_worker/worker.py:129-142
```

Estado atual dos 91 jobs:

- 19 `done`;
- 67 `needs_human`;
- 5 `failed`;
- 0 `queued`;
- 0 `running`.

### Lacunas

- nenhum `idempotency_key` universal;
- nenhum lease owner/token;
- nenhuma garantia transacional entre ação no portal e status do job;
- `account_id` não impõe company composta;
- recuperação por idade pode repetir ação se o portal concluiu e o worker morreu antes de gravar;
- HITL é representado no evidence/status, não no modelo executável da futura SPEC-055.

A SPEC-054 deve adicionar integridade e contratos de idempotência preparatórios, sem reescrever o worker.

## 10.3 Auxiliares

`tenant_auxiliaries` possui boa unicidade por `(company_id, slug)`.

`auxiliary_runs` não possui idempotency key.

A SPEC-054 deve:

- normalizar schema e FKs;
- não migrar ainda todo histórico para Work Runs;
- deixar o backfill universal para a SPEC-055/058.

---

# 11. Achados P2 — performance e higiene

## 11.1 Índices duplicados confirmados

| Tabela | Índices equivalentes |
|---|---|
| `company_credits` | `idx_company_credits_company`, `idx_tenant_credits_tenant` |
| `credit_transactions` | `idx_credit_transactions_company`, `idx_credit_transactions_tenant` |
| `documents` | `idx_documents_ingestion_strategy`, `idx_documents_strategy` |
| `memory_processing_locks` | `idx_memory_locks_unique`, índice da constraint unique |
| `subscriptions` | `idx_subscriptions_company`, `idx_subscriptions_company_id`, `idx_subscriptions_tenant` |

Não remover automaticamente.

A SPEC-054 deve verificar:

- dependências;
- uso real;
- constraint backing index;
- planos de consulta;
- rollback.

## 11.2 Foreign keys sem índice dedicado

Os advisors apontaram FKs sem índice em tabelas como:

- `agent_blueprint_releases`;
- `agent_delegations`;
- `agent_mcp_connections`;
- `agent_mcp_tools`;
- `agent_release_rollouts`;
- `approval_requests`;
- `auxiliary_runs`;
- `auxiliary_templates`;
- `company_members`;
- `portal_jobs`;
- `tenant_capability_entitlements`;
- `tenant_corridors`.

Cada uma deve ser avaliada por cardinalidade e padrão de delete/join.

## 11.3 Policies com initplan ineficiente

Há policies que chamam `auth.uid()` ou `current_setting()` por linha.

A recomendação do Supabase é usar, quando semanticamente válido:

```sql
(select auth.uid())
```

para permitir initPlan estável por statement.

Essa otimização deve ser feita somente após testes de isolamento.

## 11.4 Índices “não usados”

O advisor aponta muitos índices não usados.

O banco é recente e tem pouco volume. “Não usado” nesse período não é autorização para remover.

A SPEC-054 deve congelar a regra:

```text
índice não usado + banco jovem ≠ índice inútil
```

Remoção somente com:

- janela de observação;
- query inventory;
- plano de rollback;
- comparação de latência.

---

# 12. Testes e observabilidade

## 12.1 Testes atuais

Existem testes úteis de source inspection, por exemplo:

```text
backend/tests/test_spec048_isolamento_corretoras.py
```

Esse teste confirma a presença de guards no código, mas não executa o banco com papéis reais.

Evidência:

```text
backend/tests/test_spec048_isolamento_corretoras.py:3-11
backend/tests/test_spec048_isolamento_corretoras.py:39-80
```

## 12.2 Lacuna

Faltam testes de integração que executem de fato:

- `anon`;
- `authenticated` tenant A;
- `authenticated` tenant B;
- `service_role`;
- Admin global;
- usuário sem vínculo;
- usuário multiempresa;
- função RPC;
- bucket privado;
- signed URL;
- view security invoker;
- tool SSRF;
- MCP env allowlist.

## 12.3 Suite obrigatória da SPEC-054

### Database security tests

- anon não lê dados privados;
- anon não executa RPC interna;
- tenant A não lê tenant B;
- tenant A não grava tenant B;
- member não executa ação de owner;
- service route sem `.eq(company_id)` é detectada em teste/repository lint;
- view respeita tenant;
- função financeira não é pública;
- password hash nunca sai por API pública.

### Storage tests

- bucket privado recusa URL pública;
- signed URL expira;
- upload exige tenant/path correto;
- delete exige owner/role;
- MIME inválido é rejeitado;
- arquivo de tenant A não é lido pelo tenant B.

### Tool security tests

- loopback bloqueado;
- rede privada bloqueada;
- metadata cloud bloqueada;
- redirect para IP privado bloqueado;
- DNS rebinding simulado bloqueado;
- response acima do limite interrompida;
- segredo não aparece em log;
- MCP recebe somente env allowlisted.

### Migration tests

- ambiente vazio sobe do baseline;
- ambiente atual recebe migrations incrementais sem drift;
- rollback documentado;
- constraints validam;
- nenhuma contagem de negócio muda inesperadamente.

---

# 13. Pontos fortes que devem ser preservados

1. Smith permanece runtime único.
2. Todas as tabelas públicas já têm RLS habilitado.
3. Não foram encontrados órfãos nas tabelas company-scoped auditadas.
4. Não foram encontrados vínculos cross-tenant nos testes de integridade executados.
5. `requireCompanyMember` foi corrigido para validar empresa ativa por request.
6. `company_members` já modela usuário multiempresa.
7. Capability Resolver falha fechado em erro de banco e papel inválido.
8. Portal worker possui claim atômico, timeout e recuperação de stale jobs.
9. Routine engine possui claim atômico e fail-safe de falhas.
10. Credenciais/sessões de portal estão cifradas.
11. `portal-evidence` está privado.
12. Technical WhatsApp sandbox possui triggers que bloqueiam aprendizado global.
13. Não existem HTTP tools ou MCPs ativos neste momento, permitindo endurecer antes do rollout.
14. O banco não apresenta corrupção relacional evidente nas verificações executadas.
15. A arquitetura das SPECs 052 e 053 já define corretamente a direção.

---

# 14. Arquitetura recomendada para a SPEC-054

A SPEC-054 não deve tentar criar o Work OS inteiro.

Ela deve entregar uma fundação confiável para as SPECs 055–062.

## Trilha A — Emergency Security Closure

- revogar RPCs públicas críticas;
- corrigir `search_path`;
- fechar view security definer;
- tornar buckets privados;
- preservar fluxos server-side;
- testes de não regressão de login/signup/uploads.

## Trilha B — Schema Baseline & Migration Governance

- snapshot DDL real;
- inventário de objetos;
- baseline canônico;
- classificar migrations antigas;
- remover DDL solto do caminho operacional;
- política de naming/versionamento;
- schema diff automatizado;
- branch de banco para teste.

## Trilha C — Tenant Isolation & Integrity

- FKs ausentes;
- checks cross-company;
- RLS/policies por categoria;
- repositories com filtros obrigatórios;
- separar clientes DB por finalidade;
- testes tenant A × tenant B;
- preservar service role somente onde necessário.

## Trilha D — Runtime & Tool Hardening

- HTTP Egress Guard;
- MCP env allowlist;
- sandbox;
- revalidação em tempo de execução;
- scopes reais;
- Authority Strict em shadow mode;
- idempotency contract.

## Trilha E — Performance, Observability & Rollout

- índices duplicados;
- índices de FK;
- policies otimizadas;
- advisors como gate;
- métricas;
- canary Amandus → Resulta → Autofleet;
- rollback.

---

# 15. Sequência recomendada de implementação da SPEC-054

## Bloco 0 — Preflight e congelamento

- registrar commit inicial;
- exportar DDL metadata-only atual;
- registrar migrations atuais;
- registrar advisors atuais;
- backup lógico/point-in-time confirmado;
- abrir branch de código;
- preferencialmente criar branch Supabase de desenvolvimento;
- proibir deploy automático durante migrations críticas.

## Bloco 1 — P0 RPC/View/Storage

- grants de functions;
- private schema;
- `search_path`;
- view `security_invoker` ou service-only;
- buckets privados;
- signed URLs;
- backfill de paths;
- testes de login, signup, documentos, mídia e voz.

## Bloco 2 — Baseline reproduzível

- gerar baseline sem dados;
- mapear cada objeto ao owner documental;
- marcar legado;
- criar migrations faltantes sem reexecutar DDL perigoso;
- validar ambiente limpo;
- validar produção sem diff destrutivo.

## Bloco 3 — Integridade e isolamento

- company FKs `NOT VALID`;
- validação;
- constraints cross-company;
- policies por grupo;
- clients e repositories;
- testes reais multi-tenant.

## Bloco 4 — Authority e egress

- preencher scopes;
- entitlement policy;
- HTTP guard;
- MCP env/sandbox;
- strict shadow mode;
- canary.

## Bloco 5 — Performance e limpeza segura

- índices duplicados;
- FK indexes;
- RLS initplans;
- functions/search paths restantes;
- advisors sem erros críticos.

## Bloco 6 — Production readiness

- Resulta e Autofleet em canary;
- métricas;
- logs;
- rollback ensaiado;
- relatório final;
- atualização da documentação canônica.

---

# 16. Decisões que a SPEC-054 deve congelar

1. `service_role` não será cliente padrão de toda rota tenant-facing.
2. Função interna não ficará executável por `PUBLIC` por conveniência.
3. Password hash nunca será retornado por RPC exposta.
4. Buckets de documentos, mídia e voz serão privados por padrão.
5. Views tenant-facing usarão `security_invoker` ou contrato privado.
6. Todo objeto company-scoped terá FK ou justificativa formal.
7. Toda ação externa terá idempotency contract.
8. `scope = {}` não será aceito para capability sensível em produção.
9. `AUTHORITY_STRICT_MODE` será ativado por rollout, não por big bang.
10. HTTP genérico não executará sem egress guard.
11. MCP não herdará ambiente completo.
12. Nenhuma migration histórica será reaplicada cegamente.
13. O banco vivo atual será transformado em baseline reproduzível.
14. Nenhuma tabela será apagada na SPEC-054.
15. Nenhum motor paralelo será criado.
16. A SPEC-055 continuará responsável por Work Runs/HITL duráveis.
17. A SPEC-056 continuará responsável pelo Skill Registry/Tool Gateway completo.
18. A SPEC-057 continuará responsável por Artifact Hub/Report Studio.

---

# 17. Riscos de execução e mitigação

| Risco | Severidade | Mitigação |
|---|---|---|
| Revogar RPC quebra login/signup | Alta | confirmar chamadas server-side; testes antes/depois; grant service role explícito |
| Fechar bucket quebra links existentes | Alta | inventário de URLs, backfill, compatibilidade temporária, signed URL |
| FK falha por dado órfão futuro | Média | NOT VALID, relatório, limpeza e VALIDATE |
| RLS bloqueia rota legítima | Alta | route inventory, branch, testes por papel, rollout canário |
| Authority Strict remove tool necessária | Alta | shadow mode, diff de tools, canary |
| Baseline recria objeto diferente | Alta | diff DDL, ambiente limpo, não aplicar baseline sobre produção |
| Índice removido degrada consulta | Média | observação, EXPLAIN, rollback |
| MCP perde variável necessária | Média | manifest de env por servidor e healthcheck |
| SSRF guard bloqueia API legítima | Média | allowlist versionada e teste por connector |
| Idempotência muda comportamento | Alta | chave compatível, dry-run, métricas e replay tests |

---

# 18. Critérios de aceite da futura SPEC-054

A implementação da SPEC-054 somente estará concluída quando:

- nenhuma RPC interna crítica for executável por `anon`;
- `get_user_for_login` não expuser hash via API pública;
- signup não aceitar papel/owner/empresa arbitrários do client;
- saldo não puder ser alterado por RPC pública;
- relatórios globais de custo forem Admin-only;
- a view UCP não contornar RLS;
- documentos/mídias/voz privados usarem signed URLs;
- o schema atual puder ser reproduzido em ambiente novo;
- todas as migrations futuras estiverem rastreadas;
- company FKs críticas existirem e estiverem validadas;
- zero órfãos forem mantidos;
- filtros tenant e policies tiverem testes reais;
- nenhum dado de tenant A puder ser acessado por tenant B;
- HTTP SSRF tests estiverem verdes;
- MCP receber somente env permitido;
- scopes sensíveis estiverem preenchidos;
- Authority Strict estiver validado em canary;
- idempotency contracts estiverem documentados;
- advisors não apresentarem erro crítico não aceito formalmente;
- APPLY/VERIFY/ROLLBACK existirem por migration;
- nenhum motor paralelo tiver sido criado;
- Resulta e Autofleet continuarem operacionais.

---

# 19. Arquivos e áreas que a SPEC-054 deverá considerar

## Banco/migrations

- `backend/supabase/migrations/`;
- baseline atual a ser criado;
- functions/grants;
- storage buckets/policies;
- RLS/policies;
- constraints e índices;
- schema privado para funções internas.

## Backend Smith

- `backend/app/core/database.py`;
- `backend/app/agents/graph.py`;
- `backend/app/agents/capability_resolver.py`;
- `backend/app/services/tool_authority.py`;
- `backend/app/agents/tools/http_request.py`;
- `backend/app/services/mcp_gateway_service.py`;
- `backend/app/agents/tools/mcp_factory.py`;
- repositories/services company-scoped;
- `backend/app/services/routine_engine.py`;
- `backend/portal_worker/worker.py`.

## Web/server

- `lib/auth.ts`;
- `lib/iron-session.ts`;
- `lib/admin/admin-auth.ts`;
- factories de Supabase clients;
- upload/download de documentos, mídia e voz;
- rotas tenant-facing;
- rotas Admin.

## Testes

- testes source atuais;
- nova suite DB multi-role;
- nova suite Storage;
- nova suite SSRF/MCP;
- migration smoke tests;
- canary tests Resulta/Autofleet.

---

# 20. Conclusão final

```text
A auditoria não encontrou um sistema destruído ou uma arquitetura inviável.

Encontrou uma fundação funcional que cresceu mais rápido
que sua governança de schema e segurança.

Os dados atuais estão coerentes nas verificações executadas.
Os claims de Rotinas e Portais funcionam.
O Smith deve ser preservado.

Mas existem exposições P0 reais em RPCs e Storage,
e a deriva de migrations impede reprodução confiável.

A SPEC-054 deve primeiro fechar as portas críticas,
depois transformar o banco vivo em baseline canônico,
reforçar isolamento e integridade,
e somente então ativar Authority Strict e novas ferramentas.

Sem big bang.
Sem apagar tabelas.
Sem segundo runtime.
Sem remendos paralelos.
```
