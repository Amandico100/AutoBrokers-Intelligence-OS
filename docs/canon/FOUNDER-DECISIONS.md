---
> **Status:** canônico — registro append-only
> **Criado em:** 25/07/2026
> **Função:** log imutável das decisões do Founder e do líder de plano que governam a execução
---

# Founder Decisions — registro append-only

## Regras deste documento

1. Este arquivo é **append-only**. Nenhuma entrada existente pode ser editada ou apagada.
2. Uma decisão só é revogada por uma **nova entrada** que a marque como `SUPERSEDED BY D-nn`.
3. Toda entrada declara: data, contexto, pergunta, opções, decisão, motivo, SPECs afetadas, consequência para a execução.
4. Um executor que encontrar ambiguidade material **para** e registra uma entrada `PENDENTE` aqui — não decide sozinho.
5. Decisões técnicas rotineiras **não** vêm para cá. Só o que muda arquitetura, escopo, sequência, risco ou dinheiro.

## Índice

| ID | Assunto | Estado | Data |
|---|---|---|---|
| D1 | Execução dos Lotes 1–5 da SPEC-052 | **APROVADO COM AJUSTE** | 25/07/2026 |
| D2 | Diretório canônico de migrations | **APROVADO COM PROTEÇÃO** | 25/07/2026 |
| D3 | Antecipação da fundação da SPEC-061 | **APROVADO** | 25/07/2026 |
| D4 | Captura antecipada de Usage Events | **APROVADO SEM BILLING** | 25/07/2026 |
| D5 | Escopo — proibição de redução unilateral | **APROVADO** | 25/07/2026 |
| D6 | Método de execução, blocos e gates | **APROVADO** | 25/07/2026 |
| D7 | Material de INTAKE (460 MB com PII) | **APROVADO — PRESERVAR** | 25/07/2026 |
| D8 | Pareamento WhatsApp Resulta/AutoFleet | **NOT_CONFIRMED** | 25/07/2026 |
| D9 | Memórias antigas do Claude | **APROVADO — NÃO APAGAR** | 25/07/2026 |
| D10 | Worktree e branches de execução | **APROVADO** | 25/07/2026 |
| **D11** | **Supabase Free sem PITR — Recovery Pack manual** | **APROVADO** | 25/07/2026 |
| P1 | Acessos de infraestrutura para preflight | **RESOLVIDA POR D11** | 25/07/2026 |

---

## D1 — Execução dos Lotes 1–5 da SPEC-052

**Data:** 25/07/2026 · **Estado:** APROVADO COM AJUSTE

### Contexto

A auditoria global de 25/07/2026 confirmou que a sequência 054–062 detalha o Work OS com profundidade, mas **não atribui dono executor** aos Lotes 1–5 da SPEC-052 (unificação global do RAG, Publisher único, Context Assembly 2.0, Memory Fabric e primeiro corpus global). O índice canônico declarava o programa "documentalmente completo".

### Decisão

**Não será criada SPEC-063.** Os lotes são executados dentro das SPECs existentes e de um pacote nominal de fechamento, mapeados em [`specs/ADDENDUM-SPEC-052-EXECUTION-MAP.md`](specs/ADDENDUM-SPEC-052-EXECUTION-MAP.md):

| Lote SPEC-052 | Dono executor |
|---|---|
| **Lote 1** — Unificação global (uma única coleção `autobrokers_global`) | **SPEC-054 Bloco B** |
| **Lote 2** — Global Knowledge Publisher único | pacote **SPEC-052 Cognitive Foundation Closure**, após SPEC-057 e antes da SPEC-058 |
| **Lote 3** — Context Assembly 2.0 (Outcome Router, Context Planner, Evidence Builder) | **SPEC-056 Bloco B** |
| **Lote 4** — Memory Fabric | diagnóstico/correção inicial na **SPEC-054 Bloco C**; implementação completa na **SPEC-059 Bloco A** |
| **Lote 5** — Primeiro corpus global governado | pacote **SPEC-052 Cognitive Foundation Closure**, após SPEC-057 e antes da SPEC-058 |
| Ponte Atendimento/corredores → Work Runs | **SPEC-055 — integração operacional** |

