# SPEC-054 — Foundation Hardening & Schema Governance

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANÔNICA E AUTORIZADA PARA EXECUÇÃO — aprovada pelo Founder em 24/07/2026  
**Autoridade superior:** `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md` e `SPEC-053-autobrokers-work-os-core-harness.md`  
**Auditoria obrigatória:** `../audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md`  
**Runtime preservado:** Smith + LangGraph/LangChain + FastAPI + Supabase + Redis + Qdrant + MinIO  
**Projeto Supabase de produção:** `AutoBrokers Intelligence OS` — ref `dcajcvlzcjbmyapmklil`  
**Escopo:** fechar exposições críticas, tornar o schema reproduzível, reforçar isolamento multi-tenant, endurecer Storage, HTTP, MCP e autoridade de tools, preparar idempotência e estabelecer governança de migrations sem reescrever o produto.  
**Natureza desta SPEC:** esta SPEC autoriza implementação, migrations, testes, rollout canário e atualização documental, desde que todos os gates, backups, VERIFY e ROLLBACK definidos abaixo sejam respeitados.

---

# 0. Comando direto ao executor — Fable, Opus, Codex ou equivalente

Você está autorizado a **implementar integralmente esta SPEC**.

Não transforme esta tarefa em outra rodada longa de planejamento. A auditoria preparatória já foi concluída. Leia as fontes obrigatórias, confirme que a `main` está atual e execute.

## 0.1 Modo de execução obrigatório

A execução deve ocorrer em **três blocos**, sequenciais, dentro de uma única iniciativa de implementação:

1. **Bloco A — Fechamento P0: RPCs, view e Storage**;
2. **Bloco B — Baseline, migrations, integridade e isolamento**;
3. **Bloco C — Egress, MCP, Authority, idempotência, performance e rollout**.

Esse é o menor número seguro de blocos. Não fragmentar em dezenas de micro-SPECs. Subtarefas internas são permitidas, mas não devem virar novos projetos, novos runtimes ou novas aprovações burocráticas.

## 0.2 Regra de autonomia

Se os testes e gates estiverem verdes, avance automaticamente para o próximo bloco.

Pare e solicite decisão do CEO/Founder somente se ocorrer uma das condições de parada definidas na seção 18:

- risco real de perda de dados;
- backup/PITR indisponível;
- diff destrutivo não previsto;
- contradição entre SPEC-052, SPEC-053 e esta SPEC;
- necessidade de remover tabela ou dado de negócio;
- quebra não resolvida do piloto Resulta ou AutoFleet;
- decisão comercial que não possa ser inferida tecnicamente.

## 0.3 Saída esperada

O executor deve entregar:

- código implementado;
- migrations versionadas;
- testes automatizados;
- APPLY/VERIFY/ROLLBACK por migration;
- relatório final de execução;
- evidências dos testes do piloto;
- atualização do índice canônico;
- zero motor paralelo;
- zero perda de dados;
- zero exposição crítica conhecida aceita silenciosamente.

---

# 1. Leitura obrigatória e ordem de autoridade

Antes de alterar qualquer arquivo ou banco:

1. atualizar a `main`;
2. registrar o commit inicial;
3. ler a SPEC-052;
4. ler a SPEC-053;
5. ler a auditoria preparatória desta SPEC;
6. ler `docs/canon/ADR-001-runtime.md`;
7. ler as migrations e o código real atingido;
8. consultar o banco vivo em modo read-only para confirmar assinaturas e contagens.

Comandos mínimos:

```bash
git fetch origin
git checkout main
git pull origin main
git rev-parse HEAD
git status --short
```

Ordem de autoridade:

```text
SPEC-052
→ SPEC-053
→ SPEC-054
→ SPECs posteriores subordinadas
→ ADRs e documentos históricos quando não conflitarem
→ código atual apenas como estado de implementação, não como autoridade de produto
```

Em conflito, não inventar uma terceira arquitetura.

---

# 2. Resultado de negócio que esta SPEC deve produzir

Esta SPEC é fundacional, mas não pode ser tratada como “infraestrutura sem valor”. Seu objetivo é permitir que o AutoBrokers execute trabalho real para corretoras com segurança e previsibilidade.

Ao final, o sistema deve estar mais preparado para:

- atender clientes sem misturar dados entre corretoras;
- consultar documentos e apólices privadas sem expor URLs públicas;
- executar Rotinas e Auxiliares sem duplicar side effects;
- usar portais autenticados sem cruzar contas de empresas;
- conectar tools, APIs e MCPs sem abrir SSRF ou vazar segredos;
- medir consumo sem expor dados de outras corretoras;
- evoluir para Work Runs duráveis na SPEC-055;
- sustentar Resulta e AutoFleet como pilotos reais;
- escalar para novas corretoras sem depender de filtros manuais frágeis.

Princípio de produto:

```text
Segurança e governança só são consideradas concluídas
quando preservam ou aumentam a capacidade de entregar resultado ao corretor.
```

---

# 3. Estado inicial confirmado pela auditoria

A implementação deve partir dos fatos abaixo, sem repetir uma auditoria completa:

- 78 tabelas no schema `public`;
- uma view pública;
- três tabelas no schema `graveyard`;
- RLS habilitado nas 78 tabelas públicas;
- 28 tabelas com RLS e zero policies;
- uso amplo de `service_role` no backend e server-side Web;
- 15 funções `SECURITY DEFINER`;
- 12 executáveis por `anon` e `authenticated`;
- sete funções `SECURITY DEFINER` sem `search_path` fixado;
- `get_user_for_login` retorna `password_hash`;
- overloads de `create_user_account` recebem empresa, papel e ownership;
- `debit_company_balance` aceita empresa e valor sem contrato suficiente;
- relatórios globais de tokens estão acessíveis por grants excessivos;
- `ucp_connection_summary` não usa `security_invoker` e possui grants públicos excessivos;
- `chat-docs`, `chat-media`, `voice-messages` e `avatars` estão públicos;
- `portal-evidence` está privado e deve continuar privado;
- histórico oficial de migrations incompleto em relação ao banco vivo;
- 14 tabelas operacionais com `company_id` sem FK;
- nenhum órfão ou cruzamento de tenant encontrado nas verificações executadas;
- 24 capabilities, 46 bindings e todos os scopes vazios;
- zero entitlements por tenant;
- `AUTHORITY_STRICT_MODE` desligado por padrão;
- zero HTTP tools e zero MCPs cadastrados atualmente;
- Routine Engine e Portal Worker possuem claims úteis, mas não idempotência universal.

Se alguma dessas métricas tiver mudado, registrar o delta no relatório inicial. Não alterar o plano sem causa técnica concreta.

---

# 4. Princípios invioláveis

1. Smith permanece o runtime único.
2. Supabase permanece a fonte durável de verdade operacional.
3. Não criar outro scheduler, fila, executor, Vault, RAG ou registry.
4. Não apagar tabelas nesta SPEC.
5. Não reaplicar migrations históricas cegamente.
6. Não usar `schema_completo.sql` como migration de produção.
7. Não quebrar Resulta ou AutoFleet para “limpar arquitetura”.
8. Não expor hash, token, senha, cookie, storage state ou segredo em API, log ou relatório.
9. Empresa, papel, ownership e permissionamento nunca vêm livremente do client.
10. Toda operação company-scoped deve derivar `company_id` da sessão, vínculo ou execução governada.
11. Toda ação externa sensível deve possuir autoridade, approval quando aplicável e idempotency contract.
12. RLS não substitui validação de aplicação; validação de aplicação não substitui defesa no banco.
13. `service_role` é ferramenta privilegiada, não cliente padrão universal.
14. Bucket privado é o padrão para documentos, mídias, áudios e evidências.
15. HTTP genérico não executa sem egress guard.
16. MCP não herda todo o ambiente do processo pai.
17. Authority Strict entra por shadow mode e canário, nunca por big bang.
18. Cada migration deve ser pequena o suficiente para rollback, mesmo dentro dos três blocos macro.
19. Nenhuma otimização de índice pode reduzir segurança ou confiabilidade.
20. Critério final é resultado operacional preservado para os corretores.

---

# 5. Estratégia de branch, commits e rollout

## 5.1 Branch

Criar uma única branch:

```text
spec-054-foundation-hardening
```

## 5.2 Organização recomendada de commits

Usar no máximo cinco commits lógicos, preferencialmente três:

1. `spec054(a): close critical rpc view and storage exposure`;
2. `spec054(b): establish schema baseline tenant integrity and db governance`;
3. `spec054(c): harden egress mcp authority idempotency and rollout`;
4. opcional: testes/ajustes de integração;
5. opcional: relatório final e documentação.

Não misturar formatação ampla, renomeações cosméticas ou refactors não relacionados.

## 5.3 Produção

A ordem obrigatória é:

```text
branch local
→ testes unitários
→ banco efêmero ou Supabase Branch
→ testes de integração
→ deploy de código compatível
→ migration expand-only
→ VERIFY
→ canário Amandus
→ Resulta
→ AutoFleet
→ relatório final
```

Quando uma mudança exigir código antes do banco ou banco antes do código, usar padrão expand/contract compatível.

---

# 6. Preflight universal

Executar uma vez antes do Bloco A.

## 6.1 Registrar estado

Salvar no relatório inicial:

- commit da `main`;
- branch criada;
- project ref do Supabase;
- data/hora UTC;
- lista de migrations registradas;
- contagem de tabelas/views/functions/policies;
- advisors de segurança e performance;
- contagem de objetos dos buckets atingidos;
- status de jobs e runs;
- status do backup/PITR;
- resultado do smoke test do piloto.

## 6.2 Backup e reversibilidade

Confirmar pelo menos um:

- PITR disponível e ativo;
- backup lógico metadata-only + backup dos objetos alterados;
- snapshot/branch restaurável validado.

Não iniciar migration crítica sem restauração possível.

## 6.3 Smoke test inicial do produto

Executar e registrar:

- login de usuário real de teste;
- troca entre Resulta e AutoFleet pelo usuário multiempresa autorizado;
- bloqueio de usuário sem vínculo;
- carregamento do dashboard;
- leitura e alteração permitida de Dados da Corretora;
- gestão de equipe autorizada;
- abertura do chat principal;
- upload e leitura de um documento de teste;
- upload e leitura de mídia de teste;
- conexão/status do WhatsApp por empresa;
- leitura da lista de Rotinas;
- leitura da lista de Auxiliares;
- leitura do estado de Portais;
- execução de um fluxo somente leitura ou sandbox quando disponível.

Esses testes formam o **Broker Outcome Regression Pack** da SPEC-054.

---

# 7. BLOCO A — Fechamento P0: RPCs, view e Storage

## Objetivo

Eliminar exposições públicas críticas sem quebrar login, signup, dashboard, uploads, chat, documentos ou integrações.

## Saída do bloco

- nenhuma RPC interna crítica executável por `anon`;
- nenhum hash retornável pela API pública;
- criação de conta privilegiada inacessível diretamente ao client;
- débito de saldo inacessível publicamente;
- relatórios globais Admin/service-only;
- view UCP sem bypass de RLS;
- buckets sensíveis privados;
- UI e APIs usando signed URLs ou proxy autorizado;
- testes do Broker Outcome Regression Pack verdes.

## 7.1 Migration A1 — grants e funções críticas

Criar migration com timestamp real, por exemplo:

```text
backend/supabase/migrations/<timestamp>_spec054_a1_rpc_security.sql
```

A migration deve conter comentários `APPLY`, `VERIFY` e `ROLLBACK`.

### 7.1.1 Inventário por assinatura

Antes de alterar, consultar `pg_proc` e registrar todas as assinaturas exatas. Nunca usar `ALTER FUNCTION nome` sem a assinatura completa quando houver overload.

### 7.1.2 Revogar execução pública

Revogar `EXECUTE` de `PUBLIC`, `anon` e `authenticated` das funções internas, incluindo no mínimo:

- `public.get_user_for_login(varchar)`;
- as duas overloads de `public.create_user_account(...)`;
- `public.debit_company_balance(uuid,numeric)`;
- `public.get_token_usage_by_company(timestamptz,timestamptz)`;
- `public.get_token_usage_report(timestamptz,timestamptz)`;
- trigger functions técnicas identificadas na auditoria;
- qualquer outra `SECURITY DEFINER` sem caso de uso público formal.

Conceder somente o mínimo necessário, normalmente:

```sql
GRANT EXECUTE ON FUNCTION ... TO service_role;
```

Não conceder a `authenticated` apenas para “fazer funcionar”.

### 7.1.3 Default privileges