### Motivo

Os lotes são execução da SPEC soberana, não escopo novo. Criar SPEC-063 fragmentaria a autoridade e adiaria implementação — o que o índice canônico proíbe expressamente.

### Restrição explícita

A ponte de Atendimento **não** pode transformar o agente externo em um agente com todas as capacidades do Core. As restrições da SPEC-053 §5.2 permanecem integralmente.

O Lote 5 deve produzir um corpus **real e curado**, não uma quantidade artificial de documentos para satisfazer um número.

### SPECs afetadas
052, 054, 055, 056, 057, 058, 059.

---

## D2 — Diretório canônico de migrations

**Data:** 25/07/2026 · **Estado:** APROVADO COM PROTEÇÃO ADICIONAL

### Contexto

A auditoria confirmou deriva real: 21 migrations rastreadas em `supabase_migrations.schema_migrations` contra 28 arquivos `.sql` no repositório, distribuídos em **dois diretórios**, mais 3 DDLs monolíticos históricos. O cruzamento preciso revelou 9 versões aplicadas sem arquivo no repo e 16 arquivos sem versão rastreada.

### Decisão

Diretório canônico para **novas** migrations:

```text
backend/supabase/migrations/
```

**Proteções obrigatórias — nesta ordem, antes de qualquer reorganização:**

1. inventariar todos os arquivos;
2. calcular e registrar checksums;
3. confrontar com `supabase_migrations.schema_migrations` no banco vivo;
4. produzir o manifesto;
5. classificar cada arquivo (`aplicada` / `não rastreada` / `histórica` / `monolítica` / `órfã`);
6. registrar a migration isolada de `supabase/migrations/` no manifesto;
7. proteger contra dupla aplicação;
8. atualizar o tooling;
9. **somente depois** reorganizar arquivos históricos.

### Proibições

- Não mover, apagar, renomear ou reaplicar migration existente antes do manifesto aprovado.
- `schema_completo.sql`, `upgrade_v6.2.sql` e `storage_buckets.sql` **nunca** são bootstrap automático.
- DDLs monolíticos só são marcados como históricos após auditoria de referências no código e no tooling.

### SPECs afetadas
054 (Bloco B principalmente), e toda SPEC posterior que crie schema.

**Detalhamento operacional:** [`MIGRATIONS-AUTHORITY.md`](MIGRATIONS-AUTHORITY.md).

---

## D3 — Antecipação da fundação da SPEC-061

**Data:** 25/07/2026 · **Estado:** APROVADO

### Contexto

As SPECs 056, 057, 058, 059 e 060 exigem cada uma um "Portal Admin mínimo", mas a arquitetura definitiva do Admin só é definida na SPEC-061, oitava da fila. Executar a ordem literal produziria cinco conjuntos de páginas sobre a arquitetura antiga, migrados depois. A auditoria também confirmou que a autoridade de sessão admin ainda é parcialmente client-side.

### Decisão

Após a **SPEC-055**, executar a **fundação** da SPEC-061:

- autenticação administrativa server-side;
- RBAC e permissions;
- Control Plane BFF;
- Admin Command Gateway;
- shell e navegação;
- audit trail de comandos.

**Não** construir nesse ponto: Home executiva, Admin Inbox, Cockpits 360º, Hubs completos ou migração das páginas históricas — esses permanecem nos Blocos B/C da SPEC-061, após a SPEC-060.

### Motivo

Duplo ganho: elimina retrabalho garantido em cinco SPECs e fecha cedo o risco de autoridade em `localStorage`.

### SPECs afetadas
056, 057, 058, 059, 060, 061.

---

## D4 — Captura antecipada de Usage Events

**Data:** 25/07/2026 · **Estado:** APROVADO, SEM BILLING COMERCIAL

### Contexto

O modelo de negócio é consumo. As SPECs 055–060 consumiriam tokens sem ledger, e a SPEC-062 (última) precisaria fazer backfill de eventos nunca capturados. Hoje `token_usage_logs` tem 1.235 registros, todos com `billed = false`.

### Decisão

A **SPEC-055** implementa o write-path técnico **append-only** de usage events, ligado a:

```text
tenant · Work Run · step · Skill · Tool · provider · modelo
· tokens · custo técnico · Artifact · correlation · idempotency
```

Todo registro é marcado como:

```text
PRE_LAUNCH_NON_BILLABLE
```

### Proibido nesta fase

preço ao cliente · rating comercial · planos · invoices · cobrança · pagamentos · overage · multiplicador comercial.

Tudo isso permanece na **SPEC-062** e depende de decisão comercial futura do Founder.

### Motivo

Resolve o problema técnico de medição sem antecipar a definição comercial ainda em aberto.

### SPECs afetadas
055 (implementa), 062 (consome e comercializa).

---

## D5 — Escopo: proibição de redução unilateral

**Data:** 25/07/2026 · **Estado:** APROVADO

### Contexto

A auditoria sugeriu adiar PPTX/DOCX (SPEC-057), SEO/AEO e Business Discovery (SPEC-060) e personalização de Briefing por cargo (SPEC-059).

### Decisão

Essas sugestões são **propostas registradas**, não alteração canônica. **Nenhum escopo pode ser removido, adiado ou reduzido pelo executor.** As SPECs permanecem íntegras.

Qualquer redução futura exige entrada nova neste documento com decisão explícita do Founder.

### Consequência

O executor que encontrar dificuldade em uma entrega de escopo **não a remove**: completa o restante, registra a dificuldade em [`CHANGE-ADDENDA.md`](CHANGE-ADDENDA.md) e explicita no relatório final o que ficou fora e por quê.

---

## D6 — Método de execução, blocos e gates

**Data:** 25/07/2026 · **Estado:** APROVADO

### Decisão

```text
Um bloco = uma entrega coesa = um gate verificável
```

- Um bloco **não** é obrigatoriamente uma sessão nem um único commit.
- Um bloco pode ter vários commits, compactação de conversa, reinício de sessão e migrations em momentos distintos.
- A unidade de controle é o **resultado do bloco**, não a contagem de commits.
- Uma SPEC tem: **uma branch, um relatório final e um gate final**.
- Gates internos rodam **automaticamente**: aplicar → VERIFY → testes → verde → avançar.
- **Não** exigir aprovação manual do Founder entre todos os blocos.
- Parada apenas pelas oito condições canônicas do `CLAUDE.md` §11.
- Uma pasta única de execução; uma branch por SPEC/pacote.
- Recomendado: sessão nova do Claude por SPEC, usando os arquivos persistentes como contexto.

### Motivo

Lotes grandes atendem à preferência do Founder por menos idas e vindas; gates automáticos preservam segurança sem transformar o processo em burocracia de 31 aprovações.

---

## D7 — Material de INTAKE (460 MB com PII)

**Data:** 25/07/2026 · **Estado:** APROVADO — PRESERVAR

### Contexto

A auditoria localizou ~460 MB / 2.247 arquivos de material operacional bruto de Resulta e AutoFleet (áudios `.opus`, fotos, vídeos, PDFs, `.vcf`) em `AutoBrokers-Fable-Audit/docs/intake/INTAKE/`, corretamente ignorado pelo `.gitignore`, mas em cópia única de disco e sem política de retenção.

### Decisão

Esse material **não** deve ser:

- removido;
- versionado no Git;
- ingerido automaticamente;
- usado como corpus global.

Permanece preservado até existirem: backup criptografado, classificação, política de retenção, política de PII e autorização explícita de uso.

### Consequência