Aplicar, para o owner correto das migrations:

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA public
REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
```

Se houver mais de um owner relevante, tratar explicitamente. Registrar no relatório.

### 7.1.4 `search_path`

Para toda função `SECURITY DEFINER` preservada:

- qualificar tabelas e funções com schema;
- fixar `search_path` mínimo;
- incluir somente schemas realmente necessários;
- não usar `search_path = public` como única defesa;
- evitar chamadas a objetos não qualificados controláveis por usuário.

Padrão recomendado quando compatível:

```sql
SET search_path = pg_catalog, public
```

Se a função depender de `auth`, `extensions` ou outro schema, declarar conscientemente.

### 7.1.5 `get_user_for_login`

Decisão canônica:

- a API pública nunca deve retornar `password_hash`;
- a autenticação customizada pode consultar o hash apenas no server-side privilegiado;
- o caminho preferencial é remover a dependência de RPC pública e fazer consulta server-side explícita com seleção mínima;
- se a função for temporariamente preservada, ela deve ser service-only, ter `search_path` fixo e não ser chamável via chave pública.

Atualizar `lib/auth.ts` para que:

- normalize e-mail;
- selecione somente campos necessários;
- não logue hash;
- não retorne hash ao browser;
- preserve lockout e migração SHA-256 → bcrypt;
- mantenha mensagem genérica para usuário inexistente/senha inválida.

Após busca completa no repositório, remover a função somente se não houver outro consumidor. Caso contrário, mantê-la revogada e marcada como deprecated até o contract seguinte.

### 7.1.6 `create_user_account`

Decisão canônica:

- somente rotas server-side validadas criam usuário;
- `company_id`, `role`, `is_owner` e `status` são derivados no servidor;
- signup público nunca cria `admin_company` ou owner por parâmetros enviados pelo client;
- convite/equipe deve validar empresa ativa e papel do vínculo.

Ações:

1. revogar execução pública das duas overloads;
2. identificar a assinatura canônica atualmente usada;
3. atualizar chamadas server-side;
4. eliminar a overload antiga somente após confirmar zero consumidores;
5. adicionar testes de tentativa de escalada de papel.

### 7.1.7 `debit_company_balance`

Decisão canônica:

- service-only;
- `p_amount` deve ser positivo;
- saldo e ledger devem ser transacionais;
- a operação deve aceitar uma chave idempotente ou referência de transação;
- nenhum débito pode existir sem linha correspondente em `credit_transactions`.

Na SPEC-054, implementar o mínimo transacional seguro sem redesenhar billing completo. Se o contrato atual não permitir idempotência sem breaking change, criar uma nova assinatura versionada e manter a anterior revogada/deprecated até migração dos callers.

### 7.1.8 Relatórios globais

`get_token_usage_by_company` e `get_token_usage_report` devem ser Admin/service-only.

Se houver necessidade de relatório por corretora, criar consulta tenant-scoped separada que derive company da sessão. Não reutilizar função global com filtro vindo do client.

### 7.1.9 Trigger functions

Trigger functions não precisam de execução pública. Revogar grants públicos preservando os triggers existentes.

## 7.2 Migration A2 — view UCP

Criar migration:

```text
backend/supabase/migrations/<timestamp>_spec054_a2_ucp_view_security.sql
```

### Regra

Buscar todos os consumidores de `ucp_connection_summary`.

- Se for somente interna/Admin: revogar `SELECT` de `PUBLIC`, `anon` e `authenticated`, concedendo apenas role interna necessária.
- Se for tenant-facing: recriar/alterar com `security_invoker = true`, filtro tenant verificável e grant mínimo de `SELECT`.

Nunca manter owner privilegiado + grants públicos + ausência de `security_invoker`.

Adicionar teste tenant A × tenant B.

## 7.3 Storage privado e compatibilidade

### 7.3.1 Classificação canônica

| Bucket | Estado final |
|---|---|
| `portal-evidence` | privado, preservar |
| `chat-docs` | privado |
| `chat-media` | privado |
| `voice-messages` | privado |
| `avatars` | leitura pública opcional; escrita autenticada e owner-scoped |

### 7.3.2 Ordem expand/contract

Não desligar o acesso público antes de o código aceitar URLs privadas.

Executar nesta ordem:

1. inventariar todos os locais que salvam ou consomem URLs/path;
2. criar resolver central de Storage que aceite path canônico e URL legada;
3. alterar APIs para retornar signed URL curta ou stream autorizado;
4. alterar frontend para não persistir signed URL como identificador durável;
5. usar path como referência durável;
6. testar objetos existentes;
7. somente então tornar bucket privado e substituir policies;
8. backfill de referências legadas quando necessário;
9. remover compatibilidade pública apenas após contagem zero de referências antigas inseguras.

### 7.3.3 Path canônico

Novos objetos devem seguir:

```text
<company_id>/<user_id-ou-system>/<domain>/<uuid>.<ext>
```

Exemplos:

```text
<company_id>/<user_id>/chat-docs/<uuid>.pdf
<company_id>/<user_id>/chat-media/<uuid>.webp
<company_id>/<user_id>/voice-messages/<uuid>.ogg
<company_id>/system/portal-evidence/<job_id>/<uuid>.pdf
```

A empresa nunca deve ser aceita sem validação da sessão ou do job governado.

### 7.3.4 Signed URLs

- validade curta e configurável;
- não persistir URL assinada no banco;
- renovar sob autorização;
- não incluir segredo em logs;
- downloads devem emitir `Cache-Control` coerente com sensibilidade;
- documentos privados não podem ter URL pública permanente.

### 7.3.5 Policies

Substituir policies abertas por policies mínimas.

Para buckets usados apenas pelo backend service-role, manter sem policy pública.

Para upload direto autenticado, exigir:

- usuário autenticado;
- vínculo ativo na empresa;
- path iniciando pela empresa correta;
- owner ou papel permitido;
- operação específica;
- tamanho e MIME permitidos.

Não criar policy baseada em `auth.uid()` se a identidade customizada do produto não estiver mapeada ao Supabase Auth. Nesse caso, usar upload/download via rota server-side autorizada.

### 7.3.6 Validação de arquivo

- validar tamanho antes e durante upload;
- verificar MIME real/magic bytes;
- bloquear executáveis e HTML ativo quando não necessário;
- sanitizar nome;
- gerar UUID server-side;
- aplicar quota por tenant;
- registrar audit event;
- manter pipeline de sanitização antes de entregar conteúdo à LLM.

## 7.4 Testes obrigatórios do Bloco A

### RPC

- chave anon não executa `get_user_for_login`;
- chave anon não executa `create_user_account`;
- chave anon não executa `debit_company_balance`;
- authenticated não executa relatórios globais;
- login server-side continua funcionando;
- signup legítimo continua funcionando;
- tentativa de signup como owner/admin é ignorada ou rejeitada;
- lockout continua funcionando;
- migração de hash legado continua funcionando;
- hash nunca aparece em resposta HTTP.

### View

- anon não lê a view interna;
- tenant A não lê tenant B quando tenant-facing;
- Admin continua acessando quando autorizado.

### Storage

- URL pública antiga deixa de funcionar após contract;
- signed URL funciona e expira;
- tenant A não acessa objeto de tenant B;
- upload sem vínculo falha;
- MIME inválido falha;
- arquivo acima do limite falha;
- chat, documentos e voz continuam funcionando para usuário autorizado;
- portal evidence continua privado e acessível ao fluxo autorizado.

## 7.5 VERIFY do Bloco A

Executar queries read-only que confirmem:

- grants das funções;
- quantidade de funções `SECURITY DEFINER` executáveis por anon = 0, exceto exceção formal documentada;
- funções preservadas com `search_path` fixado;
- view com grant/reloptions corretos;
- buckets com estado final;
- policies abertas removidas;
- contagens de objetos inalteradas;
- login/signup/upload/download verdes;
- Broker Outcome Regression Pack verde.

## 7.6 ROLLBACK do Bloco A

Cada migration deve conter rollback documental exato:

- restaurar grants anteriores apenas para service path necessário;
- restaurar definição anterior da view;
- reativar temporariamente compatibilidade de Storage por código, não tornar documentos públicos permanentemente sem decisão;
- preservar todos os objetos;
- não reverter segurança por conveniência sem registrar incidente.

Se Storage precisar de rollback emergencial, preferir proxy server-side compatível em vez de reabrir o bucket.

---

# 8. BLOCO B — Baseline, migrations, integridade e isolamento

## Objetivo

Transformar o banco vivo em fundação reproduzível e reforçar invariantes multi-tenant sem apagar dados ou reescrever o Smith.

## Saída do bloco

- baseline metadata-only versionado;
- processo oficial de bootstrap de ambiente novo;
- migrations futuras rastreadas;
- objetos classificados;
- FKs company-scoped críticas adicionadas e validadas;
- relações cross-company impedidas no banco;
- service-only versus tenant-facing documentado;
- testes reais de isolamento;
- zero órfãos;
- zero mudança inesperada de contagem de negócio.

## 8.1 Baseline canônico

### 8.1.1 Não aplicar baseline sobre produção

O baseline representa o estado de produção em uma data de corte. Ele serve para criar ambientes novos e detectar drift. Não deve ser executado sobre o banco que o originou.

### 8.1.2 Estrutura de arquivos

Criar:

```text
backend/supabase/baseline/README.md
backend/supabase/baseline/20260724_production_schema.sql
backend/supabase/baseline/20260724_object_manifest.json
backend/supabase/baseline/20260724_migration_history.json
scripts/db/bootstrap_from_baseline.sh
scripts/db/verify_schema_drift.sh
```

A data final deve refletir a execução real.

### 8.1.3 Conteúdo do baseline

Incluir DDL e metadados necessários de:

- schemas de aplicação;
- tabelas;
- tipos;
- constraints;
- índices;
- funções;
- triggers;
- views;
- grants;
- RLS/policies;
- buckets/policies declarativas da aplicação;
- extensions requeridas.

Não incluir:

- dados de clientes;
- hashes;
- tokens;
- secrets;
- objetos internos gerenciados pelo Supabase que não devam ser recriados manualmente;
- storage objects;
- auth users reais.

### 8.1.4 Classificação de objetos

Manifest deve classificar cada objeto:

```text
canonical
legacy-compatible
service-only
platform-global
tenant-scoped
user-scoped
graveyard
historical-snapshot
manual-drift-to-normalize
```

O snapshot de maio deve ser marcado como histórico da arquitetura anterior, nunca como baseline atual.

### 8.1.5 Governança futura

A partir desta SPEC:

- toda alteração de schema entra por migration oficial;
- migration aplicada manualmente deve ser adicionada ao repositório no mesmo trabalho;
- nenhuma DDL operacional fica somente em documento de design;
- toda migration possui APPLY/VERIFY/ROLLBACK;
- CI cria banco efêmero a partir do baseline + migrations posteriores;
- CI falha em drift inesperado;
- produção não recebe baseline novamente.

## 8.2 Migration B1 — FKs de company

Adicionar FKs progressivamente usando `NOT VALID` e depois `VALIDATE CONSTRAINT` quando suportado.

### Tabelas operacionais prioritárias

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

A tabela `_ta1_resulta_agents_snapshot` deve ser classificada como snapshot histórico. Não criar FK sem antes decidir se ela permanece em `public`, vai para `graveyard` em SPEC futura ou será exportada. Esta SPEC não a remove.

### Comportamento de delete

Definir por domínio, não aplicar CASCADE indiscriminadamente.

Padrão recomendado:

- logs, auditoria, cobrança, evidências e jobs: `ON DELETE RESTRICT`;
- dados derivados regeneráveis: avaliar `CASCADE` somente com justificativa;
- referências opcionais: `SET NULL` quando histórico precisar sobreviver;
- empresas devem ser soft-deleted na aplicação; exclusão física é operação administrativa excepcional.

## 8.3 Relações cross-company

### 8.3.1 Portais

Garantir no banco:

```text
portal_jobs.company_id = portal_accounts.company_id
```

Estratégia recomendada:

1. criar constraint/unique compatível em `(id, company_id)` de `portal_accounts`;
2. criar FK composta nullable em `(account_id, company_id)`;
3. validar dados existentes;
4. manter validação de aplicação.

### 8.3.2 Rotinas e Agents

Garantir:

```text
routines.agent_id pertence à mesma company_id
```

Usar FK composta ou trigger de constraint, conforme compatibilidade do schema atual.

`agent_id` pode continuar nullable.

### 8.3.3 `routine_runs`

Adicionar de forma expand-only:

- `company_id uuid` nullable inicialmente;
- backfill por `routines.company_id`;
- índice;
- FK;
- `NOT NULL` somente após verificação;
- nenhuma alteração ainda para substituir `routine_runs` por Work Runs.

### 8.3.4 Demais relações

Verificar e impedir cruzamento em:

- auxiliary run ↔ tenant auxiliary;
- rollout ↔ tenant agent;
- approval ↔ company/run;
- document ↔ owner/company;
- connection ↔ owner/company;
- qualquer FK simples que permita ID de outra empresa.

Não criar triggers redundantes se uma FK composta resolver.

## 8.4 `agent_memories`

Antes de alterar:

- inventariar os registros atuais sem reproduzir conteúdo sensível no relatório;
- classificar cada registro como platform, tenant, agent ou user;
- preservar os registros globais técnicos;
- impedir que memória tenant seja tratada como global.

A SPEC-054 pode adicionar campos de escopo compatíveis, mas não deve redesenhar toda Memory Fabric da SPEC-052.

Estratégia expand-only possível:

- `scope_type`;
- `company_id` nullable;
- `agent_id` nullable;
- `user_id` nullable;
- check constraint coerente;
- nova unicidade por escopo;
- backfill dos sete registros conhecidos.

Se essa mudança exigir decisão sem evidência, registrar como pendência explícita para a implementação da SPEC-052, sem bloquear o restante da SPEC-054.

## 8.5 RLS e classes de acesso

### 8.5.1 Classificação obrigatória

Toda tabela pública deve pertencer a uma classe:

1. `public_read`;
2. `authenticated_global_read`;
3. `tenant_direct`;
4. `service_only`;
5. `admin_only`;
6. `deprecated_or_graveyard`.

Registrar a classificação no manifest.

### 8.5.2 Tabelas service-only

Para tabelas operadas exclusivamente pelo backend privilegiado:

- manter RLS ligado;
- zero policy pode ser intencional;
- revogar grants desnecessários de `anon` e `authenticated`;
- documentar owner e serviços consumidores;
- exigir company filter no repository;
- adicionar testes de rota.

### 8.5.3 Tabelas tenant-direct

Somente criar policy direta se a identidade real do usuário estiver disponível no JWT usado pelo PostgREST.

Não inventar policy baseada em `auth.uid()` quando o produto usa `users_v2` + iron-session sem vínculo canônico com `auth.users`.

Quando o acesso for server-side:

- validar sessão;
- resolver empresa ativa;
- validar `company_members` a cada request;
- derivar papel do vínculo;
- aplicar filtro tenant obrigatório;
- nunca aceitar company do body/query como autoridade.

## 8.6 Governança de clientes Supabase

Criar ou consolidar factories explícitas:

```text
service/admin client
user-context client
public/anon client
```

Regras:

- service key somente em servidor;
- nenhum módulo client-side importa service key;
- rota tenant-facing não usa service client sem autorização e filtro explícitos;
- funções internas recebem `TenantContext` ou equivalente;
- `company_id` é derivado uma vez e propagado como contexto confiável;
- logs registram company/run sem registrar segredo.

Adicionar teste estático que falhe se `SUPABASE_SERVICE_ROLE_KEY` aparecer em módulo client-side ou variável `NEXT_PUBLIC_*`.

## 8.7 Repository guard

Sem reescrever todo o acesso a dados, criar guard compartilhado para queries company-scoped.

Objetivo:

- reduzir chamadas soltas com service-role;
- tornar explícito quando uma tabela exige company;
- impedir operação sem tenant em repositories críticos;
- permitir exceção somente por função Admin/service formal.

Áreas prioritárias:

- Agents;
- documentos/conhecimento;
- Rotinas;
- Auxiliares;
- Portais;
- integrações/conexões;
- equipe;
- atividades/insights;
- billing/credits.

## 8.8 Testes obrigatórios do Bloco B

### Banco

- zero órfãos antes e depois;
- todas as novas FKs validam;
- inserção de company inexistente falha;
- portal job com conta de outra company falha;
- rotina com Agent de outra company falha;
- run recebe company correta;
- contagens não mudam inesperadamente.

### API multi-tenant

- usuário Resulta não lê AutoFleet;
- usuário AutoFleet não lê Resulta;
- usuário multiempresa acessa somente empresa ativa;
- troca de empresa altera corretamente o contexto;
- remoção de vínculo bloqueia acesso imediatamente;
- papel vem do vínculo daquela empresa;
- client não consegue forçar company pelo body/query/header.

### Baseline

- banco vazio sobe a partir do baseline;
- migrations posteriores aplicam;
- schema resultante corresponde ao contract esperado;
- baseline não contém dados ou segredos;
- drift script falha com diferença não autorizada.

## 8.9 VERIFY do Bloco B

- manifest completo versionado;
- bootstrap efêmero verde;
- histórico de migrations registrado;
- FKs validadas;
- zero órfãos;
- zero cross-company;
- grants coerentes com classe;
- todas as rotas críticas passam pelo contexto tenant;
- Broker Outcome Regression Pack verde.

## 8.10 ROLLBACK do Bloco B

- FKs novas podem ser removidas individualmente;
- colunas expand-only não precisam ser apagadas no rollback emergencial;
- código deve tolerar colunas novas;
- baseline nunca é aplicado em produção e não requer rollback;
- se repository guard quebrar uma rota, reverter código mantendo constraints válidas;
- não remover dados para “fazer FK passar”.

---

# 9. BLOCO C — Egress, MCP, Authority, idempotência, performance e rollout

## Objetivo

Endurecer as superfícies que permitirão ao AutoBrokers executar trabalho externo com segurança e preparar a transição para Work Runs duráveis.

## Saída do bloco

- HTTP Egress Guard integrado à tool existente;
- MCP com env mínimo, limites e revalidação;
- scopes reais no Capability Registry;
- entitlements explícitos para capabilities sensíveis do piloto;
- Authority Strict com modos off/shadow/on;
- canário concluído;
- contratos de idempotência em Rotinas, Portais e Auxiliares;
- índices críticos tratados;
- métricas e alertas mínimos;
- nenhum MCP ou HTTP tool ativado sem homologação.

## 9.1 HTTP Egress Guard

Não criar uma segunda HTTP Tool. Endurecer `HttpRequestTool` e o router existentes.

### 9.1.1 Novo módulo compartilhado

Criar, por exemplo:

```text
backend/app/security/http_egress.py
```

Responsabilidades:

- parse e normalização de URL;
- `https` obrigatório por padrão;
- allowlist de host por tool/connector;
- allowlist de porta;
- resolução DNS antes da chamada;
- bloqueio de IPv4/IPv6 privado;
- bloqueio de loopback;
- bloqueio de link-local;
- bloqueio de multicast/reserved;
- bloqueio de metadata cloud;
- revalidação de cada redirect ou redirects desligados;
- proteção contra DNS rebinding;
- timeout de connect/read/write/pool/total;
- streaming com limite de bytes;
- content-type permitido;
- normalização de headers;
- remoção/redação de segredos em logs;
- classificação de método como read/write;
- exigência de approval/idempotency para write sensível.

### 9.1.2 Metadata endpoints mínimos a bloquear

Incluir cobertura para:

- `169.254.169.254`;
- `metadata.google.internal`;
- link-local IPv6;
- localhost e aliases;
- redes RFC1918;
- hostnames que resolvam para endereço privado.

### 9.1.3 Logs

Remover logs de kwargs/body bruto.

Logar apenas:

- tool id;
- company id;
- agent id;
- host normalizado;
- método;
- status;
- latência;
- bytes;
- run/trace id;
- decisão do guard.

Nunca logar authorization, cookies, tokens, CPF, apólice completa ou body sensível.

### 9.1.4 Segredos

Headers secretos devem vir do Vault/conexão autorizada, não do prompt nem de config aberta.

### 9.1.5 Estado inicial

Como existem zero HTTP tools cadastradas, manter rollout desativado até os testes terminarem. Cadastrar somente uma tool sandbox de teste controlada antes do primeiro caso real.

## 9.2 MCP Gateway

Endurecer o gateway existente. Não instalar outro gateway.

### 9.2.1 Environment allowlist

Substituir:

```python
env = dict(os.environ)
```

por construção explícita.

Base mínima possível:

- `PATH` controlado;
- `PYTHONPATH` controlado;
- `PYTHONUNBUFFERED`;
- locale necessário;
- token específico daquele provider/conexão;
- variáveis explicitamente declaradas no manifest daquele servidor.

Nenhuma chave de LLM, Supabase service key, portal vault key ou token alheio deve chegar ao subprocesso.

### 9.2.2 Isolamento do processo

No Linux de produção:

- cwd temporário dedicado;
- permissões mínimas;
- process group próprio;
- kill do process group no timeout;
- limites de CPU/memória quando suportados;
- limite de stdout/stderr;
- arquivos temporários removidos;
- egress por servidor quando a infraestrutura permitir;
- sem shell;
- comando vindo somente do mapa interno homologado.

### 9.2.3 Revalidação no momento da chamada

Antes de `tools/call`, revalidar:

- Agent existe;
- Agent pertence à company ativa;
- tool continua habilitada;
- MCP server continua ativo e homologado;
- capability está ativa;
- entitlement permite;
- conexão pertence à mesma company/owner;
- approval está válido quando necessário;
- run/trace id está presente;
- parâmetros respeitam schema e limites.

O objeto DynamicMCPTool deve carregar ou resolver `company_id`/contexto de execução, não apenas `agent_id`.

### 9.2.4 Output

- schema validado;
- tamanho máximo;
- binário vira artifact/reference, não stdout gigante;
- erro interno não devolve stack/segredo à LLM;
- stdout/stderr sanitizados.

## 9.3 Capability Registry

### 9.3.1 Schema de scope mínimo

Preencher `scope` para todos os bindings, especialmente sensíveis.

Contract recomendado:

```json
{
  "data_scope": "platform|tenant|user",
  "operations": ["read", "prepare", "write", "send", "execute"],
  "resources": ["document", "calendar", "portal", "whatsapp", "drive"],
  "providers": ["provider-slug"],
  "allowed_targets": [],
  "max_items": 100,
  "max_bytes": 5000000,
  "approval": "never|policy|always",
  "pii": "none|limited|allowed",
  "audit": true
}
```

Não exigir campos irrelevantes para capability simples, mas `scope = {}` deixa de ser aceito para risco médio/alto.

### 9.3.2 Capability de portal

Corrigir `tenant.portal.execute`.

Preferir capabilities separadas:

- leitura;
- preparação;
- execução com side effect.

Execução deve exigir:

- conexão/Vault;
- company correta;
- journey permitida;
- approval conforme risco;
- idempotency key;
- evidência;
- limite de volume.

Não duplicar capabilities operacionais já existentes; consolidar aliases históricos.

### 9.3.3 Entitlements

Criar entitlements explícitos para capabilities sensíveis dos tenants canários:

- empresa técnica/Amandus;
- Resulta;
- AutoFleet.

Não habilitar HTTP/MCP/portal write automaticamente para todos.

Ausência de entitlement pode continuar significando herança para capabilities de baixo risco durante compatibilidade, mas risco alto deve ter decisão explícita antes do default ON.

## 9.4 Authority Strict: off, shadow e on

O env atual booleano deve evoluir para:

```text
AUTHORITY_STRICT_MODE=off|shadow|on
```

### off

Comportamento legado preservado.

### shadow

- calcula decisão estrita;
- preserva decisão legada;
- registra diferenças;
- não bloqueia usuário;
- gera métrica por Agent, capability e tool.

### on

- Registry + scope + entitlement + conexão + provider + approval governam;
- tools_config vira toggle visual compatível;
- nenhuma tool entra só por cadastro legado.

### Rollout

1. CI e testes;
2. empresa técnica/Amandus em `shadow`;
3. corrigir divergências;
4. Amandus em `on`;
5. Resulta em `shadow` e depois `on`;
6. AutoFleet em `shadow` e depois `on`;
7. default `on` somente após estabilidade;
8. remover caminho permissivo em SPEC posterior quando não houver rollback necessário.

## 9.5 Idempotency contracts

A SPEC-055 criará Work Runs universais. Esta SPEC deve preparar as estruturas atuais.

### 9.5.1 `routine_runs`

Adicionar:

- `idempotency_key text`;
- `scheduled_for timestamptz`;
- unique parcial por rotina/ocorrência;
- índice por company/status/started_at;
- preenchimento pelo scheduler.

Chave recomendada:

```text
routine:<routine_id>:<scheduled_for_utc>
```

O claim não deve criar duas execuções para a mesma ocorrência.

### 9.5.2 `portal_jobs`

Adicionar:

- `idempotency_key text` nullable para compatibilidade;
- unique parcial `(company_id, idempotency_key)` quando não nulo;
- `requested_by`/trace quando disponível;
- validação de key em journeys com side effect.

Uma tentativa repetida deve retornar o job existente ou estado conhecido, não criar ação duplicada.

### 9.5.3 `auxiliary_runs`

Adicionar idempotency key e origem do disparo quando aplicável.

### 9.5.4 Envios externos

Reutilizar logs/dedupes existentes quando corretos, mas estabelecer contract comum:

```text
company + provider + operation + business_object + semantic_version
```

Não usar somente timestamp aleatório como idempotência.

### 9.5.5 Limite desta SPEC

Não criar ainda:

- Work Run universal completo;
- checkpoint universal;
- interrupts universais;
- nova fila universal.

Isso pertence à SPEC-055.

## 9.6 Performance e higiene

### 9.6.1 Índices duplicados

Revisar equivalências confirmadas em:

- `company_credits`;
- `credit_transactions`;
- `documents`;
- `memory_processing_locks`;
- `subscriptions`.

Remover somente índice realmente redundante, sem remover índice que sustenta constraint.

Registrar antes/depois e rollback.

### 9.6.2 Índices de FK

Adicionar índices onde joins/deletes e advisors justificarem, priorizando:

- `company_members`;
- `portal_jobs`;
- `approval_requests`;
- `agent_release_rollouts`;
- `tenant_capability_entitlements`;
- `agent_mcp_connections`;
- `agent_mcp_tools`;
- FKs novas da SPEC-054.

### 9.6.3 Policies

Otimizar `auth.uid()`/`current_setting()` para initPlan somente após testes de isolamento.

### 9.6.4 Índice não usado

Banco jovem + índice não usado não autoriza remoção.

Exigir janela de observação, query inventory e rollback.

## 9.7 Observabilidade

Criar métricas/eventos mínimos:

- RPC denied por role;
- signed URL emitida/negada;
- storage cross-tenant blocked;
- SSRF guard blocked;
- HTTP bytes/latência/status;
- MCP spawn/timeout/deny;
- authority shadow diff;
- capability denied por scope/entitlement;
- idempotency hit;
- duplicate prevented;
- FK violation por domínio;
- migration verify result.

Não registrar PII desnecessária.

## 9.8 Testes obrigatórios do Bloco C

### HTTP

- loopback bloqueado;
- RFC1918 bloqueado;
- metadata cloud bloqueada;
- IPv6 local bloqueado;
- redirect para privado bloqueado;
- DNS resolve para privado e é bloqueado;
- response acima do limite interrompida;
- content-type inválido bloqueado;
- segredo não aparece em log;
- host permitido funciona;
- POST sensível sem approval/idempotency falha.

### MCP

- subprocesso não recebe Supabase key;
- subprocesso não recebe chaves de LLM alheias;
- timeout mata process group;
- output acima do limite falha de forma segura;
- tool desabilitada entre graph build e call é bloqueada;
- Agent de outra company é bloqueado;
- approval expirado é bloqueado;
- schema inválido é rejeitado.

### Authority

- off preserva legado;
- shadow não bloqueia e registra diff;
- on bloqueia tool sem capability;
- scope vazio de risco alto falha fechado;
- entitlement disabled bloqueia;
- conexão ausente bloqueia;
- provider indisponível bloqueia;
- papel inválido recebe zero capability.

### Idempotência

- mesma ocorrência de rotina gera um run;
- mesma key de portal retorna job existente;
- retry após timeout não duplica side effect simulado;
- keys são tenant-scoped;
- dois tenants podem usar a mesma key sem colisão.

## 9.9 VERIFY do Bloco C

- zero HTTP tool real ativada sem allowlist;
- zero MCP ativo sem manifest/env allowlist;
- 100% dos bindings de risco médio/alto com scope não vazio;
- entitlements canários registrados;
- shadow metrics coletadas;
- Amandus/Resulta/AutoFleet sem perda de tools legítimas;
- idempotency indexes ativos;
- zero run/job duplicado nos testes;
- advisors sem erro crítico não aceito;
- Broker Outcome Regression Pack verde.

## 9.10 ROLLBACK do Bloco C

- Authority volta de `on` para `shadow` ou `off` por env;
- scopes e entitlements permanecem como dados, não precisam ser apagados;
- HTTP tools podem ser desativadas sem remover guard;
- MCP servers podem ser desativados por catálogo;
- colunas de idempotência são expand-only;
- índices novos podem ser removidos individualmente;
- não reintroduzir herança completa de environment no MCP;
- não remover SSRF guard para corrigir integração; ajustar allowlist.

---

# 10. Broker Outcome Regression Pack final

A execução só é concluída se os fluxos abaixo funcionarem depois dos três blocos.

## Identidade e multiempresa

- login válido;
- login inválido genérico;
- lockout;
- troca Resulta ↔ AutoFleet;
- usuário sem vínculo recebe 403;
- equipe lista membros corretos;
- papel é o papel do vínculo.

## Dados e documentos

- dados da Resulta permanecem Resulta;
- dados da AutoFleet permanecem AutoFleet;
- upload de PDF privado;
- leitura autorizada por signed URL/proxy;
- tenant B não lê arquivo do tenant A;
- imagem e áudio do chat funcionam;
- documento chega ao pipeline de conhecimento sem URL pública permanente.

## Chat e agentes

- chat principal abre;
- Agent correto da empresa ativa é carregado;
- mensagem de abertura usa variáveis vivas;
- Knowledge Base Tool continua disponível conforme capability;
- human handoff/csv continuam conforme configuração e Authority.

## WhatsApp

- status por empresa não cruza tenants;
- canal Resulta não aparece na AutoFleet;
- canal AutoFleet não aparece na Resulta;
- pairing/status existente não é quebrado;
- envio sandbox autorizado funciona quando disponível.

## Rotinas e Auxiliares

- listagem carrega;
- criação/edição autorizada funciona;
- execução sandbox gera um run;
- retry não duplica ocorrência;
- entrega de teste usa canal da company correta;
- Auxiliar não atravessa tenant.

## Portais

- contas continuam cifradas;
- job somente leitura funciona em sandbox;
- account de outra company é rejeitada;
- evidence permanece privada;
- retry com mesma key não duplica job;
- `needs_human` continua recuperável.

## Admin

- relatórios globais continuam disponíveis apenas ao Admin;
- nenhuma rota pública expõe hash/custo global/conexão de outra empresa;
- cockpit de capabilities mostra estado coerente.

---

# 11. Arquivos mínimos que provavelmente serão alterados

O executor deve confirmar pelo código real. Lista inicial:

## Migrations/baseline

- `backend/supabase/migrations/`;
- `backend/supabase/baseline/`;
- `scripts/db/`.

## Auth e acesso ao Supabase

- `lib/auth.ts`;
- `lib/iron-session.ts`;
- `lib/admin/admin-auth.ts`;
- factories de Supabase Web/server;
- rotas de signup/login/equipe.

## Storage

- rotas de upload/download;
- componentes de chat/documentos/áudio/avatar;
- serviços de ingestão e referências de arquivo;
- portal evidence resolver.

## Backend Smith

- `backend/app/core/database.py`;
- `backend/app/agents/capability_resolver.py`;
- `backend/app/services/tool_authority.py`;
- `backend/app/agents/graph.py`;
- `backend/app/agents/tools/http_request.py`;
- novo `backend/app/security/http_egress.py`;
- `backend/app/services/mcp_gateway_service.py`;
- `backend/app/agents/tools/mcp_factory.py`;
- `backend/app/services/routine_engine.py`;
- `backend/portal_worker/worker.py`;
- serviços de Auxiliares e approvals.

## Testes

- testes unitários existentes;
- nova suite de segurança DB/REST;
- nova suite Storage;
- nova suite multi-tenant;
- nova suite HTTP SSRF;
- nova suite MCP;
- nova suite Authority shadow/on;
- nova suite idempotência;
- smoke test do piloto.

---

# 12. Formato obrigatório das migrations

Cada migration deve iniciar com:

```sql
-- SPEC-054 — <nome do lote>
-- PURPOSE: <objetivo>
-- MODE: EXPAND-ONLY | CONTRACT | SECURITY-CLOSURE
-- PRECONDITIONS: <condições>
-- APPLY: <como aplicar>
-- VERIFY: <queries exatas>
-- ROLLBACK: <passos exatos>
-- DATA IMPACT: NONE | BACKFILL CONTROLADO
-- LOCK RISK: LOW | MEDIUM | HIGH
```

Regras:

- `IF EXISTS`/`IF NOT EXISTS` somente quando não esconder drift importante;
- não engolir exception genérica em migration;
- não usar `DROP ... CASCADE`;
- não truncar;
- não deletar dados para satisfazer constraint;
- backfill paginado se volume justificar;
- lock timeout e statement timeout conscientes;
- verificar contagens antes/depois;
- migration deve falhar de forma explícita se precondition não for atendida.

---

# 13. CI e gates obrigatórios

## Gate 1 — lint e unit

- Python lint/type/test relevante;
- TypeScript lint/type/test relevante;
- migrations parseiam;
- nenhum segredo novo no git;
- nenhum service key em bundle client.

## Gate 2 — banco efêmero

- baseline sobe;
- migrations posteriores aplicam;
- tests DB/REST passam;
- schema diff esperado;
- rollback ensaiado onde viável.

## Gate 3 — integração

- auth;
- multiempresa;
- storage;
- chat;
- capabilities;
- routine/portal sandbox;
- HTTP/MCP security.

## Gate 4 — produção canária

- Amandus/empresa técnica;
- Resulta;
- AutoFleet;
- métricas por pelo menos uma janela operacional definida pelo executor conforme risco;
- zero cross-tenant;
- zero aumento anormal de 401/403/500;
- zero quebra de upload/download;
- zero ferramenta legítima perdida sem explicação.

## Gate 5 — conclusão

- relatório final;
- advisors finais;
- documentação atualizada;
- todos os critérios de aceite atendidos ou exceção formal aprovada pelo Founder.

---

# 14. Critérios de aceite

A SPEC-054 somente está concluída quando:

1. nenhuma RPC crítica interna for executável por `anon`;
2. nenhuma resposta pública puder conter `password_hash`;
3. signup não aceitar empresa/papel/owner arbitrários;
4. débito de saldo não puder ser chamado publicamente;
5. relatórios globais forem Admin/service-only;
6. a view UCP não contornar RLS;
7. documentos, mídias e voz forem privados por padrão;
8. `portal-evidence` continuar privado;
9. signed URLs/proxy autorizado funcionarem;
10. tenant A não acessar objeto de tenant B;
11. o banco puder ser criado em ambiente novo pelo baseline oficial;
12. migrations futuras estiverem rastreadas;
13. FKs company-scoped prioritárias estiverem validadas;
14. relações cross-company forem impedidas no banco;
15. zero órfãos forem mantidos;
16. service role estiver restrito a caminhos server-side justificados;
17. filtros tenant tiverem testes reais;
18. HTTP SSRF tests estiverem verdes;
19. MCP receber somente env permitido;
20. scopes de risco médio/alto não estiverem vazios;
21. entitlements sensíveis dos canários forem explícitos;
22. Authority Strict tiver shadow mode funcional;
23. Amandus, Resulta e AutoFleet passarem no canário;
24. Rotinas, Portais e Auxiliares possuírem idempotency key preparatória;
25. nenhuma ocorrência/job de teste for duplicada;
26. advisors não apresentarem erro crítico não aceito formalmente;
27. APPLY/VERIFY/ROLLBACK existirem;
28. Broker Outcome Regression Pack estiver verde;
29. nenhum runtime paralelo tiver sido criado;
30. relatório final estiver publicado.

---

# 15. Definition of Done por bloco

## Bloco A concluído

```text
Portas públicas críticas fechadas
+ login/signup preservados
+ Storage privado funcional
+ piloto sem regressão
```

## Bloco B concluído

```text
Banco reproduzível
+ migrations governadas
+ integridade tenant reforçada
+ zero órfãos/cross-tenant
```

## Bloco C concluído

```text
Tools e MCPs endurecidos
+ Authority governada
+ idempotência preparatória
+ rollout canário aprovado
```

## SPEC concluída

```text
Fundação segura e reproduzível
que permite avançar para Work Runs duráveis
sem reconstruir o AutoBrokers.
```

---

# 16. Relatório final obrigatório

Criar:

```text
docs/canon/reports/SPEC-054-execution-report-<YYYY-MM-DD>.md
```

Conteúdo mínimo:

1. commit inicial;
2. commit final;
3. branch/PR;
4. migrations criadas;
5. objetos alterados;
6. grants antes/depois;
7. buckets antes/depois;
8. FKs e constraints;
9. baseline criado;
10. testes executados;
11. Broker Outcome Regression Pack;
12. métricas de canário;
13. advisors antes/depois;
14. problemas encontrados;
15. decisões tomadas;
16. rollback disponível;
17. pendências legítimas para SPEC-055/056;
18. confirmação de zero perda de dados;
19. confirmação de zero runtime paralelo;
20. status final: PASS, PASS WITH ACCEPTED EXCEPTION ou FAIL.

Não incluir segredos nem dados pessoais.

---

# 17. O que não pertence à SPEC-054

Não implementar aqui:

- Work Run universal completo;
- queue universal;
- checkpoint universal;
- LangGraph interrupts universais;
- HITL universal;
- Skill Registry completo;
- Tool Gateway completo de produto;
- Artifact Hub;
- Report Studio;
- nova fábrica completa de Auxiliares;
- briefing/proatividade completos;
- Research Intelligence completa;
- Portal Admin Control Plane completo;
- billing completo do Work OS.

A SPEC-054 prepara a fundação para esses componentes.

---

# 18. Condições de parada obrigatória

O executor deve parar e solicitar decisão do CEO/Founder se:

1. backup/PITR não estiver disponível;
2. houver órfãos ou cross-tenant não previstos que exijam apagar dados;
3. fechar uma RPC exigir mudar o modelo comercial de signup/equipe;
4. tornar bucket privado exigir indisponibilidade relevante sem compatibilidade;
5. baseline revelar objeto crítico sem owner/uso identificável;
6. FK exigir comportamento de delete sem decisão segura;
7. Authority Strict remover capability essencial sem equivalente;
8. uma integração legítima exigir acesso a rede privada não documentado;
9. MCP necessitar segredo não previsto no manifest;
10. Resulta ou AutoFleet apresentarem vazamento, perda de acesso ou parada operacional;
11. migration produzir lock de alto risco incompatível com a janela;
12. houver necessidade de apagar tabela, corpus ou histórico;
13. SPEC-052/053 forem contraditas;
14. for necessário criar runtime, scheduler, registry ou Vault paralelo.

Falha de teste comum não exige aprovação: corrigir e continuar.

---

# 19. Decisões congeladas por esta SPEC

1. A execução ocorrerá em três blocos macro.
2. O executor está autorizado a avançar automaticamente com gates verdes.
3. Segurança P0 vem antes de novas features de tools.
4. O banco vivo será baseline, não alvo de replay histórico cego.
5. Service role não será autoridade implícita de toda rota tenant-facing.
6. Storage privado é o padrão.
7. Função interna não ficará pública por conveniência.
8. Company e role nunca vêm do client como autoridade.
9. FKs e constraints reforçarão invariantes já mantidas pelo código.
10. HTTP e MCP serão endurecidos antes da ativação real.
11. Scope vazio não será aceito para capability sensível.
12. Authority Strict será ativado progressivamente.
13. Idempotência será adicionada às estruturas atuais sem antecipar todo o Work Run.
14. Smith, Routine Engine e Portal Worker serão preservados.
15. Resulta e AutoFleet são canários obrigatórios.
16. Resultado do corretor é gate de qualidade, não detalhe posterior.

---

# 20. Próxima SPEC subordinada

Após a execução e aprovação desta SPEC, criar e executar:

```text
SPEC-055 — Durable Work Runs, Queue, Checkpoints & HITL
```

A SPEC-055 deverá usar a fundação entregue aqui para consolidar:

- `work_runs` como execução universal;
- steps e attempts;
- fila durável;
- leases;
- retries;
- checkpoints;
- cancelamento;
- interrupts e resume;
- approvals executáveis;
- idempotência universal;
- recuperação após crash;
- integração de Rotinas, Auxiliares e Portais sem duplicar executores;
- observabilidade de ponta a ponta.

Não iniciar a SPEC-055 enquanto os critérios P0, baseline e isolamento da SPEC-054 não estiverem aprovados.

---

# 21. Checklist final do executor

## Antes

- [ ] `main` atualizada e commit registrado.
- [ ] SPEC-052, 053, auditoria e SPEC-054 lidas.
- [ ] Backup/PITR confirmado.
- [ ] Smoke test inicial registrado.
- [ ] Branch criada.

## Bloco A

- [ ] RPCs críticas fechadas.
- [ ] Hash não exposto.
- [ ] Signup privilegiado protegido.
- [ ] Débito e relatórios globalmente protegidos.
- [ ] View UCP corrigida.
- [ ] Storage privado funcional.
- [ ] Signed URLs/proxy testados.
- [ ] Broker Outcome Pack verde.

## Bloco B

- [ ] Baseline e manifest criados.
- [ ] Bootstrap efêmero verde.
- [ ] FKs adicionadas e validadas.
- [ ] Cross-company impedido.
- [ ] Zero órfãos.
- [ ] Classes de acesso documentadas.
- [ ] Service client governado.
- [ ] Testes multi-tenant verdes.

## Bloco C

- [ ] HTTP Egress Guard integrado.
- [ ] SSRF tests verdes.
- [ ] MCP env allowlist e limites implementados.
- [ ] Revalidação em call implementada.
- [ ] Scopes preenchidos.
- [ ] Entitlements canários definidos.
- [ ] Authority shadow/on testado.
- [ ] Idempotência preparatória ativa.
- [ ] Índices revisados com rollback.
- [ ] Amandus, Resulta e AutoFleet aprovados.

## Encerramento

- [ ] Advisors finais registrados.
- [ ] Relatório final publicado.
- [ ] Índice canônico atualizado.
- [ ] Zero perda de dados confirmada.
- [ ] Zero runtime paralelo confirmado.
- [ ] Pendências transferidas para SPEC-055/056.
- [ ] Status final declarado.