Nenhuma limpeza de worktrees pode ocorrer antes de D7 ser resolvida. O Lote 5 da SPEC-052 (corpus global) **não** pode usar esse material sem nova decisão.

---

## D8 — Pareamento WhatsApp de Resulta e AutoFleet

**Data:** 25/07/2026 · **Estado:** NOT_CONFIRMED

### Contexto

O [relatório da SPEC-051](reports/SPEC-051-IMPLEMENTATION-REPORT.md), de 22/07/2026, declara que a ação física de QR **não foi executada** e que nenhuma pendência física foi solicitada ao Founder. A auditoria encontrou 8 `observed_sessions` e 177 `observed_events` no banco, o que sugere pareamento posterior ou origem no ambiente técnico Amandus, sem evidência documental.

### Decisão

O estado é tratado como **`NOT_CONFIRMED`** até existir evidência física registrada.

- **Não bloqueia** a SPEC-054 nem as SPECs seguintes.
- **É obrigatório** antes do rollout final da SPEC-062.
- O relatório da SPEC-051 deve ser atualizado quando houver confirmação.

---

## D9 — Memórias antigas do Claude

**Data:** 25/07/2026 · **Estado:** APROVADO — NÃO APAGAR

### Decisão

As memórias globais do usuário **não** devem ser apagadas automaticamente pelo executor.

O [`CLAUDE.md`](../../CLAUDE.md) do repositório passa a ser a autoridade de processo do projeto e declara explicitamente (§4) que instruções baseadas em **SPEC-013** ou em interpretações superadas da **SPEC-014** não são autoridade.

### Consequência

Conflito entre memória global e `CLAUDE.md`: **`CLAUDE.md` vence**, sempre.

---

## D10 — Worktree e branches de execução

**Data:** 25/07/2026 · **Estado:** APROVADO

### Decisão

Uma única pasta persistente de execução:

```text
C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-Opus-Exec
```

Uma branch por SPEC ou pacote:

```text
chore/execution-foundation            ← Fase 0 (esta)
feat/spec054-foundation-hardening
feat/spec055-durable-work-runs
feat/spec061-control-plane-foundation
feat/spec056-skill-tool-gateway
feat/spec057-artifact-hub
feat/spec052-cognitive-foundation-closure
feat/spec058-auxiliary-routine-factory
feat/spec059-intelligence-fabric
feat/spec060-research-intelligence
feat/spec061-control-plane-full
feat/spec062-evals-billing-readiness
```

Os worktrees antigos (`AutoBrokers-Intelligence-OS`, `AutoBrokers-Fable-Exec-SPEC016`, `AutoBrokers-Fable-Audit`) **não** devem ser alterados nem removidos nesta fase.

### Motivo

Elimina a confusão de múltiplas pastas que já ocorreu, mantendo `main` como referência estável e um único ambiente de trabalho.

---

## D11 — Supabase Free sem PITR, compensado por Recovery Pack manual

**Data:** 25/07/2026 · **Estado:** APROVADO

### Contexto

O preflight do Bloco A concluiu com veredito `BLOCKED_BY_ACCESS` porque backup e PITR do Supabase não puderam ser confirmados. O Founder decidiu **permanecer no plano Free** neste momento, sem upgrade para Pro e sem ativação de PITR.

### Decisão

A ausência de PITR **deixa de bloquear** a execução, desde que, antes do primeiro write, seja produzido e validado um Recovery Pack específico e verificável.

O Recovery Pack deve conter, no mínimo:

1. backup lógico manual **quando** houver conexão de banco disponível;
2. Recovery Pack específico e verificável do bloco em execução;
3. rollback versionado por migration;
4. cópia local dos objetos de Storage afetados;
5. checksums;
6. VERIFY antes e depois de cada mudança.

### Gate de prosseguimento

Prossegue-se com **uma** destas condições:

- **A** — dump lógico completo validado **+** Recovery Pack validado; **ou**
- **B** — sem conexão de banco: Recovery Pack específico completo, objetos baixados, checksums válidos e rollback integral validado.

Para somente se **ambas** falharem.

### Resultado da aplicação em 25/07/2026 — Bloco A

Aplicou-se o **caminho B**. `pg_dump`, `psql` e Supabase CLI não estão instalados na máquina e não há string de conexão do banco disponível localmente (apenas arquivos `.env.example`, sem valores reais).

Pacote produzido em `C:\Users\amand\Backups\AutoBrokers\SPEC-054-A-20260725\` — fora do Git, fora de qualquer worktree:

| Item | Estado |
|---|---|
| Estado-antes documentado | ✅ `00-STATE-BEFORE.md` |
| ACLs, owners e `search_path` originais | ✅ |
| Definição e ACL originais da view UCP | ✅ |
| Configuração e policies originais de Storage | ✅ |
| Snapshot das 12 linhas do backfill | ✅ `messages-image-url-snapshot.csv` |
| Cópia local dos objetos | ✅ **56 objetos, 7 MB, 0 falhas** |
| Checksums SHA-256 | ✅ `storage-checksums.csv` + `checksums.sha256` |
| Scripts de rollback | ✅ 4 scripts, um por migration |
| Contagens de negócio de referência | ✅ |

**Veredito:** `READY_WITH_MANUAL_RECOVERY_PACK`

### Restrições que permanecem

- O pacote cobre **exatamente** o que o Bloco A altera. Não é substituto de backup completo do banco.
- `portal-evidence` é privado e **não** é alterado pelo Bloco A.
- Antes do **Bloco B**, que mexe em schema e integridade, será necessário reavaliar a estratégia de backup — o Recovery Pack específico não é suficiente para alterações estruturais amplas.
- A SPEC-062 §30 continua exigindo **restore comprovado** antes do go-live. D11 não revoga isso.

### SPECs afetadas
054 (desbloqueia o Bloco A), 062 (mantém a exigência de restore drill).

---

## D12 — Rotação de secrets adiada até o pré-go-live

**Data:** 25/07/2026 · **Estado:** APROVADO

### Contexto

Durante a execução do Bloco A, credenciais de produção foram compartilhadas em texto puro num canal de chat. O executor sinalizou a exposição e recomendou rotação imediata.

### Decisão do Founder

A rotação geral é **adiada até o pré-go-live**.

**Motivo:** ambiente controlado, sem clientes externos ativos, e a rotação completa durante a construção interromperia o desenvolvimento. Amandus é corretora fictícia; Resulta e AutoFleet são pilotos do Founder e sócios.

### Restrições que permanecem

Esta decisão **não** autoriza: imprimir secrets · reproduzi-los em respostas · colocá-los em commit · incluí-los em log · gravá-los em documentação · criar cópias desnecessárias.

### Gatilho de reabertura

Se for detectado segredo **versionado publicamente** ou acessível por terceiros, isso é **bloqueador** e deve ser informado imediatamente. Fora disso, nenhuma SPEC para por causa de rotação.

### Obrigação transferida

A rotação completa passa a ser **pré-condição da SPEC-062** (readiness e go-live).

---

## D13 — Ambiente controlado de pré-produção

**Data:** 25/07/2026 · **Estado:** APROVADO

### Decisão

O AutoBrokers está em ambiente controlado de construção. Amandus é fictícia; Resulta e AutoFleet são pilotos do Founder. Não há cliente externo dependente. Celulares, números e conversas são controlados pelo Founder.

**Consequência:** migrations, merges e deploys podem ser executados com autonomia, mantendo APPLY/VERIFY/ROLLBACK. Pequena regressão interna de sandbox **não** é bloqueio permanente — corrige-se dentro do mesmo bloco. O padrão de construção continua sendo definitivo de produção.

### Permanecem proibidos sem autorização específica

Envio real de WhatsApp a terceiros · ação real em portal de seguradora · ativação de agente externo · remoção irreversível de dados · vazamento entre tenants · exposição de secrets.

---

## D14 — Widget público: preservar função, remover permissão pública

**Data:** 25/07/2026 · **Estado:** CONFIRMADO PELO FOUNDER

### Confirmação

O widget público (`/embed/[agentId]`) existe no código como **funcionalidade futura** de chat incorporável ao site de uma corretora. **Não está instalado em nenhum site público de cliente** e não é usado por usuários externos. O chat do Dashboard e os WhatsApps **não** são esse widget.

### Consequência para o Bloco A

A revogação de `EXECUTE` público em `check_and_increment_rate_limit` está **correta e sem risco**: o único chamador é `backend/app/api/middleware/widget_security.py` via service role. Nenhuma compatibilidade externa bloqueia a mudança e não há sessão externa ativa a preservar.

---

## P1 — Acessos de infraestrutura  `RESOLVIDA POR D11`

**Data de abertura:** 25/07/2026 · **Estado:** PENDENTE — aguardando Founder

### Contexto

A auditoria teve acesso read-only ao Supabase, mas **não** a EasyPanel, Qdrant de produção, MinIO de produção, Redis de produção nem a evidência de backup/restore.

### Consequência

- **Não bloqueia** a Fase 0.
- **Bloqueia** qualquer write em produção da SPEC-054 até o preflight de infraestrutura ser concluído.
- A SPEC-062 §30 exige restore comprovado; sem acesso não há como agendar o drill.

### Pergunta ao Founder

Fornecer acesso read-only a EasyPanel, Qdrant, MinIO e Redis de produção, e informar se existe rotina de backup ativa hoje.

### Perguntas secundárias abertas

1. Os objetos de `chat-docs` (30) e `chat-media` (26) têm URLs públicas já enviadas a clientes por WhatsApp? Necessário antes de fechar os buckets (SPEC-054 Bloco A).
2. `backend/docker-compose.yml` espelha produção? Se sim, `minio:latest` e credenciais default viram item obrigatório de hardening.

---

## D15 — Identidade de marca da corretora entra no escopo da SPEC-057

**Data:** 25/07/2026 · **Estado:** AUTORIZADA pelo Founder (mensagem de 25/07) · **Origem:** Founder

### O que foi decidido

A SPEC-057 passa a incluir, além do Artifact Hub e do Report Studio:

1. **Captura automática da identidade visual da corretora** a partir do site e das
   redes sociais que ela declarar (Firecrawl + busca direta).
2. **Página "Identidade da corretora"** dentro de Personalização → Corretora, com
   tudo editável pelo corretor.
3. **Toda peça entregue carrega a marca da corretora** — logo obrigatório,
   paleta derivada, tipografia quando houver sinal.
4. **Catálogo de templates premium** desenhado pelo Executor, não fornecido pelo
   Founder. O Visual Acceptance Pack passa a ser **produzido** pelo Executor e
   **revisado** pelo Founder, invertendo o fluxo previsto na SPEC-057 §14.

### Palavras do Founder

> "TODOS OS LAYOUTS PQ VC TEM MUITO BOM GOSTO. MAS QUERO NIVEL MAIS PREMIUM
> ENTERPRISE, WOW POSSIVEL." · "VC NAO PRECISA ESPERAR O HUMANO... VC VAI CRIAR
> ISSO AGORA." · "EU NO FINAL VOU ANALISAR E FAZER AJUSTES SE PRECISAR."

### O que esta decisão NÃO autoriza

- Publicar peça em nome da corretora para terceiros sem aprovação.
- Capturar qualquer host que a corretora não tenha declarado.
- Usar dado de segurado em peça de demonstração.
- Reduzir o escopo original da SPEC-057 (Artifact Hub segue integral).

### Consequência

Escopo maior que o previsto. Registrado em CA-008. O gate humano da SPEC-057 §14
continua existindo — muda apenas quem produz o material que passa por ele.
